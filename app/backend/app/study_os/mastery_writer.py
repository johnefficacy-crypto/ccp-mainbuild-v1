from __future__ import annotations

import logging
import os
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Literal
from uuid import uuid4

from app.study_os.mastery_engine import derive_from_analytics
from app.study_os.mastery_engine.schemas import (
    AttemptQuestionAnalytics,
    AttemptTopicAnalytics,
    DerivedAttemptAnalytics,
)

logger = logging.getLogger("career_copilot.study_os.mastery_writer")

FlagState = Literal["off", "shadow", "live"]

# Per-attempt mastery delta cap, in mastery units (0..1). 0.15 unit == 15 db.
_CAP_UNIT = Decimal("0.15")

# Trust weight applied to mastery deltas by source. Manual self-reports carry
# ~30% of the influence of a platform-scored attempt at the same accuracy, so
# they can still nudge mastery without dominating it. See
# docs/architecture/mock_trust_model.md for the rationale.
TRUST_WEIGHT: dict[str, Decimal] = {
    "platform_verified": Decimal("1.0"),
    "admin_verified": Decimal("1.0"),
    "self_reported": Decimal("0.3"),
}


def _weighted_delta(base_delta: Decimal, trust_level: str) -> Decimal:
    """Scale a capped mastery delta by the source trust weight."""
    return base_delta * TRUST_WEIGHT.get(trust_level, Decimal("0.3"))


# Correction CATEGORY now comes from the shared correction_policy (§7) on the
# CorrectionTaskDraft itself — MasteryWriter is a pure persistence adapter and
# carries NO classification logic. It only persists draft.category verbatim.

# Observable signal for a recoverable deferral (mock_tests compat row not yet
# present). Tests read this; ops can scrape it. Not a silent skip.
correction_metrics: Counter = Counter()


class MasteryWriter:
    def __init__(self, supabase: Any, flag_state: FlagState) -> None:
        self.supabase = supabase
        self.flag_state = flag_state

    async def process_attempt(self, attempt_id: str) -> None:
        # Ordering decision (PR-fix-3): implementation B — the writer derives
        # mastery inline from the persisted raw attempt data (mock_attempts +
        # mock_attempt_responses, whose is_correct is set at submit time), NOT
        # from mock_attempt_summary. It therefore does not depend on PR4's
        # derivation having run, and a failed/pending derivation cannot silently
        # suppress mastery writes. See docs/study_os/mock_submit_flow.md.
        if self.flag_state == "off":
            return

        analytics = self._load_analytics(attempt_id)
        if analytics is None:
            return

        trust_level = self._load_trust_level(attempt_id)
        current_mastery = self._load_current_mastery(analytics.user_id)
        existing_error_topics = self._load_existing_error_topics(analytics.user_id)
        result = derive_from_analytics(
            analytics, current_mastery, existing_error_topics, source_trust=trust_level
        )

        self._write_shadow(attempt_id, result.mastery_deltas, self.flag_state, trust_level)

        if self.flag_state == "live":
            self._apply_mastery(attempt_id, result.mastery_deltas, trust_level)
            self._apply_error_patterns(result.error_signals)
            self._draft_correction_tasks(attempt_id, result.correction_task_drafts)

    def redraft_corrections(self, attempt_id: str) -> None:
        """Recovery entry point: re-derive and (idempotently) draft corrections
        for ``attempt_id`` AFTER its mock_tests compat row exists.

        Called by the mock_tests-retry sweeper hook so a transient missing-row
        miss in :meth:`_draft_correction_tasks` is recovered, not lost. Only
        meaningful at FF=live (corrections are a live-only write); shadow/off
        return without touching anything. The best-effort read-before-insert
        guard makes this SERIAL-retry safe (re-running after the inline
        submit-time pass inserts each correction once) — it is NOT concurrency-
        safe without a DB unique constraint (separate follow-up).
        """
        if self.flag_state != "live":
            return
        analytics = self._load_analytics(attempt_id)
        if analytics is None:
            return
        trust_level = self._load_trust_level(attempt_id)
        current_mastery = self._load_current_mastery(analytics.user_id)
        existing_error_topics = self._load_existing_error_topics(analytics.user_id)
        result = derive_from_analytics(
            analytics, current_mastery, existing_error_topics, source_trust=trust_level
        )
        self._draft_correction_tasks(attempt_id, result.correction_task_drafts)

    def _load_analytics(self, attempt_id: str) -> DerivedAttemptAnalytics | None:
        attempt_rows = self.supabase.table("mock_attempts").select("id,user_id").eq("id", attempt_id).limit(1).execute().data or []
        if not attempt_rows:
            return None
        attempt = attempt_rows[0]
        responses = self.supabase.table("mock_attempt_responses").select("question_id,is_correct,time_spent_sec,question_snapshot").eq("attempt_id", attempt_id).execute().data or []
        by_topic: dict[tuple[str, str | None], dict[str, Any]] = {}
        questions: list[AttemptQuestionAnalytics] = []
        for r in responses:
            q = r.get("question_snapshot") or {}
            topic_id = q.get("topic_id")
            if not topic_id:
                continue
            microtopic_id = q.get("microtopic_id")
            is_correct = bool(r.get("is_correct"))
            questions.append(
                AttemptQuestionAnalytics(
                    question_id=r.get("question_id"),
                    topic_id=topic_id,
                    microtopic_id=microtopic_id,
                    is_correct=is_correct,
                    difficulty=q.get("difficulty") or "medium",
                    source_type=q.get("source_type") or "authored",
                    pyq_year=q.get("pyq_year"),
                    expected_time_sec=q.get("expected_time_sec"),
                    actual_time_sec=r.get("time_spent_sec"),
                    error_type=r.get("error_type"),
                    confidence=Decimal(str(q.get("confidence") or "0.5")),
                )
            )
            key = (topic_id, microtopic_id)
            stats = by_topic.setdefault(key, {"attempted": 0, "correct": 0})
            stats["attempted"] += 1
            stats["correct"] += 1 if is_correct else 0

        topics = [
            AttemptTopicAnalytics(
                topic_id=t,
                microtopic_id=mt,
                attempted=s["attempted"],
                correct=s["correct"],
                accuracy_pct=(Decimal(s["correct"]) * Decimal("100") / Decimal(s["attempted"])) if s["attempted"] else Decimal("0"),
            )
            for (t, mt), s in by_topic.items()
        ]
        return DerivedAttemptAnalytics(attempt_id=attempt_id, user_id=attempt["user_id"], questions=questions, topics=topics)

    def _load_trust_level(self, attempt_id: str) -> str:
        rows = (
            self.supabase.table("mock_tests")
            .select("trust_level")
            .eq("mock_attempt_id", attempt_id)
            .limit(1)
            .execute()
            .data or []
        )
        # Platform attempts always go through mock_attempts, so default to
        # platform_verified if the mock_tests row isn't written yet.
        return (rows[0].get("trust_level") or "platform_verified") if rows else "platform_verified"

    def _load_current_mastery(self, user_id: str) -> dict[str, Decimal]:
        rows = self.supabase.table("user_topic_mastery").select("topic_id,mastery_score").eq("user_id", user_id).execute().data or []
        out: dict[str, Decimal] = {}
        for r in rows:
            if r.get("topic_id"):
                out[r["topic_id"]] = Decimal(str(r.get("mastery_score") or "50")) / Decimal("100")
        return out

    def _load_existing_error_topics(self, user_id: str) -> set[str]:
        rows = self.supabase.table("user_topic_error_patterns").select("topic_id").eq("user_id", user_id).execute().data or []
        return {r.get("topic_id") for r in rows if r.get("topic_id")}

    def _write_shadow(self, attempt_id: str, deltas: list[Any], flag_state: FlagState, trust_level: str = "platform_verified") -> None:
        payload = []
        for d in deltas:
            unweighted_db = (d.capped_delta * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            weighted = _weighted_delta(d.capped_delta, trust_level)
            delta_db = (weighted * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            current_db = (d.current_mastery * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            would_be = min(Decimal("100"), max(Decimal("0"), current_db + delta_db))
            payload.append({
                "id": str(uuid4()),
                "attempt_id": attempt_id,
                "user_id": d.user_id,
                "topic_id": d.topic_id,
                "proposed_delta_unit": str(weighted),
                "proposed_delta_db": str(delta_db),
                "proposed_delta_db_unweighted": str(unweighted_db),
                "current_mastery_db": str(current_db),
                "would_be_mastery_db": str(would_be),
                "flag_state": flag_state,
                "trust_level": trust_level,
            })
        if payload:
            self.supabase.table("mock_mastery_shadow").insert(payload).execute()

    def _apply_mastery(self, attempt_id: str, deltas: list[Any], trust_level: str = "platform_verified") -> None:
        for d in deltas:
            # Cap (whiplash guard): bound one mock's swing to ±0.15 unit. PR5a
            # emits both delta_raw_unit and delta_capped_unit; we read the capped
            # field (``capped_delta``) and re-cap defensively so a bad upstream
            # value can never write more than ±15 db. This is a different
            # invariant from the [0,100] clamp the RPC applies (overflow guard).
            # Trust weight is applied after capping so a self-reported mock can
            # never exceed the cap even at weight=1.0.
            delta_unit = min(_CAP_UNIT, max(-_CAP_UNIT, Decimal(str(d.capped_delta))))
            delta_unit = _weighted_delta(delta_unit, trust_level)
            delta_db = (delta_unit * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            # Idempotent + atomic. The RPC skips when an audit row already exists
            # for (user, topic, attempt), and applies the clamp + mastery write +
            # audit insert in one transaction, so re-submission is a silent no-op
            # and partial failure can't desync mastery from its audit trail.
            self.supabase.rpc(
                "apply_mock_mastery_delta",
                {
                    "p_user_id": d.user_id,
                    "p_topic_id": d.topic_id,
                    "p_attempt_id": attempt_id,
                    "p_delta_db": float(delta_db),
                    "p_reason": "mock_submit",
                },
            ).execute()

    def _apply_error_patterns(self, signals: list[Any]) -> None:
        for s in signals:
            self.supabase.table("user_topic_error_patterns").upsert({
                "id": str(uuid4()), "user_id": s.user_id, "topic_id": s.topic_id, "microtopic_id": s.microtopic_id,
                "error_type": s.error_type, "error_count": s.count,
            }, on_conflict="user_id,topic_id,microtopic_id,error_type").execute()

    def _load_mock_test_id_for_attempt(self, attempt_id: str) -> str | None:
        """The mock_tests.id for this attempt's compat row, or None if not emitted
        yet. mock_correction_tasks.mock_test_id is a NOT NULL FK to mock_tests, so
        corrections cannot be drafted until that row exists."""
        rows = (
            self.supabase.table("mock_tests")
            .select("id")
            .eq("mock_attempt_id", attempt_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        return rows[0].get("id") if rows else None

    @staticmethod
    def _source_questions_from_evidence(draft: Any) -> list[str]:
        """The wrong/source question ids backing this draft (stored in the legacy
        ``source_questions`` jsonb column)."""
        return [str(q) for q in (draft.evidence.related_question_ids or [])]

    def _correction_exists(
        self, mock_test_id: str, user_id: str, category: str, topic: str | None
    ) -> bool:
        """Best-effort deduplication: a drafted correction with the same
        (mock_test_id, user_id, category, topic) already exists. mock_correction_
        tasks has no unique constraint for this use case, so this is a read-before-
        insert guard — SERIAL-retry safe but NOT concurrency-safe. Robust de-dup
        via a partial unique index is OUT OF SCOPE (separate follow-up)."""
        rows = (
            self.supabase.table("mock_correction_tasks")
            .select("id, topic")
            .eq("mock_test_id", mock_test_id)
            .eq("user_id", user_id)
            .eq("category", category)
            .eq("state", "drafted")
            .execute()
            .data
            or []
        )
        return any((r.get("topic") or None) == (topic or None) for r in rows)

    def _draft_correction_tasks(self, attempt_id: str, drafts: list[Any]) -> None:
        """Persist corrections into the EXISTING mock_correction_tasks schema (063).

        Pure persistence adapter: the CATEGORY is taken verbatim from
        ``draft.category`` (computed by the shared correction_policy from error
        evidence) — NO classification happens here. Writes only columns that
        exist (mock_test_id, user_id, category, title, topic, source_questions,
        state); never the mastery-engine-shaped task_type/priority/evidence_json/
        duration_minutes/source_attempt_id, and never mock_test_id=None.
        Serial-retry idempotent via best-effort read-before-insert dedup (NOT
        concurrency-safe without a DB unique constraint — separate follow-up).
        When the mock_tests compat row is not present yet, corrections are
        deferred with an observable signal and recovered by the mock_tests-retry
        sweeper hook.
        """
        if not drafts:
            return
        mock_test_id = self._load_mock_test_id_for_attempt(attempt_id)
        if not mock_test_id:
            # RECOVERABLE, NOT silent: the mock_tests emit is best-effort with a
            # sweeper retry; redraft_corrections re-runs once the row lands.
            correction_metrics["correction_deferred_missing_mock_test"] += 1
            logger.warning(
                "correction draft deferred: no mock_tests compat row yet for "
                "attempt=%s (recoverable via mock_tests_retry sweeper)",
                attempt_id,
            )
            return

        from app.study_os.correction_policy import CANONICAL_CATEGORIES, correction_title

        payload: list[dict] = []
        seen: set[tuple[str, str | None]] = set()
        for d in drafts:
            category = d.category
            if category not in CANONICAL_CATEGORIES:
                # Policy could not classify this draft — skip rather than guess
                # (no blind default; never violate the 063 CHECK).
                continue
            topic = d.topic_id
            key = (category, topic)
            if key in seen:
                continue  # de-dup within this batch
            if self._correction_exists(mock_test_id, d.user_id, category, topic):
                continue  # de-dup against already-drafted corrections (idempotent)
            seen.add(key)
            payload.append({
                "mock_test_id": mock_test_id,
                "user_id": d.user_id,
                "category": category,
                "title": correction_title(category),
                "topic": topic,
                "source_questions": self._source_questions_from_evidence(d),
                "state": "drafted",
            })
        if payload:
            self.supabase.table("mock_correction_tasks").insert(payload).execute()


def get_mastery_write_flag() -> FlagState:
    raw = (os.getenv("FF_MOCK_MASTERY_WRITES") or "off").strip().lower()
    return raw if raw in {"off", "shadow", "live"} else "off"
