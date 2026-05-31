"""
Dispatcher logic: maps exam_identity to structural_format,
and structural_format to extractor version.

This is the ONE place where v1 / v1.5 / v2 / v3 dispatch logic
lives. Adding a new extractor version means updating this file
and adding the extractor module — not modifying the pipeline.
"""

from enum import Enum


class StructuralFormat(str, Enum):
    MCQ_BILINGUAL_TWO_COLUMN = 'mcq_bilingual_two_column'
    MCQ_MONOLINGUAL_SINGLE = 'mcq_monolingual_single'
    ESSAY_LONG_FORM = 'essay_long_form'
    MIXED_OBJECTIVE_SUBJECTIVE = 'mixed_objective_subjective'
    TECHNICAL_WITH_FIGURES = 'technical_with_figures'
    VERNACULAR_NON_DEVANAGARI = 'vernacular_non_devanagari'
    UNKNOWN = 'unknown'


class ExamIdentity(str, Enum):
    UPSC_CSE_PRELIMS_GS1 = 'upsc_cse_prelims_gs1'
    UPSC_CSE_PRELIMS_CSAT = 'upsc_cse_prelims_csat'
    UPSC_CSE_MAINS_ESSAY = 'upsc_cse_mains_essay'
    UPSC_CSE_MAINS_GS1 = 'upsc_cse_mains_gs1'
    UPSC_CSE_MAINS_GS2 = 'upsc_cse_mains_gs2'
    UPSC_CSE_MAINS_GS3 = 'upsc_cse_mains_gs3'
    UPSC_CSE_MAINS_GS4 = 'upsc_cse_mains_gs4'
    UPSC_CSE_MAINS_OPTIONAL_SOCIOLOGY = 'upsc_cse_mains_optional_sociology'
    UPSC_CSE_MAINS_OPTIONAL_PSIR = 'upsc_cse_mains_optional_psir'
    UPSC_CSE_MAINS_OPTIONAL_HISTORY = 'upsc_cse_mains_optional_history'
    UPSC_CSE_MAINS_OPTIONAL_ANTHROPOLOGY = 'upsc_cse_mains_optional_anthropology'
    UPSC_CSE_MAINS_OPTIONAL_TECHNICAL = 'upsc_cse_mains_optional_technical'
    UPSC_OTHER = 'upsc_other'
    STATE_PSC_OTHER = 'state_psc_other'
    BANKING_OTHER = 'banking_other'
    UNKNOWN = 'unknown'


# ───────────────────────────────────────────────────────────────
# Mapping: exam_identity → expected structural_format
# Used when classification model is "admin chooses identity,
# system infers format" (option (b) from architecture discussion).
#
# Admin can override the inferred format if a specific paper has
# an unusual layout (e.g., a Mains optional that's actually MCQ).
# ───────────────────────────────────────────────────────────────

EXAM_TO_FORMAT_DEFAULT: dict[ExamIdentity, StructuralFormat] = {
    ExamIdentity.UPSC_CSE_PRELIMS_GS1:  StructuralFormat.MCQ_BILINGUAL_TWO_COLUMN,
    ExamIdentity.UPSC_CSE_PRELIMS_CSAT: StructuralFormat.MCQ_BILINGUAL_TWO_COLUMN,

    ExamIdentity.UPSC_CSE_MAINS_ESSAY:  StructuralFormat.ESSAY_LONG_FORM,
    ExamIdentity.UPSC_CSE_MAINS_GS1:    StructuralFormat.ESSAY_LONG_FORM,
    ExamIdentity.UPSC_CSE_MAINS_GS2:    StructuralFormat.ESSAY_LONG_FORM,
    ExamIdentity.UPSC_CSE_MAINS_GS3:    StructuralFormat.ESSAY_LONG_FORM,
    ExamIdentity.UPSC_CSE_MAINS_GS4:    StructuralFormat.ESSAY_LONG_FORM,

    ExamIdentity.UPSC_CSE_MAINS_OPTIONAL_SOCIOLOGY:   StructuralFormat.ESSAY_LONG_FORM,
    ExamIdentity.UPSC_CSE_MAINS_OPTIONAL_PSIR:         StructuralFormat.ESSAY_LONG_FORM,
    ExamIdentity.UPSC_CSE_MAINS_OPTIONAL_HISTORY:      StructuralFormat.ESSAY_LONG_FORM,
    ExamIdentity.UPSC_CSE_MAINS_OPTIONAL_ANTHROPOLOGY: StructuralFormat.ESSAY_LONG_FORM,
    ExamIdentity.UPSC_CSE_MAINS_OPTIONAL_TECHNICAL:    StructuralFormat.TECHNICAL_WITH_FIGURES,

    ExamIdentity.UPSC_OTHER:      StructuralFormat.UNKNOWN,
    ExamIdentity.STATE_PSC_OTHER: StructuralFormat.UNKNOWN,
    ExamIdentity.BANKING_OTHER:   StructuralFormat.UNKNOWN,
    ExamIdentity.UNKNOWN:         StructuralFormat.UNKNOWN,
}


# ───────────────────────────────────────────────────────────────
# Eligibility: which formats can the v1 extractor handle?
# This is the load-bearing constant. Changes here are scope changes.
# ───────────────────────────────────────────────────────────────

ELIGIBLE_FORMATS_V1: frozenset[StructuralFormat] = frozenset({
    StructuralFormat.MCQ_BILINGUAL_TWO_COLUMN,
})


# ───────────────────────────────────────────────────────────────
# Source kind: provenance of the uploaded PDF.
# ELIGIBLE_SOURCE_KINDS_V1 = the two kinds whose input is clean
# enough for the v1 OCR + segmentation pipeline.
# ───────────────────────────────────────────────────────────────

class SourceKind(str, Enum):
    OFFICIAL_ARCHIVE    = 'official_archive'    # UPSC's published archive; ~1yr delay
    OFFICIAL_SCAN       = 'official_scan'        # legacy alias; prefer official_archive
    SANITIZED_COACHING  = 'sanitized_coaching'   # coaching PDF, watermarks removed
    RAW_COACHING        = 'raw_coaching'          # coaching PDF as-is; overlays present
    SME_AUTHORED        = 'sme_authored'          # SME-authored or transcribed test content
    CROWD_SOURCED       = 'crowd_sourced'         # community-contributed; unclear provenance
    UNKNOWN             = 'unknown'


ELIGIBLE_SOURCE_KINDS_V1: frozenset[SourceKind] = frozenset({
    SourceKind.OFFICIAL_ARCHIVE,
    SourceKind.OFFICIAL_SCAN,       # legacy alias; accepted for backwards compat
    SourceKind.SANITIZED_COACHING,
    SourceKind.SME_AUTHORED,
})


def is_source_eligible_v1(source_kind: SourceKind) -> bool:
    """True iff the source_kind is clean enough for the v1 extractor."""
    return source_kind in ELIGIBLE_SOURCE_KINDS_V1


def infer_format_from_identity(identity: ExamIdentity) -> StructuralFormat:
    """Look up the default structural_format for an exam_identity.

    Returns UNKNOWN if the identity has no known format mapping
    (caller must handle).
    """
    return EXAM_TO_FORMAT_DEFAULT.get(identity, StructuralFormat.UNKNOWN)


def is_extractable_by_v1(format: StructuralFormat) -> bool:
    """True iff v1 extractor can process this structural_format."""
    return format in ELIGIBLE_FORMATS_V1
