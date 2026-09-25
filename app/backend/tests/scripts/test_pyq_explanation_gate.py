"""Unit tests for ``scripts/pyq_explanation_gate.py``.

Loaded by absolute path, like ``test_ssc_cgl_readiness.py``: ``scripts`` under
the backend rootdir resolves to app/backend/scripts.

Coverage:
- `input` scopes by exam, paper, verified status, MCQ, subject, projection and
  existing explanations, counts every exclusion, and carries the stimulus;
- `input` refuses an export holding another exam's paper;
- the gate passes a clean row and emits the CMS shape (rationales folded to
  {option_id: text}, formula wrapped, final answer = key, no reviewer_status);
- each hard flag quarantines, and a `verified` signature cannot release it;
- soft flags quarantine but release on a `verified` signature;
- the answer-phrase check flags an announced other option and ignores a
  passing mention;
- the quarantine CSV has the review-worksheet columns with `decision` blank;
- dry run writes nothing.

Fully offline.
"""
from __future__ import annotations

import csv
import importlib.util
import io
import json
import pathlib

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_SCRIPT = _ROOT / "scripts" / "pyq_explanation_gate.py"
_spec = importlib.util.spec_from_file_location("pyq_explanation_gate", _SCRIPT)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

EXAM = "exam-1"
QA = "Quantitative Aptitude"
GA = "General Awareness"
ALIASES = {QA: "quantitative-aptitude", GA: "general-awareness"}


def _q(qid, *, paper="p1", section=QA, status="verified", qtype="mcq", key="o-c", n=1):
    return {"id": qid, "paper_id": paper, "year": 2024, "section": section,
            "question_number": n, "question_type": qtype, "question_text": f"stem {qid}",
            "correct_option_id": key and f"{qid}-{key}", "reviewer_status": status}


def _opts(qid, correct="c", labels="abcd"):
    return [{"id": f"{qid}-o-{l}", "question_id": qid, "option_label": l.upper(),
             "option_text": f"opt {l}", "is_correct": l == correct,
             "reviewer_status": "verified"} for l in labels]


PAPERS = [{"id": "p1", "exam_id": EXAM}, {"id": "p2", "exam_id": EXAM}]


def _input_row(qid="q1", key="c"):
    return {
        "question_id": qid, "year": 2024, "question_number": 1, "question_text": "What is 6x7?",
        "options": [{"id": f"{qid}-o-{l}", "label": l, "text": l, "correct": l == key} for l in "abcd"],
        "correct_option_id": f"{qid}-o-{key}", "subject_slug": "quantitative-aptitude",
        "topic_name": "", "paper_id": "p1", "section": QA, "stimulus_text": "",
    }


def _draft(qid="q1", final="c", verdict="AGREE", labels="abcd", text="6 x 7 = 42."):
    return {
        "question_id": qid, "short_explanation": text, "explanation_text": "",
        "option_rationales": [{"option_id": f"{qid}-o-{l}", "label": l, "rationale": f"r {l}"}
                              for l in labels],
        "solution_steps": [], "formula_used": "a x b", "common_traps": [],
        "key_verdict": verdict, "proposed_correct_option_id": None,
        "final_answer_option_id": final and f"{qid}-o-{final}",
        "explanation_source_type": "platform_original", "license_status": "owned",
        "reviewer_status": "pending",
    }


# ─── input ───────────────────────────────────────────────────────────────────
def test_input_scopes_and_counts_every_exclusion():
    questions = [
        _q("in1"), _q("in2", paper="p2", n=2),
        _q("pend", status="pending"), _q("desc", qtype="descriptive"),
        _q("ga", section=GA), _q("unproj"), _q("done"), _q("nokey", key=None),
        _q("fewopt"),
    ]
    options = [o for qid in ("in1", "in2", "pend", "desc", "ga", "unproj", "done", "nokey")
               for o in _opts(qid)] + _opts("fewopt", labels="a")
    stimuli = [{"id": "s1", "question_ids": ["in2"], "content_text": "A table", "display_order": 1}]
    rows, skips = mod.build_input(
        questions, options, stimuli, PAPERS, [],
        exam_id=EXAM, section_aliases=ALIASES, subjects={"quantitative-aptitude"},
        projected_ids={"in1", "in2", "pend", "desc", "ga", "done", "nokey", "fewopt"},
        exclude_ids={"done"},
    )
    assert [r["question_id"] for r in rows] == ["in1", "in2"]
    assert skips == {"question_not_verified": 1, "not_mcq": 1, "subject_out_of_scope": 1,
                     "not_projected": 1, "already_explained": 1, "no_answer_key": 1,
                     "too_few_verified_options": 1}
    assert rows[1]["stimulus_text"] == "A table"
    assert rows[0]["options"][0]["label"] == "a"
    assert set(rows[0]) >= {"question_id", "year", "question_number", "question_text", "options",
                            "correct_option_id", "subject_slug", "topic_name"}


def test_input_paper_filter():
    qs = [_q("a"), _q("b", paper="p2")]
    rows, skips = mod.build_input(qs, _opts("a") + _opts("b"), [], PAPERS, [],
                                  exam_id=EXAM, section_aliases=ALIASES,
                                  subjects={"quantitative-aptitude"}, paper_ids={"p2"})
    assert [r["question_id"] for r in rows] == ["b"]
    assert skips == {"paper_out_of_scope": 1}


def test_input_refuses_foreign_exam_paper():
    with pytest.raises(SystemExit):
        mod.build_input([], [], [], PAPERS + [{"id": "px", "exam_id": "other"}], [],
                        exam_id=EXAM, section_aliases=ALIASES, subjects={"quantitative-aptitude"})


# ─── gate ────────────────────────────────────────────────────────────────────
def test_clean_row_passes_in_cms_shape():
    res = mod.run_gate([_input_row()], [_draft()])
    assert not res["quarantined"]
    (row,) = res["passed"]
    assert row["final_answer_option_id"] == "q1-o-c"
    assert row["option_rationales"] == {f"q1-o-{l}": f"r {l}" for l in "abcd"}
    assert row["formula_used"] == ["a x b"]
    assert row["ambiguity_status"] == "none"
    assert "reviewer_status" not in row
    assert set(row) <= mod_allowed()


def mod_allowed():
    # Mirror of _EXPLANATION_FIELDS | {"question_id"} in admin_exam_intel_cms.py.
    return {"question_id", "short_explanation", "explanation_text", "solution_steps",
            "option_rationales", "formula_used", "common_traps", "final_answer_option_id",
            "alternate_answer_option_id", "final_answer_mock_option_id",
            "alternate_answer_mock_option_id", "ambiguity_status", "explanation_source_type",
            "source_url", "source_document_id", "source_hash", "license_status", "metadata"}


@pytest.mark.parametrize("draft, inp, flag", [
    (_draft(final="b"), _input_row(), "final_answer_mismatch"),
    (_draft(final=None), _input_row(), "final_answer_missing"),
    (_draft(verdict="DISPUTED"), _input_row(), "key_disputed"),
    (_draft(qid="zz"), _input_row(), "unknown_question"),
])
def test_hard_flags_quarantine_and_refuse_signature(draft, inp, flag):
    res = mod.run_gate([inp], [draft])
    assert not res["passed"]
    (row,) = res["quarantined"]
    assert flag in row["flags"].split(";")
    assert row["decision"] == ""
    signed = [dict(row, decision="verified", notes="looks fine")]
    res2 = mod.run_gate([inp], [draft], signed=signed)
    assert not res2["released"] and not res2["passed"]
    assert res2["refused_signatures"] == [draft["question_id"]]


def test_key_inconsistent_is_hard():
    inp = _input_row()
    inp["options"][0]["correct"] = True  # two options marked correct
    res = mod.run_gate([inp], [_draft()])
    assert "key_inconsistent" in res["quarantined"][0]["flags"]


def test_foreign_rationale_is_hard():
    d = _draft()
    d["option_rationales"].append({"option_id": "elsewhere", "label": "e", "rationale": "x"})
    res = mod.run_gate([_input_row()], [d])
    assert "rationale_foreign_option" in res["quarantined"][0]["flags"]


def test_soft_flag_releases_on_verified_signature():
    d = _draft(labels="abc")  # option d has no rationale
    res = mod.run_gate([_input_row()], [d])
    (row,) = res["quarantined"]
    assert row["flags"] == "rationale_missing_option"
    res2 = mod.run_gate([_input_row()], [d], signed=[dict(row, decision="verified", notes="d is obvious")])
    (rel,) = res2["released"]
    assert rel["metadata"]["explanation_gate"] == {
        "released_flags": ["rationale_missing_option"], "operator_note": "d is obvious"}
    res3 = mod.run_gate([_input_row()], [d], signed=[dict(row, decision="rejected")])
    assert not res3["released"] and res3["quarantined"][0]["decision"] == "rejected"


def test_keyed_option_needs_no_rationale():
    res = mod.run_gate([_input_row()], [_draft(labels="abd")])  # c is keyed
    assert res["passed"] and not res["quarantined"]


def test_bad_decision_value_aborts():
    row = mod.quarantine_row(_draft(), _input_row(), ["x"], "")
    with pytest.raises(SystemExit):
        mod.run_gate([_input_row()], [_draft()], signed=[dict(row, decision="approve")])


@pytest.mark.parametrize("text, flagged", [
    ("So the answer is (b).", True),
    ("The correct option is d.", True),
    ("Option (a) is correct because ...", True),
    ("Hence, option b", True),
    ("The answer is (c).", False),                      # the keyed option
    ("Option (b) gives 40, the slip of adding.", False),  # a passing mention
    ("The answer is 42.", False),
    ("The answer is D using I and III.", False),        # a person in a seating set
    ("The answer is option d.", True),
])
def test_answer_phrase_check(text, flagged):
    res = mod.run_gate([_input_row()], [_draft(text=text)])
    assert bool(res["quarantined"]) is flagged


def test_duplicate_draft_rows_quarantine():
    res = mod.run_gate([_input_row()], [_draft(), _draft()])
    assert len(res["quarantined"]) == 2 and not res["passed"]


def test_not_drafted_is_reported():
    res = mod.run_gate([_input_row("q1"), _input_row("q2")], [_draft("q1")])
    assert res["not_drafted"] == ["q2"]


# ─── cli ─────────────────────────────────────────────────────────────────────
def test_cli_gate_writes_worksheet_shaped_quarantine(tmp_path):
    inp = tmp_path / "in.json"
    drf = tmp_path / "draft.json"
    inp.write_text(json.dumps([_input_row("q1"), _input_row("q2")]), encoding="utf-8")
    drf.write_text(json.dumps([_draft("q1"), _draft("q2", final="a")]), encoding="utf-8")
    out = tmp_path / "out"

    assert mod.main(["gate", "--input", str(inp), "--draft", str(drf), "--out-dir", str(out)]) == 0
    assert not out.exists()  # dry run

    assert mod.main(["gate", "--input", str(inp), "--draft", str(drf),
                     "--out-dir", str(out), "--apply"]) == 0
    body = json.loads((out / "cms_body.json").read_text(encoding="utf-8"))
    assert body["entity"] == "pyq-question-explanations"
    assert [r["question_id"] for r in body["rows"]] == ["q1"]
    rows = list(csv.DictReader(io.open(out / "quarantine.csv", encoding="utf-8-sig")))
    assert list(rows[0].keys()) == mod.WORKSHEET_FIELDS
    assert rows[0]["row_id"] == "q2" and rows[0]["decision"] == ""
    assert "final_answer_mismatch" in rows[0]["flags"]


def test_worksheet_fields_match_review_tool():
    spec = importlib.util.spec_from_file_location(
        "pyq_question_review", _ROOT / "scripts" / "pyq_question_review.py")
    review = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(review)
    assert mod.WORKSHEET_FIELDS == review.WORKSHEET_FIELDS
    assert mod.DECISIONS == review.DECISIONS
