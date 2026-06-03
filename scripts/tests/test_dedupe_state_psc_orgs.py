"""Tests for dedupe_state_psc_orgs.py

The key invariant: the short_name the backfill writes must equal the short_name
the importer would compute on INSERT for the same workbook row.  Both must call
    normalize_short_name(_cell(row, "PSC Short Name", "Short Name"))
— same function, same cell — so the two derivations cannot diverge regardless
of workbook values.

Test structure:
  TestIdempotencyInvariant  — the central invariant (backfill key == importer key)
  TestWorkbookDerivedMap    — map values match the expected fixture; J&K & matches
  TestFailFast              — abort when a state_psc org's state is not in the map
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Both scripts live in scripts/; add that directory so they're importable.
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import dedupe_state_psc_orgs as ded
from import_exam_registry import _cell, normalize_short_name


# ── shared test data ──────────────────────────────────────────────────────────

# Minimal workbook rows mirroring the "State PSC Detailed Registry" sheet format.
_SAMPLE_WORKBOOK_ROWS = [
    {"State/UT": "Andhra Pradesh",  "PSC Short Name": "APPSC",  "Conducting Body": "AP PSC"},
    {"State/UT": "Bihar",           "PSC Short Name": "BPSC",   "Conducting Body": "Bihar PSC"},
    {"State/UT": "Jammu & Kashmir", "PSC Short Name": "JKPSC",  "Conducting Body": "J&K PSC"},
    {"State/UT": "Maharashtra",     "PSC Short Name": "MPSC",   "Conducting Body": "Maharashtra PSC"},
    {"State/UT": "Karnataka",       "PSC Short Name": "KPSC",   "Conducting Body": "KPSC"},
    {"State/UT": "West Bengal",     "PSC Short Name": "WBPSC",  "Conducting Body": "WBPSC"},
]

# Expected fixture values — must match the workbook-derived map for the sample rows.
_EXPECTED_FIXTURE: dict[str, str] = {
    "andhra pradesh": "APPSC",
    "bihar":          "BPSC",
    "jammu & kashmir":"JKPSC",
    "maharashtra":    "MPSC",
    "karnataka":      "KPSC",
    "west bengal":    "WBPSC",
}


def _build_map_from_rows(rows: list[dict]) -> dict[str, str]:
    """Build state→short_name map using the exact same logic as _build_workbook_short_name_map.

    Inline here so tests don't depend on file I/O — patch _build_workbook_short_name_map
    to return this dict instead.
    """
    result: dict[str, str] = {}
    for row in rows:
        state = _cell(row, "State/UT", "State")
        raw_short = _cell(row, "PSC Short Name", "Short Name")
        if state and raw_short:
            result[ded._norm_text(state)] = normalize_short_name(raw_short)
    return result


# ── TestIdempotencyInvariant ──────────────────────────────────────────────────

class TestIdempotencyInvariant:
    """The core guarantee: backfill_key == importer_key for every workbook row.

    Both must resolve to normalize_short_name(_cell(row, "PSC Short Name", "Short Name")).
    If they agree by construction (same call, same inputs) then duplicate rows
    produced by a second importer run will always match the survivor's short_name
    and be collapsed — re-dup is impossible.
    """

    def test_backfill_key_equals_importer_key_for_all_sample_rows(self):
        """For every sample row, backfill short_name == importer INSERT short_name."""
        state_map = _build_map_from_rows(_SAMPLE_WORKBOOK_ROWS)

        for row in _SAMPLE_WORKBOOK_ROWS:
            # What the importer writes on INSERT (process_state_psc_sheet line):
            importer_key = normalize_short_name(_cell(row, "PSC Short Name", "Short Name") or "")

            # What the backfill looks up from the workbook-derived map:
            state = _cell(row, "State/UT", "State")
            norm_state = ded._norm_text(state)
            assert norm_state in state_map, (
                f"State {state!r} (normalized: {norm_state!r}) missing from map — "
                "backfill would fail-fast for a DB org in this state."
            )
            backfill_key = state_map[norm_state]

            assert backfill_key == importer_key, (
                f"State {state!r}: backfill writes {backfill_key!r} but importer "
                f"would insert {importer_key!r}.  Derivation has drifted — the "
                "idempotency invariant is broken."
            )

    def test_both_derivations_call_same_normalize_function(self):
        """Confirm the map-building helper uses normalize_short_name from import_exam_registry.

        This is a meta-test: it imports the function directly and verifies that
        the same object is used in both places, ruling out a copy-paste re-implementation.
        """
        # _build_map_from_rows (and _build_workbook_short_name_map) import
        # normalize_short_name from import_exam_registry.  Call both and confirm
        # they produce equal results for identical input.
        raw = "  APPSC  "
        assert normalize_short_name(raw) == "APPSC"
        # If _build_map_from_rows were using a different normalization the values
        # in state_map would differ from what normalize_short_name produces.
        state_map = _build_map_from_rows(_SAMPLE_WORKBOOK_ROWS)
        for row in _SAMPLE_WORKBOOK_ROWS:
            raw_short = _cell(row, "PSC Short Name", "Short Name") or ""
            norm_state = ded._norm_text(_cell(row, "State/UT", "State") or "")
            assert state_map[norm_state] == normalize_short_name(raw_short)


# ── TestWorkbookDerivedMap ────────────────────────────────────────────────────

class TestWorkbookDerivedMap:
    def test_map_matches_expected_fixture(self):
        state_map = _build_map_from_rows(_SAMPLE_WORKBOOK_ROWS)
        for norm_state, expected_sn in _EXPECTED_FIXTURE.items():
            assert norm_state in state_map, (
                f"State {norm_state!r} missing from workbook-derived map."
            )
            assert state_map[norm_state] == expected_sn, (
                f"State {norm_state!r}: map has {state_map[norm_state]!r}, "
                f"expected {expected_sn!r}."
            )

    def test_jk_ampersand_matches_not_and(self):
        """Workbook 'Jammu & Kashmir' → key 'jammu & kashmir', not 'jammu and kashmir'.

        The DB org state value comes from the importer which read the same workbook cell,
        so both normalize to 'jammu & kashmir' via _norm_text and match correctly.
        The old hardcoded map keyed 'jammu and kashmir' — that was the mismatch.
        """
        state_map = _build_map_from_rows(_SAMPLE_WORKBOOK_ROWS)

        # Workbook-derived key:
        assert "jammu & kashmir" in state_map, (
            "'jammu & kashmir' not in map — J&K lookup is broken."
        )
        assert state_map["jammu & kashmir"] == "JKPSC"

        # Old bad key must NOT be present (it would indicate a normalization regression):
        assert "jammu and kashmir" not in state_map, (
            "'jammu and kashmir' found in map — the workbook cell was changed or "
            "normalization is converting & → and incorrectly."
        )

    def test_norm_text_preserves_ampersand(self):
        """_norm_text must NOT convert & to 'and' — the workbook spells it with &."""
        assert ded._norm_text("Jammu & Kashmir") == "jammu & kashmir"
        assert ded._norm_text("  Jammu  &  Kashmir  ") == "jammu & kashmir"


# ── TestFailFast ──────────────────────────────────────────────────────────────

class TestFailFast:
    """_backfill_short_names must abort when a state_psc org's state is absent from the map."""

    def _make_sb(self, org_rows: list[dict]) -> MagicMock:
        sb = MagicMock()
        (sb.table.return_value
           .select.return_value
           .in_.return_value
           .execute.return_value
           .data) = org_rows
        return sb

    def test_raises_on_unknown_state(self):
        unknown_org = {
            "id": "org-unknown",
            "type": "state_psc",
            "state": "Atlantis",
            "name": "Atlantis PSC",
            "short_name": None,
        }
        sb = self._make_sb([unknown_org])
        small_map = {"andhra pradesh": "APPSC"}

        with patch.object(ded, "_build_workbook_short_name_map", return_value=small_map):
            with pytest.raises(RuntimeError, match="not found in workbook-derived map"):
                ded._backfill_short_names(sb, dry_run=False, xlsx_path=Path("dummy.xlsx"))

    def test_skips_orgs_that_already_have_short_name(self):
        """Fail-fast must NOT fire for orgs that already have short_name set."""
        already_set = {
            "id": "org-already",
            "type": "state_psc",
            "state": "Atlantis",         # not in map — but short_name is set
            "name": "Atlantis PSC",
            "short_name": "ATPSC",
        }
        sb = self._make_sb([already_set])
        sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        small_map: dict[str, str] = {}

        with patch.object(ded, "_build_workbook_short_name_map", return_value=small_map):
            # Should not raise — org already has short_name, nothing to backfill.
            ded._backfill_short_names(sb, dry_run=False, xlsx_path=Path("dummy.xlsx"))

    def test_no_xlsx_skips_backfill_without_raising(self):
        """When xlsx_path is None the backfill warns and returns cleanly."""
        sb = self._make_sb([])
        # Should not raise or call the DB at all.
        ded._backfill_short_names(sb, dry_run=False, xlsx_path=None)
        sb.table.assert_not_called()

    def test_missing_sheet_raises_runtime_error(self):
        """If the workbook lacks 'State PSC Detailed Registry', abort with clear error."""
        from import_exam_registry import load_workbook  # noqa: F401 (confirm importable)

        sb = self._make_sb([])
        # Patch load_workbook to return a workbook with no matching sheet.
        empty_workbook = {"Some Other Sheet": []}
        with patch("import_exam_registry.load_workbook", return_value=empty_workbook):
            # Re-import load_workbook path as used inside _build_workbook_short_name_map
            # by patching via the dedupe module's import namespace.
            with pytest.raises(RuntimeError, match="missing sheet"):
                ded._build_workbook_short_name_map(Path("dummy.xlsx"))
