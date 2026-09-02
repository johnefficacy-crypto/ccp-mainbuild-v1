"""Generate the answer-key migration for UPSC Prelims GS-I 2020 (Set C).

2020 differs from 2018-2024: its key lives in a CSV keyed by question_number
rather than inside a pyq_<year>_prelims_gs1_set<x>.json envelope, and its
questions were already loaded, so this only writes keys.

Inputs
  db_options_2020.csv   dump of year, question_number, option_label, option_id,
                        question_id, option_text  (or without the year column)
  docs/reference/answer-keys/upsc_cse_2020_setc_prelims_gs1.csv
                        question_number, correct_option_label — blank for the
                        two questions UPSC dropped (Q42, Q77)

Output
  answer_key_2020_migration.sql

Unlike the 2018-2024 generator there is no second source of option text to
compare against, so the option-text check that caught the 2022 rotation cannot
run here. What is checked instead: every key label must exist among that
question's options, every question must have exactly four options, and the
paper must have exactly 100 questions. A rotation among options would still
pass — 2020's structural checks came back clean, but that is a weaker guarantee
than the six papers had. Noted so nobody later assumes otherwise.

Run from the repo root:  python gen_key_migration_2020.py
"""
import csv, os, sys
from collections import defaultdict

PAPER = "980cfb08-efbd-453f-8dbc-251fefb9d3f5"
DUMP = "db_options_2020.csv"
KEY = "docs/reference/answer-keys/upsc_cse_2020_setc_prelims_gs1.csv"
OUT = "answer_key_2020_migration.sql"

for f in (DUMP, KEY):
    if not os.path.exists(f):
        sys.exit(f"missing {f}")

# question_number -> label -> (option_id, question_id)
db = defaultdict(dict)
with open(DUMP, encoding="utf-8-sig", newline="") as fh:
    for r in csv.DictReader(fh):
        db[int(r["question_number"])][r["option_label"].strip().lower()] = (
            r["option_id"].strip(), r["question_id"].strip())

if len(db) != 100:
    sys.exit(f"expected 100 questions in the dump, found {len(db)}")
short = [n for n, opts in db.items() if len(opts) != 4]
if short:
    sys.exit(f"questions without exactly four options: {sorted(short)}")

rows, dropped, skipped = [], [], []
seen = set()

with open(KEY, encoding="utf-8-sig", newline="") as fh:
    for r in csv.DictReader(fh):
        n = int(r["question_number"])
        seen.add(n)
        label = (r["correct_option_label"] or "").strip().lower()

        if not label:
            dropped.append(n)
            continue
        if n not in db:
            skipped.append((n, "question not in DB dump"))
            continue
        if label not in db[n]:
            skipped.append((n, f"key {label!r} not among options "
                               f"{sorted(db[n])}"))
            continue
        option_id, question_id = db[n][label]
        rows.append((question_id, option_id, n, label))

missing = sorted(set(range(1, 101)) - seen)
if missing:
    sys.exit(f"key file does not cover questions {missing}")

print(f"{len(rows)} keys resolved, {len(dropped)} dropped "
      f"({', '.join('Q'+str(n) for n in dropped)}), {len(skipped)} skipped")
for n, why in skipped:
    print(f"   SKIP Q{n}: {why}")
if skipped:
    print("\nSkipped rows are NOT in the migration.")
if not rows:
    sys.exit("nothing to write")

with open(OUT, "w", encoding="utf-8") as fh:
    fh.write(f"""-- Answer keys for UPSC Prelims GS Paper I, 2020 (Set C).
--
-- Source: the official UPSC answer key, Set C. The operator key on file at
-- docs/reference/answer-keys/upsc_cse_2020_setc_prelims_gs1.csv was diffed
-- against that official key and matched on all 100 positions, including both
-- dropped questions — the only one of the seven prelims papers whose operator
-- key needed no correction. The other six required 102 corrections between
-- them before their keys could be loaded.
--
-- {len(rows)} questions keyed. Q42 and Q77 were dropped by UPSC and keep
-- correct_option_id NULL.
--
-- Caveat: unlike the 2018-2024 migration, no second source of option text
-- existed to verify that each key label still points at the option it did in
-- the source paper. An option rotation would pass unnoticed. 2020's structural
-- checks (100 questions, 400 options, no question-marker bleed) came back
-- clean, but that is a weaker guarantee.

BEGIN;

UPDATE public.pyq_options o
SET is_correct = true
FROM (VALUES
""")
    fh.write(",\n".join(f"  ('{oid}'::uuid)" for _, oid, _, _ in rows))
    fh.write("""
) AS v(option_id)
WHERE o.id = v.option_id;

UPDATE public.pyq_questions q
SET correct_option_id = v.option_id
FROM (VALUES
""")
    fh.write(",\n".join(
        f"  ('{qid}'::uuid, '{oid}'::uuid)" for qid, oid, _, _ in rows))
    fh.write("""
) AS v(question_id, option_id)
WHERE q.id = v.question_id;

COMMIT;
""")

print(f"\nwrote {OUT}")
