"""Tests for the exam-cycle trust-gate endpoints (migration 261).

POST  /api/admin/exam-intelligence-cms/exam-cycles/{id}/review
POST  /api/admin/exam-intelligence-cms/exam-cycles           (create -> draft)
PATCH /api/admin/exam-intelligence-cms/exam-cycles/{id}       (material edit demotes)

``review_exam_cycle`` runs in Postgres under a row lock; CI has no live DB for
the endpoint path, so ``_CycleRpc`` mirrors the SQL gate exactly (reason ->
target status -> lock/CAS -> transition -> reviewer separation -> atomic audit +
stamp/clear). The real SQL is exercised end-to-end in
tests/exam_intelligence/test_exam_cycles_trust_gate_behaviour.py.
"""
from __future__ import annotations

import uuid as _uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intel_cms as cms_api
from app.core.auth import get_current_user
from tests.persona_questions._stub import SBStub, _Exec

EXAM = "11111111-1111-4111-8111-111111111111"
CYCLE = "22222222-2222-4222-8222-222222222222"
AUTHOR = "author-1"
REVIEWER = {"id": "rev-9", "email": "rev@example.com", "role": "admin",
            "permissions": [cms_api.PERM_REVIEW]}
CMS_ONLY = {"id": "c", "email": "c@x", "role": "admin",
            "permissions": [cms_api.PERM_CMS]}
_BASE = "/api/admin/exam-intelligence-cms"

_ALLOWED = {
    "draft": ("reviewed",),
    "reviewed": ("verified", "draft"),
    "verified": ("reviewed", "draft"),
}


class _CycleRpc:
    def __init__(self, params, db):
        self._p = params
        self._db = db

    def execute(self):
        p, db = self._p, self._db
        reason = p.get("p_reason")
        if reason is None or not (8 <= len(reason.strip()) <= 500):
            raise Exception("invalid_reason")
        if p["p_target_status"] not in ("draft", "reviewed", "verified"):
            raise Exception("invalid_target_status")

        cyc = next((c for c in db.get("exam_cycles", []) if c.get("id") == p["p_cycle_id"]), None)
        if cyc is None:
            raise Exception(f"not_found: exam_cycle {p['p_cycle_id']}")
        if cyc.get("reviewer_status") != p["p_expected_status"]:
            raise Exception("concurrent_modification")

        cur, tgt = cyc.get("reviewer_status"), p["p_target_status"]
        if tgt not in _ALLOWED.get(cur, ()):
            raise Exception(f"transition_not_allowed: {cur} -> {tgt}")

        if tgt == "verified":
            if cyc.get("created_by") is None:
                raise Exception("creator_missing")
            if str(cyc["created_by"]) == str(p["p_actor_id"]):
                raise Exception("reviewer_is_creator")

        audit_id = str(_uuid.uuid4())
        db.setdefault("admin_audit_logs", []).append({
            "id": audit_id, "actor_id": p["p_actor_id"], "actor_email": p["p_actor_email"],
            "action": "exam_intel.cms.cycle.review",
            "entity_type": "exam_cycle", "entity_id": p["p_cycle_id"],
            "new_value": {"from_status": p["p_expected_status"], "to_status": tgt},
            "notes": "admin_exam_intel_cms",
        })
        cyc["reviewer_status"] = tgt
        if tgt == "draft":
            cyc["reviewed_by"] = None
            cyc["reviewed_at"] = None
        else:
            cyc["reviewed_by"] = p["p_actor_id"]
            cyc["reviewed_at"] = "now"
        return _Exec({"ok": True, "audit_id": audit_id, "row": dict(cyc)})


class _CycleReviewSBStub(SBStub):
    def rpc(self, name, params=None):
        if name == "review_exam_cycle":
            return _CycleRpc(params or {}, self.db)
        return super().rpc(name, params)


def _world(*, status="draft", created_by=AUTHOR, extra=None):
    cyc = {"id": CYCLE, "exam_id": EXAM, "year": 2026, "cycle_name": "2026",
           "status": "open", "exam_start": "2026-09-01", "reviewer_status": status,
           "reviewed_by": None, "reviewed_at": None, "created_by": created_by}
    if extra:
        cyc.update(extra)
    return {"exam_cycles": [cyc], "exams": [{"id": EXAM}], "admin_audit_logs": []}


def _client(sb, user=REVIEWER):
    app = FastAPI()
    app.include_router(cms_api.router, prefix="/api")
    cms_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[cms_api._flag_enabled] = lambda: None
    if user is not None:
        app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app, raise_server_exceptions=False)


def _review(client, status, reason="reviewed against the official notification"):
    return client.post(f"{_BASE}/exam-cycles/{CYCLE}/review",
                       json={"status": status, "reason": reason})


# ── review endpoint ─────────────────────────────────────────────────────────


def test_two_step_promotion_stamps_reviewer():
    sb = _CycleReviewSBStub(_world(status="draft"))
    client = _client(sb)
    assert _review(client, "reviewed").status_code == 200
    assert sb.db["exam_cycles"][0]["reviewer_status"] == "reviewed"
    r = _review(client, "verified")
    assert r.status_code == 200, r.text
    row = r.json()["row"]
    assert row["reviewer_status"] == "verified"
    assert row["reviewed_by"] == "rev-9"
    assert row["reviewed_at"]
    assert len(sb.db["admin_audit_logs"]) == 2


def test_draft_cannot_jump_to_verified():
    sb = _CycleReviewSBStub(_world(status="draft"))
    r = _review(_client(sb), "verified")
    assert r.status_code == 422, r.text
    assert "not allowed" in r.text.lower()
    assert len(sb.db["admin_audit_logs"]) == 0


def test_creator_cannot_verify_own_cycle():
    sb = _CycleReviewSBStub(_world(status="reviewed", created_by=REVIEWER["id"]))
    r = _review(_client(sb), "verified")
    assert r.status_code == 422, r.text
    assert "reviewer_is_creator" in r.text
    assert sb.db["exam_cycles"][0]["reviewer_status"] == "reviewed"


def test_missing_creator_fails_closed():
    sb = _CycleReviewSBStub(_world(status="reviewed", created_by=None))
    r = _review(_client(sb), "verified")
    assert r.status_code == 422, r.text
    assert "creator_missing" in r.text


def test_demote_to_draft_clears_stamp():
    sb = _CycleReviewSBStub(_world(status="verified",
                                   extra={"reviewed_by": "rev-9", "reviewed_at": "now"}))
    r = _review(_client(sb), "draft", reason="reopening cycle for re-review")
    assert r.status_code == 200, r.text
    row = sb.db["exam_cycles"][0]
    assert row["reviewer_status"] == "draft"
    assert row["reviewed_by"] is None
    assert row["reviewed_at"] is None


def test_stale_expected_status_is_409():
    # existing status is draft; the endpoint reads it and calls with expected=draft
    # → target 'reviewed' is valid; to force a CAS miss we mutate between read and
    # RPC by pre-setting an incompatible status the endpoint won't expect.
    sb = _CycleReviewSBStub(_world(status="reviewed"))

    # Endpoint reads reviewer_status='reviewed' and sends expected='reviewed';
    # simulate a concurrent change by flipping the row before the RPC executes.
    orig_rpc = sb.rpc

    def _racing_rpc(name, params=None):
        sb.db["exam_cycles"][0]["reviewer_status"] = "draft"
        return orig_rpc(name, params)

    sb.rpc = _racing_rpc  # type: ignore[assignment]
    r = _review(_client(sb), "verified")
    assert r.status_code == 409, r.text


def test_short_reason_is_422():
    sb = _CycleReviewSBStub(_world(status="draft"))
    r = _review(_client(sb), "reviewed", reason="short")
    assert r.status_code == 422, r.text


def test_unknown_cycle_is_404():
    sb = _CycleReviewSBStub(_world(status="draft"))
    r = _client(sb).post(
        f"{_BASE}/exam-cycles/99999999-9999-4999-8999-999999999999/review",
        json={"status": "reviewed", "reason": "review a nonexistent cycle"},
    )
    assert r.status_code == 404, r.text


def test_cms_only_permission_is_403():
    sb = _CycleReviewSBStub(_world(status="draft"))
    r = _review(_client(sb, CMS_ONLY), "reviewed")
    assert r.status_code == 403, r.text


def test_disallowed_target_status_is_422():
    sb = _CycleReviewSBStub(_world(status="draft"))
    r = _review(_client(sb), "bogus")
    assert r.status_code == 422, r.text


# ── create lands draft + stamps author ──────────────────────────────────────


def test_create_cycle_lands_draft_and_records_author():
    sb = _CycleReviewSBStub({"exam_cycles": [], "exams": [{"id": EXAM}], "admin_audit_logs": []})
    r = _client(sb, {**REVIEWER, "permissions": [cms_api.PERM_CMS]}).post(
        f"{_BASE}/exam-cycles",
        json={"reason": "author the 2026 cycle draft",
              "payload": {"exam_id": EXAM, "year": 2026, "cycle_name": "2026"}},
    )
    assert r.status_code == 200, r.text
    row = sb.db["exam_cycles"][0]
    # reviewer_status is a DB default (not a client field) → never client-set here;
    # created_by is stamped for reviewer separation at verify time.
    assert "reviewer_status" not in row or row.get("reviewer_status") in (None, "draft")
    assert row["created_by"] == REVIEWER["id"]


# ── material edit on a reviewed/verified cycle demotes it ───────────────────


def test_material_edit_of_verified_cycle_demotes_to_draft():
    sb = _CycleReviewSBStub(_world(status="verified",
                                   extra={"reviewed_by": "rev-9", "reviewed_at": "now"}))
    r = _client(sb, {**REVIEWER, "permissions": [cms_api.PERM_CMS]}).patch(
        f"{_BASE}/exam-cycles/{CYCLE}",
        json={"reason": "correct the exam_start date",
              "payload": {"exam_start": "2026-10-01"}},
    )
    assert r.status_code == 200, r.text
    row = sb.db["exam_cycles"][0]
    assert row["reviewer_status"] == "draft"
    assert row["reviewed_by"] is None
    assert row["exam_start"] == "2026-10-01"


def test_material_edit_of_reviewed_cycle_demotes_to_draft():
    sb = _CycleReviewSBStub(_world(status="reviewed",
                                   extra={"reviewed_by": "rev-9", "reviewed_at": "now"}))
    r = _client(sb, {**REVIEWER, "permissions": [cms_api.PERM_CMS]}).patch(
        f"{_BASE}/exam-cycles/{CYCLE}",
        json={"reason": "replace reviewed source provenance",
              "payload": {"source_url": "https://official.example/corrigendum.pdf"}},
    )
    assert r.status_code == 200, r.text
    row = sb.db["exam_cycles"][0]
    assert row["reviewer_status"] == "draft"
    assert row["reviewed_by"] is None
    assert row["reviewed_at"] is None


def test_metadata_edit_of_verified_cycle_demotes_to_draft():
    sb = _CycleReviewSBStub(_world(status="verified",
                                   extra={"reviewed_by": "rev-9", "reviewed_at": "now"}))
    r = _client(sb, {**REVIEWER, "permissions": [cms_api.PERM_CMS]}).patch(
        f"{_BASE}/exam-cycles/{CYCLE}",
        json={"reason": "correct reviewed cycle metadata",
              "payload": {"metadata": {"tier": "national"}}},
    )
    assert r.status_code == 200, r.text
    assert sb.db["exam_cycles"][0]["reviewer_status"] == "draft"


def test_non_material_edit_of_verified_cycle_keeps_verified():
    sb = _CycleReviewSBStub(_world(status="verified",
                                   extra={"reviewed_by": "rev-9", "reviewed_at": "now"}))
    r = _client(sb, {**REVIEWER, "permissions": [cms_api.PERM_CMS]}).patch(
        f"{_BASE}/exam-cycles/{CYCLE}",
        json={"reason": "advance operational status to active",
              "payload": {"status": "active"}},
    )
    assert r.status_code == 200, r.text
    assert sb.db["exam_cycles"][0]["reviewer_status"] == "verified"
