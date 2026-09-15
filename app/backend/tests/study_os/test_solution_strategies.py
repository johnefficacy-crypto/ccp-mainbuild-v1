"""GQR-S1 — learner-facing Solution Strategy delivery.

Covers the batched verified-only Quant read (`heuristics_for_questions`), the
normalized governance-stripped projection (`solution_strategies`), and the
`mock_engine.get_review` attachment. Contract:
docs/architecture/solution-strategies-improvement-lab.md.
"""
from __future__ import annotations

from app.study_os import mock_engine, quant_heuristics, solution_strategies as ss
from tests.persona_questions._stub import SBStub


def _heur(
    hid,
    *,
    status="verified",
    active=True,
    name="H",
    htype="shortcut",
    topic_id="t1",
    microtopic_id=None,
    topic_family="quant",
    microtopic_family="quant",
    microtopic_parent=None,
    **extra,
):
    def _subject(family):
        return {
            "slug": "quantitative-aptitude" if family == "quant" else "reasoning",
            "subject_group": "numerical" if family == "quant" else "reasoning",
        }

    row = {
        "id": hid, "topic_id": topic_id, "microtopic_id": microtopic_id,
        "topic": {"subject": _subject(topic_family)} if topic_id else None,
        "microtopic": {
            "parent_topic_id": (
                topic_id if microtopic_parent is None else microtopic_parent
            ),
            "subject": _subject(microtopic_family),
        } if microtopic_id else None,
        "content_type": "quant_heuristic",
        "card_code": f"code-{hid}", "name": name, "card_subtype": htype,
        "applicability_rule": {"op": "secret"}, "formula_latex": r"\frac{a}{b}",
        "standard_method": "long way", "faster_method": "fast way",
        "worked_example": "eg", "common_traps": "trap",
        "reviewer_status": status, "reviewer_notes": "internal note",
        "reviewed_by": "admin-x", "created_by": "author-y", "is_active": active,
        "updated_at": "2026-07-14T00:00:00Z",
    }
    row.update(extra)
    return row


def _link(
    qid,
    hid,
    *,
    status="verified",
    relevance="primary",
    topic="t1",
    micro=None,
):
    return {
        "id": f"lnk-{qid}-{hid}",
        "question_id": qid,
        "card_id": hid,
        "relevance": relevance,
        "reviewer_status": status,
        # SBStub deliberately ignores PostgREST select projections, so fixtures
        # carry the embedded bank-question scope returned by the real link query.
        "question": {"topic_id": topic, "microtopic_id": micro},
    }


# ── batched quant read ───────────────────────────────────────────────────────

def test_batched_read_one_link_one_heuristic_query():
    calls = {"n": 0}
    sb = SBStub({
        "quant_question_heuristics": [_link("q1", "h1"), _link("q2", "h2")],
        "content_cards": [_heur("h1", name="A"), _heur("h2", name="B")],
    })
    orig_table = sb.table

    def _counting_table(name):
        if name in ("quant_question_heuristics", "content_cards"):
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
        "content_cards": [
            _heur("h-ok", status="verified", active=True),
            _heur("h-pending", status="pending", active=True),
            _heur("h-inactive", status="verified", active=False),
            _heur("h-badlink", status="verified", active=True),
        ],
    })
    out = quant_heuristics.heuristics_for_questions(sb, ["q1"])
    assert [h["id"] for h in out["q1"]] == ["h-ok"]


def test_batched_rejects_wrong_topic_or_microtopic_link():
    sb = SBStub({
        "quant_question_heuristics": [
            _link("q-topic-mismatch", "h-topic", topic="reasoning-topic"),
            _link("q-micro-mismatch", "h-micro", topic="t1", micro="other-micro"),
            _link("q-micro-match", "h-micro", topic="t1", micro="m1"),
        ],
        "content_cards": [
            _heur("h-topic", topic_id="t1", microtopic_id=None),
            _heur("h-micro", topic_id="t1", microtopic_id="m1"),
        ],
    })
    out = quant_heuristics.heuristics_for_questions(
        sb,
        ["q-topic-mismatch", "q-micro-mismatch", "q-micro-match"],
    )
    assert out["q-topic-mismatch"] == []
    assert out["q-micro-mismatch"] == []
    assert [h["id"] for h in out["q-micro-match"]] == ["h-micro"]


def test_batched_no_cross_question_leakage_and_ordering():
    sb = SBStub({
        "quant_question_heuristics": [
            _link("q1", "h1", relevance="related"),
            _link("q1", "h2", relevance="primary"),
            _link("q2", "h1", relevance="primary"),
        ],
        "content_cards": [_heur("h1", name="Zeta"), _heur("h2", name="Alpha")],
    })
    out = quant_heuristics.heuristics_for_questions(sb, ["q1", "q2"])
    # q1: primary(h2) before related(h1); q2 only has h1 (its own relevance).
    assert [h["id"] for h in out["q1"]] == ["h2", "h1"]
    assert [h["id"] for h in out["q2"]] == ["h1"]
    assert out["q2"][0]["relevance"] == "primary"


def test_batched_same_name_order_is_stable_by_id():
    sb = SBStub({
        "quant_question_heuristics": [
            _link("q1", "h-z", relevance="primary"),
            _link("q1", "h-a", relevance="primary"),
        ],
        "content_cards": [
            _heur("h-z", name="Same name"),
            _heur("h-a", name="Same name"),
        ],
    })
    out = quant_heuristics.heuristics_for_questions(sb, ["q1"])
    assert [h["id"] for h in out["q1"]] == ["h-a", "h-z"]


def test_batched_authority_does_not_return_governance_fields():
    sb = SBStub({
        "quant_question_heuristics": [_link("q1", "h1")],
        "content_cards": [_heur("h1")],
    })
    raw = quant_heuristics.heuristics_for_questions(sb, ["q1"])["q1"][0]
    for forbidden in (
        "applicability_rule", "reviewer_status", "reviewer_notes", "reviewed_by",
        "created_by", "updated_at", "is_active", "card_code", "topic_id",
        "microtopic_id",
    ):
        assert forbidden not in raw


def test_single_question_helper_delegates_to_batched_contract():
    sb = SBStub({
        "quant_question_heuristics": [_link("q1", "h1")],
        "content_cards": [_heur("h1")],
    })
    assert quant_heuristics.heuristics_for_question(sb, "q1") == (
        quant_heuristics.heuristics_for_questions(sb, ["q1"])["q1"]
    )


def test_batched_empty_input_performs_no_reads():
    sb = SBStub({"quant_question_heuristics": [], "content_cards": []})
    sb.table = lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no query on empty input"))
    assert quant_heuristics.heuristics_for_questions(sb, []) == {}
    assert quant_heuristics.heuristics_for_question(sb, "") == []


# ── normalized projection ────────────────────────────────────────────────────

def test_projection_renames_and_strips_governance_fields():
    sb = SBStub({
        "quant_question_heuristics": [_link("q1", "h1", relevance="secondary")],
        "content_cards": [_heur("h1", name="Base-100")],
    })
    out = ss.strategies_for_questions(sb, ["q1"])
    dto = out["q1"][0]
    assert set(dto) == set(ss.ALLOWED_FIELDS)
    assert dto["subject_family"] == "quant"
    # card_subtype is projected onto the DTO's strategy_type; faster_method now
    # carries the SAME name on the source row (migration 291 normalised the old
    # shortcut_method/faster_method split away), so the projector no longer
    # renames it - it passes it through.
    assert dto["strategy_type"] == "shortcut"        # from card_subtype
    assert dto["faster_method"] == "fast way"
    assert dto["key_observation"] is None
    assert dto["relevance"] == "secondary"
    # Governance and source-only columns must never reach the learner payload.
    # card_subtype is here because the DTO exposes it as strategy_type, never
    # under its source name; applicability_rule is here because a row read from
    # an older snapshot could still carry it even though migration 291 dropped
    # the column.
    for forbidden in ("applicability_rule", "reviewer_status", "reviewer_notes",
                      "reviewed_by", "created_by", "card_subtype",
                      "content_type", "card_code", "is_active", "updated_at"):
        assert forbidden not in dto


def test_projection_every_requested_id_present_and_empty_for_none():
    sb = SBStub({
        "quant_question_heuristics": [_link("q1", "h1")],
        "content_cards": [_heur("h1")],
    })
    out = ss.strategies_for_questions(sb, ["q1", "q-none"])
    assert out["q-none"] == []
    assert len(out["q1"]) == 1


def test_projection_fails_soft_on_source_error(monkeypatch):
    sb = SBStub({"quant_question_heuristics": [], "content_cards": []})
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
             "question_snapshot": {
                 "question_text": "Q1", "question_type": "mcq", "topic_id": "t1"
             },
             "selected_option_id": "o1", "is_correct": True, "time_spent_sec": 5},
            {"id": "r2", "attempt_id": "att-1", "question_id": "q2",
             "question_snapshot": {
                 "question_text": "Q2", "question_type": "mcq", "topic_id": "t2"
             },
             "selected_option_id": "o2", "is_correct": False, "time_spent_sec": 9},
        ],
        "mock_attempt_response_classification": [],
        "quant_question_heuristics": [_link("q1", "h1", topic="t1")],
        "content_cards": [_heur("h1", name="Base-100", topic_id="t1")],
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
