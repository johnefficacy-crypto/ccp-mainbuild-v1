"""PYQ → Mock Bank projection service.

Thin Python orchestration layer that wraps the SECURITY DEFINER RPC
``project_pyq_question_to_mock_bank`` (migration 183).  All eligibility
checks and the atomic upsert live in the DB function; this module provides:

  - preview_paper_projection()   — dry-run: which questions would sync
  - sync_paper_projection()      — call the RPC per eligible question
  - get_paper_projection_status() — aggregated projection state for a paper

The RPC is the single source of truth.  Python never directly writes to
``pyq_mock_question_projections`` or ``mock_question_bank``.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any

logger = logging.getLogger("career_copilot.admin.pyq_mock_projection")


# ── Eligibility constants (mirrors the RPC — used for preview dry-run) ────────

_ELIGIBLE_Q_TYPES     = frozenset({"mcq"})
_VERIFIED_PAPER       = "verified"
_VERIFIED_QUESTION    = "verified"
_VERIFIED_OPTION      = "verified"
_VERIFIED_TAG         = "verified"
_PRIMARY_TAG_ROLE     = "primary"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _fetch_paper(sb: Any, paper_id: str) -> dict | None:
    rows = (
        sb.table("pyq_papers")
        .select("id, exam_id, year, trust_status")
        .eq("id", paper_id)
        .limit(1)
        .execute()
        .data
    ) or []
    return rows[0] if rows else None


def _fetch_paper_questions(sb: Any, paper_id: str) -> list[dict]:
    return (
        sb.table("pyq_questions")
        .select(
            "id, pyq_paper_id, question_text, question_type, reviewer_status, "
            "correct_option_id, observed_difficulty, expected_solve_time_sec"
        )
        .eq("pyq_paper_id", paper_id)
        .execute()
        .data
    ) or []


def _fetch_options_for_question(sb: Any, question_id: str) -> list[dict]:
    return (
        sb.table("pyq_options")
        .select("id, question_id, option_text, is_correct, reviewer_status")
        .eq("question_id", question_id)
        .execute()
        .data
    ) or []


def _fetch_primary_tags(sb: Any, question_id: str) -> list[dict]:
    return (
        sb.table("pyq_question_topic_tags")
        .select("id, question_id, topic_id, tag_role, reviewer_status")
        .eq("question_id", question_id)
        .eq("tag_role", _PRIMARY_TAG_ROLE)
        .execute()
        .data
    ) or []


def _fetch_existing_projection(sb: Any, question_id: str) -> dict | None:
    rows = (
        sb.table("pyq_mock_question_projections")
        .select("pyq_question_id, mock_question_id, sync_status, source_content_hash, projected_at, updated_at")
        .eq("pyq_question_id", question_id)
        .limit(1)
        .execute()
        .data
    ) or []
    return rows[0] if rows else None


def compute_content_hash(question: dict, options: list[dict]) -> str:
    """Stable SHA-256 hash of canonical content.

    Mirrors the hash computed inside ``project_pyq_question_to_mock_bank``
    (migration 183, Section D).  Keep in sync when the RPC hash formula changes.

    Formula: q_text NUL sorted_verified_opt_texts_joined_by_NUL NUL verified_correct_opt
    Only VERIFIED options are included so the hash tracks audited content only.
    """
    q_text = (question.get("question_text") or "").strip().lower()
    verified = [o for o in options if o.get("reviewer_status") == _VERIFIED_OPTION]
    opt_texts = sorted((o.get("option_text") or "").strip().lower() for o in verified)
    correct_opt = next(
        ((o.get("option_text") or "").strip().lower() for o in verified if o.get("is_correct")),
        "",
    )
    raw = q_text + "\x00" + "\x00".join(opt_texts) + "\x00" + correct_opt
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _check_question_eligibility(
    paper: dict,
    question: dict,
    options: list[dict],
    primary_tags: list[dict],
) -> tuple[bool, str]:
    """Return (eligible, reason) for a single question.

    Mirrors the eligibility checks in the SECURITY DEFINER RPC.
    """
    if paper.get("trust_status") != _VERIFIED_PAPER:
        return False, f"paper_not_verified:{paper.get('trust_status')}"

    if question.get("reviewer_status") != _VERIFIED_QUESTION:
        return False, f"question_not_verified:{question.get('reviewer_status')}"

    if question.get("question_type") not in _ELIGIBLE_Q_TYPES:
        return False, f"not_mcq:{question.get('question_type')}"

    if not (question.get("question_text") or "").strip():
        return False, "empty_question_text"

    verified_options = [o for o in options if o.get("reviewer_status") == _VERIFIED_OPTION]
    if len(verified_options) < 2:
        return False, f"too_few_verified_options:{len(verified_options)}"

    empty_text = [
        o for o in verified_options
        if not (o.get("option_text") or "").strip()
    ]
    if empty_text:
        return False, f"empty_verified_option_text:{len(empty_text)}"

    correct_options = [o for o in verified_options if o.get("is_correct")]
    if len(correct_options) != 1:
        return False, f"not_exactly_one_correct:{len(correct_options)}"

    correct_id = question.get("correct_option_id")
    if correct_id is not None and correct_options[0].get("id") != correct_id:
        return False, f"correct_option_id_mismatch:{correct_id}"

    verified_primary = [
        t for t in primary_tags
        if t.get("reviewer_status") == _VERIFIED_TAG
        and t.get("tag_role") == _PRIMARY_TAG_ROLE
    ]
    if len(verified_primary) != 1:
        return False, f"not_exactly_one_verified_primary_tag:{len(verified_primary)}"

    return True, "eligible"


# ── Public API ─────────────────────────────────────────────────────────────────

def preview_paper_projection(sb: Any, paper_id: str) -> dict:
    """Dry-run: assess projection eligibility for every question in a paper.

    Makes no writes.  Returns a per-question breakdown so the operator can
    see exactly which questions would project and which are blocked and why.

    Returns:
        {
          "paper_id": str,
          "paper": {id, exam_id, year, trust_status},
          "total": int,
          "eligible_count": int,
          "ineligible_count": int,
          "already_projected_count": int,
          "would_update_count": int,
          "would_create_count": int,
          "questions": [{question_id, eligible, reason, existing_projection, content_hash}]
        }
    """
    paper = _fetch_paper(sb, paper_id)
    if paper is None:
        raise LookupError(f"pyq paper {paper_id!r} not found")

    questions = _fetch_paper_questions(sb, paper_id)

    results: list[dict] = []
    eligible_count = 0
    already_projected = 0
    would_update = 0
    would_create = 0

    for q in questions:
        qid = q["id"]
        options    = _fetch_options_for_question(sb, qid)
        p_tags     = _fetch_primary_tags(sb, qid)
        projection = _fetch_existing_projection(sb, qid)

        eligible, reason = _check_question_eligibility(paper, q, options, p_tags)
        content_hash = compute_content_hash(q, options) if eligible else None

        entry: dict = {
            "question_id": qid,
            "eligible": eligible,
            "reason": reason,
            "existing_projection": projection,
            "content_hash": content_hash,
        }

        if eligible:
            eligible_count += 1
            if projection:
                already_projected += 1
                if projection.get("source_content_hash") != content_hash:
                    entry["would_update"] = True
                    would_update += 1
                else:
                    entry["would_update"] = False
            else:
                would_create += 1
        results.append(entry)

    return {
        "paper_id": paper_id,
        "paper": paper,
        "total": len(questions),
        "eligible_count": eligible_count,
        "ineligible_count": len(questions) - eligible_count,
        "already_projected_count": already_projected,
        "would_update_count": would_update,
        "would_create_count": would_create,
        "questions": results,
    }


def sync_paper_projection(
    sb: Any,
    paper_id: str,
    actor_id: str,
    *,
    audit_reason: str = "admin_sync",
    question_ids: list[str] | None = None,
) -> dict:
    """Call ``project_pyq_question_to_mock_bank`` for eligible questions.

    When ``question_ids`` is given, only those questions are synced (must
    belong to the paper).  Otherwise all questions in the paper are attempted.

    Returns:
        {
          "paper_id": str,
          "attempted": int,
          "outcomes": {
            "unchanged": int,
            "updated": int,
            "created": int,
            "ineligible": int,
            "error": int,
          },
          "questions": [{question_id, outcome, mock_question_id, detail}]
        }
    """
    paper = _fetch_paper(sb, paper_id)
    if paper is None:
        raise LookupError(f"pyq paper {paper_id!r} not found")

    questions = _fetch_paper_questions(sb, paper_id)
    if question_ids is not None:
        requested = set(question_ids)
        # Validate all requested IDs belong to this paper
        paper_qids = {q["id"] for q in questions}
        foreign = requested - paper_qids
        if foreign:
            raise ValueError(
                f"question_ids not in paper {paper_id!r}: {sorted(foreign)}"
            )
        questions = [q for q in questions if q["id"] in requested]

    results: list[dict] = []
    outcome_counts: dict[str, int] = {
        "unchanged": 0, "updated": 0, "created": 0, "ineligible": 0, "error": 0,
    }

    for q in questions:
        qid = q["id"]
        rpc_result = (
            sb.rpc(
                "project_pyq_question_to_mock_bank",
                {
                    "p_pyq_question_id": qid,
                    "p_actor_id": actor_id,
                    "p_audit_reason": audit_reason,
                },
            )
            .execute()
            .data
        )

        # RPC returns a JSONB record or list-of-one
        result_data: dict = {}
        if isinstance(rpc_result, list) and rpc_result:
            result_data = rpc_result[0] or {}
        elif isinstance(rpc_result, dict):
            result_data = rpc_result

        outcome = result_data.get("outcome", "error")
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
        results.append({
            "question_id": qid,
            "outcome": outcome,
            "mock_question_id": result_data.get("mock_question_id"),
            "detail": result_data,
        })

    return {
        "paper_id": paper_id,
        "attempted": len(questions),
        "outcomes": outcome_counts,
        "questions": results,
    }


def get_paper_projection_status(sb: Any, paper_id: str) -> dict:
    """Aggregated projection state for a paper.

    Returns counts by ``sync_status`` and lists any stale/blocked projections
    so the operator can see what needs attention without running a full preview.

    Returns:
        {
          "paper_id": str,
          "paper": {id, exam_id, year, trust_status},
          "total_questions": int,
          "projection_counts": {"active": N, "stale": N, "blocked": N, "archived": N},
          "unprojected_count": int,
          "stale_projections": [{pyq_question_id, mock_question_id, sync_status, updated_at}]
        }
    """
    paper = _fetch_paper(sb, paper_id)
    if paper is None:
        raise LookupError(f"pyq paper {paper_id!r} not found")

    questions = _fetch_paper_questions(sb, paper_id)
    question_ids = [q["id"] for q in questions]

    projections: list[dict] = []
    if question_ids:
        projections = (
            sb.table("pyq_mock_question_projections")
            .select("pyq_question_id, mock_question_id, sync_status, updated_at, last_sync_result")
            .in_("pyq_question_id", question_ids)
            .execute()
            .data
        ) or []

    projection_map = {p["pyq_question_id"]: p for p in projections}
    counts: dict[str, int] = {"active": 0, "stale": 0, "blocked": 0, "archived": 0}
    for p in projections:
        status = p.get("sync_status", "unknown")
        counts[status] = counts.get(status, 0) + 1

    unprojected = len(question_ids) - len(projections)
    stale = [p for p in projections if p.get("sync_status") in ("stale", "blocked")]

    return {
        "paper_id": paper_id,
        "paper": paper,
        "total_questions": len(questions),
        "projection_counts": counts,
        "unprojected_count": unprojected,
        "stale_projections": stale,
    }
