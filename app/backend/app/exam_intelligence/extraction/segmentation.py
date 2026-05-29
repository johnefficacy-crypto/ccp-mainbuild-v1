"""Vertical clustering and question-block emission.

Algorithm (v3 — ordinal-anchored, document-monotonic, stem-only):
1. Detect columns via x-histogram bimodality (layout.py).
2. Assign words to columns (layout.py).
3. Within each column, reconstruct visual lines by y-overlap (reconstruct_lines).
4. Find anchor lines: first word x_min ≤ column_left_edge + 0.04 AND ordinal ∈ [1, 100]
   AND ordinal > last_accepted_ordinal (monotonic).
5. For each anchor, find_stem_end: stop at option labels, MCQ footers, or next anchor.
6. Emit ExtractedQuestion for each anchor–stem span.

Public API (v3, used by pipeline.py):
    reconstruct_lines, join_lines_text, AnchorLine, find_anchor_lines,
    find_stem_end, build_question, segment_column

Legacy API (kept for test_segmentation.py backward compatibility):
    segment_page, cluster_by_vertical_gap, block_to_question
"""
from __future__ import annotations

import re
import statistics
from dataclasses import dataclass

from .layout import assign_words_to_columns, detect_columns
from .ordinal import detect_ordinal, strip_ordinal
from .types import ExtractedQuestion, Region, Word

_ORDINAL_MIN = 1
_ORDINAL_MAX = 200
_ANCHOR_MAX = 100         # questions rarely exceed 100; filters OCR noise above this
_ANCHOR_X_GAP = 0.04      # x_min must be within this absolute distance of column left edge

_WS_RE = re.compile(r'[ \t]+')
_OPTION_RE = re.compile(r'^\s*\([a-dA-D]\)')
# Matches a word token that is entirely OCR gutter noise (pipe chars and/or whitespace).
# Used to skip leading noise WORDS before the spatial gate so the gate evaluates the
# ordinal token's bbox, not the pipe's.
_NOISE_WORD_RE = re.compile(r'^[|\s]+$')
# Strips leading pipe/whitespace from a TEXT string (for build_question first-line clean-up).
_LEADING_NOISE_RE = re.compile(r'^[|\s]+')
_MCQ_FOOTER_RES = [
    re.compile(r'select\s+the\s+answer', re.IGNORECASE),
    re.compile(r'codes?\s+below', re.IGNORECASE),
    re.compile(r'^\s*which\s+of\s+the\s+following.*given\s+below', re.IGNORECASE),
    re.compile(r'^\s*choose\s+the\s+correct', re.IGNORECASE),
]

# Legacy fraction gate kept for segment_page backward compatibility.
_ANCHOR_X_FRACTION = 0.35


# ---------------------------------------------------------------------------
# v3 public API
# ---------------------------------------------------------------------------

def reconstruct_lines(words: list[Word]) -> list[list[Word]]:
    """Group words into visual lines by y-overlap.

    Two words are on the same line when their vertical overlap ≥ 60% of the
    smaller word's height.  Words within each line are sorted left-to-right.
    """
    if not words:
        return []

    sorted_words = sorted(words, key=lambda w: (w.bbox[1], w.bbox[0]))

    lines: list[list[Word]] = []
    current: list[Word] = [sorted_words[0]]
    cur_y_min = sorted_words[0].bbox[1]
    cur_y_max = sorted_words[0].bbox[3]

    for word in sorted_words[1:]:
        wy_min, wy_max = word.bbox[1], word.bbox[3]
        word_h = wy_max - wy_min

        overlap_top = max(wy_min, cur_y_min)
        overlap_bot = min(wy_max, cur_y_max)
        overlap = max(0.0, overlap_bot - overlap_top)

        line_h = cur_y_max - cur_y_min
        smaller_h = min(word_h, line_h)

        if smaller_h > 0 and (overlap / smaller_h) >= 0.60:
            current.append(word)
            cur_y_max = max(cur_y_max, wy_max)
        else:
            lines.append(sorted(current, key=lambda w: w.bbox[0]))
            current = [word]
            cur_y_min = wy_min
            cur_y_max = wy_max

    if current:
        lines.append(sorted(current, key=lambda w: w.bbox[0]))

    return lines


def join_lines_text(lines: list[list[Word]]) -> str:
    """Join lines with newline; words within a line with space."""
    return '\n'.join(' '.join(w.text for w in line) for line in lines if line)


@dataclass
class AnchorLine:
    line_idx: int
    ordinal: int


def find_anchor_lines(
    lines: list[list[Word]],
    effective_left: float,
    last_accepted_ordinal: int = 0,
) -> list[AnchorLine]:
    """Identify question-anchor lines within a column's reconstructed lines.

    A line is an anchor if:
    * First word x_min ≤ effective_left + _ANCHOR_X_GAP (0.04).
    * Joined line text starts with an ordinal ∈ [1, _ANCHOR_MAX].
    * Ordinal is strictly greater than last_accepted_ordinal (monotonic).
    """
    anchors: list[AnchorLine] = []
    running = last_accepted_ordinal

    for idx, line in enumerate(lines):
        if not line:
            continue
        # Skip leading pure-noise tokens so the spatial gate evaluates the
        # ordinal token's x position, not the gutter pipe's.
        ci = 0
        while ci < len(line) and _NOISE_WORD_RE.match(line[ci].text):
            ci += 1
        if ci >= len(line):
            continue
        content_word = line[ci]
        if content_word.bbox[0] > effective_left + _ANCHOR_X_GAP:
            continue
        # Build text from the content word onward; strip any fused leading noise
        # (e.g. "|26." as a single OCR token) before ordinal matching.
        text = _LEADING_NOISE_RE.sub('', ' '.join(w.text for w in line[ci:]))
        ordinal = detect_ordinal(text)
        if ordinal is None:
            continue
        if not (_ORDINAL_MIN <= ordinal <= _ANCHOR_MAX):
            continue
        if ordinal <= running:
            continue
        running = ordinal
        anchors.append(AnchorLine(line_idx=idx, ordinal=ordinal))

    return anchors


def find_stem_end(
    lines: list[list[Word]],
    anchor_idx: int,
    column_left_edge: float,
) -> int:
    """Return the exclusive end index for this anchor's stem.

    Stops when the next line is:
    * An option label: first word matches _OPTION_RE (e.g. "(a)").
    * An MCQ footer: line text matches a footer pattern.
    * The next anchor candidate: first word within x-gate AND detect_ordinal succeeds.
    Returns len(lines) if no stop is found.
    """
    for i in range(anchor_idx + 1, len(lines)):
        line = lines[i]
        if not line:
            continue
        # Skip leading noise tokens — same design principle as find_anchor_lines.
        ci = 0
        while ci < len(line) and _NOISE_WORD_RE.match(line[ci].text):
            ci += 1
        if ci >= len(line):
            continue
        content_word = line[ci]
        text = _LEADING_NOISE_RE.sub('', ' '.join(w.text for w in line[ci:]))

        if _OPTION_RE.match(content_word.text):
            return i

        for pat in _MCQ_FOOTER_RES:
            if pat.search(text):
                return i

        if content_word.bbox[0] <= column_left_edge + _ANCHOR_X_GAP:
            if detect_ordinal(text) is not None:
                return i

    return len(lines)


def build_question(
    ordinal: int,
    stem_lines: list[list[Word]],
    page: int,
) -> ExtractedQuestion | None:
    """Build an ExtractedQuestion from an ordinal and its stem lines."""
    all_words = [w for line in stem_lines for w in line]
    if not all_words:
        return None

    first_line_raw = ' '.join(w.text for w in stem_lines[0])
    first_line_text = strip_ordinal(_LEADING_NOISE_RE.sub('', first_line_raw))
    rest = [_LEADING_NOISE_RE.sub('', ' '.join(w.text for w in line)) for line in stem_lines[1:] if line]
    question_text = '\n'.join(
        _WS_RE.sub(' ', part).strip()
        for part in [first_line_text] + rest
        if part.strip()
    ).strip()

    if not question_text:
        return None

    x_min = min(w.bbox[0] for w in all_words)
    y_min = min(w.bbox[1] for w in all_words)
    x_max = max(w.bbox[2] for w in all_words)
    y_max = max(w.bbox[3] for w in all_words)
    region = Region(page=page, bbox=(x_min, y_min, x_max, y_max))

    confs = [w.confidence for w in all_words if w.confidence >= 0]
    ocr_p50 = statistics.median(confs) if confs else 0.0

    return ExtractedQuestion(
        question_number=ordinal,
        question_text=question_text,
        regions=[region],
        confidence_by_field={"ocr_p50": ocr_p50, "segmentation": 1.0},
    )


def segment_column(
    lines: list[list[Word]],
    column_left_edge: float,
    last_accepted_ordinal: int,
    page: int,
) -> tuple[list[ExtractedQuestion], int]:
    """Segment one column into questions.

    Returns (questions, updated_last_accepted_ordinal) so the caller can
    thread document-wide monotonicity across columns and pages.
    """
    anchors = find_anchor_lines(lines, column_left_edge, last_accepted_ordinal)

    questions: list[ExtractedQuestion] = []
    for anchor in anchors:
        stem_end = find_stem_end(lines, anchor.line_idx, column_left_edge)
        stem_lines = lines[anchor.line_idx:stem_end]
        q = build_question(anchor.ordinal, stem_lines, page)
        if q is not None:
            questions.append(q)

    updated = anchors[-1].ordinal if anchors else last_accepted_ordinal
    return questions, updated


# ---------------------------------------------------------------------------
# Legacy segment_page — kept for test_segmentation.py backward compatibility.
# Uses the older _ANCHOR_X_FRACTION=0.35 gate rather than the 0.02 absolute gate.
# ---------------------------------------------------------------------------

def segment_page(words: list[Word], page: int) -> list[ExtractedQuestion]:
    """Per-page segmentation using the legacy x-fraction anchor gate.

    Preserved so existing unit tests continue to pass unchanged.
    Production extraction uses segment_column (via pipeline._process_page_words).
    """
    if not words:
        return []

    columns = detect_columns(words)
    col_words = assign_words_to_columns(words, columns)

    questions: list[ExtractedQuestion] = []
    for col_idx in sorted(col_words.keys()):
        col = col_words[col_idx]
        if not col:
            continue
        col_start, col_end = columns[col_idx]
        lines = _reconstruct_lines(col)
        questions.extend(_segment_lines(lines, col_start, col_end, page))

    return questions


# ---------------------------------------------------------------------------
# Legacy internals for segment_page
# ---------------------------------------------------------------------------

def _reconstruct_lines(words: list[Word]) -> list[list[Word]]:
    if not words:
        return []

    heights = [w.bbox[3] - w.bbox[1] for w in words if w.bbox[3] > w.bbox[1]]
    median_h = statistics.median(heights) if heights else 0.015
    line_tol = 0.6 * median_h

    sorted_words = sorted(words, key=lambda w: (w.bbox[1], w.bbox[0]))

    lines: list[list[Word]] = []
    current: list[Word] = [sorted_words[0]]
    line_y_top = sorted_words[0].bbox[1]
    line_y_bot = sorted_words[0].bbox[3]

    for word in sorted_words[1:]:
        word_y_mid = (word.bbox[1] + word.bbox[3]) / 2.0
        line_y_mid = (line_y_top + line_y_bot) / 2.0

        if abs(word_y_mid - line_y_mid) <= line_tol:
            current.append(word)
            line_y_bot = max(line_y_bot, word.bbox[3])
        else:
            lines.append(sorted(current, key=lambda w: w.bbox[0]))
            current = [word]
            line_y_top = word.bbox[1]
            line_y_bot = word.bbox[3]

    if current:
        lines.append(sorted(current, key=lambda w: w.bbox[0]))

    return lines


def _line_text(line: list[Word]) -> str:
    return ' '.join(w.text for w in line)


def _is_anchor(line: list[Word], col_start: float, col_end: float) -> int | None:
    if not line:
        return None
    first_word = line[0]
    col_width = col_end - col_start
    threshold = col_start + _ANCHOR_X_FRACTION * col_width
    if first_word.bbox[0] > threshold:
        return None
    ordinal = detect_ordinal(_line_text(line))
    if ordinal is None:
        return None
    if not (_ORDINAL_MIN <= ordinal <= _ORDINAL_MAX):
        return None
    return ordinal


def _assemble_question(
    qnum: int, lines: list[list[Word]], page: int
) -> ExtractedQuestion | None:
    all_words = [w for line in lines for w in line]
    if not all_words:
        return None

    first_line_text = strip_ordinal(_line_text(lines[0]))
    rest = [_line_text(line) for line in lines[1:] if line]
    question_text = '\n'.join(
        _WS_RE.sub(' ', part).strip() for part in [first_line_text] + rest
        if part.strip()
    ).strip()

    if not question_text:
        return None

    x_min = min(w.bbox[0] for w in all_words)
    y_min = min(w.bbox[1] for w in all_words)
    x_max = max(w.bbox[2] for w in all_words)
    y_max = max(w.bbox[3] for w in all_words)
    region = Region(page=page, bbox=(x_min, y_min, x_max, y_max))

    confs = [w.confidence for w in all_words if w.confidence >= 0]
    ocr_p50 = statistics.median(confs) if confs else 0.0

    return ExtractedQuestion(
        question_number=qnum,
        question_text=question_text,
        regions=[region],
        confidence_by_field={"ocr_p50": ocr_p50, "segmentation": 1.0},
    )


def _segment_lines(
    lines: list[list[Word]],
    col_start: float,
    col_end: float,
    page: int,
) -> list[ExtractedQuestion]:
    questions: list[ExtractedQuestion] = []
    current_qnum: int | None = None
    current_lines: list[list[Word]] = []

    for line in lines:
        ordinal = _is_anchor(line, col_start, col_end)
        if ordinal is not None:
            if current_qnum is not None and current_lines:
                q = _assemble_question(current_qnum, current_lines, page)
                if q is not None:
                    questions.append(q)
            current_qnum = ordinal
            current_lines = [line]
        elif current_qnum is not None:
            current_lines.append(line)

    if current_qnum is not None and current_lines:
        q = _assemble_question(current_qnum, current_lines, page)
        if q is not None:
            questions.append(q)

    return questions


# ---------------------------------------------------------------------------
# Legacy helpers — retained for direct test coverage
# ---------------------------------------------------------------------------

def cluster_by_vertical_gap(
    words: list[Word],
    gap_factor: float = 1.2,
) -> list[list[Word]]:
    """Cluster vertically adjacent words into line-blocks.

    Gap threshold = gap_factor × median(word height).
    """
    if not words:
        return []

    sorted_words = sorted(words, key=lambda w: (w.bbox[1], w.bbox[0]))

    heights = [w.bbox[3] - w.bbox[1] for w in sorted_words if w.bbox[3] > w.bbox[1]]
    if not heights:
        return [sorted_words]

    median_height = statistics.median(heights)
    threshold = gap_factor * median_height

    blocks: list[list[Word]] = []
    current_block: list[Word] = [sorted_words[0]]
    prev_bottom = sorted_words[0].bbox[3]

    for word in sorted_words[1:]:
        gap = word.bbox[1] - prev_bottom
        if gap > threshold:
            blocks.append(current_block)
            current_block = []
        current_block.append(word)
        prev_bottom = max(prev_bottom, word.bbox[3])

    if current_block:
        blocks.append(current_block)

    return blocks


def block_to_question(block: list[Word]) -> ExtractedQuestion | None:
    """Convert a word-block to an ExtractedQuestion, or None if not a question."""
    if not block:
        return None

    joined = _join_block_text(block)
    ordinal = detect_ordinal(joined)
    if ordinal is None:
        return None
    if not (_ORDINAL_MIN <= ordinal <= _ORDINAL_MAX):
        return None

    question_text = strip_ordinal(joined)
    question_text = '\n'.join(
        _WS_RE.sub(' ', line).strip()
        for line in question_text.split('\n')
    ).strip()

    if not question_text:
        return None

    bbox = _block_bbox(block)
    page = block[0].page
    region = Region(page=page, bbox=bbox)

    confidences = [w.confidence for w in block if w.confidence >= 0]
    ocr_p50 = statistics.median(confidences) if confidences else 0.0

    return ExtractedQuestion(
        question_number=ordinal,
        question_text=question_text,
        regions=[region],
        confidence_by_field={"ocr_p50": ocr_p50, "segmentation": 1.0},
    )


def _join_block_text(block: list[Word]) -> str:
    if not block:
        return ""

    sorted_words = sorted(block, key=lambda w: (w.bbox[1], w.bbox[0]))
    heights = [w.bbox[3] - w.bbox[1] for w in sorted_words if w.bbox[3] > w.bbox[1]]
    median_h = statistics.median(heights) if heights else 0.02
    line_threshold = 0.6 * median_h

    lines: list[list[str]] = [[sorted_words[0].text]]
    prev_bottom = sorted_words[0].bbox[3]

    for word in sorted_words[1:]:
        if word.bbox[1] > prev_bottom - line_threshold:
            lines.append([])
        lines[-1].append(word.text)
        prev_bottom = max(prev_bottom, word.bbox[3])

    return '\n'.join(' '.join(line) for line in lines if line)


def _block_bbox(block: list[Word]) -> tuple[float, float, float, float]:
    x_min = min(w.bbox[0] for w in block)
    y_min = min(w.bbox[1] for w in block)
    x_max = max(w.bbox[2] for w in block)
    y_max = max(w.bbox[3] for w in block)
    return (x_min, y_min, x_max, y_max)
