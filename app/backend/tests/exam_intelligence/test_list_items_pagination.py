"""Pagination + IN()-batching regression for admin_exam_intelligence.list_items.

Third location of the #1016 / #1022 bug class: list_items paged with
`.order().limit(limit + offset)` + a Python slice (truncates past db-max-rows)
AND fed an unbatched `.in_("question_id", <all exam questions>)` (414s past the
URL-length ceiling). Both made the review queue return 0 rows for a real,
non-empty pending set once the exam had more than ~1000 questions — live-
observed against essay_pyq_tag.

The stub models BOTH failure modes: a hard per-read `server_cap` (db-max-rows)
that only complete `.range()` paging defeats, and an IN() that raises past the
250-id ceiling that only batching defeats. A fixture larger than the cap that
still lists completely can only do so if both are fixed.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intelligence as admin_api
from app.core.auth import get_current_user
from tests.exam_intelligence._capping_stub import CappingSB, _CapQuery

_CEILING = 250  # matches admin_api._LIST_IN_BATCH — the max ids one IN() may carry


class _CeilingCapQuery(_CapQuery):
    """CappingSB query that also rejects an oversized IN(), like the live proxy
    returning 414 for a URL past its length ceiling."""

    def in_(self, key, vals):
        vals = list(vals)
        if len(vals) > _CEILING:
            raise RuntimeError(
                f"IN() over {len(vals)} ids exceeds the {_CEILING}-id URL-length ceiling"
            )
        return super().in_(key, vals)


class _CeilingCappingSB(CappingSB):
    def table(self, name):
        return _CeilingCapQuery(self.db.get(name, []), self.server_cap)


def _build_app(sb, role: str = "super_admin"):
    app = FastAPI()
    app.include_router(admin_api.router, prefix="/api")
    admin_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "admin-1", "role": role, "permissions": [],
    }
    return app


def _seed_essay_tags(n: int):
    """One exam/paper with `n` questions, each carrying one pending essay tag.
    n is chosen > the server cap and > the 250-id IN() ceiling on purpose."""
    questions = [{"id": f"q{i:05d}", "pyq_paper_id": "p1"} for i in range(n)]
    tags = [
        {
            "id": f"et{i:05d}", "question_id": f"q{i:05d}", "theme_id": "th1",
            "secondary_theme_id": None, "essay_type": "quote_abstract",
            "quote_source_type": None, "tagging_source": "imported",
            "confidence_score": 0.5, "reviewer_status": "pending",
            "reviewed_by": None, "reviewed_at": None,
            # descending created_at so newest-first order is checkable
            "created_at": f"2026-05-01T00:{i // 60:02d}:{i % 60:02d}+00:00",
        }
        for i in range(n)
    ]
    return {
        "exams": [{"id": "e1", "slug": "upsc-cse", "name": "UPSC CSE", "is_active": True}],
        "pyq_papers": [{"id": "p1", "exam_id": "e1"}],
        "pyq_questions": questions,
        "essay_pyq_tags": tags,
    }


_LIST = "/api/admin/exam-intelligence/exams/e1/items"


def test_returns_complete_set_past_the_cap_and_the_in_ceiling():
    # 1500 rows > server_cap (1000) and > IN() ceiling (250): the old
    # limit+offset+slice / unbatched-IN path returned 0; the fix returns all.
    sb = _CeilingCappingSB(_seed_essay_tags(1500), server_cap=admin_api._LIST_PAGE)
    client = TestClient(_build_app(sb))
    body = client.get(f"{_LIST}?kind=essay_pyq_tag&status=pending&limit=50&offset=0").json()
    assert body["count"] == 1500  # full match total, not a capped 1000
    assert len(body["items"]) == 50


def test_pagination_is_stable_and_non_overlapping_across_pages():
    sb = _CeilingCappingSB(_seed_essay_tags(1500), server_cap=admin_api._LIST_PAGE)
    client = TestClient(_build_app(sb))
    p1 = client.get(f"{_LIST}?kind=essay_pyq_tag&status=pending&limit=50&offset=0").json()["items"]
    p2 = client.get(f"{_LIST}?kind=essay_pyq_tag&status=pending&limit=50&offset=50").json()["items"]
    ids1 = [r["id"] for r in p1]
    ids2 = [r["id"] for r in p2]
    assert len(set(ids1)) == 50 and len(set(ids2)) == 50
    assert set(ids1).isdisjoint(ids2)  # no duplicated / skipped rows
    # Newest-first: page 1 all sort above page 2.
    assert min(r["created_at"] for r in p1) >= max(r["created_at"] for r in p2)


def test_pyq_question_topic_tag_shares_the_path_and_still_lists():
    # The same code path serves pyq_question_topic_tag — prove the shared change
    # didn't regress it, again past the cap + ceiling.
    seed = _seed_essay_tags(1200)
    seed["pyq_question_topic_tags"] = [
        {"id": f"tag{i:05d}", "question_id": f"q{i:05d}", "topic_id": "t1",
         "tag_weight": 1.0, "tag_role": "primary", "tagging_source": "manual",
         "confidence_score": 0.3, "reviewer_status": "pending",
         "created_at": f"2026-05-01T00:{i // 60:02d}:{i % 60:02d}+00:00"}
        for i in range(1200)
    ]
    sb = _CeilingCappingSB(seed, server_cap=admin_api._LIST_PAGE)
    client = TestClient(_build_app(sb))
    body = client.get(f"{_LIST}?kind=pyq_question_topic_tag&status=pending&limit=100").json()
    assert body["count"] == 1200
    assert len(body["items"]) == 100


def test_empty_scope_returns_clean_empty():
    sb = _CeilingCappingSB(_seed_essay_tags(0), server_cap=admin_api._LIST_PAGE)
    client = TestClient(_build_app(sb))
    body = client.get(f"{_LIST}?kind=essay_pyq_tag&status=pending").json()
    assert body == {"items": [], "count": 0}
