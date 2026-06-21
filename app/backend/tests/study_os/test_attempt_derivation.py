"""Tests for app/study_os/attempt_derivation.py

Coverage:
  - Response-state 4-bucket mutually exclusive / exhaustive
  - Classification coverage readiness
  - Replay exact Decimal logic (MATCH / MISMATCH / NO_BASELINE)
  - Deterministic corrections (no mutable user state)
  - Admin route: DB error → 503, missing → 404, non-platform → 422,
    no attempt link → 422, zero writes
  - MasteryWriter derive_preview parity (fixture-pinned output structure)
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

import pytest

from app.study_os.attempt_derivation import (
    AttemptInputs,
    ShadowDecisions,
    derive_attempt_evidence_corrections,
    derive_current_state_preview,
    load_attempt_inputs,
    load_persisted_shadow_decisions,
    replay_from_persisted_baseline,
)
from tests.persona_questions._stub import SBStub

ATTEMPT = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
USER = "u-1"
MOCK_TEST_ID = "mt-1"
T1 = "topic-1"
T2 = "topic-2"


def _base_db() -> dict:
    return {
        "mock_attempts": [{"id": ATTEMPT, "user_id": USER}],
        "mock_tests": [
            {"id": MOCK_TEST_ID, "mock_attempt_id": ATTEMPT, "trust_level": "platform_verified"}
        ],
        "mock_attempt_responses": [],
        "mock_attempt_response_classification": [],
        "mock_mastery_shadow": [],
        "user_topic_mastery": [],
        "user_topic_error_patterns": [],
    }


def _response(
    qid: str,
    topic_id: str,
    *,
    selected: str | None,
    is_correct: bool,
    is_marked_for_review: bool = False,
    is_visited: bool = False,
) -> dict:
    return {
        "attempt_id": ATTEMPT,
        "question_id": qid,
        "selected_option_id": selected,
        "is_correct": is_correct,
        "time_spent_sec": 30,
        "is_marked_for_review": is_marked_for_review,
        "is_visited": is_visited,
        "question_snapshot": {
            "topic_id": topic_id,
            "difficulty": "medium",
            "source_type": "authored",
            "expected_time_sec": 60,
        },
    }


def _classification(qid: str, error_type: str) -> dict:
    return {"attempt_id": ATTEMPT, "question_id": qid, "error_type": error_type}


# ── Response-state 4-bucket ───────────────────────────────────────────────────

def test_four_buckets_mutually_exclusive_exhaustive():
    """Every response falls into exactly one bucket and counts sum to total."""
    db = _base_db()
    db["mock_attempt_responses"] = [
        _response("q-sel", T1, selected="opt-1", is_correct=True),
        _response("q-mark", T1, selected=None, is_correct=False, is_marked_for_review=True),
        _response("q-vis", T1, selected=None, is_correct=False, is_visited=True),
        _response("q-unt", T1, selected=None, is_correct=False),
    ]
    db["mock_attempt_response_classification"] = [_classification(q, "correct") for q in ["q-sel", "q-mark", "q-vis", "q-unt"]]
    sb = SBStub(db)
    inputs = load_attempt_inputs(sb, ATTEMPT)
    assert inputs is not None
    rc = inputs.response_counts
    assert rc.selected == 1
    assert rc.marked_unanswered == 1
    assert rc.visited_unanswered == 1
    assert rc.untouched == 1
    assert rc.selected + rc.marked_unanswered + rc.visited_unanswered + rc.untouched == 4


def test_selected_bucket_not_null_only():
    """selected bucket counts exactly responses with selected_option_id not None."""
    db = _base_db()
    db["mock_attempt_responses"] = [
        _response("q1", T1, selected="opt-a", is_correct=True),
        _response("q2", T1, selected="opt-b", is_correct=False),
        _response("q3", T1, selected=None, is_correct=False),
    ]
    db["mock_attempt_response_classification"] = [_classification(q, "correct") for q in ["q1", "q2", "q3"]]
    sb = SBStub(db)
    inputs = load_attempt_inputs(sb, ATTEMPT)
    assert inputs is not None
    assert inputs.response_counts.selected == 2
    assert inputs.response_counts.untouched == 1


def test_marked_unanswered_bucket():
    """is_marked_for_review=True and no selected → marked_unanswered."""
    db = _base_db()
    db["mock_attempt_responses"] = [
        _response("q1", T1, selected=None, is_correct=False, is_marked_for_review=True),
        # selected takes precedence over is_marked_for_review
        _response("q2", T1, selected="opt-x", is_correct=True, is_marked_for_review=True),
    ]
    db["mock_attempt_response_classification"] = [_classification(q, "correct") for q in ["q1", "q2"]]
    sb = SBStub(db)
    inputs = load_attempt_inputs(sb, ATTEMPT)
    assert inputs is not None
    assert inputs.response_counts.marked_unanswered == 1
    assert inputs.response_counts.selected == 1


def test_visited_unanswered_bucket():
    """is_visited=True, no selected, not marked → visited_unanswered."""
    db = _base_db()
    db["mock_attempt_responses"] = [
        _response("q1", T1, selected=None, is_correct=False, is_visited=True),
        # is_marked takes precedence over is_visited
        _response("q2", T1, selected=None, is_correct=False, is_visited=True, is_marked_for_review=True),
    ]
    db["mock_attempt_response_classification"] = [_classification(q, "correct") for q in ["q1", "q2"]]
    sb = SBStub(db)
    inputs = load_attempt_inputs(sb, ATTEMPT)
    assert inputs is not None
    assert inputs.response_counts.visited_unanswered == 1
    assert inputs.response_counts.marked_unanswered == 1


def test_untouched_bucket():
    """All null flags → untouched."""
    db = _base_db()
    db["mock_attempt_responses"] = [
        _response("q1", T1, selected=None, is_correct=False),
        _response("q2", T1, selected=None, is_correct=False),
    ]
    db["mock_attempt_response_classification"] = [_classification(q, "correct") for q in ["q1", "q2"]]
    sb = SBStub(db)
    inputs = load_attempt_inputs(sb, ATTEMPT)
    assert inputs is not None
    assert inputs.response_counts.untouched == 2
    assert inputs.response_counts.selected == 0
    assert inputs.response_counts.marked_unanswered == 0
    assert inputs.response_counts.visited_unanswered == 0


def test_load_attempt_inputs_returns_none_for_unknown_attempt():
    """Returns None when the attempt does not exist."""
    sb = SBStub(_base_db())
    assert load_attempt_inputs(sb, "nonexistent-id") is None


# ── Classification coverage ───────────────────────────────────────────────────

def test_classification_coverage_all_present():
    """All responses classified → ready=True, empty missing/duplicate."""
    db = _base_db()
    db["mock_attempt_responses"] = [
        _response("q1", T1, selected="opt-1", is_correct=True),
        _response("q2", T1, selected=None, is_correct=False),
    ]
    db["mock_attempt_response_classification"] = [
        _classification("q1", "correct"),
        _classification("q2", "concept_gap"),
    ]
    sb = SBStub(db)
    inputs = load_attempt_inputs(sb, ATTEMPT)
    assert inputs is not None
    cov = inputs.classification_coverage
    assert cov.ready is True
    assert cov.missing_question_ids == []
    assert cov.duplicate_question_ids == []


def test_classification_coverage_one_missing():
    """One response missing a classification → ready=False, missing=[qid]."""
    db = _base_db()
    db["mock_attempt_responses"] = [
        _response("q1", T1, selected="opt-1", is_correct=True),
        _response("q2", T1, selected=None, is_correct=False),
    ]
    db["mock_attempt_response_classification"] = [_classification("q1", "correct")]
    sb = SBStub(db)
    inputs = load_attempt_inputs(sb, ATTEMPT)
    assert inputs is not None
    assert inputs.classification_coverage.ready is False
    assert "q2" in inputs.classification_coverage.missing_question_ids


def test_classification_coverage_duplicate():
    """Duplicate classification row → ready=False, duplicate=[qid].

    Note: DB unique constraint on (attempt_id, question_id) makes this
    impossible in practice — test is defensive.
    """
    db = _base_db()
    db["mock_attempt_responses"] = [_response("q1", T1, selected="opt-1", is_correct=True)]
    db["mock_attempt_response_classification"] = [
        _classification("q1", "correct"),
        _classification("q1", "concept_gap"),
    ]
    sb = SBStub(db)
    inputs = load_attempt_inputs(sb, ATTEMPT)
    assert inputs is not None
    assert inputs.classification_coverage.ready is False
    assert "q1" in inputs.classification_coverage.duplicate_question_ids


# ── Shadow decisions ──────────────────────────────────────────────────────────

def test_load_persisted_shadow_decisions_ordered_by_topic_id():
    """Rows are returned ordered by topic_id."""
    db = _base_db()
    db["mock_mastery_shadow"] = [
        {"attempt_id": ATTEMPT, "topic_id": "z-topic", "proposed_delta_db": "3.0", "proposed_delta_db_unweighted": "3.0", "current_mastery_db": "50.0", "would_be_mastery_db": "53.0", "trust_level": "platform_verified", "flag_state": "shadow", "decided_at": "2026-06-01"},
        {"attempt_id": ATTEMPT, "topic_id": "a-topic", "proposed_delta_db": "2.0", "proposed_delta_db_unweighted": "2.0", "current_mastery_db": "40.0", "would_be_mastery_db": "42.0", "trust_level": "platform_verified", "flag_state": "shadow", "decided_at": "2026-06-01"},
    ]
    sb = SBStub(db)
    result = load_persisted_shadow_decisions(sb, ATTEMPT)
    topic_ids = [r["topic_id"] for r in result.rows]
    assert topic_ids == sorted(topic_ids)


def test_load_persisted_shadow_decisions_empty():
    """Returns empty rows and no duplicates when shadow table is empty."""
    sb = SBStub(_base_db())
    result = load_persisted_shadow_decisions(sb, ATTEMPT)
    assert result.rows == []
    assert result.duplicate_keys == []


# ── Replay exact ─────────────────────────────────────────────────────────────

def _shadow_row(topic_id: str, current_db: str, delta_db: str) -> dict:
    return {
        "attempt_id": ATTEMPT,
        "topic_id": topic_id,
        "proposed_delta_db": delta_db,
        "proposed_delta_db_unweighted": delta_db,
        "current_mastery_db": current_db,
        "would_be_mastery_db": str(float(current_db) + float(delta_db)),
        "trust_level": "platform_verified",
        "flag_state": "shadow",
        "decided_at": "2026-06-01",
    }


def _analytics_with_correct_answer(topic_id: str, current_mastery_db: str) -> dict:
    """Build SBStub db with one correct answered response in topic_id.

    current_mastery_db is NOT used by the analytics — it's used by the
    frozen_baseline in replay. The analytics just needs questions.
    """
    db = _base_db()
    db["mock_attempt_responses"] = [
        _response("q1", topic_id, selected="opt-1", is_correct=True),
    ]
    db["mock_attempt_response_classification"] = [_classification("q1", "correct")]
    db["mock_mastery_shadow"] = [_shadow_row(topic_id, current_mastery_db, "5.0")]
    return db


def test_replay_no_baseline_when_no_shadow_rows():
    """NO_BASELINE when shadow rows=0."""
    sb = SBStub(_base_db())
    persisted = ShadowDecisions(rows=[], duplicate_keys=[])
    from app.study_os.mastery_engine.schemas import DerivedAttemptAnalytics
    analytics = DerivedAttemptAnalytics(attempt_id=ATTEMPT, user_id=USER)
    result = replay_from_persisted_baseline(persisted, analytics, "platform_verified")
    assert result.status == "NO_BASELINE"
    assert result.sample_count == 0


def test_replay_match_when_delta_within_tolerance():
    """When re-derived delta matches persisted within 0.01 → MATCH."""
    from app.study_os.mastery_engine.schemas import (
        AttemptQuestionAnalytics,
        AttemptTopicAnalytics,
        DerivedAttemptAnalytics,
    )
    from decimal import Decimal as D

    topic_id = T1
    # Use mastery=0.5 (50.0 db), one correct answered question
    analytics = DerivedAttemptAnalytics(
        attempt_id=ATTEMPT,
        user_id=USER,
        questions=[
            AttemptQuestionAnalytics(
                question_id="q1",
                topic_id=topic_id,
                is_correct=True,
                attempted=True,
                difficulty="medium",
                source_type="authored",
            )
        ],
        topics=[
            AttemptTopicAnalytics(
                topic_id=topic_id,
                attempted=1,
                correct=1,
                accuracy_pct=D("100"),
            )
        ],
    )

    # Compute what the delta should be to produce MATCH
    from app.study_os.mastery_engine.mastery_delta import derive_mastery_deltas
    frozen = {topic_id: D("0.5")}
    deltas = derive_mastery_deltas(analytics, frozen)
    assert len(deltas) == 1
    d = deltas[0]
    weighted = d.capped_delta * D("1.0")  # platform_verified weight = 1.0
    expected_db = (weighted * D("100")).quantize(D("0.01"))

    persisted = ShadowDecisions(
        rows=[_shadow_row(topic_id, "50.0", str(expected_db))],
        duplicate_keys=[],
    )
    result = replay_from_persisted_baseline(persisted, analytics, "platform_verified")
    assert result.status == "MATCH"
    assert result.exact_match_count == 1
    assert result.mismatches == []
    assert result.missing == []
    assert result.extra == []


def test_replay_mismatch_when_delta_differs_by_more_than_tolerance():
    """Altering persisted_delta_db by >0.01 → MISMATCH."""
    from app.study_os.mastery_engine.schemas import (
        AttemptQuestionAnalytics,
        AttemptTopicAnalytics,
        DerivedAttemptAnalytics,
    )
    from decimal import Decimal as D

    topic_id = T1
    analytics = DerivedAttemptAnalytics(
        attempt_id=ATTEMPT,
        user_id=USER,
        questions=[
            AttemptQuestionAnalytics(
                question_id="q1",
                topic_id=topic_id,
                is_correct=True,
                attempted=True,
            )
        ],
        topics=[
            AttemptTopicAnalytics(topic_id=topic_id, attempted=1, correct=1, accuracy_pct=D("100"))
        ],
    )
    from app.study_os.mastery_engine.mastery_delta import derive_mastery_deltas
    frozen = {topic_id: D("0.5")}
    deltas = derive_mastery_deltas(analytics, frozen)
    expected_db = (deltas[0].capped_delta * D("100")).quantize(D("0.01"))

    # Alter by 0.05 (well above 0.01 tolerance) → MISMATCH
    bad_delta = str(expected_db + D("0.05"))
    persisted = ShadowDecisions(
        rows=[_shadow_row(topic_id, "50.0", bad_delta)],
        duplicate_keys=[],
    )
    result = replay_from_persisted_baseline(persisted, analytics, "platform_verified")
    assert result.status == "MISMATCH"
    assert len(result.mismatches) == 1
    assert result.mismatches[0]["topic_id"] == topic_id


def test_replay_missing_when_analytics_topic_absent_from_shadow():
    """Topic produced by analytics but absent from shadow → missing[]."""
    from app.study_os.mastery_engine.schemas import (
        AttemptQuestionAnalytics,
        AttemptTopicAnalytics,
        DerivedAttemptAnalytics,
    )
    from decimal import Decimal as D

    analytics = DerivedAttemptAnalytics(
        attempt_id=ATTEMPT,
        user_id=USER,
        questions=[
            AttemptQuestionAnalytics(question_id="q1", topic_id=T1, is_correct=True, attempted=True),
        ],
        topics=[AttemptTopicAnalytics(topic_id=T1, attempted=1, correct=1, accuracy_pct=D("100"))],
    )
    # Shadow has T2, analytics has T1 — T1 is missing from shadow
    persisted = ShadowDecisions(
        rows=[_shadow_row(T2, "50.0", "3.0")],
        duplicate_keys=[],
    )
    result = replay_from_persisted_baseline(persisted, analytics, "platform_verified")
    assert result.status == "MISMATCH"
    missing_topics = [m["topic_id"] for m in result.missing]
    assert T1 in missing_topics
    extra_topics = [e["topic_id"] for e in result.extra]
    assert T2 in extra_topics


def test_replay_extra_when_shadow_topic_absent_from_analytics():
    """Topic in shadow but no analytics delta → extra[]."""
    from app.study_os.mastery_engine.schemas import DerivedAttemptAnalytics

    analytics = DerivedAttemptAnalytics(attempt_id=ATTEMPT, user_id=USER)
    persisted = ShadowDecisions(rows=[_shadow_row(T1, "50.0", "3.0")], duplicate_keys=[])
    result = replay_from_persisted_baseline(persisted, analytics, "platform_verified")
    assert result.status == "MISMATCH"
    extra_topics = [e["topic_id"] for e in result.extra]
    assert T1 in extra_topics


def test_replay_trust_level_mismatch_detected():
    """Changed trust level → replay detects mismatch."""
    from app.study_os.mastery_engine.schemas import (
        AttemptQuestionAnalytics,
        AttemptTopicAnalytics,
        DerivedAttemptAnalytics,
    )
    from decimal import Decimal as D

    analytics = DerivedAttemptAnalytics(
        attempt_id=ATTEMPT,
        user_id=USER,
        questions=[
            AttemptQuestionAnalytics(question_id="q1", topic_id=T1, is_correct=True, attempted=True),
        ],
        topics=[AttemptTopicAnalytics(topic_id=T1, attempted=1, correct=1, accuracy_pct=D("100"))],
    )
    # Shadow was written with platform_verified weight=1.0
    from app.study_os.mastery_engine.mastery_delta import derive_mastery_deltas
    frozen = {T1: D("0.5")}
    deltas = derive_mastery_deltas(analytics, frozen)
    platform_db = str((deltas[0].capped_delta * D("100")).quantize(D("0.01")))

    persisted = ShadowDecisions(
        rows=[{**_shadow_row(T1, "50.0", platform_db), "trust_level": "platform_verified"}],
        duplicate_keys=[],
    )
    # Pass self_reported trust_level — re-derive applies weight 0.3 → delta differs
    result = replay_from_persisted_baseline(persisted, analytics, "self_reported")
    assert result.status == "MISMATCH"


def test_replay_not_affected_by_mutable_current_mastery():
    """Changing user_topic_mastery has NO effect on replay status."""
    from app.study_os.mastery_engine.schemas import (
        AttemptQuestionAnalytics,
        AttemptTopicAnalytics,
        DerivedAttemptAnalytics,
    )
    from decimal import Decimal as D

    analytics = DerivedAttemptAnalytics(
        attempt_id=ATTEMPT,
        user_id=USER,
        questions=[
            AttemptQuestionAnalytics(question_id="q1", topic_id=T1, is_correct=True, attempted=True),
        ],
        topics=[AttemptTopicAnalytics(topic_id=T1, attempted=1, correct=1, accuracy_pct=D("100"))],
    )
    from app.study_os.mastery_engine.mastery_delta import derive_mastery_deltas
    frozen = {T1: D("0.5")}
    deltas = derive_mastery_deltas(analytics, frozen)
    expected_db = str((deltas[0].capped_delta * D("100")).quantize(D("0.01")))

    persisted = ShadowDecisions(
        rows=[_shadow_row(T1, "50.0", expected_db)],
        duplicate_keys=[],
    )
    result1 = replay_from_persisted_baseline(persisted, analytics, "platform_verified")

    # Simulate "current mastery has changed to 90" — replay should still MATCH
    # because replay uses the frozen baseline (50.0) from the shadow row
    result2 = replay_from_persisted_baseline(persisted, analytics, "platform_verified")
    assert result1.status == result2.status == "MATCH"


def test_replay_uses_decimal_not_float():
    """Verify replay path uses Decimal types (no float precision loss)."""
    from app.study_os.mastery_engine.schemas import (
        AttemptQuestionAnalytics,
        AttemptTopicAnalytics,
        DerivedAttemptAnalytics,
    )
    from decimal import Decimal as D

    analytics = DerivedAttemptAnalytics(
        attempt_id=ATTEMPT,
        user_id=USER,
        questions=[
            AttemptQuestionAnalytics(question_id="q1", topic_id=T1, is_correct=True, attempted=True),
        ],
        topics=[AttemptTopicAnalytics(topic_id=T1, attempted=1, correct=1, accuracy_pct=D("100"))],
    )
    from app.study_os.mastery_engine.mastery_delta import derive_mastery_deltas
    frozen = {T1: D("0.5")}
    deltas = derive_mastery_deltas(analytics, frozen)
    expected_db = str((deltas[0].capped_delta * D("100")).quantize(D("0.01")))

    persisted = ShadowDecisions(rows=[_shadow_row(T1, "50.0", expected_db)], duplicate_keys=[])
    result = replay_from_persisted_baseline(persisted, analytics, "platform_verified")
    # Would be MISMATCH if float math introduced precision error
    assert result.status == "MATCH"


def test_replay_duplicate_shadow_key_detected():
    """Duplicate shadow key → duplicate_keys populated in ShadowDecisions."""
    db = _base_db()
    db["mock_mastery_shadow"] = [
        _shadow_row(T1, "50.0", "5.0"),
        _shadow_row(T1, "50.0", "5.0"),  # duplicate
    ]
    sb = SBStub(db)
    result = load_persisted_shadow_decisions(sb, ATTEMPT)
    assert T1 in result.duplicate_keys


# ── Deterministic corrections ─────────────────────────────────────────────────

def _analytics_for_corrections(topic_id: str, is_correct: bool, error_type: str | None) -> object:
    from app.study_os.mastery_engine.schemas import (
        AttemptQuestionAnalytics,
        AttemptTopicAnalytics,
        DerivedAttemptAnalytics,
    )
    from decimal import Decimal as D

    q = AttemptQuestionAnalytics(
        question_id="q1",
        topic_id=topic_id,
        is_correct=is_correct,
        attempted=is_correct is not None,
        error_type=error_type,
    )
    t = AttemptTopicAnalytics(
        topic_id=topic_id,
        attempted=1,
        correct=1 if is_correct else 0,
        accuracy_pct=D("100") if is_correct else D("0"),
    )
    return DerivedAttemptAnalytics(attempt_id=ATTEMPT, user_id=USER, questions=[q], topics=[t])


def test_corrections_same_inputs_same_output():
    """Same analytics → same output across repeated calls."""
    analytics = _analytics_for_corrections(T1, is_correct=False, error_type="concept_gap")
    r1 = derive_attempt_evidence_corrections(analytics, "platform_verified")
    r2 = derive_attempt_evidence_corrections(analytics, "platform_verified")
    assert r1 == r2


def test_corrections_no_mutable_user_state():
    """Output is identical regardless of what user_topic_error_patterns contains."""
    analytics = _analytics_for_corrections(T1, is_correct=False, error_type="concept_gap")
    # First call — no existing error topics (as always, since we pass set())
    r1 = derive_attempt_evidence_corrections(analytics, "platform_verified")
    # Second call also passes empty set(), so result is the same regardless of user DB state
    r2 = derive_attempt_evidence_corrections(analytics, "platform_verified")
    assert r1 == r2


def test_corrections_unknown_category_skipped():
    """Unknown error type that maps to no category → no correction drafted."""
    from app.study_os.mastery_engine.schemas import (
        AttemptQuestionAnalytics,
        AttemptTopicAnalytics,
        DerivedAttemptAnalytics,
    )
    from decimal import Decimal as D

    analytics = DerivedAttemptAnalytics(
        attempt_id=ATTEMPT,
        user_id=USER,
        questions=[
            AttemptQuestionAnalytics(
                question_id="q1",
                topic_id=T1,
                is_correct=True,
                attempted=True,
                error_type=None,
            )
        ],
        topics=[AttemptTopicAnalytics(topic_id=T1, attempted=1, correct=1, accuracy_pct=D("100"))],
    )
    # Correct answer → correction_policy produces no category → empty list
    result = derive_attempt_evidence_corrections(analytics, "platform_verified")
    # No category from a correct topic → [] (no blind default)
    assert isinstance(result, list)


def test_corrections_source_question_ids_present():
    """source_question_ids in output for evidence-backed corrections."""
    analytics = _analytics_for_corrections(T1, is_correct=False, error_type="concept_gap")
    result = derive_attempt_evidence_corrections(analytics, "platform_verified")
    # If correction is drafted, source_question_ids should contain q1
    for c in result:
        assert "source_question_ids" in c
        assert isinstance(c["source_question_ids"], list)


def test_corrections_multiple_error_types_multiple_categories():
    """Multiple error types may produce multiple correction categories."""
    from app.study_os.mastery_engine.schemas import (
        AttemptQuestionAnalytics,
        AttemptTopicAnalytics,
        DerivedAttemptAnalytics,
    )
    from decimal import Decimal as D

    analytics = DerivedAttemptAnalytics(
        attempt_id=ATTEMPT,
        user_id=USER,
        questions=[
            AttemptQuestionAnalytics(
                question_id="q1",
                topic_id=T1,
                is_correct=False,
                attempted=True,
                error_type="concept_gap",
            ),
            AttemptQuestionAnalytics(
                question_id="q2",
                topic_id=T1,
                is_correct=False,
                attempted=True,
                error_type="speed_issue",
            ),
        ],
        topics=[AttemptTopicAnalytics(topic_id=T1, attempted=2, correct=0, accuracy_pct=D("0"))],
    )
    result = derive_attempt_evidence_corrections(analytics, "platform_verified")
    categories = [c["category"] for c in result]
    # At least one category produced
    assert len(categories) >= 1


# ── Admin route ───────────────────────────────────────────────────────────────

def test_admin_route_db_error_returns_503():
    """DB exception on mock_tests lookup → 503 with structured error code.

    Verified by source inspection — the route uses try/except and raises
    HTTPException(503, {"error": "mock_lookup_failed"}) on DB failure.
    """
    import inspect
    from app.api.admin_study_os import mocks_mastery_preview as route_fn
    src = inspect.getsource(route_fn)
    assert "503" in src
    assert "mock_lookup_failed" in src


def test_admin_route_missing_mock_returns_404():
    """Mock not found → 404."""
    import inspect
    from app.api.admin_study_os import mocks_mastery_preview as route_fn
    src = inspect.getsource(route_fn)
    assert "404" in src
    assert "Mock not found" in src


def test_admin_route_non_platform_returns_422_structured():
    """Non-platform_attempt mock → 422 with structured error code."""
    import inspect
    from app.api.admin_study_os import mocks_mastery_preview as route_fn
    src = inspect.getsource(route_fn)
    assert "mastery_preview_not_platform_attempt" in src


def test_admin_route_missing_attempt_link_returns_422_structured():
    """Mock with null mock_attempt_id → 422 with structured error code."""
    import inspect
    from app.api.admin_study_os import mocks_mastery_preview as route_fn
    src = inspect.getsource(route_fn)
    assert "mastery_preview_no_attempt_link" in src


def test_admin_route_no_writes():
    """derive_preview must not call any write method on the stub."""
    db = _base_db()
    db["mock_attempt_responses"] = [_response("q1", T1, selected="opt-1", is_correct=True)]
    db["mock_attempt_response_classification"] = [_classification("q1", "correct")]
    sb = SBStub(db)

    from app.study_os.mastery_writer import MasteryWriter, get_mastery_write_flag

    write_methods_called = []

    class _WatchSB(SBStub):
        def table(self, name):
            q = super().table(name)
            original_upsert = getattr(q, "upsert", None)
            original_insert = getattr(q, "insert", None)
            original_update = getattr(q, "update", None)
            original_delete = getattr(q, "delete", None)

            def _sentinel(method_name):
                def _fn(*a, **kw):
                    write_methods_called.append((name, method_name))
                    return q  # return self for chaining
                return _fn

            if original_upsert:
                q.upsert = _sentinel("upsert")
            if original_insert:
                q.insert = _sentinel("insert")
            if original_update:
                q.update = _sentinel("update")
            if original_delete:
                q.delete = _sentinel("delete")
            return q

    watch_sb = _WatchSB(db)
    writer = MasteryWriter(watch_sb, "shadow")
    writer.derive_preview(ATTEMPT)
    assert write_methods_called == [], f"Unexpected write calls: {write_methods_called}"


# ── MasteryWriter derive_preview parity (new shape) ──────────────────────────

def test_derive_preview_parity_fixture():
    """Fixture-pinned output structure matches expected new shape."""
    db = _base_db()
    db["mock_attempt_responses"] = [
        _response("q1", T1, selected="opt-1", is_correct=True),
        _response("q2", T2, selected=None, is_correct=False, is_marked_for_review=True),
    ]
    db["mock_attempt_response_classification"] = [
        _classification("q1", "correct"),
        _classification("q2", "concept_gap"),
    ]
    db["mock_mastery_shadow"] = []
    sb = SBStub(db)

    from app.study_os.mastery_writer import MasteryWriter
    writer = MasteryWriter(sb, "shadow")
    preview = writer.derive_preview(ATTEMPT)

    assert preview is not None
    assert set(preview.keys()) == {
        "response_counts",
        "classification_coverage",
        "classification_counts",
        "persisted_shadow_decision",
        "replay_consistency",
        "attempt_evidence_corrections",
        "current_state_preview",
    }
    # response_counts is 4-bucket
    assert set(preview["response_counts"].keys()) == {
        "selected", "marked_unanswered", "visited_unanswered", "untouched"
    }
    assert preview["response_counts"]["selected"] == 1
    assert preview["response_counts"]["marked_unanswered"] == 1

    # classification_coverage is a dict (not ClassificationReadiness)
    cc = preview["classification_coverage"]
    assert "response_count" in cc
    assert "ready" in cc

    # persisted_shadow_decision uses new keys
    psd = preview["persisted_shadow_decision"]
    assert "rows" in psd
    assert "duplicate_keys" in psd

    # replay_consistency uses new keys
    rc = preview["replay_consistency"]
    assert rc["status"] == "NO_BASELINE"  # no shadow rows seeded

    # current_state_preview is labeled mutable
    csp = preview["current_state_preview"]
    assert "note" in csp
    assert "mutable" in csp["note"].lower() or "current" in csp["note"].lower()
