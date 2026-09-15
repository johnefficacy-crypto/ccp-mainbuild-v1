"""The activate authority split for content cards (CONTENT-01, migration 291).

The contract (docs/architecture/content-studio.md §1.1) has always said that
``content_studio.activate`` is a SEPARATE, higher-trust authority and that
neither author nor review may flip ``is_active``. That split shipped for
writing_prompts only (migration 226); the two content tables had no activate
route at all, so is_active defaulted true and could not be set through the API.

These tests pin the split now that content_cards has one. They are the
permission-split tests the CONTENT-01 brief asked for.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import content_studio as cs
from app.core.auth import get_current_user
from tests.persona_questions._stub import SBStub
from tests.exam_intelligence.test_content_studio_quant_heuristics import (
    CSSBStub, _HEUR, _TOKEN, _seed,
)

# CSSBStub answers every RPC with a canned payload — deliberately, since that
# file proves the ROUTER contract only. The permission split is a router
# concern, so it uses CSSBStub. Anything that depends on what the RPC actually
# DOES uses SBStub, whose _cms_set_content_card_active emulates migration 291's
# precondition machine. The RPC's real behaviour against live Postgres is proven
# separately when the migration is applied.

_BASE = "/api/admin/content-studio"
AUTHOR = cs.PERM_AUTHOR
REVIEW = cs.PERM_REVIEW
ACTIVATE = cs.PERM_ACTIVATE


def _client(sb, *, permissions) -> TestClient:
    app = FastAPI()
    app.include_router(cs.router, prefix="/api")
    cs.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[cs._flag_enabled] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "op-1", "email": "op@example.com", "role": "admin",
        "permissions": permissions, "is_anonymous": False,
    }
    return TestClient(app, raise_server_exceptions=False)


def _body(**over) -> dict:
    body = {"expected_updated_at": _TOKEN, "reason": "ready for learner delivery"}
    body.update(over)
    return body


# ── the split itself ────────────────────────────────────────────────────────

def test_author_cannot_activate():
    """The whole point of the third authority: authoring a card must not let the
    author put it in front of a learner."""
    sb = CSSBStub(_seed(reviewer_status="verified", is_active=False))
    r = _client(sb, permissions=[AUTHOR]).post(
        f"{_BASE}/content-cards/{_HEUR}/activate", json=_body())
    assert r.status_code == 403, r.text


def test_reviewer_cannot_activate():
    """Verifying is not publishing. A reviewer with content_studio.review — and
    nothing else — must be refused."""
    sb = CSSBStub(_seed(reviewer_status="verified", is_active=False))
    r = _client(sb, permissions=[REVIEW]).post(
        f"{_BASE}/content-cards/{_HEUR}/activate", json=_body())
    assert r.status_code == 403, r.text


def test_author_and_reviewer_together_still_cannot_activate():
    """Holding both of the lower authorities must not add up to the third one."""
    sb = CSSBStub(_seed(reviewer_status="verified", is_active=False))
    r = _client(sb, permissions=[AUTHOR, REVIEW]).post(
        f"{_BASE}/content-cards/{_HEUR}/activate", json=_body())
    assert r.status_code == 403, r.text


def test_activate_authority_can_activate():
    sb = SBStub(_seed(reviewer_status="verified", is_active=False))
    r = _client(sb, permissions=[ACTIVATE]).post(
        f"{_BASE}/content-cards/{_HEUR}/activate", json=_body())
    assert r.status_code == 200, r.text
    assert r.json()["result"]["eligible"] is True


def test_deactivate_needs_the_same_authority_not_review():
    sb = SBStub(_seed(reviewer_status="verified", is_active=True))
    assert _client(sb, permissions=[REVIEW]).post(
        f"{_BASE}/content-cards/{_HEUR}/deactivate", json=_body(reason="withdrawing this card")
    ).status_code == 403
    sb = SBStub(_seed(reviewer_status="verified", is_active=True))
    r = _client(sb, permissions=[ACTIVATE]).post(
        f"{_BASE}/content-cards/{_HEUR}/deactivate", json=_body(reason="withdrawing this card"))
    assert r.status_code == 200, r.text
    assert r.json()["result"]["is_active"] is False


# ── eligibility is the RPC's business, not the router's ─────────────────────

def test_blocked_activation_is_a_200_with_blockers_not_an_error():
    """A blocked activation is a NORMAL answer (migration 226's rule). The router
    never computes eligibility, so an unverified card comes back 200 carrying
    the reason it cannot go live."""
    sb = SBStub(_seed(reviewer_status="pending", is_active=False))
    r = _client(sb, permissions=[ACTIVATE]).post(
        f"{_BASE}/content-cards/{_HEUR}/activate", json=_body())
    assert r.status_code == 200, r.text
    result = r.json()["result"]
    assert result["eligible"] is False
    assert "card_not_verified" in result["blockers"]


def test_blockers_are_collected_not_short_circuited():
    sb = CSSBStub(_seed(reviewer_status="pending", is_active=True))
    r = _client(sb, permissions=[ACTIVATE]).post(
        f"{_BASE}/content-cards/{_HEUR}/activate", json=_body(reason="short"))
    assert r.status_code == 422, r.text  # reason length is a body-level rule


def test_stale_cas_token_is_a_409_not_a_blocker():
    sb = SBStub(_seed(reviewer_status="verified", is_active=False))
    r = _client(sb, permissions=[ACTIVATE]).post(
        f"{_BASE}/content-cards/{_HEUR}/activate",
        json=_body(expected_updated_at="2020-01-01T00:00:00Z"))
    assert r.status_code == 409, r.text


def test_missing_card_is_404():
    sb = SBStub(_seed())
    r = _client(sb, permissions=[ACTIVATE]).post(
        f"{_BASE}/content-cards/00000000-0000-0000-0000-0000000000ff/activate", json=_body())
    assert r.status_code == 404, r.text


# ── the reason is mandatory and auditable ───────────────────────────────────

def test_activation_writes_an_audit_row_carrying_the_reason():
    sb = SBStub(_seed(reviewer_status="verified", is_active=False))
    _client(sb, permissions=[ACTIVATE]).post(
        f"{_BASE}/content-cards/{_HEUR}/activate", json=_body(reason="cleared for the 2026 cycle"))
    audit = sb.db["admin_audit_logs"]
    assert len(audit) == 1
    assert audit[0]["action"] == "content_card_activated"
    assert audit[0]["notes"] == "cleared for the 2026 cycle"
