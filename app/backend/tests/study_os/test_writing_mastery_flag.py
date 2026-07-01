"""FF_WRITING_MASTERY_WRITES resolution tests (fail-closed + Lane A gate)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_PATH = Path(__file__).parents[2] / "app/study_os/writing_practice/mastery_flag.py"


def _load():
    spec = importlib.util.spec_from_file_location("wp_mastery_flag", _PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


mf = _load()
USER = "11111111-1111-4111-8111-111111111111"


@pytest.mark.parametrize("raw,expected", [
    (None, "off"), ("", "off"), ("off", "off"), ("shadow", "shadow"),
    ("live", "live"), ("LIVE", "live"), ("garbage", "off"), (" shadow ", "shadow"),
])
def test_get_flag_fails_closed(monkeypatch, raw, expected):
    if raw is None:
        monkeypatch.delenv("FF_WRITING_MASTERY_WRITES", raising=False)
    else:
        monkeypatch.setenv("FF_WRITING_MASTERY_WRITES", raw)
    assert mf.get_writing_mastery_write_flag() == expected


def test_off_and_shadow_passthrough():
    assert mf.resolve_effective_writing_mastery_flag("off", USER) == "off"
    assert mf.resolve_effective_writing_mastery_flag("shadow", USER) == "shadow"


def test_live_blocked_by_lane_a_gate(monkeypatch):
    # Lane A gate is closed by default -> live downgrades to shadow regardless of allowlist.
    monkeypatch.setenv("FF_WRITING_MASTERY_LIVE_USER_IDS", USER)
    assert mf.LANE_A_LIVE_UNBLOCKED is False
    assert mf.resolve_effective_writing_mastery_flag("live", USER) == "shadow"


def test_live_allowlist_when_gate_open(monkeypatch):
    monkeypatch.setattr(mf, "LANE_A_LIVE_UNBLOCKED", True)
    monkeypatch.setenv("FF_WRITING_MASTERY_LIVE_USER_IDS", USER)
    assert mf.resolve_effective_writing_mastery_flag("live", USER) == "live"
    # user not in allowlist -> shadow
    assert mf.resolve_effective_writing_mastery_flag("live", "22222222-2222-4222-8222-222222222222") == "shadow"
    # empty allowlist -> shadow
    monkeypatch.setenv("FF_WRITING_MASTERY_LIVE_USER_IDS", "")
    assert mf.resolve_effective_writing_mastery_flag("live", USER) == "shadow"
