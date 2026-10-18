# Schermate (spec testuale del design — basta questa, non serve aprire il canvas)

Stile: vedi `tokens.json`. Font IBM Plex Sans (testo) + IBM Plex Mono (date, sigle, conteggi). Card bianche r=14 su fondo #F2F4F6, bordo #DCE1E7. Badge stato colorati (open/soon/cycle/direct). Icone SVG a tratto, niente emoji. Lingua: italiano. Mobile first (390 px), su desktop colonna centrale max 480 px.
Tab bar in basso con 3 voci: Radar · Atenei · Avvisi.

## 1. Radar (home)
- Header: data + "Aggiornato HH:MM" (da `meta.json`), titolo "Radar PhD", campanella → Avvisi (pallino se non letti).
- Ricerca testuale su titolo/snippet.
- 3 tessere: Aperte · Scade < 30 gg · Nuove oggi.
- Chip filtro scorrevoli: Tutte, EPFL, ETH, Oxford, Cambridge, Imperial, MIT, Harvard, Stanford, Caltech, Princeton.
- Lista card: pallino blu se nuova, "ATENEO · dipartimento", badge stato, titolo, tipo, scadenza (arancione se < 30 gg). Tap → Dettaglio.

## 2. Dettaglio posizione
- Indietro, segnalibro (salva in localStorage), link all'annuncio originale.
- Ateneo + badge, titolo, laboratorio/supervisore se presenti.
- Griglia 2×2: Scadenza · Inizio · Durata · Finanziamento (campo assente → "—").
- "Come candidarsi": passi numerati (da `universities.json` dell'ateneo).
- "Chi contattare": nome + email se presenti; pulsanti "Scrivi email" (mailto:, nessun testo pre-generato) e "Aggiungi al calendario" (file .ics generato nel browser).
- Piè: "Fonte: … · controllato X fa".

## 3. Atenei
- Atenei raggruppati per modello: Posizione diretta (ETH) · Scuola dottorale + supervisore (EPFL) · Ammissione + borsa UK (Oxford, Cambridge, Imperial) · Ammissione di dipartimento USA (MIT, Harvard, Stanford, Caltech, Princeton). Ogni gruppo ha una riga di spiegazione.
- Riga: nome, dipartimenti, badge "N aperte"/"nessuna", prossima scadenza. Tap → Scheda ateneo.

## 4. Scheda ateneo
- Header alto ~330 px con **foto fissa del campus** a tutta larghezza (`photo` in universities.json), velatura scura dal basso per leggere il testo bianco: città · dipartimento, nome ateneo, badge del modello. Credit della foto in piccolo. Pulsante indietro tondo semitrasparente.
- Tab segmentati: Come funziona (riassunto, passi, "Da preparare") · Contatti (lista + "Scrivi email") · Fonti (pagine monitorate + ultimo controllo).

## 5. Avvisi
- Ultimi avvisi (nuova posizione, scadenza, pagina cambiata), tap → posizione o fonte.
- Parole chiave attivabili + "Aggiungi" (filtrano la lista nel Radar; salvate in localStorage).
- Frequenza e regole: in v1 sono solo filtri della vista in app; le notifiche Telegram seguono `config/sources.yaml`.
