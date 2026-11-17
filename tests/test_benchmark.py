"""Media, deviazione standard e limiti μ ± kσ (R6–R7; V4, V9, V10).

I valori attesi sono calcolati a mano, con serie scelte per rendere facile il conto:
- 8, 8, 10, 12, 12 → μ = 10, scarti −2, −2, 0, 2, 2, somma dei quadrati 16, varianza 16/4 = 4, σ = 2;
- 1, 2, 3, … → in una finestra di n giorni consecutivi la media è (primo + ultimo) ÷ 2 e la varianza
  campionaria è n(n+1)/12 (per n = 30: 77,5).
"""

import math
from datetime import date

import pandas as pd
import pytest

from benchmark import FixedBenchmark, MovingBenchmark, add_limits, compute_benchmark


def daily(values, start="2025-01-01") -> pd.Series:
    return pd.Series(values, index=pd.date_range(start, periods=len(values)), dtype="float64")


def counting(n: int) -> pd.Series:
    """1, 2, 3, … n: il valore del giorno numero i è i."""
    return daily(range(1, n + 1))


def day(n: int, start="2025-01-01") -> pd.Timestamp:
    return pd.Timestamp(start) + pd.Timedelta(days=n - 1)


# --- Limiti: V9 --------------------------------------------------------------------------------


def test_v9_limiti_con_k_3():
    series = daily([8, 8, 10, 12, 12])
    limits = add_limits(compute_benchmark(series, FixedBenchmark(date(2025, 1, 1), date(2025, 1, 5), 2)), 3)
    assert limits["mean"].iloc[0] == pytest.approx(10)
    assert limits["std"].iloc[0] == pytest.approx(2)
    assert limits["lower"].iloc[0] == pytest.approx(4)
    assert limits["upper"].iloc[0] == pytest.approx(16)


@pytest.mark.parametrize("k, lower, upper", [(1, 8, 12), (2, 6, 14), (2.5, 5, 15), (0.5, 9, 11)])
def test_limiti_seguono_k(k, lower, upper):
    series = daily([8, 8, 10, 12, 12])
    limits = add_limits(compute_benchmark(series, FixedBenchmark(date(2025, 1, 1), date(2025, 1, 5), 2)), k)
    assert (limits["lower"].iloc[0], limits["upper"].iloc[0]) == (pytest.approx(lower), pytest.approx(upper))


def test_add_limits_non_modifica_la_tabella_ricevuta():
    benchmark = compute_benchmark(daily([8, 8, 10, 12, 12]), FixedBenchmark(date(2025, 1, 1), date(2025, 1, 5), 2))
    add_limits(benchmark, 3)
    assert list(benchmark.columns) == ["mean", "std", "n_valid"]


@pytest.mark.parametrize("bad", [0, -1, math.nan, math.inf])
def test_k_non_valido_e_un_errore(bad):
    benchmark = compute_benchmark(daily([8, 8, 10, 12, 12]), FixedBenchmark(date(2025, 1, 1), date(2025, 1, 5), 2))
    with pytest.raises(ValueError, match="maggiore di zero"):
        add_limits(benchmark, bad)


# --- Benchmark fisso ----------------------------------------------------------------------------


def test_fisso_media_e_sigma_sono_uguali_per_tutti_i_giorni():
    series = daily([8, 8, 10, 12, 12, 50, 60])
    result = compute_benchmark(series, FixedBenchmark(date(2025, 1, 1), date(2025, 1, 5), 2))
    assert result["mean"].tolist() == pytest.approx([10] * 7)
    assert result["std"].tolist() == pytest.approx([2] * 7)
    assert result["n_valid"].tolist() == [5] * 7


def test_fisso_gli_estremi_del_periodo_sono_inclusi():
    series = daily([100, 8, 8, 10, 12, 12, 100])  # il 1° e il 7° sono fuori dal periodo 2–6
    result = compute_benchmark(series, FixedBenchmark(date(2025, 1, 2), date(2025, 1, 6), 2))
    assert result["mean"].iloc[0] == pytest.approx(10)
    assert result["n_valid"].iloc[0] == 5


def test_fisso_i_giorni_esclusi_non_contano_ne_come_zero_ne_nel_numero():
    series = daily([8, 8, math.nan, 10, 12, 12])
    result = compute_benchmark(series, FixedBenchmark(date(2025, 1, 1), date(2025, 1, 6), 2))
    assert result["n_valid"].iloc[0] == 5
    assert result["mean"].iloc[0] == pytest.approx(10)  # con uno 0 al posto del mancante sarebbe 8,33


def test_v4_giorni_validi_insufficienti_nessun_limite():
    series = daily([8, 10, 12] + [math.nan] * 40)  # 3 giorni validi in tutto il periodo
    limits = add_limits(compute_benchmark(series, FixedBenchmark(date(2025, 1, 1), date(2025, 2, 12), 30)), 3)
    assert limits["n_valid"].iloc[0] == 3  # il numero vero resta visibile
    assert limits[["mean", "std", "lower", "upper"]].isna().all().all()


def test_fisso_proprio_sulla_soglia_i_limiti_ci_sono():
    series = daily([8, 12] * 15)  # 30 giorni validi
    result = compute_benchmark(series, FixedBenchmark(date(2025, 1, 1), date(2025, 1, 30), 30))
    assert not math.isnan(result["mean"].iloc[0])
    result = compute_benchmark(series, FixedBenchmark(date(2025, 1, 1), date(2025, 1, 30), 31))
    assert math.isnan(result["mean"].iloc[0])


# --- Benchmark mobile ---------------------------------------------------------------------------


def test_mobile_finestra_di_30_giorni_calcolata_a_mano():
    series = counting(40)
    result = compute_benchmark(series, MovingBenchmark(30, 2))
    # Giorno 35: la finestra va dal giorno 5 al 34 (30 giorni, il 35 è escluso).
    assert result["n_valid"].loc[day(35)] == 30
    assert result["mean"].loc[day(35)] == pytest.approx((5 + 34) / 2)  # 19,5
    assert result["std"].loc[day(35)] == pytest.approx(math.sqrt(30 * 31 / 12))  # √77,5
    # Giorno 31: la finestra va dal giorno 1 al 30.
    assert result["mean"].loc[day(31)] == pytest.approx(15.5)


def test_mobile_primi_giorni_senza_storia():
    result = compute_benchmark(counting(40), MovingBenchmark(30, 2))
    assert result["n_valid"].loc[day(1)] == 0 and math.isnan(result["mean"].loc[day(1)])
    assert result["n_valid"].loc[day(2)] == 1 and math.isnan(result["mean"].loc[day(2)])  # ne servono 2
    assert result["n_valid"].loc[day(3)] == 2
    assert result["mean"].loc[day(3)] == pytest.approx(1.5)  # media di 1 e 2
    assert result["std"].loc[day(3)] == pytest.approx(math.sqrt(0.5))


def test_mobile_con_il_minimo_predefinito_servono_30_giorni_validi():
    result = compute_benchmark(counting(40), MovingBenchmark(30))  # min_valid_days = 30
    assert result["n_valid"].loc[day(20)] == 19 and math.isnan(result["mean"].loc[day(20)])
    assert result["n_valid"].loc[day(31)] == 30 and not math.isnan(result["mean"].loc[day(31)])


def test_mobile_i_giorni_esclusi_restano_fuori_dalla_finestra():
    series = counting(40)
    series[day(10)] = math.nan
    result = compute_benchmark(series, MovingBenchmark(30, 2))
    assert result["n_valid"].loc[day(35)] == 29  # giorni 5–34 senza il 10
    assert result["mean"].loc[day(35)] == pytest.approx((585 - 10) / 29)  # somma 5…34 = 585


def test_v10_mobile_cambiare_il_valore_del_giorno_d_non_cambia_i_suoi_limiti():
    series = counting(40)
    before = add_limits(compute_benchmark(series, MovingBenchmark(30, 2)), 3)
    changed = series.copy()
    changed[day(35)] = 999.0
    after = add_limits(compute_benchmark(changed, MovingBenchmark(30, 2)), 3)
    assert after.loc[day(35)].tolist() == pytest.approx(before.loc[day(35)].tolist())
    assert after.loc[day(36)]["mean"] != pytest.approx(before.loc[day(36)]["mean"])  # il giorno dopo sì
    assert after.loc[day(34)].tolist() == pytest.approx(before.loc[day(34)].tolist())  # il giorno prima no


def test_mobile_i_limiti_cambiano_nel_tempo_quelli_del_fisso_no():
    series = counting(60)
    moving = compute_benchmark(series, MovingBenchmark(30, 2))
    fixed = compute_benchmark(series, FixedBenchmark(date(2025, 1, 1), date(2025, 1, 30), 2))
    assert moving["mean"].loc[day(40)] != pytest.approx(moving["mean"].loc[day(50)])
    assert fixed["mean"].loc[day(40)] == fixed["mean"].loc[day(50)]


# --- Parametri non validi -------------------------------------------------------------------------


@pytest.mark.parametrize("window", [0, 1, 7, 45, 366])
def test_finestra_mobile_non_ammessa(window):
    with pytest.raises(ValueError, match="finestra mobile"):
        MovingBenchmark(window)


@pytest.mark.parametrize("window", [30, 90, 180, 365])
def test_finestre_mobili_ammesse(window):
    assert MovingBenchmark(window).window_days == window


@pytest.mark.parametrize("minimum", [1, 0, -5])
def test_servono_almeno_due_giorni_validi(minimum):
    with pytest.raises(ValueError, match="almeno 2"):
        FixedBenchmark(date(2025, 1, 1), date(2025, 1, 31), minimum)
    with pytest.raises(ValueError, match="almeno 2"):
        MovingBenchmark(30, minimum)


def test_periodo_fisso_con_inizio_dopo_la_fine():
    with pytest.raises(ValueError, match="prima della fine"):
        FixedBenchmark(date(2025, 2, 1), date(2025, 1, 1))


def test_la_serie_deve_avere_date_in_ordine_crescente():
    series = counting(5).iloc[::-1]
    with pytest.raises(ValueError, match="ordine crescente"):
        compute_benchmark(series, MovingBenchmark(30, 2))
    with pytest.raises(ValueError, match="ordine crescente"):
        compute_benchmark(pd.Series([1.0, 2.0, 3.0]), FixedBenchmark(date(2025, 1, 1), date(2025, 1, 3), 2))
