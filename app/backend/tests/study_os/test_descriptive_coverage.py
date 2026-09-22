"""P4 — coverage: what has been written, and what is still waiting.

The number an aspirant needs is not "how much of the corpus exists" but "how
much of it have I actually answered". These pin the three things that make that
number trustworthy: only SUBMITTED attempts count, nothing is dropped between
the three groupings, and an average over nothing is absent rather than zero.
"""
from __future__ import annotations

import pytest

from app.study_os import descriptive as d

EXAM = "exam-1"
USER = "user-1"
PSIR = "Political Science and International Relations"


class Table:
    def __init__(self, rows):
        self._rows = rows
        self._f = []
        self._range = None

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


def _q(qid, paper, number, *, marks=15, text=None):
    return {
        "id": qid, "pyq_paper_id": paper, "question_number": number,
        "question_text": text or f"Question {qid}.",
        "question_type": "descriptive", "reviewer_status": "verified",
        "metadata": {"optional_subject": PSIR, "optional_paper_number": 1,
                     "marks": marks},
    }


def _attempt(aid, qid, *, status="submitted", score=8, user=USER):
    return {"id": aid, "user_id": user, "pyq_question_id": qid,
            "status": status, "self_total": score}


def _db(attempts=(), tags=(), topics=()):
    return Db({
        "pyq_papers": [
            {"id": "p-2019", "exam_id": EXAM, "year": 2019,
             "paper_code": "UPSC-CSE-MAINS-OPT-2019-PSIR-P1",
             "trust_status": "pending",
             "metadata": {"paper_kind": "optional", "optional_subject": PSIR,
                          "optional_paper_number": 1,
                          "split_from_bucket_id": "b"}},
        ],
        "pyq_questions": [_q("q-1", "p-2019", 101), _q("q-2", "p-2019", 102),
                          _q("q-3", "p-2019", 103)],
        "descriptive_attempts": list(attempts),
        "pyq_question_topic_tags": list(tags),
        "topics": list(topics),
        "subjects": [],
    })


# ── only submitted attempts count ──────────────────────────────────────────

def test_nothing_attempted_is_zero_of_the_available_total():
    out = d.coverage(_db(), USER, exam_id=EXAM)
    assert out["totals"] == {
        "available": 3, "attempted": 0, "unattempted": 3,
        "avg_self_score": None, "subjects": 1,
    }


def test_a_submitted_attempt_counts_as_covered():
    out = d.coverage(_db([_attempt("a-1", "q-1")]), USER, exam_id=EXAM)
    assert out["totals"]["attempted"] == 1
    assert out["totals"]["unattempted"] == 2


def test_an_open_draft_does_not_count():
    """Coverage must not go up by opening questions and closing the tab."""
    out = d.coverage(_db([_attempt("a-1", "q-1", status="draft")]), USER, exam_id=EXAM)
    assert out["totals"]["attempted"] == 0


def test_two_attempts_at_one_question_are_one_covered_question():
    out = d.coverage(
        _db([_attempt("a-1", "q-1", score=6), _attempt("a-2", "q-1", score=10)]),
        USER, exam_id=EXAM,
    )
    assert out["totals"]["attempted"] == 1
    # ...but both scores inform the average, because both are judgements made.
    assert out["totals"]["avg_self_score"] == 8.0
    assert out["subjects"][0]["scored_attempts"] == 2


def test_another_users_attempts_never_count():
    out = d.coverage(_db([_attempt("a-x", "q-1", user="someone-else")]),
                     USER, exam_id=EXAM)
    assert out["totals"]["attempted"] == 0


# ── the average ────────────────────────────────────────────────────────────

def test_an_average_over_nothing_is_absent_not_zero():
    """0 would read as "everything they wrote scored zero"."""
    out = d.coverage(_db(), USER, exam_id=EXAM)
    assert out["totals"]["avg_self_score"] is None
    assert out["subjects"][0]["avg_self_score"] is None
    assert out["subjects"][0]["groups"][0]["avg_self_score"] is None


def test_an_unscored_submitted_attempt_counts_as_covered_but_not_as_a_score():
    out = d.coverage(_db([_attempt("a-1", "q-1", score=None)]), USER, exam_id=EXAM)
    assert out["totals"]["attempted"] == 1
    assert out["totals"]["avg_self_score"] is None
    assert out["subjects"][0]["scored_attempts"] == 0


def test_the_average_is_over_attempts_not_over_questions():
    out = d.coverage(
        _db([_attempt("a-1", "q-1", score=12), _attempt("a-2", "q-2", score=6),
             _attempt("a-3", "q-2", score=6)]),
        USER, exam_id=EXAM,
    )
    assert out["totals"]["avg_self_score"] == 8.0  # (12 + 6 + 6) / 3


# ── grouping falls back without dropping anything ──────────────────────────

def test_an_untagged_question_still_appears_under_its_paper():
    """An aspirant deciding what to write next needs the whole corpus, not the
    well-tagged part of it."""
    out = d.coverage(_db(), USER, exam_id=EXAM)
    groups = out["subjects"][0]["groups"]
    assert len(groups) == 1
    assert groups[0]["source"] == "paper"
    assert groups[0]["available"] == 3


def test_a_tagged_question_groups_by_its_topic_when_the_syllabus_cannot_place_it():
    db = _db(
        tags=[{"question_id": "q-1", "topic_id": "t-1", "tag_role": "primary",
               "reviewer_status": "verified"}],
        topics=[{"id": "t-1", "name": "A topic no syllabus contains",
                 "level": "microtopic", "parent_topic_id": None,
                 "subject_id": "s-1", "metadata": {}}],
    )
    out = d.coverage(db, USER, exam_id=EXAM)
    groups = {g["label"]: g for g in out["subjects"][0]["groups"]}
    assert groups["A topic no syllabus contains"]["source"] == "topic"
    assert groups["A topic no syllabus contains"]["available"] == 1
    # The other two are still counted, under the paper.
    assert sum(g["available"] for g in out["subjects"][0]["groups"]) == 3


def test_a_syllabus_placed_question_groups_by_paper_and_section():
    db = _db(
        tags=[{"question_id": "q-1", "topic_id": "t-1", "tag_role": "primary",
               "reviewer_status": "verified"}],
        topics=[{"id": "t-1", "name": "Aurangzeb", "level": "microtopic",
                 "parent_topic_id": None, "subject_id": "s-1",
                 "metadata": {"paper_id": "GS_1", "macro_topic": "Medieval India"}}],
    )
    out = d.coverage(db, USER, exam_id=EXAM)
    placed = [g for g in out["subjects"][0]["groups"] if g["source"] == "syllabus"]
    assert len(placed) == 1
    assert placed[0]["label"] == "GS1 · Medieval India"


def test_every_question_lands_in_exactly_one_group():
    db = _db(
        tags=[{"question_id": "q-1", "topic_id": "t-1", "tag_role": "primary",
               "reviewer_status": "verified"}],
        topics=[{"id": "t-1", "name": "Sovereignty", "level": "microtopic",
                 "parent_topic_id": None, "subject_id": "s-1", "metadata": {}}],
    )
    out = d.coverage(db, USER, exam_id=EXAM)
    assert sum(g["available"] for g in out["subjects"][0]["groups"]) == 3
    assert out["subjects"][0]["available"] == 3


# ── the not-yet-attempted list ─────────────────────────────────────────────

def test_the_unattempted_list_names_what_is_left():
    out = d.coverage(_db([_attempt("a-1", "q-1")]), USER, exam_id=EXAM)
    group = out["subjects"][0]["groups"][0]
    assert {u["id"] for u in group["unattempted"]} == {"q-2", "q-3"}
    assert group["unattempted_total"] == 2


def test_an_attempted_question_leaves_the_unattempted_list():
    out = d.coverage(
        _db([_attempt("a-1", "q-1"), _attempt("a-2", "q-2"), _attempt("a-3", "q-3")]),
        USER, exam_id=EXAM,
    )
    group = out["subjects"][0]["groups"][0]
    assert group["unattempted"] == [] and group["unattempted_total"] == 0


def test_a_long_unattempted_list_is_capped_and_says_how_many_more():
    """"and 340 more" is information; a silently shortened list is not."""
    many = [_q(f"q-{i:04d}", "p-2019", 100 + i) for i in range(120)]
    db = _db()
    db.tables["pyq_questions"] = many
    out = d.coverage(db, USER, exam_id=EXAM)
    group = out["subjects"][0]["groups"][0]
    assert len(group["unattempted"]) == d._UNATTEMPTED_SHOWN
    assert group["unattempted_total"] == 120


def test_an_unattempted_entry_carries_enough_to_choose_from():
    out = d.coverage(_db(), USER, exam_id=EXAM)
    entry = out["subjects"][0]["groups"][0]["unattempted"][0]
    assert entry["excerpt"] and entry["marks"] == 15
    assert entry["paper_id"] == "p-2019"


# ── scope ──────────────────────────────────────────────────────────────────

def test_a_map_question_is_not_counted_as_available():
    """It cannot be practised here, so counting it would make the subject
    permanently incompletable."""
    db = _db()
    db.tables["pyq_questions"] = [
        _q("q-1", "p-2019", 101),
        # The signal is the reviewed metadata flag, not the wording: a question
        # that merely mentions a map is still answerable in prose.
        {**_q("q-map", "p-2019", 102),
         "question_text": "Mark the following on the outline map of India.",
         "metadata": {"optional_subject": PSIR, "optional_paper_number": 1,
                      "marks": 15, "map_item": True}},
    ]
    out = d.coverage(db, USER, exam_id=EXAM)
    assert out["totals"]["available"] == 1


def test_a_subject_filter_narrows_the_whole_report():
    assert d.coverage(_db(), USER, exam_id=EXAM, subject=PSIR)["totals"]["available"] == 3
    assert d.coverage(_db(), USER, exam_id=EXAM, subject="Anthropology")["subjects"] == []


def test_coverage_requires_an_exam():
    with pytest.raises(d.DescriptiveError) as exc:
        d.coverage(_db(), USER, exam_id="")
    assert exc.value.status == 400


def test_an_exam_with_no_papers_is_empty_not_an_error():
    out = d.coverage(Db({"pyq_papers": []}), USER, exam_id=EXAM)
    assert out["subjects"] == [] and out["totals"]["available"] == 0
