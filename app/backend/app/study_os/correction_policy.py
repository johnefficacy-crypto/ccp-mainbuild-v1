"""Source-neutral mock-correction CATEGORIZATION policy (§7 unification).

Single owner of correction classification shared by BOTH origins:

  * canonical 063 categories (the migration-063 ``mock_correction_tasks_
    category_check`` set),
  * raw-error ALIAS normalization (one place),
  * deterministic category SELECTION + a stable tie-break,
  * emit thresholds (the only per-origin variation is the explicit
    ``evidence_mode``), and
  * the correction TITLES.

Identical normalized :class:`CorrectionPolicyInput` ⇒ identical category, title,
and emit decision, regardless of whether the evidence came from a manually
logged mock (``mocks.py``) or a generated/platform attempt (``mastery_engine`` /
``MasteryWriter``). There is NO branching on "manual" vs "generated" here — the
adapters normalize into this module and read the same answer back.

Categories are derived from ERROR EVIDENCE, never from a correction ``task_type``
(task_type is action style only — duration/execution). Unknown raw evidence
normalizes to ``None`` and is ignored; it never becomes a blind ``concept_gap``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

# Canonical correction categories — the migration-063 mock_correction_tasks
# category CHECK. Owned here; ``mocks`` re-exports it as VALID_CORRECTION_CATEGORIES.
CANONICAL_CATEGORIES: frozenset[str] = frozenset(
    {"concept_gap", "memory_gap", "careless", "speed_issue", "option_trap"}
)

# Per-category title templates (moved here from mocks._CORRECTION_DEFAULTS so both
# paths build identical titles).
TITLES: dict[str, str] = {
    "concept_gap": "Concept drill",
    "memory_gap": "Spaced revision",
    "careless": "Accuracy drill",
    "speed_issue": "Timed retrieval set",
    "option_trap": "Distractor elimination drill",
}

# Raw error-type / key → canonical category. Derived from the LIVE producers, not
# a prompt list:
#   * manual mock ``error_patterns`` keys (mocks._draft_corrections_from_mock):
#       concept, memory, careless, time, option
#   * generated error types (mastery_engine/error_patterns.TRACKED):
#       option_trap, calc_error, concept_gap
#   * the now-retired MasteryWriter alias sets (_MEMORY_LIKE / _SPEED_LIKE).
# Canonical values map to themselves. Anything absent here is UNKNOWN → None.
_ALIASES: dict[str, str] = {
    # concept
    "concept_gap": "concept_gap",
    "concept": "concept_gap",
    # memory
    "memory_gap": "memory_gap",
    "memory": "memory_gap",
    "recall": "memory_gap",
    "fact_recall": "memory_gap",
    "forgetting": "memory_gap",
    # careless / calculation slips
    "careless": "careless",
    "calc_error": "careless",
    "calculation_error": "careless",
    # speed / timing
    "speed_issue": "speed_issue",
    "time": "speed_issue",
    "time_pressure": "speed_issue",
    "slow": "speed_issue",
    "timeout": "speed_issue",
    # option traps
    "option_trap": "option_trap",
    "option": "option_trap",
    "trap": "option_trap",
}

# Stable, documented precedence for equal-weight ties — same evidence always
# resolves to the same winner.
_TIE_BREAK_ORDER: tuple[str, ...] = (
    "concept_gap",
    "option_trap",
    "memory_gap",
    "careless",
    "speed_issue",
)

# Emit thresholds. The ONLY per-origin variation is evidence_mode:
#   * question_level — generated/platform attempt: per-question evidence, so
#     attempted/accuracy are reliable.
#   * summary        — manually logged mock: aggregate error_patterns/weak_topics,
#     no reliable attempted/accuracy.
_MIN_ATTEMPTED = 3
_LOW_ACCURACY_PCT = Decimal("50")
_CONCEPT_TRAP_FLOOR = 2

EvidenceMode = Literal["question_level", "summary"]


def normalize_error_type(raw: str | None) -> str | None:
    """Map a raw error type / error_patterns key to a canonical category, or None
    if it is unknown (ignored — never a blind default)."""
    if raw is None:
        return None
    return _ALIASES.get(str(raw).strip().lower())


def correction_title(category: str, topic: str | None) -> str:
    """Deterministic, non-empty correction title for a category (+ optional topic)."""
    base = TITLES.get(category, "Correction drill")
    return f"{base} · {topic}" if topic else base


@dataclass(frozen=True)
class CorrectionPolicyInput:
    """Normalized correction evidence — the single input both origins build."""

    topic: str | None
    error_counts: dict[str, int] = field(default_factory=dict)  # raw OR canonical → count
    attempted: int = 0
    accuracy_pct: Decimal = Decimal("100")
    weak_topic: bool = False
    prior_error: bool = False
    wrong_pyq: bool = False
    source_question_ids: tuple[str, ...] = ()
    evidence_mode: EvidenceMode = "question_level"


def canonical_counts(error_counts: dict[str, int]) -> dict[str, int]:
    """Collapse raw error counts onto canonical categories; drop unknown/≤0."""
    out: dict[str, int] = {}
    for raw, n in (error_counts or {}).items():
        try:
            c = int(n or 0)
        except (TypeError, ValueError):
            c = 0
        if c <= 0:
            continue
        cat = normalize_error_type(raw)
        if cat is None:
            continue  # unknown evidence is ignored, never defaulted
        out[cat] = out.get(cat, 0) + c
    return out


def select_category(inp: CorrectionPolicyInput) -> str | None:
    """Deterministic category from normalized evidence — mode-independent.

    Highest canonical error count wins; ties break by ``_TIE_BREAK_ORDER``. With
    no usable error evidence, fall back to ``concept_gap`` ONLY on an explicit
    weak-topic / low-accuracy / unrecovered-prior-error signal; otherwise None.
    Unknown raw error types contribute nothing and never force a default.
    """
    counts = canonical_counts(inp.error_counts)
    if counts:
        return min(
            counts,
            key=lambda c: (
                -counts[c],
                _TIE_BREAK_ORDER.index(c) if c in _TIE_BREAK_ORDER else len(_TIE_BREAK_ORDER),
            ),
        )
    if inp.weak_topic or inp.prior_error or inp.accuracy_pct < _LOW_ACCURACY_PCT:
        return "concept_gap"  # explicit, signal-driven fallback (not blind)
    return None


def should_emit(inp: CorrectionPolicyInput) -> bool:
    """Whether this evidence warrants a correction. Thresholds differ only by the
    explicit ``evidence_mode``."""
    counts = canonical_counts(inp.error_counts)
    if inp.evidence_mode == "summary":
        # Manually logged mock: any usable error signal, or a weak-topic fallback.
        return bool(counts) or inp.weak_topic
    # question_level (generated): low-accuracy practice, concept/trap pressure, or
    # an unrecovered prior error.
    concept_trap = counts.get("concept_gap", 0) + counts.get("option_trap", 0)
    recovered = inp.attempted > 0 and inp.accuracy_pct >= _LOW_ACCURACY_PCT
    return (
        (inp.attempted >= _MIN_ATTEMPTED and inp.accuracy_pct < _LOW_ACCURACY_PCT)
        or concept_trap >= _CONCEPT_TRAP_FLOOR
        or (inp.prior_error and not recovered)
    )
