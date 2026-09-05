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
- an over-500-char note is truncated client-side, never sent raw;
- paper scoping by phase (Mains AND any other phase, e.g. Prelims) and by
  explicit paper id, including that explicit ids bypass the phase filter;
- the MCQ-only ``mcq_no_correct_option`` flag, which is the single option-level
  signal the offline sweep can give for a Prelims/CSAT paper;
- the ``no_primary_tag`` ABSENCE flag, firing and not firing;
- ``difficulty`` vocabulary enforcement, including that ``very_hard`` can never
  be written through this tool;
- an unknown ``assign_topic_id`` aborting the whole run before any call;
- a worksheet written before the two new columns existed applying unchanged;
- rows carrying any mix of decision / assign_topic_id / difficulty.

No test here constructs a ``Client``: the fakes below implement only the verbs
``do_apply`` calls, so the suite stays fully offline and ``requests`` is never
needed.
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


def test_mcq_without_correct_option_is_flagged():
    """The one option-level signal available offline — MCQ rows only."""
    flags = mod.question_flags(
        _q(question_type="mcq", correct_option_id=None), {}, set())
    assert "mcq_no_correct_option" in flags


def test_mcq_with_correct_option_is_not_flagged():
    flags = mod.question_flags(
        _q(question_type="mcq", correct_option_id="opt-1"), {}, set())
    assert "mcq_no_correct_option" not in flags
    assert flags == []


def test_descriptive_question_never_gets_the_mcq_flag():
    """Mains rows have no options; the flag must not fire on them."""
    flags = mod.question_flags(
        _q(question_type="descriptive", correct_option_id=None), {}, set())
    assert "mcq_no_correct_option" not in flags


def test_mcq_flag_is_a_flag_not_a_verdict():
    """A flagged row is emitted for a human, never auto-decided or sampled."""
    q = _q(id="q1", question_type="mcq", correct_option_id=None)
    rows = mod.build_worksheet([q], [], set(), set(), {}, set())
    assert len(rows) == 1
    assert "mcq_no_correct_option" in rows[0]["flags"]
    assert rows[0]["sample_reason"] == "flagged"
    assert rows[0]["decision"] == ""


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


# ─── sweep: no_primary_tag (the ABSENCE check) ───────────────────────────────
def test_no_primary_tag_fires_on_a_question_with_no_tags_at_all():
    """The regression this flag exists for: an untagged paper used to sweep
    clean, because a question with no tags produces no tag row to flag."""
    rows = mod.build_worksheet([_q(id="q1")], [], set(), set(), {}, set())
    assert len(rows) == 1
    assert "no_primary_tag" in rows[0]["flags"]
    # A named flag, not a verdict — emitted for a human, never auto-decided,
    # and never eligible for the clean/spot-check path.
    assert rows[0]["sample_reason"] == "flagged"
    assert rows[0]["decision"] == ""


def test_no_primary_tag_fires_when_every_tag_is_non_primary():
    tags = [_t(id="t1", question_id="q1", tag_role="secondary"),
            _t(id="t2", question_id="q1", tag_role="trap")]
    rows = mod.build_worksheet([_q(id="q1")], tags, {"TID"}, set(), {}, set())
    q_row = next(r for r in rows if r["row_type"] == "question")
    assert "no_primary_tag" in q_row["flags"]


def test_no_primary_tag_does_not_fire_when_a_primary_tag_exists():
    tags = [_t(id="t1", question_id="q1", tag_role="primary")]
    rows = mod.build_worksheet([_q(id="q1")], tags, {"TID"}, set(), {}, set())
    q_row = next(r for r in rows if r["row_type"] == "question")
    assert q_row["flags"] == ""
    assert "no_primary_tag" not in q_row["flags"]


def test_no_primary_tag_is_scoped_to_its_own_question():
    """Another question's primary tag must not clear this question's flag."""
    tags = [_t(id="t1", question_id="q1", tag_role="primary")]
    rows = mod.build_worksheet(
        [_q(id="q1", question_number=1), _q(id="q2", question_number=2)],
        tags, {"TID"}, set(), {}, set())
    by_id = {r["row_id"]: r for r in rows if r["row_type"] == "question"}
    assert "no_primary_tag" not in by_id["q1"]["flags"]
    assert "no_primary_tag" in by_id["q2"]["flags"]


def test_no_primary_tag_never_appears_on_tag_rows():
    tags = [_t(id="t1", question_id="q1", tag_role="secondary")]
    rows = mod.build_worksheet([_q(id="q1")], tags, {"TID"}, set(), {}, set())
    tag_row = next(r for r in rows if r["row_type"] == "tag")
    assert "no_primary_tag" not in tag_row["flags"]


def test_no_primary_tag_composes_with_the_other_flags():
    """Flags accumulate — the absence check does not replace the presence ones."""
    rows = mod.build_worksheet(
        [_q(id="q1", question_text="x", question_type="mcq", correct_option_id=None)],
        [], set(), set(), {}, set())
    flags = rows[0]["flags"].split(";")
    assert set(flags) >= {"empty_or_short", "mcq_no_correct_option", "no_primary_tag"}


def test_index_tags_by_question_and_has_primary_tag():
    tags = [_t(id="t1", question_id="q1", tag_role="primary"),
            _t(id="t2", question_id="q1", tag_role="secondary"),
            _t(id="t3", question_id="q2", tag_role="secondary")]
    index = mod.index_tags_by_question(tags)
    assert len(index["q1"]) == 2 and len(index["q2"]) == 1
    assert mod.has_primary_tag("q1", index) is True
    assert mod.has_primary_tag("q2", index) is False
    assert mod.has_primary_tag("q_absent", index) is False


# ─── sweep: the two new worksheet columns ────────────────────────────────────
def test_new_columns_are_appended_and_blank_on_write():
    # Appended, not reordered — an existing consumer reading by position is safe.
    # (stimulus_preview was appended after these two by the stimulus/option pass;
    # what this test pins is that they kept their slots, not that they are last.)
    assert mod.WORKSHEET_FIELDS[9:11] == ["assign_topic_id", "difficulty"]
    assert mod.WORKSHEET_FIELDS[:9] == [
        "row_type", "row_id", "paper_year", "question_number_or_topic_id",
        "text_preview", "flags", "sample_reason", "decision", "notes",
    ]
    rows = mod.build_worksheet([_q(id="q1")], [_t(id="t1", question_id="q1")],
                               {"TID"}, set(), {}, set())
    assert len(rows) == 2
    for r in rows:
        assert r["assign_topic_id"] == ""
        assert r["difficulty"] == ""


# ─── sweep: sampling ─────────────────────────────────────────────────────────
def test_sampling_from_clean_only_and_flagged_always_present():
    # 10 clean questions + 1 flagged (too short) in one paper. Each clean
    # question carries a primary tag, otherwise no_primary_tag flags them all
    # and nothing is left to sample — which is the point of the new flag.
    clean = [_q(id=f"c{i}", paper_id="p1", question_number=i,
                question_text=f"Valid unique clean question number {i} here.")
             for i in range(10)]
    flagged = _q(id="bad", paper_id="p1", question_number=99, question_text="x")
    tags = [_t(id=f"pt{i}", question_id=f"c{i}", topic_id="TID") for i in range(10)]
    tags.append(_t(id="ptbad", question_id="bad", topic_id="TID"))
    rows = mod.build_worksheet(clean + [flagged], tags, {"TID"}, set(), {}, set())
    q_rows = [r for r in rows if r["row_type"] == "question"]

    by_id = {r["row_id"]: r for r in q_rows}
    # Flagged row is present, marked flagged, never a spot_check.
    assert by_id["bad"]["sample_reason"] == "flagged"
    assert "empty_or_short" in by_id["bad"]["flags"]
    # Spot-check question rows are all clean.
    spot = [r for r in q_rows if r["sample_reason"] == "spot_check"]
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
    """Only the verbs ``do_apply`` uses. Never a real ``mod.Client``."""

    def __init__(self, fail_on=None):
        self.calls = []
        self._fail_on = fail_on or ()

    def _record(self, method, path, body):
        self.calls.append({"method": method, "path": path, "body": body})
        if any(token in path for token in self._fail_on):
            raise RuntimeError(f"{method} {path} -> 500: boom")
        return {"ok": True}

    def patch(self, path, body):
        return self._record("PATCH", path, body)

    def post(self, path, body):
        return self._record("POST", path, body)


def _catalog(tmp_path, ids=("TID", "TID2")):
    p = tmp_path / "catalog.json"
    p.write_text(json.dumps([{"id": i, "text": f"Topic {i}"} for i in ids]),
                 encoding="utf-8")
    return p


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


def _apply_args(worksheet, catalog, **kw):
    parser = mod.build_parser()
    argv = ["apply", "--worksheet", str(worksheet), "--sleep", "0",
            "--topic-catalog", str(catalog)]
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
    args = _apply_args(ws, _catalog(tmp_path), apply=True, confirm=True)
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
    args = _apply_args(ws, _catalog(tmp_path))  # no --apply/--confirm -> dry run
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
    args = _apply_args(ws, _catalog(tmp_path), apply=True, confirm=True)
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
    args = _apply_args(ws, _catalog(tmp_path), apply=True, confirm=True)
    rc = mod.do_apply(fake, args)
    assert rc == 0
    sent = fake.calls[0]["body"]["reviewer_notes"]
    assert len(sent) == mod.NOTE_MAX  # truncated, never the raw 700 chars
    assert "truncated" in capsys.readouterr().err


def test_apply_rejects_unrecognized_decision(tmp_path):
    rows = [_row(row_type="question", row_id="q1", paper_year="2020", decision="maybe")]
    ws = _write_worksheet(tmp_path, rows)
    fake = FakeClient()
    args = _apply_args(ws, _catalog(tmp_path), apply=True, confirm=True)
    assert mod.do_apply(fake, args) == 2
    assert fake.calls == []


# ─── apply: difficulty vocabulary ────────────────────────────────────────────
def test_apply_refuses_very_hard_and_sends_nothing(tmp_path, capsys):
    """It must be impossible to write very_hard through this tool.

    The column has no DB CHECK; the CMS route is the enforcement point and the
    PYQ->mock projection silently rewrites anything outside easy|medium|hard to
    'medium'. This aborts offline, before the first call.
    """
    rows = [_row(row_type="question", row_id="q1", paper_year="2020",
                 difficulty="very_hard")]
    ws = _write_worksheet(tmp_path, rows)
    fake = FakeClient()
    args = _apply_args(ws, _catalog(tmp_path), apply=True, confirm=True)
    assert mod.do_apply(fake, args) == 2
    assert fake.calls == []
    err = capsys.readouterr().err
    assert "q1" in err                      # the offending row is named
    assert "very_hard" in err
    assert "'hard'" in err                  # and the correct value suggested


def test_very_hard_is_absent_from_the_accepted_vocabulary():
    assert mod.DIFFICULTIES == {"easy", "medium", "hard"}
    assert "very_hard" not in mod.DIFFICULTIES


@pytest.mark.parametrize("bad", ["medium_high", "moderate", "tough", "unknown", "1"])
def test_apply_rejects_every_other_non_canonical_difficulty(tmp_path, bad):
    rows = [_row(row_type="question", row_id="q1", paper_year="2020", difficulty=bad)]
    ws = _write_worksheet(tmp_path, rows)
    fake = FakeClient()
    args = _apply_args(ws, _catalog(tmp_path), apply=True, confirm=True)
    assert mod.do_apply(fake, args) == 2
    assert fake.calls == []


@pytest.mark.parametrize("good", ["easy", "medium", "hard", "HARD", " medium "])
def test_apply_accepts_the_three_canonical_difficulties(tmp_path, good):
    rows = [_row(row_type="question", row_id="q1", paper_year="2020", difficulty=good)]
    ws = _write_worksheet(tmp_path, rows)
    fake = FakeClient()
    args = _apply_args(ws, _catalog(tmp_path), apply=True, confirm=True)
    assert mod.do_apply(fake, args) == 0
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call["method"] == "PATCH"
    assert call["path"] == "/api/admin/exam-intelligence-cms/pyq-questions/q1"
    assert call["body"]["payload"] == {"observed_difficulty": good.strip().lower()}
    assert 8 <= len(call["body"]["reason"]) <= mod.REASON_MAX


# ─── apply: assign_topic_id ──────────────────────────────────────────────────
def test_apply_aborts_on_unknown_assign_topic_id_before_any_call(tmp_path, capsys):
    rows = [
        _row(row_type="question", row_id="q1", paper_year="2020", assign_topic_id="TID"),
        _row(row_type="question", row_id="q2", paper_year="2020", assign_topic_id="GHOST"),
        _row(row_type="question", row_id="q3", paper_year="2021", decision="verified"),
    ]
    ws = _write_worksheet(tmp_path, rows)
    fake = FakeClient()
    args = _apply_args(ws, _catalog(tmp_path), apply=True, confirm=True)
    assert mod.do_apply(fake, args) == 2
    # The WHOLE run aborts — the valid rows are not half-applied either.
    assert fake.calls == []
    err = capsys.readouterr().err
    assert "q2" in err and "GHOST" in err
    assert "q1" not in err


def test_apply_creates_a_primary_tag_via_the_cms_route(tmp_path):
    rows = [_row(row_type="question", row_id="q1", paper_year="2020",
                 assign_topic_id="TID", notes="matches syllabus node 3.2")]
    ws = _write_worksheet(tmp_path, rows)
    fake = FakeClient()
    args = _apply_args(ws, _catalog(tmp_path), apply=True, confirm=True)
    assert mod.do_apply(fake, args) == 0
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call["method"] == "POST"
    assert call["path"] == "/api/admin/exam-intelligence-cms/pyq-question-topic-tags"
    assert call["body"]["payload"] == {
        "question_id": "q1", "topic_id": "TID",
        "tag_role": "primary", "tagging_source": "manual",
    }
    # CMS WriteEnvelope.reason: required, 8-500 chars, carries the operator note.
    reason = call["body"]["reason"]
    assert 8 <= len(reason) <= mod.REASON_MAX
    assert "matches syllabus node 3.2" in reason
    # reviewer_status is NEVER sent — the route forces 'pending'.
    assert "reviewer_status" not in call["body"]["payload"]


def test_apply_reason_is_capped_at_the_envelope_limit(tmp_path):
    rows = [_row(row_type="question", row_id="q1", paper_year="2020",
                 assign_topic_id="TID", notes="y" * 900)]
    ws = _write_worksheet(tmp_path, rows)
    fake = FakeClient()
    args = _apply_args(ws, _catalog(tmp_path), apply=True, confirm=True)
    assert mod.do_apply(fake, args) == 0
    assert len(fake.calls[0]["body"]["reason"]) == mod.REASON_MAX


def test_apply_rejects_new_columns_on_a_tag_row(tmp_path, capsys):
    """Both columns are question-only; a value on a tag row would otherwise be
    silently dropped, losing the operator's typed intent."""
    rows = [_row(row_type="tag", row_id="t1", paper_year="2020", assign_topic_id="TID"),
            _row(row_type="tag", row_id="t2", paper_year="2020", difficulty="easy")]
    ws = _write_worksheet(tmp_path, rows)
    fake = FakeClient()
    args = _apply_args(ws, _catalog(tmp_path), apply=True, confirm=True)
    assert mod.do_apply(fake, args) == 2
    assert fake.calls == []
    err = capsys.readouterr().err
    assert "t1" in err and "t2" in err


def test_apply_requires_a_topic_catalog(tmp_path, capsys):
    """Programmatic callers get the same refusal argparse gives the CLI."""
    ws = _write_worksheet(tmp_path, [_row(row_type="question", row_id="q1",
                                          paper_year="2020", decision="verified")])
    args = _apply_args(ws, _catalog(tmp_path), apply=True, confirm=True)
    args.topic_catalog = None
    fake = FakeClient()
    assert mod.do_apply(fake, args) == 2
    assert fake.calls == []
    assert "--topic-catalog is required" in capsys.readouterr().err


# ─── apply: mixed fields, and backward compatibility ─────────────────────────
def test_apply_handles_any_mix_of_the_three_fields(tmp_path):
    rows = [
        # decision only — unchanged behaviour.
        _row(row_type="question", row_id="q1", paper_year="2020", decision="verified"),
        # difficulty only.
        _row(row_type="question", row_id="q2", paper_year="2020", difficulty="hard"),
        # assign_topic_id only.
        _row(row_type="question", row_id="q3", paper_year="2020", assign_topic_id="TID"),
        # all three at once.
        _row(row_type="question", row_id="q4", paper_year="2020", decision="verified",
             assign_topic_id="TID2", difficulty="easy"),
        # entirely blank — skipped, exactly as a blank decision always was.
        _row(row_type="question", row_id="q5", paper_year="2020"),
        # tag row, decision only.
        _row(row_type="tag", row_id="t1", paper_year="2020", decision="rejected"),
    ]
    ws = _write_worksheet(tmp_path, rows)
    fake = FakeClient()
    args = _apply_args(ws, _catalog(tmp_path), apply=True, confirm=True)
    assert mod.do_apply(fake, args) == 0

    assert [c["path"] for c in fake.calls if "/items/" in c["path"] and "/q1/" in c["path"]] == [
        "/api/admin/exam-intelligence/items/pyq_question/q1/review"]
    # q2: difficulty only, no review call.
    q2 = [c for c in fake.calls if c["path"].endswith("/pyq-questions/q2")]
    assert len(q2) == 1 and q2[0]["body"]["payload"] == {"observed_difficulty": "hard"}
    assert not [c for c in fake.calls if "/q2/review" in c["path"]]
    # q3: tag create only.
    q3 = [c for c in fake.calls
          if c["method"] == "POST" and c["body"]["payload"]["question_id"] == "q3"]
    assert len(q3) == 1
    assert not [c for c in fake.calls if "/q3/review" in c["path"]]
    # q4: all three, content edits first, the verdict last.
    q4 = [c for c in fake.calls
          if "/q4" in c["path"] or c["body"].get("payload", {}).get("question_id") == "q4"]
    assert [c["method"] for c in q4] == ["PATCH", "POST", "PATCH"]
    assert q4[0]["path"].endswith("/pyq-questions/q4")
    assert q4[1]["path"].endswith("/pyq-question-topic-tags")
    assert q4[2]["path"] == "/api/admin/exam-intelligence/items/pyq_question/q4/review"
    # q5: untouched.
    assert not [c for c in fake.calls if "q5" in json.dumps(c)]
    # t1: unchanged review PATCH on the tag kind.
    assert [c for c in fake.calls if "/t1/" in c["path"]][0]["body"] == {
        "reviewer_status": "rejected"}


def test_a_failed_content_write_does_not_promote_the_row(tmp_path, capsys):
    """A decision is the promotion. If the difficulty write failed, the row
    must not be verified on the strength of a half-applied worksheet row."""
    rows = [_row(row_type="question", row_id="q1", paper_year="2020",
                 decision="verified", difficulty="hard")]
    ws = _write_worksheet(tmp_path, rows)
    fake = FakeClient(fail_on=("/pyq-questions/q1",))
    args = _apply_args(ws, _catalog(tmp_path), apply=True, confirm=True)
    assert mod.do_apply(fake, args) == 1
    assert len(fake.calls) == 1                    # the review PATCH never ran
    assert not [c for c in fake.calls if "/review" in c["path"]]
    assert "SKIPPED" in capsys.readouterr().err


def test_an_old_worksheet_without_the_new_columns_applies_unchanged(tmp_path):
    """A CSV written before assign_topic_id/difficulty existed must behave
    exactly as it did then — the missing keys read as blank."""
    old_fields = ["row_type", "row_id", "paper_year", "question_number_or_topic_id",
                  "text_preview", "flags", "sample_reason", "decision", "notes"]
    ws = tmp_path / "old_worksheet.csv"
    with ws.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=old_fields)
        w.writeheader()
        w.writerow({k: "" for k in old_fields} | {
            "row_type": "question", "row_id": "q1", "paper_year": "2020",
            "decision": "verified"})
        w.writerow({k: "" for k in old_fields} | {
            "row_type": "tag", "row_id": "t1", "paper_year": "2020",
            "decision": "needs_correction", "notes": "wrong topic"})
        w.writerow({k: "" for k in old_fields} | {
            "row_type": "question", "row_id": "q2", "paper_year": "2020"})

    fake = FakeClient()
    args = _apply_args(ws, _catalog(tmp_path), apply=True, confirm=True)
    assert mod.do_apply(fake, args) == 0
    assert [(c["method"], c["path"], c["body"]) for c in fake.calls] == [
        ("PATCH", "/api/admin/exam-intelligence/items/pyq_question/q1/review",
         {"reviewer_status": "verified"}),
        ("PATCH", "/api/admin/exam-intelligence/items/pyq_question_topic_tag/t1/review",
         {"reviewer_status": "needs_correction", "reviewer_notes": "wrong topic"}),
    ]


def test_dry_run_validates_and_reports_the_new_fields_without_writing(tmp_path, capsys):
    rows = [_row(row_type="question", row_id="q1", paper_year="2020",
                 decision="verified", assign_topic_id="TID", difficulty="hard")]
    ws = _write_worksheet(tmp_path, rows)
    fake = FakeClient()
    args = _apply_args(ws, _catalog(tmp_path))  # dry run
    assert mod.do_apply(fake, args) == 0
    assert fake.calls == []
    out = capsys.readouterr().out
    assert "DRY RUN" in out
    assert "assign_topic_id" in out and "difficulty:hard" in out and "verified" in out


# ─── export helpers (pure) ───────────────────────────────────────────────────
_PAPERS = [
    {"id": "p1", "exam_phase_id": "MAINS", "year": 2020},
    {"id": "p2", "exam_phase_id": "PRELIMS", "year": 2020},
    {"id": "p3", "exam_phase_id": "MAINS", "year": 2019},
    {"id": "p4", "exam_phase_id": "PRELIMS", "year": 2018},
    {"id": "p5", "year": 2017},  # no phase at all
]


def test_select_papers_by_mains_phase():
    got = mod.select_papers(_PAPERS, {"MAINS"}, None)
    assert {p["id"] for p in got} == {"p1", "p3"}


def test_select_papers_by_prelims_phase():
    """The same scoping mechanism, pointed at a non-Mains phase."""
    got = mod.select_papers(_PAPERS, {"PRELIMS"}, None)
    assert {p["id"] for p in got} == {"p2", "p4"}


def test_select_papers_accepts_several_phases():
    got = mod.select_papers(_PAPERS, {"MAINS", "PRELIMS"}, None)
    assert {p["id"] for p in got} == {"p1", "p2", "p3", "p4"}


def test_explicit_paper_ids_bypass_the_phase_filter():
    """Naming a paper is the scope — a phase mismatch must not empty the run.

    This is the case that used to fail: a Prelims paper id passed while the
    phase scope still defaulted to Mains returned nothing at all.
    """
    got = mod.select_papers(_PAPERS, {"MAINS"}, {"p2", "p4"})
    assert {p["id"] for p in got} == {"p2", "p4"}


def test_explicit_paper_id_reaches_a_paper_with_no_phase():
    got = mod.select_papers(_PAPERS, {"MAINS"}, {"p5"})
    assert {p["id"] for p in got} == {"p5"}


def test_select_papers_never_falls_through_to_everything():
    """No scope must mean no papers, never the whole exam."""
    assert mod.select_papers(_PAPERS, None, None) == []
    assert mod.select_papers(_PAPERS, set(), None) == []


def test_export_parser_accepts_repeatable_exam_phase_id():
    args = mod.build_parser().parse_args([
        "export", "--exam-phase-id", "PRELIMS", "--exam-phase-id", "CSAT",
    ])
    assert args.exam_phase_id == ["PRELIMS", "CSAT"]
    # --mains-phase-id keeps its default so Mains invocations are unchanged.
    assert args.mains_phase_id == mod.DEFAULT_MAINS_PHASE_ID


def test_merge_questions_carries_type_and_correct_option():
    """Both are needed offline so the sweep can raise mcq_no_correct_option."""
    pending = [{"id": "q1", "pyq_paper_id": "p1", "question_number": 1,
                "reviewer_status": "pending"}]
    cms = {"q1": {"id": "q1", "pyq_paper_id": "p1", "question_text": "Stem?",
                  "question_type": "mcq", "correct_option_id": "opt-2"}}
    row = mod.merge_questions(pending, cms, {"p1": 2024}, {})[0]
    assert row["question_type"] == "mcq"
    assert row["correct_option_id"] == "opt-2"


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


# ─── catalog: multi-body, microtopic-only ────────────────────────────────────
def _topic(tid, *, level="microtopic", exams=("rbi",), subject="s1",
           name=None, is_active=True):
    row = {"id": tid, "level": level, "subject_id": subject,
           "slug": f"slug-{tid}", "name": name or f"Topic {tid}",
           "is_active": is_active}
    if exams is not None:
        row["metadata"] = {"tier": "official", "exams": list(exams)}
    return row


def test_catalog_spans_several_body_keys_in_one_file():
    """RBI shares subjects with sebi/pfrda/ifsca — one catalogue, all bodies."""
    topics = [
        _topic("t-rbi", exams=["rbi"]),
        _topic("t-sebi", exams=["sebi"]),
        _topic("t-pfrda", exams=["pfrda"]),
        _topic("t-ifsca", exams=["ifsca"]),
        _topic("t-upsc", exams=["upsc"]),
    ]
    rows = mod.catalog_rows(topics, ["rbi", "sebi", "pfrda", "ifsca"])
    assert {r["id"] for r in rows} == {"t-rbi", "t-sebi", "t-pfrda", "t-ifsca"}
    # A body outside the requested set is not pulled in.
    assert "t-upsc" not in {r["id"] for r in rows}


def test_catalog_emits_a_shared_microtopic_exactly_once():
    """A row listing several requested bodies is one row, not one per body."""
    topics = [_topic("shared", exams=["rbi", "sebi", "pfrda", "ifsca"])]
    rows = mod.catalog_rows(topics, ["rbi", "sebi", "pfrda", "ifsca"])
    assert len(rows) == 1
    assert rows[0]["exams"] == ["ifsca", "pfrda", "rbi", "sebi"]


def test_catalog_matches_on_intersection_not_equality():
    """A row carrying MORE bodies than asked for still matches."""
    topics = [_topic("t1", exams=["rbi", "sebi", "upsc"])]
    rows = mod.catalog_rows(topics, ["rbi"])
    assert [r["id"] for r in rows] == ["t1"]
    assert rows[0]["exams"] == ["rbi"]  # only the requested overlap is reported


def test_catalog_excludes_every_non_microtopic_level():
    topics = [
        _topic("leaf", level="microtopic"),
        _topic("parent", level="topic"),
        _topic("concept", level="concept"),
    ]
    rows = mod.catalog_rows(topics, ["rbi"])
    assert [r["id"] for r in rows] == ["leaf"]
    assert all(r["level"] == "microtopic" for r in rows)


def test_catalog_drops_rows_with_no_or_malformed_exams_key():
    topics = [
        _topic("ok"),
        _topic("no-meta", exams=None),
        {"id": "meta-not-dict", "level": "microtopic", "metadata": "rbi"},
        {"id": "exams-not-list", "level": "microtopic", "metadata": {"exams": "rbi"}},
    ]
    rows = mod.catalog_rows(topics, ["rbi"])
    assert [r["id"] for r in rows] == ["ok"]


def test_catalog_drops_inactive_rows_and_casefolds_bodies():
    topics = [
        _topic("live", exams=["RBI"], is_active=True),
        _topic("dead", exams=["rbi"], is_active=False),
    ]
    rows = mod.catalog_rows(topics, ["rBi"])
    assert [r["id"] for r in rows] == ["live"]


def test_catalog_is_byte_stable_across_input_order():
    a = [_topic("t2", name="Beta", subject="s1"), _topic("t1", name="Alpha", subject="s1")]
    b = list(reversed(a))
    assert mod.catalog_rows(a, ["rbi"]) == mod.catalog_rows(b, ["rbi"])


def test_catalog_requires_at_least_one_body():
    with pytest.raises(ValueError):
        mod.catalog_rows([_topic("t1")], [])


def test_catalog_output_loads_back_through_load_topic_catalog(tmp_path):
    """The file `catalog` writes is exactly what `sweep`/`apply` accept."""
    rows = mod.catalog_rows(
        [_topic("t1", exams=["rbi"]), _topic("t2", exams=["sebi"])], ["rbi", "sebi"])
    p = tmp_path / "cat.json"
    p.write_text(json.dumps(rows), encoding="utf-8")
    valid, orphan, names = mod.load_topic_catalog(str(p))
    assert valid == {"t1", "t2"}
    assert orphan == set()
    assert names["t1"] == "Topic t1"


def test_do_catalog_unions_bodies_and_writes_the_file(tmp_path):
    class TopicsClient:
        def __init__(self, topics):
            self.topics = topics
            self.params = []

        def all_items(self, path, params=None):
            self.params.append((path, dict(params or {})))
            return list(self.topics)

    topics = [_topic("t1", exams=["rbi"]), _topic("t2", exams=["sebi", "rbi"]),
              _topic("t3", exams=["upsc"]), _topic("t4", level="topic", exams=["rbi"])]
    c = TopicsClient(topics)
    out = tmp_path / "cat.json"
    args = mod.build_parser().parse_args(
        ["catalog", "--body", "rbi", "--body", "sebi", "--out", str(out), "--apply"])
    assert mod.do_catalog(c, args) == 0

    # level is narrowed server-side; the body filter is not a server predicate.
    assert c.params[0][0].endswith("/topics")
    assert c.params[0][1]["level"] == "microtopic"
    assert "exams" not in c.params[0][1] and "body" not in c.params[0][1]

    written = json.loads(out.read_text(encoding="utf-8"))
    assert {r["id"] for r in written} == {"t1", "t2"}


def test_do_catalog_dry_run_writes_nothing(tmp_path):
    class TopicsClient:
        def all_items(self, path, params=None):
            return [_topic("t1", exams=["rbi"])]

    out = tmp_path / "cat.json"
    args = mod.build_parser().parse_args(["catalog", "--body", "rbi", "--out", str(out)])
    assert mod.do_catalog(TopicsClient(), args) == 0
    assert not out.exists()


# ─── load_topic_catalog: microtopic-only, strict when known ──────────────────
def test_load_topic_catalog_rejects_a_top_level_topic_id(tmp_path):
    p = tmp_path / "cat.json"
    p.write_text(json.dumps([
        {"id": "leaf", "text": "Leaf", "level": "microtopic"},
        {"id": "parent", "text": "Parent", "level": "topic"},
    ]), encoding="utf-8")
    with pytest.raises(ValueError) as exc:
        mod.load_topic_catalog(str(p))
    assert "parent" in str(exc.value)
    assert "microtopic" in str(exc.value)


def test_load_topic_catalog_still_accepts_a_flat_levelless_catalogue(tmp_path):
    """The hand-written UPSC files are [{id, text}] and must keep loading."""
    p = tmp_path / "cat.json"
    p.write_text(json.dumps([{"id": "a", "text": "A"}, {"id": "b", "text": "B"}]),
                 encoding="utf-8")
    valid, orphan, names = mod.load_topic_catalog(str(p))
    assert valid == {"a", "b"} and orphan == set() and names["a"] == "A"


# ─── difficulty: write without a tag, and clear back to null ─────────────────
def test_difficulty_writes_without_any_tag_or_decision(tmp_path):
    """The shape the three tagged exams need: difficulty only, nothing else."""
    rows = [_row(row_type="question", row_id="q1", paper_year="2020",
                 difficulty="hard", assign_topic_id="", decision="")]
    ws = _write_worksheet(tmp_path, rows)
    fake = FakeClient()
    assert mod.do_apply(fake, _apply_args(ws, _catalog(tmp_path), apply=True, confirm=True)) == 0
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call["method"] == "PATCH"
    assert call["path"] == "/api/admin/exam-intelligence-cms/pyq-questions/q1"
    assert call["body"]["payload"] == {"observed_difficulty": "hard"}
    # No tag was created and no review verdict was sent.
    assert all("topic-tags" not in c["path"] and "/review" not in c["path"]
               for c in fake.calls)


def test_difficulty_none_clears_the_value_to_null(tmp_path):
    rows = [_row(row_type="question", row_id="q1", paper_year="2020", difficulty="none")]
    ws = _write_worksheet(tmp_path, rows)
    fake = FakeClient()
    assert mod.do_apply(fake, _apply_args(ws, _catalog(tmp_path), apply=True, confirm=True)) == 0
    assert len(fake.calls) == 1
    assert fake.calls[0]["body"]["payload"] == {"observed_difficulty": None}
    assert "clear" in fake.calls[0]["body"]["reason"]


def test_difficulty_clear_is_case_insensitive_like_every_other_value(tmp_path):
    rows = [_row(row_type="question", row_id="q1", paper_year="2020", difficulty="NONE")]
    ws = _write_worksheet(tmp_path, rows)
    fake = FakeClient()
    assert mod.do_apply(fake, _apply_args(ws, _catalog(tmp_path), apply=True, confirm=True)) == 0
    assert fake.calls[0]["body"]["payload"] == {"observed_difficulty": None}


def test_a_blank_difficulty_still_never_clears_anything(tmp_path):
    """Blank means 'leave alone'. Clearing must be typed, or a sweep of
    untouched rows would wipe the corpus."""
    rows = [_row(row_type="question", row_id="q1", paper_year="2020",
                 difficulty="", decision="verified")]
    ws = _write_worksheet(tmp_path, rows)
    fake = FakeClient()
    assert mod.do_apply(fake, _apply_args(ws, _catalog(tmp_path), apply=True, confirm=True)) == 0
    assert all("pyq-questions/" not in c["path"] for c in fake.calls)


def test_clearing_difficulty_composes_with_a_decision(tmp_path):
    rows = [_row(row_type="question", row_id="q1", paper_year="2020",
                 difficulty="none", decision="verified")]
    ws = _write_worksheet(tmp_path, rows)
    fake = FakeClient()
    assert mod.do_apply(fake, _apply_args(ws, _catalog(tmp_path), apply=True, confirm=True)) == 0
    paths = [c["path"] for c in fake.calls]
    # Content edit runs BEFORE the verdict, unchanged by the clear path.
    assert paths == ["/api/admin/exam-intelligence-cms/pyq-questions/q1",
                     "/api/admin/exam-intelligence/items/pyq_question/q1/review"]


def test_a_failed_clear_does_not_promote_the_row(tmp_path, capsys):
    rows = [_row(row_type="question", row_id="q1", paper_year="2020",
                 difficulty="none", decision="verified")]
    ws = _write_worksheet(tmp_path, rows)
    fake = FakeClient(fail_on=("pyq-questions/",))
    assert mod.do_apply(fake, _apply_args(ws, _catalog(tmp_path), apply=True, confirm=True)) == 1
    assert all("/review" not in c["path"] for c in fake.calls)


def test_difficulty_clear_is_rejected_on_a_tag_row(tmp_path, capsys):
    rows = [_row(row_type="tag", row_id="t1", paper_year="2020", difficulty="none")]
    ws = _write_worksheet(tmp_path, rows)
    fake = FakeClient()
    assert mod.do_apply(fake, _apply_args(ws, _catalog(tmp_path), apply=True, confirm=True)) == 2
    assert fake.calls == []


def test_clear_sentinel_is_not_smuggled_into_the_difficulty_vocabulary():
    """`none` must never reach the API as a literal observed_difficulty."""
    assert mod.DIFFICULTY_CLEAR not in mod.DIFFICULTIES


@pytest.mark.parametrize("bad", ["null", "nil", "clear", "blank", "-"])
def test_only_the_documented_clear_token_is_accepted(tmp_path, bad):
    rows = [_row(row_type="question", row_id="q1", paper_year="2020", difficulty=bad)]
    ws = _write_worksheet(tmp_path, rows)
    fake = FakeClient()
    assert mod.do_apply(fake, _apply_args(ws, _catalog(tmp_path), apply=True, confirm=True)) == 2
    assert fake.calls == []


# ─── timeout ─────────────────────────────────────────────────────────────────
def test_timeout_defaults_to_180_on_every_subcommand():
    p = mod.build_parser()
    for argv in (["catalog", "--body", "rbi"],
                 ["export", "--exam-id", "e1"],
                 ["apply", "--worksheet", "w.csv", "--topic-catalog", "c.json"]):
        assert p.parse_args(argv).timeout == mod.DEFAULT_TIMEOUT == 180


def test_timeout_is_overridable_and_reaches_the_client():
    args = mod.build_parser().parse_args(["--timeout", "300", "catalog", "--body", "rbi"])
    assert args.timeout == 300


# ─── option flags ────────────────────────────────────────────────────────────
def _opt(text="Option text", correct=False, label="a"):
    return {"question_id": "q1", "option_label": label, "option_text": text,
            "is_correct": correct}


def _mcq(**kw):
    base = {"id": "q1", "question_type": "mcq", "correct_option_id": "opt-2",
            "question_text": "A properly long and valid question stem here?"}
    base.update(kw)
    return base


def _four(correct_at=1):
    return [_opt(f"Choice {i}", correct=(i == correct_at), label=chr(97 + i))
            for i in range(4)]


def test_a_well_formed_mcq_raises_no_option_flag():
    assert mod.option_flags(_mcq(), _four()) == []


@pytest.mark.parametrize("n", [0, 1, 2, 3, 6, 7])
def test_option_count_outside_the_expected_range_flags(n):
    opts = [_opt(f"Choice {i}", correct=(i == 0), label=chr(97 + i)) for i in range(n)]
    assert "option_count_unexpected" in mod.option_flags(_mcq(), opts)


@pytest.mark.parametrize("n", [4, 5])
def test_four_and_five_options_are_accepted(n):
    opts = [_opt(f"Choice {i}", correct=(i == 0), label=chr(97 + i)) for i in range(n)]
    assert "option_count_unexpected" not in mod.option_flags(_mcq(), opts)


def test_no_option_marked_correct_flags():
    opts = [_opt(f"Choice {i}", correct=False, label=chr(97 + i)) for i in range(4)]
    flags = mod.option_flags(_mcq(), opts)
    assert "no_option_marked_correct" in flags
    assert "multiple_options_marked_correct" not in flags


def test_more_than_one_correct_flags():
    opts = _four()
    opts[2]["is_correct"] = True
    flags = mod.option_flags(_mcq(), opts)
    assert "multiple_options_marked_correct" in flags
    assert "no_option_marked_correct" not in flags


def test_duplicate_option_text_flags_once():
    opts = _four()
    opts[3]["option_text"] = opts[0]["option_text"]
    flags = mod.option_flags(_mcq(), opts)
    assert flags.count("duplicate_option_text") == 1


def test_duplicate_detection_normalises_whitespace_and_case():
    opts = _four()
    opts[3]["option_text"] = "  " + opts[0]["option_text"].upper() + " "
    assert "duplicate_option_text" in mod.option_flags(_mcq(), opts)


def test_blank_option_texts_are_not_duplicates_of_each_other():
    """Two empty options are a count/content problem, not a duplicate claim."""
    opts = _four()
    opts[2]["option_text"] = ""
    opts[3]["option_text"] = "   "
    assert "duplicate_option_text" not in mod.option_flags(_mcq(), opts)


def test_option_flags_never_fire_on_a_descriptive_question():
    q = _mcq(question_type="descriptive", correct_option_id=None)
    assert mod.option_flags(q, []) == []


def test_absent_options_file_runs_no_option_checks():
    """None means 'did not look', and must not read as 'looked and passed'."""
    assert mod.option_flags(_mcq(), None) == []


def test_option_flags_compose_rather_than_short_circuit():
    opts = [_opt("Same", correct=True, label="a"), _opt("Same", correct=True, label="b")]
    flags = mod.option_flags(_mcq(), opts)
    assert set(flags) == {"option_count_unexpected", "multiple_options_marked_correct",
                          "duplicate_option_text"}


def test_index_options_by_question_preserves_the_none_distinction():
    assert mod.index_options_by_question(None) is None
    idx = mod.index_options_by_question([_opt(), {**_opt(), "question_id": "q2"}])
    assert set(idx) == {"q1", "q2"}


# ─── stimuli ─────────────────────────────────────────────────────────────────
def _stim(sid="s1", qids=("q1",), text="Seven people sit in a row facing north.",
          kind="passage", order=1):
    return {"id": sid, "stimulus_type": kind, "content_text": text,
            "display_order": order, "question_ids": list(qids)}


def test_index_stimuli_by_question_fans_one_stimulus_across_its_members():
    idx = mod.index_stimuli_by_question([_stim(qids=("q1", "q2", "q3"))])
    assert set(idx) == {"q1", "q2", "q3"}
    assert idx["q2"][0]["id"] == "s1"


def test_index_stimuli_handles_no_stimuli():
    assert mod.index_stimuli_by_question(None) == {}
    assert mod.index_stimuli_by_question([]) == {}


def test_stimulus_preview_shows_the_setup_and_its_type():
    out = mod.stimulus_preview([_stim()])
    assert out.startswith("[passage] ")
    assert "Seven people sit in a row" in out


def test_stimulus_preview_joins_several_in_display_order():
    out = mod.stimulus_preview([
        _stim(sid="s2", text="Second thing", kind="table", order=2),
        _stim(sid="s1", text="First thing", kind="passage", order=1),
    ])
    assert out.index("First thing") < out.index("Second thing")
    assert "[table]" in out and "[passage]" in out


def test_stimulus_preview_is_blank_without_a_stimulus():
    assert mod.stimulus_preview([]) == ""


# ─── worksheet integration ───────────────────────────────────────────────────
def _wq(qid, **kw):
    base = {"id": qid, "paper_id": "p1", "year": 2024, "question_number": 1,
            "question_type": "mcq", "correct_option_id": "opt-2",
            "question_text": "A properly long and valid question stem here?"}
    base.update(kw)
    return base


def _primary(qid):
    return {"id": f"t-{qid}", "question_id": qid, "topic_id": "TID",
            "tag_role": "primary", "reviewer_status": "verified"}


def test_worksheet_carries_the_stimulus_next_to_each_set_member():
    qs = [_wq("q1", question_number=1), _wq("q2", question_number=2)]
    stimuli = [_stim(qids=("q1", "q2"), text="Table: sales by month.", kind="table")]
    rows = mod.build_worksheet(qs, [_primary("q1"), _primary("q2")], {"TID"}, set(),
                               {"TID": "T"}, set(), stimuli=stimuli)
    qrows = [r for r in rows if r["row_type"] == "question"]
    assert len(qrows) == 2
    assert all("Table: sales by month." in r["stimulus_preview"] for r in qrows)


def test_worksheet_stimulus_column_is_blank_without_the_file():
    rows = mod.build_worksheet([_wq("q1")], [_primary("q1")], {"TID"}, set(),
                               {"TID": "T"}, set())
    assert [r["stimulus_preview"] for r in rows if r["row_type"] == "question"] == [""]


def test_tag_rows_never_carry_a_stimulus_preview():
    rows = mod.build_worksheet([_wq("q1")], [_primary("q1")], {"TID"}, set(),
                               {"TID": "T"}, set(),
                               stimuli=[_stim(qids=("q1",))])
    assert all(r["stimulus_preview"] == "" for r in rows if r["row_type"] == "tag")


def test_an_option_defect_flags_the_row_and_bars_it_from_the_clean_path():
    """Same contract as every existing check: flagged rows go to a human."""
    opts = [{**o, "question_id": "q1"} for o in _four(correct_at=0)]
    opts[1]["is_correct"] = True          # two correct
    rows = mod.build_worksheet([_wq("q1")], [_primary("q1")], {"TID"}, set(),
                               {"TID": "T"}, set(), options=opts)
    q = [r for r in rows if r["row_type"] == "question"][0]
    assert "multiple_options_marked_correct" in q["flags"]
    assert q["sample_reason"] == "flagged"
    assert q["sample_reason"] != "spot_check"


def test_a_clean_mcq_with_good_options_stays_eligible_for_spot_check():
    opts = [{**o, "question_id": "q1"} for o in _four()]
    rows = mod.build_worksheet([_wq("q1")], [_primary("q1")], {"TID"}, set(),
                               {"TID": "T"}, set(), options=opts)
    q = [r for r in rows if r["row_type"] == "question"][0]
    assert q["flags"] == ""
    assert q["sample_reason"] == "spot_check"


def test_worksheet_without_options_does_not_flag_a_broken_mcq():
    """Proves the checks are genuinely off, not silently passing."""
    rows = mod.build_worksheet([_wq("q1")], [_primary("q1")], {"TID"}, set(),
                               {"TID": "T"}, set())
    q = [r for r in rows if r["row_type"] == "question"][0]
    assert "no_option_marked_correct" not in q["flags"]


def test_new_column_is_appended_so_older_worksheets_still_read():
    assert mod.WORKSHEET_FIELDS[-1] == "stimulus_preview"
    assert mod.WORKSHEET_FIELDS[:11] == [
        "row_type", "row_id", "paper_year", "question_number_or_topic_id",
        "text_preview", "flags", "sample_reason", "decision", "notes",
        "assign_topic_id", "difficulty"]


# ─── export fetch shapes ─────────────────────────────────────────────────────
def test_options_page_matches_the_routes_lower_limit_cap():
    """/pyq-options is le=50; paging it at the usual 200 would 422."""
    assert mod._OPTIONS_PAGE == 50


class ExportClient:
    """Serves only the routes `do_export` calls, recording how it called them."""

    PAPER = "p1"
    PHASE = "ph1"

    def __init__(self, options_by_q=None, stimuli=None, links=None):
        self.calls = []
        self._options = options_by_q or {}
        self._stimuli = stimuli or []
        self._links = links or {}

    def all_items(self, path, params=None, page=200):
        params = dict(params or {})
        self.calls.append({"path": path, "params": params, "page": page})
        if path.endswith("/pyq-papers"):
            return [{"id": self.PAPER, "year": 2024, "exam_phase_id": self.PHASE}]
        if path.endswith("/exam-phase-sections"):
            return [{"id": "sec1", "section_label": "Reasoning"}]
        if path.endswith("/pyq-questions"):
            return [{"id": "q1", "question_number": 1, "question_type": "mcq",
                     "question_text": "Who sits immediate right of R?",
                     "pyq_paper_id": self.PAPER, "correct_option_id": "o2",
                     "section_id": "sec1"}]
        if path.endswith("/items"):
            kind = params.get("kind")
            if kind == "pyq_question":
                return [{"id": "q1", "pyq_paper_id": self.PAPER, "question_number": 1}]
            return []
        if path.endswith("/pyq-question-topic-tags"):
            return []
        if path.endswith("/pyq-stimuli"):
            return [s for s in self._stimuli if s["pyq_paper_id"] == params.get("pyq_paper_id")]
        if path.endswith("/pyq-question-stimuli"):
            return self._links.get(params.get("stimulus_id"), [])
        if path.endswith("/pyq-options"):
            return self._options.get(params.get("question_id"), [])
        raise AssertionError(f"unexpected route {path}")


def _export_args(out, **kw):
    argv = ["export", "--exam-id", "e1", "--paper-id", ExportClient.PAPER,
            "--out", str(out)]
    for k, v in kw.items():
        if v is True:
            argv.append(f"--{k}")
    return mod.build_parser().parse_args(argv)


def _export_fixture():
    stim = {"id": "s1", "pyq_paper_id": ExportClient.PAPER, "section_id": "sec1",
            "stimulus_type": "passage", "content_text": "Seven people sit in a row.",
            "language": "en", "display_order": 1, "reviewer_status": "verified"}
    links = {"s1": [{"id": "l1", "question_id": "q1", "stimulus_id": "s1",
                     "reviewer_status": "pending"}]}
    opts = {"q1": [{"id": f"o{i}", "option_label": chr(97 + i),
                    "option_text": f"Choice {i}", "is_correct": i == 2,
                    "display_order": i, "reviewer_status": "verified"}
                   for i in range(4)]}
    return stim, links, opts


def test_export_writes_all_four_files(tmp_path):
    stim, links, opts = _export_fixture()
    c = ExportClient(options_by_q=opts, stimuli=[stim], links=links)
    assert mod.do_export(c, _export_args(tmp_path, apply=True)) == 0
    for name in ("questions_export.json", "tags_export.json",
                 "stimuli_export.json", "options_export.json"):
        assert (tmp_path / name).exists(), name


def test_export_keys_stimuli_on_paper_and_links_on_stimulus(tmp_path):
    """The routes allow nothing else: /pyq-stimuli filters by paper only, and
    /pyq-question-stimuli takes no paper filter."""
    stim, links, opts = _export_fixture()
    c = ExportClient(options_by_q=opts, stimuli=[stim], links=links)
    mod.do_export(c, _export_args(tmp_path, apply=True))
    st_calls = [x for x in c.calls if x["path"].endswith("/pyq-stimuli")]
    lk_calls = [x for x in c.calls if x["path"].endswith("/pyq-question-stimuli")]
    assert [x["params"] for x in st_calls] == [{"pyq_paper_id": ExportClient.PAPER}]
    assert [x["params"] for x in lk_calls] == [{"stimulus_id": "s1"}]


def test_export_pages_options_at_the_routes_cap(tmp_path):
    stim, links, opts = _export_fixture()
    c = ExportClient(options_by_q=opts, stimuli=[stim], links=links)
    mod.do_export(c, _export_args(tmp_path, apply=True))
    opt_calls = [x for x in c.calls if x["path"].endswith("/pyq-options")]
    assert opt_calls, "options were never fetched"
    assert all(x["page"] == 50 for x in opt_calls)
    assert [x["params"] for x in opt_calls] == [{"question_id": "q1"}]


def test_exported_stimulus_resolves_its_question_ids_and_link_status(tmp_path):
    stim, links, opts = _export_fixture()
    c = ExportClient(options_by_q=opts, stimuli=[stim], links=links)
    mod.do_export(c, _export_args(tmp_path, apply=True))
    got = json.loads((tmp_path / "stimuli_export.json").read_text(encoding="utf-8"))
    assert len(got) == 1
    assert got[0]["question_ids"] == ["q1"]
    # The LINK's own reviewer_status is preserved, not the stimulus's.
    assert got[0]["reviewer_status"] == "verified"
    assert got[0]["link_status_by_question"] == {"q1": "pending"}


def test_exported_options_carry_the_correctness_marker(tmp_path):
    stim, links, opts = _export_fixture()
    c = ExportClient(options_by_q=opts, stimuli=[stim], links=links)
    mod.do_export(c, _export_args(tmp_path, apply=True))
    got = json.loads((tmp_path / "options_export.json").read_text(encoding="utf-8"))
    assert len(got) == 4
    assert all(o["question_id"] == "q1" for o in got)
    assert sum(1 for o in got if o["is_correct"]) == 1


def test_export_links_are_scoped_to_the_exported_questions(tmp_path):
    """A stimulus shared with an out-of-scope question must not leak that id."""
    stim, links, opts = _export_fixture()
    links["s1"].append({"id": "l2", "question_id": "q-other", "stimulus_id": "s1",
                        "reviewer_status": "verified"})
    c = ExportClient(options_by_q=opts, stimuli=[stim], links=links)
    mod.do_export(c, _export_args(tmp_path, apply=True))
    got = json.loads((tmp_path / "stimuli_export.json").read_text(encoding="utf-8"))
    assert got[0]["question_ids"] == ["q1"]


def test_export_writes_empty_files_when_there_are_none(tmp_path):
    """An empty file says 'we looked'; an absent one says nothing."""
    c = ExportClient(options_by_q={}, stimuli=[], links={})
    assert mod.do_export(c, _export_args(tmp_path, apply=True)) == 0
    assert json.loads((tmp_path / "stimuli_export.json").read_text(encoding="utf-8")) == []
    assert json.loads((tmp_path / "options_export.json").read_text(encoding="utf-8")) == []


def test_export_dry_run_writes_nothing(tmp_path):
    stim, links, opts = _export_fixture()
    c = ExportClient(options_by_q=opts, stimuli=[stim], links=links)
    assert mod.do_export(c, _export_args(tmp_path)) == 0
    assert not (tmp_path / "stimuli_export.json").exists()
    assert not (tmp_path / "options_export.json").exists()


def test_export_makes_no_write_calls(tmp_path):
    """export is read-only: the fake client has no patch/post at all."""
    stim, links, opts = _export_fixture()
    c = ExportClient(options_by_q=opts, stimuli=[stim], links=links)
    mod.do_export(c, _export_args(tmp_path, apply=True))
    assert not hasattr(c, "patch") and not hasattr(c, "post")
