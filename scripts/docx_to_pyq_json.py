#!/usr/bin/env python3
"""Convert a UPSC CSE Prelims question paper (.docx) into a PYQ bulk-import v2 envelope.

Deterministic, stdlib-only (``zipfile`` + ``xml.etree``) — no new dependency, no
OCR, no model in the loop. A ``.docx`` carries an exact text layer; this reads it
verbatim so the same input always produces byte-identical output. That matters
because ``pyq_bulk_import`` dedupes on ``normalized_question_hash``: text that
drifts between runs re-imports as a new question instead of deduping.

Output is the v2 envelope documented in
``app/backend/app/exam_intelligence/pyq_bulk_import.py``::

    POST /api/admin/exam-intelligence-cms/pyq-papers/{paper_id}/bulk-import/preflight
    POST /api/admin/exam-intelligence-cms/pyq-papers/{paper_id}/bulk-import/commit

Answer keys are NOT inferred. ``correct_option_label`` is null unless an explicit
``--answer-key`` CSV is supplied, and the envelope is marked incomplete without
one. The v2 importer rejects an ``mcq`` row with no ``correct_option_label``, so
an unkeyed envelope fails preflight by design rather than importing a guess.

Usage::

    python scripts/docx_to_pyq_json.py paper.docx \
        --year 2024 --set-code C --paper-label GS1 \
        --answer-key key_2024.csv \
        --dropped 42,47,90 \
        -o pyq_2024_prelims_gs1_setc.json

    # inspect the parse without writing a file
    python scripts/docx_to_pyq_json.py paper.docx --year 2024 --set-code C --report
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

# A question stem opens with "<n>. " at paragraph start. The number must equal
# the next expected question number (see _parse_blocks) — a bare positional
# regex would also match statement lists and years inside a stem.
Q_START = re.compile(r"^\s*(\d{1,3})\.\s+(.*)$", re.S)

# Options print as "(a) text". UPSC uses lowercase a-d throughout Prelims GS.
OPT = re.compile(r"^\s*\(([a-d])\)\s*(.*)$", re.S)

# The supplied .docx files are retyped/OCR-derived, not UPSC originals, and carry
# character-level damage to option markers: "{b)" for "(b)", "c)" for "(c)",
# "(C)" for "(c)". This matches a marker with either bracket corrupted or absent
# and any case; _split_options only accepts the repair when the recovered letter
# is the next one due, so a genuinely scrambled marker still fails loudly.
OPT_LOOSE = re.compile(r"^\s*[\(\{\[\|]?\s*([A-Da-d])\s*[\)\}\]]\.?\s+(.*)$", re.S)

OPTION_LABELS = ("a", "b", "c", "d")

# Option text that points back at numbered statements in the stem: "1 and 2 only",
# "Only two", "All four". If a stem carries none of the numbering these refer to,
# the question is unanswerable as parsed.
STATEMENT_REF = re.compile(
    r"\b\d\s*(?:,|and)\s*\d\b|\bonly one\b|\bonly two\b|\bonly three\b"
    r"|\ball (?:three|four)\b|\bnone\b",
    re.I,
)


# ── docx reading ─────────────────────────────────────────────────────────────


def _para_text(p: ET.Element) -> str:
    """Concatenate a paragraph's runs, honouring tabs and explicit breaks.

    ``<w:br/>`` becomes ``\\n`` because UPSC papers frequently pack all four
    options into a single paragraph separated by breaks; the caller splits on it.
    """
    out: list[str] = []
    for node in p.iter():
        if node.tag == W + "t":
            out.append(node.text or "")
        elif node.tag == W + "tab":
            out.append("\t")
        elif node.tag == W + "br":
            out.append("\n")
    return "".join(out)


def _num_id(p: ET.Element) -> str | None:
    """Return the paragraph's numbering instance id, or None if unnumbered."""
    npr = p.find(W + "pPr/" + W + "numPr")
    if npr is None:
        return None
    node = npr.find(W + "numId")
    return node.get(W + "val") if node is not None else None


def _table_lines(tbl: ET.Element) -> list[str]:
    """Flatten a table to one pipe-joined line per row, in printed order.

    ``pyq_questions.question_text`` is plain text, so the pairs/matching tables
    that appear mid-stem have to be linearised. Cells are joined with ' | ' —
    unambiguous and reversible — rather than reflowed into prose.
    """
    lines: list[str] = []
    for tr in tbl.findall(W + "tr"):
        cells = [
            " ".join(_para_text(p) for p in tc.findall(W + "p")).strip()
            for tc in tr.findall(W + "tc")
        ]
        if any(cells):
            lines.append(" | ".join(cells))
    return lines


def _blocks(path: str):
    """Yield ('p', text, num_id) and ('tbl', lines, None) in document order."""
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    body = root.find(W + "body")
    if body is None:
        raise ValueError(f"{path}: no <w:body>")
    for child in body:
        if child.tag == W + "p":
            yield "p", _para_text(child), _num_id(child)
        elif child.tag == W + "tbl":
            yield "tbl", _table_lines(child), None


# ── parsing ──────────────────────────────────────────────────────────────────


def _split_options(text: str, next_expected: str | None) -> list[tuple[str, str]]:
    """Extract (label, text) pairs from a paragraph holding one or more options.

    Handles both layouts seen in the corpus: one option per paragraph, and all
    four in a single paragraph separated by line breaks.

    ``next_expected`` is the label the question is due next. A well-formed
    "(b)" is always taken. A damaged marker is repaired only when the letter it
    recovers is exactly ``next_expected`` — so "{b)" in the b position is fixed,
    while a marker reading "d" where "b" is due is left unmatched and surfaces
    as a validation error instead of being silently reordered.
    """
    found: list[tuple[str, str]] = []
    due = next_expected

    def _advance(label: str) -> str | None:
        i = OPTION_LABELS.index(label)
        return OPTION_LABELS[i + 1] if i + 1 < len(OPTION_LABELS) else None

    for line in text.split("\n"):
        m = OPT.match(line)
        if m:
            # "(b). Two" — the stray period belongs to the damaged marker, not
            # to the option text. No option legitimately opens with one.
            found.append((m.group(1), m.group(2).strip().lstrip(".:").strip()))
            due = _advance(m.group(1))
            continue
        loose = OPT_LOOSE.match(line)
        if loose and due is not None and loose.group(1).lower() == due:
            found.append((due, loose.group(2).strip()))
            due = _advance(due)
            continue
        if found:
            # Continuation of the previous option's text (wrapped line).
            label, prev = found[-1]
            found[-1] = (label, (prev + " " + line.strip()).strip())
    return found


def _parse_blocks(path: str) -> list[dict]:
    """Segment the document into questions.

    A new question starts only at a paragraph whose leading number is exactly
    ``expected`` — so "1. Konkani" inside a statement list can never open a
    question, and a paper with a skipped or repeated number fails loudly in
    ``validate`` rather than silently mis-segmenting.
    """
    questions: list[dict] = []
    cur: dict | None = None
    expected = 1
    list_counter: dict[str, int] = {}
    active_num_id: str | None = None

    for kind, value, num_id in _blocks(path):
        if kind == "tbl":
            if cur is not None:
                cur["stem_parts"].extend(value)
                cur["has_table"] = True
                active_num_id = None
            continue

        text = value.strip()
        if not text:
            continue

        m = Q_START.match(text)
        if m and int(m.group(1)) == expected:
            cur = {
                "number": expected,
                "stem_parts": [m.group(2).strip()] if m.group(2).strip() else [],
                "options": [],
                "has_table": False,
            }
            questions.append(cur)
            expected += 1
            list_counter.clear()
            active_num_id = None
            continue

        if cur is None:
            # Front matter before question 1 (instructions, headers).
            continue

        due = None
        if cur["options"]:
            last = cur["options"][-1][0]
            i = OPTION_LABELS.index(last)
            due = OPTION_LABELS[i + 1] if i + 1 < len(OPTION_LABELS) else None
        else:
            due = OPTION_LABELS[0]
        opts = _split_options(text, due)
        if opts:
            cur["options"].extend(opts)
            active_num_id = None
            continue

        if cur["options"]:
            # Text after the options began — a trailing note attached to the
            # last option rather than a new stem line.
            label, prev = cur["options"][-1]
            cur["options"][-1] = (label, (prev + " " + text).strip())
            continue

        if num_id is not None:
            # Word strips the visible marker from auto-numbered list items, but
            # the options reference them ("1, 2 and 3"), so restore it. Each
            # question's list carries its own numId starting at 1 (verified
            # across the 2022/2023/2024 corpus), so counting per instance is
            # exact — no numbering.xml restart semantics needed.
            if num_id != active_num_id:
                active_num_id = num_id
                list_counter.setdefault(num_id, 0)
            list_counter[num_id] += 1
            cur["stem_parts"].append(f"{list_counter[num_id]}. {text}")
        else:
            cur["stem_parts"].append(text)
            active_num_id = None

    return questions


# ── validation ───────────────────────────────────────────────────────────────


def validate(questions: list[dict], expected_count: int | None) -> list[str]:
    """Structural checks. Every failure is a hard error, never a silent repair."""
    errors: list[str] = []

    if expected_count is not None and len(questions) != expected_count:
        errors.append(f"parsed {len(questions)} questions, expected {expected_count}")

    for q in questions:
        n = q["number"]
        if not q["stem_parts"]:
            errors.append(f"Q{n}: empty stem")
        labels = [label for label, _ in q["options"]]
        if labels != list(OPTION_LABELS):
            errors.append(f"Q{n}: options are {labels or 'none'}, expected ['a','b','c','d']")
        for label, otext in q["options"]:
            if not otext.strip():
                errors.append(f"Q{n}: option ({label}) is empty")

        # A stem whose options say "1 and 2 only" must actually carry numbered
        # statements. Some source documents drop Word's list numbering entirely,
        # which leaves the statements present but unnumbered and the question
        # unanswerable. Three stem shapes legitimately satisfy the reference
        # without a numbered list: a restored "1." list, a table ("how many
        # pairs are correctly matched"), and UPSC's "Statement-I / Statement-II"
        # assertion-reason form.
        stem = "\n".join(q["stem_parts"])
        anchored = (
            re.search(r"^\d+\.\s", stem, re.M)
            or q.get("has_table")
            or re.search(r"\bStatement[-\s]*(?:I+|[1-9])\b", stem)
        )
        if any(STATEMENT_REF.search(t) for _, t in q["options"]) and not anchored:
            errors.append(
                f"Q{n}: options reference numbered statements but the stem carries none "
                f"(source document lost its list numbering)"
            )

    numbers = [q["number"] for q in questions]
    if numbers != list(range(1, len(numbers) + 1)):
        errors.append("question numbers are not a contiguous 1..N run")

    return errors


def _load_answer_key(path: str) -> dict[int, str]:
    """Read a two-column ``question_number,correct_option_label`` CSV.

    Deliberately a separate operator-supplied file: the official UPSC key PDFs
    are scans, and a key transcribed by anything other than a human reading the
    official document is not a key (CLAUDE.md → determinism over heuristics).
    """
    key: dict[int, str] = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            num = int(str(row["question_number"]).strip())
            label = str(row["correct_option_label"]).strip().lower()
            if label and label not in OPTION_LABELS:
                raise ValueError(f"answer key Q{num}: label {label!r} is not one of a-d")
            if num in key:
                raise ValueError(f"answer key Q{num}: duplicated")
            if label:
                key[num] = label
    return key


# ── envelope ─────────────────────────────────────────────────────────────────


def build_envelope(
    questions: list[dict],
    *,
    ref_prefix: str,
    answer_key: dict[int, str],
    dropped: set[int],
    difficulty: str | None,
) -> dict:
    """Emit the v2 bulk-import envelope.

    ``question_number`` and ``display_order`` both carry the printed number:
    each is uniquely indexed per paper (migration 223), and keeping them equal
    means the printed order survives a re-import.
    """
    rows = []
    for q in questions:
        n = q["number"]
        row = {
            "source_question_ref": f"{ref_prefix}-Q{n}",
            "question_number": n,
            "display_order": n,
            "question_text": "\n".join(q["stem_parts"]).strip(),
            "question_type": "mcq",
            "options": [
                {
                    "label": label,
                    "source_label": f"({label})",
                    "text": otext,
                    "display_order": i + 1,
                }
                for i, (label, otext) in enumerate(q["options"])
            ],
            "correct_option_label": answer_key.get(n),
        }
        if difficulty:
            row["observed_difficulty"] = difficulty
        if n in dropped:
            # Recorded, not silently omitted: the paper should read as the
            # 100-question exam that was actually sat. A dropped item has no
            # correct option, so it can never satisfy the projection's
            # exactly-one-correct-option gate and stays out of practice.
            row["dropped_by_upsc"] = True
        rows.append(row)

    return {"format_version": 2, "questions": rows}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("docx")
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--set-code", required=True, help="Printed series/set, e.g. A or C")
    ap.add_argument("--paper-label", default="GS1", help="source_question_ref prefix (default GS1)")
    ap.add_argument("--answer-key", help="CSV: question_number,correct_option_label")
    ap.add_argument("--dropped", default="", help="Comma-separated question numbers dropped by UPSC")
    ap.add_argument("--expect", type=int, default=100, help="Expected question count (default 100)")
    ap.add_argument("--difficulty", choices=("easy", "medium", "hard"),
                    help="observed_difficulty for every row; the mock projection only "
                         "honours these three values (migration 183)")
    ap.add_argument("-o", "--out", help="Write envelope JSON here")
    ap.add_argument("--report", action="store_true", help="Print a parse summary to stderr")
    args = ap.parse_args(argv)

    questions = _parse_blocks(args.docx)
    errors = validate(questions, args.expect)

    dropped = {int(x) for x in args.dropped.split(",") if x.strip()}
    unknown = sorted(d for d in dropped if d > len(questions) or d < 1)
    if unknown:
        errors.append(f"--dropped names questions outside 1..{len(questions)}: {unknown}")

    answer_key = _load_answer_key(args.answer_key) if args.answer_key else {}
    if answer_key:
        missing = sorted(
            q["number"] for q in questions
            if q["number"] not in answer_key and q["number"] not in dropped
        )
        if missing:
            errors.append(f"answer key is missing non-dropped questions: {missing}")
        keyed_dropped = sorted(dropped & set(answer_key))
        if keyed_dropped:
            errors.append(f"answer key asserts a correct option for dropped questions: {keyed_dropped}")

    if args.report:
        print(f"parsed {len(questions)} questions from {args.docx}", file=sys.stderr)
        print(f"  set {args.set_code}, year {args.year}, dropped {sorted(dropped) or 'none'}", file=sys.stderr)
        print(f"  answer key: {len(answer_key) or 'ABSENT'}", file=sys.stderr)
        for e in errors:
            print(f"  ERROR {e}", file=sys.stderr)

    if errors:
        for e in errors:
            print(f"error: {e}", file=sys.stderr)
        return 1

    envelope = build_envelope(
        questions,
        ref_prefix=args.paper_label,
        answer_key=answer_key,
        dropped=dropped,
        difficulty=args.difficulty,
    )

    if not answer_key:
        print(
            "warning: no --answer-key supplied; correct_option_label is null on every row "
            "and preflight will reject this envelope",
            file=sys.stderr,
        )

    text = json.dumps(envelope, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"wrote {args.out} ({len(envelope['questions'])} questions)", file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
