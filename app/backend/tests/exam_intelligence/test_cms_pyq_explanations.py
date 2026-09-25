"""CMS create / curate contract for PYQ question explanations (migration 230).

Migration 230 landed the table, its fail-closed verification guard and the
service_role review RPC, but no write path — so an authored explanation could
not be created at all. These tests pin the write path added here:

- rows are born ``reviewer_status='pending'`` and the route never sets verified;
- the field allowlist, enum vocabulary and FK checks match migration 230;
- ``unique (question_id, explanation_source_type)`` is one explanation per
  question PER SOURCE, so a second row under a different source type is
  ALLOWED (the coaching/official operator import path stays open) while a
  repeat of the same pair is a named 422;
- PATCH cannot move ``reviewer_status`` — promotion belongs to the review RPC.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intel_cms as cms_api
from app.core.auth import get_current_user
from tests.exam_intelligence.test_cms_taxonomy import TaxSBStub

_BASE = "/api/admin/exam-intelligence-cms"
_EXPL = f"{_BASE}/pyq-question-explanations"


def _cms_client(sb: TaxSBStub) -> TestClient:
    app = FastAPI()
    app.include_router(cms_api.router, prefix="/api")
    cms_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[cms_api._flag_enabled] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "admin-1", "role": "super_admin", "permissions": [cms_api.PERM_CMS],
    }
    return TestClient(app, raise_server_exceptions=False)


def _seed() -> dict:
    return {
        "exams": [{"id": "e1", "slug": "sebi-grade-a", "name": "SEBI Grade A", "is_active": True}],
        "pyq_papers": [{"id": "p1", "exam_id": "e1", "year": 2024}],
        "pyq_questions": [
            {"id": "q1", "pyq_paper_id": "p1", "reviewer_status": "verified"},
            {"id": "q2", "pyq_paper_id": "p1", "reviewer_status": "verified"},
        ],
        "pyq_options": [
            {"id": "o1", "question_id": "q1", "option_label": "A", "is_correct": True},
            {"id": "o2", "question_id": "q1", "option_label": "B", "is_correct": False},
            {"id": "o9", "question_id": "q2", "option_label": "A", "is_correct": True},
        ],
        "pyq_question_explanations": [],
    }


def _payload(**over) -> dict:
    row = {
        "question_id": "q1",
        "short_explanation": "Contribution is sales less variable cost.",
        "solution_steps": [],
        "option_rationales": {"o2": "Sales less fixed cost is not contribution."},
        "formula_used": [],
        "common_traps": [],
        "final_answer_option_id": "o1",
        "explanation_source_type": "platform_original",
        "license_status": "owned",
    }
    row.update(over)
    return row


# ── create lands pending ──────────────────────────────────────────────────


def test_create_explanation_lands_pending():
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).post(
        _EXPL, json={"reason": "authoring the SEBI explanation", "payload": _payload()},
    )
    assert r.status_code == 200, r.text
    row = sb.db["pyq_question_explanations"][0]
    assert row["reviewer_status"] == "pending"
    assert row["question_id"] == "q1"
    assert row["explanation_source_type"] == "platform_original"
    assert row["license_status"] == "owned"


def test_create_forces_pending_even_if_caller_sends_verified():
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).post(
        _EXPL,
        json={"reason": "trying to seed verified", "payload": _payload(reviewer_status="verified")},
    )
    assert r.status_code == 200, r.text
    assert sb.db["pyq_question_explanations"][0]["reviewer_status"] == "pending"


def test_create_defaults_source_type_to_platform_original():
    """Omitting the column relies on the DB default; the route writes it
    explicitly so the uniqueness probe and the insert agree."""
    sb = TaxSBStub(_seed())
    payload = _payload()
    payload.pop("explanation_source_type")
    r = _cms_client(sb).post(_EXPL, json={"reason": "no source type sent", "payload": payload})
    assert r.status_code == 200, r.text
    assert sb.db["pyq_question_explanations"][0]["explanation_source_type"] == "platform_original"


# ── allowlist ─────────────────────────────────────────────────────────────


def test_create_rejects_unknown_field():
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).post(
        _EXPL,
        json={"reason": "sending a worksheet-only field", "payload": _payload(draft_confidence="high")},
    )
    assert r.status_code == 422, r.text
    assert "draft_confidence" in str(r.json()["detail"])
    assert sb.db["pyq_question_explanations"] == []


def test_create_rejects_reviewer_owned_fields():
    """reviewed_by/reviewed_at are review-queue-owned and not in the create
    allowlist, so an attempt to stamp reviewer identity is rejected outright."""
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).post(
        _EXPL, json={"reason": "stamping reviewer identity", "payload": _payload(reviewed_by="admin-1")},
    )
    assert r.status_code == 422, r.text
    assert "reviewed_by" in str(r.json()["detail"])


# ── enum vocabulary (migration 230 CHECK constraints) ─────────────────────


def test_create_rejects_bad_ambiguity_status():
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).post(
        _EXPL, json={"reason": "bad ambiguity value", "payload": _payload(ambiguity_status="unclear")},
    )
    assert r.status_code == 422, r.text
    assert "ambiguity_status" in str(r.json()["detail"])


def test_create_rejects_bad_source_type():
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).post(
        _EXPL, json={"reason": "bad source type", "payload": _payload(explanation_source_type="authored")},
    )
    assert r.status_code == 422, r.text
    assert "explanation_source_type" in str(r.json()["detail"])


def test_create_rejects_bad_license_status():
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).post(
        _EXPL, json={"reason": "bad licence value", "payload": _payload(license_status="free")},
    )
    assert r.status_code == 422, r.text
    assert "license_status" in str(r.json()["detail"])


# ── jsonb container shapes ────────────────────────────────────────────────


def test_create_rejects_string_for_jsonb_array_column():
    """``formula_used`` is jsonb NOT NULL DEFAULT '[]'. Postgres would accept a
    bare string as valid jsonb, so the wrong container must be caught here."""
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).post(
        _EXPL,
        json={"reason": "worksheet emits a bare string", "payload": _payload(formula_used="Contribution = S - V")},
    )
    assert r.status_code == 422, r.text
    assert "formula_used must be a JSON array" in str(r.json()["detail"])


def test_create_rejects_array_for_jsonb_object_column():
    """``option_rationales`` is jsonb NOT NULL DEFAULT '{}' — an object."""
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).post(
        _EXPL,
        json={"reason": "worksheet emits an array here", "payload": _payload(
            option_rationales=[{"option_id": "o2", "rationale": "no"}])},
    )
    assert r.status_code == 422, r.text
    assert "option_rationales must be a JSON object" in str(r.json()["detail"])


# ── FK and same-question option integrity ─────────────────────────────────


def test_create_rejects_unknown_question_id():
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).post(
        _EXPL, json={"reason": "question does not exist", "payload": _payload(question_id="nope")},
    )
    assert r.status_code == 422, r.text
    assert "question_id does not resolve" in str(r.json()["detail"])
    assert sb.db["pyq_question_explanations"] == []


def test_create_requires_question_id():
    sb = TaxSBStub(_seed())
    payload = _payload()
    payload.pop("question_id")
    r = _cms_client(sb).post(_EXPL, json={"reason": "no question id at all", "payload": payload})
    assert r.status_code == 422, r.text
    assert "question_id is required" in str(r.json()["detail"])


def test_create_rejects_option_from_a_different_question():
    """Mirrors the same-question integrity trigger so the operator gets a named
    422 instead of a raw trigger exception surfaced as a 409."""
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).post(
        _EXPL, json={"reason": "option belongs to q2", "payload": _payload(final_answer_option_id="o9")},
    )
    assert r.status_code == 422, r.text
    assert "belongs to a different question" in str(r.json()["detail"])


# ── unique (question_id, explanation_source_type) ─────────────────────────


def test_create_rejects_duplicate_question_and_source_type():
    sb = TaxSBStub(_seed())
    client = _cms_client(sb)
    first = client.post(_EXPL, json={"reason": "first authored explanation", "payload": _payload()})
    assert first.status_code == 200, first.text

    second = client.post(_EXPL, json={"reason": "second attempt, same source", "payload": _payload()})
    assert second.status_code == 422, second.text
    detail = str(second.json()["detail"])
    assert "already exists" in detail
    assert "q1" in detail and "platform_original" in detail
    assert len(sb.db["pyq_question_explanations"]) == 1


def test_create_allows_second_explanation_under_a_different_source_type():
    """``unique (question_id, explanation_source_type)`` is deliberate: one
    explanation per question PER SOURCE. The coaching/official operator import
    path described in docs/architecture/pyq-explanations.md depends on a second
    row being creatable alongside the platform-authored one."""
    sb = TaxSBStub(_seed())
    client = _cms_client(sb)
    first = client.post(_EXPL, json={"reason": "platform authored row", "payload": _payload()})
    assert first.status_code == 200, first.text

    second = client.post(
        _EXPL,
        json={"reason": "imported reference explanation", "payload": _payload(
            explanation_source_type="coaching", license_status="permission_pending")},
    )
    assert second.status_code == 200, second.text
    rows = sb.db["pyq_question_explanations"]
    assert len(rows) == 2
    assert {r["explanation_source_type"] for r in rows} == {"platform_original", "coaching"}
    assert all(r["reviewer_status"] == "pending" for r in rows)


# ── PATCH cannot move reviewer_status ─────────────────────────────────────


def test_patch_cannot_move_reviewer_status():
    sb = TaxSBStub(_seed())
    client = _cms_client(sb)
    created = client.post(_EXPL, json={"reason": "row to curate later", "payload": _payload()})
    assert created.status_code == 200, created.text
    expl_id = sb.db["pyq_question_explanations"][0]["id"]

    r = client.patch(
        f"{_EXPL}/{expl_id}",
        json={"reason": "trying to self-verify", "payload": {"reviewer_status": "verified"}},
    )
    assert r.status_code == 422, r.text
    assert "reviewer_status" in str(r.json()["detail"])
    assert sb.db["pyq_question_explanations"][0]["reviewer_status"] == "pending"


def test_patch_cannot_reparent_question_id():
    """question_id is create-only: re-parenting would strand the answer option
    references, which the DB trigger proves against the original question."""
    sb = TaxSBStub(_seed())
    client = _cms_client(sb)
    client.post(_EXPL, json={"reason": "row to curate later", "payload": _payload()})
    expl_id = sb.db["pyq_question_explanations"][0]["id"]

    r = client.patch(
        f"{_EXPL}/{expl_id}", json={"reason": "moving to another question", "payload": {"question_id": "q2"}},
    )
    assert r.status_code == 422, r.text
    assert "question_id" in str(r.json()["detail"])
    assert sb.db["pyq_question_explanations"][0]["question_id"] == "q1"


def test_patch_updates_allowed_content_field():
    sb = TaxSBStub(_seed())
    client = _cms_client(sb)
    client.post(_EXPL, json={"reason": "row to curate later", "payload": _payload()})
    expl_id = sb.db["pyq_question_explanations"][0]["id"]

    r = client.patch(
        f"{_EXPL}/{expl_id}",
        json={"reason": "tightening the wording", "payload": {
            "short_explanation": "Contribution = sales - variable cost.",
            "common_traps": ["Subtracting fixed cost instead of variable cost."],
        }},
    )
    assert r.status_code == 200, r.text
    row = sb.db["pyq_question_explanations"][0]
    assert row["short_explanation"] == "Contribution = sales - variable cost."
    assert row["common_traps"] == ["Subtracting fixed cost instead of variable cost."]
    assert row["reviewer_status"] == "pending"


def test_patch_rejects_bad_enum_and_bad_shape():
    sb = TaxSBStub(_seed())
    client = _cms_client(sb)
    client.post(_EXPL, json={"reason": "row to curate later", "payload": _payload()})
    expl_id = sb.db["pyq_question_explanations"][0]["id"]

    bad_enum = client.patch(
        f"{_EXPL}/{expl_id}", json={"reason": "bad licence on patch", "payload": {"license_status": "free"}},
    )
    assert bad_enum.status_code == 422, bad_enum.text

    bad_shape = client.patch(
        f"{_EXPL}/{expl_id}", json={"reason": "bad shape on patch", "payload": {"solution_steps": "one step"}},
    )
    assert bad_shape.status_code == 422, bad_shape.text
    assert "solution_steps must be a JSON array" in str(bad_shape.json()["detail"])


def test_patch_unknown_explanation_is_404():
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).patch(
        f"{_EXPL}/missing", json={"reason": "row does not exist", "payload": {"short_explanation": "x"}},
    )
    assert r.status_code == 404, r.text


# ── bulk import ───────────────────────────────────────────────────────────


def test_bulk_import_explanations_lands_pending_with_per_row_errors():
    sb = TaxSBStub(_seed())
    rows = [
        _payload(),
        _payload(question_id="q2", final_answer_option_id="o9"),
        _payload(question_id="nope"),                      # FK failure
        _payload(question_id="q1", explanation_source_type="coaching", formula_used="oops"),  # shape failure
    ]
    r = _cms_client(sb).post(
        f"{_BASE}/bulk-import",
        json={"reason": "applying the authored worksheet", "entity": "pyq-question-explanations", "rows": rows},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok_count"] == 2
    assert body["error_count"] == 2
    assert len(sb.db["pyq_question_explanations"]) == 2
    assert all(row["reviewer_status"] == "pending" for row in sb.db["pyq_question_explanations"])
    errors = [res["error"] for res in body["results"] if not res["ok"]]
    assert any("question_id" in e for e in errors)
    assert any("formula_used must be a JSON array" in e for e in errors)


def test_bulk_import_rejects_duplicate_pair_within_the_same_batch():
    sb = TaxSBStub(_seed())
    r = _cms_client(sb).post(
        f"{_BASE}/bulk-import",
        json={"reason": "same question twice in one batch", "entity": "pyq-question-explanations",
              "rows": [_payload(), _payload()]},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok_count"] == 1
    assert body["error_count"] == 1
    assert "already exists" in str(body["results"][1]["error"])
    assert len(sb.db["pyq_question_explanations"]) == 1


# ── REG-CORPUS-02: authored rows keyed by mock_question_id (migration 310) ──


def _authored_seed() -> dict:
    seed = _seed()
    seed["mock_question_options"] = [
        {"id": "m1a", "question_id": "mq1", "option_index": 0, "is_correct": True},
        {"id": "m1b", "question_id": "mq1", "option_index": 1, "is_correct": False},
        {"id": "m2a", "question_id": "mq2", "option_index": 0, "is_correct": True},
    ]
    seed["pyq_question_explanations"] = [
        {"id": "x-pyq", "question_id": "q1", "reviewer_status": "pending",
         "explanation_source_type": "platform_original"},
        {"id": "x-auth", "mock_question_id": "mq1", "reviewer_status": "pending",
         "explanation_source_type": "platform_original", "final_answer_mock_option_id": "m1a"},
    ]
    return seed


def test_list_filters_authored_explanations_by_mock_question_id():
    sb = TaxSBStub(_authored_seed())
    r = _cms_client(sb).get(_EXPL, params={"mock_question_id": "mq1"})
    assert r.status_code == 200, r.text
    assert [row["id"] for row in r.json()["items"]] == ["x-auth"]


def test_patch_authored_answer_must_be_an_option_of_the_same_mock_question():
    sb = TaxSBStub(_authored_seed())
    client = _cms_client(sb)
    bad = client.patch(f"{_EXPL}/x-auth", json={
        "reason": "repointing the key option", "payload": {"final_answer_mock_option_id": "m2a"},
    })
    assert bad.status_code == 422
    assert "different question" in bad.json()["detail"]
    ok = client.patch(f"{_EXPL}/x-auth", json={
        "reason": "repointing the key option", "payload": {"final_answer_mock_option_id": "m1b"},
    })
    assert ok.status_code == 200, ok.text


def test_pyq_explanation_cannot_take_a_mock_option_answer():
    sb = TaxSBStub(_authored_seed())
    r = _cms_client(sb).patch(f"{_EXPL}/x-pyq", json={
        "reason": "wrong family of option", "payload": {"final_answer_mock_option_id": "m1a"},
    })
    assert r.status_code == 422
    assert "only valid on an explanation keyed to a mock question" in r.json()["detail"]
