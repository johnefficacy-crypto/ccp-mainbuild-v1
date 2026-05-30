"""
extraction_runs lifecycle.

Every extraction invocation creates an extraction_runs row.
Status transitions are explicit:  running → completed | failed | killed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


EXTRACTOR_NAME = "upsc_pyq_question_extractor"


class RunStatus(str, Enum):
    RUNNING   = 'running'
    COMPLETED = 'completed'
    FAILED    = 'failed'
    KILLED    = 'killed'


@dataclass
class RunMetrics:
    questions_extracted: int = 0
    rows_inserted: int = 0
    rows_skipped_idempotent: int = 0
    rows_linked_fuzzy: int = 0
    pages_processed: int = 0
    pages_skipped: int = 0
    error_count: int = 0
    error_log: list[dict] = field(default_factory=list)
    confidence_p50: float | None = None
    confidence_p90: float | None = None
    dry_run_rows: list[dict] = field(default_factory=list)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def start_run(
    sb,
    document_id: str,
    extractor_version: str,
    dry_run: bool,
    triggered_by_user_id: str | None,
) -> str:
    """Insert extraction_runs row with status='running'. Returns the run UUID."""
    payload: dict[str, Any] = {
        'document_id': document_id,
        'extractor_name': EXTRACTOR_NAME,
        'extractor_version': extractor_version,
        'status': RunStatus.RUNNING.value,
        'started_at': _now(),
        'metadata': {
            'dry_run': dry_run,
            'triggered_by_user_id': triggered_by_user_id,
        },
    }
    res = sb.table('extraction_runs').insert(payload).execute()
    return res.data[0]['id']


def is_killed(sb, run_id: str) -> bool:
    """True if the run's status has been set to 'killed' externally.

    Writers should call this between batches to honor the kill switch promptly.
    """
    res = (
        sb.table('extraction_runs')
        .select('status')
        .eq('id', run_id)
        .limit(1)
        .execute()
    )
    return bool(res.data) and res.data[0]['status'] == RunStatus.KILLED.value


def complete_run(
    sb,
    run_id: str,
    metrics: RunMetrics,
    final_status: RunStatus = RunStatus.COMPLETED,
) -> None:
    """Transition run to terminal status and record metrics.

    Use COMPLETED even when error_count > 0 — per-row failures are non-fatal.
    Use FAILED only for uncaught pipeline exceptions.
    Use KILLED only when the kill switch was honored.
    """
    metadata: dict[str, Any] = {
        'questions_extracted': metrics.questions_extracted,
        'rows_inserted': metrics.rows_inserted,
        'rows_skipped_idempotent': metrics.rows_skipped_idempotent,
        'rows_linked_fuzzy': metrics.rows_linked_fuzzy,
        'pages_processed': metrics.pages_processed,
        'pages_skipped': metrics.pages_skipped,
        'error_log': metrics.error_log,
    }
    if metrics.dry_run_rows:
        metadata['dry_run_rows'] = metrics.dry_run_rows

    update: dict[str, Any] = {
        'status': final_status.value,
        'completed_at': _now(),
        'row_count': metrics.rows_inserted,
        'error_count': metrics.error_count,
        'confidence_p50': metrics.confidence_p50,
        'confidence_p90': metrics.confidence_p90,
        'error_log': metrics.error_log,
        'metadata': metadata,
    }
    sb.table('extraction_runs').update(update).eq('id', run_id).execute()


def fail_run(sb, run_id: str, error: Exception, partial_metrics: RunMetrics) -> None:
    """Terminal failure — records the exception and transitions to FAILED."""
    partial_metrics.error_count += 1
    partial_metrics.error_log.append({
        'kind': 'pipeline_exception',
        'error_type': type(error).__name__,
        'error_message': str(error),
    })
    complete_run(sb, run_id, partial_metrics, RunStatus.FAILED)
