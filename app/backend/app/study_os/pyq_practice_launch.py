"""PYQ v2 PR-9 (unit A) — planner task -> PYQ practice launch resolution.

A planner "practice"/"revision" study task launches a PYQ practice attempt over
the task's topic. The task row is the SOLE authority for exam context (§17
content-scoping): a client never supplies mode/target/exam.

``resolve_practice_payload`` maps a ``study_tasks`` row to the
``start_pyq_practice`` argument shape, or None when the task has no topic/exam to
practice (only topic practice is wired here).

The typed-launch -> action URL/label computation is deliberately NOT implemented
here yet: the launch endpoint is **task-owned** (`POST /study/tasks/{task_id}/
launch-pyq-practice`), but a task's `launch_entity_id` is the TOPIC id, not the
task id — so an action helper keyed on `launch_entity_id` would encode the wrong
identity. Computing the action belongs at the mission-control call site (which
has the `study_tasks.id`) and is a later slice.
"""
from __future__ import annotations

LAUNCH_PYQ_PRACTICE = "pyq_practice"


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
