"""Launch-target -> action URL/label tests (§11.1)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_PATH = Path(__file__).parents[2] / "app/study_os/writing_practice/launch.py"


def _load():
    spec = importlib.util.spec_from_file_location("wp_launch", _PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


L = _load()


def test_english_session_action_url_and_label():
    out = L.compute_action(
        "english_writing_session",
        "session-abc",
        {"exercise_type": "sentence_construction"},
    )
    assert out == {
        "action_url": "/app/study/practice/english/session-abc",
        "action_label": "Start sentence practice",
    }


def test_unknown_exercise_falls_back_to_default_label():
    out = L.compute_action("english_writing_session", "s1", {"exercise_type": "mystery"})
    assert out["action_label"] == "Start writing practice"
    assert out["action_url"] == "/app/study/practice/english/s1"


def test_non_english_launch_type_returns_none():
    assert L.compute_action("mock_attempt", "m1", {}) is None
    assert L.compute_action(None, "s1", {}) is None


def test_missing_entity_id_still_resolves_with_null_url():
    # Planner-shaped writing task: no pre-existing session, so entity id is
    # null. The action must still resolve (so the Study Home CTA renders) with
    # a null action_url — the click creates the session server-side.
    out = L.compute_action(
        "english_writing_session", None, {"exercise_type": "sentence_construction"}
    )
    assert out == {
        "action_url": None,
        "action_label": "Start sentence practice",
    }


def test_missing_entity_id_falls_back_to_default_label():
    out = L.compute_action("english_writing_session", None, {})
    assert out == {"action_url": None, "action_label": "Start writing practice"}


def test_context_none_is_safe():
    out = L.compute_action("english_writing_session", "s1", None)
    assert out["action_label"] == "Start writing practice"
