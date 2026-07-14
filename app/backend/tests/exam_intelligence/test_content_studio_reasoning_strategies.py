"""Router-layer tests for Content Studio reasoning-strategy operations (GQR-S3).

Covers the `/api/admin/content-studio/reasoning-strategies` surface added over
migration 261 (`app/api/content_studio.py`) at the FastAPI boundary: the shared
read gate, list filters + pagination, the strategy reviewer-transition guard
(which matches quant heuristics and DIFFERS from writing prompts), the reopen-
verified note rule, dual-CAS body requirements, and RPC error-code → HTTP mapping.
The atomic RPC *behaviour* (audit rows, CAS, transition matrix) is owned by the
migration-261 RPC; here we only prove the router contract. Mirrors
test_content_studio_quant_heuristics.py.
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

_TOPIC = "00000000-0000-0000-0000-0000000000b1"
_MICRO = "00000000-0000-0000-0000-0000000000c1"
_STRAT = "00000000-0000-0000-0000-0000000000e1"
_ABSENT = "00000000-0000-0000-0000-0000000000ff"
_TOKEN = "2026-07-10T00:00:00Z"  # matches the seeded strategy's updated_at (content CAS)


def _review_body(**over) -> dict:
    body = {"status": "verified", "expected_status": "pending",
            "expected_updated_at": _TOKEN, "reason": "a valid audit reason"}
    body.update(over)
    return body


class _CSQuery(_Query):
    """Adds ilike / range / count='exact' on the read path."""

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
    def __init__(self, stub, fn_name, params):
        self._stub = stub
        self._fn_name = fn_name
        self._params = params

    def execute(self):
        self._stub.rpc_calls.append((self._fn_name, self._params))
        if self._stub.rpc_error is not None:
            raise RuntimeError(self._stub.rpc_error)
        return _Exec(self._stub.rpc_result if self._stub.rpc_result is not None
                     else {"ok": True, "audit_id": "aud-1", "strategy_id": _STRAT,
                           "prev_status": "pending", "new_status": "verified"})


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


def _client(sb: CSSBStub, *, permissions=None, role="admin", anonymous=False) -> TestClient:
    app = FastAPI()
    app.include_router(cs.router, prefix="/api")
    cs.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[cs._flag_enabled] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "op-1",
        "email": "op@example.com",
        "role": role,
        "permissions": permissions if permissions is not None else [REVIEW],
        "is_anonymous": anonymous,
    }
    return TestClient(app, raise_server_exceptions=False)


def _seed(**over) -> dict:
    row = {
        "id": _STRAT, "topic_id": _TOPIC, "microtopic_id": None,
        "strategy_code": "RS-SYL-01", "name": "Syllogism Venn method",
        "strategy_type": "diagram_method", "applicability_rule": {"op": "syllogism"},
        "formula_latex": None, "standard_method": "Draw all-case Venn diagrams",
        "faster_method": "Eliminate on definite-only conclusions",
        "key_observation": "Possibility cases flip 'some' conclusions",
        "reviewer_status": "pending", "is_active": True,
        "created_at": "2026-07-10T00:00:00Z", "updated_at": "2026-07-10T00:00:00Z",
    }
    row.update(over)
    return {"reasoning_strategies": [row], "topics": [{"id": _TOPIC, "name": "Reasoning"}],
            "admin_audit_logs": []}


# ── read gating ─────────────────────────────────────────────────────────────


def test_list_readable_by_author_review_manage_and_super_admin():
    for perms, role in (([AUTHOR], "admin"), ([REVIEW], "admin"),
                        ([ASSIGN], "admin"), ([], "super_admin")):
        sb = CSSBStub(_seed())
        r = _client(sb, permissions=perms, role=role).get(f"{_BASE}/reasoning-strategies")
        assert r.status_code == 200, (perms, role, r.text)


def test_list_denied_without_any_content_permission():
    sb = CSSBStub(_seed())
    r = _client(sb, permissions=["some.other"]).get(f"{_BASE}/reasoning-strategies")
    assert r.status_code == 403


def test_list_denied_for_anonymous():
    sb = CSSBStub(_seed())
    r = _client(sb, permissions=[REVIEW], role="user", anonymous=True).get(f"{_BASE}/reasoning-strategies")
    assert r.status_code == 403


# ── read filters + enrichment ───────────────────────────────────────────────


def test_list_filters_by_type_and_status():
    seed = _seed()
    seed["reasoning_strategies"].append({
        "id": "s2", "topic_id": _TOPIC, "strategy_code": "RS-2", "name": "Trap A",
        "strategy_type": "trap", "reviewer_status": "verified", "is_active": True,
        "created_at": "2026-07-11T00:00:00Z", "updated_at": "2026-07-11T00:00:00Z"})
    sb = CSSBStub(seed)
    r = _client(sb).get(f"{_BASE}/reasoning-strategies?strategy_type=diagram_method&reviewer_status=pending")
    assert r.status_code == 200, r.text
    assert {s["id"] for s in r.json()["items"]} == {_STRAT}


def test_list_enriches_topic_name_and_search_matches_name():
    sb = CSSBStub(_seed())
    r = _client(sb).get(f"{_BASE}/reasoning-strategies?q=syllogism")
    body = r.json()
    assert {s["id"] for s in body["items"]} == {_STRAT}
    assert body["items"][0]["topic_name"] == "Reasoning"
    assert body["total"] == 1
    r2 = _client(sb).get(f"{_BASE}/reasoning-strategies?q=nomatch")
    assert r2.json()["items"] == []


def test_get_returns_404_when_absent():
    sb = CSSBStub(_seed())
    r = _client(sb).get(f"{_BASE}/reasoning-strategies/{_ABSENT}")
    assert r.status_code == 404


def test_get_returns_enriched_row():
    sb = CSSBStub(_seed())
    r = _client(sb).get(f"{_BASE}/reasoning-strategies/{_STRAT}")
    assert r.status_code == 200, r.text
    assert r.json()["topic_name"] == "Reasoning"


# ── review permission + transition guard ────────────────────────────────────


def test_review_requires_review_permission():
    sb = CSSBStub(_seed())
    r = _client(sb, permissions=[AUTHOR]).post(
        f"{_BASE}/reasoning-strategies/{_STRAT}/review", json=_review_body())
    assert r.status_code == 403


def test_review_happy_path_calls_rpc_with_marshalled_params():
    sb = CSSBStub(_seed())
    r = _client(sb, permissions=[REVIEW]).post(
        f"{_BASE}/reasoning-strategies/{_STRAT}/review", json=_review_body())
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True
    fn, params = sb.rpc_calls[-1]
    assert fn == "cms_review_reasoning_strategy"
    assert params["p_strategy_id"] == _STRAT
    assert params["p_expected_status"] == "pending"
    assert params["p_expected_updated_at"] == _TOKEN
    assert params["p_new_status"] == "verified"
    assert params["p_reason"] == "a valid audit reason"
    assert params["p_actor_user_id"] == "op-1"


def test_review_rejects_unknown_target_status():
    sb = CSSBStub(_seed())
    r = _client(sb, permissions=[REVIEW]).post(
        f"{_BASE}/reasoning-strategies/{_STRAT}/review", json=_review_body(status="bogus"))
    assert r.status_code == 422
    assert not sb.rpc_calls


def test_review_requires_content_cas_token_and_reason():
    sb = CSSBStub(_seed())
    # Missing content CAS token → 422 (pydantic), no RPC fired.
    body = _review_body()
    body.pop("expected_updated_at")
    r = _client(sb, permissions=[REVIEW]).post(f"{_BASE}/reasoning-strategies/{_STRAT}/review", json=body)
    assert r.status_code == 422
    # Missing / too-short reason → 422, no RPC fired.
    r2 = _client(sb, permissions=[REVIEW]).post(
        f"{_BASE}/reasoning-strategies/{_STRAT}/review", json=_review_body(reason="short"))
    assert r2.status_code == 422
    assert not sb.rpc_calls


def test_review_blocks_illegal_transition_needscorrection_to_verified():
    # Strategy matrix (matches heuristics, differs from writing prompts):
    # needs_correction may go to pending|rejected only — NOT straight to verified.
    sb = CSSBStub(_seed(reviewer_status="needs_correction"))
    r = _client(sb, permissions=[REVIEW]).post(
        f"{_BASE}/reasoning-strategies/{_STRAT}/review",
        json=_review_body(status="verified", expected_status="needs_correction"))
    assert r.status_code == 422, r.text
    assert not sb.rpc_calls


def test_review_allows_needscorrection_to_pending():
    sb = CSSBStub(_seed(reviewer_status="needs_correction"))
    r = _client(sb, permissions=[REVIEW]).post(
        f"{_BASE}/reasoning-strategies/{_STRAT}/review",
        json=_review_body(status="pending", expected_status="needs_correction"))
    assert r.status_code == 200, r.text


def test_review_allows_rejected_to_pending():
    # rejected → pending must be reachable (the review queue exposes a rejected filter).
    sb = CSSBStub(_seed(reviewer_status="rejected"))
    r = _client(sb, permissions=[REVIEW]).post(
        f"{_BASE}/reasoning-strategies/{_STRAT}/review",
        json=_review_body(status="pending", expected_status="rejected"))
    assert r.status_code == 200, r.text


def test_reopen_verified_requires_reviewer_notes():
    sb = CSSBStub(_seed(reviewer_status="verified"))
    r = _client(sb, permissions=[REVIEW]).post(
        f"{_BASE}/reasoning-strategies/{_STRAT}/review",
        json=_review_body(status="needs_correction", expected_status="verified"))
    assert r.status_code == 422, r.text
    assert not sb.rpc_calls
    r2 = _client(sb, permissions=[REVIEW]).post(
        f"{_BASE}/reasoning-strategies/{_STRAT}/review",
        json=_review_body(status="needs_correction", expected_status="verified",
                          reviewer_notes="Venn method misses possibility cases"))
    assert r2.status_code == 200, r2.text


# ── RPC error mapping ───────────────────────────────────────────────────────


def test_review_maps_concurrent_modification_to_409():
    sb = CSSBStub(_seed())
    sb.rpc_error = "concurrent_modification: strategy content changed since read"
    r = _client(sb, permissions=[REVIEW]).post(
        f"{_BASE}/reasoning-strategies/{_STRAT}/review", json=_review_body())
    assert r.status_code == 409


def test_review_maps_not_found_to_404():
    sb = CSSBStub(_seed())
    sb.rpc_error = "not_found: strategy does not exist"
    r = _client(sb, permissions=[REVIEW]).post(
        f"{_BASE}/reasoning-strategies/{_STRAT}/review", json=_review_body())
    assert r.status_code == 404


def test_review_maps_transition_not_allowed_to_422():
    sb = CSSBStub(_seed())
    sb.rpc_error = "transition_not_allowed: pending -> pending is not permitted"
    r = _client(sb, permissions=[REVIEW]).post(
        f"{_BASE}/reasoning-strategies/{_STRAT}/review", json=_review_body())
    assert r.status_code == 422


def test_review_rejects_extra_body_fields():
    sb = CSSBStub(_seed())
    r = _client(sb, permissions=[REVIEW]).post(
        f"{_BASE}/reasoning-strategies/{_STRAT}/review", json=_review_body(bogus_field="x"))
    assert r.status_code == 422
