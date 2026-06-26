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
