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

The supplied corpus is retyped/OCR-derived rather than official UPSC files, and no
two years share a layout. Rather than special-casing each, the parser normalises
first and then runs one state machine:

- **Lines, not paragraphs.** Some years put a whole question — stem, statements and
  all four options — in a single paragraph separated by ``<w:br/>``. Paragraphs are
  flattened to lines so those years parse like the rest.
- **Detected question marker.** Years mark questions ``1.``, ``Q.1)`` or
  ``Question 1.``. The style is detected per document by whichever candidate yields
  the longest run of consecutive numbers from 1, so a bare ``1.`` statement inside a
  stem can never be mistaken for a question opener in a ``Question 1.`` paper.
- **Restored list numbering.** Word keeps auto-list markers out of the text layer,
  but options refer to them ("1 and 2 only"). Decimal lists are restored as
  ``1.``/``2.``; lower-letter lists are the options themselves and become a-d.

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

# Question-opener styles seen across the corpus, most specific first so a tie
# resolves to the more distinctive marker.
MARKER_PATTERNS = (
    ("Q.N)", re.compile(r"^\s*Q\.?\s*(\d{1,3})\s*[).:]\s*(.*)$", re.S)),
    # One year prints the opener three ways within the same file — "Question 1.",
    # "Question 5:" and "Question: 6." — so both separators are optional and may
    # appear on either side of the number.
    ("Question N.", re.compile(r"^\s*Question\s*[-.:]?\s*(\d{1,3})\s*[-.:)]?\s*(.*)$", re.S | re.I)),
    ("N.", re.compile(r"^\s*(\d{1,3})\s*\.\s+(.*)$", re.S)),
)

# Options print as "(a) text". UPSC uses lowercase a-d throughout Prelims GS.
OPT = re.compile(r"^\s*\(([a-d])\)\s*(.*)$", re.S)

# The supplied .docx files are retyped/OCR-derived and carry character-level damage
# to option markers: "{b)" for "(b)", "c)" for "(c)", "(C)" for "(c)". Some years
# print "a)" with no opening bracket throughout. This matches a marker with either
# bracket corrupted or absent and any case; _match_option only accepts it when the
# recovered letter is the next one due, so a scrambled marker still fails loudly.
OPT_LOOSE = re.compile(r"^\s*[\(\{\[\|]?\s*([A-Da-d])\s*[\)\}\]]\.?\s+(.*)$", re.S)

OPTION_LABELS = ("a", "b", "c", "d")

# Two options run together on one line with no separating break — "(c) 3 only
# d)1 and 3". The marker must be preceded by whitespace and followed immediately
# by non-space: that is precisely the shape OPT_LOOSE rejects (it requires
# whitespace after the marker), so the two are complementary and a normally
# spaced bracketed letter inside option text — "Item (d) of the schedule" — is
# never mistaken for the next option.
GLUED = {label: re.compile(rf"\s+[\(\{{\[]?\s*{label}\s*[\)\}}\]](?=\S)", re.I)
         for label in OPTION_LABELS}

# Options that name specific statements by index — "1 and 2 only", "2 only",
# "Both 1 and 2". These make the stem's numbering load-bearing: without it the
# reader cannot tell which statement is which, and the question is unanswerable.
INDEX_REF = re.compile(r"\b\d\s*(?:,|and)\s*\d\b|\b[1-9]\s+only\b", re.I)

# Options that merely tally statements — "Only two", "All four". The count is
# taken over the statements as printed, so their numbering is cosmetic and its
# absence does not make the question unanswerable.
COUNT_REF = re.compile(
    r"\bonly one\b|\bonly two\b|\bonly three\b|\ball (?:three|four)\b|\bnone\b", re.I
)

# A statement run sits between a lead-in and the interrogative that closes the
# stem. Used only by --number-unmarked-statements; see _number_unmarked().
LEAD_IN = re.compile(r"consider the following|following (?:statements|pairs)|statements\s*:\s*$", re.I)
CLOSING = re.compile(r"^\s*(?:which|how many|select the correct|the correct answer)", re.I)


# ── docx reading ─────────────────────────────────────────────────────────────


def _para_text(p: ET.Element) -> str:
    """Concatenate a paragraph's runs, honouring tabs and explicit breaks."""
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


def _num_formats(z: zipfile.ZipFile) -> dict[str, str]:
    """Map numbering instance id -> level-0 numFmt (``decimal``, ``lowerLetter``...).

    Absent or unreadable numbering.xml yields an empty map; callers then treat a
    numbered paragraph as decimal, which is the dominant case in this corpus.
    """
    if "word/numbering.xml" not in z.namelist():
        return {}
    try:
        root = ET.fromstring(z.read("word/numbering.xml"))
    except ET.ParseError:
        return {}
    abstracts: dict[str, str] = {}
    for a in root.findall(W + "abstractNum"):
        lvl = a.find(W + "lvl")
        if lvl is None:
            continue
        fmt = lvl.find(W + "numFmt")
        if fmt is not None:
            abstracts[a.get(W + "abstractNumId")] = fmt.get(W + "val")
    out: dict[str, str] = {}
    for num in root.findall(W + "num"):
        ref = num.find(W + "abstractNumId")
        if ref is not None and ref.get(W + "val") in abstracts:
            out[num.get(W + "numId")] = abstracts[ref.get(W + "val")]
    return out


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


class Line:
    """One logical line: text plus the list identity it inherited, if any."""

    __slots__ = ("text", "num_id", "num_fmt", "table")

    def __init__(self, text: str, num_id: str | None = None,
                 num_fmt: str | None = None, table: bool = False) -> None:
        self.text = text
        self.num_id = num_id
        self.num_fmt = num_fmt
        self.table = table


def _read_lines(path: str) -> list[Line]:
    """Flatten the document body to lines in printed order.

    A paragraph holding several lines is split on its explicit breaks; only the
    first line inherits the paragraph's list identity, since Word applies the
    marker once per paragraph however many breaks follow.
    """
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
        fmts = _num_formats(z)
    body = root.find(W + "body")
    if body is None:
        raise ValueError(f"{path}: no <w:body>")

    lines: list[Line] = []
    for child in body:
        if child.tag == W + "p":
            num_id = _num_id(child)
            # An unresolvable numId is treated as decimal: that is the dominant
            # list in this corpus and the shape the option markers refer to.
            fmt = fmts.get(num_id, "decimal") if num_id is not None else None
            for i, part in enumerate(_para_text(child).split("\n")):
                if part.strip():
                    lines.append(Line(part, num_id if i == 0 else None,
                                      fmt if i == 0 else None))
        elif child.tag == W + "tbl":
            for row in _table_lines(child):
                lines.append(Line(row, table=True))
    return lines


# ── parsing ──────────────────────────────────────────────────────────────────


def detect_marker(lines: list[Line]) -> tuple[str, re.Pattern]:
    """Pick the question-opener style this document actually uses.

    Each candidate is scored by how far a strictly consecutive scan from 1 gets.
    The winner is the style that segments the paper, so a ``Question 1.`` paper
    whose stems also contain bare ``1.`` statement lines cannot be mis-segmented.
    """
    best = (0, MARKER_PATTERNS[0][0], MARKER_PATTERNS[0][1])
    for name, pattern in MARKER_PATTERNS:
        expected = 1
        for line in lines:
            m = pattern.match(line.text.strip())
            if m and int(m.group(1)) == expected:
                expected += 1
        run = expected - 1
        if run > best[0]:
            best = (run, name, pattern)
    return best[1], best[2]


def _match_option(text: str, due: str | None) -> tuple[str, str] | None:
    """Match one printed option line, repairing a damaged marker when unambiguous.

    A well-formed "(b)" is always taken. A damaged or bracket-less marker is
    accepted only when the letter it recovers is exactly ``due`` — so "{b)" in the
    b position is repaired, while a marker reading "d" where "b" is due is left
    unmatched and surfaces as a validation error instead of being silently
    reordered, which would be a guess about which option is the answer.
    """
    m = OPT.match(text)
    if m:
        # "(b). Two" — the stray period belongs to the damaged marker, not to the
        # option text. No option legitimately opens with one.
        return m.group(1), m.group(2).strip().lstrip(".:").strip()
    loose = OPT_LOOSE.match(text)
    if loose and due is not None and loose.group(1).lower() == due:
        return due, loose.group(2).strip().lstrip(".:").strip()
    return None


def _split_glued(cur: dict, due_label) -> None:
    """Peel options that were printed run-together onto one line.

    Splits only where the embedded marker is the label actually due next, so a
    stray bracket inside an option's text cannot manufacture an extra option.
    """
    while True:
        nxt = due_label()
        if nxt is None:
            return
        label, body = cur["options"][-1]
        m = GLUED[nxt].search(body)
        if not m or not body[m.end():].strip() or not body[:m.start()].strip():
            return
        cur["options"][-1] = (label, body[:m.start()].strip())
        cur["options"].append((nxt, body[m.end():].strip()))


def _parse_lines(lines: list[Line], pattern: re.Pattern) -> list[dict]:
    """Segment the flattened document into questions.

    A new question starts only where the marker's number is exactly ``expected``,
    so a repeated or skipped number fails loudly in ``validate`` rather than
    silently mis-segmenting.
    """
    questions: list[dict] = []
    cur: dict | None = None
    expected = 1
    counters: dict[str, int] = {}
    active_num_id: str | None = None

    def due_label() -> str | None:
        if cur is None:
            return None
        if not cur["options"]:
            return OPTION_LABELS[0]
        i = OPTION_LABELS.index(cur["options"][-1][0])
        return OPTION_LABELS[i + 1] if i + 1 < len(OPTION_LABELS) else None

    for line in lines:
        text = line.text.strip()
        if not text:
            continue

        m = pattern.match(text)
        if m and int(m.group(1)) == expected:
            rest = m.group(2).strip()
            cur = {
                "number": expected,
                "stem_parts": [rest] if rest else [],
                "options": [],
                "has_table": False,
            }
            questions.append(cur)
            expected += 1
            counters.clear()
            active_num_id = None
            continue

        if cur is None:
            # Front matter before question 1 (instructions, headers).
            continue

        if line.table:
            cur["stem_parts"].append(text)
            cur["has_table"] = True
            active_num_id = None
            continue

        due = due_label()

        # A lower-letter auto-list IS the option list: Word holds "a)" in
        # numbering.xml, so the text layer carries only the option body.
        if line.num_fmt == "lowerLetter" and due is not None:
            if line.num_id != active_num_id:
                active_num_id = line.num_id
                counters.setdefault(line.num_id, 0)
            counters[line.num_id] += 1
            idx = counters[line.num_id] - 1
            if idx < len(OPTION_LABELS):
                cur["options"].append((OPTION_LABELS[idx], text))
            continue

        opt = _match_option(text, due)
        if opt:
            cur["options"].append(opt)
            _split_glued(cur, due_label)
            active_num_id = None
            continue

        if cur["options"]:
            # Text after the options began — a trailing note attached to the last
            # option rather than a new stem line. It may itself be the next option
            # printed without a separating space ("d)1 and 3"), which the option
            # matchers reject, so re-check for a glued marker after appending.
            label, prev = cur["options"][-1]
            cur["options"][-1] = (label, (prev + " " + text).strip())
            _split_glued(cur, due_label)
            continue

        if line.num_id is not None:
            # Word strips the visible marker from auto-numbered list items, but the
            # options reference them ("1, 2 and 3"), so restore it. Each question's
            # list is its own numbering instance starting at 1, so counting per
            # instance is exact — no numbering.xml restart semantics needed.
            if line.num_id != active_num_id:
                active_num_id = line.num_id
                counters.setdefault(line.num_id, 0)
            counters[line.num_id] += 1
            cur["stem_parts"].append(f"{counters[line.num_id]}. {text}")
        else:
            cur["stem_parts"].append(text)
            active_num_id = None

    return questions


def _parse_blocks(path: str) -> list[dict]:
    """Parse a paper, detecting its question-marker style first."""
    lines = _read_lines(path)
    _, pattern = detect_marker(lines)
    return _parse_lines(lines, pattern)


# ── validation ───────────────────────────────────────────────────────────────


def _number_unmarked(q: dict) -> bool:
    """Restore ``1.``/``2.`` on a statement run whose source lost its list numbering.

    Opt-in (``--number-unmarked-statements``) because it infers structure the file
    does not state. What it infers is only *print order*: the statements are
    already in the stem in the order they were printed, so numbering them 1..N by
    position restores the marker Word dropped rather than inventing an order. It
    is still an inference — a stem line misread as a statement would shift every
    number after it — so it runs only when the shape is unambiguous: a lead-in, a
    run of two or more lines, then the closing interrogative, with nothing already
    numbered.

    Returns True when it changed the stem.
    """
    parts = q["stem_parts"]
    if any(re.match(r"^\d+\.\s", line) for line in parts):
        return False
    lead = next((i for i, line in enumerate(parts) if LEAD_IN.search(line)), None)
    if lead is None:
        return False
    close = next((i for i in range(lead + 1, len(parts)) if CLOSING.match(parts[i])), None)
    if close is None or close - lead < 3:
        return False
    for offset, i in enumerate(range(lead + 1, close), start=1):
        parts[i] = f"{offset}. {parts[i]}"
    return True


def _sort_complete_options(q: dict) -> bool:
    """Put a full but out-of-sequence option set back in a-b-c-d order.

    Some source lines print the four options shuffled — a, c, b, d — while every
    label is present exactly once. Ordering by label then loses nothing and infers
    nothing: each option keeps the text it was printed with, and the label is what
    ties an answer key to an option. A set with a missing or duplicated label is
    left alone, so it still fails validation rather than being quietly patched.
    """
    labels = [label for label, _ in q["options"]]
    if sorted(labels) != list(OPTION_LABELS) or labels == list(OPTION_LABELS):
        return False
    q["options"].sort(key=lambda pair: OPTION_LABELS.index(pair[0]))
    return True


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
        # unanswerable. Options that only tally statements ("Only two") are exempt:
        # the count runs over the statements as printed, so their numbering is
        # cosmetic. Three stem shapes legitimately satisfy an index reference
        # without a numbered list: a restored "1." list, a table ("how many pairs
        # are correctly matched"), and UPSC's "Statement-I / Statement-II" form.
        stem = "\n".join(q["stem_parts"])
        anchored = (
            re.search(r"^\d+\.\s", stem, re.M)
            or q.get("has_table")
            or re.search(r"\bStatement[-\s]*(?:I+|[1-9])\b", stem)
        )
        if any(INDEX_REF.search(t) for _, t in q["options"]) and not anchored:
            errors.append(
                f"Q{n}: options name statements by index but the stem carries no numbering "
                f"(source document lost its list numbering)"
            )

    numbers = [q["number"] for q in questions]
    if numbers != list(range(1, len(numbers) + 1)):
        errors.append("question numbers are not a contiguous 1..N run")

    return errors


def _load_answer_key(path: str) -> dict[int, str]:
    """Read a two-column ``question_number,correct_option_label`` CSV.

    Deliberately a separate operator-supplied file: the official UPSC key PDFs are
    scans, and a key transcribed by anything other than a human reading the
    official document is not a key (CLAUDE.md -> determinism over heuristics).
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

    ``question_number`` and ``display_order`` both carry the printed number: each
    is uniquely indexed per paper (migration 223), and keeping them equal means
    the printed order survives a re-import.
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
    ap.add_argument("--number-unmarked-statements", action="store_true",
                    help="Restore 1./2. on statement runs whose source lost Word's list "
                         "numbering, by printed order. Reports which questions were "
                         "changed so they can be eye-checked before verification.")
    ap.add_argument("--difficulty", choices=("easy", "medium", "hard"),
                    help="observed_difficulty for every row; the mock projection only "
                         "honours these three values (migration 183)")
    ap.add_argument("-o", "--out", help="Write envelope JSON here")
    ap.add_argument("--report", action="store_true", help="Print a parse summary to stderr")
    args = ap.parse_args(argv)

    lines = _read_lines(args.docx)
    marker_name, pattern = detect_marker(lines)
    questions = _parse_lines(lines, pattern)

    reordered = [q["number"] for q in questions if _sort_complete_options(q)]

    renumbered: list[int] = []
    if args.number_unmarked_statements:
        for q in questions:
            if any(INDEX_REF.search(t) for _, t in q["options"]) and _number_unmarked(q):
                renumbered.append(q["number"])

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
        print(f"  marker style {marker_name!r}, set {args.set_code}, year {args.year}, "
              f"dropped {sorted(dropped) or 'none'}", file=sys.stderr)
        print(f"  answer key: {len(answer_key) or 'ABSENT'}", file=sys.stderr)
        if reordered:
            print(f"  option order normalised on {len(reordered)} questions: {reordered}",
                  file=sys.stderr)
        if renumbered:
            print(f"  statement numbering restored by printed order on "
                  f"{len(renumbered)} questions: {renumbered}", file=sys.stderr)
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
