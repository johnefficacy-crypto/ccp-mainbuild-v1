"""English writing practice — server-owned prompt resolution for subject launches.

Resolves ONE launchable writing prompt (verified + active + runtime-ready +
DEFAULT-DENY applicable) for a subject/topic/exam context WITHOUT letting the
browser pick a prompt_id. Shared by the subject-practice orchestrator
(app.api.subject_practice) and the /api/study/subjects readiness computation so
both use one gate. Pure resolution only — session creation stays in the api
layer's single-birth path (writing_practice.create_learning_session)."""
from __future__ import annotations

import logging
from typing import Any

from app.study_os.writing_practice import applicability

logger = logging.getLogger("career_copilot.study_os.writing_practice.subject_launch")

# Mirror of cms_writing_runtime_ready_types() (migration 226). DB is authoritative;
# this is only a fail-safe fallback.
RUNTIME_READY_EXERCISE_TYPES: tuple[str, ...] = ("sentence_construction",)


def runtime_ready_types(supabase: Any) -> list[str]:
    try:
        data = (supabase.rpc("cms_writing_runtime_ready_types", {}).execute()).data
    except Exception:  # noqa: BLE001 — fall back to the mirrored constant
        data = None
    if isinstance(data, (list, tuple)) and data and all(isinstance(x, str) for x in data):
        return [str(x) for x in data]
    return list(RUNTIME_READY_EXERCISE_TYPES)


def _verified_active_prompts(supabase: Any, *, subject_ids: list[str], topic_id: str | None = None) -> list[dict]:
    query = (
        supabase.table("writing_prompts")
        .select("id,exercise_type,subject_id,topic_id")
        .eq("reviewer_status", "verified")
        .eq("is_active", True)
        .in_("subject_id", list(subject_ids))
    )
    if topic_id:
        query = query.eq("topic_id", topic_id)
    return query.execute().data or []


def _applicable(supabase: Any, prompt_ids: list[str], *, exam_id, exam_phase_id) -> set[str]:
    try:
        return applicability.resolve_applicable_prompt_ids(
            supabase, prompt_ids, exam_id=exam_id, exam_phase_id=exam_phase_id
        )
    except Exception:  # noqa: BLE001 — fail-closed: unresolved applicability => not launchable
        logger.warning("applicability resolve failed; treating as none applicable", exc_info=True)
        return set()


def resolve_launch_prompt_id(
    supabase: Any, *, subject_id: str | None, topic_id: str | None, exam_id: str | None, exam_phase_id: str | None
) -> str | None:
    """Deterministically select ONE launchable prompt for a subject (+optional
    topic) in the given exam context, or None. verified+active by subject_id ->
    runtime-ready allowlist -> DEFAULT-DENY applicability -> smallest id (stable)."""
    if not subject_id:
        return None
    rows = _verified_active_prompts(supabase, subject_ids=[str(subject_id)], topic_id=topic_id)
    ready = set(runtime_ready_types(supabase))
    ready_ids = [str(r["id"]) for r in rows if r.get("exercise_type") in ready]
    if not ready_ids:
        return None
    eligible = _applicable(supabase, ready_ids, exam_id=exam_id, exam_phase_id=exam_phase_id)
    surviving = [pid for pid in ready_ids if pid in eligible]
    return sorted(surviving)[0] if surviving else None


def available_writing_subject_ids(
    supabase: Any, subject_ids: list[str], *, exam_id: str | None, exam_phase_id: str | None = None
) -> set[str]:
    """Subset of ``subject_ids`` that have >=1 launchable writing prompt (same gate
    as ``resolve_launch_prompt_id``). Batched for the subjects readiness surface."""
    ids = [str(s) for s in dict.fromkeys(subject_ids) if s]
    if not ids:
        return set()
    rows = _verified_active_prompts(supabase, subject_ids=ids)
    ready = set(runtime_ready_types(supabase))
    ready_rows = [r for r in rows if r.get("exercise_type") in ready]
    ready_ids = [str(r["id"]) for r in ready_rows]
    if not ready_ids:
        return set()
    eligible = _applicable(supabase, ready_ids, exam_id=exam_id, exam_phase_id=exam_phase_id)
    return {str(r["subject_id"]) for r in ready_rows if str(r["id"]) in eligible and r.get("subject_id")}
