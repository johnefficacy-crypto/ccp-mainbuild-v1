"""CMS create/patch endpoint tests for exam_candidate_counts (J3 PR2,
migration 219). Mirrors the exam-competition-metrics CMS test pattern."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intel_cms as cms_api
from app.core.auth import get_current_user
from tests.persona_questions._stub import SBStub

_BASE = "/api/admin/exam-intelligence-cms"
_CC = f"{_BASE}/exam-candidate-counts"


def _client(sb: SBStub, *, role: str = "super_admin", permissions=None) -> TestClient:
    app = FastAPI()
    app.include_router(cms_api.router, prefix="/api")
    cms_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[cms_api._flag_enabled] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "admin-1", "role": role,
        "permissions": [cms_api.PERM_CMS] if permissions is None else permissions,
    }
    return TestClient(app, raise_server_exceptions=False)


def _seed():
    return {
        "exams": [{"id": "e1"}],
        "exam_cycles": [{"id": "cy1", "exam_id": "e1"}],
        "exam_phases": [{"id": "ph1", "exam_id": "e1", "exam_cycle_id": "cy1"}, {"id": "ph2", "exam_id": "e1"}],
    }


def test_create_applied_count():
    sb = SBStub(_seed())
    r = _client(sb).post(_CC, json={"reason": "seed applied", "payload": {
        "exam_id": "e1", "exam_cycle_id": "cy1", "scope_kind": "cycle",
        "count_type": "applied", "count_value": 1200000,
    }})
    assert r.status_code == 200, r.text
    row = sb.db["exam_candidate_counts"][0]
    assert row["count_type"] == "applied" and row["reviewer_status"] == "draft"


def test_create_appeared_phase_count():
    sb = SBStub(_seed())
    r = _client(sb).post(_CC, json={"reason": "seed appeared", "payload": {
        "exam_id": "e1", "exam_cycle_id": "cy1", "exam_phase_id": "ph1",
        "scope_kind": "phase", "count_type": "appeared", "count_value": 500000,
    }})
    assert r.status_code == 200, r.text
    assert sb.db["exam_candidate_counts"][0]["exam_phase_id"] == "ph1"


def test_applied_count_rejects_phase_scope():
    sb = SBStub(_seed())
    r = _client(sb).post(_CC, json={"reason": "bad applied", "payload": {
        "exam_id": "e1", "exam_cycle_id": "cy1", "exam_phase_id": "ph1",
        "scope_kind": "phase", "count_type": "applied", "count_value": 1200000,
    }})
    assert r.status_code == 422
    assert "applied counts must be scope_kind" in r.json()["detail"]


def test_appeared_cycle_aggregate_allowed_without_phase():
    sb = SBStub(_seed())
    r = _client(sb).post(_CC, json={"reason": "aggregate appeared", "payload": {
        "exam_id": "e1", "exam_cycle_id": "cy1",
        "scope_kind": "cycle", "count_type": "appeared", "count_value": 1000000,
    }})
    assert r.status_code == 200, r.text


def test_phase_belongs_to_different_exam_rejected():
    sb = SBStub({**_seed(), "exams": [{"id": "e1"}, {"id": "e2"}]})
    r = _client(sb).post(_CC, json={"reason": "cross-exam phase", "payload": {
        "exam_id": "e2", "exam_cycle_id": "cy1", "exam_phase_id": "ph1",
        "scope_kind": "phase", "count_type": "appeared", "count_value": 500000,
    }})
    assert r.status_code == 422
    assert "different exam" in r.json()["detail"]


def test_phase_belongs_to_different_cycle_rejected():
    sb = SBStub({**_seed(), "exam_cycles": [{"id": "cy1", "exam_id": "e1"}, {"id": "cy2", "exam_id": "e1"}]})
    r = _client(sb).post(_CC, json={"reason": "cross-cycle phase", "payload": {
        "exam_id": "e1", "exam_cycle_id": "cy2", "exam_phase_id": "ph1",
        "scope_kind": "phase", "count_type": "appeared", "count_value": 500000,
    }})
    assert r.status_code == 422
    assert "different exam_cycle_id" in r.json()["detail"]


def test_negative_count_value_rejected():
    sb = SBStub(_seed())
    r = _client(sb).post(_CC, json={"reason": "bad count", "payload": {
        "exam_id": "e1", "exam_cycle_id": "cy1", "scope_kind": "cycle",
        "count_type": "applied", "count_value": -5,
    }})
    assert r.status_code == 422


def test_missing_exam_cycle_id_rejected():
    sb = SBStub(_seed())
    r = _client(sb).post(_CC, json={"reason": "no cycle", "payload": {
        "exam_id": "e1", "scope_kind": "cycle", "count_type": "applied", "count_value": 1000,
    }})
    assert r.status_code == 422
    assert "exam_cycle_id is required" in r.json()["detail"]


def test_patch_candidate_count_whitelisted():
    sb = SBStub({**_seed(), "exam_candidate_counts": [
        {"id": "cc1", "exam_id": "e1", "exam_cycle_id": "cy1", "scope_kind": "cycle",
         "count_type": "applied", "count_value": 1000, "reviewer_status": "draft"},
    ]})
    r = _client(sb).patch(f"{_CC}/cc1", json={"reason": "fix count", "payload": {"count_value": 1050, "bogus": 1}})
    assert r.status_code == 200
    assert sb.db["exam_candidate_counts"][0]["count_value"] == 1050


def test_patch_candidate_count_rejects_scope_change():
    sb = SBStub({**_seed(), "exam_candidate_counts": [
        {"id": "cc1", "exam_id": "e1", "exam_cycle_id": "cy1", "scope_kind": "cycle",
         "count_type": "applied", "count_value": 1000, "reviewer_status": "draft"},
    ]})
    r = _client(sb).patch(f"{_CC}/cc1", json={"reason": "try scope change", "payload": {"exam_cycle_id": "cy2"}})
    assert r.status_code == 422
    assert "No allowed fields" in r.json()["detail"]


def test_patch_missing_row_404():
    sb = SBStub(_seed())
    r = _client(sb).patch(f"{_CC}/no-such", json={"reason": "no such row", "payload": {"count_value": 1}})
    assert r.status_code == 404


def test_template_unbound_phase_rejected():
    """checkpost P1-3: ph2 is a template/unbound phase (exam_cycle_id IS NULL).
    A phase-scoped appeared count must NOT accept it — the phase must be bound
    to the same cycle (OD-3)."""
    sb = SBStub(_seed())
    r = _client(sb).post(_CC, json={"reason": "unbound phase appeared", "payload": {
        "exam_id": "e1", "exam_cycle_id": "cy1", "exam_phase_id": "ph2",
        "scope_kind": "phase", "count_type": "appeared", "count_value": 500000,
    }})
    assert r.status_code == 422
    assert "template/unbound phase" in r.json()["detail"]


def test_patch_candidate_count_rejects_category_change():
    """checkpost P1-4: reservation_category_id is immutable scope — a reopened
    draft must not repoint its category (which could supersede a parent in a
    different category scope)."""
    sb = SBStub({**_seed(), "exam_candidate_counts": [
        {"id": "cc1", "exam_id": "e1", "exam_cycle_id": "cy1", "scope_kind": "cycle",
         "count_type": "applied", "reservation_category_id": None,
         "count_value": 1000, "reviewer_status": "draft"},
    ]})
    r = _client(sb).patch(f"{_CC}/cc1", json={"reason": "try category change", "payload": {"reservation_category_id": "cat-obc"}})
    assert r.status_code == 422
    assert "No allowed fields" in r.json()["detail"]
    assert sb.db["exam_candidate_counts"][0]["reservation_category_id"] is None


# ── Permission tier (checkpost P0-1): candidate-count create/patch are normal
# Manage-Exam canonical edits gated on `exam_intelligence.manage`, NOT on the
# Advanced-Repair `exam_intelligence.cms`. ────────────────────────────────────

def _create_body():
    return {"reason": "seed applied", "payload": {
        "exam_id": "e1", "exam_cycle_id": "cy1", "scope_kind": "cycle",
        "count_type": "applied", "count_value": 1200000,
    }}


def test_create_allowed_for_manage_permission():
    sb = SBStub(_seed())
    r = _client(sb, role="admin", permissions=["exam_intelligence.manage"]).post(_CC, json=_create_body())
    assert r.status_code == 200, r.text


def test_create_forbidden_for_cms_only_permission():
    sb = SBStub(_seed())
    r = _client(sb, role="admin", permissions=["exam_intelligence.cms"]).post(_CC, json=_create_body())
    assert r.status_code == 403, r.text


def test_create_forbidden_for_review_only_permission():
    sb = SBStub(_seed())
    r = _client(sb, role="admin", permissions=["exam_intelligence.review"]).post(_CC, json=_create_body())
    assert r.status_code == 403, r.text


def test_patch_allowed_for_manage_permission():
    sb = SBStub({**_seed(), "exam_candidate_counts": [
        {"id": "cc1", "exam_id": "e1", "exam_cycle_id": "cy1", "scope_kind": "cycle",
         "count_type": "applied", "reservation_category_id": None, "count_value": 1000,
         "reviewer_status": "draft", "version_no": 1},
    ]})
    r = _client(sb, role="admin", permissions=["exam_intelligence.manage"]).patch(
        f"{_CC}/cc1", json={"reason": "curate value", "payload": {"count_value": 1050}})
    assert r.status_code == 200, r.text
    assert sb.db["exam_candidate_counts"][0]["count_value"] == 1050
