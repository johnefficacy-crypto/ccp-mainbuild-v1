"""Pure session/unit rollup logic for finalize_writing_session (§4.3b, §9.1a).

The database writes (row locks, conditional monotonic UPDATE) wrap these pure
functions; the decision logic lives here so it is unit-testable without a DB.
"""
from __future__ import annotations

from dataclasses import dataclass

# Unit states (§4.4b)
UNIT_NOT_STARTED = "not_started"
UNIT_DRAFT = "draft"
UNIT_EVAL_PENDING = "evaluation_pending"
UNIT_EVAL_FAILED = "evaluation_failed"
UNIT_REWRITE_REQUIRED = "rewrite_required"
UNIT_READY = "ready"
UNIT_COMPLETED = "completed"

# Session states (§4.3a)
SESSION_ACTIVE = "active"
SESSION_EVAL_PENDING = "evaluation_pending"
SESSION_REWRITE_REQUIRED = "rewrite_required"
SESSION_SUBMITTED = "submitted"
SESSION_COMPLETED = "completed"
SESSION_EVAL_INCOMPLETE = "evaluation_incomplete"
SESSION_ABANDONED = "abandoned"

# Evaluation outcomes (§4.3c), ordered worst -> best for monotonic improvement.
OUTCOME_UNSCORED = "unscored"
OUTCOME_DETERMINISTIC_ONLY = "deterministic_only"
OUTCOME_FULLY_EVALUATED = "fully_evaluated"
_OUTCOME_RANK = {None: -1, OUTCOME_UNSCORED: 0, OUTCOME_DETERMINISTIC_ONLY: 1, OUTCOME_FULLY_EVALUATED: 2}

# overall_status -> (is_terminal, per-unit outcome) mapping (§4.6a-1).
_OVERALL_TERMINAL = {"completed", "terminal_partial", "failed"}
_OVERALL_TO_OUTCOME = {
    "completed": OUTCOME_FULLY_EVALUATED,
    "terminal_partial": OUTCOME_DETERMINISTIC_ONLY,
    "failed": OUTCOME_UNSCORED,
}


@dataclass
class UnitView:
    """A unit's rollup-relevant state."""

    unit_number: int
    status: str
    overall_status: str | None = None  # latest evaluation overall_status, if any
    recovery_available: bool = False   # evaluation_failed but ret/gen still possible


def overall_status_is_terminal(overall_status: str | None) -> bool:
    return overall_status in _OVERALL_TERMINAL


def unit_outcome(overall_status: str | None) -> str | None:
    """Per-unit outcome for a terminal evaluation, else None (§4.6a-1)."""
    return _OVERALL_TO_OUTCOME.get(overall_status or "")


def roll_up_session_status(units: list[UnitView]) -> str:
    """Session status by the locked priority order (§4.3b), first match wins."""
    statuses = {u.status for u in units}

    # 1. any unit not_started/draft -> active
    if statuses & {UNIT_NOT_STARTED, UNIT_DRAFT}:
        return SESSION_ACTIVE

    # 2. any evaluation_pending, or evaluation_failed still recoverable -> pending
    if UNIT_EVAL_PENDING in statuses or any(
        u.status == UNIT_EVAL_FAILED and u.recovery_available for u in units
    ):
        return SESSION_EVAL_PENDING

    # 3. evaluation_failed with recovery exhausted -> terminal evaluation_incomplete
    if any(u.status == UNIT_EVAL_FAILED and not u.recovery_available for u in units):
        return SESSION_EVAL_INCOMPLETE

    # 4. any rewrite_required -> rewrite_required
    if UNIT_REWRITE_REQUIRED in statuses:
        return SESSION_REWRITE_REQUIRED

    # 5. all ready/completed -> completed
    if statuses and statuses <= {UNIT_READY, UNIT_COMPLETED}:
        return SESSION_COMPLETED

    # Fallback (empty or unexpected) -> active
    return SESSION_ACTIVE


def aggregate_session_outcome(units: list[UnitView]) -> str | None:
    """Deterministic session-level outcome over required units (§9.1a).

    Returns None while any required unit's latest evaluation is non-terminal.
    """
    if not units:
        return None
    if any(not overall_status_is_terminal(u.overall_status) for u in units):
        return None  # rule 1: not yet computable
    outcomes = [unit_outcome(u.overall_status) for u in units]
    if OUTCOME_UNSCORED in outcomes:
        return OUTCOME_UNSCORED               # rule 2: any deterministic failure
    if OUTCOME_DETERMINISTIC_ONLY in outcomes:
        return OUTCOME_DETERMINISTIC_ONLY     # rule 3: any language-only failure
    return OUTCOME_FULLY_EVALUATED            # rule 4: all fully evaluated


def monotonic_outcome(current: str | None, candidate: str | None) -> str | None:
    """Return the outcome to persist: never downgrade (§9.1a conditional write)."""
    if candidate is None:
        return current
    if _OUTCOME_RANK[candidate] > _OUTCOME_RANK[current]:
        return candidate
    return current
