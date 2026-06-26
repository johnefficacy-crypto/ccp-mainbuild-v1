"""Role-resolution hardening for ``app.core.auth._serialize_user``.

Privilege-escalation regression suite. The auth role MUST come ONLY from
``app_metadata.role`` — the service-role-only (canonical) source per
migration 134/151 and the module docstring.

``user_metadata`` (a.k.a. ``raw_user_meta_data``) is writable by the user
themselves via ``supabase.auth.updateUser({ data: { role: ... } })``, and
the JWT ``role`` claim merely reflects that same user_metadata. A previous
fallback chain consulted both when ``app_metadata.role`` was absent — which
let any normal signup self-assign ``role="super_admin"`` and pass
``require_admin`` / ``require_super_admin``. These tests pin the fix: only
``app_metadata.role`` is ever trusted.
"""
from __future__ import annotations

from app.core.auth import AUTH_ROLES, _serialize_user


class _FakeUser:
    """Minimal gotrue-User stand-in for ``_serialize_user``."""

    def __init__(self, *, app_metadata=None, user_metadata=None, uid="u-1",
                 email="u@example.com"):
        self.id = uid
        self.email = email
        self.app_metadata = dict(app_metadata or {})
        self.user_metadata = dict(user_metadata or {})
        self.created_at = "2026-01-01T00:00:00Z"


# ─── The escalation vectors — both must resolve to "user" ───────────────────


def test_user_metadata_role_super_admin_does_not_escalate():
    """Client-writable user_metadata.role MUST NOT grant a role.

    A normal signup with NO app_metadata.role who self-assigns
    user_metadata={"role": "super_admin"} must resolve to "user".
    """
    user = _FakeUser(
        app_metadata={},
        user_metadata={"role": "super_admin"},
    )
    resolved = _serialize_user(user, claims={})
    assert resolved["role"] == "user", (
        "user_metadata.role leaked into the auth role — privilege escalation"
    )


def test_user_metadata_role_admin_does_not_escalate():
    """The same vector with 'admin' (the broader admin tier) is also blocked."""
    user = _FakeUser(
        app_metadata={},
        user_metadata={"role": "admin"},
    )
    resolved = _serialize_user(user, claims={})
    assert resolved["role"] == "user"


def test_jwt_claim_role_does_not_escalate():
    """A JWT ``role`` claim with empty app_metadata MUST resolve to "user".

    The Supabase JWT role claim reflects user_metadata, so trusting it is
    the same escalation by another path.
    """
    user = _FakeUser(app_metadata={}, user_metadata={})
    resolved = _serialize_user(user, claims={"role": "admin", "sub": "u-1"})
    assert resolved["role"] == "user"


def test_both_user_metadata_and_jwt_claim_lose_to_empty_app_metadata():
    """Belt-and-suspenders: both client-controlled sources set, both ignored."""
    user = _FakeUser(
        app_metadata={},
        user_metadata={"role": "super_admin"},
    )
    resolved = _serialize_user(
        user, claims={"role": "super_admin", "sub": "u-1"}
    )
    assert resolved["role"] == "user"


# ─── The legitimate path — app_metadata.role is honoured ────────────────────


def test_app_metadata_admin_resolves_to_admin():
    """A legitimately provisioned app_metadata.role='admin' still wins."""
    user = _FakeUser(app_metadata={"role": "admin"})
    resolved = _serialize_user(user, claims={})
    assert resolved["role"] == "admin"


def test_app_metadata_super_admin_resolves_to_super_admin():
    user = _FakeUser(app_metadata={"role": "super_admin"})
    resolved = _serialize_user(user, claims={})
    assert resolved["role"] == "super_admin"


def test_app_metadata_role_wins_over_conflicting_user_metadata():
    """When both are present, the canonical app_metadata source is used."""
    user = _FakeUser(
        app_metadata={"role": "user"},
        user_metadata={"role": "super_admin"},
    )
    resolved = _serialize_user(user, claims={"role": "super_admin"})
    assert resolved["role"] == "user"


# ─── Coercion / default behaviour ───────────────────────────────────────────


def test_no_role_anywhere_defaults_to_user():
    user = _FakeUser(app_metadata={}, user_metadata={})
    resolved = _serialize_user(user, claims={})
    assert resolved["role"] == "user"


def test_unexpected_app_metadata_role_coerces_to_user():
    """A non-canonical app_metadata.role (e.g. legacy 'mentor') is rejected."""
    user = _FakeUser(app_metadata={"role": "mentor"})
    resolved = _serialize_user(user, claims={})
    assert resolved["role"] == "user"
    assert resolved["role"] in AUTH_ROLES


def test_claims_still_used_for_sub_and_email_fallback():
    """Removing the role fallback must not break sub/email fallback from claims."""

    class _SparseUser:
        id = None
        email = None
        app_metadata = {"role": "admin"}
        user_metadata = {}
        created_at = None

    resolved = _serialize_user(
        _SparseUser(), claims={"sub": "claim-sub", "email": "claim@x.com"}
    )
    assert resolved["id"] == "claim-sub"
    assert resolved["email"] == "claim@x.com"
    # And the legitimate app_metadata role still resolves correctly.
    assert resolved["role"] == "admin"
