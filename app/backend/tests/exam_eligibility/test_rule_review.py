"""Tests for the document-gated eligibility-rule review endpoint (migration 257).

POST /api/admin/exam-eligibility/rules/{rule_id}/review

The RPC (``review_exam_eligibility_rule``) is authoritative and runs in Postgres;
CI has no live DB, so ``_ReviewSBStub`` mirrors every check in the SQL exactly
(reason gate → target status → lock/CAS → transition → reviewer separation →
ambiguity guard → provenance gate → atomic audit + update). Any bypass of the
thin Python prechecks is caught here as it would be at the DB level.
"""
from __future__ import annotations

import uuid as _uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_eligibility as admin_api
from app.core.auth import get_current_user
from tests.persona_questions._stub import SBStub, _Exec

EXAM = "11111111-1111-4111-8111-111111111111"
RULE = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
DOC = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
SYL = "55555555-5555-4555-8555-555555555555"
AUTHOR = "author-1"
REVIEWER = {"id": "rev-9", "email": "rev@example.com", "role": "admin",
            "permissions": ["exam_eligibility.manage"]}


# ── RPC emulation ───────────────────────────────────────────────────────────


class _RuleRpc:
    def __init__(self, params, db):
        self._p = params
        self._db = db

    def execute(self):
        p, db = self._p, self._db
        reason = p.get("p_reason")
        if reason is None or not (8 <= len(reason.strip()) <= 500):
            raise Exception("invalid_reason")
        if p["p_target_status"] not in ("draft", "verified", "archived"):
            raise Exception("invalid_target_status")

        rule = next((r for r in db.get("exam_eligibility_rules", []) if r.get("id") == p["p_rule_id"]), None)
        if rule is None:
            raise Exception(f"not_found: rule {p['p_rule_id']}")
        if rule.get("reviewer_status") != p["p_expected_status"]:
            raise Exception("concurrent_modification")

        cur, tgt = rule.get("reviewer_status"), p["p_target_status"]
        allowed = {
            "draft": ("verified", "archived"),
            "verified": ("draft", "archived"),
            "archived": ("draft",),
        }
        if tgt not in allowed.get(cur, ()):
            raise Exception(f"transition_not_allowed: {cur} -> {tgt}")

        if cur == "draft" and tgt == "verified":
            # Fail closed on missing authorship (migration 257).
            if rule.get("created_by") is None:
                raise Exception("creator_missing")
            if str(rule["created_by"]) == str(p["p_actor_id"]):
                raise Exception("reviewer_is_creator")
            if rule.get("rule_type") in ("discipline", "min_percentage"):
                sibling = "min_percentage" if rule["rule_type"] == "discipline" else "discipline"
                for s in db.get("exam_eligibility_rules", []):
                    if (s.get("exam_id") == rule.get("exam_id")
                            and s.get("scope") == rule.get("scope")
                            and s.get("rule_type") == sibling
                            and s.get("reviewer_status") == "verified"
                            and (s.get("stream_id") or None) == (rule.get("stream_id") or None)
                            and s.get("id") != rule.get("id")):
                        raise Exception("ambiguous_linked_qualification")

            blocking = []
            if rule.get("source_document_id") is None:
                blocking.append("source_document_id_missing")
            if rule.get("source_page_start") is None or rule.get("source_page_end") is None:
                blocking.append("source_page_locator_missing")
            if rule.get("source_document_id") is not None:
                asset = next((a for a in db.get("document_assets", []) if a.get("id") == rule["source_document_id"]), None)
                if asset is None:
                    blocking.append("source_document_id_not_found")
                else:
                    if asset.get("status") != "processed":
                        blocking.append("source_document_id_not_processed")
                    if asset.get("source_kind") not in ("official_archive", "official_scan"):
                        blocking.append("source_document_id_untrusted_source_kind")
                    if (asset.get("metadata") or {}).get("exam_id") != rule.get("exam_id"):
                        blocking.append("source_document_id_exam_mismatch")
                    verified_syl = any(
                        sd.get("source_document_id") == rule["source_document_id"]
                        and sd.get("exam_id") == rule.get("exam_id")
                        and sd.get("trust_status") == "verified"
                        for sd in db.get("syllabus_documents", [])
                    )
                    if not verified_syl:
                        blocking.append("no_verified_syllabus_document")
                    ps, pe = rule.get("source_page_start"), rule.get("source_page_end")
                    if ps is not None and pe is not None:
                        want = pe - ps + 1
                        pages = {
                            pg.get("page_number") for pg in db.get("document_pages", [])
                            if pg.get("document_id") == asset.get("id")
                            and pg.get("extraction_status") == "extracted"
                            and ps <= pg.get("page_number") <= pe
                        }
                        if len(pages) < want:
                            blocking.append("referenced_page_not_extracted")
            if blocking:
                raise Exception(f"provenance_incomplete: blocking_fields={','.join(blocking)}")

        audit_id = str(_uuid.uuid4())
        db.setdefault("admin_audit_logs", []).append({
            "id": audit_id, "actor_id": p["p_actor_id"], "actor_email": p["p_actor_email"],
            "action": "eligibility_rule.review", "entity_type": "exam_eligibility_rule",
            "entity_id": p["p_rule_id"],
            "new_value": {"from_status": p["p_expected_status"], "to_status": tgt, "reason": reason.strip()},
            "notes": "admin_exam_eligibility",
        })
        rule["reviewer_status"] = tgt
        if tgt == "verified":
            rule["verified_by"] = p["p_actor_id"]
            rule["verified_at"] = "now"
        else:
            rule["verified_by"] = None
            rule["verified_at"] = None
        return _Exec({"ok": True, "audit_id": audit_id, "row": dict(rule)})


class _ReviewSBStub(SBStub):
    def rpc(self, name, params=None):
        if name == "review_exam_eligibility_rule":
            return _RuleRpc(params or {}, self.db)
        return super().rpc(name, params)


# ── fixtures ────────────────────────────────────────────────────────────────


def _world(*, rule_extra=None, verified_syllabus=True, doc_extra=None,
           pages=(1, 2, 3), rule_status="draft"):
    rule = {
        "id": RULE, "exam_id": EXAM, "stream_id": None, "scope": "all",
        "rule_type": "age_min", "value_num": 21, "value_text": None, "value_json": None,
        "is_knockout": True, "source_url": None, "source_notes": None,
        "source_document_id": DOC, "source_page_start": 1, "source_page_end": 2,
        "created_by": AUTHOR, "reviewer_status": rule_status,
        "verified_by": None, "verified_at": None,
    }
    if rule_extra:
        rule.update(rule_extra)
    doc = {
        "id": DOC, "scope": "admin_exam_intelligence", "document_kind": "notification",
        "status": "processed", "source_kind": "official_archive",
        "storage_bucket": "exam-docs", "storage_path": "sebi/2024.pdf",
        "uploaded_by": "uploader-1", "metadata": {"exam_id": EXAM},
    }
    if doc_extra:
        doc.update(doc_extra)
    db = {
        "exam_eligibility_rules": [rule],
        "document_assets": [doc],
        "syllabus_documents": (
            [{"id": SYL, "exam_id": EXAM, "source_document_id": DOC, "trust_status": "verified"}]
            if verified_syllabus else []
        ),
        "document_pages": [
            {"id": f"pg{n}", "document_id": DOC, "page_number": n, "extraction_status": "extracted"}
            for n in pages
        ],
        "admin_audit_logs": [],
    }
    return db


def _client(sb, user=REVIEWER):
    app = FastAPI()
    app.include_router(admin_api.router, prefix="/api")
    admin_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    if user is not None:
        app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app, raise_server_exceptions=False)


def _review(client, status="verified", reason="verified against official notification"):
    return client.post(f"/api/admin/exam-eligibility/rules/{RULE}/review",
                       json={"status": status, "reason": reason})


# ── tests ───────────────────────────────────────────────────────────────────


def test_second_actor_verifies_valid_rule():
    sb = _ReviewSBStub(_world())
    r = _review(_client(sb))
    assert r.status_code == 200, r.text
    assert r.json()["rule"]["reviewer_status"] == "verified"
    assert r.json()["rule"]["verified_by"] == "rev-9"
    assert len(sb.db["admin_audit_logs"]) == 1


def test_verify_fails_for_same_creator():
    sb = _ReviewSBStub(_world())
    r = _review(_client(sb, {**REVIEWER, "id": AUTHOR}))
    assert r.status_code == 422, r.text
    assert "reviewer_is_creator" in r.text
    assert len(sb.db["admin_audit_logs"]) == 0
    assert sb.db["exam_eligibility_rules"][0]["reviewer_status"] == "draft"


def test_verify_fails_closed_when_creator_missing():
    # Legacy/manual rows carry a NULL created_by — verification must fail closed
    # (a second actor cannot be proven).
    sb = _ReviewSBStub(_world(rule_extra={"created_by": None}))
    r = _review(_client(sb))
    assert r.status_code == 422, r.text
    assert "creator_missing" in r.text
    assert len(sb.db["admin_audit_logs"]) == 0
    assert sb.db["exam_eligibility_rules"][0]["reviewer_status"] == "draft"


def test_verify_fails_without_verified_syllabus_document():
    sb = _ReviewSBStub(_world(verified_syllabus=False))
    r = _review(_client(sb))
    assert r.status_code == 422, r.text
    assert "no_verified_syllabus_document" in r.json()["detail"]["blocking_fields"]


def test_verify_fails_without_page_locator():
    sb = _ReviewSBStub(_world(rule_extra={"source_page_start": None, "source_page_end": None}))
    r = _review(_client(sb))
    assert r.status_code == 422, r.text
    assert "source_page_locator_missing" in r.json()["detail"]["blocking_fields"]


def test_verify_fails_when_referenced_page_not_extracted():
    # Rule cites pages 1-2 but only page 1 is extracted.
    sb = _ReviewSBStub(_world(pages=(1,)))
    r = _review(_client(sb))
    assert r.status_code == 422, r.text
    assert "referenced_page_not_extracted" in r.json()["detail"]["blocking_fields"]


def test_verify_fails_for_unprocessed_asset():
    sb = _ReviewSBStub(_world(doc_extra={"status": "processing"}))
    r = _review(_client(sb))
    assert r.status_code == 422, r.text
    assert "source_document_id_not_processed" in r.json()["detail"]["blocking_fields"]


def test_verify_fails_for_non_authoritative_source_kind():
    sb = _ReviewSBStub(_world(doc_extra={"source_kind": "sanitized_coaching"}))
    r = _review(_client(sb))
    assert r.status_code == 422, r.text
    assert "source_document_id_untrusted_source_kind" in r.json()["detail"]["blocking_fields"]


def test_verify_fails_for_exam_mismatch():
    sb = _ReviewSBStub(_world(doc_extra={"metadata": {"exam_id": "other-exam"}}))
    r = _review(_client(sb))
    assert r.status_code == 422, r.text
    assert "source_document_id_exam_mismatch" in r.json()["detail"]["blocking_fields"]


def test_verify_without_document_link_is_blocked():
    sb = _ReviewSBStub(_world(rule_extra={"source_document_id": None}))
    r = _review(_client(sb))
    assert r.status_code == 422, r.text
    assert "source_document_id_missing" in r.json()["detail"]["blocking_fields"]


def test_ambiguous_linked_qualification_blocked_at_verify():
    world = _world(rule_extra={"rule_type": "discipline", "value_num": None,
                               "value_text": "LLB"})
    world["exam_eligibility_rules"].append({
        "id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", "exam_id": EXAM, "stream_id": None,
        "scope": "all", "rule_type": "min_percentage", "value_num": 60,
        "reviewer_status": "verified",
    })
    sb = _ReviewSBStub(world)
    r = _review(_client(sb))
    assert r.status_code == 422, r.text
    assert "ambiguous_linked_qualification" in r.text


def test_verify_writes_audit_and_status_atomically_on_success():
    sb = _ReviewSBStub(_world())
    _review(_client(sb))
    assert sb.db["exam_eligibility_rules"][0]["reviewer_status"] == "verified"
    assert len(sb.db["admin_audit_logs"]) == 1


def test_blocked_verify_writes_no_audit_no_status_change():
    sb = _ReviewSBStub(_world(verified_syllabus=False))
    _review(_client(sb))
    assert sb.db["exam_eligibility_rules"][0]["reviewer_status"] == "draft"
    assert len(sb.db["admin_audit_logs"]) == 0


def test_disallowed_transition_is_422():
    # archived → verified is not permitted.
    sb = _ReviewSBStub(_world(rule_status="archived"))
    r = _review(_client(sb), status="verified")
    assert r.status_code == 422, r.text
    assert "not allowed" in r.text.lower()


def test_verify_then_demote_clears_stamp():
    sb = _ReviewSBStub(_world())
    assert _review(_client(sb)).status_code == 200
    r = _review(_client(sb), status="draft", reason="reopening for correction")
    assert r.status_code == 200, r.text
    row = sb.db["exam_eligibility_rules"][0]
    assert row["reviewer_status"] == "draft"
    assert row["verified_by"] is None


def test_unknown_rule_is_404():
    sb = _ReviewSBStub(_world())
    r = _client(sb).post(
        "/api/admin/exam-eligibility/rules/99999999-9999-4999-8999-999999999999/review",
        json={"status": "verified", "reason": "verify a nonexistent rule row"},
    )
    assert r.status_code == 404, r.text


def test_short_reason_is_422():
    sb = _ReviewSBStub(_world())
    r = _review(_client(sb), reason="short")
    assert r.status_code == 422, r.text
