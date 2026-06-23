"""Tests for the PYQ-paper trust_status lifecycle endpoint.

POST /admin/exam-intelligence-cms/pyq-papers/{paper_id}/review

Covers:
- pending → verified (happy path)
- pending → rejected (happy path)
- verified → rejected (downgrade allowed)
- rejected → verified (re-verify allowed)
- 404 for unknown paper
- 422 for disallowed target status (e.g. 'pending')
- 422 for reason shorter than 8 chars
- 403 when unauthenticated
- audit log row written with from/to status and reviewer email
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intel_cms as cms_api
from app.core.auth import get_current_user
from tests.exam_intelligence.test_cms_taxonomy import TaxSBStub

_BASE = "/api/admin/exam-intelligence-cms"

_ADMIN = {"id": "admin-1", "email": "admin@example.com", "role": "super_admin", "permissions": [cms_api.PERM_CMS]}


def _client(sb, *, authed: bool = True):
    app = FastAPI()
    app.include_router(cms_api.router, prefix="/api")
    cms_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[cms_api._flag_enabled] = lambda: None
    if authed:
        app.dependency_overrides[get_current_user] = lambda: _ADMIN
    return TestClient(app, raise_server_exceptions=False)


def _seed(trust_status: str = "pending") -> dict:
    return {
        "pyq_papers": [{"id": "p1", "exam_id": "e1", "year": 2024, "trust_status": trust_status}],
        "admin_audit_logs": [],
    }


def _review(client, paper_id: str, status: str, reason: str = "operator verified source docs"):
    return client.post(
        f"{_BASE}/pyq-papers/{paper_id}/review",
        json={"status": status, "reason": reason},
    )


# ── happy paths ────────────────────────────────────────────────────────


def test_pending_to_verified():
    sb = TaxSBStub(_seed("pending"))
    r = _review(_client(sb), "p1", "verified")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["row"]["trust_status"] == "verified"
    assert sb.db["pyq_papers"][0]["trust_status"] == "verified"


def test_pending_to_rejected():
    sb = TaxSBStub(_seed("pending"))
    r = _review(_client(sb), "p1", "rejected")
    assert r.status_code == 200, r.text
    assert r.json()["row"]["trust_status"] == "rejected"
    assert sb.db["pyq_papers"][0]["trust_status"] == "rejected"


def test_verified_to_rejected():
    sb = TaxSBStub(_seed("verified"))
    r = _review(_client(sb), "p1", "rejected")
    assert r.status_code == 200, r.text
    assert r.json()["row"]["trust_status"] == "rejected"


def test_rejected_to_verified():
    sb = TaxSBStub(_seed("rejected"))
    r = _review(_client(sb), "p1", "verified")
    assert r.status_code == 200, r.text
    assert r.json()["row"]["trust_status"] == "verified"


# ── audit log ─────────────────────────────────────────────────────────


def test_review_writes_audit_log_with_provenance():
    sb = TaxSBStub(_seed("pending"))
    r = _review(_client(sb), "p1", "verified", reason="confirmed via official source")
    assert r.status_code == 200, r.text
    assert r.json()["audit_id"] is not None
    logs = sb.db.get("admin_audit_logs", [])
    assert len(logs) == 1
    log = logs[0]
    assert log["action"] == "exam_intel.cms.pyq_paper.review"
    assert log["entity_type"] == "pyq_paper"
    assert log["entity_id"] == "p1"
    assert log["new_value"]["from_status"] == "pending"
    assert log["new_value"]["to_status"] == "verified"
    assert log["new_value"]["reason"] == "confirmed via official source"
    assert log["new_value"]["reviewed_by"] == "admin@example.com"
    assert log["actor_id"] == "admin-1"


# ── error cases ────────────────────────────────────────────────────────


def test_review_unknown_paper_404():
    sb = TaxSBStub(_seed())
    r = _review(_client(sb), "does-not-exist", "verified")
    assert r.status_code == 404, r.text


def test_review_rejects_pending_as_target_status():
    sb = TaxSBStub(_seed("verified"))
    r = _review(_client(sb), "p1", "pending")
    assert r.status_code == 422, r.text


def test_review_rejects_unknown_status():
    sb = TaxSBStub(_seed())
    r = _review(_client(sb), "p1", "approved")
    assert r.status_code == 422, r.text


def test_review_requires_reason_at_least_8_chars():
    sb = TaxSBStub(_seed())
    r = _review(_client(sb), "p1", "verified", reason="short")
    assert r.status_code == 422, r.text


def test_review_requires_auth():
    sb = TaxSBStub(_seed())
    r = _review(_client(sb, authed=False), "p1", "verified")
    assert r.status_code in (401, 403), r.text
