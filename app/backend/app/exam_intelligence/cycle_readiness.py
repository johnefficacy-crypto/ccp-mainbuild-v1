"""Cycle activation checklist — nine-step readiness derivation (I9).

``compute_cycle_readiness`` is the single authority for deriving each step's
status from live DB state.  Any unhandled exception propagates to the caller;
the outer ``_safe()`` in management_read_model returns cycle_readiness=null
(D16/A7 unavailable state) rather than fabricating missing evidence status.

Architecture gate refs: D01-D16.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("career_copilot.exam_intelligence.cycle_readiness")

_MISSING = "missing"
_UPLOADED = "uploaded"
_EXTRACTING = "extracting"
_REVIEW_PENDING = "review_pending"
_READY = "ready"
_STALE = "stale"
_FAILED = "failed"
_NA = "not_applicable"

_MGMT_MODES_NO_DOCS = ("index_only", "archive")
_MGMT_MODES_LIGHT = ("light", "index_only", "archive")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _step(
    n: int,
    key: str,
    label: str,
    status: str,
    *,
    gate_class: str,
    evidence_scope: str,
    not_applicable_reason: str | None = None,
    action_cta: dict | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    return {
        "step": n,
        "key": key,
        "label": label,
        "status": status,
        "not_applicable_reason": not_applicable_reason,
        "gate_class": gate_class,
        "evidence_scope": evidence_scope,
        "action_cta": action_cta,
        "note": note,
    }



def compute_cycle_readiness(
    sb,
    exam_id: str,
    cycle_id: str | None,
    exam: dict[str, Any],
) -> dict[str, Any]:
    """Compute the nine-step cycle activation checklist.

    Each step is read fail-soft: errors yield status="missing" and continue.
    """
    computed_at = _now_iso()
    management_mode = (exam or {}).get("management_mode", "")
    steps: list[dict[str, Any]] = []
    locked_coverage_count = 0

    # Step 1: cycle_details
    if not cycle_id:
        s1 = _step(1, "cycle_details", "Cycle details", _MISSING,
                   gate_class="hard", evidence_scope="selected_cycle",
                   action_cta={"label": "Go to Setup", "url": f"/admin/exam-intelligence/exams/{exam_id}?tab=setup"})
    else:
        rows = (sb.table("exam_cycles")
                .select("id, cycle_name, year, status")
                .eq("id", cycle_id).limit(1).execute().data or [])
        cycle_row = rows[0] if rows else None
        if cycle_row and cycle_row.get("cycle_name") and cycle_row.get("year") is not None:
            s1 = _step(1, "cycle_details", "Cycle details", _READY,
                       gate_class="hard", evidence_scope="selected_cycle")
        else:
            s1 = _step(1, "cycle_details", "Cycle details", _MISSING,
                       gate_class="hard", evidence_scope="selected_cycle",
                       action_cta={"label": "Go to Setup", "url": f"/admin/exam-intelligence/exams/{exam_id}?tab=setup"})
    steps.append(s1)

    # Step 2: phases_schedule
    if not cycle_id:
        s2 = _step(2, "phases_schedule", "Phases schedule", _NA,
                   gate_class="hard", evidence_scope="selected_cycle",
                   not_applicable_reason="no_selected_cycle")
    else:
        phase_rows = (sb.table("exam_phases")
                      .select("id")
                      .eq("exam_cycle_id", cycle_id).limit(1).execute().data or [])
        if phase_rows:
            s2 = _step(2, "phases_schedule", "Phases schedule", _READY,
                       gate_class="hard", evidence_scope="selected_cycle")
        else:
            s2 = _step(2, "phases_schedule", "Phases schedule", _MISSING,
                       gate_class="hard", evidence_scope="selected_cycle",
                       action_cta={"label": "Add phase", "url": f"/admin/exam-intelligence/exams/{exam_id}?tab=setup"})
    steps.append(s2)

    # Step 3: source_documents
    if management_mode in _MGMT_MODES_NO_DOCS:
        s3 = _step(3, "source_documents", "Source documents", _NA,
                   gate_class="advisory", evidence_scope="exam_wide",
                   not_applicable_reason="optional_for_management_mode")
    else:
        # document_assets has no exam_id column; filter via scope + metadata in Python
        all_asset_rows = (sb.table("document_assets")
                          .select("id, metadata, status")
                          .eq("scope", "admin_exam_intelligence")
                          .limit(500).execute().data or [])
        doc_rows = [r for r in all_asset_rows if (r.get("metadata") or {}).get("exam_id") == exam_id]
        if not doc_rows:
            s3 = _step(3, "source_documents", "Source documents", _MISSING,
                       gate_class="advisory", evidence_scope="exam_wide")
        else:
            processed = any(d.get("status") == "processed" for d in doc_rows)
            if not processed:
                doc_ids = [d["id"] for d in doc_rows if d.get("id")]
                job_rows: list = []
                if doc_ids:
                    job_rows = (sb.table("document_processing_jobs")
                                .select("id, status")
                                .in_("document_id", doc_ids).execute().data or [])
                processed = any(j.get("status") == "succeeded" for j in job_rows)
            if processed:
                s3 = _step(3, "source_documents", "Source documents", _READY,
                           gate_class="advisory", evidence_scope="exam_wide")
            else:
                s3 = _step(3, "source_documents", "Source documents", _UPLOADED,
                           gate_class="advisory", evidence_scope="exam_wide")
    steps.append(s3)

    # Step 4: extraction
    if management_mode in _MGMT_MODES_NO_DOCS:
        s4 = _step(4, "extraction", "Text extraction", _NA,
                   gate_class="advisory", evidence_scope="exam_wide",
                   not_applicable_reason="optional_for_management_mode")
    else:
        # document_assets has no exam_id column; filter via scope + metadata
        all_asset_rows4 = (sb.table("document_assets")
                           .select("id, metadata")
                           .eq("scope", "admin_exam_intelligence")
                           .limit(500).execute().data or [])
        doc_ids = [r["id"] for r in all_asset_rows4
                   if (r.get("metadata") or {}).get("exam_id") == exam_id and r.get("id")]
        if not doc_ids:
            s4 = _step(4, "extraction", "Text extraction", _MISSING,
                       gate_class="advisory", evidence_scope="exam_wide")
        else:
            job_rows = (sb.table("document_processing_jobs")
                        .select("id, status")
                        .eq("job_type", "text_extract")
                        .in_("document_id", doc_ids).execute().data or [])
            statuses = [j.get("status") for j in job_rows]
            if not statuses:
                s4 = _step(4, "extraction", "Text extraction", _UPLOADED,
                           gate_class="advisory", evidence_scope="exam_wide")
            elif "failed" in statuses:
                s4 = _step(4, "extraction", "Text extraction", _FAILED,
                           gate_class="advisory", evidence_scope="exam_wide",
                           action_cta={"label": "View documents", "url": f"/admin/exam-intelligence/exams/{exam_id}?tab=documents"})
            elif "needs_review" in statuses:
                s4 = _step(4, "extraction", "Text extraction", _REVIEW_PENDING,
                           gate_class="advisory", evidence_scope="exam_wide")
            elif any(s in statuses for s in ("queued", "running")):
                s4 = _step(4, "extraction", "Text extraction", _EXTRACTING,
                           gate_class="advisory", evidence_scope="exam_wide")
            elif "succeeded" in statuses:
                s4 = _step(4, "extraction", "Text extraction", _READY,
                           gate_class="advisory", evidence_scope="exam_wide")
            else:
                s4 = _step(4, "extraction", "Text extraction", _MISSING,
                           gate_class="advisory", evidence_scope="exam_wide")
    steps.append(s4)

    # Step 5: syllabus_mapping
    if management_mode in _MGMT_MODES_NO_DOCS:
        s5 = _step(5, "syllabus_mapping", "Syllabus mapping", _NA,
                   gate_class="hard", evidence_scope="mixed",
                   not_applicable_reason="optional_for_management_mode")
    else:
        cov_rows = (sb.table("exam_topic_coverage")
                    .select("id")
                    .eq("exam_id", exam_id)
                    .eq("reviewer_status", "locked").execute().data or [])
        locked_coverage_count = len(cov_rows)
        if locked_coverage_count == 0:
            s5 = _step(5, "syllabus_mapping", "Syllabus mapping", _MISSING,
                       gate_class="hard", evidence_scope="mixed")
        else:
            mention_rows = (sb.table("syllabus_topic_mentions")
                            .select("id, reviewer_status")
                            .eq("exam_id", exam_id).execute().data or [])
            pending_count = sum(
                1 for m in mention_rows
                if m.get("reviewer_status") in ("pending", "needs_correction")
            )
            if pending_count == 0:
                s5 = _step(5, "syllabus_mapping", "Syllabus mapping", _READY,
                           gate_class="hard", evidence_scope="mixed")
            else:
                s5 = _step(5, "syllabus_mapping", "Syllabus mapping", _REVIEW_PENDING,
                           gate_class="advisory", evidence_scope="mixed")
    steps.append(s5)

    # Step 6: pyq_readiness
    if management_mode in _MGMT_MODES_NO_DOCS:
        s6 = _step(6, "pyq_readiness", "PYQ readiness", _NA,
                   gate_class="advisory", evidence_scope="exam_wide",
                   not_applicable_reason="optional_for_management_mode")
    else:
        paper_rows = (sb.table("pyq_papers")
                      .select("id")
                      .eq("exam_id", exam_id)
                      .eq("trust_status", "verified").execute().data or [])
        verified_paper_ids = [p["id"] for p in paper_rows if p.get("id")]
        if not verified_paper_ids:
            s6 = _step(6, "pyq_readiness", "PYQ readiness", _MISSING,
                       gate_class="advisory", evidence_scope="exam_wide")
        else:
            q_rows = (sb.table("pyq_questions")
                      .select("id, reviewer_status")
                      .in_("pyq_paper_id", verified_paper_ids).execute().data or [])
            verified_q_ids = [
                q["id"] for q in q_rows
                if q.get("reviewer_status") == "verified" and q.get("id")
            ]
            pending_qs = any(
                q.get("reviewer_status") in ("pending", "needs_correction") for q in q_rows
            )
            if not verified_q_ids:
                s6 = _step(6, "pyq_readiness", "PYQ readiness", _MISSING,
                           gate_class="advisory", evidence_scope="exam_wide")
            else:
                tag_rows = (sb.table("pyq_question_topic_tags")
                            .select("id, reviewer_status")
                            .in_("question_id", verified_q_ids).execute().data or [])
                verified_tags = [t for t in tag_rows if t.get("reviewer_status") == "verified"]
                pending_tags = any(
                    t.get("reviewer_status") in ("pending", "needs_correction") for t in tag_rows
                )
                if not verified_tags:
                    s6 = _step(6, "pyq_readiness", "PYQ readiness", _MISSING,
                               gate_class="advisory", evidence_scope="exam_wide")
                elif pending_qs or pending_tags:
                    s6 = _step(6, "pyq_readiness", "PYQ readiness", _REVIEW_PENDING,
                               gate_class="advisory", evidence_scope="exam_wide")
                else:
                    s6 = _step(6, "pyq_readiness", "PYQ readiness", _READY,
                               gate_class="advisory", evidence_scope="exam_wide")
    steps.append(s6)

    # Step 7: policy_updates
    pu_rows = (sb.table("exam_policy_updates")
               .select("id, reviewer_status, exam_cycle_id")
               .eq("exam_id", exam_id).execute().data or [])
    relevant = [
        r for r in pu_rows
        if r.get("exam_cycle_id") == cycle_id or r.get("exam_cycle_id") is None
    ]
    pending_pu = any(r.get("reviewer_status") in ("pending", "needs_correction") for r in relevant)
    if pending_pu:
        s7 = _step(7, "policy_updates", "Policy updates", _REVIEW_PENDING,
                   gate_class="advisory", evidence_scope="mixed")
    else:
        s7 = _step(7, "policy_updates", "Policy updates", _READY,
                   gate_class="advisory", evidence_scope="mixed")
    steps.append(s7)

    # Step 8: competition_context
    comp_rows = (sb.table("exam_competition_metrics")
                 .select("id, reviewer_status")
                 .eq("exam_id", exam_id).execute().data or [])
    reviewed = [r for r in comp_rows if r.get("reviewer_status") in ("reviewed", "locked")]
    if reviewed:
        s8 = _step(8, "competition_context", "Competition context", _READY,
                   gate_class="advisory", evidence_scope="exam_wide")
    elif management_mode in _MGMT_MODES_LIGHT and not comp_rows:
        s8 = _step(8, "competition_context", "Competition context", _NA,
                   gate_class="advisory", evidence_scope="exam_wide",
                   not_applicable_reason="optional_for_management_mode")
    else:
        s8 = _step(8, "competition_context", "Competition context", _MISSING,
                   gate_class="advisory", evidence_scope="exam_wide")
    steps.append(s8)

    # Step 9: review_activate
    if management_mode in _MGMT_MODES_NO_DOCS:
        s9 = _step(9, "review_activate", "Review & activate", _NA,
                   gate_class="hard", evidence_scope="exam_wide",
                   not_applicable_reason="optional_for_management_mode")
    else:
        step1_ready = s1["status"] == _READY
        step2_ready = s2["status"] == _READY
        coverage_ok = locked_coverage_count >= 1
        if step1_ready and step2_ready and coverage_ok:
            s9 = _step(9, "review_activate", "Review & activate", _READY,
                       gate_class="hard", evidence_scope="exam_wide")
        elif not step1_ready or not step2_ready:
            s9 = _step(9, "review_activate", "Review & activate", _MISSING,
                       gate_class="hard", evidence_scope="exam_wide",
                       note="Hard gates (cycle details, phases) must be ready first")
        else:
            s9 = _step(9, "review_activate", "Review & activate", _REVIEW_PENDING,
                       gate_class="hard", evidence_scope="exam_wide",
                       note="Syllabus coverage must be locked")
    steps.append(s9)

    return {
        "cycle_id": cycle_id,
        "computed_at": computed_at,
        "steps": steps,
    }
