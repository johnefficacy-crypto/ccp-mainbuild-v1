"""Competition Intelligence context for Study OS (read-only).

Reads ``exam_competition_metrics`` (migration 055) and exposes the
verified competition picture for an exam: vacancy, applicant ratio,
cutoff / difficulty trends and a derived cycle-pressure block.

Verified-only contract: only ``reviewer_status in ('locked', 'reviewed')``
rows are read, and ``locked`` is preferred over ``reviewed``. Nothing is
estimated silently — when no reviewed row exists the helper returns a
safe ``available=False`` shape. There is no AI and no scraping here.
"""
from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger("career_copilot.study_os.competition_context")

_READABLE_STATUSES = ("locked", "reviewed")


def _safe(call: Callable[[], Any], default: Any = None) -> Any:
    try:
        return call()
    except Exception as exc:  # noqa: BLE001
        logger.warning("competition_context read failed: %s", exc)
        return default


def _empty(exam_id: str | None = None) -> dict[str, Any]:
    return {
        "available": False,
        "exam_id": exam_id,
        "exam_cycle_id": None,
        "exam_phase_id": None,
        "vacancy_total": None,
        "vacancy_by_category": {},
        "applicant_count": None,
        "selection_ratio": None,
        "selection_ratio_legacy": None,
        "selection_rate": None,
        "candidates_per_vacancy": None,
        "ratio_denominator": None,
        "cutoff_trend": {},
        "difficulty_trend": {},
        "cutoff_by_category": {},
        "difficulty_assessment": {},
        "competition_pressure_score": None,
        "cycle_pressure": {
            "days_remaining": None,
            "pressure_level": "unknown",
            "reason": None,
        },
        "trust": {
            "source_basis": None,
            "reviewer_status": None,
            "confidence_score": None,
            "evidence_count": 0,
        },
    }


def _pick_best(
    rows: list[dict[str, Any]], exam_cycle_id: str | None
) -> dict[str, Any] | None:
    """Pick the authoritative cycle_summary metrics row for the requested
    (or, if absent, the most recent) cycle.

    OD-10 shared selector: rows disposed with a metric_kind use
    ``is_current_published`` as the single source of truth — never a
    per-reader "best row" heuristic. Legacy undisposed rows
    (metric_kind IS NULL) fall back to the prior locked-preferred /
    latest-created heuristic so pre-migration data is not dropped.
    """
    if not rows:
        return None

    cycle_summary_rows = [r for r in rows if r.get("metric_kind") == "cycle_summary"]
    current = [r for r in cycle_summary_rows if r.get("is_current_published")]
    if current:
        if exam_cycle_id:
            for r in current:
                if r.get("exam_cycle_id") == exam_cycle_id:
                    return r
        # No exact cycle match requested/found — most recently reviewed wins.
        return sorted(current, key=lambda r: str(r.get("reviewed_at") or r.get("created_at") or ""), reverse=True)[0]

    legacy = [r for r in rows if r.get("metric_kind") is None]
    if not legacy:
        return None

    def _key(r: dict[str, Any]) -> tuple:
        cycle_match = 1 if exam_cycle_id and r.get("exam_cycle_id") == exam_cycle_id else 0
        locked = 1 if r.get("reviewer_status") == "locked" else 0
        return (cycle_match, locked, str(r.get("created_at") or ""))

    return sorted(legacy, key=_key, reverse=True)[0]




def _pressure_level(score: float | None, days_remaining: int | None) -> str:
    """Coarse, deterministic pressure bucket.

    Driven primarily by the reviewed ``competition_pressure_score`` and
    nudged up one bucket when the exam is very close.
    """
    if score is None:
        return "unknown"
    if score >= 66:
        level = "high"
    elif score >= 33:
        level = "medium"
    else:
        level = "low"
    if days_remaining is not None and days_remaining <= 30:
        level = {"low": "medium", "medium": "high", "high": "high"}[level]
    return level


def _pressure_reason(
    level: str, days_remaining: int | None, selection_ratio: float | None
) -> str | None:
    if level == "unknown":
        return None
    bits: list[str] = []
    if days_remaining is not None:
        bits.append(f"{days_remaining} days to the exam")
    if selection_ratio is not None and selection_ratio > 0:
        bits.append(f"selection ratio ~{selection_ratio:.4f}")
    if not bits:
        return f"Competition pressure is {level}."
    return f"Competition pressure is {level} ({', '.join(bits)})."


def competition_context(
    supabase: Any,
    exam_id: str | None,
    *,
    exam_cycle_id: str | None = None,
    days_remaining: int | None = None,
) -> dict[str, Any]:
    """Return the ``competition_context`` block for ``exam_id``.

    ``days_remaining`` is supplied by the caller (Mission Control already
    computes it from ``exam_cycles``) so this helper never duplicates that
    read. Always returns a dict — never raises.
    """
    if not exam_id:
        return _empty(exam_id)

    rows = _safe(
        lambda: (
            supabase.table("exam_competition_metrics")
            .select(
                "id, exam_id, exam_cycle_id, exam_phase_id, vacancy_total, "
                "vacancy_by_category, applicant_count, selection_ratio, "
                "cutoff_trend, difficulty_trend, cutoff_by_category, "
                "difficulty_assessment, metric_kind, is_current_published, "
                "competition_pressure_score, "
                "source_basis, confidence_score, evidence_count, "
                "reviewer_status, reviewed_at, created_at"
            )
            .eq("exam_id", exam_id)
            .in_("reviewer_status", list(_READABLE_STATUSES))
            .limit(200)
            .execute()
            .data
        ),
        default=[],
    ) or []

    best = _pick_best(rows, exam_cycle_id)
    if not best:
        return _empty(exam_id)

    # This function is not called with an explicit phase — pick the
    # current-published phase_cutoff row for whichever cycle `best` resolved
    # to (there is at most one per cycle+phase, and typically one phase per
    # cycle in the read paths that call this helper).
    resolved_cycle_id = best.get("exam_cycle_id")
    phase_cutoff = next(
        (
            r for r in rows
            if r.get("metric_kind") == "phase_cutoff"
            and r.get("is_current_published")
            and r.get("exam_cycle_id") == resolved_cycle_id
        ),
        None,
    )

    score = best.get("competition_pressure_score")
    try:
        score = float(score) if score is not None else None
    except (TypeError, ValueError):
        score = None

    selection_ratio = best.get("selection_ratio")
    try:
        selection_ratio = float(selection_ratio) if selection_ratio is not None else None
    except (TypeError, ValueError):
        selection_ratio = None

    level = _pressure_level(score, days_remaining)
    return {
        "available": True,
        "exam_id": exam_id,
        "exam_cycle_id": best.get("exam_cycle_id"),
        "exam_phase_id": (phase_cutoff or {}).get("exam_phase_id"),
        "vacancy_total": best.get("vacancy_total"),
        "vacancy_by_category": best.get("vacancy_by_category") or {},
        "applicant_count": best.get("applicant_count"),
        "selection_ratio": selection_ratio,
        # Ratio contract, PR-1 half (resolutions §1.2): the provenance-proven
        # applied/appeared denominator lands in PR 2 — these stay null until
        # then, never derived from the ambiguous legacy applicant_count.
        "selection_ratio_legacy": selection_ratio,
        "selection_rate": None,
        "candidates_per_vacancy": None,
        "ratio_denominator": None,
        "cutoff_trend": (phase_cutoff or best).get("cutoff_trend") or {},
        "difficulty_trend": (phase_cutoff or best).get("difficulty_trend") or {},
        "cutoff_by_category": (phase_cutoff or {}).get("cutoff_by_category") or {},
        "difficulty_assessment": (phase_cutoff or {}).get("difficulty_assessment") or {},
        "competition_pressure_score": score,
        "cycle_pressure": {
            "days_remaining": days_remaining,
            "pressure_level": level,
            "reason": _pressure_reason(level, days_remaining, selection_ratio),
        },
        "trust": {
            "source_basis": best.get("source_basis"),
            "reviewer_status": best.get("reviewer_status"),
            "confidence_score": best.get("confidence_score"),
            "evidence_count": best.get("evidence_count") or 0,
        },
    }
