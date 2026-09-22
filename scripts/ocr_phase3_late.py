#!/usr/bin/env python3
r"""
ocr_phase3_late.py - score the papers phase 3 could not classify, once their
identity is settled by operator decision.

    2017 GS2  <- QP-CSM-17-010926-GENERAL-STUDIES-PAPER - II.pdf
    2023 GS2  <- QP-CSM-23-GENERAL-STUDIES-PAPER-II-180923.pdf
    2021 GS1  <- QP-CSM-21-GENSTUDIESPAPER-I-110122.pdf

IDENTITY IS TAKEN AS GIVEN, NOT RE-DERIVED. The filename date stamps are
republication dates (010926 = 2026, 110122 = 2022), not exam years, so nothing
here reads them. Phase 3's classifier abstained on all three; the OCR failures
that caused it, recorded for the audit trail:

    2017 GS2  year printed in a pale violet stamp typeface, dropped entirely;
              real paper-set code STH-G-GSD missed in the top-right margin
    2023 GS2  year double-struck, OCR'd as "2083"; "(Paper II)" lost an I, so
              the English label read "Paper I" against a Hindi label reading II
    2021 GS1  no raw file existed in the corpus when phase 2 ran

Setup is the unchanged phase-3 setup: 300 DPI, tesseract eng,
strip_legacy_font, full-text partial_ratio, single 85 cut (>=95 exact,
85-94 variant, <85 orphan), and the re-gate's English-word floor of 667
(ocr_regate.py) in place of the retired 1500 raw-token floor.

Fully offline: no DB, no network, no writes to any input. OCR is cached under
the existing phase-3 cache, so a re-run costs nothing.

IDEMPOTENT. The phase-3 CSV already carries a row per DB question for these
papers with verdict `unverifiable` - phase 3's own conclusion - and those rows
are never touched. Rows this script adds are marked `scoring_pass=phase3-late`.
A paper already present as `phase3-late` is re-scored and CHECKED against what
is stored, but not appended again, so repeated runs cannot duplicate rows.

OUTPUTS
    workbench/audit/ocr_cache/<year>_<paper>.txt   (canonical cache)
    workbench/audit/ocr_phase3_verdict.csv         (APPEND ONLY)
"""

import csv
import glob
import json
import os
import re
import shutil

import reconcile_gs_sources as R
import ocr_reconcile_phase3 as P3

ENG_WORD_FLOOR = 667          # from ocr_regate.py; replaces MIN_RAW_TOKENS
MAX_NOISE_PCT = 5.0

# Operator-supplied identity: (year, paper, source filename).
PAPERS = [
    ("2017", "GS2", "QP-CSM-17-010926-GENERAL-STUDIES-PAPER - II.pdf"),
    ("2021", "GS1", "QP-CSM-21-GENSTUDIESPAPER-I-110122.pdf"),
    ("2023", "GS2", "QP-CSM-23-GENERAL-STUDIES-PAPER-II-180923.pdf"),
]

CACHE_DIR = P3.CACHE_DIR
RAW_CACHE = P3.RAW_CACHE
P3_CSV = P3.OUT_CSV
UNLOCK = P3.UNLOCK
MISFILE_SHARE = P3.MISFILE_SHARE

SCHEMA = ["source", "file", "year", "paper", "question_number",
          "paper_local_number", "global_number", "en_len", "verdict",
          "best_score", "best_other_score", "best_other_year",
          "best_other_paper", "ocr_derived"]
PASS_COL = "scoring_pass"
LATE = "phase3-late"


def load_paper(year, paper, pdf_name):
    path = os.path.join(P3.NEW_SRC, pdf_name)
    if not os.path.exists(path):
        raise SystemExit("input not found: %s" % path)
    raw = P3.cached_ocr(path)
    dst = os.path.join(CACHE_DIR, "%s_%s.txt" % (year, paper))
    if not os.path.exists(dst):
        shutil.copyfile(
            os.path.join(RAW_CACHE, os.path.splitext(pdf_name)[0] + ".txt"), dst)
    m = P3.paper_metrics(raw)
    m["low_conf"] = (m["eng_words"] < ENG_WORD_FLOOR
                     or m["noise"] > MAX_NOISE_PCT)
    m["reason"] = ("eng_words %d<%d" % (m["eng_words"], ENG_WORD_FLOOR)
                   if m["eng_words"] < ENG_WORD_FLOOR else
                   "noise %.1f%%>%.1f%%" % (m["noise"], MAX_NOISE_PCT)
                   if m["noise"] > MAX_NOISE_PCT else "")
    m["file"] = pdf_name
    return m


def all_targets(papers):
    out = dict(papers)
    for c in sorted(glob.glob(os.path.join(CACHE_DIR, "*.txt"))):
        mm = re.fullmatch(r"(\d{4})_(GS[1-4])\.txt", os.path.basename(c))
        if not mm or (mm.group(1), mm.group(2)) in out:
            continue
        with open(c, encoding="utf-8") as fh:
            m = P3.paper_metrics(fh.read())
        m["low_conf"] = (m["eng_words"] < ENG_WORD_FLOOR
                         or m["noise"] > MAX_NOISE_PCT)
        out[(mm.group(1), mm.group(2))] = m
    return out


def score_paper(key, papers, targets):
    rows = []
    for path in sorted(glob.glob(R.SRC_GLOB)):
        for q in R.iter_json_questions(path):
            if q.get("parse_error") or q.get("unrecognised") or not q.get("in_scope"):
                continue
            if (q["year"], q["paper"]) != key:
                continue
            ne = R.normalize(q["en"])
            verdict, s = P3.score_one(ne, papers[key])
            other, oy, op = P3.best_elsewhere(ne, targets, key)
            rows.append(["db", q["file"], q["year"], q["paper"], q["qno"],
                         q["local_no"], q["global_no"], q["en_len"], verdict, s,
                         other, oy, op, "true"])
    p = os.path.join(UNLOCK, "upsc-mains-%s.json" % key[0])
    if os.path.exists(p):
        with open(p, encoding="utf-8-sig") as fh:
            data = json.load(fh)
        for u in data:
            if u.get("paper") != key[1]:
                continue
            ne = R.normalize(u.get("question_text", ""))
            verdict, s = P3.score_one(ne, papers[key])
            other, oy, op = P3.best_elsewhere(ne, targets, key)
            rows.append(["unlockias", "upsc-mains-%s.json" % key[0], key[0],
                         key[1], u.get("q_label", ""),
                         u.get("paper_local_number", ""),
                         u.get("question_number", ""),
                         len(u.get("question_text", "")), verdict, s,
                         other, oy, op, "true"])
    return rows


def main():
    papers = {}
    for year, paper, pdf in PAPERS:
        papers[(year, paper)] = load_paper(year, paper, pdf)
    targets = all_targets(papers)

    with open(P3_CSV, encoding="utf-8-sig") as fh:
        rd = csv.DictReader(fh)
        existing = list(rd)
        fields = list(rd.fieldnames)
    already = set((r["year"], r["paper"]) for r in existing
                  if r.get(PASS_COL) == LATE)

    scored, to_append, checked = {}, [], []
    for key in sorted(papers):
        rows = score_paper(key, papers, targets)
        scored[key] = rows
        if key in already:
            checked.append((key, verify(existing, key, rows)))
        else:
            to_append += rows

    if to_append:
        out_fields = fields + ([PASS_COL] if PASS_COL not in fields else [])
        with open(P3_CSV, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=out_fields)
            w.writeheader()
            for r in existing:
                r.setdefault(PASS_COL, "phase3")
                w.writerow(r)
            for r in to_append:
                d = dict(zip(SCHEMA, r))
                d[PASS_COL] = LATE
                w.writerow(d)
        print("appended %d rows (%d existing rows preserved)"
              % (len(to_append), len(existing)))
    else:
        print("nothing to append; all papers already scored")
    for key, ok in checked:
        print("  %s %s already present from an earlier run - re-scored and "
              "%s" % (key[0], key[1], "identical" if ok else "**MISMATCH**"))

    report(papers, scored)


def verify(existing, key, rows):
    """Re-scored values must match what is already stored for that paper."""
    stored = sorted((r["source"], r["file"], r["question_number"], r["verdict"],
                     r["best_score"])
                    for r in existing
                    if r.get(PASS_COL) == LATE
                    and (r["year"], r["paper"]) == key)
    fresh = sorted((r[0], r[1], str(r[4]), r[8], str(r[9])) for r in rows)
    return stored == fresh


def _counts(rows, source):
    c = {"exact": 0, "variant": 0, "orphan": 0, "unverifiable": 0}
    for r in rows:
        if r[0] == source:
            c[r[8]] += 1
    return c


def report(papers, scored):
    print()
    print("=== extraction quality (English-word floor %d) ===" % ENG_WORD_FLOOR)
    for key in sorted(papers):
        m = papers[key]
        print("  %s %s  raw_tokens=%d  eng_words=%d  noise=%.1f%%  gate=%s"
              % (key[0], key[1], m["raw_tokens"], m["eng_words"], m["noise"],
                 ("LOW (%s)" % m["reason"]) if m["low_conf"] else "pass"))
        print("      %s" % m["file"])

    print()
    print("=== 1. DB rows ===")
    for key in sorted(scored):
        c = _counts(scored[key], "db")
        sc = [r[9] for r in scored[key]
              if r[0] == "db" and isinstance(r[9], (int, float))]
        print("  %s %s: %d rows -> exact %d, variant %d, orphan %d, "
              "unverifiable %d  (scores %.1f-%.1f)"
              % (key[0], key[1], sum(c.values()), c["exact"], c["variant"],
                 c["orphan"], c["unverifiable"],
                 min(sc) if sc else 0, max(sc) if sc else 0))

    print()
    print("=== 2. UnlockIAS trust ===")
    for key in sorted(scored):
        c = _counts(scored[key], "unlockias")
        n = sum(c.values())
        if not n:
            print("  %s %s: no UnlockIAS rows" % key)
            continue
        share = 100.0 * c["orphan"] / n if n else 0.0
        v = ("TRUSTED" if c["orphan"] == 0
             else "MISFILED" if share >= MISFILE_SHARE else "PARTIAL")
        print("  %s %s: %d rows -> exact %d, variant %d, orphan %d (%.0f%%)"
              "  => %s" % (key[0], key[1], n, c["exact"], c["variant"],
                           c["orphan"], share, v))
        for r in scored[key]:
            if r[0] == "unlockias" and r[8] == "orphan":
                print("      orphan local Q%s @%.1f (best elsewhere %s %s @%s)"
                      % (r[5], r[9], r[11], r[12], r[10]))


if __name__ == "__main__":
    main()
