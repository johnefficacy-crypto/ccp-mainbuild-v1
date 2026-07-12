"""``ca:generate`` worker — drain one CA generation job (GQR-G3).

Mirrors the EWP evaluation worker (`writing_practice/evaluation_worker.py`): claim a
job via a lease+fencing RPC, run the LLM stages A/B/C **outside any DB transaction**,
run deterministic Stage-D validation (code), then commit every artefact + the job ack
atomically through the fencing-checked ``ca_complete_generation`` RPC. On error the job
is released via ``ca_fail_generation_job`` (retry/backoff, terminal at max_attempts).

Shadow / no authority: candidates land in ``current_affairs_question_candidates`` with a
validation verdict and full audit; NOTHING here promotes, publishes, or writes the
objective bank. Claims/events are inserted ``reviewer_status='pending'`` — never verified.

The scheduler cron for ``ca:generate`` is wired in GQR-G5 (alongside ``ca:ingest``); this
module exposes the pure worker function so it is unit-testable and schedulable later.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from app.current_affairs.generation import adapters as ad
from app.current_affairs.generation.validator import validate_candidate

logger = logging.getLogger("career_copilot.current_affairs.generation_worker")

_JOB_KIND = "ca_generation"


def _temp_claim_id(ei: int, ci: int) -> str:
    return f"e{ei}c{ci}"


def _build_persist_payload(
    document: dict[str, Any],
    *,
    adapter: ad.GenerationAdapter,
    source_authority: str | None,
    existing_fingerprints: frozenset[str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Run stages A→D for one document. Returns (persist_payload, audit_runs).

    Claims carry a client-side ``temp_id``; candidates reference those temp ids, and the
    complete RPC resolves temp ids → inserted claim uuids atomically. Validation runs
    against the temp-id map so it needs no DB round-trip.
    """
    runs: list[dict[str, Any]] = []
    source_by_doc = {str(document.get("id")): (source_authority or "")}

    extraction = adapter.extract(document)
    if extraction.run:
        runs.append(extraction.run.to_dict())

    out_events: list[dict[str, Any]] = []
    for ei, event in enumerate(extraction.events):
        # Assign temp ids + build the validation context for this event's claims.
        claims_by_id: dict[str, dict[str, Any]] = {}
        evidence_by_claim: dict[str, list[dict[str, Any]]] = {}
        persist_claims: list[dict[str, Any]] = []
        pipeline_claims: list[dict[str, Any]] = []
        for ci, claim in enumerate(event.get("claims") or []):
            tid = _temp_claim_id(ei, ci)
            evidence = list(claim.get("evidence") or [])
            claims_by_id[tid] = {**claim, "id": tid}
            evidence_by_claim[tid] = evidence
            pipeline_claims.append({**claim, "id": tid})
            persist_claims.append({
                "temp_id": tid,
                "claim_text": claim.get("claim_text"),
                "claim_fingerprint": claim.get("claim_fingerprint"),
                "factual_status": claim.get("factual_status") or "current",
                "evidence": evidence,
            })

        gen = adapter.generate(event, pipeline_claims)
        if gen.run:
            runs.append(gen.run.to_dict())

        persist_candidates: list[dict[str, Any]] = []
        for payload in gen.candidates:
            verification = adapter.verify(
                payload, pipeline_claims,
                [e for c in (payload.get("linked_claim_ids") or []) for e in evidence_by_claim.get(str(c), [])],
            )
            if verification.run:
                runs.append(verification.run.to_dict())
            result = validate_candidate(
                payload,
                claims_by_id=claims_by_id,
                evidence_by_claim=evidence_by_claim,
                source_authority_by_document=source_by_doc,
                event=event,
                existing_fingerprints=existing_fingerprints,
            )
            persist_candidates.append({
                "question_payload": payload,
                "question_fingerprint": payload.get("question_fingerprint"),
                "linked_temp_claim_ids": [str(c) for c in (payload.get("linked_claim_ids") or [])],
                "status": "review_ready" if result.ok else "validation_failed",
                "validation_result": result.to_dict(),
                "verifier_verdict": verification.verdict,
            })

        out_events.append({
            "temp_id": f"e{ei}",
            "canonical_title": event.get("canonical_title"),
            "event_date": event.get("event_date"),
            "category": event.get("category"),
            "event_fingerprint": event.get("event_fingerprint"),
            "editorial_importance": event.get("editorial_importance") or "normal",
            "relevance_from": event.get("relevance_from"),
            "relevance_until": event.get("relevance_until"),
            "claims": persist_claims,
            "candidates": persist_candidates,
        })

    return {"events": out_events}, runs


def run_generation_worker_pass(sb: Any, *, lease_seconds: int = 900) -> dict[str, Any]:
    """Claim and process at most one pending CA generation job."""
    claim = sb.rpc("ca_claim_generation_job", {
        "p_lease_seconds": lease_seconds, "p_job_kinds": [_JOB_KIND],
    }).execute().data
    if not claim:
        return {"processed": 0, "status": "idle"}

    job_id = claim["job_id"]
    token = claim["claim_token"]
    try:
        document = claim["document"]
        adapter = ad.get_generation_adapter()
        existing = frozenset(str(f) for f in (claim.get("existing_fingerprints") or []))
        persist, runs = _build_persist_payload(
            document, adapter=adapter,
            source_authority=claim.get("source_authority_level"),
            existing_fingerprints=existing,
        )
        out = sb.rpc("ca_complete_generation", {
            "p_job_id": job_id,
            "p_claim_token": token,
            "p_document_id": document.get("id"),
            "p_events": persist["events"],
            "p_generation_runs": runs,
            "p_adapter_version": adapter.version,
        }).execute().data
        candidate_count = sum(len(e["candidates"]) for e in persist["events"])
        review_ready = sum(
            1 for e in persist["events"] for c in e["candidates"] if c["status"] == "review_ready"
        )
        return {
            "processed": 1, "status": "succeeded", "job_id": job_id,
            "events": len(persist["events"]), "candidates": candidate_count,
            "review_ready": review_ready, "result": out,
        }
    except Exception as exc:  # noqa: BLE001 — record the failure on the job row
        logger.exception("ca generation failed for job %s", job_id)
        try:
            sb.rpc("ca_fail_generation_job", {
                "p_job_id": job_id, "p_claim_token": token, "p_error": str(exc)[:500],
            }).execute()
        except Exception:  # noqa: BLE001 — fencing may already have moved the job
            logger.exception("could not record job failure for %s", job_id)
        return {"processed": 1, "status": "failed", "job_id": job_id, "error": str(exc)[:200]}


def sweep_stale_generation_jobs(sb: Any, *, lease_seconds: int = 900) -> dict[str, Any]:
    """Reclaim jobs whose lease expired (crashed/hung worker)."""
    swept = sb.rpc("ca_sweep_stale_generation_jobs", {"p_lease_seconds": lease_seconds}).execute().data or 0
    return {"swept": int(swept)}
