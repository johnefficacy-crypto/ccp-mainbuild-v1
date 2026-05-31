import pytest
from app.exam_intelligence.extraction.dispatch import (
    StructuralFormat, ExamIdentity,
    EXAM_TO_FORMAT_DEFAULT, ELIGIBLE_FORMATS_V1,
    infer_format_from_identity, is_extractable_by_v1,
)


class TestExamToFormatMapping:
    def test_prelims_gs1_maps_to_mcq_bilingual(self):
        assert (EXAM_TO_FORMAT_DEFAULT[ExamIdentity.UPSC_CSE_PRELIMS_GS1]
                == StructuralFormat.MCQ_BILINGUAL_TWO_COLUMN)

    def test_prelims_csat_maps_to_mcq_bilingual(self):
        assert (EXAM_TO_FORMAT_DEFAULT[ExamIdentity.UPSC_CSE_PRELIMS_CSAT]
                == StructuralFormat.MCQ_BILINGUAL_TWO_COLUMN)

    def test_mains_essay_maps_to_essay_long_form(self):
        assert (EXAM_TO_FORMAT_DEFAULT[ExamIdentity.UPSC_CSE_MAINS_ESSAY]
                == StructuralFormat.ESSAY_LONG_FORM)

    def test_all_mains_gs_papers_map_to_essay(self):
        for ident in [
            ExamIdentity.UPSC_CSE_MAINS_GS1,
            ExamIdentity.UPSC_CSE_MAINS_GS2,
            ExamIdentity.UPSC_CSE_MAINS_GS3,
            ExamIdentity.UPSC_CSE_MAINS_GS4,
        ]:
            assert (EXAM_TO_FORMAT_DEFAULT[ident]
                    == StructuralFormat.ESSAY_LONG_FORM)

    def test_non_technical_optionals_map_to_essay(self):
        for ident in [
            ExamIdentity.UPSC_CSE_MAINS_OPTIONAL_SOCIOLOGY,
            ExamIdentity.UPSC_CSE_MAINS_OPTIONAL_PSIR,
            ExamIdentity.UPSC_CSE_MAINS_OPTIONAL_HISTORY,
            ExamIdentity.UPSC_CSE_MAINS_OPTIONAL_ANTHROPOLOGY,
        ]:
            assert (EXAM_TO_FORMAT_DEFAULT[ident]
                    == StructuralFormat.ESSAY_LONG_FORM)

    def test_technical_optional_maps_to_figures(self):
        assert (EXAM_TO_FORMAT_DEFAULT[ExamIdentity.UPSC_CSE_MAINS_OPTIONAL_TECHNICAL]
                == StructuralFormat.TECHNICAL_WITH_FIGURES)

    def test_unknown_identity_maps_to_unknown_format(self):
        assert (EXAM_TO_FORMAT_DEFAULT[ExamIdentity.UNKNOWN]
                == StructuralFormat.UNKNOWN)

    def test_every_exam_identity_has_a_mapping(self):
        """Compile-time-equivalent check: no enum value goes unmapped."""
        for identity in ExamIdentity:
            assert identity in EXAM_TO_FORMAT_DEFAULT, (
                f"{identity} has no entry in EXAM_TO_FORMAT_DEFAULT. "
                f"Adding a new ExamIdentity value requires updating "
                f"dispatch.py."
            )


class TestEligibilityV1:
    def test_only_mcq_bilingual_is_eligible(self):
        assert ELIGIBLE_FORMATS_V1 == frozenset({
            StructuralFormat.MCQ_BILINGUAL_TWO_COLUMN,
        })

    def test_essay_not_eligible_for_v1(self):
        assert not is_extractable_by_v1(StructuralFormat.ESSAY_LONG_FORM)

    def test_technical_not_eligible_for_v1(self):
        assert not is_extractable_by_v1(StructuralFormat.TECHNICAL_WITH_FIGURES)

    def test_vernacular_not_eligible_for_v1(self):
        assert not is_extractable_by_v1(StructuralFormat.VERNACULAR_NON_DEVANAGARI)

    def test_unknown_not_eligible_for_v1(self):
        assert not is_extractable_by_v1(StructuralFormat.UNKNOWN)

    def test_mcq_bilingual_eligible_for_v1(self):
        assert is_extractable_by_v1(StructuralFormat.MCQ_BILINGUAL_TWO_COLUMN)


class TestInferFormat:
    def test_known_identity_infers_correct_format(self):
        assert (infer_format_from_identity(ExamIdentity.UPSC_CSE_PRELIMS_GS1)
                == StructuralFormat.MCQ_BILINGUAL_TWO_COLUMN)

    def test_unknown_identity_returns_unknown_format(self):
        assert (infer_format_from_identity(ExamIdentity.UNKNOWN)
                == StructuralFormat.UNKNOWN)
