"""Tests for the deterministic Stage-2 language evaluator (§5.1, §5.3)."""
import pytest

pytest.importorskip("pydantic")

from pydantic import ValidationError

from app.study_os.writing_practice.language_evaluator import (
    LANGUAGE_EVALUATOR_VERSION,
    LanguageIssueOut,
    evaluate_language,
    utf16_span,
)

_ISSUE_DICT_KEYS = [
    "issue_type",
    "span_start_utf16",
    "span_end_utf16",
    "quoted_text",
    "original_text",
    "suggested_text",
    "explanation",
    "severity",
    "predecessor_issue_event_id",
]


def test_determinism_identical_output_twice():
    text = "they is gonna break  things\n" + "word " * 50
    a = evaluate_language(text, exercise_type="paragraph_writing")
    b = evaluate_language(text, exercise_type="paragraph_writing")
    assert a.to_issue_dicts() == b.to_issue_dicts()
    assert a.evaluator_version == LANGUAGE_EVALUATOR_VERSION


def test_bad_issue_type_raises():
    with pytest.raises(ValidationError):
        LanguageIssueOut(
            issue_type="not_a_real_type",
            span_start_utf16=0,
            span_end_utf16=1,
            quoted_text="x",
            explanation="e",
            severity="must_fix",
        )


def test_extra_forbid_rejection():
    with pytest.raises(ValidationError):
        LanguageIssueOut(
            issue_type="punctuation",
            span_start_utf16=0,
            span_end_utf16=1,
            quoted_text="x",
            explanation="e",
            severity="must_fix",
            unexpected_field=1,
        )


def test_span_end_before_start_raises():
    with pytest.raises(ValidationError):
        LanguageIssueOut(
            issue_type="punctuation",
            span_start_utf16=5,
            span_end_utf16=2,
            quoted_text="x",
            explanation="e",
            severity="must_fix",
        )


def test_utf16_span_with_non_bmp_emoji():
    # "😀" is a non-BMP char: len()==1 in Python but 2 UTF-16 code units.
    text = "😀 he are wrong"
    result = evaluate_language(text, exercise_type="sentence_correction")
    sva = [i for i in result.issues if i.issue_type == "subject_verb_agreement"]
    assert len(sva) == 1
    issue = sva[0]
    # UTF-16 slice must equal quoted_text (frontend contract §4.5b).
    utf16 = text.encode("utf-16-le")
    sliced = utf16[issue.span_start_utf16 * 2 : issue.span_end_utf16 * 2].decode(
        "utf-16-le"
    )
    assert sliced == issue.quoted_text == "he are"
    # Emoji is 2 code units, so "he" starts at offset 3, not 2.
    assert issue.span_start_utf16 == 3


def test_utf16_span_helper_not_found():
    assert utf16_span("hello", "zzz") is None


def test_predecessor_lineage_linking():
    text = "gonna win"
    prior = [
        {
            "issue_event_id": "evt-123",
            "issue_type": "informal_usage",
            "quoted_text": "gonna",
        }
    ]
    result = evaluate_language(
        text, exercise_type="paragraph_writing", active_prior_issues=prior
    )
    informal = [i for i in result.issues if i.issue_type == "informal_usage"]
    assert len(informal) == 1
    assert informal[0].predecessor_issue_event_id == "evt-123"


def test_no_lineage_when_no_prior_match():
    result = evaluate_language("gonna win", exercise_type="paragraph_writing")
    informal = [i for i in result.issues if i.issue_type == "informal_usage"]
    assert informal[0].predecessor_issue_event_id is None


def test_double_space_and_lowercase_start_detected():
    result = evaluate_language("this  text", exercise_type="paragraph_writing")
    types = [i.issue_type for i in result.issues]
    assert types.count("punctuation") == 2  # lowercase start + double space
    # Sorted by span start.
    starts = [i.span_start_utf16 for i in result.issues]
    assert starts == sorted(starts)


def test_run_on_sentence_detected():
    long_sentence = " ".join(["word"] * 50)
    result = evaluate_language(long_sentence, exercise_type="paragraph_writing")
    assert any(i.issue_type == "run_on_sentence" for i in result.issues)
    assert any(i.severity == "must_fix" for i in result.issues)


def test_to_issue_dicts_shape():
    result = evaluate_language("they is here", exercise_type="sentence_correction")
    dicts = result.to_issue_dicts()
    assert dicts, "expected at least one issue"
    for d in dicts:
        assert list(d.keys()) == _ISSUE_DICT_KEYS


def test_invalid_predecessor_reference_raises(monkeypatch):
    # Force the mock to emit a bogus predecessor not in active_prior_issues.
    import app.study_os.writing_practice.language_evaluator as le

    real = le.MockLanguageEvaluator.evaluate

    def patched(self, answer_text, **kwargs):
        res = real(self, answer_text, **kwargs)
        if res.issues:
            res.issues[0].predecessor_issue_event_id = "ghost-id"
        return res

    monkeypatch.setattr(le.MockLanguageEvaluator, "evaluate", patched)
    with pytest.raises(ValueError):
        evaluate_language("gonna win", exercise_type="paragraph_writing")
