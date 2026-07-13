"""Current-affairs relevance-window retirement (GQR-G5b).

The ``ca:promote-sweep`` scheduler job calls ``sweep_expired_current_events`` to actively
archive current-affairs EVENTS whose editorial relevance window has closed
(``relevance_until < today``). This is defence-in-depth on top of the read-time filters
(the attempt-start eligibility helper requires ``event.status='active'`` and questions'
``valid_until > now``): archiving the event flips a durable editorial signal so an expired
event never re-enters a freshly-published bundle. It NEVER mutates promoted
``mock_question_bank`` rows or historical attempts — expiry must never delete history.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("career_copilot.current_affairs.retirement")


def _as_int(data: Any) -> int:
    n = data if isinstance(data, int) else (data or 0)
    try:
        return int(n or 0)
    except (TypeError, ValueError):
        return 0


def sweep_expired_current_events(supabase: Any) -> dict[str, Any]:
    """Archive active current-affairs events past their relevance window. Returns
    ``{"archived": <int>}`` (0 on a quiet tick)."""
    return {"archived": _as_int(supabase.rpc("ca_sweep_expired_current_events", {}).execute().data)}


def sweep_expired_retry_items(supabase: Any) -> dict[str, Any]:
    """Expire pending personalised retry items past their relevance window / no-longer-
    relevant (GQR-G6). Expiry only STOPS future scheduling — it never deletes historical
    attempt analytics (the frozen attempt rows are untouched). Returns ``{"retry_expired": <int>}``."""
    return {"retry_expired": _as_int(supabase.rpc("ca_sweep_expired_retry_items", {}).execute().data)}
