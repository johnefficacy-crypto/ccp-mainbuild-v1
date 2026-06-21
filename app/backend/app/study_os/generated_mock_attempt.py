"""Generated-mock ATTEMPT START service (A-PR3, D4 Option-B). MUTATING.

This is the FIRST mutating Track A service. ``persist_and_start`` assembles a
generated-mock blueprint (A-PR1 envelope + A-PR2 selection) using SERVER-SIDE
thresholds, and — ONLY when the readiness outcome is 'ready' — atomically
persists the blueprint and starts an attempt from it via the
``start_attempt_from_blueprint`` plpgsql function (migration 179).

Hardening invariants ("born hardened"):

  * SERVER-SIDE thresholds. The selection thresholds (selectable_statuses,
    verified_status, min_per_section, min_locked_coverage) are fixed here and are
    NEVER taken from the caller. A client cannot loosen the readiness gate.
  * READY-GATE. When the outcome is not 'ready' the service starts NOTHING — it
    returns the verdict and performs zero writes.
  * SINGLE ATOMIC WRITE. The RPC is the only write. It runs in ONE Postgres
    transaction (blueprint + attempt + N response rows + status flip) and rolls
    the whole thing back on any failure — no orphan rows. The write goes through
    ``safe_required`` and RAISES on failure (no ``_safe`` on the write path).
  * LOADER REUSE. Generated attempts reuse ``mock_attempts.template_snapshot``
    and frozen ``question_snapshot`` rows in the SAME shape ``start_attempt``
    produces, so the entire mock_engine read/score path loads them unchanged —
    no FE or loader change, mock_engine stays byte-identical to main.

OUT OF SCOPE: exposure tracking (A-PR4), personalization (A-PR5), descriptive
items (Track B), the parked template-path pool divergence, content seeding, and
the operator live-canary smoke (a separate post-merge step).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from app.study_os.mock_blueprint_selection import build_blueprint_with_selection
from app.study_os.mock_engine import _question_snapshot
from app.utils.safe import safe_required

logger = logging.getLogger("career_copilot.study_os.generated_mock_attempt")

# ── SERVER-SIDE thresholds — fixed, never caller-supplied ────────────────────────
# These mirror the diagnostic's production discipline (published-only selectable
# pool, verified depth signal, ≥30 base MCQs/section, ≥1 locked coverage row).
# Holding them here is the readiness gate's teeth: the endpoint ignores any
# client-supplied threshold fields, so a caller cannot weaken the bar.
_SELECTABLE_STATUSES = ["published"]
_VERIFIED_STATUS = "verified"
_MIN_PER_SECTION = 30
_MIN_LOCKED_COVERAGE = 1

# Generated attempts get a 24h window (mirrors start_attempt's expires_at idea;
# the value is computed server-side and passed to the RPC as p_expires_at).
_ATTEMPT_TTL = timedelta(hours=24)

# Fallbacks when a section's authored marks/negative_marking are absent. Marks are
# section-bound for generated attempts (each section carries total marks +
# negative_marking); per-question marks are derived from them and frozen into the
# question_snapshot, exactly like template attempts freeze template-level marks.
_DEFAULT_MARKS_PER_CORRECT = 1.0
_DEFAULT_MARKS_PER_WRONG = 0.25


def _parse_negative_marking(value) -> float:
    """Per-question wrong-answer penalty (absolute) from an authored value.

    Authored ``negative_marking`` is stored as a signed string (e.g. '-0.50').
    Coerce to a non-negative float; fall back to the default on absence/garbage.
    """
    try:
        return abs(float(value))
    except (TypeError, ValueError):
        return _DEFAULT_MARKS_PER_WRONG


def _load_questions(sb, question_ids: list[str]) -> dict[str, dict]:
    """Fetch question rows + ordered options for the selected ids.

    READ path (not a write). The ids come from A-PR2 selection over the readiness
    base pool, so every id resolves; options are attached so the frozen
    ``question_snapshot`` carries answer choices.
    """
    if not question_ids:
        return {}
    q_rows = (
        safe_required(
            lambda: sb.table("mock_question_bank")
            .select("*")
            .in_("id", question_ids)
            .execute(),
            op="generated_mock_attempt.load_questions",
            log=logger,
            allow_empty=True,
        )
        or []
    )
    opt_rows = (
        safe_required(
            lambda: sb.table("mock_question_options")
            .select("*")
            .in_("question_id", question_ids)
            .order("option_index")
            .execute(),
            op="generated_mock_attempt.load_options",
            log=logger,
            allow_empty=True,
        )
        or []
    )
    opts_by_q: dict[str, list[dict]] = {}
    for o in opt_rows:
        opts_by_q.setdefault(o["question_id"], []).append(o)
    return {r["id"]: {**r, "options": opts_by_q.get(r["id"], [])} for r in q_rows}


def _build_attempt_payload(
    payload: dict,
    questions_by_id: dict[str, dict],
    *,
    exam_id: str,
    exam_phase_id: str,
) -> tuple[dict, list[dict], list[str]]:
    """Build the attempt ``template_snapshot`` + frozen response rows.

    Reuses ``_question_snapshot`` and mirrors the shape ``start_attempt`` writes
    (``question_ids`` / ``sections`` with per-section ``question_ids`` /
    ``interface_mode``), so ``get_attempt`` and the scoring path consume it with
    no special-casing. Per-section ids are recovered from the flat, section-
    ordered ``question_ids`` using the selector's per-section ``selected_count``.
    """
    section_meta = {
        s.get("section_id"): s for s in (payload.get("section_snapshot") or [])
    }
    selector_sections = (payload.get("selector_snapshot") or {}).get("sections") or []
    flat_ids = list(payload.get("question_ids") or [])

    snapshot_sections: list[dict] = []
    response_rows: list[dict] = []
    ordered_ids: list[str] = []
    missing_ids: list[str] = []          # selected ids that failed to load a bank row
    bad_snapshot_ids: list[str] = []     # MCQ snapshots missing options/correct_option_id
    cursor = 0

    for idx, sel in enumerate(selector_sections):
        count = int(sel.get("selected_count") or 0)
        sec_ids = flat_ids[cursor : cursor + count]
        cursor += count

        meta = section_meta.get(sel.get("section_id"), {})
        authored_count = int(sel.get("question_count") or len(sec_ids) or 0)
        sec_marks = meta.get("marks")
        if sec_marks is not None and authored_count > 0:
            per_q_correct = float(sec_marks) / authored_count
        else:
            per_q_correct = _DEFAULT_MARKS_PER_CORRECT
        per_q_wrong = _parse_negative_marking(meta.get("negative_marking"))

        section_ids_loaded: list[str] = []
        for qid in sec_ids:
            q = questions_by_id.get(qid)
            if q is None:
                # FAIL CLOSED: a selected id that does not resolve to a bank row
                # (data drift / race) must NOT silently shrink the attempt. Record
                # it and raise after the loop — never `continue` into a short freeze.
                missing_ids.append(qid)
                continue
            snapshot = _question_snapshot(
                q,
                marks_per_correct=per_q_correct,
                marks_per_wrong=per_q_wrong,
            )
            # MCQ integrity: a scoreable single-option item needs both options and
            # a correct_option_id frozen, or the scorer cannot mark it.
            if not snapshot.get("options") or not snapshot.get("correct_option_id"):
                bad_snapshot_ids.append(qid)
            response_rows.append(
                {
                    "question_id": qid,
                    "question_snapshot": snapshot,
                }
            )
            section_ids_loaded.append(qid)
            ordered_ids.append(qid)

        snapshot_sections.append(
            {
                "section_index": idx,
                "section_id": sel.get("section_id"),
                "section_label": sel.get("section_label"),
                "subject_id": sel.get("subject_id"),
                "question_ids": section_ids_loaded,
                "question_count": len(section_ids_loaded),
                "duration_mins": meta.get("duration_mins"),
                "marks_per_correct": per_q_correct,
                "marks_per_wrong": per_q_wrong,
            }
        )

    # FAIL-CLOSED freeze invariant (checked BEFORE the RPC, so a violation writes
    # nothing): every selected question must resolve to a usable MCQ snapshot and
    # the frozen set must equal the selection exactly — a ready 100-question
    # selection can never persist as a 99-question attempt.
    if missing_ids:
        raise RuntimeError(
            "generated attempt freeze aborted: "
            f"{len(missing_ids)} selected question(s) failed to load a bank row "
            f"(e.g. {missing_ids[:5]}); refusing to start a shrunk attempt"
        )
    if bad_snapshot_ids:
        raise RuntimeError(
            "generated attempt freeze aborted: "
            f"{len(bad_snapshot_ids)} MCQ snapshot(s) missing options/"
            f"correct_option_id (e.g. {bad_snapshot_ids[:5]})"
        )
    if len(response_rows) != len(flat_ids):
        raise RuntimeError(
            "generated attempt freeze aborted: frozen response count "
            f"{len(response_rows)} != selected question count {len(flat_ids)}"
        )

    template_snapshot = {
        # Provenance — these mirror the blueprint, NOT a mock_templates row.
        "source": payload.get("source"),
        "exam_id": exam_id,
        "exam_phase_id": exam_phase_id,
        "generated": True,
        # Shape consumed by mock_engine.get_attempt / scoring (same as start_attempt).
        "question_ids": ordered_ids,
        "sections": snapshot_sections,
        "interface_mode": "simple",
        "allow_switching": True,
        # negative_marking governs the scoring path; per-question marks are frozen
        # per question_snapshot above. Section locks are off for generated attempts.
        "negative_marking": True,
        "marks_per_correct": _DEFAULT_MARKS_PER_CORRECT,
        "marks_per_wrong": _DEFAULT_MARKS_PER_WRONG,
        "total_questions": len(ordered_ids),
        "section_locks_enabled": False,
    }
    return template_snapshot, response_rows, ordered_ids


def persist_and_start(
    sb,
    *,
    user_id: str,
    exam_id: str,
    exam_phase_id: str,
    source: str = "exam_realistic",
) -> dict:
    """Build a generated blueprint and atomically start an attempt from it.

    Returns a dict carrying ``outcome``:
      * ready    → {outcome:'ready', blueprint_id, attempt_id, question_count,
        expires_at, selector_snapshot}.
      * non-ready (thin_bank / blocked) → {outcome, readiness, section_shortfall,
        thresholds} and performs ZERO writes (the endpoint maps this to 409).

    Raises RuntimeError if the readiness was 'ready' but the atomic RPC write
    failed (the transaction rolled back, so nothing was persisted).
    """
    # 1. Assemble the blueprint with SERVER-SIDE thresholds. Non-mutating.
    payload = build_blueprint_with_selection(
        sb,
        exam_id=exam_id,
        exam_phase_id=exam_phase_id,
        user_id=user_id,
        source=source,
        selectable_statuses=_SELECTABLE_STATUSES,
        verified_status=_VERIFIED_STATUS,
        min_per_section=_MIN_PER_SECTION,
        min_locked_coverage=_MIN_LOCKED_COVERAGE,
    )

    outcome = payload.get("outcome")
    if outcome != "ready":
        # READY-GATE: start nothing, write nothing. Surface the verdict.
        return {
            "outcome": outcome,
            "readiness": payload.get("readiness_snapshot"),
            "section_shortfall": payload.get("section_shortfall") or [],
            "thresholds": payload.get("thresholds"),
        }

    # 2. Load the selected questions + options and freeze the attempt payload.
    flat_ids = list(payload.get("question_ids") or [])
    questions_by_id = _load_questions(sb, flat_ids)
    template_snapshot, response_rows, ordered_ids = _build_attempt_payload(
        payload, questions_by_id, exam_id=exam_id, exam_phase_id=exam_phase_id
    )

    # 3. The blueprint content columns the RPC persists into mock_generated_blueprints.
    blueprint_for_rpc = {
        "source": payload.get("source"),
        "template_snapshot": payload.get("template_snapshot"),
        "section_snapshot": payload.get("section_snapshot"),
        "selector_snapshot": payload.get("selector_snapshot"),
        "question_ids": ordered_ids,
        "readiness_snapshot": payload.get("readiness_snapshot"),
    }

    expires_at = (datetime.now(timezone.utc) + _ATTEMPT_TTL).isoformat()

    # 4. THE ONLY WRITE — one atomic transaction. safe_required surfaces failure
    #    as None (logged), and we RAISE so a partial/rolled-back write never looks
    #    like success. No _safe on this path.
    rows = safe_required(
        lambda: sb.rpc(
            "start_attempt_from_blueprint",
            {
                "p_user": user_id,
                "p_exam": exam_id,
                "p_exam_phase": exam_phase_id,
                "p_blueprint": blueprint_for_rpc,
                "p_template_snapshot": template_snapshot,
                "p_response_rows": response_rows,
                "p_expires_at": expires_at,
            },
        ).execute(),
        op="generated_mock_attempt.start_attempt_from_blueprint",
        log=logger,
    )
    if not rows:
        raise RuntimeError(
            "start_attempt_from_blueprint returned no row (atomic write failed; "
            "nothing was persisted)"
        )

    row = rows[0]
    return {
        "outcome": "ready",
        "blueprint_id": row.get("blueprint_id"),
        "attempt_id": row.get("attempt_id"),
        "question_count": len(ordered_ids),
        # Surfaced to the caller: the 24h blueprint validity window (server-set)
        # and the honest per-section selector snapshot (eligible/selected/relaxed).
        "expires_at": expires_at,
        "selector_snapshot": payload.get("selector_snapshot"),
    }
