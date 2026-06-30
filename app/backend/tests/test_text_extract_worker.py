"""Tests for text_extract_worker.py (issue #540).

Covers:
- claim_next_text_extract_job: empty queue → None, non-empty → oldest queued row
- run_worker_pass: idle (empty queue), successful run, conflict (race), failure
- Admin-scope detection: admin_exam_intelligence scope uses admin_scope param
- Personal-scope documents: owner_user_id path (scope not in _ADMIN_SCOPES)
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, call, patch
from uuid import uuid4

import pytest

from app.library.text_extract_worker import (
    _ADMIN_SCOPES,
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

    def select(self, *_a, **_kw):
        return self

    def eq(self, col, val):
        self._filters.append(("eq", col, val))
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
        if self._order_key:
            rows = sorted(rows, key=lambda r: r.get(self._order_key, ""), reverse=self._desc)
        if self._limit_n is not None:
            rows = rows[: self._limit_n]
        return _R(rows)


class _Sb:
    def __init__(self, jobs: list[dict], docs: list[dict]):
        self._jobs = jobs
        self._docs = docs

    def table(self, name: str):
        if name == "document_processing_jobs":
            return _Q(self._jobs)
        if name == "document_assets":
            return _Q(self._docs)
        raise KeyError(name)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _job(job_id=None, document_id=None, status="queued", created_at="2026-01-01T00:00:00Z"):
    return {
        "id": job_id or str(uuid4()),
        "document_id": document_id or str(uuid4()),
        "job_type": "text_extract",
        "status": status,
        "created_at": created_at,
    }


def _doc(doc_id=None, scope="library", owner_user_id="user-1"):
    return {
        "id": doc_id or str(uuid4()),
        "scope": scope,
        "owner_user_id": owner_user_id,
    }


# ── claim_next_text_extract_job ──────────────────────────────────────────────


def test_claim_empty_queue():
    sb = _Sb(jobs=[], docs=[])
    assert claim_next_text_extract_job(sb) is None


def test_claim_returns_oldest_queued():
    doc_id = str(uuid4())
    j_old = _job(document_id=doc_id, status="queued", created_at="2026-01-01T00:00:00Z")
    j_new = _job(document_id=doc_id, status="queued", created_at="2026-01-02T00:00:00Z")
    sb = _Sb(jobs=[j_new, j_old], docs=[])
    result = claim_next_text_extract_job(sb)
    assert result["id"] == j_old["id"]


def test_claim_ignores_non_queued():
    j_running = _job(status="running")
    j_failed = _job(status="failed")
    j_succeeded = _job(status="succeeded")
    sb = _Sb(jobs=[j_running, j_failed, j_succeeded], docs=[])
    # All rows filtered to status='queued' — none match
    result = claim_next_text_extract_job(sb)
    assert result is None


def test_claim_returns_queued_ignores_others():
    j_q = _job(status="queued", created_at="2026-01-01T00:00:00Z")
    j_r = _job(status="running")
    sb = _Sb(jobs=[j_r, j_q], docs=[])
    result = claim_next_text_extract_job(sb)
    assert result["id"] == j_q["id"]


# ── run_worker_pass ──────────────────────────────────────────────────────────


def test_run_worker_pass_idle():
    sb = _Sb(jobs=[], docs=[])
    result = run_worker_pass(sb)
    assert result["processed"] == 0
    assert result["status"] == "idle"
    assert result["job_id"] is None


def test_run_worker_pass_success():
    doc_id = str(uuid4())
    job_id = str(uuid4())
    j = _job(job_id=job_id, document_id=doc_id, status="queued")
    d = _doc(doc_id=doc_id, scope="library")
    sb = _Sb(jobs=[j], docs=[d])

    fake_result = {"job": {"id": job_id, "status": "succeeded"}, "document": d}
    with patch(
        "app.library.text_extract_worker.run_text_extract_job",
        return_value=fake_result,
    ) as mock_run:
        result = run_worker_pass(sb)

    assert result["processed"] == 1
    assert result["status"] == "succeeded"
    assert result["job_id"] == job_id
    assert result["error"] is None
    # Non-admin scope → admin_scope=None, user_id=None
    mock_run.assert_called_once_with(sb, job_id, user_id=None, admin_scope=None)


def test_run_worker_pass_admin_scope():
    doc_id = str(uuid4())
    job_id = str(uuid4())
    j = _job(job_id=job_id, document_id=doc_id, status="queued")
    d = _doc(doc_id=doc_id, scope="admin_exam_intelligence", owner_user_id=None)
    sb = _Sb(jobs=[j], docs=[d])

    fake_result = {"job": {"id": job_id, "status": "succeeded"}, "document": d}
    with patch(
        "app.library.text_extract_worker.run_text_extract_job",
        return_value=fake_result,
    ) as mock_run:
        result = run_worker_pass(sb)

    assert result["processed"] == 1
    mock_run.assert_called_once_with(
        sb, job_id, user_id=None, admin_scope="admin_exam_intelligence"
    )


def test_run_worker_pass_conflict():
    from app.library.text_extract import ExtractConflict

    doc_id = str(uuid4())
    job_id = str(uuid4())
    j = _job(job_id=job_id, document_id=doc_id, status="queued")
    d = _doc(doc_id=doc_id)
    sb = _Sb(jobs=[j], docs=[d])

    with patch(
        "app.library.text_extract_worker.run_text_extract_job",
        side_effect=ExtractConflict("already claimed"),
    ):
        result = run_worker_pass(sb)

    # Conflict is not counted as processed — another worker won
    assert result["processed"] == 0
    assert result["status"] == "conflict"
    assert result["job_id"] == job_id


def test_run_worker_pass_failure():
    doc_id = str(uuid4())
    job_id = str(uuid4())
    j = _job(job_id=job_id, document_id=doc_id, status="queued")
    d = _doc(doc_id=doc_id)
    sb = _Sb(jobs=[j], docs=[d])

    with patch(
        "app.library.text_extract_worker.run_text_extract_job",
        side_effect=RuntimeError("parser crash"),
    ):
        result = run_worker_pass(sb)

    # Extraction failed but the job was processed (run attempted)
    assert result["processed"] == 1
    assert result["status"] == "failed"
    assert "parser crash" in result["error"]


def test_run_worker_pass_missing_doc_scope():
    """If the document_assets row is missing, scope defaults to None → admin_scope=None."""
    doc_id = str(uuid4())
    job_id = str(uuid4())
    j = _job(job_id=job_id, document_id=doc_id, status="queued")
    # No matching doc in the stub
    sb = _Sb(jobs=[j], docs=[])

    fake_result = {"job": {"id": job_id, "status": "succeeded"}, "document": None}
    with patch(
        "app.library.text_extract_worker.run_text_extract_job",
        return_value=fake_result,
    ) as mock_run:
        run_worker_pass(sb)

    mock_run.assert_called_once_with(sb, job_id, user_id=None, admin_scope=None)


# ── _ADMIN_SCOPES constant ───────────────────────────────────────────────────


def test_admin_scopes_contains_expected():
    assert "admin_exam_intelligence" in _ADMIN_SCOPES
