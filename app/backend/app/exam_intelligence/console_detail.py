"""Per-exam action console read (Wave 4.6I-BE) — read-only.

Backs GET /api/admin/exam-intelligence/console/exams/{exam_id}. Assembles a
single-exam activation view: verdict, advisory mock readiness, action queue,
activation checks, and stages — all from NAMED existing reads.

Status parity is load-bearing: ``activation_verdict.status`` is produced by the
SAME pure classifier the 4.6H list uses (``work_queue.classify_exam``) over the
SAME aggregate (``work_queue.aggregate(sb, [exam])``). There is no parallel
status rule here.

Reason parity: every classifier-owned blocker/flag has a matching non-publish
activation check + action item; ``activation_verdict.reasons`` are stable
semantic tokens derived from the classifier (never advisory areas). The
per-area pending detail comes from ``aggregate(..., include_details=True)`` so a
``needs_action`` verdict is always explained. The endpoint fails closed if a
non-ready status has no classifier-owned explanation.

Guards: no score_percent/confidence_score/confidence_percent leaves this module;
every correctness-critical read pages fully and uses ``execute_or_raise``
(failure → 5xx, never a fabricated verdict); unknown exam → 404. Read-only.

BUG-EI-2 final fix: document readiness is sourced from document_processing_jobs
(job_type='text_extract', latest job per asset). trust_status on
syllabus_documents is a human-review gate, not an extraction signal.
"""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from app.db.utils import execute_or_raise
from app.exam_intelligence import work_queue as _wq
from app.exam_intelligence.diagnostics import assemble_mock_readiness_report
from app.exam_intelligence.readiness import load_doc_extraction_counts, load_first_failing_doc_strict

# Mock-readiness inputs mirror the existing /exams/{id}/mock-readiness defaults.
_SELECTABLE_MOCK_STATUSES = ["verified", "published"]
_VERIFIED_STATUS = "verified"
_MIN_PER_SECTION = 30
_MIN_LOCKED_COVERAGE = 1

_AREA_ORDER = [
    "setup", "documents", "syllabus", "topic_coverage", "pyq",
    "updates", "competition", "mock_readiness", "publish",
]
_HARD_AREAS = {"setup", "topic_coverage", "publish"}
# Areas whose state is owned by the shared classifier (must explain a non-ready verdict).
_CLASSIFIER_AREAS = {"setup", "topic_coverage", "pyq", "syllabus", "updates"}

_STAGES = [
    {"id": "setup", "label": "Setup", "areas": ["setup", "documents"]},
    {"id": "evidence", "label": "Evidence", "areas": ["syllabus", "topic_coverage", "pyq"]},
    {"id": "review", "label": "Review", "areas": ["updates", "competition", "mock_readiness"]},
    {"id": "activation", "label": "Activation", "areas": ["publish"]},
]

_SEVERITY_RANK = {"blocker": 0, "action": 1, "advisory": 2}


def _check(area, gate, state, detail, reasons=None, evidence_refs=None) -> dict[str, Any]:
    return {"area": area, "gate": gate, "state": state, "detail": detail,
            "reasons": reasons or [], "evidence_refs": evidence_refs or []}


# ── Identity ────────────────────────────────────────────────────────────────

def _require_exam(sb, exam_id: str) -> dict[str, Any]:
    rows = execute_or_raise(
        "console_detail.exam",
        lambda: sb.table("exams")
        .select("id, slug, name, conducting_organization_id, exam_family_id")
        .eq("id", exam_id).limit(1).execute().data,
    ) or []
    if not rows:
        raise HTTPException(status_code=404, detail="exam not found")
    return rows[0]


def _family_name(sb, family_id: str | None) -> str | None:
    if not family_id:
        return None
    rows = execute_or_raise(
        "console_detail.family",
        lambda: sb.table("exam_families").select("id, name").eq("id", family_id).limit(1).execute().data,
    ) or []
    return rows[0].get("name") if rows else None


# ── Strict, paged per-area reads (areas not owned by the aggregate) ─────────

def _paged(sb, make_query, operation: str) -> list[dict[str, Any]]:
    return _wq._fetch_all_pages(make_query, operation=operation)




def _syllabus_verified_count(sb, exam_id: str) -> int:
    rows = _paged(
        sb,
        lambda: sb.table("syllabus_topic_mentions").select("id, reviewer_status")
        .eq("exam_id", exam_id).order("id"),
        "console_detail.syllabus",
    )
    return sum(1 for r in rows if r.get("reviewer_status") == "verified")


def _competition(sb, exam_id: str) -> dict[str, Any]:
    """Strict, paged read of reviewed/locked competition metrics. Selection
    precedence: locked over reviewed, then newest. Never reads confidence_score."""
    rows = _paged(
        sb,
        lambda: sb.table("exam_competition_metrics").select("id, reviewer_status, created_at")
        .eq("exam_id", exam_id).in_("reviewer_status", ["locked", "reviewed"]).order("id"),
        "console_detail.competition",
    )
    if not rows:
        return {"available": False, "row_id": None}
    locked = [r for r in rows if r.get("reviewer_status") == "locked"]
    pool = locked or rows
    best = max(pool, key=lambda r: r.get("created_at") or "")
    return {"available": True, "row_id": best.get("id")}


# ── Mock readiness (separate + advisory) ────────────────────────────────────

def _mock_readiness(sb, exam_id: str) -> dict[str, str]:
    report = assemble_mock_readiness_report(
        sb, exam_id=exam_id,
        selectable_statuses=_SELECTABLE_MOCK_STATUSES,
        verified_status=_VERIFIED_STATUS,
        min_per_section=_MIN_PER_SECTION,
        min_locked_coverage=_MIN_LOCKED_COVERAGE,
    )
    phases = report.get("phases") or []
    summary = {"ready": 0, "thin_bank": 0, "blocked": 0}
    counted = False
    for ph in phases:
        vs = (ph.get("readiness_verdict") or {}).get("summary") or {}
        for k in summary:
            val = int(vs.get(k, 0) or 0)
            summary[k] += val
            if val:
                counted = True
    if not phases or not counted:
        return {"status": "unknown", "detail": "Mock readiness not computable for this exam yet"}
    if summary["blocked"]:
        status = "blocked"
    elif summary["thin_bank"]:
        status = "thin_bank"
    else:
        status = "ready"
    detail = f"{summary['ready']} ready · {summary['thin_bank']} thin · {summary['blocked']} blocked section(s)"
    return {"status": status, "detail": detail}


# ── Action queue copy + entity kinds ────────────────────────────────────────

_ACTION_COPY = {
    "setup": ("Define exam phases", "Setup must exist before any activation work."),
    "documents": ("Upload & extract documents", "Source documents feed syllabus and PYQ evidence."),
    "syllabus": ("Review syllabus mentions", "Pending mentions are not yet usable evidence."),
    "topic_coverage": ("Lock topic coverage", "The planner consumes only locked coverage rows."),
    "pyq": ("Verify PYQ", "Questions need verified paper + question + topic tag."),
    "updates": ("Verify official updates", "Pending updates do not propagate."),
    "competition": ("Review competition metrics", "No reviewed competition signal exists yet."),
    "mock_readiness": ("Strengthen the mock bank", "Mock bank is thin or blocked (advisory only)."),
}

# Area-level entity kind. NULL for PYQ because a PYQ action's causal rows can be
# questions, tags, OR options — the precise kinds live in evidence_refs.
_AREA_ENTITY_KIND = {
    "topic_coverage": "exam_topic_coverage",
    "syllabus": "syllabus_topic_mention",
    "updates": "exam_policy_updates",
    "competition": "exam_competition_metrics",
    "documents": "document_assets",
    "setup": "exam_phases",
    "pyq": None,
    "mock_readiness": None,
}


def _first_evidence_by_kinds(evidence_refs: list[dict], kinds: set[str]) -> dict | None:
    """Return first evidence_ref whose kind is in the given set, or None."""
    return next((r for r in evidence_refs if r.get("kind") in kinds), None)


def _resolve_pyq_paper_id(
    sb, kind: str, row_id: str
) -> tuple[str | None, str | None]:
    """Resolve a PYQ evidence ref to (paper_id, question_id).

    - pyq_question: row_id is question → direct lookup
    - pyq_question_topic_tag: row_id is tag → lookup tag.question_id → lookup question
    - pyq_option: row_id is option → lookup option.question_id → lookup question

    Returns (paper_id, question_id) so the CTA can link to the question directly.
    """
    def _get_question(question_id: str) -> tuple[str | None, str | None]:
        rows = (
            sb.table("pyq_questions")
            .select("id, pyq_paper_id")
            .eq("id", question_id)
            .limit(1)
            .execute()
            .data
        ) or []
        if not rows:
            return None, None
        return rows[0].get("pyq_paper_id"), question_id

    if kind == "pyq_question":
        return _get_question(row_id)

    if kind == "pyq_question_topic_tag":
        tag_rows = (
            sb.table("pyq_question_topic_tags")
            .select("id, question_id")
            .eq("id", row_id)
            .limit(1)
            .execute()
            .data
        ) or []
        if not tag_rows:
            return None, None
        return _get_question(tag_rows[0].get("question_id") or "")

    if kind == "pyq_option":
        opt_rows = (
            sb.table("pyq_options")
            .select("id, question_id")
            .eq("id", row_id)
            .limit(1)
            .execute()
            .data
        ) or []
        if not opt_rows:
            return None, None
        return _get_question(opt_rows[0].get("question_id") or "")

    return None, None


def _severity_for(area: str, state: str) -> str:
    if area in _HARD_AREAS and state == "blocked":
        return "blocker"
    if area == "mock_readiness":
        return "advisory"
    return "action"


def _deep_link(
    area: str, exam_id: str, cycle_id: str | None,
    entity_row_id: str | None = None,
    paper_id: str | None = None,
    doc_status: str | None = None,
) -> tuple[str, str]:
    """Return (cta_label, cta_route) per the locked I8-B deep-link contract (design §7.2).

    Each area generates the exact task-state URL needed to land on the causal entity:
    - syllabus/topic_coverage: ?row={mention_or_coverage_id}
    - pyq: ?paper={paper_id}&row={question_id}
    - updates: ?row={update_id}
    - documents: ?document={doc_id}&status={failed|pending}
    """
    base = f"/admin/exam-intelligence/exams/{exam_id}"
    cyc = f"cycle={cycle_id}&" if cycle_id else ""
    row = f"&row={entity_row_id}" if entity_row_id else ""
    pap = f"&paper={paper_id}" if paper_id else ""
    doc_s = f"&status={doc_status}" if doc_status else ""
    doc_id_param = f"&document={entity_row_id}" if entity_row_id else ""
    _routes: dict[str, tuple[str, str]] = {
        "setup":          ("Go to Setup",             f"{base}?tab=setup"),
        "documents":      ("Go to Documents",          f"{base}?{cyc}tab=documents{doc_id_param}{doc_s}"),
        "syllabus":       ("Review pending mentions",  f"{base}?tab=syllabus&status=pending{row}"),
        "topic_coverage": ("Review unlocked rows",     f"{base}?tab=syllabus&status=pending_review{row}"),
        "pyq":            ("Review pending questions", f"{base}?{cyc}tab=pyq{pap}&status=pending{row}"),
        "updates":        ("Review pending updates",   f"{base}?tab=updates&status=pending{row}"),
        "competition":    ("Open competition",          f"{base}?{cyc}tab=competition"),
        "mock_readiness": ("Go to Review & Activate", f"{base}?tab=review"),
    }
    return _routes.get(area, ("Open workspace", base))


def _build_action_queue(sb, checks: list[dict[str, Any]], exam_id: str,
                        cycle_id: str | None = None) -> list[dict[str, Any]]:
    """Build the ordered action queue using kind-specific evidence selection."""
    items: list[dict[str, Any]] = []
    for chk in checks:
        area = chk["area"]
        if area == "publish" or chk["state"] in {"done", "unknown"}:
            continue
        title, why = _ACTION_COPY[area]
        evidence_refs = chk.get("evidence_refs", [])

        entity_row_id: str | None = None
        paper_id: str | None = None
        doc_status: str | None = None

        if area == "pyq":
            qref = _first_evidence_by_kinds(
                evidence_refs, {"pyq_question", "pyq_question_topic_tag", "pyq_option"}
            )
            if qref:
                try:
                    paper_id, entity_row_id = _resolve_pyq_paper_id(
                        sb, qref["kind"], qref["row_id"]
                    )
                except Exception:  # noqa: BLE001
                    paper_id = None
                    entity_row_id = qref["row_id"]
        elif area == "syllabus":
            ref = _first_evidence_by_kinds(evidence_refs, {"syllabus_topic_mention"})
            entity_row_id = ref["row_id"] if ref else None
        elif area == "topic_coverage":
            ref = _first_evidence_by_kinds(evidence_refs, {"exam_topic_coverage"})
            entity_row_id = ref["row_id"] if ref else None
        elif area == "updates":
            ref = _first_evidence_by_kinds(evidence_refs, {"exam_policy_updates"})
            entity_row_id = ref["row_id"] if ref else None
        elif area == "documents":
            ref = _first_evidence_by_kinds(evidence_refs, {"document_assets"})
            if ref:
                entity_row_id = ref["row_id"]
                doc_status = ref.get("extraction_status")
        else:
            entity_row_id = evidence_refs[0]["row_id"] if evidence_refs else None

        cta_label, cta_route = _deep_link(
            area, exam_id, cycle_id, entity_row_id,
            paper_id=paper_id, doc_status=doc_status,
        )
        items.append({
            "id": area,
            "severity": _severity_for(area, chk["state"]),
            "area": area,
            "title": title,
            "why": why,
            "cta_label": cta_label,
            "cta_route": cta_route,
            "entity_kind": _AREA_ENTITY_KIND.get(area),
            "entity_id": entity_row_id,
            "evidence_refs": evidence_refs,
            "status": "open",
        })
    items.sort(key=lambda i: (_SEVERITY_RANK[i["severity"]], _AREA_ORDER.index(i["area"])))
    return items


# ── Assembly ─────────────────────────────────────────────────────────────────

def build_console_detail(sb, exam_id: str, cycle_id: str | None = None) -> dict[str, Any]:
    exam = _require_exam(sb, exam_id)

    # Status parity + reason detail: SAME aggregate + SAME pure classifier.
    agg = _wq.aggregate(sb, [exam], include_details=True)[exam["id"]]
    classified = _wq.classify_exam(agg)
    status = classified["status"]
    flags = set(classified["flags"])
    by_area = agg["pending_by_area"]

    org_name = _wq.load_org_names(sb, [exam]).get(exam.get("conducting_organization_id"))
    family_name = _family_name(sb, exam.get("exam_family_id"))

    # Advisory-area reads (not owned by the classifier) — strict + paged.
    # strict=True: any DB failure raises DatabaseError → 5xx (never fabricated zero counts).
    doc_counts = load_doc_extraction_counts(sb, exam_id, strict=True)
    failing_doc = (
        load_first_failing_doc_strict(sb, exam_id, cycle_id)
        if doc_counts["total"] > 0 and doc_counts["extracted"] < doc_counts["total"]
        else None
    )
    syllabus_verified = _syllabus_verified_count(sb, exam_id)
    competition = _competition(sb, exam_id)
    mock = _mock_readiness(sb, exam_id)

    def _pending_reasons(area: str) -> list[str]:
        d = by_area[area]
        reasons = ["pending_review"]
        if d["stale_count"] > 0:
            reasons.append("stale_review_queue")
        return reasons

    checks: list[dict[str, Any]] = []

    # setup (hard)
    if agg["phase_count"] > 0:
        checks.append(_check("setup", "hard", "done", f"{agg['phase_count']} phase(s) defined"))
    else:
        checks.append(_check("setup", "hard", "blocked", "No exam phases defined", ["no_phases"]))

    # documents (advisory) — real extraction status from document_processing_jobs
    # (job_type='text_extract', latest job per asset). trust_status on
    # syllabus_documents is orthogonal to extraction (BUG-EI-2 final fix).
    extracted  = doc_counts["extracted"]
    doc_total  = doc_counts["total"]
    if extracted >= 1:
        checks.append(_check("documents", "advisory", "done", f"{extracted} document(s) extracted"))
    elif doc_total >= 1:
        doc_evidence = [failing_doc] if failing_doc else []
        checks.append(_check("documents", "advisory", "needs_action",
                             f"{doc_total} uploaded, none extracted",
                             evidence_refs=doc_evidence))
    else:
        checks.append(_check("documents", "advisory", "needs_action", "No documents uploaded"))

    # syllabus (advisory; needs_action on pending, else verified-presence advisory)
    syl = by_area["syllabus"]
    if syl["pending_count"] > 0:
        checks.append(_check("syllabus", "advisory", "needs_action",
                             f"{syl['pending_count']} mention(s) pending review",
                             _pending_reasons("syllabus"), syl["evidence_refs"]))
    elif syllabus_verified == 0:
        checks.append(_check("syllabus", "advisory", "needs_action", "No verified syllabus mentions"))
    else:
        checks.append(_check("syllabus", "advisory", "done", f"{syllabus_verified} verified, none pending"))

    # topic_coverage (hard)
    tc = by_area["topic_coverage"]
    if agg["locked_coverage_count"] == 0:
        # Blocked, but pending coverage rows still carry pending/stale reasons +
        # evidence (the classifier reports them too). Deterministic order:
        # no_locked_coverage, pending_review, stale_review_queue.
        tc_reasons = ["no_locked_coverage"]
        if tc["pending_count"] > 0:
            tc_reasons.append("pending_review")
            if tc["stale_count"] > 0:
                tc_reasons.append("stale_review_queue")
        detail = "No locked topic coverage — planner cannot use this exam"
        if tc["pending_count"] > 0:
            detail += f" · {tc['pending_count']} pending review"
        checks.append(_check("topic_coverage", "hard", "blocked", detail,
                             tc_reasons, tc["evidence_refs"]))
    elif tc["pending_count"] > 0:
        checks.append(_check("topic_coverage", "hard", "needs_action",
                             f"{agg['locked_coverage_count']} locked · {tc['pending_count']} pending review",
                             _pending_reasons("topic_coverage"), tc["evidence_refs"]))
    else:
        checks.append(_check("topic_coverage", "hard", "done", f"{agg['locked_coverage_count']} locked coverage row(s)"))

    # pyq (advisory): missing verified AND/OR pending sub-rows
    pq = by_area["pyq"]
    pyq_reasons: list[str] = []
    if agg["verified_pyq_count"] == 0:
        pyq_reasons.append("missing_pyq")
    if pq["pending_count"] > 0:
        pyq_reasons.extend(_pending_reasons("pyq"))
    if pyq_reasons:
        detail = f"{agg['verified_pyq_count']} of {agg['total_pyq_count']} verified"
        if pq["pending_count"]:
            detail += f" · {pq['pending_count']} pending review"
        checks.append(_check("pyq", "advisory", "needs_action", detail, pyq_reasons, pq["evidence_refs"]))
    else:
        checks.append(_check("pyq", "advisory", "done", f"{agg['verified_pyq_count']} of {agg['total_pyq_count']} verified"))

    # updates (advisory; classifier-owned via policy pending)
    up = by_area["updates"]
    if up["pending_count"] > 0:
        checks.append(_check("updates", "advisory", "needs_action",
                             f"{up['pending_count']} update(s) need verification",
                             _pending_reasons("updates"), up["evidence_refs"]))
    else:
        checks.append(_check("updates", "advisory", "done", "No updates pending verification"))

    # competition (advisory) — selected row id is the evidence.
    if competition["available"]:
        checks.append(_check("competition", "advisory", "done", "Competition metrics reviewed",
                             evidence_refs=[{"kind": "exam_competition_metrics", "row_id": competition["row_id"]}]))
    else:
        checks.append(_check("competition", "advisory", "needs_action", "No reviewed competition metrics"))

    # mock_readiness (advisory)
    mock_state = {"ready": "done", "thin_bank": "needs_action", "blocked": "needs_action",
                  "unknown": "unknown"}[mock["status"]]
    checks.append(_check("mock_readiness", "advisory", mock_state, mock["detail"]))

    # publish (hard) — the activation outcome, derived from the same status.
    pub_state = {"blocked": "blocked", "needs_action": "needs_action", "ready": "done"}[status]
    pub_detail = {
        "blocked": "Blocked by an upstream hard gate",
        "needs_action": "Outstanding work before activation",
        "ready": "All activation gates pass",
    }[status]
    checks.append(_check("publish", "hard", pub_state, pub_detail))

    # Order checks deterministically by area.
    checks.sort(key=lambda c: _AREA_ORDER.index(c["area"]))

    action_queue = _build_action_queue(sb, checks, exam_id, cycle_id)

    # Top-level evidence_refs = de-duplicated union of every check's refs.
    seen: set[tuple] = set()
    evidence_refs: list[dict[str, Any]] = []
    for chk in checks:
        for ref in chk["evidence_refs"]:
            key = (ref["kind"], ref["row_id"])
            if key not in seen:
                seen.add(key)
                evidence_refs.append(ref)

    # ── Verdict: reasons are classifier-derived semantic tokens only. ──
    reason_tokens: list[str] = []
    if agg["phase_count"] == 0:
        reason_tokens.append("no_phases")
    if "missing_coverage" in flags:
        reason_tokens.append("no_locked_coverage")
    if "missing_pyq" in flags:
        reason_tokens.append("missing_pyq")
    if "pending_review" in flags:
        reason_tokens.append("pending_review")
    if "stale_review_queue" in flags:
        reason_tokens.append("stale_review_queue")

    headline = {
        "blocked": "Not ready for aspirants",
        "needs_action": "Needs work before activation",
        "ready": "Ready for aspirants",
    }[status]

    # Fail closed: a non-ready status must be explained by a classifier-owned,
    # non-publish check AND a matching action item.
    if status != "ready":
        explained = any(
            c["area"] in _CLASSIFIER_AREAS and c["state"] in {"blocked", "needs_action"}
            for c in checks
        )
        if not explained or not action_queue:
            raise RuntimeError(
                f"console detail reason-parity violation for {exam_id}: status={status}"
            )

    return {
        "exam": {
            "id": exam["id"], "slug": exam.get("slug"), "name": exam.get("name"),
            "organization_name": org_name, "family_name": family_name,
        },
        "activation_verdict": {
            "status": status, "headline": headline,
            "reasons": reason_tokens if status != "ready" else [],
        },
        "mock_readiness": mock,
        "action_queue": action_queue,
        "activation_checks": checks,
        "stages": _STAGES,
        "evidence_refs": evidence_refs,
        "generated_at": _wq._now().isoformat(),
    }
