"""Calcolo degli indicatori da formule predefinite (R5 di SPECIFICA.md).

Questo modulo non conosce Streamlit: riceve la tabella pulita del `loader` e la
definizione di un indicatore, e restituisce la serie dell'indicatore.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

import pandas as pd

# Formule predefinite: nome -> numero di ingressi (A, B, C).
FORMULAS = {"A/B": 2, "(A+B)/C": 3}

# La portata media è in l/s; il volume del giorno in m³ è portata × 86.400 s ÷ 1.000 l/m³.
L_PER_S_TO_M3_PER_DAY = 86.4


@dataclass(frozen=True)
class Input:
    """Una colonna della tabella e il fattore che la converte nell'unità voluta."""

    column: str
    factor: float = 1.0

    def __post_init__(self) -> None:
        if not (math.isfinite(self.factor) and self.factor > 0):
            raise ValueError(f"Il fattore di conversione di «{self.column}» deve essere maggiore di zero.")


@dataclass(frozen=True)
class Indicator:
    """Un indicatore: una formula predefinita applicata a colonne della tabella.

    `plausible_range` (estremi inclusi) è l'intervallo di valori fisicamente
    possibili: fuori da qui il giorno è «fuori scala». `None` = nessun controllo.
    `utility` (l'utenza, es. «SOV-SA01 P2B») e `parameter` (cosa si misura, es.
    «Energia specifica [kWh/m³]») servono ai report; se mancano, restano vuoti.
    """

    name: str
    formula: str
    inputs: tuple[Input, ...]
    plausible_range: tuple[float, float] | None = None
    utility: str = ""
    parameter: str = ""

    def __post_init__(self) -> None:
        if self.formula not in FORMULAS:
            raise ValueError(f"Formula sconosciuta «{self.formula}»: quelle disponibili sono {', '.join(FORMULAS)}.")
        if len(self.inputs) != FORMULAS[self.formula]:
            raise ValueError(f"La formula {self.formula} richiede {FORMULAS[self.formula]} ingressi, non {len(self.inputs)}.")
        if self.plausible_range is not None:
            low, high = self.plausible_range
            if not (math.isfinite(low) and math.isfinite(high) and low < high):
                raise ValueError("L'intervallo plausibile deve avere due estremi finiti, con il minimo sotto il massimo.")


class DayStatus(StrEnum):
    """Perché un giorno entra o non entra nel benchmark (R4)."""

    VALID = "valido"
    MISSING = "mancante"
    STOPPED = "fermo"
    OUT_OF_RANGE = "fuori scala"


def _numerator_denominator(table: pd.DataFrame, indicator: Indicator) -> tuple[pd.Series, pd.Series]:
    """Numeratore e denominatore della formula, con i fattori già applicati."""
    values = [table[i.column] * i.factor for i in indicator.inputs]
    if indicator.formula == "A/B":
        return values[0], values[1]
    return values[0] + values[1], values[2]  # (A+B)/C


def compute_indicator(table: pd.DataFrame, indicator: Indicator) -> pd.Series:
    """Applica i fattori agli ingressi, poi la formula; stesso indice (date) della tabella.

    Un ingresso mancante dà un risultato mancante (mai zero). Una divisione per
    zero dà un risultato mancante, non infinito: un infinito non è un valore misurato.
    """
    numerator, denominator = _numerator_denominator(table, indicator)
    return (numerator / denominator.where(denominator != 0)).rename(indicator.name)


def classify_days(table: pd.DataFrame, indicator: Indicator) -> pd.Series:
    """Assegna a ogni giorno un solo motivo (R4), in quest'ordine di precedenza:

    1. mancante: un ingresso manca;
    2. fermo: numeratore o denominatore ≤ 0 (l'impianto non ha lavorato o non ha trattato acqua);
    3. fuori scala: valore fuori dall'intervallo plausibile;
    4. valido.

    Per (A+B)/C basta una pompa in marcia: il giorno è di fermo solo se A+B ≤ 0.
    """
    numerator, denominator = _numerator_denominator(table, indicator)
    value = compute_indicator(table, indicator)
    missing = numerator.isna() | denominator.isna()
    stopped = ~missing & ((numerator <= 0) | (denominator <= 0))
    if indicator.plausible_range is None:
        out_of_range = pd.Series(False, index=table.index)
    else:
        low, high = indicator.plausible_range
        out_of_range = ~missing & ~stopped & ((value < low) | (value > high))

    status = pd.Series(DayStatus.VALID, index=table.index, dtype=object)
    status[out_of_range] = DayStatus.OUT_OF_RANGE
    status[stopped] = DayStatus.STOPPED
    status[missing] = DayStatus.MISSING
    return status.rename("status")


def valid_values(values: pd.Series, status: pd.Series) -> pd.Series:
    """I valori dei soli giorni validi; negli altri giorni NaN (la linea si interrompe)."""
    return values.where(status == DayStatus.VALID)


SPECIFIC_ENERGY = "Energia specifica [kWh/m³]"


def _specific_energy(utility: str, energy: str, flow: str, plausible_range: tuple[float, float]) -> Indicator:
    inputs = (Input(energy), Input(flow, L_PER_S_TO_M3_PER_DAY))
    return Indicator(f"Energia specifica {utility} [kWh/m³]", "A/B", inputs, plausible_range, utility, SPECIFIC_ENERGY)


# Utenze preconfigurate (R5b). Per ora in codice; passeranno in `settings` (R14).
DEFAULT_INDICATORS: tuple[Indicator, ...] = (
    _specific_energy("SOV-SA01 P2B", "SOV-SA01 Energia P2B", "SOV-SA01 Portata media P2B", (0, 5)),
    _specific_energy("SOV-SA01 P3A", "SOV-SA01 Energia P3A", "SOV-SA01 Portata media P3A", (0, 5)),
    Indicator(
        "Energia specifica SFI-SA02 [kWh/m³]",
        "(A+B)/C",
        (
            Input("SFI-SA02 Energia P1"),
            Input("SFI-SA02 Energia P2"),
            Input("SFI-SA02 Portata media", L_PER_S_TO_M3_PER_DAY),
        ),
        (0, 10),
        "SFI-SA02",
        SPECIFIC_ENERGY,
    ),
)
