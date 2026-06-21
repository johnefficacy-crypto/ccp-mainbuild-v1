"""Tests for management read-model endpoints (Phase 0 — backend prerequisite).

Covers: list pagination and filters, current-cycle selection, per-area deep-link
CTAs, 404 semantics, fail-closed reads, select_current_cycle pure function.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intelligence as admin_api
from app.core.auth import get_current_user
from app.core.errors import DatabaseError
from app.exam_intelligence import work_queue as _wq
from tests.persona_questions._stub import SBStub

_RECENT = "2026-06-16T00:00:00+00:00"


def _build_app(sb, role="super_admin"):
    app = FastAPI()
    app.include_router(admin_api.router, prefix="/api")
    admin_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    user = {
        "id": "admin-1",
        "role": role,
        "permissions": ["exam_intelligence.review"] if role == "admin" else [],
    }
    app.dependency_overrides[get_current_user] = lambda: user
    return app


class _Seed:
    def __init__(self):
        self.db: dict = {t: [] for t in (
            "exams", "exam_phases", "exam_topic_coverage", "syllabus_topic_mentions",
            "exam_policy_updates", "pyq_papers", "pyq_questions",
            "pyq_question_topic_tags", "pyq_options", "organizations", "exam_families",
            "exam_cycles",
        )}

    def exam(self, eid, *, name, mode="core", phases=1, locked=1, vpyq=0,
             org=None, family=None, active=True):
        self.db["exams"].append({
            "id": eid, "slug": eid, "name": name, "exam_type": "recruitment",
            "is_active": active, "exam_family_id": family,
            "management_mode": mode, "cadence": "annual",
            "conducting_organization_id": org,
        })
        for i in range(phases):
            self.db["exam_phases"].append({"id": f"{eid}-ph{i}", "exam_id": eid})
        for i in range(locked):
            self.db["exam_topic_coverage"].append({
                "id": f"{eid}-cl{i}", "exam_id": eid,
                "reviewer_status": "locked", "created_at": _RECENT,
            })
        if vpyq:
            self.db["pyq_papers"].append(
                {"id": f"{eid}-pp", "exam_id": eid, "trust_status": "verified"})
            for i in range(vpyq):
                qid = f"{eid}-vq{i}"
                self.db["pyq_questions"].append({
                    "id": qid, "pyq_paper_id": f"{eid}-pp",
                    "reviewer_status": "verified", "created_at": _RECENT,
                })
                self.db["pyq_question_topic_tags"].append({
                    "id": f"{qid}-t", "question_id": qid,
                    "reviewer_status": "verified", "created_at": _RECENT,
                })
        return self

    def cycle(self, cid, exam_id, *, name="Cycle", year=2026, status="active"):
        self.db["exam_cycles"].append({
            "id": cid, "exam_id": exam_id, "cycle_name": name,  # real DB column
            "year": year, "status": status, "created_at": _RECENT,
        })
        return self

    def phase(self, pid, exam_id, cycle_id, *, name="Phase", slug="phase", order=1,
              start=None, end=None, status=None):
        self.db["exam_phases"].append({
            "id": pid, "exam_id": exam_id, "exam_cycle_id": cycle_id,
            "phase_name": name, "phase_slug": slug, "phase_order": order,  # real DB columns
            "phase_start": start, "phase_end": end, "status": status,
        })
        return self

    def org(self, oid, name):
        self.db["organizations"].append({"id": oid, "name": name})
        return self

    def family(self, fid, name):
        self.db["exam_families"].append({"id": fid, "name": name})
        return self


def _basic_seed():
    s = _Seed()
    s.org("org1", "UPSC")
    s.family("fam1", "Civil Services")
    s.exam("rdy", name="Ready Exam", locked=1, vpyq=1, org="org1", family="fam1")
    s.exam("blk", name="Blocked Exam", phases=0, locked=0)
    s.exam("na", name="Needs Action", locked=1, vpyq=0)
    s.cycle("cy1", "rdy", name="2026 Cycle", year=2026, status="active")
    s.phase("ph1", "rdy", "cy1", name="Prelims", slug="prelims", order=1)
    return s.db


def _client(role="super_admin", db=None):
    sb = SBStub(db if db is not None else _basic_seed())
    return TestClient(_build_app(sb, role=role)), sb


# ── select_current_cycle — pure function tests ───────────────────────────────

def test_select_current_cycle_active_wins():
    cycles = [
        {"id": "b", "status": "open", "year": 2026},
        {"id": "a", "status": "active", "year": 2025},
        {"id": "c", "status": "expected", "year": 2027},
    ]
    assert _wq.select_current_cycle(cycles)["id"] == "a"


def test_select_current_cycle_open_beats_expected():
    cycles = [
        {"id": "b", "status": "expected", "year": 2027},
        {"id": "a", "status": "open", "year": 2026},
    ]
    assert _wq.select_current_cycle(cycles)["id"] == "a"


def test_select_current_cycle_highest_year_fallback():
    cycles = [
        {"id": "a", "status": "closed", "year": 2024},
        {"id": "b", "status": "closed", "year": 2026},
        {"id": "c", "status": "closed", "year": 2025},
    ]
    assert _wq.select_current_cycle(cycles)["id"] == "b"


def test_select_current_cycle_uuid_tiebreaker():
    """When year is equal and no active/open/expected, lowest UUID wins."""
    cycles = [
        {"id": "z-uuid", "status": "closed", "year": 2026},
        {"id": "a-uuid", "status": "closed", "year": 2026},
    ]
    assert _wq.select_current_cycle(cycles)["id"] == "a-uuid"


def test_select_current_cycle_empty_returns_none():
    assert _wq.select_current_cycle([]) is None


def test_select_current_cycle_none_status_is_low_priority():
    cycles = [
        {"id": "b", "status": None, "year": 2027},
        {"id": "a", "status": "expected", "year": 2026},
    ]
    assert _wq.select_current_cycle(cycles)["id"] == "a"


# ── Management list endpoint ─────────────────────────────────────────────────

def test_management_list_requires_permission():
    client, _ = _client(role="user")
    r = client.get("/api/admin/exam-intelligence/management/exams")
    assert r.status_code == 403


def test_management_list_paginated_shape():
    client, _ = _client()
    r = client.get("/api/admin/exam-intelligence/management/exams?active_state=all")
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert "total_count" in body
    assert "limit" in body
    assert "offset" in body
    assert "has_next" in body


def test_management_list_returns_exam_fields():
    client, _ = _client()
    r = client.get("/api/admin/exam-intelligence/management/exams?active_state=all")
    body = r.json()
    assert body["total_count"] >= 1
    item = next(i for i in body["items"] if i["id"] == "rdy")
    assert item["name"] == "Ready Exam"
    assert item["organization_name"] == "UPSC"
    assert item["family_name"] == "Civil Services"
    assert item["status"] in {"blocked", "needs_action", "ready"}
    assert "blocker_count" in item
    assert "flags" in item
    assert "readiness_summary" in item


def test_management_list_workflow_filter_blocked():
    client, _ = _client()
    r = client.get("/api/admin/exam-intelligence/management/exams?active_state=all&workflow=blocked")
    body = r.json()
    assert all(i["status"] == "blocked" for i in body["items"])
    assert any(i["id"] == "blk" for i in body["items"])
    assert all(i["id"] != "rdy" for i in body["items"])


def test_management_list_workflow_filter_ready():
    client, _ = _client()
    r = client.get("/api/admin/exam-intelligence/management/exams?active_state=all&workflow=ready")
    body = r.json()
    assert all(i["status"] == "ready" for i in body["items"])
    assert any(i["id"] == "rdy" for i in body["items"])


def test_management_list_includes_current_cycle():
    client, _ = _client()
    r = client.get("/api/admin/exam-intelligence/management/exams?active_state=all")
    body = r.json()
    rdy = next(i for i in body["items"] if i["id"] == "rdy")
    # rdy has an active cycle
    assert rdy["current_cycle"] is not None
    assert rdy["current_cycle"]["id"] == "cy1"
    assert rdy["current_cycle"]["year"] == 2026


def test_management_list_current_cycle_has_phases():
    client, _ = _client()
    r = client.get("/api/admin/exam-intelligence/management/exams?active_state=all")
    body = r.json()
    rdy = next(i for i in body["items"] if i["id"] == "rdy")
    phases = rdy["current_cycle"]["phases"]
    assert len(phases) >= 1
    ph = phases[0]
    assert ph["label"] == "Prelims"
    assert ph["slug"] == "prelims"


def test_management_list_no_cycle_exam_has_null_current_cycle():
    client, _ = _client()
    r = client.get("/api/admin/exam-intelligence/management/exams?active_state=all")
    body = r.json()
    blk = next(i for i in body["items"] if i["id"] == "blk")
    assert blk["current_cycle"] is None


def test_management_list_active_cycle_beats_open():
    s = _Seed()
    s.exam("ex1", name="Exam1", locked=1, vpyq=1)
    s.db["exam_cycles"].extend([
        {"id": "c-open", "exam_id": "ex1", "cycle_name": "Open", "year": 2026,
         "status": "open", "created_at": _RECENT},
        {"id": "c-active", "exam_id": "ex1", "cycle_name": "Active", "year": 2025,
         "status": "active", "created_at": _RECENT},
    ])
    sb = SBStub(s.db)
    client = TestClient(_build_app(sb))
    r = client.get("/api/admin/exam-intelligence/management/exams?active_state=all")
    body = r.json()
    ex1 = next(i for i in body["items"] if i["id"] == "ex1")
    assert ex1["current_cycle"]["id"] == "c-active"  # active wins over open


def test_management_list_pagination():
    s = _Seed()
    for i in range(5):
        s.exam(f"e{i}", name=f"Exam {i}", locked=1)
    sb = SBStub(s.db)
    client = TestClient(_build_app(sb))
    r = client.get("/api/admin/exam-intelligence/management/exams?active_state=all&limit=2&offset=0")
    body = r.json()
    assert len(body["items"]) == 2
    assert body["total_count"] == 5
    assert body["has_next"] is True


# ── Management detail endpoint ───────────────────────────────────────────────

def _detail(client, eid, **params):
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"/api/admin/exam-intelligence/management/exams/{eid}"
    if qs:
        url += f"?{qs}"
    return client.get(url)


def test_management_detail_404_unknown_exam():
    client, _ = _client()
    assert _detail(client, "ghost").status_code == 404


def test_management_detail_returns_fields():
    client, _ = _client()
    r = _detail(client, "rdy")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "rdy"
    assert body["name"] == "Ready Exam"
    assert body["organization_name"] == "UPSC"
    assert body["family_name"] == "Civil Services"
    assert body["status"] in {"blocked", "needs_action", "ready"}
    assert "flags" in body
    assert "blocker_count" in body
    assert "action_queue" in body
    assert "activation_verdict" in body
    assert "activation_checks" in body
    assert "stages" in body


def test_management_detail_includes_all_cycles():
    s = _Seed()
    s.exam("ex", name="Exam", locked=1, vpyq=1)
    s.db["exam_cycles"].extend([
        {"id": "c1", "exam_id": "ex", "cycle_name": "2024", "year": 2024,
         "status": "closed", "created_at": _RECENT},
        {"id": "c2", "exam_id": "ex", "cycle_name": "2026", "year": 2026,
         "status": "active", "created_at": _RECENT},
    ])
    sb = SBStub(s.db)
    client = TestClient(_build_app(sb))
    r = _detail(client, "ex")
    body = r.json()
    assert len(body["cycles"]) == 2
    cycle_ids = {c["id"] for c in body["cycles"]}
    assert cycle_ids == {"c1", "c2"}


def test_management_detail_current_cycle_is_active():
    client, _ = _client()
    body = _detail(client, "rdy").json()
    assert body["current_cycle"]["id"] == "cy1"


def test_management_detail_explicit_cycle_id():
    s = _Seed()
    s.exam("ex", name="Exam", locked=1, vpyq=1)
    s.db["exam_cycles"].extend([
        {"id": "c1", "exam_id": "ex", "cycle_name": "2024", "year": 2024,
         "status": "closed", "created_at": _RECENT},
        {"id": "c2", "exam_id": "ex", "cycle_name": "2026", "year": 2026,
         "status": "active", "created_at": _RECENT},
    ])
    sb = SBStub(s.db)
    client = TestClient(_build_app(sb))
    # Requesting c1 explicitly overrides the active-cycle selection
    body = client.get(
        "/api/admin/exam-intelligence/management/exams/ex?cycle_id=c1"
    ).json()
    assert body["current_cycle"]["id"] == "c1"


def test_management_detail_404_for_unknown_cycle():
    client, _ = _client()
    r = _detail(client, "rdy", cycle_id="ghost-cycle")
    assert r.status_code == 404


def test_management_detail_action_queue_has_tab_deep_links():
    """All action queue CTAs must deep-link to /exams/:id?tab=<area>."""
    client, _ = _client()
    body = _detail(client, "blk").json()  # blk is blocked: many actions
    assert len(body["action_queue"]) > 0
    for item in body["action_queue"]:
        assert item["cta_route"].startswith("/admin/exam-intelligence/exams/blk"), item
        assert "tab=" in item["cta_route"], item


def test_management_detail_action_queue_no_generic_label():
    client, _ = _client()
    body = _detail(client, "blk").json()
    for item in body["action_queue"]:
        assert item["cta_label"] != "Open workspace", item["area"]


def test_management_detail_section_readiness_advisory_null_on_failure():
    """section_readiness is advisory: a read failure yields null, not 5xx."""
    from app.exam_intelligence import management_read_model as _mrm

    # Patch compute_exam_workspace_readiness to raise
    import app.exam_intelligence.management_read_model as _mrm_module

    def _fail(*args, **kwargs):
        raise RuntimeError("simulated advisory failure")

    original = _mrm_module.compute_exam_workspace_readiness
    _mrm_module.compute_exam_workspace_readiness = _fail
    try:
        client, _ = _client()
        r = _detail(client, "rdy")
        assert r.status_code == 200
        assert r.json()["section_readiness"] is None
    finally:
        _mrm_module.compute_exam_workspace_readiness = original


def test_management_detail_fail_closed_on_exam_read_failure():
    """A failed exam read must return 5xx (never a fabricated 404 or 200)."""
    from tests.exam_intelligence.test_console_detail_api import FailingSBStub

    sb = FailingSBStub(_basic_seed(), "exams")
    client = TestClient(_build_app(sb), raise_server_exceptions=False)
    r = client.get("/api/admin/exam-intelligence/management/exams/rdy")
    assert r.status_code == 500


def test_management_detail_status_parity_with_list():
    """management detail status must match management list status for same exam."""
    client, _ = _client()
    list_r = client.get(
        "/api/admin/exam-intelligence/management/exams?active_state=all"
    ).json()
    list_status = {row["id"]: row["status"] for row in list_r["items"]}
    for eid in ["rdy", "blk", "na"]:
        detail_r = _detail(client, eid).json()
        assert detail_r["status"] == list_status[eid], eid
        assert detail_r["activation_verdict"]["status"] == list_status[eid], eid


# ── Schema-column regression tests ──────────────────────────────────────────
# These tests exist to prevent stub tests from passing while production
# PostgREST returns a 42703 (column not found) error due to wrong column names
# in the SELECT string.

def test_cycle_cols_use_real_db_column_names():
    """_CYCLE_COLS must contain cycle_name, not the API-normalized 'name' column."""
    from app.exam_intelligence.management_read_model import _CYCLE_COLS, _PHASE_COLS
    assert "cycle_name" in _CYCLE_COLS, "_CYCLE_COLS must select cycle_name (real DB col)"
    # Ensure we haven't accidentally left the wrong column name
    col_names = {c.strip() for c in _CYCLE_COLS.split(",")}
    assert "name" not in col_names, "raw 'name' col not in exam_cycles; use cycle_name"
    assert "phase_name" in _PHASE_COLS, "_PHASE_COLS must select phase_name (real DB col)"
    assert "phase_start" in _PHASE_COLS, "_PHASE_COLS must select phase_start (real DB col)"
    assert "phase_end" in _PHASE_COLS, "_PHASE_COLS must select phase_end (real DB col)"
    phase_col_names = {c.strip() for c in _PHASE_COLS.split(",")}
    assert "start_date" not in phase_col_names, "start_date not in exam_phases; use phase_start"
    assert "end_date" not in phase_col_names, "end_date not in exam_phases; use phase_end"


def test_list_cycle_name_maps_to_api_name_field():
    """cycle_name DB column must appear as 'name' in the API response."""
    s = _Seed()
    s.exam("ex", name="Exam", locked=1)
    s.db["exam_cycles"].append({
        "id": "cy-reg", "exam_id": "ex", "cycle_name": "My Cycle 2026",
        "year": 2026, "status": "active", "created_at": _RECENT,
    })
    sb = SBStub(s.db)
    client = TestClient(_build_app(sb))
    r = client.get("/api/admin/exam-intelligence/management/exams?active_state=all")
    body = r.json()
    ex = next(i for i in body["items"] if i["id"] == "ex")
    assert ex["current_cycle"]["name"] == "My Cycle 2026", (
        "cycle_name DB col must map to .name in the API response"
    )


def test_list_phase_db_columns_map_to_api_fields():
    """phase_name/phase_start/phase_end/status are exposed as label/start_date/end_date/status."""
    s = _Seed()
    s.exam("ex", name="Exam", locked=1)
    s.db["exam_cycles"].append({
        "id": "cy-ph-reg", "exam_id": "ex", "cycle_name": "2026",
        "year": 2026, "status": "active", "created_at": _RECENT,
    })
    s.db["exam_phases"].append({
        "id": "ph-reg", "exam_id": "ex", "exam_cycle_id": "cy-ph-reg",
        "phase_name": "Prelims", "phase_slug": "prelims", "phase_order": 1,
        "phase_start": "2026-06-01", "phase_end": "2026-06-30", "status": "upcoming",
    })
    sb = SBStub(s.db)
    client = TestClient(_build_app(sb))
    r = client.get("/api/admin/exam-intelligence/management/exams?active_state=all")
    body = r.json()
    ex = next(i for i in body["items"] if i["id"] == "ex")
    ph = ex["current_cycle"]["phases"][0]
    assert ph["label"] == "Prelims", "phase_name DB col → .label in API"
    assert ph["start_date"] == "2026-06-01", "phase_start DB col → .start_date in API"
    assert ph["end_date"] == "2026-06-30", "phase_end DB col → .end_date in API"
    assert ph["status"] == "upcoming", "phase status must be present in API response"


def test_list_response_includes_family_options():
    """Management list response includes family_options for the family filter dropdown."""
    client, _ = _client()
    r = client.get("/api/admin/exam-intelligence/management/exams?active_state=all")
    body = r.json()
    assert "family_options" in body, "response must include family_options"
    fam_opt = next((f for f in body["family_options"] if f["id"] == "fam1"), None)
    assert fam_opt is not None, "fam1 must appear in family_options"
    assert fam_opt["name"] == "Civil Services"


def test_list_family_options_excluded_when_no_family():
    """Exams without a family do not contribute phantom entries to family_options."""
    s = _Seed()
    s.exam("no-fam", name="No Family Exam", locked=1)  # no family
    sb = SBStub(s.db)
    client = TestClient(_build_app(sb))
    r = client.get("/api/admin/exam-intelligence/management/exams?active_state=all")
    body = r.json()
    assert body["family_options"] == [], "no family → empty family_options"
