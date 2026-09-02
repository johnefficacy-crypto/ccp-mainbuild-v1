"""Compare every option text, label by label, between the DB and the JSON files.

The key migration only checks the option at the *key* label. A rotation among
the three distractors would pass that check silently, so this compares all four.

Detects, per question:
  ROTATED   the same four texts are present but on different labels
  DIFFERS   a label's text differs and it is not a rotation
  MISSING   a label present in one source and absent from the other

Inputs: db_options.csv (year, question_number, option_label, option_id,
        question_id, option_text) and pyq_<year>_prelims_gs1_set<x>.json

This detects divergence between two sources, not correctness. Both came through
the same docx parser, so a fault shared by both will pass. Anything it reports
needs checking against the official question paper before you decide which side
is wrong.

Run from the repo root:  python option_audit.py
"""
import csv, json, os, re, sys
from collections import defaultdict

DUMP = "db_options.csv"


def norm(s):
    s = (s or "").lower()
    s = s.replace("\u2018", "'").replace("\u2019", "'")
    s = s.replace("\u201c", '"').replace("\u201d", '"')
    s = s.replace("\u2013", "-").replace("\u2014", "-")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return s.strip()


if not os.path.exists(DUMP):
    sys.exit(f"missing {DUMP}")

db = defaultdict(lambda: defaultdict(dict))
with open(DUMP, encoding="utf-8-sig", newline="") as fh:
    for r in csv.DictReader(fh):
        db[str(r["year"]).strip()][int(r["question_number"])][
            r["option_label"].strip().lower()] = r["option_text"]

rotated, differs, missing, checked = [], [], [], 0

for fn in sorted(f for f in os.listdir(".")
                 if f.startswith("pyq_") and "_prelims_gs1_set" in f
                 and f.endswith(".json")):
    year = fn.split("_")[1]
    if year not in db:
        print(f"{year}: not in dump, skipped")
        continue

    for q in json.load(open(fn, encoding="utf-8"))["questions"]:
        n = q["question_number"]
        dbq = db[year].get(n)
        if not dbq:
            continue
        jsq = {o.get("label", "").lower(): o.get("text")
               for o in q.get("options", [])}
        checked += 1

        for lab in sorted(set(dbq) | set(jsq)):
            if lab not in dbq:
                missing.append((year, n, lab, "absent from DB"))
            elif lab not in jsq:
                missing.append((year, n, lab, "absent from JSON"))

        shared = sorted(set(dbq) & set(jsq))
        bad = [l for l in shared if norm(dbq[l]) != norm(jsq[l])]
        if not bad:
            continue

        # Rotation: same multiset of texts, different label assignment.
        if sorted(norm(dbq[l]) for l in shared) == \
           sorted(norm(jsq[l]) for l in shared):
            moved = {}
            for l in bad:
                target = next((m for m in shared
                               if norm(jsq[m]) == norm(dbq[l])), "?")
                moved[l] = target
            rotated.append((year, n, moved))
        else:
            for l in bad:
                differs.append((year, n, l, jsq[l], dbq[l]))

print(f"checked {checked} questions\n")

if rotated:
    print(f"ROTATED ({len(rotated)} questions) "
          "-- same texts, wrong labels. Highest risk: invisible to count "
          "checks, and puts the key on the wrong option.")
    for year, n, moved in rotated:
        m = ", ".join(f"db {a} = json {b}" for a, b in sorted(moved.items()))
        print(f"   {year} Q{n}: {m}")
    print()

if differs:
    print(f"DIFFERS ({len(differs)} options)")
    for year, n, lab, j, d in differs:
        print(f"   {year} Q{n} ({lab})")
        print(f"      json: {j!r}")
        print(f"      db:   {d!r}")
    print()

if missing:
    print(f"MISSING ({len(missing)})")
    for year, n, lab, why in missing:
        print(f"   {year} Q{n} ({lab}): {why}")
    print()

if not (rotated or differs or missing):
    print("no divergence between DB and JSON on any option label.")
