"""Pagina Streamlit: si sceglie una serie o un indicatore e se ne vede il grafico, con benchmark e limiti."""

from datetime import date
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from benchmark import (
    DEFAULT_MIN_VALID_DAYS,
    MOVING_WINDOWS,
    FixedBenchmark,
    MovingBenchmark,
    add_limits,
    compute_benchmark,
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

DATA_FILE = Path(__file__).parent / "dati" / "set-dati.xlsx"
LETTERS = "ABC"  # nomi degli ingressi di una formula
CUSTOM = "Personalizzato"
MIN_FACTOR = 1e-9  # il fattore deve essere maggiore di zero
DEFAULT_RANGE = (0.0, 10.0)  # intervallo plausibile di partenza per un indicatore personalizzato
DEFAULT_FIXED_PERIOD = (date(2025, 1, 1), date(2025, 12, 31))  # l'esempio della specifica
DEFAULT_K = 3.0  # ampiezza dei limiti in deviazioni standard (R7)

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


def format_number(value: float) -> str:
    """Quattro decimali con la virgola."""
    return f"{value:.4f}".replace(".", ",")


def describe(indicator: Indicator) -> str:
    """Formula con le colonne e i fattori, per la didascalia."""
    terms = []
    for letter, item in zip(LETTERS, indicator.inputs):
        factor = "" if item.factor == 1 else f" × {format_factor(item.factor)}"
        terms.append(f"{letter} = {item.column}{factor}")
    return f"{indicator.formula}, con " + "; ".join(terms)


def choose_indicator(columns: list[str]) -> Indicator:
    """Controlli per scegliere l'utenza e, se serve, cambiare formula, colonne e fattori."""
    presets = {indicator.name: indicator for indicator in DEFAULT_INDICATORS}
    choice_column, formula_column = st.columns([3, 1])
    with choice_column:
        choice = st.selectbox("Utenza", [*presets, CUSTOM])
    preset = presets.get(choice)

    # Le chiavi contengono la scelta: cambiando utenza i controlli ripartono dai valori del preset.
    formulas = list(FORMULAS)
    default_formula = preset.formula if preset else formulas[0]
    with formula_column:
        formula = st.selectbox("Formula", formulas, index=formulas.index(default_formula), key=f"{choice}:formula")

    inputs = []
    for n, (letter, form_column) in enumerate(zip(LETTERS[: FORMULAS[formula]], st.columns(FORMULAS[formula]))):
        default = preset.inputs[n] if preset and n < len(preset.inputs) else Input(columns[n])
        with form_column:
            column = st.selectbox(
                f"Colonna per {letter}", columns, index=columns.index(default.column), key=f"{choice}:{letter}:column"
            )
            factor = st.number_input(
                f"Fattore di conversione di {letter}",
                min_value=MIN_FACTOR,
                value=float(default.factor),
                format="%g",
                key=f"{choice}:{letter}:factor",
            )
        inputs.append(Input(column, factor))

    default_range = preset.plausible_range if preset and preset.plausible_range else DEFAULT_RANGE
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
        return preset
    return Indicator("Indicatore personalizzato", formula, tuple(inputs), (low, high))


def choose_benchmark(index: pd.DatetimeIndex) -> tuple[FixedBenchmark | MovingBenchmark | None, float]:
    """Controlli per benchmark e coefficiente k.

    Il benchmark è None se il periodo fisso non è ancora completo.
    """
    first, last = index.min().date(), index.max().date()
    kind_column, detail_column, min_column = st.columns([1, 2, 1])
    with kind_column:
        kind = st.radio("Benchmark", ["Fisso", "Mobile"], horizontal=True)
    with min_column:
        min_valid_days = st.number_input("Giorni validi minimi", min_value=2, value=DEFAULT_MIN_VALID_DAYS, step=1)
    k_column, _ = st.columns([1, 3])
    with k_column:
        k = st.number_input("Ampiezza dei limiti (k, in σ)", min_value=0.1, value=DEFAULT_K, step=0.5, format="%g")
    with detail_column:
        if kind == "Mobile":
            window = st.radio("Finestra (giorni precedenti)", MOVING_WINDOWS, index=MOVING_WINDOWS.index(365), horizontal=True)
            return MovingBenchmark(window, min_valid_days), k
        period = st.date_input(
            "Periodo di riferimento",
            value=(max(DEFAULT_FIXED_PERIOD[0], first), min(DEFAULT_FIXED_PERIOD[1], last)),
            min_value=first,
            max_value=last,
            format="DD/MM/YYYY",
        )
    if len(period) != 2:
        return None, k
    return FixedBenchmark(period[0], period[1], min_valid_days), k


def build_chart(
    series: pd.Series,
    status: pd.Series,
    limits: pd.DataFrame | None,
    spec: FixedBenchmark | MovingBenchmark | None,
    y_label: str,
    show_excluded: bool,
) -> alt.LayerChart:
    """Grafico a livelli: periodo del benchmark, linee, giorni esclusi."""
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


st.set_page_config(page_title="Monitoraggio impianti", layout="wide")
st.title("Monitoraggio impianti")

try:
    data, report = load_data()
except DataLoadError as exc:
    st.error(str(exc))
    st.stop()

mode = st.radio("Cosa guardare", ["Indicatore", "Serie del file"], horizontal=True)

if mode == "Serie del file":
    name = st.selectbox("Serie", data.columns)
    series = data[name]
    missing = f"{int(series.isna().sum())} valori mancanti in questa serie"
else:
    indicator = choose_indicator(list(data.columns))
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

if mode == "Indicatore":
    spec, k = choose_benchmark(data.index)
    limits = add_limits(compute_benchmark(series, spec), k) if spec is not None else None
    st.altair_chart(build_chart(series, status, limits, spec, name, exclude), width="stretch")
else:
    st.line_chart(series, x_label="Giorno", y_label=name)
st.caption(
    f"Periodo: {data.index.min():%d/%m/%Y} – {data.index.max():%d/%m/%Y} · {len(series)} giorni · {missing}"
)

if mode == "Indicatore":
    show_benchmark(limits, spec)

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
