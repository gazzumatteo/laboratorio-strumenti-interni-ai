"""Report HTML e mail `.eml` di un evento (R12, R13; V20, V21 nella parte controllabile senza programma di posta).

L'evento è quello di V11 (tre giorni a 200 dal giorno 40 di una serie a 100 ± 2, benchmark fisso, N = 3):
il valore atteso dei campi è calcolato a mano in `known_cases.py`.
"""

import math
import re
import xml.etree.ElementTree as ET
from email import message_from_bytes, policy

import pandas as pd
import pytest
from known_cases import BENCHMARK_DAYS, build_series, day
from test_alarms import fixed_limits

from alarms import AlarmEvent, Direction, find_events
from export import (
    build_event_chart_svg,
    build_event_email,
    build_report_html,
    email_file_name,
    format_deviation,
    format_number,
    parse_recipients,
    report_file_name,
)
from indicators import Indicator, Input

INDICATOR = Indicator("Energia specifica di prova", "A/B", (Input("a"), Input("b")), None, "Utenza di prova", "Energia specifica [kWh/m³]")

# Campi attesi dell'evento di V11, come li scrive l'app (numeri con 4 decimali e virgola; scostamento con segno).
EXPECTED_FIELDS = ["Utenza di prova", "Energia specifica [kWh/m³]", "200,0000", "100,0000", "2,0342", "+100,00 %"]
EXPECTED_LIMITS = "93,8974 – 106,1026"  # 100 ∓ 3 × 2,0342
EXPECTED_DATES = {"Inizio": "09/02/2025", "Scatto": "11/02/2025", "Fine": "11/02/2025"}  # giorni 40, 42, 42


@pytest.fixture(scope="module")
def case():
    series = build_series(spike_days=(40, 41, 42))
    limits = fixed_limits(series)
    (event,) = find_events(series, limits, 3, INDICATOR.name)
    return event, series, limits


def mail_of(event, recipients=()):
    return message_from_bytes(build_event_email(event, INDICATOR, list(recipients)), policy=policy.default)


# --- Formati -----------------------------------------------------------------------------------------


@pytest.mark.parametrize("value, text", [(0.7127, "0,7127"), (200, "200,0000"), (1.10944, "1,1094"), (math.nan, "–")])
def test_numeri_con_quattro_decimali_e_virgola(value, text):
    assert format_number(value) == text


@pytest.mark.parametrize("value, text", [(-35.7512, "-35,75"), (23.784, "+23,78"), (100, "+100,00"), (math.nan, "–")])
def test_scostamento_con_segno_e_due_decimali(value, text):
    assert format_deviation(value) == text


# --- Report HTML (R12) -------------------------------------------------------------------------------


def test_report_contiene_i_sette_campi_e_i_valori_attesi(case):
    event, series, limits = case
    page = build_report_html(event, INDICATOR, series, limits, [("Benchmark", "fisso")])
    for text in EXPECTED_FIELDS + [EXPECTED_LIMITS, *EXPECTED_DATES.values(), "3 giorni", "sopra i limiti"]:
        assert text in page, text
    assert "<svg" in page  # il grafico
    assert page.startswith("<!doctype html>") and 'lang="it"' in page


def test_report_riporta_le_impostazioni_ricevute(case):
    event, series, limits = case
    page = build_report_html(event, INDICATOR, series, limits, [("Benchmark", "fisso, dal 01/01/2025"), ("Limiti", "μ ± 3σ")])
    assert "fisso, dal 01/01/2025" in page and "μ ± 3σ" in page


def test_report_e_autonomo_nessuna_risorsa_esterna(case):
    event, series, limits = case
    page = build_report_html(event, INDICATOR, series, limits, [])
    assert not re.search(r'(src|href)="https?://', page) and "<script" not in page and "<link" not in page


def test_report_identico_a_parita_di_input(case):
    event, series, limits = case
    assert build_report_html(event, INDICATOR, series, limits, []) == build_report_html(event, INDICATOR, series, limits, [])


def test_report_senza_il_testo_nan(case):
    event, series, limits = case
    nan_event = AlarmEvent(**{**event.__dict__, "deviation_pct": math.nan})
    page = build_report_html(nan_event, INDICATOR, series, limits, [])
    assert "nan" not in page.lower().replace("finanz", "") and "<td>–</td>" in page


def test_report_protegge_il_testo_dall_html(case):
    event, series, limits = case
    hostile = Indicator("<script>alert(1)</script> & \"x\"", "A/B", (Input("a"), Input("b")), None, "<b>Utenza</b>", "P&Q")
    page = build_report_html(event, hostile, series, limits, [("<i>voce</i>", "<script>1</script>")])
    assert "<script" not in page and "<b>Utenza</b>" not in page and "<i>voce</i>" not in page
    assert "&lt;b&gt;Utenza&lt;/b&gt;" in page and "P&amp;Q" in page


def test_nome_del_file_del_report(case):
    event, *_ = case
    assert report_file_name(event, INDICATOR) == "report-allarme-Utenza-di-prova-2025-02-09.html"


# --- Grafico dell'evento ------------------------------------------------------------------------------


def test_grafico_e_xml_valido_con_tre_cerchi_sui_giorni_dell_evento(case):
    event, series, limits = case
    root = ET.fromstring(build_event_chart_svg(event, series, limits))
    circles = [el for el in root.iter() if el.tag.endswith("circle")]
    assert len(circles) == 3 == event.duration_days


def test_grafico_va_da_30_giorni_prima_a_14_dopo_l_evento(case):
    event, series, limits = case
    svg = build_event_chart_svg(event, series, limits)
    # primo giorno 9/2 − 30 giorni = 10/1; ultimo giorno 11/2 + 14 giorni = 25/2
    assert "dal 10/01/2025 al 25/02/2025" in svg
    assert "10/01/25" in svg and "25/02/25" in svg and "scatto 11/02/2025" in svg


# --- Mail (R13) ------------------------------------------------------------------------------------------------


def test_mail_oggetto_e_corpo(case):
    event, *_ = case
    message = mail_of(event)
    assert message["Subject"] == "Allarme — Energia specifica di prova: sopra i limiti dal 09/02/2025"
    body = message.get_content()
    for text in EXPECTED_FIELDS + [*EXPECTED_DATES.values(), "3 giorni"]:
        assert text in body, text
    assert "report HTML" in body  # il grafico sta nel report


def test_mail_non_ha_grafico_ne_allegati_ne_parti_html(case):
    event, *_ = case
    raw = build_event_email(event, INDICATOR, ["a@x.it"])
    message = message_from_bytes(raw, policy=policy.default)
    assert not message.is_multipart() and message.get_content_type() == "text/plain" and message.get_content_charset() == "utf-8"
    assert not list(message.iter_attachments())
    assert b"<svg" not in raw and b"image/" not in raw and b"text/html" not in raw


def test_mail_e_una_bozza_senza_mittente_ne_data(case):
    event, *_ = case
    message = mail_of(event, ["a@x.it"])
    assert message["X-Unsent"] == "1" and message["From"] is None and message["Date"] is None


def test_mail_destinatari(case):
    event, *_ = case
    assert mail_of(event, ["a@x.it", "b@y.com"])["To"] == "a@x.it, b@y.com"
    assert mail_of(event, [])["To"] is None  # senza destinatari: il campo A: resta da compilare


def test_mail_identica_a_parita_di_input(case):
    event, *_ = case
    assert build_event_email(event, INDICATOR, ["a@x.it"]) == build_event_email(event, INDICATOR, ["a@x.it"])


def test_mail_senza_nan_con_scostamento_non_calcolabile(case):
    event, *_ = case
    body = mail_of(AlarmEvent(**{**event.__dict__, "deviation_pct": math.nan})).get_content()
    assert "Scostamento %: –" in body and "nan" not in body.lower()


def test_mail_caratteri_speciali_si_leggono_identici(case):
    event, *_ = case
    odd = Indicator("Energia è μ <x> & \"y\" [kWh/m³]", "A/B", (Input("a"), Input("b")), None, "UT & <b>", "P è μ")
    message = message_from_bytes(build_event_email(event, odd, []), policy=policy.default)
    assert "Energia è μ <x> & \"y\" [kWh/m³]" in message["Subject"]
    assert "UT & <b>" in message.get_content() and "P è μ" in message.get_content()


def test_mail_oggetto_lungo_resta_intero(case):
    event, *_ = case
    long = Indicator("N" * 300, "A/B", (Input("a"), Input("b")))
    assert "N" * 300 in message_from_bytes(build_event_email(event, long, []), policy=policy.default)["Subject"]


def test_il_nome_della_mail_e_del_report_non_hanno_caratteri_speciali(case):
    event, *_ = case
    odd = Indicator("x", "A/B", (Input("a"), Input("b")), None, "UT / <b> & è")
    assert email_file_name(event, INDICATOR) == "allarme-Utenza-di-prova-2025-02-09.eml"
    for name in (email_file_name(event, odd), report_file_name(event, odd)):
        assert re.fullmatch(r"[A-Za-z0-9.\-]+", name), name


# --- Destinatari -----------------------------------------------------------------------------------------------


def test_destinatari_separati_da_virgola_o_punto_e_virgola():
    assert parse_recipients(" a@x.it ;b@y.it,, ; c@z.it ") == ["a@x.it", "b@y.it", "c@z.it"]


def test_destinatari_senza_doppioni_anche_con_maiuscole_diverse():
    assert parse_recipients("A@x.it, a@X.it, b@y.it") == ["A@x.it", "b@y.it"]


@pytest.mark.parametrize("text", ["", " ", " , ; "])
def test_nessun_destinatario(text):
    assert parse_recipients(text) == []


@pytest.mark.parametrize(
    "bad",
    ["abc", "a@", "@b.it", "a@b@c.it", "a b@c.it", "a@b.it\nBcc: x@y.it", "a@b.it\rX: y", "<a@b.it>", '"a"@b.it'],
)
def test_indirizzo_non_valido(bad):
    with pytest.raises(ValueError, match="non è un indirizzo e-mail valido"):
        parse_recipients(bad)


def test_il_messaggio_d_errore_cita_l_indirizzo_sbagliato():
    with pytest.raises(ValueError, match="«abc»"):
        parse_recipients("ok@x.it, abc")


def test_a_capo_nei_destinatari_non_puo_diventare_un_altra_intestazione(case):
    event, *_ = case
    with pytest.raises(ValueError):
        build_event_email(event, INDICATOR, ["a@b.it\nBcc: x@y.it"])
