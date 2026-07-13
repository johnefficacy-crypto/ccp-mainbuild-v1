"""Stages A/B/C — the LLM adapter boundary for CA generation (SHADOW).

Mirrors the EWP semantic-adapter contract (`writing_practice/semantic_evaluator.py`):
provider-swappable behind a stable boundary, model resolved from env (never hardcoded),
fail-closed statuses, and telemetry (provider/model/prompt_version/tokens/cost/latency)
returned for the generation audit — never raw text persisted.

Default is the deterministic MOCK provider so the whole pipeline runs end-to-end in CI
with no provider and no key. The real provider-backed adapter is constructed only when
``FF_CA_LLM=shadow`` (fails closed to the mock otherwise). Output is shadow / no
authority in every mode: candidates still pass Stage-D validation + the operator gate.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any

PROMPT_VERSION = "ca-gen-v1"
_PROVIDER = "anthropic"
_DEFAULT_MODEL = "claude-opus-4-8"

# Stage identifiers — recorded as ``action`` on current_affairs_generation_runs.
ACTION_EXTRACTION = "extraction"
ACTION_MCQ_GENERATION = "mcq_generation"
ACTION_VERIFICATION = "verification"


def _flag() -> str:
    """FF_CA_LLM resolution. Fails CLOSED to ``off`` (→ deterministic mock)."""
    return (os.getenv("FF_CA_LLM") or "off").strip().lower()


def _hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


@dataclass
class AdapterRun:
    """Telemetry-only audit envelope for one LLM call → a generation_runs row."""

    action: str
    status: str = "succeeded"  # succeeded | malformed | refusal | timeout | provider_error | mock
    provider: str | None = None
    model: str | None = None
    prompt_version: str | None = PROMPT_VERSION
    input_hash: str | None = None
    output_hash: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    estimated_cost_usd: float | None = None
    latency_ms: int | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action, "status": self.status, "provider": self.provider,
            "model": self.model, "prompt_version": self.prompt_version,
            "input_hash": self.input_hash, "output_hash": self.output_hash,
            "input_tokens": self.input_tokens, "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens, "estimated_cost_usd": self.estimated_cost_usd,
            "latency_ms": self.latency_ms, "error": self.error,
        }


@dataclass
class ExtractionResult:
    events: list[dict[str, Any]] = field(default_factory=list)
    run: AdapterRun | None = None


@dataclass
class GenerationResult:
    candidates: list[dict[str, Any]] = field(default_factory=list)
    run: AdapterRun | None = None


@dataclass
class VerificationResult:
    verdict: dict[str, Any] = field(default_factory=dict)
    run: AdapterRun | None = None


class GenerationAdapter:
    """Boundary implemented by the mock and the real provider adapter."""

    version = "ca-abstract"

    def extract(self, document: dict[str, Any]) -> ExtractionResult:  # pragma: no cover
        raise NotImplementedError

    def generate(self, event: dict[str, Any], claims: list[dict[str, Any]]) -> GenerationResult:  # pragma: no cover
        raise NotImplementedError

    def verify(
        self, candidate: dict[str, Any], claims: list[dict[str, Any]],
        evidence: list[dict[str, Any]],
    ) -> VerificationResult:  # pragma: no cover
        raise NotImplementedError


# ── Deterministic mock (CI / shadow default) ───────────────────────────────
_SENT_SPLIT = "([.!?])"


def _first_sentence(text: str) -> str:
    import re

    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    return (parts[0] if parts else (text or "")).strip()


class MockGenerationAdapter(GenerationAdapter):
    """Fully deterministic; derives one event → one claim → one MCQ from the document
    text. Structurally faithful so the pipeline + Stage-D validator exercise real
    shapes without a provider. Produces stable fingerprints for dedup testing."""

    version = f"ca-mock:{PROMPT_VERSION}"

    def extract(self, document: dict[str, Any]) -> ExtractionResult:
        raw = str(document.get("raw_text") or "")
        title = str(document.get("title") or "").strip() or _first_sentence(raw)[:120]
        run = AdapterRun(action=ACTION_EXTRACTION, status="mock", provider="mock",
                         model=self.version, input_hash=_hash({"doc": document.get("id"), "raw": raw}))
        if not title:
            run.output_hash = _hash([])
            return ExtractionResult(events=[], run=run)
        claim_text = _first_sentence(raw) or title
        event = {
            "canonical_title": title,
            "event_date": document.get("published_at") or document.get("fetched_at"),
            "category": document.get("category") or document.get("document_type"),
            "event_fingerprint": _hash(["evt", title.lower()]),
            "editorial_importance": "normal",
            "claims": [{
                "claim_text": claim_text,
                "claim_fingerprint": _hash(["clm", claim_text.lower()]),
                "factual_status": "current",
                "evidence": [{
                    "document_id": document.get("id"),
                    "evidence_text": claim_text,
                    "start_offset": 0,
                    "end_offset": len(claim_text),
                    "evidence_role": "primary",
                }],
            }],
        }
        run.output_hash = _hash([event["event_fingerprint"]])
        return ExtractionResult(events=[event], run=run)

    def generate(self, event: dict[str, Any], claims: list[dict[str, Any]]) -> GenerationResult:
        run = AdapterRun(action=ACTION_MCQ_GENERATION, status="mock", provider="mock",
                         model=self.version, input_hash=_hash({"event": event.get("event_fingerprint")}))
        if not claims:
            run.output_hash = _hash([])
            return GenerationResult(candidates=[], run=run)
        claim = claims[0]
        title = str(event.get("canonical_title") or "").strip()
        answer = title or str(claim.get("claim_text") or "")
        payload = {
            "stem": f"Which of the following is correct regarding the event dated "
                    f"{event.get('event_date')}?",
            "options": [
                {"id": "a", "text": answer},
                {"id": "b", "text": f"{answer} (unrelated variant one)"},
                {"id": "c", "text": f"{answer} (unrelated variant two)"},
                {"id": "d", "text": f"{answer} (unrelated variant three)"},
            ],
            "correct_option_id": "a",
            "explanation": f"Per the source claim: {claim.get('claim_text')}",
            "distractor_rationales": {
                "b": "Not supported by the cited claim.",
                "c": "Not supported by the cited claim.",
                "d": "Not supported by the cited claim.",
            },
            "linked_claim_ids": [claim.get("id")] if claim.get("id") else [],
            "difficulty": "medium",
            "style": "statement_recall",
            "question_fingerprint": _hash(["mcq", (event.get("event_fingerprint"), answer.lower())]),
        }
        run.output_hash = _hash([payload["question_fingerprint"]])
        return GenerationResult(candidates=[payload], run=run)

    def verify(self, candidate, claims, evidence) -> VerificationResult:
        # Advisory only (Stage C). The mock affirms; the deterministic validator (Stage
        # D) is the real gate, so an affirming verifier can never bypass validation.
        run = AdapterRun(action=ACTION_VERIFICATION, status="mock", provider="mock",
                         model=self.version, input_hash=_hash({"fp": candidate.get("question_fingerprint")}))
        verdict = {
            "supported_answer": True,
            "single_correct": True,
            "options_safe": True,
            "explanation_supported": bool(evidence),
            "time_dependent_or_ambiguous": False,
            "advisory_only": True,
        }
        run.output_hash = _hash(verdict)
        return VerificationResult(verdict=verdict, run=run)


def get_generation_adapter() -> GenerationAdapter:
    """Return the active adapter. Deterministic mock unless ``FF_CA_LLM=shadow`` and a
    real provider adapter is importable — and even then the real adapter is SHADOW
    (its output still passes Stage-D validation + the operator gate)."""
    if _flag() == "shadow":
        try:
            from app.current_affairs.generation.provider_adapter import (
                ProviderGenerationAdapter,
            )

            return ProviderGenerationAdapter()
        except Exception:  # noqa: BLE001 — no approved provider adapter → fail closed to mock
            return MockGenerationAdapter()
    return MockGenerationAdapter()
