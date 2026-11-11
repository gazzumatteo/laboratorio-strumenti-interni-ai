# 03 — Come chiedere all'agente

## Perché conta

Una richiesta all'agente è un piccolo incarico di lavoro. Se l'incarico è chiaro, il risultato si può controllare. Se è vago, l'agente riempie i vuoti con le sue scelte, e voi scoprite quali solo leggendo il codice.

Non serve un linguaggio speciale. Serve dire le stesse cose che direste a un collega a cui affidate un lavoro.

## La struttura di una richiesta

Una buona richiesta ha quattro parti. Sono le stesse della specifica, in piccolo.

| Parte | Cosa dice | Esempio |
|---|---|---|
| **Contesto** | dove siamo, cosa c'è già, quali file guardare | "La specifica è in `SPECIFICA.md`. I dati sono già caricati da `load_data`." |
| **Cosa voglio** | il risultato, uno solo | "Aggiungi al grafico la media e i limiti di controllo." |
| **Vincoli** | cosa non deve cambiare, cosa non usare | "Non cambiare il caricamento dei dati. Nessuna libreria nuova." |
| **Come verifico** | come capiremo che è fatto | "Con il file d'esempio, i limiti si vedono come due linee tratteggiate e la media è circa 1,1." |

## Prima e dopo

Richiesta vaga:

> Migliora il grafico.

Cosa manca: quale grafico? Migliorare in che senso? Si può cambiare la libreria? Come capisco se è migliorato?

La stessa richiesta resa verificabile:

> Nel grafico della pagina principale aggiungi la media come linea continua e i limiti di controllo come linee tratteggiate (le regole di calcolo sono nella specifica, sezione Requisiti). Non cambiare il resto della pagina. Quando hai finito, dimmi il valore della media per la misura di riferimento, così lo confronto con quello atteso.

## Le regole pratiche

- **Una cosa per volta.** Una richiesta, un risultato. Se chiedete tre cose insieme e una va storta, è difficile capire quale.
- **Citate i file, non incollateli.** L'agente li sa aprire da solo: "leggi `SPECIFICA.md`" è meglio che incollare il testo nella chat. Così legge sempre la versione aggiornata.
- **Chiedete prima il piano.** Per qualsiasi modifica non banale: "prima proponimi un piano, non modificare niente". Leggete il piano, correggetelo, poi dite di procedere.
- **Dite cosa non toccare.** I vincoli evitano le modifiche "già che c'ero".
- **Chiedete le prove, non le rassicurazioni.** "Fammi vedere il risultato del test" vale più di "funziona?".
- **Parlate del risultato, non del codice.** Non dovete dire all'agente come scrivere una funzione: dite cosa deve succedere e come lo controllate.

## Quando la risposta non va bene

- Se l'agente ha frainteso, ditegli cosa ha frainteso, in una frase. Non ripetete la richiesta uguale.
- Se dopo due o tre tentativi gira ancora intorno allo stesso errore, fermatevi: tornate all'ultimo commit buono, riscrivete la richiesta in modo più preciso e apritela in una sessione nuova (vedi [04 — Il ciclo di sviluppo](04-ciclo-di-sviluppo.md)).
- Se vi accorgete che la richiesta era sbagliata perché la specifica era incompleta, aggiornate prima la specifica.

## Checklist

- [ ] La richiesta dice dove siamo e quali file guardare.
- [ ] Chiede un solo risultato.
- [ ] Dice cosa non va cambiato.
- [ ] Dice come verificherò il risultato.
- [ ] Per una modifica non banale ho chiesto prima il piano.
- [ ] Non ho incollato file che l'agente può leggere da solo.
