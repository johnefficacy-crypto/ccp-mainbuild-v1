"""Per-exam action console read (Wave 4.6I-BE) — read-only.

Backs GET /api/admin/exam-intelligence/console/exams/{exam_id}. Assembles a
single-exam activation view: verdict, advisory mock readiness, action queue,
activation checks, and stages — all from NAMED existing reads.

Status parity is load-bearing: ``activation_verdict.status`` is produced by the
SAME pure classifier the 4.6H list uses (``work_queue.classify_exam``) over the
SAME aggregate (``work_queue.aggregate(sb, [exam])``). There is no parallel
status rule here. Mock readiness is separate and advisory — it never changes the
activation status.

Guards: no score_percent/confidence_score/confidence_percent leaves this module;
correctness-critical reads use ``execute_or_raise`` (failure → 5xx, never a
fabricated verdict); unknown exam → 404. Read-only; no writes.
"""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from app.db.utils import execute_or_raise
from app.exam_intelligence import work_queue as _wq
from app.exam_intelligence.diagnostics import assemble_mock_readiness_report
from app.study_os.competition_context import competition_context
from app.study_os.update_context import policy_update_context

# Mock-readiness inputs mirror the existing /exams/{id}/mock-readiness defaults.
_SELECTABLE_MOCK_STATUSES = ["verified", "published"]
_VERIFIED_STATUS = "verified"
_MIN_PER_SECTION = 30
_MIN_LOCKED_COVERAGE = 1

# Deterministic area order (used for action-queue tie-breaking + check order).
_AREA_ORDER = [
    "setup", "documents", "syllabus", "topic_coverage", "pyq",
    "updates", "competition", "mock_readiness", "publish",
]
_HARD_AREAS = {"setup", "topic_coverage", "publish"}

_STAGES = [
    {"id": "setup", "label": "Setup", "areas": ["setup", "documents"]},
    {"id": "evidence", "label": "Evidence", "areas": ["syllabus", "topic_coverage", "pyq"]},
    {"id": "review", "label": "Review", "areas": ["updates", "competition", "mock_readiness"]},
    {"id": "activation", "label": "Activation", "areas": ["publish"]},
]

_SEVERITY_RANK = {"blocker": 0, "action": 1, "advisory": 2}
_EVIDENCE_CAP = 20  # bound the refs we surface per area


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


# ── Per-area reads (each grounded in a named table/helper) ──────────────────

def _coverage_rows(sb, exam_id: str) -> list[dict[str, Any]]:
    return execute_or_raise(
        "console_detail.coverage",
        lambda: sb.table("exam_topic_coverage").select("id, reviewer_status")
        .eq("exam_id", exam_id).limit(5000).execute().data,
    ) or []


def _syllabus_rows(sb, exam_id: str) -> list[dict[str, Any]]:
    return execute_or_raise(
        "console_detail.syllabus",
        lambda: sb.table("syllabus_topic_mentions").select("id, reviewer_status")
        .eq("exam_id", exam_id).limit(5000).execute().data,
    ) or []


def _document_rows(sb, exam_id: str) -> list[dict[str, Any]]:
    return execute_or_raise(
        "console_detail.documents",
        lambda: sb.table("document_assets").select("id, extraction_status")
        .eq("exam_id", exam_id).limit(2000).execute().data,
    ) or []


def _setup_check(agg) -> dict[str, Any]:
    n = agg["phase_count"]
    if n > 0:
        return _check("setup", "hard", "done", f"{n} phase{'s' if n != 1 else ''} defined")
    return _check("setup", "hard", "blocked", "No exam phases defined", ["no_phases"])


def _documents_check(rows) -> dict[str, Any]:
    total = len(rows)
    extracted = sum(1 for r in rows if r.get("extraction_status") == "succeeded")
    if extracted >= 1:
        return _check("documents", "advisory", "done", f"{extracted} document{'s' if extracted != 1 else ''} extracted")
    if total >= 1:
        return _check("documents", "advisory", "needs_action", f"{total} uploaded, none extracted yet")
    return _check("documents", "advisory", "needs_action", "No documents uploaded")


def _syllabus_check(rows) -> tuple[dict[str, Any], list[str]]:
    verified = sum(1 for r in rows if r.get("reviewer_status") == "verified")
    pending = [r["id"] for r in rows if r.get("reviewer_status") in {"pending", "needs_correction"} and r.get("id")]
    if verified >= 1 and not pending:
        return _check("syllabus", "advisory", "done", f"{verified} verified, none pending"), []
    if pending:
        return _check("syllabus", "advisory", "needs_action", f"{len(pending)} mention(s) pending review"), pending
    return _check("syllabus", "advisory", "needs_action", "No verified syllabus mentions"), []


def _coverage_check(agg, rows) -> tuple[dict[str, Any], list[str]]:
    locked = agg["locked_coverage_count"]
    ids = [r["id"] for r in rows if r.get("id")][:_EVIDENCE_CAP]
    if locked >= 1:
        return _check("topic_coverage", "hard", "done", f"{locked} locked coverage row(s)"), ids
    # reviewed-but-not-locked still fails the planner gate.
    return _check("topic_coverage", "hard", "blocked",
                  "No locked topic coverage — planner cannot use this exam", ["no_locked_coverage"]), ids


def _pyq_check(agg) -> dict[str, Any]:
    v, t = agg["verified_pyq_count"], agg["total_pyq_count"]
    if v >= 1:
        return _check("pyq", "advisory", "done", f"{v} of {t} questions fully verified")
    return _check("pyq", "advisory", "needs_action",
                  f"0 of {t} questions clear the verified-paper + question + tag gate", ["missing_pyq"])


def _updates_check(ctx) -> tuple[dict[str, Any], list[str]]:
    pending = ctx.get("needs_verification") or []
    pending_ids = [u.get("id") for u in pending if u.get("id")][:_EVIDENCE_CAP]
    if pending_ids:
        return _check("updates", "advisory", "needs_action", f"{len(pending_ids)} update(s) need verification"), pending_ids
    return _check("updates", "advisory", "done", "No updates pending verification"), []


def _competition_check(ctx) -> tuple[dict[str, Any], list[str]]:
    if ctx.get("available"):
        rid = ctx.get("id")
        return _check("competition", "advisory", "done", "Competition metrics reviewed"), ([rid] if rid else [])
    return _check("competition", "advisory", "needs_action", "No reviewed competition metrics"), []


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


def _mock_check(mock: dict[str, str]) -> dict[str, Any]:
    state = {"ready": "done", "thin_bank": "needs_action", "blocked": "needs_action",
             "unknown": "unknown"}[mock["status"]]
    return _check("mock_readiness", "advisory", state, mock["detail"])


def _publish_check(status: str) -> dict[str, Any]:
    # The publish gate IS the activation outcome — derived from the same status,
    # never a parallel rule. hard gate.
    state = {"blocked": "blocked", "needs_action": "needs_action", "ready": "done"}[status]
    detail = {
        "blocked": "Blocked by an upstream hard gate",
        "needs_action": "Outstanding work before activation",
        "ready": "All activation gates pass",
    }[status]
    return _check("publish", "hard", state, detail)


def _check(area: str, gate: str, state: str, detail: str, reasons: list[str] | None = None) -> dict[str, Any]:
    return {"area": area, "gate": gate, "state": state, "detail": detail, "reasons": reasons or []}


# ── Action queue ─────────────────────────────────────────────────────────────

_ACTION_COPY = {
    "setup": ("Define exam phases", "Setup must exist before any activation work."),
    "documents": ("Upload & extract documents", "Source documents feed syllabus and PYQ evidence."),
    "syllabus": ("Review syllabus mentions", "Pending mentions are not yet usable evidence."),
    "topic_coverage": ("Lock topic coverage", "The planner consumes only locked coverage rows."),
    "pyq": ("Verify PYQ", "No question clears verified paper + question + tag."),
    "updates": ("Verify official updates", "Unverified updates do not propagate."),
    "competition": ("Review competition metrics", "No reviewed competition signal exists yet."),
    "mock_readiness": ("Strengthen the mock bank", "Mock bank is thin or blocked (advisory only)."),
}

_AREA_ENTITY_KIND = {
    "topic_coverage": "exam_topic_coverage",
    "syllabus": "syllabus_topic_mention",
    "updates": "exam_policy_updates",
    "competition": "exam_competition_metrics",
    "pyq": "pyq_question",
    "documents": "document_assets",
    "setup": "exam_phases",
    "mock_readiness": "mock_question_bank",
}


def _severity_for(area: str, state: str) -> str:
    if area in _HARD_AREAS and state == "blocked":
        return "blocker"
    if area == "mock_readiness":
        return "advisory"
    return "action"


def _build_action_queue(checks: list[dict[str, Any]], exam_id: str,
                        evidence_by_area: dict[str, list[str]]) -> list[dict[str, Any]]:
    workspace_route = f"/admin/exam-intelligence/workspace/{exam_id}"
    items: list[dict[str, Any]] = []
    for chk in checks:
        area = chk["area"]
        # publish is the activation OUTCOME, not an action to take.
        if area == "publish" or chk["state"] in {"done", "unknown"}:
            continue
        title, why = _ACTION_COPY[area]
        kind = _AREA_ENTITY_KIND.get(area)
        refs = [{"kind": kind, "row_id": rid} for rid in evidence_by_area.get(area, [])] if kind else []
        items.append({
            "id": area,
            "severity": _severity_for(area, chk["state"]),
            "area": area,
            "title": title,
            "why": why,
            "cta_label": "Open workspace",
            "cta_route": workspace_route,  # workspace areas are tabs there (verified route)
            "entity_kind": kind,
            "entity_id": None,
            "evidence_refs": refs,
            "status": "open",
        })
    items.sort(key=lambda i: (_SEVERITY_RANK[i["severity"]], _AREA_ORDER.index(i["area"])))
    return items


# ── Assembly ─────────────────────────────────────────────────────────────────

def build_console_detail(sb, exam_id: str) -> dict[str, Any]:
    exam = _require_exam(sb, exam_id)

    # Status parity: same aggregate + same pure classifier as the 4.6H list.
    agg = _wq.aggregate(sb, [exam])[exam["id"]]
    classified = _wq.classify_exam(agg)
    status = classified["status"]

    org_name = _wq.load_org_names(sb, [exam]).get(exam.get("conducting_organization_id"))
    family_name = _family_name(sb, exam.get("exam_family_id"))

    # Per-area reads (single-exam; each grounded in a named source).
    cov_rows = _coverage_rows(sb, exam_id)
    syl_rows = _syllabus_rows(sb, exam_id)
    doc_rows = _document_rows(sb, exam_id)
    updates_ctx = policy_update_context(sb, exam_id)
    competition_ctx = competition_context(sb, exam_id)
    mock = _mock_readiness(sb, exam_id)

    setup_chk = _setup_check(agg)
    docs_chk = _documents_check(doc_rows)
    syl_chk, syl_ev = _syllabus_check(syl_rows)
    cov_chk, cov_ev = _coverage_check(agg, cov_rows)
    pyq_chk = _pyq_check(agg)
    upd_chk, upd_ev = _updates_check(updates_ctx)
    comp_chk, comp_ev = _competition_check(competition_ctx)
    mock_chk = _mock_check(mock)
    pub_chk = _publish_check(status)

    checks = [setup_chk, docs_chk, syl_chk, cov_chk, pyq_chk, upd_chk, comp_chk, mock_chk, pub_chk]

    evidence_by_area = {
        "syllabus": syl_ev, "topic_coverage": cov_ev,
        "updates": upd_ev, "competition": comp_ev,
    }
    action_queue = _build_action_queue(checks, exam_id, evidence_by_area)

    # Top-level evidence_refs = de-duplicated union of action-item refs.
    seen: set[tuple] = set()
    evidence_refs: list[dict[str, Any]] = []
    for item in action_queue:
        for ref in item["evidence_refs"]:
            key = (ref["kind"], ref["row_id"])
            if key not in seen:
                seen.add(key)
                evidence_refs.append(ref)

    headline = {
        "blocked": "Not ready for aspirants",
        "needs_action": "Needs work before activation",
        "ready": "Ready for aspirants",
    }[status]
    reasons = [c["detail"] for c in checks if c["gate"] == "hard" and c["state"] == "blocked"]
    if status == "needs_action" and not reasons:
        reasons = [c["detail"] for c in checks if c["state"] == "needs_action"]

    return {
        "exam": {
            "id": exam["id"], "slug": exam.get("slug"), "name": exam.get("name"),
            "organization_name": org_name, "family_name": family_name,
        },
        "activation_verdict": {"status": status, "headline": headline, "reasons": reasons},
        "mock_readiness": mock,
        "action_queue": action_queue,
        "activation_checks": checks,
        "stages": _STAGES,
        "evidence_refs": evidence_refs,
        "generated_at": _wq._now().isoformat(),
    }
