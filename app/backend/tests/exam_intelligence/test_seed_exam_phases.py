"""Tests for exam phase seeder slug derivation."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

# Allow imports without editable install
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts"))

from import_exam_registry import (
    _extract_state_from_body,
    _strip_leading_body_from_exam_name,
    exam_slug,
)
from seed_exam_phases import derive_seed_exam_slug, parse_phase_names, seed_phase_rows


def _importer_slug(exam_name: str, conducting_body: str) -> str:
    state_prefix = _extract_state_from_body(conducting_body)
    clean_exam_name = _strip_leading_body_from_exam_name(exam_name, conducting_body)
    return exam_slug(state_prefix, clean_exam_name)


class TestSeedExamPhaseSlugDerivation:
    def test_jammu_kashmir_combined_competitive_matches_importer(self):
        exam_name = "Jammu & Kashmir PSC ù Combined Competitive Examination"
        conducting_body = "Jammu & Kashmir PSC"

        slug, clean_exam_name = derive_seed_exam_slug(exam_name, conducting_body)

        assert slug == _importer_slug(exam_name, conducting_body)
        assert clean_exam_name == "Combined Competitive Examination"
        assert slug == "jammu-kashmir-combined-competitive-examination"
        assert "national-jammu-kashmir-psc" not in slug
        assert "jammu-kashmir-jammu-kashmir" not in slug

    def test_jammu_kashmir_civil_judge_matches_importer(self):
        exam_name = "Jammu & Kashmir PSC ù Civil Judge / Judicial Service"
        conducting_body = "Jammu & Kashmir PSC"

        slug, clean_exam_name = derive_seed_exam_slug(exam_name, conducting_body)

        assert slug == _importer_slug(exam_name, conducting_body)
        assert clean_exam_name == "Civil Judge / Judicial Service"
        assert slug == "jammu-kashmir-civil-judge-judicial-service"
        assert "national-jammu-kashmir-psc" not in slug
        assert "jammu-kashmir-jammu-kashmir" not in slug

    def test_jammu_kashmir_departmental_matches_importer(self):
        exam_name = "Jammu & Kashmir PSC ù Departmental Examinations"
        conducting_body = "Jammu & Kashmir PSC"

        slug, clean_exam_name = derive_seed_exam_slug(exam_name, conducting_body)

        assert slug == _importer_slug(exam_name, conducting_body)
        assert clean_exam_name == "Departmental Examinations"
        assert slug == "jammu-kashmir-departmental-examinations"
        assert "national-jammu-kashmir-psc" not in slug
        assert "jammu-kashmir-jammu-kashmir" not in slug

    def test_assistant_engineer_lecturer_medical_officer_matches_importer(self):
        exam_name = "Assistant Engineer / Lecturer / Medical Officer"
        conducting_body = "Rajasthan PSC"

        slug, clean_exam_name = derive_seed_exam_slug(exam_name, conducting_body)

        assert slug == _importer_slug(exam_name, conducting_body)
        assert clean_exam_name == exam_name
        assert slug == "rajasthan-assistant-engineer-lecturer-medical-officer"

    def test_mpsc_rajyaseva_matches_importer(self):
        exam_name = "MPSC Rajyaseva (Maharashtra Civil Services)"
        conducting_body = "MPSC"

        slug, clean_exam_name = derive_seed_exam_slug(exam_name, conducting_body)

        assert slug == _importer_slug(exam_name, conducting_body)
        assert clean_exam_name == exam_name
        assert slug == "maharashtra-mpsc-rajyaseva-maharashtra-civil-services"
        assert not slug.startswith("madhya-pradesh")

    def test_upsc_civil_services_matches_importer(self):
        exam_name = "UPSC Civil Services Examination"
        conducting_body = "UPSC"

        slug, clean_exam_name = derive_seed_exam_slug(exam_name, conducting_body)

        assert slug == _importer_slug(exam_name, conducting_body)
        assert clean_exam_name == exam_name
        assert slug == "national-upsc-civil-services-examination"

    def test_normal_national_row_without_body_prefix_matches_importer(self):
        exam_name = "Civil Services Examination"
        conducting_body = "UPSC"

        slug, clean_exam_name = derive_seed_exam_slug(exam_name, conducting_body)

        assert slug == _importer_slug(exam_name, conducting_body)
        assert clean_exam_name == exam_name
        assert slug == "national-civil-services-examination"


class TestParsePhaseNames:
    def test_splits_common_phase_separators(self):
        assert parse_phase_names("Prelims; Mains / Interview") == [
            "Prelims",
            "Mains",
            "Interview",
        ]


class TestSeedPhaseRows:
    def test_live_insert_marks_stub_for_date_authoring_without_phase_window(self):
        sb = MagicMock()
        table = sb.table.return_value
        # _find_exam_id select chain
        table.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"id": "exam-1", "slug": "jammu-kashmir-combined-competitive-examination"}
        ]
        # _phase_exists adds a second eq before limit; return no existing phase.
        table.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

        seed_phase_rows(
            sb,
            [(
                "jammu-kashmir-combined-competitive-examination",
                "Combined Competitive Examination",
                ["Prelims"],
            )],
            dry_run=False,
        )

        payload = table.insert.call_args[0][0]
        assert payload["metadata"]["import_source"] == "exam_registry_workbook"
        assert payload["metadata"]["needs_phase_date_authoring"] is True
        assert "phase_window" not in payload["metadata"]
