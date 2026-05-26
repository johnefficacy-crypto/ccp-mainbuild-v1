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

    q_rows = _safe(
        lambda: supabase.table("mock_question_bank")
        .select("*")
        .in_("id", question_ids)
        .eq("reviewer_status", "published")
        .or_(f"valid_until.is.null,valid_until.gt.{now_iso}")
        .execute(),
        default=None,
    )
    questions = {r["id"]: r for r in (getattr(q_rows, "data", None) or [])}

    opt_rows = _safe(
        lambda: supabase.table("mock_question_options")
        .select("*")
        .in_("question_id", question_ids)
        .order("option_index")
        .execute(),
        default=None,
    )
    opts_by_q: dict[str, list[dict]] = {}
    for o in (getattr(opt_rows, "data", None) or []):
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
        "options": [
            {
                "id": o["id"],
                "option_text": o["option_text"],
                "option_index": o["option_index"],
            }
            for o in (q.get("options") or [])
        ],
    }


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
    }

    attempt_rows = _require(
        lambda: supabase.table("mock_attempts").insert({
            "user_id": user_id,
            "template_id": template["id"],
            "template_snapshot": template_snapshot,
            "status": "in_progress",
            "started_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
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

    return {
        "attempt_id": attempt_id,
        "expires_at": expires_at.isoformat(),
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
    }


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
    return {"ok": True, "idempotent": False}


def submit_attempt(supabase: Any, user_id: str, attempt_id: str) -> dict:
    """Score and finalise the attempt. Idempotent — second call returns same result."""
    attempt = _fetch_attempt(supabase, user_id, attempt_id)

    if attempt["status"] == "submitted":
        return _build_result(supabase, attempt)

    if attempt["status"] != "in_progress":
        raise ValueError("attempt is not in progress")

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

    now_iso = _now_iso()
    _safe(
        lambda: supabase.table("mock_attempts")
        .update({
            "status": "submitted",
            "submitted_at": now_iso,
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

    # Compatibility row for existing Mocks.jsx analytics
    _emit_mock_tests_row(supabase, user_id, attempt, score_raw, max_score,
                         total_correct, total_wrong, total_q, now_iso)

    updated_attempt = {
        **attempt,
        "status": "submitted",
        "submitted_at": now_iso,
        "score_raw": round(score_raw, 2),
        "score_percentage": pct,
        "total_correct": total_correct,
        "total_wrong": total_wrong,
        "total_unattempted": total_unattempted,
    }
    return _build_result(supabase, updated_attempt, responses=responses, updates=updates)


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

    return {
        "attempt_id": attempt["id"],
        "status": attempt.get("status"),
        "submitted_at": attempt.get("submitted_at"),
        "score_raw": attempt.get("score_raw"),
        "score_percentage": attempt.get("score_percentage"),
        "total_correct": attempt.get("total_correct"),
        "total_wrong": attempt.get("total_wrong"),
        "total_unattempted": attempt.get("total_unattempted"),
        "per_question": per_question,
    }


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
