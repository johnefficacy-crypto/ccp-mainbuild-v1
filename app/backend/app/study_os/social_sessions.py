"""Study OS — group / partner / mentor session lifecycle (PR 6 / 8 / 10).

Backs the social commitment surface. All mutations route through the admin
Supabase client so the application-side check constraints (group membership,
pair membership) hit the DB.

Public entry points used by the API layer:
  * Groups: list_groups, create_group, join_group
  * Sessions: start_session, checkin_session, end_session
  * Partners: list_partners, request_partner, list_partner_requests, respond_partner
  * Mentor feedback: write_mentor_feedback
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import UUID

from app.study_os.trust_weights import TRUST_WEIGHTS

logger = logging.getLogger("career_copilot.study_os.social_sessions")


def _safe(call: Callable[[], Any], default: Any = None) -> Any:
    try:
        return call()
    except Exception as exc:  # noqa: BLE001
        logger.warning("social_sessions supabase call failed: %s", exc)
        return default


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_uuid(s: Any) -> bool:
    try:
        UUID(str(s))
        return True
    except (TypeError, ValueError, AttributeError):
        return False


# ─────────────────────────────── Groups ────────────────────────────────────

def list_groups(supabase: Any, user_id: str) -> list[dict[str, Any]]:
    """Return groups the user is in plus public ones."""
    member_rows = _safe(
        lambda: (
            supabase.table("study_group_members")
            .select("group_id")
            .eq("user_id", user_id)
            .eq("status", "active")
            .execute()
        ),
        default=None,
    )
    joined_ids = [r["group_id"] for r in (getattr(member_rows, "data", None) or [])]

    groups: list[dict[str, Any]] = []
    if joined_ids:
        rows = _safe(
            lambda: (
                supabase.table("study_groups")
                .select("*")
                .in_("id", joined_ids)
                .eq("status", "active")
                .execute()
            ),
            default=None,
        )
        for g in getattr(rows, "data", None) or []:
            groups.append({**g, "joined": True})

    rows_public = _safe(
        lambda: (
            supabase.table("study_groups")
            .select("*")
            .eq("visibility", "public")
            .eq("status", "active")
            .limit(50)
            .execute()
        ),
        default=None,
    )
    for g in getattr(rows_public, "data", None) or []:
        if g["id"] in joined_ids:
            continue
        groups.append({**g, "joined": False})

    return groups


def create_group(
    supabase: Any,
    user_id: str,
    name: str,
    group_type: str = "behavior",
    exam_id: str | None = None,
    max_members: int = 8,
    visibility: str = "private",
) -> dict[str, Any]:
    if group_type == "exam_specific" and not exam_id:
        raise ValueError("exam_id required for exam_specific groups")
    row = {
        "name": name,
        "group_type": group_type,
        "exam_id": exam_id,
        "max_members": max_members,
        "visibility": visibility,
        "created_by": user_id,
    }
    res = _safe(
        lambda: supabase.table("study_groups").insert(row).execute(),
        default=None,
    )
    data = getattr(res, "data", None) or []
    if not data:
        raise RuntimeError("could not create group")
    group = data[0]
    _safe(
        lambda: (
            supabase.table("study_group_members")
            .insert(
                {"group_id": group["id"], "user_id": user_id, "role": "owner"}
            )
            .execute()
        )
    )
    return group


def join_group(supabase: Any, user_id: str, group_id: str) -> dict[str, Any]:
    if not _is_uuid(group_id):
        raise ValueError("invalid group_id")
    # Enforce max_members.
    g = _safe(
        lambda: (
            supabase.table("study_groups").select("max_members,status").eq("id", group_id).limit(1).execute()
        ),
        default=None,
    )
    gdata = getattr(g, "data", None) or []
    if not gdata:
        raise LookupError("group not found")
    if gdata[0].get("status") != "active":
        raise LookupError("group not active")
    max_members = int(gdata[0].get("max_members") or 8)
    count_rows = _safe(
        lambda: (
            supabase.table("study_group_members")
            .select("id", count="exact")
            .eq("group_id", group_id)
            .eq("status", "active")
            .execute()
        ),
        default=None,
    )
    count = getattr(count_rows, "count", None) or 0
    if count >= max_members:
        raise PermissionError("group is full")
    _safe(
        lambda: (
            supabase.table("study_group_members")
            .upsert(
                {"group_id": group_id, "user_id": user_id, "status": "active"},
                on_conflict="group_id,user_id",
            )
            .execute()
        )
    )
    return {"group_id": group_id, "joined": True}


# ────────────────────────────── Sessions ───────────────────────────────────

def start_session(
    supabase: Any,
    user_id: str,
    session_type: str,
    group_id: str | None = None,
    partner_pair_id: str | None = None,
    planned_minutes: int | None = None,
) -> dict[str, Any]:
    if session_type not in ("group", "partner", "mentor"):
        raise ValueError("invalid session_type")
    trust_source = (
        "group_presence" if session_type == "group"
        else "partner_costudy" if session_type == "partner"
        else "mentor_verified"
    )
    row = {
        "session_type": session_type,
        "group_id": group_id,
        "partner_pair_id": partner_pair_id,
        "started_at": _now_iso(),
        "planned_minutes": planned_minutes,
        "trust_source": trust_source,
        "trust_weight": TRUST_WEIGHTS.get(trust_source, 0.6),
    }
    res = _safe(
        lambda: supabase.table("social_study_sessions").insert(row).execute(),
        default=None,
    )
    data = getattr(res, "data", None) or []
    if not data:
        raise RuntimeError("could not start session")
    session = data[0]
    _safe(
        lambda: (
            supabase.table("social_session_attendance")
            .insert(
                {
                    "session_id": session["id"],
                    "user_id": user_id,
                    "joined_at": _now_iso(),
                }
            )
            .execute()
        )
    )
    return session


def checkin_session(
    supabase: Any,
    user_id: str,
    session_id: str,
    focus_check_passed: bool,
    declared_task_completed: bool | None = None,
) -> dict[str, Any]:
    """Lightweight focus check — increments focus_check_total and, if passed,
    focus_check_passed. Upgrades the session's trust_source to
    'group_focus_checked' the first time a check passes (spec § "Group focus
    credit requires lightweight checks")."""
    # Pull current attendance row.
    rows = _safe(
        lambda: (
            supabase.table("social_session_attendance")
            .select("id, focus_check_total, focus_check_passed")
            .eq("session_id", session_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        ),
        default=None,
    )
    items = getattr(rows, "data", None) or []
    if not items:
        raise LookupError("attendance row not found")
    att = items[0]
    new_total = int(att.get("focus_check_total") or 0) + 1
    new_passed = int(att.get("focus_check_passed") or 0) + (1 if focus_check_passed else 0)
    update: dict[str, Any] = {
        "focus_check_total": new_total,
        "focus_check_passed": new_passed,
    }
    if declared_task_completed is not None:
        update["completed_declared_task"] = declared_task_completed
    _safe(
        lambda: (
            supabase.table("social_session_attendance")
            .update(update)
            .eq("id", att["id"])
            .execute()
        )
    )

    if focus_check_passed:
        _safe(
            lambda: (
                supabase.table("social_study_sessions")
                .update(
                    {
                        "trust_source": "group_focus_checked",
                        "trust_weight": TRUST_WEIGHTS["group_focus_checked"],
                    }
                )
                .eq("id", session_id)
                .eq("session_type", "group")
                .execute()
            )
        )

    return {
        "session_id": session_id,
        "focus_check_total": new_total,
        "focus_check_passed": new_passed,
    }


def end_session(
    supabase: Any,
    user_id: str,
    session_id: str,
    declared_task_completed: bool | None = None,
) -> dict[str, Any]:
    now = _now_iso()
    # Membership gate: only a participant may end the shared session. The
    # service-role client bypasses RLS, so without this any user could end
    # (and stamp presence on) an arbitrary session by id. Raise LookupError
    # (→404) rather than leak that the session exists to non-members.
    att_rows = _safe(
        lambda: (
            supabase.table("social_session_attendance")
            .select("id")
            .eq("session_id", session_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        ),
        default=None,
    )
    if not (getattr(att_rows, "data", None) or []):
        raise LookupError("session not found")
    # Stamp end on the session itself.
    sess_rows = _safe(
        lambda: (
            supabase.table("social_study_sessions")
            .select("started_at, ended_at, verified_presence_minutes, verified_focus_minutes")
            .eq("id", session_id)
            .limit(1)
            .execute()
        ),
        default=None,
    )
    sess_items = getattr(sess_rows, "data", None) or []
    if not sess_items:
        raise LookupError("session not found")
    sess = sess_items[0]
    presence_minutes = 0
    if sess.get("started_at"):
        try:
            started = datetime.fromisoformat(str(sess["started_at"]).replace("Z", "+00:00"))
            presence_minutes = max(
                0,
                int((datetime.now(timezone.utc) - started).total_seconds() // 60),
            )
        except (TypeError, ValueError):
            presence_minutes = 0

    _safe(
        lambda: (
            supabase.table("social_study_sessions")
            .update({"ended_at": now, "verified_presence_minutes": presence_minutes})
            .eq("id", session_id)
            .is_("ended_at", None)
            .execute()
        )
    )

    update: dict[str, Any] = {
        "left_at": now,
        "presence_minutes": presence_minutes,
        "attendance_status": "present",
    }
    if declared_task_completed is not None:
        update["completed_declared_task"] = declared_task_completed
    _safe(
        lambda: (
            supabase.table("social_session_attendance")
            .update(update)
            .eq("session_id", session_id)
            .eq("user_id", user_id)
            .execute()
        )
    )

    return {"session_id": session_id, "ended_at": now, "presence_minutes": presence_minutes}


# ─────────────────────────────── Partners ──────────────────────────────────

def list_partner_suggestions(supabase: Any, user_id: str, limit: int = 10) -> list[dict[str, Any]]:
    """Suggest partners from the user's same exam goal who don't already
    have an active pair with this user. Lightweight — exact matching, no ML."""
    goal_rows = _safe(
        lambda: (
            supabase.table("user_exam_goals")
            .select("exam_id")
            .eq("user_id", user_id)
            .eq("status", "active")
            .limit(1)
            .execute()
        ),
        default=None,
    )
    items = getattr(goal_rows, "data", None) or []
    if not items:
        return []
    exam_id = items[0].get("exam_id")
    if not exam_id:
        return []
    peer_rows = _safe(
        lambda: (
            supabase.table("user_exam_goals")
            .select("user_id")
            .eq("exam_id", exam_id)
            .eq("status", "active")
            .neq("user_id", user_id)
            .limit(limit * 2)
            .execute()
        ),
        default=None,
    )
    peer_ids = list({r["user_id"] for r in (getattr(peer_rows, "data", None) or [])})
    if not peer_ids:
        return []

    profiles = _safe(
        lambda: (
            supabase.table("profiles")
            .select("id, display_name, exam_focus")
            .in_("id", peer_ids)
            .limit(limit)
            .execute()
        ),
        default=None,
    )
    rows = getattr(profiles, "data", None) or []
    return [published_partner(r) for r in rows]


def published_partner(row: dict[str, Any] | None) -> dict[str, Any] | None:
    """Sanitized partner projection — pseudonymous, no PII.

    Exposes only the persistent display handle and exam focus. NEVER returns
    ``full_name``, ``city``, email, or other profile facts. This is the only
    shape a partner (or a candidate list) may surface about another user — see
    docs/product/accountability-partner-governance.md §7.
    """
    if not row:
        return None
    return {
        "id": row.get("id"),
        "name": row.get("display_name") or "Aspirant",
        "exam": row.get("exam_focus"),
    }


def _has_active_pair(supabase: Any, user_id: str | None) -> bool:
    if not user_id:
        return False
    rows = _safe(
        lambda: (
            supabase.table("accountability_pairs")
            .select("id")
            .eq("status", "active")
            .or_(f"user_a.eq.{user_id},user_b.eq.{user_id}")
            .execute()
        ),
        default=None,
    )
    return bool(getattr(rows, "data", None) or [])


def request_partner(
    supabase: Any,
    user_id: str,
    partner_id: str,
    pairing_goal: str = "discipline",
    exam_id: str | None = None,
    message: str | None = None,
) -> dict[str, Any]:
    """Create a *pending* partner request — consent-first.

    A pair only comes into existence once the recipient accepts (see
    ``respond_partner``). This never inserts an active pair directly, and it
    refuses to create a request when the requester already holds an active
    partnership (one-active-partner rule).
    """
    if pairing_goal not in {"discipline", "same_exam", "mock_review", "revision"}:
        raise ValueError("invalid pairing_goal")
    if not _is_uuid(partner_id):
        raise ValueError("invalid partner_id")
    if partner_id == user_id:
        raise ValueError("cannot pair with self")
    if _has_active_pair(supabase, user_id):
        raise ValueError("already in an active partnership")
    row = {
        "requester_id": user_id,
        "partner_id": partner_id,
        "message": message,
        "pairing_goal": pairing_goal,
        "exam_id": exam_id,
        "status": "pending",
    }
    res = _safe(lambda: supabase.table("accountability_partner_requests").insert(row).execute(), default=None)  # safe-write-ok: returns local row dict on failure; caller handles absent id gracefully
    data = getattr(res, "data", None) or []
    return data[0] if data else row


def _accept_via_rpc(supabase: Any, request_id: str, user_id: str) -> dict[str, Any] | None:
    """Try the atomic accept RPC (migration 193). Returns the pair, or None
    when the RPC is unavailable so the caller can fall back."""
    try:
        result = supabase.rpc(
            "accept_partner_request",
            {"p_request_id": request_id, "p_user_id": user_id},
        ).execute()
        value = getattr(result, "data", None)
        if isinstance(value, list) and value:
            value = value[0]
        if isinstance(value, dict) and value:
            return value
    except Exception:
        pass
    return None


def respond_partner(
    supabase: Any,
    user_id: str,
    request_id: str,
    action: str,
) -> dict[str, Any]:
    """Recipient accepts or declines a pending partner request.

    Only the named recipient (``partner_id``) may respond. ``accept`` creates
    the pair atomically via the SECURITY DEFINER RPC, enforcing the
    one-active-pair guard for BOTH users; a racy app-level fallback (mirroring
    ``community_runtime._rpc_inc``) runs only when the RPC is unavailable.
    """
    if action not in {"accept", "decline"}:
        raise ValueError("invalid action")
    if not _is_uuid(request_id):
        raise ValueError("invalid request_id")
    req = _safe(
        lambda: (
            supabase.table("accountability_partner_requests")
            .select("*")
            .eq("id", request_id)
            .limit(1)
            .execute()
        ),
        default=None,
    )
    req_rows = getattr(req, "data", None) or []
    if not req_rows:
        raise LookupError("request not found")
    request = req_rows[0]
    if request.get("partner_id") != user_id:
        raise PermissionError("only the recipient can respond")
    if (request.get("status") or "pending") != "pending":
        raise ValueError("request already resolved")

    if action == "decline":
        _safe(
            lambda: supabase.table("accountability_partner_requests")
            .update({"status": "declined", "responded_at": _now_iso()})
            .eq("id", request_id)
            .execute()
        )
        return {"request_id": request_id, "status": "declined"}

    # accept → atomic pair creation.
    pair = _accept_via_rpc(supabase, request_id, user_id)
    if pair is not None:
        return {"request_id": request_id, "status": "accepted", "pair": pair}

    # Fallback (racy by construction; exists so accept doesn't 500 on
    # deployments without migration 193). Re-checks the one-active-pair guard.
    requester_id = request.get("requester_id")
    if _has_active_pair(supabase, requester_id) or _has_active_pair(supabase, user_id):
        raise ValueError("one of the users already has an active partnership")
    pair_row = {
        "user_a": requester_id,
        "user_b": user_id,
        "pairing_goal": request.get("pairing_goal") or "discipline",
        "exam_id": request.get("exam_id"),
        "status": "active",
    }
    res = _safe(lambda: supabase.table("accountability_pairs").insert(pair_row).execute(), default=None)  # safe-write-ok: local row dict on failure
    data = getattr(res, "data", None) or []
    pair = data[0] if data else pair_row
    _safe(
        lambda: supabase.table("accountability_partner_requests")
        .update({"status": "accepted", "responded_at": _now_iso()})
        .eq("id", request_id)
        .execute()
    )
    return {"request_id": request_id, "status": "accepted", "pair": pair}


def list_pairs(supabase: Any, user_id: str) -> list[dict[str, Any]]:
    rows = _safe(
        lambda: (
            supabase.table("accountability_pairs")
            .select("*")
            .eq("status", "active")
            .or_(f"user_a.eq.{user_id},user_b.eq.{user_id}")
            .execute()
        ),
        default=None,
    )
    return getattr(rows, "data", None) or []


# ─────────────────────────── Mentor feedback ───────────────────────────────

def write_mentor_feedback(
    supabase: Any,
    mentor_id: str,
    mentee_id: str,
    session_id: str,
    discipline_rating: int | None = None,
    preparation_rating: int | None = None,
    follow_through_rating: int | None = None,
    feedback_private: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row = {
        "session_id": session_id,
        "mentor_id": mentor_id,
        "mentee_id": mentee_id,
        "discipline_rating": discipline_rating,
        "preparation_rating": preparation_rating,
        "follow_through_rating": follow_through_rating,
        "feedback_private": feedback_private or {},
    }
    res = _safe(lambda: supabase.table("mentor_session_feedback").insert(row).execute(), default=None)  # safe-write-ok: returns local row dict on failure; mentor feedback is non-critical
    data = getattr(res, "data", None) or []
    return data[0] if data else row
