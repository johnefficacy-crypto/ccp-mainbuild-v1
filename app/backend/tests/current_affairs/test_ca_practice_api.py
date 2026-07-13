"""Router-level tests for the CA learner attempt API (GQR-G5a) — status mapping.

Verifies the endpoints translate the service/RPC domain errors into 404/403/422 rather
than leaking 500s (checkpost #976 F9). Reuses the RPC-emulating ``CaSB``.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import current_affairs_practice as api
from app.core.auth import get_current_user
from tests.current_affairs.test_ca_attempts import CaSB, _attempt_seed

_A = "11111111-1111-1111-1111-111111111111"  # a real attempt uuid path value
_Q = "22222222-2222-2222-2222-222222222222"
_O = "33333333-3333-3333-3333-333333333333"


def _client(sb, user_id="u1"):
    app = FastAPI()
    app.include_router(api.router, prefix="/api")
    app.dependency_overrides[get_current_user] = lambda: {"id": user_id}
    api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    return TestClient(app)


def _seed_owned(user_id="u1", status="in_progress"):
    seed = _attempt_seed(status)
    seed["current_affairs_attempts"][0]["id"] = _A
    seed["current_affairs_attempts"][0]["user_id"] = user_id
    resp = seed["current_affairs_attempt_responses"][0]
    resp["attempt_id"] = _A
    resp["mock_question_id"] = _Q
    resp["question_snapshot"]["options"] = [{"id": _O, "option_text": "RBI", "option_index": 0}]
    resp["question_snapshot"]["correct_option_id"] = _O
    return seed


def test_get_unknown_attempt_is_404():
    resp = _client(CaSB({"current_affairs_attempts": []})).get(f"/api/study/current-affairs/attempts/{_A}")
    assert resp.status_code == 404


def test_get_non_owner_is_403():
    resp = _client(CaSB(_seed_owned("owner")), user_id="intruder").get(
        f"/api/study/current-affairs/attempts/{_A}")
    assert resp.status_code == 403


def test_get_owned_attempt_is_200():
    resp = _client(CaSB(_seed_owned("u1"))).get(f"/api/study/current-affairs/attempts/{_A}")
    assert resp.status_code == 200
    assert resp.json()["attempt_id"] == _A


def test_save_non_owner_is_403():
    resp = _client(CaSB(_seed_owned("owner")), user_id="intruder").post(
        f"/api/study/current-affairs/attempts/{_A}/answer",
        json={"question_id": _Q, "selected_option_id": _O, "client_seq": 1})
    assert resp.status_code == 403


def test_save_option_not_in_question_is_422():
    resp = _client(CaSB(_seed_owned("u1"))).post(
        f"/api/study/current-affairs/attempts/{_A}/answer",
        json={"question_id": _Q, "selected_option_id": "44444444-4444-4444-4444-444444444444",
              "client_seq": 1})
    assert resp.status_code == 422


def test_save_ok_is_200():
    resp = _client(CaSB(_seed_owned("u1"))).post(
        f"/api/study/current-affairs/attempts/{_A}/answer",
        json={"question_id": _Q, "selected_option_id": _O, "client_seq": 1})
    assert resp.status_code == 200
    assert resp.json().get("ok")


def test_submit_non_owner_is_403():
    resp = _client(CaSB(_seed_owned("owner")), user_id="intruder").post(
        f"/api/study/current-affairs/attempts/{_A}/submit")
    assert resp.status_code == 403


def test_submit_ok_is_200():
    resp = _client(CaSB(_seed_owned("u1"))).post(f"/api/study/current-affairs/attempts/{_A}/submit")
    assert resp.status_code == 200
    assert resp.json()["outcome"] == "submitted"


class _InfraFailSB(CaSB):
    """Emulates a Supabase transport/DB fault (not a domain token) on save."""
    def rpc(self, name, params=None):
        if name == "ca_save_current_affairs_answer":
            raise RuntimeError("connection reset by peer")
        return super().rpc(name, params)


def test_save_infra_fault_is_500_not_422():
    # F5: an unrecognised infrastructure failure must NOT be mislabelled a learner 422.
    app = FastAPI()
    app.include_router(api.router, prefix="/api")
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1"}
    api.get_supabase_admin = lambda: _InfraFailSB(_seed_owned("u1"))  # type: ignore[assignment]
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(f"/api/study/current-affairs/attempts/{_A}/answer",
                       json={"question_id": _Q, "selected_option_id": _O, "client_seq": 1})
    assert resp.status_code == 500


def test_save_negative_seq_rejected_by_schema():
    # F5: Pydantic bounds reject negative/out-of-range timing + sequence before the RPC.
    resp = _client(CaSB(_seed_owned("u1"))).post(
        f"/api/study/current-affairs/attempts/{_A}/answer",
        json={"question_id": _Q, "selected_option_id": _O, "client_seq": -1})
    assert resp.status_code == 422
