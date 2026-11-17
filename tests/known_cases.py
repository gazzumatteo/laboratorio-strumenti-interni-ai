"""Dati costruiti con anomalie in punti precisi, e il risultato atteso (V11–V14 di SPECIFICA.md).

I risultati attesi stanno qui sotto e sono stati calcolati a mano PRIMA di scrivere i test:
se un test fallisce, l'errore è nel codice dell'app o in questo calcolo, non nel confronto.

Serie base: 60 giorni, dal giorno 1 (1 gennaio 2025) al giorno 60. Il valore è 98 nei giorni
dispari e 102 in quelli pari. Il benchmark è fisso sui giorni 1–30, N = 3 e k = 3.

Calcolo a mano del benchmark (giorni 1–30: 15 valori a 98 e 15 a 102):
    media μ = 100
    ogni scarto è ±2, quindi la somma dei quadrati è 30 × 4 = 120
    varianza campionaria = 120 / 29, quindi σ = √(120/29) ≈ 2,0342
    limiti con k = 3: μ ± 3σ ≈ 93,897 e 106,103 → 98 e 102 stanno dentro, 200 sta fuori
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

import pandas as pd

from alarms import Direction

# --- Risultati attesi ----------------------------------------------------------------

FIRST_DAY = date(2025, 1, 1)  # giorno 1
DAYS = 60
BENCHMARK_DAYS = (1, 30)  # il benchmark fisso usa i giorni 1–30
EXPECTED_MEAN = 100.0
EXPECTED_STD = math.sqrt(120 / 29)
EXPECTED_LOWER = EXPECTED_MEAN - 3 * EXPECTED_STD
EXPECTED_UPPER = EXPECTED_MEAN + 3 * EXPECTED_STD
SPIKE = 200.0


@dataclass(frozen=True)
class AlarmCase:
    """Una variante della serie e gli eventi attesi (primo giorno, giorno di scatto, ultimo giorno, durata)."""

    name: str
    spike_days: tuple[int, ...]  # giorni a 200
    missing_days: tuple[int, ...]  # giorni senza valore
    persistence: int  # N
    expected: tuple[tuple[int, int, int, int], ...]  # (primo, scatto, ultimo, durata), in numeri di giorno


ALARM_CASES = (
    # V11: tre giorni consecutivi a 200 dal giorno 40, N = 3 → un evento, che scatta il giorno 42.
    AlarmCase("V11 tre giorni, N=3", (40, 41, 42), (), 3, ((40, 42, 42, 3),)),
    # Con N = 2 lo stesso evento scatta al secondo giorno e dura comunque 3 giorni.
    AlarmCase("tre giorni, N=2: scatta il giorno 41", (40, 41, 42), (), 2, ((40, 41, 42, 3),)),
    # Con N = 1 scatta subito, il primo giorno.
    AlarmCase("tre giorni, N=1: scatta il giorno 40", (40, 41, 42), (), 1, ((40, 40, 42, 3),)),
    # V12: solo due giorni a 200 → con N = 3 nessun evento, con N = 2 uno.
    AlarmCase("V12 due giorni, N=3: nessun evento", (40, 41), (), 3, ()),
    AlarmCase("V12 due giorni, N=2: un evento", (40, 41), (), 2, ((40, 41, 41, 2),)),
    # V13: un giorno normale in mezzo interrompe la sequenza → con N = 2 nessun evento.
    AlarmCase("V13 giorno normale in mezzo, N=2", (40, 42), (), 2, ()),
    # V13: anche un giorno mancante la interrompe (Q5).
    AlarmCase("V13 giorno mancante in mezzo, N=2", (40, 42), (41,), 2, ()),
    # Con N = 1 le due anomalie isolate sono due eventi distinti, non uno.
    AlarmCase("due anomalie separate, N=1: due eventi", (40, 42), (), 1, ((40, 40, 40, 1), (42, 42, 42, 1))),
    # Due sequenze separate (fuori dai giorni 1–30 del benchmark), entrambe lunghe abbastanza: due eventi.
    AlarmCase("due sequenze da tre, N=3", (40, 41, 42, 50, 51, 52), (), 3, ((40, 42, 42, 3), (50, 52, 52, 3))),
)

# V14: nell'evento di V11 il valore è 200 e μ = 100 → scostamento % = (200 − 100) ÷ 100 × 100 = +100.
EXPECTED_V11_EVENT = {
    "value": 200.0,
    "mean": 100.0,
    "std": EXPECTED_STD,
    "deviation_pct": 100.0,
    "direction": Direction.ABOVE,
}


# --- Costruzione dei dati (dopo i risultati attesi) ---------------------------------------------


def day(n: int) -> pd.Timestamp:
    """Il giorno numero n (il giorno 1 è il 1 gennaio 2025)."""
    return pd.Timestamp(FIRST_DAY) + pd.Timedelta(days=n - 1)


def build_series(
    spike_days: tuple[int, ...] = (), missing_days: tuple[int, ...] = (), spike_value: float = SPIKE
) -> pd.Series:
    """La serie base di 60 giorni (98 nei giorni dispari, 102 nei pari) con le anomalie e i mancanti indicati."""
    values = [98.0 if n % 2 == 1 else 102.0 for n in range(1, DAYS + 1)]
    for n in spike_days:
        values[n - 1] = spike_value
    for n in missing_days:
        values[n - 1] = math.nan
    return pd.Series(values, index=pd.DatetimeIndex([day(n) for n in range(1, DAYS + 1)], name="date"))
