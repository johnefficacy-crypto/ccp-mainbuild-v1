"""Cycle activation checklist computation (I9).

Nine-step activation checklist per I6 gate document (PR #761, approved 2026-06-24).
D01-D16 all APPROVED. Returns backend-derived step statuses; frontend must not
recompute completion or activation authority.

Status vocabulary (D03): missing | uploaded | extracting | review_pending |
                         ready | stale | failed | not_applicable
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Any

from app.db.utils import execute_or_raise
from app.exam_intelligence.console_detail import build_console_detail

logger = logging.getLogger("career_copilot.exam_intelligence.cycle_checklist")

CONTRACT_VERSION = 1

STEP_LABELS = {
    "cycle_details": "Cycle details",
    "phases_schedule": "Phases and schedule",
    "source_documents": "Source documents",
    "extraction": "Extraction",
    "syllabus_mapping": "Syllabus mapping",
    "pyq_readiness": "PYQ readiness",
    "policy_updates": "Policy updates",
    "competition_context": "Competition context",
    "review_activate": "Review and activate",
}

STEP_ORDER = list(STEP_LABELS.keys())

def _now_iso():
    return datetime.now(timezone.utc).isoformat()

def _safe(call, default=None):
    try:
        return call()
    except Exception as exc:
        logger.warning("cycle_checklist advisory read failed: %s", exc)
        return default

def _make_step(step_id, status, gate_class, evidence_scope="selected_cycle",
               action_cta=None, note=None, not_applicable_reason=None):
    out = {
        "step_id": step_id,
        "label": STEP_LABELS[step_id],
        "status": status,
        "gate_class": gate_class,
        "evidence_scope": evidence_scope,
        "action_cta": action_cta,
        "note": note,
    }
    if not_applicable_reason is not None:
        out["not_applicable_reason"] = not_applicable_reason
    return out

def _exam_base_url(exam_id):
    return f"/admin/exam-intelligence/exams/{exam_id}"


def _compute_extraction_status(sb, exam_id, cycle_id):
    """Compute extraction status from document_processing_jobs for docs linked to exam."""
    doc_rows = (sb.table("exam_documents")
                .select("document_asset_id")
                .eq("exam_id", exam_id)
                .limit(500)
                .execute().data) or []
    if not doc_rows:
        return "missing"

    asset_ids = [r["document_asset_id"] for r in doc_rows if r.get("document_asset_id")]
    if not asset_ids:
        return "missing"

    job_rows = (sb.table("document_processing_jobs")
                .select("asset_id, status, created_at, id")
                .in_("asset_id", asset_ids)
                .eq("job_type", "text_extract")
                .order("created_at", desc=True)
                .order("id", desc=True)
                .limit(500)
                .execute().data) or []

    seen = set()
    latest_statuses = []
    for r in job_rows:
        aid = r.get("asset_id")
        if aid and aid not in seen:
            seen.add(aid)
            latest_statuses.append(r.get("status"))

    if not latest_statuses:
        return "missing"

    if any(s == "failed" for s in latest_statuses):
        return "failed"
    if any(s == "needs_review" for s in latest_statuses):
        return "review_pending"
    if any(s in ("queued", "running") for s in latest_statuses):
        return "extracting"
    if any(s == "succeeded" for s in latest_statuses):
        return "ready"
    return "missing"


def _count_verified_pyq(sb, exam_id):
    """Count PYQ questions that pass all three verified gates (exam-wide)."""
    papers = (sb.table("pyq_papers")
              .select("id")
              .eq("exam_id", exam_id)
              .eq("trust_status", "verified")
              .limit(500)
              .execute().data) or []
    if not papers:
        return 0

    paper_ids = [p["id"] for p in papers]

    questions = (sb.table("pyq_questions")
                 .select("id")
                 .in_("pyq_paper_id", paper_ids)
                 .eq("reviewer_status", "verified")
                 .limit(500)
                 .execute().data) or []
    if not questions:
        return 0

    q_ids = [q["id"] for q in questions]

    tags = (sb.table("pyq_question_topic_tags")
            .select("question_id")
            .in_("question_id", q_ids)
            .eq("reviewer_status", "verified")
            .limit(500)
            .execute().data) or []

    tagged_q_ids = {t["question_id"] for t in tags if t.get("question_id")}
    return len(tagged_q_ids)


def compute_cycle_activation_checklist(sb, exam_id: str, cycle_id: str) -> dict | None:
    """Compute 9-step activation checklist for a selected cycle.
    Returns None if cycle not found for this exam.
    """
    # --- Step 1: cycle_details ---
    cycles = execute_or_raise(
        "cycle_checklist.cycles",
        lambda: sb.table("exam_cycles").select("id, exam_id, cycle_name, year, status").eq("id", cycle_id).limit(1).execute().data
    ) or []
    if not cycles or cycles[0].get("exam_id") != exam_id:
        return None
    cycle = cycles[0]

    cycle_name = (cycle.get("cycle_name") or "").strip()
    cycle_year = cycle.get("year")
    cycle_details_ready = bool(cycle_name and cycle_year is not None)

    steps = []

    # Step 1: cycle_details
    steps.append(_make_step(
        "cycle_details",
        status="ready" if cycle_details_ready else "missing",
        gate_class="hard",
        evidence_scope="selected_cycle",
        action_cta={"label": "Go to Setup", "url": f"{_exam_base_url(exam_id)}?tab=setup"},
        note=None if cycle_details_ready else "Cycle name and year are required.",
    ))

    # Step 2: phases_schedule
    phase_rows = _safe(
        lambda: (sb.table("exam_phases").select("id").eq("exam_cycle_id", cycle_id).limit(1).execute().data),
        default=[],
    ) or []
    phases_ready = len(phase_rows) > 0
    steps.append(_make_step(
        "phases_schedule",
        status="ready" if phases_ready else "missing",
        gate_class="hard",
        evidence_scope="selected_cycle",
        action_cta={"label": "Go to Setup", "url": f"{_exam_base_url(exam_id)}?tab=setup"},
        note=None if phases_ready else "At least one phase belonging to this cycle is required.",
    ))

    # Step 3: source_documents
    doc_rows = _safe(
        lambda: (sb.table("exam_documents").select("id, document_asset_id").eq("exam_id", exam_id).limit(1).execute().data),
        default=[],
    ) or []
    docs_status = "ready" if doc_rows else "missing"
    steps.append(_make_step(
        "source_documents",
        status=docs_status,
        gate_class="advisory",
        evidence_scope="exam_wide",
        action_cta={"label": "Open Documents", "url": f"{_exam_base_url(exam_id)}?cycle={cycle_id}&tab=documents"},
        note=None if doc_rows else "No source documents uploaded yet.",
    ))

    # Step 4: extraction
    extract_status = _safe(lambda: _compute_extraction_status(sb, exam_id, cycle_id), default="missing")
    steps.append(_make_step(
        "extraction",
        status=extract_status,
        gate_class="advisory",
        evidence_scope="exam_wide",
        action_cta={"label": "Open Documents", "url": f"{_exam_base_url(exam_id)}?cycle={cycle_id}&tab=documents"},
    ))

    # Step 5: syllabus_mapping
    locked_cov = _safe(
        lambda: (sb.table("exam_topic_coverage")
                 .select("id")
                 .eq("exam_id", exam_id)
                 .eq("reviewer_status", "locked")
                 .or_(f"exam_cycle_id.eq.{cycle_id},exam_cycle_id.is.null")
                 .limit(1)
                 .execute().data),
        default=[],
    ) or []
    coverage_ready = len(locked_cov) > 0

    pending_mentions = _safe(
        lambda: (sb.table("syllabus_topic_mentions")
                 .select("id")
                 .eq("exam_id", exam_id)
                 .in_("reviewer_status", ["pending", "needs_correction"])
                 .limit(1)
                 .execute().data),
        default=[],
    ) or []
    mentions_clear = len(pending_mentions) == 0

    if not coverage_ready:
        syllabus_status = "missing"
    elif not mentions_clear:
        syllabus_status = "review_pending"
    else:
        syllabus_status = "ready"

    steps.append(_make_step(
        "syllabus_mapping",
        status=syllabus_status,
        gate_class="hard",
        evidence_scope="exam_wide",
        action_cta={"label": "Review Syllabus", "url": f"{_exam_base_url(exam_id)}?tab=syllabus&status=pending"},
        note=None if coverage_ready else "At least one locked topic coverage row required.",
    ))

    # Step 6: pyq_readiness
    verified_pyq = _safe(lambda: _count_verified_pyq(sb, exam_id), default=0)
    pyq_status = "ready" if (verified_pyq or 0) > 0 else "missing"
    steps.append(_make_step(
        "pyq_readiness",
        status=pyq_status,
        gate_class="advisory",
        evidence_scope="exam_wide",
        action_cta={"label": "Open PYQ Workbench", "url": f"{_exam_base_url(exam_id)}?cycle={cycle_id}&tab=pyq"},
        note=None if pyq_status == "ready" else "No verified PYQ questions found.",
    ))

    # Step 7: policy_updates
    pending_updates = _safe(
        lambda: (sb.table("exam_policy_updates")
                 .select("id")
                 .eq("exam_id", exam_id)
                 .in_("reviewer_status", ["pending", "needs_correction"])
                 .or_(f"exam_cycle_id.eq.{cycle_id},exam_cycle_id.is.null")
                 .limit(1)
                 .execute().data),
        default=[],
    ) or []
    updates_status = "review_pending" if pending_updates else "ready"
    steps.append(_make_step(
        "policy_updates",
        status=updates_status,
        gate_class="advisory",
        evidence_scope="mixed",
        action_cta={"label": "Review Updates", "url": f"{_exam_base_url(exam_id)}?tab=updates&status=pending"},
        note=None if updates_status == "ready" else "Pending policy updates require review.",
    ))

    # Step 8: competition_context
    exam_rows = execute_or_raise(
        "cycle_checklist.exam",
        lambda: sb.table("exams").select("id, management_mode").eq("id", exam_id).limit(1).execute().data
    ) or []
    management_mode = exam_rows[0].get("management_mode") if exam_rows else None

    if management_mode in ("light", "index_only", "archive"):
        comp_rows = _safe(
            lambda: (sb.table("exam_competition_metrics")
                     .select("id")
                     .eq("exam_id", exam_id)
                     .in_("reviewer_status", ["reviewed", "locked"])
                     .limit(1)
                     .execute().data),
            default=[],
        ) or []
        if not comp_rows:
            steps.append(_make_step(
                "competition_context",
                status="not_applicable",
                gate_class="advisory",
                evidence_scope="exam_wide",
                action_cta=None,
                not_applicable_reason=f"management_mode_{management_mode}",
            ))
        else:
            steps.append(_make_step(
                "competition_context",
                status="ready",
                gate_class="advisory",
                evidence_scope="exam_wide",
                action_cta=None,
            ))
    else:
        comp_rows = _safe(
            lambda: (sb.table("exam_competition_metrics")
                     .select("id")
                     .eq("exam_id", exam_id)
                     .in_("reviewer_status", ["reviewed", "locked"])
                     .limit(1)
                     .execute().data),
            default=[],
        ) or []
        comp_status = "ready" if comp_rows else "missing"
        steps.append(_make_step(
            "competition_context",
            status=comp_status,
            gate_class="advisory",
            evidence_scope="exam_wide",
            action_cta={"label": "Open Competition", "url": f"{_exam_base_url(exam_id)}?cycle={cycle_id}&tab=competition"},
            note=None if comp_status == "ready" else "No competition context found for this exam.",
        ))

    # Step 9: review_activate
    hard_prereqs_met = cycle_details_ready and phases_ready and coverage_ready

    verdict_ready = False
    if hard_prereqs_met:
        verdict_data = _safe(
            lambda: build_console_detail(sb, exam_id, cycle_id),
            default=None,
        )
        if verdict_data:
            verdict_ready = verdict_data.get("activation_verdict", {}).get("status") == "ready"

    if management_mode in ("index_only", "archive"):
        review_status = "not_applicable"
        review_na_reason = f"management_mode_{management_mode}"
        review_cta = None
    elif not hard_prereqs_met:
        review_status = "missing"
        review_na_reason = None
        review_cta = {"label": "Go to Setup", "url": f"{_exam_base_url(exam_id)}?tab=setup"}
    elif verdict_ready:
        review_status = "ready"
        review_na_reason = None
        review_cta = {"label": "Review & Activate", "url": f"{_exam_base_url(exam_id)}?cycle={cycle_id}&tab=review"}
    else:
        review_status = "review_pending"
        review_na_reason = None
        review_cta = {"label": "Review & Activate", "url": f"{_exam_base_url(exam_id)}?cycle={cycle_id}&tab=review"}

    review_step = _make_step(
        "review_activate",
        status=review_status,
        gate_class="hard",
        evidence_scope="selected_cycle",
        action_cta=review_cta,
    )
    if review_na_reason:
        review_step["not_applicable_reason"] = review_na_reason
    steps.append(review_step)

    computed_at = _now_iso()
    return {
        "cycle_id": cycle_id,
        "computed_at": computed_at,
        "steps": steps,
    }
