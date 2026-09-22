"""Essay-PYQ-tag review via the generic exam-intelligence review surface.

`essay_pyq_tags.reviewer_status` had no writable path — admin_exam_intel_cms's
PATCH allowlist excludes it — so all rows were stuck 'pending' and the Essay
Builder's aspirant PYQ-tags sidebar could never show verified data. Registering
`essay_pyq_tag` in admin_exam_intelligence._REVIEWABLE (a direct mirror of
pyq_question_topic_tag) makes the existing generic routes drive it:

    GET   /admin/exam-intelligence/exams/{exam_id}/items?kind=essay_pyq_tag
    PATCH /admin/exam-intelligence/items/essay_pyq_tag/{id}/review

No new endpoint code, no schema change.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intelligence as admin_api
from app.core.auth import get_current_user
from tests.persona_questions._stub import SBStub


def _build_app(sb: SBStub, role: str = "super_admin"):
    app = FastAPI()
    app.include_router(admin_api.router, prefix="/api")
    admin_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "admin-1",
        "role": role,
        "permissions": ["exam_intelligence.review"] if role == "admin" else [],
    }
    return app


def _seed():
    # e1 owns paper p1 → questions q1, q2. e2 owns paper p2 → question q9.
    # Essay tags: t1 (pending, e1), t2 (verified, e1), t9 (pending, e2 — must be
    # scoped OUT when listing e1, exactly like pyq_question_topic_tag).
    return {
        "exams": [
            {"id": "e1", "slug": "upsc-cse", "name": "UPSC CSE", "exam_type": "recruitment", "is_active": True},
            {"id": "e2", "slug": "ssc-cgl", "name": "SSC CGL", "exam_type": "recruitment", "is_active": True},
        ],
        "essay_themes": [
            {"id": "th1", "theme_code": "JUSTICE", "theme_name": "Justice", "status": "active"},
        ],
        "pyq_papers": [
            {"id": "p1", "exam_id": "e1"},
            {"id": "p2", "exam_id": "e2"},
        ],
        "pyq_questions": [
            {"id": "q1", "pyq_paper_id": "p1", "reviewer_status": "verified"},
            {"id": "q2", "pyq_paper_id": "p1", "reviewer_status": "verified"},
            {"id": "q9", "pyq_paper_id": "p2", "reviewer_status": "verified"},
        ],
        "essay_pyq_tags": [
            {"id": "et1", "question_id": "q1", "theme_id": "th1", "secondary_theme_id": None,
             "essay_type": "quote_abstract", "quote_source_type": None, "tagging_source": "imported",
             "confidence_score": 0.5, "reviewer_status": "pending", "reviewed_by": None,
             "reviewed_at": None, "created_at": "2026-05-01T00:00:00+00:00"},
            {"id": "et2", "question_id": "q2", "theme_id": "th1", "secondary_theme_id": None,
             "essay_type": "issue_concrete", "quote_source_type": None, "tagging_source": "imported",
             "confidence_score": 0.5, "reviewer_status": "verified", "reviewed_by": None,
             "reviewed_at": None, "created_at": "2026-04-30T00:00:00+00:00"},
            {"id": "et9", "question_id": "q9", "theme_id": "th1", "secondary_theme_id": None,
             "essay_type": "quote_abstract", "quote_source_type": None, "tagging_source": "imported",
             "confidence_score": 0.5, "reviewer_status": "pending", "reviewed_by": None,
             "reviewed_at": None, "created_at": "2026-04-29T00:00:00+00:00"},
        ],
    }


_LIST = "/api/admin/exam-intelligence/exams/e1/items"
_REVIEW = "/api/admin/exam-intelligence/items/essay_pyq_tag"


def test_essay_pyq_tag_is_registered_reviewable():
    assert "essay_pyq_tag" in admin_api._REVIEWABLE
    assert admin_api._REVIEWABLE["essay_pyq_tag"]["table"] == "essay_pyq_tags"


def test_list_pending_essay_pyq_tags_returns_real_rows_scoped_to_exam():
    client = TestClient(_build_app(SBStub(_seed())))
    r = client.get(f"{_LIST}?kind=essay_pyq_tag&status=pending")
    assert r.status_code == 200, r.text
    ids = {row["id"] for row in r.json()["items"]}
    # et1 is pending & under e1; et2 is verified (filtered by status); et9 is
    # pending but under e2 (scoped out via question→paper→exam).
    assert ids == {"et1"}


def test_review_promotes_pending_tag_to_verified_and_read_reflects_it():
    sb = SBStub(_seed())
    client = TestClient(_build_app(sb))
    r = client.patch(f"{_REVIEW}/et1/review", json={"reviewer_status": "verified"})
    assert r.status_code == 200, r.text
    assert r.json()["reviewer_status"] == "verified"
    assert r.json()["reviewed_by"] == "admin-1"
    # Now it surfaces under the verified filter and is gone from pending.
    verified = client.get(f"{_LIST}?kind=essay_pyq_tag&status=verified").json()["items"]
    assert "et1" in {row["id"] for row in verified}
    pending = client.get(f"{_LIST}?kind=essay_pyq_tag&status=pending").json()["items"]
    assert "et1" not in {row["id"] for row in pending}


def test_invalid_status_is_rejected_like_the_topic_tag_analog():
    client = TestClient(_build_app(SBStub(_seed())))
    r = client.patch(f"{_REVIEW}/et1/review", json={"reviewer_status": "bogus"})
    assert r.status_code == 422  # ReviewBody pattern — same rejection as any kind


def test_review_blocked_for_non_admin():
    client = TestClient(_build_app(SBStub(_seed()), role="user"))
    r = client.patch(f"{_REVIEW}/et1/review", json={"reviewer_status": "verified"})
    assert r.status_code == 403
