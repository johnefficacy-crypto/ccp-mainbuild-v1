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


def test_discipline_matching_is_boundary_safe_not_substring():
    # Short acronyms must NOT substring-match unrelated fields (checkpost P0).
    assert evaluate_exam_for_user([_r("discipline", value_text="IT")], {"disciplines": ["Statistics"]})["status"] == "not_eligible"
    assert evaluate_exam_for_user([_r("discipline", value_text="CA")], {"disciplines": ["Vocational Training"]})["status"] == "not_eligible"
    assert evaluate_exam_for_user([_r("discipline", value_text="Law")], {"disciplines": ["Flawless Studies"]})["status"] == "not_eligible"
    # …but the alias still resolves the real qualification.
    assert evaluate_exam_for_user([_r("discipline", value_text="IT")], {"disciplines": ["Information Technology"]})["status"] == "eligible"


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


def test_stream_availability_fails_closed_on_unknown_value():
    assert evaluate_exam_for_user([_r("stream_availability", value_text="not_offered")], {})["status"] == "not_eligible"
    # A typo / unsupported value must NOT pass (fail closed, checkpost P1).
    assert evaluate_exam_for_user([_r("stream_availability", value_text="maybe")], {})["status"] == "not_eligible"
    assert evaluate_exam_for_user([_r("stream_availability", value_text="offered")], {})["status"] == "eligible"


# ── record correlation ─────────────────────────────────────────────────────


def test_combination_requires_one_record_to_satisfy_all_bound_clauses():
    rule = [_r("qualification_combination", value_json=_QC)]  # LLB AND >=60%
    # LLB at 50% + unrelated B.Com at 75% must NOT satisfy "LLB AND 60%".
    mixed = {"education_records": [
        {"disciplines": ["LLB"], "percentage": 50, "level": "graduation"},
        {"disciplines": ["B.Com"], "percentage": 75, "level": "graduation"},
    ], "disciplines": ["LLB", "B.Com"], "best_percentage": 75}
    assert evaluate_exam_for_user(rule, mixed)["status"] == "not_eligible"
    # One record that is BOTH LLB and >=60% satisfies it.
    good = {"education_records": [{"disciplines": ["LLB"], "percentage": 65, "level": "graduation"}],
            "disciplines": ["LLB"], "best_percentage": 65}
    assert evaluate_exam_for_user(rule, good)["status"] == "eligible"


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


def test_summarize_loads_value_json_for_combination_rules():
    # Regression for the checkpost P0: the DB loader must SELECT value_json, or a
    # verified qualification_combination is always None -> not_eligible.
    exam = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
    invalidate_eligibility_rules_cache()
    sb = SBStub({
        "exams": [{"id": exam, "slug": "sebi-grade-a", "name": "SEBI Grade A", "is_active": True, "exam_family_id": None}],
        "exam_streams": [],
        "exam_eligibility_rules": [
            {"exam_id": exam, "stream_id": None, "scope": "all", "rule_type": "qualification_combination",
             "value_num": None, "value_text": None, "value_json": _QC, "is_knockout": True, "reviewer_status": "verified"},
        ],
        "profiles": [{"id": "u1", "nationality": "Indian"}],
        "aspirant_education": [{"user_id": "u1", "level": "graduation", "degree": "LLB",
                                "stream": "law", "percentage": 70, "is_completed": True}],
    })
    out = summarize_user_eligibility(sb, "u1")
    invalidate_eligibility_rules_cache()
    # LLB at 70% satisfies "LLB AND 60%" -> eligible (would be not_eligible if
    # value_json were dropped by the projection).
    assert any(i["slug"] == "sebi-grade-a" for i in out["eligible"])


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
