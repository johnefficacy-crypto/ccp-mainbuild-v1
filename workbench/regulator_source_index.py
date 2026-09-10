"""Index the IFSCA and PFRDA recollected-question books onto loaded paper rows.

The books are compendia: one PDF per exam-year carrying every phase and paper.
Each page repeats a running header that names the year, the phase and the paper
("IFSCA Grade A 2024 Phase 1 Paper 1 Recollected Questions"), and each section
inside a paper opens with a subject heading. Those two lines are the whole join:

    paper_code  IFSCA-GA-2024-P1P1-REAS
                       |    |     |
                       |    |     `-- subject heading "Reasoning Ability"
                       |    `-------- running header "Phase 1 Paper 1"
                       `------------- running header year / book file

question_number is per paper, and the books number each subject section from 1,
so (paper_code, question_number) addresses exactly one printed question.

No SEBI book is in the repo, so SEBI is not indexed here.
"""
from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass, field

# --- running header -> (year, phase-paper token) -----------------------------
RE_PAGENO_HEADER = re.compile(r"^\s*(\d{1,3})\s*\n(.+)$", re.M)
RE_HEADER = re.compile(
    r"(?P<exam>IFSCA|F?PFRDA|FRDA)\s+Grade\s+A\s+(?P<year>\d{4})\s+"
    r"Phase\s*(?P<phase>\d)\s*[-–]?\s*"
    r"(?:Paper\s*[-–]?\s*(?P<paper>\d)|(?P<desc>Descriptive))",
    re.I,
)

SUBJECT_TO_CODE = {
    "quantitative aptitude": "QUANT",
    "reasoning ability": "REAS",
    "english language": "ENG",
    "general awareness": "GA",
    "commerce & accountancy": "COMM",
    "commerce & accounts": "COMM",
    "costing": "COST",
    "economic & social development": "ECO",
    "economics": "ECO",
    "finance": "FIN",
    "management": "MGMT",
    "companies act": "CA",
    "pension sector": "PENS",
    "banking, capital market & bullion": "FIN",
    "banking capital market & bullion": "FIN",
    "banking capital marketing & bullion": "FIN",
    "ifsca & gift city": "GIFT",
    "ifsca & gift city ": "GIFT",
    "insurance & pension": "INSPEN",
    "union budget & economic survey": "BUDGET",
}

RE_QMARK = re.compile(r"^\s*Q\s?\.?\s*(\d{1,3})\s*[\.\)]\s*(.*)$")
RE_OPT = re.compile(r"^\s*\(?([A-Ea-e])\)?\s*[\.\)]\s*(.*)$")
RE_DIRECTIONS = re.compile(
    r"^\s*(?:Directions?|Direction|Instructions?)\s*\(?\s*Q?\.?\s*"
    r"(\d{1,3})\s*(?:[-–—]{1,2}\s*(?:Q\.?)?(\d{1,3}))?\s*\)?\s*[:.]?\s*(.*)$",
    re.I,
)
RE_ANSWER_TABLE = re.compile(r"^\s*Question\s+Answer\b", re.I)
# a block may cover a range or a single question: "(11-15)" or "(25)"
RE_RANGE = re.compile(r"Q?\.?(\d{1,3})\s*(?:[-–—]\s*Q?\.?(\d{1,3}))?\s*\)?")
# a Directions header does not always start its own line - the extractor can
# weld it onto the tail of the preceding option
# these books head a block three ways: "Directions (11-15):", "11-15) Direction:"
# and a bare range welded to the previous option as "I.Q11-15)"
RE_DIRECTIONS_ANY = re.compile(
    r"(?:Directions?|Instructions?)\s*:?\s*\(\s*Q?\.?\s*\d{1,3}\s*[-–—)]"
    r"|(?:\bI\.)?\s*Q?\.?\d{1,3}\s*[-–—]\s*Q?\.?\d{1,3}\s*\)\s*"
    r"(?:Directions?|Instructions?)?",
    re.I)
# U+0003 is the bullet glyph these books draw before an option's text
RE_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
# page furniture that the extractor leaves in the flow
RE_FURNITURE = re.compile(
    r"^\s*(?:\d{1,3}|(?:IFSCA|PFRDA|FRDA)\s+Grade\s+A\s+\d{4}.*|"
    r"Recollected|Questions|Answer\s*Key|Page\s*\d+|\|\s*P\s*a\s*g\s*e.*)\s*$",
    re.I,
)


def squash(text: str) -> tuple[str, list[int]]:
    """Lowercase-alphanumeric reduction plus an index map back into `text`."""
    out: list[str] = []
    idx: list[int] = []
    for i, ch in enumerate(text):
        if ch.isalnum():
            out.append(ch.lower())
            idx.append(i)
    return "".join(out), idx


def ascii_digits(text: str) -> str:
    """Fold every Unicode decimal-digit codepoint down to its ASCII digit."""
    out = []
    for ch in text:
        if not ch.isascii() and unicodedata.category(ch) == "Nd":
            out.append(str(unicodedata.digit(ch)))
        else:
            out.append(ch)
    return "".join(out)


@dataclass
class SourceQuestion:
    paper_code: str
    number: int
    stem: str
    options: dict[str, str] = field(default_factory=dict)
    direction_body: str = ""
    direction_range: tuple[int, int] | None = None
    page: int = 0


def _phase_token(m: re.Match) -> str:
    phase = m.group("phase")
    paper = "1" if m.group("desc") else m.group("paper")
    return f"P{phase}P{paper}"


def parse_book(path: str, exam_prefix: str) -> dict[str, dict[int, SourceQuestion]]:
    """Return {paper_code: {question_number: SourceQuestion}} for one book."""
    raw = open(path, encoding="utf-8").read()
    pages = raw.split("\f")
    pages = [RE_CONTROL.sub(" ", pg) for pg in pages]
    papers: dict[str, dict[int, SourceQuestion]] = {}

    subject = None
    section = None            # (year, phase token)
    pending_dir: tuple[int, int, str] | None = None
    cur: SourceQuestion | None = None
    cur_opt: str | None = None
    collecting_dir = False
    dir_lines: list[str] = []

    def close_question() -> None:
        nonlocal cur, cur_opt
        if cur is not None and cur.paper_code:
            papers.setdefault(cur.paper_code, {}).setdefault(cur.number, cur)
        cur, cur_opt = None, None

    for pno, page in enumerate(pages, start=1):
        hm = RE_PAGENO_HEADER.search(page)
        header = hm.group(2).strip() if hm else ""
        m = RE_HEADER.search(header)
        if not m:
            continue
        if re.search(r"Answer\s*Key", header, re.I):
            close_question()
            section = None
            continue
        new_section = (m.group("year"), _phase_token(m))
        if new_section != section:
            close_question()
            section, subject, pending_dir = new_section, None, None
        year, ptok = section

        for line in page.split("\n"):
            s = line.strip()
            if not s:
                if collecting_dir and dir_lines:
                    collecting_dir = False
                continue
            if RE_FURNITURE.match(s) or RE_ANSWER_TABLE.match(s):
                continue

            key = s.lower().rstrip(" .")
            if key in SUBJECT_TO_CODE and not RE_OPT.match(s):
                close_question()
                subject, pending_dir, collecting_dir = SUBJECT_TO_CODE[key], None, False
                continue

            cut = RE_DIRECTIONS_ANY.search(s)
            if cut:
                # a block header ends whatever came before it, whether it opens
                # its own line or was welded onto the tail of the last option
                head = s[:cut.start()].strip()
                if head and cur is not None:
                    if cur_opt is not None:
                        cur.options[cur_opt] = (cur.options[cur_opt] + " " + head).strip()
                    else:
                        cur.stem = (cur.stem + " " + head).strip()
                close_question()
                s = s[cut.start():].strip()
                rm = RE_RANGE.search(s)
                if rm:
                    body = s[rm.end():].strip().lstrip(":.").strip()
                    dir_lines = [body] if body else []
                    lo = int(rm.group(1))
                    hi = int(rm.group(2)) if rm.group(2) else lo
                    pending_dir = (lo, hi, "")
                    collecting_dir = True
                    continue

            dm = RE_DIRECTIONS.match(s)
            if dm:
                close_question()
                lo = int(dm.group(1))
                hi = int(dm.group(2)) if dm.group(2) else lo
                dir_lines = [dm.group(3).strip()] if dm.group(3).strip() else []
                pending_dir = (lo, hi, "")
                collecting_dir = True
                continue

            qm = RE_QMARK.match(s)
            if qm:
                if collecting_dir:
                    collecting_dir = False
                    if pending_dir:
                        pending_dir = (pending_dir[0], pending_dir[1],
                                       " ".join(dir_lines).strip())
                    dir_lines = []
                close_question()
                if subject is None:
                    continue
                num = int(qm.group(1))
                code = f"{exam_prefix}-GA-{year}-{ptok}-{subject}"
                cur = SourceQuestion(paper_code=code, number=num,
                                     stem=qm.group(2).strip(), page=pno)
                if pending_dir and pending_dir[0] <= num <= pending_dir[1]:
                    cur.direction_body = pending_dir[2]
                    cur.direction_range = (pending_dir[0], pending_dir[1])
                cur_opt = None
                continue

            if collecting_dir:
                dir_lines.append(s)
                continue

            om = RE_OPT.match(s)
            if om and cur is not None:
                label = om.group(1).lower()
                # an option label only opens a new option when it advances
                if cur_opt is None or label > cur_opt:
                    cur_opt = label
                    cur.options[label] = om.group(2).strip()
                    continue
            if cur is not None:
                if cur_opt is not None:
                    cur.options[cur_opt] = (cur.options[cur_opt] + " " + s).strip()
                else:
                    cur.stem = (cur.stem + " " + s).strip()

    close_question()
    return papers


BOOKS = [
    ("docs/reference/pyq/ifsca/IFSCA-Grade-A-Phase-1-2-Previous-Year-Papers-Book-2023.pdf", "IFSCA"),
    ("docs/reference/pyq/ifsca/IFSCA-Grade-A-Phase-1-2-Previous-Year-Papers-Book-2024.pdf", "IFSCA"),
    ("docs/reference/pyq/ifsca/IFSCA-Grade-A-Phase-1-2-Previous-Year-Papers-2025.pdf", "IFSCA"),
    ("docs/reference/pyq/pfrda/PFRDA-Grade-A-2022-Phase-12-Previous-Year-Paper-Book.pdf", "PFRDA"),
    ("docs/reference/pyq/pfrda/PFRDA-Grade-A-2025-Phase-12-Previous-Year-Paper-Book.pdf", "PFRDA"),
]


def load_all(textdir: str) -> dict[str, dict[int, SourceQuestion]]:
    merged: dict[str, dict[int, SourceQuestion]] = {}
    for pdf, prefix in BOOKS:
        txt = os.path.join(textdir, os.path.basename(pdf).replace(".pdf", ".txt"))
        if not os.path.exists(txt):
            continue
        for code, qs in parse_book(txt, prefix).items():
            merged.setdefault(code, {}).update(qs)
    return merged
