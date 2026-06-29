"""Tests for the PYQ-source trust_status lifecycle endpoint (review).

POST /admin/exam-intelligence-cms/pyq-sources/{source_id}/review

This is the deferred OD-2 follow-up: pyq_sources previously had no dedicated
review action (trust_status was only PATCH-editable).  The endpoint mirrors
``review_pyq_paper`` and is backed by the atomic ``cms_review_pyq_source`` RPC
(migration 193).

Covers:
- Authorization: exam_intelligence.review required; cms-only → 403;
  super_admin → allowed; unauthenticated → 401/403
- Transition matrix (mirrors paper review):
    pending  → verified ✓   pending  → rejected ✓
    verified → rejected ✓   rejected → pending  ✓
    rejected → verified ✗   verified → pending  ✗  (no-ops also ✗)
- Audit row written with action exam_intel.cms.pyq_source.review
- trust_status actually updated on the row
- Concurrent-modification guard → 409 (no false audit row)
- 404 for unknown source
- 422 for short reason / unknown target status
- Direct-RPC validation (RPC authoritative without Python prechecks)
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intel_cms as cms_api
from app.core.auth import get_current_user
from tests.exam_intelligence.test_cms_taxonomy import TaxSBStub

_BASE = "/api/admin/exam-intelligence-cms"

_REVIEWER = {
    "id": "rev-1", "email": "reviewer@example.com",
    "role": "admin", "permissions": [cms_api.PERM_REVIEW],
}
_CMS_ONLY = {
    "id": "cms-1", "email": "cms@example.com",
    "role": "admin", "permissions": [cms_api.PERM_CMS],
}
_SUPER = {
    "id": "sup-1", "email": "super@example.com",
    "role": "super_admin", "permissions": [],
}


def _client(sb, user=_REVIEWER):
    app = FastAPI()
    app.include_router(cms_api.router, prefix="/api")
    cms_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[cms_api._flag_enabled] = lambda: None
    if user is not None:
        app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app, raise_server_exceptions=False)


def _seed(trust_status: str = "pending", **extra) -> dict:
    source = {
        "id": "src-1", "exam_id": "e1",
        "source_type": "official",
        "source_url": "https://upsc.gov.in/registry/2024",
        "title": "UPSC Official 2024 Registry",
        "trust_status": trust_status,
        "metadata": {},
        **extra,
    }
    return {"pyq_sources": [source], "admin_audit_logs": []}


def _review(client, source_id="src-1", status="verified", reason="operator verified registry source"):
    return client.post(
        f"{_BASE}/pyq-sources/{source_id}/review",
        json={"status": status, "reason": reason},
    )


# ── Authorization ──────────────────────────────────────────────────────


def test_reviewer_permission_allowed():
    sb = TaxSBStub(_seed("pending"))
    r = _review(_client(sb, _REVIEWER), status="verified")
    assert r.status_code == 200, r.text


def test_cms_only_permission_is_403():
    sb = TaxSBStub(_seed("pending"))
    r = _review(_client(sb, _CMS_ONLY), status="verified")
    assert r.status_code == 403, r.text


def test_super_admin_bypasses_review_permission():
    sb = TaxSBStub(_seed("pending"))
    r = _review(_client(sb, _SUPER), status="verified")
    assert r.status_code == 200, r.text


def test_unauthenticated_is_rejected():
    sb = TaxSBStub(_seed("pending"))
    r = _review(_client(sb, user=None), status="verified")
    assert r.status_code in (401, 403), r.text


# ── Allowed transitions ────────────────────────────────────────────────


def test_pending_to_verified():
    sb = TaxSBStub(_seed("pending"))
    r = _review(_client(sb), status="verified")
    assert r.status_code == 200, r.text
    assert r.json()["row"]["trust_status"] == "verified"
    # trust_status actually updated on the underlying row
    assert sb.db["pyq_sources"][0]["trust_status"] == "verified"


def test_pending_to_rejected():
    sb = TaxSBStub(_seed("pending"))
    r = _review(_client(sb), status="rejected")
    assert r.status_code == 200, r.text
    assert r.json()["row"]["trust_status"] == "rejected"
    assert sb.db["pyq_sources"][0]["trust_status"] == "rejected"


def test_verified_to_rejected():
    sb = TaxSBStub(_seed("verified"))
    r = _review(_client(sb), status="rejected")
    assert r.status_code == 200, r.text
    assert r.json()["row"]["trust_status"] == "rejected"
    assert sb.db["pyq_sources"][0]["trust_status"] == "rejected"


def test_rejected_to_pending_requeue():
    sb = TaxSBStub(_seed("rejected"))
    r = _review(_client(sb), status="pending")
    assert r.status_code == 200, r.text
    assert r.json()["row"]["trust_status"] == "pending"
    assert sb.db["pyq_sources"][0]["trust_status"] == "pending"


# ── Blocked transitions ────────────────────────────────────────────────


def test_rejected_to_verified_blocked():
    sb = TaxSBStub(_seed("rejected"))
    r = _review(_client(sb), status="verified")
    assert r.status_code == 422, r.text
    assert "not allowed" in r.json()["detail"].lower()
    # no mutation, no audit row
    assert sb.db["pyq_sources"][0]["trust_status"] == "rejected"
    assert len(sb.db.get("admin_audit_logs", [])) == 0


def test_verified_to_pending_blocked():
    sb = TaxSBStub(_seed("verified"))
    r = _review(_client(sb), status="pending")
    assert r.status_code == 422, r.text
    assert "not allowed" in r.json()["detail"].lower()


def test_noop_pending_to_pending_blocked():
    sb = TaxSBStub(_seed("pending"))
    r = _review(_client(sb), status="pending")
    assert r.status_code == 422, r.text


def test_noop_verified_to_verified_blocked():
    sb = TaxSBStub(_seed("verified"))
    r = _review(_client(sb), status="verified")
    assert r.status_code == 422, r.text


def test_unknown_status_422():
    sb = TaxSBStub(_seed())
    r = _review(_client(sb), status="approved")
    assert r.status_code == 422, r.text


# ── Audit correctness ──────────────────────────────────────────────────


def test_audit_written_on_review():
    sb = TaxSBStub(_seed("pending"))
    r = _review(_client(sb), status="verified", reason="confirmed via official registry")
    assert r.status_code == 200, r.text
    assert r.json()["audit_id"] is not None
    logs = sb.db.get("admin_audit_logs", [])
    assert len(logs) == 1
    log = logs[0]
    assert log["action"] == "exam_intel.cms.pyq_source.review"
    assert log["entity_type"] == "pyq_source"
    assert log["entity_id"] == "src-1"
    assert log["new_value"]["from_status"] == "pending"
    assert log["new_value"]["to_status"] == "verified"
    assert log["new_value"]["reason"] == "confirmed via official registry"
    assert log["new_value"]["reviewed_by"] == "reviewer@example.com"
    assert log["actor_id"] == "rev-1"


def test_single_audit_row_on_success():
    sb = TaxSBStub(_seed("pending"))
    r = _review(_client(sb), status="verified")
    assert r.status_code == 200, r.text
    assert len(sb.db.get("admin_audit_logs", [])) == 1


# ── Concurrent modification guard ─────────────────────────────────────


class _ConflictStub(TaxSBStub):
    """Flip trust_status to a conflicting value between Python's pre-validation
    SELECT and the review RPC, simulating another writer.  The RPC detects
    trust_status != p_expected_status and raises concurrent_modification → no
    audit row, no status mutation commit."""

    def rpc(self, fn_name, params=None):
        if fn_name == "cms_review_pyq_source":
            p = params or {}
            for src in self.db.get("pyq_sources", []):
                if src.get("id") == p.get("p_source_id"):
                    src["trust_status"] = "rejected"
        return super().rpc(fn_name, params)


def test_concurrent_modification_returns_409():
    sb = _ConflictStub(_seed("pending"))
    r = _review(_client(sb), status="verified")
    assert r.status_code == 409, r.text
    # Atomicity: no false audit row.
    assert len(sb.db.get("admin_audit_logs", [])) == 0


# ── Other error cases ──────────────────────────────────────────────────


def test_unknown_source_404():
    sb = TaxSBStub(_seed())
    r = _review(_client(sb), source_id="does-not-exist", status="verified")
    assert r.status_code == 404, r.text


def test_reason_too_short_422():
    sb = TaxSBStub(_seed())
    r = _review(_client(sb), status="verified", reason="short")
    assert r.status_code == 422, r.text


# ── Direct-RPC validation (RPC authoritative without Python prechecks) ──


def _rpc_raises(sb, params: dict, expected_substr: str) -> None:
    rpc = sb.rpc("cms_review_pyq_source", params)
    raised = False
    try:
        rpc.execute()
    except Exception as exc:
        raised = True
        assert expected_substr in str(exc), f"Expected {expected_substr!r} in {str(exc)!r}"
    assert raised, f"Expected RPC to raise with {expected_substr!r} but it returned normally"
    assert len(sb.db.get("admin_audit_logs", [])) == 0, "No audit row on RPC failure"


_VALID_RPC_PARAMS = {
    "p_source_id":       "src-1",
    "p_expected_status": "pending",
    "p_target_status":   "verified",
    "p_reason":          "operator confirmed registry source",
    "p_actor_id":        "rev-1",
    "p_actor_email":     "reviewer@example.com",
}


def test_direct_rpc_rejects_invalid_transition():
    sb = TaxSBStub(_seed("rejected"))
    _rpc_raises(
        sb,
        {**_VALID_RPC_PARAMS, "p_expected_status": "rejected", "p_target_status": "verified"},
        "transition_not_allowed",
    )


def test_direct_rpc_rejects_short_reason():
    sb = TaxSBStub(_seed("pending"))
    _rpc_raises(sb, {**_VALID_RPC_PARAMS, "p_reason": "short"}, "invalid_reason")


def test_direct_rpc_rejects_null_reason():
    sb = TaxSBStub(_seed("pending"))
    _rpc_raises(sb, {**_VALID_RPC_PARAMS, "p_reason": None}, "invalid_reason")


def test_direct_rpc_rejects_whitespace_only_reason():
    sb = TaxSBStub(_seed("pending"))
    _rpc_raises(sb, {**_VALID_RPC_PARAMS, "p_reason": "   "}, "invalid_reason")


def test_direct_rpc_rejects_unknown_target_status():
    sb = TaxSBStub(_seed("pending"))
    _rpc_raises(sb, {**_VALID_RPC_PARAMS, "p_target_status": "approved"}, "invalid_target_status")


def test_direct_rpc_rejects_concurrent_modification():
    sb = TaxSBStub(_seed("verified"))
    _rpc_raises(
        sb,
        {**_VALID_RPC_PARAMS, "p_expected_status": "pending", "p_target_status": "rejected"},
        "concurrent_modification",
    )
