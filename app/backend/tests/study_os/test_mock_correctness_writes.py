"""X-PR0 — correctness-critical write hardening for the mock attempt engine.

Pins that a silent DB failure on the two correctness-critical finalization
writes no longer leaves an attempt looking submitted with inconsistent marks:

* per-response score write fails  -> SubmissionPersistenceError, attempt stays in_progress
* attempt finalization write fails -> AttemptFinalizationError, attempt stays in_progress
* a best-effort write (job enqueue) failing the same way does NOT raise (scope guard)
* after a simulated mid-finalize failure the submit re-runs cleanly (idempotent, no double-count)
"""
from __future__ import annotations

import pytest

from app.study_os import mock_engine as svc
from app.study_os.mock_engine import (
    AttemptFinalizationError,
    SubmissionPersistenceError,
)
from tests.persona_questions._stub import SBStub, _Exec

# Reuse the engine test fixtures so the seed shape stays in one place.
from tests.study_os.test_mock_engine import _seeded_db


# ─── failure-injecting Supabase wrapper ───────────────────────────────────────
#
# Wraps an SBStub and forces ``execute()`` to return empty ``.data`` for a
# chosen write op on a single target table — exactly what supabase-py reports
# for a misrouted/rejected insert/update. Reads and all other tables pass
# through unchanged, so we isolate one write site at a time.

class _FailQuery:
    def __init__(self, inner, ops):
        self._inner = inner
        self._ops = ops

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
        if "update" in self._ops and i._pending_update not in (None, "__delete__"):
            return _Exec([])
        if "insert" in self._ops and i._pending_insert is not None:
            return _Exec([])
        if "upsert" in self._ops and i._pending_upsert is not None:
            return _Exec([])
        return i.execute()


class _FailWritesSB:
    def __init__(self, inner: SBStub, target_table: str, ops):
        self.db = inner.db
        self._inner = inner
        self._target = target_table
        self._ops = {ops} if isinstance(ops, str) else set(ops)

    def table(self, name: str):
        q = self._inner.table(name)
        return _FailQuery(q, self._ops) if name == self._target else q

    def rpc(self, *a, **k):
        return self._inner.rpc(*a, **k)


def _attempt_row(sb: SBStub, attempt_id: str) -> dict:
    return next(a for a in sb.db["mock_attempts"] if a["id"] == attempt_id)


# ─── response-score write failure ─────────────────────────────────────────────

def test_response_score_write_failure_raises_and_leaves_attempt_unsubmitted():
    sb, _, _ = _seeded_db()
    attempt_id = svc.start_attempt(sb, "user-1", "test-mock-1")["attempt_id"]

    failing = _FailWritesSB(sb, "mock_attempt_responses", "update")
    with pytest.raises(SubmissionPersistenceError):
        svc.submit_attempt(failing, "user-1", attempt_id)

    # The attempt must NOT have flipped to submitted (the safe state).
    assert _attempt_row(sb, attempt_id)["status"] == "in_progress"
    # No compat row was emitted (it lives after the finalization flip).
    assert [r for r in sb.db.get("mock_tests", []) if r.get("user_id") == "user-1"] == []


# ─── attempt finalization write failure ───────────────────────────────────────

def test_attempt_finalization_write_failure_raises():
    sb, _, _ = _seeded_db()
    attempt_id = svc.start_attempt(sb, "user-1", "test-mock-1")["attempt_id"]

    failing = _FailWritesSB(sb, "mock_attempts", "update")
    with pytest.raises(AttemptFinalizationError):
        svc.submit_attempt(failing, "user-1", attempt_id)

    assert _attempt_row(sb, attempt_id)["status"] == "in_progress"
    assert [r for r in sb.db.get("mock_tests", []) if r.get("user_id") == "user-1"] == []


# ─── scope guard: best-effort writes must still swallow failure ────────────────

def test_best_effort_job_enqueue_does_not_raise_on_empty_write():
    """schedule_job uses _safe (best-effort); an empty insert must NOT raise.

    Proves the hardening did not widen to the job-lifecycle writes.
    """
    sb, _, _ = _seeded_db()
    sb.db.setdefault("mock_attempt_jobs", [])
    failing = _FailWritesSB(sb, "mock_attempt_jobs", {"insert", "update"})
    # Must complete without raising.
    svc.schedule_job(failing, svc.JOB_ANALYTICS_RETRY, "attempt-xyz")


# ─── re-runnability: idempotent re-submit after a mid-finalize failure ─────────

def test_resubmit_after_failed_finalize_rescores_without_double_count():
    sb, _, questions = _seeded_db()
    attempt_id = svc.start_attempt(sb, "user-1", "test-mock-1")["attempt_id"]
    for i, q in enumerate(questions):
        svc.save_answer(
            sb, "user-1", attempt_id, q["id"], q["correct_option_id"],
            is_marked_for_review=False, client_seq=i + 1, time_spent_sec=5,
        )

    # First submit fails at the per-response score write.
    failing = _FailWritesSB(sb, "mock_attempt_responses", "update")
    with pytest.raises(SubmissionPersistenceError):
        svc.submit_attempt(failing, "user-1", attempt_id)
    assert _attempt_row(sb, attempt_id)["status"] == "in_progress"

    # Retry on the healthy client re-scores cleanly.
    result = svc.submit_attempt(sb, "user-1", attempt_id)
    assert result["status"] == "submitted"
    assert result["total_correct"] == len(questions)

    # Exactly one compat row — no double-count from the partial first run.
    user_rows = [r for r in sb.db["mock_tests"] if r.get("user_id") == "user-1"]
    assert len(user_rows) == 1
