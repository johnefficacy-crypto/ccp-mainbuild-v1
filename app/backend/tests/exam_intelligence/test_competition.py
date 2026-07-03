"""Tests for Phase 12 competition intelligence shapers."""
from __future__ import annotations

from app.exam_intelligence.competition import (
    competition_series,
    cutoff_series,
    vacancy_series,
)
from tests.persona_questions._stub import SBStub


_BASE_DB = {
    "exam_cycles": [
        {"id": "cy-2022", "exam_id": "exam-1", "year": 2022, "cycle_name": "CSE 2022", "status": "completed"},
        {"id": "cy-2023", "exam_id": "exam-1", "year": 2023, "cycle_name": "CSE 2023", "status": "completed"},
        {"id": "cy-2024", "exam_id": "exam-1", "year": 2024, "cycle_name": "CSE 2024", "status": "active"},
    ],
    "exam_phases": [
        {"id": "ph-prelims", "exam_id": "exam-1", "phase_name": "Prelims", "phase_slug": "prelims", "phase_order": 1},
        {"id": "ph-mains", "exam_id": "exam-1", "phase_name": "Mains", "phase_slug": "mains", "phase_order": 2},
    ],
}


def _metrics_db():
    db = {k: list(v) for k, v in _BASE_DB.items()}
    db["exam_competition_metrics"] = [
        # 2022 prelims — reviewed
        {
            "id": "m1", "exam_id": "exam-1", "exam_cycle_id": "cy-2022",
            "exam_phase_id": "ph-prelims", "vacancy_total": 1011,
            "vacancy_by_category": {"general": 410, "obc": 270, "sc": 152, "st": 79, "ews": 100},
            "applicant_count": 1130000, "selection_ratio": 0.000924,
            "cutoff_trend": {"general": 88.22, "obc": 87.54, "sc": 74.08, "st": 69.35},
            "difficulty_trend": {"overall": "medium"},
            "competition_pressure_score": 81.2, "reviewer_status": "reviewed",
            "source_basis": "official", "confidence_score": 0.92,
        },
        # 2023 prelims — locked
        {
            "id": "m2", "exam_id": "exam-1", "exam_cycle_id": "cy-2023",
            "exam_phase_id": "ph-prelims", "vacancy_total": 1105,
            "vacancy_by_category": {"general": 442, "obc": 298, "sc": 165, "st": 82, "ews": 118},
            "applicant_count": 1290000, "selection_ratio": 0.000857,
            "cutoff_trend": {"general": 75.41, "obc": 74.75, "sc": 59.25, "st": 47.82},
            "difficulty_trend": {"overall": "hard"},
            "competition_pressure_score": 85.7, "reviewer_status": "locked",
            "source_basis": "official", "confidence_score": 0.95,
        },
        # 2024 prelims — draft, must be excluded
        {
            "id": "m3", "exam_id": "exam-1", "exam_cycle_id": "cy-2024",
            "exam_phase_id": "ph-prelims", "vacancy_total": 1056,
            "vacancy_by_category": {"general": 420},
            "cutoff_trend": {"general": 80.0},
            "reviewer_status": "draft", "source_basis": "manual", "confidence_score": 0.2,
        },
    ]
    return db


def test_competition_series_excludes_unreviewed_and_sorts_by_year():
    sb = SBStub(_metrics_db())
    series = competition_series(sb, "exam-1")
    assert [r["cycle_year"] for r in series] == [2022, 2023]
    assert series[0]["vacancy_total"] == 1011
    assert series[1]["competition_pressure_score"] == 85.7
    assert series[0]["phase_slug"] == "prelims"


def test_competition_series_empty_when_exam_missing():
    assert competition_series(SBStub({}), "") == []
    assert competition_series(SBStub({}), "exam-x") == []


def test_cutoff_series_pivots_by_category():
    sb = SBStub(_metrics_db())
    series = competition_series(sb, "exam-1")
    cuts = cutoff_series(series)
    assert sorted(cuts.keys()) == ["general", "obc", "sc", "st"]
    assert cuts["general"] == [
        {"year": 2022, "marks": 88.22, "phase_slug": "prelims"},
        {"year": 2023, "marks": 75.41, "phase_slug": "prelims"},
    ]


def test_cutoff_series_handles_list_payload_takes_last_value():
    series = [
        {"cycle_year": 2023, "phase_slug": "mains",
         "cutoff_trend": {"general": [None, 880, 905]}},
    ]
    cuts = cutoff_series(series)
    assert cuts["general"] == [{"year": 2023, "marks": 905.0, "phase_slug": "mains"}]


def test_cutoff_series_skips_garbage_payloads():
    series = [
        {"cycle_year": 2023, "phase_slug": "prelims", "cutoff_trend": "not-a-dict"},
        {"cycle_year": 2024, "phase_slug": "prelims",
         "cutoff_trend": {"general": "n/a", "obc": None, "ews": "57.1"}},
    ]
    cuts = cutoff_series(series)
    assert cuts == {"ews": [{"year": 2024, "marks": 57.1, "phase_slug": "prelims"}]}


def test_vacancy_series_collapses_phases_per_cycle():
    # Same cycle, two phases — vacancy_total should only count once.
    db = _metrics_db()
    db["exam_competition_metrics"].append({
        "id": "m4", "exam_id": "exam-1", "exam_cycle_id": "cy-2023",
        "exam_phase_id": "ph-mains", "vacancy_total": 1105,
        "vacancy_by_category": {"general": 442},
        "reviewer_status": "locked", "source_basis": "official", "confidence_score": 0.9,
    })
    sb = SBStub(db)
    series = competition_series(sb, "exam-1")
    vac = vacancy_series(series)
    years = [pt["year"] for pt in vac["total"]]
    assert years == [2022, 2023]
    assert vac["total"][1]["count"] == 1105
    assert [pt["count"] for pt in vac["by_category"]["general"]] == [410, 442]


def test_vacancy_series_empty_payload_when_no_data():
    assert vacancy_series([]) == {"total": [], "by_category": {}}


# ── J3 PR1: metric_kind-disposed rows + cutoff_by_category (resolutions §1) ──

from app.exam_intelligence.competition import cutoff_direction  # noqa: E402


def _disposed_db():
    return {
        "exam_cycles": [
            {"id": "cy-2023", "exam_id": "exam-2", "year": 2023, "cycle_name": "CSE 2023", "status": "completed"},
            {"id": "cy-2024", "exam_id": "exam-2", "year": 2024, "cycle_name": "CSE 2024", "status": "active"},
        ],
        "exam_phases": [
            {"id": "ph-prelims", "exam_id": "exam-2", "phase_name": "Prelims", "phase_slug": "prelims", "phase_order": 1},
        ],
        "exam_competition_metrics": [
            # cycle_summary, current published — owns vacancy.
            {
                "id": "cs-2023", "exam_id": "exam-2", "exam_cycle_id": "cy-2023", "exam_phase_id": None,
                "metric_kind": "cycle_summary", "is_current_published": True,
                "vacancy_total": 1105, "vacancy_by_category": {"general": 442},
                "applicant_count": 1290000, "reviewer_status": "locked", "source_basis": "official",
                "confidence_score": 0.95,
            },
            # A superseded (non-current) cycle_summary row for the same scope
            # must NOT leak into the series (OD-10 shared selector).
            {
                "id": "cs-2023-old", "exam_id": "exam-2", "exam_cycle_id": "cy-2023", "exam_phase_id": None,
                "metric_kind": "cycle_summary", "is_current_published": False,
                "vacancy_total": 999, "reviewer_status": "reviewed", "source_basis": "official",
                "confidence_score": 0.5,
            },
            # phase_cutoff, current published — owns cutoff.
            {
                "id": "pc-2023", "exam_id": "exam-2", "exam_cycle_id": "cy-2023", "exam_phase_id": "ph-prelims",
                "metric_kind": "phase_cutoff", "is_current_published": True,
                "cutoff_by_category": {"general": {"marks": 75.41, "max_marks": 200}},
                "difficulty_assessment": {"level": "harder", "basis": "cutoff rose vs prior cycle"},
                "reviewer_status": "locked", "source_basis": "official", "confidence_score": 0.9,
            },
            {
                "id": "pc-2024", "exam_id": "exam-2", "exam_cycle_id": "cy-2024", "exam_phase_id": "ph-prelims",
                "metric_kind": "phase_cutoff", "is_current_published": True,
                "cutoff_by_category": {"general": {"marks": 88.22, "max_marks": 200}},
                "reviewer_status": "reviewed", "source_basis": "official", "confidence_score": 0.9,
            },
        ],
    }


def test_select_current_excludes_non_published_disposed_rows():
    sb = SBStub(_disposed_db())
    series = competition_series(sb, "exam-2")
    # Exactly one entry per (cycle, phase); the superseded cs-2023-old must
    # not have created a second 2023/None row nor overwritten the vacancy.
    scoped = [r for r in series if r["cycle_year"] == 2023 and r["phase_slug"] == "prelims"]
    assert len(scoped) == 1
    assert scoped[0]["vacancy_total"] == 1105


def test_competition_series_merges_cycle_summary_and_phase_cutoff():
    sb = SBStub(_disposed_db())
    series = competition_series(sb, "exam-2")
    row = next(r for r in series if r["cycle_year"] == 2023 and r["phase_slug"] == "prelims")
    # Vacancy comes from the cycle_summary sibling; cutoff from phase_cutoff.
    assert row["vacancy_total"] == 1105
    assert row["cutoff_by_category"]["general"]["marks"] == 75.41
    assert row["difficulty_assessment"]["level"] == "harder"


def test_cutoff_series_prefers_cutoff_by_category_over_legacy_trend():
    series = [
        {
            "cycle_year": 2023, "phase_slug": "prelims",
            "cutoff_trend": {"general": 999},  # must be ignored when the new shape is present
            "cutoff_by_category": {"general": {"marks": 75.41, "max_marks": 200}},
        },
    ]
    cuts = cutoff_series(series)
    assert cuts["general"] == [{"year": 2023, "marks": 75.41, "phase_slug": "prelims", "max_marks": 200}]


def test_ratio_contract_fields_null_until_pr2_denominator():
    sb = SBStub(_disposed_db())
    series = competition_series(sb, "exam-2")
    row = next(r for r in series if r["cycle_year"] == 2023 and r["phase_slug"] == "prelims")
    assert row["selection_rate"] is None
    assert row["candidates_per_vacancy"] is None
    assert row["ratio_denominator"] is None
    # selection_ratio is preserved verbatim as the deprecated alias.
    assert row["selection_ratio_legacy"] == row["selection_ratio"]


def test_cutoff_direction_requires_two_comparable_points():
    assert cutoff_direction([{"year": 2023, "marks": 75.0, "max_marks": 200, "phase_slug": "prelims"}]) is None
    rising = cutoff_direction([
        {"year": 2022, "marks": 70.0, "max_marks": 200, "phase_slug": "prelims"},
        {"year": 2023, "marks": 75.0, "max_marks": 200, "phase_slug": "prelims"},
    ])
    assert rising == "rising"
    falling = cutoff_direction([
        {"year": 2022, "marks": 80.0, "max_marks": 200, "phase_slug": "prelims"},
        {"year": 2023, "marks": 75.0, "max_marks": 200, "phase_slug": "prelims"},
    ])
    assert falling == "falling"


def test_cutoff_direction_null_when_max_marks_differs():
    # Not comparable (different max_marks) — must return None, never guess.
    assert cutoff_direction([
        {"year": 2022, "marks": 70.0, "max_marks": 200, "phase_slug": "prelims"},
        {"year": 2023, "marks": 75.0, "max_marks": 100, "phase_slug": "prelims"},
    ]) is None
