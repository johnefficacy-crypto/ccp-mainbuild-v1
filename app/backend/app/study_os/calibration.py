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
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)

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


def _safe(call, default):
    try:
        return call()
    except Exception as exc:  # noqa: BLE001
        logger.warning("calibration read failed: %s", exc)
        return default


def resolve_required_subjects(supabase: Any, exam_id: str, user_id: str) -> list[dict]:
    """Subjects whose locked coverage still lacks validated mastery for the user.

    A subject is REQUIRED only when at least one of its locked-coverage topics
    has no ``user_topic_mastery`` row for this user (i.e. there is no validated
    mastery to supersede a self-reported prior). Subjects whose every locked
    topic is already validated are dropped. Returns distinct subjects sorted by
    ``subject_id`` for deterministic ordering and hashing. Returns ``[]`` on any
    read failure (callers treat an empty required set as "nothing to calibrate").
    """
    cov_rows = _safe(
        lambda: (
            supabase.table("exam_topic_coverage")
            .select("topic_id")
            .eq("exam_id", exam_id)
            .eq("reviewer_status", "locked")
            .limit(5000)
            .execute()
            .data
        ),
        default=[],
    ) or []
    topic_ids = list({r["topic_id"] for r in cov_rows if r.get("topic_id")})
    if not topic_ids:
        return []

    topic_rows = _safe(
        lambda: (
            supabase.table("topics")
            .select("id, subject_id")
            .in_("id", topic_ids)
            .limit(5000)
            .execute()
            .data
        ),
        default=[],
    ) or []
    subject_topics: dict[str, set[str]] = {}
    for t in topic_rows:
        sid = t.get("subject_id")
        tid = t.get("id")
        if sid is None or tid is None:
            continue
        subject_topics.setdefault(str(sid), set()).add(str(tid))
    if not subject_topics:
        return []

    mastery_rows = _safe(
        lambda: (
            supabase.table("user_topic_mastery")
            .select("topic_id")
            .eq("user_id", user_id)
            .limit(5000)
            .execute()
            .data
        ),
        default=[],
    ) or []
    validated_topic_ids = {str(m["topic_id"]) for m in mastery_rows if m.get("topic_id")}

    required_ids = [
        sid
        for sid, tids in subject_topics.items()
        if any(tid not in validated_topic_ids for tid in tids)
    ]
    if not required_ids:
        return []

    subj_rows = _safe(
        lambda: (
            supabase.table("subjects")
            .select("id, name")
            .in_("id", required_ids)
            .limit(5000)
            .execute()
            .data
        ),
        default=[],
    ) or []
    names_by_id = {str(s["id"]): s.get("name") for s in subj_rows if s.get("id") is not None}

    return [
        {"subject_id": sid, "subject_name": names_by_id.get(sid)}
        for sid in sorted(required_ids)
    ]


def read_gate(supabase: Any, user_id: str, exam_id: str) -> dict | None:
    """Return the ``user_exam_calibration`` row for (user, exam), or None.

    Returns None on read failure too — callers treat "unknown gate" as
    not-completed (priors are not consumed) and not-explicitly-gated.
    """
    rows = _safe(
        lambda: (
            supabase.table("user_exam_calibration")
            .select("status, required_subject_set_hash, attempts_used")
            .eq("user_id", user_id)
            .eq("exam_id", exam_id)
            .limit(1)
            .execute()
            .data
        ),
        default=None,
    )
    if not rows:
        return None
    return rows[0]


def gate_status(supabase: Any, user_id: str, exam_id: str) -> str | None:
    """'completed' | 'skipped' | None. Only 'completed' authorises priors."""
    gate = read_gate(supabase, user_id, exam_id)
    return gate.get("status") if gate else None


def has_existing_plan(supabase: Any, user_id: str, exam_id: str) -> bool:
    """Whether the user already has any plan (any status) for this exam.

    Used to grandfather existing users: the calibration gate is a
    pre-first-plan interstitial, so a user who already has a plan for the exam
    is never retroactively blocked from regenerating it. Matches either the
    ``exam_id`` column or the legacy ``target_exam`` column.
    """
    rows = _safe(
        lambda: (
            supabase.table("study_plans")
            .select("id, exam_id, target_exam")
            .eq("user_id", user_id)
            .limit(200)
            .execute()
            .data
        ),
        default=[],
    ) or []
    target = str(exam_id)
    for r in rows:
        if str(r.get("exam_id") or "") == target or str(r.get("target_exam") or "") == target:
            return True
    return False


def calibration_required(supabase: Any, user_id: str, exam_id: str) -> bool:
    """True when the user must calibrate before a FIRST plan can be generated.

    NOT required when any of these hold:
      * the required subject set is empty (nothing to calibrate);
      * the gate record status is already 'completed' or 'skipped';
      * the user already has a plan for this exam (grandfathered — the gate is a
        pre-first-plan interstitial, not a retroactive block on existing users).

    Fails OPEN (returns False) on infrastructure errors: a soft onboarding gate
    must never wedge plan generation on a transient read failure, and the
    frontend still gates interactively.
    """
    try:
        required = resolve_required_subjects(supabase, exam_id, user_id)
        if not required:
            return False
        if gate_status(supabase, user_id, exam_id) in ("completed", "skipped"):
            return False
        if has_existing_plan(supabase, user_id, exam_id):
            return False
        return True
    except Exception:  # noqa: BLE001
        logger.exception("calibration_required check failed for %s/%s", user_id, exam_id)
        return False


def calibration_required_payload(exam_id: str | None) -> dict[str, Any]:
    """Stable shape returned by plan entrypoints when calibration is required."""
    return {
        "generated": False,
        "calibration_required": True,
        "reason": "calibration_required",
        "exam_id": exam_id,
    }
