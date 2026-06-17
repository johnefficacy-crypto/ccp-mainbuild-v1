"""Source-neutral mock-correction CATEGORIZATION policy (§7 unification).

Single owner of correction classification shared by BOTH origins:

  * canonical 063 categories (the migration-063 ``mock_correction_tasks_
    category_check`` set),
  * raw-error ALIAS normalization (one place, grounded in the live producers),
  * deterministic, ordered category SELECTION over AGGREGATED evidence,
  * a single source-neutral emission rule, and
  * the category-only correction TITLES.

Both adapters build a :class:`CorrectionPolicyInput` and call
:func:`select_categories`, which returns the canonical correction SET (ordered,
each category at most once) — so identical normalized evidence yields the same
ordered category set, the same titles, and the same emit decision regardless of
origin. There is NO branching on "manual" vs "generated"; ``evidence_mode`` is
descriptive metadata only and never changes emission for the same positive
evidence.

Categories come from ERROR EVIDENCE, never from a correction ``task_type``.
Unknown raw evidence normalizes to ``None`` and is ignored — never a blind
``concept_gap``.
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

# Category-only title templates. Topic is NOT appended (it lives in the separate
# ``topic`` column); both origins persist these exact strings so titles are
# origin-independent (no "· Polity" vs "· <uuid>" drift).
TITLES: dict[str, str] = {
    "concept_gap": "Concept drill",
    "memory_gap": "Spaced revision",
    "careless": "Accuracy drill",
    "speed_issue": "Timed retrieval set",
    "option_trap": "Distractor elimination drill",
}

# Raw error-type / key → canonical category. GROUNDED in the live producers:
#   * generated question error_type (attempt_analytics/classifier.py RULES):
#       concept_gap, knowledge_gap, option_trap, calc_error, silly_mistake,
#       time_pressure_unattempted  (marked_unanswered / "correct" → not an error)
#   * mastery.py _VALID_ERROR_TYPES (migration-033 check):
#       concept_gap, memory_gap, careless, speed_issue, misread_question,
#       option_trap, formula_confusion, time_management
#   * manual mock error_patterns keys (frontend Mocks.jsx / mocks.py):
#       concept, calc, time, misread, guess, memory, careless, option
# Canonical values map to themselves. Anything absent here is UNKNOWN → None
# (ignored — never defaulted). "guess"/"marked_unanswered"/"correct"/"unknown"
# are deliberately left UNKNOWN (no clean category).
_ALIASES: dict[str, str] = {
    # concept (incl. knowledge/formula deficiencies)
    "concept_gap": "concept_gap",
    "concept": "concept_gap",
    "knowledge_gap": "concept_gap",
    "formula_confusion": "concept_gap",
    # memory / recall
    "memory_gap": "memory_gap",
    "memory": "memory_gap",
    "recall": "memory_gap",
    "fact_recall": "memory_gap",
    "forgetting": "memory_gap",
    # careless / calculation slips / misreads
    "careless": "careless",
    "calc": "careless",
    "calc_error": "careless",
    "calculation_error": "careless",
    "silly": "careless",
    "silly_mistake": "careless",
    "misread": "careless",
    "misread_question": "careless",
    # speed / timing
    "speed_issue": "speed_issue",
    "time": "speed_issue",
    "time_pressure": "speed_issue",
    "time_pressure_unattempted": "speed_issue",
    "time_management": "speed_issue",
    "slow": "speed_issue",
    "timeout": "speed_issue",
    # option traps
    "option_trap": "option_trap",
    "option": "option_trap",
    "trap": "option_trap",
}

# Stable, documented precedence for equal-weight ties — same evidence always
# resolves to the same order.
_TIE_BREAK_ORDER: tuple[str, ...] = (
    "concept_gap",
    "option_trap",
    "memory_gap",
    "careless",
    "speed_issue",
)

_MIN_ATTEMPTED = 3
_LOW_ACCURACY_PCT = Decimal("50")

EvidenceMode = Literal["question_level", "summary"]


def normalize_error_type(raw: str | None) -> str | None:
    """Map a raw error type / error_patterns key to a canonical category, or None
    if unknown (ignored — never a blind default)."""
    if raw is None:
        return None
    return _ALIASES.get(str(raw).strip().lower())


def correction_title(category: str) -> str:
    """Category-only, origin-independent correction title."""
    return TITLES.get(category, "Correction drill")


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
    evidence_mode: EvidenceMode = "question_level"  # descriptive only


def canonical_counts(error_counts: dict[str, int]) -> dict[str, int]:
    """Aggregate raw error counts onto canonical categories; drop unknown/≤0.

    Alias collisions (e.g. ``concept`` + ``concept_gap``) collapse into ONE
    canonical count. Independent of dict insertion order.
    """
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


def _explicit_fallback(inp: CorrectionPolicyInput) -> bool:
    """Signal-driven concept_gap fallback when there is NO recognized error
    evidence: weak topic, low-accuracy practice, or an unrecovered prior error."""
    recovered = inp.attempted > 0 and inp.accuracy_pct >= _LOW_ACCURACY_PCT
    return (
        inp.weak_topic
        or (inp.attempted >= _MIN_ATTEMPTED and inp.accuracy_pct < _LOW_ACCURACY_PCT)
        or (inp.prior_error and not recovered)
    )


def select_categories(inp: CorrectionPolicyInput) -> list[str]:
    """The canonical correction SET for this evidence — ordered, each at most once.

    Source-neutral. Recognized canonical error counts (aliases aggregated) are
    emitted highest-count-first, ties broken by ``_TIE_BREAK_ORDER``. With no
    recognized error evidence, returns ``["concept_gap"]`` ONLY on an explicit
    fallback signal; otherwise ``[]``. Deterministic — never depends on dict
    insertion order, never branches on caller identity.
    """
    counts = canonical_counts(inp.error_counts)
    if counts:
        return sorted(
            counts,
            key=lambda c: (-counts[c], _TIE_BREAK_ORDER.index(c)),
        )
    if _explicit_fallback(inp):
        return ["concept_gap"]
    return []


def should_emit(inp: CorrectionPolicyInput) -> bool:
    """Whether this evidence warrants any correction (source-neutral)."""
    return bool(select_categories(inp))


def select_category(inp: CorrectionPolicyInput) -> str | None:
    """Compatibility wrapper — the first canonical category, or None."""
    cats = select_categories(inp)
    return cats[0] if cats else None
