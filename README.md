# Radar PhD

Monitora le pagine PhD di EPFL, ETH, Oxford, Cambridge, Imperial, MIT, Harvard, Stanford e Caltech.
Tutto gratis: gira su GitHub Actions, il sito (installabile come app su desktop e iPhone) è su GitHub Pages, gli avvisi arrivano su Telegram.

Istruzioni di sviluppo: `CLAUDE.md`. Spec delle schermate: `design/SCREENS.md`.

## Messa online (una volta sola)
1. **Repo pubblico** su GitHub (es. `radar-phd`, senza README/licenza), poi in locale:
   `git remote add origin https://github.com/<utente>/radar-phd.git` e `git push -u origin main`.
2. **Pages**: Settings → Pages → Source "Deploy from a branch" → `main` / `/docs` → Save.
   L'app sarà su `https://<utente>.github.io/radar-phd/`.
3. **Telegram** (facoltativo): su Telegram scrivi a @BotFather → `/newbot` → copia il token.
   Manda un messaggio qualsiasi al tuo bot, poi apri `https://api.telegram.org/bot<TOKEN>/getUpdates`
   e copia `chat.id`. In GitHub: Settings → Secrets and variables → Actions → New repository secret:
   `RADAR_TELEGRAM_TOKEN` e `RADAR_TELEGRAM_CHAT_ID`.
3b. **IA Gemini** (facoltativo, gratis): crea la chiave su https://aistudio.google.com/apikey e aggiungila come secret
   `RADAR_GEMINI_API_KEY`. Ogni posizione riceve voto di pertinenza, riassunto ed etichette. Il profilo usato
   per il voto è `profilo:` in `config/sources.yaml`.
4. **Permessi Actions**: Settings → Actions → General → Workflow permissions → "Read and write permissions".
5. **Primo giro**: Actions → radar-monitor → Run workflow. Poi gira da solo ogni 6 ore.
6. **Installa l'app**: su Mac/PC apri il sito con Chrome/Edge → icona "Installa" nella barra degli indirizzi;
   su iPhone apri con Safari → Condividi → "Aggiungi alla schermata Home".
