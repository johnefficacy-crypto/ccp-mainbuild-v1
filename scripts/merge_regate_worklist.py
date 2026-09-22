#!/usr/bin/env python3
r"""
merge_regate_worklist.py - merge the re-gated verdicts into repair_worklist.csv
and recompute the apply-eligible set.

Fully offline: no DB, no network, no re-OCR. Read-only on the OCR caches and the
extraction JSONs. The only file written is repair_worklist.csv, and only by
APPENDING columns - every existing column, including the phase-3 columns, is
copied through verbatim.

HOW THE MERGE IS DONE (and why it is not a row join)
----------------------------------------------------
`ocr_regate_verdict.csv` is keyed by SOURCE-JSON question; `repair_worklist.csv`
is keyed by DB question. They are not 1:1 - e.g. 2016 GS1 has 40 source rows
(two source files contribute 20 each) against 27 worklist rows. Joining them on
(year, paper, number) would silently mis-pair rows.

So the merge re-scores the worklist's OWN text columns against the same cached
OCR, using the same scoring function the re-gate used. The re-gate decides WHICH
papers are in play; the worklist rows are then scored directly. This is exactly
how phase 3 populated its own worklist columns.

Both sides are scored. The eligibility rule needs a DB verdict AND an UnlockIAS
verdict, and for a re-gated paper the phase-3 UnlockIAS verdict is
`unverifiable` (the paper was gated out), so scoring only `db_text` would leave
every re-gated row ineligible by construction.

COLUMNS APPENDED
    regate_db_verdict, regate_db_score
    regate_unlockias_verdict, regate_unlockias_score
    gate_relaxed            true only on rows whose paper the re-gate admitted
    apply_eligible          true where the EFFECTIVE verdicts meet the rule

EFFECTIVE VERDICT = the re-gated verdict where one exists, else the phase-3
verdict. ELIGIBLE = effective DB verdict `orphan` AND effective UnlockIAS
verdict `exact`.
"""

import csv
import os
from collections import Counter, defaultdict

import reconcile_gs_sources as R
import ocr_regate as G

WORKLIST = os.path.join(R.OUT_DIR, "repair_worklist.csv")

NEW_COLS = ["regate_db_verdict", "regate_db_score",
            "regate_unlockias_verdict", "regate_unlockias_score",
            "gate_relaxed",
            "late_db_verdict", "late_db_score",
            "late_unlockias_verdict", "late_unlockias_score",
            "apply_eligible"]

# Papers phase 3 could not classify, resolved later by operator decision and
# scored by ocr_phase3_late.py. They are a separate pass from the re-gate: those
# papers were excluded by the raw-token gate, these by a failed classification.
LATE_PAPERS = [("2017", "GS2"), ("2021", "GS1"), ("2023", "GS2")]

# Years the operator run was told to leave alone, for flagging only. This
# script writes nothing to any database; the flag exists so the report can
# separate "meets the rule" from "may actually be applied".
HOLD_YEARS = ("2013", "2014", "2015", "2026")


def relaxed_papers():
    """(year, paper) -> cached-OCR metrics, for papers the re-gate admitted."""
    papers = G.load_papers()
    floor, observed_min, clean = G.derive_floor(papers)
    out = {}
    for k, v in papers.items():
        new_pass = v["eng_words"] >= floor and v["noise"] <= G.MAX_NOISE_PCT
        old_pass = v["old_pass"]
        if new_pass and not old_pass:
            out[k] = v
    return out, floor, observed_min


def late_papers(floor):
    """(year, paper) -> cached-OCR metrics, for the late-classified papers."""
    out = {}
    for key in LATE_PAPERS:
        path = os.path.join(G.CACHE_DIR, "%s_%s.txt" % key)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as fh:
            m = G.metrics(fh.read())
        m["low_conf"] = m["eng_words"] < floor or m["noise"] > G.MAX_NOISE_PCT
        out[key] = m
    return out


def main():
    papers, floor, observed_min = relaxed_papers()
    late = late_papers(floor)

    with open(WORKLIST, encoding="utf-8-sig") as fh:
        rd = csv.DictReader(fh)
        rows = list(rd)
        fields = list(rd.fieldnames)
    fields_out = fields + [c for c in NEW_COLS if c not in fields]

    before = Counter()
    after = Counter()
    rescored = Counter()

    for r in rows:
        for c in NEW_COLS:
            r.setdefault(c, "")
        key = (r["year"], r["paper"])

        # pre-relaxation eligibility, for the before/after comparison
        was = (r.get("phase3_db_verdict") == "orphan"
               and r.get("phase3_unlockias_verdict") == "exact")
        if was:
            before[key] += 1

        info = papers.get(key)
        if info is not None:
            r["gate_relaxed"] = "true"
            if (r.get("db_text") or "").strip():
                v, s = G.score(R.normalize(r["db_text"]), info)
                r["regate_db_verdict"], r["regate_db_score"] = v, s
                rescored[(key, "db")] += 1
            if (r.get("unlockias_text") or "").strip():
                v, s = G.score(R.normalize(r["unlockias_text"]), info)
                r["regate_unlockias_verdict"], r["regate_unlockias_score"] = v, s
                rescored[(key, "ul")] += 1

        linfo = late.get(key)
        if linfo is not None:
            if (r.get("db_text") or "").strip():
                v, s = G.score(R.normalize(r["db_text"]), linfo)
                r["late_db_verdict"], r["late_db_score"] = v, s
                rescored[(key, "db")] += 1
            if (r.get("unlockias_text") or "").strip():
                v, s = G.score(R.normalize(r["unlockias_text"]), linfo)
                r["late_unlockias_verdict"], r["late_unlockias_score"] = v, s
                rescored[(key, "ul")] += 1

        # precedence: late-classified > re-gated > phase 3
        eff_db = (r["late_db_verdict"] or r["regate_db_verdict"]
                  or r.get("phase3_db_verdict") or "")
        eff_ul = (r["late_unlockias_verdict"] or r["regate_unlockias_verdict"]
                  or r.get("phase3_unlockias_verdict") or "")
        elig = (eff_db == "orphan" and eff_ul == "exact")
        r["apply_eligible"] = "true" if elig else ""
        if elig:
            after[key] += 1

    with open(WORKLIST, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=fields_out)
        w.writeheader()
        w.writerows(rows)

    report(rows, papers, before, after, floor, observed_min)


def report(rows, papers, before, after, floor, observed_min):
    print("re-gate floor: %d English words (30%% below clean minimum %d)"
          % (floor, observed_min))
    print("papers admitted by the re-gate: %d -> %s"
          % (len(papers), ", ".join("%s %s" % k for k in sorted(papers))))
    print()
    print("=== APPLY-ELIGIBLE SET (db orphan AND unlockias exact) ===")
    print("%-12s %10s %10s %8s  %s" % ("year/paper", "before", "after",
                                       "delta", "note"))
    keys = sorted(set(before) | set(after))
    for k in keys:
        b, a = before.get(k, 0), after.get(k, 0)
        note = []
        if b == 0 and a > 0:
            note.append("NEW IN SCOPE")
        if k in papers:
            note.append("re-gated paper")
        if k[0] in HOLD_YEARS:
            note.append("HOLD (%s excluded by the operator brief)" % k[0])
        print("%-12s %10d %10d %+8d  %s"
              % ("%s %s" % k, b, a, a - b, "; ".join(note)))
    print("%-12s %10d %10d %+8d" % ("TOTAL", sum(before.values()),
                                    sum(after.values()),
                                    sum(after.values()) - sum(before.values())))
    print()
    applyable = sum(n for k, n in after.items() if k[0] not in HOLD_YEARS)
    print("eligible after hold-years are removed: %d" % applyable)

    # why orphan rows fail the rule
    print()
    print("=== why orphan rows are NOT eligible ===")
    reasons = Counter()
    for r in rows:
        eff_db = (r["late_db_verdict"] or r["regate_db_verdict"]
                  or r.get("phase3_db_verdict") or "")
        if eff_db != "orphan" or r["apply_eligible"]:
            continue
        eff_ul = (r["late_unlockias_verdict"] or r["regate_unlockias_verdict"]
                  or r.get("phase3_unlockias_verdict") or "")
        reasons[(r["year"], r["paper"], eff_ul or "(no paired UnlockIAS text)")] += 1
    for k in sorted(reasons):
        print("  %s %s  unlockias=%-28s %d" % (k[0], k[1], k[2], reasons[k]))

    # unverifiable census
    print()
    print("=== still unverifiable ===")
    unv = Counter()
    for r in rows:
        eff_db = (r["late_db_verdict"] or r["regate_db_verdict"]
                  or r.get("phase3_db_verdict") or "")
        if eff_db == "unverifiable":
            unv[(r["year"], r["paper"])] += 1
    for k in sorted(unv):
        print("  %s %s: %d rows" % (k[0], k[1], unv[k]))
    print("  total: %d rows" % sum(unv.values()))

    print()
    print("=== worklist rows with NO verdict of any kind ===")
    none_ = Counter()
    for r in rows:
        eff = (r["late_db_verdict"] or r["regate_db_verdict"]
               or r.get("phase3_db_verdict") or "")
        if not eff:
            none_[(r["year"], r["paper"])] += 1
    for k in sorted(none_):
        print("  %s %s: %d" % (k[0], k[1], none_[k]))
    print("  total: %d of %d worklist rows" % (sum(none_.values()), len(rows)))
    blank_text = sum(1 for r in rows
                     if not (r.get("db_text") or "").strip()
                     and not (r["late_db_verdict"] or r["regate_db_verdict"]
                              or r.get("phase3_db_verdict") or ""))
    print("  of which carry no db_text at all (insert candidates): %d" % blank_text)


if __name__ == "__main__":
    main()
