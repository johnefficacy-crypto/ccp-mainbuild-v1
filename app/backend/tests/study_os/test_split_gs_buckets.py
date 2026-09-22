"""Assignment and abort contract for scripts/split_gs_buckets.py.

The GS year-buckets carry nothing that says which of the four papers a question
came from, so the script derives it from three independent signals and refuses
to move anything when they disagree. Those rules are pure functions precisely so
they can be proven here, without a database and without the 200 MB OCR cache.

The counts per paper vary year to year, so nothing in the script — and nothing
in these tests — may split by a question-number range.
"""
from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
import uuid
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "split_gs_buckets",
    Path(__file__).resolve().parents[4] / "scripts/split_gs_buckets.py",
)
sgb = importlib.util.module_from_spec(_SPEC)
sys.modules["split_gs_buckets"] = sgb
_SPEC.loader.exec_module(sgb)

YEAR = 2019
# asyncpg decodes uuid columns to uuid.UUID, NOT str. The fixtures use real
# UUID objects so the tests exercise the types the script receives at runtime —
# str fixtures are exactly what let a --live json.dumps TypeError through once.
BUCKET_ID = uuid.UUID("5466e62f-0000-0000-0000-000000000019")


def _qid(label: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_OID, f"gs-{label}")


def _new(n: int) -> uuid.UUID:
    return uuid.UUID(f"cccccccc-0000-0000-0000-{n:012d}")


# Distinctive sentences: each belongs to exactly one paper, so a match is a
# statement about provenance rather than about shared UPSC phrasing.
TEXT = {
    1: "Safeguarding the Indian art heritage is the need of the moment. Comment.",
    2: "The Indian party system is passing through a phase of transition. Analyse.",
    3: "Enumerate the indirect taxes subsumed under the Goods and Services Tax.",
    4: "What do you understand by probity in governance? Illustrate with examples.",
}
ESSAY_TEXT = "Wisdom finds truth. Write an essay of about 1000-1200 words."


def _corpus(*, papers=(1, 2, 3, 4), essay=False, year=YEAR):
    """(year, paper) -> OCR text. Each paper's page contains only its own text."""
    out = {(year, p): sgb._normalise("Section A " + TEXT[p] + " Section B") for p in papers}
    if essay:
        out[(year, sgb.ESSAY)] = sgb._normalise("Section A " + ESSAY_TEXT)
    return out


def _q(paper_or_text, number):
    text = TEXT[paper_or_text] if isinstance(paper_or_text, int) else paper_or_text
    return {"id": _qid(f"{number}"), "question_number": number, "question_text": text}


def _bucket(**over):
    b = {
        "id": BUCKET_ID,
        "exam_id": sgb.EXAM_ID,
        "exam_phase_id": sgb.EXAM_PHASE_ID,
        "exam_cycle_id": None,
        "year": YEAR,
        "paper_code": None,
        "metadata": {"note": "unreliable — never read for assignment"},
    }
    b.update(over)
    return b


def _sitting():
    """One question per paper, in printed order. The smallest honest bucket."""
    questions = [_q(p, p) for p in (1, 2, 3, 4)]
    tags = {str(q["id"]): p for p, q in zip((1, 2, 3, 4), questions)}
    return questions, tags


# ── 1. assignment comes from the primary tag ───────────────────────────────

def test_primary_tag_subject_slug_assigns_the_paper():
    q = _q(1, 1)
    row = sgb.assign_question(q, tag_paper=1, ocr_papers=_corpus()[YEAR, 1] and
                              {p: t for (y, p), t in _corpus().items()})
    assert row["assigned"] == 1
    assert row["method"] == "tag"
    assert row["disagrees"] is False


def test_tag_papers_maps_canonical_slugs_and_ignores_the_empty_shells():
    rows = [
        {"question_id": "q1", "subject_slug": "upsc-cse-mains-gs1"},
        {"question_id": "q2", "subject_slug": "upsc-cse-mains-gs4"},
        {"question_id": "q3", "subject_slug": "upsc-mains-gs2"},      # empty shell
        {"question_id": "q4", "subject_slug": "upsc-mains-essay"},    # empty shell
        {"question_id": "q5", "subject_slug": "upsc-gs-paper-1"},     # empty shell
        {"question_id": "q6", "subject_slug": "indian-polity"},       # not a GS paper
    ]
    assert sgb._tag_papers(rows) == {"q1": 1, "q2": 4}


def test_two_primary_tags_disagreeing_assign_nothing_rather_than_picking_one():
    rows = [
        {"question_id": "q1", "subject_slug": "upsc-cse-mains-gs1"},
        {"question_id": "q1", "subject_slug": "upsc-cse-mains-gs3"},
    ]
    assert sgb._tag_papers(rows) == {}


def test_a_clean_sitting_plans_one_paper_per_gs_with_the_real_counts():
    """Counts come from the questions, never from a number range: GS1 gets three
    questions here and GS2 one, and the plan must say so."""
    questions = [_q(1, 1), _q(1, 2), _q(1, 3), _q(2, 4)]
    tags = {str(q["id"]): (1 if i < 3 else 2) for i, q in enumerate(questions)}

    planned, rows = sgb.plan_bucket(_bucket(), questions, tag_papers=tags, corpus=_corpus())

    assert [p["paper_code"] for p in planned] == [
        "UPSC-CSE-MAINS-GS-2019-GS1",
        "UPSC-CSE-MAINS-GS-2019-GS2",
    ]
    assert [p["question_count"] for p in planned] == [3, 1]
    assert [p["metadata"]["paper_kind"] for p in planned] == ["gs", "gs"]
    assert [p["metadata"]["gs_paper"] for p in planned] == [1, 2]
    moved = [qid for p in planned for qid in p["question_ids"]]
    assert sorted(moved) == sorted(q["id"] for q in questions)
    assert len(moved) == len(set(moved)) == 4
    assert all(r["method"] == "tag" for r in rows)


# ── 2. OCR disagreement aborts the bucket ──────────────────────────────────

def test_ocr_matching_another_paper_while_the_tag_paper_misses_is_a_disagreement():
    row = sgb.assign_question(
        _q(3, 7),  # GS3's text...
        tag_paper=1,  # ...tagged GS1
        ocr_papers={p: t for (y, p), t in _corpus().items()},
    )
    assert row["disagrees"] is True
    assert row["ocr_paper"] == 3 and row["tag_paper"] == 1
    assert row["ocr_score"] >= sgb.OCR_MATCH_CUT
    assert row["tag_score"] < sgb.OCR_MATCH_CUT


def test_one_disagreement_aborts_the_whole_bucket_and_writes_nothing():
    questions, tags = _sitting()
    tags[str(questions[0]["id"])] = 3  # GS1's question tagged GS3

    with pytest.raises(sgb.BucketAbort) as exc:
        sgb.plan_bucket(_bucket(), questions, tag_papers=tags, corpus=_corpus())

    msg = str(exc.value)
    assert "disagreement" in msg
    assert "nothing written for 2019" in msg
    assert sgb.REVIEW_CSV.name in msg


def test_text_that_also_matches_the_tag_paper_is_not_a_disagreement():
    """Whole-paper partial_ratio is generous. A question whose wording clears the
    cut against two papers of one sitting is ambiguous text, not evidence the tag
    is wrong — vetoing on the winning score alone would abort every real bucket."""
    shared = TEXT[2]
    corpus = {(YEAR, 1): sgb._normalise(shared + " and more GS1"),
              (YEAR, 2): sgb._normalise(shared)}
    row = sgb.assign_question(
        {"id": _qid("s"), "question_number": 1, "question_text": shared},
        tag_paper=1,
        ocr_papers={p: t for (y, p), t in corpus.items()},
    )
    assert row["tag_score"] >= sgb.OCR_MATCH_CUT
    assert row["disagrees"] is False


def test_a_year_with_no_verification_at_all_is_refused_as_tag_only():
    """2015 GS4, 2024 and 2025 have no OCR. One signal is not enough to give a
    possibly-fabricated question a real paper's provenance — but the refusal is
    now the tag-only rule's, which a human can lift year by year."""
    questions, tags = _sitting()
    with pytest.raises(sgb.BucketAbort) as exc:
        sgb.plan_bucket(_bucket(), questions, tag_papers=tags, corpus={})
    msg = str(exc.value)
    assert "tag-only" in msg
    assert "nothing to check against" in msg
    assert "--tag-only-years 2019" in msg


def test_a_named_tag_only_year_splits_and_stamps_every_row_tag_only():
    questions, tags = _sitting()
    planned, rows = sgb.plan_bucket(
        _bucket(), questions, tag_papers=tags, corpus={},
        tag_only_years=frozenset({YEAR}),
    )
    assert [p["paper"] for p in planned] == [1, 2, 3, 4]
    # `tag_only`, not `tag`: the row says the tag was the only thing that
    # placed it, which is exactly what 2013 (1/93) and 2014 (5/78) were.
    assert {r["method"] for r in rows} == {"tag_only"}
    assert all(m == "tag_only" for p in planned for m in p["methods"])


# ── 3. untagged questions ──────────────────────────────────────────────────

def test_untagged_question_matching_the_essay_source_becomes_essay():
    questions, tags = _sitting()
    questions.append(_q(ESSAY_TEXT, 5))  # no tag for it

    planned, rows = sgb.plan_bucket(
        _bucket(), questions, tag_papers=tags, corpus=_corpus(essay=True)
    )

    essay = [p for p in planned if p["paper"] == sgb.ESSAY]
    assert len(essay) == 1
    assert essay[0]["paper_code"] == "UPSC-CSE-MAINS-GS-2019-ESSAY"
    assert essay[0]["metadata"]["paper_kind"] == "essay"
    assert essay[0]["metadata"]["gs_paper"] == sgb.ESSAY
    assert essay[0]["question_count"] == 1
    assert [r["method"] for r in rows if r["assigned"] == sgb.ESSAY] == ["ocr_essay"]
    # Essay sorts last, after GS4.
    assert [p["paper"] for p in planned] == [1, 2, 3, 4, sgb.ESSAY]


def test_untagged_question_matching_no_essay_source_is_unassigned_and_aborts():
    questions, tags = _sitting()
    questions.append(_q("A question nobody tagged and no paper contains.", 5))

    with pytest.raises(sgb.BucketAbort) as exc:
        sgb.plan_bucket(_bucket(), questions, tag_papers=tags, corpus=_corpus(essay=True))
    assert "1 unassigned" in str(exc.value)


# ── 4. monotonic order ─────────────────────────────────────────────────────

def test_paper_index_falling_as_question_number_rises_is_flagged():
    rows = [
        {"assigned": 1, "question_number": 1},
        {"assigned": 3, "question_number": 2},
        {"assigned": 2, "question_number": 3},  # GS2 after GS3 — impossible
        {"assigned": 4, "question_number": 4},
    ]
    flagged = sgb.order_violations(rows)
    assert [r["question_number"] for r in flagged] == [3]


def test_repeated_paper_index_is_not_a_violation():
    rows = [{"assigned": 1, "question_number": n} for n in range(1, 21)]
    rows += [{"assigned": 2, "question_number": n} for n in range(21, 41)]
    assert sgb.order_violations(rows) == []


def test_essay_after_gs4_is_in_order_and_essay_before_it_is_not():
    ok = [{"assigned": 4, "question_number": 1}, {"assigned": sgb.ESSAY, "question_number": 2}]
    bad = [{"assigned": sgb.ESSAY, "question_number": 1}, {"assigned": 4, "question_number": 2}]
    assert sgb.order_violations(ok) == []
    assert [r["question_number"] for r in sgb.order_violations(bad)] == [2]


def test_an_out_of_order_bucket_splits_and_records_a_warning():
    """CORRECTED RULE. The check assumed a bucket's `question_number` runs in
    printed paper order. On the real corpus it does not — the dry run rejected
    up to 51 rows in a bucket whose tags the OCR agreed with, against 29
    disagreements in the whole corpus. An assumption that fires that often
    against evidence that agrees is the assumption that is wrong.

    So the drop is still computed and still written to the review sheet, and it
    no longer stops the bucket."""
    questions = [_q(1, 1), _q(3, 2), _q(2, 3), _q(4, 4)]
    tags = {str(q["id"]): p for q, p in zip(questions, (1, 3, 2, 4))}

    planned, rows = sgb.plan_bucket(_bucket(), questions, tag_papers=tags,
                                    corpus=_corpus())

    assert [p["paper"] for p in planned] == [1, 2, 3, 4]
    flagged = [r for r in rows if r["reason"] == "order_warning"]
    assert [r["question_number"] for r in flagged] == [3]


def test_an_order_warning_does_not_stop_a_bucket_but_a_disagreement_does():
    """The two are separated on purpose: one is an assumption about printing
    order, the other is evidence about content."""
    questions = [_q(1, 1), _q(3, 2), _q(2, 3)]
    tags = {str(q["id"]): p for q, p in zip(questions, (1, 3, 2))}
    sgb.plan_bucket(_bucket(), questions, tag_papers=tags, corpus=_corpus())

    tags[str(questions[0]["id"])] = 3  # now GS1's text is tagged GS3
    with pytest.raises(sgb.BucketAbort) as exc:
        sgb.plan_bucket(_bucket(), questions, tag_papers=tags, corpus=_corpus())
    assert "disagreement" in str(exc.value)
    assert "not blocking" in str(exc.value)


# ── 5. UUID serialisation on the live path ─────────────────────────────────

def test_plan_metadata_json_serialises_with_a_uuid_bucket_id():
    questions, tags = _sitting()
    planned, _ = sgb.plan_bucket(_bucket(), questions, tag_papers=tags, corpus=_corpus())
    for plan in planned:
        assert plan["metadata"]["split_from_bucket_id"] == str(BUCKET_ID)
        assert isinstance(plan["metadata"]["split_from_bucket_id"], str)
        json.dumps(plan["metadata"])  # would raise TypeError on a raw UUID


def test_insert_args_build_a_jsonb_string_and_keep_the_column_types_native():
    questions, tags = _sitting()
    planned, _ = sgb.plan_bucket(_bucket(), questions, tag_papers=tags, corpus=_corpus())
    args = sgb.insert_args(_bucket(), planned[0])

    exam_id, phase_id, cycle_id, year, paper_code, meta_json = args
    assert (exam_id, phase_id) == (sgb.EXAM_ID, sgb.EXAM_PHASE_ID)
    assert year == YEAR
    # paper_code is the COLUMN, not only metadata: pyq_papers_unique_known_uidx
    # is (exam_id, exam_phase_id, year, paper_date, shift, paper_code), and the
    # four papers of one sitting share everything but the code.
    assert paper_code == "UPSC-CSE-MAINS-GS-2019-GS1"
    assert isinstance(meta_json, str)
    assert json.loads(meta_json)["paper_code"] == paper_code


def test_retire_args_stringify_ids_for_jsonb_but_not_the_uuid_column():
    planned = [{"paper_id": _new(1)}, {"paper_id": _new(2)}]
    bucket_id, split_into = sgb.retire_args(_bucket(), planned)

    # $1 is a uuid column parameter — asyncpg encodes uuid.UUID natively there.
    assert bucket_id == BUCKET_ID and isinstance(bucket_id, uuid.UUID)
    # $2 is jsonb, so it must already be a JSON string of strings.
    assert json.loads(split_into) == [str(_new(1)), str(_new(2))]


def test_uuid_str_is_narrow_and_leaves_other_types_alone():
    assert sgb.uuid_str(BUCKET_ID) == str(BUCKET_ID)
    assert sgb.uuid_str("already-a-string") == "already-a-string"
    assert sgb.uuid_str(None) is None
    assert sgb.uuid_str(2019) == 2019  # not "2019" — no blanket default=str


# ── 6. scope ───────────────────────────────────────────────────────────────

def _row(**over):
    r = {"id": _new(7), "year": YEAR, "paper_code": None, "metadata": {}}
    r.update(over)
    return r


def test_scope_accepts_an_unsplit_bucket():
    assert sgb.scope_violation(_row()) is None
    assert sgb.is_in_scope(_row()) is True


@pytest.mark.parametrize(
    "row, fragment",
    [
        (_row(metadata={"split_from_bucket_id": str(BUCKET_ID)}), "split_from_bucket_id"),
        (_row(paper_code="UPSC-CSE-MAINS-GS-2019-GS1"), "paper_code"),
        (_row(metadata={"paper_code": "UPSC-CSE-MAINS-GS-2019-GS1"}), "paper_code"),
        (_row(metadata={"retired": True}), "retired"),
        (_row(metadata={"corpus_half": "thematic"}), "corpus_half"),
        (_row(year=None), "no year"),
    ],
)
def test_scope_rejects_rows_that_are_not_unsplit_buckets(row, fragment):
    why = sgb.scope_violation(row)
    assert why is not None and fragment in why
    assert sgb.is_in_scope(row) is False


def test_scope_abort_names_every_offender_and_is_not_skippable():
    rows = [
        _row(),
        _row(year=2018, paper_code="UPSC-CSE-MAINS-GS-2018-GS2"),
        _row(year=2017, metadata={"retired": True}),
    ]
    with pytest.raises(sgb.ScopeAbort) as exc:
        sgb.assert_bucket_scope(rows)

    msg = str(exc.value)
    assert "nothing was written" in msg
    assert "2018" in msg and "2017" in msg
    # A ScopeAbort stops the run; a BucketAbort only skips one bucket. The
    # caller distinguishes them by type, so they must not share one.
    assert not isinstance(exc.value, sgb.BucketAbort)


def test_scope_reads_metadata_from_json_text_as_well_as_a_dict():
    assert sgb.scope_violation(_row(metadata='{"retired": true}')) == "retired"
    assert sgb.as_metadata("not json") == {}
    assert sgb.as_metadata(None) == {}


def test_the_bucket_query_is_explicit_and_never_prefix_matches():
    sql = sgb._BUCKET_SQL.lower()
    assert "like" not in sql and "similar to" not in sql and "~" not in sql
    for clause in (
        "p.paper_code is null",
        "metadata->>'paper_code' is null",
        "metadata->>'corpus_half' is null",
        "metadata->>'split_from_bucket_id' is null",
        "'retired')::boolean, false) is not true",
    ):
        assert clause in sql


# ── 7. _split_one and two-run idempotency ──────────────────────────────────


class FakeDb:
    """Papers and questions as rows, mutated exactly as the live path does."""

    def __init__(self, papers, questions):
        self.papers = [dict(p) for p in papers]
        self.questions = [dict(q) for q in questions]
        self.inserts = 0
        self._n = 0

    def select_buckets(self):
        return [
            p for p in self.papers
            if sgb.is_in_scope(p)
            and any(q["pyq_paper_id"] == p["id"] for q in self.questions)
        ]

    async def fetch(self, sql, *args):
        if "from public.pyq_questions" in sql and "topic_tags" not in sql:
            return sorted(
                (q for q in self.questions if q["pyq_paper_id"] == args[0]),
                key=lambda q: q["question_number"],
            )
        if "essay_pyq_tags" in sql:
            return [{"question_id": str(q["id"])}
                    for q in self.questions
                    if q["pyq_paper_id"] == args[0] and q.get("essay")]
        if "pyq_question_topic_tags" in sql:
            return [
                {"question_id": str(q["id"]), "subject_slug": f"upsc-cse-mains-gs{q['gs']}"}
                for q in self.questions
                if q["pyq_paper_id"] == args[0] and q.get("gs")
            ]
        if "from public.pyq_papers" in sql:
            wanted = set(args[0])
            return [{"paper_code": p["paper_code"], "id": p["id"]}
                    for p in self.papers if p["paper_code"] in wanted]
        raise AssertionError(sql)

    async def fetchval(self, sql, *args):
        if "pyq_question_stimuli" in sql:
            return 0
        if sql.strip().startswith("insert"):
            self.inserts += 1
            self._n += 1
            new_id = _new(900 + self._n)
            exam_id, phase_id, cycle_id, year, paper_code, meta_json = args
            self.papers.append({
                "id": new_id, "exam_id": exam_id, "exam_phase_id": phase_id,
                "exam_cycle_id": cycle_id, "year": year, "paper_code": paper_code,
                "trust_status": "pending", "metadata": json.loads(meta_json),
            })
            return new_id
        raise AssertionError(sql)

    async def execute(self, sql, *args):
        if "set pyq_paper_id" in sql:
            target, label, qids, methods, scores = args
            # Mirrors the UPDATE's unnest: the three arrays are parallel, and
            # a null score is dropped rather than stored (jsonb_strip_nulls).
            by_id = dict(zip(qids, zip(methods, scores)))
            for q in self.questions:
                if q["id"] in by_id:
                    method, score = by_id[q["id"]]
                    stamp = {"gs_paper": label, "assignment_method": method}
                    if score is not None:
                        stamp["ocr_score"] = score
                    q["pyq_paper_id"] = target
                    q["metadata"] = {**(q.get("metadata") or {}), **stamp}
            return
        if "'retired', true" in sql:
            bucket_id, split_into_json = args
            for p in self.papers:
                if p["id"] == bucket_id:
                    p["metadata"] = {**sgb.as_metadata(p["metadata"]),
                                     "retired": True,
                                     "split_into": json.loads(split_into_json)}
            return
        raise AssertionError(sql)


def _demo_db():
    questions = [
        {**_q(p, n), "pyq_paper_id": BUCKET_ID, "gs": p, "metadata": {}}
        for n, p in enumerate((1, 1, 2, 3, 4), start=1)
    ]
    # Two GS1 questions need distinct ids; _q keys on the number, so they are.
    return FakeDb([_bucket()], questions)


def _pass(db, corpus):
    """One run over the whole scope, mirroring run()'s body."""
    selected = db.select_buckets()
    sgb.assert_bucket_scope(selected)
    created = moved = 0
    for bucket in selected:
        out = asyncio.run(sgb._split_one(db, bucket, live=True, corpus=corpus))
        created += out["created"]
        moved += out["moved"]
    return {"selected": len(selected), "created": created, "moved": moved}


def test_live_run_inserts_repoints_and_retires_the_bucket():
    db = _demo_db()
    out = _pass(db, _corpus())

    assert out == {"selected": 1, "created": 4, "moved": 5}
    # The bucket row survives — retired, never deleted.
    bucket = next(p for p in db.papers if p["id"] == BUCKET_ID)
    assert sgb.as_metadata(bucket["metadata"])["retired"] is True
    assert len(sgb.as_metadata(bucket["metadata"])["split_into"]) == 4
    assert all(isinstance(i, str) for i in sgb.as_metadata(bucket["metadata"])["split_into"])
    # Every question left the bucket and carries its paper stamp.
    assert not any(q["pyq_paper_id"] == BUCKET_ID for q in db.questions)
    assert [q["metadata"]["gs_paper"] for q in db.questions] == ["1", "1", "2", "3", "4"]
    assert all(p["trust_status"] == "pending" for p in db.papers if p["id"] != BUCKET_ID)


def test_dry_run_writes_nothing_but_reports_the_full_plan():
    db = _demo_db()
    out = asyncio.run(sgb._split_one(db, _bucket(), live=False, corpus=_corpus()))

    assert db.inserts == 0
    assert out["created"] == 4 and out["reused"] == 0 and out["moved"] == 5
    assert all(q["pyq_paper_id"] == BUCKET_ID for q in db.questions)


def test_stimulus_links_abort_the_bucket_before_anything_is_written():
    """Migration 223's trg_pyq_questions_revalidate_paper_move refuses a
    pyq_paper_id move when the question links to a stimulus on another paper.
    Moving stimuli is out of scope, so the bucket is reported, not patched."""
    db = _demo_db()

    async def stimuli(sql, *args):
        return 3 if "pyq_question_stimuli" in sql else 0
    db.fetchval = stimuli

    with pytest.raises(sgb.BucketAbort) as exc:
        asyncio.run(sgb._split_one(db, _bucket(), live=True, corpus=_corpus()))
    assert "trg_pyq_questions_revalidate_paper_move" in str(exc.value)
    assert db.inserts == 0


def test_second_run_over_run_one_state_selects_nothing_and_writes_nothing():
    """The idempotency proof: run 1's OUTPUT, fed back as run 2's INPUT, must
    select nothing — 0 selected, 0 created, 0 moved."""
    db = _demo_db()
    corpus = _corpus()

    first = _pass(db, corpus)
    assert first == {"selected": 1, "created": 4, "moved": 5}
    assert len(db.papers) == 5  # the bucket plus the four papers it made

    second = _pass(db, corpus)
    assert second == {"selected": 0, "created": 0, "moved": 0}
    assert len(db.papers) == 5


def test_run_two_rejects_the_produced_rows_for_every_reason_independently():
    """Shape and lineage both. Either guard alone would stop the re-split, so
    removing one still fails a test rather than silently doubling the corpus."""
    db = _demo_db()
    _pass(db, _corpus())

    splits = [p for p in db.papers if p["id"] != BUCKET_ID]
    assert len(splits) == 4
    for p in splits:
        meta = sgb.as_metadata(p["metadata"])
        assert meta["split_from_bucket_id"] == str(BUCKET_ID)
        assert p["paper_code"] == meta["paper_code"]
        assert sgb.scope_violation(p) is not None
    assert sgb.scope_violation(next(p for p in db.papers if p["id"] == BUCKET_ID)) == "retired"


# ── 8. reporting ───────────────────────────────────────────────────────────

def test_summary_line_counts_each_category():
    questions, tags = _sitting()
    questions.append(_q(ESSAY_TEXT, 5))
    _, rows = sgb.plan_bucket(_bucket(), questions, tag_papers=tags, corpus=_corpus(essay=True))

    line = sgb.summarise(YEAR, rows)
    assert "2019" in line
    assert "tag-assigned 4" in line
    assert "OCR-agreed 4" in line
    assert "disagreements 0" in line
    assert "untagged 1" in line
    assert "essay 1" in line


def test_review_csv_carries_the_evidence_for_every_row(tmp_path, monkeypatch):
    questions, tags = _sitting()
    _, rows = sgb.plan_bucket(_bucket(), questions, tag_papers=tags, corpus=_corpus())

    out = tmp_path / "gs_split_review.csv"
    monkeypatch.setattr(sgb, "REVIEW_CSV", out)
    sgb._write_review([{**r, "year": YEAR} for r in rows])

    import csv
    got = list(csv.DictReader(out.read_text(encoding="utf-8-sig").splitlines()))
    assert len(got) == 4
    assert got[0]["question_id"] == str(questions[0]["id"])  # UUID, not repr'd
    assert got[0]["tag_paper"] == "1"
    assert float(got[0]["ocr_score"]) >= sgb.OCR_MATCH_CUT
    assert got[0]["excerpt"] == TEXT[1][:sgb.REVIEW_EXCERPT_CHARS]
    # A clean row carries an empty reason rather than being left out: the sheet
    # is the whole bucket, so a reviewer can see what was NOT flagged too.
    assert got[0]["reason"] == ""
    assert list(got[0]) == ["year", "question_id", "question_number", "tag_paper",
                            "ocr_paper", "ocr_score", "method",
                            "verified_against", "reason", "excerpt"]


def test_paper_code_is_deterministic_and_year_scoped():
    assert sgb.paper_code_for(2019, 1) == "UPSC-CSE-MAINS-GS-2019-GS1"
    assert sgb.paper_code_for(2013, 4) == "UPSC-CSE-MAINS-GS-2013-GS4"
    assert sgb.paper_code_for(2019, sgb.ESSAY) == "UPSC-CSE-MAINS-GS-2019-ESSAY"


# ── 9. Essay comes from its own tag table ──────────────────────────────────
#
# THE BUG THE DRY RUN FOUND. 13 of 13 buckets aborted, ~8 unassigned per year,
# 100 in total. Every one was an Essay question: they carry no GS topic tag —
# they are not GS topics — so the first pass read them as untagged, and essay
# OCR exists for 2026 alone. Their tag was never missing. It was in
# `essay_pyq_tags`, which IS the statement "this is an Essay question".

def test_an_essay_tagged_question_is_essay_without_any_ocr():
    """Twelve of the thirteen years have no essay page at all."""
    row = sgb.assign_question(
        {"id": _qid("e"), "question_number": 9, "question_text": ESSAY_TEXT},
        tag_paper=None,
        ocr_papers={p: t for (y, p), t in _corpus().items()},  # GS pages only
        has_essay_tag=True,
    )
    assert row["assigned"] == sgb.ESSAY
    assert row["method"] == "essay_tag"
    assert row["disagrees"] is False


def test_the_essay_tag_resolves_the_unassigned_rows_that_blocked_every_bucket():
    questions, tags = _sitting()
    essays = [_q(ESSAY_TEXT, n) for n in (5, 6, 7, 8)]
    questions += essays
    essay_ids = {str(q["id"]) for q in essays}

    planned, rows = sgb.plan_bucket(
        _bucket(), questions, tag_papers=tags, corpus=_corpus(),
        essay_tagged=essay_ids,
    )

    assert [r for r in rows if r["assigned"] is None] == []
    essay_paper = next(p for p in planned if p["paper"] == sgb.ESSAY)
    assert essay_paper["question_count"] == 4
    assert essay_paper["metadata"]["assignment_method"] == ["essay_tag"]


def test_a_gs_tag_still_beats_an_essay_tag():
    """A question carrying both is a GS question someone also filed under an
    essay theme; the GS tag is the one that names a paper."""
    row = sgb.assign_question(
        _q(2, 1), tag_paper=2,
        ocr_papers={p: t for (y, p), t in _corpus().items()},
        has_essay_tag=True,
    )
    assert row["assigned"] == 2 and row["method"] == "tag"


def test_the_essay_page_verifies_the_essay_tag_where_one_exists():
    """2026 is the one year with an essay page. A GS page matching this text
    while the essay page does not is the same disagreement the tag path
    refuses on."""
    corpus = _corpus(essay=True)
    row = sgb.assign_question(
        _q(3, 1),  # GS3's text...
        tag_paper=None,
        ocr_papers={p: t for (y, p), t in corpus.items()},
        has_essay_tag=True,  # ...claimed as Essay
    )
    assert row["disagrees"] is True


def test_no_essay_page_means_no_veto_on_the_essay_tag():
    """An absent page is not evidence. Without this, the twelve years with no
    essay OCR would abort on the very rows the tag just resolved."""
    row = sgb.assign_question(
        _q(3, 1), tag_paper=None,
        ocr_papers={p: t for (y, p), t in _corpus().items()},  # no essay page
        has_essay_tag=True,
    )
    assert row["assigned"] == sgb.ESSAY and row["disagrees"] is False


def test_an_untagged_question_with_no_essay_tag_is_still_unassigned():
    """The rule widened by exactly one table, not into a catch-all."""
    questions, tags = _sitting()
    questions.append(_q("A question nobody tagged anywhere.", 5))
    with pytest.raises(sgb.BucketAbort) as exc:
        sgb.plan_bucket(_bucket(), questions, tag_papers=tags, corpus=_corpus())
    assert "1 unassigned" in str(exc.value)


# ── 10. human overrides ────────────────────────────────────────────────────

def _overrides_csv(tmp_path, rows):
    path = tmp_path / "gs_split_overrides.csv"
    lines = ["question_id,paper,reason"]
    lines += [f"{qid},{paper},{reason}" for qid, paper, reason in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_an_override_beats_the_tag_and_the_ocr(tmp_path):
    row = sgb.assign_question(
        _q(1, 1), tag_paper=1,
        ocr_papers={p: t for (y, p), t in _corpus().items()},
        override=4,
    )
    assert row["assigned"] == 4
    assert row["method"] == "override"
    assert row["disagrees"] is False


def test_an_override_resolves_a_row_the_signals_could_not(tmp_path):
    questions, tags = _sitting()
    questions.append(_q("A question nobody tagged anywhere.", 5))
    overrides = {str(questions[-1]["id"]): sgb.ESSAY}

    planned, rows = sgb.plan_bucket(
        _bucket(), questions, tag_papers=tags, corpus=_corpus(),
        overrides=overrides,
    )
    assert [r for r in rows if r["assigned"] is None] == []
    essay = next(p for p in planned if p["paper"] == sgb.ESSAY)
    assert essay["metadata"]["assignment_method"] == ["override"]


def test_an_override_is_named_in_the_papers_metadata(tmp_path):
    """The row says how it was decided rather than implying the signals
    agreed."""
    questions, tags = _sitting()
    planned, _ = sgb.plan_bucket(
        _bucket(), questions, tag_papers=tags, corpus=_corpus(),
        overrides={str(questions[0]["id"]): 1},
    )
    gs1 = next(p for p in planned if p["paper"] == 1)
    assert "override" in gs1["metadata"]["assignment_method"]


def test_the_override_sheet_reads_every_paper_name(tmp_path):
    ids = [str(_qid(str(i))) for i in range(5)]
    path = _overrides_csv(tmp_path, [
        (ids[0], "GS1", "read the paper"),
        (ids[1], "GS4", "ethics case study"),
        (ids[2], "ESSAY", "it is an essay"),
        (ids[3], "gs2", "lowercase is fine"),
        (ids[4], " ESSAY ", "whitespace is fine"),
    ])
    got = sgb.load_overrides(path)
    assert got == {ids[0]: 1, ids[1]: 4, ids[2]: sgb.ESSAY, ids[3]: 2,
                   ids[4]: sgb.ESSAY}


def test_a_missing_override_sheet_is_the_normal_case(tmp_path):
    assert sgb.load_overrides(tmp_path / "nothing.csv") == {}


def test_a_typo_in_the_override_sheet_is_refused_loudly(tmp_path):
    """A typo in an override is a human decision that did not happen."""
    path = _overrides_csv(tmp_path, [(str(_qid("x")), "GS5", "no such paper")])
    with pytest.raises(sgb.ScopeAbort) as exc:
        sgb.load_overrides(path)
    assert "GS5" in str(exc.value)
    assert "line 2" in str(exc.value)


def test_an_override_row_with_no_question_id_is_skipped(tmp_path):
    path = _overrides_csv(tmp_path, [("", "GS1", "blank line")])
    assert sgb.load_overrides(path) == {}


# ── 11. the review sheet is written on a dry run ───────────────────────────
#
# 13 aborts and 0 rows on disk: the operator was told something was wrong and
# given no way to see what. The rows ride on the exception now.

def test_the_abort_carries_its_review_rows():
    questions, tags = _sitting()
    questions.append(_q("Nobody tagged this.", 5))
    with pytest.raises(sgb.BucketAbort) as exc:
        sgb.plan_bucket(_bucket(), questions, tag_papers=tags, corpus=_corpus())

    assert len(exc.value.rows) == 5           # the WHOLE bucket, not just the bad row
    reasons = {r["reason"] for r in exc.value.rows}
    assert "unassigned" in reasons and "" in reasons


def test_every_row_carries_exactly_one_reason():
    questions, tags = _sitting()
    _, rows = sgb.plan_bucket(_bucket(), questions, tag_papers=tags, corpus=_corpus())
    assert all(r["reason"] in {"", "unassigned", "disagreement", "order_warning"}
               for r in rows)


def test_a_disagreement_outranks_an_order_warning_in_the_reason():
    """One reason per row, and the blocking one is the one that gets said."""
    questions, tags = _sitting()
    tags[str(questions[0]["id"])] = 3
    with pytest.raises(sgb.BucketAbort) as exc:
        sgb.plan_bucket(_bucket(), questions, tag_papers=tags, corpus=_corpus())
    flagged = [r for r in exc.value.rows if r["reason"]]
    assert all(r["reason"] == "disagreement" for r in flagged if r["disagrees"])


def test_the_review_sheet_is_written_even_with_nothing_to_report(tmp_path, monkeypatch):
    """A stale sheet from a previous run is worse than an empty one."""
    out = tmp_path / "gs_split_review.csv"
    monkeypatch.setattr(sgb, "REVIEW_CSV", out)
    sgb._write_review([])
    assert out.is_file()
    header = out.read_text(encoding="utf-8-sig").splitlines()[0]
    assert header.startswith("year,question_id,question_number")


def test_the_review_sheet_records_the_reason_for_each_flagged_row(tmp_path, monkeypatch):
    questions, tags = _sitting()
    questions.append(_q("Nobody tagged this.", 5))
    with pytest.raises(sgb.BucketAbort) as exc:
        sgb.plan_bucket(_bucket(), questions, tag_papers=tags, corpus=_corpus())
    rows = exc.value.rows

    out = tmp_path / "gs_split_review.csv"
    monkeypatch.setattr(sgb, "REVIEW_CSV", out)
    sgb._write_review([{**r, "year": YEAR} for r in rows])

    import csv
    got = list(csv.DictReader(out.read_text(encoding="utf-8-sig").splitlines()))
    assert len(got) == 5
    assert [r["reason"] for r in got].count("unassigned") == 1
    assert all(r["year"] == str(YEAR) for r in got)


def test_the_excerpt_is_the_briefs_eighty_characters():
    long_text = "Examine " + ("the nature of sovereignty in a globalised order " * 5)
    row = sgb.assign_question({"id": _qid("l"), "question_number": 1,
                               "question_text": long_text},
                              tag_paper=1, ocr_papers={})
    assert len(row["excerpt"]) == 80 == sgb.REVIEW_EXCERPT_CHARS


# ── 9. the assignment stamp ────────────────────────────────────────────────
#
# THE BUG THIS SECTION EXISTS FOR. The split moved 957 questions and stamped
# each one with `gs_paper` — which paper it is on — and nothing about HOW that
# was decided. `assignment_method` went onto the PAPER, where it is a set over
# the whole paper and cannot answer "why is THIS question here". The 27
# operator overrides were applied correctly and then became invisible:
# `assignment_method='override'` counted zero on demo.

def test_every_moved_question_carries_the_method_that_placed_it():
    db = _demo_db()
    _pass(db, _corpus())
    for q in db.questions:
        assert q["metadata"]["assignment_method"] == "tag"
        # `gs_paper` is the label column, so it is text — unchanged by this PR.
        assert q["metadata"]["gs_paper"] in {"1", "2", "3", "4"}


def test_an_overridden_question_carries_override_on_the_question_itself(tmp_path):
    db = _demo_db()
    moved = db.questions[2]           # tagged GS2, hand-placed onto GS3
    overrides = {str(moved["id"]): 3}
    for bucket in db.select_buckets():
        asyncio.run(sgb._split_one(db, bucket, live=True, corpus=_corpus(),
                                   overrides=overrides))
    assert moved["metadata"]["assignment_method"] == "override"
    assert moved["metadata"]["gs_paper"] == "3"
    # Every other row keeps its own method — the stamp is per question, not a
    # property of the paper the override happened to land on.
    assert {q["metadata"]["assignment_method"] for q in db.questions
            if q["id"] != moved["id"]} == {"tag"}


def test_the_ocr_score_is_stamped_where_one_was_computed():
    db = _demo_db()
    _pass(db, _corpus())
    for q in db.questions:
        assert q["metadata"]["ocr_score"] >= sgb.OCR_MATCH_CUT


def test_a_question_nothing_scored_carries_no_ocr_score_key_at_all():
    """A 0.0 there would read as "scored, and scored zero"; the absence is the
    honest statement. 2024 and 2025 have no OCR page at all."""
    db = _demo_db()
    for bucket in db.select_buckets():
        asyncio.run(sgb._split_one(db, bucket, live=True, corpus={},
                                   tag_only_years=frozenset({YEAR})))
    for q in db.questions:
        assert "ocr_score" not in q["metadata"]
        assert q["metadata"]["assignment_method"] == "tag_only"


def test_the_essay_tag_stamps_essay_tag_not_tag():
    questions, tags = _sitting()
    essay = _q(ESSAY_TEXT, 5)
    questions.append(essay)
    planned, rows = sgb.plan_bucket(
        _bucket(), questions, tag_papers=tags, corpus=_corpus(essay=True),
        essay_tagged={str(essay["id"])},
    )
    by_paper = {p["paper"]: p for p in planned}
    assert by_paper[sgb.ESSAY]["methods"] == ["essay_tag"]


def test_the_method_arrays_stay_parallel_to_the_question_ids():
    """The UPDATE zips these three arrays by position. A plan whose arrays are
    built in different orders would stamp questions with each other's methods,
    which is worse than not stamping at all."""
    questions, tags = _sitting()
    planned, rows = sgb.plan_bucket(_bucket(), questions, tag_papers=tags,
                                    corpus=_corpus())
    by_id = {r["id"]: r for r in rows}
    for plan in planned:
        assert len(plan["methods"]) == len(plan["question_ids"])
        assert len(plan["ocr_scores"]) == len(plan["question_ids"])
        for qid, method, score in zip(plan["question_ids"], plan["methods"],
                                      plan["ocr_scores"]):
            assert method == by_id[qid]["method"]
            assert score == by_id[qid]["ocr_score"]


# ── 10. the verdict sheet: verification without OCR ────────────────────────

def _verdict_csv(tmp_path, rows):
    path = tmp_path / "gs_2024_2025_verdict.csv"
    lines = ["year,paper,global_number,verdict,best_score"]
    lines += [f"{y},{p},{n},{v},95" for y, p, n, v in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_the_verdict_sheet_reads_only_corroborated_rows(tmp_path):
    """`unverifiable` (2024 GS4, no raw DOCX) and `orphan` say the text was
    never matched, so the paper is the source file's word alone — which is
    what the tag already is. One claim repeated twice is not two signals."""
    path = _verdict_csv(tmp_path, [
        (2024, "GS1", 1, "exact"),
        (2024, "GS2", 2, "variant"),
        (2024, "GS4", 3, "unverifiable"),
        (2025, "GS3", 4, "orphan"),
    ])
    assert sgb.load_verdict_papers(path) == {(2024, 1): 1, (2024, 2): 2}


def test_a_global_number_shared_by_sub_parts_resolves_to_one_paper(tmp_path):
    """`global_number` is not unique — a question with sub-parts shares one —
    but every duplicate names the same paper, so the mapping is well defined
    even though it is not injective."""
    path = _verdict_csv(tmp_path, [
        (2024, "GS4", 11, "exact"),
        (2024, "GS4", 11, "exact"),
    ])
    assert sgb.load_verdict_papers(path) == {(2024, 11): 4}


def test_a_global_number_claimed_by_two_papers_aborts_the_whole_run(tmp_path):
    path = _verdict_csv(tmp_path, [
        (2024, "GS1", 7, "exact"),
        (2024, "GS3", 7, "variant"),
    ])
    with pytest.raises(sgb.ScopeAbort) as exc:
        sgb.load_verdict_papers(path)
    assert "disagrees with itself" in str(exc.value)


def test_a_missing_verdict_sheet_is_not_an_error(tmp_path):
    assert sgb.load_verdict_papers(tmp_path / "absent.csv") == {}


def test_the_verdict_sheet_reads_the_essay_paper(tmp_path):
    path = _verdict_csv(tmp_path, [(2025, "ESSAY", 1, "exact")])
    assert sgb.load_verdict_papers(path) == {(2025, 1): sgb.ESSAY}


def test_the_verdict_verifies_a_year_that_has_no_ocr_at_all():
    """2024 and 2025 aborted as "no OCR". They are not tag-only: the DOCX
    reconciliation corroborates 60/79 and 75/79 of them, both far above the
    50% bar, so they have a real second signal — just not an optical one."""
    questions, tags = _sitting()
    verdicts = {(YEAR, p): p for p in (1, 2, 3, 4)}
    planned, rows = sgb.plan_bucket(_bucket(), questions, tag_papers=tags,
                                    corpus={}, verdict_papers=verdicts)
    assert [p["paper"] for p in planned] == [1, 2, 3, 4]
    # `tag`, not `tag_only` — the year WAS verified, by the verdict sheet.
    assert {r["method"] for r in rows} == {"tag"}
    assert [r["verified_against"] for r in rows] == [1, 2, 3, 4]


def test_a_verdict_contradicting_the_tag_is_a_disagreement():
    questions, tags = _sitting()
    verdicts = {(YEAR, p): p for p in (1, 2, 3, 4)}
    verdicts[(YEAR, 3)] = 1
    with pytest.raises(sgb.BucketAbort) as exc:
        sgb.plan_bucket(_bucket(), questions, tag_papers=tags, corpus={},
                        verdict_papers=verdicts)
    assert "1 tag/OCR disagreement" in str(exc.value)
    assert [r["disagrees"] for r in exc.value.rows] == [False, False, True, False]


def test_the_verdict_replaces_ocr_rather_than_competing_with_it():
    """Where both exist the verdict wins, because it read the official DOCX and
    the OCR read a scan. They never actually compete — the verdict sheet covers
    2024/2025 and those years have no OCR — but the precedence must be stated."""
    row = sgb.assign_question(_q(1, 1), tag_paper=1,
                              ocr_papers=sgb.papers_for_year(_corpus(), YEAR),
                              verdict_paper=1)
    assert row["verified_against"] == 1
    assert row["ocr_paper"] == 1          # the OCR is still recorded
    assert row["disagrees"] is False


def test_a_question_the_verdict_never_placed_is_not_counted_against_the_tags():
    """2024's GS4 has no raw DOCX, so 19 of its 79 rows are `unverifiable`. An
    absence of evidence must not read as evidence against."""
    questions, tags = _sitting()
    verdicts = {(YEAR, 1): 1, (YEAR, 2): 2}    # 3 and 4 uncorroborated
    planned, rows = sgb.plan_bucket(_bucket(), questions, tag_papers=tags,
                                    corpus={}, verdict_papers=verdicts)
    assert sgb.agreement_rate(rows) == (2, 2)
    assert len(planned) == 4


# ── 11. the tag-only rule, one rule for every year ─────────────────────────

def test_agreement_rate_counts_only_what_the_signal_reached():
    rows = [
        {"tag_paper": 1, "verified_against": 1},
        {"tag_paper": 3, "verified_against": 2},
        {"tag_paper": 4, "verified_against": None},   # the signal had no opinion
        {"tag_paper": None, "verified_against": 2},   # an override, not a tag
    ]
    assert sgb.agreement_rate(rows) == (1, 2)


def test_agreement_rate_of_a_year_nothing_could_check_is_zero_over_zero():
    assert sgb.agreement_rate([{"tag_paper": 1, "verified_against": None}]) == (0, 0)


def test_a_year_agreeing_below_half_is_refused_with_its_rate():
    """2013 agreed on 1 of 93 and 2014 on 5 of 78. Both split anyway, stamped
    `tag` — which said they were verified. They were not.

    The shape is the real one: each paper's OCR page matches a different
    question, so no single row is a disagreement — the year simply has almost
    no corroboration."""
    questions, _ = _sitting()
    corpus = {(YEAR, p): sgb._normalise(TEXT[p]) for p in (1, 2, 3, 4)}
    tags = {str(q["id"]): 4 for q in questions}
    with pytest.raises(sgb.BucketAbort) as exc:
        sgb.plan_bucket(_bucket(), questions, tag_papers=tags, corpus=corpus)
    msg = str(exc.value)
    assert "agrees with the tags on 1/4" in msg
    assert "(25%)" in msg
    assert "below the 50% bar" in msg
    assert f"--tag-only-years {YEAR}" in msg


def test_a_year_agreeing_at_exactly_half_is_not_tag_only():
    """The bar is `< 50%`, so a year that splits evenly is verified. Stated
    because an off-by-one here silently relabels a whole year."""
    questions, tags = _sitting()
    verdicts = {(YEAR, 1): 1, (YEAR, 2): 2}
    planned, rows = sgb.plan_bucket(_bucket(), questions, tag_papers=tags,
                                    corpus={}, verdict_papers=verdicts)
    assert sgb.agreement_rate(rows) == (2, 2)
    assert {r["method"] for r in rows} == {"tag"}


def test_the_tag_only_rule_is_the_same_rule_for_the_verdict_signal():
    """One rule for all years, whichever signal the year has. A verdict year
    that corroborates under half the tags is refused exactly as an OCR year is.

    The rows the verdict places elsewhere carry no tag to contradict, so they
    are not disagreements — only uncorroborated."""
    questions, _ = _sitting()
    tags = {str(questions[3]["id"]): 4}
    verdicts = {(YEAR, 1): 1, (YEAR, 2): 2, (YEAR, 3): 3, (YEAR, 4): 1}
    with pytest.raises(sgb.BucketAbort) as exc:
        sgb.plan_bucket(_bucket(), questions, tag_papers=tags, corpus={},
                        verdict_papers=verdicts)
    assert "tag-only" in str(exc.value)
    assert "0/1" in str(exc.value)


def test_a_named_tag_only_year_leaves_overrides_and_essay_tags_alone():
    """Only `tag` becomes `tag_only`. An override is still a human decision and
    an essay tag is still a tag in another table — neither is less certain
    because the year's OCR failed."""
    questions, tags = _sitting()
    essay = _q(ESSAY_TEXT, 5)
    questions.append(essay)
    overrides = {str(questions[0]["id"]): 2}
    planned, rows = sgb.plan_bucket(
        _bucket(), questions, tag_papers=tags, corpus={},
        essay_tagged={str(essay["id"])}, overrides=overrides,
        tag_only_years=frozenset({YEAR}),
    )
    by_method: dict[str, int] = {}
    for r in rows:
        by_method[r["method"]] = by_method.get(r["method"], 0) + 1
    assert by_method == {"override": 1, "tag_only": 3, "essay_tag": 1}


# ── 12. the dry-run summary reports the rate ───────────────────────────────

def test_the_summary_line_leads_with_the_agreement_rate():
    questions, tags = _sitting()
    _, rows = sgb.plan_bucket(_bucket(), questions, tag_papers=tags,
                              corpus=_corpus())
    line = sgb.summarise(YEAR, rows)
    assert "agreement 4/4 = 100%" in line


def test_the_summary_says_so_when_there_was_nothing_to_check():
    questions, tags = _sitting()
    _, rows = sgb.plan_bucket(_bucket(), questions, tag_papers=tags, corpus={},
                              tag_only_years=frozenset({YEAR}))
    line = sgb.summarise(YEAR, rows)
    assert "agreement 0/0 (nothing to check)" in line
    assert "TAG-ONLY 4" in line


def test_the_review_sheet_records_the_method_and_the_verification(tmp_path, monkeypatch):
    questions, tags = _sitting()
    _, rows = sgb.plan_bucket(_bucket(), questions, tag_papers=tags,
                              corpus=_corpus())
    out = tmp_path / "gs_split_review.csv"
    monkeypatch.setattr(sgb, "REVIEW_CSV", out)
    sgb._write_review([{**r, "year": YEAR} for r in rows])

    import csv
    got = list(csv.DictReader(out.read_text(encoding="utf-8-sig").splitlines()))
    assert [r["method"] for r in got] == ["tag"] * 4
    assert [r["verified_against"] for r in got] == ["1", "2", "3", "4"]
