"""The read that made 1,351 questions look like 19.

Every bulk read in `study_os/descriptive.py` called `.execute()` with no
`.range()` and no `.order()`. PostgREST answers such a read with its first page
— Supabase's `db-max-rows` — and the module treated that page as the whole
corpus. Nothing errored: a truncated read is a successful one.

The symptom on demo, for Political Science: 777 verified paper-half + 574
verified thematic questions in the database, and a subject chip reading 19, two
papers reading 5 each, and "no themes" — the thematic papers never survived the
papers read at all.

These tests use a stub that enforces a row cap the way the server does, so a
read without pagination is short and a read with it is complete.
"""
from __future__ import annotations

from typing import Any

import pytest

from app.study_os import descriptive as d

EXAM = "5466e62f-7382-4a38-ba96-2fe5fbfeaba2"
USER = "user-p0"
PSIR = "Political Science and International Relations"


class CappedTable:
    """One table, capped at `cap` rows per response — like `db-max-rows`.

    A query with no `.range()` therefore sees only the first `cap` rows, which
    is exactly the server's behaviour and exactly what the old code did.
    """

    def __init__(self, rows, cap):
        self._rows = rows
        self._cap = cap
        self._filters = []
        self._order = None
        self._range = None
        self._limit = None

    def select(self, *a, **k):
        return self

    def eq(self, key, val):
        self._filters.append((key, "eq", val))
        return self

    def in_(self, key, vals):
        self._filters.append((key, "in", list(vals)))
        return self

    def order(self, key, desc=False):
        self._order = (key, desc)
        return self

    def range(self, a, b):
        self._range = (a, b)
        return self

    def limit(self, n):
        self._limit = n
        return self

    def execute(self):
        rows = [r for r in self._rows if self._matches(r)]
        if self._order:
            key, desc = self._order
            rows.sort(key=lambda r: str(r.get(key) or ""), reverse=desc)
        if self._range is not None:
            a, b = self._range
            rows = rows[a : b + 1]
        if self._limit is not None:
            rows = rows[: self._limit]
        # THE CAP. Applied last, exactly as a server row ceiling is.
        return type("Exec", (), {"data": rows[: self._cap]})()

    def _matches(self, row):
        for key, op, val in self._filters:
            if op == "eq" and row.get(key) != val:
                return False
            if op == "in" and row.get(key) not in val:
                return False
        return True


class CappedDb:
    def __init__(self, tables, cap):
        self._tables = tables
        self._cap = cap
        self.requests = 0

    def table(self, name):
        self.requests += 1
        return CappedTable(self._tables.get(name, []), self._cap)


def _seed(n_papers=6, per_paper=40, tagged=False):
    """Enough rows that any realistic cap truncates, if nothing paginates."""
    papers, questions, tags, topics = [], [], [], []
    for p in range(n_papers):
        thematic = p >= n_papers - 2
        papers.append({
            "id": f"paper-{p:03d}",
            "exam_id": EXAM,
            "year": 2013 + p,
            "paper_code": f"UPSC-CSE-MAINS-OPT-{2013 + p}-PSIR-P1",
            "trust_status": "pending",
            "metadata": (
                {"paper_kind": "optional", "corpus_half": "thematic"}
                if thematic
                else {"paper_kind": "optional", "optional_subject": PSIR,
                      "optional_paper_number": 1,
                      "split_from_bucket_id": "bucket"}
            ),
        })
        for q in range(per_paper):
            qid = f"q-{p:03d}-{q:03d}"
            questions.append({
                "id": qid,
                "pyq_paper_id": f"paper-{p:03d}",
                "question_number": 100 + q,
                "question_text": f"Question {p}.{q}",
                "question_type": "descriptive",
                "reviewer_status": "verified",
                "metadata": (
                    {"optional_subject": PSIR, "corpus_half": "thematic"}
                    if thematic
                    else {"optional_subject": PSIR, "optional_paper_number": 1}
                ),
            })
            if tagged and thematic:
                tags.append({"question_id": qid, "topic_id": "t-1",
                             "tag_role": "primary", "reviewer_status": "verified"})
    if tagged:
        topics.append({"id": "t-1", "name": "Sovereignty", "level": "microtopic",
                       "parent_topic_id": None, "subject_id": "s",
                       "metadata": {}})
    return {
        "pyq_papers": papers,
        "pyq_questions": questions,
        "pyq_question_topic_tags": tags,
        "topics": topics,
        "descriptive_attempts": [],
    }


# ── the truncation ───────────────────────────────────────────────────────


@pytest.mark.parametrize("cap", [5, 19, 50, 137])
def test_the_catalogue_counts_every_question_whatever_the_row_cap(cap):
    """The whole bug in one assertion. 6 papers × 40 = 240 questions; with a
    cap of 5 the old code reported a handful and called it the corpus."""
    db = CappedDb(_seed(), cap)
    out = d.get_catalog(db, EXAM, subject=PSIR)

    counts = {s["subject"]: s["question_count"] for s in out["subjects"]}
    assert counts[PSIR] == 240


def test_every_paper_is_listed_whatever_the_row_cap():
    """Four real papers, not the two that happened to be in the first page."""
    db = CappedDb(_seed(), cap=7)
    out = d.get_catalog(db, EXAM, subject=PSIR)

    assert len(out["papers"]) == 4
    assert all(p["question_count"] == 40 for p in out["papers"])


def test_the_thematic_half_is_not_lost_to_the_cap():
    """"No themes" on demo was the thematic PAPERS never surviving the papers
    read, so their questions were never even asked for."""
    db = CappedDb(_seed(tagged=True), cap=7)
    out = d.get_catalog(db, EXAM, subject=PSIR)

    total = sum(p["question_count"] for p in out["themes"])
    assert total == 80  # two thematic papers × 40
    names = {t["theme"] for p in out["themes"] for s in p["sections"] for t in s["themes"]}
    assert names == {"Sovereignty"}


def test_the_question_list_is_not_truncated_by_the_cap():
    db = CappedDb(_seed(), cap=7)
    out = d.list_questions(db, USER, exam_id=EXAM, subject=PSIR, limit=200)
    assert out["total_matching"] == 240


def test_pagination_stops_rather_than_looping_forever():
    """A full page must be followed by another read; a short page must end it.
    Getting this wrong is an infinite loop against production."""
    db = CappedDb(_seed(n_papers=2, per_paper=3), cap=10_000)
    d.get_catalog(db, EXAM, subject=PSIR)
    assert db.requests < 50


# ── tags must never gate listing ─────────────────────────────────────────


def test_untagged_verified_questions_are_listed_and_counted():
    """Tags drive theme GROUPING only. The listing gate is reviewer_status
    verified + descriptive + not map-only, and nothing else."""
    db = CappedDb(_seed(tagged=False), cap=10_000)  # not one tag anywhere
    out = d.get_catalog(db, EXAM, subject=PSIR)

    counts = {s["subject"]: s["question_count"] for s in out["subjects"]}
    assert counts[PSIR] == 240
    assert sum(p["question_count"] for p in out["papers"]) == 160
    # The thematic half is still counted — as "Untagged", not as nothing.
    assert sum(p["question_count"] for p in out["themes"]) == 80

    listed = d.list_questions(db, USER, exam_id=EXAM, subject=PSIR, limit=200)
    assert listed["total_matching"] == 240


def test_a_broken_tag_read_does_not_shrink_the_listing():
    """Themes degrade to Untagged; the count does not move."""
    seed = _seed(tagged=True)
    db = CappedDb(seed, cap=10_000)
    original = db.table

    def _table(name):
        t = original(name)
        if name == "pyq_question_topic_tags":
            def _boom():
                raise RuntimeError("tag read failed")
            t.execute = _boom
        return t

    db.table = _table
    out = d.get_catalog(db, EXAM, subject=PSIR)
    counts = {s["subject"]: s["question_count"] for s in out["subjects"]}
    assert counts[PSIR] == 240
    assert sum(p["question_count"] for p in out["themes"]) == 80


def test_marks_never_gate_the_listing():
    """Not one fixture question carries `marks`; all 240 are listed."""
    seed = _seed()
    assert all("marks" not in q["metadata"] for q in seed["pyq_questions"])
    out = d.list_questions(CappedDb(seed, 10_000), USER, exam_id=EXAM,
                           subject=PSIR, limit=200)
    assert out["total_matching"] == 240
