"""Indicatori da formule predefinite e classificazione dei giorni (R4–R5; V15)."""

import math

import pandas as pd
import pytest

from indicators import (
    DEFAULT_INDICATORS,
    L_PER_S_TO_M3_PER_DAY,
    DayStatus,
    Indicator,
    Input,
    classify_days,
    compute_indicator,
    valid_values,
)

V, M, S, O = DayStatus.VALID, DayStatus.MISSING, DayStatus.STOPPED, DayStatus.OUT_OF_RANGE


def table(**columns) -> pd.DataFrame:
    n = len(next(iter(columns.values())))
    return pd.DataFrame(columns, index=pd.date_range("2025-01-01", periods=n), dtype="float64")


def ratio(plausible_range=None, factor_b=1.0) -> Indicator:
    return Indicator("rapporto", "A/B", (Input("a"), Input("b", factor_b)), plausible_range)


# --- Formule: V15 ------------------------------------------------------------------------------


def test_v15_somma_diviso_c():
    indicator = Indicator("x", "(A+B)/C", (Input("a"), Input("b"), Input("c")))
    assert compute_indicator(table(a=[10], b=[20], c=[3]), indicator).iloc[0] == pytest.approx(10)


def test_rapporto_semplice():
    assert compute_indicator(table(a=[100, 9], b=[4, 3]), ratio()).tolist() == pytest.approx([25, 3])


def test_il_fattore_si_applica_all_ingresso_prima_della_formula():
    # 100 kWh con una portata di 10 l/s: 10 × 86,4 = 864 m³ al giorno → 100 ÷ 864 kWh/m³.
    value = compute_indicator(table(a=[100], b=[10]), ratio(factor_b=L_PER_S_TO_M3_PER_DAY)).iloc[0]
    assert value == pytest.approx(100 / 864)


def test_i_fattori_valgono_anche_nella_somma():
    indicator = Indicator("x", "(A+B)/C", (Input("a", 2), Input("b", 0.5), Input("c")))
    # (10 × 2 + 20 × 0,5) ÷ 3 = 30 ÷ 3
    assert compute_indicator(table(a=[10], b=[20], c=[3]), indicator).iloc[0] == pytest.approx(10)


def test_ingresso_mancante_da_risultato_mancante_non_zero():
    value = compute_indicator(table(a=[math.nan, 5.0], b=[2.0, math.nan]), ratio())
    assert value.isna().all()


def test_divisione_per_zero_e_mancante_non_infinito():
    value = compute_indicator(table(a=[5.0], b=[0.0]), ratio())
    assert value.isna().all() and not math.isinf(value.iloc[0])


def test_il_nome_della_serie_e_quello_dell_indicatore():
    assert compute_indicator(table(a=[1], b=[1]), Indicator("Il mio indicatore", "A/B", (Input("a"), Input("b")))).name == (
        "Il mio indicatore"
    )


# --- Classificazione dei giorni (R4) -------------------------------------------------------------


def test_classificazione_con_precedenza_mancante_fermo_fuori_scala_valido():
    # intervallo plausibile 0–5; il rapporto è a ÷ b
    data = table(
        a=[10, math.nan, 0, 10, -5, math.nan, 100, 10, 10],
        b=[10, 10, 10, 0, 10, 0, 10, 10, 10],
    )
    status = classify_days(data, ratio((0, 5)))
    assert status.tolist() == [
        V,  # 10 ÷ 10 = 1
        M,  # A manca
        S,  # A = 0: l'impianto non ha lavorato
        S,  # B = 0: nessuna acqua trattata
        S,  # A < 0
        M,  # manca A e B è 0: «mancante» vince su «fermo»
        O,  # 100 ÷ 10 = 10, oltre il massimo
        V,
        V,
    ]


def test_intervallo_plausibile_con_estremi_inclusi():
    data = table(a=[0.5, 5.0, 0.4999, 5.0001], b=[1.0, 1.0, 1.0, 1.0])
    assert classify_days(data, ratio((0.5, 5.0))).tolist() == [V, V, O, O]


def test_senza_intervallo_plausibile_nessun_giorno_e_fuori_scala():
    assert classify_days(table(a=[1e9], b=[1.0]), ratio(None)).tolist() == [V]


def test_somma_diviso_c_una_pompa_ferma_non_e_un_giorno_di_fermo():
    indicator = Indicator("x", "(A+B)/C", (Input("a"), Input("b"), Input("c")), (0, 10))
    data = table(a=[0, 0, 4, -5, 10], b=[20, 0, 0, 10, 20], c=[3, 3, 0, 1, math.nan])
    assert classify_days(data, indicator).tolist() == [
        V,  # A = 0 ma B = 20: (0 + 20) ÷ 3, normale
        S,  # A + B = 0: tutte le pompe ferme
        S,  # C = 0: nessuna acqua trattata
        V,  # A + B = 5 > 0 anche se A è negativo: conta solo la somma
        M,  # manca C
    ]


def test_valid_values_tiene_solo_i_giorni_validi():
    data = table(a=[10, math.nan, 0, 100, 4], b=[10, 10, 10, 10, 2])
    indicator = ratio((0, 5))
    values = valid_values(compute_indicator(data, indicator), classify_days(data, indicator))
    assert values.iloc[[0, 4]].tolist() == pytest.approx([1.0, 2.0])
    assert values.iloc[[1, 2, 3]].isna().all()


# --- Definizione dell'indicatore -------------------------------------------------------------------


@pytest.mark.parametrize("factor", [0, -1, math.nan, math.inf])
def test_fattore_non_valido(factor):
    with pytest.raises(ValueError, match="maggiore di zero"):
        Input("a", factor)


def test_formula_sconosciuta():
    with pytest.raises(ValueError, match="Formula sconosciuta"):
        Indicator("x", "A*B", (Input("a"), Input("b")))


@pytest.mark.parametrize("formula, count", [("A/B", 3), ("A/B", 1), ("(A+B)/C", 2)])
def test_numero_di_ingressi_sbagliato(formula, count):
    with pytest.raises(ValueError, match="richiede"):
        Indicator("x", formula, tuple(Input(c) for c in "abc"[:count]))


@pytest.mark.parametrize("bad", [(5, 1), (1, 1), (0, math.inf), (math.nan, 1)])
def test_intervallo_plausibile_non_valido(bad):
    with pytest.raises(ValueError, match="intervallo plausibile"):
        Indicator("x", "A/B", (Input("a"), Input("b")), bad)


def test_utenze_preconfigurate():
    assert [i.utility for i in DEFAULT_INDICATORS] == ["SOV-SA01 P2B", "SOV-SA01 P3A", "SFI-SA02"]
    assert {i.parameter for i in DEFAULT_INDICATORS} == {"Energia specifica [kWh/m³]"}
    assert [i.plausible_range for i in DEFAULT_INDICATORS] == [(0, 5), (0, 5), (0, 10)]
    p2b, p3a, sfi = DEFAULT_INDICATORS
    assert [(i.column, i.factor) for i in p2b.inputs] == [
        ("SOV-SA01 Energia P2B", 1.0),
        ("SOV-SA01 Portata media P2B", 86.4),
    ]
    assert p3a.formula == "A/B" and sfi.formula == "(A+B)/C"
    assert sfi.inputs[2].factor == 86.4 and sfi.inputs[0].factor == sfi.inputs[1].factor == 1.0
