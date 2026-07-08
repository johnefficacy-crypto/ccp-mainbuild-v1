"""PYQ v2 PR-9 (unit A) — planner task -> PYQ practice launch resolution.

A planner "practice"/"revision" study task launches a PYQ practice attempt over
the task's topic. The task row is the SOLE authority for exam context (§17
content-scoping): a client never supplies mode/target/exam. This module holds the
two PURE resolution helpers the launch endpoint composes:

  * ``resolve_practice_payload`` — map a ``study_tasks`` row to the
    ``start_pyq_practice`` argument shape, or None when the task has no
    topic/exam to practice (only topic practice is wired here).
  * ``pyq_practice_action`` — the typed launch-target -> action URL/label shape
    (mirrors ``writing_practice/launch.py::compute_action``); the frontend
    affordance a mission-control response renders. Never store a URL in the DB.
"""
from __future__ import annotations

LAUNCH_PYQ_PRACTICE = "pyq_practice"

_ACTION_LABEL = "Practice this topic"


def resolve_practice_payload(task: dict) -> dict | None:
    """Map a ``study_tasks`` row to ``start_pyq_practice`` kwargs, or None.

    A task resolves to topic PYQ practice only when it pins BOTH a ``topic_id``
    and an ``exam_id`` (topic ids are shared across exams — topic practice is
    only well-defined inside one exam). A task with neither can't resolve here.
    """
    topic_id = task.get("topic_id")
    exam_id = task.get("exam_id")
    if not topic_id or not exam_id:
        return None
    return {"mode": "topic", "target_id": topic_id, "exam_id": exam_id}


def pyq_practice_action(launch_type: str | None, launch_entity_id, launch_context) -> dict | None:
    """Return {action_url, action_label} for a PYQ-practice launch target, or None.

    Only ``pyq_practice`` is handled here; unknown/None launch types return None
    so callers fall back to their existing behaviour. ``action_url`` is the stable
    frontend affordance placeholder (a button POSTs the launch endpoint; the exact
    wiring is a later slice), NEVER persisted to the database.
    """
    if launch_type != LAUNCH_PYQ_PRACTICE or not launch_entity_id:
        return None
    return {
        "action_url": f"/app/study/tasks/{launch_entity_id}/pyq-practice",
        "action_label": _ACTION_LABEL,
    }
