"""Admin coverage-derivation API tests.

Covers the single endpoint added to ``app.api.admin_exam_intelligence``:

    POST /admin/exam-intelligence/exams/{exam_id}/coverage/derive

Mirrors ``test_score_snapshot_admin_api.py``'s structure/fixtures/client
setup. Unlike the snapshot-compute endpoint, ``derive_topic_coverage`` is
stubbed out directly (monkeypatched on the router module) rather than
exercised end-to-end, since the 19 tests in ``test_coverage_derivation.py``
already cover ``derive_topic_coverage()`` itself in depth. This module only
proves the HTTP layer: permission gating, scope-error mapping, read-error
mapping, audit-call contract, and the happy path.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.api import admin_exam_intelligence as admin_api
from tests.exam_intelligence.test_admin_api import _build_app
from tests.persona_questions._stub import SBStub


def _seed():
    return {
        "exams": [
            {"id": "e1", "slug": "ssc-cgl", "name": "SSC CGL",
             "exam_type": "recruitment", "is_active": True},
        ],
    }


_DERIVE_BASE = "/api/admin/exam-intelligence/exams/e1/coverage/derive"


def _happy_result():
    return {
        "written": 3,
        "updated": 1,
        "skipped": 0,
        "triaged": 0,
        "no_row": 2,
        "errors": 0,
        "total_topics": 6,
        "read_error": False,
        "invalid_scope": False,
        "deltas": [],
        "triage": [],
    }


# ─── Permission gating ────────────────────────────────────────────────────
def test_derive_blocked_for_caller_without_manage_permission(monkeypatch):
    """role='admin' only carries exam_intelligence.review, not .manage."""
    monkeypatch.setattr(admin_api, "derive_topic_coverage", lambda *a, **k: _happy_result())
    sb = SBStub(_seed())
    client = TestClient(_build_app(sb, role="admin"))
    r = client.post(_DERIVE_BASE, json={"exam_phase_id": None})
    assert r.status_code == 403


def test_derive_blocked_for_plain_user(monkeypatch):
    monkeypatch.setattr(admin_api, "derive_topic_coverage", lambda *a, **k: _happy_result())
    sb = SBStub(_seed())
    client = TestClient(_build_app(sb, role="user"))
    r = client.post(_DERIVE_BASE, json={"exam_phase_id": None})
    assert r.status_code == 403


# ─── Invalid scope ────────────────────────────────────────────────────────
def test_derive_invalid_scope_returns_422(monkeypatch):
    def _fake(sb, exam_id, *, exam_phase_id=None):
        result = _happy_result()
        result["invalid_scope"] = True
        return result

    monkeypatch.setattr(admin_api, "derive_topic_coverage", _fake)
    sb = SBStub(_seed())
    client = TestClient(_build_app(sb))
    r = client.post(_DERIVE_BASE, json={"exam_phase_id": "invalid_scope"})
    assert r.status_code == 422


# ─── Read error ───────────────────────────────────────────────────────────
def test_derive_read_error_returns_502(monkeypatch):
    def _fake(sb, exam_id, *, exam_phase_id=None):
        result = _happy_result()
        result["read_error"] = True
        return result

    monkeypatch.setattr(admin_api, "derive_topic_coverage", _fake)
    sb = SBStub(_seed())
    client = TestClient(_build_app(sb))
    r = client.post(_DERIVE_BASE, json={"exam_phase_id": None})
    assert r.status_code == 502


# ─── Audit contract ───────────────────────────────────────────────────────
def test_derive_success_invokes_audit_with_derive_action(monkeypatch):
    monkeypatch.setattr(admin_api, "derive_topic_coverage", lambda *a, **k: _happy_result())

    calls: list[dict] = []

    def _fake_audit(supabase, actor, action, **kwargs):
        calls.append({"action": action, "kwargs": kwargs})
        return "audit-id-1"

    monkeypatch.setattr(admin_api, "_audit", _fake_audit)

    sb = SBStub(_seed())
    client = TestClient(_build_app(sb))
    r = client.post(_DERIVE_BASE, json={"exam_phase_id": None})
    assert r.status_code == 200
    assert len(calls) == 1
    assert calls[0]["action"] == "exam_topic_coverage.derive"
    assert calls[0]["kwargs"]["entity_type"] == "exam_topic_coverage"
    assert calls[0]["kwargs"]["entity_id"] == "e1"


# ─── Happy path ───────────────────────────────────────────────────────────
def test_derive_happy_path_returns_200_with_summary(monkeypatch):
    monkeypatch.setattr(admin_api, "derive_topic_coverage", lambda *a, **k: _happy_result())
    sb = SBStub(_seed())
    client = TestClient(_build_app(sb))
    r = client.post(_DERIVE_BASE, json={"exam_phase_id": None})
    assert r.status_code == 200
    body = r.json()
    assert body["exam_id"] == "e1"
    assert body["written"] == 3
    assert body["updated"] == 1
    assert "derivation_version" in body


# ─── P1-4 fix (checkpost): exam_phase_id is a REQUIRED key ─────────────────
# (its value may be null for explicit exam-wide) — no more implicit
# exam-wide default from an omitted/empty body.
def test_derive_empty_body_returns_422_missing_required_key(monkeypatch):
    monkeypatch.setattr(admin_api, "derive_topic_coverage", lambda *a, **k: _happy_result())
    sb = SBStub(_seed())
    client = TestClient(_build_app(sb))
    r = client.post(_DERIVE_BASE, json={})
    assert r.status_code == 422


def test_derive_explicit_null_exam_phase_id_succeeds_exam_wide(monkeypatch):
    calls: list[dict] = []

    def _fake(sb, exam_id, *, exam_phase_id=None):
        calls.append({"exam_id": exam_id, "exam_phase_id": exam_phase_id})
        return _happy_result()

    monkeypatch.setattr(admin_api, "derive_topic_coverage", _fake)
    sb = SBStub(_seed())
    client = TestClient(_build_app(sb))
    r = client.post(_DERIVE_BASE, json={"exam_phase_id": None})
    assert r.status_code == 200
    assert len(calls) == 1
    assert calls[0]["exam_phase_id"] is None
