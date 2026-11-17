# Checklist di verifica manuale dell'app

Quello che i test automatici non vedono: l'app vera, nel browser, con gli occhi. Si segue ogni volta che si
finisce un passo importante. Le sigle V16–V22 sono le verifiche di [SPECIFICA.md](../SPECIFICA.md) §4.

**Prima di cominciare**

- [ ] I test automatici passano: `uv run pytest` (nessun errore, nessun test saltato).
- [ ] Nella radice non c'è un `configurazione.json` di una prova precedente (altrimenti i valori di partenza sono i suoi): se c'è, spostatelo o cancellatelo.

**1. Avvio e primo grafico** (V16, V18)

- [ ] `uv run streamlit run app.py` apre l'app nel browser.
- [ ] Entro 5 secondi compare il grafico dell'indicatore «Energia specifica SOV-SA01 P2B».
- [ ] Sotto il grafico: «Periodo: 16/03/2024 – 15/09/2026 · 914 giorni».
- [ ] Nessun messaggio d'errore e nessun avviso giallo.

**2. I controlli cambiano davvero il risultato** (V17)

- [ ] Cambio l'utenza (P3A, poi SFI-SA02): il grafico, le colonne e la formula cambiano. SFI-SA02 usa `(A+B)/C`.
- [ ] Cambio k da 3 a 1: le linee dei limiti si avvicinano alla media e i giorni anomali aumentano.
- [ ] Cambio N da 3 a 1: gli allarmi diventano uguali o più numerosi, mai meno.
- [ ] Passo da benchmark Fisso a Mobile e scelgo una finestra: i limiti smettono di essere due righe orizzontali.
- [ ] Tolgo la spunta a «Escludi giorni di fermo…»: compaiono i giorni di fermo (valore 0) e il grafico si schiaccia.

**3. Numeri attesi con il file d'esempio** (V2, V3, V5)

- [ ] P2B, benchmark Mobile 365, k = 3, N = 3: un solo evento, 06/06/2024 → 12/06/2024, sotto i limiti, scostamento −35,75 %.
- [ ] P3A, stesse impostazioni: un evento 21/07/2025 → 30/07/2025, sopra i limiti, +23,78 %.
- [ ] SFI-SA02, stesse impostazioni: due eventi (04/07/2024 sopra, +33,16 %; 09/04/2025 sotto, −68,73 %).
- [ ] P3A: i due giorni «fuori scala» (11 e 19/07/2024) non sono nel grafico, ma segnati come esclusi.
- [ ] Trend (R15), P2B: ultimi 90 giorni → pendenza −0,000616 su 83 giorni (dal 18/06/2026 al 15/09/2026); 30 giorni → −0,007521 su 25 giorni.
- [ ] Trend, P3A, 30 giorni: «Pendenza non calcolata» e il motivo (solo 9 giorni con un valore, ne servono 10).

**4. Errori comprensibili** (V19)

- [ ] Rinomino `dati/set-dati.xlsx` e riavvio: compare un messaggio in italiano che dice che il file non c'è, senza traceback. Poi rimetto il nome giusto.
- [ ] Nel campo dei destinatari scrivo `abc`: compare l'errore con «abc», e i pulsanti «Scarica la mail» e «Salva» spariscono o si disattivano.
- [ ] Svuoto una data del periodo di riferimento: il pulsante «Salva» si disattiva e dice perché.

**5. Report e mail** (V20, V21)

- [ ] «Scarica il report HTML», aprirlo nel browser: ci sono utenza, parametro, valore, media, deviazione standard, scostamento % e il grafico.
- [ ] Il report si apre anche senza rete (scollego il wifi e lo riapro).
- [ ] Con destinatari scritti, «Scarica la mail (.eml)» e doppio clic: il programma di posta la apre già compilata (destinatari, oggetto, corpo), senza inviare niente.
- [ ] La mail non contiene il grafico e dice che si trova nel report.

**6. Configurazione salvata** (V22)

- [ ] Cambio k a 2 e N a 4, scrivo un destinatario, premo «Salva la configurazione di questa utenza»: compare «Configurazione salvata in configurazione.json».
- [ ] Apro `configurazione.json` con un editor di testo: si legge, e ci sono i valori scelti.
- [ ] Chiudo l'app e la riavvio: k = 2, N = 4 e il destinatario sono quelli scelti.
- [ ] Cambio k senza salvare: compare «Ci sono modifiche non salvate»; riavviando torna il valore salvato.
- [ ] Rovino a mano il file (tolgo una virgola): l'app parte lo stesso, con un avviso in italiano e i valori predefiniti.
- [ ] Cancello `configurazione.json` a fine prova (contiene indirizzi e-mail, non va nel repository).

**Esito**

Data: ____ · Chi: ____ · Punti che non tornano: ____
