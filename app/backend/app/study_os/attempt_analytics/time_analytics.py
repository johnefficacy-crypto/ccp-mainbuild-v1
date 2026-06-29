from __future__ import annotations

from datetime import datetime


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def compute_dwell_times(
    responses: list[dict], events: list[dict], submitted_at: str | None
) -> tuple[dict[str, int], list[str], dict[str, int]]:
    warnings: list[str] = []
    by_q: dict[str, int] = {}
    malformed_events = 0
    events_used = 0
    if not events:
        warnings.append("mock_attempt_events missing; fallback to responses.time_spent_sec")
        for r in responses:
            by_q[r["question_id"]] = int(r.get("time_spent_sec") or 0)
        return by_q, warnings, {"events_malformed": 0, "events_used": 0}

    sorted_events = []
    for e in events:
        if not e.get("occurred_at"):
            malformed_events += 1
            continue
        sorted_events.append(e)
    sorted_events.sort(key=lambda e: _parse(e["occurred_at"]))
    for i, evt in enumerate(sorted_events):
        # PR2b compatibility alias. TODO(PR-integrate follow-up): once PR2b
        # locks a single event naming contract, deprecate + remove this alias.
        if evt.get("event_type") not in {"question.visited", "question_visited"}:
            continue
        qid = evt.get("question_id")
        if not qid:
            malformed_events += 1
            continue
        t0 = _parse(evt["occurred_at"])
        events_used += 1
        end = _parse(submitted_at) if submitted_at else t0
        for nxt in sorted_events[i + 1 :]:
            if nxt.get("event_type") in {"question.visited", "question_visited"}:
                end = _parse(nxt["occurred_at"])
                break
        by_q[qid] = max(0, int((end - t0).total_seconds()))

    for r in responses:
        by_q.setdefault(r["question_id"], int(r.get("time_spent_sec") or 0))
    if len(by_q) < len(responses):
        warnings.append("partial event coverage; fallback applied per-question")
    if malformed_events:
        warnings.append(f"malformed events dropped: {malformed_events}")
    return by_q, warnings, {"events_malformed": malformed_events, "events_used": events_used}
