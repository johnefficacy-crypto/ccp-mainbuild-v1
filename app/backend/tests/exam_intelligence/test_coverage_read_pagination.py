"""Coverage reads must be ordered, complete, and never silently partial.

Two defects, both silent, both live during the 2026-09-12 publication run:

1. **Unordered range paging.** `coverage.py` and `coverage_derivation.py`
   each range-paginated with no `.order(...)`. Range paging without a total
   order is undefined in Postgres — every window is a separate query, so rows
   repeat across pages while others never appear. In `verified_pyq_topic_counts`
   that lands on a topic's PYQ frequency: not a missing row a caller can
   notice, a plausible-looking wrong number.

2. **Bare `.limit(N)` reads above the server cap.** `locked_topic_coverage_summary`
   asked for `.limit(1000)` — exactly `db-max-rows` — and `locked_topic_coverage`
   for `.limit(2000)`, which PostgREST serves as 1 000. Both truncated the
   moment an exam held that many locked coverage rows; UPSC CSE Mains holds
   1 497.

`PagingSB` models the server cap, honours `.range()` and `.order()`, and
shuffles any read that did not ask for an order — the licence Postgres
actually has, and what a correct paginated read must not depend on.
"""
from __future__ import annotations

import random
from typing import Any

from app.exam_intelligence.coverage import (
    _PAGE,
    locked_topic_coverage,
    locked_topic_coverage_summary,
    verified_pyq_topic_counts,
)
from tests.exam_intelligence.test_score_snapshot_idempotency import PagingSB, _Q, _R

# Above the 1 000-row server cap, at the scale the publication run hit.
N_TOPICS = 1497
N_QUESTIONS = 3294


def _topic(i: int) -> dict:
    return {"id": f"t{i:06d}", "name": f"Topic {i:06d}", "slug": f"topic-{i:06d}",
            "level": "microtopic", "is_active": True, "subject_id": "s1"}


def _coverage_corpus() -> dict:
    return {
        "exam_topic_coverage": [
            {
                "id": f"cov{i:06d}", "exam_id": "e1", "topic_id": f"t{i:06d}",
                "exam_phase_id": None, "exam_cycle_id": None,
                "exam_priority_score": float(i % 100), "is_high_yield": i % 7 == 0,
                "confidence_score": 0.8, "reviewer_status": "locked",
            }
            for i in range(N_TOPICS)
        ],
        "topics": [_topic(i) for i in range(N_TOPICS)],
        "subjects": [{"id": "s1", "slug": "psir", "name": "PSIR",
                      "subject_group": "optional", "is_active": True}],
    }


def _frequency_corpus() -> dict:
    """One verified paper, N verified questions, one primary tag each across
    40 topics — so a truncated read shows up as an undercount, not as a
    missing topic."""
    return {
        "pyq_papers": [{"id": "p1", "exam_id": "e1", "trust_status": "verified"}],
        "pyq_questions": [
            {"id": f"q{i:06d}", "pyq_paper_id": "p1", "reviewer_status": "verified"}
            for i in range(N_QUESTIONS)
        ],
        "pyq_question_topic_tags": [
            {
                "id": f"tag{i:06d}", "question_id": f"q{i:06d}",
                "topic_id": f"t{i % 40:06d}",
                "reviewer_status": "verified", "tag_role": "primary",
            }
            for i in range(N_QUESTIONS)
        ],
    }


# ── 1. Frequency counts are complete and stable ──────────────────────────────
def test_pyq_frequency_is_complete_across_the_server_cap():
    """3 294 questions against a 1 000-row ceiling. Every topic's count must be
    exact — the whole corpus divided evenly over 40 topics."""
    sb = PagingSB(_frequency_corpus())
    counts = verified_pyq_topic_counts(sb, "e1")

    assert counts is not None, "read reported incomplete"
    assert sum(counts.values()) == N_QUESTIONS
    assert len(counts) == 40
    expected = {f"t{t:06d}": len([i for i in range(N_QUESTIONS) if i % 40 == t])
                for t in range(40)}
    assert counts == expected


def test_pyq_frequency_is_identical_across_repeated_reads():
    """The undercount was intermittent: same inputs, different answers. Ten
    reads against a stub that reshuffles every unordered query must agree."""
    db = _frequency_corpus()
    results = [verified_pyq_topic_counts(PagingSB(db, seed=s), "e1") for s in range(10)]
    assert all(r is not None for r in results)
    assert all(r == results[0] for r in results), "frequency varies between reads"


# ── 2. Locked-coverage reads page past the cap ───────────────────────────────
def test_locked_topic_coverage_summary_returns_every_row_past_the_cap():
    """Was `.limit(1000)`; 1 497 rows exist."""
    rows = locked_topic_coverage_summary(PagingSB(_coverage_corpus()), "e1")
    assert rows is not None
    assert len(rows) == N_TOPICS
    assert len({r["topic_id"] for r in rows}) == N_TOPICS
    assert all(r["subject_name"] == "PSIR" for r in rows)  # joins survived chunking


def test_locked_topic_coverage_returns_every_row_past_the_cap():
    """Was `.limit(2000)`, which the server serves as 1 000."""
    rows = locked_topic_coverage(PagingSB(_coverage_corpus()), "e1")
    assert rows is not None
    assert len(rows) == N_TOPICS
    scores = [r["priority_score"] or 0 for r in rows]
    assert scores == sorted(scores, reverse=True)  # documented ordering kept
    assert all(r["topic"] for r in rows)  # topic-name join covered every row


# ── 3. An incomplete read refuses instead of answering partially ─────────────
def _short_read_sb(db: dict, table: str) -> PagingSB:
    """Drops one row from `table`'s reads while still reporting the true exact
    count — a partial read that looks exactly like success."""

    class _ShortSB(PagingSB):
        def table(self, name: str) -> _Q:
            q = super().table(name)
            if name != table:
                return q
            inner = q.execute

            def _short() -> _R:
                resp = inner()
                if resp.count is None or not resp.data:
                    return resp
                return _R(resp.data[:-1], count=resp.count)

            q.execute = _short  # type: ignore[method-assign]
            return q

    return _ShortSB(db)


def test_short_frequency_read_returns_none_not_an_undercount():
    """The whole point: a partial frequency map is worse than no map, because
    every caller can recognise `None`/empty and none can recognise partial."""
    assert verified_pyq_topic_counts(
        _short_read_sb(_frequency_corpus(), "pyq_question_topic_tags"), "e1"
    ) is None


def test_short_coverage_read_returns_none_not_a_truncated_list():
    assert locked_topic_coverage_summary(
        _short_read_sb(_coverage_corpus(), "exam_topic_coverage"), "e1"
    ) is None
    assert locked_topic_coverage(
        _short_read_sb(_coverage_corpus(), "exam_topic_coverage"), "e1"
    ) is None


def test_a_genuinely_empty_exam_is_still_empty_not_none():
    """Fail-closed must not swallow the ordinary "nothing here" answer."""
    sb = PagingSB({"exam_topic_coverage": [], "topics": [], "subjects": [],
                   "pyq_papers": [], "pyq_questions": [], "pyq_question_topic_tags": []})
    assert locked_topic_coverage_summary(sb, "e1") == []
    assert locked_topic_coverage(sb, "e1") == []
    assert verified_pyq_topic_counts(sb, "e1") == {}


def test_page_size_matches_the_server_cap_assumption():
    """The corpora above only exercise the multi-page path while `_PAGE` is at
    or below the modelled cap; pin it so a change here cannot quietly turn
    these into single-page reads."""
    assert _PAGE == 1000
