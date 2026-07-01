"""Typed launch-target -> action URL/label computation (architecture §11.1).

study_tasks stores a typed launch target (launch_type / launch_entity_id /
launch_context); the mission-control API computes the frontend URL and label at
response time. Never store a frontend URL in the database.
"""
from __future__ import annotations

LAUNCH_ENGLISH_WRITING_SESSION = "english_writing_session"

# Exercise-type -> aspirant-facing label for the launch button.
_EXERCISE_LABELS = {
    "sentence_construction": "Start sentence practice",
    "sentence_correction": "Start correction practice",
    "vocabulary_in_context": "Start vocabulary practice",
    "sentence_rewrite": "Start rewrite practice",
    "sentence_reconstruction": "Start sentence reconstruction",
    "paragraph_writing": "Start paragraph practice",
    "summary_writing": "Start summary practice",
    "precis_practice": "Start précis practice",
    "essay_practice": "Start essay practice",
    "letter_practice": "Start letter practice",
}
_DEFAULT_LABEL = "Start writing practice"


def compute_action(launch_type: str | None, launch_entity_id, launch_context) -> dict | None:
    """Return {action_url, action_label} for a task's launch target, or None.

    Only ``english_writing_session`` is handled here; unknown/None launch types
    return None so callers can fall back to their existing behaviour.
    """
    if launch_type != LAUNCH_ENGLISH_WRITING_SESSION or not launch_entity_id:
        return None
    context = launch_context or {}
    exercise_type = context.get("exercise_type") if isinstance(context, dict) else None
    return {
        "action_url": f"/app/study/practice/english/{launch_entity_id}",
        "action_label": _EXERCISE_LABELS.get(exercise_type, _DEFAULT_LABEL),
    }
