"""
Writer. Translates ExtractionResult into pyq_questions rows.

ALL writes via admin_exam_intel_cms.create_pyq_question() — the existing CMS
create path. This forces reviewer_status='pending' and writes the audit log.
Bypassing it is forbidden.

Dry-run mode (default): builds row payloads, stores them in the extraction_runs
metadata.dry_run_rows field. Does NOT call the CMS path.

Live mode (--confirm): calls create_pyq_question for each candidate after
applying idempotency + fuzzy dedup checks.
"""
from __future__ import annotations

import statistics
from typing import Any

from app.exam_intelligence.extraction.idempotency import (
    DedupDecision,
    compute_content_hash,
    compute_idempotency_key,
    decide_dedup,
)
from app.exam_intelligence.extraction.run import RunMetrics, is_killed
from app.exam_intelligence.extraction.types import ExtractedQuestion, ExtractionResult

# Sentinel admin context for service-role extractor writes.
# The CMS path requires an 'admin' dict for the audit log.  Service-role
# extractor runs have no user; we record that explicitly.
_EXTRACTOR_ADMIN_CTX: dict[str, Any] = {
    'id': None,
    'role': 'service_role',
    'source': 'auto_extractor',
}

# source_kind value for pyq_questions rows created by the extractor.
# This is the per-CMS-row source_kind (migration 149), distinct from
# document_assets.source_kind (migration 153/154).
_ROW_SOURCE_KIND = 'auto_extracted'


def _create_pyq_question(sb, payload: dict, reason: str) -> dict:
    """Call create_pyq_question as a regular Python function (not via HTTP).

    Constructs WriteEnvelope and passes the extractor's synthetic admin context.
    Returns the result dict from the CMS path.
    """
    from app.api.admin_exam_intel_cms import WriteEnvelope, create_pyq_question
    body = WriteEnvelope(reason=reason, payload=payload)
    return create_pyq_question(body=body, admin=_EXTRACTOR_ADMIN_CTX, __=None)


def _build_row_payload(
    q: ExtractedQuestion,
    document_id: str,
    run_id: str,
    extractor_version: str,
    pyq_paper_id: str,
    idempotency_key: str,
    content_hash: str,
) -> dict[str, Any]:
    """Build the payload dict for create_pyq_question.

    Maps ExtractedQuestion fields onto the pyq_questions column names.
    reviewer_status is NOT included — the CMS path forces 'pending'.
    """
    payload: dict[str, Any] = {
        'pyq_paper_id': pyq_paper_id,
        'question_number': q.question_number,
        'question_text': q.question_text,
        'source_kind': _ROW_SOURCE_KIND,
        'source_document_id': document_id,
        'source_page': q.regions[0].page if q.regions else None,
        'source_regions': [
            {'page': r.page, 'bbox': list(r.bbox)} for r in q.regions
        ],
        'extractor_version': extractor_version,
        'extraction_run_id': run_id,
        'idempotency_key': idempotency_key,
        'content_hash': content_hash,
        'confidence_by_field': q.confidence_by_field or {},
    }
    if q.options:
        payload['options'] = [
            {
                'option_label': opt.label.upper(),
                'option_text': opt.option_text,
            }
            for opt in q.options
        ]
    return payload


def _fetch_existing_rows(sb, document_id: str, pyq_paper_id: str) -> list[dict]:
    """Fetch existing pyq_questions for dedup comparison.

    Queries by pyq_paper_id (catches all rows for the paper, including manual
    rows with source_document_id=NULL) unioned with source_document_id (catches
    rows from previous extractor runs on the same document regardless of paper).
    De-duplicated by row id before returning.
    """
    by_paper = (
        sb.table('pyq_questions')
        .select('id, idempotency_key, content_hash, question_text')
        .eq('pyq_paper_id', pyq_paper_id)
        .execute()
    )
    by_doc = (
        sb.table('pyq_questions')
        .select('id, idempotency_key, content_hash, question_text')
        .eq('source_document_id', document_id)
        .execute()
    )
    seen: set[str] = set()
    rows: list[dict] = []
    for row in (by_paper.data or []) + (by_doc.data or []):
        if row['id'] not in seen:
            seen.add(row['id'])
            rows.append(row)
    return rows


def write_extraction_result(
    sb,
    result: ExtractionResult,
    run_id: str,
    pyq_paper_id: str,
    dry_run: bool,
    fuzzy_threshold: float = 0.85,
) -> RunMetrics:
    """Process every ExtractedQuestion, apply dedup, write via CMS path.

    Returns RunMetrics. Does not call complete_run / fail_run — caller does that
    so it can handle exceptions and set the correct terminal status.
    """
    metrics = RunMetrics(
        questions_extracted=len(result.questions),
        pages_processed=len(result.pages_processed),
        pages_skipped=len(result.pages_skipped),
    )

    existing_rows = _fetch_existing_rows(sb, result.document_id, pyq_paper_id)
    confidences: list[float] = []

    for q in result.questions:
        # Honor the kill switch between rows.
        if is_killed(sb, run_id):
            metrics.error_log.append({
                'kind': 'killed_during_write',
                'at_question_number': q.question_number,
            })
            break

        idem_key = compute_idempotency_key(
            document_id=result.document_id,
            page=q.regions[0].page if q.regions else 0,
            question_number=q.question_number,
            extractor_version=result.extractor_version,
        )
        c_hash = compute_content_hash(q.question_text)

        decision = decide_dedup(
            candidate_question_text=q.question_text,
            candidate_idempotency_key=idem_key,
            candidate_content_hash=c_hash,
            existing_rows_for_document=existing_rows,
            fuzzy_threshold=fuzzy_threshold,
        )

        if conf := q.confidence_by_field.get('ocr_p50'):
            # Tesseract confidence is 0-100; extraction_runs.confidence_p50/p90
            # are constrained to [0..1] (migration 149, numeric(4,3)).
            confidences.append(conf / 100.0 if conf > 1.0 else conf)

        payload = _build_row_payload(
            q=q,
            document_id=result.document_id,
            run_id=run_id,
            extractor_version=result.extractor_version,
            pyq_paper_id=pyq_paper_id,
            idempotency_key=idem_key,
            content_hash=c_hash,
        )

        if dry_run:
            dry_row: dict[str, Any] = {
                'payload': payload,
                'dedup_decision': {
                    'action': decision.action,
                    'reason': decision.reason,
                    'linked_row_id': decision.linked_row_id,
                },
            }
            if q.options:
                dry_row['metadata'] = {
                    'options': [
                        {
                            'option_label': opt.label.upper(),
                            'option_text': opt.option_text,
                        }
                        for opt in q.options
                    ]
                }
            metrics.dry_run_rows.append(dry_row)
            continue

        # Live write path.
        if decision.action == 'skip_idempotent':
            metrics.rows_skipped_idempotent += 1
            continue

        import logging as _logging
        _log = _logging.getLogger(__name__)

        try:
            result_row = _create_pyq_question(
                sb,
                payload=payload,
                reason=(
                    f"auto_extractor v{result.extractor_version} "
                    f"run={run_id} doc={result.document_id} Q{q.question_number}"
                ),
            )
            if isinstance(result_row, dict) and not result_row.get('ok', True):
                child_errors = result_row.get('child_errors', [])
                _log.warning(
                    "create_pyq_question returned ok=false for Q%s: %s",
                    q.question_number,
                    child_errors,
                )
                metrics.error_count += 1
                metrics.error_log.append({
                    'kind': 'create_pyq_question_ok_false',
                    'question_number': q.question_number,
                    'child_errors': child_errors,
                })
            else:
                if decision.action == 'link_fuzzy_duplicate':
                    metrics.rows_linked_fuzzy += 1
                else:
                    metrics.rows_inserted += 1
        except Exception as exc:  # noqa: BLE001
            metrics.error_count += 1
            metrics.error_log.append({
                'kind': 'create_pyq_question_failed',
                'question_number': q.question_number,
                'error_type': type(exc).__name__,
                'error_message': str(exc),
            })

    if confidences:
        confidences_sorted = sorted(confidences)
        n = len(confidences_sorted)
        metrics.confidence_p50 = confidences_sorted[n // 2]
        metrics.confidence_p90 = confidences_sorted[int(n * 0.9)]

    return metrics
