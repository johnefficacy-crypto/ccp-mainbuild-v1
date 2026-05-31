"""Tests for PR4 backend additions to list_pyq_papers and get_pyq_paper.

Covers:
- list with exam_cycle_id returns only matching papers
- list without exam_cycle_id returns all (existing behavior)
- list with unknown cycle returns empty array (not 404)
- GET /{paper_id} happy path returns full row
- GET /{paper_id} unknown id → 404
- both endpoints respect the permission gate
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intel_cms as cms_api
from app.core.auth import get_current_user
from tests.exam_intelligence.test_cms_taxonomy import TaxSBStub

_BASE = "/api/admin/exam-intelligence-cms"


def _client(sb, *, authed: bool = True):
    app = FastAPI()
    app.include_router(cms_api.router, prefix="/api")
    cms_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[cms_api._flag_enabled] = lambda: None
    if authed:
        app.dependency_overrides[get_current_user] = lambda: {
            "id": "admin-1", "role": "super_admin", "permissions": [cms_api.PERM_CMS],
        }
    return TestClient(app, raise_server_exceptions=False)


def _seed():
    return {
        "pyq_papers": [
            {"id": "p1", "exam_id": "e1", "exam_cycle_id": "cycle-a", "year": 2024,
             "trust_status": "pending"},
            {"id": "p2", "exam_id": "e1", "exam_cycle_id": "cycle-b", "year": 2023,
             "trust_status": "pending"},
            {"id": "p3", "exam_id": "e1", "exam_cycle_id": "cycle-a", "year": 2022,
             "trust_status": "verified"},
        ],
    }


def test_list_with_exam_cycle_id_returns_only_matching():
    sb = TaxSBStub(_seed())
    r = _client(sb).get(f"{_BASE}/pyq-papers?exam_id=e1&exam_cycle_id=cycle-a")
    assert r.status_code == 200, r.text
    ids = [p["id"] for p in r.json()["items"]]
    assert sorted(ids) == ["p1", "p3"]
    assert "p2" not in ids


def test_list_without_exam_cycle_id_returns_all():
    sb = TaxSBStub(_seed())
    r = _client(sb).get(f"{_BASE}/pyq-papers?exam_id=e1")
    assert r.status_code == 200
    ids = [p["id"] for p in r.json()["items"]]
    assert sorted(ids) == ["p1", "p2", "p3"]


def test_list_with_unknown_cycle_returns_empty():
    sb = TaxSBStub(_seed())
    r = _client(sb).get(f"{_BASE}/pyq-papers?exam_cycle_id=cycle-nonexistent")
    assert r.status_code == 200
    assert r.json()["items"] == []


def test_get_paper_happy_path():
    sb = TaxSBStub(_seed())
    r = _client(sb).get(f"{_BASE}/pyq-papers/p1")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == "p1"
    assert body["exam_cycle_id"] == "cycle-a"


def test_get_paper_unknown_returns_404():
    sb = TaxSBStub(_seed())
    r = _client(sb).get(f"{_BASE}/pyq-papers/no-such-paper")
    assert r.status_code == 404


def test_list_permission_gate():
    sb = TaxSBStub(_seed())
    r = _client(sb, authed=False).get(f"{_BASE}/pyq-papers")
    assert r.status_code in (401, 403)


def test_get_permission_gate():
    sb = TaxSBStub(_seed())
    r = _client(sb, authed=False).get(f"{_BASE}/pyq-papers/p1")
    assert r.status_code in (401, 403)
