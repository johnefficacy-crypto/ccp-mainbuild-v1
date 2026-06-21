"""Regression tests for BUG-EI-2 final fix.

Previous broken state: ``_documents()`` in both console_detail.py and
readiness.py queried ``document_assets`` with non-existent columns
(exam_id, extraction_status, exam_cycle_id) causing PostgREST 42703 → HTTP 500.

Interim Option A (now superseded): query ``syllabus_documents`` and use
``trust_status == "verified"`` as an extraction proxy.  This undercounted
because trust_status is a human-review gate, orthogonal to extraction.

Final fix (this file covers): document readiness is sourced from
``document_processing_jobs`` (job_type='text_extract', latest job per asset).
Exam ownership is stored in ``document_assets.metadata.exam_id``.

Assertions:
1. Endpoint returns 200 when document_assets + succeeded text_extract job present.
2. A succeeded text_extract job counts as extracted (state="done").
3. A syllabus_documents row with trust_status='verified' ALONE (no text_extract
   job) does NOT register as an extracted document.
4. An asset with no job at all (not_started) is NOT counted as extracted.
5. Endpoint returns 200 with zero admin-EI documents.
6. document_assets IS queried as the asset roster; syllabus_documents is not the
   extraction source.
7. _AREA_ENTITY_KIND["documents"] == "document_assets".
"""
from __future__ import annotations

from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intelligence as admin_api
from app.core.auth import get_current_user
from app.exam_intelligence.readiness import load_doc_extraction_counts
from tests.persona_questions._stub import SBStub


_RECENT = "2026-06-21T00:00:00+00:00"


def _build_app(sb):
    app = FastAPI()
    app.include_router(admin_api.router, prefix="/api")
    admin_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    user = {"id": "admin-1", "role": "super_admin", "permissions": []}
    app.dependency_overrides[get_current_user] = lambda: user
    return app


def _minimal_ready_db(*, doc_assets=None, doc_jobs=None):
    """Minimal DB with one fully-ready exam (phases + locked coverage + verified PYQ).

    doc_assets: list of document_assets rows (scope='admin_exam_intelligence',
                metadata contains exam_id).
    doc_jobs:   list of document_processing_jobs rows.
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
        "syllabus_topic_mentions": [],
        "exam_policy_updates": [],
        "exam_competition_metrics": [],
        "mock_question_bank": [],
        "organizations": [],
        "exam_families": [],
        # syllabus_documents present but NOT used as extraction source.
        "syllabus_documents": [
            {"id": "sd1", "exam_id": "e1", "trust_status": "verified",
             "document_type": "syllabus"},
        ],
        # Real extraction sources:
        "document_assets": doc_assets if doc_assets is not None else [],
        "document_processing_jobs": doc_jobs if doc_jobs is not None else [],
    }
    return db


def _admin_ei_asset(asset_id: str) -> dict:
    return {
        "id": asset_id,
        "scope": "admin_exam_intelligence",
        "metadata": {"exam_id": "e1"},
    }


def _text_extract_job(asset_id: str, status: str) -> dict:
    return {
        "document_id": asset_id,
        "job_type": "text_extract",
        "status": status,
        "created_at": _RECENT,
    }


# ── 1. 200 with document_assets + succeeded text_extract job ─────────────────

def test_endpoint_returns_200_with_succeeded_text_extract_job():
    """Endpoint must not 500 when a document_assets row has a succeeded text_extract job."""
    db = _minimal_ready_db(
        doc_assets=[_admin_ei_asset("da1")],
        doc_jobs=[_text_extract_job("da1", "succeeded")],
    )
    client = TestClient(_build_app(SBStub(db)))
    r = client.get("/api/admin/exam-intelligence/console/exams/e1")
    assert r.status_code == 200, r.text


# ── 2. Succeeded text_extract job → state="done" ─────────────────────────────

def test_succeeded_job_counts_as_extracted():
    """A succeeded text_extract job must register as extracted (state='done')."""
    db = _minimal_ready_db(
        doc_assets=[_admin_ei_asset("da1")],
        doc_jobs=[_text_extract_job("da1", "succeeded")],
    )
    client = TestClient(_build_app(SBStub(db)))
    body = client.get("/api/admin/exam-intelligence/console/exams/e1").json()
    checks = {c["area"]: c for c in body["activation_checks"]}
    doc_check = checks["documents"]
    assert doc_check["state"] == "done", doc_check
    assert "1" in doc_check["detail"]


# ── 3. syllabus_documents trust_status='verified' alone → NOT extracted ───────

def test_verified_syllabus_document_alone_not_counted_as_extracted():
    """trust_status='verified' on syllabus_documents is a human-review gate.
    Without a succeeded text_extract job, the document is not extracted.
    The DB has a verified syllabus_documents row (set up in _minimal_ready_db),
    but no document_assets / text_extract jobs → state must be needs_action.
    """
    db = _minimal_ready_db(doc_assets=[], doc_jobs=[])
    client = TestClient(_build_app(SBStub(db)))
    body = client.get("/api/admin/exam-intelligence/console/exams/e1").json()
    checks = {c["area"]: c for c in body["activation_checks"]}
    doc_check = checks["documents"]
    assert doc_check["state"] == "needs_action", doc_check
    assert "No documents" in doc_check["detail"]


# ── 4. Asset with no job → not_started → NOT extracted ───────────────────────

def test_asset_with_no_job_not_counted_as_extracted():
    """An admin_exam_intelligence asset with no text_extract job at all must not
    count as extracted — it is not_started, so state is needs_action."""
    db = _minimal_ready_db(
        doc_assets=[_admin_ei_asset("da1")],
        doc_jobs=[],  # no processing job
    )
    client = TestClient(_build_app(SBStub(db)))
    body = client.get("/api/admin/exam-intelligence/console/exams/e1").json()
    checks = {c["area"]: c for c in body["activation_checks"]}
    doc_check = checks["documents"]
    assert doc_check["state"] == "needs_action", doc_check
    assert "none extracted" in doc_check["detail"]


# ── 5. 200 with zero admin-EI documents ──────────────────────────────────────

def test_endpoint_returns_200_with_no_admin_ei_documents():
    """No document_assets rows: documents check is needs_action but endpoint returns 200."""
    db = _minimal_ready_db(doc_assets=[], doc_jobs=[])
    client = TestClient(_build_app(SBStub(db)))
    r = client.get("/api/admin/exam-intelligence/console/exams/e1")
    assert r.status_code == 200, r.text
    checks = {c["area"]: c for c in r.json()["activation_checks"]}
    assert checks["documents"]["state"] == "needs_action"
    assert "No documents" in checks["documents"]["detail"]


# ── 6. document_assets queried; syllabus_documents not extraction source ──────

def test_documents_helper_queries_document_assets():
    """Regression guard: extraction must come from document_assets +
    document_processing_jobs, never from syllabus_documents.trust_status.
    """
    queried_tables: list[str] = []

    class TrackingSBStub(SBStub):
        def table(self, name):
            queried_tables.append(name)
            return super().table(name)

    db = _minimal_ready_db(
        doc_assets=[_admin_ei_asset("da1")],
        doc_jobs=[_text_extract_job("da1", "succeeded")],
    )
    client = TestClient(_build_app(TrackingSBStub(db)))
    r = client.get("/api/admin/exam-intelligence/console/exams/e1")
    assert r.status_code == 200
    assert "document_assets" in queried_tables, (
        f"document_assets must be queried for extraction roster; tables queried: {queried_tables}"
    )
    assert "document_processing_jobs" in queried_tables, (
        f"document_processing_jobs must be queried for extraction status; tables queried: {queried_tables}"
    )


# ── 7. _AREA_ENTITY_KIND["documents"] == "document_assets" ───────────────────

def test_documents_action_item_entity_kind_is_document_assets():
    """_AREA_ENTITY_KIND['documents'] must be 'document_assets' (not 'syllabus_documents')."""
    from app.exam_intelligence.console_detail import _AREA_ENTITY_KIND
    assert _AREA_ENTITY_KIND["documents"] == "document_assets", _AREA_ENTITY_KIND
    db = _minimal_ready_db(doc_assets=[], doc_jobs=[])
    client = TestClient(_build_app(SBStub(db)))
    body = client.get("/api/admin/exam-intelligence/console/exams/e1").json()
    doc_items = [i for i in body["action_queue"] if i["area"] == "documents"]
    assert doc_items, "documents area should be in action_queue when no docs present"
    assert doc_items[0]["entity_kind"] == "document_assets", doc_items[0]


# ── 8. Strict path: asset read failure → 5xx ────────────────────────────────

def test_strict_asset_read_failure_returns_500():
    """console endpoint must return 5xx when document_assets read fails (strict=True)."""
    class BrokenAssetSB(SBStub):
        def table(self, name):
            if name == "document_assets":
                m = MagicMock()
                m.select.return_value = m
                m.eq.return_value = m
                m.order.return_value = m
                m.range.return_value = m
                m.execute.side_effect = RuntimeError("DB asset read failure")
                return m
            return super().table(name)

    db = _minimal_ready_db(doc_assets=[], doc_jobs=[])
    client = TestClient(_build_app(BrokenAssetSB(db)), raise_server_exceptions=False)
    r = client.get("/api/admin/exam-intelligence/console/exams/e1")
    assert r.status_code == 500, r.text


# ── 9. Strict path: job read failure → 5xx ──────────────────────────────────

def test_strict_job_read_failure_returns_500():
    """console endpoint must return 5xx when document_processing_jobs read fails (strict=True)."""
    class BrokenJobSB(SBStub):
        def table(self, name):
            if name == "document_processing_jobs":
                m = MagicMock()
                m.select.return_value = m
                m.eq.return_value = m
                m.in_.return_value = m
                m.order.return_value = m
                m.range.return_value = m
                m.execute.side_effect = RuntimeError("DB job read failure")
                return m
            return super().table(name)

    db = _minimal_ready_db(
        doc_assets=[_admin_ei_asset("da1")],
        doc_jobs=[],
    )
    client = TestClient(_build_app(BrokenJobSB(db)), raise_server_exceptions=False)
    r = client.get("/api/admin/exam-intelligence/console/exams/e1")
    assert r.status_code == 500, r.text


# ── 10. needs_review status in vocabulary ────────────────────────────────────

def test_needs_review_job_counted_in_vocabulary():
    """An asset whose latest text_extract job has status='needs_review' is counted
    under needs_review (not extracted, pending, failed, or not_started)."""
    from app.exam_intelligence.readiness import load_doc_extraction_counts

    db = _minimal_ready_db(
        doc_assets=[_admin_ei_asset("da1"), _admin_ei_asset("da2")],
        doc_jobs=[
            _text_extract_job("da1", "needs_review"),
            _text_extract_job("da2", "succeeded"),
        ],
    )
    counts = load_doc_extraction_counts(SBStub(db), "e1", strict=True)
    assert counts["needs_review"] == 1, counts
    assert counts["extracted"] == 1, counts
    assert counts["not_started"] == 0, counts
    assert "needs_review" in counts


# ── 11. Deterministic latest job: (created_at, id) tiebreaker ───────────────

def test_latest_job_id_tiebreaker_when_same_created_at():
    """When two jobs share the same created_at, the one with the higher id wins
    (lexicographic sort ascending on (created_at, id) — last entry wins)."""
    from app.exam_intelligence.readiness import load_doc_extraction_counts

    # job-A (id='a') → failed; job-B (id='b') → succeeded — same created_at.
    # After sort by (created_at, id), 'b' > 'a', so job-B wins → extracted.
    db = _minimal_ready_db(
        doc_assets=[_admin_ei_asset("da1")],
        doc_jobs=[
            {"document_id": "da1", "job_type": "text_extract",
             "status": "failed", "created_at": _RECENT, "id": "job-a"},
            {"document_id": "da1", "job_type": "text_extract",
             "status": "succeeded", "created_at": _RECENT, "id": "job-b"},
        ],
    )
    counts = load_doc_extraction_counts(SBStub(db), "e1", strict=True)
    assert counts["extracted"] == 1, f"job-b (id='job-b') should win tiebreak: {counts}"
    assert counts["failed"] == 0, counts
