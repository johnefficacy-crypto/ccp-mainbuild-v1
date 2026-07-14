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
_STREAM2 = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeee2"
_CYCLE = "ffffffff-ffff-4fff-8fff-ffffffffffff"

# Rule-level provenance lives on exam_cycle_stream_eligibility (migration 248),
# NOT on the exam_cycles row — the displayed "verified from source on date" claim
# must attest the eligibility RULES, not the cycle metadata.
_RULE_SOURCE = "https://sebi.gov.in/legal-eligibility.pdf"
_RULE_VERIFIED_AT = "2025-02-10T00:00:00Z"


def _world_with_cycle(
    cutoff_basis="fixed_date",
    cutoff_date="2025-01-01",
    *,
    reviewer_status="verified",
    operational_status="open",
    notification_date="2025-01-01",
    rule_source_url=_RULE_SOURCE,
    rule_verified_at=_RULE_VERIFIED_AT,
):
    return {
        "exams": [{"id": _EXAM, "slug": "sebi-grade-a", "name": "SEBI Grade A",
                   "is_active": True, "exam_family_id": None}],
        "exam_streams": [{"id": _STREAM, "exam_id": _EXAM, "stream_key": "legal",
                          "name": "Legal", "is_active": True}],
        # The authoritative cycle: only reviewer_status='verified' AND an
        # operational status (expected/open/active) feeds the band (migration 261).
        "exam_cycles": [{"id": _CYCLE, "exam_id": _EXAM, "cycle_name": "2025 Cycle",
                         "year": 2025, "notification_date": notification_date,
                         "source_url": "https://sebi.gov.in/notif.pdf",
                         "reviewed_at": "2025-02-01T00:00:00Z",
                         "reviewer_status": reviewer_status, "status": operational_status}],
        "exam_eligibility_rules": [
            {"exam_id": _EXAM, "stream_id": None, "scope": "all",
             "rule_type": "education_min_level", "value_num": None,
             "value_text": "graduation", "is_knockout": True, "reviewer_status": "verified"},
        ],
        "exam_cycle_stream_eligibility": [
            {"exam_cycle_id": _CYCLE, "stream_id": _STREAM, "scope": "all",
             "rule_type": "age_max", "value_num": 30, "value_text": None, "value_json": None,
             "cutoff_date_basis": cutoff_basis, "cutoff_date": cutoff_date,
             "is_knockout": True, "reviewer_status": "verified",
             "source_url": rule_source_url, "verified_at": rule_verified_at},
        ],
        "profiles": [{"id": "u1", "date_of_birth": _DOB, "nationality": "Indian"}],
        "aspirant_education": [{"user_id": "u1", "level": "graduation", "is_completed": True}],
    }


def _world_two_streams(*, cutoffs, sources):
    """Two streams under the same verified cycle, each with its OWN fixed-date age
    rule and source — for the cycle-level unanimity checks (P1-2 / P1-3)."""
    world = _world_with_cycle()
    world["exam_streams"].append(
        {"id": _STREAM2, "exam_id": _EXAM, "stream_key": "research",
         "name": "Research", "is_active": True}
    )
    world["exam_cycle_stream_eligibility"] = [
        {"exam_cycle_id": _CYCLE, "stream_id": sid, "scope": "all",
         "rule_type": "age_max", "value_num": 60, "value_text": None, "value_json": None,
         "cutoff_date_basis": "fixed_date", "cutoff_date": cd,
         "is_knockout": True, "reviewer_status": "verified",
         "source_url": src, "verified_at": _RULE_VERIFIED_AT}
        for sid, cd, src in (
            (_STREAM, cutoffs[0], sources[0]),
            (_STREAM2, cutoffs[1], sources[1]),
        )
    ]
    return world


def test_summarize_attaches_cutoff_aware_cycle_band():
    invalidate_eligibility_rules_cache()
    out = summarize_user_eligibility(SBStub(_world_with_cycle()), "u1")
    invalidate_eligibility_rules_cache()

    item = next(i for i in out["eligible"] if i["slug"] == "sebi-grade-a")
    # Baseline verdict (graduation) is unchanged and separate.
    assert item["reasons"] == []
    # Cycle band present, nested per verified cycle with authoritative metadata.
    band = item["cycle"]
    assert band is not None
    assert band["status"] == "eligible"
    cyc = band["cycles"][0]
    assert cyc["cycle_id"] == _CYCLE
    assert cyc["cycle_name"] == "2025 Cycle"
    assert cyc["cycle_status"] == "open"  # operational status surfaced
    assert cyc["notification_date"] == "2025-01-01"
    assert cyc["cutoff_date"] == "2025-01-01"  # fixed_date cut-off
    # Provenance attests the eligibility RULE, not the cycle metadata row.
    assert cyc["source_url"] == _RULE_SOURCE
    assert cyc["verified_at"] == _RULE_VERIFIED_AT
    assert cyc["status"] == "eligible"
    st = cyc["streams"][0]
    assert st["stream_id"] == _STREAM
    assert st["status"] == "eligible"
    assert st["cutoff_date"] == "2025-01-01"
    assert st["source_url"] == _RULE_SOURCE
    assert st["verified_at"] == _RULE_VERIFIED_AT


def test_summarize_cycle_notification_resolves_on_verified_cycle():
    # With a VERIFIED authoritative cycle, a cycle_notification age rule now
    # resolves on the cycle's notification_date (trust gate, migration 261).
    invalidate_eligibility_rules_cache()
    out = summarize_user_eligibility(
        SBStub(_world_with_cycle(cutoff_basis="cycle_notification", cutoff_date=None)), "u1"
    )
    invalidate_eligibility_rules_cache()
    item = next(i for i in out["eligible"] if i["slug"] == "sebi-grade-a")
    cyc = item["cycle"]["cycles"][0]
    assert cyc["status"] == "eligible"
    assert cyc["cutoff_date"] == "2025-01-01"  # resolved from notification_date


def test_summarize_cycle_notification_unknown_when_notification_missing():
    # A verified cycle that carries no notification_date cannot resolve a
    # cycle_notification cut-off → the stream stays unknown (never today-based).
    invalidate_eligibility_rules_cache()
    out = summarize_user_eligibility(
        SBStub(_world_with_cycle(cutoff_basis="cycle_notification", cutoff_date=None,
                                 notification_date=None)),
        "u1",
    )
    invalidate_eligibility_rules_cache()
    item = next(i for i in out["eligible"] if i["slug"] == "sebi-grade-a")
    cyc = item["cycle"]["cycles"][0]
    assert cyc["status"] == "unknown"
    assert cyc["cutoff_date"] is None
    # P2: the unknown carries a concrete unresolved-cut-off reason (never a false
    # "verified rules missing").
    st = cyc["streams"][0]
    assert any("cut-off" in r.lower() for r in st["reasons"])


def test_summarize_cycle_band_is_none_for_unverified_cycle():
    # Trust gate: a cycle rule whose exam_cycles row is NOT verified is dropped —
    # an unreviewed cycle is never shown, and baseline is never substituted.
    invalidate_eligibility_rules_cache()
    out = summarize_user_eligibility(SBStub(_world_with_cycle(reviewer_status="draft")), "u1")
    invalidate_eligibility_rules_cache()
    item = next(i for i in out["eligible"] if i["slug"] == "sebi-grade-a")
    assert item["cycle"] is None


def test_summarize_cycle_band_excludes_non_current_cycle():
    # P1: a verified but cancelled/closed/completed cycle is history, NOT
    # current-cycle eligibility — it must not appear in the band.
    for terminal in ("cancelled", "closed", "completed"):
        invalidate_eligibility_rules_cache()
        out = summarize_user_eligibility(
            SBStub(_world_with_cycle(operational_status=terminal)), "u1"
        )
        invalidate_eligibility_rules_cache()
        item = next(i for i in out["eligible"] if i["slug"] == "sebi-grade-a")
        assert item["cycle"] is None, f"{terminal} cycle must be excluded"


def test_summarize_cycle_cutoff_and_source_none_when_streams_disagree():
    # P1: cycle-level cutoff/source are emitted ONLY when every displayed stream
    # agrees; divergent per-stream provenance must NOT collapse to one value.
    invalidate_eligibility_rules_cache()
    out = summarize_user_eligibility(
        SBStub(_world_two_streams(
            cutoffs=("2025-01-01", "2025-06-01"),
            sources=("https://sebi.gov.in/legal.pdf", "https://sebi.gov.in/research.pdf"),
        )),
        "u1",
    )
    invalidate_eligibility_rules_cache()
    item = next(i for i in out["eligible"] if i["slug"] == "sebi-grade-a")
    cyc = item["cycle"]["cycles"][0]
    assert cyc["cutoff_date"] is None
    assert cyc["source_url"] is None
    per = {s["stream_id"]: s for s in cyc["streams"]}
    assert per[_STREAM]["cutoff_date"] == "2025-01-01"
    assert per[_STREAM2]["cutoff_date"] == "2025-06-01"
    assert per[_STREAM]["source_url"] == "https://sebi.gov.in/legal.pdf"
    assert per[_STREAM2]["source_url"] == "https://sebi.gov.in/research.pdf"


def test_summarize_cycle_cutoff_and_source_unanimous_when_streams_agree():
    invalidate_eligibility_rules_cache()
    out = summarize_user_eligibility(
        SBStub(_world_two_streams(
            cutoffs=("2025-01-01", "2025-01-01"),
            sources=("https://sebi.gov.in/one.pdf", "https://sebi.gov.in/one.pdf"),
        )),
        "u1",
    )
    invalidate_eligibility_rules_cache()
    item = next(i for i in out["eligible"] if i["slug"] == "sebi-grade-a")
    cyc = item["cycle"]["cycles"][0]
    assert cyc["cutoff_date"] == "2025-01-01"
    assert cyc["source_url"] == "https://sebi.gov.in/one.pdf"


def test_summarize_cycle_band_is_none_without_cycle_rules():
    world = _world_with_cycle()
    world["exam_cycle_stream_eligibility"] = []
    invalidate_eligibility_rules_cache()
    out = summarize_user_eligibility(SBStub(world), "u1")
    invalidate_eligibility_rules_cache()
    item = next(i for i in out["eligible"] if i["slug"] == "sebi-grade-a")
    assert item["cycle"] is None


def _sebi_band(sb):
    out = summarize_user_eligibility(sb, "u1")
    item = next(i for i in out["eligible"] if i["slug"] == "sebi-grade-a")
    return item["cycle"]


def test_summarize_reads_cycles_fresh_no_stale_trust():
    # Trust-freshness (P0, migration-261 fail-closed): verified cycles are read
    # FRESH on every summary and never cached, so demoting or retiring a cycle is
    # reflected on the very next call — a demoted/cancelled cycle can never stay
    # aspirant-trusted for a TTL window. Guards against re-introducing a cache
    # that would keep a stale verified cycle in the Compass current-cycle band.
    world = _world_with_cycle()  # verified + open → band present
    sb = SBStub(world)

    invalidate_eligibility_rules_cache()
    band = _sebi_band(sb)
    assert band is not None and band["cycles"], "verified current cycle should surface"

    # Demote the SAME exam_cycles row (as a CMS/registry writer would) — WITHOUT
    # clearing any cache. A fresh read must drop it immediately.
    world["exam_cycles"][0]["reviewer_status"] = "draft"
    assert _sebi_band(sb) is None, "demoted cycle must not stay trusted"

    # Re-verify but retire to a terminal operational status → still dropped
    # (verified-but-historical is not current-cycle eligibility).
    world["exam_cycles"][0]["reviewer_status"] = "verified"
    world["exam_cycles"][0]["status"] = "cancelled"
    assert _sebi_band(sb) is None, "retired cycle must not stay trusted"
    invalidate_eligibility_rules_cache()
