"""Shared onboarding-calibration gate logic.

Single source of truth for the calibration gate so the user-facing API, the
planner, scheduled regeneration, and any other caller enforce identical
semantics. This module NEVER writes to ``user_topic_mastery`` and never derives
mastery — it only resolves the required subject set, reads the explicit
``user_exam_calibration`` gate record, and answers two questions:

  * ``calibration_required`` — must this user calibrate before a FIRST plan can
    be generated?  (drives the interstitial + the backend plan precondition)
  * ``gate_status`` — has the user explicitly completed/skipped calibration?
    (authorises self-reported prior consumption: only ``completed`` does)

Unlock state (may a plan be generated?) and evidence-consumption state (may
self-reported priors influence scoring?) are deliberately kept separate.

**Fail closed on read failure.** Every read reports an explicit health flag.
When the gate state cannot be determined (a coverage / topic / mastery /
subject / gate / plan read failed), the helpers do NOT silently treat the user
as "nothing to calibrate" (which would unlock generation) — they surface
``CalibrationUnavailable`` / ``check_failed`` so the caller can return a
retryable error instead of a bypass.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)


class CalibrationUnavailable(Exception):
    """Calibration state could not be determined due to a read failure.

    Callers MUST fail closed: do not unlock plan generation and do not report
    the user as calibrated — surface a retryable error (e.g. HTTP 503).
    """


# Server-owned band → prior_mastery and attempts → confidence maps. The client
# only ever submits a band; these live here so the API is the sole writer.
BAND_TO_PRIOR_MASTERY: dict[str, float | None] = {
    "strong": 80.0,
    "decent": 60.0,
    "weak": 35.0,
    "new": None,
}


def report_confidence_from_attempts(attempts_used: int) -> float:
    if attempts_used == 0:
        return 0.5
    if attempts_used == 1:
        return 0.75
    return 1.0


def required_subject_set_hash(subject_ids: list[str]) -> str:
    """Stable hash of the required subject set (order/dup-independent)."""
    return hashlib.sha256(
        ",".join(sorted({str(s) for s in subject_ids})).encode("utf-8")
    ).hexdigest()


def _read(call) -> tuple[Any, bool]:
    """Run a read; return ``(value, ok)``. ``ok`` is False on any exception."""
    try:
        return call(), True
    except Exception as exc:  # noqa: BLE001
        logger.warning("calibration read failed: %s", exc)
        return None, False


def resolve_required_subjects(
    supabase: Any, exam_id: str, user_id: str
) -> tuple[list[dict], bool]:
    """Return ``(required_subjects, ok)``.

    A subject is REQUIRED only when at least one of its locked-coverage topics
    has no ``user_topic_mastery`` row for this user (i.e. there is no validated
    mastery to supersede a self-reported prior). Subjects whose every locked
    topic is already validated are dropped. Distinct + sorted by ``subject_id``.

    ``ok`` is False when ANY underlying read (coverage, topics, mastery,
    subjects) failed — in that case the subject list is ``[]`` but callers must
    treat the state as UNKNOWN (fail closed), NOT as "nothing to calibrate".
    A legitimately empty required set returns ``([], True)``.
    """
    cov_rows, ok = _read(
        lambda: (
            supabase.table("exam_topic_coverage")
            .select("topic_id")
            .eq("exam_id", exam_id)
            .eq("reviewer_status", "locked")
            .limit(5000)
            .execute()
            .data
        )
    )
    if not ok:
        return [], False
    topic_ids = list({r["topic_id"] for r in (cov_rows or []) if r.get("topic_id")})
    if not topic_ids:
        return [], True

    topic_rows, ok = _read(
        lambda: (
            supabase.table("topics")
            .select("id, subject_id")
            .in_("id", topic_ids)
            .limit(5000)
            .execute()
            .data
        )
    )
    if not ok:
        return [], False
    subject_topics: dict[str, set[str]] = {}
    for t in (topic_rows or []):
        sid = t.get("subject_id")
        tid = t.get("id")
        if sid is None or tid is None:
            continue
        subject_topics.setdefault(str(sid), set()).add(str(tid))
    if not subject_topics:
        return [], True

    mastery_rows, ok = _read(
        lambda: (
            supabase.table("user_topic_mastery")
            .select("topic_id")
            .eq("user_id", user_id)
            .limit(5000)
            .execute()
            .data
        )
    )
    if not ok:
        return [], False
    validated_topic_ids = {
        str(m["topic_id"]) for m in (mastery_rows or []) if m.get("topic_id")
    }

    required_ids = [
        sid
        for sid, tids in subject_topics.items()
        if any(tid not in validated_topic_ids for tid in tids)
    ]
    if not required_ids:
        return [], True

    subj_rows, ok = _read(
        lambda: (
            supabase.table("subjects")
            .select("id, name")
            .in_("id", required_ids)
            .limit(5000)
            .execute()
            .data
        )
    )
    if not ok:
        return [], False
    names_by_id = {
        str(s["id"]): s.get("name") for s in (subj_rows or []) if s.get("id") is not None
    }

    return (
        [
            {"subject_id": sid, "subject_name": names_by_id.get(sid)}
            for sid in sorted(required_ids)
        ],
        True,
    )


def read_gate(supabase: Any, user_id: str, exam_id: str) -> tuple[dict | None, bool]:
    """Return ``(gate_row_or_None, ok)`` for the ``user_exam_calibration`` row."""
    rows, ok = _read(
        lambda: (
            supabase.table("user_exam_calibration")
            .select("status, required_subject_set_hash, attempts_used")
            .eq("user_id", user_id)
            .eq("exam_id", exam_id)
            .limit(1)
            .execute()
            .data
        )
    )
    if not ok:
        return None, False
    return ((rows[0] if rows else None), True)


def gate_status(supabase: Any, user_id: str, exam_id: str) -> str | None:
    """'completed' | 'skipped' | None. Only 'completed' authorises priors.

    Returns None on a read failure too — the planner's prior-consumption path
    treats "unknown gate" as not-completed (fail closed: no priors).
    """
    gate, ok = read_gate(supabase, user_id, exam_id)
    return gate.get("status") if (ok and gate) else None


def has_existing_plan(supabase: Any, user_id: str, exam_id: str) -> tuple[bool, bool]:
    """Return ``(exists, ok)`` — whether the user already has any plan for this exam.

    Used to grandfather existing users: the calibration gate is a
    pre-first-plan interstitial, so a user who already has a plan for the exam
    is never retroactively blocked from regenerating it. Matches the canonical
    ``exam_id`` column AND the legacy free-text ``target_exam`` column, the
    latter against BOTH the exam UUID and the exam slug (legacy rows store a
    slug like ``"ssc-cgl"`` with a NULL ``exam_id``, so a UUID-only comparison
    would miss them and wrongly gate a real existing user).
    """
    exam_rows, ok = _read(
        lambda: (
            supabase.table("exams")
            .select("slug")
            .eq("id", exam_id)
            .limit(1)
            .execute()
            .data
        )
    )
    if not ok:
        return False, False
    slug = exam_rows[0].get("slug") if exam_rows else None

    plan_rows, ok = _read(
        lambda: (
            supabase.table("study_plans")
            .select("id, exam_id, target_exam")
            .eq("user_id", user_id)
            .limit(200)
            .execute()
            .data
        )
    )
    if not ok:
        return False, False
    targets = {str(exam_id)}
    if slug:
        targets.add(str(slug))
    for r in (plan_rows or []):
        if str(r.get("exam_id") or "") in targets or str(r.get("target_exam") or "") in targets:
            return True, True
    return False, True


def evaluate_calibration(supabase: Any, user_id: str, exam_id: str) -> dict:
    """Health-aware single source of truth for the gate.

    Returns a dict::

        {
          "check_failed": bool,          # a read failed → caller must fail closed
          "required": bool | None,       # True=must calibrate, False=unlocked, None when check_failed
          "status": "completed" | "skipped" | None,
          "required_subjects": [ {subject_id, subject_name} ],
          "needs_update": bool,
          "required_subject_set_hash": str | None,
        }

    ``required`` is False when: the required set is empty (nothing to
    calibrate), the gate is completed/skipped, OR the user already has a plan
    for the exam (existing-user grandfather). On ANY read failure ``check_failed``
    is True and ``required`` is None — never silently unlocked.
    """
    unknown = {
        "check_failed": True,
        "required": None,
        "status": None,
        "required_subjects": [],
        "needs_update": False,
        "required_subject_set_hash": None,
    }

    subjects, ok = resolve_required_subjects(supabase, exam_id, user_id)
    if not ok:
        return unknown
    cur_hash = required_subject_set_hash([s["subject_id"] for s in subjects])
    if not subjects:
        return {
            "check_failed": False,
            "required": False,
            "status": "completed",
            "required_subjects": [],
            "needs_update": False,
            "required_subject_set_hash": cur_hash,
        }

    gate, ok = read_gate(supabase, user_id, exam_id)
    if not ok:
        return unknown
    status = gate.get("status") if gate else None
    if status in ("completed", "skipped"):
        needs_update = bool(gate and gate.get("required_subject_set_hash") != cur_hash)
        return {
            "check_failed": False,
            "required": False,
            "status": status,
            "required_subjects": subjects,
            "needs_update": needs_update,
            "required_subject_set_hash": cur_hash,
        }

    existing, ok = has_existing_plan(supabase, user_id, exam_id)
    if not ok:
        return unknown
    return {
        "check_failed": False,
        "required": not existing,
        "status": status,
        "required_subjects": subjects,
        "needs_update": False,
        "required_subject_set_hash": cur_hash,
    }


def calibration_required(supabase: Any, user_id: str, exam_id: str) -> bool:
    """True when the user must calibrate before a FIRST plan can be generated.

    Raises ``CalibrationUnavailable`` when the state cannot be determined
    (a read failed) so callers fail closed instead of unlocking generation.
    """
    result = evaluate_calibration(supabase, user_id, exam_id)
    if result["check_failed"]:
        raise CalibrationUnavailable()
    return bool(result["required"])


def calibration_required_payload(exam_id: str | None) -> dict[str, Any]:
    """Stable shape returned by plan entrypoints when calibration is required."""
    return {
        "generated": False,
        "calibration_required": True,
        "reason": "calibration_required",
        "exam_id": exam_id,
    }
