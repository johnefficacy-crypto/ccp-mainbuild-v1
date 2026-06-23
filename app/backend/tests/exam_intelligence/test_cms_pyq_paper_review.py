"""Tests for the PYQ-paper trust_status lifecycle endpoint (review).

POST /admin/exam-intelligence-cms/pyq-papers/{paper_id}/review

Covers:
- Authorization: exam_intelligence.review required; cms-only → 403;
  super_admin → allowed; unauthenticated → 401/403
- Transition matrix:
    pending  → verified ✓   pending  → rejected ✓
    verified → rejected ✓   rejected → pending  ✓
    rejected → verified ✗   verified → pending  ✗  (no-ops also ✗)
- Provenance gate: pending → verified blocked when source_url/source_type missing
- Audit-first: audit log written before status update; raises on audit failure
- Conditional update: 409 when trust_status changed concurrently
- 404 for unknown paper
- 422 for short reason
- 422 for completely unknown target status
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
    paper = {
        "id": "p1", "exam_id": "e1", "year": 2024,
        "trust_status": trust_status,
        "source_url": "https://upsc.gov.in/2024.pdf",
        "source_type": "official",
        **extra,
    }
    return {"pyq_papers": [paper], "admin_audit_logs": []}


def _review(client, paper_id="p1", status="verified", reason="operator verified source docs"):
    return client.post(
        f"{_BASE}/pyq-papers/{paper_id}/review",
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
    assert sb.db["pyq_papers"][0]["trust_status"] == "verified"


def test_pending_to_rejected():
    sb = TaxSBStub(_seed("pending"))
    r = _review(_client(sb), status="rejected")
    assert r.status_code == 200, r.text
    assert r.json()["row"]["trust_status"] == "rejected"


def test_verified_to_rejected():
    sb = TaxSBStub(_seed("verified"))
    r = _review(_client(sb), status="rejected")
    assert r.status_code == 200, r.text
    assert r.json()["row"]["trust_status"] == "rejected"


def test_rejected_to_pending():
    sb = TaxSBStub(_seed("rejected"))
    r = _review(_client(sb), status="pending")
    assert r.status_code == 200, r.text
    assert r.json()["row"]["trust_status"] == "pending"


# ── Blocked transitions ────────────────────────────────────────────────


def test_rejected_to_verified_blocked():
    sb = TaxSBStub(_seed("rejected"))
    r = _review(_client(sb), status="verified")
    assert r.status_code == 422, r.text
    assert "not allowed" in r.json()["detail"].lower()


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


# ── Provenance gate (pending → verified) ──────────────────────────────


def test_pending_to_verified_blocked_when_source_url_missing():
    sb = TaxSBStub(_seed("pending", source_url=None))
    r = _review(_client(sb), status="verified")
    assert r.status_code == 422, r.text
    detail = r.json()["detail"]
    assert detail["error"] == "provenance_incomplete"
    assert "source_url" in detail["blocking_fields"]


def test_pending_to_verified_blocked_when_source_type_unknown():
    sb = TaxSBStub(_seed("pending", source_type="unknown"))
    r = _review(_client(sb), status="verified")
    assert r.status_code == 422, r.text
    detail = r.json()["detail"]
    assert detail["error"] == "provenance_incomplete"
    assert "source_type" in detail["blocking_fields"]


def test_pending_to_verified_blocked_when_both_provenance_fields_missing():
    sb = TaxSBStub(_seed("pending", source_url=None, source_type="unknown"))
    r = _review(_client(sb), status="verified")
    assert r.status_code == 422, r.text
    detail = r.json()["detail"]
    assert set(detail["blocking_fields"]) == {"source_url", "source_type"}


def test_provenance_gate_does_not_apply_to_rejected():
    # pending → rejected is allowed even without provenance fields
    sb = TaxSBStub(_seed("pending", source_url=None, source_type="unknown"))
    r = _review(_client(sb), status="rejected")
    assert r.status_code == 200, r.text


# ── Audit-first correctness ────────────────────────────────────────────


def test_audit_written_before_status_update():
    sb = TaxSBStub(_seed("pending"))
    r = _review(_client(sb), status="verified", reason="confirmed via official source")
    assert r.status_code == 200, r.text
    assert r.json()["audit_id"] is not None
    logs = sb.db.get("admin_audit_logs", [])
    assert len(logs) == 1
    log = logs[0]
    assert log["action"] == "exam_intel.cms.pyq_paper.review"
    assert log["new_value"]["from_status"] == "pending"
    assert log["new_value"]["to_status"] == "verified"
    assert log["new_value"]["reason"] == "confirmed via official source"
    assert log["new_value"]["reviewed_by"] == "reviewer@example.com"
    assert log["actor_id"] == "rev-1"


# ── Concurrent modification guard ─────────────────────────────────────


class _ConflictStub(TaxSBStub):
    """Injects a concurrent status change between Python's pre-validation SELECT
    and the atomic RPC, simulating another writer acting in the window between
    the two calls.  The RPC detects trust_status != p_expected_status and raises
    concurrent_modification → neither the audit row nor the paper update commit."""

    def rpc(self, fn_name, params=None):
        if fn_name == "review_pyq_paper":
            p = params or {}
            for paper in self.db.get("pyq_papers", []):
                if paper.get("id") == p.get("p_paper_id"):
                    # Flip to a conflicting status before the RPC logic runs.
                    paper["trust_status"] = "rejected"
        return super().rpc(fn_name, params)


def test_concurrent_modification_returns_409():
    """Between Python's pre-validation SELECT and the review RPC, another writer
    changes trust_status.  The RPC raises concurrent_modification → 409, and
    crucially NO audit row is written (the transaction was rolled back)."""
    sb = _ConflictStub(_seed("pending"))
    # Python SELECT sees "pending" → passes p_expected_status="pending" to RPC.
    # _ConflictStub.rpc() flips the paper to "rejected" before _RpcQuery runs.
    # _RpcQuery finds trust_status="rejected" != "pending" → raises → 409.
    r = _review(_client(sb), status="verified")
    assert r.status_code == 409, r.text
    # Verify atomicity: no false audit row must have been written.
    assert len(sb.db.get("admin_audit_logs", [])) == 0


def test_no_false_audit_on_conflict():
    """Complement: a successful review writes exactly one audit row."""
    sb = TaxSBStub(_seed("pending"))
    r = _review(_client(sb), status="verified")
    assert r.status_code == 200, r.text
    logs = sb.db.get("admin_audit_logs", [])
    assert len(logs) == 1
    assert logs[0]["new_value"]["to_status"] == "verified"


# ── Direct-RPC validation (RPC is authoritative without Python prechecks) ─────


def _rpc_raises(sb, params: dict, expected_substr: str) -> None:
    """Call _RpcQuery.execute() directly; assert it raises and the message contains
    expected_substr; assert no audit row was written (rollback semantics)."""
    rpc = sb.rpc("review_pyq_paper", params)
    raised = False
    try:
        rpc.execute()
    except Exception as exc:
        raised = True
        assert expected_substr in str(exc), f"Expected {expected_substr!r} in {str(exc)!r}"
    assert raised, f"Expected RPC to raise with {expected_substr!r} but it returned normally"
    assert len(sb.db.get("admin_audit_logs", [])) == 0, "No audit row on RPC failure"


_VALID_RPC_PARAMS = {
    "p_paper_id":        "p1",
    "p_expected_status": "pending",
    "p_target_status":   "verified",
    "p_reason":          "operator confirmed source documents",
    "p_actor_id":        "rev-1",
    "p_actor_email":     "reviewer@example.com",
}


def test_direct_rpc_rejects_invalid_transition():
    """RPC refuses rejected→verified even when Python prechecks are bypassed."""
    sb = TaxSBStub(_seed("rejected"))
    _rpc_raises(
        sb,
        {**_VALID_RPC_PARAMS, "p_expected_status": "rejected", "p_target_status": "verified"},
        "transition_not_allowed",
    )


def test_direct_rpc_rejects_short_reason():
    """RPC refuses a reason shorter than 8 characters regardless of Pydantic."""
    sb = TaxSBStub(_seed("pending"))
    _rpc_raises(
        sb,
        {**_VALID_RPC_PARAMS, "p_reason": "short"},
        "invalid_reason",
    )


def test_direct_rpc_rejects_provenance_missing():
    """RPC refuses pending→verified when the paper's source_url is absent,
    even without the Python provenance precheck firing."""
    sb = TaxSBStub(_seed("pending", source_url=None))
    _rpc_raises(
        sb,
        _VALID_RPC_PARAMS,
        "provenance_incomplete",
    )


# ── Provenance race ────────────────────────────────────────────────────


class _ProvenanceRaceStub(TaxSBStub):
    """Simulates a concurrent CMS edit that clears source_url *after* Python's
    pre-validation SELECT passes but before the RPC acquires its lock.
    trust_status is unchanged, so the concurrent-modification guard does NOT
    fire — only the provenance re-check on the locked row catches the race."""

    def rpc(self, fn_name, params=None):
        if fn_name == "review_pyq_paper":
            p = params or {}
            for paper in self.db.get("pyq_papers", []):
                if paper.get("id") == p.get("p_paper_id"):
                    paper["source_url"] = None   # concurrent CMS edit
        return super().rpc(fn_name, params)


def test_provenance_race_no_audit_no_status_change():
    """Python SELECT sees valid source_url → precheck passes.  Between that and
    the RPC, a concurrent writer clears source_url (trust_status unchanged).
    The RPC re-checks provenance on the locked row → 422; no audit row written
    and trust_status remains 'pending'."""
    sb = _ProvenanceRaceStub(_seed("pending"))
    r = _review(_client(sb), status="verified")
    assert r.status_code == 422, r.text
    detail = r.json()["detail"]
    assert detail["error"] == "provenance_incomplete"
    assert "source_url" in detail["blocking_fields"]
    # Atomicity: no false audit row and trust_status not changed
    assert len(sb.db.get("admin_audit_logs", [])) == 0
    assert sb.db["pyq_papers"][0]["trust_status"] == "pending"


# ── Other error cases ──────────────────────────────────────────────────


def test_unknown_paper_404():
    sb = TaxSBStub(_seed())
    r = _review(_client(sb), paper_id="does-not-exist", status="verified")
    assert r.status_code == 404, r.text


def test_reason_too_short_422():
    sb = TaxSBStub(_seed())
    r = _review(_client(sb), status="verified", reason="short")
    assert r.status_code == 422, r.text
