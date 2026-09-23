"""EXPL-READ-01 — verified PYQ explanations on the mock attempt-review response.

The load-bearing property is the GATE: only ``reviewer_status='verified'`` rows
reach an aspirant, and the read is LIVE, so unverifying one retracts it from
reviews of attempts already taken. These tests fail loudly if either breaks.
"""
from __future__ import annotations

import uuid

import pytest

from app.study_os import mock_engine as svc
from app.study_os import pyq_explanations
from tests.study_os.test_mock_engine import _make_question, _make_template
from tests.persona_questions._stub import SBStub

PYQ_QID = "pyq-question-1"


def _seeded(explanation_rows: list[dict] | None = None, pyq_option_rows: list[dict] | None = None):
    """One template whose FIRST question carries PYQ lineage, so exactly one
    question in the attempt can attract an explanation and the rest act as the
    control group."""
    template, questions = _make_template("expl-mock-1")
    questions[0]["pyq_question_id"] = PYQ_QID
    db = {
        "mock_templates": [template],
        "mock_question_bank": questions,
        "mock_question_options": [o for q in questions for o in q["options"]],
        "mock_attempts": [],
        "mock_attempt_responses": [],
        "mock_tests": [],
        "pyq_question_explanations": explanation_rows or [],
        "pyq_options": pyq_option_rows or [],
        # The selector's active-lineage guard (mock_engine._load_questions_for_template)
        # refuses to start an attempt on a PYQ-derived question with no active
        # projection, so the fixture must carry one for the lineage-bearing question.
        "pyq_mock_question_projections": [
            {"mock_question_id": questions[0]["id"], "sync_status": "active"}
        ],
    }
    return SBStub(db), template, questions


def _explanation(**overrides) -> dict:
    row = {
        "id": str(uuid.uuid4()),
        "question_id": PYQ_QID,
        "explanation_source_type": "platform_original",
        "reviewer_status": "verified",
        "short_explanation": "Repo rate is the policy rate.",
        "explanation_text": "The repo rate is the rate at which the RBI lends.",
        "solution_steps": ["Identify the policy rate.", "Rule out the reverse repo."],
        "option_rationales": {},
        "formula_used": [],
        "common_traps": ["Confusing repo with reverse repo."],
        # Governance / provenance columns that must NEVER reach the learner.
        "reviewed_by": "admin-1",
        "reviewed_at": "2026-09-23T00:00:00+00:00",
        "license_status": "owned",
        "source_url": "https://example.invalid/internal-source",
        "source_hash": "deadbeef",
        "ambiguity_status": "none",
        "metadata": {"internal": "do not leak"},
    }
    row.update(overrides)
    return row


def _review(sb, template_slug="expl-mock-1"):
    start = svc.start_attempt(sb, "user-1", template_slug)
    attempt_id = start["attempt_id"]
    svc.submit_attempt(sb, "user-1", attempt_id)
    return svc.get_review(sb, "user-1", attempt_id), attempt_id


def _pyq_question(review, questions):
    return next(q for q in review["questions"] if q["question_id"] == questions[0]["id"])


# ─── the gate ────────────────────────────────────────────────────────────────

def test_verified_explanation_reaches_the_review_response():
    sb, _t, questions = _seeded([_explanation()])
    review, _ = _review(sb)
    payload = _pyq_question(review, questions)["pyq_explanation"]
    assert payload is not None
    assert payload["short_explanation"] == "Repo rate is the policy rate."
    assert payload["explanation_text"].startswith("The repo rate")


@pytest.mark.parametrize("status", ["pending", "rejected", "needs_correction"])
def test_unverified_explanation_never_reaches_an_aspirant(status):
    """THE gate. All 402 live rows are 'pending' today; if this regresses they
    surface to learners unreviewed."""
    sb, _t, questions = _seeded([_explanation(reviewer_status=status)])
    review, _ = _review(sb)
    assert _pyq_question(review, questions)["pyq_explanation"] is None


def test_gate_holds_when_a_verified_and_an_unverified_row_share_a_question():
    """A verified row must not drag its rejected sibling along."""
    sb, _t, questions = _seeded(
        [
            _explanation(
                explanation_source_type="coaching",
                reviewer_status="rejected",
                short_explanation="REJECTED CONTENT",
            ),
            _explanation(explanation_source_type="official", short_explanation="Verified one."),
        ]
    )
    review, _ = _review(sb)
    payload = _pyq_question(review, questions)["pyq_explanation"]
    assert payload["short_explanation"] == "Verified one."


def test_governance_and_provenance_columns_never_leak():
    sb, _t, questions = _seeded([_explanation()])
    review, _ = _review(sb)
    payload = _pyq_question(review, questions)["pyq_explanation"]
    assert set(payload) == set(pyq_explanations.ALLOWED_FIELDS)
    for leaked in (
        "reviewer_status", "reviewed_by", "reviewed_at", "license_status",
        "source_url", "source_hash", "ambiguity_status", "metadata",
        "explanation_source_type", "question_id",
    ):
        assert leaked not in payload


# ─── live, not frozen ────────────────────────────────────────────────────────

def test_unverifying_after_the_attempt_retracts_it_from_a_later_review():
    """The whole point of reading live rather than snapshotting: a retraction
    must reach attempts that were already taken."""
    sb, _t, questions = _seeded([_explanation()])
    review, attempt_id = _review(sb)
    assert _pyq_question(review, questions)["pyq_explanation"] is not None

    sb.db["pyq_question_explanations"][0]["reviewer_status"] = "needs_correction"

    after = svc.get_review(sb, "user-1", attempt_id)
    assert _pyq_question(after, questions)["pyq_explanation"] is None


def test_verifying_after_the_attempt_reaches_an_attempt_already_taken():
    """The other half: a row verified later benefits past attempts, which the
    snapshot-copy route could never do."""
    sb, _t, questions = _seeded([_explanation(reviewer_status="pending")])
    review, attempt_id = _review(sb)
    assert _pyq_question(review, questions)["pyq_explanation"] is None

    sb.db["pyq_question_explanations"][0]["reviewer_status"] = "verified"

    after = svc.get_review(sb, "user-1", attempt_id)
    assert _pyq_question(after, questions)["pyq_explanation"] is not None


def test_explanation_is_not_written_into_the_frozen_snapshot():
    sb, _t, questions = _seeded([_explanation()])
    review, _ = _review(sb)
    row = _pyq_question(review, questions)
    assert "pyq_explanation" not in row["question_snapshot"]
    for stored in sb.db["mock_attempt_responses"]:
        assert "pyq_explanation" not in (stored.get("question_snapshot") or {})


# ─── existing behaviour is unchanged where there is nothing verified ─────────

def test_questions_without_a_verified_explanation_are_untouched():
    sb, _t, questions = _seeded([_explanation()])
    review, _ = _review(sb)
    others = [q for q in review["questions"] if q["question_id"] != questions[0]["id"]]
    assert len(others) == 4
    for row in others:
        assert row["pyq_explanation"] is None
        # The flat snapshot explanation still reaches review exactly as before.
        assert row["explanation"] == "Explanation text."
        assert row["solution_strategies"] == []


def test_authored_question_without_pyq_lineage_does_not_break_review():
    sb, _t, _questions = _seeded([])
    sb.db["mock_question_bank"][0].pop("pyq_question_id", None)
    review, _ = _review(sb)
    assert len(review["questions"]) == 5
    assert all(q["pyq_explanation"] is None for q in review["questions"])


def test_flat_snapshot_explanation_is_not_suppressed_by_a_verified_one():
    """Deliberate: the structured panel is additive. The two never collide on
    live data today (regulatory bank rows carry an empty `explanation`), so
    suppressing the flat field would be an unrequested behaviour change."""
    sb, _t, questions = _seeded([_explanation()])
    review, _ = _review(sb)
    row = _pyq_question(review, questions)
    assert row["explanation"] == "Explanation text."
    assert row["pyq_explanation"] is not None


# ─── option_rationales: keyed by an id that does not survive projection ──────

def _pyq_options():
    """Four verified PYQ options. The projection numbers options
    `row_number() over (order by option_label, id) - 1`, so B → option_index 1,
    which is the index `_make_option` gives its second option."""
    return [
        {"id": "pyq-opt-d", "question_id": PYQ_QID, "option_label": "D", "reviewer_status": "verified"},
        {"id": "pyq-opt-b", "question_id": PYQ_QID, "option_label": "B", "reviewer_status": "verified"},
        {"id": "pyq-opt-a", "question_id": PYQ_QID, "option_label": "A", "reviewer_status": "verified"},
        {"id": "pyq-opt-c", "question_id": PYQ_QID, "option_label": "C", "reviewer_status": "verified"},
    ]


def test_option_rationales_are_rekeyed_from_pyq_option_id_to_option_index():
    """`option_rationales` is keyed by `pyq_options.id`, but the projection
    (272:547-562) gives each projected option a FRESH uuid, so that key resolves
    to nothing in the frozen snapshot. The backend must do the join."""
    sb, _t, questions = _seeded(
        [_explanation(option_rationales={"pyq-opt-b": "B is right.", "pyq-opt-c": "C confuses repo."})],
        _pyq_options(),
    )
    # Frozen snapshot options are option_index 1..4 (see _make_option).
    review, _ = _review(sb)
    rationales = _pyq_question(review, questions)["pyq_explanation"]["option_rationales"]
    by_index = {r["option_index"]: r["rationale"] for r in rationales}
    assert by_index == {1: "B is right.", 2: "C confuses repo."}
    # Ordered by option_index so the panel prints them in option order.
    assert [r["option_index"] for r in rationales] == [1, 2]
    # The raw pyq option id never reaches the learner payload.
    assert all("pyq_option_id" not in r for r in rationales)


def test_rationale_for_an_option_absent_from_the_frozen_snapshot_is_dropped():
    """If option verification changed after the attempt, a recomputed index can
    fall outside the frozen option list. Better to show nothing for that option
    than to print its rationale against a different one."""
    sb, _t, questions = _seeded(
        [_explanation(option_rationales={"pyq-opt-a": "A is a distractor."})],
        _pyq_options(),
    )
    # 'A' → index 0, which _make_option never produces (its indexes are 1..4).
    review, _ = _review(sb)
    assert _pyq_question(review, questions)["pyq_explanation"]["option_rationales"] == []


def test_unresolvable_rationale_key_is_dropped_rather_than_mispositioned():
    sb, _t, questions = _seeded(
        [_explanation(option_rationales={"pyq-opt-missing": "orphan"})], _pyq_options()
    )
    review, _ = _review(sb)
    assert _pyq_question(review, questions)["pyq_explanation"]["option_rationales"] == []


def test_blank_rationales_are_skipped():
    sb, _t, questions = _seeded(
        [_explanation(option_rationales={"pyq-opt-b": "   ", "pyq-opt-c": "kept"})],
        _pyq_options(),
    )
    review, _ = _review(sb)
    rationales = _pyq_question(review, questions)["pyq_explanation"]["option_rationales"]
    assert [r["rationale"] for r in rationales] == ["kept"]


# ─── structure is preserved, not flattened ───────────────────────────────────

def test_structured_fields_stay_structured():
    sb, _t, questions = _seeded(
        [_explanation(
            solution_steps=["one", "two"],
            formula_used=["r = p * t"],
            common_traps=["trap a", "trap b"],
        )]
    )
    review, _ = _review(sb)
    payload = _pyq_question(review, questions)["pyq_explanation"]
    assert payload["solution_steps"] == ["one", "two"]
    assert payload["formula_used"] == ["r = p * t"]
    assert payload["common_traps"] == ["trap a", "trap b"]


@pytest.mark.parametrize("bad", [None, {}, "not a list", 7])
def test_non_list_jsonb_columns_degrade_to_empty_lists(bad):
    sb, _t, questions = _seeded([_explanation(solution_steps=bad, common_traps=bad)])
    review, _ = _review(sb)
    payload = _pyq_question(review, questions)["pyq_explanation"]
    assert payload["solution_steps"] == []
    assert payload["common_traps"] == []


# ─── several verified rows: deterministic, but NOT a precedence mechanism ────

def test_multiple_verified_rows_pick_the_same_one_every_time():
    """`unique (question_id, explanation_source_type)` permits several rows.
    No precedence is implemented on purpose — only stability is asserted here,
    so this test does not freeze an accidental product ranking."""
    rows = [
        _explanation(id="id-2", explanation_source_type="official", short_explanation="official"),
        _explanation(id="id-1", explanation_source_type="coaching", short_explanation="coaching"),
    ]
    sb, _t, questions = _seeded(rows)
    review, attempt_id = _review(sb)
    first = _pyq_question(review, questions)["pyq_explanation"]["short_explanation"]

    # Same inputs in the opposite row order must still yield the same choice.
    sb.db["pyq_question_explanations"].reverse()
    again = svc.get_review(sb, "user-1", attempt_id)
    assert _pyq_question(again, questions)["pyq_explanation"]["short_explanation"] == first


# ─── fail-soft ───────────────────────────────────────────────────────────────

def test_source_read_failure_does_not_break_the_review(monkeypatch):
    sb, _t, questions = _seeded([_explanation()])

    def _boom(*_a, **_k):
        raise RuntimeError("explanations source down")

    monkeypatch.setattr(pyq_explanations, "_verified_rows", _boom)
    with pytest.raises(RuntimeError):
        pyq_explanations._verified_rows(sb, [PYQ_QID], strict=True)

    # Restore a failing *query* instead, so the module's own _safe handles it.
    monkeypatch.undo()
    original_table = sb.table

    def _table(name):
        if name == "pyq_question_explanations":
            raise RuntimeError("explanations source down")
        return original_table(name)

    monkeypatch.setattr(sb, "table", _table)
    review, _ = _review(sb)
    assert len(review["questions"]) == 5
    assert all(q["pyq_explanation"] is None for q in review["questions"])


def test_strict_mode_propagates_a_read_failure():
    """A future standalone feed must be able to tell an outage apart from
    'nothing verified'."""

    class _Boom:
        def table(self, _name):
            raise RuntimeError("down")

    with pytest.raises(RuntimeError):
        pyq_explanations.explanations_for_pyq_questions(_Boom(), [PYQ_QID], strict=True)


def test_empty_input_short_circuits_without_touching_the_database():
    class _Boom:
        def table(self, _name):  # pragma: no cover - must never be reached
            raise AssertionError("no query should be issued for an empty id list")

    assert pyq_explanations.explanations_for_pyq_questions(_Boom(), []) == {}
    assert pyq_explanations.explanations_for_pyq_questions(_Boom(), [None, ""]) == {}


def test_option_read_is_skipped_when_no_rationales_are_present():
    """Two queries only when the join is actually needed; one otherwise."""
    sb, _t, _questions = _seeded([_explanation(option_rationales={})], _pyq_options())
    seen: list[str] = []
    original_table = sb.table

    def _table(name):
        seen.append(name)
        return original_table(name)

    sb.table = _table  # type: ignore[method-assign]
    pyq_explanations.explanations_for_pyq_questions(sb, [PYQ_QID])
    assert "pyq_options" not in seen
