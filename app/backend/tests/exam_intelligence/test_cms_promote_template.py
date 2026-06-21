"""PR4a — POST /exam-phases/promote-template

Tests the endpoint that clones a generic (cycle-agnostic) template phase into
a specific exam cycle.  Uses the TaxSBStub from test_cms_taxonomy.py for the
select-side query support; adds a _FailInsertQuery helper for the write-failure
matrix.
"""
from __future__ import annotations

import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intel_cms as cms_api
from app.core.auth import get_current_user
from tests.exam_intelligence.test_cms_taxonomy import TaxSBStub
from tests.persona_questions._stub import SBStub, _Query

_BASE = "/api/admin/exam-intelligence-cms/exam-phases/promote-template"
_PERM_CMS = cms_api.PERM_CMS

# ─── stub helpers ────────────────────────────────────────────────────────────


class _FailWriteQuery(_Query):
    """Raises on the first write (insert or update) for a named table."""

    def execute(self):
        if self._pending_insert is not None or (
            self._pending_update is not None and self._pending_update != "__delete__"
        ):
            raise RuntimeError("stub: injected write failure")
        return super().execute()


class _FailWriteSBStub(TaxSBStub):
    def __init__(self, db, *, fail_table: str):
        super().__init__(db)
        self._fail_table = fail_table

    def table(self, name: str):
        q = super().table(name)
        if name == self._fail_table:
            fq = _FailWriteQuery(name, self.db)
            # Copy filters/pending state would be needed if base table() returned
            # a partially-configured query; here we start fresh because the
            # endpoint builds its own query chain.
            return fq
        return q


# ─── client factory ──────────────────────────────────────────────────────────


def _client(sb: TaxSBStub, *, role: str = "super_admin") -> TestClient:
    app = FastAPI()
    app.include_router(cms_api.router, prefix="/api")
    cms_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[cms_api._flag_enabled] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "admin-1",
        "email": "admin@test.local",
        "role": role,
        "permissions": [_PERM_CMS] if role != "user" else [],
    }
    return TestClient(app, raise_server_exceptions=False)


# ─── seed factory ────────────────────────────────────────────────────────────

_EXAM_ID = "exam-1"
_CYCLE_ID = "cycle-1"
_TEMPLATE_ID = "phase-tmpl-1"
_OTHER_EXAM_ID = "exam-2"
_OTHER_CYCLE_ID = "cycle-x"


def _seed(*, extra_phases: list | None = None) -> dict:
    return {
        "exams": [
            {"id": _EXAM_ID, "slug": "upsc-cse", "name": "UPSC CSE", "is_active": True},
            {"id": _OTHER_EXAM_ID, "slug": "ssc-cgl", "name": "SSC CGL", "is_active": True},
        ],
        "exam_cycles": [
            {"id": _CYCLE_ID, "exam_id": _EXAM_ID, "year": 2026, "cycle_name": "2026"},
            {"id": _OTHER_CYCLE_ID, "exam_id": _OTHER_EXAM_ID, "year": 2026, "cycle_name": "2026"},
        ],
        "exam_phases": [
            {
                "id": _TEMPLATE_ID,
                "exam_id": _EXAM_ID,
                "exam_cycle_id": None,          # template — no cycle
                "phase_name": "Prelims",
                "phase_slug": "prelims",
                "phase_order": 1,
                "status": "active",
                "metadata": {},
            },
            *(extra_phases or []),
        ],
        "admin_audit_logs": [],
    }


def _body(**overrides) -> dict:
    base = {
        "template_phase_id": _TEMPLATE_ID,
        "target_cycle_id": _CYCLE_ID,
        "phase_start": "2026-06-01",
        "reason": "Attaching template to 2026 cycle",
    }
    base.update(overrides)
    return base


# ─── 1. Happy path ───────────────────────────────────────────────────────────


def test_promote_happy_path_201():
    sb = TaxSBStub(_seed())
    r = _client(sb).post(_BASE, json=_body())
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["ok"] is True
    created = body["row"]

    # New phase is cycle-bound
    assert created["exam_cycle_id"] == _CYCLE_ID
    assert created["exam_id"] == _EXAM_ID
    assert created["phase_slug"] == "prelims"
    assert created["status"] == "expected"           # default when omitted

    # Provenance metadata present
    meta = created["metadata"]
    assert meta["promoted_from_template_phase_id"] == _TEMPLATE_ID
    assert meta["promoted_via"] == "exam_workspace.promote_template_to_cycle"
    assert meta["promote_reason"] == "Attaching template to 2026 cycle"

    # Template row untouched (still cycle-agnostic)
    template = next(p for p in sb.db["exam_phases"] if p["id"] == _TEMPLATE_ID)
    assert template["exam_cycle_id"] is None

    # Audit row written
    assert len(sb.db["admin_audit_logs"]) == 1
    audit = sb.db["admin_audit_logs"][0]
    assert audit["action"] == "exam_intel.cms.phase.promote_template"
    assert audit["entity_id"] == created["id"]


# ─── 2. Source not a template ────────────────────────────────────────────────


def test_promote_source_not_template_422():
    cycle_bound = {
        "id": "phase-bound-1",
        "exam_id": _EXAM_ID,
        "exam_cycle_id": _CYCLE_ID,           # already bound
        "phase_name": "Mains",
        "phase_slug": "mains",
        "phase_order": 2,
        "status": "expected",
        "metadata": {},
    }
    sb = TaxSBStub(_seed(extra_phases=[cycle_bound]))
    r = _client(sb).post(_BASE, json=_body(template_phase_id="phase-bound-1"))
    assert r.status_code == 422
    assert "source_phase_must_be_template" in r.text


# ─── 3. Cross-exam cycle ─────────────────────────────────────────────────────


def test_promote_cross_exam_422():
    sb = TaxSBStub(_seed())
    r = _client(sb).post(_BASE, json=_body(target_cycle_id=_OTHER_CYCLE_ID))
    assert r.status_code == 422
    assert "target_cycle_exam_mismatch" in r.text


# ─── 4. Date validation ──────────────────────────────────────────────────────


def test_promote_phase_end_before_start_422():
    sb = TaxSBStub(_seed())
    r = _client(sb).post(_BASE, json=_body(phase_start="2026-09-01", phase_end="2026-08-01"))
    assert r.status_code == 422
    assert "invalid_phase_date_range" in r.text


def test_promote_missing_phase_start_422():
    sb = TaxSBStub(_seed())
    # phase_start is required by Pydantic — omitting it yields 422 from body validation
    payload = {k: v for k, v in _body().items() if k != "phase_start"}
    r = _client(sb).post(_BASE, json=payload)
    assert r.status_code == 422


# ─── 5. Invalid status ───────────────────────────────────────────────────────


def test_promote_invalid_status_422():
    sb = TaxSBStub(_seed())
    r = _client(sb).post(_BASE, json=_body(status="verified"))
    assert r.status_code == 422
    assert "invalid_status" in r.text


# ─── 6. Collision ────────────────────────────────────────────────────────────


def test_promote_collision_409():
    existing = {
        "id": str(uuid.uuid4()),
        "exam_id": _EXAM_ID,
        "exam_cycle_id": _CYCLE_ID,
        "phase_name": "Prelims",
        "phase_slug": "prelims",   # same slug as template
        "phase_order": 1,
        "status": "expected",
        "metadata": {},
    }
    sb = TaxSBStub(_seed(extra_phases=[existing]))
    r = _client(sb).post(_BASE, json=_body())
    assert r.status_code == 409
    body = r.json()
    detail = body.get("detail", body)
    assert detail["code"] == "cycle_phase_already_exists"
    assert detail["existing_phase_id"] == existing["id"]


# ─── 7. Phase insert fails → 500, no orphan audit ────────────────────────────


def test_promote_phase_insert_fails_500_no_audit():
    sb = _FailWriteSBStub(_seed(), fail_table="exam_phases")
    r = _client(sb).post(_BASE, json=_body())
    assert r.status_code == 500
    # No audit row must have been written
    assert sb.db.get("admin_audit_logs", []) == []


# ─── 8. Audit insert fails → 500, phase still exists ────────────────────────


def test_promote_audit_insert_fails_500_phase_survives():
    sb = _FailWriteSBStub(_seed(), fail_table="admin_audit_logs")
    r = _client(sb).post(_BASE, json=_body())
    assert r.status_code == 500
    body = r.json()
    detail = body.get("detail", body)
    assert detail["code"] == "audit_write_failed"
    phase_id = detail["phase_id"]
    assert phase_id  # non-empty

    # Phase was created and NOT rolled back
    cycle_phases = [
        p for p in sb.db.get("exam_phases", [])
        if p.get("exam_cycle_id") == _CYCLE_ID
    ]
    assert len(cycle_phases) == 1
    assert cycle_phases[0]["id"] == phase_id


# ─── 9. Non-CMS user → 403 ───────────────────────────────────────────────────


def test_promote_non_cms_user_403():
    sb = TaxSBStub(_seed())
    r = _client(sb, role="user").post(_BASE, json=_body())
    assert r.status_code == 403


# ─── 10. Status omitted → defaults to "expected" ────────────────────────────


def test_promote_status_omitted_defaults_expected():
    sb = TaxSBStub(_seed())
    r = _client(sb).post(_BASE, json=_body())
    assert r.status_code == 201, r.text
    assert r.json()["row"]["status"] == "expected"
