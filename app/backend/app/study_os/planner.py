"""Phase 7 — deterministic Study OS planner.

``generate_plan(supabase, user_id)`` composes a day's ``study_tasks`` from
the four Study OS input groups:

  User        — persona ``study_policy`` (task count / sizing),
                ``user_topic_mastery`` (weakness), ``user_topic_error_patterns``.
  Exam        — locked ``exam_topic_coverage`` (priority / high-yield),
                verified PYQ topic counts (frequency),
                ``topic_prerequisites`` (ordering).
  Competition — ``competition_context`` cycle pressure (intensity bias).
  Policy      — ``policy_update_context`` (informational; an official
                ``affects_syllabus`` change surfaces a flag).
  Analytical snapshots — locked ``exam_topic_score_snapshots`` (reviewed AI priority
                          signal; confidence-weighted, max 15 pts additive; read
                          failure degrades gracefully to zero — plan still generates).

Deterministic and defensive: no AI, no randomness — the same inputs always
produce the same plan. Persists one active ``study_plan`` per user, a
``study_plan_versions`` audit row, the day's ``study_tasks`` (each with a
``priority_score`` and a ``why_this_task`` explanation), and a
``study_adaptation_events`` row. ``generate_plan`` never raises.
"""
from __future__ import annotations

import logging
import threading
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable

from cachetools import TTLCache

from app.exam_intelligence.coverage import verified_pyq_topic_counts
from app.exam_intelligence.lookup import resolve_exam_by_id, resolve_exam_by_slug
from app.exam_intelligence.score_snapshots import locked_score_snapshots
from app.study_os import calibration
from app.study_os.competition_context import competition_context
from app.study_os.exam_target_window import resolve_exam_target_window
from app.study_os.plan_preferences import focus_weights, get_plan_preferences
from app.study_os.update_context import policy_update_context
from app.study_os.writing_practice import planner_tasks
from app.study_os.writing_practice.launch import LAUNCH_ENGLISH_WRITING_SESSION
from app.utils.safe import safe_required

logger = logging.getLogger("career_copilot.study_os.planner")

PLANNER_VERSION = "planner_v1"

# Typed launch target for practice/revision tasks (PYQ v2 PR-9). Kept as a
# local string literal rather than importing from ``study_os.pyq_practice_launch``
# to avoid a cross-lane import dependency; a shared constant can be unified later.
LAUNCH_PYQ_PRACTICE = "pyq_practice"

# task_type values whose plan tasks resolve to a PYQ topic-practice launch.
_LAUNCH_STAMP_TASK_TYPES = {"retrieval_practice", "revision"}

# EWP-5: max auto-generated english_writing_session tasks per plan generation.
# Writing tasks are additive (a distinct modality) and bounded so they never
# crowd out the topic-study plan.
_MAX_WRITING_TASKS = 2

# preferred_task_size -> minutes per task block.
_SIZE_MINUTES = {"small": 25, "medium": 40, "large": 60}
_DEFAULT_SIZE = "medium"

# The soonest upcoming exam cycle is identical across users and only changes
# daily. Cache it (keyed by exam_id + date) so the several planner reads of
# exam_cycles for one exam within a request wave — e.g. mission-control's
# regen-trigger fan-out, which also computes days-remaining for the same exam —
# collapse to a single round-trip. Reset between tests via tests/conftest.py.
# ``False`` is the sentinel for 'no upcoming cycle'.
_NEXT_CYCLE_TTL_SECONDS = 600
_next_cycle_cache: TTLCache = TTLCache(maxsize=256, ttl=_NEXT_CYCLE_TTL_SECONDS)
_next_cycle_lock = threading.Lock()


def invalidate_planner_cache() -> None:
    """Drop the planner's process-local caches (test hook / admin reset)."""
    with _next_cycle_lock:
        _next_cycle_cache.clear()


def _cached_next_cycle(supabase: Any, exam_id: str, today_iso: str) -> dict[str, Any] | None:
    """Soonest upcoming exam cycle (``id, exam_start, cycle_name``) for an exam,
    per-exam+date TTL cached. Returns ``None`` when there is no upcoming cycle."""
    cache_key = (exam_id, today_iso)
    with _next_cycle_lock:
        if cache_key in _next_cycle_cache:
            cached = _next_cycle_cache[cache_key]
            return None if cached is False else cached
    rows = (
        _safe(
            lambda: (
                supabase.table("exam_cycles")
                .select("id, exam_start, cycle_name")
                .eq("exam_id", exam_id)
                .gte("exam_start", today_iso)
                .order("exam_start")
                .limit(1)
                .execute()
                .data
            ),
            default=[],
        )
        or []
    )
    cycle = rows[0] if rows else None
    with _next_cycle_lock:
        _next_cycle_cache[cache_key] = cycle if cycle else False
    return cycle
_DEFAULT_MAX_TASKS = 4

_TASK_LABEL = {
    "concept_learning": "Concept learning",
    "retrieval_practice": "Retrieval practice",
    "revision": "Revision",
}

# topic_prerequisites relation types that gate ordering.
_ORDERING_RELATIONS = {"requires", "recommended_before"}

# Sentinel distinguishing a failed read from a legitimately-empty result.
# Used by ``_load_user_signals`` so a transient ``user_topic_mastery`` read
# failure does NOT look like "user has no validated mastery" (which would let a
# self-report wrongly override real evidence). When in doubt, fail closed.
_READ_FAILED = object()


def _safe(call: Callable[[], Any], default: Any = None) -> Any:
    try:
        return call()
    except Exception as exc:  # noqa: BLE001
        logger.warning("planner read/write failed: %s", exc)
        return default


def _today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


# ─── Input gathering ──────────────────────────────────────────────────────
def _resolve_target_exam(supabase: Any, user_id: str) -> dict[str, Any] | None:
    """Resolve the user's target exam to a full ``exams`` row (or None)."""
    profile = (
        _safe(
            lambda: (
                supabase.table("profiles")
                .select("target_exam")
                .eq("id", user_id)
                .limit(1)
                .execute()
                .data
            ),
            default=[],
        )
        or []
    )
    target = (profile[0] if profile else {}).get("target_exam")
    if not target:
        prefs = (
            _safe(
                lambda: (
                    supabase.table("aspirant_preferences")
                    .select("target_exams")
                    .eq("user_id", user_id)
                    .limit(1)
                    .execute()
                    .data
                ),
                default=[],
            )
            or []
        )
        exams = (prefs[0] if prefs else {}).get("target_exams") or []
        if isinstance(exams, list) and exams:
            target = exams[0]
    if not target:
        return None
    candidate = str(target)
    if len(candidate) == 36 and candidate.count("-") == 4:
        exam = resolve_exam_by_id(supabase, candidate)
        if exam:
            return exam
    return resolve_exam_by_slug(supabase, candidate)


_OPERATIONAL_CYCLE_STATUSES = ("expected", "open", "active")


def _cycle_planner_exposed(supabase: Any, cycle_id: str | None) -> bool:
    """D12/D14 canonical planner / Study-OS exposure for a cycle.

    Exposure requires BOTH: the cycle is operational (``status`` in
    ``expected``/``open``/``active``) AND ``planner_activation_enabled`` is set — read from the
    same resolved cycle row so the planner and cycle_readiness Step 9 agree on the SAME authority.
    ``resolve_exam_target_window`` only excludes ``cancelled`` cycles and its fallback can select a
    ``closed``/``completed`` cycle; readiness marks such a cycle Step 9 not_applicable (D05 §6:
    activation policy applies only to operational cycles), so the planner MUST refuse it too or the
    exact readiness↔planner drift this gate removes would reappear.

    Fail-closed: no cycle, a read failure, a non-operational status, or an unset flag → not exposed
    (a `light` exam is never planner-activated without an explicit per-cycle opt-in).
    """
    if not cycle_id:
        return False
    rows = _safe(
        lambda: (
            supabase.table("exam_cycles")
            .select("status, planner_activation_enabled")
            .eq("id", cycle_id)
            .limit(1)
            .execute()
            .data
        ),
        default=None,
    )
    if not rows:
        return False
    row = rows[0]
    if (row.get("status") or "") not in _OPERATIONAL_CYCLE_STATUSES:
        return False
    return bool(row.get("planner_activation_enabled"))


def _days_remaining(supabase: Any, exam_id: str) -> int | None:
    today = datetime.now(timezone.utc).date()
    cycle = _cached_next_cycle(supabase, exam_id, today.isoformat())
    if not cycle or not cycle.get("exam_start"):
        return None
    try:
        start = datetime.fromisoformat(str(cycle["exam_start"])).date()
    except (ValueError, TypeError):
        return None
    return max(0, (start - today).days)


def _load_locked_coverage(supabase: Any, exam_id: str) -> list[dict[str, Any]]:
    """Locked ``exam_topic_coverage`` rows enriched with topic/subject names.

    Only ``reviewer_status='locked'`` rows are planner-ready — the same
    verified-only contract the rest of Study OS uses.
    """
    rows = (
        _safe(
            lambda: (
                supabase.table("exam_topic_coverage")
                .select(
                    "id, exam_cycle_id, exam_phase_id, section_id, topic_id, "
                    "exam_priority_score, is_high_yield, confidence_score, "
                    "coverage_depth, expected_difficulty, reviewer_status"
                )
                .eq("exam_id", exam_id)
                .eq("reviewer_status", "locked")
                .limit(2000)
                .execute()
                .data
            ),
            default=[],
        )
        or []
    )
    topic_ids = list({r.get("topic_id") for r in rows if r.get("topic_id")})
    if not topic_ids:
        return []
    topic_rows = (
        _safe(
            lambda: (
                supabase.table("topics")
                # Include ``parent_topic_id`` + ``level`` so callers (e.g.
                # /api/study/topics) can render the Subject → Topic →
                # Microtopic → Concept hierarchy without a second round-trip.
                .select("id, name, slug, subject_id, is_active, parent_topic_id, level")
                .in_("id", topic_ids)
                .limit(2000)
                .execute()
                .data
            ),
            default=[],
        )
        or []
    )
    topics_by_id = {t["id"]: t for t in topic_rows if t.get("id")}
    subject_ids = list(
        {t.get("subject_id") for t in topics_by_id.values() if t.get("subject_id")}
    )
    subjects_by_id: dict[str, dict[str, Any]] = {}
    if subject_ids:
        subj_rows = (
            _safe(
                lambda: (
                    supabase.table("subjects")
                    .select("id, name")
                    .in_("id", subject_ids)
                    .limit(500)
                    .execute()
                    .data
                ),
                default=[],
            )
            or []
        )
        subjects_by_id = {s["id"]: s for s in subj_rows if s.get("id")}

    out: list[dict[str, Any]] = []
    for r in rows:
        topic = topics_by_id.get(r.get("topic_id"))
        if not topic or topic.get("is_active") is False:
            continue
        subject = subjects_by_id.get(topic.get("subject_id")) or {}
        out.append(
            {
                "coverage_id": r.get("id"),
                "topic_id": r.get("topic_id"),
                "topic_name": topic.get("name") or topic.get("slug"),
                # Hierarchy fields surfaced for /api/study/topics. Null is
                # legitimate for root-level topics; never coerce to None
                # for non-root rows.
                "parent_topic_id": topic.get("parent_topic_id"),
                "topic_level": topic.get("level"),
                "subject_id": topic.get("subject_id"),
                "subject_name": subject.get("name"),
                "exam_cycle_id": r.get("exam_cycle_id"),
                "exam_phase_id": r.get("exam_phase_id"),
                "coverage_priority": _num(r.get("exam_priority_score")),
                "is_high_yield": bool(r.get("is_high_yield")),
                "confidence_score": r.get("confidence_score"),
            }
        )
    return out


def _load_prerequisites(
    supabase: Any, topic_ids: list[str]
) -> dict[str, set[str]]:
    """Map ``topic_id -> {prerequisite_topic_id}`` for ordering relations.

    Consumes ONLY locked prerequisite edges (``reviewer_status = 'locked'``)
    per the J2-A′ gate §G; draft/pending_review/reviewed/rejected edges are
    excluded at the query level and never influence planner ordering.
    """
    if not topic_ids:
        return {}
    rows = (
        _safe(
            lambda: (
                supabase.table("topic_prerequisites")
                .select("topic_id, prerequisite_topic_id, relation_type")
                .in_("topic_id", topic_ids)
                .eq("reviewer_status", "locked")
                .limit(5000)
                .execute()
                .data
            ),
            default=[],
        )
        or []
    )
    prereqs: dict[str, set[str]] = {}
    for r in rows:
        if r.get("relation_type") not in _ORDERING_RELATIONS:
            continue
        tid = r.get("topic_id")
        pid = r.get("prerequisite_topic_id")
        if tid and pid:
            prereqs.setdefault(tid, set()).add(pid)
    return prereqs


def _load_user_signals_ex(
    supabase: Any, user_id: str, exam_id: str
) -> tuple[dict[str, float], set[str], bool]:
    """Return ``(mastery_by_topic, topics_with_error_patterns, mastery_ok)``.

    When a topic has both an exam-scoped and a global mastery row the
    exam-scoped one wins.

    ``mastery_ok`` is ``False`` only when the ``user_topic_mastery`` read
    itself failed (distinct from an empty result). A failed read is treated as
    an empty mastery map for scoring, and callers MUST NOT apply self-assessment
    priors in that case — otherwise a transient DB error would let a user's
    self-report silently replace their real validated mastery.

    ``_load_user_signals`` is the back-compatible 2-tuple wrapper kept for the
    several existing callers that don't need the read-health flag.
    """
    mastery_rows = _safe(
        lambda: (
            supabase.table("user_topic_mastery")
            .select("topic_id, exam_id, mastery_score")
            .eq("user_id", user_id)
            .limit(5000)
            .execute()
            .data
        ),
        default=_READ_FAILED,
    )
    mastery_ok = mastery_rows is not _READ_FAILED
    if not mastery_ok or mastery_rows is None:
        mastery_rows = []
    mastery: dict[str, float] = {}
    exam_scoped: set[str] = set()
    for r in mastery_rows:
        tid = r.get("topic_id")
        if not tid:
            continue
        is_exam = r.get("exam_id") == exam_id
        if tid in exam_scoped and not is_exam:
            continue
        mastery[tid] = _num(r.get("mastery_score"))
        if is_exam:
            exam_scoped.add(tid)

    error_rows = (
        _safe(
            lambda: (
                supabase.table("user_topic_error_patterns")
                .select("topic_id")
                .eq("user_id", user_id)
                .limit(5000)
                .execute()
                .data
            ),
            default=[],
        )
        or []
    )
    error_topics = {r.get("topic_id") for r in error_rows if r.get("topic_id")}
    return mastery, error_topics, mastery_ok


def _load_user_signals(
    supabase: Any, user_id: str, exam_id: str
) -> tuple[dict[str, float], set[str]]:
    """Back-compat 2-tuple view of :func:`_load_user_signals_ex`.

    Kept stable for callers (subjects / plan_timeline / report_cards / the
    topics API) that only need ``(mastery, error_topics)`` and not the
    mastery-read-health flag the planner consumes for fail-closed priors.
    """
    mastery, error_topics, _ = _load_user_signals_ex(supabase, user_id, exam_id)
    return mastery, error_topics


def _load_topic_priors(
    supabase: Any, user_id: str, exam_id: str, coverage_topic_ids: list[str]
) -> dict[str, dict[str, Any]]:
    """Return topic_id → {prior_mastery, report_confidence, band, subject_id,
    attempts_used} from self-assessment.

    Only fills the cold-start gap — validated mastery always wins at call site.
    Subject-level rows are expanded to all coverage topic_ids with that subject_id;
    each entry carries ``"assessment_level": "subject"`` to record granularity.
    Returns an empty dict on DB read failure (plan still generates).
    """
    rows = _safe(lambda: (
        supabase.table("user_topic_self_assessment")
        .select("subject_id, band, prior_mastery, report_confidence, attempts_used")
        .eq("user_id", user_id)
        .eq("exam_id", exam_id)
        .is_("topic_id", None)
        .not_.is_("subject_id", None)
        .limit(500)
        .execute()
        .data
    ), default=[]) or []

    if not rows or not coverage_topic_ids:
        return {}

    # Map subject_id → prior entry (prior_mastery, report_confidence, band, ...)
    subject_priors: dict[str, dict[str, Any]] = {}
    for r in rows:
        sid = r.get("subject_id")
        if not sid:
            continue
        pm_raw = r.get("prior_mastery")
        pm = float(pm_raw) if pm_raw is not None else None
        rc = float(r.get("report_confidence") or 0.5)
        band = r.get("band") or "new"
        au_raw = r.get("attempts_used")
        try:
            attempts_used = int(au_raw) if au_raw is not None else None
        except (TypeError, ValueError):
            attempts_used = None
        subject_priors[sid] = {
            "prior_mastery": pm,
            "report_confidence": rc,
            "band": band,
            "subject_id": sid,
            "attempts_used": attempts_used,
            "assessment_level": "subject",
        }

    if not subject_priors:
        return {}

    # Expand: find which coverage topic_ids belong to which subject
    topic_rows = _safe(lambda: (
        supabase.table("topics")
        .select("id, subject_id")
        .in_("id", coverage_topic_ids)
        .in_("subject_id", list(subject_priors.keys()))
        .limit(5000)
        .execute()
        .data
    ), default=[]) or []

    priors: dict[str, dict[str, Any]] = {}
    for t in topic_rows:
        tid = t.get("id")
        sid = t.get("subject_id")
        if tid and sid and sid in subject_priors:
            priors[tid] = subject_priors[sid]

    return priors


def _self_assessment_summary(
    topic_priors: dict[str, dict[str, Any]]
) -> dict[str, Any] | None:
    """Audit rollup of the self-assessment priors that fed this plan.

    ``None`` when no priors contributed. Otherwise reports how many topics got
    a prior, the granularity, the per-band counts, the shared ``attempts_used``,
    and the distinct subjects that contributed.

    ``by_band`` counts DISTINCT SUBJECTS per band, not expanded topics: priors
    are reported at subject granularity, so one large subject (many coverage
    topics) must not dominate the band tally. ``topics_with_prior`` remains a
    topic count for breadth-of-impact.
    """
    if not topic_priors:
        return None
    # Dedupe to one prior entry per subject before tallying bands.
    by_subject: dict[str, dict[str, Any]] = {}
    for entry in topic_priors.values():
        sid = entry.get("subject_id")
        if sid and sid not in by_subject:
            by_subject[sid] = entry
    by_band: dict[str, int] = {}
    attempts_used: Any = None
    for entry in by_subject.values():
        band = entry.get("band") or "new"
        by_band[band] = by_band.get(band, 0) + 1
        if attempts_used is None and entry.get("attempts_used") is not None:
            attempts_used = entry.get("attempts_used")
    return {
        "topics_with_prior": len(topic_priors),
        "assessment_level": "subject",
        "by_band": by_band,
        "attempts_used": attempts_used,
        "subject_ids": sorted(by_subject.keys()),
    }


# ─── Scoring + task shaping ───────────────────────────────────────────────
# A pinned topic is boosted hard so it reliably earns a slot in the plan.
_PIN_BONUS = 30.0


def _score_topic(
    cov: dict[str, Any],
    pyq_count: int,
    mastery: float | None,
    has_errors: bool,
    *,
    weights: dict[str, float],
    pinned: bool,
    snapshot: dict[str, Any] | None = None,
) -> tuple[float, float]:
    """Return ``(priority_score, mastery_gap)`` for one coverage row.

    Transparent linear blend — see module docstring for the input groups.
    ``weights`` (coverage_w / mastery_w / high_yield_bonus) come from the
    user's chosen weighting ``focus``; a topic with no mastery row is
    treated as a moderate-high gap (55) so never-practised topics still
    earn attention without dominating. Pinned topics get a flat boost.

    When a locked score snapshot is available it contributes up to 15 pts
    as a bounded additive term. Absent snapshots degrade gracefully to zero
    for this component only — the rest of the score is unchanged.
    Confidence modulates the snapshot component — low-confidence snapshots
    contribute less; when confidence is absent it defaults to 1.0 (full weight).
    """
    coverage_priority = cov["coverage_priority"]
    mastery_gap = (100.0 - mastery) if mastery is not None else 55.0
    pyq_factor = min(20.0, pyq_count * 5.0)
    snapshot_component = (
        min(15.0,
            float(snapshot.get("exam_priority_score") or 0) / 100.0 * 15.0
            * min(1.0, max(0.0, float(1.0 if snapshot.get("confidence_score") is None else snapshot.get("confidence_score")))))
        if snapshot else 0.0
    )
    high_yield_bonus = weights["high_yield_bonus"] if cov["is_high_yield"] else 0.0
    error_signal = 10.0 if has_errors else 0.0
    pin_bonus = _PIN_BONUS if pinned else 0.0
    score = (
        weights["coverage_w"] * coverage_priority
        + weights["mastery_w"] * mastery_gap
        + pyq_factor
        + snapshot_component
        + high_yield_bonus
        + error_signal
        + pin_bonus
    )
    return round(_clamp(score), 2), round(mastery_gap, 2)


def _task_type(mastery: float | None, has_errors: bool) -> str:
    if mastery is None:
        return "concept_learning"
    if mastery < 45:
        return "concept_learning"
    if mastery < 75 or has_errors:
        return "retrieval_practice"
    return "revision"


def _order_topics(
    scored: list[dict[str, Any]], prereqs: dict[str, set[str]]
) -> list[dict[str, Any]]:
    """Prerequisite-aware, priority-greedy ordering.

    ``scored`` must already be sorted by ``priority_score`` descending.
    Repeatedly takes the highest-priority topic whose in-set prerequisites
    are all placed; falls back to plain priority order if blocked (cycle or
    prerequisite outside the candidate set).
    """
    all_ids = {c["topic_id"] for c in scored}
    placed: list[dict[str, Any]] = []
    placed_ids: set[str] = set()
    remaining = list(scored)
    while remaining:
        pick = None
        for c in remaining:
            in_set_prereqs = prereqs.get(c["topic_id"], set()) & all_ids
            if in_set_prereqs <= placed_ids:
                pick = c
                break
        if pick is None:
            pick = remaining[0]
        placed.append(pick)
        placed_ids.add(pick["topic_id"])
        remaining.remove(pick)
    return placed


def _why_summary(
    cov: dict[str, Any],
    task_type: str,
    pyq_count: int,
    mastery: float | None,
    pressure_level: str,
    pinned: bool,
    snapshot: dict[str, Any] | None = None,
    mastery_source: str = "none",
    band: str | None = None,
) -> str:
    topic = cov["topic_name"]
    exam_bits = "a verified high-yield topic" if cov["is_high_yield"] else "a verified topic"
    bits = [f"{topic} is {exam_bits} for your exam"]
    if pinned:
        bits.append("you pinned it")
    if pyq_count:
        bits.append(f"{pyq_count} verified PYQ appearance(s)")
    if snapshot:
        conf = snapshot.get("confidence_score")
        if conf is not None:
            bits.append(f"analysis confidence {round(conf * 100)}%")
    # Mastery provenance must be honest: only validated evidence may be phrased
    # as "recent accuracy". Self-reports are flagged as not-yet-validated; a
    # 'new' self-report (no estimate) reads as "never studied".
    if mastery_source == "self_reported":
        if mastery is None:
            bits.append(
                "you marked this as never studied "
                "(self-assessment, not yet validated by practice)"
            )
        else:
            bits.append(
                f"you rated yourself '{band}' here — a self-assessment estimate "
                f"(~{round(mastery)}%, not yet validated by practice)"
            )
    elif mastery_source == "validated" and mastery is not None:
        bits.append(f"your recent accuracy is {round(mastery)}%")
    else:
        bits.append("you haven't practised it yet")
    if pressure_level == "high":
        bits.append("competition pressure for this cycle is high")
    label = _TASK_LABEL.get(task_type, task_type).lower()
    return "; ".join(bits) + f" — scheduled as a {label} block."


def _build_tasks(
    ordered: list[dict[str, Any]],
    *,
    max_tasks: int,
    minutes: int,
    pressure_level: str,
    exam_id: str,
) -> list[dict[str, Any]]:
    today = _today_iso()
    tasks: list[dict[str, Any]] = []
    for cov in ordered[:max_tasks]:
        task_type = cov["_task_type"]
        label = _TASK_LABEL.get(task_type, "Study")
        snap = cov.get("_snapshot")
        mastery_source = cov.get("_mastery_source", "none")
        prior_entry = cov.get("_prior_entry")
        prior_band = prior_entry.get("band") if prior_entry else None
        why = {
            "coverage_priority": cov["coverage_priority"],
            "verified_pyq_count": cov["_pyq_count"],
            "mastery_score": cov["_mastery"],
            "mastery_gap": cov["_mastery_gap"],
            "high_yield": cov["is_high_yield"],
            "has_error_patterns": cov["_has_errors"],
            "pinned": cov["_pinned"],
            "competition_pressure": pressure_level,
            "priority_score": cov["_priority_score"],
            "snapshot_id": snap.get("snapshot_id") if snap else None,
            "snapshot_priority_score": snap.get("exam_priority_score") if snap else None,
            "snapshot_confidence": snap.get("confidence_score") if snap else None,
            "snapshot_model_version": snap.get("model_version") if snap else None,
            "snapshot_computed_at": snap.get("computed_at") if snap else None,
            "snapshot_evidence_count": snap.get("evidence_count") if snap else None,
            "mastery_source": mastery_source,
            "summary": _why_summary(
                cov,
                task_type,
                cov["_pyq_count"],
                cov["_mastery"],
                pressure_level,
                cov["_pinned"],
                snap,
                mastery_source=mastery_source,
                band=prior_band,
            ),
        }
        # Persist self-assessment provenance whenever a prior contributed —
        # including band='new' (explicit "never studied"), where prior_mastery
        # is None but the report is still a real signal distinguishable from a
        # topic with no self-report at all.
        if prior_entry:
            why["self_assessment_band"] = prior_entry.get("band")
            why["self_assessment_prior_mastery"] = prior_entry.get("prior_mastery")
            why["self_assessment_confidence"] = prior_entry.get("report_confidence")
            why["self_assessment_level"] = prior_entry.get("assessment_level") or "subject"
        task = {
            "user_id": None,  # filled in by _persist
            "title": f"{cov['topic_name']} · {label}",
            "task_type": task_type,
            "subject": cov.get("subject_name"),
            "topic": cov["topic_name"],
            "subject_id": cov.get("subject_id"),
            "topic_id": cov["topic_id"],
            "exam_id": exam_id,
            "exam_phase_id": cov.get("exam_phase_id"),
            "exam_topic_coverage_id": cov.get("coverage_id"),
            "scheduled_date": today,
            "day_label": "Today",
            "status": "planned",
            "planned_minutes": minutes,
            "priority_score": cov["_priority_score"],
            "why_this_task": why,
        }
        # PYQ v2 PR-9: a practice/revision task on a real topic+exam resolves to
        # a typed PYQ topic-practice launch. Stamp the launch columns
        # (migration 205) so the client can open the right target deterministically.
        # Other task types (e.g. concept_learning) or tasks missing topic/exam are
        # left unstamped — launch columns stay absent, preserving prior behaviour.
        topic_id = cov.get("topic_id")
        if task_type in _LAUNCH_STAMP_TASK_TYPES and topic_id and exam_id:
            task["launch_type"] = LAUNCH_PYQ_PRACTICE
            task["launch_entity_id"] = topic_id
            task["launch_context"] = {
                "mode": "topic",
                "target_id": topic_id,
                "exam_id": exam_id,
            }
            why["launch_target"] = LAUNCH_PYQ_PRACTICE
        tasks.append(task)
    return tasks


# ─── Persistence ──────────────────────────────────────────────────────────
def _active_plan(supabase: Any, user_id: str) -> dict[str, Any] | None:
    rows = (
        _safe(
            lambda: (
                supabase.table("study_plans")
                .select("id, status, current_plan_version_id")
                .eq("user_id", user_id)
                .eq("status", "active")
                .limit(1)
                .execute()
                .data
            ),
            default=[],
        )
        or []
    )
    return rows[0] if rows else None


def _open_writing_topic_ids(supabase: Any, user_id: str) -> set[str]:
    """Topics that already carry an ACTIVE (non-``planned``) writing task today.

    Dedup source for EWP-5 generation. Deliberately excludes ``status='planned'``
    rows: ``_persist`` clears today's planned tasks before re-inserting on every
    regeneration, so counting them would suppress the writing task on the second
    regen and it would vanish. Only started/completed writing tasks (which
    ``_persist`` preserves) should block a duplicate for the same topic.
    """
    plan = _active_plan(supabase, user_id)
    if not plan:
        return set()
    today = _today_iso()
    rows = (
        _safe(
            lambda: (
                supabase.table("study_tasks")
                .select("topic_id, status")
                .eq("plan_id", plan["id"])
                .eq("scheduled_date", today)
                .eq("launch_type", LAUNCH_ENGLISH_WRITING_SESSION)
                .execute()
                .data
            ),
            default=[],
        )
        or []
    )
    return {
        r["topic_id"]
        for r in rows
        if r.get("topic_id") and r.get("status") != "planned"
    }


def _generate_writing_tasks(
    supabase: Any,
    user_id: str,
    ordered: list[dict[str, Any]],
    *,
    exam_id: str,
    exam_phase_id: str | None,
    minutes: int,
) -> list[dict[str, Any]]:
    """Deterministically build english_writing_session tasks for this plan.

    Never raises and never blocks plan generation: any read failure degrades to
    an empty list (no writing tasks) via the fail-closed helpers in
    ``writing_practice.planner_tasks``.
    """
    candidate_topic_ids = [c.get("topic_id") for c in ordered if c.get("topic_id")]
    if not candidate_topic_ids:
        return []
    eligible = planner_tasks.resolve_writing_eligible_topic_ids(
        supabase,
        exam_id=exam_id,
        exam_phase_id=exam_phase_id,
        candidate_topic_ids=candidate_topic_ids,
    )
    if not eligible:
        return []
    existing = _open_writing_topic_ids(supabase, user_id)
    return planner_tasks.build_writing_tasks(
        ordered,
        exam_id=exam_id,
        exam_phase_id=exam_phase_id,
        minutes=minutes,
        today=_today_iso(),
        eligible_topic_ids=eligible,
        existing_writing_topic_ids=existing,
        max_writing_tasks=_MAX_WRITING_TASKS,
    )


def _next_version_number(supabase: Any, plan_id: str) -> int:
    rows = (
        _safe(
            lambda: (
                supabase.table("study_plan_versions")
                .select("version_number")
                .eq("plan_id", plan_id)
                .order("version_number", desc=True)
                .limit(1)
                .execute()
                .data
            ),
            default=[],
        )
        or []
    )
    if not rows:
        return 1
    try:
        return int(rows[0].get("version_number") or 0) + 1
    except (TypeError, ValueError):
        return 1


def _persist(
    supabase: Any,
    user_id: str,
    exam: dict[str, Any],
    plan_phase_id: str | None,
    tasks: list[dict[str, Any]],
    input_context: dict[str, Any],
    event_type: str,
) -> dict[str, Any]:
    """Persist a freshly-computed plan. Fail closed on every critical write.

    Every Supabase write below uses :func:`safe_required`. If any one
    returns ``None`` the function short-circuits with
    ``{"generated": False, "reason": "<code>"}`` so ``apply_plan`` never
    reports success on a partially-written plan. The previous bare
    ``_safe(...)`` pattern was masking constraint violations (e.g. an
    ``event_type`` that wasn't in the CHECK list) and letting the API
    return ``{generated: True}`` while the audit row never wrote.

    ``study_plans.title`` is ``NOT NULL`` with no default; omitting it was
    rejected by Postgres with ``23502`` and the whole apply failed. We now
    populate every ``NOT NULL`` column (``user_id``, ``title``) on insert
    and give ``description`` a non-null safe string. The update path never
    touches ``title`` so a re-version cannot null it out.

    supabase-py exposes no client-side transaction, so on any failure
    *after* the first insert we run a compensating rollback that tears
    down exactly what this call created, in reverse FK-safe order, leaving
    no orphan ``study_plans`` / ``study_plan_versions`` / ``study_tasks``
    rows behind.
    """
    exam_id = exam.get("id")
    exam_name = exam.get("name") or "Exam"
    today = _today_iso()
    title = f"{exam_name} Study Plan"
    description = f"Adaptive plan covering locked high-yield topics for {exam_name}."

    # Compensating-rollback stack: each entry is a no-arg delete/restore run
    # via ``_safe`` (best-effort) in reverse creation order on failure.
    rollback_ops: list[Callable[[], Any]] = []

    def _rollback() -> None:
        for op in reversed(rollback_ops):
            _safe(op)

    plan = _active_plan(supabase, user_id)
    if plan:
        plan_id = plan["id"]
        prev_version_id = plan.get("current_plan_version_id")
    else:
        created = safe_required(
            lambda: (
                supabase.table("study_plans")
                .insert(
                    {
                        "user_id": user_id,
                        "title": title,
                        "description": description,
                        "status": "active",
                        "start_date": today,
                        "exam_id": exam_id,
                        "active_phase_id": plan_phase_id,
                        "metadata": {
                            "theme": f"{exam_name} adaptive plan",
                            "target": "Cover locked high-yield topics",
                        },
                        "generation_context": input_context,
                        "updated_at": _now_iso(),
                    }
                )
                .execute()
            ),
            op="study_plans.insert",
        )
        if created is None:
            return {"generated": False, "reason": "plan_persist_failed"}
        plan_id = created[0]["id"]
        prev_version_id = None
        rollback_ops.append(
            lambda: supabase.table("study_plans").delete().eq("id", plan_id).execute()
        )

    version_number = _next_version_number(supabase, plan_id)
    version = safe_required(
        lambda: (
            supabase.table("study_plan_versions")
            .insert(
                {
                    "plan_id": plan_id,
                    "user_id": user_id,
                    "version_number": version_number,
                    "generator_version": PLANNER_VERSION,
                    "reason": input_context.get("reason"),
                    "input_context": input_context,
                    "output_summary": {
                        "task_count": len(tasks),
                        "topics": [t["topic"] for t in tasks],
                    },
                    "activated_at": _now_iso(),
                }
            )
            .execute()
        ),
        op="study_plan_versions.insert",
    )
    if version is None:
        _rollback()
        return {"generated": False, "reason": "version_persist_failed"}
    plan_version_id = version[0]["id"]
    rollback_ops.append(
        lambda: supabase.table("study_plan_versions")
        .delete()
        .eq("id", plan_version_id)
        .execute()
    )

    # Idempotent regeneration: clear today's still-planned tasks for this
    # plan, then insert the fresh set. Completed / in-progress tasks stay.
    # ``allow_empty=True`` because a fresh plan legitimately deletes zero
    # rows on the first apply — that is not a failure.
    cleared = safe_required(
        lambda: (
            supabase.table("study_tasks")
            .delete()
            .eq("plan_id", plan_id)
            .eq("scheduled_date", today)
            .eq("status", "planned")
            .execute()
        ),
        op="study_tasks.delete_today",
        allow_empty=True,
    )
    if cleared is None:
        _rollback()
        return {"generated": False, "reason": "task_cleanup_failed"}

    task_rows = [
        {**t, "user_id": user_id, "plan_id": plan_id, "plan_version_id": plan_version_id}
        for t in tasks
    ]
    if task_rows:
        inserted_tasks = safe_required(
            lambda: supabase.table("study_tasks").insert(task_rows).execute(),
            op="study_tasks.insert",
        )
        if inserted_tasks is None:
            _rollback()
            return {"generated": False, "reason": "task_persist_failed"}
        rollback_ops.append(
            lambda: supabase.table("study_tasks")
            .delete()
            .eq("plan_version_id", plan_version_id)
            .execute()
        )

    updated_plan = safe_required(
        lambda: (
            supabase.table("study_plans")
            .update(
                {
                    "current_plan_version_id": plan_version_id,
                    "active_phase_id": plan_phase_id,
                    "updated_at": _now_iso(),
                }
            )
            .eq("id", plan_id)
            .execute()
        ),
        op="study_plans.update_active_version",
    )
    if updated_plan is None:
        _rollback()
        return {"generated": False, "reason": "plan_persist_failed"}
    rollback_ops.append(
        lambda: supabase.table("study_plans")
        .update({"current_plan_version_id": prev_version_id})
        .eq("id", plan_id)
        .execute()
    )

    audit = safe_required(
        lambda: (
            supabase.table("study_adaptation_events")
            .insert(
                {
                    "user_id": user_id,
                    "plan_id": plan_id,
                    "plan_version_id": plan_version_id,
                    "event_type": event_type,
                    "trigger_source": PLANNER_VERSION,
                    "trigger_payload": {"reason": input_context.get("reason")},
                    "change_summary": {
                        "task_count": len(tasks),
                        "version_number": version_number,
                    },
                }
            )
            .execute()
        ),
        op="study_adaptation_events.insert",
    )
    if audit is None:
        _rollback()
        return {"generated": False, "reason": "audit_persist_failed"}

    return {
        "generated": True,
        "plan_id": plan_id,
        "plan_version_id": plan_version_id,
        "version_number": version_number,
    }


# ─── Public entrypoint ────────────────────────────────────────────────────
def _compute_plan(
    supabase: Any,
    user_id: str,
    *,
    reason: str,
    expected_exam_id: str | None = None,
) -> dict[str, Any]:
    """Compute (but do not persist) today's plan candidate.

    Returns one of two shapes:
      - failure: ``{"generated": False, "reason": "...", "exam": slug?}``
      - success: ``{"generated": True, "exam": <row>, "plan_phase_id": ...,
                    "tasks": [...], "input_context": {...},
                    "competition_pressure": "...", "focus": "...",
                    "policy_affects_syllabus": bool}``
    """
    if not user_id:
        return {"generated": False, "reason": "no_user"}

    exam = _resolve_target_exam(supabase, user_id)
    if not exam or not exam.get("id"):
        return {"generated": False, "reason": "no_target_exam"}
    exam_id = exam["id"]

    if expected_exam_id is not None and str(exam_id) != str(expected_exam_id):
        # TOCTOU guard: the target exam changed between the calibration gate
        # check (performed for ``expected_exam_id``) and this resolution. Refuse
        # to generate/persist for a different exam whose gate was never checked.
        return {"generated": False, "reason": "target_changed", "exam": exam.get("slug")}

    today = datetime.now(timezone.utc).date()
    resolver_result = resolve_exam_target_window(supabase, exam_id=exam_id, today=today)

    # D12/D14 (D05 evidence-engine PR-3): a `light` exam is exposed to Study OS / planner
    # activation ONLY when its target cycle opts in via `exam_cycles.planner_activation_enabled`
    # — the SAME canonical authority cycle_readiness Step 9 consumes (shared authority, no
    # readiness↔planner drift). A non-exposed light exam is not a planner target; readiness marks
    # its review_activate not_applicable. `core` is always planner-eligible; index_only/archive
    # planner gating is a separate concern (readiness already marks them N/A).
    if (exam or {}).get("management_mode") == "light" and not _cycle_planner_exposed(
        supabase, resolver_result.get("cycle_id")
    ):
        return {"generated": False, "reason": "planner_activation_disabled", "exam": exam.get("slug")}

    # User autonomy: weighting focus, plan-shape overrides, pin / mute.
    prefs = get_plan_preferences(supabase, user_id)
    muted = set(prefs.get("muted_topic_ids") or [])
    pinned = set(prefs.get("pinned_topic_ids") or [])
    weights = focus_weights(prefs.get("focus"))

    coverage = _load_locked_coverage(supabase, exam_id)
    if not coverage:
        return {
            "generated": False,
            "reason": "no_locked_coverage",
            "exam": exam.get("slug"),
        }
    coverage = [c for c in coverage if c["topic_id"] not in muted]
    if not coverage:
        return {
            "generated": False,
            "reason": "all_topics_muted",
            "exam": exam.get("slug"),
        }

    # Phase-specific coverage: prefer rows tagged to the resolver's target phase;
    # fall back to exam-wide locked coverage only when none match.
    resolver_phase_id = resolver_result["target_phase_id"]
    if resolver_phase_id is not None:
        phase_coverage = [c for c in coverage if c.get("exam_phase_id") == resolver_phase_id]
        if phase_coverage:
            coverage = phase_coverage

    topic_ids = [c["topic_id"] for c in coverage]
    pyq_counts = verified_pyq_topic_counts(supabase, exam_id) or {}
    prereqs = _load_prerequisites(supabase, topic_ids)
    mastery, error_topics, mastery_ok = _load_user_signals_ex(supabase, user_id, exam_id)

    # Resolver is the single target authority — days_remaining may be None
    # (open-ended current phase) and must not be coerced to 0.
    days_remaining = resolver_result["days_remaining"]
    comp = competition_context(supabase, exam_id, days_remaining=days_remaining)
    pressure_level = (comp.get("cycle_pressure") or {}).get("pressure_level", "unknown")
    policy_updates = policy_update_context(supabase, exam_id)

    # Task count + sizing: a user preference overrides the persona policy.
    snapshot = (
        _safe(
            lambda: (
                supabase.table("aspirant_persona_snapshots")
                .select("study_policy")
                .eq("user_id", user_id)
                .order("computed_at", desc=True)
                .limit(1)
                .execute()
                .data
            ),
            default=[],
        )
        or []
    )
    study_policy = (snapshot[0] if snapshot else {}).get("study_policy") or {}
    pref_max = prefs.get("max_tasks_per_day")
    if pref_max:
        max_tasks = max(1, min(8, int(pref_max)))
    else:
        try:
            max_tasks = int(study_policy.get("max_tasks_per_day") or _DEFAULT_MAX_TASKS)
        except (TypeError, ValueError):
            max_tasks = _DEFAULT_MAX_TASKS
        max_tasks = max(1, min(8, max_tasks))
    size = (
        prefs.get("preferred_task_size")
        or study_policy.get("preferred_task_size")
        or _DEFAULT_SIZE
    )
    minutes = _SIZE_MINUTES.get(size, _SIZE_MINUTES[_DEFAULT_SIZE])

    # Locked score snapshots provide a reviewed analytical priority signal.
    # Gracefully degrades to an empty dict when none exist (draft-only or
    # not yet computed), leaving the rest of the scoring unchanged.
    # Returns None on DB read failure — plan still generates with no snapshot component.
    _snap_result = locked_score_snapshots(supabase, exam_id, exam_phase_id=resolver_phase_id)
    snapshot_read_failed = _snap_result is None
    score_snapshots_by_topic: dict[str, dict[str, Any]] = {
        s["topic_id"]: s
        for s in (_snap_result or [])
    }

    # Self-assessment priors: fill cold-start gap when no validated mastery exists.
    # A DB failure returns {} and the plan still generates with the standard 55-pt gap.
    # Two independent preconditions, both required before any prior is consumed:
    #   * ``mastery_ok`` — fail closed: if the validated-mastery read itself failed,
    #     a transient error must never let a self-report override real evidence we
    #     simply couldn't load this request.
    #   * the calibration gate is explicitly ``completed`` — partially-saved evidence
    #     (no completed gate) or evidence left over after the user SKIPPED must not
    #     influence scoring. ``skipped`` / ``none`` / partial all → cold-start.
    # Gate status is read once here and recorded in input_context for audit; plan
    # generation itself is never blocked in the planner (the API layer owns unlock).
    calibration_gate_status = calibration.gate_status(supabase, user_id, exam_id)
    gate_done = calibration_gate_status == "completed"
    topic_priors = (
        _load_topic_priors(supabase, user_id, exam_id, topic_ids)
        if (mastery_ok and gate_done)
        else {}
    )

    # score every locked-coverage topic
    for cov in coverage:
        tid = cov["topic_id"]
        pyq_count = int(pyq_counts.get(tid, 0))
        topic_mastery = mastery.get(tid)
        mastery_source = "validated" if tid in mastery else "none"
        prior_entry = topic_priors.get(tid)
        if topic_mastery is None and prior_entry is not None:
            pm = prior_entry["prior_mastery"]
            rc = prior_entry["report_confidence"]
            if pm is not None:
                # Bands strong/decent/weak carry an estimate: blend toward a
                # neutral 45 by the report confidence.
                neutral = 45.0
                topic_mastery = round(rc * pm + (1.0 - rc) * neutral, 1)
            # band 'new' (pm is None): keep cold-start scoring (topic_mastery
            # stays None → 55-pt gap), but STILL mark the provenance as a
            # self-report so an explicit "never studied" is distinguishable
            # from a topic with no self-report at all (which stays 'none').
            mastery_source = "self_reported"
        has_errors = tid in error_topics
        is_pinned = tid in pinned
        topic_snapshot = score_snapshots_by_topic.get(tid)
        score, gap = _score_topic(
            cov, pyq_count, topic_mastery, has_errors,
            weights=weights, pinned=is_pinned, snapshot=topic_snapshot,
        )
        cov["_pyq_count"] = pyq_count
        cov["_mastery"] = topic_mastery
        cov["_mastery_gap"] = gap
        cov["_has_errors"] = has_errors
        cov["_pinned"] = is_pinned
        cov["_priority_score"] = score
        cov["_task_type"] = _task_type(topic_mastery, has_errors)
        cov["_snapshot"] = topic_snapshot
        cov["_mastery_source"] = mastery_source
        cov["_prior_entry"] = prior_entry

    coverage.sort(key=lambda c: c["_priority_score"], reverse=True)
    ordered = _order_topics(coverage, prereqs)

    # Resolver is single authority for active_phase_id.
    # Coverage-majority is fallback only when resolver has no target phase
    # (cycle_exam_start or not_connected paths).
    if resolver_phase_id is not None:
        plan_phase_id = resolver_phase_id
    else:
        phase_counts: dict[str, int] = {}
        for c in coverage:
            ph = c.get("exam_phase_id")
            if ph:
                phase_counts[ph] = phase_counts.get(ph, 0) + 1
        plan_phase_id = (
            max(phase_counts, key=phase_counts.get) if phase_counts else None
        )

    tasks = _build_tasks(
        ordered,
        max_tasks=max_tasks,
        minutes=minutes,
        pressure_level=pressure_level,
        exam_id=exam_id,
    )

    # EWP-5: auto-generate real english_writing_session sentence tasks for
    # writing-eligible English topics (verified+active prompts only). Additive
    # and bounded; deduped against active writing tasks so regen never
    # duplicates. Uses the plan phase so launch-time prompt selection re-derives
    # the same eligible set.
    writing_tasks = _generate_writing_tasks(
        supabase,
        user_id,
        ordered,
        exam_id=exam_id,
        exam_phase_id=plan_phase_id,
        minutes=minutes,
    )
    if writing_tasks:
        tasks.extend(writing_tasks)

    input_context = {
        "reason": reason,
        "generator_version": PLANNER_VERSION,
        "exam_id": exam_id,
        "exam_slug": exam.get("slug"),
        "locked_topic_count": len(coverage),
        "writing_task_count": len(writing_tasks),
        "days_remaining": days_remaining,
        "competition_pressure": pressure_level,
        "policy_affects_syllabus": bool(policy_updates.get("affects_syllabus")),
        "study_policy": {"max_tasks_per_day": max_tasks, "preferred_task_size": size},
        "preferences": {
            "focus": prefs.get("focus"),
            "pinned_count": len(pinned),
            "muted_count": len(muted),
        },
        "snapshot_read_failed": snapshot_read_failed,
        "snapshot_set_summary": [
            {
                "topic_id": s["topic_id"],
                "snapshot_id": s.get("snapshot_id"),
                "model_version": s.get("model_version"),
                "computed_at": s.get("computed_at"),
            }
            for s in score_snapshots_by_topic.values()
        ] if not snapshot_read_failed else None,
        "mastery_read_failed": not mastery_ok,
        "calibration_gate_status": calibration_gate_status,
        "self_assessment_summary": _self_assessment_summary(topic_priors),
    }

    return {
        "generated": True,
        "exam": exam,
        "plan_phase_id": plan_phase_id,
        "tasks": tasks,
        "input_context": input_context,
        "competition_pressure": pressure_level,
        "focus": prefs.get("focus"),
    }


def _task_summary(t: dict[str, Any]) -> dict[str, Any]:
    return {
        "topic_id": t.get("topic_id"),
        "title": t["title"],
        "task_type": t["task_type"],
        "topic": t["topic"],
        "priority_score": t["priority_score"],
        "planned_minutes": t["planned_minutes"],
        "why_this_task": t["why_this_task"],
    }


def _active_plan_today_tasks(supabase: Any, user_id: str) -> list[dict[str, Any]]:
    """Return today's still-planned tasks for the user's active plan."""
    plan = _active_plan(supabase, user_id)
    if not plan:
        return []
    today = _today_iso()
    rows = (
        _safe(
            lambda: (
                supabase.table("study_tasks")
                .select(
                    "id, topic_id, title, task_type, topic, priority_score, "
                    "planned_minutes, why_this_task, status, scheduled_date"
                )
                .eq("plan_id", plan["id"])
                .eq("scheduled_date", today)
                .execute()
                .data
            ),
            default=[],
        )
        or []
    )
    return rows


def _diff_tasks(
    before: list[dict[str, Any]],
    after: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return a structured diff: ``added`` / ``removed`` / ``unchanged`` topic ids."""
    before_topics = {b.get("topic_id"): b for b in before if b.get("topic_id")}
    after_topics = {a.get("topic_id"): a for a in after if a.get("topic_id")}
    added = sorted(set(after_topics) - set(before_topics))
    removed = sorted(set(before_topics) - set(after_topics))
    unchanged = sorted(set(before_topics) & set(after_topics))
    return {
        "added": [_task_summary(after_topics[t]) for t in added],
        "removed": [
            {
                "topic_id": t,
                "title": before_topics[t].get("title"),
                "task_type": before_topics[t].get("task_type"),
                "status": before_topics[t].get("status"),
            }
            for t in removed
        ],
        "unchanged": unchanged,
        "added_count": len(added),
        "removed_count": len(removed),
        "unchanged_count": len(unchanged),
    }


def _build_tradeoffs(
    before_tasks: list[dict[str, Any]], after_tasks: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Deterministic trade-off list for the draft preview.

    Pairs the highest-priority added topic with the highest-priority removed
    topic to express "gained X at the cost of Y". Items beyond the shorter
    list are unpaired (cost=None for gain-only, gained=None for cost-only).
    ``risk_delta`` is positive when the cost outranks the gain on the same
    100-pt priority scale the planner already uses for `priority_score`.

    Inputs come from the same maps `_diff_tasks` works over, so the
    numbers cannot drift from the diff itself.
    """
    before_by_topic = {b.get("topic_id"): b for b in before_tasks if b.get("topic_id")}
    after_by_topic = {a.get("topic_id"): a for a in after_tasks if a.get("topic_id")}
    added_topics = set(after_by_topic) - set(before_by_topic)
    removed_topics = set(before_by_topic) - set(after_by_topic)

    def _score(d: dict[str, Any]) -> float:
        try:
            return float(d.get("priority_score") or 0)
        except (TypeError, ValueError):
            return 0.0

    added_sorted = sorted(
        (after_by_topic[t] for t in added_topics),
        key=lambda d: (-_score(d), str(d.get("topic") or "")),
    )
    removed_sorted = sorted(
        (before_by_topic[t] for t in removed_topics),
        key=lambda d: (-_score(d), str(d.get("topic") or "")),
    )

    out: list[dict[str, Any]] = []
    pair_count = max(len(added_sorted), len(removed_sorted))
    for i in range(pair_count):
        a = added_sorted[i] if i < len(added_sorted) else None
        r = removed_sorted[i] if i < len(removed_sorted) else None
        gained = a.get("topic") if a else None
        cost = r.get("topic") if r else None
        a_minutes = int((a.get("planned_minutes") if a else 0) or 0)
        r_minutes = int((r.get("planned_minutes") if r else 0) or 0)
        magnitude_minutes = max(a_minutes, r_minutes)
        magnitude_hours = round(magnitude_minutes / 60.0, 2)
        # risk_delta on the planner's own 100-pt scale: positive when the
        # cost side outranks the gain side (risk rises on the dropped topic).
        risk_delta = round((_score(r) if r else 0.0) - (_score(a) if a else 0.0), 1)
        out.append({
            "gained": gained,
            "cost": cost,
            "magnitude_hours": magnitude_hours,
            "magnitude_minutes": magnitude_minutes,
            "risk_delta": risk_delta,
            "gained_priority": _score(a) if a else None,
            "cost_priority": _score(r) if r else None,
        })
    return out[:5]


def _risk_level(diff: dict[str, Any], before_count: int) -> str:
    """Rough risk label from how much of the plan is mutating."""
    if before_count == 0:
        return "low"
    total_changes = diff["added_count"] + diff["removed_count"]
    ratio = total_changes / max(1, before_count)
    if ratio >= 0.75:
        return "high"
    if ratio >= 0.4:
        return "medium"
    return "low"


def compute_draft_plan(
    supabase: Any, user_id: str, *, expected_exam_id: str | None = None
) -> dict[str, Any]:
    """Compute today's plan candidate without mutating any persisted plan.

    Returns the same envelope as ``apply_plan`` but with ``applied=False``,
    no version row, no adaptation event, and the active plan's still-planned
    tasks for today as ``before_tasks``. Safe to call repeatedly.
    """
    try:
        computed = _compute_plan(
            supabase, user_id, reason="plan_draft", expected_exam_id=expected_exam_id
        )
        if not computed.get("generated"):
            return computed

        tasks = computed["tasks"]
        before = _active_plan_today_tasks(supabase, user_id)
        before_tasks = [
            {
                "topic_id": b.get("topic_id"),
                "title": b.get("title"),
                "task_type": b.get("task_type"),
                "topic": b.get("topic"),
                "priority_score": b.get("priority_score"),
                "planned_minutes": b.get("planned_minutes"),
                "why_this_task": b.get("why_this_task"),
                "status": b.get("status"),
            }
            for b in before
        ]
        after_tasks = [_task_summary(t) for t in tasks]
        diff = _diff_tasks(before_tasks, after_tasks)
        tradeoffs = _build_tradeoffs(before_tasks, after_tasks)
        exam = computed["exam"]
        return {
            "applied": False,
            "generated": True,
            "exam": exam.get("slug"),
            "exam_name": exam.get("name"),
            "competition_pressure": computed["competition_pressure"],
            "focus": computed["focus"],
            "before_tasks": before_tasks,
            "after_tasks": after_tasks,
            "changes": diff,
            "tradeoffs": tradeoffs,
            "risk_level": _risk_level(diff, len(before_tasks)),
            "generated_at": _now_iso(),
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("compute_draft_plan failed for %s", user_id)
        return {
            "generated": False,
            "reason": "error",
            "error": str(exc)[:200],
        }


def apply_plan(
    supabase: Any,
    user_id: str,
    *,
    reason: str = "manual_apply",
    event_type: str = "manual_regeneration",
    expected_exam_id: str | None = None,
) -> dict[str, Any]:
    """Apply today's computed plan. Always persists when ``generated=True``.

    Idempotent: ``_persist`` reuses the active plan, clears today's still-
    planned tasks for that plan, and inserts the fresh set; completed /
    in-progress tasks survive. Creates exactly one ``study_plan_versions``
    row and one ``study_adaptation_events`` row per call.

    ``event_type`` defaults to ``manual_regeneration`` — the value present
    in the ``study_adaptation_events.event_type`` CHECK constraint
    (migration 033). The previous default ``manual_application`` was not
    in the constraint, so every audit insert was being rejected by
    Postgres and silently swallowed by the old bare ``_safe`` wrapper.
    """
    try:
        before = _active_plan_today_tasks(supabase, user_id)
        before_tasks = [
            {
                "topic_id": b.get("topic_id"),
                "title": b.get("title"),
                "task_type": b.get("task_type"),
                "topic": b.get("topic"),
                "priority_score": b.get("priority_score"),
                "planned_minutes": b.get("planned_minutes"),
                "why_this_task": b.get("why_this_task"),
                "status": b.get("status"),
            }
            for b in before
        ]

        computed = _compute_plan(
            supabase, user_id, reason=reason, expected_exam_id=expected_exam_id
        )
        if not computed.get("generated"):
            return computed

        tasks = computed["tasks"]
        exam = computed["exam"]
        persisted = _persist(
            supabase,
            user_id,
            exam,
            computed["plan_phase_id"],
            tasks,
            computed["input_context"],
            event_type,
        )
        if not persisted.get("generated"):
            return persisted

        after_tasks = [_task_summary(t) for t in tasks]
        diff = _diff_tasks(before_tasks, after_tasks)
        return {
            **persisted,
            "applied": True,
            "exam": exam.get("slug"),
            "exam_name": exam.get("name"),
            "task_count": len(tasks),
            "focus": computed["focus"],
            "competition_pressure": computed["competition_pressure"],
            "before_tasks": before_tasks,
            "after_tasks": after_tasks,
            "changes": diff,
            "risk_level": _risk_level(diff, len(before_tasks)),
            "tasks": after_tasks,  # back-compat with /api/study/plan/generate callers
            "generated_at": _now_iso(),
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("apply_plan failed for %s", user_id)
        return {
            "generated": False,
            "reason": "error",
            "error": str(exc)[:200],
        }


def generate_plan(
    supabase: Any,
    user_id: str,
    *,
    reason: str = "manual_generation",
    event_type: str = "manual_regeneration",
    expected_exam_id: str | None = None,
) -> dict[str, Any]:
    """Generate and persist today's study plan for ``user_id``.

    Thin wrapper over :func:`apply_plan` — kept for callers of the existing
    ``/api/study/plan/generate`` route and for scheduled / signal-driven
    regenerations (``regen.regenerate_on_signal``).
    """
    return apply_plan(
        supabase, user_id, reason=reason, event_type=event_type,
        expected_exam_id=expected_exam_id,
    )


# ───────────────────────── regen-trigger surfacing ─────────────────────────
#
# These thresholds match the auto-regen contract described in
# docs/product/aspirant-platform-strategy.md §2: misses > 2 consecutive days,
# upcoming deadline compression, mock-score drift, backlog over threshold.
# The numbers are intentionally conservative so the strip is only loud when
# the planner would actually rewire the schedule on the next regen.
_MISSED_STREAK_MIN = 2
_BACKLOG_LOW = 7
_BACKLOG_MED = 10
_BACKLOG_HIGH = 15
_DEADLINE_MED_DAYS = 30
_DEADLINE_HIGH_DAYS = 14
_MOCK_DRIFT_MIN_PER_WINDOW = 2
_MOCK_DRIFT_LOW_PP = 5
_MOCK_DRIFT_MED_PP = 10


def _missed_days_streak(supabase: Any, user_id: str, today: date) -> dict[str, Any] | None:
    """Count consecutive days (ending yesterday) where every planned task
    was missed/skipped. Returns the trigger payload or None when below the
    floor (≥ 2 consecutive days).
    """
    lookback = 14
    rows = _safe(
        lambda: (
            supabase.table("study_tasks")
            .select("status, scheduled_date")
            .eq("user_id", user_id)
            .gte("scheduled_date", (today - timedelta(days=lookback)).isoformat())
            .lt("scheduled_date", today.isoformat())
            .limit(2000)
            .execute()
            .data
        ),
        default=[],
    ) or []
    if not rows:
        return None
    by_day: dict[str, list[str]] = {}
    for r in rows:
        d = (r.get("scheduled_date") or "")[:10]
        if not d:
            continue
        by_day.setdefault(d, []).append((r.get("status") or "planned").lower())

    streak = 0
    streak_start: str | None = None
    cursor = today - timedelta(days=1)
    while cursor >= today - timedelta(days=lookback):
        key = cursor.isoformat()
        statuses = by_day.get(key)
        if not statuses:
            break  # day with no planned task breaks the streak
        if any(s == "completed" for s in statuses):
            break
        streak += 1
        streak_start = key
        cursor -= timedelta(days=1)

    if streak < _MISSED_STREAK_MIN:
        return None
    if streak >= 4:
        severity = "high"
    elif streak >= 3:
        severity = "medium"
    else:
        severity = "low"
    return {
        "code": "missed_days_streak",
        "severity": severity,
        "label": f"Missed {streak} planned day(s) in a row.",
        "evidence": {
            "streak_length": streak,
            "streak_start_date": streak_start,
            "lookback_days": lookback,
        },
    }


def _backlog_trigger(supabase: Any, user_id: str, today: date) -> dict[str, Any] | None:
    """Open backlog over the LOW threshold becomes a regen trigger."""
    rows = _safe(
        lambda: (
            supabase.table("study_tasks")
            .select("status")
            .eq("user_id", user_id)
            .lte("scheduled_date", today.isoformat())
            .limit(5000)
            .execute()
            .data
        ),
        default=[],
    ) or []
    backlog = sum(
        1 for r in rows
        if (r.get("status") or "").lower() in {"planned", "in_progress", "carried_forward"}
    )
    if backlog < _BACKLOG_LOW:
        return None
    if backlog >= _BACKLOG_HIGH:
        severity = "high"
    elif backlog >= _BACKLOG_MED:
        severity = "medium"
    else:
        severity = "low"
    return {
        "code": "backlog_threshold",
        "severity": severity,
        "label": f"Open backlog is {backlog} tasks (threshold {_BACKLOG_LOW}).",
        "evidence": {
            "backlog_count": backlog,
            "threshold_low": _BACKLOG_LOW,
            "threshold_med": _BACKLOG_MED,
            "threshold_high": _BACKLOG_HIGH,
        },
    }


def _deadline_trigger(supabase: Any, user_id: str, today: date) -> dict[str, Any] | None:
    """Target-exam ``exam_start`` within ``_DEADLINE_MED_DAYS`` is a trigger."""
    target = _safe(lambda: _resolve_target_exam(supabase, user_id), None)
    exam_id = target.get("id") if target else None
    if not exam_id:
        return None
    cycle = _cached_next_cycle(supabase, exam_id, today.isoformat())
    if not cycle:
        return None
    exam_start_str = cycle.get("exam_start")
    try:
        exam_start = date.fromisoformat(str(exam_start_str)[:10])
    except (TypeError, ValueError):
        return None
    days_remaining = (exam_start - today).days
    if days_remaining < 0 or days_remaining > _DEADLINE_MED_DAYS:
        return None
    severity = "high" if days_remaining <= _DEADLINE_HIGH_DAYS else "medium"
    return {
        "code": "deadline_compression",
        "severity": severity,
        "label": f"Exam is in {days_remaining} day(s) ({exam_start.isoformat()}).",
        "evidence": {
            "days_remaining": days_remaining,
            "exam_start": exam_start.isoformat(),
            "exam_cycle_id": cycle.get("id"),
        },
    }


def _mock_drift_trigger(supabase: Any, user_id: str) -> dict[str, Any] | None:
    """Compare avg percentage of the last 2 mocks vs the prior 2."""
    rows = _safe(
        lambda: (
            supabase.table("mock_tests")
            .select("id, attempted_at, scored_marks, total_marks")
            .eq("user_id", user_id)
            .order("attempted_at", desc=True)
            .limit(8)
            .execute()
            .data
        ),
        default=[],
    ) or []

    def _pct(m: dict[str, Any]) -> float | None:
        try:
            scored = float(m.get("scored_marks") or 0)
            total = float(m.get("total_marks") or 0)
            if total <= 0:
                return None
            return (scored / total) * 100.0
        except (TypeError, ValueError):
            return None

    pcts = [p for p in (_pct(m) for m in rows) if p is not None]
    if len(pcts) < _MOCK_DRIFT_MIN_PER_WINDOW * 2:
        return None
    recent = pcts[:_MOCK_DRIFT_MIN_PER_WINDOW]
    prior = pcts[_MOCK_DRIFT_MIN_PER_WINDOW : _MOCK_DRIFT_MIN_PER_WINDOW * 2]
    recent_avg = sum(recent) / len(recent)
    prior_avg = sum(prior) / len(prior)
    delta = round(recent_avg - prior_avg, 1)
    if delta >= -_MOCK_DRIFT_LOW_PP:
        return None
    drop = abs(delta)
    severity = "high" if drop >= _MOCK_DRIFT_MED_PP else "medium" if drop >= _MOCK_DRIFT_LOW_PP + 2 else "low"
    return {
        "code": "mock_score_drift",
        "severity": severity,
        "label": f"Recent mock average dropped {drop:.1f} pts vs the prior window.",
        "evidence": {
            "recent_avg_pct": round(recent_avg, 1),
            "prior_avg_pct": round(prior_avg, 1),
            "delta_pct": delta,
            "window_size": _MOCK_DRIFT_MIN_PER_WINDOW,
        },
    }


def build_regen_triggers(supabase: Any, user_id: str) -> list[dict[str, Any]]:
    """Return the active auto-regen triggers as a deterministic list.

    Each item: ``{code, severity, label, evidence}`` where ``code`` is one
    of ``missed_days_streak | backlog_threshold | deadline_compression |
    mock_score_drift``. The list is informational — the planner does NOT
    apply changes from this surface; the user still draws via
    /api/study/plan/draft and applies via /api/study/plan/apply.
    """
    if not user_id:
        return []
    today = date.today()
    triggers: list[dict[str, Any]] = []
    for builder in (
        lambda: _missed_days_streak(supabase, user_id, today),
        lambda: _backlog_trigger(supabase, user_id, today),
        lambda: _deadline_trigger(supabase, user_id, today),
        lambda: _mock_drift_trigger(supabase, user_id),
    ):
        try:
            row = builder()
        except Exception:  # noqa: BLE001
            row = None
        if row:
            triggers.append(row)
    return triggers
