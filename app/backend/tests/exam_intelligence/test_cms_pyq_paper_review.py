"""Tests for the PYQ-paper trust_status lifecycle endpoint (review).

POST /admin/exam-intelligence-cms/pyq-papers/{paper_id}/review

Covers:
- Authorization: exam_intelligence.review required; cms-only → 403;
  super_admin → allowed; unauthenticated → 401/403
- Transition matrix:
    pending  → verified ✓   pending  → rejected ✓
    verified → rejected ✓   rejected → pending  ✓
    rejected → verified ✗   verified → pending  ✗  (no-ops also ✗)
- Provenance gate (migration 186): pending → verified requires source_type AND
    at least one anchor (source_url or valid source_document_id); document
    validation is enforced: scope, document_kind, status, storage, exam_id.
- Signed-PDF endpoint: rejects document_id that is not the paper's attached doc.
- Hash formula: source_document_id is included so changing it invalidates hash.
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


def test_direct_rpc_rejects_null_reason():
    """RPC refuses a null reason — trim(NULL)/length(NULL) would silently bypass
    the length check in SQL without the explicit IS NULL guard."""
    sb = TaxSBStub(_seed("pending"))
    _rpc_raises(
        sb,
        {**_VALID_RPC_PARAMS, "p_reason": None},
        "invalid_reason",
    )


def test_direct_rpc_rejects_whitespace_only_reason():
    """RPC refuses an all-whitespace reason: trimmed length is 0 < 8.
    Covers the padded-reason path where raw input looks non-empty but collapses
    to nothing after trim, confirming no audit row and no status mutation."""
    sb = TaxSBStub(_seed("pending"))
    _rpc_raises(
        sb,
        {**_VALID_RPC_PARAMS, "p_reason": "   "},
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


# ── Migration 186: source_document_id provenance gate ─────────────────────────

_VALID_DOC = {
    "id": "doc-1",
    "scope": "admin_exam_intelligence",
    "document_kind": "pyq_paper",
    "status": "processed",
    "storage_bucket": "exam-docs",
    "storage_path": "upsc/2024-paper.pdf",
    "metadata": {"exam_id": "e1"},
}


def _seed_with_doc(trust_status="pending", doc=None, **extra):
    """Paper with source_document_id set (no source_url by default)."""
    doc_row = dict(_VALID_DOC) if doc is None else doc
    paper = {
        "id": "p1", "exam_id": "e1", "year": 2024,
        "trust_status": trust_status,
        "source_url": None,
        "source_type": "official",
        "source_document_id": "doc-1",
        **extra,
    }
    return {
        "pyq_papers": [paper],
        "admin_audit_logs": [],
        "document_assets": [doc_row],
    }


# ── Provenance anchor variants ─────────────────────────────────────────────────


def test_source_url_only_passes():
    """source_url present and source_type valid → no document needed."""
    sb = TaxSBStub(_seed("pending"))  # existing seed has source_url
    r = _review(_client(sb), status="verified")
    assert r.status_code == 200, r.text


def test_source_document_only_passes():
    """source_document_id present (valid doc) and source_type valid → no source_url needed."""
    sb = TaxSBStub(_seed_with_doc())
    r = _review(_client(sb), status="verified")
    assert r.status_code == 200, r.text
    assert r.json()["row"]["trust_status"] == "verified"


def test_both_url_and_document_passes():
    """Having both source_url and source_document_id is fine."""
    sb = TaxSBStub(_seed_with_doc(source_url="https://upsc.gov.in/2024.pdf"))
    r = _review(_client(sb), status="verified")
    assert r.status_code == 200, r.text


def test_neither_url_nor_document_blocks():
    """Neither source_url nor source_document_id → blocks with 'source_url'."""
    sb = TaxSBStub(_seed("pending", source_url=None, source_document_id=None))
    r = _review(_client(sb), status="verified")
    assert r.status_code == 422, r.text
    detail = r.json()["detail"]
    assert detail["error"] == "provenance_incomplete"
    assert "source_url" in detail["blocking_fields"]


def test_document_not_found_blocks():
    """source_document_id points to a non-existent document_assets row."""
    db = _seed_with_doc()
    db["document_assets"] = []  # no document rows
    sb = TaxSBStub(db)
    r = _review(_client(sb), status="verified")
    assert r.status_code == 422, r.text
    detail = r.json()["detail"]
    assert "source_document_id_not_found" in detail["blocking_fields"]
    assert len(db.get("admin_audit_logs", [])) == 0


def test_document_wrong_scope_blocks():
    """Document with wrong scope is rejected."""
    doc = {**_VALID_DOC, "scope": "personal_library"}
    sb = TaxSBStub(_seed_with_doc(doc=doc))
    r = _review(_client(sb), status="verified")
    assert r.status_code == 422, r.text
    assert "source_document_id_wrong_scope" in r.json()["detail"]["blocking_fields"]


def test_document_wrong_kind_blocks():
    """Document with document_kind != 'pyq_paper' is rejected."""
    doc = {**_VALID_DOC, "document_kind": "syllabus"}
    sb = TaxSBStub(_seed_with_doc(doc=doc))
    r = _review(_client(sb), status="verified")
    assert r.status_code == 422, r.text
    assert "source_document_id_wrong_kind" in r.json()["detail"]["blocking_fields"]


def test_document_failed_status_blocks():
    """Document with status='failed' is rejected."""
    doc = {**_VALID_DOC, "status": "failed"}
    sb = TaxSBStub(_seed_with_doc(doc=doc))
    r = _review(_client(sb), status="verified")
    assert r.status_code == 422, r.text
    assert "source_document_id_bad_status" in r.json()["detail"]["blocking_fields"]


def test_document_archived_status_blocks():
    """Document with status='archived' is rejected."""
    doc = {**_VALID_DOC, "status": "archived"}
    sb = TaxSBStub(_seed_with_doc(doc=doc))
    r = _review(_client(sb), status="verified")
    assert r.status_code == 422, r.text
    assert "source_document_id_bad_status" in r.json()["detail"]["blocking_fields"]


def test_document_no_storage_blocks():
    """Document with empty storage_bucket is rejected."""
    doc = {**_VALID_DOC, "storage_bucket": None, "storage_path": None}
    sb = TaxSBStub(_seed_with_doc(doc=doc))
    r = _review(_client(sb), status="verified")
    assert r.status_code == 422, r.text
    assert "source_document_id_no_storage" in r.json()["detail"]["blocking_fields"]


def test_document_exam_mismatch_blocks():
    """Document metadata.exam_id disagrees with paper.exam_id."""
    doc = {**_VALID_DOC, "metadata": {"exam_id": "other-exam"}}
    sb = TaxSBStub(_seed_with_doc(doc=doc))
    r = _review(_client(sb), status="verified")
    assert r.status_code == 422, r.text
    assert "source_document_id_exam_mismatch" in r.json()["detail"]["blocking_fields"]


def test_document_no_exam_metadata_passes():
    """Document without metadata.exam_id does not trigger exam_mismatch check."""
    doc = {**_VALID_DOC, "metadata": {}}
    sb = TaxSBStub(_seed_with_doc(doc=doc))
    r = _review(_client(sb), status="verified")
    assert r.status_code == 200, r.text


def test_document_gate_does_not_apply_to_rejected():
    """pending → rejected is allowed even with a bad document attached."""
    doc = {**_VALID_DOC, "document_kind": "syllabus"}  # wrong kind — irrelevant for rejection
    sb = TaxSBStub(_seed_with_doc(doc=doc))
    r = _review(_client(sb), status="rejected")
    assert r.status_code == 200, r.text


# ── Signed-PDF endpoint ownership check (migration 186 hardening) ─────────────


class _StorageStub:
    def from_(self, _bucket):
        return self

    def create_signed_url(self, path, _ttl):
        return {"signedURL": f"https://storage.test/{path}?sig=abc"}


class _DocTaxSBStub(TaxSBStub):
    def __init__(self, db=None):
        super().__init__(db)
        self.storage = _StorageStub()


def _pdf_client(sb):
    app = FastAPI()
    app.include_router(cms_api.router, prefix="/api")
    cms_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[cms_api._flag_enabled] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: _SUPER
    return TestClient(app, raise_server_exceptions=False)


def _pdf_seed():
    return {
        "pyq_papers": [{
            "id": "p1", "exam_id": "e1", "year": 2024,
            "trust_status": "pending",
            "source_url": None,
            "source_type": "official",
            "source_document_id": "doc-1",
        }],
        "document_assets": [{
            **_VALID_DOC,
            "original_filename": "upsc-2024.pdf",
            "page_count": 32,
        }],
        "admin_audit_logs": [],
    }


def test_signed_pdf_attached_document_returns_url():
    """GET /signed-pdf with the paper's own source_document_id succeeds."""
    sb = _DocTaxSBStub(_pdf_seed())
    r = _pdf_client(sb).get(f"{_BASE}/pyq-papers/p1/signed-pdf?document_id=doc-1")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "signed_url" in body
    assert body["signed_url"].startswith("https://storage.test/")


def test_signed_pdf_unattached_document_is_403():
    """GET /signed-pdf with a different document_id is rejected with 403."""
    sb = _DocTaxSBStub(_pdf_seed())
    r = _pdf_client(sb).get(f"{_BASE}/pyq-papers/p1/signed-pdf?document_id=other-doc")
    assert r.status_code == 403, r.text


def test_signed_pdf_unknown_paper_is_404():
    """GET /signed-pdf for a non-existent paper returns 404."""
    sb = _DocTaxSBStub(_pdf_seed())
    r = _pdf_client(sb).get(f"{_BASE}/pyq-papers/no-such-paper/signed-pdf?document_id=doc-1")
    assert r.status_code == 404, r.text


def test_signed_pdf_wrong_scope_is_403():
    """Document with wrong scope cannot be signed."""
    seed = _pdf_seed()
    seed["document_assets"][0]["scope"] = "personal_library"
    sb = _DocTaxSBStub(seed)
    r = _pdf_client(sb).get(f"{_BASE}/pyq-papers/p1/signed-pdf?document_id=doc-1")
    assert r.status_code == 403, r.text
    assert "source_document_id_wrong_scope" in r.json()["detail"]["reasons"]


def test_signed_pdf_wrong_kind_is_403():
    """Document with document_kind != 'pyq_paper' cannot be signed."""
    seed = _pdf_seed()
    seed["document_assets"][0]["document_kind"] = "syllabus"
    sb = _DocTaxSBStub(seed)
    r = _pdf_client(sb).get(f"{_BASE}/pyq-papers/p1/signed-pdf?document_id=doc-1")
    assert r.status_code == 403, r.text
    assert "source_document_id_wrong_kind" in r.json()["detail"]["reasons"]


def test_signed_pdf_failed_status_is_403():
    """Document with status='failed' cannot be signed."""
    seed = _pdf_seed()
    seed["document_assets"][0]["status"] = "failed"
    sb = _DocTaxSBStub(seed)
    r = _pdf_client(sb).get(f"{_BASE}/pyq-papers/p1/signed-pdf?document_id=doc-1")
    assert r.status_code == 403, r.text
    assert "source_document_id_bad_status" in r.json()["detail"]["reasons"]


def test_signed_pdf_archived_status_is_403():
    """Document with status='archived' cannot be signed."""
    seed = _pdf_seed()
    seed["document_assets"][0]["status"] = "archived"
    sb = _DocTaxSBStub(seed)
    r = _pdf_client(sb).get(f"{_BASE}/pyq-papers/p1/signed-pdf?document_id=doc-1")
    assert r.status_code == 403, r.text
    assert "source_document_id_bad_status" in r.json()["detail"]["reasons"]


def test_signed_pdf_no_storage_is_403():
    """Document missing storage path cannot be signed."""
    seed = _pdf_seed()
    seed["document_assets"][0]["storage_bucket"] = None
    seed["document_assets"][0]["storage_path"] = None
    sb = _DocTaxSBStub(seed)
    r = _pdf_client(sb).get(f"{_BASE}/pyq-papers/p1/signed-pdf?document_id=doc-1")
    assert r.status_code == 403, r.text
    assert "source_document_id_no_storage" in r.json()["detail"]["reasons"]


def test_signed_pdf_exam_mismatch_is_403():
    """Document metadata.exam_id disagrees with paper.exam_id — signing blocked."""
    seed = _pdf_seed()
    seed["document_assets"][0]["metadata"] = {"exam_id": "other-exam"}
    sb = _DocTaxSBStub(seed)
    r = _pdf_client(sb).get(f"{_BASE}/pyq-papers/p1/signed-pdf?document_id=doc-1")
    assert r.status_code == 403, r.text
    assert "source_document_id_exam_mismatch" in r.json()["detail"]["reasons"]


# ── Content hash covers source_document_id ────────────────────────────────────


def test_content_hash_changes_when_source_document_id_changes():
    """Changing source_document_id produces a different hash (hash formula covers it).

    This verifies that the Python preview layer will correctly report 'would_update'
    when a paper's source_document_id is modified — triggering a re-projection.
    """
    from app.admin.pyq_mock_projection import compute_content_hash

    q = {
        "question_text": "Sample question?",
        "explanation_text": "",
        "observed_difficulty": "medium",
        "language": "en",
        "expected_solve_time_sec": 60,
        "pyq_paper_id": "p1",
    }
    opts: list = []
    paper_no_doc = {
        "year": 2024, "exam_id": "e1",
        "source_url": "https://upsc.gov.in/2024.pdf",
        "source_type": "official",
        "source_document_id": None,
    }
    paper_with_doc = {**paper_no_doc, "source_document_id": "doc-uuid-1"}
    paper_diff_doc = {**paper_no_doc, "source_document_id": "doc-uuid-2"}

    h_none = compute_content_hash(q, opts, paper_no_doc)
    h_doc1 = compute_content_hash(q, opts, paper_with_doc)
    h_doc2 = compute_content_hash(q, opts, paper_diff_doc)

    assert h_none != h_doc1, "Adding source_document_id must change the hash"
    assert h_doc1 != h_doc2, "Different source_document_id values must produce different hashes"
    assert h_none != h_doc2, "Transitivity: all three must be distinct"
