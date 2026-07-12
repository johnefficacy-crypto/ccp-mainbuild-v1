"""Quant performance signals — sibling to mastery, SHADOW only (GQR-Q8).

Derives an independent accuracy + time-ratio signal from attempt analytics
(§3.3). This is NOT a mastery tier and NEVER writes ``user_topic_mastery``: the
existing 5% over-time penalty in ``mastery_engine/mastery_delta.py`` is left
untouched: any reconciliation of the two writers is a separate governed decision.

Thresholds are shadow defaults — centrally VERSIONED (``policy_version``) and
covered by deterministic tests, to be recalibrated from real attempt
distributions before any activation (GQR-Q9, blocked on the Lane A gate).
"""
from __future__ import annotations

import hashlib
import logging
import statistics
from typing import Any, Iterable

logger = logging.getLogger("career_copilot.study_os.quant_signals")

_SIGNALS = "quant_performance_signals"

# Versioned shadow policy. NOT product truth — recalibrated from real data later.
QUANT_SIGNAL_POLICY: dict[str, Any] = {
    "version": "qsp_v1",
    "min_samples": 5,          # below this → insufficient_evidence
    "concept_accuracy": 0.40,  # accuracy < this → concept_gap
    "application_accuracy": 0.70,  # accuracy < this → application_gap
    "speed_time_ratio": 1.30,  # median ratio ≥ this (with decent accuracy) → speed_gap
    "calc_time_ratio": 1.80,   # median ratio ≥ this (with decent accuracy) → calculation_gap
    "outlier_time_ratio": 6.0,  # per-item ratio above this is an extreme dwell → excluded
    "confidence_target": 20,   # sample count at which confidence saturates to 1.0
}

# Recommendation labels (§3.3).
SIGNAL_TYPES = (
    "insufficient_evidence", "concept_gap", "application_gap",
    "speed_gap", "calculation_gap", "stable",
)


def _get(row: Any, key: str, default: Any = None) -> Any:
    if isinstance(row, dict):
        return row.get(key, default)
    return getattr(row, key, default)


def _usable_ratio(row: Any, *, outlier_cap: float) -> float | None:
    """Return actual/expected time ratio for a row, or None if it must be
    excluded: unanswered, missing/zero expected time, zero-duration response, or
    an extreme dwell outlier (§3.3 exclusions)."""
    if not _get(row, "attempted", True):
        return None
    expected = _get(row, "expected_time_sec")
    actual = _get(row, "actual_time_sec")
    if not expected or expected <= 0:
        return None
    if not actual or actual <= 0:
        return None
    ratio = float(actual) / float(expected)
    if ratio > outlier_cap:
        return None
    return ratio


def _label(*, sample_count: int, accuracy: float, median_ratio: float | None, policy: dict) -> str:
    if sample_count < policy["min_samples"]:
        return "insufficient_evidence"
    if accuracy < policy["concept_accuracy"]:
        return "concept_gap"
    if accuracy < policy["application_accuracy"]:
        return "application_gap"
    # Accuracy is acceptable — distinguish thinking-speed vs arithmetic-speed.
    if median_ratio is not None:
        if median_ratio >= policy["calc_time_ratio"]:
            return "calculation_gap"
        if median_ratio >= policy["speed_time_ratio"]:
            return "speed_gap"
    return "stable"


def _fingerprint(topic_id, microtopic_id, ratios, correct, total, policy_version) -> str:
    payload = f"{policy_version}|{topic_id}|{microtopic_id}|{correct}/{total}|" + \
        ",".join(f"{r:.4f}" for r in sorted(ratios))
    return hashlib.sha256(payload.encode()).hexdigest()


def derive_signals(
    analytics: Iterable[Any],
    *,
    policy: dict | None = None,
) -> list[dict[str, Any]]:
    """Group attempt-analytics rows by (topic_id, microtopic_id) and derive one
    shadow signal per group. Rows failing the §3.3 exclusions are dropped from
    the time computation; a group with only-excluded rows still yields an
    ``insufficient_evidence`` signal so the absence is explicit.
    """
    policy = policy or QUANT_SIGNAL_POLICY
    outlier_cap = policy["outlier_time_ratio"]

    groups: dict[tuple, dict[str, Any]] = {}
    for row in analytics:
        topic_id = _get(row, "topic_id")
        if not topic_id:
            continue
        micro = _get(row, "microtopic_id")
        key = (topic_id, micro)
        g = groups.setdefault(key, {"correct": 0, "answered": 0, "ratios": []})
        if _get(row, "attempted", True):
            g["answered"] += 1
            if _get(row, "is_correct"):
                g["correct"] += 1
        ratio = _usable_ratio(row, outlier_cap=outlier_cap)
        if ratio is not None:
            g["ratios"].append(ratio)

    out: list[dict[str, Any]] = []
    for (topic_id, micro), g in groups.items():
        answered = g["answered"]
        ratios = g["ratios"]
        accuracy = (g["correct"] / answered) if answered else 0.0
        median_ratio = statistics.median(ratios) if ratios else None
        p75_ratio = (
            statistics.quantiles(ratios, n=4)[2] if len(ratios) >= 2
            else (ratios[0] if ratios else None)
        )
        # Confidence saturates toward 1.0 as the answered sample grows.
        confidence = min(1.0, answered / policy["confidence_target"]) if answered else 0.0
        signal_type = _label(
            sample_count=answered, accuracy=accuracy, median_ratio=median_ratio, policy=policy,
        )
        out.append({
            "topic_id": topic_id,
            "microtopic_id": micro,
            "signal_type": signal_type,
            "sample_count": answered,
            "accuracy_pct": round(accuracy * 100, 2),
            "median_time_ratio": round(median_ratio, 4) if median_ratio is not None else None,
            "p75_time_ratio": round(p75_ratio, 4) if p75_ratio is not None else None,
            "confidence": round(confidence, 4),
            "policy_version": policy["version"],
            "input_fingerprint": _fingerprint(
                topic_id, micro, ratios, g["correct"], answered, policy["version"]
            ),
        })
    return out


def persist_signals(
    supabase: Any,
    *,
    user_id: str,
    signals: list[dict[str, Any]],
    exam_id: str | None = None,
    now_iso: str | None = None,
) -> int:
    """SHADOW-write derived signals to ``quant_performance_signals``.

    Upserts on (user_id, exam_id, topic_id, microtopic_id, policy_version) so a
    recompute overwrites the current signal rather than accumulating rows. NEVER
    touches ``user_topic_mastery`` — this is a sibling shadow signal only.
    Returns the number of signals written.
    """
    if not signals:
        return 0
    from datetime import datetime, timezone
    computed_at = now_iso or datetime.now(timezone.utc).isoformat()
    payload = [
        {
            "user_id": user_id,
            "exam_id": exam_id,
            "topic_id": s["topic_id"],
            "microtopic_id": s.get("microtopic_id"),
            "signal_type": s["signal_type"],
            "sample_count": s["sample_count"],
            "accuracy_pct": s["accuracy_pct"],
            "median_time_ratio": s["median_time_ratio"],
            "p75_time_ratio": s["p75_time_ratio"],
            "confidence": s["confidence"],
            "policy_version": s["policy_version"],
            "computed_at": computed_at,
            "input_fingerprint": s.get("input_fingerprint"),
        }
        for s in signals
    ]
    supabase.table(_SIGNALS).upsert(
        payload,
        on_conflict="user_id,exam_id,topic_id,microtopic_id,policy_version",
    ).execute()  # safe-write-ok: shadow signal; upsert is idempotent, no retry job
    return len(payload)
