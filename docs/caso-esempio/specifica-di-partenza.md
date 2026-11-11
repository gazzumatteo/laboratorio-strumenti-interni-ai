# Proposta di sviluppo piattaforma per Anomaly Detection e manutenzione predittiva su dati Historian

> Documento ricevuto dal committente, riscritto senza intestazione né contatti. È il punto di partenza grezzo: nella tappa 1 lo semplificate.

## 1. Premessa

Realizzare una demo applicativa che utilizzi tecniche di analisi statistica e successivamente metodologie di Intelligenza Artificiale per identificare anomalie operative e possibili decadimenti prestazionali di impianti e apparecchiature.

L'obiettivo è verificare come i dati storici possano essere trasformati in informazioni utili per il monitoraggio delle prestazioni e per la manutenzione predittiva.

## 2. Fonte dei dati

Per lo sviluppo della demo verrà utilizzato un file Excel contenente dati storici provenienti dal sistema di telecontrollo.

In un possibile sviluppo futuro, gli stessi dati potrebbero essere acquisiti direttamente dal sistema Historian aziendale.

I dati utilizzati potranno essere:

- consumi energetici;
- volumi trattati;
- portate;
- pressioni.

## 3. Flessibilità del sistema

Uno dei requisiti fondamentali è che il sistema sia completamente configurabile.

L'utente dovrà poter decidere:

- quali utenze monitorare;
- quali parametri utilizzare;
- quali indicatori calcolare;
- quale metodologia statistica applicare;
- quali soglie adottare;
- come costruire il benchmark;
- chi deve ricevere le notifiche.

Non tutte le utenze dovranno necessariamente essere monitorate nello stesso modo.

## 4. Metodologie di analisi

### 4.1 Analisi di indicatori derivati

L'applicazione dovrà consentire la creazione di KPI ottenuti mediante formule personalizzabili.

Esempi:

- Energia specifica EnPI: EnPI = kWh/m³ = Energia consumata / Volume trattato
- Formula personalizzata: (Tag A + Tag B) / Tag C

L'utente dovrà poter definire autonomamente tali formule attraverso la dashboard.

### 4.2 Analisi di variabili singole

Per alcune utenze può essere sufficiente monitorare il valore di una variabile senza costruire alcun rapporto.

Esempi:

- pressione;
- portata;
- livello;
- consumo energetico;
- corrente assorbita;
- temperatura;
- concentrazione di processo.

Anche in questo caso il valore verrà confrontato con il benchmark statistico.

## 5. Benchmark statistico

Uno degli elementi chiave del sistema sarà la costruzione del benchmark.

Non si desidera che il sistema imponga un'unica modalità di definizione del benchmark. Sarà l'utente a scegliere il metodo più adatto alla singola utenza.

### 5.1 Benchmark fisso

L'utente seleziona uno specifico periodo storico ritenuto rappresentativo del corretto funzionamento.

Esempi:

- anno 2025;
- primo semestre 2026;
- periodo personalizzato.

Una volta creato, il benchmark rimane invariato fino a nuova configurazione.

Questo approccio è particolarmente utile per evidenziare derive lente di prestazione.

### 5.2 Benchmark mobile

L'utente sceglie una finestra temporale che si aggiorna automaticamente.

Esempi:

- ultimi 30 giorni;
- ultimi 90 giorni;
- ultimi 180 giorni;
- ultimi 365 giorni.

Questo metodo permette di adattarsi ai cambiamenti naturali del processo.

### 5.3 Analisi statistica

Per ogni parametro monitorato il sistema dovrà calcolare:

- media (μ);
- deviazione standard (σ).

Da tali valori verranno determinati i limiti di controllo:

- Limite Superiore = μ + 3σ
- Limite Inferiore = μ − 3σ

I nuovi dati acquisiti verranno confrontati quotidianamente con tali limiti.

## 6. Analisi dei trend

Oltre al controllo statistico, il sistema dovrà valutare l'andamento temporale dei parametri.

L'obiettivo è individuare derive lente o peggioramenti progressivi che potrebbero non essere immediatamente evidenti tramite il solo controllo ±3σ.

L'analisi potrà essere effettuata mediante regressione lineare e calcolo della pendenza del trend.

## 7. Gestione delle anomalie

Una possibile logica di rilevazione prevede che:

- un parametro venga considerato anomalo quando supera il limite definito dal benchmark;
- l'allarme sia generato soltanto se l'anomalia permane per un numero configurabile di giorni consecutivi (es. 3 giorni).

In questo modo si riduce il numero di falsi positivi.

## 8. Dashboard di gestione

Per la rappresentazione grafica si prevede l'utilizzo di Grafana.

La dashboard dovrebbe consentire di visualizzare:

- andamento storico dei KPI;
- media del benchmark;
- limiti ±3σ;
- trend;
- eventi anomali rilevati.

## 9. Sistema di notifiche

Quando viene rilevata un'anomalia il sistema dovrà:

- registrare l'evento;
- memorizzarlo nello storico;
- inviare automaticamente una e-mail agli utenti configurati.

L'e-mail dovrebbe contenere:

- utenza;
- parametro monitorato;
- valore rilevato;
- media del benchmark;
- deviazione standard;
- scostamento percentuale;
- grafico sintetico dell'andamento.

## 10. Risultato atteso

Realizzare una piattaforma configurabile dall'utente che trasformi i dati del telecontrollo in informazioni operative ad alto valore aggiunto, consentendo di monitorare automaticamente prestazioni e comportamenti degli impianti, individuare anomalie, intercettare derive lente e fornire un supporto concreto alle attività di gestione, manutenzione predittiva ed efficientamento energetico.
