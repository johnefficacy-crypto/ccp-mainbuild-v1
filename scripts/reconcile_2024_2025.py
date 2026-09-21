#!/usr/bin/env python3
r"""
reconcile_2024_2025.py — Reconcile 2024 & 2025 GS source JSONs against the raw
Mains DOCX. DOCX extraction is EXACT (python-docx): no OCR, no rasterization, no
confidence gate. ocr_derived=false on every row.

Raw (…\Mains\done):
  2024: UPSC_CSE_2024_Main_GS-1/2/3.docx   (NO GS4 raw -> those rows unverifiable)
  2025: UPSC_CSE_2025_Main_GS-1/2/3/4.docx

Source rows are OUTSIDE the UPSCCSEMains* glob. Scope decision (see the report's
"Files used / out of scope" section):
  USED (one authoritative file per year+paper):
    2024 GS1-4: "GS{n} 2024.json"
    2025 GS1-4: "final_GS{n}.json"
  OUT OF SCOPE (not scored, to avoid double-counting):
    "UPSC-CSE-Mains-GS{n} 2024.json" — exact duplicates of "GS{n} 2024.json"
    "retry_GS2/GS3.json"            — exact duplicates of final_GS2/GS3
    "retry_GS4.json"                — 6-question subset of final_GS4
    "gs{n}_2025_tag_batch.json"     — tag records (question_id/topic_id/reason),
                                      no question text -> nothing to match
    "Essay 2024.json"               — Essay, not GS

Matching: same 85 cut, full-text partial_ratio vs the whole DOCX paper.
  score >= 95 -> exact ; 85 <= score < 95 -> variant ; score < 85 -> orphan.
2024 GS4 has no raw -> unverifiable.

Output: workbench/audit/gs_2024_2025_verdict.csv, gs_2024_2025.md.
"""

import csv
import json
import os
from collections import Counter, defaultdict

from rapidfuzz import fuzz

import reconcile_gs_sources as R

DL = r"D:\Users\user\Downloads"
DONE = os.path.join(R.RAW_DIRS[0], "done")
OUT_DIR = R.OUT_DIR
OUT_CSV = os.path.join(OUT_DIR, "gs_2024_2025_verdict.csv")
OUT_MD = os.path.join(OUT_DIR, "gs_2024_2025.md")

MATCH_CUT, EXACT_CUT = 85, 95

# authoritative source file -> (year, paper, raw docx path or None)
USED = {
    "GS1 2024.json": ("2024", "GS1", os.path.join(DONE, "UPSC_CSE_2024_Main_GS-1.docx")),
    "GS2 2024.json": ("2024", "GS2", os.path.join(DONE, "UPSC_CSE_2024_Main_GS-2.docx")),
    "GS3 2024.json": ("2024", "GS3", os.path.join(DONE, "UPSC_CSE_2024_Main_GS-3.docx")),
    "GS4 2024.json": ("2024", "GS4", None),   # no raw -> unverifiable
    "final_GS1.json": ("2025", "GS1", os.path.join(DONE, "UPSC_CSE_2025_Main_GS-1.docx")),
    "final_GS2.json": ("2025", "GS2", os.path.join(DONE, "UPSC_CSE_2025_Main_GS-2.docx")),
    "final_GS3.json": ("2025", "GS3", os.path.join(DONE, "UPSC_CSE_2025_Main_GS-3.docx")),
    "final_GS4.json": ("2025", "GS4", os.path.join(DONE, "UPSC_CSE_2025_Main_GS-4.docx")),
}
OUT_OF_SCOPE = {
    "UPSC-CSE-Mains-GS1 2024.json": "exact duplicate of 'GS1 2024.json'",
    "UPSC-CSE-Mains-GS2 2024.json": "exact duplicate of 'GS2 2024.json'",
    "UPSC-CSE-Mains-GS3 2024.json": "exact duplicate of 'GS3 2024.json'",
    "UPSC-CSE-Mains-GS4 2024.json": "exact duplicate of 'GS4 2024.json'",
    "retry_GS2.json": "exact duplicate of 'final_GS2.json'",
    "retry_GS3.json": "exact duplicate of 'final_GS3.json'",
    "retry_GS4.json": "6-question subset of 'final_GS4.json'",
    "gs1_2025_tag_batch.json": "tag records (question_id/topic_id/reason), no question text",
    "gs2_2025_tag_batch.json": "tag records, no question text",
    "gs3_2025_tag_batch.json": "tag records, no question text",
    "gs4_2025_tag_batch.json": "tag records, no question text",
    "Essay 2024.json": "Essay paper, not GS",
}


def docx_fulltext(path):
    text, err = R.extract_raw_text(path)   # python-docx -> ascii_only; exact, no OCR
    return R.normalize(text), err


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    # extract raw DOCX once per distinct path
    docx_norm = {}
    for _, (_, _, path) in USED.items():
        if path and path not in docx_norm:
            docx_norm[path], _ = docx_fulltext(path)

    rows = []
    for fname, (year, paper, path) in USED.items():
        data = json.load(open(os.path.join(DL, fname), encoding="utf-8-sig"))
        for q in data:
            if not isinstance(q, dict):
                continue
            qno = q.get("question_number", "")
            ref = q.get("source_question_ref", "")
            en = q.get("question_text") or q.get("text_en") or ""
            ne = R.normalize(en)
            local, glob = R.paper_local_and_global(paper, qno, ref)
            if path is None:
                verdict, best = "unverifiable", ""       # 2024 GS4: no raw
            elif len(ne) < R.MIN_JSON_EN_LEN:
                verdict, best = "orphan", ""
            else:
                s = round(fuzz.partial_ratio(ne, docx_norm[path]), 1)
                verdict = "exact" if s >= EXACT_CUT else ("variant" if s >= MATCH_CUT else "orphan")
                best = s
            rows.append([fname, year, paper, qno, local, glob, len(en),
                         verdict, best, "false"])

    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "year", "paper", "question_number", "paper_local_number",
                    "global_number", "en_len", "verdict", "best_score", "ocr_derived"])
        w.writerows(rows)

    write_report(rows)
    print(f"rows: {len(rows)}  CSV: {OUT_CSV}  MD: {OUT_MD}")


def _dist(xs):
    xs = [x for x in xs if isinstance(x, (int, float))]
    if not xs:
        return "n=0 (unverifiable)"
    import statistics as st
    return f"n={len(xs)} min={min(xs):.1f} median={st.median(xs):.1f} max={max(xs):.1f}"


def write_report(rows):
    L = ["# 2024 & 2025 GS reconciliation vs raw DOCX", ""]
    L.append("DOCX extraction is exact (python-docx) — no OCR, no rasterization, no "
             "confidence gate; `ocr_derived=false` on every row. Full-text `partial_ratio` "
             "match, single 85 cut (exact >=95, variant 85-95, orphan <85). 2024 GS4 has "
             "no raw DOCX -> unverifiable.")
    L.append("")
    L.append("## Files used (one authoritative file per year+paper)")
    L.append("")
    L.append("| source file | year | paper | raw docx |")
    L.append("|---|---|---|---|")
    for f, (y, p, path) in USED.items():
        L.append(f"| {f} | {y} | {p} | {os.path.basename(path) if path else '— (none)'} |")
    L.append("")
    L.append("## Files judged OUT OF SCOPE (not scored)")
    L.append("")
    L.append("| source file | reason |")
    L.append("|---|---|")
    for f, why in OUT_OF_SCOPE.items():
        L.append(f"| {f} | {why} |")
    L.append("")
    L.append("Duplicates were verified by comparing the full set of normalised question "
             "texts (not just the first): each `UPSC-CSE-Mains-GSx 2024` shares all 20/19 "
             "questions with `GSx 2024`; `retry_GS2/GS3` share all 20 with `final_GS2/GS3`; "
             "`retry_GS4`'s 6 questions are all present in `final_GS4`. The same questions "
             "are therefore scored once, not twice.")
    L.append("")

    by = defaultdict(lambda: Counter())
    sc = defaultdict(list)
    for r in rows:
        y, p, verdict, best = r[1], r[2], r[7], r[8]
        by[(y, p)][verdict] += 1
        sc[(y, p)].append(best)
    L.append("## Verdict counts by year and paper")
    L.append("")
    L.append("| year | paper | exact | variant | orphan | unverifiable | total | score dist |")
    L.append("|---|---|---|---|---|---|---|---|")
    for (y, p) in sorted(by):
        c = by[(y, p)]
        tot = sum(c.values())
        L.append(f"| {y} | {p} | {c['exact']} | {c['variant']} | {c['orphan']} | "
                 f"{c['unverifiable']} | {tot} | {_dist(sc[(y, p)])} |")
    L.append("")
    # year rollups
    yc = defaultdict(lambda: Counter())
    for r in rows:
        yc[r[1]][r[7]] += 1
    L.append("## Verdict counts by year")
    L.append("")
    L.append("| year | exact | variant | orphan | unverifiable | total |")
    L.append("|---|---|---|---|---|---|")
    for y in sorted(yc):
        c = yc[y]
        L.append(f"| {y} | {c['exact']} | {c['variant']} | {c['orphan']} | "
                 f"{c['unverifiable']} | {sum(c.values())} |")
    L.append("")

    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))


if __name__ == "__main__":
    main()
