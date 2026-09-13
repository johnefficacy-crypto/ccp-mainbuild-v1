"""MASTERY-GATE-01 — refuse mastery writes from attempts with too little signal.

Shadow-mode evidence from the 23 pre-flip attempts: ``df35b2a8`` answered ONE
question of 75 (correct) and proposed an average of **+14.40 db** against the
±15 cap; ``fade04bf`` answered 1 of 10 and proposed +9.60. Blanks were never
scored as wrong — shadow rows track answered questions only — so the defect is
not the cap and not blank handling: it is that a one-observation sample is
allowed to reach the cap at all.

Two floors, both on answered counts, both REFUSING rather than discounting:

  * attempt floor — fewer than 5 answered questions → the whole delta set is
    dropped, so no live write and no shadow row;
  * topic floor — inside an attempt that clears, a topic backed by fewer than 2
    answered questions contributes no delta; its siblings are untouched.

Both floors are MASTERY-ONLY. Derivation still runs, and the corrections and
error patterns derived from the same analytics are never suppressed: an error
is evidence at n=1, a rate estimate is not.

The attempt itself is never modified: it still persists, still scores, still
appears in history. Stub-only (in-memory SBStub); no live DB.
"""
from __future__ import annotations

import asyncio
from decimal import Decimal

from app.study_os import mastery_writer as mw
from app.study_os.mastery_engine import derive_from_analytics
from tests.persona_questions._stub import SBStub

ATTEMPT = "33333333-3333-3333-3333-333333333333"
USER = "u-gate"
MOCK_TEST_ID = "mt-gate"


def _base_db() -> dict:
    return {
        "mock_attempts": [{"id": ATTEMPT, "user_id": USER}],
        "mock_tests": [
            {
                "id": MOCK_TEST_ID,
                "mock_attempt_id": ATTEMPT,
                "trust_level": "platform_verified",
                "user_id": USER,
                "source_type": "platform_attempt",
            }
        ],
        "mock_attempt_responses": [],
        "mock_attempt_response_classification": [],
        "mock_correction_tasks": [],
        "mock_mastery_shadow": [],
        "user_topic_mastery": [],
        "user_topic_mastery_audit": [],
        "user_topic_error_patterns": [],
    }


def _response(qid: str, topic_id: str, *, selected: str | None, is_correct: bool) -> dict:
    return {
        "attempt_id": ATTEMPT,
        "question_id": qid,
        "selected_option_id": selected,
        "is_correct": is_correct,
        "time_spent_sec": 30,
        "question_snapshot": {
            "topic_id": topic_id,
            "difficulty": "medium",
            "source_type": "authored",
            "expected_time_sec": 60,
        },
    }


def _classification(qid: str, error_type: str) -> dict:
    return {"attempt_id": ATTEMPT, "question_id": qid, "error_type": error_type}


def _seed(sb: SBStub, answered: list[tuple[str, str, bool]], blanks: list[tuple[str, str]]) -> None:
    """``answered`` = (qid, topic_id, is_correct); ``blanks`` = (qid, topic_id)."""
    sb.db["mock_attempt_responses"] = [
        _response(qid, topic, selected="opt-1", is_correct=ok) for qid, topic, ok in answered
    ] + [_response(qid, topic, selected=None, is_correct=False) for qid, topic in blanks]
    # One classification row per response — the readiness gate requires full
    # coverage before mastery runs at all.
    sb.db["mock_attempt_response_classification"] = [
        _classification(qid, "correct" if ok else "concept_gap") for qid, _t, ok in answered
    ] + [_classification(qid, "time_pressure_unattempted") for qid, _t in blanks]


def _run(sb: SBStub, flag: str = "live") -> None:
    asyncio.run(mw.MasteryWriter(sb, flag).process_attempt(ATTEMPT))


def _shadow_topics(sb: SBStub) -> set[str]:
    return {r["topic_id"] for r in sb.db["mock_mastery_shadow"]}


def _audit_topics(sb: SBStub) -> set[str]:
    return {r["topic_id"] for r in sb.db["user_topic_mastery_audit"]}


def setup_function() -> None:
    mw.mastery_gate_metrics.clear()


# ── 1. THE DEFECT: 1 answered, 74 blank ───────────────────────────────────────

def test_single_answered_question_writes_no_mastery(caplog):
    """``df35b2a8``'s shape: one correct answer, 74 untouched → +14.40 db today.

    Written first: this is the case the gate exists for. Zero mastery writes,
    zero shadow rows, and a refusal an operator can find.
    """
    sb = SBStub(_base_db())
    _seed(
        sb,
        answered=[("q-1", "t-a", True)],
        blanks=[(f"q-b{i}", f"t-b{i % 9}") for i in range(74)],
    )
    with caplog.at_level("INFO", logger="career_copilot.study_os.mastery_writer"):
        _run(sb)

    assert sb.db["mock_mastery_shadow"] == []
    assert sb.db["user_topic_mastery_audit"] == []
    assert sb.db["user_topic_mastery"] == []
    # The refusal is observable, and names the attempt, the user and the count.
    assert mw.mastery_gate_metrics["attempt_floor_refused"] == 1
    assert "mastery refused (attempt floor)" in caplog.text
    assert ATTEMPT in caplog.text
    assert USER in caplog.text
    assert "answered=1" in caplog.text
    # The attempt itself is untouched — it still exists exactly as submitted.
    assert sb.db["mock_attempts"] == [{"id": ATTEMPT, "user_id": USER}]


# ── 2. attempt clears, every topic refused ────────────────────────────────────

def test_seven_answered_across_seven_topics_yields_no_deltas():
    """7 answered > the attempt floor of 5, but each topic has exactly 1 answer."""
    sb = SBStub(_base_db())
    _seed(sb, answered=[(f"q-{i}", f"t-{i}", i % 2 == 0) for i in range(7)], blanks=[])
    _run(sb)

    assert sb.db["mock_mastery_shadow"] == []
    assert sb.db["user_topic_mastery_audit"] == []
    assert mw.mastery_gate_metrics["attempt_floor_refused"] == 0
    assert mw.mastery_gate_metrics["topic_floor_refused"] == 7


# ── 3. the one genuine attempt's shape: 9 answered ────────────────────────────

def test_nine_answered_writes_only_topics_with_two_or_more():
    """``4e866434``'s shape (9 questions, mostly correct), spread over 5 topics.

    t-a 3 answers, t-b 2, t-c 2, t-d 1, t-e 1 → exactly the first three write.
    """
    sb = SBStub(_base_db())
    _seed(
        sb,
        answered=[
            ("q-a1", "t-a", True), ("q-a2", "t-a", True), ("q-a3", "t-a", False),
            ("q-b1", "t-b", True), ("q-b2", "t-b", True),
            ("q-c1", "t-c", True), ("q-c2", "t-c", True),
            ("q-d1", "t-d", True),
            ("q-e1", "t-e", True),
        ],
        blanks=[],
    )
    _run(sb)

    assert _shadow_topics(sb) == {"t-a", "t-b", "t-c"}
    assert _audit_topics(sb) == {"t-a", "t-b", "t-c"}
    assert mw.mastery_gate_metrics["topic_floor_refused"] == 2


# ── 4. the gate must not perturb a surviving delta ────────────────────────────

def test_surviving_delta_is_identical_to_the_ungated_value():
    """One topic with 5 answers, one with 1: the first writes, unchanged."""
    sb = SBStub(_base_db())
    _seed(
        sb,
        answered=[(f"q-x{i}", "t-x", i < 3) for i in range(5)] + [("q-y1", "t-y", True)],
        blanks=[],
    )
    # What the engine would produce with no gate at all.
    analytics = mw.MasteryWriter(sb, "shadow")._load_analytics(ATTEMPT)
    ungated = {
        d.topic_id: d for d in derive_from_analytics(analytics).mastery_deltas
    }

    _run(sb)

    assert _shadow_topics(sb) == {"t-x"}
    assert _audit_topics(sb) == {"t-x"}
    row = next(r for r in sb.db["mock_mastery_shadow"] if r["topic_id"] == "t-x")
    expected_db = (
        ungated["t-x"].capped_delta * mw.TRUST_WEIGHT["platform_verified"] * Decimal("100")
    ).quantize(Decimal("0.01"))
    assert row["proposed_delta_db"] == str(expected_db)
    # ...and the refused topic contributed nothing at all.
    assert all(r["topic_id"] != "t-y" for r in sb.db["mock_mastery_shadow"])


# ── 5. exactly at each threshold, and one below ───────────────────────────────

def test_exactly_five_answered_and_exactly_two_per_topic_pass():
    sb = SBStub(_base_db())
    _seed(
        sb,
        answered=[
            ("q-a1", "t-a", True), ("q-a2", "t-a", True),
            ("q-b1", "t-b", True), ("q-b2", "t-b", False),
            ("q-c1", "t-c", True),
        ],
        blanks=[],
    )
    _run(sb)

    # 5 answered == the floor → the attempt clears (floor is "fewer than 5").
    assert mw.mastery_gate_metrics["attempt_floor_refused"] == 0
    # 2 answers == the topic floor → both t-a and t-b write; t-c's single does not.
    assert _shadow_topics(sb) == {"t-a", "t-b"}
    assert _audit_topics(sb) == {"t-a", "t-b"}


def test_four_answered_is_refused_one_below_the_floor():
    sb = SBStub(_base_db())
    _seed(
        sb,
        answered=[("q-a1", "t-a", True), ("q-a2", "t-a", True),
                  ("q-a3", "t-a", True), ("q-a4", "t-a", True)],
        blanks=[],
    )
    _run(sb)

    assert sb.db["mock_mastery_shadow"] == []
    assert sb.db["user_topic_mastery_audit"] == []
    assert mw.mastery_gate_metrics["attempt_floor_refused"] == 1


# ── 6. the gate runs in shadow mode too ───────────────────────────────────────

def test_refused_attempt_writes_no_shadow_row_in_shadow_mode():
    """This is what makes the pre-flip shadow corpus usable as a baseline."""
    sb = SBStub(_base_db())
    _seed(sb, answered=[("q-1", "t-a", True)], blanks=[("q-2", "t-a")])
    _run(sb, flag="shadow")

    assert sb.db["mock_mastery_shadow"] == []
    assert mw.mastery_gate_metrics["attempt_floor_refused"] == 1


def test_topic_floor_also_applies_in_shadow_mode():
    sb = SBStub(_base_db())
    _seed(
        sb,
        answered=[("q-a1", "t-a", True), ("q-a2", "t-a", True), ("q-a3", "t-a", True),
                  ("q-b1", "t-b", True), ("q-b2", "t-b", True), ("q-c1", "t-c", True)],
        blanks=[],
    )
    _run(sb, flag="shadow")

    assert _shadow_topics(sb) == {"t-a", "t-b"}
    # Shadow mode never writes live mastery, gate or no gate.
    assert sb.db["user_topic_mastery_audit"] == []


# ── 7. the floors are mastery-only ────────────────────────────────────────────

def test_refused_attempt_still_writes_corrections_and_error_patterns():
    """An error is evidence at n=1; a rate estimate is not.

    The attempt floor drops the deltas but never the error/correction signals —
    ``error_signal`` is a flat 10.0 in the planner's ``_score_topic``, wider than
    the top-eight score spread, so suppressing those would move the plan further
    than the mastery gate does.
    """
    sb = SBStub(_base_db())
    _seed(sb, answered=[("q-1", "t-a", False), ("q-2", "t-a", False)], blanks=[])
    _run(sb)

    assert mw.mastery_gate_metrics["attempt_floor_refused"] == 1
    assert sb.db["mock_mastery_shadow"] == []
    assert sb.db["user_topic_mastery_audit"] == []
    # ...but the evidence of the two wrong answers survives.
    assert {r["topic_id"] for r in sb.db["user_topic_error_patterns"]} == {"t-a"}
    assert any(c["topic"] == "t-a" for c in sb.db["mock_correction_tasks"])


def test_topic_floor_refusal_also_keeps_its_corrections():
    """Same rule one level down: a single-answer topic still reports its error."""
    sb = SBStub(_base_db())
    _seed(
        sb,
        answered=[("q-a1", "t-a", True), ("q-a2", "t-a", True), ("q-a3", "t-a", True),
                  ("q-a4", "t-a", True), ("q-b1", "t-b", False)],
        blanks=[],
    )
    _run(sb)

    # t-b is refused for mastery...
    assert _shadow_topics(sb) == {"t-a"}
    assert _audit_topics(sb) == {"t-a"}
    assert mw.mastery_gate_metrics["topic_floor_refused"] == 1
    # ...and still reports its single wrong answer as an error pattern.
    assert any(r["topic_id"] == "t-b" for r in sb.db["user_topic_error_patterns"])
