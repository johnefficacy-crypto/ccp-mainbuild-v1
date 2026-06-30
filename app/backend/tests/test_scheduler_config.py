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


# ── run_job_now failure classification ───────────────────────────────────────


def test_run_job_now_failed_extraction_returns_ok_false():
    """run_job_now must honour _is_failure_result: a failed doc:text_extract
    job returns ok=False rather than the old always-True behaviour."""
    from unittest.mock import patch
    from app.notifications.scheduler import run_job_now

    failed_result = {"processed": 1, "status": "failed", "job_id": "xyz", "error": "crash"}
    with patch("app.notifications.scheduler.JOBS", {"doc:text_extract": lambda: failed_result}):
        out = run_job_now("doc:text_extract")

    assert out["ok"] is False
    assert out["result"] == failed_result


def test_run_job_now_succeeded_extraction_returns_ok_true():
    """A successful doc:text_extract job must still return ok=True."""
    from unittest.mock import patch
    from app.notifications.scheduler import run_job_now

    success_result = {"processed": 1, "status": "succeeded", "job_id": "xyz", "error": None}
    with patch("app.notifications.scheduler.JOBS", {"doc:text_extract": lambda: success_result}):
        out = run_job_now("doc:text_extract")

    assert out["ok"] is True


def test_run_job_now_idle_returns_ok_true():
    """An idle pass (nothing queued) is not a failure."""
    from unittest.mock import patch
    from app.notifications.scheduler import run_job_now

    idle_result = {"processed": 0, "status": "idle", "job_id": None, "error": None}
    with patch("app.notifications.scheduler.JOBS", {"doc:text_extract": lambda: idle_result}):
        out = run_job_now("doc:text_extract")

    assert out["ok"] is True


# ── JOB_PERMISSIONS ──────────────────────────────────────────────────────────


def test_job_permissions_doc_text_extract():
    from app.notifications.scheduler import JOB_PERMISSIONS
    assert JOB_PERMISSIONS.get("doc:text_extract") == "exam_intelligence.cms"


def test_job_permissions_notif_dispatch_not_restricted():
    """Standard notification jobs must not be in the restricted map."""
    from app.notifications.scheduler import JOB_PERMISSIONS
    assert "notif:dispatch" not in JOB_PERMISSIONS
