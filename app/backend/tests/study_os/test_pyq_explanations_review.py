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


def _seeded(
    explanation_rows: list[dict] | None = None,
    pyq_option_rows: list[dict] | None = None,
    *,
    projected_option_ids: dict[int, str] | None = None,
):
    """One template whose FIRST question carries PYQ lineage, so exactly one
    question in the attempt can attract an explanation and the rest act as the
    control group.

    ``projected_option_ids`` maps ``option_index`` → ``pyq_options.id`` on the
    lineage-bearing question, standing in for what migration 307 writes onto
    ``mock_question_options.pyq_option_id``. Left unset, the option rows carry no
    source id — a question projected BEFORE 307, which must keep working through
    the positional fallback.
    """
    template, questions = _make_template("expl-mock-1")
    questions[0]["pyq_question_id"] = PYQ_QID
    for option in questions[0]["options"]:
        option["pyq_option_id"] = (projected_option_ids or {}).get(option["option_index"])
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


# ─── EXPL-OPTID-01: joining by identity rather than by position ──────────────
#
# Migration 307 carries pyq_options.id onto mock_question_options, so the frozen
# snapshot can resolve a rationale to its option by IDENTITY. The positional
# derivation stays as the fallback for rows projected before 307 and for rows the
# 307 backfill left NULL. These tests pin which one wins, and prove the identity
# path is not merely equivalent — it is right where position is wrong.


def test_joins_by_pyq_option_id_when_the_snapshot_carries_it():
    sb, _t, questions = _seeded(
        [_explanation(option_rationales={"pyq-opt-b": "B is right.", "pyq-opt-c": "C confuses repo."})],
        _pyq_options(),
        projected_option_ids={1: "pyq-opt-b", 2: "pyq-opt-c", 3: "pyq-opt-a", 4: "pyq-opt-d"},
    )
    review, _ = _review(sb)
    rationales = _pyq_question(review, questions)["pyq_explanation"]["option_rationales"]
    assert {r["option_index"]: r["rationale"] for r in rationales} == {
        1: "B is right.",
        2: "C confuses repo.",
    }


def test_still_joins_positionally_when_the_snapshot_carries_no_source_id():
    """A question projected BEFORE 307, or one the backfill left NULL. The
    fallback must keep working — it is what 394 existing explanations use."""
    sb, _t, questions = _seeded(
        [_explanation(option_rationales={"pyq-opt-b": "B is right.", "pyq-opt-c": "C confuses repo."})],
        _pyq_options(),
        # projected_option_ids omitted → every option row has pyq_option_id None.
    )
    review, _ = _review(sb)
    rationales = _pyq_question(review, questions)["pyq_explanation"]["option_rationales"]
    assert {r["option_index"]: r["rationale"] for r in rationales} == {
        1: "B is right.",
        2: "C confuses repo.",
    }


def test_identity_wins_per_option_on_a_partially_backfilled_question():
    """The backfill populates what it can prove and leaves the rest NULL, so one
    question can carry both. Each option resolves by whichever key it has."""
    sb, _t, questions = _seeded(
        [_explanation(option_rationales={"pyq-opt-b": "by id", "pyq-opt-c": "by position"})],
        _pyq_options(),
        projected_option_ids={1: "pyq-opt-b"},  # only this one was backfilled
    )
    review, _ = _review(sb)
    rationales = _pyq_question(review, questions)["pyq_explanation"]["option_rationales"]
    assert {r["option_index"]: r["rationale"] for r in rationales} == {
        1: "by id",
        2: "by position",
    }


def test_reordered_options_join_correctly_by_id_and_would_join_wrongly_by_position():
    """THE POINT OF THIS PR, constructed deliberately.

    At projection time the question's verified options sorted B, C, A, D by
    (option_label, id), so the snapshot froze option_index 1 → pyq-opt-b and
    2 → pyq-opt-c.

    Afterwards the source options are re-labelled: 'B' becomes 'W' and 'C'
    becomes 'X'. Nothing about the frozen snapshot changes — the learner still
    sees the same four options in the same order — but the LIVE sort is now
    A, D, W, X, so the positional derivation maps pyq-opt-b → 2 and
    pyq-opt-c → 3. Every rationale would land on the wrong option, with nothing
    in the response to indicate it.

    Joining by pyq_option_id is immune: the id did not move.
    """
    reordered = [
        {"id": "pyq-opt-a", "question_id": PYQ_QID, "option_label": "A", "reviewer_status": "verified"},
        {"id": "pyq-opt-d", "question_id": PYQ_QID, "option_label": "D", "reviewer_status": "verified"},
        {"id": "pyq-opt-b", "question_id": PYQ_QID, "option_label": "W", "reviewer_status": "verified"},
        {"id": "pyq-opt-c", "question_id": PYQ_QID, "option_label": "X", "reviewer_status": "verified"},
    ]
    rationales_in = {"pyq-opt-b": "B is right.", "pyq-opt-c": "C confuses repo."}

    # The positional derivation, on its own, now points somewhere else entirely.
    positional = pyq_explanations._option_index_by_pyq_option_id(
        SBStub({"pyq_options": reordered}), [PYQ_QID]
    )
    assert positional["pyq-opt-b"] == 2 and positional["pyq-opt-c"] == 3, (
        "fixture no longer reproduces the drift this test exists to catch"
    )

    # With the source ids on the snapshot, the join ignores that drift.
    sb, _t, questions = _seeded(
        [_explanation(option_rationales=rationales_in)],
        reordered,
        projected_option_ids={1: "pyq-opt-b", 2: "pyq-opt-c", 3: "pyq-opt-a", 4: "pyq-opt-d"},
    )
    review, _ = _review(sb)
    by_index = {
        r["option_index"]: r["rationale"]
        for r in _pyq_question(review, questions)["pyq_explanation"]["option_rationales"]
    }
    assert by_index == {1: "B is right.", 2: "C confuses repo."}

    # And the same corpus WITHOUT the source ids gets it wrong — which is the
    # bug this PR closes, pinned here so the fallback's limit stays visible.
    sb_old, _t2, questions_old = _seeded(
        [_explanation(option_rationales=rationales_in)], reordered
    )
    review_old, _ = _review(sb_old)
    by_index_old = {
        r["option_index"]: r["rationale"]
        for r in _pyq_question(review_old, questions_old)["pyq_explanation"]["option_rationales"]
    }
    assert by_index_old == {2: "B is right.", 3: "C confuses repo."}
    assert by_index_old != by_index


def test_a_source_id_that_is_not_in_the_snapshot_falls_back_rather_than_vanishing():
    """A rationale for an option the snapshot does not carry must not be dropped
    just because identity missed — position still gets its chance."""
    sb, _t, questions = _seeded(
        [_explanation(option_rationales={"pyq-opt-c": "C confuses repo."})],
        _pyq_options(),
        projected_option_ids={1: "pyq-opt-b"},  # pyq-opt-c is not on any option row
    )
    review, _ = _review(sb)
    rationales = _pyq_question(review, questions)["pyq_explanation"]["option_rationales"]
    assert [(r["option_index"], r["rationale"]) for r in rationales] == [(2, "C confuses repo.")]


def test_the_internal_join_key_never_reaches_the_learner_payload():
    sb, _t, questions = _seeded(
        [_explanation(option_rationales={"pyq-opt-b": "B is right."})],
        _pyq_options(),
        projected_option_ids={1: "pyq-opt-b"},
    )
    review, _ = _review(sb)
    payload = _pyq_question(review, questions)["pyq_explanation"]
    assert set(payload) == set(pyq_explanations.ALLOWED_FIELDS)
    for rationale in payload["option_rationales"]:
        assert set(rationale) == {"option_index", "rationale"}


def test_rationales_stay_ordered_by_option_after_an_identity_join():
    """Identity resolution can produce indexes in any order; the panel prints
    them top to bottom, so the response must still be sorted."""
    sb, _t, questions = _seeded(
        [_explanation(option_rationales={
            "pyq-opt-d": "fourth", "pyq-opt-a": "third", "pyq-opt-c": "second", "pyq-opt-b": "first",
        })],
        _pyq_options(),
        projected_option_ids={1: "pyq-opt-b", 2: "pyq-opt-c", 3: "pyq-opt-a", 4: "pyq-opt-d"},
    )
    review, _ = _review(sb)
    rationales = _pyq_question(review, questions)["pyq_explanation"]["option_rationales"]
    assert [r["option_index"] for r in rationales] == [1, 2, 3, 4]
    assert [r["rationale"] for r in rationales] == ["first", "second", "third", "fourth"]


def test_lineage_in_the_attempt_payload_reveals_nothing_about_the_answer():
    """`pyq_option_id` has to live in the frozen snapshot for review to join on
    it, and ``get_attempt`` serves the snapshot's option list verbatim
    (``mock_engine.py:779``), so it is visible during the attempt too. That is
    accepted, not overlooked: it is an opaque id for the SOURCE row and says
    nothing about which option is correct. The property that matters is the one
    pinned here — the attempt payload still carries no answer signal.
    """
    sb, _t, questions = _seeded(
        [_explanation(option_rationales={"pyq-opt-b": "B is right."})],
        _pyq_options(),
        projected_option_ids={1: "pyq-opt-b", 2: "pyq-opt-c", 3: "pyq-opt-a", 4: "pyq-opt-d"},
    )
    start = svc.start_attempt(sb, "user-1", "expl-mock-1")
    attempt = svc.get_attempt(sb, "user-1", start["attempt_id"])
    served = [q for q in attempt["questions"] if q["question_id"] == questions[0]["id"]]
    assert served, "lineage-bearing question was not served"

    for option in served[0]["options"]:
        # No answer signal, before or after 307.
        assert "is_correct" not in option
    assert "correct_option_id" not in served[0]
    # And no explanation reaches an unsubmitted attempt.
    assert "pyq_explanation" not in served[0]
    assert "explanation" not in served[0]
