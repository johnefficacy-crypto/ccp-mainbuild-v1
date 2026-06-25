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
    pyq_workbench  — pyq_papers + pyq_questions + pyq_question_topic_tags for exam_id (always exam-wide; cycle_id is provenance context only)
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

from app.db.utils import execute_or_raise
from app.exam_intelligence.pyq_readiness import aggregate_pyq_evidence

logger = logging.getLogger("career_copilot.exam_intelligence.readiness")

_STATUS_SCORE = {"empty": 0, "partial": 50, "ready": 80, "locked": 100}
_STALE_DAYS = 30
_DOC_PAGE = 1000


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


def _doc_pages_strict(sb, make_query, operation: str) -> list[dict]:
    """Full-pagination, fail-closed fetch. Any DB failure raises DatabaseError (→ 5xx)."""
    out: list[dict] = []
    start = 0
    while True:
        page = execute_or_raise(
            operation,
            lambda s=start: make_query().range(s, s + _DOC_PAGE - 1).execute().data,
        ) or []
        out.extend(page)
        if len(page) < _DOC_PAGE:
            break
        start += _DOC_PAGE
    return out


def load_doc_extraction_counts(
    sb, exam_id: str, cycle_id: str | None = None, *, strict: bool = False
) -> dict:
    """Return extraction counts for admin_exam_intelligence docs owned by exam_id.

    Extraction status is sourced from document_processing_jobs (job_type='text_extract',
    latest job per asset, deterministic by (created_at, id)).
    trust_status on syllabus_documents is a human-review gate, not an extraction
    signal (BUG-EI-2 final fix).

    document_assets has no exam_id column; ownership is stored in metadata JSONB
    by admin_exam_intel_documents.py at upload time.

    strict=True (console): fail-closed — any DB failure raises DatabaseError (→ 5xx).
    strict=False (workspace readiness): fail-soft — DB failures degrade to zero counts.
    """
    # Fetch all admin EI assets; filter to exam (and optionally cycle) in Python
    # because document_assets.exam_id does not exist as a column.
    if strict:
        asset_rows = _doc_pages_strict(
            sb,
            lambda: (
                sb.table("document_assets")
                .select("id, metadata")
                .eq("scope", "admin_exam_intelligence")
                .order("id")
            ),
            "doc_extraction.assets",
        )
    else:
        def _load_assets() -> list[dict]:
            out: list[dict] = []
            start = 0
            while True:
                page = (
                    sb.table("document_assets")
                    .select("id, metadata")
                    .eq("scope", "admin_exam_intelligence")
                    .order("id")
                    .range(start, start + _DOC_PAGE - 1)
                    .execute()
                    .data
                ) or []
                out.extend(page)
                if len(page) < _DOC_PAGE:
                    break
                start += _DOC_PAGE
            return out

        asset_rows = _safe(_load_assets, default=[]) or []

    assets = [r for r in asset_rows if (r.get("metadata") or {}).get("exam_id") == exam_id]
    if cycle_id:
        assets = [r for r in assets if (r.get("metadata") or {}).get("exam_cycle_id") == cycle_id]

    total = len(assets)
    if total == 0:
        return {"total": 0, "extracted": 0, "pending": 0, "failed": 0,
                "needs_review": 0, "not_started": 0}

    asset_ids = [r["id"] for r in assets]

    # Batch-load latest text_extract job per asset — no per-asset N+1 queries.
    all_jobs: list[dict] = []
    for i in range(0, len(asset_ids), 500):
        batch = asset_ids[i : i + 500]
        if strict:
            jobs = _doc_pages_strict(
                sb,
                lambda b=batch: (
                    sb.table("document_processing_jobs")
                    .select("document_id, status, created_at, id")
                    .in_("document_id", b)
                    .eq("job_type", "text_extract")
                    .order("id")
                ),
                "doc_extraction.jobs",
            )
        else:
            def _load_batch(b=batch) -> list[dict]:
                out: list[dict] = []
                start = 0
                while True:
                    page = (
                        sb.table("document_processing_jobs")
                        .select("document_id, status, created_at, id")
                        .in_("document_id", b)
                        .eq("job_type", "text_extract")
                        .order("id")
                        .range(start, start + _DOC_PAGE - 1)
                        .execute()
                        .data
                    ) or []
                    out.extend(page)
                    if len(page) < _DOC_PAGE:
                        break
                    start += _DOC_PAGE
                return out

            jobs = _safe(_load_batch, default=[]) or []
        all_jobs.extend(jobs)

    # Latest job per asset: deterministic by (created_at, id) so ties resolve consistently.
    latest: dict[str, str] = {}
    for j in sorted(all_jobs, key=lambda x: (x.get("created_at") or "", x.get("id") or "")):
        latest[j["document_id"]] = j["status"]

    extracted    = sum(1 for aid in asset_ids if latest.get(aid) == "succeeded")
    pending      = sum(1 for aid in asset_ids if latest.get(aid) in {"queued", "running"})
    failed       = sum(1 for aid in asset_ids if latest.get(aid) == "failed")
    needs_review = sum(1 for aid in asset_ids if latest.get(aid) == "needs_review")
    not_started  = sum(1 for aid in asset_ids if aid not in latest)

    return {
        "total": total,
        "extracted": extracted,
        "pending": pending,
        "failed": failed,
        "needs_review": needs_review,
        "not_started": not_started,
    }


def load_first_failing_doc_strict(sb, exam_id: str, cycle_id: str | None = None) -> dict | None:
    """Return {row_id, extraction_status} for first failed/pending document asset (strict pager).
    Returns None when all docs are extracted or there are no docs.
    """
    asset_rows = _doc_pages_strict(
        sb,
        lambda: (
            sb.table("document_assets")
            .select("id, metadata")
            .eq("scope", "admin_exam_intelligence")
            .order("id")
        ),
        "first_failing_doc.assets",
    )
    assets = [r for r in asset_rows if (r.get("metadata") or {}).get("exam_id") == exam_id]
    if cycle_id:
        assets = [r for r in assets if (r.get("metadata") or {}).get("exam_cycle_id") == cycle_id]
    if not assets:
        return None
    asset_ids = [r["id"] for r in assets]
    all_jobs: list[dict] = []
    for i in range(0, len(asset_ids), 500):
        batch = asset_ids[i : i + 500]
        all_jobs.extend(
            _doc_pages_strict(
                sb,
                lambda b=batch: (
                    sb.table("document_processing_jobs")
                    .select("document_id, status, created_at, id")
                    .in_("document_id", b)
                    .eq("job_type", "text_extract")
                    .order("id")
                ),
                "first_failing_doc.jobs",
            )
        )
    latest: dict[str, str] = {}
    for j in sorted(all_jobs, key=lambda x: (x.get("created_at") or "", x.get("id") or "")):
        latest[j["document_id"]] = j["status"]
    for aid in asset_ids:
        st = latest.get(aid)
        if st == "failed":
            return {"kind": "document_assets", "row_id": aid, "extraction_status": "failed"}
        if st in {"queued", "running"} or st is None:
            return {"kind": "document_assets", "row_id": aid, "extraction_status": "pending"}
    return None


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
    # D10: fetch ALL papers for exam_id — NO cycle filter whatsoever.
    # Full pagination + failure tracking (fail-soft: degrade, not crash).
    _PAGE = 500
    _read_failed = False

    def _paged(make_query, label):
        nonlocal _read_failed
        out: list[dict] = []
        start = 0
        while True:
            try:
                page = make_query().order("id").range(start, start + _PAGE - 1).execute().data or []
            except Exception as exc:  # noqa: BLE001
                logger.warning("pyq_workbench read failed (%s): %s", label, exc)
                _read_failed = True
                return out
            out.extend(page)
            if len(page) < _PAGE:
                break
            start += _PAGE
        return out

    papers = _paged(
        lambda: sb.table("pyq_papers").select("id, exam_cycle_id, trust_status").eq("exam_id", exam_id),
        "papers",
    )

    paper_ids = [p["id"] for p in papers if p.get("id")]

    # Fetch all questions in chunks (URL-length safety) with pagination inside each chunk.
    all_questions: list[dict] = []
    for i in range(0, len(paper_ids), 100):
        batch = paper_ids[i : i + 100]
        all_questions.extend(_paged(
            lambda b=batch: (
                sb.table("pyq_questions")
                .select("id, pyq_paper_id, reviewer_status")
                .in_("pyq_paper_id", b)
            ),
            "questions",
        ))

    question_ids = [q["id"] for q in all_questions if q.get("id")]

    # Fetch all topic tags in chunks (needed for gate 3).
    all_topic_tags: list[dict] = []
    for i in range(0, len(question_ids), 100):
        batch = question_ids[i : i + 100]
        all_topic_tags.extend(_paged(
            lambda b=batch: (
                sb.table("pyq_question_topic_tags")
                .select("id, question_id, reviewer_status")
                .in_("question_id", b)
            ),
            "topic_tags",
        ))

    # topic_tags_total is available directly from loaded rows.
    topic_tags_total = len(all_topic_tags)

    # Restore options_total count-only query (fail-soft, not required for trust gates).
    options_total = 0
    for i in range(0, len(question_ids), 500):
        batch = question_ids[i : i + 500]
        cnt = _safe(
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
        options_total += cnt

    # Delegate all readiness logic to the D10 canonical aggregator.
    ev = aggregate_pyq_evidence(
        papers=papers,
        questions=all_questions,
        topic_tags=all_topic_tags,
        selected_cycle_id=cycle_id,
    )

    # If any required read failed, override state to "failed".
    if _read_failed:
        ev = {**ev, "state": "failed"}

    d10_state = ev.get("state", "missing")

    # Map D10 state → legacy section vocabulary.
    # D10 does not use "locked"; legacy "locked" remains valid for syllabus/competition.
    _D10_TO_LEGACY = {
        "missing": "empty",
        "review_pending": "partial",
        "ready": "ready",
        "failed": "empty",    # fail-soft: degrade to empty with blocker
    }
    legacy_status = _D10_TO_LEGACY.get(d10_state, "empty")

    # Build blockers from D10 evidence fields.
    blockers: list[str] = []
    if _read_failed:
        blockers.append("pyq readiness read failed — data may be incomplete")
    elif ev.get("papers_total", 0) == 0:
        blockers.append("no PYQ papers uploaded")
    else:
        papers_pending_review = ev.get("papers_pending_review", 0)
        if papers_pending_review > 0:
            blockers.append(f"{papers_pending_review} paper{'s' if papers_pending_review != 1 else ''} pending review")
        pending_question_count = ev.get("pending_question_count", 0)
        if pending_question_count > 0:
            blockers.append(f"{pending_question_count} question{'s' if pending_question_count != 1 else ''} pending review")
        # Gate-3 blocker: questions cleared gates 1+2 but no verified tag yet.
        eligible = ev.get("questions_eligible_before_tag_gate", 0)
        if eligible > 0 and ev.get("verified_question_count", 0) == 0:
            pending_tags = ev.get("pending_tag_count", 0)
            if pending_tags > 0:
                blockers.append(f"{pending_tags} topic tag{'s' if pending_tags != 1 else ''} pending review")
            else:
                blockers.append(f"{eligible} question{'s' if eligible != 1 else ''} missing verified topic tag")
        # Catch-all: review_pending with no corrective blocker yet.
        # Covers: verified paper + zero questions, verified paper + all rejected questions.
        if not blockers and ev.get("verified_question_count", 0) == 0:
            q_on_vp = ev.get("questions_on_verified_papers", 0)
            if q_on_vp == 0:
                verified_paper_count = sum(
                    1 for p in papers if p.get("trust_status") == "verified"
                )
                if verified_paper_count > 0:
                    blockers.append(
                        f"{verified_paper_count} verified paper"
                        f"{'s' if verified_paper_count != 1 else ''} "
                        "have no questions uploaded"
                    )
            else:
                blockers.append(
                    f"{q_on_vp} question"
                    f"{'s' if q_on_vp != 1 else ''} on verified paper(s) "
                    "have no valid reviewer status"
                )

    return {
        "section": "pyq_workbench",
        "label": "PYQ Workbench",
        "status": legacy_status,
        "score_percent": _STATUS_SCORE[legacy_status],
        "weight": 3,
        "blockers": blockers,
        "counts": {
            "present": ev.get("verified_question_count", 0),
            "required": max(ev.get("questions_total", 0), 1),
        },
        "metrics": {
            "papers": ev.get("papers_total", 0),
            "questions_total": ev.get("questions_total", 0),
            "questions_verified": ev.get("verified_question_count", 0),
            "questions_locked": 0,          # always 0; "locked" is not valid per D10/schema
            "options_total": options_total,
            "topic_tags_total": topic_tags_total,
            "pyq_readiness": ev,            # full D10 canonical object, additive
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
