"""Router-layer tests for Content Studio CA question-candidate review + promotion
(GQR-G4a). The atomic RPC behaviour (CAS, audit, bank insert, links) is proven
against real Postgres by `app/supabase/validation/validate_ca_promotion_rpcs.sql`;
here we prove the router contract: read gating, the review transition guard, the
publish gate on promotion, and RPC param mapping / error → HTTP.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import content_studio as cs
from app.core.auth import get_current_user
from tests.persona_questions._stub import SBStub, _Exec, _Query

_BASE = "/api/admin/content-studio"
REVIEW = cs.PERM_REVIEW
AUTHOR = cs.PERM_AUTHOR
PUBLISH = cs.PERM_PUBLISH

_CAND = "00000000-0000-0000-0000-0000000000e1"
_EVENT = "00000000-0000-0000-0000-0000000000e2"


class _CSQuery(_Query):
    def __init__(self, name, db):
        super().__init__(name, db)
        self._count_exact = False
        self._range = None

    def select(self, *args, **kwargs):
        if kwargs.get("count") == "exact":
            self._count_exact = True
        return self

    def range(self, lo, hi):
        self._range = (lo, hi)
        return self

    def execute(self):
        res = super().execute()
        out = _Exec(list(res.data))
        if self._count_exact:
            out.count = len(out.data)
        if self._range:
            lo, hi = self._range
            out.data = out.data[lo:hi + 1]
        return out


class _CSRpc:
    def __init__(self, stub, fn, params):
        self._stub, self._fn, self._params = stub, fn, params

    def execute(self):
        self._stub.rpc_calls.append((self._fn, self._params))
        if self._stub.rpc_error is not None:
            raise RuntimeError(self._stub.rpc_error)
        return _Exec(self._stub.rpc_result if self._stub.rpc_result is not None
                     else {"ok": True, "audit_id": "aud-1"})


class CSSBStub(SBStub):
    def __init__(self, db=None):
        super().__init__(db)
        self.rpc_calls: list[tuple[str, dict]] = []
        self.rpc_error: str | None = None
        self.rpc_result = None

    def table(self, name):
        return _CSQuery(name, self.db)

    def rpc(self, fn, params=None):
        return _CSRpc(self, fn, params or {})


def _client(sb, *, permissions=None, role="admin", anonymous=False):
    app = FastAPI()
    app.include_router(cs.router, prefix="/api")
    cs.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[cs._flag_enabled] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "op-1", "email": "op@example.com", "role": role,
        "permissions": permissions if permissions is not None else [REVIEW],
        "is_anonymous": anonymous,
    }
    return TestClient(app, raise_server_exceptions=False)


def _seed(status="review_ready"):
    return {
        "current_affairs_question_candidates": [{
            "id": _CAND, "event_id": _EVENT, "status": status,
            "question_payload": {"stem": "Q?", "correct_option_id": "a"},
            "question_fingerprint": "fp-1", "created_at": "2026-07-10T00:00:00Z",
        }],
        "current_affairs_events": [{"id": _EVENT, "canonical_title": "E", "status": "active"}],
        "current_affairs_claims": [], "current_affairs_generation_runs": [],
    }


# ── read gating ─────────────────────────────────────────────────────────────
def test_list_readable_by_content_perms_denied_otherwise():
    assert _client(CSSBStub(_seed()), permissions=[REVIEW]).get(
        f"{_BASE}/ca-question-candidates").status_code == 200
    assert _client(CSSBStub(_seed()), permissions=["some.other"]).get(
        f"{_BASE}/ca-question-candidates").status_code == 403


def test_get_returns_review_context():
    r = _client(CSSBStub(_seed()), permissions=[REVIEW]).get(f"{_BASE}/ca-question-candidates/{_CAND}")
    assert r.status_code == 200
    body = r.json()
    assert body["candidate"]["id"] == _CAND and body["event"]["id"] == _EVENT
    assert "claims" in body and "generation_runs" in body


# ── review transition guard + RPC mapping ───────────────────────────────────
def test_review_rejects_illegal_transition():
    sb = CSSBStub(_seed())
    r = _client(sb, permissions=[REVIEW]).post(
        f"{_BASE}/ca-question-candidates/{_CAND}/review",
        json={"status": "promoted", "expected_status": "review_ready"})
    assert r.status_code == 422
    assert not sb.rpc_calls  # never reaches the RPC


def test_review_approve_calls_rpc_with_params():
    sb = CSSBStub(_seed())
    r = _client(sb, permissions=[REVIEW]).post(
        f"{_BASE}/ca-question-candidates/{_CAND}/review",
        json={"status": "approved", "expected_status": "review_ready"})
    assert r.status_code == 200
    fn, params = sb.rpc_calls[0]
    assert fn == "ca_review_candidate"
    assert params["p_candidate_id"] == _CAND
    assert params["p_new_status"] == "approved" and params["p_expected_status"] == "review_ready"
    assert params["p_actor_user_id"] == "op-1"


def test_send_back_requires_reason():
    sb = CSSBStub(_seed(status="approved"))
    r = _client(sb, permissions=[REVIEW]).post(
        f"{_BASE}/ca-question-candidates/{_CAND}/review",
        json={"status": "review_ready", "expected_status": "approved"})
    assert r.status_code == 422 and not sb.rpc_calls


def test_review_denied_for_author_only():
    r = _client(CSSBStub(_seed()), permissions=[AUTHOR]).post(
        f"{_BASE}/ca-question-candidates/{_CAND}/review",
        json={"status": "approved", "expected_status": "review_ready"})
    assert r.status_code == 403


def test_review_conflict_maps_to_409():
    sb = CSSBStub(_seed())
    sb.rpc_error = "concurrent_modification: expected review_ready but found approved (P0409)"
    r = _client(sb, permissions=[REVIEW]).post(
        f"{_BASE}/ca-question-candidates/{_CAND}/review",
        json={"status": "approved", "expected_status": "review_ready"})
    assert r.status_code == 409


# ── promotion requires the higher publish gate ──────────────────────────────
def test_promote_denied_without_publish_permission():
    r = _client(CSSBStub(_seed(status="approved")), permissions=[REVIEW]).post(
        f"{_BASE}/ca-question-candidates/{_CAND}/promote", json={})
    assert r.status_code == 403


def test_promote_calls_rpc_when_publish_permitted():
    sb = CSSBStub(_seed(status="approved"))
    sb.rpc_result = {"ok": True, "mock_question_id": "mq-1", "candidate_id": _CAND}
    r = _client(sb, permissions=[PUBLISH]).post(
        f"{_BASE}/ca-question-candidates/{_CAND}/promote", json={"expected_status": "approved"})
    assert r.status_code == 200
    fn, params = sb.rpc_calls[0]
    assert fn == "ca_promote_candidate"
    assert params["p_candidate_id"] == _CAND and params["p_expected_status"] == "approved"
    assert params["p_actor_user_id"] == "op-1"
