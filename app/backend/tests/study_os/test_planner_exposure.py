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
