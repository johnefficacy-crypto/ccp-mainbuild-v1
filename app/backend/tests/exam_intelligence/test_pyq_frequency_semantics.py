"""Tests for primary-only PYQ frequency semantics in verified_pyq_topic_counts."""
from __future__ import annotations

from app.exam_intelligence.coverage import verified_pyq_topic_counts
from tests.persona_questions._stub import SBStub


def _paper(exam_id="exam-1"):
    return {"id": "paper-1", "exam_id": exam_id, "trust_status": "verified"}


def _question(qid, paper_id="paper-1", status="verified"):
    return {"id": qid, "pyq_paper_id": paper_id, "reviewer_status": status}


def _tag(qid, tid, role="primary", status="verified"):
    return {"question_id": qid, "topic_id": tid, "reviewer_status": status, "tag_role": role}


def test_primary_only_counts_correctly():
    """q1→t1 primary, q2→t1 primary, q3→t2 primary → {t1: 2, t2: 1}."""
    sb = SBStub({
        "pyq_papers": [_paper()],
        "pyq_questions": [
            _question("q1"),
            _question("q2"),
            _question("q3"),
        ],
        "pyq_question_topic_tags": [
            _tag("q1", "t1", role="primary"),
            _tag("q2", "t1", role="primary"),
            _tag("q3", "t2", role="primary"),
        ],
    })
    result = verified_pyq_topic_counts(sb, "exam-1")
    assert result == {"t1": 2, "t2": 1}


def test_secondary_tag_does_not_inflate():
    """q1 has primary→t1 AND secondary→t2 → {t1: 1}, t2 absent or 0."""
    sb = SBStub({
        "pyq_papers": [_paper()],
        "pyq_questions": [_question("q1")],
        "pyq_question_topic_tags": [
            _tag("q1", "t1", role="primary"),
            _tag("q1", "t2", role="secondary"),
        ],
    })
    result = verified_pyq_topic_counts(sb, "exam-1")
    assert result.get("t1") == 1
    assert result.get("t2", 0) == 0


def test_trap_tag_excluded():
    """q1 has primary→t1 AND trap→t2 → only {t1: 1}."""
    sb = SBStub({
        "pyq_papers": [_paper()],
        "pyq_questions": [_question("q1")],
        "pyq_question_topic_tags": [
            _tag("q1", "t1", role="primary"),
            _tag("q1", "t2", role="trap"),
        ],
    })
    result = verified_pyq_topic_counts(sb, "exam-1")
    assert result.get("t1") == 1
    assert result.get("t2", 0) == 0


def test_calculation_layer_excluded():
    """q1 has primary→t1 AND calculation_layer→t3 → only {t1: 1}."""
    sb = SBStub({
        "pyq_papers": [_paper()],
        "pyq_questions": [_question("q1")],
        "pyq_question_topic_tags": [
            _tag("q1", "t1", role="primary"),
            _tag("q1", "t3", role="calculation_layer"),
        ],
    })
    result = verified_pyq_topic_counts(sb, "exam-1")
    assert result.get("t1") == 1
    assert result.get("t3", 0) == 0


def test_empty_exam_id_returns_empty():
    """verified_pyq_topic_counts(sb, "") == {}."""
    sb = SBStub({
        "pyq_papers": [_paper()],
        "pyq_questions": [_question("q1")],
        "pyq_question_topic_tags": [_tag("q1", "t1")],
    })
    result = verified_pyq_topic_counts(sb, "")
    assert result == {}


def test_unverified_paper_gate():
    """Paper trust_status='pending', question+tag both verified → returns {}."""
    sb = SBStub({
        "pyq_papers": [{"id": "paper-1", "exam_id": "exam-1", "trust_status": "pending"}],
        "pyq_questions": [_question("q1")],
        "pyq_question_topic_tags": [_tag("q1", "t1")],
    })
    result = verified_pyq_topic_counts(sb, "exam-1")
    assert result == {}


def test_pending_question_excluded():
    """Paper verified, question reviewer_status='pending', tag verified → returns {}."""
    sb = SBStub({
        "pyq_papers": [_paper()],
        "pyq_questions": [_question("q1", status="pending")],
        "pyq_question_topic_tags": [_tag("q1", "t1")],
    })
    result = verified_pyq_topic_counts(sb, "exam-1")
    assert result == {}
