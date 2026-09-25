"""REG-CORPUS-04 — body-agnostic authored topics and the exam-tier filter.

P1: a topic with NO ``metadata.exams`` key, in a body-agnostic subject, serves
every exam whose phase sections examine that subject. Keyed topics are
unchanged. P2: topic practice serves the learner's exam tier
(``metadata.exam_tier``) by default and can include the other tier; generated
mocks are tier-strict.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import mock_engine as mock_engine_api
from app.api import subject_practice
from app.core.auth import get_current_user
from app.exam_intelligence import authored_scope as scope
from app.exam_intelligence.diagnostics import authored_pool_rows
from app.study_os import pyq_practice as svc
from app.study_os.mock_blueprint_selection import build_blueprint_with_selection
from tests.persona_questions._stub import SBStub

SSC = "55c00000-0000-0000-0000-000000000001"
SEBI = "5eb10000-0000-0000-0000-000000000001"
IFSCA = "1f5ca000-0000-0000-0000-000000000001"
UPSC = "09500000-0000-0000-0000-000000000001"
CSAT = "c5a70000-0000-0000-0000-000000000001"  # has a QA section, no tier

S_QA = "0a000000-0000-0000-0000-0000000000aa"
S_COST = "c0510000-0000-0000-0000-0000000000aa"
S_HIST = "0b000000-0000-0000-0000-0000000000aa"

T_QA = "0a000000-0000-0000-0000-000000000001"        # QA, no exams key
T_QA_SEBI = "0a000000-0000-0000-0000-000000000002"   # QA, keyed [sebi]
T_QA_OFFICER = "0a000000-0000-0000-0000-000000000003"  # QA, no key, officer rows only
T_IFSCA = "c0510000-0000-0000-0000-000000000009"     # costing, keyed [ifsca]
T_HIST = "0b000000-0000-0000-0000-000000000001"      # history, no key (not body-agnostic)


def _opts(qid: str) -> list[dict]:
    return [
        {"id": f"opt-{qid}-{i}", "question_id": qid, "option_text": f"Option {i}",
         "option_index": i, "is_correct": i == 1, "display_order": i}
        for i in range(4)
    ]


def _authored(qid: str, topic: str, subject: str, tier: str | None = None) -> dict:
    meta = {"rubric_level": "L2"}
    if tier:
        meta["exam_tier"] = tier
    return {
        "id": qid, "question_text": f"Authored {qid}", "question_type": "mcq",
        "reviewer_status": "verified", "correct_option_id": f"opt-{qid}-1",
        "exam_id": None, "subject_id": subject, "topic_id": topic, "microtopic_id": None,
        "pyq_question_id": None, "pyq_paper_id": None, "pyq_year": None,
        "source_kind": "authored", "source_type": None, "difficulty": "medium",
        "is_current": False, "is_current_based": False, "valid_until": None,
        "metadata": meta,
    }


def _bank() -> list[dict]:
    return [
        _authored("qa-f", T_QA, S_QA, "foundation"),
        _authored("qa-o", T_QA, S_QA, "officer"),
        _authored("qa-untiered", T_QA, S_QA),
        _authored("qa-sebi", T_QA_SEBI, S_QA, "officer"),
        _authored("qa-officer-only", T_QA_OFFICER, S_QA, "officer"),
        _authored("ifsca-only", T_IFSCA, S_COST, "officer"),
        _authored("hist", T_HIST, S_HIST, "foundation"),
    ]


def _seed(bank: list[dict] | None = None) -> dict:
    bank = _bank() if bank is None else bank
    phases = {SSC: "ph-ssc", SEBI: "ph-sebi", IFSCA: "ph-ifsca", UPSC: "ph-upsc", CSAT: "ph-csat"}
    sections = [
        ("ph-ssc", S_QA), ("ph-sebi", S_QA), ("ph-sebi", S_COST),
        ("ph-ifsca", S_QA), ("ph-ifsca", S_COST), ("ph-upsc", S_HIST), ("ph-csat", S_QA),
    ]
    return {
        "exams": [
            {"id": SSC, "slug": "ssc-cgl"}, {"id": SEBI, "slug": "sebi-grade-a"},
            {"id": IFSCA, "slug": "ifsca-grade-a"}, {"id": UPSC, "slug": "upsc-cse"},
            {"id": CSAT, "slug": "upsc-csat"},
        ],
        "exam_phases": [{"id": pid, "exam_id": eid} for eid, pid in phases.items()],
        "exam_phase_sections": [
            {"id": f"sec-{i}", "exam_phase_id": ph, "subject_id": subj}
            for i, (ph, subj) in enumerate(sections)
        ],
        "subjects": [
            {"id": S_QA, "slug": "quantitative-aptitude"},
            {"id": S_COST, "slug": "costing"},
            {"id": S_HIST, "slug": "history"},
        ],
        "topics": [
            {"id": T_QA, "subject_id": S_QA, "metadata": {"ssc_cgl_tier1_area": "Arithmetic"}},
            {"id": T_QA_SEBI, "subject_id": S_QA, "metadata": {"exams": ["sebi"]}},
            {"id": T_QA_OFFICER, "subject_id": S_QA, "metadata": {}},
            {"id": T_IFSCA, "subject_id": S_COST, "metadata": {"exams": ["ifsca"]}},
            {"id": T_HIST, "subject_id": S_HIST, "metadata": {}},
        ],
        "mock_question_bank": [dict(r) for r in bank],
        "mock_question_options": [o for r in bank for o in _opts(r["id"])],
        "mock_question_stimuli": [],
        "mock_question_sources": [],
    }


def _db(bank: list[dict] | None = None) -> SBStub:
    return SBStub(_seed(bank))


def _ids(exam: str, topic: str, **kw) -> set[str]:
    rows = svc.select_practice_rows(_db(), mode="topic", exam_id=exam, target_id=topic, limit=50, **kw)
    return {r["id"] for r in rows}


# ── P1 body-agnostic eligibility ──────────────────────────────────────────────

def test_ssc_cgl_learner_sees_authored_qa_row():
    assert _ids(SSC, T_QA) == {"qa-f", "qa-untiered"}


def test_sebi_learner_sees_the_same_qa_row():
    assert _ids(SEBI, T_QA) == {"qa-o", "qa-untiered"}


def test_sebi_still_cannot_see_ifsca_only_keyed_rows():
    assert _ids(SEBI, T_IFSCA, include_other_tier=True) == set()
    assert _ids(IFSCA, T_IFSCA) == {"ifsca-only"}


def test_keyed_topic_in_a_body_agnostic_subject_is_not_widened():
    # SSC examines Quant, but this Quant topic names only SEBI.
    assert _ids(SSC, T_QA_SEBI, include_other_tier=True) == set()
    assert _ids(SEBI, T_QA_SEBI) == {"qa-sebi"}


def test_exam_without_that_section_sees_no_body_agnostic_rows():
    assert _ids(UPSC, T_QA, include_other_tier=True) == set()


def test_unkeyed_topic_outside_the_body_agnostic_subjects_is_never_served():
    # UPSC examines history, but history is not a shared (body-agnostic) tree.
    assert _ids(UPSC, T_HIST, include_other_tier=True) == set()


def test_unkeyed_exam_without_agnostic_sections_issues_no_pool_read():
    calls = []
    sb = _db()
    sb.db["exam_phase_sections"] = [s for s in sb.db["exam_phase_sections"] if s["exam_phase_id"] != "ph-csat"]
    assert scope.authored_rows_for_exam(sb, CSAT, lambda: calls.append(1) or _bank()) == []
    assert calls == []


def test_failed_section_read_fails_closed_without_breaking_keyed_rows():
    sb = _db()
    real = sb.table

    def table(name):
        if name == "exam_phases":
            raise RuntimeError("boom")
        return real(name)

    sb.table = table  # type: ignore[method-assign]
    assert scope.agnostic_subject_ids_for_exam(sb, SSC) == frozenset()
    assert svc.select_practice_rows(sb, mode="topic", exam_id=SSC, target_id=T_QA, limit=50) == []
    rows = svc.select_practice_rows(sb, mode="topic", exam_id=SEBI, target_id=T_QA_SEBI, limit=50)
    assert [r["id"] for r in rows] == ["qa-sebi"]


def test_mock_pool_is_tier_strict_and_keeps_untiered_rows():
    pool = {r["id"] for r in authored_pool_rows(_db(), exam_id=SSC, statuses=["verified"])}
    assert pool == {"qa-f", "qa-untiered"}
    sebi = {r["id"] for r in authored_pool_rows(_db(), exam_id=SEBI, statuses=["verified"])}
    assert sebi == {"qa-o", "qa-untiered", "qa-sebi", "qa-officer-only"}
    # an exam with no tier is not filtered
    csat = {r["id"] for r in authored_pool_rows(_db(), exam_id=CSAT, statuses=["verified"])}
    assert csat == {"qa-f", "qa-o", "qa-untiered", "qa-officer-only"}


def _mock_sb(exam: str, slug: str, bank: list[dict]) -> SBStub:
    phase = f"ph-{slug}"
    return SBStub({
        "exams": [{"id": exam, "slug": slug}],
        "exam_phases": [{"id": phase, "exam_id": exam, "phase_name": "Tier 1", "phase_slug": "tier-1",
                         "phase_order": 1, "duration_mins": 60}],
        "exam_phase_sections": [{
            "id": "sec-qa", "exam_phase_id": phase, "subject_id": S_QA,
            "section_label": "Quantitative Aptitude", "question_count": 10, "marks": 20,
            "duration_mins": None, "negative_marking": "-0.50", "difficulty_level": "medium",
            "weightage_percent": 100.0, "sort_order": 0,
        }],
        "subjects": [{"id": S_QA, "slug": "quantitative-aptitude"}],
        "topics": [{"id": T_QA, "subject_id": S_QA, "metadata": {}}],
        "exam_topic_coverage": [{"id": "cov-qa", "exam_id": exam, "exam_phase_id": phase,
                                 "section_id": "sec-qa", "reviewer_status": "locked"}],
        "mock_question_bank": bank,
    })


def _tiered_bank() -> list[dict]:
    rows = []
    for tier in ("foundation", "officer"):
        for i in range(10):
            r = _authored(f"{tier[0]}-{i:02d}", T_QA, S_QA, tier)
            r["reviewer_status"] = "published"
            rows.append(r)
    return rows


def _build_mock(exam: str, slug: str) -> dict:
    return build_blueprint_with_selection(
        _mock_sb(exam, slug, _tiered_bank()), exam_id=exam, exam_phase_id=f"ph-{slug}", user_id="u",
        selectable_statuses=["published"], verified_status="verified",
        min_per_section=1, min_locked_coverage=1,
    )


def test_ssc_cgl_generated_mock_never_draws_an_officer_authored_row():
    payload = _build_mock(SSC, "ssc-cgl")
    ids = set(payload["question_ids"])
    assert ids == {f"f-{i:02d}" for i in range(10)}
    assert not any(i.startswith("o-") for i in ids)
    # the officer rows are not even in the section's eligible pool
    [sec] = payload["selector_snapshot"]["sections"]
    assert sec["eligible_pool_count"] == 10


def test_officer_exam_generated_mock_never_draws_a_foundation_authored_row():
    payload = _build_mock(SEBI, "sebi-grade-a")
    assert set(payload["question_ids"]) == {f"o-{i:02d}" for i in range(10)}


def test_resolved_scope_names_key_sections_and_tier():
    s = scope.resolve_exam_scope(_db(), SSC)
    assert s == scope.ExamAuthoredScope(None, frozenset({S_QA}), "foundation")
    s = scope.resolve_exam_scope(_db(), SEBI)
    assert s == scope.ExamAuthoredScope("sebi", frozenset({S_QA}), "officer")
    assert scope.resolve_exam_scope(_db(), None).empty


# ── P2 exam tier ──────────────────────────────────────────────────────────────

def test_topic_practice_can_include_the_other_tier():
    assert _ids(SSC, T_QA, include_other_tier=True) == {"qa-f", "qa-o", "qa-untiered"}
    assert _ids(SEBI, T_QA, include_other_tier=True) == {"qa-f", "qa-o", "qa-untiered"}


def test_exam_with_no_tier_is_never_tier_filtered():
    assert _ids(CSAT, T_QA) == {"qa-f", "qa-o", "qa-untiered"}


def test_readiness_uses_the_default_tier_like_launch():
    sb = _db()
    assert svc.practiceable_topic_ids(sb, exam_id=SSC, topic_ids=[T_QA, T_QA_OFFICER]) == {T_QA}
    assert svc.practiceable_topic_ids(sb, exam_id=SEBI, topic_ids=[T_QA, T_QA_OFFICER]) == {T_QA, T_QA_OFFICER}


def test_exam_tier_config_is_the_specified_mapping():
    foundation = {"ssc-cgl", "ssc-chsl", "ibps-clerk", "sbi-clerk", "rrb-ntpc", "ibps-rrb-clerk"}
    officer = {"ibps-po", "sbi-po", "rbi-grade-b", "sebi-grade-a", "nabard-grade-a",
               "ifsca-grade-a", "pfrda-grade-a"}
    assert all(scope.exam_tier_for_slug(s) == "foundation" for s in foundation)
    assert all(scope.exam_tier_for_slug(s) == "officer" for s in officer)
    assert set(scope.EXAM_TIERS.values()) <= set(scope.EXAM_TIER_VALUES)
    assert scope.exam_tier_for_slug("upsc-cse") is None


def test_start_topic_practice_freezes_only_the_learner_tier():
    res = svc.start_pyq_practice(_db(), user_id="u1", mode="topic", target_id=T_QA, exam_id=SSC)
    assert res["outcome"] == "ready" and res["question_count"] == 2


def test_mock_practice_api_forwards_include_other_tier(monkeypatch):
    seen = {}

    def _capture(*a, **k):
        seen.update(k)
        return {"outcome": "ready", "attempt_id": "att-1"}

    monkeypatch.setattr(mock_engine_api, "start_pyq_practice", _capture)
    app = FastAPI()
    app.include_router(mock_engine_api.router, prefix="/api")
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1"}
    mock_engine_api.get_supabase_admin = lambda: _db()  # type: ignore[assignment]
    client = TestClient(app)
    body = {"mode": "topic", "target_id": T_QA, "exam_id": SSC}
    assert client.post("/api/study/mocks/practice/start", json=body).status_code == 200
    assert seen["include_other_tier"] is False
    assert client.post("/api/study/mocks/practice/start",
                       json={**body, "include_other_tier": True}).status_code == 200
    assert seen["include_other_tier"] is True


def test_subject_practice_api_forwards_include_other_tier_for_topic_modes(monkeypatch):
    seen = {}

    def _capture(*a, **k):
        seen.update(k)
        return {"outcome": "ready", "attempt_id": "att-2"}

    monkeypatch.setattr(subject_practice, "start_pyq_practice", _capture)
    seed = _seed()
    seed["profiles"] = [{"id": "u-1", "target_exam": SSC}]
    seed["exams"][0].update({"name": "SSC CGL", "exam_type": "recruitment", "is_active": True})
    seed["exam_topic_coverage"] = [{"id": "cov", "exam_id": SSC, "topic_id": T_QA, "reviewer_status": "locked"}]
    for t in seed["topics"]:
        t.update({"name": t["id"], "slug": t["id"], "is_active": True})
    seed["subjects"][0].update({"name": "Quant", "subject_group": "numerical", "is_active": True})
    sb = SBStub(seed)
    app = FastAPI()
    app.include_router(subject_practice.router, prefix="/api")
    app.dependency_overrides[get_current_user] = lambda: {"id": "u-1"}
    subject_practice.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    resp = TestClient(app).post(f"/api/study/subjects/{S_QA}/practice/start",
                                json={"mode": "topic_pyq", "topic_id": T_QA, "include_other_tier": True})
    assert resp.status_code == 200, resp.json()
    assert seen["include_other_tier"] is True
