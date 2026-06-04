"""Tests for Concern 1 (org create) and Concerns 2+3 (exam slug gen + org linkage).

Tests are written FIRST — they fail against the current code and pass after
the implementation in admin_trust.py and admin_exam_intel_cms.py.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api import admin_trust, admin_exam_intel_cms
from app.core.auth import get_current_user
from app.core.config import get_settings


# ─── Shared stubs ──────────────────────────────────────────────────────────


class R:
    def __init__(self, data=None, count=None):
        self.data = data
        self.count = count


def _admin_user():
    return {"id": "admin-1", "role": "super_admin", "permissions": []}


# ════════════════════════════════════════════════════════════════════════════
#  Concern 1 — POST /admin/organizations
# ════════════════════════════════════════════════════════════════════════════


class _OrgCreateSB:
    """Supabase stub for the org-create endpoint."""

    def __init__(
        self,
        *,
        same_name_rows=None,   # rows returned by the soft-match query
        insert_raises=None,    # exception to raise on insert (simulate dup idx)
        inserted_row=None,     # row returned after successful insert
    ):
        self.same_name_rows = same_name_rows or []
        self.insert_raises = insert_raises
        self.inserted_row = inserted_row or {"id": "org-new", "name": "Bihar PSC", "type": "state_psc", "short_name": "BPSC", "state": "Bihar", "is_verified": False, "trust_tier": "unverified", "metadata": {}}
        self.inserted_payload = None
        self.audit_logged = False

    def table(self, name):
        outer = self

        class T:
            def __init__(self, tname):
                self._name = tname
                self._filters = {}

            def select(self, *a, **k):
                return self

            def ilike(self, *a, **k):
                return self

            def eq(self, k, v):
                self._filters[k] = v
                return self

            def limit(self, *a, **k):
                return self

            def insert(self, payload):
                if self._name == "organizations":
                    outer.inserted_payload = payload
                    if outer.insert_raises:
                        raise outer.insert_raises
                return self

            def execute(self):
                if self._name == "organizations" and outer.inserted_payload is None:
                    # soft-match query path
                    return R(outer.same_name_rows)
                if self._name == "organizations" and outer.inserted_payload is not None:
                    return R([outer.inserted_row])
                if self._name == "admin_audit_logs":
                    outer.audit_logged = True
                    return R([{"id": "audit-1"}])
                return R([])

        return T(name)


def _build_trust_app():
    app = FastAPI()
    app.include_router(admin_trust.router)
    app.dependency_overrides[get_current_user] = _admin_user
    return app


def test_org_create_forces_unverified(monkeypatch):
    """Client-supplied is_verified and trust_tier MUST be ignored; server forces false/unverified."""
    sb = _OrgCreateSB()
    monkeypatch.setattr(admin_trust, "get_supabase_admin", lambda: sb)
    client = TestClient(_build_trust_app(), raise_server_exceptions=False)

    resp = client.post("/admin/organizations", json={
        "name": "Bihar PSC",
        "type": "state_psc",
        "short_name": "BPSC",
        "state": "Bihar",
        "is_verified": True,       # must be overridden
        "trust_tier": "verified",  # must be overridden
    })
    assert resp.status_code == 201
    payload = sb.inserted_payload
    assert payload["is_verified"] is False
    assert payload["trust_tier"] == "unverified"


def test_org_create_requires_short_name(monkeypatch):
    """Missing short_name → 422."""
    sb = _OrgCreateSB()
    monkeypatch.setattr(admin_trust, "get_supabase_admin", lambda: sb)
    client = TestClient(_build_trust_app(), raise_server_exceptions=False)

    resp = client.post("/admin/organizations", json={
        "name": "Bihar PSC",
        "type": "state_psc",
        # no short_name
    })
    assert resp.status_code == 422


def test_org_create_409_on_duplicate_short_name(monkeypatch):
    """Duplicate short_name (unique index violation) → 409."""

    class _DupExc(Exception):
        pass

    sb = _OrgCreateSB(insert_raises=_DupExc("duplicate key value violates unique constraint"))
    monkeypatch.setattr(admin_trust, "get_supabase_admin", lambda: sb)
    client = TestClient(_build_trust_app(), raise_server_exceptions=False)

    resp = client.post("/admin/organizations", json={
        "name": "Bihar PSC",
        "type": "state_psc",
        "short_name": "BPSC",
        "state": "Bihar",
    })
    assert resp.status_code == 409


def test_org_create_soft_warning_on_same_name(monkeypatch):
    """Same name exists (different short_name) → 201 with non-empty warnings list."""
    sb = _OrgCreateSB(
        same_name_rows=[{"id": "org-old", "name": "Bihar PSC"}],
    )
    monkeypatch.setattr(admin_trust, "get_supabase_admin", lambda: sb)
    client = TestClient(_build_trust_app(), raise_server_exceptions=False)

    resp = client.post("/admin/organizations", json={
        "name": "Bihar PSC",
        "type": "state_psc",
        "short_name": "BPSC-ALT",
        "state": "Bihar",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["warnings"]  # non-empty
    assert body["warnings"][0]["existing_id"] == "org-old"


def test_org_create_no_warning_when_no_same_name(monkeypatch):
    """No existing same-name row → 201 with empty warnings list."""
    sb = _OrgCreateSB(same_name_rows=[])
    monkeypatch.setattr(admin_trust, "get_supabase_admin", lambda: sb)
    client = TestClient(_build_trust_app(), raise_server_exceptions=False)

    resp = client.post("/admin/organizations", json={
        "name": "New PSC",
        "type": "state_psc",
        "short_name": "NPSC",
    })
    assert resp.status_code == 201
    assert resp.json()["warnings"] == []


# ════════════════════════════════════════════════════════════════════════════
#  Concerns 2 + 3 — exam create: org linkage + server-side slug gen
# ════════════════════════════════════════════════════════════════════════════


def _patch_settings(monkeypatch):
    """Enable the ADMIN_STUDY_OS_ENABLED flag so the CMS router is active."""
    settings = get_settings()
    monkeypatch.setattr(settings, "ADMIN_STUDY_OS_ENABLED", True)


class _ExamCreateSB:
    """Stub for exam create — tracks inserts and supports org lookup."""

    def __init__(self, *, org_row=None, slug_collision=False):
        self.org_row = org_row  # None → org not found
        self.slug_collision = slug_collision
        self.inserted_payload = None

    def table(self, name):
        outer = self

        class T:
            def __init__(self, tname):
                self._name = tname
                self._filters = {}

            def select(self, *a, **k):
                return self

            def eq(self, k, v):
                self._filters[k] = v
                return self

            def limit(self, *a, **k):
                return self

            def insert(self, payload):
                if self._name == "exams":
                    outer.inserted_payload = payload
                    if outer.slug_collision:
                        raise Exception("duplicate key value violates unique constraint")
                return self

            def execute(self):
                if self._name == "exams" and outer.inserted_payload is not None:
                    return R([{**outer.inserted_payload, "id": "exam-new"}])
                if self._name == "organizations" and outer.org_row:
                    return R([outer.org_row])
                if self._name == "admin_audit_logs":
                    return R([{"id": "audit-1"}])
                # exam_families / exams lookup → empty (family_id not supplied)
                return R([])

        return T(name)


def _build_cms_app(sb, monkeypatch):
    _patch_settings(monkeypatch)
    app = FastAPI()
    app.include_router(admin_exam_intel_cms.router)
    # Patch module-level get_supabase_admin used inside the handler
    monkeypatch.setattr(admin_exam_intel_cms, "get_supabase_admin", lambda: sb)
    monkeypatch.setattr(admin_exam_intel_cms, "invalidate_exam_lookup_cache", lambda: None)
    app.dependency_overrides[get_current_user] = _admin_user
    return app


def test_exam_create_persists_conducting_org_id(monkeypatch):
    """conducting_organization_id in payload must be forwarded to the DB insert."""
    org_row = {"id": "org-1", "type": "central_commission", "state": None}
    sb = _ExamCreateSB(org_row=org_row)
    app = _build_cms_app(sb, monkeypatch)
    client = TestClient(app, raise_server_exceptions=False)

    resp = client.post("/admin/exam-intelligence-cms/exams", json={
        "reason": "adding exam for test",
        "payload": {
            "name": "SSC CGL",
            "conducting_organization_id": "org-1",
        },
    })
    assert resp.status_code == 200
    assert sb.inserted_payload is not None
    assert sb.inserted_payload.get("conducting_organization_id") == "org-1"


def test_exam_create_ignores_payload_slug(monkeypatch):
    """Any slug supplied in the payload must be discarded; server generates it."""
    sb = _ExamCreateSB()
    app = _build_cms_app(sb, monkeypatch)
    client = TestClient(app, raise_server_exceptions=False)

    resp = client.post("/admin/exam-intelligence-cms/exams", json={
        "reason": "test slug override",
        "payload": {
            "name": "SSC CGL",
            "slug": "my-custom-slug",  # must be ignored
        },
    })
    assert resp.status_code == 200
    assert sb.inserted_payload["slug"] != "my-custom-slug"


def test_exam_create_slug_plain_name(monkeypatch):
    """Without a state_psc org, slug = slugify(name)."""
    sb = _ExamCreateSB()
    app = _build_cms_app(sb, monkeypatch)
    client = TestClient(app, raise_server_exceptions=False)

    resp = client.post("/admin/exam-intelligence-cms/exams", json={
        "reason": "slug from name",
        "payload": {"name": "SSC Combined Graduate Level Exam"},
    })
    assert resp.status_code == 200
    assert sb.inserted_payload["slug"] == "ssc-combined-graduate-level-exam"


def test_exam_create_slug_state_psc_prefixes_state(monkeypatch):
    """state_psc org with state → slug = slugify(state)+'-'+slugify(name)."""
    org_row = {"id": "org-psc", "type": "state_psc", "state": "Punjab"}
    sb = _ExamCreateSB(org_row=org_row)
    app = _build_cms_app(sb, monkeypatch)
    client = TestClient(app, raise_server_exceptions=False)

    resp = client.post("/admin/exam-intelligence-cms/exams", json={
        "reason": "state psc exam",
        "payload": {
            "name": "Punjab State Services Exam",
            "conducting_organization_id": "org-psc",
        },
    })
    assert resp.status_code == 200
    assert sb.inserted_payload["slug"] == "punjab-punjab-state-services-exam"


def test_exam_create_slug_state_psc_no_state_falls_back(monkeypatch):
    """state_psc org but state=None → falls back to slugify(name)."""
    org_row = {"id": "org-psc", "type": "state_psc", "state": None}
    sb = _ExamCreateSB(org_row=org_row)
    app = _build_cms_app(sb, monkeypatch)
    client = TestClient(app, raise_server_exceptions=False)

    resp = client.post("/admin/exam-intelligence-cms/exams", json={
        "reason": "state psc no state",
        "payload": {
            "name": "State Services Exam",
            "conducting_organization_id": "org-psc",
        },
    })
    assert resp.status_code == 200
    assert sb.inserted_payload["slug"] == "state-services-exam"


def test_exam_create_slug_collision_is_409(monkeypatch):
    """Duplicate slug → 409, no numeric suffix appended."""
    sb = _ExamCreateSB(slug_collision=True)
    app = _build_cms_app(sb, monkeypatch)
    client = TestClient(app, raise_server_exceptions=False)

    resp = client.post("/admin/exam-intelligence-cms/exams", json={
        "reason": "collision test",
        "payload": {"name": "SSC CGL"},
    })
    assert resp.status_code == 409
    body = resp.json()
    # Detail must mention the slug so the operator can act on it
    assert "ssc-cgl" in body.get("detail", "")
