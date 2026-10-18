"""Imperial Aeronautics — "PhD opportunities and funding".

Le offerte stanno tra l'<h2> "Funded PhD opportunities" e l'<h2> successivo, come:
  <p>Title: <a href="...docx">Titolo</a></p>  <p>Deadline: 26/05/2026</p>  <p>Supervisors: ...</p>
Le date sono nel formato britannico gg/mm/aaaa.
"""
from __future__ import annotations

import re
from datetime import date
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..extract import matched_keywords
from ..models import Candidate, Source

_DATE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")


def _dmy(text: str) -> date | None:
    m = _DATE.search(text)
    if not m:
        return None
    d, mo, y = map(int, m.groups())
    try:
        return date(y, mo, d)
    except ValueError:
        return None


def parse(html: str, source: Source, keywords: list[str], markers: list[str]) -> list[Candidate]:
    soup = BeautifulSoup(html, "html.parser")
    root = soup.select_one("main") or soup
    start = next((h for h in root.find_all("h2") if "funded phd" in h.get_text(" ", strip=True).lower()), None)
    if start is None:
        return []
    out: list[Candidate] = []
    cur: Candidate | None = None
    for el in start.find_all_next(["h2", "p"]):
        if el.name == "h2":
            break
        text = re.sub(r"\s+", " ", el.get_text(" ", strip=True))
        low = text.lower()
        if low.startswith("title:"):
            a = el.find("a", href=True)
            title = text.split(":", 1)[1].strip()
            cur = Candidate(uni=source.uni, title=title,
                            url=urljoin(source.url, a["href"]) if a else source.url,
                            source_url=source.url, snippet="")
            out.append(cur)
        elif cur is not None and low.startswith("deadline"):
            cur.deadline = _dmy(text)
        elif cur is not None and low.startswith("supervisor"):
            cur.snippet = text[:280]
    for c in out:
        c.matched_keywords = matched_keywords(c.title + " " + c.snippet, keywords)
    return out
