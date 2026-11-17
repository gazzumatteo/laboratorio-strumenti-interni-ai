# SPECIFICA — Monitoraggio dei consumi energetici delle pompe

Strumento interno che legge uno storico di misure giornaliere, calcola indicatori, li confronta con un benchmark statistico e segnala le anomalie che durano più giorni.

Punto di partenza: [specifica-di-partenza.md](docs/caso-esempio/specifica-di-partenza.md), ridotta qui a ciò che si costruisce in questo corso. Dati: [dati/set-dati.xlsx](dati/set-dati.xlsx).

> Le scelte segnate **(provvisoria)** sono decisioni mie in attesa di conferma di chi conosce l'impianto. Sono elencate in [Domande aperte](#domande-aperte).

---

## 1. Stato attuale

**Cosa c'è oggi.** I dati arrivano da un export del sistema di telecontrollo in un file Excel. Non esiste uno strumento che li guardi: le anomalie si vedono solo quando qualcuno apre il file. La richiesta del committente è ampia (Grafana, notifiche, metodi AI, formule libere) e va ridotta.

**Cosa c'è nei dati** (verificato sul file):

| | Foglio `giornalieri` (usato) | Foglio `dati 5min` (non usato) |
|---|---|---|
| Righe × colonne | 2.679 × 18 | 57.612 × 10 |
| Periodo | 16/03/2024 – 16/09/2026 | 28/02/2026 – 16/09/2026 |
| Contenuto | energia e portata media di 3 impianti: SOV-SA01 (6 pompe), SFI-SA04, SFI-SA02 | potenza e portata di 2 impianti |

Struttura del foglio: 3 righe di intestazione (tag, descrizione, nome colonna), poi i dati. La prima colonna è la data-ora.

**Difetti del foglio `giornalieri`.**

1. **Non c'è una riga per giorno.** 915 date distinte, 2.679 righe. 914 date su 915 hanno una riga alle 23:45; 526 righe sono alle 00:00 e spesso ripetono i valori delle 23:45 del giorno prima (non sempre: alcune colonne SFI differiscono). In più ci sono 1.234 righe a orari sparsi, spesso a raffiche di righe uguali a pochi millisecondi di distanza. Quattro date hanno più righe alle 23:45, distanti 1–6 ms; non sempre sono uguali.
2. **L'ultima data (16/09/2026) ha solo la riga delle 00:00**, cioè un giorno incompleto.
3. **I valori mancanti sono scritti come testo `Null`**, non come celle vuote.
4. **Molte pompe sono quasi sempre ferme.** Giorni con energia e portata maggiori di zero: P1A 53, P2A 68, P1B 3, P3B 59, contro P3A 883 e P2B 907.
5. **Outlier fisicamente impossibili.** `SOV-SA01 Energia P3A` vale 2.306.359 l'11/07/2024 e 2.352.164 il 19/07/2024. Il massimo di tutti gli altri giorni è circa 8.500.
6. **La portata è in l/s, non è un volume.** L'energia specifica richiede una conversione. Le unità dell'energia non sono scritte nel file.
7. **SFI-SA04 ha molti valori mancanti e valori assurdi** (p99 dell'indicatore oltre 13.000). Non è usato (vedi [Fuori](#5-fuori)).

---

## 2. Requisiti

### Preparazione dei dati

- **R1 — Caricamento.** Legge il solo foglio `giornalieri`. Il nome di ogni serie è la descrizione (riga 2 dell'intestazione), per esempio `SOV-SA01 Energia P2B`.
- **R2 — Una riga per giorno.** Per ogni data si tiene la riga delle 23:45:00; se sono più d'una, la prima in ordine di orario. Tutte le altre righe (00:00, orari sparsi, raffiche) si scartano. Una data senza riga alle 23:45 si scarta (giorno incompleto). **(provvisoria)**
- **R3 — Valori mancanti.** `Null` e celle vuote diventano "mancante". Non si sostituiscono con zero, non si interpolano.
- **R4 — Giorno non valido.** Per un indicatore, un giorno è non valido se: (a) manca uno degli ingressi, (b) l'impianto è fermo, cioè il numeratore o il denominatore della formula (dopo i fattori) è ≤ 0: per `A/B` è `A` ≤ 0 o `B` ≤ 0, per `(A+B)/C` è `A+B` ≤ 0 o `C` ≤ 0, così un giorno con una sola pompa in marcia resta valido, (c) l'indicatore è fuori dall'intervallo plausibile scelto per quell'indicatore. Un giorno non valido non entra nel benchmark e non è mai un giorno anomalo; nel grafico è marcato con il motivo (mancante, fermo, fuori scala).

### Indicatori

- **R5 — Indicatori.** Tipi predefiniti: variabile singola `A`, rapporto `A/B`, `(A+B)/C`. Ogni ingresso è una colonna con un fattore di conversione (default 1). Per la portata media in l/s il fattore verso m³/giorno è 86,4 (86.400 s ÷ 1.000 l/m³), cioè si assume la portata media sulle 24 ore. **(provvisoria)** Energia specifica = energia ÷ (portata × 86,4), in kWh/m³.
- **R5b — Utenze preconfigurate.** `SOV-SA01 P2B` e `SOV-SA01 P3A` (A/B, intervallo plausibile 0–5 kWh/m³); `SFI-SA02` ((P1+P2)/portata, intervallo 0–10 kWh/m³). L'utente può aggiungerne scegliendo tipo di indicatore e colonne tra quelle del file.

### Benchmark e limiti

- **R6 — Benchmark.** Per ogni indicatore l'utente sceglie:
  - **fisso**: un periodo di date (inizio e fine); μ e σ calcolati una volta;
  - **mobile**: 30, 90, 180 o 365 giorni. Per il giorno *D* la finestra contiene i giorni precedenti *D*, **escluso *D***, quindi i limiti variano nel tempo.
  
  μ e σ si calcolano solo sui giorni validi, con la deviazione standard campionaria (divisore *n*−1). Se la finestra ha meno giorni validi del minimo il benchmark non è calcolato e l'app mostra "dati insufficienti" con il numero di giorni validi trovati. Il minimo è 30 per default (provvisorio) e l'utente lo può cambiare (almeno 2): con la finestra mobile di 30 giorni il valore 30 richiede che tutti i giorni precedenti siano validi.
- **R7 — Limiti.** Limite superiore = μ + kσ, inferiore = μ − kσ. k è configurabile, default 3.
- **R8 — Giorno anomalo.** Un giorno valido con valore strettamente fuori dai limiti. Si registra se sopra o sotto.

### Allarmi

- **R9 — Persistenza.** Un allarme esiste solo se ci sono almeno *N* giorni di calendario consecutivi anomali (N configurabile, default 3). Un giorno non valido interrompe la sequenza, e così un giorno anomalo dalla parte opposta dei limiti (3 giorni sopra e 2 sotto non fanno un allarme da 5). Si genera un solo evento per sequenza, non uno per giorno.
- **R10 — Evento.** Contiene: utenza, indicatore, primo giorno anomalo, giorno di scatto (l'*N*-esimo), ultimo giorno anomalo, durata in giorni, direzione (sopra/sotto), valore del giorno di scatto, μ e σ in vigore quel giorno, scostamento % = (valore − μ) ÷ μ × 100. L'elenco degli eventi si ricalcola a ogni avvio dai dati e dalla configurazione; non c'è un database.

### Uscite

- **R11 — Interfaccia.** Una pagina: l'utente sceglie l'indicatore, il tipo di benchmark e il periodo, k, N. Vede il grafico (serie, μ, limiti, giorni anomali evidenziati, giorni non validi marcati), l'elenco degli eventi e la quantità di giorni scartati dalla pulizia. Se il file manca o una colonna non c'è, compare un messaggio in italiano che dice cosa manca, senza traceback.
- **R12 — Report HTML.** Per ogni evento, un report scaricabile che si apre nel browser, con: utenza, parametro, valore rilevato, media del benchmark, deviazione standard, scostamento %, grafico dell'andamento. Il report è un unico file HTML senza dipendenze esterne (si apre anche senza rete); il grafico è un SVG in linea, dal 30° giorno prima dell'inizio al 14° dopo la fine dell'evento, con serie, media, limiti e giorni dell'evento evidenziati. Il report riporta anche i limiti nel giorno di scatto, il periodo dell'evento e le impostazioni usate (formula e fattori, benchmark, k, N, filtro dei giorni esclusi). Stesso input, stesso file: non c'è la data di generazione.
- **R13 — Mail.** Per ogni evento, un file `.eml` già compilato, con i destinatari scelti dall'utente per l'indicatore (ripuliti dai doppioni; un indirizzo di forma non valida dà un errore e nessun file). Il testo contiene gli stessi dati del report: utenza, parametro, valore rilevato, media, deviazione standard, scostamento % e periodo dell'evento. **Non contiene il grafico** (scelta per la demo: nessun allegato, nessuna immagine, nessuna dipendenza in più); rimanda al report HTML. Il file è una bozza (`X-Unsent: 1`, senza mittente né data, quindi stesso input → stesso file). Non si invia nulla. Finché non c'è R14, i destinatari si scrivono nell'app a ogni avvio.
- **R14 — Configurazione.** Le scelte (indicatori, ingressi, fattori, intervallo plausibile, benchmark, k, N, destinatari) si salvano in un file JSON leggibile con un editor di testo e si ricaricano all'avvio. Ogni indicatore ha la propria configurazione: non tutte le utenze si monitorano allo stesso modo. Il file è `configurazione.json` nella radice del repository (non è versionato: contiene indirizzi e-mail), con una voce per utenza e le chiavi in inglese (`formula`, `inputs`, `plausible_range`, `benchmark`, `k`, `persistence_days`, `recipients`). Si salva col pulsante «Salva la configurazione di questa utenza», che riscrive solo la voce di quell'utenza e lascia intatte le altre. Se il file manca, si parte dai valori predefiniti; se una voce è rovinata o scritta male a mano (o cita una colonna che nel file dei dati non c'è) compare un avviso in italiano e quell'utenza riparte dai predefiniti, senza fermare le altre; se non si legge tutto il file, avviso e predefiniti, e il successivo salvataggio lo sostituisce. L'utenza scelta e la casella dei giorni esclusi non si salvano.

---

## 3. Vincoli

- **Stack:** Python 3.12 gestito con uv; interfaccia Streamlit; lettura Excel con pandas/openpyxl. La libreria dei grafici si sceglie nel piano della tappa 3, preferendo quella già inclusa con Streamlit se basta. Nessun'altra dipendenza senza averlo concordato.
- **Esecuzione:** sul PC dell'utente, nel browser. Nessun server, nessun database, nessun accesso di rete richiesto.
- **Sola lettura:** `dati/set-dati.xlsx` non si modifica mai; la pulizia avviene in memoria.
- **Struttura del codice:** i moduli di calcolo non importano Streamlit; solo `app.py` lo fa. Ogni modulo di calcolo si prova da solo, con dati scritti nel test.
- **Lingua:** nomi nel codice in inglese; commenti, documentazione e testi dell'interfaccia in italiano.
- **Dati di prova:** i test non dipendono da `set-dati.xlsx`, tranne le verifiche V1–V6 che usano proprio quel file.
- **Prestazioni:** lettura e pulizia del foglio giornaliero in meno di 2 secondi (misurato: 0,14 s per la sola lettura).

---

## 4. Verifiche

I valori attesi sono scritti **prima** della costruzione. Quelli sul file d'esempio sono stati calcolati con uno script a parte durante la lettura dei dati; i test in tappa 6 li riconfermeranno.

### Sui dati veri

| # | Requisito | Verifica | Esito atteso |
|---|---|---|---|
| V1 | R1, R2 | Caricare e pulire `giornalieri` | 914 giorni, dal 2024-03-16 al 2026-09-15; nessuna data ripetuta; 16/09/2026 assente |
| V2 | R4, R5 | Energia specifica P2B | 907 giorni validi, 7 di fermo, 0 mancanti; mediana tra 1,09 e 1,12 kWh/m³ (calcolata: 1,105) |
| V3 | R4 | Energia specifica P3A, intervallo 0–5 | 31 giorni di fermo, 2 fuori scala (11/07/2024 e 19/07/2024), 881 validi; massimo dei validi ≤ 1,5 |
| V4 | R6 | Benchmark su P1B (3 giorni validi in tutto il periodo) | messaggio "dati insufficienti", nessun limite disegnato |
| V5 | R6, R8 | P2B: benchmark fisso sul 2025 e mobile a 365 giorni | i limiti del fisso sono costanti, quelli del mobile cambiano; le differenze nelle anomalie trovate sono spiegabili da quella differenza |
| V6 | R9 | Sui dati veri, stesse impostazioni e N = 1 contro N = 3 | gli eventi a N = 3 sono ≤ quelli a N = 1, e ognuno è contenuto in uno di N = 1 |

### Su dati costruiti (risultato noto)

| # | Requisito | Verifica | Esito atteso |
|---|---|---|---|
| V7 | R3 | File di prova con `Null` in una cella | la cella è "mancante", non 0 |
| V8 | R2 | File di prova: 3 righe alle 23:45 della stessa data, a 1 ms | resta la prima; le altre sono scartate |
| V9 | R7 | Valori 8, 8, 10, 12, 12 (μ = 10, σ = 2), k = 3 | limiti 4 e 16 |
| V10 | R6 | Benchmark mobile: cambiare il valore del giorno *D* | i limiti del giorno *D* non cambiano |
| V11 | R8, R9 | 60 giorni a 98/102 alternati, 3 giorni consecutivi a 200 dal giorno 40; benchmark fisso sui giorni 1–30; N = 3 | 1 evento: inizio giorno 40, scatto giorno 42, fine giorno 42, durata 3, direzione sopra |
| V12 | R9 | Come V11 con soli 2 giorni a 200 | N = 3: 0 eventi; N = 2: 1 evento |
| V13 | R9 | Come V11 con un giorno normale tra due giorni a 200, oppure un giorno mancante | N = 2: 0 eventi (la sequenza si interrompe) |
| V14 | R10 | Evento di V11 con μ = 100 e valore 200 | scostamento % = +100 |
| V15 | R5 | `(A+B)/C` con A = 10, B = 20, C = 3 e fattore 1 | 10 |

### Sull'app (checklist manuale)

| # | Requisito | Verifica | Esito atteso |
|---|---|---|---|
| V16 | R11 | Avviare l'app con il comando scritto nel file di regole | si apre nel browser e mostra il grafico entro 5 secondi |
| V17 | R11 | Scegliere un altro indicatore, un altro k, un altro N | il grafico, i limiti e l'elenco eventi cambiano di conseguenza |
| V18 | R11 | Il periodo mostrato | da 16/03/2024 a 15/09/2026 |
| V19 | R11 | Rinominare il file dei dati e riavviare | messaggio in italiano, senza traceback |
| V20 | R12 | Scaricare il report di un evento | si apre nel browser e contiene i sette campi e il grafico |
| V21 | R13 | Aprire il `.eml` con doppio clic | il programma di posta lo apre già compilato (destinatari, oggetto, corpo); nessun invio |
| V22 | R14 | Cambiare k e N, chiudere e riaprire l'app | i valori sono quelli scelti |

---

## 5. Fuori

Non si costruisce adesso, e di proposito:

- **Grafana.** La dashboard è nell'app Streamlit.
- **Invio vero delle e-mail.** Si produce solo il file `.eml`.
- **Collegamento diretto a Historian o a un database.** La sorgente è l'Excel.
- **Foglio `dati 5min`.** Non è un valore al giorno e copre solo 6 mesi; si può aggiungere come variante.
- **Formule scritte liberamente dall'utente.** Solo i tipi A, A/B, (A+B)/C. È l'esercizio dopo il corso.
- **Metodi di intelligenza artificiale.** Solo statistica (μ ± kσ).
- **Analisi di trend con regressione lineare.** Facoltativa, tappa 7.
- **Storico degli eventi memorizzato.** Gli eventi si ricalcolano a ogni avvio.
- **Accesso con password, più utenti, ruoli.**
- **Interpolazione o ricostruzione dei dati mancanti.**
- **SFI-SA04 e le pompe quasi sempre ferme** (P1A, P2A, P1B, P3B di SOV-SA01) come utenze preconfigurate. Si possono aggiungere dall'app, ma per le pompe quasi sempre ferme l'app può rispondere "dati insufficienti" (R6).
- **Controllo di unità e correttezza fisica delle colonne** oltre all'intervallo plausibile (R4).

---

## 6. Flusso dell'app e moduli

```
dati/set-dati.xlsx  (foglio "giornalieri", sola lettura)
        │
        ▼
  1. loader        →  tabella giornaliera pulita: una riga per giorno, numeri o "mancante"
        │
        ▼
  2. indicators    →  serie dell'indicatore scelto, con i giorni non validi marcati (motivo)
        │
        ▼
  3. benchmark     →  μ, σ, limite inferiore e superiore (costanti o per giorno)
        │
        ▼
  4. alarms        →  giorni anomali → eventi (persistenza di N giorni)
        │
        ▼
  5. export  → report HTML e file .eml          6. app → grafico, elenco eventi, comandi

  settings  ⟷  legge e scrive configurazione.json; app e gli altri moduli ricevono i valori già letti
```

**Dati → calcoli → risultati.** `loader` produce i dati puliti; `indicators`, `benchmark` e `alarms` sono i calcoli, in cascata, ognuno con in ingresso solo l'uscita del precedente e i propri parametri; `export` e `app` mostrano i risultati.

| Modulo | Responsabilità (una sola) | Riceve | Restituisce | Non fa |
|---|---|---|---|---|
| `loader` | Dal file Excel alla tabella giornaliera pulita (R1–R3) | percorso del file | tabella con indice = data, una colonna per serie, e un riepilogo delle righe scartate | calcoli sui valori, giorni di fermo |
| `indicators` | Costruire l'indicatore dagli ingressi e marcare i giorni non validi (R4, R5) | tabella, definizione dell'indicatore | serie dell'indicatore e, per ogni giorno, valido oppure il motivo | benchmark, soglie di allarme |
| `benchmark` | Calcolare μ, σ e limiti (R6, R7) | serie, tipo di benchmark, periodo o finestra, k | per ogni giorno: μ, σ, limite inferiore, limite superiore, oppure "dati insufficienti" | decidere quali giorni sono allarmi |
| `alarms` | Segnare i giorni anomali e raggrupparli in eventi (R8–R10) | serie, limiti, N | giorni anomali ed elenco eventi | disegnare, scrivere file |
| `export` | Trasformare un evento in report HTML e in `.eml` (R12, R13) | evento, serie, destinatari | testo del report e del messaggio | calcolare qualcosa |
| `settings` | Leggere e scrivere la configurazione (R14) | percorso del file | oggetto di configurazione, valori di default se il file manca | calcoli, grafica |
| `app` | Interfaccia Streamlit: comandi, grafico, messaggi d'errore (R11) | azioni dell'utente | pagina nel browser | logica di calcolo |

**Regole tra i moduli.** Si dipende solo "in avanti" nel flusso: `loader` non conosce `indicators`, e così via. Solo `app` importa Streamlit e solo `settings` tocca il file di configurazione. Così ogni calcolo si prova con una serie scritta a mano (V7–V15) senza avviare l'app.

---

## Domande aperte

Da portare a chi conosce l'impianto o i dati. Fino alla risposta valgono le scelte provvisorie.

| # | Domanda | Scelta provvisoria |
|---|---|---|
| Q1 | Qual è la riga giusta del giorno? Le righe alle 23:45 e quelle a orari sparsi sono letture diverse? Che significano le righe a raffiche? | Vale la riga delle 23:45, la prima se ce ne sono più d'una (R2) |
| Q2 | L'energia è in kWh? E la portata media è calcolata sulle 24 ore o solo sul tempo di marcia della pompa? | kWh; sulle 24 ore, fattore 86,4 (R5). La mediana 1,105 di P2B è coerente con questa ipotesi |
| Q3 | Cosa sono i valori 2.306.359 e 2.352.164 di P3A (11 e 19/07/2024)? Errore di lettura o guasto reale? | Errore di lettura: esclusi con l'intervallo plausibile (R4) |
| Q4 | Cosa significa "impianto fermo"? Energia o portata uguali a zero, o sotto una soglia? | Numeratore o denominatore della formula ≤ 0 (R4). Su SFI-SA02 in 5 giorni una sola pompa è a zero e l'indicatore è normale |
| Q5 | Il giorno non valido (fermo, dato mancante) interrompe una sequenza di anomalie o la sospende? | La interrompe (R9) |
| Q6 | La finestra mobile include il giorno valutato? | No, solo i giorni precedenti (R6) |
| Q7 | Servono almeno quanti giorni validi per fidarsi di un benchmark? | 30 (R6) |
| Q8 | Quali sono gli intervalli plausibili per ogni indicatore? | 0–5 per P2B e P3A, 0–10 per SFI-SA02 (R5b). Da confermare: il p99 di SFI-SA02 è 5,76 |
| Q9 | Nel foglio a 5 minuti la colonna `POTENZA ORB-PO04 [bar]` ha l'unità di una pressione, i valori (fino a 104) e il tag fanno pensare a una potenza in kW. Quale delle due? | Non rilevante finché il foglio è fuori |
| Q10 | Perché SFI-SA04 ha molti valori mancanti e valori assurdi? | Fuori dalla demo |
| Q11 | Se l'anomalia passa da sopra a sotto i limiti senza giorni normali in mezzo, è un unico allarme o due? | Due: cambiare parte dei limiti interrompe la sequenza (R9). Sui dati veri non succede mai |
