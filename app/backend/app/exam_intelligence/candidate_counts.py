"""Applied-vs-Appeared candidate-count read helpers (J3 PR 2).

Reads ``exam_candidate_counts`` rows that have cleared review
(``reviewer_status in ('reviewed', 'locked')``) and derives the
provenance-proven ratio denominator that ``competition.py`` (aspirant
series) and ``competition_context.py`` (Study OS pressure explanation)
both consume — the atomic switch described in resolutions §1.2 PR-2 half.

Denominator preference: ``appeared`` (an aspirant actually sitting the
exam is the truest measure of competition) -> ``applied`` -> ``None``.
Only the official total (``reservation_category_id IS NULL``) is used for
the scalar denominator; per-category counts are exposed separately for
callers that want a category breakdown but never silently substituted for
the total.

No AI. No inference beyond the documented preference order. Nothing is
estimated when no provenance-proven count exists — the ratio fields stay
null (resolutions §1.2: "Only rows with a provenance-proven denominator
ever produce a non-null selection_rate").
"""
from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger("career_copilot.exam_intelligence.candidate_counts")

_READY_STATUSES = ("reviewed", "locked")
_DENOMINATOR_PREFERENCE = ("appeared", "applied")


def _safe(call: Callable[[], Any], default: Any = None) -> Any:
    try:
        return call()
    except Exception as exc:  # noqa: BLE001
        logger.warning("candidate_counts read failed: %s", exc)
        return default


def _load_counts(supabase: Any, exam_id: str, exam_cycle_id: str | None) -> list[dict[str, Any]]:
    # Cycle is mandatory: exam_candidate_counts rows are cycle-scoped, so a
    # cycle-less read would mix counts across cycles. Fail closed instead.
    if not exam_id or not exam_cycle_id:
        return []

    def _builder():
        q = (
            supabase.table("exam_candidate_counts")
            .select(
                "id, exam_id, exam_cycle_id, exam_phase_id, scope_kind, count_type, "
                "reservation_category_id, count_value, is_current_published, "
                "reviewer_status, reviewed_at, created_at"
            )
            .eq("exam_id", exam_id)
            .in_("reviewer_status", list(_READY_STATUSES))
            .is_("reservation_category_id", None)
            .limit(200)
            .eq("exam_cycle_id", exam_cycle_id)
        )
        return q.execute().data

    return _safe(_builder, default=[]) or []


def _select_current(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Shared current-row selector (mirrors competition.py's OD-10 pattern):
    only ``is_current_published`` rows are authoritative — no per-reader
    "pick best" heuristic."""
    return [r for r in rows if r.get("is_current_published")]


def _load_phase_orders(supabase: Any, exam_id: str) -> dict[str, int]:
    rows = _safe(
        lambda: (
            supabase.table("exam_phases")
            .select("id, phase_order")
            .eq("exam_id", exam_id)
            .limit(200)
            .execute()
            .data
        ),
        default=[],
    ) or []
    return {r["id"]: (r.get("phase_order") if r.get("phase_order") is not None else 999999) for r in rows if r.get("id")}


def _pick_representative(rows: list[dict[str, Any]], count_type: str, phase_orders: dict[str, int]) -> dict[str, Any] | None:
    """Among current-published official-total rows of ``count_type`` for the
    scope, prefer the explicitly-labelled cycle-level aggregate
    (``scope_kind='cycle'``); otherwise fall back to the earliest phase
    (lowest ``phase_order``) as the representative denominator — the first
    stage of a multi-phase exam typically has the largest turnout, so it is
    the most conservative (largest, least-selective) appeared/applied
    figure available. This is a documented judgment call, not a silent
    guess: the exact scope used is always returned alongside the value.
    """
    candidates = [r for r in rows if r.get("count_type") == count_type]
    if not candidates:
        return None
    cycle_agg = [r for r in candidates if r.get("scope_kind") == "cycle"]
    if cycle_agg:
        return cycle_agg[0]
    phase_rows = [r for r in candidates if r.get("scope_kind") == "phase"]
    if not phase_rows:
        return None
    phase_rows.sort(key=lambda r: phase_orders.get(r.get("exam_phase_id"), 999999))
    return phase_rows[0]


def ratio_denominator(
    supabase: Any, exam_id: str | None, exam_cycle_id: str | None
) -> tuple[int | None, str | None, dict[str, Any] | None]:
    """Return ``(denominator_value, denominator_label, source_row)``.

    ``denominator_label`` is ``"appeared"`` | ``"applied"`` | ``None``.
    Never estimates: returns ``(None, None, None)`` when no reviewed/locked
    provenance-proven count exists for the scope.

    ``exam_cycle_id`` is REQUIRED: candidate counts are cycle-scoped facts,
    so a cycle-less caller (e.g. a legacy reviewed/locked competition
    metric that migration 216 preserved without an ``exam_cycle_id``)
    fails closed with no denominator rather than borrowing an arbitrary
    count from some other cycle of the exam.
    """
    if not exam_id or not exam_cycle_id:
        return None, None, None

    rows = _select_current(_load_counts(supabase, exam_id, exam_cycle_id))
    if not rows:
        return None, None, None
    phase_orders = _load_phase_orders(supabase, exam_id)

    for count_type in _DENOMINATOR_PREFERENCE:
        row = _pick_representative(rows, count_type, phase_orders)
        if row is not None and row.get("count_value") is not None:
            return int(row["count_value"]), count_type, row

    return None, None, None


def derive_rates(
    vacancy_total: int | float | None, denominator: int | None
) -> tuple[float | None, float | None]:
    """Return ``(selection_rate, candidates_per_vacancy)``.

    ``selection_rate`` = vacancies / denominator (chance of selection).
    ``candidates_per_vacancy`` = denominator / vacancies (inverse — how many
    candidates compete per seat). Both null unless both inputs are
    positive numbers — never divide by zero, never guess.
    """
    try:
        vac = float(vacancy_total) if vacancy_total is not None else None
    except (TypeError, ValueError):
        vac = None
    try:
        denom = float(denominator) if denominator is not None else None
    except (TypeError, ValueError):
        denom = None
    if vac is None or denom is None or vac <= 0 or denom <= 0:
        return None, None
    return vac / denom, denom / vac
