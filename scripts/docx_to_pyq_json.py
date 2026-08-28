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
  ``1.``/``2.``; lower-letter lists are the options themselves and become a-d
  (a-e on the papers that print a fifth option).

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

# Options print as "(a) text". UPSC uses lowercase labels throughout Prelims GS.
OPT = re.compile(r"^\s*\(([a-e])\)\s*(.*)$", re.S)

# The supplied .docx files are retyped/OCR-derived and carry character-level damage
# to option markers: "{b)" for "(b)", "c)" for "(c)", "(C)" for "(c)". Some years
# print "a)" with no opening bracket throughout. This matches a marker with either
# bracket corrupted or absent and any case; _match_option only accepts it when the
# recovered letter is the next one due, so a scrambled marker still fails loudly.
OPT_LOOSE = re.compile(r"^\s*[\(\{\[\|]?\s*([A-Ea-e])\s*[\)\}\]]\.?\s+(.*)$", re.S)

# SEBI/coaching-format papers print "A. Nariman Point, Mumbai" — an uppercase
# letter, a period, and NO bracket at all. Both patterns above require a
# closing bracket, so on those files zero options parse and every question
# fails validation with "options are none". This is the bracket-less form.
# The trailing ``\s+`` is required: it is what separates a marker from the
# "A.Nariman" run-together shape, which is damage rather than a marker.
OPT_DOT = re.compile(r"^\s*([A-Ea-e])\s*[.)]\s+(.*)$", re.S)

# "A. K. Sen", "B. R. Ambedkar" — an initials run in a stem has exactly the
# shape of a dot marker. What gives it away is the SECOND initial: no option
# body legitimately opens with another single letter and a period. Checked
# against the text following a candidate marker, never against the marker.
INITIALS_RUN = re.compile(r"^[A-Za-z]\s*\.\s")

# A bare "Options:" / "Options :" label line introduces the option block in the
# coaching format (182 occurrences across the corpus). It is a label, not
# content: appending it to the stem would change normalized_question_hash and
# render in the aspirant UI. Dropping a line that carries no content can never
# lose information, so this applies to every style.
OPTIONS_LABEL = re.compile(r"^\s*Options?\s*:\s*$", re.I)

# The label alphabet, in printed order. ``due_label`` walks it, so extending it
# is what lets a fifth option be recognised at all: before "e" was here, a
# printed "(e)" matched no marker and was appended to option (d)'s text.
OPTION_LABELS = ("a", "b", "c", "d", "e")

# A question carries four options or five — nothing else is a paper, it is
# damage. Both sets are prefixes of OPTION_LABELS, so a partial set like
# a/b/c/e is not merely short, it is out of sequence, and is rejected by name.
VALID_LABEL_SETS = (list(OPTION_LABELS[:4]), list(OPTION_LABELS[:5]))
_EXPECTED_LABELS = " or ".join(str(labels).replace(" ", "") for labels in VALID_LABEL_SETS)


def _is_complete_label_set(labels) -> bool:
    """True only for a full a-d or a-e run, in order."""
    return list(labels) in VALID_LABEL_SETS


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
#
# Matched against the WHOLE option, not searched inside it. Searching for a
# digit pair was the bug: a fill-in-the-blanks option "2/3,1" contains the
# substring "3,1" and read as an index list, so SEBI-GA-2022-P1-CA Q1 was
# rejected for numbering it never needed. An index reference is a shape, not
# the presence of digits, so the option must consist of nothing else.
#
# A statement index is a single digit 1-9 (papers do not number past that), and
# it must carry index syntax — a keyword, a multi-index list, or "only". A bare
# "1" is deliberately NOT an index reference: on a quantitative paper the whole
# option set is bare numbers, and those are answers, not statement pointers.
_IDX = r"[1-9]"
_IDX_SEP = r"\s*(?:,|and|nor|&)\s*"
INDEX_OPTION = re.compile(
    rf"^\s*(?:"
    rf"(?:only|both|neither|either)\s+{_IDX}(?:{_IDX_SEP}{_IDX})*"   # "Only 1", "Both 1 and 2"
    rf"|{_IDX}(?:{_IDX_SEP}{_IDX})+(?:\s+only)?"                     # "1 and 2 only", "1, 2 and 3"
    rf"|{_IDX}\s+only"                                              # "2 only"
    rf")\s*\.?\s*$",
    re.I,
)

# The wordless members of the same family. On their own they say nothing about
# numbering — "None of the above" is at home on any question — so they only
# count alongside a real index reference.
INDEX_SIBLING = re.compile(
    r"^\s*(?:none|all|any)\s+of\s+(?:the\s+)?(?:above|these)\s*\.?\s*$", re.I
)


def _names_statement_indices(options) -> bool:
    """True when this question's options point at numbered statements.

    Requires at least one genuine index reference, and at least two members of
    the family in total. A real statement question always offers several ("1
    only", "2 only", "Both 1 and 2", "Neither 1 nor 2"); a single stray match is
    far more likely to be a value that happens to read like an index.
    """
    numeric = sum(1 for _, text in options if INDEX_OPTION.match(text))
    siblings = sum(1 for _, text in options if INDEX_SIBLING.match(text))
    return numeric >= 1 and numeric + siblings >= 2


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


def _raw_option_letter(text: str, style: str) -> str | None:
    """The label a line would carry under ``style``, ignoring what is due.

    Used only for scoring a style across a document. ``dot`` applies the
    initials guard here too, so a paper full of "A. K. Sen" cannot inflate the
    dot score and win a document that is really bracket-style.
    """
    if style == "dot":
        m = OPT_DOT.match(text)
        if m and not INITIALS_RUN.match(m.group(2)):
            return m.group(1).lower()
        return None
    m = OPT.match(text) or OPT_LOOSE.match(text)
    return m.group(1).lower() if m else None


def detect_option_style(lines: list[Line]) -> str:
    """Pick the option-marker style this document actually uses.

    Mirrors ``detect_marker``: score each candidate by how much of the paper it
    segments, and let the winner run alone, rather than trying every pattern on
    every line. That is what keeps the change additive — a UPSC bracket paper
    scores far higher on ``bracket`` than on ``dot``, so its stems are never
    exposed to the bracket-less pattern and cannot drift.

    A style scores one point per line that continues an a-b-c-d(-e) run, with a
    fresh "a" always allowed to start the next question's block. Out-of-sequence
    letters score nothing, so prose is not mistaken for a marker.
    """
    best = (0, "bracket")
    for style in ("bracket", "dot"):
        score = 0
        i = 0
        for line in lines:
            text = line.text.strip()
            if not text or OPTIONS_LABEL.match(text):
                continue
            letter = _raw_option_letter(text, style)
            if letter is None:
                continue
            if letter == OPTION_LABELS[i]:
                score += 1
                i = (i + 1) % len(OPTION_LABELS)
            elif letter == OPTION_LABELS[0]:
                # A four-option paper restarts at "a" without ever reaching "e".
                score += 1
                i = 1
        if score > best[0]:
            best = (score, style)
    return best[1]


def _match_option(text: str, due: str | None, style: str = "bracket") -> tuple[str, str] | None:
    """Match one printed option line, repairing a damaged marker when unambiguous.

    A well-formed "(b)" is always taken. A damaged or bracket-less marker is
    accepted only when the letter it recovers is exactly ``due`` — so "{b)" in the
    b position is repaired, while a marker reading "d" where "b" is due is left
    unmatched and surfaces as a validation error instead of being silently
    reordered, which would be a guess about which option is the answer.

    ``style`` selects the document's own marker family (see ``detect_option_style``)
    and the two never mix. Under ``dot`` there is no bracket to signal that a
    letter was meant as a marker, so EVERY dot marker is gated on ``due`` — the
    same treatment a damaged bracket marker already gets. That single rule is
    what keeps "B. Ambedkar" in a stem out of the option list: options have not
    started there, so "a" is due and "b" is refused. The initials guard then
    covers the one case ``due`` cannot, an "A. K. Sen" sitting where "a" is due.
    """
    if style == "dot":
        m = OPT_DOT.match(text)
        if m and due is not None and m.group(1).lower() == due:
            body = m.group(2)
            if INITIALS_RUN.match(body):
                return None
            return due, body.strip().lstrip(".:").strip()
        return None

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


def _parse_lines(lines: list[Line], pattern: re.Pattern,
                 option_style: str = "bracket") -> list[dict]:
    """Segment the flattened document into questions.

    A new question starts only where the marker's number is exactly ``expected``,
    so a repeated or skipped number fails loudly in ``validate`` rather than
    silently mis-segmenting.

    ``option_style`` defaults to ``bracket``, so every existing caller and the
    whole UPSC corpus take exactly the path they took before this parameter
    existed.
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

        # A bare "Options:" label introduces the block and carries no content.
        # Dropped before anything else so it can reach neither the stem nor the
        # option list.
        if OPTIONS_LABEL.match(text):
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

        opt = _match_option(text, due, option_style)
        if opt:
            cur["options"].append(opt)
            if option_style == "bracket":
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
            if option_style == "bracket":
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
    """Parse a paper, detecting its question-marker and option-marker styles first."""
    lines = _read_lines(path)
    _, pattern = detect_marker(lines)
    return _parse_lines(lines, pattern, detect_option_style(lines))


# ── validation ───────────────────────────────────────────────────────────────


def _statement_run(q: dict) -> tuple[int, int] | None:
    """Bounds of an unnumbered statement run in the stem, or None if there is none.

    Read-only, and deliberately so: ``validate`` needs to know whether a statement
    run exists in order to describe the defect accurately, and it must not renumber
    the stem as a side effect of reporting on it. ``_number_unmarked`` applies the
    numbering once these same bounds come back.
    """
    parts = q["stem_parts"]
    if any(re.match(r"^\d+\.\s", line) for line in parts):
        return None
    lead = next((i for i, line in enumerate(parts) if LEAD_IN.search(line)), None)
    if lead is None:
        return None
    close = next((i for i in range(lead + 1, len(parts)) if CLOSING.match(parts[i])), None)
    if close is None or close - lead < 3:
        return None
    return lead, close


def _index_reference_defect(q: dict) -> str:
    """Describe the defect behind an index reference with no numbering to match.

    Names the offending option, offers the likelier of the two readings, and says
    what the operator can actually do — which is never a ``corrections`` entry:
    ``relabel`` only reorders labels, ``add_options`` refuses a label that already
    parsed, and ``options_from_stem`` refuses a question that already has options.
    The remedy is the source document or exclusion, and saying so up front saves
    the operator discovering it three refusals later.
    """
    indexed = [(label, text) for label, text in q["options"] if INDEX_OPTION.match(text)]
    plain = [text for label, text in q["options"]
             if not INDEX_OPTION.match(text) and not INDEX_SIBLING.match(text)]

    label, text = indexed[0]
    more = f" (and {len(indexed) - 1} more)" if len(indexed) > 1 else ""
    verb = "refer" if len(indexed) > 1 else "refers"
    parts = [f"option ({label}) {text!r}{more} {verb} to items by number, "
             f"but the stem carries no numbered list."]

    if len(plain) >= 2:
        shown = ", ".join(repr(t) for t in plain[:3])
        parts.append(
            f"The other options are plain items ({shown}), so the numerals most likely "
            f"point at the options themselves rather than at statements — a paper that "
            f"printed numbered options and was retyped with letters."
        )
    else:
        parts.append("The source document most likely lost its list numbering.")

    if _statement_run(q) is None:
        # No run to restore, so every automated remedy is out. Say so, rather than
        # let the operator find out through three separate corrections refusals.
        parts.append("--number-unmarked-statements cannot help: the stem has no "
                     "statement run to number.")
        parts.append("No corrections operation repairs this either — relabel only "
                     "reorders labels, add_options refuses a label that already "
                     "parsed, options_from_stem refuses a question that already has "
                     "options. Fix the source document or exclude the question.")
    else:
        parts.append("--number-unmarked-statements restores the run by printed order.")
    return " ".join(parts)


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
    bounds = _statement_run(q)
    if bounds is None:
        return False
    lead, close = bounds
    parts = q["stem_parts"]
    for offset, i in enumerate(range(lead + 1, close), start=1):
        parts[i] = f"{offset}. {parts[i]}"
    return True


def _sort_complete_options(q: dict) -> bool:
    """Put a full but out-of-sequence option set back in alphabetical order.

    Some source lines print the options shuffled — a, c, b, d — while every label
    is present exactly once. Ordering by label then loses nothing and infers
    nothing: each option keeps the text it was printed with, and the label is what
    ties an answer key to an option. A set with a missing or duplicated label is
    left alone, so it still fails validation rather than being quietly patched —
    which is also why a five-option set is reordered only when it is complete.
    """
    labels = [label for label, _ in q["options"]]
    ordered = sorted(labels)
    if not _is_complete_label_set(ordered) or labels == ordered:
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
        if not _is_complete_label_set(labels):
            errors.append(
                f"Q{n}: options are {labels or 'none'}, expected {_EXPECTED_LABELS}"
            )
        for label, otext in q["options"]:
            if not otext.strip():
                errors.append(f"Q{n}: option ({label}) is empty")

        # A stem whose options say "1 and 2 only" must actually carry numbered
        # statements. Options that only tally statements ("Only two") are exempt:
        # the count runs over the statements as printed, so their numbering is
        # cosmetic. Three stem shapes legitimately satisfy an index reference
        # without a numbered list: a restored "1." list, a table ("how many pairs
        # are correctly matched"), and UPSC's "Statement-I / Statement-II" form.
        #
        # Two different defects reach this branch, and the operator needs to know
        # which one they are looking at:
        #
        #   lost numbering    the stem printed a numbered list and the source
        #                     dropped Word's numbering, leaving the statements
        #                     present but unmarked. Every option is an index
        #                     reference ("1 only" / "Both 1 and 2"), and
        #                     --number-unmarked-statements can restore the run.
        #
        #   renumbered options  the paper printed its answer choices as a numbered
        #                     list, was retyped with letters, and an option still refers
        #                     back numerically — IFSCA-GA-2023-P2P2-FIN Q5 offers
        #                     "A. RBI / B. MMTC / C. Banks / D. 1 and 3", where "1
        #                     and 3" means options (a) and (c). The other options
        #                     are plain items and there is no statement run at all,
        #                     so the flag is powerless and numbering the stem would
        #                     mean inventing statements that were never printed.
        #
        # Both stay errors — "1 and 3" read against lettered options is ambiguous
        # to an aspirant, and which reading is right is not deterministically
        # recoverable. Only the diagnosis differs.
        stem = "\n".join(q["stem_parts"])
        anchored = (
            re.search(r"^\d+\.\s", stem, re.M)
            or q.get("has_table")
            or re.search(r"\bStatement[-\s]*(?:I+|[1-9])\b", stem)
        )
        if _names_statement_indices(q["options"]) and not anchored:
            errors.append(f"Q{n}: {_index_reference_defect(q)}")

    numbers = [q["number"] for q in questions]
    if numbers != list(range(1, len(numbers) + 1)):
        errors.append("question numbers are not a contiguous 1..N run")

    return errors


def apply_corrections(questions: list[dict], corrections: dict) -> list[str]:
    """Apply operator-supplied repairs for source-document damage.

    A correction only changes how options were *formatted* — their labels, or
    whether a run was printed as a list instead of as options. It never states
    which option is correct: that stays with the answer key, and a correction that
    displaced the keyed option would show up as an unresolved key at build time.

    Two operations, both purely positional:

    ``relabel``  assign these labels to the parsed options in printed order, for a
                 paper that printed them out of sequence or duplicated a letter.
    ``options_from_stem``  take the last N numbered lines off the stem and make
                 them the first N labels, for a paper that formatted its options
                 as a decimal list so they parsed as statements.
    ``add_options``  supply the text of an option the source file dropped
                 entirely. This is the only operation that introduces text rather
                 than rearranging what was parsed, so it is deliberately the
                 narrowest: the label must be absent, and the result must be a
                 complete a-d or a-e set.

    Returns the notes describing what was applied, for the report.
    """
    by_number = {q["number"]: q for q in questions}
    applied: list[str] = []
    for raw_num, spec in sorted(corrections.items()):
        if raw_num.startswith("_"):
            continue
        num = int(raw_num)
        q = by_number.get(num)
        if q is None:
            raise ValueError(f"correction Q{num}: no such question in this paper")

        if "relabel" in spec:
            labels = spec["relabel"]
            if len(labels) != len(q["options"]):
                raise ValueError(
                    f"correction Q{num}: relabel lists {len(labels)} labels but the "
                    f"question parsed {len(q['options'])} options"
                )
            q["options"] = [(label, text) for label, (_, text) in zip(labels, q["options"])]
            q["options"].sort(key=lambda pair: OPTION_LABELS.index(pair[0]))
            applied.append(f"Q{num}: relabelled options {'/'.join(labels)}")

        if "add_options" in spec:
            existing = {label for label, _ in q["options"]}
            for label, text in sorted(spec["add_options"].items()):
                if label in existing:
                    raise ValueError(
                        f"correction Q{num}: add_options would overwrite the parsed "
                        f"option ({label})"
                    )
                q["options"].append((label, text))
            q["options"].sort(key=lambda pair: OPTION_LABELS.index(pair[0]))
            if not _is_complete_label_set([label for label, _ in q["options"]]):
                raise ValueError(
                    f"correction Q{num}: add_options leaves the option set "
                    f"{[label for label, _ in q['options']]}, not {_EXPECTED_LABELS}"
                )
            applied.append(
                f"Q{num}: supplied missing option(s) "
                f"{'/'.join(sorted(spec['add_options']))}"
            )

        if "options_from_stem" in spec:
            count = int(spec["options_from_stem"])
            if q["options"]:
                raise ValueError(
                    f"correction Q{num}: options_from_stem but the question already "
                    f"parsed {len(q['options'])} options"
                )
            tail = q["stem_parts"][-count:]
            if len(tail) != count or not all(re.match(r"^\d+\.\s", line) for line in tail):
                raise ValueError(
                    f"correction Q{num}: the last {count} stem lines are not a numbered run"
                )
            q["stem_parts"] = q["stem_parts"][:-count]
            q["options"] = [
                (OPTION_LABELS[i], re.sub(r"^\d+\.\s*", "", line))
                for i, line in enumerate(tail)
            ]
            applied.append(f"Q{num}: promoted {count} stem lines to options")

    return applied


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
                raise ValueError(
                    f"answer key Q{num}: label {label!r} is not one of "
                    f"{'/'.join(OPTION_LABELS)}"
                )
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
    ap.add_argument("--corrections", help="JSON of operator repairs for source-document "
                                          "damage; see docs/reference/corrections/")
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
    option_style = detect_option_style(lines)
    questions = _parse_lines(lines, pattern, option_style)

    applied: list[str] = []
    if args.corrections:
        with open(args.corrections, encoding="utf-8") as fh:
            applied = apply_corrections(questions, json.load(fh))

    reordered = [q["number"] for q in questions if _sort_complete_options(q)]

    renumbered: list[int] = []
    if args.number_unmarked_statements:
        for q in questions:
            if _names_statement_indices(q["options"]) and _number_unmarked(q):
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
        print(f"  marker style {marker_name!r}, option style {option_style!r}, "
              f"set {args.set_code}, year {args.year}, "
              f"dropped {sorted(dropped) or 'none'}", file=sys.stderr)
        print(f"  answer key: {len(answer_key) or 'ABSENT'}", file=sys.stderr)
        for line in applied:
            print(f"  correction applied — {line}", file=sys.stderr)
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
