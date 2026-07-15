"""Unit tests for the server-owned SubjectRuntimePolicy registry (GQR-1).

Pins the runtime authority GQR-1 introduces: family resolution from canonical
governed metadata, inventory/planner resolvers as the live authority (not dead
config), byte-stable English/PYQ output, and the General-Awareness fences (no PYQ
mode, no PYQ planner stamp). Also pins registry/handler parity.
"""
from __future__ import annotations

from app.study_os import subject_runtime_policy as srp


# ── Family resolution ──────────────────────────────────────────────────────
def test_family_resolves_from_governed_group_first():
    assert srp.family_for_subject(subject_group="numerical") == "quant"
    assert srp.family_for_subject(subject_group="verbal") == "english"
    assert srp.family_for_subject(subject_group="reasoning") == "reasoning"
    assert srp.family_for_subject(subject_group="general-awareness") == "general_awareness"


def test_family_falls_back_to_slug_then_none():
    assert srp.family_for_subject(slug="quantitative-aptitude") == "quant"
    assert srp.family_for_subject(slug="english-language") == "english"
    assert srp.family_for_subject(slug="general-intelligence-reasoning") == "reasoning"
    # UPSC General Studies is ungoverned for this registry → generic, never GA.
    assert srp.family_for_subject(subject_group="gs", slug="upsc-polity") is None
    assert srp.family_for_subject() is None


def test_initial_policies_match_contract_families():
    assert set(srp.SUBJECT_RUNTIME_POLICIES) == {
        "english", "quant", "reasoning", "general_awareness",
    }
    assert srp.SUBJECT_RUNTIME_POLICIES["quant"].supported_modes == (
        "topic_practice", "timed_practice", "heuristic_drill", "calculation_gym",
    )


def test_general_awareness_policy_fences():
    ga = srp.SUBJECT_RUNTIME_POLICIES["general_awareness"]
    assert ga.mastery_enabled is False
    assert ga.correction_enabled is False
    assert ga.retry_policy == "ephemeral_ca"
    # GQR-G5: weekly current-affairs is the only wired GA runtime — no PYQ leak, no
    # topic-driven mode; monthly stays declared-but-unwired.
    assert ga.wired_runtime_modes == ("weekly_current_affairs",)


# ── Inventory resolver is the authority (finding 1) ────────────────────────
def _ctx(*, eng=False, topics=()):
    return srp.InventoryContext(eng_available=eng, available_topic_ids=tuple(topics))


def test_english_family_emits_writing_and_pyq():
    modes = srp.resolve_subject_modes(
        slug="english-language", subject_group="verbal",
        ctx=_ctx(eng=True, topics=["t-1"]),
    )
    types = [m["type"] for m in modes]
    assert types == ["english_writing", "error_lab", "topic_pyq", "mock_section"]
    assert next(m for m in modes if m["type"] == "topic_pyq")["target_topic_id"] == "t-1"


def test_reasoning_family_emits_topic_and_timed_practice():
    # GQR-R10: reasoning surfaces topic PYQ + timed practice, both server_launch, both
    # targeting the weakest projected topic. Added via policy wiring, no subjects.py branch.
    modes = srp.resolve_subject_modes(
        slug="general-intelligence-reasoning", subject_group="reasoning",
        ctx=_ctx(topics=["t-7"]),
    )
    server_modes = [m for m in modes if m["route_type"] == "server_launch"]
    assert [m["type"] for m in server_modes] == ["topic_pyq", "timed_practice"]
    assert all(m["target_topic_id"] == "t-7" for m in server_modes)
    assert srp.is_wired_mode("timed_practice") is True


def test_reasoning_timed_practice_hidden_without_projected_topics():
    assert srp.resolve_subject_modes(
        slug="general-intelligence-reasoning", subject_group="reasoning", ctx=_ctx(),
    ) == []


def test_quant_family_emits_pyq_and_calculation_gym():
    modes = srp.resolve_subject_modes(
        slug="quantitative-aptitude", subject_group="numerical",
        ctx=_ctx(eng=True, topics=["t-9"]),  # eng signal present but Quant policy omits writing
    )
    assert [m["type"] for m in modes] == ["topic_pyq", "mock_section", "calculation_gym"]


def test_quant_calculation_gym_does_not_require_projected_topics():
    modes = srp.resolve_subject_modes(
        slug="quantitative-aptitude", subject_group="numerical", ctx=_ctx(),
    )
    assert [m["type"] for m in modes] == ["calculation_gym"]
    assert modes[0]["target_topic_id"] is None


def test_general_awareness_subject_gets_no_pyq_mode_even_with_topics():
    # Proves the policy gates the runtime — GA is fenced off from the generic PYQ path
    # although topics are projected. No English/PYQ branch in subjects.py could do this.
    # GQR-G5: GA surfaces the bundle-driven weekly current-affairs launch, and ONLY that
    # — never a topic_pyq/english_writing mode, even with eng + topics present.
    modes = srp.resolve_subject_modes(
        slug="general-awareness", subject_group="general-awareness",
        ctx=_ctx(eng=True, topics=["t-1", "t-2"]),
    )
    assert [m["type"] for m in modes] == ["weekly_current_affairs"]
    ca = modes[0]
    assert ca["route_type"] == "server_launch"
    assert ca["launch_mode"] == "weekly_current_affairs"
    assert ca["target_topic_id"] is None  # bundle-driven, never a projected topic
    assert srp.is_wired_mode("weekly_current_affairs") is True


def test_unknown_subject_falls_back_to_generic_pyq():
    modes = srp.resolve_subject_modes(
        slug="upsc-polity", subject_group="gs", ctx=_ctx(topics=["t-3"]),
    )
    assert [m["type"] for m in modes] == ["topic_pyq", "mock_section"]


def test_weakest_topic_selection_is_preserved():
    # lowest mastery wins; error-flag then stable str tiebreak.
    ctx = srp.InventoryContext(
        available_topic_ids=("t-b", "t-a", "t-c"),
        mastery={"t-b": 80.0, "t-a": 80.0, "t-c": 20.0},
        error_topics=frozenset({"t-a"}),
    )
    modes = srp.resolve_subject_modes(slug="quantitative-aptitude", subject_group="numerical", ctx=ctx)
    assert next(m for m in modes if m["type"] == "topic_pyq")["target_topic_id"] == "t-c"


# ── Planner resolver delegates by family (finding 2) ───────────────────────
def test_planner_stamps_pyq_for_pyq_subjects():
    for group, slug in [("numerical", "quantitative-aptitude"),
                        ("verbal", "english-language"),
                        ("reasoning", "general-intelligence-reasoning"),
                        (None, "upsc-polity")]:  # ungoverned → generic still PYQ
        out = srp.resolve_planner_launch(
            "retrieval_practice", subject_slug=slug, subject_group=group,
            topic_id="t-1", exam_id="e-1",
        )
        assert out == {
            "launch_type": "pyq_practice",
            "launch_entity_id": "t-1",
            "launch_context": {"mode": "topic", "target_id": "t-1", "exam_id": "e-1"},
        }, (group, slug)


def test_planner_never_stamps_pyq_for_general_awareness():
    out = srp.resolve_planner_launch(
        "retrieval_practice", subject_slug="general-awareness",
        subject_group="general-awareness", topic_id="t-1", exam_id="e-1",
    )
    assert out is None
    # revision too
    assert srp.resolve_planner_launch(
        "revision", subject_group="general-awareness", topic_id="t-1", exam_id="e-1",
    ) is None


def test_planner_none_for_other_task_types_or_missing_ctx():
    assert srp.resolve_planner_launch("concept_learning", subject_group="numerical",
                                     topic_id="t-1", exam_id="e-1") is None
    assert srp.resolve_planner_launch("retrieval_practice", subject_group="numerical",
                                     topic_id=None, exam_id="e-1") is None
    # No subject identity at all → generic PYQ resolver, byte-stable with prior default.
    assert srp.resolve_planner_launch("revision", topic_id="t-1", exam_id="e-1") is not None


# ── Wiring integrity (finding 3) ───────────────────────────────────────────
def test_wired_modes_and_launch_handlers_are_in_parity():
    from app.api.subject_practice import _LAUNCH_HANDLERS

    assert set(srp.WIRED_RUNTIME_MODES) == set(_LAUNCH_HANDLERS)


def test_hub_mode_descriptor_is_byte_stable():
    assert srp.WIRED_RUNTIME_MODES["english_writing"].hub_mode() == {
        "type": "english_writing", "label": "Sentence practice",
        "target_topic_id": None, "route_type": "server_launch",
        "launch_mode": "english_writing",
    }
