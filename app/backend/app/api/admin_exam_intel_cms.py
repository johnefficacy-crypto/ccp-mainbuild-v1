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
from app.exam_intelligence.document_policy import CLASSIFIED_PHASE_KINDS
from app.exam_intelligence.lookup import invalidate_exam_lookup_cache
from app.exam_intelligence.option_normalize import option_hash, question_hash
from app.utils.safe import safe_required

logger = logging.getLogger("career_copilot.api.admin_exam_intel_cms")

router = APIRouter(prefix="/admin/exam-intelligence-cms", tags=["admin-exam-intelligence-cms"])

PERM_CMS = "exam_intelligence.cms"
PERM_REVIEW = "exam_intelligence.review"
# Normal Manage-Exam canonical editing tier (J2 gate §D, permissions.py
# lines 92-98). Candidate-count create/curate are ordinary operational edits,
# NOT Advanced Repair — they are gated on `manage`, not `cms`. `cms` stays
# exclusive to Advanced Repair; `review` stays exclusive to trust/lifecycle.
PERM_MANAGE = "exam_intelligence.manage"


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


def _safe_list(supabase, table: str, **filters) -> list[dict[str, Any]]:
    """Best-effort list of rows matching equality filters (returns [] on error)."""
    try:
        q = supabase.table(table).select("*")
        for k, v in filters.items():
            q = q.eq(k, v)
        return q.execute().data or []
    except Exception:  # noqa: BLE001
        return []


def _constraint_violation_http_error(exc: Exception) -> HTTPException | None:
    """Map a Postgres unique (23505) / check (23514) violation to a friendly
    HTTP error, or return None if the exception is not a recognised constraint
    violation (caller should then fall through to other handling / re-raise).

    supabase-py surfaces these as ``postgrest.exceptions.APIError`` carrying a
    ``.code`` (SQLSTATE) and a message that includes the offending
    index/constraint name; we match on the code first and fall back to the
    message so it stays robust across client versions."""
    code = getattr(exc, "code", None) or getattr(exc, "pgcode", None)
    msg = str(exc)
    low = msg.lower()
    is_unique = code == "23505" or "23505" in msg or "duplicate key" in low
    is_check = code == "23514" or "23514" in msg or "check constraint" in low

    if is_unique:
        # unique(question_id, stimulus_id) on pyq_question_stimuli.
        if ("question_id" in low and "stimulus_id" in low) or "question_id_stimulus_id" in low:
            detail = "a link between this question and stimulus already exists"
        elif "question_display_order" in low:
            detail = "display_order already used for this question"
        elif "paper_display_order" in low:
            detail = "display_order already used for this paper"
        else:
            detail = "a row with these unique values already exists"
        return HTTPException(status_code=409, detail=detail)

    if is_check:
        if "display_order" in low:
            detail = "display_order must be >= 1"
        else:
            detail = msg
        return HTTPException(status_code=422, detail=detail)

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
    "management_mode", "cadence",
}
_EXAM_TYPES = ("recruitment", "entrance", "certification", "opportunity", "other")
_EXAM_MGMT_MODES = ("core", "light", "index_only", "archive")
_EXAM_CADENCES = ("annual", "biannual", "recurring", "irregular", "one_off", "unknown")


def _exam_slug(name: str, org: dict | None) -> str:
    from app.common.strings import slugify
    if org and org.get("type") == "state_psc" and org.get("state"):
        return slugify(org["state"]) + "-" + slugify(name)
    return slugify(name)


@router.get("/exams")
def list_exams(
    is_active: bool | None = Query(default=None),
    exam_family_id: str | None = Query(default=None),
    exam_type: str | None = Query(default=None),
    management_mode: str | None = Query(default=None),
    cadence: str | None = Query(default=None),
    conducting_organization_id: str | None = Query(default=None),
    q: str | None = Query(default=None, description="Case-insensitive substring match on exam name."),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    query = supabase.table("exams").select(
        "id, exam_family_id, slug, name, exam_type, default_difficulty_level, description, is_active, metadata, conducting_organization_id, management_mode, cadence, created_at, updated_at",
        count="exact",
    ).order("created_at", desc=True)
    if is_active is not None:
        query = query.eq("is_active", is_active)
    if exam_family_id:
        query = query.eq("exam_family_id", exam_family_id)
    if exam_type:
        query = query.eq("exam_type", exam_type)
    if management_mode:
        query = query.eq("management_mode", management_mode)
    if cadence:
        query = query.eq("cadence", cadence)
    if conducting_organization_id:
        query = query.eq("conducting_organization_id", conducting_organization_id)
    if q and q.strip():
        query = query.ilike("name", f"%{q.strip()}%")
    res = query.range(offset, offset + limit - 1).execute()
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
    if "management_mode" in row and row["management_mode"] is not None and row["management_mode"] not in _EXAM_MGMT_MODES:
        raise HTTPException(status_code=422, detail=f"management_mode must be one of {_EXAM_MGMT_MODES}")
    if "cadence" in row and row["cadence"] is not None and row["cadence"] not in _EXAM_CADENCES:
        raise HTTPException(status_code=422, detail=f"cadence must be one of {_EXAM_CADENCES}")
    if row.get("exam_family_id") and not _safe_select(supabase, "exam_families", id=row["exam_family_id"]):
        raise HTTPException(status_code=422, detail="exam_family_id does not resolve")

    # Apply create-only defaults after validation so invalid explicit values still 422.
    row.setdefault("management_mode", "light")
    row.setdefault("cadence", "unknown")

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
    if "management_mode" in patch and patch["management_mode"] is not None and patch["management_mode"] not in _EXAM_MGMT_MODES:
        raise HTTPException(status_code=422, detail=f"management_mode must be one of {_EXAM_MGMT_MODES}")
    if "cadence" in patch and patch["cadence"] is not None and patch["cadence"] not in _EXAM_CADENCES:
        raise HTTPException(status_code=422, detail=f"cadence must be one of {_EXAM_CADENCES}")
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
    "phase_start", "phase_end", "phase_kind",
}
_PHASE_STATUSES = ("expected", "active", "completed", "cancelled")
# Canonical classified kinds are owned by document_policy (D05 §1). 'other' is a
# DB-legal explicit "unclassified" marker (migration 210 CHECK) — accepted here so
# the API surface matches the column constraint (422 here instead of a DB error).
_PHASE_KINDS = (*CLASSIFIED_PHASE_KINDS, "other")


def _validate_phase_kind(row: dict[str, Any]) -> None:
    """422 on unknown phase_kind; None/absent is allowed (unset / unclassified)."""
    if "phase_kind" in row and row["phase_kind"] is not None and row["phase_kind"] not in _PHASE_KINDS:
        raise HTTPException(
            status_code=422,
            detail=f"invalid_phase_kind: phase_kind must be one of {_PHASE_KINDS} or null",
        )


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
    _validate_phase_kind(row)
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
    _validate_phase_kind(patch)
    patch["updated_at"] = _now_iso()
    updated = supabase.table("exam_phases").update(patch).eq("id", phase_id).execute().data or []
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.phase.update",
        entity_type="exam_phase", entity_id=phase_id,
        new_value={"reason": body.reason, "patch": patch, "previous": existing},
    )
    return {"ok": True, "audit_id": audit_id, "row": updated[0] if updated else existing | patch}


class PromoteTemplateBody(BaseModel):
    template_phase_id: str
    target_cycle_id: str
    phase_start: str
    phase_end: str | None = None
    phase_order: int | None = None
    status: str | None = None
    reason: str = Field(..., min_length=8, max_length=500)


@router.post("/exam-phases/promote-template", status_code=201)
def promote_template_to_cycle(
    body: PromoteTemplateBody,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()

    # 1. Load source template phase
    source = _safe_select(supabase, "exam_phases", id=body.template_phase_id)
    if not source:
        raise HTTPException(status_code=404, detail="template phase not found")

    # 2. Must be a template (no cycle binding)
    if source.get("exam_cycle_id") is not None:
        raise HTTPException(status_code=422, detail="source_phase_must_be_template")

    # 3. Load target cycle
    cycle = _safe_select(supabase, "exam_cycles", id=body.target_cycle_id)
    if not cycle:
        raise HTTPException(status_code=404, detail="target cycle not found")

    # 4. Cycle must belong to the same exam
    if cycle.get("exam_id") != source.get("exam_id"):
        raise HTTPException(status_code=422, detail="target_cycle_exam_mismatch")

    # 5. Validate inputs
    if not body.phase_start:
        raise HTTPException(status_code=422, detail="phase_start is required")
    if body.phase_end is not None and body.phase_end < body.phase_start:
        raise HTTPException(status_code=422, detail="invalid_phase_date_range")
    if body.status is not None and body.status not in _PHASE_STATUSES:
        raise HTTPException(status_code=422, detail="invalid_status")

    # 6. Collision check
    existing_phases = supabase.table("exam_phases").select("id").eq(
        "exam_id", source["exam_id"]
    ).eq("exam_cycle_id", body.target_cycle_id).eq(
        "phase_slug", source["phase_slug"]
    ).execute().data or []
    if existing_phases:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "cycle_phase_already_exists",
                "existing_phase_id": existing_phases[0]["id"],
            },
        )

    # 7. Insert new phase via safe_required
    now_iso = _now_iso()
    new_row = {
        "exam_id": source["exam_id"],
        "exam_cycle_id": body.target_cycle_id,
        "phase_name": source["phase_name"],
        "phase_slug": source["phase_slug"],
        "phase_order": body.phase_order if body.phase_order is not None else source.get("phase_order", 0),
        "status": body.status or "expected",
        "phase_start": body.phase_start,
        "phase_end": body.phase_end,
        "metadata": {
            "promoted_from_template_phase_id": source["id"],
            "promoted_from_template_at": now_iso,
            "promoted_via": "exam_workspace.promote_template_to_cycle",
            "promote_reason": body.reason,
        },
    }
    inserted = safe_required(
        lambda: supabase.table("exam_phases").insert(new_row).execute(),
        op="exam_phases.promote_template_insert",
    )
    if inserted is None:
        raise HTTPException(status_code=500, detail="persist_failed")
    created = inserted[0]
    phase_id = created["id"]

    # 8. Required audit via safe_required (NOT _audit — must not silently swallow)
    audit_rows = safe_required(
        lambda: supabase.table("admin_audit_logs").insert({
            "actor_id": admin.get("id"),
            "actor_email": admin.get("email"),
            "action": "exam_intel.cms.phase.promote_template",
            "entity_type": "exam_phase",
            "entity_id": phase_id,
            "new_value": {
                "reason": body.reason,
                "template_phase_id": body.template_phase_id,
                "target_cycle_id": body.target_cycle_id,
                "row": created,
            },
            "notes": "admin_exam_intel_cms",
        }).execute(),
        op="admin_audit_logs.promote_template_insert",
    )
    if audit_rows is None:
        raise HTTPException(
            status_code=500,
            detail={"code": "audit_write_failed", "phase_id": phase_id},
        )

    # 9. Return 201 with created phase
    return {"ok": True, "audit_id": audit_rows[0].get("id") if audit_rows else None, "row": created}


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


# Allowed trust_status transitions for syllabus_documents (migration 257).
_SYLLABUS_ALLOWED_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "pending": ("verified", "rejected"),
    "verified": ("rejected", "superseded", "pending"),
    "rejected": ("pending",),
    "superseded": ("pending",),
}
_SYLLABUS_ALL_TARGET_STATUSES = frozenset(
    s for targets in _SYLLABUS_ALLOWED_TRANSITIONS.values() for s in targets
)


class SyllabusReviewBody(BaseModel):
    status: str = Field(..., description="Target trust_status: 'verified', 'rejected', 'pending', or 'superseded'")
    reason: str = Field(..., min_length=8, max_length=500)


@router.post("/syllabus-documents/{document_id}/review")
def review_syllabus_document(
    document_id: str,
    body: SyllabusReviewBody,
    admin: dict = Depends(require_permission(PERM_REVIEW)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Transition a syllabus document's trust_status (document trust gate).

    Promotion to ``verified`` is authoritative inside the
    ``review_syllabus_document`` RPC (migration 257): under a row lock it
    requires the linked ``document_assets`` row to be an authoritative
    (official_archive/official_scan), processed notification/corrigendum with
    populated storage, at least one extracted page, and matching exam (and
    cycle, when set); the reviewer must not be the document's uploader. Moving
    away from verified clears the reviewer attribution. Generic CMS create/link
    paths never set trust_status directly — this is the only promotion path.
    """
    if body.status not in _SYLLABUS_ALL_TARGET_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"status must be one of {sorted(_SYLLABUS_ALL_TARGET_STATUSES)}",
        )
    supabase = get_supabase_admin()
    existing = _safe_select(supabase, "syllabus_documents", id=document_id)
    if not existing:
        raise HTTPException(status_code=404, detail="syllabus_document not found")

    from_status = existing.get("trust_status", "pending")
    allowed = _SYLLABUS_ALLOWED_TRANSITIONS.get(from_status, ())
    if body.status not in allowed:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Transition '{from_status}' → '{body.status}' is not allowed. "
                f"Allowed targets from '{from_status}': {list(allowed)}"
            ),
        )

    try:
        result = supabase.rpc(
            "review_syllabus_document",
            {
                "p_document_id": document_id,
                "p_expected_status": from_status,
                "p_target_status": body.status,
                "p_reason": body.reason,
                "p_actor_id": admin.get("id"),
                "p_actor_email": admin.get("email"),
            },
        ).execute()
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        low = msg.lower()
        if "concurrent_modification" in low:
            raise HTTPException(
                status_code=409,
                detail="Concurrent modification: document trust_status changed since read. Re-fetch and retry.",
            ) from exc
        if "not_found" in low:
            raise HTTPException(status_code=404, detail="syllabus_document not found") from exc
        if "provenance_incomplete" in low:
            blocking: list[str] = []
            if "blocking_fields=" in low:
                fields_raw = low.split("blocking_fields=", 1)[1].split()[0].rstrip(".,")
                blocking = [f for f in fields_raw.split(",") if f]
            raise HTTPException(
                status_code=422,
                detail={"error": "provenance_incomplete", "blocking_fields": blocking},
            ) from exc
        if any(tok in low for tok in (
            "transition_not_allowed", "invalid_reason", "invalid_target_status",
        )):
            raise HTTPException(status_code=422, detail=msg) from exc
        logger.exception("review_syllabus_document RPC failed; no status change recorded")
        raise HTTPException(
            status_code=500,
            detail="Review transaction failed; no status change recorded.",
        ) from exc

    data = result.data
    return {"ok": True, "audit_id": data["audit_id"], "row": data["row"]}


# ════════════════════════════════════════════════════════════════════════
#  PYQ papers — created at trust_status='pending'
# ════════════════════════════════════════════════════════════════════════


_PAPER_FIELDS = {
    "pyq_source_id", "exam_id", "exam_cycle_id", "exam_phase_id",
    "year", "paper_date", "shift", "paper_code", "source_url",
    "source_type", "source_document_id", "content_hash", "metadata",
}
_PAPER_SOURCE_TYPES = ("official", "memory_based", "coaching", "community", "aggregator", "unknown")
# Provenance fields that require re-validation when a paper is verified.
# Changes to these fields on a verified paper must go through set-provenance.
_PROVENANCE_FIELDS = frozenset({"source_url", "source_type", "source_document_id", "pyq_source_id"})

# Scope fields (exam/cycle/phase identity). Changing any of these re-triggers the
# scope validator, and on a verified paper they are review-sensitive (EI-CLEAN-09).
_PAPER_SCOPE_FIELDS = frozenset({"exam_id", "exam_cycle_id", "exam_phase_id"})


def _pyq_paper_scope_error(
    supabase: Any,
    *,
    exam_id: Any,
    exam_cycle_id: Any,
    exam_phase_id: Any,
) -> str | None:
    """EI-CLEAN-09: full exam/cycle/phase scope integrity for the direct
    pyq_papers write paths (create / patch / bulk-import).

    ``pyq_papers.exam_id``, ``exam_cycle_id`` and ``exam_phase_id`` are
    independent FKs, so — mirroring the ``cms_pyq_onboarding`` RPC (migration
    220) — this validates each dimension independently and returns the same
    stable token vocabulary (mapped to HTTP 422 by callers), or ``None`` when the
    combination is consistent:

      * ``exam_not_found``            — supplied exam does not exist;
      * ``exam_cycle_not_found``      — supplied cycle does not exist;
      * ``exam_cycle_exam_mismatch``  — cycle belongs to a different exam;
      * ``exam_phase_not_found``      — supplied phase does not exist;
      * ``exam_phase_exam_mismatch``  — phase belongs to a different exam;
      * ``exam_phase_cycle_mismatch`` — phase not bound to the paper's cycle.

    Phase↔cycle uses null-safe equality: the paper's cycle must equal the
    phase's own cycle. An exam-level / cycle-agnostic phase (cycle NULL) is a
    legitimate target for an exam-level paper (cycle also NULL) — unlike the
    cycle-scoped onboarding modal, the general pyq_papers table supports
    exam-level phases, so both-NULL is consistent. A cycle-bound phase on a
    cycle-less paper (or vice versa) and a cross-cycle phase both fail closed.
    """
    if exam_id is not None:
        if not _safe_select(supabase, "exams", id=exam_id):
            return "exam_not_found"

    if exam_cycle_id is not None:
        cycle = _safe_select(supabase, "exam_cycles", id=exam_cycle_id)
        if not cycle:
            return "exam_cycle_not_found"
        if exam_id is not None and str(cycle.get("exam_id")) != str(exam_id):
            return "exam_cycle_exam_mismatch"

    if exam_phase_id:
        phase = _safe_select(supabase, "exam_phases", id=exam_phase_id)
        if not phase:
            return "exam_phase_not_found"
        if exam_id is not None and str(phase.get("exam_id")) != str(exam_id):
            return "exam_phase_exam_mismatch"
        phase_cycle = phase.get("exam_cycle_id")
        paper_cycle_none = exam_cycle_id is None
        phase_cycle_none = phase_cycle is None
        if paper_cycle_none != phase_cycle_none or (
            not paper_cycle_none and str(phase_cycle) != str(exam_cycle_id)
        ):
            return "exam_phase_cycle_mismatch"
    return None


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
    _pc_err = _pyq_paper_scope_error(
        supabase,
        exam_id=row.get("exam_id"),
        exam_cycle_id=row.get("exam_cycle_id"),
        exam_phase_id=row.get("exam_phase_id"),
    )
    if _pc_err:
        raise HTTPException(status_code=422, detail=_pc_err)
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
    # EI-CLEAN-09: a verified paper's scope identity (exam/cycle/phase) is
    # review-sensitive — reassigning trusted evidence to another exam/cycle/phase
    # must go back through review, not the generic curate endpoint.
    if existing.get("trust_status") == "verified" and _PAPER_SCOPE_FIELDS & set(patch):
        raise HTTPException(
            status_code=422,
            detail={
                "error": "scope_locked",
                "message": (
                    "Scope fields (exam_id, exam_cycle_id, exam_phase_id) cannot be "
                    "changed on a verified paper — reassigning trusted evidence to "
                    "another exam/cycle/phase requires re-review. Move the paper back "
                    "to pending first."
                ),
            },
        )
    # EI-CLEAN-09: re-validate the full exam/cycle/phase scope whenever the patch
    # touches ANY scope field, on the merged (existing ⊕ patch) values — so an
    # exam_id-only change still revalidates the retained cycle/phase, while
    # unrelated edits to a legacy row are never retroactively blocked.
    if _PAPER_SCOPE_FIELDS & set(patch):
        merged = {**existing, **patch}
        _pc_err = _pyq_paper_scope_error(
            supabase,
            exam_id=merged.get("exam_id"),
            exam_cycle_id=merged.get("exam_cycle_id"),
            exam_phase_id=merged.get("exam_phase_id"),
        )
        if _pc_err:
            raise HTTPException(status_code=422, detail=_pc_err)
    if existing.get("trust_status") == "verified" and _PROVENANCE_FIELDS & set(patch):
        raise HTTPException(
            status_code=422,
            detail={
                "error": "provenance_locked",
                "message": (
                    "Provenance fields (source_url, source_type, source_document_id) "
                    "cannot be changed on a verified paper. "
                    "Use POST /pyq-papers/{id}/set-provenance, which validates the new "
                    "provenance and moves the paper back to pending for re-review."
                ),
            },
        )
    updated = supabase.table("pyq_papers").update(patch).eq("id", paper_id).execute().data or []
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.pyq_paper.update",
        entity_type="pyq_paper", entity_id=paper_id,
        new_value={"reason": body.reason, "patch": patch, "previous": existing},
    )
    return {"ok": True, "audit_id": audit_id, "row": updated[0] if updated else existing | patch}


@router.post("/pyq-papers/{paper_id}/set-provenance")
def set_pyq_paper_provenance(
    paper_id: str,
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Update provenance fields with full document validation.

    Validates the resulting provenance state (same six invariants as
    review_pyq_paper). If the paper is currently verified it is automatically
    moved back to pending, requiring re-review before the projection RPC can run.
    """
    supabase = get_supabase_admin()
    existing = _safe_select(supabase, "pyq_papers", id=paper_id)
    if not existing:
        raise HTTPException(status_code=404, detail="pyq_paper not found")

    patch = {k: v for k, v in body.payload.items() if k in _PROVENANCE_FIELDS}
    if not patch:
        raise HTTPException(
            status_code=422,
            detail=f"Payload must contain at least one of: {sorted(_PROVENANCE_FIELDS)}",
        )
    if "source_type" in patch and patch["source_type"] not in _PAPER_SOURCE_TYPES:
        raise HTTPException(status_code=422, detail=f"source_type must be one of {_PAPER_SOURCE_TYPES}")

    # Compute the resulting provenance state after applying the patch
    result_source_type = patch.get("source_type", existing.get("source_type"))
    result_source_url = patch.get("source_url", existing.get("source_url"))
    result_source_doc_id = patch.get("source_document_id", existing.get("source_document_id"))
    result_pyq_source_id = patch.get("pyq_source_id", existing.get("pyq_source_id"))

    # Run the same provenance gate as review_pyq_paper (Python side; SQL RPC
    # re-runs it under DB lock at verification time)
    blocking: list[str] = []
    if result_source_type in (None, "", "unknown"):
        blocking.append("source_type")
    if not (result_source_url and str(result_source_url).strip()) and not result_source_doc_id:
        blocking.append("source_url")

    if result_source_doc_id:
        doc = _safe_select(supabase, "document_assets", id=result_source_doc_id)
        if not doc:
            blocking.append("source_document_id_not_found")
        else:
            if doc.get("scope") != "admin_exam_intelligence":
                blocking.append("source_document_id_wrong_scope")
            if doc.get("document_kind") != "pyq_paper":
                blocking.append("source_document_id_wrong_kind")
            if doc.get("status") in ("failed", "archived"):
                blocking.append("source_document_id_bad_status")
            if not doc.get("storage_bucket") or not doc.get("storage_path"):
                blocking.append("source_document_id_no_storage")
            doc_exam = (doc.get("metadata") or {}).get("exam_id")
            if doc_exam and doc_exam != existing.get("exam_id"):
                blocking.append("source_document_id_exam_mismatch")

    # Validate pyq_source_id when present in patch: must exist and belong to the same exam.
    if "pyq_source_id" in patch and patch["pyq_source_id"] is not None:
        pyq_src = _safe_select(supabase, "pyq_sources", id=patch["pyq_source_id"])
        if not pyq_src:
            blocking.append("pyq_source_id_not_found")
        elif pyq_src.get("exam_id") != existing.get("exam_id"):
            blocking.append("pyq_source_id_exam_mismatch")

    if blocking:
        raise HTTPException(
            status_code=422,
            detail={"error": "provenance_incomplete", "blocking_fields": blocking},
        )

    was_verified = existing.get("trust_status") == "verified"

    try:
        rpc_data = supabase.rpc(
            "cms_set_pyq_paper_provenance",
            {
                "p_paper_id":            paper_id,
                "p_actor_id":            admin.get("id"),
                "p_actor_email":         admin.get("email"),
                "p_patch":               patch,
                "p_reason":              body.reason,
                "p_previous_provenance": {k: existing.get(k) for k in _PROVENANCE_FIELDS},
                "p_was_verified":        was_verified,
            },
        ).execute().data
    except Exception as exc:
        msg = str(exc)
        msg_lower = msg.lower()
        if "provenance_incomplete" in msg_lower:
            blocking_exc: list[str] = []
            if "blocking_fields=" in msg_lower:
                fields_raw = msg_lower.split("blocking_fields=", 1)[1].split()[0].rstrip(".,")
                blocking_exc = [f for f in fields_raw.split(",") if f]
            raise HTTPException(
                status_code=422,
                detail={"error": "provenance_incomplete", "blocking_fields": blocking_exc},
            ) from exc
        if "not_found" in msg_lower:
            raise HTTPException(status_code=404, detail=msg) from exc
        logger.exception("cms_set_pyq_paper_provenance RPC failed; mutation rolled back")
        raise HTTPException(
            status_code=500,
            detail="Provenance update failed; no change was recorded.",
        ) from exc
    rpc = rpc_data or {}
    # Re-select the paper after the RPC so the response row is always authoritative.
    # Using the pre-lock `existing` snapshot would expose any concurrent field change
    # to an unpatched column as stale data in the caller's UI.
    paper_after = _safe_select(supabase, "pyq_papers", id=paper_id)
    return {
        "ok": True,
        "audit_id": rpc.get("audit_id"),
        "demoted_from_verified": rpc.get("demoted_from_verified", False),
        "row": paper_after if paper_after is not None else {
            **existing, **patch,
            "trust_status": rpc.get("trust_status_after", existing.get("trust_status")),
        },
    }


# ════════════════════════════════════════════════════════════════════════
#  Contextual PYQ onboarding — atomic create-source + create-paper + link-doc
#  (APPROVED gate: PYQ-Source-and-Paper-Onboarding-Gate-2026-06-25.md §B.4/B.5)
# ════════════════════════════════════════════════════════════════════════


class PyqOnboardingSource(BaseModel):
    """Optional source block. Either reuse an existing source via
    ``existing_pyq_source_id`` (no creation, no trust mutation — OD-2) or supply
    a creatable source. ``source_id`` is the canonical FK to ``source_registry``
    (admitted by ``_PYQ_SOURCE_FIELDS``)."""

    existing_pyq_source_id: str | None = None
    source_id: str | None = None
    source_type: str | None = "official"
    title: str | None = None
    source_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PyqOnboardingPaper(BaseModel):
    """Required paper block. Always born ``pending``."""

    year: int
    paper_date: str | None = None
    shift: str | None = None
    paper_code: str | None = None
    source_url: str | None = None
    source_type: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PyqOnboardingBody(BaseModel):
    reason: str = Field(..., min_length=8, max_length=500)
    exam_id: str
    exam_cycle_id: str | None = None
    exam_phase_id: str | None = None
    source: PyqOnboardingSource | None = None
    paper: PyqOnboardingPaper
    document_id: str | None = None


@router.post("/pyq-onboarding")
def pyq_onboarding(
    body: PyqOnboardingBody,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Atomically create an optional PYQ source, a pending PYQ paper, and an
    optional document link inside a single transactional SECURITY DEFINER RPC.

    All database changes (source insert, paper insert, document link, three
    audit rows) commit together or roll back together — there is no
    application-level rollback (OD-6).  Source and paper are always born
    ``pending``; an existing source's ``trust_status`` is never mutated
    (OD-1 / OD-2).
    """
    supabase = get_supabase_admin()

    src = body.source
    if src is not None:
        # Validate the create-path source_type early (the RPC re-validates under
        # the lock; this gives the operator an immediate, specific 422).
        if (
            src.existing_pyq_source_id is None
            and src.source_type
            and src.source_type not in _PYQ_SOURCE_TYPES
        ):
            raise HTTPException(
                status_code=422,
                detail=f"source.source_type must be one of {_PYQ_SOURCE_TYPES}",
            )

    if body.paper.source_type and body.paper.source_type not in _PAPER_SOURCE_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"paper.source_type must be one of {_PAPER_SOURCE_TYPES}",
        )

    p_source: dict[str, Any] | None = None
    if src is not None:
        p_source = {
            "existing_pyq_source_id": src.existing_pyq_source_id,
            "source_id": src.source_id,
            "source_type": src.source_type,
            "title": src.title,
            "source_url": src.source_url,
            "metadata": src.metadata,
        }

    p_paper = {
        "year": body.paper.year,
        "paper_date": body.paper.paper_date,
        "shift": body.paper.shift,
        "paper_code": body.paper.paper_code,
        "source_url": body.paper.source_url,
        "source_type": body.paper.source_type,
        "metadata": body.paper.metadata,
    }

    try:
        rpc_data = supabase.rpc(
            "cms_pyq_onboarding",
            {
                "p_actor_id": admin.get("id"),
                "p_actor_email": admin.get("email"),
                "p_reason": body.reason,
                "p_exam_id": body.exam_id,
                "p_exam_cycle_id": body.exam_cycle_id,
                "p_exam_phase_id": body.exam_phase_id,
                "p_source": p_source,
                "p_paper": p_paper,
                "p_document_id": body.document_id,
            },
        ).execute().data
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        msg_lower = msg.lower()
        if "document_not_linkable" in msg_lower:
            blocking: list[str] = []
            if "blocking_fields=" in msg_lower:
                fields_raw = msg_lower.split("blocking_fields=", 1)[1].split()[0].rstrip(".,")
                blocking = [f for f in fields_raw.split(",") if f]
            raise HTTPException(
                status_code=422,
                detail={"error": "document_not_linkable", "blocking_fields": blocking},
            ) from exc
        if any(
            tok in msg_lower
            for tok in (
                "invalid_reason",
                "exam_not_found",
                "exam_cycle_not_found",
                "exam_cycle_exam_mismatch",
                "exam_phase_not_found",
                "exam_phase_exam_mismatch",
                "exam_phase_cycle_mismatch",
                "pyq_source_not_found",
                "pyq_source_exam_mismatch",
                "invalid_source_type",
                "invalid_paper",
            )
        ):
            raise HTTPException(status_code=422, detail=msg) from exc
        logger.exception("cms_pyq_onboarding RPC failed; transaction rolled back")
        raise HTTPException(
            status_code=500,
            detail="PYQ onboarding failed; no change was recorded.",
        ) from exc

    rpc = rpc_data or {}
    return {
        "ok": True,
        "audit_id": rpc.get("audit_id"),
        "source": rpc.get("source"),
        "paper": rpc.get("paper"),
        "document_link": rpc.get("document_link"),
    }


# Allowed trust_status transitions for pyq_papers.
# Any transition not listed here is rejected with 422.
_ALLOWED_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "pending":  ("verified", "rejected"),
    "verified": ("rejected",),
    "rejected": ("pending",),
}

# Provenance anchor: either source_url or source_document_id must be present.
# source_type must always be a known value. Document content validation is
# authoritative inside the RPC (under the row lock); Python only checks that
# at least one anchor field is populated so the operator gets an early signal.

# All valid target statuses (union of all allowed-transition values)
_ALL_TARGET_STATUSES = frozenset(s for targets in _ALLOWED_TRANSITIONS.values() for s in targets)


class PaperReviewBody(BaseModel):
    status: str = Field(..., description="Target trust_status: 'verified', 'rejected', or 'pending'")
    reason: str = Field(..., min_length=8, max_length=500)


@router.post("/pyq-papers/{paper_id}/review")
def review_pyq_paper(
    paper_id: str,
    body: PaperReviewBody,
    admin: dict = Depends(require_permission(PERM_REVIEW)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Transition a PYQ paper's trust_status.

    Allowed transitions::

        pending  → verified | rejected
        verified → rejected
        rejected → pending

    For ``pending → verified``, the paper must have ``source_url`` set and
    ``source_type`` not 'unknown'; a 422 with ``blocking_fields`` is returned
    otherwise so the operator can complete the record first.

    The audit log is written **before** the status update so the intent is
    always captured even if the subsequent UPDATE fails.  The UPDATE is
    guarded on the current trust_status (optimistic-lock) to prevent silent
    overwrites when two operators act concurrently.
    """
    if body.status not in _ALL_TARGET_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"status must be one of {sorted(_ALL_TARGET_STATUSES)}",
        )
    supabase = get_supabase_admin()
    existing = _safe_select(supabase, "pyq_papers", id=paper_id)
    if not existing:
        raise HTTPException(status_code=404, detail="pyq_paper not found")

    from_status = existing.get("trust_status", "pending")
    allowed = _ALLOWED_TRANSITIONS.get(from_status, ())
    if body.status not in allowed:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Transition '{from_status}' → '{body.status}' is not allowed. "
                f"Allowed targets from '{from_status}': {list(allowed)}"
            ),
        )

    # Provenance gate: pending → verified requires (a) valid source_type and
    # (b) at least one anchor — non-empty source_url OR a source_document_id.
    # Document content validation is authoritative in the RPC (under the row
    # lock); Python only gives an early signal on obviously missing anchors.
    if from_status == "pending" and body.status == "verified":
        blocking: list[str] = []
        if existing.get("source_type") in (None, "", "unknown"):
            blocking.append("source_type")
        if (not (existing.get("source_url") and str(existing.get("source_url")).strip())
                and not existing.get("source_document_id")):
            blocking.append("source_url")
        if blocking:
            raise HTTPException(
                status_code=422,
                detail={"error": "provenance_incomplete", "blocking_fields": blocking},
            )

    # Single atomic RPC: audit INSERT + paper UPDATE in one DB transaction.
    # If a concurrent writer changed trust_status between the SELECT above and
    # the RPC, the function detects it via SELECT FOR UPDATE + expected-status
    # guard and raises "concurrent_modification" → both writes are rolled back
    # (no false audit rows).
    try:
        result = supabase.rpc(
            "review_pyq_paper",
            {
                "p_paper_id":        paper_id,
                "p_expected_status": from_status,
                "p_target_status":   body.status,
                "p_reason":          body.reason,
                "p_actor_id":        admin.get("id"),
                "p_actor_email":     admin.get("email"),
            },
        ).execute()
    except Exception as exc:
        msg = str(exc)
        msg_lower = msg.lower()
        # concurrent_modification → 409
        if "concurrent_modification" in msg_lower:
            raise HTTPException(
                status_code=409,
                detail="Concurrent modification: paper trust_status changed since read. Re-fetch and retry.",
            ) from exc
        # provenance_incomplete → 422 with structured blocking_fields
        if "provenance_incomplete" in msg_lower:
            blocking: list[str] = []
            if "blocking_fields=" in msg_lower:
                fields_raw = msg_lower.split("blocking_fields=", 1)[1].split()[0].rstrip(".,")
                blocking = [f for f in fields_raw.split(",") if f]
            raise HTTPException(
                status_code=422,
                detail={"error": "provenance_incomplete", "blocking_fields": blocking},
            ) from exc
        # other RPC contract failures → 422
        if any(tok in msg_lower for tok in (
            "transition_not_allowed", "invalid_reason",
            "invalid_target_status", "not_allowed",
        )):
            raise HTTPException(status_code=422, detail=msg) from exc
        # paper deleted between SELECT and RPC → 404
        if "not_found" in msg_lower:
            raise HTTPException(status_code=404, detail=msg) from exc
        logger.exception("review_pyq_paper RPC failed; no status change recorded")
        raise HTTPException(
            status_code=500,
            detail="Review transaction failed; no status change recorded.",
        ) from exc

    data = result.data
    return {"ok": True, "audit_id": data["audit_id"], "row": data["row"]}


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
    paper = _safe_select(supabase, "pyq_papers", id=paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="pyq_paper not found")
    if paper.get("source_document_id") != document_id:
        raise HTTPException(status_code=403, detail="document not attached to this paper")

    asset = (
        supabase.table("document_assets")
        .select("id, scope, document_kind, status, storage_bucket, storage_path, original_filename, page_count, metadata")
        .eq("id", document_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not asset:
        raise HTTPException(status_code=404, detail="document_asset not found")
    row = asset[0]

    # Re-run the same document invariants enforced by review_pyq_paper RPC.
    # Prevents signing a URL for a document that would fail verification.
    doc_errors: list[str] = []
    if row.get("scope") != "admin_exam_intelligence":
        doc_errors.append("source_document_id_wrong_scope")
    if row.get("document_kind") != "pyq_paper":
        doc_errors.append("source_document_id_wrong_kind")
    if row.get("status") in ("failed", "archived"):
        doc_errors.append("source_document_id_bad_status")
    if not row.get("storage_bucket") or not row.get("storage_path"):
        doc_errors.append("source_document_id_no_storage")
    doc_exam = (row.get("metadata") or {}).get("exam_id")
    if doc_exam and doc_exam != paper.get("exam_id"):
        doc_errors.append("source_document_id_exam_mismatch")
    if doc_errors:
        raise HTTPException(
            status_code=403,
            detail={"error": "document_not_signable", "reasons": doc_errors},
        )

    bucket = row.get("storage_bucket")
    path = row.get("storage_path")

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
            supabase, admin, body.import_token,
            paper_id=paper_id, override_errors=body.override_errors,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        # Batch-level conflict (e.g. checkpost round 3 fix #3b: a stimulus
        # ref's content diverges from the already-canonical stored row) —
        # mirrors preflight's existing ValueError -> 422 mapping. Raised
        # before any writes, so nothing was committed.
        raise HTTPException(status_code=422, detail=str(exc)) from exc

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
    # Section linkage + printed-order preservation (migration 223, PR-3).
    # section_id assignment is backstopped by DB triggers enforcing the
    # question's section shares its paper's exam_phase_id.
    "section_id", "source_question_ref", "display_order",
}
_QUESTION_TYPES = ("mcq", "numerical", "descriptive", "caselet", "matching", "other")
_OPTION_FIELDS = {
    "option_label", "option_text", "normalized_option_hash", "normalized_value",
    "is_correct", "metadata",
    # Printed label + explicit display order (migration 223, PR-3).
    "display_order", "source_label",
}


@router.get("/pyq-questions")
def list_pyq_questions(
    pyq_paper_id: str | None = Query(default=None),
    reviewer_status: str | None = Query(default=None),
    source_kind: str | None = Query(default=None),
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
    if source_kind:
        q = q.eq("source_kind", source_kind)
    res = q.range(offset, offset + limit - 1).execute()
    return {"items": res.data or [], "total": getattr(res, "count", None), "limit": limit, "offset": offset}


@router.get("/pyq-questions/{question_id}")
def get_pyq_question(
    question_id: str,
    _admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    rows = (
        supabase.table("pyq_questions")
        .select("*")
        .eq("id", question_id)
        .limit(1)
        .execute()
        .data
    ) or []
    if not rows:
        raise HTTPException(status_code=404, detail="Question not found")
    return rows[0]


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
    # Assigning section_id is backstopped by migration 223's DB trigger, which
    # enforces the question's section shares its paper's exam_phase_id (and that
    # any existing stimulus link stays section-compatible). Surface that trigger
    # failure as a 422 with the DB message rather than a raw 500.
    if "section_id" in patch and patch.get("section_id") is not None:
        try:
            updated = supabase.table("pyq_questions").update(patch).eq("id", question_id).execute().data or []
        except Exception as exc:  # noqa: BLE001
            msg = str(exc)
            if "exam_phase" in msg or "section" in msg:
                raise HTTPException(status_code=422, detail=msg) from exc
            raise
    else:
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
    limit: int = Query(default=50, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """List PYQ options with pagination, optionally filtered by question_id."""
    supabase = get_supabase_admin()
    q = (
        supabase.table("pyq_options")
        .select("*", count="exact")
        .order("option_label", desc=False)
        .order("id", desc=False)
    )
    if question_id:
        q = q.eq("question_id", question_id)
    res = q.range(offset, offset + limit - 1).execute()
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
#  PYQ stimuli (shared passages / caselets / DI tables) + question links
#  Migration 223 (PR-3). Stimuli are created at reviewer_status='pending'
#  (DB default) and reviewed INDEPENDENTLY through the review-side router —
#  shared passage CONTENT is not auto-verified by a question's review,
#  because the same passage may back other still-unreviewed questions. Only
#  the question→stimulus LINK is cascaded by question review (migration 227).
# ════════════════════════════════════════════════════════════════════════


# reviewer_status is intentionally absent — lifecycle moves go through the
# review-side router (PATCH /items/pyq_stimulus/{id}/review), never curate.
_STIMULUS_FIELDS = {
    "pyq_paper_id", "section_id", "stimulus_type", "content_text",
    "language", "display_order", "metadata",
    # Media fields (PR-11 slice 1, migration 233): first-class media storage.
    "document_asset_id", "asset_locator", "alt_text",
}
_STIMULUS_TYPES = ("passage", "caselet", "table", "chart", "image", "diagram", "other")
# Text stimuli (passage/caselet/table) and media stimuli (image/chart/diagram)
# are authored from this surface. Media rows are validated by migration 233's
# pyq_stimuli_media_guard() (a linked document_asset_id must be a live
# admin_exam_intelligence image asset; verification later requires alt_text +
# a linked asset), so this layer just passes the fields through and surfaces the
# DB guard as 422. 'other' has no defined authoring contract yet and stays
# deferred. READS of any pre-existing rows are NOT gated — only writes.
_STIMULUS_TYPES_CREATABLE = frozenset(("passage", "caselet", "table", "image", "chart", "diagram"))
_LINK_FIELDS = {"question_id", "stimulus_id", "display_order"}

# Substrings of migration 233 pyq_stimuli_media_guard() raises (and the 223
# section trigger) that indicate a client-fixable bad write → HTTP 422.
_STIMULUS_GUARD_422_MARKERS = (
    "exam_phase", "section",
    "document_asset_id", "document_kind", "unusable status",
    "media_stimulus_requires_alt_text", "media_stimulus_requires_asset",
)


def _reject_uncreatable_stimulus_type(stimulus_type: Any) -> None:
    """422 when a create/edit tries to set a stimulus_type with no authoring
    contract on this surface yet ('other'). Media types (image/chart/diagram)
    ARE creatable and validated by the DB media guard. Assumes the value already
    passed the full-enum check."""
    if stimulus_type is not None and stimulus_type not in _STIMULUS_TYPES_CREATABLE:
        raise HTTPException(
            status_code=422,
            detail=(
                f"stimulus_type {stimulus_type!r} is not creatable from this "
                "surface; use passage/caselet/table or a media type "
                "(image/chart/diagram)"
            ),
        )


@router.get("/pyq-stimuli")
def list_pyq_stimuli(
    pyq_paper_id: str | None = Query(default=None),
    reviewer_status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """List PYQ stimuli, filtered by paper (and optional reviewer_status),
    ordered by display_order (nulls last) then created_at."""
    supabase = get_supabase_admin()
    q = (
        supabase.table("pyq_stimuli")
        .select("*", count="exact")
        .order("display_order", desc=False, nullsfirst=False)
        .order("created_at", desc=False)
    )
    if pyq_paper_id:
        q = q.eq("pyq_paper_id", pyq_paper_id)
    if reviewer_status:
        q = q.eq("reviewer_status", reviewer_status)
    res = q.range(offset, offset + limit - 1).execute()
    return {"items": res.data or [], "total": getattr(res, "count", None), "limit": limit, "offset": offset}


@router.post("/pyq-stimuli")
def create_pyq_stimulus(
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Create a shared stimulus. Lands at reviewer_status='pending' (DB
    default) — reviewer_status is never accepted here; promotion is the
    review router's job. A bad section_id is backstopped by migration 223's
    trigger (section must share the paper's exam_phase_id) → surfaced as 422."""
    supabase = get_supabase_admin()
    row = {k: v for k, v in body.payload.items() if k in _STIMULUS_FIELDS}
    if not row.get("pyq_paper_id"):
        raise HTTPException(status_code=422, detail="pyq_paper_id is required")
    if row.get("stimulus_type") and row["stimulus_type"] not in _STIMULUS_TYPES:
        raise HTTPException(status_code=422, detail=f"stimulus_type must be one of {_STIMULUS_TYPES}")
    _reject_uncreatable_stimulus_type(row.get("stimulus_type"))
    try:
        inserted = supabase.table("pyq_stimuli").insert(row).execute().data or []
    except Exception as exc:  # noqa: BLE001
        mapped = _constraint_violation_http_error(exc)
        if mapped is not None:
            raise mapped from exc
        msg = str(exc)
        if any(m in msg for m in _STIMULUS_GUARD_422_MARKERS):
            raise HTTPException(status_code=422, detail=msg) from exc
        raise
    new = inserted[0] if inserted else row
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.pyq_stimulus.create",
        entity_type="pyq_stimulus", entity_id=new.get("id"),
        new_value={"reason": body.reason, "row": new},
    )
    return {"ok": True, "audit_id": audit_id, "row": new}


@router.patch("/pyq-stimuli/{stimulus_id}")
def update_pyq_stimulus(
    stimulus_id: str,
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Curate a stimulus. pyq_paper_id (reparenting the paper) and
    reviewer_status are NOT allowed here — lifecycle moves belong to the
    review router. Note: migration 223's trigger (extended by 233) downgrades a
    *verified* stimulus back to 'needs_correction' when content_text/
    stimulus_type/language/metadata or the media fields (alt_text/
    document_asset_id/asset_locator) change, so no extra code is needed here."""
    supabase = get_supabase_admin()
    existing = _safe_select(supabase, "pyq_stimuli", id=stimulus_id)
    if not existing:
        raise HTTPException(status_code=404, detail="pyq_stimulus not found")
    # Exclude pyq_paper_id from curate — no reparenting via this endpoint.
    patch = {k: v for k, v in body.payload.items() if k in (_STIMULUS_FIELDS - {"pyq_paper_id"})}
    if not patch:
        raise HTTPException(status_code=422, detail="No allowed fields in payload")
    if patch.get("stimulus_type") and patch["stimulus_type"] not in _STIMULUS_TYPES:
        raise HTTPException(status_code=422, detail=f"stimulus_type must be one of {_STIMULUS_TYPES}")
    _reject_uncreatable_stimulus_type(patch.get("stimulus_type"))
    try:
        updated = supabase.table("pyq_stimuli").update(patch).eq("id", stimulus_id).execute().data or []
    except Exception as exc:  # noqa: BLE001
        mapped = _constraint_violation_http_error(exc)
        if mapped is not None:
            raise mapped from exc
        msg = str(exc)
        if any(m in msg for m in _STIMULUS_GUARD_422_MARKERS):
            raise HTTPException(status_code=422, detail=msg) from exc
        raise
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.pyq_stimulus.update",
        entity_type="pyq_stimulus", entity_id=stimulus_id,
        new_value={"reason": body.reason, "patch": patch, "previous": existing},
    )
    return {"ok": True, "audit_id": audit_id, "row": updated[0] if updated else existing | patch}


@router.delete("/pyq-stimuli/{stimulus_id}")
def delete_pyq_stimulus(
    stimulus_id: str,
    reason: str = Query(..., min_length=8, max_length=500),
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Hard-delete a stimulus (its question links cascade-delete via FK).

    Content-integrity guard (fix #3): a stimulus may NOT be deleted while any
    question it provides context to is terminally 'verified' — that would leave
    a verified question whose reviewed passage/table context is gone. Move those
    questions to needs_correction/rejected first. Deletion is allowed when no
    linked question is verified."""
    supabase = get_supabase_admin()
    existing = _safe_select(supabase, "pyq_stimuli", id=stimulus_id)
    if not existing:
        raise HTTPException(status_code=404, detail="pyq_stimulus not found")

    # Resolve the links this delete would cascade, and the questions they back.
    links = _safe_list(supabase, "pyq_question_stimuli", stimulus_id=stimulus_id)
    linked_question_ids = [l.get("question_id") for l in links if l.get("question_id")]
    verified_question_ids: list[str] = []
    if linked_question_ids:
        q_rows = (
            supabase.table("pyq_questions")
            .select("id, reviewer_status")
            .in_("id", linked_question_ids)
            .execute()
            .data
            or []
        )
        verified_question_ids = [
            r.get("id") for r in q_rows if r.get("reviewer_status") == "verified"
        ]
    if verified_question_ids:
        raise HTTPException(
            status_code=409,
            detail=(
                f"cannot delete a stimulus while {len(verified_question_ids)} linked "
                "question(s) are verified; move those questions to "
                "needs_correction/rejected first"
            ),
        )

    supabase.table("pyq_stimuli").delete().eq("id", stimulus_id).execute()
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.pyq_stimulus.delete",
        entity_type="pyq_stimulus", entity_id=stimulus_id,
        new_value={
            "reason": reason,
            "previous": existing,
            "cascade_deleted_link_count": len(links),
            "linked_question_count": len(linked_question_ids),
        },
    )
    return {
        "ok": True,
        "audit_id": audit_id,
        "deleted": existing,
        "cascade_deleted_link_count": len(links),
    }


@router.get("/pyq-question-stimuli")
def list_pyq_question_stimuli(
    question_id: str | None = Query(default=None),
    stimulus_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """List question↔stimulus links, filtered by question_id and/or
    stimulus_id (at least one required). Ordered by display_order (nulls
    last) then created_at."""
    if not question_id and not stimulus_id:
        raise HTTPException(status_code=422, detail="question_id or stimulus_id is required")
    supabase = get_supabase_admin()
    q = (
        supabase.table("pyq_question_stimuli")
        .select("*", count="exact")
        .order("display_order", desc=False, nullsfirst=False)
        .order("created_at", desc=False)
    )
    if question_id:
        q = q.eq("question_id", question_id)
    if stimulus_id:
        q = q.eq("stimulus_id", stimulus_id)
    res = q.range(offset, offset + limit - 1).execute()
    return {"items": res.data or [], "total": getattr(res, "count", None), "limit": limit, "offset": offset}


@router.post("/pyq-question-stimuli")
def create_pyq_question_stimulus(
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Link a question to a stimulus. Lands at reviewer_status='pending'
    (DB default). Migration 223's trigger enforces both sides share a paper
    (and section, when both set) → surfaced as 422 on violation."""
    supabase = get_supabase_admin()
    row = {k: v for k, v in body.payload.items() if k in _LINK_FIELDS}
    if not row.get("question_id") or not row.get("stimulus_id"):
        raise HTTPException(status_code=422, detail="question_id and stimulus_id are required")
    try:
        inserted = supabase.table("pyq_question_stimuli").insert(row).execute().data or []
    except Exception as exc:  # noqa: BLE001
        mapped = _constraint_violation_http_error(exc)
        if mapped is not None:
            raise mapped from exc
        msg = str(exc)
        if "exam_phase" in msg or "section" in msg or "paper" in msg:
            raise HTTPException(status_code=422, detail=msg) from exc
        raise
    new = inserted[0] if inserted else row
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.pyq_question_stimulus.create",
        entity_type="pyq_question_stimulus", entity_id=new.get("id"),
        new_value={"reason": body.reason, "row": new},
    )
    return {"ok": True, "audit_id": audit_id, "row": new}


@router.patch("/pyq-question-stimuli/{link_id}")
def update_pyq_question_stimulus(
    link_id: str,
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Curate a link's display_order only. Repointing (question_id/
    stimulus_id) and reviewer_status are NOT allowed here — a repoint would
    reset the link's own review state via the DB trigger and belongs to a
    delete+create, and lifecycle moves belong to the review router."""
    supabase = get_supabase_admin()
    existing = _safe_select(supabase, "pyq_question_stimuli", id=link_id)
    if not existing:
        raise HTTPException(status_code=404, detail="pyq_question_stimulus not found")
    patch = {k: v for k, v in body.payload.items() if k == "display_order"}
    if not patch:
        raise HTTPException(status_code=422, detail="No allowed fields in payload")
    try:
        updated = supabase.table("pyq_question_stimuli").update(patch).eq("id", link_id).execute().data or []
    except Exception as exc:  # noqa: BLE001
        mapped = _constraint_violation_http_error(exc)
        if mapped is not None:
            raise mapped from exc
        raise
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.pyq_question_stimulus.update",
        entity_type="pyq_question_stimulus", entity_id=link_id,
        new_value={"reason": body.reason, "patch": patch, "previous": existing},
    )
    return {"ok": True, "audit_id": audit_id, "row": updated[0] if updated else existing | patch}


@router.delete("/pyq-question-stimuli/{link_id}")
def delete_pyq_question_stimulus(
    link_id: str,
    reason: str = Query(..., min_length=8, max_length=500),
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Delete a question↔stimulus link.

    Content-integrity guard (fix #3): a link may NOT be deleted while the
    question it provides context to is terminally 'verified' — dropping the
    passage/table association a verified question was reviewed against would
    orphan that reviewed evidence. Move the question to needs_correction/
    rejected first. Deletion is allowed when the question is
    pending/needs_correction/rejected."""
    supabase = get_supabase_admin()
    existing = _safe_select(supabase, "pyq_question_stimuli", id=link_id)
    if not existing:
        raise HTTPException(status_code=404, detail="pyq_question_stimulus not found")

    question_id = existing.get("question_id")
    question = _safe_select(supabase, "pyq_questions", id=question_id) if question_id else None
    if question and question.get("reviewer_status") == "verified":
        raise HTTPException(
            status_code=409,
            detail=(
                "cannot delete a link whose question is verified; move the "
                "question to needs_correction/rejected first"
            ),
        )

    supabase.table("pyq_question_stimuli").delete().eq("id", link_id).execute()
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.pyq_question_stimulus.delete",
        entity_type="pyq_question_stimulus", entity_id=link_id,
        new_value={"reason": reason, "previous": existing, "question_id": question_id},
    )
    return {"ok": True, "audit_id": audit_id, "deleted": existing}


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
    "cutoff_by_category", "difficulty_assessment", "breakdown_complete",
    "competition_pressure_score",
    "source_basis", "confidence_score",
    "reviewer_notes", "metadata",
    # applicant_count/cutoff_trend/difficulty_trend/selection_ratio/
    # evidence_count are DEPRECATED — intentionally excluded from the write
    # allowlist. applicant_count is the semantically-overloaded legacy volume
    # column (resolutions §1.2 PR-2 atomic switch / OD-6): the applied-vs-
    # appeared distinction now lives in exam_candidate_counts, so NO new
    # ambiguous applicant_count values may be written. The DB column is kept
    # (immutable-migration / deprecate-in-place), just never written here.
    # evidence_count is derived from exam_competition_metric_evidence, never
    # caller-supplied. metric_kind/version_no/supersedes_id/superseded_at/
    # is_current_published are server-controlled (lifecycle RPC only).
}
_COMPETITION_SOURCE_BASIS = (
    "manual", "official", "reviewed_analysis", "derived", "model_generated"
)
_RESERVATION_CATEGORY_CODES = {"general", "ews", "obc", "sc", "st"}


def _validate_competition_payload(row: dict[str, Any]) -> None:
    if row.get("source_basis") and row["source_basis"] not in _COMPETITION_SOURCE_BASIS:
        raise HTTPException(
            status_code=422,
            detail=f"source_basis must be one of {_COMPETITION_SOURCE_BASIS}",
        )
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
    # App-layer fast-path mirror of the DB validation trigger (migration 216
    # `_ecm_validate_jsonb`) — the DB trigger is the source of truth; this
    # gives a fast 422 instead of a raw DB error for the common cases.
    cutoff = row.get("cutoff_by_category")
    if cutoff:
        if not isinstance(cutoff, dict):
            raise HTTPException(status_code=422, detail="cutoff_by_category must be an object")
        for cat, val in cutoff.items():
            if cat not in _RESERVATION_CATEGORY_CODES:
                raise HTTPException(status_code=422, detail=f"cutoff_by_category: unknown category {cat!r}")
            if not isinstance(val, dict) or "marks" not in val:
                raise HTTPException(
                    status_code=422,
                    detail=f"cutoff_by_category[{cat}] must be an object {{marks, max_marks?}}, not a bare value",
                )
            if "stage" in val:
                raise HTTPException(status_code=422, detail=f"cutoff_by_category[{cat}]: 'stage' is not permitted")
    vacancy = row.get("vacancy_by_category")
    if vacancy:
        if not isinstance(vacancy, dict):
            raise HTTPException(status_code=422, detail="vacancy_by_category must be an object")
        for cat, val in vacancy.items():
            if cat not in _RESERVATION_CATEGORY_CODES:
                raise HTTPException(status_code=422, detail=f"vacancy_by_category: unknown category {cat!r}")
            if not isinstance(val, int) or isinstance(val, bool) or val < 0:
                raise HTTPException(status_code=422, detail=f"vacancy_by_category[{cat}] must be a non-negative integer")
    difficulty = row.get("difficulty_assessment")
    if difficulty:
        if not isinstance(difficulty, dict) or difficulty.get("level") not in ("harder", "stable", "easier"):
            raise HTTPException(status_code=422, detail="difficulty_assessment.level must be one of harder|stable|easier")
        basis = difficulty.get("basis") or ""
        if not (8 <= len(basis) <= 500):
            raise HTTPException(status_code=422, detail="difficulty_assessment.basis must be 8-500 characters")


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
    if not row.get("exam_cycle_id"):
        raise HTTPException(status_code=422, detail="exam_cycle_id is required (OD-11: every new-model competition row is cycle-anchored)")
    if not _safe_select(supabase, "exams", id=row["exam_id"]):
        raise HTTPException(status_code=422, detail="exam_id does not resolve")
    _validate_competition_payload(row)

    # metric_kind + field-ownership (OD-11): derived from exam_phase_id, not
    # client-supplied. cycle_summary owns vacancy/pressure; phase_cutoff owns
    # cutoff/difficulty. Mixing either way is a 422, not a silent drop.
    is_phase_scoped = bool(row.get("exam_phase_id"))
    row["metric_kind"] = "phase_cutoff" if is_phase_scoped else "cycle_summary"
    if is_phase_scoped:
        if any(row.get(f) is not None for f in ("vacancy_total", "applicant_count", "competition_pressure_score")) or row.get("vacancy_by_category"):
            raise HTTPException(status_code=422, detail="A phase-scoped (exam_phase_id set) row is phase_cutoff and cannot carry vacancy/pressure fields")
    else:
        if row.get("cutoff_by_category") or row.get("difficulty_assessment"):
            raise HTTPException(status_code=422, detail="A cycle-level (no exam_phase_id) row is cycle_summary and cannot carry cutoff/difficulty fields")
    row["reviewer_status"] = "draft"
    row["version_no"] = 1
    try:
        inserted = supabase.table("exam_competition_metrics").insert(row).execute().data or []
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        if "duplicate key" in msg.lower() or "ecm_working" in msg.lower():
            raise HTTPException(
                status_code=409,
                detail="A working (draft/pending_review) revision already exists for this scope — edit it instead of creating a new one",
            ) from exc
        raise HTTPException(status_code=422, detail=f"Could not create competition metric: {msg}") from exc
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
    not movable here; the review-side router owns that lifecycle.

    Scope fields (``exam_id``/``exam_cycle_id``/``exam_phase_id``) are
    immutable post-create: changing them without re-deriving ``metric_kind``
    would let a phase_cutoff row silently become an orphaned/incorrect
    cycle_summary row (or vice versa). Correcting scope means creating a new
    row for the right scope, not moving an existing row across scopes.
    """
    supabase = get_supabase_admin()
    existing = _safe_select(supabase, "exam_competition_metrics", id=metric_id)
    if not existing:
        raise HTTPException(status_code=404, detail="exam_competition_metric not found")
    patch = {
        k: v for k, v in body.payload.items()
        if k in _COMPETITION_FIELDS and k not in ("exam_id", "exam_cycle_id", "exam_phase_id")
    }
    if not patch:
        raise HTTPException(status_code=422, detail="No allowed fields in payload")
    _validate_competition_payload(patch)

    # Field-ownership (OD-11), same rule create enforces. metric_kind is fixed
    # at create (scope fields are immutable here), so validate the MERGED row
    # (existing values overlaid with this patch) against the existing kind —
    # a phase_cutoff row must not gain vacancy/pressure fields, a cycle_summary
    # row must not gain cutoff/difficulty fields. Without this, such a patch is
    # caught only by the DB `ecm_kind_field_ownership` CHECK and surfaces as an
    # unhandled 500 instead of a clean 422. metric_kind IS NULL (legacy-triaged)
    # rows are exempt, mirroring the CHECK.
    def _merged(field: str) -> Any:
        return patch[field] if field in patch else existing.get(field)

    metric_kind = existing.get("metric_kind")
    if metric_kind == "phase_cutoff":
        if any(_merged(f) is not None for f in ("vacancy_total", "applicant_count", "competition_pressure_score")) or _merged("vacancy_by_category"):
            raise HTTPException(status_code=422, detail="A phase_cutoff row cannot carry vacancy/pressure fields (field-ownership, OD-11)")
    elif metric_kind == "cycle_summary":
        if _merged("cutoff_by_category") or _merged("difficulty_assessment"):
            raise HTTPException(status_code=422, detail="A cycle_summary row cannot carry cutoff/difficulty fields (field-ownership, OD-11)")

    patch["updated_at"] = _now_iso()
    try:
        updated = supabase.table("exam_competition_metrics").update(patch).eq("id", metric_id).execute().data or []
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        low = msg.lower()
        if "published_row_immutable" in low:
            raise HTTPException(
                status_code=409,
                detail="This row is published (reviewed/locked) and its content is frozen — reopen it for edit (clones a new draft revision) instead of patching it",
            ) from exc
        if "ecm_kind_field_ownership" in low:
            raise HTTPException(
                status_code=422,
                detail="Patch violates metric_kind field-ownership (cycle_summary owns vacancy/pressure; phase_cutoff owns cutoff/difficulty)",
            ) from exc
        raise HTTPException(status_code=422, detail=f"Could not update competition metric: {msg}") from exc
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.competition_metric.update",
        entity_type="exam_competition_metric", entity_id=metric_id,
        new_value={"reason": body.reason, "patch": patch, "previous": existing},
    )
    return {"ok": True, "audit_id": audit_id, "row": updated[0] if updated else existing | patch}


# ════════════════════════════════════════════════════════════════════════
#  Applied-vs-Appeared candidate counts (migration 219, J3 PR 2). Created
#  at reviewer_status='draft'; moves through review lifecycle via the
#  review-side router (admin_exam_intelligence.py). CMS-side create + curate.
# ════════════════════════════════════════════════════════════════════════

_CANDIDATE_COUNT_FIELDS = {
    "exam_id", "exam_cycle_id", "exam_phase_id",
    "scope_kind", "count_type", "reservation_category_id", "count_value",
    "source_basis", "confidence_score", "reviewer_notes", "metadata",
    # version_no/supersedes_id/superseded_at/is_current_published are
    # server-controlled (lifecycle RPC only) — never client-writable.
}
_CANDIDATE_COUNT_SOURCE_BASIS = (
    "manual", "official", "reviewed_analysis", "derived", "model_generated"
)


def _validate_candidate_count_payload(row: dict[str, Any]) -> None:
    if row.get("source_basis") and row["source_basis"] not in _CANDIDATE_COUNT_SOURCE_BASIS:
        raise HTTPException(
            status_code=422,
            detail=f"source_basis must be one of {_CANDIDATE_COUNT_SOURCE_BASIS}",
        )
    if row.get("confidence_score") is not None:
        try:
            n = float(row["confidence_score"])
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail="confidence_score must be numeric")
        if not (0 <= n <= 1):
            raise HTTPException(status_code=422, detail="confidence_score must be in [0, 1]")
    if "count_value" in row:
        try:
            n = int(row["count_value"])
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail="count_value must be a non-negative integer")
        if n < 0:
            raise HTTPException(status_code=422, detail="count_value must be a non-negative integer")
    if row.get("scope_kind") and row["scope_kind"] not in ("cycle", "phase"):
        raise HTTPException(status_code=422, detail="scope_kind must be one of ('cycle', 'phase')")
    if row.get("count_type") and row["count_type"] not in ("applied", "appeared"):
        raise HTTPException(status_code=422, detail="count_type must be one of ('applied', 'appeared')")


def _validate_candidate_count_scope(supabase, row: dict[str, Any]) -> None:
    """App-layer fast-path mirror of the DB scope-integrity trigger and the
    OD-3 count_type/scope_kind shape CHECK (migration 219) — a phase must
    belong to the same exam AND cycle. The DB is the source of truth; this
    gives a fast 422 instead of a raw DB error for the common cases."""
    count_type = row.get("count_type")
    scope_kind = row.get("scope_kind")
    phase_id = row.get("exam_phase_id")

    if count_type == "applied" and (scope_kind != "cycle" or phase_id):
        raise HTTPException(
            status_code=422,
            detail="applied counts must be scope_kind='cycle' with no exam_phase_id (OD-3)",
        )
    if count_type == "appeared":
        if scope_kind == "phase" and not phase_id:
            raise HTTPException(status_code=422, detail="A phase-scoped appeared count requires exam_phase_id")
        if scope_kind == "cycle" and phase_id:
            raise HTTPException(status_code=422, detail="A cycle-scoped appeared count must not carry exam_phase_id")
    if scope_kind == "cycle" and phase_id:
        raise HTTPException(status_code=422, detail="scope_kind='cycle' rows must not carry exam_phase_id")
    if scope_kind == "phase" and not phase_id:
        raise HTTPException(status_code=422, detail="scope_kind='phase' rows require exam_phase_id")

    if phase_id:
        phase = _safe_select(supabase, "exam_phases", id=phase_id)
        if not phase:
            raise HTTPException(status_code=422, detail="exam_phase_id does not resolve")
        if phase.get("exam_id") != row.get("exam_id"):
            raise HTTPException(status_code=422, detail="exam_phase_id belongs to a different exam")
        # OD-3: the phase must belong to the SAME exam AND the SAME cycle.
        # A NULL exam_cycle_id (template / unbound phase) does NOT match any
        # cycle — it is rejected, not treated as a wildcard (checkpost P1-3).
        phase_cycle = phase.get("exam_cycle_id")
        if phase_cycle is None:
            raise HTTPException(
                status_code=422,
                detail="exam_phase_id is a template/unbound phase (exam_cycle_id IS NULL); a phase-scoped count requires a phase bound to the same cycle (OD-3)",
            )
        if phase_cycle != row.get("exam_cycle_id"):
            raise HTTPException(status_code=422, detail="exam_phase_id belongs to a different exam_cycle_id")


@router.post("/exam-candidate-counts")
def create_candidate_count(
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_MANAGE)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Create an applied-vs-appeared candidate-count row (J3 PR 2).

    Lands at ``reviewer_status='draft'``. Reviewers move it through
    pending_review -> reviewed -> locked via the review-side router; only
    reviewed/locked rows feed the ratio denominator (resolutions §1.2 PR-2
    half) and are surfaced to aspirants.
    """
    supabase = get_supabase_admin()
    row = {k: v for k, v in body.payload.items() if k in _CANDIDATE_COUNT_FIELDS}
    if not row.get("exam_id"):
        raise HTTPException(status_code=422, detail="exam_id is required")
    if not row.get("exam_cycle_id"):
        raise HTTPException(status_code=422, detail="exam_cycle_id is required")
    if not row.get("scope_kind"):
        raise HTTPException(status_code=422, detail="scope_kind is required")
    if not row.get("count_type"):
        raise HTTPException(status_code=422, detail="count_type is required")
    if row.get("count_value") is None:
        raise HTTPException(status_code=422, detail="count_value is required")
    if not _safe_select(supabase, "exams", id=row["exam_id"]):
        raise HTTPException(status_code=422, detail="exam_id does not resolve")
    if not _safe_select(supabase, "exam_cycles", id=row["exam_cycle_id"]):
        raise HTTPException(status_code=422, detail="exam_cycle_id does not resolve")
    _validate_candidate_count_payload(row)
    _validate_candidate_count_scope(supabase, row)

    row["reviewer_status"] = "draft"
    row["version_no"] = 1
    try:
        inserted = supabase.table("exam_candidate_counts").insert(row).execute().data or []
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        if "duplicate key" in msg.lower() or "ecc_working" in msg.lower():
            raise HTTPException(
                status_code=409,
                detail="A working (draft/pending_review) revision already exists for this scope — edit it instead of creating a new one",
            ) from exc
        raise HTTPException(status_code=422, detail=f"Could not create candidate count: {msg}") from exc
    new = inserted[0] if inserted else row
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.candidate_count.create",
        entity_type="exam_candidate_count", entity_id=new.get("id"),
        new_value={"reason": body.reason, "row": new},
    )
    return {"ok": True, "audit_id": audit_id, "row": new}


@router.patch("/exam-candidate-counts/{count_id}")
def update_candidate_count(
    count_id: str,
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_MANAGE)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Curate an existing candidate-count row. ``reviewer_status`` is not
    movable here; the review-side router owns that lifecycle. Scope fields
    are immutable post-create for the same reason as competition metrics —
    correcting scope means creating a new row for the right scope."""
    supabase = get_supabase_admin()
    existing = _safe_select(supabase, "exam_candidate_counts", id=count_id)
    if not existing:
        raise HTTPException(status_code=404, detail="exam_candidate_count not found")
    # reservation_category_id is IMMUTABLE scope (checkpost P1-4): a reopened
    # draft must not repoint its category, which would let it supersede a
    # parent in a different category scope. Correcting the category means a
    # fresh root row, not a patch.
    patch = {
        k: v for k, v in body.payload.items()
        if k in _CANDIDATE_COUNT_FIELDS
        and k not in (
            "exam_id", "exam_cycle_id", "exam_phase_id",
            "scope_kind", "count_type", "reservation_category_id",
        )
    }
    if not patch:
        raise HTTPException(status_code=422, detail="No allowed fields in payload")
    _validate_candidate_count_payload(patch)

    patch["updated_at"] = _now_iso()
    try:
        updated = supabase.table("exam_candidate_counts").update(patch).eq("id", count_id).execute().data or []
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        low = msg.lower()
        if "published_row_immutable" in low:
            raise HTTPException(
                status_code=409,
                detail="This row is published (reviewed/locked) and its content is frozen — reopen it for edit (clones a new draft revision) instead of patching it",
            ) from exc
        raise HTTPException(status_code=422, detail=f"Could not update candidate count: {msg}") from exc
    audit_id = _audit(
        supabase, admin, "exam_intel.cms.candidate_count.update",
        entity_type="exam_candidate_count", entity_id=count_id,
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


def _subject_ids_for_exam_family(supabase, exam_family_id: str) -> list[str]:
    """M4: subjects have no direct exam_family_id column (see J2-A gate,
    Section 0.5). Resolve the same way exam-scoped topic resolution is
    LOCKED to resolve for a single exam (coverage path), generalised to
    every exam in the family: exams(exam_family_id) -> exam_topic_coverage
    (exam_id) -> topics -> distinct subject_id.
    """
    exam_rows = (
        supabase.table("exams").select("id").eq("exam_family_id", exam_family_id).execute().data or []
    )
    exam_ids = [r["id"] for r in exam_rows if r.get("id")]
    if not exam_ids:
        return []
    coverage_rows = (
        supabase.table("exam_topic_coverage").select("topic_id").in_("exam_id", exam_ids).execute().data or []
    )
    topic_ids = sorted({r["topic_id"] for r in coverage_rows if r.get("topic_id")})
    if not topic_ids:
        return []
    topic_rows = (
        supabase.table("topics").select("subject_id").in_("id", topic_ids).execute().data or []
    )
    return sorted({r["subject_id"] for r in topic_rows if r.get("subject_id")})


@router.get("/subjects")
def list_subjects(
    is_active: bool | None = Query(default=None),
    q: str | None = Query(default=None),
    exam_family_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    subject_ids: list[str] | None = None
    if exam_family_id:
        subject_ids = _subject_ids_for_exam_family(supabase, exam_family_id)
        if not subject_ids:
            # M4 empty-scope contract (mirrors OD-5 for exam-scoped topics):
            # no fallback to the global subject list — an empty, well-formed
            # result communicates "no subjects mapped for this family yet".
            return {"items": [], "total": 0, "limit": limit, "offset": offset}
    query = supabase.table("subjects").select(
        "id, slug, name, subject_group, default_difficulty_level, description, is_active, metadata, created_at, updated_at",
        count="exact",
    ).order("name", desc=False)
    if is_active is not None:
        query = query.eq("is_active", is_active)
    if q:
        query = query.ilike("name", f"%{q.strip()}%")
    if subject_ids is not None:
        query = query.in_("id", subject_ids)
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
    # Advanced Repair is NOT a bypass around graph acyclicity (J2-A′ gate
    # blocker 1): even the cms writer goes through the single cycle-safe RPC
    # (global advisory lock + recursive transitive-cycle check). New edges land
    # as 'draft' — cms retains its exceptional-cleanup DELETE authority below,
    # but cannot silently create a transitive cycle or a live edge.
    try:
        res = supabase.rpc(
            "cms_write_topic_prerequisite",
            {
                "p_id": None,
                "p_topic_id": topic_id,
                "p_prerequisite_topic_id": prereq_id,
                "p_relation_type": row.get("relation_type") or "requires",
                "p_strength": row.get("strength", 1.0),
                "p_source_basis": row.get("source_basis"),
                "p_created_by": admin.get("id"),
                # Preserve caller-supplied metadata (CMS _TOPIC_PREREQ_FIELDS
                # includes it); the RPC persists it instead of dropping it.
                "p_metadata": row.get("metadata"),
                "p_expected_status": None,
            },
        ).execute()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=409, detail=str(exc))
    data = getattr(res, "data", None)
    new = (data[0] if isinstance(data, list) and data else data) or row
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


# Allowed trust_status transitions for pyq_sources. Mirrors review_pyq_paper's
# matrix exactly (migration 185). Any transition not listed here → 422.
_PYQ_SOURCE_ALLOWED_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "pending":  ("verified", "rejected"),
    "verified": ("rejected",),
    "rejected": ("pending",),
}
_PYQ_SOURCE_ALL_TARGET_STATUSES = frozenset(
    s for targets in _PYQ_SOURCE_ALLOWED_TRANSITIONS.values() for s in targets
)


class PyqSourceReviewBody(BaseModel):
    status: str = Field(..., description="Target trust_status: 'verified', 'rejected', or 'pending'")
    reason: str = Field(..., min_length=8, max_length=500)


@router.post("/pyq-sources/{source_id}/review")
def review_pyq_source(
    source_id: str,
    body: PyqSourceReviewBody,
    admin: dict = Depends(require_permission(PERM_REVIEW)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Transition a PYQ source's trust_status (the deferred OD-2 follow-up).

    Mirrors ``review_pyq_paper``: a dedicated review action backed by a single
    atomic SECURITY DEFINER RPC (``cms_review_pyq_source``) that writes the audit
    row and the status UPDATE in one DB transaction.

    Allowed transitions::

        pending  → verified | rejected
        verified → rejected
        rejected → pending  (re-queue)

    Unlike papers, sources have no provenance gate.  The audit log is written
    inside the same transaction as the UPDATE; a concurrent trust_status change
    between the SELECT below and the RPC is detected via SELECT FOR UPDATE and
    rolled back (no false audit rows).
    """
    if body.status not in _PYQ_SOURCE_ALL_TARGET_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"status must be one of {sorted(_PYQ_SOURCE_ALL_TARGET_STATUSES)}",
        )
    supabase = get_supabase_admin()
    existing = _safe_select(supabase, "pyq_sources", id=source_id)
    if not existing:
        raise HTTPException(status_code=404, detail="pyq_source not found")

    from_status = existing.get("trust_status", "pending")
    allowed = _PYQ_SOURCE_ALLOWED_TRANSITIONS.get(from_status, ())
    if body.status not in allowed:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Transition '{from_status}' → '{body.status}' is not allowed. "
                f"Allowed targets from '{from_status}': {list(allowed)}"
            ),
        )

    # Single atomic RPC: audit INSERT + source UPDATE in one DB transaction.
    # If a concurrent writer changed trust_status between the SELECT above and
    # the RPC, the function detects it via SELECT FOR UPDATE + expected-status
    # guard and raises "concurrent_modification" → both writes are rolled back.
    try:
        result = supabase.rpc(
            "cms_review_pyq_source",
            {
                "p_source_id":       source_id,
                "p_expected_status": from_status,
                "p_target_status":   body.status,
                "p_reason":          body.reason,
                "p_actor_id":        admin.get("id"),
                "p_actor_email":     admin.get("email"),
            },
        ).execute()
    except Exception as exc:
        msg = str(exc)
        msg_lower = msg.lower()
        # concurrent_modification → 409
        if "concurrent_modification" in msg_lower:
            raise HTTPException(
                status_code=409,
                detail="Concurrent modification: source trust_status changed since read. Re-fetch and retry.",
            ) from exc
        # other RPC contract failures → 422
        if any(tok in msg_lower for tok in (
            "transition_not_allowed", "invalid_reason",
            "invalid_target_status", "not_allowed",
        )):
            raise HTTPException(status_code=422, detail=msg) from exc
        # source deleted between SELECT and RPC → 404
        if "not_found" in msg_lower:
            raise HTTPException(status_code=404, detail=msg) from exc
        logger.exception("cms_review_pyq_source RPC failed; no status change recorded")
        raise HTTPException(
            status_code=500,
            detail="Review transaction failed; no status change recorded.",
        ) from exc

    data = result.data
    return {"ok": True, "audit_id": data["audit_id"], "row": data["row"]}


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
        "enums": {"status": _PHASE_STATUSES, "phase_kind": _PHASE_KINDS},
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
        # EI-CLEAN-09: reject rows whose phase belongs to a different cycle.
        "row_validator": lambda sb, cleaned: _pyq_paper_scope_error(
            sb,
            exam_id=cleaned.get("exam_id"),
            exam_cycle_id=cleaned.get("exam_cycle_id"),
            exam_phase_id=cleaned.get("exam_phase_id"),
        ),
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
        # Optional per-entity semantic validator (e.g. EI-CLEAN-09 phase↔cycle).
        row_validator = cfg.get("row_validator")
        if row_validator:
            row_err = row_validator(supabase, cleaned)
            if row_err:
                results.append({"index": idx, "ok": False, "error": row_err})
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


# ════════════════════════════════════════════════════════════════════════
#  Bulk update / bulk retire — apply one patch to many selected rows
# ════════════════════════════════════════════════════════════════════════
#
# Mirrors the single-row PATCH/DELETE endpoints above but fans a single
# operator-supplied patch (or retire) out over a list of ids gathered from
# the CMS table's filter + row-select UI. Scoped to the same entities the
# UI already treats as editable/deactivatable (EDITABLE_ENTITIES /
# DEACTIVATABLE_ENTITIES on the frontend) — lifecycle-owned entities
# (pyq-papers, pyq-questions, ...) stay out of scope; those go through the
# review queue, not a bulk field-set.
#
# Columns that must NEVER be bulk-editable, per entity. This is the integrity
# boundary for /bulk-update — NOT the frontend field picker, which is only a UX
# affordance. bulk_update() is a generic direct-table UPDATE and does NOT run the
# entity-specific FK-existence / scope-consistency / hierarchy validators that the
# single-row create/PATCH paths do (e.g. phase↔cycle belongs-to-exam, topic
# parent is a level=topic in the same subject, pyq_source belongs to exam). So a
# reference/scope/hierarchy column set in one bulk call across many rows could
# land invalid combinations the single-row path would have rejected. Rather than
# duplicate every validator here, we keep bulk-edit to scalar/enum/flag columns
# and route all FK/scope/hierarchy reassignment through the single-row form where
# the validation lives. Also excludes identity/dedup columns:
#   - slug / cycle_name / phase_name / phase_slug — unique/compound keys; setting
#     one value across a batch fails past row 1 anyway.
#   - name — never a meaningful batch-wide set.
#   - pyq_sources.source_id — external dedup/provenance key (same rationale the
#     single-row edit form uses to hide it; UI hiding is not an integrity boundary).
#   - trust_status — pipeline-owned (matches the single-row exclusion).
_BULK_EDIT_PROTECTED: dict[str, set[str]] = {
    "exam-families": {"slug", "name"},
    # exam_family_id / conducting_organization_id are FKs with no existence check here.
    "exams": {"name", "slug", "exam_family_id", "conducting_organization_id"},
    "exam-cycles": {"exam_id", "cycle_name"},
    # exam_cycle_id is the scope FK validated (phase↔cycle↔exam) only on the single-row path.
    "exam-phases": {"exam_id", "phase_name", "phase_slug", "exam_cycle_id"},
    "subjects": {"slug", "name"},
    # subject_id / parent_topic_id are FKs; level ties into the "microtopic/concept
    # needs a level=topic parent in the same subject" rule enforced only single-row.
    "topics": {"slug", "name", "subject_id", "parent_topic_id", "level"},
    "pyq-sources": {"trust_status", "source_id", "exam_id"},
}

_MAX_BULK_IDS = 500

_BULK_EDIT_CONFIG: dict[str, dict[str, Any]] = {
    "exam-families": {"table": "exam_families", "allowed": _FAMILY_FIELDS - _BULK_EDIT_PROTECTED["exam-families"], "enums": {}},
    "exams": {
        "table": "exams",
        "allowed": _EXAM_FIELDS - _BULK_EDIT_PROTECTED["exams"],
        "enums": {"exam_type": _EXAM_TYPES, "management_mode": _EXAM_MGMT_MODES, "cadence": _EXAM_CADENCES},
    },
    "exam-cycles": {
        "table": "exam_cycles",
        "allowed": _CYCLE_FIELDS - _BULK_EDIT_PROTECTED["exam-cycles"],
        "enums": {"status": _CYCLE_STATUSES},
    },
    "exam-phases": {
        "table": "exam_phases",
        "allowed": _PHASE_FIELDS - _BULK_EDIT_PROTECTED["exam-phases"],
        "enums": {"status": _PHASE_STATUSES, "phase_kind": _PHASE_KINDS},
    },
    "subjects": {"table": "subjects", "allowed": _SUBJECT_FIELDS - _BULK_EDIT_PROTECTED["subjects"], "enums": {}},
    "topics": {"table": "topics", "allowed": _TOPIC_FIELDS - _BULK_EDIT_PROTECTED["topics"], "enums": {}},
    "pyq-sources": {
        "table": "pyq_sources",
        "allowed": _PYQ_SOURCE_FIELDS - _BULK_EDIT_PROTECTED["pyq-sources"],
        "enums": {"source_type": _PYQ_SOURCE_TYPES},
    },
}

# Only these two entities have a soft-delete (is_active=false) lifecycle.
_BULK_DEACTIVATABLE_TABLES: dict[str, str] = {
    "exam-families": "exam_families",
    "exams": "exams",
}


class BulkUpdateBody(BaseModel):
    reason: str = Field(..., min_length=8, max_length=500)
    entity: str = Field(..., min_length=4, max_length=50)
    ids: list[str] = Field(..., min_length=1, max_length=_MAX_BULK_IDS)
    patch: dict[str, Any] = Field(..., min_length=1)


@router.post("/bulk-update")
def bulk_update(
    body: BulkUpdateBody,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Apply one patch to many rows of the same entity, by id.

    Per-id result is returned (mirrors ``bulk_import``'s per-row shape) so a
    row that 404s or trips a constraint doesn't block the rest of the batch.
    One aggregate audit row is written for the whole call, same convention
    as ``bulk_import``.
    """
    cfg = _BULK_EDIT_CONFIG.get(body.entity)
    if not cfg:
        raise HTTPException(
            status_code=422,
            detail=f"Entity {body.entity!r} does not support bulk update; allowed: {sorted(_BULK_EDIT_CONFIG)}",
        )
    patch = {k: v for k, v in body.patch.items() if k in cfg["allowed"]}
    if not patch:
        raise HTTPException(
            status_code=422,
            detail=f"No allowed fields in patch for {body.entity!r}; allowed: {sorted(cfg['allowed'])}",
        )
    for col, choices in cfg["enums"].items():
        v = patch.get(col)
        if v is not None and v not in choices:
            raise HTTPException(status_code=422, detail=f"{col} must be one of {choices}")
    if body.entity == "exam-phases":
        _validate_phase_kind(patch)

    supabase = get_supabase_admin()
    patch_with_ts = {**patch, "updated_at": _now_iso()}
    results: list[dict[str, Any]] = []
    ok_count = 0
    for row_id in body.ids:
        try:
            updated = supabase.table(cfg["table"]).update(patch_with_ts).eq("id", row_id).execute().data or []
        except Exception as exc:  # noqa: BLE001
            results.append({"id": row_id, "ok": False, "error": str(exc)[:200]})
            continue
        if not updated:
            results.append({"id": row_id, "ok": False, "error": "not found"})
            continue
        results.append({"id": row_id, "ok": True})
        ok_count += 1
    if body.entity == "exams" and ok_count:
        invalidate_exam_lookup_cache()
    error_count = len(body.ids) - ok_count
    audit_id = _audit(
        supabase, admin, f"exam_intel.cms.{cfg['table']}.bulk_update",
        entity_type=cfg["table"], entity_id=None,
        new_value={"reason": body.reason, "ids": body.ids, "patch": patch, "ok_count": ok_count, "error_count": error_count},
    )
    return {
        "ok": error_count == 0,
        "audit_id": audit_id,
        "entity": body.entity,
        "total": len(body.ids),
        "ok_count": ok_count,
        "error_count": error_count,
        "results": results,
    }


class BulkDeactivateBody(BaseModel):
    reason: str = Field(..., min_length=8, max_length=500)
    entity: str = Field(..., min_length=4, max_length=50)
    ids: list[str] = Field(..., min_length=1, max_length=_MAX_BULK_IDS)


@router.post("/bulk-deactivate")
def bulk_deactivate(
    body: BulkDeactivateBody,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Soft-delete many rows at once (is_active=false). Same restriction as
    the single-row DELETE endpoints: only exam-families and exams have this
    lifecycle; child rows keep their FK."""
    table = _BULK_DEACTIVATABLE_TABLES.get(body.entity)
    if not table:
        raise HTTPException(
            status_code=422,
            detail=f"Entity {body.entity!r} does not support bulk retire; allowed: {sorted(_BULK_DEACTIVATABLE_TABLES)}",
        )
    supabase = get_supabase_admin()
    results: list[dict[str, Any]] = []
    ok_count = 0
    for row_id in body.ids:
        try:
            updated = (
                supabase.table(table)
                .update({"is_active": False, "updated_at": _now_iso()})
                .eq("id", row_id)
                .execute()
                .data
                or []
            )
        except Exception as exc:  # noqa: BLE001
            results.append({"id": row_id, "ok": False, "error": str(exc)[:200]})
            continue
        if not updated:
            results.append({"id": row_id, "ok": False, "error": "not found"})
            continue
        results.append({"id": row_id, "ok": True})
        ok_count += 1
    if body.entity == "exams" and ok_count:
        invalidate_exam_lookup_cache()
    error_count = len(body.ids) - ok_count
    audit_id = _audit(
        supabase, admin, f"exam_intel.cms.{table}.bulk_deactivate",
        entity_type=table, entity_id=None,
        new_value={"reason": body.reason, "ids": body.ids, "ok_count": ok_count, "error_count": error_count},
    )
    return {
        "ok": error_count == 0,
        "audit_id": audit_id,
        "entity": body.entity,
        "total": len(body.ids),
        "ok_count": ok_count,
        "error_count": error_count,
        "results": results,
    }


# ─── Source registry (picker list) ───────────────────────────────────────────


@router.get("/source-registry")
def list_source_registry(
    include_discovery: bool = Query(
        default=False,
        description="When false (default) only official, non-discovery sources are returned. "
                    "Set true to include aggregator / discovery-only sources.",
    ),
    source_type: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Source registry picker — returns official sources by default.

    The default filter (is_official_source=true AND discovery_only=false AND
    is_active=true) keeps the picker clean for exam-setup workflows. Pass
    include_discovery=true to surface aggregator / discovery-only rows (e.g. for
    advanced auditing). Note: include_discovery bypasses is_official_source and
    discovery_only but NEVER is_active — inactive sources are excluded from every
    response regardless of the toggle.
    """
    supabase = get_supabase_admin()
    query = supabase.table("source_registry").select(
        "id, source_name, official_url, source_type, is_official_source, "
        "discovery_only, can_publish_directly, is_active",
        count="exact",
    ).order("source_name")
    # is_active is filtered unconditionally — inactive sources never appear,
    # even when include_discovery=true.
    query = query.eq("is_active", True)
    if not include_discovery:
        query = query.eq("is_official_source", True).eq("discovery_only", False)
    if source_type:
        query = query.eq("source_type", source_type)
    res = query.range(offset, offset + limit - 1).execute()
    return {
        "items": res.data or [],
        "total": getattr(res, "count", None),
        "limit": limit,
        "offset": offset,
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
