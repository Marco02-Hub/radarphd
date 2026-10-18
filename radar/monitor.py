"""Un giro di monitoraggio: scarica, confronta, salva, genera avvisi."""
from __future__ import annotations

import sqlite3
from datetime import date

from . import db
from .config import load_sources
from .extract import page_text, text_hash
from .fetch import fetch
from .models import Alert, Candidate, Source
from .parsers import parser_for

DEADLINE_REMINDERS_DAYS = (14, 3)


def _upsert_candidate(con: sqlite3.Connection, c: Candidate) -> bool:
    """Ritorna True se la posizione è nuova."""
    ts = db.now()
    row = con.execute("SELECT url FROM positions WHERE url = ?", (c.url,)).fetchone()
    if row:
        con.execute(
            "UPDATE positions SET last_checked = ?, active = 1, deadline = COALESCE(?, deadline) WHERE url = ?",
            (ts, c.deadline.isoformat() if c.deadline else None, c.url),
        )
        return False
    con.execute(
        "INSERT INTO positions (url, uni, title, snippet, deadline, keywords, source_url, first_seen, last_checked)"
        " VALUES (?,?,?,?,?,?,?,?,?)",
        (c.url, c.uni, c.title, c.snippet, c.deadline.isoformat() if c.deadline else None,
         ",".join(c.matched_keywords), c.source_url, ts, ts),
    )
    return True


def _check_info_page(con: sqlite3.Connection, src: Source, html: str) -> Alert | None:
    h = text_hash(page_text(html, src.selector))
    ts = db.now()
    row = con.execute("SELECT hash FROM pages WHERE url = ?", (src.url,)).fetchone()
    if row is None:
        con.execute("INSERT INTO pages VALUES (?,?,?,?,?)", (src.url, src.uni, h, ts, ts))
        return None  # primo giro: memorizza senza avvisare
    if row["hash"] == h:
        con.execute("UPDATE pages SET last_checked = ? WHERE url = ?", (ts, src.url))
        return None
    con.execute("UPDATE pages SET hash = ?, last_checked = ?, last_changed = ? WHERE url = ?", (h, ts, ts, src.url))
    return Alert("page_changed", src.uni, f"{src.uni}: pagina modificata — {src.name}", src.url)


def _deadline_alerts(con: sqlite3.Connection, today: date) -> list[Alert]:
    out = []
    rows = con.execute("SELECT url, uni, title, deadline FROM positions WHERE active = 1 AND deadline IS NOT NULL")
    for r in rows.fetchall():
        days = (date.fromisoformat(r["deadline"]) - today).days
        for d in DEADLINE_REMINDERS_DAYS:
            if 0 <= days <= d:
                done = con.execute("SELECT 1 FROM deadline_alerts_sent WHERE url=? AND days=?", (r["url"], d)).fetchone()
                if not done:
                    con.execute("INSERT INTO deadline_alerts_sent VALUES (?,?)", (r["url"], d))
                    out.append(Alert("deadline_soon", r["uni"], f"{r['uni']}: «{r['title']}» scade tra {days} giorni", r["url"]))
                break
    return out


def run_once(con: sqlite3.Connection | None = None, fetcher=fetch) -> list[Alert]:
    con = con or db.connect()
    sources, keywords, markers = load_sources()
    alerts: list[Alert] = []
    for src in sources:
        html = fetcher(src.url)
        if html is None:
            continue
        if src.type == "listing":
            ts = db.now()
            con.execute("INSERT INTO pages VALUES (?,?,?,?,?) ON CONFLICT(url) DO UPDATE SET last_checked = ?",
                        (src.url, src.uni, text_hash(page_text(html, src.selector)), ts, ts, ts))
            for c in parser_for(src)(html, src, keywords, markers):
                if _upsert_candidate(con, c):
                    alerts.append(Alert("new_position", c.uni, f"Nuova posizione {c.uni}: {c.title}", c.url))
        else:
            a = _check_info_page(con, src, html)
            if a:
                alerts.append(a)
    alerts += _deadline_alerts(con, date.today())
    for a in alerts:
        con.execute("INSERT INTO alerts (kind, uni, text, url, created_at) VALUES (?,?,?,?,?)",
                    (a.kind, a.uni, a.text, a.url, db.now()))
    con.commit()
    return alerts
