"""Pagina Streamlit: si sceglie una serie o un indicatore e se ne vede il grafico."""

from datetime import date
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from alarms import AlarmEvent, alarm_days, find_anomalous_days, find_events
from benchmark import (
    DEFAULT_MIN_VALID_DAYS,
    MOVING_WINDOWS,
    FixedBenchmark,
    MovingBenchmark,
    add_limits,
    compute_benchmark,
)
from export import (
    build_event_email,
    build_report_html,
    email_file_name,
    format_deviation,
    format_number,
    parse_recipients,
    report_file_name,
)
from indicators import (
    DEFAULT_INDICATORS,
    FORMULAS,
    DayStatus,
    Indicator,
    Input,
    classify_days,
    compute_indicator,
    valid_values,
)
from loader import CleaningReport, DataLoadError, load_daily
from settings import IndicatorSettings, load_settings, save_indicator_settings
from trend import DEFAULT_TREND_DAYS, MIN_TREND_POINTS, TREND_PERIODS, compute_trend

DATA_FILE = Path(__file__).parent / "dati" / "set-dati.xlsx"
CONFIG_FILE = Path(__file__).parent / "configurazione.json"  # R14; è nel .gitignore: contiene indirizzi e-mail
MIN_K = 0.1  # il k più piccolo che il campo accetta
LETTERS = "ABC"  # nomi degli ingressi di una formula
CUSTOM = "Personalizzato"
MIN_FACTOR = 1e-9  # il fattore deve essere maggiore di zero
DEFAULT_RANGE = (0.0, 10.0)  # intervallo plausibile di partenza per un indicatore personalizzato
DEFAULT_FIXED_PERIOD = (date(2025, 1, 1), date(2025, 12, 31))  # l'esempio della specifica
DEFAULT_K = 3.0  # ampiezza dei limiti in deviazioni standard (R7)
DEFAULT_PERSISTENCE_DAYS = 3  # giorni consecutivi fuori dai limiti prima che scatti l'allarme (R9)
ALARM_DAY, ANOMALOUS_DAY = "in allarme", "anomalo, sotto soglia"
ANOMALY_STYLE = {  # categoria: (colore, forma)
    ALARM_DAY: ("#ff3b30", "circle"),
    ANOMALOUS_DAY: ("#ffd60a", "diamond"),
}

# Colori e tratteggi del grafico. Tratteggio = [lunghezza segmento, lunghezza vuoto]; [1, 0] = linea continua.
INDICATOR_COLOR = "#4c9be8"
INDICATOR_LINE, MEAN_LINE, UPPER_LINE, LOWER_LINE = "Indicatore", "Media (μ)", "Limite superiore", "Limite inferiore"
LINE_STYLE = {
    INDICATOR_LINE: (INDICATOR_COLOR, [1, 0]),
    MEAN_LINE: ("#9aa0a6", [1, 0]),
    UPPER_LINE: ("#e5534b", [6, 4]),
    LOWER_LINE: ("#e5534b", [6, 4]),
}
EXCLUDED_COLORS = {
    DayStatus.STOPPED.value: "#f0a020",
    DayStatus.OUT_OF_RANGE.value: "#b050d0",
    DayStatus.MISSING.value: "#8a8f98",
}
STATUS_LABELS = {
    DayStatus.VALID: "giorni validi",
    DayStatus.MISSING: "con dati mancanti",
    DayStatus.STOPPED: "di fermo",
    DayStatus.OUT_OF_RANGE: "fuori scala",
}


@st.cache_data
def load_data() -> tuple[pd.DataFrame, CleaningReport]:
    return load_daily(DATA_FILE)


def format_factor(factor: float) -> str:
    return f"{factor:g}".replace(".", ",")


def describe(indicator: Indicator) -> str:
    """Formula con le colonne e i fattori, per la didascalia."""
    terms = []
    for letter, item in zip(LETTERS, indicator.inputs):
        factor = "" if item.factor == 1 else f" × {format_factor(item.factor)}"
        terms.append(f"{letter} = {item.column}{factor}")
    return f"{indicator.formula}, con " + "; ".join(terms)


def choose_indicator(
    columns: list[str], saved: dict[str, IndicatorSettings]
) -> tuple[Indicator, str, IndicatorSettings | None]:
    """Controlli per scegliere l'utenza e, se serve, cambiare formula, colonne e fattori.

    Ogni utenza parte dalla sua configurazione salvata, se c'è e se le sue colonne esistono
    nel file dei dati; altrimenti dai valori predefiniti. Restituisce l'indicatore, il nome
    della scelta e la configurazione salvata usata (None se non c'è o non è utilizzabile).
    """
    presets = {indicator.name: indicator for indicator in DEFAULT_INDICATORS}
    choice_column, formula_column = st.columns([3, 1])
    with choice_column:
        choice = st.selectbox("Utenza", [*presets, CUSTOM])
    preset = presets.get(choice)

    entry = saved_entry(saved, choice, columns)
    if entry is not None:
        defaults, default_formula, default_range = entry.inputs, entry.formula, entry.plausible_range
    elif preset is not None:
        defaults, default_formula, default_range = preset.inputs, preset.formula, preset.plausible_range or DEFAULT_RANGE
    else:
        defaults, default_formula, default_range = (), next(iter(FORMULAS)), DEFAULT_RANGE

    # Le chiavi contengono la scelta: cambiando utenza i controlli ripartono dai valori di quell'utenza.
    formulas = list(FORMULAS)
    with formula_column:
        formula = st.selectbox("Formula", formulas, index=formulas.index(default_formula), key=f"{choice}:formula")

    inputs = []
    for n, (letter, form_column) in enumerate(zip(LETTERS[: FORMULAS[formula]], st.columns(FORMULAS[formula]))):
        default = defaults[n] if n < len(defaults) else Input(columns[n])
        with form_column:
            column = st.selectbox(
                f"Colonna per {letter}", columns, index=columns.index(default.column), key=f"{choice}:{letter}:column"
            )
            factor = st.number_input(
                f"Fattore di conversione di {letter}",
                min_value=MIN_FACTOR,
                value=max(float(default.factor), MIN_FACTOR),
                format="%g",
                key=f"{choice}:{letter}:factor",
            )
        inputs.append(Input(column, factor))

    low_column, high_column = st.columns(2)
    with low_column:
        low = st.number_input("Valore minimo plausibile", value=float(default_range[0]), format="%g", key=f"{choice}:low")
    with high_column:
        high = st.number_input("Valore massimo plausibile", value=float(default_range[1]), format="%g", key=f"{choice}:high")
    if low >= high:
        st.error("Il valore minimo plausibile deve essere più basso del massimo.")
        st.stop()

    same_as_preset = preset is not None and (preset.formula, preset.inputs, preset.plausible_range) == (
        formula,
        tuple(inputs),
        (low, high),
    )
    # Un preset non modificato tiene utenza e parametro, che servono al report.
    if same_as_preset:
        return preset, choice, entry
    return Indicator("Indicatore personalizzato", formula, tuple(inputs), (low, high)), choice, entry


def saved_entry(saved: dict[str, IndicatorSettings], choice: str, columns: list[str]) -> IndicatorSettings | None:
    """La configurazione salvata di un'utenza, se le sue colonne esistono nel file dei dati (R14)."""
    entry = saved.get(choice)
    if entry is None:
        return None
    unknown = [item.column for item in entry.inputs if item.column not in columns]
    if unknown:
        st.warning(
            f"Nella configurazione salvata di «{choice}» la colonna «{unknown[0]}» non c'è nel file dei dati: "
            "si usano i valori predefiniti."
        )
        return None
    return entry


def choose_benchmark(
    index: pd.DatetimeIndex, choice: str, saved: IndicatorSettings | None
) -> tuple[FixedBenchmark | MovingBenchmark | None, float, int]:
    """Controlli per benchmark, coefficiente k e giorni dell'allarme N, di un'utenza.

    Partono dai valori salvati per quell'utenza, se ci sono. Il benchmark è None se il
    periodo fisso non è ancora completo.
    """
    first, last = index.min().date(), index.max().date()
    saved_benchmark = saved.benchmark if saved else None
    min_valid_days_default = saved_benchmark.min_valid_days if saved_benchmark else DEFAULT_MIN_VALID_DAYS
    kind_column, detail_column, min_column = st.columns([1, 2, 1])
    with kind_column:
        kind = st.radio(
            "Benchmark",
            ["Fisso", "Mobile"],
            index=1 if isinstance(saved_benchmark, MovingBenchmark) else 0,
            horizontal=True,
            key=f"{choice}:benchmark",
        )
    with min_column:
        min_valid_days = st.number_input(
            "Giorni validi minimi", min_value=2, value=min_valid_days_default, step=1, key=f"{choice}:min_valid_days"
        )
    k_column, persistence_column, _ = st.columns([1, 1, 2])
    with k_column:
        k = st.number_input(
            "Ampiezza dei limiti (k, in σ)",
            min_value=MIN_K,
            value=max(saved.k, MIN_K) if saved else DEFAULT_K,
            step=0.5,
            format="%g",
            key=f"{choice}:k",
        )
    with persistence_column:
        persistence = st.number_input(
            "Giorni consecutivi per l'allarme (N)",
            min_value=1,
            value=saved.persistence if saved else DEFAULT_PERSISTENCE_DAYS,
            step=1,
            key=f"{choice}:persistence",
        )
    with detail_column:
        if kind == "Mobile":
            window_default = saved_benchmark.window_days if isinstance(saved_benchmark, MovingBenchmark) else 365
            window = st.radio(
                "Finestra (giorni precedenti)",
                MOVING_WINDOWS,
                index=MOVING_WINDOWS.index(window_default),
                horizontal=True,
                key=f"{choice}:window",
            )
            return MovingBenchmark(window, min_valid_days), k, persistence
        period = st.date_input(
            "Periodo di riferimento",
            value=fixed_period_default(saved_benchmark, first, last),
            min_value=first,
            max_value=last,
            format="DD/MM/YYYY",
            key=f"{choice}:period",
        )
    if len(period) != 2:
        return None, k, persistence
    return FixedBenchmark(period[0], period[1], min_valid_days), k, persistence


def fixed_period_default(saved_benchmark: FixedBenchmark | MovingBenchmark | None, first: date, last: date) -> tuple[date, date]:
    """Il periodo di partenza del benchmark fisso: quello salvato, ristretto ai giorni del file, o l'esempio."""
    if isinstance(saved_benchmark, FixedBenchmark):
        start, end = max(saved_benchmark.start, first), min(saved_benchmark.end, last)
        if start <= end:
            return start, end
    return max(DEFAULT_FIXED_PERIOD[0], first), min(DEFAULT_FIXED_PERIOD[1], last)


def choose_recipients(choice: str, saved: IndicatorSettings | None) -> list[str] | None:
    """Campo dei destinatari della mail (R13). `None` se c'è un indirizzo non valido, già segnalato."""
    text = st.text_input(
        "Destinatari della mail (separati da virgola)",
        value=", ".join(saved.recipients) if saved else "",
        key=f"{choice}:recipients",
        help="Il file .eml si apre già compilato nel programma di posta. Non si invia nulla.",
    )
    try:
        return parse_recipients(text)
    except ValueError as exc:
        st.error(str(exc))
        return None


def show_save_controls(choice: str, current: IndicatorSettings | None, saved: IndicatorSettings | None) -> None:
    """Pulsante per salvare la configurazione di questa utenza in `configurazione.json`, e il suo stato (R14)."""
    note_column, button_column = st.columns([3, 1])
    with button_column:
        clicked = st.button("Salva la configurazione di questa utenza", disabled=current is None)
    if clicked and current is not None:
        try:
            save_indicator_settings(CONFIG_FILE, choice, current)
            saved = current
        except OSError as exc:
            st.error(f"Non riesco a scrivere {CONFIG_FILE.name}: {exc.strerror or exc}.")
    with note_column:
        if current is None:
            st.caption("Per salvare servono un periodo di riferimento completo e destinatari validi.")
        elif saved is None:
            st.caption(f"Valori predefiniti: questa utenza non ha ancora una configurazione salvata in {CONFIG_FILE.name}.")
        elif current == saved:
            st.caption(f"Configurazione salvata in {CONFIG_FILE.name}.")
        else:
            st.caption("Ci sono modifiche non salvate.")


def build_chart(
    series: pd.Series,
    status: pd.Series,
    limits: pd.DataFrame | None,
    spec: FixedBenchmark | MovingBenchmark | None,
    y_label: str,
    show_excluded: bool,
    anomalies: pd.Series | None = None,
    events: list[AlarmEvent] | None = None,
) -> alt.LayerChart:
    """Grafico a livelli: periodo del benchmark, linee, giorni anomali, giorni esclusi."""
    frame = pd.DataFrame({"date": series.index, INDICATOR_LINE: series.to_numpy()})
    if limits is not None:
        frame[MEAN_LINE] = limits["mean"].to_numpy()
        frame[UPPER_LINE] = limits["upper"].to_numpy()
        frame[LOWER_LINE] = limits["lower"].to_numpy()
    line_names = [name for name in LINE_STYLE if name in frame.columns]

    # L'asse y segue serie e limiti. I giorni esclusi stanno in una fascia libera sotto i dati,
    # non al loro valore: un fermo vale 0 e un picco 690, e distorcerebbero l'asse.
    finite = pd.Series(frame[line_names].to_numpy().ravel()).dropna()
    if finite.empty:
        y_scale = alt.Scale(zero=False)
        marks_y = 0.0
    else:
        span = float(finite.max() - finite.min()) or 1.0
        marks_y = float(finite.min()) - 0.05 * span
        y_scale = alt.Scale(domain=[float(finite.min()) - 0.10 * span, float(finite.max()) + 0.05 * span], zero=False)

    layers: list[alt.Chart] = []
    if isinstance(spec, FixedBenchmark):
        period = pd.DataFrame(
            {"start": [pd.Timestamp(spec.start)], "end": [pd.Timestamp(spec.end)], "label": ["Periodo del benchmark"]}
        )
        layers.append(
            alt.Chart(period)
            .mark_rect(opacity=0.12, color=INDICATOR_COLOR)
            .encode(x="start:T", x2="end:T", tooltip=alt.Tooltip("label:N", title=""))
        )

    layers.append(
        alt.Chart(frame)
        .transform_fold(line_names, as_=["linea", "valore"])
        .mark_line()
        .encode(
            x=alt.X("date:T", title="Giorno"),
            y=alt.Y("valore:Q", title=y_label, scale=y_scale),
            color=alt.Color(
                "linea:N",
                scale=alt.Scale(domain=line_names, range=[LINE_STYLE[n][0] for n in line_names]),
                legend=alt.Legend(title=None, orient="top"),
            ),
            strokeDash=alt.StrokeDash(
                "linea:N",
                scale=alt.Scale(domain=line_names, range=[LINE_STYLE[n][1] for n in line_names]),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("date:T", title="Giorno", format="%d/%m/%Y"),
                alt.Tooltip("linea:N", title="Linea"),
                alt.Tooltip("valore:Q", title="Valore", format=".4f"),
            ],
        )
    )

    anomalous = anomalies.dropna() if anomalies is not None else pd.Series(dtype=object)
    if not anomalous.empty:
        in_alarm = alarm_days(events or [])
        points = pd.DataFrame(
            {
                "date": anomalous.index,
                "valore": series[anomalous.index].to_numpy(),
                "categoria": [ALARM_DAY if day in in_alarm else ANOMALOUS_DAY for day in anomalous.index],
                "direzione": [d.value for d in anomalous],
            }
        )
        layers.append(
            alt.Chart(points)
            .mark_point(filled=True, size=60, opacity=0.95)
            .encode(
                x="date:T",
                y=alt.Y("valore:Q", scale=y_scale),
                color=alt.Color(
                    "categoria:N",
                    scale=alt.Scale(domain=list(ANOMALY_STYLE), range=[c for c, _ in ANOMALY_STYLE.values()]),
                    legend=alt.Legend(title="Giorni anomali", orient="top"),
                ),
                shape=alt.Shape(
                    "categoria:N",
                    scale=alt.Scale(domain=list(ANOMALY_STYLE), range=[s for _, s in ANOMALY_STYLE.values()]),
                    legend=alt.Legend(title="Giorni anomali", orient="top"),
                ),
                tooltip=[
                    alt.Tooltip("date:T", title="Giorno", format="%d/%m/%Y"),
                    alt.Tooltip("valore:Q", title="Valore", format=".4f"),
                    alt.Tooltip("categoria:N", title="Giorno"),
                    alt.Tooltip("direzione:N", title="Rispetto ai limiti"),
                ],
            )
        )

    excluded = status[status != DayStatus.VALID] if show_excluded else status.iloc[0:0]
    if not excluded.empty:
        marks = pd.DataFrame({"date": excluded.index, "motivo": [s.value for s in excluded], "y": marks_y})
        layers.append(
            alt.Chart(marks)
            .mark_point(shape="triangle-up", filled=True, size=45, opacity=0.9)
            .encode(
                x="date:T",
                y=alt.Y("y:Q", scale=y_scale),
                color=alt.Color(
                    "motivo:N",
                    scale=alt.Scale(domain=list(EXCLUDED_COLORS), range=list(EXCLUDED_COLORS.values())),
                    legend=alt.Legend(title="Giorni esclusi", orient="top"),
                ),
                tooltip=[alt.Tooltip("date:T", title="Giorno", format="%d/%m/%Y"), alt.Tooltip("motivo:N", title="Motivo")],
            )
        )
    # Il colore ha un significato diverso in ogni livello: scale e legende separate.
    chart = alt.layer(*layers).resolve_scale(color="independent", shape="independent")
    return chart.properties(height=400).interactive(bind_y=False)


def show_events(events: list[AlarmEvent], anomalous_days: int, persistence: int) -> None:
    """Tabella degli eventi di allarme, o il perché non ce ne sono."""
    st.subheader("Eventi di allarme")
    if not events:
        st.info(
            f"Nessun allarme: {anomalous_days} giorni anomali, ma nessuna sequenza arriva a {persistence} "
            f"giorni consecutivi dalla stessa parte dei limiti."
            if anomalous_days
            else "Nessun allarme: nessun giorno fuori dai limiti."
        )
        return
    table = pd.DataFrame(
        {
            "Inizio": [e.first_day for e in events],
            "Scatto": [e.trigger_day for e in events],
            "Fine": [e.last_day for e in events],
            "Durata (giorni)": [e.duration_days for e in events],
            "Direzione": [e.direction.value for e in events],
            "Valore": [format_number(e.value) for e in events],
            "Media (μ)": [format_number(e.mean) for e in events],
            "σ": [format_number(e.std) for e in events],
            "Scostamento %": [format_deviation(e.deviation_pct) for e in events],
        }
    )
    date_format = st.column_config.DateColumn(format="DD/MM/YYYY")
    st.dataframe(
        table,
        hide_index=True,
        width="stretch",
        column_config={"Inizio": date_format, "Scatto": date_format, "Fine": date_format},
    )


def report_settings(
    indicator: Indicator, spec: FixedBenchmark | MovingBenchmark, k: float, persistence: int, exclude: bool
) -> list[tuple[str, str]]:
    """Le impostazioni usate, come coppie etichetta/valore per il report."""
    if isinstance(spec, FixedBenchmark):
        benchmark = f"fisso, dal {spec.start:%d/%m/%Y} al {spec.end:%d/%m/%Y}"
    else:
        benchmark = f"mobile, ultimi {spec.window_days} giorni prima di ogni giorno"
    return [
        ("Indicatore", describe(indicator)),
        ("Benchmark", benchmark),
        ("Giorni validi minimi", str(spec.min_valid_days)),
        ("Limiti", f"μ ± {format_factor(k)}σ"),
        ("Persistenza (N)", f"{persistence} giorni consecutivi fuori dai limiti"),
        (
            "Giorni di fermo, fuori scala e con dati mancanti",
            "esclusi dal calcolo" if exclude else "inclusi nel calcolo",
        ),
    ]


def event_label(event: AlarmEvent) -> str:
    return (
        f"{event.first_day:%d/%m/%Y} → {event.last_day:%d/%m/%Y} · {event.direction.value} · "
        f"{event.duration_days} {'giorno' if event.duration_days == 1 else 'giorni'}"
    )


def show_event_downloads(
    events: list[AlarmEvent],
    indicator: Indicator,
    series: pd.Series,
    limits: pd.DataFrame,
    settings: list[tuple[str, str]],
    recipients: list[str] | None,
) -> None:
    """Scelta dell'evento (se più di uno) e download del suo report HTML (R12) e della sua mail `.eml` (R13).

    `recipients` è None se nel campo c'è un indirizzo non valido: la mail non si offre.
    """
    if len(events) == 1:
        event = events[0]
    else:
        chosen = st.selectbox("Evento", range(len(events)), format_func=lambda i: event_label(events[i]))
        event = events[chosen]
    st.download_button(
        "Scarica il report HTML",
        data=build_report_html(event, indicator, series, limits, settings),
        file_name=report_file_name(event, indicator),
        mime="text/html",
    )

    if recipients is None:
        return
    if not recipients:
        st.caption("Nessun destinatario: la mail si aprirà con il campo A: vuoto.")
    st.download_button(
        "Scarica la mail (.eml)",
        data=build_event_email(event, indicator, recipients),
        file_name=email_file_name(event, indicator),
        mime="message/rfc822",
    )


def show_benchmark(limits: pd.DataFrame | None, spec: FixedBenchmark | MovingBenchmark | None) -> None:
    """Media, deviazione standard e giorni validi del benchmark scelto, o il motivo per cui mancano."""
    if spec is None or limits is None:
        st.info("Scegli la data di inizio e quella di fine del periodo di riferimento.")
        return
    row = limits.iloc[-1]
    if isinstance(spec, FixedBenchmark):
        scope = f"giorni dal {spec.start:%d/%m/%Y} al {spec.end:%d/%m/%Y}"
    else:
        scope = f"{spec.window_days} giorni prima del {limits.index[-1]:%d/%m/%Y}"
    if pd.isna(row["mean"]):
        n_valid = int(row["n_valid"])
        valid_label = "giorno valido" if n_valid == 1 else "giorni validi"
        st.warning(f"Dati insufficienti ({scope}): {n_valid} {valid_label}, ne servono almeno {spec.min_valid_days}.")
    else:
        mean_column, std_column, days_column = st.columns(3)
        mean_column.metric("Media (μ)", format_number(row["mean"]))
        std_column.metric("Deviazione standard (σ)", format_number(row["std"]))
        days_column.metric("Giorni validi usati", int(row["n_valid"]), help=scope)
    if isinstance(spec, MovingBenchmark):
        st.caption(f"Benchmark mobile definito in {int(limits['mean'].notna().sum())} giorni su {len(limits)}.")


def show_trend(series: pd.Series, choice: str) -> None:
    """Pendenza della regressione lineare sugli ultimi giorni scelti (R15), o il motivo per cui manca."""
    period_column, slope_column = st.columns([2, 1])
    with period_column:
        days = st.radio(
            "Periodo del trend (ultimi giorni)",
            TREND_PERIODS,
            index=TREND_PERIODS.index(DEFAULT_TREND_DAYS),
            horizontal=True,
            key=f"{choice}:trend_days",
        )
    trend = compute_trend(series, days)
    with slope_column:
        if trend is None:
            st.metric("Pendenza del trend (per giorno)", "–")
        else:
            st.metric(
                "Pendenza del trend (per giorno)",
                f"{trend.slope_per_day:+.6f}".replace(".", ","),
                help="Quanto cambia in media l'indicatore ogni giorno: positiva se sale, negativa se scende. "
                "Moltiplicata per 30 dà la variazione in un mese.",
            )
    if trend is None:
        st.caption(
            f"Pendenza non calcolata: servono almeno {MIN_TREND_POINTS} giorni con un valore negli ultimi {days} giorni."
        )
    else:
        st.caption(
            f"Retta di regressione su {trend.n_valid} giorni con un valore, "
            f"dal {trend.period_start:%d/%m/%Y} al {trend.period_end:%d/%m/%Y}."
        )


st.set_page_config(page_title="Monitoraggio impianti", layout="wide")
st.title("Monitoraggio impianti")

try:
    data, report = load_data()
except DataLoadError as exc:
    st.error(str(exc))
    st.stop()

loaded_settings = load_settings(CONFIG_FILE)
for warning in loaded_settings.warnings:
    st.warning(warning)

mode = st.radio("Cosa guardare", ["Indicatore", "Serie del file"], horizontal=True)

if mode == "Serie del file":
    name = st.selectbox("Serie", data.columns)
    series = data[name]
    missing = f"{int(series.isna().sum())} valori mancanti in questa serie"
else:
    indicator, choice, saved = choose_indicator(list(data.columns), loaded_settings.indicators)
    name = indicator.name
    series = compute_indicator(data, indicator)
    status = classify_days(data, indicator)
    exclude = st.checkbox("Escludi giorni di fermo, fuori scala e con dati mancanti", value=True)
    if exclude:
        series = valid_values(series, status)
    st.caption(describe(indicator))
    counts = status.value_counts()
    missing = " · ".join(f"{int(counts.get(s, 0))} {STATUS_LABELS[s]}" for s in DayStatus) + (
        "" if exclude else " (tutti i giorni disegnati)"
    )

alarm_note = ""
if mode == "Indicatore":
    spec, k, persistence = choose_benchmark(data.index, choice, saved)
    recipients = choose_recipients(choice, saved)
    current = (
        None
        if spec is None or recipients is None
        else IndicatorSettings(
            indicator.formula, indicator.inputs, indicator.plausible_range, spec, k, persistence, tuple(recipients)
        )
    )
    show_save_controls(choice, current, saved)
    limits = add_limits(compute_benchmark(series, spec), k) if spec is not None else None
    anomalies = find_anomalous_days(series, limits) if limits is not None else None
    events = find_events(series, limits, persistence, name) if limits is not None else []
    if anomalies is not None:
        n_anomalous = int(anomalies.notna().sum())
        anomalous_label = "giorno anomalo" if n_anomalous == 1 else "giorni anomali"
        alarm_label = "allarme" if len(events) == 1 else "allarmi"
        alarm_note = f" · {n_anomalous} {anomalous_label} · {len(events)} {alarm_label}"
    st.altair_chart(build_chart(series, status, limits, spec, name, exclude, anomalies, events), width="stretch")
else:
    st.line_chart(series, x_label="Giorno", y_label=name)
st.caption(
    f"Periodo: {data.index.min():%d/%m/%Y} – {data.index.max():%d/%m/%Y} · {len(series)} giorni · {missing}{alarm_note}"
)

if mode == "Indicatore":
    show_benchmark(limits, spec)
    show_trend(series, choice)
    if anomalies is not None:
        show_events(events, int(anomalies.notna().sum()), persistence)
        if events:
            show_event_downloads(
                events, indicator, series, limits, report_settings(indicator, spec, k, persistence, exclude), recipients
            )

with st.expander("Pulizia dei dati"):
    incomplete = ", ".join(f"{d:%d/%m/%Y}" for d in report.incomplete_days) or "nessuna"
    st.markdown(
        f"- Righe lette dal foglio: {report.rows_read}\n"
        f"- Giorni tenuti (una riga per giorno, quella delle 23:45): {report.days_kept}\n"
        f"- Righe scartate perché non delle 23:45: {report.rows_other_time}\n"
        f"- Righe scartate perché ripetute: {report.rows_duplicate}\n"
        f"- Date scartate perché senza riga delle 23:45: {incomplete}\n"
        f"- Valori mancanti in tutta la tabella: {report.missing_cells}"
    )
