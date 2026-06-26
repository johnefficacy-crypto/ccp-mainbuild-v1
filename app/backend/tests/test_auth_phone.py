"""Phone OTP: the serialized user exposes `phone` (login is phone-based now)."""
from __future__ import annotations

from app.core.auth import _serialize_user


class _FakeUser:
    def __init__(self, phone=None, email=None):
        self.id = "u-1"
        self.email = email
        self.phone = phone
        self.user_metadata = {"name": "U"}
        self.app_metadata = {"role": "user", "permissions": []}
        self.created_at = "2026-01-01T00:00:00Z"


def test_serialize_user_includes_phone_from_user_object():
    out = _serialize_user(_FakeUser(phone="+919999900001"))
    assert out["phone"] == "+919999900001"
    assert out["role"] == "user"


def test_serialize_user_phone_falls_back_to_jwt_claim():
    out = _serialize_user(_FakeUser(phone=None), {"phone": "+15555550100"})
    assert out["phone"] == "+15555550100"


def test_serialize_user_phone_none_when_absent():
    out = _serialize_user(_FakeUser(), {})
    assert out["phone"] is None
    # Email stays optional and independent.
    assert out["email"] is None


def test_serialize_user_ignores_user_metadata_role():
    """user_metadata.role is client-writable and must NEVER grant access.

    A caller can set arbitrary user_metadata via signInWithOtp options.data,
    so a `role` smuggled there must be ignored — only app_metadata.role
    (admin-API only) and the Supabase-signed JWT claim are trusted.
    """
    user = _FakeUser()
    user.user_metadata = {"role": "super_admin", "name": "Attacker"}
    user.app_metadata = {}  # no canonical role set
    out = _serialize_user(user, {})  # no JWT role claim either
    assert out["role"] == "user"


def test_serialize_user_app_metadata_role_still_trusted():
    """app_metadata.role (server-set) remains authoritative."""
    user = _FakeUser()
    user.app_metadata = {"role": "admin", "permissions": []}
    out = _serialize_user(user, {})
    assert out["role"] == "admin"


def test_serialize_user_email_falls_back_to_user_metadata():
    """Phone-OTP signup stores the optional receipt email in user_metadata."""
    user = _FakeUser()
    user.email = None
    user.user_metadata = {"name": "U", "email": "receipts@example.com"}
    out = _serialize_user(user, {})
    assert out["email"] == "receipts@example.com"
