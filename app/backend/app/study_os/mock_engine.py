"""Mock Engine — server-authoritative attempt loop (PR1).

Handles: start → answer (idempotent upsert) → submit → result.

Scoring always reads from question_snapshot frozen at attempt start, never
from live mock_question_bank rows — so post-submit edits cannot alter scores.

After submit, a compatibility row is written to mock_tests so the existing
Mocks.jsx analytics list keeps working unchanged.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.study_os.attempt_events import record_server_event
from app.study_os.attempt_analytics import service as attempt_analytics
from app.study_os.attempt_event_types import (
    ATTEMPT_AUTO_SUBMITTED,
    ATTEMPT_STARTED,
    ATTEMPT_SUBMITTED,
    QUESTION_ANSWERED,
)

logger = logging.getLogger("career_copilot.study_os.mock_engine")


# ── helpers ────────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _safe(call, default=None):
    try:
        return call()
    except Exception as exc:  # noqa: BLE001
        logger.warning("mock_engine supabase call failed: %s", exc)
        return default


def _require(call, op: str):
    try:
        result = call()
        items = getattr(result, "data", result) or []
        if not items:
            raise RuntimeError(f"{op}: no rows returned")
        return items
    except RuntimeError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"{op} failed: {exc}") from exc


# ── question loading ───────────────────────────────────────────────────────────

def _load_questions_for_template(supabase: Any, template: dict) -> list[dict]:
    """Load questions + options for a template, ordered by template config.

    PR2 selector hardening: only published questions that haven't expired are
    eligible for new attempts.  Existing frozen ``question_snapshot`` rows are
    unaffected — scoring always reads from the snapshot, never from this path.
    """
    question_ids: list[str] = (template.get("config") or {}).get("question_ids") or []
    if not question_ids:
        return []

    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).isoformat()

    q_exec = supabase.table("mock_question_bank") \
        .select("*") \
        .in_("id", question_ids) \
        .eq("reviewer_status", "published") \
        .or_(f"valid_until.is.null,valid_until.gt.{now_iso}") \
        .execute()
    questions = {r["id"]: r for r in (q_exec.data or [])}

    opt_exec = supabase.table("mock_question_options") \
        .select("*") \
        .in_("question_id", question_ids) \
        .order("option_index") \
        .execute()
    opts_by_q: dict[str, list[dict]] = {}
    for o in (opt_exec.data or []):
        opts_by_q.setdefault(o["question_id"], []).append(o)

    out = []
    for qid in question_ids:
        q = questions.get(qid)
        if not q:
            continue
        out.append({**q, "options": opts_by_q.get(qid, [])})
    return out


def _question_snapshot(q: dict, *, marks_per_correct: float = 1.0, marks_per_wrong: float = 0.25) -> dict:
    """Frozen copy of a question + its options, stored in mock_attempt_responses.

    PR2: marks are template-bound (not question-bound), so they are passed in
    from the template config rather than read from the question row.
    Existing snapshots already have marks frozen; this only affects new attempts.
    """
    return {
        "id": q["id"],
        "question_text": q["question_text"],
        "question_type": q["question_type"],
        "marks": marks_per_correct,
        "negative_marks": marks_per_wrong,
        "correct_option_id": q.get("correct_option_id"),
        "explanation": q.get("explanation"),
        # Mastery write-back (PR5) derives deltas straight from the frozen
        # snapshot, so the topic/difficulty/source signals it weights on must be
        # captured here at attempt start — never read back from the live bank.
        "topic_id": q.get("topic_id"),
        "microtopic_id": q.get("microtopic_id"),
        "difficulty": q.get("difficulty") or "medium",
        "source_type": q.get("source_type") or "authored",
        "expected_time_sec": q.get("expected_time_sec"),
        "options": [
            {
                "id": o["id"],
                "option_text": o["option_text"],
                "option_index": o["option_index"],
            }
            for o in (q.get("options") or [])
        ],
    }


def select_questions_for_template(supabase: Any, template_id: str, user_id: str) -> list[dict]:
    """PR2d selector hook; currently supports section fixed selectors and legacy config.question_ids."""
    sections = _safe(lambda: supabase.table("mock_template_sections").select("*").eq("template_id", template_id).order("section_index").execute(), default=None)
    sec_rows = getattr(sections, "data", None) or []
    if not sec_rows:
        return []
    ordered: list[str] = []
    for sec in sec_rows:
        selector = sec.get("selector") or {}
        if selector.get("mode") == "fixed":
            ordered.extend(selector.get("question_ids") or [])
    if not ordered:
        return []
    q_rows = _safe(lambda: supabase.table("mock_question_bank").select("*").in_("id", ordered).execute(), default=None)
    by_id = {r["id"]: r for r in (getattr(q_rows, "data", None) or [])}
    return [by_id[qid] for qid in ordered if qid in by_id]


# ── public API ─────────────────────────────────────────────────────────────────

def start_attempt(supabase: Any, user_id: str, template_slug: str) -> dict:
    """Create a new in_progress attempt.

    Raises:
        LookupError — template not found or has no questions.
        ConflictError — active attempt already exists.
        RuntimeError — DB insert failed.
    """
    tmpl_rows = _safe(
        lambda: supabase.table("mock_templates")
        .select("*")
        .eq("slug", template_slug)
        .eq("status", "active")
        .limit(1)
        .execute(),
        default=None,
    )
    templates = getattr(tmpl_rows, "data", None) or []
    if not templates:
        raise LookupError(f"template '{template_slug}' not found")
    template = templates[0]

    existing = _safe(
        lambda: supabase.table("mock_attempts")
        .select("id,status,expires_at,started_at")
        .eq("user_id", user_id)
        .eq("template_id", template["id"])
        .eq("status", "in_progress")
        .limit(1)
        .execute(),
        default=None,
    )
    if (getattr(existing, "data", None) or []):
        raise ConflictError("active attempt already exists for this template")

    questions = select_questions_for_template(supabase, template["id"], user_id)
    if not questions:
        questions = _load_questions_for_template(supabase, template)
    if not questions:
        raise LookupError("template has no available questions")

    now = _now()
    expires_at = now + timedelta(seconds=int(template.get("duration_sec") or 3600))

    template_snapshot = {
        "id": template["id"],
        "slug": template["slug"],
        "name": template["name"],
        "total_questions": template.get("total_questions"),
        "duration_sec": template.get("duration_sec"),
        "negative_marking": template.get("negative_marking"),
        "marks_per_correct": float(template.get("marks_per_correct") or 1),
        "marks_per_wrong": float(template.get("marks_per_wrong") or 0.25),
        "question_ids": [q["id"] for q in questions],
        "interface_mode": (template.get("config") or {}).get("interface_mode", "simple"),
        "sections": (template.get("config") or {}).get("sections") or [],
        "allow_switching": bool((template.get("config") or {}).get("allow_switching", True)),
    }

    attempt_rows = _require(
        lambda: supabase.table("mock_attempts").insert({
            "user_id": user_id,
            "template_id": template["id"],
            "template_snapshot": template_snapshot,
            "status": "in_progress",
            "started_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "current_section_index": 0,
            "section_locks_enabled": not bool((template.get("config") or {}).get("allow_switching", True)),
        }).execute(),
        op="mock_attempts.insert",
    )
    attempt = attempt_rows[0]
    attempt_id = attempt["id"]

    tmpl_marks     = float(template.get("marks_per_correct") or 1)
    tmpl_neg_marks = float(template.get("marks_per_wrong") or 0.25)
    response_rows = [
        {
            "attempt_id": attempt_id,
            "question_id": q["id"],
            "question_snapshot": _question_snapshot(
                q,
                marks_per_correct=tmpl_marks,
                marks_per_wrong=tmpl_neg_marks,
            ),
            "is_visited": False,
            "is_marked_for_review": False,
            "client_seq": 0,
        }
        for q in questions
    ]
    _require(
        lambda: supabase.table("mock_attempt_responses").insert(response_rows).execute(),
        op="mock_attempt_responses.insert_initial",
    )

    record_server_event(
        supabase, attempt_id, user_id, ATTEMPT_STARTED,
        payload={"template_slug": template_slug},
        occurred_at=now.isoformat(),
    )

    return {
        "attempt_id": attempt_id,
        "expires_at": expires_at.isoformat(),
        "current_section_index": 0,
        "section_locks_enabled": not bool((template.get("config") or {}).get("allow_switching", True)),
        "questions": [_serialise_question_for_attempt(q) for q in questions],
    }


def get_attempt(supabase: Any, user_id: str, attempt_id: str) -> dict:
    """Return current attempt state with saved responses and time_remaining_sec."""
    attempt = _fetch_attempt(supabase, user_id, attempt_id)

    resp_rows = _safe(
        lambda: supabase.table("mock_attempt_responses")
        .select("*")
        .eq("attempt_id", attempt_id)
        .execute(),
        default=None,
    )
    responses = getattr(resp_rows, "data", None) or []

    snapshot = attempt.get("template_snapshot") or {}
    question_ids: list[str] = snapshot.get("question_ids") or []

    resp_by_q = {r["question_id"]: r for r in responses}

    questions_out = []
    for qid in question_ids:
        r = resp_by_q.get(qid)
        snap = (r or {}).get("question_snapshot") or {}
        questions_out.append({
            "question_id": qid,
            "question_text": snap.get("question_text"),
            "question_type": snap.get("question_type"),
            "marks": snap.get("marks"),
            "negative_marks": snap.get("negative_marks"),
            "options": snap.get("options") or [],
            "selected_option_id": (r or {}).get("selected_option_id"),
            "is_marked_for_review": bool((r or {}).get("is_marked_for_review")),
            "is_visited": bool((r or {}).get("is_visited")),
            "time_spent_sec": int((r or {}).get("time_spent_sec") or 0),
        })

    time_remaining = _time_remaining_sec(attempt)

    return {
        "attempt_id": attempt_id,
        "status": attempt["status"],
        "expires_at": attempt["expires_at"],
        "time_remaining_sec": time_remaining,
        "questions": questions_out,
        "current_section_index": int(attempt.get("current_section_index") or 0),
        "template_interface_mode": snapshot.get("interface_mode") or "simple",
        "template_config": {"interface_mode": snapshot.get("interface_mode"), "allow_switching": snapshot.get("allow_switching")},
        "sections": _get_section_states(supabase, attempt_id),
    }




def _question_section_index(snapshot: dict, question_id: str) -> int | None:
    qids = snapshot.get("question_ids") or []
    sections = snapshot.get("sections") or []
    for sec in sections:
        idx = int(sec.get("section_index") or 0)
        for qid in sec.get("question_ids") or []:
            if qid == question_id:
                return idx
    if question_id in qids:
        return 0
    return None


def _get_section_states(supabase: Any, attempt_id: str) -> list[dict]:
    rows = _safe(lambda: supabase.table("mock_attempt_section_state").select("*").eq("attempt_id", attempt_id).order("section_index").execute(), default=None)
    return getattr(rows, "data", None) or []


def enter_section(supabase: Any, user_id: str, attempt_id: str, section_index: int) -> dict:
    attempt = _fetch_attempt(supabase, user_id, attempt_id)
    current = int(attempt.get("current_section_index") or 0)
    locked = bool(attempt.get("section_locks_enabled"))
    if locked and section_index < current:
        raise ValueError("backward section movement is not allowed")
    now = _now_iso()
    _safe(lambda: supabase.table("mock_attempts").update({"current_section_index": section_index}).eq("id", attempt_id).execute(), default=None)
    _safe(lambda: supabase.table("mock_attempt_section_state").upsert({"attempt_id": attempt_id, "section_index": section_index, "entered_at": now}).execute(), default=None)
    return {"ok": True, "current_section_index": section_index}

def save_answer(
    supabase: Any,
    user_id: str,
    attempt_id: str,
    question_id: str,
    selected_option_id: str | None,
    is_marked_for_review: bool,
    client_seq: int,
    time_spent_sec: int,
) -> dict:
    """Idempotent upsert for a single answer.

    Rejected (raises ValueError) when:
      - attempt is not in_progress
      - attempt has expired
      - incoming client_seq ≤ stored client_seq (stale/duplicate)
    """
    attempt = _fetch_attempt(supabase, user_id, attempt_id)
    if attempt["status"] != "in_progress":
        raise ValueError("attempt is not in progress")
    if _time_remaining_sec(attempt) <= 0:
        raise ValueError("attempt has expired")
    snapshot = attempt.get("template_snapshot") or {}
    if bool(attempt.get("section_locks_enabled")):
        expected = _question_section_index(snapshot, question_id)
        if expected is not None and expected != int(attempt.get("current_section_index") or 0):
            raise ValueError("question is outside current section")

    existing = _safe(
        lambda: supabase.table("mock_attempt_responses")
        .select("id,client_seq")
        .eq("attempt_id", attempt_id)
        .eq("question_id", question_id)
        .limit(1)
        .execute(),
        default=None,
    )
    existing_rows = getattr(existing, "data", None) or []
    if existing_rows:
        stored_seq = int(existing_rows[0].get("client_seq") or 0)
        if client_seq <= stored_seq:
            return {"ok": True, "idempotent": True}

    payload = {
        "selected_option_id": selected_option_id,
        "is_marked_for_review": is_marked_for_review,
        "is_visited": True,
        "time_spent_sec": time_spent_sec,
        "client_seq": client_seq,
        "updated_at": _now_iso(),
    }

    _safe(
        lambda: supabase.table("mock_attempt_responses")
        .update(payload)
        .eq("attempt_id", attempt_id)
        .eq("question_id", question_id)
        .execute(),
        default=None,
    )

    record_server_event(
        supabase, attempt_id, user_id, QUESTION_ANSWERED,
        payload={
            "question_id": question_id,
            "selected_option_id": selected_option_id,
            "is_marked_for_review": is_marked_for_review,
            "time_spent_sec": time_spent_sec,
        },
    )

    return {"ok": True, "idempotent": False}


def _finalize_submission(
    supabase: Any,
    attempt: dict,
    user_id: str,
    *,
    submitted_at: str,
    event_type: str,
) -> tuple[dict, list[dict], list[dict]]:
    """Score an in-progress attempt and flip it to ``submitted``.

    Shared by the user-initiated ``submit_attempt`` and the sweeper's
    ``auto_submit_attempt``. Handles only the deterministic, snapshot-based work
    (scoring, status flip, lifecycle event, Mocks.jsx compat row). Derivation is
    NOT run here — callers decide whether to run it inline or schedule a job.
    """
    attempt_id = attempt["id"]
    resp_rows = _safe(
        lambda: supabase.table("mock_attempt_responses")
        .select("*")
        .eq("attempt_id", attempt_id)
        .execute(),
        default=None,
    )
    responses = getattr(resp_rows, "data", None) or []

    snapshot = attempt.get("template_snapshot") or {}
    neg_marking = bool(snapshot.get("negative_marking", True))

    total_correct = 0
    total_wrong = 0
    total_unattempted = 0
    score_raw = 0.0
    updates = []

    for r in responses:
        snap = r.get("question_snapshot") or {}
        correct_opt = snap.get("correct_option_id")
        selected = r.get("selected_option_id")
        marks = float(snap.get("marks") or 1)
        neg = float(snap.get("negative_marks") or 0)

        if not selected:
            total_unattempted += 1
            is_correct = None
            awarded = 0.0
        elif selected == correct_opt:
            total_correct += 1
            is_correct = True
            awarded = marks
            score_raw += marks
        else:
            total_wrong += 1
            is_correct = False
            if neg_marking:
                awarded = -neg
                score_raw -= neg
            else:
                awarded = 0.0

        updates.append({
            "id": r["id"],
            "is_correct": is_correct,
            "marks_awarded": awarded,
        })

    for upd in updates:
        _safe(
            lambda u=upd: supabase.table("mock_attempt_responses")
            .update({"is_correct": u["is_correct"], "marks_awarded": u["marks_awarded"]})
            .eq("id", u["id"])
            .execute(),
            default=None,
        )

    total_q = len(responses)
    max_score = sum(
        float((r.get("question_snapshot") or {}).get("marks") or 1)
        for r in responses
    )
    pct = round(score_raw / max_score * 100, 2) if max_score > 0 else 0.0

    _safe(
        lambda: supabase.table("mock_attempts")
        .update({
            "status": "submitted",
            "submitted_at": submitted_at,
            "score_raw": round(score_raw, 2),
            "score_percentage": pct,
            "total_correct": total_correct,
            "total_wrong": total_wrong,
            "total_unattempted": total_unattempted,
        })
        .eq("id", attempt_id)
        .execute(),
        default=None,
    )

    # Server-authoritative event — written immediately after the status flip.
    record_server_event(
        supabase, attempt_id, user_id, event_type,
        payload={
            "score_raw": round(score_raw, 2),
            "score_percentage": pct,
            "total_correct": total_correct,
            "total_wrong": total_wrong,
            "total_unattempted": total_unattempted,
        },
        occurred_at=submitted_at,
    )

    # Compatibility row for existing Mocks.jsx analytics
    _emit_mock_tests_row(supabase, user_id, attempt, score_raw, max_score,
                         total_correct, total_wrong, total_q, submitted_at)

    updated_attempt = {
        **attempt,
        "status": "submitted",
        "submitted_at": submitted_at,
        "score_raw": round(score_raw, 2),
        "score_percentage": pct,
        "total_correct": total_correct,
        "total_wrong": total_wrong,
        "total_unattempted": total_unattempted,
    }
    return updated_attempt, responses, updates


def submit_attempt(supabase: Any, user_id: str, attempt_id: str) -> dict:
    """Score and finalise the attempt. Idempotent — second call returns same result."""
    attempt = _fetch_attempt(supabase, user_id, attempt_id)

    if attempt["status"] == "submitted":
        return _build_result(supabase, attempt)

    if attempt["status"] != "in_progress":
        raise ValueError("attempt is not in progress")

    now_iso = _now_iso()
    updated_attempt, responses, updates = _finalize_submission(
        supabase, attempt, user_id, submitted_at=now_iso, event_type=ATTEMPT_SUBMITTED,
    )

    try:
        attempt_analytics.compute_and_persist(supabase, attempt_id)
        _complete_job(supabase, JOB_ANALYTICS_RETRY, attempt_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("derivation failed attempt=%s", attempt_id, exc_info=exc)
        schedule_job(supabase, JOB_ANALYTICS_RETRY, attempt_id, last_error=str(exc))

    return _build_result(supabase, updated_attempt, responses=responses, updates=updates)


def auto_submit_attempt(supabase: Any, attempt_id: str) -> dict:
    """Submit an expired in-progress attempt on the user's behalf (sweeper path).

    Idempotent: a no-op once the attempt has left ``in_progress``. Stamps
    ``submitted_at`` with the attempt's ``expires_at`` (the moment the window
    actually closed, not the sweeper's wall clock) and emits
    ``attempt.auto_submitted``. Derivation is scheduled as an ``analytics_retry``
    job rather than run synchronously, so one slow derivation cannot stall the
    sweep batch.
    """
    attempt = _fetch_attempt_by_id(supabase, attempt_id)
    if attempt is None or attempt.get("status") != "in_progress":
        return {"ok": True, "skipped": True}

    submitted_at = attempt.get("expires_at") or _now_iso()
    _finalize_submission(
        supabase, attempt, attempt["user_id"],
        submitted_at=submitted_at, event_type=ATTEMPT_AUTO_SUBMITTED,
    )
    schedule_job(supabase, JOB_ANALYTICS_RETRY, attempt_id)
    return {"ok": True, "skipped": False, "submitted_at": submitted_at}


def get_result(supabase: Any, user_id: str, attempt_id: str) -> dict:
    attempt = _fetch_attempt(supabase, user_id, attempt_id)
    if attempt["status"] != "submitted":
        raise ValueError("attempt not yet submitted")
    return _build_result(supabase, attempt)


# ── internal helpers ───────────────────────────────────────────────────────────

def _fetch_attempt(supabase: Any, user_id: str, attempt_id: str) -> dict:
    rows = _safe(
        lambda: supabase.table("mock_attempts")
        .select("*")
        .eq("id", attempt_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute(),
        default=None,
    )
    items = getattr(rows, "data", None) or []
    if not items:
        raise LookupError("attempt not found")
    return items[0]


def _fetch_attempt_by_id(supabase: Any, attempt_id: str) -> dict | None:
    """Fetch an attempt without an owner filter — for system/sweeper paths."""
    rows = _safe(
        lambda: supabase.table("mock_attempts")
        .select("*")
        .eq("id", attempt_id)
        .limit(1)
        .execute(),
        default=None,
    )
    return (getattr(rows, "data", None) or [None])[0]


def _time_remaining_sec(attempt: dict) -> int:
    expires_str = attempt.get("expires_at")
    if not expires_str:
        return 0
    try:
        expires = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
        delta = (expires - _now()).total_seconds()
        return max(0, int(delta))
    except Exception:  # noqa: BLE001
        return 0


def _serialise_question_for_attempt(q: dict, *, marks_per_correct: float = 1.0, marks_per_wrong: float = 0.25) -> dict:
    """Serialise a question for the attempt GET response.

    PR2: marks come from the frozen question_snapshot (which was written at
    attempt-start with template-level marks), not from the live question row.
    Callers should prefer reading from question_snapshot; this helper is used
    when re-hydrating from the snapshot dict directly.
    """
    return {
        "question_id": q["id"],
        "question_text": q["question_text"],
        "question_type": q["question_type"],
        "marks": float(q.get("marks") or marks_per_correct),
        "negative_marks": float(q.get("negative_marks") or marks_per_wrong),
        "options": [
            {
                "id": o["id"],
                "option_text": o["option_text"],
                "option_index": o["option_index"],
            }
            for o in (q.get("options") or [])
        ],
    }


def _build_result(
    supabase: Any,
    attempt: dict,
    responses: list[dict] | None = None,
    updates: list[dict] | None = None,
) -> dict:
    if responses is None:
        resp_rows = _safe(
            lambda: supabase.table("mock_attempt_responses")
            .select("*")
            .eq("attempt_id", attempt["id"])
            .execute(),
            default=None,
        )
        responses = getattr(resp_rows, "data", None) or []

    upd_by_id = {u["id"]: u for u in (updates or [])}

    per_question = []
    for r in responses:
        snap = r.get("question_snapshot") or {}
        upd = upd_by_id.get(r["id"], {})
        is_correct = upd.get("is_correct", r.get("is_correct"))
        marks_awarded = upd.get("marks_awarded", r.get("marks_awarded"))
        correct_opt = snap.get("correct_option_id")
        per_question.append({
            "question_id": r["question_id"],
            "question_text": snap.get("question_text"),
            "selected_option_id": r.get("selected_option_id"),
            "correct_option_id": correct_opt,
            "is_correct": is_correct,
            "marks_awarded": marks_awarded,
            "options": snap.get("options") or [],
            "explanation": snap.get("explanation"),
        })

    summary_rows = _safe(lambda: supabase.table("mock_attempt_summary").select("*").eq("attempt_id", attempt["id"]).limit(1).execute(), default=None)
    summary = (getattr(summary_rows, "data", None) or [None])[0]
    section_rows = _safe(lambda: supabase.table("mock_attempt_section_breakdown").select("*").eq("attempt_id", attempt["id"]).order("section_index").execute(), default=None)
    return {
        "attempt_id": attempt["id"],
        "status": attempt.get("status"),
        "submitted_at": attempt.get("submitted_at"),
        "score_raw": (summary or {}).get("score_raw", attempt.get("score_raw")),
        "score_percentage": (summary or {}).get("score_percentage", attempt.get("score_percentage")),
        "total_correct": (summary or {}).get("total_correct", attempt.get("total_correct")),
        "total_wrong": (summary or {}).get("total_wrong", attempt.get("total_wrong")),
        "total_unattempted": (summary or {}).get("total_unattempted", attempt.get("total_unattempted")),
        "section_breakdown": getattr(section_rows, "data", None) or [],
        "per_question": per_question,
    }




def get_analytics(supabase: Any, user_id: str, attempt_id: str) -> dict:
    attempt = _fetch_attempt(supabase, user_id, attempt_id)
    if attempt.get("status") != "submitted":
        raise ValueError("attempt not yet submitted")
    topics = _safe(lambda: supabase.table("mock_attempt_topic_breakdown").select("*").eq("attempt_id", attempt_id).execute(), default=None)
    classes = _safe(lambda: supabase.table("mock_attempt_response_classification").select("*").eq("attempt_id", attempt_id).execute(), default=None)
    summary_rows = _safe(lambda: supabase.table("mock_attempt_summary").select("analytics_quality").eq("attempt_id", attempt_id).limit(1).execute(), default=None)
    return {
        "attempt_id": attempt_id,
        "topic_breakdown": getattr(topics, "data", None) or [],
        "response_classification": getattr(classes, "data", None) or [],
        "analytics_quality": ((getattr(summary_rows, "data", None) or [{}])[0]).get("analytics_quality") or {},
    }


def get_review(supabase: Any, user_id: str, attempt_id: str) -> dict:
    attempt = _fetch_attempt(supabase, user_id, attempt_id)
    if attempt.get("status") != "submitted":
        raise ValueError("attempt not yet submitted")
    resp_rows = _safe(lambda: supabase.table("mock_attempt_responses").select("*").eq("attempt_id", attempt_id).execute(), default=None)
    cls_rows = _safe(lambda: supabase.table("mock_attempt_response_classification").select("question_id,error_type").eq("attempt_id", attempt_id).execute(), default=None)
    cls = {r.get("question_id"): r.get("error_type") for r in (getattr(cls_rows, "data", None) or [])}
    questions = []
    for r in (getattr(resp_rows, "data", None) or []):
        snap = r.get("question_snapshot") or {}
        questions.append({
            "question_id": r.get("question_id"),
            "question_snapshot": snap,
            "selected_option_id": r.get("selected_option_id"),
            "is_correct": r.get("is_correct"),
            "error_type": cls.get(r.get("question_id")),
            "explanation": snap.get("explanation"),
            "time_spent_sec": int(r.get("time_spent_sec") or 0),
        })
    return {"attempt_id": attempt_id, "questions": questions}

def _emit_mock_tests_row(
    supabase: Any,
    user_id: str,
    attempt: dict,
    score_raw: float,
    max_score: float,
    total_correct: int,
    total_wrong: int,
    total_q: int,
    submitted_at: str,
) -> None:
    """Write a mock_tests row compatible with the existing Mocks.jsx schema."""
    snap = attempt.get("template_snapshot") or {}
    duration_sec = int(snap.get("duration_sec") or 0)
    duration_mins = round(duration_sec / 60) if duration_sec else None

    _safe(
        lambda: supabase.table("mock_tests").insert({
            "user_id": user_id,
            "test_name": snap.get("name") or "Mock",
            "title": snap.get("name") or "Mock",
            "exam_name": snap.get("exam_family") or snap.get("slug") or "",
            "scored_marks": round(score_raw, 2),
            "total_marks": max_score,
            "duration_mins": duration_mins,
            "correct_answers": total_correct,
            "wrong_answers": total_wrong,
            "questions_attempted": total_correct + total_wrong,
            "review_state": "unreviewed",
            "attempted_at": submitted_at,
            "metadata": {"mock_attempt_id": attempt["id"]},
        }).execute(),
        default=None,
    )


class ConflictError(Exception):
    pass


# ── consolidated background jobs (PR-fix-3) ─────────────────────────────────────
#
# A single sweeper drains ``mock_attempt_jobs`` and dispatches by ``job_kind``.
# Running two cron loops over the same DB would compete on locks and split
# observability, so auto-submit and derivation retry share one loop. A new job
# kind (e.g. ``mastery_retry``) only needs a branch in ``_run_job``.

JOB_AUTO_SUBMIT = "auto_submit"
JOB_ANALYTICS_RETRY = "analytics_retry"
JOB_MASTERY_RETRY = "mastery_retry"

_ACTIVE_JOB_STATUSES = ["pending", "running"]


def _backoff_seconds(attempts: int) -> int:
    return min(2 ** max(attempts, 1), 300)


def schedule_job(
    supabase: Any,
    job_kind: str,
    attempt_id: str,
    *,
    scheduled_for: str | None = None,
    last_error: str | None = None,
) -> None:
    """Enqueue (or reschedule) an active job for an attempt.

    Idempotent against the partial unique index on (job_kind, attempt_id) for
    pending/running rows: if an active job already exists it is reset to pending
    with a fresh schedule rather than duplicated.
    """
    existing = _safe(
        lambda: supabase.table("mock_attempt_jobs")
        .select("id,attempts")
        .eq("job_kind", job_kind)
        .eq("attempt_id", attempt_id)
        .in_("status", _ACTIVE_JOB_STATUSES)
        .limit(1)
        .execute(),
        default=None,
    )
    item = (getattr(existing, "data", None) or [None])[0]
    now_iso = scheduled_for or _now_iso()
    if item:
        patch = {"status": "pending", "scheduled_for": now_iso, "updated_at": _now_iso()}
        if last_error is not None:
            patch["last_error"] = last_error[:500]
        _safe(lambda: supabase.table("mock_attempt_jobs").update(patch).eq("id", item["id"]).execute(), default=None)
    else:
        payload = {
            "job_kind": job_kind,
            "attempt_id": attempt_id,
            "scheduled_for": now_iso,
            "attempts": 0,
            "status": "pending",
            "last_error": last_error[:500] if last_error else None,
        }
        _safe(lambda: supabase.table("mock_attempt_jobs").insert(payload).execute(), default=None)


def _complete_job(supabase: Any, job_kind: str, attempt_id: str) -> None:
    """Mark any active job for (job_kind, attempt) done — keeps the row for audit."""
    _safe(
        lambda: supabase.table("mock_attempt_jobs")
        .update({"status": "done", "last_error": None, "updated_at": _now_iso()})
        .eq("job_kind", job_kind)
        .eq("attempt_id", attempt_id)
        .in_("status", _ACTIVE_JOB_STATUSES)
        .execute(),
        default=None,
    )


def _mark_running(supabase: Any, job: dict, now: datetime) -> int:
    """Claim a job: bump attempts (bounds crash loops) and flag it running."""
    attempts = int(job.get("attempts") or 0) + 1
    _safe(
        lambda: supabase.table("mock_attempt_jobs")
        .update({"status": "running", "attempts": attempts, "updated_at": now.isoformat()})
        .eq("id", job["id"])
        .execute(),
        default=None,
    )
    return attempts


def _reschedule_job(supabase: Any, job: dict, attempts: int, last_error: str, now: datetime) -> None:
    next_at = (now + timedelta(seconds=_backoff_seconds(attempts))).isoformat()
    _safe(
        lambda: supabase.table("mock_attempt_jobs")
        .update({"status": "pending", "scheduled_for": next_at, "last_error": last_error[:500], "updated_at": now.isoformat()})
        .eq("id", job["id"])
        .execute(),
        default=None,
    )


def _fail_job(supabase: Any, job: dict, last_error: str, now: datetime) -> None:
    _safe(
        lambda: supabase.table("mock_attempt_jobs")
        .update({"status": "failed", "last_error": last_error[:500], "updated_at": now.isoformat()})
        .eq("id", job["id"])
        .execute(),
        default=None,
    )


def _run_job(supabase: Any, job: dict) -> None:
    """Dispatch a single job by kind. Raises on failure so the sweeper retries."""
    kind = job.get("job_kind")
    attempt_id = job.get("attempt_id")
    if kind == JOB_AUTO_SUBMIT:
        auto_submit_attempt(supabase, attempt_id)
    elif kind == JOB_ANALYTICS_RETRY:
        attempt_analytics.compute_and_persist(supabase, attempt_id)
    else:
        raise RuntimeError(f"unknown job_kind {kind!r}")


def run_sweeper(
    supabase: Any,
    *,
    now: datetime | None = None,
    batch: int = 50,
    max_attempts: int = 5,
) -> dict:
    """Single background loop for the mock engine.

    Phase A enqueues auto-submit jobs for attempts whose window closed more than
    60s ago. Phase B claims due jobs and dispatches them by kind. A crash between
    claim and completion leaves the job ``running`` with ``scheduled_for`` in the
    past, so the next cycle reclaims it; both job kinds are idempotent, so
    reprocessing is safe and no orphan rows are produced.
    """
    now = now or _now()
    counts = {"enqueued": 0, "auto_submitted": 0, "derivations": 0, "failed": 0, "errors": 0}

    # Phase A — detect expired in-progress attempts, enqueue auto-submit jobs.
    threshold = (now - timedelta(seconds=60)).isoformat()
    expired = _safe(
        lambda: supabase.table("mock_attempts")
        .select("id")
        .eq("status", "in_progress")
        .lt("expires_at", threshold)
        .limit(batch)
        .execute(),
        default=None,
    )
    for row in (getattr(expired, "data", None) or []):
        schedule_job(supabase, JOB_AUTO_SUBMIT, row["id"], scheduled_for=now.isoformat())
        counts["enqueued"] += 1

    # Phase B — claim and run due jobs.
    due = _safe(
        lambda: supabase.table("mock_attempt_jobs")
        .select("*")
        .in_("status", _ACTIVE_JOB_STATUSES)
        .lte("scheduled_for", now.isoformat())
        .order("scheduled_for", desc=False)
        .limit(batch)
        .execute(),
        default=None,
    )
    for job in (getattr(due, "data", None) or []):
        if int(job.get("attempts") or 0) >= max_attempts:
            _fail_job(supabase, job, "max_attempts_exceeded", now)
            counts["failed"] += 1
            continue
        attempts = _mark_running(supabase, job, now)
        kind = job.get("job_kind")
        try:
            _run_job(supabase, job)
            _complete_job(supabase, kind, job.get("attempt_id"))
            if kind == JOB_AUTO_SUBMIT:
                counts["auto_submitted"] += 1
            elif kind == JOB_ANALYTICS_RETRY:
                counts["derivations"] += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("sweeper job failed kind=%s attempt=%s: %s", kind, job.get("attempt_id"), exc)
            _reschedule_job(supabase, job, attempts, str(exc), now)
            counts["errors"] += 1

    return counts
