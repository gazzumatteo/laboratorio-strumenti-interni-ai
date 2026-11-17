"""Giorni anomali ed eventi con persistenza (R8–R10; V6, V11–V14)."""

import math

import pandas as pd
import pytest
from known_cases import (
    ALARM_CASES,
    BENCHMARK_DAYS,
    EXPECTED_LOWER,
    EXPECTED_MEAN,
    EXPECTED_STD,
    EXPECTED_UPPER,
    EXPECTED_V11_EVENT,
    SPIKE,
    build_series,
    day,
)

from alarms import Direction, alarm_days, find_anomalous_days, find_events
from benchmark import FixedBenchmark, add_limits, compute_benchmark


def fixed_limits(series: pd.Series, k: float = 3.0) -> pd.DataFrame:
    first, last = BENCHMARK_DAYS
    return add_limits(compute_benchmark(series, FixedBenchmark(day(first).date(), day(last).date(), 30)), k)


def events_of(series: pd.Series, persistence: int, k: float = 3.0):
    return find_events(series, fixed_limits(series, k), persistence, "prova")


# --- I limiti dei dati costruiti sono quelli calcolati a mano ------------------------------------


def test_limiti_della_serie_costruita():
    limits = fixed_limits(build_series())
    assert limits["mean"].iloc[0] == pytest.approx(EXPECTED_MEAN)
    assert limits["std"].iloc[0] == pytest.approx(EXPECTED_STD)
    assert limits["lower"].iloc[0] == pytest.approx(EXPECTED_LOWER)
    assert limits["upper"].iloc[0] == pytest.approx(EXPECTED_UPPER)
    assert limits["n_valid"].iloc[0] == 30


# --- Giorni anomali (R8) --------------------------------------------------------------------


def test_giorni_anomali_sono_solo_quelli_a_200():
    series = build_series(spike_days=(40, 41, 42))
    anomalies = find_anomalous_days(series, fixed_limits(series))
    assert list(anomalies.dropna().index) == [day(40), day(41), day(42)]
    assert set(anomalies.dropna()) == {Direction.ABOVE}


def test_senza_anomalie_nessun_giorno_anomalo_e_nessun_evento():
    series = build_series()
    assert find_anomalous_days(series, fixed_limits(series)).notna().sum() == 0
    assert events_of(series, 1) == []


def test_valore_sotto_i_limiti_ha_direzione_sotto():
    series = build_series(spike_days=(40, 41, 42), spike_value=10.0)
    anomalies = find_anomalous_days(series, fixed_limits(series))
    assert set(anomalies.dropna()) == {Direction.BELOW}
    assert events_of(series, 3)[0].direction == Direction.BELOW


def test_valore_esattamente_sul_limite_non_e_anomalo():
    # Limiti scritti a mano: il confronto è «strettamente fuori».
    index = pd.date_range("2025-01-01", periods=4)
    limits = pd.DataFrame({"mean": 10.0, "std": 2.0, "lower": 4.0, "upper": 16.0, "n_valid": 30}, index=index)
    values = pd.Series([16.0, 4.0, 16.0001, 3.9999], index=index)
    assert list(find_anomalous_days(values, limits)) == [None, None, Direction.ABOVE, Direction.BELOW]


def test_giorno_escluso_o_senza_limiti_non_e_mai_anomalo():
    index = pd.date_range("2025-01-01", periods=3)
    limits = pd.DataFrame(
        {"mean": [10.0, 10.0, math.nan], "std": 2.0, "lower": [4.0, 4.0, math.nan], "upper": [16.0, 16.0, math.nan]},
        index=index,
    )
    values = pd.Series([100.0, math.nan, 100.0], index=index)  # il 1° è fuori; il 2° è escluso; il 3° non ha limiti
    assert list(find_anomalous_days(values, limits)) == [Direction.ABOVE, None, None]


def test_serie_e_limiti_su_giorni_diversi_sono_un_errore():
    series = build_series()
    with pytest.raises(ValueError, match="stessi giorni"):
        find_anomalous_days(series, fixed_limits(series).iloc[:-1])


# --- Eventi con persistenza: V11, V12, V13 e varianti --------------------------------------------


@pytest.mark.parametrize("case", ALARM_CASES, ids=[c.name for c in ALARM_CASES])
def test_eventi_attesi(case):
    series = build_series(case.spike_days, case.missing_days)
    found = events_of(series, case.persistence)
    actual = tuple((e.first_day, e.trigger_day, e.last_day, e.duration_days) for e in found)
    expected = tuple((day(a), day(b), day(c), d) for a, b, c, d in case.expected)
    assert actual == expected


def test_v11_valori_dell_evento():
    (event,) = events_of(build_series(spike_days=(40, 41, 42)), 3)
    assert event.direction == EXPECTED_V11_EVENT["direction"]
    assert event.value == EXPECTED_V11_EVENT["value"] == SPIKE
    assert event.mean == pytest.approx(EXPECTED_V11_EVENT["mean"])
    assert event.std == pytest.approx(EXPECTED_V11_EVENT["std"])


def test_v14_scostamento_percentuale():
    (event,) = events_of(build_series(spike_days=(40, 41, 42)), 3)
    assert event.deviation_pct == pytest.approx(EXPECTED_V11_EVENT["deviation_pct"])  # +100


def test_scostamento_negativo_con_valore_sotto_la_media():
    (event,) = events_of(build_series(spike_days=(40, 41, 42), spike_value=50.0), 3)
    assert event.deviation_pct == pytest.approx(-50.0)


def test_scostamento_non_calcolabile_se_la_media_e_zero():
    index = pd.date_range("2025-01-01", periods=3)
    limits = pd.DataFrame({"mean": 0.0, "std": 1.0, "lower": -3.0, "upper": 3.0, "n_valid": 30}, index=index)
    (event,) = find_events(pd.Series([9.0, 9.0, 9.0], index=index), limits, 3, "prova")
    assert math.isnan(event.deviation_pct)


def test_l_evento_e_uno_solo_anche_se_la_sequenza_continua():
    series = build_series(spike_days=tuple(range(40, 51)))  # 11 giorni consecutivi
    (event,) = events_of(series, 3)
    assert (event.first_day, event.trigger_day, event.last_day, event.duration_days) == (day(40), day(42), day(50), 11)


def test_cambio_di_direzione_interrompe_la_sequenza():
    # Q11: sopra e poi sotto, senza giorni normali in mezzo, sono due sequenze.
    series = build_series(spike_days=(40, 41))
    series[day(42)] = 10.0
    series[day(43)] = 10.0
    assert events_of(series, 3) == []  # nessuna delle due arriva a 3
    two = events_of(series, 2)
    assert [(e.direction, e.first_day, e.last_day) for e in two] == [
        (Direction.ABOVE, day(40), day(41)),
        (Direction.BELOW, day(42), day(43)),
    ]


def test_giorno_assente_dal_calendario_interrompe_la_sequenza():
    # Non basta che i giorni siano anomali e vicini nell'elenco: devono essere giorni di calendario consecutivi.
    series = build_series(spike_days=(40, 41, 42, 43)).drop(day(42))
    assert events_of(series, 3) == []
    assert len(events_of(series, 2)) == 1  # 40–41 sì; 43 da solo no


def test_benchmark_insufficiente_non_da_allarmi():
    series = build_series(spike_days=(40, 41, 42))
    first, last = BENCHMARK_DAYS
    limits = add_limits(compute_benchmark(series, FixedBenchmark(day(first).date(), day(last).date(), 31)), 3)
    assert limits["lower"].isna().all()  # solo 30 giorni validi, ne servono 31
    assert find_events(series, limits, 1, "prova") == []


@pytest.mark.parametrize("bad", [0, -1, 2.5, True, "3"])
def test_persistenza_non_valida_e_un_errore(bad):
    series = build_series()
    with pytest.raises(ValueError, match="intero maggiore di zero"):
        find_events(series, fixed_limits(series), bad, "prova")


def test_il_nome_dell_indicatore_finisce_nell_evento():
    series = build_series(spike_days=(40, 41, 42))
    (event,) = find_events(series, fixed_limits(series), 3, "Energia specifica di prova")
    assert event.indicator == "Energia specifica di prova"


def test_giorni_in_allarme_vanno_dal_primo_all_ultimo_giorno_dell_evento():
    events = events_of(build_series(spike_days=(40, 41, 42, 50, 51, 52, 53)), 3)
    assert alarm_days(events) == {day(n) for n in (40, 41, 42, 50, 51, 52, 53)}
    assert alarm_days([]) == set()


# --- Più persistenza, meno eventi (V6) ---------------------------------------------------------


def test_v6_con_n_3_gli_eventi_sono_meno_e_contenuti_in_quelli_di_n_1():
    # Sequenze anomale lunghe 1, 2, 3 e 5 giorni, separate da giorni normali.
    series = build_series(spike_days=(35, 38, 39, 42, 43, 44, 48, 49, 50, 51, 52))
    n1, n3 = events_of(series, 1), events_of(series, 3)
    assert [e.duration_days for e in n1] == [1, 2, 3, 5]
    assert [e.duration_days for e in n3] == [3, 5]
    for event in n3:
        assert any(o.first_day <= event.first_day and event.last_day <= o.last_day for o in n1)
