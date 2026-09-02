"""Generate the answer-key migration for UPSC Prelims GS Paper I, 2018-2024.

Inputs
  db_options.csv                    dump of year, question_number, option_label,
                                    option_id, question_id, option_text
  pyq_<year>_prelims_gs1_set<x>.json  source files, correct_option_label already
                                    rekeyed from the official UPSC answer keys

Output
  answer_key_migration.sql          two UPDATE statements in one transaction

The generator verifies, per question, that the option text the JSON carries at
the key label matches the option text the DB holds at that same label. A
divergence means the two disagree about which option is which, so the key label
cannot be trusted to point at the same thing -- that row is skipped and reported
rather than written.

Dropped questions (correct_option_label null) are skipped and left NULL.

Run from the repo root:  python gen_key_migration.py
"""
import csv, json, os, re, sys
from collections import defaultdict

DUMP = "db_options.csv"
OUT = "answer_key_migration.sql"


def norm(s):
    """Loose comparison: case, whitespace, punctuation and quote style."""
    s = (s or "").lower()
    s = s.replace("\u2018", "'").replace("\u2019", "'")
    s = s.replace("\u201c", '"').replace("\u201d", '"')
    s = s.replace("\u2013", "-").replace("\u2014", "-")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return s.strip()


if not os.path.exists(DUMP):
    sys.exit(f"missing {DUMP} - run the operator SELECT first")

# year -> qnum -> label -> (option_id, question_id, option_text)
db = defaultdict(lambda: defaultdict(dict))
with open(DUMP, encoding="utf-8-sig", newline="") as fh:
    for r in csv.DictReader(fh):
        db[str(r["year"]).strip()][int(r["question_number"])][
            r["option_label"].strip().lower()
        ] = (r["option_id"].strip(), r["question_id"].strip(), r["option_text"])

rows, skipped, dropped = [], [], []

for fn in sorted(f for f in os.listdir(".")
                 if f.startswith("pyq_") and "_prelims_gs1_set" in f):
    year = fn.split("_")[1]
    if year not in db:
        skipped.append((year, "-", "year absent from db_options.csv"))
        continue

    for q in json.load(open(fn, encoding="utf-8"))["questions"]:
        n = q["question_number"]
        label = (q.get("correct_option_label") or "").strip().lower()

        if not label:
            dropped.append((year, n))
            continue

        dbq = db[year].get(n)
        if not dbq:
            skipped.append((year, n, "question not in DB dump"))
            continue
        if label not in dbq:
            skipped.append((year, n, f"label {label!r} not in DB "
                                     f"{sorted(dbq)}"))
            continue

        option_id, question_id, db_text = dbq[label]
        json_text = next((o.get("text") for o in q.get("options", [])
                          if o.get("label") == label), None)

        if norm(json_text) != norm(db_text):
            skipped.append((year, n,
                            f"option text differs at {label!r}: "
                            f"json={json_text!r} db={db_text!r}"))
            continue

        rows.append((question_id, option_id, year, n, label))

print(f"{len(rows)} keys resolved, {len(dropped)} dropped questions skipped, "
      f"{len(skipped)} skipped")
for year, n in dropped:
    print(f"   dropped  {year} Q{n}")
for year, n, why in skipped:
    print(f"   SKIP     {year} Q{n}: {why}")

if skipped:
    print("\nSkipped rows above are NOT in the migration. Resolve them "
          "before loading, or accept that those questions stay keyless.")

if not rows:
    sys.exit("nothing to write")

with open(OUT, "w", encoding="utf-8") as fh:
    fh.write(f"""-- Answer keys for UPSC Prelims GS Paper I, 2018-2024.
--
-- Source: the official UPSC answer-key PDFs, per series:
--   2018 Set C, 2019 Set B, 2021 Set C, 2022 Set A, 2023 Set A, 2024 Set C.
--
-- These keys were never loaded at import time; every question in the corpus
-- carried correct_option_id NULL and every option is_correct false. The JSON
-- source files' correct_option_label field disagreed with the official keys on
-- 102 of 595 questions and was regenerated from the PDFs before this migration
-- was produced.
--
-- {len(rows)} questions keyed. {len(dropped)} questions dropped by UPSC keep
-- correct_option_id NULL and are deliberately absent from this migration.

BEGIN;

UPDATE public.pyq_options o
SET is_correct = true
FROM (VALUES
""")
    fh.write(",\n".join(
        f"  ('{oid}'::uuid)"
        for _, oid, y, n, lab in rows))
    fh.write("""
) AS v(option_id)
WHERE o.id = v.option_id;

UPDATE public.pyq_questions q
SET correct_option_id = v.option_id
FROM (VALUES
""")
    fh.write(",\n".join(
        f"  ('{qid}'::uuid, '{oid}'::uuid)"
        for qid, oid, _, _, _ in rows))
    fh.write("""
) AS v(question_id, option_id)
WHERE q.id = v.question_id;

COMMIT;
""")

print(f"\nwrote {OUT}")
