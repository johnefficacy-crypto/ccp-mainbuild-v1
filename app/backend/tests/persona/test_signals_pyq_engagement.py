"""PYQ v2 PR-10 — persona behavioural aggregates for direct-PYQ engagement.

`collect_user_signals` derives, read-only over the 30d window, how much the
learner practices projected PYQs (mock attempts from a pyq_practice_* blueprint)
and runs trap drills — new behavioural signals that feed the classifier.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.persona.signals import collect_user_signals
from tests.persona_questions._stub import SBStub


def _recent() -> str:
    return (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()


def _old() -> str:
    return (datetime.now(timezone.utc) - timedelta(days=45)).isoformat()


def _db(**tables) -> SBStub:
    base = {"profiles": [{"id": "u-1"}]}
    base.update(tables)
    return SBStub(base)


def test_pyq_practice_and_trap_drill_sessions_counted():
    recent = _recent()
    sb = _db(
        mock_generated_blueprints=[
            {"id": "bp1", "user_id": "u-1", "source": "pyq_practice_topic"},
            {"id": "bp2", "user_id": "u-1", "source": "pyq_practice_paper"},
            {"id": "bpX", "user_id": "u-1", "source": "exam_realistic"},  # not PYQ practice
        ],
        mock_attempts=[
            {"id": "a1", "user_id": "u-1", "generated_blueprint_id": "bp1", "started_at": recent},
            {"id": "a2", "user_id": "u-1", "generated_blueprint_id": "bp2", "started_at": recent},
            {"id": "aX", "user_id": "u-1", "generated_blueprint_id": "bpX", "started_at": recent},  # non-PYQ blueprint
        ],
        user_trap_drill_attempts=[
            {"user_id": "u-1", "drill_seed": "s1", "attempted_at": recent},
            {"user_id": "u-1", "drill_seed": "s1", "attempted_at": recent},  # same session
            {"user_id": "u-1", "drill_seed": "s2", "attempted_at": recent},
        ],
    )
    s = collect_user_signals(sb, "u-1")
    assert s["pyq_practice_sessions_30d"] == 2  # a1,a2 only (aX's blueprint isn't PYQ practice)
    assert s["trap_drill_sessions_30d"] == 2  # s1, s2 distinct drill runs


def test_old_activity_outside_window_not_counted():
    old = _old()
    sb = _db(
        mock_generated_blueprints=[{"id": "bp1", "user_id": "u-1", "source": "pyq_practice_topic"}],
        mock_attempts=[{"id": "a1", "user_id": "u-1", "generated_blueprint_id": "bp1", "started_at": old}],
        user_trap_drill_attempts=[{"user_id": "u-1", "drill_seed": "s1", "attempted_at": old}],
    )
    s = collect_user_signals(sb, "u-1")
    assert s["pyq_practice_sessions_30d"] == 0
    assert s["trap_drill_sessions_30d"] == 0


def test_zero_when_no_pyq_activity():
    s = collect_user_signals(_db(), "u-1")
    assert s["pyq_practice_sessions_30d"] == 0
    assert s["trap_drill_sessions_30d"] == 0


def test_seedless_drill_rows_each_count_as_one_session():
    recent = _recent()
    sb = _db(
        user_trap_drill_attempts=[
            {"user_id": "u-1", "drill_seed": None, "attempted_at": recent},
            {"user_id": "u-1", "drill_seed": None, "attempted_at": recent},
            {"user_id": "u-1", "drill_seed": "s1", "attempted_at": recent},
        ],
    )
    s = collect_user_signals(sb, "u-1")
    assert s["trap_drill_sessions_30d"] == 3  # 2 seedless + 1 distinct seed
