"""SerpApi usage quota guard.

SerpApi's free tier is 250 searches/month. ``external_api_usage``
(migration 124) tracks per-provider daily and monthly counts so a discovery
pass can short-circuit before it spends quota. Only successful, uncached
SerpApi responses count against the tier (cached/errored searches are free),
so :func:`record_serpapi_usage` is called *after* a request returns — never on
a cached or errored response.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any, cast

from supabase import Client

from app.common.time import utc_now_iso

logger = logging.getLogger(__name__)

_PROVIDER = "serpapi"


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _usage_month(day: date) -> str:
    return day.strftime("%Y-%m")


def can_use_serpapi(supabase: Client, *, daily_cap: int, monthly_cap: int) -> bool:
    """Return ``True`` only when neither the daily nor monthly cap is reached.

    Fails closed: if the usage table can't be read we deny the call rather
    than risk blowing the free-tier cap on a blind spend.
    """
    day = _today()
    month = _usage_month(day)
    try:
        daily_rows = cast(list[dict[str, Any]], (
            supabase.table("external_api_usage")
            .select("count")
            .eq("provider", _PROVIDER)
            .eq("usage_date", day.isoformat())
            .execute()
            .data
            or []
        ))
        monthly_rows = cast(list[dict[str, Any]], (
            supabase.table("external_api_usage")
            .select("count")
            .eq("provider", _PROVIDER)
            .eq("usage_month", month)
            .execute()
            .data
            or []
        ))
    except Exception as exc:  # noqa: BLE001
        logger.warning("serpapi quota read failed; denying call: %s", exc)
        return False

    daily_count = sum(int(r.get("count") or 0) for r in daily_rows)
    if daily_cap and daily_count >= daily_cap:
        logger.info("serpapi quota: daily cap reached count=%d cap=%d", daily_count, daily_cap)
        return False
    monthly_count = sum(int(r.get("count") or 0) for r in monthly_rows)
    if monthly_cap and monthly_count >= monthly_cap:
        logger.info("serpapi quota: monthly cap reached count=%d cap=%d", monthly_count, monthly_cap)
        return False
    return True


def record_serpapi_usage(supabase: Client, *, count: int = 1) -> None:
    """Increment today's SerpApi usage counter by ``count``.

    Read-modify-write rather than a true atomic increment: supabase-py can't
    express ``count = count + n``, and the scrape pass is serialised per
    source (one claim lock at a time), so the race window is negligible. A
    Postgres RPC is the upgrade path if concurrent passes ever share the
    counter.
    """
    day = _today()
    month = _usage_month(day)
    try:
        existing = cast(list[dict[str, Any]], (
            supabase.table("external_api_usage")
            .select("id, count")
            .eq("provider", _PROVIDER)
            .eq("usage_month", month)
            .eq("usage_date", day.isoformat())
            .limit(1)
            .execute()
            .data
            or []
        ))
        if existing:
            row = existing[0]
            supabase.table("external_api_usage").update(
                {"count": int(row.get("count") or 0) + count, "updated_at": utc_now_iso()}
            ).eq("id", row["id"]).execute()
        else:
            supabase.table("external_api_usage").insert(
                {
                    "provider": _PROVIDER,
                    "usage_month": month,
                    "usage_date": day.isoformat(),
                    "count": count,
                }
            ).execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning("serpapi usage record failed: %s", exc)
