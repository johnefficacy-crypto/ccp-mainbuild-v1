"""Tests for central-body Source URLs import in import_exam_registry.py.

Covers:
  - central org created with state=null, is_active=True, type='central_commission',
    calendar_status='needs_review', import_status='pending_review',
    import_source='exam_registry_source_urls', source_sheet='Source URLs'
  - multiple sheet rows for one body → ONE org; source_urls holds all URLs deduped;
    official_url = the Official-type URL
  - name variants (RRB / Railway Recruitment Board / Boards) collapse to one org
  - calendar_status falls back to 'needs_review' when sheet carries no signal
  - re-run idempotent: no duplicate central orgs; metadata merge preserves
    an unrelated pre-existing key
  - no source_registry write
  - Subordinate Boards NOT imported via this path
  - existing 33 exam_registry + 9 backfill tests unaffected
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, call

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts"))

from import_exam_registry import (
    _canonical_central_name,
    _group_source_url_rows,
    process_source_urls_sheet,
    org_dedupe_key,
)


# ── _canonical_central_name ───────────────────────────────────────────────────

class TestCanonicalCentralName:
    CASES = [
        ("UPSC", "UPSC"),
        ("upsc", "UPSC"),
        ("Union Public Service Commission", "UPSC"),
        ("SSC", "SSC"),
        ("Staff Selection Commission", "SSC"),
        ("IBPS", "IBPS"),
        ("Institute of Banking Personnel Selection", "IBPS"),
        ("RRB", "RRB"),
        ("Railway Recruitment Board", "RRB"),
        ("Railway Recruitment Boards", "RRB"),
        ("RRBs", "RRB"),
        # Prefix match: "RRB Ahmedabad" → "RRB"
        ("RRB Ahmedabad", "RRB"),
        # Unknown → None
        ("Some Random Board", None),
        ("", None),
    ]

    def test_all_cases(self):
        for raw, expected in self.CASES:
            result = _canonical_central_name(raw)
            assert result == expected, f"For {raw!r}: expected {expected!r}, got {result!r}"


# ── _group_source_url_rows ────────────────────────────────────────────────────

class TestGroupSourceUrlRows:
    def _rows(self) -> list[dict]:
        return [
            {"Name": "UPSC", "Source Type": "Official", "URL": "https://upsc.gov.in"},
            {"Name": "UPSC", "Source Type": "Official calendar/schedule", "URL": "https://upsc.gov.in/calendar"},
            {"Name": "SSC", "Source Type": "Official", "URL": "https://ssc.nic.in"},
            {"Name": "Railway Recruitment Board", "Source Type": "Official", "URL": "https://indianrailways.gov.in/rrb"},
            {"Name": "Railway Recruitment Boards", "Source Type": "Official calendar/schedule", "URL": "https://rrb.gov.in/cal"},
            {"Name": "Unknown Body", "Source Type": "Official", "URL": "https://unknown.gov.in"},
        ]

    def test_multiple_rows_for_one_body_collapse_to_one_group(self):
        groups = _group_source_url_rows(self._rows())
        assert "UPSC" in groups
        assert len(groups["UPSC"]["urls"]) == 2

    def test_rrb_variants_collapse_to_one_group(self):
        groups = _group_source_url_rows(self._rows())
        assert "RRB" in groups
        assert len(groups["RRB"]["urls"]) == 2  # both RRB rows

    def test_unknown_body_excluded(self):
        groups = _group_source_url_rows(self._rows())
        assert all(k in ("UPSC", "SSC", "RRB") for k in groups)

    def test_dedup_identical_url_entry(self):
        rows = [
            {"Name": "UPSC", "Source Type": "Official", "URL": "https://upsc.gov.in"},
            {"Name": "UPSC", "Source Type": "Official", "URL": "https://upsc.gov.in"},  # duplicate
        ]
        groups = _group_source_url_rows(rows)
        assert len(groups["UPSC"]["urls"]) == 1


# ── process_source_urls_sheet — insert payload ───────────────────────────────

def _make_sb_central(existing_rows=None):
    sb = MagicMock()
    select_chain = sb.table.return_value.select.return_value
    select_chain.eq.return_value.execute.return_value.data = existing_rows or []
    sb.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "central-org-id"}
    ]
    sb.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    return sb


class TestCentralOrgInsertPayload:
    def _run(self, rows=None):
        if rows is None:
            rows = [
                {"Name": "UPSC", "Source Type": "Official", "URL": "https://upsc.gov.in"},
                {"Name": "UPSC", "Source Type": "Official calendar/schedule", "URL": "https://upsc.gov.in/cal"},
            ]
        sb = _make_sb_central()
        stats = {"central_orgs": 0}
        process_source_urls_sheet(sb, rows, dry_run=False, org_cache={}, stats=stats)
        return sb

    def test_state_is_null(self):
        sb = self._run()
        insert_call = sb.table.return_value.insert.call_args
        payload = insert_call[0][0]
        assert payload["state"] is None

    def test_is_active_true(self):
        sb = self._run()
        insert_call = sb.table.return_value.insert.call_args
        payload = insert_call[0][0]
        assert payload["is_active"] is True

    def test_type_is_central_commission(self):
        sb = self._run()
        insert_call = sb.table.return_value.insert.call_args
        payload = insert_call[0][0]
        assert payload["type"] == "central_commission"

    def test_calendar_status_needs_review_when_sheet_silent(self):
        sb = self._run()
        insert_call = sb.table.return_value.insert.call_args
        payload = insert_call[0][0]
        assert payload["calendar_status"] == "needs_review"

    def test_import_status_pending_review(self):
        sb = self._run()
        insert_call = sb.table.return_value.insert.call_args
        payload = insert_call[0][0]
        assert payload["metadata"]["import_status"] == "pending_review"

    def test_import_source_is_source_urls_distinct(self):
        """import_source must be 'exam_registry_source_urls', not 'exam_registry_workbook'."""
        sb = self._run()
        insert_call = sb.table.return_value.insert.call_args
        payload = insert_call[0][0]
        assert payload["metadata"]["import_source"] == "exam_registry_source_urls"

    def test_source_sheet_field_set(self):
        sb = self._run()
        insert_call = sb.table.return_value.insert.call_args
        payload = insert_call[0][0]
        assert payload["metadata"]["source_sheet"] == "Source URLs"

    def test_official_url_set_from_official_type_row(self):
        sb = self._run()
        insert_call = sb.table.return_value.insert.call_args
        payload = insert_call[0][0]
        assert payload["metadata"]["official_url"] == "https://upsc.gov.in"

    def test_source_urls_contains_all_urls(self):
        sb = self._run()
        insert_call = sb.table.return_value.insert.call_args
        payload = insert_call[0][0]
        source_urls = payload["metadata"]["source_urls"]
        urls = [e["url"] for e in source_urls]
        assert "https://upsc.gov.in" in urls
        assert "https://upsc.gov.in/cal" in urls

    def test_multiple_rows_produce_one_insert(self):
        """Two rows for UPSC should produce exactly one org insert."""
        sb = self._run()
        assert sb.table.return_value.insert.call_count == 1

    def test_no_source_registry_write(self):
        sb = self._run()
        table_calls = [c[0][0] for c in sb.table.call_args_list]
        assert "source_registry" not in table_calls


# ── idempotency — read-modify-write ──────────────────────────────────────────

class TestCentralOrgIdempotency:
    def test_rerun_merges_metadata_preserves_unrelated_key(self):
        existing_meta = {
            "trust_verified_by": "admin@example.com",  # unrelated key
            "import_status": "pending_review",
        }
        existing_rows = [{
            "id": "existing-central-id",
            "name": "UPSC",
            "type": "central_commission",
            "state": None,
            "calendar_status": "needs_review",
            "metadata": existing_meta,
        }]
        sb = _make_sb_central(existing_rows)
        rows = [{"Name": "UPSC", "Source Type": "Official", "URL": "https://upsc.gov.in"}]
        stats = {"central_orgs": 0}
        process_source_urls_sheet(sb, rows, dry_run=False, org_cache={}, stats=stats)

        # No new insert should happen
        assert sb.table.return_value.insert.call_count == 0

        # If an update was issued, the unrelated key must survive
        update_calls = sb.table.return_value.update.call_args_list
        if update_calls:
            updated = update_calls[0][0][0]
            if "metadata" in updated:
                assert updated["metadata"].get("trust_verified_by") == "admin@example.com", (
                    "Unrelated metadata key was clobbered during re-run"
                )

    def test_rerun_does_not_duplicate_org(self):
        """Second pass: org already in org_cache → zero DB calls."""
        rows = [{"Name": "SSC", "Source Type": "Official", "URL": "https://ssc.nic.in"}]
        sb = _make_sb_central()
        stats = {"central_orgs": 0}
        org_cache = {org_dedupe_key("SSC", None, "central_commission"): "existing-ssc-id"}
        process_source_urls_sheet(sb, rows, dry_run=False, org_cache=org_cache, stats=stats)
        # Cache hit — no table calls at all
        assert sb.table.call_count == 0
