"""Phase 7 — deterministic Study OS planner."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import study_os as study_os_api
from app.core.auth import get_current_user
from app.study_os.planner import generate_plan
from tests.persona_questions._stub import SBStub


def _seed() -> dict:
    """An SSC CGL slice: 4 locked topics (+1 draft that must be ignored),
    one prerequisite edge, partial mastery, one error pattern, a PYQ chain
    for t1, and a small persona study policy.
    """
    return {
        "profiles": [{"id": "u-1", "target_exam": "ssc-cgl"}],
        "exams": [
            {"id": "exam-1", "slug": "ssc-cgl", "name": "SSC CGL",
             "exam_type": "recruitment", "is_active": True}
        ],
        "exam_cycles": [
            {"id": "cyc-1", "exam_id": "exam-1", "exam_start": "2026-09-15"}
        ],
        "exam_topic_coverage": [
            {"id": "cov-1", "exam_id": "exam-1", "exam_cycle_id": "cyc-1",
             "exam_phase_id": "ph1", "topic_id": "t1", "exam_priority_score": 88,
             "is_high_yield": True, "confidence_score": 0.86, "reviewer_status": "locked"},
            {"id": "cov-2", "exam_id": "exam-1", "exam_cycle_id": "cyc-1",
             "exam_phase_id": "ph1", "topic_id": "t2", "exam_priority_score": 80,
             "is_high_yield": True, "confidence_score": 0.81, "reviewer_status": "locked"},
            {"id": "cov-3", "exam_id": "exam-1", "exam_cycle_id": "cyc-1",
             "exam_phase_id": "ph1", "topic_id": "t3", "exam_priority_score": 60,
             "is_high_yield": False, "confidence_score": 0.7, "reviewer_status": "locked"},
            {"id": "cov-4", "exam_id": "exam-1", "exam_cycle_id": "cyc-1",
             "exam_phase_id": "ph1", "topic_id": "t4", "exam_priority_score": 50,
             "is_high_yield": False, "confidence_score": 0.66, "reviewer_status": "locked"},
            # draft coverage — must never reach the planner.
            {"id": "cov-5", "exam_id": "exam-1", "exam_cycle_id": "cyc-1",
             "exam_phase_id": "ph1", "topic_id": "t5", "exam_priority_score": 99,
             "is_high_yield": True, "confidence_score": 0.4, "reviewer_status": "draft"},
        ],
        "topics": [
            {"id": "t1", "name": "Percentage", "slug": "percentage", "subject_id": "s1", "is_active": True},
            {"id": "t2", "name": "Profit and Loss", "slug": "profit-and-loss", "subject_id": "s1", "is_active": True},
            {"id": "t3", "name": "Time and Work", "slug": "time-and-work", "subject_id": "s1", "is_active": True},
            {"id": "t4", "name": "Vocabulary", "slug": "vocabulary", "subject_id": "s2", "is_active": True},
            {"id": "t5", "name": "Draft Topic", "slug": "draft-topic", "subject_id": "s1", "is_active": True},
        ],
        "subjects": [
            {"id": "s1", "name": "Quantitative Aptitude"},
            {"id": "s2", "name": "English Language"},
        ],
        "topic_prerequisites": [
            {"topic_id": "t2", "prerequisite_topic_id": "t1",
             "relation_type": "requires", "reviewer_status": "locked"},
        ],
        "user_topic_mastery": [
            {"user_id": "u-1", "topic_id": "t1", "exam_id": "exam-1", "mastery_score": 80},
            {"user_id": "u-1", "topic_id": "t2", "exam_id": "exam-1", "mastery_score": 30},
            # t3 has been practised (mastery row) and shows an error pattern —
            # the realistic invariant, since both come from the same mock.
            {"user_id": "u-1", "topic_id": "t3", "exam_id": "exam-1", "mastery_score": 50},
        ],
        "user_topic_error_patterns": [
            {"user_id": "u-1", "topic_id": "t3", "error_type": "concept_gap"},
        ],
        "aspirant_persona_snapshots": [
            {"user_id": "u-1", "computed_at": "2026-05-01T00:00:00+00:00",
             "study_policy": {"max_tasks_per_day": 3, "preferred_task_size": "small"}},
        ],
        "pyq_papers": [{"id": "paper-1", "exam_id": "exam-1", "trust_status": "verified"}],
        "pyq_questions": [
            {"id": "q1", "pyq_paper_id": "paper-1", "reviewer_status": "verified"}
        ],
        "pyq_question_topic_tags": [
            {"question_id": "q1", "topic_id": "t1", "reviewer_status": "verified", "tag_role": "primary"}
        ],
    }


# ─── Guard conditions ─────────────────────────────────────────────────────
def test_no_target_exam_is_reported_not_raised():
    sb = SBStub({"profiles": [{"id": "u-1", "target_exam": None}]})
    out = generate_plan(sb, "u-1")
    assert out == {"generated": False, "reason": "no_target_exam"}


def test_no_locked_coverage_is_reported():
    sb = SBStub({
        "profiles": [{"id": "u-1", "target_exam": "ssc-cgl"}],
        "exams": [{"id": "exam-1", "slug": "ssc-cgl", "name": "SSC CGL",
                   "exam_type": "recruitment", "is_active": True}],
        "exam_topic_coverage": [
            {"id": "c", "exam_id": "exam-1", "topic_id": "t1",
             "exam_priority_score": 90, "reviewer_status": "draft"}
        ],
        "topics": [{"id": "t1", "name": "Percentage", "subject_id": "s1", "is_active": True}],
    })
    out = generate_plan(sb, "u-1")
    assert out["generated"] is False
    assert out["reason"] == "no_locked_coverage"


# ─── Plan generation ──────────────────────────────────────────────────────
def test_generate_plan_persists_plan_version_tasks_and_event():
    sb = SBStub(_seed())
    out = generate_plan(sb, "u-1")
    assert out["generated"] is True
    assert out["task_count"] == 3  # capped by max_tasks_per_day
    assert out["version_number"] == 1

    # one active plan, one version row, one adaptation event
    assert len(sb.db["study_plans"]) == 1
    assert sb.db["study_plans"][0]["exam_id"] == "exam-1"
    assert len(sb.db["study_plan_versions"]) == 1
    assert sb.db["study_plan_versions"][0]["generator_version"] == "planner_v1"
    assert len(sb.db["study_adaptation_events"]) == 1
    assert sb.db["study_adaptation_events"][0]["event_type"] == "manual_regeneration"

    # tasks carry the planner output columns
    tasks = sb.db["study_tasks"]
    assert len(tasks) == 3
    for t in tasks:
        assert t["plan_version_id"] == sb.db["study_plan_versions"][0]["id"]
        assert t["status"] == "planned"
        assert t["planned_minutes"] == 25  # preferred_task_size = small
        assert isinstance(t["priority_score"], (int, float))
        assert "summary" in t["why_this_task"]
    # the draft-coverage topic never appears
    assert all(t["topic_id"] != "t5" for t in tasks)


def test_prerequisite_topic_is_scheduled_before_its_dependent():
    sb = SBStub(_seed())
    out = generate_plan(sb, "u-1")
    order = [t["topic"] for t in out["tasks"]]
    # t2 (Profit and Loss) scores higher than t1 (Percentage) but requires
    # it, so Percentage must come first despite the lower score.
    assert order.index("Percentage") < order.index("Profit and Loss")


def test_task_type_follows_mastery_and_errors():
    sb = SBStub(_seed())
    out = generate_plan(sb, "u-1")
    by_topic = {t["topic"]: t for t in out["tasks"]}
    # mastery 80 -> revision; mastery 30 -> concept_learning;
    # no mastery + an error pattern -> retrieval_practice.
    assert by_topic["Percentage"]["task_type"] == "revision"
    assert by_topic["Profit and Loss"]["task_type"] == "concept_learning"
    assert by_topic["Time and Work"]["task_type"] == "retrieval_practice"


def test_verified_pyq_count_flows_into_why_this_task():
    sb = SBStub(_seed())
    out = generate_plan(sb, "u-1")
    pct = next(t for t in out["tasks"] if t["topic"] == "Percentage")
    # t1 has one verified PYQ tag on a verified question.
    assert pct["why_this_task"]["verified_pyq_count"] == 1


def test_regeneration_is_idempotent_and_versions_increment():
    sb = SBStub(_seed())
    generate_plan(sb, "u-1")
    second = generate_plan(sb, "u-1")
    assert second["version_number"] == 2
    # the active plan is reused, not duplicated
    assert len(sb.db["study_plans"]) == 1
    # today's planned tasks are replaced, not piled up
    assert len(sb.db["study_tasks"]) == 3
    assert len(sb.db["study_plan_versions"]) == 2
    assert len(sb.db["study_adaptation_events"]) == 2


def test_completed_tasks_survive_regeneration():
    sb = SBStub(_seed())
    generate_plan(sb, "u-1")
    # mark one of today's tasks completed, then regenerate
    sb.db["study_tasks"][0]["status"] = "completed"
    generate_plan(sb, "u-1")
    statuses = [t["status"] for t in sb.db["study_tasks"]]
    # the completed task is kept; the planned ones were refreshed
    assert statuses.count("completed") == 1
    assert statuses.count("planned") == 3


# ─── API route ────────────────────────────────────────────────────────────
def _app(sb: SBStub, user_id: str = "u-1"):
    app = FastAPI()
    app.include_router(study_os_api.router, prefix="/api")
    study_os_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[get_current_user] = lambda: {"id": user_id, "role": "user"}
    return app


def test_generate_plan_route_returns_plan():
    seed = _seed()
    # Unlock the onboarding-calibration gate (PR #778): the route now short-
    # circuits with ``calibration_required`` when a first-plan calibration is
    # still pending. A 'skipped' gate satisfies it without altering planner I/O.
    seed["user_exam_calibration"] = [
        {"id": "cal-route", "user_id": "u-1", "exam_id": "exam-1", "status": "skipped"}
    ]
    sb = SBStub(seed)
    client = TestClient(_app(sb))
    r = client.post("/api/study/plan/generate")
    assert r.status_code == 200
    body = r.json()
    assert body["generated"] is True
    assert body["exam"] == "ssc-cgl"
    assert len(body["tasks"]) == 3


# ─── PR3: resolver wiring tests ───────────────────────────────────────────

from datetime import date, timedelta
from unittest.mock import patch


def _seed_with_phases(*, phase_id_a="ph-prelims", phase_id_b="ph-mains",
                      active_phase_start_delta=-5, active_phase_end=None,
                      future_phase_start_delta=30):
    """Seed with two phases: a current active one and a future expected one."""
    today = date.today()
    return {
        "profiles": [{"id": "u-1", "target_exam": "ssc-cgl"}],
        "exams": [{"id": "exam-1", "slug": "ssc-cgl", "name": "SSC CGL",
                   "exam_type": "recruitment", "is_active": True}],
        "exam_cycles": [{"id": "cyc-1", "exam_id": "exam-1",
                         "status": "active",
                         "exam_start": (today + timedelta(days=90)).isoformat(),
                         "reviewer_status": "verified", "cycle_name": "2026", "year": 2026,
                         "created_at": "2026-01-01T00:00:00Z"}],
        "exam_phases": [
            {"id": phase_id_a, "exam_id": "exam-1", "exam_cycle_id": "cyc-1",
             "phase_name": "Prelims", "phase_slug": "prelims", "phase_order": 1,
             "status": "active",
             "phase_start": (today + timedelta(days=active_phase_start_delta)).isoformat(),
             "phase_end": active_phase_end},
            {"id": phase_id_b, "exam_id": "exam-1", "exam_cycle_id": "cyc-1",
             "phase_name": "Mains", "phase_slug": "mains", "phase_order": 2,
             "status": "expected",
             "phase_start": (today + timedelta(days=future_phase_start_delta)).isoformat(),
             "phase_end": None},
        ],
        "exam_topic_coverage": [
            {"id": "cov-1", "exam_id": "exam-1", "exam_cycle_id": "cyc-1",
             "exam_phase_id": phase_id_a, "topic_id": "t1",
             "exam_priority_score": 88, "is_high_yield": True,
             "confidence_score": 0.86, "reviewer_status": "locked"},
            {"id": "cov-2", "exam_id": "exam-1", "exam_cycle_id": "cyc-1",
             "exam_phase_id": phase_id_a, "topic_id": "t2",
             "exam_priority_score": 80, "is_high_yield": True,
             "confidence_score": 0.81, "reviewer_status": "locked"},
            {"id": "cov-3", "exam_id": "exam-1", "exam_cycle_id": "cyc-1",
             "exam_phase_id": phase_id_b, "topic_id": "t3",
             "exam_priority_score": 60, "is_high_yield": False,
             "confidence_score": 0.70, "reviewer_status": "locked"},
        ],
        "topics": [
            {"id": "t1", "name": "Percentage", "slug": "percentage",
             "subject_id": "s1", "is_active": True},
            {"id": "t2", "name": "Profit and Loss", "slug": "profit-and-loss",
             "subject_id": "s1", "is_active": True},
            {"id": "t3", "name": "Time and Work", "slug": "time-and-work",
             "subject_id": "s1", "is_active": True},
        ],
        "subjects": [{"id": "s1", "name": "Quantitative Aptitude"}],
        "topic_prerequisites": [],
        "user_topic_mastery": [],
        "user_topic_error_patterns": [],
        "aspirant_persona_snapshots": [
            {"user_id": "u-1", "computed_at": "2026-05-01T00:00:00+00:00",
             "study_policy": {"max_tasks_per_day": 5, "preferred_task_size": "small"}},
        ],
        "pyq_papers": [],
        "pyq_questions": [],
        "pyq_question_topic_tags": [],
    }


def test_pr3_resolver_phase_wins_over_coverage_majority():
    """Resolver target wins over coverage-majority with genuine divergence.

    Seed: stale Prelims (phase_end 10 days ago, skipped by ladder-2) + future Mains.
    Coverage: 2 rows tagged to Prelims (t1, t2), 1 row to Mains (t3).
    Coverage-majority  → ph-prelims (2 > 1).
    Resolver ladder-3  → ph-mains (next_future_phase).
    Expected: active_phase_id = ph-mains AND all tasks come from Mains coverage (t3).
    """
    today = date.today()
    seed = {
        "profiles": [{"id": "u-1", "target_exam": "ssc-cgl"}],
        "exams": [{"id": "exam-1", "slug": "ssc-cgl", "name": "SSC CGL",
                   "exam_type": "recruitment", "is_active": True}],
        "exam_cycles": [{"id": "cyc-1", "exam_id": "exam-1", "reviewer_status": "verified", "cycle_name": "2026",
                         "status": "active",
                         "exam_start": (today - timedelta(days=5)).isoformat(),
                         "year": 2026, "created_at": "2026-01-01T00:00:00Z"}],
        "exam_phases": [
            {"id": "ph-prelims", "exam_id": "exam-1", "exam_cycle_id": "cyc-1",
             "phase_name": "Prelims", "phase_slug": "prelims", "phase_order": 1,
             "status": "active",
             "phase_start": (today - timedelta(days=60)).isoformat(),
             "phase_end": (today - timedelta(days=10)).isoformat()},  # stale
            {"id": "ph-mains", "exam_id": "exam-1", "exam_cycle_id": "cyc-1",
             "phase_name": "Mains", "phase_slug": "mains", "phase_order": 2,
             "status": "expected",
             "phase_start": (today + timedelta(days=30)).isoformat(),
             "phase_end": None},
        ],
        # 2 Prelims rows → coverage-majority = ph-prelims
        # 1 Mains row  → resolver target = ph-mains (phase-specific filter wins)
        "exam_topic_coverage": [
            {"id": "cov-1", "exam_id": "exam-1", "exam_cycle_id": "cyc-1",
             "exam_phase_id": "ph-prelims", "topic_id": "t1",
             "exam_priority_score": 88, "is_high_yield": True,
             "confidence_score": 0.86, "reviewer_status": "locked"},
            {"id": "cov-2", "exam_id": "exam-1", "exam_cycle_id": "cyc-1",
             "exam_phase_id": "ph-prelims", "topic_id": "t2",
             "exam_priority_score": 80, "is_high_yield": True,
             "confidence_score": 0.81, "reviewer_status": "locked"},
            {"id": "cov-3", "exam_id": "exam-1", "exam_cycle_id": "cyc-1",
             "exam_phase_id": "ph-mains", "topic_id": "t3",
             "exam_priority_score": 70, "is_high_yield": True,
             "confidence_score": 0.75, "reviewer_status": "locked"},
        ],
        "topics": [
            {"id": "t1", "name": "Percentage", "slug": "percentage",
             "subject_id": "s1", "is_active": True},
            {"id": "t2", "name": "Profit and Loss", "slug": "profit-and-loss",
             "subject_id": "s1", "is_active": True},
            {"id": "t3", "name": "Time and Work", "slug": "time-and-work",
             "subject_id": "s1", "is_active": True},
        ],
        "subjects": [{"id": "s1", "name": "Quantitative Aptitude"}],
        "topic_prerequisites": [],
        "user_topic_mastery": [],
        "user_topic_error_patterns": [],
        "aspirant_persona_snapshots": [
            {"user_id": "u-1", "computed_at": "2026-05-01T00:00:00+00:00",
             "study_policy": {"max_tasks_per_day": 5, "preferred_task_size": "small"}},
        ],
        "pyq_papers": [], "pyq_questions": [], "pyq_question_topic_tags": [],
    }
    sb = SBStub(seed)
    out = generate_plan(sb, "u-1")
    assert out["generated"] is True
    plan = sb.db["study_plans"][0]
    # Resolver wins: active_phase_id = Mains, not the coverage-majority (Prelims)
    assert plan["active_phase_id"] == "ph-mains"
    assert plan["active_phase_id"] != "ph-prelims"
    # Phase-specific coverage filter: only Mains topic (t3) in tasks
    assert all(t["topic_id"] == "t3" for t in sb.db["study_tasks"])


def test_pr3_resolver_none_phase_falls_back_to_coverage_majority():
    """When resolver has no target_phase_id (cycle_exam_start path), coverage-majority is used."""
    today = date.today()
    # Seed with no phases so resolver returns cycle_exam_start (no target_phase_id)
    seed = {
        "profiles": [{"id": "u-1", "target_exam": "ssc-cgl"}],
        "exams": [{"id": "exam-1", "slug": "ssc-cgl", "name": "SSC CGL",
                   "exam_type": "recruitment", "is_active": True}],
        "exam_cycles": [{"id": "cyc-1", "exam_id": "exam-1",
                         "status": "active",
                         "exam_start": (today + timedelta(days=60)).isoformat(),
                         "reviewer_status": "verified", "cycle_name": "2026", "year": 2026,
                         "created_at": "2026-01-01T00:00:00Z"}],
        "exam_phases": [],
        "exam_topic_coverage": [
            {"id": "cov-1", "exam_id": "exam-1", "exam_cycle_id": "cyc-1",
             "exam_phase_id": "ph-majority", "topic_id": "t1",
             "exam_priority_score": 88, "is_high_yield": True,
             "confidence_score": 0.86, "reviewer_status": "locked"},
            {"id": "cov-2", "exam_id": "exam-1", "exam_cycle_id": "cyc-1",
             "exam_phase_id": "ph-majority", "topic_id": "t2",
             "exam_priority_score": 80, "is_high_yield": True,
             "confidence_score": 0.81, "reviewer_status": "locked"},
        ],
        "topics": [
            {"id": "t1", "name": "Percentage", "slug": "percentage",
             "subject_id": "s1", "is_active": True},
            {"id": "t2", "name": "Profit and Loss", "slug": "profit-and-loss",
             "subject_id": "s1", "is_active": True},
        ],
        "subjects": [{"id": "s1", "name": "Quantitative Aptitude"}],
        "topic_prerequisites": [],
        "user_topic_mastery": [],
        "user_topic_error_patterns": [],
        "aspirant_persona_snapshots": [
            {"user_id": "u-1", "computed_at": "2026-05-01T00:00:00+00:00",
             "study_policy": {"max_tasks_per_day": 5, "preferred_task_size": "small"}},
        ],
        "pyq_papers": [], "pyq_questions": [], "pyq_question_topic_tags": [],
    }
    sb = SBStub(seed)
    out = generate_plan(sb, "u-1")
    assert out["generated"] is True
    # Resolver returns cycle_exam_start, target_phase_id=None → fallback to coverage-majority
    plan = sb.db["study_plans"][0]
    assert plan["active_phase_id"] == "ph-majority"
    # days_remaining = countdown to exam_start (numeric, not None)
    gen_ctx = sb.db["study_plans"][0]["generation_context"]
    assert isinstance(gen_ctx["days_remaining"], int)
    assert gen_ctx["days_remaining"] > 0


def test_pr3_open_ended_current_phase_days_remaining_none_no_crash():
    """Open-ended current phase: days_remaining is None; planner must not crash or coerce to 0."""
    today = date.today()
    seed = _seed_with_phases(
        phase_id_a="ph-prelims",
        phase_id_b="ph-mains",
        active_phase_start_delta=-5,
        active_phase_end=None,  # open-ended → resolver returns days_remaining=None
        future_phase_start_delta=30,
    )
    # Remove the future mains phase so resolver picks current_phase (no phase_end)
    seed["exam_phases"] = [seed["exam_phases"][0]]
    sb = SBStub(seed)
    out = generate_plan(sb, "u-1")
    assert out["generated"] is True
    gen_ctx = sb.db["study_plans"][0]["generation_context"]
    assert gen_ctx["days_remaining"] is None  # not coerced to 0


def test_pr3_active_phase_id_create_path_write_failure_surfaces(caplog):
    """INSERT failure propagates through safe_required → fail-closed with observable log.

    No existing plan → _persist takes the insert branch.  A SBStub subclass
    raises inside execute() so safe_required naturally logs the failure and
    returns None.  generate_plan must return generated=False, reason=plan_persist_failed,
    and the op tag must appear in the WARNING log — not silently swallowed.
    """
    import logging
    from tests.persona_questions._stub import SBStub as _SBStub, _Query

    class _FailInsertQuery(_Query):
        def execute(self):
            if self._pending_insert is not None:
                raise RuntimeError("stub: injected insert failure")
            return super().execute()

    class _FailInsertSBStub(_SBStub):
        def table(self, name):
            q = super().table(name)
            if name == "study_plans":
                proxy = _FailInsertQuery(name, self.db)
                return proxy
            return q

    seed = _seed_with_phases(active_phase_start_delta=-5, active_phase_end=None)
    seed["exam_phases"] = [seed["exam_phases"][0]]

    sb = _FailInsertSBStub(seed)
    with caplog.at_level(logging.WARNING):
        out = generate_plan(sb, "u-1")

    assert out["generated"] is False
    assert out["reason"] == "plan_persist_failed"
    assert "study_plans.insert" in caplog.text


def test_pr3_active_phase_id_update_path_write_failure_surfaces(caplog):
    """UPDATE failure propagates through safe_required → fail-closed with observable log.

    Pre-existing active plan → _persist takes the update branch.  A SBStub
    subclass raises inside execute() on update so safe_required naturally logs
    the failure and returns None.  generate_plan must return generated=False,
    reason=plan_persist_failed, and the op tag must appear in the WARNING log.
    """
    import logging
    from tests.persona_questions._stub import SBStub as _SBStub, _Query

    class _FailUpdateQuery(_Query):
        def execute(self):
            if self._pending_update is not None and self._pending_update != "__delete__":
                raise RuntimeError("stub: injected update failure")
            return super().execute()

    class _FailUpdateSBStub(_SBStub):
        def __init__(self, db, *, enabled=False):
            super().__init__(db)
            self._fail_enabled = enabled

        def table(self, name):
            q = super().table(name)
            if name == "study_plans" and self._fail_enabled:
                proxy = _FailUpdateQuery(name, self.db)
                return proxy
            return q

    seed = _seed_with_phases(active_phase_start_delta=-5, active_phase_end=None)
    seed["exam_phases"] = [seed["exam_phases"][0]]

    # First generate with normal stub to create an existing plan
    normal_sb = SBStub(seed)
    first = generate_plan(normal_sb, "u-1")
    assert first["generated"] is True
    assert len(normal_sb.db["study_plans"]) == 1

    # Second generate with failing stub (update path); failure must surface
    sb = _FailUpdateSBStub(normal_sb.db, enabled=True)
    with caplog.at_level(logging.WARNING):
        out = generate_plan(sb, "u-1")

    assert out["generated"] is False
    assert out["reason"] == "plan_persist_failed"
    assert "study_plans.update_active_version" in caplog.text


def test_pr3_planner_does_not_re_select_cycle_independently():
    """Planner uses resolver's cycle; _cached_next_cycle is not called for phase/days selection."""
    import app.study_os.planner as planner_mod

    seed = _seed_with_phases(active_phase_start_delta=-5, active_phase_end=None)
    seed["exam_phases"] = [seed["exam_phases"][0]]
    sb = SBStub(seed)

    cache_calls = []
    real_cached = planner_mod._cached_next_cycle

    def spy_cached(supabase, exam_id, today_str):
        cache_calls.append(("_cached_next_cycle", exam_id))
        return real_cached(supabase, exam_id, today_str)

    with patch.object(planner_mod, "_cached_next_cycle", spy_cached):
        out = generate_plan(sb, "u-1")

    assert out["generated"] is True
    # _cached_next_cycle must NOT be called (the old _days_remaining path is gone)
    assert not any(name == "_cached_next_cycle" for name, _ in cache_calls), (
        f"_cached_next_cycle was called {len(cache_calls)} time(s) — planner is still "
        "re-selecting cycle independently of the resolver"
    )


# ─── J2-A′ gate §G: locked-only prerequisite edges ────────────────────────
def test_load_prerequisites_consumes_only_locked_edges():
    """_load_prerequisites must load edges with reviewer_status='locked' and
    ignore every other lifecycle state (draft/pending_review/reviewed/rejected).
    """
    from app.study_os.planner import _load_prerequisites

    sb = SBStub({
        "topic_prerequisites": [
            # locked → must be loaded
            {"topic_id": "t2", "prerequisite_topic_id": "t1",
             "relation_type": "requires", "reviewer_status": "locked"},
            # non-locked → must all be ignored
            {"topic_id": "t3", "prerequisite_topic_id": "t1",
             "relation_type": "requires", "reviewer_status": "draft"},
            {"topic_id": "t3", "prerequisite_topic_id": "t2",
             "relation_type": "requires", "reviewer_status": "pending_review"},
            {"topic_id": "t4", "prerequisite_topic_id": "t1",
             "relation_type": "requires", "reviewer_status": "reviewed"},
            {"topic_id": "t4", "prerequisite_topic_id": "t2",
             "relation_type": "requires", "reviewer_status": "rejected"},
        ],
    })

    prereqs = _load_prerequisites(sb, ["t1", "t2", "t3", "t4"])

    # Only the locked edge survives.
    assert prereqs == {"t2": {"t1"}}
    # Non-locked edges leave no trace.
    assert "t3" not in prereqs
    assert "t4" not in prereqs


# ─── PYQ v2 PR-9: typed PYQ-practice launch stamp ─────────────────────────
def test_pyq_practice_launch_stamped_on_practice_and_revision_tasks():
    """retrieval_practice and revision tasks on a real topic+exam carry the
    typed PYQ-practice launch stamp; concept_learning tasks do not."""
    sb = SBStub(_seed())
    out = generate_plan(sb, "u-1")
    assert out["generated"] is True

    tasks_by_topic = {t["topic_id"]: t for t in sb.db["study_tasks"]}
    exam_id = "exam-1"

    # t1: mastery 80 → revision
    revision = tasks_by_topic["t1"]
    assert revision["task_type"] == "revision"
    assert revision["launch_type"] == "pyq_practice"
    assert revision["launch_entity_id"] == "t1"
    assert revision["launch_context"] == {
        "mode": "topic", "target_id": "t1", "exam_id": exam_id,
    }
    assert revision["why_this_task"]["launch_target"] == "pyq_practice"

    # t3: mastery 50 + error pattern → retrieval_practice
    practice = tasks_by_topic["t3"]
    assert practice["task_type"] == "retrieval_practice"
    assert practice["launch_type"] == "pyq_practice"
    assert practice["launch_entity_id"] == "t3"
    assert practice["launch_context"] == {
        "mode": "topic", "target_id": "t3", "exam_id": exam_id,
    }
    assert practice["why_this_task"]["launch_target"] == "pyq_practice"

    # t2: mastery 30 → concept_learning → NO launch stamp
    concept = tasks_by_topic["t2"]
    assert concept["task_type"] == "concept_learning"
    assert concept.get("launch_type") is None
    assert concept.get("launch_entity_id") is None
    assert concept.get("launch_context") is None
    assert "launch_target" not in concept["why_this_task"]


def test_pyq_practice_launch_columns_persist_on_study_tasks():
    """The launch columns actually persist onto the study_tasks rows."""
    sb = SBStub(_seed())
    out = generate_plan(sb, "u-1")
    assert out["generated"] is True

    stamped = [t for t in sb.db["study_tasks"] if t.get("launch_type")]
    # At least the revision (t1) and retrieval_practice (t3) tasks are stamped.
    assert stamped, "no study_tasks row carried a launch stamp"
    for t in stamped:
        assert t["launch_type"] == "pyq_practice"
        assert t["launch_entity_id"] == t["topic_id"]
        assert t["launch_context"]["mode"] == "topic"
        assert t["launch_context"]["target_id"] == t["topic_id"]
        assert t["launch_context"]["exam_id"] == "exam-1"
