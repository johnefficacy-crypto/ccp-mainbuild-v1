from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal

from app.study_os.correction_policy import (
    CorrectionPolicyInput,
    normalize_error_type,
    select_categories,
)

from .schemas import CorrectionEvidence, CorrectionTaskDraft, DerivedAttemptAnalytics, ErrorPatternSignal


def _priority(error_count: int, has_hard: bool) -> int:
    val = 5 - min(error_count, 3) - (1 if has_hard else 0)
    return max(1, min(5, val))


def _action_task_type(category: str, wrong_pyq: bool) -> str:
    """ACTION/execution style for a correction — drives estimated_minutes only.

    Derived AFTER category selection; it never changes the canonical category.
    ``wrong_pyq`` upgrades a memory_gap revision to PYQ revision but does not
    override the evidence-derived category.
    """
    if category == "concept_gap":
        return "concept_review"
    if category == "option_trap":
        return "trap_review"
    if category == "memory_gap":
        return "pyq_revision" if wrong_pyq else "practice_drill"
    return "practice_drill"  # careless, speed_issue


def derive_correction_tasks(
    analytics: DerivedAttemptAnalytics,
    error_signals: list[ErrorPatternSignal],
    existing_error_topics: set[str],
    source_trust: str = "platform_verified",
) -> list[CorrectionTaskDraft]:
    """Generated correction drafts — one per canonical category per topic.

    Category set + emission are delegated to the shared correction_policy (§7),
    fed from the ACTUAL question-level error evidence (``analytics.questions``)
    rather than the narrower ``error_signals`` write-vocabulary — so memory/
    speed/misread evidence survives to the policy. ``error_signals`` is still
    accepted for signature compatibility but is no longer the category source.
    """
    by_topic = {t.topic_id: t for t in analytics.topics}
    q_by_topic: dict[str, list] = defaultdict(list)
    for q in analytics.questions:
        q_by_topic[q.topic_id].append(q)

    drafts: list[CorrectionTaskDraft] = []
    for topic_id in sorted(set(list(by_topic.keys()) + list(existing_error_topics))):
        topic = by_topic.get(topic_id)
        attempted = topic.attempted if topic else 0
        accuracy = topic.accuracy_pct if topic else Decimal("100")
        questions = q_by_topic.get(topic_id, [])

        # RAW error counts from the question-level analytics (every recognized
        # alias survives — not filtered to the mastery error-write vocabulary).
        raw_counts: Counter = Counter()
        for q in questions:
            if q.error_type and normalize_error_type(q.error_type) is not None:
                raw_counts[q.error_type] += 1

        related_ids = sorted({q.question_id for q in questions if (not q.is_correct) or q.error_type})
        wrong_pyq = any((not q.is_correct and q.source_type == "pyq") for q in questions)

        policy_input = CorrectionPolicyInput(
            topic=topic_id,
            error_counts=dict(raw_counts),
            attempted=attempted,
            accuracy_pct=accuracy,
            prior_error=topic_id in existing_error_topics,
            wrong_pyq=wrong_pyq,
            source_question_ids=tuple(related_ids),
            evidence_mode="question_level",
        )
        categories = select_categories(policy_input)
        if not categories:
            continue  # no usable evidence — never a blind default

        has_hard = any(q.difficulty == "hard" for q in questions)
        err_count = sum(raw_counts.values())
        priority = _priority(err_count, has_hard)
        is_platform = source_trust == "platform_verified"

        # One CorrectionTaskDraft per canonical category for this topic.
        for category in categories:
            task_type = _action_task_type(category, wrong_pyq)
            reason = f"{category} ({task_type}) — {attempted} attempted at {accuracy}% accuracy"
            evidence = CorrectionEvidence(
                accuracy_pct=accuracy,
                error_types=sorted(raw_counts.keys()),
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
