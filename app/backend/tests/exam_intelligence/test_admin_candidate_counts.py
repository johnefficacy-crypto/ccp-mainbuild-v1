"""Admin candidate-count (applied-vs-appeared, J3 PR2) API tests.

Mirrors test_admin_api.py's exam_competition_metrics review-endpoint test
pattern (migration 218's lifecycle RPC is analogous to 216's).
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intelligence as admin_api
from app.core.auth import get_current_user
from tests.persona_questions._stub import SBStub


def _build_app(sb: SBStub, role: str = "super_admin"):
    app = FastAPI()
    app.include_router(admin_api.router, prefix="/api")
    admin_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    user_dict = {
        "id": "admin-1",
        "role": role,
        "permissions": ["exam_intelligence.review"] if role == "admin" else [],
    }
    app.dependency_overrides[get_current_user] = lambda: user_dict
    return app


def _seed():
    return {
        "exams": [{"id": "e1", "slug": "upsc-cse", "name": "UPSC CSE", "is_active": True}],
        "exam_cycles": [{"id": "cy1", "exam_id": "e1", "year": 2024}],
        "exam_phases": [{"id": "ph1", "exam_id": "e1", "phase_order": 1}],
        "reservation_categories": [{"id": "cat-general", "code": "general"}],
        "source_registry": [
            {"id": "src1", "is_active": True, "is_verified": True, "discovery_only": False, "source_type": "official_pdf"},
        ],
        "exam_candidate_counts": [
            {
                "id": "cc1", "exam_id": "e1", "exam_cycle_id": "cy1", "exam_phase_id": "ph1",
                "scope_kind": "phase", "count_type": "appeared", "reservation_category_id": None,
                "count_value": 500000, "reviewer_status": "pending_review",
                "source_basis": "official", "is_current_published": False, "version_no": 1,
                "created_at": "2026-05-01T00:00:00+00:00",
            },
            {
                "id": "cc2", "exam_id": "e1", "exam_cycle_id": "cy1", "exam_phase_id": None,
                "scope_kind": "cycle", "count_type": "applied", "reservation_category_id": None,
                "count_value": 1200000, "reviewer_status": "locked",
                "source_basis": "official", "is_current_published": True, "version_no": 1,
                "created_at": "2026-04-01T00:00:00+00:00",
            },
        ],
    }


def test_candidate_counts_list_maps_rows_and_exam_name():
    sb = SBStub(_seed())
    client = TestClient(_build_app(sb))
    r = client.get("/api/admin/exam-intelligence/candidate-counts?exam_id=e1")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 2
    by_id = {row["id"]: row for row in body["items"]}
    assert by_id["cc1"]["exam"] == "UPSC CSE"
    assert by_id["cc2"]["status"] == "locked"


def test_candidate_count_review_rejects_missing_evidence():
    sb = SBStub(_seed())
    client = TestClient(_build_app(sb))
    r = client.patch(
        "/api/admin/exam-intelligence/candidate-counts/cc1/review",
        json={"reviewer_status": "reviewed"},
    )
    assert r.status_code == 422
    assert "missing_or_stale_evidence" in r.json()["detail"]


def test_candidate_count_review_promotes_with_matching_evidence():
    sb = SBStub(_seed())
    sb.db["exam_candidate_count_evidence"] = [
        {
            "id": "ev1", "count_id": "cc1", "evidence_kind": "official_result",
            "evidence_role": "primary", "source_id": "src1",
            "evidence_url": "https://upsc.gov.in/result.pdf",
            "claim_value": {
                "count_type": "appeared", "scope_kind": "phase",
                "exam_phase_id": "ph1", "reservation_category_code": None,
                "count_value": 500000,
            },
        },
    ]
    client = TestClient(_build_app(sb))
    r = client.patch(
        "/api/admin/exam-intelligence/candidate-counts/cc1/review",
        json={"reviewer_status": "reviewed"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["new_status"] == "reviewed"
    row = next(c for c in sb.db["exam_candidate_counts"] if c["id"] == "cc1")
    assert row["reviewer_status"] == "reviewed"
    assert row["is_current_published"] is True


def test_candidate_count_review_rejects_null_source_id_evidence():
    """checkpost P1-5: source_id IS NULL is NOT trusted. Even a claim-value-
    matching primary evidence row with no source_registry link (only a raw
    evidence_url) fails the §7 source-trust predicate."""
    sb = SBStub(_seed())
    sb.db["exam_candidate_count_evidence"] = [
        {
            "id": "ev1", "count_id": "cc1", "evidence_kind": "official_result",
            "evidence_role": "primary", "source_id": None,
            "evidence_url": "https://upsc.gov.in/result.pdf",
            "claim_value": {
                "count_type": "appeared", "scope_kind": "phase",
                "exam_phase_id": "ph1", "reservation_category_code": None,
                "count_value": 500000,
            },
        },
    ]
    client = TestClient(_build_app(sb))
    r = client.patch(
        "/api/admin/exam-intelligence/candidate-counts/cc1/review",
        json={"reviewer_status": "reviewed"},
    )
    assert r.status_code == 422
    assert "missing_or_stale_evidence" in r.json()["detail"]


def test_candidate_count_review_rejects_evidence_without_url_or_doc():
    """checkpost P1-5: §7 requires an evidence_url OR document_asset_id in
    addition to a trusted source_registry row."""
    sb = SBStub(_seed())
    sb.db["exam_candidate_count_evidence"] = [
        {
            "id": "ev1", "count_id": "cc1", "evidence_kind": "official_result",
            "evidence_role": "primary", "source_id": "src1",
            "evidence_url": None, "document_asset_id": None,
            "claim_value": {
                "count_type": "appeared", "scope_kind": "phase",
                "exam_phase_id": "ph1", "reservation_category_code": None,
                "count_value": 500000,
            },
        },
    ]
    client = TestClient(_build_app(sb))
    r = client.patch(
        "/api/admin/exam-intelligence/candidate-counts/cc1/review",
        json={"reviewer_status": "reviewed"},
    )
    assert r.status_code == 422
    assert "missing_or_stale_evidence" in r.json()["detail"]


def test_candidate_count_review_rejects_malformed_claim_value_shape():
    """checkpost P1-5: a non-numeric claim_value.count_value must fail the
    shape guard and never qualify (no uncontrolled cast/compare error)."""
    sb = SBStub(_seed())
    sb.db["exam_candidate_count_evidence"] = [
        {
            "id": "ev1", "count_id": "cc1", "evidence_kind": "official_result",
            "evidence_role": "primary", "source_id": "src1",
            "evidence_url": "https://upsc.gov.in/result.pdf",
            "claim_value": {
                "count_type": "appeared", "scope_kind": "phase",
                "exam_phase_id": "ph1", "reservation_category_code": None,
                "count_value": "five lakh",  # malformed — not a number
            },
        },
    ]
    client = TestClient(_build_app(sb))
    r = client.patch(
        "/api/admin/exam-intelligence/candidate-counts/cc1/review",
        json={"reviewer_status": "reviewed"},
    )
    assert r.status_code == 422
    assert "missing_or_stale_evidence" in r.json()["detail"]


def test_candidate_count_review_rejects_stale_evidence():
    # Evidence claim_value.count_value does not match the current parent
    # count_value — must not qualify (mirrors 216's stale-evidence test).
    sb = SBStub(_seed())
    sb.db["exam_candidate_count_evidence"] = [
        {
            "id": "ev1", "count_id": "cc1", "evidence_kind": "official_result",
            "evidence_role": "primary", "source_id": "src1",
            "claim_value": {
                "count_type": "appeared", "scope_kind": "phase",
                "exam_phase_id": "ph1", "reservation_category_code": None,
                "count_value": 499999,  # stale — parent is 500000
            },
        },
    ]
    client = TestClient(_build_app(sb))
    r = client.patch(
        "/api/admin/exam-intelligence/candidate-counts/cc1/review",
        json={"reviewer_status": "reviewed"},
    )
    assert r.status_code == 422
    assert "missing_or_stale_evidence" in r.json()["detail"]


def test_candidate_count_review_rejects_reviewed_analysis_as_sole_evidence():
    sb = SBStub(_seed())
    sb.db["exam_candidate_count_evidence"] = [
        {
            "id": "ev1", "count_id": "cc1", "evidence_kind": "reviewed_analysis",
            "evidence_role": "primary", "source_id": "src1",
            "claim_value": {
                "count_type": "appeared", "scope_kind": "phase",
                "exam_phase_id": "ph1", "reservation_category_code": None,
                "count_value": 500000,
            },
        },
    ]
    client = TestClient(_build_app(sb))
    r = client.patch(
        "/api/admin/exam-intelligence/candidate-counts/cc1/review",
        json={"reviewer_status": "reviewed"},
    )
    assert r.status_code == 422


def test_candidate_count_review_rejects_draft_to_reviewed_jump():
    sb = SBStub(_seed())
    sb.db["exam_candidate_counts"][0]["reviewer_status"] = "draft"
    client = TestClient(_build_app(sb))
    r = client.patch(
        "/api/admin/exam-intelligence/candidate-counts/cc1/review",
        json={"reviewer_status": "reviewed"},
    )
    assert r.status_code == 422
    assert "transition_not_allowed" in r.json()["detail"]


def test_candidate_count_review_missing_returns_404():
    sb = SBStub(_seed())
    client = TestClient(_build_app(sb))
    r = client.patch(
        "/api/admin/exam-intelligence/candidate-counts/no-such/review",
        json={"reviewer_status": "reviewed"},
    )
    assert r.status_code == 404


def test_candidate_count_reopen_for_edit_clones_published_row():
    sb = SBStub(_seed())
    client = TestClient(_build_app(sb))
    r = client.post(
        "/api/admin/exam-intelligence/candidate-counts/cc2/reopen-for-edit",
        json={"reviewer_notes": "Correcting a transcription error."},
    )
    assert r.status_code == 200, r.text
    draft = r.json()["draft"]
    assert draft["reviewer_status"] == "draft"
    assert draft["id"] != "cc2"
    published = next(c for c in sb.db["exam_candidate_counts"] if c["id"] == "cc2")
    assert published["reviewer_status"] == "locked"  # never mutated in place (OD-7)


def test_candidate_count_evidence_attach_and_list():
    sb = SBStub(_seed())
    client = TestClient(_build_app(sb))
    r = client.post(
        "/api/admin/exam-intelligence/candidate-counts/cc1/evidence",
        json={
            "evidence_kind": "official_result",
            "source_id": "src1",
            "claim_value": {
                "count_type": "appeared", "scope_kind": "phase",
                "exam_phase_id": "ph1", "reservation_category_code": None,
                "count_value": 500000,
            },
        },
    )
    assert r.status_code == 200, r.text
    listed = client.get("/api/admin/exam-intelligence/candidate-counts/cc1/evidence")
    assert listed.status_code == 200
    assert listed.json()["count"] == 1


def test_candidate_count_evidence_rejects_published_parent():
    sb = SBStub(_seed())
    client = TestClient(_build_app(sb))
    r = client.post(
        "/api/admin/exam-intelligence/candidate-counts/cc2/evidence",
        json={
            "evidence_kind": "official_result",
            "source_id": "src1",
            "claim_value": {"count_value": 1200000},
        },
    )
    assert r.status_code == 409


def test_candidate_counts_blocked_for_non_admin():
    sb = SBStub(_seed())
    client = TestClient(_build_app(sb, role="user"))
    assert client.get("/api/admin/exam-intelligence/candidate-counts").status_code == 403
