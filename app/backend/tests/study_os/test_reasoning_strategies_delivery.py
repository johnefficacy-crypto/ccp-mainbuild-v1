"""GQR-S4 — Reasoning independent-question Solution Strategy delivery.

Covers the batched verified-only Reasoning read (`strategies_for_questions`), its
registration in the shared `solution_strategies` aggregator, and the
`mock_engine.get_review` attachment. Mirrors the Quant (GQR-S1) contract. Contract:
docs/architecture/solution-strategies-improvement-lab.md §8.
"""
from __future__ import annotations

from app.study_os import mock_engine, reasoning_strategies as rs, solution_strategies as ss
from tests.persona_questions._stub import SBStub


def _subject(family):
    return {
        "slug": "reasoning" if family == "reasoning" else "quantitative-aptitude",
        "subject_group": "reasoning" if family == "reasoning" else "numerical",
    }


def _strat(sid, *, status="verified", active=True, name="S", stype="approach",
           topic_id="rt1", microtopic_id=None, topic_family="reasoning",
           microtopic_family="reasoning", microtopic_parent=None, **extra):
    row = {
        "id": sid, "topic_id": topic_id, "microtopic_id": microtopic_id,
        "topic": {"subject": _subject(topic_family)} if topic_id else None,
        "microtopic": {
            "parent_topic_id": topic_id if microtopic_parent is None else microtopic_parent,
            "subject": _subject(microtopic_family),
        } if microtopic_id else None,
        "strategy_code": f"code-{sid}", "name": name, "strategy_type": stype,
        "applicability_rule": {"op": "secret"}, "formula_latex": r"\frac{a}{b}",
        "standard_method": "long way", "faster_method": "fast way",
        "key_observation": "spot the fixed pivot", "worked_example": "eg",
        "common_traps": "trap", "reviewer_status": status,
        "reviewer_notes": "internal note", "reviewed_by": "admin-x",
        "created_by": "author-y", "is_active": active, "updated_at": "2026-07-14T00:00:00Z",
    }
    row.update(extra)
    return row


def _link(qid, sid, *, status="verified", relevance="primary", topic="rt1", micro=None):
    return {
        "id": f"lnk-{qid}-{sid}", "question_id": qid, "strategy_id": sid,
        "relevance": relevance, "reviewer_status": status,
        # SBStub ignores PostgREST select projections, so the fixture carries the
        # embedded bank-question scope the real link query returns.
        "question": {"topic_id": topic, "microtopic_id": micro},
    }


# ── batched reasoning read ────────────────────────────────────────────────────

def test_batched_read_one_link_one_strategy_query():
    calls = {"n": 0}
    sb = SBStub({
        "reasoning_question_strategies": [_link("q1", "s1"), _link("q2", "s2")],
        "reasoning_strategies": [_strat("s1", name="A"), _strat("s2", name="B")],
    })
    orig = sb.table

    def _counting(name):
        if name in ("reasoning_question_strategies", "reasoning_strategies"):
            calls["n"] += 1
        return orig(name)

    sb.table = _counting  # type: ignore[assignment]
    out = rs.strategies_for_questions(sb, ["q1", "q2", "q1", "", None])
    assert set(out) == {"q1", "q2"}
    assert calls["n"] == 2
    assert [s["id"] for s in out["q1"]] == ["s1"]
    assert [s["id"] for s in out["q2"]] == ["s2"]


def test_batched_gate_excludes_unverified_or_inactive():
    sb = SBStub({
        "reasoning_question_strategies": [
            _link("q1", "s-ok"),
            _link("q1", "s-pending"),
            _link("q1", "s-inactive"),
            _link("q1", "s-badlink", status="pending"),
        ],
        "reasoning_strategies": [
            _strat("s-ok"),
            _strat("s-pending", status="pending"),
            _strat("s-inactive", active=False),
            _strat("s-badlink"),
        ],
    })
    assert [s["id"] for s in rs.strategies_for_questions(sb, ["q1"])["q1"]] == ["s-ok"]


def test_batched_rejects_wrong_scope_and_cross_subject():
    sb = SBStub({
        "reasoning_question_strategies": [
            _link("q-topic-mismatch", "s-topic", topic="other-topic"),
            _link("q-micro-mismatch", "s-micro", topic="rt1", micro="other-micro"),
            _link("q-quant-subject", "s-quant", topic="rt1"),
            _link("q-ok", "s-micro", topic="rt1", micro="rm1"),
        ],
        "reasoning_strategies": [
            _strat("s-topic", topic_id="rt1", microtopic_id=None),
            _strat("s-micro", topic_id="rt1", microtopic_id="rm1"),
            # A strategy whose scope resolves to Quant taxonomy must never attach.
            _strat("s-quant", topic_id="rt1", topic_family="quant"),
        ],
    })
    out = rs.strategies_for_questions(
        sb, ["q-topic-mismatch", "q-micro-mismatch", "q-quant-subject", "q-ok"])
    assert out["q-topic-mismatch"] == []
    assert out["q-micro-mismatch"] == []
    assert out["q-quant-subject"] == []
    assert [s["id"] for s in out["q-ok"]] == ["s-micro"]


def test_batched_no_cross_question_leak_and_ordering():
    sb = SBStub({
        "reasoning_question_strategies": [
            _link("q1", "s1", relevance="related"),
            _link("q1", "s2", relevance="primary"),
            _link("q2", "s1", relevance="primary"),
        ],
        "reasoning_strategies": [_strat("s1", name="Zeta"), _strat("s2", name="Alpha")],
    })
    out = rs.strategies_for_questions(sb, ["q1", "q2"])
    assert [s["id"] for s in out["q1"]] == ["s2", "s1"]
    assert [s["id"] for s in out["q2"]] == ["s1"]
    assert out["q2"][0]["relevance"] == "primary"


def test_batched_authority_strips_governance_fields():
    sb = SBStub({
        "reasoning_question_strategies": [_link("q1", "s1")],
        "reasoning_strategies": [_strat("s1")],
    })
    raw = rs.strategies_for_questions(sb, ["q1"])["q1"][0]
    for forbidden in (
        "applicability_rule", "reviewer_status", "reviewer_notes", "reviewed_by",
        "created_by", "updated_at", "is_active", "strategy_code", "topic_id",
        "microtopic_id",
    ):
        assert forbidden not in raw


def test_single_question_wrapper_delegates():
    sb = SBStub({
        "reasoning_question_strategies": [_link("q1", "s1")],
        "reasoning_strategies": [_strat("s1")],
    })
    assert rs.strategies_for_question(sb, "q1") == rs.strategies_for_questions(sb, ["q1"])["q1"]


def test_batched_empty_input_no_reads():
    sb = SBStub({"reasoning_question_strategies": [], "reasoning_strategies": []})
    sb.table = lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no query on empty input"))
    assert rs.strategies_for_questions(sb, []) == {}
    assert rs.strategies_for_question(sb, "") == []


# ── aggregator registration ───────────────────────────────────────────────────

def test_aggregator_projects_reasoning_with_key_observation_and_subject_tag():
    sb = SBStub({
        "quant_question_heuristics": [], "quant_heuristics": [],
        "reasoning_question_strategies": [_link("q1", "s1", relevance="secondary")],
        "reasoning_strategies": [_strat("s1", name="Elimination by fixed pivot")],
    })
    dto = ss.strategies_for_questions(sb, ["q1"])["q1"][0]
    assert set(dto) == set(ss.ALLOWED_FIELDS)
    assert dto["subject_family"] == "reasoning"
    assert dto["strategy_type"] == "approach"
    assert dto["key_observation"] == "spot the fixed pivot"
    assert dto["relevance"] == "secondary"
    for forbidden in ("applicability_rule", "reviewer_status", "strategy_code"):
        assert forbidden not in dto


def test_aggregator_composes_sources_with_per_subject_isolation():
    # A single canonical question has ONE topic scope, so it can never match both
    # a Quant heuristic and a Reasoning strategy (a topic belongs to one subject).
    # The aggregator composes sources ACROSS an attempt while keeping each
    # question's strategies to its own subject — proven with two questions, each
    # scoped to its own family; neither source leaks onto the other's question.
    sb = SBStub({
        "quant_question_heuristics": [{
            "id": "ql", "question_id": "q-quant", "heuristic_id": "h1",
            "relevance": "primary", "reviewer_status": "verified",
            "question": {"topic_id": "qt1", "microtopic_id": None},
        }],
        "quant_heuristics": [{
            "id": "h1", "topic_id": "qt1", "microtopic_id": None,
            "topic": {"subject": _subject("quant")},
            "name": "Quant one", "heuristic_type": "shortcut",
            "shortcut_method": "fast", "reviewer_status": "verified", "is_active": True,
        }],
        "reasoning_question_strategies": [_link("q-reason", "s1", topic="rt1")],
        "reasoning_strategies": [_strat("s1", name="Reasoning one", topic_id="rt1")],
    })
    out = ss.strategies_for_questions(sb, ["q-quant", "q-reason"])
    assert [d["subject_family"] for d in out["q-quant"]] == ["quant"]
    assert [d["subject_family"] for d in out["q-reason"]] == ["reasoning"]


def test_aggregator_reasoning_source_fails_soft(monkeypatch):
    sb = SBStub({"quant_question_heuristics": [], "quant_heuristics": [],
                 "reasoning_question_strategies": [], "reasoning_strategies": []})
    monkeypatch.setattr(
        ss.reasoning_strategies, "strategies_for_questions",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("boom")))
    assert ss.strategies_for_questions(sb, ["q1"]) == {"q1": []}


# ── get_review attachment ─────────────────────────────────────────────────────

def test_get_review_attaches_reasoning_strategies():
    sb = SBStub({
        "mock_attempts": [{
            "id": "att-1", "user_id": "u-1", "status": "submitted",
            "template_snapshot": {"question_ids": ["q1", "q2"]},
        }],
        "mock_attempt_responses": [
            {"id": "r1", "attempt_id": "att-1", "question_id": "q1",
             "question_snapshot": {"question_text": "Q1", "question_type": "mcq"},
             "selected_option_id": "o1", "is_correct": True, "time_spent_sec": 5},
            {"id": "r2", "attempt_id": "att-1", "question_id": "q2",
             "question_snapshot": {"question_text": "Q2", "question_type": "mcq"},
             "selected_option_id": "o2", "is_correct": False, "time_spent_sec": 9},
        ],
        "mock_attempt_response_classification": [],
        "quant_question_heuristics": [], "quant_heuristics": [],
        "reasoning_question_strategies": [_link("q1", "s1")],
        "reasoning_strategies": [_strat("s1", name="Blood-relation chart")],
    })
    out = mock_engine.get_review(sb, "u-1", "att-1")
    by_qid = {q["question_id"]: q for q in out["questions"]}
    got = by_qid["q1"]["solution_strategies"]
    assert [s["name"] for s in got] == ["Blood-relation chart"]
    assert got[0]["subject_family"] == "reasoning"
    assert "reviewer_status" not in got[0]
    assert by_qid["q2"]["solution_strategies"] == []



# ── GQR-S7 set/stimulus-aware delivery ───────────────────────────────────────

def _stimulus_link(stimulus_id, strategy_id, *, status="verified", relevance="primary"):
    return {
        "id": f"sl-{stimulus_id}-{strategy_id}",
        "stimulus_id": stimulus_id,
        "strategy_id": strategy_id,
        "reviewer_status": status,
        "relevance": relevance,
    }


def test_stimulus_read_is_batched_gated_and_matches_every_question_scope():
    calls = {"n": 0}
    sb = SBStub({
        "reasoning_stimulus_strategies": [
            _stimulus_link("stim-1", "s-set"),
            _stimulus_link("stim-1", "s-pending-link", status="pending"),
            _stimulus_link("stim-2", "s-micro"),
        ],
        "reasoning_strategies": [
            _strat("s-set", name="Fix the reference frame"),
            _strat("s-pending-link"),
            _strat("s-micro", topic_id="rt1", microtopic_id="rm1"),
        ],
    })
    orig = sb.table

    def _counting(name):
        if name in ("reasoning_stimulus_strategies", "reasoning_strategies"):
            calls["n"] += 1
        return orig(name)

    sb.table = _counting  # type: ignore[assignment]
    out = rs.strategies_for_stimuli(
        sb,
        {
            "stim-1": [
                {"topic_id": "rt1", "microtopic_id": "rm1"},
                {"topic_id": "rt1", "microtopic_id": "rm2"},
            ],
            # Microtopic-scoped strategy must fail closed because the second
            # question in this set has a different microtopic.
            "stim-2": [
                {"topic_id": "rt1", "microtopic_id": "rm1"},
                {"topic_id": "rt1", "microtopic_id": "rm2"},
            ],
        },
    )
    assert calls["n"] == 2
    assert [row["id"] for row in out["stim-1"]] == ["s-set"]
    assert out["stim-2"] == []
    assert "reviewer_status" not in out["stim-1"][0]


def test_stimulus_aggregator_is_fail_soft_and_projects_shared_dto(monkeypatch):
    sb = SBStub({
        "reasoning_stimulus_strategies": [_stimulus_link("stim-1", "s1")],
        "reasoning_strategies": [_strat("s1", name="Build the arrangement grid")],
    })
    dto = ss.strategies_for_stimuli(
        sb, {"stim-1": [{"topic_id": "rt1", "microtopic_id": None}]}
    )["stim-1"][0]
    assert set(dto) == set(ss.ALLOWED_FIELDS)
    assert dto["subject_family"] == "reasoning"

    monkeypatch.setattr(
        ss.reasoning_strategies,
        "strategies_for_stimuli",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    assert ss.strategies_for_stimuli(
        sb, {"stim-1": [{"topic_id": "rt1"}]}
    ) == {"stim-1": []}


def test_get_review_emits_one_shared_stimulus_group_and_preserves_question_strategy():
    shared_stimulus = {
        "id": "frozen-row",
        "pyq_stimulus_id": "stim-1",
        "stimulus_type": "passage",
        "content_text": "Five people sit in a row.",
        "language": "en",
        "display_order": 0,
    }
    sb = SBStub({
        "mock_attempts": [{
            "id": "att-set", "user_id": "u-1", "status": "submitted",
            "template_snapshot": {"question_ids": ["q1", "q2", "q3"]},
        }],
        "mock_attempt_responses": [
            {
                "attempt_id": "att-set", "question_id": "q1",
                "question_snapshot": {
                    "question_text": "Q1", "topic_id": "rt1", "microtopic_id": "rm1",
                    "stimuli": [shared_stimulus],
                },
                "is_correct": True,
            },
            {
                "attempt_id": "att-set", "question_id": "q2",
                "question_snapshot": {
                    "question_text": "Q2", "topic_id": "rt1", "microtopic_id": "rm2",
                    "stimuli": [shared_stimulus],
                },
                "is_correct": False,
            },
            {
                "attempt_id": "att-set", "question_id": "q3",
                "question_snapshot": {
                    "question_text": "Q3", "topic_id": "rt1", "microtopic_id": "rm1",
                    "stimuli": [],
                },
                "is_correct": False,
            },
        ],
        "mock_attempt_response_classification": [],
        "quant_question_heuristics": [],
        "quant_heuristics": [],
        "reasoning_question_strategies": [_link("q1", "s-question")],
        "reasoning_stimulus_strategies": [_stimulus_link("stim-1", "s-set")],
        "reasoning_strategies": [
            _strat("s-question", name="Question-specific elimination"),
            _strat("s-set", name="Build one arrangement grid"),
        ],
    })

    payload = mock_engine.get_review(sb, "u-1", "att-set")
    assert len(payload["stimulus_solution_strategies"]) == 1
    group = payload["stimulus_solution_strategies"][0]
    assert group["pyq_stimulus_id"] == "stim-1"
    assert group["question_ids"] == ["q1", "q2"]
    assert group["first_attempt_order"] == 1
    assert [row["name"] for row in group["strategies"]] == ["Build one arrangement grid"]
    by_qid = {row["question_id"]: row for row in payload["questions"]}
    assert by_qid["q1"]["solution_strategies"][0]["name"] == "Question-specific elimination"
    assert "stimulus_solution_strategies" not in by_qid["q1"]
    assert by_qid["q2"]["solution_strategies"] == []
    assert by_qid["q3"]["solution_strategies"] == []
