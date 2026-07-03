"""Acceptance tests — J3 Mixed-Format PDF Gate, PR 3 (Option B / B1).

See docs/status/J3-Mixed-Format-PDF-Gate-2026-07-02.md and
docs/status/J3-Implementation-Checklist-2026-07-02.md ("PR 3").

Covers the locked-scope acceptance list (gate doc Section E):
- declared mixed_format=true raises ExtractionMixedFormatError pre-OCR,
  zero pyq_questions writes (OCR + writer spied, asserted not called).
- a homogeneous mcq_bilingual_two_column document still extracts as today
  (no regression).
- two split sub-documents (each re-uploaded separately, mixed_format not
  set) extract independently and successfully.

Unit-level: no live Supabase/Tesseract creds required. document_assets
row fetch and OCR are mocked/patched directly.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.exam_intelligence.extraction.dispatch import ExamIdentity, SourceKind, StructuralFormat
from app.exam_intelligence.extraction.pipeline import (
    ExtractionMixedFormatError,
    MIXED_FORMAT_WORKAROUND_SOP,
    _DocumentAssetsRow,
    _is_mixed_format_declared,
)

DOC_ID = "11111111-1111-1111-1111-111111111111"


def _mcq_row(document_id: str, mixed_format: bool = False) -> _DocumentAssetsRow:
    return _DocumentAssetsRow(
        id=document_id,
        structural_format=StructuralFormat.MCQ_BILINGUAL_TWO_COLUMN,
        exam_identity=ExamIdentity.UPSC_CSE_PRELIMS_GS1,
        source_kind=SourceKind.SANITIZED_COACHING,
        document_kind="pyq_paper",
        storage_path="",
        mixed_format=mixed_format,
    )


# ─────────────────────────────────────────────────────────────────────────
# _is_mixed_format_declared — validation of the B1 admin-declared flag
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "metadata,expected",
    [
        (None, False),
        ({}, False),
        ({"mixed_format": True}, True),
        ({"mixed_format": False}, False),
        ({"mixed_format": "true"}, False),   # string truthy value rejected — must be literal bool
        ({"mixed_format": 1}, False),         # int truthy value rejected
        ({"mixed_format": None}, False),
        ({"other_key": "value"}, False),
    ],
)
def test_is_mixed_format_declared_validation(metadata, expected):
    assert _is_mixed_format_declared(metadata) is expected


# ─────────────────────────────────────────────────────────────────────────
# Scope-fence: mixed_format=true rejects pre-OCR, zero pyq_questions writes
# ─────────────────────────────────────────────────────────────────────────

def test_mixed_format_declared_raises_before_ocr_zero_writes():
    """Declaring mixed_format=true must reject before any OCR/PDF processing
    and must not touch the pyq_questions writer path at all."""
    from app.exam_intelligence.extraction import pipeline

    with patch.object(
        pipeline, "_fetch_document_assets_row", return_value=_mcq_row(DOC_ID, mixed_format=True)
    ), patch.object(pipeline, "fitz") as mock_fitz, patch(
        "app.exam_intelligence.extraction.ocr.ocr_page"
    ) as mock_ocr_page, patch(
        "app.api.admin_exam_intel_cms.create_pyq_question",
    ) as mock_create_question:
        with pytest.raises(ExtractionMixedFormatError) as excinfo:
            pipeline.extract(b"%PDF-fake-bytes", document_id=DOC_ID)

        # Error message must name the workaround and link the SOP doc.
        message = str(excinfo.value)
        assert "mixed-format" in message.lower()
        assert "split" in message.lower()
        assert MIXED_FORMAT_WORKAROUND_SOP in message

        # No PDF was even opened — the guard runs before fitz.open().
        mock_fitz.open.assert_not_called()
        # No OCR call occurred.
        mock_ocr_page.assert_not_called()
        # No write path was touched.
        mock_create_question.assert_not_called()


def test_mixed_format_false_does_not_raise_mixed_format_error():
    """mixed_format=false (the default) must not trigger the mixed-format guard
    — it should fall through to the ordinary scope-fence checks."""
    from app.exam_intelligence.extraction import pipeline

    with patch.object(
        pipeline, "_fetch_document_assets_row", return_value=_mcq_row(DOC_ID, mixed_format=False)
    ):
        # A malformed/empty PDF will fail later inside fitz.open, but it must
        # NOT fail with ExtractionMixedFormatError.
        with pytest.raises(Exception) as excinfo:
            pipeline.extract(b"not-a-real-pdf", document_id=DOC_ID)
        assert not isinstance(excinfo.value, ExtractionMixedFormatError)


# ─────────────────────────────────────────────────────────────────────────
# Regression: homogeneous mcq_bilingual_two_column extracts as today
# ─────────────────────────────────────────────────────────────────────────

def test_homogeneous_mcq_document_extracts_without_mixed_format_error():
    """A homogeneous mcq_bilingual_two_column document (mixed_format unset)
    must proceed past the scope fence exactly as before this change —
    regression guard for the new mixed_format check."""
    from app.exam_intelligence.extraction import pipeline
    from app.exam_intelligence.extraction.types import Word

    words_by_page = {
        1: [
            Word(text="1.", bbox=(0.47, 0.10, 0.50, 0.12), page=1, confidence=95.0),
            Word(text="What", bbox=(0.47, 0.12, 0.55, 0.14), page=1, confidence=95.0),
            Word(text="is", bbox=(0.56, 0.12, 0.60, 0.14), page=1, confidence=95.0),
            Word(text="X?", bbox=(0.61, 0.12, 0.65, 0.14), page=1, confidence=95.0),
        ],
    }

    class _FakePage:
        def __init__(self, n):
            self._n = n

        def get_pixmap(self, matrix=None):
            pix = MagicMock()
            pix.width, pix.height = 10, 10
            pix.samples = b"\x00" * (10 * 10 * 3)
            return pix

    class _FakeDoc:
        page_count = 3

        def __getitem__(self, idx):
            return _FakePage(idx + 1)

        def close(self):
            pass

    with patch.object(
        pipeline, "_fetch_document_assets_row", return_value=_mcq_row(DOC_ID, mixed_format=False)
    ), patch.object(pipeline.fitz, "open", return_value=_FakeDoc()), patch.object(
        pipeline.Image, "frombytes", return_value=MagicMock()
    ), patch(
        "app.exam_intelligence.extraction.pipeline.ocr_page",
        side_effect=lambda img, page_num: words_by_page.get(page_num, []),
    ):
        result = pipeline.extract(b"%PDF-fake", document_id=DOC_ID, pages=[1])

    assert result.document_id == DOC_ID
    assert 1 in result.pages_processed
    assert result.errors == [] or all("mixed" not in str(e).lower() for e in result.errors)


# ─────────────────────────────────────────────────────────────────────────
# Split sub-documents extract independently
# ─────────────────────────────────────────────────────────────────────────

def test_split_sub_documents_extract_independently():
    """After splitting a mixed-format PDF per the workaround SOP, each
    homogeneous sub-document (mixed_format not set) must extract on its
    own without interference from the other."""
    from app.exam_intelligence.extraction.pipeline import extract_from_words
    from app.exam_intelligence.extraction.types import Word

    doc_a_id = "22222222-2222-2222-2222-222222222222"  # e.g. the MCQ section
    doc_b_id = "33333333-3333-3333-3333-333333333333"  # e.g. a second MCQ section

    words_a = [
        Word(text="1.", bbox=(0.47, 0.10, 0.50, 0.12), page=1, confidence=95.0),
        Word(text="Alpha?", bbox=(0.51, 0.10, 0.60, 0.12), page=1, confidence=95.0),
    ]
    words_b = [
        Word(text="1.", bbox=(0.47, 0.10, 0.50, 0.12), page=1, confidence=95.0),
        Word(text="Beta?", bbox=(0.51, 0.10, 0.60, 0.12), page=1, confidence=95.0),
    ]

    result_a = extract_from_words(words_a, page=1, document_id=doc_a_id)
    result_b = extract_from_words(words_b, page=1, document_id=doc_b_id)

    assert result_a.document_id == doc_a_id
    assert result_b.document_id == doc_b_id
    # Independent extraction — no cross-document ordinal/state leakage.
    assert result_a.pages_processed == [1]
    assert result_b.pages_processed == [1]


# ─────────────────────────────────────────────────────────────────────────
# document_kind gate unaffected by this change
# ─────────────────────────────────────────────────────────────────────────

def test_wrong_document_kind_still_rejected():
    from app.exam_intelligence.extraction import pipeline
    from app.exam_intelligence.extraction.pipeline import ExtractionWrongDocumentKindError

    row = _mcq_row(DOC_ID, mixed_format=False)
    row = pipeline._DocumentAssetsRow(
        **{**row.__dict__, "document_kind": "syllabus"}
    )
    with patch.object(pipeline, "_fetch_document_assets_row", return_value=row):
        with pytest.raises(ExtractionWrongDocumentKindError):
            pipeline.extract(b"%PDF-fake", document_id=DOC_ID)
