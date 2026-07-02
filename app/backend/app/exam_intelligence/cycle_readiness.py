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

from app.exam_intelligence.pyq_readiness import aggregate_pyq_evidence

logger = logging.getLogger("career_copilot.exam_intelligence.cycle_readiness")

_MISSING = "missing"
_UPLOADED = "uploaded"
_EXTRACTING = "extracting"
_REVIEW_PENDING = "review_pending"
_READY = "ready"
_STALE = "stale"
_FAILED = "failed"
_NA = "not_applicable"

# D05: index_only REQUIRES source provenance — only archive skips source docs.
# D14: management modes are core, light, index_only, archive.
_MGMT_MODES_NO_DOCS = ("archive",)          # D05: only archive skips source docs

# D12: index_only and archive skip review_activate.
_MGMT_MODES_NO_ACTIVATE = ("index_only", "archive")  # D12: these skip review_activate

# D11: light, index_only, archive skip competition_context.
_MGMT_MODES_COMPETITION_NA = ("light", "index_only", "archive")  # D11

# D05 §1 / D12: canonical classified phase kinds. `NULL` and `'other'` are UNCLASSIFIED
# (D05: "requires operator classification before a blocking policy is applied") and therefore
# never count toward required-phase completeness. The 7 concrete kinds below are the classified
# set. (Deeper per-phase evidence-policy completeness — syllabus/pattern/PYQ/answer-key per
# phase_kind, D05 §2–5 policy tables — is the separate D05 evidence-engine contract, gated on
# D06/D08; D12's required-phase-completeness gate at this layer is canonical CLASSIFICATION.)
_CLASSIFIED_PHASE_KINDS = (
    "objective_written", "descriptive_written", "mixed_written",
    "interview", "physical_test", "medical", "document_verification",
)


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
    checks=None,
    applicability: str | None = None,
    metrics=None,
) -> dict[str, Any]:
    # D14: derive applicability from gate_class when not explicitly provided.
    if applicability is None:
        applicability = "required" if gate_class == "hard" else "conditional"
    return {
        "step": n,
        "step_id": key,       # canonical name per contract
        "key": key,           # backward compat alias
        "label": label,
        "status": status,
        "gate_class": gate_class,
        "evidence_scope": evidence_scope,
        "not_applicable_reason": not_applicable_reason,
        "action_cta": action_cta,
        "note": note,
        "checks": checks or [],
        "applicability": applicability,
        "metrics": metrics or {},
    }


def _na_step(
    n: int,
    key: str,
    label: str,
    reason: str | None,
    *,
    gate_class: str,
    evidence_scope: str,
    note: str | None = None,
) -> dict[str, Any]:
    return _step(
        n, key, label, _NA,
        gate_class=gate_class, evidence_scope=evidence_scope,
        not_applicable_reason=reason,
        applicability="not_applicable",
        note=note,
    )


_PAGE = 500


def _get_exam_doc_ids(sb, exam_id: str, cycle_id: str | None = None) -> list[str]:
    """Return document_asset ids owned by this exam (via metadata.exam_id).

    Cycle isolation (D05 fail-closed): when cycle_id is provided, only include
    docs explicitly tagged to that cycle (metadata.exam_cycle_id == cycle_id).
    Unscoped docs (exam_cycle_id absent/None) are excluded — the upload API
    makes exam_cycle_id optional and an unscoped doc must not satisfy a
    different cycle's readiness.  Docs tagged to a different cycle are also
    excluded.  Uses paged queries (500 at a time).
    """
    all_rows: list[dict] = []
    offset = 0
    while True:
        batch = (
            sb.table("document_assets")
            .select("id, metadata")
            .eq("scope", "admin_exam_intelligence")
            .range(offset, offset + _PAGE - 1)
            .execute()
            .data
            or []
        )
        all_rows.extend(batch)
        if len(batch) < _PAGE:
            break
        offset += _PAGE

    result = []
    for r in all_rows:
        if not r.get("id"):
            continue
        meta = r.get("metadata") or {}
        if meta.get("exam_id") != exam_id:
            continue
        if cycle_id is not None:
            doc_cycle = meta.get("exam_cycle_id")
            # D05 fail-closed: when a cycle is selected, only count documents
            # explicitly tagged to that cycle.  Unscoped documents (doc_cycle is
            # None) are NOT inherited — the upload API makes exam_cycle_id optional
            # and a cycle-specific document uploaded without cycle metadata must not
            # satisfy a different cycle's readiness.  Canonical exam-wide evidence
            # roles are a future D05 registration concern.
            if doc_cycle != cycle_id:
                continue
        result.append(r["id"])
    return result


def _latest_jobs_by_doc(sb, doc_ids: list[str], job_type: str) -> dict[str, str]:
    """D06: For each document_id, keep only the latest job by (created_at DESC, id DESC).

    Returns dict[doc_id -> status] (only for documents that have at least one job
    of the requested type).
    """
    if not doc_ids:
        return {}
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
    return {doc_id: job.get("status", "") for doc_id, job in latest.items()}


def _resolve_coverage(sb, exam_id: str, cycle_id: str) -> dict[str, Any]:
    """D08: Return coverage metrics after precedence resolution.

    Coverage scope = selected-cycle rows (exam_cycle_id = cycle_id) UNION
    exam-wide rows (exam_cycle_id IS NULL).  Per (exam_phase_id, topic_id) pair,
    selected-cycle row takes precedence over exam-wide row.  Count only rows
    with reviewer_status = 'locked' after precedence resolution.

    Returns dict with keys: cycle_specific_rows, exam_wide_rows, effective_rows, locked_rows.
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

    locked_rows = sum(1 for status in resolved.values() if status == "locked")
    return {
        "cycle_specific_rows": len(cycle_rows),
        "exam_wide_rows": len(wide_rows),
        "effective_rows": len(resolved),
        "locked_rows": locked_rows,
    }


def compute_cycle_readiness(
    sb,
    exam_id: str,
    cycle_id: str | None,
    exam: dict[str, Any],
    *,
    activation_verdict: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute the nine-step cycle activation checklist.

    Each step is read fail-soft: errors yield status="missing" and continue.
    """
    computed_at = _now_iso()
    management_mode = (exam or {}).get("management_mode", "")
    steps: list[dict[str, Any]] = []
    # D12/D14: canonical planner/Study-OS exposure authority for the SELECTED cycle
    # (migration 209, `exam_cycles.planner_activation_enabled`). Captured in Step 1 and
    # consumed by Step 9 to decide `light` applicability. Fail-closed default: not exposed.
    planner_exposed = False

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
            .select("id, cycle_name, year, status, planner_activation_enabled")
            .eq("id", cycle_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        cycle_row = rows[0] if rows else None
        planner_exposed = bool((cycle_row or {}).get("planner_activation_enabled"))
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
    # A1: No-cycle -> not_applicable with no_selected_cycle.
    # -------------------------------------------------------------------------
    if not cycle_id:
        s2 = _na_step(
            2, "phases_schedule", "Phases schedule", "no_selected_cycle",
            gate_class="hard", evidence_scope="selected_cycle",
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

    # A1/A2 cascade: if no cycle selected, or cycle has no phases, steps 3-9 = not_applicable.
    no_cycle = not cycle_id
    no_phases = bool(cycle_id) and s2["status"] != _READY

    if no_cycle or no_phases:
        def _cascade_na(n, key, label, gate_class, ev_scope):
            if no_cycle:
                return _na_step(n, key, label, "no_selected_cycle",
                                gate_class=gate_class, evidence_scope=ev_scope)
            else:  # no_phases — D15: must have typed reason
                return _na_step(n, key, label, "no_phases_in_cycle",
                                gate_class=gate_class, evidence_scope=ev_scope,
                                note="No phases defined for selected cycle")

        steps += [
            _cascade_na(3, "source_documents", "Source documents", "advisory", "exam_wide"),
            _cascade_na(4, "extraction", "Text extraction", "advisory", "exam_wide"),
            _cascade_na(5, "syllabus_mapping", "Syllabus mapping", "hard", "mixed"),
            _cascade_na(6, "pyq_readiness", "PYQ readiness", "advisory", "exam_wide"),
            _cascade_na(7, "policy_updates", "Policy updates", "advisory", "mixed"),
            _cascade_na(8, "competition_context", "Competition context", "advisory", "exam_wide"),
            _cascade_na(9, "review_activate", "Review & activate", "hard", "exam_wide"),
        ]
        return {"cycle_id": cycle_id, "computed_at": computed_at, "steps": steps}

    # -------------------------------------------------------------------------
    # Step 3: source_documents
    # D05: index_only REQUIRES source provenance — only archive gets N/A here.
    # A1/A2: handled above via cascade.
    # -------------------------------------------------------------------------
    if management_mode in _MGMT_MODES_NO_DOCS:
        # D05: only archive gets N/A.
        s3 = _na_step(
            3, "source_documents", "Source documents", "optional_for_management_mode",
            gate_class="advisory", evidence_scope="exam_wide",
        )
    else:
        doc_ids = _get_exam_doc_ids(sb, exam_id, cycle_id)
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
                latest_by_doc = _latest_jobs_by_doc(sb, doc_ids, "text_extract")
                processed = any(s == "succeeded" for s in latest_by_doc.values())
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
    #   Docs with no jobs at all -> not started (not failed).
    # A1/A2: handled above via cascade.
    # -------------------------------------------------------------------------
    if management_mode in _MGMT_MODES_NO_DOCS:
        s4 = _na_step(
            4, "extraction", "Text extraction", "optional_for_management_mode",
            gate_class="advisory", evidence_scope="exam_wide",
        )
    else:
        doc_ids = _get_exam_doc_ids(sb, exam_id, cycle_id)
        if not doc_ids:
            s4 = _step(
                4, "extraction", "Text extraction", _MISSING,
                gate_class="advisory", evidence_scope="exam_wide",
            )
        else:
            # D06: latest-per-document, job_type=text_extract.
            latest_by_doc = _latest_jobs_by_doc(sb, doc_ids, "text_extract")
            docs_with_jobs = set(latest_by_doc.keys())
            docs_without_jobs = [d for d in doc_ids if d not in docs_with_jobs]
            latest_statuses = list(latest_by_doc.values())

            if any(s == "succeeded" for s in latest_statuses):
                # D06: ONE success = step ready; failures on other docs are advisory only.
                s4 = _step(
                    4, "extraction", "Text extraction", _READY,
                    gate_class="advisory", evidence_scope="exam_wide",
                )
            elif any(s == "needs_review" for s in latest_statuses):
                # D06: review_pending > extracting > uploaded > missing
                s4 = _step(
                    4, "extraction", "Text extraction", _REVIEW_PENDING,
                    gate_class="advisory", evidence_scope="exam_wide",
                )
            elif any(s in ("queued", "running") for s in latest_statuses):
                s4 = _step(
                    4, "extraction", "Text extraction", _EXTRACTING,
                    gate_class="advisory", evidence_scope="exam_wide",
                )
            elif docs_without_jobs:
                # Some docs have no jobs -> not started yet (not failed)
                s4 = _step(
                    4, "extraction", "Text extraction", _UPLOADED,
                    gate_class="advisory", evidence_scope="exam_wide",
                )
            elif latest_statuses and all(s == "failed" for s in latest_statuses):
                s4 = _step(
                    4, "extraction", "Text extraction", _FAILED,
                    gate_class="advisory", evidence_scope="exam_wide",
                    action_cta={"label": "View documents", "url": f"/admin/exam-intelligence/exams/{exam_id}?tab=documents"},
                )
            else:
                s4 = _step(
                    4, "extraction", "Text extraction", _UPLOADED,
                    gate_class="advisory", evidence_scope="exam_wide",
                )
    steps.append(s4)

    # -------------------------------------------------------------------------
    # Step 5: syllabus_mapping
    # D07: Hard gate = locked_coverage_count >= 1 (from D08 resolution).
    #      Advisory = pending mention reviews (separate from hard gate).
    #      Status: locked=0 -> missing; locked>=1 + pending -> review_pending (advisory);
    #              locked>=1 + no pending -> ready (hard).
    # D08: Coverage scope uses precedence resolution via _resolve_coverage().
    # A1/A2: handled above via cascade.
    # -------------------------------------------------------------------------
    coverage_metrics: dict[str, Any] = {}

    # D08: precedence-resolved locked count (cycle-scoped + exam-wide).
    coverage_metrics = _resolve_coverage(sb, exam_id, cycle_id)
    locked_count = coverage_metrics["locked_rows"]

    mention_rows = (
        sb.table("syllabus_topic_mentions")
        .select("id, reviewer_status")
        .eq("exam_id", exam_id)
        .execute()
        .data
        or []
    )
    pending_count = sum(
        1 for m in mention_rows
        if m.get("reviewer_status") in ("pending", "needs_correction")
    )

    checks = [
        {"check_id": "locked_coverage", "gate_class": "hard",
         "status": _READY if locked_count >= 1 else _MISSING, "locked_count": locked_count},
        {"check_id": "mention_review", "gate_class": "advisory",
         "status": _REVIEW_PENDING if pending_count > 0 else _READY, "pending_count": pending_count},
    ]

    if locked_count == 0:
        s5 = _step(
            5, "syllabus_mapping", "Syllabus mapping", _MISSING,
            gate_class="hard", evidence_scope="mixed",
            checks=checks, metrics=coverage_metrics,
        )
    elif pending_count > 0:
        s5 = _step(
            5, "syllabus_mapping", "Syllabus mapping", _REVIEW_PENDING,
            gate_class="advisory", evidence_scope="mixed",
            checks=checks, metrics=coverage_metrics,
        )
    else:
        s5 = _step(
            5, "syllabus_mapping", "Syllabus mapping", _READY,
            gate_class="hard", evidence_scope="mixed",
            checks=checks, metrics=coverage_metrics,
        )
    steps.append(s5)

    # -------------------------------------------------------------------------
    # Step 6: pyq_readiness
    # D10: Use canonical aggregate_pyq_evidence (exam-wide, NOT cycle-scoped).
    # A1/A2: handled above via cascade.
    # -------------------------------------------------------------------------
    # Fetch data for exam-wide PYQ (D10: NOT cycle-scoped)
    papers = (
        sb.table("pyq_papers")
        .select("id, exam_cycle_id, trust_status")
        .eq("exam_id", exam_id)
        .execute()
        .data
        or []
    )
    paper_ids = [p["id"] for p in papers if p.get("id")]
    questions: list[dict] = []
    tags: list[dict] = []
    if paper_ids:
        questions = (
            sb.table("pyq_questions")
            .select("id, pyq_paper_id, reviewer_status")
            .in_("pyq_paper_id", paper_ids)
            .execute()
            .data
            or []
        )
        q_ids = [q["id"] for q in questions if q.get("id")]
        if q_ids:
            tags = (
                sb.table("pyq_question_topic_tags")
                .select("id, question_id, reviewer_status")
                .in_("question_id", q_ids)
                .execute()
                .data
                or []
            )

    pyq = aggregate_pyq_evidence(
        papers=papers, questions=questions, topic_tags=tags, selected_cycle_id=cycle_id
    )
    pyq_status = pyq.get("state", _MISSING)
    s6 = _step(
        6, "pyq_readiness", "PYQ readiness", pyq_status,
        gate_class="advisory", evidence_scope="exam_wide",
        metrics={
            "verified_question_count": pyq.get("verified_question_count", 0),
            "questions_total": pyq.get("questions_total", 0),
            "pending_question_count": pyq.get("pending_question_count", 0),
        },
    )
    steps.append(s6)

    # -------------------------------------------------------------------------
    # Step 7: policy_updates
    # Scope: cycle-scoped rows + exam-wide rows (exam_cycle_id IS NULL).
    # A1/A2: handled above via cascade.
    # -------------------------------------------------------------------------
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
    # D11: light/index_only/archive -> not_applicable.
    #      core: cycle-scoped check only.
    # A1/A2: handled above via cascade.
    # -------------------------------------------------------------------------
    if not management_mode:
        s8 = _step(
            8, "competition_context", "Competition context", _MISSING,
            gate_class="advisory", evidence_scope="selected_cycle",
            note="Management mode classification required",
        )
    else:
        # D11: query selected-cycle rows first — evidence must never be hidden.
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
            # Valid evidence exists — must become ready regardless of mode.
            s8 = _step(
                8, "competition_context", "Competition context", _READY,
                gate_class="advisory", evidence_scope="selected_cycle",
            )
        elif management_mode in _MGMT_MODES_COMPETITION_NA:
            # D11: only N/A when no valid evidence AND mode makes it optional.
            s8 = _na_step(
                8, "competition_context", "Competition context", "optional_for_management_mode",
                gate_class="advisory", evidence_scope="selected_cycle",
            )
        else:
            s8 = _step(
                8, "competition_context", "Competition context", _MISSING,
                gate_class="advisory", evidence_scope="selected_cycle",
            )
    steps.append(s8)

    # -------------------------------------------------------------------------
    # Step 9: review_activate  (D12 — selected-cycle activation minimum)
    #
    # Evaluates the D12 planner-activation minimum DIRECTLY for the SELECTED CYCLE (never the
    # exam-wide work_queue.classify_exam verdict, whose counts span every cycle):
    #     minimum = cycle_details_complete (s1)
    #               AND required_phases_complete (D05/D14)
    #               AND >=1 applicable locked coverage row (D08 selected-cycle + exam-wide).
    #
    # Required-phase COMPLETENESS (D12 "required phases complete", D05 §1): every non-cancelled
    # phase in the selected cycle carries a canonical, classified `phase_kind` (migration 209).
    # `NULL`/`'other'` are UNCLASSIFIED (D05: an active unclassified phase requires operator
    # action) and never count. Lifecycle `status` is NOT used as a completeness signal. (Deeper
    # per-phase evidence-policy completeness — D05 §2–5 policy tables — is the separate D05
    # evidence-engine contract, gated on D06/D08; this layer gates on canonical classification.)
    #
    # Mode applicability (D12/D14 matrix): index_only/archive -> not_applicable (N/A). `core`
    # -> required (always evaluated). `light` -> conditional: applicable ONLY when the selected
    # cycle is exposed to Study OS / planner activation (`exam_cycles.planner_activation_enabled`,
    # the canonical authority — NOT `exams.is_active`); when not exposed it is N/A
    # (planner_activation_disabled). `NULL` mode -> classification required.
    phase_rows = (
        sb.table("exam_phases").select("status, phase_kind").eq("exam_cycle_id", cycle_id).execute().data or []
    )
    _active_phases = [p for p in phase_rows if (p.get("status") or "") != "cancelled"]
    required_phases_complete = bool(_active_phases) and all(
        (p.get("phase_kind") or "") in _CLASSIFIED_PHASE_KINDS for p in _active_phases
    )
    _light_not_exposed = management_mode == "light" and not planner_exposed
    if management_mode in _MGMT_MODES_NO_ACTIVATE:
        # D14: review_activate is not_applicable for index_only/archive.
        s9 = _na_step(
            9, "review_activate", "Review & activate", "planner_activation_disabled",
            gate_class="hard", evidence_scope="selected_cycle_plus_exam_wide",
        )
    elif not management_mode:
        s9 = _step(
            9, "review_activate", "Review & activate", _MISSING,
            gate_class="hard", evidence_scope="selected_cycle_plus_exam_wide",
            applicability="required",
            note="Management mode classification required",
        )
    elif _light_not_exposed:
        # D12/D14: `light` review_activate is conditional; its condition (Study-OS/planner
        # exposure) is false, so it resolves to not_applicable with applicability=conditional.
        s9 = _step(
            9, "review_activate", "Review & activate", _NA,
            gate_class="hard", evidence_scope="selected_cycle_plus_exam_wide",
            applicability="conditional",
            not_applicable_reason="planner_activation_disabled",
        )
    else:
        # core (required), or light with exposure enabled (conditional, condition true).
        applicability = "conditional" if management_mode == "light" else "required"
        cycle_ok = s1["status"] == _READY
        coverage_ok = locked_count >= 1
        minimum_met = cycle_ok and required_phases_complete and coverage_ok
        # Locked deep-link contract: route the CTA to the first failed prerequisite, preserving
        # selected-cycle identity (?cycle=<id> so the blocker opens the cycle whose readiness
        # produced it). Phase classification is an operator action in the Setup tab.
        _base = f"/admin/exam-intelligence/exams/{exam_id}?cycle={cycle_id}"
        if minimum_met:
            cta = None
            note = None
        elif not cycle_ok:
            cta = {"label": "Complete setup", "url": f"{_base}&tab=setup"}
            note = "Selected-cycle activation prerequisites incomplete"
        elif not required_phases_complete:
            cta = {"label": "Classify exam phases", "url": f"{_base}&tab=setup"}
            note = "One or more phases are unclassified (missing canonical phase_kind)"
        else:  # coverage is the failure
            cta = {"label": "Review syllabus coverage", "url": f"{_base}&tab=syllabus"}
            note = "Selected-cycle activation prerequisites incomplete"
        s9 = _step(
            9, "review_activate", "Review & activate",
            _READY if minimum_met else _MISSING,
            gate_class="hard", evidence_scope="selected_cycle_plus_exam_wide",
            applicability=applicability,
            checks=[
                {"check_id": "cycle_details_complete", "gate_class": "hard", "status": s1["status"]},
                {"check_id": "required_phases_complete", "gate_class": "hard",
                 "status": _READY if required_phases_complete else _MISSING},
                {"check_id": "applicable_locked_coverage", "gate_class": "hard",
                 "status": _READY if coverage_ok else _MISSING, "locked_count": locked_count},
            ],
            note=note,
            action_cta=cta,
        )
    steps.append(s9)

    return {
        "cycle_id": cycle_id,
        "computed_at": computed_at,
        "steps": steps,
    }
