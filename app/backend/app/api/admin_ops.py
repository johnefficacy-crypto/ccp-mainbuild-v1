"""Admin operations endpoints — marketplace KPIs, AI policy view, RBAC user mgmt.

Supersedes the hardcoded placeholder endpoints in router_admin
(/marketplace, /ai-policy, /users/create). Reads real Supabase tables;
falls back to zero on failure so the admin console always renders.

RBAC role management (Step 3/4) lives here too: the source of truth for an
auth role is ``auth.users.raw_app_meta_data.role`` (Supabase app_metadata),
read/written exclusively through the service-role admin client. The backend
is authoritative; the frontend RBAC console is UX only.
"""
from __future__ import annotations

import inspect
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import AUTH_ROLES, require_admin, require_super_admin
from app.db.supabase_client import get_supabase_admin


logger = logging.getLogger("career_copilot.api.admin_ops")

router = APIRouter(prefix="/admin", tags=["admin-ops"])

# Audit action strings (Step 9). Use these exact values.
AUDIT_ROLE_CHANGE = "rbac.role_change"
AUDIT_ADMIN_INVITE = "rbac.admin_invite"
AUDIT_FORCE_SIGNOUT = "rbac.force_signout"


def _count(sb, table: str, **filters) -> int:
    try:
        q = sb.table(table).select("id", count="exact")
        for k, v in filters.items():
            q = q.eq(k, v)
        return int(getattr(q.execute(), "count", None) or 0)
    except Exception:
        return 0


def _count_since(sb, table: str, ts_col: str, since: datetime, **filters) -> int:
    try:
        q = sb.table(table).select("id", count="exact").gte(ts_col, since.isoformat())
        for k, v in filters.items():
            q = q.eq(k, v)
        return int(getattr(q.execute(), "count", None) or 0)
    except Exception:
        return 0


# ───────────────────────────── Marketplace ─────────────────────────────


@router.get("/marketplace")
def marketplace_kpis(user: dict = Depends(require_admin)) -> dict:
    sb = get_supabase_admin()
    kpis = {
        "courses": _count(sb, "courses"),
        "community_resources": _count(sb, "community_resources", status="approved"),
        "mentors": _count(sb, "profiles", is_mentor=True),
        "active_bookings": _count(sb, "mentor_bookings", status="confirmed")
            + _count(sb, "mentor_bookings", status="awaiting_mentor"),
        "completed_bookings": _count(sb, "mentor_bookings", status="completed"),
        "open_resource_reports": _count(sb, "community_resource_reports", status="open"),
    }
    try:
        flags = (
            sb.table("community_resource_reports")
            .select("id,resource_id,reason,status,created_at")
            .order("created_at", desc=True)
            .limit(10)
            .execute()
            .data
            or []
        )
    except Exception:
        flags = []
    return {"kpis": kpis, "flags": flags}


# ───────────────────────────── AI policy ─────────────────────────────


AI_POLICY_RULES = [
    {
        "id": "deterministic_eligibility_authority",
        "rule": "AI must never override deterministic eligibility verdicts.",
        "enabled": True,
    },
    {
        "id": "source_registry_required",
        "rule": "AI must cite source registry for any recruitment claim.",
        "enabled": True,
    },
    {
        "id": "admin_review_for_promotion",
        "rule": "AI may extract structure from documents; canonical promotion still requires admin review.",
        "enabled": True,
    },
    {
        "id": "ai_response_flag_routes_to_moderation",
        "rule": "User-flagged AI responses must create a moderation_items entry within the same request.",
        "enabled": True,
    },
    {
        "id": "low_confidence_label",
        "rule": "AI responses with confidence < 0.7 must be visibly labelled as low-confidence in the UI.",
        "enabled": True,
    },
]


@router.get("/ai-policy")
def ai_policy(user: dict = Depends(require_admin)) -> dict:
    """AI guardrail policy view.

    Rules are code-side constants (versioned in source) so audits replay
    the policy active when a decision was made. The telemetry block
    reads real moderation_items + ai_messages so ops can see how the
    guardrails are firing.
    """
    sb = get_supabase_admin()
    flagged_24h = 0
    flagged_total = 0
    recent_flags: list[dict] = []
    try:
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        flagged_24h = _count_since(sb, "ai_messages", "created_at", since, is_flagged=True)
        flagged_total = _count(sb, "ai_messages", is_flagged=True)
        recent_flags = (
            sb.table("moderation_items")
            .select("id,entity_id,reason,status,severity,created_at")
            .eq("entity_type", "ai_response")
            .order("created_at", desc=True)
            .limit(10)
            .execute()
            .data
            or []
        )
    except Exception:
        pass
    return {
        "rules": AI_POLICY_RULES,
        "guardrails": [r["rule"] for r in AI_POLICY_RULES],
        "model": "scripted-v1",
        "swap_target": "anthropic:claude-opus-4-7",
        "active": True,
        "telemetry": {
            "flagged_messages_24h": flagged_24h,
            "flagged_messages_total": flagged_total,
            "recent_flags": recent_flags,
        },
    }


# ════════════════════════════ RBAC user management ════════════════════════
#
# Auth roles only: user / admin / super_admin. ``mentor`` is a domain
# capability (profiles.is_mentor) and is rejected as a role input.


def _auth_admin(sb):
    """Return the Supabase auth admin API off the service-role client."""
    return sb.auth.admin


def _as_user(resp: Any) -> Any:
    """Unwrap a gotrue UserResponse (``.user``) or pass a raw user through."""
    return getattr(resp, "user", None) or resp


def _app_metadata(user_obj: Any) -> dict:
    meta = (
        getattr(user_obj, "app_metadata", None)
        or getattr(user_obj, "raw_app_meta_data", None)
        or {}
    )
    return dict(meta) if isinstance(meta, dict) else {}


def _user_role(user_obj: Any) -> str:
    role = _app_metadata(user_obj).get("role")
    return role if role in AUTH_ROLES else "user"


def _serialize_auth_user(user_obj: Any) -> dict:
    um = getattr(user_obj, "user_metadata", None) or getattr(user_obj, "raw_user_meta_data", None) or {}
    um = um if isinstance(um, dict) else {}
    return {
        "id": getattr(user_obj, "id", None),
        "email": getattr(user_obj, "email", None),
        "name": um.get("name") or um.get("full_name"),
        "role": _user_role(user_obj),
        "plan": um.get("plan", "free"),
        "created_at": getattr(user_obj, "created_at", None),
        "last_login_at": getattr(user_obj, "last_sign_in_at", None),
    }


def _list_all_auth_users(sb) -> list[Any]:
    """Page through every auth user via the admin API.

    ``list_users`` returns at most one page; we walk pages until a short/empty
    page so the super_admin count is exact rather than first-page-only.
    """
    admin = _auth_admin(sb)
    users: list[Any] = []
    page = 1
    per_page = 200
    while True:
        try:
            res = admin.list_users(page=page, per_page=per_page)
        except TypeError:
            # Older signature: list_users() with no pagination kwargs.
            res = admin.list_users()
            users.extend(getattr(res, "users", None) or (res if isinstance(res, list) else []))
            break
        batch = getattr(res, "users", None) or (res if isinstance(res, list) else [])
        users.extend(batch)
        if len(batch) < per_page or not batch:
            break
        page += 1
        if page > 1000:  # hard safety ceiling
            break
    return users


def _count_super_admins(sb) -> int:
    return sum(1 for u in _list_all_auth_users(sb) if _user_role(u) == "super_admin")


def _audit_rbac(
    sb,
    actor: dict,
    action: str,
    *,
    target_user_id: str | None,
    target_email: str | None = None,
    old_role: str | None = None,
    new_role: str | None = None,
    reason: str | None = None,
    route: str,
) -> None:
    """Append an admin_audit_logs row for an RBAC mutation.

    Never logs tokens / keys / passwords. ``entity_type`` is NOT NULL in the
    schema, so we always set it; the structured detail lives in ``new_value``.
    """
    payload = {
        "actor_id": actor.get("id"),
        "actor_email": actor.get("email"),
        "target_user_id": target_user_id,
        "target_email": target_email,
        "old_role": old_role,
        "new_role": new_role,
        "reason": reason,
        "route": route,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        sb.table("admin_audit_logs").insert(
            {
                "actor_id": actor.get("id"),
                "actor_email": actor.get("email"),
                "action": action,
                "entity_type": "auth_user",
                "entity_id": target_user_id,
                "new_value": payload,
                "notes": route,
            }
        ).execute()
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "rbac_audit_insert_failed action=%s actor_id=%s target=%s exc=%s",
            action, actor.get("id"), target_user_id, type(exc).__name__, exc_info=True,
        )


class RoleChangeBody(BaseModel):
    role: str
    reason: str | None = None


class AdminCreateBody(BaseModel):
    email: str
    password: str
    name: str = ""
    role: str = "admin"
    scope: list[str] = []


def _validate_role_input(role: str) -> str:
    role = (role or "").strip()
    if role == "mentor":
        raise HTTPException(status_code=400, detail="mentor is not an auth role")
    if role not in AUTH_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"invalid role; allowed: {sorted(AUTH_ROLES)}",
        )
    return role


@router.get("/users")
def list_users(user: dict = Depends(require_admin)) -> dict:
    """List auth users with their canonical role for the RBAC console."""
    sb = get_supabase_admin()
    try:
        rows = [_serialize_auth_user(u) for u in _list_all_auth_users(sb)]
    except Exception as exc:  # noqa: BLE001
        logger.exception("list_users failed")
        raise HTTPException(status_code=502, detail="Could not list users") from exc
    return {"items": rows, "total": len(rows)}


@router.put("/users/{user_id}/role")
def change_user_role(
    user_id: str,
    body: RoleChangeBody,
    actor: dict = Depends(require_super_admin),
) -> dict:
    """Change an auth user's role (super_admin only).

    Writes the role to ``app_metadata.role`` (single source of truth),
    preserving every other app_metadata key, and records an audit row. The
    target's existing JWT keeps the stale role until they re-login, so the
    response carries ``requires_session_refresh``.
    """
    new_role = _validate_role_input(body.role)
    sb = get_supabase_admin()
    admin = _auth_admin(sb)

    target = _as_user(admin.get_user_by_id(user_id))
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    old_role = _user_role(target)

    demoting_super = old_role == "super_admin" and new_role != "super_admin"
    if demoting_super:
        # Pre-check the live super_admin population before removing one. A sole
        # super_admin can never be demoted; in practice that demotion is always
        # a self-demote (you must be super_admin to reach this route), so the
        # self-demote message is the one callers normally see.
        super_count = _count_super_admins(sb)
        if super_count <= 1:
            if actor.get("id") == user_id:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot self-demote unless another active super_admin exists",
                )
            raise HTTPException(
                status_code=400,
                detail="Cannot remove the last super_admin",
            )

    # Preserve other app_metadata keys; only the role changes.
    app_meta = _app_metadata(target)
    app_meta["role"] = new_role
    admin.update_user_by_id(user_id, {"app_metadata": app_meta})

    _audit_rbac(
        sb, actor, AUDIT_ROLE_CHANGE,
        target_user_id=user_id,
        target_email=getattr(target, "email", None),
        old_role=old_role,
        new_role=new_role,
        reason=body.reason,
        route="PUT /api/admin/users/{user_id}/role",
    )
    return {
        "ok": True,
        "user_id": user_id,
        "old_role": old_role,
        "new_role": new_role,
        "requires_session_refresh": True,
    }


@router.post("/users/create")
def admin_create_user(body: AdminCreateBody, actor: dict = Depends(require_super_admin)) -> dict:
    """Create a staff user with a canonical auth role (super_admin only)."""
    role = _validate_role_input(body.role)
    if "@" not in body.email or "." not in body.email:
        raise HTTPException(status_code=400, detail="Invalid email")
    if not body.password or len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    sb = get_supabase_admin()
    admin = _auth_admin(sb)
    created = _as_user(
        admin.create_user(
            {
                "email": body.email,
                "password": body.password,
                "email_confirm": True,
                "user_metadata": {"name": body.name} if body.name else {},
                "app_metadata": {"role": role, "scope": body.scope},
            }
        )
    )
    new_id = getattr(created, "id", None)
    _audit_rbac(
        sb, actor, AUDIT_ADMIN_INVITE,
        target_user_id=new_id,
        target_email=body.email,
        old_role=None,
        new_role=role,
        reason=None,
        route="POST /api/admin/users/create",
    )
    return {
        "ok": True,
        "user": {"id": new_id, "email": body.email, "role": role, "scope": body.scope},
    }


def _force_signout(sb, user_id: str) -> dict:
    """Best-effort revocation of a user's sessions.

    Strategy (Step 4):
      1. Prefer ``auth.admin.sign_out(user_id)`` IFF the SDK exposes a
         by-user-id signout. supabase-auth 2.29's ``sign_out(jwt, scope)`` is
         session/JWT-scoped, not user-id-scoped, so it is intentionally NOT
         used here (passing a user id as a JWT would no-op silently).
      2. Else cycle a short ``ban_duration`` via ``update_user_by_id`` to
         invalidate the active session, then immediately unban. This is
         best-effort: existing access tokens stay valid until they expire,
         but refresh is blocked so the next refresh forces a re-login.
      3. Else report ``signout_supported: false`` — the installed gotrue
         build exposes neither path (documented in AGENTS.md).
    """
    admin = _auth_admin(sb)
    fn = getattr(admin, "sign_out", None)
    if callable(fn):
        try:
            params = list(inspect.signature(fn).parameters)
        except (TypeError, ValueError):
            params = []
        # Only a by-user-id signout is usable here. Skip the jwt-scoped one.
        if params and params[0] not in {"jwt", "token", "access_token"}:
            try:
                fn(user_id)
                return {"signout_supported": True, "method": "sign_out"}
            except Exception as exc:  # noqa: BLE001
                logger.warning("force_signout.sign_out failed: %s", exc)
    try:
        admin.update_user_by_id(user_id, {"ban_duration": "1h"})
        admin.update_user_by_id(user_id, {"ban_duration": "none"})
        return {"signout_supported": True, "method": "ban_cycle"}
    except Exception as exc:  # noqa: BLE001
        logger.warning("force_signout.ban_cycle failed: %s", exc)
        return {"signout_supported": False}


@router.post("/users/{user_id}/force-signout")
def force_signout_user(user_id: str, actor: dict = Depends(require_super_admin)) -> dict:
    """Force-sign-out a user (super_admin only)."""
    sb = get_supabase_admin()
    admin = _auth_admin(sb)
    target_email = None
    try:
        target = _as_user(admin.get_user_by_id(user_id))
        target_email = getattr(target, "email", None)
    except Exception:  # noqa: BLE001
        pass
    result = _force_signout(sb, user_id)
    _audit_rbac(
        sb, actor, AUDIT_FORCE_SIGNOUT,
        target_user_id=user_id,
        target_email=target_email,
        reason=None,
        route="POST /api/admin/users/{user_id}/force-signout",
    )
    return {"ok": True, "requires_session_refresh": True, **result}
