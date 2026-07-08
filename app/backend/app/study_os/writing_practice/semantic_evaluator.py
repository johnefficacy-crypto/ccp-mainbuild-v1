"""EWP-SP1b provider-backed semantic (LLM) evaluator adapter — SHADOW ONLY.

Authorized by docs/architecture/ewp-semantic-evaluator-adapter.md, which permits
building this adapter in SHADOW mode only. It is wired ONLY behind
``language_evaluator.get_semantic_shadow_evaluator()`` (constructed exclusively
when ``FF_WRITING_LLM_EVAL=shadow``). Its output NEVER reaches
``ewp_complete_language_evaluation`` — the canonical completion path stays
deterministic (``get_language_evaluator`` is unchanged). No mastery effect, no
prompt activation, no writing gate opened. The adapter measures only.

Governance constraints honoured here (arch doc §3 SHADOW, §4 safety controls):

- Provider-swappable behind the shipped ``LanguageEvaluator`` boundary; the model
  is resolved from configuration/env, never hardcoded to a single build.
- Fail-closed: ANY provider/parse/timeout/circuit/refusal condition returns a
  telemetry-only status and empty authoritative signal — it can never turn a
  deterministic verdict into a pass (the deterministic result is what the worker
  persists).
- No raw text persisted: this module returns issue COUNTS + a summary verdict to
  the worker's telemetry sink; the worker records only the input hash + summary
  (provider/model/prompt_version/confidence/tokens/cost/latency/status). Raw
  answer/prompt/source text is sent to the provider to evaluate one answer, but
  is never written to ``writing_language_evaluator_runs`` or returned for
  persistence.

The adapter returns a :class:`SemanticShadowResult` (a ``LanguageResult``
subclass carrying telemetry-only attributes) so it satisfies the
``LanguageEvaluator`` protocol while conveying provider/token/cost/status to the
worker probe. It never raises: every failure mode maps to a recorded status.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict, ValidationError

from .language_evaluator import (
    IssueType,
    LanguageIssueOut,
    LanguageResult,
    Severity,
    SourceComparison,
    utf16_span,
)

logger = logging.getLogger("career_copilot.study_os.writing_semantic_evaluator")

# Prompt-template build identifier — stored on telemetry so a prompt change is
# distinguishable in the shadow evidence window (arch doc §4.6, §5.2 reset rule).
PROMPT_VERSION = "ewp-sem-v1"

# Adapter/evaluator version reported to telemetry (model + prompt build). Kept
# distinct from the deterministic lang-mock-v* versions so findings stay
# auditable. The model id is appended at runtime by the adapter.
ADAPTER_VERSION_PREFIX = "lang-llm-shadow"

SEMANTIC_PROVIDER = "anthropic"

# Model id is resolved from env at build time (arch doc §6: default to the latest
# Claude models; never hardcode a single build id in the doc/source). Provider is
# swappable behind the boundary.
_DEFAULT_MODEL = "claude-opus-4-7"


def _resolve_model() -> str:
    return (os.getenv("EWP_SEMANTIC_MODEL") or _DEFAULT_MODEL).strip()


# Per-model USD price per 1M tokens (input, output). Rates are per the claude-api
# reference (Current Models table): the Opus tier is $5.00 in / $25.00 out per
# 1M tokens, the Sonnet tier $3.00 / $15.00. Cost is derived from observed token
# counts x these rates (arch doc §5 G5-e cost ceiling is measured from this).
_MODEL_PRICING_USD_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-opus-4-7": (5.00, 25.00),
    "claude-opus-4-6": (5.00, 25.00),
    "claude-sonnet-4-6": (3.00, 15.00),
}
_DEFAULT_PRICING = (5.00, 25.00)


def _estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    in_rate, out_rate = _MODEL_PRICING_USD_PER_MTOK.get(model, _DEFAULT_PRICING)
    return round(
        (input_tokens / 1_000_000.0) * in_rate + (output_tokens / 1_000_000.0) * out_rate,
        6,
    )


@dataclass(frozen=True)
class SemanticAdapterConfig:
    """Resilience + cost knobs (arch doc §4). All overridable for tests."""

    model: str = field(default_factory=_resolve_model)
    timeout_s: float = 20.0            # hard per-call wall timeout (§4)
    max_retries: int = 2               # at most 2 retries on transient errors (§4)
    backoff_base_s: float = 0.5        # exponential backoff base
    circuit_failure_threshold: int = 5  # consecutive failures -> open breaker
    circuit_cooldown_s: float = 60.0   # breaker stays open for this window
    confidence_threshold: float = 0.6  # below -> low_confidence (mirrors rubric 0.6)
    max_tokens: int = 1024


@dataclass
class SemanticShadowResult(LanguageResult):
    """``LanguageResult`` + telemetry-only fields. NEVER persisted as canonical.

    ``status`` is one of the ``writing_language_evaluator_runs`` telemetry states:
    ``succeeded`` | ``malformed`` | ``refusal`` | ``low_confidence`` |
    ``timeout`` | ``provider_error`` | ``skipped`` (skipped carries
    ``error_code='circuit_open'`` — the breaker short-circuited the call).
    These statuses route to NOTHING canonical; they are shadow measurement only.
    """

    status: str = "succeeded"
    provider: str | None = None
    provider_model: str | None = None
    prompt_version: str | None = None
    confidence: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    estimated_cost_usd: float | None = None
    error_code: str | None = None
    error_message: str | None = None


# --- structured model output (strict JSON via tool use) ---------------------

_SEMANTIC_TOOL_NAME = "record_semantic_evaluation"

# Tool input schema constrains the model to the frozen §5.1 taxonomy and the
# fixed severity set — the model is given no new vocabulary (arch doc §2.1).
_ISSUE_TYPES: tuple[str, ...] = (
    "sentence_fragment", "run_on_sentence", "subject_verb_agreement", "tense",
    "article", "preposition", "pronoun_reference", "modifier", "spelling",
    "punctuation", "word_choice", "collocation", "redundancy", "informal_usage",
    "cohesion", "logical_order", "off_topic", "word_limit", "format_violation",
)
_SEVERITIES: tuple[str, ...] = ("advisory", "should_fix", "must_fix")

_SEMANTIC_TOOL_SCHEMA = {
    "name": _SEMANTIC_TOOL_NAME,
    "description": (
        "Record a structured semantic evaluation of the learner's answer. "
        "Only use issue_type values from the provided enum; do not invent new "
        "categories."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "issues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "issue_type": {"type": "string", "enum": list(_ISSUE_TYPES)},
                        "severity": {"type": "string", "enum": list(_SEVERITIES)},
                        "quoted_text": {"type": "string"},
                        "explanation": {"type": "string"},
                    },
                    "required": ["issue_type", "severity", "quoted_text", "explanation"],
                },
            },
            "source_comparison": {
                "type": ["string", "null"],
                "enum": [
                    "source_unchanged",
                    "meaning_not_preserved",
                    "source_comparison_uncertain",
                    None,
                ],
            },
            "meaning_preserved_confidence": {"type": "number"},
            "refusal": {"type": "boolean"},
        },
        "required": ["issues", "meaning_preserved_confidence"],
    },
}

_SYSTEM_PROMPT = (
    "You are a Stage-2 English writing evaluator running in a measurement-only "
    "shadow mode. Given a learner's answer (and, for correction/grammar/vocabulary "
    "exercises, the prompt and the source sentence they were asked to fix), "
    "identify concrete language issues and judge whether the answer preserves the "
    "source's meaning. Report findings ONLY through the record_semantic_evaluation "
    "tool. Use issue_type values strictly from the provided enum. Provide "
    "meaning_preserved_confidence in [0,1]. Set refusal=true only if you cannot "
    "evaluate the content for safety reasons."
)


class _SemanticIssue(BaseModel):
    model_config = ConfigDict(extra="ignore")
    issue_type: IssueType
    severity: Severity
    quoted_text: str
    explanation: str


class _SemanticVerdict(BaseModel):
    model_config = ConfigDict(extra="ignore")
    issues: list[_SemanticIssue] = []
    source_comparison: SourceComparison | None = None
    meaning_preserved_confidence: float | None = None
    refusal: bool = False


class _CircuitBreaker:
    """Trip to open after N consecutive failures; skip provider for a cooldown.

    Single-worker use (scheduler runs max_instances=1) but guarded with a lock so
    a future concurrent worker cannot corrupt the counter.
    """

    def __init__(self, *, threshold: int, cooldown_s: float) -> None:
        self._threshold = threshold
        self._cooldown_s = cooldown_s
        self._consecutive = 0
        self._opened_until = 0.0
        self._lock = threading.Lock()

    def is_open(self) -> bool:
        with self._lock:
            return time.monotonic() < self._opened_until

    def record_success(self) -> None:
        with self._lock:
            self._consecutive = 0
            self._opened_until = 0.0

    def record_failure(self) -> None:
        with self._lock:
            self._consecutive += 1
            if self._consecutive >= self._threshold:
                self._opened_until = time.monotonic() + self._cooldown_s

    def reset(self) -> None:
        with self._lock:
            self._consecutive = 0
            self._opened_until = 0.0


def _is_timeout(exc: BaseException) -> bool:
    if isinstance(exc, TimeoutError):
        return True
    try:
        import anthropic
    except ImportError:
        return False
    return isinstance(exc, getattr(anthropic, "APITimeoutError", ()))


def _is_transient(exc: BaseException) -> bool:
    """Transient = retryable (timeout / connection / 5xx / rate limit)."""
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    try:
        import anthropic
    except ImportError:
        return False
    transient_types = tuple(
        t for t in (
            getattr(anthropic, "APITimeoutError", None),
            getattr(anthropic, "APIConnectionError", None),
            getattr(anthropic, "InternalServerError", None),
            getattr(anthropic, "RateLimitError", None),
        ) if t is not None
    )
    if transient_types and isinstance(exc, transient_types):
        return True
    status_exc = getattr(anthropic, "APIStatusError", None)
    if status_exc is not None and isinstance(exc, status_exc):
        return int(getattr(exc, "status_code", 0) or 0) >= 500
    return False


class SemanticLanguageEvaluator:
    """Provider-backed shadow evaluator implementing the LanguageEvaluator boundary."""

    def __init__(
        self,
        *,
        config: SemanticAdapterConfig | None = None,
        client_factory=None,
        breaker: _CircuitBreaker | None = None,
    ) -> None:
        self._config = config or SemanticAdapterConfig()
        self._client_factory = client_factory
        self._breaker = breaker or _shared_breaker(self._config)

    @property
    def evaluator_version(self) -> str:
        return f"{ADAPTER_VERSION_PREFIX}:{self._config.model}:{PROMPT_VERSION}"

    def _build_client(self):
        if self._client_factory is not None:
            return self._client_factory()
        import anthropic  # deferred: no import cost on the off path

        # Key is sourced from the environment via the SDK's default resolution
        # (ANTHROPIC_API_KEY). Never hardcoded.
        return anthropic.Anthropic(timeout=self._config.timeout_s)

    def _fail(self, *, status: str, error_code: str | None = None, error_message: str | None = None) -> SemanticShadowResult:
        return SemanticShadowResult(
            issues=[],
            evaluator_version=self.evaluator_version,
            source_comparison=None,
            needs_human_review=False,
            status=status,
            provider=SEMANTIC_PROVIDER,
            provider_model=self._config.model,
            prompt_version=PROMPT_VERSION,
            error_code=error_code,
            error_message=error_message,
        )

    def evaluate(
        self,
        answer_text: str,
        *,
        exercise_type: str,
        prompt_text: str | None = None,
        source_text: str | None = None,
        active_prior_issues: list[dict] | None = None,
        resolved_prior_lineages: list[dict] | None = None,
    ) -> SemanticShadowResult:
        # Circuit breaker: skip the provider entirely while open (arch doc §4).
        # Recorded as 'skipped' with error_code='circuit_open' (a valid telemetry
        # status; no migration needed to add a distinct 'circuit_open' state).
        if self._breaker.is_open():
            return self._fail(status="skipped", error_code="circuit_open",
                              error_message="circuit breaker open; provider call skipped")

        try:
            client = self._build_client()
        except Exception as exc:  # noqa: BLE001 - SDK missing / bad config -> fail closed
            self._breaker.record_failure()
            return self._fail(status="provider_error", error_code=exc.__class__.__name__,
                              error_message=str(exc)[:200])

        resp, err_status, err = self._call_with_retry(client, answer_text,
                                                       exercise_type=exercise_type,
                                                       prompt_text=prompt_text,
                                                       source_text=source_text)
        if resp is None:
            self._breaker.record_failure()
            return self._fail(status=err_status, error_code=err[0], error_message=err[1])

        # A response arrived at transport level — reset the breaker regardless of
        # whether the content is usable (a malformed/refusal reply is not an outage).
        self._breaker.record_success()

        # Refusal / safety stop.
        if getattr(resp, "stop_reason", None) == "refusal":
            return self._telemetry_only(resp, status="refusal")

        verdict = self._parse(resp)
        if verdict is None:
            return self._telemetry_only(resp, status="malformed",
                                        error_code="schema_invalid")
        if verdict.refusal:
            return self._telemetry_only(resp, status="refusal")

        confidence = verdict.meaning_preserved_confidence
        status = "succeeded"
        if confidence is not None and confidence < self._config.confidence_threshold:
            status = "low_confidence"

        issues = self._map_issues(answer_text, verdict)
        return self._build_result(resp, status=status, verdict=verdict, issues=issues,
                                   confidence=confidence)

    # --- internals ----------------------------------------------------------

    def _call_with_retry(self, client, answer_text, *, exercise_type, prompt_text, source_text):
        user_prompt = self._render_prompt(answer_text, exercise_type=exercise_type,
                                          prompt_text=prompt_text, source_text=source_text)
        attempt = 0
        while True:
            try:
                resp = client.messages.create(
                    model=self._config.model,
                    max_tokens=self._config.max_tokens,
                    system=_SYSTEM_PROMPT,
                    tools=[_SEMANTIC_TOOL_SCHEMA],
                    tool_choice={"type": "tool", "name": _SEMANTIC_TOOL_NAME},
                    messages=[{"role": "user", "content": user_prompt}],
                )
                return resp, "succeeded", (None, None)
            except Exception as exc:  # noqa: BLE001 - classify and fail closed
                transient = _is_transient(exc)
                if transient and attempt < self._config.max_retries:
                    attempt += 1
                    time.sleep(self._config.backoff_base_s * (2 ** (attempt - 1)))
                    continue
                status = "timeout" if _is_timeout(exc) else "provider_error"
                logger.warning("semantic adapter call failed status=%s err=%s",
                               status, exc.__class__.__name__)
                return None, status, (exc.__class__.__name__, str(exc)[:200])

    def _render_prompt(self, answer_text, *, exercise_type, prompt_text, source_text) -> str:
        parts = [f"Exercise type: {exercise_type}"]
        if prompt_text:
            parts.append(f"Prompt:\n{prompt_text}")
        if source_text:
            parts.append(f"Source sentence to preserve:\n{source_text}")
        parts.append(f"Learner answer:\n{answer_text}")
        return "\n\n".join(parts)

    def _parse(self, resp) -> _SemanticVerdict | None:
        tool_input = None
        for block in getattr(resp, "content", None) or []:
            if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == _SEMANTIC_TOOL_NAME:
                tool_input = getattr(block, "input", None)
                break
        if not isinstance(tool_input, dict):
            return None
        try:
            return _SemanticVerdict.model_validate(tool_input)
        except ValidationError:
            return None

    def _map_issues(self, answer_text: str, verdict: _SemanticVerdict) -> list[LanguageIssueOut]:
        out: list[LanguageIssueOut] = []
        for issue in verdict.issues:
            span = utf16_span(answer_text, issue.quoted_text) if issue.quoted_text else None
            start, end = span if span is not None else (0, 0)
            try:
                out.append(LanguageIssueOut(
                    issue_type=issue.issue_type,
                    span_start_utf16=start,
                    span_end_utf16=end,
                    quoted_text=issue.quoted_text,
                    explanation=issue.explanation,
                    severity=issue.severity,
                ))
            except Exception:  # noqa: BLE001 - drop a malformed single issue, keep the rest
                continue
        return out

    def _usage(self, resp) -> tuple[int | None, int | None, int | None, float | None]:
        usage = getattr(resp, "usage", None)
        if usage is None:
            return None, None, None, None
        in_tok = getattr(usage, "input_tokens", None)
        out_tok = getattr(usage, "output_tokens", None)
        if in_tok is None or out_tok is None:
            return in_tok, out_tok, None, None
        total = int(in_tok) + int(out_tok)
        cost = _estimate_cost_usd(self._config.model, int(in_tok), int(out_tok))
        return int(in_tok), int(out_tok), total, cost

    def _telemetry_only(self, resp, *, status: str, error_code: str | None = None) -> SemanticShadowResult:
        in_tok, out_tok, total, cost = self._usage(resp)
        return SemanticShadowResult(
            issues=[], evaluator_version=self.evaluator_version,
            source_comparison=None, needs_human_review=False,
            status=status, provider=SEMANTIC_PROVIDER,
            provider_model=self._config.model, prompt_version=PROMPT_VERSION,
            input_tokens=in_tok, output_tokens=out_tok, total_tokens=total,
            estimated_cost_usd=cost, error_code=error_code,
        )

    def _build_result(self, resp, *, status, verdict, issues, confidence) -> SemanticShadowResult:
        in_tok, out_tok, total, cost = self._usage(resp)
        return SemanticShadowResult(
            issues=issues, evaluator_version=self.evaluator_version,
            source_comparison=verdict.source_comparison, needs_human_review=False,
            status=status, provider=SEMANTIC_PROVIDER,
            provider_model=self._config.model, prompt_version=PROMPT_VERSION,
            confidence=confidence, input_tokens=in_tok, output_tokens=out_tok,
            total_tokens=total, estimated_cost_usd=cost,
        )


# Process-wide breaker so consecutive failures across worker passes accumulate.
_BREAKER_LOCK = threading.Lock()
_BREAKER: _CircuitBreaker | None = None


def _shared_breaker(config: SemanticAdapterConfig) -> _CircuitBreaker:
    global _BREAKER
    with _BREAKER_LOCK:
        if _BREAKER is None:
            _BREAKER = _CircuitBreaker(
                threshold=config.circuit_failure_threshold,
                cooldown_s=config.circuit_cooldown_s,
            )
        return _BREAKER


def build_semantic_evaluator() -> SemanticLanguageEvaluator:
    """Construct the real provider-backed shadow adapter (arch doc §7)."""
    return SemanticLanguageEvaluator()
