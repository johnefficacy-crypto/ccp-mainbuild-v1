"""CORPUS-READINESS-01 — the report's derivation, on fixtures only.

No database and no network: every test builds from a dict or the committed
fixture. The script's ``--live`` path is operator-only and is never exercised
here, by CI, or by an agent.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[4]
_SPEC = importlib.util.spec_from_file_location(
    "corpus_readiness_report", _ROOT / "scripts/corpus_readiness_report.py"
)
crr = importlib.util.module_from_spec(_SPEC)
sys.modules["corpus_readiness_report"] = crr
_SPEC.loader.exec_module(crr)

FIXTURE = Path(__file__).parent / "fixtures/corpus_readiness_demo.json"


def _fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _report(data: dict) -> dict:
    return crr.build_report(data)


def _cell(report: dict, subject: str, exam: str) -> dict:
    return next(
        r for r in report["section1"] if r["subject"] == subject and r["exam"] == exam
    )


# ── section 5: a subject with micros but no macro layer ────────────────────

def test_subject_with_microtopics_but_no_macro_layer_is_flagged():
    report = _report(_fixture())
    orphan = next(t for t in report["section5"] if t["subject"] == "Orphan Microtopics")
    assert orphan["micro"] == 2 and orphan["macro"] == 0
    assert orphan["micro_without_macro"] is True
    # and every properly-parented subject is not flagged
    qa = next(t for t in report["section5"] if t["subject"] == "Quantitative Aptitude")
    assert qa["micro_without_macro"] is False


# ── section 3: blocked exam, reported as INPUTS not a verdict ──────────────

def test_blocked_exam_reports_observed_provenance_fields_not_a_verdict():
    report = _report(_fixture())
    ssc = next(b for b in report["section3"] if b["exam"] == "ssc-cgl")
    assert ssc["questions"] == 2
    assert ssc["unverified"] == 2      # nothing reviewed
    assert ssc["untagged"] == 2        # nothing tagged
    p = ssc["provenance"]
    assert p["papers"] == 2
    assert p["not_official"] == 2      # 'unknown' and 'coaching'
    assert p["no_source_url"] == 1     # only p-ssc-1 has none
    assert p["no_source_document_id"] == 2
    assert p["trust_pending"] == 2
    # The report carries no pass/fail key at all — that is the point.
    assert "verdict" not in p and "passes_gate" not in p


def test_markdown_states_the_gate_is_not_reproduced_and_cites_271():
    md = crr.render_markdown(_report(_fixture()), generated_at="2026-09-22",
                             mode="fixture", source="demo")
    assert "271_review_pyq_paper_question_count_gate.sql" in md
    assert "INPUTS, not its verdict" in md
    # Never phrase an observation as a gate outcome.
    for banned in ("fails the provenance gate", "passes the provenance gate"):
        assert banned not in md.lower()


# ── section 4: zero-question catalogues ────────────────────────────────────

def test_zero_question_catalogues_are_listed():
    report = _report(_fixture())
    assert "Banking" in report["section4"]
    assert "Capital Market" in report["section4"]
    assert "Quantitative Aptitude" not in report["section4"]


# ── thematic rows: questions yes, papers no ────────────────────────────────

def test_thematic_rows_count_as_questions_but_never_as_papers():
    report = _report(_fixture())
    gs = _cell(report, "General Studies I", "upsc-cse")
    # 2 GS descriptive + 1 thematic descriptive all reach the subject
    assert gs["tagged"] == 3
    assert gs["descriptive"] == 3
    # ...but only the one real GS paper is counted as a paper
    assert gs["papers"] == 1


# ── retired buckets: gone from every section ───────────────────────────────

def test_retired_bucket_is_excluded_everywhere():
    report = _report(_fixture())
    nab_qa = _cell(report, "Quantitative Aptitude", "national-nabard-grade-a")
    # q-nab-retired-1 is tagged to t-qa-micro-1 but sits on a retired bucket
    assert nab_qa["tagged"] == 2          # not 3
    assert nab_qa["papers"] == 1          # the retired bucket is not a paper
    nab = [b for b in report["section3"] if b["exam"] == "national-nabard-grade-a"]
    if nab:
        assert nab[0]["provenance"]["papers"] == 1


def test_a_retired_bucket_hides_its_questions_even_when_they_are_verified():
    """Retiring the only live bucket zeroes the exam's questions. The row itself
    survives, carrying the locked-coverage counts — "this subject is covered for
    this exam but has no corpus" is a gap worth seeing, not one worth hiding."""
    data = _fixture()
    for p in data["papers"]:
        if p["id"] == "p-nab-1":
            p["metadata"]["retired"] = True
    report = _report(data)
    nab = [r for r in report["section1"] if r["exam"] == "national-nabard-grade-a"]
    assert nab, "a covered subject should still appear"
    assert all(r["tagged"] == 0 and r["projected"] == 0 and r["papers"] == 0 for r in nab)


# ── shared subjects: no metadata.exams, must not be emptied ────────────────

def test_shared_body_agnostic_subjects_are_counted_not_emptied():
    """The three shared subjects carry no metadata.exams key. Counting through
    topics.subject_id reaches them; any body/exam filter would not."""
    report = _report(_fixture())
    for name in ("Quantitative Aptitude", "General Intelligence and Reasoning"):
        cell = _cell(report, name, "national-nabard-grade-a")
        assert cell["tagged"] > 0, name
    # and no fixture subject carries the key this report must not depend on
    assert all("metadata" not in s for s in _fixture()["subjects"])


# ── descriptive questions are never projected ──────────────────────────────

def test_descriptive_questions_are_never_counted_as_projected():
    report = _report(_fixture())
    gs = _cell(report, "General Studies I", "upsc-cse")
    assert gs["descriptive"] == 3 and gs["projected"] == 0


def test_a_stray_projection_row_on_a_descriptive_question_is_still_not_counted():
    """Defence in depth: the corpus rule is that descriptive never projects, so
    a row that exists anyway is a data defect and must not inflate the count."""
    data = _fixture()
    data["projected"].append(
        {"id": "mb-bad", "pyq_question_id": "q-upsc-desc-1",
         "topic_id": "t-gs-macro-1", "microtopic_id": "t-gs-micro-1"}
    )
    gs = _cell(_report(data), "General Studies I", "upsc-cse")
    assert gs["projected"] == 0


# ── inactive topics ────────────────────────────────────────────────────────

def test_inactive_topics_are_excluded_from_tree_counts():
    report = _report(_fixture())
    qa = next(t for t in report["section5"] if t["subject"] == "Quantitative Aptitude")
    assert qa["micro"] == 2  # t-qa-micro-dead is is_active=false


# ── section 2: features derived, not asserted ──────────────────────────────

def test_feature_readiness_is_derived_from_the_counts():
    report = _report(_fixture())
    by_subject = {r["subject"]: r for r in report["section2"]}

    qa = by_subject["Quantitative Aptitude"]
    assert qa["mcq_practice"] is True            # 2 projected
    assert qa["topic_mastery"] is True           # microtopic_id + locked coverage
    assert qa["answer_writing"] is False         # no descriptive
    assert qa["syllabus_navigation"] is True     # macro + micro

    gi = by_subject["General Intelligence and Reasoning"]
    assert gi["mcq_practice"] is True
    # projected row carries microtopic_id NULL, and its coverage row is draft
    assert gi["topic_mastery"] is False

    gs = by_subject["General Studies I"]
    assert gs["mcq_practice"] is False
    assert gs["answer_writing"] is True          # verified descriptive + tags


def test_topic_mastery_needs_both_a_microtopic_id_and_locked_coverage():
    data = _fixture()
    for c in data["coverage"]:
        if c["topic_id"].startswith("t-qa"):
            c["reviewer_status"] = "draft"
    qa = next(r for r in _report(data)["section2"] if r["subject"] == "Quantitative Aptitude")
    assert qa["topic_mastery"] is False
    assert qa["mcq_practice"] is True  # unchanged — the rules are independent


# ── determinism ────────────────────────────────────────────────────────────

def test_two_runs_on_the_same_fixture_are_byte_identical(tmp_path):
    out_a, out_b = tmp_path / "a", tmp_path / "b"
    for out in (out_a, out_b):
        crr.main(["--from-fixture", str(FIXTURE), "--out-dir", str(out), "--seed"])
    for name in ("corpus-readiness.md", "corpus-readiness.csv"):
        assert (out_a / name).read_bytes() == (out_b / name).read_bytes(), name


def test_ordering_is_subject_then_exam_and_independent_of_input_order():
    data = _fixture()
    shuffled = dict(data)
    for key in ("subjects", "exams", "topics", "papers", "questions", "tags"):
        shuffled[key] = list(reversed(data[key]))
    a = [(r["subject"], r["exam"]) for r in _report(data)["section1"]]
    b = [(r["subject"], r["exam"]) for r in _report(shuffled)["section1"]]
    assert a == b == sorted(a)


# ── CSV ────────────────────────────────────────────────────────────────────

def test_csv_header_is_stable_and_carries_a_flag_per_feature():
    csv_text = crr.render_csv(_report(_fixture()))
    header = csv_text.splitlines()[0]
    assert header == ",".join(crr.CSV_COLUMNS)
    for feature in crr.FEATURES:
        assert feature in header
    assert csv_text.endswith("\n") and "\r" not in csv_text


def test_csv_numbers_match_section_1():
    report = _report(_fixture())
    rows = crr.render_csv(report).splitlines()[1:]
    assert len(rows) == len(report["section1"])
    first = rows[0].split(",")
    s1 = report["section1"][0]
    assert first[0] == s1["subject"] and first[1] == s1["exam"]


# ── the seed doc ───────────────────────────────────────────────────────────

def test_seed_output_is_marked_as_fixture_data_not_live_counts():
    md = crr.render_markdown(_report(_fixture()), generated_at="2026-09-22",
                             mode="fixture", source="demo", seed=True)
    assert "Example output — fixture data, not live counts" in md
    assert "--live" in md


def test_committed_seed_doc_matches_a_fresh_run_of_the_fixture(tmp_path):
    """The committed doc is not hand-edited: regenerating reproduces it byte for
    byte. If this fails, someone typed a number in by hand."""
    crr.main(["--from-fixture", str(FIXTURE), "--out-dir", str(tmp_path), "--seed"])
    for name in ("corpus-readiness.md", "corpus-readiness.csv"):
        committed = (_ROOT / "docs/status" / name).read_bytes()
        assert (tmp_path / name).read_bytes() == committed, name


# ── the script never writes to a database ──────────────────────────────────

def test_the_module_contains_no_write_statement():
    src = (_ROOT / "scripts/corpus_readiness_report.py").read_text(encoding="utf-8")
    lowered = src.lower()
    for banned in ("insert into", "update ", "delete from", "review_pyq_paper("):
        assert banned not in lowered.replace("-- ", ""), banned
