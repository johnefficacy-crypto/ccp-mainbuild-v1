"""PLAN-UI-01 — the seven-day planner board: reads, placement, create, remove.

The board is the read model behind the drag-and-drop planner surface, plus the
four mutations that surface needs. It is deliberately NOT part of ``planner.py``:
nothing here scores, ranks, or generates. It moves rows the planner already
produced and creates rows the user asked for.

Two invariants run through every mutation:

* **A user's arrangement is a user placement.** Any task the user drags — a
  planner-generated one included — is stamped ``source='user'`` (migration 289).
  That is what stops the 03:00 sweep in ``planner._persist`` from deleting it.
  Moving a card is the user saying "I chose this"; the column exists to record
  exactly that.
* **Ownership is enforced here, not by RLS.** Every read and write goes through
  the service-role client, which bypasses RLS, so each query is scoped by
  ``user_id`` explicitly. A task id belonging to someone else matches no row and
  raises 404 — it never mutates.

Ordering within a day is ``day_ordinal`` (migration 290), NULL for any task the
user has never arranged. Readers sort ``day_ordinal`` ascending with NULLs last,
then ``priority_score`` descending, so an unarranged day keeps precisely the
order it has today.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

from app.study_os.plan_preferences import get_plan_preferences
from app.study_os.planner import (
    _SIZE_MINUTES,
    _DEFAULT_SIZE,
    _active_plan,
    _resolve_target_exam,
    _safe,
    load_scoped_coverage_checked,
)
from app.study_os.task_reasoning import _detail_safe_copy

logger = logging.getLogger("career_copilot.study_os.planner_board")

#: The board shows today plus the next six days. A calendar beyond seven days is
#: explicitly out of scope, and the window is the validation boundary for every
#: date a client sends: a placement outside it is rejected, not clamped.
BOARD_DAYS = 7

#: Columns the board and the mutations read back. ``source`` and ``day_ordinal``
#: are the two PLAN-PIN-01 / PLAN-UI-01 additions; everything else already
#: existed and is what a card renders.
_TASK_COLUMNS = (
    "id, title, topic, topic_id, subject, subject_id, task_type, status, "
    "scheduled_date, day_label, planned_minutes, duration_mins, priority_score, "
    "source, day_ordinal, why_this_task, exam_topic_coverage_id"
)


class BoardError(Exception):
    """A board mutation refused, with the HTTP status the route should return.

    Carrying the status here keeps the routes thin and keeps one refusal
    vocabulary across all four mutations — a not-found is 404 whether it was a
    missing plan, a missing task, or someone else's task id.
    """

    def __init__(self, code: str, message: str, status: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def window_dates(today: date | None = None) -> list[str]:
    """The board's seven ISO dates, today first."""
    start = today or _today()
    return [(start + timedelta(days=i)).isoformat() for i in range(BOARD_DAYS)]


def day_label_for(target: str, today: date | None = None) -> str:
    """The stored ``day_label`` for a board date.

    ``day_label`` is legacy display text that predates ``scheduled_date`` and is
    still what ``GET /api/study/plan`` orders by. Keeping it consistent with the
    date means a moved task does not read as "Today" on Thursday's column.
    """
    start = today or _today()
    try:
        d = date.fromisoformat(target)
    except (TypeError, ValueError):
        return "Today"
    delta = (d - start).days
    if delta == 0:
        return "Today"
    if delta == 1:
        return "Tomorrow"
    return d.strftime("%a %d %b")


def validate_board_date(value: Any, today: date | None = None) -> str:
    """Return a normalised ISO date inside the board window, or raise.

    Rejects a malformed string, a datetime, and any date outside today..+6.
    Clamping would be worse than refusing: a client that computed the wrong day
    would silently write to a day the user never pointed at.
    """
    if not isinstance(value, str):
        raise BoardError("invalid_date", "Pick a day in the next seven days.", 400)
    try:
        parsed = date.fromisoformat(value.strip())
    except ValueError:
        raise BoardError("invalid_date", "Pick a day in the next seven days.", 400) from None
    allowed = window_dates(today)
    iso = parsed.isoformat()
    if iso not in allowed:
        raise BoardError("date_out_of_window", "Pick a day in the next seven days.", 400)
    return iso


def _sort_key(task: dict[str, Any]) -> tuple[int, float, float, str]:
    """``day_ordinal`` ascending with NULLs last, then priority descending.

    Sorted in Python rather than in PostgREST because the window is at most a
    week of rows and the NULLs-last + secondary-descending combination is the
    part that has to be exactly right — a day the user has never arranged must
    come back in the same order it does today.
    """
    ordinal = task.get("day_ordinal")
    try:
        score = float(task.get("priority_score") or 0)
    except (TypeError, ValueError):
        score = 0.0
    if ordinal is None:
        return (1, 0.0, -score, str(task.get("id") or ""))
    try:
        return (0, float(ordinal), -score, str(task.get("id") or ""))
    except (TypeError, ValueError):
        return (1, 0.0, -score, str(task.get("id") or ""))


def _card(task: dict[str, Any]) -> dict[str, Any]:
    """One task as the board renders it.

    ``why`` prefers the planner's OWN sentence — ``why_this_task.summary``,
    written by ``_why_summary`` at generation time and naming the actual
    evidence ("a verified high-yield topic; 1 verified PYQ appearance; your
    recent accuracy is 80%") — and falls back to the deterministic template only
    when there is none, which is the case for every user-created task.

    Worth knowing: ``GET /api/study/plan`` does NOT do this. It calls
    ``_detail_safe_copy(t, None, task_type)`` with ``matched_topic`` hardcoded
    to ``None`` (``canonical.py:1877``), so its ``why_this_task_summary`` is
    always the generic branch even though the specific sentence is sitting in
    the same row. See "Defects observed".
    """
    task_type = (task.get("task_type") or "").lower()
    source = task.get("source") or "planner"
    why_blob = task.get("why_this_task")
    summary = (why_blob or {}).get("summary") if isinstance(why_blob, dict) else None
    return {
        "id": task.get("id"),
        "title": task.get("title") or task.get("topic") or task.get("subject"),
        "topic": task.get("topic"),
        "topic_id": task.get("topic_id"),
        "subject": task.get("subject"),
        "subject_id": task.get("subject_id"),
        "task_type": task.get("task_type"),
        "status": task.get("status") or "planned",
        "scheduled_date": task.get("scheduled_date"),
        "planned_minutes": task.get("planned_minutes") or task.get("duration_mins"),
        "priority_score": task.get("priority_score"),
        "source": source,
        "placed_by_user": source == "user",
        "day_ordinal": task.get("day_ordinal"),
        "why": summary or _detail_safe_copy(task, None, task_type),
    }


def _window_tasks(
    supabase: Any, plan_id: str, user_id: str, dates: list[str]
) -> list[dict[str, Any]] | None:
    """Every task on this plan inside the window. ``None`` on a read failure.

    Fails closed: the board must not render an empty week because one read
    blipped. A caller that gets ``None`` reports the error rather than showing a
    week the user would read as "my plan is gone".
    """
    rows = _safe(
        lambda: (
            supabase.table("study_tasks")
            .select(_TASK_COLUMNS)
            .eq("plan_id", plan_id)
            .eq("user_id", user_id)
            .gte("scheduled_date", dates[0])
            .lte("scheduled_date", dates[-1])
            .execute()
            .data
        ),
        default=None,
    )
    if rows is None:
        return None
    return list(rows)


def get_board(supabase: Any, user_id: str) -> dict[str, Any]:
    """The seven-day board: one column per date, each with its ordered cards."""
    dates = window_dates()
    plan = _active_plan(supabase, user_id)
    if not plan:
        return {
            "plan_id": None,
            "today": dates[0],
            "days": [
                {"date": d, "label": day_label_for(d), "tasks": []} for d in dates
            ],
            "max_tasks_per_day": None,
            "read_error": False,
        }

    rows = _window_tasks(supabase, plan["id"], user_id, dates)
    if rows is None:
        raise BoardError(
            "board_read_failed", "Your plan is temporarily unavailable.", 503
        )

    by_date: dict[str, list[dict[str, Any]]] = {d: [] for d in dates}
    for row in rows:
        bucket = by_date.get(str(row.get("scheduled_date") or ""))
        if bucket is not None:
            bucket.append(row)

    prefs = get_plan_preferences(supabase, user_id)
    max_per_day = prefs.get("max_tasks_per_day")

    return {
        "plan_id": plan["id"],
        "today": dates[0],
        "days": [
            {
                "date": d,
                "label": day_label_for(d),
                "tasks": [_card(t) for t in sorted(by_date[d], key=_sort_key)],
            }
            for d in dates
        ],
        "max_tasks_per_day": int(max_per_day) if max_per_day else None,
        "read_error": False,
    }


def list_candidates(supabase: Any, user_id: str) -> dict[str, Any]:
    """Locked-coverage topics the user could add, minus what is already placed.

    The same locked coverage the planner ranks, filtered by the same elective
    scope and the same muted list — so the palette can never offer a topic the
    planner itself would refuse to schedule. Ordered by the coverage row's own
    ``exam_priority_score``; this does NOT re-run the planner's scorer, which
    stays the planner's business.
    """
    exam = _safe(lambda: _resolve_target_exam(supabase, user_id), default=None)
    exam_id = (exam or {}).get("id")
    if not exam_id:
        return {"items": [], "exam_id": None, "read_error": False}

    coverage, coverage_ok = load_scoped_coverage_checked(supabase, user_id, exam_id)
    if not coverage_ok:
        raise BoardError(
            "candidates_read_failed", "Topics are temporarily unavailable.", 503
        )

    prefs = get_plan_preferences(supabase, user_id)
    muted = {str(t) for t in (prefs.get("muted_topic_ids") or [])}

    scheduled: set[str] = set()
    plan = _active_plan(supabase, user_id)
    if plan:
        rows = _window_tasks(supabase, plan["id"], user_id, window_dates())
        if rows is None:
            raise BoardError(
                "candidates_read_failed", "Topics are temporarily unavailable.", 503
            )
        scheduled = {str(r["topic_id"]) for r in rows if r.get("topic_id")}

    def _score(cov: dict[str, Any]) -> float:
        try:
            return float(cov.get("exam_priority_score") or 0)
        except (TypeError, ValueError):
            return 0.0

    items = [
        {
            "topic_id": str(c["topic_id"]),
            "topic": c.get("topic_name"),
            "subject": c.get("subject_name"),
            "subject_id": c.get("subject_id"),
            "exam_priority_score": _score(c),
            "is_high_yield": bool(c.get("is_high_yield")),
            # How regularly this topic has been asked in its own subject-paper
            # (PRED-01). A percentile within that paper, so it reads the same
            # for an optional as for GS — unlike the raw priority beside it.
            # None where the row has no year evidence; the palette shows
            # nothing rather than inventing a band.
            "predictability_band": c.get("predictability_band"),
        }
        for c in coverage
        if c.get("topic_id")
        and str(c["topic_id"]) not in scheduled
        and str(c["topic_id"]) not in muted
    ]
    items.sort(key=lambda i: (-i["exam_priority_score"], str(i["topic"] or "")))
    return {"items": items, "exam_id": exam_id, "read_error": False}


def _owned_task(supabase: Any, user_id: str, task_id: str) -> dict[str, Any]:
    """One task belonging to this user, or 404.

    ``treat_error_as_default`` is not available here, so a read failure and a
    genuine miss both surface as a miss — acceptable because the caller's next
    step is a scoped UPDATE that would also match nothing. What matters is that
    another user's id can never come back.
    """
    rows = (
        _safe(
            lambda: (
                supabase.table("study_tasks")
                .select(_TASK_COLUMNS)
                .eq("id", task_id)
                .eq("user_id", user_id)
                .limit(1)
                .execute()
                .data
            ),
            default=[],
        )
        or []
    )
    if not rows:
        raise BoardError("task_not_found", "Task not found.", 404)
    return rows[0]


def _renumber(
    supabase: Any,
    plan_id: str,
    user_id: str,
    target_date: str,
    *,
    order: list[str],
) -> None:
    """Write ``day_ordinal`` 0..n-1 across one day, in the given id order.

    Compacting on every mutation keeps ordinals dense and makes "insert at
    position k" exact. This is NOT a bulk-replace endpoint: the ids come from
    the server's own read of that day, never from the client, so a stale client
    cannot delete or reorder rows it has not seen.
    """
    for index, task_id in enumerate(order):
        _safe(
            lambda tid=task_id, idx=index: (
                supabase.table("study_tasks")
                .update({"day_ordinal": idx, "updated_at": _now_iso()})
                .eq("id", tid)
                .eq("user_id", user_id)
                .eq("plan_id", plan_id)
                .execute()
            )
        )


def _day_task_ids(
    supabase: Any, plan_id: str, user_id: str, target_date: str
) -> list[str]:
    rows = (
        _safe(
            lambda: (
                supabase.table("study_tasks")
                .select(_TASK_COLUMNS)
                .eq("plan_id", plan_id)
                .eq("user_id", user_id)
                .eq("scheduled_date", target_date)
                .execute()
                .data
            ),
            default=[],
        )
        or []
    )
    return [str(r["id"]) for r in sorted(rows, key=_sort_key) if r.get("id")]


def move_task(
    supabase: Any,
    user_id: str,
    task_id: str,
    *,
    scheduled_date: Any,
    position: Any = None,
) -> dict[str, Any]:
    """Place one task on a day at a position. Reorder and move are the same call.

    The task is stamped ``source='user'``: the user has now arranged it, so the
    nightly regeneration must leave it alone. A planner-generated card dragged
    by the user becomes a user placement — that is the whole point of the
    surface, and without the stamp the move would be undone at 03:00.
    """
    target_date = validate_board_date(scheduled_date)
    task = _owned_task(supabase, user_id, task_id)
    plan_id = task.get("plan_id") or (_active_plan(supabase, user_id) or {}).get("id")
    if not plan_id:
        raise BoardError("no_active_plan", "No active plan.", 404)

    origin_date = str(task.get("scheduled_date") or "")

    updated = _safe(
        lambda: (
            supabase.table("study_tasks")
            .update(
                {
                    "scheduled_date": target_date,
                    "day_label": day_label_for(target_date),
                    "source": "user",
                    "updated_at": _now_iso(),
                }
            )
            .eq("id", task_id)
            .eq("user_id", user_id)
            .execute()
            .data
        ),
        default=None,
    )
    if not updated:
        raise BoardError("task_not_found", "Task not found.", 404)

    # Rebuild the destination day with the moved task at `position`. Reading the
    # day back from the server (rather than trusting a client-sent order) is what
    # makes a concurrent double-move converge instead of duplicating: the task id
    # is a primary key, so it appears exactly once however many times it moved.
    ids = [t for t in _day_task_ids(supabase, plan_id, user_id, target_date) if t != task_id]
    try:
        index = int(position) if position is not None else len(ids)
    except (TypeError, ValueError):
        index = len(ids)
    index = max(0, min(index, len(ids)))
    ids.insert(index, str(task_id))
    _renumber(supabase, plan_id, user_id, target_date, order=ids)

    if origin_date and origin_date != target_date:
        _renumber(
            supabase,
            plan_id,
            user_id,
            origin_date,
            order=_day_task_ids(supabase, plan_id, user_id, origin_date),
        )

    return _card(_owned_task(supabase, user_id, task_id))


def create_user_task(
    supabase: Any,
    user_id: str,
    *,
    topic_id: Any,
    scheduled_date: Any,
    position: Any = None,
    task_type: str = "concept",
) -> dict[str, Any]:
    """Create a user-placed task for a locked-coverage topic on a board day.

    The topic must be in the user's own scoped locked coverage. Accepting an
    arbitrary topic id would let the palette place content the planner has never
    verified for this exam, which is the one thing the verified-only read
    contract exists to prevent.
    """
    target_date = validate_board_date(scheduled_date)

    plan = _active_plan(supabase, user_id)
    if not plan:
        raise BoardError("no_active_plan", "Generate a plan before adding tasks.", 409)
    plan_id = plan["id"]

    exam = _safe(lambda: _resolve_target_exam(supabase, user_id), default=None)
    exam_id = (exam or {}).get("id")
    if not exam_id:
        raise BoardError("no_target_exam", "Pick an exam first.", 409)

    coverage, coverage_ok = load_scoped_coverage_checked(supabase, user_id, exam_id)
    if not coverage_ok:
        raise BoardError("candidates_read_failed", "Topics are temporarily unavailable.", 503)
    match = next(
        (c for c in coverage if str(c.get("topic_id")) == str(topic_id)), None
    )
    if match is None:
        raise BoardError("topic_not_available", "That topic isn't in your syllabus.", 400)

    existing = _window_tasks(supabase, plan_id, user_id, window_dates())
    if existing is None:
        raise BoardError("board_read_failed", "Your plan is temporarily unavailable.", 503)
    if any(
        str(t.get("topic_id")) == str(topic_id)
        and str(t.get("scheduled_date")) == target_date
        for t in existing
    ):
        raise BoardError(
            "duplicate_topic", "That topic is already on this day.", 409
        )

    prefs = get_plan_preferences(supabase, user_id)
    size = prefs.get("preferred_task_size") or _DEFAULT_SIZE
    minutes = _SIZE_MINUTES.get(size, _SIZE_MINUTES[_DEFAULT_SIZE])

    try:
        score = float(match.get("exam_priority_score") or 0)
    except (TypeError, ValueError):
        score = 0.0

    row = {
        "user_id": user_id,
        "plan_id": plan_id,
        "title": f"{match.get('topic_name')} · Study",
        "task_type": task_type,
        "subject": match.get("subject_name"),
        "subject_id": match.get("subject_id"),
        "topic": match.get("topic_name"),
        "topic_id": str(topic_id),
        "exam_id": exam_id,
        "exam_phase_id": match.get("exam_phase_id"),
        "exam_topic_coverage_id": match.get("coverage_id"),
        "scheduled_date": target_date,
        "day_label": day_label_for(target_date),
        "status": "planned",
        "source": "user",
        "planned_minutes": minutes,
        "priority_score": score,
        "why_this_task": {"placed_by": "user", "coverage_priority": score},
        "updated_at": _now_iso(),
    }
    inserted = _safe(
        lambda: supabase.table("study_tasks").insert(row).execute().data,
        default=None,
    )
    if not inserted:
        raise BoardError("create_failed", "Couldn't add that task.", 503)

    created = inserted[0]
    ids = [
        t for t in _day_task_ids(supabase, plan_id, user_id, target_date)
        if t != str(created.get("id"))
    ]
    try:
        index = int(position) if position is not None else len(ids)
    except (TypeError, ValueError):
        index = len(ids)
    index = max(0, min(index, len(ids)))
    ids.insert(index, str(created.get("id")))
    _renumber(supabase, plan_id, user_id, target_date, order=ids)

    return _card(_owned_task(supabase, user_id, str(created.get("id"))))


def delete_task(supabase: Any, user_id: str, task_id: str) -> dict[str, Any]:
    """Remove one task the user owns, then compact its day's ordinals."""
    task = _owned_task(supabase, user_id, task_id)
    plan_id = task.get("plan_id")
    origin_date = str(task.get("scheduled_date") or "")

    deleted = _safe(
        lambda: (
            supabase.table("study_tasks")
            .delete()
            .eq("id", task_id)
            .eq("user_id", user_id)
            .execute()
            .data
        ),
        default=None,
    )
    if deleted is None:
        raise BoardError("delete_failed", "Couldn't remove that task.", 503)

    if plan_id and origin_date:
        _renumber(
            supabase,
            plan_id,
            user_id,
            origin_date,
            order=_day_task_ids(supabase, plan_id, user_id, origin_date),
        )
    return {"id": task_id, "deleted": True, "scheduled_date": origin_date or None}
