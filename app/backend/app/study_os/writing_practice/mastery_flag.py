"""FF_WRITING_MASTERY_WRITES resolution (architecture §10.1, §10.2).

Mirrors the mock mastery flag (app.study_os.mastery_writer) but adds the Lane A
blocking constraint: writing `live` is prohibited until the unified aggregator
exists and the mock mastery pipeline is proven live (§10.2 Option B). Until then
`live` fails closed to `shadow`. Everything fails closed to `off`.
"""
from __future__ import annotations

import logging
import os
from typing import Literal

logger = logging.getLogger("career_copilot.study_os.writing_mastery_flag")

FlagState = Literal["off", "shadow", "live"]

# Lane A gate: flip to True only once the unified aggregator is in place AND
# FF_MOCK_MASTERY_WRITES=live is cleared (see checklist Lane A).
LANE_A_LIVE_UNBLOCKED = False


def get_writing_mastery_write_flag() -> FlagState:
    raw = (os.getenv("FF_WRITING_MASTERY_WRITES") or "off").strip().lower()
    return raw if raw in {"off", "shadow", "live"} else "off"  # fail closed


def resolve_effective_writing_mastery_flag(requested_flag: FlagState, user_id: str) -> FlagState:
    """Resolve the global flag against the per-user allowlist and the Lane A gate.

      off    -> off
      shadow -> shadow
      live + Lane A blocked                 -> shadow (fail-closed; the default today)
      live + user in allowlist + unblocked  -> live
      live + user NOT in allowlist          -> shadow (fail-closed)
      live + allowlist empty/malformed      -> shadow (fail-closed)
    """
    if requested_flag != "live":
        return requested_flag

    if not LANE_A_LIVE_UNBLOCKED:
        logger.warning(
            "writing mastery FF=live but Lane A live-write gate is not cleared — "
            "downgrading to shadow for user=%s", user_id,
        )
        return "shadow"

    raw_ids = os.getenv("FF_WRITING_MASTERY_LIVE_USER_IDS", "").strip()
    if not raw_ids:
        logger.warning(
            "writing mastery FF=live but FF_WRITING_MASTERY_LIVE_USER_IDS is empty — "
            "downgrading to shadow for user=%s", user_id,
        )
        return "shadow"

    try:
        allowlist = {uid.strip() for uid in raw_ids.split(",") if uid.strip()}
    except Exception:  # pragma: no cover - defensive
        logger.exception("failed to parse FF_WRITING_MASTERY_LIVE_USER_IDS — shadow for %s", user_id)
        return "shadow"

    return "live" if user_id in allowlist else "shadow"
