"""Commento AI di un evento di allarme (R16 di SPECIFICA.md).

Questo modulo non conosce Streamlit. Riceve l'evento, l'indicatore e la serie, manda
a un modello Gemini solo i numeri dell'evento e restituisce un breve commento in
italiano per la squadra di manutenzione. Il commento è un'ipotesi da verificare.

La chiave si legge solo dalla variabile d'ambiente `GEMINI_API_KEY`: non sta in nessun
file, non si stampa e non compare nei messaggi d'errore (che sono scritti qui, in
italiano, e non riportano mai il testo dell'eccezione).
"""

from __future__ import annotations

import os

import httpx2  # è il trasporto di google-genai: da lì arrivano i timeout e gli errori di rete
import pandas as pd
from google import genai
from google.genai import errors, types

from alarms import AlarmEvent
from export import format_deviation, format_number
from indicators import Indicator

API_KEY_VARIABLE = "GEMINI_API_KEY"
MODEL_VARIABLE = "GEMINI_MODEL"
# Modello Flash scelto guardando `client.models.list()` con una chiave vera (vedi SPECIFICA.md, Q13).
DEFAULT_MODEL = "gemini-3.7-flash"
TIMEOUT_SECONDS = 30
RECENT_VALUES = 30  # al massimo gli ultimi valori dell'indicatore inviati al modello
MAX_WORDS = 120

INSTRUCTIONS = f"""Sei un assistente per la squadra di manutenzione di un impianto. Ricevi i numeri di un evento di allarme su un indicatore e scrivi un commento breve in italiano.

Regole:
- Al massimo {MAX_WORDS} parole, in parole semplici, in un testo continuo, senza titoli.
- Dì cosa è successo e quanto è grave rispetto al benchmark (scostamento e limiti).
- Indica due o tre possibili cause, scritte sempre come ipotesi da verificare, mai come cose certe.
- Chiudi con la prima cosa da controllare.
- Usa solo i numeri che ricevi: non inventare valori, date, nomi di macchine o misure.
- Se i dati non bastano per dire qualcosa, dillo."""


class AiCommentError(Exception):
    """Il commento non si è potuto ottenere. Il messaggio è in italiano e si può mostrare così com'è."""


def api_key() -> str | None:
    """La chiave dalla variabile d'ambiente, o None se manca o è vuota."""
    return os.environ.get(API_KEY_VARIABLE, "").strip() or None


def model_name() -> str:
    return os.environ.get(MODEL_VARIABLE, "").strip() or DEFAULT_MODEL


def build_prompt(
    event: AlarmEvent,
    indicator: Indicator,
    values: pd.Series,
    limits: pd.DataFrame | None = None,
    k: float | None = None,
) -> str:
    """Il testo mandato al modello: solo numeri dell'evento e degli ultimi valori dell'indicatore.

    Se ci sono `limits` (la tabella dei limiti) e `k`, si aggiungono i limiti del giorno di scatto
    e l'ampiezza k: servono al modello per dire quanto è grave lo scostamento.
    Niente destinatari, nomi di persone o impostazioni di mail. I valori sono quelli con un
    dato, fino all'ultimo giorno dell'evento (al massimo `RECENT_VALUES`), già scritti come
    li mostra l'app, così il modello cita le stesse cifre che vede l'utente.
    """
    recent = values.loc[:event.last_day].dropna().tail(RECENT_VALUES)
    recent_lines = "\n".join(f"{day:%d/%m/%Y}: {format_number(value)}" for day, value in recent.items())
    deviation = format_deviation(event.deviation_pct)
    limit_lines = ""
    if limits is not None and k is not None:
        lower, upper = limits.at[event.trigger_day, "lower"], limits.at[event.trigger_day, "upper"]
        limit_lines = (
            f"Limite inferiore nel giorno di scatto: {format_number(lower)}\n"
            f"Limite superiore nel giorno di scatto: {format_number(upper)}\n"
            f"Ampiezza dei limiti (k): {f'{k:g}'.replace('.', ',')} deviazioni standard\n"
        )
    return (
        f"Utenza: {indicator.utility or 'non indicata'}\n"
        f"Parametro: {indicator.parameter or indicator.name}\n"
        f"Direzione: {event.direction.value} i limiti\n"
        f"Primo giorno anomalo: {event.first_day:%d/%m/%Y}\n"
        f"Giorno di scatto dell'allarme: {event.trigger_day:%d/%m/%Y}\n"
        f"Ultimo giorno anomalo: {event.last_day:%d/%m/%Y}\n"
        f"Durata: {event.duration_days} giorni consecutivi\n"
        f"Valore nel giorno di scatto: {format_number(event.value)}\n"
        f"Media del benchmark (μ): {format_number(event.mean)}\n"
        f"Deviazione standard (σ): {format_number(event.std)}\n"
        f"Scostamento % dalla media: {deviation if deviation == '–' else deviation + ' %'}\n"
        f"{limit_lines}\n"
        f"Ultimi valori dell'indicatore (fino all'ultimo giorno dell'evento):\n{recent_lines}"
    )


def _make_client() -> genai.Client:
    key = api_key()
    if key is None:
        raise AiCommentError(
            f"Il commento AI è spento: manca la chiave. Imposta la variabile d'ambiente {API_KEY_VARIABLE} "
            "e riavvia l'app (come si fa è nella guida, tappa 8)."
        )
    return genai.Client(api_key=key, http_options=types.HttpOptions(timeout=TIMEOUT_SECONDS * 1000))


def _translate(exc: Exception, model: str) -> AiCommentError:
    """Un messaggio italiano per ogni caso d'errore; mai il testo originale, mai la chiave."""
    if isinstance(exc, httpx2.TimeoutException):
        return AiCommentError(f"Il modello non ha risposto entro {TIMEOUT_SECONDS} secondi. Riprova tra poco.")
    if isinstance(exc, httpx2.TransportError):
        return AiCommentError("Non riesco a raggiungere Gemini: controlla la connessione a Internet e riprova.")
    if isinstance(exc, errors.APIError):
        reason = _reason(exc)
        if exc.code in (401, 403) or reason == "API_KEY_INVALID":
            return AiCommentError(
                f"La chiave in {API_KEY_VARIABLE} non è valida o non ha il permesso di usare questo servizio. "
                "Controllala (o creane una nuova) su Google AI Studio."
            )
        if exc.code == 429:
            return AiCommentError(
                "La quota o il credito di questa chiave sono esauriti. Aspetta un po' oppure controlla il piano su Google AI Studio."
            )
        if exc.code == 404:
            return AiCommentError(f"Il modello «{model}» non è disponibile con questa chiave. Cambia {MODEL_VARIABLE}.")
        return AiCommentError(f"Gemini ha risposto con un errore (codice {exc.code}). Riprova più tardi.")
    return AiCommentError("Non sono riuscito a ottenere il commento dal modello. Riprova più tardi.")


def _reason(exc: errors.APIError) -> str | None:
    """Il motivo scritto nei dettagli dell'errore (es. `API_KEY_INVALID`), se c'è."""
    details = exc.details if isinstance(exc.details, dict) else {}
    for item in details.get("error", {}).get("details", []):
        if isinstance(item, dict) and item.get("reason"):
            return str(item["reason"])
    return None


def comment_event(
    event: AlarmEvent,
    indicator: Indicator,
    values: pd.Series,
    *,
    limits: pd.DataFrame | None = None,
    k: float | None = None,
    client=None,
) -> str:
    """Il commento del modello sull'evento, in italiano, come testo semplice (R16).

    `limits` e `k` (opzionali) sono i limiti dell'evento e l'ampiezza scelta: vanno al modello.
    `client` è opzionale: se manca se ne crea uno con la chiave dell'ambiente (e senza chiave
    si solleva `AiCommentError`). Nei test si passa un client finto, che non chiama la rete.
    Ogni errore diventa un `AiCommentError` con un messaggio italiano, senza traceback.
    """
    model = model_name()
    try:
        if client is None:
            client = _make_client()
        response = client.models.generate_content(
            model=model,
            contents=build_prompt(event, indicator, values, limits, k),
            config=types.GenerateContentConfig(system_instruction=INSTRUCTIONS),
        )
        text = (response.text or "").strip()
    except AiCommentError:
        raise  # già in italiano (per esempio «manca la chiave»)
    except Exception as exc:  # noqa: BLE001 - ogni errore dell'SDK e della rete va tradotto, non mostrato
        raise _translate(exc, model) from None
    if not text:
        raise AiCommentError("Il modello non ha restituito nessun commento. Riprova.")
    return text
