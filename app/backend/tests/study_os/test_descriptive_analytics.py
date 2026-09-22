"""P5 — weekly analytics, computed from the attempts that already exist.

No new tracking: what an aspirant wrote, when, for how long, and how they
judged it is the whole input.

The thing these mostly hold is restraint. ~87% of the corpus carries no marks
and most questions carry no word limit, so every "vs target" number here is an
average over the subset that HAS a target — and each one states its own sample
size rather than quietly averaging over a target that does not exist.
"""
from __future__ import annotations

import pytest

from app.study_os import descriptive as d

USER = "user-1"


class Table:
    def __init__(self, rows):
        self._rows, self._f, self._range = rows, [], None

    def select(self, *a, **k):
        return self

    def eq(self, k, v):
        self._f.append((k, v))
        return self

    def in_(self, k, vals):
        self._f.append((k, list(vals)))
        return self

    def order(self, *a, **k):
        return self

    def range(self, a, b):
        self._range = (a, b)
        return self

    def limit(self, n):
        return self

    def execute(self):
        rows = [r for r in self._rows if self._ok(r)]
        if self._range:
            rows = rows[self._range[0] : self._range[1] + 1]
        return type("X", (), {"data": rows})()

    def _ok(self, row):
        for k, v in self._f:
            if isinstance(v, list):
                if row.get(k) not in v:
                    return False
            elif row.get(k) != v:
                return False
        return True


class Db:
    def __init__(self, tables):
        self.tables = tables

    def table(self, name):
        return Table(self.tables.get(name, []))


FULL = {k: 2 for k in d.RUBRIC_KEYS}


def _attempt(aid, qid, submitted, *, words=250, seconds=1080, scores=None,
             total=12, status="submitted", user=USER):
    return {
        "id": aid, "user_id": user, "pyq_question_id": qid, "status": status,
        "answer_text": "x", "word_count": words, "time_spent_seconds": seconds,
        "timer_target_seconds": 1080, "pasted_chars": 0, "answer_mode": "typed",
        "self_scores": FULL if scores is None else scores,
        "self_total": total, "notes": None,
        "started_at": submitted, "submitted_at": submitted,
        "updated_at": submitted,
    }


def _question(qid, *, marks=15, word_limit=250):
    meta = {}
    if marks is not None:
        meta["marks"] = marks
    if word_limit is not None:
        meta["word_limit"] = word_limit
    return {"id": qid, "pyq_paper_id": "p-1", "question_number": 1,
            "question_text": "Discuss.", "question_type": "descriptive",
            "reviewer_status": "verified", "metadata": meta}


def _db(attempts, questions=None, tags=(), topics=()):
    return Db({
        "descriptive_attempts": list(attempts),
        "pyq_questions": list(questions or [_question("q-1")]),
        "pyq_papers": [{"id": "p-1", "exam_id": "e", "year": 2020,
                        "paper_code": "X", "trust_status": "pending",
                        "metadata": {}}],
        "pyq_question_topic_tags": list(tags),
        "topics": list(topics),
        "subjects": [],
    })


# ── nothing written ────────────────────────────────────────────────────────

def test_no_attempts_gives_an_empty_report_not_an_error():
    out = d.analytics(_db([]), USER)
    assert out["submitted_total"] == 0
    assert out["weeks"] == []
    assert out["streak_weeks"] == 0
    assert out["weakest_dimensions"] is None
    assert all(v is None for v in out["rubric"].values())


def test_a_draft_is_not_an_answer_written():
    out = d.analytics(_db([_attempt("a", "q-1", "2026-03-02T10:00:00Z",
                                    status="draft")]), USER)
    assert out["submitted_total"] == 0


def test_another_users_attempts_are_never_counted():
    out = d.analytics(
        _db([_attempt("a", "q-1", "2026-03-02T10:00:00Z", user="other")]), USER
    )
    assert out["submitted_total"] == 0


def test_analytics_needs_a_user():
    with pytest.raises(d.DescriptiveError) as exc:
        d.analytics(_db([]), "")
    assert exc.value.status == 401


# ── weeks ──────────────────────────────────────────────────────────────────

def test_attempts_are_grouped_into_iso_weeks_starting_monday():
    out = d.analytics(_db([
        _attempt("a", "q-1", "2026-03-02T10:00:00Z"),   # Monday
        _attempt("b", "q-1", "2026-03-08T23:00:00Z"),   # the Sunday after
        _attempt("c", "q-1", "2026-03-09T00:30:00Z"),   # the next Monday
    ]), USER)
    assert [w["week"] for w in out["weeks"]] == ["2026-03-02", "2026-03-09"]
    assert [w["submitted"] for w in out["weeks"]] == [2, 1]


def test_the_window_keeps_the_most_recent_weeks():
    attempts = [
        _attempt(f"a{i}", "q-1", f"2026-0{1 + i // 4}-{(i % 4) * 7 + 2:02d}T10:00:00Z")
        for i in range(12)
    ]
    out = d.analytics(_db(attempts), USER, weeks=3)
    assert len(out["weeks"]) == 3
    assert out["weeks"] == sorted(out["weeks"], key=lambda w: w["week"])
    assert out["submitted_total"] == 12  # the total is not windowed


# ── words and time, only where a target exists ─────────────────────────────

def test_words_are_compared_only_where_the_question_states_a_limit():
    out = d.analytics(
        _db(
            [_attempt("a", "q-1", "2026-03-02T10:00:00Z", words=300),
             _attempt("b", "q-2", "2026-03-02T11:00:00Z", words=900)],
            questions=[_question("q-1", word_limit=250),
                       _question("q-2", word_limit=None)],
        ),
        USER,
    )
    week = out["weeks"][0]
    # Only q-1 has a limit, so only its 300 words are averaged against it.
    assert week["avg_words"] == 300.0
    assert week["avg_word_limit"] == 250.0
    assert week["words_sample"] == 1


def test_time_is_compared_only_where_the_question_carries_marks():
    """~87% of the corpus has no marks, so no target — an average "vs target"
    over everything would be an average over a target that does not exist."""
    out = d.analytics(
        _db(
            [_attempt("a", "q-1", "2026-03-02T10:00:00Z", seconds=1200),
             _attempt("b", "q-2", "2026-03-02T11:00:00Z", seconds=60)],
            questions=[_question("q-1", marks=15), _question("q-2", marks=None)],
        ),
        USER,
    )
    week = out["weeks"][0]
    assert week["avg_seconds"] == 1200.0
    assert week["avg_target_seconds"] == float(15 * d.SECONDS_PER_MARK)
    assert week["time_sample"] == 1


def test_a_week_with_no_comparable_question_reports_absent_not_zero():
    out = d.analytics(
        _db([_attempt("a", "q-2", "2026-03-02T10:00:00Z")],
            questions=[_question("q-2", marks=None, word_limit=None)]),
        USER,
    )
    week = out["weeks"][0]
    assert week["avg_words"] is None and week["words_sample"] == 0
    assert week["avg_seconds"] is None and week["time_sample"] == 0
    assert week["submitted"] == 1  # they still wrote one


# ── the rubric ─────────────────────────────────────────────────────────────

def test_each_rubric_dimension_gets_its_own_mean():
    out = d.analytics(_db([
        _attempt("a", "q-1", "2026-03-02T10:00:00Z",
                 scores={**FULL, "examples": 0}, total=10),
        _attempt("b", "q-1", "2026-03-03T10:00:00Z",
                 scores={**FULL, "examples": 1}, total=11),
    ]), USER)
    assert out["rubric"]["structure"] == 2.0
    assert out["rubric"]["examples"] == 0.5


def test_the_weakest_dimension_is_the_lowest_mean():
    out = d.analytics(_db([
        _attempt("a", "q-1", "2026-03-02T10:00:00Z",
                 scores={**FULL, "conclusion": 0}, total=10),
    ]), USER)
    assert out["weakest_dimensions"] == ["conclusion"]


def test_a_tie_for_weakest_is_reported_as_a_tie():
    """Two equally weak dimensions are two findings, not one picked by
    dictionary order."""
    out = d.analytics(_db([
        _attempt("a", "q-1", "2026-03-02T10:00:00Z",
                 scores={**FULL, "conclusion": 0, "examples": 0}, total=8),
    ]), USER)
    assert out["weakest_dimensions"] == ["conclusion", "examples"]


def test_a_dimension_nobody_scored_does_not_become_the_weakest():
    partial = {k: 2 for k in d.RUBRIC_KEYS if k != "examples"}
    out = d.analytics(_db([
        _attempt("a", "q-1", "2026-03-02T10:00:00Z", scores=partial, total=10),
    ]), USER)
    assert out["rubric"]["examples"] is None
    assert out["weakest_dimensions"] != ["examples"]


# ── the streak ─────────────────────────────────────────────────────────────

def test_the_streak_counts_consecutive_weeks_ending_now():
    out = d.analytics(_db([
        _attempt("a", "q-1", "2026-03-02T10:00:00Z"),
        _attempt("b", "q-1", "2026-03-09T10:00:00Z"),
        _attempt("c", "q-1", "2026-03-16T10:00:00Z"),
    ]), USER, today="2026-03-18")
    assert out["streak_weeks"] == 3


def test_a_missed_week_ends_the_streak():
    out = d.analytics(_db([
        _attempt("a", "q-1", "2026-03-02T10:00:00Z"),
        _attempt("c", "q-1", "2026-03-16T10:00:00Z"),
    ]), USER, today="2026-03-18")
    assert out["streak_weeks"] == 1


def test_this_week_being_unwritten_does_not_break_the_streak():
    """It is Tuesday for everyone at some point. A streak that resets every
    Monday morning measures the calendar, not the habit."""
    out = d.analytics(_db([
        _attempt("a", "q-1", "2026-03-09T10:00:00Z"),
        _attempt("b", "q-1", "2026-03-16T10:00:00Z"),
    ]), USER, today="2026-03-24")  # the week of the 23rd, nothing written yet
    assert out["streak_weeks"] == 2


def test_a_long_gap_leaves_no_streak():
    out = d.analytics(_db([_attempt("a", "q-1", "2026-01-05T10:00:00Z")]),
                      USER, today="2026-03-18")
    assert out["streak_weeks"] == 0


# ── topic strength ─────────────────────────────────────────────────────────

def _tagged(n, topic_name, *, totals):
    questions = [_question(f"q-{topic_name}-{i}") for i in range(n)]
    tags = [{"question_id": q["id"], "topic_id": f"t-{topic_name}",
             "tag_role": "primary", "reviewer_status": "verified"}
            for q in questions]
    topics = [{"id": f"t-{topic_name}", "name": topic_name, "level": "microtopic",
               "parent_topic_id": None, "subject_id": "s", "metadata": {}}]
    attempts = [
        _attempt(f"a-{topic_name}-{i}", q["id"], f"2026-03-0{2 + i}T10:00:00Z",
                 total=totals[i])
        for i, q in enumerate(questions)
    ]
    return questions, tags, topics, attempts


def test_a_topic_below_the_threshold_is_not_called_strong_or_weak():
    """Two answers is a mood; three is the smallest number a direction can be
    read from. Saying "your weakest topic" off one attempt is an accusation."""
    qs, tags, tops, atts = _tagged(2, "Federalism", totals=[3, 4])
    out = d.analytics(_db(atts, questions=qs, tags=tags, topics=tops), USER)
    assert out["strongest_topics"] == [] and out["weakest_topics"] == []
    assert out["topics_below_threshold"] == 1
    assert out["min_attempts_per_topic"] == d.MIN_ATTEMPTS_PER_TOPIC


def test_a_topic_at_the_threshold_is_ranked():
    qs, tags, tops, atts = _tagged(3, "Federalism", totals=[9, 10, 11])
    out = d.analytics(_db(atts, questions=qs, tags=tags, topics=tops), USER)
    assert out["strongest_topics"] == [
        {"topic": "Federalism", "attempts": 3, "avg_self_total": 10.0}
    ]
    assert out["topics_below_threshold"] == 0


def test_strong_and_weak_are_the_two_ends_of_one_ranking():
    q1, t1, top1, a1 = _tagged(3, "Strong", totals=[11, 12, 12])
    q2, t2, top2, a2 = _tagged(3, "Weak", totals=[2, 3, 4])
    out = d.analytics(
        _db(a1 + a2, questions=q1 + q2, tags=t1 + t2, topics=top1 + top2), USER
    )
    assert out["strongest_topics"][0]["topic"] == "Strong"
    assert out["weakest_topics"][0]["topic"] == "Weak"


def test_an_untagged_attempt_is_counted_but_not_ranked_by_topic():
    out = d.analytics(_db([
        _attempt("a", "q-1", "2026-03-02T10:00:00Z"),
        _attempt("b", "q-1", "2026-03-03T10:00:00Z"),
        _attempt("c", "q-1", "2026-03-04T10:00:00Z"),
    ]), USER)
    assert out["submitted_total"] == 3
    assert out["strongest_topics"] == []
    assert out["topics_below_threshold"] == 0


def test_an_unscored_attempt_does_not_drag_a_topic_average_to_zero():
    qs, tags, tops, atts = _tagged(3, "Federalism", totals=[9, 9, 9])
    atts.append(_attempt("a-none", qs[0]["id"], "2026-03-06T10:00:00Z", total=None))
    out = d.analytics(_db(atts, questions=qs, tags=tags, topics=tops), USER)
    assert out["strongest_topics"][0]["avg_self_total"] == 9.0
    assert out["strongest_topics"][0]["attempts"] == 3


# ── helpers ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("stamp,monday", [
    ("2026-03-02T10:00:00Z", "2026-03-02"),
    ("2026-03-08T23:59:00Z", "2026-03-02"),
    ("2026-03-09T00:00:00Z", "2026-03-09"),
])
def test_week_start_is_the_monday(stamp, monday):
    assert d._week_start(stamp) == monday


@pytest.mark.parametrize("bad", [None, "", "not-a-date", "2026-13-40"])
def test_an_unparseable_timestamp_has_no_week(bad):
    assert d._week_start(bad) is None


def test_a_mean_over_nothing_is_absent():
    assert d._mean([]) is None
    assert d._mean([0.0, 0.0]) == 0.0  # a real zero survives
