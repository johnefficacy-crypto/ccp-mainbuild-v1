"""Content Studio — canonical content authoring/governance (subject-scoped).

Per docs/architecture/content-studio.md + migration 214 (content scoping):
canonical `writing_prompts` are SUBJECT-scoped (no exam columns); applicability
is carried by `writing_prompt_targets`. This router is the operator write path:

  Library / Review Queue  → writing_prompts create/list/get/patch/review/bulk
                             (author = content_studio.author; review =
                              content_studio.review; reads = author OR review OR
                              exam_intelligence.manage)
  Exam Assignments        → writing_prompt_targets list/propose/review/remove.
                             Split by the LOCKED J2 authority separation:
                             manage (exam_intelligence.manage) PROPOSES an inert
                             pending_review assignment; review
                             (exam_intelligence.review) PROMOTES it to an
                             effective active|excluded state and removes it.
                             Making content applicable is a lifecycle transition,
                             which manage never performs (§1.1 + J2 gate §D).

Every write goes through an atomic SECURITY DEFINER RPC (migration 215); this
layer is validation + permission + error mapping only.

ACTIVATION is intentionally absent: migration 214's activation gate deactivated
all prompts and blocks reactivation until the applicability resolver +
session/planner enforcement + writing_prompts_public_read replacement land
(separate PR). There is no activate endpoint here.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StrictStr,
    ValidationError,
    field_validator,
    model_validator,
)

from app.api.admin_exam_intel_cms import WriteEnvelope, _flag_enabled, _safe_select
from app.core.auth import get_current_user, require_permission
from app.core.permissions import (
    CONTENT_STUDIO_AUTHOR,
    CONTENT_STUDIO_REVIEW,
    EXAM_INTELLIGENCE_MANAGE,
    EXAM_INTELLIGENCE_REVIEW,
)
from app.db.supabase_client import get_supabase_admin

logger = logging.getLogger("career_copilot.api.content_studio")

router = APIRouter(prefix="/admin/content-studio", tags=["admin-content-studio"])

PERM_AUTHOR = CONTENT_STUDIO_AUTHOR
PERM_REVIEW = CONTENT_STUDIO_REVIEW
# Applicability authority is split by the locked J2 gate (see permissions.py):
#   PERM_ASSIGN        (manage) — PROPOSE an inert pending_review assignment
#   PERM_ASSIGN_REVIEW (review) — PROMOTE it to effective active|excluded + remove
PERM_ASSIGN = EXAM_INTELLIGENCE_MANAGE
PERM_ASSIGN_REVIEW = EXAM_INTELLIGENCE_REVIEW

_EXERCISE_TYPES = Literal[
    "sentence_construction", "sentence_correction", "vocabulary_in_context",
    "sentence_rewrite", "sentence_reconstruction", "paragraph_writing",
    "summary_writing", "precis_practice", "essay_practice", "letter_practice",
]

_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "pending": ("verified", "rejected", "needs_correction"),
    "needs_correction": ("verified", "rejected", "pending"),
    "verified": ("rejected", "needs_correction"),
    "rejected": (),
}
_TARGET_STATUSES = frozenset(s for t in _TRANSITIONS.values() for s in t)

# NOT-NULL columns (some via DEFAULT) — reject explicit null at the boundary.
_NOT_NULL = frozenset({
    "subject_id", "topic_id", "exercise_type", "prompt_text",
    "difficulty_level", "max_rewrite_attempts", "metadata",
})


def _require_content_read(user: dict = Depends(get_current_user)) -> dict:
    """A reviewer or the Manage-Exam operator must be able to load the queue."""
    if user.get("is_anonymous"):
        raise HTTPException(status_code=403, detail="Anonymous users cannot access this resource")
    if user.get("role") == "super_admin":
        return user
    perms = set(user.get("permissions") or [])
    if perms & {PERM_AUTHOR, PERM_REVIEW, PERM_ASSIGN, PERM_ASSIGN_REVIEW}:
        return user
    raise HTTPException(
        status_code=403,
        detail="Missing permission: content_studio.author/review or exam_intelligence.manage/review")


class _RejectExplicitNull(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def _no_explicit_null(cls, data):
        if isinstance(data, dict):
            bad = sorted(k for k in _NOT_NULL if k in data and data[k] is None)
            if bad:
                raise ValueError(f"these fields may not be null: {bad}")
        return data


class _PromptBase(_RejectExplicitNull):
    model_config = ConfigDict(extra="forbid")
    topic_id: UUID
    microtopic_id: UUID | None = None
    exercise_type: _EXERCISE_TYPES
    prompt_text: StrictStr = Field(min_length=1)
    source_text: StrictStr | None = None
    required_words: list[StrictStr] | None = None
    required_sentence_count: StrictInt | None = Field(default=None, gt=0)
    difficulty_level: StrictInt = Field(ge=1, le=10)
    min_words: StrictInt | None = Field(default=None, ge=0)
    max_words: StrictInt | None = Field(default=None, ge=0)
    max_rewrite_attempts: StrictInt | None = Field(default=None, ge=0)
    rubric_id: UUID | None = None
    source_document_id: UUID | None = None
    metadata: dict[str, Any] | None = None

    @field_validator("max_words")
    @classmethod
    def _max_ge_min(cls, v, info):
        mn = info.data.get("min_words")
        if v is not None and mn is not None and v < mn:
            raise ValueError("max_words must be >= min_words")
        return v


class WritingPromptCreate(_PromptBase):
    subject_id: UUID


class WritingPromptPatch(_RejectExplicitNull):
    model_config = ConfigDict(extra="forbid")
    subject_id: UUID | None = None
    topic_id: UUID | None = None
    microtopic_id: UUID | None = None
    exercise_type: _EXERCISE_TYPES | None = None
    prompt_text: StrictStr | None = Field(default=None, min_length=1)
    source_text: StrictStr | None = None
    required_words: list[StrictStr] | None = None
    required_sentence_count: StrictInt | None = Field(default=None, gt=0)
    difficulty_level: StrictInt | None = Field(default=None, ge=1, le=10)
    min_words: StrictInt | None = Field(default=None, ge=0)
    max_words: StrictInt | None = Field(default=None, ge=0)
    max_rewrite_attempts: StrictInt | None = Field(default=None, ge=0)
    rubric_id: UUID | None = None
    source_document_id: UUID | None = None
    metadata: dict[str, Any] | None = None


class WritingPromptBulkRow(_PromptBase):
    external_key: StrictStr = Field(min_length=1)

    @field_validator("external_key")
    @classmethod
    def _nonblank(cls, v):
        if not v or not v.strip():
            raise ValueError("external_key must be non-blank")
        return v.strip()


class WritingPromptBulkBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(..., min_length=8, max_length=500)
    subject_id: UUID = Field(..., description="all rows belong to this subject (idempotency scope)")
    rows: list[WritingPromptBulkRow] = Field(..., min_length=1, max_length=500)


class WritingPromptReviewBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str
    reason: str = Field(..., min_length=8, max_length=500)
    reviewer_notes: str | None = Field(default=None, max_length=2000)


class WritingPromptTargetProposeBody(BaseModel):
    """manage authority: PROPOSE an inert pending_review assignment (§J2 split).

    There is deliberately no ``applicability_status`` — manage can only create an
    inert proposal; making it effective (active|excluded) is a review transition.
    """
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(..., min_length=8, max_length=500)
    is_global: bool = False
    exam_family_id: UUID | None = None
    exam_id: UUID | None = None
    exam_phase_id: UUID | None = None
    priority_score: float | None = None


class WritingPromptTargetReviewBody(BaseModel):
    """review authority: PROMOTE a pending_review assignment to effective state."""
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(..., min_length=8, max_length=500)
    applicability_status: Literal["active", "excluded"]
    priority_score: float | None = None
    expected_updated_at: str = Field(..., description="CAS token from the target's updated_at")


def _jsonable(model: BaseModel, *, exclude_unset: bool) -> dict[str, Any]:
    return model.model_dump(mode="json", exclude_unset=exclude_unset)


def _parse(model_cls, payload: dict[str, Any]):
    try:
        return model_cls(**(payload or {}))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=json.loads(exc.json())) from exc


def _map_rpc_error(exc: Exception, ctx: str) -> HTTPException:
    low = str(exc).lower()
    if "concurrent_modification" in low:
        return HTTPException(status_code=409,
                             detail="Concurrent modification: changed since read. Re-fetch and retry.")
    if "prompt_verified_locked" in low:
        return HTTPException(status_code=422, detail={
            "error": "prompt_verified_locked",
            "message": "A verified prompt cannot be edited. Move it to 'needs_correction' via review first."})
    if "target_exists" in low:
        return HTTPException(status_code=409, detail=str(exc))
    if any(tok in low for tok in (
        "transition_not_allowed", "invalid_target_status", "missing_actor_id",
        "invalid_reason", "invalid_scope", "bulk_locked_row",
        "target_effective_locked",
    )) or "violates check constraint" in low:
        return HTTPException(status_code=422, detail=str(exc))
    if "not_found" in low:
        return HTTPException(status_code=404, detail=str(exc))
    logger.exception("%s RPC failed; no change recorded", ctx)
    return HTTPException(status_code=500, detail="content_studio RPC failed")


def _rpc_row(result) -> dict:
    data = getattr(result, "data", None)
    if isinstance(data, dict):
        return data
    return (data or [{}])[0] if isinstance(data, list) and data else (data or {})


# ── Library / Review Queue ─────────────────────────────────────────────────


@router.get("/writing-prompts")
def list_writing_prompts(
    subject_id: str | None = Query(default=None),
    topic_id: str | None = Query(default=None),
    microtopic_id: str | None = Query(default=None),
    exercise_type: str | None = Query(default=None),
    difficulty_level: int | None = Query(default=None, ge=1, le=10),
    reviewer_status: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    q: str | None = Query(default=None, description="substring match on prompt_text"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(_require_content_read),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    query = supabase.table("writing_prompts").select("*", count="exact").order("created_at", desc=True)
    for col, val in (
        ("subject_id", subject_id), ("topic_id", topic_id), ("microtopic_id", microtopic_id),
        ("exercise_type", exercise_type), ("difficulty_level", difficulty_level),
        ("reviewer_status", reviewer_status),
    ):
        if val is not None:
            query = query.eq(col, val)
    if is_active is not None:
        query = query.eq("is_active", is_active)
    if q:
        query = query.ilike("prompt_text", f"%{q}%")
    res = query.range(offset, offset + limit - 1).execute()
    return {"items": res.data or [], "total": getattr(res, "count", None), "limit": limit, "offset": offset}


@router.get("/writing-prompts/{prompt_id}")
def get_writing_prompt(
    prompt_id: str,
    _admin: dict = Depends(_require_content_read),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    prompt = _safe_select(supabase, "writing_prompts", id=prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="writing_prompt not found")
    return prompt


@router.post("/writing-prompts")
def create_writing_prompt(
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_AUTHOR)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    model = _parse(WritingPromptCreate, body.payload)
    try:
        result = supabase.rpc("cms_create_writing_prompt", {
            "p_payload": _jsonable(model, exclude_unset=True),
            "p_reason": body.reason,
            "p_actor_user_id": admin.get("id"),
            "p_actor_email": admin.get("email"),
        }).execute()
    except Exception as exc:  # noqa: BLE001
        raise _map_rpc_error(exc, "create_writing_prompt") from exc
    res = _rpc_row(result)
    return {"ok": True, "audit_id": res.get("audit_id"), "row": res.get("row")}


@router.patch("/writing-prompts/{prompt_id}")
def update_writing_prompt(
    prompt_id: str,
    body: WriteEnvelope,
    admin: dict = Depends(require_permission(PERM_AUTHOR)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    model = _parse(WritingPromptPatch, body.payload)
    patch = _jsonable(model, exclude_unset=True)
    if not patch:
        raise HTTPException(status_code=422, detail="No fields to update")
    existing = _safe_select(supabase, "writing_prompts", id=prompt_id)
    if not existing:
        raise HTTPException(status_code=404, detail="writing_prompt not found")
    merged_min = patch.get("min_words", existing.get("min_words"))
    merged_max = patch.get("max_words", existing.get("max_words"))
    if isinstance(merged_min, int) and isinstance(merged_max, int) and merged_max < merged_min:
        raise HTTPException(status_code=422, detail="max_words must be >= min_words (merged with stored values)")
    try:
        result = supabase.rpc("cms_update_writing_prompt", {
            "p_prompt_id": prompt_id,
            "p_expected_updated_at": existing.get("updated_at"),
            "p_patch": patch,
            "p_reason": body.reason,
            "p_actor_user_id": admin.get("id"),
            "p_actor_email": admin.get("email"),
        }).execute()
    except Exception as exc:  # noqa: BLE001
        raise _map_rpc_error(exc, "update_writing_prompt") from exc
    return {"ok": True, "result": _rpc_row(result)}


@router.post("/writing-prompts/bulk")
def bulk_upsert_writing_prompts(
    body: WritingPromptBulkBody,
    admin: dict = Depends(require_permission(PERM_AUTHOR)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    rows = [_jsonable(r, exclude_unset=True) for r in body.rows]
    try:
        result = supabase.rpc("cms_bulk_upsert_writing_prompts", {
            "p_subject_id": str(body.subject_id),
            "p_rows": rows,
            "p_reason": body.reason,
            "p_actor_user_id": admin.get("id"),
            "p_actor_email": admin.get("email"),
        }).execute()
    except Exception as exc:  # noqa: BLE001
        raise _map_rpc_error(exc, "bulk_upsert_writing_prompts") from exc
    return {"ok": True, "result": _rpc_row(result)}


@router.post("/writing-prompts/{prompt_id}/review")
def review_writing_prompt(
    prompt_id: str,
    body: WritingPromptReviewBody,
    admin: dict = Depends(require_permission(PERM_REVIEW)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    if body.status not in _TARGET_STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {sorted(_TARGET_STATUSES)}")
    supabase = get_supabase_admin()
    existing = _safe_select(supabase, "writing_prompts", id=prompt_id)
    if not existing:
        raise HTTPException(status_code=404, detail="writing_prompt not found")
    from_status = existing.get("reviewer_status", "pending")
    if body.status not in _TRANSITIONS.get(from_status, ()):
        raise HTTPException(status_code=422, detail=(
            f"Transition '{from_status}' → '{body.status}' is not allowed. "
            f"Allowed: {list(_TRANSITIONS.get(from_status, ()))}"))
    try:
        result = supabase.rpc("cms_review_writing_prompt", {
            "p_prompt_id": prompt_id,
            "p_expected_status": from_status,
            "p_expected_updated_at": existing.get("updated_at"),
            "p_new_status": body.status,
            "p_reason": body.reason,
            "p_reviewer_notes": body.reviewer_notes,
            "p_actor_user_id": admin.get("id"),
            "p_actor_email": admin.get("email"),
        }).execute()
    except Exception as exc:  # noqa: BLE001
        raise _map_rpc_error(exc, "review_writing_prompt") from exc
    return {"ok": True, "result": _rpc_row(result)}


# ── Exam Assignments (applicability — writing_prompt_targets) ───────────────


@router.get("/writing-prompts/{prompt_id}/targets")
def list_writing_prompt_targets(
    prompt_id: str,
    _admin: dict = Depends(_require_content_read),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    res = (supabase.table("writing_prompt_targets").select("*")
           .eq("prompt_id", prompt_id).order("created_at", desc=True).execute())
    return {"items": res.data or []}


@router.post("/writing-prompts/{prompt_id}/targets")
def propose_writing_prompt_target(
    prompt_id: str,
    body: WritingPromptTargetProposeBody,
    admin: dict = Depends(require_permission(PERM_ASSIGN)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """manage: propose an INERT pending_review assignment (§J2 authority split)."""
    supabase = get_supabase_admin()
    try:
        result = supabase.rpc("cms_propose_writing_prompt_target", {
            "p_prompt_id": prompt_id,
            "p_is_global": body.is_global,
            "p_exam_family_id": str(body.exam_family_id) if body.exam_family_id else None,
            "p_exam_id": str(body.exam_id) if body.exam_id else None,
            "p_exam_phase_id": str(body.exam_phase_id) if body.exam_phase_id else None,
            "p_priority": body.priority_score,
            "p_reason": body.reason,
            "p_actor_user_id": admin.get("id"),
            "p_actor_email": admin.get("email"),
        }).execute()
    except Exception as exc:  # noqa: BLE001
        raise _map_rpc_error(exc, "propose_writing_prompt_target") from exc
    return {"ok": True, "result": _rpc_row(result)}


@router.post("/writing-prompt-targets/{target_id}/review")
def review_writing_prompt_target(
    target_id: str,
    body: WritingPromptTargetReviewBody,
    admin: dict = Depends(require_permission(PERM_ASSIGN_REVIEW)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """review: promote a pending_review assignment to effective active|excluded."""
    supabase = get_supabase_admin()
    try:
        result = supabase.rpc("cms_review_writing_prompt_target", {
            "p_target_id": target_id,
            "p_expected_updated_at": body.expected_updated_at,
            "p_new_status": body.applicability_status,
            "p_priority": body.priority_score,
            "p_reason": body.reason,
            "p_actor_user_id": admin.get("id"),
            "p_actor_email": admin.get("email"),
        }).execute()
    except Exception as exc:  # noqa: BLE001
        raise _map_rpc_error(exc, "review_writing_prompt_target") from exc
    return {"ok": True, "result": _rpc_row(result)}


class _TargetRemoveBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(..., min_length=8, max_length=500)
    expected_updated_at: str = Field(..., description="CAS token from the target's updated_at")


@router.post("/writing-prompt-targets/{target_id}/remove")
def remove_writing_prompt_target(
    target_id: str,
    body: _TargetRemoveBody,
    admin: dict = Depends(require_permission(PERM_ASSIGN_REVIEW)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """review: CAS-guarded removal of an assignment (audits the exact old row)."""
    supabase = get_supabase_admin()
    try:
        result = supabase.rpc("cms_remove_writing_prompt_target", {
            "p_target_id": target_id,
            "p_expected_updated_at": body.expected_updated_at,
            "p_reason": body.reason,
            "p_actor_user_id": admin.get("id"),
            "p_actor_email": admin.get("email"),
        }).execute()
    except Exception as exc:  # noqa: BLE001
        raise _map_rpc_error(exc, "remove_writing_prompt_target") from exc
    return {"ok": True, "result": _rpc_row(result)}
