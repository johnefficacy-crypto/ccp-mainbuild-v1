"""PR-fix-10a — answer persistence correctness invariant tests.

Three invariants verified:

1. QUESTION_ANSWERED event must not be recorded if the response row update raises.
2. The answer endpoint returns 503 (not 200) when the DB update fails.
3. Submit returns 409 when client claims more answered questions than the DB has.

These tests fail before PR-fix-10a lands and pass after. Inverting any of
Fix 1–4 in a throwaway branch causes at least one test here to fail.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import mock_engine as mock_engine_api
from app.core.auth import get_current_user
from app.study_os import mock_engine as svc
from app.study_os.mock_engine import AnswerPersistenceError
from app.study_os.attempt_event_types import QUESTION_ANSWERED
from tests.persona_questions._stub import SBStub, _Query, _Exec
from tests.study_os.test_mock_engine import _seeded_db


# ── helpers ────────────────────────────────────────────────────────────────────

def _count_question_answered(sb: SBStub) -> int:
    return sum(
        1
        for e in sb.db.get("mock_attempt_events", [])
        if e.get("event_type") == QUESTION_ANSWERED
    )


class _RaisingQuery(_Query):
    """A _Query that raises on execute() when updating mock_attempt_responses."""

    def execute(self):
        if self.name == "mock_attempt_responses" and self._pending_update is not None:
            raise Exception("simulated DB failure — 22003 value out of range for type integer")
        return super().execute()


class _RaisingResponseSBStub(SBStub):
    """SBStub that injects a DB error on any mock_attempt_responses UPDATE."""

    def table(self, name: str):
        q = _RaisingQuery(name, self.db)
        return q


class _EmptyUpdateQuery(_Query):
    """A _Query that returns 0 updated rows for mock_attempt_responses updates."""

    def execute(self):
        if self.name == "mock_attempt_responses" and self._pending_update is not None:
            return _Exec([])  # 0 rows updated — row not found
        return super().execute()


class _EmptyUpdateSBStub(SBStub):
    """SBStub that returns 0 updated rows for mock_attempt_responses."""

    def table(self, name: str):
        return _EmptyUpdateQuery(name, self.db)


def _client(sb: SBStub, user_id: str = "user-1"):
    app = FastAPI()
    app.include_router(mock_engine_api.router, prefix="/api")
    app.dependency_overrides[get_current_user] = lambda: {"id": user_id}
    mock_engine_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    return TestClient(app)


# ── Test 1: event not recorded when update raises ──────────────────────────────

def test_event_not_recorded_when_response_update_fails():
    """QUESTION_ANSWERED event must not be recorded if response row update raises."""
    sb_seed, _, questions = _seeded_db()

    # Start the attempt with a normal stub so the rows get created.
    start = svc.start_attempt(sb_seed, "user-1", "test-mock-1")
    attempt_id = start["attempt_id"]
    q = questions[0]
    events_before = _count_question_answered(sb_seed)

    # Now swap to the raising stub (same DB dict — mutations are shared).
    raising_sb = _RaisingResponseSBStub(sb_seed.db)

    with pytest.raises(Exception):
        svc.save_answer(
            raising_sb,
            "user-1",
            attempt_id,
            q["id"],
            q["correct_option_id"],
            is_marked_for_review=False,
            client_seq=1,
            time_spent_sec=5,
        )

    assert _count_question_answered(sb_seed) == events_before, (
        "QUESTION_ANSWERED event recorded despite response update failure. "
        "This violates the source-of-truth invariant."
    )


# ── Test 1b: AnswerPersistenceError raised when 0 rows updated ────────────────

def test_answer_persistence_error_raised_when_zero_rows_updated():
    """save_answer must raise AnswerPersistenceError when update affects 0 rows."""
    sb_seed, _, questions = _seeded_db()
    start = svc.start_attempt(sb_seed, "user-1", "test-mock-1")
    attempt_id = start["attempt_id"]
    q = questions[0]

    zero_sb = _EmptyUpdateSBStub(sb_seed.db)

    with pytest.raises(AnswerPersistenceError):
        svc.save_answer(
            zero_sb,
            "user-1",
            attempt_id,
            q["id"],
            q["correct_option_id"],
            is_marked_for_review=False,
            client_seq=1,
            time_spent_sec=5,
        )


# ── Test 2: API returns 503 on persistence failure ────────────────────────────

def test_api_returns_503_on_persistence_failure():
    """Answer endpoint must return 503, not 200, when DB update fails."""
    sb_seed, _, questions = _seeded_db()
    start = svc.start_attempt(sb_seed, "user-1", "test-mock-1")
    attempt_id = start["attempt_id"]
    q = questions[0]

    # Use a stub that raises on response update.
    raising_sb = _RaisingResponseSBStub(sb_seed.db)
    client = _client(raising_sb)

    response = client.post(
        f"/api/study/mocks/attempts/{attempt_id}/answer",
        json={
            "question_id": q["id"],
            "selected_option_id": q["correct_option_id"],
            "client_seq": 1,
        },
    )
    assert response.status_code == 503, (
        f"Expected 503 on persistence failure, got {response.status_code}"
    )
    body = response.json()
    assert body.get("error") == "persistence_failed" or (
        # FastAPI wraps the detail dict; handle both shapes.
        isinstance(body.get("detail"), dict)
        and body["detail"].get("error") == "persistence_failed"
    ), f"Unexpected body: {body}"
    assert response.headers.get("Retry-After") == "1"


# ── Test 3: submit returns 409 when client claims more than DB ────────────────

def test_submit_rejects_when_client_claims_more_than_db():
    """Submit must refuse if client says answered=20 but DB has answered=0."""
    sb, _, questions = _seeded_db()
    start = svc.start_attempt(sb, "user-1", "test-mock-1")
    attempt_id = start["attempt_id"]

    # Save nothing — DB has 0 answered.
    client = _client(sb)

    response = client.post(
        f"/api/study/mocks/attempts/{attempt_id}/submit",
        json={"claimed_answered_count": 20},
    )
    assert response.status_code == 409, (
        f"Expected 409 on client/server mismatch, got {response.status_code}"
    )
    body = response.json()
    detail = body.get("detail") or body
    if isinstance(detail, dict):
        assert detail.get("error") == "client_server_mismatch", f"Unexpected detail: {detail}"


def test_submit_accepts_when_claimed_count_matches_db():
    """Submit must succeed when claimed_answered_count equals or is less than DB count."""
    sb, _, questions = _seeded_db()
    start = svc.start_attempt(sb, "user-1", "test-mock-1")
    attempt_id = start["attempt_id"]
    q = questions[0]

    # Save one answer.
    svc.save_answer(
        sb, "user-1", attempt_id, q["id"], q["correct_option_id"],
        is_marked_for_review=False, client_seq=1, time_spent_sec=5,
    )

    client = _client(sb)

    # claimed_answered_count=1 matches DB (1 answered).
    response = client.post(
        f"/api/study/mocks/attempts/{attempt_id}/submit",
        json={"claimed_answered_count": 1},
    )
    assert response.status_code == 200, (
        f"Expected 200 when claimed count matches DB, got {response.status_code}: {response.text}"
    )


def test_submit_accepts_null_claimed_count():
    """Submit with no claimed_answered_count skips the consistency check."""
    sb, _, _ = _seeded_db()
    start = svc.start_attempt(sb, "user-1", "test-mock-1")
    attempt_id = start["attempt_id"]

    client = _client(sb)
    response = client.post(
        f"/api/study/mocks/attempts/{attempt_id}/submit",
        json={},
    )
    assert response.status_code == 200, (
        f"Expected 200 with no claimed_answered_count, got {response.status_code}: {response.text}"
    )
