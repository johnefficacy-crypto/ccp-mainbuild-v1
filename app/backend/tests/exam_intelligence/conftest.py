"""Shared fixtures for exam_intelligence tests.

Pins work_queue._now() to a fixed UTC datetime so that staleness
calculations are deterministic regardless of when tests run.

_RECENT = "2026-06-16T00:00:00+00:00" and STALE_REVIEW_DAYS = 14 mean the
boundary falls on 2026-06-16. By anchoring _now() to 2026-06-23T00:00:00Z
the stale cutoff is 2026-06-09, keeping _RECENT safely non-stale and
_STALE ("2026-01-01") firmly stale.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.exam_intelligence import work_queue as wq

_FIXED_NOW = datetime(2026, 6, 23, 0, 0, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def pin_work_queue_now(monkeypatch):
    monkeypatch.setattr(wq, "_now", lambda: _FIXED_NOW)
