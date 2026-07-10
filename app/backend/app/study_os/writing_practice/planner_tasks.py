"""Deterministic English-writing task generation for the planner (EWP-5, §11).

The Study OS planner (``study_os.planner``) builds topic-study tasks from locked
``exam_topic_coverage``. This module lets it ALSO auto-generate real
``english_writing_session`` practice tasks, so EWP sentence tasks are created by
the planner — not hand-inserted by an operator.

Two responsibilities, both deterministic (no AI, no randomness — same inputs
always produce the same tasks):

* :func:`resolve_writing_eligible_topic_ids` — the DB read. The subset of
  candidate coverage ``topic_id``s that currently have a launchable
  ``sentence_construction`` prompt: verified + active + English-subject +
  runtime-ready + applicability-active for the exam context. This mirrors the
  launch-time selection contract in ``api.writing_practice._select_launch_prompt``
  so a generated task can never dead-end on a ``409 no_eligible_prompt``.

* :func:`build_writing_tasks` — the pure builder. Given already priority-ordered
  scored coverage rows and the eligible-topic set, emit writing task dicts
  (``task_type='sentence_construction'``, ``launch_type='english_writing_session'``,
  ``launch_entity_id=None``, ``launch_context={'exercise_type': ...}``), deduped
  against still-active writing tasks and capped.

Layering: this lives in ``study_os.writing_practice`` (never imports the API
layer). It reuses the applicability resolver and the launch-type constant from
the same package.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Iterable

from app.study_os.writing_practice import applicability
from app.study_os.writing_practice.launch import LAUNCH_ENGLISH_WRITING_SESSION

logger = logging.getLogger("career_copilot.study_os.writing_practice.planner_tasks")

# The only runtime-ready writing exercise today (migration 224 /
# ``cms_writing_runtime_ready_types``). The planner generates this type; other
# writing types (correction/vocab/paragraph) stay inactive until they reach
# runtime readiness. Kept as a fail-safe fallback if the DB function is
# unreachable — the RPC is authoritative when it responds.
_RUNTIME_READY_FALLBACK: tuple[str, ...] = ("sentence_construction",)
_ENGLISH_SUBJECT_SLUG = "english-language"

# Exercise type the planner generates. task_type mirrors the exercise type per
# architecture §11.2.
WRITING_EXERCISE_TYPE = "sentence_construction"
_WRITING_TASK_LABEL = "Sentence practice"


def _safe(call: Callable[[], Any], default: Any = None) -> Any:
    try:
        return call()
    except Exception as exc:  # noqa: BLE001
        logger.warning("writing-planner read failed: %s", exc)
        return default


def _english_subject_id(supabase: Any) -> str | None:
    """The ``english-language`` subject id (migration 205 seed), or None.

    Writing prompts are subject-scoped; the launch selector filters candidates
    on this subject, so eligibility resolution must gate on the same subject.
    """
    rows = _safe(
        lambda: (
            supabase.table("subjects")
            .select("id")
            .eq("slug", _ENGLISH_SUBJECT_SLUG)
            .limit(1)
            .execute()
            .data
        ),
        default=[],
    ) or []
    row = rows[0] if rows else None
    return str(row["id"]) if row and row.get("id") else None


def _runtime_ready_types(supabase: Any) -> set[str]:
    """Runtime-ready exercise types. DB function authoritative; constant fallback."""
    data = _safe(
        lambda: supabase.rpc("cms_writing_runtime_ready_types", {}).execute().data,
        default=None,
    )
    if isinstance(data, list) and data:
        return {str(x) for x in data}
    return set(_RUNTIME_READY_FALLBACK)


def resolve_writing_eligible_topic_ids(
    supabase: Any,
    *,
    exam_id: str | None,
    exam_phase_id: str | None,
    candidate_topic_ids: Iterable[str] | None = None,
) -> set[str]:
    """Coverage ``topic_id``s that currently have a launchable writing prompt.

    Fail-closed: any read failure or missing English subject yields the empty
    set, so the planner simply generates no writing tasks rather than emitting
    ones that would 409 on launch. Mirrors ``_select_launch_prompt``'s gates
    (verified + active + English subject + runtime-ready + applicability) at
    topic granularity.
    """
    candidates = (
        [str(t) for t in candidate_topic_ids if t] if candidate_topic_ids is not None else None
    )
    if candidates is not None and not candidates:
        return set()
    subject_id = _english_subject_id(supabase)
    if not subject_id:
        # No english-language subject resolved (mis-seeded config or read
        # failure). Fail closed: generate no writing tasks rather than matching
        # prompts without subject scoping.
        return set()

    def _query() -> list[dict[str, Any]]:
        q = (
            supabase.table("writing_prompts")
            .select("id,exercise_type,topic_id")
            .eq("reviewer_status", "verified")
            .eq("is_active", True)
            .eq("subject_id", subject_id)
        )
        if candidates is not None:
            q = q.in_("topic_id", candidates)
        return q.limit(2000).execute().data

    ready_types = _runtime_ready_types(supabase)
    # The planner stamps every generated task as WRITING_EXERCISE_TYPE
    # (sentence_construction), so eligibility must be pinned to that exact type —
    # NOT merely "any runtime-ready type". The runtime-ready allowlist is designed
    # to widen (vocabulary_in_context, correction, ...) via future migrations; if
    # we accepted any ready type, a topic whose only prompt is a future vocabulary
    # prompt would wrongly make the planner emit a sentence_construction task.
    # Also guards that our own type is still runtime-ready (a migration removing it
    # from the allowlist must stop generation, not emit non-launchable tasks).
    if WRITING_EXERCISE_TYPE not in ready_types:
        return set()
    rows = _safe(_query, default=[]) or []
    # prompt_id -> topic_id for sentence_construction, topic-pinned prompts only.
    ready: list[tuple[str, str]] = [
        (str(r["id"]), str(r["topic_id"]))
        for r in rows
        if r.get("exercise_type") == WRITING_EXERCISE_TYPE and r.get("topic_id")
    ]
    if not ready:
        return set()

    eligible_prompt_ids = _safe(
        lambda: applicability.resolve_applicable_prompt_ids(
            supabase,
            [pid for pid, _ in ready],
            exam_id=exam_id,
            exam_phase_id=exam_phase_id,
        ),
        default=set(),
    ) or set()
    return {tid for pid, tid in ready if pid in eligible_prompt_ids}


def _why_writing(cov: dict[str, Any]) -> dict[str, Any]:
    """Deterministic ``why_this_task`` for a generated writing task."""
    topic = cov.get("topic_name") or "This topic"
    high_yield = bool(cov.get("is_high_yield"))
    yield_bit = "a verified high-yield topic" if high_yield else "a verified topic"
    summary = (
        f"{topic} is {yield_bit} for your exam with English writing practice "
        f"available — scheduled as a sentence practice block."
    )
    return {
        "coverage_priority": cov.get("coverage_priority"),
        "high_yield": high_yield,
        "priority_score": cov.get("_priority_score"),
        "exercise_type": WRITING_EXERCISE_TYPE,
        "launch_target": LAUNCH_ENGLISH_WRITING_SESSION,
        "summary": summary,
    }


def build_writing_tasks(
    ordered_coverage: list[dict[str, Any]],
    *,
    exam_id: str,
    exam_phase_id: str | None,
    minutes: int,
    today: str,
    eligible_topic_ids: set[str],
    existing_writing_topic_ids: set[str],
    max_writing_tasks: int,
) -> list[dict[str, Any]]:
    """Emit ``english_writing_session`` task dicts for writing-eligible topics.

    ``ordered_coverage`` is the planner's already priority-ordered, scored
    coverage list — iteration order gives deterministic, priority-first
    selection. A topic is emitted only when it is writing-eligible, not already
    carrying an active (non-planned) writing task today, and not already picked
    in this pass. Capped at ``max_writing_tasks``.

    The emitted task carries ``launch_entity_id=None`` (no session yet — the
    learner's click creates it via ``POST /api/study/tasks/{id}/launch-writing``)
    and ``exam_phase_id`` equal to the phase eligibility was resolved against, so
    the launch selector re-derives the same eligible prompt set.
    """
    if max_writing_tasks <= 0 or not eligible_topic_ids:
        return []
    tasks: list[dict[str, Any]] = []
    picked: set[str] = set()
    for cov in ordered_coverage:
        if len(tasks) >= max_writing_tasks:
            break
        tid = cov.get("topic_id")
        if not tid or tid not in eligible_topic_ids:
            continue
        if tid in existing_writing_topic_ids or tid in picked:
            continue
        picked.add(tid)
        why = _why_writing(cov)
        tasks.append(
            {
                "user_id": None,  # filled in by planner._persist
                "title": f"{cov.get('topic_name')} · {_WRITING_TASK_LABEL}",
                "task_type": WRITING_EXERCISE_TYPE,
                "subject": cov.get("subject_name"),
                "topic": cov.get("topic_name"),
                "subject_id": cov.get("subject_id"),
                "topic_id": tid,
                "exam_id": exam_id,
                "exam_phase_id": exam_phase_id,
                "exam_topic_coverage_id": cov.get("coverage_id"),
                "scheduled_date": today,
                "day_label": "Today",
                "status": "planned",
                "planned_minutes": minutes,
                "priority_score": cov.get("_priority_score"),
                "why_this_task": why,
                "launch_type": LAUNCH_ENGLISH_WRITING_SESSION,
                "launch_entity_id": None,
                "launch_context": {"exercise_type": WRITING_EXERCISE_TYPE},
            }
        )
    return tasks
