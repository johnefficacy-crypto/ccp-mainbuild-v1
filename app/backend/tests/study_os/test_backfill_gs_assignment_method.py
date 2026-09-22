"""The stamp contract for scripts/backfill_gs_assignment_method.py.

WHAT THIS REPAIRS. The split moved 957 questions onto 55 papers and wrote
`metadata.gs_paper` on each — which paper it is on — and nothing about HOW that
was decided. `assignment_method` went onto the PAPER, where it is a set over
the whole paper and cannot answer "why is THIS question here". The 27 operator
overrides were applied correctly and then became invisible: a count of
`assignment_method='override'` on demo returned zero.

This backfill recomputes the method for rows that have ALREADY moved and writes
only that stamp. The tests below exist mostly to prove the two negatives: it
never moves a question, and it never invents a method it cannot derive.
"""
from __future__ import annotations

import asyncio
import importlib.util
import sys
import types
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
_SPEC = importlib.util.spec_from_file_location(
    "backfill_gs_assignment_method",
    ROOT / "scripts/backfill_gs_assignment_method.py",
)
bf = importlib.util.module_from_spec(_SPEC)
sys.modules["backfill_gs_assignment_method"] = bf
_SPEC.loader.exec_module(bf)

sgb = bf.sgb
TAG_ONLY = frozenset({2013, 2014})


def _qid(n: int) -> uuid.UUID:
    return uuid.UUID(f"cf790942-0000-0000-0000-{n:012d}")


def _row(n, *, year=2018, metadata=None, question_number=None):
    return {
        "id": _qid(n),
        "pyq_paper_id": uuid.UUID("5466e62f-0000-0000-0000-000000000001"),
        "question_number": question_number if question_number is not None else n,
        "metadata": metadata if metadata is not None else {"gs_paper": "1"},
        "year": year,
        "paper_metadata": {"split_from_bucket_id": "b"},
    }


def _plan(rows, **over):
    kwargs = {
        "tags": {}, "essay_tagged": set(), "overrides": {},
        "tag_only_years": TAG_ONLY,
    }
    kwargs.update(over)
    return bf.plan_stamps(rows, **kwargs)


# ── 1. how the method is derived ───────────────────────────────────────────

def test_an_override_beats_every_other_signal():
    """The 27 rows in the operator sheet. A question can carry a GS tag AND an
    essay tag AND an override — the override is the human's decision and is
    the only one of the three that was made deliberately about this question."""
    assert bf.method_for("q", tag_paper=1, has_essay_tag=True, overridden=True,
                         tag_only_year=False) == "override"
    # Even in a tag-only year: the year's OCR failing says nothing about a
    # placement a person made by hand.
    assert bf.method_for("q", tag_paper=1, has_essay_tag=True, overridden=True,
                         tag_only_year=True) == "override"


def test_a_gs_tag_is_tag_in_a_verified_year_and_tag_only_otherwise():
    assert bf.method_for("q", tag_paper=3, has_essay_tag=False,
                         overridden=False, tag_only_year=False) == "tag"
    assert bf.method_for("q", tag_paper=3, has_essay_tag=False,
                         overridden=False, tag_only_year=True) == "tag_only"


def test_an_essay_tag_places_a_question_with_no_gs_tag():
    """Essay questions carry no GS topic tag — they are not GS topics. Their
    tag lives in `essay_pyq_tags`, which is exactly the statement "this is an
    Essay question"."""
    assert bf.method_for("q", tag_paper=None, has_essay_tag=True,
                         overridden=False, tag_only_year=False) == "essay_tag"


def test_an_essay_tag_does_not_become_tag_only():
    """`tag_only` is a statement about the GS tags a year's OCR failed to
    corroborate. An essay tag is in another table and is not less certain
    because the year's GS pages did not extract."""
    assert bf.method_for("q", tag_paper=None, has_essay_tag=True,
                         overridden=False, tag_only_year=True) == "essay_tag"


def test_a_gs_tag_still_beats_an_essay_tag():
    assert bf.method_for("q", tag_paper=2, has_essay_tag=True,
                         overridden=False, tag_only_year=False) == "tag"


def test_a_row_nothing_explains_gets_no_method_rather_than_a_guess():
    assert bf.method_for("q", tag_paper=None, has_essay_tag=False,
                         overridden=False, tag_only_year=False) is None


# ── 2. the plan ────────────────────────────────────────────────────────────

def test_each_row_is_planned_with_the_method_its_signals_give_it():
    rows = [_row(1), _row(2), _row(3), _row(4)]
    writes, unexplained = _plan(
        rows,
        tags={str(_qid(1)): 1, str(_qid(4)): 2},
        essay_tagged={str(_qid(2))},
        overrides={str(_qid(3)): 3},
    )
    assert dict(writes) == {
        str(_qid(1)): "tag",
        str(_qid(2)): "essay_tag",
        str(_qid(3)): "override",
        str(_qid(4)): "tag",
    }
    assert unexplained == []


def test_2013_and_2014_are_stamped_tag_only_not_tag():
    """They agreed with the OCR on 1 of 93 and 5 of 78 and split anyway, before
    the rule existed. Stamping them `tag` would record them as verified."""
    rows = [_row(1, year=2013), _row(2, year=2014), _row(3, year=2015)]
    writes, _ = _plan(rows, tags={str(_qid(n)): 1 for n in (1, 2, 3)})
    assert dict(writes) == {
        str(_qid(1)): "tag_only",
        str(_qid(2)): "tag_only",
        str(_qid(3)): "tag",
    }


def test_a_tag_only_year_given_on_the_command_line_is_honoured():
    rows = [_row(1, year=2020)]
    writes, _ = _plan(rows, tags={str(_qid(1)): 1},
                      tag_only_years=frozenset({2020}))
    assert writes == [(str(_qid(1)), "tag_only")]


def test_a_year_arriving_as_text_still_resolves():
    """asyncpg gives `year` as an int, but a CSV or a view can give text. The
    tag-only decision must not turn on the column's type."""
    rows = [_row(1, year="2013")]
    writes, _ = _plan(rows, tags={str(_qid(1)): 1})
    assert writes == [(str(_qid(1)), "tag_only")]


def test_a_row_with_no_signal_is_reported_and_never_stamped():
    rows = [_row(1), _row(2)]
    writes, unexplained = _plan(rows, tags={str(_qid(1)): 1})
    assert writes == [(str(_qid(1)), "tag")]
    assert [r["id"] for r in unexplained] == [_qid(2)]


def test_a_row_already_carrying_the_right_method_is_not_rewritten():
    """The run is idempotent. A second pass over a stamped corpus plans
    nothing, so it cannot be told apart from a first pass gone wrong."""
    rows = [_row(1, metadata={"gs_paper": "1", "assignment_method": "tag"})]
    writes, unexplained = _plan(rows, tags={str(_qid(1)): 1})
    assert writes == []
    assert unexplained == []


def test_a_row_carrying_the_wrong_method_is_corrected():
    rows = [_row(1, year=2013,
                 metadata={"gs_paper": "1", "assignment_method": "tag"})]
    writes, _ = _plan(rows, tags={str(_qid(1)): 1})
    assert writes == [(str(_qid(1)), "tag_only")]


def test_metadata_arriving_as_json_text_is_read_not_overwritten():
    rows = [_row(1, metadata='{"gs_paper": "1", "assignment_method": "tag"}')]
    writes, _ = _plan(rows, tags={str(_qid(1)): 1})
    assert writes == []


# ── 3. the statements ──────────────────────────────────────────────────────

def test_the_update_writes_the_stamp_and_nothing_else():
    """THE WHOLE SAFETY ARGUMENT. The split already moved these rows and was
    verified correct — 55 papers, 957 questions, counts exact. This script must
    not be able to move one, so `pyq_paper_id` may not appear in its UPDATE."""
    assert "pyq_paper_id" not in bf._STAMP_SQL
    assert "assignment_method" in bf._STAMP_SQL
    assert bf._STAMP_SQL.strip().startswith("update public.pyq_questions")


def test_nothing_in_the_script_inserts_deletes_or_retires():
    body = (ROOT / "scripts/backfill_gs_assignment_method.py").read_text()
    for forbidden in ("insert into", "delete from", "'retired'"):
        assert forbidden not in body.lower()


def test_the_stamp_merges_into_existing_metadata_rather_than_replacing_it():
    """`gs_paper` and `split_from_bucket_id` are already on these rows and are
    the only record of the split. A `set metadata = jsonb_build_object(...)`
    here would erase them."""
    assert "coalesce(metadata, '{}'::jsonb)" in bf._STAMP_SQL
    assert "||" in bf._STAMP_SQL


def test_only_questions_on_split_papers_are_selected():
    """`split_from_bucket_id` is the mark the split leaves. Without it this
    would reach optional papers, unsplit buckets and hand-made rows."""
    assert "split_from_bucket_id" in bf._MOVED_SQL
    assert "is not null" in bf._MOVED_SQL
    assert "exam_phase_id = $2::uuid" in bf._MOVED_SQL


def test_the_tag_query_reads_primary_tags_only():
    assert "tag_role = 'primary'" in bf._TAGS_SQL


# ── 4. the override sheet ──────────────────────────────────────────────────

def test_the_overrides_default_to_the_same_sheet_the_split_used():
    """A second copy of the path is how the two come to disagree about which
    27 rows a human placed."""
    assert bf.sgb is sgb          # imported, not restated
    assert sgb.OVERRIDES_CSV.name == "gs_split_overrides.csv"
    assert "workbench/audit" in sgb.OVERRIDES_CSV.as_posix()


def test_a_missing_override_sheet_reads_as_no_overrides_not_an_error(tmp_path):
    assert sgb.load_overrides(tmp_path / "absent.csv") == {}


def test_an_override_sheet_typo_is_refused_before_anything_is_written(tmp_path):
    path = tmp_path / "gs_split_overrides.csv"
    path.write_text("question_id,paper,reason\nabc,GS5,typo\n", encoding="utf-8")
    with pytest.raises(sgb.ScopeAbort):
        sgb.load_overrides(path)


# ── 5. the run ─────────────────────────────────────────────────────────────

class FakeConn:
    """Just enough asyncpg to run the script's body against fixtures."""

    def __init__(self, rows, tags, essay):
        self.rows = rows
        self.tags = tags
        self.essay = essay
        self.executed: list[tuple] = []

    async def fetch(self, sql, *args):
        if "split_from_bucket_id" in sql:
            return self.rows
        if "essay_pyq_tags" in sql:
            return [{"question_id": q} for q in self.essay]
        if "pyq_question_topic_tags" in sql:
            return [{"question_id": q, "subject_slug": f"upsc-cse-mains-gs{p}"}
                    for q, p in self.tags.items()]
        raise AssertionError(sql)

    async def execute(self, sql, *args):
        self.executed.append((sql, args))

    def transaction(self):
        conn = self

        class _Txn:
            async def __aenter__(self_inner):
                return conn

            async def __aexit__(self_inner, *exc):
                return False

        return _Txn()

    async def close(self):
        pass


def _run(monkeypatch, tmp_path, conn, *, live, argv_overrides=None):
    fake_asyncpg = types.ModuleType("asyncpg")

    async def _connect(dsn):
        return conn

    fake_asyncpg.connect = _connect
    monkeypatch.setitem(sys.modules, "asyncpg", fake_asyncpg)
    monkeypatch.setenv("DATABASE_URL", "postgresql://fixture")
    return asyncio.run(bf.run(
        live=live,
        overrides_path=argv_overrides or (tmp_path / "absent.csv"),
        tag_only_years=TAG_ONLY,
    ))


def _fixture_conn():
    rows = [_row(1), _row(2), _row(3, year=2013), _row(4)]
    return FakeConn(
        rows,
        tags={str(_qid(1)): 1, str(_qid(3)): 2, str(_qid(4)): 1},
        essay=[str(_qid(2))],
    )


def test_a_dry_run_executes_no_statement_at_all(monkeypatch, tmp_path, capsys):
    conn = _fixture_conn()
    rc = _run(monkeypatch, tmp_path, conn, live=False)
    assert conn.executed == []
    assert rc == 0
    out = capsys.readouterr().out
    assert "DRY RUN — no writes" in out
    assert "4 of 4 moved question(s) to stamp" in out
    assert "essay_tag 1, tag 2, tag_only 1" in out


def test_a_live_run_stamps_every_planned_row_once(monkeypatch, tmp_path):
    conn = _fixture_conn()
    rc = _run(monkeypatch, tmp_path, conn, live=True)
    assert rc == 0
    assert len(conn.executed) == 4
    assert {args[1] for _, args in conn.executed} == {"tag", "essay_tag", "tag_only"}
    assert all(sql is bf._STAMP_SQL for sql, _ in conn.executed)


def test_a_second_live_run_over_a_stamped_corpus_writes_nothing(
    monkeypatch, tmp_path
):
    conn = _fixture_conn()
    _run(monkeypatch, tmp_path, conn, live=True)
    stamped = {qid: method for _, (qid, method) in conn.executed}
    for row in conn.rows:
        method = stamped.get(str(row["id"]))
        if method:
            row["metadata"] = {**row["metadata"], "assignment_method": method}

    again = FakeConn(conn.rows, conn.tags, conn.essay)
    rc = _run(monkeypatch, tmp_path, again, live=True)
    assert again.executed == []
    assert rc == 0


def test_an_unexplained_row_makes_the_run_exit_nonzero(monkeypatch, tmp_path, capsys):
    conn = FakeConn([_row(1), _row(9)], tags={str(_qid(1)): 1}, essay=[])
    rc = _run(monkeypatch, tmp_path, conn, live=False)
    assert rc == 1
    err = capsys.readouterr().err
    assert "no tag, no essay tag and no override" in err
    assert str(_qid(9)) in err


def test_an_absent_override_sheet_says_so_rather_than_reporting_zero(
    monkeypatch, tmp_path, capsys
):
    """"0 overrides" is ambiguous between "there were none" and "I was pointed
    at the wrong file". The demo count of `override` was zero for the second
    reason once already."""
    _run(monkeypatch, tmp_path, _fixture_conn(), live=False)
    assert "does not exist" in capsys.readouterr().err


def test_the_overrides_that_were_applied_are_recovered_from_the_sheet(
    monkeypatch, tmp_path, capsys
):
    """The 27 operator rows, e.g. cf790942… CPEC → 2018-GS3. They are already
    on the right paper; this is the label that should have gone with them."""
    path = tmp_path / "gs_split_overrides.csv"
    path.write_text(
        "question_id,paper,reason\n"
        f"{_qid(1)},GS3,CPEC belongs to international relations\n",
        encoding="utf-8",
    )
    conn = _fixture_conn()
    _run(monkeypatch, tmp_path, conn, live=True, argv_overrides=path)
    by_id = {args[0]: args[1] for _, args in conn.executed}
    assert by_id[str(_qid(1))] == "override"
    assert "1 override(s)" in capsys.readouterr().out


def test_an_empty_corpus_is_reported_and_not_an_error(monkeypatch, tmp_path, capsys):
    conn = FakeConn([], tags={}, essay=[])
    assert _run(monkeypatch, tmp_path, conn, live=True) == 0
    assert "nothing to stamp" in capsys.readouterr().out
    assert conn.executed == []
