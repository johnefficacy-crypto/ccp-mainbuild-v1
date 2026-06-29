"""Supabase access-token verification for FastAPI.

Phase 1.5: MongoDB + custom JWT have been removed. Authentication is now
delegated entirely to Supabase Auth. Every protected backend route validates
the access token by calling Supabase's auth admin endpoint.

Concurrency notes:

* Dashboard boot fans out 5+ protected requests with the same bearer
  inside a second. Without a cross-request cache each request issues
  its own ``auth/v1/user`` round-trip to Supabase. A 45-second TTL
  cache collapses identical-token requests to one Supabase call within
  the TTL window. Invalid tokens are never cached.
* Even with a cache, three first-callers can race the cache-miss check
  in the millisecond window before any has written. The per-token
  ``threading.Lock`` adds single-flight semantics so only one thread
  per token issues the round-trip; the rest block on the lock and pick
  up the populated cache entry. ``get_current_user`` is a sync FastAPI
  dependency running in the threadpool, so ``threading.Lock`` is the
  right primitive — not ``asyncio.Lock``.
"""
from __future__ import annotations

import hashlib
import logging
import os
import threading
from typing import Annotated, Any

from cachetools import TTLCache
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db.supabase_client import get_supabase_admin

logger = logging.getLogger("career_copilot.auth")
security = HTTPBearer(auto_error=False)

# ── Canonical auth roles ───────────────────────────────────────────────
# These are the ONLY auth roles. ``mentor`` is a domain capability, not a
# role (see profiles.is_mentor / /api/auth/me capabilities.mentor). The
# backend is authoritative; frontend role gates are UX only.
AUTH_ROLES = frozenset({"user", "admin", "super_admin"})
ADMIN_ROLES = frozenset({"admin", "super_admin"})


def _auth_debug_enabled() -> bool:
    """Optional diagnostic logging gated by ``AUTH_DEBUG=1``.

    Default OFF in prod. When enabled, the cache hit/miss path emits
    DEBUG records keyed by the first 8 chars of the SHA-256 of the
    token — never the raw token. Useful for confirming the single-flight
    lock actually collapses a burst within a single worker before
    chasing a "multi-worker cache fragmentation" hypothesis.
    """
    return os.environ.get("AUTH_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}


def _short_token_id(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:8]


def _adbg(stage: str, token: str, **extra: Any) -> None:
    if not _auth_debug_enabled():
        return
    extras = " ".join(f"{k}={v}" for k, v in extra.items())
    logger.debug("auth.%s tok=%s %s", stage, _short_token_id(token), extras)


# ── Cross-request token cache ──────────────────────────────────────────
_TOKEN_CACHE_TTL_SECONDS = 45
_TOKEN_CACHE_MAXSIZE = 10000
_token_cache: TTLCache = TTLCache(
    maxsize=_TOKEN_CACHE_MAXSIZE, ttl=_TOKEN_CACHE_TTL_SECONDS
)
_token_cache_lock = threading.Lock()

# ── Per-token single-flight ────────────────────────────────────────────
_token_flight_locks: dict[str, threading.Lock] = {}
_token_flight_guard = threading.Lock()


def _token_cache_key(token: str) -> str:
    # Hash so we never hold raw tokens in memory longer than necessary
    # and so cache dumps in tracebacks/logs do not leak credentials.
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _flight_lock_for(key: str) -> threading.Lock:
    """Return the per-token lock, creating it on first use.

    The guard lock makes the get-or-create atomic so two concurrent
    first-callers don't end up with two different lock objects (which
    would let both issue the Supabase round-trip).
    """
    with _token_flight_guard:
        lock = _token_flight_locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _token_flight_locks[key] = lock
        return lock


def _release_flight_lock(key: str) -> None:
    """Drop the per-token lock once the cache holds a fresh entry.

    Failed/invalid tokens don't populate the cache, so they also don't
    leave a lock behind here — preventing unbounded growth under
    brute-force / DoS retry patterns.
    """
    with _token_flight_guard:
        _token_flight_locks.pop(key, None)


def invalidate_token(token: str) -> None:
    """Drop ``token`` from the cross-request auth cache.

    Wire this into any logout route. The frontend currently calls
    Supabase ``signOut()`` directly so there is no backend logout
    handler to wire into yet; this helper is exposed for future use
    and for tests.
    """
    if not token:
        return
    key = _token_cache_key(token)
    with _token_cache_lock:
        _token_cache.pop(key, None)
    _release_flight_lock(key)


def _cache_get(token: str) -> dict | None:
    with _token_cache_lock:
        return _token_cache.get(_token_cache_key(token))


def _cache_set(token: str, user: dict) -> None:
    with _token_cache_lock:
        _token_cache[_token_cache_key(token)] = user


def _serialize_user(user: Any, claims: dict | None = None) -> dict:
    """Normalise a Supabase user object (gotrue User) into a plain dict."""
    claims = claims or {}
    metadata = (
        getattr(user, "user_metadata", None)
        or getattr(user, "raw_user_meta_data", None)
        or {}
    )
    app_metadata = (
        getattr(user, "app_metadata", None)
        or getattr(user, "raw_app_meta_data", None)
        or {}
    )
    # Role resolution — ONLY ``app_metadata.role`` is trusted.
    #   * app_metadata (raw_app_meta_data) is service-role-only: a user
    #     cannot write it. This is the canonical source per migration
    #     134/151 and this module's docstring.
    #   * user_metadata (raw_user_meta_data) and the JWT ``role`` claim
    #     (which merely reflects user_metadata) are CLIENT-WRITABLE via
    #     ``supabase.auth.updateUser({ data: { role: ... } })``. Consulting
    #     them as a fallback let any user self-assign ``super_admin`` and
    #     pass require_admin/require_super_admin — a full privilege
    #     escalation. They are therefore deliberately NOT consulted.
    # Absent/unexpected app_metadata.role coerces to "user".
    role = app_metadata.get("role")
    # Mentor is no longer an auth role; anything outside the canonical set
    # (including a missing role) coerces to "user" so a stale/unexpected
    # role can never grant access.
    if role not in AUTH_ROLES:
        if role is not None:
            logger.warning("auth.role_coerced_to_user original_role=%s", role)
        role = "user"
    permissions = app_metadata.get("permissions") or []
    if isinstance(permissions, str):
        permissions = [permissions]
    # Supabase anonymous sign-ins set `is_anonymous=true` in the JWT claims
    # and on `app_metadata`. Either source is authoritative — we coerce to
    # bool so downstream code can rely on a stable shape.
    is_anonymous = bool(
        claims.get("is_anonymous")
        or app_metadata.get("is_anonymous")
        or getattr(user, "is_anonymous", False)
    )
    return {
        "id": getattr(user, "id", None) or claims.get("sub"),
        # For phone-OTP users the Supabase auth email is null; the signup
        # form stores the optional receipt email in user_metadata.email.
        "email": getattr(user, "email", None) or claims.get("email") or metadata.get("email"),
        "phone": getattr(user, "phone", None)
        or (user.get("phone") if isinstance(user, dict) else None)
        or claims.get("phone"),
        "name": metadata.get("name") or metadata.get("full_name"),
        "avatar": metadata.get("avatar_url"),
        "role": role,
        "onboarded": bool(metadata.get("onboarded", False)),
        "plan": metadata.get("plan", "free"),
        "goal_exams": metadata.get("goal_exams", []),
        "permissions": permissions,
        "is_anonymous": is_anonymous,
        "created_at": getattr(user, "created_at", None),
        "claims": claims,
    }


def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> dict:
    """Validate the Supabase access token and return the resolved user.

    The resolved user is memoised on ``request.state`` keyed by token so
    a single FastAPI request that fans out to multiple protected
    dependencies only hits ``auth/v1/user`` once. Lifetime = this
    request only.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    token = credentials.credentials

    # 1. Request-scoped memo (single FastAPI request fanout).
    cached = getattr(request.state, "current_user", None)
    cached_token = getattr(request.state, "current_user_token", None)
    if cached is not None and cached_token == token:
        _adbg("request_memo_hit", token)
        return cached

    # 2. Cross-request TTL cache. Invalid tokens are NEVER cached.
    cross_request_cached = _cache_get(token)
    if cross_request_cached is not None:
        request.state.current_user = cross_request_cached
        request.state.current_user_token = token
        _adbg("ttl_cache_hit", token)
        return cross_request_cached

    # 3. Single-flight: only one thread per token issues the Supabase
    # round-trip when the cache is cold. Concurrent siblings block on
    # the per-token lock and pick up the populated cache below.
    cache_key = _token_cache_key(token)
    flight_lock = _flight_lock_for(cache_key)
    _adbg("flight_lock_wait", token)
    with flight_lock:
        _adbg("flight_lock_acquired", token)
        # Double-checked locking: by the time we acquired the lock the
        # leader may already have populated the cache.
        cross_request_cached = _cache_get(token)
        if cross_request_cached is not None:
            request.state.current_user = cross_request_cached
            request.state.current_user_token = token
            _release_flight_lock(cache_key)
            _adbg("flight_followed_leader", token)
            return cross_request_cached
        _adbg("flight_leader_round_trip", token)

        try:
            admin = get_supabase_admin()
            # Supabase admin client validates the JWT with the project's
            # secret and returns the canonical user object.
            result = admin.auth.get_user(token)
        except Exception as exc:  # noqa: BLE001
            # Invalid tokens are NEVER cached. Drop the per-token lock
            # so the next retry runs cleanly.
            _release_flight_lock(cache_key)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid Supabase access token: {exc}",
            )

        user = getattr(result, "user", None)
        if user is None:
            _release_flight_lock(cache_key)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Supabase returned no user for token",
            )

        # Decode unverified claims for role/sub fallback (signature
        # already verified by Supabase).
        claims: dict = {}
        try:
            import jwt

            claims = jwt.decode(token, options={"verify_signature": False})
        except Exception:
            claims = {}

        serialised = _serialize_user(user, claims)
        request.state.current_user = serialised
        request.state.current_user_token = token
        _cache_set(token, serialised)
        # Cache is now warm — the per-token lock has served its purpose.
        _release_flight_lock(cache_key)
        return serialised


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Allow any admin-tier role (``admin`` or ``super_admin``).

    Centralised second-layer gate for broad admin-only routes. A missing or
    invalid token is already rejected with 401 by ``get_current_user``, so
    here we only enforce identity class + role membership.
    """
    if user.get("is_anonymous"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anonymous users cannot access admin",
        )
    if user.get("role") not in ADMIN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Admin role required (allowed: {sorted(ADMIN_ROLES)})",
        )
    return user


def require_super_admin(user: dict = Depends(get_current_user)) -> dict:
    """Allow only ``super_admin``.

    ``super_admin`` passes both this and :func:`require_admin`; ``admin`` and
    ``user`` are rejected with 403.
    """
    if user.get("is_anonymous"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anonymous users cannot access admin",
        )
    if user.get("role") != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="super_admin role required (allowed: ['super_admin'])",
        )
    return user


def require_permission(permission: str):
    def _dep(user: dict = Depends(get_current_user)) -> dict:
        # Anonymous users can never satisfy a permission check — short-
        # circuit before the perm match so the 403 reason is unambiguous.
        # Restored alongside ``get_current_user_required_permanent`` —
        # the same dropped-on-merge that broke reminders.py also lost
        # this guard.
        if user.get("is_anonymous"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Anonymous users cannot access this resource",
            )
        # super_admin bypasses explicit permission checks; admin/user must
        # carry the granular permission.
        if user.get("role") == "super_admin":
            return user
        perms = set(user.get("permissions") or [])
        if permission not in perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission}",
            )
        return user
    return _dep


def get_current_user_required_permanent(
    user: dict = Depends(get_current_user),
) -> dict:
    """Like :func:`get_current_user` but rejects anonymous Supabase users.

    Use on endpoints that demand a permanent identity (payments, document
    upload, anything that mutates persistent state on behalf of a user we
    expect to come back). Anonymous callers get a 403 so the frontend can
    prompt them to link a real identity.

    Restored after a merge between
    ``perf: fix 1 — auth token cache`` (9357403) and
    ``fix(backend): … auth single-flight …`` (54e8bba) silently dropped
    the function, leaving ``app/api/reminders.py`` import-broken on
    ``main``. Without this, server.py and five test modules fail at
    collection — re-adding it unblocks the rest of the suite.
    """
    if user.get("is_anonymous"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anonymous users cannot access this resource",
        )
    return user


def get_current_user_required_anonymous(
    user: dict = Depends(get_current_user),
) -> dict:
    """Like :func:`get_current_user` but rejects *permanent* Supabase users.

    The mirror of :func:`get_current_user_required_permanent`. Used by the
    merge-claim *mint* endpoint: only an anonymous session may create a claim
    over its own onboarding progress, so a permanent caller (who has nothing to
    rescue) is rejected with a 403.
    """
    if not user.get("is_anonymous"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="An anonymous session is required for this resource",
        )
    return user


def get_optional_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> dict | None:
    if credentials is None or not credentials.credentials:
        return None
    # Token was supplied — validate it. An invalid/expired token must surface
    # as 401 so callers don't silently degrade to anonymous behaviour. Only
    # the "no Authorization header" path should return None.
    return get_current_user(request, credentials)
