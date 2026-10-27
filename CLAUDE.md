# Radar PhD

App personale che monitora le pagine PhD di 9 atenei (EPFL, ETH, Oxford, Cambridge, Imperial, MIT, Harvard, Stanford, Caltech) per ing. meccanica/aerospaziale e settori affini, e mostra: posizioni aperte, scadenze, come funziona la candidatura, chi contattare. UI in italiano.

## Vincoli (non negoziabili)
- **Costo zero.** Solo servizi gratuiti: GitHub (repo pubblico, Actions, Pages), bot Telegram e il **piano gratuito dell'API Gemini** (Google AI Studio, senza fatturazione). Niente server, hosting, database, domini o API a pagamento, incluse API di AI e motori di ricerca a pagamento. Se una soluzione richiede una carta di credito, è esclusa.
- **IA solo lato server:** la chiave Gemini sta nei segreti di GitHub (`RADAR_GEMINI_API_KEY`), mai nel frontend. Il testo dell'IA (voto, motivo, riassunto, etichette) è mostrato con l'etichetta "IA"; professore e scadenza dall'IA sono accettati solo se citati alla lettera dalla pagina.
- **Ricerca = lettura diretta delle pagine ufficiali** (scraping gentile: robots.txt, 1 richiesta ogni ≥5 s per dominio), più eventuali aggregatori gratuiti.
- **Frontend senza build:** HTML + CSS + JS vanilla in `docs/`. Niente npm, framework o bundler.
- **App installabile (PWA):** sul Mac/PC "Installa app" dal browser, su iPhone Safari → Condividi → "Aggiungi alla schermata Home". Serve `manifest.webmanifest`, `sw.js` e le icone.
- **Mai inventare dati:** campo non trovato nella pagina = `null`, mostrato come "—". Ogni posizione ha `source_url` e `last_checked`.
- **Niente email pre-generate:** "Scrivi email" apre solo `mailto:`.

## Architettura
```
GitHub Actions (cron ogni 6 h, gratis)
  radar run-once:  fetch.py → extract.py → monitor.py → SQLite (data/radar.sqlite)
                   → notify.py (Telegram) → export.py → docs/data/*.json
  commit & push
GitHub Pages serve docs/  →  PWA legge docs/data/*.json
```
Stato utente (posizioni salvate, parole chiave scelte, avvisi letti) = `localStorage` nel browser.

## Mappa file
| File | Ruolo |
|---|---|
| `radar/fetch.py` | download con robots.txt e rate limit |
| `radar/extract.py` | trova annunci (link con marker PhD + parola chiave), scadenza, hash pagine |
| `radar/monitor.py` | un giro: nuove posizioni, pagine cambiate, promemoria scadenze (14/3 gg) |
| `radar/ai.py` | voto di pertinenza 0–10, motivo, riassunto ed etichette con Gemini (max 30 posizioni/giro, ≤10 richieste/min) |
| `radar/export.py` | scrive `docs/data/{positions,universities,alerts,meta}.json` |
| `radar/notify.py` | Telegram (+ email opzionale), credenziali solo da env |
| `config/sources.yaml` | pagine da monitorare, parole chiave per gruppo (`fluidi`, `ml`, `altro` → etichetta "ML + fluidi"), `profilo` usato dall'IA. URL `verified: false` = da controllare |
| `config/universities.yaml` | modello di candidatura, passi, contatti, foto campus per ateneo |
| `design/SCREENS.md` | **spec delle 5 schermate: leggi questa, non serve altro per la UI** |
| `design/tokens.json` | colori, font, raggi |
| `docs/` | la PWA (`index.html`, `app.css`, `app.js`, `sw.js`, `manifest.webmanifest`, `icons/`, `img/campus/`) |

## Task (in ordine, uno alla volta; `pytest` verde e commit dopo ognuno)
1. **Fonti.** Verifica ogni URL di `sources.yaml` (apri la pagina, controlla che esista e che riguardi PhD meccanica/aero). Correggi, imposta `verified: true`, aggiungi `selector` dove la pagina è rumorosa. Per le pagine che caricano gli annunci via JavaScript cerca un endpoint JSON/RSS pubblico; se non c'è, segnalo e passa oltre.
2. **Parser specifici** in `radar/parsers/<sito>.py` solo dove l'estrazione generica fallisce. Test con fixture HTML salvate in `tests/fixtures/` (mai rete nei test).
3. **Dati atenei.** Completa `universities.yaml` (passi, contatti ufficiali, scadenze) solo da pagine ufficiali; aggiungi la URL della fonte accanto a ogni dato.
4. **Foto campus.** Una foto per ateneo da Wikimedia Commons con licenza libera, ridimensionata ~1200 px larghezza, < 250 KB, in `docs/img/campus/<id>.jpg`; compila `photo_credit` (autore, licenza, link).
5. **PWA** in `docs/` secondo `design/SCREENS.md`: `index.html`, `app.css`, `app.js` (router a hash: `#/`, `#/p/<id>`, `#/atenei`, `#/ateneo/<id>`, `#/avvisi`), `manifest.webmanifest`, `sw.js` (cache dell'app, dati sempre freschi dalla rete), icone 192/512 + `apple-touch-icon` 180.
6. **Deploy.** Repo pubblico, Pages da `main` / `docs`, segreti Telegram, primo `workflow_dispatch`. Spiega all'utente i passi manuali.

## Comandi
```bash
pip install -e ".[dev]"
pytest
radar run-once     # giro completo (rete) + export
radar export       # solo JSON
python -m http.server -d docs 8000   # prova la PWA in locale
```

## Come lavorare (risparmio token)
- Non rileggere file già letti in questa sessione; non aprire `data/` o `docs/data/` (generati).
- Modifiche piccole e mirate; niente refactor non richiesti.
- Prima di un task lungo scrivi in 3 righe cosa farai, poi fallo.
- A fine task: una riga su cosa è cambiato e cosa resta da fare.
