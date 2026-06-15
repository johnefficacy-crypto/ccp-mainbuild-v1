"""Tests for the mock content-readiness diagnostics (pure-read).

Mirrors test_diagnostics.py: in-memory SBStub fixtures, no live DB. Covers the
census vocabulary discovery, base/current pool segmentation, the three-signal
source distribution, and the verdict state machine with caller-supplied
thresholds.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.exam_intelligence.diagnostics import (
    _chunked,
    _fetch_all,
    assemble_mock_readiness_report,
    locked_coverage_count,
    readiness_verdict,
    section_structure_completeness,
    selectable_mcq_depth,
    source_distribution,
    status_value_census,
    verified_pyq_tag_depth,
)
from tests.persona_questions._stub import SBStub

EXAM = "exam-1"
PHASE = "phase-1"
SEC = "sec-1"
SUBJ = "subj-1"


def _iso_future(days: int = 30) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def _iso_past(days: int = 30) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _sb(**tables) -> SBStub:
    sb = SBStub()
    for name, rows in tables.items():
        sb.db[name] = list(rows)
    return sb


def _mcq(idx: int, **over) -> dict:
    row = {
        "id": f"q-{idx}",
        "exam_id": EXAM,
        "subject_id": SUBJ,
        "topic_id": "topic-1",
        "difficulty": "medium",
        "question_type": "mcq",
        "reviewer_status": "verified",
        "is_current": False,
        "is_current_based": False,
        "valid_until": None,
        "source_type": "authored",
        "source_kind": "authored",
    }
    row.update(over)
    return row


def _stocked_sb(*, n_questions: int, coverage_status: str = "locked") -> SBStub:
    """A single-section exam with complete structure + n selectable MCQs."""
    return _sb(
        exam_phases=[{"id": PHASE, "exam_id": EXAM, "phase_name": "P", "phase_slug": "p"}],
        exam_phase_sections=[
            {
                "id": SEC,
                "exam_phase_id": PHASE,
                "subject_id": SUBJ,
                "section_label": "A",
                "question_count": 100,
                "marks": 200,
                "duration_mins": 120,
                "sort_order": 0,
            }
        ],
        mock_question_bank=[_mcq(i) for i in range(n_questions)],
        exam_topic_coverage=[
            {"id": "cov-1", "exam_id": EXAM, "exam_phase_id": PHASE,
             "section_id": SEC, "reviewer_status": coverage_status}
        ],
    )


def _chain(sb: SBStub):
    structure = section_structure_completeness(sb, EXAM)
    depth = selectable_mcq_depth(sb, EXAM, ["verified", "published"])
    coverage = locked_coverage_count(sb, EXAM)
    return structure, depth, coverage


# ── Paging / chunking helpers (corpus totals must not cap at the page limit) ──

def test_fetch_all_pages_until_short_page_and_concatenates():
    batches = [
        [{"id": 1}, {"id": 2}],
        [{"id": 3}, {"id": 4}],
        [{"id": 5}],  # short page -> stop
    ]
    seq = iter(batches)

    class _Exec:
        def __init__(self, data):
            self.data = data

    class _Page:
        def range(self, *_a):
            return self

        def execute(self):
            return _Exec(next(seq))

    out = _fetch_all(lambda: _Page(), page_size=2)
    assert [r["id"] for r in out] == [1, 2, 3, 4, 5]


def test_fetch_all_stops_on_exact_multiple_with_empty_trailing_page():
    batches = [[{"id": 1}, {"id": 2}], []]  # full page then empty -> stop
    seq = iter(batches)

    class _Exec:
        def __init__(self, data):
            self.data = data

    class _Page:
        def range(self, *_a):
            return self

        def execute(self):
            return _Exec(next(seq))

    out = _fetch_all(lambda: _Page(), page_size=2)
    assert [r["id"] for r in out] == [1, 2]


def test_chunked_splits_large_in_lists():
    assert _chunked([], size=2) == []
    assert _chunked([1, 2, 3, 4, 5], size=2) == [[1, 2], [3, 4], [5]]


# ── A. status_value_census ────────────────────────────────────────────────────

def test_census_returns_distinct_value_count_maps():
    sb = _sb(
        mock_question_bank=[
            {"id": "a", "reviewer_status": "verified"},
            {"id": "b", "reviewer_status": "verified"},
            {"id": "c", "reviewer_status": "draft"},
        ],
        pyq_questions=[{"id": "q", "reviewer_status": "pending"}],
        pyq_question_topic_tags=[{"id": "t", "reviewer_status": "verified"}],
        pyq_papers=[{"id": "p", "trust_status": "verified"}],
        exam_topic_coverage=[{"id": "cov", "reviewer_status": "locked"}],
    )
    census = status_value_census(sb)
    assert census["mock_question_bank.reviewer_status"] == {"verified": 2, "draft": 1}
    assert census["pyq_questions.reviewer_status"] == {"pending": 1}
    assert census["pyq_question_topic_tags.reviewer_status"] == {"verified": 1}
    assert census["pyq_papers.trust_status"] == {"verified": 1}
    assert census["exam_topic_coverage.reviewer_status"] == {"locked": 1}


def test_census_reports_nulls_without_assuming_vocabulary():
    sb = _sb(
        mock_question_bank=[{"id": "a", "reviewer_status": None}],
        pyq_questions=[],
        pyq_question_topic_tags=[],
        pyq_papers=[],
        exam_topic_coverage=[],
    )
    census = status_value_census(sb)
    assert census["mock_question_bank.reviewer_status"] == {"<null>": 1}
    assert census["pyq_questions.reviewer_status"] == {}


# ── B. section_structure_completeness ─────────────────────────────────────────

def test_structure_flags_missing_fields():
    sb = _sb(
        exam_phases=[{"id": PHASE, "exam_id": EXAM}],
        exam_phase_sections=[
            {"id": SEC, "exam_phase_id": PHASE, "subject_id": SUBJ, "section_label": "A",
             "question_count": None, "marks": 10, "duration_mins": None, "sort_order": 0},
        ],
    )
    out = section_structure_completeness(sb, EXAM)
    assert out["section_count"] == 1
    assert out["sections_missing_structure"] == 1
    sec = out["sections"][0]
    assert sec["complete"] is False
    assert set(sec["missing"]) == {"question_count", "duration_mins"}


def test_structure_no_phases_returns_empty():
    sb = _sb(exam_phases=[], exam_phase_sections=[])
    out = section_structure_completeness(sb, EXAM)
    assert out["section_count"] == 0
    assert out["sections"] == []


def test_structure_duration_falls_back_to_phase_common_timer():
    # Common-timer phase: phase.duration_mins set, section duration NULL by
    # design -> section is still structurally complete (duration_source=phase).
    sb = _sb(
        exam_phases=[{"id": PHASE, "exam_id": EXAM, "duration_mins": 120}],
        exam_phase_sections=[
            {"id": SEC, "exam_phase_id": PHASE, "subject_id": SUBJ, "section_label": "A",
             "question_count": 100, "marks": 200, "duration_mins": None, "sort_order": 0},
        ],
    )
    sec = section_structure_completeness(sb, EXAM)["sections"][0]
    assert sec["complete"] is True
    assert sec["duration_source"] == "phase"
    assert "duration_mins" not in sec["missing"]


def test_structure_duration_missing_when_neither_section_nor_phase():
    sb = _sb(
        exam_phases=[{"id": PHASE, "exam_id": EXAM}],  # no phase-level duration
        exam_phase_sections=[
            {"id": SEC, "exam_phase_id": PHASE, "subject_id": SUBJ, "section_label": "A",
             "question_count": 100, "marks": 200, "duration_mins": None, "sort_order": 0},
        ],
    )
    sec = section_structure_completeness(sb, EXAM)["sections"][0]
    assert sec["duration_source"] is None
    assert "duration_mins" in sec["missing"]


# ── C. selectable_mcq_depth ───────────────────────────────────────────────────

def test_selectable_depth_segments_current_out_of_base_pool():
    sb = _sb(
        mock_question_bank=[
            _mcq(1),
            _mcq(2),
            _mcq(3),
            _mcq(4, is_current=True),
            _mcq(5, is_current_based=True),
        ],
    )
    out = selectable_mcq_depth(sb, EXAM, ["verified", "published"])
    assert out["base_total"] == 3
    assert out["current_total"] == 2
    # base and current are reported separately, never folded together.
    assert sum(g["count"] for g in out["base_depth"]) == 3
    assert sum(g["count"] for g in out["current_depth"]) == 2


def test_selectable_depth_excludes_expired_and_non_selectable():
    sb = _sb(
        mock_question_bank=[
            _mcq(1),
            _mcq(2, valid_until=_iso_past()),         # expired
            _mcq(3, reviewer_status="draft"),          # not selectable status
            _mcq(4, question_type="comprehension"),    # not an answerable type
            _mcq(5, valid_until=_iso_future()),        # future expiry: kept
        ],
    )
    out = selectable_mcq_depth(sb, EXAM, ["verified", "published"])
    assert out["base_total"] == 2  # q-1 and q-5 only


def test_selectable_depth_empty_when_no_statuses_passed():
    sb = _stocked_sb(n_questions=5)
    out = selectable_mcq_depth(sb, EXAM, [])
    assert out["base_total"] == 0
    assert out["base_depth"] == []


# ── D. source_distribution ────────────────────────────────────────────────────

def test_source_distribution_segments_base_and_current_over_eligible_pool():
    sb = _sb(
        mock_question_bank=[
            _mcq(1, source_type="pyq", source_kind="pyq"),
            _mcq(2, source_type="authored", source_kind="authored"),
            _mcq(3, source_type="current_event", source_kind="current_event",
                 is_current=True),                       # current segment
            _mcq(4, source_type="pyq", reviewer_status="draft"),   # not selectable
            _mcq(5, source_type="pyq", question_type="comprehension"),  # not answerable
            _mcq(6, source_type="pyq", valid_until=_iso_past()),   # expired
        ],
        mock_question_sources=[
            {"question_id": "q-1", "source_kind": "pyq"},
            {"question_id": "q-2", "source_kind": "standard_source"},  # disagrees w/ bank
            {"question_id": "q-3", "source_kind": "current_event"},
        ],
    )
    out = source_distribution(sb, EXAM, ["verified", "published"])
    base = out["base_source_distribution"]
    current = out["current_source_distribution"]
    # Base pool = q-1, q-2 only (q-4/5/6 excluded by the eligible-pool filter).
    assert base["by_bank_source_type"] == {"pyq": 1, "authored": 1}
    assert base["by_bank_source_kind"] == {"pyq": 1, "authored": 1}
    assert base["by_sources_table_source_kind"] == {"pyq": 1, "standard_source": 1}
    # Current pool = q-3 only, segmented OUT of base.
    assert current["by_bank_source_type"] == {"current_event": 1}
    assert current["by_sources_table_source_kind"] == {"current_event": 1}


# ── E. verified_pyq_tag_depth ─────────────────────────────────────────────────

def test_verified_pyq_tag_depth_filters_all_three_gates():
    sb = _sb(
        pyq_papers=[
            {"id": "p1", "exam_id": EXAM, "trust_status": "verified"},
            {"id": "p2", "exam_id": EXAM, "trust_status": "pending"},  # paper not trusted
        ],
        pyq_questions=[
            {"id": "vq1", "pyq_paper_id": "p1", "reviewer_status": "verified"},
            {"id": "vq2", "pyq_paper_id": "p1", "reviewer_status": "pending"},  # q not verified
            {"id": "vq3", "pyq_paper_id": "p2", "reviewer_status": "verified"},  # wrong paper
        ],
        pyq_question_topic_tags=[
            {"question_id": "vq1", "topic_id": "t1", "tag_role": "primary", "reviewer_status": "verified"},
            {"question_id": "vq1", "topic_id": "t1", "tag_role": "primary", "reviewer_status": "pending"},  # tag not verified
            {"question_id": "vq2", "topic_id": "t1", "tag_role": "primary", "reviewer_status": "verified"},  # q gate fails
        ],
    )
    out = verified_pyq_tag_depth(sb, EXAM, "verified")
    assert out["total"] == 1
    assert out["depth"] == [{"topic_id": "t1", "tag_role": "primary", "count": 1}]


# ── F. locked_coverage_count ──────────────────────────────────────────────────

def test_locked_coverage_count_breaks_down_by_status_and_section():
    sb = _sb(
        exam_topic_coverage=[
            {"id": "c1", "exam_id": EXAM, "section_id": SEC, "reviewer_status": "locked"},
            {"id": "c2", "exam_id": EXAM, "section_id": SEC, "reviewer_status": "reviewed"},
            {"id": "c3", "exam_id": EXAM, "section_id": "sec-2", "reviewer_status": "locked"},
        ],
    )
    out = locked_coverage_count(sb, EXAM)
    assert out["total"] == 3
    assert out["by_status"] == {"locked": 2, "reviewed": 1}
    assert out["by_section"][SEC] == {"locked": 1, "reviewed": 1}
    assert out["by_section"]["sec-2"] == {"locked": 1}


# ── G. readiness_verdict ──────────────────────────────────────────────────────

def test_verdict_ready_for_fully_stocked_exam():
    structure, depth, coverage = _chain(_stocked_sb(n_questions=40))
    verdict = readiness_verdict(
        structure, depth, coverage, min_per_section=30, min_locked_coverage=1
    )
    sec = verdict["sections"][0]
    assert sec["verdict"] == "ready"
    assert sec["reasons"] == []
    assert verdict["summary"]["ready"] == 1


def test_verdict_thin_bank_when_pool_below_threshold():
    structure, depth, coverage = _chain(_stocked_sb(n_questions=5))
    verdict = readiness_verdict(
        structure, depth, coverage, min_per_section=30, min_locked_coverage=1
    )
    sec = verdict["sections"][0]
    assert sec["verdict"] == "thin_bank"
    assert sec["reasons"] == ["thin_mcq_pool"]


def test_verdict_blocked_when_no_locked_coverage():
    # coverage rows exist but are 'reviewed', not 'locked' → locked count is 0.
    structure, depth, coverage = _chain(
        _stocked_sb(n_questions=40, coverage_status="reviewed")
    )
    verdict = readiness_verdict(
        structure, depth, coverage, min_per_section=30, min_locked_coverage=1
    )
    sec = verdict["sections"][0]
    assert sec["verdict"] == "blocked"
    assert "no_locked_coverage" in sec["reasons"]


def test_verdict_counts_phase_level_sectionless_locked_coverage():
    # Locked coverage recorded at phase level (section_id NULL) applies to the
    # section and must NOT yield a false no_locked_coverage block.
    sb = _sb(
        exam_phases=[{"id": PHASE, "exam_id": EXAM, "duration_mins": 120}],
        exam_phase_sections=[
            {"id": SEC, "exam_phase_id": PHASE, "subject_id": SUBJ, "section_label": "A",
             "question_count": 100, "marks": 200, "duration_mins": 120, "sort_order": 0},
        ],
        mock_question_bank=[_mcq(i) for i in range(40)],
        exam_topic_coverage=[
            {"id": "cov-pl", "exam_id": EXAM, "exam_phase_id": PHASE,
             "section_id": None, "reviewer_status": "locked"},  # phase-level
        ],
    )
    structure, depth, coverage = _chain(sb)
    verdict = readiness_verdict(
        structure, depth, coverage, min_per_section=30, min_locked_coverage=1
    )
    sec = verdict["sections"][0]
    assert sec["verdict"] == "ready"
    assert "no_locked_coverage" not in sec["reasons"]
    assert sec["locked_coverage"] == 1


def test_verdict_blocked_when_no_sections():
    sb = _sb(exam_phases=[], exam_phase_sections=[], mock_question_bank=[], exam_topic_coverage=[])
    structure, depth, coverage = _chain(sb)
    verdict = readiness_verdict(
        structure, depth, coverage, min_per_section=1, min_locked_coverage=1
    )
    assert verdict["sections"][0]["verdict"] == "blocked"
    assert verdict["sections"][0]["reasons"] == ["no_sections"]


def test_verdict_thresholds_are_honoured_as_passed():
    # Same fixture, different thresholds → different verdicts (no baked default).
    structure, depth, coverage = _chain(_stocked_sb(n_questions=5))
    lenient = readiness_verdict(
        structure, depth, coverage, min_per_section=3, min_locked_coverage=1
    )
    strict = readiness_verdict(
        structure, depth, coverage, min_per_section=10, min_locked_coverage=1
    )
    assert lenient["sections"][0]["verdict"] == "ready"
    assert strict["sections"][0]["verdict"] == "thin_bank"


def test_verdict_emits_pool_scope_subject():
    # Fix 4: consumers must know the base pool is subject-level, not selector.
    structure, depth, coverage = _chain(_stocked_sb(n_questions=40))
    verdict = readiness_verdict(
        structure, depth, coverage, min_per_section=30, min_locked_coverage=1
    )
    assert verdict["pool_scope"] == "subject"
    assert depth["pool_scope"] == "subject"


# ── Phase scoping (Fix 2) ─────────────────────────────────────────────────────

def _two_phase_sb() -> SBStub:
    """Two phases, each with its own subject/section/coverage.

    Phase 1 is fully stocked (ready); phase 2's subject has a thin bank
    (thin_bank). Proves verdicts are grouped per phase and not cross-polluted.
    """
    P1, P2 = "phase-1", "phase-2"
    SEC1, SEC2 = "sec-1", "sec-2"
    SUBJ1, SUBJ2 = "subj-1", "subj-2"
    bank = (
        [_mcq(i, subject_id=SUBJ1) for i in range(40)]
        + [_mcq(100 + i, subject_id=SUBJ2) for i in range(3)]  # thin
    )
    return _sb(
        exam_phases=[
            {"id": P1, "exam_id": EXAM, "phase_name": "Prelims", "phase_slug": "prelims", "phase_order": 1},
            {"id": P2, "exam_id": EXAM, "phase_name": "Mains", "phase_slug": "mains", "phase_order": 2},
        ],
        exam_phase_sections=[
            {"id": SEC1, "exam_phase_id": P1, "subject_id": SUBJ1, "section_label": "A",
             "question_count": 100, "marks": 200, "duration_mins": 120, "sort_order": 0},
            {"id": SEC2, "exam_phase_id": P2, "subject_id": SUBJ2, "section_label": "B",
             "question_count": 100, "marks": 200, "duration_mins": 120, "sort_order": 0},
        ],
        mock_question_bank=bank,
        exam_topic_coverage=[
            {"id": "cov-1", "exam_id": EXAM, "exam_phase_id": P1, "section_id": SEC1, "reviewer_status": "locked"},
            {"id": "cov-2", "exam_id": EXAM, "exam_phase_id": P2, "section_id": SEC2, "reviewer_status": "locked"},
        ],
    )


def test_assembler_groups_verdicts_per_phase_without_cross_pollution():
    report = assemble_mock_readiness_report(
        _two_phase_sb(),
        exam_id=EXAM,
        selectable_statuses=["verified", "published"],
        min_per_section=30,
        min_locked_coverage=1,
    )
    phases = {p["phase_slug"]: p for p in report["phases"]}
    assert set(phases) == {"prelims", "mains"}
    # Each phase verdict is scoped to its own section/subject, not merged.
    prelims_sec = phases["prelims"]["readiness_verdict"]["sections"][0]
    mains_sec = phases["mains"]["readiness_verdict"]["sections"][0]
    assert prelims_sec["section_label"] == "A"
    assert prelims_sec["verdict"] == "ready"
    assert prelims_sec["base_pool"] == 40
    assert mains_sec["section_label"] == "B"
    assert mains_sec["verdict"] == "thin_bank"        # thin subject does not
    assert mains_sec["base_pool"] == 3                # borrow phase-1's depth
    # Each phase verdict carries its own exam_phase_id.
    assert phases["prelims"]["readiness_verdict"]["exam_phase_id"] == "phase-1"
    assert phases["mains"]["readiness_verdict"]["exam_phase_id"] == "phase-2"


def test_assembler_scopes_to_single_phase_when_phase_id_given():
    report = assemble_mock_readiness_report(
        _two_phase_sb(),
        exam_id=EXAM,
        exam_phase_id="phase-2",
        selectable_statuses=["verified", "published"],
        min_per_section=30,
        min_locked_coverage=1,
    )
    assert [p["phase_slug"] for p in report["phases"]] == ["mains"]
    assert report["phases"][0]["readiness_verdict"]["sections"][0]["verdict"] == "thin_bank"


# ── Assembler ─────────────────────────────────────────────────────────────────

def test_assembler_runs_census_and_marks_skipped_blocks():
    sb = _stocked_sb(n_questions=40)
    # No selectable statuses / thresholds → status-dependent blocks are skipped.
    report = assemble_mock_readiness_report(sb, exam_id=EXAM)
    assert "status_value_census" in report
    assert "selectable_mcq_depth" not in report     # exam-level, needs statuses
    # Per-phase structure / coverage are always computed.
    phase = report["phases"][0]
    assert "section_structure" in phase
    assert "locked_coverage" in phase
    assert "readiness_verdict" not in phase
    assert any("selectable_mcq_depth" in s for s in report["skipped"])


def test_assembler_full_report_when_inputs_supplied():
    sb = _stocked_sb(n_questions=40)
    report = assemble_mock_readiness_report(
        sb,
        exam_id=EXAM,
        selectable_statuses=["verified", "published"],
        verified_status="verified",
        min_per_section=30,
        min_locked_coverage=1,
    )
    assert "selectable_mcq_depth" in report          # exam-level, top of report
    assert "source_distribution" in report
    phase = report["phases"][0]
    assert phase["readiness_verdict"]["sections"][0]["verdict"] == "ready"
    assert "verified_pyq_tag_depth" in phase
    assert report["skipped"] == []
