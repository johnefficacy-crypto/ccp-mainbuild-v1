from __future__ import annotations

from decimal import Decimal

from fastapi import HTTPException

from app.study_os.attempt_analytics.service import derive_attempt_analytics, compute_and_persist
from app.study_os.attempt_analytics.time_analytics import compute_dwell_times


def _q(i: int, **overrides):
    base = {
        "question_id": f"q{i}",
        "selected_option_id": "o" if i % 2 else None,
        "is_correct": bool(i % 3 == 0),
        "is_marked_for_review": False,
        "is_visited": True,
        "time_spent_sec": 60,
        "question_snapshot": {
            "marks": "1",
            "negative_marks": "0.25",
            "expected_time_sec": 60,
            "difficulty": "medium",
            "section_index": 0 if i <= 15 else 1,
            "section_name": "S1" if i <= 15 else "S2",
            "topic_id": "11111111-1111-1111-1111-111111111111",
            "microtopic_id": "22222222-2222-2222-2222-222222222222",
            "subject": "Quant",
            "option_tags": {"o": {"role": "normal"}},
        },
    }
    base.update(overrides)
    return base


def test_derivation_decimal_negative_marking_and_classifications():
    responses = [_q(i) for i in range(1, 31)]
    # craft each error type
    responses[0].update({"is_correct": True})  # correct
    responses[1].update({"is_correct": False, "selected_option_id": "o", "time_spent_sec": 10})  # silly
    responses[2].update({"is_correct": False, "selected_option_id": "o", "time_spent_sec": 60}); responses[2]["question_snapshot"]["option_tags"] = {"o": {"role": "calculation_layer"}}  # calc
    responses[3].update({"is_correct": False, "selected_option_id": "o", "time_spent_sec": 60}); responses[3]["question_snapshot"]["option_tags"] = {"o": {"role": "trap"}}  # trap
    responses[4].update({"is_correct": False, "time_spent_sec": 100})  # concept
    responses[5].update({"is_correct": False, "selected_option_id": "o"})  # knowledge
    responses[6].update({"is_visited": False, "selected_option_id": None})  # time_pressure
    responses[7].update({"is_marked_for_review": True, "selected_option_id": None})  # marked

    attempt = {"id": "a1", "status": "submitted", "submitted_at": "2026-01-01T00:30:00+00:00", "template_snapshot": {"duration_sec": 1800}}
    out = derive_attempt_analytics(attempt, responses, [])
    assert out.summary.score_raw.quantize(Decimal("0.01"))
    assert "mock_attempt_events missing; fallback to responses.time_spent_sec" in out.warnings
    labels = {r.error_type for r in out.response_classification[:8]}
    assert labels == {"correct", "silly_mistake", "calc_error", "option_trap", "concept_gap", "knowledge_gap", "time_pressure_unattempted", "marked_unanswered"}


def test_negative_marking_precise():
    responses = []
    for i in range(1, 16):
        responses.append(_q(i, selected_option_id="o", is_correct=i <= 10))
    attempt = {"id": "a2", "status": "submitted", "submitted_at": "2026-01-01T00:30:00+00:00", "template_snapshot": {"duration_sec": 1800}}
    out = derive_attempt_analytics(attempt, responses, [])
    assert out.summary.score_raw == Decimal("8.75")


def test_unsubmitted_422():
    class R:
        def __init__(self, data): self.data = data
    class T:
        def __init__(self, sb, name): self.sb = sb; self.name = name
        def select(self, *_): return self
        def eq(self, *_): return self
        def limit(self, *_): return self
        def execute(self):
            if self.name == "mock_attempts":
                return R([{"id": "a", "status": "in_progress"}])
            return R([])
    class SB:
        def table(self, n): return T(self, n)
    try:
        compute_and_persist(SB(), "a")
    except HTTPException as e:
        assert e.status_code == 422
    else:
        raise AssertionError("expected 422")


def test_dwell_times_from_occurred_at_events():
    """DB-shaped event rows using occurred_at should be used for dwell time computation."""
    responses = [
        {"question_id": "q1", "time_spent_sec": 999},
        {"question_id": "q2", "time_spent_sec": 999},
    ]
    events = [
        {
            "event_type": "question.visited",
            "question_id": "q1",
            "occurred_at": "2026-01-01T00:00:00+00:00",
            "source": "client",
        },
        {
            "event_type": "question.visited",
            "question_id": "q2",
            "occurred_at": "2026-01-01T00:01:30+00:00",
            "source": "client",
        },
    ]
    submitted_at = "2026-01-01T00:03:00+00:00"
    by_q, warnings, stats = compute_dwell_times(responses, events, submitted_at)

    # The fallback warning must NOT appear — events were used
    assert "mock_attempt_events missing; fallback to responses.time_spent_sec" not in warnings
    # At least one event must have been consumed
    assert stats["events_used"] > 0
    # Dwell times must come from event timestamps, not from time_spent_sec (999)
    assert by_q["q1"] == 90   # 00:00:00 → 00:01:30 = 90 s
    assert by_q["q2"] == 90   # 00:01:30 → submitted 00:03:00 = 90 s


def test_dwell_times_created_at_is_malformed():
    """Event rows with created_at (wrong field) must be counted as malformed and skipped."""
    responses = [
        {"question_id": "q1", "time_spent_sec": 42},
    ]
    events = [
        {
            "event_type": "question.visited",
            "question_id": "q1",
            # Wrong field name — the DB column is occurred_at, not created_at
            "created_at": "2026-01-01T00:00:00+00:00",
            "source": "client",
        },
    ]
    submitted_at = "2026-01-01T00:01:00+00:00"
    by_q, warnings, stats = compute_dwell_times(responses, events, submitted_at)

    # The malformed event must have been counted
    assert stats["events_malformed"] >= 1
    # No events should have been used for dwell time
    assert stats["events_used"] == 0
    # Fallback to time_spent_sec should apply
    assert by_q["q1"] == 42
