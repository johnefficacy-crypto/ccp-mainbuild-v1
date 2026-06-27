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


def resolve_target_exam_checked(supabase: Any, user_id: str) -> tuple[dict | None, bool]:
    """Health-aware target-exam resolution → ``(exam_row_or_None, ok)``.

    Mirrors ``planner._resolve_target_exam`` but reports read health so callers
    can fail closed: a transient ``profiles`` / ``aspirant_preferences`` read
    failure is NOT mistaken for "the user has no target exam" (which would let the
    calibration gate return "proceed" and an uncalibrated first plan through).
    ``ok`` is False only when a read needed to determine the target failed;
    ``(None, True)`` means the user genuinely has no target exam.
    """
    from app.exam_intelligence.lookup import resolve_exam_by_id, resolve_exam_by_slug

    profile, ok = _read(
        lambda: (
            supabase.table("profiles")
            .select("target_exam")
            .eq("id", user_id)
            .limit(1)
            .execute()
            .data
        )
    )
    if not ok:
        return None, False
    target = (profile[0] if profile else {}).get("target_exam")
    if not target:
        prefs, ok = _read(
            lambda: (
                supabase.table("aspirant_preferences")
                .select("target_exams")
                .eq("user_id", user_id)
                .limit(1)
                .execute()
                .data
            )
        )
        if not ok:
            return None, False
        exams = (prefs[0] if prefs else {}).get("target_exams") or []
        if isinstance(exams, list) and exams:
            target = exams[0]
    if not target:
        return None, True  # genuinely no target exam
    candidate = str(target)
    try:
        if len(candidate) == 36 and candidate.count("-") == 4:
            exam = resolve_exam_by_id(supabase, candidate)
            if exam:
                return exam, True
        return resolve_exam_by_slug(supabase, candidate), True
    except Exception as exc:  # noqa: BLE001
        logger.warning("calibration target-exam lookup failed: %s", exc)
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
    plan_rows = plan_rows or []
    target = str(exam_id)
    # Canonical match FIRST — no ``exams`` lookup needed, so a transient exams
    # read can never block a plan whose canonical UUID already matches.
    for r in plan_rows:
        if str(r.get("exam_id") or "") == target:
            return True, True
    # Legacy free-text match — resolve the slug only now, and only if needed.
    exam_rows, ok = _read(
        lambda: (
            supabase.table("exams").select("slug").eq("id", exam_id).limit(1).execute().data
        )
    )
    if not ok:
        return False, False
    slug = exam_rows[0].get("slug") if exam_rows else None
    if slug:
        for r in plan_rows:
            if str(r.get("target_exam") or "") == str(slug):
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

    ``required`` is False when: the gate is completed/skipped, the user already
    has a plan for the exam (existing-user grandfather), OR the required set is
    empty (nothing to calibrate). On a read failure that would be needed to make
    the decision, ``check_failed`` is True and ``required`` is None — never
    silently unlocked.

    POSITIVE unlock evidence (completed/skipped gate, existing plan) is evaluated
    FIRST, so an unrelated coverage / topics / mastery / subjects outage can never
    re-block a user who is already definitively unlocked (the OR contract). Only a
    user with no positive unlock evidence needs a healthy required-set read.
    ``attempts_used`` is returned from the gate row so callers need not re-read it.
    """
    unknown = {
        "check_failed": True,
        "required": None,
        "status": None,
        "required_subjects": [],
        "needs_update": False,
        "required_subject_set_hash": None,
        "attempts_used": None,
    }

    gate, gate_ok = read_gate(supabase, user_id, exam_id)

    # 1. A completed/skipped gate is sufficient — coverage health is irrelevant.
    if gate_ok and gate and gate.get("status") in ("completed", "skipped"):
        subjects, subj_ok = resolve_required_subjects(supabase, exam_id, user_id)
        cur_hash = (
            required_subject_set_hash([s["subject_id"] for s in subjects])
            if subj_ok else None
        )
        # needs_update is best-effort: failure to recompute the hash must NOT
        # revoke plan access for an already-unlocked user.
        needs_update = bool(
            subj_ok and cur_hash is not None
            and gate.get("required_subject_set_hash") != cur_hash
        )
        return {
            "check_failed": False,
            "required": False,
            "status": gate.get("status"),
            "required_subjects": subjects if subj_ok else [],
            "needs_update": needs_update,
            "required_subject_set_hash": cur_hash,
            "attempts_used": gate.get("attempts_used"),
        }

    # 2. An existing plan (canonical or legacy) grandfathers the user. The
    #    required set is resolved best-effort (for the edit affordance); a
    #    coverage outage yields [] but never revokes the unlock.
    existing, exist_ok = has_existing_plan(supabase, user_id, exam_id)
    if exist_ok and existing:
        subjects, subj_ok = resolve_required_subjects(supabase, exam_id, user_id)
        cur_hash = (
            required_subject_set_hash([s["subject_id"] for s in subjects])
            if subj_ok else None
        )
        return {
            "check_failed": False,
            "required": False,
            "status": gate.get("status") if gate else None,
            "required_subjects": subjects if subj_ok else [],
            "needs_update": False,
            "required_subject_set_hash": cur_hash,
            "attempts_used": gate.get("attempts_used") if gate else None,
        }

    # 3. No positive unlock evidence → a HEALTHY required-set read is required to
    #    decide; an unhealthy read here fails closed.
    subjects, subj_ok = resolve_required_subjects(supabase, exam_id, user_id)
    if not subj_ok:
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
            "attempts_used": None,
        }
    # Required set non-empty → to assert required=True we must be SURE there is no
    # gate and no existing plan; if either read failed we cannot be sure.
    if not gate_ok or not exist_ok:
        return unknown
    return {
        "check_failed": False,
        "required": True,
        "status": gate.get("status") if gate else None,
        "required_subjects": subjects,
        "needs_update": False,
        "required_subject_set_hash": cur_hash,
        "attempts_used": None,
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
