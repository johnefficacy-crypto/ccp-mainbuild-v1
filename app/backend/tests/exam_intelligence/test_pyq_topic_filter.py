"""Regression tests for the PYQ Explorer topic/subject filter.

Root cause (see docs/status/pyq-topic-filter-investigation-2026-08-26.md):
`list_exam_pyqs` fetched `pyq_question_topic_tags` with a single unbatched
`.in_("question_id", <up to ~1000 ids>)`, far past the 250-id IN() URL-length
ceiling the rest of the codebase batches at. The oversized request failed and
the outer try/except returned `{items: [], total: 0}` — so every topic/subject
selection looked like "no results" instead of "the query broke."

The stub here models that ceiling: any `.in_(col, values)` with more than
`_CEILING` ids raises (as PostgREST/proxy would with a 414). So a topic filter
over >250 tagged questions passes ONLY because the endpoint now batches; revert
the batching and these tests fail with total == 0.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import exam_intelligence as ei_api
from app.core.auth import get_current_user
from tests.persona_questions._stub import SBStub, _Query

_CEILING = 250  # matches ei_api._BATCH — the max ids one IN() may carry


class _CeilingQuery(_Query):
    def in_(self, key, vals):
        vals = list(vals)
        if len(vals) > _CEILING:
            raise RuntimeError(
                f"IN() over {len(vals)} ids exceeds the {_CEILING}-id URL-length ceiling"
            )
        return super().in_(key, vals)


class _CeilingSB(SBStub):
    """SBStub that rejects an oversized IN() the way the live proxy does."""

    def table(self, name: str):
        return _CeilingQuery(name, self.db)


def _build_app(sb):
    app = FastAPI()
    app.include_router(ei_api.router, prefix="/api")
    ei_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[get_current_user] = lambda: {"id": "u-1", "role": "user", "permissions": []}
    return app


def _seed(n_tagged: int, *, topic_id: str = "t1") -> dict:
    """One verified paper with `n_tagged` verified questions, each carrying a
    verified primary tag to `topic_id` (subject s1)."""
    questions = [
        {
            "id": f"q{i:05d}",
            "pyq_paper_id": "p1",
            "question_number": i + 1,
            "question_text": f"Question {i}",
            "observed_difficulty": "medium",
            "reviewer_status": "verified",
        }
        for i in range(n_tagged)
    ]
    tags = [
        {
            "id": f"tag{i:05d}",
            "question_id": f"q{i:05d}",
            "topic_id": topic_id,
            "tag_role": "primary",
            "reviewer_status": "verified",
        }
        for i in range(n_tagged)
    ]
    return {
        "exams": [{"id": "e1", "slug": "upsc-cse"}],
        "pyq_papers": [
            {"id": "p1", "exam_id": "e1", "year": 2024, "exam_phase_id": None, "trust_status": "verified"}
        ],
        "subjects": [{"id": "s1", "name": "General Studies"}],
        "topics": [{"id": topic_id, "name": "Ancient India", "subject_id": "s1"}],
        "pyq_questions": questions,
        "pyq_question_topic_tags": tags,
    }


def _get(sb, params: str):
    client = TestClient(_build_app(sb))
    r = client.get(f"/api/exam-intelligence/exams/upsc-cse/pyqs?{params}")
    assert r.status_code == 200, r.text
    return r.json()


def test_topic_filter_over_more_than_250_tags_returns_correct_count():
    """300 verified questions tagged to one topic -> filtering by it returns 300,
    not 0. The oversized single IN() would raise under the ceiling stub; batching
    keeps every IN() <= 250 so the correct count comes back."""
    body = _get(_CeilingSB(_seed(300)), "topic_id=t1&page=1&page_size=20")
    assert body["total"] == 300
    assert len(body["items"]) == 20  # first page
    assert "error" not in body


def test_subject_filter_over_more_than_250_tags_returns_correct_count():
    body = _get(_CeilingSB(_seed(300)), "subject_id=s1&page=1&page_size=20")
    assert body["total"] == 300
    assert "error" not in body


def test_topic_filter_boundary_250_and_251_do_not_regress():
    """Exactly the ceiling (250) and one past it (251) both resolve correctly —
    _chunks(…, 250) keeps each IN() at or under the limit."""
    assert _get(_CeilingSB(_seed(250)), "topic_id=t1&page=1&page_size=100")["total"] == 250
    assert _get(_CeilingSB(_seed(251)), "topic_id=t1&page=1&page_size=100")["total"] == 251


def test_unfiltered_browse_has_no_regression():
    """No topic/subject filter -> the browse list still returns everything (the
    tag-join branch is skipped)."""
    body = _get(_CeilingSB(_seed(300)), "page=1&page_size=20")
    assert body["total"] == 300
    assert "error" not in body


def test_legitimately_empty_topic_returns_clean_empty_without_error():
    """A topic with no tagged questions returns total 0 and NO error field, so a
    genuine empty is distinguishable from a broken query."""
    body = _get(_CeilingSB(_seed(10)), "topic_id=does-not-exist&page=1&page_size=20")
    assert body["total"] == 0
    assert body["items"] == []
    assert "error" not in body


def test_genuine_query_failure_is_logged_and_flagged_not_silently_empty(caplog):
    """A real read failure (not a size overflow) must be logged with the actual
    exception AND surfaced via the response `error` field — never manufactured as
    a fake, indistinguishable `total: 0`."""

    class _BoomSB(_CeilingSB):
        def table(self, name: str):
            if name == "pyq_questions":
                raise RuntimeError("boom: pyq_questions read failed")
            return super().table(name)

    with caplog.at_level(logging.ERROR):
        body = _get(_BoomSB(_seed(10)), "topic_id=t1&page=1&page_size=20")

    assert body["items"] == []
    assert "error" in body  # distinguishable from a legitimate empty
    assert any(
        "pyqs list failed" in rec.getMessage() and rec.levelno >= logging.ERROR
        for rec in caplog.records
    ), "the underlying exception must be logged, not swallowed"
