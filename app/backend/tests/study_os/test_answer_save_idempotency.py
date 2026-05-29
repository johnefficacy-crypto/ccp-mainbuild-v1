"""PR-fix-7 — answer-save retry idempotency (AC9).

A client whose first /answer POST fails after the server already committed the
write replays the SAME client_seq on retry. The server must acknowledge that
replay without re-processing: no second response row, no duplicate
QUESTION_ANSWERED event. Verified here at DB row-count level.
"""
from __future__ import annotations

from app.study_os import mock_engine as svc
from app.study_os.attempt_event_types import QUESTION_ANSWERED

from tests.study_os.test_mock_engine import _seeded_db


def _count_question_answered(sb) -> int:
    return sum(
        1
        for e in sb.db.get("mock_attempt_events", [])
        if e.get("event_type") == QUESTION_ANSWERED
    )


def _count_responses(sb, attempt_id, question_id) -> int:
    return sum(
        1
        for r in sb.db.get("mock_attempt_responses", [])
        if r.get("attempt_id") == attempt_id and r.get("question_id") == question_id
    )


def test_retry_same_client_seq_does_not_double_insert():
    sb, _, questions = _seeded_db()
    start = svc.start_attempt(sb, "user-1", "test-mock-1")
    attempt_id = start["attempt_id"]
    q = questions[0]
    correct_opt = q["correct_option_id"]

    # First save commits the write and emits exactly one QUESTION_ANSWERED event.
    first = svc.save_answer(
        sb, "user-1", attempt_id, q["id"], correct_opt,
        is_marked_for_review=False, client_seq=7, time_spent_sec=10,
    )
    assert first["idempotent"] is False
    events_after_first = _count_question_answered(sb)
    rows_after_first = _count_responses(sb, attempt_id, q["id"])
    assert events_after_first == 1
    assert rows_after_first == 1  # pre-inserted row updated in place, not duplicated

    # Retry of the exact same write (same client_seq) — acknowledged, not re-run.
    retry = svc.save_answer(
        sb, "user-1", attempt_id, q["id"], correct_opt,
        is_marked_for_review=False, client_seq=7, time_spent_sec=10,
    )
    assert retry["idempotent"] is True
    assert retry["status"] == "already_recorded"

    # No new event, no new row.
    assert _count_question_answered(sb) == events_after_first
    assert _count_responses(sb, attempt_id, q["id"]) == rows_after_first

    # Stored answer is unchanged and intact.
    state = svc.get_attempt(sb, "user-1", attempt_id)
    answered = next(qq for qq in state["questions"] if qq["question_id"] == q["id"])
    assert answered["selected_option_id"] == correct_opt


def test_multiple_retries_same_seq_stay_idempotent():
    sb, _, questions = _seeded_db()
    start = svc.start_attempt(sb, "user-1", "test-mock-1")
    attempt_id = start["attempt_id"]
    q = questions[1]
    correct_opt = q["correct_option_id"]

    svc.save_answer(sb, "user-1", attempt_id, q["id"], correct_opt,
                    is_marked_for_review=False, client_seq=3, time_spent_sec=5)
    baseline_events = _count_question_answered(sb)

    for _ in range(3):
        out = svc.save_answer(sb, "user-1", attempt_id, q["id"], correct_opt,
                              is_marked_for_review=False, client_seq=3, time_spent_sec=5)
        assert out["status"] == "already_recorded"

    assert _count_question_answered(sb) == baseline_events
    assert _count_responses(sb, attempt_id, q["id"]) == 1


def test_higher_seq_after_failed_retry_records_new_write():
    """A genuinely newer write (higher client_seq) is processed normally."""
    sb, _, questions = _seeded_db()
    start = svc.start_attempt(sb, "user-1", "test-mock-1")
    attempt_id = start["attempt_id"]
    q = questions[2]
    opts = q["options"]
    correct_opt = q["correct_option_id"]
    other = next(o["id"] for o in opts if o["id"] != correct_opt)

    svc.save_answer(sb, "user-1", attempt_id, q["id"], correct_opt,
                    is_marked_for_review=False, client_seq=1, time_spent_sec=5)
    events_after_first = _count_question_answered(sb)

    out = svc.save_answer(sb, "user-1", attempt_id, q["id"], other,
                          is_marked_for_review=False, client_seq=2, time_spent_sec=8)
    assert out["idempotent"] is False
    assert _count_question_answered(sb) == events_after_first + 1
    assert _count_responses(sb, attempt_id, q["id"]) == 1  # still one row, updated in place

    state = svc.get_attempt(sb, "user-1", attempt_id)
    answered = next(qq for qq in state["questions"] if qq["question_id"] == q["id"])
    assert answered["selected_option_id"] == other
