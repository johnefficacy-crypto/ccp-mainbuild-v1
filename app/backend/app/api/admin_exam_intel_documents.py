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
    # Only allow completion from the initial 'uploaded' state.
    current_status = row.get("status")
    if current_status != "uploaded":
        if current_status == "archived":
            detail = {"error": "document_archived", "message": "document is archived; archive is terminal"}
        elif current_status == "processed":
            detail = {"error": "already_processed", "message": "document extraction already completed"}
        elif current_status == "processing":
            detail = {"error": "already_processing", "message": "extraction is already in progress"}
        elif current_status == "failed":
            detail = {"error": "previous_extraction_failed", "message": "use the retry endpoint to re-attempt extraction"}
        else:
            detail = {"error": "invalid_transition", "message": f"cannot complete from status={current_status!r}"}
        raise HTTPException(status_code=409, detail=detail)

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
    # CAS: only flip to processing if status is still uploaded (archive race guard).
    cas_result = (
        sb.table("document_assets")
        .update(patch)
        .eq("id", row["id"])
        .eq("status", "uploaded")
        .execute()
        .data
        or []
    )
    if not cas_result:
        # Something changed the document after our initial read (e.g. concurrent archive).
        refreshed = _load_admin_asset(sb, row["id"])
        if refreshed and refreshed.get("status") == "archived":
            raise HTTPException(status_code=409, detail={"error": "document_archived", "message": "document was archived before processing could begin"})
        raise HTTPException(status_code=409, detail={"error": "concurrent_state_change", "message": "document status changed concurrently; reload and retry"})

    enqueued = False
    job_id: str | None = None
    try:
        result = _text_extract.enqueue_text_extract_job(sb, row["id"])
        enqueued = bool(result.get("enqueued"))
        job_id = (result.get("job") or {}).get("id")
    except Exception:  # noqa: BLE001
        logger.exception("admin text-extract enqueue failed for doc=%s", row["id"])
        # Enqueue failure must not strand the document in 'processing' — a later
        # call would be rejected as already_processing with no retry path.
        # CAS rollback: only restore to 'uploaded' if we are still in 'processing'.
        # If archive won the race the row is already 'archived'; inspect the result
        # before deciding what to tell the caller.
        rollback_rows = (
            sb.table("document_assets")
            .update({"status": "uploaded"})
            .eq("id", row["id"])
            .eq("status", "processing")
            .execute()
            .data or []
        )
        if not rollback_rows:
            # CAS rollback matched 0 rows — something changed status out from under
            # us while we were handling the enqueue error.  Re-read and respond with
            # the actual terminal state so the caller is never told to retry
            # complete-upload on a document that can no longer be processed.
            refreshed = _load_admin_asset(sb, row["id"])
            if not refreshed:
                raise HTTPException(
                    status_code=409,
                    detail={"error": "concurrent_state_change", "message": "document no longer exists; it may have been deleted concurrently"},
                )
            actual_status = refreshed.get("status")
            if actual_status == "archived":
                raise HTTPException(
                    status_code=409,
                    detail={"error": "document_archived", "message": "document was archived before extraction could begin"},
                )
            raise HTTPException(
                status_code=409,
                detail={"error": "concurrent_state_change", "message": f"document status changed to {actual_status!r} concurrently; reload and retry"},
            )
        raise HTTPException(
            status_code=502,
            detail={"error": "enqueue_failed", "message": "text extraction job could not be queued; document status restored to uploaded — retry complete-upload"},
        )

    # Run extraction synchronously. Admin docs have owner_user_id=NULL and
    # scope='admin_exam_intelligence'; the service validates both.
    extraction_result: dict | None = None
    if job_id:
        try:
            extraction_result = _text_extract.run_text_extract_job(
                sb, job_id, user_id=None, admin_scope="admin_exam_intelligence"
            )
        except _text_extract.ExtractConflict:
            logger.info("admin text-extract job %s already claimed (race)", job_id)
        except Exception:  # noqa: BLE001
            logger.exception("admin text-extract run failed for doc=%s job=%s", row["id"], job_id)

    _audit(
        sb, admin, "exam_intel.cms.document.complete_upload",
        entity_type="document_asset", entity_id=row["id"],
        new_value={
            "content_hash": content_hash,
            "enqueued": enqueued,
            "extraction_attempted": job_id is not None,
        },
    )
    # Re-read from DB to return accurate post-extraction state.
    final_row = _load_admin_asset(sb, row["id"]) or {**row, **patch}
    return {
        "ok": True,
        "document": _shape(final_row),
        "text_extract_enqueued": enqueued,
    }


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
        # Wire storage in. source_document_id links the asset so the proposer
        # can find extracted document_pages via the correct asset ID.
        # Replacing the source on a verified syllabus document demotes it to
        # pending — the new PDF must be re-reviewed (mirrors PYQ link behaviour).
        patch = {
            "storage_path": asset["storage_path"],
            "content_hash": asset.get("content_hash"),
            "source_document_id": document_id,
            "updated_at": _now_iso(),
        }
        if existing.get("trust_status") == "verified":
            patch["trust_status"] = "pending"
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
            "source_document_id": document_id,
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
    """Link a document_assets row to a PYQ paper via source_document_id.

    Runs the same six document invariants as review_pyq_paper. If the paper is
    currently verified it is moved back to pending so provenance must be
    re-reviewed before the projection RPC can run.
    """
    sb = get_supabase_admin()
    asset = _load_admin_asset(sb, document_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Document not found")
    paper = _safe_select(sb, "pyq_papers", id=body.pyq_paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="pyq_paper not found")

    # Run the same document invariants as review_pyq_paper step 6c.
    # (_load_admin_asset already verified scope='admin_exam_intelligence'.)
    blocking: list[str] = []
    if asset.get("document_kind") != "pyq_paper":
        blocking.append("source_document_id_wrong_kind")
    if asset.get("status") in ("failed", "archived"):
        blocking.append("source_document_id_bad_status")
    if not asset.get("storage_bucket") or not asset.get("storage_path"):
        blocking.append("source_document_id_no_storage")
    doc_exam = (asset.get("metadata") or {}).get("exam_id")
    if doc_exam and doc_exam != paper.get("exam_id"):
        blocking.append("source_document_id_exam_mismatch")
    if blocking:
        raise HTTPException(
            status_code=422,
            detail={"error": "document_not_linkable", "blocking_fields": blocking},
        )

    was_verified = paper.get("trust_status") == "verified"
    try:
        rpc_data = sb.rpc(
            "cms_link_document_to_pyq_paper",
            {
                "p_document_id":  document_id,
                "p_paper_id":     body.pyq_paper_id,
                "p_actor_id":     admin.get("id"),
                "p_actor_email":  admin.get("email"),
                "p_reason":       body.reason,
                "p_was_verified": was_verified,
            },
        ).execute().data
    except Exception as exc:
        msg = str(exc)
        msg_lower = msg.lower()
        if "document_not_linkable" in msg_lower:
            blocking_exc: list[str] = []
            if "blocking_fields=" in msg_lower:
                fields_raw = msg_lower.split("blocking_fields=", 1)[1].split()[0].rstrip(".,")
                blocking_exc = [f for f in fields_raw.split(",") if f]
            raise HTTPException(
                status_code=422,
                detail={"error": "document_not_linkable", "blocking_fields": blocking_exc},
            ) from exc
        if "not_found" in msg_lower:
            raise HTTPException(status_code=404, detail=msg) from exc
        logger.exception("cms_link_document_to_pyq_paper RPC failed; mutation rolled back")
        raise HTTPException(
            status_code=500,
            detail="Link mutation failed; no change was recorded.",
        ) from exc
    synthetic_patch: dict = {"source_document_id": document_id}
    if was_verified:
        synthetic_patch["trust_status"] = "pending"
    return {
        "ok": True,
        "audit_id": (rpc_data or {}).get("audit_id"),
        "pyq_paper": paper | synthetic_patch,
    }


class ArchiveDocumentRequest(BaseModel):
    reason: str = Field(..., min_length=8, max_length=500)


@router.post("/{document_id}/archive")
def archive_document(
    document_id: str,
    body: ArchiveDocumentRequest,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Archive an admin exam-intelligence document.

    Blocked if a job is actively running (to avoid the runner undoing the
    archive). Blocked if verified pyq_papers or syllabus_documents reference
    this asset as their source (demote them first).
    """
    sb = get_supabase_admin()
    asset = _load_admin_asset(sb, document_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Document not found")
    if asset.get("status") == "archived":
        raise HTTPException(status_code=409, detail="Document already archived")

    # Block if a job is actively running — the runner would undo the archive.
    running_jobs = (
        sb.table("document_processing_jobs")
        .select("id")
        .eq("document_id", document_id)
        .eq("status", "running")
        .limit(1)
        .execute()
        .data or []
    )
    if running_jobs:
        raise HTTPException(
            status_code=409,
            detail={"error": "extraction_running", "message": "wait for running extraction to finish before archiving"},
        )

    # Block if verified pyq_papers reference this asset as source.
    trusted_papers = (
        sb.table("pyq_papers")
        .select("id")
        .eq("source_document_id", document_id)
        .eq("trust_status", "verified")
        .limit(50)
        .execute()
        .data or []
    )
    if trusted_papers:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "trusted_provenance_exists",
                "message": "verified pyq_papers reference this document; demote them first",
                "blocking_paper_ids": [p["id"] for p in trusted_papers],
            },
        )

    # Block if verified syllabus_documents reference this asset via source_document_id.
    trusted_syllabus = (
        sb.table("syllabus_documents")
        .select("id")
        .eq("source_document_id", document_id)
        .eq("trust_status", "verified")
        .limit(50)
        .execute()
        .data or []
    )
    if trusted_syllabus:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "trusted_provenance_exists",
                "message": "verified syllabus_documents reference this document; demote them first",
                "blocking_syllabus_ids": [s["id"] for s in trusted_syllabus],
            },
        )

    # Cancel queued jobs (running was already blocked above).
    sb.table("document_processing_jobs").update({
        "status": "failed",
        "finished_at": _now_iso(),
        "error_code": "document_archived",
        "error_message": "document was archived before extraction could run",
    }).eq("document_id", document_id).eq("status", "queued").execute()

    # Re-check for running jobs after cancelling queued ones — narrow the TOCTOU
    # window where a queued job was claimed between the first check and the cancel.
    running_after = (
        sb.table("document_processing_jobs")
        .select("id")
        .eq("document_id", document_id)
        .eq("status", "running")
        .limit(1)
        .execute()
        .data or []
    )
    if running_after:
        raise HTTPException(
            status_code=409,
            detail={"error": "extraction_running", "message": "extraction job was claimed during archive; retry after it finishes"},
        )

    sb.table("document_assets").update({"status": "archived"}).eq("id", document_id).execute()

    _audit(
        sb, admin, "exam_intel.cms.document.archive",
        entity_type="document_asset", entity_id=document_id,
        new_value={"status": "archived", "reason": body.reason},
    )
    return {"ok": True, "document_id": document_id, "status": "archived"}


def _extension(filename: str) -> str:
    return (os.path.splitext(filename or "")[1] or "").lstrip(".").lower()
