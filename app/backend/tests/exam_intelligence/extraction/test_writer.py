"""Unit tests for writer.py."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, call

from app.exam_intelligence.extraction.types import (
    ExtractedQuestion,
    ExtractionResult,
    Region,
    Word,
)
from app.exam_intelligence.extraction.writer import (
    _build_row_payload,
    _fetch_existing_rows,
    write_extraction_result,
)
from app.exam_intelligence.extraction.run import RunMetrics


def _make_question(qnum: int, page: int = 3, text: str = "What is X?") -> ExtractedQuestion:
    return ExtractedQuestion(
        question_number=qnum,
        question_text=text,
        regions=[Region(page=page, bbox=(0.1, 0.1, 0.9, 0.3))],
        confidence_by_field={'ocr_p50': 87.0},
    )


def _make_result(questions=None, document_id='doc-a') -> ExtractionResult:
    if questions is None:
        questions = [_make_question(1), _make_question(2)]
    return ExtractionResult(
        document_id=document_id,
        extractor_version='0.2.0',
        questions=questions,
        pages_processed=[3, 5],
        pages_skipped=[1, 2],
        errors=[],
    )


def _make_sb(existing_rows=None, kill_status='running'):
    sb = MagicMock()
    # _fetch_existing_rows
    sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = (
        existing_rows or []
    )
    # is_killed
    sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {'status': kill_status}
    ]
    return sb


class TestBuildRowPayload:
    def test_includes_pyq_paper_id(self):
        q = _make_question(1)
        p = _build_row_payload(q, 'doc-a', 'run-1', '0.2.0', 'paper-1', 'idem-key', 'c-hash')
        assert p['pyq_paper_id'] == 'paper-1'

    def test_includes_question_number(self):
        q = _make_question(42)
        p = _build_row_payload(q, 'doc-a', 'run-1', '0.2.0', 'paper-1', 'idem-key', 'c-hash')
        assert p['question_number'] == 42

    def test_includes_source_kind_auto_extracted(self):
        q = _make_question(1)
        p = _build_row_payload(q, 'doc-a', 'run-1', '0.2.0', 'paper-1', 'idem-key', 'c-hash')
        assert p['source_kind'] == 'auto_extracted'

    def test_includes_extraction_run_id(self):
        q = _make_question(1)
        p = _build_row_payload(q, 'doc-a', 'run-1', '0.2.0', 'paper-1', 'idem-key', 'c-hash')
        assert p['extraction_run_id'] == 'run-1'

    def test_includes_idempotency_key(self):
        q = _make_question(1)
        p = _build_row_payload(q, 'doc-a', 'run-1', '0.2.0', 'paper-1', 'idem-key', 'c-hash')
        assert p['idempotency_key'] == 'idem-key'

    def test_includes_source_page(self):
        q = _make_question(1, page=7)
        p = _build_row_payload(q, 'doc-a', 'run-1', '0.2.0', 'paper-1', 'idem-key', 'c-hash')
        assert p['source_page'] == 7

    def test_reviewer_status_not_in_payload(self):
        """reviewer_status must not be passed — CMS path forces 'pending'."""
        q = _make_question(1)
        p = _build_row_payload(q, 'doc-a', 'run-1', '0.2.0', 'paper-1', 'idem-key', 'c-hash')
        assert 'reviewer_status' not in p


class TestWriteExtractionResultDryRun:
    def test_dry_run_does_not_call_cms(self):
        sb = _make_sb()
        result = _make_result()
        with patch('app.exam_intelligence.extraction.writer._create_pyq_question') as mock_cms:
            metrics = write_extraction_result(sb, result, 'run-1', 'paper-1', dry_run=True)
            mock_cms.assert_not_called()

    def test_dry_run_populates_dry_run_rows(self):
        sb = _make_sb()
        result = _make_result([_make_question(1), _make_question(2)])
        with patch('app.exam_intelligence.extraction.writer._create_pyq_question'):
            metrics = write_extraction_result(sb, result, 'run-1', 'paper-1', dry_run=True)
        assert len(metrics.dry_run_rows) == 2

    def test_dry_run_rows_contain_dedup_decision(self):
        sb = _make_sb()
        result = _make_result([_make_question(1)])
        with patch('app.exam_intelligence.extraction.writer._create_pyq_question'):
            metrics = write_extraction_result(sb, result, 'run-1', 'paper-1', dry_run=True)
        assert 'dedup_decision' in metrics.dry_run_rows[0]
        assert 'action' in metrics.dry_run_rows[0]['dedup_decision']

    def test_dry_run_metrics_counts(self):
        sb = _make_sb()
        result = _make_result([_make_question(1), _make_question(2)])
        with patch('app.exam_intelligence.extraction.writer._create_pyq_question'):
            metrics = write_extraction_result(sb, result, 'run-1', 'paper-1', dry_run=True)
        assert metrics.questions_extracted == 2
        assert metrics.rows_inserted == 0
        assert metrics.rows_skipped_idempotent == 0


class TestWriteExtractionResultLive:
    def test_live_inserts_new_questions(self):
        sb = _make_sb(existing_rows=[])
        result = _make_result([_make_question(1)])
        with patch('app.exam_intelligence.extraction.writer._create_pyq_question') as mock_cms:
            mock_cms.return_value = {'ok': True}
            metrics = write_extraction_result(sb, result, 'run-1', 'paper-1', dry_run=False)
        assert mock_cms.call_count == 1
        assert metrics.rows_inserted == 1

    def test_live_skips_idempotent(self):
        """If idempotency_key already exists, skip without calling CMS."""
        from app.exam_intelligence.extraction.idempotency import compute_idempotency_key
        q = _make_question(1)
        idem_key = compute_idempotency_key('doc-a', 3, 1, '0.2.0')
        existing = [{'id': 'existing-row', 'idempotency_key': idem_key, 'content_hash': 'x', 'question_text': 'x'}]
        sb = _make_sb(existing_rows=existing)
        result = _make_result([q])
        with patch('app.exam_intelligence.extraction.writer._create_pyq_question') as mock_cms:
            metrics = write_extraction_result(sb, result, 'run-1', 'paper-1', dry_run=False)
        mock_cms.assert_not_called()
        assert metrics.rows_skipped_idempotent == 1

    def test_live_handles_cms_failure_gracefully(self):
        sb = _make_sb(existing_rows=[])
        result = _make_result([_make_question(1)])
        with patch('app.exam_intelligence.extraction.writer._create_pyq_question') as mock_cms:
            mock_cms.side_effect = RuntimeError("DB error")
            metrics = write_extraction_result(sb, result, 'run-1', 'paper-1', dry_run=False)
        assert metrics.error_count == 1
        assert metrics.rows_inserted == 0
        assert metrics.error_log[0]['kind'] == 'create_pyq_question_failed'

    def test_live_collects_confidence_metrics(self):
        sb = _make_sb(existing_rows=[])
        result = _make_result([_make_question(1), _make_question(2)])
        with patch('app.exam_intelligence.extraction.writer._create_pyq_question') as mock_cms:
            mock_cms.return_value = {'ok': True}
            metrics = write_extraction_result(sb, result, 'run-1', 'paper-1', dry_run=False)
        assert metrics.confidence_p50 is not None

    def test_kill_switch_stops_processing(self):
        """When is_killed returns True, processing stops early."""
        sb = _make_sb(kill_status='killed')
        result = _make_result([_make_question(1), _make_question(2), _make_question(3)])
        with patch('app.exam_intelligence.extraction.writer._create_pyq_question') as mock_cms:
            metrics = write_extraction_result(sb, result, 'run-1', 'paper-1', dry_run=False)
        # Kill detected before first row is processed
        assert mock_cms.call_count == 0
        assert any(e.get('kind') == 'killed_during_write' for e in metrics.error_log)


class TestDocumentKindGuard:
    """Integration: ExtractionWrongDocumentKindError fires before DB writes."""

    def test_wrong_document_kind_raises_before_run_starts(self):
        from unittest.mock import patch, MagicMock
        from app.exam_intelligence.extraction.pipeline import (
            ExtractionWrongDocumentKindError,
            extract,
        )
        from app.exam_intelligence.extraction.dispatch import (
            StructuralFormat, ExamIdentity, SourceKind,
        )
        from app.exam_intelligence.extraction.pipeline import _DocumentAssetsRow

        row = _DocumentAssetsRow(
            id='doc-a',
            structural_format=StructuralFormat.MCQ_BILINGUAL_TWO_COLUMN,
            exam_identity=ExamIdentity.UPSC_CSE_PRELIMS_GS1,
            source_kind=SourceKind.SANITIZED_COACHING,
            document_kind='notification',
            storage_path='',
        )
        with patch('app.exam_intelligence.extraction.pipeline._fetch_document_assets_row', return_value=row):
            with pytest.raises(ExtractionWrongDocumentKindError) as exc:
                extract(pdf_bytes=b'', document_id='doc-a')
        assert 'notification' in str(exc.value)
        assert 'pyq_paper' in str(exc.value)
