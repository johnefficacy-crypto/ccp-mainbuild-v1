"""Tests for J3 PR2 applied-vs-appeared ratio helpers (candidate_counts.py)
and the atomic ratio switch in competition.py / competition_context.py.
"""
from __future__ import annotations

from app.exam_intelligence.candidate_counts import derive_rates, ratio_denominator
from app.exam_intelligence.competition import competition_series
from app.study_os.competition_context import competition_context
from tests.persona_questions._stub import SBStub

_BASE_DB = {
    "exams": [{"id": "exam-1", "slug": "upsc-cse"}],
    "exam_cycles": [
        {"id": "cy-2024", "exam_id": "exam-1", "year": 2024, "cycle_name": "CSE 2024", "status": "active"},
    ],
    "exam_phases": [
        {"id": "ph-prelims", "exam_id": "exam-1", "phase_name": "Prelims", "phase_slug": "prelims", "phase_order": 1},
        {"id": "ph-mains", "exam_id": "exam-1", "phase_name": "Mains", "phase_slug": "mains", "phase_order": 2},
    ],
}


def _db(**extra):
    db = {k: list(v) for k, v in _BASE_DB.items()}
    db.update(extra)
    return db


# ─── derive_rates ──────────────────────────────────────────────────────


def test_derive_rates_null_when_denominator_missing():
    assert derive_rates(1000, None) == (None, None)


def test_derive_rates_null_when_vacancy_missing():
    assert derive_rates(None, 500000) == (None, None)


def test_derive_rates_null_on_zero_or_negative():
    assert derive_rates(0, 500000) == (None, None)
    assert derive_rates(1000, 0) == (None, None)


def test_derive_rates_computes_both_directions():
    rate, per_vacancy = derive_rates(1000, 500000)
    assert round(rate, 6) == round(1000 / 500000, 6)
    assert round(per_vacancy, 2) == 500.0


# ─── ratio_denominator preference: appeared > applied > null ──────────


def test_ratio_denominator_null_when_no_reviewed_locked_counts():
    sb = SBStub(_db())
    value, label, row = ratio_denominator(sb, "exam-1", "cy-2024")
    assert (value, label, row) == (None, None, None)


def test_ratio_denominator_fails_closed_without_cycle_id():
    """Cycle-less callers (e.g. legacy reviewed/locked competition metrics
    preserved by migration 216 without an exam_cycle_id) must get NO
    denominator — never an arbitrary count borrowed from another cycle
    (Codex review, PR #870)."""
    sb = SBStub(_db(exam_candidate_counts=[
        {
            "id": "c-appeared", "exam_id": "exam-1", "exam_cycle_id": "cy-2024",
            "exam_phase_id": None, "scope_kind": "cycle", "count_type": "appeared",
            "reservation_category_id": None, "count_value": 950000,
            "reviewer_status": "locked", "is_current_published": True,
        },
    ]))
    value, label, row = ratio_denominator(sb, "exam-1", None)
    assert (value, label, row) == (None, None, None)


def test_ratio_denominator_ignores_draft_rows():
    sb = SBStub(_db(exam_candidate_counts=[
        {
            "id": "c1", "exam_id": "exam-1", "exam_cycle_id": "cy-2024",
            "exam_phase_id": None, "scope_kind": "cycle", "count_type": "applied",
            "reservation_category_id": None, "count_value": 999999,
            "reviewer_status": "draft", "is_current_published": False,
        },
    ]))
    value, label, _row = ratio_denominator(sb, "exam-1", "cy-2024")
    assert (value, label) == (None, None)


def test_ratio_denominator_prefers_appeared_over_applied():
    # Cycle-level (target_phase_id=None): both a cycle appeared aggregate and a
    # cycle applied aggregate exist — appeared wins.
    sb = SBStub(_db(exam_candidate_counts=[
        {
            "id": "c-applied", "exam_id": "exam-1", "exam_cycle_id": "cy-2024",
            "exam_phase_id": None, "scope_kind": "cycle", "count_type": "applied",
            "reservation_category_id": None, "count_value": 1200000,
            "reviewer_status": "locked", "is_current_published": True,
        },
        {
            "id": "c-appeared", "exam_id": "exam-1", "exam_cycle_id": "cy-2024",
            "exam_phase_id": None, "scope_kind": "cycle", "count_type": "appeared",
            "reservation_category_id": None, "count_value": 950000,
            "reviewer_status": "reviewed", "is_current_published": True,
        },
    ]))
    value, label, _row = ratio_denominator(sb, "exam-1", "cy-2024")
    assert (value, label) == (950000, "appeared")


def test_cycle_level_denominator_never_uses_a_phase_row():
    """checkpost P0-2: a cycle-level denominator (target_phase_id=None) must
    use ONLY an explicitly-labelled cycle aggregate — never a phase row
    (no 'earliest phase / largest turnout' heuristic, PD-2). With only a
    phase-scoped appeared count present, the cycle-level denominator is null."""
    sb = SBStub(_db(exam_candidate_counts=[
        {
            "id": "c-phase", "exam_id": "exam-1", "exam_cycle_id": "cy-2024",
            "exam_phase_id": "ph-prelims", "scope_kind": "phase", "count_type": "appeared",
            "reservation_category_id": None, "count_value": 950000,
            "reviewer_status": "locked", "is_current_published": True,
        },
    ]))
    value, label, row = ratio_denominator(sb, "exam-1", "cy-2024", target_phase_id=None)
    assert (value, label, row) == (None, None, None)


def test_phase_scoped_denominator_uses_only_matching_phase_appeared():
    """checkpost P0-2: a Mains row must never read a Prelims appeared count.
    Each phase's denominator is that phase's own appeared count; a cycle
    applied aggregate is the only permitted fallback."""
    sb = SBStub(_db(exam_candidate_counts=[
        {
            "id": "c-prelims", "exam_id": "exam-1", "exam_cycle_id": "cy-2024",
            "exam_phase_id": "ph-prelims", "scope_kind": "phase", "count_type": "appeared",
            "reservation_category_id": None, "count_value": 900000,
            "reviewer_status": "locked", "is_current_published": True,
        },
        {
            "id": "c-mains", "exam_id": "exam-1", "exam_cycle_id": "cy-2024",
            "exam_phase_id": "ph-mains", "scope_kind": "phase", "count_type": "appeared",
            "reservation_category_id": None, "count_value": 15000,
            "reviewer_status": "locked", "is_current_published": True,
        },
    ]))
    v_mains, l_mains, _ = ratio_denominator(sb, "exam-1", "cy-2024", target_phase_id="ph-mains")
    assert (v_mains, l_mains) == (15000, "appeared")
    v_pre, l_pre, _ = ratio_denominator(sb, "exam-1", "cy-2024", target_phase_id="ph-prelims")
    assert (v_pre, l_pre) == (900000, "appeared")


def test_phase_scoped_denominator_falls_back_to_cycle_applied():
    """A phase with no appeared count falls back to the cycle applied
    aggregate (applied is always cycle-scoped, OD-3) — never another phase."""
    sb = SBStub(_db(exam_candidate_counts=[
        {
            "id": "c-prelims", "exam_id": "exam-1", "exam_cycle_id": "cy-2024",
            "exam_phase_id": "ph-prelims", "scope_kind": "phase", "count_type": "appeared",
            "reservation_category_id": None, "count_value": 900000,
            "reviewer_status": "locked", "is_current_published": True,
        },
        {
            "id": "c-applied", "exam_id": "exam-1", "exam_cycle_id": "cy-2024",
            "exam_phase_id": None, "scope_kind": "cycle", "count_type": "applied",
            "reservation_category_id": None, "count_value": 1200000,
            "reviewer_status": "locked", "is_current_published": True,
        },
    ]))
    # Mains (no Mains appeared row) → cycle applied aggregate, NOT Prelims 900000.
    v, l, _ = ratio_denominator(sb, "exam-1", "cy-2024", target_phase_id="ph-mains")
    assert (v, l) == (1200000, "applied")


def test_ratio_denominator_falls_back_to_applied_when_no_appeared():
    sb = SBStub(_db(exam_candidate_counts=[
        {
            "id": "c-applied", "exam_id": "exam-1", "exam_cycle_id": "cy-2024",
            "exam_phase_id": None, "scope_kind": "cycle", "count_type": "applied",
            "reservation_category_id": None, "count_value": 1200000,
            "reviewer_status": "locked", "is_current_published": True,
        },
    ]))
    value, label, _row = ratio_denominator(sb, "exam-1", "cy-2024")
    assert (value, label) == (1200000, "applied")


def test_ratio_denominator_prefers_cycle_aggregate_over_phase_rows():
    sb = SBStub(_db(exam_candidate_counts=[
        {
            "id": "c-cycle-agg", "exam_id": "exam-1", "exam_cycle_id": "cy-2024",
            "exam_phase_id": None, "scope_kind": "cycle", "count_type": "appeared",
            "reservation_category_id": None, "count_value": 1000000,
            "reviewer_status": "locked", "is_current_published": True,
        },
        {
            "id": "c-phase", "exam_id": "exam-1", "exam_cycle_id": "cy-2024",
            "exam_phase_id": "ph-prelims", "scope_kind": "phase", "count_type": "appeared",
            "reservation_category_id": None, "count_value": 950000,
            "reviewer_status": "locked", "is_current_published": True,
        },
    ]))
    value, label, _row = ratio_denominator(sb, "exam-1", "cy-2024")
    assert (value, label) == (1000000, "appeared")


def test_ratio_denominator_ignores_per_category_rows():
    # A per-category row (reservation_category_id set) must never be
    # substituted for the official total denominator.
    sb = SBStub(_db(exam_candidate_counts=[
        {
            "id": "c-cat", "exam_id": "exam-1", "exam_cycle_id": "cy-2024",
            "exam_phase_id": None, "scope_kind": "cycle", "count_type": "applied",
            "reservation_category_id": "cat-general", "count_value": 500000,
            "reviewer_status": "locked", "is_current_published": True,
        },
    ]))
    value, label, _row = ratio_denominator(sb, "exam-1", "cy-2024")
    assert (value, label) == (None, None)


# ─── atomic switch: competition_series / competition_context ─────────


def _series_db(count_rows):
    db = _db()
    db["exam_competition_metrics"] = [
        {
            "id": "m1", "exam_id": "exam-1", "exam_cycle_id": "cy-2024",
            "exam_phase_id": None, "metric_kind": "cycle_summary",
            "vacancy_total": 1000, "vacancy_by_category": {},
            "applicant_count": 5000000, "selection_ratio": 0.0002,
            "cutoff_by_category": {}, "difficulty_assessment": {},
            "competition_pressure_score": 90.0, "is_current_published": True,
            "reviewer_status": "locked", "source_basis": "official",
            "confidence_score": 0.9, "created_at": "2024-01-01T00:00:00Z",
        },
    ]
    db["exam_candidate_counts"] = count_rows
    return db


def test_competition_series_uses_candidate_counts_denominator():
    sb = SBStub(_series_db([
        {
            "id": "c1", "exam_id": "exam-1", "exam_cycle_id": "cy-2024",
            "exam_phase_id": None, "scope_kind": "cycle", "count_type": "appeared",
            "reservation_category_id": None, "count_value": 500000,
            "reviewer_status": "locked", "is_current_published": True,
        },
    ]))
    series = competition_series(sb, "exam-1")
    assert len(series) == 1
    entry = series[0]
    assert entry["ratio_denominator"] == "appeared"
    assert round(entry["selection_rate"], 6) == round(1000 / 500000, 6)
    # The legacy alias is preserved verbatim (resolutions §1.2) alongside
    # the new provenance-proven fields.
    assert entry["selection_ratio_legacy"] == 0.0002


def test_competition_series_ratio_stays_null_without_candidate_counts():
    sb = SBStub(_series_db([]))
    series = competition_series(sb, "exam-1")
    entry = series[0]
    assert entry["ratio_denominator"] is None
    assert entry["selection_rate"] is None
    assert entry["candidates_per_vacancy"] is None


def test_competition_pressure_score_unchanged_by_ratio_switch():
    """Regression: OD-5 forbids this PR from touching
    competition_pressure_score itself — only count display + the pressure
    explanation text change."""
    sb_with_counts = SBStub(_series_db([
        {
            "id": "c1", "exam_id": "exam-1", "exam_cycle_id": "cy-2024",
            "exam_phase_id": None, "scope_kind": "cycle", "count_type": "appeared",
            "reservation_category_id": None, "count_value": 500000,
            "reviewer_status": "locked", "is_current_published": True,
        },
    ]))
    sb_without_counts = SBStub(_series_db([]))

    ctx_with = competition_context(sb_with_counts, "exam-1", exam_cycle_id="cy-2024", days_remaining=10)
    ctx_without = competition_context(sb_without_counts, "exam-1", exam_cycle_id="cy-2024", days_remaining=10)

    assert ctx_with["competition_pressure_score"] == ctx_without["competition_pressure_score"] == 90.0
    assert ctx_with["cycle_pressure"]["pressure_level"] == ctx_without["cycle_pressure"]["pressure_level"]
    # But the explanation text and ratio fields DO differ (the fix this PR
    # ships): a provenance-proven denominator changes the count display and
    # the human-readable reason, never the score/level themselves.
    assert ctx_with["ratio_denominator"] == "appeared"
    assert ctx_without["ratio_denominator"] is None
    assert ctx_with["selection_rate"] is not None
    assert ctx_without["selection_rate"] is None


def test_competition_context_pressure_reason_reflects_denominator():
    sb = SBStub(_series_db([
        {
            "id": "c1", "exam_id": "exam-1", "exam_cycle_id": "cy-2024",
            "exam_phase_id": None, "scope_kind": "cycle", "count_type": "appeared",
            "reservation_category_id": None, "count_value": 500000,
            "reviewer_status": "locked", "is_current_published": True,
        },
    ]))
    ctx = competition_context(sb, "exam-1", exam_cycle_id="cy-2024", days_remaining=10)
    assert "appeared" in (ctx["cycle_pressure"]["reason"] or "")


def test_two_phase_series_never_shows_a_prelims_denominator_on_the_mains_row():
    """checkpost P0-2 regression: a two-phase series must attach each phase's
    OWN appeared count. The Mains row's selection_rate/denominator comes from
    Mains appeared (15000), never Prelims appeared (900000); the cycle_summary
    row uses only the cycle aggregate."""
    db = _db()
    db["exam_competition_metrics"] = [
        {
            "id": "m-cycle", "exam_id": "exam-1", "exam_cycle_id": "cy-2024",
            "exam_phase_id": None, "metric_kind": "cycle_summary",
            "vacancy_total": 1000, "vacancy_by_category": {},
            "applicant_count": 5000000, "selection_ratio": 0.0002,
            "cutoff_by_category": {}, "difficulty_assessment": {},
            "competition_pressure_score": 90.0, "is_current_published": True,
            "reviewer_status": "locked", "source_basis": "official",
            "confidence_score": 0.9, "created_at": "2024-01-01T00:00:00Z",
        },
        {
            "id": "m-prelims", "exam_id": "exam-1", "exam_cycle_id": "cy-2024",
            "exam_phase_id": "ph-prelims", "metric_kind": "phase_cutoff",
            "cutoff_by_category": {}, "difficulty_assessment": {},
            "is_current_published": True, "reviewer_status": "locked",
            "source_basis": "official", "confidence_score": 0.9,
            "created_at": "2024-01-01T00:00:00Z",
        },
        {
            "id": "m-mains", "exam_id": "exam-1", "exam_cycle_id": "cy-2024",
            "exam_phase_id": "ph-mains", "metric_kind": "phase_cutoff",
            "cutoff_by_category": {}, "difficulty_assessment": {},
            "is_current_published": True, "reviewer_status": "locked",
            "source_basis": "official", "confidence_score": 0.9,
            "created_at": "2024-01-01T00:00:00Z",
        },
    ]
    db["exam_candidate_counts"] = [
        {
            "id": "cc-cycle-applied", "exam_id": "exam-1", "exam_cycle_id": "cy-2024",
            "exam_phase_id": None, "scope_kind": "cycle", "count_type": "applied",
            "reservation_category_id": None, "count_value": 5000000,
            "reviewer_status": "locked", "is_current_published": True,
        },
        {
            "id": "cc-prelims", "exam_id": "exam-1", "exam_cycle_id": "cy-2024",
            "exam_phase_id": "ph-prelims", "scope_kind": "phase", "count_type": "appeared",
            "reservation_category_id": None, "count_value": 900000,
            "reviewer_status": "locked", "is_current_published": True,
        },
        {
            "id": "cc-mains", "exam_id": "exam-1", "exam_cycle_id": "cy-2024",
            "exam_phase_id": "ph-mains", "scope_kind": "phase", "count_type": "appeared",
            "reservation_category_id": None, "count_value": 15000,
            "reviewer_status": "locked", "is_current_published": True,
        },
    ]
    series = competition_series(SBStub(db), "exam-1")
    by_phase = {e["phase_id"]: e for e in series}

    mains = by_phase["ph-mains"]
    assert mains["ratio_denominator"] == "appeared"
    # Mains vacancy is inherited from the cycle_summary (1000); the denominator
    # is Mains appeared (15000), NOT Prelims appeared (900000).
    assert round(mains["selection_rate"], 9) == round(1000 / 15000, 9)

    prelims = by_phase["ph-prelims"]
    assert round(prelims["selection_rate"], 9) == round(1000 / 900000, 9)

    # The cycle_summary row uses only the cycle aggregate (applied 5,000,000).
    cyc = by_phase[None]
    assert cyc["ratio_denominator"] == "applied"
    assert round(cyc["selection_rate"], 9) == round(1000 / 5000000, 9)
