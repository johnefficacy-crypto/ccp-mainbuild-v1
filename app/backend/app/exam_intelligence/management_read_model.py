"""Management read model (backend prerequisite for I8-A/B — Phase 0).

Serves:
  GET /api/admin/exam-intelligence/management/exams        — paginated list
  GET /api/admin/exam-intelligence/management/exams/{id}  — single-exam detail

The top-level verdict uses ``work_queue.classify_exam`` as the single authority
(status parity is load-bearing — same classifier as the console list and console
detail). Advisory per-section readiness comes from ``compute_exam_workspace_readiness``.

Failure semantics:
  - Unknown exam → 404
  - Correctness-critical read failure → DatabaseError → 5xx (via execute_or_raise)
  - Advisory read failure (section_readiness) → null field, never 5xx
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException

from app.db.utils import execute_or_raise
from app.exam_intelligence import work_queue as _wq
from app.exam_intelligence.console_detail import build_console_detail
from app.exam_intelligence.readiness import compute_exam_workspace_readiness

logger = logging.getLogger("career_copilot.exam_intelligence.management_read_model")

_EXAM_COLS = (
    "id, slug, name, exam_type, is_active, exam_family_id, "
    "management_mode, cadence, conducting_organization_id"
)
# Real DB column names — PostgREST returns 42703 if these are wrong.
# exam_cycles: cycle_name (not name), year, status
# exam_phases: phase_name (not name), phase_start/phase_end (not start_date/end_date), status
_CYCLE_COLS = "id, exam_id, cycle_name, year, status, created_at"
_PHASE_COLS = (
    "id, exam_id, exam_cycle_id, phase_name, phase_slug, phase_order, "
    "phase_start, phase_end, status"
)


def _safe(call, default=None):
    try:
        return call()
    except Exception as exc:  # noqa: BLE001
        logger.warning("management advisory read failed: %s", exc)
        return default


def _load_family_names(sb, family_ids: list[str]) -> dict[str, str]:
    if not family_ids:
        return {}
    rows = _wq._batch_paged(sb, "exam_families", "id", family_ids, "id, name")
    return {r["id"]: r.get("name") for r in rows if r.get("id")}


def _load_cycles_for_exams(sb, exam_ids: list[str]) -> list[dict[str, Any]]:
    if not exam_ids:
        return []
    return _wq._batch_paged(sb, "exam_cycles", "exam_id", exam_ids, _CYCLE_COLS)


def _load_phases_for_cycles(sb, cycle_ids: list[str]) -> list[dict[str, Any]]:
    if not cycle_ids:
        return []
    return _wq._batch_paged(sb, "exam_phases", "exam_cycle_id", cycle_ids, _PHASE_COLS)


def _group_by_key(rows: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        k = r.get(key)
        if k:
            out.setdefault(k, []).append(r)
    return out


def _format_phase(p: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": p.get("id"),
        "slug": p.get("phase_slug"),
        "label": p.get("phase_name"),       # DB: phase_name → API: label
        "phase_order": p.get("phase_order"),
        "start_date": p.get("phase_start"),  # DB: phase_start → API: start_date
        "end_date": p.get("phase_end"),      # DB: phase_end   → API: end_date
        "status": p.get("status"),
    }


def _format_cycle(c: dict[str, Any], phases: list[dict[str, Any]]) -> dict[str, Any]:
    sorted_phases = sorted(
        [_format_phase(p) for p in phases],
        key=lambda p: (p.get("phase_order") or 0, p.get("id") or ""),
    )
    return {
        "id": c.get("id"),
        "name": c.get("cycle_name"),   # DB: cycle_name → API: name
        "year": c.get("year"),
        "status": c.get("status"),
        "phases": sorted_phases,
    }


def _advisory_readiness_summary(a: dict[str, Any]) -> dict[str, Any]:
    """Lightweight advisory readiness summary from aggregate signals.

    Uses locked section-state vocabulary (design-lock Section 4.4): ``missing | ready``.
    Never authorizes or blocks activation — that authority is ``classify_exam``.
    """
    return {
        "setup": "ready" if a.get("phase_count", 0) > 0 else "missing",
        "topic_coverage": "ready" if a.get("locked_coverage_count", 0) > 0 else "missing",
        "pyq": "ready" if a.get("verified_pyq_count", 0) > 0 else "missing",
        "pending_review_count": a.get("pending_review_count", 0),
        "stale_review_count": a.get("stale_review_count", 0),
    }


def _require_exam(sb, exam_id: str) -> dict[str, Any]:
    """Load exam by id. Raises 404 if not found; DatabaseError (→ 5xx) on read failure."""
    rows = execute_or_raise(
        "management.exam",
        lambda: sb.table("exams").select(_EXAM_COLS).eq("id", exam_id).limit(1).execute().data,
    ) or []
    if not rows:
        raise HTTPException(status_code=404, detail="exam not found")
    return rows[0]


def list_management_exams(
    sb,
    *,
    base_filters: dict[str, Any],
    workflow: str | None,
    sort: str,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    """Paginated list of exams with family/current-cycle/phase hierarchy and verdict.

    All correctness-critical reads (candidates, aggregate, cycles, phases, orgs,
    families) use ``execute_or_raise`` — never silently truncated or degraded to
    empty data. Advisory readiness summary is derived from the aggregate signals.
    """
    # Candidate load + aggregate (correctness-critical)
    exams = _wq.load_candidates(sb, **base_filters)
    agg = _wq.aggregate(sb, exams)
    org_names = _wq.load_org_names(sb, exams)

    # Family names (correctness-critical)
    family_ids = sorted({e.get("exam_family_id") for e in exams if e.get("exam_family_id")})
    family_names = _load_family_names(sb, family_ids)

    # Build classified rows
    rows: list[dict[str, Any]] = []
    for e in exams:
        a = agg.get(e["id"])
        if a is None:
            continue
        c = _wq.classify_exam(a)
        org_id = e.get("conducting_organization_id")
        fam_id = e.get("exam_family_id")
        rows.append({
            "id": e["id"],
            "slug": e.get("slug"),
            "name": e.get("name"),
            "exam_type": e.get("exam_type"),
            "family_id": fam_id,
            "family_name": family_names.get(fam_id) if fam_id else None,
            "organization_id": org_id,
            "organization_name": org_names.get(org_id) if org_id else None,
            "management_mode": e.get("management_mode"),
            "cadence": e.get("cadence"),
            "is_active": e.get("is_active"),
            "status": c["status"],
            "flags": c["flags"],
            "blocker_count": c["blocker_count"],
            "first_blocker_text": c["first_blocker_text"],
            "readiness_summary": _advisory_readiness_summary(a),
            "current_cycle": None,  # populated below
        })

    # Cycles: load for all exams, select current per exam (correctness-critical)
    exam_ids = [e["id"] for e in exams]
    cycle_rows = _load_cycles_for_exams(sb, exam_ids)
    cycles_by_exam = _group_by_key(cycle_rows, "exam_id")

    current_by_exam: dict[str, dict[str, Any] | None] = {
        e["id"]: _wq.select_current_cycle(cycles_by_exam.get(e["id"], []))
        for e in exams
    }

    # Phases for all current cycles (correctness-critical)
    current_cycle_ids = sorted({c["id"] for c in current_by_exam.values() if c})
    phase_rows = _load_phases_for_cycles(sb, current_cycle_ids)
    phases_by_cycle = _group_by_key(phase_rows, "exam_cycle_id")

    # Attach current_cycle to each row
    row_by_id = {r["id"]: r for r in rows}
    for eid, cur in current_by_exam.items():
        row = row_by_id.get(eid)
        if row is None or cur is None:
            continue
        row["current_cycle"] = _format_cycle(cur, phases_by_cycle.get(cur.get("id", ""), []))

    # Family options for the front-door dropdown — derived from the full candidate
    # set (before workflow filter and pagination) so the list stays complete.
    family_options = sorted(
        [{"id": fid, "name": family_names[fid]} for fid in family_ids if fid in family_names],
        key=lambda f: (f["name"] or "").lower(),
    )

    # Workflow filter → sort → paginate
    rows = _wq.apply_workflow(rows, workflow)
    rows = _wq.sort_rows(rows, sort)
    total_count = len(rows)
    page = rows[offset : offset + limit]

    return {
        "items": page,
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
        "has_next": offset + len(page) < total_count,
        "family_options": family_options,
    }


def get_management_exam_detail(
    sb,
    exam_id: str,
    cycle_id: str | None = None,
) -> dict[str, Any]:
    """Single-exam management detail with all cycles, per-section readiness, and action queue.

    Unknown exam → 404. Critical read failure → 5xx. Advisory read failure
    (``section_readiness``) → null field, not 5xx.
    """
    # Load exam (fail-closed)
    exam = _require_exam(sb, exam_id)

    # Classify (correctness-critical — same aggregate + classifier as the list)
    agg_map = _wq.aggregate(sb, [exam])
    a = agg_map[exam_id]
    classified = _wq.classify_exam(a)

    # Names
    org_names = _wq.load_org_names(sb, [exam])
    fam_id = exam.get("exam_family_id")
    family_names = _load_family_names(sb, [fam_id] if fam_id else [])
    org_id = exam.get("conducting_organization_id")

    # All cycles for this exam (correctness-critical)
    all_cycles = _load_cycles_for_exams(sb, [exam_id])

    # Resolve selected cycle
    selected_cycle: dict[str, Any] | None
    if cycle_id:
        matched = [c for c in all_cycles if c.get("id") == cycle_id]
        if not matched:
            raise HTTPException(status_code=404, detail="cycle not found")
        selected_cycle = matched[0]
    else:
        selected_cycle = _wq.select_current_cycle(all_cycles)

    selected_cycle_id = selected_cycle.get("id") if selected_cycle else None

    # Phases for all cycles (correctness-critical)
    all_cycle_ids = [c["id"] for c in all_cycles if c.get("id")]
    all_phase_rows = _load_phases_for_cycles(sb, all_cycle_ids)
    phases_by_cycle = _group_by_key(all_phase_rows, "exam_cycle_id")

    cycles_with_phases = [
        _format_cycle(c, phases_by_cycle.get(c.get("id", ""), []))
        for c in all_cycles
    ]
    current_cycle_shaped = (
        _format_cycle(selected_cycle, phases_by_cycle.get(selected_cycle_id or "", []))
        if selected_cycle else None
    )

    # Per-section readiness (advisory, fail-soft — null on failure is acceptable)
    section_readiness = _safe(
        lambda: compute_exam_workspace_readiness(sb, exam_id, selected_cycle_id)
    )

    # Console detail: action queue + verdict (correctness-critical, fail-hard → 5xx)
    console = build_console_detail(sb, exam_id, selected_cycle_id)

    return {
        "id": exam["id"],
        "slug": exam.get("slug"),
        "name": exam.get("name"),
        "exam_type": exam.get("exam_type"),
        "family_id": fam_id,
        "family_name": family_names.get(fam_id) if fam_id else None,
        "organization_id": org_id,
        "organization_name": org_names.get(org_id) if org_id else None,
        "management_mode": exam.get("management_mode"),
        "cadence": exam.get("cadence"),
        "is_active": exam.get("is_active"),
        "status": classified["status"],
        "flags": classified["flags"],
        "blocker_count": classified["blocker_count"],
        "first_blocker_text": classified["first_blocker_text"],
        "readiness_summary": _advisory_readiness_summary(a),
        "current_cycle": current_cycle_shaped,
        "cycles": cycles_with_phases,
        "section_readiness": section_readiness,
        "action_queue": console["action_queue"],
        "activation_verdict": console["activation_verdict"],
        "activation_checks": console["activation_checks"],
        "stages": console["stages"],
        "evidence_refs": console["evidence_refs"],
        "generated_at": _wq._now().isoformat(),
    }
