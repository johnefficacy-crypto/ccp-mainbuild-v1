"""Router-layer tests for Content Studio writing-prompt operations.

Covers the subject-scoped `/api/admin/content-studio` surface (migration 215 +
`app/api/content_studio.py`) at the FastAPI boundary — permission gating,
strict Pydantic validation, read filters, the reviewer-transition guard, and
RPC error-code → HTTP mapping. The atomic RPC *behaviour* (audit rows, CAS,
verified-lock, bulk lifecycle, scope validation) is proven against real
Postgres in ``tests/study_os/test_content_studio_ops_pg_behaviour.py``.

Key architecture facts enforced here:
  - content is SUBJECT-scoped (subject_id/topic_id/microtopic_id); there are NO
    exam columns on writing_prompts (migration 214 dropped them),
  - authoring/curation/bulk = content_studio.author; review = content_studio.review;
    reads = author OR review OR exam_intelligence.manage OR super_admin,
  - applicability (writing_prompt_targets / "Exam Assignments") = exam_intelligence.manage,
  - there is NO activate endpoint (activation is gated by migration 214).
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import content_studio as cs
from app.core.auth import get_current_user
from tests.persona_questions._stub import SBStub, _Exec, _Query

_BASE = "/api/admin/content-studio"
AUTHOR = cs.PERM_AUTHOR
REVIEW = cs.PERM_REVIEW
ASSIGN = cs.PERM_ASSIGN

_SUBJECT = "00000000-0000-0000-0000-0000000000a1"
_TOPIC = "00000000-0000-0000-0000-0000000000b1"
_MICRO = "00000000-0000-0000-0000-0000000000c1"
_PROMPT = "00000000-0000-0000-0000-0000000000d1"
_EXAM = "00000000-0000-0000-0000-0000000000e1"
_ABSENT = "00000000-0000-0000-0000-0000000000ff"  # valid UUID, not in seed
_TOKEN = "2026-07-01T00:00:00Z"  # matches the seeded prompt's updated_at (CAS token)
_TARGET = "00000000-0000-0000-0000-0000000000c2"  # a valid target UUID


class _CSQuery(_Query):
    """Adds ilike / range / count='exact' on the read path (like _MngQuery)."""

    def __init__(self, name, db):
        super().__init__(name, db)
        self._count_exact = False
        self._range = None

    def select(self, *args, **kwargs):
        if kwargs.get("count") == "exact":
            self._count_exact = True
        return self

    def ilike(self, key, pattern):
        self.filters.append((key, "ilike", str(pattern).strip("%").lower()))
        return self

    def range(self, lo, hi):
        self._range = (lo, hi)
        return self

    def execute(self):
        if (self._pending_insert is not None or self._pending_update is not None
                or self._pending_upsert is not None):
            return super().execute()
        ilikes = [(k, v) for (k, op, v) in self.filters if op == "ilike"]
        self.filters = [f for f in self.filters if f[1] != "ilike"]
        res = super().execute()
        data = list(res.data)
        for k, needle in ilikes:
            data = [r for r in data if isinstance(r.get(k), str) and needle in r[k].lower()]
        out = _Exec(data)
        if self._count_exact:
            out.count = len(data)
        if self._range:
            lo, hi = self._range
            out.data = data[lo:hi + 1]
        return out


class _CSRpc:
    """Records the call and returns a canned success dict, or raises a canned
    exception so the router's ``_map_rpc_error`` can be exercised."""

    def __init__(self, stub, fn_name, params):
        self._stub = stub
        self._fn_name = fn_name
        self._params = params

    def execute(self):
        self._stub.rpc_calls.append((self._fn_name, self._params))
        if self._stub.rpc_error is not None:
            raise RuntimeError(self._stub.rpc_error)
        return _Exec(self._stub.rpc_result if self._stub.rpc_result is not None
                     else {"ok": True, "audit_id": "aud-1", "prompt_id": _PROMPT})


class CSSBStub(SBStub):
    def __init__(self, db=None):
        super().__init__(db)
        self.rpc_calls: list[tuple[str, dict]] = []
        self.rpc_error: str | None = None
        self.rpc_result = None

    def table(self, name: str):
        return _CSQuery(name, self.db)

    def rpc(self, fn_name: str, params: dict | None = None):
        return _CSRpc(self, fn_name, params or {})


def _client(sb: CSSBStub, *, permissions=None, role="admin") -> TestClient:
    app = FastAPI()
    app.include_router(cs.router, prefix="/api")
    cs.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[cs._flag_enabled] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "op-1",
        "email": "op@example.com",
        "role": role,
        "permissions": permissions if permissions is not None else [AUTHOR],
        "is_anonymous": False,
    }
    return TestClient(app, raise_server_exceptions=False)


def _seed() -> dict:
    return {
        "writing_prompts": [
            {"id": _PROMPT, "subject_id": _SUBJECT, "topic_id": _TOPIC,
             "microtopic_id": None, "exercise_type": "sentence_construction",
             "prompt_text": "Write a sentence.", "difficulty_level": 1,
             "min_words": 5, "max_words": 20, "max_rewrite_attempts": 3,
             "reviewer_status": "pending", "is_active": False,
             "metadata": {}, "updated_at": "2026-07-01T00:00:00Z",
             "created_at": "2026-07-01T00:00:00Z"},
        ],
        "writing_prompt_targets": [],
        "admin_audit_logs": [],
    }


def _valid_payload(**over) -> dict:
    body = {"subject_id": _SUBJECT, "topic_id": _TOPIC,
            "exercise_type": "sentence_construction",
            "prompt_text": "Compose one grammatical sentence.",
            "difficulty_level": 3, "min_words": 5, "max_words": 30}
    body.update(over)
    return body


def _bulk_row(**over) -> dict:
    """A bulk row carries no subject_id (subject is body-level, idempotency scope)."""
    row = _valid_payload(**over)
    row.pop("subject_id", None)
    return row


# ── read permission gating ────────────────────────────────────────────────


def test_list_readable_by_author_review_manage_and_super_admin():
    for perms, role in (([AUTHOR], "admin"), ([REVIEW], "admin"),
                        ([ASSIGN], "admin"), ([], "super_admin")):
        sb = CSSBStub(_seed())
        r = _client(sb, permissions=perms, role=role).get(f"{_BASE}/writing-prompts")
        assert r.status_code == 200, (perms, role, r.text)


def test_list_denied_without_any_content_permission():
    sb = CSSBStub(_seed())
    r = _client(sb, permissions=["some.other"]).get(f"{_BASE}/writing-prompts")
    assert r.status_code == 403


def test_list_denied_for_anonymous():
    sb = CSSBStub(_seed())
    r = _client(sb, permissions=[AUTHOR], role="user").get(f"{_BASE}/writing-prompts")
    # role user with author perm passes; flip to anonymous:
    app = FastAPI()
    app.include_router(cs.router, prefix="/api")
    cs.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[cs._flag_enabled] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "anon", "role": "user", "permissions": [AUTHOR], "is_anonymous": True}
    r2 = TestClient(app, raise_server_exceptions=False).get(f"{_BASE}/writing-prompts")
    assert r.status_code == 200 and r2.status_code == 403


# ── read filters ──────────────────────────────────────────────────────────


def test_list_filters_by_subject_and_status():
    seed = _seed()
    seed["writing_prompts"].append(
        {"id": "p2", "subject_id": "other", "topic_id": _TOPIC,
         "exercise_type": "sentence_correction", "prompt_text": "x",
         "difficulty_level": 1, "reviewer_status": "verified", "is_active": True,
         "metadata": {}, "created_at": "2026-07-02T00:00:00Z"})
    sb = CSSBStub(seed)
    r = _client(sb).get(f"{_BASE}/writing-prompts?subject_id={_SUBJECT}&reviewer_status=pending")
    assert r.status_code == 200, r.text
    ids = {p["id"] for p in r.json()["items"]}
    assert ids == {_PROMPT}


def test_list_text_search_matches_prompt_text():
    sb = CSSBStub(_seed())
    r = _client(sb).get(f"{_BASE}/writing-prompts?q=grammat")
    assert r.status_code == 200, r.text
    assert r.json()["items"] == []  # seeded prompt_text has no 'grammat'
    r2 = _client(sb).get(f"{_BASE}/writing-prompts?q=sentence")
    assert {p["id"] for p in r2.json()["items"]} == {_PROMPT}


def test_get_returns_404_when_absent():
    sb = CSSBStub(_seed())
    r = _client(sb).get(f"{_BASE}/writing-prompts/{_ABSENT}")
    assert r.status_code == 404


def test_get_malformed_uuid_is_422_not_404():
    # UUID path typing must produce a controlled 422 at the boundary, not a
    # _safe_select-swallowed 404 nor an unmapped 500.
    sb = CSSBStub(_seed())
    r = _client(sb).get(f"{_BASE}/writing-prompts/not-a-uuid")
    assert r.status_code == 422


def test_list_malformed_uuid_filter_is_422():
    sb = CSSBStub(_seed())
    r = _client(sb).get(f"{_BASE}/writing-prompts?subject_id=not-a-uuid")
    assert r.status_code == 422


def test_get_returns_prompt():
    sb = CSSBStub(_seed())
    r = _client(sb).get(f"{_BASE}/writing-prompts/{_PROMPT}")
    assert r.status_code == 200, r.text
    assert r.json()["id"] == _PROMPT


# ── create: permission + strict validation ────────────────────────────────


def test_create_denied_without_author():
    sb = CSSBStub(_seed())
    r = _client(sb, permissions=[REVIEW]).post(
        f"{_BASE}/writing-prompts",
        json={"reason": "add a prompt", "payload": _valid_payload()})
    assert r.status_code == 403


def test_create_happy_path_calls_rpc():
    sb = CSSBStub(_seed())
    r = _client(sb).post(
        f"{_BASE}/writing-prompts",
        json={"reason": "add a canonical prompt", "payload": _valid_payload()})
    assert r.status_code == 200, r.text
    assert sb.rpc_calls and sb.rpc_calls[-1][0] == "cms_create_writing_prompt"
    sent = sb.rpc_calls[-1][1]["p_payload"]
    assert sent["subject_id"] == _SUBJECT and "id" not in sent


def test_create_rejects_unknown_field():
    sb = CSSBStub(_seed())
    r = _client(sb).post(
        f"{_BASE}/writing-prompts",
        json={"reason": "sneak an extra field", "payload": _valid_payload(exam_id=_EXAM)})
    assert r.status_code == 422
    assert not sb.rpc_calls


def test_create_rejects_explicit_null_on_not_null_column():
    sb = CSSBStub(_seed())
    r = _client(sb).post(
        f"{_BASE}/writing-prompts",
        json={"reason": "explicit null topic", "payload": _valid_payload(topic_id=None)})
    assert r.status_code == 422
    assert not sb.rpc_calls


def test_create_rejects_max_words_below_min():
    sb = CSSBStub(_seed())
    r = _client(sb).post(
        f"{_BASE}/writing-prompts",
        json={"reason": "invalid word bounds", "payload": _valid_payload(min_words=30, max_words=10)})
    assert r.status_code == 422
    assert not sb.rpc_calls


def test_create_requires_subject_id():
    sb = CSSBStub(_seed())
    payload = _valid_payload()
    payload.pop("subject_id")
    r = _client(sb).post(f"{_BASE}/writing-prompts",
                         json={"reason": "missing subject", "payload": payload})
    assert r.status_code == 422


# ── create: reserved metadata + required-word / prompt-text canonicalization ──


def test_create_rejects_reserved_external_key_in_metadata():
    sb = CSSBStub(_seed())
    r = _client(sb).post(
        f"{_BASE}/writing-prompts",
        json={"reason": "claim an import key", "payload": _valid_payload(metadata={"external_key": "x"})})
    assert r.status_code == 422
    assert not sb.rpc_calls


def test_create_rejects_exam_scope_keys_in_metadata():
    # exam_id/exam_cycle_id/exam_phase_id in metadata would reopen the dual-authority
    # backdoor migration 214 closed — reject them at the boundary.
    for key in ("exam_id", "exam_cycle_id", "exam_phase_id"):
        sb = CSSBStub(_seed())
        r = _client(sb).post(
            f"{_BASE}/writing-prompts",
            json={"reason": "smuggle exam scope", "payload": _valid_payload(metadata={key: _EXAM})})
        assert r.status_code == 422, key
        assert not sb.rpc_calls


def test_create_rejects_blank_prompt_text():
    sb = CSSBStub(_seed())
    r = _client(sb).post(
        f"{_BASE}/writing-prompts",
        json={"reason": "whitespace prompt text", "payload": _valid_payload(prompt_text="   ")})
    assert r.status_code == 422


def test_create_rejects_invalid_required_words():
    sb = CSSBStub(_seed())
    for bad in (["", "ok"], ["  "], ["two words"], ["Policy", "policy"], ["hi!"]):
        r = _client(sb).post(
            f"{_BASE}/writing-prompts",
            json={"reason": "bad required words", "payload": _valid_payload(required_words=bad)})
        assert r.status_code == 422, bad
    assert not sb.rpc_calls


def test_create_canonicalizes_required_words():
    sb = CSSBStub(_seed())
    r = _client(sb).post(
        f"{_BASE}/writing-prompts",
        json={"reason": "trim required words", "payload": _valid_payload(required_words=["  Ran  ", "quick-fix"])})
    assert r.status_code == 200, r.text
    assert sb.rpc_calls[-1][1]["p_payload"]["required_words"] == ["Ran", "quick-fix"]


# ── patch: merged word-bound validation + verified-lock mapping + client CAS ──


def test_patch_requires_expected_updated_at_token():
    sb = CSSBStub(_seed())
    r = _client(sb).patch(
        f"{_BASE}/writing-prompts/{_PROMPT}",
        json={"reason": "no CAS token", "payload": {"difficulty_level": 4}})
    assert r.status_code == 422
    assert not sb.rpc_calls


def test_patch_passes_client_token_unchanged():
    # The router must pass the CLIENT's token, not a server-read fresh one.
    sb = CSSBStub(_seed())
    r = _client(sb).patch(
        f"{_BASE}/writing-prompts/{_PROMPT}",
        json={"reason": "edit difficulty", "expected_updated_at": "2020-01-01T00:00:00Z",
              "payload": {"difficulty_level": 4}})
    assert r.status_code == 200, r.text
    assert sb.rpc_calls[-1][1]["p_expected_updated_at"] == "2020-01-01T00:00:00Z"


def test_patch_rejects_reserved_external_key():
    sb = CSSBStub(_seed())
    r = _client(sb).patch(
        f"{_BASE}/writing-prompts/{_PROMPT}",
        json={"reason": "drop the import key", "expected_updated_at": _TOKEN,
              "payload": {"metadata": {"external_key": "y"}}})
    assert r.status_code == 422
    assert not sb.rpc_calls


def test_patch_merged_min_max_validation_uses_stored_values():
    sb = CSSBStub(_seed())
    r = _client(sb).patch(
        f"{_BASE}/writing-prompts/{_PROMPT}",
        json={"reason": "shrink max below stored min", "expected_updated_at": _TOKEN,
              "payload": {"max_words": 3}})
    assert r.status_code == 422
    assert not sb.rpc_calls


def test_patch_empty_payload_rejected():
    sb = CSSBStub(_seed())
    r = _client(sb).patch(f"{_BASE}/writing-prompts/{_PROMPT}",
                          json={"reason": "no fields at all", "expected_updated_at": _TOKEN, "payload": {}})
    assert r.status_code == 422


def test_patch_404_when_prompt_absent():
    sb = CSSBStub(_seed())
    r = _client(sb).patch(f"{_BASE}/writing-prompts/{_ABSENT}",
                          json={"reason": "patch a ghost", "expected_updated_at": _TOKEN,
                                "payload": {"difficulty_level": 4}})
    assert r.status_code == 404


def test_patch_malformed_uuid_is_422_not_404():
    sb = CSSBStub(_seed())
    r = _client(sb).patch(f"{_BASE}/writing-prompts/not-a-uuid",
                          json={"reason": "malformed id", "expected_updated_at": _TOKEN,
                                "payload": {"difficulty_level": 4}})
    assert r.status_code == 422
    assert not sb.rpc_calls


def test_patch_maps_verified_locked_to_422():
    sb = CSSBStub(_seed())
    sb.rpc_error = "prompt_verified_locked: demote via review first"
    r = _client(sb).patch(f"{_BASE}/writing-prompts/{_PROMPT}",
                          json={"reason": "edit a verified prompt", "expected_updated_at": _TOKEN,
                                "payload": {"difficulty_level": 4}})
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "prompt_verified_locked"


def test_patch_maps_concurrent_modification_to_409():
    sb = CSSBStub(_seed())
    sb.rpc_error = "concurrent_modification: prompt changed since read"
    r = _client(sb).patch(f"{_BASE}/writing-prompts/{_PROMPT}",
                          json={"reason": "stale write attempt", "expected_updated_at": _TOKEN,
                                "payload": {"difficulty_level": 4}})
    assert r.status_code == 409


# ── review: transition guard + permission + client CAS ────────────────────


def _review_body(**over) -> dict:
    body = {"status": "verified", "expected_status": "pending",
            "expected_updated_at": _TOKEN, "reason": "content looks correct"}
    body.update(over)
    return body


def test_review_denied_without_review_permission():
    sb = CSSBStub(_seed())
    r = _client(sb, permissions=[AUTHOR]).post(
        f"{_BASE}/writing-prompts/{_PROMPT}/review", json=_review_body(reason="author cannot review"))
    assert r.status_code == 403


def test_review_requires_cas_fields():
    sb = CSSBStub(_seed())
    r = _client(sb, permissions=[REVIEW]).post(
        f"{_BASE}/writing-prompts/{_PROMPT}/review",
        json={"status": "verified", "reason": "no CAS fields at all"})
    assert r.status_code == 422
    assert not sb.rpc_calls


def test_review_rejects_unknown_status():
    sb = CSSBStub(_seed())
    r = _client(sb, permissions=[REVIEW]).post(
        f"{_BASE}/writing-prompts/{_PROMPT}/review", json=_review_body(status="published"))
    assert r.status_code == 422
    assert not sb.rpc_calls


def test_review_rejects_disallowed_transition_by_client_expected_status():
    sb = CSSBStub(_seed())
    r = _client(sb, permissions=[REVIEW]).post(
        f"{_BASE}/writing-prompts/{_PROMPT}/review",
        json=_review_body(status="verified", expected_status="rejected", reason="rejected is terminal"))
    assert r.status_code == 422
    assert not sb.rpc_calls


def test_review_happy_path_passes_client_tokens_unchanged():
    sb = CSSBStub(_seed())
    r = _client(sb, permissions=[REVIEW]).post(
        f"{_BASE}/writing-prompts/{_PROMPT}/review",
        json=_review_body(expected_status="pending", expected_updated_at="2019-05-05T00:00:00Z"))
    assert r.status_code == 200, r.text
    assert sb.rpc_calls[-1][0] == "cms_review_writing_prompt"
    assert sb.rpc_calls[-1][1]["p_expected_status"] == "pending"
    assert sb.rpc_calls[-1][1]["p_expected_updated_at"] == "2019-05-05T00:00:00Z"


def test_review_404_when_prompt_absent_from_rpc():
    sb = CSSBStub(_seed())
    sb.rpc_error = "not_found: writing_prompt does not exist"
    r = _client(sb, permissions=[REVIEW]).post(
        f"{_BASE}/writing-prompts/{_ABSENT}/review", json=_review_body())
    assert r.status_code == 404


# ── bulk import ───────────────────────────────────────────────────────────


def test_bulk_requires_external_key_per_row():
    sb = CSSBStub(_seed())
    r = _client(sb).post(
        f"{_BASE}/writing-prompts/bulk",
        json={"reason": "import without keys", "subject_id": _SUBJECT,
              "rows": [_bulk_row()]})
    assert r.status_code == 422
    assert not sb.rpc_calls


def test_bulk_happy_path_passes_subject_and_rows():
    sb = CSSBStub(_seed())
    sb.rpc_result = {"ok": True, "created": 2, "updated": 0, "unchanged": 0}
    rows = [_bulk_row(external_key="ek-1"),
            _bulk_row(external_key="ek-2", prompt_text="Another sentence here.")]
    r = _client(sb).post(
        f"{_BASE}/writing-prompts/bulk",
        json={"reason": "seed two prompts", "subject_id": _SUBJECT, "rows": rows})
    assert r.status_code == 200, r.text
    call = sb.rpc_calls[-1]
    assert call[0] == "cms_bulk_upsert_writing_prompts"
    assert call[1]["p_subject_id"] == _SUBJECT
    assert len(call[1]["p_rows"]) == 2


def test_bulk_rejects_unknown_field_in_row():
    sb = CSSBStub(_seed())
    r = _client(sb).post(
        f"{_BASE}/writing-prompts/bulk",
        json={"reason": "row with exam column", "subject_id": _SUBJECT,
              "rows": [_bulk_row(external_key="ek-1", exam_id=_EXAM)]})
    assert r.status_code == 422


def test_bulk_maps_locked_row_to_422():
    sb = CSSBStub(_seed())
    sb.rpc_error = "bulk_locked_row: external_key ek-1 is verified"
    r = _client(sb).post(
        f"{_BASE}/writing-prompts/bulk",
        json={"reason": "reimport onto verified", "subject_id": _SUBJECT,
              "rows": [_bulk_row(external_key="ek-1")]})
    assert r.status_code == 422


# ── Exam Assignments (writing_prompt_targets) — J2 propose/review/remove split ─
#
# manage (exam_intelligence.manage) PROPOSES inert pending_review; review
# (exam_intelligence.review) PROMOTES to active|excluded and removes.

ASSIGN_REVIEW = cs.PERM_ASSIGN_REVIEW


def test_propose_target_requires_manage_permission():
    sb = CSSBStub(_seed())
    r = _client(sb, permissions=[AUTHOR]).post(
        f"{_BASE}/writing-prompts/{_PROMPT}/targets",
        json={"reason": "author cannot assign", "is_global": True})
    assert r.status_code == 403


def test_propose_target_happy_path_calls_propose_rpc():
    sb = CSSBStub(_seed())
    sb.rpc_result = {"ok": True, "target_id": "t-1"}
    r = _client(sb, permissions=[ASSIGN]).post(
        f"{_BASE}/writing-prompts/{_PROMPT}/targets",
        json={"reason": "propose a global assignment", "is_global": True})
    assert r.status_code == 200, r.text
    assert sb.rpc_calls[-1][0] == "cms_propose_writing_prompt_target"
    assert sb.rpc_calls[-1][1]["p_is_global"] is True
    # manage cannot smuggle an effective status — no p_status param exists.
    assert "p_status" not in sb.rpc_calls[-1][1]


def test_propose_target_rejects_applicability_status_field():
    # manage may not set an effective status even by sending the field.
    sb = CSSBStub(_seed())
    r = _client(sb, permissions=[ASSIGN]).post(
        f"{_BASE}/writing-prompts/{_PROMPT}/targets",
        json={"reason": "try to activate directly", "is_global": True,
              "applicability_status": "active"})
    assert r.status_code == 422
    assert not sb.rpc_calls


def test_propose_target_maps_duplicate_to_409():
    sb = CSSBStub(_seed())
    sb.rpc_error = "target_exists: an assignment for this (prompt, scope) already exists"
    r = _client(sb, permissions=[ASSIGN]).post(
        f"{_BASE}/writing-prompts/{_PROMPT}/targets",
        json={"reason": "duplicate scope proposal", "is_global": True})
    assert r.status_code == 409


def test_review_target_requires_review_permission():
    # manage may propose but NOT promote to effective.
    sb = CSSBStub(_seed())
    r = _client(sb, permissions=[ASSIGN]).post(
        f"{_BASE}/writing-prompt-targets/{_TARGET}/review",
        json={"reason": "manage cannot activate", "applicability_status": "active",
              "expected_updated_at": _TOKEN})
    assert r.status_code == 403


def test_review_target_happy_path_calls_review_rpc():
    sb = CSSBStub(_seed())
    sb.rpc_result = {"ok": True, "target_id": "t-1"}
    r = _client(sb, permissions=[ASSIGN_REVIEW]).post(
        f"{_BASE}/writing-prompt-targets/{_TARGET}/review",
        json={"reason": "promote to active", "applicability_status": "active",
              "expected_updated_at": _TOKEN})
    assert r.status_code == 200, r.text
    assert sb.rpc_calls[-1][0] == "cms_review_writing_prompt_target"
    assert sb.rpc_calls[-1][1]["p_expected_updated_at"] == _TOKEN
    assert sb.rpc_calls[-1][1]["p_new_status"] == "active"


def test_review_target_rejects_pending_review_status():
    # review may only set active|excluded (Literal) — pending_review is rejected.
    sb = CSSBStub(_seed())
    r = _client(sb, permissions=[ASSIGN_REVIEW]).post(
        f"{_BASE}/writing-prompt-targets/{_TARGET}/review",
        json={"reason": "cannot set pending", "applicability_status": "pending_review",
              "expected_updated_at": _TOKEN})
    assert r.status_code == 422
    assert not sb.rpc_calls


def test_review_target_requires_cas_token():
    sb = CSSBStub(_seed())
    r = _client(sb, permissions=[ASSIGN_REVIEW]).post(
        f"{_BASE}/writing-prompt-targets/{_TARGET}/review",
        json={"reason": "no CAS token supplied", "applicability_status": "active"})
    assert r.status_code == 422
    assert not sb.rpc_calls


def test_review_target_maps_invalid_scope_to_422():
    # global + excluded is rejected by the RPC.
    sb = CSSBStub(_seed())
    sb.rpc_error = "invalid_scope: a global assignment cannot be excluded"
    r = _client(sb, permissions=[ASSIGN_REVIEW]).post(
        f"{_BASE}/writing-prompt-targets/{_TARGET}/review",
        json={"reason": "exclude a global row", "applicability_status": "excluded",
              "expected_updated_at": _TOKEN})
    assert r.status_code == 422


def test_list_targets_readable_by_content_reader():
    seed = _seed()
    seed["writing_prompt_targets"].append(
        {"id": "t-1", "prompt_id": _PROMPT, "is_global": True,
         "applicability_status": "active", "created_at": "2026-07-01T00:00:00Z"})
    sb = CSSBStub(seed)
    r = _client(sb, permissions=[REVIEW]).get(f"{_BASE}/writing-prompts/{_PROMPT}/targets")
    assert r.status_code == 200, r.text
    assert {t["id"] for t in r.json()["items"]} == {"t-1"}


def test_remove_target_requires_review_permission():
    sb = CSSBStub(_seed())
    r = _client(sb, permissions=[ASSIGN]).post(
        f"{_BASE}/writing-prompt-targets/{_TARGET}/remove",
        json={"reason": "manage cannot remove effective", "expected_updated_at": _TOKEN})
    assert r.status_code == 403


def test_remove_target_requires_cas_token():
    sb = CSSBStub(_seed())
    r = _client(sb, permissions=[ASSIGN_REVIEW]).post(
        f"{_BASE}/writing-prompt-targets/{_TARGET}/remove",
        json={"reason": "no CAS token supplied"})
    assert r.status_code == 422
    assert not sb.rpc_calls


def test_remove_target_maps_not_found_to_404():
    sb = CSSBStub(_seed())
    sb.rpc_error = "not_found: writing_prompt_target does not exist"
    r = _client(sb, permissions=[ASSIGN_REVIEW]).post(
        f"{_BASE}/writing-prompt-targets/{_ABSENT}/remove",
        json={"reason": "removing a ghost target", "expected_updated_at": _TOKEN})
    assert r.status_code == 404


# ── RPC error mapping through a REAL postgrest APIError (not just canned str) ──


def test_map_rpc_error_handles_real_postgrest_apierror():
    """The claimed ERRCODE→HTTP mapping must hold for the actual exception type
    supabase-py raises, not only bare RuntimeError strings."""
    from postgrest.exceptions import APIError

    cases = {
        "concurrent_modification: prompt changed since read": 409,
        "prompt_verified_locked: demote via review first": 422,
        "invalid_scope: subject must be english-language": 422,
        "target_exists: an assignment already exists": 409,
        "not_found: writing_prompt does not exist": 404,
    }
    for message, expected in cases.items():
        err = APIError({"code": "P0", "message": message, "details": None, "hint": None})
        mapped = cs._map_rpc_error(err, "unit")
        assert mapped.status_code == expected, (message, mapped.status_code)


# ── Activation lifecycle (migration 224) — content_studio.activate authority ──
#
# Activation is a SEPARATE, higher-trust permission. Neither author nor review
# may activate. The RPC is the SOLE eligibility authority: a blocked activation
# is a NORMAL 200 {eligible:false, blockers} answer; CAS mismatch → 409.

ACTIVATE = cs.PERM_ACTIVATE


def test_activate_route_is_registered():
    paths = {r.path for r in cs.router.routes}
    assert any(p.endswith("/activate") for p in paths)
    assert any(p.endswith("/deactivate") for p in paths)


def _activate_body(**over) -> dict:
    body = {"reason": "content is verified and assigned", "expected_updated_at": _TOKEN}
    body.update(over)
    return body


def test_activate_denied_for_author():
    sb = CSSBStub(_seed())
    r = _client(sb, permissions=[AUTHOR]).post(
        f"{_BASE}/writing-prompts/{_PROMPT}/activate", json=_activate_body())
    assert r.status_code == 403
    assert not sb.rpc_calls


def test_activate_denied_for_reviewer():
    sb = CSSBStub(_seed())
    r = _client(sb, permissions=[REVIEW]).post(
        f"{_BASE}/writing-prompts/{_PROMPT}/activate", json=_activate_body())
    assert r.status_code == 403
    assert not sb.rpc_calls


def test_activate_allowed_for_activate_permission_and_super_admin():
    for perms, role in (([ACTIVATE], "admin"), ([], "super_admin")):
        sb = CSSBStub(_seed())
        sb.rpc_result = {"eligible": True, "ok": True, "prompt_id": _PROMPT, "is_active": True}
        r = _client(sb, permissions=perms, role=role).post(
            f"{_BASE}/writing-prompts/{_PROMPT}/activate", json=_activate_body())
        assert r.status_code == 200, (perms, role, r.text)
        assert sb.rpc_calls[-1][0] == "cms_activate_writing_prompt"


def test_activate_requires_cas_token():
    sb = CSSBStub(_seed())
    r = _client(sb, permissions=[ACTIVATE]).post(
        f"{_BASE}/writing-prompts/{_PROMPT}/activate", json={"reason": "no CAS token here"})
    assert r.status_code == 422
    assert not sb.rpc_calls


def test_activate_requires_reason_min_length():
    sb = CSSBStub(_seed())
    r = _client(sb, permissions=[ACTIVATE]).post(
        f"{_BASE}/writing-prompts/{_PROMPT}/activate",
        json={"reason": "short", "expected_updated_at": _TOKEN})
    assert r.status_code == 422
    assert not sb.rpc_calls


def test_activate_rejects_unknown_field():
    sb = CSSBStub(_seed())
    r = _client(sb, permissions=[ACTIVATE]).post(
        f"{_BASE}/writing-prompts/{_PROMPT}/activate",
        json=_activate_body(is_active=True))
    assert r.status_code == 422
    assert not sb.rpc_calls


def test_activate_passes_client_token_and_omits_runtime_allowlist():
    # The API must NOT widen the server-owned runtime allowlist.
    sb = CSSBStub(_seed())
    sb.rpc_result = {"eligible": True, "ok": True, "prompt_id": _PROMPT, "is_active": True}
    r = _client(sb, permissions=[ACTIVATE]).post(
        f"{_BASE}/writing-prompts/{_PROMPT}/activate",
        json=_activate_body(expected_updated_at="2019-01-01T00:00:00Z"))
    assert r.status_code == 200, r.text
    call = sb.rpc_calls[-1][1]
    assert call["p_expected_updated_at"] == "2019-01-01T00:00:00Z"
    assert "p_exercise_runtime_allowlist" not in call


def test_activate_eligibility_blocked_is_200_with_blockers():
    # A blocked activation is a NORMAL answer (not an error). The router surfaces
    # the RPC's {eligible:false, blockers} verdict verbatim at HTTP 200.
    sb = CSSBStub(_seed())
    sb.rpc_result = {"eligible": False, "prompt_id": _PROMPT,
                     "blockers": ["prompt_not_verified", "no_active_applicability_target"]}
    r = _client(sb, permissions=[ACTIVATE]).post(
        f"{_BASE}/writing-prompts/{_PROMPT}/activate", json=_activate_body())
    assert r.status_code == 200, r.text
    res = r.json()["result"]
    assert res["eligible"] is False
    assert set(res["blockers"]) == {"prompt_not_verified", "no_active_applicability_target"}


def test_activate_maps_stale_cas_to_409():
    sb = CSSBStub(_seed())
    sb.rpc_error = "concurrent_modification: stale_prompt — prompt changed since read"
    r = _client(sb, permissions=[ACTIVATE]).post(
        f"{_BASE}/writing-prompts/{_PROMPT}/activate", json=_activate_body())
    assert r.status_code == 409


def test_activate_maps_not_found_to_404():
    sb = CSSBStub(_seed())
    sb.rpc_error = "not_found: writing_prompt does not exist"
    r = _client(sb, permissions=[ACTIVATE]).post(
        f"{_BASE}/writing-prompts/{_ABSENT}/activate", json=_activate_body())
    assert r.status_code == 404


def test_activate_malformed_uuid_is_422():
    sb = CSSBStub(_seed())
    r = _client(sb, permissions=[ACTIVATE]).post(
        f"{_BASE}/writing-prompts/not-a-uuid/activate", json=_activate_body())
    assert r.status_code == 422
    assert not sb.rpc_calls


def test_deactivate_denied_for_author_and_reviewer():
    for perms in ([AUTHOR], [REVIEW]):
        sb = CSSBStub(_seed())
        r = _client(sb, permissions=perms).post(
            f"{_BASE}/writing-prompts/{_PROMPT}/deactivate", json=_activate_body())
        assert r.status_code == 403, perms
        assert not sb.rpc_calls


def test_deactivate_happy_path_passes_client_token():
    sb = CSSBStub(_seed())
    sb.rpc_result = {"ok": True, "prompt_id": _PROMPT, "is_active": False}
    r = _client(sb, permissions=[ACTIVATE]).post(
        f"{_BASE}/writing-prompts/{_PROMPT}/deactivate",
        json=_activate_body(reason="retire this prompt", expected_updated_at="2018-01-01T00:00:00Z"))
    assert r.status_code == 200, r.text
    assert sb.rpc_calls[-1][0] == "cms_deactivate_writing_prompt"
    assert sb.rpc_calls[-1][1]["p_expected_updated_at"] == "2018-01-01T00:00:00Z"


def test_deactivate_requires_cas_token():
    sb = CSSBStub(_seed())
    r = _client(sb, permissions=[ACTIVATE]).post(
        f"{_BASE}/writing-prompts/{_PROMPT}/deactivate", json={"reason": "no CAS token here"})
    assert r.status_code == 422
    assert not sb.rpc_calls


# ── Selector option feeds + correction-note read-back (EWP-SP4) ─────────────


_FAMILY = "00000000-0000-0000-0000-0000000000f1"
_PHASE = "00000000-0000-0000-0000-0000000000f2"


def _seed_selectors() -> dict:
    seed = _seed()
    seed["subjects"] = [{"id": _SUBJECT, "slug": "english", "name": "English Language"}]
    seed["topics"] = [
        {"id": _TOPIC, "subject_id": _SUBJECT, "parent_topic_id": None,
         "slug": "rc", "name": "Reading Comprehension", "level": "topic"},
        {"id": _MICRO, "subject_id": _SUBJECT, "parent_topic_id": _TOPIC,
         "slug": "inference", "name": "Inference", "level": "microtopic"},
    ]
    seed["exam_families"] = [{"id": _FAMILY, "slug": "ssc", "name": "SSC", "is_active": True}]
    seed["exams"] = [{"id": _EXAM, "exam_family_id": _FAMILY, "slug": "cgl",
                      "name": "SSC CGL", "is_active": True}]
    seed["exam_phases"] = [{"id": _PHASE, "exam_id": _EXAM, "exam_cycle_id": None,
                            "phase_name": "Tier 1", "status": "active"}]
    seed["writing_rubrics"] = [{"id": "00000000-0000-0000-0000-0000000000a9",
                                "name": "Essay Rubric", "version": 2}]
    seed["document_assets"] = [{"id": "00000000-0000-0000-0000-0000000000d9",
                                "scope": "admin_exam_intelligence", "title": "Syllabus PDF",
                                "original_filename": "syllabus.pdf", "document_kind": "syllabus",
                                "created_at": "2026-07-01T00:00:00Z"}]
    return seed


def test_selector_feeds_require_content_read_permission():
    for path in ("taxonomy/subjects", "taxonomy/topics", "exam-scope/families",
                 "exam-scope/exams", "exam-scope/phases", "rubrics", "source-documents"):
        sb = CSSBStub(_seed_selectors())
        denied = _client(sb, permissions=["some.other"]).get(f"{_BASE}/{path}")
        assert denied.status_code == 403, (path, denied.text)
        ok = _client(sb, permissions=[ASSIGN]).get(f"{_BASE}/{path}")
        assert ok.status_code == 200, (path, ok.text)


def test_subject_options_shape():
    sb = CSSBStub(_seed_selectors())
    r = _client(sb, permissions=[AUTHOR]).get(f"{_BASE}/taxonomy/subjects")
    assert r.status_code == 200, r.text
    assert r.json()["items"][0]["name"] == "English Language"


def test_topic_options_filter_by_subject_and_level():
    sb = CSSBStub(_seed_selectors())
    r = _client(sb, permissions=[AUTHOR]).get(
        f"{_BASE}/taxonomy/topics?subject_id={_SUBJECT}&level=topic")
    assert r.status_code == 200, r.text
    ids = {t["id"] for t in r.json()["items"]}
    assert ids == {_TOPIC}


def test_microtopic_options_filter_by_parent_topic():
    sb = CSSBStub(_seed_selectors())
    r = _client(sb, permissions=[AUTHOR]).get(
        f"{_BASE}/taxonomy/topics?parent_topic_id={_TOPIC}&level=microtopic")
    assert r.status_code == 200, r.text
    ids = {t["id"] for t in r.json()["items"]}
    assert ids == {_MICRO}


def test_exam_options_filter_by_family():
    sb = CSSBStub(_seed_selectors())
    r = _client(sb, permissions=[ASSIGN]).get(
        f"{_BASE}/exam-scope/exams?exam_family_id={_FAMILY}")
    assert r.status_code == 200, r.text
    assert {e["id"] for e in r.json()["items"]} == {_EXAM}


def test_phase_options_filter_by_exam():
    sb = CSSBStub(_seed_selectors())
    r = _client(sb, permissions=[ASSIGN]).get(f"{_BASE}/exam-scope/phases?exam_id={_EXAM}")
    assert r.status_code == 200, r.text
    assert r.json()["items"][0]["phase_name"] == "Tier 1"


def test_get_prompt_enriches_readable_labels():
    seed = _seed_selectors()
    seed["writing_prompts"][0]["microtopic_id"] = _MICRO
    sb = CSSBStub(seed)
    r = _client(sb, permissions=[REVIEW]).get(f"{_BASE}/writing-prompts/{_PROMPT}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["subject_name"] == "English Language"
    assert body["topic_name"] == "Reading Comprehension"
    assert body["microtopic_name"] == "Inference"
    # ids are never mutated by enrichment
    assert body["subject_id"] == _SUBJECT


def test_targets_enriched_with_exam_names():
    seed = _seed_selectors()
    seed["writing_prompt_targets"] = [
        {"id": _TARGET, "prompt_id": _PROMPT, "exam_id": _EXAM, "is_global": False,
         "applicability_status": "active", "updated_at": _TOKEN, "created_at": _TOKEN}]
    sb = CSSBStub(seed)
    r = _client(sb, permissions=[ASSIGN]).get(f"{_BASE}/writing-prompts/{_PROMPT}/targets")
    assert r.status_code == 200, r.text
    assert r.json()["items"][0]["exam_name"] == "SSC CGL"


def test_correction_note_returns_latest_needs_correction_audit():
    seed = _seed_selectors()
    seed["admin_audit_logs"] = [
        {"actor_email": "rev@x.io", "action": "writing_prompt_status_transition",
         "entity_type": "writing_prompt", "entity_id": _PROMPT,
         "new_value": {"reviewer_status": "needs_correction", "reviewer_notes": "Fix tense.",
                       "reason": "grammar"}, "notes": "grammar",
         "created_at": "2026-07-05T00:00:00Z"},
    ]
    sb = CSSBStub(seed)
    r = _client(sb, permissions=[AUTHOR]).get(
        f"{_BASE}/writing-prompts/{_PROMPT}/correction-note")
    assert r.status_code == 200, r.text
    note = r.json()["note"]
    assert note["reviewer_notes"] == "Fix tense."
    assert note["actor_email"] == "rev@x.io"


def test_correction_note_absent_returns_null():
    sb = CSSBStub(_seed_selectors())
    r = _client(sb, permissions=[AUTHOR]).get(
        f"{_BASE}/writing-prompts/{_PROMPT}/correction-note")
    assert r.status_code == 200, r.text
    assert r.json()["note"] is None
