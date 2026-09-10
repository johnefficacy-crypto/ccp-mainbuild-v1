"""Parse a LotusArise-style optional PYQ PDF (year-wise section) into JSON.

Usage:
    python3 parse_optional.py <pdf> <subject_name> <subject_code> <first_page>
"""
import re, sys, json, subprocess

PDF, SUBJECT, CODE, FIRST = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]

raw = subprocess.run(["pdftotext", "-layout", "-f", FIRST, PDF, "-"],
                     capture_output=True, text=True).stdout
for a, b in [("\u2018", "'"), ("\u2019", "'"), ("\u201c", '"'), ("\u201d", '"'),
             ("\u2013", "-"), ("\u2014", "-"), ("\u2212", "-"), ("\u25aa", " "),
             ("\u2022", " "), ("\u00d7", "x"), ("\u00a0", " "), ("\ufb01", "fi"), ("\ufb02", "fl"),
             ("\ufb00", "ff"), ("\ufb03", "ffi"), ("\ufb04", "ffl")]:
    raw = raw.replace(a, b)

lines = []
for ln in raw.split("\n"):
    ln = ln.replace("\f", "").rstrip()
    if re.fullmatch(r"\s*\d{1,3}\s*", ln):
        continue
    ln = re.sub(r"^(\s*)[lI]\.(\s)", r"\g<1>1.\g<2>", ln)      # source typo l. -> 1.
    if re.match(r"\s*SECTION\s*[-'\s]*[AB]\s*'?\s*$", ln, re.I):
        continue
    ln = re.sub(r"(?<=[.?\"'])\s+(?=[b-f]\s*\)\s*\.?\s*[A-Z\"'])", "\n", ln)
    for piece in ln.split("\n"):
        if piece.strip():
            lines.append(piece)

YEAR = re.compile(rf"{re.escape(SUBJECT)}[^\n]*?Paper\s*-?\s*(\d{{4}})"
                  rf"|{re.escape(SUBJECT)}\s*[-\u2013]\s*(\d{{4}})", re.I)
PHDR = re.compile(r"^\s*(?:[A-Za-z ]*(?:Questions?|Question Paper)\s*:?\s*)?"
                  r"PAPER\s*[-\u2013]?\s*(1|2|I|II)\s*(?:[-\u2013]?\s*\(?\s*\d{4}\s*\)?)?\s*$", re.I)

blocks, year, cur = [], None, None
for ln in lines:
    mp = PHDR.match(ln)
    if not mp:
        m = YEAR.search(ln)
        if m:
            year = m.group(1) or m.group(2); cur = None; continue
    m = mp
    if m and year:
        _v = m.group(1).upper()
        _pno = {"I": 1, "II": 2}.get(_v) or int(_v)
        cur = {"year": int(year), "pno": _pno, "lines": []}
        blocks.append(cur); continue
    if cur is not None:
        cur["lines"].append(ln)

_R = ["i","ii","iii","iv","v","vi","vii","viii",
      "ix","x","xi","xii","xiii","xiv","xv","xvi"]
# Paper-2 sometimes continues the sequence (ix..xvi) -> fold back to 1..8
ROMAN = {r: str(n % 8 or 8) for n, r in enumerate(_R, 1)}
_R20 = _R + ["xvii", "xviii", "xix", "xx"]
ITEM = re.compile(r"^\s*\(\s*(" + "|".join(sorted(_R20, key=len, reverse=True)) +
                  r")\s*\)\s*(.*)$", re.I)
RHDR = re.compile(r"^\s*(" + "|".join(sorted(_R, key=len, reverse=True)) + r")\s*[.)]\s*(.*)$")
QHDR = re.compile(r"^\s*(?:Q\s*\.?\s*([1-8])\s*[.)]?|([1-8])\s*[.)]|([1-8])\s+(?=\(|[a-fA-F]\s*\)))\s*(.*)$")
SUBP = re.compile(r"^\s*(?:[1-8]\s*\.?\s+|[1-8]\s*\.\s*)?"
                  r"(?:\(\s*([a-fA-F])\s*\)|([a-fA-F])\s*\)\s*\.?|([a-fA-F])\s*\.)"
                  r"\s*(.*)$")
MAPSTEM = re.compile(r"outline map|mark the location|places marked on the map|"
                     r"identify the following places", re.I)
SUBN = re.compile(r"^\s*([1-6])\s*[.)]\s+(.*)$")
SUBPR = re.compile(r"^\s*\(\s*(viii|vii|vi|iv|iii|ii|i|v)\s*\)\s*(.*)$", re.I)
SUBR = re.compile(r"^\s*(VIII|VII|VI|IV|III|II|I|V)\s*[.)]\s+(.*)$")
R2L = {r: "abcdefgh"[i] for i, r in enumerate(
    ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"])}
LETTERS = "abcdef"
N2L = {str(i + 1): c for i, c in enumerate(LETTERS)}


def clean(text):
    text = re.sub(r"\s+", " ", text).strip()
    marks = None
    for pat in (r"\(\s*(\d{1,2})\s*m\s*\)\s*$",
                r"\(\s*(\d{1,2})\s*marks?\s*\)\s*\.?\s*$",
                r"\b(\d{1,2})\s*marks?\s*\.?\s*$",
                r"[\s.]\b(10|15|20)\s*$"):
        m = re.search(pat, text, re.I)
        if m and int(m.group(1)) in (10, 15, 20):
            marks = int(m.group(1)); text = text[:m.start()].strip(); break
    text = re.sub(r"\s*\(?\d{1,2}\s*[x*]\s*\d{1,2}\s*[-=]\s*\d{2,3}.*$", "", text, flags=re.I).strip()
    text = text.strip(" .,:;-")
    if text and text[-1] not in ".?\"'":
        text += "."
    return text, marks


papers = []
for b in blocks:
    body = b["lines"]
    q_pref = {m.group(1) for m in
              (re.match(r"^\s*Q\s*\.?\s*([1-8])", l) for l in body) if m}
    n_digit = sum(1 for l in body if re.match(r"^\s*(?:Q\s*\.?\s*)?[1-8]\s*[.):]", l))
    uses_roman = sum(1 for l in body if RHDR.match(l)) >= 4 and n_digit < 4

    qs, qnum, sub, buf = [], None, None, []
    expect_q, expect_s = 1, 0
    map_mode = False

    def flush():
        global buf
        if qnum and sub and buf:
            text, marks = clean(" ".join(buf))
            stem_only = re.fullmatch(
                r"(?:answer|write|comment on|write notes on)\b[^.?]{0,90}"
                r"(?:150|250)?\s*words?[^.?]{0,30}\.?", text, re.I)
            if len(text) > 3 and not text.strip(". ").isdigit() and not stem_only:
                qs.append({"question_number": f"{qnum}{sub}",
                           "section_ref": "Section A" if int(qnum) <= 4 else "Section B",
                           "question_type": "descriptive",
                           "is_compulsory": qnum in ("1", "5"),
                           "marks": marks,
                           "marks_inferred": 10 if qnum in ("1", "5") else (20 if sub == "a" else 15),
                           "marks_source": "printed" if marks is not None else "inferred",
                           "word_limit": 150 if qnum in ("1", "5") else None,
                           "parent_question_number": qnum,
                           "question_text": text,
                           "_ord": len(qs),
                           "map_item": bool(sub and "(" in sub),
                           "options": None, "correct_option": None})
        buf = []

    def take_sub(letter, rest):
        global sub, expect_s, buf
        idx = LETTERS.index(letter)
        if idx < expect_s:
            return False
        flush(); sub = letter; expect_s = idx + 1; buf = [rest]
        return True

    def take_next(rest):
        """A marker of a different style: take the next letter in sequence."""
        global sub, expect_s, buf
        if expect_s >= len(LETTERS):
            return False
        flush(); sub = LETTERS[expect_s]; expect_s += 1; buf = [rest]
        return True

    def open_q(num, rest):
        global qnum, expect_q, expect_s, sub, buf, map_mode
        flush(); qnum = num; expect_q = int(num) + 1; expect_s = 0; map_mode = False
        ms = SUBP.match(rest)
        if ms:
            letter = (ms.group(1) or ms.group(2) or ms.group(3)).lower()
            if take_sub(letter, ms.group(4)):
                return
        sub, buf = None, []

    for ln in body:
        if uses_roman:
            mr = RHDR.match(ln)
            if mr and int(ROMAN[mr.group(1).lower()]) >= expect_q:
                open_q(ROMAN[mr.group(1).lower()], mr.group(2)); continue
        mh = QHDR.match(ln)
        qn = (mh.group(1) or mh.group(2) or mh.group(3)) if mh else None
        if qn and mh.group(1) is None and (qn in q_pref or uses_roman):
            qn = None                      # bare N. is a sub-part here
        if qn and int(qn) >= expect_q:
            open_q(qn, mh.group(4)); continue
        ms = SUBP.match(ln)
        if ms:
            letter = (ms.group(1) or ms.group(2) or ms.group(3)).lower()
            if take_sub(letter, ms.group(4)):
                continue
        if buf and MAPSTEM.search(" ".join(buf)):
            map_mode = True
        # inside a map list, numbered/roman entries are locations, not sub-parts
        if map_mode and qnum:
            mm = re.match(r"^\s*(?:\(?\s*([ivx]{1,5}|\d{1,2})\s*[).])\s+(.*)$", ln, re.I)
            if mm and mm.group(2).strip():
                flush()
                base = sub.split("(")[0] if sub else ""
                sub = f"{base}({mm.group(1).lower()})"
                buf = [mm.group(2)]
                continue
        mi = ITEM.match(ln)
        if mi and qnum and sub is None:
            flush(); sub = "(" + mi.group(1).lower() + ")"; buf = [mi.group(2)]
            continue
        if mi and qnum and sub and sub.startswith("("):
            flush(); sub = "(" + mi.group(1).lower() + ")"; buf = [mi.group(2)]
            continue
        mpr = SUBPR.match(ln)
        if mpr and qnum and sub is not None and take_next(mpr.group(2)):
            continue
        mr2 = SUBR.match(ln)
        if mr2 and qnum and take_sub(R2L[mr2.group(1)], mr2.group(2)):
            continue
        mn = SUBN.match(ln)
        if mn and qnum and take_sub(N2L[mn.group(1)], mn.group(2)):
            continue
        if sub is not None:
            buf.append(ln)
    flush()

    seen, dedup = set(), []
    for q in qs:
        if q["question_number"] in seen:
            continue
        seen.add(q["question_number"]); dedup.append(q)
    dedup.sort(key=lambda q: (int(q["parent_question_number"]), q["_ord"]))
    for i, q in enumerate(dedup, 1):
        q["display_order"] = i
        q.pop("_ord", None)
        if q["map_item"]:
            q["marks"], q["marks_inferred"], q["marks_source"] = None, None, "unknown"
            q["question_format"] = "map_identification_item"

    papers.append({"paper_code": f"UPSC-CSM-{b['year']}-{CODE}-P{b['pno']}",
                   "exam_slug": "upsc-cse", "exam_cycle_year": b["year"],
                   "optional_subject": SUBJECT, "paper_number": b["pno"],
                   "max_marks": 250, "duration_minutes": 180, "languages": ["en"],
                   "source_type": "aggregator", "source_url": None,
                   "source_document_id": PDF.split("/")[-1],
                   "source_publisher": "LotusArise IAS",
                   "trust_status": "pending", "internal_header_verified": None,
                   "questions": dedup})

papers.sort(key=lambda p: (-p["exam_cycle_year"], p["paper_number"]))
years = sorted({p["exam_cycle_year"] for p in papers})
out = {"extraction_meta": {
    "extracted_on": "2026-09-05", "source_file": PDF.split("/")[-1],
    "optional_subject": SUBJECT,
    "years_covered": f"{years[0]}-{years[-1]}" if years else None,
    "capture_method": "pdftotext_layout_parse",
    "section_ref_derivation": "derived from question number (Q1-4 = Section A, Q5-8 = Section B)",
    "marks_note": "marks = printed in source (null if absent); marks_inferred = UPSC structural rule; marks_source flags which",
    "language_coverage": ["en"], "hindi_present": False,
    "verified_against_official": False},
    "papers": papers}
dst = f"/home/claude/psir/upsc-{CODE.lower()}-pyq.json"
json.dump(out, open(dst, "w"), indent=2, ensure_ascii=False)

exp = {f"{q}{c}" for q in "15" for c in "abcde"} | {f"{q}{c}" for q in "234678" for c in "abc"}
print(f"{SUBJECT}: {len(papers)} papers, {sum(len(p['questions']) for p in papers)} questions "
      f"(expected {28*len(papers)}) -> {dst}")
for p in papers:
    miss = sorted(exp - {q["question_number"] for q in p["questions"]})
    if miss:
        print(f"  {p['paper_code']}: {len(p['questions'])} | missing {miss}")
