"""Estrazione generica. Parser specifici per sito andranno in radar/parsers/."""
from __future__ import annotations

import hashlib
import re
from datetime import date
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .models import Candidate, Source

MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"], start=1)}
MONTHS.update({k[:3]: v for k, v in list(MONTHS.items())})

# "1 December 2026", "2nd Dec 2026", "December 1, 2026", "2026-12-01"
_DMY = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3,9})\.?\s+(\d{4})\b")
_MDY = re.compile(r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,\s*(\d{4})\b")
# Titoli che non sono posizioni di dottorato anche se citano "PhD" (es. "PhD required").
NOT_PHD_TITLE = re.compile(r"post-?doc|research (assistant|associate|fellow)|lecturer|professor", re.I)
# Testi di link che sono un indirizzo, non il titolo di un annuncio.
_NOT_A_TITLE = re.compile(r"^(https?://|www\.)|^\S+@\S+$", re.I)
_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_DEADLINE_HINT = re.compile(r"(deadline|closing date|apply by|application[s]? close)", re.I)


def _scope(html: str, selector: str | None) -> BeautifulSoup:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header"]):
        tag.decompose()
    if selector:
        part = soup.select_one(selector)
        if part is not None:
            return part
    return soup


def page_text(html: str, selector: str | None = None) -> str:
    text = _scope(html, selector).get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text)


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_deadline(text: str) -> date | None:
    """Cerca una data vicino a parole come 'deadline'. Ritorna None se incerta."""
    m = _DEADLINE_HINT.search(text)
    window = text[m.start(): m.start() + 120] if m else ""
    if not window:
        return None
    for rx, order in ((_ISO, "ymd"), (_DMY, "dmy"), (_MDY, "mdy")):
        hit = rx.search(window)
        if not hit:
            continue
        try:
            if order == "ymd":
                y, mo, d = map(int, hit.groups())
            elif order == "dmy":
                d, mon, y = hit.groups()
                mo, d, y = MONTHS[mon.lower()], int(d), int(y)
            else:
                mon, d, y = hit.groups()
                mo, d, y = MONTHS[mon.lower()], int(d), int(y)
            return date(y, mo, d)
        except (KeyError, ValueError):
            continue
    return None


def matched_keywords(text: str, keywords: list[str]) -> list[str]:
    low = text.lower()
    return [k for k in keywords if k in low]


def find_candidates(html: str, source: Source, keywords: list[str], markers: list[str]) -> list[Candidate]:
    """Link il cui testo (o il blocco attorno) parla di PhD e contiene una parola chiave."""
    root = _scope(html, source.selector)
    # parola intera: "doctoral" non deve scattare dentro "postdoctoral"
    marker_rx = re.compile(r"\b(" + "|".join(re.escape(m) for m in markers) + r")", re.I)
    seen: set[str] = set()
    out: list[Candidate] = []
    for a in root.find_all("a", href=True):
        title = a.get_text(" ", strip=True)
        if len(title) < 12 or NOT_PHD_TITLE.search(title) or _NOT_A_TITLE.search(title):
            continue
        if a["href"].lower().startswith(("mailto:", "tel:", "javascript:")):
            continue
        block = a.find_parent(["li", "article", "tr", "div"]) or a
        context = re.sub(r"\s+", " ", block.get_text(" ", strip=True))[:600]
        low = (title + " " + context).lower()
        if not marker_rx.search(low):
            continue
        hits = matched_keywords(low, keywords)
        if not hits:
            continue
        url = urljoin(source.url, a["href"])
        if url in seen:
            continue
        seen.add(url)
        out.append(Candidate(
            uni=source.uni, title=title, url=url, source_url=source.url,
            snippet=context[:280], deadline=parse_deadline(context), matched_keywords=hits,
        ))
    return out
