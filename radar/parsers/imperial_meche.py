"""Imperial Mechanical Engineering — "Current PhD studentships".

Ogni studentship è una scheda a tendina: <a href="#tabpanel_N">Titolo</a> apre il pannello id="tabpanel_N"
con descrizione, contatti e (a volte) scadenza. Sono tutte studentship di dottorato del dipartimento.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from ..extract import find_supervisor, matched_keywords, parse_deadline, supervisor_from_title
from ..models import Candidate, Source


def parse(html: str, source: Source, keywords: list[str], markers: list[str]) -> list[Candidate]:
    soup = BeautifulSoup(html, "html.parser")
    root = soup.select_one("main") or soup
    base = source.url.split("#")[0]
    # qui gli annunci si chiamano sempre "PhD Studentship ..."; "Centres for Doctoral Training" è un'altra scheda
    marker_rx = re.compile(r"\bphd\b|studentship", re.I)
    out: list[Candidate] = []
    seen: set[str] = set()
    for a in root.select('a[href^="#tabpanel_"]'):
        anchor = a["href"][1:]
        title = re.sub(r"\s+", " ", a.get_text(" ", strip=True))
        if anchor in seen or not marker_rx.search(title):  # altre schede: "Research groups", "SKF UTC"...
            continue
        seen.add(anchor)
        panel = soup.find(id=anchor)
        body = re.sub(r"\s+", " ", panel.get_text(" ", strip=True)) if panel else ""
        out.append(Candidate(
            uni=source.uni, title=title, url=f"{base}#{anchor}", source_url=source.url,
            snippet=body[:280], deadline=parse_deadline(body),
            matched_keywords=matched_keywords(title + " " + body, keywords),
            supervisor=supervisor_from_title(title) or find_supervisor(body),
        ))
    return out
