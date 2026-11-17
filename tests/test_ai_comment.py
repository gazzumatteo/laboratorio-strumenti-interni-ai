"""Il commento AI di un evento (R16; V24 nella parte automatica).

Nessun test chiama l'API vera: si usa un client finto che registra cosa riceve. L'evento è quello di V11
(tre giorni a 200 dal giorno 40 di una serie a 100 ± 2), lo stesso di `test_export.py`.
"""

import httpx2
import pandas as pd
import pytest
from google.genai import errors
from known_cases import build_series
from test_alarms import fixed_limits

import ai_comment
from ai_comment import AiCommentError, build_prompt, comment_event
from alarms import find_events
from indicators import Indicator, Input

INDICATOR = Indicator("Energia specifica di prova", "A/B", (Input("a"), Input("b")), None, "Utenza di prova", "Energia specifica [kWh/m³]")
SENTINEL_KEY = "chiave-sentinella-non-reale-0123456789"  # se compare da qualche parte, la chiave è trapelata


class FakeResponse:
    def __init__(self, text):
        self.text = text


class FakeClient:
    """Fa le veci di `genai.Client`: registra le chiamate e risponde con un testo o con un errore."""

    def __init__(self, text="Commento di prova.", error=None):
        self.text, self.error, self.calls = text, error, []
        self.models = self

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return FakeResponse(self.text)


@pytest.fixture(scope="module")
def case():
    series = build_series(spike_days=(40, 41, 42))
    (event,) = find_events(series, fixed_limits(series), 3, INDICATOR.name)
    return event, series


# --- Cosa si manda al modello ------------------------------------------------------------------------


def test_il_prompt_ha_i_numeri_dell_evento(case):
    event, series = case
    prompt = build_prompt(event, INDICATOR, series)
    for text in ["Utenza di prova", "Energia specifica [kWh/m³]", "200,0000", "100,0000", "2,0342", "+100,00 %", "sopra i limiti",
                 "09/02/2025", "11/02/2025", "3 giorni"]:  # fmt: skip
        assert text in prompt, text


def test_il_prompt_ha_al_massimo_30_valori_e_nessuno_dopo_la_fine_dell_evento(case):
    event, series = case
    prompt = build_prompt(event, INDICATOR, series)
    lines = [line for line in prompt.splitlines() if line[:2].isdigit() and line[2] == "/" and ": " in line]
    days = [pd.to_datetime(line.split(": ")[0], format="%d/%m/%Y") for line in lines]
    assert len(lines) == 30
    assert days[-1] == event.last_day and max(days) <= event.last_day
    assert lines[-1].endswith(": 200,0000")  # l'ultimo giorno dell'evento


def test_i_valori_mancanti_non_sono_inviati(case):
    event, series = case
    with_gap = series.copy()
    with_gap.iloc[30:35] = float("nan")
    lines = [ln for ln in build_prompt(event, INDICATOR, with_gap).splitlines() if ln[:2].isdigit() and ": " in ln]
    assert not any("–" in ln for ln in lines) and len(lines) == 30


def test_il_prompt_non_ha_destinatari_ne_chiave(case, monkeypatch):
    event, series = case
    monkeypatch.setenv("GEMINI_API_KEY", SENTINEL_KEY)
    client = FakeClient()
    comment_event(event, INDICATOR, series, client=client)
    (call,) = client.calls
    sent = f"{call['contents']}\n{call['config'].system_instruction}"
    assert SENTINEL_KEY not in sent
    assert "@" not in sent and "destinatari" not in sent.lower()


def test_le_istruzioni_chiedono_italiano_120_parole_e_ipotesi(case):
    event, series = case
    client = FakeClient()
    comment_event(event, INDICATOR, series, client=client)
    instructions = client.calls[0]["config"].system_instruction
    for text in ["italiano", "120 parole", "ipotesi", "solo i numeri che ricevi"]:
        assert text in instructions, text


# --- Cosa si riceve ----------------------------------------------------------------------------------


def test_il_commento_e_il_testo_del_modello_senza_spazi_attorno(case):
    event, series = case
    client = FakeClient(text="  Il consumo è salito.\n")
    assert comment_event(event, INDICATOR, series, client=client) == "Il consumo è salito."
    assert len(client.calls) == 1


def test_il_modello_e_quello_predefinito_o_quello_della_variabile(case, monkeypatch):
    event, series = case
    client = FakeClient()
    comment_event(event, INDICATOR, series, client=client)
    assert client.calls[0]["model"] == ai_comment.DEFAULT_MODEL
    monkeypatch.setenv("GEMINI_MODEL", "gemini-prova")
    comment_event(event, INDICATOR, series, client=client)
    assert client.calls[1]["model"] == "gemini-prova"


@pytest.mark.parametrize("text", [None, "", "   \n"])
def test_una_risposta_vuota_e_un_errore_in_italiano(case, text):
    event, series = case
    with pytest.raises(AiCommentError, match="nessun commento"):
        comment_event(event, INDICATOR, series, client=FakeClient(text=text))


# --- Errori: ognuno ha il suo messaggio italiano, senza traceback e senza chiave ---------------------


def api_error(cls, code, reason=None):
    details = [{"@type": "type.googleapis.com/google.rpc.ErrorInfo", "reason": reason}] if reason else []
    body = {"error": {"code": code, "message": f"messaggio inglese con {SENTINEL_KEY}", "status": "X", "details": details}}
    return cls(code, body)


ERROR_CASES = [
    ("chiave non valida (400 dell'API)", api_error(errors.ClientError, 400, "API_KEY_INVALID"), "non è valida"),
    ("chiave non autorizzata (403)", api_error(errors.ClientError, 403), "non è valida"),
    ("chiave non autorizzata (401)", api_error(errors.ClientError, 401), "non è valida"),
    ("quota esaurita (429)", api_error(errors.ClientError, 429), "quota o il credito"),
    ("modello non trovato (404)", api_error(errors.ClientError, 404), "non è disponibile"),
    ("servizio in errore (503)", api_error(errors.ServerError, 503), "codice 503"),
    ("tempo scaduto", httpx2.ReadTimeout(f"timeout {SENTINEL_KEY}"), "entro 30 secondi"),
    ("rete assente", httpx2.ConnectError(f"rete {SENTINEL_KEY}"), "connessione a Internet"),
    ("errore imprevisto", RuntimeError(f"boom {SENTINEL_KEY}"), "Riprova più tardi"),
]


@pytest.mark.parametrize("error, expected", [(e, t) for _, e, t in ERROR_CASES], ids=[c[0] for c in ERROR_CASES])
def test_ogni_errore_ha_il_suo_messaggio_italiano(case, monkeypatch, error, expected):
    event, series = case
    monkeypatch.setenv("GEMINI_API_KEY", SENTINEL_KEY)
    with pytest.raises(AiCommentError) as caught:
        comment_event(event, INDICATOR, series, client=FakeClient(error=error))
    message = str(caught.value)
    assert expected in message
    assert SENTINEL_KEY not in message  # né la chiave né il testo originale dell'errore
    assert caught.value.__cause__ is None


# --- Chiave e client ---------------------------------------------------------------------------------


@pytest.mark.parametrize("value", [None, "", "   "])
def test_senza_chiave_si_solleva_un_errore_che_dice_come_attivarla(case, monkeypatch, value):
    event, series = case
    if value is not None:
        monkeypatch.setenv("GEMINI_API_KEY", value)
    assert ai_comment.api_key() is None
    with pytest.raises(AiCommentError, match="GEMINI_API_KEY"):
        comment_event(event, INDICATOR, series)


def test_il_client_vero_si_crea_con_la_chiave_dell_ambiente_e_30_secondi(monkeypatch):
    seen = {}

    def fake_client(**kwargs):
        seen.update(kwargs)
        return "client"

    monkeypatch.setenv("GEMINI_API_KEY", SENTINEL_KEY)
    monkeypatch.setattr(ai_comment.genai, "Client", fake_client)
    assert ai_comment._make_client() == "client"
    assert seen["api_key"] == SENTINEL_KEY
    assert seen["http_options"].timeout == 30_000  # millisecondi


def test_la_chiave_non_sta_in_nessun_file_del_codice():
    from pathlib import Path

    root = Path(__file__).parent.parent
    for path in [root / "ai_comment.py", root / "app.py", root / "export.py"]:
        assert "AIza" not in path.read_text(encoding="utf-8"), path.name  # prefisso delle chiavi Google


# --- Limiti e k vanno al modello; gli errori nella creazione del client diventano messaggi italiani ----


def test_il_prompt_ha_i_limiti_del_giorno_di_scatto_e_k(case):
    event, series = case
    limits = fixed_limits(series)  # k = 3
    prompt = build_prompt(event, INDICATOR, series, limits, 3.0)
    assert "Limite inferiore nel giorno di scatto: 93,8974" in prompt
    assert "Limite superiore nel giorno di scatto: 106,1026" in prompt
    assert "Ampiezza dei limiti (k): 3 deviazioni standard" in prompt
    assert "2,5 deviazioni" in build_prompt(event, INDICATOR, series, fixed_limits(series, 2.5), 2.5)


def test_senza_limiti_il_prompt_non_li_inventa(case):
    event, series = case
    assert "Limite" not in build_prompt(event, INDICATOR, series)


def test_comment_event_manda_i_limiti_al_modello(case):
    event, series = case
    client = FakeClient()
    comment_event(event, INDICATOR, series, limits=fixed_limits(series), k=3.0, client=client)
    assert "Limite superiore nel giorno di scatto: 106,1026" in client.calls[0]["contents"]


def test_un_errore_nella_creazione_del_client_e_un_messaggio_italiano(case, monkeypatch):
    event, series = case

    def broken_client(**kwargs):
        raise ValueError(f"impossibile creare il client con {SENTINEL_KEY}")

    monkeypatch.setenv("GEMINI_API_KEY", SENTINEL_KEY)
    monkeypatch.setattr(ai_comment.genai, "Client", broken_client)
    with pytest.raises(AiCommentError) as caught:
        comment_event(event, INDICATOR, series)
    assert "Riprova più tardi" in str(caught.value) and SENTINEL_KEY not in str(caught.value)
