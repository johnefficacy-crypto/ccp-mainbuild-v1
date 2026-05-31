"""Admin-only PDF upload for Exam Intelligence documents.

Replaces manual ``storage_path`` entry on syllabus_documents / pyq_papers
with a real upload flow. Reuses the library document foundation:
``document_assets`` (migration 111) for the storage shell, ``document_pages``
(migration 113) for extracted text, and the shared ``text_extract`` service
to parse PDFs. Admin-scope assets (``scope='admin_exam_intelligence'``,
``visibility='admin_only'``, ``owner_user_id IS NULL``) are service-role only
by RLS; every route here also requires the CMS permission and the
``ADMIN_STUDY_OS_ENABLED`` flag.

Flow:
  upload-url     → mint signed Storage URL + document_assets row ('uploaded')
  complete-upload→ verify hash, flip to 'processing', enqueue text_extract
  GET /{id}      → metadata + pages count + extraction status
  GET /          → list filtered by exam_id / document_kind / status
  link-to-syllabus / link-to-pyq-paper → wire the asset into the CMS rows
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.admin_exam_intel_cms import PERM_CMS, _audit, _flag_enabled, _safe_select
from app.core.auth import require_permission
from app.core.config import get_settings
from app.db.supabase_client import get_supabase_admin
from app.exam_intelligence.extraction.dispatch import (
    ExamIdentity,
    SourceKind,
    StructuralFormat,
    infer_format_from_identity,
)
from app.library import text_extract as _text_extract

logger = logging.getLogger("career_copilot.api.admin_exam_intel_documents")

router = APIRouter(
    prefix="/admin/exam-intelligence-cms/documents",
    tags=["admin-exam-intelligence-cms-documents"],
)

# document_kind values valid for admin exam-intelligence uploads (migration 111
# CHECK). Personal-library kinds (note_pdf/image/text_file) are not allowed.
ADMIN_DOC_KINDS = {"syllabus", "pyq_paper", "notification", "corrigendum", "answer_key"}

# Map an admin document_kind to a syllabus_documents.document_type (migration
# 031 CHECK) when linking.
_SYLLABUS_DOCTYPE = {
    "syllabus": "syllabus_pdf",
    "notification": "notification",
    "corrigendum": "corrigendum",
    "answer_key": "other",
    "pyq_paper": "other",
}

_PDF_MIME = "application/pdf"
_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _bucket() -> str:
    return get_settings().LIBRARY_STORAGE_BUCKET


def _max_bytes() -> int:
    return get_settings().LIBRARY_MAX_UPLOAD_MB * 1024 * 1024


def _safe_filename_fragment(filename: str) -> str:
    base = os.path.basename(filename or "")
    cleaned = _SAFE_FILENAME_RE.sub("-", base).strip("-._") or "file"
    return cleaned[:80]


def _admin_storage_path(exam_id: str, filename: str) -> str:
    today = datetime.now(timezone.utc).strftime("%Y/%m/%d")
    return f"admin-exam-intelligence/{exam_id}/{today}/{uuid4()}/{_safe_filename_fragment(filename)}"


def _sha256_hex(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def _try_download_bytes(sb, bucket: str, path: str) -> bytes | None:
    try:
        data = sb.storage.from_(bucket).download(path)
    except Exception as exc:  # noqa: BLE001
        logger.warning("admin storage download failed for %s/%s: %s", bucket, path, exc)
        return None
    return bytes(data) if data is not None else None


def _normalise_signed(signed: dict) -> tuple[str | None, str | None]:
    upload_url = signed.get("signed_url") or signed.get("signedUrl") or signed.get("signedURL")
    return upload_url, signed.get("token")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_admin_asset(sb, document_id: str) -> dict | None:
    row = _safe_select(sb, "document_assets", id=document_id)
    if not row or row.get("scope") != "admin_exam_intelligence":
        return None
    return row


def _extraction_status(sb, document_id: str) -> dict[str, Any]:
    jobs = (
        sb.table("document_processing_jobs")
        .select("id, status, job_type, error_code, error_message, finished_at, created_at")
        .eq("document_id", document_id)
        .eq("job_type", "text_extract")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
        .data
        or []
    )
    return jobs[0] if jobs else {}


def _pages_count(sb, document_id: str) -> int:
    rows = (
        sb.table("document_pages")
        .select("id")
        .eq("document_id", document_id)
        .limit(10000)
        .execute()
        .data
        or []
    )
    return len(rows)


def _shape(row: dict) -> dict:
    return {
        "id": row.get("id"),
        "scope": row.get("scope"),
        "document_kind": row.get("document_kind"),
        "title": row.get("title"),
        "original_filename": row.get("original_filename"),
        "mime_type": row.get("mime_type"),
        "file_size_bytes": row.get("file_size_bytes"),
        "storage_bucket": row.get("storage_bucket"),
        "storage_path": row.get("storage_path"),
        "content_hash": row.get("content_hash"),
        "page_count": row.get("page_count"),
        "visibility": row.get("visibility"),
        "status": row.get("status"),
        "exam_identity": row.get("exam_identity"),
        "structural_format": row.get("structural_format"),
        "source_kind": row.get("source_kind"),
        "sanitized_from_document_id": row.get("sanitized_from_document_id"),
        "metadata": row.get("metadata") or {},
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


# ── Schemas ───────────────────────────────────────────────────────────────


class DocUploadUrlRequest(BaseModel):
    exam_id: str = Field(min_length=1)
    document_kind: str = Field(min_length=1, max_length=40)
    filename: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=1, max_length=120)
    size_bytes: int = Field(ge=1)
    exam_cycle_id: str | None = None
    exam_phase_id: str | None = None
    title: str | None = Field(default=None, max_length=200)
    # Classification fields (migration 152-153)
    exam_identity: str | None = Field(default=None, max_length=60)
    structural_format: str | None = Field(default=None, max_length=60)
    source_kind: str | None = Field(default=None, max_length=40)
    sanitized_from_document_id: str | None = None


class DocCompleteUploadRequest(BaseModel):
    document_id: str = Field(min_length=1)
    client_hash: str | None = Field(default=None, max_length=128)


class LinkSyllabusRequest(BaseModel):
    reason: str = Field(..., min_length=8, max_length=500)
    syllabus_document_id: str | None = None
    document_type: str | None = Field(default=None, max_length=40)


class LinkPyqPaperRequest(BaseModel):
    reason: str = Field(..., min_length=8, max_length=500)
    pyq_paper_id: str = Field(min_length=1)


# ── Endpoints ───────────────────────────────────────────────────────────────


@router.post("/upload-url")
def create_document_upload_url(
    body: DocUploadUrlRequest,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    if body.document_kind not in ADMIN_DOC_KINDS:
        raise HTTPException(status_code=422, detail=f"document_kind must be one of {sorted(ADMIN_DOC_KINDS)}")
    if body.mime_type != _PDF_MIME:
        raise HTTPException(status_code=400, detail="Only application/pdf is accepted")
    if _extension(body.filename) != "pdf":
        raise HTTPException(status_code=400, detail="filename must be a .pdf")
    if body.size_bytes > _max_bytes():
        raise HTTPException(status_code=400, detail={"code": "file_too_large", "max_bytes": _max_bytes()})

    # Validate and coerce classification fields (migration 152-153).
    exam_identity_val: str = ExamIdentity.UNKNOWN.value
    structural_format_val: str = StructuralFormat.UNKNOWN.value
    source_kind_val: str = SourceKind.UNKNOWN.value

    if body.exam_identity:
        try:
            exam_identity_val = ExamIdentity(body.exam_identity).value
        except ValueError:
            raise HTTPException(status_code=422, detail=f"exam_identity {body.exam_identity!r} is not a valid ExamIdentity value")
        # Auto-infer structural_format from exam_identity if not overridden.
        inferred = infer_format_from_identity(ExamIdentity(exam_identity_val))
        structural_format_val = inferred.value

    if body.structural_format:
        try:
            structural_format_val = StructuralFormat(body.structural_format).value
        except ValueError:
            raise HTTPException(status_code=422, detail=f"structural_format {body.structural_format!r} is not a valid StructuralFormat value")

    if body.source_kind:
        try:
            source_kind_val = SourceKind(body.source_kind).value
        except ValueError:
            raise HTTPException(status_code=422, detail=f"source_kind {body.source_kind!r} is not a valid SourceKind value")

    sb = get_supabase_admin()
    if not _safe_select(sb, "exams", id=body.exam_id):
        raise HTTPException(status_code=422, detail="exam_id does not resolve")

    if body.sanitized_from_document_id:
        ref = _safe_select(sb, "document_assets", id=body.sanitized_from_document_id)
        if not ref:
            raise HTTPException(status_code=422, detail="sanitized_from_document_id does not resolve")

    bucket = _bucket()
    path = _admin_storage_path(body.exam_id, body.filename)
    try:
        signed = sb.storage.from_(bucket).create_signed_upload_url(path)
    except Exception as exc:  # noqa: BLE001
        logger.exception("admin create_signed_upload_url failed")
        raise HTTPException(status_code=502, detail=f"Storage error: {exc}") from exc
    upload_url, token = _normalise_signed(signed)
    if not upload_url:
        raise HTTPException(status_code=502, detail="Storage did not return a signed URL")

    asset = {
        "owner_user_id": None,
        "uploaded_by": admin.get("id"),
        "scope": "admin_exam_intelligence",
        "document_kind": body.document_kind,
        "title": body.title,
        "original_filename": body.filename,
        "mime_type": body.mime_type,
        "file_size_bytes": body.size_bytes,
        "storage_bucket": bucket,
        "storage_path": path,
        # Real hash is computed at complete-upload; the column is NOT NULL so
        # a unique placeholder holds the slot until then.
        "content_hash": f"pending:{uuid4().hex}",
        "processing_policy": "extract_text",
        "visibility": "admin_only",
        "status": "uploaded",
        "exam_identity": exam_identity_val,
        "structural_format": structural_format_val,
        "source_kind": source_kind_val,
        "sanitized_from_document_id": body.sanitized_from_document_id,
        "metadata": {
            "exam_id": body.exam_id,
            "exam_cycle_id": body.exam_cycle_id,
            "exam_phase_id": body.exam_phase_id,
            "title": body.title,
        },
    }
    inserted = sb.table("document_assets").insert(asset).execute().data or []
    row = inserted[0] if inserted else asset
    _audit(
        sb, admin, "exam_intel.cms.document.upload_url",
        entity_type="document_asset", entity_id=row.get("id"),
        new_value={
            "exam_id": body.exam_id,
            "document_kind": body.document_kind,
            "storage_path": path,
            "exam_identity": exam_identity_val,
            "structural_format": structural_format_val,
            "source_kind": source_kind_val,
        },
    )
    return {
        "document_id": row.get("id"),
        "storage_bucket": bucket,
        "storage_path": path,
        "upload_url": upload_url,
        "upload_token": token,
    }


@router.post("/complete-upload")
def complete_document_upload(
    body: DocCompleteUploadRequest,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    sb = get_supabase_admin()
    row = _load_admin_asset(sb, body.document_id)
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    if row.get("mime_type") != _PDF_MIME:
        raise HTTPException(status_code=400, detail="Only application/pdf documents can be processed")

    object_bytes = _try_download_bytes(sb, row["storage_bucket"], row["storage_path"])
    if object_bytes is not None:
        content_hash = _sha256_hex(object_bytes)
        size = len(object_bytes)
    elif body.client_hash:
        content_hash = body.client_hash.lower()
        size = row.get("file_size_bytes")
    else:
        raise HTTPException(status_code=400, detail="content_hash unavailable: storage read failed and no client_hash provided")

    patch = {"content_hash": content_hash, "file_size_bytes": size, "status": "processing"}
    sb.table("document_assets").update(patch).eq("id", row["id"]).execute()

    enqueued = False
    try:
        result = _text_extract.enqueue_text_extract_job(sb, row["id"])
        enqueued = bool(result.get("enqueued"))
    except Exception:  # noqa: BLE001
        logger.exception("admin text-extract enqueue failed for doc=%s", row["id"])

    _audit(
        sb, admin, "exam_intel.cms.document.complete_upload",
        entity_type="document_asset", entity_id=row["id"],
        new_value={"content_hash": content_hash, "enqueued": enqueued},
    )
    return {"ok": True, "document": _shape({**row, **patch}), "text_extract_enqueued": enqueued}


@router.get("/{document_id}")
def get_document(
    document_id: str,
    _admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    sb = get_supabase_admin()
    row = _load_admin_asset(sb, document_id)
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    return {
        "document": _shape(row),
        "pages_count": _pages_count(sb, document_id),
        "extraction": _extraction_status(sb, document_id),
    }


@router.get("/{document_id}/pages")
def get_document_pages(
    document_id: str,
    limit: int = Query(default=500, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Per-page extracted text for a syllabus/PYQ PDF — feeds the admin pages
    viewer (and manual syllabus_topic_mention creation in the CMS)."""
    sb = get_supabase_admin()
    if not _load_admin_asset(sb, document_id):
        raise HTTPException(status_code=404, detail="Document not found")
    rows = (
        sb.table("document_pages")
        .select("page_number, text_content, char_count, extraction_status")
        .eq("document_id", document_id)
        .order("page_number", desc=False)
        .limit(limit + offset)
        .execute()
        .data
        or []
    )
    page = rows[offset : offset + limit]
    return {"items": page, "total": len(rows), "limit": limit, "offset": offset}


@router.get("")
def list_documents(
    exam_id: str | None = Query(default=None),
    document_kind: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    sb = get_supabase_admin()
    q = sb.table("document_assets").select("*").eq("scope", "admin_exam_intelligence").order("created_at", desc=True)
    if document_kind:
        q = q.eq("document_kind", document_kind)
    if status:
        q = q.eq("status", status)
    rows = q.limit(2000).execute().data or []
    # exam_id lives in metadata (document_assets has no exam column), so it is
    # filtered in Python rather than via a JSON operator.
    if exam_id:
        rows = [r for r in rows if (r.get("metadata") or {}).get("exam_id") == exam_id]
    total = len(rows)
    page = rows[offset : offset + limit]
    return {"items": [_shape(r) for r in page], "total": total, "limit": limit, "offset": offset}


@router.post("/{document_id}/link-to-syllabus")
def link_to_syllabus(
    document_id: str,
    body: LinkSyllabusRequest,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    sb = get_supabase_admin()
    asset = _load_admin_asset(sb, document_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Document not found")
    meta = asset.get("metadata") or {}

    if body.syllabus_document_id:
        existing = _safe_select(sb, "syllabus_documents", id=body.syllabus_document_id)
        if not existing:
            raise HTTPException(status_code=404, detail="syllabus_document not found")
        # Wire storage in; never touch trust_status — it stays in the review
        # pipeline.
        patch = {
            "storage_path": asset["storage_path"],
            "content_hash": asset.get("content_hash"),
            "updated_at": _now_iso(),
        }
        updated = sb.table("syllabus_documents").update(patch).eq("id", body.syllabus_document_id).execute().data or []
        result = updated[0] if updated else existing | patch
        action = "exam_intel.cms.document.link_syllabus_update"
    else:
        new_row = {
            "exam_id": meta.get("exam_id"),
            "exam_cycle_id": meta.get("exam_cycle_id"),
            "document_type": body.document_type or _SYLLABUS_DOCTYPE.get(asset.get("document_kind"), "other"),
            "title": asset.get("title") or asset.get("original_filename"),
            "storage_path": asset["storage_path"],
            "content_hash": asset.get("content_hash"),
            "trust_status": "pending",
        }
        if not new_row["exam_id"]:
            raise HTTPException(status_code=422, detail="asset has no exam_id in metadata")
        inserted = sb.table("syllabus_documents").insert(new_row).execute().data or []
        result = inserted[0] if inserted else new_row
        action = "exam_intel.cms.document.link_syllabus_create"

    audit_id = _audit(
        sb, admin, action,
        entity_type="syllabus_document", entity_id=result.get("id"),
        new_value={"reason": body.reason, "document_asset_id": document_id},
    )
    return {"ok": True, "audit_id": audit_id, "syllabus_document": result}


@router.post("/{document_id}/link-to-pyq-paper")
def link_to_pyq_paper(
    document_id: str,
    body: LinkPyqPaperRequest,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    sb = get_supabase_admin()
    asset = _load_admin_asset(sb, document_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Document not found")
    paper = _safe_select(sb, "pyq_papers", id=body.pyq_paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="pyq_paper not found")

    meta = {**(paper.get("metadata") or {}), "document_asset_id": document_id}
    patch = {
        "metadata": meta,
        "source_url": f"storage://{asset['storage_bucket']}/{asset['storage_path']}",
        "updated_at": _now_iso(),
    }
    updated = sb.table("pyq_papers").update(patch).eq("id", body.pyq_paper_id).execute().data or []
    result = updated[0] if updated else paper | patch
    audit_id = _audit(
        sb, admin, "exam_intel.cms.document.link_pyq_paper",
        entity_type="pyq_paper", entity_id=body.pyq_paper_id,
        new_value={"reason": body.reason, "document_asset_id": document_id},
    )
    return {"ok": True, "audit_id": audit_id, "pyq_paper": result}


def _extension(filename: str) -> str:
    return (os.path.splitext(filename or "")[1] or "").lstrip(".").lower()
