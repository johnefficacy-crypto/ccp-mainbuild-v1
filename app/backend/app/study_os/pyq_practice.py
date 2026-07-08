"""PYQ v2 PR-5/6 (slice B) — learner PYQ practice attempt assembly.

Selects VERIFIED, actively-projected PYQ questions from ``mock_question_bank`` by
paper / section / topic and assembles them into an ad-hoc attempt through the
generated-attempt blueprint path (``start_attempt_from_blueprint``, migrations
174/175/178/179). No new attempt schema and no new route: the existing
``/study/mocks/attempts/{id}`` answer / submit / result / review flow serves the
practice attempt unchanged, and PR-5/6 slice A already makes that path render the
projected passage + printed option labels from the frozen snapshot.

Trust / correctness posture:
  * only ``reviewer_status in (verified, published, live)`` bank rows,
  * only rows whose PYQ projection is ``sync_status='active'`` (checked bounded
    to the candidate ids, not the whole table),
  * a practice attempt is single-exam — a set is never assembled across exams
    (topic practice REQUIRES ``exam_id``; any pool that still spans exams is
    rejected),
  * paper / section practice preserves the source PYQ **printed order**
    (``pyq_questions.display_order`` → ``question_number`` → ``source_question_ref``),
  * option/stimulus fidelity is frozen at start via ``_question_snapshot`` and
    the generated loader's fail-closed passage read.
"""
from __future__ import annotations

import logging
import uuid as _uuid
from datetime import datetime, timedelta, timezone

from app.study_os.generated_mock_attempt import _load_questions
from app.study_os.mock_engine import _question_snapshot
from app.utils.safe import safe_required

logger = logging.getLogger("career_copilot.study_os.pyq_practice")

_SELECTABLE = ("verified", "published", "live")
_ATTEMPT_TTL = timedelta(hours=24)
_DEFAULT_LIMIT = 100
_MAX_LIMIT = 200
# practice is a learning mode — no negative marking.
_MARKS_PER_CORRECT = 1.0
_MARKS_PER_WRONG = 0.0

# mode -> (blueprint source tag, mock_question_bank filter column)
_MODES: dict[str, tuple[str, str]] = {
    "paper": ("pyq_practice_paper", "pyq_paper_id"),
    "section": ("pyq_practice_section", "section_id"),
    "topic": ("pyq_practice_topic", "topic_id"),
}
# modes whose learner experience must follow the source paper's printed order.
_SOURCE_ORDERED_MODES = frozenset({"paper", "section"})


class PracticeInputError(ValueError):
    """Bad practice request — mapped to HTTP 422 by the endpoint."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_uuid(value: str, field: str) -> None:
    try:
        _uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        raise PracticeInputError(f"{field} must be a valid UUID") from None


def _active_projection_ids(sb, candidate_ids: list[str]) -> frozenset[str]:
    """The subset of ``candidate_ids`` whose PYQ projection is currently active.

    Bounded to the candidate ids (``.in_``) rather than scanning every active
    projection in the table — this is a learner-facing per-click path. Raises on
    read failure (fail-closed): a practice set must never be assembled from a bank
    whose active-projection guard could not be evaluated.
    """
    if not candidate_ids:
        return frozenset()
    rows = safe_required(
        lambda: sb.table("pyq_mock_question_projections")
        .select("mock_question_id")
        .eq("sync_status", "active")
        .in_("mock_question_id", candidate_ids)
        .execute(),
        op="pyq_practice.active_projections",
        log=logger,
        allow_empty=True,
    )
    if rows is None:
        raise RuntimeError("pyq_practice: could not read active PYQ projections")
    return frozenset(r["mock_question_id"] for r in rows)


def _printed_order_meta(sb, pyq_question_ids: list[str]) -> dict[str, dict]:
    """Source-order metadata per ``pyq_questions.id`` for printed-order sorting.

    PR-4 did not project the question-level printed order into
    ``mock_question_bank`` (only option/section order), so paper/section practice
    joins back to ``pyq_questions`` for ``display_order`` / ``question_number`` /
    ``source_question_ref``. Fail-closed on read error (paper/section practice
    must not silently fall back to arbitrary id order)."""
    if not pyq_question_ids:
        return {}
    rows = safe_required(
        lambda: sb.table("pyq_questions")
        .select("id,display_order,question_number,source_question_ref")
        .in_("id", pyq_question_ids)
        .execute(),
        op="pyq_practice.printed_order",
        log=logger,
        allow_empty=True,
    )
    if rows is None:
        raise RuntimeError("pyq_practice: could not read source PYQ printed order")
    return {r["id"]: r for r in rows}


def _num(v) -> tuple[int, float]:
    """Sort helper: numeric-first, NULLs/non-numeric last, deterministically."""
    if isinstance(v, bool):  # bool is an int subclass — treat as non-numeric
        return (1, 0.0)
    if isinstance(v, (int, float)):
        return (0, float(v))
    try:
        return (0, float(v))
    except (TypeError, ValueError):
        return (1, 0.0)


def select_practice_rows(
    sb, *, mode: str, exam_id: str | None, target_id: str, limit: int
) -> list[dict]:
    """Resolve the projected-PYQ bank rows for a practice request.

    Returns bank rows (not just ids), ordered by the source printed order for
    paper/section modes and newest-year-first for topic mode, capped to ``limit``.
    """
    if mode not in _MODES:
        raise PracticeInputError(f"unknown practice mode: {mode!r}")
    _, filter_col = _MODES[mode]
    now_iso = _now_iso()
    q = (
        sb.table("mock_question_bank")
        .select("id,pyq_question_id,pyq_paper_id,section_id,topic_id,exam_id,reviewer_status,valid_until,pyq_year")
        .in_("reviewer_status", list(_SELECTABLE))
        .eq(filter_col, target_id)
    )
    q = q.not_.is_("pyq_question_id", "null")
    if exam_id:
        q = q.eq("exam_id", exam_id)
    q = q.or_(f"valid_until.is.null,valid_until.gt.{now_iso}")
    res = safe_required(
        lambda: q.execute(),
        op="pyq_practice.select_rows",
        log=logger,
        allow_empty=True,
    )
    if res is None:
        raise RuntimeError("pyq_practice: could not read the practice question pool")

    candidates = [
        r for r in res
        if r.get("pyq_question_id")
        and (not r.get("valid_until") or str(r["valid_until"]) > now_iso)
    ]
    if not candidates:
        return []

    active = _active_projection_ids(sb, [r["id"] for r in candidates])
    pool = [r for r in candidates if r["id"] in active]
    if not pool:
        return []

    if mode in _SOURCE_ORDERED_MODES:
        meta = _printed_order_meta(sb, [r["pyq_question_id"] for r in pool if r.get("pyq_question_id")])

        def _key(r: dict) -> tuple:
            m = meta.get(r.get("pyq_question_id"), {})
            do = m.get("display_order")
            qn = m.get("question_number")
            sr = m.get("source_question_ref")
            return (
                do is None, _num(do),
                qn is None, _num(qn),
                str(sr) if sr is not None else "",
                str(r.get("id")),
            )
        pool.sort(key=_key)
    else:  # topic: newest PYQ year first, then id
        pool.sort(key=lambda r: (-(r.get("pyq_year") or 0), str(r.get("id"))))
    return pool[:limit]


def _resolve_exam_phase(sb, mode: str, target_id: str, rows: list[dict]) -> str | None:
    """Best-effort exam-phase for the blueprint (nullable on the attempt path)."""
    if mode == "section":
        res = safe_required(
            lambda: sb.table("exam_phase_sections").select("exam_phase_id").eq("id", target_id).limit(1).execute(),
            op="pyq_practice.section_phase",
            log=logger,
            allow_empty=True,
        )
        if res:
            return res[0].get("exam_phase_id")
        return None
    section_ids = sorted({r.get("section_id") for r in rows if r.get("section_id")})
    if not section_ids:
        return None
    res = safe_required(
        lambda: sb.table("exam_phase_sections").select("exam_phase_id").in_("id", section_ids).execute(),
        op="pyq_practice.rows_phase",
        log=logger,
        allow_empty=True,
    )
    phases = {r.get("exam_phase_id") for r in (res or []) if r.get("exam_phase_id")}
    return next(iter(phases)) if len(phases) == 1 else None


def _build_practice_payload(
    ids: list[str],
    questions_by_id: dict[str, dict],
    *,
    exam_id: str | None,
    exam_phase_id: str | None,
    source: str,
    mode: str,
    target_id: str,
) -> tuple[dict, list[dict], list[str]]:
    """Freeze the attempt payload. Fail-closed (mirrors generated attempts): every
    selected id must resolve to a usable MCQ snapshot and the frozen set must
    equal the selection exactly — a projected set never persists shrunk."""
    response_rows: list[dict] = []
    ordered_ids: list[str] = []
    missing_ids: list[str] = []
    bad_snapshot_ids: list[str] = []
    for qid in ids:
        q = questions_by_id.get(qid)
        if q is None:
            missing_ids.append(qid)
            continue
        snap = _question_snapshot(q, marks_per_correct=_MARKS_PER_CORRECT, marks_per_wrong=_MARKS_PER_WRONG)
        if not snap.get("options") or not snap.get("correct_option_id"):
            bad_snapshot_ids.append(qid)
        response_rows.append({"question_id": qid, "question_snapshot": snap})
        ordered_ids.append(qid)

    if missing_ids:
        raise RuntimeError(
            f"pyq_practice freeze aborted: {len(missing_ids)} selected question(s) "
            f"failed to load a bank row (e.g. {missing_ids[:5]})"
        )
    if bad_snapshot_ids:
        raise RuntimeError(
            f"pyq_practice freeze aborted: {len(bad_snapshot_ids)} MCQ snapshot(s) "
            f"missing options/correct_option_id (e.g. {bad_snapshot_ids[:5]})"
        )
    if len(response_rows) != len(ids):
        raise RuntimeError(
            f"pyq_practice freeze aborted: frozen response count {len(response_rows)} "
            f"!= selected count {len(ids)}"
        )

    template_snapshot = {
        "source": source,
        "exam_id": exam_id,
        "exam_phase_id": exam_phase_id,
        "generated": True,
        "practice": True,
        "practice_mode": mode,
        "practice_target_id": target_id,
        # shape consumed by mock_engine.get_attempt / scoring (same as start_attempt)
        "question_ids": ordered_ids,
        "sections": [
            {
                "section_index": 0,
                "section_id": None,
                "section_label": "Practice",
                "question_ids": ordered_ids,
                "question_count": len(ordered_ids),
                "marks_per_correct": _MARKS_PER_CORRECT,
                "marks_per_wrong": _MARKS_PER_WRONG,
            }
        ],
        "interface_mode": "simple",
        "allow_switching": True,
        # practice is a learning mode: no negative marking, no section locks.
        "negative_marking": False,
        "marks_per_correct": _MARKS_PER_CORRECT,
        "marks_per_wrong": _MARKS_PER_WRONG,
        "total_questions": len(ordered_ids),
        "section_locks_enabled": False,
    }
    return template_snapshot, response_rows, ordered_ids


def start_pyq_practice(
    sb,
    *,
    user_id: str,
    mode: str,
    target_id: str,
    exam_id: str | None = None,
    limit: int = _DEFAULT_LIMIT,
) -> dict:
    """Assemble and atomically start a PYQ practice attempt.

    Returns ``{outcome:'ready', attempt_id, blueprint_id, question_count,
    expires_at, source, exam_id}`` on success, or ``{outcome:'empty_pool'}`` when
    no eligible projected PYQ matches (endpoint → 409, zero writes). Raises
    ``PracticeInputError`` (→ 422) for bad input, or RuntimeError if the atomic
    RPC write fails (rolled back).
    """
    if mode not in _MODES:
        raise PracticeInputError(f"unknown practice mode: {mode!r}")
    if not target_id:
        raise PracticeInputError("target_id is required")
    _require_uuid(target_id, "target_id")
    if exam_id is not None:
        _require_uuid(exam_id, "exam_id")
    # topic ids are shared across exams — a topic practice set is only well-defined
    # inside one exam, so exam_id is mandatory for topic mode.
    if mode == "topic" and not exam_id:
        raise PracticeInputError("exam_id is required for topic practice")

    source, _ = _MODES[mode]
    limit = max(1, min(int(limit or _DEFAULT_LIMIT), _MAX_LIMIT))

    rows = select_practice_rows(sb, mode=mode, exam_id=exam_id, target_id=target_id, limit=limit)
    if not rows:
        return {"outcome": "empty_pool", "question_count": 0}

    # Single-exam invariant: never assemble an attempt spanning exams (would
    # contaminate attempt/analytics/mastery metadata under one recorded exam_id).
    pool_exams = {r.get("exam_id") for r in rows if r.get("exam_id")}
    if len(pool_exams) > 1:
        raise PracticeInputError(
            "practice selection spans multiple exams; pass exam_id to disambiguate"
        )
    resolved_exam_id = exam_id or (next(iter(pool_exams)) if pool_exams else None)

    ids = [r["id"] for r in rows]
    exam_phase_id = _resolve_exam_phase(sb, mode, target_id, rows)

    # _load_questions fails closed if the projected passage read fails.
    questions_by_id = _load_questions(sb, ids)
    template_snapshot, response_rows, ordered_ids = _build_practice_payload(
        ids,
        questions_by_id,
        exam_id=resolved_exam_id,
        exam_phase_id=exam_phase_id,
        source=source,
        mode=mode,
        target_id=target_id,
    )

    blueprint_for_rpc = {
        "source": source,
        "template_snapshot": template_snapshot,
        "section_snapshot": template_snapshot["sections"],
        "selector_snapshot": {"mode": mode, "target_id": target_id, "exam_id": resolved_exam_id},
        "question_ids": ordered_ids,
        "readiness_snapshot": {"question_count": len(ordered_ids)},
    }
    expires_at = (datetime.now(timezone.utc) + _ATTEMPT_TTL).isoformat()

    rows_out = safe_required(
        lambda: sb.rpc(
            "start_attempt_from_blueprint",
            {
                "p_user": user_id,
                "p_exam": resolved_exam_id,
                "p_exam_phase": exam_phase_id,
                "p_blueprint": blueprint_for_rpc,
                "p_template_snapshot": template_snapshot,
                "p_response_rows": response_rows,
                "p_expires_at": expires_at,
            },
        ).execute(),
        op="pyq_practice.start_attempt_from_blueprint",
        log=logger,
    )
    if not rows_out:
        raise RuntimeError(
            "pyq_practice: start_attempt_from_blueprint returned no row "
            "(atomic write failed; nothing was persisted)"
        )
    row = rows_out[0]
    return {
        "outcome": "ready",
        "attempt_id": row.get("attempt_id"),
        "blueprint_id": row.get("blueprint_id"),
        "question_count": len(ordered_ids),
        "expires_at": expires_at,
        "source": source,
        "exam_id": resolved_exam_id,
    }
