"""Reachability + paper-composition reads.

Both replace hardcoded frontend data, so what they must get right is not the
arithmetic — it is refusing to plot a corpus that only LOOKS assessed.

Two shapes exist in production that a naive `GROUP BY observed_difficulty`
would happily chart:

  * all NULL — never assessed. Mains (phase 626ec667…) is 1 131 questions like
    this; 2025 CSAT (phase d813043d…) is 80.
  * uniformly 'medium' — the August 2026 bulk-import default. The CSAT archive
    (phase 1d6611c7…) is 221 questions like this; exam aded8ee9… is ~940.

Neither is distinguishable from a judged paper one row at a time, which is why
eligibility is computed over the whole paper. Verified live 2026-09-03: only
UPSC Prelims GS-I qualifies.

Composition has its OWN eligibility off a different column, and the two must
not be conflated — a paper can be fully tagged and never assessed, or assessed
and untagged.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import exam_intelligence as ei_api
from app.core.auth import get_current_user
from app.exam_intelligence.reachability import (
    ELIGIBLE,
    NOT_ASSESSED,
    UNIFORM,
    UNRECOGNISED,
    classify_paper,
    exam_reachability,
    paper_composition,
    tally_paper,
)
from tests.persona_questions._stub import SBStub, _Query


class _PagedQuery(_Query):
    """SBStub's ``.range()`` is a no-op, so a paginating reader would be
    handed the full result set on every page and loop forever once a
    fixture crosses the 1 000-row page size — which the CSAT archive's 221
    questions on top of the nine GS-I papers does. Honour the range here so
    these tests exercise the real pagination loop instead of dodging it.
    """

    def __init__(self, name, db):
        super().__init__(name, db)
        self._range: tuple[int, int] | None = None

    def range(self, from_n, to_n):
        self._range = (from_n, to_n)
        return self

    def execute(self):
        res = super().execute()
        if self._range and isinstance(res.data, list):
            start, end = self._range
            res.data = res.data[start : end + 1]
        return res


class PagedSB(SBStub):
    def table(self, name: str):
        return _PagedQuery(name, self.db)


# The nine assessed UPSC Prelims GS Paper I papers. 2018-2025 sit under phase
# 715de35f…, 2026 under 6566d50e… — one continuous series across two phase ids,
# which is why the series is enumerated by paper and never gathered by phase.
GS1 = {
    2018: (39, 45, 16),
    2019: (22, 59, 19),
    2020: (18, 50, 32),
    2021: (18, 54, 28),
    2022: (21, 53, 26),
    2023: (17, 55, 28),
    2024: (23, 50, 27),
    2025: (16, 58, 26),
    2026: (10, 56, 34),
}
PHASE_OLD = "715de35f"
PHASE_2026 = "6566d50e"


def _paper(pid, year, phase, code="GS-1", metadata=None):
    return {
        "id": pid,
        "exam_id": "e1",
        "year": year,
        "exam_phase_id": phase,
        "paper_code": code,
        "trust_status": "verified",
        "metadata": metadata or {},
    }


def _questions(pid, spec):
    """`spec` is a list of observed_difficulty values, one per question."""
    return [
        {
            "id": f"{pid}-q{i:04d}",
            "pyq_paper_id": pid,
            "observed_difficulty": d,
            "reviewer_status": "verified",
        }
        for i, d in enumerate(spec)
    ]


def _bands(counts):
    easy, medium, hard = counts
    return ["easy"] * easy + ["medium"] * medium + ["hard"] * hard


def _upsc_db():
    papers, questions = [], []
    for year, counts in GS1.items():
        pid = f"p-gs1-{year}"
        papers.append(_paper(pid, year, PHASE_2026 if year == 2026 else PHASE_OLD))
        questions.extend(_questions(pid, _bands(counts)))
    return {
        "exams": [{"id": "e1", "slug": "upsc-cse"}],
        "exam_phases": [
            {"id": PHASE_OLD, "phase_name": "Prelims", "phase_slug": "prelims"},
            {"id": PHASE_2026, "phase_name": "Prelims", "phase_slug": "prelims-2026"},
        ],
        "pyq_papers": papers,
        "pyq_questions": questions,
        "pyq_question_topic_tags": [],
        "topics": [],
    }


def _client(db):
    sb = PagedSB(db)
    app = FastAPI()
    app.include_router(ei_api.router, prefix="/api")
    ei_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "u-1",
        "role": "user",
        "permissions": [],
    }
    return TestClient(app), sb


# ── Eligibility, unit level ──────────────────────────────────────────────────


def test_all_null_is_never_assessed():
    """Mains: 1 131 questions, every observed_difficulty NULL."""
    assert classify_paper(tally_paper(_questions("p", [None] * 40))) == NOT_ASSESSED


def test_uniform_medium_is_not_a_judgement():
    """The CSAT archive: 221 questions, every one the bulk-import default."""
    assert classify_paper(tally_paper(_questions("p", ["medium"] * 221))) == UNIFORM


def test_a_partly_assessed_paper_is_not_assessed():
    """A judged subset must not be presented as a complete pass — plotting 60
    judged questions out of 100 would silently redraw the paper as smaller."""
    spec = ["easy"] * 30 + ["hard"] * 30 + [None] * 40
    assert classify_paper(tally_paper(_questions("p", spec))) == NOT_ASSESSED


def test_two_distinct_bands_is_the_floor():
    assert classify_paper(tally_paper(_questions("p", ["easy", "hard"]))) == ELIGIBLE
    assert classify_paper(tally_paper(_questions("p", ["easy", "easy"]))) == UNIFORM


def test_an_out_of_vocabulary_value_is_not_a_fourth_band():
    spec = ["easy"] * 10 + ["medium"] * 10 + ["moderate"] * 5
    assert classify_paper(tally_paper(_questions("p", spec))) == UNRECOGNISED


def test_blank_string_counts_as_never_assessed():
    spec = ["easy"] * 10 + ["hard"] * 10 + ["  "]
    assert classify_paper(tally_paper(_questions("p", spec))) == NOT_ASSESSED


def test_band_values_are_normalised_before_counting():
    counts = tally_paper(_questions("p", ["Easy", " HARD ", "medium"]))
    assert (counts["easy"], counts["medium"], counts["hard"]) == (1, 1, 1)
    assert counts["null"] == 0 and counts["other"] == 0


def test_empty_paper_is_not_assessed():
    assert classify_paper(tally_paper([])) == NOT_ASSESSED


# ── Service level ────────────────────────────────────────────────────────────


def test_nine_upsc_papers_including_2025():
    out = exam_reachability(PagedSB(_upsc_db()), "e1")
    got = {p["year"]: (p["easy"], p["medium"], p["hard"]) for p in out["papers"]}
    assert got == GS1
    assert len(out["papers"]) == 9
    # The paper tagged 2026-09-04, which the hardcoded config never showed.
    assert 2025 in got


def test_papers_come_back_oldest_first():
    out = exam_reachability(PagedSB(_upsc_db()), "e1")
    years = [p["year"] for p in out["papers"]]
    assert years == sorted(years)


def test_the_series_spans_two_phase_ids():
    """The reason this is scoped by paper: gathering by phase returns eight or
    one, never nine, and does so silently."""
    out = exam_reachability(PagedSB(_upsc_db()), "e1")
    assert {p["phase_id"] for p in out["papers"]} == {PHASE_OLD, PHASE_2026}

    narrowed = exam_reachability(PagedSB(_upsc_db()), "e1", PHASE_OLD)
    assert [p["year"] for p in narrowed["papers"]] == list(range(2018, 2026))
    narrowed_2026 = exam_reachability(PagedSB(_upsc_db()), "e1", PHASE_2026)
    assert [p["year"] for p in narrowed_2026["papers"]] == [2026]


def test_ineligible_papers_are_excluded_with_a_reason():
    db = _upsc_db()
    db["pyq_papers"].append(_paper("p-csat-arch", 2024, "1d6611c7", code="CSAT"))
    db["pyq_questions"].extend(_questions("p-csat-arch", ["medium"] * 221))
    db["pyq_papers"].append(_paper("p-csat-2025", 2025, "d813043d", code="CSAT"))
    db["pyq_questions"].extend(_questions("p-csat-2025", [None] * 80))

    out = exam_reachability(PagedSB(db), "e1")
    assert len(out["papers"]) == 9
    assert out["excluded"][UNIFORM] == 1
    assert out["excluded"][NOT_ASSESSED] == 1
    assert out["papers_considered"] == 11


def test_an_exam_with_no_assessed_papers_returns_nothing_to_plot():
    db = {
        "exams": [{"id": "e2", "slug": "upsc-cse-mains"}],
        "exam_phases": [{"id": "626ec667", "phase_name": "Mains", "phase_slug": "mains"}],
        "pyq_papers": [_paper("p-m1", 2024, "626ec667")],
        "pyq_questions": _questions("p-m1", [None] * 60),
    }
    db["pyq_papers"][0]["exam_id"] = "e2"
    out = exam_reachability(PagedSB(db), "e2")
    assert out["papers"] == []
    assert out["excluded"][NOT_ASSESSED] == 1


def test_unverified_questions_never_reach_the_count():
    db = _upsc_db()
    for q in db["pyq_questions"]:
        if q["pyq_paper_id"] == "p-gs1-2025":
            q["reviewer_status"] = "pending"
    out = exam_reachability(PagedSB(db), "e1")
    years = [p["year"] for p in out["papers"]]
    assert 2025 not in years
    assert out["excluded"][NOT_ASSESSED] == 1


def test_unverified_papers_never_reach_the_count():
    db = _upsc_db()
    for p in db["pyq_papers"]:
        if p["year"] == 2020:
            p["trust_status"] = "pending"
    out = exam_reachability(PagedSB(db), "e1")
    assert 2020 not in [p["year"] for p in out["papers"]]


# ── Endpoint ─────────────────────────────────────────────────────────────────


def test_reachability_endpoint_returns_nine_points():
    client, _ = _client(_upsc_db())
    r = client.get("/api/exam-intelligence/exams/upsc-cse/reachability")
    assert r.status_code == 200
    body = r.json()
    assert body["verified_only"] is True
    assert body["bands"] == ["easy", "medium", "hard"]
    assert len(body["papers"]) == 9
    assert {p["year"] for p in body["papers"]} == set(GS1)
    # The metadata blob never ships; only the reviewed display label does.
    assert "metadata" not in body["papers"][0]
    assert "set_label" in body["papers"][0]


def test_reachability_endpoint_derives_the_set_label():
    db = _upsc_db()
    for p in db["pyq_papers"]:
        if p["year"] == 2025:
            p["metadata"] = {"paper_set": "SET-A", "internal_note": "do not surface"}
    client, _ = _client(db)
    body = client.get("/api/exam-intelligence/exams/upsc-cse/reachability").json()
    row = next(p for p in body["papers"] if p["year"] == 2025)
    assert row["set_label"] == "Set A"
    assert "internal_note" not in str(row)


def test_reachability_endpoint_on_an_unknown_exam():
    client, _ = _client(_upsc_db())
    body = client.get("/api/exam-intelligence/exams/nope/reachability").json()
    assert body["exam_id"] is None
    assert body["papers"] == []


# ── Composition ──────────────────────────────────────────────────────────────


def _tag(qid, topic_id, tag_id=None, role="primary", status="verified"):
    return {
        "id": tag_id or f"tag-{qid}-{topic_id}",
        "question_id": qid,
        "topic_id": topic_id,
        "tag_role": role,
        "reviewer_status": status,
    }


def _composition_db():
    """One microtopic-tagged GS-I paper and one top-level-tagged CSAT paper."""
    gs_qs = _questions("p-gs1", _bands((16, 58, 26)))
    csat_qs = _questions("p-csat", [None] * 4)
    return {
        "exams": [{"id": "e1", "slug": "upsc-cse"}],
        "exam_phases": [{"id": PHASE_OLD, "phase_name": "Prelims", "phase_slug": "prelims"}],
        "pyq_papers": [
            _paper("p-gs1", 2025, PHASE_OLD, metadata={"set_code": "a"}),
            _paper("p-csat", 2025, PHASE_OLD, code="CSAT"),
            _paper("p-bare", 2024, PHASE_OLD, code="GS-1"),
        ],
        "pyq_questions": gs_qs + csat_qs + _questions("p-bare", ["easy"] * 3),
        # GS-I tags sit at MICROTOPIC level; CSAT's sit at TOP LEVEL. Same shape
        # on screen, different meaning.
        "pyq_question_topic_tags": (
            [_tag(q["id"], "m-fr" if i % 2 else "m-parl") for i, q in enumerate(gs_qs)]
            + [_tag(q["id"], "t-compre") for q in csat_qs]
        ),
        "topics": [
            {"id": "m-fr", "name": "Fundamental Rights", "parent_topic_id": "t-polity"},
            {"id": "m-parl", "name": "Parliament", "parent_topic_id": "t-polity"},
            {"id": "t-polity", "name": "Polity", "parent_topic_id": None},
            {"id": "t-compre", "name": "Comprehension", "parent_topic_id": None},
        ],
    }


def test_composition_reports_microtopic_level_and_groups_under_the_parent():
    out = paper_composition(PagedSB(_composition_db()), "p-gs1")
    assert out["tag_level"] == "microtopic"
    assert out["tagged_questions"] == 100
    assert out["untagged_questions"] == 0
    assert len(out["groups"]) == 1
    group = out["groups"][0]
    assert group["topic_name"] == "Polity"
    assert group["questions"] == 100
    assert {c["topic_name"] for c in group["children"]} == {
        "Fundamental Rights",
        "Parliament",
    }
    assert sum(c["questions"] for c in group["children"]) == 100


def test_composition_reports_top_level_tagging_separately():
    """2025 CSAT's tags are all top-level topics — not equivalent to the GS-I
    microtopic breakdown, and must not be reported as if they were."""
    out = paper_composition(PagedSB(_composition_db()), "p-csat")
    assert out["tag_level"] == "topic"
    assert out["groups"] == [
        {
            "topic_id": "t-compre",
            "topic_name": "Comprehension",
            "questions": 4,
            "children": [],
        }
    ]


def test_composition_eligibility_is_independent_of_difficulty():
    """The CSAT paper is 100% NULL difficulty and still composes; the bare
    paper is fully assessed and still has nothing to compose."""
    db = _composition_db()
    assert paper_composition(PagedSB(db), "p-csat")["groups"]
    bare = paper_composition(PagedSB(db), "p-bare")
    assert bare["groups"] == []
    assert bare["tagged_questions"] == 0
    assert bare["untagged_questions"] == 3
    assert bare["tag_level"] is None


def test_composition_counts_a_question_once():
    db = _composition_db()
    first_q = db["pyq_questions"][0]["id"]
    db["pyq_question_topic_tags"].append(_tag(first_q, "m-parl", tag_id="zz-second"))
    out = paper_composition(PagedSB(db), "p-gs1")
    assert out["tagged_questions"] == 100
    assert out["multi_tagged_questions"] == 1
    assert sum(g["questions"] for g in out["groups"]) == 100


def test_composition_ignores_secondary_and_unverified_tags():
    db = _composition_db()
    for t in db["pyq_question_topic_tags"]:
        if t["question_id"].startswith("p-gs1"):
            t["tag_role"] = "secondary"
            break
    for t in db["pyq_question_topic_tags"]:
        if t["question_id"].startswith("p-gs1") and t["tag_role"] == "primary":
            t["reviewer_status"] = "pending"
            break
    out = paper_composition(PagedSB(db), "p-gs1")
    assert out["tagged_questions"] == 98
    assert out["untagged_questions"] == 2


def test_composition_orders_groups_by_size():
    db = _composition_db()
    db["topics"].append({"id": "m-eco", "name": "Fiscal policy", "parent_topic_id": "t-eco"})
    db["topics"].append({"id": "t-eco", "name": "Economy", "parent_topic_id": None})
    for t in db["pyq_question_topic_tags"][:10]:
        if t["question_id"].startswith("p-gs1"):
            t["topic_id"] = "m-eco"
    out = paper_composition(PagedSB(db), "p-gs1")
    sizes = [g["questions"] for g in out["groups"]]
    assert sizes == sorted(sizes, reverse=True)


def test_composition_endpoint_404s_on_an_unverified_paper():
    db = _composition_db()
    db["pyq_papers"][0]["trust_status"] = "pending"
    client, _ = _client(db)
    assert client.get("/api/exam-intelligence/pyq-papers/p-gs1/composition").status_code == 404


def test_composition_endpoint_returns_the_set_label_not_the_blob():
    client, _ = _client(_composition_db())
    body = client.get("/api/exam-intelligence/pyq-papers/p-gs1/composition").json()
    assert body["set_label"] == "Set A"
    assert "metadata" not in body
    assert body["tag_level"] == "microtopic"
