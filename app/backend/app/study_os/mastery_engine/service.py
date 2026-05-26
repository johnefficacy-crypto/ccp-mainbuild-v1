from __future__ import annotations

from decimal import Decimal
from typing import Any

from .correction_tasks import derive_correction_tasks
from .error_patterns import derive_error_pattern_signals
from .mastery_delta import derive_mastery_deltas
from .schemas import DerivationResult, DerivedAttemptAnalytics


def derive_from_analytics(
    analytics: DerivedAttemptAnalytics,
    current_mastery_by_topic: dict[str, Decimal] | None = None,
    existing_error_topics: set[str] | None = None,
) -> DerivationResult:
    if not analytics.questions and not analytics.topics:
        return DerivationResult()
    mastery_deltas = derive_mastery_deltas(analytics, current_mastery_by_topic or {})
    error_signals = derive_error_pattern_signals(analytics)
    correction_tasks = derive_correction_tasks(analytics, error_signals, existing_error_topics or set())
    return DerivationResult(
        mastery_deltas=mastery_deltas,
        error_signals=error_signals,
        correction_task_drafts=correction_tasks,
    )
