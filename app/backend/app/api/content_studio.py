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
from app.study_os.quant_heuristics import review_heuristic as _review_quant_heuristic
from app.study_os.reasoning_strategies import review_strategy as _review_reasoning_strategy
from app.study_os.writing_practice.deterministic import tokenize_words as _tokenize_words
from app.core.auth import get_current_user, require_permission
from app.core.permissions import (
    CONTENT_STUDIO_ACTIVATE,
    CONTENT_STUDIO_AUTHOR,
    CONTENT_STUDIO_REVIEW,
    EXAM_INTELLIGENCE_MANAGE,
    EXAM_INTELLIGENCE_REVIEW,
    MOCK_QUESTIONS_PUBLISH,
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
# Promotion of a CA candidate INTO the objective bank is a publish action — a
# higher-trust gate than the candidate approve/reject review step (content_studio.review).
PERM_PUBLISH = MOCK_QUESTIONS_PUBLISH

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
        "invalid_reason", "invalid_reviewer_notes", "invalid_scope",
        "bulk_locked_row", "target_effective_locked", "reserved_metadata_key",
        # CA review/promotion RPC tokens (GQR-G4, migration 249).
        "actor_required", "illegal_target_status", "illegal_transition",
        "reason_required_on_reopen", "candidate_not_approved", "event_not_active",
        "event_relevance_expired", "correct_option_not_resolved", "validation_not_passed",
        "empty_stem", "empty_explanation", "must_have_exactly_four_options",
        "duplicate_options", "no_linked_claim", "noncurrent_or_missing_claim",
        "no_resolvable_evidence", "sole_evidence_discovery_only",
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


# Mirror of ewp_validate_prompt_scope's source_document provenance predicate
# (migration 215). A picker must never offer a document the write RPC would
# reject with invalid_scope, so the feed replicates the exact check: scope,
# non-null valid document_kind, non-null status not in (failed, archived), and
# non-blank storage bucket + path.
_VALID_DOCUMENT_KINDS = frozenset(
    {"syllabus", "notification", "corrigendum", "pyq_paper", "answer_key", "other"}
)
_INVALID_DOCUMENT_STATUSES = frozenset({"failed", "archived"})


def _document_passes_provenance(doc: dict) -> bool:
    """Exact replica of ewp_validate_prompt_scope's source_document check."""
    if doc.get("scope") != "admin_exam_intelligence":
        return False
    kind = doc.get("document_kind")
    if kind is None or kind not in _VALID_DOCUMENT_KINDS:
        return False
    status = doc.get("status")
    if status is None or status in _INVALID_DOCUMENT_STATUSES:
        return False
    if not (doc.get("storage_bucket") or "").strip():
        return False
    if not (doc.get("storage_path") or "").strip():
        return False
    return True


def _batch_name_map(supabase, table: str, ids, field: str = "name") -> dict:
    """One SELECT resolving id → label for a set of ids (no N+1)."""
    uniq = sorted({str(i) for i in ids if i})
    if not uniq:
        return {}
    res = supabase.table(table).select(f"id,{field}").in_("id", uniq).execute()
    return {r.get("id"): r.get(field) for r in (res.data or [])}


def _enrich_prompt_labels_batch(supabase, items: list) -> list:
    """Attach *_name/*_title display labels to a PAGE of writing_prompts rows,
    resolving each taxonomy/provenance table in a SINGLE batched query (distinct
    ids across the page) — never per-row. Ids are never mutated."""
    rows = [p for p in (items or []) if isinstance(p, dict)]
    if not rows:
        return items
    subjects = _batch_name_map(supabase, "subjects", [p.get("subject_id") for p in rows])
    topics = _batch_name_map(
        supabase, "topics",
        [p.get("topic_id") for p in rows] + [p.get("microtopic_id") for p in rows])
    rubrics = _batch_name_map(supabase, "writing_rubrics", [p.get("rubric_id") for p in rows])
    doc_ids = sorted({str(p.get("source_document_id")) for p in rows if p.get("source_document_id")})
    docs: dict = {}
    if doc_ids:
        res = (supabase.table("document_assets")
               .select("id,title,original_filename").in_("id", doc_ids).execute())
        docs = {r.get("id"): (r.get("title") or r.get("original_filename")) for r in (res.data or [])}
    for p in rows:
        sid, tid, mid = p.get("subject_id"), p.get("topic_id"), p.get("microtopic_id")
        rid, did = p.get("rubric_id"), p.get("source_document_id")
        p["subject_name"] = subjects.get(str(sid)) if sid else None
        p["topic_name"] = topics.get(str(tid)) if tid else None
        p["microtopic_name"] = topics.get(str(mid)) if mid else None
        p["rubric_name"] = rubrics.get(str(rid)) if rid else None
        p["source_document_title"] = docs.get(str(did)) if did else None
    return items


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
    items = _enrich_prompt_labels_batch(supabase, res.data or [])
    return {"items": items, "total": getattr(res, "count", None), "limit": limit, "offset": offset}


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


# Bound every option feed so a runaway taxonomy/registry can never return an
# unbounded page to the operator's picker.
_OPTION_LIMIT = 500


@router.get("/taxonomy/subjects")
def list_subject_options(
    _admin: dict = Depends(_require_content_read),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Writing-prompt subject feed. HARD-SCOPED to the single subject the write
    validator (ewp_validate_prompt_scope) accepts — the ACTIVE `english-language`
    subject — so the picker can never offer a subject create/verify would reject
    with invalid_scope."""
    supabase = get_supabase_admin()
    res = (supabase.table("subjects").select("id,slug,name")
           .eq("slug", "english-language").eq("is_active", True)
           .order("name").limit(_OPTION_LIMIT).execute())
    return {"items": res.data or []}


@router.get("/taxonomy/topics")
def list_topic_options(
    subject_id: UUID | None = Query(default=None),
    parent_topic_id: UUID | None = Query(default=None),
    level: str | None = Query(default=None, description="topic | microtopic | concept"),
    _admin: dict = Depends(_require_content_read),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Dependent taxonomy feed mirroring the write validator: only ACTIVE topics,
    scoped to a subject (topics) or a parent topic (microtopics). A parent filter
    is REQUIRED — an unfiltered call would return the whole tree, so it is a 422."""
    if subject_id is None and parent_topic_id is None:
        raise HTTPException(
            status_code=422,
            detail="taxonomy/topics requires subject_id (topics) or parent_topic_id (microtopics)")
    supabase = get_supabase_admin()
    query = (supabase.table("topics")
             .select("id,slug,name,level,subject_id,parent_topic_id,is_active")
             .eq("is_active", True).order("name").limit(_OPTION_LIMIT))
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
           .eq("is_active", True).order("name").limit(_OPTION_LIMIT).execute())
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
             .eq("is_active", True).order("name").limit(_OPTION_LIMIT))
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
    """Dependent feed: phases of one exam. exam_id is REQUIRED — an unfiltered
    call would return every phase in the registry, so it is a 422."""
    if exam_id is None:
        raise HTTPException(status_code=422, detail="exam-scope/phases requires exam_id")
    supabase = get_supabase_admin()
    res = (supabase.table("exam_phases").select("id,phase_name,exam_id,exam_cycle_id,status")
           .eq("exam_id", str(exam_id)).order("phase_name").limit(_OPTION_LIMIT).execute())
    return {"items": res.data or []}


@router.get("/rubrics")
def list_rubric_options(
    _admin: dict = Depends(_require_content_read),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    res = (supabase.table("writing_rubrics").select("id,name,version")
           .order("name").limit(_OPTION_LIMIT).execute())
    return {"items": res.data or []}


@router.get("/source-documents")
def list_source_document_options(
    _admin: dict = Depends(_require_content_read),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Admin exam-intelligence documents that a prompt may cite as its source.

    Every returned row is guaranteed to PASS ewp_validate_prompt_scope's
    provenance check (mirrored in `_document_passes_provenance`): valid
    document_kind, live status (not failed/archived), and non-blank storage
    bucket + path. The kind allowlist is pushed to the query; the null/blank
    guards are applied in Python to match the RPC's `btrim` semantics exactly.

    All filterable provenance clauses (scope, kind allowlist, non-null status,
    status not in failed/archived, non-null + non-empty storage bucket/path) are
    pushed into the query so the `limit` window can never hide older valid
    documents behind newer invalid ones; the Python guard only adds the
    whitespace-only (`btrim`) edge the SQL layer can't express."""
    supabase = get_supabase_admin()
    res = (supabase.table("document_assets")
           .select("id,title,original_filename,document_kind,scope,status,"
                   "storage_bucket,storage_path")
           .eq("scope", "admin_exam_intelligence")
           .in_("document_kind", sorted(_VALID_DOCUMENT_KINDS))
           .not_.is_("status", "null")
           .not_.in_("status", sorted(_INVALID_DOCUMENT_STATUSES))
           .not_.is_("storage_bucket", "null").neq("storage_bucket", "")
           .not_.is_("storage_path", "null").neq("storage_path", "")
           .order("created_at", desc=True).limit(_OPTION_LIMIT).execute())
    items = [
        {"id": d.get("id"), "title": d.get("title"),
         "original_filename": d.get("original_filename"),
         "document_kind": d.get("document_kind")}
        for d in (res.data or []) if _document_passes_provenance(d)
    ]
    return {"items": items}


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


# ── Quant heuristic authority (GQR-Q7) ──────────────────────────────────────
#
# quant_heuristics (migration 243; review RPC hardened in 245) are subject/topic-
# scoped canonical content governed here. The backend shipped read/selection + the
# review-lifecycle RPC (`cms_review_quant_heuristic`) ahead of the UI; this section
# is the operator API glue: a permission-gated Library read + the governance review
# transition (dual CAS on status + content updated_at, mandatory audit reason).
# There is NO create/edit/activate/assign path — migration 243 ships only the
# review RPC (heuristics carry no publication/applicability lane), so authoring
# is a later governed PR. Reads reuse the shared `_require_content_read` gate;
# reviewing is content_studio.review, exactly like writing prompts.
#
# The heuristic transition matrix (mirrored from migration 243) DIFFERS from the
# writing-prompt one: needs_correction routes back to pending (never straight to
# verified), a verified heuristic can only be reopened for correction, and a
# rejected heuristic can be reopened to pending for rework.
_QH_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "pending": ("verified", "rejected", "needs_correction"),
    "needs_correction": ("pending", "rejected"),
    "verified": ("needs_correction",),
    "rejected": ("pending",),
}
_QH_TARGET_STATUSES = frozenset(s for t in _QH_TRANSITIONS.values() for s in t)
_QH_TYPES = frozenset({"shortcut", "standard_method", "trap", "estimation"})


class QuantHeuristicReviewBody(BaseModel):
    """Review-lifecycle body for a quant heuristic.

    The RPC (`cms_review_quant_heuristic`, migration 246) CAS-guards on BOTH
    ``expected_status`` (the reviewer_status the client last saw) AND
    ``expected_updated_at`` (the content-revision token — so a reviewer can never
    verify a revision they did not read), requires an 8–500 char audit ``reason``
    on every decision, and requires ``reviewer_notes`` when reopening a verified
    heuristic for correction (enforced here AND in the RPC)."""
    model_config = ConfigDict(extra="forbid")
    status: str
    expected_status: str = Field(..., description="reviewer_status the client last saw (CAS)")
    expected_updated_at: str = Field(..., description="updated_at the client last read (content CAS token)")
    reason: str = Field(..., min_length=8, max_length=500)
    reviewer_notes: str | None = Field(default=None, max_length=2000)


def _enrich_heuristic_labels_batch(supabase, items: list) -> list:
    """Attach topic_name/microtopic_name to a PAGE of quant_heuristics rows in a
    single batched query (both columns reference `topics`); ids are never mutated."""
    rows = [h for h in (items or []) if isinstance(h, dict)]
    if not rows:
        return items
    topics = _batch_name_map(
        supabase, "topics",
        [h.get("topic_id") for h in rows] + [h.get("microtopic_id") for h in rows])
    for h in rows:
        tid, mid = h.get("topic_id"), h.get("microtopic_id")
        h["topic_name"] = topics.get(str(tid)) if tid else None
        h["microtopic_name"] = topics.get(str(mid)) if mid else None
    return items


@router.get("/quant-heuristics")
def list_quant_heuristics(
    topic_id: UUID | None = Query(default=None),
    microtopic_id: UUID | None = Query(default=None),
    heuristic_type: str | None = Query(default=None),
    reviewer_status: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    q: str | None = Query(default=None, description="substring match on name"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(_require_content_read),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    query = supabase.table("quant_heuristics").select("*", count="exact").order("created_at", desc=True)
    for col, val in (
        ("topic_id", topic_id), ("microtopic_id", microtopic_id),
        ("heuristic_type", heuristic_type), ("reviewer_status", reviewer_status),
    ):
        if val is not None:
            query = query.eq(col, str(val))
    if is_active is not None:
        query = query.eq("is_active", is_active)
    if q:
        query = query.ilike("name", f"%{q}%")
    res = query.range(offset, offset + limit - 1).execute()
    items = _enrich_heuristic_labels_batch(supabase, res.data or [])
    return {"items": items, "total": getattr(res, "count", None), "limit": limit, "offset": offset}


@router.get("/quant-heuristics/{heuristic_id}")
def get_quant_heuristic(
    heuristic_id: UUID,
    _admin: dict = Depends(_require_content_read),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    heuristic = _safe_select(supabase, "quant_heuristics", id=str(heuristic_id))
    if not heuristic:
        raise HTTPException(status_code=404, detail="quant_heuristic not found")
    return _enrich_heuristic_labels_batch(supabase, [heuristic])[0]


@router.post("/quant-heuristics/{heuristic_id}/review")
def review_quant_heuristic(
    heuristic_id: UUID,
    body: QuantHeuristicReviewBody,
    admin: dict = Depends(require_permission(PERM_REVIEW)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    if body.status not in _QH_TARGET_STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {sorted(_QH_TARGET_STATUSES)}")
    # Guard the transition against the status the CLIENT actually saw; the RPC
    # re-checks expected_status under the row lock (CAS) and owns the audit row.
    if body.status not in _QH_TRANSITIONS.get(body.expected_status, ()):
        raise HTTPException(status_code=422, detail=(
            f"Transition '{body.expected_status}' → '{body.status}' is not allowed. "
            f"Allowed: {list(_QH_TRANSITIONS.get(body.expected_status, ()))}"))
    # Reopening a verified heuristic for correction must carry a note (mirrors the RPC).
    notes = (body.reviewer_notes or "").strip() or None
    if body.expected_status == "verified" and body.status == "needs_correction" and notes is None:
        raise HTTPException(
            status_code=422,
            detail="reviewer_notes required when reopening a verified heuristic")
    supabase = get_supabase_admin()
    try:
        result = _review_quant_heuristic(
            supabase,
            heuristic_id=str(heuristic_id),
            expected_status=body.expected_status,
            # CLIENT's content token — never a server-minted fresh read — so a
            # content edit after the reviewer's read loses with 409.
            expected_updated_at=body.expected_updated_at,
            new_status=body.status,
            reviewer_notes=notes,
            reason=body.reason,
            actor_user_id=admin.get("id"),
            actor_email=admin.get("email"),
        )
    except Exception as exc:  # noqa: BLE001
        raise _map_rpc_error(exc, "review_quant_heuristic") from exc
    return {"ok": True, "result": result}


# ── Reasoning strategy authority (GQR-S3) ───────────────────────────────────
#
# reasoning_strategies (migration 262) are the Reasoning-lane equivalent of quant
# heuristics: subject/topic-scoped canonical solving strategies governed here. This
# section is the operator API glue — a permission-gated Library read + the
# governance review transition (dual CAS on status + content updated_at, mandatory
# audit reason), mirroring the quant-heuristic surface exactly. There is NO
# create/edit/activate/assign path in this PR (migration 262 ships only the review
# RPC — authoring is a later governed slice, exactly as GQR-Q7 deferred quant
# authoring). Reads reuse the shared `_require_content_read` gate; reviewing is
# content_studio.review. GQR-S3 stops before learner delivery; the batched
# projection is GQR-S4.
#
# The transition matrix (mirrored from migration 262) matches the heuristic one:
# needs_correction routes back to pending (never straight to verified), a verified
# strategy can only be reopened for correction, and a rejected strategy can be
# reopened to pending for rework.
_RS_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "pending": ("verified", "rejected", "needs_correction"),
    "needs_correction": ("pending", "rejected"),
    "verified": ("needs_correction",),
    "rejected": ("pending",),
}
_RS_TARGET_STATUSES = frozenset(s for t in _RS_TRANSITIONS.values() for s in t)
_RS_TYPES = frozenset({"approach", "pattern", "elimination", "diagram_method", "set_method", "trap"})


class ReasoningStrategyReviewBody(BaseModel):
    """Review-lifecycle body for a reasoning strategy.

    The RPC (`cms_review_reasoning_strategy`, migration 262) CAS-guards on BOTH
    ``expected_status`` (the reviewer_status the client last saw) AND
    ``expected_updated_at`` (the content-revision token — so a reviewer can never
    verify a revision they did not read), requires an 8–500 char audit ``reason``
    on every decision, and requires ``reviewer_notes`` when reopening a verified
    strategy for correction (enforced here AND in the RPC)."""
    model_config = ConfigDict(extra="forbid")
    status: str
    expected_status: str = Field(..., description="reviewer_status the client last saw (CAS)")
    expected_updated_at: str = Field(..., description="updated_at the client last read (content CAS token)")
    reason: str = Field(..., min_length=8, max_length=500)
    reviewer_notes: str | None = Field(default=None, max_length=2000)


def _enrich_strategy_labels_batch(supabase, items: list) -> list:
    """Attach topic_name/microtopic_name to a PAGE of reasoning_strategies rows in a
    single batched query (both columns reference `topics`); ids are never mutated."""
    rows = [s for s in (items or []) if isinstance(s, dict)]
    if not rows:
        return items
    topics = _batch_name_map(
        supabase, "topics",
        [s.get("topic_id") for s in rows] + [s.get("microtopic_id") for s in rows])
    for s in rows:
        tid, mid = s.get("topic_id"), s.get("microtopic_id")
        s["topic_name"] = topics.get(str(tid)) if tid else None
        s["microtopic_name"] = topics.get(str(mid)) if mid else None
    return items


@router.get("/reasoning-strategies")
def list_reasoning_strategies(
    topic_id: UUID | None = Query(default=None),
    microtopic_id: UUID | None = Query(default=None),
    strategy_type: str | None = Query(default=None),
    reviewer_status: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    q: str | None = Query(default=None, description="substring match on name"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(_require_content_read),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    query = supabase.table("reasoning_strategies").select("*", count="exact").order("created_at", desc=True)
    for col, val in (
        ("topic_id", topic_id), ("microtopic_id", microtopic_id),
        ("strategy_type", strategy_type), ("reviewer_status", reviewer_status),
    ):
        if val is not None:
            query = query.eq(col, str(val))
    if is_active is not None:
        query = query.eq("is_active", is_active)
    if q:
        query = query.ilike("name", f"%{q}%")
    res = query.range(offset, offset + limit - 1).execute()
    items = _enrich_strategy_labels_batch(supabase, res.data or [])
    return {"items": items, "total": getattr(res, "count", None), "limit": limit, "offset": offset}


@router.get("/reasoning-strategies/{strategy_id}")
def get_reasoning_strategy(
    strategy_id: UUID,
    _admin: dict = Depends(_require_content_read),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    strategy = _safe_select(supabase, "reasoning_strategies", id=str(strategy_id))
    if not strategy:
        raise HTTPException(status_code=404, detail="reasoning_strategy not found")
    return _enrich_strategy_labels_batch(supabase, [strategy])[0]


@router.post("/reasoning-strategies/{strategy_id}/review")
def review_reasoning_strategy(
    strategy_id: UUID,
    body: ReasoningStrategyReviewBody,
    admin: dict = Depends(require_permission(PERM_REVIEW)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    if body.status not in _RS_TARGET_STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {sorted(_RS_TARGET_STATUSES)}")
    # Guard the transition against the status the CLIENT actually saw; the RPC
    # re-checks expected_status under the row lock (CAS) and owns the audit row.
    if body.status not in _RS_TRANSITIONS.get(body.expected_status, ()):
        raise HTTPException(status_code=422, detail=(
            f"Transition '{body.expected_status}' → '{body.status}' is not allowed. "
            f"Allowed: {list(_RS_TRANSITIONS.get(body.expected_status, ()))}"))
    # Reopening a verified strategy for correction must carry a note (mirrors the RPC).
    notes = (body.reviewer_notes or "").strip() or None
    if body.expected_status == "verified" and body.status == "needs_correction" and notes is None:
        raise HTTPException(
            status_code=422,
            detail="reviewer_notes required when reopening a verified strategy")
    supabase = get_supabase_admin()
    try:
        result = _review_reasoning_strategy(
            supabase,
            strategy_id=str(strategy_id),
            expected_status=body.expected_status,
            # CLIENT's content token — never a server-minted fresh read — so a
            # content edit after the reviewer's read loses with 409.
            expected_updated_at=body.expected_updated_at,
            new_status=body.status,
            reviewer_notes=notes,
            reason=body.reason,
            actor_user_id=admin.get("id"),
            actor_email=admin.get("email"),
        )
    except Exception as exc:  # noqa: BLE001
        raise _map_rpc_error(exc, "review_reasoning_strategy") from exc
    return {"ok": True, "result": result}


# ── Current-affairs question candidates (GQR-G4a: operator review + promotion) ──
# The human gate (ADR 0006): a shadow-generated candidate becomes a bank question
# ONLY via an operator decision here. Reviewing (approve/reject/send-back) is
# `content_studio.review`; PROMOTION into the objective bank is the higher-trust
# `mock_questions:publish`. Both run through audited SECURITY DEFINER RPCs
# (`ca_review_candidate` / `ca_promote_candidate`, migration 248) that CAS-guard on
# the status the reviewer saw and own the admin_audit_logs entry. No new sidebar
# surface — this is a Content Studio content type (no-new-surface rule).
_CA_REVIEW_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "review_ready": ("approved", "rejected"),
    "approved": ("rejected", "review_ready"),  # reject, or send back for rework
    "rejected": ("review_ready",),             # reopen
}
_CA_REVIEW_TARGETS = frozenset(s for t in _CA_REVIEW_TRANSITIONS.values() for s in t)


class CaCandidateReviewBody(BaseModel):
    """Approve / reject / send-back a CA question candidate. The RPC dual-CAS-guards
    on BOTH ``expected_status`` and ``expected_updated_at`` (the content-revision token
    the reviewer read — so a decision can never land on an unseen revision) and requires
    an 8-500 char audit ``reason`` (mirrors the quant-heuristic review contract)."""
    model_config = ConfigDict(extra="forbid")
    status: str
    expected_status: str = Field(..., description="candidate status the client last saw (CAS)")
    expected_updated_at: str = Field(..., description="candidate updated_at the client read (content CAS)")
    reason: str = Field(..., min_length=8, max_length=500)
    reviewer_notes: str | None = Field(default=None, max_length=2000)


class CaCandidatePromoteBody(BaseModel):
    """Promote an APPROVED candidate into the objective bank as a current_event
    question. Dual-CAS on ``expected_status`` (must be ``approved``) + ``expected_updated_at``,
    with a mandatory audit ``reason``. The RPC revalidates the persisted Stage-D verdict +
    evidence integrity before writing the bank row."""
    model_config = ConfigDict(extra="forbid")
    expected_status: str = Field(default="approved", description="must be 'approved' (CAS)")
    expected_updated_at: str = Field(..., description="candidate updated_at the client read (content CAS)")
    reason: str = Field(..., min_length=8, max_length=500)


@router.get("/ca-question-candidates")
def list_ca_candidates(
    status: str | None = Query(default=None),
    event_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(_require_content_read),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    query = (
        supabase.table("current_affairs_question_candidates")
        .select("*", count="exact").order("created_at", desc=True)
    )
    if status is not None:
        query = query.eq("status", status)
    if event_id is not None:
        query = query.eq("event_id", str(event_id))
    res = query.range(offset, offset + limit - 1).execute()
    return {"items": res.data or [], "total": getattr(res, "count", None),
            "limit": limit, "offset": offset}


@router.get("/ca-question-candidates/{candidate_id}")
def get_ca_candidate(
    candidate_id: UUID,
    _admin: dict = Depends(_require_content_read),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    candidate = _safe_select(supabase, "current_affairs_question_candidates", id=str(candidate_id))
    if not candidate:
        raise HTTPException(status_code=404, detail="ca_question_candidate not found")
    return _build_ca_review_envelope(supabase, candidate)


def _build_ca_review_envelope(supabase, candidate: dict[str, Any]) -> dict[str, Any]:
    """Full Stage-E review context (checkpost #970 F2): the candidate, its event with
    editorial/relevance fields, the candidate-linked claims (from the payload's
    ``resolved_claim_ids``) each with its exact evidence spans + document/source
    metadata and authority level (ADR 0007), and the full generation audit lineage.
    CA evidence tables are service-role only, so the client cannot fetch this itself."""
    payload = candidate.get("question_payload") or {}
    event = _safe_select(supabase, "current_affairs_events", id=str(candidate.get("event_id")))

    resolved_ids = [str(c) for c in (payload.get("resolved_claim_ids") or []) if c]
    claims_out: list[dict[str, Any]] = []
    for cid in resolved_ids:
        claim = _safe_select(supabase, "current_affairs_claims", id=cid)
        if not claim:
            claims_out.append({"id": cid, "missing": True, "evidence": []})
            continue
        ev_rows = (
            supabase.table("current_affairs_claim_evidence").select("*").eq("claim_id", cid).execute().data
        ) or []
        evidence = []
        for ev in ev_rows:
            doc = _safe_select(supabase, "current_affairs_documents", id=str(ev.get("document_id")))
            src = _safe_select(supabase, "current_affairs_sources", id=str(doc.get("source_id"))) if doc else None
            evidence.append({
                "evidence_text": ev.get("evidence_text"),
                "start_offset": ev.get("start_offset"), "end_offset": ev.get("end_offset"),
                "evidence_role": ev.get("evidence_role"),
                "document": {"id": (doc or {}).get("id"), "title": (doc or {}).get("title"),
                             "source_url": (doc or {}).get("source_url"),
                             "published_at": (doc or {}).get("published_at")} if doc else None,
                "source": {"name": (src or {}).get("name"),
                           "authority_level": (src or {}).get("authority_level"),
                           "is_active": (src or {}).get("is_active")} if src else None,
            })
        claims_out.append({
            "id": claim.get("id"), "claim_text": claim.get("claim_text"),
            "factual_status": claim.get("factual_status"),
            "reviewer_status": claim.get("reviewer_status"), "evidence": evidence,
        })

    runs = (
        supabase.table("current_affairs_generation_runs").select("*")
        .eq("candidate_id", str(candidate.get("id"))).execute().data
    ) or []
    # ADR 0007 warning surfaced for the operator: no non-discovery_only active source.
    all_auth = [
        (e.get("source") or {}).get("authority_level")
        for c in claims_out for e in c.get("evidence", [])
    ]
    warnings: list[str] = []
    if resolved_ids and not any(a and a != "discovery_only" for a in all_auth):
        warnings.append("sole_evidence_discovery_only")
    if not resolved_ids:
        warnings.append("no_linked_claim")
    if not candidate.get("validation_result", {}).get("ok"):
        warnings.append("validation_failed")

    return {
        "candidate": candidate, "event": event, "claims": claims_out,
        "generation_runs": runs, "warnings": warnings,
    }


@router.post("/ca-question-candidates/{candidate_id}/review")
def review_ca_candidate(
    candidate_id: UUID,
    body: CaCandidateReviewBody,
    admin: dict = Depends(require_permission(PERM_REVIEW)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    if body.status not in _CA_REVIEW_TARGETS:
        raise HTTPException(status_code=422, detail=f"status must be one of {sorted(_CA_REVIEW_TARGETS)}")
    if body.status not in _CA_REVIEW_TRANSITIONS.get(body.expected_status, ()):
        raise HTTPException(status_code=422, detail=(
            f"Transition '{body.expected_status}' → '{body.status}' is not allowed. "
            f"Allowed: {list(_CA_REVIEW_TRANSITIONS.get(body.expected_status, ()))}"))
    notes = (body.reviewer_notes or "").strip() or None
    if body.expected_status == "approved" and body.status == "review_ready" and notes is None:
        raise HTTPException(status_code=422,
                            detail="reviewer_notes required when sending an approved candidate back")
    supabase = get_supabase_admin()
    try:
        result = supabase.rpc("ca_review_candidate", {
            "p_candidate_id": str(candidate_id),
            "p_expected_status": body.expected_status,
            "p_expected_updated_at": body.expected_updated_at,
            "p_new_status": body.status,
            "p_reason": body.reason,
            "p_reviewer_notes": notes,
            "p_actor_user_id": admin.get("id"),
            "p_actor_email": admin.get("email"),
        }).execute().data
    except Exception as exc:  # noqa: BLE001
        raise _map_rpc_error(exc, "review_ca_candidate") from exc
    return {"ok": True, "result": result}


@router.post("/ca-question-candidates/{candidate_id}/promote")
def promote_ca_candidate(
    candidate_id: UUID,
    body: CaCandidatePromoteBody,
    admin: dict = Depends(require_permission(PERM_PUBLISH)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    # Publish-gated human action: the RPC requires an approved candidate + a live,
    # unexpired event and writes the bank row as source_kind='current_event'. The
    # model/worker can never reach this path.
    supabase = get_supabase_admin()
    try:
        result = supabase.rpc("ca_promote_candidate", {
            "p_candidate_id": str(candidate_id),
            "p_expected_status": body.expected_status,
            "p_expected_updated_at": body.expected_updated_at,
            "p_reason": body.reason,
            "p_actor_user_id": admin.get("id"),
            "p_actor_email": admin.get("email"),
        }).execute().data
    except Exception as exc:  # noqa: BLE001
        raise _map_rpc_error(exc, "promote_ca_candidate") from exc
    return {"ok": True, "result": result}
