# Guida al laboratorio

## Come usare questa guida

Questa guida accompagna il corso passo per passo. Si può seguire in aula oppure da soli, anche settimane dopo, insieme alla registrazione.

Il lavoro è diviso in **tappe**. Ogni tappa ha un obiettivo, cosa chiedere all'agente, cosa controllare, come verificare il risultato e un commit finale. Se restate indietro, potete ripartire dalla tappa già pronta (vedi [Ripartire da una tappa](#ripartire-da-una-tappa)).

Le richieste all'agente **le scrivete voi**. Per ogni tappa trovate i punti che la richiesta deve contenere, non un testo da copiare: scrivere la richiesta è parte dell'esercizio. Per la struttura di una richiesta vedi [03 — Come chiedere all'agente](docs/linee-guida/03-come-chiedere-all-agente.md).

Il metodo segue tre fasi: **Progettazione** (tappe 1 e 2), **Sviluppo** (tappe 3, 4 e 5), **Testing** (tappa 6).

## Prima di iniziare

1. Aprite un terminale (PowerShell su Windows) nella cartella dove volete lavorare e clonate il repository:
   ```
   git clone https://github.com/gazzumatteo/laboratorio-strumenti-interni-ai.git
   cd laboratorio-strumenti-interni-ai
   ```
2. Controllate l'ambiente:
   ```
   uv run tools/verifica_ambiente.py
   ```
   Ogni riga deve dire `[OK]`. Per le righe `[ERRORE]` lo script dice cosa fare.
3. Aprite la cartella in VS Code:
   ```
   code .
   ```
4. Aprite il pannello dell'assistente (Claude Code o Codex) dall'icona nella barra laterale e controllate di aver fatto l'accesso: scrivete una domanda qualsiasi e aspettate la risposta.

Da qui in avanti il terminale serve poco: si lavora nel pannello dell'agente e, per i commit, nel pannello *Source Control* di VS Code.

## Claude Code e Codex a confronto

Il metodo è lo stesso con entrambi. Cambiano alcuni comandi.

| Cosa | Claude Code | Codex |
|---|---|---|
| Aprire il pannello | icona di Claude Code nella barra laterale | icona di Codex nella barra laterale |
| Modalità pianificazione (l'agente propone, non modifica) | selettore della modalità sotto la casella di testo: scegliete la modalità piano | comando `/plan` |
| Creare il file di regole | comando `/init`; se non è disponibile, chiedete all'agente di creare il file | comando `/init` (crea `AGENTS.md`) |
| Nuova sessione | pulsante per una nuova conversazione in cima al pannello | pulsante per una nuova conversazione in cima al pannello |
| Permessi | l'agente chiede conferma prima di comandi e modifiche: leggete e approvate | scegliete la modalità che chiede conferma prima di agire |

## Git in tre gesti

**Fare un commit** (salvare un punto di lavoro): pannello *Source Control* di VS Code, scrivete un messaggio e premete *Commit*. Oppure dal terminale:

```
git add -A
git commit -m "Specifica semplificata"
```

**Vedere la storia:** `git log --oneline`, oppure la sezione *Graph* del pannello *Source Control*.

### Ripartire da una tappa

Ogni tappa ha una versione già pronta, salvata con un **tag** nel ramo `soluzione`. Se siete indietro o qualcosa si è rotto, ripartite da lì senza perdere il vostro lavoro:

```
git fetch origin --tags
git switch -c riparto-da-tappa-3 tappa-3-grafico
```

Il primo comando scarica le tappe pronte. Il secondo crea un nuovo ramo di lavoro (`riparto-da-tappa-3`, il nome lo scegliete voi) a partire dalla tappa indicata. I vostri commit restano sul ramo di prima.

Se avete modifiche non salvate, prima fate un commit oppure mettetele da parte con `git stash`.

## Le tappe

### Tappa 1 — La specifica (`tappa-1-specifica`)

**Obiettivo.** Trasformare la richiesta di partenza in una specifica piccola e verificabile, salvata in `SPECIFICA.md`. Leggete prima [docs/caso-esempio/](docs/caso-esempio/README.md).

**Cosa chiedere all'agente.** In due o tre richieste separate:
- leggere la specifica di partenza e i dati, e riportarvi cosa ha capito, cosa c'è nei dati e quali problemi vede, **senza scrivere codice**;
- dopo aver deciso voi cosa tenere e cosa tagliare: scrivere `SPECIFICA.md` nei quattro campi (stato attuale, requisiti, vincoli, verifiche), con una lista "Fuori";
- descrivere il flusso dell'app (dati → calcoli → risultati) e dividerlo in pochi moduli, uno per responsabilità.

**Cosa controllare.**
- L'agente vi ha riportato i difetti dei dati? Per ognuno la specifica ha una regola?
- Ci sono ancora aggettivi senza un criterio misurabile?
- La lista "Fuori" contiene quello che avete deciso di tagliare?

**Come verificare.** Ogni requisito ha almeno una verifica scritta. Sui dubbi di dominio (cosa significa una colonna, quale valore tenere) chiedete al docente: in aula le scelte le fissa lui. Se seguite da soli, le trovate nella registrazione e nella `SPECIFICA.md` del ramo `soluzione` (`git show tappa-1-specifica:SPECIFICA.md`).

**Commit.** `SPECIFICA.md`.

**Se sei indietro.** Si parte dal ramo `main`.

**Approfondisci.** [01 — Dall'idea alla specifica](docs/linee-guida/01-dall-idea-alla-specifica.md).

### Tappa 2 — Il file di regole (`tappa-2-regole`)

**Obiettivo.** Un file di regole che l'agente legge a ogni sessione, valido per Claude Code e per Codex.

**Cosa chiedere all'agente.**
- generare il file con `/init` (vedi la tabella sopra);
- migliorarlo: stack (Python 3.12 con uv, Streamlit), comandi per avviare l'app e i test, convenzioni (nomi nel codice in inglese, commenti e documentazione in italiano), "prima proponi un piano e aspetta la conferma", "i commit li faccio io";
- con Claude Code: spostare le regole in `AGENTS.md` e lasciare in `CLAUDE.md` solo la riga `@AGENTS.md`.

**Cosa controllare.** Il file è corto (una o due pagine), non contiene password né indirizzi interni, rimanda a `SPECIFICA.md`.

**Come verificare.** Aprite una sessione nuova e chiedete all'agente quali regole deve seguire in questo progetto: la risposta deve corrispondere al file.

**Commit.** `AGENTS.md` (e `CLAUDE.md` se usate Claude Code).

**Se sei indietro.** `tappa-1-specifica`.

**Approfondisci.** [02 — Il file di regole](docs/linee-guida/02-file-di-regole.md).

### Tappa 3 — Il primo grafico (`tappa-3-grafico`)

**Obiettivo.** L'app si avvia nel browser e mostra il grafico di una serie dal file Excel. È il traguardo del primo giorno.

**Cosa chiedere all'agente.** In modalità pianificazione, un piano per:
- creare il progetto uv;
- caricare il foglio dei dati giornalieri applicando le regole della specifica (dati mancanti, una riga per giorno, righe da scartare);
- una pagina Streamlit in cui si sceglie una serie e se ne vede il grafico.

Leggete il piano, correggetelo se serve, poi fatelo eseguire.

**Cosa controllare.** Il caricamento segue le regole della specifica, non regole inventate. Le librerie aggiunte sono solo quelle previste.

**Come verificare.**
- L'app si avvia con il comando scritto nel file di regole (di solito `uv run streamlit run …`) e si apre nel browser.
- Cambiando serie, il grafico cambia.
- Il periodo mostrato va da marzo 2024 a settembre 2026.

Se al primo avvio Streamlit chiede un indirizzo email nel terminale, premete Invio per saltare.

**Commit.** Il progetto con il grafico funzionante.

**Se sei indietro.** `tappa-2-regole`.

**Approfondisci.** [04 — Il ciclo di sviluppo](docs/linee-guida/04-ciclo-di-sviluppo.md).

### Tappa 4 — Indicatori e benchmark (`tappa-4-benchmark`)

**Obiettivo.** Monitorare un indicatore calcolato (per esempio l'energia specifica in kWh/m³) e confrontarlo con un benchmark statistico.

**Cosa chiedere all'agente.** Un passo per volta, ognuno con il suo piano:
- indicatori da formule predefinite (A/B e (A+B)/C), con un fattore di conversione delle unità;
- un filtro che escluda i giorni in cui l'impianto è fermo;
- benchmark fisso (un periodo scelto) e mobile (ultimi 30, 90, 180 o 365 giorni);
- media (μ) e limiti μ ± kσ, con k = 3 di default, disegnati sul grafico.

**Cosa controllare.** Senza il filtro sui giorni di fermo, l'indicatore ha valori enormi: con il filtro, no. I limiti cambiano quando cambiate benchmark o k.

**Come verificare.** Con l'energia specifica della pompa P2B dell'impianto SOV-SA01, la mediana è circa 1,1 kWh/m³. Confrontate il benchmark fisso con quello mobile: trovano le stesse anomalie? Se no, perché?

**Commit.** Indicatori, benchmark e limiti sul grafico.

**Se sei indietro.** `tappa-3-grafico`.

**Approfondisci.** [03 — Come chiedere all'agente](docs/linee-guida/03-come-chiedere-all-agente.md).

### Tappa 5 — Allarmi e mail (`tappa-5-allarmi`)

**Obiettivo.** Un allarme quando il valore resta fuori dai limiti per N giorni consecutivi, con l'elenco degli eventi e la mail di avviso.

**Cosa chiedere all'agente.**
- l'allarme con persistenza di N giorni (N = 3 di default), configurabile;
- l'elenco degli eventi e i giorni anomali evidenziati sul grafico;
- per ogni allarme, una mail salvata come file `.eml` con utenza, parametro, valore, media, deviazione standard, scostamento percentuale e periodo dell'evento, con destinatari configurabili (nessun invio vero).

Nella tappa pronta del ramo `soluzione` ci sono in più un report HTML scaricabile, con il grafico, e il salvataggio della configurazione. In aula non si costruiscono: il docente li mostra. Se avanza tempo, provate a chiederli voi.

**Cosa controllare.** Gli allarmi partono solo dopo N giorni consecutivi fuori limite, non al primo giorno.

**Come verificare.**
- Con N = 3 gli allarmi sono meno che con N = 1, sugli stessi dati.
- Il file `.eml` si apre con un doppio clic in Outlook (o nel vostro programma di posta) già compilato.

**Commit.** Allarmi e mail.

**Se sei indietro.** `tappa-4-benchmark`.

**Approfondisci.** [05 — Verificare](docs/linee-guida/05-verificare.md).

### Tappa 6 — I test (`tappa-6-test`)

**Obiettivo.** Prove automatiche sui calcoli, con dati di cui conoscete già il risultato.

**Cosa chiedere all'agente.**
- generare una serie di dati con anomalie inserite in punti precisi, e scrivere prima il risultato atteso;
- test sui calcoli: limiti, giorni fuori limite, allarmi con persistenza;
- una checklist di verifica manuale dell'app;
- poi, in una **sessione nuova**: rileggere il codice confrontandolo con la specifica ed elencare cosa non torna, senza correggere.

**Cosa controllare.** I test controllano numeri precisi, non solo che "non ci siano errori". Il risultato atteso l'avete deciso voi, prima.

**Come verificare.** I test passano con il comando scritto nel file di regole. Provate a rompere apposta un calcolo (per esempio chiedete all'agente di cambiare k da 3 a 2 nel codice): almeno un test deve fallire. Poi annullate la modifica.

**Commit.** Test, dati di prova e checklist.

**Se sei indietro.** `tappa-5-allarmi`.

**Approfondisci.** [05 — Verificare](docs/linee-guida/05-verificare.md).

### Tappa 7 — Il trend (`tappa-7-trend`, facoltativa)

**Obiettivo.** Individuare le derive lente con la pendenza della regressione lineare sull'ultimo periodo.

**Cosa chiedere all'agente.** La pendenza del trend su un periodo scelto, mostrata nell'app, con un test su una serie di cui conoscete la pendenza.

**Come verificare.** Su una serie costruita che cresce di 1 al giorno, la pendenza è 1.

**Commit.** Trend.

**Se sei indietro.** `tappa-6-test`.

## Se avanza tempo

- Il report HTML di un evento, con il grafico, e il salvataggio della configurazione (vedi tappa 5).
- Varianti: un secondo indicatore, un altro impianto, il foglio con i dati ogni 5 minuti.
- Oppure: scrivete con l'agente la `SPECIFICA.md` di uno strumento vostro. Solo la specifica, niente codice.

## Dopo il corso

- **Esercizio:** permettere all'utente di scrivere le proprie formule per gli indicatori. Vedi [07 — Riusare il metodo](docs/linee-guida/07-riusare-il-metodo.md).
- Quando partite su un caso vostro, seguite la checklist di [07 — Riusare il metodo](docs/linee-guida/07-riusare-il-metodo.md) e, prima, [06 — Quando non farlo da soli](docs/linee-guida/06-quando-non-farlo-da-soli.md).
