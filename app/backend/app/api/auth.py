"""Auth router: Supabase-backed `/api/auth/me`.

Phase 1.5 removed the local JWT/bcrypt/MongoDB auth path. Login/signup/logout
happen client-side via Supabase Auth (`@supabase/supabase-js`). The backend
only verifies the access token attached to subsequent API calls.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from app.core.auth import AUTH_ROLES, get_current_user
from app.db.supabase_client import get_supabase_admin

logger = logging.getLogger("career_copilot.api.auth")
router = APIRouter(prefix="/auth", tags=["auth"])


def _authoritative_role(sb, user_id: str, fallback: str) -> str:
    """Re-read the role from the Supabase admin user record.

    ``get_current_user`` already derives the role from the Supabase-validated
    token, but a role change writes ``app_metadata.role`` while the caller's
    JWT still carries the old value. Re-reading the admin user record reflects
    the change immediately and guarantees we never trust a client-sent role.
    Best-effort: any failure (e.g. no service-role env in tests) falls back to
    the token-derived role, which is itself authoritative (Supabase-validated).
    """
    try:
        resp = sb.auth.admin.get_user_by_id(user_id)
        user_obj = getattr(resp, "user", None) or resp
        app_meta = getattr(user_obj, "app_metadata", None) or {}
        role = app_meta.get("role") if isinstance(app_meta, dict) else None
        if role in AUTH_ROLES:
            return role
        if role:
            logger.warning("auth.me.role_coerced original_role=%s", role)
            return "user"
    except Exception:  # noqa: BLE001
        pass
    return fallback


def _mentor_capability(sb, user_id: str) -> bool:
    """Source ``capabilities.mentor`` from profiles.is_mentor (never role)."""
    try:
        rows = (
            sb.table("profiles").select("is_mentor").eq("id", user_id).limit(1).execute().data
            or []
        )
        return bool(rows[0].get("is_mentor")) if rows else False
    except Exception:  # noqa: BLE001
        return False


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    """Return the Supabase-authenticated user that owns the access token.

    Role is re-fetched from the authoritative Supabase admin record; mentor is
    exposed as a capability (``capabilities.mentor``), never as an auth role.
    """
    user_id = current_user.get("id")
    role = current_user.get("role")
    capabilities = {"mentor": False}
    if user_id:
        sb = None
        try:
            sb = get_supabase_admin()
        except Exception:  # noqa: BLE001
            sb = None
        if sb is not None:
            role = _authoritative_role(sb, user_id, role)
            capabilities["mentor"] = _mentor_capability(sb, user_id)
    return {"user": {**current_user, "role": role, "capabilities": capabilities}}
