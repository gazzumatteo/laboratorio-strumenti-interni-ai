"""Configurazione salvata (R14): lettura, scrittura e voci rovinate."""

import json
from datetime import date

import pytest

from benchmark import FixedBenchmark, MovingBenchmark
from indicators import Input
from settings import IndicatorSettings, load_settings, save_indicator_settings

MOVING = IndicatorSettings(
    "A/B", (Input("Energia"), Input("Portata", 86.4)), (0.0, 5.0), MovingBenchmark(90, 20), 2.5, 4, ("a@x.it", "b@y.it")
)
FIXED = IndicatorSettings(
    "(A+B)/C",
    (Input("E1"), Input("E2"), Input("Q", 86.4)),
    (0.0, 10.0),
    FixedBenchmark(date(2025, 1, 1), date(2025, 12, 31), 30),
    3.0,
    3,
)


@pytest.fixture
def path(tmp_path):
    return tmp_path / "configurazione.json"


def entry(**changes) -> dict:
    """Una voce valida (la stessa di FIXED, in JSON) con qualche campo cambiato o tolto (valore `...` = togli)."""
    data = {
        "formula": "(A+B)/C",
        "inputs": [{"column": "E1", "factor": 1.0}, {"column": "E2", "factor": 1.0}, {"column": "Q", "factor": 86.4}],
        "plausible_range": {"min": 0.0, "max": 10.0},
        "benchmark": {"type": "fixed", "start": "2025-01-01", "end": "2025-12-31", "min_valid_days": 30},
        "k": 3.0,
        "persistence_days": 3,
        "recipients": [],
    }
    for key, value in changes.items():
        if value is ...:
            data.pop(key)
        else:
            data[key] = value
    return data


def write(path, **indicators):
    path.write_text(json.dumps({"version": 1, "indicators": indicators}), encoding="utf-8")


def test_file_assente_non_e_un_errore(path):
    loaded = load_settings(path)
    assert loaded.indicators == {} and loaded.warnings == ()


def test_salvare_e_rileggere_da_le_stesse_scelte(path):
    save_indicator_settings(path, "Utenza è μ [kWh/m³]", MOVING)
    save_indicator_settings(path, "Altra", FIXED)
    loaded = load_settings(path)
    assert loaded.indicators == {"Utenza è μ [kWh/m³]": MOVING, "Altra": FIXED}
    assert loaded.warnings == ()


def test_il_file_si_legge_con_un_editor_di_testo(path):
    save_indicator_settings(path, "Utenza è μ", MOVING)
    text = path.read_text(encoding="utf-8")
    assert "\n  " in text  # rientri
    assert "Utenza è μ" in text and "\\u" not in text  # niente caratteri trasformati in codici
    assert json.loads(text)["indicators"]["Utenza è μ"]["k"] == 2.5


def test_salvando_una_voce_le_altre_restano_come_erano(path):
    write(path, Altra={**entry(), "nota": "scritta a mano"}, Rotta={"formula": 7})
    save_indicator_settings(path, "Nuova", MOVING)
    saved = json.loads(path.read_text(encoding="utf-8"))["indicators"]
    assert saved["Altra"]["nota"] == "scritta a mano" and saved["Rotta"] == {"formula": 7}
    assert set(saved) == {"Altra", "Rotta", "Nuova"}


def test_salvare_una_voce_esistente_la_sostituisce(path):
    save_indicator_settings(path, "U", MOVING)
    save_indicator_settings(path, "U", IndicatorSettings("A/B", MOVING.inputs, MOVING.plausible_range, MOVING.benchmark, 5.0, 4, ()))
    loaded = load_settings(path)
    assert loaded.indicators["U"].k == 5.0 and loaded.indicators["U"].recipients == ()


def test_nessun_file_temporaneo_resta_dopo_il_salvataggio(path):
    save_indicator_settings(path, "U", MOVING)
    assert [p.name for p in path.parent.iterdir()] == ["configurazione.json"]


def test_cartella_inesistente_da_oserror(tmp_path):
    with pytest.raises(OSError):
        save_indicator_settings(tmp_path / "manca" / "c.json", "U", MOVING)


@pytest.mark.parametrize(
    "bad",
    [
        entry(formula="A*B"),
        entry(inputs=entry()["inputs"][:2]),
        entry(inputs=[{"column": "E1", "factor": 0}, {"column": "E2", "factor": 1}, {"column": "Q", "factor": 1}]),
        entry(inputs=[{"column": "E1", "factor": "1"}, {"column": "E2", "factor": 1}, {"column": "Q", "factor": 1}]),
        entry(plausible_range={"min": 5, "max": 1}),
        entry(k=-1),
        entry(k=0),
        entry(k="3"),
        entry(persistence_days=0),
        entry(persistence_days=2.5),
        entry(persistence_days=True),
        entry(benchmark={"type": "boh"}),
        entry(benchmark={"type": "moving", "window_days": 45}),
        entry(benchmark={"type": "fixed", "start": "01/01/2025", "end": "2025-12-31"}),
        entry(benchmark={"type": "fixed", "start": "2025-12-31", "end": "2025-01-01"}),
        entry(benchmark={"type": "moving", "window_days": 90, "min_valid_days": 1}),
        entry(recipients="a@x.it"),
        entry(recipients=["a@x.it", 3]),
        entry(k=...),
        entry(plausible_range=...),
        [1, 2],
    ],
    ids=lambda v: str(v)[:60],
)
def test_voce_non_valida_e_scartata_con_un_avviso_e_le_altre_si_leggono(path, bad):
    write(path, X=bad, Buona=entry())
    loaded = load_settings(path)
    assert set(loaded.indicators) == {"Buona"}
    assert len(loaded.warnings) == 1 and "«X»" in loaded.warnings[0]


def test_campi_facoltativi_hanno_un_valore_di_partenza(path):
    benchmark = {"type": "fixed", "start": "2025-01-01", "end": "2025-12-31"}
    write(path, X=entry(recipients=..., benchmark=benchmark))
    loaded = load_settings(path)
    assert loaded.warnings == ()
    assert loaded.indicators["X"].recipients == () and loaded.indicators["X"].benchmark.min_valid_days == 30


@pytest.mark.parametrize(
    "content",
    ["{ non json", "", "[1]", '{"version": 2, "indicators": {}}', '{"version": 1}', '{"version": 1, "indicators": []}'],
)
def test_file_illeggibile_da_un_avviso_e_nessuna_voce(path, content):
    path.write_text(content, encoding="utf-8")
    loaded = load_settings(path)
    assert loaded.indicators == {}
    assert len(loaded.warnings) == 1 and "configurazione.json" in loaded.warnings[0] and "sostituito" in loaded.warnings[0]


def test_file_non_utf8_da_un_avviso(path):
    path.write_bytes(b"\xff\xfe\x00bad")
    assert len(load_settings(path).warnings) == 1


def test_salvando_su_un_file_rotto_lo_si_sostituisce(path):
    path.write_text("{ non json", encoding="utf-8")
    save_indicator_settings(path, "Nuova", FIXED)
    loaded = load_settings(path)
    assert loaded.indicators == {"Nuova": FIXED} and loaded.warnings == ()


@pytest.mark.parametrize("k", [0.0, -1.0, float("nan"), float("inf")])
def test_k_non_valido_alla_costruzione(k):
    with pytest.raises(ValueError):
        IndicatorSettings("A/B", MOVING.inputs, MOVING.plausible_range, MOVING.benchmark, k, 3)


@pytest.mark.parametrize("persistence", [0, -1, True, 2.5])
def test_persistenza_non_valida_alla_costruzione(persistence):
    with pytest.raises(ValueError):
        IndicatorSettings("A/B", MOVING.inputs, MOVING.plausible_range, MOVING.benchmark, 3.0, persistence)
