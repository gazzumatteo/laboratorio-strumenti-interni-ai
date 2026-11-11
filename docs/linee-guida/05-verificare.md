# 05 — Verificare

## Perché conta

Quando l'agente dice "fatto", è una dichiarazione, non una prova. Le prove servono proprio perché possono smentirla.

C'è anche una seconda distinzione: **"funziona" e "è giusto" sono due cose diverse.** Un'app può aprirsi, mostrare un grafico e calcolare dei limiti, e i limiti essere sbagliati perché ha preso la colonna sbagliata o ha contato come zero un valore mancante. Nessun messaggio di errore vi avvisa. Ve ne accorgete solo se avete deciso prima cosa aspettarvi.

Scrivere codice oggi costa poco. Verificare che faccia la cosa giusta è la parte del lavoro che resta vostra.

## Decidere prima cosa aspettarsi

Prima di chiedere una funzione, scrivete il risultato atteso: è il campo "Verifiche" della specifica ([01 — Dall'idea alla specifica](01-dall-idea-alla-specifica.md)). Esempi:

- "con il file d'esempio, la mediana della misura di riferimento è circa 1,1";
- "con 3 giorni di persistenza gli allarmi sono meno che con 1 giorno";
- "il report si apre nel browser e contiene il grafico".

Se il risultato atteso lo scrivete dopo aver visto quello dell'agente, tenderete a trovarlo giusto.

## I livelli di test

Un **test** è un piccolo programma che controlla in automatico un risultato. Lo scrive l'agente, voi decidete cosa deve controllare. Ci sono tre livelli; non serve conoscerli nel dettaglio, ma serve sapere che esistono.

| Livello | Cosa controlla | Esempio |
|---|---|---|
| **Unitario** | una singola funzione, da sola | "la funzione che calcola i limiti, con media 10 e deviazione 2, dà 4 e 16" |
| **Funzionale** | un pezzo di comportamento, con più funzioni insieme | "caricando un file con 5 anomalie, l'elenco eventi ne contiene 5" |
| **End-to-end** | l'app intera, come la usa una persona | "aprendo l'app nel browser e scegliendo una misura, compare il grafico" |

Per uno strumento interno piccolo, i test unitari e funzionali sui calcoli sono quelli che valgono di più: sono veloci e controllano proprio la parte che non si vede a occhio.

## Dati con anomalie note

Per sapere se un rilevatore di anomalie funziona, serve una serie di cui **conoscete già** le anomalie. Si costruisce apposta:

1. una serie regolare (per esempio un valore intorno a 100, con piccole oscillazioni);
2. qualche anomalia inserita in punti precisi (per esempio 3 giorni consecutivi a 200 a partire da una data scelta);
3. il risultato atteso, scritto prima: "un allarme, che inizia in quella data".

Poi si chiede all'agente un test che usi questi dati e controlli esattamente quel risultato. Se il test passa con i dati costruiti, potete fidarvi di più dei risultati sui dati veri.

## La checklist manuale

Alcune cose si controllano meglio a occhio, nell'app. Scrivete una breve lista e seguitela ogni volta che finite un passo importante:

- l'app si avvia con il comando scritto nelle regole;
- ogni controllo dell'interfaccia cambia davvero il risultato;
- con il file d'esempio i numeri sono quelli attesi;
- con un file sbagliato (colonna mancante, file vuoto) compare un messaggio comprensibile, non un errore tecnico.

## Chi scrive non verifica

Chi ha scritto il codice è il meno adatto a trovarne gli errori: vale per le persone e vale per l'agente. Per una verifica più seria:

- aprite una **sessione nuova** dell'agente, che non ha visto il lavoro;
- chiedetele di rileggere il codice confrontandolo con la specifica e di elencare cosa non torna, senza correggere niente;
- decidete voi quali osservazioni sono fondate.

## Checklist

- [ ] Il risultato atteso è scritto prima di vedere quello dell'agente.
- [ ] C'è almeno un test sui calcoli principali.
- [ ] C'è un test con dati ad anomalie note e risultato atteso esatto.
- [ ] Ho una checklist manuale e l'ho seguita.
- [ ] Una sessione nuova ha riletto il lavoro rispetto alla specifica.
- [ ] Non ho fatto commit su un "fatto" senza prove.
