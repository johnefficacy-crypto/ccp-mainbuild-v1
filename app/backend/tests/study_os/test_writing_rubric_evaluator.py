"""Tests for the deterministic Stage-3 rubric evaluator (§5.4)."""
import pytest

pytest.importorskip("pydantic")

from pydantic import ValidationError

from app.study_os.writing_practice.rubric_evaluator import (
    RUBRIC_EVALUATOR_VERSION,
    DimensionScoreOut,
    evaluate_rubric,
)

_DIMS = [
    {"key": "grammar_accuracy", "max_score": 10.0},
    {"key": "coherence", "max_score": 10.0},
]


def test_determinism_identical_output_twice():
    text = " ".join(["Sentence here."] * 30)
    a = evaluate_rubric(text, dimensions=_DIMS)
    b = evaluate_rubric(text, dimensions=_DIMS)
    assert a.to_dict() == b.to_dict()
    assert a.evaluator_version == RUBRIC_EVALUATOR_VERSION


def test_high_confidence_point_estimate():
    # Long text → high confidence → point score, no range.
    text = " ".join(["The scheme is useful and clear."] * 40)
    result = evaluate_rubric(text, dimensions=_DIMS)
    assert result.needs_human_review is False
    for d in result.dimension_scores:
        assert d.score is not None
        assert d.score_min is None and d.score_max is None
        assert 0.0 <= d.score <= 10.0


def test_low_confidence_range_branch():
    # Medium-short text: confidence in [0.5, 0.6) → range, not needs_review.
    text = " ".join(["word"] * 44)  # 44/80 = 0.55 confidence
    result = evaluate_rubric(text, dimensions=_DIMS)
    assert result.needs_human_review is False
    for d in result.dimension_scores:
        assert d.score is None
        assert d.score_min is not None and d.score_max is not None
        assert d.score_max >= d.score_min


def test_needs_human_review_branch():
    # Very short text → confidence < 0.5 → needs_human_review.
    result = evaluate_rubric("too short", dimensions=_DIMS)
    assert result.needs_human_review is True


def test_to_dict_shape():
    result = evaluate_rubric("some answer text here", dimensions=_DIMS)
    d = result.to_dict()
    assert set(d.keys()) == {"dimensions", "needs_human_review", "evaluator_version"}
    assert isinstance(d["dimensions"], list)


def test_extra_forbid_rejection():
    with pytest.raises(ValidationError):
        DimensionScoreOut(key="k", score=5.0, confidence=0.9, oops=1)


def test_low_confidence_requires_range():
    with pytest.raises(ValidationError):
        DimensionScoreOut(key="k", score=5.0, confidence=0.3)


def test_high_confidence_requires_point():
    with pytest.raises(ValidationError):
        DimensionScoreOut(key="k", score_min=1.0, score_max=2.0, confidence=0.9)


def test_confidence_out_of_range_raises():
    with pytest.raises(ValidationError):
        DimensionScoreOut(key="k", score=5.0, confidence=1.5)
