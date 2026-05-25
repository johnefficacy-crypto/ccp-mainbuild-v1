"""CMS create / bulk-import contract for PYQ topic tags (migration 032).

Tags are how PYQ data feeds Study OS: a locked coverage row is planner-ready
when its topic has a *verified* PYQ tag. The CMS must let operators create
tags (single + bulk at PYQ scale) that always land ``pending`` and flow
through the existing /admin/exam-intelligence review queue, and verified
tags must still reach the planner. These tests pin that chain.
"""
from __future__ import annotations

import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intel_cms as cms_api
from app.api import admin_exam_intelligence as review_api
from app.core.auth import get_current_user
from scripts import validate_exam_intelligence_seed as validator
from tests.exam_intelligence.test_cms_taxonomy import TaxSBStub

_BASE = "/api/admin/exam-intelligence-cms"
_TAGS = f"{_BASE}/pyq-question-topic-tags"


def _cms_client(sb: TaxSBStub) -> TestClient:
    app = FastAPI()
    app.include_router(cms_api.router, prefix="/api")
    cms_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[cms_api._flag_enabled] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "admin-1", "role": "super_admin", "permissions": [cms_api.PERM_CMS],
    }
    return TestClient(app, raise_server_exceptions=False)


def _review_client(sb: TaxSBStub) -> TestClient:
    app = FastAPI()
    app.include_router(review_api.router, prefix="/api")
    review_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "admin-1", "role": "super_admin", "permissions": [],
    }
    return TestClient(app, raise_server_exceptions=False)


def _seed() -> dict:
    return {
        "exams": [{"id": "e1", "slug": "ssc-cgl", "name": "SSC CGL", "is_active": True}],
        "pyq_papers": [{"id": "p1", "exam_id": "e1", "year": 2024}],
        "pyq_questions": [{"id": "q1", "pyq_paper_id": "p1", "reviewer_status": "verified"}],
        "subjects": [{"id": "s1", "slug": "quant", "name": "Quant", "is_active": True}],
        "topics": [{"id": "t1", "subject_id": "s1", "slug": "pct", "name": "Percentages", "is_active": True}],
    }


# ── 1 & 2. create forces pending ──────────────────────────────────────────


def test_create_tag_lands_pending():
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).post(
        _TAGS,
        json={"reason": "tagging q1 to percentages", "payload": {
            "question_id": "q1", "topic_id": "t1", "tag_role": "primary", "tagging_source": "manual"}},
    )
    assert r.status_code == 200, r.text
    row = sb.db["pyq_question_topic_tags"][0]
    assert row["reviewer_status"] == "pending"
    assert row["question_id"] == "q1" and row["topic_id"] == "t1"


def test_create_tag_forces_pending_even_if_caller_sends_verified():
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).post(
        _TAGS,
        json={"reason": "trying to seed verified", "payload": {
            "question_id": "q1", "topic_id": "t1", "reviewer_status": "verified"}},
    )
    assert r.status_code == 200, r.text
    assert sb.db["pyq_question_topic_tags"][0]["reviewer_status"] == "pending"


# ── 3. bulk import at PYQ scale with per-row errors ───────────────────────


def test_bulk_import_1000_tags_mixed_valid_invalid():
    sb = TaxSBStub(_seed())
    rows = []
    for i in range(1000):
        topic = "bad-topic" if i % 100 == 0 else "t1"  # 10 invalid, 990 valid
        rows.append({"question_id": "q1", "topic_id": topic,
                     "tag_role": "primary", "tagging_source": "imported", "metadata": {"i": i}})
    r = _cms_client(sb).post(
        f"{_BASE}/bulk-import",
        json={"reason": "bulk seeding a paper-set of tags", "entity": "pyq-question-topic-tags", "rows": rows},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok_count"] == 990
    assert body["error_count"] == 10
    assert len(sb.db["pyq_question_topic_tags"]) == 990
    bad = [res for res in body["results"] if not res["ok"]]
    assert len(bad) == 10
    assert all("topic_id" in res["error"] for res in bad)
    assert all(t["reviewer_status"] == "pending" for t in sb.db["pyq_question_topic_tags"])


def test_bulk_import_tags_allows_more_than_default_cap_but_subjects_do_not():
    sb = TaxSBStub(_seed())
    client = _cms_client(sb)
    # subjects keep the 500 default cap.
    over = client.post(
        f"{_BASE}/bulk-import",
        json={"reason": "too many subjects at once", "entity": "subjects",
              "rows": [{"slug": f"s{i}", "name": f"S{i}"} for i in range(501)]},
    )
    assert over.status_code == 422, over.text
    assert "at most 500" in str(over.json().get("detail"))


# ── 4. existing review queue still reviews CMS-created tags ───────────────


def test_review_queue_reviews_cms_created_tag():
    sb = TaxSBStub(_seed())
    create = _cms_client(sb).post(_TAGS, json={"reason": "seeding for review", "payload": {"question_id": "q1", "topic_id": "t1"}})
    assert create.status_code == 200, create.text
    tag_id = sb.db["pyq_question_topic_tags"][0]["id"]

    rev = _review_client(sb).patch(
        f"/api/admin/exam-intelligence/items/pyq_question_topic_tag/{tag_id}/review",
        json={"reviewer_status": "verified"},
    )
    assert rev.status_code == 200, rev.text
    assert rev.json()["reviewer_status"] == "verified"


# ── 5. planner regression: verified tags reach planner readiness ──────────


def test_planner_picks_up_verified_tag(monkeypatch):
    sb = TaxSBStub({
        "exams": [{"id": "e1", "slug": "ssc-cgl", "name": "SSC CGL", "is_active": True}],
        "exam_cycles": [{"id": "cy1", "exam_id": "e1", "status": "open"}],
        "exam_phases": [{"id": "ph1", "exam_id": "e1", "phase_name": "T1", "status": "active"}],
        "subjects": [{"id": "s1", "slug": "quant", "name": "Quant", "is_active": True}],
        "topics": [{"id": "t1", "subject_id": "s1", "slug": "pct", "name": "Percentages", "is_active": True}],
        # Locked coverage that is NOT admin_review and has no notes — so it is
        # only planner-ready if a verified PYQ tag backs the topic.
        "exam_topic_coverage": [{"id": "c1", "exam_id": "e1", "topic_id": "t1",
                                 "source_basis": "pyq_analysis", "reviewer_status": "locked", "review_notes": None}],
        "pyq_papers": [{"id": "p1", "exam_id": "e1", "year": 2024}],
        "pyq_questions": [{"id": "q1", "pyq_paper_id": "p1", "reviewer_status": "verified"}],
    })
    # Create the tag through the CMS — it lands pending.
    create = _cms_client(sb).post(_TAGS, json={"reason": "tag feeding the planner", "payload": {"question_id": "q1", "topic_id": "t1"}})
    assert create.status_code == 200, create.text
    assert sb.db["pyq_question_topic_tags"][0]["reviewer_status"] == "pending"

    # Promote it through review.
    sb.db["pyq_question_topic_tags"][0]["reviewer_status"] = "verified"

    # The readiness validator (planner gate) now resolves the locked coverage
    # via the verified tag's evidence chain.
    monkeypatch.setattr(validator, "get_supabase_admin", lambda: sb)
    monkeypatch.setattr(sys, "argv", ["validate", "--exam-slug", "ssc-cgl", "--strict"])
    assert validator.main() == 0


# ── pyq-sources create ────────────────────────────────────────────────────


def test_create_pyq_source_lands_pending():
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).post(
        f"{_BASE}/pyq-sources",
        json={"reason": "registering a source", "payload": {
            "exam_id": "e1", "source_type": "official", "title": "SSC official PYQ", "trust_status": "verified"}},
    )
    assert r.status_code == 200, r.text
    assert sb.db["pyq_sources"][0]["trust_status"] == "pending"
