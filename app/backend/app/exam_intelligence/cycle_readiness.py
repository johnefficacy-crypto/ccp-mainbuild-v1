"""Cycle activation checklist — nine-step readiness derivation (I9).

``compute_cycle_readiness`` is the single authority for deriving each step's
status from live DB state.  Any unhandled exception propagates to the caller;
the outer ``_safe()`` in management_read_model returns cycle_readiness=null
(D16/A7 unavailable state) rather than fabricating missing evidence status.

Architecture gate refs: D01-D16.
Decision records implemented: D05, D06, D07, D08, D10, D11, D12, D14, D15, A1, A2.
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

# D05: index_only REQUIRES source provenance — only archive gets N/A for source_documents.
# D14: management modes are core, light, index_only, archive.
_MGMT_MODES_NO_DOCS = ("archive",)  # only archive skips document steps

# D12: only core and light get the real review_activate check.
_MGMT_MODES_REVIEW_NA = ("index_only", "archive")


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


def _get_exam_doc_ids(sb, exam_id: str) -> list[str]:
    """Return document_asset ids owned by this exam (via metadata.exam_id)."""
    all_rows = (
        sb.table("document_assets")
        .select("id, metadata")
        .eq("scope", "admin_exam_intelligence")
        .limit(500)
        .execute()
        .data
        or []
    )
    return [
        r["id"]
        for r in all_rows
        if r.get("id") and (r.get("metadata") or {}).get("exam_id") == exam_id
    ]


def _latest_jobs_by_doc(sb, doc_ids: list[str], job_type: str) -> list[dict]:
    """D06: For each document_id, keep only the latest job by (created_at DESC, id DESC).

    Returns one job dict per document_id (only those that have at least one job
    of the requested type).
    """
    if not doc_ids:
        return []
    all_jobs = (
        sb.table("document_processing_jobs")
        .select("id, document_id, status, created_at")
        .eq("job_type", job_type)
        .in_("document_id", doc_ids)
        .execute()
        .data
        or []
    )
    # Group by document_id, keep latest by (created_at, id) descending.
    latest: dict[str, dict] = {}
    for job in all_jobs:
        doc_id = job.get("document_id")
        if not doc_id:
            continue
        existing = latest.get(doc_id)
        if existing is None:
            latest[doc_id] = job
        else:
            # Compare (created_at, id) — ISO timestamps sort lexicographically.
            j_key = (job.get("created_at", ""), job.get("id", ""))
            e_key = (existing.get("created_at", ""), existing.get("id", ""))
            if j_key > e_key:
                latest[doc_id] = job
    return list(latest.values())


def _resolve_coverage(sb, exam_id: str, cycle_id: str) -> int:
    """D08: Return locked coverage count after precedence resolution.

    Coverage scope = selected-cycle rows (exam_cycle_id = cycle_id) UNION
    exam-wide rows (exam_cycle_id IS NULL).  Per (exam_phase_id, topic_id) pair,
    selected-cycle row takes precedence over exam-wide row.  Count only rows
    with reviewer_status = 'locked' after precedence resolution.
    """
    # Fetch all rows for this exam; split cycle-scoped vs exam-wide in Python
    # to avoid relying on IS NULL PostgREST syntax in test stubs.
    all_rows = (
        sb.table("exam_topic_coverage")
        .select("exam_cycle_id, exam_phase_id, topic_id, reviewer_status")
        .eq("exam_id", exam_id)
        .execute()
        .data
        or []
    )
    cycle_rows = [r for r in all_rows if r.get("exam_cycle_id") == cycle_id]
    wide_rows = [r for r in all_rows if r.get("exam_cycle_id") is None]

    # Build precedence map: cycle-scoped takes priority over exam-wide.
    resolved: dict[tuple, str] = {}
    for r in wide_rows:
        key = (r.get("exam_phase_id"), r.get("topic_id"))
        resolved[key] = r.get("reviewer_status", "")
    for r in cycle_rows:
        key = (r.get("exam_phase_id"), r.get("topic_id"))
        resolved[key] = r.get("reviewer_status", "")  # overrides wide

    return sum(1 for status in resolved.values() if status == "locked")


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

    # -------------------------------------------------------------------------
    # Step 1: cycle_details
    # A1: No-cycle persistent checklist — step 1 = missing with CTA.
    # -------------------------------------------------------------------------
    if not cycle_id:
        s1 = _step(
            1, "cycle_details", "Cycle details", _MISSING,
            gate_class="hard", evidence_scope="selected_cycle",
            action_cta={"label": "Go to Setup", "url": f"/admin/exam-intelligence/exams/{exam_id}?tab=setup"},
        )
    else:
        rows = (
            sb.table("exam_cycles")
            .select("id, cycle_name, year, status")
            .eq("id", cycle_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        cycle_row = rows[0] if rows else None
        if cycle_row and cycle_row.get("cycle_name") and cycle_row.get("year") is not None:
            s1 = _step(
                1, "cycle_details", "Cycle details", _READY,
                gate_class="hard", evidence_scope="selected_cycle",
            )
        else:
            s1 = _step(
                1, "cycle_details", "Cycle details", _MISSING,
                gate_class="hard", evidence_scope="selected_cycle",
                action_cta={"label": "Go to Setup", "url": f"/admin/exam-intelligence/exams/{exam_id}?tab=setup"},
            )
    steps.append(s1)

    # -------------------------------------------------------------------------
    # Step 2: phases_schedule
    # A1: No-cycle → not_applicable with no_selected_cycle.
    # -------------------------------------------------------------------------
    if not cycle_id:
        s2 = _step(
            2, "phases_schedule", "Phases schedule", _NA,
            gate_class="hard", evidence_scope="selected_cycle",
            not_applicable_reason="no_selected_cycle",
        )
    else:
        phase_rows = (
            sb.table("exam_phases")
            .select("id")
            .eq("exam_cycle_id", cycle_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        if phase_rows:
            s2 = _step(
                2, "phases_schedule", "Phases schedule", _READY,
                gate_class="hard", evidence_scope="selected_cycle",
            )
        else:
            s2 = _step(
                2, "phases_schedule", "Phases schedule", _MISSING,
                gate_class="hard", evidence_scope="selected_cycle",
                action_cta={"label": "Add phase", "url": f"/admin/exam-intelligence/exams/{exam_id}?tab=setup"},
            )
    steps.append(s2)

    # A2: When cycle_id present but no phases exist, steps 3-9 cascade to not_applicable.
    no_phases = bool(cycle_id and s2["status"] != _READY)

    # -------------------------------------------------------------------------
    # Step 3: source_documents
    # D05: index_only REQUIRES source provenance — only archive gets N/A here.
    # D06: Deterministic latest-per-document check for processed status.
    # A1/A2: no-cycle or no-phases → not_applicable.
    # -------------------------------------------------------------------------
    if not cycle_id or no_phases:
        s3 = _step(
            3, "source_documents", "Source documents", _NA,
            gate_class="advisory", evidence_scope="exam_wide",
            not_applicable_reason="no_selected_cycle",
        )
    elif management_mode in _MGMT_MODES_NO_DOCS:
        # D05: only archive gets N/A.
        s3 = _step(
            3, "source_documents", "Source documents", _NA,
            gate_class="advisory", evidence_scope="exam_wide",
            not_applicable_reason="optional_for_management_mode",
        )
    else:
        doc_ids = _get_exam_doc_ids(sb, exam_id)
        if not doc_ids:
            s3 = _step(
                3, "source_documents", "Source documents", _MISSING,
                gate_class="advisory", evidence_scope="exam_wide",
            )
        else:
            # Check asset status first, then fall back to latest-per-doc job status (D06).
            asset_rows = (
                sb.table("document_assets")
                .select("id, status, metadata")
                .eq("scope", "admin_exam_intelligence")
                .limit(500)
                .execute()
                .data
                or []
            )
            doc_id_set = set(doc_ids)
            exam_assets = [r for r in asset_rows if r.get("id") in doc_id_set]
            processed = any(d.get("status") == "processed" for d in exam_assets)
            if not processed:
                latest_jobs = _latest_jobs_by_doc(sb, doc_ids, "text_extract")
                processed = any(j.get("status") == "succeeded" for j in latest_jobs)
            if processed:
                s3 = _step(
                    3, "source_documents", "Source documents", _READY,
                    gate_class="advisory", evidence_scope="exam_wide",
                )
            else:
                s3 = _step(
                    3, "source_documents", "Source documents", _UPLOADED,
                    gate_class="advisory", evidence_scope="exam_wide",
                )
    steps.append(s3)

    # -------------------------------------------------------------------------
    # Step 4: extraction
    # D06: Deterministic latest-per-document extraction.
    #   One success among latest-per-doc = step ready.
    #   Remaining failures on latest jobs = advisory only (don't block ready).
    # A1/A2: no-cycle or no-phases → not_applicable.
    # -------------------------------------------------------------------------
    if not cycle_id or no_phases:
        s4 = _step(
            4, "extraction", "Text extraction", _NA,
            gate_class="advisory", evidence_scope="exam_wide",
            not_applicable_reason="no_selected_cycle",
        )
    elif management_mode in _MGMT_MODES_NO_DOCS:
        s4 = _step(
            4, "extraction", "Text extraction", _NA,
            gate_class="advisory", evidence_scope="exam_wide",
            not_applicable_reason="optional_for_management_mode",
        )
    else:
        doc_ids = _get_exam_doc_ids(sb, exam_id)
        if not doc_ids:
            s4 = _step(
                4, "extraction", "Text extraction", _MISSING,
                gate_class="advisory", evidence_scope="exam_wide",
            )
        else:
            # D06: latest-per-document, job_type=text_extract.
            latest_jobs = _latest_jobs_by_doc(sb, doc_ids, "text_extract")
            if not latest_jobs:
                s4 = _step(
                    4, "extraction", "Text extraction", _UPLOADED,
                    gate_class="advisory", evidence_scope="exam_wide",
                )
            else:
                statuses = [j.get("status") for j in latest_jobs]
                # D06: ONE success = step ready; failures on other docs are advisory only.
                if "succeeded" in statuses:
                    s4 = _step(
                        4, "extraction", "Text extraction", _READY,
                        gate_class="advisory", evidence_scope="exam_wide",
                    )
                elif any(s in statuses for s in ("queued", "running")):
                    s4 = _step(
                        4, "extraction", "Text extraction", _EXTRACTING,
                        gate_class="advisory", evidence_scope="exam_wide",
                    )
                elif "needs_review" in statuses:
                    s4 = _step(
                        4, "extraction", "Text extraction", _REVIEW_PENDING,
                        gate_class="advisory", evidence_scope="exam_wide",
                    )
                elif "failed" in statuses:
                    s4 = _step(
                        4, "extraction", "Text extraction", _FAILED,
                        gate_class="advisory", evidence_scope="exam_wide",
                        action_cta={"label": "View documents", "url": f"/admin/exam-intelligence/exams/{exam_id}?tab=documents"},
                    )
                else:
                    s4 = _step(
                        4, "extraction", "Text extraction", _MISSING,
                        gate_class="advisory", evidence_scope="exam_wide",
                    )
    steps.append(s4)

    # -------------------------------------------------------------------------
    # Step 5: syllabus_mapping
    # D07: Hard gate = locked_coverage_count >= 1 (from D08 resolution).
    #      Advisory = pending mention reviews (separate from hard gate).
    #      Status: locked=0 → missing; locked>=1 + pending → review_pending (advisory);
    #              locked>=1 + no pending → ready (hard).
    # D08: Coverage scope uses precedence resolution via _resolve_coverage().
    # A1/A2: no-cycle or no-phases → not_applicable.
    # -------------------------------------------------------------------------
    locked_coverage_count = 0

    if not cycle_id or no_phases:
        s5 = _step(
            5, "syllabus_mapping", "Syllabus mapping", _NA,
            gate_class="hard", evidence_scope="mixed",
            not_applicable_reason="no_selected_cycle",
        )
    else:
        # D08: precedence-resolved locked count (cycle-scoped + exam-wide).
        locked_coverage_count = _resolve_coverage(sb, exam_id, cycle_id)

        if locked_coverage_count == 0:
            # D07: Hard gate: locked=0 → missing.
            s5 = _step(
                5, "syllabus_mapping", "Syllabus mapping", _MISSING,
                gate_class="hard", evidence_scope="mixed",
            )
        else:
            # D07: Advisory check: pending mention reviews.
            mention_rows = (
                sb.table("syllabus_topic_mentions")
                .select("id, reviewer_status")
                .eq("exam_id", exam_id)
                .execute()
                .data
                or []
            )
            pending_mentions = sum(
                1 for m in mention_rows
                if m.get("reviewer_status") in ("pending", "needs_correction")
            )
            if pending_mentions > 0:
                # locked>=1 but pending mentions → review_pending (advisory gate_class per D07).
                s5 = _step(
                    5, "syllabus_mapping", "Syllabus mapping", _REVIEW_PENDING,
                    gate_class="advisory", evidence_scope="mixed",
                )
            else:
                # locked>=1 and no pending → ready (hard gate_class per D07).
                s5 = _step(
                    5, "syllabus_mapping", "Syllabus mapping", _READY,
                    gate_class="hard", evidence_scope="mixed",
                )
    steps.append(s5)

    # -------------------------------------------------------------------------
    # Step 6: pyq_readiness
    # D10: PYQ three-gate: verified paper → verified question → verified topic_tag.
    #      ONE fully verified chain (paper→question→tag all verified) = ready.
    #      Pending items don't downgrade if any verified chain exists.
    # A1/A2: no-cycle or no-phases → not_applicable.
    # -------------------------------------------------------------------------
    if not cycle_id or no_phases:
        s6 = _step(
            6, "pyq_readiness", "PYQ readiness", _NA,
            gate_class="advisory", evidence_scope="exam_wide",
            not_applicable_reason="no_selected_cycle",
        )
    else:
        paper_rows = (
            sb.table("pyq_papers")
            .select("id")
            .eq("exam_id", exam_id)
            .eq("trust_status", "verified")
            .execute()
            .data
            or []
        )
        verified_paper_ids = [p["id"] for p in paper_rows if p.get("id")]
        if not verified_paper_ids:
            s6 = _step(
                6, "pyq_readiness", "PYQ readiness", _MISSING,
                gate_class="advisory", evidence_scope="exam_wide",
            )
        else:
            q_rows = (
                sb.table("pyq_questions")
                .select("id, reviewer_status")
                .in_("pyq_paper_id", verified_paper_ids)
                .execute()
                .data
                or []
            )
            verified_q_ids = [
                q["id"] for q in q_rows
                if q.get("reviewer_status") == "verified" and q.get("id")
            ]
            if not verified_q_ids:
                s6 = _step(
                    6, "pyq_readiness", "PYQ readiness", _MISSING,
                    gate_class="advisory", evidence_scope="exam_wide",
                )
            else:
                tag_rows = (
                    sb.table("pyq_question_topic_tags")
                    .select("question_id, reviewer_status")
                    .in_("question_id", verified_q_ids)
                    .execute()
                    .data
                    or []
                )
                # D10: ONE fully verified chain (paper→question→tag all verified) = ready.
                verified_q_set = set(verified_q_ids)
                verified_tagged_q_ids = {
                    t["question_id"]
                    for t in tag_rows
                    if t.get("reviewer_status") == "verified"
                    and t.get("question_id") in verified_q_set
                }
                if verified_tagged_q_ids:
                    # At least one full chain exists → ready regardless of pending items.
                    s6 = _step(
                        6, "pyq_readiness", "PYQ readiness", _READY,
                        gate_class="advisory", evidence_scope="exam_wide",
                    )
                else:
                    # Verified questions exist but none have a verified tag.
                    pending_tags = any(
                        t.get("reviewer_status") in ("pending", "needs_correction") for t in tag_rows
                    )
                    pending_qs = any(
                        q.get("reviewer_status") in ("pending", "needs_correction") for q in q_rows
                    )
                    if pending_qs or pending_tags:
                        s6 = _step(
                            6, "pyq_readiness", "PYQ readiness", _REVIEW_PENDING,
                            gate_class="advisory", evidence_scope="exam_wide",
                        )
                    else:
                        s6 = _step(
                            6, "pyq_readiness", "PYQ readiness", _MISSING,
                            gate_class="advisory", evidence_scope="exam_wide",
                        )
    steps.append(s6)

    # -------------------------------------------------------------------------
    # Step 7: policy_updates
    # Scope: cycle-scoped rows + exam-wide rows (exam_cycle_id IS NULL).
    # A1/A2: no-cycle or no-phases → not_applicable.
    # -------------------------------------------------------------------------
    if not cycle_id or no_phases:
        s7 = _step(
            7, "policy_updates", "Policy updates", _NA,
            gate_class="advisory", evidence_scope="mixed",
            not_applicable_reason="no_selected_cycle",
        )
    else:
        pu_rows = (
            sb.table("exam_policy_updates")
            .select("id, reviewer_status, exam_cycle_id")
            .eq("exam_id", exam_id)
            .execute()
            .data
            or []
        )
        relevant = [
            r for r in pu_rows
            if r.get("exam_cycle_id") == cycle_id or r.get("exam_cycle_id") is None
        ]
        pending_pu = any(r.get("reviewer_status") in ("pending", "needs_correction") for r in relevant)
        if pending_pu:
            s7 = _step(
                7, "policy_updates", "Policy updates", _REVIEW_PENDING,
                gate_class="advisory", evidence_scope="mixed",
            )
        else:
            s7 = _step(
                7, "policy_updates", "Policy updates", _READY,
                gate_class="advisory", evidence_scope="mixed",
            )
    steps.append(s7)

    # -------------------------------------------------------------------------
    # Step 8: competition_context
    # D11: Scoped to selected cycle only (exam_cycle_id = cycle_id).
    #      If no cycle selected → not_applicable with no_selected_cycle.
    # A1/A2: no-cycle or no-phases → not_applicable.
    # -------------------------------------------------------------------------
    if not cycle_id or no_phases:
        s8 = _step(
            8, "competition_context", "Competition context", _NA,
            gate_class="advisory", evidence_scope="exam_wide",
            not_applicable_reason="no_selected_cycle",
        )
    else:
        # D11: cycle-scoped query only.
        comp_rows = (
            sb.table("exam_competition_metrics")
            .select("id, reviewer_status")
            .eq("exam_id", exam_id)
            .eq("exam_cycle_id", cycle_id)
            .execute()
            .data
            or []
        )
        reviewed = [r for r in comp_rows if r.get("reviewer_status") in ("reviewed", "locked")]
        if reviewed:
            s8 = _step(
                8, "competition_context", "Competition context", _READY,
                gate_class="advisory", evidence_scope="exam_wide",
            )
        else:
            s8 = _step(
                8, "competition_context", "Competition context", _MISSING,
                gate_class="advisory", evidence_scope="exam_wide",
            )
    steps.append(s8)

    # -------------------------------------------------------------------------
    # Step 9: review_activate
    # D12: only core and light modes get the real check.
    #      index_only and archive → not_applicable with optional_for_management_mode.
    #      Minimum: cycle_details ready + phases_schedule ready + >=1 locked coverage row.
    # A1/A2: no-cycle or no-phases → not_applicable.
    # -------------------------------------------------------------------------
    if not cycle_id or no_phases:
        s9 = _step(
            9, "review_activate", "Review & activate", _NA,
            gate_class="hard", evidence_scope="exam_wide",
            not_applicable_reason="no_selected_cycle",
        )
    elif management_mode in _MGMT_MODES_REVIEW_NA:
        # D12: index_only and archive → not_applicable.
        s9 = _step(
            9, "review_activate", "Review & activate", _NA,
            gate_class="hard", evidence_scope="exam_wide",
            not_applicable_reason="optional_for_management_mode",
        )
    else:
        # D12: core and light — minimum gates.
        step1_ready = s1["status"] == _READY
        step2_ready = s2["status"] == _READY
        coverage_ok = locked_coverage_count >= 1
        if step1_ready and step2_ready and coverage_ok:
            s9 = _step(
                9, "review_activate", "Review & activate", _READY,
                gate_class="hard", evidence_scope="exam_wide",
            )
        elif not step1_ready or not step2_ready:
            s9 = _step(
                9, "review_activate", "Review & activate", _MISSING,
                gate_class="hard", evidence_scope="exam_wide",
                note="Hard gates (cycle details, phases) must be ready first",
            )
        else:
            s9 = _step(
                9, "review_activate", "Review & activate", _REVIEW_PENDING,
                gate_class="hard", evidence_scope="exam_wide",
                note="Syllabus coverage must be locked",
            )
    steps.append(s9)

    return {
        "cycle_id": cycle_id,
        "computed_at": computed_at,
        "steps": steps,
    }
