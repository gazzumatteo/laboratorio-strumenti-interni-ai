# 04 — Il ciclo di sviluppo

## Perché conta

Un agente non fa una cosa e si ferma: prova, controlla, corregge, riprova. Il vostro lavoro è decidere come gira questo ciclo: cosa gli chiedete, quando gli dite di andare avanti, quando lo fermate. Se lo guidate bene, ogni passo vi lascia qualcosa che funziona e che potete ritrovare.

## Il ciclo

Ogni passo di lavoro segue lo stesso giro:

1. **Piano.** L'agente propone cosa farà, voi lo leggete.
2. **Modifica.** L'agente cambia i file.
3. **Prova.** Si controlla che funzioni: test, avvio dell'app, verifiche della specifica.
4. **Commit.** Se le prove passano, salvate il punto raggiunto con un commit.

Poi si riparte con il passo successivo. Passi piccoli: un passo che richiede più di qualche minuto di lavoro dell'agente è probabilmente troppo grande.

## Leggere il piano prima di dire sì

Entrambi gli assistenti hanno una **modalità pianificazione**: l'agente legge e ragiona, ma non modifica niente finché non approvate. Usatela per ogni passo non banale.

Quando leggete il piano, chiedetevi:

- tocca solo i file che mi aspetto?
- fa una cosa sola, quella che ho chiesto?
- dice come verificherà il risultato?
- aggiunge librerie o cartelle che non ho chiesto?

Correggere un piano costa una frase. Correggere il codice dopo costa molto di più.

## I permessi

Mentre lavora, l'agente chiede il permesso per lanciare comandi o modificare file. Non approvate a occhi chiusi:

- **di solito sì:** leggere file del progetto, lanciare i test, avviare l'app, installare una libreria prevista dalla specifica;
- **fermatevi a leggere:** cancellare file, modificare file fuori dalla cartella del progetto, comandi che non capite;
- **di solito no:** comandi che scrivono su sistemi aziendali, che inviano dati fuori, che cambiano impostazioni del PC.

Se non capite un comando, chiedete all'agente cosa fa prima di approvarlo.

## Il commit lo fa una persona

L'agente dice "fatto". Il commit lo decidete voi, dopo aver visto le prove. Un commit è una dichiarazione: "a questo punto funziona, l'ho controllato". Per questo nel file di regole conviene scrivere che i commit li fate voi.

Si può fare commit dal pannello *Source Control* di VS Code oppure dal terminale:

```
git add -A
git commit -m "Grafico con media e limiti di controllo"
```

Il messaggio dice cosa è cambiato, in una riga.

## Git come rete di sicurezza

Con un commit per ogni passo, qualunque errore si recupera:

- per vedere cosa è cambiato dall'ultimo commit: pannello *Source Control*, oppure `git diff`;
- per buttare le modifiche non ancora salvate e tornare all'ultimo commit: dal pannello *Source Control*, "Discard All Changes" (attenzione: non si torna indietro);
- per ripartire da un punto salvato: un **tag** è un nome dato a un commit (per esempio `tappa-3-grafico`), e da lì si può creare un nuovo ramo di lavoro.

Più spesso fate commit, meno lavoro rischiate di perdere.

## Quando fermarsi

Fermatevi e cambiate approccio quando:

- **l'agente gira in tondo:** tenta la stessa correzione due o tre volte senza risultato;
- **la conversazione è lunga:** dopo molti scambi l'agente tende a confondere decisioni vecchie e nuove;
- **non capite più cosa sta facendo:** se non sapreste spiegarlo a un collega, non approvate altro.

Cosa fare: tornate all'ultimo commit buono, aprite una **sessione nuova** e riformulate la richiesta in modo più preciso. La sessione nuova non ricorda la conversazione precedente, ma non serve: quello che conta è scritto nei file (specifica, file di regole, codice). La memoria del progetto sta nei file, non nella chat.

## Checklist

- [ ] Ogni passo parte da un piano letto e approvato.
- [ ] I passi sono piccoli: un risultato ciascuno.
- [ ] Ho capito ogni comando prima di approvarlo.
- [ ] Faccio commit solo dopo aver visto le prove.
- [ ] Ogni commit ha un messaggio che dice cosa è cambiato.
- [ ] Se l'agente gira in tondo, torno all'ultimo commit e apro una sessione nuova.
