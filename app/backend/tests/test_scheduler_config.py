"""Tests for scheduler configuration hardening.

Covers:
- _parse_text_extract_interval: valid, zero, negative, non-integer,
  below min, above max — all invalid values must return the default.
- _is_failure_result: doc:text_extract failure propagation to ok=False.
- _is_noop_result: doc:text_extract idle suppression.
"""
from __future__ import annotations

import pytest


# ── _is_failure_result ───────────────────────────────────────────────────────


def test_is_failure_result_failed_extraction():
    from app.notifications.scheduler import _is_failure_result

    result = {"processed": 1, "status": "failed", "job_id": "abc", "error": "crash"}
    assert _is_failure_result("doc:text_extract", result) is True


def test_is_failure_result_success_not_failure():
    from app.notifications.scheduler import _is_failure_result

    result = {"processed": 1, "status": "succeeded", "job_id": "abc", "error": None}
    assert _is_failure_result("doc:text_extract", result) is False


def test_is_failure_result_conflict_not_failure():
    from app.notifications.scheduler import _is_failure_result

    # conflict → processed=0; not an operational failure
    result = {"processed": 0, "status": "conflict", "job_id": "abc", "error": "claimed"}
    assert _is_failure_result("doc:text_extract", result) is False


def test_is_failure_result_other_job_always_false():
    from app.notifications.scheduler import _is_failure_result

    assert _is_failure_result("mock:sweeper", {"failed": 1}) is False
    assert _is_failure_result("notif:dispatch", {"error": "x"}) is False


# ── _is_noop_result ──────────────────────────────────────────────────────────


def test_is_noop_result_idle():
    from app.notifications.scheduler import _is_noop_result

    assert _is_noop_result("doc:text_extract", {"processed": 0, "status": "idle"}) is True


def test_is_noop_result_processed_not_noop():
    from app.notifications.scheduler import _is_noop_result

    assert _is_noop_result("doc:text_extract", {"processed": 1, "status": "succeeded"}) is False


# ── _parse_text_extract_interval ─────────────────────────────────────────────


@pytest.mark.parametrize("bad_value,expected", [
    ("0",     60),   # zero — out of range
    ("-1",    60),   # negative
    ("abc",   60),   # non-integer
    ("",      60),   # empty string
    ("9",     60),   # below minimum (10)
    ("3601",  60),   # above maximum (3600)
    ("99999", 60),   # far above maximum
])
def test_invalid_interval_falls_back_to_default(bad_value, expected, monkeypatch):
    monkeypatch.setenv("TEXT_EXTRACT_WORKER_INTERVAL_SECONDS", bad_value)
    from app.notifications.scheduler import _parse_text_extract_interval
    assert _parse_text_extract_interval() == expected


@pytest.mark.parametrize("good_value", ["10", "60", "120", "3600"])
def test_valid_interval_accepted(good_value, monkeypatch):
    monkeypatch.setenv("TEXT_EXTRACT_WORKER_INTERVAL_SECONDS", good_value)
    from app.notifications.scheduler import _parse_text_extract_interval
    assert _parse_text_extract_interval() == int(good_value)


def test_default_when_env_unset(monkeypatch):
    monkeypatch.delenv("TEXT_EXTRACT_WORKER_INTERVAL_SECONDS", raising=False)
    from app.notifications.scheduler import _parse_text_extract_interval, _TEXT_EXTRACT_INTERVAL_DEFAULT
    assert _parse_text_extract_interval() == _TEXT_EXTRACT_INTERVAL_DEFAULT
