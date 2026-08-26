"""Unit tests for ``scripts/pyq_question_review.py``.

The script lives at the repo root (mirroring scripts/syllabus_mention_review.py),
so it is loaded by absolute path rather than via the ``scripts`` package (which
resolves to app/backend/scripts under the backend pytest rootdir).

Coverage:
- every sweep flag category, true-positive AND false-positive;
- per-paper scoping of duplicate_text;
- sampling picks only from clean rows, flagged rows always appear;
- apply issues the exact PATCH set (method/url/kind/body), skips blanks;
- a blank decision on a flagged row does not raise;
- an over-500-char note is truncated client-side, never sent raw.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import pathlib

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_SCRIPT = _ROOT / "scripts" / "pyq_question_review.py"
_spec = importlib.util.spec_from_file_location("pyq_question_review", _SCRIPT)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


# ─── sweep: question flags ───────────────────────────────────────────────────
def _q(**kw):
    base = {"id": "q1", "paper_id": "p1", "year": 2020, "question_number": 1,
            "question_text": "A properly long and valid question stem here?"}
    base.update(kw)
    return base


def test_empty_or_short_true_and_false():
    assert "empty_or_short" in mod.question_flags(_q(question_text="short"), {}, set())
    assert "empty_or_short" in mod.question_flags(_q(question_text="   "), {}, set())
    assert "empty_or_short" not in mod.question_flags(_q(), {}, set())


def test_non_ascii_suspect_true_false_and_hindi_year_exemption():
    dirty = _q(question_text="Discuss the impact of ×× mojibake artefact.")
    assert "non_ascii_suspect" in mod.question_flags(dirty, {}, set())
    # Same row, but its year is declared a legitimate bilingual/Hindi year.
    assert "non_ascii_suspect" not in mod.question_flags(dirty, {}, {"2020"})
    # Plain ASCII in a non-Hindi year must not flag.
    assert "non_ascii_suspect" not in mod.question_flags(_q(), {}, set())


def test_suspicious_repeat_char_true_and_false():
    assert "suspicious_repeat_char" in mod.question_flags(
        _q(question_text="Leftover extraction artefact xxxx in the stem body."), {}, set())
    assert "suspicious_repeat_char" not in mod.question_flags(_q(), {}, set())


def test_duplicate_text_true_and_false():
    text = "This exact question text appears twice in one paper for sure."
    counts = {mod.normalize_text(text): 2}
    assert "duplicate_text" in mod.question_flags(_q(question_text=text), counts, set())
    # Unique text (count 1) does not flag.
    assert "duplicate_text" not in mod.question_flags(
        _q(question_text=text), {mod.normalize_text(text): 1}, set())


def test_duplicate_text_is_scoped_per_paper():
    """Identical text in DIFFERENT papers must NOT flag as duplicate."""
    text = "Identical stem shared across two different papers entirely."
    qs = [
        _q(id="a", paper_id="p1", question_text=text),
        _q(id="b", paper_id="p2", question_text=text),
    ]
    rows = mod.build_worksheet(qs, [], set(), set(), {}, set())
    for r in rows:
        assert "duplicate_text" not in r["flags"], r
    # But two identical in the SAME paper flag both.
    qs_same = [
        _q(id="a", paper_id="p1", question_number=1, question_text=text),
        _q(id="b", paper_id="p1", question_number=2, question_text=text),
    ]
    rows_same = mod.build_worksheet(qs_same, [], set(), set(), {}, set())
    assert all("duplicate_text" in r["flags"] for r in rows_same)


# ─── sweep: tag flags ────────────────────────────────────────────────────────
def _t(**kw):
    base = {"id": "t1", "question_id": "q1", "topic_id": "TID", "tag_role": "primary"}
    base.update(kw)
    return base


def test_unknown_topic_true_and_false():
    assert "unknown_topic" in mod.tag_flags(_t(topic_id="ghost"), {"TID"}, set())
    assert "unknown_topic" not in mod.tag_flags(_t(topic_id="TID"), {"TID"}, set())


def test_orphaned_topic_only_when_catalog_distinguishes():
    # Present in catalog and marked orphan -> orphaned_topic.
    assert "orphaned_topic" in mod.tag_flags(_t(topic_id="TID"), {"TID"}, {"TID"})
    # No orphan distinction -> never orphaned, only unknown can fire.
    assert "orphaned_topic" not in mod.tag_flags(_t(topic_id="TID"), {"TID"}, set())


def test_non_primary_true_and_false():
    assert "non_primary" in mod.tag_flags(_t(tag_role="secondary"), {"TID"}, set())
    assert "non_primary" not in mod.tag_flags(_t(tag_role="primary"), {"TID"}, set())


def test_load_topic_catalog_orphan_markers(tmp_path):
    cat = [
        {"id": "clean", "text": "Clean topic"},
        {"id": "orph1", "text": "Orphan by flag", "orphaned": True},
        {"id": "orph2", "text": "Orphan by status", "status": "pre_split_orphan"},
        {"id": "orph3", "text": "Orphan by reviewed", "reviewed": False},
    ]
    p = tmp_path / "cat.json"
    p.write_text(json.dumps(cat), encoding="utf-8")
    valid, orphan, names = mod.load_topic_catalog(str(p))
    assert valid == {"clean", "orph1", "orph2", "orph3"}
    assert orphan == {"orph1", "orph2", "orph3"}
    assert names["clean"] == "Clean topic"


# ─── sweep: sampling ─────────────────────────────────────────────────────────
def test_sampling_from_clean_only_and_flagged_always_present():
    # 10 clean questions + 1 flagged (too short) in one paper.
    clean = [_q(id=f"c{i}", paper_id="p1", question_number=i,
                question_text=f"Valid unique clean question number {i} here.")
             for i in range(10)]
    flagged = _q(id="bad", paper_id="p1", question_number=99, question_text="x")
    rows = mod.build_worksheet(clean + [flagged], [], set(), set(), {}, set())

    by_id = {r["row_id"]: r for r in rows}
    # Flagged row is present, marked flagged, never a spot_check.
    assert by_id["bad"]["sample_reason"] == "flagged"
    assert "empty_or_short" in by_id["bad"]["flags"]
    # Spot-check rows are all clean.
    spot = [r for r in rows if r["sample_reason"] == "spot_check"]
    assert spot, "expected at least one spot-check sample"
    for r in spot:
        assert r["flags"] == ""
    # min(8, ceil(0.2*10)) = 2 spot-checks.
    assert len(spot) == 2


def test_spread_sample_is_bounded_and_spread():
    rows = [{"id": i} for i in range(50)]
    picked = mod.spread_sample(rows)
    assert len(picked) == 8            # capped at 8
    ids = [r["id"] for r in picked]
    assert ids[0] == 0 and ids[-1] > 30  # spread, not the first 8
    assert mod.spread_sample([]) == []
    assert len(mod.spread_sample([{"id": 1}])) == 1  # ceil guarantees >=1


# ─── apply ───────────────────────────────────────────────────────────────────
class FakeClient:
    def __init__(self):
        self.calls = []

    def patch(self, path, body):
        self.calls.append({"method": "PATCH", "path": path, "body": body})
        return {"ok": True}


def _write_worksheet(tmp_path, rows):
    p = tmp_path / "worksheet.csv"
    with p.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=mod.WORKSHEET_FIELDS)
        w.writeheader()
        w.writerows(rows)
    return p


def _row(**kw):
    base = {k: "" for k in mod.WORKSHEET_FIELDS}
    base.update(kw)
    return base


def _apply_args(worksheet, **kw):
    parser = mod.build_parser()
    argv = ["apply", "--worksheet", str(worksheet), "--sleep", "0"]
    for k, v in kw.items():
        if v is True:
            argv.append(f"--{k}")
    return parser.parse_args(argv)


def test_apply_issues_exact_patch_set_and_skips_blanks(tmp_path):
    rows = [
        _row(row_type="question", row_id="q1", paper_year="2020", decision="verified"),
        _row(row_type="question", row_id="q2", paper_year="2020", decision=""),  # blank -> skip
        _row(row_type="tag", row_id="t1", paper_year="2020", decision="rejected"),
        _row(row_type="question", row_id="q3", paper_year="2021",
             decision="needs_correction", notes="off topic"),
    ]
    ws = _write_worksheet(tmp_path, rows)
    fake = FakeClient()
    args = _apply_args(ws, apply=True, confirm=True)
    rc = mod.do_apply(fake, args)
    assert rc == 0

    got = {c["path"]: c for c in fake.calls}
    assert len(fake.calls) == 3  # blank skipped
    assert "/api/admin/exam-intelligence/items/pyq_question/q1/review" in got
    assert got["/api/admin/exam-intelligence/items/pyq_question/q1/review"]["body"] == {
        "reviewer_status": "verified"}
    assert got["/api/admin/exam-intelligence/items/pyq_question_topic_tag/t1/review"]["body"] == {
        "reviewer_status": "rejected"}
    q3 = got["/api/admin/exam-intelligence/items/pyq_question/q3/review"]
    assert q3["method"] == "PATCH"
    assert q3["body"] == {"reviewer_status": "needs_correction", "reviewer_notes": "off topic"}
    # q2 never patched.
    assert all("/q2/" not in c["path"] for c in fake.calls)


def test_apply_dry_run_writes_nothing(tmp_path):
    rows = [_row(row_type="question", row_id="q1", paper_year="2020", decision="verified")]
    ws = _write_worksheet(tmp_path, rows)
    fake = FakeClient()
    args = _apply_args(ws)  # no --apply/--confirm -> dry run
    rc = mod.do_apply(fake, args)
    assert rc == 0
    assert fake.calls == []


def test_apply_blank_on_flagged_row_does_not_raise(tmp_path):
    rows = [
        _row(row_type="question", row_id="q1", paper_year="2020",
             flags="empty_or_short", sample_reason="flagged", decision=""),
        _row(row_type="question", row_id="q2", paper_year="2020", decision="verified"),
    ]
    ws = _write_worksheet(tmp_path, rows)
    fake = FakeClient()
    args = _apply_args(ws, apply=True, confirm=True)
    rc = mod.do_apply(fake, args)  # must not raise on the flagged-but-blank row
    assert rc == 0
    assert len(fake.calls) == 1
    assert "/q2/" in fake.calls[0]["path"]


def test_apply_truncates_over_length_note(tmp_path, capsys):
    long_note = "z" * 700
    rows = [_row(row_type="tag", row_id="t1", paper_year="2020",
                 decision="verified", notes=long_note)]
    ws = _write_worksheet(tmp_path, rows)
    fake = FakeClient()
    args = _apply_args(ws, apply=True, confirm=True)
    rc = mod.do_apply(fake, args)
    assert rc == 0
    sent = fake.calls[0]["body"]["reviewer_notes"]
    assert len(sent) == mod.NOTE_MAX  # truncated, never the raw 700 chars
    assert "truncated" in capsys.readouterr().err


def test_apply_rejects_unrecognized_decision(tmp_path):
    rows = [_row(row_type="question", row_id="q1", paper_year="2020", decision="maybe")]
    ws = _write_worksheet(tmp_path, rows)
    fake = FakeClient()
    args = _apply_args(ws, apply=True, confirm=True)
    assert mod.do_apply(fake, args) == 2
    assert fake.calls == []


# ─── export helpers (pure) ───────────────────────────────────────────────────
def test_classify_mains_papers_filters_to_phase():
    papers = [
        {"id": "p1", "exam_phase_id": "MAINS", "year": 2020},
        {"id": "p2", "exam_phase_id": "PRELIMS", "year": 2020},
        {"id": "p3", "exam_phase_id": "MAINS", "year": 2019},
    ]
    got = mod.classify_mains_papers(papers, "MAINS", None)
    assert {p["id"] for p in got} == {"p1", "p3"}
    # explicit override narrows further.
    got2 = mod.classify_mains_papers(papers, "MAINS", {"p1"})
    assert {p["id"] for p in got2} == {"p1"}


def test_merge_questions_attaches_text_and_drops_non_mains():
    pending = [
        {"id": "q1", "pyq_paper_id": "p1", "section_id": "s1", "question_number": 1,
         "language": "en", "reviewer_status": "pending"},
        {"id": "qX", "pyq_paper_id": "pP", "section_id": "s9", "question_number": 5,
         "reviewer_status": "pending"},  # not in cms_by_id -> dropped
    ]
    cms = {"q1": {"id": "q1", "pyq_paper_id": "p1", "question_text": "Real stem?",
                  "question_type": "descriptive"}}
    merged = mod.merge_questions(pending, cms, {"p1": 2020}, {"s1": "GS1"})
    assert len(merged) == 1
    row = merged[0]
    assert row["id"] == "q1"
    assert row["question_text"] == "Real stem?"
    assert row["year"] == 2020
    assert row["section"] == "GS1"
