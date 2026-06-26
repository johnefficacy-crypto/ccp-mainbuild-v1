"""P-slice-2b O-slice-2: self-assessment priors wired into the planner."""
from __future__ import annotations

import pytest

from app.study_os.planner import _load_topic_priors, generate_plan
from tests.persona_questions._stub import SBStub


def _base_seed() -> dict:
    """Minimal seed: 2 locked-coverage topics in the same subject, no priors by default."""
    return {
        "profiles": [{"id": "u-1", "target_exam": "ssc-cgl"}],
        "exams": [
            {
                "id": "exam-1",
                "slug": "ssc-cgl",
                "name": "SSC CGL",
                "exam_type": "recruitment",
                "is_active": True,
            },
        ],
        "exam_cycles": [
            {"id": "cyc-1", "exam_id": "exam-1", "exam_start": "2026-09-15"},
        ],
        "exam_topic_coverage": [
            {
                "id": "cov-1",
                "exam_id": "exam-1",
                "exam_cycle_id": "cyc-1",
                "exam_phase_id": None,
                "topic_id": "t1",
                "exam_priority_score": 80,
                "is_high_yield": True,
                "confidence_score": 0.85,
                "reviewer_status": "locked",
            },
            {
                "id": "cov-2",
                "exam_id": "exam-1",
                "exam_cycle_id": "cyc-1",
                "exam_phase_id": None,
                "topic_id": "t2",
                "exam_priority_score": 60,
                "is_high_yield": False,
                "confidence_score": 0.7,
                "reviewer_status": "locked",
            },
        ],
        "topics": [
            {"id": "t1", "name": "Percentage", "slug": "percentage", "subject_id": "s1", "is_active": True},
            {"id": "t2", "name": "Profit and Loss", "slug": "profit-and-loss", "subject_id": "s1", "is_active": True},
        ],
        "subjects": [{"id": "s1", "name": "Quantitative Aptitude"}],
        "aspirant_persona_snapshots": [
            {
                "user_id": "u-1",
                "computed_at": "2026-05-01T00:00:00+00:00",
                "study_policy": {"max_tasks_per_day": 4, "preferred_task_size": "small"},
            },
        ],
    }


def _self_assessment_row(
    subject_id: str = "s1",
    band: str = "strong",
    prior_mastery: float | None = 80.0,
    report_confidence: float = 0.5,
    attempts_used: int = 0,
) -> dict:
    return {
        "id": f"sa-{subject_id}-{band}",
        "user_id": "u-1",
        "exam_id": "exam-1",
        "subject_id": subject_id,
        "topic_id": None,
        "band": band,
        "prior_mastery": prior_mastery,
        "report_confidence": report_confidence,
        "attempts_used": attempts_used,
        "source": "onboarding_self_report",
    }


# ── 1. First-timer: strong band, 0 attempts — prior is hedged ───────────────

def test_first_timer_strong_subject_hedged():
    """0 attempts + strong → effective mastery~62.5, task is NOT revision (mastery < 75)."""
    seed = _base_seed()
    seed["user_topic_self_assessment"] = [
        _self_assessment_row(band="strong", prior_mastery=80.0, report_confidence=0.5, attempts_used=0)
    ]
    sb = SBStub(seed)
    out = generate_plan(sb, "u-1")
    assert out["generated"] is True

    tasks = sb.db.get("study_tasks", [])
    t1_task = next((t for t in tasks if t["topic_id"] == "t1"), None)
    assert t1_task is not None

    # effective = 0.5*80 + 0.5*45 = 62.5
    mastery_score = t1_task["why_this_task"]["mastery_score"]
    assert mastery_score is not None
    assert abs(mastery_score - 62.5) < 0.2

    # mastery < 75 → not revision
    assert t1_task["task_type"] != "revision"
    assert t1_task["why_this_task"]["mastery_source"] == "self_reported"


# ── 2. Veteran: strong band, 2+ attempts — full confidence → revision ───────

def test_veteran_strong_subject_full_prior():
    """2+ attempts + strong → effective mastery=80 → task_type=revision."""
    seed = _base_seed()
    seed["user_topic_self_assessment"] = [
        _self_assessment_row(band="strong", prior_mastery=80.0, report_confidence=1.0, attempts_used=2)
    ]
    sb = SBStub(seed)
    out = generate_plan(sb, "u-1")
    assert out["generated"] is True

    tasks = sb.db.get("study_tasks", [])
    t1_task = next((t for t in tasks if t["topic_id"] == "t1"), None)
    assert t1_task is not None

    # effective = 1.0*80 + 0.0*45 = 80.0
    mastery_score = t1_task["why_this_task"]["mastery_score"]
    assert mastery_score is not None
    assert abs(mastery_score - 80.0) < 0.2

    assert t1_task["task_type"] == "revision"
    assert t1_task["why_this_task"]["mastery_source"] == "self_reported"


# ── 3. Validated mastery wins over self-reported prior ───────────────────────

def test_validated_mastery_wins():
    """Topic with real mastery row → prior ignored, mastery_source=validated."""
    seed = _base_seed()
    # self-assessment says strong (80), but actual mastery row says 30
    seed["user_topic_self_assessment"] = [
        _self_assessment_row(band="strong", prior_mastery=80.0, report_confidence=1.0)
    ]
    seed["user_topic_mastery"] = [
        {"user_id": "u-1", "topic_id": "t1", "exam_id": "exam-1", "mastery_score": 30.0}
    ]
    sb = SBStub(seed)
    out = generate_plan(sb, "u-1")
    assert out["generated"] is True

    tasks = sb.db.get("study_tasks", [])
    t1_task = next((t for t in tasks if t["topic_id"] == "t1"), None)
    assert t1_task is not None

    why = t1_task["why_this_task"]
    # validated mastery should be 30, not 80
    assert abs(why["mastery_score"] - 30.0) < 0.2
    assert why["mastery_source"] == "validated"


# ── 4. Subject prior propagates to both topics in that subject ───────────────

def test_subject_prior_propagates_to_topics():
    """Subject-level prior fills both t1 and t2 (same subject_id s1) with same effective mastery."""
    seed = _base_seed()
    seed["user_topic_self_assessment"] = [
        _self_assessment_row(
            subject_id="s1", band="decent", prior_mastery=60.0,
            report_confidence=0.75, attempts_used=1
        )
    ]
    sb = SBStub(seed)
    out = generate_plan(sb, "u-1")
    assert out["generated"] is True

    tasks = sb.db.get("study_tasks", [])
    t1_task = next((t for t in tasks if t["topic_id"] == "t1"), None)
    t2_task = next((t for t in tasks if t["topic_id"] == "t2"), None)
    assert t1_task is not None
    assert t2_task is not None

    # effective = 0.75*60 + 0.25*45 = 45 + 11.25 = 56.25
    for task in [t1_task, t2_task]:
        why = task["why_this_task"]
        assert why["mastery_source"] == "self_reported"
        assert why["mastery_score"] is not None
        assert abs(why["mastery_score"] - 56.25) < 0.2


# ── 5. new band → cold start, mastery_source=none ───────────────────────────

def test_new_band_cold_start_unchanged():
    """band=new → prior_mastery=None → mastery stays None, mastery_source=none."""
    seed = _base_seed()
    seed["user_topic_self_assessment"] = [
        _self_assessment_row(band="new", prior_mastery=None, report_confidence=0.5)
    ]
    sb = SBStub(seed)
    out = generate_plan(sb, "u-1")
    assert out["generated"] is True

    tasks = sb.db.get("study_tasks", [])
    t1_task = next((t for t in tasks if t["topic_id"] == "t1"), None)
    assert t1_task is not None

    why = t1_task["why_this_task"]
    # No mastery → cold start default gap = 55
    assert why["mastery_score"] is None
    assert why["mastery_gap"] == 55.0
    assert why["mastery_source"] == "none"
    # task_type should be concept_learning (mastery is None)
    assert t1_task["task_type"] == "concept_learning"


# ── 6. mastery_source appears in why_this_task ───────────────────────────────

def test_mastery_source_in_why():
    """why_this_task has mastery_source field for all tasks."""
    seed = _base_seed()
    sb = SBStub(seed)
    out = generate_plan(sb, "u-1")
    assert out["generated"] is True

    tasks = sb.db.get("study_tasks", [])
    assert len(tasks) > 0
    for task in tasks:
        why = task["why_this_task"]
        assert "mastery_source" in why
        assert why["mastery_source"] in {"validated", "self_reported", "none"}


# ── 7. No priors: unchanged behavior ─────────────────────────────────────────

def test_no_priors_unchanged_behavior():
    """No self-assessment rows → plan still generates with cold-start mastery=None."""
    seed = _base_seed()
    sb = SBStub(seed)
    out = generate_plan(sb, "u-1")
    assert out["generated"] is True

    tasks = sb.db.get("study_tasks", [])
    assert len(tasks) >= 1

    for task in tasks:
        why = task["why_this_task"]
        # No priors → cold start
        assert why["mastery_score"] is None
        assert why["mastery_source"] == "none"


# ── 8. DB failure reading priors degrades gracefully ─────────────────────────

def test_priors_read_failure_degrades_gracefully():
    """DB failure on priors read → plan still generates, mastery stays None."""
    import tests.persona_questions._stub as stub_mod

    class FailPriorsStub(stub_mod.SBStub):
        def table(self, name):
            if name == "user_topic_self_assessment":
                raise RuntimeError("DB unavailable")
            return super().table(name)

    sb = FailPriorsStub(_base_seed())
    out = generate_plan(sb, "u-1")
    assert out["generated"] is True

    tasks = sb.db.get("study_tasks", [])
    assert len(tasks) >= 1
    for task in tasks:
        why = task["why_this_task"]
        # Failure → no priors → cold start
        assert why["mastery_score"] is None
        assert why["mastery_source"] == "none"
