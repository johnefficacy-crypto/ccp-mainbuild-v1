"""Schema-truth contract for the exam_topic_coverage CMS write path.

``exam_topic_coverage`` (migration 030) has no ``priority`` or
``is_active`` column — the planner activates on ``exam_priority_score`` /
``is_high_yield`` and the verified-evidence chain. The CMS whitelist had
drifted to the stale ``priority`` / ``is_active`` names, which silently
dropped real fields and broke the list endpoint's ``ORDER BY``.

These tests pin the corrected contract end to end:
* real schema fields persist on create, status stays forced to
  ``pending_review``;
* the stale ``priority`` / ``is_active`` keys are rejected with 422;
* a coverage row created through the CMS and then locked still satisfies
  the planner readiness validator;
* the read-only review queue still loads coverage rows.
"""
from __future__ import annotations

import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intel_cms as cms_api
from app.api import admin_exam_intelligence as review_api
from app.core.auth import get_current_user
from scripts import validate_exam_intelligence_seed as validator
from tests.persona_questions._stub import SBStub

_BASE = "/api/admin/exam-intelligence-cms"


def _cms_client(sb: SBStub) -> TestClient:
    app = FastAPI()
    app.include_router(cms_api.router, prefix="/api")
    cms_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[cms_api._flag_enabled] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "admin-1",
        "role": "super_admin",
        "permissions": [cms_api.PERM_CMS],
    }
    return TestClient(app, raise_server_exceptions=False)


def _review_client(sb: SBStub) -> TestClient:
    app = FastAPI()
    app.include_router(review_api.router, prefix="/api")
    review_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "admin-1",
        "role": "super_admin",
        "permissions": [],
    }
    return TestClient(app, raise_server_exceptions=False)


def _seed() -> dict:
    return {
        "exams": [{"id": "exam-1", "slug": "ssc-cgl", "name": "SSC CGL", "is_active": True}],
        "topics": [{"id": "t1", "name": "Percentages", "slug": "percentages", "subject_id": "sub1", "is_active": True}],
        "subjects": [{"id": "sub1", "name": "Quant", "is_active": True}],
    }


# ── 1. real fields persist, status forced ───────────────────────────────


def test_create_coverage_with_real_fields_persists_and_forces_pending_review():
    sb = SBStub(_seed())
    client = _cms_client(sb)
    r = client.post(
        f"{_BASE}/exam-topic-coverage",
        json={
            "reason": "seeding a real coverage row",
            "payload": {
                "exam_id": "exam-1",
                "topic_id": "t1",
                "coverage_depth": "core",
                "expected_difficulty": "medium",
                "exam_priority_score": 84.5,
                "is_high_yield": True,
                "confidence_score": 0.78,
                "source_basis": "admin_review",
                "review_notes": "verified against the official syllabus PDF",
                "metadata": {"evidence_count": 3},
            },
        },
    )
    assert r.status_code == 200, r.text
    row = sb.db["exam_topic_coverage"][0]
    # Every real field round-trips.
    assert row["coverage_depth"] == "core"
    assert row["exam_priority_score"] == 84.5
    assert row["confidence_score"] == 0.78
    assert row["source_basis"] == "admin_review"
    assert row["review_notes"] == "verified against the official syllabus PDF"
    assert row["metadata"] == {"evidence_count": 3}
    # Forced default is preserved even though the schema column is writable.
    assert row["reviewer_status"] == "pending_review"
    # Stale names never appear on the persisted row.
    assert "priority" not in row
    assert "is_active" not in row


# ── 2. stale fields rejected with 422 ────────────────────────────────────


def test_create_coverage_rejects_legacy_priority_with_422():
    sb = SBStub(_seed())
    client = _cms_client(sb)
    r = client.post(
        f"{_BASE}/exam-topic-coverage",
        json={
            "reason": "attempting the stale priority field",
            "payload": {"exam_id": "exam-1", "topic_id": "t1", "priority": 5},
        },
    )
    assert r.status_code == 422, r.text
    assert "priority" in str(r.json().get("detail"))
    # Nothing was written.
    assert not sb.db.get("exam_topic_coverage")


def test_create_coverage_rejects_legacy_is_active_with_422():
    sb = SBStub(_seed())
    client = _cms_client(sb)
    r = client.post(
        f"{_BASE}/exam-topic-coverage",
        json={
            "reason": "attempting the stale is_active field",
            "payload": {"exam_id": "exam-1", "topic_id": "t1", "is_active": True},
        },
    )
    assert r.status_code == 422, r.text
    assert "is_active" in str(r.json().get("detail"))
    assert not sb.db.get("exam_topic_coverage")


# ── 3. planner readiness validator passes after create + lock ────────────


def test_readiness_validator_passes_after_coverage_created_and_locked(monkeypatch):
    sb = SBStub(
        {
            **_seed(),
            "exam_cycles": [{"id": "cyc-1", "exam_id": "exam-1", "status": "open"}],
            "exam_phases": [{"id": "ph-1", "exam_id": "exam-1", "phase_name": "Tier 1", "status": "active"}],
        }
    )
    client = _cms_client(sb)
    r = client.post(
        f"{_BASE}/exam-topic-coverage",
        json={
            "reason": "coverage row that will be locked into the planner",
            "payload": {
                "exam_id": "exam-1",
                "topic_id": "t1",
                "coverage_depth": "core",
                "exam_priority_score": 84.5,
                "is_high_yield": True,
                "confidence_score": 0.78,
                "source_basis": "admin_review",
                "review_notes": "admin-verified evidence chain",
            },
        },
    )
    assert r.status_code == 200, r.text
    assert sb.db["exam_topic_coverage"][0]["reviewer_status"] == "pending_review"

    # Promote through review (the lifecycle move the review router owns).
    sb.db["exam_topic_coverage"][0]["reviewer_status"] = "locked"

    # The readiness validator reads the same Supabase data.
    monkeypatch.setattr(validator, "get_supabase_admin", lambda: sb)
    monkeypatch.setattr(sys, "argv", ["validate", "--exam-slug", "ssc-cgl", "--strict"])
    assert validator.main() == 0


# ── 4. review queue still loads coverage rows ────────────────────────────


def test_review_queue_still_loads_coverage_rows():
    sb = SBStub(
        {
            **_seed(),
            "exam_topic_coverage": [
                {
                    "id": "c1", "exam_id": "exam-1", "topic_id": "t1",
                    "exam_phase_id": "ph-1", "coverage_depth": "core",
                    "expected_difficulty": "medium", "exam_priority_score": 84,
                    "is_high_yield": True, "confidence_score": 0.78,
                    "source_basis": "official_syllabus", "reviewer_status": "locked",
                    "metadata": {}, "created_at": "2026-05-01T00:00:00+00:00",
                }
            ],
        }
    )
    client = _review_client(sb)
    r = client.get("/api/admin/exam-intelligence/topic-coverage?exam_id=exam-1")
    assert r.status_code == 200, r.text
    body = r.json()
    ids = [row.get("id") for row in body.get("items", [])]
    assert "c1" in ids, body
