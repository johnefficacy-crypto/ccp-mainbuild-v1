"""PYQ Intelligence v2 PR-3 — admin CMS + review API for stimuli and links.

Covers the migration-223 surfaces added in this PR:
  - CMS list/create/patch/delete for pyq_stimuli (allowlist enforcement:
    reviewer_status is never curatable; pyq_paper_id is not reparentable).
  - CMS create/list for pyq_question_stimuli links (>=1 filter required).
  - The two new review kinds routed through the generic review_item path:
    PATCH /items/pyq_stimulus/{id}/review and
    PATCH /items/pyq_question_stimulus/{id}/review.
  - Permission separation: PERM_CMS vs PERM_REVIEW.

Harness mirrors test_cms_pyq_paper_review.py / test_review_cascade.py
(TaxSBStub + FastAPI() + TestClient + dependency overrides).
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intel_cms as cms_api
from app.api import admin_exam_intelligence as admin_api
from app.core.auth import get_current_user
from tests.exam_intelligence.test_cms_taxonomy import TaxSBStub

_CMS_BASE = "/api/admin/exam-intelligence-cms"
_REVIEW_BASE = "/api/admin/exam-intelligence"

_CMS_ACTOR = {"id": "cms-1", "email": "cms@example.com", "role": "admin", "permissions": [cms_api.PERM_CMS]}
_REVIEW_ACTOR = {"id": "rev-1", "email": "rev@example.com", "role": "admin", "permissions": [admin_api.ADMIN_PERM]}


def _cms_client(sb, user=_CMS_ACTOR):
    app = FastAPI()
    app.include_router(cms_api.router, prefix="/api")
    cms_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[cms_api._flag_enabled] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app, raise_server_exceptions=False)


def _review_client(sb, user=_REVIEW_ACTOR):
    app = FastAPI()
    app.include_router(admin_api.router, prefix="/api")
    admin_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app, raise_server_exceptions=False)


def _seed():
    return {
        "pyq_papers": [{"id": "paper-1", "exam_id": "e1", "exam_phase_id": "ph1"}],
        "pyq_questions": [{"id": "q-1", "pyq_paper_id": "paper-1", "reviewer_status": "pending"}],
        "pyq_stimuli": [
            {"id": "st-1", "pyq_paper_id": "paper-1", "section_id": None,
             "stimulus_type": "passage", "content_text": "A shared passage.",
             "language": "en", "display_order": 1, "reviewer_status": "pending",
             "reviewed_by": None, "reviewed_at": None, "metadata": {},
             "created_at": "2026-07-01T00:00:00Z"},
        ],
        "pyq_question_stimuli": [
            {"id": "lnk-1", "question_id": "q-1", "stimulus_id": "st-1",
             "display_order": 1, "reviewer_status": "pending",
             "reviewed_by": None, "reviewed_at": None,
             "created_at": "2026-07-01T00:00:00Z"},
        ],
        "admin_audit_logs": [],
    }


# ── pyq_stimuli: list ──────────────────────────────────────────────────

def test_list_pyq_stimuli_by_paper():
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).get(f"{_CMS_BASE}/pyq-stimuli?pyq_paper_id=paper-1")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == "st-1"
    assert {"limit", "offset"} <= set(body)


def test_list_pyq_stimuli_reviewer_status_filter():
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).get(f"{_CMS_BASE}/pyq-stimuli?pyq_paper_id=paper-1&reviewer_status=verified")
    assert r.status_code == 200, r.text
    assert r.json()["total"] == 0


# ── pyq_stimuli: create ────────────────────────────────────────────────

def test_create_pyq_stimulus_persists_and_audits():
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).post(
        f"{_CMS_BASE}/pyq-stimuli",
        json={"reason": "adding a shared passage", "payload": {
            "pyq_paper_id": "paper-1", "stimulus_type": "caselet",
            "content_text": "New caselet body.", "display_order": 2}},
    )
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True
    row = next(s for s in sb.db["pyq_stimuli"] if s.get("content_text") == "New caselet body.")
    assert row["stimulus_type"] == "caselet"
    assert len(sb.db["admin_audit_logs"]) == 1
    assert sb.db["admin_audit_logs"][0]["action"] == "exam_intel.cms.pyq_stimulus.create"


def test_create_pyq_stimulus_ignores_reviewer_status_in_payload():
    """reviewer_status is not in _STIMULUS_FIELDS — an attempt to seed a
    verified stimulus through create must be stripped (DB default 'pending')."""
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).post(
        f"{_CMS_BASE}/pyq-stimuli",
        json={"reason": "attempting to self-verify", "payload": {
            "pyq_paper_id": "paper-1", "content_text": "sneaky",
            "reviewer_status": "verified"}},
    )
    assert r.status_code == 200, r.text
    row = next(s for s in sb.db["pyq_stimuli"] if s.get("content_text") == "sneaky")
    assert "reviewer_status" not in row, "reviewer_status must not be settable via create"


def test_create_pyq_stimulus_requires_paper():
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).post(
        f"{_CMS_BASE}/pyq-stimuli",
        json={"reason": "missing the paper id", "payload": {"content_text": "x"}},
    )
    assert r.status_code == 422, r.text


def test_create_pyq_stimulus_bad_type_422():
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).post(
        f"{_CMS_BASE}/pyq-stimuli",
        json={"reason": "bad stimulus type value", "payload": {
            "pyq_paper_id": "paper-1", "stimulus_type": "nonsense"}},
    )
    assert r.status_code == 422, r.text


# ── pyq_stimuli: patch ─────────────────────────────────────────────────

def test_patch_pyq_stimulus_display_order():
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).patch(
        f"{_CMS_BASE}/pyq-stimuli/st-1",
        json={"reason": "reordering the stimulus", "payload": {"display_order": 5}},
    )
    assert r.status_code == 200, r.text
    assert next(s for s in sb.db["pyq_stimuli"] if s["id"] == "st-1")["display_order"] == 5


def test_patch_pyq_stimulus_reviewer_status_rejected():
    """reviewer_status is not curatable — payload with only reviewer_status
    has no allowed fields → 422; the row is unchanged."""
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).patch(
        f"{_CMS_BASE}/pyq-stimuli/st-1",
        json={"reason": "trying to verify via curate", "payload": {"reviewer_status": "verified"}},
    )
    assert r.status_code == 422, r.text
    assert next(s for s in sb.db["pyq_stimuli"] if s["id"] == "st-1")["reviewer_status"] == "pending"


def test_patch_pyq_stimulus_pyq_paper_id_not_reparentable():
    """pyq_paper_id is excluded from the curate allowlist — a payload with
    only pyq_paper_id has no allowed fields → 422."""
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).patch(
        f"{_CMS_BASE}/pyq-stimuli/st-1",
        json={"reason": "attempt to reparent paper", "payload": {"pyq_paper_id": "paper-2"}},
    )
    assert r.status_code == 422, r.text
    assert next(s for s in sb.db["pyq_stimuli"] if s["id"] == "st-1")["pyq_paper_id"] == "paper-1"


def test_patch_pyq_stimulus_unknown_stimulus_404():
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).patch(
        f"{_CMS_BASE}/pyq-stimuli/nope",
        json={"reason": "no such stimulus row", "payload": {"display_order": 3}},
    )
    assert r.status_code == 404, r.text


# ── pyq_stimuli: delete ────────────────────────────────────────────────

def test_delete_pyq_stimulus():
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).delete(f"{_CMS_BASE}/pyq-stimuli/st-1")
    assert r.status_code == 200, r.text
    assert all(s["id"] != "st-1" for s in sb.db["pyq_stimuli"])
    assert any(a["action"] == "exam_intel.cms.pyq_stimulus.delete" for a in sb.db["admin_audit_logs"])


# ── pyq_question_stimuli: links ────────────────────────────────────────

def test_list_question_stimuli_requires_a_filter():
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).get(f"{_CMS_BASE}/pyq-question-stimuli")
    assert r.status_code == 422, r.text


def test_list_question_stimuli_by_question():
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).get(f"{_CMS_BASE}/pyq-question-stimuli?question_id=q-1")
    assert r.status_code == 200, r.text
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["id"] == "lnk-1"


def test_create_question_stimulus_link():
    seed = _seed()
    seed["pyq_stimuli"].append({
        "id": "st-2", "pyq_paper_id": "paper-1", "section_id": None,
        "stimulus_type": "chart", "content_text": None, "language": "en",
        "display_order": 2, "reviewer_status": "pending", "reviewed_by": None,
        "reviewed_at": None, "metadata": {}, "created_at": "2026-07-01T00:00:00Z",
    })
    sb = TaxSBStub(seed)
    r = _cms_client(sb).post(
        f"{_CMS_BASE}/pyq-question-stimuli",
        json={"reason": "linking question to chart", "payload": {
            "question_id": "q-1", "stimulus_id": "st-2", "display_order": 2}},
    )
    assert r.status_code == 200, r.text
    assert any(l.get("stimulus_id") == "st-2" for l in sb.db["pyq_question_stimuli"])
    assert any(a["action"] == "exam_intel.cms.pyq_question_stimulus.create" for a in sb.db["admin_audit_logs"])


def test_create_link_requires_both_ids():
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).post(
        f"{_CMS_BASE}/pyq-question-stimuli",
        json={"reason": "missing the stimulus id", "payload": {"question_id": "q-1"}},
    )
    assert r.status_code == 422, r.text


def test_patch_link_display_order_only():
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).patch(
        f"{_CMS_BASE}/pyq-question-stimuli/lnk-1",
        json={"reason": "reordering the link", "payload": {"display_order": 9}},
    )
    assert r.status_code == 200, r.text
    assert next(l for l in sb.db["pyq_question_stimuli"] if l["id"] == "lnk-1")["display_order"] == 9


def test_patch_link_reviewer_status_rejected():
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).patch(
        f"{_CMS_BASE}/pyq-question-stimuli/lnk-1",
        json={"reason": "trying to verify the link", "payload": {"reviewer_status": "verified"}},
    )
    assert r.status_code == 422, r.text
    assert next(l for l in sb.db["pyq_question_stimuli"] if l["id"] == "lnk-1")["reviewer_status"] == "pending"


def test_delete_question_stimulus_link():
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).delete(f"{_CMS_BASE}/pyq-question-stimuli/lnk-1")
    assert r.status_code == 200, r.text
    assert all(l["id"] != "lnk-1" for l in sb.db["pyq_question_stimuli"])


# ── review kinds (generic review_item path) ────────────────────────────

def test_review_pyq_stimulus_sets_reviewer_columns():
    sb = TaxSBStub(_seed())
    r = _review_client(sb).patch(
        f"{_REVIEW_BASE}/items/pyq_stimulus/st-1/review",
        json={"reviewer_status": "verified"},
    )
    assert r.status_code == 200, r.text
    row = next(s for s in sb.db["pyq_stimuli"] if s["id"] == "st-1")
    assert row["reviewer_status"] == "verified"
    assert row["reviewed_by"] == "rev-1"
    assert row["reviewed_at"] is not None


def test_review_pyq_question_stimulus_link_sets_reviewer_columns():
    sb = TaxSBStub(_seed())
    r = _review_client(sb).patch(
        f"{_REVIEW_BASE}/items/pyq_question_stimulus/lnk-1/review",
        json={"reviewer_status": "verified"},
    )
    assert r.status_code == 200, r.text
    row = next(l for l in sb.db["pyq_question_stimuli"] if l["id"] == "lnk-1")
    assert row["reviewer_status"] == "verified"
    assert row["reviewed_by"] == "rev-1"


def test_review_unknown_stimulus_returns_404():
    sb = TaxSBStub(_seed())
    r = _review_client(sb).patch(
        f"{_REVIEW_BASE}/items/pyq_stimulus/no-such/review",
        json={"reviewer_status": "verified"},
    )
    assert r.status_code == 404, r.text


# ── permission separation ──────────────────────────────────────────────

def test_cms_endpoint_rejects_review_only_actor():
    sb = TaxSBStub(_seed())
    r = _cms_client(sb, user=_REVIEW_ACTOR).get(f"{_CMS_BASE}/pyq-stimuli?pyq_paper_id=paper-1")
    assert r.status_code == 403, r.text


def test_review_endpoint_rejects_cms_only_actor():
    sb = TaxSBStub(_seed())
    r = _review_client(sb, user=_CMS_ACTOR).patch(
        f"{_REVIEW_BASE}/items/pyq_stimulus/st-1/review",
        json={"reviewer_status": "verified"},
    )
    assert r.status_code == 403, r.text
