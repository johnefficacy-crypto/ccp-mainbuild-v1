"""P2 — the answer history: every attempt an aspirant has written.

The surface exists because a submitted attempt is never replaced. Writing a
question again keeps the old answer, and the comparison between the two is the
only evidence of improvement this product has. So the contract these pin is:
nothing is dropped, nothing is another user's, and the full answer text never
travels in a list.
"""
from __future__ import annotations

import pytest

from app.study_os import descriptive as d

PSIR = "Political Science and International Relations"
USER = "user-me"
OTHER = "user-someone-else"


class Table:
    """One table with PostgREST-shaped filters, ordering and a row cap."""

    def __init__(self, rows, cap):
        self._rows = rows
        self._cap = cap
        self._filters = []
        self._orders = []
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
        self._orders.append((key, desc))
        return self

    def range(self, a, b):
        self._range = (a, b)
        return self

    def limit(self, n):
        self._limit = n
        return self

    def execute(self):
        rows = [r for r in self._rows if self._matches(r)]
        for key, desc in reversed(self._orders):
            rows.sort(key=lambda r: str(r.get(key) or ""), reverse=desc)
        if self._range is not None:
            a, b = self._range
            rows = rows[a : b + 1]
        if self._limit is not None:
            rows = rows[: self._limit]
        return type("Exec", (), {"data": rows[: self._cap]})()

    def _matches(self, row):
        for key, op, val in self._filters:
            if op == "eq" and row.get(key) != val:
                return False
            if op == "in" and row.get(key) not in val:
                return False
        return True


class Db:
    def __init__(self, tables, cap=1000):
        self._tables = tables
        self._cap = cap

    def table(self, name):
        return Table(self._tables.get(name, []), self._cap)


def _paper(pid, year, *, thematic=False, number=1):
    return {
        "id": pid,
        "exam_id": "exam-1",
        "year": year,
        "paper_code": f"UPSC-CSE-MAINS-OPT-{year}-PSIR-P{number}",
        "trust_status": "pending",
        "metadata": (
            {"paper_kind": "optional", "corpus_half": "thematic",
             "optional_subject": PSIR}
            if thematic
            else {"paper_kind": "optional", "optional_subject": PSIR,
                  "optional_paper_number": number, "split_from_bucket_id": "b"}
        ),
    }


def _question(qid, pid, number, text, *, thematic=False, marks=15, status="verified"):
    meta = {"optional_subject": PSIR, "marks": marks}
    if thematic:
        meta["corpus_half"] = "thematic"
    else:
        meta["optional_paper_number"] = 1
    return {
        "id": qid, "pyq_paper_id": pid, "question_number": number,
        "question_text": text, "question_type": "descriptive",
        "reviewer_status": status, "metadata": meta,
    }


def _attempt(aid, qid, *, user=USER, status="submitted", words=250, score=8,
             started="2026-03-01T10:00:00Z", submitted="2026-03-01T11:00:00Z",
             mode="typed", pasted=0, text="An answer."):
    return {
        "id": aid, "user_id": user, "pyq_question_id": qid, "status": status,
        "answer_text": text, "word_count": words, "time_spent_seconds": 1800,
        "timer_target_seconds": 1080, "pasted_chars": pasted,
        "answer_mode": mode, "self_scores": {"structure": 2}, "self_total": score,
        "notes": None, "started_at": started,
        "submitted_at": submitted if status == "submitted" else None,
        "updated_at": submitted or started,
    }


def _db(**over):
    tables = {
        "pyq_papers": [_paper("p-2019", 2019), _paper("p-2021", 2021),
                       _paper("p-th", 2020, thematic=True)],
        "pyq_questions": [
            _question("q-a", "p-2019", 101, "Examine the idea of sovereignty in a globalised order."),
            _question("q-b", "p-2021", 102, "Discuss coalition politics in India."),
            _question("q-t", "p-th", 103, "Trace the evolution of federalism.", thematic=True),
        ],
        "pyq_question_topic_tags": [
            {"question_id": "q-t", "topic_id": "t-1", "tag_role": "primary",
             "reviewer_status": "verified"},
        ],
        "topics": [{"id": "t-1", "name": "Federalism", "level": "microtopic",
                    "parent_topic_id": None, "subject_id": "s-1", "metadata": {}}],
        "subjects": [{"id": "s-1", "name": PSIR, "slug": "upsc-cse-mains-opt-psir-p1"}],
        "descriptive_attempts": [
            _attempt("a-1", "q-a", started="2026-01-10T09:00:00Z",
                     submitted="2026-01-10T10:00:00Z", score=6, words=180),
            _attempt("a-2", "q-a", started="2026-02-10T09:00:00Z",
                     submitted="2026-02-10T10:00:00Z", score=9, words=260),
            _attempt("a-3", "q-b", started="2026-03-10T09:00:00Z",
                     submitted="2026-03-10T10:00:00Z", mode="handwritten",
                     words=0, pasted=None),
            _attempt("a-4", "q-t", status="draft", started="2026-04-10T09:00:00Z",
                     submitted=None, score=None, pasted=120),
            _attempt("a-x", "q-a", user=OTHER, started="2026-05-01T09:00:00Z",
                     submitted="2026-05-01T10:00:00Z"),
        ],
    }
    tables.update(over)
    return Db(tables)


# ── the list ───────────────────────────────────────────────────────────────

def test_every_attempt_is_listed_newest_first():
    out = d.list_attempts(_db(), USER)
    assert [i["id"] for i in out["items"]] == ["a-4", "a-3", "a-2", "a-1"]
    assert out["total"] == 4


def test_another_users_attempt_never_appears():
    out = d.list_attempts(_db(), USER)
    assert "a-x" not in {i["id"] for i in out["items"]}
    other = d.list_attempts(_db(), OTHER)
    assert [i["id"] for i in other["items"]] == ["a-x"]


def test_a_list_row_carries_the_question_but_not_the_answer():
    """A hundred-row page must not be a hundred essays."""
    row = d.list_attempts(_db(), USER)["items"][0]
    assert "answer_text" not in row
    assert row["question"]["excerpt"]
    assert row["question"]["breadcrumb"]["source"]


def test_the_excerpt_is_cut_on_a_word_boundary_with_an_ellipsis():
    long_text = "Examine " + ("the nature of sovereignty " * 20)
    db = _db(pyq_questions=[_question("q-a", "p-2019", 101, long_text)])
    row = d.list_attempts(db, USER)["items"][-1]
    excerpt = row["question"]["excerpt"]
    assert excerpt.endswith("…")
    assert len(excerpt) <= d._EXCERPT_CHARS + 1
    assert "  " not in excerpt


def test_breadcrumb_shows_the_sitting_for_a_paper_question():
    rows = {i["id"]: i for i in d.list_attempts(_db(), USER)["items"]}
    assert "2019" in rows["a-1"]["question"]["breadcrumb"]["source"]
    assert "15 marks" in rows["a-1"]["question"]["breadcrumb"]["source"]


def test_breadcrumb_says_theme_compilation_for_the_thematic_half():
    rows = {i["id"]: i for i in d.list_attempts(_db(), USER)["items"]}
    assert rows["a-4"]["question"]["breadcrumb"]["source"].startswith("Theme compilation")
    assert rows["a-4"]["question"]["theme"] == "Federalism"
    assert rows["a-4"]["question"]["is_thematic"] is True


def test_an_attempt_survives_its_question_losing_verification():
    """Their answer is theirs. Hiding it because the corpus changed under them
    would be the surface lying about their own history."""
    db = _db(pyq_questions=[
        _question("q-a", "p-2019", 101, "Examine sovereignty.", status="rejected"),
        _question("q-b", "p-2021", 102, "Discuss coalition politics."),
        _question("q-t", "p-th", 103, "Trace federalism.", thematic=True),
    ])
    out = d.list_attempts(db, USER)
    assert {"a-1", "a-2"} <= {i["id"] for i in out["items"]}
    rows = {i["id"]: i for i in out["items"]}
    assert rows["a-1"]["question"]["excerpt"] == "Examine sovereignty."


# ── badges ─────────────────────────────────────────────────────────────────

def test_answer_mode_badge_defaults_to_typed_and_reports_handwritten():
    rows = {i["id"]: i for i in d.list_attempts(_db(), USER)["items"]}
    assert rows["a-1"]["answer_mode"] == "typed"
    assert rows["a-3"]["answer_mode"] == "handwritten"


def test_an_attempt_predating_answer_mode_reads_typed():
    db = _db(descriptive_attempts=[{**_attempt("a-1", "q-a"), "answer_mode": None}])
    assert d.list_attempts(db, USER)["items"][0]["answer_mode"] == "typed"


def test_the_pasted_badge_is_three_valued_not_two():
    """0 and null are different answers: null is "this attempt predates paste
    tracking", 0 is "nothing was pasted". A two-valued badge would assert
    something nobody measured."""
    rows = {i["id"]: i for i in d.list_attempts(_db(), USER)["items"]}
    assert rows["a-1"]["has_pasted_text"] is False   # measured, clean
    assert rows["a-4"]["has_pasted_text"] is True    # measured, pasted
    assert rows["a-3"]["has_pasted_text"] is None    # never measured


# ── filters ────────────────────────────────────────────────────────────────

def test_filter_by_paper():
    out = d.list_attempts(_db(), USER, paper_id="p-2019")
    assert [i["id"] for i in out["items"]] == ["a-2", "a-1"]


def test_filter_by_theme():
    out = d.list_attempts(_db(), USER, theme="Federalism")
    assert [i["id"] for i in out["items"]] == ["a-4"]


def test_filter_by_subject():
    assert d.list_attempts(_db(), USER, subject=PSIR)["total"] == 4
    assert d.list_attempts(_db(), USER, subject="Anthropology")["total"] == 0


def test_filter_by_status():
    assert [i["id"] for i in d.list_attempts(_db(), USER, status="draft")["items"]] == ["a-4"]
    assert d.list_attempts(_db(), USER, status="submitted")["total"] == 3


@pytest.mark.parametrize("since,until,expected", [
    ("2026-02-01", None, ["a-4", "a-3", "a-2"]),
    (None, "2026-02-28", ["a-2", "a-1"]),
    ("2026-02-01", "2026-03-31", ["a-3", "a-2"]),
])
def test_filter_by_date_range_is_inclusive(since, until, expected):
    out = d.list_attempts(_db(), USER, since=since, until=until)
    assert [i["id"] for i in out["items"]] == expected


def test_filters_compose():
    out = d.list_attempts(_db(), USER, subject=PSIR, status="submitted",
                          paper_id="p-2019", since="2026-02-01")
    assert [i["id"] for i in out["items"]] == ["a-2"]


# ── facets ─────────────────────────────────────────────────────────────────

def test_facets_describe_the_whole_history_not_the_filtered_page():
    """A filter list that shrinks as you use it cannot be used to widen a
    selection again."""
    out = d.list_attempts(_db(), USER, status="draft")
    assert out["total"] == 1
    statuses = {f["value"] for f in out["facets"]["statuses"]}
    assert statuses == {"draft", "submitted"}
    assert {f["value"] for f in out["facets"]["themes"]} == {"Federalism"}
    assert len(out["facets"]["papers"]) == 3


def test_facets_offer_only_subjects_the_aspirant_has_written_in():
    out = d.list_attempts(_db(), USER)
    assert [f["value"] for f in out["facets"]["subjects"]] == [PSIR]
    assert out["facets"]["subjects"][0]["count"] == 4


# ── paging ─────────────────────────────────────────────────────────────────

def test_paging_walks_the_whole_history_without_repeating_a_row():
    seen, offset = [], 0
    while True:
        out = d.list_attempts(_db(), USER, limit=1, offset=offset)
        seen.extend(i["id"] for i in out["items"])
        if not out["has_more"]:
            break
        offset += 1
    assert seen == ["a-4", "a-3", "a-2", "a-1"]
    assert len(seen) == len(set(seen))


def test_the_page_size_is_capped():
    out = d.list_attempts(_db(), USER, limit=10_000)
    assert out["limit"] == d._MAX_ATTEMPT_PAGE


def test_a_history_longer_than_the_server_cap_is_still_complete():
    """The P0.5 rule, on this surface: 320 attempts against a 19-row cap."""
    attempts = [
        _attempt(f"a-{i:04d}", "q-a", started=f"2026-01-01T00:{i % 60:02d}:00Z")
        for i in range(320)
    ]
    db = Db({**_db()._tables, "descriptive_attempts": attempts}, cap=19)
    out = d.list_attempts(db, USER, limit=200)
    assert out["total"] == 320


# ── one attempt, read-only ─────────────────────────────────────────────────

def test_attempt_detail_carries_the_full_answer_and_offers_a_rewrite():
    out = d.attempt_detail(_db(), USER, "a-1")
    assert out["attempt"]["answer_text"] == "An answer."
    assert out["attempt"]["question"]["excerpt"]
    assert out["can_rewrite"] is True


def test_attempt_detail_refuses_another_users_attempt():
    with pytest.raises(d.DescriptiveError) as exc:
        d.attempt_detail(_db(), USER, "a-x")
    assert exc.value.status == 404


# ── compare ────────────────────────────────────────────────────────────────

def test_compare_returns_attempts_oldest_first_because_progress_runs_forwards():
    out = d.compare_attempts(_db(), USER, "q-a")
    assert [a["id"] for a in out["attempts"]] == ["a-1", "a-2"]
    assert out["count"] == 2 and out["submitted_count"] == 2


def test_compare_states_the_first_and_last_score_and_word_count():
    """Stated server-side so two surfaces cannot disagree about what improved."""
    out = d.compare_attempts(_db(), USER, "q-a")
    assert (out["self_total_first"], out["self_total_last"]) == (6, 9)
    assert (out["word_count_first"], out["word_count_last"]) == (180, 260)


def test_compare_carries_the_answer_text_because_that_is_the_comparison():
    out = d.compare_attempts(_db(), USER, "q-a")
    assert all(a["answer_text"] == "An answer." for a in out["attempts"])


def test_compare_ignores_a_draft_in_the_score_trend_but_still_lists_it():
    out = d.compare_attempts(_db(), USER, "q-t")
    assert [a["id"] for a in out["attempts"]] == ["a-4"]
    assert out["submitted_count"] == 0
    assert out["self_total_first"] is None


def test_compare_never_crosses_users():
    out = d.compare_attempts(_db(), OTHER, "q-a")
    assert [a["id"] for a in out["attempts"]] == ["a-x"]


def test_compare_of_an_unattempted_question_is_empty_not_an_error():
    out = d.compare_attempts(_db(), USER, "q-never")
    assert out["attempts"] == [] and out["question"] is None


def test_compare_requires_a_question():
    with pytest.raises(d.DescriptiveError) as exc:
        d.compare_attempts(_db(), USER, "")
    assert exc.value.status == 400
