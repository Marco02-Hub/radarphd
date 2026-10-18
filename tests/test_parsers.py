from datetime import date
from pathlib import Path

from radar.extract import find_candidates, parse_deadline
from radar.models import Source
from radar.parsers import parser_for
from radar.parsers.jobs_ac_uk import closing_date
from radar.parsers import jobs_ac_uk

FIX = Path(__file__).parent / "fixtures"
KW = ["fluid", "energy", "aerospace", "mechanical engineering", "robotics"]
MK = ["phd", "ph.d", "doctoral", "doctorate", "dphil", "studentship"]


def _html(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


def test_generic_skips_postdocs():
    html = """<ul>
      <li><a href="/1">Postdoctoral Researcher in Fluid Dynamics</a></li>
      <li><a href="/2">Research Associate in robotics, PhD required</a></li>
      <li><a href="/3">Doctoral Student in Fluid Mechanics</a></li></ul>"""
    src = Source(uni="ETH", name="t", url="https://x.org/", type="listing")
    assert [c.url for c in find_candidates(html, src, KW, MK)] == ["https://x.org/3"]


def test_parse_deadline_ordinal():
    assert parse_deadline("Deadline: 2nd December 2026") == date(2026, 12, 2)


def test_oxford_studentships_and_projects():
    src = Source(uni="Oxford", name="t", url="https://eng.ox.ac.uk/study/research-studentships", type="listing")
    out = parser_for(src)(_html("oxford_eng_studentships.html"), src, KW, MK)
    studs = [c for c in out if "/research-studentships/" in c.url]
    assert len(studs) == 5
    assert studs[0].title == "Research Studentship in Control and Engineering Biology"
    assert all(c.deadline == date(2026, 12, 2) for c in studs)
    projects = [c for c in out if c not in studs]
    assert len(projects) == 2
    assert projects[0].title.startswith("Thermomigration of Hydrogen")
    assert projects[0].url.startswith("https://www.materials.ox.ac.uk/article/")
    assert projects[0].deadline is None  # sotto un titolo senza scadenza: non si inventa


def test_imperial_aero_funded_only():
    src = Source(uni="Imperial", name="t", type="listing",
                 url="https://www.imperial.ac.uk/aeronautics/study/phd/phd-opportunities-and-funding/")
    out = parser_for(src)(_html("imperial_aero_opportunities.html"), src, KW, MK)
    assert [c.title for c in out] == ["Computational Simulation Driven In-Vivo Microvascular Characterisation"]
    assert out[0].deadline == date(2026, 5, 26)
    assert out[0].url.endswith(".docx")
    assert "Supervisors" in out[0].snippet


def test_jobs_ac_uk_phd_with_keyword():
    src = Source(uni="UK", name="t", type="listing",
                 url="https://www.jobs.ac.uk/search/?keywords=phd+mechanical+engineering")
    out = jobs_ac_uk.parse(_html("jobs_ac_uk_mechanical.html"), src, KW, MK, today=date(2026, 10, 18))
    assert [c.title[:40] for c in out] == ["PhD Studentship - Dynamic Performance an"]
    assert out[0].deadline == date(2027, 1, 12)  # "Expires 12 Jan" -> prossimo 12 gennaio
    assert out[0].matched_keywords == ["energy"]


def test_closing_date_year_rollover():
    assert closing_date("Closes 15 Nov", date(2026, 10, 18)) == date(2026, 11, 15)
    assert closing_date("Closes 06 Jan", date(2026, 10, 18)) == date(2027, 1, 6)
    assert closing_date("Date Placed: 13 Oct", date(2026, 10, 18)) is None
