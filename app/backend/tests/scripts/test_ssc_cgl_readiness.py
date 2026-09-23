"""Unit tests for ``scripts/ssc_cgl_readiness.py``.

The script lives at the repo root's ``scripts/`` directory (mirroring
``scripts/pyq_question_review.py``), so it is loaded by absolute path rather
than via the ``scripts`` package, which resolves to app/backend/scripts under
the backend pytest rootdir.

Coverage:
- every P1 counter, true-positive AND false-positive, on fixtures whose
  expected numbers are written out by hand;
- an absent options file reports "not computed" and NEVER zero;
- question_number gaps are anchored at 1 and report repeats separately;
- per-paper and corpus-wide duplicate stems are different numbers;
- the catalogue-fit sample is spread, proportional and deterministic;
- a topic-LEVEL row in the catalogue aborts the load by name;
- the P4 projection gate reproduces migration 271's blocking-field set,
  including that a paper with a source_document_id is reported as having an
  UNEVALUATED document check rather than a pass;
- dry run writes nothing; --apply writes exactly the files it names.

Fully offline: the module opens no network connection and holds no client.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import pathlib

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_SCRIPT = _ROOT / "scripts" / "ssc_cgl_readiness.py"
_spec = importlib.util.spec_from_file_location("ssc_cgl_readiness", _SCRIPT)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


QA = "Quantitative Aptitude"
GI = "General Intelligence and Reasoning"
EN = "English Comprehension"


def _q(qid, paper="p1", section=QA, number=1, text=None, qtype="mcq", key="o1"):
    return {
        "id": qid, "paper_id": paper, "section": section,
        "question_number": number,
        "question_text": text if text is not None
        else f"A properly long and valid stem about percentage number {number}?",
        "question_type": qtype, "correct_option_id": key, "year": 2024,
    }


def _paper(pid="p1", **kw):
    base = {"id": pid, "year": 2024, "paper_code": pid.upper(),
            "shift": "shift-1", "trust_status": "pending",
            "source_type": "official", "source_url": "https://ssc.gov.in/x.pdf",
            "source_document_id": None, "question_count": 3}
    base.update(kw)
    return base


def _write(path, obj):
    path.write_text(json.dumps(obj), encoding="utf-8")
    return str(path)


# ─── P1 counters ─────────────────────────────────────────────────────────────
def test_section_split_counts_each_section_separately():
    out = mod.paper_readiness(
        [_q("a", section=QA), _q("b", section=GI, number=2),
         _q("c", section=GI, number=3)], None)
    assert out["questions"] == 3
    assert out["by_section"] == {GI: 2, QA: 1}


def test_a_question_with_no_section_is_named_not_dropped():
    out = mod.paper_readiness([_q("a", section=None)], None)
    assert out["by_section"] == {"(unsectioned)": 1}
    assert out["questions"] == 1


def test_absent_options_file_reports_not_computed_never_zero():
    """Absence is not a pass. A counter that did not run must not read as one
    that ran and found nothing."""
    out = mod.paper_readiness([_q("a")], None)
    assert out["missing_options"] is None
    assert out["missing_answer_key"] is None
    assert mod._cell(out["missing_options"]) == "not computed"


def test_missing_options_counts_mcqs_with_no_option_rows():
    questions = [_q("a"), _q("b", number=2)]
    by_q = {"a": [{"question_id": "a", "is_correct": True}]}
    out = mod.paper_readiness(questions, by_q)
    assert out["missing_options"] == 1


def test_a_descriptive_question_is_not_counted_as_missing_options():
    out = mod.paper_readiness([_q("a", qtype="descriptive", key=None)], {})
    assert out["missing_options"] == 0
    assert out["missing_answer_key"] == 0


def test_answer_key_satisfied_by_either_source():
    """correct_option_id and pyq_options.is_correct are independent sources.
    Either one present means the question HAS a key."""
    only_column = mod.paper_readiness(
        [_q("a", key="o1")], {"a": [{"is_correct": False}]})
    only_rows = mod.paper_readiness(
        [_q("a", key=None)], {"a": [{"is_correct": True}]})
    neither = mod.paper_readiness(
        [_q("a", key=None)], {"a": [{"is_correct": False}]})
    assert only_column["missing_answer_key"] == 0
    assert only_rows["missing_answer_key"] == 0
    assert neither["missing_answer_key"] == 1


def test_duplicate_stems_are_counted_after_normalisation():
    same = "The ratio of two numbers is three to four. Find the smaller."
    out = mod.paper_readiness(
        [_q("a", text=same), _q("b", number=2, text=f"  {same.upper()}  "),
         _q("c", number=3)], None)
    assert out["duplicate_stem_groups"] == 1
    assert out["duplicate_stem_questions"] == 2


def test_corpus_duplicates_and_paper_duplicates_are_different_numbers():
    """A stem repeating between two shifts is normal; the same stem twice
    inside one paper is an import defect. Reporting one as the other hides
    whichever is the real finding."""
    same = "Which figure completes the series shown in the given diagram set?"
    questions = [_q("a", paper="p1", text=same),
                 _q("b", paper="p2", text=same)]
    per_paper = mod.paper_readiness([questions[0]], None)
    assert per_paper["duplicate_stem_questions"] == 0
    assert mod.corpus_duplicate_stems(questions) == (1, 2)


def test_non_ascii_and_repeat_char_flags_fire_and_do_not_over_fire():
    clean = mod.paper_readiness([_q("a")], None)
    assert clean["non_ascii"] == 0 and clean["repeat_char"] == 0
    dirty = mod.paper_readiness(
        [_q("a", text="What is the value of कुछ in this stem here?"),
         _q("b", number=2, text="A stem with aaaaa repeated characters inside.")],
        None)
    assert dirty["non_ascii"] == 1
    assert dirty["repeat_char"] == 1


def test_empty_or_short_matches_the_sweeps_fifteen_character_floor():
    out = mod.paper_readiness([_q("a", text="short"), _q("b", number=2)], None)
    assert out["empty_or_short"] == 1


# ─── question_number gaps ────────────────────────────────────────────────────
def test_gaps_are_anchored_at_one_not_at_the_lowest_present_number():
    """A paper numbered 7..9 is missing six questions, not numbered oddly."""
    missing, repeated, non_numeric = mod.question_number_gaps([7, 8, 9])
    assert missing == [1, 2, 3, 4, 5, 6]
    assert repeated == [] and non_numeric == 0


def test_repeats_and_non_numeric_numbers_are_reported_separately():
    missing, repeated, non_numeric = mod.question_number_gaps([1, 2, 2, 4, "Q5", None])
    assert missing == [3]
    assert repeated == [2]
    assert non_numeric == 2


def test_a_complete_paper_reports_no_gaps():
    assert mod.question_number_gaps([1, 2, 3]) == ([], [], 0)


def test_no_numbers_at_all_is_not_a_gap_list_to_infinity():
    assert mod.question_number_gaps([]) == ([], [], 0)


# ─── catalogue fit ───────────────────────────────────────────────────────────
def _catalogue_file(tmp_path, rows):
    return _write(tmp_path / "cat.json", rows)


def test_a_topic_level_row_aborts_the_catalogue_load_by_name(tmp_path):
    """A top-level topic id is the wrong granularity for a question tag and
    would report coverage this corpus cannot use."""
    path = _catalogue_file(tmp_path, [
        {"id": "t1", "text": "Arithmetic", "level": "topic"},
        {"id": "m1", "text": "Percentage", "level": "microtopic"},
    ])
    with pytest.raises(ValueError, match=r"non-microtopic row"):
        mod.load_catalogue(path)


def test_a_catalogue_without_a_level_key_still_loads(tmp_path):
    """The hand-written UPSC catalogues are flat [{id, text}] and predate the
    field; only a row that STATES a wrong level is rejected."""
    rows = mod.load_catalogue(_catalogue_file(
        tmp_path, [{"id": "m1", "text": "Time and Work"}]))
    assert [r["id"] for r in rows] == ["m1"]
    assert "time" in rows[0]["tokens"] and "work" in rows[0]["tokens"]


def test_significant_tokens_drop_short_words_and_stopwords():
    tokens = mod.significant_tokens("What is the correct answer to this question?")
    assert tokens == set()
    assert "percentage" in mod.significant_tokens("Find the percentage increase.")


def test_fit_is_scored_on_the_microtopics_tokens_not_the_stems():
    """A stem is fifty words and a microtopic name is two. Scoring the overlap
    against the stem would call every question unmatched."""
    cat = [{"id": "m1", "label": "Percentage", "tokens": {"percentage"}},
           {"id": "m2", "label": "Syllogism", "tokens": {"syllogism"}}]
    row, score = mod.best_fit(
        mod.significant_tokens(
            "Find the percentage increase when a price rises from 40 to 50."),
        cat)
    assert row["id"] == "m1" and score == 1.0


def test_a_stem_matching_nothing_scores_zero():
    cat = [{"id": "m1", "label": "Percentage", "tokens": {"percentage"}}]
    row, score = mod.best_fit(mod.significant_tokens("Rearrange these letters."), cat)
    assert score == 0.0 and row is None


def test_sample_allocation_is_proportional_and_sums_exactly():
    alloc = mod.allocate_sample({QA: 500, GI: 300, EN: 200}, 100)
    assert sum(alloc.values()) == 100
    assert alloc[QA] > alloc[GI] > alloc[EN]


def test_every_non_empty_section_gets_at_least_one_sampled_row():
    """A section absent from the sample cannot contribute a gap candidate, and
    'we did not look' would read in the report as 'nothing found'."""
    alloc = mod.allocate_sample({QA: 990, GI: 5, EN: 5}, 20)
    assert min(alloc.values()) >= 1
    assert sum(alloc.values()) == 20


def test_allocation_never_exceeds_the_corpus():
    alloc = mod.allocate_sample({QA: 3}, 100)
    assert alloc == {QA: 3}


def test_the_sample_is_spread_not_the_first_n():
    rows = [{"n": i} for i in range(100)]
    picked = [r["n"] for r in mod.spread_sample(rows, 5)]
    assert picked[0] == 0 and picked[-1] > 50
    assert picked == [r["n"] for r in mod.spread_sample(rows, 5)]  # deterministic


def test_catalogue_fit_reports_matched_unmatched_and_gap_candidates():
    catalogue = [{"id": "m1", "label": "Percentage", "tokens": {"percentage"}}]
    questions = (
        [_q(f"m{i}", number=i, text="Find the percentage increase in the price.")
         for i in range(1, 5)]
        + [_q(f"u{i}", number=10 + i,
              text="Arrange the given syllogism premises into a valid conclusion.")
           for i in range(1, 5)]
    )
    fit = mod.catalogue_fit(questions, catalogue, sample_size=8)
    assert fit["sample_size_actual"] == 8
    assert fit["matched"] == 4 and fit["unmatched"] == 4
    tokens = {c["candidate_token"] for c in fit["new_microtopic_candidates"]}
    assert "syllogism" in tokens
    assert "percentage" not in tokens  # covered by the catalogue


def test_gap_candidates_below_the_support_floor_are_not_listed():
    catalogue = [{"id": "m1", "label": "Percentage", "tokens": {"percentage"}}]
    questions = [_q("u1", number=1, text="Solve this unique cryptarithm puzzle now.")]
    fit = mod.catalogue_fit(questions, catalogue, sample_size=5)
    assert fit["new_microtopic_candidates"] == []


# ─── P4 projection gate ──────────────────────────────────────────────────────
def test_a_complete_paper_passes_the_gate():
    g = mod.projection_readiness(_paper())
    assert g["gate"] == "pass" and g["blocking_fields"] == []


@pytest.mark.parametrize("overrides,expected", [
    ({"source_type": "unknown"}, "source_type"),
    ({"source_type": None}, "source_type"),
    ({"source_url": "   ", "source_document_id": None}, "source_url"),
    ({"source_url": None, "source_document_id": None}, "source_url"),
    ({"question_count": 0}, "no_questions (DB) / questions (API)"),
])
def test_each_blocking_field_is_reported_by_name(overrides, expected):
    g = mod.projection_readiness(_paper(**overrides))
    assert g["gate"] == "blocked"
    assert expected in g["blocking_fields"]


def test_a_source_document_id_satisfies_the_anchor_without_a_url():
    g = mod.projection_readiness(
        _paper(source_url=None, source_document_id="doc-1"))
    assert g["blocking_fields"] == []


def test_a_paper_with_a_document_is_flagged_as_document_checks_unevaluated():
    """Check (c) reads document_assets, which no export file carries. A 'pass'
    on such a paper is not a claim that its document validates."""
    g = mod.projection_readiness(_paper(source_document_id="doc-1"))
    assert g["gate"] == "pass"
    assert g["document_checks_not_evaluated"] is True
    assert mod.projection_readiness(_paper())["document_checks_not_evaluated"] is False


def test_every_blocking_field_is_reported_at_once_not_one_per_run():
    g = mod.projection_readiness(
        _paper(source_type="unknown", source_url=None, source_document_id=None,
               question_count=0))
    assert len(g["blocking_fields"]) == 3


# ─── report assembly + CLI ───────────────────────────────────────────────────
def test_questions_whose_paper_is_absent_from_the_export_are_named():
    report = mod.build_report([_q("a", paper="ghost")], [_paper("p1")], None, None, 0)
    assert report["orphaned_paper_ids"] == ["ghost"]


def test_csv_rows_carry_not_computed_when_options_were_not_supplied():
    report = mod.build_report([_q("a")], [_paper("p1")], None, None, 0)
    [row] = mod.csv_rows(report)
    assert row["missing_options"] == "not computed"
    assert row["projection_gate"] == "pass"


def _cli_inputs(tmp_path):
    questions = [_q("a", number=1), _q("b", number=3, section=GI)]
    return {
        "--questions": _write(tmp_path / "q.json", questions),
        "--papers": _write(tmp_path / "p.json", [_paper("p1", question_count=2)]),
    }


def _argv(inputs, *extra):
    argv = []
    for k, v in inputs.items():
        argv += [k, v]
    return argv + list(extra)


def test_dry_run_writes_nothing(tmp_path, capsys):
    md = tmp_path / "out.md"
    csv_path = tmp_path / "out.csv"
    rc = mod.main(_argv(_cli_inputs(tmp_path),
                        "--out-md", str(md), "--out-csv", str(csv_path)))
    assert rc == 0
    assert not md.exists() and not csv_path.exists()
    out = capsys.readouterr().out
    assert "DRY RUN" in out
    assert "option counters NOT computed" in out


def test_apply_writes_exactly_the_files_it_names(tmp_path):
    md = tmp_path / "r.md"
    csv_path = tmp_path / "r.csv"
    rc = mod.main(_argv(_cli_inputs(tmp_path),
                        "--out-md", str(md), "--out-csv", str(csv_path), "--apply"))
    assert rc == 0
    assert md.exists() and csv_path.exists()

    with csv_path.open(encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 1
    assert rows[0]["questions"] == "2"
    assert rows[0]["question_number_missing"] == "2"
    assert rows[0]["projection_gate"] == "pass"

    body = md.read_text(encoding="utf-8")
    assert "P1 — per-paper readiness" in body
    assert "P4 — projection readiness" in body
    assert "lexical coverage signal" not in body  # no catalogue was supplied


def test_a_catalogue_turns_on_the_fit_section(tmp_path):
    inputs = _cli_inputs(tmp_path)
    inputs["--topic-catalog"] = _write(
        tmp_path / "cat.json",
        [{"id": "m1", "text": "Percentage", "level": "microtopic"}])
    md = tmp_path / "r.md"
    rc = mod.main(_argv(inputs, "--out-md", str(md),
                        "--out-csv", str(tmp_path / "r.csv"), "--apply"))
    assert rc == 0
    body = md.read_text(encoding="utf-8")
    assert "lexical coverage signal" in body
    assert "Proposed new microtopics" in body


def test_unreadable_inputs_abort_with_a_named_error(tmp_path, capsys):
    rc = mod.main(["--questions", str(tmp_path / "nope.json"),
                   "--papers", str(tmp_path / "nope2.json")])
    assert rc == 2
    assert "cannot read inputs" in capsys.readouterr().err
