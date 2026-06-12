"""Tests for the new source_id and staleness_status filters on
GET /api/admin/verification-reports.

Confirms:
  1. staleness_status filter returns only matching rows.
  2. Unknown staleness_status returns 422.
  3. source_id filter resolves through scrape_queue.source_id and returns
     only reports whose queue row belongs to that source.
  4. source_id with no matching queue rows returns empty items list.
  5. source_id + staleness_status combined (AND) filters correctly.
  6. Reports include staleness_status in the list response items.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_verification_reports as vr_api
from app.core.auth import get_current_user
from tests.persona_questions._stub import SBStub


_ADMIN = {
    "id": "admin-uuid-1",
    "email": "admin@test.local",
    "role": "admin",
    "permissions": ["recruitments.manage"],
}

SOURCE_A = "src-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
SOURCE_B = "src-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
QUEUE_A1 = "q-aaaa-1111-1111-111111111111"
QUEUE_A2 = "q-aaaa-2222-2222-222222222222"
QUEUE_B1 = "q-bbbb-1111-1111-111111111111"
RPT_1 = "rpt-1111-1111-1111-111111111111"
RPT_2 = "rpt-2222-2222-2222-222222222222"
RPT_3 = "rpt-3333-3333-3333-333333333333"


def _world():
    return {
        "scrape_queue": [
            {"id": QUEUE_A1, "source_id": SOURCE_A},
            {"id": QUEUE_A2, "source_id": SOURCE_A},
            {"id": QUEUE_B1, "source_id": SOURCE_B},
        ],
        "recruitment_verification_reports": [
            {
                "id": RPT_1,
                "scrape_queue_id": QUEUE_A1,
                "recruitment_id": None,
                "lifecycle_status": "classified",
                "staleness_status": "pending_reverification_batch",
                "criticality_tier": "C_STANDARD_LONG_TAIL",
                "exam_family_key": None,
                "recommended_action": "request_admin_review",
                "trigger_reason": "initial_scrape",
                "report_version": 1,
                "chain_root_id": None,
                "superseded_by": None,
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
            },
            {
                "id": RPT_2,
                "scrape_queue_id": QUEUE_A2,
                "recruitment_id": None,
                "lifecycle_status": "classified",
                "staleness_status": "needs_reverification",
                "criticality_tier": "B_TECHNICAL_CONDITIONAL",
                "exam_family_key": "upsc",
                "recommended_action": "request_admin_review",
                "trigger_reason": "source_hash_changed",
                "report_version": 1,
                "chain_root_id": None,
                "superseded_by": None,
                "created_at": "2026-01-02T00:00:00+00:00",
                "updated_at": "2026-01-02T00:00:00+00:00",
            },
            {
                "id": RPT_3,
                "scrape_queue_id": QUEUE_B1,
                "recruitment_id": None,
                "lifecycle_status": "classified",
                "staleness_status": "pending_reverification_batch",
                "criticality_tier": "A_HIGH_STAKES",
                "exam_family_key": "ssc",
                "recommended_action": "await_official_proof",
                "trigger_reason": "initial_scrape",
                "report_version": 1,
                "chain_root_id": None,
                "superseded_by": None,
                "created_at": "2026-01-03T00:00:00+00:00",
                "updated_at": "2026-01-03T00:00:00+00:00",
            },
        ],
    }


def _build_app(sb: SBStub) -> TestClient:
    app = FastAPI()
    app.include_router(vr_api.router, prefix="/api")
    vr_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[get_current_user] = lambda: _ADMIN
    return TestClient(app)


# ── staleness_status filter ────────────────────────────────────────────


def test_staleness_status_filter_returns_matching_rows():
    sb = SBStub(_world())
    r = _build_app(sb).get(
        "/api/admin/verification-reports?staleness_status=pending_reverification_batch"
    )
    assert r.status_code == 200
    ids = {item["id"] for item in r.json()["items"]}
    assert ids == {RPT_1, RPT_3}


def test_staleness_status_filter_needs_reverification():
    sb = SBStub(_world())
    r = _build_app(sb).get(
        "/api/admin/verification-reports?staleness_status=needs_reverification"
    )
    assert r.status_code == 200
    ids = {item["id"] for item in r.json()["items"]}
    assert ids == {RPT_2}


def test_unknown_staleness_status_returns_422():
    sb = SBStub(_world())
    r = _build_app(sb).get(
        "/api/admin/verification-reports?staleness_status=made_up_value"
    )
    assert r.status_code == 422
    assert "staleness_status" in r.json()["detail"]


# ── source_id filter ───────────────────────────────────────────────────


def test_source_id_filter_returns_only_reports_for_that_source():
    sb = SBStub(_world())
    r = _build_app(sb).get(
        f"/api/admin/verification-reports?source_id={SOURCE_A}"
    )
    assert r.status_code == 200
    ids = {item["id"] for item in r.json()["items"]}
    assert ids == {RPT_1, RPT_2}


def test_source_id_filter_excludes_other_sources():
    sb = SBStub(_world())
    r = _build_app(sb).get(
        f"/api/admin/verification-reports?source_id={SOURCE_B}"
    )
    assert r.status_code == 200
    ids = {item["id"] for item in r.json()["items"]}
    assert ids == {RPT_3}


def test_source_id_with_no_matching_queue_rows_returns_empty():
    sb = SBStub(_world())
    unknown_source = "src-9999-9999-9999-999999999999"
    r = _build_app(sb).get(
        f"/api/admin/verification-reports?source_id={unknown_source}"
    )
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == []


# ── combined filter ────────────────────────────────────────────────────


def test_source_id_and_staleness_combined_and_filters():
    """Only RPT_1 belongs to SOURCE_A AND has staleness_status=pending_reverification_batch."""
    sb = SBStub(_world())
    r = _build_app(sb).get(
        f"/api/admin/verification-reports"
        f"?source_id={SOURCE_A}"
        f"&staleness_status=pending_reverification_batch"
    )
    assert r.status_code == 200
    ids = {item["id"] for item in r.json()["items"]}
    assert ids == {RPT_1}


def test_source_id_and_staleness_combined_no_match():
    """SOURCE_B has only pending_reverification_batch; needs_reverification → empty."""
    sb = SBStub(_world())
    r = _build_app(sb).get(
        f"/api/admin/verification-reports"
        f"?source_id={SOURCE_B}"
        f"&staleness_status=needs_reverification"
    )
    assert r.status_code == 200
    assert r.json()["items"] == []


# ── response shape ─────────────────────────────────────────────────────


def test_list_items_include_staleness_status_field():
    sb = SBStub(_world())
    r = _build_app(sb).get("/api/admin/verification-reports")
    assert r.status_code == 200
    for item in r.json()["items"]:
        assert "staleness_status" in item


def test_list_response_echoes_limit_and_offset():
    sb = SBStub(_world())
    r = _build_app(sb).get("/api/admin/verification-reports?limit=10&offset=5")
    assert r.status_code == 200
    body = r.json()
    assert body["limit"] == 10
    assert body["offset"] == 5
