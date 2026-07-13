"""Regulatory shared-core overlap — the substrate for the combined multi-exam
Study OS plan (Lane R R2, increment 1).

The planner (`planner._compute_plan`) is single-target-exam today. Before it can
produce ONE combined plan across a user's several regulatory target exams
(≈70% shared foundation / 20% target-regulator delta / 10% current affairs) and
avoid re-planning a common topic already mastered, it needs a deterministic model
of *what is shared vs. regulator-specific* across those exams. That model lives
here as pure, side-effect-free functions plus one defensive DB wrapper.

This increment is read-only: it introduces no plan mutation and does not touch
`_compute_plan`. Applying the allocation + cross-exam dedup inside the plan loop
is increment 2 (a separate, focused PR).

Determinism: every function is a pure map over sorted inputs — no `Date.now`,
no randomness — so the same inputs always yield byte-identical output, matching
the planner's deterministic contract.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Iterable, Mapping

logger = logging.getLogger("career_copilot.study_os.shared_core")

# Default 70/20/10 split (shared foundation / target-regulator delta / current
# affairs). Weights are a named default so the planner and tests share one
# source of truth; the split is applied by ``allocation_targets`` with a
# largest-remainder rounding so the parts always sum to the requested total.
DEFAULT_ALLOCATION: tuple[float, float, float] = (0.70, 0.20, 0.10)

FINANCIAL_REGULATORY_FAMILY_SLUG = "financial-regulatory"


# ── Pure functions ───────────────────────────────────────────────────────────

def _clean_set(topics: Iterable[Any]) -> set[str]:
    return {str(t) for t in topics if t}


def partition_topics(
    coverage_by_exam: Mapping[str, Iterable[Any]],
) -> dict[str, Any]:
    """Split the union of the exams' locked topics into shared-core vs per-exam
    delta.

    ``coverage_by_exam`` maps exam_id → the topic_ids locked for that exam. A
    topic covered by TWO OR MORE of the exams is shared core (author/study once,
    counts for all that cover it); a topic covered by exactly one is that exam's
    delta.

    Returns ``{"shared_core": [topic_id, …],
               "delta_by_exam": {exam_id: [topic_id, …]}}`` — all lists sorted.
    """
    sets: dict[str, set[str]] = {
        str(exam_id): _clean_set(topics) for exam_id, topics in coverage_by_exam.items()
    }
    counts: dict[str, int] = {}
    for topics in sets.values():
        for t in topics:
            counts[t] = counts.get(t, 0) + 1
    shared = {t for t, c in counts.items() if c >= 2}
    return {
        "shared_core": sorted(shared),
        "delta_by_exam": {exam_id: sorted(topics - shared) for exam_id, topics in sets.items()},
    }


def mastery_reuse(
    coverage_by_exam: Mapping[str, Iterable[Any]],
    mastered: Iterable[Any],
) -> list[dict[str, Any]]:
    """Shared-core topics the user has already mastered — so the combined plan
    reuses them instead of re-planning the same foundation per exam.

    A topic qualifies only if it is (a) mastered and (b) covered by ≥2 of the
    exams (i.e. genuinely shared). Returns
    ``[{"topic_id": t, "exams": [exam_id, …]}, …]`` sorted by topic_id, with each
    ``exams`` list sorted.
    """
    sets: dict[str, set[str]] = {
        str(exam_id): _clean_set(topics) for exam_id, topics in coverage_by_exam.items()
    }
    mastered_set = _clean_set(mastered)
    out: list[dict[str, Any]] = []
    for t in sorted(mastered_set):
        exams = sorted(exam_id for exam_id, topics in sets.items() if t in topics)
        if len(exams) >= 2:
            out.append({"topic_id": t, "exams": exams})
    return out


def allocation_targets(
    total: int,
    weights: tuple[float, float, float] = DEFAULT_ALLOCATION,
) -> dict[str, int]:
    """Split ``total`` task slots into shared-core / target-delta / current-affairs
    integer counts that sum EXACTLY to ``total`` (largest-remainder rounding).

    Deterministic: ties in the remainder are broken by fixed band order
    (shared_core, target_delta, current_affairs), so the output never depends on
    dict/iteration order.
    """
    bands = ("shared_core", "target_delta", "current_affairs")
    if total <= 0:
        return {b: 0 for b in bands}
    w = list(weights)
    wsum = sum(w) or 1.0
    raw = [total * (x / wsum) for x in w]
    floors = [int(r) for r in raw]
    remainder = total - sum(floors)
    # Distribute the remainder to the largest fractional parts; fixed band order
    # breaks exact ties deterministically.
    order = sorted(range(len(bands)), key=lambda i: (raw[i] - floors[i], -i), reverse=True)
    for i in order[:remainder]:
        floors[i] += 1
    return dict(zip(bands, floors))


# ── DB-aware wrapper ─────────────────────────────────────────────────────────

def _safe(call: Callable[[], Any], default: Any = None) -> Any:
    try:
        return call()
    except Exception as exc:  # noqa: BLE001
        logger.warning("shared_core supabase call failed: %s", exc)
        return default


def _resolve_regulatory_target_exams(supabase: Any, user_id: str) -> list[dict[str, Any]]:
    """The user's target exams that belong to the financial-regulatory family and
    are active. Returns ``[{id, slug, name}, …]`` (possibly empty)."""
    fam = _safe(
        lambda: (
            supabase.table("exam_families")
            .select("id")
            .eq("slug", FINANCIAL_REGULATORY_FAMILY_SLUG)
            .limit(1)
            .execute()
            .data
        ),
        default=[],
    ) or []
    if not fam:
        return []
    family_id = fam[0]["id"]

    prefs = _safe(
        lambda: (
            supabase.table("user_study_plan_preferences")
            .select("target_exams")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
            .data
        ),
        default=[],
    ) or []
    target_ids = (prefs[0] if prefs else {}).get("target_exams") or []
    target_ids = [str(t) for t in target_ids if t]
    if not target_ids:
        return []

    rows = _safe(
        lambda: (
            supabase.table("exams")
            .select("id, slug, name, exam_family_id, is_active")
            .in_("id", target_ids)
            .eq("exam_family_id", family_id)
            .eq("is_active", True)
            .execute()
            .data
        ),
        default=[],
    ) or []
    return [{"id": r["id"], "slug": r.get("slug"), "name": r.get("name")} for r in rows]


def summarize_regulatory_overlap(
    supabase: Any,
    user_id: str,
    *,
    total_tasks: int = 10,
    mastery_threshold: float = 0.7,
) -> dict[str, Any]:
    """Read-only shared-core overlap for the user's active regulatory target exams.

    Deterministic given the DB state. ``mastery_threshold`` defines "mastered"
    for reuse (provisional — the planner scores mastery continuously; this binary
    cut is a review knob, not a verdict). Never raises: any read failure yields an
    empty, honest summary rather than a wrong one.

    Shape::

        {
          "exams": [{id, slug, name}, …],
          "shared_core": [topic_id, …],
          "delta_by_exam": {exam_id: [topic_id, …]},
          "mastery_reuse": [{topic_id, exams:[…]}, …],
          "allocation": {"shared_core": n, "target_delta": n, "current_affairs": n},
        }
    """
    from app.exam_intelligence.coverage import locked_topic_coverage

    exams = _resolve_regulatory_target_exams(supabase, user_id)
    if len(exams) < 2:
        # Overlap is only meaningful across ≥2 regulatory exams.
        return {
            "exams": exams,
            "shared_core": [],
            "delta_by_exam": {e["id"]: [] for e in exams},
            "mastery_reuse": [],
            "allocation": allocation_targets(total_tasks),
        }

    coverage_by_exam: dict[str, list[str]] = {}
    for e in exams:
        rows = _safe(lambda e=e: locked_topic_coverage(supabase, e["id"]), default=[]) or []
        coverage_by_exam[e["id"]] = [r.get("topic_id") for r in rows if r.get("topic_id")]

    mastery_rows = _safe(
        lambda: (
            supabase.table("user_topic_mastery")
            .select("topic_id, mastery_score")
            .eq("user_id", user_id)
            .limit(5000)
            .execute()
            .data
        ),
        default=[],
    ) or []
    mastered = {
        r.get("topic_id")
        for r in mastery_rows
        if r.get("topic_id") and _num(r.get("mastery_score")) >= mastery_threshold
    }

    part = partition_topics(coverage_by_exam)
    return {
        "exams": exams,
        "shared_core": part["shared_core"],
        "delta_by_exam": part["delta_by_exam"],
        "mastery_reuse": mastery_reuse(coverage_by_exam, mastered),
        "allocation": allocation_targets(total_tasks),
    }


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
