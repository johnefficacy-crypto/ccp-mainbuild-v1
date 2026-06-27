"""P-slice-2b O-slice-2: self-assessment priors wired into the planner."""
from __future__ import annotations

import pytest

from app.study_os.planner import _load_topic_priors, generate_plan
from app.study_os.task_reasoning import build_task_reasoning_detail
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


# ── 5. new band → cold-start scoring, but explicit self-report provenance ────

def test_new_band_cold_start_explicit_self_report():
    """band=new → prior_mastery=None → mastery stays None and the cold-start gap
    (55) is preserved, BUT it is now an explicit self-report: mastery_source is
    'self_reported' and self_assessment_band='new' is persisted, so it is
    distinguishable from a topic with NO self-report at all (see test 7)."""
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
    # Cold-start scoring intent preserved: no estimate → mastery None, gap 55.
    assert why["mastery_score"] is None
    assert why["mastery_gap"] == 55.0
    # task_type should be concept_learning (mastery is None)
    assert t1_task["task_type"] == "concept_learning"
    # Provenance is now an explicit self-report (was 'none' pre-hardening).
    assert why["mastery_source"] == "self_reported"
    # 'new' band is persisted so "never studied" is distinguishable from "no report".
    assert why["self_assessment_band"] == "new"
    assert why["self_assessment_prior_mastery"] is None
    assert why["self_assessment_level"] == "subject"


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
        # No priors → cold start, and NO self-report provenance at all
        # (contrast test 5: band='new' is a real report → self_reported).
        assert why["mastery_score"] is None
        assert why["mastery_source"] == "none"
        assert "self_assessment_band" not in why


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


# ── 9. mastery-read failure → priors NOT consumed (fail closed) ──────────────

def test_mastery_read_failure_blocks_priors():
    """A user_topic_mastery READ FAILURE must not let a self-report override
    validated evidence: no prior is consumed and input_context flags it."""
    import tests.persona_questions._stub as stub_mod

    class FailMasteryStub(stub_mod.SBStub):
        def table(self, name):
            if name == "user_topic_mastery":
                raise RuntimeError("user_topic_mastery unavailable")
            return super().table(name)

    seed = _base_seed()
    # A confident 'strong' prior that WOULD blend if priors were consumed.
    seed["user_topic_self_assessment"] = [
        _self_assessment_row(band="strong", prior_mastery=80.0, report_confidence=1.0, attempts_used=2)
    ]
    sb = FailMasteryStub(seed)
    out = generate_plan(sb, "u-1")
    assert out["generated"] is True

    tasks = sb.db.get("study_tasks", [])
    assert len(tasks) >= 1
    # No task may be self_reported — priors were fail-closed.
    for task in tasks:
        why = task["why_this_task"]
        assert why["mastery_source"] != "self_reported"
        assert why["mastery_score"] is None
        assert "self_assessment_band" not in why

    gen_ctx = sb.db["study_plans"][0]["generation_context"]
    assert gen_ctx["mastery_read_failed"] is True
    # No priors consumed → summary stays None.
    assert gen_ctx["self_assessment_summary"] is None


# ── 10. _why_summary honesty: no fake "recent accuracy" for self-reports ─────

def test_why_summary_self_reported_has_no_recent_accuracy():
    """Self-reported summary must NOT claim 'recent accuracy'; validated DOES."""
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
    summary = t1_task["why_this_task"]["summary"]
    assert "recent accuracy" not in summary
    assert "not yet validated by practice" in summary

    # Validated task: 'recent accuracy' IS present.
    vseed = _base_seed()
    vseed["user_topic_mastery"] = [
        {"user_id": "u-1", "topic_id": "t1", "exam_id": "exam-1", "mastery_score": 72.0}
    ]
    vsb = SBStub(vseed)
    vout = generate_plan(vsb, "u-1")
    assert vout["generated"] is True
    vtasks = vsb.db.get("study_tasks", [])
    vt1 = next((t for t in vtasks if t["topic_id"] == "t1"), None)
    assert vt1 is not None
    assert vt1["why_this_task"]["mastery_source"] == "validated"
    assert "recent accuracy" in vt1["why_this_task"]["summary"]


# ── 11. self_assessment_summary audit payload is expanded ────────────────────

def test_self_assessment_summary_audit_payload():
    """input_context.self_assessment_summary carries by_band, attempts_used,
    subject_ids, and assessment_level when priors exist."""
    seed = _base_seed()
    seed["user_topic_self_assessment"] = [
        _self_assessment_row(band="decent", prior_mastery=60.0, report_confidence=0.75, attempts_used=1)
    ]
    sb = SBStub(seed)
    out = generate_plan(sb, "u-1")
    assert out["generated"] is True

    gen_ctx = sb.db["study_plans"][0]["generation_context"]
    summary = gen_ctx["self_assessment_summary"]
    assert summary is not None
    # Both t1 and t2 share subject s1 → both get the 'decent' prior.
    assert summary["topics_with_prior"] == 2
    assert summary["assessment_level"] == "subject"
    assert summary["by_band"] == {"decent": 2}
    assert summary["attempts_used"] == 1
    assert summary["subject_ids"] == ["s1"]


# ── 12. self_assessment_prior reasoning-trace row (from persisted lineage) ────

def test_self_assessment_prior_trace_row_from_lineage():
    """build_task_reasoning_detail emits a self_assessment_prior trace row from
    the persisted why dict, with no DB re-query, marked not-yet-validated."""
    # 'new' band: prior_mastery None.
    new_task = {
        "id": "task-new", "topic": "Percentage", "task_type": "concept_learning",
        "status": "planned", "planned_minutes": 25,
        "why_this_task": {
            "mastery_source": "self_reported",
            "self_assessment_band": "new",
            "self_assessment_prior_mastery": None,
            "self_assessment_confidence": 0.5,
            "self_assessment_level": "subject",
        },
    }
    result = build_task_reasoning_detail(new_task)
    rows = [r for r in result["reasoning_trace"] if r.get("rule_key") == "self_assessment_prior"]
    assert len(rows) == 1
    assert rows[0]["band"] == "new"
    assert rows[0]["prior_mastery"] is None
    assert rows[0]["assessment_level"] == "subject"
    assert rows[0]["status"] == "not yet validated by practice"
    assert "never studied" in rows[0]["label"]

    # Banded estimate: prior_mastery present.
    est_task = {
        "id": "task-est", "topic": "Percentage", "task_type": "retrieval_practice",
        "status": "planned", "planned_minutes": 25,
        "why_this_task": {
            "mastery_source": "self_reported",
            "self_assessment_band": "strong",
            "self_assessment_prior_mastery": 80.0,
            "self_assessment_confidence": 1.0,
            "self_assessment_level": "subject",
        },
    }
    est_rows = [
        r for r in build_task_reasoning_detail(est_task)["reasoning_trace"]
        if r.get("rule_key") == "self_assessment_prior"
    ]
    assert len(est_rows) == 1
    assert est_rows[0]["band"] == "strong"
    assert est_rows[0]["prior_mastery"] == 80.0
    assert "not yet validated by practice" in est_rows[0]["label"]

    # No self-report → no row.
    plain_task = {
        "id": "task-plain", "topic": "Percentage", "task_type": "revision",
        "status": "planned", "planned_minutes": 25,
        "why_this_task": {"mastery_source": "none"},
    }
    plain_rows = [
        r for r in build_task_reasoning_detail(plain_task)["reasoning_trace"]
        if r.get("rule_key") == "self_assessment_prior"
    ]
    assert len(plain_rows) == 0
