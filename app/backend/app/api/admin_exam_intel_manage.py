"""Admin Exam Intelligence — Manage Exam operational editors (J2-A).

This router surfaces *canonical operational editing* (topics + aliases)
inside the **Manage Exam** workspace, distinct from the Advanced Repair
CMS (``admin_exam_intel_cms``). Per the J2 gate
(``docs/status/Manage-Exam-Operational-Editors-Gate-2026-07-01.md`` §D):

- Every mutation is gated by ``exam_intelligence.manage`` — a single-token
  guard, NOT an OR of manage/cms. ``exam_intelligence.cms`` stays exclusive
  to Advanced Repair; ``exam_intelligence.review`` stays exclusive to
  trust/lifecycle transitions. ``super_admin`` bypasses (rule 1).
- Editing NEVER promotes reviewer_status / trust / coverage / activation;
  every write carries a reason and an audit record (rule 3).
- Verified/locked content is not silently editable: a topic with locked
  coverage must be reopened via ``review`` before ``manage`` may edit or
  delete it (rule 4).
- Destructive actions are bounded: a topic with aliases, locked coverage,
  or prerequisite edges returns 409 — forced cleanup belongs in Advanced
  Repair under ``exam_intelligence.cms`` (rule 5).
- ``manage`` is currently a global permission (no per-exam assignment
  model yet), so every endpoint enforces the requested ``exam_id`` and all
  parent-child relationships (subject ∈ exam, topic ∈ subject) server-side
  (rule / limitation D.3).

The editor reuses the exact table contracts and helpers of the CMS
module so the two surfaces cannot drift.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.admin_exam_intel_cms import (
    WriteEnvelope,
    _audit,
    _flag_enabled,
    _now_iso,
    _reject_unknown,
    _norm_alias,
    _safe_select,
    _TOPIC_ALIAS_FIELDS,
    _TOPIC_FIELDS,
    _TOPIC_LEVELS,
)
from app.core.auth import get_current_user, require_permission
from app.core.permissions import EXAM_INTELLIGENCE_MANAGE
from app.db.supabase_client import get_supabase_admin

logger = logging.getLogger("career_copilot.api.admin_exam_intel_manage")

router = APIRouter(
    prefix="/admin/exam-intelligence-manage",
    tags=["admin-exam-intelligence-manage"],
)

PERM_MANAGE = EXAM_INTELLIGENCE_MANAGE
PERM_REVIEW = "exam_intelligence.review"

# ── Prerequisite lifecycle (J2-A′ gate) ───────────────────────────────────
_PREREQ_FIELDS = {"topic_id", "prerequisite_topic_id", "relation_type", "strength", "source_basis"}
_PREREQ_RELATIONS = ("requires", "recommended_before", "supports", "foundation_for")
_ORDERING_RELATIONS = {"requires", "recommended_before"}
# States a manage-tier operator may edit/delete/submit from.
_MANAGE_EDITABLE = {"draft", "rejected"}
# Review-only lifecycle transitions (from, to). Everything else is 409.
_REVIEW_TRANSITIONS = {
    ("draft", "rejected"),
    ("pending_review", "reviewed"),
    ("pending_review", "rejected"),
    ("reviewed", "locked"),
    ("reviewed", "rejected"),
    ("reviewed", "draft"),
    ("locked", "reviewed"),  # reopen — requires review_notes
}


def _require_prereq_read(user: dict = Depends(get_current_user)) -> dict:
    """Read gate for prerequisite lists: existing admin/read access.

    A review-only operator MUST be able to load the rows they review, so this
    accepts manage OR review (super_admin bypasses) — gate §F blocker 2.
    """
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


def _require_prereq_scope(supabase, exam_id: str, topic_id: str, prerequisite_topic_id: str) -> None:
    """Both endpoints of an edge must belong to the exam's resolved subjects (PD-1)."""
    _require_topic_in_exam(supabase, exam_id, topic_id)
    _require_topic_in_exam(supabase, exam_id, prerequisite_topic_id)


def _rpc_row(res) -> dict:
    data = getattr(res, "data", None)
    if isinstance(data, list):
        return data[0] if data else {}
    return data or {}


# ─── Scope resolution (gate OD-4: coverage path) ──────────────────────────


def _exam_subject_ids(supabase, exam_id: str) -> set[str]:
    """Return the distinct subject ids the exam covers.

    Resolution path is the exam's declared coverage (OD-4):
    ``exam_topic_coverage(exam_id) → topics → distinct subject_id``.
    Never falls back to the global subject list (OD-5).
    """
    cov = (
        supabase.table("exam_topic_coverage")
        .select("topic_id")
        .eq("exam_id", exam_id)
        .execute()
        .data
        or []
    )
    topic_ids = sorted({r["topic_id"] for r in cov if r.get("topic_id")})
    if not topic_ids:
        return set()
    topics = (
        supabase.table("topics")
        .select("id, subject_id")
        .in_("id", topic_ids)
        .execute()
        .data
        or []
    )
    return {t["subject_id"] for t in topics if t.get("subject_id")}


def _require_subject_in_exam(supabase, exam_id: str, subject_id: str) -> None:
    if subject_id not in _exam_subject_ids(supabase, exam_id):
        raise HTTPException(
            status_code=422,
            detail="subject_id is not part of this exam's coverage",
        )


def _topic_has_locked_coverage(supabase, topic_id: str) -> bool:
    row = (
        supabase.table("exam_topic_coverage")
        .select("id")
        .eq("topic_id", topic_id)
        .eq("reviewer_status", "locked")
        .limit(1)
        .execute()
        .data
        or []
    )
    return bool(row)


def _topic_dependencies(supabase, topic_id: str) -> list[str]:
    """Return human-readable dependency labels blocking a topic delete.

    Covers every consumer that would either cascade-delete dependent rows
    or reject at the DB layer (ON DELETE RESTRICT), so the endpoint returns
    a clean 409 instead of silently cascading or 500-ing (gate rule 5):

    - child topics (``parent_topic_id`` is ON DELETE CASCADE — a delete here
      would silently remove the whole microtopic/concept subtree);
    - aliases, prerequisite edges (both directions), topic relation edges
      (all ON DELETE CASCADE);
    - exam coverage and syllabus evidence (ON DELETE RESTRICT);
    - PYQ question topic tags (ON DELETE RESTRICT — question-tagged topic).
    """
    blockers: list[str] = []
    if _safe_select(supabase, "topics", parent_topic_id=topic_id):
        blockers.append("child topics")
    if _safe_select(supabase, "topic_aliases", topic_id=topic_id):
        blockers.append("aliases")
    if _safe_select(supabase, "exam_topic_coverage", topic_id=topic_id):
        blockers.append("exam coverage")
    if _safe_select(supabase, "topic_prerequisites", topic_id=topic_id):
        blockers.append("prerequisite edges (as topic)")
    if _safe_select(supabase, "topic_prerequisites", prerequisite_topic_id=topic_id):
        blockers.append("prerequisite edges (as prerequisite)")
    if _safe_select(supabase, "pyq_question_topic_tags", topic_id=topic_id):
        blockers.append("PYQ question tags")
    if _safe_select(supabase, "syllabus_topic_mentions", topic_id=topic_id):
        blockers.append("syllabus mentions")
    if _safe_select(supabase, "topic_relation_edges", source_topic_id=topic_id):
        blockers.append("topic relation edges (as source)")
    if _safe_select(supabase, "topic_relation_edges", target_topic_id=topic_id):
        blockers.append("topic relation edges (as target)")
    return blockers


# ════════════════════════════════════════════════════════════════════════
#  Exam → subjects (scope resolver)
# ════════════════════════════════════════════════════════════════════════


@router.get("/exams/{exam_id}/subjects")
def list_exam_subjects(
    exam_id: str,
    _admin: dict = Depends(_require_prereq_read),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """List the subjects an exam covers (coverage path, OD-4).

    Empty coverage → empty list (OD-5): the caller shows an empty state
    and must NOT fall back to the global subject list.
    """
    supabase = get_supabase_admin()
    if not _safe_select(supabase, "exams", id=exam_id):
        raise HTTPException(status_code=404, detail="Exam not found")
    subject_ids = sorted(_exam_subject_ids(supabase, exam_id))
    if not subject_ids:
        return {"items": [], "total": 0}
    subjects = (
        supabase.table("subjects")
        .select("id, slug, name, subject_group, is_active")
        .in_("id", subject_ids)
        .order("name", desc=False)
        .execute()
        .data
        or []
    )
    return {"items": subjects, "total": len(subjects)}


# ════════════════════════════════════════════════════════════════════════
#  Topics (canonical operational editing)
# ════════════════════════════════════════════════════════════════════════


@router.get("/topics")
def list_topics(
    exam_id: str = Query(...),
    subject_id: str = Query(...),
    parent_topic_id: str | None = Query(default=None),
    level: str | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(_require_prereq_read),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    _require_subject_in_exam(supabase, exam_id, subject_id)
    query = (
        supabase.table("topics")
        .select(
            "id, subject_id, parent_topic_id, slug, name, level, "
            "default_difficulty_level, description, is_active, metadata, "
            "created_at, updated_at",
            count="exact",
        )
        .eq("subject_id", subject_id)
        .order("name", desc=False)
        .order("id", desc=False)
    )
    if parent_topic_id:
        query = query.eq("parent_topic_id", parent_topic_id)
    if level:
        query = query.eq("level", level)
    if q:
        query = query.ilike("name", f"%{q.strip()}%")
    res = query.range(offset, offset + limit - 1).execute()
    return {
        "items": res.data or [],
        "total": getattr(res, "count", None),
        "limit": limit,
        "offset": offset,
    }


@router.post("/topics")
def create_topic(
    body: WriteEnvelope,
    exam_id: str = Query(...),
    admin: dict = Depends(require_permission(PERM_MANAGE)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    _reject_unknown(body.payload, _TOPIC_FIELDS, "topics")
    row = {k: v for k, v in body.payload.items() if k in _TOPIC_FIELDS}
    if not row.get("subject_id") or not row.get("slug") or not row.get("name"):
        raise HTTPException(status_code=422, detail="subject_id, slug, name are required")
    if row.get("level") and row["level"] not in _TOPIC_LEVELS:
        raise HTTPException(status_code=422, detail=f"level must be one of {_TOPIC_LEVELS}")
    _require_subject_in_exam(supabase, exam_id, row["subject_id"])
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
    # Operational CREATE must not silently overwrite (no import/upsert
    # semantics): a natural-key collision would bypass the PATCH locked-
    # coverage guard yet be audited as a create. Probe explicitly and 409.
    # The DB unique index on (subject_id, parent_topic_id, slug) does NOT
    # catch top-level duplicates because NULL parent_topic_id is distinct in
    # a unique index, so the probe handles the NULL-parent case in code.
    candidates = (
        supabase.table("topics")
        .select("id, parent_topic_id")
        .eq("subject_id", row["subject_id"])
        .eq("slug", row["slug"])
        .execute()
        .data
        or []
    )
    if any((c.get("parent_topic_id") or None) == (parent_id or None) for c in candidates):
        raise HTTPException(
            status_code=409,
            detail="a topic with this (subject, parent, slug) already exists",
        )
    try:
        inserted = supabase.table("topics").insert(row).execute().data or []
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=409, detail=f"Insert failed: {exc}")
    new = inserted[0] if inserted else row
    audit_id = _audit(
        supabase, admin, "exam_intel.manage.topic.create",
        entity_type="topic", entity_id=new.get("id"),
        new_value={"reason": body.reason, "exam_id": exam_id, "row": new},
        notes="admin_exam_intel_manage",
    )
    return {"ok": True, "audit_id": audit_id, "row": new}


@router.patch("/topics/{topic_id}")
def update_topic(
    topic_id: str,
    body: WriteEnvelope,
    exam_id: str = Query(...),
    admin: dict = Depends(require_permission(PERM_MANAGE)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    existing = _safe_select(supabase, "topics", id=topic_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Topic not found")
    _require_subject_in_exam(supabase, exam_id, existing.get("subject_id"))
    _reject_unknown(body.payload, _TOPIC_FIELDS, "topics")
    patch = {k: v for k, v in body.payload.items() if k in _TOPIC_FIELDS}
    if not patch:
        raise HTTPException(status_code=422, detail="No allowed fields in payload")
    if patch.get("level") and patch["level"] not in _TOPIC_LEVELS:
        raise HTTPException(status_code=422, detail=f"level must be one of {_TOPIC_LEVELS}")
    # Rule 4: manage must not silently edit locked content. If the topic has
    # locked coverage, ANY canonical field change (including is_active
    # deactivation and default_difficulty_level) must go through review first —
    # a narrow identity-only guard would let a load-bearing topic be
    # deactivated or re-weighted out from under a locked/planner-ready row.
    if _topic_has_locked_coverage(supabase, topic_id):
        raise HTTPException(
            status_code=409,
            detail=(
                "topic has locked coverage; reopen it via review "
                "(exam_intelligence.review) before editing it with manage"
            ),
        )
    # Effective subject/parent integrity (OD-15). When subject_id changes but
    # parent_topic_id is not in the patch, the RETAINED parent must still
    # belong to the new subject — otherwise a move would strand a child under
    # a parent in the old subject. An explicit null clears the parent.
    target_subject = patch.get("subject_id", existing.get("subject_id"))
    if patch.get("subject_id"):
        _require_subject_in_exam(supabase, exam_id, patch["subject_id"])
    parent_in_patch = "parent_topic_id" in patch
    effective_parent = patch.get("parent_topic_id") if parent_in_patch else existing.get("parent_topic_id")
    if effective_parent:
        parent = _safe_select(supabase, "topics", id=effective_parent)
        if not parent:
            raise HTTPException(status_code=422, detail="parent_topic_id does not resolve")
        if parent.get("subject_id") != target_subject:
            raise HTTPException(
                status_code=422,
                detail=(
                    "parent_topic_id belongs to a different subject than the "
                    "target subject; clear or reassign the parent when moving subjects"
                ),
            )
    patch["updated_at"] = _now_iso()
    updated = supabase.table("topics").update(patch).eq("id", topic_id).execute().data or []
    audit_id = _audit(
        supabase, admin, "exam_intel.manage.topic.update",
        entity_type="topic", entity_id=topic_id,
        new_value={"reason": body.reason, "exam_id": exam_id, "patch": patch, "previous": existing},
        notes="admin_exam_intel_manage",
    )
    return {"ok": True, "audit_id": audit_id, "row": updated[0] if updated else existing | patch}


@router.delete("/topics/{topic_id}")
def delete_topic(
    topic_id: str,
    exam_id: str = Query(...),
    reason: str = Query(..., min_length=8, max_length=500),
    admin: dict = Depends(require_permission(PERM_MANAGE)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Bounded delete (rule 5). Blocked (409) when the topic has aliases,
    coverage, or prerequisite edges. Forced cleanup belongs in Advanced
    Repair under ``exam_intelligence.cms``."""
    supabase = get_supabase_admin()
    existing = _safe_select(supabase, "topics", id=topic_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Topic not found")
    _require_subject_in_exam(supabase, exam_id, existing.get("subject_id"))
    blockers = _topic_dependencies(supabase, topic_id)
    if blockers:
        raise HTTPException(
            status_code=409,
            detail=(
                "topic has dependencies (" + ", ".join(blockers) + "); "
                "resolve them or use Advanced Repair for forced cleanup"
            ),
        )
    # Safety net: any remaining ON DELETE RESTRICT consumer not enumerated
    # above must surface as a 409, never an unhandled 500.
    try:
        supabase.table("topics").delete().eq("id", topic_id).execute()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=409,
            detail=f"topic has remaining dependencies and cannot be deleted: {exc}",
        )
    audit_id = _audit(
        supabase, admin, "exam_intel.manage.topic.delete",
        entity_type="topic", entity_id=topic_id,
        new_value={"reason": reason, "exam_id": exam_id, "deleted": existing},
        notes="admin_exam_intel_manage",
    )
    return {"ok": True, "audit_id": audit_id, "id": topic_id}


# ════════════════════════════════════════════════════════════════════════
#  Topic aliases
# ════════════════════════════════════════════════════════════════════════


def _require_topic_in_exam(supabase, exam_id: str, topic_id: str) -> dict:
    topic = _safe_select(supabase, "topics", id=topic_id)
    if not topic:
        raise HTTPException(status_code=422, detail="topic_id does not resolve")
    _require_subject_in_exam(supabase, exam_id, topic.get("subject_id"))
    return topic


@router.get("/topic-aliases")
def list_topic_aliases(
    exam_id: str = Query(...),
    topic_id: str = Query(...),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(require_permission(PERM_MANAGE)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    _require_topic_in_exam(supabase, exam_id, topic_id)
    res = (
        supabase.table("topic_aliases")
        .select("id, topic_id, alias, normalized_alias, source_context, created_at", count="exact")
        .eq("topic_id", topic_id)
        .order("created_at", desc=True)
        .order("id", desc=False)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return {
        "items": res.data or [],
        "total": getattr(res, "count", None),
        "limit": limit,
        "offset": offset,
    }


@router.post("/topic-aliases")
def create_topic_alias(
    body: WriteEnvelope,
    exam_id: str = Query(...),
    admin: dict = Depends(require_permission(PERM_MANAGE)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    _reject_unknown(body.payload, _TOPIC_ALIAS_FIELDS, "topic_aliases")
    row = {k: v for k, v in body.payload.items() if k in _TOPIC_ALIAS_FIELDS}
    if not row.get("topic_id") or not row.get("alias"):
        raise HTTPException(status_code=422, detail="topic_id and alias are required")
    _require_topic_in_exam(supabase, exam_id, row["topic_id"])
    row["normalized_alias"] = _norm_alias(row["alias"])
    try:
        inserted = supabase.table("topic_aliases").insert(row).execute().data or []
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=409, detail=f"Insert failed: {exc}")
    new = inserted[0] if inserted else row
    audit_id = _audit(
        supabase, admin, "exam_intel.manage.topic_alias.create",
        entity_type="topic_alias", entity_id=new.get("id"),
        new_value={"reason": body.reason, "exam_id": exam_id, "row": new},
        notes="admin_exam_intel_manage",
    )
    return {"ok": True, "audit_id": audit_id, "row": new}


@router.delete("/topic-aliases/{alias_id}")
def delete_topic_alias(
    alias_id: str,
    exam_id: str = Query(...),
    reason: str = Query(..., min_length=8, max_length=500),
    admin: dict = Depends(require_permission(PERM_MANAGE)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    existing = _safe_select(supabase, "topic_aliases", id=alias_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Topic alias not found")
    _require_topic_in_exam(supabase, exam_id, existing.get("topic_id"))
    supabase.table("topic_aliases").delete().eq("id", alias_id).execute()
    audit_id = _audit(
        supabase, admin, "exam_intel.manage.topic_alias.delete",
        entity_type="topic_alias", entity_id=alias_id,
        new_value={"reason": reason, "exam_id": exam_id, "deleted": existing},
        notes="admin_exam_intel_manage",
    )
    return {"ok": True, "audit_id": audit_id, "id": alias_id}


# ════════════════════════════════════════════════════════════════════════
#  Topic prerequisites (J2-A′ — lifecycle + cycle-safe writes)
# ════════════════════════════════════════════════════════════════════════
#
# Every ordering-graph write (create + endpoint/relation-changing edit) goes
# through the cycle-safe RPC `cms_write_topic_prerequisite` (single global
# advisory lock + recursive cycle check). Lifecycle transitions are review-
# only except the manage submit handoff. See the J2-A′ gate §C/§E/§F.


class PrereqReviewEnvelope(BaseModel):
    reason: str = Field(..., min_length=8, max_length=500)
    target_status: str
    review_notes: str | None = None


@router.get("/topic-prerequisites")
def list_topic_prerequisites(
    exam_id: str = Query(...),
    topic_id: str = Query(...),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(_require_prereq_read),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """List prerequisite edges touching a topic, in BOTH directions (edges
    where the topic is the dependent AND edges where it is the prerequisite),
    per the gate's both-directional contract. Readable by manage OR review."""
    supabase = get_supabase_admin()
    _require_topic_in_exam(supabase, exam_id, topic_id)
    cols = (
        "id, topic_id, prerequisite_topic_id, relation_type, strength, "
        "source_basis, reviewer_status, reviewed_by, reviewed_at, "
        "review_notes, created_at, updated_at"
    )
    outgoing = (
        supabase.table("topic_prerequisites").select(cols).eq("topic_id", topic_id).execute().data
        or []
    )
    incoming = (
        supabase.table("topic_prerequisites").select(cols).eq("prerequisite_topic_id", topic_id).execute().data
        or []
    )
    merged = {r["id"]: r for r in [*outgoing, *incoming]}
    items = sorted(merged.values(), key=lambda r: (r.get("created_at") or "", r.get("id") or ""), reverse=True)
    total = len(items)
    page = items[offset:offset + limit]
    return {"items": page, "total": total, "limit": limit, "offset": offset}


@router.post("/topic-prerequisites")
def create_topic_prerequisite(
    body: WriteEnvelope,
    exam_id: str = Query(...),
    admin: dict = Depends(require_permission(PERM_MANAGE)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    _reject_unknown(body.payload, _PREREQ_FIELDS, "topic_prerequisites")
    row = {k: v for k, v in body.payload.items() if k in _PREREQ_FIELDS}
    topic_id = row.get("topic_id")
    prereq_id = row.get("prerequisite_topic_id")
    if not topic_id or not prereq_id:
        raise HTTPException(status_code=422, detail="topic_id and prerequisite_topic_id are required")
    relation = row.get("relation_type") or "requires"
    if relation not in _PREREQ_RELATIONS:
        raise HTTPException(status_code=422, detail=f"relation_type must be one of {_PREREQ_RELATIONS}")
    _require_prereq_scope(supabase, exam_id, topic_id, prereq_id)
    try:
        res = supabase.rpc(
            "cms_write_topic_prerequisite",
            {
                "p_id": None,
                "p_topic_id": topic_id,
                "p_prerequisite_topic_id": prereq_id,
                "p_relation_type": relation,
                "p_strength": row.get("strength", 1.0),
                "p_source_basis": row.get("source_basis"),
                "p_created_by": admin.get("id"),
                "p_metadata": None,
                "p_expected_status": None,
            },
        ).execute()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=409, detail=str(exc))
    new = _rpc_row(res)
    audit_id = _audit(
        supabase, admin, "exam_intel.manage.topic_prerequisite.create",
        entity_type="topic_prerequisite", entity_id=new.get("id"),
        new_value={"reason": body.reason, "exam_id": exam_id, "row": new},
        notes="admin_exam_intel_manage",
    )
    return {"ok": True, "audit_id": audit_id, "row": new}


@router.patch("/topic-prerequisites/{prereq_id}")
def update_topic_prerequisite(
    prereq_id: str,
    body: WriteEnvelope,
    exam_id: str = Query(...),
    admin: dict = Depends(require_permission(PERM_MANAGE)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    supabase = get_supabase_admin()
    existing = _safe_select(supabase, "topic_prerequisites", id=prereq_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Topic prerequisite not found")
    if existing.get("reviewer_status") not in _MANAGE_EDITABLE:
        raise HTTPException(
            status_code=409,
            detail="edge is not editable in its current review state; reopen via review first",
        )
    _reject_unknown(body.payload, _PREREQ_FIELDS, "topic_prerequisites")
    patch = {k: v for k, v in body.payload.items() if k in _PREREQ_FIELDS}
    if not patch:
        raise HTTPException(status_code=422, detail="No allowed fields in payload")
    relation = patch.get("relation_type", existing.get("relation_type"))
    if relation not in _PREREQ_RELATIONS:
        raise HTTPException(status_code=422, detail=f"relation_type must be one of {_PREREQ_RELATIONS}")
    topic_id = patch.get("topic_id", existing.get("topic_id"))
    prereq_topic = patch.get("prerequisite_topic_id", existing.get("prerequisite_topic_id"))
    _require_prereq_scope(supabase, exam_id, topic_id, prereq_topic)
    # The RPC re-runs the cycle check under the global lock — this covers both
    # endpoint changes and a relation promotion into the ordering set.
    try:
        res = supabase.rpc(
            "cms_write_topic_prerequisite",
            {
                "p_id": prereq_id,
                "p_topic_id": topic_id,
                "p_prerequisite_topic_id": prereq_topic,
                "p_relation_type": relation,
                "p_strength": patch.get("strength", existing.get("strength")),
                "p_source_basis": patch.get("source_basis", existing.get("source_basis")),
                "p_created_by": existing.get("created_by"),
                "p_metadata": None,
                # CAS: only update if the edge is still in the state we validated
                # AND has not been modified since we read it — blocks a concurrent
                # review/lock transition and a same-state lost update.
                "p_expected_status": existing.get("reviewer_status"),
                "p_expected_updated_at": existing.get("updated_at"),
            },
        ).execute()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=409, detail=str(exc))
    updated = _rpc_row(res)
    audit_id = _audit(
        supabase, admin, "exam_intel.manage.topic_prerequisite.update",
        entity_type="topic_prerequisite", entity_id=prereq_id,
        new_value={"reason": body.reason, "exam_id": exam_id, "patch": patch, "previous": existing},
        notes="admin_exam_intel_manage",
    )
    return {"ok": True, "audit_id": audit_id, "row": updated or (existing | patch)}


@router.post("/topic-prerequisites/{prereq_id}/submit")
def submit_topic_prerequisite(
    prereq_id: str,
    body: WriteEnvelope,
    exam_id: str = Query(...),
    admin: dict = Depends(require_permission(PERM_MANAGE)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Manage submit handoff: draft/rejected → pending_review (the sole
    non-trust lifecycle transition manage may perform)."""
    supabase = get_supabase_admin()
    existing = _safe_select(supabase, "topic_prerequisites", id=prereq_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Topic prerequisite not found")
    _require_prereq_scope(supabase, exam_id, existing.get("topic_id"), existing.get("prerequisite_topic_id"))
    if existing.get("reviewer_status") not in _MANAGE_EDITABLE:
        raise HTTPException(status_code=409, detail="only draft or rejected edges can be submitted")
    # CAS: the transition only lands if the edge is still draft/rejected, so a
    # concurrent review transition cannot be clobbered (last-write-wins).
    affected = (
        supabase.table("topic_prerequisites")
        .update({"reviewer_status": "pending_review", "updated_at": _now_iso()})
        .eq("id", prereq_id)
        .in_("reviewer_status", ["draft", "rejected"])
        .execute()
        .data
        or []
    )
    if not affected:
        raise HTTPException(status_code=409, detail="edge changed review state concurrently; re-fetch and retry")
    audit_id = _audit(
        supabase, admin, "exam_intel.manage.topic_prerequisite.submit",
        entity_type="topic_prerequisite", entity_id=prereq_id,
        new_value={"reason": body.reason, "exam_id": exam_id, "from": existing.get("reviewer_status")},
        notes="admin_exam_intel_manage",
    )
    return {"ok": True, "audit_id": audit_id, "id": prereq_id, "reviewer_status": "pending_review"}


@router.post("/topic-prerequisites/{prereq_id}/review")
def review_topic_prerequisite(
    prereq_id: str,
    body: PrereqReviewEnvelope,
    exam_id: str = Query(...),
    admin: dict = Depends(require_permission(PERM_REVIEW)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Review-only lifecycle transitions (gate §C.2). Reopen requires notes."""
    supabase = get_supabase_admin()
    existing = _safe_select(supabase, "topic_prerequisites", id=prereq_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Topic prerequisite not found")
    _require_prereq_scope(supabase, exam_id, existing.get("topic_id"), existing.get("prerequisite_topic_id"))
    current = existing.get("reviewer_status")
    target = body.target_status
    if (current, target) not in _REVIEW_TRANSITIONS:
        raise HTTPException(status_code=409, detail=f"transition {current} -> {target} is not permitted")
    if (current, target) == ("locked", "reviewed") and not (body.review_notes or "").strip():
        raise HTTPException(status_code=422, detail="reopen (locked -> reviewed) requires review_notes")
    patch: dict[str, Any] = {
        "reviewer_status": target,
        "reviewed_by": admin.get("id"),
        "reviewed_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    if body.review_notes is not None:
        patch["review_notes"] = body.review_notes
    # CAS on the observed `current` state so two reviewers cannot both transition
    # from the same starting state (last-write-wins).
    affected = (
        supabase.table("topic_prerequisites")
        .update(patch)
        .eq("id", prereq_id)
        .eq("reviewer_status", current)
        .execute()
        .data
        or []
    )
    if not affected:
        raise HTTPException(status_code=409, detail="edge changed review state concurrently; re-fetch and retry")
    audit_id = _audit(
        supabase, admin, f"exam_intel.review.topic_prerequisite.{target}",
        entity_type="topic_prerequisite", entity_id=prereq_id,
        new_value={"reason": body.reason, "exam_id": exam_id, "from": current, "to": target,
                   "review_notes": body.review_notes},
        notes="admin_exam_intel_manage",
    )
    return {"ok": True, "audit_id": audit_id, "id": prereq_id, "reviewer_status": target}


@router.delete("/topic-prerequisites/{prereq_id}")
def delete_topic_prerequisite(
    prereq_id: str,
    exam_id: str = Query(...),
    reason: str = Query(..., min_length=8, max_length=500),
    admin: dict = Depends(require_permission(PERM_MANAGE)),
    __: None = Depends(_flag_enabled),
) -> dict[str, Any]:
    """Manage delete — only while draft/rejected. pending_review/reviewed/
    locked require a review-authority rollback first (gate C.3). Forced
    cleanup at any state remains Advanced Repair / exam_intelligence.cms."""
    supabase = get_supabase_admin()
    existing = _safe_select(supabase, "topic_prerequisites", id=prereq_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Topic prerequisite not found")
    _require_prereq_scope(supabase, exam_id, existing.get("topic_id"), existing.get("prerequisite_topic_id"))
    if existing.get("reviewer_status") not in _MANAGE_EDITABLE:
        raise HTTPException(
            status_code=409,
            detail="only draft/rejected edges can be deleted by manage; roll back via review first",
        )
    # CAS: only delete if still draft/rejected (a concurrent submit/review must
    # not be silently discarded).
    affected = (
        supabase.table("topic_prerequisites")
        .delete()
        .eq("id", prereq_id)
        .in_("reviewer_status", ["draft", "rejected"])
        .execute()
        .data
        or []
    )
    if not affected:
        raise HTTPException(status_code=409, detail="edge changed review state concurrently; re-fetch and retry")
    audit_id = _audit(
        supabase, admin, "exam_intel.manage.topic_prerequisite.delete",
        entity_type="topic_prerequisite", entity_id=prereq_id,
        new_value={"reason": reason, "exam_id": exam_id, "deleted": existing},
        notes="admin_exam_intel_manage",
    )
    return {"ok": True, "audit_id": audit_id, "id": prereq_id}
