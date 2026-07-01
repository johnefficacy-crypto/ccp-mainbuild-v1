"""Stage-3 rubric evaluator (architecture §5.4) — DETERMINISTIC MOCK.

Pure, synchronous, no external calls, no database access. Provides the
per-dimension score contract (§5.4) with confidence gating and a deterministic
mock scorer standing in for the async LLM adapter (deferred to a later slice).
No randomness, no time, no network.

Dimension keys come from ``writing_rubrics.dimensions`` (§4.13) — no rubric
labels are hardcoded here. Nothing here touches the database — callers persist
the results.
"""
from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, model_validator

from . import deterministic

# Bump when the mock scoring formula or output contract changes; stored on the
# evaluation row alongside dimension_scores so historical scores stay auditable.
RUBRIC_EVALUATOR_VERSION = "rubric-mock-v1"

# Confidence gating thresholds (§5.4).
_RANGE_THRESHOLD = 0.6  # below → emit a range instead of a point estimate
_HUMAN_REVIEW_THRESHOLD = 0.5  # any dimension below → needs_human_review


class DimensionScoreOut(BaseModel):
    """One rubric dimension's score with confidence gating (§5.4)."""

    model_config = ConfigDict(extra="forbid")

    key: str
    score: float | None = None
    score_min: float | None = None
    score_max: float | None = None
    confidence: float
    rationale: str | None = None

    @model_validator(mode="after")
    def _check_confidence(self) -> "DimensionScoreOut":
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be within [0, 1]")
        if self.confidence < _RANGE_THRESHOLD:
            # Low confidence: a range must be present; a point estimate is optional.
            if self.score_min is None or self.score_max is None:
                raise ValueError(
                    "low-confidence dimension must supply score_min and score_max"
                )
            if self.score_max < self.score_min:
                raise ValueError("score_max must be >= score_min")
        else:
            if self.score is None:
                raise ValueError("high-confidence dimension must supply a point score")
        return self


@dataclass
class RubricResult:
    """Structured Stage-3 result (persisted as writing_evaluations.dimension_scores)."""

    dimension_scores: list[DimensionScoreOut]
    needs_human_review: bool
    evaluator_version: str = RUBRIC_EVALUATOR_VERSION

    def to_dict(self) -> dict:
        return {
            "dimensions": [d.model_dump() for d in self.dimension_scores],
            "needs_human_review": self.needs_human_review,
            "evaluator_version": self.evaluator_version,
        }


def _quality_fraction(word_count: int, sentence_count: int) -> float:
    """Deterministic base-quality fraction in [0, 1].

    Formula (documented, deterministic): reward text with enough words and a
    healthy words-per-sentence balance. Empty text scores 0. Grows with word
    count up to a plateau at 120 words; a words-per-sentence ratio near 15 is
    ideal, penalised as it drifts away.
    """
    if word_count == 0:
        return 0.0
    length_component = min(word_count / 120.0, 1.0)
    if sentence_count == 0:
        balance_component = 0.5
    else:
        wps = word_count / sentence_count
        balance_component = max(0.0, 1.0 - abs(wps - 15.0) / 15.0)
    return max(0.0, min(1.0, 0.6 * length_component + 0.4 * balance_component))


def _confidence(word_count: int) -> float:
    """Deterministic confidence in [0, 1] — higher for longer text.

    Very short answers are uncertain; confidence climbs to ~1.0 by 80 words.
    """
    return max(0.0, min(1.0, word_count / 80.0))


def evaluate_rubric(answer_text: str, *, dimensions: list[dict]) -> RubricResult:
    """Score ``answer_text`` against ``dimensions`` (each ``{"key", "max_score"}``).

    Deterministic mock: a base quality fraction (from word/sentence counts) is
    scaled by each dimension's ``max_score`` and clamped to ``[0, max_score]``.
    Confidence is derived from length. When confidence < 0.6 a range is emitted
    instead of a point; when any dimension's confidence < 0.5 the result is
    flagged ``needs_human_review``.
    """
    wc = deterministic.word_count(answer_text)
    sc = deterministic.sentence_count(answer_text)
    quality = _quality_fraction(wc, sc)
    confidence = _confidence(wc)

    scores: list[DimensionScoreOut] = []
    needs_human_review = False
    for dim in dimensions:
        key = dim["key"]
        max_score = float(dim["max_score"])
        point = max(0.0, min(max_score, quality * max_score))

        if confidence < _HUMAN_REVIEW_THRESHOLD:
            needs_human_review = True

        if confidence < _RANGE_THRESHOLD:
            # Emit a symmetric range around the point estimate, clamped.
            margin = max_score * (1.0 - confidence) * 0.25
            scores.append(
                DimensionScoreOut(
                    key=key,
                    score=None,
                    score_min=max(0.0, point - margin),
                    score_max=min(max_score, point + margin),
                    confidence=confidence,
                    rationale="Low confidence: score reported as a range.",
                )
            )
        else:
            scores.append(
                DimensionScoreOut(
                    key=key,
                    score=point,
                    confidence=confidence,
                    rationale="Deterministic mock score from length and balance.",
                )
            )

    return RubricResult(
        dimension_scores=scores,
        needs_human_review=needs_human_review,
        evaluator_version=RUBRIC_EVALUATOR_VERSION,
    )
