"""Verifiche sul file dei dati vero (V1–V6 di SPECIFICA.md), con i valori attesi scritti nella specifica.

Gli eventi con benchmark mobile a 365 giorni (k = 3, N = 3) sono stati calcolati a parte, durante la
lettura dei dati, e verificati nell'app: qui restano come punti di riferimento.
"""

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from alarms import Direction, find_events
from benchmark import FixedBenchmark, MovingBenchmark, add_limits, compute_benchmark
from indicators import DEFAULT_INDICATORS, DayStatus, Indicator, Input, L_PER_S_TO_M3_PER_DAY, classify_days, compute_indicator, valid_values
from loader import load_daily

DATA_FILE = Path(__file__).parent.parent / "dati" / "set-dati.xlsx"
P2B, P3A, SFI = DEFAULT_INDICATORS
D = pd.Timestamp


@pytest.fixture(scope="module")
def data():
    table, report = load_daily(DATA_FILE)
    return table, report


@pytest.fixture(scope="module")
def table(data):
    return data[0]


def valid_series(table, indicator):
    return valid_values(compute_indicator(table, indicator), classify_days(table, indicator))


def events(table, indicator, spec, k=3.0, persistence=3):
    series = valid_series(table, indicator)
    return find_events(series, add_limits(compute_benchmark(series, spec), k), persistence, indicator.name)


def counts(table, indicator) -> dict[DayStatus, int]:
    return classify_days(table, indicator).value_counts().to_dict()


# --- V1: caricamento e pulizia -------------------------------------------------------------------


def test_v1_914_giorni_dal_16_03_2024_al_15_09_2026(data):
    table, report = data
    assert len(table) == report.days_kept == 914
    assert table.index.min() == D("2024-03-16") and table.index.max() == D("2026-09-15")
    assert table.index.is_unique and table.index.is_monotonic_increasing
    assert D("2026-09-16") not in table.index


def test_v1_le_colonne_sono_numeriche_e_ci_sono_quelle_attese(table):
    assert all(str(dtype) == "float64" for dtype in table.dtypes)
    for column in ("SOV-SA01 Energia P2B", "SOV-SA01 Portata media P3A", "SFI-SA02 Energia P1", "SFI-SA02 Portata media"):
        assert column in table.columns


def test_la_pulizia_non_inventa_giorni_ne_zeri(data):
    table, report = data
    assert report.rows_read == report.days_kept + report.rows_other_time + report.rows_duplicate
    assert report.missing_cells == int(table.isna().sum().sum())


# --- V2, V3: classificazione dei giorni ------------------------------------------------------------


def test_v2_p2b_907_validi_7_fermi_nessun_mancante(table):
    c = counts(table, P2B)
    assert c == {DayStatus.VALID: 907, DayStatus.STOPPED: 7}
    median = valid_series(table, P2B).median()
    assert 1.09 <= median <= 1.12
    assert median == pytest.approx(1.105, abs=5e-4)


def test_v3_p3a_31_fermi_2_fuori_scala_881_validi(table):
    c = counts(table, P3A)
    assert c[DayStatus.STOPPED] == 31
    assert c[DayStatus.OUT_OF_RANGE] == 2
    assert c[DayStatus.VALID] == 881
    out_of_range = classify_days(table, P3A)[lambda s: s == DayStatus.OUT_OF_RANGE]
    assert list(out_of_range.index) == [D("2024-07-11"), D("2024-07-19")]
    assert valid_series(table, P3A).max() <= 1.5


def test_p3a_senza_intervallo_plausibile_i_due_valori_assurdi_sarebbero_validi(table):
    # Il motivo dell'intervallo plausibile (Q3): senza, le due letture da milioni di kWh (11 e 19/07/2024)
    # darebbero un indicatore cento volte oltre il massimo plausibile (5) e inquinerebbero media e limiti.
    no_range = Indicator(P3A.name, P3A.formula, P3A.inputs, None)
    assert valid_series(table, no_range).max() > 100


# --- V4: benchmark insufficiente ---------------------------------------------------------------------


def test_v4_p1b_ha_3_giorni_validi_e_nessun_limite(table):
    p1b = Indicator("P1B", "A/B", (Input("SOV-SA01 Energia P1B"), Input("SOV-SA01 Portata media P1B", L_PER_S_TO_M3_PER_DAY)), (0, 5))
    series = valid_series(table, p1b)
    assert series.notna().sum() == 3
    for spec in (FixedBenchmark(date(2024, 3, 16), date(2026, 9, 15)), MovingBenchmark(365)):
        limits = add_limits(compute_benchmark(series, spec), 3)
        assert limits["lower"].isna().all() and limits["upper"].isna().all()
        assert limits["n_valid"].max() == 3


# --- V5: fisso contro mobile -----------------------------------------------------------------------------


def test_v5_p2b_limiti_fissi_costanti_limiti_mobili_che_cambiano(table):
    series = valid_series(table, P2B)
    fixed = compute_benchmark(series, FixedBenchmark(date(2025, 1, 1), date(2025, 12, 31)))
    moving = compute_benchmark(series, MovingBenchmark(365))
    assert fixed["mean"].nunique() == 1 and fixed["std"].nunique() == 1
    assert fixed["mean"].iloc[0] == pytest.approx(1.1003, abs=5e-5)
    assert fixed["std"].iloc[0] == pytest.approx(0.0266, abs=5e-5)
    assert moving["mean"].dropna().nunique() > 100
    assert moving["mean"].iloc[:30].isna().all()  # nei primi 30 giorni non ci sono ancora 30 giorni validi di storia


# --- V6: più persistenza, meno eventi -------------------------------------------------------------------------


@pytest.mark.parametrize("indicator", DEFAULT_INDICATORS, ids=[i.utility for i in DEFAULT_INDICATORS])
@pytest.mark.parametrize("spec", [MovingBenchmark(365), FixedBenchmark(date(2025, 1, 1), date(2025, 12, 31))], ids=["mobile", "fisso 2025"])
def test_v6_gli_eventi_a_n_3_sono_meno_di_quelli_a_n_1_e_contenuti_in_essi(table, indicator, spec):
    n1, n3 = events(table, indicator, spec, persistence=1), events(table, indicator, spec, persistence=3)
    assert len(n3) <= len(n1)
    for event in n3:
        assert any(o.first_day <= event.first_day and event.last_day <= o.last_day for o in n1)


# --- Eventi di riferimento (benchmark mobile 365, k = 3, N = 3) ---------------------------------------------------


def check_event(event, first, trigger, last, duration, direction, value, mean, std, deviation):
    assert (event.first_day, event.trigger_day, event.last_day) == (D(first), D(trigger), D(last))
    assert event.duration_days == duration and event.direction == direction
    assert event.value == pytest.approx(value, abs=5e-5)
    assert event.mean == pytest.approx(mean, abs=5e-5)
    assert event.std == pytest.approx(std, abs=5e-5)
    assert event.deviation_pct == pytest.approx(deviation, abs=5e-3)


def test_evento_p2b_giugno_2024(table):
    (event,) = events(table, P2B, MovingBenchmark(365))
    check_event(event, "2024-06-06", "2024-06-08", "2024-06-12", 7, Direction.BELOW, 0.7127, 1.1094, 0.0856, -35.75)


def test_evento_p3a_luglio_2025(table):
    (event,) = events(table, P3A, MovingBenchmark(365))
    assert (event.first_day, event.last_day, event.duration_days) == (D("2025-07-21"), D("2025-07-30"), 10)
    assert event.direction == Direction.ABOVE
    assert (event.value, event.mean, event.std) == pytest.approx((1.4200, 1.1472, 0.0448), abs=5e-5)
    assert event.deviation_pct == pytest.approx(23.78, abs=5e-3)


def test_evento_p3a_con_benchmark_fisso_2025_ha_scostamento_diverso(table):
    # Stesso evento, benchmark diverso: lo scostamento è +21,46 % (fisso) invece di +23,78 % (mobile).
    fixed_events = events(table, P3A, FixedBenchmark(date(2025, 1, 1), date(2025, 12, 31)))
    july = [e for e in fixed_events if e.first_day == D("2025-07-21")]
    assert len(july) == 1
    assert july[0].deviation_pct == pytest.approx(21.46, abs=5e-3)


def test_eventi_sfi_sa02_mobile_sono_due_uno_sopra_e_uno_sotto(table):
    first, second = events(table, SFI, MovingBenchmark(365))
    check_event(first, "2024-07-04", "2024-07-06", "2024-07-09", 6, Direction.ABOVE, 5.3029, 3.9823, 0.4016, 33.16)
    check_event(second, "2025-04-09", "2025-04-11", "2025-04-22", 14, Direction.BELOW, 1.4001, 4.4770, 0.6828, -68.73)
