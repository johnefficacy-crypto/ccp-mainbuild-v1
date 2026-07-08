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
from tests.exam_intelligence.test_cms_taxonomy import TaxSBStub, _TaxQuery

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
    r = _cms_client(sb).delete(f"{_CMS_BASE}/pyq-stimuli/st-1?reason=obsolete shared passage")
    assert r.status_code == 200, r.text
    assert all(s["id"] != "st-1" for s in sb.db["pyq_stimuli"])
    audit = next(a for a in sb.db["admin_audit_logs"] if a["action"] == "exam_intel.cms.pyq_stimulus.delete")
    assert audit["new_value"]["reason"] == "obsolete shared passage"
    assert audit["new_value"]["cascade_deleted_link_count"] == 1


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
    r = _cms_client(sb).delete(f"{_CMS_BASE}/pyq-question-stimuli/lnk-1?reason=wrong association")
    assert r.status_code == 200, r.text
    assert all(l["id"] != "lnk-1" for l in sb.db["pyq_question_stimuli"])
    audit = next(a for a in sb.db["admin_audit_logs"] if a["action"] == "exam_intel.cms.pyq_question_stimulus.delete")
    assert audit["new_value"]["reason"] == "wrong association"
    assert audit["new_value"]["question_id"] == "q-1"


# ── fix #3: destructive-delete guards (reason + verified-question integrity) ──

def test_delete_stimulus_without_reason_422():
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).delete(f"{_CMS_BASE}/pyq-stimuli/st-1")
    assert r.status_code == 422, r.text
    assert any(s["id"] == "st-1" for s in sb.db["pyq_stimuli"]), "row must survive a rejected delete"


def test_delete_link_without_reason_422():
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).delete(f"{_CMS_BASE}/pyq-question-stimuli/lnk-1")
    assert r.status_code == 422, r.text
    assert any(l["id"] == "lnk-1" for l in sb.db["pyq_question_stimuli"])


def test_delete_link_blocked_when_question_verified_409():
    seed = _seed()
    seed["pyq_questions"][0]["reviewer_status"] = "verified"
    sb = TaxSBStub(seed)
    r = _cms_client(sb).delete(f"{_CMS_BASE}/pyq-question-stimuli/lnk-1?reason=trying to drop verified link")
    assert r.status_code == 409, r.text
    assert "verified" in str(r.json()["detail"]).lower()
    assert any(l["id"] == "lnk-1" for l in sb.db["pyq_question_stimuli"]), "nothing deleted"


def test_delete_link_allowed_when_question_needs_correction():
    seed = _seed()
    seed["pyq_questions"][0]["reviewer_status"] = "needs_correction"
    sb = TaxSBStub(seed)
    r = _cms_client(sb).delete(f"{_CMS_BASE}/pyq-question-stimuli/lnk-1?reason=cleanup after demotion")
    assert r.status_code == 200, r.text
    assert all(l["id"] != "lnk-1" for l in sb.db["pyq_question_stimuli"])


def test_delete_stimulus_blocked_when_linked_question_verified_409():
    seed = _seed()
    seed["pyq_questions"][0]["reviewer_status"] = "verified"
    sb = TaxSBStub(seed)
    r = _cms_client(sb).delete(f"{_CMS_BASE}/pyq-stimuli/st-1?reason=trying to drop live passage")
    assert r.status_code == 409, r.text
    assert "1" in str(r.json()["detail"])
    assert any(s["id"] == "st-1" for s in sb.db["pyq_stimuli"]), "nothing deleted"


def test_delete_stimulus_allowed_when_no_verified_linked_question():
    seed = _seed()
    seed["pyq_questions"][0]["reviewer_status"] = "rejected"
    sb = TaxSBStub(seed)
    r = _cms_client(sb).delete(f"{_CMS_BASE}/pyq-stimuli/st-1?reason=safe to remove passage")
    assert r.status_code == 200, r.text
    assert all(s["id"] != "st-1" for s in sb.db["pyq_stimuli"])


# ── PR-11 slice 1: media stimulus authoring (migration 233) ──────────────────

def test_create_image_stimulus_persists_media_fields():
    """image/chart/diagram are now creatable; the media fields (document_asset_id,
    asset_locator, alt_text) pass through to the row. DB integrity (asset must be
    a live admin image; verify needs alt_text + asset) is enforced by migration
    233's guard, not this layer."""
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).post(
        f"{_CMS_BASE}/pyq-stimuli",
        json={"reason": "adding a Venn-diagram image", "payload": {
            "pyq_paper_id": "paper-1", "stimulus_type": "image",
            "document_asset_id": "asset-1", "alt_text": "A Venn diagram of three sets",
            "asset_locator": {"page_number": 4, "bbox": [10, 20, 30, 40]},
            "display_order": 3}},
    )
    assert r.status_code == 200, r.text
    row = next(s for s in sb.db["pyq_stimuli"] if s.get("stimulus_type") == "image")
    assert row["document_asset_id"] == "asset-1"
    assert row["alt_text"] == "A Venn diagram of three sets"
    assert row["asset_locator"] == {"page_number": 4, "bbox": [10, 20, 30, 40]}
    assert sb.db["admin_audit_logs"][-1]["action"] == "exam_intel.cms.pyq_stimulus.create"


def test_patch_stimulus_to_media_type_allowed():
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).patch(
        f"{_CMS_BASE}/pyq-stimuli/st-1",
        json={"reason": "switching to a diagram", "payload": {
            "stimulus_type": "diagram", "alt_text": "flowchart"}},
    )
    assert r.status_code == 200, r.text
    row = next(s for s in sb.db["pyq_stimuli"] if s["id"] == "st-1")
    assert row["stimulus_type"] == "diagram"
    assert row["alt_text"] == "flowchart"


def test_create_stimulus_other_type_still_422():
    """'other' has no authoring contract yet and stays deferred."""
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).post(
        f"{_CMS_BASE}/pyq-stimuli",
        json={"reason": "attempting an other stimulus", "payload": {
            "pyq_paper_id": "paper-1", "stimulus_type": "other", "content_text": "x"}},
    )
    assert r.status_code == 422, r.text
    assert all(s.get("stimulus_type") != "other" for s in sb.db["pyq_stimuli"])


def test_create_media_stimulus_db_guard_maps_to_422():
    """A DB media-guard rejection (e.g. non-image asset) surfaces as 422, not 500."""
    class _GuardStub(TaxSBStub):
        def table(self, name):
            if name == "pyq_stimuli":
                raise RuntimeError(
                    "pyq_stimuli.document_asset_id asset-x has document_kind pyq_paper "
                    "(media stimuli require an image asset)"
                )
            return super().table(name)

    sb = _GuardStub(_seed())
    r = _cms_client(sb).post(
        f"{_CMS_BASE}/pyq-stimuli",
        json={"reason": "wrong-kind asset", "payload": {
            "pyq_paper_id": "paper-1", "stimulus_type": "chart",
            "document_asset_id": "asset-x", "alt_text": "bar chart"}},
    )
    assert r.status_code == 422, r.text
    assert "document_kind" in str(r.json()["detail"])


def test_create_stimulus_text_types_allowed():
    sb = TaxSBStub(_seed())
    for t in ("passage", "caselet", "table"):
        r = _cms_client(sb).post(
            f"{_CMS_BASE}/pyq-stimuli",
            json={"reason": f"adding a {t} stimulus", "payload": {
                "pyq_paper_id": "paper-1", "stimulus_type": t, "content_text": f"{t} body"}},
        )
        assert r.status_code == 200, r.text


# ── fix #5: unique / check violations map to 409 / 422, not 500 ───────────────

class _ConstraintErr(Exception):
    """APIError-shaped: carries a SQLSTATE .code like postgrest.exceptions.APIError."""
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class _ConstraintQuery(_TaxQuery):
    def __init__(self, name, db, *, fail_table, code, message):
        super().__init__(name, db)
        self._fail_table = fail_table
        self._code = code
        self._message = message

    def execute(self):
        if (
            (self._pending_insert is not None or self._pending_update not in (None, "__delete__"))
            and self.name == self._fail_table
        ):
            raise _ConstraintErr(self._code, self._message)
        return super().execute()


class _ConstraintSBStub(TaxSBStub):
    def __init__(self, db, *, fail_table, code, message):
        super().__init__(db)
        self._fail_table = fail_table
        self._code = code
        self._message = message

    def table(self, name: str):
        return _ConstraintQuery(
            name, self.db, fail_table=self._fail_table,
            code=self._code, message=self._message,
        )


def test_duplicate_link_unique_violation_409():
    sb = _ConstraintSBStub(
        _seed(), fail_table="pyq_question_stimuli", code="23505",
        message='duplicate key value violates unique constraint '
                '"pyq_question_stimuli_question_id_stimulus_id_key"',
    )
    r = _cms_client(sb).post(
        f"{_CMS_BASE}/pyq-question-stimuli",
        json={"reason": "linking a duplicate", "payload": {
            "question_id": "q-1", "stimulus_id": "st-1", "display_order": 3}},
    )
    assert r.status_code == 409, r.text
    assert "already exists" in str(r.json()["detail"]).lower()


def test_duplicate_display_order_stimulus_unique_violation_409():
    sb = _ConstraintSBStub(
        _seed(), fail_table="pyq_stimuli", code="23505",
        message='duplicate key value violates unique constraint '
                '"pyq_stimuli_paper_display_order_uidx"',
    )
    r = _cms_client(sb).post(
        f"{_CMS_BASE}/pyq-stimuli",
        json={"reason": "colliding display order", "payload": {
            "pyq_paper_id": "paper-1", "stimulus_type": "passage",
            "content_text": "y", "display_order": 1}},
    )
    assert r.status_code == 409, r.text
    assert "display_order" in str(r.json()["detail"]).lower()


def test_nonpositive_display_order_check_violation_422():
    sb = _ConstraintSBStub(
        _seed(), fail_table="pyq_stimuli", code="23514",
        message='new row violates check constraint '
                '"pyq_stimuli_display_order_positive_chk"',
    )
    r = _cms_client(sb).patch(
        f"{_CMS_BASE}/pyq-stimuli/st-1",
        json={"reason": "setting an invalid order", "payload": {"display_order": 0}},
    )
    assert r.status_code == 422, r.text
    assert ">= 1" in str(r.json()["detail"])


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


# ── fix #1: review-queue exam-scoping for the two new kinds ───────────────

def _two_exam_seed():
    """Two exams, each owning one paper → one question → one stimulus → one link."""
    return {
        "pyq_papers": [
            {"id": "paper-A", "exam_id": "exam-A", "exam_phase_id": "phA"},
            {"id": "paper-B", "exam_id": "exam-B", "exam_phase_id": "phB"},
        ],
        "pyq_questions": [
            {"id": "qA", "pyq_paper_id": "paper-A", "reviewer_status": "pending"},
            {"id": "qB", "pyq_paper_id": "paper-B", "reviewer_status": "pending"},
        ],
        "pyq_stimuli": [
            {"id": "stA", "pyq_paper_id": "paper-A", "section_id": None,
             "stimulus_type": "passage", "content_text": "A", "language": "en",
             "display_order": 1, "reviewer_status": "pending", "reviewed_by": None,
             "reviewed_at": None, "metadata": {}, "created_at": "2026-07-01T00:00:00Z"},
            {"id": "stB", "pyq_paper_id": "paper-B", "section_id": None,
             "stimulus_type": "passage", "content_text": "B", "language": "en",
             "display_order": 1, "reviewer_status": "pending", "reviewed_by": None,
             "reviewed_at": None, "metadata": {}, "created_at": "2026-07-01T00:00:00Z"},
        ],
        "pyq_question_stimuli": [
            {"id": "lnkA", "question_id": "qA", "stimulus_id": "stA", "display_order": 1,
             "reviewer_status": "pending", "reviewed_by": None, "reviewed_at": None,
             "created_at": "2026-07-01T00:00:00Z"},
            {"id": "lnkB", "question_id": "qB", "stimulus_id": "stB", "display_order": 1,
             "reviewer_status": "pending", "reviewed_by": None, "reviewed_at": None,
             "created_at": "2026-07-01T00:00:00Z"},
        ],
        "admin_audit_logs": [],
    }


def test_list_items_pyq_stimulus_is_exam_scoped():
    sb = TaxSBStub(_two_exam_seed())
    r = _review_client(sb).get(
        f"{_REVIEW_BASE}/exams/exam-A/items?kind=pyq_stimulus&status=all"
    )
    assert r.status_code == 200, r.text
    ids = {row["id"] for row in r.json()["items"]}
    assert ids == {"stA"}, f"exam-A must not see exam-B's stimulus: {ids}"


def test_list_items_pyq_question_stimulus_is_exam_scoped():
    sb = TaxSBStub(_two_exam_seed())
    r = _review_client(sb).get(
        f"{_REVIEW_BASE}/exams/exam-A/items?kind=pyq_question_stimulus&status=all"
    )
    assert r.status_code == 200, r.text
    ids = {row["id"] for row in r.json()["items"]}
    assert ids == {"lnkA"}, f"exam-A must not see exam-B's link: {ids}"


def test_list_items_pyq_stimulus_scope_empty_for_unknown_exam():
    sb = TaxSBStub(_two_exam_seed())
    r = _review_client(sb).get(
        f"{_REVIEW_BASE}/exams/exam-Z/items?kind=pyq_stimulus&status=all"
    )
    assert r.status_code == 200, r.text
    assert r.json()["items"] == []


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
