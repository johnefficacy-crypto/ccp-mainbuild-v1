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


def _cycle_aggregate(rows: list[dict[str, Any]], count_type: str) -> dict[str, Any] | None:
    """The explicitly-labelled cycle-level aggregate row of ``count_type``
    (``scope_kind='cycle'`` and no ``exam_phase_id``). This is the ONLY row
    permitted to stand for a cycle-level denominator — a phase row is never
    promoted to cycle scope (PD-2, Determinism > Heuristics)."""
    for r in rows:
        if (
            r.get("count_type") == count_type
            and r.get("scope_kind") == "cycle"
            and not r.get("exam_phase_id")
            and r.get("count_value") is not None
        ):
            return r
    return None


def _phase_appeared(rows: list[dict[str, Any]], phase_id: str) -> dict[str, Any] | None:
    """The appeared count for one specific phase (``scope_kind='phase'`` and
    matching ``exam_phase_id``). A Mains row therefore only ever reads a
    Mains appeared count — never another phase's turnout."""
    for r in rows:
        if (
            r.get("count_type") == "appeared"
            and r.get("scope_kind") == "phase"
            and r.get("exam_phase_id") == phase_id
            and r.get("count_value") is not None
        ):
            return r
    return None


def ratio_denominator(
    supabase: Any,
    exam_id: str | None,
    exam_cycle_id: str | None,
    target_phase_id: str | None = None,
) -> tuple[int | None, str | None, dict[str, Any] | None]:
    """Return ``(denominator_value, denominator_label, source_row)``.

    ``denominator_label`` is ``"appeared"`` | ``"applied"`` | ``None``.
    Never estimates: returns ``(None, None, None)`` when no reviewed/locked
    provenance-proven count exists for the scope.

    ``target_phase_id`` selects the denominator granularity deterministically
    (no cross-phase heuristic — PD-2):

    * ``target_phase_id is None`` → **cycle-level** denominator. Use ONLY an
      explicitly-labelled cycle aggregate (``scope_kind='cycle'``): prefer the
      appeared cycle aggregate, then the applied cycle aggregate, else null.
      A phase row is NEVER substituted for a cycle-level denominator.
    * ``target_phase_id`` set → **phase-scoped** denominator. Use only that
      phase's appeared count; if none, fall back to the cycle-level applied
      aggregate (applied is always cycle-scoped, OD-3), else null. A Mains row
      can therefore never show a Prelims count.

    ``exam_cycle_id`` is REQUIRED: candidate counts are cycle-scoped facts,
    so a cycle-less caller (e.g. a legacy reviewed/locked competition metric
    that migration 216 preserved without an ``exam_cycle_id``) fails closed
    with no denominator rather than borrowing a count from another cycle.
    """
    if not exam_id or not exam_cycle_id:
        return None, None, None

    rows = _select_current(_load_counts(supabase, exam_id, exam_cycle_id))
    if not rows:
        return None, None, None

    if target_phase_id is None:
        # Cycle-level: cycle aggregates only, appeared → applied → null.
        for count_type in _DENOMINATOR_PREFERENCE:
            row = _cycle_aggregate(rows, count_type)
            if row is not None:
                return int(row["count_value"]), count_type, row
        return None, None, None

    # Phase-scoped: this phase's appeared count, then the cycle applied
    # aggregate as the only permitted fallback, else null.
    row = _phase_appeared(rows, target_phase_id)
    if row is not None:
        return int(row["count_value"]), "appeared", row
    row = _cycle_aggregate(rows, "applied")
    if row is not None:
        return int(row["count_value"]), "applied", row
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
