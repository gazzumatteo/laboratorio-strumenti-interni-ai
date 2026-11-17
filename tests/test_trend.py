"""Pendenza del trend (R15; V23).

Risultati attesi calcolati a mano:
- una serie che cresce di 1 al giorno ha pendenza 1 (e −0,5 al giorno dà −0,5; una costante dà 0);
- valori 1, 3, 2, 5 nei giorni 0, 1, 2, 3: x̄ = 1,5, ȳ = 2,75; Σ(x−x̄)(y−ȳ) = 2,625 − 0,125 − 0,375 + 3,375 = 5,5;
  Σ(x−x̄)² = 5; pendenza = 5,5 ÷ 5 = 1,1.
"""

import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from indicators import DEFAULT_INDICATORS, classify_days, compute_indicator, valid_values
from loader import load_daily
from trend import DEFAULT_TREND_DAYS, MIN_TREND_POINTS, TREND_PERIODS, compute_trend

D = pd.Timestamp


def daily(values, start="2025-01-01") -> pd.Series:
    return pd.Series(values, index=pd.date_range(start, periods=len(values)), dtype="float64")


def day(n: int) -> pd.Timestamp:
    """Il giorno numero n: il giorno 1 è il 1 gennaio 2025."""
    return D("2025-01-01") + pd.Timedelta(days=n - 1)


# --- Serie di cui si conosce la pendenza (V23) -----------------------------------------------------


def test_v23_serie_che_cresce_di_1_al_giorno_ha_pendenza_1():
    trend = compute_trend(daily(range(30)), 30)
    assert trend.slope_per_day == pytest.approx(1.0)
    assert trend.n_valid == 30


@pytest.mark.parametrize("step", [-0.5, 0.0, 0.25, 2.0, 1000.0])
def test_la_pendenza_e_il_passo_giornaliero(step):
    series = daily([7 + step * i for i in range(40)])
    assert compute_trend(series, 30).slope_per_day == pytest.approx(step, abs=1e-9)


def test_il_livello_della_serie_non_cambia_la_pendenza():
    assert compute_trend(daily([100 + 2 * i for i in range(30)]), 30).slope_per_day == pytest.approx(2.0)
    assert compute_trend(daily([1e6 + 2 * i for i in range(30)]), 30).slope_per_day == pytest.approx(2.0)


def test_caso_numerico_calcolato_a_mano():
    assert compute_trend(daily([1, 3, 2, 5]), 4, min_points=2).slope_per_day == pytest.approx(1.1)


def test_serie_costante_pendenza_zero():
    assert compute_trend(daily([5.0] * 30), 30).slope_per_day == pytest.approx(0.0, abs=1e-12)


# --- Il periodo ------------------------------------------------------------------------------------------


def test_conta_solo_gli_ultimi_giorni_del_periodo():
    # 60 giorni: per i primi 30 sale di 1 al giorno, per gli ultimi 30 resta fermo a 100.
    series = daily([float(i) for i in range(30)] + [100.0] * 30)
    assert compute_trend(series, 30).slope_per_day == pytest.approx(0.0, abs=1e-12)
    assert compute_trend(series, 60).slope_per_day > 0.5


def test_il_periodo_finisce_con_l_ultimo_giorno_e_include_gli_estremi():
    series = daily([float(n) for n in range(1, 101)])  # il valore del giorno n è n
    trend = compute_trend(series, 10)
    assert (trend.period_start, trend.period_end) == (day(91), day(100))
    assert trend.n_valid == 10 and trend.slope_per_day == pytest.approx(1.0)


def test_periodo_piu_lungo_della_serie_usa_tutta_la_serie():
    trend = compute_trend(daily([float(i) for i in range(20)]), 365)
    assert trend.n_valid == 20 and trend.slope_per_day == pytest.approx(1.0)


# --- Giorni esclusi o assenti ---------------------------------------------------------------------------------


def test_i_giorni_esclusi_non_sono_punti_ne_valgono_zero():
    values = [5.0] * 30
    for n in (3, 4, 10, 11, 12, 20):
        values[n] = math.nan
    trend = compute_trend(daily(values), 30)
    assert trend.n_valid == 24
    assert trend.slope_per_day == pytest.approx(0.0, abs=1e-12)  # con degli zeri al posto dei NaN non sarebbe 0


def test_giorni_esclusi_non_spostano_la_pendenza():
    values = [float(i) for i in range(30)]
    for n in (5, 6, 7, 20):
        values[n] = math.nan
    assert compute_trend(daily(values), 30).slope_per_day == pytest.approx(1.0)


def test_giorni_assenti_dal_calendario_non_spostano_la_pendenza():
    # Il tempo si conta sul calendario, non sulla posizione: togliere delle righe non cambia la retta.
    series = daily([float(i) for i in range(30)]).drop(pd.date_range("2025-01-06", "2025-01-10"))
    assert len(series) == 25
    assert compute_trend(series, 30).slope_per_day == pytest.approx(1.0)


# --- Soglia dei punti -----------------------------------------------------------------------------------------------


def test_sotto_la_soglia_dei_punti_la_pendenza_non_c_e():
    assert MIN_TREND_POINTS == 10
    nine = daily([float(i) for i in range(9)] + [math.nan] * 21)
    assert compute_trend(nine, 30) is None
    ten = daily([float(i) for i in range(10)] + [math.nan] * 20)
    assert compute_trend(ten, 30) is not None


def test_con_un_punto_solo_non_esiste_una_retta_anche_chiedendo_un_minimo_di_1():
    assert compute_trend(daily([1.0] + [math.nan] * 29), 30, min_points=1) is None


def test_serie_vuota_o_tutta_esclusa():
    assert compute_trend(daily([]), 30) is None
    assert compute_trend(daily([math.nan] * 30), 30) is None


# --- Parametri non validi --------------------------------------------------------------------------------------------


@pytest.mark.parametrize("bad", [1, 0, -30, 2.5, True, "30"])
def test_periodo_non_valido(bad):
    with pytest.raises(ValueError, match="almeno 2 giorni"):
        compute_trend(daily(range(30)), bad)


def test_la_serie_deve_avere_date_in_ordine_crescente():
    with pytest.raises(ValueError, match="ordine crescente"):
        compute_trend(daily(range(30)).iloc[::-1], 30)
    with pytest.raises(ValueError, match="ordine crescente"):
        compute_trend(pd.Series([1.0, 2.0, 3.0]), 30)


def test_periodi_ammessi_e_predefinito():
    assert TREND_PERIODS == (30, 90, 180, 365) and DEFAULT_TREND_DAYS in TREND_PERIODS


# --- Sui dati veri: confronto con un calcolo indipendente (numpy.polyfit) ------------------------------------------------


@pytest.fixture(scope="module")
def real_table():
    return load_daily(Path(__file__).parent.parent / "dati" / "set-dati.xlsx")[0]


@pytest.mark.parametrize("indicator", DEFAULT_INDICATORS, ids=[i.utility for i in DEFAULT_INDICATORS])
@pytest.mark.parametrize("days", TREND_PERIODS)
def test_dati_veri_stessa_pendenza_di_polyfit(real_table, indicator, days):
    series = valid_values(compute_indicator(real_table, indicator), classify_days(real_table, indicator))
    window = series[series.index > series.index.max() - pd.Timedelta(days=days)].dropna()
    x = (window.index - window.index[0]).days.to_numpy(float)
    trend = compute_trend(series, days)
    if len(window) < MIN_TREND_POINTS:  # succede a P3A negli ultimi 30 giorni: 9 giorni validi, ne servono 10
        assert trend is None
        return
    expected = np.polyfit(x, window.to_numpy(), 1)[0]
    assert trend.slope_per_day == pytest.approx(expected, rel=1e-9, abs=1e-12)
    assert trend.n_valid == len(window)


def test_dati_veri_p3a_ultimi_30_giorni_hanno_solo_9_giorni_validi_quindi_nessuna_pendenza(real_table):
    p3a = DEFAULT_INDICATORS[1]
    series = valid_values(compute_indicator(real_table, p3a), classify_days(real_table, p3a))
    assert series[series.index > series.index.max() - pd.Timedelta(days=30)].notna().sum() == 9
    assert compute_trend(series, 30) is None


def test_dati_veri_valori_di_riferimento_a_90_giorni(real_table):
    # Calcolati a parte con numpy.polyfit prima di scrivere il modulo (kWh/m³ al giorno).
    p2b, _, sfi = DEFAULT_INDICATORS
    p2b_series = valid_values(compute_indicator(real_table, p2b), classify_days(real_table, p2b))
    sfi_series = valid_values(compute_indicator(real_table, sfi), classify_days(real_table, sfi))
    trend = compute_trend(p2b_series, 90)
    assert (trend.slope_per_day, trend.n_valid) == (pytest.approx(-0.000616, abs=5e-7), 83)  # scende lentamente
    assert (trend.period_start, trend.period_end) == (D("2026-06-18"), D("2026-09-15"))
    assert compute_trend(sfi_series, 90).slope_per_day == pytest.approx(0.001586, abs=5e-7)  # sale lentamente
