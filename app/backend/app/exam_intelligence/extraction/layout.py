from __future__ import annotations
import numpy as np
from .types import Word


def detect_columns(words: list[Word]) -> list[tuple[float, float]]:
    """Detect column boundaries via histogram valley detection."""
    if not words:
        return [(0.0, 1.0)]
    x_centers = np.array([(w.bbox[0] + w.bbox[2]) / 2.0 for w in words])
    counts, edges = np.histogram(x_centers, bins=50, range=(0.0, 1.0))
    centers = (edges[:-1] + edges[1:]) / 2.0
    valley = int(np.argmin(counts))
    split = float(centers[valley])
    if split <= 0.1 or split >= 0.9:
        return [(0.0, 1.0)]
    return [(0.0, split), (split, 1.0)]


def assign_words_to_columns(
    words: list[Word],
    columns: list[tuple[float, float]],
) -> dict[int, list[Word]]:
    """Assign each word to a column by centroid x."""
    result: dict[int, list[Word]] = {i: [] for i in range(len(columns))}
    for w in words:
        cx = (w.bbox[0] + w.bbox[2]) / 2.0
        for i, (lo, hi) in enumerate(columns):
            if lo <= cx < hi:
                result[i].append(w)
                break
        else:
            result[len(columns) - 1].append(w)
    return result
