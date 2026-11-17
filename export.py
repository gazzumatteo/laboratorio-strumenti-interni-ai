"""Report HTML e mail `.eml` di un evento di allarme (R12 e R13 di SPECIFICA.md).

Questo modulo non conosce Streamlit e non calcola nulla: riceve l'evento, la
serie, i limiti e le impostazioni già pronte, e restituisce il testo del report
o i byte della mail. Il grafico del report è un SVG scritto qui, dentro l'HTML:
il file si apre anche senza rete. La mail non ha il grafico.
"""

from __future__ import annotations

import html
import re
from email import policy
from email.message import EmailMessage

import pandas as pd

from alarms import AlarmEvent
from indicators import Indicator

# Il grafico mostra l'evento con un po' di contesto prima e dopo.
CONTEXT_BEFORE = pd.Timedelta(days=30)
CONTEXT_AFTER = pd.Timedelta(days=14)

# Dimensioni del grafico in pixel: area totale e margini per gli assi.
WIDTH, HEIGHT = 900, 360
LEFT, RIGHT, TOP, BOTTOM = 70, 20, 30, 50
Y_TICKS, X_TICKS = 5, 6

INDICATOR_COLOR, MEAN_COLOR, LIMIT_COLOR, EVENT_COLOR = "#2f6fb5", "#8a8f98", "#d1342b", "#d1342b"


def format_number(value: float) -> str:
    """Quattro decimali con la virgola; «–» se il valore manca."""
    return "–" if pd.isna(value) else f"{value:.4f}".replace(".", ",")


def format_deviation(value: float) -> str:
    """Scostamento con segno e due decimali; «–» se non è calcolabile (μ = 0)."""
    return "–" if pd.isna(value) else f"{value:+.2f}".replace(".", ",")


def _date(day: pd.Timestamp) -> str:
    return f"{day:%d/%m/%Y}"


def _days(n: int) -> str:
    return "1 giorno" if n == 1 else f"{n} giorni"


def _segments(values: pd.Series) -> list[list[tuple[pd.Timestamp, float]]]:
    """I tratti di valori consecutivi: un valore mancante spezza la linea."""
    segments: list[list[tuple[pd.Timestamp, float]]] = []
    current: list[tuple[pd.Timestamp, float]] = []
    for day, value in values.items():
        if pd.isna(value):
            if current:
                segments.append(current)
            current = []
        else:
            current.append((day, float(value)))
    if current:
        segments.append(current)
    return segments


def build_event_chart_svg(event: AlarmEvent, series: pd.Series, limits: pd.DataFrame) -> str:
    """Grafico SVG dell'evento: indicatore, μ, limiti, giorni dell'evento e giorno di scatto.

    La finestra va da 30 giorni prima dell'inizio a 14 giorni dopo la fine,
    limitata ai giorni presenti nella serie.
    """
    values = series.loc[event.first_day - CONTEXT_BEFORE : event.last_day + CONTEXT_AFTER]
    window = limits.loc[values.index]
    first, last = values.index[0], values.index[-1]
    day_span = max((last - first).days, 1)

    finite = pd.concat([values, window["mean"], window["lower"], window["upper"]]).dropna()
    low, high = (float(finite.min()), float(finite.max())) if not finite.empty else (0.0, 1.0)
    pad = 0.05 * ((high - low) or 1.0)
    low, high = low - pad, high + pad
    plot_width, plot_height = WIDTH - LEFT - RIGHT, HEIGHT - TOP - BOTTOM

    def x(day: pd.Timestamp) -> float:
        return LEFT + (day - first).days / day_span * plot_width

    def y(value: float) -> float:
        return TOP + (high - value) / (high - low) * plot_height

    def lines(series_: pd.Series, css_class: str, color: str, dash: str = "") -> list[str]:
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        parts = []
        for segment in _segments(series_):
            if len(segment) == 1:  # un giorno isolato: un punto, altrimenti non si vedrebbe
                day, value = segment[0]
                parts.append(f'<circle class="{css_class}" cx="{x(day):.1f}" cy="{y(value):.1f}" r="2" fill="{color}"/>')
            else:
                points = " ".join(f"{x(day):.1f},{y(value):.1f}" for day, value in segment)
                parts.append(
                    f'<polyline class="{css_class}" points="{points}" fill="none" '
                    f'stroke="{color}" stroke-width="2"{dash_attr}/>'
                )
        return parts

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" width="100%" role="img">',
        f"<title>{html.escape(event.indicator)}: dal {_date(first)} al {_date(last)}</title>",
        f'<rect x="0" y="0" width="{WIDTH}" height="{HEIGHT}" fill="#ffffff"/>',
    ]

    # Griglia orizzontale ed etichette dell'asse y.
    for i in range(Y_TICKS):
        value = low + (high - low) * i / (Y_TICKS - 1)
        parts.append(
            f'<line x1="{LEFT}" y1="{y(value):.1f}" x2="{WIDTH - RIGHT}" y2="{y(value):.1f}" stroke="#e3e5e8"/>'
            f'<text x="{LEFT - 8}" y="{y(value) + 4:.1f}" text-anchor="end" font-size="12" fill="#4a4f57">'
            f'{f"{value:.2f}".replace(".", ",")}</text>'
        )
    # Etichette dell'asse x: date equidistanti.
    for i in range(X_TICKS):
        day = first + pd.Timedelta(days=round(day_span * i / (X_TICKS - 1)))
        # La prima e l'ultima etichetta si allineano al bordo, altrimenti escono dal grafico.
        anchor = "start" if i == 0 else "end" if i == X_TICKS - 1 else "middle"
        parts.append(
            f'<text x="{x(day):.1f}" y="{HEIGHT - BOTTOM + 20}" text-anchor="{anchor}" font-size="12" fill="#4a4f57">'
            f"{day:%d/%m/%y}</text>"
        )
    parts.append(
        f'<line x1="{LEFT}" y1="{HEIGHT - BOTTOM}" x2="{WIDTH - RIGHT}" y2="{HEIGHT - BOTTOM}" stroke="#4a4f57"/>'
    )

    parts += lines(window["mean"], "mean", MEAN_COLOR)
    parts += lines(window["upper"], "limit upper", LIMIT_COLOR, "6 4")
    parts += lines(window["lower"], "limit lower", LIMIT_COLOR, "6 4")
    parts += lines(values, "indicator", INDICATOR_COLOR)

    # Giorno di scatto: linea verticale con etichetta.
    trigger_x = x(event.trigger_day)
    parts.append(
        f'<line class="trigger" x1="{trigger_x:.1f}" y1="{TOP}" x2="{trigger_x:.1f}" y2="{HEIGHT - BOTTOM}" '
        f'stroke="#1f2328" stroke-dasharray="2 3"/>'
        f'<text x="{trigger_x + 4:.1f}" y="{TOP - 10}" font-size="12" fill="#1f2328">'
        f"scatto {_date(event.trigger_day)}</text>"
    )
    # Giorni dell'evento: cerchi rossi sopra la linea.
    for day in pd.date_range(event.first_day, event.last_day):
        if day in values.index and pd.notna(values[day]):
            parts.append(
                f'<circle class="event-day" cx="{x(day):.1f}" cy="{y(float(values[day])):.1f}" r="4" '
                f'fill="{EVENT_COLOR}"/>'
            )
    parts.append("</svg>")
    return "\n".join(parts)


def _alarm_fields(event: AlarmEvent, indicator: Indicator) -> list[tuple[str, str]]:
    """I dati dell'allarme che stanno sia nel report sia nella mail (R12, R13)."""
    deviation = format_deviation(event.deviation_pct)
    return [
        ("Utenza", indicator.utility or "non indicata"),
        ("Parametro", indicator.parameter or indicator.name),
        ("Valore rilevato (giorno di scatto)", format_number(event.value)),
        ("Media del benchmark (μ)", format_number(event.mean)),
        ("Deviazione standard (σ)", format_number(event.std)),
        ("Scostamento %", deviation if deviation == "–" else f"{deviation} %"),
    ]


def _event_period(event: AlarmEvent) -> list[tuple[str, str]]:
    return [
        ("Inizio", _date(event.first_day)),
        ("Scatto", _date(event.trigger_day)),
        ("Fine", _date(event.last_day)),
        ("Durata", _days(event.duration_days)),
        ("Direzione", f"{event.direction.value} i limiti"),
    ]


def _rows(rows: list[tuple[str, str]]) -> str:
    return "\n".join(f"<tr><th>{html.escape(label)}</th><td>{html.escape(value)}</td></tr>" for label, value in rows)


def build_report_html(
    event: AlarmEvent,
    indicator: Indicator,
    series: pd.Series,
    limits: pd.DataFrame,
    settings: list[tuple[str, str]],
) -> str:
    """Pagina HTML completa del report di un evento (R12).

    `settings` sono coppie etichetta/valore già scritte da chi chiama (benchmark,
    k, N, ...). Stesso input, stesso testo: nel report non c'è la data di generazione.
    """
    parameter = indicator.parameter or indicator.name
    lower = limits.at[event.trigger_day, "lower"]
    upper = limits.at[event.trigger_day, "upper"]
    fields = [*_alarm_fields(event, indicator), ("Limiti nel giorno di scatto", f"{format_number(lower)} – {format_number(upper)}")]
    period = _event_period(event)
    title = f"Report di allarme — {indicator.name}"
    return f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
  body {{ font-family: system-ui, -apple-system, "Segoe UI", sans-serif; color: #1f2328; background: #ffffff;
         max-width: 960px; margin: 0 auto; padding: 24px 16px; line-height: 1.4; }}
  h1 {{ font-size: 1.5rem; margin: 0 0 4px; }}
  h2 {{ font-size: 1.1rem; margin: 28px 0 8px; }}
  p.sub {{ color: #4a4f57; margin: 0; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ text-align: left; padding: 6px 10px; border-bottom: 1px solid #e3e5e8; vertical-align: top; }}
  th {{ width: 40%; font-weight: 600; }}
  .legend span {{ margin-right: 18px; white-space: nowrap; }}
  .swatch {{ display: inline-block; width: 18px; height: 3px; vertical-align: middle; margin-right: 6px; }}
  .dot {{ display: inline-block; width: 9px; height: 9px; border-radius: 50%; vertical-align: middle; margin-right: 6px; }}
  footer {{ margin-top: 28px; color: #4a4f57; font-size: 0.9rem; }}
  @media print {{ body {{ padding: 0; }} h2 {{ break-after: avoid; }} svg {{ break-inside: avoid; }} }}
</style>
</head>
<body>
<h1>{html.escape(title)}</h1>
<p class="sub">Allarme {html.escape(event.direction.value)} i limiti dal {_date(event.first_day)} al {_date(event.last_day)}.</p>

<h2>Dati dell'allarme</h2>
<table>
{_rows(fields)}
</table>

<h2>Periodo dell'evento</h2>
<table>
{_rows(period)}
</table>

<h2>Andamento</h2>
{build_event_chart_svg(event, series, limits)}
<p class="legend">
<span><i class="swatch" style="background:{INDICATOR_COLOR}"></i>{html.escape(parameter)}</span>
<span><i class="swatch" style="background:{MEAN_COLOR}"></i>Media (μ)</span>
<span><i class="swatch" style="background:{LIMIT_COLOR}"></i>Limiti μ ± kσ</span>
<span><i class="dot" style="background:{EVENT_COLOR}"></i>Giorni dell'evento</span>
</p>

<h2>Impostazioni usate</h2>
<table>
{_rows(settings)}
</table>

<footer>Scostamento % = (valore − μ) ÷ μ × 100, nel giorno di scatto. Report prodotto dall'app Monitoraggio impianti.</footer>
</body>
</html>
"""


def _file_stem(event: AlarmEvent, indicator: Indicator) -> str:
    """Utenza e data dell'evento, solo con lettere, cifre e trattini: es. SOV-SA01-P2B-2024-06-06."""
    label = re.sub(r"[^A-Za-z0-9]+", "-", indicator.utility or indicator.name).strip("-") or "indicatore"
    return f"{label}-{event.first_day:%Y-%m-%d}"


def report_file_name(event: AlarmEvent, indicator: Indicator) -> str:
    """Es. report-allarme-SOV-SA01-P2B-2024-06-06.html."""
    return f"report-allarme-{_file_stem(event, indicator)}.html"


def email_file_name(event: AlarmEvent, indicator: Indicator) -> str:
    """Es. allarme-SOV-SA01-P2B-2024-06-06.eml."""
    return f"allarme-{_file_stem(event, indicator)}.eml"


def parse_recipients(text: str) -> list[str]:
    """Indirizzi scritti separati da virgola o punto e virgola → lista senza doppioni (R13).

    Controlla solo la forma (testo, una sola @, testo): non contatta nessun server.
    Un indirizzo non valido dà `ValueError` con un messaggio per l'utente.
    """
    recipients: list[str] = []
    seen: set[str] = set()
    for raw in re.split(r"[;,]", text):
        address = raw.strip()
        if not address:
            continue
        local, at, domain = address.partition("@")
        if not (at and local and domain) or "@" in domain or re.search(r"\s", address) or any(c in address for c in "<>\"\\"):
            raise ValueError(f"«{address}» non è un indirizzo e-mail valido.")
        if address.lower() not in seen:
            seen.add(address.lower())
            recipients.append(address)
    return recipients


def build_event_email(event: AlarmEvent, indicator: Indicator, recipients: list[str]) -> bytes:
    """Il file `.eml` di un evento: una bozza già compilata, senza grafico (R13). Non invia nulla.

    `X-Unsent: 1` fa aprire il file in Outlook come messaggio da inviare. Non ci sono
    `From` né `Date`: stesso input, stesso file.
    """
    message = EmailMessage(policy=policy.SMTP)
    if recipients:
        message["To"] = ", ".join(recipients)
    message["Subject"] = (
        f"Allarme — {indicator.name}: {event.direction.value} i limiti dal {_date(event.first_day)}"
    )
    message["X-Unsent"] = "1"
    details = "\n".join(f"{label}: {value}" for label, value in _alarm_fields(event, indicator))
    period = "\n".join(f"{label}: {value}" for label, value in _event_period(event))
    message.set_content(
        f"Allarme su {indicator.utility or indicator.name}: il valore è rimasto {event.direction.value} i limiti "
        f"per {_days(event.duration_days)} consecutivi.\n\n"
        f"{details}\n\n"
        f"Periodo dell'evento\n{period}\n\n"
        "Scostamento % = (valore − μ) ÷ μ × 100, nel giorno di scatto.\n"
        "Il grafico dell'andamento è nel report HTML dell'evento.\n",
        charset="utf-8",
    )
    return message.as_bytes()
