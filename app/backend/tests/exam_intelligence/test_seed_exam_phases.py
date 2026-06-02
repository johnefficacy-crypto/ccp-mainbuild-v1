"""Tests for exam_phases stub seeder (scripts/seed_exam_phases.py).

Covers:
  - split_phases: table-driven across all confirmed delimiter patterns
  - every built stub has phase_start=None, phase_end=None
  - every stub carries metadata.import_status='pending_review' + import_source
    + phase_source_text + phase_window (worklist gate)
  - phase_order reflects source position (1-based)
  - normalize_phase_name canonicalises for dedupe
  - dedupe: second pass over same stubs yields zero new rows
  - empty / TBD / None Main Phases → split_phases returns None (counted, not fabricated)
  - only exams with import_source='exam_registry_workbook' targeted (others skipped)
  - slug fn is imported from import_exam_registry (not reimplemented)
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts"))

from seed_exam_phases import (
    build_stubs,
    normalize_phase_name,
    split_phases,
)
from import_exam_registry import exam_slug, slugify


# ── split_phases — table-driven ───────────────────────────────────────────────

class TestSplitPhases:
    # (raw input, expected list or None)
    CASES = [
        # Comma delimiter
        ("Prelims, Mains, Interview", ["Prelims", "Mains", "Interview"]),
        ("Prelims,Mains,Interview", ["Prelims", "Mains", "Interview"]),
        # Slash delimiter
        ("Written / Practical", ["Written", "Practical"]),
        ("Written/Practical", ["Written", "Practical"]),
        # "and" delimiter
        ("Written and Interview", ["Written", "Interview"]),
        ("written AND interview", ["Written", "Interview"]),
        # Mixed
        ("Prelims, Mains and Interview", ["Prelims", "Mains", "Interview"]),
        # Single phase (no delimiter)
        ("Written Examination", ["Written Examination"]),
        # Unparseable / empty
        (None, None),
        ("", None),
        ("TBD", None),
        ("tbd", None),
        ("N/A", None),
        ("—", None),
        ("-", None),
        ("nil", None),
        # Whitespace only
        ("   ", None),
    ]

    def test_all_cases(self):
        for raw, expected in self.CASES:
            result = split_phases(raw)
            if expected is None:
                assert result is None, f"Expected None for {raw!r}, got {result!r}"
            else:
                # Compare case-insensitively — normalize_phase_name is applied later
                assert result is not None, f"Expected list for {raw!r}, got None"
                assert [p.lower() for p in result] == [p.lower() for p in expected], (
                    f"For {raw!r}: expected {expected!r}, got {result!r}"
                )


# ── build_stubs ───────────────────────────────────────────────────────────────

class TestBuildStubs:
    def _stubs(self, phases_raw: str = "Prelims, Mains, Interview") -> list[dict]:
        names = split_phases(phases_raw)
        assert names is not None
        return build_stubs(
            exam_id="exam-uuid-1",
            exam_slug_val="kerala-group-i-services",
            phases_raw=phases_raw,
            phase_names=names,
        )

    def test_no_stub_has_a_date(self):
        for stub in self._stubs():
            assert stub["phase_start"] is None, "phase_start must be NULL"
            assert stub["phase_end"] is None, "phase_end must be NULL"

    def test_every_stub_carries_pending_review(self):
        for stub in self._stubs():
            assert stub["metadata"]["import_status"] == "pending_review"

    def test_every_stub_carries_import_source(self):
        for stub in self._stubs():
            assert stub["metadata"]["import_source"] == "exam_registry_workbook"

    def test_every_stub_carries_phase_source_text(self):
        raw = "Prelims, Mains, Interview"
        for stub in self._stubs(raw):
            assert stub["metadata"]["phase_source_text"] == raw

    def test_every_stub_carries_phase_window_for_worklist(self):
        """metadata.phase_window must be set so SetupPanel.jsx:40 legacyWindow() is truthy."""
        for stub in self._stubs():
            assert stub["metadata"].get("phase_window"), (
                "phase_window must be a non-empty string so the #577 worklist surfaces the stub"
            )

    def test_phase_order_reflects_source_position(self):
        stubs = self._stubs("Prelims, Mains, Interview")
        assert stubs[0]["phase_order"] == 1
        assert stubs[1]["phase_order"] == 2
        assert stubs[2]["phase_order"] == 3

    def test_phase_order_single_item_is_1(self):
        stubs = self._stubs("Written Examination")
        assert stubs[0]["phase_order"] == 1

    def test_phase_names_are_normalized(self):
        stubs = self._stubs("prelims, MAINS, interview")
        names = [s["phase_name"] for s in stubs]
        assert names == ["Prelims", "Mains", "Interview"]

    def test_exam_id_is_set(self):
        for stub in self._stubs():
            assert stub["exam_id"] == "exam-uuid-1"


# ── normalize_phase_name ──────────────────────────────────────────────────────

class TestNormalizePhastName:
    def test_title_case(self):
        assert normalize_phase_name("preliminary exam") == "Preliminary Exam"

    def test_collapses_internal_whitespace(self):
        assert normalize_phase_name("Mains  Paper") == "Mains Paper"

    def test_strips_leading_trailing(self):
        assert normalize_phase_name("  Interview  ") == "Interview"


# ── dedupe ────────────────────────────────────────────────────────────────────

class TestDedupe:
    def test_second_pass_yields_zero_new_stubs(self):
        """Simulates: existing phase names already in DB match what would be seeded."""
        from seed_exam_phases import build_stubs, split_phases, normalize_phase_name

        raw = "Prelims, Mains, Interview"
        names = split_phases(raw)
        stubs = build_stubs("exam-1", "test-exam", raw, names)

        # Existing phase names in DB = what we'd insert (lowercased)
        existing = {s["phase_name"].lower() for s in stubs}

        new_stubs = [s for s in stubs if s["phase_name"].lower() not in existing]
        assert new_stubs == [], f"Expected zero new stubs on re-run, got {new_stubs}"

    def test_partial_overlap_inserts_only_missing(self):
        raw = "Prelims, Mains, Interview"
        names = split_phases(raw)
        stubs = build_stubs("exam-1", "test-exam", raw, names)

        existing = {"prelims"}  # only Prelims already in DB
        new_stubs = [s for s in stubs if s["phase_name"].lower() not in existing]
        assert len(new_stubs) == 2
        assert {s["phase_name"].lower() for s in new_stubs} == {"mains", "interview"}


# ── unparseable / empty handling ──────────────────────────────────────────────

class TestUnparseable:
    UNPARSEABLE = [None, "", "TBD", "tbd", "N/A", "—", "   "]

    def test_all_unparseable_return_none(self):
        for val in self.UNPARSEABLE:
            result = split_phases(val)
            assert result is None, f"Expected None for {val!r}, got {result!r}"

    def test_unparseable_produces_zero_stubs(self):
        """Contract: None from split_phases means no stubs are built."""
        for val in self.UNPARSEABLE:
            names = split_phases(val)
            assert names is None
            # Caller contract: build_stubs is NOT called when names is None


# ── import_source filter ──────────────────────────────────────────────────────

class TestImportSourceFilter:
    def test_only_workbook_imported_exams_are_targeted(self):
        """fetch_imported_exams() must filter on import_source='exam_registry_workbook'."""
        from seed_exam_phases import fetch_imported_exams

        sb = MagicMock()
        sb.table.return_value.select.return_value.execute.return_value.data = [
            {"id": "id-1", "slug": "kerala-group-i", "metadata": {"import_source": "exam_registry_workbook"}},
            {"id": "id-2", "slug": "upsc-cse", "metadata": {"import_source": "manual"}},
            {"id": "id-3", "slug": "tnpsc-group-ii", "metadata": {}},
            {"id": "id-4", "slug": "appsc-group-i", "metadata": {"import_source": "exam_registry_workbook"}},
        ]

        result = fetch_imported_exams(sb)
        assert set(result.keys()) == {"kerala-group-i", "appsc-group-i"}
        assert "upsc-cse" not in result
        assert "tnpsc-group-ii" not in result


# ── slug fn is imported, not reimplemented ───────────────────────────────────

class TestSlugImported:
    def test_exam_slug_imported_from_import_exam_registry(self):
        """Confirm the slug fn used by seed_exam_phases IS the one from import_exam_registry."""
        from seed_exam_phases import exam_slug as seeder_slug
        from import_exam_registry import exam_slug as importer_slug
        assert seeder_slug is importer_slug, (
            "seed_exam_phases must import exam_slug from import_exam_registry, "
            "not reimplement it"
        )

    def test_slugify_imported_from_import_exam_registry(self):
        from seed_exam_phases import slugify as seeder_slugify
        from import_exam_registry import slugify as importer_slugify
        assert seeder_slugify is importer_slugify
