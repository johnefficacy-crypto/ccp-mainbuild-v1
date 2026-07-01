"""EWP-2B mastery outbox drain (architecture §8.2, §10.1).

Post-commit worker for the transactional mastery outbox. The evaluation
transaction enqueues a ``writing_mastery_outbox`` row (with the flag state pinned
at creation); this drain claims it via ``ewp_claim_mastery_outbox`` (FOR UPDATE
SKIP LOCKED + lease), re-derives the unit-level evidence DETERMINISTICALLY from
the committed evaluation, and writes the evidence + shadow rows idempotently
through ``ewp_complete_mastery_outbox`` (ON CONFLICT (evidence_key) DO NOTHING).

Mastery writes are SHADOW-ONLY until the Lane A gate clears (see mastery_flag);
even a ``live`` pinned flag only writes evidence + shadow here — the unified
aggregator publish is a separate, gated step and is intentionally not done.

Single-instance in the scheduler; this pass drains at most one outbox row.
"""
from __future__ import annotations

import logging
from typing import Any

from app.study_os.writing_practice import evidence_deriver as ev

logger = logging.getLogger("career_copilot.study_os.writing_mastery_outbox")


def run_outbox_pass(sb: Any, *, lease_seconds: int = 900) -> dict[str, Any]:
    """Claim and process at most one pending EVALUATION mastery-outbox row.

    Emits, in ONE idempotent batch: the unit-level evidence row (when warranted)
    AND one projection-linked row per current-state automatic issue projection on
    the evaluation (§4.12/§10.1). review_correction rows are drained separately
    by ``run_review_correction_pass``.
    """
    claim = (
        sb.rpc("ewp_claim_mastery_outbox", {"p_lease_seconds": lease_seconds}).execute()
    ).data
    if not claim:
        # No evaluation row pending — drain a review_correction row (§4.12c) so the
        # single scheduled outbox job covers both kinds.
        return run_review_correction_pass(sb, lease_seconds=lease_seconds)

    outbox_id = claim["id"]
    token = claim["claim_token"]
    try:
        pairs: list[dict[str, Any]] = []
        unit = ev.derive_unit_evidence(
            user_id=claim["user_id"], evaluation_id=claim["evaluation_id"],
            topic_id=claim["topic_id"], microtopic_id=claim.get("microtopic_id"),
            exam_id=claim.get("exam_id"), source_entity_id=claim["source_entity_id"],
            exercise_type=claim["exercise_type"],
            has_unresolved_must_fix=claim["has_unresolved_must_fix"],
            resolved_issue_count=claim["resolved_issue_count"],
            overall_status=claim["overall_status"],
        )
        if unit is not None:
            pairs.append({"evidence": unit.to_evidence_dict(), "shadow": unit.to_shadow_dict()})

        # One projection-linked row per current-state automatic issue projection.
        for proj in claim.get("issue_projections") or []:
            row = ev.derive_issue_evidence(
                user_id=claim["user_id"], evaluation_id=claim["evaluation_id"],
                topic_id=claim["topic_id"], exam_id=claim.get("exam_id"),
                source_entity_id=claim["source_entity_id"], exercise_type=claim["exercise_type"],
                issue_projection_id=proj["issue_projection_id"],
                issue_microtopic_id=proj.get("microtopic_id"),
                evidence_tier=proj["evidence_tier"],
            )
            pairs.append({"evidence": row.to_evidence_dict(), "shadow": row.to_shadow_dict()})

        sb.rpc("ewp_complete_mastery_outbox_batch", {
            "p_id": outbox_id, "p_claim_token": token,
            "p_pairs": pairs if pairs else None,
        }).execute()
        return {
            "processed": 1, "status": "done" if pairs else "done_noop", "id": outbox_id,
            "rows": len(pairs), "flag": claim.get("mastery_flag_state"),
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("mastery outbox drain failed for %s", outbox_id)
        try:
            sb.rpc("ewp_fail_mastery_outbox", {
                "p_id": outbox_id, "p_claim_token": token, "p_error": str(exc)[:500],
            }).execute()
        except Exception:  # noqa: BLE001
            logger.exception("could not record outbox failure for %s", outbox_id)
        return {"processed": 1, "status": "failed", "id": outbox_id, "error": str(exc)[:200]}


def run_review_correction_pass(sb: Any, *, lease_seconds: int = 900) -> dict[str, Any]:
    """Claim and apply at most one pending review_correction outbox row (§4.12c).

    The correction op (retract/replace/re-assert) and the op-specific projection
    are resolved in-DB by the claim RPC; here we re-derive the correction evidence
    key (owner of the §4.12b layout) and hand the evidence + shadow payloads to
    ``ewp_complete_review_correction``, which inserts them under the correction
    trigger (superserses the effective tail, latest-review, op↔decision). The
    mode is the pinned one copied from the assertion (never re-resolved).
    """
    claim = (
        sb.rpc("ewp_claim_review_correction_outbox", {"p_lease_seconds": lease_seconds}).execute()
    ).data
    if not claim:
        return {"processed": 0, "status": "idle"}

    outbox_id = claim["id"]
    token = claim["claim_token"]
    try:
        row = ev.derive_review_correction_evidence(
            evidence_op=claim["evidence_op"], user_id=claim["user_id"],
            evaluation_id=claim["evaluation_id"], topic_id=claim["topic_id"],
            microtopic_id=claim.get("microtopic_id"), exam_id=claim.get("exam_id"),
            source_type=claim["source_type"], source_entity_id=claim["source_entity_id"],
            evidence_tier=claim["evidence_tier"],
            issue_projection_id=claim["issue_projection_id"],
            review_event_id=claim["review_event_id"],
            supersedes_evidence_key=claim["supersedes_evidence_key"],
        )
        evidence = {
            **row.to_evidence_dict(),
            "review_event_id": claim["review_event_id"],
            "supersedes_evidence_key": claim["supersedes_evidence_key"],
        }
        shadow = row.to_shadow_dict()
        sb.rpc("ewp_complete_review_correction", {
            "p_id": outbox_id, "p_claim_token": token,
            "p_evidence": evidence, "p_shadow": shadow,
        }).execute()
        return {
            "processed": 1, "status": "done", "id": outbox_id,
            "evidence_op": claim["evidence_op"], "flag": claim.get("mastery_flag_state"),
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("review-correction drain failed for %s", outbox_id)
        try:
            sb.rpc("ewp_fail_mastery_outbox", {
                "p_id": outbox_id, "p_claim_token": token, "p_error": str(exc)[:500],
            }).execute()
        except Exception:  # noqa: BLE001
            logger.exception("could not record correction failure for %s", outbox_id)
        return {"processed": 1, "status": "failed", "id": outbox_id, "error": str(exc)[:200]}


def sweep_stale_outbox(sb: Any, *, lease_seconds: int = 900) -> dict[str, Any]:
    """Reclaim mastery-outbox rows whose lease expired (crash after claim); §8.3."""
    swept = (
        sb.rpc("ewp_sweep_stale_mastery_outbox", {"p_lease_seconds": lease_seconds}).execute()
    ).data or 0
    return {"swept": int(swept)}
