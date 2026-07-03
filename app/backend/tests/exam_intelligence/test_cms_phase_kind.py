"""EI-CLEAN-01 — canonical ``exam_phases.phase_kind`` editing contract.

Covers the ``_validate_phase_kind`` guard added to ``create_phase`` (POST) and
``update_phase`` (PATCH): the 7 canonical D05 kinds and the DB-legal ``other``
marker are accepted, ``null``/omitted is accepted (unset = unclassified), and
any other value is rejected with HTTP 422 (before the DB CHECK would fire).

Reuses ``TaxSBStub`` / ``_client`` from the promote-template suite's seed model.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intel_cms as cms_api
from app.core.auth import get_current_user
from app.exam_intelligence.document_policy import CLASSIFIED_PHASE_KINDS
from tests.exam_intelligence.test_cms_taxonomy import TaxSBStub

_BASE = "/api/admin/exam-intelligence-cms/exam-phases"
_PERM_CMS = cms_api.PERM_CMS
_EXAM_ID = "exam-1"
_CYCLE_ID = "cycle-1"
_PHASE_ID = "phase-1"


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


def _seed(*, phase_kind: str | None = None) -> dict:
    return {
        "exams": [{"id": _EXAM_ID, "slug": "upsc-cse", "name": "UPSC CSE", "is_active": True}],
        "exam_cycles": [{"id": _CYCLE_ID, "exam_id": _EXAM_ID, "year": 2026, "cycle_name": "2026"}],
        "exam_phases": [
            {
                "id": _PHASE_ID,
                "exam_id": _EXAM_ID,
                "exam_cycle_id": _CYCLE_ID,
                "phase_name": "Prelims",
                "phase_slug": "prelims",
                "phase_order": 1,
                "status": "expected",
                "phase_kind": phase_kind,
                "metadata": {},
            }
        ],
        "admin_audit_logs": [],
    }


def _create_body(**payload_overrides) -> dict:
    payload = {
        "exam_id": _EXAM_ID,
        "exam_cycle_id": _CYCLE_ID,
        "phase_name": "Mains",
        "phase_slug": "mains",
        "phase_order": 2,
    }
    payload.update(payload_overrides)
    return {"reason": "add phase", "payload": payload}


# ── create (POST) ────────────────────────────────────────────────────────────


def test_create_accepts_each_canonical_kind():
    for kind in CLASSIFIED_PHASE_KINDS:
        sb = TaxSBStub(_seed())
        r = _client(sb).post(_BASE, json=_create_body(phase_kind=kind, phase_slug=f"p-{kind}"))
        assert r.status_code == 200, (kind, r.text)
        assert r.json()["row"]["phase_kind"] == kind


def test_create_accepts_other_marker():
    sb = TaxSBStub(_seed())
    r = _client(sb).post(_BASE, json=_create_body(phase_kind="other"))
    assert r.status_code == 200, r.text
    assert r.json()["row"]["phase_kind"] == "other"


def test_create_allows_null_and_omitted_kind():
    sb = TaxSBStub(_seed())
    r_null = _client(sb).post(_BASE, json=_create_body(phase_kind=None, phase_slug="p-null"))
    assert r_null.status_code == 200, r_null.text

    sb2 = TaxSBStub(_seed())
    r_omit = _client(sb2).post(_BASE, json=_create_body(phase_slug="p-omit"))
    assert r_omit.status_code == 200, r_omit.text


def test_create_rejects_unknown_kind_422():
    sb = TaxSBStub(_seed())
    r = _client(sb).post(_BASE, json=_create_body(phase_kind="viva_voce"))
    assert r.status_code == 422, r.text
    assert "invalid_phase_kind" in r.text


# ── update (PATCH) ───────────────────────────────────────────────────────────


def test_patch_classifies_unclassified_phase():
    sb = TaxSBStub(_seed(phase_kind=None))
    r = _client(sb).patch(
        f"{_BASE}/{_PHASE_ID}",
        json={"reason": "classify", "payload": {"phase_kind": "objective_written"}},
    )
    assert r.status_code == 200, r.text
    assert r.json()["row"]["phase_kind"] == "objective_written"


def test_patch_rejects_unknown_kind_422():
    sb = TaxSBStub(_seed(phase_kind=None))
    r = _client(sb).patch(
        f"{_BASE}/{_PHASE_ID}",
        json={"reason": "classify", "payload": {"phase_kind": "not_a_kind"}},
    )
    assert r.status_code == 422, r.text
    assert "invalid_phase_kind" in r.text
