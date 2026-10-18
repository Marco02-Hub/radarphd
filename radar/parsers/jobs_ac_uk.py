"""jobs.ac.uk — pagina risultati di ricerca (25 per pagina, ordinati per data).

Ogni risultato è un div.j-search-result__result con titolo, ente e "Closes 15 Nov" o "Expires 12 Jan" (senza anno).
Si tengono solo i risultati col marker PhD nel titolo e almeno una parola chiave nel testo.
"""
from __future__ import annotations

import re
from datetime import date
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..extract import MONTHS, NOT_PHD_TITLE, matched_keywords
from ..models import Candidate, Source

_CLOSES = re.compile(r"\b(?:Closes|Expires)\s+(\d{1,2})\s+([A-Za-z]{3,9})\b")


def closing_date(text: str, today: date) -> date | None:
    """La pagina non indica l'anno: si prende la prima occorrenza a partire da oggi
    (un annuncio ancora in elenco non è già scaduto da mesi)."""
    m = _CLOSES.search(text)
    if not m or m.group(2).lower() not in MONTHS:
        return None
    d, mo = int(m.group(1)), MONTHS[m.group(2).lower()]
    for y in (today.year, today.year + 1):
        try:
            cand = date(y, mo, d)
        except ValueError:
            return None
        if cand >= today:
            return cand
    return None


def parse(html: str, source: Source, keywords: list[str], markers: list[str],
          today: date | None = None) -> list[Candidate]:
    today = today or date.today()
    soup = BeautifulSoup(html, "html.parser")
    marker_rx = re.compile(r"\b(" + "|".join(re.escape(m) for m in markers) + r")", re.I)
    out: list[Candidate] = []
    for res in soup.select(".j-search-result__result"):
        a = res.select_one(".j-search-result__text a[href]") or res.find("a", href=True)
        if a is None:
            continue
        title = a.get_text(" ", strip=True)
        if not marker_rx.search(title) or NOT_PHD_TITLE.search(title):
            continue
        text = re.sub(r"\s+", " ", res.get_text(" ", strip=True))
        hits = matched_keywords(text, keywords)
        if not hits:
            continue
        out.append(Candidate(
            uni=source.uni, title=title, url=urljoin(source.url, a["href"]), source_url=source.url,
            snippet=text.replace(" Save", "")[:280], deadline=closing_date(text, today),
            matched_keywords=hits,
        ))
    return out
