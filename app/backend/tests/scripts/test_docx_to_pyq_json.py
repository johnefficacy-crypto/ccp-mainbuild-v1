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
