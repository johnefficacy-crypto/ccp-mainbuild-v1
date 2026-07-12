"""GQR-Q8 — Calculation Gym deterministic generator + frozen session scoring."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.study_os import calc_gym
from tests.persona_questions._stub import SBStub


# ── deterministic generation ──────────────────────────────────────────────────

def test_same_seed_same_items():
    for skill in calc_gym.SKILLS:
        a = calc_gym.generate_items(skill, 12, seed=42)
        b = calc_gym.generate_items(skill, 12, seed=42)
        assert a == b, f"{skill} not reproducible for a fixed seed"
        assert len(a) == 12


def test_different_seed_diverges():
    a = calc_gym.generate_items("tables", 20, seed=1)
    b = calc_gym.generate_items("tables", 20, seed=2)
    assert a != b


def test_expected_answers_are_correct():
    # tables / squares / cubes / roots / patterns have checkable arithmetic.
    for it in calc_gym.generate_items("tables", 30, seed=7):
        assert int(it["expected_answer"]) == it["operands"]["a"] * it["operands"]["b"]
    for it in calc_gym.generate_items("squares", 30, seed=7):
        assert int(it["expected_answer"]) == it["operands"]["n"] ** 2
    for it in calc_gym.generate_items("cubes", 30, seed=7):
        assert int(it["expected_answer"]) == it["operands"]["n"] ** 3
    for it in calc_gym.generate_items("square_roots", 30, seed=7):
        assert int(it["expected_answer"]) ** 2 == it["operands"]["radicand"]
    for it in calc_gym.generate_items("cube_roots", 30, seed=7):
        assert int(it["expected_answer"]) ** 3 == it["operands"]["radicand"]
    for it in calc_gym.generate_items("ratio_simplify", 30, seed=7):
        a, b = (int(x) for x in it["expected_answer"].split(":"))
        from math import gcd
        assert gcd(a, b) == 1  # fully reduced


def test_unknown_skill_raises():
    with pytest.raises(ValueError):
        calc_gym.generate_items("astrophysics", 5, seed=1)


# ── frozen session create + score ─────────────────────────────────────────────

def _db():
    return SBStub({"calc_gym_sessions": [], "calc_gym_session_items": []})


def test_create_session_freezes_items_without_leaking_answers():
    sb = _db()
    out = calc_gym.create_session(
        sb, user_id="u1", skill="squares", question_count=10, duration_sec=180, seed=99,
    )
    assert len(out["items"]) == 10
    # learner-facing items never expose the expected answer
    assert all("expected_answer" not in it for it in out["items"])
    # but the frozen rows persisted DO carry the expected answer
    stored = sb.db["calc_gym_session_items"]
    assert len(stored) == 10
    assert all(r["expected_answer"] for r in stored)
    assert sb.db["calc_gym_sessions"][0]["seed"] == 99


def test_submit_scores_against_frozen_answers():
    sb = _db()
    out = calc_gym.create_session(
        sb, user_id="u1", skill="tables", question_count=6, duration_sec=120, seed=5,
    )
    sid = out["session_id"]
    # Rebuild the expected answers from the same seed and answer all correctly
    # except one wrong.
    expected = calc_gym.generate_items("tables", 6, seed=5)
    answers = {
        it["item_index"]: {"user_answer": it["expected_answer"], "time_spent_sec": 3}
        for it in expected
    }
    answers[0]["user_answer"] = "-999"  # deliberately wrong
    res = calc_gym.submit_session(sb, session_id=sid, user_id="u1", answers=answers)
    assert res["score_total"] == 6
    assert res["score_correct"] == 5
    assert res["total_time_sec"] == 18
    assert sb.db["calc_gym_sessions"][0]["status"] == "submitted"


def test_submit_is_idempotent():
    sb = _db()
    out = calc_gym.create_session(
        sb, user_id="u1", skill="cubes", question_count=4, duration_sec=90, seed=3,
    )
    sid = out["session_id"]
    expected = calc_gym.generate_items("cubes", 4, seed=3)
    answers = {it["item_index"]: {"user_answer": it["expected_answer"], "time_spent_sec": 2} for it in expected}
    first = calc_gym.submit_session(sb, session_id=sid, user_id="u1", answers=answers)
    assert first["score_correct"] == 4 and first["idempotent"] is False
    second = calc_gym.submit_session(sb, session_id=sid, user_id="u1", answers={})
    assert second["idempotent"] is True
    assert second["score_correct"] == 4  # unchanged, not rescored to 0


def test_submit_rejects_late_submission_and_marks_expired():
    sb = _db()
    t0 = datetime(2026, 7, 12, tzinfo=timezone.utc)
    out = calc_gym.create_session(
        sb, user_id="u1", skill="squares", question_count=4, duration_sec=60, seed=1, now=t0,
    )
    sid = out["session_id"]
    late = t0 + timedelta(seconds=120)  # past the 60s deadline
    with pytest.raises(ValueError, match="expired"):
        calc_gym.submit_session(sb, session_id=sid, user_id="u1", answers={}, now=late)
    sess = sb.db["calc_gym_sessions"][0]
    assert sess["status"] == "expired"
    assert sess.get("score_correct") is None  # never scored


def test_submit_rejects_non_in_progress_state():
    sb = _db()
    out = calc_gym.create_session(sb, user_id="u1", skill="squares", question_count=3, duration_sec=90, seed=1)
    sb.db["calc_gym_sessions"][0]["status"] = "expired"
    with pytest.raises(ValueError, match="not in progress"):
        calc_gym.submit_session(sb, session_id=out["session_id"], user_id="u1", answers={})


def test_submit_scoped_to_owner():
    sb = _db()
    out = calc_gym.create_session(sb, user_id="u1", skill="squares", question_count=3, duration_sec=90, seed=1)
    with pytest.raises(LookupError, match="not found"):
        calc_gym.submit_session(sb, session_id=out["session_id"], user_id="attacker", answers={})
    # the session is untouched by the rejected cross-user attempt
    assert sb.db["calc_gym_sessions"][0]["status"] == "in_progress"


def test_create_session_rolls_back_parent_on_child_failure():
    """Atomic cascade: a child-insert failure must leave no orphan session."""
    class _FailItems(SBStub):
        def table(self, name):
            q = super().table(name)
            if name == "calc_gym_session_items":
                def _boom(_payload):
                    raise RuntimeError("forced child insert failure")
                q.insert = _boom
            return q

    sb = _FailItems({"calc_gym_sessions": [], "calc_gym_session_items": []})
    with pytest.raises(RuntimeError, match="forced child insert failure"):
        calc_gym.create_session(sb, user_id="u1", skill="squares", question_count=5, duration_sec=90, seed=1)
    assert sb.db["calc_gym_sessions"] == []   # parent rolled back
    assert sb.db["calc_gym_session_items"] == []
