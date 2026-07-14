"""GQR-S1 — learner-facing Solution Strategy delivery.

Covers the batched verified-only Quant read (`heuristics_for_questions`), the
normalized governance-stripped projection (`solution_strategies`), and the
`mock_engine.get_review` attachment. Contract:
docs/architecture/solution-strategies-improvement-lab.md.
"""
from __future__ import annotations

from app.study_os import mock_engine, quant_heuristics, solution_strategies as ss
from tests.persona_questions._stub import SBStub


def _heur(hid, *, status="verified", active=True, name="H", htype="shortcut", **extra):
    row = {
        "id": hid, "topic_id": "t1", "microtopic_id": None,
        "heuristic_code": f"code-{hid}", "name": name, "heuristic_type": htype,
        "applicability_rule": {"op": "secret"}, "formula_latex": r"\frac{a}{b}",
        "standard_method": "long way", "shortcut_method": "fast way",
        "worked_example": "eg", "common_traps": "trap",
        "reviewer_status": status, "reviewer_notes": "internal note",
        "reviewed_by": "admin-x", "created_by": "author-y", "is_active": active,
        "updated_at": "2026-07-14T00:00:00Z",
    }
    row.update(extra)
    return row


def _link(qid, hid, *, status="verified", relevance="primary"):
    return {"id": f"lnk-{qid}-{hid}", "question_id": qid, "heuristic_id": hid,
            "relevance": relevance, "reviewer_status": status}


# ── batched quant read ───────────────────────────────────────────────────────

def test_batched_read_one_link_one_heuristic_query():
    calls = {"n": 0}
    sb = SBStub({
        "quant_question_heuristics": [_link("q1", "h1"), _link("q2", "h2")],
        "quant_heuristics": [_heur("h1", name="A"), _heur("h2", name="B")],
    })
    orig_table = sb.table

    def _counting_table(name):
        if name in ("quant_question_heuristics", "quant_heuristics"):
            calls["n"] += 1
        return orig_table(name)

    sb.table = _counting_table  # type: ignore[assignment]
    out = quant_heuristics.heuristics_for_questions(sb, ["q1", "q2", "q1", "", None])
    assert set(out) == {"q1", "q2"}          # dedup + drop empties
    assert calls["n"] == 2                    # exactly one link + one heuristic query
    assert [h["id"] for h in out["q1"]] == ["h1"]
    assert [h["id"] for h in out["q2"]] == ["h2"]


def test_batched_gate_excludes_unverified_link_and_unverified_or_inactive_heuristic():
    sb = SBStub({
        "quant_question_heuristics": [
            _link("q1", "h-ok"),
            _link("q1", "h-pending"),            # link ok, heuristic pending
            _link("q1", "h-inactive"),           # link ok, heuristic inactive
            _link("q1", "h-badlink", status="pending"),  # link not verified
        ],
        "quant_heuristics": [
            _heur("h-ok", status="verified", active=True),
            _heur("h-pending", status="pending", active=True),
            _heur("h-inactive", status="verified", active=False),
            _heur("h-badlink", status="verified", active=True),
        ],
    })
    out = quant_heuristics.heuristics_for_questions(sb, ["q1"])
    assert [h["id"] for h in out["q1"]] == ["h-ok"]


def test_batched_no_cross_question_leakage_and_ordering():
    sb = SBStub({
        "quant_question_heuristics": [
            _link("q1", "h1", relevance="related"),
            _link("q1", "h2", relevance="primary"),
            _link("q2", "h1", relevance="primary"),
        ],
        "quant_heuristics": [_heur("h1", name="Zeta"), _heur("h2", name="Alpha")],
    })
    out = quant_heuristics.heuristics_for_questions(sb, ["q1", "q2"])
    # q1: primary(h2) before related(h1); q2 only has h1 (its own relevance).
    assert [h["id"] for h in out["q1"]] == ["h2", "h1"]
    assert [h["id"] for h in out["q2"]] == ["h1"]
    assert out["q2"][0]["relevance"] == "primary"


def test_batched_empty_input_performs_no_reads():
    sb = SBStub({"quant_question_heuristics": [], "quant_heuristics": []})
    sb.table = lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no query on empty input"))
    assert quant_heuristics.heuristics_for_questions(sb, []) == {}


# ── normalized projection ────────────────────────────────────────────────────

def test_projection_renames_and_strips_governance_fields():
    sb = SBStub({
        "quant_question_heuristics": [_link("q1", "h1", relevance="secondary")],
        "quant_heuristics": [_heur("h1", name="Base-100")],
    })
    out = ss.strategies_for_questions(sb, ["q1"])
    dto = out["q1"][0]
    assert set(dto) == set(ss.ALLOWED_FIELDS)
    assert dto["subject_family"] == "quant"
    assert dto["strategy_type"] == "shortcut"        # renamed from heuristic_type
    assert dto["faster_method"] == "fast way"        # renamed from shortcut_method
    assert dto["key_observation"] is None
    assert dto["relevance"] == "secondary"
    for forbidden in ("applicability_rule", "reviewer_status", "reviewer_notes",
                      "reviewed_by", "created_by", "heuristic_type",
                      "shortcut_method", "is_active", "updated_at"):
        assert forbidden not in dto


def test_projection_every_requested_id_present_and_empty_for_none():
    sb = SBStub({
        "quant_question_heuristics": [_link("q1", "h1")],
        "quant_heuristics": [_heur("h1")],
    })
    out = ss.strategies_for_questions(sb, ["q1", "q-none"])
    assert out["q-none"] == []
    assert len(out["q1"]) == 1


def test_projection_fails_soft_on_source_error(monkeypatch):
    sb = SBStub({"quant_question_heuristics": [], "quant_heuristics": []})
    monkeypatch.setattr(
        ss.quant_heuristics, "heuristics_for_questions",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("boom")))
    out = ss.strategies_for_questions(sb, ["q1"])
    assert out == {"q1": []}          # source error → [], never raises


# ── get_review attachment ────────────────────────────────────────────────────

def _review_sb():
    return SBStub({
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
        "quant_question_heuristics": [_link("q1", "h1")],
        "quant_heuristics": [_heur("h1", name="Base-100")],
    })


def test_get_review_attaches_verified_only_solution_strategies():
    out = mock_engine.get_review(_review_sb(), "u-1", "att-1")
    by_qid = {q["question_id"]: q for q in out["questions"]}
    assert [s["name"] for s in by_qid["q1"]["solution_strategies"]] == ["Base-100"]
    # No governance leak, and unlinked question gets an empty list.
    assert "reviewer_status" not in by_qid["q1"]["solution_strategies"][0]
    assert by_qid["q2"]["solution_strategies"] == []
    # Strategies are a sibling, never merged into the frozen snapshot.
    assert "solution_strategies" not in by_qid["q1"]["question_snapshot"]
