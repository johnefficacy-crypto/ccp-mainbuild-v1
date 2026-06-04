"""Tests: RejectRequest.reason is required (8–500 chars).

Written BEFORE the tightening — tests must fail until RejectRequest.reason
becomes a required Field(min_length=8, max_length=500).
"""
from __future__ import annotations

from copy import deepcopy
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.admin_verification_reports import RejectRequest, reject_report


ADMIN = {"id": "admin-1", "role": "admin"}
REPORT_ID = "rpt-001"


# ── pydantic schema ───────────────────────────────────────────────────

def test_reject_request_requires_reason():
    with pytest.raises(ValidationError):
        RejectRequest()


def test_reject_request_rejects_short_reason():
    with pytest.raises(ValidationError):
        RejectRequest(reason="short")


def test_reject_request_rejects_empty_reason():
    with pytest.raises(ValidationError):
        RejectRequest(reason="")


def test_reject_request_rejects_reason_over_500():
    with pytest.raises(ValidationError):
        RejectRequest(reason="x" * 501)


def test_reject_request_accepts_valid_reason():
    r = RejectRequest(reason="Duplicate entry confirmed by admin review.")
    assert r.reason == "Duplicate entry confirmed by admin review."


def test_reject_request_accepts_exactly_8_chars():
    r = RejectRequest(reason="12345678")
    assert len(r.reason) == 8


def test_reject_request_accepts_exactly_500_chars():
    r = RejectRequest(reason="x" * 500)
    assert len(r.reason) == 500


# ── endpoint behaviour ────────────────────────────────────────────────

class _R:
    def __init__(self, data):
        self.data = data


class _FakeTable:
    def __init__(self, rows):
        self._rows = rows
        self._filters: dict = {}

    def select(self, *_):
        return self

    def update(self, _payload):
        return self

    def eq(self, col, val):
        self._filters[col] = val
        return self

    def limit(self, _):
        return self

    def execute(self):
        rows = [r for r in self._rows if all(r.get(k) == v for k, v in self._filters.items())]
        return _R(rows)


class _FakeSB:
    def __init__(self, reports=()):
        self._reports = [deepcopy(r) for r in reports]

    def table(self, _name):
        return _FakeTable(self._reports)


def _make_sb():
    return _FakeSB(reports=[{"id": REPORT_ID, "lifecycle_status": "classified"}])


@patch("app.api.admin_verification_reports.update_lifecycle_status")
@patch("app.api.admin_verification_reports.get_supabase_admin")
def test_reject_endpoint_succeeds_with_valid_reason(mock_sb, mock_update):
    mock_sb.return_value = _make_sb()
    mock_update.return_value = {"id": REPORT_ID, "lifecycle_status": "rejected"}

    result = reject_report(
        report_id=REPORT_ID,
        payload=RejectRequest(reason="Confirmed duplicate — same exam already published."),
        admin=ADMIN,
    )
    assert result["lifecycle_status"] == "rejected"
    mock_update.assert_called_once_with(mock_sb.return_value, REPORT_ID, "rejected")
