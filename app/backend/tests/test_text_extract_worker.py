"""Tests for text_extract_worker.py (issue #540).

Covers:
- claim_next_text_extract_job: empty queue, FIFO ordering, non-queued rows
  ignored, non-admin scopes excluded — scope resolved via document_assets join
- run_worker_pass: idle, success, conflict race, failure with fallback recovery
- Admin-scope routing: admin_exam_intelligence → admin_scope= param forwarded
  from embedded document_assets row (not hard-coded)
- Fallback failure recovery: stranded 'running' job AND parent document_assets
  row both flipped to 'failed'
- _ADMIN_SCOPES constant

Schema alignment: document_processing_jobs has NO scope column; scope lives on
document_assets and is resolved via the inner-join embed.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, call, patch
from uuid import uuid4

import pytest

from app.library.text_extract_worker import (
    _ADMIN_SCOPES,
    _TRANSIENT_ERROR_CODES,
    BASE_BACKOFF_SECONDS,
    MAX_TRANSIENT_ATTEMPTS,
    _fallback_fail_job,
    claim_next_retry_job,
    claim_next_text_extract_job,
    run_worker_pass,
)


# ── Minimal Supabase stub ────────────────────────────────────────────────────


class _R:
    def __init__(self, data):
        self.data = data


class _Q:
    """Chainable query stub. Supports PostgREST embedded resource filters
    (e.g. 'document_assets.scope') and inner-join embedding."""

    def __init__(self, rows: list[dict], docs: list[dict] | None = None):
        self._rows = rows
        self._docs = docs or []
        self._filters: list[tuple] = []
        self._order_key: str | None = None
        self._desc = False
        self._limit_n: int | None = None
        self._update_payload: dict | None = None
        self._op = "select"
        self._embed_docs = False

    def select(self, *_a, **_kw):
        self._op = "select"
        if _a and "document_assets" in str(_a[0]):
            self._embed_docs = True
        return self

    def update(self, payload: dict):
        self._op = "update"
        self._update_payload = payload
        return self

    def eq(self, col, val):
        self._filters.append(("eq", col, val))
        return self

    def neq(self, col, val):
        self._filters.append(("neq", col, val))
        return self

    def in_(self, col, vals):
        self._filters.append(("in", col, vals))
        return self

    def order(self, col, *, desc=False):
        self._order_key = col
        self._desc = desc
        return self

    def limit(self, n):
        self._limit_n = n
        return self

    def execute(self):
        rows = list(self._rows)

        # Inner-join embed: attach the matching document_assets row.
        # !inner semantics: rows with no matching doc are excluded.
        if self._embed_docs:
            doc_by_id = {d["id"]: d for d in self._docs}
            rows = [
                {**r, "document_assets": doc_by_id[r["document_id"]]}
                for r in rows
                if r.get("document_id") in doc_by_id
            ]

        for op, col, val in self._filters:
            if "." in col:
                # Embedded resource filter: "resource.field"
                resource, field = col.split(".", 1)
                if op == "eq":
                    rows = [r for r in rows if (r.get(resource) or {}).get(field) == val]
                elif op == "in":
                    rows = [r for r in rows if (r.get(resource) or {}).get(field) in val]
                elif op == "neq":
                    rows = [r for r in rows if (r.get(resource) or {}).get(field) != val]
            elif op == "eq":
                rows = [r for r in rows if r.get(col) == val]
            elif op == "in":
                rows = [r for r in rows if r.get(col) in val]
            elif op == "neq":
                rows = [r for r in rows if r.get(col) != val]

        if self._op == "update" and self._update_payload:
            for r in rows:
                r.update(self._update_payload)
        if self._order_key:
            rows = sorted(rows, key=lambda r: r.get(self._order_key, ""), reverse=self._desc)
        if self._limit_n is not None:
            rows = rows[: self._limit_n]
        return _R(rows)


class _Sb:
    def __init__(self, jobs: list[dict], docs: list[dict] | None = None):
        self._jobs = jobs
        self._docs = docs or []

    def table(self, name: str):
        if name == "document_processing_jobs":
            return _Q(self._jobs, self._docs)
        if name == "document_assets":
            return _Q(self._docs)
        raise KeyError(name)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _job(
    job_id=None,
    document_id=None,
    status="queued",
    created_at="2026-01-01T00:00:00Z",
    error_code=None,
    attempt_count=0,
    finished_at=None,
):
    """Build a document_processing_jobs row. No scope field — scope lives on
    document_assets and is resolved via the inner-join embed."""
    return {
        "id": job_id or str(uuid4()),
        "document_id": document_id or str(uuid4()),
        "job_type": "text_extract",
        "status": status,
        "created_at": created_at,
        "error_code": error_code,
        "attempt_count": attempt_count,
        "finished_at": finished_at,
    }


def _doc(doc_id=None, scope="admin_exam_intelligence", owner_user_id=None):
    return {
        "id": doc_id or str(uuid4()),
        "scope": scope,
        "status": "processing",
        "owner_user_id": owner_user_id,
    }


# ── claim_next_text_extract_job ──────────────────────────────────────────────


def test_claim_empty_queue():
    sb = _Sb(jobs=[])
    assert claim_next_text_extract_job(sb) is None


def test_claim_returns_oldest_admin_queued():
    doc_id = str(uuid4())
    doc = _doc(doc_id=doc_id, scope="admin_exam_intelligence")
    j_old = _job(document_id=doc_id, status="queued", created_at="2026-01-01T00:00:00Z")
    j_new = _job(document_id=doc_id, status="queued", created_at="2026-01-02T00:00:00Z")
    sb = _Sb(jobs=[j_new, j_old], docs=[doc])
    result = claim_next_text_extract_job(sb)
    assert result["id"] == j_old["id"]


def test_claim_ignores_non_queued():
    doc_id = str(uuid4())
    doc = _doc(doc_id=doc_id, scope="admin_exam_intelligence")
    j_running = _job(document_id=doc_id, status="running")
    j_failed = _job(document_id=doc_id, status="failed")
    j_succeeded = _job(document_id=doc_id, status="succeeded")
    sb = _Sb(jobs=[j_running, j_failed, j_succeeded], docs=[doc])
    assert claim_next_text_extract_job(sb) is None


def test_claim_excludes_personal_library_scope():
    """Jobs whose parent document has scope='personal_library' must never be
    claimed — scope is resolved through document_assets, not the job row."""
    doc_personal = _doc(scope="personal_library")
    doc_admin = _doc(scope="admin_exam_intelligence")
    j_personal = _job(document_id=doc_personal["id"], status="queued",
                       created_at="2026-01-01T00:00:00Z")
    j_admin = _job(document_id=doc_admin["id"], status="queued",
                   created_at="2026-01-02T00:00:00Z")
    sb = _Sb(jobs=[j_personal, j_admin], docs=[doc_personal, doc_admin])
    result = claim_next_text_extract_job(sb)
    assert result is not None
    assert result["id"] == j_admin["id"]


def test_claim_excludes_unknown_scope():
    """Jobs whose parent document has an unrecognised scope are excluded."""
    doc = _doc(scope="some_other_scope")
    j = _job(document_id=doc["id"], status="queued")
    sb = _Sb(jobs=[j], docs=[doc])
    assert claim_next_text_extract_job(sb) is None


def test_claim_excludes_job_with_no_matching_document():
    """!inner semantics: a job with no document_assets row is excluded."""
    j = _job(status="queued")  # document_id points nowhere
    sb = _Sb(jobs=[j], docs=[])
    assert claim_next_text_extract_job(sb) is None


def test_claim_result_contains_embedded_scope():
    """The returned row includes the embedded document_assets so run_worker_pass
    can forward the correct admin_scope without a second query."""
    doc = _doc(scope="admin_exam_intelligence")
    j = _job(document_id=doc["id"], status="queued")
    sb = _Sb(jobs=[j], docs=[doc])
    result = claim_next_text_extract_job(sb)
    assert result is not None
    assert result["document_assets"]["scope"] == "admin_exam_intelligence"


# ── run_worker_pass ──────────────────────────────────────────────────────────


def test_run_worker_pass_idle():
    sb = _Sb(jobs=[])
    result = run_worker_pass(sb)
    assert result["processed"] == 0
    assert result["status"] == "idle"
    assert result["job_id"] is None


def test_run_worker_pass_success():
    doc_id = str(uuid4())
    job_id = str(uuid4())
    doc = _doc(doc_id=doc_id, scope="admin_exam_intelligence")
    j = _job(job_id=job_id, document_id=doc_id, status="queued")
    sb = _Sb(jobs=[j], docs=[doc])

    fake_result = {"job": {"id": job_id, "status": "succeeded"}, "document": {}}
    with patch(
        "app.library.text_extract_worker.run_text_extract_job",
        return_value=fake_result,
    ) as mock_run:
        result = run_worker_pass(sb)

    assert result["processed"] == 1
    assert result["status"] == "succeeded"
    assert result["job_id"] == job_id
    assert result["error"] is None
    # admin_scope must come from the embedded document_assets row, not hard-coded.
    mock_run.assert_called_once_with(
        sb, job_id, user_id=None, admin_scope="admin_exam_intelligence"
    )


def test_run_worker_pass_conflict():
    from app.library.text_extract import ExtractConflict

    doc_id = str(uuid4())
    job_id = str(uuid4())
    doc = _doc(doc_id=doc_id, scope="admin_exam_intelligence")
    j = _job(job_id=job_id, document_id=doc_id, status="queued")
    sb = _Sb(jobs=[j], docs=[doc])

    with patch(
        "app.library.text_extract_worker.run_text_extract_job",
        side_effect=ExtractConflict("already claimed"),
    ):
        result = run_worker_pass(sb)

    assert result["processed"] == 0
    assert result["status"] == "conflict"
    assert result["job_id"] == job_id


def test_run_worker_pass_extract_error_sets_failed():
    """_ExtractError from run_text_extract_job (after internal _fail) → status='failed'."""
    from app.library.text_extract import _ExtractError

    doc_id = str(uuid4())
    job_id = str(uuid4())
    doc = _doc(doc_id=doc_id, scope="admin_exam_intelligence")
    j = _job(job_id=job_id, document_id=doc_id, status="queued")
    sb = _Sb(jobs=[j], docs=[doc])

    with patch(
        "app.library.text_extract_worker.run_text_extract_job",
        side_effect=_ExtractError("parser_crash", "pypdf blew up"),
    ):
        result = run_worker_pass(sb)

    assert result["processed"] == 1
    assert result["status"] == "failed"
    assert "pypdf blew up" in result["error"]


def test_run_worker_pass_unhandled_error_fallback_recovery():
    """An unexpected exception triggers the fallback UPDATE to prevent both
    a stranded 'running' job and a stuck 'processing' document_assets row.

    claim_next_text_extract_job is mocked to bypass the SELECT so we can
    test the exception path regardless of job status in the DB.
    """
    doc_id = str(uuid4())
    job_id = str(uuid4())
    candidate = {
        "id": job_id,
        "document_id": doc_id,
        "document_assets": {"scope": "admin_exam_intelligence"},
    }
    sb = _Sb(jobs=[])  # empty — claim is mocked below

    with patch(
        "app.library.text_extract_worker.claim_next_text_extract_job",
        return_value=candidate,
    ), patch(
        "app.library.text_extract_worker.run_text_extract_job",
        side_effect=RuntimeError("unexpected transport error"),
    ), patch(
        "app.library.text_extract_worker._fallback_fail_job"
    ) as mock_fallback:
        result = run_worker_pass(sb)

    # Fallback must receive document_id so it can update both rows.
    mock_fallback.assert_called_once_with(sb, job_id, doc_id, "unexpected transport error")
    assert result["processed"] == 1
    assert result["status"] == "failed"


# ── _fallback_fail_job ───────────────────────────────────────────────────────


def test_fallback_fail_job_writes_failed_to_job_and_document():
    """_fallback_fail_job flips both the job row (WHERE status='running') and
    the parent document_assets row (WHERE status != 'archived') to 'failed'."""
    doc_id = str(uuid4())
    job_id = str(uuid4())
    job_row = {"id": job_id, "status": "running"}
    doc_row = {"id": doc_id, "status": "processing"}
    sb = _Sb(jobs=[job_row], docs=[doc_row])

    _fallback_fail_job(sb, job_id, doc_id, "transport error")

    assert job_row["status"] == "failed"
    assert job_row["error_code"] == "worker_unhandled_error"
    assert doc_row["status"] == "failed"


def test_fallback_fail_job_does_not_clobber_archived_document():
    """An archived document must stay archived even when the job fails."""
    doc_id = str(uuid4())
    job_id = str(uuid4())
    job_row = {"id": job_id, "status": "running"}
    doc_row = {"id": doc_id, "status": "archived"}
    sb = _Sb(jobs=[job_row], docs=[doc_row])

    _fallback_fail_job(sb, job_id, doc_id, "transport error")

    assert job_row["status"] == "failed"
    assert doc_row["status"] == "archived"  # not touched


def test_fallback_fail_job_does_not_update_job_unless_running():
    """Scoped to status='running': a job that is already terminal is not clobbered,
    and critically the document is also left untouched (conditional guard)."""
    doc_id = str(uuid4())
    job_id = str(uuid4())
    job_row = {"id": job_id, "status": "succeeded"}
    doc_row = {"id": doc_id, "status": "processed"}
    sb = _Sb(jobs=[job_row], docs=[doc_row])

    _fallback_fail_job(sb, job_id, doc_id, "late error")

    assert job_row["status"] == "succeeded"  # unchanged
    assert doc_row["status"] == "processed"  # not clobbered when job CAS missed


def test_fallback_fail_job_does_not_crash_on_sb_error():
    """A DB failure in the fallback must be swallowed (best-effort)."""
    class _BadSb:
        def table(self, _):
            raise RuntimeError("DB unavailable")

    _fallback_fail_job(_BadSb(), str(uuid4()), str(uuid4()), "some error")


# ── fail-closed final_status ────────────────────────────────────────────────


def test_run_worker_pass_missing_job_row_returns_failed():
    """If run_text_extract_job returns a result with no 'job' key, the worker
    must fail-closed (status='failed') rather than assuming success."""
    doc_id = str(uuid4())
    job_id = str(uuid4())
    doc = _doc(doc_id=doc_id, scope="admin_exam_intelligence")
    j = _job(job_id=job_id, document_id=doc_id, status="queued")
    sb = _Sb(jobs=[j], docs=[doc])

    with patch(
        "app.library.text_extract_worker.run_text_extract_job",
        return_value={},  # no 'job' key
    ):
        result = run_worker_pass(sb)

    assert result["processed"] == 1
    assert result["status"] == "failed"


def test_run_worker_pass_unexpected_final_status_returns_failed():
    """An unrecognised status string must be normalised to 'failed'."""
    doc_id = str(uuid4())
    job_id = str(uuid4())
    doc = _doc(doc_id=doc_id, scope="admin_exam_intelligence")
    j = _job(job_id=job_id, document_id=doc_id, status="queued")
    sb = _Sb(jobs=[j], docs=[doc])

    with patch(
        "app.library.text_extract_worker.run_text_extract_job",
        return_value={"job": {"id": job_id, "status": "unknown_state"}},
    ):
        result = run_worker_pass(sb)

    assert result["processed"] == 1
    assert result["status"] == "failed"


# ── claim_next_retry_job ─────────────────────────────────────────────────────


def test_retry_returns_transient_failed_job_past_backoff():
    """A failed job with a transient error_code, under the attempt cap, and past
    the backoff window is returned by claim_next_retry_job."""
    doc = _doc(scope="admin_exam_intelligence")
    j = _job(
        document_id=doc["id"],
        status="failed",
        error_code="download_failed",
        attempt_count=1,
        finished_at="2020-01-01T00:00:00Z",  # far in the past → past backoff
    )
    sb = _Sb(jobs=[j], docs=[doc])
    result = claim_next_retry_job(sb)
    assert result is not None
    assert result["id"] == j["id"]


def test_retry_skips_terminal_error_code():
    """A failed job with a terminal error_code (e.g. unsupported_mime) must
    never be returned by claim_next_retry_job."""
    doc = _doc(scope="admin_exam_intelligence")
    j = _job(
        document_id=doc["id"],
        status="failed",
        error_code="unsupported_mime",
        attempt_count=1,
        finished_at="2020-01-01T00:00:00Z",
    )
    sb = _Sb(jobs=[j], docs=[doc])
    assert claim_next_retry_job(sb) is None


def test_retry_skips_job_at_max_attempts():
    """A job that has already reached MAX_TRANSIENT_ATTEMPTS must not be
    retried even if its error_code is transient."""
    doc = _doc(scope="admin_exam_intelligence")
    j = _job(
        document_id=doc["id"],
        status="failed",
        error_code="download_failed",
        attempt_count=MAX_TRANSIENT_ATTEMPTS,
        finished_at="2020-01-01T00:00:00Z",
    )
    sb = _Sb(jobs=[j], docs=[doc])
    assert claim_next_retry_job(sb) is None


def test_retry_respects_backoff_window():
    """A job whose backoff window has not expired (finished_at is too recent)
    is not returned even if it is otherwise retry-eligible."""
    from datetime import datetime, timezone

    doc = _doc(scope="admin_exam_intelligence")
    # finished_at is 1 second ago; attempt_count=1 → need BASE_BACKOFF_SECONDS
    just_failed = datetime.now(timezone.utc).isoformat()
    j = _job(
        document_id=doc["id"],
        status="failed",
        error_code="download_failed",
        attempt_count=1,
        finished_at=just_failed,
    )
    sb = _Sb(jobs=[j], docs=[doc])
    assert claim_next_retry_job(sb) is None


def test_retry_pass_requeues_and_runs_failed_job():
    """run_worker_pass re-queues a retry-eligible failed job before calling
    run_text_extract_job, allowing _claim_job (which requires status='queued')
    to atomically claim it."""
    doc_id = str(uuid4())
    job_id = str(uuid4())
    doc = _doc(doc_id=doc_id, scope="admin_exam_intelligence")
    j = _job(
        job_id=job_id,
        document_id=doc_id,
        status="failed",
        error_code="download_failed",
        attempt_count=1,
        finished_at="2020-01-01T00:00:00Z",
    )
    sb = _Sb(jobs=[j], docs=[doc])

    fake_result = {"job": {"id": job_id, "status": "succeeded"}, "document": {}}
    with patch(
        "app.library.text_extract_worker.run_text_extract_job",
        return_value=fake_result,
    ) as mock_run:
        result = run_worker_pass(sb)

    assert result["processed"] == 1
    assert result["status"] == "succeeded"
    assert result["job_id"] == job_id
    # The job must have been re-queued (status flipped to 'queued') so
    # _claim_job inside run_text_extract_job can atomically claim it.
    assert j["status"] == "queued"
    mock_run.assert_called_once_with(sb, job_id, user_id=None, admin_scope="admin_exam_intelligence")


def test_retry_not_attempted_when_queued_job_exists():
    """The normal FIFO queued path takes priority over the retry path.
    If a queued job exists, claim_next_retry_job must not be called."""
    doc_id = str(uuid4())
    job_id_queued = str(uuid4())
    job_id_failed = str(uuid4())
    doc = _doc(doc_id=doc_id, scope="admin_exam_intelligence")
    j_queued = _job(job_id=job_id_queued, document_id=doc_id, status="queued")
    j_failed = _job(
        job_id=job_id_failed,
        document_id=doc_id,
        status="failed",
        error_code="download_failed",
        attempt_count=1,
        finished_at="2020-01-01T00:00:00Z",
    )
    sb = _Sb(jobs=[j_queued, j_failed], docs=[doc])

    fake_result = {"job": {"id": job_id_queued, "status": "succeeded"}, "document": {}}
    with patch(
        "app.library.text_extract_worker.run_text_extract_job",
        return_value=fake_result,
    ) as mock_run:
        result = run_worker_pass(sb)

    assert result["job_id"] == job_id_queued
    assert result["status"] == "succeeded"
    mock_run.assert_called_once()


# ── _ADMIN_SCOPES constant ───────────────────────────────────────────────────


def test_admin_scopes_contains_expected():
    assert "admin_exam_intelligence" in _ADMIN_SCOPES


def test_personal_library_not_in_admin_scopes():
    assert "personal_library" not in _ADMIN_SCOPES


def test_transient_error_codes_contains_expected():
    assert _TRANSIENT_ERROR_CODES >= {"download_failed", "storage_object_missing", "page_write_failed"}


def test_terminal_codes_not_in_transient_set():
    for code in ("unsupported_mime", "ownership_mismatch", "scope_mismatch",
                 "archived", "file_too_large_for_extract", "extract_timeout"):
        assert code not in _TRANSIENT_ERROR_CODES, f"{code} must be terminal"
