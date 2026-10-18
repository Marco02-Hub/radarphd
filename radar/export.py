"""Esporta il DB in JSON statici letti dalla web app (docs/data/*.json, servita da GitHub Pages)."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from . import ROOT, db
from .config import load_sources, load_universities

OUT_DIR = ROOT / "docs" / "data"


def _write(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def export(con: sqlite3.Connection, out_dir: Path = OUT_DIR) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    positions = [dict(r) for r in con.execute(
        "SELECT url, uni, title, snippet, deadline, keywords, source_url, first_seen, last_checked"
        " FROM positions WHERE active = 1 ORDER BY first_seen DESC")]
    for p in positions:
        p["keywords"] = [k for k in (p["keywords"] or "").split(",") if k]

    sources, _, _ = load_sources()
    unis = []
    for u in load_universities():
        u = dict(u)
        u["open_count"] = sum(1 for p in positions if p["uni"] == u["id"])
        u["sources"] = []
        for s in (s for s in sources if s.uni == u["id"]):
            row = con.execute("SELECT last_checked FROM pages WHERE url = ?", (s.url,)).fetchone()
            u["sources"].append({"name": s.name, "url": s.url, "type": s.type,
                                 "last_checked": row["last_checked"] if row else None})
        unis.append(u)

    alerts = [dict(r) for r in con.execute(
        "SELECT kind, uni, text, url, created_at FROM alerts ORDER BY id DESC LIMIT 100")]

    _write(out_dir / "positions.json", positions)
    _write(out_dir / "universities.json", unis)
    _write(out_dir / "alerts.json", alerts)
    _write(out_dir / "meta.json", {"updated_at": db.now()})
