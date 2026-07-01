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
    """Claim and process at most one pending mastery-outbox row."""
    claim = (
        sb.rpc("ewp_claim_mastery_outbox", {"p_lease_seconds": lease_seconds}).execute()
    ).data
    if not claim:
        return {"processed": 0, "status": "idle"}

    outbox_id = claim["id"]
    if claim.get("skipped"):
        # review-correction rows are acked as no-ops by the claim RPC (EWP-3).
        return {"processed": 1, "status": "skipped", "id": outbox_id}

    try:
        row = ev.derive_unit_evidence(
            user_id=claim["user_id"], evaluation_id=claim["evaluation_id"],
            topic_id=claim["topic_id"], microtopic_id=claim.get("microtopic_id"),
            exam_id=claim.get("exam_id"), source_entity_id=claim["source_entity_id"],
            has_unresolved_must_fix=claim["has_unresolved_must_fix"],
            resolved_issue_count=claim["resolved_issue_count"],
            overall_status=claim["overall_status"],
        )
        if row is None:
            # No evidence warranted (e.g. non-terminal); ack the row as done.
            sb.rpc("ewp_complete_mastery_outbox", {
                "p_id": outbox_id, "p_evidence": None, "p_shadow": None,
            }).execute()
            return {"processed": 1, "status": "done_noop", "id": outbox_id}

        sb.rpc("ewp_complete_mastery_outbox", {
            "p_id": outbox_id,
            "p_evidence": row.to_evidence_dict(),
            "p_shadow": row.to_shadow_dict(),
        }).execute()
        return {
            "processed": 1, "status": "done", "id": outbox_id,
            "tier": row.evidence_tier, "flag": claim.get("mastery_flag_state"),
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("mastery outbox drain failed for %s", outbox_id)
        try:
            sb.rpc("ewp_fail_mastery_outbox", {
                "p_id": outbox_id, "p_error": str(exc)[:500],
            }).execute()
        except Exception:  # noqa: BLE001
            logger.exception("could not record outbox failure for %s", outbox_id)
        return {"processed": 1, "status": "failed", "id": outbox_id, "error": str(exc)[:200]}
