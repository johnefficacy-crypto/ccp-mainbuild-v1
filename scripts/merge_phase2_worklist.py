#!/usr/bin/env python3
r"""
merge_phase2_worklist.py - merge the phase-2 OCR verdicts into
repair_worklist.csv and recompute the apply-eligible set.

Fully offline: no DB, no network, no re-OCR. Read-only on the OCR caches and on
ocr_phase2_verdict.csv. The only file written is repair_worklist.csv, and only
by APPENDING columns - every existing column, including the phase-3, re-gate and
late columns, is copied through verbatim.

WHY THIS PASS EXISTS
--------------------
repair_worklist.csv predates the OCR verdict columns. Phase 3 wrote its own four
columns for its DB years only (2016/2017/2018/2023); the re-gate and the late
pass wrote theirs for the papers they admitted. Phase 2 - the OLDEST layer -
never wrote anything to the worklist, so 382 worklist rows across the papers
phase 2 DID score carried no verdict at all:

    2013 GS1-GS4, 2014 GS2-GS4, 2019 GS3/GS4, 2020 GS2/GS4, 2021 GS4

Those are exactly the papers whose phase-2 verdicts are not `unverifiable`, i.e.
the papers that passed the phase-2 low-confidence gate and were used as matching
targets. The set is derived from ocr_phase2_verdict.csv at run time and
cross-checked against a recomputation of the phase-2 gate over the cached OCR.

HOW THE MERGE IS DONE (and why it is not a row join)
----------------------------------------------------
Same caveat as the re-gate merge. `ocr_phase2_verdict.csv` is keyed by
SOURCE-JSON question; `repair_worklist.csv` is keyed by DB question, and they
are not 1:1 - e.g. 2013 GS2 has 50 source rows against 48 worklist rows, and the
numbering is not shared. Joining on (year, paper, number) would silently
mis-pair rows.

So the merge re-scores the worklist's OWN `db_text` and `unlockias_text` against
the same cached 300 DPI OCR, with the same scoring function - `strip_legacy_font`,
full-text `partial_ratio`, single 85 cut (>=95 exact, 85-94 variant, <85 orphan),
MIN_JSON_EN_LEN floor on the question side. Phase 2 decides WHICH papers are in
play; the worklist rows are then scored directly. This is exactly how phase 3
and the re-gate merge populated their own worklist columns.

Both sides are scored, because the eligibility rule needs a DB verdict AND an
UnlockIAS verdict.

COLUMNS APPENDED
    phase2_db_verdict, phase2_db_score
    phase2_unlockias_verdict, phase2_unlockias_score

PRECEDENCE - phase 2 is the oldest layer and therefore the last resort:
    late > re-gate > phase 3 > phase 2
EFFECTIVE VERDICT = the first non-empty verdict in that order.
ELIGIBLE = effective DB verdict `orphan` AND effective UnlockIAS verdict `exact`.
`apply_eligible` is recomputed for every row under the extended precedence; no
row that was eligible before can become ineligible, because phase 2 is only
consulted where every newer layer is silent.
"""

import csv
import os
from collections import Counter, defaultdict

import reconcile_gs_sources as R
import ocr_regate as G
import ocr_reconcile_phase2 as P2

WORKLIST = os.path.join(R.OUT_DIR, "repair_worklist.csv")
P2_CSV = os.path.join(R.OUT_DIR, "ocr_phase2_verdict.csv")

NEW_COLS = ["phase2_db_verdict", "phase2_db_score",
            "phase2_unlockias_verdict", "phase2_unlockias_score"]

# Verdict columns in precedence order, newest first.
DB_CHAIN = ["late_db_verdict", "regate_db_verdict", "phase3_db_verdict",
            "phase2_db_verdict"]
UL_CHAIN = ["late_unlockias_verdict", "regate_unlockias_verdict",
            "phase3_unlockias_verdict", "phase2_unlockias_verdict"]

# Years the operator run was told to leave alone, for flagging only. This
# script writes nothing to any database; the flag exists so the report can
# separate "meets the rule" from "may actually be applied".
HOLD_YEARS = ("2013", "2014", "2015", "2026")

# Why the rows phase 2 cannot reach still carry no verdict. Keyed by year.
NO_VERDICT_CAUSE = {
    "2015": "not in any OCR phase's scope - 2015 has a usable PDF text layer "
            "and was reconciled by the text-layer pass (gs_source_verdict.csv); "
            "phase 2's YEARS set excludes it, so no OCR verdict was ever "
            "produced for it",
    "2022": "same as 2015 - text-layer year, reconciled by the text-layer pass, "
            "outside phase 2's YEARS set",
    "2024": "outside every GS OCR phase - 2024/2025 carry no in-scope GS source "
            "questions and were reconciled separately by reconcile_2024_2025.py "
            "(gs_2024_2025_verdict.csv)",
    "2025": "outside every GS OCR phase - 2024/2025 carry no in-scope GS source "
            "questions and were reconciled separately by reconcile_2024_2025.py "
            "(gs_2024_2025_verdict.csv)",
    "2026": "phase 3 scored the 2026 papers but wrote worklist columns only for "
            "its DB years (2016/2017/2018/2023), so its 2026 verdicts never "
            "reached the worklist; 2026 GS1 has columns only because the "
            "re-gate admitted it. These rows are UnlockIAS-only (no db_text), "
            "so no DB verdict is possible for them in any case",
}


def phase2_scored_papers():
    """(year, paper) -> cached-OCR metrics, for the papers phase 2 scored.

    Ground truth is ocr_phase2_verdict.csv: a paper was scored iff at least one
    of its rows carries a verdict other than `unverifiable`. The phase-2 gate is
    then recomputed over today's cache as a guard: every paper phase 2 scored
    must still pass it, so a stale cache or a moved constant is caught rather
    than silently changing the scope.

    The converse does NOT hold and is not asserted. Papers that pass the gate
    today but were `unverifiable` in phase 2 (2016/2017/2018/2023) had no
    classifiable raw file when phase 2 ran; their cache entries were written
    later by phase 3, which owns their verdicts. They are excluded here.
    """
    scored = set()
    seen = set()
    with open(P2_CSV, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            key = (r["year"], r["paper"])
            seen.add(key)
            if r["verdict"] != "unverifiable":
                scored.add(key)

    out = {}
    recomputed = set()
    for key in sorted(seen):
        path = os.path.join(G.CACHE_DIR, "%s_%s.txt" % key)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as fh:
            m = G.metrics(fh.read())
        if (m["raw_tokens"] >= P2.MIN_RAW_TOKENS
                and m["noise"] <= P2.MAX_NOISE_PCT):
            recomputed.add(key)
        if key in scored:
            out[key] = m

    regressed = scored - recomputed
    if regressed:
        raise SystemExit(
            "papers phase 2 scored no longer pass the phase-2 gate over the "
            "cached OCR - the cache or the constants have moved: %s"
            % sorted(regressed))
    return out, sorted(recomputed - scored)


def effective(row, chain):
    """First non-empty verdict along a precedence chain, with its source column."""
    for c in chain:
        v = (row.get(c) or "").strip()
        if v:
            return v, c
    return "", ""


def main():
    papers, later_cached = phase2_scored_papers()

    with open(WORKLIST, encoding="utf-8-sig") as fh:
        rd = csv.DictReader(fh)
        rows = list(rd)
        fields = list(rd.fieldnames)
    fields_out = fields + [c for c in NEW_COLS if c not in fields]

    before = Counter()
    populated = Counter()
    no_text = Counter()

    for r in rows:
        for c in NEW_COLS:
            r.setdefault(c, "")

        # eligibility as the worklist stands now, before phase 2 is consulted
        was = (effective(r, DB_CHAIN[:3])[0] == "orphan"
               and effective(r, UL_CHAIN[:3])[0] == "exact")
        if was:
            before[(r["year"], r["paper"])] += 1

        key = (r["year"], r["paper"])
        info = papers.get(key)
        if info is None:
            continue
        if (r.get("db_text") or "").strip():
            v, s = G.score(R.normalize(r["db_text"]), info)
            r["phase2_db_verdict"], r["phase2_db_score"] = v, s
            populated[(key, "db")] += 1
        else:
            no_text[(key, "db")] += 1
        if (r.get("unlockias_text") or "").strip():
            v, s = G.score(R.normalize(r["unlockias_text"]), info)
            r["phase2_unlockias_verdict"], r["phase2_unlockias_score"] = v, s
            populated[(key, "ul")] += 1
        else:
            no_text[(key, "ul")] += 1

    after = Counter()
    for r in rows:
        eff_db = effective(r, DB_CHAIN)[0]
        eff_ul = effective(r, UL_CHAIN)[0]
        elig = (eff_db == "orphan" and eff_ul == "exact")
        r["apply_eligible"] = "true" if elig else ""
        if elig:
            after[(r["year"], r["paper"])] += 1

    with open(WORKLIST, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=fields_out)
        w.writeheader()
        w.writerows(rows)

    report(rows, papers, before, after, populated, no_text, later_cached)


def report(rows, papers, before, after, populated, no_text, later_cached):
    print("papers phase 2 scored (gate-passing, verdict != unverifiable): %d"
          % len(papers))
    print("  " + ", ".join("%s %s" % k for k in sorted(papers)))
    if later_cached:
        print("papers that pass the phase-2 gate today but were "
              "unverifiable in phase 2 (no raw file then; cached and "
              "scored later by phase 3) - excluded here: %s"
              % ", ".join("%s %s" % k for k in later_cached))
    print()

    print("=== ROWS POPULATED BY THE PHASE-2 MERGE ===")
    print("%-12s %10s %10s %10s %10s" % ("year/paper", "db", "unlockias",
                                         "no db_text", "no ul_text"))
    keys = sorted(papers)
    for k in keys:
        print("%-12s %10d %10d %10d %10d"
              % ("%s %s" % k, populated[(k, "db")], populated[(k, "ul")],
                 no_text[(k, "db")], no_text[(k, "ul")]))
    print("%-12s %10d %10d %10d %10d"
          % ("TOTAL", sum(populated[(k, "db")] for k in keys),
             sum(populated[(k, "ul")] for k in keys),
             sum(no_text[(k, "db")] for k in keys),
             sum(no_text[(k, "ul")] for k in keys)))
    touched = sum(1 for r in rows
                  if r["phase2_db_verdict"] or r["phase2_unlockias_verdict"])
    print("worklist rows carrying at least one phase-2 verdict: %d" % touched)
    print()

    print("=== phase-2 verdict distribution on the populated rows ===")
    for side, col in (("db", "phase2_db_verdict"),
                      ("unlockias", "phase2_unlockias_verdict")):
        c = Counter(r[col] for r in rows if r[col])
        print("  %-10s %s" % (side, ", ".join("%s=%d" % kv
                                              for kv in sorted(c.items()))))
    print()

    print("=== APPLY-ELIGIBLE SET (db orphan AND unlockias exact) ===")
    print("%-12s %10s %10s %8s  %s" % ("year/paper", "before", "after",
                                       "delta", "note"))
    ks = sorted(set(before) | set(after))
    for k in ks:
        b, a = before.get(k, 0), after.get(k, 0)
        note = []
        if b == 0 and a > 0:
            note.append("NEW IN SCOPE")
        if k in papers:
            note.append("phase-2 paper")
        if k[0] in HOLD_YEARS:
            note.append("HOLD (%s excluded by the operator brief)" % k[0])
        print("%-12s %10d %10d %+8d  %s"
              % ("%s %s" % k, b, a, a - b, "; ".join(note)))
    print("%-12s %10d %10d %+8d" % ("TOTAL", sum(before.values()),
                                    sum(after.values()),
                                    sum(after.values()) - sum(before.values())))
    print("eligible after hold-years are removed: %d"
          % sum(n for k, n in after.items() if k[0] not in HOLD_YEARS))
    print()

    print("=== why phase-2 orphan rows are still NOT eligible ===")
    reasons = Counter()
    for r in rows:
        if r.get("apply_eligible"):
            continue
        eff_db, src = effective(r, DB_CHAIN)
        if eff_db != "orphan" or src != "phase2_db_verdict":
            continue
        eff_ul = effective(r, UL_CHAIN)[0]
        reasons[(r["year"], r["paper"],
                 eff_ul or "(no paired UnlockIAS text)")] += 1
    for k in sorted(reasons):
        print("  %s %s  unlockias=%-28s %d" % (k[0], k[1], k[2], reasons[k]))
    print()

    print("=== worklist rows with NO verdict of any kind, after the merge ===")
    none_ = Counter()
    for r in rows:
        if effective(r, DB_CHAIN)[0] or effective(r, UL_CHAIN)[0]:
            continue
        none_[(r["year"], r["paper"])] += 1
    by_year = defaultdict(int)
    for k in sorted(none_):
        print("  %s %s: %d" % (k[0], k[1], none_[k]))
        by_year[k[0]] += none_[k]
    print("  total: %d of %d worklist rows" % (sum(none_.values()), len(rows)))
    print()
    print("  reason per remaining bucket:")
    for y in sorted(by_year):
        print("  - %s (%d rows): %s"
              % (y, by_year[y], NO_VERDICT_CAUSE.get(y, "unclassified")))

    print()
    print("=== phase-2 papers: rows left without a DB verdict ===")
    left = Counter()
    for r in rows:
        if (r["year"], r["paper"]) not in papers:
            continue
        if effective(r, DB_CHAIN)[0]:
            continue
        left[(r["year"], r["paper"])] += 1
    for k in sorted(left):
        print("  %s %s: %d (no db_text - insert candidates, nothing to score)"
              % (k[0], k[1], left[k]))
    print("  total: %d" % sum(left.values()))


if __name__ == "__main__":
    main()
