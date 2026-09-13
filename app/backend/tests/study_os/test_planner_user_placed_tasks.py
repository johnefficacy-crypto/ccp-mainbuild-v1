"""PLAN-PIN-01 — user-placed tasks must survive the nightly regeneration.

``_persist`` clears today's still-``planned`` tasks before re-inserting the
freshly-computed set, and ``regenerate_stale_plans`` runs that path nightly at
03:00. Before migration 289 nothing on ``study_tasks`` could express "a person
placed this": every arrangement a user made was destroyed by the next sweep.

This suite pins the new contract end to end — the defect case first.
"""
from __future__ import annotations

from typing import Any

from tests.persona_questions._stub import SBStub
from tests.study_os.test_planner import _seed

from app.study_os.planner import _today_iso, apply_plan


def _widen_coverage(seed: dict, extra: int) -> None:
    """Add ``extra`` more locked topics so the candidate pool exceeds max_tasks.

    The shared ``_seed`` carries only 4 locked topics. A slot-arithmetic
    assertion needs the pool to be the non-binding constraint, otherwise
    "the planner emitted 5" is indistinguishable from "the planner ran out of
    topics".
    """
    for i in range(extra):
        tid = f"tx{i}"
        seed["topics"].append(
            {"id": tid, "name": f"Extra {i}", "slug": tid, "subject_id": "s1", "is_active": True}
        )
        seed["exam_topic_coverage"].append(
            {
                "id": f"cov-{tid}",
                "exam_id": "exam-1",
                "exam_cycle_id": "cyc-1",
                "exam_phase_id": "ph1",
                "topic_id": tid,
                "exam_priority_score": 40 - i,
                "is_high_yield": False,
                "confidence_score": 0.6,
                "reviewer_status": "locked",
            }
        )


def _seed_with_plan(
    *,
    user_tasks: list[dict[str, Any]] | None = None,
    max_tasks: int = 3,
    extra_topics: int = 0,
) -> SBStub:
    """A seeded stub carrying an ALREADY-ACTIVE plan plus optional user tasks.

    ``_persist`` only reaches its delete step on a plan that already exists, so
    the regeneration case needs the plan row seeded up front rather than created
    by a first apply.
    """
    seed = _seed()
    if extra_topics:
        _widen_coverage(seed, extra_topics)
    seed["study_plans"] = [
        {
            "id": "plan-1",
            "user_id": "u-1",
            "status": "active",
            "title": "SSC CGL Study Plan",
            "current_plan_version_id": None,
        }
    ]
    seed["aspirant_persona_snapshots"] = [
        {
            "user_id": "u-1",
            "computed_at": "2026-05-01T00:00:00+00:00",
            "study_policy": {
                "max_tasks_per_day": max_tasks,
                "preferred_task_size": "small",
            },
        }
    ]
    seed["study_tasks"] = list(user_tasks or [])
    return SBStub(seed)


def _user_task(task_id: str, topic_id: str | None, *, date: str | None = None) -> dict:
    return {
        "id": task_id,
        "user_id": "u-1",
        "plan_id": "plan-1",
        "topic_id": topic_id,
        "title": f"user placed {task_id}",
        "task_type": "concept",
        "status": "planned",
        "source": "user",
        "scheduled_date": date or _today_iso(),
        "planned_minutes": 25,
        "priority_score": 1.0,
    }


def _planner_task(task_id: str, topic_id: str) -> dict:
    return {
        "id": task_id,
        "user_id": "u-1",
        "plan_id": "plan-1",
        "topic_id": topic_id,
        "title": f"planner placed {task_id}",
        "task_type": "concept",
        "status": "planned",
        "source": "planner",
        "scheduled_date": _today_iso(),
        "planned_minutes": 25,
        "priority_score": 1.0,
    }


def _rows(sb: SBStub) -> list[dict[str, Any]]:
    return sb.db["study_tasks"]


# ── 1. the defect case ─────────────────────────────────────────────────


def test_user_placed_task_survives_regeneration_untouched():
    """The reason this PR exists: a regen must not delete the user's task."""
    sb = _seed_with_plan(user_tasks=[_user_task("task-user-1", "t4")])

    out = apply_plan(sb, "u-1")
    assert out["applied"] is True

    survivors = [r for r in _rows(sb) if r["id"] == "task-user-1"]
    assert len(survivors) == 1, "the user's task was deleted by the regeneration"
    assert survivors[0]["source"] == "user"
    assert survivors[0]["scheduled_date"] == _today_iso()
    assert survivors[0]["title"] == "user placed task-user-1"


# ── 2. planner rows are still swept, exactly as before ─────────────────


def test_planner_task_for_today_is_still_deleted_and_replaced():
    sb = _seed_with_plan(user_tasks=[_planner_task("task-planner-1", "t1")])

    apply_plan(sb, "u-1")

    assert not [r for r in _rows(sb) if r["id"] == "task-planner-1"]
    # ...and a fresh generated set replaced it.
    generated = [r for r in _rows(sb) if r.get("source") == "planner"]
    assert generated
    assert all(r["status"] == "planned" for r in generated)


# ── 3. slot arithmetic: the user's tasks occupy slots ──────────────────


def test_user_placed_tasks_consume_generator_slots():
    """max_tasks=8, 3 user-placed → the planner emits 5, the day totals 8."""
    placed = [
        _user_task("u-a", "t1"),
        _user_task("u-b", "t2"),
        _user_task("u-c", "t3"),
    ]
    # 4 seed topics + 8 more = 12 candidates; 3 are user-placed, so the pool
    # is never the binding constraint and the 5 below is the arithmetic.
    sb = _seed_with_plan(user_tasks=placed, max_tasks=8, extra_topics=8)

    apply_plan(sb, "u-1")

    today = _today_iso()
    generated = [
        r
        for r in _rows(sb)
        if r.get("source") == "planner" and r.get("scheduled_date") == today
    ]
    user_rows = [
        r
        for r in _rows(sb)
        if r.get("source") == "user" and r.get("scheduled_date") == today
    ]
    assert len(user_rows) == 3
    assert len(generated) == 5
    assert len(generated) + len(user_rows) == 8


def test_generator_is_unbounded_by_reservations_when_none_are_placed():
    """Control for the case above — no placements means the old arithmetic."""
    sb = _seed_with_plan(max_tasks=8, extra_topics=8)

    apply_plan(sb, "u-1")

    today = _today_iso()
    generated = [
        r
        for r in _rows(sb)
        if r.get("source") == "planner" and r.get("scheduled_date") == today
    ]
    # Nothing reserved → the full ceiling, exactly as before this change.
    assert len(generated) == 8


# ── 4. no duplicate topic ──────────────────────────────────────────────


def test_user_placed_topic_is_not_also_generated():
    """t1 is the seed's top-ranked topic. The user placed it; the planner skips it."""
    sb = _seed_with_plan(user_tasks=[_user_task("u-t1", "t1")], max_tasks=8)

    apply_plan(sb, "u-1")

    today = _today_iso()
    for_t1 = [
        r
        for r in _rows(sb)
        if r.get("topic_id") == "t1" and r.get("scheduled_date") == today
    ]
    assert len(for_t1) == 1, f"topic t1 scheduled twice today: {for_t1}"
    assert for_t1[0]["source"] == "user"


# ── 5. future-dated placements are out of today's blast radius ─────────


def test_user_placed_task_on_a_future_date_is_untouched_and_reserves_nothing():
    future = _user_task("u-future", "t4", date="2099-01-01")
    sb = _seed_with_plan(user_tasks=[future], max_tasks=8)

    apply_plan(sb, "u-1")

    kept = [r for r in _rows(sb) if r["id"] == "u-future"]
    assert len(kept) == 1
    assert kept[0]["scheduled_date"] == "2099-01-01"
    # It is not today's task, so it reserves no slot: all 4 locked topics
    # are still generated, t4 included.
    today = _today_iso()
    generated = [
        r
        for r in _rows(sb)
        if r.get("source") == "planner" and r.get("scheduled_date") == today
    ]
    assert len(generated) == 4
    assert "t4" in {r["topic_id"] for r in generated}


# ── 6. provenance stamping + fail-closed read ──────────────────────────


def test_generated_tasks_are_stamped_planner():
    sb = SBStub(_seed())
    apply_plan(sb, "u-1")
    generated = [r for r in sb.db["study_tasks"] if r.get("task_type") != "english_writing_session"]
    assert generated
    assert all(r.get("source") == "planner" for r in generated)


def test_user_placed_read_failure_fails_closed():
    """A transient read error must refuse, never look like 'nothing placed'."""
    sb = _seed_with_plan(user_tasks=[_user_task("u-a", "t1")])

    original_table = sb.table

    def _table(name: str):
        q = original_table(name)
        if name != "study_tasks":
            return q
        original_eq = q.eq

        def _eq(key, val):
            original_eq(key, val)
            if key == "source" and val == "user":
                original_execute = q.execute

                def _boom():
                    raise RuntimeError("study_tasks read failed")

                q.execute = _boom  # type: ignore[assignment]
                assert original_execute is not None
            return q

        q.eq = _eq  # type: ignore[assignment]
        return q

    sb.table = _table  # type: ignore[assignment]

    out = apply_plan(sb, "u-1")
    assert out["generated"] is False
    assert out["reason"] == "user_task_read_failed"
    # nothing was written, and the user's task is still there
    assert [r for r in sb.db["study_tasks"] if r["id"] == "u-a"]
