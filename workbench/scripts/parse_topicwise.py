"""Parse a topic-wise PYQ section into JSON.

Usage: python3 parse_topicwise.py <pdf> <subject> <code> <first_page> [last_page]
Rows carry the topic heading and the year tag, but no paper/question number —
topic-wise listings do not record them.
"""
import re, sys, json, subprocess

PDF, SUBJECT, CODE, FIRST = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
LAST = sys.argv[5] if len(sys.argv) > 5 else None

cmd = ["pdftotext", "-layout", "-f", FIRST] + (["-l", LAST] if LAST else []) + [PDF, "-"]
raw = subprocess.run(cmd, capture_output=True, text=True).stdout
for a, b in [("\u2018", "'"), ("\u2019", "'"), ("\u201c", '"'), ("\u201d", '"'),
             ("\u2013", "-"), ("\u2014", "-"), ("\u00a0", " "), ("\ufb01", "fi"), ("\ufb02", "fl"),
             ("\ufb00", "ff"), ("\ufb03", "ffi"), ("\ufb04", "ffl"), ("\u25aa", " ")]:
    raw = raw.replace(a, b)

PAPER = re.compile(r"Topic[- ]wise[^\n]*?Paper\s*-?\s*([12])|Paper\s*-?\s*([12])[^\n]*?Topic[- ]wise", re.I)
QSTART = re.compile(r"^(\s{0,5})(\d{1,3})\.\s+(\S.*)$")
YEARS = re.compile(r"\(\s*(\d{4}(?:\s*[,/&]\s*\d{4})*)\s*\)\s*\.?\s*$")

rows, heading, paper, qbuf, qnum = [], [], None, None, None


def add_heading(text):
    """A heading that wraps mid-sentence is joined to the previous line,
    not stored as a separate heading level."""
    cont = bool(re.match(r"^[a-z]|^(to|and|the|of|in|with|from|for)\b", text))
    if heading and (cont or not re.search(r"[;:.]$", heading[-1])):
        heading[-1] = (heading[-1] + " " + text).strip()
    else:
        heading.append(text)
    del heading[:-3]


def flush():
    global qbuf
    if not qbuf:
        return
    text = re.sub(r"\s+", " ", " ".join(qbuf)).strip()
    yrs = []
    m = YEARS.search(text)
    if m:
        yrs = [int(y) for y in re.findall(r"\d{4}", m.group(1))]
        text = text[:m.start()].strip()
    text = re.sub(r"\s*\b(\d{1,2})\s*marks?\s*$", "", text, flags=re.I).strip()
    text = text.strip(" .,:;-")
    if text and text[-1] not in ".?\"'":
        text += "."
    if len(text) > 15 and paper is not None:
        rows.append({"optional_subject": SUBJECT, "paper_number": paper,
                     "topic_heading": " / ".join(heading) if heading else None,
                     "question_text": text,
                     "years_asked": yrs or None,
                     "year": yrs[0] if len(yrs) == 1 else None,
                     "question_type": "descriptive",
                     "source_list_index": qnum})
    qbuf = None


for ln in raw.split("\n"):
    ln = ln.replace("\f", "").rstrip()
    if re.fullmatch(r"\s*\d{1,3}\s*", ln):
        continue
    if not ln.strip():
        continue
    m = PAPER.search(ln)
    if m:
        flush(); paper = int(m.group(1) or m.group(2)); heading = []; continue
    mq = QSTART.match(ln)
    # a numbered line at the left margin with no year and no sentence end is a heading
    if mq and len(mq.group(1)) == 0 and not YEARS.search(ln.strip()) \
            and len(ln.strip()) < 80 and not re.search(r"[.?!]$", ln.strip()):
        flush()
        if qnum is not None:
            heading, qnum = [], None
        add_heading(ln.strip())
        continue
    if mq and len(mq.group(1)) <= 5:
        flush(); qnum = int(mq.group(2)); qbuf = [mq.group(3)]; continue
    ind = len(ln) - len(ln.lstrip())
    body = ln.strip()
    # a heading: unindented, short, no year tag, no sentence-final punctuation
    is_heading = (ind <= 2 and len(body) < 90 and not YEARS.search(body)
                  and not re.search(r"[.?!\"']$", body)
                  and not re.match(r"^[a-z(\"']", body))
    if is_heading:
        flush()
        if qnum is not None:
            heading, qnum = [], None
        add_heading(body)
        continue
    # a wrapped continuation: indented, or starts lowercase / mid-sentence punctuation
    if qbuf is not None and (ind >= 3 or re.match(r"^[a-z\"'\)\u2026,;-]", body)
                             or not YEARS.search(" ".join(qbuf))):
        qbuf.append(body); continue
    # unindented, not numbered -> a heading
    flush()
    if len(ln.strip()) > 3:
        if qnum is not None:          # first heading after a question block ends a section
            heading, qnum = [], None
        add_heading(ln.strip())

flush()

years = sorted({y for r in rows for y in (r["years_asked"] or [])})
out = {"extraction_meta": {
    "extracted_on": "2026-09-05", "source_file": PDF.split("/")[-1],
    "optional_subject": SUBJECT, "layout": "topic_wise",
    "years_covered": f"{years[0]}-{years[-1]}" if years else None,
    "capture_method": "pdftotext_layout_parse",
    "structure_note": ("Source has no year-wise section, so paper number, question number, "
                       "section and marks are not recoverable. topic_heading is the raw heading "
                       "block above the question and may combine a topic and a sub-topic line."),
    "language_coverage": ["en"], "hindi_present": False,
    "verified_against_official": False,
    "source_type": "aggregator", "source_publisher": "LotusArise IAS",
    "trust_status": "pending"},
    "questions": rows}
dst = f"/home/claude/psir/upsc-{CODE.lower()}-topicwise.json"
json.dump(out, open(dst, "w"), indent=2, ensure_ascii=False)

from collections import Counter
print(f"{SUBJECT}: {len(rows)} questions -> {dst}")
print("  by paper:", dict(Counter(r['paper_number'] for r in rows)))
print("  years:", years[0] if years else None, "-", years[-1] if years else None,
      f"| no year tag: {sum(1 for r in rows if not r['years_asked'])}")
print("  distinct headings:", len({r['topic_heading'] for r in rows}))
