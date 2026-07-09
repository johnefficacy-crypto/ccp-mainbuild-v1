"""Unit tests for the server-owned writing-prompt launch resolver.

Covers ``resolve_launch_prompt_id`` / ``available_writing_subject_ids``: a
verified + active + runtime-ready + DEFAULT-DENY-applicable prompt is launchable;
a prompt with no active target (not applicable) or a non-runtime-ready
exercise_type is not. Uses the shared in-memory ``SBStub`` — the
``cms_writing_runtime_ready_types`` RPC is unhandled by the stub, so resolution
falls back to the mirrored ``sentence_construction`` allowlist.
"""
from __future__ import annotations

from app.study_os.writing_practice import subject_launch
from tests.persona_questions._stub import SBStub

_EXAM = "exam-1"


def _seed(*, exercise_type="sentence_construction", with_target=True):
    db = {
        "exams": [{"id": _EXAM, "exam_family_id": None}],
        "writing_prompts": [
            {"id": "wp-1", "subject_id": "s1", "topic_id": None,
             "exercise_type": exercise_type, "reviewer_status": "verified",
             "is_active": True},
        ],
        "writing_prompt_targets": [],
    }
    if with_target:
        db["writing_prompt_targets"].append(
            {"prompt_id": "wp-1", "is_global": True, "exam_family_id": None,
             "exam_id": None, "exam_phase_id": None, "applicability_status": "active"}
        )
    return db


def test_resolve_returns_applicable_runtime_ready_prompt():
    sb = SBStub(_seed())
    pid = subject_launch.resolve_launch_prompt_id(
        sb, subject_id="s1", topic_id=None, exam_id=_EXAM, exam_phase_id=None
    )
    assert pid == "wp-1"
    assert subject_launch.available_writing_subject_ids(
        sb, ["s1"], exam_id=_EXAM
    ) == {"s1"}


def test_resolve_none_when_not_applicable():
    # No active target -> DEFAULT-DENY -> not launchable.
    sb = SBStub(_seed(with_target=False))
    assert subject_launch.resolve_launch_prompt_id(
        sb, subject_id="s1", topic_id=None, exam_id=_EXAM, exam_phase_id=None
    ) is None
    assert subject_launch.available_writing_subject_ids(
        sb, ["s1"], exam_id=_EXAM
    ) == set()


def test_resolve_none_when_exercise_type_not_runtime_ready():
    # Verified + active + applicable, but essay is not in the runtime-ready allowlist.
    sb = SBStub(_seed(exercise_type="essay"))
    assert subject_launch.resolve_launch_prompt_id(
        sb, subject_id="s1", topic_id=None, exam_id=_EXAM, exam_phase_id=None
    ) is None
    assert subject_launch.available_writing_subject_ids(
        sb, ["s1"], exam_id=_EXAM
    ) == set()


def test_resolve_none_without_subject():
    sb = SBStub(_seed())
    assert subject_launch.resolve_launch_prompt_id(
        sb, subject_id=None, topic_id=None, exam_id=_EXAM, exam_phase_id=None
    ) is None
