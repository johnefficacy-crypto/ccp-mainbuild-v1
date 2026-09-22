"""Content Studio — answer structure review queue.

`/api/admin/content-studio/answer-structures`. Same authorities as the rest of
Content Studio (content_cards / writing prompts):

  reads      = content_studio.author OR review OR exam_intelligence.manage/review
  edit       = content_studio.author OR content_studio.review
               (a reviewer fixing a draft before approving it is the normal
               "edit-then-approve" path, not a separate authoring step)
  review     = content_studio.review
  regenerate = content_studio.author

Every write is an atomic SECURITY DEFINER RPC (migration 303) that CAS-guards on
the `updated_at` the operator read and writes its own `admin_audit_logs` row;
this layer is validation + permission + error mapping. Nothing here can make a
structure learner-visible except the review RPC's `verified` transition.
"""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from app.api.admin_exam_intel_cms import _flag_enabled, _safe_select
from app.api.content_studio import (
    PERM_AUTHOR,
    PERM_REVIEW,
    _map_rpc_error,
    _require_content_read,
    _rpc_row,
)
from app.core.auth import get_current_user, require_permission
from app.core.config import get_settings
from app.db.supabase_client import get_supabase_admin
from app.study_os import answer_structure_generation as gen
from app.study_os import descriptive as d
from app.study_os.answer_structure_schema import (
    CONTENT_FIELDS,
    EDITABLE_STATUSES,
    STATUSES,
    TRANSITIONS,
    StructureSchemaError,
    lint_structure,
    validate_structure,
)

logger = logging.getLogger("career_copilot.api.admin_answer_structures")

router = APIRouter(
    prefix="/admin/content-studio/answer-structures",
    tags=["admin-content-studio"],
)

_TABLE = "answer_structures"
_LIST_COLUMNS = "id, pyq_question_id, version, status, directive, generated_by, updated_at, reviewed_at"


def _require_editor(user: dict = Depends(get_current_user)) -> dict:
    if user.get("is_anonymous"):
        raise HTTPException(status_code=403, detail="Anonymous users cannot access this resource")
    if user.get("role") == "super_admin":
        return user
    if set(user.get("permissions") or []) & {PERM_AUTHOR, PERM_REVIEW}:
        return user
    raise HTTPException(status_code=403, detail="Missing permission: content_studio.author/review")


# ── list ─────────────────────────────────────────────────────────────────────


def _question_context(question: dict[str, Any] | None, paper: dict[str, Any] | None) -> dict[str, Any]:
    question = question or {}
    paper = paper or {}
    meta = d._meta(question)
    _, slot = d.paper_slot(paper)
    return {
        "id": question.get("id"),
        "excerpt": d._excerpt(question.get("question_text")),
        "subject": d.subject_of(question, paper),
        "paper": slot,
        "paper_code": d.paper_slot_code(paper),
        "year": d._as_int(paper.get("year")),
        "marks": d._as_int(meta.get("marks")),
        "word_limit": d._as_int(meta.get("word_limit")),
    }


@router.get("")
def list_answer_structures(
    status: str | None = Query(default=None, description="draft|in_review|verified|rejected"),
    subject: str | None = Query(default=None),
    paper: str | None = Query(default=None, description="paper slot code: GS1..GS4, ESSAY, P1, P2"),
    year: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(_require_content_read),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """The queue, filterable by subject / paper / year / status.

    Subject, paper and year live on the question and its paper, not on the
    structure, so the filter runs over the joined rows here. The queue is
    admin-only and bounded by the descriptive corpus (~12k questions), so one
    light read of the matching structures is acceptable; full rows are fetched
    only for the page shown.
    """
    if status is not None and status not in STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {list(STATUSES)}")
    supabase = get_supabase_admin()

    def _q(a: int, b: int):
        q = supabase.table(_TABLE).select(_LIST_COLUMNS).order("updated_at", desc=True)
        if status:
            q = q.eq("status", status)
        return q.range(a, b).execute().data

    rows = d._safe(lambda: d._paginate_all(_q), default=None)
    if rows is None:
        raise HTTPException(status_code=503, detail="The review queue is temporarily unavailable.")
    questions, papers = d._attempt_questions(
        supabase, [str(r["pyq_question_id"]) for r in rows if r.get("pyq_question_id")]
    )

    want_subject = (subject or "").strip().lower()
    want_paper = (paper or "").strip().upper()
    items = []
    facets: dict[str, set] = {"subjects": set(), "papers": set(), "years": set()}
    for r in rows:
        q = questions.get(str(r.get("pyq_question_id")))
        p = papers.get(str((q or {}).get("pyq_paper_id") or ""))
        ctx = _question_context(q, p)
        if ctx["subject"]:
            facets["subjects"].add(ctx["subject"])
        if ctx["paper_code"]:
            facets["papers"].add(ctx["paper_code"])
        if ctx["year"]:
            facets["years"].add(ctx["year"])
        if want_subject and (ctx["subject"] or "").lower() != want_subject:
            continue
        if want_paper and ctx["paper_code"] != want_paper:
            continue
        if year is not None and ctx["year"] != year:
            continue
        items.append({**r, "question": ctx})

    page = items[offset: offset + limit]
    return {
        "items": page,
        "total": len(items),
        "limit": limit,
        "offset": offset,
        "facets": {
            "subjects": sorted(facets["subjects"]),
            "papers": sorted(facets["papers"], key=lambda c: (d.slot_sort_key(c) or 0, c)),
            "years": sorted(facets["years"], reverse=True),
            "statuses": list(STATUSES),
        },
    }


# ── one structure, full ──────────────────────────────────────────────────────


def _audit_trail(supabase, structure_id: str) -> list[dict[str, Any]]:
    rows = d._safe(
        lambda: (
            supabase.table("admin_audit_logs")
            .select("id, actor_email, action, old_value, new_value, notes, created_at")
            .eq("entity_type", "answer_structure")
            .eq("entity_id", structure_id)
            .order("created_at", desc=True)
            .limit(100)
            .execute()
            .data
        ),
        default=[],
    ) or []
    return rows


@router.get("/{structure_id}")
def get_answer_structure(
    structure_id: UUID,
    _admin: dict = Depends(_require_content_read),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    row = _safe_select(supabase, _TABLE, id=str(structure_id))
    if not row:
        raise HTTPException(status_code=404, detail="answer_structure not found")
    qid = str(row.get("pyq_question_id"))
    questions, papers = d._attempt_questions(supabase, [qid])
    q = questions.get(qid) or {}
    p = papers.get(str(q.get("pyq_paper_id") or ""))
    versions = d._safe(
        lambda: (
            supabase.table(_TABLE)
            .select("id, version, status, updated_at")
            .eq("pyq_question_id", qid)
            .order("version", desc=True)
            .execute()
            .data
        ),
        default=[],
    ) or []
    return {
        "structure": row,
        "question": {**_question_context(q, p), "text": q.get("question_text") or ""},
        "versions": versions,
        "audit": _audit_trail(supabase, str(structure_id)),
        "allowed_transitions": list(TRANSITIONS.get(row.get("status") or "", ())),
        "editable": row.get("status") in EDITABLE_STATUSES,
    }


# ── edit ─────────────────────────────────────────────────────────────────────


class StructurePatchBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_updated_at: str = Field(..., description="updated_at the client last read (CAS)")
    reason: str = Field(..., min_length=8, max_length=500)
    payload: dict[str, Any]


@router.patch("/{structure_id}")
def update_answer_structure(
    structure_id: UUID,
    body: StructurePatchBody,
    admin: dict = Depends(_require_editor),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Edit any content field of a draft / in-review structure.

    The patch is merged onto the stored row and the RESULT is validated, so a
    reviewer cannot save a structure the schema would reject, and a partial
    patch cannot leave the row half-valid.
    """
    unknown = sorted(set(body.payload) - set(CONTENT_FIELDS))
    if unknown:
        raise HTTPException(status_code=422, detail=f"Not editable fields: {', '.join(unknown)}")
    supabase = get_supabase_admin()
    row = _safe_select(supabase, _TABLE, id=str(structure_id))
    if not row:
        raise HTTPException(status_code=404, detail="answer_structure not found")
    if row.get("status") not in EDITABLE_STATUSES:
        raise HTTPException(status_code=422, detail={
            "error": "structure_locked",
            "message": "Only draft or in-review structures can be edited. Reject it and regenerate instead.",
        })
    merged = {k: row.get(k) for k in CONTENT_FIELDS}
    merged.update(body.payload)
    try:
        normalised = validate_structure(merged)
    except StructureSchemaError as exc:
        raise HTTPException(status_code=422, detail={"error": "schema", "errors": exc.errors})
    patch = {k: normalised[k] for k in body.payload}
    try:
        result = supabase.rpc("cms_update_answer_structure", {
            "p_id": str(structure_id),
            "p_expected_updated_at": body.expected_updated_at,
            "p_patch": patch,
            "p_reason": body.reason,
            "p_actor_user_id": admin.get("id"),
            "p_actor_email": admin.get("email"),
        }).execute()
    except Exception as exc:  # noqa: BLE001
        raise _map_structure_error(exc, "update_answer_structure") from exc
    return {"ok": True, "result": _rpc_row(result), "lint_warnings": lint_structure(normalised)}


# ── review ───────────────────────────────────────────────────────────────────


class StructureReviewBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str
    expected_status: str
    expected_updated_at: str
    review_notes: str | None = Field(default=None, max_length=2000)


@router.post("/{structure_id}/review")
def review_answer_structure(
    structure_id: UUID,
    body: StructureReviewBody,
    admin: dict = Depends(require_permission(PERM_REVIEW)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    if body.status not in TRANSITIONS.get(body.expected_status, ()):
        raise HTTPException(status_code=422, detail=(
            f"Transition '{body.expected_status}' → '{body.status}' is not allowed. "
            f"Allowed: {list(TRANSITIONS.get(body.expected_status, ()))}"))
    notes = (body.review_notes or "").strip() or None
    if body.status == "rejected" and notes is None:
        raise HTTPException(status_code=422, detail="review_notes required when rejecting")
    supabase = get_supabase_admin()
    try:
        result = supabase.rpc("cms_review_answer_structure", {
            "p_id": str(structure_id),
            "p_expected_status": body.expected_status,
            "p_expected_updated_at": body.expected_updated_at,
            "p_new_status": body.status,
            "p_review_notes": notes,
            "p_actor_user_id": admin.get("id"),
            "p_actor_email": admin.get("email"),
        }).execute()
    except Exception as exc:  # noqa: BLE001
        raise _map_structure_error(exc, "review_answer_structure") from exc
    return {"ok": True, "result": _rpc_row(result)}


# ── regenerate ───────────────────────────────────────────────────────────────


class StructureRegenerateBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(..., min_length=8, max_length=500)


@router.post("/{structure_id}/regenerate")
def regenerate_answer_structure(
    structure_id: UUID,
    body: StructureRegenerateBody,
    admin: dict = Depends(require_permission(PERM_AUTHOR)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Draft a NEW version for this structure's question. The old version is
    left exactly as it is — a verified one stays live until the new draft is
    reviewed and approved, which demotes it atomically."""
    supabase = get_supabase_admin()
    row = _safe_select(supabase, _TABLE, id=str(structure_id))
    if not row:
        raise HTTPException(status_code=404, detail="answer_structure not found")
    qid = str(row.get("pyq_question_id"))
    inputs = gen.question_inputs(supabase, [qid]).get(qid)
    if inputs is None:
        raise HTTPException(status_code=422, detail="The question is not a verified descriptive question.")
    model = gen.resolve_model()
    try:
        call = gen.AnthropicModelCall(model=model, api_key=get_settings().ANTHROPIC_API_KEY or None)
    except gen.FatalModelError as exc:
        raise HTTPException(status_code=503, detail=f"Generation is not configured: {exc}")
    # One question, one ceiling: a regenerate can never cost more than this.
    budget = gen.CostBudget(max_usd=1.00)
    result = gen.generate_one(inputs, call, model=model, budget=budget)
    if not result.ok:
        raise HTTPException(status_code=502, detail={"error": "generation_failed", "message": result.error})
    try:
        created = gen.write_draft(
            supabase, result, reason=body.reason,
            actor_user_id=admin.get("id"), actor_email=admin.get("email"),
        )
    except Exception as exc:  # noqa: BLE001
        raise _map_structure_error(exc, "regenerate_answer_structure") from exc
    return {"ok": True, "result": created, "cost_usd": result.cost_usd}


def _map_structure_error(exc: Exception, ctx: str) -> HTTPException:
    low = str(exc).lower()
    if "structure_locked" in low:
        return HTTPException(status_code=422, detail={
            "error": "structure_locked",
            "message": "Only draft or in-review structures can be edited."})
    if "invalid_review_notes" in low:
        return HTTPException(status_code=422, detail="review_notes required when rejecting")
    if "uq_answer_structures_one_verified" in low:
        return HTTPException(status_code=409, detail="Another version was verified at the same time. Re-fetch and retry.")
    return _map_rpc_error(exc, ctx)
