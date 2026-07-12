"""Unit tests for the server-owned SubjectRuntimePolicy registry (GQR-1).

Pins the runtime contract GQR-1 introduces without shipping new subject behaviour:
the wired v1 adapters reproduce the prior hub descriptors byte-for-byte, the launch
endpoint dispatches only wired modes, and planner launch stamping resolves through
the registry with unchanged output for existing task types.
"""
from __future__ import annotations

from app.study_os import subject_runtime_policy as srp


def test_initial_policies_match_contract_families():
    fams = set(srp.SUBJECT_RUNTIME_POLICIES)
    assert fams == {"english", "quant", "reasoning", "general_awareness"}
    # Contract §2.2 ordered supported_modes per family.
    assert srp.SUBJECT_RUNTIME_POLICIES["quant"].supported_modes == (
        "topic_practice", "timed_practice", "heuristic_drill", "calculation_gym",
    )
    assert srp.SUBJECT_RUNTIME_POLICIES["general_awareness"].supported_modes == (
        "weekly_current_affairs", "monthly_current_affairs",
    )


def test_general_awareness_never_writes_mastery_or_correction():
    ga = srp.SUBJECT_RUNTIME_POLICIES["general_awareness"]
    assert ga.mastery_enabled is False
    assert ga.correction_enabled is False
    assert ga.retry_policy == "ephemeral_ca"


def test_only_english_and_topic_pyq_are_wired_in_v1():
    assert set(srp.WIRED_RUNTIME_MODES) == {"english_writing", "topic_pyq"}
    assert srp.is_wired_mode("english_writing") is True
    assert srp.is_wired_mode("topic_pyq") is True
    assert srp.is_wired_mode("calculation_gym") is False
    assert srp.is_wired_mode("nonsense") is False


def test_hub_mode_descriptor_is_byte_stable():
    # The exact descriptor subjects.py must emit (regression: browser contract).
    eng = srp.WIRED_RUNTIME_MODES["english_writing"].hub_mode()
    assert eng == {
        "type": "english_writing", "label": "Sentence practice",
        "target_topic_id": None, "route_type": "server_launch",
        "launch_mode": "english_writing",
    }
    pyq = srp.WIRED_RUNTIME_MODES["topic_pyq"].hub_mode(target_topic_id="t-1")
    assert pyq == {
        "type": "topic_pyq", "label": "Topic PYQ practice",
        "target_topic_id": "t-1", "route_type": "server_launch",
        "launch_mode": "topic_pyq",
    }


def test_resolve_planner_launch_preserves_pyq_stamp():
    out = srp.resolve_planner_launch("retrieval_practice", topic_id="t-1", exam_id="e-1")
    assert out == {
        "launch_type": "pyq_practice",
        "launch_entity_id": "t-1",
        "launch_context": {"mode": "topic", "target_id": "t-1", "exam_id": "e-1"},
    }
    assert srp.resolve_planner_launch("revision", topic_id="t-1", exam_id="e-1") is not None


def test_resolve_planner_launch_none_for_other_task_types_or_missing_ctx():
    assert srp.resolve_planner_launch("concept_learning", topic_id="t-1", exam_id="e-1") is None
    assert srp.resolve_planner_launch("retrieval_practice", topic_id=None, exam_id="e-1") is None
    assert srp.resolve_planner_launch("retrieval_practice", topic_id="t-1", exam_id=None) is None
