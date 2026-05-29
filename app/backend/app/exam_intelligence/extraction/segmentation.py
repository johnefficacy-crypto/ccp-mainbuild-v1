from __future__ import annotations
import re
from .types import Word, ExtractedQuestion, Region

_ORDINAL_RE = re.compile(r"^(\d{1,3})\.")


def reconstruct_lines(words: list[Word]) -> list[list[Word]]:
    """Group words into lines by y-proximity."""
    if not words:
        return []
    sorted_words = sorted(words, key=lambda w: (round(w.bbox[1] * 200), w.bbox[0]))
    lines: list[list[Word]] = []
    current: list[Word] = [sorted_words[0]]
    for w in sorted_words[1:]:
        prev_cy = (current[-1].bbox[1] + current[-1].bbox[3]) / 2.0
        this_cy = (w.bbox[1] + w.bbox[3]) / 2.0
        if abs(this_cy - prev_cy) < 0.015:
            current.append(w)
        else:
            lines.append(current)
            current = [w]
    lines.append(current)
    return lines


def segment_column(
    lines: list[list[Word]],
    effective_left: float,
    last_accepted_ordinal: int,
    page: int,
) -> tuple[list[ExtractedQuestion], int]:
    """Segment lines into questions by detecting ordinal anchors."""
    questions: list[ExtractedQuestion] = []
    current_lines: list[list[Word]] = []
    current_ordinal: int | None = None

    ANCHOR_TOLERANCE = 0.04

    def _flush():
        nonlocal current_ordinal
        if current_ordinal is None or not current_lines:
            return
        all_words = [w for line in current_lines for w in line]
        text = " ".join(w.text for w in all_words)
        x_min = min(w.bbox[0] for w in all_words)
        y_min = min(w.bbox[1] for w in all_words)
        x_max = max(w.bbox[2] for w in all_words)
        y_max = max(w.bbox[3] for w in all_words)
        questions.append(ExtractedQuestion(
            question_number=current_ordinal,
            question_text=text,
            regions=[Region(page=page, bbox=(x_min, y_min, x_max, y_max))],
        ))

    for line in lines:
        if not line:
            continue
        first_word = line[0]
        m = _ORDINAL_RE.match(first_word.text)
        if m and abs(first_word.bbox[0] - effective_left) <= ANCHOR_TOLERANCE:
            num = int(m.group(1))
            if num > last_accepted_ordinal:
                _flush()
                current_lines = [line]
                current_ordinal = num
                last_accepted_ordinal = num
                continue
        if current_ordinal is not None:
            current_lines.append(line)

    _flush()
    return questions, last_accepted_ordinal
