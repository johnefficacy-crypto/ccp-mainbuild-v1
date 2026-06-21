"""Exam Workspace readiness compute (PR2).

compute_exam_workspace_readiness(sb, exam_id, cycle_id=None) -> dict

Returns the full readiness contract: overall score + 7 section details.
Pure read; no writes; no side effects.

CYCLE_ID SEMANTICS
  Exam-scoped sections (cycle_id ignored):
    setup          — exam_phases for exam_id
    syllabus_mapper — syllabus_topic_mentions for exam_id
    updates        — exam_policy_updates for exam_id

  Cycle-scoped sections (cycle_id filters when provided; else all cycles):
    documents      — document_processing_jobs (text_extract) for exam_id [+ cycle_id]
    pyq_workbench  — pyq_papers + pyq_questions for exam_id [+ cycle_id]
    competition    — exam_competition_metrics for exam_id [+ cycle_id]

  review_activate — derived rollup of the above 6 sections (weight=0).

SCORE
  score_percent = sum(section.score_percent * section.weight) / sum(weights)
  where section.score_percent: empty=0, partial=50, ready=80, locked=100
  review_activate excluded from score (weight=0).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger("career_copilot.exam_intelligence.readiness")

_STATUS_SCORE = {"empty": 0, "partial": 50, "ready": 80, "locked": 100}
_STALE_DAYS = 30


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe(call, default=None):
    try:
        return call()
    except Exception as exc:  # noqa: BLE001
        logger.warning("readiness read failed: %s", exc)
        return default


def _days_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


# ── section computers ─────────────────────────────────────────────────────────

def _setup(sb, exam_id: str) -> dict:
    rows = _safe(
        lambda: sb.table("exam_phases").select("id").eq("exam_id", exam_id).limit(500).execute().data,
        default=[],
    ) or []
    phase_count = len(rows)
    status = "ready" if phase_count >= 1 else "empty"
    blockers = [] if phase_count >= 1 else ["no phases defined"]
    return {
        "section": "setup",
        "label": "Setup",
        "status": status,
        "score_percent": _STATUS_SCORE[status],
        "weight": 1,
        "blockers": blockers,
        "counts": {"present": phase_count, "required": 1},
        "metrics": {"phase_count": phase_count},
    }


def load_doc_extraction_counts(sb, exam_id: str, cycle_id: str | None = None) -> dict:
    """Return extraction counts for admin_exam_intelligence docs owned by exam_id.

    Extraction status is sourced from document_processing_jobs (job_type='text_extract',
    latest job per asset). trust_status on syllabus_documents is a human-review gate,
    not an extraction signal (BUG-EI-2 final fix).

    document_assets has no exam_id column; ownership is stored in metadata JSONB
    by admin_exam_intel_documents.py at upload time.
    """
    # Fetch all admin EI assets; filter to exam (and optionally cycle) in Python
    # because document_assets.exam_id does not exist as a column.
    asset_rows = _safe(
        lambda: (
            sb.table("document_assets")
            .select("id, metadata")
            .eq("scope", "admin_exam_intelligence")
            .limit(2000)
            .execute()
            .data
        ),
        default=[],
    ) or []

    assets = [r for r in asset_rows if (r.get("metadata") or {}).get("exam_id") == exam_id]
    if cycle_id:
        assets = [r for r in assets if (r.get("metadata") or {}).get("exam_cycle_id") == cycle_id]

    total = len(assets)
    if total == 0:
        return {"total": 0, "extracted": 0, "pending": 0, "failed": 0, "not_started": 0}

    asset_ids = [r["id"] for r in assets]

    # Batch-load latest text_extract job per asset — no per-asset N+1 queries.
    all_jobs: list[dict] = []
    for i in range(0, len(asset_ids), 500):
        batch = asset_ids[i : i + 500]
        jobs = _safe(
            lambda b=batch: (
                sb.table("document_processing_jobs")
                .select("document_id, status, created_at")
                .in_("document_id", b)
                .eq("job_type", "text_extract")
                .limit(5000)
                .execute()
                .data
            ),
            default=[],
        ) or []
        all_jobs.extend(jobs)

    # Latest job per asset: sort ascending so the last entry wins on ties.
    latest: dict[str, str] = {}
    for j in sorted(all_jobs, key=lambda x: x.get("created_at") or ""):
        latest[j["document_id"]] = j["status"]

    extracted   = sum(1 for aid in asset_ids if latest.get(aid) == "succeeded")
    pending     = sum(1 for aid in asset_ids if latest.get(aid) in {"queued", "running"})
    failed      = sum(1 for aid in asset_ids if latest.get(aid) == "failed")
    not_started = sum(1 for aid in asset_ids if aid not in latest)

    return {
        "total": total,
        "extracted": extracted,
        "pending": pending,
        "failed": failed,
        "not_started": not_started,
    }


def _documents(sb, exam_id: str, cycle_id: str | None) -> dict:
    counts    = load_doc_extraction_counts(sb, exam_id, cycle_id)
    total     = counts["total"]
    extracted = counts["extracted"]
    pending   = counts["pending"]
    failed    = counts["failed"]

    if extracted >= 1:
        status = "ready"
    elif total >= 1:
        status = "partial"
    else:
        status = "empty"

    blockers = []
    if total == 0:
        blockers.append("no documents uploaded")
    elif pending > 0:
        blockers.append(f"extraction pending for {pending} document{'s' if pending != 1 else ''}")

    return {
        "section": "documents",
        "label": "Documents",
        "status": status,
        "score_percent": _STATUS_SCORE[status],
        "weight": 1,
        "blockers": blockers,
        "counts": {"present": extracted, "required": 1},
        "metrics": {"total": total, "extracted": extracted, "pending": pending, "failed": failed},
    }


def _syllabus_mapper(sb, exam_id: str) -> dict:
    rows = _safe(
        lambda: (
            sb.table("syllabus_topic_mentions")
            .select("id, reviewer_status")
            .eq("exam_id", exam_id)
            .limit(20000)
            .execute()
            .data
        ),
        default=[],
    ) or []
    total = len(rows)
    pending = sum(1 for r in rows if r.get("reviewer_status") in {"pending", "needs_correction"})
    verified = sum(1 for r in rows if r.get("reviewer_status") == "verified")
    locked = sum(1 for r in rows if r.get("reviewer_status") == "locked")

    if total == 0:
        status = "empty"
    elif locked == total:
        status = "locked"
    elif locked >= 1:
        status = "ready"
    else:
        status = "partial"

    blockers = []
    if pending > 0:
        blockers.append(f"{pending} mention{'s' if pending != 1 else ''} pending review")

    return {
        "section": "syllabus_mapper",
        "label": "Syllabus Mapper",
        "status": status,
        "score_percent": _STATUS_SCORE[status],
        "weight": 2,
        "blockers": blockers,
        "counts": {"present": locked + verified, "required": 1},
        "metrics": {"total": total, "pending": pending, "verified": verified, "locked": locked},
    }


def _topic_coverage_snapshot(sb, exam_id: str, cycle_id: str | None) -> dict:
    """Non-scoring snapshot of exam_topic_coverage row counts.

    Scoped to cycle_id when provided (mirrors documents/pyq/competition behaviour).
    Returns a plain dict (NOT a section dict) — never included in score.
    """
    q = sb.table("exam_topic_coverage").select("id, reviewer_status, is_high_yield").eq("exam_id", exam_id)
    if cycle_id:
        # Include both cycle-specific rows AND exam-level rows (exam_cycle_id IS NULL)
        q = q.or_(f"exam_cycle_id.eq.{cycle_id},exam_cycle_id.is.null")
    rows = _safe(lambda: q.limit(50000).execute().data, default=[]) or []
    total = len(rows)
    draft = sum(1 for r in rows if r.get("reviewer_status") == "draft")
    pending = sum(1 for r in rows if r.get("reviewer_status") == "pending_review")
    reviewed = sum(1 for r in rows if r.get("reviewer_status") == "reviewed")
    locked = sum(1 for r in rows if r.get("reviewer_status") == "locked")
    high_yield = sum(1 for r in rows if r.get("is_high_yield"))
    return {
        "total": total,
        "draft": draft,
        "pending": pending,
        "reviewed": reviewed,
        "locked": locked,
        "high_yield": high_yield,
    }


def _pyq_workbench(sb, exam_id: str, cycle_id: str | None) -> dict:
    papers_q = sb.table("pyq_papers").select("id, exam_cycle_id").eq("exam_id", exam_id)
    if cycle_id:
        papers_q = papers_q.eq("exam_cycle_id", cycle_id)
    papers = _safe(lambda: papers_q.limit(500).execute().data, default=[]) or []
    paper_count = len(papers)

    if paper_count == 0:
        return {
            "section": "pyq_workbench",
            "label": "PYQ Workbench",
            "status": "empty",
            "score_percent": 0,
            "weight": 3,
            "blockers": ["no PYQ papers uploaded"],
            "counts": {"present": 0, "required": 1},
            "metrics": {"papers": 0, "questions_total": 0, "questions_verified": 0, "questions_locked": 0, "options_total": 0, "topic_tags_total": 0},
        }

    paper_ids = [p["id"] for p in papers]
    # Fetch questions for these papers in chunks to avoid URL length limits
    all_questions = []
    chunk = 100
    for i in range(0, len(paper_ids), chunk):
        batch = paper_ids[i : i + chunk]
        qs = _safe(
            lambda b=batch: (
                sb.table("pyq_questions")
                .select("id, pyq_paper_id, reviewer_status")
                .in_("pyq_paper_id", b)
                .limit(20000)
                .execute()
                .data
            ),
            default=[],
        ) or []
        all_questions.extend(qs)

    questions_total = len(all_questions)
    questions_verified = sum(1 for q in all_questions if q.get("reviewer_status") in {"verified", "locked"})
    questions_locked = sum(1 for q in all_questions if q.get("reviewer_status") == "locked")
    questions_pending = sum(1 for q in all_questions if q.get("reviewer_status") in {"pending", "needs_correction"})

    question_ids = [q["id"] for q in all_questions if q.get("id")]
    options_total = 0
    topic_tags_total = 0
    if question_ids:
        # Use count-only queries (no row data) in larger batches to minimise round trips
        for i in range(0, len(question_ids), 500):
            batch = question_ids[i : i + 500]
            opts_count = _safe(
                lambda b=batch: (
                    sb.table("pyq_options")
                    .select("id", count="exact")
                    .in_("question_id", b)
                    .limit(0)
                    .execute()
                    .count
                ),
                default=0,
            ) or 0
            options_total += opts_count
            tags_count = _safe(
                lambda b=batch: (
                    sb.table("pyq_question_topic_tags")
                    .select("id", count="exact")
                    .in_("question_id", b)
                    .limit(0)
                    .execute()
                    .count
                ),
                default=0,
            ) or 0
            topic_tags_total += tags_count

    papers_with_no_questions = sum(
        1 for p in papers
        if not any(q["pyq_paper_id"] == p["id"] for q in all_questions)
    )

    if questions_total == 0:
        status = "partial"  # papers exist but no questions
    elif questions_locked == questions_total and questions_total > 0:
        status = "locked"
    elif questions_total > 0 and questions_verified / questions_total >= 0.5:
        status = "ready"
    else:
        status = "partial"

    blockers = []
    if papers_with_no_questions > 0:
        blockers.append(f"{papers_with_no_questions} paper{'s' if papers_with_no_questions != 1 else ''} with 0 questions")
    if questions_pending > 0:
        blockers.append(f"{questions_pending} question{'s' if questions_pending != 1 else ''} pending review")

    return {
        "section": "pyq_workbench",
        "label": "PYQ Workbench",
        "status": status,
        "score_percent": _STATUS_SCORE[status],
        "weight": 3,
        "blockers": blockers,
        "counts": {"present": questions_verified, "required": questions_total or 1},
        "metrics": {
            "papers": paper_count,
            "questions_total": questions_total,
            "questions_verified": questions_verified,
            "questions_locked": questions_locked,
            "options_total": options_total,
            "topic_tags_total": topic_tags_total,
        },
    }


def _updates(sb, exam_id: str, cycle_id: str | None) -> dict:
    q = sb.table("exam_policy_updates").select("id, reviewer_status, created_at").eq("exam_id", exam_id)
    if cycle_id:
        q = q.eq("exam_cycle_id", cycle_id)
    rows = _safe(lambda: q.limit(5000).execute().data, default=[]) or []
    total = len(rows)
    stale_cutoff = _days_ago(_STALE_DAYS)
    pending = sum(1 for r in rows if r.get("reviewer_status") in {"pending", "needs_correction"})
    stale = sum(
        1 for r in rows
        if r.get("reviewer_status") in {"pending", "needs_correction"}
        and (r.get("created_at") or "") < stale_cutoff
    )
    verified = sum(1 for r in rows if r.get("reviewer_status") in {"verified", "locked"})
    rejected = sum(1 for r in rows if r.get("reviewer_status") == "rejected")

    if total == 0:
        status = "empty"
    elif pending == 0 and stale == 0:
        status = "ready"
    else:
        status = "partial"

    blockers = []
    if pending > 0:
        blockers.append(f"{pending} update{'s' if pending != 1 else ''} pending review")
    if stale > 0:
        blockers.append(f"{stale} update{'s' if stale != 1 else ''} stale")

    return {
        "section": "updates",
        "label": "Updates",
        "status": status,
        "score_percent": _STATUS_SCORE[status],
        "weight": 1,
        "blockers": blockers,
        "counts": {"present": verified, "required": 0},
        "metrics": {"total": total, "pending": pending, "verified": verified, "stale": stale, "rejected": rejected},
    }


def _competition(sb, exam_id: str, cycle_id: str | None) -> dict:
    q = sb.table("exam_competition_metrics").select("id, exam_cycle_id, reviewer_status").eq("exam_id", exam_id)
    if cycle_id:
        q = q.eq("exam_cycle_id", cycle_id)
    rows = _safe(lambda: q.limit(100).execute().data, default=[]) or []

    if not rows:
        status = "empty"
        reviewer_status_val = None
    else:
        statuses = [r.get("reviewer_status") for r in rows]
        active = [s for s in statuses if s != "rejected"]
        if "locked" in active:
            status = "locked"
        elif "reviewed" in active:
            status = "ready"
        elif active:
            status = "partial"
        else:
            status = "partial"
        reviewer_status_val = rows[0].get("reviewer_status")

    blockers = []
    if not rows:
        blockers.append("no competition metric for this cycle")

    breakdown = {
        "draft": sum(1 for r in rows if r.get("reviewer_status") == "draft"),
        "reviewed": sum(1 for r in rows if r.get("reviewer_status") == "reviewed"),
        "locked": sum(1 for r in rows if r.get("reviewer_status") == "locked"),
    }

    return {
        "section": "competition",
        "label": "Competition",
        "status": status,
        "score_percent": _STATUS_SCORE[status],
        "weight": 1,
        "blockers": blockers,
        "counts": {"present": len(rows), "required": 1},
        "metrics": {
            "present_for_cycle": len(rows) > 0,
            "reviewer_status": reviewer_status_val,
            "breakdown": breakdown,
        },
    }


def _review_activate(sections: list[dict]) -> dict:
    upstream = sections  # all 6 preceding sections
    ready_statuses = {"ready", "locked"}
    sections_ready = sum(1 for s in upstream if s["status"] == "ready")
    sections_locked = sum(1 for s in upstream if s["status"] == "locked")
    sections_blocked = sum(1 for s in upstream if s["status"] not in ready_statuses)

    all_ready_or_locked = all(s["status"] in ready_statuses for s in upstream)
    at_least_one_locked = any(s["status"] == "locked" for s in upstream)

    if all_ready_or_locked and at_least_one_locked:
        status = "locked"
    elif all_ready_or_locked:
        status = "ready"
    elif sections_locked + sections_ready > 0:
        status = "partial"
    else:
        status = "empty"

    # Collect upstream blockers tagged by section
    blockers = []
    for s in upstream:
        for b in s.get("blockers", []):
            blockers.append(f"[{s['section']}] {b}")

    return {
        "section": "review_activate",
        "label": "Review & Activate",
        "status": status,
        "score_percent": _STATUS_SCORE[status],
        "weight": 0,
        "blockers": blockers,
        "counts": {"present": sections_ready + sections_locked, "required": len(upstream)},
        "metrics": {
            "sections_ready": sections_ready,
            "sections_locked": sections_locked,
            "sections_blocked": sections_blocked,
        },
    }


# ── public API ────────────────────────────────────────────────────────────────

def compute_exam_workspace_readiness(sb, exam_id: str, cycle_id: str | None = None) -> dict:
    """Compute full workspace readiness for exam_id (optionally scoped to cycle_id).

    Pure read — no writes, no side effects.
    """
    topic_coverage = _topic_coverage_snapshot(sb, exam_id, cycle_id)

    sections_data = [
        _setup(sb, exam_id),
        _documents(sb, exam_id, cycle_id),
        _syllabus_mapper(sb, exam_id),
        _pyq_workbench(sb, exam_id, cycle_id),
        _updates(sb, exam_id, cycle_id),
        _competition(sb, exam_id, cycle_id),
    ]
    review_act = _review_activate(sections_data)
    all_sections = sections_data + [review_act]

    # Score: exclude weight=0 sections
    scored = [s for s in all_sections if s["weight"] > 0]
    total_weight = sum(s["weight"] for s in scored)
    if total_weight > 0:
        score_percent = round(
            sum(s["score_percent"] * s["weight"] for s in scored) / total_weight
        )
    else:
        score_percent = 0

    ready_to_activate = review_act["status"] in {"ready", "locked"}

    if score_percent == 0:
        overall_status = "empty"
    elif score_percent == 100:
        overall_status = "locked"
    elif score_percent >= 80:
        overall_status = "ready"
    else:
        overall_status = "partial"

    all_blockers = [b for s in sections_data for b in s.get("blockers", [])]

    return {
        "exam_id": exam_id,
        "cycle_id": cycle_id,
        "generated_at": _now_iso(),
        "overall": {
            "status": overall_status,
            "score_percent": score_percent,
            "ready_to_activate": ready_to_activate,
            "blockers": all_blockers,
        },
        "sections": all_sections,
        "topic_coverage": topic_coverage,
    }
