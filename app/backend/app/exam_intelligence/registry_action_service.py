"""Shared service for operator-gated exam registry mutations.

Extracted from ``admin_exam_intel_cms`` so that the apply-registry-action
endpoint in ``admin_verification_reports`` can reuse the exact same
write + audit logic without making an internal HTTP call or duplicating
field-set / validation code.

Every function here:
  - Takes a supabase admin client, an actor dict (from ``require_admin``),
    and the operation-specific params.
  - Returns ``{"ok": True, "audit_id": ..., "row": ...}`` on success.
  - Raises ``HTTPException`` (same codes as the CMS handlers) so callers
    can let FastAPI handle the error response without translation.

These are the *only* four paths that move a value from a verification
report into the exam registry. Nothing calls the DB tables directly;
all mutations go through here so the trust invariant stays single-sourced.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

logger = logging.getLogger("career_copilot.exam_intelligence.registry_action_service")


# ── Allowed field sets (mirror _CYCLE_FIELDS / _PHASE_FIELDS in the CMS) ──
# Only date-like fields are exposed here; the full CMS allows broader edits.
# The apply-action surface intentionally limits to date-relevant mutations
# so the corrigendum flow can't accidentally overwrite unrelated fields.

_CYCLE_DATE_FIELDS = {
    "notification_date", "application_start", "application_end",
    "exam_start", "exam_end", "status",
}
_CYCLE_REVIEWED_DATE_FIELDS = _CYCLE_DATE_FIELDS - {"status"}
_CYCLE_ALL_FIELDS = {
    "exam_id", "year", "cycle_name", "status",
    "notification_date", "application_start", "application_end",
    "exam_start", "exam_end", "source_url", "metadata",
}
_CYCLE_STATUSES = ("expected", "open", "active", "closed", "completed", "cancelled")

_PHASE_DATE_FIELDS = {"phase_start", "phase_end", "status"}
_PHASE_ALL_FIELDS = {
    "exam_id", "exam_cycle_id", "phase_name", "phase_slug", "phase_order",
    "mode", "duration_mins", "total_questions", "total_marks",
    "negative_marking", "status", "metadata",
    "phase_start", "phase_end",
}
_PHASE_STATUSES = ("expected", "active", "completed", "cancelled")

_POLICY_FIELDS = {
    "exam_id", "exam_cycle_id", "update_type", "title", "summary",
    "source_url", "published_at", "source_type",
    "affects_plan", "affects_deadline", "affects_eligibility",
    "affects_documents", "affects_syllabus", "affects_vacancy",
    "metadata",
}
_POLICY_UPDATE_TYPES = (
    "date_change", "syllabus_change", "vacancy_change",
    "eligibility_change", "pattern_change", "corrigendum", "other",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _audit(
    supabase: Any,
    actor: dict[str, Any],
    action: str,
    *,
    entity_type: str,
    entity_id: str | None = None,
    old_value: Any = None,
    new_value: Any = None,
    notes: str = "registry_action_service",
) -> str | None:
    try:
        rows = (
            supabase.table("admin_audit_logs")
            .insert({
                "actor_id": actor.get("id"),
                "actor_email": actor.get("email"),
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "old_value": old_value,
                "new_value": new_value,
                "notes": notes,
            })
            .execute()
            .data
            or []
        )
        return rows[0].get("id") if rows else None
    except Exception:  # noqa: BLE001
        logger.exception("audit log insert failed (registry_action_service)")
        return None


def _safe_select(supabase: Any, table: str, **filters: Any) -> dict[str, Any] | None:
    try:
        q = supabase.table(table).select("*").limit(1)
        for k, v in filters.items():
            q = q.eq(k, v)
        return (q.execute().data or [None])[0]
    except Exception:  # noqa: BLE001
        return None


# ── Core write functions ────────────────────────────────────────────────


def apply_cycle_date_update(
    supabase: Any,
    actor: dict[str, Any],
    cycle_id: str,
    patch: dict[str, Any],
    *,
    reason: str,
) -> dict[str, Any]:
    """Update date fields on an exam_cycle row.

    Allowed fields: a subset of _CYCLE_ALL_FIELDS restricted to date
    and status columns so callers from the corrigendum flow can't
    accidentally clobber unrelated cycle metadata.
    """
    existing = _safe_select(supabase, "exam_cycles", id=cycle_id)
    if not existing:
        raise HTTPException(status_code=404, detail="exam_cycle not found")
    cleaned = {k: v for k, v in patch.items() if k in _CYCLE_DATE_FIELDS}
    if not cleaned:
        raise HTTPException(status_code=422, detail="No allowed cycle fields in patch")
    if cleaned.get("status") and cleaned["status"] not in _CYCLE_STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {_CYCLE_STATUSES}")
    # Corrigendum application is another cycle authoring path. Any reviewed date
    # change invalidates the earned review state just like the CMS PATCH path.
    if existing.get("reviewer_status") in {"reviewed", "verified"} and any(
        field in cleaned and cleaned[field] != existing.get(field)
        for field in _CYCLE_REVIEWED_DATE_FIELDS
    ):
        cleaned["reviewer_status"] = "draft"
        cleaned["reviewed_by"] = None
        cleaned["reviewed_at"] = None
    cleaned["updated_at"] = _now_iso()
    updated = supabase.table("exam_cycles").update(cleaned).eq("id", cycle_id).execute().data or []
    row = updated[0] if updated else existing | cleaned
    audit_id = _audit(
        supabase, actor, "registry_action.cycle_date_update",
        entity_type="exam_cycle", entity_id=cycle_id,
        old_value={"patch_keys": list(cleaned.keys()), "previous": existing},
        new_value={"reason": reason, "patch": cleaned},
    )
    return {"ok": True, "audit_id": audit_id, "row": row}


def apply_phase_date_update(
    supabase: Any,
    actor: dict[str, Any],
    phase_id: str,
    patch: dict[str, Any],
    *,
    reason: str,
) -> dict[str, Any]:
    """Update phase_start / phase_end (and optionally status) on an exam_phases row."""
    existing = _safe_select(supabase, "exam_phases", id=phase_id)
    if not existing:
        raise HTTPException(status_code=404, detail="exam_phase not found")
    cleaned = {k: v for k, v in patch.items() if k in _PHASE_DATE_FIELDS}
    if not cleaned:
        raise HTTPException(status_code=422, detail="No allowed phase fields in patch")
    if cleaned.get("status") and cleaned["status"] not in _PHASE_STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {_PHASE_STATUSES}")
    cleaned["updated_at"] = _now_iso()
    updated = supabase.table("exam_phases").update(cleaned).eq("id", phase_id).execute().data or []
    row = updated[0] if updated else existing | cleaned
    audit_id = _audit(
        supabase, actor, "registry_action.phase_date_update",
        entity_type="exam_phase", entity_id=phase_id,
        old_value={"patch_keys": list(cleaned.keys()), "previous": existing},
        new_value={"reason": reason, "patch": cleaned},
    )
    return {"ok": True, "audit_id": audit_id, "row": row}


def apply_policy_update_create(
    supabase: Any,
    actor: dict[str, Any],
    payload: dict[str, Any],
    *,
    reason: str,
) -> dict[str, Any]:
    """Create an exam_policy_updates row at reviewer_status='pending'.

    Same guardrails as the CMS create endpoint: non-official source
    cannot set any affects_* flag to true.
    """
    row = {k: v for k, v in payload.items() if k in _POLICY_FIELDS}
    if not row.get("exam_id") or not row.get("update_type") or not row.get("title"):
        raise HTTPException(status_code=422, detail="exam_id, update_type, title are required")
    if row["update_type"] not in _POLICY_UPDATE_TYPES:
        raise HTTPException(status_code=422, detail=f"update_type must be one of {_POLICY_UPDATE_TYPES}")
    if (row.get("source_type") or "official") != "official":
        for affect in (
            "affects_plan", "affects_deadline", "affects_eligibility",
            "affects_documents", "affects_syllabus", "affects_vacancy",
        ):
            if row.get(affect):
                raise HTTPException(
                    status_code=422,
                    detail=f"Non-official policy updates cannot set {affect}=true",
                )
    row["reviewer_status"] = "pending"
    inserted = supabase.table("exam_policy_updates").insert(row).execute().data or []
    new_row = inserted[0] if inserted else row
    audit_id = _audit(
        supabase, actor, "registry_action.policy_update_create",
        entity_type="exam_policy_update", entity_id=new_row.get("id"),
        new_value={"reason": reason, "row": new_row},
    )
    return {"ok": True, "audit_id": audit_id, "row": new_row}


def apply_policy_update_edit(
    supabase: Any,
    actor: dict[str, Any],
    policy_id: str,
    patch: dict[str, Any],
    *,
    reason: str,
) -> dict[str, Any]:
    """Edit an existing exam_policy_updates row.

    reviewer_status is not touched here — lifecycle moves via the
    review-side router, not the corrigendum apply path.
    """
    existing = _safe_select(supabase, "exam_policy_updates", id=policy_id)
    if not existing:
        raise HTTPException(status_code=404, detail="exam_policy_update not found")
    cleaned = {k: v for k, v in patch.items() if k in _POLICY_FIELDS}
    if not cleaned:
        raise HTTPException(status_code=422, detail="No allowed policy fields in patch")
    if cleaned.get("update_type") and cleaned["update_type"] not in _POLICY_UPDATE_TYPES:
        raise HTTPException(status_code=422, detail=f"update_type must be one of {_POLICY_UPDATE_TYPES}")
    merged_source = cleaned.get("source_type") or existing.get("source_type") or "official"
    if merged_source != "official":
        for affect in (
            "affects_plan", "affects_deadline", "affects_eligibility",
            "affects_documents", "affects_syllabus", "affects_vacancy",
        ):
            merged = cleaned[affect] if affect in cleaned else existing.get(affect)
            if merged:
                raise HTTPException(
                    status_code=422,
                    detail=f"Non-official policy updates cannot set {affect}=true",
                )
    updated = supabase.table("exam_policy_updates").update(cleaned).eq("id", policy_id).execute().data or []
    row = updated[0] if updated else existing | cleaned
    audit_id = _audit(
        supabase, actor, "registry_action.policy_update_edit",
        entity_type="exam_policy_update", entity_id=policy_id,
        old_value={"patch_keys": list(cleaned.keys()), "previous": existing},
        new_value={"reason": reason, "patch": cleaned},
    )
    return {"ok": True, "audit_id": audit_id, "row": row}
