"""Caricamento e pulizia del foglio giornaliero (R1–R3; V1, V7, V8) su file costruiti nel test.

Ogni file ha la stessa struttura di quello vero: riga 1 = tag, riga 2 = descrizione (il nome della serie),
riga 3 = nome della colonna, poi i dati; la prima colonna è la data e ora.
"""

import hashlib
from datetime import datetime
from pathlib import Path

import pytest
from openpyxl import Workbook

from loader import DataLoadError, load_daily

DESCRIPTIONS = ("Energia", "Portata")


def write_workbook(path: Path, rows, descriptions=DESCRIPTIONS, sheet="giornalieri") -> Path:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = sheet
    worksheet.append([None, *[f"TAG{i}" for i in range(len(descriptions))]])
    worksheet.append([None, *descriptions])
    worksheet.append(["DateTime", *[f"TAG{i}" for i in range(len(descriptions))]])
    for row in rows:
        worksheet.append(list(row))
    workbook.save(path)
    return path


def at(day: int, h: int = 23, m: int = 45, s: int = 0, ms: int = 0) -> datetime:
    return datetime(2025, 3, day, h, m, s, ms * 1000)


# --- Una riga per giorno (R2) -----------------------------------------------------------------


def test_tiene_solo_la_riga_delle_23_45_e_scarta_le_altre(tmp_path):
    path = write_workbook(
        tmp_path / "d.xlsx",
        [
            (at(1, 9, 13, 8), 1.0, 1.0),  # orario sparso
            (at(1), 10.0, 100.0),
            (at(2, 0, 0), 2.0, 2.0),  # mezzanotte
            (at(2), 20.0, 200.0),
            (at(3, 12, 0), 3.0, 3.0),
            (at(3), 30.0, 300.0),
        ],
    )
    table, report = load_daily(path)
    assert table["Energia"].tolist() == [10.0, 20.0, 30.0]
    assert table["Portata"].tolist() == [100.0, 200.0, 300.0]
    assert report.rows_read == 6 and report.days_kept == 3 and report.rows_other_time == 3
    assert report.rows_duplicate == 0 and report.incomplete_days == ()


def test_l_indice_e_la_data_un_giorno_per_riga_in_ordine(tmp_path):
    # Righe scritte in ordine sparso: la tabella è comunque ordinata per giorno e senza date ripetute.
    path = write_workbook(tmp_path / "d.xlsx", [(at(3), 3.0, 3.0), (at(1), 1.0, 1.0), (at(2), 2.0, 2.0)])
    table, _ = load_daily(path)
    assert [d.day for d in table.index] == [1, 2, 3]
    assert table.index.is_unique and table.index.is_monotonic_increasing
    assert all(d.hour == 0 and d.minute == 0 for d in table.index)  # la data, senza orario


def test_v8_tre_righe_alle_23_45_della_stessa_data_resta_la_prima(tmp_path):
    # Differiscono di 1 ms. Nel file sono scritte fuori ordine: la prima *per orario* ha valore 1.
    path = write_workbook(
        tmp_path / "d.xlsx",
        [
            (at(1, ms=2), 3.0, 30.0),
            (at(1, ms=0), 1.0, 10.0),
            (at(1, ms=1), 2.0, 20.0),
        ],
    )
    table, report = load_daily(path)
    assert len(table) == 1
    assert table["Energia"].iloc[0] == 1.0 and table["Portata"].iloc[0] == 10.0
    assert report.rows_duplicate == 2 and report.days_kept == 1


def test_giorno_senza_riga_delle_23_45_e_segnalato_e_assente(tmp_path):
    path = write_workbook(
        tmp_path / "d.xlsx",
        [(at(1), 1.0, 1.0), (at(2, 12, 30), 2.0, 2.0), (at(3), 3.0, 3.0)],
    )
    table, report = load_daily(path)
    assert [d.day for d in table.index] == [1, 3]
    assert [d.day for d in report.incomplete_days] == [2]


# --- Valori mancanti (R3): V7 ------------------------------------------------------------------


def test_v7_null_diventa_mancante_non_zero(tmp_path):
    path = write_workbook(tmp_path / "d.xlsx", [(at(1), "Null", 5.0), (at(2), 0, 6.0), (at(3), 7.0, "Null")])
    table, report = load_daily(path)
    assert table["Energia"].isna().tolist() == [True, False, False]
    assert table["Portata"].isna().tolist() == [False, False, True]
    assert table["Energia"].iloc[1] == 0.0  # uno zero vero resta zero
    assert report.missing_cells == 2


def test_le_colonne_sono_numeri_anche_con_valori_mancanti(tmp_path):
    path = write_workbook(tmp_path / "d.xlsx", [(at(1), "Null", 1.0), (at(2), "Null", 2.0)])
    table, _ = load_daily(path)
    assert str(table["Energia"].dtype) == "float64"


def test_il_nome_della_serie_e_la_descrizione(tmp_path):
    path = write_workbook(tmp_path / "d.xlsx", [(at(1), 1.0, 2.0, 3.0)], descriptions=("SOV Energia", "SOV Portata", "Altro"))
    table, _ = load_daily(path)
    assert list(table.columns) == ["SOV Energia", "SOV Portata", "Altro"]


# --- Errori che si possono spiegare (R11) -----------------------------------------------------


def test_file_non_trovato(tmp_path):
    with pytest.raises(DataLoadError, match="non trovato"):
        load_daily(tmp_path / "non-esiste.xlsx")


def test_foglio_mancante(tmp_path):
    path = write_workbook(tmp_path / "d.xlsx", [(at(1), 1.0, 1.0)], sheet="altro")
    with pytest.raises(DataLoadError, match="manca il foglio «giornalieri»"):
        load_daily(path)


def test_testo_non_numerico_e_un_errore_non_un_mancante(tmp_path):
    path = write_workbook(tmp_path / "d.xlsx", [(at(1), "abc", 1.0), (at(2), 2.0, 2.0)])
    with pytest.raises(DataLoadError, match="Energia"):
        load_daily(path)


def test_descrizioni_ripetute(tmp_path):
    path = write_workbook(tmp_path / "d.xlsx", [(at(1), 1.0, 1.0)], descriptions=("Energia", "Energia"))
    with pytest.raises(DataLoadError, match="mancanti o ripetute"):
        load_daily(path)


def test_foglio_senza_dati(tmp_path):
    path = write_workbook(tmp_path / "d.xlsx", [])
    with pytest.raises(DataLoadError, match="struttura attesa"):
        load_daily(path)


def test_date_non_valide(tmp_path):
    path = write_workbook(tmp_path / "d.xlsx", [("non una data", 1.0, 1.0)])
    with pytest.raises(DataLoadError, match="date valide"):
        load_daily(path)


def test_il_file_dei_dati_non_viene_modificato(tmp_path):
    path = write_workbook(tmp_path / "d.xlsx", [(at(1), "Null", 1.0), (at(1, 3), 5.0, 5.0)])
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    load_daily(path)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
