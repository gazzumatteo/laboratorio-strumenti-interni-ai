"""Benchmark statistico: media, deviazione standard e limiti di controllo (R6–R7 di SPECIFICA.md).

Questo modulo non conosce Streamlit: riceve la serie dell'indicatore (con NaN nei
giorni esclusi) e la definizione del benchmark, e restituisce media, deviazione
standard e numero di giorni validi usati, per ogni giorno; poi i limiti μ ± kσ.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

import pandas as pd

MOVING_WINDOWS = (30, 90, 180, 365)  # giorni, come da R6
DEFAULT_MIN_VALID_DAYS = 30  # provvisorio (Q7): sotto questa soglia il benchmark non è calcolato


def _check_min_valid_days(min_valid_days: int) -> None:
    if min_valid_days < 2:
        raise ValueError("Servono almeno 2 giorni validi per calcolare una deviazione standard.")


@dataclass(frozen=True)
class FixedBenchmark:
    """Un periodo storico scelto (estremi inclusi); μ e σ restano uguali per tutti i giorni."""

    start: date
    end: date
    min_valid_days: int = DEFAULT_MIN_VALID_DAYS

    def __post_init__(self) -> None:
        if self.start > self.end:
            raise ValueError("L'inizio del periodo del benchmark deve essere prima della fine.")
        _check_min_valid_days(self.min_valid_days)


@dataclass(frozen=True)
class MovingBenchmark:
    """Gli ultimi N giorni prima di ogni giorno (il giorno stesso è escluso)."""

    window_days: int
    min_valid_days: int = DEFAULT_MIN_VALID_DAYS

    def __post_init__(self) -> None:
        if self.window_days not in MOVING_WINDOWS:
            raise ValueError(f"La finestra mobile deve essere di {', '.join(map(str, MOVING_WINDOWS))} giorni.")
        _check_min_valid_days(self.min_valid_days)


def compute_benchmark(values: pd.Series, spec: FixedBenchmark | MovingBenchmark) -> pd.DataFrame:
    """Calcola `mean`, `std` e `n_valid` per ogni giorno di `values` (stesso indice).

    I NaN (giorni esclusi) non contano mai. La deviazione standard è campionaria
    (divisore n−1). Dove i giorni validi sono meno di `min_valid_days`, `mean` e
    `std` sono NaN ("dati insufficienti"); `n_valid` resta il numero vero.
    """
    if not (isinstance(values.index, pd.DatetimeIndex) and values.index.is_monotonic_increasing):
        raise ValueError("La serie deve avere come indice date in ordine crescente.")

    if isinstance(spec, FixedBenchmark):
        period = values[(values.index >= pd.Timestamp(spec.start)) & (values.index <= pd.Timestamp(spec.end))]
        result = pd.DataFrame(
            {"mean": period.mean(), "std": period.std(), "n_valid": int(period.count())}, index=values.index
        )
    else:
        # closed="left": la finestra del giorno D va da D − N giorni a D − 1, senza D.
        window = values.rolling(f"{spec.window_days}D", closed="left")
        # Con la finestra vuota (primo giorno) il conteggio è NaN, non 0.
        n_valid = window.count().fillna(0).astype(int)
        result = pd.DataFrame({"mean": window.mean(), "std": window.std(), "n_valid": n_valid})

    insufficient = result["n_valid"] < spec.min_valid_days
    result.loc[insufficient, ["mean", "std"]] = float("nan")
    return result


def add_limits(benchmark: pd.DataFrame, k: float) -> pd.DataFrame:
    """Aggiunge i limiti di controllo (R7): `lower` = μ − kσ e `upper` = μ + kσ.

    Dove il benchmark è insufficiente (μ e σ NaN) anche i limiti sono NaN.
    Restituisce una copia: la tabella ricevuta non cambia.
    """
    if not (math.isfinite(k) and k > 0):
        raise ValueError("Il coefficiente k dei limiti deve essere un numero maggiore di zero.")
    limits = benchmark.copy()
    limits["lower"] = benchmark["mean"] - k * benchmark["std"]
    limits["upper"] = benchmark["mean"] + k * benchmark["std"]
    return limits
