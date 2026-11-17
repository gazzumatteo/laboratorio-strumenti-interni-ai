"""Pendenza del trend di un indicatore (R15 di SPECIFICA.md).

Questo modulo non conosce Streamlit: riceve la serie dell'indicatore (con NaN nei giorni
esclusi) e il numero di giorni del periodo, e restituisce la pendenza della retta di
regressione lineare, in unità dell'indicatore per giorno.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

TREND_PERIODS = (30, 90, 180, 365)  # giorni di calendario che l'utente può scegliere
DEFAULT_TREND_DAYS = 90
MIN_TREND_POINTS = 10  # provvisorio (Q12): sotto questa soglia la pendenza non è calcolata


@dataclass(frozen=True)
class Trend:
    """La pendenza e i giorni su cui è stata calcolata."""

    slope_per_day: float  # unità dell'indicatore per giorno; positiva = l'indicatore sale
    period_start: pd.Timestamp  # primo giorno del periodo (anche se senza valore)
    period_end: pd.Timestamp  # ultimo giorno del periodo = ultimo giorno della serie
    n_valid: int  # giorni con un valore, cioè i punti della regressione


def compute_trend(values: pd.Series, days: int, min_points: int = MIN_TREND_POINTS) -> Trend | None:
    """Pendenza della regressione lineare ai minimi quadrati sugli ultimi `days` giorni (R15).

    Il periodo finisce con l'ultimo giorno della serie e dura `days` giorni di calendario,
    estremi compresi. Contano solo i giorni con un valore: i NaN (giorni esclusi) non sono
    punti e non valgono zero. Sull'asse del tempo i giorni sono contati sul calendario,
    così un giorno escluso o assente non sposta gli altri. Restituisce `None` se i punti
    sono meno di `min_points` (e comunque meno di due: con un punto solo non c'è una retta).
    """
    if isinstance(days, bool) or not isinstance(days, int) or days < 2:
        raise ValueError("Il periodo del trend deve essere di almeno 2 giorni.")
    if not (isinstance(values.index, pd.DatetimeIndex) and values.index.is_monotonic_increasing):
        raise ValueError("La serie deve avere come indice date in ordine crescente.")
    if values.empty:
        return None

    period_end = values.index[-1]
    period_start = period_end - pd.Timedelta(days=days - 1)
    points = values[values.index >= period_start].dropna()
    if len(points) < max(min_points, 2):
        return None

    x = (points.index - period_start).days.to_numpy(dtype=float)  # giorni di calendario dall'inizio del periodo
    y = points.to_numpy(dtype=float)
    x_centered = x - x.mean()
    slope = float((x_centered * (y - y.mean())).sum() / (x_centered**2).sum())
    return Trend(slope, period_start, period_end, len(points))
