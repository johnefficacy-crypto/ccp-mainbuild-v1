"""Tests: bulk_dry_run() filters by selected_ids at DB level.

Concern 2 of fix/gateway-promote-wire.

Written BEFORE implementation — the test must fail until
bulk_dry_run() is fixed to use a DB-side .in_() filter instead of
a full-table scan.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.api.admin_verification_reports import BulkRequest, bulk_dry_run

ADMIN = {"id": "admin-1", "role": "admin"}


class _FilterSpyTable:
    """Query builder that records whether .in_() was called before .execute()."""

    def __init__(self, rows: list[dict], log: list):
        self._rows = rows
        self._log = log
        self._in_filter: tuple | None = None
        self._eq_filters: dict = {}

    def select(self, *_):
        return self

    def eq(self, col, val):
        self._eq_filters[col] = val
        return self

    def in_(self, col, vals):
        self._in_filter = (col, list(vals))
        self._log.append(("in_", col, list(vals)))
        return self

    def limit(self, _):
        return self

    def execute(self):
        if self._in_filter is None:
            raise AssertionError(
                "bulk_dry_run performed a full-table scan — "
                ".in_('id', selected_ids) filter was not applied before execute()"
            )
        col, vals = self._in_filter
        val_set = set(vals)
        rows = [r for r in self._rows if r.get(col) in val_set]
        return _R(rows)


class _R:
    def __init__(self, data):
        self.data = data


class _FilterSpySB:
    """Fake Supabase that enforces a DB-side .in_() filter for bulk_dry_run."""

    def __init__(self, rows: list[dict]):
        self._rows = rows
        self.filter_log: list = []

    def table(self, name):
        if name == "recruitment_verification_reports":
            return _FilterSpyTable(self._rows, self.filter_log)
        return _FilterSpyTable([], self.filter_log)


def _report(rid, tier="C_STANDARD_LONG_TAIL", status="reviewed",
            resolution="resolved_verified"):
    return {
        "id": rid,
        "scrape_queue_id": f"q-{rid}",
        "recommended_action": "request_admin_review",
        "recruitment_id": None,
        "criticality_tier": tier,
        "lifecycle_status": status,
        "risk_flags": [],
        "conflicts": [],
        "official_resolution_status": resolution,
    }


class TestBulkDryRunFilter:

    @patch("app.api.admin_verification_reports.get_supabase_admin")
    def test_db_query_filtered_by_selected_ids(self, mock_sb_factory):
        """bulk_dry_run must pass selected_ids as a DB-side filter, not scan all rows."""
        # DB has 5 reports; only 2 are selected.  If the old full-table scan
        # runs, the spy raises AssertionError before results are computed.
        all_rows = [_report(f"rpt-{i}") for i in range(5)]
        sb = _FilterSpySB(all_rows)
        mock_sb_factory.return_value = sb

        selected = ["rpt-0", "rpt-2"]
        result = bulk_dry_run(
            payload=BulkRequest(selected_ids=selected, action="bulk_promote"),
            admin=ADMIN,
        )

        # Verify the in_ filter was actually applied with the right IDs
        assert sb.filter_log, "No DB-side filter recorded — full-table scan detected"
        op, col, vals = sb.filter_log[0]
        assert op == "in_"
        assert col == "id"
        assert set(vals) == set(selected)

        # Result must only reflect the 2 selected rows
        assert result["result"]["eligible_count"] + result["result"]["blocked_count"] == len(selected)
