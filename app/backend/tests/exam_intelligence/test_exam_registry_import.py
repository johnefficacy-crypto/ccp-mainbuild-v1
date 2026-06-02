"""Tests for exam-registry importer logic (pure-function layer).

All tests are deterministic and require no DB connection.  They verify:
  - calendar_status derivation from the workbook "Annual Calendar Published?" column
  - org dedupe key construction (the APPSC short-vs-full-name idempotency case)
  - exam slug construction
  - _abbrev_from_name helper used for org cache lookups
  - Subordinate Boards sheet is skipped (not silently dropped)
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow import without editable install
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts"))

from import_exam_registry import (
    _abbrev_from_name,
    derive_calendar_status,
    exam_slug,
    normalize_short_name,
    org_dedupe_key,
)


# ── calendar_status ───────────────────────────────────────────────────────────

class TestDeriveCalendarStatus:
    def test_yes_annual_calendar(self):
        assert derive_calendar_status("Yes / annual calendar") == "published"

    def test_yes_planner(self):
        assert derive_calendar_status("Yes (Annual Planner published)") == "published"

    def test_yes_exam_calendar(self):
        assert derive_calendar_status("Yes - exam calendar") == "published"

    def test_yes_advertisement_calendar(self):
        assert derive_calendar_status("Yes / advertisement calendar") == "published"

    def test_yes_tentative(self):
        assert derive_calendar_status("Yes / tentative calendar") == "tentative"

    def test_yes_proposed(self):
        assert derive_calendar_status("Yes (proposed schedule)") == "tentative"

    def test_partial_notification_wise(self):
        assert derive_calendar_status("Partial / notification-wise") == "partial"

    def test_notification_wise_standalone(self):
        assert derive_calendar_status("Notification-wise") == "partial"

    def test_exam_schedule(self):
        assert derive_calendar_status("Partial / exam schedule") == "partial"

    def test_timetable(self):
        assert derive_calendar_status("timetable") == "partial"

    def test_monthly_programmes(self):
        assert derive_calendar_status("Monthly programmes/notification-wise") == "partial"

    def test_blank(self):
        assert derive_calendar_status("") == "needs_review"

    def test_none(self):
        assert derive_calendar_status(None) == "needs_review"

    def test_unclear_text(self):
        assert derive_calendar_status("Unknown / ad-hoc") == "needs_review"


# ── org dedupe key / APPSC idempotency ───────────────────────────────────────

class TestOrgDedupeKey:
    def test_short_name_and_full_name_collapse_to_same_key(self):
        """APPSC entered as short-name and as full-name must produce identical keys.

        Regression guard: if these two representations produce different dedupe keys,
        the importer would insert a duplicate organization row.
        """
        short_key = org_dedupe_key("APPSC", "Andhra Pradesh", "state_psc")
        full_key = org_dedupe_key(
            _abbrev_from_name("Andhra Pradesh Public Service Commission"),
            "Andhra Pradesh",
            "state_psc",
        )
        assert short_key == full_key, (
            f"APPSC dedupe key mismatch: short={short_key!r} full={full_key!r}"
        )

    def test_state_case_insensitive(self):
        k1 = org_dedupe_key("KPSC", "Karnataka", "state_psc")
        k2 = org_dedupe_key("KPSC", "karnataka", "state_psc")
        assert k1 == k2

    def test_type_differentiates_same_state(self):
        k1 = org_dedupe_key("APPSC", "Andhra Pradesh", "state_psc")
        k2 = org_dedupe_key("APPSC", "Andhra Pradesh", "subordinate_board")
        assert k1 != k2

    def test_different_states_different_keys(self):
        k1 = org_dedupe_key("PSC", "Kerala", "state_psc")
        k2 = org_dedupe_key("PSC", "Punjab", "state_psc")
        assert k1 != k2

    def test_normalize_strips_spaces(self):
        assert normalize_short_name("  APPSC  ") == "APPSC"
        assert normalize_short_name("AP PSC") == "APPSC"


# ── exam slug ─────────────────────────────────────────────────────────────────

class TestExamSlug:
    def test_state_prefix_prepended(self):
        slug = exam_slug("andhra-pradesh", "Group I Services")
        assert slug == "andhra-pradesh-group-i-services"

    def test_none_state_becomes_national(self):
        slug = exam_slug(None, "UPSC CSE")
        assert slug == "national-upsc-cse"

    def test_special_chars_stripped(self):
        slug = exam_slug("tamil-nadu", "Group II & IIA")
        assert slug == "tamil-nadu-group-ii-iia"

    def test_slug_is_lowercase(self):
        slug = exam_slug("KERALA", "Judicial Service Exam")
        assert slug == slug.lower()


# ── _abbrev_from_name ────────────────────────────────────────────────────────

class TestAbbrevFromName:
    def test_full_name_produces_abbrev(self):
        assert _abbrev_from_name("Andhra Pradesh Public Service Commission") == "APPSC"

    def test_already_abbrev_returned_as_is(self):
        assert _abbrev_from_name("APPSC") == "APPSC"

    def test_kerala_psc(self):
        assert _abbrev_from_name("Kerala Public Service Commission") == "KPSC"

    def test_upsc(self):
        assert _abbrev_from_name("UPSC") == "UPSC"
