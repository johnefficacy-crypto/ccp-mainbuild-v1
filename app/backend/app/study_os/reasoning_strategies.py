"""Reasoning strategy authority — governance review wrapper (GQR-S3).

Content Studio authors and reviews ``reasoning_strategies`` (migration 261). This
module is the thin wrapper over the ``cms_review_reasoning_strategy`` lifecycle
RPC, mirroring ``study_os.quant_heuristics.review_heuristic``.

GQR-S3 stops BEFORE learner delivery: the batched verified-only
``strategies_for_questions()`` reader and its shared-DTO projection are GQR-S4
(solution-strategies-improvement-lab.md §8.4) and are deliberately NOT added here.
When they are, the same conjunctive gate the Quant authority uses applies — a
strategy reaches a learner only when the strategy row is verified AND active AND
its question link is verified.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("career_copilot.study_os.reasoning_strategies")


def review_strategy(
    supabase: Any,
    *,
    strategy_id: str,
    expected_status: str,
    expected_updated_at: str,
    new_status: str,
    reviewer_notes: str | None,
    reason: str,
    actor_user_id: str,
    actor_email: str | None,
) -> dict:
    """Transition a strategy's reviewer_status via the audited lifecycle RPC.

    The RPC (migration 261) owns the transition matrix, dual optimistic-
    concurrency (CAS on BOTH ``expected_status`` and ``expected_updated_at`` — the
    content-revision token, so a reviewer can never verify a revision they did not
    read), the mandatory 8–500 char audit ``reason``, and the audit row. This
    wrapper only marshals params and returns the RPC's JSON result. Raises on RPC
    error (invalid transition, stale expected status, stale content token, invalid
    reason, missing actor) — callers surface those as 4xx.
    """
    res = supabase.rpc(
        "cms_review_reasoning_strategy",
        {
            "p_strategy_id": strategy_id,
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
