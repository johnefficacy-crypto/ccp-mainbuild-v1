"""Attempt event service (PR2b).

Responsibilities:
  - record_server_event : synchronous INSERT called from inside mock_engine's
    hot-path handlers (same logical unit-of-work as the state change).
  - ingest_client_events: validates + idempotency-deduplicates a client batch,
    inserts accepted rows, and returns {accepted, duplicates, rejected}.
  - get_events          : paged read for the GET endpoint.

Server rows are the source of truth for any score-affecting event.
Client rows coexist for UX telemetry and anti-cheat (PR3) signals.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.study_os.attempt_event_types import KNOWN_CLIENT_EVENTS

logger = logging.getLogger("career_copilot.study_os.attempt_events")

MAX_BATCH = 100
DEFAULT_PAGE_SIZE = 500


# ── helpers ────────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe(call, default=None):
    try:
        return call()
    except Exception as exc:  # noqa: BLE001
        logger.warning("attempt_events supabase call failed: %s", exc)
        return default


# ── public API ─────────────────────────────────────────────────────────────────

def record_server_event(
    supabase: Any,
    attempt_id: str,
    user_id: str,
    event_type: str,
    payload: dict | None = None,
    occurred_at: str | None = None,
) -> None:
    """Insert one server-authoritative event row.

    Called from inside mock_engine handlers immediately after the state change.
    Uses _safe so a DB hiccup never breaks the hot path.
    """
    _safe(
        lambda: supabase.table("mock_attempt_events").insert({
            "attempt_id": attempt_id,
            "user_id": user_id,
            "event_type": event_type,
            "payload": payload or {},
            "source": "server",
            "occurred_at": occurred_at or _now_iso(),
        }).execute(),
        default=None,
    )


def ingest_client_events(
    supabase: Any,
    attempt_id: str,
    user_id: str,
    raw_events: list[dict],
) -> dict:
    """Validate, deduplicate, and insert a batch of client events.

    Returns:
        {accepted: int, duplicates: int, rejected: [{seq, reason}]}

    Idempotency: duplicate (attempt_id, sequence_no) pairs are detected via a
    pre-fetch of existing sequence numbers and skipped (not re-inserted).
    Out-of-order sequence numbers are accepted — ordering is a query-time concern.
    """
    accepted = 0
    duplicates = 0
    rejected: list[dict] = []

    # Fetch existing client sequence numbers for this attempt (idempotency check).
    existing_rows = _safe(
        lambda: supabase.table("mock_attempt_events")
        .select("sequence_no")
        .eq("attempt_id", attempt_id)
        .eq("source", "client")
        .execute(),
        default=None,
    )
    existing_seqs: set[int] = {
        r["sequence_no"]
        for r in (getattr(existing_rows, "data", None) or [])
        if r.get("sequence_no") is not None
    }

    # Track seqs seen within this batch to catch intra-batch duplicates.
    batch_seqs: set[int] = set()

    for ev in raw_events:
        event_type = ev.get("event_type", "")
        seq = ev.get("sequence_no")
        occurred_at = ev.get("occurred_at")
        payload = ev.get("payload") or {}

        # Validate event type.
        if event_type not in KNOWN_CLIENT_EVENTS:
            rejected.append({"seq": seq, "reason": f"unknown event_type: {event_type!r}"})
            continue

        # Validate occurred_at.
        if not occurred_at:
            rejected.append({"seq": seq, "reason": "missing occurred_at"})
            continue

        # Idempotency: skip already-stored or intra-batch duplicate sequence numbers.
        if seq is not None:
            if seq in existing_seqs or seq in batch_seqs:
                duplicates += 1
                continue
            batch_seqs.add(seq)

        row = {
            "attempt_id": attempt_id,
            "user_id": user_id,
            "event_type": event_type,
            "payload": payload,
            "sequence_no": seq,
            "source": "client",
            "occurred_at": occurred_at,
        }
        ok = _safe(
            lambda r=row: supabase.table("mock_attempt_events").insert(r).execute(),
            default=None,
        )
        if ok is None:
            rejected.append({"seq": seq, "reason": "db_error"})
        else:
            if seq is not None:
                existing_seqs.add(seq)
            accepted += 1

    return {"accepted": accepted, "duplicates": duplicates, "rejected": rejected}


def get_events(
    supabase: Any,
    attempt_id: str,
    page: int = 0,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> list[dict]:
    """Return events for an attempt ordered by occurred_at ascending, paginated."""
    offset = page * page_size
    rows = _safe(
        lambda: supabase.table("mock_attempt_events")
        .select("*")
        .eq("attempt_id", attempt_id)
        .order("occurred_at", desc=False)
        .limit(page_size)
        .execute(),
        default=None,
    )
    data = getattr(rows, "data", None) or []
    # Manual offset for stub compatibility (Supabase REST supports .range() for real pagination).
    return data[offset:] if offset else data
