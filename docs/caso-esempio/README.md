# Il caso d'esempio

Durante il corso costruiamo tutti la stessa app partendo da un caso reale, messo a disposizione dall'Acquedotto del Fiora: il monitoraggio dei consumi energetici delle pompe di alcuni impianti.

**È un esempio, non lo scopo del corso.** Non stiamo facendo l'app per un'azienda in particolare. Il caso serve ad avere dati veri, con i loro difetti, e una richiesta scritta da chi lavora sugli impianti, con le sue ambiguità.

Il metodo vale per qualsiasi serie di misure nel tempo che arriva da sensori o impianti, per esempio:

- l'assorbimento di corrente dei motori di una linea di produzione;
- la pressione e la temperatura dei compressori di una centrale;
- i consumi delle cabine elettriche di uno stabilimento.

## Cosa trovate qui

| File | Cosa contiene |
|---|---|
| [specifica-di-partenza.md](specifica-di-partenza.md) | La richiesta del committente così come è arrivata, senza intestazione né contatti. È volutamente ampia: nella tappa 1 la trasformate in una specifica più piccola e verificabile. |
| [../../dati/set-dati.xlsx](../../dati/set-dati.xlsx) | I dati storici, esportati dal sistema di telecontrollo. Due fogli: `giornalieri` (un valore al giorno per circa due anni e mezzo) e `dati 5min` (un valore ogni 5 minuti per circa sei mesi). |

I dati sono forniti a solo scopo didattico.

## Prima di scrivere codice

Guardate i dati prima di decidere cosa costruire: aprite il file, oppure chiedete all'agente di analizzarlo e di riportarvi cosa trova. Quello che emerge diventa parte della specifica.
