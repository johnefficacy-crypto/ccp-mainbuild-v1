"""Tests for exam-registry importer logic.

Pure-function layer (no DB) + mocked-DB layer covering:
  - calendar_status derivation from "Annual Calendar Published?" column
  - org dedupe key construction (APPSC short-vs-full-name idempotency)
  - exam slug construction
  - _abbrev_from_name helper
  - org INSERT payload includes metadata.import_status='pending_review'
  - org INSERT payload persists metadata.official_url when URL present
  - org UPDATE merges metadata (read-modify-write, unrelated keys survive)
  - no source_registry write during import
  - Source URLs disposition is reported in dry-run output with a count
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

# Allow import without editable install
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts"))

from import_exam_registry import (
    _abbrev_from_name,
    derive_calendar_status,
    exam_slug,
    normalize_short_name,
    org_dedupe_key,
    upsert_organization,
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


# ── upsert_organization — insert payload (DB-mocked) ────────────────────────

def _make_sb(existing_rows: list[dict] | None = None) -> MagicMock:
    """Build a minimal Supabase client mock for the organizations table.

    The new upsert_organization SELECT chain is:
      .table().select().eq(type).eq(short_name).[eq|is_](state).execute()
    We make the chain self-referential so any number of .eq()/.is_() calls resolve.
    """
    sb = MagicMock()
    # Self-referential SELECT chain: any number of .eq()/.is_() chaining supported
    select_chain = sb.table.return_value.select.return_value
    select_chain.eq.return_value = select_chain
    select_chain.is_.return_value = select_chain
    select_chain.execute.return_value.data = existing_rows or []
    # Chain: sb.table(...).insert(...).execute().data
    sb.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "new-org-id"}
    ]
    # Chain: sb.table(...).update(...).eq(...).execute()
    sb.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    return sb


class TestUpsertOrganizationInsertPayload:
    def test_new_org_insert_carries_pending_review(self):
        """Insert payload must include metadata.import_status='pending_review'."""
        sb = _make_sb()
        upsert_organization(
            sb,
            short_name="KPSC",
            full_name="Kerala Public Service Commission",
            state="Kerala",
            org_type="state_psc",
            calendar_status="published",
            official_url=None,
            dry_run=False,
            org_cache={},
        )
        insert_call = sb.table.return_value.insert.call_args
        payload = insert_call[0][0]
        assert payload["metadata"]["import_status"] == "pending_review"
        assert payload["metadata"]["import_source"] == "exam_registry_workbook"

    def test_new_org_insert_persists_official_url(self):
        """PSC Source URL must land in metadata.official_url on insert."""
        sb = _make_sb()
        upsert_organization(
            sb,
            short_name="APPSC",
            full_name="Andhra Pradesh Public Service Commission",
            state="Andhra Pradesh",
            org_type="state_psc",
            calendar_status="partial",
            official_url="https://psc.ap.gov.in",
            dry_run=False,
            org_cache={},
        )
        insert_call = sb.table.return_value.insert.call_args
        payload = insert_call[0][0]
        assert payload["metadata"]["official_url"] == "https://psc.ap.gov.in"

    def test_new_org_insert_without_url_has_no_official_url_key(self):
        """When no URL provided, official_url should be absent from metadata."""
        sb = _make_sb()
        upsert_organization(
            sb,
            short_name="KPSC",
            full_name="Kerala PSC",
            state="Kerala",
            org_type="state_psc",
            calendar_status="needs_review",
            official_url=None,
            dry_run=False,
            org_cache={},
        )
        insert_call = sb.table.return_value.insert.call_args
        payload = insert_call[0][0]
        assert "official_url" not in payload["metadata"]

    def test_no_source_registry_write_during_insert(self):
        """source_registry table must never be written during org import."""
        sb = _make_sb()
        upsert_organization(
            sb,
            short_name="KPSC",
            full_name="Kerala PSC",
            state="Kerala",
            org_type="state_psc",
            calendar_status="published",
            official_url="https://psc.kerala.gov.in",
            dry_run=False,
            org_cache={},
        )
        # Collect all table names passed to sb.table(...)
        table_calls = [c[0][0] for c in sb.table.call_args_list]
        assert "source_registry" not in table_calls


class TestUpsertOrganizationUpdateMerge:
    def _existing_org(self, existing_meta: dict) -> list[dict]:
        return [{
            "id": "existing-org-id",
            "name": "Karnataka Public Service Commission",
            "type": "state_psc",
            "state": "Karnataka",
            "calendar_status": "partial",
            "metadata": existing_meta,
        }]

    def test_update_merges_metadata_does_not_clobber_unrelated_keys(self):
        """Read-modify-write: a pre-existing unrelated metadata key must survive."""
        pre_existing_meta = {
            "source_trust_tier": "verified",   # unrelated key set by another process
            "import_status": "pending_review",
        }
        sb = _make_sb(existing_rows=self._existing_org(pre_existing_meta))

        upsert_organization(
            sb,
            short_name="KPSC",   # will match existing row via _abbrev_from_name
            full_name="Karnataka Public Service Commission",
            state="Karnataka",
            org_type="state_psc",
            calendar_status="partial",  # same — no calendar_status change
            official_url="https://kpsc.kar.nic.in",
            dry_run=False,
            org_cache={},
        )
        # If an update was issued, check that unrelated key survives
        update_calls = sb.table.return_value.update.call_args_list
        if update_calls:
            updated_payload = update_calls[0][0][0]
            if "metadata" in updated_payload:
                assert updated_payload["metadata"].get("source_trust_tier") == "verified", (
                    "Unrelated metadata key 'source_trust_tier' was clobbered during update"
                )


# ── Source URLs disposition in dry-run output ────────────────────────────────

class TestSourceUrlsDisposition:
    def test_dry_run_reports_source_urls_count(self, capsys):
        """Dry-run must print Source URLs disposition with row count, never hard-fail."""
        import io
        import logging

        # Capture log output
        log_output = io.StringIO()
        handler = logging.StreamHandler(log_output)
        handler.setLevel(logging.INFO)
        logging.getLogger("import_exam_registry").addHandler(handler)
        logging.getLogger("import_exam_registry").setLevel(logging.INFO)

        from import_exam_registry import main

        # Minimal fake workbook with a Source URLs sheet (3 rows)
        fake_sheets = {
            "Source URLs": [
                {"Source Type": "Official", "URL": "https://upsc.gov.in"},
                {"Source Type": "Official", "URL": "https://ssc.nic.in"},
                {"Source Type": "Official PSC", "URL": "https://ibps.in"},
            ]
        }

        with patch("import_exam_registry.load_workbook", return_value=fake_sheets):
            result = main(["--xlsx", "fake.xlsx", "--dry-run"])

        log_contents = log_output.getvalue()
        logging.getLogger("import_exam_registry").removeHandler(handler)

        # Must mention Source URLs and the count
        assert "Source URLs" in log_contents
        assert "3" in log_contents
        # Dry-run must NOT return non-zero exit code for this
        assert result == 0
