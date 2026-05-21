"""Tests for the anonymous→permanent merge-claim endpoints.

Covers the Python orchestration + auth gating of
``POST /api/onboarding/merge-claim/create`` and ``/consume``:

* G — create requires an anonymous session; a permanent caller is rejected.
* create mints a token, stores only its sha256 hash, and returns the plaintext
  exactly once with a 15-minute expiry.
* consume requires a permanent session; an anonymous caller is rejected.
* consume hashes the token, calls ``consume_profile_merge_claim`` with the
  caller's id, and maps the RPC status discriminator to the right HTTP code.
* D — a replay (``already_consumed``) is a 200 no-op that returns the prior
  result and does NOT re-delete the anon auth user.

The merge SQL itself (criteria B/C/E/F/H) lives in the plpgsql RPC and is
exercised against a real Postgres via the manual repro steps in the PR; the
``SBStub`` fake can't run plpgsql, so here we stub the RPC's return value and
assert the endpoint's contract around it.
"""
from __future__ import annotations

import hashlib

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core import auth as auth_module
from app.profile import merge_claim as mc_module
from tests.persona_questions._stub import SBStub, _RpcCall

PERMANENT_ID = "664d94c6-907d-482a-8a0b-95571712075f"
ANON_ID = "222ca78e-752e-4a7a-b6dc-cbe8eaa92171"


class _FakeAdmin:
    def __init__(self) -> None:
        self.deleted: list[str] = []

    def delete_user(self, uid: str) -> None:
        self.deleted.append(uid)


class _FakeAuth:
    def __init__(self) -> None:
        self.admin = _FakeAdmin()


class RpcSBStub(SBStub):
    """SBStub plus a canned ``consume_profile_merge_claim`` RPC + fake auth admin."""

    def __init__(self, db=None, rpc_result=None) -> None:
        super().__init__(db)
        self.rpc_result = rpc_result
        self.rpc_calls: list[tuple[str, dict]] = []
        self.auth = _FakeAuth()

    def rpc(self, name, params=None):
        self.rpc_calls.append((name, dict(params or {})))
        if name == "consume_profile_merge_claim":
            return _RpcCall(self.rpc_result)
        return super().rpc(name, params)


def _build_app(*, is_anonymous: bool, user_id: str, rpc_result=None):
    sb = RpcSBStub({"anonymous_profile_merge_claims": []}, rpc_result=rpc_result)
    mc_module.get_supabase_admin = lambda: sb  # type: ignore[assignment]

    fake_user = {"id": user_id, "email": "u@example.com", "is_anonymous": is_anonymous}
    app = FastAPI()
    app.include_router(mc_module.router, prefix="/api")
    # The route deps (required_anonymous / required_permanent) wrap
    # get_current_user, so overriding the base dependency flows through.
    app.dependency_overrides[auth_module.get_current_user] = lambda: fake_user
    return app, sb


# ── create ────────────────────────────────────────────────────────────────


def test_create_requires_anonymous_session_rejects_permanent():
    # Criterion G: a permanent user can't mint a claim.
    app, sb = _build_app(is_anonymous=False, user_id=PERMANENT_ID)
    client = TestClient(app)
    r = client.post("/api/onboarding/merge-claim/create", json={})
    assert r.status_code == 403, r.text
    assert sb.db["anonymous_profile_merge_claims"] == []


def test_create_mints_token_and_stores_only_the_hash():
    app, sb = _build_app(is_anonymous=True, user_id=ANON_ID)
    client = TestClient(app)
    r = client.post("/api/onboarding/merge-claim/create", json={})
    assert r.status_code == 200, r.text
    body = r.json()
    token = body["token"]
    assert token and isinstance(token, str)
    assert body["expires_at"]

    rows = sb.db["anonymous_profile_merge_claims"]
    assert len(rows) == 1
    stored = rows[0]
    assert stored["anonymous_user_id"] == ANON_ID
    # Plaintext is never persisted — only its sha256 hex digest.
    expected_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    assert stored["claim_token_hash"] == expected_hash
    assert stored["claim_token_hash"] != token
    assert len(stored["claim_token_hash"]) == 64
    assert "expires_at" in stored


# ── consume ─────────────────────────────────────────────────────────────────


def test_consume_requires_permanent_session_rejects_anonymous():
    # Mirror of G on the consume side.
    app, _ = _build_app(
        is_anonymous=True,
        user_id=ANON_ID,
        rpc_result={"status": "ok", "result": {}},
    )
    client = TestClient(app)
    r = client.post("/api/onboarding/merge-claim/consume", json={"token": "x" * 32})
    assert r.status_code == 403, r.text


def test_consume_ok_hashes_token_calls_rpc_and_deletes_anon_user():
    merged = {"profiles": {"columns_filled": 2}, "persona_question_answers": {"inserted": 7, "skipped": 1}}
    app, sb = _build_app(
        is_anonymous=False,
        user_id=PERMANENT_ID,
        rpc_result={
            "status": "ok",
            "result": merged,
            "anonymous_user_id": ANON_ID,
            "permanent_user_id": PERMANENT_ID,
        },
    )
    client = TestClient(app)
    token = "tok_" + "a" * 40
    r = client.post("/api/onboarding/merge-claim/consume", json={"token": token})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["already_consumed"] is False
    assert body["merged"] == merged

    # RPC was called with the hash (never the plaintext) and the caller's id.
    assert len(sb.rpc_calls) == 1
    name, params = sb.rpc_calls[0]
    assert name == "consume_profile_merge_claim"
    assert params["p_token_hash"] == hashlib.sha256(token.encode("utf-8")).hexdigest()
    assert params["p_permanent_user_id"] == PERMANENT_ID

    # Fresh merge tidies up the now-empty anon auth user.
    assert sb.auth.admin.deleted == [ANON_ID]


def test_consume_replay_is_idempotent_noop_and_does_not_redelete():
    # Criterion D: second consume of the same token returns the prior result
    # and must NOT re-run side effects (no auth delete).
    prior = {"profiles": {"columns_filled": 0}}
    app, sb = _build_app(
        is_anonymous=False,
        user_id=PERMANENT_ID,
        rpc_result={
            "status": "already_consumed",
            "result": prior,
            "anonymous_user_id": ANON_ID,
            "permanent_user_id": PERMANENT_ID,
        },
    )
    client = TestClient(app)
    r = client.post("/api/onboarding/merge-claim/consume", json={"token": "y" * 32})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["already_consumed"] is True
    assert body["merged"] == prior
    assert sb.auth.admin.deleted == []


def test_consume_status_maps_to_http_codes():
    cases = {
        "not_found": 404,
        "expired": 410,
        "anon_missing": 409,
        "self_merge": 409,
    }
    for rpc_status, http_code in cases.items():
        app, _ = _build_app(
            is_anonymous=False,
            user_id=PERMANENT_ID,
            rpc_result={"status": rpc_status},
        )
        client = TestClient(app)
        r = client.post("/api/onboarding/merge-claim/consume", json={"token": "z" * 32})
        assert r.status_code == http_code, f"{rpc_status} -> {r.status_code}: {r.text}"
