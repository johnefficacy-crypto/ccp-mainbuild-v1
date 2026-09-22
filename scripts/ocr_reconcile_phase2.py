#!/usr/bin/env python3
r"""
ocr_reconcile_phase2.py — Phase 2: OCR-reconcile the nine scan-only years.

Years: 2013, 2014, 2016, 2017, 2018, 2019, 2020, 2021, 2023 — all four GS papers
each, wherever a classifiable raw file exists (filename-derived year+paper).

Calibrated setup, UNCHANGED (see ocr_calibration.md); nothing is retuned:
  - 300 DPI rasterization, tesseract eng only
  - reconcile_gs_sources.strip_legacy_font on the OCR output
  - FULL-TEXT matching (partial_ratio vs the whole OCR paper), NOT chunked
  - single 85 cut for both length classes:
        own_score >= 95  -> exact     (matched, verbatim)
        85 <= own_score < 95 -> variant (matched, OCR-degraded)
        own_score < 85   -> orphan    (not in the official paper)
    The 85 cut is the match/orphan boundary validated on short- AND long-form
    populations; 95 only sub-labels matched rows. No wrong_year pass here.

Every row is ocr_derived=true and is written only to phase-2 outputs; it is
never merged into the text-layer verdict CSV.

Low-confidence extraction gate (flagged, NOT scored -> unverifiable):
  - raw OCR under ~1500 tokens, OR
  - strip_legacy_font removes over ~5% of the ASCII text (legacy-font noise).

OCR text is cached per paper under workbench/audit/ocr_cache/<year>_<paper>.txt,
so the run is resumable and re-scoring needs no re-OCR.

Outputs (only): workbench/audit/ocr_phase2.md, ocr_phase2_verdict.csv.
"""

import csv
import glob
import json
import os
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
YEARS = {"2013", "2014", "2016", "2017", "2018", "2019", "2020", "2021", "2023"}
MATCH_CUT = 85       # match/orphan boundary (calibrated, not retuned)
EXACT_CUT = 95       # sub-label matched rows exact vs variant
MIN_RAW_TOKENS = 1500
MAX_NOISE_PCT = 5.0

OUT_DIR = R.OUT_DIR
CACHE_DIR = os.path.join(OUT_DIR, "ocr_cache")
OUT_MD = os.path.join(OUT_DIR, "ocr_phase2.md")
OUT_CSV = os.path.join(OUT_DIR, "ocr_phase2_verdict.csv")
TL_CSV = R.OUT_CSV


def raw_map():
    """(year,paper) -> full raw path, filename-classified, for the nine years."""
    m = {}
    for d in R.RAW_DIRS:
        for f in sorted(glob.glob(os.path.join(d, "*"))):
            if not (os.path.isfile(f) and f.lower().endswith(".pdf")):
                continue
            b = os.path.basename(f)
            y, p = R.year_from_filename(b), R.paper_from_text(b)
            if y in YEARS and p in R.GS_PAPERS and (y, p) not in m:
                m[(y, p)] = f
    return m


def ocr_paper(path):
    doc = fitz.open(path)
    mat = fitz.Matrix(DPI / 72.0, DPI / 72.0)
    parts = []
    for page in doc:
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        parts.append(pytesseract.image_to_string(img, lang="eng"))
    doc.close()
    return "\n".join(parts)


def get_ocr_text(year, paper, path):
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache = os.path.join(CACHE_DIR, f"{year}_{paper}.txt")
    if os.path.exists(cache):
        with open(cache, encoding="utf-8") as fh:
            return fh.read()
    raw = ocr_paper(path)
    with open(cache, "w", encoding="utf-8") as fh:
        fh.write(raw)
    return raw


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rmap = raw_map()

    # OCR + extraction confidence per paper
    papers = {}   # (year,paper) -> dict(full_norm, raw_tokens, eng_words, noise, low_conf, reason, file)
    for (y, p), path in sorted(rmap.items()):
        raw = get_ocr_text(y, p, path)
        ascii_t = R.ascii_only(raw)
        filt, removed = R.strip_legacy_font(ascii_t)
        raw_tokens = len(raw.split())
        eng_words = R.english_word_count(filt)
        noise = (100.0 * removed / len(ascii_t)) if ascii_t else 100.0
        low = raw_tokens < MIN_RAW_TOKENS or noise > MAX_NOISE_PCT
        reason = []
        if raw_tokens < MIN_RAW_TOKENS:
            reason.append(f"raw_tokens {raw_tokens}<{MIN_RAW_TOKENS}")
        if noise > MAX_NOISE_PCT:
            reason.append(f"noise {noise:.1f}%>{MAX_NOISE_PCT}%")
        papers[(y, p)] = {
            "full": R.normalize(filt), "raw_tokens": raw_tokens,
            "eng_words": eng_words, "noise": noise, "low_conf": low,
            "reason": "; ".join(reason), "file": os.path.relpath(path, R.RAW_DIRS[0]),
        }

    # score in-scope source questions for the nine years
    rows = []
    for path in sorted(glob.glob(R.SRC_GLOB)):
        for q in R.iter_json_questions(path):
            if q.get("parse_error") or q.get("unrecognised") or not q.get("in_scope"):
                continue
            if q["year"] not in YEARS:
                continue
            key = (q["year"], q["paper"])
            info = papers.get(key)
            ne = R.normalize(q["en"])
            if info is None:
                verdict, best = "unverifiable", ""          # no classifiable raw
            elif info["low_conf"]:
                verdict, best = "unverifiable", ""           # low-confidence extraction
            elif len(ne) < R.MIN_JSON_EN_LEN:
                verdict, best = "orphan", ""                 # too short to trust
            else:
                s = round(fuzz.partial_ratio(ne, info["full"]), 1)
                verdict = "exact" if s >= EXACT_CUT else ("variant" if s >= MATCH_CUT else "orphan")
                best = s
            rows.append([
                q["file"], q["year"], q["paper"], q["qno"], q["local_no"], q["global_no"],
                q["en_len"], verdict, best, "true",
            ])

    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "year", "paper", "question_number", "paper_local_number",
                    "global_number", "en_len", "verdict", "best_score", "ocr_derived"])
        w.writerows(rows)

    write_report(papers, rows)
    orphans_18_25 = answer_orphans(rows)
    print(f"phase-2 rows: {len(rows)}  papers OCR'd: {len(papers)}  "
          f"orphans 2018-2025: {orphans_18_25}")
    print(f"CSV: {OUT_CSV}\nMD : {OUT_MD}")


def answer_orphans(rows):
    """Orphans in 2018-2025: phase-2 OCR years in range + text-layer 2022/2024/2025."""
    n = sum(1 for r in rows if r[7] == "orphan" and "2018" <= r[1] <= "2025")
    with open(TL_CSV, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            if r["verdict"] == "orphan" and "2018" <= r["year"] <= "2025":
                n += 1  # text-layer years (2022) not covered by phase-2 OCR
    return n


def _dist(scores):
    if not scores:
        return "n=0"
    return (f"n={len(scores)} min={min(scores):.1f} median={st.median(scores):.1f} "
            f"max={max(scores):.1f}")


def write_report(papers, rows):
    L = ["# OCR reconciliation — Phase 2 (nine scan-only years)", ""]
    L.append("Calibrated setup, not retuned: 300 DPI, tesseract eng, `strip_legacy_font`, "
             "full-text matching, single 85 match cut (exact >=95, variant 85-95, orphan "
             "<85). Every row is `ocr_derived=true`. Low-confidence extraction "
             f"(raw OCR < {MIN_RAW_TOKENS} tokens OR legacy-font noise > {MAX_NOISE_PCT}%) "
             "is flagged and left `unverifiable`, not scored. Years with no classifiable "
             "raw file (2016, 2017, 2018, 2023; also 2021 GS1) are `unverifiable`.")
    L.append("")

    # extraction inventory
    L.append("## OCR extraction inventory + confidence")
    L.append("")
    L.append("| year | paper | file | raw_tokens | eng_words | noise% | confidence |")
    L.append("|---|---|---|---|---|---|---|")
    for (y, p) in sorted(papers):
        i = papers[(y, p)]
        conf = f"LOW ({i['reason']})" if i["low_conf"] else "ok"
        L.append(f"| {y} | {p} | {i['file']} | {i['raw_tokens']} | {i['eng_words']} | "
                 f"{i['noise']:.1f} | {conf} |")
    L.append("")

    # per year+paper verdict counts
    by = defaultdict(lambda: Counter())
    scores_by_year = defaultdict(list)
    for r in rows:
        y, p, verdict, best = r[1], r[2], r[7], r[8]
        by[(y, p)][verdict] += 1
        if isinstance(best, (int, float)):
            scores_by_year[y].append(best)
    L.append("## Verdict counts by year and paper")
    L.append("")
    L.append("| year | paper | exact | variant | orphan | unverifiable | total |")
    L.append("|---|---|---|---|---|---|---|")
    for (y, p) in sorted(by):
        c = by[(y, p)]
        tot = sum(c.values())
        L.append(f"| {y} | {p} | {c['exact']} | {c['variant']} | {c['orphan']} | "
                 f"{c['unverifiable']} | {tot} |")
    # year totals
    L.append("")
    L.append("## Verdict counts by year (all papers)")
    L.append("")
    L.append("| year | exact | variant | orphan | unverifiable | total | score dist (scored) |")
    L.append("|---|---|---|---|---|---|---|")
    yc = defaultdict(lambda: Counter())
    for r in rows:
        yc[r[1]][r[7]] += 1
    for y in sorted(yc):
        c = yc[y]
        tot = sum(c.values())
        L.append(f"| {y} | {c['exact']} | {c['variant']} | {c['orphan']} | "
                 f"{c['unverifiable']} | {tot} | {_dist(scores_by_year.get(y, []))} |")
    L.append("")

    # overall score distribution (scored rows only)
    allscores = [b for r in rows for b in ([r[8]] if isinstance(r[8], (int, float)) else [])]
    L.append("## Overall score distribution (scored rows)")
    L.append("")
    L.append(f"- {_dist(allscores)}")
    L.append("")
    buckets = ["<50", "50-59", "60-69", "70-79", "80-84", "85-94", "95-100"]
    cnt = Counter()
    for s in allscores:
        if s < 50: cnt["<50"] += 1
        elif s < 60: cnt["50-59"] += 1
        elif s < 70: cnt["60-69"] += 1
        elif s < 80: cnt["70-79"] += 1
        elif s < 85: cnt["80-84"] += 1
        elif s < 95: cnt["85-94"] += 1
        else: cnt["95-100"] += 1
    L.append("| bucket | n |")
    L.append("|---|---|")
    for b in buckets:
        L.append(f"| {b} | {cnt[b]} |")
    L.append("")

    # direct answer
    n18 = answer_orphans(rows)
    p18 = sum(1 for r in rows if r[7] == "orphan" and "2018" <= r[1] <= "2025")
    L.append("## Orphans in 2018-2025")
    L.append("")
    L.append(f"- Phase-2 OCR orphans (2018-2023 in range; only 2019/2020/2021 have raw): **{p18}**.")
    L.append(f"- Plus text-layer orphans 2022/2024/2025 (not OCR'd here): **{n18 - p18}**.")
    L.append(f"- **Total orphans 2018-2025: {n18}.**")
    L.append("(2018 and 2023 have no classifiable raw -> unverifiable, not orphan; "
             "2024/2025 have no in-scope source questions.)")
    L.append("")

    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))


if __name__ == "__main__":
    main()
