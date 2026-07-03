"""Admin D05 document-evidence registration + trust-review API (D12 v1, PR-4).

The D05 evidence engine (migration 211 §3–4 + ``document_policy.py``, PR-2) reads
``exam_document_evidence`` / ``exam_document_evidence_roles`` to decide whether a selected
cycle's required phases are complete. Those governance tables are service-role-only by RLS
(migration 211 ACCESS MODEL): *all* mutation — including ``trust_status`` transitions — must
flow through FastAPI permission + audit paths. This router is that path.

It lets an operator:
  * register an already-uploaded ``document_assets`` row (from admin_exam_intel_documents) as
    exam-domain evidence with one or more evidence roles,
  * verify / reject the human trust review,
  * supersede a stale registration with a newer one,
  * add / remove roles on an existing registration,
  * read the resolved D05 requirement coverage for the selected cycle (what is still unmet).

Registration lands at ``trust_status='pending'`` — registering never auto-verifies, mirroring the
document-linking flow. Until a registration is verified (and every other D05 predicate passes),
``document_policy`` treats the requirement as unmet, so Step 9 stays fail-closed.

Scope/supersession invariants are enforced in the database by the migration-211 triggers
(``_d05_check_evidence_scope`` / ``_d05_check_role_scope``); this layer does friendly pre-checks
and maps trigger violations to 422 rather than 500.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.admin_exam_intel_cms import PERM_CMS, _audit, _flag_enabled, _safe_select
from app.core.auth import require_permission
from app.db.supabase_client import get_supabase_admin
from app.exam_intelligence.document_policy import evaluate_required_phases_complete

logger = logging.getLogger("career_copilot.api.admin_exam_intel_evidence")

router = APIRouter(
    prefix="/admin/exam-intelligence-cms/evidence",
    tags=["admin-exam-intelligence-cms-evidence"],
)

# Canonical evidence-kind vocabulary lives in ``exam_evidence_kinds`` (migration 211). We read it
# live so the API never drifts from the seeded vocabulary; this is only a fail-safe fallback for
# environments where the vocabulary read returns nothing.
_EVIDENCE_KINDS_FALLBACK = {
    "primary_cycle_document", "syllabus", "exam_pattern", "pyq_paper", "answer_key",
    "phase_rules", "corrigendum", "notification", "application_instructions", "phase_schedule",
}

_TRUST_STATUSES = ("pending", "verified", "rejected", "superseded")
_OPERATIONAL_CYCLE_STATUSES = ("expected", "open", "active")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _evidence_kinds(sb) -> set[str]:
    rows = sb.table("exam_evidence_kinds").select("kind").limit(200).execute().data or []
    kinds = {r.get("kind") for r in rows if r.get("kind")}
    return kinds or set(_EVIDENCE_KINDS_FALLBACK)


def _is_trigger_violation(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(
        marker in msg
        for marker in (
            "exam_document_evidence:", "evidence role:", "does not belong",
            "not in exam", "not in parent", "conflicts with", "superseded_by_id",
        )
    )


def _load_admin_asset(sb, document_asset_id: str) -> dict | None:
    row = _safe_select(sb, "document_assets", id=document_asset_id)
    if not row or row.get("scope") != "admin_exam_intelligence":
        return None
    return row


def _authoritative_source_ids(sb, source_ids: set[str]) -> set[str]:
    """source_registry rows that pass the D05 source-authority predicate."""
    out: set[str] = set()
    for sid in {s for s in source_ids if s}:
        row = _safe_select(sb, "source_registry", id=sid)
        if row and row.get("is_active") and row.get("is_official_source") and not row.get("discovery_only"):
            out.add(sid)
    return out


def _latest_extract_status(sb, document_asset_id: str | None) -> str | None:
    if not document_asset_id:
        return None
    jobs = (
        sb.table("document_processing_jobs")
        .select("id, status, created_at")
        .eq("document_id", document_asset_id)
        .eq("job_type", "text_extract")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
        .data
        or []
    )
    return jobs[0].get("status") if jobs else None


def _roles_for(sb, evidence_ids: list[str]) -> dict[str, list[dict]]:
    by_ev: dict[str, list[dict]] = {}
    for ev_id in evidence_ids:
        rows = (
            sb.table("exam_document_evidence_roles")
            .select("id, document_evidence_id, evidence_kind, exam_cycle_id, exam_phase_id")
            .eq("document_evidence_id", ev_id)
            .limit(200)
            .execute()
            .data
            or []
        )
        by_ev[ev_id] = rows
    return by_ev


def _shape_evidence(ev: dict, *, asset: dict | None, roles: list[dict],
                    authoritative: bool, extraction_status: str | None) -> dict:
    return {
        "id": ev.get("id"),
        "document_asset_id": ev.get("document_asset_id"),
        "exam_id": ev.get("exam_id"),
        "exam_cycle_id": ev.get("exam_cycle_id"),
        "exam_phase_id": ev.get("exam_phase_id"),
        "source_registry_id": ev.get("source_registry_id"),
        "source_authoritative": authoritative,
        "trust_status": ev.get("trust_status"),
        "superseded_by_id": ev.get("superseded_by_id"),
        "reviewed_by": ev.get("reviewed_by"),
        "reviewed_at": ev.get("reviewed_at"),
        "created_at": ev.get("created_at"),
        "updated_at": ev.get("updated_at"),
        "document": {
            "title": (asset or {}).get("title"),
            "original_filename": (asset or {}).get("original_filename"),
            "document_kind": (asset or {}).get("document_kind"),
            "status": (asset or {}).get("status"),
        } if asset is not None else None,
        "extraction_status": extraction_status,
        "roles": [
            {
                "id": r.get("id"),
                "evidence_kind": r.get("evidence_kind"),
                "exam_cycle_id": r.get("exam_cycle_id"),
                "exam_phase_id": r.get("exam_phase_id"),
            }
            for r in roles
        ],
    }


# ── Schemas ──────────────────────────────────────────────────────────────────


class RoleInput(BaseModel):
    evidence_kind: str = Field(min_length=1, max_length=60)
    exam_cycle_id: str | None = None
    exam_phase_id: str | None = None


class RegisterEvidenceRequest(BaseModel):
    document_asset_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    exam_cycle_id: str | None = None
    exam_phase_id: str | None = None
    source_registry_id: str | None = None
    roles: list[RoleInput] = Field(min_length=1)
    reason: str = Field(..., min_length=8, max_length=500)


class ReviewEvidenceRequest(BaseModel):
    decision: str = Field(..., pattern="^(verified|rejected)$")
    reason: str = Field(..., min_length=8, max_length=500)


class SupersedeEvidenceRequest(BaseModel):
    superseded_by_id: str = Field(min_length=1)
    reason: str = Field(..., min_length=8, max_length=500)


class AddRoleRequest(RoleInput):
    reason: str = Field(..., min_length=8, max_length=500)


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("")
def list_evidence(
    exam_id: str = Query(..., min_length=1),
    exam_cycle_id: str | None = Query(default=None),
    trust_status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Registered evidence for an exam, with roles, asset display, and source authority."""
    sb = get_supabase_admin()
    if trust_status and trust_status not in _TRUST_STATUSES:
        raise HTTPException(status_code=422, detail=f"trust_status must be one of {list(_TRUST_STATUSES)}")
    q = (
        sb.table("exam_document_evidence")
        .select("id, document_asset_id, exam_id, exam_cycle_id, exam_phase_id, source_registry_id, "
                "trust_status, superseded_by_id, reviewed_by, reviewed_at, created_at, updated_at")
        .eq("exam_id", exam_id)
        .order("created_at", desc=True)
    )
    if trust_status:
        q = q.eq("trust_status", trust_status)
    rows = q.limit(2000).execute().data or []
    if exam_cycle_id:
        rows = [r for r in rows if r.get("exam_cycle_id") == exam_cycle_id]
    total = len(rows)
    page = rows[offset:offset + limit]

    roles_by_ev = _roles_for(sb, [r["id"] for r in page if r.get("id")])
    src_ids = {r.get("source_registry_id") for r in page if r.get("source_registry_id")}
    authoritative = _authoritative_source_ids(sb, src_ids)

    items = []
    for ev in page:
        asset = _safe_select(sb, "document_assets", id=ev.get("document_asset_id")) if ev.get("document_asset_id") else None
        items.append(_shape_evidence(
            ev,
            asset=asset,
            roles=roles_by_ev.get(ev["id"], []),
            authoritative=ev.get("source_registry_id") in authoritative,
            extraction_status=_latest_extract_status(sb, ev.get("document_asset_id")),
        ))
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/sources")
def list_sources(
    q: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    _admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """source_registry rows for the evidence source picker, each with the D05 authority verdict."""
    sb = get_supabase_admin()
    rows = (
        sb.table("source_registry")
        .select("id, source_name, source_type, state, is_active, is_official_source, discovery_only")
        .order("source_name", desc=False)
        .limit(2000)
        .execute()
        .data
        or []
    )
    if q:
        needle = q.lower()
        rows = [r for r in rows if needle in (r.get("source_name") or "").lower()]
    items = [
        {
            "id": r.get("id"),
            "source_name": r.get("source_name"),
            "source_type": r.get("source_type"),
            "state": r.get("state"),
            "is_authoritative": bool(
                r.get("is_active") and r.get("is_official_source") and not r.get("discovery_only")
            ),
        }
        for r in rows[:limit]
    ]
    return {"items": items, "total": len(items)}


@router.get("/coverage")
def evidence_coverage(
    exam_id: str = Query(..., min_length=1),
    exam_cycle_id: str = Query(..., min_length=1),
    _admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Resolved D05 required-phase completeness for the selected cycle (what is still unmet).

    Read-only view over ``document_policy.evaluate_required_phases_complete`` so operators can see
    which blocking requirements remain before Step 9 (Review & activate) can be satisfied. Mirrors
    the readiness Step-9 input resolution: management_mode + exam_type + cycle status + phases.
    """
    sb = get_supabase_admin()
    exam = _safe_select(sb, "exams", id=exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="exam not found")
    cycle = _safe_select(sb, "exam_cycles", id=exam_cycle_id)
    if not cycle or cycle.get("exam_id") != exam_id:
        raise HTTPException(status_code=404, detail="cycle not found for this exam")
    management_mode = exam.get("management_mode")
    if not management_mode:
        return {"applicable": False, "reason": "management_mode_unclassified",
                "management_mode": None, "complete": False, "unmet_requirements": []}
    if management_mode in ("index_only", "archive"):
        return {"applicable": False, "reason": "optional_for_management_mode",
                "management_mode": management_mode, "complete": False, "unmet_requirements": []}
    cycle_status = cycle.get("status")
    if (cycle_status or "") not in _OPERATIONAL_CYCLE_STATUSES:
        return {"applicable": False, "reason": "cycle_not_operational",
                "management_mode": management_mode, "cycle_status": cycle_status,
                "complete": False, "unmet_requirements": []}
    phases = (
        sb.table("exam_phases")
        .select("id, phase_kind, status, phase_name")
        .eq("exam_cycle_id", exam_cycle_id)
        .limit(500)
        .execute()
        .data
        or []
    )
    try:
        result = evaluate_required_phases_complete(
            sb, exam_id, exam_cycle_id, management_mode, phases,
            exam_type=exam.get("exam_type"), cycle_status=cycle_status,
        )
    except Exception as exc:  # noqa: BLE001 — fail-soft, never surface as 500
        logger.warning("evidence coverage evaluation failed: %s", exc)
        raise HTTPException(status_code=502, detail="coverage evaluation failed") from exc
    result.update({"applicable": True, "management_mode": management_mode, "cycle_status": cycle_status})
    return result


@router.post("")
def register_evidence(
    body: RegisterEvidenceRequest,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Register a document_asset as exam-domain evidence (trust_status='pending') with roles."""
    sb = get_supabase_admin()
    asset = _load_admin_asset(sb, body.document_asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="document asset not found")
    if asset.get("status") in ("archived",):
        raise HTTPException(status_code=422, detail="archived document cannot be registered as evidence")
    exam = _safe_select(sb, "exams", id=body.exam_id)
    if not exam:
        raise HTTPException(status_code=422, detail="exam_id does not resolve")
    asset_exam = (asset.get("metadata") or {}).get("exam_id")
    if asset_exam and asset_exam != body.exam_id:
        raise HTTPException(status_code=422, detail="document belongs to a different exam")

    kinds = _evidence_kinds(sb)
    bad = sorted({r.evidence_kind for r in body.roles if r.evidence_kind not in kinds})
    if bad:
        raise HTTPException(status_code=422, detail={"error": "unknown_evidence_kind", "kinds": bad})

    if body.source_registry_id and not _safe_select(sb, "source_registry", id=body.source_registry_id):
        raise HTTPException(status_code=422, detail="source_registry_id does not resolve")

    # Guard the (document_asset_id, exam_id) unique registration up front for a friendly 409.
    existing = (
        sb.table("exam_document_evidence")
        .select("id")
        .eq("document_asset_id", body.document_asset_id)
        .eq("exam_id", body.exam_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail={"error": "already_registered", "evidence_id": existing[0].get("id")},
        )

    evidence_row = {
        "document_asset_id": body.document_asset_id,
        "exam_id": body.exam_id,
        "exam_cycle_id": body.exam_cycle_id,
        "exam_phase_id": body.exam_phase_id,
        "source_registry_id": body.source_registry_id,
        "trust_status": "pending",
    }
    try:
        inserted = sb.table("exam_document_evidence").insert(evidence_row).execute().data or []
    except Exception as exc:  # noqa: BLE001
        if _is_trigger_violation(exc):
            raise HTTPException(status_code=422, detail={"error": "scope_violation", "message": str(exc)}) from exc
        logger.exception("evidence registration insert failed")
        raise HTTPException(status_code=500, detail="evidence registration failed") from exc
    ev = inserted[0] if inserted else evidence_row
    ev_id = ev.get("id")

    role_rows = []
    for r in body.roles:
        role_payload = {
            "document_evidence_id": ev_id,
            "evidence_kind": r.evidence_kind,
            "exam_cycle_id": r.exam_cycle_id,
            "exam_phase_id": r.exam_phase_id,
        }
        try:
            got = sb.table("exam_document_evidence_roles").insert(role_payload).execute().data or []
        except Exception as exc:  # noqa: BLE001
            # Roll back the parent registration so a partial evidence row is not stranded.
            sb.table("exam_document_evidence").delete().eq("id", ev_id).execute()
            if _is_trigger_violation(exc):
                raise HTTPException(status_code=422, detail={"error": "role_scope_violation", "message": str(exc)}) from exc
            logger.exception("evidence role insert failed")
            raise HTTPException(status_code=500, detail="evidence role registration failed") from exc
        role_rows.extend(got or [role_payload])

    _audit(
        sb, admin, "exam_intel.cms.evidence.register",
        entity_type="exam_document_evidence", entity_id=ev_id,
        new_value={
            "document_asset_id": body.document_asset_id,
            "exam_id": body.exam_id,
            "roles": [r.evidence_kind for r in body.roles],
            "reason": body.reason,
        },
    )
    return {"ok": True, "evidence": _shape_evidence(
        ev, asset=asset, roles=role_rows,
        authoritative=body.source_registry_id in _authoritative_source_ids(
            sb, {body.source_registry_id} if body.source_registry_id else set()),
        extraction_status=_latest_extract_status(sb, body.document_asset_id),
    )}


def _load_evidence(sb, evidence_id: str) -> dict | None:
    return _safe_select(sb, "exam_document_evidence", id=evidence_id)


@router.post("/{evidence_id}/review")
def review_evidence(
    evidence_id: str,
    body: ReviewEvidenceRequest,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Human trust-review transition: pending/rejected/verified → verified|rejected.

    A superseded registration is terminal and cannot be re-reviewed (supersession is a newer
    governing record, not a review verdict).
    """
    sb = get_supabase_admin()
    ev = _load_evidence(sb, evidence_id)
    if not ev:
        raise HTTPException(status_code=404, detail="evidence not found")
    if ev.get("trust_status") == "superseded":
        raise HTTPException(status_code=409, detail="superseded evidence cannot be re-reviewed")

    patch = {
        "trust_status": body.decision,
        "reviewed_by": admin.get("id"),
        "reviewed_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    updated = (
        sb.table("exam_document_evidence")
        .update(patch)
        .eq("id", evidence_id)
        .neq("trust_status", "superseded")
        .execute()
        .data
        or []
    )
    if not updated:
        raise HTTPException(status_code=409, detail="evidence changed concurrently; reload and retry")
    _audit(
        sb, admin, "exam_intel.cms.evidence.review",
        entity_type="exam_document_evidence", entity_id=evidence_id,
        new_value={"decision": body.decision, "reason": body.reason,
                   "prev_trust_status": ev.get("trust_status")},
    )
    return {"ok": True, "evidence_id": evidence_id, "trust_status": body.decision}


@router.post("/{evidence_id}/supersede")
def supersede_evidence(
    evidence_id: str,
    body: SupersedeEvidenceRequest,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Mark this registration superseded by a newer one (same exam, not itself)."""
    sb = get_supabase_admin()
    ev = _load_evidence(sb, evidence_id)
    if not ev:
        raise HTTPException(status_code=404, detail="evidence not found")
    if body.superseded_by_id == evidence_id:
        raise HTTPException(status_code=422, detail="evidence cannot supersede itself")
    target = _load_evidence(sb, body.superseded_by_id)
    if not target:
        raise HTTPException(status_code=422, detail="superseded_by_id does not resolve")
    if target.get("exam_id") != ev.get("exam_id"):
        raise HTTPException(status_code=422, detail="superseded_by_id belongs to a different exam")

    patch = {
        "trust_status": "superseded",
        "superseded_by_id": body.superseded_by_id,
        "updated_at": _now_iso(),
    }
    try:
        updated = (
            sb.table("exam_document_evidence")
            .update(patch)
            .eq("id", evidence_id)
            .execute()
            .data
            or []
        )
    except Exception as exc:  # noqa: BLE001
        if _is_trigger_violation(exc):
            raise HTTPException(status_code=422, detail={"error": "supersede_violation", "message": str(exc)}) from exc
        logger.exception("evidence supersede failed")
        raise HTTPException(status_code=500, detail="evidence supersede failed") from exc
    if not updated:
        raise HTTPException(status_code=409, detail="evidence changed concurrently; reload and retry")
    _audit(
        sb, admin, "exam_intel.cms.evidence.supersede",
        entity_type="exam_document_evidence", entity_id=evidence_id,
        new_value={"superseded_by_id": body.superseded_by_id, "reason": body.reason},
    )
    return {"ok": True, "evidence_id": evidence_id, "trust_status": "superseded",
            "superseded_by_id": body.superseded_by_id}


@router.post("/{evidence_id}/roles")
def add_role(
    evidence_id: str,
    body: AddRoleRequest,
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Add an evidence role to an existing registration (one source may satisfy many roles)."""
    sb = get_supabase_admin()
    ev = _load_evidence(sb, evidence_id)
    if not ev:
        raise HTTPException(status_code=404, detail="evidence not found")
    if body.evidence_kind not in _evidence_kinds(sb):
        raise HTTPException(status_code=422, detail={"error": "unknown_evidence_kind", "kinds": [body.evidence_kind]})
    role_payload = {
        "document_evidence_id": evidence_id,
        "evidence_kind": body.evidence_kind,
        "exam_cycle_id": body.exam_cycle_id,
        "exam_phase_id": body.exam_phase_id,
    }
    try:
        got = sb.table("exam_document_evidence_roles").insert(role_payload).execute().data or []
    except Exception as exc:  # noqa: BLE001
        if _is_trigger_violation(exc):
            raise HTTPException(status_code=422, detail={"error": "role_scope_violation", "message": str(exc)}) from exc
        msg = str(exc).lower()
        if "duplicate" in msg or "unique" in msg:
            raise HTTPException(status_code=409, detail="role already exists for this scope") from exc
        logger.exception("evidence add-role failed")
        raise HTTPException(status_code=500, detail="add role failed") from exc
    role = got[0] if got else role_payload
    _audit(
        sb, admin, "exam_intel.cms.evidence.add_role",
        entity_type="exam_document_evidence", entity_id=evidence_id,
        new_value={"evidence_kind": body.evidence_kind, "reason": body.reason},
    )
    return {"ok": True, "evidence_id": evidence_id, "role": role}


@router.delete("/{evidence_id}/roles/{role_id}")
def remove_role(
    evidence_id: str,
    role_id: str,
    reason: str = Query(..., min_length=8, max_length=500),
    admin: dict = Depends(require_permission(PERM_CMS)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Remove an evidence role. The last role may be removed; the registration itself remains."""
    sb = get_supabase_admin()
    role = _safe_select(sb, "exam_document_evidence_roles", id=role_id)
    if not role or role.get("document_evidence_id") != evidence_id:
        raise HTTPException(status_code=404, detail="role not found for this evidence")
    sb.table("exam_document_evidence_roles").delete().eq("id", role_id).execute()
    _audit(
        sb, admin, "exam_intel.cms.evidence.remove_role",
        entity_type="exam_document_evidence", entity_id=evidence_id,
        new_value={"role_id": role_id, "evidence_kind": role.get("evidence_kind"), "reason": reason},
    )
    return {"ok": True, "evidence_id": evidence_id, "removed_role_id": role_id}
