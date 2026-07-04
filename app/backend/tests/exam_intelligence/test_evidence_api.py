"""D05 document-evidence registration + trust-review API (PR-4).

Exercises the FastAPI mutation path that populates ``exam_document_evidence`` /
``exam_document_evidence_roles`` — the tables ``document_policy`` reads for Step 9 — under the
locked J2 permission separation (manage = operational edits, review = trust transitions, cms is
NOT accepted). The stub does not enforce the migration-211 triggers, so scope-violation mapping is
covered by the friendly pre-checks here plus the document_policy unit tests.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intel_evidence as ev_api
from app.core.auth import get_current_user
from tests.exam_intelligence.test_cms_taxonomy import TaxSBStub

_BASE = "/api/admin/exam-intelligence-cms/evidence"
PERM_MANAGE = ev_api.PERM_MANAGE
PERM_REVIEW = ev_api.PERM_REVIEW
PERM_CMS = "exam_intelligence.cms"


def _client(sb: TaxSBStub, *, perms=(PERM_MANAGE, PERM_REVIEW), role: str = "admin") -> TestClient:
    app = FastAPI()
    app.include_router(ev_api.router, prefix="/api")
    ev_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[ev_api._flag_enabled] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "admin-1", "email": "op@test", "role": role, "permissions": list(perms),
    }
    return TestClient(app, raise_server_exceptions=False)


def _seed() -> dict:
    return {
        "exams": [{"id": "e1", "slug": "ssc-cgl", "name": "SSC CGL",
                   "management_mode": "core", "exam_type": "recruitment"}],
        "exam_cycles": [{"id": "cA", "exam_id": "e1", "status": "active", "cycle_name": "2026"}],
        "exam_phases": [{"id": "pA", "exam_id": "e1", "exam_cycle_id": "cA",
                         "phase_kind": "objective_written", "status": "active", "phase_name": "Tier I"}],
        "document_assets": [{
            "id": "doc1", "scope": "admin_exam_intelligence", "status": "processed",
            "content_hash": "abc123", "document_kind": "syllabus", "title": "SSC CGL Syllabus",
            "original_filename": "syllabus.pdf",
            "metadata": {"exam_id": "e1", "exam_cycle_id": "cA", "exam_phase_id": "pA"},
        }],
        "source_registry": [
            {"id": "srcOK", "source_name": "SSC Official", "is_active": True,
             "is_official_source": True, "discovery_only": False},
            {"id": "srcBad", "source_name": "Coaching Blog", "is_active": True,
             "is_official_source": False, "discovery_only": True},
        ],
        "exam_evidence_kinds": [{"kind": k} for k in ("syllabus", "exam_pattern", "pyq_paper", "answer_key")],
        "exam_document_evidence": [],
        "exam_document_evidence_roles": [],
        "document_processing_jobs": [],
        "admin_audit_logs": [],
    }


def _register(client, **over) -> "object":
    body = {
        "document_asset_id": "doc1", "exam_id": "e1", "exam_cycle_id": "cA",
        "exam_phase_id": "pA", "source_registry_id": "srcOK",
        "roles": [{"evidence_kind": "syllabus", "exam_phase_id": "pA", "exam_cycle_id": "cA"}],
        "reason": "official syllabus for tier I",
    }
    body.update(over)
    return client.post(_BASE, json=body)


# ── register (manage) ───────────────────────────────────────────────────────


def test_register_creates_pending_evidence_and_role():
    sb = TaxSBStub(_seed())
    r = _register(_client(sb))
    assert r.status_code == 200, r.text
    ev = r.json()["evidence"]
    assert ev["trust_status"] == "pending"
    assert ev["source_authoritative"] is True
    assert [role["evidence_kind"] for role in ev["roles"]] == ["syllabus"]
    assert len(sb.db["exam_document_evidence"]) == 1
    assert len(sb.db["exam_document_evidence_roles"]) == 1


def test_register_rejects_unknown_evidence_kind():
    sb = TaxSBStub(_seed())
    r = _register(_client(sb), roles=[{"evidence_kind": "not_a_kind"}])
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "unknown_evidence_kind"


def test_register_rejects_missing_asset():
    sb = TaxSBStub(_seed())
    r = _register(_client(sb), document_asset_id="ghost")
    assert r.status_code == 404


def test_register_rejects_cross_exam_asset():
    sb = TaxSBStub(_seed())
    sb.db["document_assets"][0]["metadata"] = {"exam_id": "other"}
    r = _register(_client(sb))
    assert r.status_code == 422


def test_register_conflict_on_duplicate_registration():
    sb = TaxSBStub(_seed())
    assert _register(_client(sb)).status_code == 200
    r = _register(_client(sb))
    assert r.status_code == 409
    assert r.json()["detail"]["error"] == "already_registered"


def test_register_non_authoritative_source_flagged_false():
    sb = TaxSBStub(_seed())
    r = _register(_client(sb), source_registry_id="srcBad")
    assert r.status_code == 200, r.text
    assert r.json()["evidence"]["source_authoritative"] is False


# ── P0/P1 review findings ────────────────────────────────────────────────────


def test_register_rejects_incomplete_upload_placeholder():
    """A pre-complete-upload placeholder (status=uploaded / pending hash) cannot be registered."""
    sb = TaxSBStub(_seed())
    sb.db["document_assets"][0].update({"status": "uploaded", "content_hash": "pending:deadbeef"})
    r = _register(_client(sb))
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "upload_incomplete"


def test_register_rejects_cross_cycle_asset_scope():
    """A cycle-A-scoped asset cannot be registered under cycle B (D05 predicate 1)."""
    sb = TaxSBStub(_seed())
    sb.db["exam_cycles"].append({"id": "cB", "exam_id": "e1", "status": "active"})
    r = _register(_client(sb), exam_cycle_id="cB", exam_phase_id=None,
                  roles=[{"evidence_kind": "syllabus", "exam_cycle_id": "cB"}])
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "asset_cycle_scope_conflict"


def test_register_rejects_cross_phase_role_scope():
    """A phase-A-scoped asset cannot carry a role scoped to phase B."""
    sb = TaxSBStub(_seed())
    sb.db["exam_phases"].append({"id": "pB", "exam_id": "e1", "exam_cycle_id": "cA",
                                 "phase_kind": "interview", "status": "active"})
    r = _register(_client(sb), roles=[{"evidence_kind": "syllabus", "exam_phase_id": "pB"}])
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "asset_phase_scope_conflict"


def test_exam_level_asset_may_narrow_scope():
    """An exam-level (unscoped) asset may be narrowed to a cycle/phase in the same exam."""
    sb = TaxSBStub(_seed())
    sb.db["document_assets"][0]["metadata"] = {"exam_id": "e1"}
    r = _register(_client(sb))
    assert r.status_code == 200, r.text


# ── permission tiers ─────────────────────────────────────────────────────────


def test_register_requires_manage_not_cms():
    sb = TaxSBStub(_seed())
    r = _register(_client(sb, perms=(PERM_CMS,)))
    assert r.status_code == 403


def test_register_forbidden_for_review_only():
    sb = TaxSBStub(_seed())
    r = _register(_client(sb, perms=(PERM_REVIEW,)))
    assert r.status_code == 403


def test_review_requires_review_not_manage():
    sb = TaxSBStub(_seed())
    ev_id = _register(_client(sb, perms=(PERM_MANAGE,))).json()["evidence"]["id"]
    r = _client(sb, perms=(PERM_MANAGE,)).post(
        f"{_BASE}/{ev_id}/review", json={"decision": "verified", "reason": "manage cannot verify"})
    assert r.status_code == 403


def test_review_forbidden_for_cms():
    sb = TaxSBStub(_seed())
    ev_id = _register(_client(sb)).json()["evidence"]["id"]
    r = _client(sb, perms=(PERM_CMS,)).post(
        f"{_BASE}/{ev_id}/review", json={"decision": "verified", "reason": "cms cannot verify"})
    assert r.status_code == 403


def test_super_admin_bypasses_all_tiers():
    sb = TaxSBStub(_seed())
    reg = _register(_client(sb, perms=(), role="super_admin"))
    assert reg.status_code == 200, reg.text
    ev_id = reg.json()["evidence"]["id"]
    rev = _client(sb, perms=(), role="super_admin").post(
        f"{_BASE}/{ev_id}/review", json={"decision": "verified", "reason": "super admin verify"})
    assert rev.status_code == 200


def test_reads_allowed_for_manage_or_review_but_not_cms():
    sb = TaxSBStub(_seed())
    assert _client(sb, perms=(PERM_MANAGE,)).get(f"{_BASE}?exam_id=e1").status_code == 200
    assert _client(sb, perms=(PERM_REVIEW,)).get(f"{_BASE}?exam_id=e1").status_code == 200
    assert _client(sb, perms=(PERM_CMS,)).get(f"{_BASE}?exam_id=e1").status_code == 403


# ── review (review tier) ─────────────────────────────────────────────────────


def test_review_verify_sets_trust_and_reviewer():
    sb = TaxSBStub(_seed())
    ev_id = _register(_client(sb)).json()["evidence"]["id"]
    r = _client(sb).post(f"{_BASE}/{ev_id}/review",
                         json={"decision": "verified", "reason": "matches official gazette"})
    assert r.status_code == 200, r.text
    row = sb.db["exam_document_evidence"][0]
    assert row["trust_status"] == "verified"
    assert row["reviewed_by"] == "admin-1"
    assert row["reviewed_at"]


def test_review_reject_transition():
    sb = TaxSBStub(_seed())
    ev_id = _register(_client(sb)).json()["evidence"]["id"]
    r = _client(sb).post(f"{_BASE}/{ev_id}/review",
                         json={"decision": "rejected", "reason": "wrong year uploaded"})
    assert r.status_code == 200
    assert sb.db["exam_document_evidence"][0]["trust_status"] == "rejected"


def test_review_rejects_bad_decision():
    sb = TaxSBStub(_seed())
    ev_id = _register(_client(sb)).json()["evidence"]["id"]
    r = _client(sb).post(f"{_BASE}/{ev_id}/review",
                         json={"decision": "superseded", "reason": "not allowed here"})
    assert r.status_code == 422


def test_review_blocks_superseded_evidence():
    sb = TaxSBStub(_seed())
    ev_id = _register(_client(sb)).json()["evidence"]["id"]
    sb.db["exam_document_evidence"][0]["trust_status"] = "superseded"
    r = _client(sb).post(f"{_BASE}/{ev_id}/review",
                         json={"decision": "verified", "reason": "should be blocked now"})
    assert r.status_code == 409


# ── supersede (review tier) ──────────────────────────────────────────────────


def test_supersede_marks_status_and_link():
    sb = TaxSBStub(_seed())
    client = _client(sb)
    old_id = _register(client).json()["evidence"]["id"]
    sb.db["document_assets"].append({
        "id": "doc2", "scope": "admin_exam_intelligence", "status": "processed",
        "content_hash": "def456", "document_kind": "syllabus",
        "metadata": {"exam_id": "e1", "exam_cycle_id": "cA", "exam_phase_id": "pA"}})
    new_id = _register(client, document_asset_id="doc2").json()["evidence"]["id"]
    r = client.post(f"{_BASE}/{old_id}/supersede",
                    json={"superseded_by_id": new_id, "reason": "replaced by corrigendum-updated"})
    assert r.status_code == 200, r.text
    row = next(e for e in sb.db["exam_document_evidence"] if e["id"] == old_id)
    assert row["trust_status"] == "superseded"
    assert row["superseded_by_id"] == new_id


def test_supersede_rejects_self_reference():
    sb = TaxSBStub(_seed())
    ev_id = _register(_client(sb)).json()["evidence"]["id"]
    r = _client(sb).post(f"{_BASE}/{ev_id}/supersede",
                         json={"superseded_by_id": ev_id, "reason": "cannot self supersede"})
    assert r.status_code == 422


# ── roles + trust reset (manage tier) ────────────────────────────────────────


def test_add_and_remove_role():
    sb = TaxSBStub(_seed())
    client = _client(sb)
    ev_id = _register(client).json()["evidence"]["id"]
    add = client.post(f"{_BASE}/{ev_id}/roles",
                      json={"evidence_kind": "exam_pattern", "exam_phase_id": "pA", "exam_cycle_id": "cA",
                            "reason": "same pdf carries the pattern"})
    assert add.status_code == 200, add.text
    role_id = add.json()["role"]["id"]
    assert len(sb.db["exam_document_evidence_roles"]) == 2
    rm = client.delete(f"{_BASE}/{ev_id}/roles/{role_id}?reason=pattern+moved+to+own+doc")
    assert rm.status_code == 200
    assert len(sb.db["exam_document_evidence_roles"]) == 1


def test_add_role_after_verify_resets_trust_to_pending():
    """A newly asserted role must NOT inherit a prior verification — trust resets to pending."""
    sb = TaxSBStub(_seed())
    ev_id = _register(_client(sb)).json()["evidence"]["id"]
    _client(sb).post(f"{_BASE}/{ev_id}/review", json={"decision": "verified", "reason": "verified syllabus role"})
    assert sb.db["exam_document_evidence"][0]["trust_status"] == "verified"
    add = _client(sb).post(f"{_BASE}/{ev_id}/roles",
                           json={"evidence_kind": "exam_pattern", "exam_phase_id": "pA", "exam_cycle_id": "cA",
                                 "reason": "attaching pattern claim"})
    assert add.status_code == 200, add.text
    assert add.json()["trust_reset"] is True
    row = sb.db["exam_document_evidence"][0]
    assert row["trust_status"] == "pending"
    assert row["reviewed_by"] is None and row["reviewed_at"] is None


def test_remove_role_after_verify_resets_trust():
    sb = TaxSBStub(_seed())
    ev_id = _register(_client(sb)).json()["evidence"]["id"]
    role_id = sb.db["exam_document_evidence_roles"][0]["id"]
    _client(sb).post(f"{_BASE}/{ev_id}/review", json={"decision": "verified", "reason": "verified before removal"})
    rm = _client(sb).delete(f"{_BASE}/{ev_id}/roles/{role_id}?reason=role+no+longer+applies")
    assert rm.status_code == 200
    assert sb.db["exam_document_evidence"][0]["trust_status"] == "pending"


def test_role_edit_blocked_on_superseded():
    sb = TaxSBStub(_seed())
    ev_id = _register(_client(sb)).json()["evidence"]["id"]
    sb.db["exam_document_evidence"][0]["trust_status"] = "superseded"
    r = _client(sb).post(f"{_BASE}/{ev_id}/roles",
                         json={"evidence_kind": "exam_pattern", "reason": "should be blocked"})
    assert r.status_code == 409


# ── list + sources + coverage ────────────────────────────────────────────────


def test_list_returns_registered_with_roles():
    sb = TaxSBStub(_seed())
    _register(_client(sb))
    r = _client(sb).get(f"{_BASE}?exam_id=e1")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["document"]["title"] == "SSC CGL Syllabus"


def test_list_filters_by_cycle_server_side():
    sb = TaxSBStub(_seed())
    _register(_client(sb))
    r = _client(sb).get(f"{_BASE}?exam_id=e1&exam_cycle_id=cA")
    assert r.status_code == 200
    assert r.json()["total"] == 1
    r2 = _client(sb).get(f"{_BASE}?exam_id=e1&exam_cycle_id=cZ")
    assert r2.json()["total"] == 0


def test_sources_marks_authority():
    sb = TaxSBStub(_seed())
    r = _client(sb).get(f"{_BASE}/sources")
    assert r.status_code == 200
    by_id = {s["id"]: s for s in r.json()["items"]}
    assert by_id["srcOK"]["is_authoritative"] is True
    assert by_id["srcBad"]["is_authoritative"] is False


def test_coverage_reports_unmet_until_verified():
    sb = TaxSBStub(_seed())
    sb.db["exam_evidence_requirements"] = [{
        "id": "req1", "management_mode": "core", "phase_kind": "objective_written",
        "evidence_kind": "syllabus", "satisfied_by": "document_asset", "requirement_level": "required",
        "gate_effect": "block", "scope": "phase", "minimum_count": 1,
        "requires_verified_source": True, "requires_human_review": True, "requires_extraction": False,
        "condition_code": "always", "is_active": True,
    }]
    sb.db["exam_evidence_requirement_overrides"] = []
    r = _client(sb).get(f"{_BASE}/coverage?exam_id=e1&exam_cycle_id=cA")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["applicable"] is True
    assert body["complete"] is False
    assert any(u.get("evidence_kind") == "syllabus" for u in body["unmet_requirements"])


def test_coverage_not_applicable_for_index_only():
    sb = TaxSBStub(_seed())
    sb.db["exams"][0]["management_mode"] = "index_only"
    r = _client(sb).get(f"{_BASE}/coverage?exam_id=e1&exam_cycle_id=cA")
    assert r.status_code == 200
    assert r.json()["applicable"] is False
