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
from app.api import mock_engine as mock_engine_api
from app.core.auth import get_current_user
from app.study_os import generated_mock_attempt as svc
from app.study_os import mock_engine as engine
from app.study_os.mocks import VALID_CORRECTION_CATEGORIES
from app.study_os.planner import compute_draft_plan
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
        "/api/study/mocks/generated/start",
        json={"exam_id": EXAM, "exam_phase_id": PHASE, "source": "exam_realistic"},
    )
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {
        "blueprint_id", "attempt_id", "question_count", "outcome",
        "expires_at", "selector_snapshot",
    }
    assert body["outcome"] == "ready"
    assert body["question_count"] == 100
    assert body["expires_at"]
    # selector_snapshot carries the honest per-section eligible/selected breakdown.
    assert body["selector_snapshot"]["sections"]
    assert all(
        s["selected_count"] == QUESTION_COUNT
        for s in body["selector_snapshot"]["sections"]
    )


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


# ── fail-closed freeze: selected == frozen, no silent shrink ─────────────────

def test_freeze_fails_closed_when_a_selected_question_does_not_load(monkeypatch):
    # Data drift / race: a selected bank row vanishes before freeze. The attempt
    # must NOT silently persist with fewer questions — it fails closed, zero writes.
    sb = _sb()
    real_load = svc._load_questions

    def _drop_one(sb_, ids):
        loaded = real_load(sb_, ids)
        if ids:
            loaded.pop(ids[0], None)  # one selected id no longer resolves
        return loaded

    monkeypatch.setattr(svc, "_load_questions", _drop_one)
    with pytest.raises(RuntimeError):
        svc.persist_and_start(sb, user_id=USER, exam_id=EXAM, exam_phase_id=PHASE)

    assert sb.db["mock_generated_blueprints"] == []
    assert sb.db["mock_attempts"] == []
    assert sb.db["mock_attempt_responses"] == []


def test_freeze_fails_closed_on_unscoreable_mcq_snapshot(monkeypatch):
    # A selected row that loads but has no options / correct_option_id cannot be
    # scored — fail closed before the RPC rather than freeze an unscoreable item.
    sb = _sb()
    real_load = svc._load_questions

    def _corrupt(sb_, ids):
        loaded = real_load(sb_, ids)
        if ids:
            q = dict(loaded[ids[0]])
            q["options"] = []
            q["correct_option_id"] = None
            loaded[ids[0]] = q
        return loaded

    monkeypatch.setattr(svc, "_load_questions", _corrupt)
    with pytest.raises(RuntimeError):
        svc.persist_and_start(sb, user_id=USER, exam_id=EXAM, exam_phase_id=PHASE)

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
        "/api/study/mocks/generated/start",
        json={"exam_id": EXAM, "exam_phase_id": PHASE},
    )
    assert r.status_code == 409
    assert r.json()["detail"]["outcome"] == "blocked"
    assert sb.db["mock_generated_blueprints"] == []
    assert sb.db["mock_attempts"] == []


# ── XOR + owner invariants (migration 175) ───────────────────────────────────

def test_inserted_attempt_satisfies_xor_and_owner_consistency():
    sb = _sb()
    svc.persist_and_start(
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
        "/api/study/mocks/generated/start",
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


# ── signal-producer: submit goes through the EXISTING engine route ───────────
#
# A generated attempt is just a mock_attempts row with template_id NULL, so
# submit/answer/result/review reuse the engine endpoints unchanged. On submit the
# engine route runs MasteryWriter inline (api/mock_engine.submit), source-
# agnostic — these prove the generated attempt feeds Study OS mastery/correction
# signals through that one path, with no second/divergent writer.


def _engine_client(sb: SBStub, user_id: str = USER) -> TestClient:
    app = FastAPI()
    app.include_router(mock_engine_api.router, prefix="/api")
    app.dependency_overrides[get_current_user] = lambda: {"id": user_id}
    mock_engine_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    return TestClient(app)


def _start_generated(sb: SBStub) -> str:
    res = svc.persist_and_start(sb, user_id=USER, exam_id=EXAM, exam_phase_id=PHASE)
    assert res["outcome"] == "ready"
    return res["attempt_id"]


def _answer_all(sb: SBStub, attempt_id: str, *, correct: bool) -> None:
    rows = [r for r in sb.db["mock_attempt_responses"] if r["attempt_id"] == attempt_id]
    for r in rows:
        snap = r["question_snapshot"]
        cid = snap["correct_option_id"]
        chosen = cid if correct else next(o["id"] for o in snap["options"] if o["id"] != cid)
        engine.save_answer(
            sb, USER, attempt_id, r["question_id"], chosen,
            is_marked_for_review=False, client_seq=1, time_spent_sec=5,
        )


def test_submit_runs_masterywriter_for_template_id_null_attempt_shadow(monkeypatch):
    # The engine submit route still runs MasteryWriter INLINE on the first pass;
    # the durable mastery_retry row is only the completion/recovery marker. This
    # proves it fires for a template_id-null (generated) attempt — source-agnostic.
    monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "shadow")
    sb = _sb()
    attempt_id = _start_generated(sb)
    assert sb.db["mock_attempts"][0]["template_id"] is None  # generated attempt
    _answer_all(sb, attempt_id, correct=True)

    r = _engine_client(sb).post(f"/api/study/mocks/attempts/{attempt_id}/submit")
    assert r.status_code == 200

    # shadow rows written (writer ran), each maps to a frozen-snapshot topic …
    shadow = sb.db.get("mock_mastery_shadow", [])
    assert shadow
    assert all(s["flag_state"] == "shadow" for s in shadow)
    assert all(s["topic_id"] == "topic-1" for s in shadow)
    # … and NO live mutation in shadow mode.
    assert sb.db.get("user_topic_mastery", []) == []
    assert sb.db.get("user_topic_mastery_audit", []) == []
    assert sb.db.get("user_topic_error_patterns", []) == []
    assert sb.db.get("mock_correction_tasks", []) == []


def test_ff_live_applies_mastery_exactly_once_no_dual_writer(monkeypatch):
    monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "live")
    sb = _sb()
    attempt_id = _start_generated(sb)
    _answer_all(sb, attempt_id, correct=True)
    client = _engine_client(sb)

    r1 = client.post(f"/api/study/mocks/attempts/{attempt_id}/submit")
    assert r1.status_code == 200

    # live mastery applied EXACTLY ONCE for the practised topic.
    audit = [a for a in sb.db.get("user_topic_mastery_audit", []) if a["topic_id"] == "topic-1"]
    assert len(audit) == 1
    assert any(m["topic_id"] == "topic-1" for m in sb.db.get("user_topic_mastery", []))

    # DUAL-WRITER GUARD: the legacy mastery.py recompute path (driven off
    # mock_topic_breakdowns) is NOT engaged by a generated submit — the engine
    # emits a mock_tests compat row but no breakdowns, so no second/divergent
    # recompute runs alongside MasteryWriter.
    assert sb.db.get("mock_topic_breakdowns", []) == []

    # re-submit is idempotent: NO double-apply (the apply RPC guards on the audit).
    r2 = client.post(f"/api/study/mocks/attempts/{attempt_id}/submit")
    assert r2.status_code == 200
    audit2 = [a for a in sb.db.get("user_topic_mastery_audit", []) if a["topic_id"] == "topic-1"]
    assert len(audit2) == 1


def test_ff_live_correction_drafts_are_063_schema_compatible(monkeypatch):
    # A generated submit drafts corrections into the EXISTING mock_correction_tasks
    # schema (migration 063): a valid `category`, a `mock_test_id` (the compat row
    # emitted on submit), a non-empty `title` — and NONE of the old mastery-engine
    # columns. The submit emits the mock_tests row, so corrections land inline.
    monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "live")
    sb = _sb()
    attempt_id = _start_generated(sb)
    _answer_all(sb, attempt_id, correct=False)  # 0% accuracy → error/correction signals

    r = _engine_client(sb).post(f"/api/study/mocks/attempts/{attempt_id}/submit")
    assert r.status_code == 200

    # the live write-back path ran (mastery applied for the practised topic) …
    assert any(a["topic_id"] == "topic-1" for a in sb.db.get("user_topic_mastery_audit", []))
    drafts = sb.db.get("mock_correction_tasks", [])
    assert drafts  # 0% accuracy must produce at least one correction
    for d in drafts:
        assert d["category"] in VALID_CORRECTION_CATEGORIES
        assert d["mock_test_id"]
        assert d["title"]
        assert d["state"] == "drafted"
        # the old mastery-engine-shaped columns must NOT be present.
        for bad in ("task_type", "priority", "evidence_json", "duration_minutes", "source_attempt_id"):
            assert bad not in d


def test_planner_regen_reflects_live_mastery_for_affected_topic(monkeypatch):
    # After a live mastery/error update, a planner regeneration re-prioritises the
    # affected topic (planner reads user_topic_mastery + user_topic_error_patterns).
    from tests.study_os.test_runtime_e2e import _seed as _planner_seed

    sb = SBStub(_planner_seed())

    def _t1(plan):
        return next((t for t in plan["after_tasks"] if t["topic_id"] == "t1"), None)

    base = _t1(compute_draft_plan(sb, "u-1"))
    assert base is not None  # baseline: t1 has no mastery row yet (gap default)

    # Simulate the live write-back: low mastery + an error pattern for t1.
    sb.db.setdefault("user_topic_mastery", []).append(
        {"id": "m-t1", "user_id": "u-1", "topic_id": "t1", "mastery_score": 15.0}
    )
    sb.db.setdefault("user_topic_error_patterns", []).append(
        {"id": "e-t1", "user_id": "u-1", "topic_id": "t1", "error_type": "concept_gap", "error_count": 3}
    )

    after = _t1(compute_draft_plan(sb, "u-1"))
    assert after is not None
    # Worse mastery + a logged error raises the topic's priority on regen.
    assert after["priority_score"] > base["priority_score"]


def test_shadow_writer_repeated_reruns_keep_one_decision(monkeypatch):
    monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "shadow")
    sb = _sb()
    attempt_id = _start_generated(sb)
    _answer_all(sb, attempt_id, correct=True)
    engine.submit_attempt(sb, USER, attempt_id)

    import asyncio
    from app.study_os.mastery_writer import MasteryWriter

    async def _run_many() -> None:
        writer = MasteryWriter(sb, "shadow")
        await writer.process_attempt(attempt_id)
        await MasteryWriter(sb, "shadow").process_attempt(attempt_id)
        await MasteryWriter(sb, "shadow").process_attempt(attempt_id)

    asyncio.run(_run_many())

    shadow = [r for r in sb.db.get("mock_mastery_shadow", []) if r["attempt_id"] == attempt_id]
    keys = [(r["attempt_id"], r["topic_id"], r["flag_state"]) for r in shadow]
    assert keys == [(attempt_id, "topic-1", "shadow")]


def test_submit_fresh_runs_mastery_once_and_clean_replay_skips_writer(monkeypatch):
    monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "shadow")
    sb = _sb()
    attempt_id = _start_generated(sb)
    _answer_all(sb, attempt_id, correct=True)
    client = _engine_client(sb)

    calls: list[str] = []
    real_process = mock_engine_api.MasteryWriter.process_attempt

    async def _counting_process(self, attempt_id_arg):
        calls.append(attempt_id_arg)
        return await real_process(self, attempt_id_arg)

    monkeypatch.setattr(mock_engine_api.MasteryWriter, "process_attempt", _counting_process)

    r1 = client.post(f"/api/study/mocks/attempts/{attempt_id}/submit")
    before_shadow = list(sb.db.get("mock_mastery_shadow", []))
    r2 = client.post(f"/api/study/mocks/attempts/{attempt_id}/submit")

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json() == r2.json()
    assert calls == [attempt_id]
    assert sb.db.get("mock_mastery_shadow", []) == before_shadow
    retry_jobs = [j for j in sb.db.get("mock_attempt_jobs", []) if j.get("job_kind") == engine.JOB_MASTERY_RETRY]
    assert len(retry_jobs) == 1
    assert retry_jobs[0]["status"] == "done"
    assert retry_jobs[0]["mastery_flag_state"] == "shadow"


def test_replay_while_retry_pending_does_not_execute_writer_inline(monkeypatch):
    monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "shadow")
    sb = _sb()
    attempt_id = _start_generated(sb)
    _answer_all(sb, attempt_id, correct=True)
    client = _engine_client(sb)

    calls = 0
    real_sync = mock_engine_api.MasteryWriter.process_attempt_sync

    def _fail_once(self, attempt_id_arg):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("forced partial writer failure")
        return real_sync(self, attempt_id_arg)

    monkeypatch.setattr(mock_engine_api.MasteryWriter, "process_attempt_sync", _fail_once)

    r1 = client.post(f"/api/study/mocks/attempts/{attempt_id}/submit")
    assert r1.status_code == 200
    assert sb.db.get("mock_mastery_shadow", []) == []
    retry_jobs = [j for j in sb.db.get("mock_attempt_jobs", []) if j.get("job_kind") == engine.JOB_MASTERY_RETRY]
    assert len(retry_jobs) == 1
    assert retry_jobs[0]["mastery_flag_state"] == "shadow"
    assert retry_jobs[0]["status"] == "pending"

    r2 = client.post(f"/api/study/mocks/attempts/{attempt_id}/submit")
    assert r2.status_code == 200
    assert sb.db.get("mock_mastery_shadow", []) == []
    assert calls == 1
    assert len([j for j in sb.db.get("mock_attempt_jobs", []) if j.get("job_kind") == engine.JOB_MASTERY_RETRY]) == 1

    engine.run_sweeper(sb)
    shadow = [r for r in sb.db.get("mock_mastery_shadow", []) if r["attempt_id"] == attempt_id]
    assert len(shadow) == 1
    assert calls == 2

def test_mastery_retry_job_recovers_writer_failure_without_http_replay(monkeypatch):
    monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "shadow")
    sb = _sb()
    attempt_id = _start_generated(sb)
    _answer_all(sb, attempt_id, correct=True)
    client = _engine_client(sb)

    calls = 0
    real_sync = mock_engine_api.MasteryWriter.process_attempt_sync

    def _fail_once(self, attempt_id_arg):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("forced writer outage")
        return real_sync(self, attempt_id_arg)

    monkeypatch.setattr(mock_engine_api.MasteryWriter, "process_attempt_sync", _fail_once)

    r = client.post(f"/api/study/mocks/attempts/{attempt_id}/submit")
    assert r.status_code == 200
    assert sb.db.get("mock_mastery_shadow", []) == []
    retry_jobs = [j for j in sb.db.get("mock_attempt_jobs", []) if j.get("job_kind") == engine.JOB_MASTERY_RETRY]
    assert len(retry_jobs) == 1
    assert retry_jobs[0]["status"] == "pending"
    assert retry_jobs[0]["mastery_flag_state"] == "shadow"
    assert retry_jobs[0]["last_error"]

    counts = engine.run_sweeper(sb)

    assert counts["errors"] == 0
    shadow = [r for r in sb.db.get("mock_mastery_shadow", []) if r["attempt_id"] == attempt_id]
    assert len(shadow) == 1
    assert shadow[0]["topic_id"] == "topic-1"
    assert retry_jobs[0]["status"] == "done"
    assert retry_jobs[0]["last_error"] is None
    assert calls == 2

    engine.run_sweeper(sb)
    assert len([r for r in sb.db.get("mock_mastery_shadow", []) if r["attempt_id"] == attempt_id]) == 1
    assert calls == 2


def test_shadow_retry_remains_shadow_after_env_changes_to_live(monkeypatch):
    monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "shadow")
    sb = _sb()
    attempt_id = _start_generated(sb)
    _answer_all(sb, attempt_id, correct=True)
    client = _engine_client(sb)

    calls = 0
    real_sync = mock_engine_api.MasteryWriter.process_attempt_sync

    def _fail_once(self, attempt_id_arg):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("forced writer outage")
        return real_sync(self, attempt_id_arg)

    monkeypatch.setattr(mock_engine_api.MasteryWriter, "process_attempt_sync", _fail_once)

    assert client.post(f"/api/study/mocks/attempts/{attempt_id}/submit").status_code == 200
    monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "live")
    engine.run_sweeper(sb)

    shadow = [r for r in sb.db.get("mock_mastery_shadow", []) if r["attempt_id"] == attempt_id]
    assert len(shadow) == 1
    assert shadow[0]["flag_state"] == "shadow"
    assert sb.db.get("user_topic_mastery_audit", []) == []


def test_shadow_done_does_not_count_as_live_done(monkeypatch):
    monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "shadow")
    sb = _sb()
    attempt_id = _start_generated(sb)
    _answer_all(sb, attempt_id, correct=True)
    client = _engine_client(sb)

    assert client.post(f"/api/study/mocks/attempts/{attempt_id}/submit").status_code == 200
    assert [j for j in sb.db.get("mock_attempt_jobs", []) if j.get("mastery_flag_state") == "shadow" and j.get("status") == "done"]

    monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "live")
    assert client.post(f"/api/study/mocks/attempts/{attempt_id}/submit").status_code == 200

    assert [j for j in sb.db.get("mock_attempt_jobs", []) if j.get("mastery_flag_state") == "live" and j.get("status") == "done"]
    flags = {r["flag_state"] for r in sb.db.get("mock_mastery_shadow", []) if r["attempt_id"] == attempt_id}
    assert {"shadow", "live"}.issubset(flags)
    assert sb.db.get("user_topic_mastery_audit", [])


def test_mastery_retry_enqueue_failure_is_observable(monkeypatch):
    monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "shadow")
    sb = _sb()
    attempt_id = _start_generated(sb)
    _answer_all(sb, attempt_id, correct=True)
    client = _engine_client(sb)

    async def _fail_writer(self, attempt_id_arg):
        raise RuntimeError("writer failed")

    original_table = sb.table

    def _table_with_retry_insert_failure(name):
        query = original_table(name)
        if name == "mock_attempt_jobs":
            def _fail_insert(payload):
                raise RuntimeError("retry insert failed")

            query.insert = _fail_insert  # type: ignore[method-assign]
        return query

    monkeypatch.setattr(mock_engine_api.MasteryWriter, "process_attempt", _fail_writer)
    monkeypatch.setattr(sb, "table", _table_with_retry_insert_failure)

    r = client.post(f"/api/study/mocks/attempts/{attempt_id}/submit")

    assert r.status_code == 503
    assert r.json()["detail"]["error"] == "mastery_retry_enqueue_failed"
    assert sb.db.get("mock_mastery_shadow", []) == []
    assert sb.db.get("mock_attempt_jobs", []) == []

def test_ff_off_submit_creates_no_shadow_and_no_mastery_writer(monkeypatch):
    monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "off")
    sb = _sb()
    attempt_id = _start_generated(sb)
    _answer_all(sb, attempt_id, correct=True)
    client = _engine_client(sb)

    async def _unexpected_process(self, attempt_id_arg):  # pragma: no cover - should not run
        raise AssertionError("mastery writer should not run when FF is off")

    monkeypatch.setattr(mock_engine_api.MasteryWriter, "process_attempt", _unexpected_process)

    r = client.post(f"/api/study/mocks/attempts/{attempt_id}/submit")
    assert r.status_code == 200
    assert sb.db.get("mock_mastery_shadow", []) == []
    assert not any(j.get("job_kind") == engine.JOB_MASTERY_RETRY for j in sb.db.get("mock_attempt_jobs", []))
