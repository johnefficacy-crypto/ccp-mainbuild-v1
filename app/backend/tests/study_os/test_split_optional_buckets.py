"""Planning contract for scripts/split_optional_buckets.py (PRACTICE-PAPER-01).

The script separates planning from IO precisely so the grouping rules can be
proven without a database. These cover the split shape, idempotency inputs, and
the two abort conditions.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "split_optional_buckets",
    Path(__file__).resolve().parents[4] / "scripts/split_optional_buckets.py",
)
sob = importlib.util.module_from_spec(_SPEC)
sys.modules["split_optional_buckets"] = sob
_SPEC.loader.exec_module(sob)

BUCKET_ID = "aaaaaaaa-0000-0000-0000-000000000001"


def _bucket(**over):
    b = {
        "id": BUCKET_ID,
        "exam_id": "e1", "exam_phase_id": "p1", "exam_cycle_id": "c1",
        "paper_code": "UPSC-CSE-MAINS-OPT-2019",
        "metadata": {
            "paper_kind": "optional",
            "paper_code": "UPSC-CSE-MAINS-OPT-2019",
            "extraction_source": "official-pdf",
            "verified_against_official": True,
            "promotion_blocked_by": ["provenance_incomplete"],
            "unrelated_key": "must not travel",
        },
    }
    b.update(over)
    return b


def _q(qid, subject, number, **meta):
    return {"id": qid, "metadata": {"optional_subject": subject,
                                    "optional_paper_number": number, **meta}}


# ── the split shape ────────────────────────────────────────────────────────

def test_two_subjects_two_papers_produce_four_rows_with_correct_counts():
    questions = (
        [_q(f"a{i}", "Anthropology", 1) for i in range(3)]
        + [_q(f"b{i}", "Anthropology", 2) for i in range(2)]
        + [_q(f"c{i}", "Political Science & International Relations", 1) for i in range(4)]
        + [_q("d0", "Political Science & International Relations", 2)]
    )
    planned = sob.plan_bucket(_bucket(), questions)

    assert [p["paper_code"] for p in planned] == [
        "UPSC-CSE-MAINS-OPT-2019-ANTHROPOLOGY-P1",
        "UPSC-CSE-MAINS-OPT-2019-ANTHROPOLOGY-P2",
        "UPSC-CSE-MAINS-OPT-2019-POLITICAL-SCIENCE-INTERNATIONAL-RELATIONS-P1",
        "UPSC-CSE-MAINS-OPT-2019-POLITICAL-SCIENCE-INTERNATIONAL-RELATIONS-P2",
    ]
    assert [p["question_count"] for p in planned] == [3, 2, 4, 1]
    # Every question lands exactly once.
    moved = [qid for p in planned for qid in p["question_ids"]]
    assert sorted(moved) == sorted(q["id"] for q in questions)
    assert len(moved) == len(set(moved)) == 10


def test_metadata_carries_lineage_and_provenance_but_not_stray_keys():
    planned = sob.plan_bucket(_bucket(), [_q("q1", "Geography", 1)])
    meta = planned[0]["metadata"]
    assert meta["split_from_bucket_id"] == BUCKET_ID
    assert meta["optional_subject"] == "Geography"
    assert meta["optional_paper_number"] == 1
    assert meta["year"] == 2019
    assert meta["question_count"] == 1
    assert meta["paper_kind"] == "optional"
    # Provenance travels; unrelated bucket keys do not.
    assert meta["extraction_source"] == "official-pdf"
    assert meta["verified_against_official"] is True
    assert meta["promotion_blocked_by"] == ["provenance_incomplete"]
    assert "unrelated_key" not in meta
    assert "corpus_half" not in meta


def test_paper_code_is_the_idempotency_key_and_is_deterministic():
    """A re-run matches an existing split row by metadata.paper_code, so the
    same input must always produce the same code."""
    a = sob.plan_bucket(_bucket(), [_q("q1", "Public Administration", 2)])
    b = sob.plan_bucket(_bucket(), [_q("q9", "Public Administration", 2)])
    assert a[0]["paper_code"] == b[0]["paper_code"]
    assert a[0]["paper_code"] == a[0]["metadata"]["paper_code"]


def test_question_numbers_are_never_touched():
    """Block encoding (100s, 200s per subject) is the printed order. The plan
    carries ids only — nothing in it can renumber a question."""
    planned = sob.plan_bucket(_bucket(), [_q("q1", "Sociology", 1, question_number=101)])
    assert set(planned[0]) == {
        "paper_code", "optional_subject", "optional_paper_number",
        "year", "question_ids", "question_count", "metadata",
    }


# ── abort conditions ───────────────────────────────────────────────────────

@pytest.mark.parametrize("bad", [
    {"optional_subject": None, "optional_paper_number": 1},
    {"optional_subject": "", "optional_paper_number": 1},
    {"optional_subject": "History", "optional_paper_number": None},
    {"optional_subject": "History", "optional_paper_number": ""},
    {},
])
def test_missing_subject_or_paper_number_aborts_the_whole_bucket(bad):
    """Partial is worse than nothing: the unsplittable questions would be
    stranded on a bucket that the run then retires."""
    questions = [_q("good", "History", 1), {"id": "bad", "metadata": bad}]
    with pytest.raises(sob.BucketAbort) as exc:
        sob.plan_bucket(_bucket(), questions)
    assert "optional_subject" in str(exc.value)


def test_bucket_without_paper_code_aborts():
    with pytest.raises(sob.BucketAbort):
        sob.plan_bucket(_bucket(paper_code=None, metadata={"paper_kind": "optional"}),
                        [_q("q1", "History", 1)])


def test_bucket_with_no_questions_aborts():
    with pytest.raises(sob.BucketAbort):
        sob.plan_bucket(_bucket(), [])


# ── slug + year helpers ────────────────────────────────────────────────────

@pytest.mark.parametrize("raw,slug", [
    ("Anthropology", "ANTHROPOLOGY"),
    ("Political Science & International Relations", "POLITICAL-SCIENCE-INTERNATIONAL-RELATIONS"),
    ("Public Administration", "PUBLIC-ADMINISTRATION"),
    ("  spaced  out  ", "SPACED-OUT"),
    ("Sociology-II", "SOCIOLOGY-II"),
])
def test_subject_slug(raw, slug):
    assert sob.subject_slug(raw) == slug


def test_year_parsed_from_bucket_code_or_none():
    assert sob.year_from_bucket_code("UPSC-CSE-MAINS-OPT-2019") == 2019
    assert sob.year_from_bucket_code("UPSC-CSE-MAINS-OPT-NOYEAR") is None


# ── _split_one against a fake connection ───────────────────────────────────
# The planning helpers above are pure; these cover the IO layer's ordering
# guarantees, which is where the trigger-abort and idempotency live.


class FakeConn:
    """Records every statement. `existing` seeds already-split rows so a second
    run can be simulated without a database."""

    def __init__(self, questions, *, stimulus_links=0, existing=None):
        self._questions = questions
        self._stimulus_links = stimulus_links
        self._existing = existing or {}
        self.fetched = []
        self.executed = []
        self._next_id = 0

    async def fetch(self, sql, *args):
        self.fetched.append((sql, args))
        if "from public.pyq_questions" in sql:
            return self._questions
        if "from public.pyq_papers" in sql:
            return [
                {"paper_code": c, "id": self._existing[c]}
                for c in args[0]
                if c in self._existing
            ]
        raise AssertionError(f"unexpected fetch: {sql}")

    async def fetchval(self, sql, *args):
        self.fetched.append((sql, args))
        if "pyq_question_stimuli" in sql:
            return self._stimulus_links
        if sql.strip().startswith("insert"):
            self._next_id += 1
            return f"new-{self._next_id}"
        raise AssertionError(f"unexpected fetchval: {sql}")

    async def execute(self, sql, *args):
        self.executed.append((sql, args))


def _run(coro):
    import asyncio

    return asyncio.run(coro)


def test_stimulus_links_abort_the_bucket_before_anything_is_written():
    """Migration 223's trg_pyq_questions_revalidate_paper_move raises on a
    pyq_paper_id move when the question has a pyq_question_stimuli link to a
    stimulus on another paper. Moving the stimuli too is out of scope, so the
    bucket is reported, not patched around — and nothing is written."""
    conn = FakeConn([_q("q1", "History", 1)], stimulus_links=3)
    with pytest.raises(sob.BucketAbort) as exc:
        _run(sob._split_one(conn, _bucket(), live=True))

    msg = str(exc.value)
    assert "pyq_question_stimuli" in msg
    assert "trg_pyq_questions_revalidate_paper_move" in msg
    assert "3 question(s)" in msg
    # No insert, no re-point, no retire.
    assert conn.executed == []
    assert not any(s.strip().startswith("insert") for s, _ in conn.fetched)


def test_the_stimulus_probe_runs_before_any_insert():
    """Ordering is the guarantee: a bucket that would trip the trigger must be
    rejected before the first row exists, or a re-run reuses orphans."""
    conn = FakeConn([_q("q1", "History", 1), _q("q2", "History", 2)])
    _run(sob._split_one(conn, _bucket(), live=True))

    kinds = [
        "stimuli" if "pyq_question_stimuli" in s
        else "insert" if s.strip().startswith("insert")
        else "other"
        for s, _ in conn.fetched
    ]
    assert kinds.index("stimuli") < kinds.index("insert")


def test_dry_run_writes_nothing_but_still_reports_the_full_plan():
    conn = FakeConn([_q("q1", "History", 1), _q("q2", "History", 2)])
    out = _run(sob._split_one(conn, _bucket(), live=False))

    assert conn.executed == []
    assert not any(s.strip().startswith("insert") for s, _ in conn.fetched)
    assert out["created"] == 2 and out["reused"] == 0 and out["moved"] == 2
    assert out["noop"] is False


def test_live_run_inserts_repoints_and_retires_the_bucket():
    conn = FakeConn([_q("q1", "History", 1), _q("q2", "History", 2)])
    out = _run(sob._split_one(conn, _bucket(), live=True))

    assert out["created"] == 2 and out["moved"] == 2
    repoints = [a for s, a in conn.executed if "set pyq_paper_id" in s]
    assert [a[0] for a in repoints] == ["new-1", "new-2"]
    retires = [a for s, a in conn.executed if "'retired', true" in s]
    assert len(retires) == 1
    assert retires[0][0] == BUCKET_ID
    # The bucket row itself survives — retired, never deleted.
    assert not any("delete" in s.lower() for s, _ in conn.executed)


def test_second_run_is_a_noop_matched_on_paper_code():
    questions = [_q("q1", "History", 1), _q("q2", "History", 2)]
    codes = [p["paper_code"] for p in sob.plan_bucket(_bucket(), questions)]
    conn = FakeConn(questions, existing={c: f"old-{i}" for i, c in enumerate(codes)})

    out = _run(sob._split_one(conn, _bucket(), live=True))

    assert out["created"] == 0 and out["reused"] == 2
    assert out["noop"] is True
    assert not any(s.strip().startswith("insert") for s, _ in conn.fetched)
    # Re-pointing to the rows that already exist stays idempotent.
    repoints = [a for s, a in conn.executed if "set pyq_paper_id" in s]
    assert sorted(a[0] for a in repoints) == ["old-0", "old-1"]
