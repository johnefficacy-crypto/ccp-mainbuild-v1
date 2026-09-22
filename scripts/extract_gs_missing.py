#!/usr/bin/env python3
r"""Extract UPSC CSE Mains GS questions that the corpus is missing, for review.

P1 of the GS gap repair. OFFLINE: no database connection, no network, no
writes outside ``workbench/audit/gs_inserts/``. Nothing here decides that a
question goes into the corpus - it stages what the official papers print and
what the DB snapshot lacks, and a human approves rows in the review CSV.
``scripts/load_gs_inserts.py`` loads only approved rows.

WHAT IS EXTRACTED
-----------------
* 2026 GS1-GS4 + Essay: every question (no 2026 row exists in the DB).
* 2013-2023: only questions whose text is ABSENT from the DB snapshot for the
  same year. The comparison is against the whole year, not one paper, so a
  question the split filed under a different paper still counts as present.

Sources are the official-paper OCR under ``workbench/audit/ocr_cache/``
(``<year>_GS<n>.txt`` and ``phase3_raw/QP-CSM-*.txt``). 2015 GS4, all of 2024
and 2025, and every Essay paper except 2026 have NO official text in the repo,
so they cannot be extracted here and are reported as ``no_source``.

HOW A QUESTION IS FOUND (determinism over heuristics)
-----------------------------------------------------
The papers are bilingual. OCR of the Hindi half comes out as Latin-script
garble, so every line is classified by how much of it is English vocabulary
(the vocabulary is the DB snapshot's own English text plus a fixed base list).
Only English lines are kept - the Hindi half is never extracted.

A paper whose questions carry a printed word limit ("(Answer in 150 words)")
is read in ANCHORED mode: each anchor closes a question, and the question is
the unbroken run of English lines above it. Every other paper is read in
UNANCHORED mode (runs of English lines) and every row it yields is flagged
low-confidence, because nothing printed says where a question ends.

The printed count ("There are TWENTY questions") is the check on the result.
Sub-parts - (a)/(b)/(c) printed as separate questions with their own marks -
are numbered from the label column: ``(a)`` opens the next official number.
Case studies whose parts share one word limit stay one question.

Marks are taken only where printed: after the anchor on the same line, or from
the page's marks column when that column has exactly one value per question on
the page. Otherwise marks are left empty and flagged ``marks_unread`` - they
are never inferred from the word limit.

DEDUPE AND ROUTING
------------------
Text is compared to the snapshot's English (Hindi and mojibake tokens are
dropped from DB text first). Score = max(sequence ratio, content-word Dice,
content-word containment for questions of 8+ content words). Containment
exists because the DB often holds a two-part question as one row, so a single
official sub-part is a fragment of it.

    score >= 0.85        present   - counted, not staged
    0.60 <= score < 0.85 near      - near_matches.csv, NEVER loadable
    score < 0.60         insert    - staged + review.csv row

OUTPUTS (``workbench/audit/gs_inserts/``)
------------------------------------------
* ``<year>_<paper>.json``  staged questions (insert route) with provenance
* ``review.csv``          one row per staged question: approved Y/N, edited_*
* ``near_matches.csv``    0.60-0.85 matches, for a human to look at
* ``summary.md``          counts per year/paper

Re-running is safe: ``review.csv`` is merged, not overwritten - a row a human
has already filled in keeps its approved/edited columns.

    python scripts/extract_gs_missing.py
    python scripts/extract_gs_missing.py --year 2026
    python scripts/extract_gs_missing.py --db-snapshot fresh_export.json

A fresh snapshot is a JSON list (or ``{"items": [...]}``) of question rows
carrying at least ``id``, ``question_text`` and ``year`` (or a filename
``pyq_<year>_mains_questions.json``), e.g. from::

    select q.id, q.question_text, q.question_number, p.year, p.paper_code
      from public.pyq_questions q join public.pyq_papers p on p.id = q.pyq_paper_id
     where p.exam_id = '5466e62f-7382-4a38-ba96-2fe5fbfeaba2'
       and p.exam_phase_id = '626ec667-4bbf-4420-8715-48c5b83e0d11';
"""
from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
OCR_DIR = ROOT / "workbench" / "audit" / "ocr_cache"
OUT_DIR = ROOT / "workbench" / "audit" / "gs_inserts"
SNAPSHOT_GLOB = "pyq_*_mains_questions.json"

EXAM_ID = "5466e62f-7382-4a38-ba96-2fe5fbfeaba2"
EXAM_PHASE_ID = "626ec667-4bbf-4420-8715-48c5b83e0d11"

ESSAY = "ESSAY"
PAPERS = ("GS1", "GS2", "GS3", "GS4", ESSAY)
#: The only year with no DB rows at all: every question is staged.
FULL_YEAR = 2026

PRESENT_CUT = 0.85
NEAR_CUT = 0.60
#: Containment is only trusted on questions with this many content words; a
#: short question is contained in too many long ones by chance.
CONTAINMENT_MIN_WORDS = 8

#: A line is English when at least this share of its words is vocabulary.
ENGLISH_MIN_RATIO = 0.6
#: A line between this and ENGLISH_MIN_RATIO is WEAK English: it joins a
#: question only as a continuation of a line that is already English, and is
#: always flagged. Hindi-half garble scores 0.0-0.4 on the real papers.
WEAK_MIN_RATIO = 0.45
#: An English line below this share carries an ``unknown_words`` flag.
CLEAN_MIN_RATIO = 0.75
#: Suffixes stripped when a word is not in the vocabulary as printed.
_SUFFIXES = ("ing", "ed", "es", "s", "ly", "d")

ROUTE_PRESENT = "present"
ROUTE_NEAR = "near_match"
ROUTE_INSERT = "insert"

EXTRACTOR_VERSION = "gs-missing-extract-v1"

REVIEW_FIELDS = [
    "paper_code", "content_hash", "year", "paper", "official_number", "sub_part",
    "section", "marks", "word_limit", "low_confidence", "flags", "best_db_score",
    "text", "approved", "edited_text", "edited_marks", "reviewer_note",
]
#: Columns a human fills in. A re-run never overwrites them.
HUMAN_FIELDS = ("approved", "edited_text", "edited_marks", "reviewer_note")

NEAR_FIELDS = [
    "paper_code", "content_hash", "year", "paper", "official_number", "sub_part",
    "score", "measure", "db_question_id", "text", "db_text",
]

WORD_NUMBERS = {
    w: i for i, w in enumerate(
        "ONE TWO THREE FOUR FIVE SIX SEVEN EIGHT NINE TEN ELEVEN TWELVE THIRTEEN "
        "FOURTEEN FIFTEEN SIXTEEN SEVENTEEN EIGHTEEN NINETEEN TWENTY".split(), start=1)
} | {"TWENTY-FIVE": 25}

#: Fixed floor for the English vocabulary so a paper can be classified even
#: without a snapshot (fixtures, a year the snapshot lacks). Function words and
#: the directive verbs UPSC prints on nearly every question.
BASE_VOCAB = frozenset("""
a about above according across after again against all also although among an
and another answer any are as at be because been before being between both but
by can case cite comment compare context could critically define describe did
discuss do does done each elucidate enumerate evaluate examine examples explain
for from give giving has have he her his how however identify if illustrate in
india indian into is it its justify light may might more most must not of on
one only or other our out over own role should significance some state
statement substantiate such suggest than that the their them then there these
they this those through to under up upon us various was way ways we were what
when where whether which while who whom why will with within without would you
your words policy government national social economic political public
""".split())

STOPWORDS = frozenset("""
a about above after again against all also an and any are as at be because been
before being between both but by can could did do does each for from had has
have how if in into is it its may might more most no not of on or other our out
over own should so some such than that the their them then there these they
this those through to under up very was we were what when where whether which
while who whom why will with would you your answer words
""".split())

#: ``(Answer in 150 words)``, ``(150 words)``, and OCR slips like ``(Answer i in 150 words)``.
_ANCHOR_RE = re.compile(r"\(\s*(?:answer[^()\d]{0,8})?(\d{2,4})\s+words?\s*\)", re.I)
_ANCHOR_MARKS_RE = re.compile(r"words?\s*\)\s*[—–\-]?\s*(\d{1,3}(?:½)?)\s*$", re.I)
#: The paper-set code printed in every page footer (``KVMS-G-GSA/35 2``,
#: ``M-ESC-O-GSA``). The page number after it is often mis-read (``me``,
#: ``i``), so only the code is matched.
_FOOTER_RE = re.compile(r"^(?:\S{1,2}\s+)?[\W_]*[A-Z]{1,6}(?:-[A-Z]{1,6}){2,4}(?:/\d+)?(?:\s|$)")
_LABEL_ONLY_RE = re.compile(r"^\(\s*([a-d])\s*\)\s*$")
_LABEL_LEAD_RE = re.compile(r"^(?:Q?\d{1,2}\s*[.,]\s*)?\(\s*([a-d])\s*\)\s+")
_NUMBER_ONLY_RE = re.compile(r"^Q?\s?(\d{1,2})\s*[.,]\s*$")
_MARKS_ONLY_RE = re.compile(r"^(\d{1,3}(?:½)?)\s*$")
#: Marks printed at the end of the question's last text line, before the
#: word-limit line: ``... voters ? 10``.
_TRAILING_MARKS_RE = re.compile(r"[?.)\"”]\s+(\d{1,2}(?:½)?)\s*$")
_SECTION_RE = re.compile(r"SECTION\s*[—–\-]?\s*([AB])\b")
_COUNT_RE = re.compile(r"There\s+are\s+([A-Z\-]+)\s+questions", re.I)
#: A one- or two-word sentence tail on its own line (``mending.``): only ever
#: accepted as the continuation of an English line.
_SHORT_TAIL_RE = re.compile(r"^[a-z][a-z'’\-]*(?:\s[a-z][a-z'’\-]*)?[.?!,;:]$")
_WORD_RE = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)?")
_GARBLE_RE = re.compile(r"[|¥§{}<>~^@#\\]")
_ESSAY_LIMIT_RE = re.compile(r"(\d{3,4})\s*[—–\-]+\s*(\d{3,4})\s*words", re.I)
_ESSAY_MARKS_RE = re.compile(r"(\d{2,3})\s*[x×]\s*\d\s*=\s*\d{3}")
_PHASE3_YEAR = re.compile(r"QP-CSM-(\d{2})-")
_PHASE3_PAPER = re.compile(r"PAPER\s*-?\s*(IV|III|II|I)\b")
_ROMAN = {"I": "GS1", "II": "GS2", "III": "GS3", "IV": "GS4"}


# ── text utilities ───────────────────────────────────────────────────────


def normalise(text: str) -> str:
    """Fold to comparable prose: accents out, punctuation out, lowercased."""
    folded = unicodedata.normalize("NFKD", str(text or ""))
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    folded = re.sub(r"[^a-z0-9]+", " ", folded.lower())
    return re.sub(r"\s+", " ", folded).strip()


_UNICODE_FOLDS = str.maketrans({
    "‘": "'", "’": "'", "‚": "'", "‛": "'",
    "“": '"', "”": '"', "„": '"', "‟": '"',
    "–": "-", "—": "-", "−": "-",
    " ": " ", " ": " ", "​": "",
})


def content_hash(text: str) -> str:
    """sha256 of the canonical question text.

    Mirrors ``app.exam_intelligence.option_normalize.question_hash`` (NFC, fold
    smart punctuation, collapse whitespace, lowercase) so the value equals the
    ``normalized_question_hash`` the importer computes for the same text.
    """
    canon = unicodedata.normalize("NFC", str(text or "")).translate(_UNICODE_FOLDS)
    canon = re.sub(r"\s+", " ", canon).strip().lower()
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def words(text: str) -> list[str]:
    return [w.lower().replace("’", "'") for w in _WORD_RE.findall(text or "")]


def content_words(text: str) -> list[str]:
    return [w for w in normalise(text).split() if w not in STOPWORDS and len(w) > 2]


def english_part(db_text: str) -> str:
    """The English half of a DB row: every token carrying a non-ASCII char goes.

    DB rows are bilingual and often mojibake (``Ã Â¤...``). Word limits and the
    trailing ``— 10`` marks are dropped too, so they cannot inflate a match.
    """
    kept = [tok for tok in str(db_text or "").split() if tok.isascii()]
    text = " ".join(kept)
    text = _ANCHOR_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def similarity(a: str, b: str) -> tuple[float, str]:
    """(score 0..1, measure) - the best of three deterministic measures."""
    na, nb = normalise(a), normalise(b)
    if not na or not nb:
        return 0.0, "none"
    best = (difflib.SequenceMatcher(None, na, nb, autojunk=False).ratio(), "sequence")
    ca, cb = set(content_words(a)), set(content_words(b))
    if ca and cb:
        common = len(ca & cb)
        dice = 2 * common / (len(ca) + len(cb))
        if dice > best[0]:
            best = (dice, "dice")
        if len(ca) >= CONTAINMENT_MIN_WORDS:
            contained = common / len(ca)
            if contained > best[0]:
                best = (contained, "containment")
    return round(best[0], 4), best[1]


def route_for(score: float) -> str:
    if score >= PRESENT_CUT:
        return ROUTE_PRESENT
    if score >= NEAR_CUT:
        return ROUTE_NEAR
    return ROUTE_INSERT


# ── line classification ──────────────────────────────────────────────────


@dataclass
class Line:
    no: int  # 1-based line number in the source file
    text: str
    page: int
    #: english | weak | anchor | label | number | marks | section | footer | blank | other
    kind: str = "other"
    ratio: float = 0.0
    label: str | None = None
    flags: list[str] = field(default_factory=list)


def known_word(token: str, vocab: frozenset[str]) -> bool:
    base = token.split("'")[0]
    if token in vocab or base in vocab:
        return True
    return any(
        base.endswith(suffix) and len(base) - len(suffix) >= 3 and base[: -len(suffix)] in vocab
        for suffix in _SUFFIXES
    )


def english_ratio(text: str, vocab: frozenset[str]) -> tuple[float, int]:
    toks = words(_ANCHOR_RE.sub(" ", text))
    if not toks:
        return 0.0, 0
    known = sum(1 for t in toks if known_word(t, vocab))
    return known / len(toks), len(toks)


def line_flags(text: str, ratio: float) -> list[str]:
    flags = []
    if ratio < CLEAN_MIN_RATIO:
        flags.append("unknown_words")
    if _GARBLE_RE.search(text):
        flags.append("garble_chars")
    stray = [t for t in re.findall(r"\b[A-Z]\b", text) if t not in ("A", "I")]
    if len(stray) > 1:
        flags.append("stray_caps")
    return flags


def suspect_tokens(text: str, vocab: frozenset[str]) -> bool:
    """A short lowercase non-word (``ose``) is the commonest OCR substitution."""
    return any(
        len(tok) <= 3 and tok.islower() and not known_word(tok, vocab)
        for tok in _WORD_RE.findall(_ANCHOR_RE.sub(" ", text))
    )


_SPLIT_ANCHOR_HEAD = re.compile(r"\(\s*answer(?:\s+in)?\s*$", re.I)
_SPLIT_ANCHOR_TAIL = re.compile(r"^(?:in\s+)?\d{2,4}\s+words?\s*\)", re.I)


def mend_split_anchors(lines: list[str]) -> list[str]:
    """Re-join a word limit the OCR broke over two lines: ``(Answer in`` / ``250 words) 15``.

    The tail line is blanked rather than removed so line numbers still point
    at the source file.
    """
    out = list(lines)
    for i, text in enumerate(out):
        if not _SPLIT_ANCHOR_HEAD.search(text.strip()):
            continue
        j = i + 1
        while j < len(out) and not out[j].strip():
            j += 1
        if j < len(out) and _SPLIT_ANCHOR_TAIL.match(out[j].strip()):
            out[i] = f"{text.rstrip()} {out[j].strip()}"
            out[j] = ""
    return out


def classify(lines: list[str], vocab: frozenset[str]) -> list[Line]:
    out: list[Line] = []
    page = 1
    for i, raw in enumerate(mend_split_anchors(lines), start=1):
        text = raw.strip()
        ln = Line(no=i, text=text, page=page)
        if not text:
            ln.kind = "blank"
        elif _FOOTER_RE.match(text):
            ln.kind = "footer"
        elif _LABEL_ONLY_RE.match(text):
            ln.kind, ln.label = "label", _LABEL_ONLY_RE.match(text).group(1)
        elif _NUMBER_ONLY_RE.match(text):
            ln.kind = "number"
        elif _MARKS_ONLY_RE.match(text):
            ln.kind = "marks"
        elif _SECTION_RE.search(text) and len(words(text)) <= 6:
            ln.kind = "section"
        else:
            ratio, n = english_ratio(text, vocab)
            ln.ratio = ratio
            anchored = bool(_ANCHOR_RE.search(text))
            if anchored and (n <= 3 or ratio >= ENGLISH_MIN_RATIO):
                ln.kind = "anchor"
            elif n >= 3 and ratio >= ENGLISH_MIN_RATIO:
                ln.kind = "english"
            elif (n >= 3 and ratio >= WEAK_MIN_RATIO) or (n <= 2 and ratio >= 0.5) \
                    or _SHORT_TAIL_RE.match(text):
                ln.kind = "weak"
            lead = _LABEL_LEAD_RE.match(text)
            if lead:
                ln.label = lead.group(1)
            if ln.kind in ("english", "anchor", "weak"):
                ln.flags = line_flags(_ANCHOR_RE.sub(" ", text), ratio if n else 1.0)
                if suspect_tokens(text, vocab):
                    ln.flags.append("suspect_token")
                if ln.kind == "weak" and n >= 3:
                    ln.flags.append("weak_english")
        out.append(ln)
        if ln.kind == "footer":
            page += 1
    return out


# ── question assembly ────────────────────────────────────────────────────


@dataclass
class Block:
    lines: list[Line]
    anchored: bool
    word_limit: int | None = None
    marks: str | None = None
    marks_source: str | None = None
    section: str | None = None

    @property
    def page(self) -> int:
        return self.lines[-1].page

    @property
    def span(self) -> list[int]:
        return [self.lines[0].no, self.lines[-1].no]

    @property
    def embedded_parts(self) -> int:
        return sum(1 for ln in self.lines if ln.kind in ("english", "anchor") and ln.label)


def join_lines(lines: Iterable[Line]) -> str:
    """Join OCR lines into one paragraph, mending end-of-line hyphenation."""
    out = ""
    for ln in lines:
        piece = ln.text
        if out.endswith("-") and piece[:1].islower():
            out = out[:-1] + piece
        else:
            out = f"{out} {piece}" if out else piece
    return re.sub(r"\s+", " ", out).strip()


def clean_text(block: Block) -> str:
    lines = list(block.lines)
    if block.anchored:
        # Whatever follows the word limit on its line is the marks column
        # (read or mis-read, e.g. ``ES`` for 15) - never question text.
        last = lines[-1]
        cut = _ANCHOR_RE.search(last.text)
        lines[-1] = Line(no=last.no, text=last.text[: cut.start()] if cut else last.text, page=last.page)
    text = join_lines(lines)
    text = _ANCHOR_RE.sub(" ", text)
    text = re.sub(r"\s[—–\-]?\s*\d{1,3}½?\s*$", "", text) if block.anchored else _TEXT_TAIL_MARKS_RE.sub("", text)
    text = re.sub(r"\s+([?.,;:!])", r"\1", text)
    return re.sub(r"\s+", " ", text).strip().lstrip("-—–_.,;:| ").rstrip("-—–_,;:| ")


_INSTRUCTION_RE = re.compile(
    r"answer\s+(?:all\s+)?(?:the\s+)?(?:following\s+)?questions|not\s+more\s+than|"
    r"questions?\s+carr(?:y|ies)\s+equal|contents?\s+of\s+the\s+answers?|word\s+limit\s+specified|"
    r"question[-\s]cum[-\s]answer|medium\s+authori[sz]ed|struck\s+off",
    re.I,
)
#: Fewer content words than this is a fragment, not a question.
FRAGMENT_MAX_CONTENT_WORDS = 3
#: A text starting mid-sentence and shorter than this many words is the tail
#: of a question whose head the OCR lost.
TRUNCATED_FRAGMENT_WORDS = 8


def drop_reason(block: Block, vocab: frozenset[str]) -> str | None:
    """Why a block is not a question, or None. Deterministic, text-only."""
    text = clean_text(block)
    if _INSTRUCTION_RE.search(text):
        return "instruction"
    if len(content_words(text)) <= FRAGMENT_MAX_CONTENT_WORDS:
        return "fragment"
    if text[:1].islower() and len(words(text)) < TRUNCATED_FRAGMENT_WORDS:
        return "fragment"
    ratio, _ = english_ratio(text, vocab)
    if ratio < ENGLISH_MIN_RATIO:
        return "fragment"
    return None


def question_region(lines: list[Line]) -> list[Line]:
    """Everything after the instructions.

    The instructions end with "... must be clearly struck off." on every paper
    of the series; questions can start on that same page, so the first footer
    is only the fallback.
    """
    for idx, ln in enumerate(lines[:120]):
        if "struck off" in ln.text.lower():
            return lines[idx + 1:]
    for idx, ln in enumerate(lines):
        if ln.kind == "footer":
            return lines[idx + 1:]
    return lines


def printed_count(lines: list[Line]) -> int | None:
    text = " ".join(ln.text for ln in lines[:80])
    m = _COUNT_RE.search(text)
    if not m:
        return None
    return WORD_NUMBERS.get(m.group(1).upper().strip("-"))


def anchored_blocks(region: list[Line]) -> list[Block]:
    blocks: list[Block] = []
    consumed: set[int] = set()
    for idx, ln in enumerate(region):
        if ln.kind != "anchor":
            continue
        members = [ln]
        j = idx - 1
        while j >= 0:
            prev = region[j]
            if prev.kind == "blank":
                j -= 1
                continue
            if prev.kind == "footer" and members[-1].text[:1].islower():
                # The question runs over a page break: the text above the
                # footer ends mid-sentence. Step over the footer and the
                # page's number/marks column, and keep reading only if English
                # resumes.
                k = j - 1
                while k >= 0 and region[k].kind in ("blank", "marks", "number", "label"):
                    k -= 1
                if k >= 0 and region[k].kind == "english" and region[k].no not in consumed:
                    j = k
                    continue
                break
            if prev.kind not in ("english", "weak") or prev.no in consumed:
                break
            members.append(prev)
            j -= 1
        # A weak line can only continue English, never open a question.
        while len(members) > 1 and members[-1].kind == "weak":
            members.pop()
        members.reverse()
        consumed.update(m.no for m in members)
        block = Block(lines=members, anchored=True)
        block.word_limit = int(_ANCHOR_RE.search(ln.text).group(1))
        inline = _ANCHOR_MARKS_RE.search(ln.text)
        before = _TRAILING_MARKS_RE.search(members[-2].text) if len(members) > 1 else None
        after = next((m for m in region[idx + 1:] if m.kind != "blank"), None)
        if inline:
            block.marks, block.marks_source = inline.group(1), "printed_inline"
        elif before:
            block.marks, block.marks_source = before.group(1), "printed_inline"
        elif after is not None and after.kind == "marks":
            block.marks, block.marks_source = after.text.strip(), "printed_inline"
            after.kind = "marks_used"
        blocks.append(block)
    return blocks


def unanchored_blocks(region: list[Line]) -> list[Block]:
    blocks: list[Block] = []
    current: list[Line] = []
    for ln in region + [Line(no=-1, text="", page=-1, kind="other")]:
        if ln.kind in ("english", "anchor") or (ln.kind == "weak" and current):
            current.append(ln)
            continue
        if ln.kind == "blank" and current:
            continue
        if current and sum(len(words(m.text)) for m in current) >= 6:
            blocks.append(Block(lines=current, anchored=False))
        current = []
    for block in blocks:
        tail = re.search(r"\s(\d{1,2})\s*$", block.lines[-1].text)
        if tail:
            block.marks, block.marks_source = tail.group(1), "printed_inline"
    return blocks


#: A marks figure left at the end of unanchored text: ``12``, ``12½``, and
#: ``12%`` (the OCR's reading of ½). Removed from the text, never read as marks
#: unless it is plain digits.
_TEXT_TAIL_MARKS_RE = re.compile(r"\s(?:\d{1,2}\s*\+\s*)?\d{1,2}(?:½|%|\s?1/2)?(?:\s*=\s*\d{1,2}(?:½|%)?)?\s*$")


def fill_marks_from_column(region: list[Line], blocks: list[Block]) -> None:
    """Zip a page's marks column onto its questions - only on an exact count."""
    by_page: dict[int, list[Block]] = {}
    for block in blocks:
        by_page.setdefault(block.page, []).append(block)
    # The marks column is OCR'd after the page's footer, so a marks line that
    # directly follows a footer (nothing but blanks/numbers/labels between)
    # belongs to the page the footer closed.
    column: dict[int, list[str]] = {}
    after_footer = False
    for ln in region:
        if ln.kind == "footer":
            after_footer = True
            continue
        if ln.kind == "marks":
            page = ln.page - 1 if after_footer else ln.page
            column.setdefault(page, []).append(ln.text.strip())
        elif ln.kind not in ("blank", "number", "label", "marks_used"):
            after_footer = False
    for page, members in by_page.items():
        missing = [b for b in members if b.marks is None]
        values = column.get(page, [])
        inline = [b for b in members if b.marks is not None]
        # A page whose inline marks are also printed in the column: drop those.
        if inline and len(values) == len(members):
            values = [v for b, v in zip(members, values) if b.marks is None]
        if missing and len(values) == len(missing):
            for block, value in zip(missing, values):
                block.marks, block.marks_source = value, "printed_column"


def assign_sections(region: list[Line], blocks: list[Block]) -> None:
    section = None
    marks = {b.lines[0].no: b for b in blocks}
    for ln in region:
        if ln.kind == "section":
            section = _SECTION_RE.search(ln.text).group(1)
        if ln.no in marks:
            marks[ln.no].section = section


@dataclass
class Numbered:
    block: Block
    number: int
    sub_part: str | None


def number_blocks(region: list[Line], blocks: list[Block], expected: int | None) -> tuple[list[Numbered], list[str]]:
    """Official numbers + sub-parts. Returns (numbered, paper-level flags)."""
    flags: list[str] = []
    cases = [b for b in blocks if b.embedded_parts >= 2]
    simple = [b for b in blocks if b.embedded_parts < 2]
    if expected is None:
        flags.append("printed_count_unread")
    if expected is None or len(blocks) == expected or len(simple) <= (expected - len(cases)):
        if expected is not None and len(blocks) != expected:
            flags.append(f"count_mismatch:printed={expected},extracted={len(blocks)}")
        return [Numbered(b, i, None) for i, b in enumerate(blocks, start=1)], flags

    # More simple blocks than the simple questions printed: they are sub-parts.
    in_block = {ln.no for b in blocks for ln in b.lines}
    # Labels are read only up to the end of the sub-part section: the case
    # studies after it print their own (a)/(b) in the Hindi half too.
    last_simple = simple[-1].lines[-1].no
    ends = [cases[0].lines[0].no] if cases else []
    ends += [ln.no for ln in region if ln.kind == "section" and ln.no > last_simple][:1]
    stop = min(ends) if ends else None
    labels = [
        ln.label for ln in region
        if ln.label and ln.no not in in_block and (stop is None or ln.no < stop)
    ]
    if len(labels) != len(simple):
        flags.append(f"subpart_labels_unread:labels={len(labels)},parts={len(simple)}")
        return [Numbered(b, i, None) for i, b in enumerate(blocks, start=1)], flags
    numbered: list[Numbered] = []
    number = 0
    label_iter = iter(labels)
    for block in blocks:
        if block in cases:
            number += 1
            numbered.append(Numbered(block, number, None))
            continue
        label = next(label_iter)
        if label == "a" or number == 0:
            number += 1
        numbered.append(Numbered(block, number, label))
    if number != expected:
        flags.append(f"count_mismatch:printed={expected},numbered={number}")
    return numbered, flags


# ── essay ────────────────────────────────────────────────────────────────


def essay_questions(lines: list[Line]) -> tuple[list[Numbered], list[str], str | None, str | None]:
    region = question_region(lines)
    text = " ".join(ln.text for ln in lines)
    limit = _ESSAY_LIMIT_RE.search(text)
    marks = _ESSAY_MARKS_RE.search(text)
    word_limit = f"{limit.group(1)}-{limit.group(2)}" if limit else None
    marks_value = marks.group(1) if marks else None
    section = None
    blocks: list[Block] = []
    for ln in region:
        if ln.kind == "section":
            section = _SECTION_RE.search(ln.text).group(1)
            continue
        if section is None or ln.kind not in ("english", "anchor"):
            continue
        lower = ln.text.lower()
        if "essay" in lower and "write" in lower:
            continue
        prev = blocks[-1] if blocks else None
        if prev and prev.section == section and not re.search(r"[.?!\"”']\s*$", prev.lines[-1].text) \
                and prev.lines[-1].no + 2 >= ln.no:
            prev.lines.append(ln)
            continue
        block = Block(lines=[ln], anchored=False, section=section)
        blocks.append(block)
    flags = [] if len(blocks) == 8 else [f"count_mismatch:expected=8,extracted={len(blocks)}"]
    for block in blocks:
        if marks_value:
            block.marks, block.marks_source = marks_value, "printed_header"
    return [Numbered(b, i, None) for i, b in enumerate(blocks, start=1)], flags, word_limit, marks_value


# ── one paper ────────────────────────────────────────────────────────────


def paper_code_for(year: int, paper: str) -> str:
    return f"UPSC-CSE-MAINS-GS-{year}-{paper}"


def extract_paper(text: str, *, year: int, paper: str, source_file: str,
                  vocab: frozenset[str]) -> dict[str, Any]:
    """Pure: OCR text in, staged questions out. No IO."""
    lines = classify(text.splitlines(), vocab)
    region = question_region(lines)
    paper_flags: list[str] = []
    mode = "essay"
    essay_limit = None
    if paper == ESSAY:
        numbered, paper_flags, essay_limit, _ = essay_questions(lines)
        expected = 8
    else:
        expected = printed_count(lines)
        anchors = sum(1 for ln in region if ln.kind == "anchor")
        need = max(1, -(-3 * expected // 5)) if expected else 5  # ceil(60%)
        if anchors >= need:
            mode = "anchored"
            blocks = anchored_blocks(region)
        else:
            mode = "unanchored"
            blocks = unanchored_blocks(region)
        kept, dropped = [], {}
        for block in blocks:
            reason = drop_reason(block, vocab)
            if reason:
                dropped[reason] = dropped.get(reason, 0) + 1
            else:
                kept.append(block)
        blocks = kept
        paper_flags_pre = [f"dropped_{k}:{v}" for k, v in sorted(dropped.items())]
        fill_marks_from_column(region, blocks)
        assign_sections(region, blocks)
        numbered, paper_flags = number_blocks(region, blocks, expected)
        paper_flags = paper_flags_pre + paper_flags

    questions = []
    for item in numbered:
        block = item.block
        qtext = clean_text(block)
        low = [
            {"line": ln.no, "text": ln.text, "flags": ln.flags}
            for ln in block.lines if ln.flags
        ]
        flags = []
        if mode == "unanchored":
            flags.append("unanchored")
        if low:
            flags.append("low_confidence_ocr")
        if block.marks is None:
            flags.append("marks_unread")
        if qtext[:1].islower():
            flags.append("possible_truncation")
        if any(f.startswith(("count_mismatch", "subpart_labels_unread")) for f in paper_flags):
            flags.append("numbering_unverified")
        questions.append({
            "official_number": item.number,
            "sub_part": item.sub_part,
            "section": block.section,
            "text": qtext,
            "marks": block.marks,
            "marks_source": block.marks_source,
            "word_limit": essay_limit if paper == ESSAY else block.word_limit,
            "source_file": source_file,
            "line_span": block.span,
            "page": block.page,
            "low_confidence_lines": low,
            "flags": flags,
            "content_hash": content_hash(qtext),
        })
    return {
        "year": year,
        "paper": paper,
        "paper_code": paper_code_for(year, paper),
        "paper_kind": "essay" if paper == ESSAY else "gs",
        "source_file": source_file,
        "mode": mode,
        "printed_question_count": expected,
        "paper_flags": paper_flags,
        "questions": questions,
    }


# ── DB snapshot + routing ────────────────────────────────────────────────


def _rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        payload = payload.get("items") or payload.get("rows") or []
    return [r for r in payload if isinstance(r, dict)] if isinstance(payload, list) else []


def load_snapshot(paths: Iterable[Path]) -> dict[int, list[dict[str, Any]]]:
    """year -> [{id, text}] with ``text`` the English half of the DB row."""
    pool: dict[int, list[dict[str, Any]]] = {}
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        m = re.search(r"(20\d{2})", path.name)
        file_year = int(m.group(1)) if m else None
        for row in _rows(payload):
            year = row.get("year") or file_year
            if year is None:
                continue
            pool.setdefault(int(year), []).append({
                "id": str(row.get("id") or ""),
                "text": english_part(row.get("question_text") or ""),
            })
    return pool


def snapshot_vocab(pool: dict[int, list[dict[str, Any]]]) -> frozenset[str]:
    vocab = set(BASE_VOCAB)
    for rows in pool.values():
        for row in rows:
            vocab.update(words(row["text"]))
    return frozenset(vocab)


def best_match(text: str, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    best = {"score": 0.0, "measure": "none", "id": None, "text": None}
    for cand in candidates:
        if not cand["text"]:
            continue
        score, measure = similarity(text, cand["text"])
        if score > best["score"]:
            best = {"score": score, "measure": measure, "id": cand["id"], "text": cand["text"]}
    return best


def route_paper(staged: dict[str, Any], pool: list[dict[str, Any]]) -> dict[str, Any]:
    """Attach a DB match + route to every question. Pure."""
    for q in staged["questions"]:
        match = best_match(q["text"], pool)
        q["best_db_match"] = match
        q["route"] = route_for(match["score"])
    return staged


# ── source discovery ─────────────────────────────────────────────────────


def discover_sources(ocr_dir: Path = OCR_DIR) -> dict[tuple[int, str], Path]:
    """(year, paper) -> the OCR file. Longest text wins where both caches hold it."""
    found: dict[tuple[int, str], Path] = {}

    def offer(key: tuple[int, str], path: Path) -> None:
        if key not in found or path.stat().st_size > found[key].stat().st_size:
            found[key] = path

    for path in sorted(ocr_dir.glob("*.txt")):
        m = re.fullmatch(r"(\d{4})_(GS[1-4])", path.stem)
        if m:
            offer((int(m.group(1)), m.group(2)), path)
    raw = ocr_dir / "phase3_raw"
    if raw.is_dir():
        for path in sorted(raw.glob("*.txt")):
            ym = _PHASE3_YEAR.search(path.name)
            if not ym:
                continue
            year = 2000 + int(ym.group(1))
            if "ESSAY" in path.name.upper():
                offer((year, ESSAY), path)
                continue
            pm = _PHASE3_PAPER.search(path.stem.replace("-", " "))
            if pm:
                offer((year, _ROMAN[pm.group(1)]), path)
    return found


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


# ── review CSV ───────────────────────────────────────────────────────────


def review_rows(staged: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for q in staged["questions"]:
        if q["route"] != ROUTE_INSERT:
            continue
        low = bool(q["low_confidence_lines"]) or any(
            f in q["flags"] for f in ("unanchored", "possible_truncation", "numbering_unverified")
        )
        out.append({
            "paper_code": staged["paper_code"],
            "content_hash": q["content_hash"],
            "year": staged["year"],
            "paper": staged["paper"],
            "official_number": q["official_number"],
            "sub_part": q["sub_part"] or "",
            "section": q["section"] or "",
            "marks": q["marks"] or "",
            "word_limit": q["word_limit"] or "",
            "low_confidence": "Y" if low else "N",
            "flags": ";".join(q["flags"]),
            "best_db_score": q["best_db_match"]["score"],
            "text": q["text"],
            "approved": "",
            "edited_text": "",
            "edited_marks": "",
            "reviewer_note": "",
        })
    return out


def near_rows(staged: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "paper_code": staged["paper_code"],
            "content_hash": q["content_hash"],
            "year": staged["year"],
            "paper": staged["paper"],
            "official_number": q["official_number"],
            "sub_part": q["sub_part"] or "",
            "score": q["best_db_match"]["score"],
            "measure": q["best_db_match"]["measure"],
            "db_question_id": q["best_db_match"]["id"],
            "text": q["text"],
            "db_text": q["best_db_match"]["text"],
        }
        for q in staged["questions"] if q["route"] == ROUTE_NEAR
    ]


def merge_review(new_rows: list[dict[str, Any]], existing_path: Path) -> list[dict[str, Any]]:
    """Keep every human column already filled in, keyed by (paper_code, content_hash)."""
    if not existing_path.is_file():
        return new_rows
    with existing_path.open(encoding="utf-8-sig", newline="") as fh:
        old = {(r["paper_code"], r["content_hash"]): r for r in csv.DictReader(fh)}
    for row in new_rows:
        prior = old.get((row["paper_code"], row["content_hash"]))
        if prior:
            for col in HUMAN_FIELDS:
                if prior.get(col):
                    row[col] = prior[col]
    return new_rows


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


# ── run ──────────────────────────────────────────────────────────────────


def staged_for_output(staged: dict[str, Any]) -> dict[str, Any]:
    """The JSON file: insert-route questions only (every 2026 question)."""
    out = {k: v for k, v in staged.items() if k != "questions"}
    out["exam_id"] = EXAM_ID
    out["exam_phase_id"] = EXAM_PHASE_ID
    out["extractor_version"] = EXTRACTOR_VERSION
    out["questions"] = [q for q in staged["questions"] if q["route"] == ROUTE_INSERT]
    return out


def summarise(results: list[dict[str, Any]], no_source: list[tuple[int, str]]) -> str:
    lines = [
        "# UPSC CSE Mains GS - missing-question extraction",
        "",
        f"Generated by `scripts/extract_gs_missing.py` ({EXTRACTOR_VERSION}). Offline; "
        "no DB writes. Dedupe is against the DB snapshot, whole year; the loader "
        "re-checks against the live DB before any insert.",
        "",
        f"Routes: present >= {PRESENT_CUT}, near {NEAR_CUT}-{PRESENT_CUT} (never loadable), "
        f"insert < {NEAR_CUT}.",
        "",
        "| year | paper | mode | printed | extracted | present | near | missing (staged) "
        "| staged low-conf | low-conf lines | paper flags |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    totals = {"extracted": 0, "present": 0, "near": 0, "insert": 0, "lowq": 0, "lowl": 0}
    for r in results:
        qs = r["questions"]
        present = sum(1 for q in qs if q["route"] == ROUTE_PRESENT)
        near = sum(1 for q in qs if q["route"] == ROUTE_NEAR)
        ins = [q for q in qs if q["route"] == ROUTE_INSERT]
        lowq = sum(1 for q in ins if q["low_confidence_lines"] or "unanchored" in q["flags"])
        lowl = sum(len(q["low_confidence_lines"]) for q in ins)
        totals["extracted"] += len(qs)
        totals["present"] += present
        totals["near"] += near
        totals["insert"] += len(ins)
        totals["lowq"] += lowq
        totals["lowl"] += lowl
        lines.append(
            f"| {r['year']} | {r['paper']} | {r['mode']} | {r['printed_question_count'] or '?'} "
            f"| {len(qs)} | {present} | {near} | {len(ins)} | {lowq} | {lowl} "
            f"| {'; '.join(r['paper_flags']) or '-'} |"
        )
    lines.append(
        f"| **all** | | | | **{totals['extracted']}** | **{totals['present']}** "
        f"| **{totals['near']}** | **{totals['insert']}** | **{totals['lowq']}** "
        f"| **{totals['lowl']}** | |"
    )
    lines += ["", "## No official source in the repo (not extractable here)", ""]
    lines += [f"- {y} {p}" for y, p in no_source] or ["- none"]
    lines.append("")
    return "\n".join(lines)


def run(args: argparse.Namespace) -> int:
    ocr_dir = Path(args.ocr_dir)
    out_dir = Path(args.out_dir)
    snapshot_paths = [Path(p) for p in args.db_snapshot] if args.db_snapshot else sorted(ROOT.glob(SNAPSHOT_GLOB))
    pool = load_snapshot(snapshot_paths)
    vocab = snapshot_vocab(pool)
    sources = discover_sources(ocr_dir)
    years = sorted({y for y, _ in sources} | set(range(2013, 2026)))
    if args.year:
        years = [y for y in years if y in args.year]

    results, no_source = [], []
    for year in years:
        for paper in PAPERS:
            src = sources.get((year, paper))
            if src is None:
                no_source.append((year, paper))
                continue
            staged = extract_paper(
                src.read_text(encoding="utf-8", errors="replace"),
                year=year, paper=paper, source_file=rel(src), vocab=vocab,
            )
            route_paper(staged, pool.get(year, []))
            if year == FULL_YEAR:
                # No DB row exists for this year; a match is a coincidence
                # with no row to point at, so every question is staged.
                for q in staged["questions"]:
                    if q["route"] != ROUTE_INSERT:
                        q["flags"].append(f"snapshot_match:{q['best_db_match']['score']}")
                    q["route"] = ROUTE_INSERT
            results.append(staged)

    review, near = [], []
    out_dir.mkdir(parents=True, exist_ok=True)
    for staged in results:
        out = staged_for_output(staged)
        target = out_dir / f"{staged['year']}_{staged['paper']}.json"
        if out["questions"]:
            target.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        elif target.exists():
            target.unlink()
        review += review_rows(staged)
        near += near_rows(staged)

    review_path = out_dir / "review.csv"
    write_csv(review_path, REVIEW_FIELDS, merge_review(review, review_path))
    write_csv(out_dir / "near_matches.csv", NEAR_FIELDS, near)
    summary = summarise(results, no_source)
    (out_dir / "summary.md").write_text(summary, encoding="utf-8")
    print(summary)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ocr-dir", default=str(OCR_DIR))
    ap.add_argument("--out-dir", default=str(OUT_DIR))
    ap.add_argument("--db-snapshot", nargs="*", help="DB export JSON(s); default: repo-root pyq_<year>_mains_questions.json")
    ap.add_argument("--year", type=int, action="append", help="limit to one year (repeatable)")
    return run(ap.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
