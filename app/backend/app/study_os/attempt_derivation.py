"""Read-only derivation helpers for mastery preview.

All functions are zero-write. No insert/update/upsert/delete/rpc calls.

Functions:
  load_attempt_inputs          — wider SELECT with 4-bucket response state
  load_persisted_shadow_decisions — ordered shadow rows + duplicate detection
  replay_from_persisted_baseline  — exact Decimal replay, no mutable mastery
  derive_attempt_evidence_corrections — deterministic, no mutable user state
  derive_current_state_preview    — explicitly labeled mutable path
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.study_os.attempt_classification_readiness import (
    ClassificationReadiness,
    check_classification_readiness,
)
from app.study_os.mastery_engine.mastery_delta import derive_mastery_deltas
from app.study_os.mastery_engine.schemas import (
    AttemptQuestionAnalytics,
    AttemptTopicAnalytics,
    DerivedAttemptAnalytics,
)

_TRUST_WEIGHT: dict[str, Decimal] = {
    "platform_verified": Decimal("1.0"),
    "admin_verified": Decimal("1.0"),
    "self_reported": Decimal("0.3"),
}


def _weighted_delta(base_delta: Decimal, trust_level: str) -> Decimal:
    return base_delta * _TRUST_WEIGHT.get(trust_level, Decimal("0.3"))


@dataclass
class ResponseStateCounts:
    selected: int = 0
    marked_unanswered: int = 0
    visited_unanswered: int = 0
    untouched: int = 0


@dataclass
class AttemptInputs:
    analytics: DerivedAttemptAnalytics
    response_counts: ResponseStateCounts
    classification_coverage: ClassificationReadiness
    classification_counts: dict[str, int]
    classification_rows: list[dict]
    trust_level: str
    user_id: str


@dataclass
class ShadowDecisions:
    rows: list[dict] = field(default_factory=list)
    duplicate_keys: list[str] = field(default_factory=list)


@dataclass
class ReplayResult:
    status: str  # MATCH | MISMATCH | NO_BASELINE
    sample_count: int
    exact_match_count: int
    missing: list[dict] = field(default_factory=list)
    extra: list[dict] = field(default_factory=list)
    mismatches: list[dict] = field(default_factory=list)


def load_attempt_inputs(supabase: Any, attempt_id: str) -> AttemptInputs | None:
    """Single wider SELECT from mock_attempt_responses; returns None if attempt absent."""
    attempt_rows = (
        supabase.table("mock_attempts")
        .select("id,user_id")
        .eq("id", attempt_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not attempt_rows:
        return None
    user_id: str = attempt_rows[0]["user_id"]

    responses = (
        supabase.table("mock_attempt_responses")
        .select(
            "question_id,selected_option_id,is_correct,time_spent_sec,"
            "question_snapshot,is_marked_for_review,is_visited"
        )
        .eq("attempt_id", attempt_id)
        .execute()
        .data
        or []
    )

    classification_rows = (
        supabase.table("mock_attempt_response_classification")
        .select("question_id,error_type")
        .eq("attempt_id", attempt_id)
        .execute()
        .data
        or []
    )

    # 4-bucket response state — mutually exclusive and exhaustive.
    response_counts = ResponseStateCounts()
    for r in responses:
        has_selected = r.get("selected_option_id") is not None
        is_marked = bool(r.get("is_marked_for_review"))
        is_visited_val = bool(r.get("is_visited"))

        if has_selected:
            response_counts.selected += 1
        elif is_marked:
            response_counts.marked_unanswered += 1
        elif is_visited_val:
            response_counts.visited_unanswered += 1
        else:
            response_counts.untouched += 1

    # classification_counts by error_type
    classification_counts: dict[str, int] = {}
    for c in classification_rows:
        et = c.get("error_type")
        if et:
            classification_counts[et] = classification_counts.get(et, 0) + 1

    # classification_coverage reuses the shared readiness checker
    classification_coverage = check_classification_readiness(supabase, attempt_id)

    # Build DerivedAttemptAnalytics (mirrors _load_analytics but uses the wider
    # response SELECT; error_type comes from classification table, not responses)
    error_type_by_qid: dict[str, str | None] = {
        c.get("question_id"): c.get("error_type") for c in classification_rows
    }
    by_topic: dict[tuple[str, str | None], dict[str, Any]] = {}
    questions: list[AttemptQuestionAnalytics] = []
    for r in responses:
        q = r.get("question_snapshot") or {}
        topic_id = q.get("topic_id")
        if not topic_id:
            continue
        microtopic_id = q.get("microtopic_id")
        is_correct = bool(r.get("is_correct"))
        attempted = r.get("selected_option_id") is not None
        questions.append(
            AttemptQuestionAnalytics(
                question_id=r.get("question_id"),
                topic_id=topic_id,
                microtopic_id=microtopic_id,
                is_correct=is_correct,
                attempted=attempted,
                difficulty=q.get("difficulty") or "medium",
                source_type=q.get("source_type") or "authored",
                pyq_year=q.get("pyq_year"),
                expected_time_sec=q.get("expected_time_sec"),
                actual_time_sec=r.get("time_spent_sec"),
                error_type=error_type_by_qid.get(r.get("question_id")),
                confidence=Decimal(str(q.get("confidence") or "0.5")),
            )
        )
        key = (topic_id, microtopic_id)
        stats = by_topic.setdefault(key, {"attempted": 0, "correct": 0})
        if attempted:
            stats["attempted"] += 1
            stats["correct"] += 1 if is_correct else 0

    topics = [
        AttemptTopicAnalytics(
            topic_id=t,
            microtopic_id=mt,
            attempted=s["attempted"],
            correct=s["correct"],
            accuracy_pct=(
                Decimal(s["correct"]) * Decimal("100") / Decimal(s["attempted"])
                if s["attempted"]
                else Decimal("0")
            ),
        )
        for (t, mt), s in by_topic.items()
    ]
    analytics = DerivedAttemptAnalytics(
        attempt_id=attempt_id,
        user_id=user_id,
        questions=questions,
        topics=topics,
    )

    # trust_level from mock_tests compat row
    mock_test_rows = (
        supabase.table("mock_tests")
        .select("trust_level")
        .eq("mock_attempt_id", attempt_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    trust_level = (
        (mock_test_rows[0].get("trust_level") or "platform_verified")
        if mock_test_rows
        else "platform_verified"
    )

    return AttemptInputs(
        analytics=analytics,
        response_counts=response_counts,
        classification_coverage=classification_coverage,
        classification_counts=classification_counts,
        classification_rows=classification_rows,
        trust_level=trust_level,
        user_id=user_id,
    )


def load_persisted_shadow_decisions(supabase: Any, attempt_id: str) -> ShadowDecisions:
    """Read frozen shadow write decisions ordered by topic_id.

    duplicate_keys is defensive — the DB unique constraint from migration 180 on
    (attempt_id, topic_id, flag_state) makes duplicates structurally impossible,
    but we detect and surface them if they appear.
    """
    rows = (
        supabase.table("mock_mastery_shadow")
        .select(
            "topic_id,proposed_delta_db,proposed_delta_db_unweighted,"
            "current_mastery_db,would_be_mastery_db,trust_level,flag_state,decided_at"
        )
        .eq("attempt_id", attempt_id)
        .order("topic_id")
        .execute()
        .data
        or []
    )

    counts: Counter = Counter(r.get("topic_id") or "" for r in rows)
    duplicate_keys = sorted(tid for tid, n in counts.items() if n > 1 and tid)

    return ShadowDecisions(rows=rows, duplicate_keys=duplicate_keys)


def replay_from_persisted_baseline(
    persisted: ShadowDecisions,
    analytics: DerivedAttemptAnalytics,
    trust_level: str,
) -> ReplayResult:
    """Exact replay of shadow deltas using Decimal arithmetic throughout.

    Uses the frozen current_mastery_db from each shadow row as the baseline (NOT
    the mutable current mastery). This function never reads from the DB.

    status=NO_BASELINE  when no shadow rows exist (shadow was off at submit time)
    status=MATCH        when all deltas agree within 0.01 db tolerance and no
                        missing/extra topics
    status=MISMATCH     otherwise (diff > tolerance, missing topics, extra topics,
                        or trust_level changed between write and now)
    """
    if not persisted.rows:
        return ReplayResult(status="NO_BASELINE", sample_count=0, exact_match_count=0)

    shadow_by_topic: dict[str, dict] = {}
    for r in persisted.rows:
        tid = r.get("topic_id")
        if tid and tid not in shadow_by_topic:
            shadow_by_topic[tid] = r

    # Build frozen baseline dict from shadow rows (one entry per topic)
    frozen_baseline: dict[str, Decimal] = {
        tid: Decimal(str(row["current_mastery_db"])) / Decimal("100")
        for tid, row in shadow_by_topic.items()
        if row.get("current_mastery_db") is not None
    }

    # Re-derive deltas using frozen baselines (topics are independent in derive_mastery_deltas)
    replay_deltas = derive_mastery_deltas(analytics, frozen_baseline)
    replay_by_topic: dict[str, Any] = {d.topic_id: d for d in replay_deltas}

    shadow_topics = set(shadow_by_topic.keys())
    replay_topics = set(replay_by_topic.keys())

    # Topics in analytics but absent from shadow → missing
    missing = [{"topic_id": tid} for tid in sorted(replay_topics - shadow_topics)]
    # Topics in shadow but absent from analytics → extra
    extra = [{"topic_id": tid} for tid in sorted(shadow_topics - replay_topics)]

    mismatches: list[dict] = []
    exact_match_count = 0
    matched_topics = sorted(shadow_topics & replay_topics)

    for topic_id in matched_topics:
        shadow = shadow_by_topic[topic_id]
        replay_d = replay_by_topic[topic_id]

        # Apply same trust weight and quantize as _write_shadow
        weighted = _weighted_delta(replay_d.capped_delta, trust_level)
        expected_delta_db: Decimal = (weighted * Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        persisted_delta_db: Decimal = Decimal(str(shadow["proposed_delta_db"]))

        # Tolerance 0.01 db for DB numeric rounding
        if abs(expected_delta_db - persisted_delta_db) <= Decimal("0.01"):
            # Also flag trust_level divergence so ops can see it
            shadow_trust = shadow.get("trust_level") or "platform_verified"
            if shadow_trust != trust_level:
                mismatches.append({
                    "topic_id": topic_id,
                    "reason": "trust_level_changed",
                    "shadow_trust_level": shadow_trust,
                    "current_trust_level": trust_level,
                    "persisted_delta_db": str(persisted_delta_db),
                    "replay_delta_db": str(expected_delta_db),
                })
            else:
                exact_match_count += 1
        else:
            mismatches.append({
                "topic_id": topic_id,
                "persisted_delta_db": str(persisted_delta_db),
                "replay_delta_db": str(expected_delta_db),
                "diff_db": str(abs(expected_delta_db - persisted_delta_db)),
            })

    sample_count = len(matched_topics)
    status = "MATCH" if not mismatches and not missing and not extra else "MISMATCH"

    return ReplayResult(
        status=status,
        sample_count=sample_count,
        exact_match_count=exact_match_count,
        missing=missing,
        extra=extra,
        mismatches=mismatches,
    )


def derive_attempt_evidence_corrections(
    analytics: DerivedAttemptAnalytics,
    trust_level: str,
) -> list[dict]:
    """Deterministic correction derivation — no mutable user error state.

    Passes current_mastery={} and existing_error_topics=set() so output
    depends only on attempt evidence, never on the user's current DB state.
    """
    from app.study_os.correction_policy import CANONICAL_CATEGORIES, correction_title  # noqa: PLC0415
    from app.study_os.mastery_engine import derive_from_analytics  # noqa: PLC0415

    result = derive_from_analytics(
        analytics,
        current_mastery_by_topic={},
        existing_error_topics=set(),
        source_trust=trust_level,
    )

    topic_stats = {t.topic_id: t for t in analytics.topics}
    out: list[dict] = []
    for d in result.correction_task_drafts:
        category = d.category
        if category not in CANONICAL_CATEGORIES:
            continue
        topic = topic_stats.get(d.topic_id)
        out.append(
            {
                "topic_id": d.topic_id,
                "category": category,
                "title": correction_title(category),
                "source_question_ids": [
                    str(q) for q in (d.evidence.related_question_ids or [])
                ],
                "error_types": sorted(d.evidence.error_types or []),
                "attempted": topic.attempted if topic else 0,
                "accuracy_pct": float(topic.accuracy_pct) if topic else 0.0,
                "trust_level": trust_level,
            }
        )
    return out


def derive_current_state_preview(
    supabase: Any,
    analytics: DerivedAttemptAnalytics,
    trust_level: str,
) -> dict:
    """Mutable path — reads current DB mastery and error state.

    Explicitly labeled so callers understand this section reflects mutable
    user state and MUST NOT be used to determine replay PASS/FAIL.
    Zero writes.
    """
    from app.study_os.mastery_engine import derive_from_analytics  # noqa: PLC0415

    mastery_rows = (
        supabase.table("user_topic_mastery")
        .select("topic_id,mastery_score")
        .eq("user_id", analytics.user_id)
        .execute()
        .data
        or []
    )
    current_mastery: dict[str, Decimal] = {}
    for r in mastery_rows:
        if r.get("topic_id"):
            current_mastery[r["topic_id"]] = (
                Decimal(str(r.get("mastery_score") or "50")) / Decimal("100")
            )

    error_rows = (
        supabase.table("user_topic_error_patterns")
        .select("topic_id")
        .eq("user_id", analytics.user_id)
        .execute()
        .data
        or []
    )
    existing_error_topics: set[str] = {
        r.get("topic_id") for r in error_rows if r.get("topic_id")
    }

    result = derive_from_analytics(
        analytics, current_mastery, existing_error_topics, source_trust=trust_level
    )

    scale = Decimal("100")
    mastery_deltas = []
    for d in result.mastery_deltas:
        weighted = _weighted_delta(d.capped_delta, trust_level)
        mastery_deltas.append(
            {
                "topic_id": d.topic_id,
                "current_mastery_db": float(d.current_mastery * scale),
                "proposed_delta_db": float(weighted * scale),
                "would_be_mastery_db": float(
                    min(
                        Decimal("100"),
                        max(Decimal("0"), d.current_mastery * scale + weighted * scale),
                    )
                ),
            }
        )

    return {
        "note": (
            "Computed from current mastery state. "
            "May differ from persisted_shadow_decision if mastery has changed since the attempt."
        ),
        "trust_level": trust_level,
        "mastery_deltas": mastery_deltas,
    }
