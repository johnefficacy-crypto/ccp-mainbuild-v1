"""Anonymous → permanent profile merge claims.

The v2 onboarding flow writes a guest's progress against a Supabase anonymous
``profiles.id``. ``linkIdentity`` normally carries that id into the permanent
account, but when the chosen Google email already belongs to a *different*
permanent profile Supabase refuses the link. The frontend then has to sign the
anon user out and send them through the normal login — at which point the anon
profile (and its onboarding progress) would be orphaned.

These two endpoints bridge that gap with a short-lived, single-use token:

* ``POST /api/onboarding/merge-claim/create`` — minted by the *anonymous*
  session. Stores ``sha256(token)`` + a 15-minute expiry against the anon
  profile and returns the plaintext token once.
* ``POST /api/onboarding/merge-claim/consume`` — called by the *permanent*
  session after Google login. Hashes the token, runs the atomic merge RPC
  (``consume_profile_merge_claim``), then best-effort deletes the now-empty anon
  auth user. Idempotent: replaying a token returns the prior merge result.

The token is the bearer of authority: a permanent session that presents a valid
token merges the referenced anon profile into *itself*. That is deliberate — the
plaintext is only ever held by the browser that just minted it.
"""
from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.auth import (
    get_current_user_required_anonymous,
    get_current_user_required_permanent,
)
from app.db.supabase_client import get_supabase_admin

logger = logging.getLogger("career_copilot.profile.merge_claim")

router = APIRouter(prefix="/onboarding", tags=["onboarding-merge"])

CLAIM_TTL_MINUTES = 15

# RPC status → HTTP status for the consume endpoint.
_CONSUME_ERROR_STATUS: dict[str, int] = {
    "not_found": status.HTTP_404_NOT_FOUND,
    "expired": status.HTTP_410_GONE,
    "anon_missing": status.HTTP_409_CONFLICT,
    "self_merge": status.HTTP_409_CONFLICT,
}


class MergeClaimConsumeBody(BaseModel):
    token: str = Field(..., min_length=16, max_length=512)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/merge-claim/create")
async def create_merge_claim(
    user: dict = Depends(get_current_user_required_anonymous),
) -> dict[str, Any]:
    """Mint a single-use merge token for the calling anonymous profile."""
    supabase = get_supabase_admin()
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=CLAIM_TTL_MINUTES)

    try:
        supabase.table("anonymous_profile_merge_claims").insert(
            {
                "anonymous_user_id": user["id"],
                "claim_token_hash": _hash_token(token),
                "expires_at": expires_at.isoformat(),
            }
        ).execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning("merge-claim create failed for %s: %s", user.get("id"), exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create merge claim",
        ) from exc

    # The plaintext token is returned exactly once and never persisted.
    return {"token": token, "expires_at": expires_at.isoformat()}


@router.post("/merge-claim/consume")
async def consume_merge_claim(
    body: MergeClaimConsumeBody,
    user: dict = Depends(get_current_user_required_permanent),
) -> dict[str, Any]:
    """Consume a merge token, merging the referenced anon profile into the caller."""
    supabase = get_supabase_admin()
    token_hash = _hash_token(body.token)

    try:
        result = (
            supabase.rpc(
                "consume_profile_merge_claim",
                {"p_token_hash": token_hash, "p_permanent_user_id": user["id"]},
            )
            .execute()
            .data
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("merge-claim consume RPC failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Merge failed",
        ) from exc

    if not isinstance(result, dict):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Merge returned no result",
        )

    rpc_status = result.get("status")

    if rpc_status in _CONSUME_ERROR_STATUS:
        raise HTTPException(
            status_code=_CONSUME_ERROR_STATUS[rpc_status],
            detail=f"Merge claim {rpc_status}",
        )

    if rpc_status not in {"ok", "already_consumed"}:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected merge status: {rpc_status}",
        )

    # Fresh merge: tidy up the now-empty anonymous auth user. Best-effort — the
    # data merge already committed inside the RPC, and the daily cleanup cron is
    # the backstop. A replay (already_consumed) skips this; the user is gone.
    if rpc_status == "ok":
        anon_id = result.get("anonymous_user_id")
        if anon_id:
            try:
                admin = getattr(supabase.auth, "admin", None)
                if admin and hasattr(admin, "delete_user"):
                    admin.delete_user(anon_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "merge-claim consume: auth delete_user failed for %s: %s",
                    anon_id,
                    exc,
                )

    return {
        "ok": True,
        "already_consumed": rpc_status == "already_consumed",
        "merged": result.get("result") or {},
    }


__all__ = ["router"]
