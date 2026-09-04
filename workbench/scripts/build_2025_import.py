"""Build the v1 bulk-import array for UPSC CSE Prelims 2025 GS Paper I, Set A.

Merges the question file (stems + options, no answers) with the official Set A
answer key into the flat v1 row shape pyq_bulk_import.parse_bytes expects:

    question_number, question_text, option_a..option_d, correct_option,
    question_type

v1 requires correct_option on every row — there is no keyless load through this
importer, and a placeholder key would mark a wrong option true on roughly three
questions in four. So the key is merged in here, not backfilled later.

Inputs
  upsc_csp_2025_gs1.json                      100 questions, q_no 1-100
  docs/reference/answer-keys/upsc_cse_2025_seta_prelims_gs1.csv

Output
  pyq_2025_prelims_gs1_seta_v1.json           bare array, ready to POST

Run from the repo root:  python build_2025_import.py
"""
import csv, json, os, sys

SRC = "upsc_csp_2025_gs1.json"
KEY = "docs/reference/answer-keys/upsc_cse_2025_seta_prelims_gs1.csv"
OUT = "pyq_2025_prelims_gs1_seta_v1.json"

for f in (SRC, KEY):
    if not os.path.exists(f):
        sys.exit(f"missing {f}")

doc = json.load(open(SRC, encoding="utf-8"))
qs = doc["questions"]

if doc.get("booklet_series") != "A":
    sys.exit(f"expected booklet_series A, got {doc.get('booklet_series')!r}")

key = {}
with open(KEY, encoding="utf-8-sig", newline="") as fh:
    for r in csv.DictReader(fh):
        label = (r["correct_option_label"] or "").strip().upper()
        if label:
            key[int(r["question_number"])] = label

missing_key = sorted(set(q["q_no"] for q in qs) - set(key))
if missing_key:
    sys.exit(f"no key for question(s) {missing_key} — v1 requires correct_option "
             f"on every row; a keyless or placeholder row would mark a wrong "
             f"option correct")

rows = []
for q in sorted(qs, key=lambda x: x["q_no"]):
    n = q["q_no"]
    opts = q["options"]
    for lbl in ("a", "b", "c", "d"):
        if not (opts.get(lbl) or "").strip():
            sys.exit(f"Q{n} option {lbl} is empty")
    rows.append({
        "question_number": n,
        "question_text": q["stem"].strip(),
        "option_a": opts["a"].strip(),
        "option_b": opts["b"].strip(),
        "option_c": opts["c"].strip(),
        "option_d": opts["d"].strip(),
        "correct_option": key[n],
        "question_type": "mcq",
    })

nums = [r["question_number"] for r in rows]
if sorted(nums) != list(range(1, 101)):
    sys.exit(f"expected question_number 1-100 contiguous, got {len(nums)} rows")

json.dump(rows, open(OUT, "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

from collections import Counter
print(f"{len(rows)} rows -> {OUT}")
print("answer distribution:", dict(sorted(Counter(r['correct_option'] for r in rows).items())))
print("\nNOTE: v1 does not set section_id. All 100 questions will land with")
print("section_id NULL and need backfilling to 545e98d7-4088-484d-a8bd-b12ca40e82e5")
print("after commit — the same gap that caught three manually inserted 2018 rows.")
