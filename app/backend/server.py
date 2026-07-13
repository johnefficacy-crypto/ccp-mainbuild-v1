"""Career Copilot backend (Phase 1.5).

Authentication is delegated to Supabase Auth; the canonical database is
Supabase Postgres (accessed via asyncpg + the supabase-py admin client).

MongoDB and the local JWT/bcrypt shim from Phase 1 have been fully removed.
Phase-1 placeholder endpoints continue to serve the React app from
deterministic in-memory data; Phase 2 will swap each surface to its real
Supabase-backed implementation.
"""
from __future__ import annotations

import logging
import importlib

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# Load .env before importing anything that reads settings.
load_dotenv(Path(__file__).resolve().parent / ".env")

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from httpx import ConnectError, RemoteProtocolError
from pydantic import BaseModel

from app.api.accountability import router as accountability_router
from app.api.admin_exam_intelligence import router as admin_exam_intel_router
from app.api.admin_overview import router as admin_overview_router
from app.api.ai import router as ai_router
from app.api.admin_persona import router as admin_persona_router
from app.api.admin_scrape import router as admin_scrape_router
from app.api.admin_study_os import router as admin_study_os_router
from app.api.admin_exam_intel_cms import router as admin_exam_intel_cms_router
from app.api.admin_exam_intel_manage import router as admin_exam_intel_manage_router
from app.api.content_studio import router as content_studio_router
from app.api.admin_exam_intel_documents import router as admin_exam_intel_documents_router
from app.api.admin_exam_intel_evidence import router as admin_exam_intel_evidence_router
from app.api.admin_community_governance import router as admin_community_governance_router
from app.api.admin_conflicts import router as admin_conflicts_router
from app.api.admin_eligibility import router as admin_eligibility_router
from app.api.admin_copyright import (
    public_router as copyright_public_router,
    admin_router as admin_copyright_router,
)
from app.api.admin_kpis import router as admin_kpis_router
from app.api.admin_ops import router as admin_ops_router

from app.api.blogs import router as blogs_router, admin_router as admin_blogs_router
from app.api.admin_moderation import (
    router as moderation_router,
    admin_router as admin_moderation_router,
)
from app.api.auth import router as auth_router
from app.api.admin_trust import router as admin_trust_router
from app.api.admin_templates import router as admin_templates_router
from app.api.admin_verification_reports import router as admin_verification_reports_router
from app.api.evidence import router as evidence_router
from app.api.flashcards import router as flashcards_router
from app.api.mistakes import router as mistakes_router
from app.api.library import router as library_router
from app.api.notes import router as notes_router
from app.api.reports import router as reports_router
from app.api.revision import router as revision_router
from app.api.exam_intelligence import router as exam_intelligence_router
from app.api.canonical import router as canonical_router
from app.api.community_runtime import router as community_runtime_router
from app.api.eligibility import router as eligibility_router
from app.api.exam_eligibility import router as exam_eligibility_router
from app.api.exams import router as exams_router
from app.api.policy_updates import router as policy_updates_router
from app.api.reminders import router as reminders_router
from app.api.admin_exam_eligibility import router as admin_exam_eligibility_router
from app.api.marketplace import router as marketplace_router
from app.api.admin_marketplace import router as admin_marketplace_router
from app.api.notifications import router as notifications_router
from app.api.onboarding_unified import router as onboarding_unified_router
from app.profile.merge_claim import router as profile_merge_claim_router
from app.profile.onboarding import router as profile_onboarding_router
from app.profile.readiness import router as profile_readiness_router
from app.api.payments import router as payments_router
from app.api.persona import router as persona_router
from app.api.persona_questions import router as persona_questions_router
from app.api.placeholders import router as placeholders_router
from app.api.study_compare import router as study_compare_router
from app.api.study_os import router as study_os_router
from app.api.current_affairs_practice import router as current_affairs_practice_router
from app.api.subject_practice import router as subject_practice_router
from app.api.writing_practice import router as writing_practice_router
from app.api.writing_practice import tasks_router as writing_practice_tasks_router
from app.api.mock_engine import router as mock_engine_router
from app.api.pyq_practice_launch import router as pyq_practice_launch_router
from app.api.generated_mock import router as generated_mock_router
from app.api.mock_attempt_events import router as mock_attempt_events_router
from app.api.admin_mocks import router as admin_mocks_router
from app.notifications.scheduler import start_scheduler, stop_scheduler
from app.core.config import get_settings
from app.db.postgres import close_pool, get_pool

logger = logging.getLogger("career_copilot")
# Explicit format so scheduler/dispatcher records don't end up
# concatenated or with truncated URLs in captured logs.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

# Scrub api_key=<value> from any log record (httpx request logging prints the
# full SerpApi URL at INFO; it leaked the key once). Attach after basicConfig
# so the root handler exists.
from app.core.logging_filters import install_log_redaction

install_log_redaction()


def _bootstrap_mock_publishers() -> None:
    """Grant mock_questions:publish permission to emails in MOCK_PUBLISHER_BOOTSTRAP_EMAILS.

    Reads a comma-separated list of email addresses from the environment.
    Each email is resolved to a Supabase user; if found the permission is
    idempotently added to ``app_metadata.permissions``.  Unresolved emails
    log a warning and are skipped — boot never fails.

    This is intentionally synchronous (called in lifespan, not an async path).
    """
    raw = os.environ.get("MOCK_PUBLISHER_BOOTSTRAP_EMAILS", "").strip()
    if not raw:
        return

    emails = [e.strip() for e in raw.split(",") if e.strip()]
    if not emails:
        return

    permission = "mock_questions:publish"
    logger.info("bootstrap_mock_publishers: processing %d email(s)", len(emails))

    try:
        from app.db.supabase_client import get_supabase_admin
        admin = get_supabase_admin()
    except Exception as exc:  # noqa: BLE001
        logger.warning("bootstrap_mock_publishers: cannot get admin client: %s", exc)
        return

    for email in emails:
        try:
            result = admin.auth.admin.list_users()
            users = [u for u in (result or []) if getattr(u, "email", "") == email]
            if not users:
                logger.warning("bootstrap_mock_publishers: email not found: %s", email)
                continue
            user = users[0]
            user_id = str(user.id)
            existing_perms: list[str] = list(
                (getattr(user, "app_metadata", {}) or {}).get("permissions") or []
            )
            if permission in existing_perms:
                logger.info("bootstrap_mock_publishers: %s already has %s", email, permission)
                continue
            new_perms = list(set(existing_perms) | {permission})
            admin.auth.admin.update_user_by_id(
                user_id,
                {"app_metadata": {"permissions": new_perms}},
            )
            logger.info("bootstrap_mock_publishers: granted %s to %s", permission, email)
        except Exception as exc:  # noqa: BLE001
            logger.warning("bootstrap_mock_publishers: failed for %s: %s", email, exc)


def _scheduler_enabled() -> bool:
    """``ENABLE_SCHEDULER`` gates the in-process APScheduler.

    Default ``false`` so dev/test/CI boots don't spin up the cron loop
    that hammers Supabase with notifications + recompute work. Production
    must set ``ENABLE_SCHEDULER=true`` to get the background workers.
    """
    return os.environ.get("ENABLE_SCHEDULER", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Try to bring up the asyncpg pool eagerly so /api/db-health is cheap.
    try:
        await get_pool()
        logger.info("Postgres pool connected")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Postgres pool not available at startup: %s", exc)
    # Bootstrap mock publisher permissions (idempotent, never fails boot).
    try:
        _bootstrap_mock_publishers()
    except Exception as exc:  # noqa: BLE001
        logger.warning("bootstrap_mock_publishers raised unexpectedly: %s", exc)
    # APScheduler — in-process cron for notifications + recompute worker.
    scheduler_started = False
    if _scheduler_enabled():
        try:
            start_scheduler()
            scheduler_started = True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Scheduler did not start: %s", exc)
    else:
        logger.info("Scheduler disabled (ENABLE_SCHEDULER not set to true).")
    yield
    if scheduler_started:
        stop_scheduler()
    await close_pool()


app = FastAPI(title="Career Copilot API", version="0.2.0", lifespan=lifespan)

# CORS — frontend origin + emergent preview by default.
settings = get_settings()
cors_env = os.environ.get("CORS_ORIGINS", "")
if cors_env.strip():
    cors_origins = [o.strip() for o in cors_env.split(",") if o.strip()]
else:
    cors_origins = settings.BACKEND_CORS_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.exception_handler(RemoteProtocolError)
@app.exception_handler(ConnectError)
async def transient_transport_handler(request: Request, exc: Exception) -> JSONResponse:
    """Safety net for any endpoint that didn't wrap a Supabase transport
    disconnect itself: map it to a retryable 503 instead of a 500. Only the
    two transient transport errors land here; everything else is a 500."""
    logger.warning(
        "supabase_transient_unhandled on %s %s error_class=%s",
        request.method, request.url.path, type(exc).__name__,
    )
    return JSONResponse(
        status_code=503,
        content={"detail": {"code": "supabase_transient_disconnect", "retryable": True}},
        headers={"Retry-After": "2"},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled backend error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


api = APIRouter(prefix="/api")


def _load_required_router(module_path: str, attr: str = "router") -> APIRouter:
    """Load a required APIRouter with an explicit runtime error message."""
    try:
        mod = importlib.import_module(module_path)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Failed to import router module '{module_path}': {exc}") from exc
    router_obj = getattr(mod, attr, None)
    if not isinstance(router_obj, APIRouter):
        raise RuntimeError(
            f"Module '{module_path}' does not expose APIRouter '{attr}'"
        )
    return router_obj


class Health(BaseModel):
    status: str
    service: str
    ts: str


class DbHealth(BaseModel):
    status: str
    postgres: str
    supabase: str
    supabase_url: str | None = None
    ts: str


@api.get("/health", response_model=Health)
async def health() -> Health:
    return Health(
        status="ok",
        service="career-copilot",
        ts=datetime.now(timezone.utc).isoformat(),
    )


@api.get("/db-health", response_model=DbHealth)
async def db_health() -> DbHealth:
    settings = get_settings()
    supabase_status = "unreachable"
    try:
        # Authoritative liveness check — Supabase REST is the production path.
        from app.db.supabase_client import get_supabase_admin

        admin = get_supabase_admin()
        # Lightweight call against an existing canonical table; LIMIT 0 avoids
        # paying for a real read and works even if profiles is empty.
        admin.table("profiles").select("id").limit(1).execute()
        supabase_status = "connected"
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Supabase unreachable: {exc}")

    # asyncpg is best-effort. Direct Postgres hostnames are IPv6-only on
    # some Supabase tiers; if it fails we still report Supabase as healthy.
    postgres_status = "skipped"
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("SELECT 1")
        postgres_status = "connected"
    except Exception as exc:  # noqa: BLE001
        postgres_status = f"unreachable ({type(exc).__name__})"

    return DbHealth(
        status="ok",
        postgres=postgres_status,
        supabase=supabase_status,
        supabase_url=settings.NEXT_PUBLIC_SUPABASE_URL or None,
        ts=datetime.now(timezone.utc).isoformat(),
    )


api.include_router(auth_router)
api.include_router(eligibility_router)
api.include_router(exam_eligibility_router)  # PR-D1 exam-level baseline eligibility
api.include_router(exams_router)  # PR1 exams catalogue with per-caller overlay
api.include_router(policy_updates_router)  # PR3 aspirant-facing policy updates feed
api.include_router(reminders_router)  # PR4 user-owned reminders CRUD
api.include_router(admin_exam_eligibility_router)  # PR-D2 admin CRUD for exam_eligibility_rules
api.include_router(notifications_router)
api.include_router(admin_scrape_router)  # admin scraper trust-gate routes
api.include_router(admin_conflicts_router)  # consensus conflict resolution
api.include_router(admin_trust_router)
api.include_router(admin_verification_reports_router)  # PR7 gateway read API
api.include_router(admin_eligibility_router)  # recompute queue, publish impact, generic audit
api.include_router(admin_persona_router)  # PR4 admin persona controls
api.include_router(admin_exam_intel_router)  # PR5 admin exam intelligence review
api.include_router(exam_intelligence_router)  # PR5 verified-only exam intelligence reads
api.include_router(evidence_router)  # universal evidence-drawer source endpoint
api.include_router(payments_router)  # razorpay + plans
api.include_router(persona_router)  # internal aspirant persona v1
api.include_router(persona_questions_router)  # PR2 progressive tiny questions
api.include_router(subject_practice_router)  # Subject Practice Hub launch orchestrator — before canonical so /study/subjects/{id}/practice/start wins
api.include_router(current_affairs_practice_router)  # GQR-G5: GA current-affairs learner attempt runtime (own tables)
api.include_router(study_os_router)  # PR3 Study OS Mission Control — before canonical so /study/mission-control wins
api.include_router(writing_practice_router)  # EWP-2 English Writing Practice deterministic runtime
api.include_router(writing_practice_tasks_router)  # EWP-SP3 planner task -> writing-session launch
api.include_router(mock_engine_router)          # PR1 Mock Engine: start→answer→submit→score
api.include_router(pyq_practice_launch_router)  # PYQ-PR9 planner task -> PYQ practice launch
api.include_router(generated_mock_router)        # A-PR3 generated-mock attempt start (D4 Option-B)
api.include_router(mock_attempt_events_router)  # PR2b attempt events & telemetry
api.include_router(admin_templates_router)      # PR2d mock template authoring
api.include_router(admin_mocks_router)          # PR2 Admin question bank + review workflow
api.include_router(admin_study_os_router)  # admin Study OS ops (flagged via ADMIN_STUDY_OS_ENABLED)
api.include_router(admin_exam_intel_cms_router)  # admin Exam Intelligence CMS — Phase 4 (same flag)
api.include_router(admin_exam_intel_manage_router)  # J2 Manage Exam operational editors (exam_intelligence.manage)
api.include_router(content_studio_router)  # Content Studio — subject-scoped writing-prompt ops (EWP Stage 1)
api.include_router(admin_exam_intel_documents_router)  # admin Exam Intelligence PDF uploads (same flag)
api.include_router(admin_exam_intel_evidence_router)  # D05 document-evidence registration + trust review (PR-4, same flag)
api.include_router(admin_community_governance_router)  # admin Community / Mentors / Resources governance (§4.1–§4.4)
api.include_router(study_compare_router)  # Study OS comparison + social + verification
api.include_router(onboarding_unified_router)  # legacy unified guided onboarding (deprecated; Item 8 will drop)
api.include_router(profile_onboarding_router)  # POST /api/profile/onboarding-answer (Supabase anonymous auth v2)
api.include_router(profile_merge_claim_router)  # POST /api/onboarding/merge-claim/{create,consume} (anon→permanent merge)
api.include_router(profile_readiness_router)  # GET  /api/profile/readiness (per-feature unlock cards)
# Real Supabase-backed accountability + admin ops — must precede community_runtime
# and placeholders so route order wins for /accountability/mentors/* and /admin/*.
api.include_router(accountability_router)
api.include_router(_load_required_router("app.api.admin_ops"))
api.include_router(community_runtime_router)  # durable community/social routes — must precede canonical seed fallbacks
api.include_router(marketplace_router)  # marketplace catalogue + Razorpay course purchase — before canonical
api.include_router(admin_marketplace_router)  # admin marketplace CRUD + refunds
api.include_router(canonical_router)  # canonical Supabase routes — must precede placeholders
# NOTE: community_people_router was removed — every route under that prefix
# duplicated community_runtime_router's. The legacy file's own docstring
# said it was "being phased out in favour of community_runtime"; the
# real DB-backed router is the single owner now.
# Real Supabase-backed AI + admin overview — must precede placeholders so route order wins.
api.include_router(ai_router)
api.include_router(admin_overview_router)
# Phase-2 user surfaces: notes, flashcards, mistakes, revision, reports
api.include_router(library_router)  # PR1 document-asset foundation (user uploads)
api.include_router(notes_router)
api.include_router(flashcards_router)
api.include_router(mistakes_router)
api.include_router(revision_router)
api.include_router(reports_router)
# Moderation & trust workflows
api.include_router(moderation_router)  # /moderation/report, /moderation/my-reports
api.include_router(admin_moderation_router)  # /admin/moderation/...
api.include_router(admin_kpis_router)  # /admin/kpis/...
api.include_router(blogs_router)  # /blogs public list/detail
api.include_router(admin_blogs_router)  # /admin/blogs CRUD
api.include_router(copyright_public_router)  # /copyright/submit (public DMCA intake)
api.include_router(admin_copyright_router)  # /admin/copyright/...
# Placeholder/demo-only endpoints (3 admin `*-static` routes + a notifications
# toggle stub) are NOT part of the production surface and are deferred to v2.
# They are off by default; set FF_ENABLE_PLACEHOLDER_ENDPOINTS=1 to expose them
# (e.g. for local/demo). The module is still imported above because real routers
# (accountability) consume its MENTORS catalogue constant.
if (os.getenv("FF_ENABLE_PLACEHOLDER_ENDPOINTS") or "").strip().lower() in ("1", "true", "yes", "on"):
    api.include_router(placeholders_router)
app.include_router(api)


@app.get("/")
async def root():
    return {"service": "career-copilot-api", "docs": "/docs"}
