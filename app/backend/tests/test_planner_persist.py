"""Planner persistence — fail-closed contract.

The planner used to wrap every write in a bare ``_safe(...)``: a constraint
violation (e.g. ``event_type`` not in CHECK), a transient network blip, or
a 42703 schema-drift were all returned as ``{generated: True}``. This
suite pins the new contract: ``apply_plan`` must surface a structured
``reason`` whenever any of the five critical writes fails to land.
"""
from __future__ import annotations

from typing import Any

from tests.persona_questions._stub import SBStub
from tests.study_os.test_planner import _seed

from app.study_os.planner import apply_plan


# ── happy path ─────────────────────────────────────────────────────────


def test_apply_succeeds_with_no_reason_field():
    sb = SBStub(_seed())
    out = apply_plan(sb, "u-1")
    assert out["generated"] is True
    assert out["applied"] is True
    assert "reason" not in out
    # every critical row landed
    assert len(sb.db["study_plans"]) == 1
    assert len(sb.db["study_plan_versions"]) == 1
    assert len(sb.db["study_tasks"]) >= 1
    assert len(sb.db["study_adaptation_events"]) == 1


# ── enum fix ───────────────────────────────────────────────────────────


def test_apply_writes_audit_with_manual_regeneration_event_type():
    """The default ``event_type`` must be a value present in the
    ``study_adaptation_events.event_type`` CHECK constraint (migration 033).
    """
    sb = SBStub(_seed())
    out = apply_plan(sb, "u-1")
    assert out["applied"] is True
    events = sb.db["study_adaptation_events"]
    assert len(events) == 1
    assert events[0]["event_type"] == "manual_regeneration"


def test_manual_application_never_appears_in_any_payload():
    """Regression guard. The legacy default leaked into every audit
    insert and was being silently rejected by Postgres; pin that the
    string can never appear in a persisted row again.
    """
    sb = SBStub(_seed())
    apply_plan(sb, "u-1")
    for table in ("study_plans", "study_plan_versions", "study_tasks", "study_adaptation_events"):
        for row in sb.db.get(table, []):
            for value in row.values():
                if isinstance(value, str):
                    assert "manual_application" not in value, (
                        f"Stale event_type leaked into {table}: {row}"
                    )


# ── fail-closed paths ──────────────────────────────────────────────────


def _failing_sb(failing_op: str, base_seed: dict[str, Any] | None = None) -> SBStub:
    """An SBStub that returns an empty-data response for one write op.

    ``failing_op`` is matched against ``"<table>.<operation>"``. Anything
    else passes through to the normal stub behaviour.
    """
    sb = SBStub(base_seed if base_seed is not None else _seed())

    original_table = sb.table

    class _FailingQuery:
        def __init__(self, inner, table_name):
            self._inner = inner
            self._table = table_name
            self._op: str | None = None

        def __getattr__(self, name):
            attr = getattr(self._inner, name)
            if name in {"insert", "update", "upsert", "delete"}:
                # tag the op as the first mutating verb we see on this
                # query chain
                if self._op is None:
                    self._op = name

                def _wrap(*a, **kw):
                    self._inner = attr(*a, **kw)
                    return self

                return _wrap
            if name == "execute":

                def _exec():
                    op_label = f"{self._table}.{self._op or 'select'}"
                    if op_label == failing_op:
                        return _Empty()
                    return attr()

                return _exec

            def _passthrough(*a, **kw):
                self._inner = attr(*a, **kw)
                return self

            return _passthrough

    class _Empty:
        data: list = []

    def _table(name: str):
        return _FailingQuery(original_table(name), name)

    sb.table = _table  # type: ignore[assignment]
    return sb


def test_apply_fail_closed_when_study_plans_insert_returns_empty():
    sb = _failing_sb("study_plans.insert")
    out = apply_plan(sb, "u-1")
    assert out["generated"] is False
    assert out["reason"] == "plan_persist_failed"


def test_apply_fail_closed_when_version_insert_returns_empty():
    sb = _failing_sb("study_plan_versions.insert")
    out = apply_plan(sb, "u-1")
    assert out["generated"] is False
    assert out["reason"] == "version_persist_failed"


def test_apply_fail_closed_when_task_insert_returns_empty():
    sb = _failing_sb("study_tasks.insert")
    out = apply_plan(sb, "u-1")
    assert out["generated"] is False
    assert out["reason"] == "task_persist_failed"


def test_apply_fail_closed_when_adaptation_insert_returns_empty():
    sb = _failing_sb("study_adaptation_events.insert")
    out = apply_plan(sb, "u-1")
    assert out["generated"] is False
    assert out["reason"] == "audit_persist_failed"


def test_apply_tolerates_empty_delete_on_fresh_plan():
    """The today's-task delete legitimately matches zero rows on the very
    first apply — ``allow_empty=True`` keeps that from being a failure.
    """
    sb = SBStub(_seed())
    out = apply_plan(sb, "u-1")
    assert out["generated"] is True
    assert out["applied"] is True
    assert "reason" not in out


# ── title / 23502 regression (the reported bug) ────────────────────────


def test_persist_insert_sets_non_null_title():
    """``study_plans.title`` is ``NOT NULL`` with no default; omitting it
    made Postgres reject the insert with 23502. The insert must populate a
    non-null title (and a non-null description).
    """
    sb = SBStub(_seed())
    apply_plan(sb, "u-1")
    plans = sb.db["study_plans"]
    assert len(plans) == 1
    plan = plans[0]
    assert plan.get("title")  # non-null, non-empty
    assert "SSC CGL" in plan["title"]
    assert plan.get("description")  # non-null safe string


def test_persist_update_preserves_title_on_revision():
    """Re-applying reuses the active plan; the update path must never null
    out the title set on the first insert.
    """
    sb = SBStub(_seed())
    apply_plan(sb, "u-1")
    first_title = sb.db["study_plans"][0]["title"]
    assert first_title
    apply_plan(sb, "u-1")
    assert len(sb.db["study_plans"]) == 1
    assert sb.db["study_plans"][0]["title"] == first_title


class _Raising23502SB(SBStub):
    """Raises a Postgres 23502 NOT NULL violation on ``study_plans.insert``,
    mirroring production when ``title`` was omitted from the payload.
    """

    def table(self, name):  # type: ignore[override]
        q = super().table(name)
        if name == "study_plans":
            original_execute = q.execute

            def _execute():
                if q._pending_insert is not None:
                    raise RuntimeError(
                        '{"code":"23502","message":"null value in column '
                        '\\"title\\" of relation \\"study_plans\\" violates '
                        'not-null constraint"}'
                    )
                return original_execute()

            q.execute = _execute  # type: ignore[assignment]
        return q


def test_apply_surfaces_plan_persist_failed_on_23502():
    sb = _Raising23502SB(_seed())
    out = apply_plan(sb, "u-1")
    assert out["generated"] is False
    assert out["reason"] == "plan_persist_failed"
    # nothing was written — no orphan study_plans row
    assert sb.db.get("study_plans", []) == []


def test_version_failure_rolls_back_created_plan():
    """A failure *after* the plan insert must leave no orphan rows — the
    compensating rollback tears the freshly-created plan back down.
    """
    sb = _failing_sb("study_plan_versions.insert")
    out = apply_plan(sb, "u-1")
    assert out["reason"] == "version_persist_failed"
    assert sb.db.get("study_plans", []) == []
    assert sb.db.get("study_plan_versions", []) == []


def test_apply_route_returns_500_with_reason_on_persist_failure():
    """The ``/apply`` route must surface a persist failure as a non-2xx
    with the structured reason — not a misleading 200.
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api import study_os as study_os_api
    from app.core.auth import get_current_user

    # Unlock the onboarding-calibration gate (PR #778): the /apply route now
    # short-circuits with ``calibration_required`` when a first-plan calibration
    # is still pending. A 'skipped' gate lets the request reach the persist path
    # under test without altering planner I/O.
    seed = _seed()
    seed["user_exam_calibration"] = [
        {"id": "cal-route", "user_id": "u-1", "exam_id": "exam-1", "status": "skipped"}
    ]
    sb = _failing_sb("study_plans.insert", base_seed=seed)
    app = FastAPI()
    app.include_router(study_os_api.router, prefix="/api")
    study_os_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[get_current_user] = lambda: {"id": "u-1", "role": "user"}
    r = TestClient(app).post("/api/study/plan/apply")
    assert r.status_code == 500
    detail = r.json()["detail"]
    assert detail["reason"] == "plan_persist_failed"
    assert detail["generated"] is False
