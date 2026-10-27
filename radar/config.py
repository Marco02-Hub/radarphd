from __future__ import annotations

from pathlib import Path

import yaml

from . import CONFIG_DIR
from .models import Source


def load_sources(path: Path = CONFIG_DIR / "sources.yaml") -> tuple[list[Source], list[str], list[str]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    sources = [Source(**s) for s in data.get("sources", [])]
    keywords = [k for group in keyword_groups(data).values() for k in group]
    markers = [m.lower() for m in data.get("phd_markers", [])]
    return sources, keywords, markers


def keyword_groups(data: dict) -> dict[str, list[str]]:
    """Parole chiave per gruppo (minuscole). Accetta anche il vecchio formato a lista unica."""
    kw = data.get("keywords") or {}
    if isinstance(kw, list):
        kw = {"altro": kw}
    out: dict[str, list[str]] = {}
    for group, words in kw.items():
        out[group] = list(dict.fromkeys(str(w).lower() for w in (words or [])))
    return out


def load_keyword_groups(path: Path = CONFIG_DIR / "sources.yaml") -> dict[str, list[str]]:
    return keyword_groups(yaml.safe_load(path.read_text(encoding="utf-8")))


def load_profile(path: Path = CONFIG_DIR / "sources.yaml") -> str:
    return " ".join(str(yaml.safe_load(path.read_text(encoding="utf-8")).get("profilo") or "").split())


def load_universities(path: Path = CONFIG_DIR / "universities.yaml") -> list[dict]:
    return yaml.safe_load(path.read_text(encoding="utf-8")).get("universities", [])
