"""Option extraction (Module A) and Roman/Arabic disambiguation (Module B).

Module A — extract_options
  Scans lines between stem_end and the next question anchor, identifying lines
  whose first non-noise token matches an option-anchor pattern.  Assembles
  full option text (multi-line) and emits up to 4 ExtractedOption objects.

Module B — left-edge gate + sequential validation (integrated into extract_options)
  Genuine option markers sit at the column left edge (x_min ≤ column_left +
  _ANCHOR_X_GAP) and form a consecutive sequence (a→b→c→d or 1→2→3→4).
  Inline statement enumerators ((i), (ii), 1. inside the body) are indented
  past the gate threshold and are rejected even if they match the pattern.
  The per-question reset means any label sequence that doesn't start at 'a'
  or '1' (position 0) is rejected.
"""
from __future__ import annotations

import re

from .types import ExtractedOption, Word

# Option-anchor pattern.  Group assignments:
#   1 → (a)–(d) / (A)–(D)   2 → a)–d) / a.–d.   3 → (1)–(4)   4 → 1)–4.
_OPT_RE = re.compile(
    r'^\s*(?:'
    r'\(([a-dA-D])\)'    # (a)  (b)  (A)  (B)
    r'|([a-dA-D])[).]'   # a)   b.   A)   B.
    r'|\(([1-4])\)'      # (1)  (2)  (3)  (4)
    r'|([1-4])[).]'      # 1)   2.   3)   4.
    r')'
)

# Strips the leading option label (and optional whitespace) from a line.
_OPT_STRIP_RE = re.compile(
    r'^\s*(?:'
    r'\([a-dA-D1-4]\)'   # (a) / (1)
    r'|[a-dA-D1-4][).]'  # a)  / 1.
    r')\s*'
)

# Map normalised label → position (0-based).
_ALPHA_POS = {c: i for i, c in enumerate('abcd')}
_NUM_POS   = {str(i + 1): i for i in range(4)}

_NOISE_RE        = re.compile(r'^[|\s]+$')
_LEADING_NOISE_RE = re.compile(r'^[|\s]+')

# Must mirror segmentation._ANCHOR_X_GAP so the same spatial threshold applies
# to both question ordinals and option labels.
_ANCHOR_X_GAP = 0.04


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _first_content(line: list[Word]) -> tuple[int, Word] | None:
    """Return (index, word) of the first non-noise token in the line."""
    for i, w in enumerate(line):
        if not _NOISE_RE.match(w.text):
            return i, w
    return None


def _line_text_from(line: list[Word], start: int) -> str:
    return _LEADING_NOISE_RE.sub('', ' '.join(w.text for w in line[start:]))


def _extract_label(line: list[Word]) -> tuple[str, int] | None:
    """If the line starts with a recognised option label, return (normalised_label, ci).

    ci is the index of the first content word (used for the left-edge gate).
    Returns None if no label is found.
    """
    res = _first_content(line)
    if res is None:
        return None
    ci, _ = res
    text = _line_text_from(line, ci)
    m = _OPT_RE.match(text)
    if not m:
        return None
    raw = next(g for g in m.groups() if g is not None)
    return raw.lower(), ci


def _at_left_edge(line: list[Word], ci: int, column_left_edge: float) -> bool:
    """Module B gate: the anchor token must sit at the column left edge."""
    return line[ci].bbox[0] <= column_left_edge + _ANCHOR_X_GAP


def _label_position(label: str) -> int | None:
    if label in _ALPHA_POS:
        return _ALPHA_POS[label]
    if label in _NUM_POS:
        return _NUM_POS[label]
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_options(
    option_lines: list[list[Word]],
    column_left_edge: float,
) -> tuple[ExtractedOption, ...]:
    """Module A + B: extract up to 4 options from lines after the stem.

    Returns an empty tuple for non-MCQ questions or when the option sequence
    cannot be validated.

    Args:
        option_lines: Lines between the stem end and the next question anchor.
        column_left_edge: Effective left edge of the column (normalised x).
    """
    # --- Module A: scan for option-anchor lines ----------------------------
    # Each entry: (line_idx, normalised_label, content_word_index)
    candidates: list[tuple[int, str, int]] = []

    for i, line in enumerate(option_lines):
        res = _extract_label(line)
        if res is None:
            continue
        label, ci = res
        # --- Module B: left-edge gate -------------------------------------
        if not _at_left_edge(line, ci, column_left_edge):
            continue
        candidates.append((i, label, ci))

    if not candidates:
        return ()

    # --- Module B: per-question sequential validation ---------------------
    # The sequence must start at position 0 (label 'a' or '1') and be
    # strictly consecutive.  Any break discards the remainder.
    first_label = candidates[0][1]
    if _label_position(first_label) != 0:
        return ()

    # Choose the label system (alpha or numeric) from the first match.
    pos_map = _ALPHA_POS if first_label in _ALPHA_POS else _NUM_POS

    valid: list[tuple[int, str, int]] = [candidates[0]]
    for li, label, ci in candidates[1:]:
        if label not in pos_map:
            break
        if pos_map[label] != pos_map[valid[-1][1]] + 1:
            break
        valid.append((li, label, ci))
        if len(valid) == 4:
            break

    if len(valid) < 2:
        return ()

    # --- Module A: assemble option text -----------------------------------
    options: list[ExtractedOption] = []
    for k, (li, label, _ci) in enumerate(valid):
        end_li = valid[k + 1][0] if k + 1 < len(valid) else len(option_lines)
        lines_for_opt = option_lines[li:end_li]

        parts: list[str] = []
        for j, ln in enumerate(lines_for_opt):
            raw_text = _line_text_from(ln, 0)
            if j == 0:
                raw_text = _OPT_STRIP_RE.sub('', raw_text, count=1)
            raw_text = raw_text.strip()
            if raw_text:
                parts.append(raw_text)

        options.append(ExtractedOption(label=label, option_text=' '.join(parts)))

    return tuple(options)
