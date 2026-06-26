"""P-slice-2: locked_score_snapshots wired into the planner as a priority signal."""
from __future__ import annotations

import pytest

from app.exam_intelligence.score_snapshots import MODEL_VERSION
from app.study_os.planner import _score_topic, generate_plan
from tests.persona_questions._stub import SBStub


def _base_seed() -> dict:
    """Minimal seed: 2 locked-coverage topics, no snapshots by default."""
    return {
        "profiles": [{"id": "u-1", "target_exam": "ssc-cgl"}],
        "exams": [
            {"id": "exam-1", "slug": "ssc-cgl", "name": "SSC CGL",
             "exam_type": "recruitment", "is_active": True},
        ],
        "exam_cycles": [
            {"id": "cyc-1", "exam_id": "exam-1", "exam_start": "2026-09-15"},
        ],
        "exam_topic_coverage": [
            {"id": "cov-1", "exam_id": "exam-1", "exam_cycle_id": "cyc-1",
             "exam_phase_id": None, "topic_id": "t1", "exam_priority_score": 80,
             "is_high_yield": True, "confidence_score": 0.85, "reviewer_status": "locked"},
            {"id": "cov-2", "exam_id": "exam-1", "exam_cycle_id": "cyc-1",
             "exam_phase_id": None, "topic_id": "t2", "exam_priority_score": 60,
             "is_high_yield": False, "confidence_score": 0.7, "reviewer_status": "locked"},
        ],
        "topics": [
            {"id": "t1", "name": "Percentage", "slug": "percentage",
             "subject_id": "s1", "is_active": True},
            {"id": "t2", "name": "Profit and Loss", "slug": "profit-and-loss",
             "subject_id": "s1", "is_active": True},
        ],
        "subjects": [{"id": "s1", "name": "Quantitative Aptitude"}],
        "aspirant_persona_snapshots": [
            {"user_id": "u-1", "computed_at": "2026-05-01T00:00:00+00:00",
             "study_policy": {"max_tasks_per_day": 4, "preferred_task_size": "small"}},
        ],
    }


def _snapshot(topic_id: str, priority: float, confidence: float = 0.9,
              status: str = "locked") -> dict:
    return {
        "id": f"snap-{topic_id}",
        "exam_id": "exam-1",
        "topic_id": topic_id,
        "exam_phase_id": None,
        "status": status,
        "model_version": MODEL_VERSION,
        "exam_priority_score": priority,
        "is_high_yield": priority >= 70,
        "confidence_score": confidence,
        "evidence_count": 3,
        "score_components": {"frequency_component": 0.5, "coverage_component": 0.4},
        "input_summary": {"fingerprint": "abc123"},
        "computed_at": "2026-06-01T00:00:00+00:00",
    }


# ── 1. Snapshot component in _score_topic ─────────────────────────────────────

def test_snapshot_adds_bounded_component():
    """Locked snapshot adds up to 15 pts; absent snapshot adds 0."""
    weights = {"coverage_w": 1.0, "mastery_w": 0.5, "high_yield_bonus": 10.0}
    cov = {"coverage_priority": 50, "is_high_yield": False}

    score_no_snap, _ = _score_topic(cov, 0, None, False, weights=weights, pinned=False)
    score_with_snap, _ = _score_topic(
        cov, 0, None, False,
        weights=weights, pinned=False,
        snapshot={"exam_priority_score": 100.0, "confidence_score": 0.9},
    )
    assert score_with_snap > score_no_snap
    assert score_with_snap - score_no_snap <= 15.0


def test_snapshot_component_capped_at_15():
    """exam_priority_score=100 must yield exactly 15 pts snapshot_component."""
    weights = {"coverage_w": 0.0, "mastery_w": 0.0, "high_yield_bonus": 0.0}
    cov = {"coverage_priority": 0, "is_high_yield": False}
    score_no, _ = _score_topic(cov, 0, 50.0, False, weights=weights, pinned=False)
    score_yes, _ = _score_topic(
        cov, 0, 50.0, False,
        weights=weights, pinned=False,
        snapshot={"exam_priority_score": 100.0},
    )
    assert round(score_yes - score_no, 6) == 15.0


def test_null_exam_priority_score_treated_as_zero():
    """snapshot with exam_priority_score=None must add 0 pts."""
    weights = {"coverage_w": 0.0, "mastery_w": 0.0, "high_yield_bonus": 0.0}
    cov = {"coverage_priority": 0, "is_high_yield": False}
    score_no, _ = _score_topic(cov, 0, None, False, weights=weights, pinned=False)
    score_null, _ = _score_topic(
        cov, 0, None, False,
        weights=weights, pinned=False,
        snapshot={"exam_priority_score": None},
    )
    assert score_no == score_null


# ── 2. Graceful fallback when no snapshots exist ───────────────────────────────

def test_plan_generates_without_snapshots():
    """No exam_topic_score_snapshots rows → plan still generates, no crash."""
    sb = SBStub(_base_seed())
    out = generate_plan(sb, "u-1")
    assert out["generated"] is True
    tasks = sb.db.get("study_tasks", [])
    assert len(tasks) >= 1
    # why_this_task snapshot fields should be None when absent
    for t in tasks:
        why = t["why_this_task"]
        assert why["snapshot_priority_score"] is None
        assert why["snapshot_confidence"] is None
        assert why["snapshot_model_version"] is None


# ── 3. Locked snapshot flows into priority and why payload ─────────────────────

def test_locked_snapshot_boosts_priority_and_appears_in_why():
    """Topic with a locked snapshot has a higher priority and why payload fields."""
    seed = _base_seed()
    seed["exam_topic_score_snapshots"] = [_snapshot("t1", priority=90.0, confidence=0.95)]
    sb = SBStub(seed)
    out = generate_plan(sb, "u-1")
    assert out["generated"] is True

    tasks = sb.db["study_tasks"]
    t1_task = next((t for t in tasks if t["topic_id"] == "t1"), None)
    t2_task = next((t for t in tasks if t["topic_id"] == "t2"), None)

    assert t1_task is not None
    why = t1_task["why_this_task"]
    assert why["snapshot_priority_score"] == 90.0
    assert why["snapshot_confidence"] == 0.95
    assert why["snapshot_model_version"] == MODEL_VERSION

    # t1 (with snapshot) must score higher than t2 (without)
    if t2_task:
        assert t1_task["priority_score"] > t2_task["priority_score"]


def test_snapshot_confidence_appears_in_summary():
    """'analysis confidence X%' must appear in why_this_task.summary when snapshot present."""
    seed = _base_seed()
    seed["exam_topic_score_snapshots"] = [_snapshot("t1", priority=80.0, confidence=0.92)]
    sb = SBStub(seed)
    generate_plan(sb, "u-1")

    tasks = sb.db["study_tasks"]
    t1_task = next(t for t in tasks if t["topic_id"] == "t1")
    summary = t1_task["why_this_task"]["summary"]
    assert "92%" in summary or "analysis confidence" in summary


# ── 4. Draft snapshot not included ────────────────────────────────────────────

def test_draft_snapshot_not_included():
    """draft snapshot must not influence priority — only locked rows reach planner."""
    seed = _base_seed()
    seed["exam_topic_score_snapshots"] = [_snapshot("t1", priority=100.0, status="draft")]
    sb = SBStub(seed)
    generate_plan(sb, "u-1")

    tasks = sb.db["study_tasks"]
    t1_task = next((t for t in tasks if t["topic_id"] == "t1"), None)
    assert t1_task is not None
    why = t1_task["why_this_task"]
    # Draft snapshots are filtered by locked_score_snapshots() → no snapshot fields
    assert why["snapshot_priority_score"] is None


# ── 5. Snapshot for topic not in coverage is ignored ──────────────────────────

def test_snapshot_for_uncovered_topic_ignored():
    """A locked snapshot for a topic not in locked coverage must not create a task."""
    seed = _base_seed()
    # t99 has a snapshot but no coverage row
    seed["exam_topic_score_snapshots"] = [_snapshot("t99", priority=100.0)]
    sb = SBStub(seed)
    generate_plan(sb, "u-1")

    tasks = sb.db["study_tasks"]
    topic_ids = {t["topic_id"] for t in tasks}
    assert "t99" not in topic_ids


# ── 6. Determinism ────────────────────────────────────────────────────────────

def test_same_inputs_same_task_order():
    """Two consecutive generate_plan calls on the same SBStub produce the same task order."""
    seed = _base_seed()
    seed["exam_topic_score_snapshots"] = [
        _snapshot("t1", priority=90.0),
        _snapshot("t2", priority=50.0),
    ]
    sb = SBStub(seed)

    generate_plan(sb, "u-1")
    first_order = [t["topic_id"] for t in sb.db["study_tasks"]]

    # Wipe tasks so second call regenerates cleanly
    sb.db.pop("study_tasks", None)
    sb.db.pop("study_plans", None)
    sb.db.pop("study_plan_versions", None)
    sb.db.pop("study_adaptation_events", None)

    generate_plan(sb, "u-1")
    second_order = [t["topic_id"] for t in sb.db["study_tasks"]]

    assert first_order == second_order


# ── 7. Confidence modulation ───────────────────────────────────────────────────

def test_zero_confidence_produces_zero_snapshot_component():
    """confidence_score=0.0 → snapshot contributes 0 pts (same as no snapshot)."""
    weights = {"coverage_w": 0.0, "mastery_w": 0.0, "high_yield_bonus": 0.0}
    cov = {"coverage_priority": 0, "is_high_yield": False}
    score_no, _ = _score_topic(cov, 0, None, False, weights=weights, pinned=False)
    score_zero_conf, _ = _score_topic(
        cov, 0, None, False,
        weights=weights, pinned=False,
        snapshot={"exam_priority_score": 100.0, "confidence_score": 0.0},
    )
    assert score_no == score_zero_conf


def test_confidence_scales_snapshot_component():
    """confidence_score=0.5 → snapshot component is exactly half the max."""
    weights = {"coverage_w": 0.0, "mastery_w": 0.0, "high_yield_bonus": 0.0}
    cov = {"coverage_priority": 0, "is_high_yield": False}
    score_full_conf, _ = _score_topic(
        cov, 0, None, False,
        weights=weights, pinned=False,
        snapshot={"exam_priority_score": 100.0, "confidence_score": 1.0},
    )
    score_half_conf, _ = _score_topic(
        cov, 0, None, False,
        weights=weights, pinned=False,
        snapshot={"exam_priority_score": 100.0, "confidence_score": 0.5},
    )
    assert round(score_full_conf - score_half_conf, 6) == round(score_half_conf, 6)


# ── 8. Snapshot lineage in why_this_task ──────────────────────────────────────

def test_snapshot_id_and_lineage_persisted_in_why():
    """snapshot_id, computed_at, evidence_count appear in why_this_task."""
    seed = _base_seed()
    seed["exam_topic_score_snapshots"] = [_snapshot("t1", priority=80.0, confidence=0.9)]
    sb = SBStub(seed)
    generate_plan(sb, "u-1")
    tasks = sb.db["study_tasks"]
    t1_task = next(t for t in tasks if t["topic_id"] == "t1")
    why = t1_task["why_this_task"]
    assert why["snapshot_id"] == "snap-t1"
    assert why["snapshot_computed_at"] == "2026-06-01T00:00:00+00:00"
    assert why["snapshot_evidence_count"] == 3


# ── 9. Snapshot read failure ───────────────────────────────────────────────────

def test_snapshot_read_failure_recorded_in_context():
    """Snapshot table read failure → plan still generates, snapshot_read_failed=True."""
    import tests.persona_questions._stub as stub_mod

    class FailSnapStub(stub_mod.SBStub):
        def table(self, name):
            if name == "exam_topic_score_snapshots":
                raise RuntimeError("DB unavailable")
            return super().table(name)

    sb = FailSnapStub(_base_seed())
    out = generate_plan(sb, "u-1")
    assert out["generated"] is True
    # why_this_task snapshot fields must be None
    for t in sb.db["study_tasks"]:
        assert t["why_this_task"]["snapshot_id"] is None
        assert t["why_this_task"]["snapshot_priority_score"] is None


# ── 10. Snapshot reasoning trace ──────────────────────────────────────────────

def test_snapshot_reasoning_trace_row_added():
    """build_task_reasoning_detail adds a locked_score_snapshot trace row from persisted lineage."""
    from app.study_os.task_reasoning import build_task_reasoning_detail
    task = {
        "id": "task-1", "topic": "Percentage", "task_type": "revision",
        "status": "planned", "planned_minutes": 25,
        "why_this_task": {
            "snapshot_id": "snap-abc",
            "snapshot_priority_score": 80.0,
            "snapshot_confidence": 0.92,
            "snapshot_model_version": MODEL_VERSION,
            "snapshot_computed_at": "2026-06-01T00:00:00+00:00",
            "priority_score": 90.0,
        }
    }
    result = build_task_reasoning_detail(task)
    snap_rows = [r for r in result["reasoning_trace"] if r.get("rule_key") == "locked_score_snapshot"]
    assert len(snap_rows) == 1
    assert snap_rows[0]["evidence_id"] == "snap-abc"
    assert snap_rows[0]["status"] == "locked"
    assert snap_rows[0]["model_version"] == MODEL_VERSION
    assert snap_rows[0]["confidence"] == pytest.approx(0.92)


def test_no_snapshot_trace_row_when_no_snapshot():
    """No locked_score_snapshot trace row when why_this_task has no snapshot fields."""
    from app.study_os.task_reasoning import build_task_reasoning_detail
    task = {
        "id": "task-1", "topic": "Percentage", "task_type": "revision",
        "status": "planned", "planned_minutes": 25,
        "why_this_task": {"snapshot_id": None, "snapshot_priority_score": None},
    }
    result = build_task_reasoning_detail(task)
    snap_rows = [r for r in result["reasoning_trace"] if r.get("rule_key") == "locked_score_snapshot"]
    assert len(snap_rows) == 0


# ── 11. Deduplication: latest locked snapshot wins ────────────────────────────

def test_two_snapshots_same_topic_latest_wins():
    """When two locked snapshots exist for t1, the first in list (latest by computed_at) wins."""
    seed = _base_seed()
    snap_newer = {**_snapshot("t1", priority=90.0), "computed_at": "2026-06-01T00:00:00+00:00"}
    snap_older = {**_snapshot("t1", priority=50.0), "id": "snap-t1-old", "computed_at": "2026-01-01T00:00:00+00:00"}
    # SBStub returns rows in insert order; newer first → should win the dedup
    seed["exam_topic_score_snapshots"] = [snap_newer, snap_older]
    sb = SBStub(seed)
    generate_plan(sb, "u-1")
    tasks = sb.db["study_tasks"]
    t1_task = next(t for t in tasks if t["topic_id"] == "t1")
    assert t1_task["why_this_task"]["snapshot_priority_score"] == 90.0
