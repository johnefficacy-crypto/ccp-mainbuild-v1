"""Competition Intelligence read helpers (Phase 12).

Reads ``exam_competition_metrics`` rows that have cleared review
(``reviewer_status in ('reviewed', 'locked')``) and shapes them into the
time series the aspirant-facing Exam Intelligence page consumes:

* ``competition_series``  - one row per (cycle, phase) with vacancy,
  applicant count, selection ratio and the raw cutoff / difficulty
  payloads.
* ``cutoff_series``       - flattened {category -> [{year, marks, phase}]}
  built from the ``cutoff_trend`` jsonb. Convention for the jsonb shape::

      {
        "<category>": <number>,            -- single cutoff for the cycle
        "<category>": [<n1>, <n2>, ...]    -- multi-stage cutoffs ordered
      }

  Anything else is ignored. The function is forgiving so admin-entered
  rows that don't match the convention silently degrade rather than
  poison the response.
* ``vacancy_series``      - {category -> [{year, count}]} built from
  ``vacancy_by_category`` jsonb + ``vacancy_total``.

No AI. No inference. Empty inputs → empty payloads.
"""
from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger("career_copilot.exam_intelligence.competition")

_READY_STATUSES = ("reviewed", "locked")


def _safe(call: Callable[[], Any], default: Any = None) -> Any:
    try:
        return call()
    except Exception as exc:  # noqa: BLE001
        logger.warning("competition read failed: %s", exc)
        return default


def _cycle_year(cycle: dict[str, Any] | None) -> int | None:
    if not cycle:
        return None
    raw = cycle.get("year")
    try:
        return int(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def _coerce_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _load_cycles(supabase: Any, exam_id: str) -> dict[str, dict[str, Any]]:
    rows = _safe(
        lambda: (
            supabase.table("exam_cycles")
            .select("id, exam_id, year, cycle_name, status, application_start, application_end, exam_start, exam_end")
            .eq("exam_id", exam_id)
            .limit(200)
            .execute()
            .data
        ),
        default=[],
    ) or []
    return {r["id"]: r for r in rows if r.get("id")}


def _load_phases(supabase: Any, exam_id: str) -> dict[str, dict[str, Any]]:
    rows = _safe(
        lambda: (
            supabase.table("exam_phases")
            .select("id, exam_id, phase_name, phase_slug, phase_order")
            .eq("exam_id", exam_id)
            .limit(200)
            .execute()
            .data
        ),
        default=[],
    ) or []
    return {r["id"]: r for r in rows if r.get("id")}


def _load_metrics(supabase: Any, exam_id: str) -> list[dict[str, Any]]:
    rows = _safe(
        lambda: (
            supabase.table("exam_competition_metrics")
            .select(
                "id, exam_id, exam_cycle_id, exam_phase_id, "
                "vacancy_total, vacancy_by_category, applicant_count, "
                "selection_ratio, cutoff_trend, difficulty_trend, "
                "cutoff_by_category, difficulty_assessment, metric_kind, "
                "is_current_published, "
                "competition_pressure_score, source_basis, confidence_score, "
                "reviewer_status, created_at"
            )
            .eq("exam_id", exam_id)
            .in_("reviewer_status", list(_READY_STATUSES))
            .limit(500)
            .execute()
            .data
        ),
        default=[],
    ) or []
    return list(rows)


def _select_current(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The shared current-row selector (OD-10): rows disposed with a
    metric_kind use ``is_current_published`` as the single source of truth —
    no per-reader "pick best" heuristic. Legacy rows with metric_kind IS NULL
    (pre-migration-215 or awaiting operator triage) fall back to being
    included as-is so existing verified data does not vanish.
    """
    out: list[dict[str, Any]] = []
    for r in rows:
        if r.get("metric_kind") is not None:
            if r.get("is_current_published"):
                out.append(r)
        else:
            out.append(r)
    return out


def competition_series(supabase: Any, exam_id: str) -> list[dict[str, Any]]:
    """Return verified competition metrics, newest cycle last.

    A (cycle, phase) scope may now be represented by up to two disposed rows
    — a ``cycle_summary`` (vacancy/pressure) and a ``phase_cutoff``
    (cutoff/difficulty) — which are merged into one series entry per
    (cycle, phase) so existing consumers see one row as before.
    """
    if not exam_id:
        return []
    metrics = _select_current(_load_metrics(supabase, exam_id))
    if not metrics:
        return []
    cycles = _load_cycles(supabase, exam_id)
    phases = _load_phases(supabase, exam_id)

    merged: dict[tuple[Any, Any], dict[str, Any]] = {}

    def _entry(cycle_id: Any, phase_id: Any) -> dict[str, Any]:
        key = (cycle_id, phase_id)
        if key not in merged:
            cycle = cycles.get(cycle_id or "")
            phase = phases.get(phase_id or "")
            merged[key] = {
                "id": None,
                "cycle_id": cycle_id,
                "cycle_year": _cycle_year(cycle),
                "cycle_name": (cycle or {}).get("cycle_name"),
                "cycle_status": (cycle or {}).get("status"),
                "phase_id": phase_id,
                "phase_name": (phase or {}).get("phase_name"),
                "phase_slug": (phase or {}).get("phase_slug"),
                "vacancy_total": None,
                "vacancy_by_category": {},
                "applicant_count": None,
                "selection_ratio": None,
                "cutoff_trend": {},
                "difficulty_trend": {},
                "cutoff_by_category": {},
                "difficulty_assessment": {},
                "competition_pressure_score": None,
                "source_basis": None,
                "confidence_score": None,
                "reviewer_status": None,
                # Ratio contract, PR-1 half (resolutions §1.2): the
                # provenance-proven applied/appeared denominator lands in
                # PR 2 (exam_candidate_counts). Until then these stay null —
                # never derived from the ambiguous legacy applicant_count.
                "selection_rate": None,
                "candidates_per_vacancy": None,
                "ratio_denominator": None,
            }
        return merged[key]

    for row in metrics:
        kind = row.get("metric_kind")
        cycle_id = row.get("exam_cycle_id")
        if kind == "cycle_summary":
            e = _entry(cycle_id, None)
            e["id"] = row.get("id")
            e["vacancy_total"] = row.get("vacancy_total")
            e["vacancy_by_category"] = row.get("vacancy_by_category") or {}
            e["applicant_count"] = row.get("applicant_count")
            e["selection_ratio"] = row.get("selection_ratio")
            e["competition_pressure_score"] = row.get("competition_pressure_score")
            e["source_basis"] = row.get("source_basis")
            e["confidence_score"] = row.get("confidence_score")
            e["reviewer_status"] = row.get("reviewer_status")
            # Also project onto every phase entry already seen for this cycle
            # so phase rows keep vacancy visibility (vacancy is cycle-level).
            for (c_id, p_id), other in merged.items():
                if c_id == cycle_id and p_id is not None:
                    other["vacancy_total"] = e["vacancy_total"]
                    other["vacancy_by_category"] = e["vacancy_by_category"]
                    other["applicant_count"] = e["applicant_count"]
                    other["selection_ratio"] = e["selection_ratio"]
                    other["competition_pressure_score"] = e["competition_pressure_score"]
        elif kind == "phase_cutoff":
            e = _entry(cycle_id, row.get("exam_phase_id"))
            e["cutoff_trend"] = row.get("cutoff_trend") or {}
            e["difficulty_trend"] = row.get("difficulty_trend") or {}
            e["cutoff_by_category"] = row.get("cutoff_by_category") or {}
            e["difficulty_assessment"] = row.get("difficulty_assessment") or {}
            if e["id"] is None:
                e["id"] = row.get("id")
                e["source_basis"] = row.get("source_basis")
                e["confidence_score"] = row.get("confidence_score")
                e["reviewer_status"] = row.get("reviewer_status")
            # Inherit vacancy from an already-merged cycle_summary sibling.
            sibling = merged.get((cycle_id, None))
            if sibling:
                e["vacancy_total"] = sibling["vacancy_total"]
                e["vacancy_by_category"] = sibling["vacancy_by_category"]
                e["applicant_count"] = sibling["applicant_count"]
                e["selection_ratio"] = sibling["selection_ratio"]
                e["competition_pressure_score"] = sibling["competition_pressure_score"]
        else:
            # Legacy undisposed row (metric_kind IS NULL): surface as-is,
            # exactly as before migration 215.
            e = _entry(cycle_id, row.get("exam_phase_id"))
            e["id"] = row.get("id")
            e["vacancy_total"] = row.get("vacancy_total")
            e["vacancy_by_category"] = row.get("vacancy_by_category") or {}
            e["applicant_count"] = row.get("applicant_count")
            e["selection_ratio"] = row.get("selection_ratio")
            e["cutoff_trend"] = row.get("cutoff_trend") or {}
            e["difficulty_trend"] = row.get("difficulty_trend") or {}
            e["competition_pressure_score"] = row.get("competition_pressure_score")
            e["source_basis"] = row.get("source_basis")
            e["confidence_score"] = row.get("confidence_score")
            e["reviewer_status"] = row.get("reviewer_status")

    out = list(merged.values())
    for e in out:
        # selection_ratio is the deprecated-in-place key (still served
        # verbatim for external-client compatibility); selection_ratio_legacy
        # is the same value under its explicit legacy name (resolutions §1.2).
        e["selection_ratio_legacy"] = e.get("selection_ratio")

    def _sort_key(r: dict[str, Any]) -> tuple[int, str]:
        year = r.get("cycle_year")
        return (int(year) if isinstance(year, int) else -1, r.get("phase_slug") or "")

    out.sort(key=_sort_key)
    return out


def cutoff_series(series: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Flatten cutoff data across cycles into per-category points.

    Prefers the locked ``cutoff_by_category`` shape
    (``{category: {marks, max_marks?}}``, resolutions §1.5); falls back to
    the legacy ``cutoff_trend`` convention (bare number / list-of-numbers)
    for rows not yet disposed to the new shape. Result shape::

        {
          "general":  [{"year": 2024, "marks": 105.34, "max_marks": 200, "phase_slug": "prelims"}, ...],
          "obc":      [...],
          ...
        }
    """
    out: dict[str, list[dict[str, Any]]] = {}
    for row in series:
        year = row.get("cycle_year")
        if year is None:
            continue
        phase_slug = row.get("phase_slug")
        by_cat = row.get("cutoff_by_category") or {}
        if isinstance(by_cat, dict) and by_cat:
            for category, val in by_cat.items():
                if not isinstance(val, dict):
                    continue
                marks = _coerce_number(val.get("marks"))
                if marks is None:
                    continue
                point: dict[str, Any] = {"year": year, "marks": marks, "phase_slug": phase_slug}
                max_marks = _coerce_number(val.get("max_marks"))
                if max_marks is not None:
                    point["max_marks"] = max_marks
                out.setdefault(str(category).lower(), []).append(point)
            continue
        trend = row.get("cutoff_trend") or {}
        if not isinstance(trend, dict):
            continue
        for category, raw in trend.items():
            if isinstance(raw, list):
                # Multi-stage: take the last meaningful number.
                values = [_coerce_number(v) for v in raw]
                marks = next((v for v in reversed(values) if v is not None), None)
            else:
                marks = _coerce_number(raw)
            if marks is None:
                continue
            out.setdefault(str(category).lower(), []).append(
                {"year": year, "marks": marks, "phase_slug": phase_slug}
            )
    for points in out.values():
        points.sort(key=lambda p: (p.get("year") or 0, p.get("phase_slug") or ""))
    return out


def cutoff_direction(points: list[dict[str, Any]]) -> str | None:
    """Derive a qualitative direction ("rising"/"flat"/"falling") at READ TIME
    ONLY (resolutions OD-3) — never stored. Requires >= 2 points that share
    the same phase and a non-null max_marks (comparable cycles); otherwise
    returns None rather than guessing.
    """
    comparable = [p for p in points if p.get("max_marks") is not None]
    by_phase: dict[Any, list[dict[str, Any]]] = {}
    for p in comparable:
        by_phase.setdefault(p.get("phase_slug"), []).append(p)
    best: list[dict[str, Any]] | None = None
    for pts in by_phase.values():
        if len(pts) >= 2 and (best is None or len(pts) > len(best)):
            best = pts
    if not best or len(best) < 2:
        return None
    ordered = sorted(best, key=lambda p: p.get("year") or 0)
    first, last = ordered[0], ordered[-1]
    if first.get("max_marks") != last.get("max_marks"):
        return None
    delta = last["marks"] - first["marks"]
    if abs(delta) < 1e-9:
        return "flat"
    return "rising" if delta > 0 else "falling"


def vacancy_series(series: list[dict[str, Any]]) -> dict[str, Any]:
    """Build vacancy-by-year series.

    Returns::

        {
          "total":      [{"year": 2023, "count": 1105}, ...],
          "by_category": {
            "general": [{"year": 2023, "count": 442}, ...],
            ...
          }
        }

    When multiple phases exist for the same cycle we collapse on the
    earliest phase row (vacancy is a cycle-level figure, not a phase-level
    one — duplicates would double-count).
    """
    seen_cycles: set[Any] = set()
    total_points: list[dict[str, Any]] = []
    by_cat: dict[str, list[dict[str, Any]]] = {}

    for row in series:
        cycle_id = row.get("cycle_id")
        year = row.get("cycle_year")
        if year is None or cycle_id in seen_cycles:
            continue
        seen_cycles.add(cycle_id)
        if row.get("vacancy_total") is not None:
            total_points.append({"year": year, "count": int(row["vacancy_total"])})
        cat_map = row.get("vacancy_by_category") or {}
        if isinstance(cat_map, dict):
            for category, raw in cat_map.items():
                count = _coerce_number(raw)
                if count is None:
                    continue
                by_cat.setdefault(str(category).lower(), []).append(
                    {"year": year, "count": int(count)}
                )

    total_points.sort(key=lambda p: p.get("year") or 0)
    for points in by_cat.values():
        points.sort(key=lambda p: p.get("year") or 0)
    return {"total": total_points, "by_category": by_cat}
