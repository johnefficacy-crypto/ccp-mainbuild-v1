"""get_optional_user must distinguish missing-header (anon) from invalid-token (401).

Rules:
  - No Authorization header -> 200, user_id=None  (anonymous OK)
  - Valid token -> 200, user_id set
  - Invalid/expired token -> 401 propagated, NOT silent anon downgrade
"""
from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core import auth as auth_module
from app.core.auth import get_optional_user


class _FakeUser:
    id = "u-optional"
    email = "opt@test.com"
    user_metadata = {}
    app_metadata = {"role": "user", "permissions": []}
    created_at = "2026-01-01T00:00:00Z"


def _build_app(fail: bool = False):
    class _Auth:
        def get_user(self, _token):
            if fail:
                raise RuntimeError("invalid token")

            class _R:
                user = _FakeUser()

            return _R()

    class _Admin:
        auth = _Auth()

    auth_module.get_supabase_admin = lambda: _Admin()  # type: ignore[assignment]

    app = FastAPI()

    @app.get("/probe")
    def probe(user=Depends(get_optional_user)):
        return {"user_id": user["id"] if user else None}

    return app


def _reset_cache():
    with auth_module._token_cache_lock:
        auth_module._token_cache.clear()


def test_no_header_returns_anonymous():
    _reset_cache()
    client = TestClient(_build_app(fail=False), raise_server_exceptions=False)
    r = client.get("/probe")
    assert r.status_code == 200
    assert r.json()["user_id"] is None


def test_valid_token_returns_user():
    _reset_cache()
    client = TestClient(_build_app(fail=False), raise_server_exceptions=False)
    r = client.get("/probe", headers={"Authorization": "Bearer good-token"})
    assert r.status_code == 200
    assert r.json()["user_id"] == "u-optional"


def test_invalid_token_raises_401_not_anon():
    """A present-but-bad token must NOT silently become anonymous (200, None user)."""
    _reset_cache()
    client = TestClient(_build_app(fail=True), raise_server_exceptions=False)
    r = client.get("/probe", headers={"Authorization": "Bearer bad-token"})
    assert r.status_code == 401, (
        f"Expected 401 for invalid token, got {r.status_code}. "
        "Silent anon downgrade was not fixed."
    )
