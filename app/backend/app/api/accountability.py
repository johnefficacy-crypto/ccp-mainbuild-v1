"""Accountability runtime — mentor bookings backed by Supabase.

Supersedes the in-memory `/api/accountability/mentors/*` endpoints in
placeholders.py. Partners + groups already had a real (Supabase-backed)
implementation in placeholders' router_acc that we now lift out cleanly.
The marketplace mentor catalogue is still seed data, so mentor_slug is
stored alongside the optional mentor_id profile FK.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.auth import get_current_user, get_current_user_required_permanent
from app.db.supabase_client import get_supabase_admin
from app.payments import razorpay_client


router = APIRouter(prefix="/accountability", tags=["accountability"])


# Reuse the marketplace mentor catalogue from placeholders so the same
# slug → display data mapping is shared until profile-backed mentors land.
from app.api.placeholders import MENTORS  # noqa: E402


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_uuid(v: Any) -> bool:
    try:
        UUID(str(v))
        return True
    except (TypeError, ValueError, AttributeError):
        return False


def _shape_booking(row: dict) -> dict:
    return {
        "id": row.get("id"),
        "mentor_id": row.get("mentor_id"),
        "mentor_slug": row.get("mentor_slug"),
        "mentor_name": row.get("metadata", {}).get("mentor_name"),
        "slot": row.get("slot"),
        "duration_minutes": row.get("duration_minutes") or 60,
        "price_inr": row.get("price_inr"),
        "notes": row.get("notes"),
        "agenda": row.get("agenda"),
        "status": row.get("status"),
        "payment_id": row.get("payment_id"),
        "payment_status": row.get("payment_status"),
        "metadata": row.get("metadata") or {},
        "confirmed_at": row.get("confirmed_at"),
        "cancelled_at": row.get("cancelled_at"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def _resolve_mentor(mentor_id: str) -> tuple[str | None, str | None, dict | None]:
    """Resolve `mentor_id` into (profile_uuid, mentor_slug, catalogue_row)."""
    if _is_uuid(mentor_id):
        return mentor_id, None, None
    catalogue = next((m for m in MENTORS if m.get("id") == mentor_id), None)
    return None, mentor_id, catalogue


def _mentor_price_total(catalogue: dict | None, duration_minutes: int) -> int | None:
    """Server-derived booking price in whole INR (None => not bookable)."""
    price = (catalogue or {}).get("price_per_hour")
    if not price:
        return None
    duration_h = max(1, round(duration_minutes / 60))
    return int(price * duration_h)


class MentorOrderCreate(BaseModel):
    mentor_id: str
    slot: str | None = Field(default=None, description="ISO datetime or human label")
    duration_minutes: int = Field(default=60, ge=15, le=240)
    notes: str | None = None


class MentorBook(BaseModel):
    mentor_id: str
    slot: str | None = Field(default=None, description="ISO datetime or human label until structured scheduling lands")
    duration_minutes: int = Field(default=60, ge=15, le=240)
    notes: str | None = None
    # Razorpay handshake — the booking is only marked paid after the
    # server verifies these against the order it created (see /mentors/order).
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


@router.post("/mentors/order")
def create_mentor_order(
    body: MentorOrderCreate, user: dict = Depends(get_current_user_required_permanent)
) -> dict:
    """Create a Razorpay order for a mentor booking (amount fixed server-side).

    The amount and owner are pinned into the order's ``notes`` so booking
    confirmation can verify the client paid the right price as the right user.
    """
    _profile_uuid, slug, catalogue = _resolve_mentor(body.mentor_id)
    if not catalogue:
        raise HTTPException(status_code=404, detail="Mentor not found")
    price_total = _mentor_price_total(catalogue, body.duration_minutes)
    if not price_total:
        raise HTTPException(status_code=400, detail="Mentor is not bookable")
    order = razorpay_client.create_order(
        amount_inr=price_total,
        receipt=f"mentor_{slug}_{user['id'][:8]}",
        notes={
            "user_id": user["id"],
            "mentor_slug": slug,
            "kind": "mentor",
            "duration_minutes": body.duration_minutes,
            "price_inr": price_total,
        },
    )
    return {
        "order": {
            "id": order["id"],
            "amount": order["amount"],
            "currency": order.get("currency", "INR"),
            "key_id": razorpay_client.get_public_key_id(),
        },
        "mentor": {"slug": slug, "name": catalogue.get("name"), "price_inr": price_total},
    }


@router.post("/mentors/book")
def book_mentor(
    body: MentorBook, user: dict = Depends(get_current_user_required_permanent)
) -> dict:
    """Confirm a mentor booking AFTER verifying the Razorpay payment.

    Previously ``payment_status`` was set to ``captured`` from the mere
    presence of a client-supplied ``payment_id`` — anyone could forge a free
    paid booking. We now require the order/payment/signature triple, verify the
    signature with the Razorpay secret, re-fetch the order from Razorpay
    (authoritative) and bind amount + owner before crediting the booking. Fails
    closed: no valid, paid, owner-matched order => no captured booking.
    """
    _profile_uuid, slug, catalogue = _resolve_mentor(body.mentor_id)
    if not catalogue:
        raise HTTPException(status_code=404, detail="Mentor not found")
    profile_uuid = _profile_uuid
    price_total = _mentor_price_total(catalogue, body.duration_minutes)
    if not price_total:
        raise HTTPException(status_code=400, detail="Mentor is not bookable")

    # 1. Cryptographic proof the (order, payment) pair came from Razorpay.
    if not razorpay_client.verify_signature(
        body.razorpay_order_id, body.razorpay_payment_id, body.razorpay_signature
    ):
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    # 2. Re-fetch the order (authoritative) and bind EVERY server-pinned field
    #    (owner, amount, paid state, and the kind/mentor/duration in notes) so an
    #    order minted for a different mentor or duration — even at the same price
    #    — cannot be reused for this booking.
    try:
        order = razorpay_client.get_client().order.fetch(body.razorpay_order_id)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Could not verify order: {exc}")
    notes = (order or {}).get("notes") or {}
    if notes.get("user_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Order does not belong to this user")
    if int((order or {}).get("amount") or 0) != price_total * 100:
        raise HTTPException(status_code=400, detail="Payment amount mismatch")
    if (order or {}).get("status") != "paid":
        raise HTTPException(status_code=400, detail="Order is not paid")
    # Razorpay stores notes as strings — compare stringwise.
    if notes.get("kind") != "mentor":
        raise HTTPException(status_code=400, detail="Order is not a mentor order")
    if notes.get("mentor_slug") != slug:
        raise HTTPException(status_code=400, detail="Order mentor does not match booking")
    if str(notes.get("duration_minutes")) != str(body.duration_minutes):
        raise HTTPException(status_code=400, detail="Order duration does not match booking")

    sb = get_supabase_admin()
    # 3. Anti-replay: one captured booking per Razorpay order. Pre-check for a
    #    deterministic 409, with the UNIQUE index (migration 193) as the atomic
    #    backstop against a concurrent double-submit.
    existing = (
        sb.table("mentor_bookings")
        .select("id")
        .eq("razorpay_order_id", body.razorpay_order_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if existing:
        raise HTTPException(
            status_code=409, detail="This payment has already been used for a booking"
        )
    payload: dict[str, Any] = {
        "user_id": user["id"],
        "mentor_id": profile_uuid,
        "mentor_slug": slug,
        "slot": body.slot if body.slot and "T" in body.slot else None,
        "agenda": body.notes,
        "notes": body.notes,
        "duration_minutes": body.duration_minutes,
        "price_inr": price_total,
        "payment_id": body.razorpay_payment_id,
        "razorpay_order_id": body.razorpay_order_id,
        "payment_status": "captured",
        "status": "awaiting_mentor",
        "metadata": {
            "mentor_name": catalogue.get("name"),
            "slot_label": body.slot if body.slot and "T" not in body.slot else None,
        },
    }
    try:
        row = sb.table("mentor_bookings").insert(payload).execute().data
    except Exception as exc:  # noqa: BLE001
        # Unique-violation on razorpay_order_id / payment_id = replayed confirm.
        msg = str(exc).lower()
        if "duplicate" in msg or "unique" in msg or "23505" in msg:
            raise HTTPException(
                status_code=409, detail="This payment has already been used for a booking"
            )
        raise HTTPException(status_code=500, detail="Failed to create booking")
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create booking")
    return _shape_booking(row[0])


@router.get("/mentors/bookings")
def list_bookings(
    status: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    user: dict = Depends(get_current_user),
) -> dict:
    sb = get_supabase_admin()
    q = sb.table("mentor_bookings").select("*").eq("user_id", user["id"])
    if status:
        q = q.eq("status", status)
    rows = q.order("created_at", desc=True).limit(limit).execute().data or []
    return {"items": [_shape_booking(r) for r in rows]}


class CancelBody(BaseModel):
    reason: str | None = None


@router.post("/mentors/bookings/{booking_id}/cancel")
def cancel_booking(booking_id: str, body: CancelBody, user: dict = Depends(get_current_user)) -> dict:
    if not _is_uuid(booking_id):
        raise HTTPException(status_code=400, detail="Invalid id")
    sb = get_supabase_admin()
    row = (
        sb.table("mentor_bookings")
        .select("status,metadata")
        .eq("id", booking_id)
        .eq("user_id", user["id"])
        .limit(1)
        .execute()
        .data
    )
    if not row:
        raise HTTPException(status_code=404, detail="Booking not found")
    if row[0].get("status") in {"completed", "cancelled", "refunded"}:
        raise HTTPException(status_code=409, detail=f"Cannot cancel a {row[0]['status']} booking")
    updated = (
        sb.table("mentor_bookings")
        .update(
            {
                "status": "cancelled",
                "cancelled_at": _now_iso(),
                "updated_at": _now_iso(),
                "metadata": {**(row[0].get("metadata") or {}), "cancel_reason": body.reason},
            }
        )
        .eq("id", booking_id)
        .execute()
        .data
    )
    return _shape_booking(updated[0]) if updated else {"ok": True, "id": booking_id, "status": "cancelled"}


# ───────────────────────── Partners + Groups ─────────────────────────
# These already use Supabase via app.study_os.social_sessions; lifting the
# placeholder shim here keeps the contract identical for the frontend.


class PartnerReq(BaseModel):
    partner_id: str
    message: str | None = None
    pairing_goal: str = "discipline"


@router.get("/partners")
def list_partners(user: dict = Depends(get_current_user)) -> dict:
    from app.study_os.social_sessions import list_partner_suggestions, list_pairs

    sb = get_supabase_admin()
    pairs = list_pairs(sb, user["id"])
    suggestions = list_partner_suggestions(sb, user["id"], limit=10)
    return {"suggested": suggestions, "pairs": pairs}


@router.post("/partners/request")
def request_partner(body: PartnerReq, user: dict = Depends(get_current_user)) -> dict:
    from app.study_os.social_sessions import request_partner as svc_request

    try:
        return svc_request(
            get_supabase_admin(),
            user["id"],
            body.partner_id,
            pairing_goal=body.pairing_goal,
            message=body.message,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/groups")
def list_groups(user: dict = Depends(get_current_user)) -> dict:
    from app.study_os.social_sessions import list_groups as svc_list_groups

    return {"items": svc_list_groups(get_supabase_admin(), user["id"])}


class GroupJoinBody(BaseModel):
    group_id: str


@router.post("/groups/join")
def join_group(body: GroupJoinBody, user: dict = Depends(get_current_user)) -> dict:
    from app.study_os.social_sessions import join_group as svc_join

    try:
        return svc_join(get_supabase_admin(), user["id"], body.group_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
