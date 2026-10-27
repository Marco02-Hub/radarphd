"""Estrazione generica. Parser specifici per sito andranno in radar/parsers/."""
from __future__ import annotations

import hashlib
import re
from functools import lru_cache
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


@lru_cache(maxsize=512)
def _keyword_rx(k: str) -> re.Pattern:
    # inizio di parola sempre ("energy" non scatta in "synergy"); le sigle corte anche a fine parola ("ai" non in "aim")
    end = r"\b" if len(k) <= 3 else ""
    return re.compile(r"\b" + re.escape(k) + end, re.I)


def matched_keywords(text: str, keywords: list[str]) -> list[str]:
    return [k for k in keywords if _keyword_rx(k).search(text)]


def topics(keywords: list[str], groups: dict[str, list[str]]) -> list[str]:
    """Gruppi di parole chiave toccati da una posizione; "ml+fluidi" se ci sono entrambi."""
    found = [g for g, words in groups.items() if any(k in words for k in keywords)]
    if "ml" in found and "fluidi" in found:
        found.insert(0, "ml+fluidi")
    return found


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


# ---- professore referente (solo se scritto nella pagina) ----
_UP = r"[A-ZÀ-ÖØ-Þ][\w'’.-]*"
_NAME = (r"(?:Prof(?:essor)?\.?|Dr\.?)\s+(?:Dr\.?\s+)?" + _UP +
         r"(?:\s+(?:" + _UP + r"|de|van|von|der|di|da|del))*")
_NAME_RX = re.compile(_NAME)
# parole maiuscole che seguono spesso un nome ma non ne fanno parte
_STOP = {"in", "this", "the", "we", "our", "at", "and", "department", "university", "school", "institute",
         "faculty", "group", "lab", "laboratory", "research", "questions", "for", "of", "is", "will", "with",
         "nhli", "aeronautics", "imperial", "college", "eth", "epfl", "london", "zurich", "oxford", "cambridge"}
_CUES = [  # in ordine di affidabilità
    re.compile(r"supervis(?:ory team|ion team|ors|or)(?:\s*\(s\))?\s*:?\s*", re.I),
    re.compile(r"(?:led by|headed by|group of|lab(?:oratory)? of|under the supervision of)\s+", re.I),
    re.compile(r"contact(?: the supervisors?)?\s*:?\s*", re.I),
]


_TITLE_WORD = re.compile(r"(?:Prof(?:essor)?|Dr)\.?")
# parola di un nome: "Steel", "Martínez-Pañeda", "O’Neil", iniziale "B."; non "Next-generation" né "a.b@x"
_NAME_WORD = re.compile(r"[A-ZÀ-ÖØ-Þ](?:\.|[a-zà-öø-ÿ'’]+(?:-[A-ZÀ-ÖØ-Þ][a-zà-öø-ÿ'’]+)*)|de|van|von|der|di|da|del")


def _clean_name(raw: str, after: str = "") -> str | None:
    words = []
    for w in raw.split():
        if not words or _TITLE_WORD.fullmatch(w):
            words.append(w)
            continue
        w = re.sub(r"[’']s$", "", w.rstrip(",-"))  # "Mann’s" -> "Mann", "Dimitriou-" -> "Dimitriou"
        if not _NAME_WORD.fullmatch(w) or w.lower() in _STOP:
            break
        words.append(w)
    while words and words[-1].lower() in ("de", "van", "von", "der", "di", "da", "del"):
        words.pop()
    surnames = [w for w in words if not _TITLE_WORD.fullmatch(w)]
    # "Prof Laurence Brassart Many researchers": nome lungo seguito da minuscola -> l'ultima parola apre la frase
    if len(surnames) >= 3 and len(words) == len(raw.split()) and re.match(r"\s+[a-zà-ÿ]", after):
        words.pop()
        surnames.pop()
    return " ".join(words) if surnames and len(words) >= 2 else None  # "Prof" da solo non è un nome


def find_supervisor(text: str) -> str | None:
    """Nome/i del professore referente dal testo dell'annuncio, o None se non indicato."""
    for cue in _CUES:
        for m in cue.finditer(text):
            window = text[m.end(): m.end() + 160]
            names = []
            last = 0
            for n in _NAME_RX.finditer(window):
                if n.start() - last > (6 if not names else 60):  # primo nome subito dopo la parola chiave,
                    break                                        # i successivi vicini ("Prof A and Prof B")
                name = _clean_name(n.group(0), window[n.end():n.end() + 20])
                if name and name not in names:
                    names.append(name)
                last = n.end()
            if names:
                return " · ".join(names[:3])
    m = re.search(r"Prof(?:essor)?\.?\s+" + _UP + r"(?:\s+" + _UP + r")*", text)  # ultimo tentativo: primo "Prof."
    return _clean_name(m.group(0), text[m.end():m.end() + 20]) if m else None


def supervisor_from_title(title: str) -> str | None:
    """Convenzione di alcuni siti: '... (Prof Aleiferis)' o '... (Janet Wong)' in fondo al titolo."""
    m = re.search(r"\(([^()]{3,80})\)\s*$", title)
    if not m:
        return None
    inner = m.group(1).strip()
    titled = re.match(r"(?:Prof(?:essor)?|Dr)\.?\s", inner)
    parts = re.split(r"\s*(?:&|,| and )\s*", re.sub(r"^(?:Prof(?:essor)?|Dr)\.?\s+", "", inner))
    looks_like_names = all(p and all(_NAME_WORD.fullmatch(w) for w in p.split()) for p in parts)
    if looks_like_names and (titled or " " in parts[0]):  # "(EAF)", "(EV and Energy Storage)" esclusi
        return inner
    return None
