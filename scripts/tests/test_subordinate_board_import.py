"""Tests for import_subordinate_boards.py.

Coverage:
  - sentinel detection: blank / "No single SSB" / "None" / "N/A" / variant
  - real-board rows: correct payload shape, calendar_status always 'needs_review'
  - short_name comes from the imported normalize_short_name, not a reimplementation
  - idempotency: second run on same rows → 0 new inserts, only metadata updates
  - fail-fast: real Board Short Name + missing Conducting Body → ValueError
  - fail-fast: real Board Short Name + missing State/UT → ValueError
  - dry-run: no DB calls made at all
  - scope guard: accessing a forbidden table raises AssertionError
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Allow import without editable install
_SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS))

from import_exam_registry import _cell, normalize_short_name
from import_subordinate_boards import (
    _FORBIDDEN_TABLES,
    _SHEET_NAME,
    _guarded_supabase,
    _is_sentinel,
    process_subordinate_boards_sheet,
)


# ── helpers ────────────────────────────────────────────────────────────────────

def _make_row(**kwargs) -> dict:
    """Build a minimal sheet row dict, filling defaults for required columns."""
    defaults = {
        "State/UT": "Bihar",
        "Board Short Name": "BSSC",
        "Conducting Body": "Bihar Staff Selection Commission",
        "Exam / Sub-exam Family": "State Services",
        "Purpose / Posts": "Clerical",
        "Typical Phases": "Written + Interview",
        "Typical Cycle": "Annual",
        "Exam Type": "Recruitment",
        "Annual Calendar Published?": "No",
        "Board Source URL": "https://bssc.bihar.gov.in",
        "Calendar / Schedule URL": None,
        "Coverage Note": None,
    }
    defaults.update(kwargs)
    return defaults


def _mock_sb(existing_rows: list | None = None) -> MagicMock:
    """Return a mock Supabase client whose .table().select().eq*() chain
    returns existing_rows (default: empty → triggers insert path)."""
    sb = MagicMock()
    table_mock = MagicMock()
    sb.table.return_value = table_mock

    # SELECT chain: .select().eq().eq().eq().execute().data
    query_chain = MagicMock()
    query_chain.select.return_value = query_chain
    query_chain.eq.return_value = query_chain
    query_chain.execute.return_value.data = existing_rows or []
    table_mock.select.return_value = query_chain

    # INSERT chain: .insert(payload).execute().data
    insert_chain = MagicMock()
    insert_chain.execute.return_value.data = [{"id": "new-uuid"}]
    table_mock.insert.return_value = insert_chain

    # UPDATE chain: .update(payload).eq(...).execute()
    update_chain = MagicMock()
    update_chain.eq.return_value = update_chain
    table_mock.update.return_value = update_chain

    return sb


# ── sentinel detection ─────────────────────────────────────────────────────────

class TestIsSentinel:
    def test_blank_string(self):
        assert _is_sentinel("") is True

    def test_none_value(self):
        assert _is_sentinel(None) is True

    def test_whitespace_only(self):
        assert _is_sentinel("   ") is True

    def test_no_single_ssb_exact(self):
        assert _is_sentinel("No single SSB") is True

    def test_no_single_ssb_in_parens(self):
        assert _is_sentinel("(No single SSB)") is True

    def test_no_single_ssb_variant_case(self):
        assert _is_sentinel("NO SINGLE SSB") is True

    def test_none_literal(self):
        assert _is_sentinel("None") is True

    def test_na_literal(self):
        assert _is_sentinel("N/A") is True

    def test_not_applicable(self):
        assert _is_sentinel("Not Applicable") is True

    def test_real_abbreviation(self):
        assert _is_sentinel("BSSC") is False

    def test_real_fused_value(self):
        assert _is_sentinel("SLRC(ADRE)") is False

    def test_multiword_short_name(self):
        assert _is_sentinel("UP SSSC") is False


# ── short_name derivation uses the imported function ──────────────────────────

class TestShortNameDerivation:
    def test_uses_imported_normalize(self):
        # Verify the function imported from import_exam_registry is the real one.
        assert normalize_short_name("BSSC") == "BSSC"
        assert normalize_short_name("UP SSSC") == "UPSSSC"
        assert normalize_short_name("SLRC (ADRE)") == "SLRC(ADRE)"

    def test_short_name_in_inserted_payload(self):
        sb = _mock_sb()
        rows = [_make_row(**{"Board Short Name": "UP SSSC"})]
        process_subordinate_boards_sheet(sb, rows, False, _cell, normalize_short_name)
        insert_call = sb.table.return_value.insert.call_args
        payload = insert_call[0][0]
        assert payload["short_name"] == "UPSSSC"

    def test_fused_slrc_adre(self):
        sb = _mock_sb()
        rows = [_make_row(**{"Board Short Name": "SLRC (ADRE)"})]
        process_subordinate_boards_sheet(sb, rows, False, _cell, normalize_short_name)
        insert_call = sb.table.return_value.insert.call_args
        assert insert_call[0][0]["short_name"] == "SLRC(ADRE)"


# ── calendar_status is always needs_review ────────────────────────────────────

class TestCalendarStatus:
    @pytest.mark.parametrize("raw_calendar", [
        "Yes / annual calendar",
        "No",
        "Partial",
        "Tentative",
        "",
        None,
        "Unknown / ad-hoc",
    ])
    def test_always_needs_review(self, raw_calendar):
        sb = _mock_sb()
        rows = [_make_row(**{"Annual Calendar Published?": raw_calendar})]
        process_subordinate_boards_sheet(sb, rows, False, _cell, normalize_short_name)
        insert_call = sb.table.return_value.insert.call_args
        assert insert_call[0][0]["calendar_status"] == "needs_review"

    def test_raw_cell_preserved_in_metadata(self):
        sb = _mock_sb()
        rows = [_make_row(**{"Annual Calendar Published?": "Yes / annual calendar"})]
        process_subordinate_boards_sheet(sb, rows, False, _cell, normalize_short_name)
        insert_call = sb.table.return_value.insert.call_args
        meta = insert_call[0][0]["metadata"]
        assert meta["annual_calendar_published"] == "Yes / annual calendar"


# ── idempotency ────────────────────────────────────────────────────────────────

class TestIdempotency:
    def test_second_run_produces_zero_inserts(self):
        """Simulates running the importer twice on the same row.
        First run: existing_rows=[] → insert.
        Second run: existing_rows=[{...}] → update metadata, no insert.
        """
        existing = [{"id": "existing-uuid", "metadata": {"import_status": "pending_review"}}]
        sb = _mock_sb(existing_rows=existing)
        rows = [_make_row()]
        stats = process_subordinate_boards_sheet(sb, rows, False, _cell, normalize_short_name)
        # No insert call should have been made
        sb.table.return_value.insert.assert_not_called()
        assert stats["imported"] == 0
        assert stats["updated"] == 1

    def test_first_run_inserts(self):
        sb = _mock_sb(existing_rows=[])
        rows = [_make_row()]
        stats = process_subordinate_boards_sheet(sb, rows, False, _cell, normalize_short_name)
        sb.table.return_value.insert.assert_called_once()
        assert stats["imported"] == 1
        assert stats["updated"] == 0

    def test_metadata_update_merges_without_clobbering(self):
        existing = [{"id": "ex-uuid", "metadata": {"custom_key": "preserved"}}]
        sb = _mock_sb(existing_rows=existing)
        rows = [_make_row()]
        process_subordinate_boards_sheet(sb, rows, False, _cell, normalize_short_name)
        update_call = sb.table.return_value.update.call_args
        merged = update_call[0][0]["metadata"]
        assert merged["custom_key"] == "preserved"
        assert merged["import_status"] == "pending_review"


# ── sentinel skip ──────────────────────────────────────────────────────────────

class TestSentinelSkip:
    def test_no_single_ssb_skipped_not_inserted(self):
        sb = _mock_sb()
        rows = [_make_row(**{"Board Short Name": "No single SSB"})]
        stats = process_subordinate_boards_sheet(sb, rows, False, _cell, normalize_short_name)
        sb.table.return_value.insert.assert_not_called()
        assert stats["imported"] == 0
        assert len(stats["skipped_non_board_rows"]) == 1

    def test_blank_short_name_skipped(self):
        sb = _mock_sb()
        rows = [_make_row(**{"Board Short Name": ""})]
        stats = process_subordinate_boards_sheet(sb, rows, False, _cell, normalize_short_name)
        assert len(stats["skipped_non_board_rows"]) == 1

    def test_na_skipped(self):
        sb = _mock_sb()
        rows = [_make_row(**{"Board Short Name": "N/A"})]
        stats = process_subordinate_boards_sheet(sb, rows, False, _cell, normalize_short_name)
        assert len(stats["skipped_non_board_rows"]) == 1

    def test_skip_does_not_fail_even_when_body_blank(self):
        """Sentinel rows may also lack conducting body — must skip, not fail-fast."""
        sb = _mock_sb()
        rows = [_make_row(**{"Board Short Name": "None", "Conducting Body": None})]
        # Should not raise
        stats = process_subordinate_boards_sheet(sb, rows, False, _cell, normalize_short_name)
        assert len(stats["skipped_non_board_rows"]) == 1


# ── fail-fast for real-board rows ─────────────────────────────────────────────

class TestFailFast:
    def test_missing_conducting_body_raises(self):
        sb = _mock_sb()
        rows = [_make_row(**{"Conducting Body": None})]
        with pytest.raises(ValueError, match="Conducting Body is blank"):
            process_subordinate_boards_sheet(sb, rows, False, _cell, normalize_short_name)

    def test_missing_state_raises(self):
        sb = _mock_sb()
        rows = [_make_row(**{"State/UT": None})]
        with pytest.raises(ValueError, match="State/UT is blank"):
            process_subordinate_boards_sheet(sb, rows, False, _cell, normalize_short_name)

    def test_empty_string_conducting_body_raises(self):
        sb = _mock_sb()
        rows = [_make_row(**{"Conducting Body": "   "})]
        with pytest.raises(ValueError, match="Conducting Body is blank"):
            process_subordinate_boards_sheet(sb, rows, False, _cell, normalize_short_name)


# ── dry-run ────────────────────────────────────────────────────────────────────

class TestDryRun:
    def test_dry_run_makes_no_db_calls(self):
        sb = _mock_sb()
        rows = [_make_row(), _make_row(**{"Board Short Name": "APPSC", "State/UT": "AP"})]
        stats = process_subordinate_boards_sheet(sb, rows, True, _cell, normalize_short_name)
        sb.table.assert_not_called()
        assert stats["imported"] == 2

    def test_dry_run_counts_sentinels(self):
        sb = _mock_sb()
        rows = [
            _make_row(),
            _make_row(**{"Board Short Name": "No single SSB"}),
        ]
        stats = process_subordinate_boards_sheet(sb, rows, True, _cell, normalize_short_name)
        assert stats["imported"] == 1
        assert len(stats["skipped_non_board_rows"]) == 1


# ── scope guard ────────────────────────────────────────────────────────────────

class TestScopeGuard:
    @pytest.mark.parametrize("forbidden", sorted(_FORBIDDEN_TABLES))
    def test_forbidden_table_raises(self, forbidden):
        raw_sb = MagicMock()
        guarded = _guarded_supabase(raw_sb)
        with pytest.raises(AssertionError, match=forbidden):
            guarded.table(forbidden)

    def test_organizations_allowed(self):
        raw_sb = MagicMock()
        guarded = _guarded_supabase(raw_sb)
        # Should not raise
        guarded.table("organizations")


# ── org payload shape ─────────────────────────────────────────────────────────

class TestPayloadShape:
    def test_insert_payload_has_required_fields(self):
        sb = _mock_sb()
        rows = [_make_row()]
        process_subordinate_boards_sheet(sb, rows, False, _cell, normalize_short_name)
        payload = sb.table.return_value.insert.call_args[0][0]
        assert payload["type"] == "subordinate_board"
        assert payload["calendar_status"] == "needs_review"
        assert payload["is_active"] is True
        assert payload["name"] == "Bihar Staff Selection Commission"
        assert payload["state"] == "Bihar"

    def test_metadata_contains_import_keys(self):
        sb = _mock_sb()
        rows = [_make_row()]
        process_subordinate_boards_sheet(sb, rows, False, _cell, normalize_short_name)
        meta = sb.table.return_value.insert.call_args[0][0]["metadata"]
        assert meta["import_source"] == "subordinate_boards_workbook"
        assert meta["import_status"] == "pending_review"
        assert meta["source_sheet"] == _SHEET_NAME
        assert "source_urls" in meta

    def test_metadata_source_urls_shape(self):
        sb = _mock_sb()
        rows = [_make_row(**{
            "Board Source URL": "https://board.gov",
            "Calendar / Schedule URL": "https://cal.gov",
        })]
        process_subordinate_boards_sheet(sb, rows, False, _cell, normalize_short_name)
        meta = sb.table.return_value.insert.call_args[0][0]["metadata"]
        assert meta["source_urls"]["board"] == "https://board.gov"
        assert meta["source_urls"]["calendar"] == "https://cal.gov"
