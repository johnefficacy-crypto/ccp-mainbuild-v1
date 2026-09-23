"""Tests for the PYQ explanation review route.

POST /admin/exam-intelligence-cms/pyq-question-explanations/{id}/review

The route only transitions ``reviewer_status``, and does it through the
``cms_review_pyq_question_explanation`` RPC (migration 230). The stub below
reproduces that function as written, check for check, so these tests show
the route surfacing the RPC's decisions rather than making its own:

- verify succeeds on a pending row that has ``final_answer_option_id``
- verify with ``final_answer_option_id`` null → 422 carrying the RPC message
- verify with ``ambiguity_status`` other than 'none' → 422 (the RPC blocks it)
- reject / needs_correction / pending-reset along the RPC's matrix
- transitions the RPC refuses → 422, never 500
- the audit row is written by the RPC on success and never on failure
"""
from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intel_cms as cms_api
from app.core.auth import get_current_user
from tests.exam_intelligence.test_cms_taxonomy import TaxSBStub, _RpcQuery
from tests.persona_questions._stub import _Exec

_BASE = "/api/admin/exam-intelligence-cms"
_EXPL_ID = "11111111-1111-4111-8111-111111111111"
_OPT_ID = "22222222-2222-4222-8222-222222222222"

_REVIEWER = {
    "id": "33333333-3333-4333-8333-333333333333", "email": "reviewer@example.com",
    "role": "admin", "permissions": [cms_api.PERM_REVIEW],
}
_CMS_ONLY = {
    "id": "44444444-4444-4444-8444-444444444444", "email": "cms@example.com",
    "role": "admin", "permissions": [cms_api.PERM_CMS],
}


def _emulate_review_rpc(db: dict, p: dict) -> dict:
    """cms_review_pyq_question_explanation, migration 230, in the same order."""
    target = p["p_target_status"]
    if target not in ("verified", "rejected", "needs_correction", "pending"):
        raise Exception(f"invalid_target_status: {target}")
    rows = db.setdefault("pyq_question_explanations", [])
    row = next((r for r in rows if r.get("id") == p["p_id"]), None)
    if row is None:
        raise Exception(f"not_found: explanation {p['p_id']} does not exist")
    current = row.get("reviewer_status")
    if current != p["p_expected_status"]:
        raise Exception(
            f"concurrent_modification: expected {p['p_expected_status']} but row is {current}"
        )
    allowed = {
        "pending": ("verified", "rejected", "needs_correction"),
        "needs_correction": ("verified", "rejected", "pending"),
        "verified": ("needs_correction", "rejected"),
        "rejected": ("pending", "needs_correction"),
    }
    if target not in allowed.get(current, ()):
        raise Exception(f"transition_not_allowed: {current} -> {target}")
    if target == "verified":
        if row.get("license_status") not in ("owned", "licensed", "public_domain"):
            raise Exception(f"verify_requires_cleared_license: license_status={row.get('license_status')}")
        if row.get("ambiguity_status") != "none":
            raise Exception(
                f"verify_requires_resolved_ambiguity: ambiguity_status={row.get('ambiguity_status')}"
            )
        if row.get("final_answer_option_id") is None:
            raise Exception("verify_requires_final_answer: final_answer_option_id is null")
    if target == "pending":
        row.update(reviewer_status="pending", reviewed_by=None, reviewed_at=None)
    else:
        row.update(reviewer_status=target, reviewed_by=p["p_actor_user_id"], reviewed_at="now")
    audit_id = str(uuid.uuid4())
    db.setdefault("admin_audit_logs", []).append({
        "id": audit_id,
        "actor_id": p["p_actor_user_id"] or None,
        "actor_email": p["p_actor_email"],
        "admin_user_id": p["p_actor_user_id"] or None,
        "action": "pyq_explanation_review_transition",
        "entity_type": "pyq_question_explanation",
        "entity_id": row["id"],
        "old_value": {"reviewer_status": current},
        "new_value": {"reviewer_status": target},
        "notes": p["p_reviewer_notes"],
    })
    return {"ok": True, "id": row["id"], "prev_status": current,
            "new_status": target, "audit_id": audit_id}


class _ExplRpcQuery(_RpcQuery):
    def execute(self):
        self._db.setdefault("_rpc_calls", []).append((self._fn_name, dict(self._params)))
        if self._fn_name == "cms_review_pyq_question_explanation":
            return _Exec(_emulate_review_rpc(self._db, self._params))
        return super().execute()


class _ExplSB(TaxSBStub):
    def rpc(self, fn_name, params=None):
        return _ExplRpcQuery(fn_name, params or {}, self.db)


def _row(**over) -> dict:
    row = {
        "id": _EXPL_ID,
        "question_id": "q-1",
        "explanation_text": "Because the Act says so.",
        "final_answer_option_id": _OPT_ID,
        "alternate_answer_option_id": None,
        "ambiguity_status": "none",
        "explanation_source_type": "platform_original",
        "license_status": "owned",
        "reviewer_status": "pending",
        "reviewed_by": None,
        "reviewed_at": None,
    }
    row.update(over)
    return row


def _sb(**over) -> _ExplSB:
    return _ExplSB({"pyq_question_explanations": [_row(**over)], "admin_audit_logs": []})


def _client(sb, user=_REVIEWER):
    app = FastAPI()
    app.include_router(cms_api.router, prefix="/api")
    cms_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[cms_api._flag_enabled] = lambda: None
    if user is not None:
        app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app, raise_server_exceptions=False)


def _review(client, status, *, expl_id=_EXPL_ID, reason="reviewed against the answer key"):
    return client.post(
        f"{_BASE}/pyq-question-explanations/{expl_id}/review",
        json={"status": status, "reason": reason},
    )


def _stored(sb) -> dict:
    return sb.db["pyq_question_explanations"][0]


# ── verify ─────────────────────────────────────────────────────────────


def test_verify_succeeds_on_pending_row_with_final_answer():
    sb = _sb()
    r = _review(_client(sb), "verified")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["prev_status"] == "pending" and body["new_status"] == "verified"
    assert body["row"]["reviewer_status"] == "verified"
    assert _stored(sb)["reviewed_by"] == _REVIEWER["id"]


def test_verify_with_null_final_answer_surfaces_rpc_message():
    sb = _sb(final_answer_option_id=None)
    r = _review(_client(sb), "verified")
    assert r.status_code == 422, r.text
    assert "verify_requires_final_answer: final_answer_option_id is null" in r.json()["detail"]
    assert _stored(sb)["reviewer_status"] == "pending"
    assert sb.db["admin_audit_logs"] == []


@pytest.mark.parametrize("ambiguity", ["disputed", "multiple_possible", "source_conflict"])
def test_verify_blocked_by_rpc_when_ambiguity_unresolved(ambiguity):
    # final_answer_option_id is SET here, so the only thing standing in the
    # way is the ambiguity check — proving the RPC blocks it on its own, not
    # merely as a side effect of a null answer (the live held rows have both).
    sb = _sb(ambiguity_status=ambiguity)
    r = _review(_client(sb), "verified")
    assert r.status_code == 422, r.text
    assert f"verify_requires_resolved_ambiguity: ambiguity_status={ambiguity}" in r.json()["detail"]
    assert _stored(sb)["reviewer_status"] == "pending"
    assert sb.db["admin_audit_logs"] == []


@pytest.mark.parametrize("ambiguity", ["disputed", "multiple_possible"])
def test_held_rows_as_they_exist_live_cannot_be_verified(ambiguity):
    # The 8 live held rows: final answer null AND ambiguity unresolved.
    sb = _sb(ambiguity_status=ambiguity, final_answer_option_id=None)
    r = _review(_client(sb), "verified")
    assert r.status_code == 422, r.text
    assert "verify_requires_resolved_ambiguity" in r.json()["detail"]


@pytest.mark.parametrize("license_status", ["permission_pending", "restricted"])
def test_verify_blocked_when_license_not_cleared(license_status):
    sb = _sb(license_status=license_status)
    r = _review(_client(sb), "verified")
    assert r.status_code == 422, r.text
    assert "verify_requires_cleared_license" in r.json()["detail"]


# ── other transitions the RPC accepts ──────────────────────────────────


@pytest.mark.parametrize("target", ["rejected", "needs_correction"])
def test_pending_to_reject_and_needs_correction(target):
    sb = _sb()
    r = _review(_client(sb), target)
    assert r.status_code == 200, r.text
    assert _stored(sb)["reviewer_status"] == target
    assert _stored(sb)["reviewed_by"] == _REVIEWER["id"]


def test_needs_correction_back_to_pending_clears_reviewer():
    sb = _sb(reviewer_status="needs_correction", reviewed_by="someone", reviewed_at="t")
    r = _review(_client(sb), "pending")
    assert r.status_code == 200, r.text
    row = _stored(sb)
    assert row["reviewer_status"] == "pending"
    assert row["reviewed_by"] is None and row["reviewed_at"] is None


def test_verified_to_needs_correction():
    sb = _sb(reviewer_status="verified", reviewed_by="someone", reviewed_at="t")
    r = _review(_client(sb), "needs_correction")
    assert r.status_code == 200, r.text
    assert _stored(sb)["reviewer_status"] == "needs_correction"


# ── transitions the RPC refuses → 422, never 500 ───────────────────────


@pytest.mark.parametrize("current,target", [
    ("verified", "pending"),
    ("pending", "pending"),
    ("rejected", "verified"),
    ("verified", "verified"),
])
def test_disallowed_transition_is_422(current, target):
    sb = _sb(reviewer_status=current)
    r = _review(_client(sb), target)
    assert r.status_code == 422, r.text
    assert f"transition_not_allowed: {current} -> {target}" in r.json()["detail"]
    assert _stored(sb)["reviewer_status"] == current
    assert sb.db["admin_audit_logs"] == []


def test_unknown_target_status_is_422():
    sb = _sb()
    r = _review(_client(sb), "approved")
    assert r.status_code == 422, r.text
    assert "invalid_target_status: approved" in r.json()["detail"]


# ── audit ──────────────────────────────────────────────────────────────


def test_audit_row_written_by_rpc_on_transition():
    sb = _sb()
    r = _review(_client(sb), "verified", reason="checked against the SEBI key")
    assert r.status_code == 200, r.text
    logs = sb.db["admin_audit_logs"]
    assert len(logs) == 1
    log = logs[0]
    assert r.json()["audit_id"] == log["id"]
    assert log["action"] == "pyq_explanation_review_transition"
    assert log["entity_type"] == "pyq_question_explanation"
    assert log["entity_id"] == _EXPL_ID
    assert log["actor_id"] == _REVIEWER["id"]
    assert log["actor_email"] == _REVIEWER["email"]
    assert log["old_value"] == {"reviewer_status": "pending"}
    assert log["new_value"] == {"reviewer_status": "verified"}
    assert log["notes"] == "checked against the SEBI key"


def test_route_passes_expected_status_and_actor_to_rpc():
    sb = _sb(reviewer_status="needs_correction")
    _review(_client(sb), "rejected", reason="duplicate of the official row")
    name, params = sb.db["_rpc_calls"][-1]
    assert name == "cms_review_pyq_question_explanation"
    assert params == {
        "p_id": _EXPL_ID,
        "p_expected_status": "needs_correction",
        "p_target_status": "rejected",
        "p_reviewer_notes": "duplicate of the official row",
        "p_actor_user_id": _REVIEWER["id"],
        "p_actor_email": _REVIEWER["email"],
    }


def test_route_does_not_write_to_the_table_directly():
    # Status moves only inside the RPC: the route issues no UPDATE of its own
    # and no second, Python-side audit row.
    sb = _sb()
    calls: list[str] = []
    original_table = sb.table

    def _spy(name):
        q = original_table(name)
        original_update, original_insert = q.update, q.insert

        def _update(*a, **k):
            calls.append(f"update:{name}")
            return original_update(*a, **k)

        def _insert(*a, **k):
            calls.append(f"insert:{name}")
            return original_insert(*a, **k)

        q.update, q.insert = _update, _insert
        return q

    sb.table = _spy  # type: ignore[method-assign]
    r = _review(_client(sb), "verified")
    assert r.status_code == 200, r.text
    assert calls == []
    assert len(sb.db["admin_audit_logs"]) == 1


# ── errors and permissions ─────────────────────────────────────────────


def test_unknown_explanation_is_404():
    sb = _sb()
    r = _review(_client(sb), "verified", expl_id="99999999-9999-4999-8999-999999999999")
    assert r.status_code == 404, r.text


def test_concurrent_modification_is_409_without_audit():
    sb = _sb()

    class _Racing(_ExplRpcQuery):
        def execute(self):
            _stored(sb)["reviewer_status"] = "rejected"  # another reviewer won
            return super().execute()

    sb.rpc = lambda fn, params=None: _Racing(fn, params or {}, sb.db)  # type: ignore[method-assign]
    r = _review(_client(sb), "verified")
    assert r.status_code == 409, r.text
    assert sb.db["admin_audit_logs"] == []


def test_unexpected_rpc_error_is_500():
    sb = _sb()

    class _Broken(_ExplRpcQuery):
        def execute(self):
            raise Exception("connection reset by peer")

    sb.rpc = lambda fn, params=None: _Broken(fn, params or {}, sb.db)  # type: ignore[method-assign]
    r = _review(_client(sb), "verified")
    assert r.status_code == 500, r.text


def test_rpc_message_attribute_is_preferred_over_repr():
    # postgrest APIError carries the Postgres RAISE text on .message.
    sb = _sb()

    class _ApiError(Exception):
        def __init__(self, message):
            super().__init__({"code": "P0001", "message": message})
            self.message = message

    class _Raising(_ExplRpcQuery):
        def execute(self):
            raise _ApiError("verify_requires_final_answer: final_answer_option_id is null")

    sb.rpc = lambda fn, params=None: _Raising(fn, params or {}, sb.db)  # type: ignore[method-assign]
    r = _review(_client(sb), "verified")
    assert r.status_code == 422, r.text
    assert r.json()["detail"] == "verify_requires_final_answer: final_answer_option_id is null"


def test_cms_only_permission_is_403():
    sb = _sb()
    r = _review(_client(sb, _CMS_ONLY), "verified")
    assert r.status_code == 403, r.text
    assert _stored(sb)["reviewer_status"] == "pending"


def test_short_reason_is_422():
    sb = _sb()
    r = _review(_client(sb), "verified", reason="ok")
    assert r.status_code == 422, r.text
    assert sb.db.get("_rpc_calls") is None
