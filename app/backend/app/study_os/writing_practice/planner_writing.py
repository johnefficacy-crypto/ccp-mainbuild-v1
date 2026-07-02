"""EWP-5 — deterministic English writing-task generation for the planner.

Architecture §11.2 (task types), §11.3 (scheduling triggers), §15 (learning
progression / difficulty gating) and §10 (mastery shadow-safety).

Contract / hard constraints (all non-negotiable):

* **Verified-only reads.** Prompts are selected ONLY where
  ``reviewer_status='verified' AND is_active=true`` AND
  ``difficulty_level <= user_current_level``.
* **Level source is the fold, never the raw table.** ``user_current_level`` is
  derived from ``effective_user_topic_mastery_evidence`` (§4.12d / §15). If that
  fold cannot be read, the generator gates conservatively and NO-OPs — a raw
  ``user_topic_mastery_evidence`` read is never used for level.
* **Dormant until a prompt bank exists.** There are currently ZERO verified
  prompts, so with no eligible verified prompt the generator returns
  ``{"generated": 0}`` and writes nothing. This is expected in production.
* **No live mastery writes** (§10 — shadow only). This module never writes
  ``user_topic_mastery`` / evidence / shadow rows. ``next_revision_at`` is read
  as a *schedule* trigger only — never a mastery delta.
* **No new AI writes. Determinism > heuristics.** Same inputs → same output.
* **Idempotent.** A writing task is not generated twice for the same
  (trigger, topic) on the same day.

Sessions are created through the existing ``ewp_create_writing_session`` RPC in
learning mode (mirroring EWP-2's ``create_session``); the resulting session id
becomes the task's ``launch_entity_id``. The frontend URL is NEVER stored — it
is computed at response time by :mod:`app.study_os.writing_practice.launch`.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable

from app.study_os.writing_practice.constraints import validate_unit_constraints
from app.study_os.writing_practice.launch import LAUNCH_ENGLISH_WRITING_SESSION

logger = logging.getLogger("career_copilot.study_os.writing_practice.planner")

# §11.3: a repeated grammar error must recur at least this many times before it
# becomes a correction drill (deterministic threshold; conservative).
_GRAMMAR_ERROR_MIN_FREQUENCY = 2

# §15 persona bootstrap for cold-start level (writing_comfort_level → level).
_COMFORT_BOOTSTRAP = {
    "one_sentence": 3,
    "short_paragraph": 6,
    "precis": 8,
    "full_essay": 9,
}
_DEFAULT_COLD_START_LEVEL = 1

# Evidence-tier → minimum implied level once real production evidence exists.
# tier_rank order is recognition < correction < production < retention (§4.12a).
# Conservative: only production/retention evidence lifts the ceiling; anything
# below keeps the persona bootstrap. Evidence-driven fine-grained progression
# beyond this is intentionally deferred (see checklist EWP-5).
_TIER_MIN_LEVEL = {"production": 7, "retention": 8}

# §11.2 task_type ↔ prompt exercise_type used per trigger.
_TASK_RETEST = "writing_revision"
_TASK_GRAMMAR = "grammar_correction"
_EXERCISE_CORRECTION = "sentence_correction"

_PLANNED_MINUTES = 15


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _safe(call: Callable[[], Any], default: Any = None) -> Any:
    try:
        return call()
    except Exception as exc:  # noqa: BLE001
        logger.warning("writing-planner read/write failed: %s", exc)
        return default


# Sentinel: distinguishes a failed fold read (→ no-op) from a legitimately empty
# fold (→ cold-start). Fail closed on read failure.
_FOLD_READ_FAILED = object()


def _persona_bootstrap_level(supabase: Any, user_id: str) -> int:
    rows = (
        _safe(
            lambda: (
                supabase.table("aspirant_persona_snapshots")
                .select("writing_comfort_level")
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
    comfort = (rows[0] if rows else {}).get("writing_comfort_level")
    return _COMFORT_BOOTSTRAP.get(comfort, _DEFAULT_COLD_START_LEVEL)


def _derive_user_level(supabase: Any, user_id: str) -> int | None:
    """User's current writing level (§15) from the effective-evidence fold.

    Returns ``None`` when the fold cannot be read — the caller then NO-OPs
    (fail-closed). A successfully-read but empty fold yields the persona
    cold-start bootstrap. Production/retention evidence lifts the ceiling per
    ``_TIER_MIN_LEVEL``. The raw append-only evidence table is never read here.
    """
    fold_rows = _safe(
        lambda: (
            supabase.table("effective_user_topic_mastery_evidence")
            .select("evidence_tier")
            .eq("user_id", user_id)
            .limit(5000)
            .execute()
            .data
        ),
        default=_FOLD_READ_FAILED,
    )
    if fold_rows is _FOLD_READ_FAILED:
        return None
    base = _persona_bootstrap_level(supabase, user_id)
    tiers = {r.get("evidence_tier") for r in (fold_rows or [])}
    ceiling = max(
        (lvl for tier, lvl in _TIER_MIN_LEVEL.items() if tier in tiers),
        default=0,
    )
    return max(base, ceiling)


def _eligible_prompts(supabase: Any, exam_id: str, level: int) -> list[dict[str, Any]]:
    """Verified + active prompts at or below ``level`` for the exam.

    Verified-only read (non-negotiable): both filters are applied at the query
    level. The ``difficulty_level`` ceiling is applied in Python because
    PostgREST ``lte`` is fine but keeping the projection tight lets the caller
    pick the exercise it needs deterministically.
    """
    rows = (
        _safe(
            lambda: (
                supabase.table("writing_prompts")
                .select(
                    "id, exercise_type, difficulty_level, topic_id, microtopic_id, "
                    "subject_id, required_sentence_count"
                )
                .eq("exam_id", exam_id)
                .eq("reviewer_status", "verified")
                .eq("is_active", True)
                .lte("difficulty_level", level)
                .limit(500)
                .execute()
                .data
            ),
            default=[],
        )
        or []
    )
    # Deterministic order: easiest first, then a stable id tiebreak.
    return sorted(
        rows,
        key=lambda p: (int(p.get("difficulty_level") or 0), str(p.get("id") or "")),
    )


def _pick_prompt(
    prompts: list[dict[str, Any]],
    *,
    exercise_type: str | None = None,
    topic_id: str | None = None,
    microtopic_id: str | None = None,
) -> dict[str, Any] | None:
    """Deterministically pick the best eligible prompt for a trigger.

    Preference order: exact exercise+microtopic, then exercise+topic, then
    exercise-only, then microtopic/topic at any exercise, then the easiest
    available. ``prompts`` is already sorted easiest-first.
    """
    def _first(pred: Callable[[dict[str, Any]], bool]) -> dict[str, Any] | None:
        return next((p for p in prompts if pred(p)), None)

    if exercise_type and microtopic_id:
        hit = _first(lambda p: p.get("exercise_type") == exercise_type and p.get("microtopic_id") == microtopic_id)
        if hit:
            return hit
    if exercise_type and topic_id:
        hit = _first(lambda p: p.get("exercise_type") == exercise_type and p.get("topic_id") == topic_id)
        if hit:
            return hit
    if exercise_type:
        hit = _first(lambda p: p.get("exercise_type") == exercise_type)
        if hit:
            return hit
    if microtopic_id:
        hit = _first(lambda p: p.get("microtopic_id") == microtopic_id)
        if hit:
            return hit
    if topic_id:
        hit = _first(lambda p: p.get("topic_id") == topic_id)
        if hit:
            return hit
    return prompts[0] if prompts else None


def _existing_writing_task_keys(supabase: Any, user_id: str, today: str) -> set[tuple[str, str]]:
    """(trigger, topic_id) keys of today's already-generated writing tasks.

    Used for idempotency: mirrors the planner's clear-and-rebuild de-dup but
    scoped to writing launch tasks only, so a re-run on the same day does not
    duplicate a drill for the same trigger/topic.
    """
    rows = (
        _safe(
            lambda: (
                supabase.table("study_tasks")
                .select("launch_context, topic_id, scheduled_date, launch_type")
                .eq("user_id", user_id)
                .eq("scheduled_date", today)
                .eq("launch_type", LAUNCH_ENGLISH_WRITING_SESSION)
                .limit(500)
                .execute()
                .data
            ),
            default=[],
        )
        or []
    )
    keys: set[tuple[str, str]] = set()
    for r in rows:
        ctx = r.get("launch_context") or {}
        trigger = ctx.get("trigger") if isinstance(ctx, dict) else None
        topic = (ctx.get("topic_id") if isinstance(ctx, dict) else None) or r.get("topic_id")
        if trigger and topic:
            keys.add((str(trigger), str(topic)))
    return keys


def _retest_triggers(supabase: Any, user_id: str, exam_id: str, today: str) -> list[dict[str, Any]]:
    """§11.3 hard trigger: a microtopic whose ``next_revision_at`` is due.

    Reads ``user_topic_mastery.next_revision_at`` purely as a *schedule* signal
    (not a mastery delta — §10 shadow-safety). Rows due today or earlier fire a
    priority-band-1 retest.
    """
    rows = (
        _safe(
            lambda: (
                supabase.table("user_topic_mastery")
                .select("topic_id, next_revision_at, exam_id")
                .eq("user_id", user_id)
                .not_.is_("next_revision_at", None)
                .lte("next_revision_at", today + "T23:59:59+00:00")
                .limit(2000)
                .execute()
                .data
            ),
            default=[],
        )
        or []
    )
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for r in rows:
        tid = r.get("topic_id")
        # Exam-scoped or global rows both count; skip rows scoped to a different exam.
        if r.get("exam_id") and str(r.get("exam_id")) != str(exam_id):
            continue
        if not tid or tid in seen:
            continue
        seen.add(tid)
        out.append({"topic_id": tid, "microtopic_id": tid, "next_revision_at": r.get("next_revision_at")})
    return out


def _grammar_error_triggers(supabase: Any, user_id: str, exam_id: str) -> list[dict[str, Any]]:
    """§11.3: a repeated grammar error → a sentence-correction drill.

    Reads ``user_topic_error_patterns`` (deterministic, no AI) for the exam and
    fires on topics whose cumulative ``frequency_count`` reaches the threshold.
    """
    rows = (
        _safe(
            lambda: (
                supabase.table("user_topic_error_patterns")
                .select("topic_id, frequency_count, exam_id")
                .eq("user_id", user_id)
                .limit(5000)
                .execute()
                .data
            ),
            default=[],
        )
        or []
    )
    freq_by_topic: dict[str, int] = {}
    for r in rows:
        if r.get("exam_id") and str(r.get("exam_id")) != str(exam_id):
            continue
        tid = r.get("topic_id")
        if not tid:
            continue
        try:
            freq_by_topic[tid] = freq_by_topic.get(tid, 0) + int(r.get("frequency_count") or 0)
        except (TypeError, ValueError):
            continue
    return [
        {"topic_id": tid, "microtopic_id": tid, "frequency": freq}
        for tid, freq in sorted(freq_by_topic.items())
        if freq >= _GRAMMAR_ERROR_MIN_FREQUENCY
    ]


def _create_session(supabase: Any, user_id: str, prompt: dict[str, Any]) -> str | None:
    """Create a learning-mode writing session via the atomic EWP-2 RPC.

    Mirrors ``app.api.writing_practice.create_session``'s RPC params. Returns
    the new session id, or None if the RPC did not yield one.
    """
    constraints = validate_unit_constraints({"schema_version": 1})
    data = _safe(
        lambda: (
            supabase.rpc(
                "ewp_create_writing_session",
                {
                    "p_user": user_id,
                    "p_prompt": str(prompt["id"]),
                    "p_study_task": None,
                    "p_mode": "learning",
                    "p_projection_revision": 1,
                    "p_policy": "immediate",
                    "p_delay": None,
                    "p_unit_count": prompt.get("required_sentence_count") or 1,
                    "p_microtopic": prompt.get("microtopic_id"),
                    "p_constraints": constraints,
                },
            ).execute()
        ).data,
        default=None,
    )
    if isinstance(data, dict):
        # RPC may return the session row directly or a wrapping {"session": {...}}.
        session = data.get("session") if "session" in data else data
        return (session or {}).get("id")
    if isinstance(data, list) and data:
        return data[0].get("id")
    return None


def _task_row(
    user_id: str,
    exam_id: str,
    prompt: dict[str, Any],
    session_id: str,
    *,
    task_type: str,
    trigger: str,
    topic_id: str,
    title: str,
    why: str,
    plan_id: str | None,
    plan_version_id: str | None,
) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "plan_id": plan_id,
        "plan_version_id": plan_version_id,
        "title": title,
        "task_type": task_type,
        "topic_id": topic_id,
        "subject_id": prompt.get("subject_id"),
        "exam_id": exam_id,
        "scheduled_date": _today_iso(),
        "day_label": "Today",
        "status": "planned",
        "planned_minutes": _PLANNED_MINUTES,
        "why_this_task": {"summary": why, "trigger": trigger, "source": "ewp5_writing_planner"},
        # §11.1 typed launch target — never a stored URL.
        "launch_type": LAUNCH_ENGLISH_WRITING_SESSION,
        "launch_entity_id": session_id,
        "launch_context": {
            "exercise_type": prompt.get("exercise_type"),
            "trigger": trigger,
            "topic_id": topic_id,
            "prompt_id": prompt.get("id"),
        },
    }


def generate_writing_tasks(
    supabase: Any,
    user_id: str,
    *,
    exam_id: str,
    plan_id: str | None = None,
    plan_version_id: str | None = None,
) -> dict[str, Any]:
    """Generate English writing ``study_tasks`` for ``user_id`` (§11.2/§11.3).

    Returns ``{"generated": <int>, "task_ids": [...], "reason": <str?>}``.
    NO-OPs (``generated=0``) — writing nothing — when there is no target exam,
    the effective-evidence fold cannot be read, or no eligible verified prompt
    exists. Never raises.
    """
    try:
        if not user_id or not exam_id:
            return {"generated": 0, "reason": "missing_user_or_exam"}

        level = _derive_user_level(supabase, user_id)
        if level is None:
            # Fold unreadable → gate conservatively (§15). Do not fall back to
            # the raw table; a retracted production assertion could inflate level.
            return {"generated": 0, "reason": "level_unavailable"}

        prompts = _eligible_prompts(supabase, exam_id, level)
        if not prompts:
            # Dormant path: zero verified prompts today. Expected in production.
            return {"generated": 0, "reason": "no_eligible_prompt"}

        today = _today_iso()
        existing = _existing_writing_task_keys(supabase, user_id, today)

        planned: list[tuple[str, dict[str, Any], str, str]] = []  # (trigger, prompt, topic_id, task_type/title)
        task_rows: list[dict[str, Any]] = []

        # Trigger 1 — retest scheduled for a microtopic (priority band 1).
        for t in _retest_triggers(supabase, user_id, exam_id, today):
            topic_id = str(t["topic_id"])
            if ("retest_due", topic_id) in existing:
                continue
            prompt = _pick_prompt(prompts, topic_id=topic_id, microtopic_id=t.get("microtopic_id"))
            if not prompt:
                continue
            session_id = _create_session(supabase, user_id, prompt)
            if not session_id:
                continue
            existing.add(("retest_due", topic_id))
            task_rows.append(
                _task_row(
                    user_id, exam_id, prompt, session_id,
                    task_type=_TASK_RETEST, trigger="retest_due", topic_id=topic_id,
                    title="Writing revision · scheduled retest",
                    why="A scheduled retest is due for this microtopic (next_revision_at).",
                    plan_id=plan_id, plan_version_id=plan_version_id,
                )
            )

        # Trigger 2 — repeated grammar error → sentence-correction drill.
        for t in _grammar_error_triggers(supabase, user_id, exam_id):
            topic_id = str(t["topic_id"])
            if ("grammar_error", topic_id) in existing:
                continue
            prompt = _pick_prompt(
                prompts, exercise_type=_EXERCISE_CORRECTION,
                topic_id=topic_id, microtopic_id=t.get("microtopic_id"),
            )
            if not prompt:
                continue
            session_id = _create_session(supabase, user_id, prompt)
            if not session_id:
                continue
            existing.add(("grammar_error", topic_id))
            task_rows.append(
                _task_row(
                    user_id, exam_id, prompt, session_id,
                    task_type=_TASK_GRAMMAR, trigger="grammar_error", topic_id=topic_id,
                    title="Correction practice · recurring grammar error",
                    why="A grammar error has recurred; scheduled a sentence-correction drill.",
                    plan_id=plan_id, plan_version_id=plan_version_id,
                )
            )

        if not task_rows:
            return {"generated": 0, "reason": "no_trigger_fired"}

        inserted = _safe(
            lambda: supabase.table("study_tasks").insert(task_rows).execute().data,
            default=None,
        )
        if not inserted:
            return {"generated": 0, "reason": "task_persist_failed"}
        return {
            "generated": len(inserted),
            "task_ids": [r.get("id") for r in inserted],
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("generate_writing_tasks failed for %s", user_id)
        return {"generated": 0, "reason": "error", "error": str(exc)[:200]}
