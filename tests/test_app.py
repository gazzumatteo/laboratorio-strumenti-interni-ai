"""L'app Streamlit provata senza browser (AppTest): valori di partenza, controlli, errori e salvataggio.

Non toccano mai il vero `configurazione.json`: la lettura è sostituita da «nessuna configurazione salvata»
e la scrittura da un registratore.
"""

from datetime import date
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import loader
import settings
from benchmark import FixedBenchmark, MovingBenchmark
from indicators import DEFAULT_INDICATORS, Input

APP = str(Path(__file__).parent.parent / "app.py")
P2B = DEFAULT_INDICATORS[0].name


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    """Nessun file di configurazione letto o scritto; la cache dei dati si svuota a ogni prova."""
    st.cache_data.clear()
    saved_calls = []
    monkeypatch.setattr(settings, "load_settings", lambda path: settings.LoadedSettings({}))
    monkeypatch.setattr(settings, "save_indicator_settings", lambda path, name, value: saved_calls.append((name, value)))
    return saved_calls


def run_app() -> AppTest:
    return AppTest.from_file(APP, default_timeout=90).run()


def caption_with(at: AppTest, start: str) -> str:
    return next(c.value for c in at.caption if c.value.startswith(start))


def anomalous_days(at: AppTest) -> int:
    """I giorni anomali scritti nella didascalia sotto il grafico («… · 49 giorni anomali · 3 allarmi»)."""
    part = next(p for p in caption_with(at, "Periodo:").split(" · ") if "anomal" in p)
    return int(part.split()[0])


def test_l_app_parte_senza_errori_e_mostra_il_grafico():
    at = run_app()
    assert not at.exception and not at.warning and not at.error
    assert len(at.get("vega_lite_chart")) == 1


def test_v18_il_periodo_mostrato():
    assert "Periodo: 16/03/2024 – 15/09/2026" in caption_with(run_app(), "Periodo:")


def test_valori_di_partenza_k_3_n_3_e_benchmark_fisso_sul_2025():
    at = run_app()
    assert at.number_input(key=f"{P2B}:k").value == 3.0  # R7
    assert at.number_input(key=f"{P2B}:persistence").value == 3  # R9
    assert at.number_input(key=f"{P2B}:min_valid_days").value == 30  # R6
    benchmark = next(r for r in at.radio if r.key == f"{P2B}:benchmark")
    assert benchmark.value == "Fisso"
    period = at.date_input(key=f"{P2B}:period").value
    assert (period[0].isoformat(), period[1].isoformat()) == ("2025-01-01", "2025-12-31")


def test_v17_un_k_piu_piccolo_da_piu_giorni_anomali():
    at = run_app()
    at.number_input(key=f"{P2B}:persistence").set_value(1).run()  # con N = 1 ogni giorno anomalo conta
    at.number_input(key=f"{P2B}:k").set_value(3.0).run()
    with_k3 = anomalous_days(at)
    at.number_input(key=f"{P2B}:k").set_value(1.0).run()
    assert anomalous_days(at) > with_k3


def test_v17_cambiare_utenza_cambia_i_controlli_e_il_grafico():
    at = run_app()
    at.selectbox[0].select(DEFAULT_INDICATORS[2].name).run()  # SFI-SA02: formula (A+B)/C
    assert not at.exception
    assert next(s for s in at.selectbox if s.label == "Formula").value == "(A+B)/C"
    assert at.number_input(key=f"{DEFAULT_INDICATORS[2].name}:k").value == 3.0


def test_ogni_utenza_ha_i_suoi_valori_cambiare_k_di_una_non_tocca_l_altra():
    at = run_app()
    at.number_input(key=f"{P2B}:k").set_value(2.0).run()
    at.selectbox[0].select(DEFAULT_INDICATORS[1].name).run()
    assert at.number_input(key=f"{DEFAULT_INDICATORS[1].name}:k").value == 3.0


def test_con_k_altissimo_non_ci_sono_eventi_ne_download():
    at = run_app()
    at.number_input(key=f"{P2B}:k").set_value(50.0).run()
    assert not at.exception and not at.get("download_button")


def test_con_eventi_ci_sono_report_e_mail():
    at = run_app()
    labels = [d.proto.label for d in at.get("download_button")]
    assert labels == ["Scarica il report HTML", "Scarica la mail (.eml)"]


def test_indirizzo_non_valido_blocca_la_mail_e_il_salvataggio():
    at = run_app()
    at.text_input(key=f"{P2B}:recipients").set_value("a@x.it, abc").run()
    assert len(at.error) == 1 and "«abc»" in at.error[0].value
    assert [d.proto.label for d in at.get("download_button")] == ["Scarica il report HTML"]
    assert next(b for b in at.button if b.label.startswith("Salva")).disabled


def test_serie_del_file_non_ha_controlli_di_configurazione():
    at = run_app()
    next(r for r in at.radio if r.label == "Cosa guardare").set_value("Serie del file").run()
    assert not at.exception and not at.text_input
    assert not [b for b in at.button if b.label.startswith("Salva")]


def test_v19_file_dei_dati_mancante_da_un_messaggio_non_un_errore_tecnico(monkeypatch):
    def missing(path):
        raise loader.DataLoadError("File dei dati non trovato: dati/set-dati.xlsx")

    monkeypatch.setattr(loader, "load_daily", missing)
    at = run_app()
    assert not at.exception
    assert [e.value for e in at.error] == ["File dei dati non trovato: dati/set-dati.xlsx"]


def test_il_pulsante_salva_registra_la_configurazione_di_quell_utenza(isolated):
    at = run_app()
    at.number_input(key=f"{P2B}:k").set_value(2.5).run()
    at.number_input(key=f"{P2B}:persistence").set_value(4).run()
    at.text_input(key=f"{P2B}:recipients").set_value("a@x.it; b@y.it").run()
    assert isolated == []  # finché non si preme, non si scrive niente
    next(b for b in at.button if b.label.startswith("Salva")).click().run()
    assert len(isolated) == 1
    name, saved = isolated[0]
    assert name == P2B
    assert (saved.k, saved.persistence, saved.recipients) == (2.5, 4, ("a@x.it", "b@y.it"))
    assert saved.formula == "A/B" and [i.factor for i in saved.inputs] == [1.0, 86.4]
    assert isinstance(saved.benchmark, FixedBenchmark)


def test_il_pulsante_salva_ricorda_anche_il_benchmark_mobile(isolated):
    at = run_app()
    next(r for r in at.radio if r.key == f"{P2B}:benchmark").set_value("Mobile").run()
    next(r for r in at.radio if r.key == f"{P2B}:window").set_value(90).run()
    next(b for b in at.button if b.label.startswith("Salva")).click().run()
    assert isolated[0][1].benchmark == MovingBenchmark(90, 30)


def test_v22_riaprendo_l_app_i_valori_salvati_tornano(monkeypatch):
    saved = settings.IndicatorSettings(
        "A/B",
        DEFAULT_INDICATORS[0].inputs,
        (0.0, 5.0),
        MovingBenchmark(90, 20),
        2.5,
        5,
        ("ufficio@esempio.it",),
    )
    monkeypatch.setattr(settings, "load_settings", lambda path: settings.LoadedSettings({P2B: saved}))
    at = run_app()
    assert not at.exception
    assert at.number_input(key=f"{P2B}:k").value == 2.5
    assert at.number_input(key=f"{P2B}:persistence").value == 5
    assert at.number_input(key=f"{P2B}:min_valid_days").value == 20
    assert next(r for r in at.radio if r.key == f"{P2B}:benchmark").value == "Mobile"
    assert next(r for r in at.radio if r.key == f"{P2B}:window").value == 90
    assert at.text_input(key=f"{P2B}:recipients").value == "ufficio@esempio.it"
    assert any("Configurazione salvata" in c.value for c in at.caption)


def test_configurazione_con_una_colonna_inesistente_da_un_avviso_e_i_valori_predefiniti(monkeypatch):
    broken = settings.IndicatorSettings(
        "A/B",
        (Input("COLONNA INESISTENTE"), Input("SOV-SA01 Portata media P2B", 86.4)),
        (0.0, 5.0),
        FixedBenchmark(date(2025, 1, 1), date(2025, 12, 31)),
        2.5,
        5,
    )
    monkeypatch.setattr(settings, "load_settings", lambda path: settings.LoadedSettings({P2B: broken}))
    at = run_app()
    assert not at.exception
    assert len(at.warning) == 1 and "COLONNA INESISTENTE" in at.warning[0].value
    assert at.number_input(key=f"{P2B}:k").value == 3.0


# --- Trend (R15) -------------------------------------------------------------------------------------


def trend_metric(at: AppTest) -> str:
    return next(m.value for m in at.metric if m.label == "Pendenza del trend (per giorno)")


def test_trend_di_partenza_p2b_ultimi_90_giorni():
    at = run_app()
    assert not at.exception
    assert trend_metric(at) == "-0,000616"  # calcolato a parte con numpy.polyfit
    assert "su 83 giorni con un valore, dal 18/06/2026 al 15/09/2026" in caption_with(at, "Retta di regressione")


def test_trend_cambiando_il_periodo():
    at = run_app()
    next(r for r in at.radio if r.key == f"{P2B}:trend_days").set_value(30).run()
    assert trend_metric(at) == "-0,007521"
    next(r for r in at.radio if r.key == f"{P2B}:trend_days").set_value(365).run()
    assert trend_metric(at) == "-0,000042"


def test_trend_non_calcolato_se_i_giorni_validi_sono_pochi():
    at = run_app()
    at.selectbox[0].select(DEFAULT_INDICATORS[1].name).run()  # P3A: 9 giorni validi negli ultimi 30
    next(r for r in at.radio if r.key == f"{DEFAULT_INDICATORS[1].name}:trend_days").set_value(30).run()
    assert not at.exception
    assert trend_metric(at) == "–"
    assert "servono almeno 10 giorni" in caption_with(at, "Pendenza non calcolata")


def test_serie_del_file_non_ha_il_trend():
    at = run_app()
    next(r for r in at.radio if r.label == "Cosa guardare").set_value("Serie del file").run()
    assert not at.exception and not at.metric
