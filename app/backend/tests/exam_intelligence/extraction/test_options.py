"""Unit tests for options.py — Module A (extract_options) and Module B gates.

Covers:
  Module A: option pattern matching, text assembly, multi-line options.
  Module B: left-edge anchor gate, per-question sequential reset,
            statement-numeral rejection, Roman/Arabic disambiguation.
  Regression: stem recall must not regress (tested via find_stem_end gate).
"""
from __future__ import annotations

import pytest

from app.exam_intelligence.extraction.options import extract_options
from app.exam_intelligence.extraction.segmentation import find_stem_end, reconstruct_lines
from app.exam_intelligence.extraction.types import Word


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _w(
    text: str,
    x: float,
    y: float,
    w: float = 0.12,
    h: float = 0.018,
    page: int = 1,
) -> Word:
    return Word(text=text, bbox=(x, y, x + w, y + h), page=page, confidence=90.0)


def _line(*words: Word) -> list[Word]:
    return list(words)


COL_LEFT = 0.02   # column left edge used throughout tests


# ---------------------------------------------------------------------------
# Module A — pattern matching and text assembly
# ---------------------------------------------------------------------------

class TestModuleAPatterns:
    """extract_options recognises all supported option-anchor patterns."""

    def _options(self, lines):
        return extract_options(lines, COL_LEFT)

    def test_paren_lowercase_abcd(self):
        lines = [
            _line(_w("(a)", COL_LEFT, 0.10), _w("Alpha", 0.15, 0.10)),
            _line(_w("(b)", COL_LEFT, 0.13), _w("Beta",  0.15, 0.13)),
            _line(_w("(c)", COL_LEFT, 0.16), _w("Gamma", 0.15, 0.16)),
            _line(_w("(d)", COL_LEFT, 0.19), _w("Delta", 0.15, 0.19)),
        ]
        opts = self._options(lines)
        assert len(opts) == 4
        labels = [o.label for o in opts]
        assert labels == ['a', 'b', 'c', 'd']

    def test_paren_uppercase_ABCD(self):
        lines = [
            _line(_w("(A)", COL_LEFT, 0.10), _w("Alpha", 0.15, 0.10)),
            _line(_w("(B)", COL_LEFT, 0.13), _w("Beta",  0.15, 0.13)),
        ]
        opts = self._options(lines)
        assert len(opts) == 2
        assert opts[0].label == 'a'
        assert opts[1].label == 'b'

    def test_suffix_paren_lowercase(self):
        lines = [
            _line(_w("a)", COL_LEFT, 0.10), _w("First",  0.15, 0.10)),
            _line(_w("b)", COL_LEFT, 0.13), _w("Second", 0.15, 0.13)),
        ]
        opts = self._options(lines)
        assert len(opts) == 2

    def test_suffix_period_lowercase(self):
        lines = [
            _line(_w("a.", COL_LEFT, 0.10), _w("First",  0.15, 0.10)),
            _line(_w("b.", COL_LEFT, 0.13), _w("Second", 0.15, 0.13)),
        ]
        opts = self._options(lines)
        assert len(opts) == 2

    def test_numeric_paren(self):
        lines = [
            _line(_w("(1)", COL_LEFT, 0.10), _w("One",   0.15, 0.10)),
            _line(_w("(2)", COL_LEFT, 0.13), _w("Two",   0.15, 0.13)),
            _line(_w("(3)", COL_LEFT, 0.16), _w("Three", 0.15, 0.16)),
            _line(_w("(4)", COL_LEFT, 0.19), _w("Four",  0.15, 0.19)),
        ]
        opts = self._options(lines)
        assert [o.label for o in opts] == ['1', '2', '3', '4']

    def test_numeric_period(self):
        lines = [
            _line(_w("1.", COL_LEFT, 0.10), _w("One",   0.15, 0.10)),
            _line(_w("2.", COL_LEFT, 0.13), _w("Two",   0.15, 0.13)),
        ]
        opts = self._options(lines)
        assert len(opts) == 2

    def test_option_text_assembled_correctly(self):
        lines = [
            _line(_w("(a)", COL_LEFT, 0.10), _w("Both", 0.15, 0.10), _w("1 and 2", 0.28, 0.10)),
            _line(_w("(b)", COL_LEFT, 0.13), _w("Only 1", 0.15, 0.13)),
        ]
        opts = self._options(lines)
        assert "Both" in opts[0].option_text
        assert "1 and 2" in opts[0].option_text
        assert "Only 1" in opts[1].option_text

    def test_multiline_option_text(self):
        """Option text spanning two lines is joined with a space."""
        lines = [
            _line(_w("(a)", COL_LEFT, 0.10), _w("First", 0.15, 0.10)),
            _line(_w("part", 0.15, 0.13)),               # continuation (no label)
            _line(_w("(b)", COL_LEFT, 0.16), _w("Second", 0.15, 0.16)),
        ]
        opts = self._options(lines)
        assert len(opts) == 2
        assert "First" in opts[0].option_text
        assert "part" in opts[0].option_text

    def test_empty_lines_returns_empty(self):
        assert extract_options([], COL_LEFT) == ()

    def test_no_option_markers_returns_empty(self):
        lines = [
            _line(_w("Select", COL_LEFT, 0.10), _w("the code below", 0.15, 0.10)),
        ]
        assert extract_options(lines, COL_LEFT) == ()


# ---------------------------------------------------------------------------
# Module B — left-edge anchor gate
# ---------------------------------------------------------------------------

class TestModuleBLeftEdgeGate:
    """Option markers NOT at the column left edge must be rejected."""

    def test_at_left_edge_accepted(self):
        # x=0.02 ≤ COL_LEFT(0.02) + 0.04 → accepted
        lines = [
            _line(_w("(a)", 0.02, 0.10), _w("Alpha", 0.15, 0.10)),
            _line(_w("(b)", 0.02, 0.13), _w("Beta",  0.15, 0.13)),
        ]
        opts = extract_options(lines, column_left_edge=0.02)
        assert len(opts) == 2

    def test_indented_option_label_rejected(self):
        # x=0.10 > COL_LEFT(0.02) + 0.04 → body enumerator, rejected
        lines = [
            _line(_w("(a)", 0.10, 0.10), _w("Alpha", 0.20, 0.10)),
            _line(_w("(b)", 0.10, 0.13), _w("Beta",  0.20, 0.13)),
        ]
        opts = extract_options(lines, column_left_edge=0.02)
        assert opts == ()

    def test_mixed_left_edge_and_indented(self):
        # (a) at left edge accepted, inline (i) and (ii) rejected,
        # (b) at left edge accepted.
        lines = [
            _line(_w("(a)", 0.02, 0.10), _w("Alpha", 0.15, 0.10)),
            _line(_w("(i)", 0.12, 0.13), _w("sub1",  0.20, 0.13)),   # inline, rejected
            _line(_w("(ii)", 0.12, 0.16), _w("sub2", 0.20, 0.16)),   # inline, rejected
            _line(_w("(b)", 0.02, 0.19), _w("Beta",  0.15, 0.19)),
        ]
        opts = extract_options(lines, column_left_edge=0.02)
        assert len(opts) == 2
        assert [o.label for o in opts] == ['a', 'b']

    def test_exactly_at_gap_boundary_accepted(self):
        # x = COL_LEFT + _ANCHOR_X_GAP exactly → accepted (≤ is inclusive)
        boundary_x = 0.02 + 0.04  # 0.06
        lines = [
            _line(_w("(a)", boundary_x, 0.10), _w("Alpha", 0.18, 0.10)),
            _line(_w("(b)", boundary_x, 0.13), _w("Beta",  0.18, 0.13)),
        ]
        opts = extract_options(lines, column_left_edge=0.02)
        assert len(opts) == 2

    def test_one_past_gap_boundary_rejected(self):
        past_x = 0.02 + 0.04 + 0.001  # 0.061 > 0.06
        lines = [
            _line(_w("(a)", past_x, 0.10), _w("Alpha", 0.18, 0.10)),
            _line(_w("(b)", past_x, 0.13), _w("Beta",  0.18, 0.13)),
        ]
        opts = extract_options(lines, column_left_edge=0.02)
        assert opts == ()


# ---------------------------------------------------------------------------
# Module B — per-question sequential reset
# ---------------------------------------------------------------------------

class TestModuleBSequentialReset:
    """Labels must form a consecutive sequence starting at 'a' or '1'."""

    def test_sequence_starting_at_b_rejected(self):
        # No 'a' first → rejected
        lines = [
            _line(_w("(b)", COL_LEFT, 0.10), _w("Beta",  0.15, 0.10)),
            _line(_w("(c)", COL_LEFT, 0.13), _w("Gamma", 0.15, 0.13)),
        ]
        assert extract_options(lines, COL_LEFT) == ()

    def test_non_consecutive_sequence_truncated(self):
        # a, c (skips b) → stops at a; only 1 valid → empty
        lines = [
            _line(_w("(a)", COL_LEFT, 0.10), _w("Alpha", 0.15, 0.10)),
            _line(_w("(c)", COL_LEFT, 0.13), _w("Gamma", 0.15, 0.13)),
        ]
        assert extract_options(lines, COL_LEFT) == ()

    def test_single_option_insufficient(self):
        # Only (a) present → < 2 valid → empty
        lines = [
            _line(_w("(a)", COL_LEFT, 0.10), _w("Alpha", 0.15, 0.10)),
        ]
        assert extract_options(lines, COL_LEFT) == ()

    def test_two_options_accepted(self):
        lines = [
            _line(_w("(a)", COL_LEFT, 0.10), _w("Alpha", 0.15, 0.10)),
            _line(_w("(b)", COL_LEFT, 0.13), _w("Beta",  0.15, 0.13)),
        ]
        opts = extract_options(lines, COL_LEFT)
        assert len(opts) == 2

    def test_extra_option_after_d_ignored(self):
        # Four valid a-d; any extra labels after d are ignored (max 4).
        lines = [
            _line(_w("(a)", COL_LEFT, 0.10), _w("Alpha", 0.15, 0.10)),
            _line(_w("(b)", COL_LEFT, 0.13), _w("Beta",  0.15, 0.13)),
            _line(_w("(c)", COL_LEFT, 0.16), _w("Gamma", 0.15, 0.16)),
            _line(_w("(d)", COL_LEFT, 0.19), _w("Delta", 0.15, 0.19)),
            _line(_w("(e)", COL_LEFT, 0.22), _w("Epsilon", 0.15, 0.22)),  # beyond d → ignored
        ]
        opts = extract_options(lines, COL_LEFT)
        assert len(opts) == 4
        assert [o.label for o in opts] == ['a', 'b', 'c', 'd']

    def test_numeric_sequence_reset(self):
        # numeric starting at '2' → rejected
        lines = [
            _line(_w("(2)", COL_LEFT, 0.10), _w("Two",   0.15, 0.10)),
            _line(_w("(3)", COL_LEFT, 0.13), _w("Three", 0.15, 0.13)),
        ]
        assert extract_options(lines, COL_LEFT) == ()

    def test_mixed_alpha_numeric_not_treated_as_sequence(self):
        # 'a' then '2' → sequence broken (different systems)
        lines = [
            _line(_w("(a)", COL_LEFT, 0.10), _w("Alpha", 0.15, 0.10)),
            _line(_w("(2)", COL_LEFT, 0.13), _w("Two",   0.15, 0.13)),
        ]
        opts = extract_options(lines, COL_LEFT)
        # Only 'a' in valid (1 item) → < 2 → empty
        assert opts == ()


# ---------------------------------------------------------------------------
# Module B — statement-numeral vs option-marker disambiguation
# ---------------------------------------------------------------------------

class TestModuleBDisambiguation:
    """Roman and Arabic statement numerals inside the body must not become options."""

    def test_roman_statement_enumerators_inline_rejected(self):
        # I. II. III. are inline (x > left_edge + gap) → not option markers
        lines = [
            _line(_w("I.",   0.10, 0.10), _w("First stmt",  0.18, 0.10)),
            _line(_w("II.",  0.10, 0.13), _w("Second stmt", 0.18, 0.13)),
            _line(_w("III.", 0.10, 0.16), _w("Third stmt",  0.18, 0.16)),
        ]
        # These don't match _OPT_RE anyway (Roman, not a-d/1-4), so already excluded.
        assert extract_options(lines, column_left_edge=0.02) == ()

    def test_arabic_inline_statement_enumerators_rejected(self):
        # 1. 2. 3. inline (indented) → rejected by left-edge gate
        lines = [
            _line(_w("1.", 0.15, 0.10), _w("Emergence", 0.22, 0.10)),
            _line(_w("2.", 0.15, 0.13), _w("Transition", 0.22, 0.13)),
            _line(_w("3.", 0.15, 0.16), _w("Development", 0.22, 0.16)),
            _line(_w("4.", 0.15, 0.19), _w("Decline",    0.22, 0.19)),
        ]
        assert extract_options(lines, column_left_edge=0.02) == ()

    def test_inline_paren_enumerators_rejected(self):
        # (a), (b) inside a "match the following" column — indented
        lines = [
            _line(_w("(a)", 0.09, 0.10), _w("Indus",   0.18, 0.10)),
            _line(_w("(b)", 0.09, 0.13), _w("Ganges",  0.18, 0.13)),
            _line(_w("(c)", 0.09, 0.16), _w("Krishna", 0.18, 0.16)),
        ]
        assert extract_options(lines, column_left_edge=0.02) == ()

    def test_option_at_left_edge_coexists_with_body_enumerators(self):
        """Genuine options (left edge) are extracted even when body has inline labels."""
        lines = [
            # Inline body statement enumerators (rejected by gate)
            _line(_w("(i)",  0.08, 0.02), _w("sub-claim 1", 0.18, 0.02)),
            _line(_w("(ii)", 0.08, 0.05), _w("sub-claim 2", 0.18, 0.05)),
            # Genuine MCQ options (at left edge)
            _line(_w("(a)", 0.02, 0.10), _w("Both i and ii",   0.12, 0.10)),
            _line(_w("(b)", 0.02, 0.13), _w("Only i",          0.12, 0.13)),
            _line(_w("(c)", 0.02, 0.16), _w("Only ii",         0.12, 0.16)),
            _line(_w("(d)", 0.02, 0.19), _w("Neither i nor ii", 0.12, 0.19)),
        ]
        opts = extract_options(lines, column_left_edge=0.02)
        assert len(opts) == 4
        assert [o.label for o in opts] == ['a', 'b', 'c', 'd']


# ---------------------------------------------------------------------------
# Regression: find_stem_end left-edge gate for option labels
# ---------------------------------------------------------------------------

class TestFindStemEndOptionGate:
    """Body (a)/(b) enumerators must not prematurely end the stem.

    This is the Module B fix applied inside find_stem_end: option labels are
    only treated as stem-end markers when they sit at the column left edge.
    """

    def _lines(self, *line_defs):
        return list(line_defs)

    def test_option_at_left_edge_ends_stem(self):
        # Anchor at index 0; (a) at left edge at index 1 → stem ends at 1.
        anchor = _line(_w("1.", COL_LEFT, 0.02), _w("Consider", 0.12, 0.02))
        option_a = _line(_w("(a)", COL_LEFT, 0.06), _w("Alpha", 0.12, 0.06))
        lines = [anchor, option_a]
        end = find_stem_end(lines, anchor_idx=0, column_left_edge=COL_LEFT)
        assert end == 1

    def test_indented_paren_label_does_not_end_stem(self):
        # (a) at x=0.12 (indented) must NOT end the stem — it's a body enumerator.
        anchor = _line(_w("1.", COL_LEFT, 0.02), _w("Match the following", 0.12, 0.02))
        body_a = _line(_w("(a)", 0.12, 0.06), _w("Indus", 0.22, 0.06))
        body_b = _line(_w("(b)", 0.12, 0.09), _w("Ganges", 0.22, 0.09))
        opt_a  = _line(_w("(a)", COL_LEFT, 0.14), _w("Only A", 0.12, 0.14))
        lines = [anchor, body_a, body_b, opt_a]
        end = find_stem_end(lines, anchor_idx=0, column_left_edge=COL_LEFT)
        # Stem must run through body_a and body_b; stops at opt_a (left edge)
        assert end == 3

    def test_mcq_footer_still_ends_stem(self):
        # MCQ footer detection is unchanged by the option-label gate fix.
        anchor = _line(_w("1.", COL_LEFT, 0.02), _w("Consider", 0.12, 0.02))
        footer = _line(_w("Select", COL_LEFT, 0.06), _w("the answer using codes below", 0.15, 0.06))
        lines = [anchor, footer]
        end = find_stem_end(lines, anchor_idx=0, column_left_edge=COL_LEFT)
        assert end == 1

    def test_next_anchor_still_ends_stem(self):
        anchor1 = _line(_w("1.", COL_LEFT, 0.02), _w("First", 0.12, 0.02))
        anchor2 = _line(_w("2.", COL_LEFT, 0.10), _w("Second", 0.12, 0.10))
        lines = [anchor1, anchor2]
        end = find_stem_end(lines, anchor_idx=0, column_left_edge=COL_LEFT)
        assert end == 1
