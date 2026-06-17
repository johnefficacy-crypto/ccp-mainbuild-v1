from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal

from app.study_os.correction_policy import (
    CorrectionPolicyInput,
    select_category,
    should_emit,
)

from .schemas import CorrectionEvidence, CorrectionTaskDraft, DerivedAttemptAnalytics, ErrorPatternSignal


def _priority(error_count: int, has_hard: bool) -> int:
    val = 5 - min(error_count, 3) - (1 if has_hard else 0)
    return max(1, min(5, val))


def derive_correction_tasks(
    analytics: DerivedAttemptAnalytics,
    error_signals: list[ErrorPatternSignal],
    existing_error_topics: set[str],
    source_trust: str = "platform_verified",
) -> list[CorrectionTaskDraft]:
    by_topic = {t.topic_id: t for t in analytics.topics}
    q_by_topic: dict[str, list] = defaultdict(list)
    for q in analytics.questions:
        q_by_topic[q.topic_id].append(q)

    signal_counts: dict[str, Counter] = defaultdict(Counter)
    for s in error_signals:
        signal_counts[s.topic_id][s.error_type] += s.count

    drafts: list[CorrectionTaskDraft] = []
    for topic_id in sorted(set(list(by_topic.keys()) + list(existing_error_topics))):
        topic = by_topic.get(topic_id)
        attempted = topic.attempted if topic else 0
        accuracy = topic.accuracy_pct if topic else Decimal("100")
        counts = signal_counts.get(topic_id, Counter())
        questions = q_by_topic.get(topic_id, [])
        related_ids = sorted({q.question_id for q in questions if (not q.is_correct) or q.error_type})

        # CATEGORY + emit decision are delegated to the shared, source-neutral
        # correction policy (§7). Category is derived from normalized error
        # evidence — never from task_type.
        policy_input = CorrectionPolicyInput(
            topic=topic_id,
            error_counts=dict(counts),
            attempted=attempted,
            accuracy_pct=accuracy,
            prior_error=topic_id in existing_error_topics,
            wrong_pyq=any((not q.is_correct and q.source_type == "pyq") for q in questions),
            source_question_ids=tuple(related_ids),
            evidence_mode="question_level",
        )
        if not should_emit(policy_input):
            continue
        category = select_category(policy_input)
        if category is None:
            continue  # no usable evidence — never a blind default

        # task_type is ACTION STYLE only (drives estimated_minutes/execution); it
        # no longer determines the category.
        if policy_input.wrong_pyq:
            task_type = "pyq_revision"
        elif counts.get("concept_gap", 0) > counts.get("option_trap", 0):
            task_type = "concept_review"
        elif counts.get("option_trap", 0) > 0:
            task_type = "trap_review"
        else:
            task_type = "practice_drill"

        has_hard = any(q.difficulty == "hard" for q in questions)
        err_count = sum(counts.values())
        priority = _priority(err_count, has_hard)
        reason = f"{task_type} due to {attempted} attempted with {accuracy}% accuracy"
        is_platform = source_trust == "platform_verified"
        evidence = CorrectionEvidence(
            accuracy_pct=accuracy,
            error_types=sorted(list(counts.keys())),
            related_question_ids=related_ids,
            source_trust=source_trust,
            source_attempt_id=analytics.attempt_id if is_platform else None,
            canonical_topic_id=topic_id if is_platform else None,
            canonical_microtopic_id=(topic.microtopic_id if topic else None) if is_platform else None,
        )
        drafts.append(
            CorrectionTaskDraft(
                user_id=analytics.user_id,
                topic_id=topic_id,
                microtopic_id=(topic.microtopic_id if topic else None),
                category=category,
                task_type=task_type,
                priority=priority,
                reason=reason,
                evidence=evidence,
                estimated_minutes=30 if task_type in {"concept_review", "pyq_revision"} else 20,
                source_attempt_id=analytics.attempt_id,
            )
        )
    return drafts
