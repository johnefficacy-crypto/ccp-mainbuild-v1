"""Tests for the admin CRUD endpoints on ``exam_eligibility_rules`` (PR-D2)."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_eligibility as admin_api
from app.core.auth import get_current_user
from tests.persona_questions._stub import SBStub


EXAM_A = "11111111-1111-4111-8111-111111111111"
EXAM_B = "22222222-2222-4222-8222-222222222222"
RULE_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


def _build_app(sb: SBStub, role: str = "super_admin") -> FastAPI:
    app = FastAPI()
    app.include_router(admin_api.router, prefix="/api")
    admin_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    user = {
        "id": "admin-1",
        "role": role,
        "permissions": ["exam_eligibility.manage"] if role == "admin" else [],
    }
    app.dependency_overrides[get_current_user] = lambda: user
    return app


def _world():
    return {
        "exams": [
            {"id": EXAM_A, "slug": "ssc-cgl", "name": "SSC CGL", "is_active": True, "exam_family_id": None},
            {"id": EXAM_B, "slug": "upsc-cse", "name": "UPSC CSE", "is_active": True, "exam_family_id": None},
        ],
        "exam_eligibility_rules": [
            {
                "id": RULE_A,
                "exam_id": EXAM_A,
                "scope": "all",
                "rule_type": "age_min",
                "value_num": 18,
                "value_text": None,
                "is_knockout": True,
                "source_url": "https://ssc.gov.in/",
                "source_notes": None,
                "reviewer_status": "verified",
                "verified_by": "admin-9",
                "verified_at": "2026-01-01T00:00:00+00:00",
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
            },
        ],
    }


# ── Auth ──────────────────────────────────────────────────────────────────


def test_non_admin_user_is_forbidden():
    sb = SBStub(_world())
    app = FastAPI()
    app.include_router(admin_api.router, prefix="/api")
    admin_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "user-1", "role": "user", "permissions": []
    }
    r = TestClient(app).get("/api/admin/exam-eligibility/exams")
    assert r.status_code == 403


def test_admin_with_permission_can_list():
    sb = SBStub(_world())
    r = TestClient(_build_app(sb, role="admin")).get("/api/admin/exam-eligibility/exams")
    assert r.status_code == 200


# ── List ──────────────────────────────────────────────────────────────────


def test_list_exams_reports_rule_counts_per_status():
    sb = SBStub(_world())
    body = TestClient(_build_app(sb)).get("/api/admin/exam-eligibility/exams").json()
    items = {e["slug"]: e for e in body["items"]}
    assert items["ssc-cgl"]["rule_counts"]["verified"] == 1
    assert items["ssc-cgl"]["rule_counts"]["draft"] == 0
    assert items["ssc-cgl"]["total_rules"] == 1
    assert items["upsc-cse"]["total_rules"] == 0


def test_list_rules_for_unknown_exam_is_404():
    sb = SBStub(_world())
    missing = "99999999-9999-4999-8999-999999999999"
    r = TestClient(_build_app(sb)).get(f"/api/admin/exam-eligibility/exams/{missing}/rules")
    assert r.status_code == 404


def test_list_rules_returns_every_status():
    sb = SBStub(_world())
    sb.db["exam_eligibility_rules"].append(
        {
            "id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
            "exam_id": EXAM_A,
            "scope": "general",
            "rule_type": "age_max",
            "value_num": 32,
            "reviewer_status": "draft",
        }
    )
    body = (
        TestClient(_build_app(sb))
        .get(f"/api/admin/exam-eligibility/exams/{EXAM_A}/rules")
        .json()
    )
    statuses = {r["reviewer_status"] for r in body["rules"]}
    assert statuses == {"verified", "draft"}


# ── Create ────────────────────────────────────────────────────────────────


def test_create_rule_happy_path_stamps_verified_metadata():
    sb = SBStub(_world())
    payload = {
        "scope": "general",
        "rule_type": "age_max",
        "value_num": 32,
        "source_url": "https://ssc.gov.in/",
        "reviewer_status": "verified",
    }
    r = TestClient(_build_app(sb)).post(
        f"/api/admin/exam-eligibility/exams/{EXAM_A}/rules", json=payload
    )
    assert r.status_code == 200
    rule = r.json()["rule"]
    assert rule["verified_by"] == "admin-1"
    assert rule["verified_at"] is not None


def test_create_rule_rejects_unknown_scope():
    sb = SBStub(_world())
    r = TestClient(_build_app(sb)).post(
        f"/api/admin/exam-eligibility/exams/{EXAM_A}/rules",
        json={"scope": "made-up", "rule_type": "age_max", "value_num": 32},
    )
    assert r.status_code == 400
    assert "invalid_scope" in r.json()["detail"]


def test_create_rule_rejects_numeric_rule_without_value_num():
    sb = SBStub(_world())
    r = TestClient(_build_app(sb)).post(
        f"/api/admin/exam-eligibility/exams/{EXAM_A}/rules",
        json={"scope": "general", "rule_type": "age_max"},
    )
    assert r.status_code == 400
    assert "value_num" in r.json()["detail"]


def test_create_rule_rejects_text_rule_without_value_text():
    sb = SBStub(_world())
    r = TestClient(_build_app(sb)).post(
        f"/api/admin/exam-eligibility/exams/{EXAM_A}/rules",
        json={"scope": "all", "rule_type": "nationality"},
    )
    assert r.status_code == 400
    assert "value_text" in r.json()["detail"]


def test_create_rule_conflict_when_scope_rule_type_pair_exists():
    sb = SBStub(_world())
    # The fixture already has (EXAM_A, scope=all, rule_type=age_min).
    r = TestClient(_build_app(sb)).post(
        f"/api/admin/exam-eligibility/exams/{EXAM_A}/rules",
        json={"scope": "all", "rule_type": "age_min", "value_num": 21},
    )
    assert r.status_code == 409
    detail = r.json()["detail"]
    assert detail["code"] == "RULE_ALREADY_EXISTS"
    assert detail["rule_id"] == RULE_A


_STREAM = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"


def test_create_verified_new_rule_type_is_allowed_after_activation():
    # Migration 249 activates evaluator support for the new rule_types, so the
    # fail-closed verify guard is lifted — a discipline rule may now be verified.
    sb = SBStub(_world())
    r = TestClient(_build_app(sb)).post(
        f"/api/admin/exam-eligibility/exams/{EXAM_A}/rules",
        json={"scope": "all", "rule_type": "discipline", "value_text": "LLB",
              "reviewer_status": "verified", "source_url": "https://x"},
    )
    assert r.status_code == 200
    assert r.json()["rule"]["verified_by"] == "admin-1"


def test_create_new_rule_type_as_draft_is_allowed():
    sb = SBStub(_world())
    r = TestClient(_build_app(sb)).post(
        f"/api/admin/exam-eligibility/exams/{EXAM_A}/rules",
        json={"scope": "all", "rule_type": "discipline", "value_text": "LLB",
              "stream_id": _STREAM, "reviewer_status": "draft"},
    )
    assert r.status_code == 200
    assert r.json()["rule"]["stream_id"] == _STREAM


def test_stream_scoped_rule_coexists_with_common():
    # The fixture has common (all, age_min); a stream-scoped one for the same
    # (scope, rule_type) must NOT be treated as a duplicate.
    sb = SBStub(_world())
    r = TestClient(_build_app(sb)).post(
        f"/api/admin/exam-eligibility/exams/{EXAM_A}/rules",
        json={"scope": "all", "rule_type": "age_min", "value_num": 21, "stream_id": _STREAM},
    )
    assert r.status_code == 200


def test_create_qualification_combination_rejects_malformed_json():
    sb = SBStub(_world())
    r = TestClient(_build_app(sb)).post(
        f"/api/admin/exam-eligibility/exams/{EXAM_A}/rules",
        json={"scope": "all", "rule_type": "qualification_combination", "value_json": {}},
    )
    assert r.status_code == 400
    assert "valid combination" in r.json()["detail"]


def test_update_can_clear_stream_id_back_to_common():
    sb = SBStub(_world())
    sb.db["exam_eligibility_rules"].append(
        {
            "id": "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
            "exam_id": EXAM_A, "stream_id": _STREAM, "scope": "obc",
            "rule_type": "age_max", "value_num": 33, "value_text": None,
            "reviewer_status": "draft",
        }
    )
    r = TestClient(_build_app(sb)).put(
        "/api/admin/exam-eligibility/rules/dddddddd-dddd-4ddd-8ddd-dddddddddddd",
        json={"stream_id": None},
    )
    assert r.status_code == 200
    row = next(x for x in sb.db["exam_eligibility_rules"] if x["id"] == "dddddddd-dddd-4ddd-8ddd-dddddddddddd")
    assert row["stream_id"] is None


def test_create_rule_on_unknown_exam_is_404():
    sb = SBStub(_world())
    missing = "99999999-9999-4999-8999-999999999999"
    r = TestClient(_build_app(sb)).post(
        f"/api/admin/exam-eligibility/exams/{missing}/rules",
        json={"scope": "all", "rule_type": "age_min", "value_num": 18},
    )
    assert r.status_code == 404


# ── Update ────────────────────────────────────────────────────────────────


def test_update_rule_promote_draft_to_verified_stamps_metadata():
    sb = SBStub(_world())
    sb.db["exam_eligibility_rules"].append(
        {
            "id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
            "exam_id": EXAM_A,
            "scope": "general",
            "rule_type": "age_max",
            "value_num": 32,
            "source_url": "https://ssc.gov.in/",
            "reviewer_status": "draft",
            "verified_by": None,
            "verified_at": None,
        }
    )
    r = TestClient(_build_app(sb)).put(
        "/api/admin/exam-eligibility/rules/bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        json={"reviewer_status": "verified"},
    )
    assert r.status_code == 200
    updated = next(r for r in sb.db["exam_eligibility_rules"] if r["id"] == "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
    assert updated["reviewer_status"] == "verified"
    assert updated["verified_by"] == "admin-1"
    assert updated["verified_at"] is not None


def test_update_rule_demote_clears_verified_metadata():
    sb = SBStub(_world())
    # RULE_A starts verified; flipping it to draft must wipe verified_*.
    r = TestClient(_build_app(sb)).put(
        f"/api/admin/exam-eligibility/rules/{RULE_A}",
        json={"reviewer_status": "draft"},
    )
    assert r.status_code == 200
    row = next(r for r in sb.db["exam_eligibility_rules"] if r["id"] == RULE_A)
    assert row["reviewer_status"] == "draft"
    assert row["verified_by"] is None
    assert row["verified_at"] is None


def test_update_unknown_rule_is_404():
    sb = SBStub(_world())
    r = TestClient(_build_app(sb)).put(
        "/api/admin/exam-eligibility/rules/00000000-0000-4000-8000-000000000000",
        json={"value_num": 19},
    )
    assert r.status_code == 404


# ── Delete ────────────────────────────────────────────────────────────────


def test_soft_delete_archives_rule():
    sb = SBStub(_world())
    r = TestClient(_build_app(sb)).delete(
        f"/api/admin/exam-eligibility/rules/{RULE_A}"
    )
    assert r.status_code == 200
    body = r.json()
    assert body["deleted"] is True
    assert body["hard"] is False
    row = next(r for r in sb.db["exam_eligibility_rules"] if r["id"] == RULE_A)
    assert row["reviewer_status"] == "archived"


def test_hard_delete_removes_row():
    sb = SBStub(_world())
    r = TestClient(_build_app(sb)).delete(
        f"/api/admin/exam-eligibility/rules/{RULE_A}?hard=true"
    )
    assert r.status_code == 200
    assert all(rule["id"] != RULE_A for rule in sb.db["exam_eligibility_rules"])


def test_delete_unknown_rule_is_404():
    sb = SBStub(_world())
    r = TestClient(_build_app(sb)).delete(
        "/api/admin/exam-eligibility/rules/00000000-0000-4000-8000-000000000000"
    )
    assert r.status_code == 404


# ── Trust-transition provenance validation ────────────────────────────────


def test_create_rule_verified_without_source_or_waiver_is_422():
    sb = SBStub(_world())
    r = TestClient(_build_app(sb)).post(
        f"/api/admin/exam-eligibility/exams/{EXAM_A}/rules",
        json={"scope": "general", "rule_type": "age_max", "value_num": 35, "reviewer_status": "verified"},
    )
    assert r.status_code == 422
    assert "source_url" in r.json()["detail"] or "waiver_reason" in r.json()["detail"]


def test_create_rule_verified_with_source_url_passes():
    sb = SBStub(_world())
    r = TestClient(_build_app(sb)).post(
        f"/api/admin/exam-eligibility/exams/{EXAM_A}/rules",
        json={
            "scope": "general",
            "rule_type": "age_max",
            "value_num": 35,
            "source_url": "https://ssc.gov.in/notice",
            "reviewer_status": "verified",
        },
    )
    assert r.status_code == 200


def test_create_rule_verified_with_waiver_reason_passes():
    sb = SBStub(_world())
    r = TestClient(_build_app(sb)).post(
        f"/api/admin/exam-eligibility/exams/{EXAM_A}/rules",
        json={
            "scope": "general",
            "rule_type": "age_max",
            "value_num": 35,
            "waiver_reason": "Official PDF not yet published; sourced from official press release.",
            "reviewer_status": "verified",
        },
    )
    assert r.status_code == 200


def test_create_rule_draft_without_source_url_is_allowed():
    """Non-trust edits must not be blocked by provenance check."""
    sb = SBStub(_world())
    r = TestClient(_build_app(sb)).post(
        f"/api/admin/exam-eligibility/exams/{EXAM_A}/rules",
        json={"scope": "general", "rule_type": "age_max", "value_num": 35},
    )
    assert r.status_code == 200


def test_update_rule_verify_without_source_or_waiver_is_422():
    sb = SBStub(_world())
    sb.db["exam_eligibility_rules"].append(
        {
            "id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
            "exam_id": EXAM_A,
            "scope": "obc",
            "rule_type": "age_max",
            "value_num": 35,
            "source_url": None,
            "reviewer_status": "draft",
            "verified_by": None,
            "verified_at": None,
        }
    )
    r = TestClient(_build_app(sb)).put(
        "/api/admin/exam-eligibility/rules/cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        json={"reviewer_status": "verified"},
    )
    assert r.status_code == 422


def test_update_rule_verify_with_waiver_reason_passes():
    sb = SBStub(_world())
    sb.db["exam_eligibility_rules"].append(
        {
            "id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
            "exam_id": EXAM_A,
            "scope": "obc",
            "rule_type": "age_max",
            "value_num": 35,
            "source_url": None,
            "reviewer_status": "draft",
            "verified_by": None,
            "verified_at": None,
        }
    )
    r = TestClient(_build_app(sb)).put(
        "/api/admin/exam-eligibility/rules/cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        json={"reviewer_status": "verified", "waiver_reason": "Verified via direct SSC inquiry"},
    )
    assert r.status_code == 200


def test_soft_delete_without_source_or_waiver_is_422():
    sb = SBStub(_world())
    sb.db["exam_eligibility_rules"].append(
        {
            "id": "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
            "exam_id": EXAM_A,
            "scope": "sc",
            "rule_type": "age_max",
            "value_num": 37,
            "source_url": None,
            "reviewer_status": "draft",
        }
    )
    r = TestClient(_build_app(sb)).delete(
        "/api/admin/exam-eligibility/rules/dddddddd-dddd-4ddd-8ddd-dddddddddddd"
    )
    assert r.status_code == 422


def test_soft_delete_with_waiver_reason_passes():
    sb = SBStub(_world())
    sb.db["exam_eligibility_rules"].append(
        {
            "id": "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
            "exam_id": EXAM_A,
            "scope": "sc",
            "rule_type": "age_max",
            "value_num": 37,
            "source_url": None,
            "reviewer_status": "draft",
        }
    )
    r = TestClient(_build_app(sb)).delete(
        "/api/admin/exam-eligibility/rules/dddddddd-dddd-4ddd-8ddd-dddddddddddd"
        "?waiver_reason=Removing+outdated+rule"
    )
    assert r.status_code == 200
    row = next(r for r in sb.db["exam_eligibility_rules"] if r["id"] == "dddddddd-dddd-4ddd-8ddd-dddddddddddd")
    assert row["reviewer_status"] == "archived"


# ── Audit log writes ──────────────────────────────────────────────────────


def test_create_rule_writes_audit_log():
    sb = SBStub(_world())
    TestClient(_build_app(sb)).post(
        f"/api/admin/exam-eligibility/exams/{EXAM_A}/rules",
        json={"scope": "general", "rule_type": "age_max", "value_num": 35},
    )
    logs = sb.db.get("admin_audit_logs", [])
    assert len(logs) == 1
    assert logs[0]["action"] == "eligibility_rule.create"
    assert logs[0]["entity_type"] == "exam_eligibility_rule"
    assert logs[0]["actor_id"] == "admin-1"
    assert logs[0]["new_value"] is not None


def test_update_rule_non_verify_writes_update_audit_log():
    sb = SBStub(_world())
    TestClient(_build_app(sb)).put(
        f"/api/admin/exam-eligibility/rules/{RULE_A}",
        json={"value_num": 19},
    )
    logs = sb.db.get("admin_audit_logs", [])
    assert len(logs) == 1
    assert logs[0]["action"] == "eligibility_rule.update"
    assert logs[0]["entity_id"] == RULE_A
    assert logs[0]["old_value"] is not None


def test_update_rule_verify_transition_writes_verify_audit_log():
    sb = SBStub(_world())
    sb.db["exam_eligibility_rules"].append(
        {
            "id": "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
            "exam_id": EXAM_A,
            "scope": "ews",
            "rule_type": "age_max",
            "value_num": 32,
            "source_url": "https://ssc.gov.in/",
            "reviewer_status": "draft",
            "verified_by": None,
            "verified_at": None,
        }
    )
    TestClient(_build_app(sb)).put(
        "/api/admin/exam-eligibility/rules/eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
        json={"reviewer_status": "verified"},
    )
    logs = sb.db.get("admin_audit_logs", [])
    assert len(logs) == 1
    assert logs[0]["action"] == "eligibility_rule.verify"


def test_soft_delete_writes_archive_audit_log():
    sb = SBStub(_world())
    TestClient(_build_app(sb)).delete(f"/api/admin/exam-eligibility/rules/{RULE_A}")
    logs = sb.db.get("admin_audit_logs", [])
    assert len(logs) == 1
    assert logs[0]["action"] == "eligibility_rule.archive"
    assert logs[0]["entity_id"] == RULE_A
    assert logs[0]["old_value"] is not None


def test_hard_delete_writes_delete_audit_log():
    sb = SBStub(_world())
    TestClient(_build_app(sb)).delete(f"/api/admin/exam-eligibility/rules/{RULE_A}?hard=true")
    logs = sb.db.get("admin_audit_logs", [])
    assert len(logs) == 1
    assert logs[0]["action"] == "eligibility_rule.delete"
    assert logs[0]["entity_id"] == RULE_A


def test_audit_log_captures_waiver_reason_in_notes():
    sb = SBStub(_world())
    TestClient(_build_app(sb)).post(
        f"/api/admin/exam-eligibility/exams/{EXAM_A}/rules",
        json={
            "scope": "general",
            "rule_type": "age_max",
            "value_num": 35,
            "waiver_reason": "sourced from official press release",
            "reviewer_status": "verified",
        },
    )
    logs = sb.db.get("admin_audit_logs", [])
    assert "sourced from official press release" in logs[0]["notes"]
