"""Regulatory shared-core overlap — the substrate for the combined multi-exam
Study OS plan (Lane R R2, increment 1).

Read-only: introduces no plan mutation and does not touch ``_compute_plan``.
Applying the allocation + cross-exam dedup inside the plan loop is increment 2.

Correctness invariants (checkpost PR #981):
  * Canonical target-exam sources — ``aspirant_preferences.target_exams`` (slug
    list) + ``profiles.target_exam`` (primary UUID); there is no
    ``user_study_plan_preferences.target_exams``.
  * Mastery is on the **0–100** scale (``user_topic_mastery.mastery_score``,
    numeric(5,2)); the reuse threshold is 70.
  * Cross-exam reuse is FAIL-CLOSED: only a **global** mastery row (``exam_id IS
    NULL``) counts, so mastery earned for one regulator never suppresses a topic
    for another.
  * Shared core is computed from **common** coverage only (``exam_topic_coverage
    .stream_id IS NULL``); stream-specific (Legal/Actuarial/…) topics are never
    misclassified as shared — they are reported separately.
  * Reads distinguish failure from emptiness (``_READ_FAILED`` sentinel): any
    required-input read failure yields an ``unavailable`` diagnostic, never a
    summary recomputed from a partial snapshot.
  * Deterministic: exams sorted by slug; every list sorted.

The 70/20/10 allocation is the DOCUMENTED DEFAULT from
``docs/architecture/financial-regulatory-development-family.md`` §8 — not an
owner-locked policy; it is returned with a basis note and a per-band shortfall
flag, and is all-zero whenever the summary is not ``ok``.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Iterable, Mapping

logger = logging.getLogger("career_copilot.study_os.shared_core")

FINANCIAL_REGULATORY_FAMILY_SLUG = "financial-regulatory"
MASTERY_SCALE = "0-100"
DEFAULT_MASTERY_THRESHOLD = 70.0  # 0–100 scale
DEFAULT_ALLOCATION: tuple[float, float, float] = (0.70, 0.20, 0.10)
ALLOCATION_BASIS = (
    "financial-regulatory-development-family.md §8 (documented default; "
    "not owner-locked)"
)

# Distinguishes a read *failure* from a legitimately empty result.
_READ_FAILED = object()


# ── Pure functions ───────────────────────────────────────────────────────────

def _clean_set(topics: Iterable[Any]) -> set[str]:
    return {str(t) for t in topics if t}


def partition_topics(coverage_by_exam: Mapping[str, Iterable[Any]]) -> dict[str, Any]:
    """Split the union of the exams' COMMON locked topics into shared-core vs
    per-exam delta. A topic covered by ≥2 exams is shared core; a topic in
    exactly one is that exam's delta. Lists sorted."""
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
    mastered_global: Iterable[Any],
) -> list[dict[str, Any]]:
    """Shared-core topics the user has mastered GLOBALLY — reuse instead of
    re-planning per exam. ``mastered_global`` must already be restricted to
    global (exam_id IS NULL) mastery rows ≥ threshold. A topic qualifies only if
    it is covered by ≥2 exams. Returns ``[{topic_id, exams:[…]}]`` sorted."""
    sets: dict[str, set[str]] = {
        str(exam_id): _clean_set(topics) for exam_id, topics in coverage_by_exam.items()
    }
    out: list[dict[str, Any]] = []
    for t in sorted(_clean_set(mastered_global)):
        exams = sorted(exam_id for exam_id, topics in sets.items() if t in topics)
        if len(exams) >= 2:
            out.append({"topic_id": t, "exams": exams})
    return out


def allocation_targets(
    total: int, weights: tuple[float, float, float] = DEFAULT_ALLOCATION
) -> dict[str, int]:
    """Split ``total`` task slots into shared_core / target_delta / current_affairs
    integer counts summing EXACTLY to ``total`` (largest-remainder, fixed band
    order breaks ties)."""
    bands = ("shared_core", "target_delta", "current_affairs")
    if total <= 0:
        return {b: 0 for b in bands}
    wsum = sum(weights) or 1.0
    raw = [total * (x / wsum) for x in weights]
    floors = [int(r) for r in raw]
    remainder = total - sum(floors)
    order = sorted(range(len(bands)), key=lambda i: (raw[i] - floors[i], -i), reverse=True)
    for i in order[:remainder]:
        floors[i] += 1
    return dict(zip(bands, floors))


# ── DB-aware wrapper ─────────────────────────────────────────────────────────

def _try(call: Callable[[], Any]) -> Any:
    """Return the call result, or ``_READ_FAILED`` on any exception."""
    try:
        return call()
    except Exception as exc:  # noqa: BLE001
        logger.warning("shared_core supabase read failed: %s", exc)
        return _READ_FAILED


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _resolve_regulatory_target_exams(supabase: Any, user_id: str) -> Any:
    """The user's tracked exams that belong to the financial-regulatory family
    and are active, sorted by slug. Returns ``[{id, slug, name}, …]``, or
    ``_READ_FAILED`` if a required read failed. An empty family (not seeded) or an
    empty tracked list yields ``[]`` (a legitimate empty, not a failure)."""
    fam = _try(lambda: (
        supabase.table("exam_families").select("id")
        .eq("slug", FINANCIAL_REGULATORY_FAMILY_SLUG).limit(1).execute().data
    ))
    if fam is _READ_FAILED:
        return _READ_FAILED
    fam = fam or []
    if not fam:
        return []
    family_id = fam[0]["id"]

    prefs = _try(lambda: (
        supabase.table("aspirant_preferences").select("target_exams")
        .eq("user_id", user_id).limit(1).execute().data
    ))
    profile = _try(lambda: (
        supabase.table("profiles").select("target_exam").eq("id", user_id).limit(1).execute().data
    ))
    if prefs is _READ_FAILED or profile is _READ_FAILED:
        return _READ_FAILED
    slugs = [str(s) for s in ((prefs or [{}])[0].get("target_exams") or []) if s]
    primary_id = (profile or [{}])[0].get("target_exam")

    by_slug: list[dict[str, Any]] = []
    if slugs:
        rows = _try(lambda: (
            supabase.table("exams").select("id, slug, name, exam_family_id, is_active")
            .in_("slug", slugs).eq("exam_family_id", family_id).eq("is_active", True)
            .execute().data
        ))
        if rows is _READ_FAILED:
            return _READ_FAILED
        by_slug = rows or []
    by_id: list[dict[str, Any]] = []
    if primary_id:
        rows = _try(lambda: (
            supabase.table("exams").select("id, slug, name, exam_family_id, is_active")
            .eq("id", primary_id).eq("exam_family_id", family_id).eq("is_active", True)
            .execute().data
        ))
        if rows is _READ_FAILED:
            return _READ_FAILED
        by_id = rows or []

    merged: dict[str, dict[str, Any]] = {}
    for r in list(by_slug) + list(by_id):
        merged[r["id"]] = {"id": r["id"], "slug": r.get("slug"), "name": r.get("name")}
    return sorted(merged.values(), key=lambda e: (e.get("slug") or "", e["id"]))


def _read_common_coverage(supabase: Any, exam_id: str) -> Any:
    """Locked COMMON (stream_id IS NULL) topic_ids for one exam + a count of
    stream-specific topics (excluded from shared core). ``_READ_FAILED`` on
    failure — never an empty set that would masquerade as 'no coverage'."""
    rows = _try(lambda: (
        supabase.table("exam_topic_coverage").select("topic_id, stream_id")
        .eq("exam_id", exam_id).eq("reviewer_status", "locked").limit(5000).execute().data
    ))
    if rows is _READ_FAILED:
        return _READ_FAILED
    rows = rows or []
    common = sorted({r["topic_id"] for r in rows if r.get("topic_id") and r.get("stream_id") is None})
    stream_specific = len({r["topic_id"] for r in rows if r.get("topic_id") and r.get("stream_id") is not None})
    return {"common": common, "stream_specific_count": stream_specific}


def _read_global_mastery(supabase: Any, user_id: str, threshold: float) -> Any:
    """Topic_ids the user has mastered GLOBALLY (``exam_id IS NULL`` row ≥
    threshold on the 0–100 scale). ``_READ_FAILED`` on failure."""
    rows = _try(lambda: (
        supabase.table("user_topic_mastery").select("topic_id, exam_id, mastery_score")
        .eq("user_id", user_id).limit(5000).execute().data
    ))
    if rows is _READ_FAILED:
        return _READ_FAILED
    return {
        r["topic_id"]
        for r in (rows or [])
        if r.get("topic_id") and r.get("exam_id") is None and _num(r.get("mastery_score")) >= threshold
    }


def _base(exams: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "exams": exams,
        "shared_core": [],
        "delta_by_exam": {e["id"]: [] for e in exams},
        "stream_specific_by_exam": {e["id"]: 0 for e in exams},
        "mastery_reuse": [],
        "mastery_scale": MASTERY_SCALE,
        "allocation": {"shared_core": 0, "target_delta": 0, "current_affairs": 0},
        "allocation_basis": ALLOCATION_BASIS,
        "shortfall": [],
    }


def summarize_regulatory_overlap(
    supabase: Any,
    user_id: str,
    *,
    total_tasks: int = 10,
    mastery_threshold: float = DEFAULT_MASTERY_THRESHOLD,
) -> dict[str, Any]:
    """Read-only shared-core overlap for the user's active regulatory target
    exams. Never raises. On any required-input read failure returns
    ``{"status":"unavailable", "reason": …}`` rather than a summary computed from
    a partial snapshot."""
    exams = _resolve_regulatory_target_exams(supabase, user_id)
    if exams is _READ_FAILED:
        return {**_base([]), "status": "unavailable", "reason": "target_exams_read_failed"}
    if len(exams) < 2:
        return {**_base(exams), "status": "insufficient_regulatory_exams"}

    common_by_exam: dict[str, list[str]] = {}
    stream_specific_by_exam: dict[str, int] = {}
    for e in exams:
        cov = _read_common_coverage(supabase, e["id"])
        if cov is _READ_FAILED:
            return {**_base(exams), "status": "unavailable", "reason": f"coverage_read_failed:{e['id']}"}
        common_by_exam[e["id"]] = cov["common"]
        stream_specific_by_exam[e["id"]] = cov["stream_specific_count"]

    mastered = _read_global_mastery(supabase, user_id, mastery_threshold)
    if mastered is _READ_FAILED:
        return {**_base(exams), "status": "unavailable", "reason": "mastery_read_failed"}

    part = partition_topics(common_by_exam)
    delta_total = sum(len(v) for v in part["delta_by_exam"].values())

    # Allocation is all-zero unless there is a shared-core basis; per-band
    # shortfall names any band whose default target exceeds its candidate count.
    if part["shared_core"]:
        alloc = allocation_targets(total_tasks)
    else:
        alloc = {"shared_core": 0, "target_delta": 0, "current_affairs": 0}
    shortfall: list[str] = []
    if alloc["shared_core"] > len(part["shared_core"]):
        shortfall.append("shared_core")
    if alloc["target_delta"] > delta_total:
        shortfall.append("target_delta")
    if alloc["current_affairs"] > 0:
        shortfall.append("current_affairs:external(Lane GQR)")

    return {
        "status": "ok",
        "exams": exams,
        "shared_core": part["shared_core"],
        "delta_by_exam": part["delta_by_exam"],
        "stream_specific_by_exam": stream_specific_by_exam,
        "mastery_reuse": mastery_reuse(common_by_exam, mastered),
        "mastery_scale": MASTERY_SCALE,
        "mastery_threshold": mastery_threshold,
        "allocation": alloc,
        "allocation_basis": ALLOCATION_BASIS,
        "shortfall": shortfall,
    }
