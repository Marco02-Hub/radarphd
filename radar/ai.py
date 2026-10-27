"""Valutazione delle posizioni con Gemini (piano gratuito di Google AI Studio).

Per ogni posizione attiva non ancora valutata con il profilo attuale chiede a Gemini:
voto di pertinenza 0–10, motivo, riassunto in italiano, etichette tematiche.
Professore e scadenza vengono accettati solo se Gemini li cita parola per parola dal testo
della pagina (regola "mai inventare dati"), e solo se il radar non li aveva già trovati.

Senza RADAR_GEMINI_API_KEY non fa nulla. Errori e quota esaurita non fermano il giro.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import time

import httpx

from . import db
from .extract import page_text, parse_deadline

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
# alias "latest" di Google, poi un modello fisso come riserva; RADAR_GEMINI_MODEL li scavalca
DEFAULT_MODELS = ("gemini-flash-lite-latest", "gemini-flash-latest", "gemini-2.5-flash-lite")
PER_RUN = 30            # posizioni valutate per giro (il resto al giro dopo)
MIN_INTERVAL = 6.0      # secondi tra due chiamate: resta sotto i 10 RPM del piano gratuito
MAX_TRIES = 3           # tentativi per posizione prima di lasciarla senza voto
TEXT_LIMIT = 8000       # caratteri della pagina mandati al modello

SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "score": {"type": "INTEGER", "description": "pertinenza col profilo, da 0 a 10"},
        "reason": {"type": "STRING", "description": "perché quel voto, max 25 parole, in italiano"},
        "summary": {"type": "STRING", "description": "cosa farebbe il dottorando, 2-3 frasi in italiano"},
        "tags": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "1-4 etichette brevi in italiano"},
        "supervisor_quote": {"type": "STRING", "nullable": True,
                             "description": "nome del professore referente copiato esattamente dal testo, o null"},
        "deadline_quote": {"type": "STRING", "nullable": True,
                           "description": "frase del testo che contiene la scadenza della candidatura, copiata esattamente, o null"},
    },
    "required": ["score", "reason", "summary", "tags"],
}

PROMPT = """Sei un assistente che valuta annunci di dottorato (PhD) per uno studente.

PROFILO DELLO STUDENTE:
{profile}

ANNUNCIO (ateneo: {uni})
Titolo: {title}
Testo della pagina:
\"\"\"
{text}
\"\"\"

Rispondi in JSON:
- score: pertinenza dell'annuncio col profilo, intero 0-10 (10 = perfetto; 0 = non è un PhD o è fuori tema).
- reason: perché, in una frase breve.
- summary: in 2-3 frasi, di cosa si occupa il progetto. Solo informazioni presenti nel testo.
- tags: 1-4 etichette tematiche brevi (es. "ML + fluidi", "CFD", "turbolenza", "sperimentale", "robotica").
- supervisor_quote: il nome del professore/supervisore copiato ESATTAMENTE dal testo; null se non c'è.
- deadline_quote: la frase con la scadenza per candidarsi copiata ESATTAMENTE dal testo; null se non c'è.
Non inventare nulla che non sia nel testo."""


class QuotaExceeded(Exception):
    pass


def api_key() -> str | None:
    return os.environ.get("RADAR_GEMINI_API_KEY") or None


def profile_hash(profile: str) -> str:
    return hashlib.sha1(profile.encode("utf-8")).hexdigest()[:12]


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def call_gemini(prompt: str, key: str, models: tuple[str, ...], client: httpx.Client) -> tuple[dict, str]:
    """Ritorna (risposta JSON, modello usato). Prova il modello successivo se uno non esiste."""
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "responseSchema": SCHEMA, "temperature": 0.2},
    }
    last = None
    for model in models:
        r = client.post(API.format(model=model), json=body, headers={"x-goog-api-key": key})
        if r.status_code == 429:
            raise QuotaExceeded(r.text[:200])
        if r.status_code == 404:
            last = f"modello {model} non disponibile"
            continue
        r.raise_for_status()
        parts = r.json()["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
        return json.loads(text), model
    raise RuntimeError(last or "nessun modello")


def clean(raw: dict, source_text: str) -> dict:
    """Controlla e ripulisce la risposta del modello. Citazioni non presenti nel testo vengono scartate."""
    try:
        score = max(0, min(10, int(raw.get("score"))))
    except (TypeError, ValueError):
        score = None
    tags = [str(t).strip()[:30] for t in (raw.get("tags") or []) if str(t).strip()][:4]
    hay = _norm(source_text)

    sup = raw.get("supervisor_quote")
    sup = str(sup).strip() if sup else None
    if sup and (len(sup) > 80 or _norm(sup) not in hay):
        sup = None

    dl_quote = raw.get("deadline_quote")
    deadline = None
    if dl_quote and _norm(str(dl_quote)) in hay:
        deadline = parse_deadline(str(dl_quote))

    return {
        "score": score,
        "reason": str(raw.get("reason") or "").strip()[:300] or None,
        "summary": str(raw.get("summary") or "").strip()[:600] or None,
        "tags": tags,
        "supervisor": sup,
        "deadline": deadline,
    }


def enrich(con: sqlite3.Connection, fetcher, profile: str, key: str | None = None,
           client: httpx.Client | None = None, sleep=time.sleep, per_run: int = PER_RUN) -> int:
    """Valuta fino a per_run posizioni. Ritorna quante ne ha valutate."""
    key = key or api_key()
    if not key or not profile:
        return 0
    env_model = os.environ.get("RADAR_GEMINI_MODEL")
    models = (env_model,) if env_model else DEFAULT_MODELS
    client = client or httpx.Client(timeout=60)
    ph = profile_hash(profile)
    rows = con.execute(
        "SELECT url, uni, title, snippet FROM positions WHERE active = 1"
        " AND (ai_profile IS NULL OR ai_profile != ?) AND ai_tries < ? ORDER BY first_seen DESC LIMIT ?",
        (ph, MAX_TRIES, per_run)).fetchall()
    done, last_call = 0, 0.0
    for r in rows:
        text = f"{r['title']}\n{r['snippet'] or ''}"
        url = r["url"]
        if "#" not in url and not url.lower().endswith((".pdf", ".doc", ".docx")):
            html = fetcher(url)
            if html:
                text += "\n" + page_text(html)
        text = text[:TEXT_LIMIT]
        wait = MIN_INTERVAL - (time.monotonic() - last_call)
        if last_call and wait > 0:
            sleep(wait)
        last_call = time.monotonic()
        try:
            raw, model = call_gemini(PROMPT.format(profile=profile, uni=r["uni"], title=r["title"], text=text),
                                     key, models, client)
            res = clean(raw, text)
        except QuotaExceeded as e:
            print(f"[ai] quota Gemini esaurita, riprovo al prossimo giro: {e}")
            break
        except Exception as e:  # risposta malformata, rete, modello: si riprova al giro dopo
            print(f"[ai] errore su {url}: {e}")
            con.execute("UPDATE positions SET ai_tries = ai_tries + 1 WHERE url = ?", (url,))
            continue
        con.execute(
            "UPDATE positions SET ai_score = ?, ai_reason = ?, ai_summary = ?, ai_tags = ?, ai_model = ?,"
            " ai_profile = ?, ai_at = ?, ai_tries = 0,"
            " supervisor = COALESCE(supervisor, ?), deadline = COALESCE(deadline, ?) WHERE url = ?",
            (res["score"], res["reason"], res["summary"], json.dumps(res["tags"], ensure_ascii=False), model,
             ph, db.now(), res["supervisor"], res["deadline"].isoformat() if res["deadline"] else None, url))
        con.commit()  # salva subito: se il giro si interrompe le valutazioni fatte restano
        done += 1
    return done
