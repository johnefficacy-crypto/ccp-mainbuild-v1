"""Admin D05 document-evidence registration + trust-review API (D12 v1, PR-4).

The D05 evidence engine (migration 211 §3–4 + ``document_policy.py``, PR-2) reads
``exam_document_evidence`` / ``exam_document_evidence_roles`` to decide whether a selected
cycle's required phases are complete. Those governance tables are service-role-only by RLS
(migration 211 ACCESS MODEL): *all* mutation — including ``trust_status`` transitions — must
flow through FastAPI permission + audit paths. This router is that path.

Permission tiers follow the locked J2 §D separation (NOT the exceptional-repair CMS token):
  * reads (list / sources / coverage)        → ``exam_intelligence.manage`` OR ``.review``
  * register + role add/remove (operational) → ``exam_intelligence.manage``
  * verify / reject / supersede (trust)      → ``exam_intelligence.review``
  * ``super_admin`` bypasses all of the above.
``exam_intelligence.cms`` stays exclusive to Advanced Repair and is NOT accepted here.

Trust invariants enforced by this layer:
  * Registration proves upload COMPLETION independently of extraction — an ``uploaded``
    placeholder (pre ``complete-upload``, ``content_hash='pending:…'``) cannot be registered.
  * Evidence scope must be CONSISTENT with the source asset's stored upload scope: a
    cycle/phase-scoped asset cannot be re-registered under a different cycle/phase.
  * Changing roles on a VERIFIED registration atomically resets it to ``pending`` and clears the
    reviewer stamp, so a newly asserted role can never silently inherit an unrelated verification.
    Superseded/rejected registrations are terminal for role edits.

Registration lands at ``trust_status='pending'`` — registering never auto-verifies. Migration-211
triggers (``_d05_check_evidence_scope`` / ``_d05_check_role_scope``) remain the DB-level guard;
this layer does friendly pre-checks and maps trigger violations to 422.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.admin_exam_intel_cms import _audit, _flag_enabled, _safe_select
from app.core.auth import get_current_user, require_permission
from app.core.permissions import EXAM_INTELLIGENCE_MANAGE, EXAM_INTELLIGENCE_REVIEW
from app.db.supabase_client import get_supabase_admin
from app.exam_intelligence.document_policy import evaluate_required_phases_complete

logger = logging.getLogger("career_copilot.api.admin_exam_intel_evidence")

router = APIRouter(
    prefix="/admin/exam-intelligence-cms/evidence",
    tags=["admin-exam-intelligence-cms-evidence"],
)

PERM_MANAGE = EXAM_INTELLIGENCE_MANAGE   # operational edits: register + role add/remove
PERM_REVIEW = EXAM_INTELLIGENCE_REVIEW   # trust/lifecycle: verify / reject / supersede

# Canonical evidence-kind vocabulary lives in ``exam_evidence_kinds`` (migration 211). We read it
# live so the API never drifts from the seeded vocabulary; this is only a fail-safe fallback for
# environments where the vocabulary read returns nothing.
_EVIDENCE_KINDS_FALLBACK = {
    "primary_cycle_document", "syllabus", "exam_pattern", "pyq_paper", "answer_key",
    "phase_rules", "corrigendum", "notification", "application_instructions", "phase_schedule",
}

_TRUST_STATUSES = ("pending", "verified", "rejected", "superseded")
_OPERATIONAL_CYCLE_STATUSES = ("expected", "open", "active")
# document_assets that have NOT completed the upload handshake — a signed-URL placeholder whose
# bytes/hash are not yet confirmed. Registering these could satisfy a no-extraction requirement
# without a real file, so they are rejected.
_INCOMPLETE_UPLOAD_STATUSES = ("uploaded",)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def require_manage_or_review(user: dict = Depends(get_current_user)) -> dict:
    """Read gate: a manage OR review operator may load the evidence surface (super_admin bypass)."""
    if user.get("is_anonymous"):
        raise HTTPException(status_code=403, detail="Anonymous users cannot access this resource")
    if user.get("role") == "super_admin":
        return user
    perms = set(user.get("permissions") or [])
    if PERM_MANAGE in perms or PERM_REVIEW in perms:
        return user
    raise HTTPException(
        status_code=403,
        detail="Missing permission: exam_intelligence.manage or exam_intelligence.review",
    )


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


def _upload_incomplete(asset: dict) -> bool:
    """True when the asset has not completed the upload handshake (independent of extraction)."""
    if asset.get("status") in _INCOMPLETE_UPLOAD_STATUSES:
        return True
    ch = asset.get("content_hash")
    return not ch or str(ch).startswith("pending:")


def _asset_scope_conflict(meta: dict, *, cycle_id: str | None, phase_id: str | None) -> str | None:
    """D05 predicate 1: registration/role scope must not escape the asset's stored upload scope.

    A cycle-scoped asset cannot move to another cycle; a phase-scoped asset cannot move to another
    phase. An exam-level (unscoped) asset may be narrowed to any cycle/phase in the exam (the
    migration-211 triggers still validate the cycle/phase hierarchy). Returns an error code or None.
    """
    meta_cycle = meta.get("exam_cycle_id")
    meta_phase = meta.get("exam_phase_id")
    if meta_cycle and cycle_id and cycle_id != meta_cycle:
        return "asset_cycle_scope_conflict"
    if meta_phase and phase_id and phase_id != meta_phase:
        return "asset_phase_scope_conflict"
    return None


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
    """Batched (single-query) role load for a page of evidence rows."""
    by_ev: dict[str, list[dict]] = {ev_id: [] for ev_id in evidence_ids}
    if not evidence_ids:
        return by_ev
    rows = (
        sb.table("exam_document_evidence_roles")
        .select("id, document_evidence_id, evidence_kind, exam_cycle_id, exam_phase_id")
        .in_("document_evidence_id", evidence_ids)
        .limit(2000)
        .execute()
        .data
        or []
    )
    for r in rows:
        by_ev.setdefault(r.get("document_evidence_id"), []).append(r)
    return by_ev


def _assets_for(sb, asset_ids: list[str]) -> dict[str, dict]:
    """Batched (single-query) document_assets load for a page of evidence rows."""
    ids = [a for a in asset_ids if a]
    if not ids:
        return {}
    rows = (
        sb.table("document_assets")
        .select("id, title, original_filename, document_kind, status")
        .in_("id", ids)
        .limit(2000)
        .execute()
        .data
        or []
    )
    return {r["id"]: r for r in rows if r.get("id")}


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


# ── Endpoints: reads (manage OR review) ──────────────────────────────────────


@router.get("")
def list_evidence(
    exam_id: str = Query(..., min_length=1),
    exam_cycle_id: str | None = Query(default=None),
    trust_status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(require_manage_or_review),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Registered evidence for an exam, with roles, asset display, and source authority.

    ``exam_cycle_id`` / ``trust_status`` are applied server-side and pagination uses a ranged
    query with an exact count, so a cycle's rows can never be dropped by a fixed row cap.
    """
    sb = get_supabase_admin()
    if trust_status and trust_status not in _TRUST_STATUSES:
        raise HTTPException(status_code=422, detail=f"trust_status must be one of {list(_TRUST_STATUSES)}")
    q = (
        sb.table("exam_document_evidence")
        .select("id, document_asset_id, exam_id, exam_cycle_id, exam_phase_id, source_registry_id, "
                "trust_status, superseded_by_id, reviewed_by, reviewed_at, created_at, updated_at",
                count="exact")
        .eq("exam_id", exam_id)
    )
    if exam_cycle_id:
        q = q.eq("exam_cycle_id", exam_cycle_id)
    if trust_status:
        q = q.eq("trust_status", trust_status)
    resp = q.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    page = resp.data or []
    total = resp.count if getattr(resp, "count", None) is not None else len(page)

    ev_ids = [r["id"] for r in page if r.get("id")]
    roles_by_ev = _roles_for(sb, ev_ids)
    assets_by_id = _assets_for(sb, [r.get("document_asset_id") for r in page])
    authoritative = _authoritative_source_ids(sb, {r.get("source_registry_id") for r in page if r.get("source_registry_id")})

    items = [
        _shape_evidence(
            ev,
            asset=assets_by_id.get(ev.get("document_asset_id")),
            roles=roles_by_ev.get(ev["id"], []),
            authoritative=ev.get("source_registry_id") in authoritative,
            extraction_status=_latest_extract_status(sb, ev.get("document_asset_id")),
        )
        for ev in page
    ]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/sources")
def list_sources(
    q: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    _admin: dict = Depends(require_manage_or_review),
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
    _admin: dict = Depends(require_manage_or_review),
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


# ── Endpoints: registration + role edits (manage) ────────────────────────────


@router.post("")
def register_evidence(
    body: RegisterEvidenceRequest,
    admin: dict = Depends(require_permission(PERM_MANAGE)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Register a document_asset as exam-domain evidence (trust_status='pending') with roles."""
    sb = get_supabase_admin()
    asset = _load_admin_asset(sb, body.document_asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="document asset not found")
    if asset.get("status") == "archived":
        raise HTTPException(status_code=422, detail="archived document cannot be registered as evidence")
    if _upload_incomplete(asset):
        raise HTTPException(
            status_code=422,
            detail={"error": "upload_incomplete",
                    "message": "document upload has not completed; finish upload before registering as evidence"},
        )
    exam = _safe_select(sb, "exams", id=body.exam_id)
    if not exam:
        raise HTTPException(status_code=422, detail="exam_id does not resolve")
    meta = asset.get("metadata") or {}
    asset_exam = meta.get("exam_id")
    if asset_exam and asset_exam != body.exam_id:
        raise HTTPException(status_code=422, detail="document belongs to a different exam")

    # D05 predicate 1: registration + every role scope must not escape the asset's stored scope.
    conflict = _asset_scope_conflict(meta, cycle_id=body.exam_cycle_id, phase_id=body.exam_phase_id)
    if conflict:
        raise HTTPException(status_code=422, detail={"error": conflict, "scope": "registration"})
    for r in body.roles:
        rc = _asset_scope_conflict(meta, cycle_id=r.exam_cycle_id, phase_id=r.exam_phase_id)
        if rc:
            raise HTTPException(status_code=422, detail={"error": rc, "scope": "role", "evidence_kind": r.evidence_kind})

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


def _reset_verified_to_pending(sb, ev: dict, admin: dict, *, cause: str) -> None:
    """A role change on a VERIFIED registration invalidates the human review — reset atomically.

    Clears the reviewer stamp and returns to 'pending' so the newly-asserted (or removed) role set
    must be re-reviewed before it can satisfy any D05 requirement. No-op unless currently verified.
    """
    if ev.get("trust_status") != "verified":
        return
    sb.table("exam_document_evidence").update({
        "trust_status": "pending", "reviewed_by": None, "reviewed_at": None, "updated_at": _now_iso(),
    }).eq("id", ev["id"]).eq("trust_status", "verified").execute()
    _audit(
        sb, admin, "exam_intel.cms.evidence.trust_reset",
        entity_type="exam_document_evidence", entity_id=ev["id"],
        new_value={"from": "verified", "to": "pending", "cause": cause},
    )


@router.post("/{evidence_id}/roles")
def add_role(
    evidence_id: str,
    body: AddRoleRequest,
    admin: dict = Depends(require_permission(PERM_MANAGE)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Add an evidence role to an existing registration (one source may satisfy many roles).

    A role change on a verified registration resets trust to 'pending' (re-review required); a
    superseded/rejected registration is terminal for role edits.
    """
    sb = get_supabase_admin()
    ev = _load_evidence(sb, evidence_id)
    if not ev:
        raise HTTPException(status_code=404, detail="evidence not found")
    if ev.get("trust_status") in ("superseded", "rejected"):
        raise HTTPException(status_code=409,
                            detail=f"{ev.get('trust_status')} evidence is terminal; re-register to change roles")
    if body.evidence_kind not in _evidence_kinds(sb):
        raise HTTPException(status_code=422, detail={"error": "unknown_evidence_kind", "kinds": [body.evidence_kind]})
    conflict = _asset_scope_conflict(
        (_load_admin_asset(sb, ev.get("document_asset_id")) or {}).get("metadata") or {},
        cycle_id=body.exam_cycle_id, phase_id=body.exam_phase_id)
    if conflict:
        raise HTTPException(status_code=422, detail={"error": conflict, "scope": "role"})
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
    was_verified = ev.get("trust_status") == "verified"
    _reset_verified_to_pending(sb, ev, admin, cause="role_added")
    _audit(
        sb, admin, "exam_intel.cms.evidence.add_role",
        entity_type="exam_document_evidence", entity_id=evidence_id,
        new_value={"evidence_kind": body.evidence_kind, "reason": body.reason},
    )
    return {"ok": True, "evidence_id": evidence_id, "role": role, "trust_reset": was_verified}


@router.delete("/{evidence_id}/roles/{role_id}")
def remove_role(
    evidence_id: str,
    role_id: str,
    reason: str = Query(..., min_length=8, max_length=500),
    admin: dict = Depends(require_permission(PERM_MANAGE)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Remove an evidence role. Resets a verified registration to 'pending' (re-review required)."""
    sb = get_supabase_admin()
    ev = _load_evidence(sb, evidence_id)
    if not ev:
        raise HTTPException(status_code=404, detail="evidence not found")
    if ev.get("trust_status") in ("superseded", "rejected"):
        raise HTTPException(status_code=409,
                            detail=f"{ev.get('trust_status')} evidence is terminal; re-register to change roles")
    role = _safe_select(sb, "exam_document_evidence_roles", id=role_id)
    if not role or role.get("document_evidence_id") != evidence_id:
        raise HTTPException(status_code=404, detail="role not found for this evidence")
    sb.table("exam_document_evidence_roles").delete().eq("id", role_id).execute()
    was_verified = ev.get("trust_status") == "verified"
    _reset_verified_to_pending(sb, ev, admin, cause="role_removed")
    _audit(
        sb, admin, "exam_intel.cms.evidence.remove_role",
        entity_type="exam_document_evidence", entity_id=evidence_id,
        new_value={"role_id": role_id, "evidence_kind": role.get("evidence_kind"), "reason": reason},
    )
    return {"ok": True, "evidence_id": evidence_id, "removed_role_id": role_id,
            "trust_reset": was_verified}


# ── Endpoints: trust transitions (review) ────────────────────────────────────


@router.post("/{evidence_id}/review")
def review_evidence(
    evidence_id: str,
    body: ReviewEvidenceRequest,
    admin: dict = Depends(require_permission(PERM_REVIEW)),
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
    admin: dict = Depends(require_permission(PERM_REVIEW)),
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
