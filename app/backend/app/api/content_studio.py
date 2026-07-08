"""Content Studio — canonical content authoring/governance (subject-scoped).

Per docs/architecture/content-studio.md + migration 214 (content scoping):
canonical `writing_prompts` are SUBJECT-scoped (no exam columns); applicability
is carried by `writing_prompt_targets`. This router is the operator write path:

  Library / Review Queue  → writing_prompts create/list/get/patch/review/bulk
                             (author = content_studio.author; review =
                              content_studio.review; reads = author OR review OR
                              exam_intelligence.manage OR exam_intelligence.review)
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

  Activation lifecycle       → writing_prompts activate/deactivate. A SEPARATE,
                               higher-trust authority (content_studio.activate) —
                               neither author nor review may flip is_active. The
                               RPC (migration 224) is the SOLE eligibility
                               authority: a blocked activation is a NORMAL
                               {eligible:false, blockers} 200 answer; this layer
                               never computes eligibility.
"""
from __future__ import annotations

import json
import logging
import unicodedata
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
from app.study_os.writing_practice.deterministic import tokenize_words as _tokenize_words
from app.core.auth import get_current_user, require_permission
from app.core.permissions import (
    CONTENT_STUDIO_ACTIVATE,
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
# Activation is a SEPARATE, higher-trust authority (migration 224): neither author
# nor review may flip is_active. Eligibility is computed SOLELY by the RPC.
PERM_ACTIVATE = CONTENT_STUDIO_ACTIVATE

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

# Reserved metadata keys the authoring boundary must never accept:
#   * `external_key` is a SYSTEM-OWNED bulk-import identity (migration 215
#     idempotency index) — only the bulk RPC assigns it, so a manual prompt can't
#     hijack an import key and a patch can't drop it and orphan a re-import.
#   * `exam_id` / `exam_cycle_id` / `exam_phase_id` are the dual-authority scope
#     columns migration 214 DROPPED — stashing them in free-form metadata would
#     reopen exactly the exam-scope backdoor content-scoping closed. Applicability
#     lives solely in writing_prompt_targets.
_RESERVED_METADATA_KEYS = frozenset({
    "external_key", "exam_id", "exam_cycle_id", "exam_phase_id",
})


def _canonicalize_required_words(words: list[str]) -> list[str]:
    """NFC + trim each required word; require EXACTLY ONE backend word token
    (mirrors ``deterministic.tokenize_words`` — hyphen/apostrophe compounds are
    one token); dedupe case-insensitively (the backend match is case-fold). The
    display form of the first occurrence is preserved. Raises ValueError on any
    blank, multi-token, or duplicate entry so the authoring boundary can never
    store a required word the runtime coverage check can never satisfy."""
    out: list[str] = []
    seen: set[str] = set()
    for raw in words:
        norm = unicodedata.normalize("NFC", raw).strip()
        if not norm:
            raise ValueError("required_words entries must be non-blank")
        toks = _tokenize_words(norm)
        if len(toks) != 1 or toks[0] != norm:
            raise ValueError(
                f"required word {raw!r} must be exactly one word token "
                "(no blanks, punctuation, or multi-word phrases)")
        key = norm.casefold()
        if key in seen:
            raise ValueError(f"duplicate required word (case-insensitive): {raw!r}")
        seen.add(key)
        out.append(norm)
    return out


def _reject_reserved_metadata(md: dict | None) -> dict | None:
    if md is not None:
        bad = sorted(_RESERVED_METADATA_KEYS & set(md))
        if bad:
            raise ValueError(f"metadata keys are system-owned and may not be set here: {bad}")
    return md


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

    @field_validator("prompt_text")
    @classmethod
    def _prompt_text_nonblank(cls, v):
        if v is not None and not v.strip():
            raise ValueError("prompt_text must not be blank/whitespace-only")
        return v

    @field_validator("required_words")
    @classmethod
    def _canon_required_words(cls, v):
        return _canonicalize_required_words(v) if v is not None else v

    @field_validator("metadata")
    @classmethod
    def _no_reserved_metadata(cls, v):
        return _reject_reserved_metadata(v)


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

    @field_validator("prompt_text")
    @classmethod
    def _patch_prompt_text_nonblank(cls, v):
        if v is not None and not v.strip():
            raise ValueError("prompt_text must not be blank/whitespace-only")
        return v

    @field_validator("required_words")
    @classmethod
    def _patch_canon_required_words(cls, v):
        return _canonicalize_required_words(v) if v is not None else v

    @field_validator("metadata")
    @classmethod
    def _patch_no_reserved_metadata(cls, v):
        return _reject_reserved_metadata(v)


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


class WritingPromptPatchEnvelope(BaseModel):
    """Curation write body carrying the CLIENT's optimistic-lock token.

    ``expected_updated_at`` is the ``updated_at`` the operator's browser last read
    (from GET) — NOT a value the server re-reads just before the write. Passing
    the client token unchanged is what makes edit-after-edit lose (409); a
    server-minted fresh token would silently clobber a concurrent edit."""
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(..., min_length=8, max_length=500)
    expected_updated_at: str = Field(..., description="updated_at the client last read (CAS token)")
    payload: dict[str, Any] = Field(default_factory=dict)


class WritingPromptReviewBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str
    expected_status: str = Field(..., description="reviewer_status the client last saw (CAS)")
    expected_updated_at: str = Field(..., description="updated_at the client last read (CAS token)")
    reason: str = Field(..., min_length=8, max_length=500)
    reviewer_notes: str | None = Field(default=None, max_length=2000)


class WritingPromptActivateBody(BaseModel):
    """content_studio.activate authority: request activation of a verified prompt.

    Eligibility is NEVER computed here — the RPC (migration 224) verifies every
    precondition under a row lock and returns a structured
    ``{eligible, blockers}`` verdict. This body only carries the reason + the
    client's optimistic-lock token (so a stale-browser activation loses with 409).
    """
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(..., min_length=8, max_length=500)
    expected_updated_at: str = Field(..., description="updated_at the client last read (CAS token)")


class WritingPromptDeactivateBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(..., min_length=8, max_length=500)
    expected_updated_at: str = Field(..., description="updated_at the client last read (CAS token)")


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
    if "target_exists" in low or "violates unique constraint" in low:
        return HTTPException(status_code=409, detail=str(exc))
    if any(tok in low for tok in (
        "transition_not_allowed", "invalid_target_status", "missing_actor_id",
        "invalid_reason", "invalid_scope", "bulk_locked_row",
        "target_effective_locked", "reserved_metadata_key",
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


# ── Readable-label enrichment (operator usability, EWP-SP4) ─────────────────
#
# Canonical rows store bare FK UUIDs; the operator surfaces must show human
# names. Enrichment is READ-ONLY and best-effort (a resolved name that is None
# simply renders as "—"); it never changes the authoritative id columns, which
# stay `subject_id` / `topic_id` / `exam_id` / `exam_phase_id` on the wire.


def _name_of(supabase, table: str, id_val, field: str = "name"):
    if not id_val:
        return None
    row = _safe_select(supabase, table, id=str(id_val))
    return (row.get(field) if row else None)


def _enrich_prompt_labels(supabase, prompt: dict) -> dict:
    """Attach *_name display labels to a writing_prompt row (never mutates ids)."""
    if not isinstance(prompt, dict):
        return prompt
    prompt["subject_name"] = _name_of(supabase, "subjects", prompt.get("subject_id"))
    prompt["topic_name"] = _name_of(supabase, "topics", prompt.get("topic_id"))
    prompt["microtopic_name"] = _name_of(supabase, "topics", prompt.get("microtopic_id"))
    prompt["rubric_name"] = _name_of(supabase, "writing_rubrics", prompt.get("rubric_id"))
    doc_id = prompt.get("source_document_id")
    doc = _safe_select(supabase, "document_assets", id=str(doc_id)) if doc_id else None
    prompt["source_document_title"] = (
        (doc.get("title") or doc.get("original_filename")) if doc else None
    )
    return prompt


def _enrich_target_labels(supabase, target: dict) -> dict:
    """Attach exam-scope display labels to a writing_prompt_targets row."""
    if not isinstance(target, dict):
        return target
    target["exam_family_name"] = _name_of(supabase, "exam_families", target.get("exam_family_id"))
    target["exam_name"] = _name_of(supabase, "exams", target.get("exam_id"))
    target["exam_phase_name"] = _name_of(
        supabase, "exam_phases", target.get("exam_phase_id"), field="phase_name")
    return target


# ── Library / Review Queue ─────────────────────────────────────────────────


@router.get("/writing-prompts")
def list_writing_prompts(
    subject_id: UUID | None = Query(default=None),
    topic_id: UUID | None = Query(default=None),
    microtopic_id: UUID | None = Query(default=None),
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
            query = query.eq(col, str(val))
    if is_active is not None:
        query = query.eq("is_active", is_active)
    if q:
        query = query.ilike("prompt_text", f"%{q}%")
    res = query.range(offset, offset + limit - 1).execute()
    return {"items": res.data or [], "total": getattr(res, "count", None), "limit": limit, "offset": offset}


@router.get("/writing-prompts/{prompt_id}")
def get_writing_prompt(
    prompt_id: UUID,
    _admin: dict = Depends(_require_content_read),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    prompt = _safe_select(supabase, "writing_prompts", id=str(prompt_id))
    if not prompt:
        raise HTTPException(status_code=404, detail="writing_prompt not found")
    return _enrich_prompt_labels(supabase, prompt)


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
    prompt_id: UUID,
    body: WritingPromptPatchEnvelope,
    admin: dict = Depends(require_permission(PERM_AUTHOR)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    model = _parse(WritingPromptPatch, body.payload)
    patch = _jsonable(model, exclude_unset=True)
    if not patch:
        raise HTTPException(status_code=422, detail="No fields to update")
    # Best-effort merged min/max preview (the RPC re-validates scope under lock).
    existing = _safe_select(supabase, "writing_prompts", id=str(prompt_id))
    if not existing:
        raise HTTPException(status_code=404, detail="writing_prompt not found")
    merged_min = patch.get("min_words", existing.get("min_words"))
    merged_max = patch.get("max_words", existing.get("max_words"))
    if isinstance(merged_min, int) and isinstance(merged_max, int) and merged_max < merged_min:
        raise HTTPException(status_code=422, detail="max_words must be >= min_words (merged with stored values)")
    try:
        result = supabase.rpc("cms_update_writing_prompt", {
            "p_prompt_id": str(prompt_id),
            # CLIENT's token — never a server-minted fresh read — so edit-after-edit loses.
            "p_expected_updated_at": body.expected_updated_at,
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
    prompt_id: UUID,
    body: WritingPromptReviewBody,
    admin: dict = Depends(require_permission(PERM_REVIEW)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    if body.status not in _TARGET_STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {sorted(_TARGET_STATUSES)}")
    # Guard the transition against the status the CLIENT actually saw (not a fresh
    # server read) so a reviewer can't verify content that changed under them; the
    # RPC re-checks expected_status + expected_updated_at under the row lock.
    if body.status not in _TRANSITIONS.get(body.expected_status, ()):
        raise HTTPException(status_code=422, detail=(
            f"Transition '{body.expected_status}' → '{body.status}' is not allowed. "
            f"Allowed: {list(_TRANSITIONS.get(body.expected_status, ()))}"))
    supabase = get_supabase_admin()
    try:
        result = supabase.rpc("cms_review_writing_prompt", {
            "p_prompt_id": str(prompt_id),
            "p_expected_status": body.expected_status,
            "p_expected_updated_at": body.expected_updated_at,
            "p_new_status": body.status,
            "p_reason": body.reason,
            "p_reviewer_notes": body.reviewer_notes,
            "p_actor_user_id": admin.get("id"),
            "p_actor_email": admin.get("email"),
        }).execute()
    except Exception as exc:  # noqa: BLE001
        raise _map_rpc_error(exc, "review_writing_prompt") from exc
    return {"ok": True, "result": _rpc_row(result)}


# ── Activation lifecycle (is_active) — content_studio.activate authority ────
#
# Activation is a SEPARATE authority from authoring/review. The RPC is the SOLE
# eligibility authority: a blocked activation is a NORMAL 200 answer carrying
# {eligible:false, blockers:[...]} (not an error); CAS mismatch → 409; missing
# prompt → 404; malformed body → 422. The router NEVER computes eligibility.


@router.post("/writing-prompts/{prompt_id}/activate")
def activate_writing_prompt(
    prompt_id: UUID,
    body: WritingPromptActivateBody,
    admin: dict = Depends(require_permission(PERM_ACTIVATE)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    try:
        result = supabase.rpc("cms_activate_writing_prompt", {
            "p_prompt_id": str(prompt_id),
            # CLIENT's token — never a server-minted fresh read — so a stale
            # activation loses with 409.
            "p_expected_updated_at": body.expected_updated_at,
            "p_reason": body.reason,
            # Runtime-readiness allowlist stays SERVER-OWNED (migration 224); the
            # API never widens it, so this optional narrowing param is omitted.
            "p_actor_user_id": admin.get("id"),
            "p_actor_email": admin.get("email"),
        }).execute()
    except Exception as exc:  # noqa: BLE001
        raise _map_rpc_error(exc, "activate_writing_prompt") from exc
    return {"ok": True, "result": _rpc_row(result)}


@router.post("/writing-prompts/{prompt_id}/deactivate")
def deactivate_writing_prompt(
    prompt_id: UUID,
    body: WritingPromptDeactivateBody,
    admin: dict = Depends(require_permission(PERM_ACTIVATE)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    try:
        result = supabase.rpc("cms_deactivate_writing_prompt", {
            "p_prompt_id": str(prompt_id),
            "p_expected_updated_at": body.expected_updated_at,
            "p_reason": body.reason,
            "p_actor_user_id": admin.get("id"),
            "p_actor_email": admin.get("email"),
        }).execute()
    except Exception as exc:  # noqa: BLE001
        raise _map_rpc_error(exc, "deactivate_writing_prompt") from exc
    return {"ok": True, "result": _rpc_row(result)}


# ── Exam Assignments (applicability — writing_prompt_targets) ───────────────


@router.get("/writing-prompts/{prompt_id}/targets")
def list_writing_prompt_targets(
    prompt_id: UUID,
    _admin: dict = Depends(_require_content_read),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    res = (supabase.table("writing_prompt_targets").select("*")
           .eq("prompt_id", str(prompt_id)).order("created_at", desc=True).execute())
    items = [_enrich_target_labels(supabase, t) for t in (res.data or [])]
    return {"items": items}


@router.post("/writing-prompts/{prompt_id}/targets")
def propose_writing_prompt_target(
    prompt_id: UUID,
    body: WritingPromptTargetProposeBody,
    admin: dict = Depends(require_permission(PERM_ASSIGN)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """manage: propose an INERT pending_review assignment (§J2 authority split)."""
    supabase = get_supabase_admin()
    try:
        result = supabase.rpc("cms_propose_writing_prompt_target", {
            "p_prompt_id": str(prompt_id),
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
    target_id: UUID,
    body: WritingPromptTargetReviewBody,
    admin: dict = Depends(require_permission(PERM_ASSIGN_REVIEW)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """review: promote a pending_review assignment to effective active|excluded."""
    supabase = get_supabase_admin()
    try:
        result = supabase.rpc("cms_review_writing_prompt_target", {
            "p_target_id": str(target_id),
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
    target_id: UUID,
    body: _TargetRemoveBody,
    admin: dict = Depends(require_permission(PERM_ASSIGN_REVIEW)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """review: CAS-guarded removal of an assignment (audits the exact old row)."""
    supabase = get_supabase_admin()
    try:
        result = supabase.rpc("cms_remove_writing_prompt_target", {
            "p_target_id": str(target_id),
            "p_expected_updated_at": body.expected_updated_at,
            "p_reason": body.reason,
            "p_actor_user_id": admin.get("id"),
            "p_actor_email": admin.get("email"),
        }).execute()
    except Exception as exc:  # noqa: BLE001
        raise _map_rpc_error(exc, "remove_writing_prompt_target") from exc
    return {"ok": True, "result": _rpc_row(result)}


# ── Selector option lists (EWP-SP4 operator usability) ──────────────────────
#
# Read-only, permission-gated (_require_content_read) option feeds so the create/
# edit and assignment forms can offer readable, DEPENDENT selectors instead of
# raw-UUID text entry. These expose only {id, display label} tuples of canonical
# taxonomy / exam-scope rows — no aspirant-facing content — so the verified-only
# read rule (which governs learner content) does not apply here; they are the
# operator's own picker feeds under the Content Studio API source of truth.


@router.get("/taxonomy/subjects")
def list_subject_options(
    _admin: dict = Depends(_require_content_read),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    res = supabase.table("subjects").select("id,slug,name").order("name").execute()
    return {"items": res.data or []}


@router.get("/taxonomy/topics")
def list_topic_options(
    subject_id: UUID | None = Query(default=None),
    parent_topic_id: UUID | None = Query(default=None),
    level: str | None = Query(default=None, description="topic | microtopic | concept"),
    _admin: dict = Depends(_require_content_read),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Dependent taxonomy feed: topics filtered by subject (level=topic) or
    microtopics filtered by their parent topic (level=microtopic)."""
    supabase = get_supabase_admin()
    query = supabase.table("topics").select(
        "id,slug,name,level,subject_id,parent_topic_id").order("name")
    if subject_id is not None:
        query = query.eq("subject_id", str(subject_id))
    if parent_topic_id is not None:
        query = query.eq("parent_topic_id", str(parent_topic_id))
    if level is not None:
        query = query.eq("level", level)
    res = query.execute()
    return {"items": res.data or []}


@router.get("/exam-scope/families")
def list_exam_family_options(
    _admin: dict = Depends(_require_content_read),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    res = (supabase.table("exam_families").select("id,slug,name")
           .eq("is_active", True).order("name").execute())
    return {"items": res.data or []}


@router.get("/exam-scope/exams")
def list_exam_options(
    exam_family_id: UUID | None = Query(default=None),
    _admin: dict = Depends(_require_content_read),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Dependent feed: active exams, optionally narrowed to one exam family."""
    supabase = get_supabase_admin()
    query = (supabase.table("exams").select("id,slug,name,exam_family_id")
             .eq("is_active", True).order("name"))
    if exam_family_id is not None:
        query = query.eq("exam_family_id", str(exam_family_id))
    res = query.execute()
    return {"items": res.data or []}


@router.get("/exam-scope/phases")
def list_exam_phase_options(
    exam_id: UUID | None = Query(default=None),
    _admin: dict = Depends(_require_content_read),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Dependent feed: phases of one exam (exam_id required for a meaningful list)."""
    supabase = get_supabase_admin()
    query = (supabase.table("exam_phases").select("id,phase_name,exam_id,exam_cycle_id,status")
             .order("phase_name"))
    if exam_id is not None:
        query = query.eq("exam_id", str(exam_id))
    res = query.execute()
    return {"items": res.data or []}


@router.get("/rubrics")
def list_rubric_options(
    _admin: dict = Depends(_require_content_read),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    res = (supabase.table("writing_rubrics").select("id,name,version")
           .order("name").execute())
    return {"items": res.data or []}


@router.get("/source-documents")
def list_source_document_options(
    _admin: dict = Depends(_require_content_read),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Admin exam-intelligence documents that a prompt may cite as its source."""
    supabase = get_supabase_admin()
    res = (supabase.table("document_assets")
           .select("id,title,original_filename,document_kind")
           .eq("scope", "admin_exam_intelligence")
           .order("created_at", desc=True).limit(500).execute())
    return {"items": res.data or []}


@router.get("/writing-prompts/{prompt_id}/correction-note")
def get_writing_prompt_correction_note(
    prompt_id: UUID,
    _admin: dict = Depends(_require_content_read),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Author read-back of the LATEST reviewer correction note.

    Review decisions are audited in admin_audit_logs (the note is not stored on
    the prompt row). When a prompt sits in `needs_correction`, the author needs to
    see WHY: this returns the most recent status-transition audit whose new_value
    set reviewer_status='needs_correction', exposing the reviewer_notes + reason
    read-only. Returns {note: null} when there is none."""
    supabase = get_supabase_admin()
    try:
        res = (supabase.table("admin_audit_logs")
               .select("actor_email,new_value,notes,created_at")
               .eq("entity_type", "writing_prompt")
               .eq("entity_id", str(prompt_id))
               .eq("action", "writing_prompt_status_transition")
               .order("created_at", desc=True).limit(50).execute())
    except Exception:  # noqa: BLE001
        return {"note": None}
    for row in (res.data or []):
        new_value = row.get("new_value") or {}
        if isinstance(new_value, dict) and new_value.get("reviewer_status") == "needs_correction":
            return {"note": {
                "reviewer_notes": new_value.get("reviewer_notes"),
                "reason": new_value.get("reason") or row.get("notes"),
                "actor_email": row.get("actor_email"),
                "created_at": row.get("created_at"),
            }}
    return {"note": None}
