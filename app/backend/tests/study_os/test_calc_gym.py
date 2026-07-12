"""GQR-Q8 — Calculation Gym deterministic generator + frozen session scoring."""
from __future__ import annotations

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
    res = calc_gym.submit_session(sb, session_id=sid, answers=answers)
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
    first = calc_gym.submit_session(sb, session_id=sid, answers=answers)
    assert first["score_correct"] == 4 and first["idempotent"] is False
    second = calc_gym.submit_session(sb, session_id=sid, answers={})
    assert second["idempotent"] is True
    assert second["score_correct"] == 4  # unchanged, not rescored to 0
