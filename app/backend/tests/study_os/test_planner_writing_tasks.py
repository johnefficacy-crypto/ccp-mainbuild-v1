"""EWP-5 — planner generation of english_writing_session tasks.

Covers the two deterministic units in
``study_os.writing_practice.planner_tasks``:

* ``build_writing_tasks`` — pure builder (eligibility filter, dedup, cap,
  ordering, launch-stamp shape).
* ``resolve_writing_eligible_topic_ids`` — the DB gate (verified + active +
  English subject + runtime-ready + applicability), driven through ``SBStub``.
"""
from __future__ import annotations

from app.study_os import planner
from app.study_os.writing_practice import planner_tasks
from app.study_os.writing_practice.launch import LAUNCH_ENGLISH_WRITING_SESSION
from tests.persona_questions._stub import SBStub
from tests.study_os.test_planner import _seed


def _cov(topic_id: str, name: str, score: float, *, high_yield: bool = False) -> dict:
    return {
        "coverage_id": f"cov-{topic_id}",
        "topic_id": topic_id,
        "topic_name": name,
        "subject_id": "s-eng",
        "subject_name": "English Language",
        "exam_phase_id": "ph1",
        "coverage_priority": score,
        "is_high_yield": high_yield,
        "_priority_score": score,
    }


# ── build_writing_tasks (pure) ──────────────────────────────────────────────

def test_emits_launch_stamped_task_for_eligible_topic():
    ordered = [_cov("te1", "Sentence Improvement", 90, high_yield=True)]
    tasks = planner_tasks.build_writing_tasks(
        ordered,
        exam_id="exam-1",
        exam_phase_id="ph1",
        minutes=25,
        today="2026-07-10",
        eligible_topic_ids={"te1"},
        existing_writing_topic_ids=set(),
        max_writing_tasks=2,
    )
    assert len(tasks) == 1
    t = tasks[0]
    assert t["task_type"] == "sentence_construction"
    assert t["launch_type"] == LAUNCH_ENGLISH_WRITING_SESSION
    assert t["launch_entity_id"] is None  # no session yet — created on click
    assert t["launch_context"] == {"exercise_type": "sentence_construction"}
    assert t["topic_id"] == "te1"
    assert t["exam_id"] == "exam-1"
    assert t["exam_phase_id"] == "ph1"
    assert t["exam_topic_coverage_id"] == "cov-te1"
    assert t["status"] == "planned"
    assert t["planned_minutes"] == 25
    assert t["scheduled_date"] == "2026-07-10"
    assert t["user_id"] is None  # filled in by _persist
    assert t["why_this_task"]["launch_target"] == LAUNCH_ENGLISH_WRITING_SESSION


def test_skips_topics_not_in_eligible_set():
    ordered = [_cov("te1", "A", 90), _cov("tq1", "Quant", 80)]
    tasks = planner_tasks.build_writing_tasks(
        ordered,
        exam_id="exam-1",
        exam_phase_id=None,
        minutes=40,
        today="2026-07-10",
        eligible_topic_ids={"te1"},  # tq1 has no writing prompt
        existing_writing_topic_ids=set(),
        max_writing_tasks=5,
    )
    assert [t["topic_id"] for t in tasks] == ["te1"]


def test_dedup_skips_topic_with_existing_active_writing_task():
    ordered = [_cov("te1", "A", 90), _cov("te2", "B", 85)]
    tasks = planner_tasks.build_writing_tasks(
        ordered,
        exam_id="exam-1",
        exam_phase_id=None,
        minutes=40,
        today="2026-07-10",
        eligible_topic_ids={"te1", "te2"},
        existing_writing_topic_ids={"te1"},  # already started/completed today
        max_writing_tasks=5,
    )
    assert [t["topic_id"] for t in tasks] == ["te2"]


def test_respects_cap_and_priority_order():
    ordered = [
        _cov("te3", "C", 70),
        _cov("te1", "A", 95),
        _cov("te2", "B", 85),
    ]
    # ordered is priority-ordered by the planner; the builder preserves it.
    tasks = planner_tasks.build_writing_tasks(
        ordered,
        exam_id="exam-1",
        exam_phase_id=None,
        minutes=40,
        today="2026-07-10",
        eligible_topic_ids={"te1", "te2", "te3"},
        existing_writing_topic_ids=set(),
        max_writing_tasks=2,
    )
    assert [t["topic_id"] for t in tasks] == ["te3", "te1"]  # first two in order


def test_no_eligible_or_zero_cap_returns_empty():
    ordered = [_cov("te1", "A", 90)]
    assert planner_tasks.build_writing_tasks(
        ordered, exam_id="e", exam_phase_id=None, minutes=40, today="d",
        eligible_topic_ids=set(), existing_writing_topic_ids=set(), max_writing_tasks=2,
    ) == []
    assert planner_tasks.build_writing_tasks(
        ordered, exam_id="e", exam_phase_id=None, minutes=40, today="d",
        eligible_topic_ids={"te1"}, existing_writing_topic_ids=set(), max_writing_tasks=0,
    ) == []


# ── resolve_writing_eligible_topic_ids (SBStub) ─────────────────────────────

def _prompt(pid: str, topic_id: str, *, exercise="sentence_construction",
            status="verified", active=True) -> dict:
    return {
        "id": pid, "topic_id": topic_id, "subject_id": "s-eng",
        "exercise_type": exercise, "reviewer_status": status, "is_active": active,
    }


def _global_target(pid: str, status: str = "active") -> dict:
    return {
        "prompt_id": pid, "is_global": True, "exam_family_id": None,
        "exam_id": None, "exam_phase_id": None, "applicability_status": status,
    }


def _db(prompts, targets) -> SBStub:
    return SBStub({
        "subjects": [{"id": "s-eng", "slug": "english-language", "name": "English"}],
        "exams": [{"id": "exam-1", "exam_family_id": None}],
        "writing_prompts": prompts,
        "writing_prompt_targets": targets,
    })


def test_resolve_includes_verified_active_ready_applicable():
    sb = _db([_prompt("wp1", "te1")], [_global_target("wp1")])
    got = planner_tasks.resolve_writing_eligible_topic_ids(
        sb, exam_id="exam-1", exam_phase_id="ph1", candidate_topic_ids=["te1", "te2"]
    )
    assert got == {"te1"}


def test_resolve_excludes_unverified_inactive_and_non_ready():
    sb = _db(
        [
            _prompt("wp1", "te1", status="pending"),        # not verified
            _prompt("wp2", "te2", active=False),            # not active
            _prompt("wp3", "te3", exercise="paragraph_writing"),  # not runtime-ready
        ],
        [_global_target("wp1"), _global_target("wp2"), _global_target("wp3")],
    )
    got = planner_tasks.resolve_writing_eligible_topic_ids(
        sb, exam_id="exam-1", exam_phase_id=None,
        candidate_topic_ids=["te1", "te2", "te3"],
    )
    assert got == set()


def test_resolve_excludes_topic_without_active_applicability_target():
    sb = _db([_prompt("wp1", "te1")], [_global_target("wp1", status="pending_review")])
    got = planner_tasks.resolve_writing_eligible_topic_ids(
        sb, exam_id="exam-1", exam_phase_id=None, candidate_topic_ids=["te1"]
    )
    assert got == set()


def test_resolve_fails_closed_when_english_subject_missing():
    sb = SBStub({
        "subjects": [],  # no english-language subject seeded
        "exams": [{"id": "exam-1", "exam_family_id": None}],
        "writing_prompts": [_prompt("wp1", "te1")],
        "writing_prompt_targets": [_global_target("wp1")],
    })
    got = planner_tasks.resolve_writing_eligible_topic_ids(
        sb, exam_id="exam-1", exam_phase_id=None, candidate_topic_ids=["te1"]
    )
    # Fail closed: with no english-language subject resolved, no writing tasks
    # are generated even though the prompt would otherwise be eligible.
    assert got == set()


def test_resolve_empty_candidates_returns_empty():
    sb = _db([_prompt("wp1", "te1")], [_global_target("wp1")])
    assert planner_tasks.resolve_writing_eligible_topic_ids(
        sb, exam_id="exam-1", exam_phase_id=None, candidate_topic_ids=[]
    ) == set()


# ── end-to-end through the real planner._compute_plan ───────────────────────

def _seed_with_english_writing() -> dict:
    """The SSC CGL planner seed, plus an English writing prompt for t4.

    t4 (Vocabulary) is subject s2 (English Language); give s2 the
    ``english-language`` slug and land a verified+active+global
    sentence_construction prompt so the planner can generate a writing task.
    """
    db = _seed()
    for s in db["subjects"]:
        if s["id"] == "s2":
            s["slug"] = "english-language"
    db["writing_prompts"] = [
        {"id": "wp-eng-1", "topic_id": "t4", "subject_id": "s2",
         "exercise_type": "sentence_construction",
         "reviewer_status": "verified", "is_active": True},
    ]
    db["writing_prompt_targets"] = [
        {"prompt_id": "wp-eng-1", "is_global": True, "exam_family_id": None,
         "exam_id": None, "exam_phase_id": None, "applicability_status": "active"},
    ]
    return db


def test_compute_plan_generates_english_writing_task():
    result = planner._compute_plan(SBStub(_seed_with_english_writing()), "u-1", reason="test")
    assert result["generated"] is True
    writing = [t for t in result["tasks"]
               if t.get("launch_type") == LAUNCH_ENGLISH_WRITING_SESSION]
    assert len(writing) == 1
    t = writing[0]
    assert t["topic_id"] == "t4"
    assert t["task_type"] == "sentence_construction"
    assert t["launch_entity_id"] is None
    assert t["launch_context"] == {"exercise_type": "sentence_construction"}
    # additive to the topic-study plan, recorded in the audit context
    assert result["input_context"]["writing_task_count"] == 1


def test_compute_plan_no_writing_task_when_no_english_prompt():
    db = _seed()  # no writing_prompts at all
    result = planner._compute_plan(SBStub(db), "u-1", reason="test")
    assert result["generated"] is True
    assert [t for t in result["tasks"]
            if t.get("launch_type") == LAUNCH_ENGLISH_WRITING_SESSION] == []
    assert result["input_context"]["writing_task_count"] == 0


def test_compute_plan_dedups_against_active_writing_task():
    db = _seed_with_english_writing()
    # An in-progress (non-planned) writing task for t4 already exists today.
    db["study_plans"] = [
        {"id": "plan-1", "user_id": "u-1", "status": "active",
         "current_plan_version_id": "v-0"},
    ]
    db["study_tasks"] = [
        {"id": "task-existing", "plan_id": "plan-1", "user_id": "u-1",
         "topic_id": "t4", "scheduled_date": planner._today_iso(),
         "launch_type": LAUNCH_ENGLISH_WRITING_SESSION, "status": "in_progress"},
    ]
    result = planner._compute_plan(SBStub(db), "u-1", reason="test")
    assert result["generated"] is True
    assert [t for t in result["tasks"]
            if t.get("launch_type") == LAUNCH_ENGLISH_WRITING_SESSION] == []
    assert result["input_context"]["writing_task_count"] == 0
