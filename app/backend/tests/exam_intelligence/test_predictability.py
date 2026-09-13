"""PRED-01 — the predictability measure and its bands.

Pinned against `workbench/analysis/predictability.json`, the sandbox run over
1,016 topics that produced the design's figures. The sandbox script itself
(`workbench/analysis/predict.py`) reads local CSVs and is not importable here,
so its OUTPUT is the fixture and `app.exam_intelligence.predictability` is the
implementation under test.
"""
from __future__ import annotations

import json
import os
from collections import Counter

import pytest

from app.exam_intelligence.predictability import band_for, measure, score_paper

_FIXTURE = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..",
    "workbench", "analysis", "predictability.json",
)


def _fixture() -> dict:
    with open(os.path.abspath(_FIXTURE), encoding="utf-8") as fh:
        return json.load(fh)


# ── 1. Five topics spanning the bands, pinned exactly ────────────────────────
# Chosen from the fixture: one per band plus a second near_certain from a
# different paper, so the per-paper span is exercised too.
@pytest.mark.parametrize(
    "paper,topic,span,expect_p,expect_band",
    [
        # socio_p1: 43 topics, almost everything recurs — the paper that proved
        # percentiles alone mislabel a tight syllabus.
        ("socio_p1", "Protest, agitation, social movements, collective action, "
                     "social change", (1981, 2025), 0.731, "near_certain"),
        # hist_p1: 127 topics over ~660 questions — the paper that proved an
        # absolute breadth cut cannot work across papers. Its near_certain
        # topic scores 0.493, well below socio_p1's 0.731, which is precisely
        # why the bands are per-paper percentiles.
        ("hist_p1", "Hunting and gathering: Palaeolithic and Mesolithic cultures",
         (1985, 2025), 0.493, "near_certain"),
        ("psir_p1", "Marx", (1991, 2026), 0.427, "likely"),
        ("geog_p2", "Environmental degradation; deforestation, desertification",
         (1986, 2025), 0.322, "occasional"),
        ("anth_p1", "Secondary sources and participatory methods",
         (1981, 2025), 0.26, "rare"),
    ],
)
def test_five_topics_across_the_bands_match_the_reference(
    paper, topic, span, expect_p, expect_band
):
    fx = _fixture()[paper]
    lo, hi = span
    assert fx["span"] == f"{lo}-{hi}"

    # Exact match first: a short name like "Marx" is a prefix of longer topics
    # in the same paper ("Marxist approach…"), which sit in a different band.
    ref = next((t for t in fx["topics"] if t["topic"] == topic), None) or next(
        (t for t in fx["topics"] if t["topic"].startswith(topic[:40])), None
    )
    assert ref is not None, f"{topic!r} not in {paper}"
    assert ref["band"] == expect_band
    assert ref["p"] == expect_p

    got = measure(ref["years"], lo, hi)
    assert round(got["predictability"], 3) == expect_p
    assert round(got["breadth"], 3) == ref["breadth"]
    assert round(got["regularity"], 3) == ref["regularity"]
    assert round(got["recency"], 3) == ref["recency"]

    # And the band the implementation assigns matches, scored in its own paper.
    banded = score_paper({t["topic"]: t["years"] for t in fx["topics"]})
    assert banded[ref["topic"]]["predictability_band"] == expect_band


def test_every_topic_in_the_fixture_reproduces_exactly():
    """All 1,016 topics, all four components. The measure is the contract; a
    drift anywhere in it changes a published band."""
    checked = 0
    for key, paper in _fixture().items():
        lo, hi = (int(x) for x in paper["span"].split("-"))
        for t in paper["topics"]:
            got = measure(t["years"], lo, hi)
            assert round(got["predictability"], 3) == t["p"], (key, t["topic"])
            assert round(got["breadth"], 3) == t["breadth"], (key, t["topic"])
            assert round(got["regularity"], 3) == t["regularity"], (key, t["topic"])
            assert round(got["recency"], 3) == t["recency"], (key, t["topic"])
            checked += 1
    assert checked == 1016


def test_band_distribution_per_paper_matches_the_reference():
    """Tie-break differs from the sandbox — it ranked ties in JSON input order,
    which a database read cannot reproduce, so this implementation breaks ties
    by topic id. The COUNTS are unaffected: the same topics are ranked, only
    which of two equal-scoring topics sits either side of a percentile boundary
    can differ."""
    for key, paper in _fixture().items():
        got = score_paper({t["topic"]: t["years"] for t in paper["topics"]})
        assert Counter(g["predictability_band"] for g in got.values()) == Counter(
            t["band"] for t in paper["topics"]
        ), key


# ── 2. The absolute floor promotes and never demotes ─────────────────────────
def test_floor_promotes_a_recurring_topic_out_of_rare():
    """Sociology Paper-I's bottom quartile contained a topic asked in 12
    separate years. Calling that 'rare' would be plainly wrong."""
    assert band_for(0.99, breadth=0.30) == "occasional"  # would be 'rare'
    assert band_for(0.80, breadth=0.45) == "likely"      # 'rare' -> 'occasional' -> 'likely'


def test_floor_never_demotes():
    """A sprawling paper like History must keep its honest tail of genuinely
    rare topics, so a low breadth may never pull a top-percentile topic down."""
    for pct, band in ((0.00, "near_certain"), (0.20, "likely"), (0.50, "occasional")):
        for breadth in (0.0, 0.01, 0.11, 0.39):
            assert band_for(pct, breadth) == band, (pct, breadth)


def test_floor_thresholds_are_the_documented_ones():
    assert band_for(0.99, 0.119) == "rare"
    assert band_for(0.99, 0.12) == "occasional"
    assert band_for(0.50, 0.399) == "occasional"
    assert band_for(0.50, 0.40) == "likely"


# ── 3. Same breadth, different spacing → different regularity ────────────────
def test_identical_year_counts_with_different_spacing_can_land_in_different_bands():
    """Regularity carries information breadth does not: a topic asked every
    third year without fail is a different preparation object from one asked
    the same number of times in bursts."""
    span = (1990, 2019)  # Y = 30
    metronomic = [1990 + 3 * i for i in range(10)]      # every 3 years
    bursty = [1990, 1991, 1992, 1993, 1994, 2015, 2016, 2017, 2018, 2019]

    a = measure(metronomic, *span)
    b = measure(bursty, *span)

    assert a["breadth"] == b["breadth"]          # same 10 years out of 30
    assert a["regularity"] > b["regularity"]
    assert a["predictability"] > b["predictability"]

    # And that difference is enough to separate them into different bands in a
    # paper whose remaining topics sit between the two.
    filler = {f"f{i}": [1990 + i, 1995 + i, 2001 + i] for i in range(18)}
    banded = score_paper({"metronomic": metronomic, "bursty": bursty, **filler})
    assert banded["metronomic"]["predictability_band"] == "near_certain"
    assert banded["bursty"]["predictability_band"] != "near_certain"
    assert (
        banded["metronomic"]["rank_percentile"] < banded["bursty"]["rank_percentile"]
    )


def test_fewer_than_three_years_has_zero_regularity():
    """A topic asked twice is not predictable regardless of spacing, so
    regularity is 0 and breadth carries it."""
    assert measure([1990, 2020], 1990, 2020)["regularity"] == 0.0
    assert measure([1990], 1990, 2020)["regularity"] == 0.0
    assert measure([1990, 2000, 2010], 1990, 2020)["regularity"] > 0.0


# ── 4. Y is per subject-paper ────────────────────────────────────────────────
def test_span_is_per_paper_not_global():
    """Geography's corpus starts 1986 and History's 1985. Scoring both against
    a global 1980-2026 span would understate every Geography topic's breadth by
    roughly a tenth."""
    years = [1990, 1995, 2000, 2005, 2010]

    narrow = score_paper({"t": years, "other": [1986, 2025]})   # span 1986-2025, Y=40
    wide = score_paper({"t": years, "other": [1980, 2026]})     # span 1980-2026, Y=47

    assert narrow["t"]["span_years"] == 40
    assert wide["t"]["span_years"] == 47
    assert narrow["t"]["breadth"] > wide["t"]["breadth"]
    assert narrow["t"]["breadth"] == pytest.approx(5 / 40)
    assert wide["t"]["breadth"] == pytest.approx(5 / 47)


def test_two_papers_are_scored_against_their_own_spans():
    """The same year list means more in the paper with the shorter evidence
    span, and the span comes from each paper's own topics.

    Breadth is the term the span drives, so it is what this asserts. The total
    score also carries recency, which is bucketed against the span's final
    third and can move the other way — a real effect, not an anomaly, and the
    reason the comparison here is on breadth rather than on `predictability`.
    """
    geog = score_paper({"g1": [1990, 2000, 2010], "g2": [1986, 2025]})
    socio = score_paper({"s1": [1990, 2000, 2010], "s2": [1980, 2025]})
    assert geog["g1"]["span_years"] == 40
    assert socio["s1"]["span_years"] == 46
    assert geog["g1"]["breadth"] > socio["s1"]["breadth"]
    assert geog["g1"]["breadth"] == pytest.approx(3 / 40)
    assert socio["s1"]["breadth"] == pytest.approx(3 / 46)


# ── 5. Distinct years, not question counts (G3) ──────────────────────────────
def test_repeated_years_count_once():
    """Thematic rows are one per theme-year and year-wise rows one per
    question, so the same topic can arrive twice for one year. Counting rows
    would make the two corpus halves incomparable."""
    once = measure([1990, 1995, 2000], 1990, 2020)
    twice = measure([1990, 1990, 1995, 1995, 1995, 2000], 1990, 2020)
    assert once == twice


def test_an_empty_paper_scores_nothing_rather_than_dividing_by_zero():
    assert score_paper({}) == {}
    assert score_paper({"t": []}) == {}
