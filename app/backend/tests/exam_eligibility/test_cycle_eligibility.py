"""Cutoff-aware, cycle-scoped eligibility (Lane R §4 prereq 3).

The baseline evaluator measures age against ``date.today()``; the cycle layer
must measure it against the notification's official cut-off date and preserve
``unknown`` when that date — or the authoritative cycle source — is unavailable.
"""
from __future__ import annotations

from datetime import date

from app.exam_eligibility.evaluator import (
    _aggregate_cycle_status,
    _resolve_cutoff_date,
    evaluate_cycle_eligibility,
    evaluate_exam_for_user,
    summarize_user_eligibility,
    invalidate_eligibility_rules_cache,
)
from tests.persona_questions._stub import SBStub


def _age_rule(rule_type, value_num, *, basis=None, cutoff_date=None, scope="all"):
    return {
        "scope": scope,
        "rule_type": rule_type,
        "value_num": value_num,
        "value_text": None,
        "value_json": None,
        "cutoff_date_basis": basis,
        "cutoff_date": cutoff_date,
        "is_knockout": True,
    }


# A user who is 30 on 2025-01-01 (the cut-off) but 32 by the time the dashboard
# runs — the exact "verdict flips near the cut-off" case the PR fixes.
_DOB = "1994-07-20"


# ── cut-off resolution ──────────────────────────────────────────────────────


def test_fixed_date_basis_resolves_to_rule_cutoff():
    rule = _age_rule("age_max", 30, basis="fixed_date", cutoff_date="2025-01-01")
    assert _resolve_cutoff_date(rule, None) == date(2025, 1, 1)


def test_cycle_notification_basis_needs_authoritative_cycle():
    rule = _age_rule("age_max", 30, basis="cycle_notification")
    # No cycle vouched for → unresolved (authoritative source unavailable).
    assert _resolve_cutoff_date(rule, None) is None
    # With an authoritative cycle → its notification_date.
    assert _resolve_cutoff_date(rule, {"notification_date": "2025-01-01"}) == date(2025, 1, 1)


def test_absent_or_unknown_basis_resolves_to_none():
    assert _resolve_cutoff_date(_age_rule("age_max", 30), None) is None
    assert _resolve_cutoff_date(_age_rule("age_max", 30, basis="whoops"), None) is None
    # fixed_date with no date is also unresolved.
    assert _resolve_cutoff_date(_age_rule("age_max", 30, basis="fixed_date"), None) is None


# ── age is measured on the cut-off, not today ───────────────────────────────


def test_age_evaluated_on_fixed_cutoff_not_today():
    rule = [_age_rule("age_max", 30, basis="fixed_date", cutoff_date="2025-01-01")]
    profile = {"date_of_birth": _DOB}
    # On the official cut-off the aspirant is exactly 30 → eligible…
    assert evaluate_cycle_eligibility(rule, profile)["status"] == "eligible"
    # …whereas the baseline (today-based) path would knock the same user out,
    # proving the cut-off actually changed the verdict.
    assert evaluate_exam_for_user(rule, profile)["status"] == "not_eligible"


def test_age_evaluated_on_cycle_notification_date_when_authoritative():
    rule = [_age_rule("age_max", 30, basis="cycle_notification")]
    out = evaluate_cycle_eligibility(
        rule, {"date_of_birth": _DOB}, cycle={"notification_date": "2025-01-01"}
    )
    assert out["status"] == "eligible"


def test_fixed_cutoff_over_age_still_knocks_out():
    rule = [_age_rule("age_max", 30, basis="fixed_date", cutoff_date="2026-07-14")]
    # 32 on this cut-off → over the cap.
    out = evaluate_cycle_eligibility(rule, {"date_of_birth": _DOB})
    assert out["status"] == "not_eligible"
    assert any("at most 30" in r for r in out["reasons"])


# ── preserve unknown when the cut-off / cycle source is unavailable ─────────


def test_unknown_when_cycle_notification_has_no_authoritative_cycle():
    rule = [_age_rule("age_max", 30, basis="cycle_notification")]
    # cycle=None → cut-off unresolved → age rule left unevaluated → unknown,
    # never a today-based guess.
    assert evaluate_cycle_eligibility(rule, {"date_of_birth": _DOB})["status"] == "unknown"


def test_unknown_when_basis_missing():
    rule = [_age_rule("age_max", 30)]  # no basis at all
    assert evaluate_cycle_eligibility(rule, {"date_of_birth": _DOB})["status"] == "unknown"


def test_missing_dob_is_conditional_when_cutoff_is_resolvable():
    rule = [_age_rule("age_max", 30, basis="fixed_date", cutoff_date="2025-01-01")]
    out = evaluate_cycle_eligibility(rule, {})
    assert out["status"] == "conditional"
    assert "date_of_birth" in out["missing_fields"]


def test_no_cycle_rules_is_unknown():
    assert evaluate_cycle_eligibility([], {"date_of_birth": _DOB})["status"] == "unknown"


def test_unresolved_age_does_not_mask_a_decidable_knockout():
    # An unresolved cycle_notification age rule + a decidable experience knockout:
    # the concrete knockout still fires (unknown age must not swallow a real fail).
    rules = [
        _age_rule("age_max", 30, basis="cycle_notification"),
        {"scope": "all", "rule_type": "experience_min_years", "value_num": 3,
         "value_text": None, "value_json": None, "is_knockout": True},
    ]
    out = evaluate_cycle_eligibility(rules, {"date_of_birth": _DOB, "experience_years": 1})
    assert out["status"] == "not_eligible"


# ── experience_min_years (cycle-only fact) ──────────────────────────────────


def test_experience_min_years_pass_fail_missing():
    rule = [{"scope": "all", "rule_type": "experience_min_years", "value_num": 3,
             "value_text": None, "value_json": None, "is_knockout": True}]
    assert evaluate_cycle_eligibility(rule, {"experience_years": 5})["status"] == "eligible"
    assert evaluate_cycle_eligibility(rule, {"experience_years": 1})["status"] == "not_eligible"
    out = evaluate_cycle_eligibility(rule, {})
    assert out["status"] == "conditional"
    assert "experience_years" in out["missing_fields"]


# ── baseline stays today-based (no regression) ──────────────────────────────


def test_baseline_path_ignores_cutoff_fields():
    # A baseline (no cutoff_context) call never reads cutoff fields — age is
    # measured against the explicit reference_date exactly as before.
    rule = [_age_rule("age_max", 30, basis="fixed_date", cutoff_date="2025-01-01")]
    out = evaluate_exam_for_user(rule, {"date_of_birth": _DOB}, reference_date=date(2025, 1, 1))
    assert out["status"] == "eligible"  # 30 on the reference date


# ── aggregate fold ──────────────────────────────────────────────────────────


def test_aggregate_cycle_status_prefers_best_then_unknown_over_not_eligible():
    assert _aggregate_cycle_status([{"status": "not_eligible"}, {"status": "eligible"}]) == "eligible"
    assert _aggregate_cycle_status([{"status": "not_eligible"}, {"status": "conditional"}]) == "conditional"
    # unknown outranks a decisive no on a different stream — an undecidable
    # stream must not be buried.
    assert _aggregate_cycle_status([{"status": "not_eligible"}, {"status": "unknown"}]) == "unknown"
    assert _aggregate_cycle_status([{"status": "not_eligible"}]) == "not_eligible"
    assert _aggregate_cycle_status([]) == "unknown"


# ── summarize wiring: baseline and cycle bands stay separate ────────────────


_EXAM = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
_STREAM = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
_CYCLE = "ffffffff-ffff-4fff-8fff-ffffffffffff"


def _world_with_cycle(cutoff_basis="fixed_date", cutoff_date="2025-01-01"):
    return {
        "exams": [{"id": _EXAM, "slug": "sebi-grade-a", "name": "SEBI Grade A",
                   "is_active": True, "exam_family_id": None}],
        "exam_streams": [{"id": _STREAM, "exam_id": _EXAM, "stream_key": "legal",
                          "name": "Legal", "is_active": True}],
        "exam_eligibility_rules": [
            {"exam_id": _EXAM, "stream_id": None, "scope": "all",
             "rule_type": "education_min_level", "value_num": None,
             "value_text": "graduation", "is_knockout": True, "reviewer_status": "verified"},
        ],
        "exam_cycle_stream_eligibility": [
            {"exam_cycle_id": _CYCLE, "stream_id": _STREAM, "scope": "all",
             "rule_type": "age_max", "value_num": 30, "value_text": None, "value_json": None,
             "cutoff_date_basis": cutoff_basis, "cutoff_date": cutoff_date,
             "is_knockout": True, "reviewer_status": "verified"},
        ],
        "profiles": [{"id": "u1", "date_of_birth": _DOB, "nationality": "Indian"}],
        "aspirant_education": [{"user_id": "u1", "level": "graduation", "is_completed": True}],
    }


def test_summarize_attaches_cutoff_aware_cycle_band():
    invalidate_eligibility_rules_cache()
    out = summarize_user_eligibility(SBStub(_world_with_cycle()), "u1")
    invalidate_eligibility_rules_cache()

    item = next(i for i in out["eligible"] if i["slug"] == "sebi-grade-a")
    # Baseline verdict (graduation) is unchanged and separate.
    assert item["reasons"] == []
    # Cycle band present, keyed per (cycle, stream), evaluated on the cut-off.
    band = item["cycle"]
    assert band is not None
    assert band["status"] == "eligible"
    st = band["streams"][0]
    assert st["cycle_id"] == _CYCLE
    assert st["stream_id"] == _STREAM
    assert st["status"] == "eligible"


def test_summarize_cycle_band_unknown_without_authoritative_cycle():
    # A cycle_notification age rule with no trusted cycle source stays unknown.
    invalidate_eligibility_rules_cache()
    out = summarize_user_eligibility(
        SBStub(_world_with_cycle(cutoff_basis="cycle_notification", cutoff_date=None)), "u1"
    )
    invalidate_eligibility_rules_cache()
    item = next(i for i in out["eligible"] if i["slug"] == "sebi-grade-a")
    assert item["cycle"]["status"] == "unknown"


def test_summarize_cycle_band_is_none_without_cycle_rules():
    world = _world_with_cycle()
    world["exam_cycle_stream_eligibility"] = []
    invalidate_eligibility_rules_cache()
    out = summarize_user_eligibility(SBStub(world), "u1")
    invalidate_eligibility_rules_cache()
    item = next(i for i in out["eligible"] if i["slug"] == "sebi-grade-a")
    assert item["cycle"] is None
