"""A-PR3 — persist a generated blueprint + atomically start an attempt.

First MUTATING Track A service. These cover the hardening invariants the PR is
"born with":

  * ready path: blueprint row 'started', attempt with template_id NULL +
    generated_blueprint_id + owner = user, N frozen responses, correct return.
  * ATOMICITY: a forced response-freeze failure rolls back EVERYTHING.
  * ready-gate: thin_bank / blocked → 409, zero writes.
  * XOR + owner: the inserted attempt satisfies migration 175's one-source +
    owner-consistency invariants.
  * idempotency: starting the same blueprint twice yields one attempt.
  * server-side thresholds: client-supplied threshold fields are ignored.
  * loader reuse: get_attempt loads the generated attempt unchanged (source-
    agnostic), and a save/submit round-trip scores correctly.

Stub-only (the shared in-memory SBStub emulates the migration-178 RPC as one
atomic transaction); NO live DB writes.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import generated_mock as generated_mock_api
from app.core.auth import get_current_user
from app.study_os import generated_mock_attempt as svc
from app.study_os import mock_engine as engine
from tests.persona_questions._stub import SBStub

EXAM = "exam-cgl"
PHASE = "phase-tier1"
USER = "user-aspirant-1"

# SSC CGL Tier 1 shape: 4 sections × 25 = 100 questions.
SECTIONS = [
    ("sec-quant", "subj-quant", "Quantitative Aptitude", 0),
    ("sec-reason", "subj-reason", "General Intelligence & Reasoning", 1),
    ("sec-eng", "subj-eng", "English Comprehension", 2),
    ("sec-ga", "subj-ga", "General Awareness", 3),
]
QUESTION_COUNT = 25


def _options(qid: str) -> tuple[list[dict], str]:
    opts = [
        {
            "id": f"opt-{qid}-{i}",
            "question_id": qid,
            "option_text": f"Option {i}",
            "option_index": i,
            "is_correct": i == 2,
        }
        for i in range(1, 5)
    ]
    return opts, opts[1]["id"]  # correct = option_index 2


def _question(idx: int, subject_id: str, **over) -> tuple[dict, list[dict]]:
    qid = f"q-{idx:04d}"
    opts, correct = _options(qid)
    row = {
        "id": qid,
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
        "question_text": f"Question {qid}",
        "correct_option_id": correct,
        "explanation": "Because.",
    }
    row.update(over)
    return row, opts


def _stocked_bank(per_subject: int) -> tuple[list[dict], list[dict]]:
    bank, options, n = [], [], 0
    for _sid, subj, _label, _order in SECTIONS:
        for _ in range(per_subject):
            q, opts = _question(n, subj)
            bank.append(q)
            options.extend(opts)
            n += 1
    return bank, options


def _sb(*, per_subject: int = 35, question_count: int = QUESTION_COUNT,
        sections=SECTIONS, bank_options=None) -> SBStub:
    if bank_options is None:
        bank, options = _stocked_bank(per_subject)
    else:
        bank, options = bank_options
    sb = SBStub()
    sb.db.update(
        {
            "exam_phases": [
                {"id": PHASE, "exam_id": EXAM, "phase_name": "Tier 1",
                 "phase_slug": "tier-1", "phase_order": 1, "duration_mins": 60},
            ],
            "exam_phase_sections": [
                {
                    "id": sid, "exam_phase_id": PHASE, "subject_id": subj,
                    "section_label": label, "question_count": question_count,
                    "marks": 50, "duration_mins": None, "negative_marking": "-0.50",
                    "difficulty_level": "medium", "weightage_percent": 25.0,
                    "sort_order": order,
                }
                for sid, subj, label, order in sections
            ],
            "mock_question_bank": bank,
            "mock_question_options": options,
            "exam_topic_coverage": [
                {"id": f"cov-{sid}", "exam_id": EXAM, "exam_phase_id": PHASE,
                 "section_id": sid, "reviewer_status": "locked"}
                for sid, _subj, _label, _order in sections
            ],
            "mock_generated_blueprints": [],
            "mock_attempts": [],
            "mock_attempt_responses": [],
            "mock_tests": [],
        }
    )
    return sb


def _client(sb: SBStub, user_id: str = USER) -> TestClient:
    app = FastAPI()
    app.include_router(generated_mock_api.router, prefix="/api")
    app.dependency_overrides[get_current_user] = lambda: {"id": user_id}
    generated_mock_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    return TestClient(app)


# ── ready path ───────────────────────────────────────────────────────────────

def test_ready_persists_blueprint_attempt_and_frozen_responses():
    sb = _sb()
    result = svc.persist_and_start(
        sb, user_id=USER, exam_id=EXAM, exam_phase_id=PHASE, source="exam_realistic"
    )

    assert result["outcome"] == "ready"
    assert result["question_count"] == 100
    assert result["attempt_id"]
    assert result["blueprint_id"]

    # Blueprint row inserted and flipped to 'started'.
    bps = sb.db["mock_generated_blueprints"]
    assert len(bps) == 1
    bp = bps[0]
    assert bp["id"] == result["blueprint_id"]
    assert bp["status"] == "started"
    assert bp["user_id"] == USER
    assert len(bp["question_ids"]) == 100
    assert bp["expires_at"]  # NOT NULL, set by the service

    # Attempt row inserted: template_id NULL, generated_blueprint_id set, owner.
    attempts = sb.db["mock_attempts"]
    assert len(attempts) == 1
    att = attempts[0]
    assert att["id"] == result["attempt_id"]
    assert att["template_id"] is None
    assert att["generated_blueprint_id"] == result["blueprint_id"]
    assert att["user_id"] == USER
    assert att["status"] == "in_progress"

    # 100 frozen responses with a non-empty question_snapshot.
    responses = [r for r in sb.db["mock_attempt_responses"] if r["attempt_id"] == att["id"]]
    assert len(responses) == 100
    for r in responses:
        snap = r["question_snapshot"]
        assert snap.get("id")
        assert snap.get("question_text")
        assert snap.get("correct_option_id")
        assert snap.get("options")


def test_ready_via_api_returns_contract():
    sb = _sb()
    client = _client(sb)
    r = client.post(
        "/api/study-os/mocks/generated/start",
        json={"exam_id": EXAM, "exam_phase_id": PHASE, "source": "exam_realistic"},
    )
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"blueprint_id", "attempt_id", "question_count", "outcome"}
    assert body["outcome"] == "ready"
    assert body["question_count"] == 100


# ── atomicity ────────────────────────────────────────────────────────────────

def test_atomicity_response_freeze_failure_rolls_back_everything():
    sb = _sb()
    sb._force_response_freeze_failure = True  # the freeze step raises in the RPC

    with pytest.raises(RuntimeError):
        svc.persist_and_start(
            sb, user_id=USER, exam_id=EXAM, exam_phase_id=PHASE, source="exam_realistic"
        )

    # FULL rollback: no orphan blueprint / attempt / response of any kind.
    assert sb.db["mock_generated_blueprints"] == []
    assert sb.db["mock_attempts"] == []
    assert sb.db["mock_attempt_responses"] == []


# ── ready-gate ───────────────────────────────────────────────────────────────

def test_thin_bank_gate_starts_nothing():
    sb = _sb(per_subject=5)  # below min_per_section(30) → thin_bank
    result = svc.persist_and_start(
        sb, user_id=USER, exam_id=EXAM, exam_phase_id=PHASE
    )
    assert result["outcome"] == "thin_bank"
    assert result.get("readiness") is not None
    assert sb.db["mock_generated_blueprints"] == []
    assert sb.db["mock_attempts"] == []
    assert sb.db["mock_attempt_responses"] == []


def test_blocked_gate_returns_409_via_api_with_zero_writes():
    sb = _sb()
    sb.db["exam_phase_sections"] = []  # no authored sections → blocked
    client = _client(sb)
    r = client.post(
        "/api/study-os/mocks/generated/start",
        json={"exam_id": EXAM, "exam_phase_id": PHASE},
    )
    assert r.status_code == 409
    assert r.json()["detail"]["outcome"] == "blocked"
    assert sb.db["mock_generated_blueprints"] == []
    assert sb.db["mock_attempts"] == []


# ── XOR + owner invariants (migration 175) ───────────────────────────────────

def test_inserted_attempt_satisfies_xor_and_owner_consistency():
    sb = _sb()
    result = svc.persist_and_start(
        sb, user_id=USER, exam_id=EXAM, exam_phase_id=PHASE
    )
    att = sb.db["mock_attempts"][0]
    bp = sb.db["mock_generated_blueprints"][0]

    # XOR: exactly one source.
    has_template = att["template_id"] is not None
    has_blueprint = att["generated_blueprint_id"] is not None
    assert has_template != has_blueprint
    assert has_blueprint

    # Owner-consistency composite FK: attempt.user_id == blueprint.user_id.
    assert att["user_id"] == bp["user_id"] == USER
    assert att["generated_blueprint_id"] == bp["id"]


# ── idempotency ──────────────────────────────────────────────────────────────

def test_starting_same_blueprint_twice_yields_one_attempt():
    """The RPC is idempotent on (user, blueprint): a reused blueprint id with an
    in_progress attempt returns the existing attempt, never a second one."""
    sb = _sb()
    fixed_bp = str(uuid.uuid4())
    rpc_params = {
        "p_user": USER,
        "p_exam": EXAM,
        "p_exam_phase": PHASE,
        "p_blueprint": {"id": fixed_bp, "source": "exam_realistic", "question_ids": ["q-0000"]},
        "p_template_snapshot": {"question_ids": ["q-0000"]},
        "p_response_rows": [{"question_id": "q-0000", "question_snapshot": {"id": "q-0000"}}],
        "p_expires_at": "2099-01-01T00:00:00+00:00",
    }
    first = sb.rpc("start_attempt_from_blueprint", rpc_params).execute().data[0]
    second = sb.rpc("start_attempt_from_blueprint", rpc_params).execute().data[0]

    assert first["attempt_id"] == second["attempt_id"]
    assert first["blueprint_id"] == second["blueprint_id"] == fixed_bp
    # One blueprint, one attempt, one frozen response — not doubled.
    assert len(sb.db["mock_generated_blueprints"]) == 1
    assert len(sb.db["mock_attempts"]) == 1
    assert len([r for r in sb.db["mock_attempt_responses"]
                if r["attempt_id"] == first["attempt_id"]]) == 1


# ── server-side thresholds ───────────────────────────────────────────────────

def test_client_threshold_fields_in_body_are_ignored():
    # 10 per subject is BELOW the server min_per_section(30) → must stay thin_bank
    # even though the client tries to lower the bar to 1.
    sb = _sb(per_subject=10)
    client = _client(sb)
    r = client.post(
        "/api/study-os/mocks/generated/start",
        json={
            "exam_id": EXAM,
            "exam_phase_id": PHASE,
            "min_per_section": 1,
            "min_locked_coverage": 0,
            "selectable_statuses": ["draft", "published"],
        },
    )
    assert r.status_code == 409
    assert r.json()["detail"]["outcome"] == "thin_bank"
    assert sb.db["mock_attempts"] == []


def test_service_uses_fixed_server_side_thresholds(monkeypatch):
    captured = {}

    real = svc.build_blueprint_with_selection

    def _spy(sb, **kwargs):
        captured.update(kwargs)
        return real(sb, **kwargs)

    monkeypatch.setattr(svc, "build_blueprint_with_selection", _spy)
    sb = _sb()
    svc.persist_and_start(sb, user_id=USER, exam_id=EXAM, exam_phase_id=PHASE)

    assert captured["selectable_statuses"] == ["published"]
    assert captured["verified_status"] == "verified"
    assert captured["min_per_section"] == 30
    assert captured["min_locked_coverage"] == 1


# ── loader reuse (source-agnostic mock_engine load + scoring) ────────────────

def test_get_attempt_loads_generated_attempt_unchanged():
    sb = _sb()
    result = svc.persist_and_start(sb, user_id=USER, exam_id=EXAM, exam_phase_id=PHASE)
    attempt_id = result["attempt_id"]

    state = engine.get_attempt(sb, USER, attempt_id)
    assert len(state["questions"]) == 100
    # Questions hydrate from the frozen template_snapshot/question_snapshot, with
    # no template_id involved — proving the read path is source-agnostic.
    for q in state["questions"]:
        assert q["question_text"]
        assert q["options"]


def test_save_submit_round_trip_scores_correctly():
    sb = _sb()
    result = svc.persist_and_start(sb, user_id=USER, exam_id=EXAM, exam_phase_id=PHASE)
    attempt_id = result["attempt_id"]

    state = engine.get_attempt(sb, USER, attempt_id)
    # Answer the first three questions with their (frozen) correct option.
    answered = state["questions"][:3]
    for i, q in enumerate(answered):
        snap = next(
            r["question_snapshot"]
            for r in sb.db["mock_attempt_responses"]
            if r["attempt_id"] == attempt_id and r["question_id"] == q["question_id"]
        )
        engine.save_answer(
            sb, USER, attempt_id, q["question_id"], snap["correct_option_id"],
            is_marked_for_review=False, client_seq=i + 1, time_spent_sec=5,
        )

    out = engine.submit_attempt(sb, USER, attempt_id)
    assert out["status"] == "submitted"
    assert out["total_correct"] == 3
    assert out["total_wrong"] == 0
    assert out["total_unattempted"] == 97
