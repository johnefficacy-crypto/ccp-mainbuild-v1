from __future__ import annotations

from datetime import datetime


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _engaged_qids(responses: list[dict]) -> set[str]:
    """Questions the user DEMONSTRABLY interacted with — answered or marked for
    review. These are observable from the response row and must carry a
    `question.visited` anchor; a fallback among them is a real telemetry gap.
    (`is_visited` is excluded: it is set by answer-save, so it is redundant with
    `selected_option_id` and cannot evidence a visit on its own.)
    """
    return {
        r["question_id"]
        for r in responses
        if r.get("question_id")
        and (r.get("selected_option_id") is not None or r.get("is_marked_for_review"))
    }


def compute_dwell_times(
    responses: list[dict], events: list[dict], submitted_at: str | None
) -> tuple[dict[str, int], list[str], dict[str, int]]:
    warnings: list[str] = []
    by_q: dict[str, int] = {}
    malformed_events = 0
    events_used = 0
    response_qids = [r["question_id"] for r in responses]
    engaged_qids = _engaged_qids(responses)
    if not events:
        warnings.append("mock_attempt_events missing; fallback to responses.time_spent_sec")
        for r in responses:
            by_q[r["question_id"]] = int(r.get("time_spent_sec") or 0)
        return by_q, warnings, {
            "events_malformed": 0,
            "events_used": 0,
            "event_covered_questions": 0,
            "fallback_question_count": len(response_qids),
            # Engaged (answered/marked) questions that fell back — the telemetry
            # gap that matters for the shadow gate (untouched questions excluded).
            "fallback_engaged_question_count": len(engaged_qids),
        }

    sorted_events = []
    for e in events:
        if not e.get("occurred_at"):
            malformed_events += 1
            continue
        sorted_events.append(e)
    sorted_events.sort(key=lambda e: _parse(e["occurred_at"]))
    # Track which questions actually received a visit-event-derived dwell time,
    # so per-question fallback can be detected and reported (it cannot be
    # inferred from len(by_q) once every response qid is setdefault-ed below).
    event_covered_qids: set[str] = set()
    for i, evt in enumerate(sorted_events):
        # PR2b compatibility alias. TODO(PR-integrate follow-up): once PR2b
        # locks a single event naming contract, deprecate + remove this alias.
        if evt.get("event_type") not in {"question.visited", "question_visited"}:
            continue
        qid = (evt.get("payload") or {}).get("question_id") or evt.get("question_id")
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
        event_covered_qids.add(qid)

    # Per-question fallback for any response not covered by a visit event.
    # Compute the fallback set BEFORE setdefault so it is not masked by the
    # fill-in below (the prior len(by_q) < len(responses) check could never
    # trip once every response qid was setdefault-ed, silently hiding fallback).
    fallback_qids = [q for q in response_qids if q not in event_covered_qids]
    for r in responses:
        by_q.setdefault(r["question_id"], int(r.get("time_spent_sec") or 0))

    fallback_engaged_qids = [q for q in engaged_qids if q not in event_covered_qids]
    if fallback_qids:
        warnings.append("partial event coverage; fallback applied per-question")
    if fallback_engaged_qids:
        warnings.append(
            f"engaged-question fallback: {len(fallback_engaged_qids)} answered/marked "
            "question(s) had no visit event"
        )
    if malformed_events:
        warnings.append(f"malformed events dropped: {malformed_events}")
    return by_q, warnings, {
        "events_malformed": malformed_events,
        "events_used": events_used,
        "event_covered_questions": len(event_covered_qids & set(response_qids)),
        "fallback_question_count": len(fallback_qids),
        "fallback_engaged_question_count": len(fallback_engaged_qids),
    }
