"""Admin Exam Intelligence CMS — Phase 4 full-lifecycle CRUD.

The existing ``admin_exam_intelligence`` router (PR5) handles the
**review queue** for already-existing rows. This router adds the
**creation** side: admin can land new exam families, exams, cycles,
phases, syllabus documents, PYQ papers/questions/options, topic
coverage, and policy updates.

Per the spec's answered open question §12 #4: **CMS feeds the review
queue — nothing is auto-published**. So:

- Tables with ``reviewer_status`` (syllabus_topic_mentions,
  pyq_questions, exam_topic_coverage, exam_policy_updates) land at
  ``'pending'`` regardless of what the operator sends.
- Tables with ``trust_status`` (syllabus_documents, pyq_papers) land at
  ``'pending'`` regardless of what the operator sends.
- Tables with neither (exam_families, exams, exam_cycles, exam_phases,
  pyq_options) are admin-only schemas with no aspirant review surface;
  they save with whatever ``is_active``/``status`` the admin chooses.

Every write inserts an ``admin_audit_logs`` row. The same
``ADMIN_STUDY_OS_ENABLED`` env flag gates this router so the whole
Study OS admin layer toggles together.

All endpoints are gated by ``exam_intelligence.cms`` permission, with
``super_admin`` bypass (matching the rest of the admin surface). We
deliberately do NOT reuse ``exam_intelligence.review`` because the
review-queue role and the lifecycle-creator role should be separable.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.core.auth import require_permission
from app.core.config import get_settings
from app.db.supabase_client import get_supabase_admin
from app.exam_intelligence.diagnostics import (
    find_orphan_questions,
    find_stuck_documents,
    find_stuck_text_extract_jobs,
)
from app.exam_intelligence.lookup import invalidate_exam_lookup_cache
from app.exam_intelligence.option_normalize import option_hash, question_hash

logger = logging.getLogger("career_copilot.api.admin_exam_intel_cms")

router = APIRouter(prefix="/admin/exam-intelligence-cms", tags=["admin-exam-intelligence-cms"])

PERM_CMS = "exam_intelligence.cms"


# ─── Helpers (mirror admin_study_os patterns) ─────────────────────────────


def _flag_enabled() -> None:
    if not get_settings().ADMIN_STUDY_OS_ENABLED:
        raise HTTPException(
            status_code=404,
            detail="admin.study_os.enabled is off",
        )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _audit(
    supabase,
    actor: dict,
    action: str,
    *,
    entity_type: str,
    entity_id: str | None = None,
    new_value: Any = None,
    notes: str = "admin_exam_intel_cms",
) -> str | None:
    try:
        rows = (
            supabase.table("admin_audit_logs")
            .insert(
                {
                    "actor_id": actor.get("id"),
                    "actor_email": actor.get("email"),
                    "action": action,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "new_value": new_value,
                    "notes": notes,
                }
            )
            .execute()
            .data
            or []
        )
        return rows[0].get("id") if rows else None
    except Exception:  # noqa: BLE001
        logger.exception("audit log insert failed (admin_exam_intel_cms)")
        return None


def _safe_select(supabase, table: str, **filters):
    try:
        q = supabase.table(table).select("*").limit(1)
        for k, v in filters.items():
            q = q.eq(k, v)
        return (q.execute().data or [None])[0]
    except Exception:  # noqa: BLE001
        return None


class WriteEnvelope(BaseModel):
    """Standard write-body shape used by every CMS endpoint."""

    reason: str = Field(..., min_length=8, max_length=500)
    payload: dict[str, Any] = Field(default_factory=dict)


# ════════════════════════════════════════════════════════════════════════
#  Exam families
# ════════════════════════════════════════════════════════════════════════


_FAMILY_FIELDS = {"slug", "name", "description", "is_active", "metadata"}


@router.get("/exam-families")
def list_exam_families(
    is_active: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    q = (
        supabase.table("exam_families")
        .select("id, slug, name, description, is_active, metadata, created_at, updated_at", count="exact")
        .order("created_at", desc=True)
    )
    if is_active is not None:
        q = q.eq("is_active", is_active)
    try:
        res = q.range(offset, offset + limit - 1).execute()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"List failed: {exc}")
    return {"items": res.data or [], "total": getattr(res, "count", None), "limit": limit, "offset": offset}


@router.post("/exam-families")
def create_exam_family(
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    row = {k: v for k, v in body.payload.items() if k in _FAMILY_FIELDS}
    if not row.get("slug") or not row.get("name"):
        raise HTTPException(status_code=422, detail="slug and name are required")
    try:
        inserted = supabase.table("exam_families").insert(row).execute().data or []
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=409, detail=f"Insert failed: {exc}")
    if not inserted:
        raise HTTPException(status_code=500, detail="No row returned from insert")
    new = inserted[0]
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.family.create",
        entity_type="exam_family", entity_id=new.get("id"),
        new_value={"reason": body.reason, "row": new},
    )
    return {"ok": True, "audit_id": audit_id, "row": new}


@router.patch("/exam-families/{family_id}")
def update_exam_family(
    family_id: str,
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    existing = _safe_select(supabase, "exam_families", id=family_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Exam family not found")
    patch = {k: v for k, v in body.payload.items() if k in _FAMILY_FIELDS}
    if not patch:
        raise HTTPException(status_code=422, detail="No allowed fields in payload")
    patch["updated_at"] = _now_iso()
    try:
        updated = (
            supabase.table("exam_families").update(patch).eq("id", family_id).execute().data or []
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=409, detail=f"Update failed: {exc}")
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.family.update",
        entity_type="exam_family", entity_id=family_id,
        new_value={"reason": body.reason, "patch": patch, "previous": existing},
    )
    return {"ok": True, "audit_id": audit_id, "row": updated[0] if updated else existing | patch}


@router.delete("/exam-families/{family_id}")
def soft_delete_exam_family(
    family_id: str,
    reason: str = Query(..., min_length=8, max_length=500),
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Soft-delete by flipping ``is_active=false``. We never hard-delete
    because child exams may still FK-reference this row."""
    supabase = get_supabase_admin()
    existing = _safe_select(supabase, "exam_families", id=family_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Exam family not found")
    supabase.table("exam_families").update(
        {"is_active": False, "updated_at": _now_iso()}
    ).eq("id", family_id).execute()
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.family.soft_delete",
        entity_type="exam_family", entity_id=family_id,
        new_value={"reason": reason, "previous_is_active": existing.get("is_active")},
    )
    return {"ok": True, "audit_id": audit_id, "id": family_id, "is_active": False}


# ════════════════════════════════════════════════════════════════════════
#  Exams
# ════════════════════════════════════════════════════════════════════════


_EXAM_FIELDS = {
    "exam_family_id", "name", "exam_type", "default_difficulty_level",
    "description", "is_active", "metadata", "conducting_organization_id",
}
_EXAM_TYPES = ("recruitment", "entrance", "certification", "opportunity", "other")


def _exam_slug(name: str, org: dict | None) -> str:
    from app.common.strings import slugify
    if org and org.get("type") == "state_psc" and org.get("state"):
        return slugify(org["state"]) + "-" + slugify(name)
    return slugify(name)


@router.get("/exams")
def list_exams(
    is_active: bool | None = Query(default=None),
    exam_family_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    q = supabase.table("exams").select(
        "id, exam_family_id, slug, name, exam_type, default_difficulty_level, description, is_active, metadata, created_at, updated_at",
        count="exact",
    ).order("created_at", desc=True)
    if is_active is not None:
        q = q.eq("is_active", is_active)
    if exam_family_id:
        q = q.eq("exam_family_id", exam_family_id)
    res = q.range(offset, offset + limit - 1).execute()
    return {"items": res.data or [], "total": getattr(res, "count", None), "limit": limit, "offset": offset}


@router.post("/exams")
def create_exam(
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    row = {k: v for k, v in body.payload.items() if k in _EXAM_FIELDS}
    if not row.get("name"):
        raise HTTPException(status_code=422, detail="name is required")
    if row.get("exam_type") and row["exam_type"] not in _EXAM_TYPES:
        raise HTTPException(status_code=422, detail=f"exam_type must be one of {_EXAM_TYPES}")
    if row.get("exam_family_id") and not _safe_select(supabase, "exam_families", id=row["exam_family_id"]):
        raise HTTPException(status_code=422, detail="exam_family_id does not resolve")

    # Resolve conducting org for slug generation (nullable — no 422 if absent).
    org: dict | None = None
    if row.get("conducting_organization_id"):
        org = _safe_select(supabase, "organizations", id=row["conducting_organization_id"])

    slug = _exam_slug(row["name"], org)
    row["slug"] = slug  # payload-supplied slug is always overwritten

    try:
        inserted = supabase.table("exams").insert(row).execute().data or []
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=409, detail=f"Slug '{slug}' already exists: {exc}")
    new = inserted[0] if inserted else row
    invalidate_exam_lookup_cache()
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.exam.create",
        entity_type="exam", entity_id=new.get("id"),
        new_value={"reason": body.reason, "row": new},
    )
    return {"ok": True, "audit_id": audit_id, "row": new}


@router.patch("/exams/{exam_id}")
def update_exam(
    exam_id: str,
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    existing = _safe_select(supabase, "exams", id=exam_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Exam not found")
    patch = {k: v for k, v in body.payload.items() if k in _EXAM_FIELDS}
    if not patch:
        raise HTTPException(status_code=422, detail="No allowed fields in payload")
    patch["updated_at"] = _now_iso()
    updated = supabase.table("exams").update(patch).eq("id", exam_id).execute().data or []
    invalidate_exam_lookup_cache()
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.exam.update",
        entity_type="exam", entity_id=exam_id,
        new_value={"reason": body.reason, "patch": patch, "previous": existing},
    )
    return {"ok": True, "audit_id": audit_id, "row": updated[0] if updated else existing | patch}


@router.delete("/exams/{exam_id}")
def soft_delete_exam(
    exam_id: str,
    reason: str = Query(..., min_length=8, max_length=500),
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    existing = _safe_select(supabase, "exams", id=exam_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Exam not found")
    supabase.table("exams").update({"is_active": False, "updated_at": _now_iso()}).eq("id", exam_id).execute()
    invalidate_exam_lookup_cache()
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.exam.soft_delete",
        entity_type="exam", entity_id=exam_id,
        new_value={"reason": reason, "previous_is_active": existing.get("is_active")},
    )
    return {"ok": True, "audit_id": audit_id, "id": exam_id, "is_active": False}


# ════════════════════════════════════════════════════════════════════════
#  Exam cycles
# ════════════════════════════════════════════════════════════════════════


_CYCLE_FIELDS = {
    "exam_id", "year", "cycle_name", "status", "notification_date",
    "application_start", "application_end", "exam_start", "exam_end",
    "source_url", "metadata",
}
_CYCLE_STATUSES = ("expected", "open", "active", "closed", "completed", "cancelled")


@router.get("/exam-cycles")
def list_cycles(
    exam_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    year: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    q = supabase.table("exam_cycles").select("*", count="exact").order("year", desc=True)
    if exam_id:
        q = q.eq("exam_id", exam_id)
    if status:
        q = q.eq("status", status)
    if year:
        q = q.eq("year", year)
    res = q.range(offset, offset + limit - 1).execute()
    return {"items": res.data or [], "total": getattr(res, "count", None), "limit": limit, "offset": offset}


@router.post("/exam-cycles")
def create_cycle(
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    row = {k: v for k, v in body.payload.items() if k in _CYCLE_FIELDS}
    if not row.get("exam_id") or not row.get("year") or not row.get("cycle_name"):
        raise HTTPException(status_code=422, detail="exam_id, year, cycle_name are required")
    if row.get("status") and row["status"] not in _CYCLE_STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {_CYCLE_STATUSES}")
    if not _safe_select(supabase, "exams", id=row["exam_id"]):
        raise HTTPException(status_code=422, detail="exam_id does not resolve")
    try:
        inserted = supabase.table("exam_cycles").insert(row).execute().data or []
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=409, detail=f"Insert failed: {exc}")
    new = inserted[0] if inserted else row
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.cycle.create",
        entity_type="exam_cycle", entity_id=new.get("id"),
        new_value={"reason": body.reason, "row": new},
    )
    return {"ok": True, "audit_id": audit_id, "row": new}


@router.patch("/exam-cycles/{cycle_id}")
def update_cycle(
    cycle_id: str,
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    existing = _safe_select(supabase, "exam_cycles", id=cycle_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Cycle not found")
    patch = {k: v for k, v in body.payload.items() if k in _CYCLE_FIELDS}
    if not patch:
        raise HTTPException(status_code=422, detail="No allowed fields in payload")
    if patch.get("status") and patch["status"] not in _CYCLE_STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {_CYCLE_STATUSES}")
    patch["updated_at"] = _now_iso()
    updated = supabase.table("exam_cycles").update(patch).eq("id", cycle_id).execute().data or []
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.cycle.update",
        entity_type="exam_cycle", entity_id=cycle_id,
        new_value={"reason": body.reason, "patch": patch, "previous": existing},
    )
    return {"ok": True, "audit_id": audit_id, "row": updated[0] if updated else existing | patch}


# ════════════════════════════════════════════════════════════════════════
#  Exam phases
# ════════════════════════════════════════════════════════════════════════


_PHASE_FIELDS = {
    "exam_id", "exam_cycle_id", "phase_name", "phase_slug", "phase_order",
    "mode", "duration_mins", "total_questions", "total_marks",
    "negative_marking", "status", "metadata",
    "phase_start", "phase_end",
}
_PHASE_STATUSES = ("expected", "active", "completed", "cancelled")


@router.get("/exam-phases")
def list_phases(
    exam_id: str | None = Query(default=None),
    exam_cycle_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    q = supabase.table("exam_phases").select("*", count="exact").order("phase_order", desc=False)
    if exam_id:
        q = q.eq("exam_id", exam_id)
    if exam_cycle_id:
        q = q.eq("exam_cycle_id", exam_cycle_id)
    res = q.range(offset, offset + limit - 1).execute()
    return {"items": res.data or [], "total": getattr(res, "count", None), "limit": limit, "offset": offset}


@router.post("/exam-phases")
def create_phase(
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    row = {k: v for k, v in body.payload.items() if k in _PHASE_FIELDS}
    if not row.get("exam_id") or not row.get("phase_name") or not row.get("phase_slug"):
        raise HTTPException(status_code=422, detail="exam_id, phase_name, phase_slug are required")
    if row.get("status") and row["status"] not in _PHASE_STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {_PHASE_STATUSES}")
    inserted = supabase.table("exam_phases").insert(row).execute().data or []
    new = inserted[0] if inserted else row
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.phase.create",
        entity_type="exam_phase", entity_id=new.get("id"),
        new_value={"reason": body.reason, "row": new},
    )
    return {"ok": True, "audit_id": audit_id, "row": new}


@router.patch("/exam-phases/{phase_id}")
def update_phase(
    phase_id: str,
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    existing = _safe_select(supabase, "exam_phases", id=phase_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Phase not found")
    patch = {k: v for k, v in body.payload.items() if k in _PHASE_FIELDS}
    if not patch:
        raise HTTPException(status_code=422, detail="No allowed fields in payload")
    patch["updated_at"] = _now_iso()
    updated = supabase.table("exam_phases").update(patch).eq("id", phase_id).execute().data or []
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.phase.update",
        entity_type="exam_phase", entity_id=phase_id,
        new_value={"reason": body.reason, "patch": patch, "previous": existing},
    )
    return {"ok": True, "audit_id": audit_id, "row": updated[0] if updated else existing | patch}


# ════════════════════════════════════════════════════════════════════════
#  Syllabus documents — created at trust_status='pending'
# ════════════════════════════════════════════════════════════════════════


_DOC_FIELDS = {
    "exam_id", "exam_cycle_id", "source_id", "document_type", "title",
    "source_url", "storage_path", "content_hash", "published_at",
    "fetched_at", "metadata",
}
_DOC_TYPES = (
    "notification", "syllabus_pdf", "official_page", "pattern_notice",
    "corrigendum", "other",
)


@router.get("/syllabus-documents")
def list_syllabus_documents(
    exam_id: str | None = Query(default=None),
    trust_status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    q = supabase.table("syllabus_documents").select("*", count="exact").order("created_at", desc=True)
    if exam_id:
        q = q.eq("exam_id", exam_id)
    if trust_status:
        q = q.eq("trust_status", trust_status)
    res = q.range(offset, offset + limit - 1).execute()
    return {"items": res.data or [], "total": getattr(res, "count", None), "limit": limit, "offset": offset}


@router.post("/syllabus-documents")
def create_syllabus_document(
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """CMS feeds the review queue — trust_status forced to 'pending'.

    Operators promote rows to verified via the existing review queue,
    not here. This keeps the official-verification ledger honest about
    who reviewed a document and when."""
    supabase = get_supabase_admin()
    row = {k: v for k, v in body.payload.items() if k in _DOC_FIELDS}
    if not row.get("exam_id") or not row.get("document_type") or not row.get("title"):
        raise HTTPException(status_code=422, detail="exam_id, document_type, title are required")
    if row["document_type"] not in _DOC_TYPES:
        raise HTTPException(status_code=422, detail=f"document_type must be one of {_DOC_TYPES}")
    row["trust_status"] = "pending"  # spec §12 #4 — no auto-publish
    inserted = supabase.table("syllabus_documents").insert(row).execute().data or []
    new = inserted[0] if inserted else row
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.syllabus_document.create",
        entity_type="syllabus_document", entity_id=new.get("id"),
        new_value={"reason": body.reason, "row": new},
    )
    return {"ok": True, "audit_id": audit_id, "row": new}


# ════════════════════════════════════════════════════════════════════════
#  PYQ papers — created at trust_status='pending'
# ════════════════════════════════════════════════════════════════════════


_PAPER_FIELDS = {
    "pyq_source_id", "exam_id", "exam_cycle_id", "exam_phase_id",
    "year", "paper_date", "shift", "paper_code", "source_url",
    "source_type", "content_hash", "metadata",
}
_PAPER_SOURCE_TYPES = ("official", "memory_based", "coaching", "community", "aggregator", "unknown")


@router.get("/pyq-papers")
def list_pyq_papers(
    exam_id: str | None = Query(default=None),
    year: int | None = Query(default=None),
    trust_status: str | None = Query(default=None),
    exam_cycle_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    q = supabase.table("pyq_papers").select("*", count="exact").order("year", desc=True)
    if exam_id:
        q = q.eq("exam_id", exam_id)
    if year:
        q = q.eq("year", year)
    if trust_status:
        q = q.eq("trust_status", trust_status)
    if exam_cycle_id:
        q = q.eq("exam_cycle_id", exam_cycle_id)
    res = q.range(offset, offset + limit - 1).execute()
    return {"items": res.data or [], "total": getattr(res, "count", None), "limit": limit, "offset": offset}


@router.get("/pyq-papers/{paper_id}")
def get_pyq_paper(
    paper_id: str,
    _admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    paper = _safe_select(supabase, "pyq_papers", id=paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="pyq_paper not found")
    return paper


@router.post("/pyq-papers")
def create_pyq_paper(
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    row = {k: v for k, v in body.payload.items() if k in _PAPER_FIELDS}
    if not row.get("exam_id") or not row.get("year"):
        raise HTTPException(status_code=422, detail="exam_id and year are required")
    if row.get("source_type") and row["source_type"] not in _PAPER_SOURCE_TYPES:
        raise HTTPException(status_code=422, detail=f"source_type must be one of {_PAPER_SOURCE_TYPES}")
    row["trust_status"] = "pending"
    inserted = supabase.table("pyq_papers").insert(row).execute().data or []
    new = inserted[0] if inserted else row
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.pyq_paper.create",
        entity_type="pyq_paper", entity_id=new.get("id"),
        new_value={"reason": body.reason, "row": new},
    )
    return {"ok": True, "audit_id": audit_id, "row": new}


@router.patch("/pyq-papers/{paper_id}")
def update_pyq_paper(
    paper_id: str,
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Curate an existing PYQ paper. Enum-validated; lifecycle stays
    where it is (trust_status moves through the review queue, not here)."""
    supabase = get_supabase_admin()
    existing = _safe_select(supabase, "pyq_papers", id=paper_id)
    if not existing:
        raise HTTPException(status_code=404, detail="pyq_paper not found")
    patch = {k: v for k, v in body.payload.items() if k in _PAPER_FIELDS}
    if not patch:
        raise HTTPException(status_code=422, detail="No allowed fields in payload")
    if patch.get("source_type") and patch["source_type"] not in _PAPER_SOURCE_TYPES:
        raise HTTPException(status_code=422, detail=f"source_type must be one of {_PAPER_SOURCE_TYPES}")
    updated = supabase.table("pyq_papers").update(patch).eq("id", paper_id).execute().data or []
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.pyq_paper.update",
        entity_type="pyq_paper", entity_id=paper_id,
        new_value={"reason": body.reason, "patch": patch, "previous": existing},
    )
    return {"ok": True, "audit_id": audit_id, "row": updated[0] if updated else existing | patch}


# ════════════════════════════════════════════════════════════════════════
#  PYQ paper workspace sub-endpoints (PR4)
# ════════════════════════════════════════════════════════════════════════


@router.get("/pyq-papers/{paper_id}/progress")
def pyq_paper_progress(
    paper_id: str,
    _admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Return question counts, missing list, and by-status breakdown for a paper.

    ``total_expected`` uses ``metadata.expected_question_count`` if set on the
    paper row; otherwise falls back to max(question_number) present.
    """
    supabase = get_supabase_admin()
    paper = _safe_select(supabase, "pyq_papers", id=paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="pyq_paper not found")

    rows = (
        supabase.table("pyq_questions")
        .select("id, question_number, reviewer_status")
        .eq("pyq_paper_id", paper_id)
        .limit(2000)
        .execute()
        .data
        or []
    )

    present_numbers = sorted(
        {int(r["question_number"]) for r in rows if r.get("question_number") is not None}
    )
    by_status: dict[str, int] = {}
    for r in rows:
        s = r.get("reviewer_status") or "pending"
        by_status[s] = by_status.get(s, 0) + 1

    meta_expected = (paper.get("metadata") or {}).get("expected_question_count")
    total_expected: int | None = None
    if meta_expected is not None:
        try:
            total_expected = int(meta_expected)
        except (TypeError, ValueError):
            pass
    if total_expected is None and present_numbers:
        total_expected = present_numbers[-1]

    missing: list[int] = []
    if total_expected:
        full_range = set(range(1, total_expected + 1))
        missing = sorted(full_range - set(present_numbers))

    return {
        "paper_id": paper_id,
        "total_expected": total_expected,
        "present": len(rows),
        "missing": missing,
        "by_status": by_status,
    }


@router.get("/pyq-papers/{paper_id}/dup-check")
def pyq_paper_dup_check(
    paper_id: str,
    question_text: str = Query(..., min_length=1, max_length=4000),
    question_id: str | None = Query(default=None),
    _admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Find potential duplicate questions in the same paper (or same exam).

    Returns rows with a content_hash exact match, plus rows whose
    normalized question_text shares a Levenshtein ratio >= 0.80 with the
    candidate text (slightly below the extractor threshold so the reviewer
    sees borderline cases too).
    """
    import re as _re
    try:
        from Levenshtein import ratio as _ratio
    except ImportError:
        _ratio = None

    supabase = get_supabase_admin()
    paper = _safe_select(supabase, "pyq_papers", id=paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="pyq_paper not found")

    # Fetch candidate rows — same paper, exclude self
    q = (
        supabase.table("pyq_questions")
        .select("id, question_number, question_text, content_hash, reviewer_status, pyq_paper_id")
        .eq("pyq_paper_id", paper_id)
        .limit(500)
    )
    rows = q.execute().data or []
    if question_id:
        rows = [r for r in rows if r.get("id") != question_id]

    # Normalize: lowercase, replace punctuation with space, collapse whitespace
    _punct = _re.compile(r'[^\w\s]')
    _ws = _re.compile(r'\s+')

    def _norm(t: str) -> str:
        t = _punct.sub(' ', (t or '').lower())
        return _ws.sub(' ', t).strip()

    import hashlib
    candidate_norm = _norm(question_text)
    candidate_hash = hashlib.sha256(candidate_norm.encode()).hexdigest()

    matches = []
    for row in rows:
        row_hash = row.get("content_hash") or ""
        row_text = row.get("question_text") or ""
        row_norm = _norm(row_text)

        if row_hash and row_hash == candidate_hash:
            matches.append({**row, "match_type": "exact_hash", "ratio": 1.0})
        elif _ratio and row_norm:
            r = _ratio(candidate_norm, row_norm)
            if r >= 0.80:
                matches.append({**row, "match_type": "fuzzy", "ratio": round(r, 3)})

    matches.sort(key=lambda x: -x["ratio"])
    return {"matches": matches[:20], "candidate_content_hash": candidate_hash}


@router.get("/pyq-papers/{paper_id}/signed-pdf")
def pyq_paper_signed_pdf(
    paper_id: str,
    document_id: str = Query(..., min_length=1),
    _admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Return a short-lived signed URL for viewing a source PDF in the workspace."""
    supabase = get_supabase_admin()
    if not _safe_select(supabase, "pyq_papers", id=paper_id):
        raise HTTPException(status_code=404, detail="pyq_paper not found")

    asset = (
        supabase.table("document_assets")
        .select("id, storage_bucket, storage_path, original_filename, page_count")
        .eq("id", document_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not asset:
        raise HTTPException(status_code=404, detail="document_asset not found")
    row = asset[0]

    bucket = row.get("storage_bucket")
    path = row.get("storage_path")
    if not bucket or not path:
        raise HTTPException(status_code=422, detail="Document has no storage path")

    try:
        result = supabase.storage.from_(bucket).create_signed_url(path, 3600)
        signed_url = (
            result.get("signedURL")
            or result.get("signedUrl")
            or result.get("signed_url")
            or ""
        )
    except Exception as exc:
        logger.exception("signed URL creation failed for doc=%s", document_id)
        raise HTTPException(status_code=502, detail=f"Storage error: {exc}") from exc

    if not signed_url:
        raise HTTPException(status_code=502, detail="Storage did not return a signed URL")

    return {
        "document_id": document_id,
        "signed_url": signed_url,
        "original_filename": row.get("original_filename"),
        "page_count": row.get("page_count"),
    }


# ════════════════════════════════════════════════════════════════════════
#  PYQ bulk import (PR5) — preflight + idempotent commit
# ════════════════════════════════════════════════════════════════════════


class _PrefligtBody(BaseModel):
    """Accept rows as pre-parsed JSON. For CSV, use the multipart endpoints."""
    rows: list[dict[str, Any]] = Field(default_factory=list)
    reason: str = Field(default="bulk import preflight")


class _CommitBody(BaseModel):
    import_token: str
    override_errors: bool = False
    reason: str = Field(default="bulk import commit")


@router.post("/pyq-papers/{paper_id}/bulk-import/preflight")
async def pyq_bulk_preflight(
    paper_id: str,
    request: Request,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Preflight: parse CSV or JSON bytes, validate rows, run dedup. NO writes.

    Send either:
    - ``Content-Type: text/csv`` with CSV bytes
    - ``Content-Type: application/json`` with a JSON array of row objects

    Returns per-row preview + ``import_token`` for use in /commit.
    """
    from app.exam_intelligence import pyq_bulk_import as _bi

    supabase = get_supabase_admin()
    if not _safe_select(supabase, "pyq_papers", id=paper_id):
        raise HTTPException(status_code=404, detail="pyq_paper not found")

    content_type = request.headers.get("content-type", "")
    body_bytes = await request.body()
    if not body_bytes:
        raise HTTPException(status_code=422, detail="request body is empty")

    try:
        result = _bi.preflight(supabase, admin, paper_id, body_bytes, content_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return result


@router.post("/pyq-papers/{paper_id}/bulk-import/commit")
def pyq_bulk_commit(
    paper_id: str,
    body: _CommitBody,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Commit a previously preflighted PYQ bulk import.

    ``import_token`` comes from the preflight response.  Pass
    ``override_errors=true`` to attempt rows that were flagged
    ``error`` or ``duplicate`` in preflight (fuzzy rows are always
    committed unless they were also error rows).
    Idempotent: rows whose ``question_number`` already exists in the
    paper are silently skipped.
    """
    from app.exam_intelligence import pyq_bulk_import as _bi

    supabase = get_supabase_admin()
    if not _safe_select(supabase, "pyq_papers", id=paper_id):
        raise HTTPException(status_code=404, detail="pyq_paper not found")

    try:
        result = _bi.commit(
            supabase, admin, body.import_token, override_errors=body.override_errors
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    _audit(
        supabase, admin, "exam_intel.cms.pyq_bulk_import.commit",
        entity_type="pyq_paper", entity_id=paper_id,
        new_value={
            "reason": body.reason,
            "import_token": body.import_token,
            "committed": result["committed"],
            "skipped": result["skipped"],
            "failed": result["failed"],
        },
    )
    return result


# ════════════════════════════════════════════════════════════════════════
#  PYQ questions — created at reviewer_status='pending'; options upsert
#  in the same call so the question + options land atomically (best
#  effort — no row-level transaction across two tables here, but at
#  least the audit row captures both)
# ════════════════════════════════════════════════════════════════════════


_QUESTION_FIELDS = {
    "pyq_paper_id", "question_number", "question_text",
    "normalized_question_hash", "question_type", "explanation_text",
    "observed_difficulty", "expected_solve_time_sec", "language", "metadata",
    # Provenance fields (migration 149) — written by the auto-extractor.
    "source_kind", "source_document_id", "source_page", "source_regions",
    "extractor_version", "extraction_run_id", "idempotency_key",
    "content_hash", "confidence_by_field",
}
_QUESTION_TYPES = ("mcq", "numerical", "descriptive", "caselet", "matching", "other")
_OPTION_FIELDS = {"option_label", "option_text", "normalized_option_hash", "normalized_value", "is_correct", "metadata"}


@router.get("/pyq-questions")
def list_pyq_questions(
    pyq_paper_id: str | None = Query(default=None),
    reviewer_status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    q = supabase.table("pyq_questions").select("*", count="exact").order("question_number", desc=False)
    if pyq_paper_id:
        q = q.eq("pyq_paper_id", pyq_paper_id)
    if reviewer_status:
        q = q.eq("reviewer_status", reviewer_status)
    res = q.range(offset, offset + limit - 1).execute()
    return {"items": res.data or [], "total": getattr(res, "count", None), "limit": limit, "offset": offset}


@router.post("/pyq-questions")
def create_pyq_question(
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Create one PYQ question and optionally its options in a single
    call. Question lands at reviewer_status='pending'. Options are
    not gated by reviewer_status (they inherit from question)."""
    supabase = get_supabase_admin()
    row = {k: v for k, v in body.payload.items() if k in _QUESTION_FIELDS}
    if not row.get("pyq_paper_id") or not row.get("question_text"):
        raise HTTPException(status_code=422, detail="pyq_paper_id and question_text are required")
    if row.get("question_type") and row["question_type"] not in _QUESTION_TYPES:
        raise HTTPException(status_code=422, detail=f"question_type must be one of {_QUESTION_TYPES}")
    row["reviewer_status"] = "pending"
    if not row.get("normalized_question_hash"):
        q_hash = question_hash(row.get("question_text"))
        if q_hash:
            row["normalized_question_hash"] = q_hash
    inserted = supabase.table("pyq_questions").insert(row).execute().data or []
    new_q = inserted[0] if inserted else row
    question_id = new_q.get("id")

    inserted_options: list[dict] = []
    child_errors: list[dict] = []
    options = body.payload.get("options") or []
    if isinstance(options, list) and options and question_id:
        opt_rows = []
        for opt in options:
            if not isinstance(opt, dict):
                continue
            cleaned = {k: v for k, v in opt.items() if k in _OPTION_FIELDS}
            cleaned["question_id"] = question_id
            if cleaned.get("option_label") and cleaned.get("option_text"):
                if not cleaned.get("normalized_option_hash"):
                    o_hash = option_hash(cleaned.get("option_text"))
                    if o_hash:
                        cleaned["normalized_option_hash"] = o_hash
                opt_rows.append(cleaned)
        if opt_rows:
            try:
                inserted_options = supabase.table("pyq_options").insert(opt_rows).execute().data or []
            except Exception as exc:  # noqa: BLE001
                logger.exception("pyq_options insert failed for question %s", question_id)
                child_errors = [{"label": r.get("option_label"), "error": str(exc)[:200]} for r in opt_rows]

    if child_errors and question_id:
        # Options failed — delete the orphaned question row to preserve atomicity.
        try:
            supabase.table("pyq_questions").delete().eq("id", question_id).execute()
        except Exception:  # noqa: BLE001
            logger.exception("rollback delete failed for question %s", question_id)
        audit_id = _audit(
            supabase, admin, "exam_intel.cms.pyq_question.create",
            entity_type="pyq_question", entity_id=question_id,
            new_value={"reason": body.reason, "question": new_q, "child_errors": child_errors, "rolled_back": True},
        )
        return {"ok": False, "audit_id": audit_id, "question": new_q, "child_errors": child_errors}

    audit_id = _audit(
        supabase, admin, "exam_intel.cms.pyq_question.create",
        entity_type="pyq_question", entity_id=question_id,
        new_value={
            "reason": body.reason,
            "question": new_q,
            "options_inserted": len(inserted_options),
        },
    )
    return {"ok": True, "audit_id": audit_id, "question": new_q, "options": inserted_options}


@router.patch("/pyq-questions/{question_id}")
def update_pyq_question(
    question_id: str,
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Curate an existing PYQ question. Lifecycle (``reviewer_status``)
    stays where it is — promotion through the review queue uses the
    review-side router."""
    supabase = get_supabase_admin()
    existing = _safe_select(supabase, "pyq_questions", id=question_id)
    if not existing:
        raise HTTPException(status_code=404, detail="pyq_question not found")
    patch = {k: v for k, v in body.payload.items() if k in _QUESTION_FIELDS}
    if not patch:
        raise HTTPException(status_code=422, detail="No allowed fields in payload")
    if patch.get("question_type") and patch["question_type"] not in _QUESTION_TYPES:
        raise HTTPException(status_code=422, detail=f"question_type must be one of {_QUESTION_TYPES}")
    # Re-hash the question text if it changed and the caller didn't supply a hash.
    if patch.get("question_text") and not patch.get("normalized_question_hash"):
        q_hash = question_hash(patch["question_text"])
        if q_hash:
            patch["normalized_question_hash"] = q_hash
    updated = supabase.table("pyq_questions").update(patch).eq("id", question_id).execute().data or []
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.pyq_question.update",
        entity_type="pyq_question", entity_id=question_id,
        new_value={"reason": body.reason, "patch": patch, "previous": existing},
    )
    return {"ok": True, "audit_id": audit_id, "row": updated[0] if updated else existing | patch}


# ════════════════════════════════════════════════════════════════════════
#  PYQ options (standalone insert — for editing existing questions)
# ════════════════════════════════════════════════════════════════════════


@router.get("/pyq-options")
def list_pyq_options(
    question_id: str | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    _admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """List PYQ options, optionally filtered by question_id."""
    supabase = get_supabase_admin()
    q = (
        supabase.table("pyq_options")
        .select("*", count="exact")
        .order("option_label", desc=False)
    )
    if question_id:
        q = q.eq("question_id", question_id)
    res = q.limit(limit).execute()
    return {"items": res.data or [], "total": getattr(res, "count", None)}


@router.post("/pyq-options")
def create_pyq_option(
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    row = {k: v for k, v in body.payload.items() if k in _OPTION_FIELDS}
    question_id = body.payload.get("question_id")
    if not question_id or not row.get("option_label") or not row.get("option_text"):
        raise HTTPException(status_code=422, detail="question_id, option_label, option_text are required")
    if not _safe_select(supabase, "pyq_questions", id=question_id):
        raise HTTPException(status_code=422, detail="question_id does not resolve")
    row["question_id"] = question_id
    if not row.get("normalized_option_hash"):
        o_hash = option_hash(row.get("option_text"))
        if o_hash:
            row["normalized_option_hash"] = o_hash
    inserted = supabase.table("pyq_options").insert(row).execute().data or []
    new = inserted[0] if inserted else row
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.pyq_option.create",
        entity_type="pyq_option", entity_id=new.get("id"),
        new_value={"reason": body.reason, "row": new},
    )
    return {"ok": True, "audit_id": audit_id, "row": new}


@router.patch("/pyq-options/{option_id}")
def update_pyq_option(
    option_id: str,
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Curate an existing PYQ option (text fix, mark-correct toggle).

    The parent question's ``reviewer_status`` is intentionally not touched
    here — that lifecycle move belongs in the review-side router.
    """
    supabase = get_supabase_admin()
    existing = _safe_select(supabase, "pyq_options", id=option_id)
    if not existing:
        raise HTTPException(status_code=404, detail="pyq_option not found")
    patch = {k: v for k, v in body.payload.items() if k in _OPTION_FIELDS}
    if not patch:
        raise HTTPException(status_code=422, detail="No allowed fields in payload")
    if patch.get("option_text") and not patch.get("normalized_option_hash"):
        o_hash = option_hash(patch["option_text"])
        if o_hash:
            patch["normalized_option_hash"] = o_hash
    updated = supabase.table("pyq_options").update(patch).eq("id", option_id).execute().data or []
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.pyq_option.update",
        entity_type="pyq_option", entity_id=option_id,
        new_value={"reason": body.reason, "patch": patch, "previous": existing},
    )
    return {"ok": True, "audit_id": audit_id, "row": updated[0] if updated else existing | patch}


# ════════════════════════════════════════════════════════════════════════
#  Exam topic coverage — created at reviewer_status='pending_review'
# ════════════════════════════════════════════════════════════════════════


# Mirrors the real ``exam_topic_coverage`` schema (migration 030). There is
# no ``priority`` or ``is_active`` column — the planner reads
# ``exam_priority_score`` / ``is_high_yield`` instead.
_COVERAGE_FIELDS = {
    "exam_id", "exam_cycle_id", "exam_phase_id", "section_id", "topic_id",
    "coverage_depth", "expected_difficulty", "exam_priority_score",
    "is_high_yield", "confidence_score", "source_basis",
    "reviewer_status", "review_notes", "metadata",
}


@router.get("/exam-topic-coverage")
def list_exam_topic_coverage(
    exam_id: str | None = Query(default=None),
    reviewer_status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    q = supabase.table("exam_topic_coverage").select("*", count="exact").order("exam_priority_score", desc=True)
    if exam_id:
        q = q.eq("exam_id", exam_id)
    if reviewer_status:
        q = q.eq("reviewer_status", reviewer_status)
    res = q.range(offset, offset + limit - 1).execute()
    return {"items": res.data or [], "total": getattr(res, "count", None), "limit": limit, "offset": offset}


@router.post("/exam-topic-coverage")
def create_exam_topic_coverage(
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    unknown = set(body.payload) - _COVERAGE_FIELDS
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown field(s) for exam_topic_coverage: {sorted(unknown)}",
        )
    row = {k: v for k, v in body.payload.items() if k in _COVERAGE_FIELDS}
    if not row.get("exam_id") or not row.get("topic_id"):
        raise HTTPException(status_code=422, detail="exam_id and topic_id are required")
    if row.get("section_id"):
        section = _safe_select(supabase, "exam_phase_sections", id=row["section_id"])
        if not section:
            raise HTTPException(status_code=422, detail="section_id does not resolve")
        if section.get("exam_phase_id") != row.get("exam_phase_id"):
            raise HTTPException(status_code=422, detail="section_id belongs to a different exam_phase")
    row["reviewer_status"] = "pending_review"
    inserted = supabase.table("exam_topic_coverage").insert(row).execute().data or []
    new = inserted[0] if inserted else row
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.coverage.create",
        entity_type="exam_topic_coverage", entity_id=new.get("id"),
        new_value={"reason": body.reason, "row": new},
    )
    return {"ok": True, "audit_id": audit_id, "row": new}


# ════════════════════════════════════════════════════════════════════════
#  Policy updates — created at reviewer_status='pending'
# ════════════════════════════════════════════════════════════════════════


_POLICY_FIELDS = {
    "exam_id", "exam_cycle_id", "source_id", "update_type", "title",
    "summary", "source_url", "source_type", "claim_status",
    "affects_plan", "affects_deadline", "affects_eligibility",
    "affects_documents", "affects_syllabus", "affects_vacancy",
    "change_summary", "evidence", "published_at", "effective_from",
}
_POLICY_UPDATE_TYPES = (
    "notification_change", "cycle_change", "date_change", "syllabus_change",
    "pattern_change", "vacancy_change", "eligibility_change",
    "reservation_change", "document_rule_change", "other",
)


@router.get("/policy-updates")
def list_policy_updates(
    exam_id: str | None = Query(default=None),
    reviewer_status: str | None = Query(default=None),
    update_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    q = supabase.table("exam_policy_updates").select("*", count="exact").order("created_at", desc=True)
    if exam_id:
        q = q.eq("exam_id", exam_id)
    if reviewer_status:
        q = q.eq("reviewer_status", reviewer_status)
    if update_type:
        q = q.eq("update_type", update_type)
    res = q.range(offset, offset + limit - 1).execute()
    return {"items": res.data or [], "total": getattr(res, "count", None), "limit": limit, "offset": offset}


@router.post("/policy-updates")
def create_policy_update(
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    row = {k: v for k, v in body.payload.items() if k in _POLICY_FIELDS}
    if not row.get("exam_id") or not row.get("update_type") or not row.get("title"):
        raise HTTPException(status_code=422, detail="exam_id, update_type, title are required")
    if row["update_type"] not in _POLICY_UPDATE_TYPES:
        raise HTTPException(status_code=422, detail=f"update_type must be one of {_POLICY_UPDATE_TYPES}")
    # Enforce the constraint in code as well so the error message is friendly,
    # not a raw Postgres constraint violation.
    if (row.get("source_type") or "official") != "official":
        for affect in ("affects_plan", "affects_deadline", "affects_eligibility",
                       "affects_documents", "affects_syllabus", "affects_vacancy"):
            if row.get(affect):
                raise HTTPException(
                    status_code=422,
                    detail=f"Non-official policy updates cannot set {affect}=true",
                )
    row["reviewer_status"] = "pending"
    inserted = supabase.table("exam_policy_updates").insert(row).execute().data or []
    new = inserted[0] if inserted else row
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.policy_update.create",
        entity_type="exam_policy_update", entity_id=new.get("id"),
        new_value={"reason": body.reason, "row": new},
    )
    return {"ok": True, "audit_id": audit_id, "row": new}


@router.patch("/policy-updates/{policy_id}")
def update_policy_update(
    policy_id: str,
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Curate an existing exam_policy_updates row.

    Enforces the same non-official guardrail as create: a non-official
    source cannot have any ``affects_*`` flag set to true. ``reviewer_status``
    stays where it is (lifecycle moves through the review router).
    """
    supabase = get_supabase_admin()
    existing = _safe_select(supabase, "exam_policy_updates", id=policy_id)
    if not existing:
        raise HTTPException(status_code=404, detail="exam_policy_update not found")
    patch = {k: v for k, v in body.payload.items() if k in _POLICY_FIELDS}
    if not patch:
        raise HTTPException(status_code=422, detail="No allowed fields in payload")
    if patch.get("update_type") and patch["update_type"] not in _POLICY_UPDATE_TYPES:
        raise HTTPException(status_code=422, detail=f"update_type must be one of {_POLICY_UPDATE_TYPES}")
    merged_source_type = patch.get("source_type") or existing.get("source_type") or "official"
    if merged_source_type != "official":
        for affect in ("affects_plan", "affects_deadline", "affects_eligibility",
                       "affects_documents", "affects_syllabus", "affects_vacancy"):
            merged = patch[affect] if affect in patch else existing.get(affect)
            if merged:
                raise HTTPException(
                    status_code=422,
                    detail=f"Non-official policy updates cannot set {affect}=true",
                )
    updated = supabase.table("exam_policy_updates").update(patch).eq("id", policy_id).execute().data or []
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.policy_update.update",
        entity_type="exam_policy_update", entity_id=policy_id,
        new_value={"reason": body.reason, "patch": patch, "previous": existing},
    )
    return {"ok": True, "audit_id": audit_id, "row": updated[0] if updated else existing | patch}


# ════════════════════════════════════════════════════════════════════════
#  Exam competition metrics — vacancy, applicant count, cutoff trend,
#  difficulty trend. Created at reviewer_status='draft'; moves through
#  review lifecycle via the review-side router. CMS-side create + curate.
# ════════════════════════════════════════════════════════════════════════


_COMPETITION_FIELDS = {
    "exam_id", "exam_cycle_id", "exam_phase_id",
    "vacancy_total", "vacancy_by_category",
    "applicant_count", "selection_ratio",
    "cutoff_trend", "difficulty_trend", "competition_pressure_score",
    "source_basis", "confidence_score", "evidence_count",
    "reviewer_notes", "metadata",
}
_COMPETITION_SOURCE_BASIS = (
    "manual", "official", "reviewed_analysis", "derived", "model_generated"
)


def _validate_competition_payload(row: dict[str, Any]) -> None:
    if row.get("source_basis") and row["source_basis"] not in _COMPETITION_SOURCE_BASIS:
        raise HTTPException(
            status_code=422,
            detail=f"source_basis must be one of {_COMPETITION_SOURCE_BASIS}",
        )
    if row.get("selection_ratio") is not None:
        try:
            n = float(row["selection_ratio"])
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail="selection_ratio must be numeric")
        if not (0 <= n <= 1):
            raise HTTPException(status_code=422, detail="selection_ratio must be in [0, 1]")
    if row.get("confidence_score") is not None:
        try:
            n = float(row["confidence_score"])
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail="confidence_score must be numeric")
        if not (0 <= n <= 1):
            raise HTTPException(status_code=422, detail="confidence_score must be in [0, 1]")
    if row.get("competition_pressure_score") is not None:
        try:
            n = float(row["competition_pressure_score"])
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail="competition_pressure_score must be numeric")
        if not (0 <= n <= 100):
            raise HTTPException(status_code=422, detail="competition_pressure_score must be in [0, 100]")


@router.post("/exam-competition-metrics")
def create_competition_metric(
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Create a competition-intelligence row.

    Lands at ``reviewer_status='draft'``. Reviewers move it through
    pending_review → reviewed → locked via the review-side router; only
    ``locked`` rows are planner-ready and only ``locked``/``reviewed``
    rows are surfaced to aspirants.
    """
    supabase = get_supabase_admin()
    row = {k: v for k, v in body.payload.items() if k in _COMPETITION_FIELDS}
    if not row.get("exam_id"):
        raise HTTPException(status_code=422, detail="exam_id is required")
    if not _safe_select(supabase, "exams", id=row["exam_id"]):
        raise HTTPException(status_code=422, detail="exam_id does not resolve")
    _validate_competition_payload(row)
    row["reviewer_status"] = "draft"
    inserted = supabase.table("exam_competition_metrics").insert(row).execute().data or []
    new = inserted[0] if inserted else row
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.competition_metric.create",
        entity_type="exam_competition_metric", entity_id=new.get("id"),
        new_value={"reason": body.reason, "row": new},
    )
    return {"ok": True, "audit_id": audit_id, "row": new}


@router.patch("/exam-competition-metrics/{metric_id}")
def update_competition_metric(
    metric_id: str,
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Curate an existing competition-metric row. ``reviewer_status`` is
    not movable here; the review-side router owns that lifecycle."""
    supabase = get_supabase_admin()
    existing = _safe_select(supabase, "exam_competition_metrics", id=metric_id)
    if not existing:
        raise HTTPException(status_code=404, detail="exam_competition_metric not found")
    patch = {k: v for k, v in body.payload.items() if k in _COMPETITION_FIELDS}
    if not patch:
        raise HTTPException(status_code=422, detail="No allowed fields in payload")
    _validate_competition_payload(patch)
    patch["updated_at"] = _now_iso()
    updated = supabase.table("exam_competition_metrics").update(patch).eq("id", metric_id).execute().data or []
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.competition_metric.update",
        entity_type="exam_competition_metric", entity_id=metric_id,
        new_value={"reason": body.reason, "patch": patch, "previous": existing},
    )
    return {"ok": True, "audit_id": audit_id, "row": updated[0] if updated else existing | patch}


# ════════════════════════════════════════════════════════════════════════
#  Subjects (taxonomy, migration 029)
# ════════════════════════════════════════════════════════════════════════


# Exact writable columns from migration 029. ``slug`` is globally unique.
_SUBJECT_FIELDS = {
    "slug", "name", "subject_group", "default_difficulty_level",
    "description", "is_active", "metadata",
}


def _reject_unknown(payload: dict[str, Any], allowed: set[str], table: str) -> None:
    unknown = set(payload) - allowed
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown field(s) for {table}: {sorted(unknown)}",
        )


def _norm_alias(text: str) -> str:
    return (text or "").strip().lower()


@router.get("/subjects")
def list_subjects(
    is_active: bool | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    query = supabase.table("subjects").select(
        "id, slug, name, subject_group, default_difficulty_level, description, is_active, metadata, created_at, updated_at",
        count="exact",
    ).order("name", desc=False)
    if is_active is not None:
        query = query.eq("is_active", is_active)
    if q:
        query = query.ilike("name", f"%{q.strip()}%")
    res = query.range(offset, offset + limit - 1).execute()
    return {"items": res.data or [], "total": getattr(res, "count", None), "limit": limit, "offset": offset}


@router.post("/subjects")
def create_subject(
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    _reject_unknown(body.payload, _SUBJECT_FIELDS, "subjects")
    row = {k: v for k, v in body.payload.items() if k in _SUBJECT_FIELDS}
    if not row.get("slug") or not row.get("name"):
        raise HTTPException(status_code=422, detail="slug and name are required")
    row.setdefault("is_active", True)
    try:
        # Upsert by slug so re-importing the same subject is idempotent.
        inserted = supabase.table("subjects").upsert(row, on_conflict="slug").execute().data or []
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=409, detail=f"Insert failed: {exc}")
    new = inserted[0] if inserted else row
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.subject.create",
        entity_type="subject", entity_id=new.get("id"),
        new_value={"reason": body.reason, "row": new},
    )
    return {"ok": True, "audit_id": audit_id, "row": new}


@router.patch("/subjects/{subject_id}")
def update_subject(
    subject_id: str,
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    existing = _safe_select(supabase, "subjects", id=subject_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Subject not found")
    _reject_unknown(body.payload, _SUBJECT_FIELDS, "subjects")
    patch = {k: v for k, v in body.payload.items() if k in _SUBJECT_FIELDS}
    if not patch:
        raise HTTPException(status_code=422, detail="No allowed fields in payload")
    patch["updated_at"] = _now_iso()
    updated = supabase.table("subjects").update(patch).eq("id", subject_id).execute().data or []
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.subject.update",
        entity_type="subject", entity_id=subject_id,
        new_value={"reason": body.reason, "patch": patch, "previous": existing},
    )
    return {"ok": True, "audit_id": audit_id, "row": updated[0] if updated else existing | patch}


# ════════════════════════════════════════════════════════════════════════
#  Topics (taxonomy, migration 029)
# ════════════════════════════════════════════════════════════════════════


# Exact writable columns from migration 029. Slug is unique per
# (subject_id, parent_topic_id, slug); level is constrained by a CHECK.
_TOPIC_FIELDS = {
    "subject_id", "parent_topic_id", "slug", "name", "level",
    "default_difficulty_level", "description", "is_active", "metadata",
}
_TOPIC_LEVELS = ("topic", "microtopic", "concept")


@router.get("/topics")
def list_topics(
    subject_id: str | None = Query(default=None),
    parent_topic_id: str | None = Query(default=None),
    level: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    query = supabase.table("topics").select(
        "id, subject_id, parent_topic_id, slug, name, level, default_difficulty_level, description, is_active, metadata, created_at, updated_at",
        count="exact",
    ).order("name", desc=False)
    if subject_id:
        query = query.eq("subject_id", subject_id)
    if parent_topic_id:
        query = query.eq("parent_topic_id", parent_topic_id)
    if level:
        query = query.eq("level", level)
    if is_active is not None:
        query = query.eq("is_active", is_active)
    if q:
        query = query.ilike("name", f"%{q.strip()}%")
    res = query.range(offset, offset + limit - 1).execute()
    return {"items": res.data or [], "total": getattr(res, "count", None), "limit": limit, "offset": offset}


@router.post("/topics")
def create_topic(
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    _reject_unknown(body.payload, _TOPIC_FIELDS, "topics")
    row = {k: v for k, v in body.payload.items() if k in _TOPIC_FIELDS}
    if not row.get("subject_id") or not row.get("slug") or not row.get("name"):
        raise HTTPException(status_code=422, detail="subject_id, slug, name are required")
    if row.get("level") and row["level"] not in _TOPIC_LEVELS:
        raise HTTPException(status_code=422, detail=f"level must be one of {_TOPIC_LEVELS}")
    if not _safe_select(supabase, "subjects", id=row["subject_id"]):
        raise HTTPException(status_code=422, detail="subject_id does not resolve")
    parent_id = row.get("parent_topic_id")
    if parent_id:
        parent = _safe_select(supabase, "topics", id=parent_id)
        if not parent:
            raise HTTPException(status_code=422, detail="parent_topic_id does not resolve")
        if parent.get("subject_id") != row["subject_id"]:
            raise HTTPException(
                status_code=422,
                detail="parent_topic_id belongs to a different subject",
            )
    row.setdefault("is_active", True)
    try:
        # Upsert on the natural key so re-importing a topic is idempotent.
        inserted = (
            supabase.table("topics")
            .upsert(row, on_conflict="subject_id,parent_topic_id,slug")
            .execute()
            .data
            or []
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=409, detail=f"Insert failed: {exc}")
    new = inserted[0] if inserted else row
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.topic.create",
        entity_type="topic", entity_id=new.get("id"),
        new_value={"reason": body.reason, "row": new},
    )
    return {"ok": True, "audit_id": audit_id, "row": new}


@router.patch("/topics/{topic_id}")
def update_topic(
    topic_id: str,
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    existing = _safe_select(supabase, "topics", id=topic_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Topic not found")
    _reject_unknown(body.payload, _TOPIC_FIELDS, "topics")
    patch = {k: v for k, v in body.payload.items() if k in _TOPIC_FIELDS}
    if not patch:
        raise HTTPException(status_code=422, detail="No allowed fields in payload")
    if patch.get("level") and patch["level"] not in _TOPIC_LEVELS:
        raise HTTPException(status_code=422, detail=f"level must be one of {_TOPIC_LEVELS}")
    # Keep parent within the (possibly updated) subject.
    target_subject = patch.get("subject_id", existing.get("subject_id"))
    if patch.get("parent_topic_id"):
        parent = _safe_select(supabase, "topics", id=patch["parent_topic_id"])
        if not parent:
            raise HTTPException(status_code=422, detail="parent_topic_id does not resolve")
        if parent.get("subject_id") != target_subject:
            raise HTTPException(status_code=422, detail="parent_topic_id belongs to a different subject")
    patch["updated_at"] = _now_iso()
    updated = supabase.table("topics").update(patch).eq("id", topic_id).execute().data or []
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.topic.update",
        entity_type="topic", entity_id=topic_id,
        new_value={"reason": body.reason, "patch": patch, "previous": existing},
    )
    return {"ok": True, "audit_id": audit_id, "row": updated[0] if updated else existing | patch}


# ════════════════════════════════════════════════════════════════════════
#  Topic aliases (taxonomy, migration 029)
# ════════════════════════════════════════════════════════════════════════


# Operator-settable columns. ``normalized_alias`` is server-derived from
# ``alias`` (the table requires it NOT NULL with no default).
_TOPIC_ALIAS_FIELDS = {"topic_id", "alias", "source_context"}


@router.get("/topic-aliases")
def list_topic_aliases(
    topic_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    query = supabase.table("topic_aliases").select(
        "id, topic_id, alias, normalized_alias, source_context, created_at",
        count="exact",
    ).order("created_at", desc=True)
    if topic_id:
        query = query.eq("topic_id", topic_id)
    res = query.range(offset, offset + limit - 1).execute()
    return {"items": res.data or [], "total": getattr(res, "count", None), "limit": limit, "offset": offset}


@router.post("/topic-aliases")
def create_topic_alias(
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    _reject_unknown(body.payload, _TOPIC_ALIAS_FIELDS, "topic_aliases")
    row = {k: v for k, v in body.payload.items() if k in _TOPIC_ALIAS_FIELDS}
    if not row.get("topic_id") or not row.get("alias"):
        raise HTTPException(status_code=422, detail="topic_id and alias are required")
    if not _safe_select(supabase, "topics", id=row["topic_id"]):
        raise HTTPException(status_code=422, detail="topic_id does not resolve")
    row["normalized_alias"] = _norm_alias(row["alias"])
    try:
        inserted = supabase.table("topic_aliases").insert(row).execute().data or []
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=409, detail=f"Insert failed: {exc}")
    new = inserted[0] if inserted else row
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.topic_alias.create",
        entity_type="topic_alias", entity_id=new.get("id"),
        new_value={"reason": body.reason, "row": new},
    )
    return {"ok": True, "audit_id": audit_id, "row": new}


@router.delete("/topic-aliases/{alias_id}")
def delete_topic_alias(
    alias_id: str,
    reason: str = Query(..., min_length=8, max_length=500),
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Hard-delete: an alias is a pure lookup row with no review surface
    and nothing FK-references it."""
    supabase = get_supabase_admin()
    existing = _safe_select(supabase, "topic_aliases", id=alias_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Topic alias not found")
    supabase.table("topic_aliases").delete().eq("id", alias_id).execute()
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.topic_alias.delete",
        entity_type="topic_alias", entity_id=alias_id,
        new_value={"reason": reason, "deleted": existing},
    )
    return {"ok": True, "audit_id": audit_id, "id": alias_id}


# ════════════════════════════════════════════════════════════════════════
#  Topic prerequisites (taxonomy, migration 029)
# ════════════════════════════════════════════════════════════════════════


_TOPIC_PREREQ_FIELDS = {
    "topic_id", "prerequisite_topic_id", "relation_type", "strength",
    "source_basis", "metadata",
}
_TOPIC_PREREQ_RELATIONS = ("requires", "recommended_before", "supports", "foundation_for")


@router.get("/topic-prerequisites")
def list_topic_prerequisites(
    topic_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    query = supabase.table("topic_prerequisites").select(
        "id, topic_id, prerequisite_topic_id, relation_type, strength, source_basis, metadata, created_at",
        count="exact",
    ).order("created_at", desc=True)
    if topic_id:
        query = query.eq("topic_id", topic_id)
    res = query.range(offset, offset + limit - 1).execute()
    return {"items": res.data or [], "total": getattr(res, "count", None), "limit": limit, "offset": offset}


@router.post("/topic-prerequisites")
def create_topic_prerequisite(
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    _reject_unknown(body.payload, _TOPIC_PREREQ_FIELDS, "topic_prerequisites")
    row = {k: v for k, v in body.payload.items() if k in _TOPIC_PREREQ_FIELDS}
    topic_id = row.get("topic_id")
    prereq_id = row.get("prerequisite_topic_id")
    if not topic_id or not prereq_id:
        raise HTTPException(status_code=422, detail="topic_id and prerequisite_topic_id are required")
    if topic_id == prereq_id:
        raise HTTPException(status_code=422, detail="a topic cannot be its own prerequisite")
    if row.get("relation_type") and row["relation_type"] not in _TOPIC_PREREQ_RELATIONS:
        raise HTTPException(status_code=422, detail=f"relation_type must be one of {_TOPIC_PREREQ_RELATIONS}")
    if not _safe_select(supabase, "topics", id=topic_id):
        raise HTTPException(status_code=422, detail="topic_id does not resolve")
    if not _safe_select(supabase, "topics", id=prereq_id):
        raise HTTPException(status_code=422, detail="prerequisite_topic_id does not resolve")
    # Basic cycle guard: reject B→A when A→B already exists. (One level only;
    # transitive cycle detection would need a recursive CTE — see PR notes.)
    if _safe_select(supabase, "topic_prerequisites", topic_id=prereq_id, prerequisite_topic_id=topic_id):
        raise HTTPException(
            status_code=422,
            detail="cycle: the reverse prerequisite already exists",
        )
    try:
        inserted = supabase.table("topic_prerequisites").insert(row).execute().data or []
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=409, detail=f"Insert failed: {exc}")
    new = inserted[0] if inserted else row
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.topic_prerequisite.create",
        entity_type="topic_prerequisite", entity_id=new.get("id"),
        new_value={"reason": body.reason, "row": new},
    )
    return {"ok": True, "audit_id": audit_id, "row": new}


@router.delete("/topic-prerequisites/{prereq_id}")
def delete_topic_prerequisite(
    prereq_id: str,
    reason: str = Query(..., min_length=8, max_length=500),
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Hard-delete: a prerequisite edge is a pure relation row."""
    supabase = get_supabase_admin()
    existing = _safe_select(supabase, "topic_prerequisites", id=prereq_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Topic prerequisite not found")
    supabase.table("topic_prerequisites").delete().eq("id", prereq_id).execute()
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.topic_prerequisite.delete",
        entity_type="topic_prerequisite", entity_id=prereq_id,
        new_value={"reason": reason, "deleted": existing},
    )
    return {"ok": True, "audit_id": audit_id, "id": prereq_id}


# ════════════════════════════════════════════════════════════════════════
#  Exam phase sections (migration 030)
# ════════════════════════════════════════════════════════════════════════


# Real columns from migration 030. exam_phase_id + subject_id + section_label
# are NOT NULL; unique(exam_phase_id, subject_id, section_label). No
# section_code / is_optional columns; the duration column is duration_mins.
_SECTION_FIELDS = {
    "exam_phase_id", "subject_id", "section_label", "question_count", "marks",
    "duration_mins", "negative_marking", "difficulty_level", "weightage_percent",
    "sort_order", "metadata",
}


@router.get("/exam-phase-sections")
def list_exam_phase_sections(
    exam_phase_id: str | None = Query(default=None),
    subject_id: str | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    query = supabase.table("exam_phase_sections").select(
        "id, exam_phase_id, subject_id, section_label, question_count, marks, "
        "duration_mins, negative_marking, difficulty_level, weightage_percent, "
        "sort_order, metadata, created_at, updated_at",
        count="exact",
    ).order("sort_order", desc=False)
    if exam_phase_id:
        query = query.eq("exam_phase_id", exam_phase_id)
    if subject_id:
        query = query.eq("subject_id", subject_id)
    if q:
        query = query.ilike("section_label", f"%{q.strip()}%")
    res = query.range(offset, offset + limit - 1).execute()
    return {"items": res.data or [], "total": getattr(res, "count", None), "limit": limit, "offset": offset}


@router.post("/exam-phase-sections")
def create_exam_phase_section(
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    _reject_unknown(body.payload, _SECTION_FIELDS, "exam_phase_sections")
    row = {k: v for k, v in body.payload.items() if k in _SECTION_FIELDS}
    if not row.get("exam_phase_id") or not row.get("subject_id") or not row.get("section_label"):
        raise HTTPException(status_code=422, detail="exam_phase_id, subject_id, section_label are required")
    if not _safe_select(supabase, "exam_phases", id=row["exam_phase_id"]):
        raise HTTPException(status_code=422, detail="exam_phase_id does not resolve")
    if not _safe_select(supabase, "subjects", id=row["subject_id"]):
        raise HTTPException(status_code=422, detail="subject_id does not resolve")
    try:
        inserted = supabase.table("exam_phase_sections").insert(row).execute().data or []
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=409, detail=f"Insert failed: {exc}")
    new = inserted[0] if inserted else row
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.exam_phase_section.create",
        entity_type="exam_phase_section", entity_id=new.get("id"),
        new_value={"reason": body.reason, "row": new},
    )
    return {"ok": True, "audit_id": audit_id, "row": new}


@router.patch("/exam-phase-sections/{section_id}")
def update_exam_phase_section(
    section_id: str,
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    existing = _safe_select(supabase, "exam_phase_sections", id=section_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Exam phase section not found")
    _reject_unknown(body.payload, _SECTION_FIELDS, "exam_phase_sections")
    patch = {k: v for k, v in body.payload.items() if k in _SECTION_FIELDS}
    if not patch:
        raise HTTPException(status_code=422, detail="No allowed fields in payload")
    if patch.get("subject_id") and not _safe_select(supabase, "subjects", id=patch["subject_id"]):
        raise HTTPException(status_code=422, detail="subject_id does not resolve")
    patch["updated_at"] = _now_iso()
    updated = supabase.table("exam_phase_sections").update(patch).eq("id", section_id).execute().data or []
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.exam_phase_section.update",
        entity_type="exam_phase_section", entity_id=section_id,
        new_value={"reason": body.reason, "patch": patch, "previous": existing},
    )
    return {"ok": True, "audit_id": audit_id, "row": updated[0] if updated else existing | patch}


# ════════════════════════════════════════════════════════════════════════
#  Exam competition metrics — list (create/patch above)
# ════════════════════════════════════════════════════════════════════════


@router.get("/exam-competition-metrics")
def list_competition_metrics(
    exam_id: str | None = Query(default=None),
    reviewer_status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    query = supabase.table("exam_competition_metrics").select(
        "id, exam_id, exam_cycle_id, exam_phase_id, vacancy_total, applicant_count, "
        "selection_ratio, competition_pressure_score, source_basis, confidence_score, "
        "evidence_count, reviewer_status, metadata, created_at",
        count="exact",
    ).order("created_at", desc=True)
    if exam_id:
        query = query.eq("exam_id", exam_id)
    if reviewer_status:
        query = query.eq("reviewer_status", reviewer_status)
    res = query.range(offset, offset + limit - 1).execute()
    return {"items": res.data or [], "total": getattr(res, "count", None), "limit": limit, "offset": offset}


# ════════════════════════════════════════════════════════════════════════
#  Syllabus topic mentions — created at reviewer_status='pending'
# ════════════════════════════════════════════════════════════════════════


# Operator-settable columns from migration 031. ``reviewer_status`` is
# accepted in the payload (so a stale 'verified' is tolerated, not 422'd)
# but always forced to 'pending' on create. The review-queue fields
# (reviewer_notes / reviewed_by / reviewed_at) are NOT settable here — they
# flow through /admin/exam-intelligence. Note: this table has no
# ``updated_at`` column, so PATCH must not set one.
_MENTION_FIELDS = {
    "syllabus_document_id", "exam_id", "exam_cycle_id", "exam_phase_id",
    "topic_id", "raw_text", "normalized_text", "mention_type",
    "confidence_score", "extraction_method", "metadata",
}
_MENTION_CREATE_FIELDS = _MENTION_FIELDS | {"reviewer_status"}
_MENTION_TYPES = ("explicit", "implied", "parent_topic_only", "derived")


@router.get("/syllabus-topic-mentions")
def list_syllabus_topic_mentions(
    syllabus_document_id: str | None = Query(default=None),
    exam_id: str | None = Query(default=None),
    exam_phase_id: str | None = Query(default=None),
    topic_id: str | None = Query(default=None),
    reviewer_status: str | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    query = supabase.table("syllabus_topic_mentions").select(
        "id, syllabus_document_id, exam_id, exam_cycle_id, exam_phase_id, topic_id, "
        "raw_text, normalized_text, mention_type, confidence_score, extraction_method, "
        "reviewer_status, reviewer_notes, metadata, created_at",
        count="exact",
    ).order("created_at", desc=True)
    if syllabus_document_id:
        query = query.eq("syllabus_document_id", syllabus_document_id)
    if exam_id:
        query = query.eq("exam_id", exam_id)
    if exam_phase_id:
        query = query.eq("exam_phase_id", exam_phase_id)
    if topic_id:
        query = query.eq("topic_id", topic_id)
    if reviewer_status:
        query = query.eq("reviewer_status", reviewer_status)
    if q:
        query = query.ilike("raw_text", f"%{q.strip()}%")
    res = query.range(offset, offset + limit - 1).execute()
    return {"items": res.data or [], "total": getattr(res, "count", None), "limit": limit, "offset": offset}


@router.post("/syllabus-topic-mentions")
def create_syllabus_topic_mention(
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    _reject_unknown(body.payload, _MENTION_CREATE_FIELDS, "syllabus_topic_mentions")
    row = {k: v for k, v in body.payload.items() if k in _MENTION_FIELDS}
    if not row.get("syllabus_document_id") or not row.get("exam_id") or not row.get("topic_id"):
        raise HTTPException(status_code=422, detail="syllabus_document_id, exam_id, topic_id are required")
    if row.get("mention_type") and row["mention_type"] not in _MENTION_TYPES:
        raise HTTPException(status_code=422, detail=f"mention_type must be one of {_MENTION_TYPES}")
    if not _safe_select(supabase, "syllabus_documents", id=row["syllabus_document_id"]):
        raise HTTPException(status_code=422, detail="syllabus_document_id does not resolve")
    if not _safe_select(supabase, "exams", id=row["exam_id"]):
        raise HTTPException(status_code=422, detail="exam_id does not resolve")
    if not _safe_select(supabase, "topics", id=row["topic_id"]):
        raise HTTPException(status_code=422, detail="topic_id does not resolve")
    # CMS feeds the review queue — a mention can never be born verified.
    row["reviewer_status"] = "pending"
    try:
        inserted = supabase.table("syllabus_topic_mentions").insert(row).execute().data or []
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=409, detail=f"Insert failed: {exc}")
    new = inserted[0] if inserted else row
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.syllabus_mention.create",
        entity_type="syllabus_topic_mention", entity_id=new.get("id"),
        new_value={"reason": body.reason, "row": new},
    )
    return {"ok": True, "audit_id": audit_id, "row": new}


@router.patch("/syllabus-topic-mentions/{mention_id}")
def update_syllabus_topic_mention(
    mention_id: str,
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Edit the data fields of a mention. ``reviewer_status`` (and the
    reviewer_notes/reviewed_by/reviewed_at trio) are NOT editable here —
    those move through the /admin/exam-intelligence review queue."""
    supabase = get_supabase_admin()
    existing = _safe_select(supabase, "syllabus_topic_mentions", id=mention_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Syllabus topic mention not found")
    _reject_unknown(body.payload, _MENTION_FIELDS, "syllabus_topic_mentions")
    patch = {k: v for k, v in body.payload.items() if k in _MENTION_FIELDS}
    if not patch:
        raise HTTPException(status_code=422, detail="No allowed fields in payload")
    if patch.get("mention_type") and patch["mention_type"] not in _MENTION_TYPES:
        raise HTTPException(status_code=422, detail=f"mention_type must be one of {_MENTION_TYPES}")
    # No updated_at column on this table (migration 031).
    updated = supabase.table("syllabus_topic_mentions").update(patch).eq("id", mention_id).execute().data or []
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.syllabus_mention.update",
        entity_type="syllabus_topic_mention", entity_id=mention_id,
        new_value={"reason": body.reason, "patch": patch, "previous": existing},
    )
    return {"ok": True, "audit_id": audit_id, "row": updated[0] if updated else existing | patch}


# ════════════════════════════════════════════════════════════════════════
#  PYQ sources (migration 032)
# ════════════════════════════════════════════════════════════════════════


# Operator-settable columns from migration 032. ``trust_status`` is forced to
# 'pending' on create (a source can't be born verified) but is PATCH-editable
# because pyq_sources has no separate review queue. No ``updated_at`` column.
_PYQ_SOURCE_FIELDS = {
    "exam_id", "source_id", "source_type", "source_url", "title",
    "trust_status", "metadata",
}
_PYQ_SOURCE_TYPES = ("official", "memory_based", "coaching", "community", "aggregator", "unknown")


@router.get("/pyq-sources")
def list_pyq_sources(
    exam_id: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    trust_status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    query = supabase.table("pyq_sources").select(
        "id, exam_id, source_id, source_type, source_url, title, trust_status, metadata, created_at",
        count="exact",
    ).order("created_at", desc=True)
    if exam_id:
        query = query.eq("exam_id", exam_id)
    if source_type:
        query = query.eq("source_type", source_type)
    if trust_status:
        query = query.eq("trust_status", trust_status)
    res = query.range(offset, offset + limit - 1).execute()
    return {"items": res.data or [], "total": getattr(res, "count", None), "limit": limit, "offset": offset}


@router.post("/pyq-sources")
def create_pyq_source(
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    _reject_unknown(body.payload, _PYQ_SOURCE_FIELDS, "pyq_sources")
    row = {k: v for k, v in body.payload.items() if k in _PYQ_SOURCE_FIELDS}
    if not row.get("exam_id"):
        raise HTTPException(status_code=422, detail="exam_id is required")
    if row.get("source_type") and row["source_type"] not in _PYQ_SOURCE_TYPES:
        raise HTTPException(status_code=422, detail=f"source_type must be one of {_PYQ_SOURCE_TYPES}")
    if not _safe_select(supabase, "exams", id=row["exam_id"]):
        raise HTTPException(status_code=422, detail="exam_id does not resolve")
    # CMS feeds the trust pipeline — a source lands pending.
    row["trust_status"] = "pending"
    try:
        inserted = supabase.table("pyq_sources").insert(row).execute().data or []
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=409, detail=f"Insert failed: {exc}")
    new = inserted[0] if inserted else row
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.pyq_source.create",
        entity_type="pyq_source", entity_id=new.get("id"),
        new_value={"reason": body.reason, "row": new},
    )
    return {"ok": True, "audit_id": audit_id, "row": new}


@router.patch("/pyq-sources/{source_id}")
def update_pyq_source(
    source_id: str,
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    existing = _safe_select(supabase, "pyq_sources", id=source_id)
    if not existing:
        raise HTTPException(status_code=404, detail="PYQ source not found")
    _reject_unknown(body.payload, _PYQ_SOURCE_FIELDS, "pyq_sources")
    patch = {k: v for k, v in body.payload.items() if k in _PYQ_SOURCE_FIELDS}
    if not patch:
        raise HTTPException(status_code=422, detail="No allowed fields in payload")
    if patch.get("source_type") and patch["source_type"] not in _PYQ_SOURCE_TYPES:
        raise HTTPException(status_code=422, detail=f"source_type must be one of {_PYQ_SOURCE_TYPES}")
    # No updated_at column on this table (migration 032).
    updated = supabase.table("pyq_sources").update(patch).eq("id", source_id).execute().data or []
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.pyq_source.update",
        entity_type="pyq_source", entity_id=source_id,
        new_value={"reason": body.reason, "patch": patch, "previous": existing},
    )
    return {"ok": True, "audit_id": audit_id, "row": updated[0] if updated else existing | patch}


# ════════════════════════════════════════════════════════════════════════
#  PYQ question topic tags — created at reviewer_status='pending'
# ════════════════════════════════════════════════════════════════════════


# Operator-settable columns from migration 032. ``reviewer_status`` is forced
# to 'pending' on create and moves only through the review queue; the
# reviewed_by/reviewed_at pair is review-queue-owned. No ``updated_at``.
_PYQ_TAG_FIELDS = {
    "question_id", "topic_id", "tag_weight", "tag_role", "tagging_source",
    "confidence_score", "metadata",
}
_PYQ_TAG_CREATE_FIELDS = _PYQ_TAG_FIELDS | {"reviewer_status"}
_PYQ_TAG_ROLES = ("primary", "secondary", "prerequisite", "trap", "calculation_layer", "conceptual_layer")
_PYQ_TAGGING_SOURCES = ("manual", "admin", "ai", "rule", "imported")


@router.get("/pyq-question-topic-tags")
def list_pyq_question_topic_tags(
    question_id: str | None = Query(default=None),
    topic_id: str | None = Query(default=None),
    reviewer_status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    query = supabase.table("pyq_question_topic_tags").select(
        "id, question_id, topic_id, tag_weight, tag_role, tagging_source, "
        "confidence_score, reviewer_status, metadata, created_at",
        count="exact",
    ).order("created_at", desc=True)
    if question_id:
        query = query.eq("question_id", question_id)
    if topic_id:
        query = query.eq("topic_id", topic_id)
    if reviewer_status:
        query = query.eq("reviewer_status", reviewer_status)
    res = query.range(offset, offset + limit - 1).execute()
    return {"items": res.data or [], "total": getattr(res, "count", None), "limit": limit, "offset": offset}


@router.post("/pyq-question-topic-tags")
def create_pyq_question_topic_tag(
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    _reject_unknown(body.payload, _PYQ_TAG_CREATE_FIELDS, "pyq_question_topic_tags")
    row = {k: v for k, v in body.payload.items() if k in _PYQ_TAG_FIELDS}
    if not row.get("question_id") or not row.get("topic_id"):
        raise HTTPException(status_code=422, detail="question_id and topic_id are required")
    if row.get("tag_role") and row["tag_role"] not in _PYQ_TAG_ROLES:
        raise HTTPException(status_code=422, detail=f"tag_role must be one of {_PYQ_TAG_ROLES}")
    if row.get("tagging_source") and row["tagging_source"] not in _PYQ_TAGGING_SOURCES:
        raise HTTPException(status_code=422, detail=f"tagging_source must be one of {_PYQ_TAGGING_SOURCES}")
    if not _safe_select(supabase, "pyq_questions", id=row["question_id"]):
        raise HTTPException(status_code=422, detail="question_id does not resolve")
    if not _safe_select(supabase, "topics", id=row["topic_id"]):
        raise HTTPException(status_code=422, detail="topic_id does not resolve")
    # CMS feeds the review queue — a tag can never be born verified.
    row["reviewer_status"] = "pending"
    try:
        inserted = supabase.table("pyq_question_topic_tags").insert(row).execute().data or []
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=409, detail=f"Insert failed: {exc}")
    new = inserted[0] if inserted else row
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.pyq_tag.create",
        entity_type="pyq_question_topic_tag", entity_id=new.get("id"),
        new_value={"reason": body.reason, "row": new},
    )
    return {"ok": True, "audit_id": audit_id, "row": new}


@router.patch("/pyq-question-topic-tags/{tag_id}")
def update_pyq_question_topic_tag(
    tag_id: str,
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Edit non-status fields. ``reviewer_status`` (and reviewed_by/reviewed_at)
    move only through the /admin/exam-intelligence review queue."""
    supabase = get_supabase_admin()
    existing = _safe_select(supabase, "pyq_question_topic_tags", id=tag_id)
    if not existing:
        raise HTTPException(status_code=404, detail="PYQ topic tag not found")
    _reject_unknown(body.payload, _PYQ_TAG_FIELDS, "pyq_question_topic_tags")
    patch = {k: v for k, v in body.payload.items() if k in _PYQ_TAG_FIELDS}
    if not patch:
        raise HTTPException(status_code=422, detail="No allowed fields in payload")
    if patch.get("tag_role") and patch["tag_role"] not in _PYQ_TAG_ROLES:
        raise HTTPException(status_code=422, detail=f"tag_role must be one of {_PYQ_TAG_ROLES}")
    if patch.get("tagging_source") and patch["tagging_source"] not in _PYQ_TAGGING_SOURCES:
        raise HTTPException(status_code=422, detail=f"tagging_source must be one of {_PYQ_TAGGING_SOURCES}")
    # No updated_at column on this table (migration 032).
    updated = supabase.table("pyq_question_topic_tags").update(patch).eq("id", tag_id).execute().data or []
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.pyq_tag.update",
        entity_type="pyq_question_topic_tag", entity_id=tag_id,
        new_value={"reason": body.reason, "patch": patch, "previous": existing},
    )
    return {"ok": True, "audit_id": audit_id, "row": updated[0] if updated else existing | patch}


@router.delete("/pyq-question-topic-tags/{tag_id}")
def delete_pyq_question_topic_tag(
    tag_id: str,
    reason: str = Query(..., min_length=8, max_length=500),
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Hard-delete: a tag is a pure relation row with a review surface but no
    dependents; removing a mis-tag is a legitimate operator action."""
    supabase = get_supabase_admin()
    existing = _safe_select(supabase, "pyq_question_topic_tags", id=tag_id)
    if not existing:
        raise HTTPException(status_code=404, detail="PYQ topic tag not found")
    supabase.table("pyq_question_topic_tags").delete().eq("id", tag_id).execute()
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.pyq_tag.delete",
        entity_type="pyq_question_topic_tag", entity_id=tag_id,
        new_value={"reason": reason, "deleted": existing},
    )
    return {"ok": True, "audit_id": audit_id, "id": tag_id}


# ════════════════════════════════════════════════════════════════════════
#  Bulk import — CSV/JSON paste-in for any CMS entity
# ════════════════════════════════════════════════════════════════════════
#
# One generic ``POST /bulk-import`` endpoint that accepts a list of rows
# plus an entity identifier. Each row goes through the same validation
# the single-row create endpoint applies — same allowed-field whitelist,
# same FK validation, same forced status. Per-row outcome is returned so
# the operator can fix the failed rows and re-submit only those.
#
# Default cap is 500 rows per call so a single request can't fan out forever.
# PYQ topic tags raise this to 2000 (see _DEFAULT_BULK_CAP / per-entity
# ``max_rows``): a 20-year PYQ archive produces tens of thousands of tags, so
# 500-row batches make seeding an exam impractical. 2000 keeps one request
# bounded while letting an operator import a full paper-set's tags at once.
_DEFAULT_BULK_CAP = 500
# Pydantic ceiling for any single bulk request. Per-entity caps (``max_rows``)
# stay below it: 500 default, 2000 for tags/questions, 4000 for pyq-options
# (a 20-year archive has ~4 options per question, so options outscale tags).
_MAX_BULK_CAP = 4000


class BulkImportBody(BaseModel):
    """Body for ``POST /bulk-import``.

    ``entity`` is one of the CMS slugs already used by the per-entity
    endpoints (``exam-families``, ``exams``, ``exam-cycles``, etc.).
    ``rows`` is the list of payloads — each payload matches the
    single-row ``payload`` shape. The Pydantic ceiling is the absolute max
    (``_MAX_BULK_CAP``); the per-entity cap is enforced in the handler.
    """

    reason: str = Field(..., min_length=8, max_length=500)
    entity: str = Field(..., min_length=4, max_length=50)
    rows: list[dict[str, Any]] = Field(..., min_length=1, max_length=_MAX_BULK_CAP)


# Per-entity import config. (allowed_fields, required_fields,
# enum_validations, forced_fields, fk_checks, audit_action)
_IMPORT_CONFIG: dict[str, dict[str, Any]] = {
    "exam-families": {
        "table": "exam_families",
        "allowed": _FAMILY_FIELDS,
        "required": ["slug", "name"],
        "forced": {},
        "fks": {},
        "enums": {},
        "audit": "exam_intel.cms.family.bulk_create",
    },
    "exams": {
        "table": "exams",
        "allowed": _EXAM_FIELDS,
        "required": ["slug", "name"],
        "forced": {},
        "fks": {"exam_family_id": "exam_families"},
        "enums": {"exam_type": _EXAM_TYPES},
        "audit": "exam_intel.cms.exam.bulk_create",
    },
    "exam-cycles": {
        "table": "exam_cycles",
        "allowed": _CYCLE_FIELDS,
        "required": ["exam_id", "year", "cycle_name"],
        "forced": {},
        "fks": {"exam_id": "exams"},
        "enums": {"status": _CYCLE_STATUSES},
        "audit": "exam_intel.cms.cycle.bulk_create",
    },
    "exam-phases": {
        "table": "exam_phases",
        "allowed": _PHASE_FIELDS,
        "required": ["exam_id", "phase_name", "phase_slug"],
        "forced": {},
        "fks": {"exam_id": "exams"},
        "enums": {"status": _PHASE_STATUSES},
        "audit": "exam_intel.cms.phase.bulk_create",
    },
    "syllabus-documents": {
        "table": "syllabus_documents",
        "allowed": _DOC_FIELDS,
        "required": ["exam_id", "document_type", "title"],
        "forced": {"trust_status": "pending"},  # CMS feeds the review queue
        "fks": {"exam_id": "exams"},
        "enums": {"document_type": _DOC_TYPES},
        "audit": "exam_intel.cms.syllabus_document.bulk_create",
    },
    "pyq-papers": {
        "table": "pyq_papers",
        "allowed": _PAPER_FIELDS,
        "required": ["exam_id", "year"],
        "forced": {"trust_status": "pending"},
        "fks": {"exam_id": "exams"},
        "enums": {"source_type": _PAPER_SOURCE_TYPES},
        "audit": "exam_intel.cms.pyq_paper.bulk_create",
    },
    "exam-topic-coverage": {
        "table": "exam_topic_coverage",
        "allowed": _COVERAGE_FIELDS,
        "required": ["exam_id", "topic_id"],
        "forced": {"reviewer_status": "pending_review"},
        "fks": {"exam_id": "exams"},
        "enums": {},
        "audit": "exam_intel.cms.coverage.bulk_create",
    },
    "policy-updates": {
        "table": "exam_policy_updates",
        "allowed": _POLICY_FIELDS,
        "required": ["exam_id", "update_type", "title"],
        "forced": {"reviewer_status": "pending"},
        "fks": {"exam_id": "exams"},
        "enums": {"update_type": _POLICY_UPDATE_TYPES},
        "audit": "exam_intel.cms.policy_update.bulk_create",
    },
    "exam-competition-metrics": {
        "table": "exam_competition_metrics",
        "allowed": _COMPETITION_FIELDS,
        "required": ["exam_id"],
        "forced": {"reviewer_status": "draft"},
        "fks": {"exam_id": "exams"},
        "enums": {"source_basis": _COMPETITION_SOURCE_BASIS},
        "audit": "exam_intel.cms.competition_metric.bulk_create",
    },
    # Taxonomy entities upsert on their natural key so re-importing the same
    # CSV is idempotent (no duplicate subjects/topics).
    "subjects": {
        "table": "subjects",
        "allowed": _SUBJECT_FIELDS,
        "required": ["slug", "name"],
        "forced": {},
        "fks": {},
        "enums": {},
        "audit": "exam_intel.cms.subject.bulk_create",
        "upsert_on": "slug",
    },
    "topics": {
        "table": "topics",
        "allowed": _TOPIC_FIELDS,
        "required": ["subject_id", "slug", "name"],
        "forced": {},
        "fks": {"subject_id": "subjects", "parent_topic_id": "topics"},
        "enums": {"level": _TOPIC_LEVELS},
        "audit": "exam_intel.cms.topic.bulk_create",
        "upsert_on": "subject_id,parent_topic_id,slug",
    },
    "syllabus-topic-mentions": {
        "table": "syllabus_topic_mentions",
        "allowed": _MENTION_FIELDS,
        "required": ["syllabus_document_id", "exam_id", "topic_id"],
        "forced": {"reviewer_status": "pending"},
        "fks": {
            "syllabus_document_id": "syllabus_documents",
            "exam_id": "exams",
            "topic_id": "topics",
        },
        "enums": {"mention_type": _MENTION_TYPES},
        "audit": "exam_intel.cms.syllabus_mention.bulk_create",
    },
    "exam-phase-sections": {
        "table": "exam_phase_sections",
        "allowed": _SECTION_FIELDS,
        "required": ["exam_phase_id", "subject_id", "section_label"],
        "forced": {},
        "fks": {"exam_phase_id": "exam_phases", "subject_id": "subjects"},
        "enums": {},
        "audit": "exam_intel.cms.exam_phase_section.bulk_create",
        "max_rows": 500,
        "upsert_on": "exam_phase_id,subject_id,section_label",
    },
    "pyq-question-topic-tags": {
        "table": "pyq_question_topic_tags",
        "allowed": _PYQ_TAG_FIELDS,
        "required": ["question_id", "topic_id"],
        "forced": {"reviewer_status": "pending"},
        "fks": {"question_id": "pyq_questions", "topic_id": "topics"},
        "enums": {"tag_role": _PYQ_TAG_ROLES, "tagging_source": _PYQ_TAGGING_SOURCES},
        "audit": "exam_intel.cms.pyq_tag.bulk_create",
        # PYQ archives span 20 years → tens of thousands of tags; a larger
        # batch makes seeding practical.
        "max_rows": 2000,
    },
    "pyq-questions": {
        "table": "pyq_questions",
        "allowed": _QUESTION_FIELDS,
        "required": ["pyq_paper_id", "question_text"],
        "forced": {"reviewer_status": "pending"},
        "fks": {"pyq_paper_id": "pyq_papers"},
        "enums": {"question_type": _QUESTION_TYPES},
        "audit": "exam_intel.cms.pyq_question.bulk_create",
        "max_rows": 2000,
        # Each question row may carry an inline ``options`` array; children are
        # inserted against the new question id after the parent insert.
        "inline": {"key": "options", "table": "pyq_options", "fk": "question_id", "allowed": _OPTION_FIELDS},
    },
    "pyq-options": {
        "table": "pyq_options",
        "allowed": _OPTION_FIELDS | {"question_id"},
        "required": ["question_id"],
        "forced": {},
        "fks": {"question_id": "pyq_questions"},
        "enums": {},
        "audit": "exam_intel.cms.pyq_option.bulk_create",
        # Options outnumber questions (~4:1 over a 20-year archive).
        "max_rows": 4000,
    },
}


def _validate_bulk_row(cfg: dict[str, Any], row: dict[str, Any], supabase, fk_cache: dict) -> tuple[dict | None, str | None]:
    """Validate one row against the entity config. Returns (cleaned_row, error_str).

    fk_cache is a per-call memo so 500 rows referencing 10 unique exam_ids
    cost 10 lookups, not 500.
    """
    if not isinstance(row, dict):
        return None, "row must be an object"
    cleaned = {k: v for k, v in row.items() if k in cfg["allowed"]}
    for req in cfg["required"]:
        if cleaned.get(req) in (None, ""):
            return None, f"missing required field {req!r}"
    for col, choices in cfg["enums"].items():
        v = cleaned.get(col)
        if v and v not in choices:
            return None, f"{col} must be one of {choices}"
    # Policy-update non-official affects_* check.
    if cfg["table"] == "exam_policy_updates" and (cleaned.get("source_type") or "official") != "official":
        for affect in ("affects_plan", "affects_deadline", "affects_eligibility",
                       "affects_documents", "affects_syllabus", "affects_vacancy"):
            if cleaned.get(affect):
                return None, f"non-official policy update cannot set {affect}=true"
    for col, fk_table in cfg["fks"].items():
        v = cleaned.get(col)
        if not v:
            continue
        cache_key = (fk_table, v)
        if cache_key in fk_cache:
            ok = fk_cache[cache_key]
        else:
            ok = bool(_safe_select(supabase, fk_table, id=v))
            fk_cache[cache_key] = ok
        if not ok:
            return None, f"{col}={v!r} does not resolve in {fk_table}"
    for col, val in cfg["forced"].items():
        cleaned[col] = val
    return cleaned, None


@router.post("/bulk-import")
def bulk_import(
    body: BulkImportBody,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Insert many CMS rows in one call.

    Per-row result: ``{index, ok, error?, row?}``. Successful rows are
    inserted individually so one bad row in the middle doesn't block
    earlier or later rows. For maximum atomicity per row we don't try
    to bulk-insert all clean rows in one go — that would surface a
    Postgres-level error with no row attribution.
    """
    cfg = _IMPORT_CONFIG.get(body.entity)
    if not cfg:
        raise HTTPException(status_code=422, detail=f"Unknown entity {body.entity!r}; known: {sorted(_IMPORT_CONFIG)}")
    cap = cfg.get("max_rows", _DEFAULT_BULK_CAP)
    if len(body.rows) > cap:
        raise HTTPException(status_code=422, detail=f"{body.entity!r} accepts at most {cap} rows per request; got {len(body.rows)}")
    supabase = get_supabase_admin()
    fk_cache: dict = {}
    results: list[dict[str, Any]] = []
    ok_count = 0
    error_count = 0
    for idx, raw in enumerate(body.rows):
        cleaned, err = _validate_bulk_row(cfg, raw, supabase, fk_cache)
        if err:
            results.append({"index": idx, "ok": False, "error": err})
            error_count += 1
            continue
        try:
            tbl = supabase.table(cfg["table"])
            upsert_on = cfg.get("upsert_on")
            if upsert_on:
                inserted = tbl.upsert(cleaned, on_conflict=upsert_on).execute().data or []
            else:
                inserted = tbl.insert(cleaned).execute().data or []
        except Exception as exc:  # noqa: BLE001
            results.append({"index": idx, "ok": False, "error": f"db: {str(exc)[:200]}"})
            error_count += 1
            continue
        row = inserted[0] if inserted else cleaned
        result: dict[str, Any] = {"index": idx, "ok": True, "row": row}
        # Insert any inline children (e.g. a question's options) against the
        # freshly-created parent id.
        inline = cfg.get("inline")
        if inline and isinstance(raw.get(inline["key"]), list) and row.get("id"):
            n = 0
            child_errors: list[dict] = []
            for child in raw[inline["key"]]:
                if not isinstance(child, dict):
                    continue
                child_row = {k: v for k, v in child.items() if k in inline["allowed"]}
                child_row[inline["fk"]] = row["id"]
                try:
                    supabase.table(inline["table"]).insert(child_row).execute()
                    n += 1
                except Exception as child_exc:  # noqa: BLE001
                    child_errors.append({
                        "label": child_row.get("option_label") or child_row.get(inline["fk"]),
                        "error": str(child_exc)[:200],
                    })
            if child_errors:
                # Roll back parent so we never leave a question without its options.
                try:
                    supabase.table(cfg["table"]).delete().eq("id", row["id"]).execute()
                except Exception:  # noqa: BLE001
                    pass
                results.append({"index": idx, "ok": False, "error": "options insert failed", "child_errors": child_errors})
                error_count += 1
                continue
            result["children_created"] = n
        results.append(result)
        ok_count += 1
    audit_id = _audit(
        supabase, admin, cfg["audit"],
        entity_type=cfg["table"], entity_id=None,
        new_value={
            "reason": body.reason,
            "total": len(body.rows),
            "ok": ok_count,
            "errors": error_count,
        },
    )
    return {
        "ok": error_count == 0,
        "audit_id": audit_id,
        "entity": body.entity,
        "total": len(body.rows),
        "ok_count": ok_count,
        "error_count": error_count,
        "results": results,
    }


# ─── Diagnostics ──────────────────────────────────────────────────────────────


class _DiagnosticsActionBody(BaseModel):
    reason: str = Field(..., min_length=1)


@router.get("/diagnostics")
def get_diagnostics(
    exam_id: str | None = Query(default=None),
    age_minutes: int = Query(default=30, ge=1),
    admin: dict = Depends(require_permission(PERM_CMS)),
    _: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    orphans = find_orphan_questions(supabase, exam_id=exam_id)
    stuck_docs = find_stuck_documents(supabase, age_minutes=age_minutes)
    stuck_jobs = find_stuck_text_extract_jobs(supabase, age_minutes=age_minutes)
    return {
        "generated_at": _now_iso(),
        "thresholds": {"stuck_age_minutes": age_minutes},
        "orphan_questions": {"count": len(orphans), "rows": orphans},
        "stuck_documents": {"count": len(stuck_docs), "rows": stuck_docs},
        "stuck_text_extract_jobs": {"count": len(stuck_jobs), "rows": stuck_jobs},
    }


@router.post("/diagnostics/orphan-question/{question_id}/delete")
def delete_orphan_question(
    question_id: str,
    body: _DiagnosticsActionBody,
    admin: dict = Depends(require_permission(PERM_CMS)),
    _: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    opts = (
        supabase.table("pyq_options")
        .select("question_id")
        .eq("question_id", question_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if opts:
        raise HTTPException(
            status_code=409,
            detail="question has options — no longer an orphan; delete aborted",
        )
    supabase.table("pyq_questions").delete().eq("id", question_id).execute()
    _audit(
        supabase,
        admin,
        "exam_intel.cms.diagnostics.orphan_question.delete",
        entity_type="pyq_questions",
        entity_id=question_id,
        new_value={"reason": body.reason},
    )
    return {"ok": True, "deleted_question_id": question_id}


@router.post("/diagnostics/stuck-document/{document_id}/reset")
def reset_stuck_document(
    document_id: str,
    body: _DiagnosticsActionBody,
    admin: dict = Depends(require_permission(PERM_CMS)),
    _: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    doc = _safe_select(supabase, "document_assets", id=document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document_asset not found")
    if doc.get("status") != "processing":
        raise HTTPException(
            status_code=409,
            detail=f"document status is '{doc.get('status')}', not 'processing' — reset aborted",
        )
    supabase.table("document_assets").update({"status": "uploaded"}).eq("id", document_id).execute()
    _audit(
        supabase,
        admin,
        "exam_intel.cms.diagnostics.stuck_document.reset",
        entity_type="document_assets",
        entity_id=document_id,
        new_value={"reason": body.reason, "previous_status": "processing", "new_status": "uploaded"},
    )
    return {"ok": True, "document_id": document_id, "new_status": "uploaded"}


@router.post("/diagnostics/stuck-job/{job_id}/reset")
def reset_stuck_job(
    job_id: str,
    body: _DiagnosticsActionBody,
    admin: dict = Depends(require_permission(PERM_CMS)),
    _: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    job = _safe_select(supabase, "document_processing_jobs", id=job_id)
    if not job:
        raise HTTPException(status_code=404, detail="document_processing_job not found")
    if job.get("status") != "running":
        raise HTTPException(
            status_code=409,
            detail=f"job status is '{job.get('status')}', not 'running' — reset aborted",
        )
    supabase.table("document_processing_jobs").update(
        {"status": "failed", "error_code": "manual_reset", "error_message": body.reason}
    ).eq("id", job_id).execute()
    _audit(
        supabase,
        admin,
        "exam_intel.cms.diagnostics.stuck_job.reset",
        entity_type="document_processing_jobs",
        entity_id=job_id,
        new_value={"reason": body.reason},
    )
    return {"ok": True, "job_id": job_id, "new_status": "failed", "error_code": "manual_reset"}
