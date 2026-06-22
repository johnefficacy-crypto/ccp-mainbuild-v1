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


# ── MCQ-only safety restriction: msq/integer never generated-selectable (§4a/D1)

def test_msq_and_integer_rows_are_not_generated_selectable():
    """A-PR2 selection is MCQ-only (it shares ``_SELECTABLE_QUESTION_TYPES`` with
    readiness). msq/integer rows that are otherwise fully eligible (published,
    right subject, mapped, non-expired, not current, not a fixture) must neither
    enter ``question_ids`` nor inflate the eligible pool — the live scorer is
    single-option. A subject with 25 MCQ + 5 msq + 5 integer counts as 25
    selectable, NOT 35. See §4a / D1 of the decision doc."""
    bank = [_mcq(i, "subj-quant") for i in range(25)]                          # 25 MCQ
    bank += [_mcq(500 + i, "subj-quant", question_type="msq") for i in range(5)]
    bank += [_mcq(600 + i, "subj-quant", question_type="integer") for i in range(5)]
    sb = _cgl_sb(bank=bank, question_count=25)
    payload = build_blueprint_with_selection(
        sb, exam_id=EXAM, exam_phase_id=PHASE, user_id="u", **_THRESHOLDS
    )
    non_mcq_ids = (
        {f"q-{500 + i:04d}" for i in range(5)}
        | {f"q-{600 + i:04d}" for i in range(5)}
    )
    assert non_mcq_ids.isdisjoint(set(payload["question_ids"]))
    # Counts the 25 MCQs only — the 10 msq/integer rows do not inflate the pool.
    assert _by_section(payload)["sec-quant"]["eligible_pool_count"] == 25


def test_selection_pool_equals_readiness_under_mcq_only_restriction():
    """selection ≡ readiness still holds with the MCQ-only constant: a mixed bank
    yields the SAME count on the A-PR2 eligible pool and the readiness base depth,
    because both filter on the single shared ``_SELECTABLE_QUESTION_TYPES``."""
    from app.exam_intelligence.diagnostics import _SELECTABLE_QUESTION_TYPES

    assert _SELECTABLE_QUESTION_TYPES == ("mcq",)
    bank = [_mcq(i, "subj-quant") for i in range(20)]                          # 20 MCQ
    bank += [_mcq(700 + i, "subj-quant", question_type="msq") for i in range(8)]
    bank += [_mcq(800 + i, "subj-quant", question_type="integer") for i in range(8)]
    sb = _cgl_sb(bank=bank, question_count=15)
    payload = build_blueprint_with_selection(
        sb, exam_id=EXAM, exam_phase_id=PHASE, user_id="u", **_THRESHOLDS
    )
    depth = selectable_mcq_depth(sb, EXAM, ["published"])
    base_for_quant = sum(
        g["count"] for g in depth["base_depth"] if g["subject_id"] == "subj-quant"
    )
    assert _by_section(payload)["sec-quant"]["eligible_pool_count"] == base_for_quant == 20


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


# ── source-mix max_ratio enforcement ─────────────────────────────────────────

from app.study_os.mock_blueprint_selection import _select_section  # noqa: E402


def _pool_row(qid: str, source_kind: str) -> dict:
    return {"id": qid, "source_kind": source_kind, "difficulty": "medium"}


class TestSourceMixMaxRatio:
    """max_ratio enforcement: correct status for full vs partial enforcement."""

    def test_max_ratio_fully_enforced_when_backfill_available(self):
        # 8 pyq + 5 authored (13 total), target 10, max_ratio 0.5 for pyq
        # Initial selection: 8 pyq + 2 authored. After removing 3 excess pyq, backfill
        # the 3 remaining authored → 5 pyq + 5 authored = 10 rows, ratio exactly 0.5.
        pool = [_pool_row(f"pyq-{i}", "pyq") for i in range(8)]
        pool += [_pool_row(f"auth-{i}", "authored") for i in range(5)]
        constraints = {"pyq": {"min": 0.0, "max": 0.5, "fallback": "relax_to_available"}}
        chosen_ids, rungs = _select_section(
            pool, 10,
            source_mix=None, source_mix_constraints=constraints, difficulty_mix=None,
        )
        pool_by_id = {r["id"]: r for r in pool}
        pyq_count = sum(1 for qid in chosen_ids if pool_by_id[qid]["source_kind"] == "pyq")
        n = len(chosen_ids)
        assert n == 10
        assert pyq_count <= 5  # max 50% of 10
        max_rungs = [r for r in rungs if r["rung"] == "source_mix_max_constraint"]
        assert len(max_rungs) == 1
        assert max_rungs[0]["status"] == "enforced_max_ratio"
        assert max_rungs[0]["final_ratio"] <= 0.5 + 1e-9

    def test_max_ratio_partial_when_backfill_insufficient(self):
        # 8 pyq + 2 authored (10 total), target 10, max_ratio 0.5 for pyq
        # After removing 3 pyq: 5 pyq + 2 authored = 7 rows; no authored left to backfill.
        # Final ratio = 5/7 ≈ 0.71 > 0.5 → status must be enforced_max_ratio_partial.
        pool = [_pool_row(f"pyq-{i}", "pyq") for i in range(8)]
        pool += [_pool_row(f"auth-{i}", "authored") for i in range(2)]
        constraints = {"pyq": {"min": 0.0, "max": 0.5, "fallback": "relax_to_available"}}
        chosen_ids, rungs = _select_section(
            pool, 10,
            source_mix=None, source_mix_constraints=constraints, difficulty_mix=None,
        )
        pool_by_id = {r["id"]: r for r in pool}
        pyq_count = sum(1 for qid in chosen_ids if pool_by_id[qid]["source_kind"] == "pyq")
        n = len(chosen_ids)
        final_ratio = pyq_count / n if n > 0 else 0.0
        assert final_ratio > 0.5  # constraint could not be fully met
        max_rungs = [r for r in rungs if r["rung"] == "source_mix_max_constraint"]
        assert len(max_rungs) == 1
        assert max_rungs[0]["status"] == "enforced_max_ratio_partial"
        assert max_rungs[0]["final_ratio"] > 0.5

    def test_two_simultaneous_max_constraints_are_compositional(self):
        # target=10; pool: 8 pyq + 8 authored (16 total); both capped at max 0.5.
        # Pool order puts pyq first, so initial selection is pyq-0..7 + auth-0..1 (10 rows).
        # Combined caps: int(0.5 * 10) = 5 per source.
        # Single-pass enforcement: keep pyq-0..4 (5), keep auth-0..1 (2), drop pyq-5..7.
        # Backfill authored up to authored cap (5): add auth-2..4.
        # Final: 5 pyq + 5 authored = 10.  pyq-5, pyq-6, pyq-7 must NOT reappear.
        pool = [_pool_row(f"pyq-{i}", "pyq") for i in range(8)]
        pool += [_pool_row(f"auth-{i}", "authored") for i in range(8)]
        constraints = {
            "pyq": {"min": 0.0, "max": 0.5, "fallback": "relax_to_available"},
            "authored": {"min": 0.0, "max": 0.5, "fallback": "relax_to_available"},
        }
        chosen_ids, rungs = _select_section(
            pool, 10,
            source_mix=None, source_mix_constraints=constraints, difficulty_mix=None,
        )
        pool_by_id = {r["id"]: r for r in pool}
        n = len(chosen_ids)
        pyq_count = sum(1 for qid in chosen_ids if pool_by_id[qid]["source_kind"] == "pyq")
        authored_count = sum(1 for qid in chosen_ids if pool_by_id[qid]["source_kind"] == "authored")
        assert n == 10
        assert pyq_count <= 5
        assert authored_count <= 5
        max_rungs = [r for r in rungs if r["rung"] == "source_mix_max_constraint"]
        assert len(max_rungs) >= 1
        assert all(r["status"] == "enforced_max_ratio" for r in max_rungs)
        # Confirm removed pyq rows were not re-added during authored backfill
        assert not any(qid in {"pyq-5", "pyq-6", "pyq-7"} for qid in chosen_ids)
