"""Exam Intelligence read API (PR5).

User-visible, authenticated, deterministic. Every response is built from
**verified-only** rows (``reviewer_status='verified'``). No AI. No
unreviewed claims. Returns empty payloads cleanly when nothing is
verified yet, so the frontend can render a neutral "not connected yet"
state.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.auth import get_current_user
from app.db.supabase_client import get_supabase_admin
from app.exam_intelligence.lookup import list_active_exams
from app.exam_intelligence.option_insights import option_insights
from app.exam_intelligence.status import exam_intelligence_summary
from app.exam_intelligence.trap_drill import (
    build_trap_drill,
    drill_streak,
    log_drill_attempts,
)
from app.study_os.trap_drill_shadow import record_trap_drill_shadow

logger = logging.getLogger("career_copilot.api.exam_intelligence")

router = APIRouter(prefix="/exam-intelligence", tags=["exam-intelligence"])


@router.get("/exams")
def list_exams(
    limit: int = Query(100, ge=1, le=200),
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    sb = get_supabase_admin()
    try:
        items = list_active_exams(sb, limit=limit)
    except Exception as exc:  # noqa: BLE001
        logger.warning("exam_intelligence list_exams failed: %s", exc)
        items = []
    return {"items": items, "count": len(items), "verified_only": True}


@router.get("/exams/{slug}")
def get_exam_summary(
    slug: str,
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    sb = get_supabase_admin()
    try:
        return exam_intelligence_summary(sb, slug)
    except Exception as exc:  # noqa: BLE001
        logger.exception("exam_intelligence summary failed for %s", slug)
        return {
            "exam": None,
            "available": False,
            "topics": [],
            "verified_pyq_counts": {},
            "verified_syllabus_mentions": 0,
            "competition_series": [],
            "cutoff_series": {},
            "vacancy_series": {"total": [], "by_category": {}},
            "pyq_papers": [],
            "difficulty_heatmap": {"buckets": ["easy", "medium", "hard", "unknown"], "rows": [], "verified_question_count": 0},
            "verified_only": True,
            "error": str(exc)[:200],
        }


@router.get("/exams/{slug}/booklist")
def get_exam_booklist(
    slug: str,
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Verified subjectwise booklist for an exam.

    Reads ``exam_subject_resources`` (verified-only), groups rows by
    subject ordered by ``subjects.name``, then ``priority_order`` within
    each subject.  When a row has a ``marketplace_resource_id`` it is
    echoed back so the frontend can link directly to the marketplace asset.
    Returns ``subjects=[]`` cleanly when nothing is verified yet.
    """
    sb = get_supabase_admin()
    try:
        exam_rows = (
            sb.table("exams").select("id, slug").eq("slug", slug).limit(1).execute().data
            or []
        )
        exam_row = exam_rows[0] if exam_rows else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("booklist exam lookup failed for %s: %s", slug, exc)
        exam_row = None

    if not exam_row or not exam_row.get("id"):
        return {"exam_id": None, "verified_only": True, "subjects": []}

    exam_id = exam_row["id"]
    try:
        rows = (
            sb.table("exam_subject_resources")
            .select(
                "id, subject_id, topic_id, resource_type, title, author, "
                "provider, url, marketplace_resource_id, priority_order, "
                "recommended_for, subjects(id, name, slug)"
            )
            .eq("exam_id", exam_id)
            .eq("reviewer_status", "verified")
            .order("priority_order")
            .execute()
            .data
            or []
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("booklist query failed for %s", slug)
        return {
            "exam_id": exam_id,
            "verified_only": True,
            "subjects": [],
            "error": str(exc)[:200],
        }

    # Group by subject, preserving subject order by name then priority_order.
    seen: dict[str, dict] = {}
    order: list[str] = []
    for row in rows:
        subj = row.get("subjects") or {}
        sid = row.get("subject_id") or subj.get("id") or ""
        if sid not in seen:
            seen[sid] = {
                "subject_id": sid,
                "subject_name": subj.get("name") or "",
                "subject_slug": subj.get("slug") or "",
                "resources": [],
            }
            order.append(sid)
        seen[sid]["resources"].append({
            "id": row.get("id"),
            "resource_type": row.get("resource_type"),
            "title": row.get("title"),
            "author": row.get("author"),
            "provider": row.get("provider"),
            "url": row.get("url"),
            "marketplace_resource_id": row.get("marketplace_resource_id"),
            "priority_order": row.get("priority_order"),
            "recommended_for": row.get("recommended_for"),
            "topic_id": row.get("topic_id"),
        })

    subjects = sorted(
        [seen[sid] for sid in order],
        key=lambda s: s["subject_name"].lower(),
    )
    return {"exam_id": exam_id, "verified_only": True, "subjects": subjects}


@router.get("/exams/{slug}/option-insights")
def get_option_insights(
    slug: str,
    topic_id: str | None = Query(None),
    limit: int = Query(8, ge=1, le=50),
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Aspirant-facing trap-awareness + elimination-heuristic tips.

    Reads the materialised option-analytics rollups for the exam (the
    admin recompute populates them). Returns clean, UI-shaped tips with
    server-rendered human-readable lines, so the frontend stays dumb.
    Returns gracefully empty payloads when no rollup data exists yet.
    """
    sb = get_supabase_admin()
    exam_row = None
    try:
        rows = (
            sb.table("exams").select("id, slug").eq("slug", slug).limit(1).execute().data
            or []
        )
        exam_row = rows[0] if rows else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("option_insights exam lookup failed for %s: %s", slug, exc)
    if not exam_row or not exam_row.get("id"):
        return {
            "exam_id": None,
            "topic_id": topic_id,
            "verified_only": True,
            "has_data": False,
            "recurring_distractors": [],
            "elimination_tips": [],
        }
    try:
        return option_insights(sb, exam_row["id"], topic_id=topic_id, limit=limit)
    except Exception as exc:  # noqa: BLE001
        logger.exception("option_insights compute failed for %s", slug)
        return {
            "exam_id": exam_row["id"],
            "topic_id": topic_id,
            "verified_only": True,
            "has_data": False,
            "recurring_distractors": [],
            "elimination_tips": [],
            "error": str(exc)[:200],
        }


@router.get("/exams/{slug}/pyqs")
def list_exam_pyqs(
    slug: str,
    year: int | None = Query(None, ge=1980, le=2100),
    phase: str | None = Query(None),
    subject_id: str | None = Query(None),
    topic_id: str | None = Query(None),
    difficulty: str | None = Query(None, pattern="^(easy|medium|hard|unknown)$"),
    source_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Browsable PYQ explorer — verified questions only, paginated.

    Filters: year, phase (slug), subject_id, topic_id, difficulty,
    source_type. All filters are optional and combinable. Returns
    question rows with their options and topic tags.
    """
    sb = get_supabase_admin()
    empty = {
        "exam_id": None,
        "items": [],
        "total": 0,
        "page": page,
        "page_size": page_size,
        "verified_only": True,
    }

    # Resolve exam
    try:
        rows = (
            sb.table("exams").select("id, slug").eq("slug", slug).limit(1).execute().data
            or []
        )
        exam_row = rows[0] if rows else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("pyqs exam lookup failed for %s: %s", slug, exc)
        return empty

    if not exam_row or not exam_row.get("id"):
        return empty

    exam_id = exam_row["id"]

    try:
        # 1. Get verified paper ids for this exam, optionally filtered by year/phase/source_type
        paper_q = (
            sb.table("pyq_papers")
            .select("id, year, shift, paper_code, paper_date, source_type, exam_phase_id")
            .eq("exam_id", exam_id)
            .eq("trust_status", "verified")
            .limit(2000)
        )
        if year is not None:
            paper_q = paper_q.eq("year", year)
        if source_type is not None:
            paper_q = paper_q.eq("source_type", source_type)

        paper_rows = paper_q.execute().data or []

        # Phase filter: resolve phase_id from slug
        if phase:
            phase_id_rows = (
                sb.table("exam_phases")
                .select("id")
                .eq("phase_slug", phase)
                .limit(1)
                .execute()
                .data
                or []
            )
            if phase_id_rows:
                phase_uuid = phase_id_rows[0]["id"]
                paper_rows = [p for p in paper_rows if p.get("exam_phase_id") == phase_uuid]
            else:
                paper_rows = []

        paper_ids = [p["id"] for p in paper_rows if p.get("id")]
        paper_meta = {p["id"]: p for p in paper_rows}

        if not paper_ids:
            return {**empty, "exam_id": exam_id}

        # 2. Get verified questions
        q_query = (
            sb.table("pyq_questions")
            .select(
                "id, pyq_paper_id, question_number, question_text, question_type, "
                "observed_difficulty, correct_option_id, explanation_text, reviewer_status"
            )
            .in_("pyq_paper_id", paper_ids)
            .eq("reviewer_status", "verified")
            .limit(10000)
        )
        if difficulty is not None:
            q_query = q_query.eq("observed_difficulty", difficulty)

        all_questions = q_query.execute().data or []

        # topic/subject filter — needs tag join
        if topic_id or subject_id:
            tag_rows = (
                sb.table("pyq_question_topic_tags")
                .select("question_id, topic_id")
                .in_("question_id", [q["id"] for q in all_questions])
                .eq("reviewer_status", "verified")
                .limit(50000)
                .execute()
                .data
                or []
            )
            if topic_id:
                keep_qids = {t["question_id"] for t in tag_rows if t.get("topic_id") == topic_id}
            else:
                # subject filter: find topics belonging to subject
                topic_ids_for_subject = set()
                if tag_rows:
                    all_topic_ids = list({t["topic_id"] for t in tag_rows if t.get("topic_id")})
                    t_rows = (
                        sb.table("topics")
                        .select("id, subject_id")
                        .in_("id", all_topic_ids)
                        .eq("subject_id", subject_id)
                        .limit(5000)
                        .execute()
                        .data
                        or []
                    )
                    topic_ids_for_subject = {t["id"] for t in t_rows}
                keep_qids = {t["question_id"] for t in tag_rows if t.get("topic_id") in topic_ids_for_subject}
            all_questions = [q for q in all_questions if q["id"] in keep_qids]

        # 3. Deterministic sort: paper year desc, question_number asc
        def _sort_key(q):
            paper = paper_meta.get(q.get("pyq_paper_id") or "", {})
            return (-(paper.get("year") or 0), q.get("question_number") or 0)

        all_questions.sort(key=_sort_key)

        total = len(all_questions)
        offset = (page - 1) * page_size
        page_questions = all_questions[offset : offset + page_size]

        if not page_questions:
            return {**empty, "exam_id": exam_id, "total": total}

        # 4. Fetch options for this page
        page_q_ids = [q["id"] for q in page_questions]
        option_rows = (
            sb.table("pyq_options")
            .select("id, question_id, option_label, option_text, is_correct")
            .in_("question_id", page_q_ids)
            .order("option_label")
            .limit(page_size * 10)
            .execute()
            .data
            or []
        )
        options_by_qid: dict[str, list[dict]] = {}
        for opt in option_rows:
            options_by_qid.setdefault(opt["question_id"], []).append(
                {
                    "id": opt["id"],
                    "label": opt["option_label"],
                    "text": opt["option_text"],
                    "is_correct": opt["is_correct"],
                }
            )

        # 5. Fetch topic tags for this page
        tag_rows2 = (
            sb.table("pyq_question_topic_tags")
            .select("question_id, topic_id, tag_role")
            .in_("question_id", page_q_ids)
            .eq("reviewer_status", "verified")
            .limit(page_size * 20)
            .execute()
            .data
            or []
        )
        tags_by_qid: dict[str, list[dict]] = {}
        for tag in tag_rows2:
            tags_by_qid.setdefault(tag["question_id"], []).append(
                {"topic_id": tag["topic_id"], "tag_role": tag["tag_role"]}
            )

        # 6. Shape output
        items = []
        for q in page_questions:
            paper = paper_meta.get(q.get("pyq_paper_id") or "", {})
            items.append(
                {
                    "id": q["id"],
                    "paper_id": q["pyq_paper_id"],
                    "paper_year": paper.get("year"),
                    "paper_date": paper.get("paper_date"),
                    "shift": paper.get("shift"),
                    "source_type": paper.get("source_type"),
                    "question_number": q.get("question_number"),
                    "question_text": q.get("question_text"),
                    "question_type": q.get("question_type"),
                    "difficulty": q.get("observed_difficulty"),
                    "explanation": q.get("explanation_text"),
                    "options": options_by_qid.get(q["id"], []),
                    "topic_tags": tags_by_qid.get(q["id"], []),
                }
            )

        return {
            "exam_id": exam_id,
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "verified_only": True,
        }

    except Exception as exc:  # noqa: BLE001
        logger.exception("pyqs list failed for %s", slug)
        return {**empty, "exam_id": exam_id, "error": str(exc)[:200]}


@router.get("/exams/{slug}/trap-drill")
def get_trap_drill(
    slug: str,
    topic_id: str | None = Query(None),
    size: int = Query(5, ge=1, le=15),
    seed: int | None = Query(None, ge=1, le=2**31 - 1),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Build a short MCQ drill skewed toward verified questions with
    known trap patterns.

    Returns ``questions=[]`` and pool-size counts when the exam has no
    verified questions yet, so the UI can render a neutral empty
    state. When ``seed`` is supplied the same shuffle is reproduced,
    powering the deep-link contract. The user's attempt history is
    consulted for adaptive ranking — missed questions float to the
    top, recently-aced ones sink. ``drill_seed`` is echoed back on
    every payload so the client can pin it into a sharable URL.
    """
    sb = get_supabase_admin()
    exam_row = None
    try:
        rows = (
            sb.table("exams").select("id, slug").eq("slug", slug).limit(1).execute().data
            or []
        )
        exam_row = rows[0] if rows else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("trap_drill exam lookup failed for %s: %s", slug, exc)
    if not exam_row or not exam_row.get("id"):
        return {
            "exam_id": None,
            "topic_id": topic_id,
            "verified_only": True,
            "questions": [],
            "total_pool_size": 0,
            "trap_annotated_pool_size": 0,
            "drill_seed": seed,
            "adaptive": False,
            "personalised_for_user": False,
        }
    try:
        return build_trap_drill(
            sb,
            exam_row["id"],
            topic_id=topic_id,
            size=size,
            seed=seed,
            user_id=(user or {}).get("id"),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("trap_drill build failed for %s", slug)
        return {
            "exam_id": exam_row["id"],
            "topic_id": topic_id,
            "verified_only": True,
            "questions": [],
            "total_pool_size": 0,
            "trap_annotated_pool_size": 0,
            "drill_seed": seed,
            "adaptive": False,
            "personalised_for_user": False,
            "error": str(exc)[:200],
        }


class DrillAttempt(BaseModel):
    question_id: str
    is_correct: bool
    option_id: str | None = None
    topic_id: str | None = None


class DrillAttemptsBody(BaseModel):
    drill_seed: int | str | None = None
    attempts: list[DrillAttempt] = Field(default_factory=list)


@router.post("/exams/{slug}/trap-drill/attempts")
def post_trap_drill_attempts(
    slug: str,
    body: DrillAttemptsBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Persist one drill run as a batch of per-question attempts.

    Called from the modal when the drill reaches the summary screen.
    No-ops cleanly when the body has zero attempts (e.g. the user
    closed the modal mid-drill without answering anything) so the
    client can fire-and-forget. Returns the number of rows actually
    written plus how many were skipped because of bad shape.
    """
    sb = get_supabase_admin()
    exam_row = None
    try:
        rows = (
            sb.table("exams").select("id, slug").eq("slug", slug).limit(1).execute().data
            or []
        )
        exam_row = rows[0] if rows else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("trap_drill attempts exam lookup failed for %s: %s", slug, exc)
    if not exam_row or not exam_row.get("id"):
        raise HTTPException(status_code=404, detail="Unknown exam slug")
    if not body.attempts:
        return {"exam_id": exam_row["id"], "inserted": 0, "skipped": 0}
    user_id = (user or {}).get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = log_drill_attempts(
        sb,
        user_id=user_id,
        exam_id=exam_row["id"],
        attempts=[a.model_dump() for a in body.attempts],
        drill_seed=body.drill_seed,
    )
    # PR-8 (shadow only, gated behind FF_TRAP_DRILL_MASTERY_SHADOW): observe the
    # would-be mastery/revision for this drill session. Best-effort — never breaks
    # the drill-logging response, never writes live mastery.
    if result.get("inserted"):
        try:
            record_trap_drill_shadow(
                sb, user_id=user_id, exam_id=exam_row["id"], drill_seed=body.drill_seed
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("trap_drill shadow record failed: %s", exc)
    return {"exam_id": exam_row["id"], **result}


@router.get("/exams/{slug}/documents")
def get_exam_documents(
    slug: str,
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Return verified exam documents grouped by doc_type, deterministic order."""
    sb = get_supabase_admin()
    try:
        rows = (
            sb.table("exams").select("id, slug").eq("slug", slug).limit(1).execute().data
            or []
        )
        exam_row = rows[0] if rows else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("exam_documents exam lookup failed for %s: %s", slug, exc)
        exam_row = None
    if not exam_row or not exam_row.get("id"):
        return {
            "exam_id": None,
            "verified_only": True,
            "groups": {},
            "total": 0,
        }
    try:
        docs = (
            sb.table("exam_documents")
            .select("id, doc_type, title, url, cycle_year, valid_from, valid_until")
            .eq("exam_id", exam_row["id"])
            .in_("reviewer_status", ["reviewed", "locked"])
            .order("doc_type", desc=False)
            .order("cycle_year", desc=True, nullsfirst=False)
            .order("title", desc=False)
            .execute()
            .data
        ) or []
    except Exception as exc:  # noqa: BLE001
        logger.exception("exam_documents fetch failed for %s", slug)
        return {
            "exam_id": exam_row["id"],
            "verified_only": True,
            "groups": {},
            "total": 0,
            "error": str(exc)[:200],
        }
    groups: dict[str, list[dict[str, Any]]] = {}
    for d in docs:
        dt = d["doc_type"]
        groups.setdefault(dt, []).append(d)
    return {
        "exam_id": exam_row["id"],
        "verified_only": True,
        "groups": groups,
        "total": len(docs),
    }


@router.get("/exams/{slug}/trap-drill/streak")
def get_trap_drill_streak(
    slug: str,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Return the user's drill streak for this exam.

    Always returns a payload (zeros when there's nothing logged yet)
    so the UI can render a neutral empty state without an extra
    request-shape branch.
    """
    sb = get_supabase_admin()
    exam_row = None
    try:
        rows = (
            sb.table("exams").select("id, slug").eq("slug", slug).limit(1).execute().data
            or []
        )
        exam_row = rows[0] if rows else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("trap_drill streak exam lookup failed for %s: %s", slug, exc)
    user_id = (user or {}).get("id")
    if not user_id or not exam_row or not exam_row.get("id"):
        return {
            "exam_id": exam_row["id"] if exam_row else None,
            "current_streak_days": 0,
            "longest_streak_days": 0,
            "drills_this_week": 0,
            "total_attempts": 0,
            "last_attempt_at": None,
        }
    streak = drill_streak(sb, user_id=user_id, exam_id=exam_row["id"])
    return {"exam_id": exam_row["id"], **streak}
