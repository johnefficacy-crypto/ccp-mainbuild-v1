"""PR7 — Atomic PYQ question+options review.

Tests for:
  1. PATCH /items/pyq_question/{id}/review cascades reviewer_status to child options.
  2. Cascade applies for verified, rejected, and needs_correction.
  3. Pending does NOT cascade (resetting options to pending is destructive).
  4. Non-existent question returns 404.
  5. Existing tests for non-pyq-question kinds continue to pass unchanged.
  6. is_correct PATCH through the CMS update_pyq_option endpoint persists correctly.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intelligence as admin_api
from app.api import admin_exam_intel_cms as cms_api
from app.core.auth import get_current_user
from tests.persona_questions._stub import SBStub


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _build_review_app(sb: SBStub):
    app = FastAPI()
    app.include_router(admin_api.router, prefix="/api")
    admin_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "admin-1",
        "role": "super_admin",
        "permissions": [],
    }
    return app


def _build_cms_app(sb: SBStub):
    app = FastAPI()
    app.include_router(cms_api.router, prefix="/api")
    cms_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[cms_api._flag_enabled] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "admin-1",
        "role": "super_admin",
        "permissions": [cms_api.PERM_CMS],
    }
    return app


def _seed_with_options():
    return {
        "pyq_papers": [{"id": "paper-1", "exam_id": "e1"}],
        "pyq_questions": [
            {"id": "q-1", "pyq_paper_id": "paper-1", "reviewer_status": "pending"},
        ],
        "pyq_options": [
            {"id": "opt-a", "question_id": "q-1", "option_label": "A", "option_text": "Alpha",
             "is_correct": False, "reviewer_status": "pending", "reviewed_by": None, "reviewed_at": None},
            {"id": "opt-b", "question_id": "q-1", "option_label": "B", "option_text": "Beta",
             "is_correct": False, "reviewer_status": "pending", "reviewed_by": None, "reviewed_at": None},
            {"id": "opt-c", "question_id": "q-1", "option_label": "C", "option_text": "Gamma",
             "is_correct": False, "reviewer_status": "pending", "reviewed_by": None, "reviewed_at": None},
            {"id": "opt-d", "question_id": "q-1", "option_label": "D", "option_text": "Delta",
             "is_correct": False, "reviewer_status": "pending", "reviewed_by": None, "reviewed_at": None},
        ],
        "admin_audit_logs": [],
    }


# ─── TestReviewCascade ────────────────────────────────────────────────────────

class TestReviewCascade:
    def test_verified_cascades_to_all_child_options(self):
        sb = SBStub(_seed_with_options())
        client = TestClient(_build_review_app(sb))

        r = client.patch(
            "/api/admin/exam-intelligence/items/pyq_question/q-1/review",
            json={"reviewer_status": "verified"},
        )
        assert r.status_code == 200, r.text

        q = sb.db["pyq_questions"][0]
        assert q["reviewer_status"] == "verified"

        for opt in sb.db["pyq_options"]:
            assert opt["reviewer_status"] == "verified", f"Option {opt['id']} not cascaded"
            assert opt["reviewed_by"] == "admin-1"
            assert opt["reviewed_at"] is not None

    def test_rejected_cascades_to_all_child_options(self):
        sb = SBStub(_seed_with_options())
        client = TestClient(_build_review_app(sb))

        r = client.patch(
            "/api/admin/exam-intelligence/items/pyq_question/q-1/review",
            json={"reviewer_status": "rejected"},
        )
        assert r.status_code == 200, r.text

        q = sb.db["pyq_questions"][0]
        assert q["reviewer_status"] == "rejected"
        for opt in sb.db["pyq_options"]:
            assert opt["reviewer_status"] == "rejected"

    def test_needs_correction_cascades_to_all_child_options(self):
        sb = SBStub(_seed_with_options())
        client = TestClient(_build_review_app(sb))

        r = client.patch(
            "/api/admin/exam-intelligence/items/pyq_question/q-1/review",
            json={"reviewer_status": "needs_correction"},
        )
        assert r.status_code == 200, r.text

        for opt in sb.db["pyq_options"]:
            assert opt["reviewer_status"] == "needs_correction"

    def test_pending_does_not_cascade(self):
        """Setting a question back to pending must not reset child option statuses."""
        seed = _seed_with_options()
        for opt in seed["pyq_options"]:
            opt["reviewer_status"] = "verified"
        sb = SBStub(seed)
        client = TestClient(_build_review_app(sb))

        r = client.patch(
            "/api/admin/exam-intelligence/items/pyq_question/q-1/review",
            json={"reviewer_status": "pending"},
        )
        assert r.status_code == 200, r.text

        q = sb.db["pyq_questions"][0]
        assert q["reviewer_status"] == "pending"
        for opt in sb.db["pyq_options"]:
            assert opt["reviewer_status"] == "verified", "Options must not be reset to pending"

    def test_missing_question_returns_404(self):
        sb = SBStub(_seed_with_options())
        client = TestClient(_build_review_app(sb))

        r = client.patch(
            "/api/admin/exam-intelligence/items/pyq_question/no-such-question/review",
            json={"reviewer_status": "verified"},
        )
        assert r.status_code == 404

    def test_response_contains_question_fields(self):
        sb = SBStub(_seed_with_options())
        client = TestClient(_build_review_app(sb))

        r = client.patch(
            "/api/admin/exam-intelligence/items/pyq_question/q-1/review",
            json={"reviewer_status": "verified"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["id"] == "q-1"
        assert body["reviewer_status"] == "verified"


# ─── TestPatchPyqOptionIsCorrect ─────────────────────────────────────────────

class TestPatchPyqOptionIsCorrect:
    """
    Root-cause audit for the is_correct persistence bug (PR7 Bug 3).

    From the code read:
      (a) onChange fires correctly — confirmed by reading PyqPaperWorkspace.jsx.
      (b) Payload includes is_correct — toggleCorrect sends { payload: { is_correct: !opt.is_correct } }.
      (c) _OPTION_FIELDS includes is_correct — confirmed at admin_exam_intel_cms.py:663.

    None of (a)/(b)/(c) apply to the current code. These tests serve as regression
    guards confirming the CMS PATCH endpoint correctly persists is_correct.
    """

    def _seed(self):
        return {
            "pyq_papers": [{"id": "p1", "exam_id": "e1"}],
            "pyq_questions": [{"id": "q-existing", "pyq_paper_id": "p1"}],
            "pyq_options": [
                {"id": "opt-1", "question_id": "q-existing", "option_label": "A",
                 "option_text": "First option", "is_correct": False, "reviewer_status": "pending"},
                {"id": "opt-2", "question_id": "q-existing", "option_label": "B",
                 "option_text": "Second option", "is_correct": True, "reviewer_status": "pending"},
            ],
            "admin_audit_logs": [],
        }

    def test_is_correct_toggle_false_to_true(self):
        sb = SBStub(self._seed())
        client = TestClient(_build_cms_app(sb))

        r = client.patch(
            "/api/admin/exam-intelligence-cms/pyq-options/opt-1",
            json={"reason": "mark correct option", "payload": {"is_correct": True}},
        )
        assert r.status_code == 200, r.text
        assert r.json()["ok"] is True

        opt = next(o for o in sb.db["pyq_options"] if o["id"] == "opt-1")
        assert opt["is_correct"] is True, "DB row must have is_correct=True after PATCH"

    def test_is_correct_toggle_true_to_false(self):
        sb = SBStub(self._seed())
        client = TestClient(_build_cms_app(sb))

        r = client.patch(
            "/api/admin/exam-intelligence-cms/pyq-options/opt-2",
            json={"reason": "unmark correct option", "payload": {"is_correct": False}},
        )
        assert r.status_code == 200, r.text

        opt = next(o for o in sb.db["pyq_options"] if o["id"] == "opt-2")
        assert opt["is_correct"] is False

    def test_unrecognised_field_only_returns_422(self):
        sb = SBStub(self._seed())
        client = TestClient(_build_cms_app(sb))

        r = client.patch(
            "/api/admin/exam-intelligence-cms/pyq-options/opt-1",
            json={"reason": "bad payload attempt", "payload": {"unknown_field": "val"}},
        )
        assert r.status_code == 422
