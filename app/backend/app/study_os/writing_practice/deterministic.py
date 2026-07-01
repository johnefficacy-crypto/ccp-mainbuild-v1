"""Stage-1 deterministic writing checks (architecture §5.2, §4.7).

Pure, synchronous, no external calls. These are the authoritative
server-side checks run at submit time. The word-count rule is versioned so the
counting semantics stay auditable (§5.2).

Nothing here touches the database — callers persist the results.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

# Bump when the counting/tokenisation rule changes; stored on the evaluation row
# as deterministic_evaluator_version so historical counts stay auditable.
DETERMINISTIC_EVALUATOR_VERSION = "det-v1"

# A "word" is a maximal run of letters/digits/apostrophes/hyphens. Punctuation
# and whitespace separate words; hyphenated words count once.
_WORD_RE = re.compile(r"[^\W_]+(?:['\-][^\W_]+)*", re.UNICODE)
# Sentence terminators for a coarse sentence count.
_SENTENCE_SPLIT_RE = re.compile(r"[.!?]+(?:\s|$)")


def _normalise(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def tokenize_words(text: str) -> list[str]:
    """Return the list of word tokens (see module docstring for the rule)."""
    return _WORD_RE.findall(_normalise(text))


def word_count(text: str) -> int:
    return len(tokenize_words(text))


def sentence_count(text: str) -> int:
    stripped = _normalise(text).strip()
    if not stripped:
        return 0
    parts = [p for p in _SENTENCE_SPLIT_RE.split(stripped) if p.strip()]
    # A trailing clause without terminal punctuation still counts as a sentence.
    return max(len(parts), 1)


def required_word_present(answer_text: str, required_word: str) -> bool:
    """Case-insensitive word-boundary token presence (§4.7 stage-1)."""
    target = _normalise(required_word).casefold()
    return any(tok.casefold() == target for tok in tokenize_words(answer_text))


@dataclass
class DeterministicResult:
    """Structured Stage-1 result (persisted as writing_evaluations.deterministic_result)."""

    evaluator_version: str = DETERMINISTIC_EVALUATOR_VERSION
    server_word_count: int = 0
    sentence_count: int = 0
    is_empty: bool = False
    min_words_ok: bool = True
    max_words_ok: bool = True
    required_words_present: dict[str, bool] = field(default_factory=dict)
    required_words_all_present: bool = True
    duplicate_of_units: list[int] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Unit-level deterministic gate: no blocking violations."""
        return not self.violations

    def to_dict(self) -> dict:
        return {
            "evaluator_version": self.evaluator_version,
            "server_word_count": self.server_word_count,
            "sentence_count": self.sentence_count,
            "is_empty": self.is_empty,
            "min_words_ok": self.min_words_ok,
            "max_words_ok": self.max_words_ok,
            "required_words_present": self.required_words_present,
            "required_words_all_present": self.required_words_all_present,
            "duplicate_of_units": self.duplicate_of_units,
            "violations": self.violations,
        }


def evaluate_unit(
    answer_text: str,
    *,
    min_words: int | None = None,
    max_words: int | None = None,
    required_words: list[str] | None = None,
    other_unit_texts: dict[int, str] | None = None,
) -> DeterministicResult:
    """Run all Stage-1 checks for one unit's answer.

    ``other_unit_texts`` maps unit_number -> answer_text for sibling units, used
    for cross-unit duplicate detection. ``required_words`` here is the per-unit
    subset if the exercise assigns words to a unit; session-level coverage is a
    separate check (§4.7).
    """
    result = DeterministicResult()
    wc = word_count(answer_text)
    result.server_word_count = wc
    result.sentence_count = sentence_count(answer_text)
    result.is_empty = wc == 0

    if result.is_empty:
        result.violations.append("empty_answer")

    if min_words is not None and wc < min_words:
        result.min_words_ok = False
        result.violations.append("below_min_words")
    if max_words is not None and wc > max_words:
        result.max_words_ok = False
        result.violations.append("above_max_words")

    for rw in required_words or []:
        present = required_word_present(answer_text, rw)
        result.required_words_present[rw] = present
        if not present:
            result.required_words_all_present = False
    if not result.required_words_all_present:
        result.violations.append("missing_required_word")

    if other_unit_texts:
        norm_self = _normalise(answer_text).strip().casefold()
        if norm_self:
            for num, txt in sorted(other_unit_texts.items()):
                if _normalise(txt).strip().casefold() == norm_self:
                    result.duplicate_of_units.append(num)
        if result.duplicate_of_units:
            result.violations.append("duplicate_sentence")

    return result


def required_word_coverage(
    required_words: list[str], submitted_texts: list[str]
) -> tuple[bool, dict[str, bool]]:
    """Session-level required-word coverage (§4.7).

    Coverage is satisfied when each required word appears (case-insensitively,
    as a whole token) in at least one submitted answer. One sentence may satisfy
    multiple required words. Returns (all_covered, per-word presence).
    """
    per_word = {
        rw: any(required_word_present(txt, rw) for txt in submitted_texts)
        for rw in required_words
    }
    return (all(per_word.values()) if per_word else True), per_word
