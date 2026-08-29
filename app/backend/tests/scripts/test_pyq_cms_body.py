"""Unit tests for ``scripts/pyq_cms_body.py``.

The script exists because the generic CMS bulk-import endpoint is a whitelist
passthrough: it requires only ``pyq_paper_id`` and ``question_text``, treats
``question_number`` as optional, and never cross-checks it. That is how 1,789
rows across 19 papers were written with ``question_number`` NULL. Every test
here is ultimately about that: the rows this script emits are always numbered,
never carry options, and never lose a field to the whitelist in silence.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_SCRIPT = _ROOT / "scripts" / "pyq_cms_body.py"
_spec = importlib.util.spec_from_file_location("pyq_cms_body", _SCRIPT)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

PAPER = "9ca02669-5875-4e97-b2bb-5f04ed49e94b"


def _envelope(n=3, patch=None, drop=None):
    """Build a descriptive envelope. ``patch`` and ``drop`` are keyed by 1-based
    question number: {2: {"question_type": "mcq"}} and {2: ["question_number"]}."""
    patch = patch or {}
    drop = drop or {}
    questions = []
    for i in range(1, n + 1):
        q = {
            "source_question_ref": f"P2P1-Q{i}",
            "question_number": i,
            "display_order": i,
            "question_text": f"Write an essay on topic {i}.",
            "question_type": "descriptive",
        }
        q.update(patch.get(i, {}))
        for key in drop.get(i, []):
            q.pop(key, None)
        questions.append(q)
    return {"format_version": 2, "questions": questions}


def _reshape(envelope):
    return mod.reshape(envelope, paper_id=PAPER, reason="bulk import of a descriptive paper")


# ── the shape the CMS endpoint expects ───────────────────────────────────────


def test_body_is_the_generic_cms_shape():
    body = _reshape(_envelope())
    assert body["entity"] == "pyq-questions"
    assert len(body["reason"]) >= 8
    assert isinstance(body["rows"], list) and len(body["rows"]) == 3


def test_every_row_is_numbered():
    """The whole point: question_number explicit on every row, 1..N."""
    rows = _reshape(_envelope(n=5))["rows"]
    assert [r["question_number"] for r in rows] == [1, 2, 3, 4, 5]
    assert all(isinstance(r["question_number"], int) for r in rows)


def test_no_row_carries_an_options_key():
    rows = _reshape(_envelope())["rows"]
    assert all("options" not in r for r in rows)
    assert all("correct_option_label" not in r for r in rows)


def test_descriptive_type_is_preserved():
    rows = _reshape(_envelope())["rows"]
    assert all(r["question_type"] == "descriptive" for r in rows)


def test_paper_id_and_source_kind_are_stamped():
    """source_kind is whitelisted and 'bulk_import' passes the migration-149 CHECK.
    Nothing on the write path stamps it, so an import is otherwise indistinguishable
    from a hand-typed row."""
    rows = _reshape(_envelope())["rows"]
    assert all(r["pyq_paper_id"] == PAPER for r in rows)
    assert all(r["source_kind"] == "bulk_import" for r in rows)


def test_stem_and_ref_survive_the_reshape():
    row = _reshape(_envelope())["rows"][0]
    assert row["question_text"] == "Write an essay on topic 1."
    assert row["source_question_ref"] == "P2P1-Q1"
    assert row["display_order"] == 1


# ── the guards ───────────────────────────────────────────────────────────────


def test_missing_question_number_is_refused():
    with pytest.raises(ValueError, match="missing required field"):
        _reshape(_envelope(drop={2: ["question_number"]}))


def test_assertion_fires_on_a_row_missing_its_number():
    """The post-reshape gate, exercised directly against rows as they'd be sent."""
    rows = [
        {"question_number": 1, "question_text": "a"},
        {"question_text": "b"},
    ]
    with pytest.raises(ValueError, match="rows\\[1\\] has no question_number"):
        mod.assert_every_row_numbered(rows)


def test_assertion_fires_on_a_non_integer_number():
    rows = [{"question_number": "2", "question_text": "a"}]
    with pytest.raises(ValueError, match="expected an integer"):
        mod.assert_every_row_numbered(rows)


def test_assertion_names_the_consequence():
    """The message has to say WHY, or the next person relaxes the check."""
    with pytest.raises(ValueError, match="leave question_number NULL"):
        mod.assert_every_row_numbered([{"question_text": "a"}])


def test_non_contiguous_numbering_is_refused():
    env = _envelope(n=3, patch={3: {"question_number": 7}})
    with pytest.raises(ValueError, match="expected a contiguous 1..3 run"):
        _reshape(env)


def test_an_mcq_envelope_is_refused_rather_than_stripped():
    env = _envelope(n=1, patch={1: {"question_type": "mcq", "options": [
        {"label": "a", "text": "One"}, {"label": "b", "text": "Two"}],
        "correct_option_label": "a"}})
    with pytest.raises(ValueError) as exc:
        _reshape(env)
    assert "this is an MCQ envelope" in str(exc.value)
    assert "would discard them" in str(exc.value)


def test_unknown_keys_are_refused_rather_than_silently_dropped():
    env = _envelope(n=1, patch={1: {"dropped_by_upsc": True}})
    with pytest.raises(ValueError, match="would discard.*without comment"):
        _reshape(env)


def test_all_problems_are_reported_at_once():
    env = _envelope(n=2, patch={1: {"question_type": "mcq"}}, drop={2: ["question_text"]})
    with pytest.raises(ValueError) as exc:
        _reshape(env)
    assert "questions[0] has question_type 'mcq'" in str(exc.value)
    assert "questions[1] is missing required field" in str(exc.value)


def test_a_non_envelope_is_refused():
    with pytest.raises(ValueError, match="not a converter envelope"):
        _reshape({"rows": []})
    with pytest.raises(ValueError, match="non-empty list"):
        _reshape({"questions": []})


# ── end to end through main() ────────────────────────────────────────────────


def test_main_writes_a_body_file(tmp_path, capsys):
    src = tmp_path / "env.json"
    src.write_text(json.dumps(_envelope()), encoding="utf-8")
    out = tmp_path / "body.json"
    rc = mod.main([str(src), "--paper-id", PAPER, "-o", str(out)])
    assert rc == 0
    body = json.loads(out.read_text(encoding="utf-8"))
    assert body["entity"] == "pyq-questions"
    assert [r["question_number"] for r in body["rows"]] == [1, 2, 3]
    assert "wrote 3 rows" in capsys.readouterr().err


def test_main_writes_nothing_when_a_row_is_unnumbered(tmp_path, capsys):
    src = tmp_path / "env.json"
    src.write_text(json.dumps(_envelope(drop={2: ["question_number"]})), encoding="utf-8")
    out = tmp_path / "body.json"
    rc = mod.main([str(src), "--paper-id", PAPER, "-o", str(out)])
    assert rc == 1
    assert not out.exists()
    assert "missing required field" in capsys.readouterr().err


def test_main_rejects_a_short_reason(tmp_path, capsys):
    src = tmp_path / "env.json"
    src.write_text(json.dumps(_envelope()), encoding="utf-8")
    rc = mod.main([str(src), "--paper-id", PAPER, "--reason", "short"])
    assert rc == 2
    assert "at least 8 characters" in capsys.readouterr().err
