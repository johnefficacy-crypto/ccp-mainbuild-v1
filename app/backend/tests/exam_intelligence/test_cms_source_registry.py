"""GET /source-registry — official-source filter guard (PR-H).

Default (include_discovery=false) returns only rows where
is_official_source=true AND discovery_only=false.
include_discovery=true returns all rows.
Organization dropdown / org endpoint untouched (regression).
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intel_cms as cms_api
from app.core.auth import get_current_user
from tests.exam_intelligence.test_cms_taxonomy import TaxSBStub

_BASE = "/api/admin/exam-intelligence-cms"
_URL = f"{_BASE}/source-registry"


def _client(sb: TaxSBStub) -> TestClient:
    app = FastAPI()
    app.include_router(cms_api.router, prefix="/api")
    cms_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[cms_api._flag_enabled] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "a1", "role": "super_admin", "permissions": [cms_api.PERM_CMS],
    }
    return TestClient(app, raise_server_exceptions=False)


def _seed():
    return {
        "source_registry": [
            {
                "id": "src-official",
                "source_name": "UPSC Official",
                "official_url": "https://upsc.gov.in",
                "source_type": "official",
                "is_official_source": True,
                "discovery_only": False,
                "can_publish_directly": True,
                "is_active": True,
            },
            {
                "id": "src-aggregator",
                "source_name": "News Aggregator",
                "official_url": "https://agg.example.com",
                "source_type": "aggregator",
                "is_official_source": False,
                "discovery_only": True,
                "can_publish_directly": False,
                "is_active": True,
            },
            {
                "id": "src-discovery",
                "source_name": "Discovery Feed",
                "official_url": "https://discovery.example.com",
                "source_type": "aggregator",
                "is_official_source": True,
                "discovery_only": True,
                "can_publish_directly": False,
                "is_active": True,
            },
            {
                "id": "src-inactive",
                "source_name": "Retired Official",
                "official_url": "https://retired.gov.in",
                "source_type": "official",
                "is_official_source": True,
                "discovery_only": False,
                "can_publish_directly": True,
                "is_active": False,
            },
        ]
    }


def test_default_returns_official_only():
    """Default filter: is_official_source=true AND discovery_only=false."""
    sb = TaxSBStub(_seed())
    r = _client(sb).get(_URL)
    assert r.status_code == 200, r.text
    ids = {it["id"] for it in r.json()["items"]}
    assert "src-official" in ids
    assert "src-aggregator" not in ids, "aggregator row must be excluded by default"
    assert "src-discovery" not in ids, "discovery_only=true row must be excluded by default"
    assert "src-inactive" not in ids, "is_active=false row must be excluded by default"


def test_include_discovery_returns_all():
    """include_discovery=true bypasses is_official_source/discovery_only but NOT is_active."""
    sb = TaxSBStub(_seed())
    r = _client(sb).get(f"{_URL}?include_discovery=true")
    assert r.status_code == 200, r.text
    ids = {it["id"] for it in r.json()["items"]}
    assert "src-official" in ids
    assert "src-aggregator" in ids
    assert "src-discovery" in ids
    assert "src-inactive" not in ids, "is_active=false must stay excluded even with include_discovery=true"


def test_response_shape():
    """Response has items/total/limit/offset keys."""
    sb = TaxSBStub(_seed())
    r = _client(sb).get(_URL)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "items" in body
    assert "total" in body
    assert "limit" in body
    assert "offset" in body


def test_source_type_filter():
    """source_type query param narrows results (on top of the default filter)."""
    sb = TaxSBStub(_seed())
    r = _client(sb).get(f"{_URL}?source_type=official")
    assert r.status_code == 200, r.text
    ids = {it["id"] for it in r.json()["items"]}
    assert "src-official" in ids


def test_requires_permission():
    """Unauthenticated request returns 403."""
    app = FastAPI()
    app.include_router(cms_api.router, prefix="/api")
    cms_api.get_supabase_admin = lambda: TaxSBStub(_seed())  # type: ignore[assignment]
    app.dependency_overrides[cms_api._flag_enabled] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "u1", "role": "user", "permissions": [],
    }
    client = TestClient(app, raise_server_exceptions=False)
    r = client.get(_URL)
    assert r.status_code == 403
