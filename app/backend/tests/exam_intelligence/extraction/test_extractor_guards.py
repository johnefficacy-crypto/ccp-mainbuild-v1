import pytest
from unittest.mock import patch, MagicMock
from app.exam_intelligence.extraction.pipeline import (
    extract,
    ExtractionNotSupportedError,
    ExtractionRequiresClassificationError,
    ExtractionRequiresCleanInputError,
)
from app.exam_intelligence.extraction.dispatch import (
    ExamIdentity,
    SourceKind,
    StructuralFormat,
)


def _mock_doc_row(structural_format, exam_identity, source_kind=SourceKind.SANITIZED_COACHING):
    row = MagicMock()
    row.structural_format = structural_format
    row.exam_identity = exam_identity
    row.source_kind = source_kind
    row.storage_path = 'fake/path.pdf'
    return row


@patch('app.exam_intelligence.extraction.pipeline._fetch_document_assets_row')
class TestExtractorGuards:

    def test_raises_classification_required_when_format_unknown(self, mock_fetch):
        mock_fetch.return_value = _mock_doc_row(
            StructuralFormat.UNKNOWN,
            ExamIdentity.UNKNOWN,
        )
        with pytest.raises(ExtractionRequiresClassificationError) as exc:
            extract(pdf_bytes=b'', document_id='test-id')
        assert 'unknown' in str(exc.value).lower()
        assert 'classify' in str(exc.value).lower()

    def test_raises_not_supported_for_essay_format(self, mock_fetch):
        mock_fetch.return_value = _mock_doc_row(
            StructuralFormat.ESSAY_LONG_FORM,
            ExamIdentity.UPSC_CSE_MAINS_GS1,
        )
        with pytest.raises(ExtractionNotSupportedError) as exc:
            extract(pdf_bytes=b'', document_id='test-id')
        assert 'essay_long_form' in str(exc.value)
        assert 'mcq_bilingual_two_column' in str(exc.value)

    def test_raises_not_supported_for_technical_format(self, mock_fetch):
        mock_fetch.return_value = _mock_doc_row(
            StructuralFormat.TECHNICAL_WITH_FIGURES,
            ExamIdentity.UPSC_CSE_MAINS_OPTIONAL_TECHNICAL,
        )
        with pytest.raises(ExtractionNotSupportedError):
            extract(pdf_bytes=b'', document_id='test-id')

    def test_raises_not_supported_for_vernacular_format(self, mock_fetch):
        mock_fetch.return_value = _mock_doc_row(
            StructuralFormat.VERNACULAR_NON_DEVANAGARI,
            ExamIdentity.UPSC_OTHER,
        )
        with pytest.raises(ExtractionNotSupportedError):
            extract(pdf_bytes=b'', document_id='test-id')

    def test_error_message_includes_exam_identity_for_debugging(self, mock_fetch):
        mock_fetch.return_value = _mock_doc_row(
            StructuralFormat.ESSAY_LONG_FORM,
            ExamIdentity.UPSC_CSE_MAINS_GS2,
        )
        with pytest.raises(ExtractionNotSupportedError) as exc:
            extract(pdf_bytes=b'', document_id='test-id')
        assert 'upsc_cse_mains_gs2' in str(exc.value)

    def test_raises_clean_input_required_for_raw_coaching(self, mock_fetch):
        mock_fetch.return_value = _mock_doc_row(
            StructuralFormat.MCQ_BILINGUAL_TWO_COLUMN,
            ExamIdentity.UPSC_CSE_PRELIMS_GS1,
            source_kind=SourceKind.RAW_COACHING,
        )
        with pytest.raises(ExtractionRequiresCleanInputError) as exc:
            extract(pdf_bytes=b'', document_id='test-id')
        assert 'raw_coaching' in str(exc.value)
        assert 'sanitized' in str(exc.value).lower()

    def test_raises_clean_input_required_for_crowd_sourced(self, mock_fetch):
        mock_fetch.return_value = _mock_doc_row(
            StructuralFormat.MCQ_BILINGUAL_TWO_COLUMN,
            ExamIdentity.UPSC_CSE_PRELIMS_GS1,
            source_kind=SourceKind.CROWD_SOURCED,
        )
        with pytest.raises(ExtractionRequiresCleanInputError) as exc:
            extract(pdf_bytes=b'', document_id='test-id')
        assert 'crowd_sourced' in str(exc.value)

    def test_raises_clean_input_required_when_source_kind_unknown(self, mock_fetch):
        mock_fetch.return_value = _mock_doc_row(
            StructuralFormat.MCQ_BILINGUAL_TWO_COLUMN,
            ExamIdentity.UPSC_CSE_PRELIMS_GS1,
            source_kind=SourceKind.UNKNOWN,
        )
        with pytest.raises(ExtractionRequiresCleanInputError):
            extract(pdf_bytes=b'', document_id='test-id')

    def test_error_message_includes_sop_reference(self, mock_fetch):
        mock_fetch.return_value = _mock_doc_row(
            StructuralFormat.MCQ_BILINGUAL_TWO_COLUMN,
            ExamIdentity.UPSC_CSE_PRELIMS_GS1,
            source_kind=SourceKind.RAW_COACHING,
        )
        with pytest.raises(ExtractionRequiresCleanInputError) as exc:
            extract(pdf_bytes=b'', document_id='test-id')
        assert 'sanitization-sop-v1' in str(exc.value)

    def test_official_scan_passes_source_guard(self, mock_fetch):
        mock_fetch.return_value = _mock_doc_row(
            StructuralFormat.MCQ_BILINGUAL_TWO_COLUMN,
            ExamIdentity.UPSC_CSE_PRELIMS_GS1,
            source_kind=SourceKind.OFFICIAL_SCAN,
        )
        mock_doc = MagicMock()
        mock_doc.page_count = 0
        mock_doc.__enter__ = MagicMock(return_value=mock_doc)
        mock_doc.__exit__ = MagicMock(return_value=False)
        with patch('app.exam_intelligence.extraction.pipeline.fitz') as mock_fitz:
            mock_fitz.open.return_value = mock_doc
            result = extract(pdf_bytes=b'\x25\x50\x44\x46', document_id='test-id')
            assert result is not None

    def test_proceeds_when_mcq_bilingual_eligible(self, mock_fetch):
        """Guard passes through; actual extraction not tested here.
        Mock the OCR/segmentation downstream to confirm guard didn't block."""
        mock_fetch.return_value = _mock_doc_row(
            StructuralFormat.MCQ_BILINGUAL_TWO_COLUMN,
            ExamIdentity.UPSC_CSE_PRELIMS_GS1,
        )
        mock_doc = MagicMock()
        mock_doc.page_count = 0
        mock_doc.__enter__ = MagicMock(return_value=mock_doc)
        mock_doc.__exit__ = MagicMock(return_value=False)
        with patch('app.exam_intelligence.extraction.pipeline.fitz') as mock_fitz:
            mock_fitz.open.return_value = mock_doc
            result = extract(pdf_bytes=b'\x25\x50\x44\x46', document_id='test-id')
            assert result is not None
