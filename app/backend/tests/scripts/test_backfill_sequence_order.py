"""scripts/backfill_sequence_order.py — offline only; no network, no database.

Pins: derivation handles N segments and the usual option spellings; every
malformed case is FLAGGED (never guessed); the worksheet keeps the existing
nine-column review shape with a blank decision; apply is a dry run unless
--apply --confirm, re-derives before writing, refuses drift, merges metadata,
and writes a record the runtime (app/study_os/sequence_order.py) accepts.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import pathlib
import re

import pytest

from app.study_os.sequence_order import freeze_sequence, validate_record

_REPO = pathlib.Path(__file__).resolve().parents[4]
_SCRIPT = _REPO / "scripts" / "backfill_sequence_order.py"
_spec = importlib.util.spec_from_file_location("backfill_sequence_order", _SCRIPT)
bso = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bso)

STEM5 = (
    "Given below are five sentences in jumbled order. Select the option that gives their correct logical sequence.\n"
    "A. The monsoon reached Kerala early.\n"
    "B. Farmers began sowing at once.\n"
    "C. Reservoir levels rose steadily.\n"
    "D. Prices of vegetables fell.\n"
    "E. The season ended with a surplus."
)


def _q(qid="q-1", stem=STEM5, status="verified", metadata=None):
    return {"id": qid, "question_text": stem, "question_number": 7, "pyq_paper_id": "paper-1",
            "reviewer_status": status, "metadata": metadata or {"source_ref": "keep-me"}}


def _opts(texts, correct=0):
    return [{"id": f"po-{i}", "option_label": "abcd"[i], "option_text": t, "is_correct": i == correct}
            for i, t in enumerate(texts)]


FIVE = ["ABCDE", "BACDE", "EDCBA", "CABED"]


# ── derivation ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("text,expected", [
    ("BADC", ["B", "A", "D", "C"]),
    ("B-A-D-C", ["B", "A", "D", "C"]),
    ("(B) (A) (D) (C)", ["B", "A", "D", "C"]),
    ("Q, P, S, R", ["Q", "P", "S", "R"]),
    ("2 → 1 → 4 → 3", ["2", "1", "4", "3"]),
    ("None of these", None),
    ("B, A and D", None),
])
def test_option_order_spellings(text, expected):
    assert bso.option_order(text) == expected


def test_derives_five_segments_and_the_winning_order():
    d = bso.derive(_q(), _opts(FIVE, correct=0))
    assert d["flags"] == []
    assert [s["label"] for s in d["segments"]] == ["A", "B", "C", "D", "E"]  # N=5, no truncation
    assert d["segments"][4]["text"] == "The season ended with a surplus."
    assert d["order"] == ["A", "B", "C", "D", "E"]
    assert d["lead"].startswith("Given below are five sentences")
    assert d["option_orders"]["po-3"] == ["C", "A", "B", "E", "D"]


def test_parenthesised_pqrs_markers():
    stem = "Rearrange.\n(P) One.\n(Q) Two.\n(R) Three.\n(S) Four."
    d = bso.derive(_q(stem=stem), _opts(["QPSR", "PQRS", "SRQP", "RPQS"], correct=0))
    assert d["flags"] == []
    assert d["order"] == ["Q", "P", "S", "R"]


@pytest.mark.parametrize("opts,flag", [
    (_opts(FIVE, correct=None), "no_option_marked_correct"),
    ([*_opts(FIVE[:3], correct=0), {"id": "po-9", "option_text": "BACDE", "is_correct": True}], "multiple_options_marked_correct"),
    (_opts(["ABCDE", "BACDE", "None of these", "CABED"]), "option_not_an_order"),
    (_opts(["ABCDE", "BACDE", "ABCD", "CABED"]), "options_disagree_on_labels"),
    (_opts(["ABCDE", "ABCDE", "EDCBA", "CABED"]), "two_options_name_one_order"),
])
def test_malformed_options_are_flagged_not_guessed(opts, flag):
    d = bso.derive(_q(), opts)
    assert any(f.startswith(flag) for f in d["flags"]), d["flags"]


def test_ambiguous_or_missing_markers_are_flagged():
    d = bso.derive(_q(stem=STEM5.replace("E. The season", "The season")), _opts(FIVE))
    assert "label_missing_in_stem:E" in d["flags"]
    d = bso.derive(_q(stem=STEM5 + "\nA. A second A marker."), _opts(FIVE))
    assert "label_marker_ambiguous:A" in d["flags"]
    assert d["segments"] == []


def test_trailing_question_line_is_flagged():
    d = bso.derive(_q(stem=STEM5 + "\nWhich is the correct sequence?"), _opts(FIVE))
    assert "instruction_in_last_segment:E" in d["flags"]


def test_fixed_first_and_last_sentences_are_flagged():
    stem = "S1: Opening.\nP. One.\nQ. Two.\nR. Three.\nS. Four.\nS6: Closing."
    d = bso.derive(_q(stem=stem), _opts(["QPSR", "PQRS", "SRQP", "RPQS"]))
    assert any(f.startswith("fixed_sentence_in_segment") for f in d["flags"])


# ── worksheet ───────────────────────────────────────────────────────────────

def test_worksheet_keeps_the_review_shape_with_a_blank_decision(tmp_path):
    row = bso.worksheet_row("topic-1", _q(), 2024, bso.derive(_q(), _opts(FIVE)))
    path = tmp_path / "ws.csv"
    bso.write_worksheet([row], path)
    with path.open(encoding="utf-8-sig") as fh:
        header = next(csv.reader(fh))
    existing = ["row_type", "row_id", "paper_year", "question_number_or_topic_id", "text_preview",
                "flags", "sample_reason", "decision", "notes"]
    assert header[:9] == existing
    back = bso.read_worksheet(path)[0]
    assert back["decision"] == ""
    assert back["derived_order"] == "A B C D E"
    assert back["winning_option_text"] == "ABCDE"
    assert back["segment_count"] == "5"


# ── apply ───────────────────────────────────────────────────────────────────

class FakeCMS:
    def __init__(self, question, options):
        self.question, self.options, self.patches = question, options, []

    def get(self, path, params=None):
        if path.endswith(f"/pyq-questions/{self.question['id']}"):
            return self.question
        if path.endswith("/pyq-options"):
            return {"items": self.options if (params or {}).get("offset", 0) == 0 else []}
        raise AssertionError(f"unexpected GET {path}")

    def patch(self, path, body):
        self.patches.append((path, body))
        return {"ok": True}


def _signed_worksheet(tmp_path, question, options, decision="verified", **over):
    row = bso.worksheet_row("topic-1", question, 2024, bso.derive(question, options))
    row["decision"] = decision
    row.update(over)
    path = tmp_path / "ws.csv"
    bso.write_worksheet([row], path)
    return path


def test_apply_is_a_dry_run_without_confirm(tmp_path):
    cms = FakeCMS(_q(), _opts(FIVE))
    ws = _signed_worksheet(tmp_path, cms.question, cms.options)
    rep = bso.do_apply(cms, ws, reviewer="rev", reason="Reviewed orders vs papers", write=False)
    assert rep["would_write"] == 1 and rep["written"] == 0
    assert cms.patches == []


def test_apply_confirm_merges_a_record_the_runtime_accepts(tmp_path):
    cms = FakeCMS(_q(), _opts(FIVE, correct=3))
    ws = _signed_worksheet(tmp_path, cms.question, cms.options)
    rep = bso.do_apply(cms, ws, reviewer="rev", reason="Reviewed orders vs papers", write=True,
                       now="2026-09-25T00:00:00+00:00")
    assert rep["written"] == 1 and rep["refused"] == []
    path, body = cms.patches[0]
    assert path.endswith("/pyq-questions/q-1")
    meta = body["payload"]["metadata"]
    assert meta["source_ref"] == "keep-me"  # existing metadata preserved
    rec = meta["correct_order"]
    assert rec["order"] == ["C", "A", "B", "E", "D"] and rec["verified_by"] == "rev"
    assert validate_record(rec, "q-1")
    bank = [{"id": f"mo-{i}", "pyq_option_id": f"po-{i}"} for i in range(4)]
    frozen = freeze_sequence(rec, pyq_question_id="q-1", options=bank, correct_option_id="mo-3")
    assert frozen["correct_order"] == ["C", "A", "B", "E", "D"]


def test_apply_skips_blank_and_non_verified_decisions(tmp_path):
    cms = FakeCMS(_q(), _opts(FIVE))
    for decision, key in (("", "skipped_blank"), ("reject", "skipped_other_decision")):
        ws = _signed_worksheet(tmp_path, cms.question, cms.options, decision=decision)
        rep = bso.do_apply(cms, ws, reviewer="rev", reason="Reviewed orders vs papers", write=True)
        assert rep[key] == 1 and rep["written"] == 0
    assert cms.patches == []


def test_apply_refuses_drift_since_review(tmp_path):
    cms = FakeCMS(_q(), _opts(FIVE, correct=0))
    ws = _signed_worksheet(tmp_path, cms.question, cms.options)
    cms.options = _opts(FIVE, correct=1)  # the key moved after the reviewer signed
    rep = bso.do_apply(cms, ws, reviewer="rev", reason="Reviewed orders vs papers", write=True)
    assert rep["refused"] == [("q-1", "order_changed_since_review")]
    assert cms.patches == []


def test_apply_refuses_a_row_that_now_derives_with_flags(tmp_path):
    cms = FakeCMS(_q(), _opts(FIVE))
    ws = _signed_worksheet(tmp_path, cms.question, cms.options)
    cms.options = _opts(["ABCDE", "BACDE", "None of these", "CABED"])
    rep = bso.do_apply(cms, ws, reviewer="rev", reason="Reviewed orders vs papers", write=True)
    assert rep["refused"][0][1].startswith("flags:")
    assert cms.patches == []


def test_apply_refuses_unverified_questions(tmp_path):
    cms = FakeCMS(_q(status="pending"), _opts(FIVE))
    ws = _signed_worksheet(tmp_path, cms.question, cms.options)
    rep = bso.do_apply(cms, ws, reviewer="rev", reason="Reviewed orders vs papers", write=True)
    assert rep["refused"] == [("q-1", "question_not_verified")]


# ── the script and the drills page agree on which topics are parajumbles ──

def test_script_topics_match_the_drills_mapping():
    js = (_REPO / "app/frontend/src/features/study/english-drills/drillModules.js").read_text()
    pj_block = js[js.index('id: "pj"'):js.index('id: "err"')]
    ids = re.findall(r'id: "([0-9a-f-]{36})"', pj_block)
    assert tuple(ids) == bso.PARAJUMBLE_TOPIC_IDS


def test_main_requires_credentials(monkeypatch, capsys):
    monkeypatch.delenv("CCP_API_BASE", raising=False)
    monkeypatch.delenv("CCP_ADMIN_JWT", raising=False)
    assert bso.main(["export", "--out", "x.csv"]) == 2
    assert "CCP_API_BASE" in capsys.readouterr().err
    json.dumps({})  # keep json import meaningful for future cases
