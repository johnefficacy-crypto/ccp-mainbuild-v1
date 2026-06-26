"""Regression tests for the auth/authorization hardening in this branch.

Covers the security fixes landed alongside
``docs/audits/2026-06-25-auth-rbac-security-review.md``:

  * #3 — mentor-booking payment forgery (no more free "captured" bookings)
  * #6 — study-task / focus-session IDOR (service-role queries must scope by
          user_id) and forced partnerships (consent before "active")

The auth-role-resolution fix (#1) has its own suite in
``tests/test_auth_role_resolution.py``.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth import get_current_user, get_current_user_required_permanent
from tests.persona_questions._stub import SBStub


# ─── Helpers ────────────────────────────────────────────────────────────────


class _FakeOrderApi:
    def __init__(self, order):
        self._order = order

    def fetch(self, _order_id):
        return self._order


class _FakeRzpClient:
    def __init__(self, order):
        self.order = _FakeOrderApi(order)


PERM_A = {"id": "user-A", "email": "a@x.com", "role": "user", "is_anonymous": False, "permissions": []}
ANON = {"id": "anon-1", "email": None, "role": "user", "is_anonymous": True, "permissions": []}


# ═══════════════════════════ #3 — Payment forgery ═══════════════════════════


def _booking_app(sb, user, monkeypatch, *, signature_ok=True, order=None):
    from app.api import accountability

    monkeypatch.setattr(accountability, "get_supabase_admin", lambda: sb)
    monkeypatch.setattr(accountability.razorpay_client, "verify_signature", lambda *a, **k: signature_ok)
    if order is not None:
        monkeypatch.setattr(accountability.razorpay_client, "get_client", lambda: _FakeRzpClient(order))

    app = FastAPI()
    app.include_router(accountability.router)
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def _book_body(**over):
    body = {
        "mentor_id": "rohan-iyer",  # MENTORS catalogue slug, price_per_hour=2499
        "duration_minutes": 60,
        "razorpay_order_id": "order_x",
        "razorpay_payment_id": "pay_x",
        "razorpay_signature": "sig_x",
    }
    body.update(over)
    return body


def test_forged_payment_signature_does_not_create_captured_booking(monkeypatch):
    sb = SBStub({"mentor_bookings": []})
    client = _booking_app(sb, PERM_A, monkeypatch, signature_ok=False)
    r = client.post("/accountability/mentors/book", json=_book_body())
    assert r.status_code == 400, r.text
    assert sb.db["mentor_bookings"] == [], "no booking row should be written on a bad signature"


def test_anonymous_cannot_book_mentor(monkeypatch):
    # Real get_current_user_required_permanent runs (we only override the base
    # get_current_user to return an anonymous identity) → 403.
    sb = SBStub({"mentor_bookings": []})
    client = _booking_app(sb, ANON, monkeypatch, signature_ok=True)
    r = client.post("/accountability/mentors/book", json=_book_body())
    assert r.status_code == 403, r.text


def test_amount_mismatch_is_rejected(monkeypatch):
    # Valid signature but the (server-created) order amount != server price.
    sb = SBStub({"mentor_bookings": []})
    order = {"amount": 100, "notes": {"user_id": "user-A"}, "status": "paid"}
    client = _booking_app(sb, PERM_A, monkeypatch, signature_ok=True, order=order)
    r = client.post("/accountability/mentors/book", json=_book_body())
    assert r.status_code == 400, r.text
    assert sb.db["mentor_bookings"] == []


def test_order_owned_by_other_user_is_rejected(monkeypatch):
    sb = SBStub({"mentor_bookings": []})
    order = {"amount": 2499 * 100, "notes": {"user_id": "user-B"}, "status": "paid"}
    client = _booking_app(sb, PERM_A, monkeypatch, signature_ok=True, order=order)
    r = client.post("/accountability/mentors/book", json=_book_body())
    assert r.status_code == 403, r.text


def test_valid_payment_creates_captured_booking(monkeypatch):
    sb = SBStub({"mentor_bookings": []})
    order = {"amount": 2499 * 100, "notes": {"user_id": "user-A"}, "status": "paid"}
    client = _booking_app(sb, PERM_A, monkeypatch, signature_ok=True, order=order)
    r = client.post("/accountability/mentors/book", json=_book_body())
    assert r.status_code == 200, r.text
    assert r.json()["payment_status"] == "captured"
    assert len(sb.db["mentor_bookings"]) == 1


# ════════════════════════ #6 — study-task IDOR ══════════════════════════════


def _study_app(sb, user, monkeypatch):
    from app.api import canonical

    monkeypatch.setattr(canonical, "get_supabase_admin", lambda: sb)
    app = FastAPI()
    app.include_router(canonical.router_study)
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def _seed_tasks():
    return SBStub({
        "study_tasks": [
            {"id": "t-A", "user_id": "user-A", "status": "planned", "plan_id": "p"},
            {"id": "t-B", "user_id": "user-B", "status": "planned", "plan_id": "p"},
        ],
        "study_sessions": [
            {"id": "s-B", "user_id": "user-B", "started_at": None, "ended_at": None},
        ],
    })


def test_update_task_cannot_touch_another_users_task(monkeypatch):
    sb = _seed_tasks()
    client = _study_app(sb, PERM_A, monkeypatch)
    r = client.put("/study/tasks/t-B", json={"status": "completed"})
    assert r.status_code == 404, r.text
    victim = next(t for t in sb.db["study_tasks"] if t["id"] == "t-B")
    assert victim["status"] == "planned", "victim task must be unchanged"


def test_update_task_allows_own_task(monkeypatch):
    sb = _seed_tasks()
    client = _study_app(sb, PERM_A, monkeypatch)
    r = client.put("/study/tasks/t-A", json={"status": "completed"})
    assert r.status_code == 200, r.text
    own = next(t for t in sb.db["study_tasks"] if t["id"] == "t-A")
    assert own["status"] == "completed"


def test_toggle_task_cannot_touch_another_users_task(monkeypatch):
    sb = _seed_tasks()
    client = _study_app(sb, PERM_A, monkeypatch)
    r = client.post("/study/plan/toggle", json={"task_id": "t-B"})
    assert r.status_code == 404, r.text
    victim = next(t for t in sb.db["study_tasks"] if t["id"] == "t-B")
    assert victim["status"] == "planned"


def test_focus_stop_cannot_end_another_users_session(monkeypatch):
    sb = _seed_tasks()
    client = _study_app(sb, PERM_A, monkeypatch)
    r = client.post("/study/focus/stop", json={"session_id": "s-B", "notes": "pwned"})
    assert r.status_code == 404, r.text
    victim = next(s for s in sb.db["study_sessions"] if s["id"] == "s-B")
    assert victim["ended_at"] is None and victim.get("notes") != "pwned"


# ════════════════════ #6 — social: consent + membership ═════════════════════


def test_request_partner_starts_pending_and_requires_target_to_accept():
    from app.study_os.social_sessions import accept_partner, request_partner

    sb = SBStub({"accountability_pairs": []})
    partner_b = str(uuid.uuid4())
    req = request_partner(sb, "user-A", partner_b)
    assert req["status"] == "pending", "a request must not auto-activate onto the target"

    # A third party (and the requester) cannot accept on the target's behalf.
    with pytest.raises(LookupError):
        accept_partner(sb, "user-C", req["id"])
    with pytest.raises(LookupError):
        accept_partner(sb, "user-A", req["id"])

    # Only the target activates it.
    accepted = accept_partner(sb, partner_b, req["id"])
    assert accepted["status"] == "active"


def test_end_session_requires_participation():
    from app.study_os.social_sessions import end_session

    sb = SBStub({
        "social_session_attendance": [
            {"id": "att", "session_id": "sess", "user_id": "user-A"},
        ],
        "social_study_sessions": [
            {"id": "sess", "started_at": None, "ended_at": None,
             "verified_presence_minutes": None, "verified_focus_minutes": None},
        ],
    })
    # Non-participant cannot end the session.
    with pytest.raises(LookupError):
        end_session(sb, "user-Z", "sess")
    sess = sb.db["social_study_sessions"][0]
    assert sess["ended_at"] is None, "session must not be ended by a non-member"

    # Participant can.
    end_session(sb, "user-A", "sess")
    assert sb.db["social_study_sessions"][0]["ended_at"] is not None
