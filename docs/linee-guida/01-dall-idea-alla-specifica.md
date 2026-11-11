# 01 — Dall'idea alla specifica

## Perché conta

Un agente AI fa esattamente quello che capisce della vostra richiesta. Se la richiesta è vaga, le decisioni che non avete preso le prende lui, e le trovate scritte nel codice. Per esempio: cosa fare con un valore mancante, come trattare un valore fuori scala, quanto deve essere grande il grafico.

La specifica serve a prendere quelle decisioni **prima**, per iscritto, in un file che resta nel progetto. È anche il documento su cui si confrontano due persone, o una persona e l'agente, quando non sono d'accordo su cosa andava fatto.

## Prima guardate i dati

Non si scrive una specifica senza aver visto i dati veri. Aprite il file, oppure chiedete all'agente di analizzarlo e di riportarvi:

- quante righe e quante colonne ci sono, e che periodo coprono;
- come sono scritte le date e i valori mancanti;
- se ci sono righe ripetute, valori impossibili, unità di misura strane.

Quello che trovate diventa parte della specifica: una regola per i dati mancanti, un filtro per i valori impossibili, una scelta su quale riga tenere.

## I quattro campi

Una specifica utile ha quattro parti. Non è un formato obbligatorio: è un promemoria per non dimenticare niente.

| Campo | Domanda a cui risponde | Esempio |
|---|---|---|
| **Stato attuale** | Cosa c'è oggi? | "I dati arrivano in un Excel esportato a mano ogni mese. Nessuno li guarda finché non si rompe una pompa." |
| **Requisiti** | Cosa deve fare lo strumento? | "Mostrare il grafico di una misura scelta dall'utente, con la media e i limiti di controllo." |
| **Vincoli** | Entro quali limiti? | "Python con uv, interfaccia Streamlit, gira sul PC dell'utente, nessun collegamento ai sistemi di impianto." |
| **Verifiche** | Come capisco che è fatto bene? | "Con il file d'esempio, la mediana della misura X è circa 1,1." |

Il campo più importante è l'ultimo. I requisiti dicono cosa produrre; le verifiche dicono quando fermarsi.

## Dentro e fuori

Scrivete esplicitamente anche cosa **non** fate. Una richiesta reale chiede quasi sempre più di quanto serve per partire. Una lista "Fuori" evita che l'agente costruisca cose che nessuno ha chiesto adesso, e ricorda a voi che le avete scartate di proposito.

Esempio:

- **Dentro:** caricamento dell'Excel, grafico, limiti di controllo, elenco delle anomalie.
- **Fuori (per ora):** collegamento diretto al database, invio automatico di email, accesso con password.

## Dagli aggettivi ai criteri verificabili

Un aggettivo non si può controllare. Un criterio sì. Ogni volta che nella specifica compare un aggettivo, trasformatelo in qualcosa che si può misurare o osservare.

| Aggettivo | Criterio verificabile |
|---|---|
| "veloce" | "si apre in meno di 5 secondi con il file d'esempio" |
| "facile da usare" | "un collega che non l'ha mai vista sceglie una misura e vede il grafico senza istruzioni" |
| "affidabile" | "su una serie con 3 anomalie inserite apposta, ne trova esattamente 3" |
| "configurabile" | "soglia e numero di giorni si cambiano dall'interfaccia e restano salvati alla riapertura" |

Se un criterio non vi viene, spesso è perché non avete ancora deciso cosa volete. Meglio scoprirlo adesso.

## Le domande aperte

Durante la scrittura emergono dubbi che non potete sciogliere da soli: cosa misura davvero una colonna, quale unità usa, se un picco è un guasto o un errore di lettura. Scriveteli in una sezione "Domande aperte" e portateli a chi conosce l'impianto o il processo. Finché restano aperti, scrivete la scelta provvisoria che fate e perché.

L'agente non conosce il vostro impianto. Può aiutarvi a trovare i dubbi, ma non a risolverli.

## Come farla scrivere all'agente

La specifica la scrivete insieme all'agente, non la dettate parola per parola e non la delegate del tutto:

1. date all'agente il materiale di partenza (richiesta, dati) e chiedetegli di riassumere cosa ha capito e cosa non è chiaro;
2. decidete voi cosa tenere e cosa tagliare;
3. chiedetegli di scrivere la specifica nei quattro campi;
4. rileggetela: ogni requisito ha almeno una verifica? Ci sono ancora aggettivi?
5. salvatela nel progetto (per esempio `SPECIFICA.md`) e fate un commit.

## Checklist

- [ ] Ho guardato i dati veri prima di scrivere.
- [ ] La specifica ha i quattro campi: stato attuale, requisiti, vincoli, verifiche.
- [ ] C'è una lista di cose che restano fuori.
- [ ] Ogni requisito ha almeno una verifica.
- [ ] Nessun aggettivo senza un criterio misurabile.
- [ ] Le domande aperte sono scritte, con la scelta provvisoria.
- [ ] La specifica è salvata in un file del progetto, con un commit.
