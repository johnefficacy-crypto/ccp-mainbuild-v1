from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal

from .schemas import DerivedAttemptAnalytics, MasteryDelta

D = Decimal


def expected_accuracy_for_mastery(mastery: Decimal) -> Decimal:
    if mastery < D("0.3"):
        return D("0.40")
    if mastery < D("0.6"):
        return D("0.60")
    if mastery < D("0.9"):
        return D("0.75")
    return D("0.85")


def _difficulty_weight(difficulty: str) -> Decimal:
    return {"hard": D("1.5"), "medium": D("1.0"), "easy": D("0.5")}.get(difficulty, D("1.0"))


def _source_weight(source_type: str) -> Decimal:
    return {"pyq": D("1.2"), "authored": D("1.0"), "current_event": D("0.8")}.get(source_type, D("1.0"))


def _pyq_recency_weight(pyq_year: int | None, now_year: int = 2026) -> Decimal:
    if pyq_year is None:
        return D("1.0")
    age = max(0, now_year - pyq_year)
    if age <= 5:
        return D("1.0")
    decay = D("0.95") ** D(str(age - 5))
    return max(D("0.5"), decay)


def derive_mastery_deltas(
    analytics: DerivedAttemptAnalytics,
    current_mastery_by_topic: dict[str, Decimal],
) -> list[MasteryDelta]:
    topic_weighted = defaultdict(Decimal)
    topic_correct_weighted = defaultdict(Decimal)
    topic_attempted = defaultdict(int)

    for q in analytics.questions:
        # Only answered questions move mastery. Unanswered/marked rows are kept
        # in analytics.questions so the correction path still sees them (e.g.
        # time_pressure_unattempted → speed correction), but they must not
        # contribute to weighting, accuracy, attempted counts, or deltas here.
        # The loader is the single source of truth for ``attempted``; never
        # re-derive answered-ness from is_correct or any proxy.
        if not q.attempted:
            continue
        weight = _difficulty_weight(q.difficulty) * _source_weight(q.source_type)
        if q.source_type == "pyq":
            weight *= _pyq_recency_weight(q.pyq_year)
        if q.expected_time_sec and q.actual_time_sec and q.actual_time_sec > q.expected_time_sec:
            weight *= D("0.95")
        topic_weighted[q.topic_id] += weight
        topic_correct_weighted[q.topic_id] += weight if q.is_correct else D("0")
        topic_attempted[q.topic_id] += 1

    out: list[MasteryDelta] = []
    for topic_id in sorted(topic_weighted.keys()):
        attempted = topic_attempted[topic_id]
        if attempted <= 0:
            continue
        current = current_mastery_by_topic.get(topic_id, D("0.5"))
        expected = expected_accuracy_for_mastery(current)
        observed = topic_correct_weighted[topic_id] / topic_weighted[topic_id]
        weight_volume = min(D("1.0"), topic_weighted[topic_id] / D("5.0"))
        raw = (observed - expected) * weight_volume
        capped = min(D("0.15"), max(D("-0.15"), raw))
        out.append(
            MasteryDelta(
                user_id=analytics.user_id,
                topic_id=topic_id,
                current_mastery=current,
                expected_accuracy=expected,
                observed_accuracy=observed,
                raw_delta=raw,
                capped_delta=capped,
                attempted=attempted,
            )
        )
    return out
