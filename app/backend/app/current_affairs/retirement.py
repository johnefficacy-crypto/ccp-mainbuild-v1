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


def sweep_expired_current_events(supabase: Any) -> dict[str, Any]:
    """Archive active current-affairs events past their relevance window. Returns
    ``{"archived": <int>}`` (0 on a quiet tick)."""
    data = supabase.rpc("ca_sweep_expired_current_events", {}).execute().data
    archived = data if isinstance(data, int) else (data or 0)
    try:
        return {"archived": int(archived or 0)}
    except (TypeError, ValueError):
        return {"archived": 0}
