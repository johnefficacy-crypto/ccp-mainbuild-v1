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


IRDAI_ID = "33333333-3333-4333-8333-333333333333"
RETIRED_ID = "44444444-4444-4444-8444-444444444444"


def _world_with_inactive():
    world = _world()
    # A seeded-but-inactive draft regulator identity (e.g. PFRDA/IRDAI per migration 244):
    # inactive AND carrying the governed provenance='draft' marker in metadata.
    world["exams"].append(
        {
            "id": IRDAI_ID,
            "slug": "irdai-am",
            "name": "IRDAI Assistant Manager",
            "is_active": False,
            "exam_family_id": None,
            "metadata": {"provenance": "draft", "verified": False},
        }
    )
    # A second inactive exam that is NOT a draft — proves is_active=false alone
    # cannot distinguish a seeded draft from a retired identity.
    world["exams"].append(
        {
            "id": RETIRED_ID,
            "slug": "legacy-retired",
            "name": "Legacy Retired Exam",
            "is_active": False,
            "exam_family_id": None,
            "metadata": {"disposition": "retired"},
        }
    )
    # Canonical stream identities for the draft regulator exam (migration 244):
    # non-deterministic UUIDs, which is why an admin listing path is needed.
    world["exam_streams"] = [
        {
            "id": "55555555-5555-4555-8555-555555555555",
            "exam_id": IRDAI_ID,
            "stream_key": "law",
            "name": "Law",
            "metadata": {"provenance": "draft", "verified": False},
        },
        {
            "id": "66666666-6666-4666-8666-666666666666",
            "exam_id": IRDAI_ID,
            "stream_key": "actuarial",
            "name": "Actuarial",
            "metadata": {"provenance": "draft", "verified": False},
        },
    ]
    return world


def test_list_exams_hides_inactive_by_default():
    sb = SBStub(_world_with_inactive())
    body = TestClient(_build_app(sb)).get("/api/admin/exam-eligibility/exams").json()
    slugs = {e["slug"] for e in body["items"]}
    assert "irdai-am" not in slugs  # inactive draft identity not discoverable by default
    assert {"ssc-cgl", "upsc-cse"} <= slugs


def test_list_exams_include_inactive_surfaces_draft_identities():
    sb = SBStub(_world_with_inactive())
    body = (
        TestClient(_build_app(sb))
        .get("/api/admin/exam-eligibility/exams", params={"include_inactive": "true"})
        .json()
    )
    items = {e["slug"]: e for e in body["items"]}
    assert "irdai-am" in items
    assert items["irdai-am"]["is_active"] is False
    assert items["ssc-cgl"]["is_active"] is True


def test_list_exams_provenance_distinguishes_draft_from_retired():
    # is_active=false is ambiguous; provenance tells a seeded draft from a retired exam.
    sb = SBStub(_world_with_inactive())
    body = (
        TestClient(_build_app(sb))
        .get("/api/admin/exam-eligibility/exams", params={"include_inactive": "true"})
        .json()
    )
    items = {e["slug"]: e for e in body["items"]}
    assert items["irdai-am"]["provenance"] == "draft"
    assert items["legacy-retired"]["provenance"] is None  # not a draft — do not author here
    assert items["ssc-cgl"]["provenance"] is None
    # metadata itself is not leaked into the item shape.
    assert "metadata" not in items["irdai-am"]


def test_list_streams_returns_canonical_stream_ids():
    sb = SBStub(_world_with_inactive())
    body = (
        TestClient(_build_app(sb))
        .get(f"/api/admin/exam-eligibility/exams/{IRDAI_ID}/streams")
        .json()
    )
    assert body["exam"]["slug"] == "irdai-am"
    streams = {s["stream_key"]: s for s in body["streams"]}
    # migration 244 seeds six IRDAI streams incl. law — the id is what RuleCreate needs.
    assert {"law", "actuarial"} <= set(streams)
    assert streams["law"]["id"] == "55555555-5555-4555-8555-555555555555"
    assert streams["law"]["provenance"] == "draft"
    assert "metadata" not in streams["law"]


def test_list_streams_for_unknown_exam_is_404():
    sb = SBStub(_world_with_inactive())
    missing = "99999999-9999-4999-8999-999999999999"
    r = TestClient(_build_app(sb)).get(
        f"/api/admin/exam-eligibility/exams/{missing}/streams"
    )
    assert r.status_code == 404


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


def test_create_rule_lands_draft_and_stamps_created_by():
    # Migration 256: create ALWAYS lands draft (verification is a separate,
    # document-gated review transition) and stamps the author for reviewer
    # separation.
    sb = SBStub(_world())
    payload = {
        "scope": "general",
        "rule_type": "age_max",
        "value_num": 32,
        "source_url": "https://ssc.gov.in/",
    }
    r = TestClient(_build_app(sb)).post(
        f"/api/admin/exam-eligibility/exams/{EXAM_A}/rules", json=payload
    )
    assert r.status_code == 200
    rule = r.json()["rule"]
    assert rule["reviewer_status"] == "draft"
    assert rule["created_by"] == "admin-1"
    assert rule.get("verified_by") is None


def test_create_rule_as_verified_is_rejected():
    # A rule can never be born verified — the attempt is a hard 422.
    sb = SBStub(_world())
    r = TestClient(_build_app(sb)).post(
        f"/api/admin/exam-eligibility/exams/{EXAM_A}/rules",
        json={"scope": "general", "rule_type": "age_max", "value_num": 32,
              "source_url": "https://ssc.gov.in/", "reviewer_status": "verified"},
    )
    assert r.status_code == 422
    assert "cannot be created as 'verified'" in r.json()["detail"]


def test_create_rule_persists_page_locator():
    sb = SBStub(_world())
    r = TestClient(_build_app(sb)).post(
        f"/api/admin/exam-eligibility/exams/{EXAM_A}/rules",
        json={"scope": "general", "rule_type": "age_max", "value_num": 32,
              "source_document_id": "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
              "source_page_start": 3, "source_page_end": 5},
    )
    assert r.status_code == 200
    rule = r.json()["rule"]
    assert rule["source_page_start"] == 3
    assert rule["source_page_end"] == 5


def test_create_rule_rejects_half_page_locator():
    sb = SBStub(_world())
    r = TestClient(_build_app(sb)).post(
        f"/api/admin/exam-eligibility/exams/{EXAM_A}/rules",
        json={"scope": "general", "rule_type": "age_max", "value_num": 32,
              "source_page_start": 3},
    )
    assert r.status_code == 422
    assert "together" in r.json()["detail"]


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


def test_create_new_rule_type_lands_draft():
    # New rule_types are creatable, but (migration 256) always as draft — the
    # verified stamp only comes from the document-gated review path.
    sb = SBStub(_world())
    r = TestClient(_build_app(sb)).post(
        f"/api/admin/exam-eligibility/exams/{EXAM_A}/rules",
        json={"scope": "all", "rule_type": "discipline", "value_text": "LLB"},
    )
    assert r.status_code == 200
    assert r.json()["rule"]["reviewer_status"] == "draft"


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


def test_create_qualification_combination_rejects_experience_clause():
    # experience_min_years is cycle-only — not allowed in a baseline combo.
    sb = SBStub(_world())
    r = TestClient(_build_app(sb)).post(
        f"/api/admin/exam-eligibility/exams/{EXAM_A}/rules",
        json={"scope": "all", "rule_type": "qualification_combination",
              "value_json": {"op": "and", "clauses": [{"rule_type": "experience_min_years", "value_num": 3}]}},
    )
    assert r.status_code == 400


def test_create_draft_discipline_with_verified_percentage_sibling_is_allowed():
    # Creating a DRAFT discipline alongside a verified min_percentage is fine —
    # the ambiguous two-row protection fires only at verify time (in the review
    # RPC), not on draft authoring.
    world = _world()
    world["exam_eligibility_rules"].append({
        "id": "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee", "exam_id": EXAM_A, "stream_id": None,
        "scope": "all", "rule_type": "min_percentage", "value_num": 60, "reviewer_status": "verified",
    })
    sb = SBStub(world)
    r = TestClient(_build_app(sb)).post(
        f"/api/admin/exam-eligibility/exams/{EXAM_A}/rules",
        json={"scope": "all", "rule_type": "discipline", "value_text": "LLB"},
    )
    assert r.status_code == 200


def test_create_stream_availability_rejects_unknown_value():
    sb = SBStub(_world())
    r = TestClient(_build_app(sb)).post(
        f"/api/admin/exam-eligibility/exams/{EXAM_A}/rules",
        json={"scope": "all", "rule_type": "stream_availability", "value_text": "maybe"},
    )
    assert r.status_code == 400
    assert "offered" in r.json()["detail"]


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


def test_update_rule_cannot_promote_to_verified():
    # Generic update may not promote to verified — that transition is
    # document-gated and belongs to POST /rules/{id}/review (migration 256).
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
    assert r.status_code == 422
    assert "not allowed via update" in r.json()["detail"]
    updated = next(r for r in sb.db["exam_eligibility_rules"] if r["id"] == "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
    assert updated["reviewer_status"] == "draft"


def test_material_edit_demotes_verified_rule():
    # Editing a material field on a verified rule silently demotes it to draft
    # and clears the verification stamp.
    sb = SBStub(_world())  # RULE_A is verified (value_num=18)
    r = TestClient(_build_app(sb)).put(
        f"/api/admin/exam-eligibility/rules/{RULE_A}",
        json={"value_num": 19},
    )
    assert r.status_code == 200
    row = next(x for x in sb.db["exam_eligibility_rules"] if x["id"] == RULE_A)
    assert row["reviewer_status"] == "draft"
    assert row["verified_by"] is None
    assert row["verified_at"] is None
    assert row["value_num"] == 19


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


def test_create_rule_verified_is_always_422_regardless_of_source():
    # Neither a source_url nor a waiver can create a verified rule now — the
    # honour-system verification path is closed (migration 256).
    sb = SBStub(_world())
    for extra in (
        {},
        {"source_url": "https://ssc.gov.in/notice"},
        {"waiver_reason": "sourced from official press release"},
    ):
        r = TestClient(_build_app(sb)).post(
            f"/api/admin/exam-eligibility/exams/{EXAM_A}/rules",
            json={"scope": "general", "rule_type": "age_max", "value_num": 35,
                  "reviewer_status": "verified", **extra},
        )
        assert r.status_code == 422, extra


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


def test_update_rule_verify_with_waiver_reason_is_still_blocked():
    # Waiver-based verification is gone: even with a waiver_reason, generic
    # update cannot promote to verified (migration 256).
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
    assert r.status_code == 422


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
    sb.db["exam_eligibility_rules"].append(
        {
            "id": "ffffffff-ffff-4fff-8fff-ffffffffffff",
            "exam_id": EXAM_A, "scope": "st", "rule_type": "age_max",
            "value_num": 37, "reviewer_status": "draft",
        }
    )
    TestClient(_build_app(sb)).put(
        "/api/admin/exam-eligibility/rules/ffffffff-ffff-4fff-8fff-ffffffffffff",
        json={"value_num": 19},
    )
    logs = sb.db.get("admin_audit_logs", [])
    assert len(logs) == 1
    assert logs[0]["action"] == "eligibility_rule.update"
    assert logs[0]["entity_id"] == "ffffffff-ffff-4fff-8fff-ffffffffffff"
    assert logs[0]["old_value"] is not None


def test_update_rule_material_edit_demote_writes_demote_audit_log():
    sb = SBStub(_world())  # RULE_A is verified
    TestClient(_build_app(sb)).put(
        f"/api/admin/exam-eligibility/rules/{RULE_A}",
        json={"value_num": 20},
    )
    logs = sb.db.get("admin_audit_logs", [])
    assert len(logs) == 1
    assert logs[0]["action"] == "eligibility_rule.demote"


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
        },
    )
    logs = sb.db.get("admin_audit_logs", [])
    assert "sourced from official press release" in logs[0]["notes"]
