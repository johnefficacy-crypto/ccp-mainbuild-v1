"""ROADMAP-01 — the aspirant's syllabus roadmap, derived at read time.

Answers "where am I across my syllabus": every topic the user is scoped to for
one exam, grouped subject → macro topic → microtopic, each with a state derived
from evidence that already exists. Nothing here writes; no state is stored.

NODE UNIVERSE (the denominator)
    The user's scoped LOCKED coverage for the exam
    (``planner.load_scoped_coverage_checked`` — elective scoping and phase
    canonicalisation included), plus the macro parents of those topics
    (``topics.parent_topic_id``). Inactive topics are excluded. Nothing outside
    this set appears, even when the user has mastery on it.

    Every read is bounded by that universe: parents are read by id AND the
    coverage subjects; ``study_tasks`` by topic id AND subject id. The mastery
    and audit tables carry no subject column, so they are bounded by the topic
    ids of the (subject-scoped) universe. ``user_topic_mastery.exam_id`` is NOT
    filtered: a topic shared across exams is the same skill, and mastery earned
    through another exam counts.

DEFINITIONS (ROADMAP-01 §2, locked)
    attempts(topic)        COUNT(DISTINCT attempt_id) in user_topic_mastery_audit
    last_practiced(topic)  MAX(user_topic_mastery_audit.at)
    score(topic)           user_topic_mastery.mastery_score
    completed_tasks(topic) study_tasks with that topic_id and status 'completed'

    Macro state   mastered | studied | not_started
    Macro flags   weak, revise (independent booleans)
    Micro state   studied | not_started — no score, attempts or flags.

FAILURE
    Any read that fails raises :class:`RoadmapReadError`; the endpoint answers
    503. A partial tree is never rendered as complete.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from app.common.pagination import paginate
from app.study_os import roadmap_thresholds as T
from app.study_os.planner import load_scoped_coverage_checked

# The study_tasks status value that means done (api/canonical.py TASK_STATES).
TASK_COMPLETED = "completed"

STATE_MASTERED = "mastered"
STATE_STUDIED = "studied"
STATE_NOT_STARTED = "not_started"

# ``.in_()`` with thousands of ids overflows the PostgREST URL.
_IN_CHUNK = 300


class RoadmapReadError(RuntimeError):
    """A read behind the roadmap failed; the tree would be partial."""


@dataclass
class RoadmapInputs:
    """Everything the pure derivation needs, already bounded to the universe."""

    nodes: dict[str, dict[str, Any]]
    coverage_by_topic: dict[str, dict[str, Any]]
    subject_names: dict[str, str]
    mastery_rows: list[dict[str, Any]] = field(default_factory=list)
    audit_rows: list[dict[str, Any]] = field(default_factory=list)
    task_rows: list[dict[str, Any]] = field(default_factory=list)


# ─── loader ─────────────────────────────────────────────────────────────────


def _chunks(items: list[str]) -> list[list[str]]:
    return [items[i : i + _IN_CHUNK] for i in range(0, len(items), _IN_CHUNK)]


def _read_all(build: Callable[[int, int], Any], *, op: str) -> list[dict[str, Any]]:
    """Paginate one read; any failure or prefix raises."""

    def _fetch(a: int, b: int) -> Any:
        try:
            return build(a, b)
        except Exception:  # noqa: BLE001 — classified as a failed page below.
            return None

    walk = paginate(_fetch, operation=op)
    if not walk.complete:
        raise RoadmapReadError(op)
    return walk.rows


def _priority_key(row: dict[str, Any]) -> float:
    value = row.get("comparable_priority")
    return float(value) if isinstance(value, (int, float)) else float("-inf")


def load_roadmap_inputs(supabase: Any, user_id: str, exam_id: str) -> RoadmapInputs:
    """Read the node universe and the user's evidence on it. Raises on any failure."""
    try:
        coverage, ok = load_scoped_coverage_checked(supabase, user_id, exam_id)
    except Exception as exc:  # noqa: BLE001
        raise RoadmapReadError("coverage") from exc
    if not ok:
        raise RoadmapReadError("coverage")

    # One coverage row per topic: a topic can appear under more than one phase.
    # Keep the highest-priority row so priority, band and high-yield come from
    # the same row rather than being mixed across rows.
    coverage_by_topic: dict[str, dict[str, Any]] = {}
    for row in coverage:
        tid = row.get("topic_id")
        if not tid:
            continue
        tid = str(tid)
        held = coverage_by_topic.get(tid)
        if held is None or _priority_key(row) > _priority_key(held):
            coverage_by_topic[tid] = row

    nodes: dict[str, dict[str, Any]] = {}
    subject_names: dict[str, str] = {}
    for tid, row in coverage_by_topic.items():
        sid = row.get("subject_id")
        if not sid:
            continue
        nodes[tid] = {
            "id": tid,
            "name": row.get("topic_name"),
            "subject_id": str(sid),
            "parent_topic_id": str(row["parent_topic_id"]) if row.get("parent_topic_id") else None,
            "level": row.get("topic_level"),
        }
        subject_names.setdefault(str(sid), row.get("subject_name") or "")

    subject_ids = sorted(subject_names)
    parent_ids = sorted(
        {n["parent_topic_id"] for n in nodes.values() if n["parent_topic_id"]} - set(nodes)
    )
    for chunk in _chunks(parent_ids):
        rows = _read_all(
            lambda a, b, ids=chunk: (
                supabase.table("topics")
                .select("id, name, subject_id, parent_topic_id, level, is_active")
                .in_("id", ids)
                .in_("subject_id", subject_ids)
                .order("id")
                .range(a, b)
                .execute()
            ),
            op="roadmap.parent_topics",
        )
        for t in rows:
            if t.get("is_active") is False or not t.get("id"):
                continue
            nodes[str(t["id"])] = {
                "id": str(t["id"]),
                "name": t.get("name"),
                "subject_id": str(t.get("subject_id")),
                "parent_topic_id": str(t["parent_topic_id"]) if t.get("parent_topic_id") else None,
                "level": t.get("level"),
            }

    topic_ids = sorted(nodes)
    mastery_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    task_rows: list[dict[str, Any]] = []
    for chunk in _chunks(topic_ids):
        mastery_rows += _read_all(
            lambda a, b, ids=chunk: (
                supabase.table("user_topic_mastery")
                .select("id, topic_id, exam_id, mastery_score, updated_at")
                .eq("user_id", user_id)
                .in_("topic_id", ids)
                .order("id")
                .range(a, b)
                .execute()
            ),
            op="roadmap.user_topic_mastery",
        )
        audit_rows += _read_all(
            lambda a, b, ids=chunk: (
                supabase.table("user_topic_mastery_audit")
                .select("id, topic_id, attempt_id, after_mastery_db, at")
                .eq("user_id", user_id)
                .in_("topic_id", ids)
                .order("id")
                .range(a, b)
                .execute()
            ),
            op="roadmap.user_topic_mastery_audit",
        )
        task_rows += _read_all(
            lambda a, b, ids=chunk: (
                supabase.table("study_tasks")
                .select("id, topic_id, subject_id, status")
                .eq("user_id", user_id)
                .eq("status", TASK_COMPLETED)
                .in_("topic_id", ids)
                .in_("subject_id", subject_ids)
                .order("id")
                .range(a, b)
                .execute()
            ),
            op="roadmap.study_tasks",
        )

    return RoadmapInputs(
        nodes=nodes,
        coverage_by_topic=coverage_by_topic,
        subject_names=subject_names,
        mastery_rows=mastery_rows,
        audit_rows=audit_rows,
        task_rows=task_rows,
    )


# ─── pure derivation ────────────────────────────────────────────────────────


def _parse_ts(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _num(value: Any) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def macro_state(score: float | None, attempts: int, completed_tasks: int) -> str:
    if score is not None and score >= T.MASTERED_AT and attempts >= T.MIN_ATTEMPTS:
        return STATE_MASTERED
    if completed_tasks >= 1 or attempts >= 1:
        return STATE_STUDIED
    return STATE_NOT_STARTED


def is_weak(score: float | None, attempts: int) -> bool:
    return score is not None and score < T.WEAK_BELOW and attempts >= T.MIN_ATTEMPTS


def is_revise(state: str, last_practiced: datetime | None, now: datetime) -> bool:
    if state != STATE_MASTERED or last_practiced is None:
        return False
    return (now - last_practiced) > timedelta(days=T.REVISE_AFTER_DAYS)


def micro_state(completed_tasks: int) -> str:
    return STATE_STUDIED if completed_tasks >= 1 else STATE_NOT_STARTED


def _latest_mastery(rows: list[dict[str, Any]]) -> dict[str, float]:
    """One score per topic. A topic can hold a row per exam/phase; the most
    recently updated row is the current reading of that skill."""
    best: dict[str, tuple[datetime, str, float]] = {}
    floor = datetime.min.replace(tzinfo=timezone.utc)
    for r in rows:
        tid, score = r.get("topic_id"), _num(r.get("mastery_score"))
        if not tid or score is None:
            continue
        key = (_parse_ts(r.get("updated_at")) or floor, str(r.get("id") or ""), score)
        if str(tid) not in best or key[:2] > best[str(tid)][:2]:
            best[str(tid)] = key
    return {tid: v[2] for tid, v in best.items()}


def _audit_stats(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        if r.get("topic_id"):
            grouped.setdefault(str(r["topic_id"]), []).append(r)
    out: dict[str, dict[str, Any]] = {}
    for tid, items in grouped.items():
        # COUNT(DISTINCT attempt_id): NULL attempt ids are not attempts.
        attempts = len({str(r["attempt_id"]) for r in items if r.get("attempt_id")})
        dated = sorted(
            ((ts, r) for r in items if (ts := _parse_ts(r.get("at"))) is not None),
            key=lambda p: p[0],
        )
        history = [
            {"at": ts.isoformat(), "score": _num(r.get("after_mastery_db"))}
            for ts, r in dated[-T.HISTORY_POINTS:]
        ]
        out[tid] = {
            "attempts": attempts,
            "last_practiced": dated[-1][0] if dated else None,
            "history": history,
        }
    return out


def _root_of(tid: str, nodes: dict[str, dict[str, Any]]) -> str:
    """The top-most ancestor of ``tid`` still inside the universe."""
    seen = {tid}
    cur = tid
    while True:
        parent = nodes[cur].get("parent_topic_id")
        if not parent or parent not in nodes or parent in seen:
            return cur
        seen.add(parent)
        cur = parent


def derive_roadmap(inputs: RoadmapInputs, *, now: datetime) -> list[dict[str, Any]]:
    """Build the subject → macro → micro tree. Pure: no reads, no clock."""
    nodes = inputs.nodes
    cov = inputs.coverage_by_topic
    scores = _latest_mastery(inputs.mastery_rows)
    stats = _audit_stats(inputs.audit_rows)
    tasks: dict[str, int] = {}
    for r in inputs.task_rows:
        if r.get("topic_id"):
            tasks[str(r["topic_id"])] = tasks.get(str(r["topic_id"]), 0) + 1

    # A node is a macro when its parent is outside the universe; everything
    # below it (at any depth) is listed as one of its micros.
    micros_of: dict[str, list[str]] = {}
    macros: list[str] = []
    for tid in nodes:
        root = _root_of(tid, nodes)
        if root == tid:
            macros.append(tid)
        else:
            micros_of.setdefault(root, []).append(tid)

    def priority(tid: str) -> float:
        row = cov.get(tid)
        return _priority_key(row) if row else float("-inf")

    def macro_priority(tid: str) -> float:
        return max([priority(tid)] + [priority(m) for m in micros_of.get(tid, [])])

    def order(ids: list[str], key: Callable[[str], float]) -> list[str]:
        return sorted(ids, key=lambda t: (-key(t), (nodes[t].get("name") or "").casefold(), t))

    subjects: dict[str, list[dict[str, Any]]] = {}
    for tid in order(macros, macro_priority):
        node = nodes[tid]
        s = stats.get(tid, {})
        attempts = int(s.get("attempts", 0))
        last_practiced = s.get("last_practiced")
        completed = tasks.get(tid, 0)

        # Score source: own row → attempts-weighted mean of child rows → null.
        score = scores.get(tid)
        if score is None:
            weighted = [
                (scores[m], stats.get(m, {}).get("attempts", 0))
                for m in micros_of.get(tid, [])
                if m in scores
            ]
            weight = sum(w for _, w in weighted)
            if weight > 0:
                score = sum(v * w for v, w in weighted) / weight

        state = macro_state(score, attempts, completed)
        subjects.setdefault(node["subject_id"], []).append(
            {
                "topic_id": tid,
                "name": node.get("name"),
                "state": state,
                "score": round(score, 2) if score is not None else None,
                "attempts": attempts,
                "last_practiced": last_practiced.isoformat() if last_practiced else None,
                "weak": is_weak(score, attempts),
                "revise": is_revise(state, last_practiced, now),
                "history": list(s.get("history", [])),
                "completed_tasks": completed,
                "micros": [
                    {
                        "topic_id": m,
                        "name": nodes[m].get("name"),
                        "state": micro_state(tasks.get(m, 0)),
                        "completed_tasks": tasks.get(m, 0),
                        "is_high_yield": bool((cov.get(m) or {}).get("is_high_yield")),
                        "predictability_band": (cov.get(m) or {}).get("predictability_band"),
                    }
                    for m in order(micros_of.get(tid, []), priority)
                ],
            }
        )

    out: list[dict[str, Any]] = []
    for sid, macro_rows in subjects.items():
        counts = {STATE_NOT_STARTED: 0, STATE_STUDIED: 0, STATE_MASTERED: 0}
        for m in macro_rows:
            counts[m["state"]] += 1
        total = len(macro_rows)
        out.append(
            {
                "subject_id": sid,
                "name": inputs.subject_names.get(sid) or "",
                "rollup": {
                    **counts,
                    "weak_count": sum(1 for m in macro_rows if m["weak"]),
                    "revise_count": sum(1 for m in macro_rows if m["revise"]),
                    # Percentage (0-100) of macro topics mastered.
                    "pct_mastered": round(100.0 * counts[STATE_MASTERED] / total, 1) if total else 0.0,
                },
                "macros": macro_rows,
            }
        )
    out.sort(key=lambda s: (s["name"].casefold(), s["subject_id"]))
    return out


def thresholds_payload() -> dict[str, Any]:
    return {
        "weak_below": T.WEAK_BELOW,
        "mastered_at": T.MASTERED_AT,
        "min_attempts": T.MIN_ATTEMPTS,
        "revise_after_days": T.REVISE_AFTER_DAYS,
    }


def build_roadmap(supabase: Any, user_id: str, exam_id: str, *, now: datetime | None = None) -> dict[str, Any]:
    """Loader + derivation. Raises :class:`RoadmapReadError` on any failed read."""
    now = now or datetime.now(timezone.utc)
    inputs = load_roadmap_inputs(supabase, user_id, exam_id)
    return {
        "exam_id": exam_id,
        "generated_at": now.isoformat(),
        "thresholds": thresholds_payload(),
        "subjects": derive_roadmap(inputs, now=now),
    }
