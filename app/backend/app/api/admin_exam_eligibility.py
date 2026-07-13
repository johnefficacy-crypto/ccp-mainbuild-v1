"""Admin CRUD for ``exam_eligibility_rules`` (PR-D2).

Endpoint group (all require ``exam_eligibility.manage`` permission):

  GET    /api/admin/exam-eligibility/exams
         List active exams with verified/draft/archived rule counts.

  GET    /api/admin/exam-eligibility/exams/{exam_id}/rules
         All rules (every status) for one exam.

  POST   /api/admin/exam-eligibility/exams/{exam_id}/rules
         Create a new rule. Body is shape-validated by Pydantic; the
         unique (exam_id, scope, rule_type) constraint surfaces 409.

  PUT    /api/admin/exam-eligibility/rules/{rule_id}
         Update value / source / reviewer_status. Moving status to
         ``verified`` stamps ``verified_by`` and ``verified_at``.

  DELETE /api/admin/exam-eligibility/rules/{rule_id}
         Soft-delete via ``reviewer_status = 'archived'`` (the row stays
         for audit). Pass ``?hard=true`` to actually delete the row.

The user-facing evaluator (``GET /api/exams/eligibility-summary``)
already filters to ``reviewer_status='verified'`` only, so a rule
moves in/out of the live summary purely by status changes here.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.auth import require_permission
from app.db.supabase_client import get_supabase_admin
from app.exam_eligibility.evaluator import invalidate_eligibility_rules_cache

logger = logging.getLogger("career_copilot.api.admin_exam_eligibility")


def _audit(
    sb,
    admin: dict,
    action: str,
    entity_type: str,
    entity_id: str,
    before_payload=None,
    after_payload=None,
    metadata=None,
) -> None:
    sb.table("admin_audit_logs").insert({
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "actor_id": admin.get("id"),
        "actor_email": admin.get("email"),
        "old_value": before_payload,
        "new_value": after_payload,
        "notes": str(metadata or ""),
    }).execute()

ADMIN_PERM = "exam_eligibility.manage"

router = APIRouter(prefix="/admin/exam-eligibility", tags=["admin-exam-eligibility"])


# ── Validation ───────────────────────────────────────────────────────────


_ALLOWED_SCOPES = {"all", "general", "obc", "sc", "st", "ews", "pwd", "ex_serviceman", "women"}
# Baseline rule_types mirror migration 248's CHECK. experience_min_years is
# cycle-specific (§4) and is NOT a baseline type. stream_id / value_json let a
# rule be stream-scoped and carry a machine-evaluable qualification_combination.
_ALLOWED_RULE_TYPES = {
    "age_min", "age_max", "education_min_level", "nationality", "gender", "attempts_max",
    "discipline", "min_percentage", "certification", "qualification_combination",
    "stream_availability",
}
# As of migration 253 the evaluator interprets every baseline rule_type
# (stream-aware evaluation activated), so the fail-closed verify guard is lifted.
_ALLOWED_REVIEWER_STATUS = {"draft", "verified", "archived"}
_NUMERIC_RULE_TYPES = {"age_min", "age_max", "attempts_max", "min_percentage"}
_TEXT_RULE_TYPES = {
    "education_min_level", "nationality", "gender", "discipline", "certification", "stream_availability"
}
_JSON_RULE_TYPES = {"qualification_combination"}

_QC_TEXT_TYPES = {"discipline", "certification", "education_min_level", "nationality"}
# experience_min_years is cycle-only (§4) and is NOT allowed in a baseline combo.
_QC_NUM_TYPES = {"min_percentage"}
_STREAM_AVAILABILITY_VALUES = {"offered", "not_offered", "expected"}


def _valid_qualification_combination(node: Any) -> bool:
    """Mirror of migration 248's is_valid_qualification_combination()."""
    if not isinstance(node, dict):
        return False
    if "op" in node:
        if node.get("op") not in ("and", "or"):
            return False
        clauses = node.get("clauses")
        if not isinstance(clauses, list) or not clauses:
            return False
        return all(_valid_qualification_combination(c) for c in clauses)
    rt = node.get("rule_type")
    if rt in _QC_NUM_TYPES:
        return isinstance(node.get("value_num"), (int, float)) and not isinstance(node.get("value_num"), bool)
    if rt in _QC_TEXT_TYPES:
        return isinstance(node.get("value_text"), str) and bool(node.get("value_text").strip())
    return False


class RuleCreate(BaseModel):
    scope: str = Field(default="all")
    rule_type: str
    stream_id: UUID | None = None
    value_num: float | None = None
    value_text: str | None = None
    value_json: dict | list | None = None
    is_knockout: bool = True
    source_url: str | None = None
    source_notes: str | None = None
    reviewer_status: str = Field(default="draft")
    waiver_reason: str | None = None


class RuleUpdate(BaseModel):
    scope: str | None = None
    rule_type: str | None = None
    stream_id: UUID | None = None
    value_num: float | None = None
    value_text: str | None = None
    value_json: dict | list | None = None
    is_knockout: bool | None = None
    source_url: str | None = None
    source_notes: str | None = None
    reviewer_status: str | None = None
    waiver_reason: str | None = None


def _validate_rule_shape(
    *,
    scope: str,
    rule_type: str,
    value_num: float | None,
    value_text: str | None,
    reviewer_status: str,
    value_json: Any = None,
) -> None:
    if scope not in _ALLOWED_SCOPES:
        raise HTTPException(status_code=400, detail=f"invalid_scope: {scope}")
    if rule_type not in _ALLOWED_RULE_TYPES:
        raise HTTPException(status_code=400, detail=f"invalid_rule_type: {rule_type}")
    if reviewer_status not in _ALLOWED_REVIEWER_STATUS:
        raise HTTPException(status_code=400, detail=f"invalid_reviewer_status: {reviewer_status}")
    if rule_type in _NUMERIC_RULE_TYPES:
        if value_num is None:
            raise HTTPException(
                status_code=400,
                detail=f"{rule_type} requires value_num",
            )
    if rule_type in _TEXT_RULE_TYPES:
        if not value_text or not str(value_text).strip():
            raise HTTPException(
                status_code=400,
                detail=f"{rule_type} requires value_text",
            )
    if rule_type == "stream_availability" and value_text is not None:
        if str(value_text).strip().lower() not in _STREAM_AVAILABILITY_VALUES:
            raise HTTPException(
                status_code=400,
                detail="stream_availability value_text must be one of: offered, not_offered, expected",
            )
    if rule_type in _JSON_RULE_TYPES:
        if value_json is None:
            raise HTTPException(
                status_code=400,
                detail=f"{rule_type} requires value_json",
            )
        if not _valid_qualification_combination(value_json):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"{rule_type} value_json must be a valid combination: "
                    '{"op":"and"|"or","clauses":[{"rule_type":...,"value_text"|"value_num":...}, ...]}'
                ),
            )

def _reject_ambiguous_linked_qualification(
    supabase, exam_id, stream_id, scope: str, rule_type: str, reviewer_status: str
) -> None:
    """Forbid the ambiguous two-row representation of a linked qualification
    fact (checkpost P0). A verified `discipline` AND a verified `min_percentage`
    for the same (exam, stream, scope) would let the evaluator satisfy them from
    two UNRELATED education records (LLB@50% + B.Com@75%). Linked facts must be
    authored as a single record-correlated `qualification_combination`.
    """
    if reviewer_status != "verified" or rule_type not in ("discipline", "min_percentage"):
        return
    sibling = "min_percentage" if rule_type == "discipline" else "discipline"
    cands = (
        supabase.table("exam_eligibility_rules")
        .select("id, stream_id")
        .eq("exam_id", str(exam_id))
        .eq("scope", scope)
        .eq("rule_type", sibling)
        .eq("reviewer_status", "verified")
        .limit(50)
        .execute()
        .data
        or []
    )
    target = str(stream_id) if stream_id is not None else None
    if any((c.get("stream_id") or None) == target for c in cands):
        raise HTTPException(
            status_code=422,
            detail=(
                "A verified '" + sibling + "' rule already exists for this "
                "(exam, stream, scope). Linked discipline+percentage requirements "
                "must be one record-correlated 'qualification_combination', not two "
                "separate verified rules (they would be satisfiable by unrelated qualifications)."
            ),
        )


def _require_trust_provenance(source_url: str | None, waiver_reason: str | None) -> None:
    """Setting reviewer_status='verified' or archiving requires a source URL or an explicit waiver."""
    if source_url and str(source_url).strip():
        return
    if waiver_reason and str(waiver_reason).strip():
        return
    raise HTTPException(
        status_code=422,
        detail=(
            "Trust-transition requires either a non-empty source_url "
            "or a waiver_reason explaining why source documentation is unavailable."
        ),
    )


# ── Read endpoints ───────────────────────────────────────────────────────


@router.get("/exams")
def list_exams_with_rule_counts(
    _admin: dict = Depends(require_permission(ADMIN_PERM)),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    exams = (
        supabase.table("exams")
        .select("id, slug, name, is_active, exam_family_id")
        .eq("is_active", True)
        .order("name")
        .limit(500)
        .execute()
        .data
        or []
    )
    rules = (
        supabase.table("exam_eligibility_rules")
        .select("exam_id, reviewer_status")
        .limit(5000)
        .execute()
        .data
        or []
    )
    counts: dict[str, dict[str, int]] = {}
    for r in rules:
        bucket = counts.setdefault(
            r["exam_id"], {"draft": 0, "verified": 0, "archived": 0}
        )
        status = r.get("reviewer_status") or "draft"
        bucket[status] = bucket.get(status, 0) + 1
    items = []
    for e in exams:
        c = counts.get(e["id"], {"draft": 0, "verified": 0, "archived": 0})
        items.append({**e, "rule_counts": c, "total_rules": sum(c.values())})
    return {"items": items}


@router.get("/exams/{exam_id}/rules")
def list_rules_for_exam(
    exam_id: UUID,
    _admin: dict = Depends(require_permission(ADMIN_PERM)),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    exam_row = (
        supabase.table("exams")
        .select("id, slug, name")
        .eq("id", str(exam_id))
        .limit(1)
        .execute()
        .data
        or []
    )
    if not exam_row:
        raise HTTPException(status_code=404, detail="exam_not_found")
    rules = (
        supabase.table("exam_eligibility_rules")
        .select(
            "id, exam_id, stream_id, scope, rule_type, value_num, value_text, value_json, "
            "is_knockout, source_url, source_notes, reviewer_status, verified_by, verified_at, "
            "created_at, updated_at"
        )
        .eq("exam_id", str(exam_id))
        .order("rule_type")
        .order("scope")
        .limit(500)
        .execute()
        .data
        or []
    )
    return {"exam": exam_row[0], "rules": rules}


# ── Write endpoints ──────────────────────────────────────────────────────


@router.post("/exams/{exam_id}/rules")
def create_rule(
    exam_id: UUID,
    body: RuleCreate,
    admin: dict = Depends(require_permission(ADMIN_PERM)),
) -> dict[str, Any]:
    _validate_rule_shape(
        scope=body.scope,
        rule_type=body.rule_type,
        value_num=body.value_num,
        value_text=body.value_text,
        reviewer_status=body.reviewer_status,
        value_json=body.value_json,
    )
    supabase = get_supabase_admin()
    if not (
        supabase.table("exams").select("id").eq("id", str(exam_id)).limit(1).execute().data
    ):
        raise HTTPException(status_code=404, detail="exam_not_found")

    _reject_ambiguous_linked_qualification(
        supabase, exam_id, body.stream_id, body.scope, body.rule_type, body.reviewer_status
    )

    # Pre-empt the unique constraint to give a clean 409. The identity is
    # (exam_id, stream_id, scope, rule_type) per migration 248 — a common rule
    # (stream_id NULL) and a stream-specific rule for the same scope/type
    # legitimately coexist, so the stream_id must be part of this check.
    # Filtered in Python (not `.is_`) so NULL matching is driver-agnostic.
    candidates = (
        supabase.table("exam_eligibility_rules")
        .select("id, stream_id")
        .eq("exam_id", str(exam_id))
        .eq("scope", body.scope)
        .eq("rule_type", body.rule_type)
        .limit(50)
        .execute()
        .data
        or []
    )
    target_stream = str(body.stream_id) if body.stream_id is not None else None
    existing = [c for c in candidates if (c.get("stream_id") or None) == target_stream]
    if existing:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "RULE_ALREADY_EXISTS",
                "rule_id": existing[0]["id"],
                "message": "A rule with this (stream, scope, rule_type) already exists. Edit the existing row.",
            },
        )

    payload: dict[str, Any] = {
        "exam_id": str(exam_id),
        "stream_id": str(body.stream_id) if body.stream_id is not None else None,
        "scope": body.scope,
        "rule_type": body.rule_type,
        "value_num": body.value_num,
        "value_text": body.value_text,
        "value_json": body.value_json,
        "is_knockout": body.is_knockout,
        "source_url": body.source_url,
        "source_notes": body.source_notes,
        "reviewer_status": body.reviewer_status,
    }
    if body.reviewer_status == "verified":
        _require_trust_provenance(body.source_url, body.waiver_reason)
        payload["verified_by"] = admin.get("id")
        payload["verified_at"] = datetime.now(timezone.utc).isoformat()
    inserted = (
        supabase.table("exam_eligibility_rules")
        .insert(payload)
        .execute()
        .data
        or []
    )
    row = inserted[0] if inserted else None
    _audit(
        supabase,
        admin,
        "eligibility_rule.create",
        "exam_eligibility_rule",
        str(row["id"]) if row else "unknown",
        after_payload=row,
        metadata=body.waiver_reason,
    )
    invalidate_eligibility_rules_cache()
    return {"rule": row}


@router.put("/rules/{rule_id}")
def update_rule(
    rule_id: UUID,
    body: RuleUpdate,
    admin: dict = Depends(require_permission(ADMIN_PERM)),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    existing = (
        supabase.table("exam_eligibility_rules")
        .select(
            "id, exam_id, stream_id, scope, rule_type, value_num, value_text, value_json, "
            "is_knockout, source_url, source_notes, reviewer_status, "
            "verified_by, verified_at, created_at, updated_at"
        )
        .eq("id", str(rule_id))
        .limit(1)
        .execute()
        .data
        or []
    )
    if not existing:
        raise HTTPException(status_code=404, detail="rule_not_found")
    current = existing[0]

    merged_scope = body.scope if body.scope is not None else current["scope"]
    merged_type = body.rule_type if body.rule_type is not None else current["rule_type"]
    merged_value_num = body.value_num if body.value_num is not None else current.get("value_num")
    merged_value_text = (
        body.value_text if body.value_text is not None else current.get("value_text")
    )
    merged_value_json = (
        body.value_json if body.value_json is not None else current.get("value_json")
    )
    merged_status = (
        body.reviewer_status if body.reviewer_status is not None else current["reviewer_status"]
    )
    _validate_rule_shape(
        scope=merged_scope,
        rule_type=merged_type,
        value_num=merged_value_num,
        value_text=merged_value_text,
        reviewer_status=merged_status,
        value_json=merged_value_json,
    )
    merged_stream = (
        body.stream_id if "stream_id" in body.model_fields_set else current.get("stream_id")
    )
    _reject_ambiguous_linked_qualification(
        supabase, current["exam_id"], merged_stream, merged_scope, merged_type, merged_status
    )

    patch: dict[str, Any] = {}
    if body.scope is not None:
        patch["scope"] = body.scope
    if body.rule_type is not None:
        patch["rule_type"] = body.rule_type
    # stream_id uses presence-in-payload (not non-null) so an operator can CLEAR
    # a stream assignment (set null) to return a rule to common scope.
    if "stream_id" in body.model_fields_set:
        patch["stream_id"] = str(body.stream_id) if body.stream_id is not None else None
    if body.value_num is not None:
        patch["value_num"] = body.value_num
    if body.value_text is not None:
        patch["value_text"] = body.value_text
    if body.value_json is not None:
        patch["value_json"] = body.value_json
    if body.is_knockout is not None:
        patch["is_knockout"] = body.is_knockout
    if body.source_url is not None:
        patch["source_url"] = body.source_url
    if body.source_notes is not None:
        patch["source_notes"] = body.source_notes
    transitioning_to_verified = (
        body.reviewer_status == "verified"
        and current.get("reviewer_status") != "verified"
    )
    if body.reviewer_status is not None:
        patch["reviewer_status"] = body.reviewer_status
        # Promotion to ``verified`` stamps the reviewer + timestamp; any
        # transition AWAY from verified clears them so we never claim a
        # draft row was verified by someone.
        if body.reviewer_status == "verified":
            effective_source_url = body.source_url if body.source_url is not None else current.get("source_url")
            _require_trust_provenance(effective_source_url, body.waiver_reason)
            patch["verified_by"] = admin.get("id")
            patch["verified_at"] = datetime.now(timezone.utc).isoformat()
        else:
            patch["verified_by"] = None
            patch["verified_at"] = None
    patch["updated_at"] = datetime.now(timezone.utc).isoformat()

    updated = (
        supabase.table("exam_eligibility_rules")
        .update(patch)
        .eq("id", str(rule_id))
        .execute()
        .data
        or []
    )
    audit_action = "eligibility_rule.verify" if transitioning_to_verified else "eligibility_rule.update"
    _audit(
        supabase,
        admin,
        audit_action,
        "exam_eligibility_rule",
        str(rule_id),
        before_payload=current,
        after_payload=updated[0] if updated else patch,
        metadata=body.waiver_reason,
    )
    invalidate_eligibility_rules_cache()
    return {"rule": updated[0] if updated else None}


@router.delete("/rules/{rule_id}")
def delete_rule(
    rule_id: UUID,
    hard: bool = Query(default=False),
    waiver_reason: str | None = Query(default=None),
    admin: dict = Depends(require_permission(ADMIN_PERM)),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    existing = (
        supabase.table("exam_eligibility_rules")
        .select(
            "id, exam_id, scope, rule_type, value_num, value_text, "
            "is_knockout, source_url, source_notes, reviewer_status, "
            "verified_by, verified_at, created_at, updated_at"
        )
        .eq("id", str(rule_id))
        .limit(1)
        .execute()
        .data
        or []
    )
    if not existing:
        raise HTTPException(status_code=404, detail="rule_not_found")
    current = existing[0]

    if hard:
        supabase.table("exam_eligibility_rules").delete().eq("id", str(rule_id)).execute()
        _audit(
            supabase,
            admin,
            "eligibility_rule.delete",
            "exam_eligibility_rule",
            str(rule_id),
            before_payload=current,
            metadata=waiver_reason,
        )
        invalidate_eligibility_rules_cache()
        return {"deleted": True, "hard": True}

    _require_trust_provenance(current.get("source_url"), waiver_reason)
    archive_patch = {
        "reviewer_status": "archived",
        "verified_by": None,
        "verified_at": None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    supabase.table("exam_eligibility_rules").update(archive_patch).eq("id", str(rule_id)).execute()
    _audit(
        supabase,
        admin,
        "eligibility_rule.archive",
        "exam_eligibility_rule",
        str(rule_id),
        before_payload=current,
        after_payload={**current, **archive_patch},
        metadata=waiver_reason,
    )
    invalidate_eligibility_rules_cache()
    return {"deleted": True, "hard": False, "archived_by": admin.get("id")}
