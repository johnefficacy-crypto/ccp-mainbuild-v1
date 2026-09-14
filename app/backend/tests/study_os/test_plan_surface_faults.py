"""PLAN-BUG-02 — the backend halves of the six plan-page surface faults.

F2 (the heading's missing day), F4 (the exams route that failed as a whole) and
F5 (two surfaces that listed unchosen optionals) all have their cause in backend
code. F1, F3 and F6 are frontend-only and are pinned in
``app/frontend/src/pages/StudyPlan.faults.test.jsx``.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from tests.persona_questions._stub import SBStub
from tests.study_os.test_planner import _seed

from app.api import canonical
from app.study_os import plan_by_subject, plan_timeline
from app.study_os.subjects import declined_elective_subject_ids, in_scope_subject


# ── F2 — the heading must never be able to say "Day null" ────────────────


def test_plan_day_number_counts_from_the_plans_start_date():
    today = date(2026, 9, 14)
    assert canonical._plan_day_number("2026-09-14", today) == 1
    assert canonical._plan_day_number("2026-09-01", today) == 14
    assert canonical._plan_day_number("2026-09-01T00:00:00+00:00", today) == 14


def test_plan_day_number_is_none_when_it_cannot_be_known():
    """None is a real answer. The caller omits the segment; it never prints it."""
    today = date(2026, 9, 14)
    for bad in (None, "", "not-a-date", "2026-13-45"):
        assert canonical._plan_day_number(bad, today) is None
    # A plan dated in the future has no day number yet.
    assert canonical._plan_day_number("2026-10-01", today) is None


def test_active_plan_row_selects_start_date():
    """The column that supplies the heading has to actually be read.

    `_ensure_active_plan` selected only `id`, which is why `day` was hardcoded
    `None` — nothing on the response could have supplied it.
    """
    start = (datetime.now(timezone.utc).date() - timedelta(days=3)).isoformat()
    sb = SBStub(
        {
            "study_plans": [
                {"id": "plan-1", "user_id": "u-1", "status": "active", "start_date": start}
            ]
        }
    )
    row = canonical._active_plan_row(sb, "u-1")
    assert row is not None
    assert row.get("start_date") == start
    assert canonical._plan_day_number(
        row["start_date"], datetime.now(timezone.utc).date()
    ) == 4


# ── F4 — the exams route no longer fails as a whole ──────────────────────


def _exam_seed() -> dict[str, Any]:
    return {
        "exams": [
            {"id": "e1", "slug": "ssc-cgl", "name": "SSC CGL", "exam_type": "recruitment",
             "is_active": True, "exam_family_id": None, "default_difficulty_level": None},
            {"id": "e2", "slug": "upsc-cse", "name": "UPSC CSE", "exam_type": "recruitment",
             "is_active": True, "exam_family_id": None, "default_difficulty_level": None},
        ],
        "exam_topic_coverage": [
            {"id": "c1", "exam_id": "e1", "topic_id": "t1", "reviewer_status": "locked"},
            {"id": "c2", "exam_id": "e1", "topic_id": "t2", "reviewer_status": "locked"},
            {"id": "c3", "exam_id": "e1", "topic_id": "t3", "reviewer_status": "draft"},
        ],
        "exam_cycles": [
            {"id": "cy1", "exam_id": "e1", "year": 2026, "cycle_name": "2026",
             "exam_start": "2099-01-01", "reviewer_status": "verified"},
        ],
    }


def _call_exams(sb: SBStub, **kwargs: Any) -> dict[str, Any]:
    import asyncio

    from app.api import study_os as api

    original = api.get_supabase_admin
    api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    try:
        return asyncio.run(api.list_study_exams(user={"id": "u-1"}, **kwargs))
    finally:
        api.get_supabase_admin = original  # type: ignore[assignment]


def test_exams_route_returns_counts_and_cycles_without_a_per_exam_loop():
    sb = _exam_seed()
    out = _call_exams(SBStub(sb))
    by_id = {i["id"]: i for i in out["items"]}

    assert by_id["e1"]["locked_coverage_count"] == 2  # the draft row is excluded
    assert by_id["e1"]["planner_ready"] is True
    assert by_id["e1"]["next_cycle"]["id"] == "cy1"

    assert by_id["e2"]["locked_coverage_count"] == 0
    assert by_id["e2"]["planner_ready"] is False
    assert by_id["e2"]["next_cycle"] is None


def test_exams_route_issues_a_bounded_number_of_reads():
    """The regression this fault was: two reads PER EXAM, up to 500 exams.

    One slow or failing call anywhere in that loop threw out of an unguarded
    route as a 500, which is what pinned "Couldn't load exams" on the page.
    """
    seed = _exam_seed()
    seed["exams"] = [
        {"id": f"e{i}", "slug": f"x{i}", "name": f"Exam {i}", "exam_type": "recruitment",
         "is_active": True, "exam_family_id": None, "default_difficulty_level": None}
        for i in range(40)
    ]
    sb = SBStub(seed)

    calls: list[str] = []
    original_table = sb.table

    def _table(name: str):
        calls.append(name)
        return original_table(name)

    sb.table = _table  # type: ignore[assignment]

    out = _call_exams(sb)
    assert len(out["items"]) == 40
    # exams + exam_topic_coverage + exam_cycles. The old loop made 81.
    assert len(calls) == 3, calls


def test_exams_route_fails_closed_on_a_coverage_read_error():
    """A failed coverage read must never report an exam as planner-ready."""
    sb = SBStub(_exam_seed())
    original_table = sb.table

    def _table(name: str):
        q = original_table(name)
        if name == "exam_topic_coverage":
            def _boom():
                raise RuntimeError("coverage read failed")
            q.execute = _boom  # type: ignore[assignment]
        return q

    sb.table = _table  # type: ignore[assignment]

    out = _call_exams(sb)
    assert out["coverage_read_failed"] is True
    assert all(i["planner_ready"] is False for i in out["items"])


def test_exams_route_reports_a_reason_when_the_exams_read_fails():
    from fastapi import HTTPException

    sb = SBStub(_exam_seed())
    original_table = sb.table

    def _table(name: str):
        q = original_table(name)
        if name == "exams":
            def _boom():
                raise RuntimeError("exams read failed")
            q.execute = _boom  # type: ignore[assignment]
        return q

    sb.table = _table  # type: ignore[assignment]

    try:
        _call_exams(sb)
    except HTTPException as exc:
        assert exc.status_code == 503
        assert exc.detail["code"] == "exams_read_failed"
    else:  # pragma: no cover - the call must raise
        raise AssertionError("a failed exams read must not return 200")


# ── F5 — unchosen optionals must not reach either subject surface ────────


#: A PSIR-only user: both History papers are elective sections they did NOT pick.
_PSIR_SEED_SUBJECTS = [
    {"id": "sub-gs", "name": "General Studies", "slug": "gs", "subject_group": "gs"},
    {"id": "sub-psir", "name": "PSIR", "slug": "psir", "subject_group": "optional"},
    {"id": "sub-hist1", "name": "History Paper-1", "slug": "hist-1", "subject_group": "optional"},
    {"id": "sub-hist2", "name": "History Paper-2", "slug": "hist-2", "subject_group": "optional"},
]


def _elective_seed() -> dict[str, Any]:
    """Coverage carries all four subjects; the user chose only PSIR."""
    today = datetime.now(timezone.utc).date().isoformat()
    return {
        "profiles": [{"id": "u-1", "target_exam": "upsc-cse"}],
        "exams": [{"id": "exam-1", "slug": "upsc-cse", "name": "UPSC CSE",
                   "exam_type": "recruitment", "is_active": True}],
        "subjects": _PSIR_SEED_SUBJECTS,
        "topics": [
            {"id": "t-gs", "name": "Polity", "slug": "polity", "subject_id": "sub-gs", "is_active": True},
            {"id": "t-psir", "name": "Political Theory", "slug": "pt", "subject_id": "sub-psir", "is_active": True},
            {"id": "t-h1", "name": "Ancient India", "slug": "ai", "subject_id": "sub-hist1", "is_active": True},
            {"id": "t-h2", "name": "Modern India", "slug": "mi", "subject_id": "sub-hist2", "is_active": True},
        ],
        # Elective scope keys on exam_phase_sections.exam_phase_id, not on an
        # exam_id — scoping is per phase, so the phase rows are load-bearing.
        "exam_phases": [{"id": "ph-1", "exam_id": "exam-1", "phase_slug": "mains"}],
        "exam_phase_sections": [
            {"id": "sec-gs", "exam_phase_id": "ph-1", "subject_id": "sub-gs",
             "selection_kind": "compulsory", "elective_group": None},
            {"id": "sec-psir", "exam_phase_id": "ph-1", "subject_id": "sub-psir",
             "selection_kind": "elective", "elective_group": "optional"},
            {"id": "sec-h1", "exam_phase_id": "ph-1", "subject_id": "sub-hist1",
             "selection_kind": "elective", "elective_group": "optional"},
            {"id": "sec-h2", "exam_phase_id": "ph-1", "subject_id": "sub-hist2",
             "selection_kind": "elective", "elective_group": "optional"},
        ],
        "user_exam_electives": [
            {"user_id": "u-1", "exam_id": "exam-1", "elective_group": "optional",
             "subject_ids": ["sub-psir"]},
        ],
        "exam_topic_coverage": [
            {"id": "c-gs", "exam_id": "exam-1", "section_id": "sec-gs", "topic_id": "t-gs",
             "reviewer_status": "locked", "exam_priority_score": 90, "is_high_yield": True},
            {"id": "c-psir", "exam_id": "exam-1", "section_id": "sec-psir", "topic_id": "t-psir",
             "reviewer_status": "locked", "exam_priority_score": 80, "is_high_yield": True},
            {"id": "c-h1", "exam_id": "exam-1", "section_id": "sec-h1", "topic_id": "t-h1",
             "reviewer_status": "locked", "exam_priority_score": 70, "is_high_yield": False},
            {"id": "c-h2", "exam_id": "exam-1", "section_id": "sec-h2", "topic_id": "t-h2",
             "reviewer_status": "locked", "exam_priority_score": 60, "is_high_yield": False},
        ],
        # Tasks left over from before the elective choice — the actual source of
        # the fault. Every surface that groups THESE still sees History.
        "study_tasks": [
            {"id": "task-gs", "user_id": "u-1", "plan_id": "plan-1", "subject": "General Studies",
             "subject_id": "sub-gs", "topic_id": "t-gs", "scheduled_date": today,
             "status": "planned", "planned_minutes": 40, "task_type": "concept"},
            {"id": "task-psir", "user_id": "u-1", "plan_id": "plan-1", "subject": "PSIR",
             "subject_id": "sub-psir", "topic_id": "t-psir", "scheduled_date": today,
             "status": "planned", "planned_minutes": 40, "task_type": "concept"},
            {"id": "task-h1", "user_id": "u-1", "plan_id": "plan-1", "subject": "History Paper-1",
             "subject_id": "sub-hist1", "topic_id": "t-h1", "scheduled_date": today,
             "status": "planned", "planned_minutes": 40, "task_type": "concept"},
            {"id": "task-h2", "user_id": "u-1", "plan_id": "plan-1", "subject": "History Paper-2",
             "subject_id": "sub-hist2", "topic_id": "t-h2", "scheduled_date": today,
             "status": "planned", "planned_minutes": 40, "task_type": "concept"},
        ],
        "study_plans": [{"id": "plan-1", "user_id": "u-1", "status": "active",
                         "exam_id": "exam-1", "start_date": today}],
    }


def test_declined_electives_are_the_covered_subjects_outside_the_users_scope():
    sb = SBStub(_elective_seed())
    declined = declined_elective_subject_ids(sb, "u-1", "exam-1")
    assert declined == {"sub-hist1", "sub-hist2"}
    assert "sub-psir" not in declined
    assert "sub-gs" not in declined


def test_a_subject_with_no_locked_coverage_is_not_a_declined_elective():
    """The distinction the first attempt at this fix got wrong.

    A subject that carries tasks but has no locked coverage anywhere is a real
    `trust_status='preview'` / `source='weakness_map'` case the plan-by-subject
    contract has always supported. It is uncovered, not declined, and excluding
    it would delete legitimate rows.
    """
    seed = _elective_seed()
    seed["subjects"].append(
        {"id": "sub-eng", "name": "English", "slug": "eng", "subject_group": "language"}
    )
    sb = SBStub(seed)
    declined = declined_elective_subject_ids(sb, "u-1", "exam-1")
    assert "sub-eng" not in declined
    assert in_scope_subject("sub-eng", declined) is True


def test_scope_unknown_excludes_nothing_rather_than_blanking_the_surface():
    assert declined_elective_subject_ids(SBStub({}), "u-1", None) == set()
    assert declined_elective_subject_ids(SBStub({}), "u-1", "exam-1") == set()
    assert in_scope_subject("sub-hist1", set()) is True
    assert in_scope_subject("sub-hist1", None) is True


def test_unclassified_work_survives_the_scope_filter():
    """A bucket with no subject_id has no identity to test — keep it."""
    assert in_scope_subject(None, {"sub-hist1"}) is True
    assert in_scope_subject("", {"sub-hist1"}) is True
    assert in_scope_subject("sub-psir", {"sub-hist1"}) is True
    assert in_scope_subject("sub-hist1", {"sub-hist1"}) is False


def test_this_week_by_subject_hides_the_unchosen_optionals():
    sb = SBStub(_elective_seed())
    out = plan_by_subject.list_plan_by_subject(sb, "u-1")
    subject_ids = {i["subject_id"] for i in out["items"]}

    assert "sub-hist1" not in subject_ids
    assert "sub-hist2" not in subject_ids
    assert {"sub-gs", "sub-psir"} <= subject_ids


def test_this_week_by_subject_reweights_after_filtering():
    """Weights must be computed over the scope, not over the raw tasks.

    Filtering only the rendered rows would leave every weight computed against a
    total that includes papers the user does not study.
    """
    sb = SBStub(_elective_seed())
    out = plan_by_subject.list_plan_by_subject(sb, "u-1")
    assert out["total_minutes"] == 80  # GS + PSIR only, not all four
    assert sum(i["weight"] for i in out["items"]) == 1.0


def test_subjects_across_the_cycle_hides_the_unchosen_optionals():
    seed = _elective_seed()
    tasks = seed["study_tasks"]
    subjects = plan_timeline._build_subjects(
        tasks, [], {"sub-gs", "sub-psir"},
        declined_subject_ids={"sub-hist1", "sub-hist2"},
    )
    ids = {s["subject_id"] for s in subjects}

    assert "sub-hist1" not in ids
    assert "sub-hist2" not in ids
    assert ids == {"sub-gs", "sub-psir"}


def test_subjects_across_the_cycle_is_unfiltered_when_scope_is_unknown():
    seed = _elective_seed()
    subjects = plan_timeline._build_subjects(
        seed["study_tasks"], [], set(), declined_subject_ids=set()
    )
    assert {s["subject_id"] for s in subjects} == {
        "sub-gs", "sub-psir", "sub-hist1", "sub-hist2",
    }
