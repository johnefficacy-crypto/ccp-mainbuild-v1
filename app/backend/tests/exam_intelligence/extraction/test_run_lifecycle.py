"""Unit tests for run.py lifecycle functions."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, call

from app.exam_intelligence.extraction.run import (
    EXTRACTOR_NAME,
    RunMetrics,
    RunStatus,
    complete_run,
    fail_run,
    is_killed,
    start_run,
)


def _make_sb(insert_return_id='run-uuid-1', select_status='running'):
    """Build a mock Supabase client for run lifecycle tests."""
    sb = MagicMock()
    # start_run INSERT chain
    sb.table.return_value.insert.return_value.execute.return_value.data = [
        {'id': insert_return_id}
    ]
    # is_killed SELECT chain
    sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {'status': select_status}
    ]
    return sb


class TestStartRun:
    def test_returns_run_id(self):
        sb = _make_sb(insert_return_id='abc-123')
        run_id = start_run(sb, 'doc-a', '0.2.0', dry_run=True, triggered_by_user_id=None)
        assert run_id == 'abc-123'

    def test_inserts_running_status(self):
        sb = _make_sb()
        start_run(sb, 'doc-a', '0.2.0', dry_run=False, triggered_by_user_id='user-1')
        payload = sb.table.return_value.insert.call_args[0][0]
        assert payload['status'] == 'running'

    def test_inserts_correct_extractor_name(self):
        sb = _make_sb()
        start_run(sb, 'doc-a', '0.2.0', dry_run=False, triggered_by_user_id=None)
        payload = sb.table.return_value.insert.call_args[0][0]
        assert payload['extractor_name'] == EXTRACTOR_NAME

    def test_inserts_dry_run_in_metadata(self):
        sb = _make_sb()
        start_run(sb, 'doc-a', '0.2.0', dry_run=True, triggered_by_user_id=None)
        payload = sb.table.return_value.insert.call_args[0][0]
        assert payload['metadata']['dry_run'] is True

    def test_writes_to_extraction_runs_table(self):
        sb = _make_sb()
        start_run(sb, 'doc-a', '0.2.0', dry_run=False, triggered_by_user_id=None)
        sb.table.assert_called_with('extraction_runs')


class TestIsKilled:
    def test_returns_true_when_killed(self):
        sb = _make_sb(select_status='killed')
        assert is_killed(sb, 'run-a') is True

    def test_returns_false_when_running(self):
        sb = _make_sb(select_status='running')
        assert is_killed(sb, 'run-a') is False

    def test_returns_false_when_no_data(self):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        assert is_killed(sb, 'run-a') is False


class TestCompleteRun:
    def test_sets_completed_status(self):
        sb = MagicMock()
        metrics = RunMetrics(rows_inserted=80)
        complete_run(sb, 'run-a', metrics, RunStatus.COMPLETED)
        update = sb.table.return_value.update.call_args[0][0]
        assert update['status'] == 'completed'

    def test_sets_failed_status(self):
        sb = MagicMock()
        metrics = RunMetrics(error_count=5)
        complete_run(sb, 'run-a', metrics, RunStatus.FAILED)
        update = sb.table.return_value.update.call_args[0][0]
        assert update['status'] == 'failed'

    def test_records_row_count(self):
        sb = MagicMock()
        metrics = RunMetrics(rows_inserted=42)
        complete_run(sb, 'run-a', metrics, RunStatus.COMPLETED)
        update = sb.table.return_value.update.call_args[0][0]
        assert update['row_count'] == 42

    def test_records_error_count(self):
        sb = MagicMock()
        metrics = RunMetrics(error_count=3)
        complete_run(sb, 'run-a', metrics, RunStatus.COMPLETED)
        update = sb.table.return_value.update.call_args[0][0]
        assert update['error_count'] == 3

    def test_completed_with_errors_still_completed_status(self):
        """Per-row failures are non-fatal; status is still COMPLETED."""
        sb = MagicMock()
        metrics = RunMetrics(rows_inserted=95, error_count=5)
        complete_run(sb, 'run-a', metrics, RunStatus.COMPLETED)
        update = sb.table.return_value.update.call_args[0][0]
        assert update['status'] == 'completed'

    def test_dry_run_rows_in_metadata(self):
        sb = MagicMock()
        metrics = RunMetrics()
        metrics.dry_run_rows.append({'payload': {'question_text': 'Q1'}})
        complete_run(sb, 'run-a', metrics, RunStatus.COMPLETED)
        update = sb.table.return_value.update.call_args[0][0]
        assert 'dry_run_rows' in update['metadata']

    def test_updates_correct_run_id(self):
        sb = MagicMock()
        complete_run(sb, 'run-specific-id', RunMetrics(), RunStatus.COMPLETED)
        sb.table.return_value.update.return_value.eq.assert_called_with('id', 'run-specific-id')


class TestFailRun:
    def test_sets_failed_status(self):
        sb = MagicMock()
        fail_run(sb, 'run-a', ValueError("boom"), RunMetrics())
        update = sb.table.return_value.update.call_args[0][0]
        assert update['status'] == 'failed'

    def test_records_exception_in_error_log(self):
        sb = MagicMock()
        metrics = RunMetrics()
        fail_run(sb, 'run-a', RuntimeError("something went wrong"), metrics)
        update = sb.table.return_value.update.call_args[0][0]
        assert len(update['error_log']) == 1
        assert update['error_log'][0]['error_type'] == 'RuntimeError'
        assert 'something went wrong' in update['error_log'][0]['error_message']

    def test_increments_error_count(self):
        sb = MagicMock()
        metrics = RunMetrics(error_count=2)
        fail_run(sb, 'run-a', ValueError("boom"), metrics)
        update = sb.table.return_value.update.call_args[0][0]
        assert update['error_count'] == 3
