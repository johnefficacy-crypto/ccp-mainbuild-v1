"""GQR-S7 hardening for set/stimulus-aware Reasoning strategy delivery."""
from __future__ import annotations

from uuid import UUID

import pytest

from app.study_os import reasoning_strategies as rs
from app.study_os import solution_strategies as ss
from tests.persona_questions._stub import SBStub


def _subject(family: str = "reasoning") -> dict:
    return {
        "slug": "reasoning" if family == "reasoning" else "quantitative-aptitude",
        "subject_group": "reasoning" if family == "reasoning" else "numerical",
    }


def _strategy(
    strategy_id: str,
    *,
    status: str = "verified",
    active: bool = True,
    topic_id: str | None = "rt1",
    microtopic_id: str | None = None,
    family: str = "reasoning",
) -> dict:
    return {
        "id": strategy_id,
        "name": strategy_id,
        "strategy_type": "set_method",
        "formula_latex": None,
        "standard_method": "Build one shared working grid.",
        "faster_method": None,
        "key_observation": "Resolve fixed clues first.",
        "worked_example": None,
        "common_traps": "Rebuilding the set for every question.",
        "topic_id": topic_id,
        "microtopic_id": microtopic_id,
        "topic": {"subject": _subject(family)} if topic_id else None,
        "microtopic": (
            {"parent_topic_id": topic_id, "subject": _subject(family)}
            if microtopic_id
            else None
        ),
        "reviewer_status": status,
        "is_active": active,
    }


def _link(
    stimulus_id: str,
    strategy_id: str,
    *,
    status: str = "verified",
    relevance: str = "primary",
) -> dict:
    return {
        "id": f"{stimulus_id}:{strategy_id}",
        "stimulus_id": stimulus_id,
        "strategy_id": strategy_id,
        "reviewer_status": status,
        "relevance": relevance,
    }


def test_malformed_or_empty_set_scope_fails_closed_without_shortening():
    sb = SBStub(
        {
            "reasoning_stimulus_strategies": [
                _link("stim-valid", "s1"),
                _link("stim-empty", "s1"),
                _link("stim-malformed", "s1"),
            ],
            "reasoning_strategies": [_strategy("s1")],
        }
    )

    out = rs.strategies_for_stimuli(
        sb,
        {
            "stim-valid": [{"topic_id": "rt1", "microtopic_id": "rm1"}],
            "stim-empty": [],
            # The legacy implementation silently dropped the malformed element and
            # admitted the strategy using only the first scope. S7 must evaluate the
            # complete frozen set, so one malformed member makes the group ineligible.
            "stim-malformed": [
                {"topic_id": "rt1", "microtopic_id": "rm1"},
                "not-a-scope",
            ],
        },
    )

    assert [row["id"] for row in out["stim-valid"]] == ["s1"]
    assert out["stim-empty"] == []
    assert out["stim-malformed"] == []


def test_stimulus_gate_is_conjunctive_and_matches_every_question():
    sb = SBStub(
        {
            "reasoning_stimulus_strategies": [
                _link("stim-1", "ok"),
                _link("stim-1", "pending-link", status="pending"),
                _link("stim-1", "pending-strategy"),
                _link("stim-1", "inactive"),
                _link("stim-1", "micro-only"),
                _link("stim-1", "cross-subject"),
            ],
            "reasoning_strategies": [
                _strategy("ok"),
                _strategy("pending-link"),
                _strategy("pending-strategy", status="pending"),
                _strategy("inactive", active=False),
                _strategy("micro-only", microtopic_id="rm1"),
                _strategy("cross-subject", family="quant"),
            ],
        }
    )

    out = rs.strategies_for_stimuli(
        sb,
        {
            "stim-1": [
                {"topic_id": "rt1", "microtopic_id": "rm1"},
                {"topic_id": "rt1", "microtopic_id": "rm2"},
            ]
        },
    )

    assert [row["id"] for row in out["stim-1"]] == ["ok"]
    assert "reviewer_status" not in out["stim-1"][0]
    assert "topic_id" not in out["stim-1"][0]


def test_stimulus_reader_is_fail_soft_by_default_and_strict_when_requested():
    class BrokenSupabase:
        def table(self, _name):
            raise RuntimeError("database unavailable")

    scopes = {"stim-1": [{"topic_id": "rt1", "microtopic_id": None}]}
    assert rs.strategies_for_stimuli(BrokenSupabase(), scopes) == {"stim-1": []}
    with pytest.raises(RuntimeError, match="database unavailable"):
        rs.strategies_for_stimuli(BrokenSupabase(), scopes, strict=True)


def test_shared_projection_normalizes_uuid_stimulus_ids():
    stimulus_id = UUID("93417197-9b21-5e01-9460-fb5abdac2aa4")
    sb = SBStub(
        {
            "reasoning_stimulus_strategies": [_link(str(stimulus_id), "s1")],
            "reasoning_strategies": [_strategy("s1")],
        }
    )

    out = ss.strategies_for_stimuli(
        sb,
        {stimulus_id: [{"topic_id": "rt1", "microtopic_id": None}]},
    )

    assert list(out) == [str(stimulus_id)]
    assert out[str(stimulus_id)][0]["subject_family"] == "reasoning"
    assert set(out[str(stimulus_id)][0]) == set(ss.ALLOWED_FIELDS)
