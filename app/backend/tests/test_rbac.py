"""RBAC hardening tests — centralized guards, role endpoints, audit, bootstrap.

Mirrors the existing admin-endpoint test style: build a tiny FastAPI app,
override ``get_current_user`` with a plain dict, and monkeypatch
``get_supabase_admin`` with an in-memory fake. The fake models the Supabase
auth admin API (list_users / get_user_by_id / update_user_by_id / create_user)
plus ``.table()`` for admin_audit_logs — no real Supabase is contacted.
"""
from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api import admin_ops
from app.core.auth import (
    get_current_user,
    require_admin,
    require_permission,
    require_super_admin,
)
from tests.persona_questions._stub import SBStub


# ─── Fakes for the Supabase auth admin API ─────────────────────────────────


class _FakeUser:
    def __init__(self, uid, email, role=None, app_metadata=None, user_metadata=None):
        self.id = uid
        self.email = email
        self.app_metadata = dict(app_metadata) if app_metadata is not None else (
            {"role": role} if role else {}
        )
        self.user_metadata = dict(user_metadata or {})
        self.created_at = None
        self.last_sign_in_at = None


class _UserResp:
    def __init__(self, user):
        self.user = user


class _FakeAuthAdmin:
    def __init__(self, users):
        self.users = users
        self.updated: list[tuple[str, dict]] = []
        self.created: list[dict] = []

    def list_users(self, page=None, per_page=None):
        # All users live on page 1; later pages are empty (pagination stop).
        return list(self.users) if page in (None, 1) else []

    def get_user_by_id(self, uid):
        for u in self.users:
            if u.id == uid:
                return _UserResp(u)
        return _UserResp(None)

    def update_user_by_id(self, uid, attributes):
        for u in self.users:
            if u.id == uid:
                if isinstance(attributes, dict) and attributes.get("app_metadata") is not None:
                    u.app_metadata = dict(attributes["app_metadata"])
                self.updated.append((uid, attributes))
                return _UserResp(u)
        return _UserResp(None)

    def create_user(self, attributes):
        new = _FakeUser(
            f"new-{len(self.users) + 1}",
            attributes.get("email"),
            app_metadata=attributes.get("app_metadata"),
            user_metadata=attributes.get("user_metadata"),
        )
        self.users.append(new)
        self.created.append(attributes)
        return _UserResp(new)
    # Deliberately NO sign_out: force-signout falls back to the ban cycle.


class _FakeAuth:
    def __init__(self, admin):
        self.admin = admin


class FakeSupabase(SBStub):
    def __init__(self, users, db=None):
        super().__init__(db if db is not None else {"admin_audit_logs": [], "profiles": []})
        self.auth = _FakeAuth(_FakeAuthAdmin(users))


def _build_app(sb, user):
    app = FastAPI()
    app.include_router(admin_ops.router, prefix="/api")
    admin_ops.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[get_current_user] = lambda: user
    return app


ANON = {"id": "a1", "email": "a@x.com", "role": "admin", "is_anonymous": True, "permissions": []}
USER = {"id": "u1", "email": "u@x.com", "role": "user", "permissions": []}
ADMIN = {"id": "ad1", "email": "ad@x.com", "role": "admin", "permissions": []}
SUPER = {"id": "sa1", "email": "sa@x.com", "role": "super_admin", "permissions": []}


# ─── Unit: require_admin ────────────────────────────────────────────────────


def test_require_admin_anonymous_403():
    with pytest.raises(HTTPException) as e:
        require_admin(dict(ANON))
    assert e.value.status_code == 403


def test_require_admin_user_403():
    with pytest.raises(HTTPException) as e:
        require_admin(dict(USER))
    assert e.value.status_code == 403


def test_require_admin_admin_ok():
    assert require_admin(dict(ADMIN))["role"] == "admin"


def test_require_admin_super_admin_ok():
    assert require_admin(dict(SUPER))["role"] == "super_admin"


# ─── Unit: require_super_admin ──────────────────────────────────────────────


def test_require_super_admin_admin_403():
    with pytest.raises(HTTPException) as e:
        require_super_admin(dict(ADMIN))
    assert e.value.status_code == 403


def test_require_super_admin_super_admin_ok():
    assert require_super_admin(dict(SUPER))["role"] == "super_admin"


# ─── Unit: require_permission ───────────────────────────────────────────────


def test_require_permission_super_admin_bypass():
    dep = require_permission("scraper.manage")
    assert dep({"role": "super_admin", "permissions": []})["role"] == "super_admin"


def test_require_permission_admin_without_perm_403():
    dep = require_permission("scraper.manage")
    with pytest.raises(HTTPException) as e:
        dep({"role": "admin", "permissions": []})
    assert e.value.status_code == 403


def test_require_permission_anonymous_403():
    dep = require_permission("scraper.manage")
    with pytest.raises(HTTPException) as e:
        dep({"role": "admin", "is_anonymous": True, "permissions": ["scraper.manage"]})
    assert e.value.status_code == 403


# ─── Route: GET /admin/users ────────────────────────────────────────────────


def _seed_users():
    return [
        _FakeUser("sa1", "sa@x.com", role="super_admin"),
        _FakeUser("ad1", "ad@x.com", role="admin"),
        _FakeUser("u1", "u@x.com", role="user"),
    ]


def test_get_admin_users_user_403():
    sb = FakeSupabase(_seed_users())
    client = TestClient(_build_app(sb, USER))
    assert client.get("/api/admin/users").status_code == 403


def test_get_admin_users_admin_ok():
    sb = FakeSupabase(_seed_users())
    client = TestClient(_build_app(sb, ADMIN))
    r = client.get("/api/admin/users")
    assert r.status_code == 200, r.text
    roles = {row["id"]: row["role"] for row in r.json()["items"]}
    assert roles == {"sa1": "super_admin", "ad1": "admin", "u1": "user"}


# ─── Route: PUT /admin/users/{id}/role ──────────────────────────────────────


def test_put_user_role_admin_403():
    sb = FakeSupabase(_seed_users())
    client = TestClient(_build_app(sb, ADMIN))
    r = client.put("/api/admin/users/u1/role", json={"role": "admin"})
    assert r.status_code == 403


def test_put_user_role_super_admin_ok():
    users = _seed_users()
    sb = FakeSupabase(users)
    client = TestClient(_build_app(sb, SUPER))
    r = client.put("/api/admin/users/u1/role", json={"role": "admin"})
    assert r.status_code == 200, r.text
    assert r.json()["new_role"] == "admin"
    # app_metadata.role written on the target.
    target = next(u for u in sb.auth.admin.users if u.id == "u1")
    assert target.app_metadata["role"] == "admin"


def test_role_change_writes_audit():
    sb = FakeSupabase(_seed_users())
    client = TestClient(_build_app(sb, SUPER))
    client.put("/api/admin/users/u1/role", json={"role": "admin", "reason": "promo"})
    audits = sb.db["admin_audit_logs"]
    assert any(a["action"] == "rbac.role_change" and a["entity_id"] == "u1" for a in audits)
    row = next(a for a in audits if a["action"] == "rbac.role_change")
    assert row["new_value"]["new_role"] == "admin"
    assert row["new_value"]["old_role"] == "user"
    assert row["new_value"]["reason"] == "promo"


def test_cannot_remove_last_super_admin():
    # Only one super_admin in the system → demoting it must fail.
    users = [_FakeUser("sa1", "sa@x.com", role="super_admin"), _FakeUser("u1", "u@x.com", role="user")]
    sb = FakeSupabase(users)
    client = TestClient(_build_app(sb, SUPER))
    r = client.put("/api/admin/users/sa1/role", json={"role": "admin"})
    assert r.status_code == 400
    assert "super_admin" in r.json()["detail"].lower()
    # Unchanged.
    assert next(u for u in users if u.id == "sa1").app_metadata["role"] == "super_admin"


def test_cannot_self_demote_when_sole_super_admin():
    users = [_FakeUser("sa1", "sa@x.com", role="super_admin")]
    sb = FakeSupabase(users)
    client = TestClient(_build_app(sb, SUPER))  # SUPER.id == "sa1"
    r = client.put("/api/admin/users/sa1/role", json={"role": "user"})
    assert r.status_code == 400


def test_self_demote_allowed_when_another_super_admin_exists():
    users = [
        _FakeUser("sa1", "sa@x.com", role="super_admin"),
        _FakeUser("sa2", "sa2@x.com", role="super_admin"),
    ]
    sb = FakeSupabase(users)
    client = TestClient(_build_app(sb, SUPER))  # actor sa1
    r = client.put("/api/admin/users/sa1/role", json={"role": "admin"})
    assert r.status_code == 200, r.text
    assert r.json()["new_role"] == "admin"


def test_mentor_role_input_400():
    sb = FakeSupabase(_seed_users())
    client = TestClient(_build_app(sb, SUPER))
    r = client.put("/api/admin/users/u1/role", json={"role": "mentor"})
    assert r.status_code == 400
    assert r.json()["detail"] == "mentor is not an auth role"


def test_role_change_response_requires_refresh_flag():
    sb = FakeSupabase(_seed_users())
    client = TestClient(_build_app(sb, SUPER))
    r = client.put("/api/admin/users/u1/role", json={"role": "admin"})
    assert r.status_code == 200, r.text
    assert r.json()["requires_session_refresh"] is True


# ─── Route: create + force-signout ──────────────────────────────────────────


def test_create_user_super_admin_ok():
    sb = FakeSupabase(_seed_users())
    client = TestClient(_build_app(sb, SUPER))
    r = client.post(
        "/api/admin/users/create",
        json={"email": "new@x.com", "password": "supersecret", "name": "New", "role": "admin"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["user"]["role"] == "admin"
    assert any(a["action"] == "rbac.admin_invite" for a in sb.db["admin_audit_logs"])


def test_create_user_mentor_role_400():
    sb = FakeSupabase(_seed_users())
    client = TestClient(_build_app(sb, SUPER))
    r = client.post(
        "/api/admin/users/create",
        json={"email": "m@x.com", "password": "supersecret", "role": "mentor"},
    )
    assert r.status_code == 400


def test_create_user_admin_403():
    sb = FakeSupabase(_seed_users())
    client = TestClient(_build_app(sb, ADMIN))
    r = client.post(
        "/api/admin/users/create",
        json={"email": "new@x.com", "password": "supersecret", "role": "admin"},
    )
    assert r.status_code == 403


def test_force_signout_super_admin_ok():
    sb = FakeSupabase(_seed_users())
    client = TestClient(_build_app(sb, SUPER))
    r = client.post("/api/admin/users/u1/force-signout")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["signout_supported"] is True  # ban-cycle fallback
    assert any(a["action"] == "rbac.force_signout" for a in sb.db["admin_audit_logs"])


def test_force_signout_admin_403():
    sb = FakeSupabase(_seed_users())
    client = TestClient(_build_app(sb, ADMIN))
    assert client.post("/api/admin/users/u1/force-signout").status_code == 403


# ─── Bootstrap script ───────────────────────────────────────────────────────


def test_bootstrap_promotes_and_audits():
    from scripts.bootstrap_super_admin import run

    users = [_FakeUser("u1", "boss@x.com", role=None)]
    sb = FakeSupabase(users)
    code, msg = run("boss@x.com", sb=sb)
    assert code == 0
    assert users[0].app_metadata["role"] == "super_admin"
    assert any(a["action"] == "rbac.bootstrap_super_admin" for a in sb.db["admin_audit_logs"])


def test_bootstrap_idempotent_already_super_admin():
    from scripts.bootstrap_super_admin import run

    sb = FakeSupabase([_FakeUser("u1", "boss@x.com", role="super_admin")])
    code, msg = run("boss@x.com", sb=sb)
    assert code == 0
    assert msg == "already super_admin"


def test_bootstrap_no_user_exit_2():
    from scripts.bootstrap_super_admin import run

    sb = FakeSupabase([_FakeUser("u1", "someone@x.com", role="user")])
    code, msg = run("absent@x.com", sb=sb)
    assert code == 2 and msg == "no user"


def test_bootstrap_ambiguous_exit_3():
    from scripts.bootstrap_super_admin import run

    sb = FakeSupabase([
        _FakeUser("u1", "dup@x.com", role="user"),
        _FakeUser("u2", "dup@x.com", role="user"),
    ])
    code, msg = run("dup@x.com", sb=sb)
    assert code == 3 and msg == "ambiguous"
