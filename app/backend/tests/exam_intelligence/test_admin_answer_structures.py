"""Router tests for the answer-structure review queue and the learner routes.

The RPC behaviour (transitions, CAS, audit rows, one-verified demotion, RLS) is
proven against real Postgres in
tests/study_os/test_answer_structures_migration_behaviour.py. Here: the router
contract — permission gates, filters, the transition pre-check, the
reject-needs-note rule, edit validation, locked statuses, and the learner-side
submit gate.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_answer_structures as api
from app.api import descriptive_practice as learner_api
from app.core.auth import get_current_user, get_current_user_required_permanent
from app.study_os.answer_structure_schema import validate_structure

_BASE = "/api/admin/content-studio/answer-structures"
AUTHOR = api.PERM_AUTHOR
REVIEW = api.PERM_REVIEW
TOKEN = "2026-09-20T00:00:00Z"
SID = "00000000-0000-0000-0000-00000000a501"
SID2 = "00000000-0000-0000-0000-00000000a502"

_FIX = Path(__file__).resolve().parents[1] / "fixtures" / "answer_structures" / "responses.json"
GOOD = next(iter(json.loads(_FIX.read_text(encoding="utf-8")).values()))


class _Q:
    def __init__(self, db, name):
        self.db, self.name = db, name
        self.filters, self._update, self._range, self._limit = [], None, None, None

    def select(self, *a, **k):
        return self

    def eq(self, k, v):
        self.filters.append((k, lambda x, v=v: x == v))
        return self

    def neq(self, k, v):
        self.filters.append((k, lambda x, v=v: x != v))
        return self

    def in_(self, k, vs):
        vs = list(vs)
        self.filters.append((k, lambda x, vs=vs: x in vs))
        return self

    def order(self, *a, **k):
        return self

    def range(self, a, b):
        self._range = (a, b)
        return self

    def limit(self, n):
        self._limit = n
        return self

    def update(self, patch):
        self._update = patch
        return self

    def execute(self):
        rows = [r for r in self.db.setdefault(self.name, [])
                if all(f(r.get(k)) for k, f in self.filters)]
        if self._update is not None:
            for r in rows:
                r.update(self._update)
        if self._range:
            rows = rows[self._range[0]: self._range[1] + 1]
        if self._limit is not None:
            rows = rows[: self._limit]
        return type("R", (), {"data": [dict(r) for r in rows]})()


class Sb:
    def __init__(self, db):
        self.db = db
        self.rpc_calls: list[tuple[str, dict]] = []
        self.rpc_error: str | None = None

    def table(self, name):
        return _Q(self.db, name)

    def rpc(self, name, params):
        sb = self

        class _X:
            def execute(self):
                sb.rpc_calls.append((name, params))
                if sb.rpc_error:
                    raise RuntimeError(sb.rpc_error)
                return type("R", (), {"data": {"ok": True, "id": params.get("p_id")}})()

        return _X()


def _row(sid=SID, status="draft", question="q1", version=1, **over):
    r = {"id": sid, "pyq_question_id": question, "version": version, "status": status,
         **validate_structure(GOOD), "generated_by": "ai:claude-opus-5",
         "generation_meta": {}, "updated_at": TOKEN, "reviewed_at": None}
    r.update(over)
    return r


def _seed(*rows):
    return {
        "answer_structures": list(rows) or [_row()],
        "pyq_questions": [
            {"id": "q1", "pyq_paper_id": "p1", "question_text": "Governor question",
             "question_type": "descriptive", "reviewer_status": "verified",
             "metadata": {"marks": 15, "word_limit": 250}},
            {"id": "q2", "pyq_paper_id": "p2", "question_text": "Groundwater question",
             "question_type": "descriptive", "reviewer_status": "verified",
             "metadata": {"marks": 10}},
        ],
        "pyq_papers": [
            {"id": "p1", "year": 2023, "metadata": {"gs_paper": "2"}},
            {"id": "p2", "year": 2022, "metadata": {"gs_paper": "3"}},
        ],
        "admin_audit_logs": [
            {"id": "au1", "entity_type": "answer_structure", "entity_id": SID,
             "action": "answer_structure_draft_created", "created_at": TOKEN},
        ],
    }


def _client(sb, *, permissions=(REVIEW,), role="admin", anonymous=False):
    app = FastAPI()
    app.include_router(api.router, prefix="/api")
    api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[api._flag_enabled] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "op-1", "email": "op@example.com", "role": role,
        "permissions": list(permissions), "is_anonymous": anonymous,
    }
    return TestClient(app, raise_server_exceptions=False)


# ── gates ────────────────────────────────────────────────────────────────────


def test_queue_is_readable_by_content_roles_only():
    for perms, role, code in (([AUTHOR], "admin", 200), ([REVIEW], "admin", 200),
                              ([], "super_admin", 200), (["x.y"], "admin", 403)):
        r = _client(Sb(_seed()), permissions=perms, role=role).get(_BASE)
        assert r.status_code == code, (perms, r.text)


def test_review_requires_the_review_permission():
    sb = Sb(_seed())
    r = _client(sb, permissions=[AUTHOR]).post(f"{_BASE}/{SID}/review", json={
        "status": "verified", "expected_status": "draft", "expected_updated_at": TOKEN})
    assert r.status_code == 403 and sb.rpc_calls == []


# ── list filters ─────────────────────────────────────────────────────────────


def test_queue_filters_by_status_subject_paper_and_year():
    sb = Sb(_seed(_row(SID, "draft", "q1"), _row(SID2, "in_review", "q2")))
    c = _client(sb)
    assert {i["id"] for i in c.get(_BASE).json()["items"]} == {SID, SID2}
    assert [i["id"] for i in c.get(_BASE, params={"status": "in_review"}).json()["items"]] == [SID2]
    assert [i["id"] for i in c.get(_BASE, params={"paper": "gs2"}).json()["items"]] == [SID]
    assert [i["id"] for i in c.get(_BASE, params={"year": 2022}).json()["items"]] == [SID2]
    assert c.get(_BASE, params={"subject": "general studies"}).json()["total"] == 2
    facets = c.get(_BASE).json()["facets"]
    assert facets["papers"] == ["GS2", "GS3"] and facets["years"] == [2023, 2022]
    assert c.get(_BASE, params={"status": "bogus"}).status_code == 422


def test_detail_carries_question_versions_audit_and_allowed_decisions():
    body = _client(Sb(_seed())).get(f"{_BASE}/{SID}").json()
    assert body["question"]["text"] == "Governor question"
    assert body["question"]["paper"] == "GS2"
    assert body["allowed_transitions"] == ["in_review", "verified", "rejected"]
    assert body["editable"] is True
    assert body["audit"][0]["action"] == "answer_structure_draft_created"


# ── review ───────────────────────────────────────────────────────────────────


def test_approve_goes_through_the_rpc_with_the_clients_cas_token():
    sb = Sb(_seed())
    r = _client(sb).post(f"{_BASE}/{SID}/review", json={
        "status": "verified", "expected_status": "draft", "expected_updated_at": TOKEN})
    assert r.status_code == 200, r.text
    name, params = sb.rpc_calls[0]
    assert name == "cms_review_answer_structure"
    assert params["p_expected_updated_at"] == TOKEN and params["p_actor_user_id"] == "op-1"


def test_illegal_transitions_are_refused_before_the_rpc():
    sb = Sb(_seed())
    for exp, new in (("rejected", "verified"), ("verified", "draft"), ("draft", "draft")):
        r = _client(sb).post(f"{_BASE}/{SID}/review", json={
            "status": new, "expected_status": exp, "expected_updated_at": TOKEN})
        assert r.status_code == 422, (exp, new)
    assert sb.rpc_calls == []


def test_reject_requires_a_note():
    sb = Sb(_seed())
    r = _client(sb).post(f"{_BASE}/{SID}/review", json={
        "status": "rejected", "expected_status": "draft", "expected_updated_at": TOKEN,
        "review_notes": "   "})
    assert r.status_code == 422 and sb.rpc_calls == []
    r = _client(sb).post(f"{_BASE}/{SID}/review", json={
        "status": "rejected", "expected_status": "draft", "expected_updated_at": TOKEN,
        "review_notes": "Invents a committee."})
    assert r.status_code == 200
    assert sb.rpc_calls[0][1]["p_review_notes"] == "Invents a committee."


def test_rpc_errors_map_to_http():
    sb = Sb(_seed())
    for err, code in (("concurrent_modification: changed", 409),
                      ("transition_not_allowed: x", 422),
                      ("not_found: answer_structure", 404),
                      ('duplicate key value violates unique constraint "uq_answer_structures_one_verified"', 409)):
        sb.rpc_error = err
        r = _client(sb).post(f"{_BASE}/{SID}/review", json={
            "status": "verified", "expected_status": "draft", "expected_updated_at": TOKEN})
        assert r.status_code == code, (err, r.text)


# ── edit (edit-then-approve) ─────────────────────────────────────────────────


def _patch(sb, payload, perms=(REVIEW,), sid=SID):
    return _client(sb, permissions=perms).patch(f"{_BASE}/{sid}", json={
        "expected_updated_at": TOKEN, "reason": "tighten wording", "payload": payload})


def test_reviewer_can_edit_any_content_field():
    sb = Sb(_seed())
    points = copy.deepcopy(GOOD["body_points"])[:3]
    points[0]["point"] = "Sharper point"
    r = _patch(sb, {"demand": "A sharper demand line.", "body_points": points,
                    "pitfalls": ["Only criticism"]})
    assert r.status_code == 200, r.text
    name, params = sb.rpc_calls[0]
    assert name == "cms_update_answer_structure"
    assert set(params["p_patch"]) == {"demand", "body_points", "pitfalls"}
    assert params["p_patch"]["body_points"][0]["point"] == "Sharper point"


def test_an_edit_that_breaks_the_schema_is_refused():
    sb = Sb(_seed())
    r = _patch(sb, {"body_points": [{"id": "p1", "point": "only one"}]})
    assert r.status_code == 422 and "errors" in r.json()["detail"]
    assert sb.rpc_calls == []


def test_non_content_fields_are_not_editable():
    sb = Sb(_seed())
    for field in ("status", "generated_by", "reviewed_by", "version"):
        assert _patch(sb, {field: "x"}).status_code == 422
    assert sb.rpc_calls == []


def test_verified_and_rejected_structures_are_locked():
    for status in ("verified", "rejected"):
        sb = Sb(_seed(_row(status=status, review_notes="n")))
        r = _patch(sb, {"demand": "changed"})
        assert r.status_code == 422 and r.json()["detail"]["error"] == "structure_locked"
        assert sb.rpc_calls == []


def test_edit_needs_author_or_review():
    assert _patch(Sb(_seed()), {"demand": "x y z"}, perms=["exam_intelligence.manage"]).status_code == 403
    assert _patch(Sb(_seed()), {"demand": "x y z"}, perms=[AUTHOR]).status_code == 200


# ── regenerate ───────────────────────────────────────────────────────────────


def test_regenerate_writes_a_new_draft_version(monkeypatch):
    from app.study_os import answer_structure_generation as gen

    monkeypatch.setattr(gen, "AnthropicModelCall", lambda **k: (
        lambda system, user: gen.ModelReply(structure=GOOD, input_tokens=100, output_tokens=200)))
    sb = Sb(_seed(_row(status="verified", reviewed_by="u", reviewed_at=TOKEN)))
    r = _client(sb, permissions=[AUTHOR]).post(f"{_BASE}/{SID}/regenerate",
                                               json={"reason": "reviewer asked for a redo"})
    assert r.status_code == 200, r.text
    name, params = sb.rpc_calls[0]
    assert name == "cms_create_answer_structure_draft"
    assert params["p_question_id"] == "q1"
    assert params["p_payload"]["word_budget"]["total"] == 250
    # The verified version is untouched until the new draft is approved.
    assert sb.db["answer_structures"][0]["status"] == "verified"


def test_regenerate_without_a_key_is_a_503(monkeypatch):
    from app.study_os import answer_structure_generation as gen

    def _raise(**k):
        raise gen.FatalModelError("ANTHROPIC_API_KEY is not set")

    monkeypatch.setattr(gen, "AnthropicModelCall", _raise)
    sb = Sb(_seed())
    r = _client(sb, permissions=[AUTHOR]).post(f"{_BASE}/{SID}/regenerate",
                                               json={"reason": "reviewer asked for a redo"})
    assert r.status_code == 503 and sb.rpc_calls == []


# ── learner routes: the submit gate ──────────────────────────────────────────


def _learner(sb):
    app = FastAPI()
    app.include_router(learner_api.router, prefix="/api")
    learner_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    user = {"id": "me", "role": "user", "permissions": [], "is_anonymous": False}
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_user_required_permanent] = lambda: user
    return TestClient(app, raise_server_exceptions=False)


def _learner_seed(attempt_status):
    db = _seed(_row(status="verified", reviewed_by="u", reviewed_at=TOKEN))
    db["descriptive_attempts"] = [{
        "id": "a1", "user_id": "me", "pyq_question_id": "q1", "status": attempt_status,
        "answer_mode": "handwritten", "structure_version": None, "covered_point_ids": None,
    }]
    return db


def test_structure_route_is_409_before_submit_and_200_after():
    c = _learner(Sb(_learner_seed("draft")))
    r = c.get("/api/study/descriptive/attempts/a1/structure")
    assert r.status_code == 409 and r.json()["detail"]["code"] == "not_submitted"
    c = _learner(Sb(_learner_seed("submitted")))
    r = c.get("/api/study/descriptive/attempts/a1/structure")
    assert r.status_code == 200
    assert r.json()["structure"]["directive"] == GOOD["directive"]
    assert "generation_meta" not in r.json()["structure"]


def test_coverage_route_persists_ticks_for_a_handwritten_attempt():
    sb = Sb(_learner_seed("submitted"))
    r = _learner(sb).put("/api/study/descriptive/attempts/a1/coverage",
                         json={"structure_version": 1, "covered_point_ids": ["p2", "p1"]})
    assert r.status_code == 200, r.text
    assert r.json()["points_covered_pct"] == 40.0
    assert sb.db["descriptive_attempts"][0]["covered_point_ids"] == ["p1", "p2"]
