"""Unit tests for ``scripts/docx_to_pyq_json.py``.

The script lives at the repo root (mirroring scripts/pyq_question_review.py), so
it is loaded by absolute path rather than via the ``scripts`` package.

Coverage targets the two pieces of logic that can silently corrupt a paper:
- Word list numbering is stripped from the text layer, but the options refer to
  it ("1 and 2 only"), so it has to be restored exactly;
- the supplied source documents are retyped/OCR-derived and carry damaged option
  markers, which may be repaired only when unambiguous and must otherwise fail.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import zipfile

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_SCRIPT = _ROOT / "scripts" / "docx_to_pyq_json.py"
_spec = importlib.util.spec_from_file_location("docx_to_pyq_json", _SCRIPT)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _para(text: str, num_id: str | None = None) -> str:
    props = f'<w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="{num_id}"/></w:numPr></w:pPr>' if num_id else ""
    runs = "".join(
        f"<w:r><w:t>{part}</w:t></w:r>" if i == 0 else f"<w:r><w:br/><w:t>{part}</w:t></w:r>"
        for i, part in enumerate(text.split("\n"))
    )
    return f"<w:p>{props}{runs}</w:p>"


def _docx(tmp_path: pathlib.Path, body: str, name: str = "p.docx") -> str:
    path = tmp_path / name
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml", f'<w:document xmlns:w="{W}"><w:body>{body}</w:body></w:document>')
    return str(path)


def _question(tmp_path, body, name="p.docx"):
    return mod._parse_blocks(_docx(tmp_path, body, name))


def test_restores_word_list_numbering(tmp_path):
    """List markers live in numbering.xml, not the text layer — restore them."""
    body = (
        _para("1. Which of the following?")
        + _para("Konkani", num_id="1")
        + _para("Manipuri", num_id="1")
        + _para("Nepali", num_id="1")
        + _para("(a) 1 and 2 only\n(b) 1 and 3 only\n(c) 2 and 3 only\n(d) 1, 2 and 3")
    )
    q = _question(tmp_path, body)[0]
    assert q["stem_parts"][1:] == ["1. Konkani", "2. Manipuri", "3. Nepali"]
    assert [label for label, _ in q["options"]] == ["a", "b", "c", "d"]


def test_numbering_restarts_for_each_question(tmp_path):
    """Each question's list is its own numbering instance and restarts at 1."""
    body = (
        _para("1. First?")
        + _para("Alpha", num_id="1")
        + _para("Beta", num_id="1")
        + _para("(a) X\n(b) Y\n(c) Z\n(d) W")
        + _para("2. Second?")
        + _para("Gamma", num_id="2")
        + _para("(a) X\n(b) Y\n(c) Z\n(d) W")
    )
    first, second = _question(tmp_path, body)
    assert first["stem_parts"][1:] == ["1. Alpha", "2. Beta"]
    assert second["stem_parts"][1:] == ["1. Gamma"]


@pytest.mark.parametrize("marker", ["{b)", "b)", "(B)", "(b)."])
def test_repairs_unambiguous_damaged_option_marker(tmp_path, marker):
    """A damaged marker in the position it belongs to is recoverable."""
    body = (
        _para("1. Stem?")
        + _para("(a) One")
        + _para(f"{marker} Two")
        + _para("(c) Three")
        + _para("(d) Four")
    )
    q = _question(tmp_path, body, name=f"m{abs(hash(marker))}.docx")[0]
    assert [label for label, _ in q["options"]] == ["a", "b", "c", "d"]
    assert dict(q["options"])["b"] == "Two"


def test_does_not_reorder_a_scrambled_marker(tmp_path):
    """A marker reading 'd' where 'b' is due is source corruption, not noise.

    Repairing it by position would assume the printed order is right and the
    label wrong — a guess about answer identity. It must fail validation.
    """
    body = (
        _para("1. Stem?")
        + _para("(a) One")
        + _para("(d). Two")
        + _para("(b) Three")
        + _para("(d) Four")
    )
    questions = _question(tmp_path, body)
    assert [label for label, _ in questions[0]["options"]] == ["a", "d", "b", "d"]
    assert any("expected ['a','b','c','d']" in e for e in mod.validate(questions, 1))


def test_flags_a_stem_that_lost_its_list_numbering(tmp_path):
    """Unnumbered statements + numeric options = an unanswerable question."""
    body = (
        _para("1. Consider the following statements:")
        + _para("Jhelum River passes through Wular Lake.")
        + _para("Krishna River directly feeds Kolleru Lake.")
        + _para("(a) 1 only\n(b) 2 only\n(c) Both 1 and 2\n(d) Neither 1 nor 2")
    )
    errors = mod.validate(_question(tmp_path, body), 1)
    assert any("lost its list numbering" in e for e in errors)


def test_statement_form_stem_is_not_flagged(tmp_path):
    """UPSC's 'Statement-I / Statement-II' form carries its own labelling."""
    body = (
        _para("1. Consider the following statements:")
        + _para("Statement-I : Rainfall weathers rocks.")
        + _para("Statement-II : Rain water contains carbon dioxide.")
        + _para("(a) Only one is correct\n(b) Both are correct\n(c) Neither\n(d) Cannot say")
    )
    assert mod.validate(_question(tmp_path, body), 1) == []


def test_table_backed_stem_is_linearised_and_not_flagged(tmp_path):
    """A pairs table becomes pipe-joined rows; 'Only two' refers to those rows."""
    tbl = (
        "<w:tbl>"
        "<w:tr><w:tc><w:p><w:r><w:t>Party</w:t></w:r></w:p></w:tc>"
        "<w:tc><w:p><w:r><w:t>Leader</w:t></w:r></w:p></w:tc></w:tr>"
        "<w:tr><w:tc><w:p><w:r><w:t>Swatantra</w:t></w:r></w:p></w:tc>"
        "<w:tc><w:p><w:r><w:t>Rajagopalachari</w:t></w:r></w:p></w:tc></w:tr>"
        "</w:tbl>"
    )
    body = (
        _para("1. Consider the following pairs:")
        + tbl
        + _para("How many are correctly matched?")
        + _para("(a) Only one\n(b) Only two\n(c) Only three\n(d) All four")
    )
    questions = _question(tmp_path, body)
    assert "Swatantra | Rajagopalachari" in questions[0]["stem_parts"]
    assert mod.validate(questions, 1) == []


def test_dropped_question_carries_no_correct_option(tmp_path):
    """A dropped question is recorded, flagged, and left without a key."""
    body = _para("1. Stem?") + _para("(a) One\n(b) Two\n(c) Three\n(d) Four")
    envelope = mod.build_envelope(
        _question(tmp_path, body),
        ref_prefix="GS1",
        answer_key={},
        dropped={1},
        difficulty=None,
    )
    row = envelope["questions"][0]
    assert row["dropped_by_upsc"] is True
    assert row["correct_option_label"] is None
    assert row["source_question_ref"] == "GS1-Q1"
    assert row["question_number"] == row["display_order"] == 1


def test_question_start_requires_the_expected_number(tmp_path):
    """'1. Konkani' inside a list must never open a new question."""
    body = (
        _para("1. Which languages?")
        + _para("1. Konkani")
        + _para("(a) One\n(b) Two\n(c) Three\n(d) Four")
    )
    questions = _question(tmp_path, body)
    assert len(questions) == 1
    assert "1. Konkani" in questions[0]["stem_parts"]


# ── marker detection, line flattening, and damaged-source recovery ────────────


def test_detects_q_dot_n_marker_over_bare_numbers(tmp_path):
    """'Q.1)' papers also carry bare '1.' statement lines; the opener must win."""
    body = (
        _para("Q.1) Consider the following:")
        + _para("1. Alpha")
        + _para("2. Beta")
        + _para("Which of the above?")
        + _para("(a) 1 only\n(b) 2 only\n(c) Both\n(d) Neither")
        + _para("Q.2) Second?")
        + _para("(a) W\n(b) X\n(c) Y\n(d) Z")
    )
    lines = mod._read_lines(_docx(tmp_path, body))
    name, pattern = mod.detect_marker(lines)
    assert name == "Q.N)"
    questions = mod._parse_lines(lines, pattern)
    assert [q["number"] for q in questions] == [1, 2]
    assert "1. Alpha" in questions[0]["stem_parts"]


def test_detects_question_n_marker_with_mixed_separators(tmp_path):
    """One year prints 'Question 1.', 'Question 2:' and 'Question: 3.' alike."""
    body = (
        _para("Question 1. First?")
        + _para("(a) W\n(b) X\n(c) Y\n(d) Z")
        + _para("Question 2: Second?")
        + _para("(a) W\n(b) X\n(c) Y\n(d) Z")
        + _para("Question: 3. Third?")
        + _para("(a) W\n(b) X\n(c) Y\n(d) Z")
    )
    lines = mod._read_lines(_docx(tmp_path, body))
    name, pattern = mod.detect_marker(lines)
    assert name == "Question N."
    assert [q["number"] for q in mod._parse_lines(lines, pattern)] == [1, 2, 3]


def test_whole_question_in_one_paragraph_is_split_into_lines(tmp_path):
    """Some years pack stem, statements and all four options into one paragraph."""
    body = _para(
        "Q.1) Consider the following:\n1. Alpha\n2. Beta\n"
        "Which of the above?\n(a) 1 only\n(b) 2 only\n(c) Both\n(d) Neither"
    ) + _para("Q.2) Second?\n(a) W\n(b) X\n(c) Y\n(d) Z")
    q = _question(tmp_path, body)[0]
    assert q["stem_parts"][1:3] == ["1. Alpha", "2. Beta"]
    assert [label for label, _ in q["options"]] == ["a", "b", "c", "d"]


def test_lower_letter_list_becomes_the_options(tmp_path):
    """Word can hold 'a)' in numbering.xml, leaving only option text in the run."""
    body = (
        _para("1. Stem?")
        + _para("First", num_id="9")
        + _para("Second", num_id="9")
        + _para("Third", num_id="9")
        + _para("Fourth", num_id="9")
    )
    path = _docx(tmp_path, body, name="lower.docx")
    with zipfile.ZipFile(path, "a") as z:
        z.writestr("word/numbering.xml", (
            f'<w:numbering xmlns:w="{W}">'
            f'<w:abstractNum w:abstractNumId="3"><w:lvl w:ilvl="0">'
            f'<w:numFmt w:val="lowerLetter"/><w:lvlText w:val="%1)"/></w:lvl></w:abstractNum>'
            f'<w:num w:numId="9"><w:abstractNumId w:val="3"/></w:num></w:numbering>'
        ))
    q = mod._parse_blocks(path)[0]
    assert q["options"] == [("a", "First"), ("b", "Second"), ("c", "Third"), ("d", "Fourth")]


def test_splits_two_options_glued_onto_one_line(tmp_path):
    """'(c) 3 only d)1 and 3' is two options, split on the label that is due."""
    body = (
        _para("1. Stem?")
        + _para("(a) 1 only")
        + _para("(b) 2 only")
        + _para("(c) 3 only d)1 and 3")
    )
    q = _question(tmp_path, body)[0]
    assert q["options"] == [("a", "1 only"), ("b", "2 only"), ("c", "3 only"), ("d", "1 and 3")]


def test_does_not_manufacture_an_option_from_a_stray_bracket(tmp_path):
    """A bracketed letter inside option text is not the next option."""
    body = (
        _para("1. Stem?")
        + _para("(a) One")
        + _para("(b) Two")
        + _para("(c) Item (d) of the schedule")
        + _para("(d) Four")
    )
    q = _question(tmp_path, body)[0]
    assert dict(q["options"])["c"] == "Item (d) of the schedule"
    assert dict(q["options"])["d"] == "Four"


def test_counting_options_do_not_require_stem_numbering(tmp_path):
    """'Only two' tallies the statements as printed; their numbering is cosmetic."""
    body = (
        _para("1. Consider the following statements:")
        + _para("Jhelum River passes through Wular Lake.")
        + _para("Krishna River directly feeds Kolleru Lake.")
        + _para("How many of the statements given above are correct?")
        + _para("(a) Only one\n(b) Only two\n(c) None\n(d) Cannot say")
    )
    assert mod.validate(_question(tmp_path, body), 1) == []


def test_indexing_options_still_require_stem_numbering(tmp_path):
    """'1 only' names a specific statement, so the numbering is load-bearing."""
    body = (
        _para("1. Consider the following statements:")
        + _para("Jhelum River passes through Wular Lake.")
        + _para("Krishna River directly feeds Kolleru Lake.")
        + _para("Which of the statements given above is/are correct?")
        + _para("(a) 1 only\n(b) 2 only\n(c) Both 1 and 2\n(d) Neither 1 nor 2")
    )
    questions = _question(tmp_path, body)
    assert any("lost its list numbering" in e for e in mod.validate(questions, 1))
    # opt-in restoration numbers the run by printed order and clears the error
    assert mod._number_unmarked(questions[0]) is True
    assert questions[0]["stem_parts"][1:3] == [
        "1. Jhelum River passes through Wular Lake.",
        "2. Krishna River directly feeds Kolleru Lake.",
    ]
    assert mod.validate(questions, 1) == []


def test_restoration_declines_when_the_shape_is_not_a_statement_run(tmp_path):
    """No lead-in, no closing interrogative: nothing safe to number."""
    body = (
        _para("1. Which one is correct?")
        + _para("(a) 1 only\n(b) 2 only\n(c) Both 1 and 2\n(d) Neither 1 nor 2")
    )
    assert mod._number_unmarked(_question(tmp_path, body)[0]) is False


def test_complete_but_shuffled_options_are_reordered(tmp_path):
    """a, c, b, d with every label present exactly once — order by label."""
    q = {"options": [("a", "One"), ("c", "Three"), ("b", "Two"), ("d", "Four")]}
    assert mod._sort_complete_options(q) is True
    assert q["options"] == [("a", "One"), ("b", "Two"), ("c", "Three"), ("d", "Four")]


def test_incomplete_option_set_is_left_to_fail(tmp_path):
    """A duplicated or missing label is source damage, not a sort problem."""
    q = {"options": [("a", "One"), ("d", "Two"), ("b", "Three"), ("d", "Four")]}
    assert mod._sort_complete_options(q) is False
    assert q["options"][1] == ("d", "Two")


# ── operator corrections for source-document damage ──────────────────────────


def test_relabel_correction_reorders_by_supplied_labels(tmp_path):
    """Printed a/d/b/c: assign the true labels positionally, then sort."""
    body = (
        _para("1. Stem?")
        + _para("(a) Farming")
        + _para("(d) Wind")
        + _para("(b) Gardens")
        + _para("(d) Forests")
    )
    questions = _question(tmp_path, body)
    applied = mod.apply_corrections(questions, {"1": {"relabel": ["a", "d", "b", "c"]}})
    assert questions[0]["options"] == [
        ("a", "Farming"), ("b", "Gardens"), ("c", "Forests"), ("d", "Wind"),
    ]
    assert applied == ["Q1: relabelled options a/d/b/c"]
    assert mod.validate(questions, 1) == []


def test_relabel_correction_rejects_a_length_mismatch(tmp_path):
    """A correction written against a different parse must not apply silently."""
    body = _para("1. Stem?") + _para("(a) One\n(b) Two\n(c) Three\n(d) Four")
    with pytest.raises(ValueError, match="lists 3 labels"):
        mod.apply_corrections(_question(tmp_path, body), {"1": {"relabel": ["a", "b", "c"]}})


def test_options_from_stem_promotes_a_numbered_run(tmp_path):
    """A paper that formatted its options as a decimal list parses them as statements."""
    body = (
        _para("1. Stem promoting the adoption of")
        + _para("First", num_id="1")
        + _para("Second", num_id="1")
        + _para("Third", num_id="1")
        + _para("Fourth", num_id="1")
    )
    questions = _question(tmp_path, body)
    assert questions[0]["options"] == []
    mod.apply_corrections(questions, {"1": {"options_from_stem": 4}})
    assert questions[0]["options"] == [
        ("a", "First"), ("b", "Second"), ("c", "Third"), ("d", "Fourth"),
    ]
    assert questions[0]["stem_parts"] == ["Stem promoting the adoption of"]


def test_options_from_stem_refuses_when_options_already_parsed(tmp_path):
    """Guards against a correction that would duplicate an option set."""
    body = _para("1. Stem?") + _para("(a) One\n(b) Two\n(c) Three\n(d) Four")
    with pytest.raises(ValueError, match="already"):
        mod.apply_corrections(_question(tmp_path, body), {"1": {"options_from_stem": 4}})


def test_correction_for_a_missing_question_is_an_error(tmp_path):
    """A correction file written for another set must not pass unnoticed."""
    body = _para("1. Stem?") + _para("(a) One\n(b) Two\n(c) Three\n(d) Four")
    with pytest.raises(ValueError, match="no such question"):
        mod.apply_corrections(_question(tmp_path, body), {"7": {"relabel": ["a"]}})


def test_provenance_keys_are_ignored(tmp_path):
    """Underscore-prefixed keys carry provenance, not operations."""
    body = _para("1. Stem?") + _para("(a) One\n(b) Two\n(c) Three\n(d) Four")
    assert mod.apply_corrections(_question(tmp_path, body), {"_provenance": "..."}) == []


def test_add_options_supplies_an_option_the_source_dropped(tmp_path):
    """The only operation that introduces text, so it is the narrowest."""
    body = _para("1. Stem?") + _para("(a) One\n(b) Two\n(c) Three")
    questions = _question(tmp_path, body)
    applied = mod.apply_corrections(questions, {"1": {"add_options": {"d": "Four"}}})
    assert questions[0]["options"][-1] == ("d", "Four")
    assert applied == ["Q1: supplied missing option(s) d"]
    assert mod.validate(questions, 1) == []


def test_add_options_refuses_to_overwrite_a_parsed_option(tmp_path):
    """A correction must never silently replace text that was actually printed."""
    body = _para("1. Stem?") + _para("(a) One\n(b) Two\n(c) Three\n(d) Four")
    with pytest.raises(ValueError, match="overwrite"):
        mod.apply_corrections(_question(tmp_path, body), {"1": {"add_options": {"d": "Other"}}})


def test_add_options_refuses_to_leave_an_incomplete_set(tmp_path):
    """Filling one hole of two would look repaired while still being damaged."""
    body = _para("1. Stem?") + _para("(a) One\n(b) Two")
    with pytest.raises(ValueError, match=r"not \['a','b','c','d'\]"):
        mod.apply_corrections(_question(tmp_path, body), {"1": {"add_options": {"d": "Four"}}})


# ── five-option papers (a-e) ─────────────────────────────────────────────────
#
# The converter was the sole layer capping a question at four options, and it
# capped SILENTLY: "e" was absent from OPTION_LABELS, so a printed "(e)" matched
# no marker, fell through to the continuation-append, and was glued onto option
# (d)'s text. Nothing downstream could see that a fifth option had been eaten.
# These tests pin both halves of the fix: five is parsed, and anything that is
# neither a complete a-d nor a complete a-e run still fails by question number.


def test_four_option_paper_is_unchanged(tmp_path):
    """The additive half of the change: a-d papers parse and validate as before."""
    body = (
        _para("1. Which one of the following is correct?")
        + _para("(a) One\n(b) Two\n(c) Three\n(d) Four")
    )
    questions = _question(tmp_path, body)
    assert [label for label, _ in questions[0]["options"]] == ["a", "b", "c", "d"]
    assert mod.validate(questions, 1) == []


def test_five_option_paper_parses_all_five(tmp_path):
    body = (
        _para("1. Which one of the following is correct?")
        + _para("(a) One\n(b) Two\n(c) Three\n(d) Four\n(e) Five")
    )
    questions = _question(tmp_path, body)
    assert questions[0]["options"] == [
        ("a", "One"), ("b", "Two"), ("c", "Three"), ("d", "Four"), ("e", "Five"),
    ]
    assert mod.validate(questions, 1) == []


def test_fifth_option_is_never_absorbed_into_option_d(tmp_path):
    """The exact silent-corruption shape this change exists to kill."""
    body = (
        _para("1. Which one of the following is correct?")
        + _para("(a) One\n(b) Two\n(c) Three\n(d) Four\n(e) Five")
    )
    options = dict(_question(tmp_path, body)[0]["options"])
    assert options["d"] == "Four"
    assert "Five" not in options["d"]


def test_mixed_paper_carries_four_and_five_side_by_side(tmp_path):
    """Option count is a per-question property, not a per-paper one."""
    body = (
        _para("1. First?")
        + _para("(a) One\n(b) Two\n(c) Three\n(d) Four")
        + _para("2. Second?")
        + _para("(a) One\n(b) Two\n(c) Three\n(d) Four\n(e) Five")
    )
    questions = _question(tmp_path, body)
    assert [len(q["options"]) for q in questions] == [4, 5]
    assert mod.validate(questions, 2) == []


def test_partial_label_set_fails_loudly_with_the_question_number(tmp_path):
    """a/b/c/e is not a short paper, it is a damaged one — never accept it."""
    body = (
        _para("1. Stem?")
        + _para("(a) One\n(b) Two\n(c) Three\n(e) Five")
    )
    questions = _question(tmp_path, body)
    assert [label for label, _ in questions[0]["options"]] == ["a", "b", "c", "e"]
    errors = mod.validate(questions, 1)
    assert any(
        e.startswith("Q1: options are ['a', 'b', 'c', 'e']")
        and "['a','b','c','d'] or ['a','b','c','d','e']" in e
        for e in errors
    )


def test_five_options_from_a_lower_letter_auto_list(tmp_path):
    """Word holds the marker in numbering.xml, so the text layer carries no "(e)"."""
    body = (
        _para("1. Which one of the following is correct?")
        + _para("One", num_id="1")
        + _para("Two", num_id="1")
        + _para("Three", num_id="1")
        + _para("Four", num_id="1")
        + _para("Five", num_id="1")
    )
    tmp = tmp_path / "n"
    tmp.mkdir()
    path = _docx(tmp, body)
    with zipfile.ZipFile(path, "a") as z:
        z.writestr(
            "word/numbering.xml",
            f'<w:numbering xmlns:w="{W}"><w:num w:numId="1"><w:abstractNumId w:val="1"/></w:num>'
            f'<w:abstractNum w:abstractNumId="1"><w:lvl w:ilvl="0">'
            f'<w:numFmt w:val="lowerLetter"/></w:lvl></w:abstractNum></w:numbering>',
        )
    questions = mod._parse_blocks(path)
    assert questions[0]["options"] == [
        ("a", "One"), ("b", "Two"), ("c", "Three"), ("d", "Four"), ("e", "Five"),
    ]
    assert mod.validate(questions, 1) == []


@pytest.mark.parametrize("marker", ["{e)", "e)", "(E)", "(e)."])
def test_repairs_a_damaged_fifth_option_marker(tmp_path, marker):
    """OPT_LOOSE recovers a damaged "(e)" only where e is the label actually due."""
    body = (
        _para("1. Stem?")
        + _para("(a) One")
        + _para("(b) Two")
        + _para("(c) Three")
        + _para("(d) Four")
        + _para(f"{marker} Five")
    )
    assert _question(tmp_path, body)[0]["options"][-1] == ("e", "Five")


def test_shuffled_five_option_set_is_reordered(tmp_path):
    q = {"options": [("a", "One"), ("e", "Five"), ("c", "Three"), ("b", "Two"), ("d", "Four")]}
    assert mod._sort_complete_options(q) is True
    assert [label for label, _ in q["options"]] == ["a", "b", "c", "d", "e"]


def test_answer_key_accepts_e_and_still_rejects_beyond_it(tmp_path):
    key_path = tmp_path / "key.csv"
    key_path.write_text("question_number,correct_option_label\n1,E\n2,e\n", encoding="utf-8")
    assert mod._load_answer_key(str(key_path)) == {1: "e", 2: "e"}

    bad = tmp_path / "bad.csv"
    bad.write_text("question_number,correct_option_label\n1,f\n", encoding="utf-8")
    with pytest.raises(ValueError, match="is not one of a/b/c/d/e"):
        mod._load_answer_key(str(bad))


def test_envelope_carries_all_five_options(tmp_path):
    body = (
        _para("1. Which one of the following is correct?")
        + _para("(a) One\n(b) Two\n(c) Three\n(d) Four\n(e) Five")
    )
    envelope = mod.build_envelope(
        _question(tmp_path, body),
        ref_prefix="GS1",
        answer_key={1: "e"},
        dropped=set(),
        difficulty=None,
    )
    options = envelope["questions"][0]["options"]
    assert [o["label"] for o in options] == ["a", "b", "c", "d", "e"]
    assert [o["source_label"] for o in options][-1] == "(e)"
    assert [o["display_order"] for o in options] == [1, 2, 3, 4, 5]
    assert envelope["questions"][0]["correct_option_label"] == "e"


# ── dot-style option markers (SEBI / coaching format) ────────────────────────
#
# These papers print "A. Nariman Point, Mumbai" — uppercase letter, period, no
# bracket at all. Both bracket patterns require a closing bracket, so before this
# every question on such a file parsed with zero options and validate() rejected
# the whole paper with "options are none".
#
# The style is chosen per document (detect_option_style), exactly as the
# question-opener style already is, and the two families never mix. That is what
# keeps the UPSC corpus byte-identical: a bracket paper never scores as "dot", so
# its stems are never exposed to the bracket-less pattern.


def _dot_question(n, stem, labels="ABCDE", opts=("One", "Two", "Three", "Four", "Five")):
    body = _para(f"{n}. {stem}")
    for label, text in zip(labels, opts):
        body += _para(f"{label}. {text}")
    return body


def test_detects_dot_style_and_parses_five_options(tmp_path):
    body = _dot_question(1, "Where is the head office?")
    questions = _question(tmp_path, body)
    assert mod.detect_option_style(mod._read_lines(_docx(tmp_path, body, "d.docx"))) == "dot"
    assert questions[0]["options"] == [
        ("a", "One"), ("b", "Two"), ("c", "Three"), ("d", "Four"), ("e", "Five"),
    ]
    assert mod.validate(questions, 1) == []


def test_dot_style_four_option_paper(tmp_path):
    body = _dot_question(1, "Which one is correct?", labels="ABCD",
                         opts=("One", "Two", "Three", "Four"))
    questions = _question(tmp_path, body)
    assert [label for label, _ in questions[0]["options"]] == ["a", "b", "c", "d"]
    assert mod.validate(questions, 1) == []


def test_dot_style_lowercase_markers_and_paren_delimiter(tmp_path):
    """"a." and "a)" are the same family; both normalise to the house lowercase."""
    body = (
        _para("1. Stem?")
        + _para("a. One") + _para("b) Two") + _para("C. Three") + _para("D) Four")
    )
    questions = _question(tmp_path, body)
    assert questions[0]["options"] == [
        ("a", "One"), ("b", "Two"), ("c", "Three"), ("d", "Four"),
    ]
    assert mod.validate(questions, 1) == []


def test_options_label_line_is_dropped(tmp_path):
    """A bare "Options:" is a label — it must reach neither stem nor option list."""
    for label_line in ("Options:", "Options :", "OPTIONS:"):
        body = (
            _para("1. Where is the head office?")
            + _para(label_line)
            + _para("A. One") + _para("B. Two") + _para("C. Three")
            + _para("D. Four") + _para("E. Five")
        )
        questions = _question(tmp_path, body, name=f"{label_line[:7]}.docx")
        assert questions[0]["stem_parts"] == ["Where is the head office?"]
        assert [label for label, _ in questions[0]["options"]] == ["a", "b", "c", "d", "e"]
        assert mod.validate(questions, 1) == []


def test_stem_initials_do_not_become_options(tmp_path):
    """"B. Ambedkar" sits where "a" is due, so the due-gate refuses it."""
    body = (
        _para("1. Who drafted the Constitution of India?")
        + _para("B. Ambedkar chaired the drafting committee.")
        + _para("A. One") + _para("B. Two") + _para("C. Three")
        + _para("D. Four") + _para("E. Five")
    )
    questions = _question(tmp_path, body)
    assert questions[0]["stem_parts"] == [
        "Who drafted the Constitution of India?",
        "B. Ambedkar chaired the drafting committee.",
    ]
    assert questions[0]["options"] == [
        ("a", "One"), ("b", "Two"), ("c", "Three"), ("d", "Four"), ("e", "Five"),
    ]
    assert mod.validate(questions, 1) == []


def test_stem_initials_run_at_the_due_letter_is_refused(tmp_path):
    """"A. K. Sen" IS at the due letter — the second initial is what gives it away."""
    body = (
        _para("1. Who won the 1998 economics prize?")
        + _para("A. K. Sen wrote on welfare economics.")
        + _para("A. One") + _para("B. Two") + _para("C. Three")
        + _para("D. Four") + _para("E. Five")
    )
    questions = _question(tmp_path, body)
    assert questions[0]["stem_parts"] == [
        "Who won the 1998 economics prize?",
        "A. K. Sen wrote on welfare economics.",
    ]
    assert [label for label, _ in questions[0]["options"]] == ["a", "b", "c", "d", "e"]
    assert mod.validate(questions, 1) == []


def test_bracket_paper_never_selects_dot_style(tmp_path):
    """Detection is what makes this additive — a UPSC file must score as bracket."""
    body = (
        _para("1. Which one of the following is correct?")
        + _para("(a) One\n(b) Two\n(c) Three\n(d) Four")
        + _para("2. And this one?")
        + _para("(a) One\n(b) Two\n(c) Three\n(d) Four")
    )
    assert mod.detect_option_style(mod._read_lines(_docx(tmp_path, body))) == "bracket"


def test_bracket_style_envelope_is_byte_identical(tmp_path):
    """The importer dedupes on normalized_question_hash, so any drift on the UPSC
    corpus re-imports every question as new. This pins the whole emitted envelope,
    not just the option labels: stem text, option text, order, and source_label."""
    body = (
        _para("1. Consider the following statements:")
        + _para("Konkani", num_id="1")
        + _para("Manipuri", num_id="1")
        + _para("(a) 1 only\n(b) 2 only\n(c) Both 1 and 2\n(d) Neither 1 nor 2")
        + _para("2. Which one of the following is correct?")
        + _para("(a) Alpha")
        + _para("{b) Beta")
        + _para("(C) Gamma")
        + _para("(d). Delta")
    )
    questions = _question(tmp_path, body)
    envelope = mod.build_envelope(
        questions, ref_prefix="GS1", answer_key={1: "a", 2: "c"},
        dropped=set(), difficulty=None,
    )
    assert mod.validate(questions, 2) == []
    assert envelope == {
        "format_version": 2,
        "questions": [
            {
                "source_question_ref": "GS1-Q1",
                "question_number": 1,
                "display_order": 1,
                "question_text": "Consider the following statements:\n1. Konkani\n2. Manipuri",
                "question_type": "mcq",
                "options": [
                    {"label": "a", "source_label": "(a)", "text": "1 only", "display_order": 1},
                    {"label": "b", "source_label": "(b)", "text": "2 only", "display_order": 2},
                    {"label": "c", "source_label": "(c)", "text": "Both 1 and 2", "display_order": 3},
                    {"label": "d", "source_label": "(d)", "text": "Neither 1 nor 2", "display_order": 4},
                ],
                "correct_option_label": "a",
            },
            {
                "source_question_ref": "GS1-Q2",
                "question_number": 2,
                "display_order": 2,
                "question_text": "Which one of the following is correct?",
                "question_type": "mcq",
                "options": [
                    {"label": "a", "source_label": "(a)", "text": "Alpha", "display_order": 1},
                    {"label": "b", "source_label": "(b)", "text": "Beta", "display_order": 2},
                    {"label": "c", "source_label": "(c)", "text": "Gamma", "display_order": 3},
                    {"label": "d", "source_label": "(d)", "text": "Delta", "display_order": 4},
                ],
                "correct_option_label": "c",
            },
        ],
    }


def test_dot_style_does_not_weaken_complete_set_validation(tmp_path):
    """The #1037 gate still bites on a dot paper: a/b/c/e is damage, not a set."""
    body = (
        _para("1. Stem?")
        + _para("A. One") + _para("B. Two") + _para("C. Three") + _para("E. Five")
    )
    questions = _question(tmp_path, body)
    errors = mod.validate(questions, 1)
    assert any(e.startswith("Q1: options are ['a', 'b', 'c']") for e in errors)


@pytest.mark.parametrize("name,body_parts", [
    ("clean4",   ["(a) One\n(b) Two\n(c) Three\n(d) Four"]),
    ("clean5",   ["(a) One\n(b) Two\n(c) Three\n(d) Four\n(e) Five"]),
    ("damaged",  ["(a) One", "{b) Two", "(C) Three", "(d). Four"]),
    ("glued",    ["(a) 1 only", "(b) 2 only", "(c) 3 only d)1 and 3", "(d) placeholder"]),
    ("shuffled", ["(a) One", "(c) Three", "(b) Two", "(d) Four"]),
])
def test_bracket_shapes_still_detect_as_bracket(tmp_path, name, body_parts):
    """Every damaged/glued/shuffled shape the UPSC corpus actually contains must
    keep scoring as bracket — dot must never win a bracket document."""
    body = _para("1. Stem?") + "".join(_para(p) for p in body_parts)
    lines = mod._read_lines(_docx(tmp_path, body, f"{name}.docx"))
    assert mod.detect_option_style(lines) == "bracket"


# ── statement-index detection (false positive on fill-in-the-blanks) ─────────
#
# The check that a stem carries numbering when its options point at statements
# used to SEARCH each option for a digit pair. A fill-in-the-blanks option like
# "2/3,1" contains the substring "3,1", so SEBI-GA-2022-P1-CA Q1 was rejected
# for numbering it never needed. The predicate now matches the WHOLE option
# against index SHAPES, and needs two family members before it fires.


def _idx(opts):
    return mod._names_statement_indices([("x", o) for o in opts])


def test_fill_in_the_blanks_fractions_are_not_statement_indices(tmp_path):
    """SEBI-GA-2022-P1-CA Q1: the reported false positive, end to end."""
    body = (
        _para("1. The quorum for a meeting shall be _______ of total strength or "
              "___ directors, whichever is higher.")
        + _para("A. 2/3,1") + _para("B. 1/3,2") + _para("C. 1/2,2")
        + _para("D. 3/4, 1") + _para("E. None of the above")
    )
    questions = _question(tmp_path, body)
    assert [label for label, _ in questions[0]["options"]] == ["a", "b", "c", "d", "e"]
    assert mod.validate(questions, 1) == []


def test_genuine_statement_index_with_unnumbered_stem_still_fails(tmp_path):
    """The check exists because these import as unanswerable questions. It must bite."""
    body = (
        _para("1. Consider the following statements:")
        + _para("Jhelum River passes through Wular Lake.")
        + _para("Krishna River directly feeds Kolleru Lake.")
        + _para("A. 1 only") + _para("B. 2 only")
        + _para("C. Both 1 and 2") + _para("D. Neither 1 nor 2")
    )
    errors = mod.validate(_question(tmp_path, body), 1)
    assert any("lost its list numbering" in e for e in errors)


def test_genuine_statement_index_with_numbering_passes(tmp_path):
    """Same options, numbering intact — nothing to complain about.

    The statements carry Word list numbering (``num_id``) rather than literal
    "1."/"2." text: a printed "2. ..." line would be read as question 2 by the
    ``N.`` opener, which is exactly why the converter restores list numbering
    from numbering.xml instead of trusting the text layer.
    """
    body = (
        _para("1. Consider the following statements:")
        + _para("Jhelum River passes through Wular Lake.", num_id="1")
        + _para("Krishna River directly feeds Kolleru Lake.", num_id="1")
        + _para("Which of the statements given above is/are correct?")
        + _para("A. 1 only") + _para("B. 2 only")
        + _para("C. Both 1 and 2") + _para("D. Neither 1 nor 2")
    )
    questions = _question(tmp_path, body)
    assert questions[0]["stem_parts"][1:3] == [
        "1. Jhelum River passes through Wular Lake.",
        "2. Krishna River directly feeds Kolleru Lake.",
    ]
    assert mod.validate(questions, 1) == []


@pytest.mark.parametrize("name,options", [
    ("fractions",       ["2/3,1", "1/3,2", "1/2,2", "3/4, 1", "None of the above"]),
    ("bare numbers",    ["1", "2", "3", "4"]),
    ("years",           ["1991", "1998", "2005 and 2006", "None of the above"]),
    ("currency",        ["Rs. 1,00,000", "Rs. 2,50,000", "Rs. 5,00,000", "Rs. 10,00,000"]),
    ("decimals",        ["1.5", "2.75", "3.25 and 4.5", "None of the above"]),
    ("ratios",          ["1:2", "2:3", "3:4", "None of the above"]),
    ("two-digit values", ["12 and 15", "18 and 21", "24 and 27", "None of the above"]),
    ("word counts",     ["Only one", "Only two", "Only three", "All four"]),
    ("sibling alone",   ["Mumbai", "Delhi", "Chennai", "None of the above"]),
])
def test_numeric_option_text_does_not_demand_numbering(name, options):
    """Digits in an option are not an index reference — the shape is."""
    assert _idx(options) is False


@pytest.mark.parametrize("name,options", [
    ("only forms",   ["1 only", "2 only", "Both 1 and 2", "Neither 1 nor 2"]),
    ("list forms",   ["1 and 2 only", "1, 2 and 3", "2 and 3 only", "1 and 3"]),
    ("keyword-led",  ["Only 1", "Only 1 and 2", "Both 1 and 3", "None of the above"]),
    ("one + sibling", ["1 and 2 only", "None of the above", "Cannot say", "Data insufficient"]),
    ("trailing dot", ["1 only.", "2 only.", "Both 1 and 2.", "None of the above."]),
])
def test_real_index_reference_shapes_still_detected(name, options):
    assert _idx(options) is True


def test_restoration_flag_ignores_a_fill_in_the_blanks_question(tmp_path):
    """--number-unmarked-statements shares the predicate, so it does not fire either."""
    body = (
        _para("1. Consider the following blanks: the quorum shall be _______ of "
              "total strength or ___ directors.")
        + _para("Some clarifying line.")
        + _para("Another clarifying line.")
        + _para("Which of the above is correct?")
        + _para("A. 2/3,1") + _para("B. 1/3,2") + _para("C. 1/2,2")
        + _para("D. 3/4, 1") + _para("E. None of the above")
    )
    q = _question(tmp_path, body)[0]
    assert mod._names_statement_indices(q["options"]) is False


# ── statement-index: verbatim source wording + percentage shapes ─────────────
#
# The predicate is exercised above with a trimmed stem. This pins the SEBI
# question as it is actually printed — the stem carries "174(1)" and "2013",
# which are exactly the kind of stray digits the old substring search keyed on.
# Percentages were required to stay quiet but had no coverage.


def test_sebi_q1_verbatim_source_wording(tmp_path):
    """SEBI-GA-2022-P1-CA Q1 exactly as printed, section number and year included."""
    body = (
        _para("1. As per section 174(1) of companies Act, 2013, The quorum for a "
              "meeting of the board of directors of a company shall be _______ of "
              "total strength or ___ directors, whichever is higher")
        + _para("A. 2/3,1") + _para("B. 1/3,2") + _para("C. 1/2,2")
        + _para("D. 3/4, 1") + _para("E. None of the above")
    )
    questions = _question(tmp_path, body)
    assert questions[0]["options"] == [
        ("a", "2/3,1"), ("b", "1/3,2"), ("c", "1/2,2"),
        ("d", "3/4, 1"), ("e", "None of the above"),
    ]
    assert mod._names_statement_indices(questions[0]["options"]) is False
    assert mod.validate(questions, 1) == []


@pytest.mark.parametrize("name,options", [
    ("bare percentages",    ["1%", "2%", "5%", "10%"]),
    ("percentage pairs",    ["1% and 2%", "3% and 4%", "5% and 6%", "None of the above"]),
    ("qualified percents",  ["Not more than 1%", "Not more than 2%", "Up to 5%", "None of the above"]),
    ("spelled percentages", ["10 per cent", "20 per cent", "1 and 2 per cent", "None of the above"]),
    ("mixed units",         ["1 crore", "2 crore", "1 and 2 lakh", "None of the above"]),
])
def test_percentages_and_units_do_not_demand_numbering(name, options):
    """A trailing unit means the digits are a quantity, not a statement pointer."""
    assert mod._names_statement_indices([("x", o) for o in options]) is False


# ── index reference with nothing to index: two defects, two diagnoses ────────
#
# IFSCA-GA-2023-P2P2-FIN Q5 prints "A. RBI / B. MMTC / C. Banks / D. 1 and 3 /
# E. All of the above". Option (d) IS an index reference by shape, so the check
# fires correctly — but the numerals point at options (a) and (c), not at
# statements, and the stem never carried a numbered list. The old message
# asserted the stem "lost its list numbering" and pointed at
# --number-unmarked-statements, which cannot help here and whose only manual
# equivalent would be inventing statements that were never printed.
#
# Both defects still error. Only the diagnosis differs.


def _ifsca_q5(tmp_path, name="ifsca.docx"):
    body = (
        _para("1. Which of the following entities can participate in the auction of "
              "gold under the Gold Monetization Scheme (GMS)? (Topic- Bullion)")
        + _para("A. RBI") + _para("B. MMTC") + _para("C. Banks")
        + _para("D. 1 and 3") + _para("E. All of the above")
    )
    return _question(tmp_path, body, name)


def test_ifsca_q5_still_errors(tmp_path):
    """The paper is defective and must never import silently."""
    errors = mod.validate(_ifsca_q5(tmp_path), 1)
    assert len(errors) == 1
    assert errors[0].startswith("Q1: option (d) '1 and 3' refers to items by number")


def test_ifsca_q5_names_the_real_defect(tmp_path):
    """Quote the option, offer the likelier reading, and give a usable remedy."""
    error = mod.validate(_ifsca_q5(tmp_path), 1)[0]
    assert "'RBI', 'MMTC', 'Banks'" in error
    assert "point at the options themselves" in error
    assert "--number-unmarked-statements cannot help" in error
    assert "Fix the source document or exclude the question." in error
    # The old, wrong diagnosis must not appear on this shape.
    assert "lost its list numbering" not in error


def test_ifsca_q5_options_parse_intact(tmp_path):
    """The diagnosis change must not disturb parsing — a-e, text unchanged."""
    assert _ifsca_q5(tmp_path)[0]["options"] == [
        ("a", "RBI"), ("b", "MMTC"), ("c", "Banks"),
        ("d", "1 and 3"), ("e", "All of the above"),
    ]


def test_lost_numbering_keeps_its_own_diagnosis(tmp_path):
    """A real lost-numbering paper is still told it lost its numbering, and that
    the flag can restore the run — the remedy that actually applies there."""
    body = (
        _para("1. Consider the following statements:")
        + _para("Jhelum River passes through Wular Lake.")
        + _para("Krishna River directly feeds Kolleru Lake.")
        + _para("Which of the statements given above is/are correct?")
        + _para("(a) 1 only\n(b) 2 only\n(c) Both 1 and 2\n(d) Neither 1 nor 2")
    )
    error = mod.validate(_question(tmp_path, body), 1)[0]
    assert "lost its list numbering" in error
    assert "--number-unmarked-statements restores the run" in error
    # The options-referring-to-options reading must not be offered here.
    assert "point at the options themselves" not in error


def test_lost_numbering_without_a_run_says_the_flag_cannot_help(tmp_path):
    """No lead-in and no closing interrogative: nothing to number, so say so."""
    body = (
        _para("1. Which one is correct?")
        + _para("(a) 1 only\n(b) 2 only\n(c) Both 1 and 2\n(d) Neither 1 nor 2")
    )
    error = mod.validate(_question(tmp_path, body), 1)[0]
    assert "lost its list numbering" in error
    assert "--number-unmarked-statements cannot help" in error
    assert "Fix the source document or exclude the question." in error


def test_validate_does_not_renumber_the_stem_as_a_side_effect(tmp_path):
    """Reporting must be read-only: _statement_run must not mutate what it inspects."""
    body = (
        _para("1. Consider the following statements:")
        + _para("Jhelum River passes through Wular Lake.")
        + _para("Krishna River directly feeds Kolleru Lake.")
        + _para("Which of the statements given above is/are correct?")
        + _para("(a) 1 only\n(b) 2 only\n(c) Both 1 and 2\n(d) Neither 1 nor 2")
    )
    questions = _question(tmp_path, body)
    before = list(questions[0]["stem_parts"])
    mod.validate(questions, 1)
    mod.validate(questions, 1)
    assert questions[0]["stem_parts"] == before
    # and the opt-in restoration still works afterwards
    assert mod._number_unmarked(questions[0]) is True
    assert questions[0]["stem_parts"][1:3] == [
        "1. Jhelum River passes through Wular Lake.",
        "2. Krishna River directly feeds Kolleru Lake.",
    ]


# ── descriptive mode (Phase II English papers) ───────────────────────────────
#
# Five PFRDA/IFSCA Phase II English papers carry essay topics, precis passages
# and comprehension questions — no options, no answer key. The converter is
# MCQ-only, so every question failed the complete-label-set gate and the papers
# emitted nothing usable. --descriptive turns off the OPTION checks only; empty
# stems, a broken question run and a wrong count remain errors.


def _descriptive_paper(tmp_path, name="desc.docx"):
    body = (
        _para("1. Write an essay in about 300 words on: The role of pension "
              "regulation in a developing economy.")
        + _para("2. Make a precis of the following passage in about one-third of "
                "its length and suggest a suitable title.")
        + _para("3. Read the passage above and answer: what does the author "
                "identify as the principal constraint on coverage?")
    )
    return _question(tmp_path, body, name)


def test_descriptive_paper_validates_with_no_options(tmp_path):
    questions = _descriptive_paper(tmp_path)
    assert len(questions) == 3
    assert all(q["options"] == [] for q in questions)
    assert mod.validate(questions, 3, descriptive=True) == []


def test_descriptive_paper_fails_without_the_flag(tmp_path):
    """Without --descriptive these are just questions with no options."""
    errors = mod.validate(_descriptive_paper(tmp_path), 3)
    assert len(errors) == 3
    assert all("options are none" in e for e in errors)


def test_descriptive_envelope_omits_options_and_key(tmp_path):
    envelope = mod.build_envelope(
        _descriptive_paper(tmp_path), ref_prefix="P2P1", answer_key={},
        dropped=set(), difficulty=None, descriptive=True,
    )
    row = envelope["questions"][0]
    assert envelope["format_version"] == 2
    assert row["question_type"] == "descriptive"
    assert "options" not in row
    assert "correct_option_label" not in row
    assert row["question_number"] == 1 and row["display_order"] == 1
    assert row["source_question_ref"] == "P2P1-Q1"
    assert row["question_text"].startswith("Write an essay in about 300 words")


def test_descriptive_still_reports_an_empty_stem(tmp_path):
    """Turning off the option checks must not turn off the rest."""
    q = [{"number": 1, "stem_parts": [], "options": [], "has_table": False}]
    assert any("empty stem" in e for e in mod.validate(q, 1, descriptive=True))


def test_descriptive_still_reports_a_broken_question_run(tmp_path):
    q = [
        {"number": 1, "stem_parts": ["a"], "options": [], "has_table": False},
        {"number": 3, "stem_parts": ["b"], "options": [], "has_table": False},
    ]
    errors = mod.validate(q, 2, descriptive=True)
    assert any("not a contiguous" in e for e in errors)


def test_descriptive_still_reports_a_wrong_question_count(tmp_path):
    errors = mod.validate(_descriptive_paper(tmp_path), 5, descriptive=True)
    assert any("parsed 3 questions, expected 5" in e for e in errors)


def test_descriptive_refuses_a_paper_that_parsed_options(tmp_path):
    """An MCQ paper converted under --descriptive would lose its options silently."""
    body = (
        _para("1. Which one of the following is correct?")
        + _para("(a) One\n(b) Two\n(c) Three\n(d) Four")
    )
    errors = mod.validate(_question(tmp_path, body), 1, descriptive=True)
    assert len(errors) == 1
    assert "--descriptive was given but the question parsed 4 options" in errors[0]
    assert "would be discarded" in errors[0]


def test_answer_key_is_rejected_with_descriptive(tmp_path, capsys):
    key = tmp_path / "key.csv"
    key.write_text("question_number,correct_option_label\n1,a\n", encoding="utf-8")
    body = _para("1. Write an essay.")
    rc = mod.main([_docx(tmp_path, body, "k.docx"), "--year", "2023", "--set-code", "A",
                   "--descriptive", "--answer-key", str(key)])
    assert rc == 2
    assert "--answer-key cannot be combined with --descriptive" in capsys.readouterr().err


# ── MCQ behaviour is untouched ───────────────────────────────────────────────


def test_mcq_envelope_unchanged_when_descriptive_not_given(tmp_path):
    """The default path must emit exactly what it emitted before the flag existed."""
    body = (
        _para("1. Which one of the following is correct?")
        + _para("(a) One\n(b) Two\n(c) Three\n(d) Four")
    )
    questions = _question(tmp_path, body)
    assert mod.validate(questions, 1) == []
    assert mod.build_envelope(
        questions, ref_prefix="GS1", answer_key={1: "b"},
        dropped=set(), difficulty=None,
    ) == {
        "format_version": 2,
        "questions": [{
            "source_question_ref": "GS1-Q1",
            "question_number": 1,
            "display_order": 1,
            "question_text": "Which one of the following is correct?",
            "question_type": "mcq",
            "options": [
                {"label": "a", "source_label": "(a)", "text": "One", "display_order": 1},
                {"label": "b", "source_label": "(b)", "text": "Two", "display_order": 2},
                {"label": "c", "source_label": "(c)", "text": "Three", "display_order": 3},
                {"label": "d", "source_label": "(d)", "text": "Four", "display_order": 4},
            ],
            "correct_option_label": "b",
        }],
    }


def test_descriptive_suppresses_the_answer_key_warning(tmp_path, capsys):
    """The warning names correct_option_label and the v2 preflight, neither of
    which applies to a descriptive paper — it would send the operator hunting a
    key that does not exist for this paper."""
    body = _para("1. Write an essay in about 300 words on pension regulation.")
    out = tmp_path / "env.json"
    rc = mod.main([_docx(tmp_path, body, "d.docx"), "--year", "2023", "--set-code", "A",
                   "--descriptive", "--expect", "1", "-o", str(out)])
    assert rc == 0
    assert "no --answer-key supplied" not in capsys.readouterr().err


def test_mcq_still_warns_when_no_answer_key_is_given(tmp_path, capsys):
    """Unchanged for MCQ: there the warning is true and load-bearing."""
    body = (
        _para("1. Which one of the following is correct?")
        + _para("(a) One\n(b) Two\n(c) Three\n(d) Four")
    )
    out = tmp_path / "env.json"
    rc = mod.main([_docx(tmp_path, body, "m.docx"), "--year", "2023", "--set-code", "A",
                   "--expect", "1", "-o", str(out)])
    assert rc == 0
    assert "no --answer-key supplied" in capsys.readouterr().err


# ── the document's own answer-key table ──────────────────────────────────────
#
# Four SEBI Phase 1 Commerce papers print their key as a trailing
# "Question | Answer" table. _parse_lines appends every table row to the open
# stem, so the whole key landed on the paper's FINAL question. The key itself
# imported correctly (pyq_options carried exactly one is_correct per question);
# what leaked was the text — an aspirant served that last question was shown the
# answers to the entire paper. The four stems were stripped in the database by
# hand; these tests are what stops the next import from recreating them.


def _cells(values):
    return "".join(
        f"<w:tc><w:p><w:r><w:t>{v}</w:t></w:r></w:p></w:tc>" for v in values
    )


def _key_table(rows, header=("Question", "Answer")):
    trs = f"<w:tr>{_cells(header)}</w:tr>"
    trs += "".join(f"<w:tr>{_cells(row)}</w:tr>" for row in rows)
    return f"<w:tbl>{trs}</w:tbl>"


def _mcq(n, labels="abcd"):
    opts = "\n".join(f"({label}) Option {label.upper()}" for label in labels)
    return _para(f"{n}. Stem {n}?") + _para(opts)


def _paper(count, labels="abcd"):
    return "".join(_mcq(n, labels) for n in range(1, count + 1))


def _envelope(tmp_path, body, *, name="k.docx", extra=(), expect=None):
    out = tmp_path / f"{name}.json"
    argv = [_docx(tmp_path, body, name), "--year", "2023", "--set-code", "A",
            "--expect", str(expect if expect is not None else 1),
            "-o", str(out), *extra]
    rc = mod.main(argv)
    return rc, (json.loads(out.read_text(encoding="utf-8")) if rc == 0 else None)


def test_trailing_key_table_is_excluded_from_the_final_question_stem(tmp_path):
    """The leak itself: the key table must not reach the last question's text."""
    body = _paper(3) + _key_table([("1", "A"), ("2", "C"), ("3", "B")])
    questions, key = mod._parse_document(_docx(tmp_path, body, "leak.docx"))

    assert [q["stem_parts"] for q in questions] == [["Stem 1?"], ["Stem 2?"], ["Stem 3?"]]
    # Not merely "the answers are absent" — no trace of the table at all.
    assert "|" not in "\n".join(questions[-1]["stem_parts"])
    assert questions[-1]["has_table"] is False
    assert key == {1: "a", 2: "c", 3: "b"}


def test_key_table_is_emitted_as_correct_option_label_without_an_answer_key_csv(tmp_path):
    """Structured emission: a document carrying its own key needs no --answer-key."""
    body = _paper(2) + _key_table([("1", "D"), ("2", "B")])
    rc, envelope = _envelope(tmp_path, body, name="emit.docx", expect=2)

    assert rc == 0
    assert [row["correct_option_label"] for row in envelope["questions"]] == ["d", "b"]
    assert [row["question_text"] for row in envelope["questions"]] == ["Stem 1?", "Stem 2?"]


def test_key_table_with_trailing_empty_rows_keys_only_the_filled_rows(tmp_path):
    """Authors pad the table past the paper: "11 |", "12 |" under a 10-question
    paper. Padding is skipped, and it does not disqualify the table."""
    rows = [(str(n), "ABCD"[(n - 1) % 4]) for n in range(1, 11)]
    rows += [("11", ""), ("12", "")]
    body = _paper(10) + _key_table(rows)

    questions, key = mod._parse_document(_docx(tmp_path, body, "pad.docx"))
    assert sorted(key) == list(range(1, 11))
    assert 11 not in key and 12 not in key
    assert questions[-1]["stem_parts"] == ["Stem 10?"]

    rc, envelope = _envelope(tmp_path, body, name="pad2.docx", expect=10)
    assert rc == 0
    assert [row["correct_option_label"] for row in envelope["questions"]] == [
        "a", "b", "c", "d", "a", "b", "c", "d", "a", "b",
    ]


def test_five_option_key_table_normalises_uppercase_labels_to_lowercase(tmp_path):
    """Printed keys are uppercase; pyq_options.option_label is lowercase. The
    case is normalised at the boundary, so an "E" key matches option ("e")."""
    body = _paper(2, labels="abcde") + _key_table([("1", "E"), ("2", "e")])
    rc, envelope = _envelope(tmp_path, body, name="five.docx", expect=2)

    assert rc == 0
    for row in envelope["questions"]:
        assert row["correct_option_label"] == "e"
        # The key resolves against an option that actually exists on the row.
        assert row["correct_option_label"] in [o["label"] for o in row["options"]]
    assert [o["label"] for o in envelope["questions"][0]["options"]] == list("abcde")


def test_document_with_no_key_table_is_left_completely_untouched(tmp_path):
    """Byte-identical output is the contract: pyq_bulk_import dedupes on
    normalized_question_hash, so a stem that drifts re-imports as a new question.
    The line stream is returned unchanged — the same object, not merely an equal
    one — so nothing downstream can differ."""
    body = _paper(2)
    lines = mod._read_lines(_docx(tmp_path, body, "plain.docx"))
    kept, key = mod._split_embedded_answer_key(lines)

    assert kept is lines
    assert key == {}

    rc, envelope = _envelope(tmp_path, body, name="plain2.docx", expect=2)
    assert rc == 0
    assert [row["question_text"] for row in envelope["questions"]] == ["Stem 1?", "Stem 2?"]
    assert [row["correct_option_label"] for row in envelope["questions"]] == [None, None]


def test_a_trailing_content_table_is_not_read_as_a_key(tmp_path):
    """Shape-gating, from the other side: a pairs table printed last is content
    and still belongs to the stem it was printed under."""
    tbl = f"<w:tbl><w:tr>{_cells(('Party', 'Leader'))}</w:tr>" \
          f"<w:tr>{_cells(('Swatantra', 'Rajagopalachari'))}</w:tr></w:tbl>"
    body = _para("1. Consider the following pairs:") + tbl + _para(
        "(a) One\n(b) Two\n(c) Three\n(d) Four")

    lines = mod._read_lines(_docx(tmp_path, body, "pairs.docx"))
    kept, key = mod._split_embedded_answer_key(lines)
    assert kept is lines
    assert key == {}

    questions = mod._parse_blocks(_docx(tmp_path, body, "pairs2.docx"))
    assert "Swatantra | Rajagopalachari" in questions[0]["stem_parts"]


def test_key_table_naming_more_questions_than_the_paper_fails_loudly(tmp_path, capsys):
    """Truncating to the questions that exist would key the rest against a
    document nobody checked."""
    rows = [(str(n), "A") for n in range(1, 13)]
    body = _paper(10) + _key_table(rows)
    rc, _ = _envelope(tmp_path, body, name="over.docx", expect=10)

    assert rc == 1
    err = capsys.readouterr().err
    assert "names questions outside the paper's 1..10: [11, 12]" in err
    assert "answer-key table" in err


def test_key_table_short_of_the_question_count_fails_loudly(tmp_path, capsys):
    """The other direction: a key that stops early must not import a paper whose
    tail silently carries no correct option."""
    body = _paper(10) + _key_table([(str(n), "A") for n in range(1, 9)])
    rc, _ = _envelope(tmp_path, body, name="short.docx", expect=10)

    assert rc == 1
    assert "is missing non-dropped questions: [9, 10]" in capsys.readouterr().err


def test_key_table_disagreeing_with_an_answer_key_csv_is_an_error(tmp_path, capsys):
    """Two keys that differ is not a tie to break — neither is trustworthy."""
    key_path = tmp_path / "key.csv"
    key_path.write_text("question_number,correct_option_label\n1,a\n2,b\n", encoding="utf-8")
    body = _paper(2) + _key_table([("1", "A"), ("2", "C")])
    rc, _ = _envelope(tmp_path, body, name="clash.docx", expect=2,
                      extra=["--answer-key", str(key_path)])

    assert rc == 1
    err = capsys.readouterr().err
    assert "disagrees with the key table printed in the document" in err
    assert "Q2 (CSV 'b', document 'c')" in err
    assert "Q1" not in err


def test_key_table_keying_a_question_twice_is_an_error(tmp_path):
    """A question keyed twice is source damage; picking a winner is inference."""
    body = _paper(2) + _key_table([("1", "A"), ("1", "C"), ("2", "B")])
    with pytest.raises(ValueError, match=r"Q1 is keyed twice"):
        mod._parse_document(_docx(tmp_path, body, "dup.docx"))


def test_key_split_across_two_trailing_tables_is_read_as_one_key(tmp_path):
    """Long papers print the key in two columns of table. Both are excluded."""
    body = (
        _paper(4)
        + _key_table([("1", "A"), ("2", "B")])
        + _key_table([("3", "C"), ("4", "D")])
    )
    questions, key = mod._parse_document(_docx(tmp_path, body, "split.docx"))

    assert key == {1: "a", 2: "b", 3: "c", 4: "d"}
    assert questions[-1]["stem_parts"] == ["Stem 4?"]


def test_descriptive_paper_drops_the_key_but_still_excludes_the_table(tmp_path):
    """A descriptive row has no correct_option_label to carry — but the leak is
    the stem, and the stem is cleaned either way."""
    body = (
        _para("1. Write an essay on pension regulation.")
        + _para("2. Precis the passage below.")
        + _key_table([("1", "A"), ("2", "B")])
    )
    rc, envelope = _envelope(tmp_path, body, name="desc.docx", expect=2,
                             extra=["--descriptive"])

    assert rc == 0
    assert [row["question_text"] for row in envelope["questions"]] == [
        "Write an essay on pension regulation.",
        "Precis the passage below.",
    ]
    assert all("correct_option_label" not in row for row in envelope["questions"])


def test_report_names_the_document_as_the_key_source(tmp_path, capsys):
    body = _paper(2) + _key_table([("1", "A"), ("2", "B")])
    rc, _ = _envelope(tmp_path, body, name="report.docx", expect=2, extra=["--report"])

    assert rc == 0
    err = capsys.readouterr().err
    assert "answer key: 2 (read from the document's own key table)" in err
    assert "no --answer-key supplied" not in err


# ── shared directions blocks (reasoning / DI / comprehension sets) ────────────
#
# One instruction block governs a RANGE of questions and is printed between the
# previous question's last option and the next question's marker — exactly where
# the trailing-note branch appends to the last option. Before this was handled,
# the whole block landed inside option (e) of the question BEFORE the set, and
# every question in the set lost the constraints it needed.


def _ranged(tmp_path, body, name="dir.docx"):
    """Parse collecting stimuli, the way main() does."""
    path = _docx(tmp_path, body, name)
    lines, _ = mod._split_embedded_answer_key(mod._read_lines(path))
    _, pattern = mod.detect_marker(lines)
    stimuli: list[dict] = []
    questions = mod._parse_lines(lines, pattern, mod.detect_option_style(lines),
                                 stimuli_out=stimuli)
    return questions, stimuli


_SET_BODY = (
    "1. Who is an immediate neighbour of Alice?",
    "(a) Emily\n(b) Carol\n(c) Frank\n(d) George\n(e) Bob",
    "Directions (2-3): Study the information carefully and answer the question.",
    "Ten persons X, Y and Z are staying in two different flats.",
    "Z stays on an odd-numbered floor in Flat Alpha, two floors above R.",
    "2. Who stays immediately above N?",
    "(a) S\n(b) R\n(c) X\n(d) Y\n(e) None of these",
    "3. On which floor does P stay?",
    "(a) One\n(b) Two\n(c) Three\n(d) Four\n(e) Five",
)


def test_directions_block_does_not_land_in_the_previous_option(tmp_path):
    """The defect itself: the block was appended to option (e) of question 1."""
    questions, _ = _ranged(tmp_path, "".join(_para(p) for p in _SET_BODY))
    assert questions[0]["options"][-1] == ("e", "Bob")
    assert all("Directions" not in text for _, text in questions[0]["options"])


def test_directions_block_becomes_a_stimulus_governing_its_range(tmp_path):
    questions, stimuli = _ranged(tmp_path, "".join(_para(p) for p in _SET_BODY))
    assert len(stimuli) == 1
    s = stimuli[0]
    assert s["ref"] == "directions-2-3"
    assert s["governs"] == [2, 3]
    assert s["content_text"].startswith("Study the information carefully")
    assert "Z stays on an odd-numbered floor" in s["content_text"]
    assert questions[1]["stimulus_refs"] == ["directions-2-3"]
    assert questions[2]["stimulus_refs"] == ["directions-2-3"]
    # The question BEFORE the block is not governed by it.
    assert "stimulus_refs" not in questions[0]


@pytest.mark.parametrize("line,expected", [
    ("Directions (6-10): Study the information", (6, 10)),
    ("Directions (6--10): Answer the questions", (6, 10)),
    ("Direction (46-50): Study the following", (46, 50)),
    ("Instruction (6-12): Read the given passage", (6, 12)),
    ("Directions (11-15) Study the following", (11, 15)),
    ("Directions (16 - 20): What value comes", (16, 20)),
    ("Directions: (11-13) In each question", (11, 13)),
    ("6-10) Direction: Study the information", (6, 10)),
    ("Direction (6-9) Find the missing term", (6, 9)),
])
def test_every_printed_directions_shape_in_the_corpus_is_recognised(line, expected):
    """Nine shapes occur across SEBI/PFRDA/IFSCA — word first and range first,
    one hyphen or two, spaced or not, colon frequently absent."""
    got = mod._match_directions(line)
    assert got is not None and got[:2] == expected


@pytest.mark.parametrize("line", [
    "Directions: In the question below, two statements are given.",  # no range
    "Directions (10-6): a reversed range is damage, not a range",
    "(a) Some ordinary option text",
    "1. An ordinary question stem",
    "The instructions were clear to every candidate.",
])
def test_lines_that_are_not_ranged_directions_are_left_alone(line):
    """A block naming no questions cannot be linked or bounded, so it keeps the
    behaviour it had rather than being guessed at."""
    assert mod._match_directions(line) is None


def test_a_paper_with_no_directions_block_parses_byte_identically(tmp_path):
    """The constraint that matters: pyq_bulk_import dedupes on
    normalized_question_hash, so any drift re-imports as new questions."""
    body = "".join(
        _para(f"{n}. Question {n} stem?")
        + _para(f"(a) A{n}\n(b) B{n}\n(c) C{n}\n(d) D{n}")
        for n in range(1, 11)
    )
    path = _docx(tmp_path, body, "plain.docx")
    lines, key = mod._split_embedded_answer_key(mod._read_lines(path))
    _, pattern = mod.detect_marker(lines)
    style = mod.detect_option_style(lines)

    without = mod.build_envelope(
        mod._parse_lines(lines, pattern, style),
        ref_prefix="GS1", answer_key=key, dropped=set(), difficulty=None)
    collected: list[dict] = []
    with_out = mod.build_envelope(
        mod._parse_lines(lines, pattern, style, stimuli_out=collected),
        ref_prefix="GS1", answer_key=key, dropped=set(), difficulty=None,
        stimuli=collected)

    assert collected == []
    assert json.dumps(without, sort_keys=False) == json.dumps(with_out, sort_keys=False)
    # An empty array is still a key; the envelope must not grow one.
    assert "stimuli" not in with_out
    assert all("stimulus_refs" not in row for row in with_out["questions"])


def test_envelope_carries_stimuli_and_refs_in_the_v2_shape(tmp_path):
    questions, stimuli = _ranged(tmp_path, "".join(_para(p) for p in _SET_BODY))
    env = mod.build_envelope(questions, ref_prefix="P1", answer_key={},
                             dropped=set(), difficulty=None, stimuli=stimuli)
    assert env["stimuli"] == [{
        "ref": "directions-2-3",
        "stimulus_type": "caselet",
        "content_text": stimuli[0]["content_text"],
        "display_order": 1,
    }]
    assert env["questions"][1]["stimulus_refs"] == ["directions-2-3"]
    # Every declared ref must resolve, or preflight rejects the batch.
    declared = {s["ref"] for s in env["stimuli"]}
    for row in env["questions"]:
        assert set(row.get("stimulus_refs", [])) <= declared


def test_a_comprehension_block_is_typed_as_a_passage(tmp_path):
    """stimulus_type is decided by evidence in the source, not inferred from
    content: the word 'passage' in the instruction is what marks one."""
    body = (
        _para("1. A standalone question?")
        + _para("(a) A\n(b) B\n(c) C\n(d) D")
        + _para("Instruction (2-2): Read the given passage and answer the question.")
        + _para("The rise of technology has reshaped industries and daily routines.")
        + _para("2. What has technology reshaped?")
        + _para("(a) Industries\n(b) Nothing\n(c) Costs\n(d) Nobody")
    )
    _, stimuli = _ranged(tmp_path, body, "passage.docx")
    assert stimuli[0]["stimulus_type"] == "passage"


def test_two_blocks_in_one_paper_each_govern_their_own_range(tmp_path):
    body = (
        _para("Directions (1-2): First block text here.")
        + _para("Constraints for the first set.")
        + _para("1. First?") + _para("(a) A\n(b) B\n(c) C\n(d) D")
        + _para("2. Second?") + _para("(a) A\n(b) B\n(c) C\n(d) D")
        + _para("Directions (3-4): Second block text here.")
        + _para("Constraints for the second set.")
        + _para("3. Third?") + _para("(a) A\n(b) B\n(c) C\n(d) D")
        + _para("4. Fourth?") + _para("(a) A\n(b) B\n(c) C\n(d) D")
    )
    questions, stimuli = _ranged(tmp_path, body, "two.docx")
    assert [s["governs"] for s in stimuli] == [[1, 2], [3, 4]]
    assert [q.get("stimulus_refs") for q in questions] == [
        ["directions-1-2"], ["directions-1-2"], ["directions-3-4"], ["directions-3-4"]]
    assert mod._validate_stimuli(stimuli, questions) == []


def test_a_block_before_question_one_is_still_captured(tmp_path):
    """Front matter is skipped, but a block that governs question 1 is not front
    matter — it is the instruction for the first set on the paper."""
    body = (
        _para("Directions (1-1): Study the information carefully.")
        + _para("Some shared constraints.")
        + _para("1. A question?") + _para("(a) A\n(b) B\n(c) C\n(d) D")
    )
    questions, stimuli = _ranged(tmp_path, body, "front.docx")
    assert stimuli[0]["governs"] == [1]
    assert questions[0]["stimulus_refs"] == ["directions-1-1"]


def test_a_block_naming_absent_questions_links_to_nothing_and_is_reported(tmp_path):
    body = (
        _para("1. Only question?") + _para("(a) A\n(b) B\n(c) C\n(d) D")
        + _para("Directions (7-9): Instructions for questions that are not here.")
        + _para("Constraints nobody can use.")
    )
    questions, stimuli = _ranged(tmp_path, body, "absent.docx")
    assert stimuli[0]["governs"] == []
    errors = mod._validate_stimuli(stimuli, questions)
    assert any("does not have" in e for e in errors)
    # An unlinked block is never emitted: a dangling ref fails preflight.
    env = mod.build_envelope(questions, ref_prefix="P", answer_key={},
                             dropped=set(), difficulty=None, stimuli=stimuli)
    assert "stimuli" not in env


def test_overlapping_blocks_are_reported_rather_than_silently_doubled(tmp_path):
    body = (
        _para("Directions (1-2): First block.")
        + _para("First constraints.")
        + _para("1. One?") + _para("(a) A\n(b) B\n(c) C\n(d) D")
        + _para("Directions (2-3): Second block overlapping the first.")
        + _para("Second constraints.")
        + _para("2. Two?") + _para("(a) A\n(b) B\n(c) C\n(d) D")
        + _para("3. Three?") + _para("(a) A\n(b) B\n(c) C\n(d) D")
    )
    questions, stimuli = _ranged(tmp_path, body, "overlap.docx")
    errors = mod._validate_stimuli(stimuli, questions)
    assert any("claimed by two directions blocks" in e for e in errors)


def test_an_empty_block_is_reported(tmp_path):
    """The range line matched but the block that should follow never arrived."""
    body = (
        _para("Directions (2-2):")
        + _para("2. A question with no shared text above it?")
        + _para("(a) A\n(b) B\n(c) C\n(d) D")
    )
    # numbering starts at 2, so parse from a paper that opens at 1
    body = _para("1. First?") + _para("(a) A\n(b) B\n(c) C\n(d) D") + body
    questions, stimuli = _ranged(tmp_path, body, "empty.docx")
    assert any("carries no text" in e for e in mod._validate_stimuli(stimuli, questions))


def test_options_of_governed_questions_are_untouched_by_the_block(tmp_path):
    """The set's own questions parse exactly as they would standalone — the block
    is collected beside them, not merged into them."""
    questions, _ = _ranged(tmp_path, "".join(_para(p) for p in _SET_BODY))
    assert [t for _, t in questions[1]["options"]] == ["S", "R", "X", "Y", "None of these"]
    assert [t for _, t in questions[2]["options"]] == ["One", "Two", "Three", "Four", "Five"]
    assert questions[1]["stem_parts"] == ["Who stays immediately above N?"]
