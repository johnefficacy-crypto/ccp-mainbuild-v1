"""GQR-S1 scope-isolation regressions for learner-facing Quant strategies."""
from __future__ import annotations

from app.study_os import quant_heuristics as qh
from tests.persona_questions._stub import SBStub


def _subject(family="quant"):
    return {
        "slug": "quantitative-aptitude" if family == "quant" else "reasoning",
        "subject_group": "numerical" if family == "quant" else "reasoning",
    }


def _heuristic(
    *,
    topic="quant-topic",
    micro=None,
    topic_family="quant",
    micro_family="quant",
    micro_parent=None,
):
    return {
        "id": "h1",
        "topic_id": topic,
        "microtopic_id": micro,
        "topic": {"subject": _subject(topic_family)} if topic else None,
        "microtopic": {
            "parent_topic_id": topic if micro_parent is None else micro_parent,
            "subject": _subject(micro_family),
        } if micro else None,
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


def test_link_read_embeds_question_scope_without_extra_query():
    sb = SBStub({
        "quant_heuristics": [_heuristic()],
        "quant_question_heuristics": [_link()],
    })
    selects = []
    original_table = sb.table

    def _table(name):
        query = original_table(name)
        original_select = query.select

        def _select(columns, *args, **kwargs):
            selects.append((name, columns))
            return original_select(columns, *args, **kwargs)

        query.select = _select
        return query

    sb.table = _table  # type: ignore[assignment]
    qh.heuristics_for_questions(sb, ["q1"])

    link_select = next(columns for table, columns in selects if table == "quant_question_heuristics")
    heuristic_select = next(columns for table, columns in selects if table == "quant_heuristics")
    assert "question:mock_question_bank!inner(topic_id,microtopic_id)" in link_select
    assert "quant_heuristics_topic_id_fkey" in heuristic_select
    assert "quant_heuristics_microtopic_id_fkey" in heuristic_select
    assert "subject:subjects(slug,subject_group)" in heuristic_select
    assert [table for table, _columns in selects] == [
        "quant_question_heuristics",
        "quant_heuristics",
    ]


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


def test_non_quant_canonical_scope_fails_closed_even_when_question_ids_match():
    assert _read(
        _heuristic(topic="reasoning-topic", topic_family="reasoning"),
        _link(topic="reasoning-topic"),
    ) == []


def test_inconsistent_topic_microtopic_parent_fails_closed():
    assert _read(
        _heuristic(
            topic="quant-topic",
            micro="percentages",
            micro_parent="other-topic",
        ),
        _link(topic="quant-topic", micro="percentages"),
    ) == []


def test_missing_canonical_scope_metadata_fails_closed():
    heuristic = _heuristic()
    heuristic.pop("topic")
    assert _read(heuristic, _link()) == []


def test_missing_embedded_question_scope_fails_closed():
    link = _link()
    link.pop("question")
    assert _read(_heuristic(), link) == []
