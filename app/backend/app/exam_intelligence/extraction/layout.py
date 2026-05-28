"""Column detection via x-histogram bimodality analysis.

The v1 corpus uses a two-column layout with a gutter near x ≈ 0.5 (normalized).
Page width varies across papers, so the split point must be detected per-page
via histogram analysis rather than hardcoded.
"""
from __future__ import annotations

import numpy as np

from .types import Word


def detect_columns(
    words: list[Word], n_bins: int = 40
) -> list[tuple[float, float]]:
    """Build an x-histogram and detect column intervals.

    Returns a list of (x_start, x_end) intervals in normalized [0, 1] coords.
    For empty pages or single-column pages, returns [(0.0, 1.0)].
    """
    if not words:
        return [(0.0, 1.0)]

    # Use the centroid x of each word (not just left edge) for robustness.
    x_centers = np.array([(w.bbox[0] + w.bbox[2]) / 2.0 for w in words])

    counts, bin_edges = np.histogram(x_centers, bins=n_bins, range=(0.0, 1.0))
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2.0

    # Find the two highest peaks and the valley between them.
    # Simple approach: find global max in each half, then check valley depth.
    mid = n_bins // 2
    left_counts = counts[:mid]
    right_counts = counts[mid:]

    if len(left_counts) == 0 or len(right_counts) == 0:
        return [(0.0, 1.0)]

    left_peak_idx = int(np.argmax(left_counts))
    right_peak_idx = mid + int(np.argmax(right_counts))

    left_peak_val = counts[left_peak_idx]
    right_peak_val = counts[right_peak_idx]

    # Require both peaks to have meaningful density (> 5% of the higher peak).
    min_peak_height = 0.05 * max(left_peak_val, right_peak_val)
    if left_peak_val < min_peak_height or right_peak_val < min_peak_height:
        return [(0.0, 1.0)]

    # Valley = minimum between the two peaks.
    valley_slice = counts[left_peak_idx + 1: right_peak_idx]
    if len(valley_slice) == 0:
        # Peaks are adjacent — no clear gutter.
        return [(0.0, 1.0)]

    valley_min = int(np.min(valley_slice))

    # Bimodal: valley must be significantly lower than both peaks.
    # Threshold: valley ≤ 50% of the smaller peak.
    if valley_min > 0.5 * min(left_peak_val, right_peak_val):
        return [(0.0, 1.0)]

    # Split at the midpoint of all minimum-count bins in the valley.
    # This avoids picking the leftmost zero (which may be too close to
    # the left cluster) and instead centres the split in the gutter.
    min_bin_indices = [
        left_peak_idx + 1 + i
        for i, v in enumerate(valley_slice)
        if v == valley_min
    ]
    mid_bin = min_bin_indices[len(min_bin_indices) // 2]
    split = float(bin_centers[mid_bin])
    return [(0.0, split), (split, 1.0)]


def assign_words_to_columns(
    words: list[Word],
    columns: list[tuple[float, float]],
) -> dict[int, list[Word]]:
    """Assign words to columns, sorted by y_min ASC within each column.

    A word is assigned to the column whose interval contains the word's
    centroid x. Words that fall outside all columns go to the closest one.
    """
    result: dict[int, list[Word]] = {i: [] for i in range(len(columns))}

    for word in words:
        cx = (word.bbox[0] + word.bbox[2]) / 2.0
        assigned = _find_column(cx, columns)
        result[assigned].append(word)

    for col_idx in result:
        result[col_idx].sort(key=lambda w: (w.bbox[1], w.bbox[0]))

    return result


def _find_column(cx: float, columns: list[tuple[float, float]]) -> int:
    """Return the column index whose interval contains cx, or the closest."""
    for i, (start, end) in enumerate(columns):
        if start <= cx < end:
            return i
    # Fall back to closest column by midpoint distance.
    best = 0
    best_dist = float("inf")
    for i, (start, end) in enumerate(columns):
        mid = (start + end) / 2.0
        dist = abs(cx - mid)
        if dist < best_dist:
            best_dist = dist
            best = i
    return best
