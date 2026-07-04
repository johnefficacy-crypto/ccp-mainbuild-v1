"""PR-3: planner enforcement of the canonical planner/Study-OS exposure authority
(exam_cycles.planner_activation_enabled) for `light` exams — shared with cycle_readiness Step 9."""
from __future__ import annotations

from app.study_os.planner import compute_draft_plan
from tests.persona_questions._stub import SBStub


def _seed(*, mode, exposed):
    return {
        "profiles": [{"id": "u-1", "target_exam": "exam-1"}],
        "exams": [{"id": "exam-1", "slug": "exam-1", "name": "Exam One",
                   "exam_type": "recruitment", "is_active": True, "management_mode": mode}],
        "exam_cycles": [{"id": "c-1", "exam_id": "exam-1", "status": "active",
                         "exam_start": "2026-09-15", "planner_activation_enabled": exposed}],
        "exam_topic_coverage": [
            {"id": "cov-1", "exam_id": "exam-1", "exam_cycle_id": "c-1", "exam_phase_id": "ph1",
             "topic_id": "t1", "exam_priority_score": 80, "is_high_yield": True,
             "confidence_score": 0.8, "reviewer_status": "locked"},
        ],
        "topics": [{"id": "t1", "name": "Percentage", "slug": "percentage",
                    "subject_id": "s1", "is_active": True}],
        "subjects": [{"id": "s1", "name": "Quant"}],
    }


def test_light_not_exposed_refuses_to_plan():
    out = compute_draft_plan(SBStub(_seed(mode="light", exposed=False)), "u-1")
    assert out["generated"] is False
    assert out["reason"] == "planner_activation_disabled"


def test_light_exposed_generates_plan():
    out = compute_draft_plan(SBStub(_seed(mode="light", exposed=True)), "u-1")
    assert out["generated"] is True
    assert out["after_tasks"], "exposed light exam should produce tasks"


def test_core_plans_regardless_of_exposure_flag():
    # core is always planner-eligible; the exposure flag does not gate it.
    out = compute_draft_plan(SBStub(_seed(mode="core", exposed=False)), "u-1")
    assert out["generated"] is True


def test_light_no_resolvable_cycle_is_not_exposed():
    # A light exam whose only cycle is cancelled has no target cycle -> not exposed -> no plan.
    db = _seed(mode="light", exposed=True)
    db["exam_cycles"][0]["status"] = "cancelled"
    out = compute_draft_plan(SBStub(db), "u-1")
    assert out["generated"] is False
    assert out["reason"] == "planner_activation_disabled"


def test_light_exposed_but_closed_cycle_refuses():
    # resolve_exam_target_window excludes only `cancelled`; its fallback can select a `closed`
    # cycle. cycle_readiness marks a non-operational cycle Step 9 not_applicable, so the planner
    # MUST refuse even when the stale flag is set — otherwise readiness<->planner drift returns.
    db = _seed(mode="light", exposed=True)
    db["exam_cycles"][0]["status"] = "closed"
    out = compute_draft_plan(SBStub(db), "u-1")
    assert out["generated"] is False
    assert out["reason"] == "planner_activation_disabled"


def test_light_exposed_but_completed_cycle_refuses():
    db = _seed(mode="light", exposed=True)
    db["exam_cycles"][0]["status"] = "completed"
    out = compute_draft_plan(SBStub(db), "u-1")
    assert out["generated"] is False
    assert out["reason"] == "planner_activation_disabled"


def test_exposed_sibling_cycle_does_not_leak_to_unexposed_target_cycle():
    # Selected-cycle canonicity (D08/D12): Cycle B is exposed AND has its own locked coverage, but
    # Cycle A (the resolved target, `active`) is NOT exposed and has no applicable coverage. The
    # planner must refuse for A — B's exposure/coverage must never generate A's plan.
    db = _seed(mode="light", exposed=False)  # A ("c-1"): active, not exposed
    db["exam_cycles"].append({
        "id": "c-2", "exam_id": "exam-1", "status": "open",
        "exam_start": "2027-09-15", "planner_activation_enabled": True,
    })
    db["exam_topic_coverage"][0]["exam_cycle_id"] = "c-2"  # B-scoped only; not applicable to A
    out = compute_draft_plan(SBStub(db), "u-1")
    # Resolver picks the `active` cycle A (step 1); A is unexposed -> refuse.
    assert out["generated"] is False
    assert out["reason"] == "planner_activation_disabled"
