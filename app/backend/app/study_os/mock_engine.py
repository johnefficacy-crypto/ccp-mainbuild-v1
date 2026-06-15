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
from app.utils.safe import safe_required

logger = logging.getLogger("career_copilot.study_os.mock_engine")

# E2E Playwright fixtures seed mock_question_bank rows tagged with this
# source_type (app/supabase/seeds/e2e_fixtures.sql). They are 'published' so the
# fixed-id E2E selector can load them inside the E2E DB, but they must NEVER be
# eligible for production POOL selection — otherwise a test fixture could leak
# into a real generated/criteria-built attempt. The fixed-id path
# (_load_questions_for_template) loads explicit ids and is intentionally NOT
# filtered, so E2E keeps working.
_E2E_FIXTURE_SOURCE_TYPE = "e2e_fixture"



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

    _SELECTABLE = ["verified", "published", "live"]
    q_exec = supabase.table("mock_question_bank") \
        .select("*") \
        .in_("id", question_ids) \
        .in_("reviewer_status", _SELECTABLE) \
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


def _criteria_difficulty_targets(mix: dict, total: int) -> dict[str, int]:
    """Apportion ``total`` questions across difficulty buckets by ``mix`` fractions.

    Largest-remainder rounding so the per-bucket targets sum to exactly ``total``
    (plain rounding can over- or under-shoot once fractions are summed).
    """
    if not mix or total <= 0:
        return {}
    raw = {d: float(f or 0) * total for d, f in mix.items()}
    floors = {d: int(v) for d, v in raw.items()}
    remainder = total - sum(floors.values())
    for d in sorted(raw, key=lambda d: raw[d] - floors[d], reverse=True)[:max(remainder, 0)]:
        floors[d] += 1
    return floors


def _select_criteria_question_ids(supabase: Any, selector: dict, question_count: int) -> list[str]:
    """Resolve a ``criteria`` section selector to concrete published question ids.

    Honours the bank filters the admin UI can configure (exam_family, subject_id,
    topic_ids) and, when present, the ``difficulty_mix`` distribution. Only
    published, non-expired questions are eligible — same gate as ``fixed`` and
    the legacy ``config.question_ids`` path. If a difficulty bucket is short, the
    deficit is backfilled from the rest of the eligible pool so a thin bucket
    can't silently shrink the section below ``question_count``.
    """
    if question_count <= 0:
        return []
    filters = selector.get("filters") or {}
    _SELECTABLE = ["verified", "published", "live"]
    # Exclude E2E fixtures by construction: the criteria pool builds real
    # (generated) attempts, so a fixture row must never be drawn into one even if
    # it is published in this DB. Use is.null OR neq so NULL-provenance rows
    # (e.g. legacy authored questions) are RETAINED — a plain neq would drop them
    # because NULL <> 'e2e_fixture' is NULL in Postgres.
    q = (
        supabase.table("mock_question_bank")
        .select("*")
        .in_("reviewer_status", _SELECTABLE)
        .or_(f"source_type.is.null,source_type.neq.{_E2E_FIXTURE_SOURCE_TYPE}")
    )
    if filters.get("exam_family"):
        q = q.eq("exam_family", filters["exam_family"])
    if filters.get("subject_id"):
        q = q.eq("subject_id", filters["subject_id"])
    if filters.get("topic_ids"):
        q = q.in_("topic_id", list(filters["topic_ids"]))
    now_iso = _now_iso()
    q = q.or_(f"valid_until.is.null,valid_until.gt.{now_iso}")
    rows = _safe(lambda: q.execute(), default=None)
    pool = [
        r for r in (getattr(rows, "data", None) or [])
        if not r.get("valid_until") or str(r["valid_until"]) > now_iso
    ]
    # Deterministic ordering so the same template config yields the same set.
    pool.sort(key=lambda r: str(r.get("id")))

    mix = filters.get("difficulty_mix") or {}
    if not mix:
        return [r["id"] for r in pool[:question_count]]

    buckets: dict[str, list[dict]] = {}
    for r in pool:
        buckets.setdefault(r.get("difficulty") or "medium", []).append(r)
    chosen: list[str] = []
    used: set[str] = set()
    for diff, target in _criteria_difficulty_targets(mix, question_count).items():
        for r in buckets.get(diff, [])[:target]:
            chosen.append(r["id"])
            used.add(r["id"])
    if len(chosen) < question_count:
        for r in pool:
            if r["id"] in used:
                continue
            chosen.append(r["id"])
            if len(chosen) >= question_count:
                break
    return chosen[:question_count]


def select_questions_for_template(supabase: Any, template_id: str, user_id: str) -> list[dict]:
    """PR2d selector hook; supports section ``fixed`` and ``criteria`` selectors."""
    sections = _safe(lambda: supabase.table("mock_template_sections").select("*").eq("template_id", template_id).order("section_index").execute(), default=None)
    sec_rows = getattr(sections, "data", None) or []
    if not sec_rows:
        return []
    ordered: list[str] = []
    for sec in sec_rows:
        selector = sec.get("selector") or {}
        mode = selector.get("mode")
        if mode == "fixed":
            ordered.extend(selector.get("question_ids") or [])
        elif mode == "criteria":
            ordered.extend(_select_criteria_question_ids(supabase, selector, int(sec.get("question_count") or 0)))
    if not ordered:
        return []
    q_rows = _safe(lambda: supabase.table("mock_question_bank").select("*").in_("id", ordered).execute(), default=None)
    by_id = {r["id"]: r for r in (getattr(q_rows, "data", None) or [])}
    # Attach options (ordered by option_index) — without these the frozen
    # snapshot has no options and the attempt renders no answer choices.
    opt_rows = _safe(
        lambda: supabase.table("mock_question_options")
        .select("*")
        .in_("question_id", ordered)
        .order("option_index")
        .execute(),
        default=None,
    )
    opts_by_q: dict[str, list[dict]] = {}
    for o in (getattr(opt_rows, "data", None) or []):
        opts_by_q.setdefault(o["question_id"], []).append(o)
    return [{**by_id[qid], "options": opts_by_q.get(qid, [])} for qid in ordered if qid in by_id]


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
            "section_index": _question_section_index(snapshot, qid),
        })

    time_remaining = _time_remaining_sec(attempt)

    return {
        "attempt_id": attempt_id,
        "status": attempt["status"],
        "expires_at": attempt["expires_at"],
        "time_remaining_sec": time_remaining,
        "questions": questions_out,
        "current_section_index": int(attempt.get("current_section_index") or 0),
        "section_locks_enabled": bool(attempt.get("section_locks_enabled")),
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
    _safe(lambda: supabase.table("mock_attempt_section_state").upsert({"attempt_id": attempt_id, "section_index": section_index, "entered_at": now}).execute(), default=None)  # safe-write-ok: navigation state; non-critical, not used for scoring
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
            # A client retry after a partial-failure write replays the same
            # client_seq. The row was already written (and the QUESTION_ANSWERED
            # event already emitted) on the first call, so we acknowledge without
            # re-processing — no duplicate row, no duplicate side effect.
            return {"ok": True, "idempotent": True, "status": "already_recorded"}

    payload = {
        "selected_option_id": selected_option_id,
        "is_marked_for_review": is_marked_for_review,
        "is_visited": True,
        "time_spent_sec": time_spent_sec,
        "client_seq": client_seq,
        "updated_at": _now_iso(),
    }

    try:
        result = (
            supabase.table("mock_attempt_responses")
            .update(payload)
            .eq("attempt_id", attempt_id)
            .eq("question_id", question_id)
            .execute()
        )
    except Exception as exc:
        raise AnswerPersistenceError(
            f"DB write rejected for attempt={attempt_id} question={question_id}: {exc}"
        ) from exc
    updated_rows = getattr(result, "data", None) or []
    if not updated_rows:
        raise AnswerPersistenceError(
            f"answer update affected 0 rows: attempt={attempt_id} question={question_id}"
        )

    # INVARIANT: events are telemetry, not source of truth.
    # mock_attempt_responses.selected_option_id is the only authority for scoring.
    # Never record QUESTION_ANSWERED before the response row update is confirmed.
    # See docs/mock_engine/attempt_save_semantics.md.
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

    # Per-response score writes are correctness-critical: a silent failure here
    # would flip the attempt to ``submitted`` (below) while individual responses
    # keep null/stale marks. Use safe_required and raise on failure so the
    # attempt is left ``in_progress`` (the safe state) and the caller can retry —
    # re-scoring is idempotent because marks come from the frozen snapshot and
    # these are overwrites, not increments.
    for upd in updates:
        written = safe_required(
            lambda u=upd: supabase.table("mock_attempt_responses")
            .update({"is_correct": u["is_correct"], "marks_awarded": u["marks_awarded"]})
            .eq("id", u["id"])
            .execute(),
            op="mock_engine.finalize_response_score",
            log=logger,
        )
        if written is None:
            raise SubmissionPersistenceError(
                f"response score write failed: attempt={attempt_id} response={upd['id']}"
            )

    total_q = len(responses)
    max_score = sum(
        float((r.get("question_snapshot") or {}).get("marks") or 1)
        for r in responses
    )
    pct = round(score_raw / max_score * 100, 2) if max_score > 0 else 0.0

    # Attempt finalization is correctness-critical: this flip + aggregate scores
    # is the headline result the client reads back. A silent failure must not be
    # reported as a successful submission. Raising here (before the submitted
    # event and the mock_tests compat row below) leaves the attempt
    # ``in_progress`` so a retry re-runs cleanly.
    finalized = safe_required(
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
        op="mock_engine.finalize_attempt",
        log=logger,
    )
    if finalized is None:
        raise AttemptFinalizationError(
            f"attempt finalization write failed: attempt={attempt_id}"
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


def _repair_submitted_side_effects(supabase: Any, attempt_id: str) -> None:
    """Idempotently reconcile post-finalize side effects for a submitted attempt.

    Covers the ambiguous case where the ``mock_attempts`` finalization UPDATE
    committed on the server but the client call raised before the submitted
    event, the ``mock_tests`` compat row, or analytics derivation ran — so the
    resubmit fast path would otherwise skip them forever. Self-healing and
    best-effort: when a side effect is missing it schedules the existing retry
    job (the sweeper drains it and both jobs are idempotent). Never raises — a
    repair failure must not break an otherwise-successful resubmit. The
    ATTEMPT_SUBMITTED event is telemetry only (not source of truth) and is
    intentionally not re-emitted here to avoid duplicate events.
    """
    compat = _safe(
        lambda: supabase.table("mock_tests")
        .select("id")
        .eq("mock_attempt_id", attempt_id)
        .limit(1)
        .execute(),
        default=None,
    )
    if not getattr(compat, "data", None):
        schedule_job(supabase, JOB_MOCK_TESTS_RETRY, attempt_id)

    summary = _safe(
        lambda: supabase.table("mock_attempt_summary")
        .select("attempt_id")
        .eq("attempt_id", attempt_id)
        .limit(1)
        .execute(),
        default=None,
    )
    if not getattr(summary, "data", None):
        schedule_job(supabase, JOB_ANALYTICS_RETRY, attempt_id)


def submit_attempt(
    supabase: Any,
    user_id: str,
    attempt_id: str,
    claimed_answered_count: int | None = None,
) -> dict:
    """Score and finalise the attempt. Idempotent — second call returns same result."""
    attempt = _fetch_attempt(supabase, user_id, attempt_id)

    if attempt["status"] == "submitted":
        # Reconcile the ambiguous "finalization UPDATE committed but the client
        # raised before the side effects ran" case: a retry would otherwise take
        # this fast path and never (re)create the mock_tests compat row or
        # analytics, leaving a submitted attempt missing from history/analytics.
        _repair_submitted_side_effects(supabase, attempt_id)
        return _build_result(supabase, attempt)

    if attempt["status"] != "in_progress":
        raise ValueError("attempt is not in progress")

    if claimed_answered_count is not None:
        resp_rows = _safe(
            lambda: supabase.table("mock_attempt_responses")
            .select("selected_option_id")
            .eq("attempt_id", attempt_id)
            .execute(),
            default=None,
        )
        db_answered = sum(
            1 for r in (getattr(resp_rows, "data", None) or [])
            if r.get("selected_option_id") is not None
        )
        if claimed_answered_count > db_answered:
            raise SubmitConsistencyError(
                f"client claims {claimed_answered_count} answered, "
                f"DB has {db_answered}; refusing to submit"
            )

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
    # score_raw/score_percentage originate as Decimal and are persisted via
    # model_dump(mode="json"), i.e. as JSON strings. Coerce back to a number so
    # the result contract is numeric regardless of which source (summary vs
    # attempt row) supplies the value.
    def _as_number(v):
        if isinstance(v, str):
            try:
                return float(v)
            except ValueError:
                return v
        return v
    return {
        "attempt_id": attempt["id"],
        "status": attempt.get("status"),
        "submitted_at": attempt.get("submitted_at"),
        "score_raw": _as_number((summary or {}).get("score_raw", attempt.get("score_raw"))),
        "score_percentage": _as_number((summary or {}).get("score_percentage", attempt.get("score_percentage"))),
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

    try:
        supabase.table("mock_tests").insert({
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
            "source_type": "platform_attempt",
            "trust_level": "platform_verified",
            "mock_attempt_id": attempt["id"],
            "analysis_payload": {"mock_attempt_id": attempt["id"]},
        }).execute()
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "mock_tests insert failed attempt=%s, scheduling retry: %s",
            attempt.get("id"), exc,
        )
        schedule_job(supabase, JOB_MOCK_TESTS_RETRY, attempt["id"], last_error=str(exc))


def _retry_emit_mock_tests_row(supabase: Any, attempt_id: str) -> None:
    """Idempotent re-emit of a mock_tests compat row. Called by the sweeper."""
    existing = _safe(
        lambda: supabase.table("mock_tests")
        .select("id")
        .eq("mock_attempt_id", attempt_id)
        .limit(1)
        .execute(),
        default=None,
    )
    if getattr(existing, "data", None):
        return  # already present — idempotent no-op

    attempt = _fetch_attempt_by_id(supabase, attempt_id)
    if attempt is None:
        raise RuntimeError(f"attempt {attempt_id} not found for mock_tests_retry")

    resp_rows = _safe(
        lambda: supabase.table("mock_attempt_responses")
        .select("question_snapshot")
        .eq("attempt_id", attempt_id)
        .execute(),
        default=None,
    )
    responses = getattr(resp_rows, "data", None) or []
    max_score = sum(
        float((r.get("question_snapshot") or {}).get("marks") or 1) for r in responses
    )

    snap = attempt.get("template_snapshot") or {}
    duration_sec = int(snap.get("duration_sec") or 0)
    duration_mins = round(duration_sec / 60) if duration_sec else None
    score_raw = float(attempt.get("score_raw") or 0)
    total_correct = int(attempt.get("total_correct") or 0)
    total_wrong = int(attempt.get("total_wrong") or 0)
    submitted_at = attempt.get("submitted_at") or _now_iso()

    # Propagate exceptions so the sweeper's retry/backoff loop handles them.
    supabase.table("mock_tests").insert({
        "user_id": attempt["user_id"],
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
        "source_type": "platform_attempt",
        "trust_level": "platform_verified",
        "mock_attempt_id": attempt_id,
        "analysis_payload": {"mock_attempt_id": attempt_id},
    }).execute()


class ConflictError(Exception):
    pass


class AnswerPersistenceError(RuntimeError):
    pass


class SubmissionPersistenceError(RuntimeError):
    """A per-response score write failed during finalization.

    Raised before the attempt is flipped to ``submitted``, so the attempt is
    left ``in_progress`` and the submission is safely re-runnable.
    """


class AttemptFinalizationError(RuntimeError):
    """The attempt status/score finalization write failed.

    Raised before the submitted event and mock_tests compat row are emitted, so
    the attempt is left ``in_progress`` and the submission is safely re-runnable.
    """


class SubmitConsistencyError(RuntimeError):
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
JOB_MOCK_TESTS_RETRY = "mock_tests_retry"

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
        _safe(lambda: supabase.table("mock_attempt_jobs").insert(payload).execute(), default=None)  # safe-write-ok: fire-and-forget job scheduling; sweeper re-enqueues missed auto-submit jobs


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
    elif kind == JOB_MOCK_TESTS_RETRY:
        _retry_emit_mock_tests_row(supabase, attempt_id)
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
