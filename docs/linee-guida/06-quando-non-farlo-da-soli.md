# 06 — Quando non farlo da soli

## Perché conta

Costruire da soli uno strumento interno ora è alla portata di molti. Non sempre però è la scelta giusta. Ci sono casi in cui serve coinvolgere qualcun altro prima di partire, o prima che lo strumento lo usino altre persone.

## I casi in cui fermarsi a chiedere

- **Dati sensibili o personali.** Dati di clienti, dipendenti, contratti, dati sanitari. Prima di darli a un assistente AI verificate cosa permette la vostra azienda: alcuni servizi possono conservare o elaborare i dati fuori dall'azienda.
- **Sistemi di impianto (OT, SCADA, PLC).** Uno strumento che legge dati esportati è una cosa. Uno strumento che scrive verso un impianto, o si collega direttamente ai sistemi di controllo, è un'altra: lì un errore ha conseguenze fisiche. Mai senza chi è responsabile di quei sistemi.
- **Strumenti che useranno altre persone.** Se lo strumento esce dal vostro PC, qualcuno deve mantenerlo: aggiornare le librerie, correggere gli errori, rispondere a chi lo usa. Decidete chi, prima.
- **Decisioni che dipendono dallo strumento.** Se in base ai risultati si ferma un impianto o si fa un intervento, i calcoli devono essere verificati da chi conosce il processo, non solo dai test.

## Le regole dell'azienda

Molte aziende hanno regole su:

- quali assistenti AI si possono usare e con quale licenza;
- dove può girare il codice (PC personale, server interno, cloud);
- dove si salvano i repository e chi può vederli.

Informatevi prima di costruire qualcosa che volete far usare ad altri.

## Quando coinvolgere l'IT

Coinvolgete l'IT quando lo strumento deve collegarsi a database o sistemi aziendali, girare su un server, essere usato da più persone, o gestire accessi e password. Arrivare con una specifica scritta e un prototipo funzionante rende la conversazione molto più semplice.

## Checklist

- [ ] So che dati uso e se posso darli a un assistente AI.
- [ ] Lo strumento non scrive verso sistemi di impianto.
- [ ] Se lo useranno altri, è deciso chi lo mantiene.
- [ ] Conosco le regole aziendali su AI, codice e repository.
- [ ] So quando devo coinvolgere l'IT.
