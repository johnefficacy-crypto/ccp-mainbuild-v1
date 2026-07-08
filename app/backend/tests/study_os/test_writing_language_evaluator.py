"""Tests for the deterministic Stage-2 language evaluator (§5.1, §5.3)."""
import pytest

pytest.importorskip("pydantic")

from pydantic import ValidationError

import app.study_os.writing_practice.language_evaluator as le
from app.study_os.writing_practice.language_evaluator import (
    LANGUAGE_EVALUATOR_VERSION,
    LanguageIssueOut,
    compute_source_comparison,
    evaluate_language,
    get_language_evaluator,
    get_writing_llm_eval_flag,
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


# --- EWP-SP1: deterministic source-comparison result states ----------------


def test_evaluator_version_bumped():
    # Historical fixtures are keyed on the version; the source-aware change bumps it.
    assert LANGUAGE_EVALUATOR_VERSION == "lang-mock-v2"


def test_source_unchanged_detected_and_fails_closed():
    source = "He go to school every day."
    # Learner returns the sentence unchanged (only whitespace/case noise differs).
    result = evaluate_language(
        "  he GO to school every day.  ",
        exercise_type="sentence_correction",
        source_text=source,
    )
    assert result.source_comparison == "source_unchanged"
    assert result.needs_human_review is True


def test_meaning_not_preserved_only_on_empty_answer():
    # An empty answer for a source-dependent task cannot preserve meaning — this is
    # the ONLY deterministic meaning_not_preserved trigger (no similarity heuristic).
    result = evaluate_language(
        "   ", exercise_type="sentence_correction", source_text="He go home.",
    )
    assert result.source_comparison == "meaning_not_preserved"
    assert result.needs_human_review is True


def test_no_false_positive_meaning_not_preserved_on_real_correction():
    # A genuine, heavily-reworded correction must NOT be flagged meaning_not_preserved
    # (that was the gameable-threshold trap). It falls to uncertain -> human review.
    result = evaluate_language(
        "He runs quickly.",
        exercise_type="sentence_correction",
        source_text="Him fast run.",
    )
    assert result.source_comparison == "source_comparison_uncertain"
    assert result.needs_human_review is True


def test_uncertain_fails_closed_to_review():
    result = evaluate_language(
        "He goes to school every day.",
        exercise_type="sentence_correction",
        source_text="He go to school every day.",
    )
    assert result.source_comparison == "source_comparison_uncertain"
    assert result.needs_human_review is True


def test_missing_source_on_source_dependent_fails_closed():
    for missing in (None, "", "   "):
        result = evaluate_language(
            "He goes home.", exercise_type="sentence_correction", source_text=missing,
        )
        assert result.source_comparison == "source_comparison_uncertain"
        assert result.needs_human_review is True


def test_off_topic_not_emitted_for_source_mismatch():
    # Source mismatch must NEVER reuse off_topic (would contaminate content-relevance
    # mastery, PR #882). The verdict lives at the result level, not as an issue.
    result = evaluate_language(
        "Totally different clean sentence here.",
        exercise_type="sentence_correction",
        source_text="He go to school.",
    )
    assert all(i.issue_type != "off_topic" for i in result.issues)
    assert result.source_comparison == "source_comparison_uncertain"


def test_construction_prompts_unaffected_by_source_comparison():
    # Pure construction has no source; source-comparison is skipped, no review gate.
    result = evaluate_language(
        "The cat sat on the mat.",
        exercise_type="sentence_construction",
        source_text=None,
    )
    assert result.source_comparison is None
    assert result.needs_human_review is False
    # Even if a stray source is supplied, a construction type is never gated.
    result2 = evaluate_language(
        "The cat sat.", exercise_type="sentence_construction", source_text="unused",
    )
    assert result2.source_comparison is None
    assert result2.needs_human_review is False


def test_compute_source_comparison_pure_function():
    assert compute_source_comparison(
        "x", exercise_type="paragraph_writing", source_text="x") is None
    assert compute_source_comparison(
        "abc", exercise_type="grammar_fix", source_text="abc") == "source_unchanged"


def test_result_dict_carries_source_comparison():
    result = evaluate_language(
        "he go to school.", exercise_type="sentence_correction",
        source_text="he go to school.",
    )
    payload = result.to_result_dict()
    assert payload["source_comparison"] == "source_unchanged"
    assert payload["needs_human_review"] is True
    assert payload["evaluator_version"] == LANGUAGE_EVALUATOR_VERSION


# --- EWP-SP1: FF_WRITING_LLM_EVAL scaffold (off by default, stub never called) --


def test_ff_writing_llm_eval_defaults_off(monkeypatch):
    monkeypatch.delenv("FF_WRITING_LLM_EVAL", raising=False)
    assert get_writing_llm_eval_flag() == "off"
    # Garbage / unknown values fail closed to off.
    monkeypatch.setenv("FF_WRITING_LLM_EVAL", "banana")
    assert get_writing_llm_eval_flag() == "off"


def test_llm_stub_never_built_or_called_when_off(monkeypatch):
    monkeypatch.delenv("FF_WRITING_LLM_EVAL", raising=False)
    calls = {"built": 0}

    def _spy():
        calls["built"] += 1
        return le.LlmLanguageEvaluator()

    monkeypatch.setattr(le, "_build_llm_evaluator", _spy)
    ev = get_language_evaluator()
    assert isinstance(ev, le.MockLanguageEvaluator)
    # Full evaluation path must not construct or invoke the LLM stub.
    evaluate_language("he go home.", exercise_type="sentence_correction",
                      source_text="he go home.")
    assert calls["built"] == 0


def test_llm_stub_raises_if_ever_invoked():
    with pytest.raises(NotImplementedError):
        le.LlmLanguageEvaluator().evaluate("x", exercise_type="sentence_correction")


def test_non_off_flag_still_uses_mock_no_stub(monkeypatch):
    # Scaffold only: even shadow/live fall back to the mock (no approved adapter),
    # and never touch the stub in this slice.
    monkeypatch.setenv("FF_WRITING_LLM_EVAL", "shadow")
    assert isinstance(get_language_evaluator(), le.MockLanguageEvaluator)

def test_shadow_semantic_probe_is_separate_from_primary_evaluator(monkeypatch):
    monkeypatch.setenv("FF_WRITING_LLM_EVAL", "shadow")

    # Primary evaluator must stay deterministic because the worker persists this
    # result through ewp_complete_language_evaluation.
    primary = get_language_evaluator()
    assert isinstance(primary, le.MockLanguageEvaluator)

    # SP1b wires the real provider-backed semantic adapter behind this shadow
    # seam (superseding the SP1a stub). Its output must be measured/recorded
    # separately, never returned as the primary evaluator.
    from app.study_os.writing_practice import semantic_evaluator as se

    shadow = le.get_semantic_shadow_evaluator()
    assert isinstance(shadow, se.SemanticLanguageEvaluator)

def test_semantic_shadow_evaluator_none_when_off(monkeypatch):
    monkeypatch.delenv("FF_WRITING_LLM_EVAL", raising=False)
    assert le.get_semantic_shadow_evaluator() is None


def test_semantic_shadow_evaluator_not_enabled_for_live(monkeypatch):
    monkeypatch.setenv("FF_WRITING_LLM_EVAL", "live")
    assert le.get_semantic_shadow_evaluator() is None
    assert isinstance(get_language_evaluator(), le.MockLanguageEvaluator)
