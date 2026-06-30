"""Tests for text_extract_worker.py (issue #540).

Covers:
- claim_next_text_extract_job: empty queue, FIFO ordering, non-queued rows
  ignored, non-admin scopes excluded
- run_worker_pass: idle, success, conflict race, failure with fallback recovery
- Admin-scope routing: admin_exam_intelligence → admin_scope= param
- Fallback failure recovery: stranded 'running' job flipped to 'failed'
- _ADMIN_SCOPES constant
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, call, patch
from uuid import uuid4

import pytest

from app.library.text_extract_worker import (
    _ADMIN_SCOPES,
    _fallback_fail_job,
    claim_next_text_extract_job,
    run_worker_pass,
)


# ── Minimal Supabase stub ────────────────────────────────────────────────────


class _R:
    def __init__(self, data):
        self.data = data


class _Q:
    """Chainable query stub. Stores filters, executes against an in-memory list."""

    def __init__(self, rows: list[dict]):
        self._rows = rows
        self._filters: list[tuple] = []
        self._order_key: str | None = None
        self._desc = False
        self._limit_n: int | None = None
        self._update_payload: dict | None = None
        self._op = "select"

    def select(self, *_a, **_kw):
        self._op = "select"
        return self

    def update(self, payload: dict):
        self._op = "update"
        self._update_payload = payload
        return self

    def eq(self, col, val):
        self._filters.append(("eq", col, val))
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
        for op, col, val in self._filters:
            if op == "eq":
                rows = [r for r in rows if r.get(col) == val]
            elif op == "in":
                rows = [r for r in rows if r.get(col) in val]
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
            return _Q(self._jobs)
        if name == "document_assets":
            return _Q(self._docs)
        raise KeyError(name)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _job(
    job_id=None,
    document_id=None,
    status="queued",
    scope="admin_exam_intelligence",
    created_at="2026-01-01T00:00:00Z",
):
    return {
        "id": job_id or str(uuid4()),
        "document_id": document_id or str(uuid4()),
        "job_type": "text_extract",
        "status": status,
        "scope": scope,
        "created_at": created_at,
    }


def _doc(doc_id=None, scope="admin_exam_intelligence", owner_user_id=None):
    return {
        "id": doc_id or str(uuid4()),
        "scope": scope,
        "owner_user_id": owner_user_id,
    }


# ── claim_next_text_extract_job ──────────────────────────────────────────────


def test_claim_empty_queue():
    sb = _Sb(jobs=[])
    assert claim_next_text_extract_job(sb) is None


def test_claim_returns_oldest_admin_queued():
    doc_id = str(uuid4())
    j_old = _job(document_id=doc_id, status="queued", created_at="2026-01-01T00:00:00Z")
    j_new = _job(document_id=doc_id, status="queued", created_at="2026-01-02T00:00:00Z")
    sb = _Sb(jobs=[j_new, j_old])
    result = claim_next_text_extract_job(sb)
    assert result["id"] == j_old["id"]


def test_claim_ignores_non_queued():
    j_running = _job(status="running")
    j_failed = _job(status="failed")
    j_succeeded = _job(status="succeeded")
    sb = _Sb(jobs=[j_running, j_failed, j_succeeded])
    assert claim_next_text_extract_job(sb) is None


def test_claim_excludes_personal_library_scope():
    """Personal-library jobs must never be claimed by the admin worker."""
    j_personal = _job(status="queued", scope="personal_library")
    j_admin = _job(status="queued", scope="admin_exam_intelligence",
                   created_at="2026-01-02T00:00:00Z")
    sb = _Sb(jobs=[j_personal, j_admin])
    result = claim_next_text_extract_job(sb)
    # Only the admin-scoped job is returned
    assert result is not None
    assert result["id"] == j_admin["id"]


def test_claim_excludes_unknown_scope():
    j = _job(status="queued", scope="some_other_scope")
    sb = _Sb(jobs=[j])
    assert claim_next_text_extract_job(sb) is None


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
    j = _job(job_id=job_id, document_id=doc_id, status="queued",
             scope="admin_exam_intelligence")
    sb = _Sb(jobs=[j])

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
    # Admin scope is always passed for admin worker
    mock_run.assert_called_once_with(
        sb, job_id, user_id=None, admin_scope="admin_exam_intelligence"
    )


def test_run_worker_pass_conflict():
    from app.library.text_extract import ExtractConflict

    doc_id = str(uuid4())
    job_id = str(uuid4())
    j = _job(job_id=job_id, document_id=doc_id, status="queued")
    sb = _Sb(jobs=[j])

    with patch(
        "app.library.text_extract_worker.run_text_extract_job",
        side_effect=ExtractConflict("already claimed"),
    ):
        result = run_worker_pass(sb)

    # Conflict: race loss, job not attempted by this worker
    assert result["processed"] == 0
    assert result["status"] == "conflict"
    assert result["job_id"] == job_id


def test_run_worker_pass_extract_error_sets_failed():
    """_ExtractError from run_text_extract_job (after internal _fail) → status='failed'."""
    from app.library.text_extract import _ExtractError

    doc_id = str(uuid4())
    job_id = str(uuid4())
    j = _job(job_id=job_id, document_id=doc_id, status="queued")
    sb = _Sb(jobs=[j])

    with patch(
        "app.library.text_extract_worker.run_text_extract_job",
        side_effect=_ExtractError("parser_crash", "pypdf blew up"),
    ):
        result = run_worker_pass(sb)

    assert result["processed"] == 1
    assert result["status"] == "failed"
    assert "pypdf blew up" in result["error"]


def test_run_worker_pass_unhandled_error_fallback_recovery():
    """An unexpected exception triggers the fallback UPDATE to prevent a stranded 'running' job.

    claim_next_text_extract_job is mocked to bypass the SELECT so we can test
    the exception path regardless of job status in the DB.
    """
    doc_id = str(uuid4())
    job_id = str(uuid4())
    candidate = {"id": job_id, "document_id": doc_id}
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

    # Fallback was called to flip the stranded 'running' job to 'failed'
    mock_fallback.assert_called_once_with(sb, job_id, "unexpected transport error")
    assert result["processed"] == 1
    assert result["status"] == "failed"


def test_fallback_fail_job_writes_failed_only_if_running():
    """_fallback_fail_job uses a conditional UPDATE (status='running') to avoid
    clobbering jobs that were already recovered by another path."""
    job_id = str(uuid4())
    job_row = {"id": job_id, "status": "running"}
    sb = _Sb(jobs=[job_row])

    _fallback_fail_job(sb, job_id, "transport error")

    # The stub applies the update in-place; verify status was flipped
    assert job_row["status"] == "failed"
    assert job_row["error_code"] == "worker_unhandled_error"


def test_fallback_fail_job_does_not_crash_on_sb_error():
    """A DB failure in the fallback must be swallowed (best-effort)."""
    class _BadSb:
        def table(self, _):
            raise RuntimeError("DB unavailable")

    # Should not raise
    _fallback_fail_job(_BadSb(), str(uuid4()), "some error")


# ── _ADMIN_SCOPES constant ───────────────────────────────────────────────────


def test_admin_scopes_contains_expected():
    assert "admin_exam_intelligence" in _ADMIN_SCOPES


def test_personal_library_not_in_admin_scopes():
    assert "personal_library" not in _ADMIN_SCOPES
