"""Quant heuristic authority — verified-only reads + review wrapper (GQR-Q7).

Content Studio authors and reviews ``quant_heuristics`` (migration 243). This
module is the read/selection authority the learner-feedback path uses, plus a
thin wrapper over the ``cms_review_quant_heuristic`` lifecycle RPC.

Domain rule (CLAUDE.md): user-facing reads filter ``reviewer_status='verified'``
CONJUNCTIVELY. A heuristic reaches a learner only when BOTH the heuristic row and
its question link are verified — and the heuristic is active. This is defense in
depth: the link's own reviewer_status cannot leak a pending/rejected heuristic,
and the heuristic's status cannot leak through an over-eager link.
"""
from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger("career_copilot.study_os.quant_heuristics")

_HEURISTICS = "quant_heuristics"
_LINKS = "quant_question_heuristics"

# Learner-facing display order for a question's heuristics.
_RELEVANCE_RANK = {"primary": 0, "secondary": 1, "related": 2}


def _safe(call: Callable[[], Any], default: Any = None) -> Any:
    try:
        return call()
    except Exception as exc:  # noqa: BLE001
        logger.warning("db_op_failed op=quant_heuristics err=%r", exc)
        return default


def heuristics_for_question(supabase: Any, question_id: str) -> list[dict]:
    """Return the VERIFIED heuristics linked to ``question_id``, in display order.

    Two-stage verified gate:
      1. verified links for the question (link.reviewer_status='verified'),
      2. of those, the heuristics that are themselves verified AND active.
    A heuristic missing from stage 2 (pending/rejected/needs_correction or
    inactive) is dropped even if its link says verified — never leaked.
    Ordered by link relevance (primary → secondary → related) then name.
    """
    link_rows = _safe(
        lambda: supabase.table(_LINKS)
        .select("heuristic_id,relevance,reviewer_status")
        .eq("question_id", question_id)
        .eq("reviewer_status", "verified")
        .execute(),
        default=None,
    )
    links = getattr(link_rows, "data", None) or []
    if not links:
        return []
    relevance_by_id = {l["heuristic_id"]: l.get("relevance") or "related" for l in links}
    heuristic_ids = list(relevance_by_id.keys())

    heur_rows = _safe(
        lambda: supabase.table(_HEURISTICS)
        .select("*")
        .in_("id", heuristic_ids)
        .eq("reviewer_status", "verified")
        .eq("is_active", True)
        .execute(),
        default=None,
    )
    heuristics = getattr(heur_rows, "data", None) or []

    def _key(h: dict) -> tuple:
        rel = relevance_by_id.get(h["id"], "related")
        return (_RELEVANCE_RANK.get(rel, 99), (h.get("name") or "").lower())

    out = []
    for h in sorted(heuristics, key=_key):
        out.append({**h, "relevance": relevance_by_id.get(h["id"], "related")})
    return out


def heuristics_for_questions(
    supabase: Any, question_ids: list[str]
) -> dict[str, list[dict]]:
    """Batched form of :func:`heuristics_for_question` — ``{question_id: [rows]}``.

    Uses at most ONE link query and ONE heuristic query regardless of how many
    question ids are passed (no N+1). Same conjunctive verified gate: link
    verified AND heuristic verified AND heuristic active. Every requested id is
    present in the result with at least ``[]``; ids never cross-leak (a heuristic
    is attached only to the questions whose verified link references it). Order
    per question is deterministic: relevance (primary → secondary → related) then
    name. Fails soft to the initialized empty map on a read error.
    """
    ids = [q for q in dict.fromkeys(question_ids or []) if q]
    out: dict[str, list[dict]] = {q: [] for q in ids}
    if not ids:
        return out

    link_rows = _safe(
        lambda: supabase.table(_LINKS)
        .select("question_id,heuristic_id,relevance,reviewer_status")
        .in_("question_id", ids)
        .eq("reviewer_status", "verified")
        .execute(),
        default=None,
    )
    links = getattr(link_rows, "data", None) or []
    if not links:
        return out

    heuristic_ids = sorted({l["heuristic_id"] for l in links if l.get("heuristic_id")})
    if not heuristic_ids:
        return out

    heur_rows = _safe(
        lambda: supabase.table(_HEURISTICS)
        .select("*")
        .in_("id", heuristic_ids)
        .eq("reviewer_status", "verified")
        .eq("is_active", True)
        .execute(),
        default=None,
    )
    heur_by_id = {h["id"]: h for h in (getattr(heur_rows, "data", None) or []) if h.get("id")}

    for l in links:
        qid = l.get("question_id")
        h = heur_by_id.get(l.get("heuristic_id"))
        if qid in out and h is not None:
            # Spread per (question, heuristic) so a heuristic linked to several
            # questions carries each link's own relevance without shared mutation.
            out[qid].append({**h, "relevance": l.get("relevance") or "related"})

    def _key(h: dict) -> tuple:
        return (_RELEVANCE_RANK.get(h.get("relevance"), 99), (h.get("name") or "").lower())

    for qid in out:
        out[qid].sort(key=_key)
    return out


def list_verified_heuristics_for_topic(
    supabase: Any, *, topic_id: str | None = None, microtopic_id: str | None = None
) -> list[dict]:
    """Verified + active heuristics scoped to a topic or microtopic.

    At least one of ``topic_id`` / ``microtopic_id`` must be supplied; passing
    neither returns ``[]`` rather than scanning the whole table.
    """
    if not topic_id and not microtopic_id:
        return []
    q = (
        supabase.table(_HEURISTICS)
        .select("*")
        .eq("reviewer_status", "verified")
        .eq("is_active", True)
    )
    if microtopic_id:
        q = q.eq("microtopic_id", microtopic_id)
    elif topic_id:
        q = q.eq("topic_id", topic_id)
    rows = _safe(lambda: q.execute(), default=None)
    heuristics = getattr(rows, "data", None) or []
    return sorted(heuristics, key=lambda h: (h.get("name") or "").lower())


def review_heuristic(
    supabase: Any,
    *,
    heuristic_id: str,
    expected_status: str,
    expected_updated_at: str,
    new_status: str,
    reviewer_notes: str | None,
    reason: str,
    actor_user_id: str,
    actor_email: str | None,
) -> dict:
    """Transition a heuristic's reviewer_status via the audited lifecycle RPC.

    The RPC (migration 246, replacing 243) owns the transition matrix, dual
    optimistic-concurrency (CAS on BOTH ``expected_status`` and
    ``expected_updated_at`` — the content-revision token, so a reviewer can never
    verify a revision they did not read), the mandatory 8–500 char audit
    ``reason``, and the audit row. This wrapper only marshals params and returns
    the RPC's JSON result. Raises on RPC error (invalid transition, stale expected
    status, stale content token, invalid reason, missing actor) — callers surface
    those as 4xx.
    """
    res = supabase.rpc(
        "cms_review_quant_heuristic",
        {
            "p_heuristic_id": heuristic_id,
            "p_expected_status": expected_status,
            "p_expected_updated_at": expected_updated_at,
            "p_new_status": new_status,
            "p_reviewer_notes": reviewer_notes,
            "p_reason": reason,
            "p_actor_user_id": actor_user_id,
            "p_actor_email": actor_email,
        },
    ).execute()
    return getattr(res, "data", None) or {}
