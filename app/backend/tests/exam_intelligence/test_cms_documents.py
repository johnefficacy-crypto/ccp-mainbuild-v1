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
from tests.exam_intelligence.test_cms_taxonomy import TaxSBStub

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
    assert asset["status"] == "processing"
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
    assert pp["metadata"]["document_asset_id"] == "d1"
    assert pp["source_url"].startswith("storage://")


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
