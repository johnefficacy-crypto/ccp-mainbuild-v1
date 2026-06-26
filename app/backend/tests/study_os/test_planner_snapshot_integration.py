"""P-slice-2: locked_score_snapshots wired into the planner as a priority signal."""
from __future__ import annotations

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
