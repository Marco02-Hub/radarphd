"""Download educato: robots.txt, user agent esplicito, pausa per dominio."""
from __future__ import annotations

import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

USER_AGENT = "RadarPhD/0.1 (personal PhD-position monitor)"
MIN_DELAY_S = 5.0

_last_hit: dict[str, float] = {}
_robots: dict[str, RobotFileParser] = {}


def _allowed(url: str, client: httpx.Client) -> bool:
    p = urlparse(url)
    base = f"{p.scheme}://{p.netloc}"
    if base not in _robots:
        rp = RobotFileParser()
        try:
            r = client.get(base + "/robots.txt")
            rp.parse(r.text.splitlines() if r.status_code == 200 else [])
        except httpx.HTTPError:
            rp.parse([])
        _robots[base] = rp
    return _robots[base].can_fetch(USER_AGENT, url)


def fetch(url: str, client: httpx.Client | None = None) -> str | None:
    """Ritorna l'HTML della pagina, o None se vietato/errore."""
    own = client is None
    client = client or httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=20, follow_redirects=True)
    try:
        if not _allowed(url, client):
            print(f"[robots] salto {url}")
            return None
        host = urlparse(url).netloc
        wait = MIN_DELAY_S - (time.monotonic() - _last_hit.get(host, 0))
        if wait > 0:
            time.sleep(wait)
        _last_hit[host] = time.monotonic()
        r = client.get(url)
        r.raise_for_status()
        return r.text
    except httpx.HTTPError as e:
        print(f"[fetch] errore su {url}: {e}")
        return None
    finally:
        if own:
            client.close()
