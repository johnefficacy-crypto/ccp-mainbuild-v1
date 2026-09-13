"""Predictability — a difficulty axis that works for descriptive papers.

``pyq_questions.observed_difficulty`` is null on all 8,188 verified Mains
descriptive questions, deliberately: difficulty is judgeable for an MCQ
(distractors, elimination steps, obscurity of the traced fact) and meaningless
for "Discuss the impact of globalisation on informal sector workers", which
has no answer key. See ``docs/status/2026-09-12-predictability-axis-design.md``.

What *is* measurable for a descriptive paper is how reliably a topic recurs. A
theme asked in 1991, 1998, 2007, 2015 and 2023 must be prepared; one asked once
in 2019 need not be.

This module is the arithmetic only — pure functions over year lists, no
database. ``score_snapshots.py`` supplies the years and writes the result.

What predictability is NOT: not importance (a rarely-asked topic may be
foundational), not difficulty (a topic asked every year may be hard), and not a
forecast — it says how a topic has behaved, not what UPSC will do next. The
band names avoid "will appear" wording for exactly that reason.
"""
from __future__ import annotations

import statistics
from typing import Any, Iterable

#: Weights follow the measured distribution, not intuition. Breadth dominates
#: because it is what the corpus actually separates on: a fifth of topics
#: appeared once in thirty-one years and a fifth appeared eight times or more.
#: Recency is small on purpose — of 176 topics asked 6+ times, only 3 ever
#: stopped being asked, so a decay term is a guard against a rare case, not a
#: driver.
_W_BREADTH = 0.65
_W_REGULARITY = 0.25
_W_RECENCY = 0.10

#: A coefficient of variation at or above this is "as erratic as we score";
#: everything above collapses to regularity 0.
_CV_CEILING = 1.5

#: Fewer than three asks gives fewer than two gaps, and a CV over one gap is
#: meaningless. Regularity is 0 there and breadth carries the topic, which is
#: correct: a topic asked twice is not predictable regardless of spacing.
_MIN_YEARS_FOR_REGULARITY = 3

BANDS = ("near_certain", "likely", "occasional", "rare")

#: Percentile cuts within a subject-paper, applied to topics ranked by score.
_PCT_NEAR_CERTAIN = 0.10
_PCT_LIKELY = 0.35
_PCT_OCCASIONAL = 0.75

#: Absolute floors. These only ever promote — see ``band_for``.
_FLOOR_OCCASIONAL_BREADTH = 0.12
_FLOOR_LIKELY_BREADTH = 0.40


def measure(
    years: Iterable[int], span_lo: int, span_hi: int
) -> dict[str, float]:
    """Score one topic's recurrence over its subject-paper's span.

    *years* is the set of DISTINCT years the topic was asked in — not a
    question count. A paper can ask two questions on one topic in a year and
    that is not two data points. It also makes the measure robust to the
    corpus's two halves counting differently: thematic rows are one per
    theme-year, year-wise rows are one per question.

    *span_lo* / *span_hi* bound the years where the topic's own subject-paper
    has evidence. Not a global 1980-2026 constant: Geography's corpus starts
    1986 and History's 1985, so a global span would understate every Geography
    topic's breadth by a tenth.
    """
    ys = sorted({int(y) for y in years})
    span = max(int(span_hi) - int(span_lo) + 1, 1)

    breadth = len(ys) / span

    if len(ys) >= _MIN_YEARS_FOR_REGULARITY:
        gaps = [b - a for a, b in zip(ys, ys[1:])]
        mean_gap = statistics.mean(gaps)
        cv = statistics.pstdev(gaps) / (mean_gap or 1)
        regularity = 1 - min(cv, _CV_CEILING) / _CV_CEILING
    else:
        regularity = 0.0

    third = span / 3
    last = max(ys) if ys else span_lo
    if last >= span_hi - third:
        recency = 1.0
    elif last >= span_hi - 2 * third:
        recency = 0.5
    else:
        recency = 0.2

    score = _W_BREADTH * breadth + _W_REGULARITY * regularity + _W_RECENCY * recency
    return {
        "predictability": score,
        "breadth": breadth,
        "regularity": regularity,
        "recency": recency,
        "years_asked": len(ys),
        "span_years": span,
    }


def band_for(percentile: float, breadth: float) -> str:
    """Band one topic from its rank within its subject-paper, then floor it up.

    Percentile FIRST, because absolute cuts alone cannot work across papers: a
    flat ``breadth >= 0.35`` cut gave Geography and History zero near-certain
    topics and PubAd sixteen, since History Paper-I spreads ~660 questions over
    127 topics and cannot reach 35% breadth by construction. Same lesson the
    v2.0 ``exam_priority_score`` model learned about cohort normalisation.

    Absolute floors SECOND, because percentiles alone mislabel a tight
    syllabus: Sociology Paper-I has 43 topics and almost everything recurs, so
    its bottom quartile still contained a topic asked in 12 separate years —
    "rare" would be plainly wrong in a user-facing band.

    The floors only ever promote. A sprawling paper like History therefore
    keeps its honest tail of genuinely rare topics.
    """
    if percentile < _PCT_NEAR_CERTAIN:
        band = "near_certain"
    elif percentile < _PCT_LIKELY:
        band = "likely"
    elif percentile < _PCT_OCCASIONAL:
        band = "occasional"
    else:
        band = "rare"

    if band == "rare" and breadth >= _FLOOR_OCCASIONAL_BREADTH:
        band = "occasional"
    if band == "occasional" and breadth >= _FLOOR_LIKELY_BREADTH:
        band = "likely"
    return band


def score_paper(topic_years: dict[str, list[int]]) -> dict[str, dict[str, Any]]:
    """Measure and band every topic of ONE subject-paper.

    The span is derived from the supplied topics themselves — the years where
    this paper actually has evidence — so callers must pass one paper's topics
    at a time. Returns ``{topic_id: {predictability, predictability_band, ...}}``.

    Ranking is by score descending; ties are broken by ``topic_id`` so the band
    a topic lands in does not depend on dictionary iteration order. (The
    sandbox script this mirrors, ``workbench/analysis/predict.py``, left ties
    in input order, which is not reproducible from a database read.)
    """
    all_years = [y for ys in topic_years.values() for y in ys]
    if not all_years:
        return {}
    lo, hi = min(all_years), max(all_years)

    measured = {tid: measure(ys, lo, hi) for tid, ys in topic_years.items()}
    ranked = sorted(
        measured.items(), key=lambda kv: (-kv[1]["predictability"], kv[0])
    )

    n = len(ranked)
    out: dict[str, dict[str, Any]] = {}
    for i, (tid, m) in enumerate(ranked):
        band = band_for(i / n, m["breadth"])
        out[tid] = {
            **m,
            "predictability_band": band,
            "span_lo": lo,
            "span_hi": hi,
            "rank_percentile": i / n,
        }
    return out
