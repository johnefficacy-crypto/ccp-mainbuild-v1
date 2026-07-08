"""Unified attempt-evidence adapter (PYQ v2 PR-7).

Normalizes every learner attempt source into the single canonical evidence
contract — ``mastery_engine.schemas.DerivedAttemptAnalytics`` — so mastery /
planner / persona can consume one shape regardless of where the attempt came
from:

  * mock / generated / PYQ-practice attempts → ``mock_attempts`` +
    ``mock_attempt_responses`` (frozen ``question_snapshot``; already the mastery
    path — PYQ practice attempts from PR-5/6 slice B funnel through here too).
  * direct-PYQ trap-drill attempts → ``user_trap_drill_attempts`` (live
    ``pyq_questions`` lineage; previously orphaned from mastery / planner).

This module is READ-ONLY: it does not write mastery, error patterns, or
correction tasks. Wiring trap-drill (and any future SRS/flashcard) evidence into
the feature-gated, shadow-first mastery writer is PR-8. PR-7 only guarantees a
uniform evidence shape + a per-source trust tag so PR-8 can weight it correctly.

The mock loader here is the single normalization path for mock attempts:
``MasteryWriter._load_analytics`` delegates to ``load_mock_attempt_evidence`` so
there is exactly one place that turns a mock attempt into evidence.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from app.study_os.mastery_engine.schemas import (
    AttemptQuestionAnalytics,
    AttemptTopicAnalytics,
    DerivedAttemptAnalytics,
)

# ── attempt sources ──────────────────────────────────────────────────────────
SOURCE_MOCK = "mock"
SOURCE_TRAP_DRILL = "trap_drill"

# Trust tag per source, using the mastery TRUST_WEIGHT vocabulary
# (platform_verified | admin_verified | self_reported). NOT applied to any write
# in this module — carried so PR-8 weights evidence correctly. Mock attempts have
# a per-attempt trust (mock_tests.trust_level); this is the default when absent.
TRUST_BY_SOURCE: dict[str, str] = {
    SOURCE_MOCK: "platform_verified",
    # a trap drill is platform-adjudicated (server computes is_correct) over
    # verified PYQ questions, so it carries platform trust.
    SOURCE_TRAP_DRILL: "platform_verified",
}

# Deterministic namespace so one drill session (a drill_seed) maps to a stable
# synthetic attempt id (DerivedAttemptAnalytics.attempt_id is a UUID; trap drills
# have no single attempt row).
_TRAP_DRILL_NS = uuid.UUID("6f3d1e2a-0000-4000-8000-000000000007")


def _aggregate_topics(questions: list[AttemptQuestionAnalytics]) -> list[AttemptTopicAnalytics]:
    """Topic rollup identical to the mock mastery loader: every question's topic
    is registered (so an unanswered-only topic still reaches the correction path),
    but attempted/correct — hence accuracy — count answered rows only."""
    by_topic: dict[tuple[str, str | None], dict[str, int]] = {}
    for q in questions:
        stats = by_topic.setdefault((q.topic_id, q.microtopic_id), {"attempted": 0, "correct": 0})
        if q.attempted:
            stats["attempted"] += 1
            stats["correct"] += 1 if q.is_correct else 0
    return [
        AttemptTopicAnalytics(
            topic_id=t,
            microtopic_id=mt,
            attempted=s["attempted"],
            correct=s["correct"],
            accuracy_pct=(Decimal(s["correct"]) * Decimal("100") / Decimal(s["attempted"]))
            if s["attempted"]
            else Decimal("0"),
        )
        for (t, mt), s in by_topic.items()
    ]


def load_mock_attempt_evidence(sb: Any, attempt_id: str) -> DerivedAttemptAnalytics | None:
    """Normalize a mock / generated / PYQ-practice attempt into the evidence
    contract. Reads the frozen ``question_snapshot`` and the authoritative
    ``mock_attempt_response_classification`` error types. Returns None if the
    attempt does not exist.

    This is the exact logic MasteryWriter used inline; it now lives here so mock
    and direct-PYQ attempts share one normalization surface.
    """
    attempt_rows = (
        sb.table("mock_attempts").select("id,user_id").eq("id", attempt_id).limit(1).execute().data or []
    )
    if not attempt_rows:
        return None
    attempt = attempt_rows[0]
    responses = (
        sb.table("mock_attempt_responses")
        .select("question_id,selected_option_id,is_correct,time_spent_sec,question_snapshot")
        .eq("attempt_id", attempt_id)
        .execute()
        .data
        or []
    )
    # error_type is authoritative ONLY from mock_attempt_response_classification
    # (keyed (attempt_id, question_id)); a missing classification stays None —
    # never an invented category.
    classification_rows = (
        sb.table("mock_attempt_response_classification")
        .select("question_id,error_type")
        .eq("attempt_id", attempt_id)
        .execute()
        .data
        or []
    )
    error_type_by_qid: dict[str, str | None] = {
        c.get("question_id"): c.get("error_type") for c in classification_rows
    }

    questions: list[AttemptQuestionAnalytics] = []
    for r in responses:
        q = r.get("question_snapshot") or {}
        topic_id = q.get("topic_id")
        if not topic_id:
            continue
        questions.append(
            AttemptQuestionAnalytics(
                question_id=r.get("question_id"),
                topic_id=topic_id,
                microtopic_id=q.get("microtopic_id"),
                is_correct=bool(r.get("is_correct")),
                # answered iff selected_option_id is not null.
                attempted=r.get("selected_option_id") is not None,
                difficulty=q.get("difficulty") or "medium",
                source_type=q.get("source_type") or "authored",
                pyq_year=q.get("pyq_year"),
                expected_time_sec=q.get("expected_time_sec"),
                actual_time_sec=r.get("time_spent_sec"),
                error_type=error_type_by_qid.get(r.get("question_id")),
                confidence=Decimal(str(q.get("confidence") or "0.5")),
            )
        )
    return DerivedAttemptAnalytics(
        attempt_id=attempt_id,
        user_id=attempt["user_id"],
        questions=questions,
        topics=_aggregate_topics(questions),
    )


def load_trap_drill_evidence(
    sb: Any, *, user_id: str, exam_id: str, drill_seed: str | int
) -> DerivedAttemptAnalytics | None:
    """Normalize one trap-drill session (a ``drill_seed``) into the evidence
    contract. Unlike mock attempts, trap drills store no frozen snapshot — they
    reference live ``pyq_questions``, so difficulty / PYQ-year are joined from the
    bank. ``source_type='pyq'`` (drills run over verified PYQs), ``attempted=True``
    (a logged drill row is always an answered question), and ``error_type`` is
    None (drills are not run through the response classifier).

    Returns None if the session has no rows. A synthetic, deterministic UUID
    stands in for the (non-existent) single attempt id.
    """
    rows = (
        sb.table("user_trap_drill_attempts")
        .select("question_id,topic_id,is_correct")
        .eq("user_id", user_id)
        .eq("exam_id", exam_id)
        .eq("drill_seed", str(drill_seed))
        .execute()
        .data
        or []
    )
    if not rows:
        return None

    qids = sorted({r["question_id"] for r in rows if r.get("question_id")})
    q_meta: dict[str, dict] = {}
    if qids:
        for qr in (
            sb.table("pyq_questions")
            .select("id,observed_difficulty,pyq_paper_id")
            .in_("id", qids)
            .execute()
            .data
            or []
        ):
            q_meta[qr["id"]] = qr
    paper_ids = sorted({m.get("pyq_paper_id") for m in q_meta.values() if m.get("pyq_paper_id")})
    year_by_paper: dict[str, int | None] = {}
    if paper_ids:
        for pr in (
            sb.table("pyq_papers").select("id,year").in_("id", paper_ids).execute().data or []
        ):
            year_by_paper[pr["id"]] = pr.get("year")

    questions: list[AttemptQuestionAnalytics] = []
    for r in rows:
        topic_id = r.get("topic_id")
        if not topic_id:
            continue
        meta = q_meta.get(r.get("question_id"), {})
        questions.append(
            AttemptQuestionAnalytics(
                question_id=r.get("question_id"),
                topic_id=topic_id,
                microtopic_id=None,
                is_correct=bool(r.get("is_correct")),
                attempted=True,
                difficulty=meta.get("observed_difficulty") or "medium",
                source_type="pyq",
                pyq_year=year_by_paper.get(meta.get("pyq_paper_id")),
                expected_time_sec=None,
                actual_time_sec=None,
                error_type=None,
                confidence=Decimal("0.5"),
            )
        )
    synthetic_id = uuid.uuid5(_TRAP_DRILL_NS, f"{user_id}:{exam_id}:{drill_seed}")
    return DerivedAttemptAnalytics(
        attempt_id=synthetic_id,
        user_id=user_id,
        questions=questions,
        topics=_aggregate_topics(questions),
    )


def load_attempt_evidence(sb: Any, *, source: str, **kwargs: Any) -> DerivedAttemptAnalytics | None:
    """Unified entry point: normalize an attempt from any source into
    ``DerivedAttemptAnalytics``.

    * ``source=SOURCE_MOCK`` → requires ``attempt_id``.
    * ``source=SOURCE_TRAP_DRILL`` → requires ``user_id``, ``exam_id``, ``drill_seed``.
    """
    if source == SOURCE_MOCK:
        return load_mock_attempt_evidence(sb, kwargs["attempt_id"])
    if source == SOURCE_TRAP_DRILL:
        return load_trap_drill_evidence(
            sb, user_id=kwargs["user_id"], exam_id=kwargs["exam_id"], drill_seed=kwargs["drill_seed"]
        )
    raise ValueError(f"unknown attempt evidence source: {source!r}")


def trust_level_for_source(source: str) -> str:
    """The mastery TRUST_WEIGHT tag for a source (default platform_verified)."""
    return TRUST_BY_SOURCE.get(source, "platform_verified")
