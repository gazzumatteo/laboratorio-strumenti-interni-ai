# AGENTS.md

Regole del progetto per l'agente (Claude Code o Codex). Si leggono a ogni sessione.

## Stato del repository

Materiale di un corso (CSMT / CLUI-AS, 19–20 novembre 2026): si costruisce con l'agente una piccola app Streamlit che monitora serie di misure di impianti e segnala anomalie. **Siamo alla tappa 3: l'app mostra il grafico di una serie del file.** Il codice c'è: `loader.py` (R1–R3, caricamento e pulizia) e `app.py` (scelta della serie, grafico, periodo, riquadro "Pulizia dei dati", messaggio d'errore se il file manca). Gli altri moduli di SPECIFICA.md §6 non esistono ancora. Il resto del repo è guida, linee guida, dati e [SPECIFICA.md](SPECIFICA.md). L'app si costruisce a tappe (vedi [GUIDA.md](GUIDA.md)).

[SPECIFICA.md](SPECIFICA.md) è la fonte di verità: requisiti R1–R14, verifiche V1–V22, lista "Fuori" e domande aperte. Quando una scelta non è lì, non decidere in silenzio: chiedi. Il materiale di partenza è in [docs/caso-esempio/](docs/caso-esempio/README.md); il metodo del corso in [docs/linee-guida/](docs/linee-guida/).

## Stack

- **Python 3.12**, gestito con **uv**: pacchetti solo con `uv add` (di test: `uv add --dev`), mai con pip. Non si attiva né si crea a mano nessun ambiente: `uv run` crea `.venv/` da solo.
- **Streamlit** per l'interfaccia; **pandas** (con openpyxl) per leggere l'Excel. I test, con **pytest**, arrivano con la tappa 6.
- Grafici: per ora il grafico a linee incluso con Streamlit (`st.line_chart`), nessuna libreria in più. Nessun'altra dipendenza senza averlo concordato.

## Comandi

Si lanciano dalla radice del repository. L'app esiste; i test no (pytest non è ancora tra le dipendenze, arriva con la tappa 6).

- Controllo ambiente: `uv run tools/verifica_ambiente.py`
- Avvio dell'app: `uv run streamlit run app.py` (si apre nel browser; se chiede un indirizzo e-mail nel terminale, premere Invio)
- Test, dalla tappa 6: i comandi si scrivono qui quando pytest entra nel progetto

## Architettura

Flusso dati → calcoli → risultati, in cascata, un modulo per responsabilità (dettaglio e interfacce in SPECIFICA.md §6). Esistono `loader` e `app`; gli altri sono previsti:

`loader` (Excel → tabella giornaliera pulita) → `indicators` (serie dell'indicatore + giorni non validi) → `benchmark` (μ, σ, limiti fissi o mobili) → `alarms` (giorni anomali → eventi con persistenza di N giorni) → `export` (report HTML, `.eml`) e `app` (Streamlit). `settings` legge e scrive `configurazione.json`.

Regole che attraversano più file:
- Si dipende solo "in avanti" nel flusso; i moduli di calcolo **non importano Streamlit** (solo `app` lo fa), così ogni calcolo si prova con una serie scritta a mano.
- `settings` è l'unico a toccare il file di configurazione; gli altri moduli ricevono i valori già letti.
- Gli eventi non si memorizzano: si ricalcolano a ogni avvio da dati e configurazione.

## Dati

[dati/set-dati.xlsx](dati/set-dati.xlsx), foglio `giornalieri` (il foglio `dati 5min` è fuori ambito). Intestazione su 3 righe (tag, descrizione, nome colonna); il nome di una serie è la descrizione. Non è una riga per giorno e i mancanti sono scritti `Null`: la pulizia (una riga per giorno = quella delle 23:45, `Null` → mancante, non zero) è nei requisiti R2–R3 e **non va reinventata**. Il file è in sola lettura: non modificarlo mai, la pulizia avviene in memoria.

## Convenzioni

- **Nomi nel codice in inglese** (moduli, funzioni, variabili, colonne dei DataFrame che producete); **commenti, documentazione e testi dell'interfaccia in italiano**. I nomi delle serie del file Excel restano quelli originali.
- Non aggiungere cartelle o file di struttura non previsti dal piano approvato.
- Nessuna password, chiave o indirizzo interno nei file: finiscono nel repository.

## Modo di lavorare

- **Prima proponi un piano e aspetta la conferma, poi modifica.** Nel piano di ogni passo dì quali file tocchi e come verificherai il risultato. Un passo = un risultato.
- **I commit li fa l'utente**, dopo aver visto le prove: non fare `git commit`.
- Non modificare mai `dati/` né alterare un test esistente per farlo passare.
