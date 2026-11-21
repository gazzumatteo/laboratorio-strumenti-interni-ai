# Sviluppo di un Proof of Concept (PoC) applicato al monitoraggio di impianti e reti

Un laboratorio pratico: costruiamo una piccola applicazione web in Python con l'aiuto di un assistente AI di programmazione (Claude Code oppure Codex) dentro Visual Studio Code. L'app monitora serie di misure da impianti, le confronta con un benchmark statistico e segnala le anomalie.

L'app è il pretesto. Lo scopo è imparare un metodo ripetibile per costruirsi da soli strumenti interni, in tre fasi: **Progettazione → Sviluppo → Testing**. Si parte da un [caso d'esempio](docs/caso-esempio/README.md) reale, ma il metodo vale per qualsiasi caso.

## Cosa serve

- Una licenza: **Claude** piano Pro o superiore, oppure **ChatGPT** piano Plus o superiore.
- **Visual Studio Code** (versione "User setup"): <https://code.visualstudio.com/>
- L'estensione dell'assistente, installata in VS Code: "Claude Code" (editore: Anthropic) oppure "Codex – OpenAI's coding agent" (editore: OpenAI).
- **Git for Windows**: <https://git-scm.com/download/win>
- **uv**, il gestore di Python (installa anche Python). Da PowerShell:
  ```
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```

Non serve un account GitHub.

## Come si parte

Da un terminale (PowerShell su Windows):

```
git clone https://github.com/gazzumatteo/laboratorio-strumenti-interni-ai.git
cd laboratorio-strumenti-interni-ai
uv run tools/verifica_ambiente.py
```

Lo script controlla che tutto sia installato e, per ogni problema, dice cosa fare. Quando tutte le righe dicono `[OK]`:

```
code .
```

e proseguite con la [guida al laboratorio](GUIDA.md).

## Cosa c'è nel repository

| Percorso | Contenuto |
|---|---|
| [GUIDA.md](GUIDA.md) | La guida passo per passo, tappa per tappa. Si può seguire anche da soli. |
| [docs/caso-esempio/](docs/caso-esempio/README.md) | La richiesta di partenza del caso d'esempio. |
| [docs/linee-guida/](docs/linee-guida/) | Le linee guida del metodo, da riusare sui vostri casi. |
| [dati/set-dati.xlsx](dati/set-dati.xlsx) | I dati storici del caso d'esempio. |
| [tools/verifica_ambiente.py](tools/verifica_ambiente.py) | Lo script che controlla l'ambiente. |

Le linee guida:

1. [Dall'idea alla specifica](docs/linee-guida/01-dall-idea-alla-specifica.md)
2. [Il file di regole](docs/linee-guida/02-file-di-regole.md)
3. [Come chiedere all'agente](docs/linee-guida/03-come-chiedere-all-agente.md)
4. [Il ciclo di sviluppo](docs/linee-guida/04-ciclo-di-sviluppo.md)
5. [Verificare](docs/linee-guida/05-verificare.md)
6. [Quando non farlo da soli](docs/linee-guida/06-quando-non-farlo-da-soli.md)
7. [Riusare il metodo su un caso vostro](docs/linee-guida/07-riusare-il-metodo.md)

## I rami

| Ramo | Cosa contiene |
|---|---|
| `main` | Il punto di partenza: guida, linee guida, dati. Niente codice: lo costruite voi con l'agente. |
| `soluzione` | Il PoC completo e testato, preparato prima del corso. Ogni tappa ha un tag (`tappa-1-specifica` … `tappa-7-trend`) da cui ripartire se restate indietro. |
| `in-aula` | Il lavoro fatto dal vivo durante il corso, tappa per tappa, in linea con la registrazione. |

I dati del caso d'esempio sono forniti a solo scopo didattico.
