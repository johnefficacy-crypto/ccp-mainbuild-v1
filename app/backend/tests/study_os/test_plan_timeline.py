"""Plan Timeline service + API tests."""
from __future__ import annotations

from datetime import date, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import study_os as study_os_api
from app.core.auth import get_current_user
from app.study_os import plan_timeline as service
from tests.persona_questions._stub import SBStub


def _client(sb: SBStub):
    app = FastAPI()
    app.include_router(study_os_api.router, prefix="/api")
    app.dependency_overrides[get_current_user] = lambda: {"id": "u-1"}
    study_os_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    return TestClient(app)


def _exam_seed(*, with_cycle: bool = True, with_exam_start: bool = True):
    today = date.today()
    seed = {
        "profiles": [{"id": "u-1", "target_exam": "ssc-cgl"}],
        "exams": [
            {"id": "exam-1", "slug": "ssc-cgl", "name": "SSC CGL",
             "exam_type": "recruitment", "is_active": True}
        ],
    }
    if with_cycle:
        seed["exam_cycles"] = [{
            "id": "cyc-1",
            "exam_id": "exam-1",
            "cycle_name": "2026",
            "status": "active",
            "notification_date": (today - timedelta(days=30)).isoformat(),
            "application_start": (today - timedelta(days=25)).isoformat(),
            "application_end": (today - timedelta(days=10)).isoformat(),
            "exam_start": (today + timedelta(days=60)).isoformat() if with_exam_start else None,
            "year": 2026,
        }]
        seed["exam_phases"] = [
            {"id": "ph-1", "exam_id": "exam-1", "exam_cycle_id": "cyc-1",
             "phase_name": "Prelims", "phase_slug": "prelims",
             "phase_order": 1, "status": "active"},
            {"id": "ph-2", "exam_id": "exam-1", "exam_cycle_id": "cyc-1",
             "phase_name": "Mains", "phase_slug": "mains",
             "phase_order": 2, "status": "active"},
        ]
    return seed


def _plan_with_tasks(today: date, exam_start: date, *, completed: int, planned: int):
    plan_start = today - timedelta(days=20)
    return {
        "study_plans": [{
            "id": "plan-1",
            "user_id": "u-1",
            "status": "active",
            "start_date": plan_start.isoformat(),
            "end_date": exam_start.isoformat(),
            "created_at": plan_start.isoformat(),
            "updated_at": today.isoformat(),
            "metadata": {},
        }],
        "study_tasks": [
            {
                "id": f"t-{i}",
                "user_id": "u-1",
                "subject": "Polity" if i % 2 == 0 else "English",
                "subject_id": "s1" if i % 2 == 0 else "s2",
                "scheduled_date": (plan_start + timedelta(days=i * 3)).isoformat(),
                "status": "completed" if i < completed else "planned",
                "task_type": "concept",
                "planned_minutes": 60,
                "duration_mins": 60,
            }
            for i in range(planned)
        ],
        "study_sessions": [],
    }


# ── service-level ────────────────────────────────────────────────────────
def test_no_target_exam_returns_safe_fallback():
    sb = SBStub({"profiles": [{"id": "u-1", "target_exam": None}]})
    out = service.get_plan_timeline(sb, "u-1")
    assert out["cycle_progress"]["status"] == "not_connected"
    assert out["exam_context"]["exam_id"] is None
    assert out["milestones"] == []
    # The "no_exam_date" risk flag is present so the UI can surface it.
    codes = [r["code"] for r in out["risk_flags"]]
    assert "no_exam_date" in codes


def test_no_exam_date_returns_safe_fallback_with_context():
    seed = _exam_seed(with_cycle=True, with_exam_start=False)
    sb = SBStub(seed)
    out = service.get_plan_timeline(sb, "u-1")
    assert out["cycle_progress"]["status"] == "not_connected"
    assert out["exam_context"]["exam_id"] == "exam-1"
    assert out["exam_context"]["exam_start"] is None


def test_active_plan_with_tasks_returns_progress_and_series():
    today = date.today()
    exam_start = today + timedelta(days=60)
    seed = _exam_seed()
    seed.update(_plan_with_tasks(today, exam_start, completed=2, planned=6))
    sb = SBStub(seed)
    out = service.get_plan_timeline(sb, "u-1")
    assert out["exam_context"]["exam_id"] == "exam-1"
    assert out["exam_context"]["days_remaining"] == 60
    # 2/6 completed → 33%.
    assert out["cycle_progress"]["actual_progress_pct"] == 33
    assert isinstance(out["series"], list) and len(out["series"]) >= 2
    # Series is monotonically non-decreasing on planned_pct.
    plans = [p["planned_pct"] for p in out["series"]]
    assert plans == sorted(plans)
    # Phase bands are derived from cycle bounds.
    assert len(out["phase_bands"]) == 5
    assert {b["name"] for b in out["phase_bands"]} == {
        "Foundation", "Coverage", "Revision", "Mock-intensive", "Final sprint"
    }


def test_subject_progress_aggregates_planned_and_actual():
    today = date.today()
    exam_start = today + timedelta(days=60)
    seed = _exam_seed()
    seed.update(_plan_with_tasks(today, exam_start, completed=3, planned=6))
    sb = SBStub(seed)
    out = service.get_plan_timeline(sb, "u-1")
    subjects = {s["subject_name"]: s for s in out["subjects"]}
    assert "Polity" in subjects and "English" in subjects
    # 6 tasks alternate subjects → 3 each; 3 of 6 completed by index → 2
    # Polity and 1 English completed.
    assert subjects["Polity"]["completed_tasks"] == 2
    assert subjects["English"]["completed_tasks"] == 1


def test_behind_plan_risk_flag_when_actual_trails_planned():
    today = date.today()
    exam_start = today + timedelta(days=60)
    seed = _exam_seed()
    # 6 planned tasks, none completed → planned_so_far should be > 0 (some
    # scheduled in the past) while actual is 0 → behind_plan.
    seed.update(_plan_with_tasks(today, exam_start, completed=0, planned=6))
    sb = SBStub(seed)
    out = service.get_plan_timeline(sb, "u-1")
    codes = {r["code"] for r in out["risk_flags"]}
    # behind_plan only triggers when the gap is >= 10 percentage points.
    assert ("behind_plan" in codes) or (out["cycle_progress"]["gap_pct"] < 10)
    assert out["cycle_progress"]["status"] in {"behind", "on_track"}


def test_safe_fallback_on_supabase_exception():
    class Broken:
        def table(self, *a, **k):
            raise RuntimeError("supabase exploded")

    out = service.get_plan_timeline(Broken(), "u-1")
    assert out["cycle_progress"]["status"] == "not_connected"
    assert out["exam_context"]["exam_id"] is None


def test_milestones_include_today_and_exam_day():
    today = date.today()
    exam_start = today + timedelta(days=60)
    seed = _exam_seed()
    seed.update(_plan_with_tasks(today, exam_start, completed=1, planned=4))
    sb = SBStub(seed)
    out = service.get_plan_timeline(sb, "u-1")
    kinds = [m["kind"] for m in out["milestones"]]
    assert "today" in kinds
    assert "exam" in kinds
    assert "phase" in kinds


def test_milestones_phase_date_none_without_structured():
    """Phases without phase_start produce date=None, status='preview'."""
    today = date.today()
    exam_start = today + timedelta(days=60)
    seed = _exam_seed()
    seed.update(_plan_with_tasks(today, exam_start, completed=1, planned=4))
    sb = SBStub(seed)
    out = service.get_plan_timeline(sb, "u-1")
    phase_ms = [m for m in out["milestones"] if m["kind"] == "phase"]
    assert len(phase_ms) == 2
    assert all(m["date"] is None for m in phase_ms)
    assert all(m["status"] == "preview" for m in phase_ms)


def test_milestones_use_phase_start_when_structured():
    """phase_start populates the milestone date and correct past/upcoming status."""
    today = date.today()
    exam_start = today + timedelta(days=60)
    seed = _exam_seed()
    prelims_start = (today + timedelta(days=10)).isoformat()
    seed["exam_phases"][0]["phase_start"] = prelims_start
    seed.update(_plan_with_tasks(today, exam_start, completed=1, planned=4))
    sb = SBStub(seed)
    out = service.get_plan_timeline(sb, "u-1")
    phase_ms = {m["phase_slug"]: m for m in out["milestones"] if m["kind"] == "phase"}
    assert phase_ms["prelims"]["date"] == prelims_start
    assert phase_ms["prelims"]["status"] == "upcoming"
    # Phase without phase_start still gets date=None.
    assert phase_ms["mains"]["date"] is None
    assert phase_ms["mains"]["status"] == "preview"


def test_milestones_phase_start_past_status():
    """phase_start in the past produces status='past'."""
    today = date.today()
    exam_start = today + timedelta(days=60)
    seed = _exam_seed()
    seed["exam_phases"][0]["phase_start"] = (today - timedelta(days=5)).isoformat()
    seed.update(_plan_with_tasks(today, exam_start, completed=1, planned=4))
    sb = SBStub(seed)
    out = service.get_plan_timeline(sb, "u-1")
    phase_ms = {m["phase_slug"]: m for m in out["milestones"] if m["kind"] == "phase"}
    assert phase_ms["prelims"]["status"] == "past"


# ── API-level ────────────────────────────────────────────────────────────
def test_api_returns_full_envelope():
    today = date.today()
    exam_start = today + timedelta(days=60)
    seed = _exam_seed()
    seed.update(_plan_with_tasks(today, exam_start, completed=2, planned=4))
    sb = SBStub(seed)
    body = _client(sb).get("/api/study/plan/timeline").json()
    for key in (
        "exam_context",
        "plan_context",
        "cycle_progress",
        "milestones",
        "phase_bands",
        "series",
        "subjects",
        "risk_flags",
    ):
        assert key in body, f"missing {key} in plan timeline payload"
    assert body["plan_context"]["planner_version"] == "planner_v1"


def test_api_safe_fallback_when_user_has_no_exam():
    sb = SBStub({"profiles": [{"id": "u-1", "target_exam": None}]})
    body = _client(sb).get("/api/study/plan/timeline").json()
    assert body["cycle_progress"]["status"] == "not_connected"


# ── resolver wiring tests ────────────────────────────────────────────────


def test_tw1_past_exam_start_but_future_phase_connected():
    """Cycle exam_start in the past + cycle-bound Mains with future phase_start
    → connected via next_future_phase; target_date = phase_start; exam_start still present."""
    today = date.today()
    past_exam_start = (today - timedelta(days=5)).isoformat()
    future_phase_start = (today + timedelta(days=30)).isoformat()
    seed = {
        "profiles": [{"id": "u-1", "target_exam": "ssc-cgl"}],
        "exams": [{"id": "exam-1", "slug": "ssc-cgl", "name": "SSC CGL",
                   "exam_type": "recruitment", "is_active": True}],
        "exam_cycles": [{"id": "cyc-1", "exam_id": "exam-1", "cycle_name": "2026",
                         "status": "active", "exam_start": past_exam_start, "year": 2026}],
        "exam_phases": [{"id": "ph-mains", "exam_id": "exam-1", "exam_cycle_id": "cyc-1",
                         "phase_name": "Mains", "phase_slug": "mains", "phase_order": 2,
                         "status": "expected", "phase_start": future_phase_start, "phase_end": None}],
    }
    out = service.get_plan_timeline(SBStub(seed), "u-1")
    ec = out["exam_context"]
    # Resolver says connected → cycle_progress is on_track (no tasks = 0 gap, not behind)
    assert out["cycle_progress"]["status"] != "not_connected"
    assert ec["target_kind"] == "phase"
    assert ec["target_date"] == future_phase_start
    assert ec["target_phase_slug"] == "mains"
    # days_remaining > 0 — counting to phase_start
    assert ec["days_remaining"] == (date.fromisoformat(future_phase_start) - today).days
    # compat alias still present
    assert "exam_start" in ec


def test_tw2_no_target_exam_not_connected_no_crash():
    """User with no target exam → not_connected, no crash, new keys present with None."""
    sb = SBStub({"profiles": [{"id": "u-1", "target_exam": None}]})
    out = service.get_plan_timeline(sb, "u-1")
    assert out["cycle_progress"]["status"] == "not_connected"
    ec = out["exam_context"]
    for key in ("target_date", "target_kind", "target_phase_id", "target_phase_slug",
                "target_phase_name", "diagnostic"):
        assert key in ec, f"exam_context missing {key}"
        assert ec[key] is None


def test_tw3_resolver_not_connected_exam_start_still_surfaced():
    """Resolver not_connected (past exam_start, no future phase) → not_connected status;
    exam_start compat alias still populated."""
    today = date.today()
    past = (today - timedelta(days=10)).isoformat()
    seed = {
        "profiles": [{"id": "u-1", "target_exam": "ssc-cgl"}],
        "exams": [{"id": "exam-1", "slug": "ssc-cgl", "name": "SSC CGL",
                   "exam_type": "recruitment", "is_active": True}],
        "exam_cycles": [{"id": "cyc-1", "exam_id": "exam-1", "cycle_name": "2026",
                         "status": "active", "exam_start": past, "year": 2026}],
        "exam_phases": [],
    }
    seed.update(_plan_with_tasks(today, today + timedelta(days=30), completed=1, planned=3))
    out = service.get_plan_timeline(SBStub(seed), "u-1")
    ec = out["exam_context"]
    assert out["cycle_progress"]["status"] == "not_connected"
    # compat alias still surfaced from cycle
    assert "exam_start" in ec
    assert ec["target_date"] is None


def test_tw4_current_active_phase_target_date():
    """Current active phase → target_date = phase_end; null phase_end → target_date null."""
    today = date.today()
    phase_end = (today + timedelta(days=20)).isoformat()
    seed = {
        "profiles": [{"id": "u-1", "target_exam": "ssc-cgl"}],
        "exams": [{"id": "exam-1", "slug": "ssc-cgl", "name": "SSC CGL",
                   "exam_type": "recruitment", "is_active": True}],
        "exam_cycles": [{"id": "cyc-1", "exam_id": "exam-1", "cycle_name": "2026",
                         "status": "active", "exam_start": (today + timedelta(days=60)).isoformat(),
                         "year": 2026}],
        "exam_phases": [{"id": "ph-pre", "exam_id": "exam-1", "exam_cycle_id": "cyc-1",
                         "phase_name": "Prelims", "phase_slug": "prelims", "phase_order": 1,
                         "status": "active",
                         "phase_start": (today - timedelta(days=5)).isoformat(),
                         "phase_end": phase_end}],
    }
    seed.update(_plan_with_tasks(today, today + timedelta(days=60), completed=1, planned=3))
    out = service.get_plan_timeline(SBStub(seed), "u-1")
    ec = out["exam_context"]
    assert ec["target_kind"] == "phase"
    assert ec["target_date"] == phase_end
    assert ec["days_remaining"] == (date.fromisoformat(phase_end) - today).days

    # Null phase_end → target_date null, days_remaining null
    seed["exam_phases"][0]["phase_end"] = None
    out2 = service.get_plan_timeline(SBStub(seed), "u-1")
    ec2 = out2["exam_context"]
    assert ec2["target_date"] is None
    assert ec2["days_remaining"] is None


def test_tw5_diagnostic_surfaced_in_exam_context():
    """generic_templates_available_but_unattached diagnostic reaches exam_context."""
    today = date.today()
    seed = {
        "profiles": [{"id": "u-1", "target_exam": "ssc-cgl"}],
        "exams": [{"id": "exam-1", "slug": "ssc-cgl", "name": "SSC CGL",
                   "exam_type": "recruitment", "is_active": True}],
        "exam_cycles": [{"id": "cyc-1", "exam_id": "exam-1", "cycle_name": "2026",
                         "status": "active", "exam_start": (today - timedelta(days=5)).isoformat(),
                         "year": 2026}],
        # exam_cycle_id=None → template phase, unattached
        "exam_phases": [{"id": "ph-tmpl", "exam_id": "exam-1", "exam_cycle_id": None,
                         "phase_name": "Prelims", "phase_slug": "prelims", "phase_order": 1,
                         "status": "active", "phase_start": None, "phase_end": None}],
    }
    out = service.get_plan_timeline(SBStub(seed), "u-1")
    diagnostic = out["exam_context"].get("diagnostic") or []
    assert "generic_templates_available_but_unattached" in diagnostic


def test_tw6_contract_guard_no_existing_keys_dropped():
    """Every key present in a connected-exam response before wiring is still present after."""
    today = date.today()
    exam_start = today + timedelta(days=60)
    seed = _exam_seed()
    seed.update(_plan_with_tasks(today, exam_start, completed=2, planned=4))
    out = service.get_plan_timeline(SBStub(seed), "u-1")

    # Top-level keys
    for key in ("exam_context", "plan_context", "cycle_progress", "milestones",
                "phase_bands", "series", "subjects", "risk_flags", "regen_triggers"):
        assert key in out, f"top-level key dropped: {key}"

    # exam_context keys — original set must all be present
    ec = out["exam_context"]
    for key in ("exam_id", "exam_name", "cycle", "phase", "exam_start",
                "days_remaining", "trust_status"):
        assert key in ec, f"exam_context key dropped: {key}"

    # New resolver keys also present
    for key in ("target_date", "target_kind", "target_phase_id",
                "target_phase_slug", "target_phase_name", "diagnostic"):
        assert key in ec, f"exam_context missing new resolver key: {key}"

    # plan_context keys
    pc = out["plan_context"]
    for key in ("plan_id", "plan_version", "created_at", "last_adapted_at", "planner_version"):
        assert key in pc, f"plan_context key dropped: {key}"

    # cycle_progress keys
    cp = out["cycle_progress"]
    for key in ("total_days", "elapsed_days", "planned_progress_pct",
                "actual_progress_pct", "gap_pct", "status", "unit"):
        assert key in cp, f"cycle_progress key dropped: {key}"


# ── single-source-of-truth integration tests ─────────────────────────────


def test_v2_1_series_and_phase_bands_use_timeline_target_date():
    """series and phase_bands are built from timeline_target_date (a future phase start),
    not from the raw cycle exam_start which may be in the past."""
    today = date.today()
    past_exam_start = (today - timedelta(days=10)).isoformat()
    future_phase_start = (today + timedelta(days=40)).isoformat()
    seed = {
        "profiles": [{"id": "u-1", "target_exam": "ssc-cgl"}],
        "exams": [{"id": "exam-1", "slug": "ssc-cgl", "name": "SSC CGL",
                   "exam_type": "recruitment", "is_active": True}],
        "exam_cycles": [{"id": "cyc-1", "exam_id": "exam-1", "cycle_name": "2026",
                         "status": "active", "exam_start": past_exam_start, "year": 2026}],
        "exam_phases": [{"id": "ph-mains", "exam_id": "exam-1", "exam_cycle_id": "cyc-1",
                         "phase_name": "Mains", "phase_slug": "mains", "phase_order": 2,
                         "status": "expected", "phase_start": future_phase_start, "phase_end": None}],
    }
    seed.update(_plan_with_tasks(today, today + timedelta(days=40), completed=1, planned=4))
    out = service.get_plan_timeline(SBStub(seed), "u-1")
    # series is non-empty — proves cycle_end used future phase_start, not past exam_start
    assert len(out["series"]) >= 1
    # phase_bands are populated — proves _build_phase_bands got a future target, not past
    assert len(out["phase_bands"]) == 5
    # target_date is the phase start, not the past exam_start
    assert out["exam_context"]["target_date"] == future_phase_start


def test_v2_2_cycle_loaded_from_resolver_cycle_id():
    """Cycle name in exam_context comes from the resolver's chosen cycle, not _load_active_cycle."""
    today = date.today()
    seed = {
        "profiles": [{"id": "u-1", "target_exam": "ssc-cgl"}],
        "exams": [{"id": "exam-1", "slug": "ssc-cgl", "name": "SSC CGL",
                   "exam_type": "recruitment", "is_active": True}],
        "exam_cycles": [
            {"id": "cyc-old", "exam_id": "exam-1", "cycle_name": "2025 Cycle",
             "status": "completed", "exam_start": (today - timedelta(days=365)).isoformat(), "year": 2025},
            {"id": "cyc-new", "exam_id": "exam-1", "cycle_name": "2026 Cycle",
             "status": "active", "exam_start": (today + timedelta(days=90)).isoformat(), "year": 2026},
        ],
        "exam_phases": [],
    }
    seed.update(_plan_with_tasks(today, today + timedelta(days=90), completed=0, planned=2))
    out = service.get_plan_timeline(SBStub(seed), "u-1")
    # Active cycle wins in the resolver → cycle name should be the 2026 one
    assert out["exam_context"]["cycle"] == "2026 Cycle"


def test_v2_3_exam_start_in_exam_context_equals_target_date():
    """exam_context.exam_start is now the resolver target_date, not raw cycle exam_start."""
    today = date.today()
    future_phase_start = (today + timedelta(days=30)).isoformat()
    past_raw_exam_start = (today - timedelta(days=5)).isoformat()
    seed = {
        "profiles": [{"id": "u-1", "target_exam": "ssc-cgl"}],
        "exams": [{"id": "exam-1", "slug": "ssc-cgl", "name": "SSC CGL",
                   "exam_type": "recruitment", "is_active": True}],
        "exam_cycles": [{"id": "cyc-1", "exam_id": "exam-1", "cycle_name": "2026",
                         "status": "active", "exam_start": past_raw_exam_start, "year": 2026}],
        "exam_phases": [{"id": "ph-mains", "exam_id": "exam-1", "exam_cycle_id": "cyc-1",
                         "phase_name": "Mains", "phase_slug": "mains", "phase_order": 2,
                         "status": "expected", "phase_start": future_phase_start, "phase_end": None}],
    }
    seed.update(_plan_with_tasks(today, today + timedelta(days=30), completed=0, planned=2))
    out = service.get_plan_timeline(SBStub(seed), "u-1")
    ec = out["exam_context"]
    # exam_start = target_date (phase start), not the raw past exam_start
    assert ec["exam_start"] == future_phase_start
    assert ec["exam_start"] != past_raw_exam_start
    # null when resolver has no target
    seed2 = {
        "profiles": [{"id": "u-1", "target_exam": "ssc-cgl"}],
        "exams": [{"id": "exam-1", "slug": "ssc-cgl", "name": "SSC CGL",
                   "exam_type": "recruitment", "is_active": True}],
        "exam_cycles": [{"id": "cyc-1", "exam_id": "exam-1", "cycle_name": "2026",
                         "status": "active", "exam_start": past_raw_exam_start, "year": 2026}],
        "exam_phases": [],
    }
    seed2.update(_plan_with_tasks(today, today + timedelta(days=30), completed=0, planned=2))
    out2 = service.get_plan_timeline(SBStub(seed2), "u-1")
    assert out2["exam_context"]["exam_start"] is None


def test_v2_4_no_exam_date_flag_keyed_off_resolver_not_raw_exam_start():
    """no_exam_date risk flag fires when resolver is not_connected, not when exam_start is None.
    Inverse: resolver connected via a future phase → no no_exam_date, even if exam_start is past."""
    today = date.today()
    past_raw = (today - timedelta(days=5)).isoformat()
    future_phase = (today + timedelta(days=30)).isoformat()
    seed = {
        "profiles": [{"id": "u-1", "target_exam": "ssc-cgl"}],
        "exams": [{"id": "exam-1", "slug": "ssc-cgl", "name": "SSC CGL",
                   "exam_type": "recruitment", "is_active": True}],
        "exam_cycles": [{"id": "cyc-1", "exam_id": "exam-1", "cycle_name": "2026",
                         "status": "active", "exam_start": past_raw, "year": 2026}],
        "exam_phases": [{"id": "ph-mains", "exam_id": "exam-1", "exam_cycle_id": "cyc-1",
                         "phase_name": "Mains", "phase_slug": "mains", "phase_order": 2,
                         "status": "expected", "phase_start": future_phase, "phase_end": None}],
    }
    seed.update(_plan_with_tasks(today, today + timedelta(days=30), completed=1, planned=3))
    out = service.get_plan_timeline(SBStub(seed), "u-1")
    # Resolver is connected via next_future_phase → no no_exam_date flag
    flag_codes = {r["code"] for r in out["risk_flags"]}
    assert "no_exam_date" not in flag_codes
    assert out["cycle_progress"]["status"] != "not_connected"


def test_v2_5_not_connected_fires_no_exam_date_flag():
    """When resolver is not_connected (no future phase, past exam_start), no_exam_date fires."""
    today = date.today()
    past_raw = (today - timedelta(days=5)).isoformat()
    seed = {
        "profiles": [{"id": "u-1", "target_exam": "ssc-cgl"}],
        "exams": [{"id": "exam-1", "slug": "ssc-cgl", "name": "SSC CGL",
                   "exam_type": "recruitment", "is_active": True}],
        "exam_cycles": [{"id": "cyc-1", "exam_id": "exam-1", "cycle_name": "2026",
                         "status": "active", "exam_start": past_raw, "year": 2026}],
        "exam_phases": [],
    }
    seed.update(_plan_with_tasks(today, today + timedelta(days=30), completed=1, planned=3))
    out = service.get_plan_timeline(SBStub(seed), "u-1")
    flag_codes = {r["code"] for r in out["risk_flags"]}
    assert "no_exam_date" in flag_codes
    assert out["cycle_progress"]["status"] == "not_connected"
