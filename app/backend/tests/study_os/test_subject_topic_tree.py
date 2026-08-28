"""Tests for ``GET /api/study/subjects/{subject_id}/topics`` — the nested
topic → microtopic tree with locked-coverage priority (Topic Study Hub step 1).

Contract invariants:
  - structure comes from the ``topics`` table, so a topic with NO locked
    coverage still appears (coverage null), never omitted;
  - locked ``exam_topic_coverage`` supplies priority where it exists;
  - a 0-evidence rollup node (locked coverage + 0 verified primary tags) is
    flagged and sunk in order (PR #1030 guard), never silently reintroduced;
  - an unknown subject_id is a clean 404.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import study_os as study_os_api
from app.study_os import subjects as subjects_service
from app.core.auth import get_current_user
from tests.persona_questions._stub import SBStub


def _seed() -> dict:
    return {
        "profiles": [{"id": "u-1", "target_exam": "upsc-cse"}],
        "exams": [
            {"id": "exam-1", "slug": "upsc-cse", "name": "UPSC CSE",
             "exam_type": "recruitment", "is_active": True},
        ],
        "subjects": [
            {"id": "s1", "name": "History & Culture", "slug": "upsc-history",
             "subject_group": "gs"},
        ],
        "topics": [
            # macro (level='topic')
            {"id": "t-macro", "name": "Ancient India", "subject_id": "s1",
             "level": "topic", "parent_topic_id": None, "is_active": True},
            # microtopics under the macro
            {"id": "t-micro-a", "name": "Indus Valley", "subject_id": "s1",
             "level": "microtopic", "parent_topic_id": "t-macro", "is_active": True},
            {"id": "t-micro-b", "name": "Vedic Age", "subject_id": "s1",
             "level": "microtopic", "parent_topic_id": "t-macro", "is_active": True},
            # a second macro with a 0-evidence locked-coverage row (rollup)
            {"id": "t-rollup", "name": "General mental ability", "subject_id": "s1",
             "level": "topic", "parent_topic_id": None, "is_active": True},
        ],
        "exam_topic_coverage": [
            # locked coverage on one microtopic (real leaf, has evidence)
            {"id": "cov-a", "exam_id": "exam-1", "topic_id": "t-micro-a",
             "exam_priority_score": 82, "is_high_yield": True,
             "confidence_score": 0.9, "reviewer_status": "locked"},
            # locked coverage on the rollup header (0 evidence → contamination)
            {"id": "cov-r", "exam_id": "exam-1", "topic_id": "t-rollup",
             "exam_priority_score": 30, "is_high_yield": False,
             "confidence_score": 0.5, "reviewer_status": "locked"},
            # a draft row must never attach
            {"id": "cov-b", "exam_id": "exam-1", "topic_id": "t-micro-b",
             "exam_priority_score": 99, "is_high_yield": True,
             "confidence_score": 0.4, "reviewer_status": "draft"},
        ],
    }


# Real verified-primary PYQ counts: the real leaf has evidence, the rollup
# header has none. Patched so the tree logic is exercised without seeding the
# whole pyq_papers→questions→tags join.
_EVIDENCE = {"t-micro-a": 7, "t-micro-b": 0, "t-macro": 0, "t-rollup": 0}


@pytest.fixture(autouse=True)
def _patch_evidence(monkeypatch):
    monkeypatch.setattr(
        subjects_service, "verified_pyq_topic_counts", lambda sb, exam_id: dict(_EVIDENCE)
    )


def _client(sb: SBStub) -> TestClient:
    app = FastAPI()
    app.include_router(study_os_api.router, prefix="/api")
    study_os_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[get_current_user] = lambda: {"id": "u-1", "role": "user"}
    return TestClient(app)


def test_returns_nested_tree_with_priority_only_where_locked():
    body = _client(SBStub(_seed())).get("/api/study/subjects/s1/topics").json()
    assert body["subject_id"] == "s1"
    assert body["exam_id"] == "exam-1"

    roots = {n["topic_id"]: n for n in body["topics"]}
    assert set(roots) == {"t-macro", "t-rollup"}  # both macros are roots

    macro = roots["t-macro"]
    kids = {c["topic_id"]: c for c in macro["children"]}
    assert set(kids) == {"t-micro-a", "t-micro-b"}  # microtopics nested under macro

    # Locked coverage attaches only to the locked microtopic.
    assert kids["t-micro-a"]["coverage"]["exam_priority_score"] == 82.0
    assert kids["t-micro-a"]["coverage"]["is_high_yield"] is True
    # The draft-coverage microtopic gets NO coverage (draft never attaches).
    assert kids["t-micro-b"]["coverage"] is None


def test_topic_without_locked_coverage_still_appears_with_null_coverage():
    body = _client(SBStub(_seed())).get("/api/study/subjects/s1/topics").json()
    macro = next(n for n in body["topics"] if n["topic_id"] == "t-macro")
    kids = {c["topic_id"]: c for c in macro["children"]}
    # t-micro-b has no locked coverage — present, coverage null, not omitted.
    assert "t-micro-b" in kids
    assert kids["t-micro-b"]["coverage"] is None
    assert kids["t-micro-b"]["is_rollup_zero_evidence"] is False  # no coverage ⇒ not a rollup


def test_zero_evidence_rollup_node_is_flagged_and_sunk_not_dropped():
    body = _client(SBStub(_seed())).get("/api/study/subjects/s1/topics").json()
    roots = {n["topic_id"]: n for n in body["topics"]}
    # Still present (never silently dropped)…
    assert "t-rollup" in roots
    # …flagged (locked coverage but 0 verified primary tags)…
    assert roots["t-rollup"]["is_rollup_zero_evidence"] is True
    # …and a real evidence-backed leaf is NOT flagged.
    macro = roots["t-macro"]
    real_leaf = next(c for c in macro["children"] if c["topic_id"] == "t-micro-a")
    assert real_leaf["is_rollup_zero_evidence"] is False
    # Default order sinks the rollup below a real scored root. Here both roots
    # are macros; the rollup (flagged) must sort after the non-flagged macro.
    assert body["topics"][-1]["topic_id"] == "t-rollup"


def test_unknown_subject_returns_404():
    r = _client(SBStub(_seed())).get("/api/study/subjects/does-not-exist/topics")
    assert r.status_code == 404


def test_real_subject_with_no_topics_returns_empty_tree_not_404():
    seed = _seed()
    seed["topics"] = []  # subject exists, no topics
    r = _client(SBStub(seed)).get("/api/study/subjects/s1/topics")
    assert r.status_code == 200
    assert r.json()["topics"] == []


def test_no_target_exam_returns_structure_with_null_coverage():
    seed = _seed()
    seed["profiles"] = [{"id": "u-1", "target_exam": None}]
    body = _client(SBStub(seed)).get("/api/study/subjects/s1/topics").json()
    assert body["exam_id"] is None
    # Structure still returned; nothing scored.
    macro = next(n for n in body["topics"] if n["topic_id"] == "t-macro")
    assert all(c["coverage"] is None for c in macro["children"])
    assert all(not n["is_rollup_zero_evidence"] for n in body["topics"])
