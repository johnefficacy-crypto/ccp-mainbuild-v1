"""Make ``exam_priority_score`` comparable across ``source_basis``.

THE DEFECT THIS EXISTS FOR
--------------------------
``exam_topic_coverage.exam_priority_score`` holds values produced by two
different processes on two different scales, and nothing consulted a marker at
read time. Live on 2026-09-12:

===========  ==================  ======  =====  =====  =====
phase        source_basis          rows    min    avg    max
===========  ==================  ======  =====  =====  =====
mains        evidence_derived     1,497   0.00   6.42  36.10
prelims      official_syllabus       13  60.00  82.31  95.00
tier-1       hybrid                   2  78.00  83.00  88.00
tier-1       pyq_analysis             3  70.00  78.33  85.00
tier-1       official_syllabus        2  55.00  58.50  62.00
===========  ==================  ======  =====  =====  =====

**The Mains maximum is below the Prelims minimum** — not usually lower,
structurally lower. ``evidence_derived`` rows come from the v2.0 cohort model,
which normalises a topic's question count against its own paper's cohort; with
1,252 topics sharing 8,302 questions no topic can own a large share. The other
twenty rows are a human typing a 0-100 importance judgement. So a derived row
could never outrank an authored one, whatever the evidence said.

WHAT THIS DOES, AND WHAT IT DOES NOT
------------------------------------
Neither score is recomputed or rewritten — the v2.0 model's output is locked
and published, and the authored rows are somebody's deliberate judgement. This
converts each row to its **mid-rank percentile within its own source_basis**,
so rows are compared by standing among their own kind and the best of each
basis competes on equal terms.

Rescaling derived scores onto 0-100 instead was rejected: a cohort share of
0.30 is not the claim "importance 30", and presenting it as one would make the
number unreadable rather than comparable.

A set that spans only ONE ``source_basis`` is left exactly as it is — the
comparable value is the raw score, unchanged. There is nothing to reconcile in
a single-unit set, and percentile-ranking it anyway would silently respace a
ranking that was already correct: rank order survives, but the GAPS between
rows do not, and every consumer here blends the score with other terms rather
than sorting on it alone. So a single-phase exam, and every consumer scoped to
one basis, behaves bit-for-bit as before.

Percentile is set-relative by construction. Callers that compare two row sets
(before/after) must attach over a single shared reference set, or the delta
picks up movement that is only a change of denominator.
"""
from __future__ import annotations

from typing import Any, Iterable

#: The `source_basis` written by `coverage_derivation.py` for rows the v2.0
#: model produced. Every other value is a human-authored judgement.
EVIDENCE_DERIVED_BASIS = "evidence_derived"

#: Key the comparable value is attached under. Deliberately NOT
#: `exam_priority_score`: the raw column keeps its meaning, and a reader can
#: always see which of the two they are looking at.
COMPARABLE_KEY = "comparable_priority"

#: A row with no basis recorded is its own group rather than being folded in
#: with derived rows — guessing would silently mis-rank it.
_UNKNOWN_BASIS = "__unknown__"


def _score(row: dict[str, Any], score_key: str) -> float:
    try:
        return float(row.get(score_key) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def comparable_priorities(
    rows: Iterable[dict[str, Any]],
    *,
    score_key: str = "exam_priority_score",
    basis_key: str = "source_basis",
) -> list[float]:
    """Mid-rank percentile (0-100) of each row within its own ``source_basis``.

    Mid-rank, so tied rows share a value and no row is pinned to exactly 0 or
    100 by an accident of group size. A basis with one row scores 50 — a
    neutral standing, which is the only honest answer when there is nothing to
    rank against.

    Returns a list positionally aligned with *rows*; the input is not mutated.
    """
    items = list(rows)
    groups: dict[str, list[float]] = {}
    for r in items:
        basis = r.get(basis_key) or _UNKNOWN_BASIS
        groups.setdefault(basis, []).append(_score(r, score_key))

    # Single unit system → nothing to reconcile. Hand back the raw scores so a
    # single-basis consumer is untouched, gaps and all.
    if len(groups) < 2:
        return [_score(r, score_key) for r in items]

    out: list[float] = []
    for r in items:
        basis = r.get(basis_key) or _UNKNOWN_BASIS
        peers = groups[basis]
        value = _score(r, score_key)
        n = len(peers)
        below = sum(1 for p in peers if p < value)
        tied = sum(1 for p in peers if p == value)
        out.append(round(100.0 * (below + 0.5 * tied) / n, 4))
    return out


def attach_comparable_priority(
    rows: list[dict[str, Any]],
    *,
    score_key: str = "exam_priority_score",
    basis_key: str = "source_basis",
    out_key: str = COMPARABLE_KEY,
    reference: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Attach :data:`COMPARABLE_KEY` to every row, in place, and return them.

    Pass *reference* when two sets must stay comparable with each other (a
    before/after impact diff): percentiles are then computed over the reference
    and looked up per row, so a row's standing does not move just because the
    set it was measured in changed size.
    """
    if reference is None:
        for row, value in zip(rows, comparable_priorities(
            rows, score_key=score_key, basis_key=basis_key
        )):
            row[out_key] = value
        return rows

    # The reference decides whether normalisation applies at all, so a
    # before/after pair stays on one footing even if one side happens to be
    # single-basis on its own.
    ref_values = comparable_priorities(
        reference, score_key=score_key, basis_key=basis_key
    )
    lookup: dict[tuple[str, float], float] = {}
    for ref_row, value in zip(reference, ref_values):
        lookup[(ref_row.get(basis_key) or _UNKNOWN_BASIS, _score(ref_row, score_key))] = value

    for row in rows:
        key = (row.get(basis_key) or _UNKNOWN_BASIS, _score(row, score_key))
        # A row absent from the reference (a proposed change not yet in it)
        # falls back to its standing inside the set it arrived with.
        row[out_key] = lookup.get(key)
    missing = [r for r in rows if r.get(out_key) is None]
    if missing:
        for row, value in zip(missing, comparable_priorities(
            missing, score_key=score_key, basis_key=basis_key
        )):
            row[out_key] = value
    return rows
