"""Tests for mock review and correction-task endpoints in canonical.py."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import canonical as canonical_api
from app.core.auth import get_current_user
from tests.persona_questions._stub import SBStub, _Exec


def _seed() -> dict:
    return {
        "mock_tests": [
            {"id": "m1", "user_id": "u-1", "exam_id": "exam-1", "test_name": "M1"},
            {"id": "m2", "user_id": "other-user", "exam_id": "exam-1"},
        ],
        "study_plans": [{"id": "p1", "user_id": "u-1", "status": "active"}],
        "topics": [
            {"id": "t1", "name": "Percentage", "subject_id": "s1"},
            {"id": "t2", "name": "Profit", "subject_id": "s1"},
        ],
        "profiles": [{"id": "u-1"}],
    }


def _client(sb: SBStub, user_id: str = "u-1") -> TestClient:
    app = FastAPI()
    app.include_router(canonical_api.router, prefix="/api")
    canonical_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[get_current_user] = lambda: {"id": user_id, "role": "user"}
    return app, TestClient(app)


# ─── /mocks/:id/review ────────────────────────────────────────────────────
def test_review_persists_error_types_and_status():
    sb = SBStub(_seed())
    _, client = _client(sb)
    r = client.post(
        "/api/study/mocks/m1/review",
        json={
            "review_status": "reviewed",
            "error_types": {"concept_gap": 3, "time_pressure": 1},
            "notes": "Need to revisit percentages.",
        },
    )
    assert r.status_code == 200
    mock = sb.db["mock_tests"][0]
    assert mock["review_status"] == "reviewed"
    assert mock["error_types"] == {"concept_gap": 3, "time_pressure": 1}
    assert mock["notes"] == "Need to revisit percentages."


def test_review_404_for_another_users_mock():
    sb = SBStub(_seed())
    _, client = _client(sb)
    r = client.post(
        "/api/study/mocks/m2/review",
        json={"review_status": "reviewed"},
    )
    assert r.status_code == 404


def test_review_5xx_when_mock_tests_update_fails_and_does_not_continue():
    """X-PR0: a silent mock_tests update failure must 5xx, not 200, and must NOT
    fall through into the breakdown / mastery / regeneration writes."""
    sb = SBStub(_seed())

    # Force only the mock_tests UPDATE to report an empty write (the ownership
    # SELECT must still succeed so we reach the hardened update).
    class _FailUpdateQuery:
        def __init__(self, inner):
            self._inner = inner

        def __getattr__(self, name):
            attr = getattr(self._inner, name)
            if callable(attr):
                def wrapper(*a, **k):
                    res = attr(*a, **k)
                    return self if res is self._inner else res
                return wrapper
            return attr

        def execute(self):
            i = self._inner
            if i._pending_update not in (None, "__delete__"):
                return _Exec([])
            return i.execute()

    class _FailSB:
        def __init__(self, inner):
            self.db = inner.db
            self._inner = inner

        def table(self, name):
            q = self._inner.table(name)
            return _FailUpdateQuery(q) if name == "mock_tests" else q

        def rpc(self, *a, **k):
            return self._inner.rpc(*a, **k)

    _, client = _client(_FailSB(sb))
    r = client.post(
        "/api/study/mocks/m1/review",
        json={
            "review_status": "reviewed",
            "topic_breakdowns": [{"topic_id": "t1", "wrong_answers": 2}],
        },
    )
    assert r.status_code == 500
    # No continuation: breakdown rows must not have been written.
    assert sb.db.get("mock_topic_breakdowns", []) == []


def test_review_with_topic_breakdowns_aggregates_errors():
    sb = SBStub(_seed())
    _, client = _client(sb)
    r = client.post(
        "/api/study/mocks/m1/review",
        json={
            "review_status": "reviewed",
            "topic_breakdowns": [
                {"topic_id": "t1", "wrong_answers": 2,
                 "error_types": {"concept_gap": 2}},
                {"topic_id": "t2", "wrong_answers": 1,
                 "error_types": {"concept_gap": 1, "misread": 1}},
            ],
        },
    )
    assert r.status_code == 200
    mock = sb.db["mock_tests"][0]
    # error counts aggregated server-side
    assert mock["error_types"] == {"concept_gap": 3, "misread": 1}
    # breakdowns persisted
    assert len(sb.db["mock_topic_breakdowns"]) == 2


def test_review_replaces_prior_breakdowns_idempotently():
    sb = SBStub(_seed())
    _, client = _client(sb)
    client.post(
        "/api/study/mocks/m1/review",
        json={
            "review_status": "reviewed",
            "topic_breakdowns": [
                {"topic_id": "t1", "wrong_answers": 5},
            ],
        },
    )
    # Second call with a different breakdown set must replace, not append.
    client.post(
        "/api/study/mocks/m1/review",
        json={
            "review_status": "reviewed",
            "topic_breakdowns": [
                {"topic_id": "t2", "wrong_answers": 1},
            ],
        },
    )
    assert len(sb.db["mock_topic_breakdowns"]) == 1
    assert sb.db["mock_topic_breakdowns"][0]["topic_id"] == "t2"


# Phase 5: POST /api/study/mocks/{mock_id}/correction-tasks tests that
# previously pinned canonical.py's direct-to-study_tasks behavior have
# been removed. That handler was a pre-Phase-6 duplicate of
# app/api/study_os.py's service-backed flow, which writes to
# mock_correction_tasks (a staging table requiring an explicit apply
# step), not directly to study_tasks. Coverage of the surviving
# study_os.py implementation lives in tests/study_os/test_mocks.py
# (test_draft_correction_tasks_uses_error_patterns,
# test_apply_correction_task_creates_study_task_and_links, etc.).
