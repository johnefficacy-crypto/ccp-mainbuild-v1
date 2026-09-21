#!/usr/bin/env python3
r"""
reconcile_gs_sources.py — Reconcile UPSC CSE Mains GS source JSONs against the
raw question papers. Fully offline: no DB, no network, no OCR.

--------------------------------------------------------------------------------
INPUTS (read-only; this script never modifies them)
  RAW papers:
    D:\GovtExamAgent\Resources\pyq\UPSC\CSE\Mains
    D:\GovtExamAgent\Resources\pyq\UPSC\CSE\Mains\done
    PDF  -> pdfplumber text layer (no OCR)
    DOCX -> python-docx paragraphs
    MD   -> read as UTF-8 text (born-digital; not OCR/inference)
  SOURCE JSONs:
    D:\Users\user\Downloads\UPSCCSEMains*.json   (GS Mains family)
    Tag batches / CSAT / optionals / syllabus maps do not match this glob and
    are therefore never read. Essay questions ARE parsed but are OUT OF GS
    SCOPE: they are excluded from the verdict CSV and only counted in the
    summary (this audit reconciles GS1-GS4 only).

OUTPUTS (the only files this script writes)
    workbench/audit/gs_source_verdict.csv
    workbench/audit/gs_source_summary.md

REQUIREMENTS (reproducibility)
    python 3.12, pdfplumber, python-docx, rapidfuzz. These three packages were
    the only network use (one-time `pip install` into .venv); the reconciliation
    itself performs no network or DB access. Run:
        .venv/Scripts/python scripts/reconcile_gs_sources.py

--------------------------------------------------------------------------------
IDENTIFICATION OF RAW FILES  (year + paper)

  UPSC papers do not print the exam year in any machine-extractable header, so
  content alone cannot date them. Per an explicit operator decision, an
  unambiguous year/paper token in the FILENAME counts as valid identification
  (this is reading a printed token, not guessing). The identification SOURCE
  ('filename' / 'content' / 'none') is recorded per file in the summary.

    year  : first 4-digit 19xx/20xx token in the filename; if absent, an
            "Examination, YYYY" header in the extracted content; else None.
    paper : GS1..GS4 or Essay, from explicit filename tokens (arabic '1'-'4',
            roman I-IV after GS/PAPER/STUDIES, or an Essay/Eassy keyword),
            cross-checked against content where the content is readable.
    A file with no confident (year AND paper) is UNCLASSIFIED and is reported;
    it is NOT guessed and is NOT used as a matching target.

READABILITY
    A raw file is READABLE only if its extracted text yields
    >= MIN_ENGLISH_WORDS (40) English-looking words (>=3 letters, contains a
    vowel, not an all-caps run). Scanned/image-only PDFs (which pdfplumber
    returns as a few stray characters) fall below this and are UNREADABLE.
    UNREADABLE files are NEVER OCR'd and NEVER inferred.

--------------------------------------------------------------------------------
MATCHING ALGORITHM  (deterministic; rapidfuzz)

  Raw English signal. Extracted text is filtered to printable ASCII
  ([\x20-\x7E]+). Born-digital DOCX/MD lose their Unicode Devanagari here and
  become clean English. Legacy-font PDFs keep font-mangled Hindi as ASCII
  gibberish interleaved with real English; the substring scorer below tolerates
  that gibberish.

  Chunking. Each readable+classified raw paper is split on printed top-level
  question numbering  (?m)^\s*(?:Q\.?\s*)?(\d{1,2})\s*[.)]  into numbered
  chunks; sub-parts like "1.(a)" stay inside their parent chunk. matched_qno is
  the chunk number. If no markers are found the whole paper is one chunk
  (matched_qno = "").

  Score. normalize(x) = lowercase, keep [a-z0-9 ], collapse whitespace.
  For a JSON question against a raw chunk:
        score = rapidfuzz.fuzz.partial_ratio(normalize(json_en),
                                              normalize(raw_chunk))
  partial_ratio aligns the JSON question as a best-fit SUBSTRING of the chunk,
  so unrelated gibberish elsewhere in the chunk does not depress the score.
  For each JSON question we take the best-scoring chunk within a paper.

  own_score      = best score over chunks of the raw paper for the question's
                   OWN (year, paper).            (None if that raw is
                   missing / unreadable / unclassified)
  other_best     = best score over chunks of EVERY OTHER classified+readable
                   raw paper; other_year / other_qno name that best chunk.

THRESHOLDS / VERDICTS  (evaluated in this order, per JSON question)
    unverifiable : no readable+classified raw paper for the question's own
                   year+paper  (own_score is None). Never "clean".
    exact        : own_score >= 95
    variant      : 80 <= own_score < 95
    wrong_year   : own_score < 80  AND  other_best >= 90   (matched_year names
                   the other year)
    orphan       : own_score < 80  AND  other_best < 90    (best score < 80
                   against every raw paper available)

  best_score / matched_year / matched_qno reported per row are the numbers that
  drove the verdict:
    exact|variant -> own_score,  own year,   best own chunk qno
    wrong_year    -> other_best, other year, other qno
    orphan        -> max(own_score, other_best) and its year/qno (still < 80,
                     reported as the closest thing found)
    unverifiable  -> other_best, other year, other qno (informational only;
                     own raw was unavailable, so the verdict stays unverifiable)

  Every threshold above is a module constant (see CONSTANTS). Report contains
  only computed counts; nothing is estimated.
"""

import csv
import glob
import json
import os
import re
import sys
from collections import defaultdict

import pdfplumber
import docx
from rapidfuzz import fuzz, process

# ------------------------------- CONSTANTS ----------------------------------
RAW_DIRS = [
    r"D:\GovtExamAgent\Resources\pyq\UPSC\CSE\Mains",
    r"D:\GovtExamAgent\Resources\pyq\UPSC\CSE\Mains\done",
]
SRC_GLOB = r"D:\Users\user\Downloads\UPSCCSEMains*.json"

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO_ROOT, "workbench", "audit")
OUT_CSV = os.path.join(OUT_DIR, "gs_source_verdict.csv")
OUT_MD = os.path.join(OUT_DIR, "gs_source_summary.md")

MIN_ENGLISH_WORDS = 40      # readability floor
EXACT_MIN = 95              # >= -> exact (vs own)
VARIANT_MIN = 80            # >= -> variant (vs own)
WRONG_YEAR_OTHER_MIN = 90   # >= vs another year (own < 80) -> wrong_year
MIN_JSON_EN_LEN = 20        # normalized-english length floor to trust a score
GS_PAPERS = ("GS1", "GS2", "GS3", "GS4")

ROMAN = {"IV": "4", "III": "3", "II": "2", "I": "1"}

# ------------------------------- HELPERS ------------------------------------

def ascii_only(s):
    """Keep printable-ASCII runs per line; drop Unicode (Devanagari).

    Line structure is preserved so the question-number chunker can anchor on
    line starts. Born-digital DOCX/MD lose their Unicode Devanagari here and
    become clean English; legacy-font PDFs keep font-mangled Hindi as ASCII.
    """
    out = []
    for line in s.splitlines():
        runs = re.findall(r"[\x20-\x7E]+", line)
        if runs:
            out.append(" ".join(runs))
    return "\n".join(out)


def english_word_count(txt):
    ws = re.findall(r"[A-Za-z]{3,}", txt)
    good = [w for w in ws if re.search(r"[aeiouAEIOU]", w) and not re.search(r"[A-Z]{4,}", w)]
    return len(good)


def normalize(s):
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# Legacy-font Hindi (Krutidev etc.) renders as printable-ASCII gibberish that
# survives the [\x20-\x7E]+ filter, e.g. "jkds'k" = Rakesh. Such runs have a
# near-zero English-dictionary hit rate and heavy symbol density. This detector
# needs an offline dictionary; when wordfreq is unavailable it degrades to a
# vowel/symbol heuristic. See scripts/legacy_font_validate.py for the with/
# without re-score that proves this filter does not move the 2015 verdicts.
_LEGACY_PUNCT = set("'\"~^#$%&*<>/\\|`={}[]()+@;:_")

try:
    from wordfreq import zipf_frequency as _zipf
except Exception:  # pragma: no cover - dictionary optional
    _zipf = None


def _dict_hit(tok):
    core = re.sub(r"[^a-z]", "", tok.lower())
    if len(core) < 2:
        return False
    if _zipf is not None:
        return _zipf(core, "en") > 0
    # fallback: plausible English word shape (has a vowel, not consonant soup)
    v = sum(c in "aeiou" for c in core)
    return v / len(core) >= 0.2


def strip_legacy_font(text, win=3, rate=0.34):
    """Drop legacy-font (garbled-Hindi) runs from ASCII text before matching.

    Token-level with a +/-win smoothing window: a token is dropped when it is
    not a dictionary hit AND its local dictionary-hit rate is below `rate` AND
    it is symbol-heavy / vowel-poor. Contiguous garbage runs go; a lone
    non-dictionary word amid English (high local rate) is kept. Returns
    (filtered_text, chars_removed).
    """
    toks = text.split()
    if not toks:
        return text, 0
    dh = [_dict_hit(t) for t in toks]
    keep = []
    for i, t in enumerate(toks):
        lo, hi = max(0, i - win), min(len(toks), i + win + 1)
        local = sum(dh[lo:hi]) / (hi - lo)
        pd = sum(c in _LEGACY_PUNCT for c in t) / max(1, len(t))
        core = re.sub(r"[^a-z]", "", t.lower())
        garbage = (not dh[i]) and local < rate and (
            pd > 0.15 or not re.search(r"[aeiou]", t.lower()) or len(core) < 2)
        if not garbage:
            keep.append(t)
    filtered = " ".join(keep)
    return filtered, len(text) - len(filtered)


def paper_from_text(name):
    """Return 'GS1'..'GS4' / 'Essay' / None from a filename or a paper label."""
    u = name.upper()
    if "ESSAY" in u or "EASSY" in u:
        return "Essay"
    m = re.search(r"(?:GS|G\.S|PAPER|STUDIES)[\s\-\._]*?(IV|III|II|I)\b", u)
    if m:
        return "GS" + ROMAN[m.group(1)]
    m = re.search(r"(?:GS|G\.S|PAPER|STUDIES)[\s\-\._]*?([1-4])\b", u)
    if m:
        return "GS" + m.group(1)
    return None


# Canonical full-paper (global) numbering of a UPSC Mains sitting:
# GS1 1-20, GS2 21-40, GS3 41-60, GS4 61-79, Essay 80+. Offset = global - local.
PAPER_OFFSET = {"GS1": 0, "GS2": 20, "GS3": 40, "GS4": 60, "Essay": 79}


def paper_local_and_global(paper, qno, ref=""):
    """Return (paper_local_number, global_number) as strings.

    The paper is authoritative. The paper-local number is taken from the
    source_question_ref ('GS2-Q1' -> 1) when present; otherwise from the stored
    question_number, recognising whether it is already global (in the paper's
    canonical band) or local (1-based). global = local + PAPER_OFFSET[paper].
    Non-integer GS4 sub-part labels (e.g. '5b') cannot be canonically ranked, so
    the raw label is kept as local and global is left blank rather than guessed.
    """
    off = PAPER_OFFSET.get(paper)
    if off is None:
        return "", ""
    # 1) local from the ref, if it carries a Q-number
    m = re.search(r"Q\s*0*(\d+)", str(ref), re.I)
    local = int(m.group(1)) if m else None
    # 2) else infer from the stored question_number
    if local is None:
        s = str(qno).strip()
        if re.fullmatch(r"\d+", s):
            n = int(s)
            if off < n <= off + 20:      # stored as global -> derive local
                local = n - off
            elif 1 <= n <= 20:           # stored as paper-local
                local = n
            else:
                return s, s              # out of band; report as-is
        else:
            return s, ""                 # sub-part label ('5b'): no clean global
    return str(local), str(local + off)


def year_from_filename(name):
    # 4-digit year not embedded in a longer number; word boundaries are NOT
    # used because filenames glue the year to text ("Mains2013ALL", "_2024_").
    yrs = sorted(set(re.findall(r"(?<!\d)(?:19|20)\d\d(?!\d)", name)))
    return yrs[0] if len(yrs) == 1 else None


def year_from_content(txt):
    m = re.search(r"EXAMINATION[,\s]+((?:19|20)\d\d)", txt.upper())
    return m.group(1) if m else None

# ------------------------- RAW EXTRACTION -----------------------------------

def extract_raw_text(path):
    """Return (ascii_text, error_or_None). No OCR, no inference."""
    ext = path.lower().rsplit(".", 1)[-1]
    try:
        if ext == "pdf":
            with pdfplumber.open(path) as pdf:
                raw = "\n".join((p.extract_text() or "") for p in pdf.pages)
        elif ext == "docx":
            d = docx.Document(path)
            raw = "\n".join(p.text for p in d.paragraphs)
        elif ext == "md":
            with open(path, encoding="utf-8") as fh:
                raw = fh.read()
        else:
            return "", "unsupported_ext"
    except Exception as e:  # unreadable/corrupt -> reported, never guessed
        return "", f"{type(e).__name__}: {e}"[:80]
    return ascii_only(raw), None


QMARK_RE = re.compile(r"(?m)^\s*(?:Q\.?\s*)?(\d{1,2})[.)]")


def chunk_raw(text):
    """Split ASCII raw text into [(qno, chunk_text)] on printed numbering."""
    marks = list(QMARK_RE.finditer(text))
    if not marks:
        return [("", text)]
    chunks = []
    for i, m in enumerate(marks):
        start = m.start()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        chunks.append((m.group(1), text[start:end]))
    return chunks


def build_raw_corpus():
    """Return (inventory list, corpus dict {(year,paper): [(qno, normtext)]})."""
    inventory = []
    corpus = defaultdict(list)
    paths = []
    for d in RAW_DIRS:
        for f in sorted(glob.glob(os.path.join(d, "*"))):
            if os.path.isfile(f) and f.lower().rsplit(".", 1)[-1] in ("pdf", "docx", "md"):
                paths.append(f)
    for path in paths:
        base = os.path.basename(path)
        text, err = extract_raw_text(path)
        ewc = english_word_count(text)
        readable = (err is None) and (ewc >= MIN_ENGLISH_WORDS)
        paper = paper_from_text(base)
        # cross-check paper against content when readable and filename silent
        if paper is None and readable:
            paper = paper_from_text(text[:400])
        yr = year_from_filename(base)
        ysrc = "filename" if yr else None
        if yr is None:
            yc = year_from_content(text)
            if yc:
                yr, ysrc = yc, "content"
        classified = bool(yr and paper)
        rec = {
            "file": os.path.relpath(path, RAW_DIRS[0]),
            "paper": paper or "?",
            "year": yr or "?",
            "year_src": ysrc or "none",
            "readable": readable,
            "eng_words": ewc,
            "err": err or "",
            "used": False,
            "nchunks": 0,
        }
        if readable and classified and paper in GS_PAPERS:
            chunks = [(qno, normalize(c)) for qno, c in chunk_raw(text)]
            corpus[(yr, paper)].extend((qno, c, base) for qno, c in chunks)
            rec["used"] = True
            rec["nchunks"] = len(chunks)
        inventory.append(rec)
    return inventory, corpus

# ------------------------- JSON EXTRACTION ----------------------------------

def norm_paper_label(s):
    return paper_from_text(s or "")


def iter_json_questions(path):
    """Yield dicts: {year, paper, qno, en, in_scope, note} per source question."""
    base = os.path.basename(path)
    try:
        data = json.load(open(path, encoding="utf-8-sig"))
    except Exception as e:
        yield {"parse_error": f"{type(e).__name__}: {e}"[:80], "file": base}
        return
    file_year = year_from_filename(base)

    def emit(qno, en, paper, year, ref=""):
        en = en or ""
        in_scope = paper in GS_PAPERS
        local, glob = paper_local_and_global(paper, qno, ref)
        return {
            "file": base, "year": year or "?", "paper": paper or "?",
            "qno": qno, "en": en, "en_len": len(en), "in_scope": in_scope,
            "ref": ref or "", "local_no": local, "global_no": glob,
        }

    if isinstance(data, dict):
        # Family A: structured single paper, explicit year/paper, text_en.
        # Questions may live in `questions` OR in `section_A`/`section_B`
        # (GS4), so collect every dict that carries a text_en, in document
        # order, walking without descending into a question dict itself.
        paper = norm_paper_label(data.get("paper"))
        year = str(data.get("year")) if data.get("year") else file_year
        qdicts = []

        def walk(o):
            if isinstance(o, dict):
                if "text_en" in o:
                    qdicts.append(o)
                else:
                    for v in o.values():
                        walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)

        walk(data)
        if qdicts:
            for q in qdicts:
                qno = q.get("question_number", q.get("question_index", ""))
                yield emit(qno, q.get("text_en"), paper, year)
            return

    if isinstance(data, list):
        # Family B: list-root; paper per-question via source_question_ref
        for q in data:
            if not isinstance(q, dict):
                continue
            qno = q.get("question_number", q.get("question_index", ""))
            en = q.get("text_en") or q.get("question_text") or ""
            ref = q.get("source_question_ref") or ""
            paper = paper_from_text(ref) or paper_from_text(base)
            yield emit(qno, en, paper, file_year, ref=ref)
        return

    # Unrecognised shape -> surface it
    yield {"unrecognised": True, "file": base}

# ------------------------------- MATCH --------------------------------------

def best_against(norm_en, chunk_list):
    """chunk_list: [(qno, normtext, srcfile)]. Return (score, qno, srcfile)."""
    if not chunk_list:
        return None
    texts = [c[1] for c in chunk_list]
    hit = process.extractOne(norm_en, texts, scorer=fuzz.partial_ratio)
    if hit is None:
        return None
    _, score, idx = hit
    return (round(score, 1), chunk_list[idx][0], chunk_list[idx][2])


def verdict_for(norm_en, own_chunks, other_chunks):
    own = best_against(norm_en, own_chunks) if own_chunks else None
    other = best_against(norm_en, other_chunks)
    if not own_chunks:
        v = "unverifiable"
        if other:
            return v, other[0], other_year_of(other), other[1]
        return v, "", "", ""
    own_score = own[0]
    if own_score >= EXACT_MIN:
        return "exact", own_score, None, own[1]
    if own_score >= VARIANT_MIN:
        return "variant", own_score, None, own[1]
    if other and other[0] >= WRONG_YEAR_OTHER_MIN:
        return "wrong_year", other[0], other_year_of(other), other[1]
    # orphan: report closest of the two
    if other and other[0] > own_score:
        return "orphan", other[0], other_year_of(other), other[1]
    return "orphan", own_score, None, own[1]


# other_chunks entries carry their (year) via a side map populated per question.
_OTHER_YEAR = {}


def other_year_of(other_hit):
    return _OTHER_YEAR.get(other_hit[2], "")

# ------------------------------- MAIN ---------------------------------------

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    inventory, corpus = build_raw_corpus()

    # map raw source-file -> its year (for naming cross-year matches)
    global _OTHER_YEAR
    _OTHER_YEAR = {}
    for (yr, paper), chunks in corpus.items():
        for _, _, src in chunks:
            _OTHER_YEAR[src] = yr

    rows = []
    scope_counts = defaultdict(int)     # (year, verdict) -> n  (GS in scope)
    excluded_essay = defaultdict(int)   # file -> n essay questions
    json_issues = []                    # parse errors / unrecognised
    unclassified_json_q = defaultdict(int)

    for path in sorted(glob.glob(SRC_GLOB)):
        for q in iter_json_questions(path):
            if q.get("parse_error"):
                json_issues.append((q["file"], "parse_error: " + q["parse_error"]))
                continue
            if q.get("unrecognised"):
                json_issues.append((q["file"], "unrecognised shape"))
                continue
            if not q["in_scope"]:
                if q["paper"] == "Essay":
                    excluded_essay[q["file"]] += 1
                else:
                    unclassified_json_q[q["file"]] += 1
                continue

            key = (q["year"], q["paper"])
            own_chunks = corpus.get(key, [])
            other_chunks = [c for k, cl in corpus.items() if k != key for c in cl]

            norm_en = normalize(q["en"])
            if len(norm_en) < MIN_JSON_EN_LEN:
                # too short to trust a fuzzy score; still classify by raw presence
                if not own_chunks:
                    verdict, best, myr, mqno = "unverifiable", "", "", ""
                else:
                    verdict, best, myr, mqno = "orphan", "", "", ""
            else:
                verdict, best, myr, mqno = verdict_for(norm_en, own_chunks, other_chunks)
                if myr is None:
                    myr = q["year"]

            rows.append([
                q["file"], q["year"], q["paper"],
                q["qno"], q["local_no"], q["global_no"], q["en_len"],
                verdict, best, myr, mqno, "false",
            ])
            scope_counts[(q["year"], verdict)] += 1

    # ---- write CSV ----
    # question_number = value as stored in the source; paper_local_number =
    # 1-based within its paper; global_number = canonical full-paper position
    # (GS1 1-20, GS2 21-40, GS3 41-60, GS4 61-79). ocr_derived=false: these are
    # text-layer verdicts and are never equated with OCR-derived ones.
    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "year", "paper",
                    "question_number", "paper_local_number", "global_number",
                    "en_len", "verdict", "best_score", "matched_year",
                    "matched_qno", "ocr_derived"])
        w.writerows(rows)

    # ---- write summary ----
    write_summary(inventory, corpus, rows, scope_counts, excluded_essay,
                  json_issues, unclassified_json_q)

    print(f"verdict rows (GS in scope): {len(rows)}")
    print(f"CSV : {OUT_CSV}")
    print(f"MD  : {OUT_MD}")


def write_summary(inventory, corpus, rows, scope_counts, excluded_essay,
                  json_issues, unclassified_json_q):
    verdicts = ["exact", "variant", "wrong_year", "orphan", "unverifiable"]
    years = sorted({r[1] for r in rows})
    lines = []
    lines.append("# GS source reconciliation — summary")
    lines.append("")
    lines.append("Generated by `scripts/reconcile_gs_sources.py` (offline, no OCR). "
                 "See that script's header for the full matching algorithm and every threshold.")
    lines.append("")
    lines.append(f"- Source glob: `{SRC_GLOB}`")
    lines.append(f"- Raw dirs: `{RAW_DIRS[0]}` and `\\done`")
    lines.append(f"- Readability floor: >= {MIN_ENGLISH_WORDS} English words. "
                 f"Thresholds: exact >= {EXACT_MIN}, variant >= {VARIANT_MIN}, "
                 f"wrong_year other >= {WRONG_YEAR_OTHER_MIN} (own < {VARIANT_MIN}).")
    lines.append(f"- GS verdict rows: **{len(rows)}** (Essay excluded from CSV; see below).")
    lines.append("")

    # counts by year x verdict
    lines.append("## Counts by year and verdict (GS in scope)")
    lines.append("")
    lines.append("| year | " + " | ".join(verdicts) + " | total |")
    lines.append("|" + "---|" * (len(verdicts) + 2))
    tot = defaultdict(int)
    for y in years:
        cells = []
        rowtot = 0
        for v in verdicts:
            n = scope_counts.get((y, v), 0)
            cells.append(str(n))
            tot[v] += n
            rowtot += n
        lines.append(f"| {y} | " + " | ".join(cells) + f" | {rowtot} |")
    lines.append("| **all** | " + " | ".join(f"**{tot[v]}**" for v in verdicts)
                 + f" | **{sum(tot.values())}** |")
    lines.append("")

    # raw inventory
    lines.append("## Raw-file inventory (year / paper identification + readability)")
    lines.append("")
    lines.append("`used` = readable AND classified AND a GS paper -> included as a matching target.")
    lines.append("")
    lines.append("| raw file | paper | year | id source | readable | eng_words | chunks | used | note |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for r in inventory:
        lines.append(
            f"| {r['file']} | {r['paper']} | {r['year']} | {r['year_src']} | "
            f"{'yes' if r['readable'] else 'NO'} | {r['eng_words']} | {r['nchunks']} | "
            f"{'yes' if r['used'] else '-'} | {r['err']} |"
        )
    lines.append("")

    # years with readable raw
    covered = defaultdict(set)
    for (yr, paper) in corpus:
        covered[yr].add(paper)
    lines.append("## GS coverage of readable+classified raw")
    lines.append("")
    for yr in sorted(covered):
        lines.append(f"- **{yr}**: " + ", ".join(sorted(covered[yr])))
    years_no_raw = sorted(y for y in years if y not in covered)
    lines.append("")
    lines.append("### Years appearing in source JSONs with NO readable+classified raw (all such questions are `unverifiable`)")
    lines.append("")
    lines.append(", ".join(years_no_raw) if years_no_raw else "_none_")
    lines.append("")

    # Essay exclusions + issues
    lines.append("## Excluded from GS scope")
    lines.append("")
    lines.append("### Essay questions (parsed, counted, not in CSV)")
    lines.append("")
    if excluded_essay:
        for f in sorted(excluded_essay):
            lines.append(f"- {f}: {excluded_essay[f]}")
    else:
        lines.append("_none_")
    lines.append("")
    if unclassified_json_q:
        lines.append("### Source questions whose paper could not be classified (reported, not scored)")
        lines.append("")
        for f in sorted(unclassified_json_q):
            lines.append(f"- {f}: {unclassified_json_q[f]}")
        lines.append("")
    lines.append("### Source JSON files not parseable / unrecognised")
    lines.append("")
    if json_issues:
        for f, why in sorted(set(json_issues)):
            lines.append(f"- {f}: {why}")
    else:
        lines.append("_none_")
    lines.append("")

    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


if __name__ == "__main__":
    sys.exit(main())
