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
    with pytest.raises(ValueError, match="not a complete a-d"):
        mod.apply_corrections(_question(tmp_path, body), {"1": {"add_options": {"d": "Four"}}})
