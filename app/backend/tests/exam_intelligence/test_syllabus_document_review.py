"""Tests for the syllabus-document trust-gate review endpoint (migration 257).

POST /api/admin/exam-intelligence-cms/syllabus-documents/{id}/review

``review_syllabus_document`` runs in Postgres under a row lock; CI has no live
DB, so ``_SylReviewSBStub`` mirrors the SQL gate exactly (reason → target status
→ lock/CAS → transition → provenance gate that validates + locks the linked
document_assets row → atomic audit + update). Reviewer separation (actor !=
uploader) and the authoritative-source-kind gate are the core new invariants.
"""
from __future__ import annotations

import uuid as _uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intel_cms as cms_api
from app.core.auth import get_current_user
from tests.persona_questions._stub import SBStub, _Exec

SYL = "55555555-5555-4555-8555-555555555555"
DOC = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
EXAM = "11111111-1111-4111-8111-111111111111"
CYCLE = "22222222-2222-4222-8222-222222222222"
UPLOADER = "uploader-1"
REVIEWER = {"id": "rev-9", "email": "rev@example.com", "role": "admin",
            "permissions": [cms_api.PERM_REVIEW]}
_BASE = "/api/admin/exam-intelligence-cms"


class _SylRpc:
    def __init__(self, params, db):
        self._p = params
        self._db = db

    def execute(self):
        p, db = self._p, self._db
        reason = p.get("p_reason")
        if reason is None or not (8 <= len(reason.strip()) <= 500):
            raise Exception("invalid_reason")
        if p["p_target_status"] not in ("verified", "rejected", "pending", "superseded"):
            raise Exception("invalid_target_status")

        doc = next((d for d in db.get("syllabus_documents", []) if d.get("id") == p["p_document_id"]), None)
        if doc is None:
            raise Exception(f"not_found: syllabus_document {p['p_document_id']}")
        if doc.get("trust_status") != p["p_expected_status"]:
            raise Exception("concurrent_modification")

        cur, tgt = doc.get("trust_status"), p["p_target_status"]
        allowed = {
            "pending": ("verified", "rejected"),
            "verified": ("rejected", "superseded", "pending"),
            "rejected": ("pending",),
            "superseded": ("pending",),
        }
        if tgt not in allowed.get(cur, ()):
            raise Exception(f"transition_not_allowed: {cur} -> {tgt}")

        if cur == "pending" and tgt == "verified":
            blocking = []
            if doc.get("source_document_id") is None:
                blocking.append("source_document_id_missing")
            else:
                asset = next((a for a in db.get("document_assets", []) if a.get("id") == doc["source_document_id"]), None)
                if asset is None:
                    blocking.append("source_document_id_not_found")
                else:
                    if asset.get("scope") != "admin_exam_intelligence":
                        blocking.append("source_document_id_wrong_scope")
                    if asset.get("document_kind") not in ("notification", "corrigendum"):
                        blocking.append("source_document_id_wrong_kind")
                    if asset.get("status") != "processed":
                        blocking.append("source_document_id_not_processed")
                    if asset.get("source_kind") not in ("official_archive", "official_scan"):
                        blocking.append("source_document_id_untrusted_source_kind")
                    if not asset.get("storage_bucket") or not asset.get("storage_path"):
                        blocking.append("source_document_id_no_storage")
                    meta = asset.get("metadata") or {}
                    if meta.get("exam_id") != doc.get("exam_id"):
                        blocking.append("source_document_id_exam_mismatch")
                    if doc.get("exam_cycle_id") is not None and meta.get("exam_cycle_id") != doc.get("exam_cycle_id"):
                        blocking.append("source_document_id_cycle_mismatch")
                    extracted = any(
                        pg.get("document_id") == asset.get("id") and pg.get("extraction_status") == "extracted"
                        for pg in db.get("document_pages", [])
                    )
                    if not extracted:
                        blocking.append("source_document_id_no_extracted_pages")
                    if asset.get("uploaded_by") is None:
                        blocking.append("uploader_missing")
                    elif str(asset["uploaded_by"]) == str(p["p_actor_id"]):
                        blocking.append("reviewer_is_uploader")
            if blocking:
                raise Exception(f"provenance_incomplete: blocking_fields={','.join(blocking)}")

        audit_id = str(_uuid.uuid4())
        db.setdefault("admin_audit_logs", []).append({
            "id": audit_id, "actor_id": p["p_actor_id"], "actor_email": p["p_actor_email"],
            "action": "exam_intel.cms.syllabus_document.review",
            "entity_type": "syllabus_document", "entity_id": p["p_document_id"],
            "new_value": {"from_status": p["p_expected_status"], "to_status": tgt}, "notes": "admin_exam_intel_cms",
        })
        old_status = doc["trust_status"]
        old_source = doc.get("source_document_id")
        old_exam = doc.get("exam_id")
        doc["trust_status"] = tgt
        if tgt == "verified":
            doc["reviewed_by"] = p["p_actor_id"]
            doc["reviewed_at"] = "now"
            doc["reviewer_notes"] = reason.strip()
        else:
            doc["reviewed_by"] = None
            doc["reviewed_at"] = None
            doc["reviewer_notes"] = None

        # Emulate migration 257's AFTER-UPDATE cascade-demotion trigger: when a
        # verified authority stops backing (source_document_id, exam_id), demote
        # every dependent verified eligibility rule that would be left orphaned.
        if old_status == "verified" and old_source is not None and tgt != "verified":
            for rule in db.get("exam_eligibility_rules", []):
                if (rule.get("reviewer_status") == "verified"
                        and rule.get("source_document_id") == old_source
                        and rule.get("exam_id") == old_exam):
                    still_backed = any(
                        sd.get("source_document_id") == old_source
                        and sd.get("exam_id") == old_exam
                        and sd.get("trust_status") == "verified"
                        and sd.get("id") != doc.get("id")
                        for sd in db.get("syllabus_documents", [])
                    )
                    if not still_backed:
                        rule["reviewer_status"] = "draft"
                        rule["verified_by"] = None
                        rule["verified_at"] = None
                        db.setdefault("admin_audit_logs", []).append({
                            "id": str(_uuid.uuid4()), "actor_id": None,
                            "action": "eligibility_rule.auto_demote",
                            "entity_type": "exam_eligibility_rule",
                            "entity_id": rule.get("id"), "notes": "system_cascade",
                        })
        return _Exec({"ok": True, "audit_id": audit_id, "row": dict(doc)})


class _SylReviewSBStub(SBStub):
    def rpc(self, name, params=None):
        if name == "review_syllabus_document":
            return _SylRpc(params or {}, self.db)
        return super().rpc(name, params)


def _world(*, doc_extra=None, syl_extra=None, pages=True, status="pending"):
    syl = {"id": SYL, "exam_id": EXAM, "exam_cycle_id": None, "trust_status": status,
           "source_document_id": DOC, "reviewed_by": None, "reviewed_at": None,
           "reviewer_notes": None}
    if syl_extra:
        syl.update(syl_extra)
    doc = {"id": DOC, "scope": "admin_exam_intelligence", "document_kind": "notification",
           "status": "processed", "source_kind": "official_archive",
           "storage_bucket": "exam-docs", "storage_path": "sebi/notif.pdf",
           "uploaded_by": UPLOADER, "metadata": {"exam_id": EXAM}}
    if doc_extra:
        doc.update(doc_extra)
    return {
        "syllabus_documents": [syl],
        "document_assets": [doc],
        "document_pages": ([{"id": "pg1", "document_id": DOC, "page_number": 1,
                             "extraction_status": "extracted"}] if pages else []),
        "admin_audit_logs": [],
    }


def _client(sb, user=REVIEWER):
    app = FastAPI()
    app.include_router(cms_api.router, prefix="/api")
    cms_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[cms_api._flag_enabled] = lambda: None
    if user is not None:
        app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app, raise_server_exceptions=False)


def _review(client, status="verified", reason="verified against official archive PDF"):
    return client.post(f"{_BASE}/syllabus-documents/{SYL}/review",
                       json={"status": status, "reason": reason})


# ── tests ───────────────────────────────────────────────────────────────────


def test_different_reviewer_verifies_valid_document():
    sb = _SylReviewSBStub(_world())
    r = _review(_client(sb))
    assert r.status_code == 200, r.text
    row = r.json()["row"]
    assert row["trust_status"] == "verified"
    assert row["reviewed_by"] == "rev-9"
    assert row["reviewer_notes"]
    assert len(sb.db["admin_audit_logs"]) == 1


def test_verification_fails_for_same_uploader():
    sb = _SylReviewSBStub(_world())
    r = _review(_client(sb, {**REVIEWER, "id": UPLOADER}))
    assert r.status_code == 422, r.text
    assert "reviewer_is_uploader" in r.json()["detail"]["blocking_fields"]
    assert len(sb.db["admin_audit_logs"]) == 0
    assert sb.db["syllabus_documents"][0]["trust_status"] == "pending"


def test_verification_fails_closed_when_uploader_missing():
    # A legacy/manual asset with NULL uploaded_by cannot establish reviewer
    # separation → fail closed (migration 257).
    sb = _SylReviewSBStub(_world(doc_extra={"uploaded_by": None}))
    r = _review(_client(sb))
    assert r.status_code == 422, r.text
    assert "uploader_missing" in r.json()["detail"]["blocking_fields"]


def test_verification_fails_for_unprocessed_asset():
    sb = _SylReviewSBStub(_world(doc_extra={"status": "processing"}))
    r = _review(_client(sb))
    assert r.status_code == 422, r.text
    assert "source_document_id_not_processed" in r.json()["detail"]["blocking_fields"]


def test_verification_fails_for_non_authoritative_source_kind():
    sb = _SylReviewSBStub(_world(doc_extra={"source_kind": "raw_coaching"}))
    r = _review(_client(sb))
    assert r.status_code == 422, r.text
    assert "source_document_id_untrusted_source_kind" in r.json()["detail"]["blocking_fields"]


def test_verification_fails_for_wrong_kind():
    sb = _SylReviewSBStub(_world(doc_extra={"document_kind": "syllabus"}))
    r = _review(_client(sb))
    assert r.status_code == 422, r.text
    assert "source_document_id_wrong_kind" in r.json()["detail"]["blocking_fields"]


def test_verification_fails_for_exam_mismatch():
    sb = _SylReviewSBStub(_world(doc_extra={"metadata": {"exam_id": "other"}}))
    r = _review(_client(sb))
    assert r.status_code == 422, r.text
    assert "source_document_id_exam_mismatch" in r.json()["detail"]["blocking_fields"]


def test_verification_fails_for_cycle_mismatch():
    sb = _SylReviewSBStub(_world(
        syl_extra={"exam_cycle_id": CYCLE},
        doc_extra={"metadata": {"exam_id": EXAM, "exam_cycle_id": "other-cycle"}},
    ))
    r = _review(_client(sb))
    assert r.status_code == 422, r.text
    assert "source_document_id_cycle_mismatch" in r.json()["detail"]["blocking_fields"]


def test_verification_fails_without_extracted_pages():
    sb = _SylReviewSBStub(_world(pages=False))
    r = _review(_client(sb))
    assert r.status_code == 422, r.text
    assert "source_document_id_no_extracted_pages" in r.json()["detail"]["blocking_fields"]


def test_verification_fails_without_document_link():
    sb = _SylReviewSBStub(_world(syl_extra={"source_document_id": None}))
    r = _review(_client(sb))
    assert r.status_code == 422, r.text
    assert "source_document_id_missing" in r.json()["detail"]["blocking_fields"]


def test_reject_does_not_require_provenance():
    sb = _SylReviewSBStub(_world(doc_extra={"status": "processing"}))
    r = _review(_client(sb), status="rejected")
    assert r.status_code == 200, r.text
    assert sb.db["syllabus_documents"][0]["trust_status"] == "rejected"


def test_demote_clears_reviewer_attribution():
    sb = _SylReviewSBStub(_world(status="verified",
                                 syl_extra={"reviewed_by": "rev-9", "reviewer_notes": "prior"}))
    r = _review(_client(sb), status="pending", reason="reopening for re-review")
    assert r.status_code == 200, r.text
    row = sb.db["syllabus_documents"][0]
    assert row["trust_status"] == "pending"
    assert row["reviewed_by"] is None
    assert row["reviewer_notes"] is None


def test_cms_only_permission_is_403():
    sb = _SylReviewSBStub(_world())
    r = _review(_client(sb, {"id": "c", "email": "c@x", "role": "admin",
                             "permissions": [cms_api.PERM_CMS]}))
    assert r.status_code == 403, r.text


def test_disallowed_transition_is_422():
    sb = _SylReviewSBStub(_world(status="rejected"))
    r = _review(_client(sb), status="verified")
    assert r.status_code == 422, r.text
    assert "not allowed" in r.text.lower()


def test_unknown_document_is_404():
    sb = _SylReviewSBStub(_world())
    r = _client(sb).post(
        f"{_BASE}/syllabus-documents/99999999-9999-4999-8999-999999999999/review",
        json={"status": "verified", "reason": "verify a nonexistent document"},
    )
    assert r.status_code == 404, r.text


def test_short_reason_is_422():
    sb = _SylReviewSBStub(_world())
    r = _review(_client(sb), reason="short")
    assert r.status_code == 422, r.text


# ── Authority-dependency cascade demotion (migration 257 §E) ─────────────────

RULE = "77777777-7777-4777-8777-777777777777"


def _dependent_rule(**extra):
    rule = {"id": RULE, "exam_id": EXAM, "source_document_id": DOC,
            "reviewer_status": "verified", "verified_by": "rev-9",
            "verified_at": "now"}
    rule.update(extra)
    return rule


def test_demoting_syllabus_cascade_demotes_dependent_verified_rule():
    # A verified rule depends on the verified syllabus authority; demoting the
    # syllabus (verified → pending) must cascade-demote the rule to draft so a
    # verified rule never outlives its authority.
    world = _world(status="verified")
    world["exam_eligibility_rules"] = [_dependent_rule()]
    sb = _SylReviewSBStub(world)
    r = _review(_client(sb), status="pending", reason="reopening syllabus for re-review")
    assert r.status_code == 200, r.text
    rule = sb.db["exam_eligibility_rules"][0]
    assert rule["reviewer_status"] == "draft"
    assert rule["verified_by"] is None
    assert any(a.get("action") == "eligibility_rule.auto_demote"
               for a in sb.db["admin_audit_logs"])


def test_rejecting_syllabus_cascade_demotes_dependent_rule():
    world = _world(status="verified")
    world["exam_eligibility_rules"] = [_dependent_rule()]
    sb = _SylReviewSBStub(world)
    r = _review(_client(sb), status="rejected", reason="superseded by corrigendum")
    assert r.status_code == 200, r.text
    assert sb.db["exam_eligibility_rules"][0]["reviewer_status"] == "draft"


def test_cascade_leaves_independent_rule_untouched():
    # A verified rule backed by a DIFFERENT document is not affected.
    world = _world(status="verified")
    world["exam_eligibility_rules"] = [_dependent_rule(source_document_id="other-doc")]
    sb = _SylReviewSBStub(world)
    r = _review(_client(sb), status="pending", reason="reopening this syllabus only")
    assert r.status_code == 200, r.text
    assert sb.db["exam_eligibility_rules"][0]["reviewer_status"] == "verified"
