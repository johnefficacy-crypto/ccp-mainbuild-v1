from __future__ import annotations

import logging
import os
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Literal
from uuid import uuid4

from app.study_os.attempt_classification_readiness import check_classification_readiness
from app.study_os.mastery_engine import derive_from_analytics
from app.study_os.mastery_engine.schemas import (
    AttemptQuestionAnalytics,
    AttemptTopicAnalytics,
    DerivedAttemptAnalytics,
)

logger = logging.getLogger("career_copilot.study_os.mastery_writer")

FlagState = Literal["off", "shadow", "live"]


class MasteryClassificationNotReady(Exception):
    """Classifications are not yet fully populated for this attempt.

    Raised by process_attempt_sync when mock_attempt_response_classification
    is missing rows relative to mock_attempt_responses.  The caller is
    responsible for rescheduling the mastery retry job.
    """

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
        self.process_attempt_sync(attempt_id)

    def process_attempt_sync(self, attempt_id: str) -> None:
        # Ordering decision (PR-fix-3): implementation B — the writer derives
        # mastery inline from the persisted raw attempt data (mock_attempts +
        # mock_attempt_responses, whose is_correct is set at submit time), NOT
        # from mock_attempt_summary. It therefore does not depend on PR4's
        # derivation having run, and a failed/pending derivation cannot silently
        # suppress mastery writes. See docs/study_os/mock_submit_flow.md.
        if self.flag_state == "off":
            return

        readiness = check_classification_readiness(self.supabase, attempt_id)
        if not readiness.ready:
            # Classifications not yet populated — analytics_retry hasn't run yet
            # (or ran and failed partially).  Re-enqueue analytics so it can
            # classify all responses; then the D4 handoff will re-enqueue this
            # mastery job once analytics succeeds.
            from app.study_os.mock_engine import JOB_ANALYTICS_RETRY, schedule_job  # noqa: PLC0415
            schedule_job(self.supabase, JOB_ANALYTICS_RETRY, attempt_id)
            raise MasteryClassificationNotReady(
                f"classification_not_ready: missing={len(readiness.missing_question_ids)} "
                f"duplicate={len(readiness.duplicate_question_ids)}"
            )

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
        return without touching anything. Idempotent: the partial unique indexes
        from migration 181 and ON CONFLICT DO NOTHING inside the
        ensure_mock_correction_draft RPC ensure re-running inserts each
        correction at most once.
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
        responses = self.supabase.table("mock_attempt_responses").select("question_id,selected_option_id,is_correct,time_spent_sec,question_snapshot").eq("attempt_id", attempt_id).execute().data or []
        # error_type is authoritative ONLY from mock_attempt_response_classification
        # (keyed (attempt_id, question_id)) — mock_attempt_responses has no
        # error_type column, so the prior r.get("error_type") was always None.
        # Unknown/missing classification stays None: never an invented category.
        classification_rows = (
            self.supabase.table("mock_attempt_response_classification")
            .select("question_id,error_type")
            .eq("attempt_id", attempt_id)
            .execute()
            .data
            or []
        )
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
            # The user answered iff selected_option_id is not null. Only answered
            # rows move mastery; unanswered/marked rows are kept here (attempted=
            # False) so the correction path still sees them.
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
            # Always register the topic so unanswered-only topics still reach the
            # correction path, but count attempted/correct (hence accuracy_pct)
            # from answered rows only — an unanswered row must not masquerade as a
            # wrong answer and drag accuracy into a false concept_gap.
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
            # Idempotency boundary for submit replays and safe retries: preserve
            # the first accepted shadow decision for each attempt/topic/mode and
            # ignore later reruns instead of overwriting them. The backing unique
            # index is added in migration 180.
            self.supabase.table("mock_mastery_shadow").upsert(
                payload,
                on_conflict="attempt_id,topic_id,flag_state",
                ignore_duplicates=True,
            ).execute()

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
        # Schema: user_topic_error_patterns (migration 033).
        # Columns: id, user_id, topic_id, error_type, frequency_count, evidence, ...
        # microtopic_id and error_count are NOT in the schema; microtopic_id is
        # stored in evidence JSONB. No unique index covers (user_id, topic_id,
        # error_type) without exam_id/exam_phase_id, so each signal inserts a
        # new row; dedup/aggregation happens at read time.
        for s in signals:
            self.supabase.table("user_topic_error_patterns").insert({
                "id": str(uuid4()),
                "user_id": s.user_id,
                "topic_id": s.topic_id,
                "error_type": s.error_type,
                "frequency_count": s.count,
                "evidence": {
                    "microtopic_id": s.microtopic_id,
                    "signal_strength": float(s.signal_strength),
                    "evidence_question_ids": s.evidence_question_ids,
                },
            }).execute()

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

    def _draft_correction_tasks(self, attempt_id: str, drafts: list[Any]) -> None:
        """Persist corrections into the EXISTING mock_correction_tasks schema (063).

        Pure persistence adapter: the CATEGORY is taken verbatim from
        ``draft.category`` (computed by the shared correction_policy from error
        evidence) — NO classification happens here. Writes only columns that
        exist (mock_test_id, user_id, category, title, topic, source_questions,
        state); never the mastery-engine-shaped task_type/priority/evidence_json/
        duration_minutes/source_attempt_id, and never mock_test_id=None.
        All unique (category, topic) keys are persisted in ONE call to the
        ensure_mock_correction_drafts RPC — the full correction set is atomic:
        either all new rows land or none do. ON CONFLICT DO NOTHING handles
        concurrent races per key inside the same transaction.
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

        seen: set[tuple[str, str | None]] = set()
        payload: list[dict] = []
        user_id: str | None = None
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
            seen.add(key)
            user_id = d.user_id
            payload.append({
                "category": category,
                "topic": topic,
                "title": correction_title(category),
                "source_questions": self._source_questions_from_evidence(d),
            })

        if not payload:
            return

        # Single RPC call — all desired keys in one DB transaction.
        # Any error propagates; ON CONFLICT DO NOTHING handles existing rows per key.
        self.supabase.rpc(
            "ensure_mock_correction_drafts",
            {
                "p_mock_test_id": mock_test_id,
                "p_user_id": user_id,
                "p_drafts": payload,
            },
        ).execute()


    def _load_persisted_shadow_decisions(self, attempt_id: str) -> list[dict]:
        """Read the frozen shadow write decisions for this attempt from mock_mastery_shadow."""
        return (
            self.supabase.table("mock_mastery_shadow")
            .select(
                "topic_id,proposed_delta_db,proposed_delta_db_unweighted,"
                "current_mastery_db,would_be_mastery_db,trust_level,flag_state,decided_at"
            )
            .eq("attempt_id", attempt_id)
            .execute()
            .data
            or []
        )

    def derive_preview(self, attempt_id: str) -> dict | None:
        """Read-only preview — zero writes, no feature-flag dependency.

        Delegates to attempt_derivation module.  Returns None when the attempt
        is not found.  Output shape:
          response_counts            — 4-bucket response state (selected /
                                       marked_unanswered / visited_unanswered /
                                       untouched)
          classification_coverage    — readiness snapshot from classification table
          classification_counts      — error_type → count
          persisted_shadow_decision  — frozen shadow rows + duplicate detection
          replay_consistency         — EXACT Decimal replay vs persisted baseline;
                                       no mutable current mastery in this section
          attempt_evidence_corrections — deterministic corrections (no user state)
          current_state_preview      — mutable-baseline re-derivation, explicitly
                                       labeled; never used to determine PASS/FAIL
        """
        from app.study_os.attempt_derivation import (  # noqa: PLC0415
            derive_attempt_evidence_corrections,
            derive_current_state_preview,
            load_attempt_inputs,
            load_persisted_shadow_decisions,
            replay_from_persisted_baseline,
        )

        inputs = load_attempt_inputs(self.supabase, attempt_id)
        if inputs is None:
            return None

        persisted = load_persisted_shadow_decisions(self.supabase, attempt_id)
        replay = replay_from_persisted_baseline(persisted, inputs.analytics, inputs.trust_level)
        corrections = derive_attempt_evidence_corrections(inputs.analytics, inputs.trust_level)
        current_state = derive_current_state_preview(
            self.supabase, inputs.analytics, inputs.trust_level
        )

        return {
            "response_counts": {
                "selected": inputs.response_counts.selected,
                "marked_unanswered": inputs.response_counts.marked_unanswered,
                "visited_unanswered": inputs.response_counts.visited_unanswered,
                "untouched": inputs.response_counts.untouched,
            },
            "classification_coverage": {
                "response_count": inputs.classification_coverage.response_count,
                "classification_count": inputs.classification_coverage.classification_count,
                "missing_question_ids": inputs.classification_coverage.missing_question_ids,
                "duplicate_question_ids": inputs.classification_coverage.duplicate_question_ids,
                "ready": inputs.classification_coverage.ready,
            },
            "classification_counts": inputs.classification_counts,
            "persisted_shadow_decision": {
                "rows": persisted.rows,
                "duplicate_keys": persisted.duplicate_keys,
            },
            "replay_consistency": {
                "status": replay.status,
                "sample_count": replay.sample_count,
                "exact_match_count": replay.exact_match_count,
                "missing": replay.missing,
                "extra": replay.extra,
                "mismatches": replay.mismatches,
            },
            "attempt_evidence_corrections": corrections,
            "current_state_preview": current_state,
        }


def get_mastery_write_flag() -> FlagState:
    raw = (os.getenv("FF_MOCK_MASTERY_WRITES") or "off").strip().lower()
    return raw if raw in {"off", "shadow", "live"} else "off"


def resolve_effective_mastery_flag(requested_flag: FlagState, user_id: str) -> FlagState:
    """Resolve the global flag against the per-user live allowlist.

    Behaviour matrix:
      off    → off   (allowlist irrelevant)
      shadow → shadow (allowlist irrelevant)
      live + user in allowlist          → live
      live + user NOT in allowlist      → shadow   (fail-closed)
      live + allowlist empty/malformed  → shadow   (fail-closed)

    The allowlist is read from FF_MOCK_MASTERY_LIVE_USER_IDS as a
    comma-separated list of user UUIDs.  An empty or whitespace-only value
    is treated as "no users allowed" (fail-closed), so flipping the global
    FF to live with an empty allowlist produces shadow writes only.
    """
    if requested_flag != "live":
        return requested_flag

    raw_ids = os.getenv("FF_MOCK_MASTERY_LIVE_USER_IDS", "").strip()
    if not raw_ids:
        logger.warning(
            "resolve_effective_mastery_flag: FF=live but FF_MOCK_MASTERY_LIVE_USER_IDS "
            "is empty — downgrading to shadow for user=%s",
            user_id,
        )
        return "shadow"

    try:
        allowlist = {uid.strip() for uid in raw_ids.split(",") if uid.strip()}
    except Exception:
        logger.exception(
            "resolve_effective_mastery_flag: failed to parse FF_MOCK_MASTERY_LIVE_USER_IDS — "
            "downgrading to shadow for user=%s",
            user_id,
        )
        return "shadow"

    if user_id in allowlist:
        return "live"

    return "shadow"
