"""Unit tests for the EWP-2 deterministic engine, content hash, and session rollup.

Pure functions, no DB — run in CI unconditionally.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_PKG = Path(__file__).parents[2] / "app/study_os/writing_practice"


def _load(name):
    spec = importlib.util.spec_from_file_location(f"wp_{name}", _PKG / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


det = _load("deterministic")
ch = _load("content_hash")
ss = _load("session_state")


# --- content hash ---------------------------------------------------------

def test_empty_content_hash_constant():
    assert ch.compute_content_hash("") == ch.EMPTY_CONTENT_HASH
    assert ch.EMPTY_CONTENT_HASH == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_content_hash_is_lowercase_hex_64():
    h = ch.compute_content_hash("The scheme is useful.")
    assert len(h) == 64 and h == h.lower()
    int(h, 16)


# --- word / sentence counting --------------------------------------------

def test_word_count_hyphen_and_apostrophe_single_word():
    assert det.word_count("state-of-the-art") == 1
    assert det.word_count("don't stop") == 2


def test_word_count_ignores_punctuation_and_whitespace():
    assert det.word_count("  Hello,   world!  ") == 2
    assert det.word_count("") == 0


def test_sentence_count():
    assert det.sentence_count("One. Two! Three?") == 3
    assert det.sentence_count("No terminator here") == 1
    assert det.sentence_count("   ") == 0


# --- required-word presence ----------------------------------------------

def test_required_word_case_insensitive_whole_token():
    assert det.required_word_present("Despite the rain, we left.", "despite")
    # substring must not match
    assert not det.required_word_present("description", "descript")


def test_required_word_coverage_session_level():
    covered, per = det.required_word_coverage(
        ["despite", "however"],
        ["Despite the delay.", "We stayed; however, we left."],
    )
    assert covered is True
    assert per == {"despite": True, "however": True}
    covered2, per2 = det.required_word_coverage(["despite", "moreover"], ["Despite it."])
    assert covered2 is False and per2["moreover"] is False


# --- unit evaluation ------------------------------------------------------

def test_evaluate_unit_empty_flags_violation():
    r = det.evaluate_unit("")
    assert r.is_empty and "empty_answer" in r.violations and not r.passed


def test_evaluate_unit_min_max_words():
    r = det.evaluate_unit("one two three", min_words=5)
    assert not r.min_words_ok and "below_min_words" in r.violations
    r2 = det.evaluate_unit("one two three four five six", max_words=5)
    assert not r2.max_words_ok and "above_max_words" in r2.violations


def test_evaluate_unit_required_word_missing():
    r = det.evaluate_unit("A plain sentence.", required_words=["despite"])
    assert not r.required_words_all_present and "missing_required_word" in r.violations


def test_evaluate_unit_duplicate_across_units():
    r = det.evaluate_unit("The scheme is useful.", other_unit_texts={1: "The scheme is useful."})
    assert r.duplicate_of_units == [1] and "duplicate_sentence" in r.violations


def test_evaluate_unit_clean_passes():
    r = det.evaluate_unit("Despite the rain, we left early.", min_words=3, max_words=20,
                          required_words=["despite"])
    assert r.passed and r.server_word_count == 6 and r.required_words_all_present


def test_deterministic_result_serialises():
    r = det.evaluate_unit("Hello world.")
    d = r.to_dict()
    assert d["server_word_count"] == 2 and d["evaluator_version"] == det.DETERMINISTIC_EVALUATOR_VERSION


# --- session rollup -------------------------------------------------------

def _u(n, status, overall=None, recovery=False):
    return ss.UnitView(unit_number=n, status=status, overall_status=overall, recovery_available=recovery)


def test_rollup_active_when_draft_present():
    assert ss.roll_up_session_status([_u(1, ss.UNIT_DRAFT), _u(2, ss.UNIT_READY)]) == ss.SESSION_ACTIVE


def test_rollup_pending_when_eval_pending():
    assert ss.roll_up_session_status([_u(1, ss.UNIT_EVAL_PENDING), _u(2, ss.UNIT_READY)]) == ss.SESSION_EVAL_PENDING


def test_rollup_pending_when_failed_but_recoverable():
    assert ss.roll_up_session_status([_u(1, ss.UNIT_EVAL_FAILED, recovery=True)]) == ss.SESSION_EVAL_PENDING


def test_rollup_incomplete_when_recovery_exhausted():
    assert ss.roll_up_session_status([_u(1, ss.UNIT_EVAL_FAILED, recovery=False), _u(2, ss.UNIT_READY)]) == ss.SESSION_EVAL_INCOMPLETE


def test_rollup_rewrite_required():
    assert ss.roll_up_session_status([_u(1, ss.UNIT_REWRITE_REQUIRED), _u(2, ss.UNIT_READY)]) == ss.SESSION_REWRITE_REQUIRED


def test_rollup_completed_all_ready():
    assert ss.roll_up_session_status([_u(1, ss.UNIT_READY), _u(2, ss.UNIT_COMPLETED)]) == ss.SESSION_COMPLETED


def test_rollup_priority_draft_beats_pending():
    # draft (rule 1) wins over evaluation_pending (rule 2)
    assert ss.roll_up_session_status([_u(1, ss.UNIT_DRAFT), _u(2, ss.UNIT_EVAL_PENDING)]) == ss.SESSION_ACTIVE


# --- session outcome aggregation -----------------------------------------

def test_outcome_none_while_nonterminal():
    assert ss.aggregate_session_outcome([_u(1, ss.UNIT_READY, overall="partial")]) is None


def test_outcome_unscored_on_any_failure():
    units = [_u(1, ss.UNIT_READY, overall="completed"), _u(2, ss.UNIT_EVAL_FAILED, overall="failed")]
    assert ss.aggregate_session_outcome(units) == ss.OUTCOME_UNSCORED


def test_outcome_deterministic_only():
    units = [_u(1, ss.UNIT_READY, overall="completed"), _u(2, ss.UNIT_READY, overall="terminal_partial")]
    assert ss.aggregate_session_outcome(units) == ss.OUTCOME_DETERMINISTIC_ONLY


def test_outcome_fully_evaluated():
    units = [_u(1, ss.UNIT_READY, overall="completed"), _u(2, ss.UNIT_COMPLETED, overall="completed")]
    assert ss.aggregate_session_outcome(units) == ss.OUTCOME_FULLY_EVALUATED


def test_monotonic_outcome_never_downgrades():
    assert ss.monotonic_outcome(ss.OUTCOME_DETERMINISTIC_ONLY, ss.OUTCOME_UNSCORED) == ss.OUTCOME_DETERMINISTIC_ONLY
    assert ss.monotonic_outcome(ss.OUTCOME_DETERMINISTIC_ONLY, ss.OUTCOME_FULLY_EVALUATED) == ss.OUTCOME_FULLY_EVALUATED
    assert ss.monotonic_outcome(None, ss.OUTCOME_UNSCORED) == ss.OUTCOME_UNSCORED
    assert ss.monotonic_outcome(ss.OUTCOME_FULLY_EVALUATED, None) == ss.OUTCOME_FULLY_EVALUATED
