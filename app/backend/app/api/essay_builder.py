"""Essay Builder API — aspirant-facing (Idea Canvas + Spine).

Two surfaces, deliberately different trust models:

* ``/essay-brainstorm-blocks`` — **personal study content**. Every row is
  owned by the aspirant that created it (``essay_brainstorm_blocks.created_by``)
  and is only ever readable/writable by that aspirant. There is no admin
  review lifecycle on this table: these are the user's own canvas stickies,
  not shared source-of-truth content, so nothing here is gated on
  ``reviewer_status``.
* ``/essay-pyq-tags`` — **shared reference data**, read-only. The essay-theme
  tagging of real Essay-paper PYQs. Any authenticated aspirant may read it,
  and it obeys the project-wide verified-only invariant: rows surface only
  when the tag, its question, and that question's paper are all verified.

The admin authoring surface for essay themes and essay PYQ tags already
lives in ``app/api/admin_exam_intel_cms.py`` under
``/admin/exam-intelligence-cms/*`` behind ``exam_intelligence.cms``. That
router is permission- and flag-gated and is NOT the right home for
per-aspirant personal content, hence this separate module.

Ownership pattern matches ``app/api/reminders.py``: service-role client,
``created_by``-scoped filters on every read and write, and a shared 404 for
both "no such block" and "not yours" so existence never leaks.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.auth import (
    get_current_user,
    get_current_user_required_permanent,
)
from app.core.rate_limit import enforce as rate_limit_enforce
from app.db.supabase_client import get_supabase_admin

logger = logging.getLogger("career_copilot.api.essay_builder")

router = APIRouter(prefix="/essay-brainstorm-blocks", tags=["essay-builder"])
pyq_tags_router = APIRouter(prefix="/essay-pyq-tags", tags=["essay-builder"])

_TABLE = "essay_brainstorm_blocks"
_DEFAULT_LIMIT = 200
_MAX_LIMIT = 500
_MAX_TAG_LIMIT = 200
_BATCH = 250  # max ids per IN() filter (PostgREST URL-length ceiling)

_SELECT = (
    "id, theme_id, block_type, block_text, lens, linked_gs_topic_id, "
    "source_note, usage_count, created_by, metadata, created_at, updated_at"
)

# Mirrors migration 266's CHECK constraint. Spine stages come from migration
# 265; the last three are the Idea Canvas helper-rail resource types.
BlockType = Literal[
    "hook",
    "thesis",
    "argument_for",
    "argument_against",
    "example",
    "quote",
    "counter_narrative",
    "closing_thought",
    "vocab_term",
    "book_reference",
    "stat_to_verify",
]

# The six Idea Canvas mind-map branches, snake_cased from the labels the
# aspirant actually reads on the canvas. Null for Spine-stage blocks.
Lens = Literal[
    "economic_efficiency",         # "Economic Efficiency"
    "global_comparative",          # "Global & Comparative"
    "governance_implementation",   # "Governance & Implementation"
    "personal_onground",           # "Personal & On-ground"
    "social_equity_access",        # "Social Equity & Access"
    "historical_precedent",        # "Historical Precedent"
]

BLOCK_TYPES: tuple[str, ...] = tuple(BlockType.__args__)  # type: ignore[attr-defined]
LENSES: tuple[str, ...] = tuple(Lens.__args__)  # type: ignore[attr-defined]


class BlockCreate(BaseModel):
    theme_id: str
    block_type: BlockType
    block_text: str = Field(min_length=1, max_length=2000)
    lens: Lens | None = None
    linked_gs_topic_id: str | None = None


class BlockPatch(BaseModel):
    """Every field optional. ``exclude_unset`` distinguishes "not supplied"
    from an explicit ``null``, so a client can clear ``lens`` or
    ``linked_gs_topic_id`` by sending null without clearing the rest."""

    block_type: BlockType | None = None
    block_text: str | None = Field(default=None, min_length=1, max_length=2000)
    lens: Lens | None = None
    linked_gs_topic_id: str | None = None


def _is_uuid(value: Any) -> bool:
    try:
        UUID(str(value))
        return True
    except (TypeError, ValueError, AttributeError):
        return False


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _shape(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("id"),
        "theme_id": row.get("theme_id"),
        "block_type": row.get("block_type"),
        "block_text": row.get("block_text"),
        "lens": row.get("lens"),
        "linked_gs_topic_id": row.get("linked_gs_topic_id"),
        "source_note": row.get("source_note"),
        "usage_count": row.get("usage_count") or 0,
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def _row_exists(supabase: Any, table: str, row_id: str) -> bool:
    rows = (
        supabase.table(table)
        .select("id")
        .eq("id", row_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    return bool(rows)


def _require_theme(supabase: Any, theme_id: str) -> None:
    if not _is_uuid(theme_id):
        raise HTTPException(status_code=422, detail="theme_id must be a uuid")
    if not _row_exists(supabase, "essay_themes", theme_id):
        raise HTTPException(status_code=422, detail="Unknown theme_id")


def _require_topic(supabase: Any, topic_id: str) -> None:
    if not _is_uuid(topic_id):
        raise HTTPException(status_code=422, detail="linked_gs_topic_id must be a uuid")
    if not _row_exists(supabase, "topics", topic_id):
        raise HTTPException(status_code=422, detail="Unknown linked_gs_topic_id")


def _load_owned(supabase: Any, user_id: str, block_id: str) -> dict[str, Any]:
    """Return the block when owned by ``user_id``; 404 otherwise.

    "Not found" and "not yours" collapse into the same 404 so another
    aspirant's block id can never be probed for existence.
    """
    if not _is_uuid(block_id):
        raise HTTPException(status_code=404, detail="Brainstorm block not found")
    rows = (
        supabase.table(_TABLE)
        .select(_SELECT)
        .eq("id", block_id)
        .eq("created_by", user_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Brainstorm block not found")
    return rows[0]


def _chunks(items: list[Any], n: int) -> list[list[Any]]:
    return [items[i : i + n] for i in range(0, len(items), n)]


# ── Personal brainstorm blocks ─────────────────────────────────────────────


@router.get("")
def list_blocks(
    theme_id: str | None = Query(default=None),
    lens: str | None = Query(default=None),
    block_type: str | None = Query(default=None),
    limit: int = Query(default=_DEFAULT_LIMIT, ge=1, le=_MAX_LIMIT),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """The caller's own blocks, filterable by any combination of the three."""
    if lens is not None and lens not in LENSES:
        raise HTTPException(status_code=422, detail=f"lens must be one of {LENSES}")
    if block_type is not None and block_type not in BLOCK_TYPES:
        raise HTTPException(
            status_code=422, detail=f"block_type must be one of {BLOCK_TYPES}"
        )
    if theme_id is not None and not _is_uuid(theme_id):
        raise HTTPException(status_code=422, detail="theme_id must be a uuid")

    supabase = get_supabase_admin()
    query = supabase.table(_TABLE).select(_SELECT).eq("created_by", user["id"])
    if theme_id:
        query = query.eq("theme_id", theme_id)
    if lens:
        query = query.eq("lens", lens)
    if block_type:
        query = query.eq("block_type", block_type)
    rows = (
        query.order("created_at", desc=True).limit(limit).execute().data or []
    )
    return {"items": [_shape(r) for r in rows], "count": len(rows)}


@router.get("/{block_id}")
def get_block(
    block_id: str,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """One of the caller's own blocks. Another aspirant's id 404s — the read
    path enforces ownership rather than quietly returning nothing."""
    supabase = get_supabase_admin()
    return _shape(_load_owned(supabase, user["id"], block_id))


@router.post("")
def create_block(
    body: BlockCreate,
    user: dict = Depends(get_current_user_required_permanent),
) -> dict[str, Any]:
    rate_limit_enforce(user["id"], "essay_blocks.write")
    supabase = get_supabase_admin()
    _require_theme(supabase, body.theme_id)
    if body.linked_gs_topic_id:
        _require_topic(supabase, body.linked_gs_topic_id)

    payload = {
        "theme_id": body.theme_id,
        "block_type": body.block_type,
        "block_text": body.block_text,
        "lens": body.lens,
        "linked_gs_topic_id": body.linked_gs_topic_id,
        "created_by": user["id"],
    }
    rows = supabase.table(_TABLE).insert(payload).execute().data or []
    if not rows:
        raise HTTPException(status_code=500, detail="Insert failed")
    return _shape(rows[0])


@router.patch("/{block_id}")
def update_block(
    block_id: str,
    body: BlockPatch,
    user: dict = Depends(get_current_user_required_permanent),
) -> dict[str, Any]:
    rate_limit_enforce(user["id"], "essay_blocks.write")
    supabase = get_supabase_admin()
    existing = _load_owned(supabase, user["id"], block_id)

    patch = body.model_dump(exclude_unset=True)
    if not patch:
        raise HTTPException(status_code=422, detail="Nothing to update")
    # ``lens`` and ``linked_gs_topic_id`` are nullable columns, so an explicit
    # null clears them. ``block_type`` and ``block_text`` are NOT NULL — reject
    # an explicit null here rather than letting Postgres raise.
    for column in ("block_type", "block_text"):
        if column in patch and patch[column] is None:
            raise HTTPException(status_code=422, detail=f"{column} cannot be null")
    if patch.get("linked_gs_topic_id"):
        _require_topic(supabase, patch["linked_gs_topic_id"])
    patch["updated_at"] = _now_iso()

    rows = (
        supabase.table(_TABLE)
        .update(patch)
        .eq("id", block_id)
        .eq("created_by", user["id"])
        .execute()
        .data
        or []
    )
    return _shape(rows[0] if rows else {**existing, **patch})


@router.delete("/{block_id}")
def delete_block(
    block_id: str,
    user: dict = Depends(get_current_user_required_permanent),
) -> dict[str, Any]:
    rate_limit_enforce(user["id"], "essay_blocks.write")
    supabase = get_supabase_admin()
    _load_owned(supabase, user["id"], block_id)
    supabase.table(_TABLE).delete().eq("id", block_id).eq(
        "created_by", user["id"]
    ).execute()
    return {"ok": True, "id": block_id}


# ── Shared essay PYQ tags (read-only reference data) ───────────────────────


@pyq_tags_router.get("")
def list_essay_pyq_tags(
    theme_id: str | None = Query(default=None),
    limit: int = Query(default=_MAX_TAG_LIMIT, ge=1, le=_MAX_TAG_LIMIT),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Verified essay-theme tags on real Essay-paper PYQs.

    Shared reference data — no ownership scoping; any authenticated aspirant
    reads the same rows. Verified-only is enforced conjunctively: the tag,
    its question, and that question's paper must each be verified, so a
    pending or rejected tagging never reaches an aspirant. Returns an empty
    list cleanly when nothing has been promoted yet.
    """
    if theme_id is not None and not _is_uuid(theme_id):
        raise HTTPException(status_code=422, detail="theme_id must be a uuid")

    supabase = get_supabase_admin()
    query = (
        supabase.table("essay_pyq_tags")
        .select(
            "id, question_id, theme_id, secondary_theme_id, essay_type, "
            "quote_source_type, created_at"
        )
        .eq("reviewer_status", "verified")
    )
    if theme_id:
        query = query.eq("theme_id", theme_id)
    tags = query.order("created_at", desc=True).limit(limit).execute().data or []
    if not tags:
        return {"items": [], "count": 0}

    question_ids = list({t["question_id"] for t in tags if t.get("question_id")})
    questions: list[dict[str, Any]] = []
    for chunk in _chunks(question_ids, _BATCH):
        questions.extend(
            supabase.table("pyq_questions")
            .select("id, question_text, question_number, pyq_paper_id")
            .in_("id", chunk)
            .eq("reviewer_status", "verified")
            .execute()
            .data
            or []
        )
    by_qid = {q["id"]: q for q in questions}

    paper_ids = list({q["pyq_paper_id"] for q in questions if q.get("pyq_paper_id")})
    papers: list[dict[str, Any]] = []
    for chunk in _chunks(paper_ids, _BATCH):
        papers.extend(
            supabase.table("pyq_papers")
            .select("id, year")
            .in_("id", chunk)
            .eq("trust_status", "verified")
            .execute()
            .data
            or []
        )
    year_by_paper = {p["id"]: p.get("year") for p in papers}

    items: list[dict[str, Any]] = []
    for tag in tags:
        question = by_qid.get(tag.get("question_id"))
        if not question:
            continue  # question not verified -> tag does not surface
        paper_id = question.get("pyq_paper_id")
        if paper_id not in year_by_paper:
            continue  # paper not trust-verified -> tag does not surface
        items.append(
            {
                "id": tag.get("id"),
                "question_id": tag.get("question_id"),
                "theme_id": tag.get("theme_id"),
                "secondary_theme_id": tag.get("secondary_theme_id"),
                "essay_type": tag.get("essay_type"),
                "quote_source_type": tag.get("quote_source_type"),
                "question_text": question.get("question_text"),
                "question_number": question.get("question_number"),
                "year": year_by_paper.get(paper_id),
            }
        )
    return {"items": items, "count": len(items)}


__all__ = ["router", "pyq_tags_router", "BLOCK_TYPES", "LENSES"]
