from datetime import date

from radar import db
from radar.extract import find_candidates, parse_deadline, page_text
from radar.models import Source
from radar.monitor import run_once

LISTING = """
<html><body><ul>
  <li><a href="/job/1">PhD position in aeroelastic modelling of flexible wings</a>
      Application deadline: 1 December 2026</li>
  <li><a href="/job/2">Postdoc in turbulence modelling</a></li>
  <li><a href="/job/3">PhD student in organic chemistry synthesis</a></li>
</ul></body></html>
"""
SRC = Source(uni="ETH", name="test", url="https://example.org/jobs", type="listing")
KW = ["aeroelastic", "turbulence"]
MK = ["phd", "doctoral"]


def test_candidates_filtered_by_phd_and_keyword():
    out = find_candidates(LISTING, SRC, KW, MK)
    assert [c.url for c in out] == ["https://example.org/job/1"]
    assert out[0].deadline == date(2026, 12, 1)
    assert out[0].matched_keywords == ["aeroelastic"]


def test_parse_deadline_formats():
    assert parse_deadline("Closing date: 2027-01-05") == date(2027, 1, 5)
    assert parse_deadline("Apply by December 15, 2026 at noon") == date(2026, 12, 15)
    assert parse_deadline("Starts 1 March 2027") is None  # nessuna parola 'deadline'


def test_page_text_ignores_scripts():
    assert page_text("<p>Hi</p><script>x=1</script>") == "Hi"


def test_run_once_detects_new_then_nothing(tmp_path):
    con = db.connect(tmp_path / "t.sqlite")
    fake = lambda url: LISTING if "jobs.ethz.ch" in url else "<p>info page v1</p>"
    first = run_once(con, fetcher=fake)
    assert any(a.kind == "new_position" for a in first)
    assert not any(a.kind == "page_changed" for a in first)  # primo giro: solo memorizza

    second = run_once(con, fetcher=fake)
    assert not any(a.kind == "new_position" for a in second)

    changed = lambda url: LISTING if "jobs.ethz.ch" in url else "<p>info page v2</p>"
    third = run_once(con, fetcher=changed)
    assert any(a.kind == "page_changed" for a in third)


def test_export_writes_json(tmp_path):
    import json
    from radar.export import export
    con = db.connect(tmp_path / "t.sqlite")
    run_once(con, fetcher=lambda url: LISTING if "jobs.ethz.ch" in url else "<p>x</p>")
    export(con, tmp_path / "out")
    pos = json.loads((tmp_path / "out" / "positions.json").read_text())
    unis = json.loads((tmp_path / "out" / "universities.json").read_text())
    assert pos[0]["uni"] == "ETH" and pos[0]["keywords"] == ["aeroelastic"]
    assert len(unis) == 9 and next(u for u in unis if u["id"] == "ETH")["open_count"] == 1


def test_universities_have_sources():
    import re
    from radar.config import load_universities
    for u in load_universities():
        assert u["summary_source"].startswith("https://") and u["steps_source"].startswith("https://")
        for item in u["deadlines"] + u["contacts"]:
            assert item["source"].startswith("https://"), (u["id"], item)
        for d in u["deadlines"]:
            assert d["recurring"] is None or re.fullmatch(r"\d\d-\d\d", d["recurring"])
