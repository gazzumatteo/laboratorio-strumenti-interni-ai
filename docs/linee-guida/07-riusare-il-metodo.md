# 07 — Riusare il metodo su un caso vostro

## Perché conta

Il caso d'esempio del corso è servito a fare pratica. Il metodo, invece, è quello che vi portate a casa: vale per qualsiasi strumento interno, dal monitoraggio di una misura a un piccolo calcolatore per l'ufficio tecnico.

Questa pagina è la lista da seguire quando partite da soli.

## 1. Scegliete il problema

- **Piccolo e concreto.** "Vedere a colpo d'occhio quando l'assorbimento di un motore si discosta dal solito" è un buon inizio. "Una piattaforma di manutenzione predittiva" no: è il punto di arrivo, non di partenza.
- **Vostro.** Un problema che conoscete bene, così sapete giudicare se il risultato è giusto.
- **Con dati che potete usare.** Vedi [06 — Quando non farlo da soli](06-quando-non-farlo-da-soli.md).

## 2. Preparate i dati d'esempio

Un estratto reale, non troppo grande: qualche mese o qualche anno di dati, in un file Excel o CSV. Mettetelo in una cartella `dati/` del progetto. Se i dati sono sensibili, usate un estratto ripulito o dati costruiti apposta.

## 3. Create il progetto

- una cartella nuova, con `git init`;
- aprite la cartella in VS Code e il pannello dell'agente;
- primo commit con i soli dati e una nota su cosa volete fare.

## 4. Scrivete la specifica

Con l'agente, nei quattro campi: stato attuale, requisiti, vincoli, verifiche. Prima fate analizzare i dati. Lista "Fuori" esplicita. Vedi [01 — Dall'idea alla specifica](01-dall-idea-alla-specifica.md). Commit.

## 5. Create il file di regole

`/init`, poi miglioratelo con l'agente: stack, comandi, convenzioni, "prima il piano". Vedi [02 — Il file di regole](02-file-di-regole.md). Commit.

## 6. Procedete per tappe

Dividete il lavoro in tappe piccole, ognuna con un risultato che si vede, come nel corso:

1. caricamento dei dati e un primo grafico;
2. i calcoli principali;
3. gli output (elenco, report, notifiche);
4. i test.

Per ogni tappa: piano, modifica, prova, commit ([04 — Il ciclo di sviluppo](04-ciclo-di-sviluppo.md)). Alla fine di una tappa riuscita potete dargli un nome con un tag: `git tag tappa-1`.

## 7. Verificate

Risultati attesi scritti prima, test sui calcoli, dati con anomalie note, checklist manuale, rilettura da una sessione nuova. Vedi [05 — Verificare](05-verificare.md).

## Un esercizio per dopo il corso

Nell'app del corso le formule degli indicatori sono predefinite (per esempio A/B oppure (A+B)/C). La richiesta di partenza chiedeva invece che l'utente potesse **scrivere le proprie formule** dall'interfaccia.

Provate ad aggiungerlo seguendo il metodo: aggiornate prima la specifica (quali operazioni sono ammesse? cosa succede con una formula sbagliata? come si verifica?), poi piano, modifica, prova, commit. È un buon esercizio perché obbliga a pensare ai casi d'errore prima di scrivere codice.

## Oltre Streamlit

Nel corso usiamo Streamlit perché permette di avere un'interfaccia web scrivendo solo Python. Per strumenti più grandi, usati da molte persone, si separano spesso due parti: un **backend** che fa i calcoli e custodisce i dati (in Python, per esempio) e un **frontend** che è l'interfaccia nel browser (in TypeScript, con React, Next.js o Vue). È più lavoro e richiede più competenze, ma permette interfacce più ricche e più persone al lavoro sullo stesso progetto. Il metodo resta lo stesso.

## Checklist

- [ ] Il problema è piccolo, concreto e lo conosco bene.
- [ ] Ho dati d'esempio che posso usare.
- [ ] Il progetto ha git, la specifica e il file di regole, con un commit ciascuno.
- [ ] Il lavoro è diviso in tappe, ognuna con un risultato visibile.
- [ ] Ogni tappa finisce con le prove e un commit.
- [ ] I calcoli principali hanno test con risultati attesi scritti prima.
