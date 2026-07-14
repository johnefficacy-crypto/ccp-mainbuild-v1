"""Regression coverage for PR 989 cycle eligibility blockers."""
from __future__ import annotations

from app.exam_eligibility.evaluator import (
    evaluate_cycle_eligibility,
    invalidate_eligibility_rules_cache,
    summarize_user_eligibility,
)
from tests.persona_questions._stub import SBStub


_DOB = "1994-07-20"
_EXAM = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
_STREAM = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
_CYCLE = "ffffffff-ffff-4fff-8fff-ffffffffffff"


def _age_rule(value_num=30, *, basis="cycle_notification", cutoff_date=None):
    return {
        "scope": "all",
        "rule_type": "age_max",
        "value_num": value_num,
        "value_text": None,
        "value_json": None,
        "cutoff_date_basis": basis,
        "cutoff_date": cutoff_date,
        "is_knockout": True,
    }


def _experience_rule(value_num=3):
    return {
        "scope": "all",
        "rule_type": "experience_min_years",
        "value_num": value_num,
        "value_text": None,
        "value_json": None,
        "cutoff_date_basis": None,
        "cutoff_date": None,
        "is_knockout": True,
    }


def test_unresolved_cutoff_is_not_hidden_by_another_passing_rule():
    result = evaluate_cycle_eligibility(
        [_age_rule(), _experience_rule()],
        {"date_of_birth": _DOB, "experience_years": 5},
    )
    assert result["status"] == "unknown"


def test_unresolved_cutoff_does_not_hide_a_concrete_knockout():
    result = evaluate_cycle_eligibility(
        [_age_rule(), _experience_rule()],
        {"date_of_birth": _DOB, "experience_years": 1},
    )
    assert result["status"] == "not_eligible"


def test_malformed_age_threshold_fails_closed_to_unknown():
    result = evaluate_cycle_eligibility(
        [_age_rule(value_num=None, basis="fixed_date", cutoff_date="2025-01-01")],
        {"date_of_birth": _DOB},
    )
    assert result["status"] == "unknown"


def test_summary_loads_recorded_experience_for_cycle_rule():
    world = {
        "exams": [
            {
                "id": _EXAM,
                "slug": "sebi-grade-a",
                "name": "SEBI Grade A",
                "is_active": True,
                "exam_family_id": None,
            }
        ],
        "exam_streams": [
            {
                "id": _STREAM,
                "exam_id": _EXAM,
                "stream_key": "legal",
                "name": "Legal",
                "is_active": True,
            }
        ],
        "exam_eligibility_rules": [
            {
                "exam_id": _EXAM,
                "stream_id": None,
                "scope": "all",
                "rule_type": "education_min_level",
                "value_num": None,
                "value_text": "graduation",
                "value_json": None,
                "is_knockout": True,
                "reviewer_status": "verified",
            }
        ],
        "exam_cycle_stream_eligibility": [
            {
                "exam_cycle_id": _CYCLE,
                "stream_id": _STREAM,
                "reviewer_status": "verified",
                **_experience_rule(),
            }
        ],
        "profiles": [
            {"id": "u1", "date_of_birth": _DOB, "nationality": "Indian"}
        ],
        "aspirant_education": [
            {"user_id": "u1", "level": "graduation", "is_completed": True}
        ],
        "aspirant_experience": [
            {"user_id": "u1", "years_experience": 1.5},
            {"user_id": "u1", "years_experience": 2.0},
        ],
    }

    invalidate_eligibility_rules_cache()
    result = summarize_user_eligibility(SBStub(world), "u1")
    invalidate_eligibility_rules_cache()

    item = next(row for row in result["eligible"] if row["slug"] == "sebi-grade-a")
    assert item["cycle"]["status"] == "eligible"
