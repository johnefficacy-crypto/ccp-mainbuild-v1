"""Unit tests for EWP-2 transition validation, completion gate, constraints."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_PKG = Path(__file__).parents[2] / "app/study_os/writing_practice"


def _load(name):
    spec = importlib.util.spec_from_file_location(f"wp2_{name}", _PKG / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


ss = _load("session_state")


# --- completion gate ------------------------------------------------------

def _u(n, status, overall=None, recovery=False):
    return ss.UnitView(unit_number=n, status=status, overall_status=overall, recovery_available=recovery)


def test_all_ready_but_coverage_fails_is_rewrite_required():
    units = [_u(1, ss.UNIT_READY), _u(2, ss.UNIT_READY)]
    assert ss.roll_up_session_status(units, coverage_passed=False) == ss.SESSION_REWRITE_REQUIRED


def test_all_ready_but_unresolved_must_fix_is_rewrite_required():
    units = [_u(1, ss.UNIT_READY), _u(2, ss.UNIT_COMPLETED)]
    assert ss.roll_up_session_status(units, has_unresolved_must_fix=True) == ss.SESSION_REWRITE_REQUIRED


def test_all_ready_gate_passes_is_completed():
    units = [_u(1, ss.UNIT_READY), _u(2, ss.UNIT_COMPLETED)]
    assert ss.roll_up_session_status(units, coverage_passed=True, has_unresolved_must_fix=False) == ss.SESSION_COMPLETED


def test_session_complete_gate():
    assert ss.session_complete_gate(True, False) is True
    assert ss.session_complete_gate(False, False) is False
    assert ss.session_complete_gate(True, True) is False


# --- transition validation ------------------------------------------------

def test_learning_transitions_allowed():
    assert ss.is_allowed_unit_transition("learning", ss.UNIT_DRAFT, ss.UNIT_EVAL_PENDING)
    assert ss.is_allowed_unit_transition("learning", ss.UNIT_EVAL_PENDING, ss.UNIT_REWRITE_REQUIRED)
    assert ss.is_allowed_unit_transition("learning", ss.UNIT_READY, ss.UNIT_DRAFT)      # reopen
    assert ss.is_allowed_unit_transition("learning", ss.UNIT_READY, ss.UNIT_COMPLETED)


def test_exam_forbids_rewrite_required():
    assert not ss.is_allowed_unit_transition("exam", ss.UNIT_EVAL_PENDING, ss.UNIT_REWRITE_REQUIRED)
    assert not ss.is_allowed_unit_transition("exam", ss.UNIT_READY, ss.UNIT_DRAFT)      # no reopen in exam
    assert ss.is_allowed_unit_transition("exam", ss.UNIT_EVAL_PENDING, ss.UNIT_READY)


def test_completed_is_terminal():
    assert not ss.is_allowed_unit_transition("learning", ss.UNIT_COMPLETED, ss.UNIT_DRAFT)
    assert not ss.is_allowed_unit_transition("exam", ss.UNIT_COMPLETED, ss.UNIT_READY)


def test_noop_and_illegal_rejected():
    assert not ss.is_allowed_unit_transition("learning", ss.UNIT_DRAFT, ss.UNIT_DRAFT)
    assert not ss.is_allowed_unit_transition("learning", ss.UNIT_NOT_STARTED, ss.UNIT_READY)


# --- unit_constraints model (needs pydantic; runs in CI) -----------------

def test_constraints_forbid_unknown_keys():
    pytest.importorskip("pydantic")
    from pydantic import ValidationError
    c = _load("constraints")
    with pytest.raises(ValidationError):
        c.validate_unit_constraints({"schema_version": 1, "bogus": 1})


def test_constraints_max_ge_min():
    pytest.importorskip("pydantic")
    from pydantic import ValidationError
    c = _load("constraints")
    with pytest.raises(ValidationError):
        c.validate_unit_constraints({"schema_version": 1, "min_words": 10, "max_words": 5})


def test_constraints_valid_normalises():
    pytest.importorskip("pydantic")
    c = _load("constraints")
    out = c.validate_unit_constraints({"schema_version": 1, "hint_words": ["despite"], "min_words": 5, "max_words": 20})
    assert out["schema_version"] == 1 and out["hint_words"] == ["despite"] and out["max_words"] == 20


def test_constraints_default():
    pytest.importorskip("pydantic")
    c = _load("constraints")
    assert c.validate_unit_constraints(None) == {"schema_version": 1}
