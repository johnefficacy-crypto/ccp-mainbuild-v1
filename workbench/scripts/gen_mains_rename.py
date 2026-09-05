"""Generate the Mains microtopic rename + orphan-deactivation migration.

Reads the approved proposal and emits SQL that:

  1. renames all 426 verified Mains microtopics to short readable names
  2. regenerates each slug from the new name
  3. preserves the full untruncated source text in metadata.full_description
  4. deactivates the 18 pre-split orphans

Why the full text is preserved: 42 of the 426 names were truncated at exactly
300 characters by the column limit, and the source text carries the scope detail
a reviewer needs even though it is unreadable on a chart. It comes from
syllabus_topic_mentions.raw_text on document 2bfbc4bb, not from topics.name,
so the truncation is not carried forward.

The 18 orphans are pre-split rows left behind by PR #1013: 14 "Contemporary …
themes", two "Miscellaneous … themes", "Case-study archetypes" and "Flagship
schemes for vulnerable groups". They are absent from the verified 456-mention
set and carry zero primary tags — confirmed by query before this was written.
Deactivating rather than deleting keeps them recoverable and keeps any
historical FK intact.

Inputs
  mains-rename-proposal.csv   id, subject, method, proposed_name, full_name

Output
  mains_microtopic_rename.sql

Run from the repo root:  python gen_mains_rename.py
"""
import csv, hashlib, os, re, sys, json

SRC = "workbench/catalogs/mains-rename-proposal.csv"
OUT = "mains_microtopic_rename.sql"

ORPHANS = [
 '9f4e8c3c-5848-426d-b94d-bd0dcd61ceee','e985eec7-1892-498f-a043-41798b1e1480',
 'fbe18f61-cac9-41a3-88f2-c0aa78d57802','a3284754-ee69-4931-8653-2f98e7ebd76a',
 'd0b5594e-8416-47b3-b06b-13c227b72421','27a388e4-9648-4da4-8328-d0aa92b7d3af',
 'd19b8f09-c461-495e-b88c-ea96b791f9c0','da3a5849-aa34-4290-9ec4-a4c9937c9f17',
 '08be0cf6-778c-42c5-88d8-0c941f0cadd2','c2b5c010-2390-41a4-9d4b-ada83e95c788',
 '8255e2a0-76e2-4cfd-b3ff-fcb8af87baae','e32b3e50-d206-402a-a2cf-a623b7544841',
 '2bb22d62-cc65-4ee2-8477-9b0f334d53e1','d2730696-4878-4a11-a806-9955b693e5b6',
 'bf975128-6ca9-4674-9e90-f15afe4250fc','a46877f5-18ba-4125-ab77-7799541bc8cb',
 '64e81c50-6b2b-468c-b940-9c7a08a4cc61','da6e368f-bf7d-4b84-b1e0-931ac30de4ed',
]

SUBJ_PREFIX = {
 'General Studies I': 'gs1', 'General Studies II': 'gs2',
 'General Studies III': 'gs3', 'General Studies IV': 'gs4',
}

if not os.path.exists(SRC):
    sys.exit(f"missing {SRC}")


def slugify(prefix, name):
    kebab = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:80]
    return f"{prefix}-{kebab}-{hashlib.md5(name.encode()).hexdigest()[:8]}"


def q(s):
    return "'" + s.replace("'", "''") + "'"


rows = []
for enc in ("utf-8", "cp1252"):
    try:
        with open(SRC, encoding=enc, newline="") as fh:
            rows = list(csv.DictReader(fh))
        break
    except UnicodeDecodeError:
        continue
if not rows:
    sys.exit(f"could not decode {SRC}")

seen, updates = set(), []
for r in rows:
    name = r["proposed_name"].strip()
    if not name:
        sys.exit(f"row {r['id']} has no proposed_name")
    prefix = SUBJ_PREFIX.get(r["subject"])
    if prefix is None:
        sys.exit(f"unexpected subject {r['subject']!r}")
    slug = slugify(prefix, name)
    if slug in seen:
        sys.exit(f"slug collision on {slug!r} — resolve before generating")
    seen.add(slug)
    updates.append((r["id"], name, slug, r["full_name"].strip()))

if len(updates) != 426:
    sys.exit(f"expected 426 rows, got {len(updates)}")

with open(OUT, "w", encoding="utf-8") as fh:
    fh.write(f"""-- Mains microtopic rename: 426 renamed, 18 orphans deactivated.
--
-- The Mains catalogue was ingested from a curated micro-theme JSON, so its
-- names are scope descriptions rather than labels: median 129 characters, 174
-- over 200, and 42 truncated at exactly 300 by the column limit. Unusable on an
-- aspirant-facing chart, and hard to read anywhere.
--
-- This gives each microtopic a short name and moves the scope detail to
-- metadata.full_description, taken from syllabus_topic_mentions.raw_text on
-- document 2bfbc4bb (the verified 456-mention set), so the 42 truncated names
-- are restored rather than carried forward.
--
-- How the names were derived:
--   307  leading concept before the first colon — Biogeography, Aurangzeb
--    58  split children of the PR #1013 grab-bags, prefixed "Recent
--         developments:" so the two-tier structure is visible. These carry
--         dated items and have a shelf life; the enduring sibling does not.
--    46  hand-written where no usable head existed
--    15  split-family children keeping their distinguishing clause
--
-- Ids are unchanged. Names are display-only: every functional path keys on
-- topic_id, exam_topic_coverage has no name column, user_topic_mastery_audit is
-- empty, and ewp_error_lab joins to topics live. Verified before writing this.
--
-- The 18 deactivated rows are pre-split orphans from PR #1013, absent from the
-- verified mention set and carrying zero primary tags.

BEGIN;

-- Abort unless every id is a live Mains microtopic in the verified set.
DO $$
DECLARE bad int;
BEGIN
  SELECT count(*) INTO bad FROM (VALUES
""")
    fh.write(",\n".join(f"    ({q(u[0])}::uuid)" for u in updates))
    fh.write("""
  ) AS v(id)
  WHERE NOT EXISTS (
    SELECT 1 FROM public.topics t
    JOIN public.subjects s ON s.id = t.subject_id
    WHERE t.id = v.id AND t.level = 'microtopic'
      AND s.name IN ('General Studies I','General Studies II',
                     'General Studies III','General Studies IV'));
  IF bad > 0 THEN
    RAISE EXCEPTION '% id(s) are not live Mains microtopics', bad;
  END IF;
END $$;

UPDATE public.topics t SET
  name     = v.name,
  slug     = v.slug,
  metadata = coalesce(t.metadata, '{}'::jsonb)
             || jsonb_build_object('full_description', v.full_text)
FROM (VALUES
""")
    fh.write(",\n".join(
        f"  ({q(i)}::uuid, {q(n)}, {q(s)}, {q(f)})" for i, n, s, f in updates))
    fh.write(f"""
) AS v(id, name, slug, full_text)
WHERE t.id = v.id;

-- Pre-split orphans from PR #1013. Zero primary tags, absent from the verified
-- 456-mention set. Deactivated, not deleted.
UPDATE public.topics SET is_active = false
WHERE id IN (
""")
    fh.write(",\n".join(f"  {q(o)}::uuid" for o in ORPHANS))
    fh.write(f""");

-- Final assertions.
DO $$
DECLARE renamed int; long_names int; orphaned int;
BEGIN
  SELECT count(*) INTO renamed FROM public.topics t
   WHERE t.metadata ? 'full_description';
  IF renamed < {len(updates)} THEN
    RAISE EXCEPTION 'expected at least {len(updates)} renamed rows, got %', renamed;
  END IF;

  SELECT count(*) INTO long_names FROM public.topics t
    JOIN public.subjects s ON s.id = t.subject_id
   WHERE s.name IN ('General Studies I','General Studies II',
                    'General Studies III','General Studies IV')
     AND t.level = 'microtopic' AND t.is_active AND length(t.name) > 80;
  IF long_names > 0 THEN
    RAISE EXCEPTION '% active Mains microtopic(s) still exceed 80 chars', long_names;
  END IF;

  SELECT count(*) INTO orphaned FROM public.topics
   WHERE id IN ({",".join(q(o) + "::uuid" for o in ORPHANS)}) AND is_active;
  IF orphaned > 0 THEN
    RAISE EXCEPTION '% orphan(s) still active', orphaned;
  END IF;
END $$;

COMMIT;
""")

print(f"{len(updates)} renames, {len(ORPHANS)} deactivations -> {OUT}")
lens = sorted(len(u[1]) for u in updates)
print(f"new name length: min {lens[0]}, median {lens[len(lens)//2]}, max {lens[-1]}")
print(f"unique slugs: {len(seen)}")
