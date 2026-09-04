"""Merge tags-<year>-draft.csv into worksheet-<year>.csv on question_number.

Fills assign_topic_id on QUESTION rows only. Leaves difficulty and decision
blank. Refuses to overwrite a non-empty assign_topic_id. Writes
worksheet-<year>.filled.csv and leaves the original untouched.

Usage:  python merge_tags.py 2019
"""
import csv, os, sys

if len(sys.argv) != 2 or not sys.argv[1].isdigit():
    sys.exit("usage: python merge_tags.py <year>")

year = sys.argv[1]
WORKSHEET = f"worksheet-{year}.csv"
DRAFT = f"tags-{year}-draft.csv"
OUT = f"worksheet-{year}.filled.csv"

for f in (WORKSHEET, DRAFT):
    if not os.path.exists(f):
        sys.exit(f"missing {f}")

draft = {}
with open(DRAFT, encoding="utf-8-sig", newline="") as fh:
    for r in csv.DictReader(fh):
        draft[r["question_number"].strip()] = (
            r["assign_topic_id"].strip(),
            r.get("microtopic_name", "").strip(),
            r.get("confidence", "").strip(),
        )

with open(WORKSHEET, encoding="utf-8-sig", newline="") as fh:
    reader = csv.DictReader(fh)
    fields = reader.fieldnames
    rows = list(reader)

if "assign_topic_id" not in fields:
    sys.exit("worksheet has no assign_topic_id column")

filled = skipped = 0
flagged = []

for r in rows:
    if r.get("row_type") != "question":
        continue
    qnum = (r.get("question_number_or_topic_id") or "").strip()
    if qnum not in draft:
        skipped += 1
        continue
    if (r.get("assign_topic_id") or "").strip():
        skipped += 1
        continue
    topic_id, name, conf = draft[qnum]
    if not topic_id:
        skipped += 1
        continue
    r["assign_topic_id"] = topic_id
    filled += 1
    if conf in ("check", "gap"):
        flagged.append((qnum, conf, name))

with open(OUT, "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

print(f"{year}: {filled} rows filled, {skipped} skipped -> {OUT}")
if flagged:
    print(f"\n{len(flagged)} need your judgement before applying:")
    for qnum, conf, name in sorted(flagged, key=lambda t: int(t[0])):
        print(f"   Q{qnum:<4} [{conf}]  {name}")
print("\ndifficulty and decision left blank.")
