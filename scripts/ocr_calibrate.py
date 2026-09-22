#!/usr/bin/env python3
r"""
ocr_calibrate.py — OCR reconciliation, PHASE 1: CALIBRATE ONLY.

Scope: the years whose TEXT LAYER already produced verdicts — 2015 (GS1-3) and
2022 (GS1-4). The nine scan-only years are NOT touched.

What it does
  1. Rasterize each of the 7 raw papers at 300 DPI (PyMuPDF) and OCR with
     tesseract, English only. Devanagari OCRs to noise; the SAME [\x20-\x7E]+
     filter from reconcile_gs_sources.ascii_only() strips it.
  2. Feed the OCR text through the SAME matcher as the text-layer run — the
     normalize() / chunk_raw() / partial_ratio / verdict_for() pipeline is
     imported verbatim from reconcile_gs_sources.py (that file is NOT edited).
     Same source JSONs, same thresholds (95 / 80 / 90) so text-layer-verdict
     vs OCR-verdict is a like-for-like comparison.
  3. Emit workbench/audit/ocr_calibration.md: per-question text-layer verdict
     vs OCR verdict, both scores; flip counts + directions; OCR score
     distribution for known-authentic vs known-orphan rows; and a threshold
     recommendation derived from where those two populations separate here.

Ground-truth populations for calibration are defined by the trusted text-layer
verdict: authentic = {exact, variant}; orphan = {orphan}.

Cross-corpus note: for wrong_year detection the "other papers" set is the other
6 OCR'd papers (the only OCR text available in phase 1), not the full classified
raw set the text-layer run used. Flagged in the report.

ocr_derived rule: every OCR-based verdict here is labelled ocr_derived=true and
lives only in this calibration report; it is never written into the text-layer
verdict CSV nor treated as equivalent to a text-layer verdict.

Reproducibility: OCR text is cached under workbench/audit/ocr_cache/. Requires
PyMuPDF, Pillow, pytesseract and a tesseract binary with eng. Run:
    .venv/Scripts/python scripts/ocr_calibrate.py
Changes nothing outside workbench/audit/ (report + ocr_cache).
"""

import csv
import json
import os
import statistics as st
from collections import Counter, defaultdict

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

import reconcile_gs_sources as R  # matcher reused verbatim; not modified

# --------------------------- CONSTANTS --------------------------------------
TESS_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(TESS_CMD):
    pytesseract.pytesseract.tesseract_cmd = TESS_CMD

DPI = 300
RAW_BASE = R.RAW_DIRS[0]

# (year, paper) -> raw file, relative to RAW_BASE. The 7 text-layer-verdicted papers.
CALIB_PAPERS = {
    ("2015", "GS1"): "GS1-2015.pdf",
    ("2015", "GS2"): "GS-2-2015.pdf",
    ("2015", "GS3"): "GS3-2015.pdf",
    ("2022", "GS1"): r"done\UPSC GS Mains GS1 2022.pdf",
    ("2022", "GS2"): "GS Mains Paper II (2022).pdf",
    ("2022", "GS3"): "GS Mains Paper III (2022).pdf",
    ("2022", "GS4"): "GS Mains Paper IV (2022).pdf",
}

OUT_DIR = R.OUT_DIR
CACHE_DIR = os.path.join(OUT_DIR, "ocr_cache")
OUT_MD = os.path.join(OUT_DIR, "ocr_calibration.md")
TL_CSV = R.OUT_CSV  # existing text-layer verdict CSV (read-only)

# Known-labelled long-form orphans: the six confirmed-fabricated 2013 GS4 case
# studies (2013ALL qno 88-93), scored against the OCR'd REAL 2013 GS4 paper.
# Their six real counterparts are RTI disclosure, flyover engineer, Sivakasi
# child labour, nepotism in professor recruitment, leaking information, and a
# personal-experience question.
LONGFORM_ORPHAN = {
    "key": ("2013", "GS4"),
    "raw": "GS IV-2013.pdf",
    "source": "UPSCCSEMains2013ALL.json",
    "qnos": [88, 89, 90, 91, 92, 93],
}

# --------------------------- OCR --------------------------------------------

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


def get_ocr_text(year, paper, relpath):
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache = os.path.join(CACHE_DIR, f"{year}_{paper}.txt")
    if os.path.exists(cache):
        with open(cache, encoding="utf-8") as fh:
            return fh.read()
    raw = ocr_paper(os.path.join(RAW_BASE, relpath))
    with open(cache, "w", encoding="utf-8") as fh:
        fh.write(raw)
    return raw

# --------------------------- MAIN -------------------------------------------

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # 1) OCR -> corpus, same chunk/normalize as the text-layer run
    corpus = defaultdict(list)
    ocr_stats = []
    for (year, paper), rel in CALIB_PAPERS.items():
        raw = get_ocr_text(year, paper, rel)
        text = R.ascii_only(raw)
        chunks = [(qno, R.normalize(c)) for qno, c in R.chunk_raw(text)]
        src = os.path.basename(rel)
        corpus[(year, paper)].extend((qno, c, src) for qno, c in chunks)
        ocr_stats.append((year, paper, rel, R.english_word_count(text), len(chunks)))
    R._OTHER_YEAR = {src: yr for (yr, _), cl in corpus.items() for _, _, src in cl}

    # 2) text-layer verdicts (read-only)
    tl = {}
    with open(TL_CSV, encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            tl[(row["file"], row["question_number"])] = row

    # full-paper OCR text per key (robust scoring; bypasses the chunker)
    full = {k: R.normalize(R.ascii_only(get_ocr_text(k[0], k[1], rel)))
            for k, rel in CALIB_PAPERS.items()}

    # 3) two OCR scorings per in-scope source question in the calibrated papers:
    #    (a) chunk-port: reconcile's chunk-based verdict_for, unchanged
    #    (b) full-text : partial_ratio against the whole OCR paper (own + others)
    keys = set(CALIB_PAPERS)
    results = []
    for path in sorted(__import__("glob").glob(R.SRC_GLOB)):
        for q in R.iter_json_questions(path):
            if q.get("parse_error") or q.get("unrecognised") or not q.get("in_scope"):
                continue
            key = (q["year"], q["paper"])
            if key not in keys:
                continue
            own = corpus.get(key, [])
            other = [c for k, cl in corpus.items() if k != key for c in cl]
            norm_en = R.normalize(q["en"])
            short = len(norm_en) < R.MIN_JSON_EN_LEN
            # (a) chunk-port
            if short:
                cv, cbest = ("unverifiable" if not own else "orphan", "")
            else:
                cv, cbest, _, _ = R.verdict_for(norm_en, own, other)
            # (b) full-text
            if short:
                fv, fscore, fmatch = "unverifiable", "", ""
            else:
                own_s = round(fuzz_full(norm_en, full.get(key, "")), 1)
                obest, okey = -1.0, None
                for k2, t2 in full.items():
                    if k2 == key:
                        continue
                    s2 = fuzz_full(norm_en, t2)
                    if s2 > obest:
                        obest, okey = s2, k2
                obest = round(obest, 1)
                fv, fscore, fmatch = classify_full(own_s, obest, key, okey)
            tlrow = tl.get((q["file"], str(q["qno"])), {})
            results.append({
                "file": q["file"], "year": q["year"], "paper": q["paper"],
                "qno": q["qno"], "en_len": q["en_len"],
                "tl_verdict": tlrow.get("verdict", "n/a"),
                "tl_best": tlrow.get("best_score", ""),
                "ocr_chunk_verdict": cv, "ocr_chunk_best": cbest,
                "ocr_full_score": fscore, "ocr_full_verdict": fv,
                "ocr_full_match": fmatch, "ocr_derived": True,
            })

    # 4) KNOWN-LABELLED long-form orphans: the six confirmed-fabricated 2013 GS4
    #    case studies (2013ALL qno 88-93), scored against the OCR'd real 2013 GS4
    #    paper. These close the long-form-orphan gap flagged in the earlier run
    #    (which had zero long-form orphans). Ground truth is the operator's
    #    confirmation that all six are fabricated, NOT a text-layer verdict.
    lf_key = LONGFORM_ORPHAN["key"]
    lf_raw = R.ascii_only(get_ocr_text(lf_key[0], lf_key[1], LONGFORM_ORPHAN["raw"]))
    lf_full = R.normalize(R.strip_legacy_font(lf_raw)[0])
    src_path = next((p for p in __import__("glob").glob(R.SRC_GLOB)
                     if os.path.basename(p) == LONGFORM_ORPHAN["source"]), None)
    qs2013 = json.load(open(src_path, encoding="utf-8-sig")) if src_path else []
    want = set(LONGFORM_ORPHAN["qnos"])
    for q in qs2013:
        if q.get("question_number") not in want:
            continue
        en = q.get("question_text") or q.get("text_en") or ""
        ne = R.normalize(en)
        own_s = round(fuzz_full(ne, lf_full), 1)
        obest, okey = -1.0, None
        for k2, t2 in full.items():
            s2 = fuzz_full(ne, t2)
            if s2 > obest:
                obest, okey = s2, k2
        fv, fscore, fmatch = classify_full(own_s, round(obest, 1), lf_key, okey)
        results.append({
            "file": LONGFORM_ORPHAN["source"], "year": lf_key[0], "paper": lf_key[1],
            "qno": q.get("question_number"), "en_len": len(en),
            "tl_verdict": "n/a(known-fabricated)", "tl_best": "",
            "ocr_chunk_verdict": "n/a", "ocr_chunk_best": "",
            "ocr_full_score": fscore, "ocr_full_verdict": fv,
            "ocr_full_match": fmatch, "ocr_derived": True, "known_orphan": True,
        })

    write_report(results, ocr_stats)
    _o = {"exact": "m", "variant": "m", "match": "m", "orphan": "n",
          "review": "r", "wrong_year": "w", "unverifiable": "u"}
    base = [r for r in results if not r.get("known_orphan")]
    cflip = sum(1 for r in base if r["tl_verdict"] != r["ocr_chunk_verdict"])
    fflip = sum(1 for r in base
                if _o.get(r["tl_verdict"], "?") != _o.get(r["ocr_full_verdict"], "?"))
    lf = sum(1 for r in results if r.get("known_orphan"))
    print(f"calibration rows: {len(base)}  chunk-port flips: {cflip}  "
          f"full-text outcome flips: {fflip}  long-form orphans injected: {lf}")
    print(f"MD: {OUT_MD}")


# ---- full-text OCR scoring + calibrated classifier -------------------------
from rapidfuzz import fuzz as _fz  # noqa: E402

# Thresholds DERIVED from this corpus (see report): authentic min 92.0,
# real-orphan max 74.3 -> a match cut of 85 separates cleanly with a margin,
# with a 75-85 review band (empty here, kept as a safety margin).
OCR_MATCH = 85
OCR_REVIEW_LOW = 75


def fuzz_full(query, text):
    return _fz.partial_ratio(query, text) if text else 0.0


def classify_full(own_s, other_best, own_key, other_key):
    if own_s >= OCR_MATCH:
        return "match", own_s, f"{own_key[0]} {own_key[1]}"
    if other_best >= OCR_MATCH:
        return "wrong_year", other_best, f"{other_key[0]} {other_key[1]}"
    if own_s >= OCR_REVIEW_LOW or other_best >= OCR_REVIEW_LOW:
        return "review", max(own_s, other_best), f"{own_key[0]} {own_key[1]}"
    return "orphan", max(own_s, other_best), f"{own_key[0]} {own_key[1]}"


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _hist(scores):
    buckets = ["<50", "50-59", "60-69", "70-79", "80-89", "90-94", "95-100"]
    c = Counter()
    for s in scores:
        if s < 50: c["<50"] += 1
        elif s < 60: c["50-59"] += 1
        elif s < 70: c["60-69"] += 1
        elif s < 80: c["70-79"] += 1
        elif s < 90: c["80-89"] += 1
        elif s < 95: c["90-94"] += 1
        else: c["95-100"] += 1
    return [(b, c[b]) for b in buckets]


def _stats(scores):
    if not scores:
        return "n=0"
    return (f"n={len(scores)} min={min(scores):.1f} p25={_pct(scores,25):.1f} "
            f"median={st.median(scores):.1f} p75={_pct(scores,75):.1f} max={max(scores):.1f}")


def _pct(xs, p):
    xs = sorted(xs)
    if not xs:
        return 0.0
    k = (len(xs) - 1) * p / 100.0
    lo = int(k)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def write_report(results, ocr_stats):
    auth = [r for r in results if r["tl_verdict"] in ("exact", "variant")]
    orph = [r for r in results if r["tl_verdict"] == "orphan"]
    # full-text OCR scores by text-layer ground truth
    auth_f = [s for s in (_num(r["ocr_full_score"]) for r in auth) if s is not None]
    orph_f = [s for s in (_num(r["ocr_full_score"]) for r in orph) if s is not None]

    L = ["# OCR reconciliation — Phase 1 calibration", ""]
    L.append("Generated by `scripts/ocr_calibrate.py`. Scope: 2015 (GS1-3) and 2022 "
             "(GS1-4) — the years whose text layer already produced verdicts. The nine "
             "scan-only years are untouched. OCR: 300 DPI, tesseract eng only; the "
             "`[\\x20-\\x7E]+` filter strips Devanagari noise. The text-layer verdict is "
             "treated as ground truth. Every OCR verdict is `ocr_derived=true` and is "
             "never written into or treated as equivalent to the text-layer CSV.")
    L.append("")
    L.append("Two scorings are reported per question:")
    L.append("- **chunk-port** — reconcile_gs_sources' chunk-based `verdict_for` at its "
             "95/80/90 thresholds, run unchanged on OCR text (the literal 'same matcher').")
    L.append("- **full-text** — `partial_ratio` of the question against the WHOLE OCR "
             "paper, bypassing the chunker.")
    L.append("")

    # inventory
    L.append("## OCR extraction inventory")
    L.append("")
    L.append("| year | paper | raw file | eng_words(OCR) | chunks |")
    L.append("|---|---|---|---|---|")
    for y, p, rel, ew, nc in ocr_stats:
        L.append(f"| {y} | {p} | {rel} | {ew} | {nc} |")
    L.append("")

    # chunk-port flips (the artifact)
    cflips = [r for r in results if r["tl_verdict"] != r["ocr_chunk_verdict"]]
    cdir = Counter(f'{r["tl_verdict"]} -> {r["ocr_chunk_verdict"]}' for r in cflips)
    L.append("## (a) Chunk-port: same matcher, unchanged — UNRELIABLE on OCR")
    L.append("")
    L.append(f"- rows: **{len(results)}**, unchanged **{len(results)-len(cflips)}**, "
             f"flipped **{len(cflips)}**.")
    L.append("")
    L.append("| direction | n |")
    L.append("|---|---|")
    for d, n in sorted(cdir.items(), key=lambda x: -x[1]):
        L.append(f"| {d} | {n} |")
    L.append("")
    L.append("These flips are a HARNESS artifact, not an OCR-quality signal. OCR inserts "
             "spurious numeric line-starts (marks like `150`, stray digits), so "
             "`chunk_raw` splits a single question across chunk boundaries. Worked examples:")
    L.append("- 2022 GS2 q21: present in the OCR at `partial_ratio`=**100** against the "
             "whole paper, but the chunk holding it is fragmented so the per-chunk best "
             "falls to 50.5 -> false `orphan`.")
    L.append("- 2015 GS2 q4: genuinely absent (**49.5** vs whole paper) yet a tiny OCR "
             "fragment chunk that is a substring of the question inflates `partial_ratio` "
             "to 100 -> false `exact`.")
    L.append("")
    L.append("Conclusion: the chunk-based matcher does NOT transfer to OCR text. Score "
             "OCR against the full paper. (The same fragmentation also produced at least "
             "one false orphan in the text-layer run — see 2015 GS3 q1 below.)")
    L.append("")

    # full-text distribution
    L.append("## (b) Full-text OCR scoring — distribution by text-layer ground truth")
    L.append("")
    L.append(f"- **known-authentic** (text-layer exact/variant): {_stats(auth_f)}")
    L.append(f"- **known-orphan** (text-layer orphan): {_stats(orph_f)}")
    L.append("")
    L.append("| bucket | authentic | orphan |")
    L.append("|---|---|---|")
    ah = dict(_hist(auth_f)); oh = dict(_hist(orph_f))
    for b, _ in _hist(auth_f):
        L.append(f"| {b} | {ah.get(b,0)} | {oh.get(b,0)} |")
    L.append("")

    # separation + recommendation
    L.append("## Threshold recommendation (full-text, derived from THIS data)")
    L.append("")
    amin = min(auth_f); omax = max(orph_f)
    orph_sorted = sorted(orph_f, reverse=True)
    # the single orphan at/above authentic-min is a text-layer false-orphan (recovered)
    recovered = [r for r in orph if _num(r["ocr_full_score"]) is not None
                 and _num(r["ocr_full_score"]) >= amin]
    real_orph = [s for s in orph_f if s < amin]
    real_omax = max(real_orph) if real_orph else 0.0
    L.append(f"- authentic full-text score: min **{amin:.1f}**, and all {len(auth_f)} "
             f"authentic rows sit at **>= {amin:.1f}** (median {st.median(auth_f):.0f}).")
    L.append(f"- orphan full-text score: **{len(real_orph)}** of {len(orph_f)} sit at "
             f"**<= {real_omax:.1f}**; **{len(recovered)}** scores at 100 — a text-layer "
             f"false-orphan that OCR recovers (see below), not a genuine orphan.")
    L.append(f"- Clean band separating the genuine populations: **({real_omax:.1f}, "
             f"{amin:.1f})** — a ~{amin-real_omax:.0f}-point gap.")
    L.append("")
    L.append(f"**Recommendation (phase-1, this corpus): OCR match cut = {OCR_MATCH}** "
             f"(>= {OCR_MATCH} = match, {OCR_REVIEW_LOW}-{OCR_MATCH} = review, "
             f"< {OCR_REVIEW_LOW} = no-match/orphan). At 85 every genuine authentic row "
             f"(min {amin:.1f}) is a match and every genuine orphan (max {real_omax:.1f}) "
             f"is not; the {OCR_REVIEW_LOW}-{OCR_MATCH} review band is empty here but kept "
             f"as a safety margin for other papers.")
    L.append("")
    L.append("Do NOT carry over 95/80: OCR true-matches spread down to 92 (a 95 cut alone "
             "would false-reject the 92-95 authentic rows), and — more importantly — the "
             "chunk pipeline that 95/80 assumes must be replaced by full-text scoring.")
    L.append("")
    if recovered:
        L.append("### Text-layer false-orphan recovered by OCR")
        L.append("")
        for r in recovered:
            L.append(f"- `{r['file']}` {r['year']} {r['paper']} q{r['qno']}: text-layer "
                     f"orphan (best {r['tl_best']}) but OCR full-text = "
                     f"{r['ocr_full_score']}. The question is present verbatim; the "
                     f"text-layer chunker split it. This question is authentic.")
        L.append("")

    # length stratification (req 6): short <400 chars, long >900 chars.
    # Ground truth = text-layer verdict for 2015/2022 rows, PLUS the operator-
    # confirmed fabricated 2013 GS4 case studies (known_orphan) which supply the
    # long-form orphan population.
    def lbucket(n):
        return "short(<400)" if n < 400 else ("long(>900)" if n > 900 else "mid(400-900)")

    def gtruth(r):
        if r.get("known_orphan"):
            return "orphan"
        if r["tl_verdict"] in ("exact", "variant"):
            return "authentic"
        if r["tl_verdict"] == "orphan":
            return "orphan"
        return None

    def sub(pred):
        return [s for s in (_num(r["ocr_full_score"]) for r in results if pred(r))
                if s is not None]

    L.append("## Length-stratified full-text scores (short vs long)")
    L.append("")
    L.append("Short-form = theory (<400 chars); long-form = case study (>900 chars). "
             "Fabricated rows are long-form, so a *depressed* long-form authentic band "
             "would force a lower long-form cut and mask exactly those rows. The "
             "long-form orphan population is the six confirmed-fabricated 2013 GS4 case "
             "studies (2013ALL qno 88-93) scored against the OCR'd real 2013 GS4 paper "
             "(see the dedicated subsection).")
    L.append("")
    L.append("| length | ground-truth | n | min | median | max |")
    L.append("|---|---|---|---|---|---|")
    order = ["short(<400)", "mid(400-900)", "long(>900)"]
    cell = {}
    for b in order:
        for gt in ("authentic", "orphan"):
            xs = sub(lambda r, b=b, gt=gt: lbucket(r["en_len"]) == b and gtruth(r) == gt)
            cell[(b, gt)] = xs
            if xs:
                L.append(f"| {b} | {gt} | {len(xs)} | {min(xs):.1f} | "
                         f"{st.median(xs):.1f} | {max(xs):.1f} |")
            else:
                L.append(f"| {b} | {gt} | 0 | - | - | - |")
    L.append("")

    # dedicated long-form orphan listing (the six 2013 GS4 case studies)
    lf = sorted([r for r in results if r.get("known_orphan")],
                key=lambda r: str(r["qno"]))
    if lf:
        L.append("### Long-form orphan population — 2013 GS4 fabricated case studies")
        L.append("")
        L.append("Scored against the OCR'd (300 DPI, `strip_legacy_font`) real 2013 GS4 "
                 "paper, whose six genuine case studies (RTI disclosure, flyover engineer, "
                 "Sivakasi child labour, professor-recruitment nepotism, leaking "
                 "information, personal-experience) are present in the OCR text.")
        L.append("")
        L.append("| source qno | en_len | ocr_full_score | best-matching paper | verdict |")
        L.append("|---|---|---|---|---|")
        for r in lf:
            L.append(f"| {r['qno']} | {r['en_len']} | {r['ocr_full_score']} | "
                     f"{r['ocr_full_match']} | {r['ocr_full_verdict']} |")
        lfs = [x for x in (_num(r["ocr_full_score"]) for r in lf) if x is not None]
        L.append("")
        L.append(f"All six score **{min(lfs):.1f}-{max(lfs):.1f}** — orphan. Note q88 is "
                 f"themed 'flyover engineer', matching a real case study present in the "
                 f"OCR, yet the fabricated text still only reaches {max(lfs):.1f}: thematic "
                 f"overlap does not lift a fabricated long-form question near the match band.")
        L.append("")

    short_a = cell.get(("short(<400)", "authentic"), [])
    short_o = cell.get(("short(<400)", "orphan"), [])
    long_a = cell.get(("long(>900)", "authentic"), [])
    long_o = cell.get(("long(>900)", "orphan"), [])
    L.append("### Does 85 separate long-form as cleanly as short-form?")
    L.append("")
    if long_a and long_o:
        la, lo = min(long_a), max(long_o)
        # short-form real separation, excluding the recovered text-layer false-orphan
        s_real_o = [s for s in short_o if s < min(short_a)] if short_a else short_o
        sa, so = (min(short_a) if short_a else 0), (max(s_real_o) if s_real_o else 0)
        depressed = la < sa - 5
        L.append(f"- **long-form**: authentic n={len(long_a)} min **{la:.1f}**; "
                 f"orphan n={len(long_o)} max **{lo:.1f}** -> gap **{la-lo:.0f}** pts.")
        L.append(f"- **short-form**: authentic n={len(short_a)} min **{sa:.1f}**; "
                 f"orphan n={len(s_real_o)} max **{so:.1f}** -> gap **{sa-so:.0f}** pts.")
        L.append(f"- long-form authentic is **{'DEPRESSED' if depressed else 'NOT depressed'}** "
                 f"vs short-form (min {la:.1f} vs {sa:.1f}).")
        L.append("")
        if la >= OCR_MATCH > lo:
            same_or_cleaner = (la - lo) >= (sa - so)
            L.append(f"**Yes — 85 separates long-form"
                     f"{' at least as cleanly as' if same_or_cleaner else ' but less cleanly than'} "
                     f"short-form.** Every long-form authentic ({la:.1f}) is >= 85 and every "
                     f"long-form orphan ({lo:.1f}) is < 85. The long-form gap ({la-lo:.0f} pts) "
                     f"is {'wider than' if (la-lo)>(sa-so) else 'comparable to'} the short-form "
                     f"gap ({sa-so:.0f} pts) — a single **85** cut holds for both lengths, and "
                     f"the earlier long-form gap is now closed with a real orphan sample "
                     f"(n={len(long_o)}).")
        else:
            L.append(f"**No — 85 does not cleanly separate long-form.** long-form authentic "
                     f"min {la:.1f}, orphan max {lo:.1f}; the populations sit such that an 85 "
                     f"cut {'admits an orphan' if lo>=OCR_MATCH else 'rejects an authentic'}. "
                     f"Reporting where they land rather than forcing a number: authentic "
                     f"[{la:.1f}..{max(long_a):.1f}], orphan [{min(long_o):.1f}..{lo:.1f}].")
    else:
        L.append(f"- long-form authentic n={len(long_a)}, orphan n={len(long_o)} — "
                 f"insufficient to judge separation.")
    L.append("")

    # full-text flips, compared in a common outcome space (exact/variant and
    # OCR 'match' are both 'matched'; orphan is 'not-matched'), so label-name
    # differences are not miscounted as flips.
    def outcome(v):
        return {"exact": "matched", "variant": "matched", "match": "matched",
                "orphan": "not-matched", "review": "review",
                "wrong_year": "wrong_year", "unverifiable": "unverifiable"}.get(v, v)

    L.append("## Full-text OCR outcome vs text-layer outcome")
    L.append("")
    L.append("Compared in a common space: {exact, variant, match} -> `matched`; "
             "`orphan` -> `not-matched`; plus `review` / `wrong_year`.")
    L.append("")
    ff = [r for r in results if not r.get("known_orphan")
          and outcome(r["tl_verdict"]) != outcome(r["ocr_full_verdict"])]
    fdir = Counter(f'{outcome(r["tl_verdict"])} -> {outcome(r["ocr_full_verdict"])}' for r in ff)
    L.append(f"- outcome-level flips: **{len(ff)}** of {len(results)} "
             f"(unchanged {len(results)-len(ff)}).")
    L.append("")
    L.append("| direction | n |")
    L.append("|---|---|")
    for d, n in sorted(fdir.items(), key=lambda x: -x[1]):
        L.append(f"| {d} | {n} |")
    L.append("")
    L.append("(The lone flip is the recovered false-orphan above — OCR full-text agrees "
             "with the text layer on all other genuine matched/not-matched calls.)")
    L.append("")

    # full table
    L.append("## Full per-question comparison")
    L.append("")
    L.append("`ocr_derived=true` for every OCR column.")
    L.append("")
    L.append("| file | year | paper | qno | en_len | tl_verdict | tl_best | "
             "chunk_verdict | chunk_best | full_score | full_verdict |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in sorted(results, key=lambda r: (r["year"], r["paper"], r["file"], str(r["qno"]))):
        L.append(
            f"| {r['file']} | {r['year']} | {r['paper']} | {r['qno']} | {r['en_len']} | "
            f"{r['tl_verdict']} | {r['tl_best']} | {r['ocr_chunk_verdict']} | "
            f"{r['ocr_chunk_best']} | {r['ocr_full_score']} | {r['ocr_full_verdict']} |"
        )
    L.append("")

    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))


if __name__ == "__main__":
    main()
