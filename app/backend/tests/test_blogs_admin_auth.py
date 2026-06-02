from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import blogs as blogs_api
from app.core.auth import get_current_user
from tests.persona_questions._stub import SBStub


BLOG_ID = 1


def _world() -> dict[str, list[dict]]:
    return {
        "blog_posts": [
            {
                "id": BLOG_ID,
                "title": "Existing launch checklist",
                "slug": "existing-launch-checklist",
                "excerpt": "A launch checklist.",
                "content": "Body",
                "status": "draft",
                "updated_at": "2026-01-01T00:00:00+00:00",
                "published_at": None,
                "seo_title": None,
                "seo_description": None,
                "primary_cta_label": None,
                "primary_cta_url": None,
            }
        ]
    }


def _app(monkeypatch, sb: SBStub, user: dict | None = None) -> FastAPI:
    app = FastAPI()
    app.include_router(blogs_api.admin_router, prefix="/api")
    monkeypatch.setattr(blogs_api, "get_supabase_admin", lambda: sb)
    if user is not None:
        app.dependency_overrides[get_current_user] = lambda: user
    return app


def _client(monkeypatch, sb: SBStub, user: dict | None = None) -> TestClient:
    return TestClient(_app(monkeypatch, sb, user), raise_server_exceptions=False)


def _admin_user(**overrides) -> dict:
    user = {"id": "admin-1", "email": "admin@example.com", "role": "admin", "permissions": []}
    user.update(overrides)
    return user


def _content_admin() -> dict:
    return _admin_user(permissions=["blogs.manage"])


def _payload(**overrides) -> dict:
    body = {
        "title": "Updated launch checklist",
        "slug": "updated-launch-checklist",
        "excerpt": "Updated excerpt",
        "content": "Updated body",
        "status": "draft",
        "primary_intent": "eligibility",
        "primary_cta_label": "Check eligibility",
        "primary_cta_url": "/app/onboarding/chat?source=blog",
        "seo_title": "Updated SEO",
        "seo_description": "Updated SEO description",
    }
    body.update(overrides)
    return body


def test_admin_blog_routes_reject_missing_auth(monkeypatch):
    client = _client(monkeypatch, SBStub(_world()))

    assert client.get("/api/admin/blogs").status_code == 401
    assert client.get(f"/api/admin/blogs/{BLOG_ID}").status_code == 401
    assert client.post("/api/admin/blogs", json=_payload()).status_code == 401
    assert client.put(f"/api/admin/blogs/{BLOG_ID}", json=_payload()).status_code == 401
    assert client.post(f"/api/admin/blogs/{BLOG_ID}/publish").status_code == 401
    assert client.post(f"/api/admin/blogs/{BLOG_ID}/archive").status_code == 401


def test_admin_blog_routes_reject_normal_user(monkeypatch):
    client = _client(
        monkeypatch,
        SBStub(_world()),
        {"id": "user-1", "role": "user", "permissions": []},
    )

    assert client.get("/api/admin/blogs").status_code == 403
    assert client.get(f"/api/admin/blogs/{BLOG_ID}").status_code == 403
    assert client.post("/api/admin/blogs", json=_payload()).status_code == 403
    assert client.put(f"/api/admin/blogs/{BLOG_ID}", json=_payload()).status_code == 403
    assert client.post(f"/api/admin/blogs/{BLOG_ID}/publish").status_code == 403
    assert client.post(f"/api/admin/blogs/{BLOG_ID}/archive").status_code == 403


def test_admin_can_list_and_read_blogs(monkeypatch):
    client = _client(monkeypatch, SBStub(_world()), _admin_user())

    listed = client.get("/api/admin/blogs")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == BLOG_ID

    detail = client.get(f"/api/admin/blogs/{BLOG_ID}")
    assert detail.status_code == 200
    assert detail.json()["slug"] == "existing-launch-checklist"


def test_admin_without_blog_permission_cannot_mutate(monkeypatch):
    client = _client(monkeypatch, SBStub(_world()), _admin_user())

    assert client.post("/api/admin/blogs", json=_payload()).status_code == 403
    assert client.put(f"/api/admin/blogs/{BLOG_ID}", json=_payload()).status_code == 403
    assert client.post(f"/api/admin/blogs/{BLOG_ID}/publish").status_code == 403
    assert client.post(f"/api/admin/blogs/{BLOG_ID}/archive").status_code == 403


def test_content_admin_can_create_update_publish_and_archive(monkeypatch):
    sb = SBStub(_world())
    client = _client(monkeypatch, sb, _content_admin())

    created = client.post("/api/admin/blogs", json=_payload(slug="new-launch-checklist"))
    assert created.status_code == 200
    assert created.json()["slug"] == "new-launch-checklist"

    updated = client.put(f"/api/admin/blogs/{BLOG_ID}", json=_payload(status="review"))
    assert updated.status_code == 200
    assert updated.json()["status"] == "review"

    published = client.post(f"/api/admin/blogs/{BLOG_ID}/publish")
    assert published.status_code == 200
    assert published.json()["status"] == "published"
    assert published.json()["published_at"]

    archived = client.post(f"/api/admin/blogs/{BLOG_ID}/archive")
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"
