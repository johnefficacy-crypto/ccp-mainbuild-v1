"""Tests for derived exam_id on GET /admin/verification-reports/{report_id}.

Coverage:
  1. exam_id resolves from recruitments.exam_id when recruitment_id is set.
  2. exam_id is null when recruitment_id is null (200, not 500).
  3. exam_id is null when recruitment_id is set but recruitment row / its
     exam_id is missing (200, best-effort).
  4. A resolve-read transport error degrades to exam_id=null, endpoint still 200.
  5. Existing detail fields unchanged (none dropped/renamed); exam_id is the
     only added key.
"""
from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_verification_reports as vr_api
from app.core.auth import get_current_user
from tests.persona_questions._stub import SBStub


_ADMIN = {
    "id": "admin-uuid-1",
    "email": "admin@test.local",
    "role": "admin",
    "permissions": ["recruitments.manage"],
}

_REPORT_ID = "report-uuid-aaa"
_RECRUITMENT_ID = "rec-uuid-bbb"
_EXAM_ID = "exam-uuid-ccc"

_REPORT_BASE = {
    "id": _REPORT_ID,
    "recruitment_id": _RECRUITMENT_ID,
    "trigger_reason": "stale_source",
    "lifecycle_status": "open",
    "suggested_proof": None,
    "conflict_reason": None,
}


def _build_app(sb: SBStub) -> TestClient:
    app = FastAPI()
    app.include_router(vr_api.router, prefix="/api")
    vr_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[get_current_user] = lambda: _ADMIN
    return TestClient(app, raise_server_exceptions=False)


# ── 1. exam_id resolves via recruitment_id → recruitments.exam_id ─────────

def test_exam_id_resolved_from_recruitment():
    sb = SBStub({
        "recruitment_verification_reports": [dict(_REPORT_BASE)],
        "recruitments": [{"id": _RECRUITMENT_ID, "exam_id": _EXAM_ID}],
    })
    client = _build_app(sb)

    r = client.get(f"/api/admin/verification-reports/{_REPORT_ID}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["exam_id"] == _EXAM_ID


# ── 2. exam_id is null when recruitment_id is null ────────────────────────

def test_exam_id_null_when_no_recruitment_id():
    report = {**_REPORT_BASE, "recruitment_id": None}
    sb = SBStub({
        "recruitment_verification_reports": [report],
        "recruitments": [],
    })
    client = _build_app(sb)

    r = client.get(f"/api/admin/verification-reports/{_REPORT_ID}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["exam_id"] is None


# ── 3. exam_id is null when recruitment row missing or exam_id absent ─────

def test_exam_id_null_when_recruitment_row_missing():
    sb = SBStub({
        "recruitment_verification_reports": [dict(_REPORT_BASE)],
        "recruitments": [],  # recruitment row doesn't exist
    })
    client = _build_app(sb)

    r = client.get(f"/api/admin/verification-reports/{_REPORT_ID}")
    assert r.status_code == 200, r.text
    assert r.json()["exam_id"] is None


def test_exam_id_null_when_recruitment_has_no_exam_id():
    sb = SBStub({
        "recruitment_verification_reports": [dict(_REPORT_BASE)],
        "recruitments": [{"id": _RECRUITMENT_ID, "exam_id": None}],
    })
    client = _build_app(sb)

    r = client.get(f"/api/admin/verification-reports/{_REPORT_ID}")
    assert r.status_code == 200, r.text
    assert r.json()["exam_id"] is None


# ── 4. Transport error degrades to exam_id=null, still 200 ───────────────

def test_exam_id_null_on_transport_error():
    """Stub raises on recruitments table access; endpoint must still return 200."""

    class _RaisingStub:
        """Supabase stub that raises when 'recruitments' table is queried."""

        def table(self, name: str):
            if name == "recruitments":
                raise RuntimeError("simulated transport failure")
            return SBStub({
                "recruitment_verification_reports": [dict(_REPORT_BASE)],
            }).table(name)

    app = FastAPI()
    app.include_router(vr_api.router, prefix="/api")
    vr_api.get_supabase_admin = lambda: _RaisingStub()  # type: ignore[assignment]
    app.dependency_overrides[get_current_user] = lambda: _ADMIN
    client = TestClient(app, raise_server_exceptions=False)

    r = client.get(f"/api/admin/verification-reports/{_REPORT_ID}")
    assert r.status_code == 200, r.text
    assert r.json()["exam_id"] is None


# ── 5. Existing fields unchanged; exam_id is the only added key ───────────

def test_existing_fields_preserved_and_only_exam_id_added():
    sb = SBStub({
        "recruitment_verification_reports": [dict(_REPORT_BASE)],
        "recruitments": [{"id": _RECRUITMENT_ID, "exam_id": _EXAM_ID}],
    })
    client = _build_app(sb)

    r = client.get(f"/api/admin/verification-reports/{_REPORT_ID}")
    assert r.status_code == 200, r.text
    body = r.json()

    # All original fields present and unchanged.
    for key, value in _REPORT_BASE.items():
        assert body[key] == value, f"field {key!r} changed"

    # exam_id is the only extra key.
    extra_keys = set(body.keys()) - set(_REPORT_BASE.keys())
    assert extra_keys == {"exam_id"}
