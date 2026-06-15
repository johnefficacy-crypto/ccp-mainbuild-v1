"""Tests for the exam-realistic generated-mock BLUEPRINT PAYLOAD service (A-PR1).

NON-MUTATING service: it emits a blueprint payload + the diagnostic readiness
verdict and returns. It writes NOTHING to mock_generated_blueprints and starts
NO attempt. These tests pin:

  * the thin_bank canary (SSC CGL Tier 1 shape: authored structure present, base
    MCQ pool ~0) → phase summary thin_bank + per-section shortfall,
  * blocked / no_sections (a phase with no authored sections) → envelope absent,
  * non-mutating for EVERY outcome (no blueprint row, no attempt),
  * readiness reflects AUTHORED sections only (no self-reported official
    completeness),
  * thresholds are caller-supplied (no defaults baked into the service body).

Uses the same in-memory SBStub as the diagnostics tests; no live DB.
"""
from __future__ import annotations

import pytest

from app.study_os.mock_blueprint import build_blueprint_payload
from tests.persona_questions._stub import SBStub

EXAM = "exam-cgl"
PHASE = "phase-tier1"

# SSC CGL Tier 1 dev-canary: 3 AUTHORED sections (the real exam has 4 — GA is
# missing — but OP-0/this service audit authored rows only).
SECTIONS = [
    ("sec-quant", "subj-quant", "Quantitative Aptitude", 0),
    ("sec-reason", "subj-reason", "General Intelligence & Reasoning", 1),
    ("sec-eng", "subj-eng", "English Comprehension", 2),
]


def _sb(**tables) -> SBStub:
    sb = SBStub()
    for name, rows in tables.items():
        sb.db[name] = list(rows)
    return sb


def _mcq(idx: int, subject_id: str, **over) -> dict:
    row = {
        "id": f"q-{idx}",
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


def _cgl_sb(*, bank=None) -> SBStub:
    """SSC CGL Tier 1: 3 authored complete sections + per-section locked coverage.

    ``bank`` lets a test stock the mock_question_bank; default is empty (the
    live canary state: structure present, base MCQ pool ~0).
    """
    return _sb(
        exam_phases=[
            {"id": PHASE, "exam_id": EXAM, "phase_name": "Tier 1",
             "phase_slug": "tier-1", "phase_order": 1, "duration_mins": 60},
        ],
        exam_phase_sections=[
            {
                "id": sid, "exam_phase_id": PHASE, "subject_id": subj,
                "section_label": label, "question_count": 25, "marks": 50,
                "duration_mins": None, "negative_marking": "-0.50",
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


_CANARY_THRESHOLDS = dict(
    selectable_statuses=["published"],
    verified_status="verified",
    min_per_section=30,
    min_locked_coverage=1,
)


# ── thin_bank canary (the expected LIVE outcome today) ────────────────────────

def test_canary_thin_bank_with_per_section_shortfall():
    payload = build_blueprint_payload(
        _cgl_sb(),
        exam_id=EXAM,
        exam_phase_id=PHASE,
        user_id="user-1",
        **_CANARY_THRESHOLDS,
    )
    assert payload["outcome"] == "thin_bank"

    summary = payload["readiness_snapshot"]["summary"]
    # Every authored section is thin (base MCQ pool ~0), none ready/blocked.
    assert summary == {"ready": 0, "thin_bank": 3, "blocked": 0}

    # Verdict is the diagnostic's vocabulary, surfaced verbatim.
    verdict_sections = payload["readiness_snapshot"]["verdict"]["sections"]
    assert {s["verdict"] for s in verdict_sections} == {"thin_bank"}
    assert all(s["reasons"] == ["thin_mcq_pool"] for s in verdict_sections)

    # Per-section shortfall present for every thin section.
    shortfall = payload["section_shortfall"]
    assert len(shortfall) == 3
    assert all(s["shortfall"] == 30 for s in shortfall)  # 30 - 0
    assert {s["section_id"] for s in shortfall} == {sid for sid, *_ in SECTIONS}

    # Envelope present (structure authored) and carries the full realism shape.
    assert payload["structural_envelope"] is not None
    env_sec = payload["section_snapshot"][0]
    assert env_sec["negative_marking"] == "-0.50"
    assert env_sec["weightage_percent"] == 25.0
    assert env_sec["duration_source"] == "phase"  # common-timer phase
    assert env_sec["structure_complete"] is True


def test_canary_flips_to_ready_when_pool_filled_no_code_change():
    # DESIGN INTENT: same code, more data → ready. Stock each subject above
    # min_per_section (30).
    bank = []
    n = 0
    for _sid, subj, _label, _order in SECTIONS:
        for _ in range(35):
            bank.append(_mcq(n, subj))
            n += 1
    payload = build_blueprint_payload(
        _cgl_sb(bank=bank),
        exam_id=EXAM,
        exam_phase_id=PHASE,
        user_id="user-1",
        **_CANARY_THRESHOLDS,
    )
    assert payload["outcome"] == "ready"
    assert payload["readiness_snapshot"]["summary"] == {
        "ready": 3, "thin_bank": 0, "blocked": 0,
    }
    assert payload["section_shortfall"] == []  # no shortfall when ready
    assert payload["structural_envelope"] is not None


# ── blocked / no_sections ─────────────────────────────────────────────────────

def test_blocked_no_sections_envelope_absent():
    sb = _sb(
        exam_phases=[{"id": PHASE, "exam_id": EXAM, "phase_name": "Tier 1",
                      "phase_slug": "tier-1", "phase_order": 1}],
        exam_phase_sections=[],   # phase exists, no authored sections
        mock_question_bank=[],
        exam_topic_coverage=[],
    )
    payload = build_blueprint_payload(
        sb,
        exam_id=EXAM,
        exam_phase_id=PHASE,
        user_id="user-1",
        **_CANARY_THRESHOLDS,
    )
    assert payload["outcome"] == "blocked"
    verdict_sec = payload["readiness_snapshot"]["verdict"]["sections"][0]
    assert verdict_sec["verdict"] == "blocked"
    assert verdict_sec["reasons"] == ["no_sections"]
    # Envelope absent for blocked/no_sections.
    assert payload["structural_envelope"] is None
    assert payload["section_snapshot"] == []
    assert payload["template_snapshot"]["envelope_present"] is False
    assert payload["section_shortfall"] == []


# ── non-mutating for EVERY outcome ────────────────────────────────────────────

@pytest.mark.parametrize(
    "make_sb",
    [
        lambda: _cgl_sb(),                                   # thin_bank
        lambda: _sb(exam_phases=[{"id": PHASE, "exam_id": EXAM}],
                    exam_phase_sections=[], mock_question_bank=[],
                    exam_topic_coverage=[]),                 # blocked
    ],
)
def test_non_mutating_writes_no_blueprint_and_starts_no_attempt(make_sb):
    sb = make_sb()
    payload = build_blueprint_payload(
        sb,
        exam_id=EXAM,
        exam_phase_id=PHASE,
        user_id="user-1",
        **_CANARY_THRESHOLDS,
    )
    assert payload["persisted"] is False
    # No blueprint row, no attempt — for any outcome.
    assert sb.db.get("mock_generated_blueprints", []) == []
    assert sb.db.get("mock_attempts", []) == []
    # user_id is carried but written nowhere.
    assert payload["user_id"] == "user-1"


# ── readiness reflects AUTHORED sections only ─────────────────────────────────

def test_readiness_is_over_authored_sections_only():
    payload = build_blueprint_payload(
        _cgl_sb(),
        exam_id=EXAM,
        exam_phase_id=PHASE,
        user_id="user-1",
        **_CANARY_THRESHOLDS,
    )
    # 3 authored sections — the service must NOT claim official 4-section
    # completeness; the real exam has 4 (GA missing) but that is a human gate.
    assert payload["authored_structure_scope"] is True
    assert payload["template_snapshot"]["authored_section_count"] == 3
    assert len(payload["section_snapshot"]) == 3
    assert "official" in payload["scope_note"].lower()
    # No field self-reports completeness.
    assert "officially_complete" not in payload
    assert "official_completeness" not in payload


# ── thresholds are caller-supplied (no baked-in defaults) ─────────────────────

def test_thresholds_are_required_no_defaults():
    sb = _cgl_sb()
    with pytest.raises(TypeError):
        build_blueprint_payload(
            sb, exam_id=EXAM, exam_phase_id=PHASE, user_id="user-1"
        )  # missing thresholds → no defaults to fall back on


def test_threshold_values_drive_outcome_not_service_body():
    # 5 questions per subject; lenient threshold → ready, strict → thin_bank.
    bank, n = [], 0
    for _sid, subj, _label, _order in SECTIONS:
        for _ in range(5):
            bank.append(_mcq(n, subj))
            n += 1

    lenient = build_blueprint_payload(
        _cgl_sb(bank=bank), exam_id=EXAM, exam_phase_id=PHASE, user_id="u",
        selectable_statuses=["published"], verified_status="verified",
        min_per_section=3, min_locked_coverage=1,
    )
    strict = build_blueprint_payload(
        _cgl_sb(bank=bank), exam_id=EXAM, exam_phase_id=PHASE, user_id="u",
        selectable_statuses=["published"], verified_status="verified",
        min_per_section=10, min_locked_coverage=1,
    )
    assert lenient["outcome"] == "ready"
    assert strict["outcome"] == "thin_bank"


def test_rejects_non_exam_realistic_source():
    with pytest.raises(ValueError):
        build_blueprint_payload(
            _cgl_sb(), exam_id=EXAM, exam_phase_id=PHASE, user_id="u",
            source="personalized", **_CANARY_THRESHOLDS,
        )


# ── hard-validation of readiness inputs (a skipped verdict must not pass as a
#    real 'blocked/no_sections' outcome) ──────────────────────────────────────

@pytest.mark.parametrize(
    "override",
    [
        {"selectable_statuses": []},        # falsy → diagnostic would SKIP verdict
        {"selectable_statuses": None},      # falsy → diagnostic would SKIP verdict
        {"min_per_section": None},          # None → diagnostic would SKIP verdict
        {"min_locked_coverage": None},      # None → diagnostic would SKIP verdict
        {"verified_status": None},          # validated for caller consistency
        {"verified_status": ""},            # validated for caller consistency
    ],
)
def test_readiness_inputs_are_hard_validated(override):
    kwargs = dict(_CANARY_THRESHOLDS)
    kwargs.update(override)
    with pytest.raises(ValueError):
        build_blueprint_payload(
            _cgl_sb(), exam_id=EXAM, exam_phase_id=PHASE, user_id="u", **kwargs
        )


def test_valid_call_still_returns_outcome_after_validation_guard():
    # Regression: the guard must not break the happy path — canary stays thin_bank.
    payload = build_blueprint_payload(
        _cgl_sb(), exam_id=EXAM, exam_phase_id=PHASE, user_id="u",
        **_CANARY_THRESHOLDS,
    )
    assert payload["outcome"] == "thin_bank"
