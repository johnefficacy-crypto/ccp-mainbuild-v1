"""PYQ v2 PR-7 — unified attempt evidence adapter.

Normalizes mock attempts (frozen snapshot) and direct-PYQ trap-drill attempts
(live pyq_questions lineage) into one canonical contract
(DerivedAttemptAnalytics), so mastery / planner / persona consume a single shape.
Read-only: no writes here (wiring trap-drill into mastery is PR-8).
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from app.study_os import attempt_evidence as ev
from tests.persona_questions._stub import SBStub

ATTEMPT_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


def _mock_db() -> SBStub:
    return SBStub({
        "mock_attempts": [{"id": ATTEMPT_ID, "user_id": "u1"}],
        "mock_attempt_responses": [
            {"attempt_id": ATTEMPT_ID, "question_id": "q1", "selected_option_id": "o1", "is_correct": True,
             "time_spent_sec": 30, "question_snapshot": {"topic_id": "t1", "microtopic_id": "m1", "difficulty": "hard",
                                                          "source_type": "pyq", "pyq_year": 2024, "expected_time_sec": 60, "confidence": "0.7"}},
            # unanswered (selected None) — registers topic but not counted in accuracy
            {"attempt_id": ATTEMPT_ID, "question_id": "q2", "selected_option_id": None, "is_correct": False,
             "time_spent_sec": 0, "question_snapshot": {"topic_id": "t1", "microtopic_id": "m1"}},
            {"attempt_id": ATTEMPT_ID, "question_id": "q3", "selected_option_id": "o3", "is_correct": False,
             "time_spent_sec": 10, "question_snapshot": {"topic_id": "t2"}},
            # no topic → skipped entirely
            {"attempt_id": ATTEMPT_ID, "question_id": "q4", "selected_option_id": "o4", "is_correct": True,
             "time_spent_sec": 5, "question_snapshot": {}},
        ],
        "mock_attempt_response_classification": [
            {"attempt_id": ATTEMPT_ID, "question_id": "q3", "error_type": "concept_gap"},
        ],
    })


def test_mock_evidence_normalizes_questions_topics_and_error_types():
    result = ev.load_mock_attempt_evidence(_mock_db(), ATTEMPT_ID)
    assert result is not None
    assert str(result.attempt_id) == ATTEMPT_ID
    assert result.user_id == "u1"
    # q4 (no topic) dropped; q1/q2/q3 kept
    by_q = {q.question_id: q for q in result.questions}
    assert set(by_q) == {"q1", "q2", "q3"}
    assert by_q["q1"].attempted is True and by_q["q1"].source_type == "pyq" and by_q["q1"].pyq_year == 2024
    assert by_q["q1"].difficulty == "hard" and by_q["q1"].confidence == Decimal("0.7")
    assert by_q["q2"].attempted is False  # unanswered
    assert by_q["q3"].error_type == "concept_gap"
    assert by_q["q1"].error_type is None  # no classification row
    topics = {(t.topic_id, t.microtopic_id): t for t in result.topics}
    # (t1,m1): q1 answered-correct counts, q2 unanswered registers topic but not counted
    assert topics[("t1", "m1")].attempted == 1 and topics[("t1", "m1")].correct == 1 and topics[("t1", "m1")].accuracy_pct == Decimal("100")
    assert topics[("t2", None)].attempted == 1 and topics[("t2", None)].correct == 0 and topics[("t2", None)].accuracy_pct == Decimal("0")


def test_mock_evidence_missing_attempt_returns_none():
    assert ev.load_mock_attempt_evidence(_mock_db(), "no-such-attempt") is None


def _trap_db() -> SBStub:
    return SBStub({
        "user_trap_drill_attempts": [
            {"user_id": "u1", "exam_id": "e1", "drill_seed": "seed-1", "question_id": "pq1", "topic_id": "t1", "is_correct": True},
            {"user_id": "u1", "exam_id": "e1", "drill_seed": "seed-1", "question_id": "pq2", "topic_id": "t1", "is_correct": False},
            # null topic → skipped
            {"user_id": "u1", "exam_id": "e1", "drill_seed": "seed-1", "question_id": "pq3", "topic_id": None, "is_correct": True},
            # different session
            {"user_id": "u1", "exam_id": "e1", "drill_seed": "other", "question_id": "pq9", "topic_id": "t1", "is_correct": True},
        ],
        "pyq_questions": [
            {"id": "pq1", "observed_difficulty": "hard", "pyq_paper_id": "pp1"},
            {"id": "pq2", "observed_difficulty": None, "pyq_paper_id": "pp1"},
        ],
        "pyq_papers": [{"id": "pp1", "year": 2019}],
    })


def test_trap_drill_evidence_normalizes_to_same_contract():
    result = ev.load_trap_drill_evidence(_trap_db(), user_id="u1", exam_id="e1", drill_seed="seed-1")
    assert result is not None
    assert result.user_id == "u1"
    # deterministic synthetic attempt id
    assert result.attempt_id == uuid.uuid5(ev._TRAP_DRILL_NS, "u1:e1:seed-1")
    by_q = {q.question_id: q for q in result.questions}
    assert set(by_q) == {"pq1", "pq2"}  # pq3 null-topic skipped, "other" seed excluded
    assert by_q["pq1"].source_type == "pyq" and by_q["pq1"].difficulty == "hard" and by_q["pq1"].pyq_year == 2019
    assert by_q["pq1"].attempted is True and by_q["pq1"].error_type is None
    assert by_q["pq2"].difficulty == "medium"  # observed_difficulty None → medium
    topics = {t.topic_id: t for t in result.topics}
    assert topics["t1"].attempted == 2 and topics["t1"].correct == 1 and topics["t1"].accuracy_pct == Decimal("50")


def test_trap_drill_empty_session_returns_none():
    assert ev.load_trap_drill_evidence(_trap_db(), user_id="u1", exam_id="e1", drill_seed="ghost") is None


def test_dispatcher_routes_by_source():
    mock_result = ev.load_attempt_evidence(_mock_db(), source=ev.SOURCE_MOCK, attempt_id=ATTEMPT_ID)
    assert mock_result is not None and mock_result.user_id == "u1"
    trap_result = ev.load_attempt_evidence(_trap_db(), source=ev.SOURCE_TRAP_DRILL, user_id="u1", exam_id="e1", drill_seed="seed-1")
    assert trap_result is not None and len(trap_result.questions) == 2


def test_dispatcher_rejects_unknown_source():
    with pytest.raises(ValueError):
        ev.load_attempt_evidence(_mock_db(), source="essay", attempt_id=ATTEMPT_ID)


def test_trust_level_per_source():
    assert ev.trust_level_for_source(ev.SOURCE_MOCK) == "platform_verified"
    assert ev.trust_level_for_source(ev.SOURCE_TRAP_DRILL) == "platform_verified"
    assert ev.trust_level_for_source("unknown") == "platform_verified"
