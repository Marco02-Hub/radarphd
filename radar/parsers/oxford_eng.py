"""Oxford Engineering Science — pagina "Research studentships".

La pagina è un unico blocco di <p> sotto titoli <h3>:
- "Deadline: <data>" seguito dai link "Research Studentship in ..." (titoli senza parole chiave);
- "Research projects ..." con progetti: <p><strong>Titolo</strong> (supervisori)</p>, descrizione,
  "For further details see: <url>".
Tutte le voci sono dottorati di ingegneria, quindi si prendono tutte (l'app filtra per parole chiave).
"""
from __future__ import annotations

import re
from datetime import date
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..extract import matched_keywords, parse_deadline
from ..models import Candidate, Source

_URL = re.compile(r"https?://\S+")


def parse(html: str, source: Source, keywords: list[str], markers: list[str]) -> list[Candidate]:
    soup = BeautifulSoup(html, "html.parser")
    root = soup.select_one("main .usercontent") or soup.select_one("main") or soup
    out: list[Candidate] = []
    deadline: date | None = None
    project: Candidate | None = None

    for el in root.find_all(["h2", "h3", "p"], recursive=False):
        text = re.sub(r"\s+", " ", el.get_text(" ", strip=True))
        if not text:
            continue
        if el.name in ("h2", "h3"):
            deadline = parse_deadline(text)  # None per titoli senza scadenza: non si eredita
            project = None
            continue

        link = el.find("a", href=re.compile(r"/research-studentships/."))
        if link is not None:
            title = link.get_text(" ", strip=True)
            out.append(Candidate(
                uni=source.uni, title=title, url=urljoin(source.url, link["href"]),
                source_url=source.url, snippet=title, deadline=deadline,
                matched_keywords=matched_keywords(title, keywords),
            ))
            continue

        strong = el.find("strong")
        if strong is not None and strong.get_text(strip=True):
            # nuovo progetto: URL ancora ignoto, arriva con "For further details see:"
            project = Candidate(uni=source.uni, title=strong.get_text(" ", strip=True), url="",
                                source_url=source.url, deadline=deadline)
            continue

        if project is None:
            continue
        if text.lower().startswith("for further details"):
            a = el.find("a", href=True)
            m = _URL.search(text)
            href = a["href"] if a is not None else (m.group(0) if m else None)
            if href:
                project.url = urljoin(source.url, href)
                project.matched_keywords = matched_keywords(project.title + " " + project.snippet, keywords)
                out.append(project)
            project = None
        elif not project.snippet:
            project.snippet = text[:280]

    seen: set[str] = set()
    return [c for c in out if not (c.url in seen or seen.add(c.url))]
