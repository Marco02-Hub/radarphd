from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from . import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS positions (
  url          TEXT PRIMARY KEY,
  uni          TEXT NOT NULL,
  title        TEXT NOT NULL,
  snippet      TEXT,
  deadline     TEXT,              -- ISO date o NULL
  keywords     TEXT,              -- separati da virgola
  source_url   TEXT NOT NULL,
  first_seen   TEXT NOT NULL,
  last_checked TEXT NOT NULL,
  active       INTEGER NOT NULL DEFAULT 1,
  saved        INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS pages (
  url          TEXT PRIMARY KEY,
  uni          TEXT NOT NULL,
  hash         TEXT NOT NULL,
  last_checked TEXT NOT NULL,
  last_changed TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS alerts (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  kind       TEXT NOT NULL,
  uni        TEXT NOT NULL,
  text       TEXT NOT NULL,
  url        TEXT NOT NULL,
  created_at TEXT NOT NULL,
  read       INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS deadline_alerts_sent (
  url  TEXT NOT NULL,
  days INTEGER NOT NULL,
  PRIMARY KEY (url, days)
);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    cols = {r["name"] for r in con.execute("PRAGMA table_info(positions)")}
    for col, decl in (("supervisor", "TEXT"), ("detail_checked", "INTEGER NOT NULL DEFAULT 0"),
                      # valutazione Gemini (radar/ai.py)
                      ("ai_score", "INTEGER"), ("ai_reason", "TEXT"), ("ai_summary", "TEXT"), ("ai_tags", "TEXT"),
                      ("ai_model", "TEXT"), ("ai_profile", "TEXT"), ("ai_at", "TEXT"),
                      ("ai_tries", "INTEGER NOT NULL DEFAULT 0")):
        if col not in cols:  # migrazione dei DB creati prima del campo
            con.execute(f"ALTER TABLE positions ADD COLUMN {col} {decl}")
    return con
