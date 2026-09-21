"""Question labels, breadcrumbs, and placement from the real tree shape.

`question_number` is block-encoded: each subject's questions start at a
hundreds boundary, so the seventh question of a paper is numbered 108. The UI
showed "Q108", which is an internal key, and "marks not recorded", which is a
sentence about the database rather than about the question.

The tree fixtures mirror the confirmed demo shape: a primary tag points at a
microtopic, the microtopic's parent is the numbered syllabus section, and its
subject row IS the paper (`upsc-cse-mains-opt-psir-p1`).
"""
from __future__ import annotations

from typing import Any

import pytest

from tests.persona_questions._stub import SBStub

from app.study_os import descriptive as d
from app.study_os import syllabus as syl

EXAM = "5466e62f-7382-4a38-ba96-2fe5fbfeaba2"
USER = "user-labels"
PSIR = "Political Science and International Relations"


def _q(qid, number, parent=None, marks=None, paper="paper-p1", **meta):
    m = {"optional_subject": PSIR, "optional_paper_number": 1, **meta}
    if parent is not None:
        m["parent_question_number"] = parent
    if marks is not None:
        m["marks"] = marks
    return {"id": qid, "pyq_paper_id": paper, "question_number": number,
            "question_text": f"Text {qid}", "question_type": "descriptive",
            "reviewer_status": "verified", "metadata": m}


# ── the label rule, as a pure function ───────────────────────────────────


def test_block_encoded_numbers_become_positional_labels():
    """101..108 is one subject block. The aspirant sees Q1..Q4 with sub-parts,
    which is what the printed paper says."""
    rows = [
        _q("a", 101), _q("b", 102, parent=101), _q("c", 103, parent=101),
        _q("d", 104), _q("e", 105, parent=104),
        _q("f", 106),
    ]
    labels = d.paper_question_labels(rows)
    assert labels == {
        "a": "Q1", "b": "Q1(a)", "c": "Q1(b)",
        "d": "Q2", "e": "Q2(a)",
        "f": "Q3",
    }


def test_a_second_block_continues_the_numbering_of_this_paper():
    """A paper holding two subject blocks (201..) still reads 1, 2, 3."""
    rows = [_q("a", 101), _q("b", 201), _q("c", 202, parent=201)]
    assert d.paper_question_labels(rows) == {"a": "Q1", "b": "Q2", "c": "Q2(a)"}


def test_a_question_with_no_number_gets_no_label():
    """Every thematic row has question_number NULL by design. No order exists,
    so none is claimed."""
    rows = [{"id": "t1", "question_number": None, "metadata": {}}]
    assert d.paper_question_labels(rows) == {}


def test_an_empty_paper_yields_no_labels():
    assert d.paper_question_labels([]) == {}


def test_a_sub_part_whose_parent_row_is_absent_is_still_labelled():
    """The stem may not be a row of its own. Rank the missing parent by where
    its number falls, rather than dropping its children."""
    rows = [_q("a", 101), _q("b", 205, parent=204)]
    labels = d.paper_question_labels(rows)
    assert labels["a"] == "Q1"
    assert labels["b"] == "Q2(a)"


def test_sub_part_letters_follow_question_number_order():
    rows = [_q("p", 101), _q("z", 109, parent=101), _q("y", 103, parent=101)]
    labels = d.paper_question_labels(rows)
    assert labels["y"] == "Q1(a)"
    assert labels["z"] == "Q1(b)"


# ── breadcrumbs ──────────────────────────────────────────────────────────


PAPER = {"id": "paper-p1", "year": 2019,
         "metadata": {"paper_kind": "optional", "optional_subject": PSIR,
                      "optional_paper_number": 1}}
THEMATIC = {"id": "thematic", "year": 2019,
            "metadata": {"paper_kind": "optional", "corpus_half": "thematic"}}


def test_paper_half_breadcrumb_reads_like_the_printed_paper():
    crumb = d.breadcrumb_for(
        _q("x", 105, parent=104, marks=15, section_ref="Section A"),
        paper=PAPER, label="Q5(b)", topic="Sovereignty",
    )
    assert crumb["source"] == "2019 · P1 · Q5(b) · 15 marks"
    assert crumb["trail"] == [PSIR, "P1", "Section A", "Sovereignty"]


def test_thematic_breadcrumb_claims_no_paper_order():
    crumb = d.breadcrumb_for(
        _q("t", None, paper="thematic", corpus_half="thematic"),
        paper=THEMATIC, label=None, topic="Sovereignty",
    )
    assert crumb["source"] == "Theme compilation · 2019"
    assert "P1" not in crumb["trail"]
    assert crumb["trail"] == [PSIR, "Sovereignty"]


def test_unknown_levels_are_omitted_not_blanked():
    """A breadcrumb with a hole invites the reader to wonder what is missing."""
    crumb = d.breadcrumb_for(_q("x", 101), paper=PAPER, label="Q1")
    assert crumb["source"] == "2019 · P1 · Q1"
    assert crumb["trail"] == [PSIR, "P1"]


def test_marks_appear_only_when_recorded():
    """"marks not recorded" was a sentence about the database."""
    with_marks = d.breadcrumb_for(_q("x", 101, marks=10), paper=PAPER, label="Q1")
    without = d.breadcrumb_for(_q("y", 102), paper=PAPER, label="Q2")
    assert with_marks["source"].endswith("10 marks")
    assert "marks" not in without["source"]


# ── end to end through list_questions ────────────────────────────────────


def _seed():
    return {
        "pyq_papers": [PAPER | {"exam_id": EXAM, "paper_code": "P1",
                                "trust_status": "pending"}],
        "pyq_questions": [
            _q("a", 101), _q("b", 102, parent=101, marks=15), _q("c", 103, parent=101),
        ],
        "pyq_question_topic_tags": [], "topics": [], "descriptive_attempts": [],
    }


def test_the_payload_carries_a_label_and_a_breadcrumb():
    out = d.list_questions(SBStub(_seed()), USER, exam_id=EXAM, paper_id="paper-p1")
    by_id = {i["id"]: i for i in out["items"]}

    assert by_id["b"]["label"] == "Q1(a)"
    assert by_id["b"]["breadcrumb"]["source"] == "2019 · P1 · Q1(a) · 15 marks"
    assert by_id["c"]["label"] == "Q1(b)"
    # The raw number is still in the payload for sorting; it is not the label.
    assert by_id["b"]["question_number"] == 102


def test_a_question_without_marks_has_no_marks_in_its_breadcrumb():
    out = d.list_questions(SBStub(_seed()), USER, exam_id=EXAM, paper_id="paper-p1")
    crumb = next(i for i in out["items"] if i["id"] == "c")["breadcrumb"]
    assert "marks" not in crumb["source"]


# ── P1.5: placement from the tree, as the demo DB actually carries it ────


def test_a_theme_places_from_its_subject_slug_and_parent_topic():
    """Confirmed shape: the tag points at a microtopic, its parent is the
    numbered section, its subject row IS the paper. No metadata stamp needed."""
    spot = syl.place({
        "name": "Sovereignty",
        "metadata": {},
        "subject_slug": "upsc-cse-mains-opt-psir-p2",
        "parent_topic_name": "2. Theories of the state",
        "parent_official_line": "Theories of the state: Liberal, Neo-liberal…",
    })
    assert spot["placed"] is True
    assert spot["paper_id"] == "opt-psir-p2"
    assert spot["paper_label"] == "P2"
    assert spot["section"] == "2. Theories of the state"
    assert spot["section_line"].startswith("Theories of the state")


@pytest.mark.parametrize("slug,paper", [
    ("upsc-cse-mains-opt-psir-p1", "opt-psir-p1"),
    ("upsc-cse-mains-opt-anthropology-p2", "opt-anthropology-p2"),
    ("upsc-cse-mains-gs1", "GS_1"),
    ("upsc-cse-mains-gs4", "GS_4"),
])
def test_canonical_subject_slugs_give_the_paper(slug, paper):
    assert syl.paper_id_from_subject_slug(slug) == paper


@pytest.mark.parametrize("slug", [
    "upsc-mains-gs1", "upsc-mains-gs4", "upsc-mains-essay", "upsc-gs-paper-1",
    "", None, "upsc-cse-mains-opt-psir-p3",
])
def test_the_empty_gs_shells_are_not_treated_as_papers(slug):
    """`upsc-mains-gs1` and friends carry no tree. Guessing that they mean GS1
    would file real questions under a subject nobody tags."""
    assert syl.paper_id_from_subject_slug(slug) is None


def test_the_tree_route_runs_before_the_name_index():
    """A name the index knows, under a subject that disagrees, follows the
    subject — the row's own position beats a name lookup."""
    spot = syl.place({
        "name": "Indian Culture",
        "metadata": {},
        "subject_slug": "upsc-cse-mains-opt-history-p1",
        "parent_topic_name": "1. Sources",
    })
    assert spot["paper_id"] == "opt-history-p1"
    assert spot["section"] == "1. Sources"
