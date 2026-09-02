"""Generate the microtopic rename + study_sources migration from the review CSV.

Input:  microtopics-with-sources.csv
Output: microtopic_rename.sql

For each row it emits, where the proposed name differs or sources exist:
  - name  = proposed_name
  - slug  = gs-<kebab>-<8hex of proposed_name>
  - metadata gains study_sources: [{type, ref}, ...]

Rows whose proposed_name starts with DROP or MERGE are deactivated instead
(is_active = false), not deleted -- nothing is tagged to them yet, and
deactivating is reversible.

Ids in the CSV are 8-character prefixes. The SQL matches on prefix and the
whole migration aborts if any prefix does not resolve to exactly one row.

Run from the repo root:  python gen_rename_migration.py
"""
import csv, hashlib, json, os, re, sys

SRC = "microtopics-with-sources.csv"
OUT = "microtopic_rename.sql"

if not os.path.exists(SRC):
    sys.exit(f"missing {SRC}")


def slugify(name):
    kebab = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return f"gs-{kebab}-{hashlib.md5(name.encode()).hexdigest()[:8]}"


def sql_str(s):
    return "'" + s.replace("'", "''") + "'"


updates, deactivate = [], []

with open(SRC, encoding="utf-8-sig", newline="") as fh:
    for r in csv.DictReader(fh):
        prefix = r["id"].strip()
        proposed = r["proposed_name"].strip()

        if proposed.upper().startswith(("DROP", "MERGE")):
            deactivate.append((prefix, r["current_name"].strip(), proposed))
            continue

        sources = []
        if r["ncert_source"].strip():
            sources.append({"type": "ncert", "ref": r["ncert_source"].strip()})
        std = r["standard_source"].strip()
        if std and std.lower() != "ncert only":
            for part in [p.strip() for p in std.split(";") if p.strip()]:
                sources.append({"type": "standard", "ref": part})

        updates.append((prefix, proposed, slugify(proposed), sources))

with open(OUT, "w", encoding="utf-8") as fh:
    fh.write(f"""-- Microtopic renames and study-source pointers for UPSC GS.
--
-- Names moved to vocabulary aspirants already recognise: NCERT chapter and
-- subhead titles where a textbook covers the topic, plain exam vocabulary where
-- none does. Ids are unchanged, so nothing referencing a microtopic breaks.
--
-- metadata.study_sources is guidance, not provenance. It does not claim a
-- question was set from that chapter; it says this is where the syllabus a
-- candidate has already read connects to what the exam asks. Chapter TITLES are
-- stored rather than numbers, because NCERT renumbers between editions.
--
-- {len(updates)} renamed or sourced, {len(deactivate)} deactivated.

BEGIN;

-- Abort if any id prefix is ambiguous or missing.
DO $$
DECLARE bad int;
BEGIN
  SELECT count(*) INTO bad FROM (VALUES
""")
    all_prefixes = [u[0] for u in updates] + [d[0] for d in deactivate]
    fh.write(",\n".join(f"    ({sql_str(p)})" for p in all_prefixes))
    fh.write("""
  ) AS v(prefix)
  WHERE (SELECT count(*) FROM public.topics t
         WHERE t.id::text LIKE v.prefix || '%'
           AND t.level = 'microtopic') <> 1;
  IF bad > 0 THEN
    RAISE EXCEPTION 'id prefix does not resolve to exactly one microtopic: % rows', bad;
  END IF;
END $$;

UPDATE public.topics t SET
  name = v.name,
  slug = v.slug,
  metadata = t.metadata || jsonb_build_object('study_sources', v.sources)
FROM (VALUES
""")
    fh.write(",\n".join(
        f"  ({sql_str(p)}, {sql_str(n)}, {sql_str(s)}, "
        f"{sql_str(json.dumps(src, ensure_ascii=False))}::jsonb)"
        for p, n, s, src in updates))
    fh.write("""
) AS v(prefix, name, slug, sources)
WHERE t.id::text LIKE v.prefix || '%' AND t.level = 'microtopic';

""")

    if deactivate:
        fh.write("-- Deactivated: duplicate or merged elsewhere.\n")
        for prefix, cur, why in deactivate:
            fh.write(f"-- {cur} -> {why}\n")
        fh.write("UPDATE public.topics SET is_active = false\nWHERE ")
        fh.write(" OR ".join(
            f"id::text LIKE {sql_str(p)} || '%'" for p, _, _ in deactivate))
        fh.write(";\n\n")

    fh.write("COMMIT;\n")

print(f"{len(updates)} updates, {len(deactivate)} deactivations -> {OUT}")
for prefix, cur, why in deactivate:
    print(f"   deactivate {prefix}  {cur}  ({why})")
