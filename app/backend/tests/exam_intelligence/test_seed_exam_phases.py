"""Tests for exam phase seeder slug derivation."""
from __future__ import annotations

import sys
from pathlib import Path

# Allow imports without editable install
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts"))

from import_exam_registry import (
    _extract_state_from_body,
    _strip_leading_body_from_exam_name,
    exam_slug,
)
from seed_exam_phases import derive_seed_exam_slug, parse_phase_names


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
