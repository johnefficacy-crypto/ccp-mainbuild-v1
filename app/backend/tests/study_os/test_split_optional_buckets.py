"""Planning contract for scripts/split_optional_buckets.py (PRACTICE-PAPER-01).

The script separates planning from IO precisely so the grouping rules can be
proven without a database. These cover the split shape, idempotency inputs, and
the two abort conditions.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import uuid
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "split_optional_buckets",
    Path(__file__).resolve().parents[4] / "scripts/split_optional_buckets.py",
)
sob = importlib.util.module_from_spec(_SPEC)
sys.modules["split_optional_buckets"] = sob
_SPEC.loader.exec_module(sob)

# asyncpg decodes uuid columns to uuid.UUID objects, NOT strings. The fixtures
# use real UUID objects so the tests exercise the types the script actually
# receives at runtime — a str fixture is what let the --live TypeError through.
BUCKET_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")


def _uuid(n: int) -> uuid.UUID:
    return uuid.UUID(f"bbbbbbbb-0000-0000-0000-{n:012d}")


def _qid(label: str) -> uuid.UUID:
    """Stable UUID per readable label, so question ids are UUID objects too."""
    return uuid.uuid5(uuid.NAMESPACE_OID, label)


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
    return {"id": _qid(qid), "metadata": {"optional_subject": subject,
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
    assert meta["split_from_bucket_id"] == str(BUCKET_ID)
    assert isinstance(meta["split_from_bucket_id"], str)
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
            # RETURNING id on a uuid column gives a uuid.UUID, not a str.
            return _uuid(self._next_id)
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
    assert [a[0] for a in repoints] == [_uuid(1), _uuid(2)]
    retires = [a for s, a in conn.executed if "'retired', true" in s]
    assert len(retires) == 1
    # $1 is a uuid COLUMN parameter — asyncpg encodes uuid.UUID natively there,
    # so it is deliberately NOT stringified.
    assert retires[0][0] == BUCKET_ID
    # $2 is jsonb, so it must already be a JSON string.
    assert json.loads(retires[0][1]) == [str(_uuid(1)), str(_uuid(2))]
    # The bucket row itself survives — retired, never deleted.
    assert not any("delete" in s.lower() for s, _ in conn.executed)


def test_second_run_is_a_noop_matched_on_paper_code():
    questions = [_q("q1", "History", 1), _q("q2", "History", 2)]
    codes = [p["paper_code"] for p in sob.plan_bucket(_bucket(), questions)]
    conn = FakeConn(questions, existing={c: _uuid(100 + i) for i, c in enumerate(codes)})

    out = _run(sob._split_one(conn, _bucket(), live=True))

    assert out["created"] == 0 and out["reused"] == 2
    assert out["noop"] is True
    assert not any(s.strip().startswith("insert") for s, _ in conn.fetched)
    # Re-pointing to the rows that already exist stays idempotent.
    repoints = [a for s, a in conn.executed if "set pyq_paper_id" in s]
    assert sorted(a[0] for a in repoints) == [_uuid(100), _uuid(101)]


# ── the live-path payload builders (PRACTICE-PAPER-02) ─────────────────────
# `--live` crashed here, not in the planner: json.dumps cannot serialise a
# uuid.UUID, and both jsonb payloads carry ids. The planner was green the whole
# time because its fixtures used strings.


def test_every_json_dumps_in_the_script_is_covered_by_these_tests():
    """Guard the audit. If a third jsonb payload appears, this fails and the
    new one has to be built through insert_args/retire_args too."""
    src = Path(sob.__file__).read_text(encoding="utf-8")
    dumps_lines = [
        line.strip() for line in src.splitlines()
        if "json.dumps(" in line and not line.strip().startswith("#")
        and "``json.dumps``" not in line
    ]
    assert dumps_lines == [
        'json.dumps(plan["metadata"]),',
        'json.dumps([uuid_str(p["paper_id"]) for p in planned]),',
    ]


def test_planned_metadata_json_serialises_with_uuid_inputs():
    """The original crash, at the planner boundary: a UUID bucket id landed in
    metadata untouched and blew up at dumps time."""
    planned = sob.plan_bucket(_bucket(), [_q("q1", "History", 1), _q("q2", "History", 2)])
    for plan in planned:
        encoded = json.dumps(plan["metadata"])  # would raise TypeError before the fix
        assert json.loads(encoded)["split_from_bucket_id"] == str(BUCKET_ID)


def test_insert_args_shape_and_types():
    plan = sob.plan_bucket(_bucket(), [_q("q1", "History", 1)])[0]
    args = sob.insert_args(_bucket(), plan)

    assert len(args) == 6
    exam_id, phase_id, cycle_id, year, paper_code, meta_json = args
    assert (exam_id, phase_id, cycle_id) == ("e1", "p1", "c1")
    assert year == 2019
    # paper_code is a COLUMN parameter, because pyq_papers_unique_known_uidx
    # distinguishes the split rows by nothing else.
    assert paper_code == plan["paper_code"] == "UPSC-CSE-MAINS-OPT-2019-HISTORY-P1"
    assert isinstance(meta_json, str)
    assert json.loads(meta_json)["split_from_bucket_id"] == str(BUCKET_ID)


def test_insert_args_keeps_uuid_column_parameters_as_uuid_objects():
    """Only the jsonb payload is stringified. asyncpg encodes uuid.UUID for a
    uuid column natively, and str-ing it here would be a different bug."""
    bucket = _bucket(exam_id=_uuid(7), exam_phase_id=_uuid(8), exam_cycle_id=_uuid(9))
    plan = sob.plan_bucket(bucket, [_q("q1", "History", 1)])[0]
    args = sob.insert_args(bucket, plan)
    assert args[:3] == (_uuid(7), _uuid(8), _uuid(9))
    assert all(isinstance(a, uuid.UUID) for a in args[:3])


def test_retire_args_stringifies_split_into_ids():
    planned = [
        {"paper_id": _uuid(1), "paper_code": "x"},
        {"paper_id": _uuid(2), "paper_code": "y"},
    ]
    bucket_id, split_into_json = sob.retire_args(_bucket(), planned)

    assert bucket_id == BUCKET_ID and isinstance(bucket_id, uuid.UUID)
    decoded = json.loads(split_into_json)  # would raise TypeError before the fix
    assert decoded == [str(_uuid(1)), str(_uuid(2))]
    assert all(isinstance(v, str) for v in decoded)


def test_retire_args_handles_ids_that_are_already_strings():
    """A reused row's id comes from the same uuid column, but a caller passing
    a string must not become 'UUID(...)' or a double-encoded value."""
    _, split_into_json = sob.retire_args(_bucket(), [{"paper_id": "already-a-string"}])
    assert json.loads(split_into_json) == ["already-a-string"]


@pytest.mark.parametrize("value,expected", [
    (_uuid(1), str(_uuid(1))),
    ("plain", "plain"),
    (None, None),
    (7, 7),
])
def test_uuid_str_is_narrow_by_design(value, expected):
    """Not `default=str`: anything that is not a UUID passes through unchanged,
    so an unexpected type still fails loudly instead of being stringified."""
    assert sob.uuid_str(value) == expected
