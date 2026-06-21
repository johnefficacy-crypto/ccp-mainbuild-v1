from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ClassificationReadiness:
    response_count: int
    classification_count: int
    unique_classification_count: int
    missing_question_ids: list[str] = field(default_factory=list)
    duplicate_question_ids: list[str] = field(default_factory=list)
    ready: bool = False


def check_classification_readiness(supabase: Any, attempt_id: str) -> ClassificationReadiness:
    """Return a readiness snapshot for attempt_id without writing anything.

    ready=True iff every response question_id has exactly one classification row.
    A zero-response attempt has no missing/duplicate entries and is therefore
    ready (mastery produces empty deltas, which is correct).
    """
    response_rows = (
        supabase.table("mock_attempt_responses")
        .select("question_id")
        .eq("attempt_id", attempt_id)
        .execute()
        .data
        or []
    )
    response_qids: set[str] = {r["question_id"] for r in response_rows if r.get("question_id")}

    classification_rows = (
        supabase.table("mock_attempt_response_classification")
        .select("question_id")
        .eq("attempt_id", attempt_id)
        .execute()
        .data
        or []
    )
    classified_qids: list[str] = [
        c["question_id"] for c in classification_rows if c.get("question_id")
    ]
    counts = Counter(classified_qids)
    classified_qid_set = set(classified_qids)

    missing_question_ids = sorted(response_qids - classified_qid_set)
    duplicate_question_ids = sorted(qid for qid, n in counts.items() if n > 1)

    ready = not missing_question_ids and not duplicate_question_ids

    return ClassificationReadiness(
        response_count=len(response_qids),
        classification_count=len(classified_qids),
        unique_classification_count=len(classified_qid_set),
        missing_question_ids=missing_question_ids,
        duplicate_question_ids=duplicate_question_ids,
        ready=ready,
    )
