"""APScheduler in-process job runner.

Jobs:
    notif:dispatch        every 2 min   — dispatch_pending_alerts
    notif:deadline_sweep  daily 06:00   — send_deadline_alerts (3-day + 1-day)
    elig:recompute        every 5 min   — drain_recompute_queue
    doc:text_extract      every 60s     — run_worker_pass (text_extract_worker)

Lifecycle is wired into the FastAPI ``lifespan`` in ``server.py``.
The scheduler is a singleton; calls to ``start_scheduler`` are idempotent.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.db.supabase_client import get_supabase_admin
from app.notifications.dispatcher import dispatch_pending_alerts, kill_switch_enabled
from app.notifications.recompute_worker import drain_recompute_queue
from app.profile.anonymous_cleanup import cleanup_anonymous_users
from app.scraping.alerts import send_deadline_alerts

logger = logging.getLogger("career_copilot.notifications.scheduler")

_scheduler: BackgroundScheduler | None = None
_last_run: dict[str, dict[str, Any]] = {}


def _is_noop_result(name: str, result: Any) -> bool:
    """True when a scheduled-job result reflects "nothing happened".

    Idle ticks happen every couple of minutes and produced ~30 INFO
    lines per 5-minute window. We still record the result on
    ``_last_run`` (so operators can pull it from the admin endpoint),
    but route the heartbeat to DEBUG.
    """
    if not isinstance(result, dict):
        return False
    if name == "notif:dispatch":
        # Either kill-switched, or a normal tick that found nothing to send.
        if result.get("killed"):
            return True
        return (
            (result.get("checked") or 0) == 0
            and (result.get("in_app") or 0) == 0
            and (result.get("emailed") or 0) == 0
        )
    if name == "elig:recompute":
        return (result.get("checked") or 0) == 0 and (result.get("completed") or 0) == 0
    if name == "notif:deadline_sweep":
        return bool(result.get("killed")) or (result.get("sent") or 0) == 0
    if name == "anon:cleanup":
        return (result.get("deleted") or 0) == 0
    if name == "mock:sweeper":
        return not any(
            (result.get(k) or 0)
            for k in ("enqueued", "auto_submitted", "derivations", "failed", "errors")
        )
    if name == "doc:text_extract":
        return result.get("processed", 0) == 0 and result.get("status") == "idle"
    if name in ("writing:evaluate", "writing:mastery_outbox"):
        return result.get("processed", 0) == 0 and not result.get("swept")
    if name == "ca:generate":
        return result.get("processed", 0) == 0 and not result.get("swept")
    if name == "ca:ingest":
        # Routine ONLY on a clean pass where nothing material moved (not-modified/duplicate
        # ticks are noise). A failed/partial pass is never a noop — it must reach the
        # failure classifier so /admin/jobs reflects it.
        if result.get("status") != "ok":
            return False
        return not any(
            (result.get(k) or 0)
            for k in ("snapshotted", "enqueued", "deprioritised")
        )
    if name == "ca:promote-sweep":
        return (result.get("archived") or 0) == 0
    return False


def _is_failure_result(name: str, result: Any) -> bool:
    """True when a job returned a result that represents an operational failure.

    Distinguishes from _is_noop_result (nothing to do) and exceptions
    (unhandled crash). Failure results are logged as ERROR and stored with
    ok=False so /api/admin/jobs reflects the failure without raising.
    """
    if not isinstance(result, dict):
        return False
    if name == "doc:text_extract":
        # processed=1 + status='failed' means extraction was attempted and failed.
        # processed=0 + status='conflict' is a race, not a failure.
        return result.get("processed", 0) == 1 and result.get("status") == "failed"
    if name in ("writing:evaluate", "writing:mastery_outbox"):
        return result.get("status") == "failed"
    if name == "ca:generate":
        # A generation pass that attempted a job and failed it (mirrors the EWP evaluator).
        return result.get("status") == "failed"
    if name == "ca:ingest":
        # Honest classification: a source-query failure (total) or per-source/enqueue
        # errors (partial) are operational failures, not silent successes.
        return result.get("status") in ("failed", "partial")
    return False


def _wrap(name: str, func) -> Any:
    def runner() -> None:
        started = datetime.now(timezone.utc).isoformat()
        try:
            result = func()
            if _is_failure_result(name, result):
                _last_run[name] = {"at": started, "ok": False, "result": result}
                logger.error("[%s] operational failure: %s", name, result)
            elif _is_noop_result(name, result):
                _last_run[name] = {"at": started, "ok": True, "result": result}
                logger.debug("[%s] %s", name, result)
            else:
                _last_run[name] = {"at": started, "ok": True, "result": result}
                logger.info("[%s] %s", name, result)
        except Exception as exc:  # noqa: BLE001
            _last_run[name] = {"at": started, "ok": False, "error": str(exc)}
            logger.exception("[%s] failed", name)

    return runner


# ─── Job bodies ─────────────────────────────────────────────────────────────


def _job_dispatch() -> dict[str, Any]:
    return dispatch_pending_alerts(get_supabase_admin())


def _job_deadline_sweep() -> dict[str, Any]:
    sb = get_supabase_admin()
    if kill_switch_enabled(sb):
        return {"killed": True}
    return send_deadline_alerts(sb)


def _job_recompute() -> dict[str, Any]:
    return drain_recompute_queue(get_supabase_admin())


def _job_plan_regen() -> dict[str, Any]:
    # Imported lazily — the planner pulls in a chunk of the study_os
    # package, and the scheduler module is imported early in startup.
    from app.study_os.regen import regenerate_stale_plans

    return regenerate_stale_plans(get_supabase_admin())


def _job_cleanup_anonymous_users() -> dict[str, Any]:
    return cleanup_anonymous_users(get_supabase_admin())


def _job_mock_sweeper() -> dict[str, Any]:
    # Lazy import — mock_engine pulls in the study_os package, which the
    # scheduler module is imported ahead of during startup.
    from app.study_os.mock_engine import run_sweeper

    return run_sweeper(get_supabase_admin())


def _job_text_extract_worker() -> dict[str, Any]:
    from app.library.text_extract_worker import run_worker_pass

    return run_worker_pass(get_supabase_admin())


def _job_writing_evaluator() -> dict[str, Any]:
    # Lazy import — writing_practice pulls in the study_os package.
    from app.study_os.writing_practice.evaluation_worker import run_worker_pass, sweep_stale_jobs

    sb = get_supabase_admin()
    swept = sweep_stale_jobs(sb).get("swept", 0)
    result = run_worker_pass(sb)
    if swept:
        result = {**result, "swept": swept}
    return result


def _job_writing_mastery_outbox() -> dict[str, Any]:
    from app.study_os.writing_practice.mastery_outbox_worker import run_outbox_pass, sweep_stale_outbox

    sb = get_supabase_admin()
    swept = sweep_stale_outbox(sb).get("swept", 0)
    result = run_outbox_pass(sb)
    if swept:
        result = {**result, "swept": swept}
    return result


def _job_ca_ingest() -> dict[str, Any]:
    # GQR-G5b — crawl due current-affairs sources + enqueue generation per new document.
    from app.current_affairs.ingestion import run_ingest_pass

    return run_ingest_pass(get_supabase_admin())


def _job_ca_generate() -> dict[str, Any]:
    # GQR-G5b — sweep stale leases + run one shadow generation job (mirrors the EWP
    # evaluator). Generation is shadow/mock unless FF_CA_LLM is enabled; nothing is
    # promoted here (promotion stays the human gate).
    from app.current_affairs.generation.worker import (
        run_generation_worker_pass,
        sweep_stale_generation_jobs,
    )

    sb = get_supabase_admin()
    swept = sweep_stale_generation_jobs(sb).get("swept", 0)
    # require_real_provider: the scheduled cron only processes a job when a real provider
    # adapter is active — the deterministic mock never consumes a production document.
    result = run_generation_worker_pass(sb, require_real_provider=True)
    if swept:
        result = {**result, "swept": swept}
    return result


def _job_ca_promote_sweep() -> dict[str, Any]:
    # GQR-G5b — archive current-affairs events past their relevance window.
    from app.current_affairs.retirement import sweep_expired_current_events

    return sweep_expired_current_events(get_supabase_admin())


# Per-job permission overrides for the manual-trigger admin endpoint.
# Jobs not listed here fall back to the endpoint's default (require_admin).
# The value is the permission string checked by require_permission().
JOB_PERMISSIONS: dict[str, str] = {
    "doc:text_extract": "exam_intelligence.cms",
}

# Public registry — also used by the manual-trigger admin endpoint.
JOBS: dict[str, callable] = {  # type: ignore[type-arg]
    "notif:dispatch": _job_dispatch,
    "notif:deadline_sweep": _job_deadline_sweep,
    "elig:recompute": _job_recompute,
    "study:plan_regen": _job_plan_regen,
    "anon:cleanup": _job_cleanup_anonymous_users,
    "mock:sweeper": _job_mock_sweeper,
    "doc:text_extract": _job_text_extract_worker,
    "writing:evaluate": _job_writing_evaluator,
    "writing:mastery_outbox": _job_writing_mastery_outbox,
    "ca:ingest": _job_ca_ingest,
    "ca:generate": _job_ca_generate,
    "ca:promote-sweep": _job_ca_promote_sweep,
}


# ─── Lifecycle ──────────────────────────────────────────────────────────────


_TEXT_EXTRACT_INTERVAL_DEFAULT = 60
_TEXT_EXTRACT_INTERVAL_MIN = 10
_TEXT_EXTRACT_INTERVAL_MAX = 3600


def _parse_text_extract_interval() -> int:
    """Parse TEXT_EXTRACT_WORKER_INTERVAL_SECONDS from the environment.

    Accepts integers in [10, 3600]. Any invalid value (non-integer, zero,
    negative, out of range) is silently replaced by the default (60s) so
    a misconfigured env var never crashes start_scheduler and takes down
    all other scheduled jobs.
    """
    raw = os.environ.get("TEXT_EXTRACT_WORKER_INTERVAL_SECONDS", str(_TEXT_EXTRACT_INTERVAL_DEFAULT))
    try:
        value = int(raw)
        if not (_TEXT_EXTRACT_INTERVAL_MIN <= value <= _TEXT_EXTRACT_INTERVAL_MAX):
            raise ValueError(
                f"out of range [{_TEXT_EXTRACT_INTERVAL_MIN}, {_TEXT_EXTRACT_INTERVAL_MAX}]"
            )
        return value
    except (ValueError, TypeError) as exc:
        logger.warning(
            "TEXT_EXTRACT_WORKER_INTERVAL_SECONDS=%r invalid (%s); defaulting to %ds",
            raw, exc, _TEXT_EXTRACT_INTERVAL_DEFAULT,
        )
        return _TEXT_EXTRACT_INTERVAL_DEFAULT


def start_scheduler() -> BackgroundScheduler | None:
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    if os.environ.get("DISABLE_SCHEDULER", "").lower() in {"1", "true", "yes"}:
        logger.info("scheduler disabled via DISABLE_SCHEDULER env")
        return None

    sched = BackgroundScheduler(timezone="UTC")

    sched.add_job(
        _wrap("notif:dispatch", _job_dispatch),
        IntervalTrigger(minutes=2),
        id="notif:dispatch",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    # Daily 06:00 IST = 00:30 UTC
    sched.add_job(
        _wrap("notif:deadline_sweep", _job_deadline_sweep),
        CronTrigger(hour=0, minute=30, timezone="UTC"),
        id="notif:deadline_sweep",
        replace_existing=True,
    )
    sched.add_job(
        _wrap("elig:recompute", _job_recompute),
        IntervalTrigger(minutes=5),
        id="elig:recompute",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    # Daily 03:00 UTC — refresh active study plans not regenerated today.
    sched.add_job(
        _wrap("study:plan_regen", _job_plan_regen),
        CronTrigger(hour=3, minute=0, timezone="UTC"),
        id="study:plan_regen",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    # Daily 04:00 UTC — sweep anonymous Supabase users older than 30d.
    sched.add_job(
        _wrap("anon:cleanup", _job_cleanup_anonymous_users),
        CronTrigger(hour=4, minute=0, timezone="UTC"),
        id="anon:cleanup",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    # Every 30s — auto-submit expired mock attempts + drain derivation retries.
    # Single loop with a job-kind dispatcher; max_instances=1 prevents overlap.
    sched.add_job(
        _wrap("mock:sweeper", _job_mock_sweeper),
        IntervalTrigger(seconds=30),
        id="mock:sweeper",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    # Every 60s — claim and run one queued text_extract job. Single-instance
    # (max_instances=1 + coalesce=True) so a slow extraction doesn't queue
    # a second pass on top of itself. Configurable via TEXT_EXTRACT_WORKER_INTERVAL_SECONDS.
    _text_extract_interval = _parse_text_extract_interval()
    sched.add_job(
        _wrap("doc:text_extract", _job_text_extract_worker),
        IntervalTrigger(seconds=_text_extract_interval),
        id="doc:text_extract",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # Every 20s — claim and run one queued writing language-evaluation job
    # (also sweeps expired leases). Single-instance so a slow evaluator pass
    # never stacks on itself.
    sched.add_job(
        _wrap("writing:evaluate", _job_writing_evaluator),
        IntervalTrigger(seconds=20),
        id="writing:evaluate",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    # Every 20s — drain one mastery-outbox row (post-commit shadow evidence).
    sched.add_job(
        _wrap("writing:mastery_outbox", _job_writing_mastery_outbox),
        IntervalTrigger(seconds=20),
        id="writing:mastery_outbox",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # GQR-G5b — CA pipeline crons.
    # Every 30 min — crawl due current-affairs sources (per-source cadence from
    # crawl_schedule) + enqueue generation for each new document. Frequent ticks are
    # cheap: non-due sources are skipped in-pass.
    sched.add_job(
        _wrap("ca:ingest", _job_ca_ingest),
        IntervalTrigger(minutes=30),
        id="ca:ingest",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    # Every 30s — claim + run one shadow generation job (also sweeps expired leases).
    sched.add_job(
        _wrap("ca:generate", _job_ca_generate),
        IntervalTrigger(seconds=30),
        id="ca:generate",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    # Daily 02:30 UTC — archive current-affairs events past their relevance window.
    sched.add_job(
        _wrap("ca:promote-sweep", _job_ca_promote_sweep),
        CronTrigger(hour=2, minute=30, timezone="UTC"),
        id="ca:promote-sweep",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    sched.start()
    _scheduler = sched
    logger.info("APScheduler started: %s", [j.id for j in sched.get_jobs()])
    return sched


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        try:
            _scheduler.shutdown(wait=False)
        except Exception as exc:  # noqa: BLE001
            # Suppress to keep shutdown idempotent, but log so a failing
            # scheduler shutdown does not vanish from operational view.
            logger.warning("scheduler_shutdown_failed exc=%s: %s", type(exc).__name__, exc, exc_info=True)
        _scheduler = None


def list_jobs() -> list[dict[str, Any]]:
    if _scheduler is None:
        return []
    out: list[dict[str, Any]] = []
    for job in _scheduler.get_jobs():
        last = _last_run.get(job.id)
        out.append(
            {
                "id": job.id,
                "next_run_at": str(job.next_run_time) if job.next_run_time else None,
                "trigger": str(job.trigger),
                "last_run": last,
            }
        )
    return out


def run_job_now(job_id: str) -> dict[str, Any]:
    fn = JOBS.get(job_id)
    if fn is None:
        raise KeyError(job_id)
    started = datetime.now(timezone.utc).isoformat()
    try:
        result = fn()
        ok = not _is_failure_result(job_id, result)
        _last_run[job_id] = {"at": started, "ok": ok, "result": result, "manual": True}
        return {"ok": ok, "result": result}
    except Exception as exc:  # noqa: BLE001
        _last_run[job_id] = {"at": started, "ok": False, "error": str(exc), "manual": True}
        return {"ok": False, "error": str(exc)}
