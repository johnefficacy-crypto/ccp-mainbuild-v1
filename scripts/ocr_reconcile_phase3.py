#!/usr/bin/env python3
r"""
ocr_reconcile_phase3.py - Phase 3: OCR-reconcile the newly sourced official
papers (2016, 2017, 2018, 2023 GS1-GS4; 2026 all GS papers).

Fully offline: no DB, no network, no writes to any input. Read-only on the
PDFs, the DB source JSONs and the UnlockIAS extraction JSONs.

CALIBRATED SETUP, UNCHANGED (see ocr_calibration.md / ocr_phase2.md). Nothing
is retuned here:
  - 300 DPI rasterization, tesseract eng only
  - reconcile_gs_sources.strip_legacy_font on the OCR output
  - FULL-TEXT matching (partial_ratio vs the whole OCR paper), not chunked
  - single 85 cut:  >=95 exact | 85-94 variant | <85 orphan
  - low-confidence extraction gate: raw OCR < 1500 tokens OR legacy-font noise
    > 5.0% -> flagged, NOT scored, verdict unverifiable
Every scored row is ocr_derived=true.

IDENTIFICATION (year + paper) comes from the PAPER'S OWN PRINTED CONTENT, never
from the filename. The rule is documented in full at the CLASSIFICATION block
below; in short, the COVER PAGE supplies the examination year and the paper
label, and the UPSC paper-set code printed in every page footer supplies a
second paper vote and groups the four papers of one sitting. A file whose year
OR paper cannot be read from its content is reported as UNCLASSIFIED; it is
never scored and never guessed. The filename is recorded only to show whether
it agrees; it never supplies the answer.

OCR text is cached so re-scoring needs no re-OCR:
    workbench/audit/ocr_cache/phase3_raw/<pdf stem>.txt    (all pages, by file)
    workbench/audit/ocr_cache/phase3_cover/<pdf stem>.txt  (page 1 only)
    workbench/audit/ocr_cache/<year>_<paper>.txt           (canonical, written
                                                            after classification)

OUTPUTS (the only files this script writes)
    workbench/audit/ocr_phase3.md
    workbench/audit/ocr_phase3_verdict.csv
    workbench/audit/repair_worklist.csv   (NEW COLUMNS APPENDED ONLY - existing
                                           columns are copied through verbatim)
"""

import csv
import glob
import json
import os
import re
import shutil
import statistics as st
from collections import Counter, defaultdict

import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from rapidfuzz import fuzz

import reconcile_gs_sources as R

TESS_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(TESS_CMD):
    pytesseract.pytesseract.tesseract_cmd = TESS_CMD

DPI = 300
MATCH_CUT = 85
EXACT_CUT = 95
MIN_RAW_TOKENS = 1500
MAX_NOISE_PCT = 5.0

# misfiling relocation: an orphan that scores >= this against a DIFFERENT
# official paper is evidence of misfiling rather than of invention.
RELOCATE_CUT = 85
# a paper is called MISFILED when at least this share of its questions are
# orphans against their own filed paper.
MISFILE_SHARE = 50.0

NEW_SRC = r"D:\Users\user\Downloads\upsc-mains"
UNLOCK = r"D:\Users\user\Downloads\unlockias-json"
DB_YEARS = ("2016", "2017", "2018", "2023")
UNLOCK_YEARS = ("2016", "2017", "2018", "2023", "2026")

OUT_DIR = R.OUT_DIR
CACHE_DIR = os.path.join(OUT_DIR, "ocr_cache")
RAW_CACHE = os.path.join(CACHE_DIR, "phase3_raw")
COVER_CACHE = os.path.join(CACHE_DIR, "phase3_cover")
OUT_MD = os.path.join(OUT_DIR, "ocr_phase3.md")
OUT_CSV = os.path.join(OUT_DIR, "ocr_phase3_verdict.csv")
WORKLIST = os.path.join(OUT_DIR, "repair_worklist.csv")

ROM = {"I": "GS1", "II": "GS2", "III": "GS3", "IV": "GS4"}

# ----------------------------- OCR + CACHE ----------------------------------


def ocr_pdf(path):
    doc = fitz.open(path)
    mat = fitz.Matrix(DPI / 72.0, DPI / 72.0)
    parts = []
    for page in doc:
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        parts.append(pytesseract.image_to_string(img, lang="eng"))
    doc.close()
    return "\n".join(parts)


def cached_ocr(path):
    os.makedirs(RAW_CACHE, exist_ok=True)
    stem = os.path.splitext(os.path.basename(path))[0]
    cache = os.path.join(RAW_CACHE, stem + ".txt")
    if os.path.exists(cache):
        with open(cache, encoding="utf-8") as fh:
            return fh.read()
    txt = ocr_pdf(path)
    with open(cache, "w", encoding="utf-8") as fh:
        fh.write(txt)
    return txt


def cached_cover(path):
    """OCR of page 1 only - the cover page that carries the exam header."""
    os.makedirs(COVER_CACHE, exist_ok=True)
    stem = os.path.splitext(os.path.basename(path))[0]
    cache = os.path.join(COVER_CACHE, stem + ".txt")
    if os.path.exists(cache):
        with open(cache, encoding="utf-8") as fh:
            return fh.read()
    doc = fitz.open(path)
    pix = doc[0].get_pixmap(matrix=fitz.Matrix(DPI / 72.0, DPI / 72.0))
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    txt = pytesseract.image_to_string(img, lang="eng")
    doc.close()
    with open(cache, "w", encoding="utf-8") as fh:
        fh.write(txt)
    return txt


# --------------------------- CLASSIFICATION ---------------------------------
#
# Year and paper are read from the paper's OWN PRINTED CONTENT. Three printed
# tokens are used, all of them things a human reads off the cover:
#
#   (a) the COVER-PAGE examination header  ("Civil Services (Main) Examination,
#       2026", "CS (MAIN) Exam;2016", "CIVIL SERVICES (MAIN)EXAM- 2023").
#       ONLY page 1 is searched for the year: later pages carry years inside the
#       question text ("Budget 2017-18", "Act, 2016", "1917") which would
#       otherwise outvote the header.
#   (b) the COVER-PAGE paper label, English ("GENERAL STUDIES (PAPER-III)",
#       "Paper IV") and the Hindi label's trailing numeral, which OCR renders
#       with I/l/1 look-alikes ("(TIA-TA-1)" -> I, "(aea-ca 11)" -> II,
#       "(MI1-Wa-II1)" -> III, "(WI-WA-IV)" -> IV). A parenthesis group that
#       contains the word PAPER is the English label and is not counted twice.
#   (c) the UPSC paper-set code printed in the page footer of every page
#       ("M-ESC-O-GSA", "SKYC-G-GST", "KVMS-G-GSD"). Its PREFIX is constant
#       across the four papers of one sitting and is used to group them. Its
#       TRAILING SUFFIX does NOT vote on the paper: A-GS1/B-GS2/C-GS3/D-GS4 is
#       year-specific, not a UPSC convention (2017's STH-G-GSD is the GS2
#       paper). The suffix is applied later, per sitting, and only where that
#       sitting's own codes validate the mapping - see apply_code_suffix().
#
# Paper = strict winner of the printed-label vote (English label 2, Hindi
# numeral 2). A tie is NOT resolved - the file is left UNCLASSIFIED.
# Year  = the file's own cover-page year; if OCR mangled it (e.g. "2083"), the
# year printed on the cover of another file carrying the SAME paper-set code,
# but only when every readable member of that group prints the same year.
# Two files in one group resolving to the same paper is a conflict and both are
# dropped. Nothing is inferred from the filename, ever.

YEAR_ANCHORED = re.compile(
    r"(?:EXAM[A-Z]*|CIVIL\s+SERVICES|CS\s*\(MAIN\))[^0-9]{0,40}((?:19|20)\d\d)")
YEAR_ANY = re.compile(r"(?<!\d)((?:19|20)\d\d)(?!\d)")

PAPER_LABEL = re.compile(
    r"GENERAL\s*STUDIES[^A-Z0-9]{0,12}\(?\s*PAPER\s*[\-\s]*(IV|III|II|I)\b")
PAPER_LABEL2 = re.compile(r"\bPAPER\s*[\-\s]*(IV|III|II|I)\b")
PAREN = re.compile(r"\(([^()]{2,24})\)")
# strict code: the trailing letter is trusted only when it is literally A-D
CODE_STRICT = re.compile(r"([A-Z0-9]{2,5})[ \-]{1,3}[GO][ \-]{1,3}GS([ABCD])(?![A-Z0-9])")
# loose code: prefix only, tolerating OCR junk inside "GS" (e.g. "EGT-G-G8SD")
CODE_LOOSE = re.compile(r"([A-Z0-9]{2,5})[ \-]{1,3}[GO0][ \-]{1,3}G[ 0-9]?S[A-Z0-9]{1,2}")
CODE_TO_PAPER = {"A": "GS1", "B": "GS2", "C": "GS3", "D": "GS4"}

ROMAN_NUM = {"1": "GS1", "11": "GS2", "111": "GS3", "1V": "GS4"}


def _hindi_paper_votes(cover_u):
    """Trailing numeral of the Hindi paper label, OCR look-alikes normalised."""
    votes = Counter()
    for m in PAREN.finditer(cover_u):
        inner = m.group(1).strip()
        if "PAPER" in inner:                 # that is the English label
            continue
        tok = re.split(r"[-\s]+", inner)[-1]
        n = re.sub(r"[IL|!]", "1", tok)
        if n in ROMAN_NUM:
            votes[ROMAN_NUM[n]] += 1
    return votes


def classify(cover_text, full_text):
    """Return (year, paper, code_prefix, evidence) from printed content only."""
    cu = re.sub(r"\s+", " ", cover_text.upper())
    fu = re.sub(r"\s+", " ", full_text.upper())

    # --- year: cover page only
    year, ysrc = None, "none"
    hits = [y for y in YEAR_ANCHORED.findall(cu) if "2000" <= y <= "2030"]
    if hits:
        c = Counter(hits).most_common()
        if len(c) == 1 or c[0][1] > c[1][1]:
            year, ysrc = c[0][0], "cover header"
    if year is None:
        cand = set(y for y in YEAR_ANY.findall(cu) if "2000" <= y <= "2030")
        if len(cand) == 1:
            year, ysrc = cand.pop(), "cover (sole year token)"

    # --- paper-set code
    strict = Counter(m.groups() for m in CODE_STRICT.finditer(fu))
    loose = Counter(m.group(1) for m in CODE_LOOSE.finditer(fu))
    prefix = loose.most_common(1)[0][0] if loose else None
    letter = strict.most_common(1)[0][0][1] if strict else None

    # --- paper: vote over the PRINTED LABELS ONLY.
    # The code suffix deliberately does not vote here - see CODE SUFFIX below.
    pv = Counter()
    for m in PAPER_LABEL.finditer(cu):
        pv[ROM[m.group(1)]] += 2
    if not PAPER_LABEL.search(cu):
        for m in PAPER_LABEL2.finditer(cu):
            pv[ROM[m.group(1)]] += 2
    for p, n in _hindi_paper_votes(cu).items():
        pv[p] += 2 * min(n, 1)
    paper = None
    if pv:
        top = pv.most_common()
        if len(top) == 1 or top[0][1] > top[1][1]:
            paper = top[0][0]
    return year, paper, prefix, letter, {
        "year_src": ysrc, "paper_votes": dict(pv), "letter": letter or "",
        "code": "%s-GS%s" % (prefix or "?", letter or "?")}


def resolve_groups(inventory):
    """Fill a missing year from the paper-set-code group; flag paper conflicts."""
    groups = defaultdict(list)
    for i in inventory:
        if i["prefix"]:
            groups[i["prefix"]].append(i)
    for prefix, members in groups.items():
        years = set(m["year"] for m in members if m["year"])
        if len(years) == 1:
            y = years.pop()
            for m in members:
                if not m["year"]:
                    m["year"] = y
                    m["ev"]["year_src"] = "paper-set code %s (group)" % prefix
        elif len(years) > 1:
            for m in members:
                m["ev"]["year_src"] += " [group disagrees: %s]" % sorted(years)
        apply_code_suffix(prefix, members)

        claimed = Counter(m["paper"] for m in members if m["paper"])
        for m in members:
            if m["paper"] and claimed[m["paper"]] > 1:
                m["ev"]["conflict"] = ("two files in paper-set %s both resolve "
                                       "to %s" % (prefix, m["paper"]))
                m["paper"] = None


def apply_code_suffix(prefix, members):
    """Use the code suffix only where the SITTING ITSELF validates the mapping.

    A-GS1 / B-GS2 / C-GS3 / D-GS4 is NOT a universal UPSC convention - it is
    year-specific. 2017's set runs STH-G-GSO / GSD / GST / GSF, and STH-G-GSD is
    the GS2 paper, so a blanket suffix->paper vote would call it GS4. The suffix
    therefore no longer votes in classify(); it is applied here, and only when
    this sitting's own codes prove the mapping holds for this sitting:

      * every member whose suffix OCR'd cleanly as A-D has a distinct suffix,
      * at least two members were identified independently from their printed
        labels and agree with what their suffix would say, and
      * those agreements outnumber any disagreement.

    A majority, not unanimity: a single misread label glyph must not be able to
    veto the whole sitting. 2026's labels are A->GS1, B->GS2, D->GS4 agreeing
    and C->GS1 disagreeing, because the GS3 cover's Hindi numeral OCR'd as "1";
    3-to-1 validates the scheme and the suffix then corrects that one file.
    2017 offers exactly one pairing, D on a GS2 paper, which agrees with
    nothing - so that sitting's suffixes are ignored entirely.

    Where the scheme is validated the suffix is the stronger identifier - it is
    printed in every page footer and read 5-12 times, against a label read once
    - so it may settle members whose label was unreadable AND correct a member
    whose single label glyph was misread. Where it is not, the suffixes are
    ignored for the whole group and the labels stand alone.
    """
    lettered = [m for m in members if m.get("letter")]
    if not lettered:
        return
    letters = [m["letter"] for m in lettered]
    if len(set(letters)) != len(letters):
        for m in members:
            m["ev"]["code_suffix"] = "ignored: %s repeats a suffix" % prefix
        return
    pairs = [(m["letter"], m["paper"]) for m in lettered if m["paper"]]
    if not pairs:
        for m in members:
            m["ev"]["code_suffix"] = ("ignored: no label-identified member in %s "
                                      "to validate the mapping against" % prefix)
        return
    agree = [(l, p) for l, p in pairs if CODE_TO_PAPER[l] == p]
    disagree = [(l, p) for l, p in pairs if CODE_TO_PAPER[l] != p]
    if len(agree) < 2 or len(agree) <= len(disagree):
        for m in members:
            m["ev"]["code_suffix"] = (
                "ignored: %s suffix scheme is not corroborated as A-D->GS1-GS4 "
                "(%d agree, %d disagree%s)"
                % (prefix, len(agree), len(disagree),
                   "; suffix %s sits on a %s paper" % disagree[0]
                   if disagree else ""))
        return
    for m in lettered:
        want = CODE_TO_PAPER[m["letter"]]
        if m["paper"] == want:
            m["ev"]["code_suffix"] = "confirms %s" % want
        else:
            m["ev"]["code_suffix"] = (
                "set %s from suffix %s (group-validated); label vote said %s"
                % (want, m["letter"], m["paper"] or "nothing"))
            m["paper"] = want


# ----------------------------- SCORING --------------------------------------


def paper_metrics(raw):
    ascii_t = R.ascii_only(raw)
    filt, removed = R.strip_legacy_font(ascii_t)
    raw_tokens = len(raw.split())
    eng_words = R.english_word_count(filt)
    noise = (100.0 * removed / len(ascii_t)) if ascii_t else 100.0
    reasons = []
    if raw_tokens < MIN_RAW_TOKENS:
        reasons.append("raw_tokens %d<%d" % (raw_tokens, MIN_RAW_TOKENS))
    if noise > MAX_NOISE_PCT:
        reasons.append("noise %.1f%%>%.1f%%" % (noise, MAX_NOISE_PCT))
    return {"full": R.normalize(filt), "raw_tokens": raw_tokens,
            "eng_words": eng_words, "noise": noise,
            "low_conf": bool(reasons), "reason": "; ".join(reasons)}


def score_one(norm_en, info):
    """(verdict, score) for one question against one paper, else unverifiable."""
    if info is None or info["low_conf"]:
        return "unverifiable", ""
    if len(norm_en) < R.MIN_JSON_EN_LEN:
        return "orphan", ""
    s = round(fuzz.partial_ratio(norm_en, info["full"]), 1)
    return ("exact" if s >= EXACT_CUT
            else "variant" if s >= MATCH_CUT else "orphan"), s


def best_elsewhere(norm_en, papers, own_key):
    """Best score against every OTHER usable official paper -> (score, yr, pp)."""
    if len(norm_en) < R.MIN_JSON_EN_LEN:
        return "", "", ""
    best, by, bp = -1.0, "", ""
    for k, info in papers.items():
        if k == own_key or info["low_conf"]:
            continue
        s = fuzz.partial_ratio(norm_en, info["full"])
        if s > best:
            best, by, bp = s, k[0], k[1]
    return (round(best, 1) if best >= 0 else "", by, bp)


# ------------------------------- MAIN ---------------------------------------


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # 1. OCR + classify every new PDF from its own printed content
    inventory = []      # per-file record
    papers = {}         # (year, paper) -> metrics dict (phase-3 papers only)
    dupes = []
    for path in sorted(glob.glob(os.path.join(NEW_SRC, "*.pdf"))):
        base = os.path.basename(path)
        raw = cached_ocr(path)
        cover = cached_cover(path)
        year, paper, prefix, letter, ev = classify(cover, raw)
        rec = {"file": base, "year": year, "paper": paper, "prefix": prefix,
               "letter": letter,
               "fn_year": R.year_from_filename(base),
               "fn_paper": R.paper_from_text(base), "ev": ev}
        rec.update(paper_metrics(raw))
        inventory.append(rec)

    # 1a. fill a missing year from the printed paper-set code group; drop any
    #     file whose paper collides with another file in the same group
    resolve_groups(inventory)

    for rec in inventory:
        year, paper = rec["year"], rec["paper"]
        if not (year and paper and paper in R.GS_PAPERS):
            continue
        key = (year, paper)
        if key in papers:
            dupes.append((rec["file"], key))
            continue
        papers[key] = rec
        dst = os.path.join(CACHE_DIR, "%s_%s.txt" % (year, paper))
        if not os.path.exists(dst):
            shutil.copyfile(
                os.path.join(RAW_CACHE,
                             os.path.splitext(rec["file"])[0] + ".txt"), dst)

    # 1b. phase-2 cached papers also serve as cross-year relocation targets
    all_papers = dict(papers)
    for c in sorted(glob.glob(os.path.join(CACHE_DIR, "*.txt"))):
        m = re.fullmatch(r"(\d{4})_(GS[1-4])\.txt", os.path.basename(c))
        if not m:
            continue
        key = (m.group(1), m.group(2))
        if key in all_papers:
            continue
        with open(c, encoding="utf-8") as fh:
            all_papers[key] = paper_metrics(fh.read())

    # 2. DB source rows for 2016/2017/2018/2023
    db_rows = []
    for path in sorted(glob.glob(R.SRC_GLOB)):
        for q in R.iter_json_questions(path):
            if q.get("parse_error") or q.get("unrecognised") or not q.get("in_scope"):
                continue
            if q["year"] not in DB_YEARS:
                continue
            key = (q["year"], q["paper"])
            ne = R.normalize(q["en"])
            verdict, s = score_one(ne, papers.get(key))
            other, oy, op = best_elsewhere(ne, all_papers, key)
            db_rows.append([
                "db", q["file"], q["year"], q["paper"], q["qno"], q["local_no"],
                q["global_no"], q["en_len"], verdict, s, other, oy, op, "true",
            ])

    # 3. UnlockIAS extraction for 2016/2017/2018/2023 + 2026
    ul_rows = []
    for year in UNLOCK_YEARS:
        p = os.path.join(UNLOCK, "upsc-mains-%s.json" % year)
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8-sig") as fh:
            data = json.load(fh)
        for u in data:
            paper = u.get("paper")
            if paper not in R.GS_PAPERS:
                continue
            key = (year, paper)
            ne = R.normalize(u.get("question_text", ""))
            verdict, s = score_one(ne, papers.get(key))
            other, oy, op = best_elsewhere(ne, all_papers, key)
            ul_rows.append([
                "unlockias", "upsc-mains-%s.json" % year, year, paper,
                u.get("q_label", ""), u.get("paper_local_number", ""),
                u.get("question_number", ""), len(u.get("question_text", "")),
                verdict, s, other, oy, op, "true",
            ])

    rows = db_rows + ul_rows
    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["source", "file", "year", "paper", "question_number",
                    "paper_local_number", "global_number", "en_len", "verdict",
                    "best_score", "best_other_score", "best_other_year",
                    "best_other_paper", "ocr_derived"])
        w.writerows(rows)

    # 4. repair_worklist.csv - append new columns only
    wl_counts = update_worklist(papers)

    write_report(inventory, papers, dupes, db_rows, ul_rows, wl_counts)
    print("papers classified: %d  db rows: %d  unlockias rows: %d"
          % (len(papers), len(db_rows), len(ul_rows)))
    print("CSV: %s\nMD : %s\nWL : %s" % (OUT_CSV, OUT_MD, WORKLIST))


def update_worklist(papers):
    """Append phase-3 verdict columns to repair_worklist.csv. Never overwrites."""
    with open(WORKLIST, encoding="utf-8-sig") as fh:
        rd = csv.DictReader(fh)
        orig = list(rd)
        fields = list(rd.fieldnames)
    new_cols = ["phase3_db_verdict", "phase3_db_score",
                "phase3_unlockias_verdict", "phase3_unlockias_score"]
    fields_out = fields + [c for c in new_cols if c not in fields]
    counts = Counter()
    for r in orig:
        for c in new_cols:
            r.setdefault(c, "")
        if r["year"] not in DB_YEARS:
            continue
        info = papers.get((r["year"], r["paper"]))
        if (r.get("db_text") or "").strip():
            v, s = score_one(R.normalize(r["db_text"]), info)
            r["phase3_db_verdict"], r["phase3_db_score"] = v, s
            counts[("db", r["year"], v)] += 1
        if (r.get("unlockias_text") or "").strip():
            v, s = score_one(R.normalize(r["unlockias_text"]), info)
            r["phase3_unlockias_verdict"], r["phase3_unlockias_score"] = v, s
            counts[("ul", r["year"], v)] += 1
    with open(WORKLIST, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=fields_out)
        w.writeheader()
        w.writerows(orig)
    return counts


def _dist(scores):
    if not scores:
        return "n=0"
    return ("n=%d min=%.1f med=%.1f max=%.1f"
            % (len(scores), min(scores), st.median(scores), max(scores)))


def _counts_table(L, rows, title):
    by = defaultdict(Counter)
    for r in rows:
        by[(r[2], r[3])][r[8]] += 1
    L += ["", "### " + title, "",
          "| year | paper | exact | variant | orphan | unverifiable | total |",
          "|---|---|---|---|---|---|---|"]
    for k in sorted(by):
        c = by[k]
        L.append("| %s | %s | %d | %d | %d | %d | %d |"
                 % (k[0], k[1], c["exact"], c["variant"], c["orphan"],
                    c["unverifiable"], sum(c.values())))
    return by


def write_report(inventory, papers, dupes, db_rows, ul_rows, wl_counts):
    L = ["# OCR reconciliation - Phase 3 (newly sourced official papers)", ""]
    L.append("Inputs: `%s` (read-only). Calibrated phase-2 setup, not retuned: "
             "300 DPI, tesseract `eng`, `strip_legacy_font`, full-text matching, "
             "single 85 match cut (exact >=95, variant 85-94, orphan <85). Every "
             "scored row is `ocr_derived=true`. Low-confidence extraction (raw "
             "OCR < %d tokens OR legacy-font noise > %.1f%%) is flagged and left "
             "`unverifiable`, never scored and never clean. No DB writes, no "
             "network, no edits to any extraction JSON."
             % (NEW_SRC, MIN_RAW_TOKENS, MAX_NOISE_PCT))
    L.append("")
    L.append("Year and paper are read from each PDF's own printed content. The "
             "**cover page** supplies the examination year and the paper label "
             "(English `GENERAL STUDIES (PAPER-<n>)` and the Hindi label's "
             "trailing numeral); the **UPSC paper-set code** printed in every "
             "page footer (`M-ESC-O-GSA`, `SKYC-G-GST`, `KVMS-G-GSD`) supplies a "
             "second paper vote and groups the four papers of one sitting, so a "
             "cover whose year OCR'd as garbage can take the year printed on its "
             "sitting-mates' covers. Only page 1 is searched for the year: later "
             "pages carry years inside the questions themselves (\"Budget "
             "2017-18\", \"Act, 2016\", \"1917\") which would otherwise "
             "outvote the header. Ties are not resolved and nothing is ever "
             "taken from the filename; the filename column below only records "
             "whether it agrees.")

    # --- 1. inventory / quality
    L += ["", "## 1. Extraction quality per paper", "",
          "| file | content year | year read from | content paper | filename "
          "says | raw tokens | eng words post-strip | noise % | confidence |",
          "|---|---|---|---|---|---|---|---|---|"]
    for i in inventory:
        fn = "%s %s" % (i["fn_year"] or "no year", i["fn_paper"] or "?")
        clash = ((i["fn_year"] and i["year"] and i["fn_year"] != i["year"])
                 or (i["fn_paper"] and i["paper"] and i["fn_paper"] != i["paper"]))
        agree = " **DISAGREES**" if clash else ""
        conf = ("LOW (%s)" % i["reason"]) if i["low_conf"] else "ok"
        L.append("| %s | %s | %s | %s | %s%s | %d | %d | %.1f | %s |"
                 % (i["file"], i["year"] or "**UNREAD**", i["ev"]["year_src"],
                    i["paper"] or "**UNREAD**", fn, agree, i["raw_tokens"],
                    i["eng_words"], i["noise"], conf))
    unclassified = [i for i in inventory if not (i["year"] and i["paper"])]
    low = [i for i in inventory if i["low_conf"]]
    L += ["", "- Files OCR'd: **%d**. Classified from content to a GS paper: "
              "**%d**." % (len(inventory), len(papers))]
    L.append("- Unclassified from content (reported, never guessed, never "
             "scored): **%d**%s." % (
                 len(unclassified),
                 "" if not unclassified else " - " + ", ".join(
                     "`%s` (year=%s, paper=%s)"
                     % (i["file"], i["year"] or "none", i["paper"] or "none")
                     for i in unclassified)))
    L.append("- Failed / low-confidence extractions (flagged, NOT scored): "
             "**%d**%s." % (
                 len(low),
                 "" if not low else " - " + ", ".join(
                     "`%s` [%s]" % (i["file"], i["reason"]) for i in low)))
    if dupes:
        L.append("- Duplicate (year, paper) claims, second copy ignored: "
                 + ", ".join("`%s` -> %s %s" % (b, k[0], k[1]) for b, k in dupes))

    # --- 2. DB scoring
    L += ["", "## 2. DB source rows vs the now-available official papers", ""]
    L.append("Scope: the DB/source GS JSONs for 2016, 2017, 2018 and 2023 "
             "(`UPSCCSEMains*.json`), scored against the official paper for "
             "their own year and paper. Counts are per source ROW, not per "
             "distinct question: 2016 and 2017 are each covered by more than one "
             "source file (e.g. `UPSCCSEMains2016GS2.json` and "
             "`UPSCCSEMains2016APPENDGS1GS2.json`), so a paper carrying 20 "
             "questions can contribute 40 rows.")
    _counts_table(L, db_rows, "Counts by year and paper")
    yc = defaultdict(Counter)
    for r in db_rows:
        yc[r[2]][r[8]] += 1
    L += ["", "### Counts by year", "",
          "| year | exact | variant | orphan | unverifiable | total | score dist |",
          "|---|---|---|---|---|---|---|"]
    for y in sorted(yc):
        c = yc[y]
        sc = [r[9] for r in db_rows if r[2] == y and isinstance(r[9], (int, float))]
        L.append("| %s | %d | %d | %d | %d | %d | %s |"
                 % (y, c["exact"], c["variant"], c["orphan"], c["unverifiable"],
                    sum(c.values()), _dist(sc)))
    tot = Counter()
    for c in yc.values():
        tot.update(c)
    L += ["", "- Total DB rows scored across the four years: **%d** - **%d exact, "
              "%d variant, %d orphan, %d unverifiable**."
              % (sum(tot.values()), tot["exact"], tot["variant"], tot["orphan"],
                 tot["unverifiable"])]
    rel = [r for r in db_rows if r[8] == "orphan"
           and isinstance(r[10], (int, float)) and r[10] >= RELOCATE_CUT]
    L.append("- DB orphans that match a DIFFERENT official paper at >= %d "
             "(misfiled rather than invented): **%d** of %d."
             % (RELOCATE_CUT, len(rel), tot["orphan"]))
    if rel:
        rc = Counter((r[2], r[3], r[11], r[12]) for r in rel)
        for k in sorted(rc):
            L.append("    - %s %s: %d row(s) match %s %s instead"
                     % (k[0], k[1], rc[k], k[2], k[3]))

    # orphan blocks: where the DB text does not appear in the official paper
    ob = defaultdict(list)
    for r in db_rows:
        if r[8] == "orphan" and isinstance(r[9], (int, float)):
            ob[(r[2], r[3])].append(r[9])
    if ob:
        L += ["", "### Orphan blocks (DB text absent from the official paper)", "",
              "| year | paper | orphans | own-score min/med/max | best score vs "
              "any other official paper |", "|---|---|---|---|---|"]
        for k in sorted(ob):
            sc = sorted(ob[k])
            oth = [r[10] for r in db_rows if (r[2], r[3]) == k and r[8] == "orphan"
                   and isinstance(r[10], (int, float))]
            L.append("| %s | %s | %d | %.1f / %.1f / %.1f | %s |"
                     % (k[0], k[1], len(sc), sc[0], st.median(sc), sc[-1],
                        ("%.1f" % max(oth)) if oth else "-"))
        L.append("")
        L.append("A block that is orphan against its own paper AND scores no "
                 "better against any other official paper is not a filing error: "
                 "that text is not in the official corpus at all.")

    # --- 3. UnlockIAS trust test
    L += ["", "## 3. UnlockIAS extraction vs the same official papers (trust test)", ""]
    L.append("Same thresholds. A paper is **MISFILED** when at least %.0f%% of its "
             "UnlockIAS questions are orphans against the official paper they are "
             "filed under, **TRUSTED** when it has zero orphans, **PARTIAL** in "
             "between. Orphans scoring >= %d against another official paper are "
             "reported as relocations - that is what misfiling looks like."
             % (MISFILE_SHARE, RELOCATE_CUT))
    by_ul = _counts_table(L, [r for r in ul_rows if r[2] in DB_YEARS],
                          "Counts by year and paper (2016/2017/2018/2023)")
    L += ["", "### Per-paper trust line", "",
          "| year | paper | questions | exact | variant | orphan | orphan % | "
          "relocates to | verdict |",
          "|---|---|---|---|---|---|---|---|---|"]
    trust = {}
    for key in sorted(by_ul):
        c = by_ul[key]
        n = sum(c.values())
        if c["unverifiable"] == n:
            trust[key] = "UNVERIFIABLE"
            L.append("| %s | %s | %d | - | - | - | - | - | **UNVERIFIABLE** "
                     "(no usable official paper) |" % (key[0], key[1], n))
            continue
        share = 100.0 * c["orphan"] / n if n else 0.0
        orp = [r for r in ul_rows if (r[2], r[3]) == key and r[8] == "orphan"]
        relo = Counter("%s %s" % (r[11], r[12]) for r in orp
                       if isinstance(r[10], (int, float)) and r[10] >= RELOCATE_CUT)
        v = ("TRUSTED" if c["orphan"] == 0
             else "MISFILED" if share >= MISFILE_SHARE else "PARTIAL")
        trust[key] = v
        rel_s = ", ".join("%s x%d" % (k2, n2) for k2, n2 in relo.most_common(3)) or "-"
        L.append("| %s | %s | %d | %d | %d | %d | %.0f%% | %s | **%s** |"
                 % (key[0], key[1], n, c["exact"], c["variant"], c["orphan"],
                    share, rel_s, v))
    L += ["", "### Per-year trust line", ""]
    for y in DB_YEARS:
        ks = sorted(k for k in trust if k[0] == y)
        if not ks:
            L.append("- **%s: UNVERIFIABLE** - no UnlockIAS GS rows." % y)
            continue
        vs = set(trust[k] for k in ks)
        yv = ("TRUSTED" if vs == {"TRUSTED"}
              else "UNVERIFIABLE" if vs == {"UNVERIFIABLE"}
              else "MISFILED" if vs == {"MISFILED"} else "MIXED")
        L.append("- **%s: %s** - %s." % (
            y, yv, ", ".join("%s %s" % (k[1], trust[k]) for k in ks)))

    # --- 4. 2026
    L += ["", "## 4. 2026 - UnlockIAS only (the DB holds no 2026 Mains paper)", ""]
    r26 = [r for r in ul_rows if r[2] == "2026"]
    db26 = [r for r in db_rows if r[2] == "2026"]
    L.append("Nothing to reconcile on the DB side: the source JSONs contribute "
             "**%d** in-scope 2026 GS rows. The UnlockIAS 2026 extraction is "
             "scored against the official 2026 papers below." % len(db26))
    by26 = _counts_table(L, r26, "2026 counts by paper")
    L += ["", "| paper | questions | exact | variant | orphan | orphan % | verdict |",
          "|---|---|---|---|---|---|---|"]
    safe, any26 = True, False
    for key in sorted(by26):
        c = by26[key]
        n = sum(c.values())
        any26 = True
        if c["unverifiable"] == n:
            L.append("| %s | %d | - | - | - | - | **UNVERIFIABLE** |" % (key[1], n))
            safe = False
            continue
        share = 100.0 * c["orphan"] / n if n else 0.0
        v = ("TRUSTED" if c["orphan"] == 0
             else "MISFILED" if share >= MISFILE_SHARE else "PARTIAL")
        if v != "TRUSTED":
            safe = False
        L.append("| %s | %d | %d | %d | %d | %.0f%% | **%s** |"
                 % (key[1], n, c["exact"], c["variant"], c["orphan"], share, v))
    orp26 = sorted((r[3], r[5], r[9]) for r in r26 if r[8] == "orphan")
    if orp26:
        L += ["", "Orphan questions (UnlockIAS 2026, best score vs the official "
              "paper they are filed under):", ""]
        for pp, ln, sc in orp26:
            L.append("- %s local Q%s - %.1f" % (pp, ln, sc))
    L += ["", ("- **Safe to load: YES** - every 2026 UnlockIAS question has a "
               ">=85 counterpart in the official 2026 paper it is filed under."
               if (safe and any26) else
               "- **Safe to load: NO** - at least one 2026 paper is not clean "
               "against the official paper it is filed under (see the table). "
               "Loading it as-is would import unverified rows.")]

    # --- 5. worklist
    L += ["", "## 5. repair_worklist.csv update", ""]
    L.append("Four columns were **appended**; every original column, including "
             "`source_confidence`, is copied through unchanged: "
             "`phase3_db_verdict`, `phase3_db_score`, `phase3_unlockias_verdict`, "
             "`phase3_unlockias_score`.")
    L.append("")
    L.append("Scope note: no worklist row carries `source_confidence = "
             "unverifiable`. The unverifiable class in this file is spelled "
             "`aggregator-only`, and in 2016/2017/2018/2023 every row carries it. "
             "Those are the rows given a phase-3 verdict.")
    L += ["", "| year | scored text | exact | variant | orphan | unverifiable |",
          "|---|---|---|---|---|---|"]
    for y in DB_YEARS:
        for src, lab in (("db", "db_text"), ("ul", "unlockias_text")):
            c = dict((v, wl_counts[(src, y, v)]) for v in
                     ("exact", "variant", "orphan", "unverifiable"))
            if not sum(c.values()):
                continue
            L.append("| %s | %s | %d | %d | %d | %d |"
                     % (y, lab, c["exact"], c["variant"], c["orphan"],
                        c["unverifiable"]))
    L.append("")
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))


if __name__ == "__main__":
    main()
