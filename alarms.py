"""Giorni anomali ed eventi di allarme (R8–R10 di SPECIFICA.md).

Questo modulo non conosce Streamlit: riceve la serie dell'indicatore e i limiti
del benchmark, e restituisce i giorni anomali e gli eventi con persistenza.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

import pandas as pd

ONE_DAY = pd.Timedelta(days=1)


class Direction(StrEnum):
    """Da che parte dei limiti sta un giorno anomalo."""

    ABOVE = "sopra"
    BELOW = "sotto"


@dataclass(frozen=True)
class AlarmEvent:
    """Una sequenza di almeno N giorni consecutivi fuori dai limiti (R10)."""

    indicator: str
    first_day: pd.Timestamp  # primo giorno anomalo della sequenza
    trigger_day: pd.Timestamp  # l'N-esimo giorno: da qui l'allarme esiste
    last_day: pd.Timestamp  # ultimo giorno anomalo della sequenza
    duration_days: int
    direction: Direction
    value: float  # valore dell'indicatore nel giorno di scatto
    mean: float  # μ in vigore nel giorno di scatto
    std: float  # σ in vigore nel giorno di scatto
    deviation_pct: float  # (valore − μ) ÷ μ × 100; NaN se μ = 0


def find_anomalous_days(values: pd.Series, limits: pd.DataFrame) -> pd.Series:
    """Per ogni giorno `Direction.ABOVE`/`BELOW` se è anomalo, altrimenti None (R8).

    Anomalo = il giorno ha un valore e dei limiti, e il valore è *strettamente*
    fuori. Un giorno escluso (senza valore) o senza limiti (benchmark
    insufficiente) non è mai anomalo.
    """
    if not values.index.equals(limits.index):
        raise ValueError("La serie e i limiti devono riferirsi agli stessi giorni.")
    comparable = values.notna() & limits["lower"].notna() & limits["upper"].notna()
    above = comparable & (values > limits["upper"])
    below = comparable & (values < limits["lower"])
    # Costruita da una lista: assegnando None a una Series pandas lo trasforma in NaN.
    directions = [Direction.ABOVE if up else Direction.BELOW if down else None for up, down in zip(above, below)]
    return pd.Series(directions, index=values.index, dtype=object)


def find_events(values: pd.Series, limits: pd.DataFrame, min_days: int, indicator: str) -> list[AlarmEvent]:
    """Gli eventi di allarme, in ordine cronologico (R9, R10).

    Una sequenza è fatta di giorni di calendario consecutivi, tutti anomali e
    dalla stessa parte dei limiti; un giorno normale, escluso, senza limiti o
    dalla parte opposta la interrompe. Ogni sequenza lunga almeno `min_days`
    dà un solo evento (non uno per giorno).
    """
    if isinstance(min_days, bool) or not isinstance(min_days, int) or min_days < 1:
        raise ValueError("Il numero di giorni consecutivi per l'allarme deve essere un intero maggiore di zero.")

    events: list[AlarmEvent] = []

    def close(run: list[pd.Timestamp], direction: Direction | None) -> None:
        if direction is None or len(run) < min_days:
            return
        trigger = run[min_days - 1]
        value, mean = float(values[trigger]), float(limits.at[trigger, "mean"])
        events.append(
            AlarmEvent(
                indicator=indicator,
                first_day=run[0],
                trigger_day=trigger,
                last_day=run[-1],
                duration_days=len(run),
                direction=direction,
                value=value,
                mean=mean,
                std=float(limits.at[trigger, "std"]),
                deviation_pct=(value - mean) / mean * 100 if mean != 0 else math.nan,
            )
        )

    run: list[pd.Timestamp] = []
    run_direction: Direction | None = None
    for day, direction in find_anomalous_days(values, limits).items():
        if direction is not None and run and direction == run_direction and day - run[-1] == ONE_DAY:
            run.append(day)
            continue
        close(run, run_direction)
        run, run_direction = ([day], direction) if direction is not None else ([], None)
    close(run, run_direction)
    return events


def alarm_days(events: list[AlarmEvent]) -> set[pd.Timestamp]:
    """Tutti i giorni coperti dagli eventi, dal primo all'ultimo giorno anomalo."""
    return {day for event in events for day in pd.date_range(event.first_day, event.last_day)}
