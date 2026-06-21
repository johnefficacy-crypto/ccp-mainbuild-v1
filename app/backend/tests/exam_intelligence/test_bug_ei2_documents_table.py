"""Regression test for BUG-EI-2.

GET /api/admin/exam-intelligence/console/exams/{exam_id} was returning 500
because ``_documents()`` queried ``document_assets`` with
``.eq("exam_id", ...)`` and ``.select("id, extraction_status")`` — neither
column exists on that table, so PostgREST raised a 42703 error.

Fix (Option A): query ``syllabus_documents`` (which has ``exam_id`` and
``trust_status``), and count rows where ``trust_status == "verified"`` as the
document readiness proxy.

This file asserts:
1. The endpoint returns 200 (not 500) when ``syllabus_documents`` rows exist.
2. A ``trust_status="verified"`` row is counted as an extracted/verified doc.
3. The endpoint returns 200 with zero doc count when no syllabus_documents rows
   exist (the no-documents path).
4. The ``_documents()`` helper never queries ``document_assets``.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intelligence as admin_api
from app.core.auth import get_current_user
from tests.persona_questions._stub import SBStub


_RECENT = "2026-06-16T00:00:00+00:00"


def _build_app(sb):
    app = FastAPI()
    app.include_router(admin_api.router, prefix="/api")
    admin_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    user = {"id": "admin-1", "role": "super_admin", "permissions": []}
    app.dependency_overrides[get_current_user] = lambda: user
    return app


def _minimal_ready_db(*, syllabus_documents=None):
    """Minimal DB with one fully-ready exam (phases + locked coverage + verified PYQ).

    The ``syllabus_documents`` kwarg lets each test inject its own document rows.
    """
    db = {
        "exams": [
            {"id": "e1", "slug": "ssc-cgl", "name": "SSC CGL", "exam_type": "recruitment",
             "is_active": True, "management_mode": "core", "cadence": "annual",
             "exam_family_id": None, "conducting_organization_id": None},
        ],
        "exam_phases": [{"id": "e1-ph0", "exam_id": "e1"}],
        "exam_topic_coverage": [
            {"id": "e1-cl0", "exam_id": "e1", "reviewer_status": "locked", "created_at": _RECENT},
        ],
        "pyq_papers": [{"id": "e1-pp", "exam_id": "e1", "trust_status": "verified"}],
        "pyq_questions": [
            {"id": "e1-q0", "pyq_paper_id": "e1-pp", "reviewer_status": "verified",
             "created_at": _RECENT},
        ],
        "pyq_question_topic_tags": [
            {"id": "e1-t0", "question_id": "e1-q0", "reviewer_status": "verified",
             "created_at": _RECENT},
        ],
        # These tables must be present so the stub does not raise KeyError.
        "syllabus_topic_mentions": [],
        "exam_policy_updates": [],
        "exam_competition_metrics": [],
        "mock_question_bank": [],
        "organizations": [],
        "exam_families": [],
        "syllabus_documents": syllabus_documents if syllabus_documents is not None else [],
        # document_assets intentionally absent — querying it should never happen.
    }
    return db


# ── 1. Endpoint returns 200 with a verified syllabus_documents row ───────────

def test_endpoint_returns_200_with_syllabus_documents_row():
    """BUG-EI-2: was returning 500 because _documents() queried wrong table."""
    db = _minimal_ready_db(syllabus_documents=[
        {"id": "sd1", "exam_id": "e1", "trust_status": "verified",
         "document_type": "syllabus"},
    ])
    client = TestClient(_build_app(SBStub(db)))
    r = client.get("/api/admin/exam-intelligence/console/exams/e1")
    assert r.status_code == 200, r.text


# ── 2. Verified syllabus_documents row counts as an extracted document ────────

def test_verified_syllabus_document_counted_in_documents_check():
    """trust_status='verified' must register as a ready document (extracted >= 1)."""
    db = _minimal_ready_db(syllabus_documents=[
        {"id": "sd1", "exam_id": "e1", "trust_status": "verified",
         "document_type": "syllabus"},
    ])
    client = TestClient(_build_app(SBStub(db)))
    body = client.get("/api/admin/exam-intelligence/console/exams/e1").json()
    checks = {c["area"]: c for c in body["activation_checks"]}
    doc_check = checks["documents"]
    # State must be "done" because extracted >= 1.
    assert doc_check["state"] == "done", doc_check
    assert "1" in doc_check["detail"]


# ── 3. Pending syllabus_documents row does not count as verified ──────────────

def test_pending_syllabus_document_does_not_count_as_extracted():
    """trust_status='pending' must not be counted as a ready document."""
    db = _minimal_ready_db(syllabus_documents=[
        {"id": "sd2", "exam_id": "e1", "trust_status": "pending",
         "document_type": "syllabus"},
    ])
    client = TestClient(_build_app(SBStub(db)))
    body = client.get("/api/admin/exam-intelligence/console/exams/e1").json()
    checks = {c["area"]: c for c in body["activation_checks"]}
    doc_check = checks["documents"]
    # 1 uploaded but none verified — state must be needs_action.
    assert doc_check["state"] == "needs_action", doc_check
    assert "none verified" in doc_check["detail"]


# ── 4. Endpoint returns 200 with zero documents ───────────────────────────────

def test_endpoint_returns_200_with_no_documents():
    """No syllabus_documents rows: documents check is needs_action but no 500."""
    db = _minimal_ready_db(syllabus_documents=[])
    client = TestClient(_build_app(SBStub(db)))
    r = client.get("/api/admin/exam-intelligence/console/exams/e1")
    assert r.status_code == 200, r.text
    checks = {c["area"]: c for c in r.json()["activation_checks"]}
    assert checks["documents"]["state"] == "needs_action"
    assert checks["documents"]["detail"] == "No documents uploaded"


# ── 5. _documents() never queries document_assets ────────────────────────────

def test_documents_helper_does_not_query_document_assets():
    """Regression guard: the fix must not fall back to querying document_assets."""
    queried_tables: list[str] = []

    class TrackingSBStub(SBStub):
        def table(self, name):
            queried_tables.append(name)
            return super().table(name)

    db = _minimal_ready_db(syllabus_documents=[
        {"id": "sd1", "exam_id": "e1", "trust_status": "verified",
         "document_type": "syllabus"},
    ])
    client = TestClient(_build_app(TrackingSBStub(db)))
    r = client.get("/api/admin/exam-intelligence/console/exams/e1")
    assert r.status_code == 200
    assert "document_assets" not in queried_tables, (
        f"_documents() must not query document_assets; tables queried: {queried_tables}"
    )
    assert "syllabus_documents" in queried_tables, (
        f"_documents() must query syllabus_documents; tables queried: {queried_tables}"
    )


# ── 6. entity_kind for documents area is syllabus_documents ──────────────────

def test_documents_action_item_entity_kind_is_syllabus_documents():
    """_AREA_ENTITY_KIND['documents'] must be 'syllabus_documents' (not 'document_assets')."""
    db = _minimal_ready_db(syllabus_documents=[])
    client = TestClient(_build_app(SBStub(db)))
    body = client.get("/api/admin/exam-intelligence/console/exams/e1").json()
    # When documents is needs_action it appears in the action queue.
    doc_items = [i for i in body["action_queue"] if i["area"] == "documents"]
    assert doc_items, "documents area should be in action_queue when no docs present"
    assert doc_items[0]["entity_kind"] == "syllabus_documents", doc_items[0]
