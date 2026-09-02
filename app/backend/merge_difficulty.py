"""Merge difficulty-<year>-draft.csv into worksheet-<year>.filled.csv.

Fills the difficulty column on QUESTION rows, matching on question_number.
Refuses to overwrite a non-empty difficulty. Rejects anything that is not
easy/medium/hard, so a bad value fails here rather than at apply time.

Rewrites worksheet-<year>.filled.csv in place after backing it up to .bak.

Usage:  python merge_difficulty.py 2018
        python merge_difficulty.py all
"""
import csv, os, shutil, sys

YEARS = ["2018", "2019", "2021", "2022", "2023", "2024"]
VALID = {"easy", "medium", "hard"}

if len(sys.argv) != 2:
    sys.exit("usage: python merge_difficulty.py <year|all>")

targets = YEARS if sys.argv[1].lower() == "all" else [sys.argv[1]]

for year in targets:
    ws = f"worksheet-{year}.filled.csv"
    df = f"difficulty-{year}-draft.csv"
    if not os.path.exists(ws) or not os.path.exists(df):
        print(f"{year}: missing {ws if not os.path.exists(ws) else df} — skipped")
        continue

    diff = {}
    bad = []
    with open(df, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            d = r["difficulty"].strip().lower()
            if d not in VALID:
                bad.append((r["question_number"], d))
                continue
            diff[r["question_number"].strip()] = (d, r.get("confidence", "").strip())
    if bad:
        print(f"{year}: invalid difficulty values {bad} — aborted")
        continue

    with open(ws, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fields = reader.fieldnames
        rows = list(reader)

    if "difficulty" not in fields:
        print(f"{year}: worksheet has no difficulty column — skipped")
        continue

    filled = skipped = 0
    lowconf = []
    for r in rows:
        if r.get("row_type") != "question":
            continue
        q = (r.get("question_number_or_topic_id") or "").strip()
        if q not in diff:
            skipped += 1
            continue
        if (r.get("difficulty") or "").strip():
            skipped += 1
            continue
        d, conf = diff[q]
        r["difficulty"] = d
        filled += 1
        if conf == "low":
            lowconf.append((q, d))

    shutil.copy2(ws, ws + ".bak")
    with open(ws, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    msg = f"{year}: {filled} filled, {skipped} skipped"
    if lowconf:
        msg += "  | low confidence: " + ", ".join(f"Q{q}={d}" for q, d in lowconf)
    print(msg)
