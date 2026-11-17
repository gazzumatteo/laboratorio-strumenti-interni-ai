"""Caricamento e pulizia del foglio dei dati giornalieri (R1–R3 di SPECIFICA.md).

Questo modulo non conosce Streamlit: riceve un percorso e restituisce una
tabella pulita (una riga per giorno) insieme a un riepilogo di cosa è stato scartato.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

SHEET_NAME = "giornalieri"
HEADER_ROWS = 3  # righe di intestazione: tag, descrizione, nome colonna
DESCRIPTION_ROW = 1  # la descrizione (riga 2) è il nome della serie
MISSING_TEXT = "Null"  # come il telecontrollo scrive un valore mancante
DAILY_OFFSET = pd.Timedelta(hours=23, minutes=45)  # la riga delle 23:45 rappresenta il giorno


class DataLoadError(Exception):
    """Il file dei dati non si può leggere: il messaggio è pensato per l'utente."""


@dataclass(frozen=True)
class CleaningReport:
    """Cosa è successo alle righe del foglio durante la pulizia."""

    rows_read: int
    days_kept: int
    rows_other_time: int  # righe non delle 23:45 (00:00, orari sparsi, raffiche)
    rows_duplicate: int  # righe delle 23:45 ripetute per la stessa data
    incomplete_days: tuple[date, ...]  # date senza nessuna riga delle 23:45
    missing_cells: int  # valori mancanti nella tabella pulita


def load_daily(path: Path | str) -> tuple[pd.DataFrame, CleaningReport]:
    """Legge il foglio `giornalieri` e restituisce (tabella pulita, riepilogo).

    La tabella ha come indice la data (un giorno per riga, indice `date`) e una
    colonna di numeri per ogni serie, col nome della descrizione. I valori
    mancanti sono NaN: mai zero, mai interpolati.
    """
    path = Path(path)
    if not path.is_file():
        raise DataLoadError(f"File dei dati non trovato: {path}")

    try:
        raw = pd.read_excel(path, sheet_name=SHEET_NAME, header=None)
    except ValueError as exc:  # pandas segnala così un foglio che non esiste
        raise DataLoadError(f"Nel file {path.name} manca il foglio «{SHEET_NAME}».") from exc

    if raw.shape[0] <= HEADER_ROWS or raw.shape[1] < 2:
        raise DataLoadError(f"Il foglio «{SHEET_NAME}» non ha la struttura attesa (3 righe di intestazione e dati).")

    # R1: il nome della serie è la descrizione (riga 2 dell'intestazione).
    names = raw.iloc[DESCRIPTION_ROW, 1:]
    if names.isna().any() or names.duplicated().any():
        raise DataLoadError(f"Nel foglio «{SHEET_NAME}» le descrizioni delle colonne sono mancanti o ripetute.")

    body = raw.iloc[HEADER_ROWS:].reset_index(drop=True)
    try:
        timestamps = pd.to_datetime(body.iloc[:, 0])
    except (ValueError, TypeError) as exc:
        raise DataLoadError(f"Nel foglio «{SHEET_NAME}» la prima colonna non contiene date valide.") from exc
    day = timestamps.dt.normalize()

    # R2: una riga per giorno = quella delle 23:45 (i millisecondi non contano).
    is_daily_row = (timestamps.dt.floor("s") - day) == DAILY_OFFSET
    candidates = body.loc[is_daily_row].iloc[:, 1:]
    candidates.columns = pd.Index(names.to_list())
    candidates.index = pd.DatetimeIndex(day[is_daily_row], name="date")

    # Se la stessa data ha più righe delle 23:45 si tiene la prima per orario.
    by_time = timestamps[is_daily_row].to_numpy().argsort(kind="stable")
    candidates = candidates.iloc[by_time]
    is_duplicate = candidates.index.duplicated(keep="first")
    kept = candidates.loc[~is_duplicate].sort_index()

    # R3: `Null` diventa NaN. La conversione è rigorosa: un testo imprevisto
    # è un errore, non un valore mancante.
    columns = {}
    for name, column in kept.items():
        try:
            columns[name] = pd.to_numeric(column.replace(MISSING_TEXT, float("nan"))).astype("float64")
        except (ValueError, TypeError) as exc:
            raise DataLoadError(f"Colonna «{name}»: valore non numerico inatteso ({exc}).") from exc
    table = pd.DataFrame(columns, index=kept.index)

    report = CleaningReport(
        rows_read=len(body),
        days_kept=len(table),
        rows_other_time=int((~is_daily_row).sum()),
        rows_duplicate=int(is_duplicate.sum()),
        incomplete_days=tuple(d.date() for d in sorted(set(day) - set(table.index))),
        missing_cells=int(table.isna().sum().sum()),
    )
    return table, report
