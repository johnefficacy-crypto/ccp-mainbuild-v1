"""CMS create / bulk-import contract for syllabus_topic_mentions (migration 031).

The CMS feeds the review queue: every mention it creates lands at
``reviewer_status='pending'`` and is promoted only through the separate
``/admin/exam-intelligence`` review router. These tests pin that invariant
plus the bulk per-row error contract, and confirm the existing review
queue still reviews CMS-created rows.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intel_cms as cms_api
from app.api import admin_exam_intelligence as review_api
from app.core.auth import get_current_user
from tests.exam_intelligence.test_cms_taxonomy import TaxSBStub

_BASE = "/api/admin/exam-intelligence-cms"
_MENTIONS = f"{_BASE}/syllabus-topic-mentions"


def _cms_client(sb: TaxSBStub) -> TestClient:
    app = FastAPI()
    app.include_router(cms_api.router, prefix="/api")
    cms_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[cms_api._flag_enabled] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "admin-1", "role": "super_admin", "permissions": [cms_api.PERM_CMS],
    }
    return TestClient(app, raise_server_exceptions=False)


def _review_client(sb: TaxSBStub) -> TestClient:
    app = FastAPI()
    app.include_router(review_api.router, prefix="/api")
    review_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "admin-1", "role": "super_admin", "permissions": [],
    }
    return TestClient(app, raise_server_exceptions=False)


def _seed() -> dict:
    return {
        "exams": [{"id": "e1", "slug": "ssc-cgl", "name": "SSC CGL", "is_active": True}],
        "syllabus_documents": [
            {"id": "doc1", "exam_id": "e1", "title": "SSC CGL Syllabus", "document_type": "syllabus_pdf", "trust_status": "verified"}
        ],
        "subjects": [{"id": "s1", "slug": "quant", "name": "Quant", "is_active": True}],
        "topics": [
            {"id": "t1", "subject_id": "s1", "slug": "percentages", "name": "Percentages", "is_active": True},
            {"id": "t2", "subject_id": "s1", "slug": "ratios", "name": "Ratios", "is_active": True},
        ],
    }


def _payload(**over) -> dict:
    base = {"syllabus_document_id": "doc1", "exam_id": "e1", "topic_id": "t1",
            "raw_text": "Percentages and applications", "mention_type": "explicit"}
    base.update(over)
    return base


# ── 1. create forces pending ──────────────────────────────────────────────


def test_create_mention_lands_pending():
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).post(_MENTIONS, json={"reason": "seeding a mention", "payload": _payload()})
    assert r.status_code == 200, r.text
    row = sb.db["syllabus_topic_mentions"][0]
    assert row["reviewer_status"] == "pending"
    assert row["topic_id"] == "t1"
    assert row["mention_type"] == "explicit"


# ── 2. caller-supplied reviewer_status is overridden ──────────────────────


def test_create_mention_forces_pending_even_if_caller_sends_verified():
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).post(
        _MENTIONS,
        json={"reason": "trying to seed verified", "payload": _payload(reviewer_status="verified")},
    )
    assert r.status_code == 200, r.text
    # The most important assertion: a mention can never be born verified.
    assert sb.db["syllabus_topic_mentions"][0]["reviewer_status"] == "pending"


def test_create_mention_rejects_unknown_field_422():
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).post(
        _MENTIONS,
        json={"reason": "bogus field", "payload": _payload(reviewer_notes="should not be settable here")},
    )
    # reviewer_notes flows through the review queue, not CMS create.
    assert r.status_code == 422, r.text
    assert "reviewer_notes" in str(r.json().get("detail"))


# ── 3. bulk import: per-row error isolation ───────────────────────────────


def test_bulk_import_100_rows_one_bad_topic_isolated():
    sb = TaxSBStub(_seed())
    rows = []
    for i in range(100):
        topic = "bad-topic" if i == 50 else ("t1" if i % 2 == 0 else "t2")
        rows.append({"syllabus_document_id": "doc1", "exam_id": "e1", "topic_id": topic,
                     "raw_text": f"mention {i}", "mention_type": "explicit"})
    r = _cms_client(sb).post(
        f"{_BASE}/bulk-import",
        json={"reason": "bulk seeding 100 mentions", "entity": "syllabus-topic-mentions", "rows": rows},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok_count"] == 99
    assert body["error_count"] == 1
    assert len(sb.db["syllabus_topic_mentions"]) == 99
    bad = [res for res in body["results"] if not res["ok"]]
    assert len(bad) == 1 and bad[0]["index"] == 50
    assert "topic_id" in bad[0]["error"]
    # Every inserted row is forced pending.
    assert all(m["reviewer_status"] == "pending" for m in sb.db["syllabus_topic_mentions"])


# ── 4. existing review queue still reviews CMS-created mentions ───────────


def test_review_queue_reviews_cms_created_mention():
    sb = TaxSBStub(_seed())
    create = _cms_client(sb).post(_MENTIONS, json={"reason": "seeding for review", "payload": _payload()})
    assert create.status_code == 200, create.text
    mention_id = sb.db["syllabus_topic_mentions"][0]["id"]

    rev = _review_client(sb).patch(
        f"/api/admin/exam-intelligence/items/syllabus_topic_mention/{mention_id}/review",
        json={"reviewer_status": "verified", "reviewer_notes": "cross-checked PDF page 4"},
    )
    assert rev.status_code == 200, rev.text
    assert rev.json()["reviewer_status"] == "verified"
    assert sb.db["syllabus_topic_mentions"][0]["reviewer_status"] == "verified"
