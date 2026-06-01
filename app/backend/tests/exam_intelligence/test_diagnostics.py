"""Tests for the diagnostics module and endpoints (orphans + stuck rows)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intel_cms as cms_api
from app.core.auth import get_current_user
from app.exam_intelligence.diagnostics import (
    find_orphan_questions,
    find_stuck_documents,
    find_stuck_text_extract_jobs,
)
from tests.persona_questions._stub import SBStub

_BASE = "/api/admin/exam-intelligence-cms"

# ── Timestamp helpers ─────────────────────────────────────────────────────────

def _iso_ago(minutes: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()


def _iso_future(minutes: int = 5) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


# ── SBStub factory ────────────────────────────────────────────────────────────

def _sb(**tables) -> SBStub:
    sb = SBStub()
    for name, rows in tables.items():
        sb.db[name] = list(rows)
    return sb


def _client(sb: SBStub, *, flag: bool = True, perm: bool = True) -> TestClient:
    app = FastAPI()
    app.include_router(cms_api.router, prefix="/api")
    cms_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    if flag:
        app.dependency_overrides[cms_api._flag_enabled] = lambda: None
    user = {
        "id": "admin-1",
        "email": "admin@test.com",
        "role": "super_admin" if perm else "viewer",
        "permissions": ["exam_intelligence.cms"] if perm else [],
    }
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


# ── Unit: find_orphan_questions ───────────────────────────────────────────────

def test_find_orphan_questions_returns_orphans():
    sb = _sb(
        pyq_papers=[{"id": "paper-1", "exam_id": "exam-1", "year": 2024, "exam_cycle_id": None}],
        pyq_questions=[
            {"id": "q-orphan", "pyq_paper_id": "paper-1", "question_number": 1, "created_at": _iso_ago(10)},
            {"id": "q-with-opts", "pyq_paper_id": "paper-1", "question_number": 2, "created_at": _iso_ago(5)},
        ],
        pyq_options=[
            {"id": "opt-1", "question_id": "q-with-opts"},
        ],
    )
    result = find_orphan_questions(sb)
    ids = [r["id"] for r in result]
    assert "q-orphan" in ids
    assert "q-with-opts" not in ids


def test_find_orphan_questions_excludes_questions_with_options():
    sb = _sb(
        pyq_papers=[{"id": "paper-1", "exam_id": "exam-1", "year": 2024, "exam_cycle_id": None}],
        pyq_questions=[
            {"id": "q-1", "pyq_paper_id": "paper-1", "question_number": 1, "created_at": _iso_ago(5)},
        ],
        pyq_options=[
            {"id": "opt-a", "question_id": "q-1"},
            {"id": "opt-b", "question_id": "q-1"},
        ],
    )
    result = find_orphan_questions(sb)
    assert result == []


def test_find_orphan_questions_scoped_by_exam_id():
    sb = _sb(
        pyq_papers=[
            {"id": "paper-1", "exam_id": "exam-A", "year": 2024, "exam_cycle_id": None},
            {"id": "paper-2", "exam_id": "exam-B", "year": 2023, "exam_cycle_id": None},
        ],
        pyq_questions=[
            {"id": "q-A", "pyq_paper_id": "paper-1", "question_number": 1, "created_at": _iso_ago(5)},
            {"id": "q-B", "pyq_paper_id": "paper-2", "question_number": 1, "created_at": _iso_ago(5)},
        ],
        pyq_options=[],
    )
    result = find_orphan_questions(sb, exam_id="exam-A")
    ids = [r["id"] for r in result]
    assert "q-A" in ids
    assert "q-B" not in ids


# ── Unit: find_stuck_documents ────────────────────────────────────────────────

def test_find_stuck_documents_respects_age_minutes():
    sb = _sb(
        document_assets=[
            {"id": "doc-old", "status": "processing", "updated_at": _iso_ago(60), "created_at": _iso_ago(90)},
            {"id": "doc-recent", "status": "processing", "updated_at": _iso_ago(10), "created_at": _iso_ago(20)},
            {"id": "doc-processed", "status": "processed", "updated_at": _iso_ago(60), "created_at": _iso_ago(90)},
        ]
    )
    result = find_stuck_documents(sb, age_minutes=30)
    ids = [r["id"] for r in result]
    assert "doc-old" in ids
    assert "doc-recent" not in ids
    assert "doc-processed" not in ids


# ── Unit: find_stuck_text_extract_jobs ────────────────────────────────────────

def test_find_stuck_text_extract_jobs_respects_age_minutes():
    sb = _sb(
        document_processing_jobs=[
            {"id": "job-old", "job_type": "text_extract", "status": "running",
             "started_at": _iso_ago(60), "document_id": "doc-1", "error_code": None, "error_message": None},
            {"id": "job-recent", "job_type": "text_extract", "status": "running",
             "started_at": _iso_ago(10), "document_id": "doc-2", "error_code": None, "error_message": None},
            {"id": "job-done", "job_type": "text_extract", "status": "succeeded",
             "started_at": _iso_ago(60), "document_id": "doc-3", "error_code": None, "error_message": None},
            {"id": "job-other-type", "job_type": "ocr", "status": "running",
             "started_at": _iso_ago(60), "document_id": "doc-4", "error_code": None, "error_message": None},
        ]
    )
    result = find_stuck_text_extract_jobs(sb, age_minutes=30)
    ids = [r["id"] for r in result]
    assert "job-old" in ids
    assert "job-recent" not in ids
    assert "job-done" not in ids
    assert "job-other-type" not in ids


# ── API: GET /diagnostics ─────────────────────────────────────────────────────

def test_get_diagnostics_returns_three_buckets():
    sb = _sb(
        pyq_papers=[{"id": "paper-1", "exam_id": "exam-1", "year": 2024, "exam_cycle_id": None}],
        pyq_questions=[
            {"id": "q-orphan", "pyq_paper_id": "paper-1", "question_number": 1, "created_at": _iso_ago(5)},
        ],
        pyq_options=[],
        document_assets=[
            {"id": "doc-1", "status": "processing", "updated_at": _iso_ago(60), "created_at": _iso_ago(90)},
        ],
        document_processing_jobs=[
            {"id": "job-1", "job_type": "text_extract", "status": "running",
             "started_at": _iso_ago(60), "document_id": "doc-1", "error_code": None, "error_message": None},
        ],
    )
    resp = _client(sb).get(f"{_BASE}/diagnostics")
    assert resp.status_code == 200
    data = resp.json()
    assert "generated_at" in data
    assert data["thresholds"]["stuck_age_minutes"] == 30
    assert data["orphan_questions"]["count"] == 1
    assert data["orphan_questions"]["rows"][0]["id"] == "q-orphan"
    assert data["stuck_documents"]["count"] == 1
    assert data["stuck_text_extract_jobs"]["count"] == 1


def test_get_diagnostics_exam_id_filters_orphans():
    sb = _sb(
        pyq_papers=[
            {"id": "paper-A", "exam_id": "exam-A", "year": 2024, "exam_cycle_id": None},
            {"id": "paper-B", "exam_id": "exam-B", "year": 2024, "exam_cycle_id": None},
        ],
        pyq_questions=[
            {"id": "q-A", "pyq_paper_id": "paper-A", "question_number": 1, "created_at": _iso_ago(5)},
            {"id": "q-B", "pyq_paper_id": "paper-B", "question_number": 1, "created_at": _iso_ago(5)},
        ],
        pyq_options=[],
        document_assets=[],
        document_processing_jobs=[],
    )
    resp = _client(sb).get(f"{_BASE}/diagnostics?exam_id=exam-A")
    assert resp.status_code == 200
    ids = [r["id"] for r in resp.json()["orphan_questions"]["rows"]]
    assert "q-A" in ids
    assert "q-B" not in ids


# ── API: POST /diagnostics/orphan-question/{id}/delete ───────────────────────

def test_delete_orphan_question_deletes_and_audits():
    sb = _sb(
        pyq_questions=[
            {"id": "q-1", "pyq_paper_id": "paper-1", "question_number": 1, "created_at": _iso_ago(5)},
        ],
        pyq_options=[],
        admin_audit_logs=[],
    )
    resp = _client(sb).post(
        f"{_BASE}/diagnostics/orphan-question/q-1/delete",
        json={"reason": "orphan cleanup"},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    # Row deleted
    remaining = [r for r in sb.db.get("pyq_questions", []) if r["id"] == "q-1"]
    assert remaining == []
    # Audit log written
    logs = sb.db.get("admin_audit_logs", [])
    assert any("orphan_question" in l.get("action", "") for l in logs)


def test_delete_orphan_question_409_when_question_gained_options():
    sb = _sb(
        pyq_questions=[
            {"id": "q-1", "pyq_paper_id": "paper-1", "question_number": 1, "created_at": _iso_ago(5)},
        ],
        pyq_options=[{"id": "opt-1", "question_id": "q-1"}],
        admin_audit_logs=[],
    )
    resp = _client(sb).post(
        f"{_BASE}/diagnostics/orphan-question/q-1/delete",
        json={"reason": "orphan cleanup"},
    )
    assert resp.status_code == 409
    # Row intact
    remaining = [r for r in sb.db.get("pyq_questions", []) if r["id"] == "q-1"]
    assert len(remaining) == 1


# ── API: POST /diagnostics/stuck-document/{id}/reset ─────────────────────────

def test_reset_stuck_document_flips_to_uploaded():
    sb = _sb(
        document_assets=[
            {"id": "doc-1", "status": "processing", "updated_at": _iso_ago(60), "created_at": _iso_ago(90)},
        ],
        admin_audit_logs=[],
    )
    resp = _client(sb).post(
        f"{_BASE}/diagnostics/stuck-document/doc-1/reset",
        json={"reason": "stuck for 1h"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["new_status"] == "uploaded"
    updated = next(r for r in sb.db["document_assets"] if r["id"] == "doc-1")
    assert updated["status"] == "uploaded"


def test_reset_stuck_document_409_when_already_processed():
    sb = _sb(
        document_assets=[
            {"id": "doc-1", "status": "processed", "updated_at": _iso_ago(5), "created_at": _iso_ago(90)},
        ],
        admin_audit_logs=[],
    )
    resp = _client(sb).post(
        f"{_BASE}/diagnostics/stuck-document/doc-1/reset",
        json={"reason": "reset attempt"},
    )
    assert resp.status_code == 409


# ── API: POST /diagnostics/stuck-job/{id}/reset ───────────────────────────────

def test_reset_stuck_job_flips_to_failed_with_manual_reset_code():
    sb = _sb(
        document_processing_jobs=[
            {"id": "job-1", "job_type": "text_extract", "status": "running",
             "started_at": _iso_ago(60), "document_id": "doc-1", "error_code": None, "error_message": None},
        ],
        admin_audit_logs=[],
    )
    resp = _client(sb).post(
        f"{_BASE}/diagnostics/stuck-job/job-1/reset",
        json={"reason": "manual reset by ops"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["new_status"] == "failed"
    assert data["error_code"] == "manual_reset"
    updated = next(r for r in sb.db["document_processing_jobs"] if r["id"] == "job-1")
    assert updated["status"] == "failed"
    assert updated["error_code"] == "manual_reset"
    assert updated["error_message"] == "manual reset by ops"


# ── Validation: reason required (422) ────────────────────────────────────────

@pytest.mark.parametrize("url", [
    "/diagnostics/orphan-question/q-1/delete",
    "/diagnostics/stuck-document/doc-1/reset",
    "/diagnostics/stuck-job/job-1/reset",
])
def test_action_endpoints_require_reason(url):
    sb = _sb(pyq_options=[], admin_audit_logs=[])
    resp = _client(sb).post(f"{_BASE}{url}", json={})
    assert resp.status_code == 422


# ── Permission: 403 without exam_intelligence.cms ────────────────────────────

def test_get_diagnostics_requires_cms_permission():
    sb = _sb(pyq_papers=[], pyq_questions=[], pyq_options=[],
             document_assets=[], document_processing_jobs=[])
    resp = _client(sb, perm=False).get(f"{_BASE}/diagnostics")
    assert resp.status_code == 403


def test_delete_orphan_requires_cms_permission():
    sb = _sb(pyq_options=[], admin_audit_logs=[])
    resp = _client(sb, perm=False).post(
        f"{_BASE}/diagnostics/orphan-question/q-1/delete",
        json={"reason": "test"},
    )
    assert resp.status_code == 403


def test_reset_document_requires_cms_permission():
    sb = _sb(document_assets=[], admin_audit_logs=[])
    resp = _client(sb, perm=False).post(
        f"{_BASE}/diagnostics/stuck-document/doc-1/reset",
        json={"reason": "test"},
    )
    assert resp.status_code == 403


def test_reset_job_requires_cms_permission():
    sb = _sb(document_processing_jobs=[], admin_audit_logs=[])
    resp = _client(sb, perm=False).post(
        f"{_BASE}/diagnostics/stuck-job/job-1/reset",
        json={"reason": "test"},
    )
    assert resp.status_code == 403
