"""Partner consent lifecycle — request -> accept/decline -> atomic pair.

Covers the policy in docs/product/accountability-partner-governance.md §2.1
and the PR #772 review findings:
  - request creates a *pending* row, never an active pair (consent-first)
  - the message= argument no longer raises TypeError (was a real bug)
  - only the recipient may respond
  - accept creates the pair and enforces the one-active-pair guard for both
  - the published-partner DTO never leaks full_name / city (§7)
"""
from __future__ import annotations

import pytest

from app.study_os import social_sessions as ss
from tests.persona_questions._stub import SBStub

U1 = "11111111-1111-1111-1111-111111111111"
U2 = "22222222-2222-2222-2222-222222222222"
U3 = "33333333-3333-3333-3333-333333333333"


def _sb(**tables) -> SBStub:
    return SBStub({k: [dict(r) for r in v] for k, v in tables.items()})


# ── request: consent-first ────────────────────────────────────────────────

def test_request_creates_pending_not_active_pair():
    sb = _sb()
    out = ss.request_partner(sb, U1, U2, pairing_goal="discipline", message="hi")
    assert out["status"] == "pending"
    assert out["requester_id"] == U1 and out["partner_id"] == U2
    # No pair exists until the recipient accepts.
    assert sb.db.get("accountability_pairs", []) == []
    reqs = sb.db["accountability_partner_requests"]
    assert len(reqs) == 1 and reqs[0]["message"] == "hi"


def test_request_message_arg_does_not_raise():
    # Regression: accountability.py passed message= to a fn that didn't accept it.
    sb = _sb()
    ss.request_partner(sb, U1, U2, message="note")  # must not raise


def test_request_rejects_self_pairing():
    sb = _sb()
    with pytest.raises(ValueError):
        ss.request_partner(sb, U1, U1)


def test_request_blocked_when_requester_already_paired():
    sb = _sb(accountability_pairs=[{"id": "p", "user_a": U1, "user_b": U3, "status": "active"}])
    with pytest.raises(ValueError):
        ss.request_partner(sb, U1, U2)


# ── respond: accept / decline ─────────────────────────────────────────────

def test_accept_creates_pair_and_marks_request_accepted():
    sb = _sb()
    req = ss.request_partner(sb, U1, U2, pairing_goal="mock_review")
    res = ss.respond_partner(sb, U2, req["id"], "accept")
    assert res["status"] == "accepted"
    pair = res["pair"]
    assert pair["user_a"] == U1 and pair["user_b"] == U2
    assert pair["status"] == "active" and pair["pairing_goal"] == "mock_review"
    assert sb.db["accountability_partner_requests"][0]["status"] == "accepted"


def test_only_recipient_can_accept():
    sb = _sb()
    req = ss.request_partner(sb, U1, U2)
    with pytest.raises(PermissionError):
        ss.respond_partner(sb, U3, req["id"], "accept")


def test_decline_marks_declined_and_creates_no_pair():
    sb = _sb()
    req = ss.request_partner(sb, U1, U2)
    res = ss.respond_partner(sb, U2, req["id"], "decline")
    assert res["status"] == "declined"
    assert sb.db.get("accountability_pairs", []) == []
    assert sb.db["accountability_partner_requests"][0]["status"] == "declined"


def test_accept_guard_blocks_when_recipient_already_paired():
    sb = _sb(accountability_pairs=[{"id": "p", "user_a": U2, "user_b": U3, "status": "active"}])
    req = ss.request_partner(sb, U1, U2)  # requester U1 is free → request ok
    with pytest.raises(ValueError):
        ss.respond_partner(sb, U2, req["id"], "accept")  # U2 already paired


def test_cannot_respond_to_resolved_request():
    sb = _sb()
    req = ss.request_partner(sb, U1, U2)
    ss.respond_partner(sb, U2, req["id"], "decline")
    with pytest.raises(ValueError):
        ss.respond_partner(sb, U2, req["id"], "accept")


# ── privacy DTO ───────────────────────────────────────────────────────────

def test_published_partner_strips_pii():
    dto = ss.published_partner(
        {"id": U2, "display_name": "Aman R.", "full_name": "Aman Raghav", "city": "Pune", "exam_focus": "UPSC CSE 2026"}
    )
    assert dto == {"id": U2, "name": "Aman R.", "exam": "UPSC CSE 2026"}
    assert "full_name" not in dto and "city" not in dto


def test_published_partner_handles_missing_display_name():
    dto = ss.published_partner({"id": U2, "full_name": "Aman Raghav", "city": "Pune"})
    assert dto["name"] == "Aspirant"  # never falls back to full_name
    assert "full_name" not in dto and "city" not in dto


def test_published_partner_none():
    assert ss.published_partner(None) is None
