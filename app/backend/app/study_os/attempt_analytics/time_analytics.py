from __future__ import annotations

from datetime import datetime


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def compute_dwell_times(responses: list[dict], events: list[dict], submitted_at: str | None) -> tuple[dict[str, int], list[str]]:
    warnings: list[str] = []
    by_q: dict[str, int] = {}
    if not events:
        warnings.append("mock_attempt_events missing; fallback to responses.time_spent_sec")
        for r in responses:
            by_q[r["question_id"]] = int(r.get("time_spent_sec") or 0)
        return by_q, warnings

    sorted_events = sorted(events, key=lambda e: _parse(e["created_at"]))
    for i, evt in enumerate(sorted_events):
        if evt.get("event_type") != "question.visited":
            continue
        qid = evt.get("question_id")
        if not qid:
            continue
        t0 = _parse(evt["created_at"])
        end = _parse(submitted_at) if submitted_at else t0
        for nxt in sorted_events[i + 1 :]:
            if nxt.get("event_type") == "question.visited":
                end = _parse(nxt["created_at"])
                break
        by_q[qid] = max(0, int((end - t0).total_seconds()))

    for r in responses:
        by_q.setdefault(r["question_id"], int(r.get("time_spent_sec") or 0))
    if len(by_q) < len(responses):
        warnings.append("partial event coverage; fallback applied per-question")
    return by_q, warnings
