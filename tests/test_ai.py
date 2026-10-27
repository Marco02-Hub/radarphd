import json
from datetime import date

import httpx

from radar import ai, db
from radar.config import keyword_groups
from radar.extract import matched_keywords, topics


def test_keywords_match_word_starts_and_short_words_whole():
    text = "PhD in AI-driven turbulent flows; main synergy with CFD"
    kws = ["ai", "turbulen", "energy", "cfd", "main"]
    assert matched_keywords(text, kws) == ["ai", "turbulen", "cfd", "main"]
    assert matched_keywords("We aim to train models", ["ai"]) == []
    assert matched_keywords("synergy", ["energy"]) == []


def test_topics_ml_plus_fluids():
    groups = keyword_groups({"keywords": {"fluidi": ["CFD"], "ml": ["Machine Learning"], "altro": ["robotics"]}})
    assert groups["ml"] == ["machine learning"]
    assert topics(["cfd", "machine learning"], groups) == ["ml+fluidi", "fluidi", "ml"]
    assert topics(["robotics"], groups) == ["altro"]
    assert keyword_groups({"keywords": ["A", "b"]}) == {"altro": ["a", "b"]}  # vecchio formato


def test_clean_rejects_quotes_not_in_text():
    text = "Supervisor: Prof. Anna Rossi. Application deadline: 15 January 2027."
    raw = {"score": 14, "reason": "ok", "summary": "s", "tags": ["a", "b", "c", "d", "e"],
           "supervisor_quote": "Prof. Anna Rossi", "deadline_quote": "Application deadline: 15 January 2027"}
    res = ai.clean(raw, text)
    assert res["score"] == 10 and len(res["tags"]) == 4
    assert res["supervisor"] == "Prof. Anna Rossi" and res["deadline"] == date(2027, 1, 15)
    inv = ai.clean({**raw, "supervisor_quote": "Prof. Mario Bianchi", "deadline_quote": "deadline: 1 May 2027"}, text)
    assert inv["supervisor"] is None and inv["deadline"] is None


def _con(tmp_path):
    con = db.connect(tmp_path / "t.sqlite")
    con.execute("INSERT INTO positions (url, uni, title, snippet, source_url, first_seen, last_checked)"
                " VALUES ('https://x.org/job/1','ETH','PhD in ML for turbulence','s','https://x.org','t','t')")
    return con


def _gemini(answer, calls, status=200):
    def handler(req):
        calls.append(req)
        if status != 200:
            return httpx.Response(status, text="quota")
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": json.dumps(answer)}]}}]})
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_enrich_saves_score_once_per_profile(tmp_path):
    con, calls = _con(tmp_path), []
    page = "<p>Supervisor: Prof. Anna Rossi</p>"
    answer = {"score": 9, "reason": "ML e turbolenza", "summary": "Modelli neurali.", "tags": ["ML + fluidi"],
              "supervisor_quote": "Prof. Anna Rossi", "deadline_quote": None}
    client = _gemini(answer, calls)
    n = ai.enrich(con, lambda u: page, "profilo", key="k", client=client, sleep=lambda s: None)
    row = con.execute("SELECT * FROM positions").fetchone()
    assert n == 1 and row["ai_score"] == 9 and json.loads(row["ai_tags"]) == ["ML + fluidi"]
    assert row["supervisor"] == "Prof. Anna Rossi"
    assert calls[0].headers["x-goog-api-key"] == "k"
    assert ai.enrich(con, lambda u: page, "profilo", key="k", client=client, sleep=lambda s: None) == 0
    assert ai.enrich(con, lambda u: page, "profilo nuovo", key="k", client=client, sleep=lambda s: None) == 1


def test_enrich_without_key_or_with_quota_does_nothing(tmp_path, monkeypatch):
    monkeypatch.delenv("RADAR_GEMINI_API_KEY", raising=False)
    con, calls = _con(tmp_path), []
    assert ai.enrich(con, lambda u: "", "profilo", client=_gemini({}, calls)) == 0 and not calls
    assert ai.enrich(con, lambda u: "", "profilo", key="k", client=_gemini({}, calls, 429), sleep=lambda s: None) == 0
    row = con.execute("SELECT ai_score, ai_tries FROM positions").fetchone()
    assert row["ai_score"] is None and row["ai_tries"] == 0  # quota: si riprova al giro dopo senza penalità
