# 02 — Il file di regole

## Perché conta

Ogni volta che aprite una sessione nuova, l'agente non ricorda niente delle precedenti. Il file di regole è quello che legge per primo, sempre: è l'introduzione che dareste a un collega nuovo il primo giorno. Che strumenti usiamo, come si avvia il progetto, come si scrivono i nomi, cosa non si fa mai.

Senza file di regole, a ogni sessione l'agente fa delle supposizioni. Con il file di regole, le supposizioni diventano regole scritte, uguali per tutti e per ogni sessione.

## Un solo file per Claude Code e Codex

I due assistenti cercano il file con nomi diversi:

| Assistente | File che legge |
|---|---|
| Codex | `AGENTS.md` |
| Claude Code | `CLAUDE.md` (legge `AGENTS.md` solo se `CLAUDE.md` non esiste) |

Per avere un solo testo valido per entrambi:

- le regole vanno in `AGENTS.md`;
- `CLAUDE.md` contiene una sola riga: `@AGENTS.md`, che dice a Claude Code di leggere l'altro file.

Su Windows non usate i collegamenti simbolici (symlink) tra i due file: spesso non funzionano senza diritti di amministratore.

## Come si crea

Non si scrive a mano. Si chiede all'agente:

1. con il comando `/init` l'agente legge il progetto e propone un primo file di regole;
2. lo leggete e chiedete all'agente di migliorarlo, aggiungendo quello che manca (sotto);
3. se usate Claude Code, chiedete di spostare le regole in `AGENTS.md` e di lasciare in `CLAUDE.md` solo `@AGENTS.md`;
4. commit.

Se `/init` non è disponibile nel vostro pannello, chiedete all'agente di creare il file con le stesse informazioni: il risultato è lo stesso.

## Cosa metterci

- **Lo scopo del progetto** in due righe, con un rimando alla specifica.
- **Lo stack:** linguaggio, versione, librerie principali, gestore dei pacchetti (per esempio "Python 3.12, gestito con uv; si installano pacchetti solo con `uv add`").
- **I comandi:** come si avvia l'app, come si lanciano i test.
- **Le convenzioni:** dove vanno i file, come si chiamano funzioni e variabili, in che lingua si scrivono commenti e documentazione.
- **Il modo di lavorare:** "prima proponi un piano e aspetta la conferma, poi modifica"; "dopo ogni modifica avvia i test"; "non fare commit: li faccio io".
- **I divieti:** cosa non si tocca (per esempio "non modificare i file in `dati/`").

## Cosa non metterci

- Password, chiavi o indirizzi di sistemi interni: il file finisce nel repository e lo legge chiunque lo cloni.
- Lunghe spiegazioni teoriche: l'agente le legge a ogni sessione e consumano spazio.
- Regole che nessuno controlla. Se una regola non serve, toglietela.

Un file di regole buono è corto: una o due pagine bastano per un progetto piccolo.

## Quando aggiornarlo

Il file di regole cresce con il progetto. Aggiornatelo quando:

- l'agente sbaglia due volte la stessa cosa (per esempio installa i pacchetti con il comando sbagliato);
- cambiate una scelta (una libreria, una cartella, un comando);
- aggiungete i test, e quindi il comando per lanciarli.

Anche l'aggiornamento si chiede all'agente: "aggiungi al file di regole che…". Poi rileggete e fate commit.

## Checklist

- [ ] Esiste `AGENTS.md` con le regole.
- [ ] Se uso Claude Code, `CLAUDE.md` contiene solo `@AGENTS.md`.
- [ ] Ci sono stack, comandi di avvio e di test, convenzioni e lingua.
- [ ] C'è la regola "prima il piano, poi le modifiche".
- [ ] Non ci sono password, chiavi o indirizzi interni.
- [ ] Il file sta in una o due pagine.
- [ ] Ho fatto commit del file.
