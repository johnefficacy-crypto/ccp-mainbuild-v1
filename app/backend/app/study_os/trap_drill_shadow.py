"""PYQ v2 PR-8 — direct-PYQ (trap-drill) → shadow mastery/revision.

Observes the *would-be* mastery delta and revision routing for a trap-drill
session and records it in ``trap_drill_mastery_shadow`` (migration 232). This is
strictly a SHADOW observation:

  * it writes ONLY the separate ``trap_drill_mastery_shadow`` table — never
    ``user_topic_mastery`` (live), never ``mock_mastery_shadow`` (the P8-measured
    mock output), never ``user_topic_error_patterns`` or ``revision_items``;
  * it is gated behind its own flag ``FF_TRAP_DRILL_MASTERY_SHADOW`` (default off),
    independent of ``FF_MOCK_MASTERY_WRITES``, and the table's ``flag_state`` is
    CHECK-pinned to ``'shadow'`` — so it is structurally impossible for this path
    to become a live mastery write;
  * it does NOT modify any of the 36 fingerprinted mastery-validation files
    (P8 T0 baseline unaffected): it only *calls* the pure ``derive_from_analytics``
    and *reads* the PR-7 evidence adapter.

Wiring this into the actual live mastery writer (and a first-class revision
contract) is future work behind the P8/P9 gates.
"""
from __future__ import annotations

import logging
import os
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.study_os.attempt_evidence import (
    SOURCE_TRAP_DRILL,
    load_trap_drill_evidence,
    trust_level_for_source,
)
from app.study_os.mastery_engine import derive_from_analytics

logger = logging.getLogger("career_copilot.study_os.trap_drill_shadow")

_FLAG_ENV = "FF_TRAP_DRILL_MASTERY_SHADOW"

# Mirrors mastery_writer.TRUST_WEIGHT / _weighted_delta (replicated so this module
# never edits or hard-depends on the fingerprinted mastery_writer.py).
_TRUST_WEIGHT: dict[str, Decimal] = {
    "platform_verified": Decimal("1.0"),
    "admin_verified": Decimal("1.0"),
    "self_reported": Decimal("0.3"),
}
# ±0.15 unit whiplash cap, same invariant mastery_writer applies on the live path.
_CAP_UNIT = Decimal("0.15")
# revision bands align with mastery.py _mastery_band (low <45, high >=75).
_LOW_BAND = Decimal("45")
_HIGH_BAND = Decimal("75")


def is_enabled() -> bool:
    """True only when FF_TRAP_DRILL_MASTERY_SHADOW is explicitly 'shadow'.

    There is no 'live' value: any other value (incl. 'live', 'on', unset) leaves
    the path off, so trap-drill evidence can never reach a live write.
    """
    return (os.getenv(_FLAG_ENV) or "off").strip().lower() == "shadow"


def _weighted(base_delta: Decimal, trust_level: str) -> Decimal:
    return base_delta * _TRUST_WEIGHT.get(trust_level, Decimal("0.3"))


def _revision_bucket(would_be_mastery_db: Decimal) -> str:
    """P3 routing from the would-be mastery band. Trap-drill is application/trap
    evidence, so a mid-band topic routes to ``practice``; a low band signals a
    concept gap (``relearn``); an adequate band is retention-only (``review``)."""
    if would_be_mastery_db < _LOW_BAND:
        return "relearn"
    if would_be_mastery_db >= _HIGH_BAND:
        return "review"
    return "practice"


def _load_current_mastery(sb: Any, user_id: str) -> dict[str, Decimal] | None:
    """Read-only current per-topic mastery (unit scale 0–1) for the user, so the
    would-be delta is faithful.

    Returns ``None`` on a read *failure* (distinguishable from ``{}`` for a
    successful empty read). The caller fails the shadow write closed on ``None``:
    deriving against an invented baseline would write contaminated shadow
    analytics, which for a validation-only table is worse than writing nothing.
    """
    try:
        rows = (
            sb.table("user_topic_mastery")
            .select("topic_id,mastery_score")
            .eq("user_id", user_id)
            .execute()
            .data
            or []
        )
    except Exception as exc:  # noqa: BLE001 - fail closed (return None), never raise
        logger.warning("trap_drill_shadow: current mastery read failed: %s", exc)
        return None
    out: dict[str, Decimal] = {}
    for r in rows:
        score = r.get("mastery_score")
        if r.get("topic_id") is None or score is None:
            continue
        # user_topic_mastery.mastery_score is db-scale 0–100; the engine works in
        # unit scale 0–1.
        out[r["topic_id"]] = (Decimal(str(score)) / Decimal("100"))
    return out


def record_trap_drill_shadow(
    sb: Any, *, user_id: str, exam_id: str, drill_seed: str | int | None
) -> dict[str, Any]:
    """Derive and shadow-record the would-be mastery/revision for one drill session.

    Best-effort and gated: returns a small status dict and never raises — a shadow
    failure must never break trap-drill logging. Returns ``{outcome, rows}``:
      * ``disabled``     — flag off (default).
      * ``no_evidence``  — no eligible drill rows for this session.
      * ``written``      — N shadow rows upserted.
    """
    if not is_enabled():
        return {"outcome": "disabled", "rows": 0}
    if drill_seed is None:
        return {"outcome": "no_evidence", "rows": 0}
    try:
        analytics = load_trap_drill_evidence(sb, user_id=user_id, exam_id=exam_id, drill_seed=drill_seed)
    except Exception as exc:  # noqa: BLE001
        logger.warning("trap_drill_shadow: evidence load failed: %s", exc)
        return {"outcome": "no_evidence", "rows": 0}
    if analytics is None or not analytics.topics:
        return {"outcome": "no_evidence", "rows": 0}

    trust_level = trust_level_for_source(SOURCE_TRAP_DRILL)
    current = _load_current_mastery(sb, user_id)
    if current is None:
        # Fail closed: without the learner's real current mastery, the would-be
        # numbers would be computed off an invented baseline — contaminating the
        # shadow analysis. Skip the write entirely (drill response stays fine).
        return {"outcome": "read_failed", "rows": 0}
    result = derive_from_analytics(analytics, current, source_trust=trust_level)

    payload: list[dict[str, Any]] = []
    for d in result.mastery_deltas:
        capped = min(_CAP_UNIT, max(-_CAP_UNIT, Decimal(str(d.capped_delta))))
        unweighted_db = (capped * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        weighted = _weighted(capped, trust_level)
        delta_db = (weighted * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        current_db = (Decimal(str(d.current_mastery)) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        would_be = min(Decimal("100"), max(Decimal("0"), current_db + delta_db))
        payload.append({
            "synthetic_attempt_id": str(analytics.attempt_id),
            "user_id": d.user_id,
            "exam_id": exam_id,
            "drill_seed": str(drill_seed),
            "topic_id": d.topic_id,
            "proposed_delta_unit": str(weighted),
            "proposed_delta_db": str(delta_db),
            "proposed_delta_db_unweighted": str(unweighted_db),
            "current_mastery_db": str(current_db),
            "would_be_mastery_db": str(would_be),
            "revision_bucket": _revision_bucket(would_be),
            "source": "trap_drill",
            "flag_state": "shadow",
            "trust_level": trust_level,
        })

    if not payload:
        return {"outcome": "no_evidence", "rows": 0}
    try:
        sb.table("trap_drill_mastery_shadow").upsert(
            payload,
            on_conflict="synthetic_attempt_id,topic_id",
            ignore_duplicates=True,
        ).execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning("trap_drill_shadow: shadow upsert failed: %s", exc)
        return {"outcome": "no_evidence", "rows": 0}
    return {"outcome": "written", "rows": len(payload)}
