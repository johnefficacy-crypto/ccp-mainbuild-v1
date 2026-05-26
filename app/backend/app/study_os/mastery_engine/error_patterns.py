from __future__ import annotations

from decimal import Decimal

from .schemas import DerivedAttemptAnalytics, ErrorPatternSignal

TRACKED = {"option_trap", "calc_error", "concept_gap"}


def derive_error_pattern_signals(analytics: DerivedAttemptAnalytics) -> list[ErrorPatternSignal]:
    signals: list[ErrorPatternSignal] = []
    for q in analytics.questions:
        if q.error_type not in TRACKED:
            continue
        signals.append(
            ErrorPatternSignal(
                user_id=analytics.user_id,
                topic_id=q.topic_id,
                microtopic_id=q.microtopic_id,
                error_type=q.error_type,
                count=1,
                evidence_question_ids=[q.question_id],
                signal_strength=max(Decimal("0"), min(Decimal("1"), q.confidence)),
            )
        )
    return signals
