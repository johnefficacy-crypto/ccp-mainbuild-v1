"""Tests: rejection_notes persistence + bulk_reject reason enforcement.

Written BEFORE implementation — all tests must fail until:
  1. rejection_notes column exists (mocked via FakeSB).
  2. reject_report persists payload.reason to rejection_notes.
  3. BulkRequest gains a reason field; bulk_reject enforces it (422).
  4. bulk_apply threads reason to each reject_report call.
"""
from __future__ import annotations

from copy import deepcopy
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.admin_verification_reports import (
    BulkRequest,
    RejectRequest,
    bulk_apply,
    reject_report,
)

ADMIN = {"id": "admin-1", "role": "admin"}
REPORT_ID = "rpt-001"
VALID_REASON = "Confirmed duplicate — same exam already published by another source."


# ── FakeSB mirrors test_reject_reason_required.py ────────────────────

class _R:
    def __init__(self, data):
        self.data = data


class _FakeTable:
    def __init__(self, sb, name):
        self._sb = sb
        self._name = name
        self._filters: dict = {}
        self._update_payload: dict | None = None

    def select(self, *_):
        return self

    def update(self, payload):
        self._update_payload = dict(payload)
        return self

    def eq(self, col, val):
        self._filters[col] = val
        return self

    def limit(self, _):
        return self

    def execute(self):
        pool = self._sb._rows.get(self._name, [])
        matched = [r for r in pool if all(r.get(k) == v for k, v in self._filters.items())]
        if self._update_payload is not None:
            for r in matched:
                r.update(self._update_payload)
                self._sb._update_log.append({
                    "table": self._name,
                    "payload": deepcopy(self._update_payload),
                    "id": r.get("id"),
                })
        return _R(matched)


class _FakeSB:
    def __init__(self, rows: dict | None = None):
        self._rows = rows or {}
        self._update_log: list[dict] = []

    def table(self, name):
        return _FakeTable(self, name)


def _make_sb(*report_ids: str):
    rows = [{"id": rid, "lifecycle_status": "classified"} for rid in report_ids]
    return _FakeSB({"recruitment_verification_reports": rows})


# ── reject_report: reason persisted to rejection_notes ───────────────

@patch("app.api.admin_verification_reports.update_lifecycle_status")
@patch("app.api.admin_verification_reports.get_supabase_admin")
def test_reject_persists_reason_to_rejection_notes(mock_sb, mock_update):
    sb = _make_sb(REPORT_ID)
    mock_sb.return_value = sb
    mock_update.return_value = {"id": REPORT_ID, "lifecycle_status": "rejected"}

    reject_report(
        report_id=REPORT_ID,
        payload=RejectRequest(reason=VALID_REASON),
        admin=ADMIN,
    )

    notes_updates = [
        e for e in sb._update_log
        if "rejection_notes" in e["payload"]
    ]
    assert len(notes_updates) == 1, "rejection_notes must be written once"
    assert notes_updates[0]["payload"]["rejection_notes"] == VALID_REASON


@patch("app.api.admin_verification_reports.update_lifecycle_status")
@patch("app.api.admin_verification_reports.get_supabase_admin")
def test_reject_does_not_overwrite_recommended_action(mock_sb, mock_update):
    """The old no_action overwrite must be gone — recommended_action is read-only here."""
    sb = _make_sb(REPORT_ID)
    mock_sb.return_value = sb
    mock_update.return_value = {"id": REPORT_ID, "lifecycle_status": "rejected"}

    reject_report(
        report_id=REPORT_ID,
        payload=RejectRequest(reason=VALID_REASON),
        admin=ADMIN,
    )

    ra_updates = [
        e for e in sb._update_log
        if "recommended_action" in e["payload"]
    ]
    assert len(ra_updates) == 0, "recommended_action must NOT be overwritten on reject"


# ── BulkRequest: reason required for bulk_reject ─────────────────────

def test_bulk_request_reject_requires_reason():
    with pytest.raises((ValidationError, HTTPException)):
        # No reason field — should 422 or fail validation
        payload = BulkRequest(
            selected_ids=[REPORT_ID],
            action="bulk_reject",
            dry_run=False,
        )
        # If BulkRequest accepts it, bulk_apply should still 422
        # (tested separately). For now we expect Pydantic to raise.
        raise AssertionError("BulkRequest should reject bulk_reject without reason")


def test_bulk_request_promote_does_not_require_reason():
    """bulk_promote has no reason requirement."""
    payload = BulkRequest(
        selected_ids=[REPORT_ID],
        action="bulk_promote",
        dry_run=False,
    )
    assert payload.action == "bulk_promote"


def test_bulk_request_reject_accepts_valid_reason():
    payload = BulkRequest(
        selected_ids=[REPORT_ID],
        action="bulk_reject",
        dry_run=False,
        reason=VALID_REASON,
    )
    assert payload.reason == VALID_REASON


def test_bulk_request_reject_rejects_short_reason():
    with pytest.raises(ValidationError):
        BulkRequest(
            selected_ids=[REPORT_ID],
            action="bulk_reject",
            dry_run=False,
            reason="short",
        )


# ── bulk_apply: reason threaded to each reject ───────────────────────

@patch("app.api.admin_verification_reports.bulk_dry_run")
@patch("app.api.admin_verification_reports.reject_report")
@patch("app.api.admin_verification_reports.get_supabase_admin")
def test_bulk_apply_reject_threads_reason(mock_sb, mock_reject, mock_dry_run):
    mock_sb.return_value = _make_sb(REPORT_ID)
    mock_dry_run.return_value = {
        "result": {
            "eligible_count": 1,
            "blocked_count": 0,
            "blockers": [],
        }
    }
    mock_reject.return_value = {"id": REPORT_ID, "lifecycle_status": "rejected"}

    payload = BulkRequest(
        selected_ids=[REPORT_ID],
        action="bulk_reject",
        dry_run=False,
        reason=VALID_REASON,
    )
    bulk_apply(payload=payload, admin=ADMIN)

    assert mock_reject.called
    _, kwargs = mock_reject.call_args
    passed_payload = kwargs.get("payload") or mock_reject.call_args.args[1]
    assert passed_payload.reason == VALID_REASON


@patch("app.api.admin_verification_reports.bulk_dry_run")
@patch("app.api.admin_verification_reports.get_supabase_admin")
def test_bulk_apply_reject_without_reason_raises_422(mock_sb, mock_dry_run):
    """bulk_apply with bulk_reject and no reason must raise 422 before any DB call."""
    mock_sb.return_value = _make_sb(REPORT_ID)
    mock_dry_run.return_value = {
        "result": {"eligible_count": 1, "blocked_count": 0, "blockers": []}
    }

    with pytest.raises((ValidationError, HTTPException)) as exc_info:
        # Try to construct BulkRequest without reason for bulk_reject
        payload = BulkRequest(
            selected_ids=[REPORT_ID],
            action="bulk_reject",
            dry_run=False,
        )
        bulk_apply(payload=payload, admin=ADMIN)

    # Either Pydantic raises at construction or the endpoint raises 422
    if hasattr(exc_info.value, "status_code"):
        assert exc_info.value.status_code == 422
