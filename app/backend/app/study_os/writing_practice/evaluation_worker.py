"""EWP-2B async language-evaluation worker (architecture §8.1).

Claims one pending ``writing_evaluation_jobs`` row via the ``ewp_claim_evaluation_job``
RPC (FOR UPDATE SKIP LOCKED + lease + fencing token), runs the DETERMINISTIC MOCK
language evaluator (a real LLM adapter is a later, explicitly-gated slice), and
commits the result atomically through ``ewp_complete_language_evaluation`` — which
does the fencing re-check, replay guard, issue/lineage/projection inserts, the unit
transition, the mastery-outbox enqueue, the job ack, and the session rollup, all in
one transaction under the canonical locks. On any error the job is released via
``ewp_fail_evaluation_job`` (retry with backoff, or terminal_partial/failed at
max_attempts).

The evaluator call runs OUTSIDE any DB transaction (§8.1 step 3), so a hang or crash
mid-call only holds the lease — the sweeper reclaims it and fencing prevents a stale
double-apply. Single-instance in the scheduler (max_instances=1, coalesce=True); this
pass claims and runs at most one job.
"""
from __future__ import annotations

import logging
from typing import Any

from app.study_os.writing_practice import evidence_deriver as ev
from app.study_os.writing_practice import language_evaluator as lang
from app.study_os.writing_practice import rubric_evaluator as rubric
from app.study_os.writing_practice.content_hash import compute_content_hash
from app.study_os.writing_practice.mastery_flag import (
    get_writing_mastery_write_flag,
    resolve_effective_writing_mastery_flag,
)

logger = logging.getLogger("career_copilot.study_os.writing_evaluator")

# Exercise types that also get a Stage-3 rubric pass folded into the same job.
_RUBRIC_EXERCISES = frozenset({
    "paragraph_writing", "summary_writing", "precis_practice",
    "essay_practice", "letter_practice",
})


def run_worker_pass(sb: Any, *, lease_seconds: int = 900) -> dict[str, Any]:
    """Claim and run at most one pending language-evaluation job."""
    claim = (
        sb.rpc("ewp_claim_evaluation_job", {
            "p_lease_seconds": lease_seconds,
            "p_job_kinds": ["language_evaluation"],
        }).execute()
    ).data
    if not claim:
        return {"processed": 0, "status": "idle"}

    job_id = claim["job_id"]
    token = claim["claim_token"]

    # Defence-in-depth (§8.1 step 2 / §14): recompute the stored answer's hash and
    # require it to match the version's content_hash BEFORE evaluating. A mismatch
    # is CORRUPTION and must FAIL CLOSED down a DISTINCT terminal path
    # (ewp_reject_corrupt_version) — NOT the recoverable ewp_fail_evaluation_job
    # retry path — so a corrupt version can never flow into terminal_partial/ready
    # (a usable result) and never consumes a recoverable attempt.
    answer_text = claim["answer_text"]
    if compute_content_hash(answer_text) != claim["content_hash"]:
        logger.error("content_hash mismatch for job %s (version %s) — rejecting corrupt",
                     job_id, claim.get("unit_version_id"))
        try:
            out = (
                sb.rpc("ewp_reject_corrupt_version", {
                    "p_job_id": job_id, "p_claim_token": token,
                    "p_error": "content_hash_mismatch",
                }).execute()
            ).data
        except Exception:  # noqa: BLE001 — fencing may already have moved the job
            logger.exception("could not reject corrupt version for %s", job_id)
            out = None
        return {"processed": 1, "status": "rejected_corrupt", "job_id": job_id, "result": out}

    try:
        result = lang.evaluate_language(
            claim["answer_text"],
            exercise_type=claim["exercise_type"],
            # EWP-SP1: thread the immutable snapshot's prompt/source through so the
            # evaluator can run deterministic source-comparison (migration 222 returns
            # these on the claim). Missing source on a source-dependent type fails
            # closed to human review inside the evaluator.
            prompt_text=claim.get("prompt_text"),
            source_text=claim.get("source_text"),
            active_prior_issues=claim.get("active_prior_issues") or [],
            resolved_prior_lineages=claim.get("resolved_prior_lineages") or [],
        )
        issues = result.to_issue_dicts()

        dimension_scores: dict | None = None
        # EWP-SP1: a deterministic source-comparison verdict (source_unchanged /
        # meaning_not_preserved / source_comparison_uncertain) fails CLOSED to
        # human review — never positive/passing mastery evidence.
        needs_review = result.needs_human_review
        if claim["exercise_type"] in _RUBRIC_EXERCISES:
            rr = rubric.evaluate_rubric(
                claim["answer_text"], dimensions=claim.get("rubric_dimensions") or [])
            dimension_scores = rr.to_dict()
            needs_review = needs_review or rr.needs_human_review

        # A successful language stage lands overall_status='completed' in the RPC.
        # Predict the mastery evidence key deterministically so it matches the key
        # the outbox drain re-derives from the DB (idempotent end-to-end).
        flag = resolve_effective_writing_mastery_flag(
            get_writing_mastery_write_flag(), claim["user_id"])
        idempotency_key: str | None = None
        # Skip mastery derivation entirely when routed to human review: no positive
        # OR negative mastery evidence flows from a source-comparison-uncertain /
        # unchanged / not-preserved submission (fail-closed, §3.4).
        if flag in ("shadow", "live") and claim.get("is_current") and not needs_review:
            has_must_fix = any(i.get("severity") == "must_fix" for i in issues)
            predecessors = {i.get("predecessor_issue_event_id") for i in issues}
            resolved_count = sum(
                1 for a in (claim.get("active_prior_issues") or [])
                if a["issue_event_id"] not in predecessors
            )
            row = ev.derive_unit_evidence(
                user_id=claim["user_id"], evaluation_id=claim["evaluation_id"],
                topic_id=claim["topic_id"], microtopic_id=claim.get("microtopic_id"),
                exam_id=claim.get("exam_id"), source_entity_id=claim["session_id"],
                exercise_type=claim["exercise_type"],
                has_unresolved_must_fix=has_must_fix, resolved_issue_count=resolved_count,
                overall_status="completed",
            )
            idempotency_key = row.evidence_key if row else None

        out = (
            sb.rpc("ewp_complete_language_evaluation", {
                "p_job_id": job_id,
                "p_claim_token": token,
                "p_evaluator_version": result.evaluator_version,
                "p_issues": issues,
                "p_language_result": result.to_result_dict(),
                "p_dimension_scores": dimension_scores,
                "p_needs_human_review": needs_review,
                "p_mastery_flag": flag,
                "p_mastery_idempotency_key": idempotency_key,
            }).execute()
        ).data
        return {"processed": 1, "status": "succeeded", "job_id": job_id, "result": out}
    except Exception as exc:  # noqa: BLE001 — record the failure on the job row
        logger.exception("language evaluation failed for job %s", job_id)
        try:
            sb.rpc("ewp_fail_evaluation_job", {
                "p_job_id": job_id, "p_claim_token": token, "p_error": str(exc)[:500],
            }).execute()
        except Exception:  # noqa: BLE001 — fencing may already have moved the job
            logger.exception("could not record job failure for %s", job_id)
        return {"processed": 1, "status": "failed", "job_id": job_id, "error": str(exc)[:200]}


def sweep_stale_jobs(sb: Any, *, lease_seconds: int = 900) -> dict[str, Any]:
    """Reclaim jobs whose lease expired (crashed/hung worker); §8.3."""
    swept = (
        sb.rpc("ewp_sweep_stale_evaluation_jobs", {"p_lease_seconds": lease_seconds}).execute()
    ).data or 0
    return {"swept": int(swept)}
