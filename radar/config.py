from __future__ import annotations

from pathlib import Path

import yaml

from . import CONFIG_DIR
from .models import Source


def load_sources(path: Path = CONFIG_DIR / "sources.yaml") -> tuple[list[Source], list[str], list[str]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    sources = [Source(**s) for s in data.get("sources", [])]
    keywords = [k.lower() for k in data.get("keywords", [])]
    markers = [m.lower() for m in data.get("phd_markers", [])]
    return sources, keywords, markers


def load_universities(path: Path = CONFIG_DIR / "universities.yaml") -> list[dict]:
    return yaml.safe_load(path.read_text(encoding="utf-8")).get("universities", [])
