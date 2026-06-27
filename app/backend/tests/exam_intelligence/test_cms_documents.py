"""Admin PDF upload flow for Exam Intelligence documents.

Covers the signed-upload → complete → list → link lifecycle on top of the
shared document_assets / document_pages / text_extract foundation. Uses a
storage-capable stub (the shared SBStub has no ``.storage``).
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intel_documents as docs_api
from app.api.admin_exam_intel_cms import PERM_CMS
from app.core.auth import get_current_user
from tests.exam_intelligence.test_cms_taxonomy import TaxSBStub, _AuditFailRpcQuery, _RpcQuery

_BASE = "/api/admin/exam-intelligence-cms/documents"


class _Storage:
    def __init__(self, *, fail_download: bool = False):
        self.fail_download = fail_download

    def from_(self, _bucket):
        return self

    def create_signed_upload_url(self, path):
        return {"signed_url": f"https://storage.test/{path}?t=sig", "token": "tok-123"}

    def download(self, _path):
        if self.fail_download:
            raise RuntimeError("missing object")
        return b"%PDF-1.4 minimal fake pdf bytes"


class DocSBStub(TaxSBStub):
    def __init__(self, db=None, storage=None):
        super().__init__(db)
        self.storage = storage or _Storage()


def _client(sb: DocSBStub, *, role: str = "super_admin") -> TestClient:
    app = FastAPI()
    app.include_router(docs_api.router, prefix="/api")
    docs_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[docs_api._flag_enabled] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "admin-1", "role": role,
        "permissions": [PERM_CMS] if role != "user" else [],
    }
    return TestClient(app, raise_server_exceptions=False)


def _seed() -> dict:
    return {"exams": [{"id": "e1", "slug": "ssc-cgl", "name": "SSC CGL", "is_active": True}]}


def _upload_body(**over) -> dict:
    base = {"exam_id": "e1", "document_kind": "syllabus", "filename": "ssc-cgl-syllabus.pdf",
            "mime_type": "application/pdf", "size_bytes": 12345, "title": "SSC CGL Syllabus"}
    base.update(over)
    return base


# ── 1. upload-url mints a URL and creates an 'uploaded' admin asset ───────


def test_upload_url_returns_signed_url_and_creates_asset():
    sb = DocSBStub(_seed())
    r = _client(sb).post(f"{_BASE}/upload-url", json=_upload_body())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["upload_url"].startswith("https://storage.test/")
    assert body["document_id"]
    row = sb.db["document_assets"][0]
    assert row["scope"] == "admin_exam_intelligence"
    assert row["visibility"] == "admin_only"
    assert row["status"] == "uploaded"
    assert row["owner_user_id"] is None
    assert row["metadata"]["exam_id"] == "e1"
    assert row["processing_policy"] == "extract_text"


# ── 2. complete-upload flips to processing and enqueues text_extract ──────


def test_complete_upload_triggers_text_extract():
    sb = DocSBStub(_seed())
    up = _client(sb).post(f"{_BASE}/upload-url", json=_upload_body())
    doc_id = up.json()["document_id"]

    r = _client(sb).post(f"{_BASE}/complete-upload", json={"document_id": doc_id})
    assert r.status_code == 200, r.text
    assert r.json()["text_extract_enqueued"] is True
    asset = next(a for a in sb.db["document_assets"] if a["id"] == doc_id)
    # Status is no longer "uploaded" — extraction was attempted synchronously.
    # The fake PDF bytes are not valid, so extraction will have failed or succeeded
    # depending on the pypdf stub; either way status moves out of "uploaded".
    assert asset["status"] != "uploaded"
    assert not asset["content_hash"].startswith("pending:")  # real hash now
    jobs = [j for j in sb.db.get("document_processing_jobs", []) if j["document_id"] == doc_id]
    assert len(jobs) == 1 and jobs[0]["job_type"] == "text_extract"


# ── 3. list filters by exam ───────────────────────────────────────────────


def test_list_documents_filters_by_exam():
    sb = DocSBStub({
        **_seed(),
        "exams": [{"id": "e1"}, {"id": "e2"}],
        "document_assets": [
            {"id": "d1", "scope": "admin_exam_intelligence", "document_kind": "syllabus",
             "status": "processed", "metadata": {"exam_id": "e1"}, "storage_bucket": "b", "storage_path": "p1"},
            {"id": "d2", "scope": "admin_exam_intelligence", "document_kind": "pyq_paper",
             "status": "processed", "metadata": {"exam_id": "e2"}, "storage_bucket": "b", "storage_path": "p2"},
        ],
    })
    r = _client(sb).get(f"{_BASE}?exam_id=e1")
    assert r.status_code == 200, r.text
    ids = [d["id"] for d in r.json()["items"]]
    assert ids == ["d1"]


# ── 4. link to syllabus wires storage and keeps trust_status pending ──────


def test_link_to_syllabus_updates_row_trust_stays_pending():
    sb = DocSBStub({
        **_seed(),
        "document_assets": [
            {"id": "d1", "scope": "admin_exam_intelligence", "document_kind": "syllabus",
             "status": "processed", "metadata": {"exam_id": "e1"},
             "storage_bucket": "b", "storage_path": "admin/p1.pdf", "content_hash": "abc123"}
        ],
        "syllabus_documents": [
            {"id": "sd1", "exam_id": "e1", "document_type": "syllabus_pdf",
             "trust_status": "pending", "storage_path": None, "content_hash": None}
        ],
    })
    r = _client(sb).post(
        f"{_BASE}/d1/link-to-syllabus",
        json={"reason": "attach uploaded syllabus pdf", "syllabus_document_id": "sd1"},
    )
    assert r.status_code == 200, r.text
    sd = sb.db["syllabus_documents"][0]
    assert sd["storage_path"] == "admin/p1.pdf"
    assert sd["content_hash"] == "abc123"
    assert sd["trust_status"] == "pending"  # never auto-verified


def test_link_to_pyq_paper_sets_document_asset_id_and_source_url():
    sb = DocSBStub({
        **_seed(),
        "document_assets": [
            {"id": "d1", "scope": "admin_exam_intelligence", "document_kind": "pyq_paper",
             "status": "processed", "metadata": {"exam_id": "e1"},
             "storage_bucket": "b", "storage_path": "admin/p1.pdf", "content_hash": "abc"}
        ],
        "pyq_papers": [{"id": "pp1", "exam_id": "e1", "metadata": {}}],
    })
    r = _client(sb).post(
        f"{_BASE}/d1/link-to-pyq-paper",
        json={"reason": "attach uploaded pyq paper", "pyq_paper_id": "pp1"},
    )
    assert r.status_code == 200, r.text
    pp = sb.db["pyq_papers"][0]
    assert pp["source_document_id"] == "d1"


class _DocAuditFailSBStub(DocSBStub):
    """DocSBStub variant that uses _AuditFailRpcQuery for all RPC calls."""

    def rpc(self, fn_name, params=None):
        return _AuditFailRpcQuery(fn_name, params or {}, self.db)


class _LinkDocRaceRpcQuery(_RpcQuery):
    """Simulates a concurrent document_assets mutation occurring between the
    Python pre-check and the cms_link_document_to_pyq_paper RPC validation step.

    In production, FOR UPDATE on document_assets (migration 189) prevents this
    race.  This stub archives the document before the RPC's own validation runs.
    """

    def _exec_cms_link_document_to_pyq_paper(self):
        for doc in self._db.get("document_assets", []):
            doc["status"] = "archived"
        return super()._exec_cms_link_document_to_pyq_paper()


class _LinkDocRaceSBStub(DocSBStub):
    def rpc(self, fn_name, params=None):
        return _LinkDocRaceRpcQuery(fn_name, params or {}, self.db)


def test_link_to_pyq_paper_doc_race_returns_422_and_paper_unchanged():
    """Document archived concurrently (between Python precheck and RPC) is caught
    by the RPC's FOR UPDATE + validation step (migration 189).  The endpoint must
    return 422 with document_not_linkable / source_document_id_bad_status; the
    paper row must be unchanged and no audit row written.
    """
    sb = _LinkDocRaceSBStub({
        **_seed(),
        "document_assets": [
            {"id": "d1", "scope": "admin_exam_intelligence", "document_kind": "pyq_paper",
             "status": "processed", "metadata": {"exam_id": "e1"},
             "storage_bucket": "b", "storage_path": "admin/p1.pdf", "content_hash": "abc"},
        ],
        "pyq_papers": [{"id": "pp1", "exam_id": "e1", "metadata": {}}],
        "admin_audit_logs": [],
    })
    r = _client(sb).post(
        f"{_BASE}/d1/link-to-pyq-paper",
        json={"reason": "attach uploaded pyq paper", "pyq_paper_id": "pp1"},
    )
    # Python precheck passes (doc is 'processed'); RPC archives it before its
    # own validation → blocked with source_document_id_bad_status.
    assert r.status_code == 422, r.text
    detail = r.json().get("detail", {})
    assert "document_not_linkable" in str(detail)
    assert "source_document_id_bad_status" in str(detail)
    # Paper must be unchanged — the RPC raised before mutating.
    pp = sb.db["pyq_papers"][0]
    assert pp.get("source_document_id") is None
    assert len(sb.db["admin_audit_logs"]) == 0


def test_link_to_pyq_paper_audit_failure_returns_500_and_paper_unchanged():
    """If the DB-level audit INSERT fails, the transaction rolls back the
    pyq_papers UPDATE too.  Endpoint returns 500; source_document_id is not
    set; no audit row written.  Regression for the update-then-best-effort-audit
    pattern replaced by the atomic cms_link_document_to_pyq_paper RPC (migration 188).
    """
    sb = _DocAuditFailSBStub({
        **_seed(),
        "document_assets": [
            {"id": "d1", "scope": "admin_exam_intelligence", "document_kind": "pyq_paper",
             "status": "processed", "metadata": {"exam_id": "e1"},
             "storage_bucket": "b", "storage_path": "admin/p1.pdf", "content_hash": "abc"},
        ],
        "pyq_papers": [{"id": "pp1", "exam_id": "e1", "metadata": {}}],
        "admin_audit_logs": [],
    })
    r = _client(sb).post(
        f"{_BASE}/d1/link-to-pyq-paper",
        json={"reason": "attach uploaded pyq paper", "pyq_paper_id": "pp1"},
    )
    assert r.status_code == 500, r.text
    # Paper must be unchanged — the RPC rolled back both writes atomically.
    pp = sb.db["pyq_papers"][0]
    assert pp.get("source_document_id") is None
    assert len(sb.db["admin_audit_logs"]) == 0


def test_get_document_pages_returns_extracted_text():
    sb = DocSBStub({
        **_seed(),
        "document_assets": [
            {"id": "d1", "scope": "admin_exam_intelligence", "document_kind": "syllabus",
             "status": "processed", "metadata": {"exam_id": "e1"}, "storage_bucket": "b", "storage_path": "p1"}
        ],
        "document_pages": [
            {"id": "pg2", "document_id": "d1", "page_number": 2, "text_content": "Section B", "char_count": 9, "extraction_status": "extracted"},
            {"id": "pg1", "document_id": "d1", "page_number": 1, "text_content": "Section A", "char_count": 9, "extraction_status": "extracted"},
        ],
    })
    r = _client(sb).get(f"{_BASE}/d1/pages")
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert [p["page_number"] for p in items] == [1, 2]  # ordered
    assert items[0]["text_content"] == "Section A"


# ── 5. non-admin is blocked ───────────────────────────────────────────────


def test_non_admin_blocked_403():
    sb = DocSBStub(_seed())
    r = _client(sb, role="user").post(f"{_BASE}/upload-url", json=_upload_body())
    assert r.status_code == 403, r.text


# ── 6. non-PDF rejected at complete-upload ────────────────────────────────


def test_non_pdf_rejected_on_complete_upload():
    sb = DocSBStub({
        **_seed(),
        "document_assets": [
            {"id": "d1", "scope": "admin_exam_intelligence", "document_kind": "syllabus",
             "status": "uploaded", "mime_type": "text/plain",
             "storage_bucket": "b", "storage_path": "p1.txt", "content_hash": "pending:x"}
        ],
    })
    r = _client(sb).post(f"{_BASE}/complete-upload", json={"document_id": "d1"})
    assert r.status_code == 400, r.text
    assert "pdf" in str(r.json().get("detail")).lower()


def test_upload_url_rejects_non_pdf_mime():
    sb = DocSBStub(_seed())
    r = _client(sb).post(f"{_BASE}/upload-url", json=_upload_body(mime_type="text/plain", filename="x.txt"))
    assert r.status_code == 400, r.text


# ── 7. lifecycle / race / archive regression tests ────────────────────────


def test_complete_upload_on_archived_document_returns_409():
    """complete-upload on an archived document must 409 before any mutation."""
    sb = DocSBStub({
        **_seed(),
        "document_assets": [
            {"id": "d1", "scope": "admin_exam_intelligence", "document_kind": "syllabus",
             "status": "archived", "mime_type": "application/pdf",
             "storage_bucket": "b", "storage_path": "p1.pdf", "content_hash": "abc"}
        ],
    })
    r = _client(sb).post(f"{_BASE}/complete-upload", json={"document_id": "d1"})
    assert r.status_code == 409, r.text
    detail = r.json().get("detail", {})
    assert "archived" in str(detail).lower()
    # Asset must remain archived — not mutated.
    assert sb.db["document_assets"][0]["status"] == "archived"


def test_complete_upload_cas_race_archived_during_processing_transition():
    """If the document is archived between the status read and the processing
    update, the CAS update returns 0 rows and the endpoint returns 409."""
    class _ArchiveDuringCasSBStub(DocSBStub):
        """Archives the document_asset *before* the CAS update executes,
        simulating an archive that races past the status pre-check."""
        def table(self, name):
            return _ArchiveDuringCasQuery(name, self.db, self.storage)

    class _ArchiveDuringCasQuery(type(DocSBStub({}).table("x"))):
        def __init__(self, name, db, storage):
            super().__init__(name, db)
            self._storage = storage
        @property
        def storage(self):
            return self._storage

        def execute(self):
            # Intercept the CAS update (update with both id= and status=uploaded filters).
            if (
                self._pending_update is not None
                and self._pending_update != "__delete__"
                and "status" in (self._pending_update or {})
                and self._pending_update.get("status") == "processing"
            ):
                # Simulate archive winning the race: flip the asset to archived before CAS.
                for r in self.db.get("document_assets", []):
                    if r.get("id") == next(
                        (v for k, op, v in self.filters if k == "id" and op == "eq"), None
                    ):
                        r["status"] = "archived"
                        break
            return super().execute()

    sb = DocSBStub({
        **_seed(),
        "document_assets": [
            {"id": "d1", "scope": "admin_exam_intelligence", "document_kind": "syllabus",
             "status": "uploaded", "mime_type": "application/pdf",
             "storage_bucket": "b", "storage_path": "p1.pdf", "content_hash": "pending:x"}
        ],
    })
    # Manually replace the table method with the race stub.
    original_table = sb.table

    def racing_table(name):
        q = original_table(name)
        if name == "document_assets":
            class _RacingQ(type(q)):
                def execute(self_q):
                    if (
                        self_q._pending_update is not None
                        and self_q._pending_update != "__delete__"
                        and self_q._pending_update.get("status") == "processing"
                        and any(op == "eq" and k == "status" for k, op, _ in self_q.filters)
                    ):
                        # Archive the asset BEFORE the CAS runs — simulates the race.
                        for row in sb.db.get("document_assets", []):
                            row["status"] = "archived"
                    return super(_RacingQ, self_q).execute()
            q.__class__ = _RacingQ
        return q

    sb.table = racing_table
    r = _client(sb).post(f"{_BASE}/complete-upload", json={"document_id": "d1"})
    assert r.status_code == 409, r.text
    assert "archived" in str(r.json().get("detail", "")).lower()
    # Asset must remain archived after the race.
    assert sb.db["document_assets"][0]["status"] == "archived"


def test_archive_document_success_and_audit_written():
    """archive endpoint returns 200 and writes an audit row."""
    sb = DocSBStub({
        **_seed(),
        "document_assets": [
            {"id": "d1", "scope": "admin_exam_intelligence", "document_kind": "syllabus",
             "status": "processed", "mime_type": "application/pdf",
             "storage_bucket": "b", "storage_path": "p1.pdf", "content_hash": "abc"}
        ],
        "pyq_papers": [],
        "syllabus_documents": [],
        "document_processing_jobs": [],
        "admin_audit_logs": [],
    })
    r = _client(sb).post(f"{_BASE}/d1/archive", json={"reason": "superseded by new version"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["status"] == "archived"
    # Asset must be archived in DB.
    assert sb.db["document_assets"][0]["status"] == "archived"
    # Audit log must have been written.
    logs = sb.db.get("admin_audit_logs", [])
    assert len(logs) == 1
    assert logs[0]["action"] == "exam_intel.cms.document.archive"
    assert logs[0]["new_value"]["reason"] == "superseded by new version"
    assert "force" not in logs[0]["new_value"]


def test_archive_document_blocked_by_verified_pyq_paper():
    """Archive must 409 when a verified pyq_paper references the document."""
    sb = DocSBStub({
        **_seed(),
        "document_assets": [
            {"id": "d1", "scope": "admin_exam_intelligence", "document_kind": "pyq_paper",
             "status": "processed", "mime_type": "application/pdf",
             "storage_bucket": "b", "storage_path": "p1.pdf", "content_hash": "abc"}
        ],
        "pyq_papers": [
            {"id": "pp1", "exam_id": "e1", "source_document_id": "d1", "trust_status": "verified"}
        ],
        "syllabus_documents": [],
        "document_processing_jobs": [],
    })
    r = _client(sb).post(f"{_BASE}/d1/archive", json={"reason": "superseded by new version"})
    assert r.status_code == 409, r.text
    detail = r.json().get("detail", {})
    assert "trusted_provenance_exists" in str(detail)
    assert "pp1" in str(detail)
    # Asset must NOT be archived.
    assert sb.db["document_assets"][0]["status"] == "processed"


def test_archive_document_blocked_by_verified_syllabus_document():
    """Archive must 409 when a verified syllabus_document references the document."""
    sb = DocSBStub({
        **_seed(),
        "document_assets": [
            {"id": "d1", "scope": "admin_exam_intelligence", "document_kind": "syllabus",
             "status": "processed", "mime_type": "application/pdf",
             "storage_bucket": "b", "storage_path": "p1.pdf", "content_hash": "abc"}
        ],
        "pyq_papers": [],
        "syllabus_documents": [
            {"id": "sd1", "exam_id": "e1", "source_document_id": "d1", "trust_status": "verified"}
        ],
        "document_processing_jobs": [],
    })
    r = _client(sb).post(f"{_BASE}/d1/archive", json={"reason": "superseded by new version"})
    assert r.status_code == 409, r.text
    detail = r.json().get("detail", {})
    assert "trusted_provenance_exists" in str(detail)
    assert "sd1" in str(detail)


def test_link_to_syllabus_demotes_verified_trust_status():
    """Replacing source on a verified syllabus document must demote trust to pending."""
    sb = DocSBStub({
        **_seed(),
        "document_assets": [
            {"id": "d1", "scope": "admin_exam_intelligence", "document_kind": "syllabus",
             "status": "processed", "metadata": {"exam_id": "e1"},
             "storage_bucket": "b", "storage_path": "admin/p2.pdf", "content_hash": "newhash"}
        ],
        "syllabus_documents": [
            {"id": "sd1", "exam_id": "e1", "document_type": "syllabus_pdf",
             "trust_status": "verified", "storage_path": "old/p1.pdf", "content_hash": "oldhash"}
        ],
    })
    r = _client(sb).post(
        f"{_BASE}/d1/link-to-syllabus",
        json={"reason": "replacing with updated syllabus pdf", "syllabus_document_id": "sd1"},
    )
    assert r.status_code == 200, r.text
    sd = sb.db["syllabus_documents"][0]
    assert sd["trust_status"] == "pending", "verified syllabus_document must be demoted on source replacement"
    assert sd["source_document_id"] == "d1"
    assert sd["storage_path"] == "admin/p2.pdf"
