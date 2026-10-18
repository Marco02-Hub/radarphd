"""Parser specifici per sito, usati solo dove l'estrazione generica fallisce.

Ogni parser ha la firma di extract.find_candidates: (html, source, keywords, markers) -> list[Candidate].
"""
from __future__ import annotations

from typing import Callable

from ..extract import find_candidates
from ..models import Candidate, Source
from . import imperial_aero, imperial_meche, jobs_ac_uk, oxford_eng

Parser = Callable[[str, Source, list[str], list[str]], list[Candidate]]

# prefisso URL della fonte -> parser
PARSERS: dict[str, Parser] = {
    "https://eng.ox.ac.uk/study/research-studentships": oxford_eng.parse,
    "https://www.imperial.ac.uk/aeronautics/study/phd/phd-opportunities-and-funding": imperial_aero.parse,
    "https://www.jobs.ac.uk/search": jobs_ac_uk.parse,
    "https://www.imperial.ac.uk/mechanical-engineering/study/phd/phd-opportunities/current-phd-studentships":
        imperial_meche.parse,
}


def parser_for(source: Source) -> Parser:
    for prefix, fn in PARSERS.items():
        if source.url.startswith(prefix):
            return fn
    return find_candidates
