"""Improvement Lab — personalized learner strategy feeds (GQR-S6).

Contract: docs/architecture/solution-strategies-improvement-lab.md §10.3 + §11.

A BOUNDED, owner-scoped projection over the learner's SUBMITTED mock-attempt
history:

  recent submitted attempts (owner-scoped, bounded, newest first)
    → their response questions (bounded)
      → the verified-only Solution Strategy set for a DETERMINISTIC recent-first
        question window (LIVE, via the shared aggregator — never a full dump)
        → per-strategy evidence (times_seen / wrong / correct / last_seen /
          recent source questions), strongest relevance across links
          → ranked wrong-associated and recent first, then relevance, then name.

Failure semantics (checkpost #999 F1): the feed's OWN reads (attempts, responses)
do NOT fail soft — a database failure PROPAGATES so the endpoint returns a non-2xx
and the client shows its error state, rather than disguising an outage as "no
history". A genuine empty history (no attempts / no verified linked content) is a
normal ``[]`` (HTTP 200). The verified-only strategy projection inherits the shared
aggregator's per-source fail-soft (that fail-soft is the review-path contract §11.7,
not a licence to hide a feed-read failure).

Other guardrails: never reads governed strategy tables directly; every read is
owner-scoped and submitted-only; reads are bounded; content is a live verified-only
projection (withdrawn/inactive strategies vanish without touching history); only the
learner-safe DTO + aggregate evidence leave the server (governance stripped by
construction in the projector). No saved-strategy table, no planner writes, no
target-solve-time inference.
"""
from __future__ import annotations

import logging
from typing import Any

from app.study_os import solution_strategies

logger = logging.getLogger("career_copilot.study_os.improvement_lab")

# Bounded reads (contract §10.3 step 1-2, §11.3) — no unbounded scan, no full dump.
_MAX_ATTEMPTS = 30
_MAX_RESPONSES = 8000
_MAX_QUESTIONS = 500
_MAX_ITEMS = 50
_MAX_SOURCE_QUESTIONS = 5

_RELEVANCE_RANK = {"primary": 0, "secondary": 1, "related": 2}


def build_feed(supabase: Any, user_id: str | None, subject_family: str) -> list[dict]:
    """Return the ranked, evidence-annotated learner strategy feed for one subject.

    ``subject_family`` is ``"quant"`` or ``"reasoning"``. Returns ``[]`` for an
    unknown user or a genuinely empty history. RAISES on a database read failure of
    the feed's own reads (so the caller surfaces an error, not a fake-empty feed).
    """
    if not user_id:
        return []

    # 1. Recent SUBMITTED attempts owned by the caller — newest first, bounded.
    #    A read failure propagates (see module docstring / checkpost #999 F1).
    attempts = (
        supabase.table("mock_attempts")
        .select("id,submitted_at")
        .eq("user_id", user_id)
        .eq("status", "submitted")
        .order("submitted_at", desc=True)
        .limit(_MAX_ATTEMPTS)
        .execute()
        .data
        or []
    )
    submitted_by_attempt = {
        a["id"]: a.get("submitted_at") for a in attempts if isinstance(a, dict) and a.get("id")
    }
    if not submitted_by_attempt:
        return []

    # 2. Responses across those attempts (bounded), for per-question evidence.
    responses = (
        supabase.table("mock_attempt_responses")
        .select("attempt_id,question_id,is_correct")
        .in_("attempt_id", list(submitted_by_attempt))
        .limit(_MAX_RESPONSES)
        .execute()
        .data
        or []
    )
    if len(responses) >= _MAX_RESPONSES:
        # No silent cap: if the response window is saturated, say so.
        logger.warning(
            "improvement_lab response cap hit user=%s cap=%s — window may be partial",
            user_id, _MAX_RESPONSES,
        )

    q_ev: dict[str, dict] = {}
    for r in responses:
        if not isinstance(r, dict):
            continue
        qid = r.get("question_id")
        if not qid:
            continue
        ev = q_ev.setdefault(qid, {"seen": 0, "wrong": 0, "correct": 0, "last_seen_at": None})
        ev["seen"] += 1
        if r.get("is_correct") is True:
            ev["correct"] += 1
        elif r.get("is_correct") is False:
            ev["wrong"] += 1
        seen_at = submitted_by_attempt.get(r.get("attempt_id"))
        if seen_at and (ev["last_seen_at"] is None or seen_at > ev["last_seen_at"]):
            ev["last_seen_at"] = seen_at
    if not q_ev:
        return []

    # DETERMINISTIC recent-first question window (checkpost #999 F2): the bounded
    # set is the most-recently-seen questions, tie-broken by id — never an
    # arbitrary database row order.
    ordered_q = sorted(q_ev)  # id asc (stable tie-break)
    ordered_q.sort(key=lambda qid: q_ev[qid]["last_seen_at"] or "", reverse=True)  # recent first
    question_ids = ordered_q[:_MAX_QUESTIONS]

    # 3. Verified-only LIVE strategies for that window, via the shared aggregator
    #    (governance stripped by construction; the aggregator is per-source fail-soft).
    by_q = solution_strategies.strategies_for_questions(supabase, question_ids)

    # 4/5. Aggregate evidence per strategy of the requested subject.
    acc: dict[str, dict] = {}
    for qid in question_ids:
        ev = q_ev.get(qid)
        if ev is None:
            continue
        for dto in by_q.get(qid, []):
            if not isinstance(dto, dict) or dto.get("subject_family") != subject_family:
                continue
            sid = dto.get("id")
            if not sid:
                continue
            a = acc.get(sid)
            if a is None:
                a = acc[sid] = {**dto, "times_seen": 0, "wrong_count": 0, "correct_count": 0,
                                "last_seen_at": None, "_sources": {}}
            a["times_seen"] += ev["seen"]
            a["wrong_count"] += ev["wrong"]
            a["correct_count"] += ev["correct"]
            if ev["last_seen_at"] and (
                a["last_seen_at"] is None or ev["last_seen_at"] > a["last_seen_at"]
            ):
                a["last_seen_at"] = ev["last_seen_at"]
            # Strongest relevance across every link (checkpost #999 F3) — not the
            # first-encountered value, which depended on undefined row order.
            if _RELEVANCE_RANK.get(dto.get("relevance"), 99) < _RELEVANCE_RANK.get(a.get("relevance"), 99):
                a["relevance"] = dto.get("relevance")
            prev = a["_sources"].get(qid)
            cur = ev["last_seen_at"] or ""
            if prev is None or cur > prev:
                a["_sources"][qid] = cur

    items = []
    for a in acc.values():
        sources = a.pop("_sources")
        # Recent source questions first (by their last_seen), id-tie-broken, then cap.
        ordered_src = sorted(sources)  # id asc
        ordered_src.sort(key=lambda qid: sources[qid], reverse=True)  # last_seen desc
        a["source_question_ids"] = ordered_src[:_MAX_SOURCE_QUESTIONS]
        items.append(a)

    # 6. Rank: wrong-associated and recent first, then relevance, then stable name/id.
    #    Staged stable sorts, least-significant key first.
    items.sort(key=lambda s: ((s.get("name") or "").lower(), str(s.get("id") or "")))
    items.sort(key=lambda s: _RELEVANCE_RANK.get(s.get("relevance"), 99))
    items.sort(key=lambda s: (s.get("last_seen_at") or ""), reverse=True)
    items.sort(key=lambda s: 0 if (s.get("wrong_count") or 0) > 0 else 1)
    return items[:_MAX_ITEMS]
