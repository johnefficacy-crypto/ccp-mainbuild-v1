"""GQR-S1 scope-isolation regressions for learner-facing Quant strategies."""
from __future__ import annotations

from app.study_os import quant_heuristics as qh
from tests.persona_questions._stub import SBStub


def _heuristic(*, topic="quant-topic", micro=None):
    return {
        "id": "h1",
        "topic_id": topic,
        "microtopic_id": micro,
        "name": "Scoped method",
        "heuristic_type": "shortcut",
        "formula_latex": None,
        "standard_method": "method",
        "shortcut_method": "shortcut",
        "worked_example": None,
        "common_traps": None,
        "reviewer_status": "verified",
        "is_active": True,
    }


def _link(*, topic="quant-topic", micro=None):
    return {
        "question_id": "q1",
        "heuristic_id": "h1",
        "relevance": "primary",
        "reviewer_status": "verified",
        "question": {"topic_id": topic, "microtopic_id": micro},
    }


def _read(heuristic, link):
    sb = SBStub({
        "quant_heuristics": [heuristic],
        "quant_question_heuristics": [link],
    })
    return qh.heuristics_for_questions(sb, ["q1"])["q1"]


def test_topic_only_scope_requires_exact_topic_match():
    assert _read(_heuristic(), _link(topic="reasoning-topic")) == []


def test_microtopic_scope_requires_parent_topic_and_microtopic_match():
    heuristic = _heuristic(topic="quant-topic", micro="percentages")

    assert _read(
        heuristic,
        _link(topic="reasoning-topic", micro="percentages"),
    ) == []
    assert _read(
        heuristic,
        _link(topic="quant-topic", micro="profit-loss"),
    ) == []
    assert [row["id"] for row in _read(
        heuristic,
        _link(topic="quant-topic", micro="percentages"),
    )] == ["h1"]


def test_missing_embedded_question_scope_fails_closed():
    link = _link()
    link.pop("question")
    assert _read(_heuristic(), link) == []
