"""Improvement Lab — personalized learner strategy feeds (GQR-S6).

Contract: docs/architecture/solution-strategies-improvement-lab.md §10.3 + §11.

A BOUNDED, owner-scoped projection over the learner's SUBMITTED mock-attempt
history:

  recent submitted attempts (owner-scoped, bounded)
    → their response questions (bounded)
      → the verified-only Solution Strategy set for those questions (LIVE, via the
        shared aggregator — never a full-library dump)
        → per-strategy evidence (times_seen / wrong / correct / last_seen /
          recent source questions)
          → ranked wrong-associated and recent first, then relevance, then name.

Guardrails preserved: never reads governed strategy tables directly; every read is
owner-scoped and submitted-only; reads are bounded; content is a live verified-only
projection (withdrawn/inactive strategies vanish without touching history); only the
learner-safe DTO + aggregate evidence leave the server (governance stripped by
construction in the projector); fail-soft — any read failure yields ``[]``, never a
500. No saved-strategy table, no planner writes, no target-solve-time inference.
"""
from __future__ import annotations

import logging
from typing import Any, Callable

from app.study_os import solution_strategies

logger = logging.getLogger("career_copilot.study_os.improvement_lab")

# Bounded reads (contract §10.3 step 1-2, §11.3) — no unbounded scan, no full dump.
_MAX_ATTEMPTS = 30
_MAX_RESPONSES = 2000
_MAX_QUESTIONS = 500
_MAX_ITEMS = 50
_MAX_SOURCE_QUESTIONS = 5

_RELEVANCE_RANK = {"primary": 0, "secondary": 1, "related": 2}


def _safe(call: Callable[[], Any], default: Any = None) -> Any:
    try:
        return call()
    except Exception as exc:  # noqa: BLE001
        logger.warning("db_op_failed op=improvement_lab err=%r", exc)
        return default


def build_feed(supabase: Any, user_id: str | None, subject_family: str) -> list[dict]:
    """Return the ranked, evidence-annotated learner strategy feed for one subject.

    ``subject_family`` is ``"quant"`` or ``"reasoning"``. Returns ``[]`` for an
    unknown user, empty history, or any read failure (fail-soft).
    """
    if not user_id:
        return []

    # 1. Recent SUBMITTED attempts owned by the caller (bounded). Never the
    #    unowner-scoped system path — this is learner content.
    att_rows = _safe(
        lambda: supabase.table("mock_attempts")
        .select("id,submitted_at")
        .eq("user_id", user_id)
        .eq("status", "submitted")
        .order("submitted_at", desc=True)
        .limit(_MAX_ATTEMPTS)
        .execute(),
        default=None,
    )
    attempts = getattr(att_rows, "data", None) or []
    submitted_by_attempt = {
        a["id"]: a.get("submitted_at") for a in attempts if isinstance(a, dict) and a.get("id")
    }
    if not submitted_by_attempt:
        return []

    # 2. Responses across those attempts (bounded), for per-question evidence.
    resp_rows = _safe(
        lambda: supabase.table("mock_attempt_responses")
        .select("attempt_id,question_id,is_correct")
        .in_("attempt_id", list(submitted_by_attempt))
        .limit(_MAX_RESPONSES)
        .execute(),
        default=None,
    )
    responses = getattr(resp_rows, "data", None) or []

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

    # 3. Verified-only LIVE strategies for the attempted questions (bounded set),
    #    via the shared aggregator (fail-soft; governance stripped by construction).
    question_ids = list(q_ev)[:_MAX_QUESTIONS]
    by_q = _safe(
        lambda: solution_strategies.strategies_for_questions(supabase, question_ids),
        default={},
    ) or {}

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
                a = acc[sid] = {
                    **dto,
                    "times_seen": 0,
                    "wrong_count": 0,
                    "correct_count": 0,
                    "last_seen_at": None,
                    "source_question_ids": [],
                }
            a["times_seen"] += ev["seen"]
            a["wrong_count"] += ev["wrong"]
            a["correct_count"] += ev["correct"]
            if ev["last_seen_at"] and (
                a["last_seen_at"] is None or ev["last_seen_at"] > a["last_seen_at"]
            ):
                a["last_seen_at"] = ev["last_seen_at"]
            if qid not in a["source_question_ids"]:
                a["source_question_ids"].append(qid)

    items = list(acc.values())
    for it in items:
        it["source_question_ids"] = it["source_question_ids"][:_MAX_SOURCE_QUESTIONS]

    # 6. Rank: wrong-associated and recent first, then relevance, then stable name/id.
    #    Staged stable sorts, least-significant key first.
    items.sort(key=lambda s: ((s.get("name") or "").lower(), str(s.get("id") or "")))
    items.sort(key=lambda s: _RELEVANCE_RANK.get(s.get("relevance"), 99))
    items.sort(key=lambda s: (s.get("last_seen_at") or ""), reverse=True)
    items.sort(key=lambda s: 0 if (s.get("wrong_count") or 0) > 0 else 1)
    return items[:_MAX_ITEMS]
