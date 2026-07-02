"""EWP-5 — writing-task generator + mission-control launch wiring.

Pure unit tests against the in-memory SBStub. No real DB, no network.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from tests.persona_questions._stub import SBStub

pytest.importorskip("app.study_os.writing_practice.planner_writing")

from app.study_os.mission_control import _load_today_tasks  # noqa: E402
from app.study_os.writing_practice import planner_writing as pw  # noqa: E402


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _yesterday_ts() -> str:
    return (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()


def _verified_prompt(**overrides) -> dict:
    base = {
        "id": "prompt-1",
        "exam_id": "exam-1",
        "subject_id": "subj-1",
        "topic_id": "topic-1",
        "microtopic_id": "topic-1",
        "exercise_type": "sentence_correction",
        "difficulty_level": 1,
        "reviewer_status": "verified",
        "is_active": True,
        "required_sentence_count": 1,
    }
    base.update(overrides)
    return base


# ── generator: dormant path ────────────────────────────────────────────────


def test_generator_noop_when_no_verified_prompt():
    # A due retest exists but there is NO verified/active prompt → no-op.
    sb = SBStub({
        "user_topic_mastery": [
            {"user_id": "u-1", "topic_id": "topic-1", "exam_id": "exam-1",
             "next_revision_at": _yesterday_ts()},
        ],
        # unverified prompt must be ignored
        "writing_prompts": [_verified_prompt(reviewer_status="pending", is_active=False)],
    })
    out = pw.generate_writing_tasks(sb, "u-1", exam_id="exam-1")
    assert out["generated"] == 0
    assert out["reason"] == "no_eligible_prompt"
    assert sb.db.get("study_tasks", []) == []
    assert sb.db.get("writing_sessions", []) == []


def test_generator_noop_when_fold_unreadable():
    # No effective-evidence fold table at all → conservative no-op (fail-closed).
    class _NoFold(SBStub):
        def table(self, name):
            if name == "effective_user_topic_mastery_evidence":
                raise RuntimeError("fold view not available")
            return super().table(name)

    sb = _NoFold({"writing_prompts": [_verified_prompt()]})
    out = pw.generate_writing_tasks(sb, "u-1", exam_id="exam-1")
    assert out["generated"] == 0
    assert out["reason"] == "level_unavailable"


# ── generator: active path (mocked verified prompt + due retest) ────────────


def test_generator_creates_one_writing_task_on_due_retest():
    sb = SBStub({
        "effective_user_topic_mastery_evidence": [],  # readable, empty → cold-start level
        "writing_prompts": [_verified_prompt(exercise_type="sentence_construction")],
        "user_topic_mastery": [
            {"user_id": "u-1", "topic_id": "topic-1", "exam_id": "exam-1",
             "next_revision_at": _yesterday_ts()},
        ],
    })
    out = pw.generate_writing_tasks(sb, "u-1", exam_id="exam-1")
    assert out["generated"] == 1

    tasks = sb.db["study_tasks"]
    assert len(tasks) == 1
    task = tasks[0]
    assert task["task_type"] == "writing_revision"
    assert task["launch_type"] == "english_writing_session"
    # launch_entity_id is the created session id.
    session_ids = {s["id"] for s in sb.db["writing_sessions"]}
    assert task["launch_entity_id"] in session_ids
    assert task["launch_context"]["exercise_type"] == "sentence_construction"
    assert task["launch_context"]["trigger"] == "retest_due"
    # No URL stored anywhere.
    assert "action_url" not in task


def test_generator_is_idempotent_same_day():
    sb = SBStub({
        "effective_user_topic_mastery_evidence": [],
        "writing_prompts": [_verified_prompt()],
        "user_topic_mastery": [
            {"user_id": "u-1", "topic_id": "topic-1", "exam_id": "exam-1",
             "next_revision_at": _yesterday_ts()},
        ],
    })
    first = pw.generate_writing_tasks(sb, "u-1", exam_id="exam-1")
    second = pw.generate_writing_tasks(sb, "u-1", exam_id="exam-1")
    assert first["generated"] == 1
    assert second["generated"] == 0
    assert len(sb.db["study_tasks"]) == 1


def test_generator_grammar_error_makes_correction_drill():
    sb = SBStub({
        "effective_user_topic_mastery_evidence": [],
        "writing_prompts": [_verified_prompt(exercise_type="sentence_correction")],
        "user_topic_error_patterns": [
            {"user_id": "u-1", "topic_id": "topic-1", "exam_id": "exam-1", "frequency_count": 3},
        ],
    })
    out = pw.generate_writing_tasks(sb, "u-1", exam_id="exam-1")
    assert out["generated"] == 1
    task = sb.db["study_tasks"][0]
    assert task["task_type"] == "grammar_correction"
    assert task["launch_context"]["exercise_type"] == "sentence_correction"
    assert task["launch_context"]["trigger"] == "grammar_error"


def test_generator_respects_difficulty_ceiling():
    # Cold-start level 1; a difficulty-9 prompt must NOT be eligible.
    sb = SBStub({
        "effective_user_topic_mastery_evidence": [],
        "writing_prompts": [_verified_prompt(difficulty_level=9)],
        "user_topic_mastery": [
            {"user_id": "u-1", "topic_id": "topic-1", "exam_id": "exam-1",
             "next_revision_at": _yesterday_ts()},
        ],
    })
    out = pw.generate_writing_tasks(sb, "u-1", exam_id="exam-1")
    assert out["generated"] == 0
    assert out["reason"] == "no_eligible_prompt"


# ── mission-control launch wiring (§11.1) ───────────────────────────────────


def test_mission_control_serializes_english_launch_action():
    sb = SBStub({
        "study_tasks": [
            {
                "id": "task-eng", "plan_id": "plan-1", "scheduled_date": _today(),
                "status": "planned", "title": "Correction practice",
                "task_type": "grammar_correction",
                "launch_type": "english_writing_session",
                "launch_entity_id": "sess-1",
                "launch_context": {"exercise_type": "sentence_correction"},
            },
        ],
    })
    shaped = _load_today_tasks(sb, "plan-1")
    assert len(shaped) == 1
    t = shaped[0]
    assert t["launch_type"] == "english_writing_session"
    assert t["launch_entity_id"] == "sess-1"
    assert t["action_url"] == "/app/study/practice/english/sess-1"
    assert t["action_label"] == "Start correction practice"


def test_mission_control_leaves_non_english_task_untouched():
    sb = SBStub({
        "study_tasks": [
            {
                "id": "task-std", "plan_id": "plan-1", "scheduled_date": _today(),
                "status": "planned", "title": "Algebra · Concept learning",
                "task_type": "concept_learning",
                "launch_type": None, "launch_entity_id": None, "launch_context": None,
            },
        ],
    })
    shaped = _load_today_tasks(sb, "plan-1")
    assert len(shaped) == 1
    t = shaped[0]
    assert "action_url" not in t
    assert "action_label" not in t
    assert "launch_type" not in t
