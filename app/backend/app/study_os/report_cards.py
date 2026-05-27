from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from app.study_os import weekly_review as weekly_review_service


def _safe(fn, default):
    try:
        return fn()
    except Exception:
        return default


def _ratio(n: int, d: int) -> float | None:
    if not d:
        return None
    return round(float(n) / float(d), 3)


def _period_bounds(period: str, anchor: date) -> tuple[date, date]:
    if period == "daily":
        return anchor, anchor
    if period == "weekly":
        start = anchor - timedelta(days=anchor.weekday())
        return start, start + timedelta(days=6)
    if period == "monthly":
        start = anchor.replace(day=1)
        if start.month == 12:
            nxt = date(start.year + 1, 1, 1)
        else:
            nxt = date(start.year, start.month + 1, 1)
        return start, nxt - timedelta(days=1)
    raise ValueError("period must be daily|weekly|monthly")


def _score_labels(score: float | None) -> str:
    if score is None:
        return "No evidence"
    pct = score * 100
    if pct >= 90:
        return "Excellent adherence"
    if pct >= 75:
        return "On track"
    if pct >= 60:
        return "Recoverable gap"
    if pct >= 40:
        return "Needs plan correction"
    return "Plan mismatch"


def _mock_label(m: dict[str, Any]) -> str:
    return str(m.get("test_name") or m.get("title") or "Mock test")


def _task_label(t: dict[str, Any]) -> str:
    title = t.get("title") or t.get("topic") or t.get("subject")
    return str(title or "Task")


def _build_highlights(
    *,
    scores: dict[str, Any],
    completed_tasks: int,
    planned_tasks: int,
    active_days: int,
    planned_days: int,
    mocks_taken: int,
    mocks_reviewed: int,
    revision_done: int,
    revision_total: int,
    corr_completed: int,
    corr_created: int,
    focus_minutes: int,
    planned_minutes: int,
) -> list[dict[str, Any]]:
    """Top 3 wins for the period, in deterministic priority order.

    Only fires a candidate when the underlying metric crosses a fixed
    threshold computed from existing scores. Never invents fact rows.
    """
    out: list[dict[str, Any]] = []
    adherence = scores.get("plan_adherence_score")
    if planned_tasks and adherence is not None and adherence >= 0.7:
        out.append({
            "kind": "task_completion",
            "label": f"Completed {completed_tasks} of {planned_tasks} planned tasks ({int(adherence * 100)}%).",
        })
    consistency = scores.get("consistency_score")
    if planned_days and consistency is not None and consistency >= 0.8:
        out.append({
            "kind": "consistency",
            "label": f"Active on {active_days} of {planned_days} planned days.",
        })
    if planned_minutes and focus_minutes >= planned_minutes and focus_minutes > 0:
        out.append({
            "kind": "focus_minutes",
            "label": f"Focus time {focus_minutes // 60}h beat the planned {planned_minutes // 60}h.",
        })
    mock_review = scores.get("mock_review_score")
    if mocks_taken and mock_review is not None and mock_review >= 0.8:
        out.append({
            "kind": "mock_review",
            "label": f"Reviewed {mocks_reviewed} of {mocks_taken} mocks.",
        })
    revision = scores.get("revision_completion_score")
    if revision_total and revision is not None and revision >= 0.8:
        out.append({
            "kind": "revision",
            "label": f"Closed {revision_done} of {revision_total} revision blocks.",
        })
    corr = scores.get("correction_completion_score")
    if corr_created and corr is not None and corr >= 0.7:
        out.append({
            "kind": "corrections",
            "label": f"Closed {corr_completed} of {corr_created} correction tasks.",
        })
    return out[:3]


def _build_corrections(
    *,
    tasks: list[dict[str, Any]],
    mocks: list[dict[str, Any]],
    corrections: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Top 3 misses with linkable task ids.

    Surfaces missed tasks, then skipped tasks, then unreviewed mocks, then
    open correction tasks, in that fixed order. Each entry carries the
    underlying row's id so the UI can link straight to it.
    """
    out: list[dict[str, Any]] = []
    for t in tasks:
        if t.get("status") == "missed" and t.get("id"):
            out.append({
                "kind": "missed_task",
                "label": f"Missed: {_task_label(t)}.",
                "task_id": t.get("id"),
            })
            if len(out) >= 3:
                return out
    for t in tasks:
        if t.get("status") == "skipped" and t.get("id"):
            out.append({
                "kind": "skipped_task",
                "label": f"Skipped: {_task_label(t)}.",
                "task_id": t.get("id"),
            })
            if len(out) >= 3:
                return out
    for m in mocks:
        state = (m.get("review_state") or "").lower()
        if state in {"", "scheduled", "unreviewed"} and m.get("id"):
            out.append({
                "kind": "mock_unreviewed",
                "label": f"Pending review: {_mock_label(m)}.",
                "mock_id": m.get("id"),
            })
            if len(out) >= 3:
                return out
    for c in corrections:
        if (c.get("status") or "").lower() not in {"completed", "dismissed"} and c.get("id"):
            label = c.get("topic") or "correction task"
            out.append({
                "kind": "correction_open",
                "label": f"Open correction: {label}.",
                "correction_id": c.get("id"),
                "mock_id": c.get("mock_test_id"),
            })
            if len(out) >= 3:
                return out
    return out[:3]


def _build_next_actions(
    *,
    tasks: list[dict[str, Any]],
    mocks: list[dict[str, Any]],
    corrections: list[dict[str, Any]],
    revision_total: int,
    revision_done: int,
) -> list[dict[str, Any]]:
    """Up to 3 concrete suggestions, all derivable from existing rows.

    Fixed evaluation order so a given input always produces the same output.
    """
    out: list[dict[str, Any]] = []

    # Suggestion 1: review the oldest unreviewed mock.
    unreviewed_mock = next(
        (
            m for m in sorted(
                mocks, key=lambda r: (r.get("attempted_at") or "")
            )
            if (m.get("review_state") or "").lower() in {"", "scheduled", "unreviewed"}
            and m.get("id")
        ),
        None,
    )
    if unreviewed_mock:
        out.append({
            "kind": "review_mock",
            "label": f"Review pending mock: {_mock_label(unreviewed_mock)}.",
            "mock_id": unreviewed_mock.get("id"),
        })

    # Suggestion 2: clear the backlog topic with the most carried-forward tasks.
    backlog_by_topic: dict[str, int] = {}
    for t in tasks:
        if t.get("status") == "carried_forward":
            key = t.get("topic") or t.get("subject") or "Backlog"
            backlog_by_topic[str(key)] = backlog_by_topic.get(str(key), 0) + 1
    if backlog_by_topic:
        topic, count = max(
            backlog_by_topic.items(),
            key=lambda kv: (kv[1], kv[0]),  # tie-break by topic name for determinism
        )
        out.append({
            "kind": "clear_backlog",
            "label": f"Clear backlog topic: {topic} ({count} carried-forward).",
            "topic": topic,
        })

    # Suggestion 3: resume focus on the subject with the most missed tasks.
    missed_by_subject: dict[str, int] = {}
    for t in tasks:
        if t.get("status") == "missed":
            key = t.get("subject") or t.get("topic") or "Plan"
            missed_by_subject[str(key)] = missed_by_subject.get(str(key), 0) + 1
    if missed_by_subject:
        subject, count = max(
            missed_by_subject.items(),
            key=lambda kv: (kv[1], kv[0]),
        )
        out.append({
            "kind": "resume_subject",
            "label": f"Resume focus on {subject} ({count} missed task(s)).",
            "subject": subject,
        })

    if len(out) < 3:
        open_corr = next(
            (
                c for c in corrections
                if (c.get("status") or "").lower() not in {"completed", "dismissed"}
                and c.get("id")
            ),
            None,
        )
        if open_corr:
            label = open_corr.get("topic") or "correction task"
            out.append({
                "kind": "finish_correction",
                "label": f"Finish open correction: {label}.",
                "correction_id": open_corr.get("id"),
                "mock_id": open_corr.get("mock_test_id"),
            })

    if len(out) < 3 and revision_total and revision_done < revision_total:
        remaining = revision_total - revision_done
        out.append({
            "kind": "finish_revision",
            "label": f"Finish {remaining} remaining revision block(s).",
        })

    return out[:3]


_HIGH_YIELD_MASTERED_THRESHOLD = 75.0  # matches `revision_due` in /api/study/topics


def _build_high_yield_coverage(
    supabase: Any, user_id: str
) -> dict[str, Any]:
    """`{covered, total, exam_id, mastered_threshold}` for the target exam.

    Counts locked high-yield ``exam_topic_coverage`` rows for the user's
    target exam, then counts how many of those topics the user has a
    mastery score ≥ 75 for in ``user_topic_mastery`` (the same threshold
    `/api/study/topics` already uses to mark a topic ``revision_due``).
    Returns zeros + ``trust_status='preview'`` when no target exam or no
    locked coverage exists — never raises.
    """
    try:
        from app.study_os.planner import (
            _load_locked_coverage,
            _load_user_signals,
            _resolve_target_exam,
        )
    except Exception:
        return {
            "covered": 0,
            "total": 0,
            "exam_id": None,
            "mastered_threshold": _HIGH_YIELD_MASTERED_THRESHOLD,
            "trust_status": "preview",
        }
    target = _safe(lambda: _resolve_target_exam(supabase, user_id), None)
    if not target or not target.get("id"):
        return {
            "covered": 0,
            "total": 0,
            "exam_id": None,
            "mastered_threshold": _HIGH_YIELD_MASTERED_THRESHOLD,
            "trust_status": "preview",
        }
    exam_id = target["id"]
    coverage = _safe(lambda: _load_locked_coverage(supabase, exam_id), []) or []
    high_yield = [c for c in coverage if c.get("is_high_yield")]
    total = len(high_yield)
    if total == 0:
        return {
            "covered": 0,
            "total": 0,
            "exam_id": exam_id,
            "mastered_threshold": _HIGH_YIELD_MASTERED_THRESHOLD,
            "trust_status": "locked",
        }
    mastery, _ = _safe(lambda: _load_user_signals(supabase, user_id, exam_id), ({}, set()))
    covered = sum(
        1
        for c in high_yield
        if (mastery.get(c.get("topic_id")) or 0) >= _HIGH_YIELD_MASTERED_THRESHOLD
    )
    return {
        "covered": covered,
        "total": total,
        "exam_id": exam_id,
        "mastered_threshold": _HIGH_YIELD_MASTERED_THRESHOLD,
        "trust_status": "locked",
    }


def _age_bucket(age_days: int) -> str:
    if age_days <= 3:
        return "0-3d"
    if age_days <= 7:
        return "4-7d"
    if age_days <= 14:
        return "8-14d"
    return "15d+"


_BACKLOG_BUCKETS = ["0-3d", "4-7d", "8-14d", "15d+"]
_BACKLOG_OPEN_STATES = {"planned", "in_progress", "carried_forward"}


def _build_backlog_heatmap(
    supabase: Any, user_id: str, anchor: date
) -> dict[str, Any]:
    """`{subjects:[{subject, total, buckets:{...}}], buckets:[...], total}`.

    Pulls every open study_task whose ``scheduled_date`` ≤ ``anchor`` (the
    same backlog definition `weekly_review._backlog_count` already uses)
    and bins each row by subject + age bucket. Subjects are sorted by
    backlog count desc with a deterministic alpha tie-break. Returns the
    canonical bucket order via ``buckets`` so the frontend can render the
    grid columns without hard-coding the list itself.
    """
    rows = _safe(
        lambda: (
            supabase.table("study_tasks")
            .select("status, subject, scheduled_date")
            .eq("user_id", user_id)
            .lte("scheduled_date", anchor.isoformat())
            .limit(5000)
            .execute()
            .data
        ),
        default=[],
    ) or []
    by_subject: dict[str, dict[str, int]] = {}
    grand_total = 0
    for r in rows:
        if r.get("status") not in _BACKLOG_OPEN_STATES:
            continue
        scheduled = r.get("scheduled_date") or ""
        try:
            sd = date.fromisoformat(str(scheduled)[:10])
        except ValueError:
            continue
        age = (anchor - sd).days
        if age < 0:
            # Future-dated open tasks are not yet backlog.
            continue
        bucket = _age_bucket(age)
        subject = (r.get("subject") or "Unassigned").strip() or "Unassigned"
        slot = by_subject.setdefault(
            subject, {b: 0 for b in _BACKLOG_BUCKETS}
        )
        slot[bucket] += 1
        grand_total += 1

    items = []
    for subject, buckets in by_subject.items():
        total = sum(buckets.values())
        items.append({
            "subject": subject,
            "total": total,
            "buckets": buckets,
        })
    items.sort(key=lambda r: (-r["total"], r["subject"]))
    return {
        "buckets": list(_BACKLOG_BUCKETS),
        "subjects": items,
        "total": grand_total,
    }


def _compute(supabase: Any, user_id: str, period: str, anchor: date) -> dict[str, Any]:
    start, end = _period_bounds(period, anchor)
    tasks = _safe(lambda: supabase.table("study_tasks").select("id, title, subject, topic, status, task_type, scheduled_date, planned_minutes").eq("user_id", user_id).gte("scheduled_date", start.isoformat()).lte("scheduled_date", end.isoformat()).execute().data, []) or []
    sessions = _safe(lambda: supabase.table("study_sessions").select("duration_mins, started_at").eq("user_id", user_id).gte("started_at", start.isoformat()).lte("started_at", (end + timedelta(days=1)).isoformat()).execute().data, []) or []
    mocks = _safe(lambda: supabase.table("mock_tests").select("id, test_name, title, attempted_at, review_state, trust_label").eq("user_id", user_id).gte("attempted_at", start.isoformat()).lte("attempted_at", (end + timedelta(days=1)).isoformat()).execute().data, []) or []
    corrections = _safe(lambda: supabase.table("mock_correction_tasks").select("id, status, created_at, mock_test_id, topic").eq("user_id", user_id).gte("created_at", start.isoformat()).lte("created_at", (end + timedelta(days=1)).isoformat()).execute().data, []) or []

    planned_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t.get("status") == "completed")
    missed_tasks = sum(1 for t in tasks if t.get("status") == "missed")
    skipped_tasks = sum(1 for t in tasks if t.get("status") == "skipped")
    carried = sum(1 for t in tasks if t.get("status") == "carried_forward")
    planned_minutes = sum(int(t.get("planned_minutes") or 0) for t in tasks)
    completed_minutes = sum(int(t.get("planned_minutes") or 0) for t in tasks if t.get("status") == "completed")
    focus_minutes = sum(int(s.get("duration_mins") or 0) for s in sessions)
    active_days = len({(s.get("started_at") or "")[:10] for s in sessions if s.get("started_at")})
    planned_days = len({str(t.get("scheduled_date")) for t in tasks if t.get("scheduled_date")})
    revision_total = sum(1 for t in tasks if t.get("task_type") == "revision")
    revision_done = sum(1 for t in tasks if t.get("task_type") == "revision" and t.get("status") == "completed")

    mocks_taken = len(mocks)
    mocks_reviewed = sum(1 for m in mocks if (m.get("review_state") or "") in {"reviewed", "correction_drafted"})
    corr_created = len(corrections)
    corr_completed = sum(1 for c in corrections if c.get("status") == "completed")

    scores = {
        "plan_adherence_score": _ratio(completed_tasks, planned_tasks),
        "plan_completion_score": _ratio(completed_minutes, planned_minutes),
        "focus_adherence_score": _ratio(focus_minutes, planned_minutes),
        "consistency_score": _ratio(active_days, planned_days),
        "backlog_delta": carried,
        "revision_completion_score": _ratio(revision_done, revision_total),
        "mock_review_score": _ratio(mocks_reviewed, mocks_taken),
        "correction_completion_score": _ratio(corr_completed, corr_created),
    }

    highlights = _build_highlights(
        scores=scores,
        completed_tasks=completed_tasks,
        planned_tasks=planned_tasks,
        active_days=active_days,
        planned_days=planned_days,
        mocks_taken=mocks_taken,
        mocks_reviewed=mocks_reviewed,
        revision_done=revision_done,
        revision_total=revision_total,
        corr_completed=corr_completed,
        corr_created=corr_created,
        focus_minutes=focus_minutes,
        planned_minutes=planned_minutes,
    )
    corrections_items = _build_corrections(tasks=tasks, mocks=mocks, corrections=corrections)
    next_actions = _build_next_actions(
        tasks=tasks,
        mocks=mocks,
        corrections=corrections,
        revision_total=revision_total,
        revision_done=revision_done,
    )
    high_yield_coverage = _build_high_yield_coverage(supabase, user_id)
    backlog_heatmap = _build_backlog_heatmap(supabase, user_id, end)

    payload = {
        "user_id": user_id,
        "period_type": period,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "planned_tasks": planned_tasks,
        "completed_tasks": completed_tasks,
        "missed_tasks": missed_tasks,
        "skipped_tasks": skipped_tasks,
        "carried_forward_tasks": carried,
        "planned_minutes": planned_minutes,
        "completed_minutes": completed_minutes,
        "focus_minutes": focus_minutes,
        "active_study_days": active_days,
        "planned_study_days": planned_days,
        "mocks_taken": mocks_taken,
        "mocks_reviewed": mocks_reviewed,
        "correction_tasks_created": corr_created,
        "correction_tasks_completed": corr_completed,
        "scores": {
            **scores,
            "label": _score_labels(scores.get("plan_adherence_score")),
        },
        "highlights": highlights,
        "corrections": corrections_items,
        "next_actions": next_actions,
        "evidence_summary": {
            "source": "platform_tracked",
            "mock_score_block": {
                "mocks_taken": mocks_taken,
                "mocks_reviewed": mocks_reviewed,
                "trust_label": "platform_verified",
            },
        },
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }
    # high_yield_coverage + backlog_heatmap are not columns on
    # study_report_cards (migration 100) — they reflect current mastery /
    # backlog state, not a frozen snapshot, so we compute them fresh on
    # every read and merge them into the response without persisting.
    _safe(lambda: supabase.table("study_report_cards").upsert(payload, on_conflict="user_id,period_type,period_start").execute(), None)  # safe-write-ok: computed fresh on every read; persistence is best-effort caching
    row = _safe(lambda: supabase.table("study_report_cards").select("*").eq("user_id", user_id).eq("period_type", period).eq("period_start", start.isoformat()).limit(1).execute().data, [])
    persisted = (row or [payload])[0]
    persisted["high_yield_coverage"] = high_yield_coverage
    persisted["backlog_heatmap"] = backlog_heatmap
    return persisted


def get_report_card(supabase: Any, user_id: str, period: str, anchor: date) -> dict[str, Any]:
    start, _ = _period_bounds(period, anchor)
    row = _safe(lambda: supabase.table("study_report_cards").select("*").eq("user_id", user_id).eq("period_type", period).eq("period_start", start.isoformat()).limit(1).execute().data, [])
    if row:
        out = dict(row[0])
        # high_yield_coverage + backlog_heatmap are recomputed live so the
        # values reflect the user's *current* mastery + backlog, not the
        # frozen state from when the report card row was first persisted.
        out["high_yield_coverage"] = _build_high_yield_coverage(supabase, user_id)
        _, period_end = _period_bounds(period, anchor)
        out["backlog_heatmap"] = _build_backlog_heatmap(supabase, user_id, period_end)
        return out
    if period == "daily" and start == datetime.now(timezone.utc).date():
        return _compute(supabase, user_id, period, anchor)
    return _compute(supabase, user_id, period, anchor)


def compute_report_card(supabase: Any, user_id: str, period: str, anchor: date) -> dict[str, Any]:
    if period == "weekly":
        weekly_review_service.compute_weekly_review(supabase, user_id, anchor - timedelta(days=anchor.weekday()))
    return _compute(supabase, user_id, period, anchor)


def history(supabase: Any, user_id: str, period: str, limit: int = 12) -> list[dict[str, Any]]:
    rows = _safe(lambda: supabase.table("study_report_cards").select("*").eq("user_id", user_id).eq("period_type", period).order("period_start", desc=True).limit(limit).execute().data, [])
    return rows or []
