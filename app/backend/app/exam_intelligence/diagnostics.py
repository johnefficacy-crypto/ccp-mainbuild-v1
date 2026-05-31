"""Pure-read diagnostic helpers for operational hygiene.

find_orphan_questions  — pyq_questions with zero pyq_options children.
find_stuck_documents   — document_assets stuck in 'processing' > age_minutes.
find_stuck_text_extract_jobs — document_processing_jobs text_extract rows
                               stuck in 'running' > age_minutes.

All functions accept a Supabase admin client and return plain dicts.
No writes are performed here; action endpoints live in the API layer.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("career_copilot.exam_intelligence.diagnostics")


def find_orphan_questions(
    sb, *, exam_id: str | None = None, limit: int = 200
) -> list[dict]:
    """Return pyq_questions rows that have no corresponding pyq_options rows.

    Performs three cheap point-reads rather than a raw SQL NOT EXISTS so the
    logic works with the PostgREST / SBStub query interface.
    """
    paper_q = sb.table("pyq_papers").select("id, exam_id, year, exam_cycle_id")
    if exam_id:
        paper_q = paper_q.eq("exam_id", exam_id)
    papers = paper_q.execute().data or []
    paper_map: dict[str, dict] = {p["id"]: p for p in papers}
    if not paper_map:
        return []

    q_query = (
        sb.table("pyq_questions")
        .select("id, pyq_paper_id, question_number, created_at")
        .order("created_at", desc=True)
        .limit(limit)
    )
    if exam_id:
        q_query = q_query.in_("pyq_paper_id", list(paper_map.keys()))
    questions = q_query.execute().data or []
    if not questions:
        return []

    q_ids = [q["id"] for q in questions]
    opts = (
        sb.table("pyq_options")
        .select("question_id")
        .in_("question_id", q_ids)
        .execute()
        .data
        or []
    )
    has_options = {o["question_id"] for o in opts}

    result = []
    for q in questions:
        if q["id"] not in has_options:
            paper = paper_map.get(q.get("pyq_paper_id") or "", {})
            result.append(
                {
                    "id": q["id"],
                    "pyq_paper_id": q.get("pyq_paper_id"),
                    "question_number": q.get("question_number"),
                    "created_at": q.get("created_at"),
                    "exam_id": paper.get("exam_id"),
                    "year": paper.get("year"),
                    "exam_cycle_id": paper.get("exam_cycle_id"),
                }
            )
    return result


def find_stuck_documents(
    sb, *, age_minutes: int = 30, limit: int = 200
) -> list[dict]:
    """Return document_assets rows in 'processing' status older than age_minutes."""
    cutoff = (
        datetime.now(timezone.utc) - timedelta(minutes=age_minutes)
    ).isoformat()
    return (
        sb.table("document_assets")
        .select("id, status, updated_at, created_at")
        .eq("status", "processing")
        .lt("updated_at", cutoff)
        .limit(limit)
        .execute()
        .data
        or []
    )


def find_stuck_text_extract_jobs(
    sb, *, age_minutes: int = 30, limit: int = 200
) -> list[dict]:
    """Return document_processing_jobs text_extract rows stuck in 'running'."""
    cutoff = (
        datetime.now(timezone.utc) - timedelta(minutes=age_minutes)
    ).isoformat()
    return (
        sb.table("document_processing_jobs")
        .select("id, job_type, status, started_at, document_id, error_code, error_message")
        .eq("job_type", "text_extract")
        .eq("status", "running")
        .lt("started_at", cutoff)
        .limit(limit)
        .execute()
        .data
        or []
    )
