"""Tests for A-PR2 section-wise selection + relaxation ladder (non-mutating).

Pins the core invariant — the selection pool EQUALS the readiness base pool —
plus the relaxation-ladder scaffolding, deterministic ordering, shortfall →
thin_bank propagation, and non-mutation for every outcome. Uses the same
in-memory SBStub as the diagnostics / A-PR1 tests; no live DB.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.exam_intelligence.diagnostics import selectable_mcq_depth
from app.study_os.mock_blueprint_selection import build_blueprint_with_selection
from tests.persona_questions._stub import SBStub

EXAM = "exam-cgl"
PHASE = "phase-tier1"

SECTIONS = [
    ("sec-quant", "subj-quant", "Quantitative Aptitude", 0),
    ("sec-reason", "subj-reason", "General Intelligence & Reasoning", 1),
    ("sec-eng", "subj-eng", "English Comprehension", 2),
]

_THRESHOLDS = dict(
    selectable_statuses=["published"],
    verified_status="verified",
    min_per_section=30,
    min_locked_coverage=1,
)


def _sb(**tables) -> SBStub:
    sb = SBStub()
    for name, rows in tables.items():
        sb.db[name] = list(rows)
    return sb


def _iso_past(days: int = 5) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _mcq(idx: int, subject_id: str, **over) -> dict:
    row = {
        "id": f"q-{idx:04d}",
        "exam_id": EXAM,
        "subject_id": subject_id,
        "topic_id": "topic-1",
        "difficulty": "medium",
        "question_type": "mcq",
        "reviewer_status": "published",
        "is_current": False,
        "is_current_based": False,
        "valid_until": None,
        "source_type": "authored",
        "source_kind": "authored",
    }
    row.update(over)
    return row


def _cgl_sb(*, bank=None, question_count=25) -> SBStub:
    return _sb(
        exam_phases=[
            {"id": PHASE, "exam_id": EXAM, "phase_name": "Tier 1",
             "phase_slug": "tier-1", "phase_order": 1, "duration_mins": 60},
        ],
        exam_phase_sections=[
            {
                "id": sid, "exam_phase_id": PHASE, "subject_id": subj,
                "section_label": label, "question_count": question_count,
                "marks": 50, "duration_mins": None, "negative_marking": "-0.50",
                "difficulty_level": "medium", "weightage_percent": 25.0,
                "sort_order": order,
            }
            for sid, subj, label, order in SECTIONS
        ],
        mock_question_bank=list(bank or []),
        exam_topic_coverage=[
            {"id": f"cov-{sid}", "exam_id": EXAM, "exam_phase_id": PHASE,
             "section_id": sid, "reviewer_status": "locked"}
            for sid, _subj, _label, _order in SECTIONS
        ],
    )


def _stocked_bank(per_subject: int) -> list:
    bank, n = [], 0
    for _sid, subj, _label, _order in SECTIONS:
        for _ in range(per_subject):
            bank.append(_mcq(n, subj))
            n += 1
    return bank


def _by_section(payload) -> dict:
    return {s["section_id"]: s for s in payload["selector_snapshot"]["sections"]}


# ── POOL-MATCH GUARD: selection pool ≡ readiness base pool ─────────────────────

def test_eligible_pool_equals_readiness_base_depth_per_section():
    sb = _cgl_sb(bank=_stocked_bank(35), question_count=25)
    payload = build_blueprint_with_selection(
        sb, exam_id=EXAM, exam_phase_id=PHASE, user_id="u", **_THRESHOLDS
    )
    depth = selectable_mcq_depth(sb, EXAM, ["published"])
    secs = _by_section(payload)
    for sid, subj, _label, _order in SECTIONS:
        base_for_subj = sum(
            g["count"] for g in depth["base_depth"] if g["subject_id"] == subj
        )
        assert secs[sid]["eligible_pool_count"] == base_for_subj == 35


# ── base-pool predicate exclusions ────────────────────────────────────────────

def test_current_affairs_rows_are_not_selected():
    bank = _stocked_bank(35)
    # Add current rows to one subject; they must not enter the base mock.
    bank += [_mcq(900 + i, "subj-quant", is_current=True) for i in range(5)]
    bank += [_mcq(950 + i, "subj-quant", is_current_based=True) for i in range(5)]
    sb = _cgl_sb(bank=bank, question_count=25)
    payload = build_blueprint_with_selection(
        sb, exam_id=EXAM, exam_phase_id=PHASE, user_id="u", **_THRESHOLDS
    )
    current_ids = {f"q-{900 + i:04d}" for i in range(5)} | {f"q-{950 + i:04d}" for i in range(5)}
    assert current_ids.isdisjoint(set(payload["question_ids"]))
    # Pool still counts only the 35 base rows for that subject.
    assert _by_section(payload)["sec-quant"]["eligible_pool_count"] == 35


def test_descriptive_non_answerable_rows_are_not_selected():
    bank = _stocked_bank(35)
    bank += [_mcq(800 + i, "subj-quant", question_type="comprehension") for i in range(5)]
    sb = _cgl_sb(bank=bank, question_count=25)
    payload = build_blueprint_with_selection(
        sb, exam_id=EXAM, exam_phase_id=PHASE, user_id="u", **_THRESHOLDS
    )
    descriptive_ids = {f"q-{800 + i:04d}" for i in range(5)}
    assert descriptive_ids.isdisjoint(set(payload["question_ids"]))
    assert _by_section(payload)["sec-quant"]["eligible_pool_count"] == 35


def test_e2e_fixtures_excluded_null_provenance_retained():
    bank = [_mcq(i, "subj-quant") for i in range(10)]                       # authored
    bank += [_mcq(100 + i, "subj-quant", source_type=None) for i in range(5)]   # NULL kept
    bank += [_mcq(200 + i, "subj-quant", source_type="e2e_fixture") for i in range(7)]  # excluded
    # other subjects unstocked → those sections thin, irrelevant here
    sb = _cgl_sb(bank=bank, question_count=12)
    payload = build_blueprint_with_selection(
        sb, exam_id=EXAM, exam_phase_id=PHASE, user_id="u", **_THRESHOLDS
    )
    sec = _by_section(payload)["sec-quant"]
    assert sec["eligible_pool_count"] == 15  # 10 authored + 5 NULL; 7 fixtures excluded
    fixture_ids = {f"q-{200 + i:04d}" for i in range(7)}
    assert fixture_ids.isdisjoint(set(payload["question_ids"]))


def test_expired_rows_are_not_selected():
    bank = [_mcq(i, "subj-quant") for i in range(10)]
    bank += [_mcq(300 + i, "subj-quant", valid_until=_iso_past()) for i in range(4)]
    sb = _cgl_sb(bank=bank, question_count=8)
    payload = build_blueprint_with_selection(
        sb, exam_id=EXAM, exam_phase_id=PHASE, user_id="u", **_THRESHOLDS
    )
    assert _by_section(payload)["sec-quant"]["eligible_pool_count"] == 10


# ── ready section: filled to question_count, deterministic ─────────────────────

def test_ready_section_filled_to_question_count_and_deterministic():
    sb = _cgl_sb(bank=_stocked_bank(35), question_count=25)
    p1 = build_blueprint_with_selection(
        sb, exam_id=EXAM, exam_phase_id=PHASE, user_id="u", **_THRESHOLDS
    )
    p2 = build_blueprint_with_selection(
        _cgl_sb(bank=_stocked_bank(35), question_count=25),
        exam_id=EXAM, exam_phase_id=PHASE, user_id="u", **_THRESHOLDS,
    )
    assert p1["outcome"] == "ready"
    secs = _by_section(p1)
    for sid, *_ in SECTIONS:
        assert secs[sid]["selected_count"] == 25
        assert secs[sid]["shortfall"] == 0
    assert len(p1["question_ids"]) == 75  # 3 sections × 25
    # Deterministic across independent calls.
    assert p1["question_ids"] == p2["question_ids"]
    # Stable id ordering within a section.
    assert p1["question_ids"] == sorted(p1["question_ids"])


# ── thin section: structured shortfall + thin_bank, no under-fill ──────────────

def test_thin_section_reports_shortfall_and_thin_bank():
    # 5 per subject: below min_per_section(30) AND below question_count(25).
    sb = _cgl_sb(bank=_stocked_bank(5), question_count=25)
    payload = build_blueprint_with_selection(
        sb, exam_id=EXAM, exam_phase_id=PHASE, user_id="u", **_THRESHOLDS
    )
    assert payload["outcome"] == "thin_bank"
    secs = _by_section(payload)
    for sid, *_ in SECTIONS:
        assert secs[sid]["selected_count"] == 5      # no under-fill beyond pool
        assert secs[sid]["shortfall"] == 20          # 25 - 5
    assert len(payload["question_ids"]) == 15        # exactly the available rows


def test_ready_per_readiness_but_selection_shortfall_downgrades_to_thin_bank():
    # base_pool 40 ≥ min_per_section(30) → readiness ready; but question_count 100
    # > pool → selection short → must downgrade to thin_bank, never ready.
    sb = _cgl_sb(bank=_stocked_bank(40), question_count=100)
    payload = build_blueprint_with_selection(
        sb, exam_id=EXAM, exam_phase_id=PHASE, user_id="u", **_THRESHOLDS
    )
    assert payload["readiness_snapshot"]["summary"]["ready"] == 3  # readiness said ready
    assert payload["outcome"] == "thin_bank"                       # selection downgraded
    assert payload.get("selection_downgraded_ready_to_thin_bank") is True
    assert payload["section_shortfall"]
    assert all(s["shortfall"] == 60 for s in payload["section_shortfall"])


# ── relaxation ladder scaffolding ─────────────────────────────────────────────

def test_ladder_order_and_inert_noop_rungs():
    sb = _cgl_sb(bank=_stocked_bank(35), question_count=25)
    payload = build_blueprint_with_selection(
        sb, exam_id=EXAM, exam_phase_id=PHASE, user_id="u", **_THRESHOLDS
    )
    snap = payload["selector_snapshot"]
    assert snap["ladder"] == [
        "exposure_cooldown", "personalization", "source_mix", "difficulty_mix",
    ]
    assert "section_count" in snap["non_relaxable"]
    rungs = _by_section(payload)["sec-quant"]["rungs"]
    by_name = {r["rung"]: r for r in rungs}
    # Exposure (A-PR4) + personalization (A-PR5) present but inert — never relax.
    assert by_name["exposure_cooldown"]["status"].startswith("inert")
    assert by_name["exposure_cooldown"]["relaxed"] is False
    assert by_name["personalization"]["status"].startswith("inert")
    assert by_name["personalization"]["relaxed"] is False
    # No mix targets in the envelope → source-mix not enforced; difficulty straight.
    assert by_name["source_mix"]["status"] == "not_applicable_no_targets"
    assert by_name["difficulty_mix"]["status"] == "applied_no_mix"


def test_source_mix_enforced_only_when_envelope_carries_targets():
    # Inject a Wave-5-style source_mix onto the section envelope via metadata that
    # A-PR1 does not yet emit; the selector must read it defensively.
    sb = _cgl_sb(bank=_stocked_bank(35), question_count=25)
    # Monkey-add source_mix to the phase section row so the envelope carries it.
    for row in sb.db["exam_phase_sections"]:
        row["source_mix"] = {"authored": 1.0}
    # The envelope (section_snapshot) is built by A-PR1 and won't include source_mix
    # since A-PR1 doesn't select those columns — so this stays not_applicable,
    # proving A-PR2 only enforces what the ENVELOPE carries, not raw table columns.
    payload = build_blueprint_with_selection(
        sb, exam_id=EXAM, exam_phase_id=PHASE, user_id="u", **_THRESHOLDS
    )
    rung = {r["rung"]: r for r in _by_section(payload)["sec-quant"]["rungs"]}["source_mix"]
    assert rung["status"] == "not_applicable_no_targets"


# ── non-mutation for every outcome ────────────────────────────────────────────

@pytest.mark.parametrize(
    "make_sb",
    [
        lambda: _cgl_sb(bank=_stocked_bank(35), question_count=25),   # ready
        lambda: _cgl_sb(bank=_stocked_bank(5), question_count=25),    # thin_bank
        lambda: _sb(                                                  # blocked
            exam_phases=[{"id": PHASE, "exam_id": EXAM}],
            exam_phase_sections=[], mock_question_bank=[], exam_topic_coverage=[],
        ),
    ],
)
def test_non_mutating_for_every_outcome(make_sb):
    sb = make_sb()
    payload = build_blueprint_with_selection(
        sb, exam_id=EXAM, exam_phase_id=PHASE, user_id="u", **_THRESHOLDS
    )
    assert payload["persisted"] is False
    assert sb.db.get("mock_generated_blueprints", []) == []
    assert sb.db.get("mock_attempts", []) == []


def test_blocked_outcome_leaves_selection_empty():
    sb = _sb(
        exam_phases=[{"id": PHASE, "exam_id": EXAM}],
        exam_phase_sections=[], mock_question_bank=[], exam_topic_coverage=[],
    )
    payload = build_blueprint_with_selection(
        sb, exam_id=EXAM, exam_phase_id=PHASE, user_id="u", **_THRESHOLDS
    )
    assert payload["outcome"] == "blocked"
    assert payload["question_ids"] == []
    assert payload["selector_snapshot"]["sections"] == []
