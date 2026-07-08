"""Stage-2 language evaluator (architecture §5.1, §5.3) — DETERMINISTIC MOCK.

Pure, synchronous, no external calls, no database access. This module provides
the structured language-issue contract (§5.3) and a deterministic rule-based
mock evaluator standing in for the async LLM adapter. A real LLM adapter is a
later slice and is selected behind ``get_language_evaluator`` (see the TODO
there); nothing here ever touches the network.

Spans are UTF-16 code-unit offsets (§4.5b) so the frontend can verify
``answer_text.sliceUTF16(start, end) === quoted_text`` for emoji / non-BMP text.

Nothing here touches the database — callers persist the results.
"""
from __future__ import annotations

import logging
import os
import re
import unicodedata
from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, model_validator

from . import deterministic

logger = logging.getLogger("career_copilot.study_os.writing_language_evaluator")

# Bump when the mock rule set or output contract changes; stored on the
# evaluation row as language_evaluator_version so historical findings stay
# auditable (§4.6). v2 adds deterministic source-comparison result states
# (EWP-SP1): source_unchanged / meaning_not_preserved / source_comparison_uncertain.
LANGUAGE_EVALUATOR_VERSION = "lang-mock-v2"

# --- EWP-SP1 source-aware evaluation ---------------------------------------

# Deterministic source-comparison outcomes. These are RESULT-LEVEL states, NOT
# §5.1 issue types — they deliberately do NOT reuse `off_topic` (that projects
# to misread_question/concept_gap in §6 and would contaminate content-relevance
# mastery; PR #882 mistake). Any non-None state here fails CLOSED to human
# review (never positive/passing mastery evidence). See
# docs/architecture/ewp-semantic-evaluator-adapter.md §3.4.
SourceComparison = Literal[
    "source_unchanged",
    "meaning_not_preserved",
    "source_comparison_uncertain",
]

# Exercise types whose correctness is defined against `source_text` (the learner
# must correct / transform a given sentence). Pure CONSTRUCTION prompts
# (sentence_construction, paragraph_writing, …) have no source and are UNAFFECTED
# — source-comparison is skipped for them entirely.
def _is_source_dependent(exercise_type: str | None) -> bool:
    t = (exercise_type or "").lower()
    return (
        "correction" in t
        or "grammar" in t
        or t.startswith("vocabulary")
        or "vocabulary_in_context" in t
    )


_WS_RE = re.compile(r"\s+")


def _normalize_for_compare(text: str | None) -> str:
    """NFC + whitespace-collapse + case-fold normalisation for source comparison.

    Built on the same NFC base the deterministic layer uses (deterministic._normalise)
    so the two stages agree on Unicode form. Punctuation is preserved (adding a
    period can itself be a valid correction), only surrounding/duplicated
    whitespace and letter case are normalised away.
    """
    normalized = unicodedata.normalize("NFC", text or "")
    return _WS_RE.sub(" ", normalized.strip()).casefold()


def compute_source_comparison(
    answer_text: str,
    *,
    exercise_type: str | None,
    source_text: str | None,
) -> SourceComparison | None:
    """DETERMINISTIC source-comparison verdict (no heuristics, no model call).

    Returns None when the exercise is not source-dependent (construction prompts
    are unaffected). Otherwise:

    - source required but missing/empty  -> source_comparison_uncertain (fail closed)
    - answer empty after normalisation   -> meaning_not_preserved (nothing was
      submitted to preserve the source's meaning — never a false positive on a
      real, non-empty correction)
    - normalised answer == normalised source -> source_unchanged (returned as-is)
    - otherwise                          -> source_comparison_uncertain

    `meaning_not_preserved` is emitted ONLY on the empty-answer case. Semantic
    "is this a meaning-preserving correction" is NOT deterministically decidable
    from (answer, source) — any string-similarity / token-overlap threshold is
    gameable and false-positives on aggressive-but-correct rewrites (rejected in
    the adapter doc §2). So every non-trivial changed answer falls to
    `source_comparison_uncertain` and is routed to human review rather than
    guessed at.
    """
    if not _is_source_dependent(exercise_type):
        return None
    norm_source = _normalize_for_compare(source_text)
    if not norm_source:
        return "source_comparison_uncertain"
    norm_answer = _normalize_for_compare(answer_text)
    if not norm_answer:
        return "meaning_not_preserved"
    if norm_answer == norm_source:
        return "source_unchanged"
    return "source_comparison_uncertain"

# The §5.1 issue-type taxonomy. These map to canonical microtopics backend-side
# (§4.15); the evaluator returns only the issue_type, never taxonomy IDs.
IssueType = Literal[
    "sentence_fragment",
    "run_on_sentence",
    "subject_verb_agreement",
    "tense",
    "article",
    "preposition",
    "pronoun_reference",
    "modifier",
    "spelling",
    "punctuation",
    "word_choice",
    "collocation",
    "redundancy",
    "informal_usage",
    "cohesion",
    "logical_order",
    "off_topic",
    "word_limit",
    "format_violation",
]

Severity = Literal["advisory", "should_fix", "must_fix"]

# Small deterministic lexicon for the informal-usage rule.
_INFORMAL_TOKENS = frozenset({"gonna", "wanna", "gotta", "kinda", "stuff", "thing"})

# A sentence with no internal period and more than this many words is flagged as
# a run-on sentence.
_RUN_ON_WORD_THRESHOLD = 45


class LanguageIssueOut(BaseModel):
    """One structured language finding (§5.3), persisted to writing_issue_events."""

    model_config = ConfigDict(extra="forbid")

    issue_type: IssueType
    span_start_utf16: int = 0
    span_end_utf16: int = 0
    quoted_text: str
    original_text: str | None = None
    suggested_text: str | None = None
    explanation: str
    severity: Severity
    # When set, links this issue to a prior-version issue for lineage (§4.8a).
    # Validated against active_prior_issues ids in ``evaluate_language``.
    predecessor_issue_event_id: str | None = None

    @model_validator(mode="after")
    def _check_span(self) -> "LanguageIssueOut":
        if self.span_start_utf16 < 0 or self.span_end_utf16 < 0:
            raise ValueError("UTF-16 spans must be non-negative")
        if self.span_end_utf16 < self.span_start_utf16:
            raise ValueError("span_end_utf16 must be >= span_start_utf16")
        return self


def utf16_span(text: str, substring: str, start_char: int = 0) -> tuple[int, int] | None:
    """Locate ``substring`` in ``text`` and return its (start, end) UTF-16 offsets.

    ``start_char`` is a Python character index at which to begin searching.
    Returns None when the substring is not found. Offsets are UTF-16 code-unit
    counts (encode the char prefix as UTF-16-LE and divide by 2), matching
    JavaScript string indexing so ``text.sliceUTF16(start, end) == substring``.
    """
    char_idx = text.find(substring, start_char)
    if char_idx < 0:
        return None
    start = len(text[:char_idx].encode("utf-16-le")) // 2
    end = start + len(substring.encode("utf-16-le")) // 2
    return start, end


@dataclass
class LanguageResult:
    """Structured Stage-2 result (persisted as writing_evaluations.language_result)."""

    issues: list[LanguageIssueOut]
    evaluator_version: str = LANGUAGE_EVALUATOR_VERSION
    # EWP-SP1: deterministic source-comparison verdict (None when the exercise is
    # not source-dependent). Any non-None value forces needs_human_review.
    source_comparison: SourceComparison | None = None
    # Fail-closed routing flag. When True the worker sets needs_human_review on
    # the evaluation and emits NO positive/negative mastery evidence.
    needs_human_review: bool = False

    def to_result_dict(self) -> dict:
        """Serialised language_result payload persisted on the evaluation row."""
        return {
            "issues": self.to_issue_dicts(),
            "evaluator_version": self.evaluator_version,
            "source_comparison": self.source_comparison,
            "needs_human_review": self.needs_human_review,
        }

    def to_issue_dicts(self) -> list[dict]:
        """Return each issue as a plain dict with the fixed §5.3 key order."""
        return [
            {
                "issue_type": issue.issue_type,
                "span_start_utf16": issue.span_start_utf16,
                "span_end_utf16": issue.span_end_utf16,
                "quoted_text": issue.quoted_text,
                "original_text": issue.original_text,
                "suggested_text": issue.suggested_text,
                "explanation": issue.explanation,
                "severity": issue.severity,
                "predecessor_issue_event_id": issue.predecessor_issue_event_id,
            }
            for issue in self.issues
        ]


class LanguageEvaluator(Protocol):
    """Adapter boundary for Stage-2 language evaluation."""

    def evaluate(
        self,
        answer_text: str,
        *,
        exercise_type: str,
        prompt_text: str | None = None,
        source_text: str | None = None,
        active_prior_issues: list[dict] | None = None,
        resolved_prior_lineages: list[dict] | None = None,
    ) -> LanguageResult:
        ...


class MockLanguageEvaluator:
    """Deterministic rule-based mock (no randomness, no time, no network).

    Detection rules (each maps to a §5.1 issue_type):

    - double space ``"  "`` → ``punctuation`` (should_fix)
    - lowercase first letter of the whole answer → ``punctuation`` (should_fix)
    - an informal token from ``_INFORMAL_TOKENS`` → ``informal_usage`` (should_fix)
    - a sentence > 45 words with no internal period → ``run_on_sentence`` (must_fix)
    - the bigrams ``he/she/it are`` or ``they is`` → ``subject_verb_agreement`` (must_fix)

    Findings are sorted by ``span_start_utf16``. Lineage: when a detected issue's
    ``quoted_text`` matches an ``active_prior_issues`` item of the same
    issue_type, ``predecessor_issue_event_id`` is set to that item's id.
    """

    def evaluate(
        self,
        answer_text: str,
        *,
        exercise_type: str,
        prompt_text: str | None = None,
        source_text: str | None = None,
        active_prior_issues: list[dict] | None = None,
        resolved_prior_lineages: list[dict] | None = None,
    ) -> LanguageResult:
        issues: list[LanguageIssueOut] = []

        # Rule: double space.
        span = utf16_span(answer_text, "  ")
        if span is not None:
            issues.append(
                LanguageIssueOut(
                    issue_type="punctuation",
                    span_start_utf16=span[0],
                    span_end_utf16=span[1],
                    quoted_text="  ",
                    explanation="Remove the duplicated space.",
                    severity="should_fix",
                )
            )

        # Rule: lowercase first letter of the whole answer.
        stripped = answer_text.lstrip()
        if stripped and stripped[0].isalpha() and stripped[0].islower():
            offset = len(answer_text) - len(stripped)
            span = utf16_span(answer_text, stripped[0], start_char=offset)
            if span is not None:
                issues.append(
                    LanguageIssueOut(
                        issue_type="punctuation",
                        span_start_utf16=span[0],
                        span_end_utf16=span[1],
                        quoted_text=stripped[0],
                        suggested_text=stripped[0].upper(),
                        explanation="Begin the sentence with a capital letter.",
                        severity="should_fix",
                    )
                )

        # Rule: informal usage. Scan tokens deterministically, first hit per token.
        seen_starts: set[int] = set()
        for token in deterministic.tokenize_words(answer_text):
            if token.casefold() in _INFORMAL_TOKENS:
                span = utf16_span(answer_text, token)
                if span is not None and span[0] not in seen_starts:
                    seen_starts.add(span[0])
                    issues.append(
                        LanguageIssueOut(
                            issue_type="informal_usage",
                            span_start_utf16=span[0],
                            span_end_utf16=span[1],
                            quoted_text=token,
                            explanation="Avoid informal vocabulary in formal writing.",
                            severity="should_fix",
                        )
                    )

        # Rule: subject-verb agreement on naive bigrams.
        lowered = answer_text.lower()
        for phrase in ("he are", "she are", "it are", "they is"):
            idx = lowered.find(phrase)
            if idx >= 0:
                quoted = answer_text[idx : idx + len(phrase)]
                span = utf16_span(answer_text, quoted, start_char=idx)
                if span is not None:
                    issues.append(
                        LanguageIssueOut(
                            issue_type="subject_verb_agreement",
                            span_start_utf16=span[0],
                            span_end_utf16=span[1],
                            quoted_text=quoted,
                            explanation="The subject and verb do not agree in number.",
                            severity="must_fix",
                        )
                    )

        # Rule: run-on sentence (> threshold words, no internal period).
        search_from = 0
        for sentence in _split_sentences(answer_text):
            span = utf16_span(answer_text, sentence, start_char=search_from)
            if span is not None:
                search_from = answer_text.find(sentence, search_from) + len(sentence)
            if "." not in sentence and deterministic.word_count(sentence) > _RUN_ON_WORD_THRESHOLD:
                if span is not None:
                    issues.append(
                        LanguageIssueOut(
                            issue_type="run_on_sentence",
                            span_start_utf16=span[0],
                            span_end_utf16=span[1],
                            quoted_text=sentence,
                            explanation="Split this overly long sentence.",
                            severity="must_fix",
                        )
                    )

        # Lineage: link detected issues to matching prior active issues.
        _apply_lineage(issues, active_prior_issues or [])

        issues.sort(key=lambda i: i.span_start_utf16)

        # EWP-SP1: deterministic source-comparison. Only meaningful for
        # source-dependent exercise types; construction prompts get None and are
        # unaffected. Any verdict fails CLOSED to human review.
        source_comparison = compute_source_comparison(
            answer_text, exercise_type=exercise_type, source_text=source_text,
        )
        return LanguageResult(
            issues=issues,
            evaluator_version=LANGUAGE_EVALUATOR_VERSION,
            source_comparison=source_comparison,
            needs_human_review=source_comparison is not None,
        )


def _split_sentences(text: str) -> list[str]:
    """Split on newlines (coarse boundary that keeps periodless run-ons intact)."""
    return [seg for seg in text.split("\n") if seg.strip()]


def _apply_lineage(issues: list[LanguageIssueOut], active_prior_issues: list[dict]) -> None:
    for issue in issues:
        for prior in active_prior_issues:
            if (
                prior.get("issue_type") == issue.issue_type
                and prior.get("quoted_text") == issue.quoted_text
            ):
                issue.predecessor_issue_event_id = prior.get("issue_event_id")
                break


FlagState = Literal["off", "shadow", "live"]


def get_writing_llm_eval_flag() -> FlagState:
    """Resolve FF_WRITING_LLM_EVAL. Fails CLOSED to ``off``.

    SCAFFOLD ONLY (EWP-SP1): no real semantic/LLM adapter ships in this slice.
    The flag exists so the off→shadow→live rollout plumbing is in place; the
    real model adapter is gated on docs/architecture/ewp-semantic-evaluator-adapter.md
    being APPROVED (still a PROPOSAL). Default and effective value today is ``off``.
    """
    raw = (os.getenv("FF_WRITING_LLM_EVAL") or "off").strip().lower()
    return raw if raw in {"off", "shadow", "live"} else "off"  # fail closed


class LlmLanguageEvaluator:
    """STUB semantic/LLM adapter slot — NOT IMPLEMENTED in this slice.

    Deliberately holds no model client, makes no network call, and adds no
    dependency. It exists only to mark the adapter seam. It is NEVER instantiated
    or invoked while FF_WRITING_LLM_EVAL is off (the effective value today);
    reaching it is a bug, so every method fails loudly.
    """

    def evaluate(self, *args, **kwargs) -> LanguageResult:  # noqa: D401
        raise NotImplementedError(
            "LlmLanguageEvaluator is a scaffold stub — the semantic adapter is "
            "gated on ewp-semantic-evaluator-adapter.md APPROVAL and is never "
            "invoked while FF_WRITING_LLM_EVAL=off"
        )


def _build_llm_evaluator() -> LanguageEvaluator:
    """Construct the SHADOW semantic adapter (EWP-SP1b).

    Isolated so tests can observe it is never called on the off path. Imported
    lazily to avoid a hard dependency on the provider SDK for the deterministic
    path and to break the language_evaluator <-> semantic_evaluator import cycle.
    Authorized in SHADOW mode only by
    docs/architecture/ewp-semantic-evaluator-adapter.md; this adapter is reached
    exclusively through get_semantic_shadow_evaluator() when
    FF_WRITING_LLM_EVAL=shadow, and its output never feeds the canonical
    completion RPC.
    """
    from . import semantic_evaluator

    return semantic_evaluator.build_semantic_evaluator()


def get_semantic_shadow_evaluator() -> LanguageEvaluator | None:
    """Return the shadow-only semantic evaluator when FF_WRITING_LLM_EVAL=shadow.

    This is deliberately separate from get_language_evaluator(): the primary
    evaluator remains deterministic because the worker persists its result
    through ewp_complete_language_evaluation. Shadow output must be measured
    separately and must not become authoritative lifecycle/mastery input.
    """
    if get_writing_llm_eval_flag() != "shadow":
        return None
    return _build_llm_evaluator()


def get_language_evaluator() -> LanguageEvaluator:
    """Return the active language evaluator.

    While FF_WRITING_LLM_EVAL is ``off`` (the only supported value this slice),
    this returns the deterministic mock and NEVER touches the LLM stub. Any
    non-off flag also falls back to the mock for now (no approved adapter) — a
    non-off flag is a no-op until the adapter doc is approved; the stub is only
    constructed once that lands.
    """
    flag = get_writing_llm_eval_flag()
    if flag != "off":
        logger.warning(
            "FF_WRITING_LLM_EVAL=%s but no approved semantic adapter — using the "
            "deterministic mock (scaffold only)", flag,
        )
    return MockLanguageEvaluator()


def evaluate_language(
    answer_text: str,
    *,
    exercise_type: str,
    prompt_text: str | None = None,
    source_text: str | None = None,
    active_prior_issues: list[dict] | None = None,
    resolved_prior_lineages: list[dict] | None = None,
) -> LanguageResult:
    """Evaluate ``answer_text`` and return structured language findings.

    ``prompt_text`` / ``source_text`` come from the immutable per-session snapshot
    (migration 221/222) and enable deterministic source-comparison for
    source-dependent exercise types (EWP-SP1). Both default to None so existing
    callers stay backward-compatible.

    ``active_prior_issues`` items look like
    ``{"issue_event_id": str, "issue_type": str, "quoted_text": str}``. Any
    ``predecessor_issue_event_id`` on a returned issue must reference one of
    those ids; a mismatch raises ``ValueError`` (§4.8a — the backend validates
    every referenced id before assigning lineage).
    """
    result = get_language_evaluator().evaluate(
        answer_text,
        exercise_type=exercise_type,
        prompt_text=prompt_text,
        source_text=source_text,
        active_prior_issues=active_prior_issues,
        resolved_prior_lineages=resolved_prior_lineages,
    )

    allowed_ids = {p.get("issue_event_id") for p in (active_prior_issues or [])}
    for issue in result.issues:
        if (
            issue.predecessor_issue_event_id is not None
            and issue.predecessor_issue_event_id not in allowed_ids
        ):
            raise ValueError(
                "predecessor_issue_event_id "
                f"{issue.predecessor_issue_event_id!r} is not in active_prior_issues"
            )
    return result
