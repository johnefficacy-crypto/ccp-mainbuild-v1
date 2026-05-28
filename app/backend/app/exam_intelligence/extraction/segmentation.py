"""Vertical clustering and question-block emission.

Algorithm:
1. Detect columns via x-histogram bimodality.
2. Assign words to columns.
3. Within each column, cluster vertically adjacent words into blocks using
   a gap threshold derived from the median line height.
4. Emit ExtractedQuestion for blocks whose joined text starts with a
   printed ordinal in [1, 200].
"""
from __future__ import annotations

import re
import statistics

from .layout import assign_words_to_columns, detect_columns
from .ordinal import detect_ordinal, strip_ordinal
from .types import ExtractedQuestion, Region, Word

# Ordinals outside this range are rejected as OCR noise.
_ORDINAL_MIN = 1
_ORDINAL_MAX = 200

_WS_RE = re.compile(r'[ \t]+')


def cluster_by_vertical_gap(
    words: list[Word],
    gap_factor: float = 1.5,
) -> list[list[Word]]:
    """Cluster vertically adjacent words into line-blocks.

    Gap threshold = gap_factor × median(word height) for the set of words.
    A new block starts whenever the vertical gap between consecutive words
    (sorted by y_min) exceeds the threshold.
    """
    if not words:
        return []

    # Words are assumed to already be sorted by (y_min, x_min).
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
    """Convert a word-block to an ExtractedQuestion, or None if not a question.

    Steps:
    1. Join word texts (single space between words on the same line,
       newline between lines based on vertical gap).
    2. Detect leading ordinal. Discard if absent or outside [1, 200].
    3. Strip ordinal and normalize internal whitespace.
    4. Build a single bounding Region from the block extent.
    5. Confidence = median OCR confidence across block words.
    """
    if not block:
        return None

    joined = _join_block_text(block)
    ordinal = detect_ordinal(joined)
    if ordinal is None:
        return None
    if not (_ORDINAL_MIN <= ordinal <= _ORDINAL_MAX):
        return None

    question_text = strip_ordinal(joined)
    # Normalize runs of spaces/tabs to single space (preserve newlines).
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


def segment_page(words: list[Word], page: int) -> list[ExtractedQuestion]:
    """Full per-page segmentation: column detection → clustering → question emit."""
    if not words:
        return []

    columns = detect_columns(words)
    col_words = assign_words_to_columns(words, columns)

    questions: list[ExtractedQuestion] = []
    for col_idx in sorted(col_words.keys()):
        col = col_words[col_idx]
        if not col:
            continue
        blocks = cluster_by_vertical_gap(col)
        for block in blocks:
            q = block_to_question(block)
            if q is not None:
                questions.append(q)

    return questions


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _join_block_text(block: list[Word]) -> str:
    """Join words within a block, inserting newlines at large vertical jumps."""
    if not block:
        return ""

    sorted_words = sorted(block, key=lambda w: (w.bbox[1], w.bbox[0]))
    heights = [w.bbox[3] - w.bbox[1] for w in sorted_words if w.bbox[3] > w.bbox[1]]
    median_h = statistics.median(heights) if heights else 0.02
    line_threshold = 0.6 * median_h  # smaller gap = same line

    lines: list[list[str]] = [[sorted_words[0].text]]
    prev_bottom = sorted_words[0].bbox[3]
    prev_top = sorted_words[0].bbox[1]

    for word in sorted_words[1:]:
        # New line if word's top is below previous word's bottom - threshold
        if word.bbox[1] > prev_bottom - line_threshold:
            lines.append([])
        lines[-1].append(word.text)
        prev_bottom = max(prev_bottom, word.bbox[3])

    return '\n'.join(' '.join(line) for line in lines if line)


def _block_bbox(block: list[Word]) -> tuple[float, float, float, float]:
    """Compute the bounding box of all words in a block."""
    x_min = min(w.bbox[0] for w in block)
    y_min = min(w.bbox[1] for w in block)
    x_max = max(w.bbox[2] for w in block)
    y_max = max(w.bbox[3] for w in block)
    return (x_min, y_min, x_max, y_max)
