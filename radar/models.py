from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

SourceType = Literal["listing", "info"]
AlertKind = Literal["new_position", "deadline_soon", "page_changed"]


@dataclass
class Source:
    uni: str
    name: str
    url: str
    type: SourceType
    verified: bool = False
    selector: str | None = None


@dataclass
class Candidate:
    """Annuncio trovato in una pagina listing (non ancora salvato)."""
    uni: str
    title: str
    url: str
    source_url: str
    snippet: str = ""
    deadline: date | None = None
    matched_keywords: list[str] = field(default_factory=list)


@dataclass
class Alert:
    kind: AlertKind
    uni: str
    text: str
    url: str
