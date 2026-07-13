"""Stream-aware evaluation of the new baseline rule_types (Lane R §4 activation).

Covers discipline / min_percentage / certification / qualification_combination /
stream_availability, the four-state contract, and the per-stream breakdown.
"""
from __future__ import annotations

from app.exam_eligibility.evaluator import (
    evaluate_exam_for_user,
    _eval_qualification_combination,
    summarize_user_eligibility,
    invalidate_eligibility_rules_cache,
)
from tests.persona_questions._stub import SBStub


def _r(rule_type, **kw):
    row = {"scope": "all", "rule_type": rule_type, "value_num": None,
           "value_text": None, "value_json": None, "is_knockout": True, "stream_id": None}
    row.update(kw)
    return row


# ── discipline ─────────────────────────────────────────────────────────────


def test_discipline_pass_is_eligible():
    out = evaluate_exam_for_user([_r("discipline", value_text="LLB")], {"disciplines": ["B.A. LLB"]})
    assert out["status"] == "eligible"


def test_discipline_mismatch_is_not_eligible():
    out = evaluate_exam_for_user([_r("discipline", value_text="LLB")], {"disciplines": ["B.Sc Physics"]})
    assert out["status"] == "not_eligible"


def test_discipline_missing_is_conditional():
    out = evaluate_exam_for_user([_r("discipline", value_text="LLB")], {})
    assert out["status"] == "conditional"
    assert "disciplines" in out["missing_fields"]


# ── min_percentage ─────────────────────────────────────────────────────────


def test_min_percentage_pass_and_fail_and_missing():
    rule = [_r("min_percentage", value_num=60)]
    assert evaluate_exam_for_user(rule, {"best_percentage": 65})["status"] == "eligible"
    assert evaluate_exam_for_user(rule, {"best_percentage": 55})["status"] == "not_eligible"
    assert evaluate_exam_for_user(rule, {})["status"] == "conditional"


# ── certification ──────────────────────────────────────────────────────────


def test_certification_pass_and_fail():
    rule = [_r("certification", value_text="Bar Council")]
    assert evaluate_exam_for_user(rule, {"certifications": ["Bar Council of India"]})["status"] == "eligible"
    assert evaluate_exam_for_user(rule, {"certifications": ["First Aid"]})["status"] == "not_eligible"
    assert evaluate_exam_for_user(rule, {})["status"] == "conditional"


# ── stream_availability ────────────────────────────────────────────────────


def test_stream_not_offered_is_not_eligible():
    out = evaluate_exam_for_user([_r("stream_availability", value_text="not_offered")], {})
    assert out["status"] == "not_eligible"


# ── qualification_combination ──────────────────────────────────────────────


_QC = {"op": "and", "clauses": [
    {"rule_type": "discipline", "value_text": "LLB"},
    {"rule_type": "min_percentage", "value_num": 60},
]}


def test_qualification_combination_and_pass_fail_missing():
    rule = [_r("qualification_combination", value_json=_QC)]
    assert evaluate_exam_for_user(rule, {"disciplines": ["LLB"], "best_percentage": 70})["status"] == "eligible"
    assert evaluate_exam_for_user(rule, {"disciplines": ["LLB"], "best_percentage": 50})["status"] == "not_eligible"
    assert evaluate_exam_for_user(rule, {"disciplines": ["LLB"]})["status"] == "conditional"


def test_qualification_combination_or_semantics():
    node = {"op": "or", "clauses": [
        {"rule_type": "discipline", "value_text": "LLB"},
        {"rule_type": "certification", "value_text": "CA"},
    ]}
    assert _eval_qualification_combination(node, {"disciplines": ["LLB"], "certifications": []}) == "pass"
    assert _eval_qualification_combination(node, {"disciplines": ["B.Sc"], "certifications": ["CA"]}) == "pass"
    assert _eval_qualification_combination(node, {"disciplines": ["B.Sc"], "certifications": ["X"]}) == "fail"
    # one clause missing, none pass -> missing
    assert _eval_qualification_combination(node, {"disciplines": ["B.Sc"]}) == "missing"


# ── per-stream breakdown in summarize ──────────────────────────────────────


def test_summarize_includes_per_stream_breakdown():
    exam = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    stream = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
    invalidate_eligibility_rules_cache()
    sb = SBStub({
        "exams": [{"id": exam, "slug": "sebi-grade-a", "name": "SEBI Grade A", "is_active": True, "exam_family_id": None}],
        "exam_streams": [{"id": stream, "exam_id": exam, "stream_key": "legal", "name": "Legal", "is_active": True}],
        "exam_eligibility_rules": [
            # common: graduation (pass for a graduate)
            {"exam_id": exam, "stream_id": None, "scope": "all", "rule_type": "education_min_level",
             "value_num": None, "value_text": "graduation", "is_knockout": True, "reviewer_status": "verified"},
            # stream Legal: requires LLB discipline
            {"exam_id": exam, "stream_id": stream, "scope": "all", "rule_type": "discipline",
             "value_num": None, "value_text": "LLB", "is_knockout": True, "reviewer_status": "verified"},
        ],
        "profiles": [{"id": "u1", "nationality": "Indian"}],
        "aspirant_education": [{"user_id": "u1", "level": "graduation", "degree": "B.Com",
                                "stream": "commerce", "percentage": 70, "is_completed": True}],
    })
    out = summarize_user_eligibility(sb, "u1")
    invalidate_eligibility_rules_cache()
    # Exam-wide verdict uses common rules only -> graduate is eligible.
    items = out["eligible"]
    assert any(i["slug"] == "sebi-grade-a" for i in items)
    item = next(i for i in items if i["slug"] == "sebi-grade-a")
    # Per-stream breakdown present; the Legal stream needs LLB -> not_eligible.
    assert "streams" in item
    legal = next(s for s in item["streams"] if s["stream_key"] == "legal")
    assert legal["status"] == "not_eligible"
