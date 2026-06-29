"""Phase-1 placeholder router — ISOLATED / deferred to v2.

This module once backed ~45 un-migrated screens with static/in-memory data.
Those surfaces now have real Supabase-backed routers, and the duplicate
placeholder routes (accountability, community, marketplace, recruitments, and
the in-memory per-user state) have been removed.

What remains is a small set of demo-only admin endpoints with no real
equivalent yet (the three `*-static` readouts and a notifications-toggle stub).
They are **off by default** — ``server.py`` only mounts this router when
``FF_ENABLE_PLACEHOLDER_ENDPOINTS`` is truthy (local/demo use). They are tracked
as v2 scope, not part of the production surface.

The module stays importable because the real accountability router consumes the
``MENTORS`` mentor catalogue below; that constant is the only thing other code
depends on here.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import require_admin


# ── Mentor catalogue (consumed by the real accountability router) ────────────
MENTORS = [
    {"id": "rohan-iyer", "name": "Rohan Iyer", "headline": "Ex-RBI Grade B · interview specialist", "price_per_hour": 2499, "rating": 4.9, "sessions": 134, "exams": ["rbi-grade-b-2026"], "languages": ["English", "Hindi"], "bio": "Cleared RBI Grade B 2018, served 3 years before mentoring full-time."},
    {"id": "priyanka-desai", "name": "Priyanka Desai", "headline": "AIR 42 UPSC CSE 2022 · answer writing", "price_per_hour": 3499, "rating": 5.0, "sessions": 88, "exams": ["upsc-cse-2026"], "languages": ["English"], "bio": "IRS officer. Focus: Mains answer architecture and essay framing."},
    {"id": "sandeep-reddy", "name": "Sandeep Reddy", "headline": "SSC CGL Quant trainer · topper of '19", "price_per_hour": 999, "rating": 4.7, "sessions": 412, "exams": ["ssc-cgl-2026"], "languages": ["English", "Telugu"], "bio": "Trained 8000+ students. Focus: shortcut-free accuracy building."},
    {"id": "fatima-ahmed", "name": "Fatima Ahmed", "headline": "IBPS PO · working CM with 6yr ops", "price_per_hour": 1499, "rating": 4.8, "sessions": 176, "exams": ["ibps-po-xv", "sbi-clerk-2026"], "languages": ["English", "Urdu"], "bio": "Mains strategy + banking awareness without bloat."},
]

_now = lambda: datetime.now(timezone.utc).isoformat()  # noqa: E731


# ── Demo-only admin endpoints (mounted only when the feature flag is on) ──────

router_admin = APIRouter(prefix="/admin", tags=["admin"])


@router_admin.get("/sources-static")
async def admin_sources_static(_admin: dict = Depends(require_admin)):
    return {
        "items": [
            {"id": "src-ssc", "name": "ssc.gov.in", "trust": "official", "last_run": _now(), "queue_depth": 2},
            {"id": "src-ibps", "name": "ibps.in", "trust": "official", "last_run": _now(), "queue_depth": 1},
            {"id": "src-rbi", "name": "rbi.org.in", "trust": "official", "last_run": _now(), "queue_depth": 0},
        ]
    }


@router_admin.get("/scraper/runs-static")
async def admin_scraper_runs_static(_admin: dict = Depends(require_admin)):
    return {
        "items": [
            {"id": "run-12", "source": "ssc.gov.in", "status": "ok", "items_found": 4, "promoted": 2, "at": _now()},
            {"id": "run-11", "source": "ibps.in", "status": "queued", "items_found": 1, "promoted": 0, "at": _now()},
        ]
    }


@router_admin.get("/eligibility-queue-static")
async def admin_eligibility_queue_static(_admin: dict = Depends(require_admin)):
    return {
        "items": [
            {"id": "eq-1", "user_id": "u-101", "recruitment": "ssc-cgl-2026", "verdict": "conditional", "reason": "qualification missing", "at": _now()},
            {"id": "eq-2", "user_id": "u-205", "recruitment": "rbi-grade-b-2026", "verdict": "rejected", "reason": "age out of range", "at": _now()},
        ]
    }


class NotifToggle(BaseModel):
    channel: str
    enabled: bool


@router_admin.post("/notifications/toggle")
async def admin_notif_toggle(body: NotifToggle, _admin: dict = Depends(require_admin)):
    return {"ok": True, "channel": body.channel, "enabled": body.enabled}


# Aggregate router for easy include (mounted conditionally in server.py).
router = APIRouter()
router.include_router(router_admin)
