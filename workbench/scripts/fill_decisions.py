"""Fill decision=verified on every mechanically clean question row.

    python fill_decisions.py <worksheets_dir> [--write]

Writes opt_<paper>_reviewed.csv next to each tagged worksheet, with
``decision`` set to ``verified`` on rows the sweep left unflagged, and blank on
rows it flagged. Blank means the existing tool skips them and they stay pending.

Then apply each with the real tool, which PATCHes
``/items/pyq_question/{id}/review``:

    python scripts\\pyq_question_review.py apply ^
      --exam-id 5466e62f-7382-4a38-ba96-2fe5fbfeaba2 ^
      --topic-catalog workbench\\catalogs\\opt_<paper>_topics.json ^
      --worksheet workbench\\worksheets\\opt_<paper>_reviewed.csv ^
      --apply --confirm

The tags are already applied, so those rows come back 409 and are counted as
failures by that tool - harmless, and the reason the counts will look noisy.

WHAT ``verified`` MEANS HERE, and it is narrower than the word suggests:
the text has no duplicate, no empty or truncated stem, no unexplained
non-ASCII, and a structure consistent with its paper; it carries a primary
topic tag; and its paper is anchored on a registered source document. It has
NOT been diffed against an official UPSC paper - those are unpublished before
2016 and this corpus is compiler-sourced. Sociology 2014 Paper-II is the
standing proof that a compiler can be wrong in ways no mechanical check sees.
"""
import csv, io, glob, os, sys

WS = sys.argv[1] if len(sys.argv) > 1 else "workbench/worksheets"
WRITE = "--write" in sys.argv
IGNORABLE = {"no_primary_tag", ""}

tot_v = tot_p = 0
for path in sorted(glob.glob(os.path.join(WS, "opt_*_tagged.csv"))):
    rows = list(csv.DictReader(io.open(path, encoding="utf-8-sig")))
    v = p = 0
    for r in rows:
        if (r.get("row_type") or "") != "question":
            continue
        real = {f.strip() for f in (r.get("flags") or "").split(",")} - IGNORABLE
        if real:
            r["decision"] = ""          # stays pending, read it by hand
            p += 1
        else:
            r["decision"] = "verified"
            v += 1
    out = path.replace("_tagged.csv", "_reviewed.csv")
    if WRITE:
        with io.open(out, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
    print("%-34s verified=%-5d pending=%-4d %s"
          % (os.path.basename(path), v, p, os.path.basename(out) if WRITE else ""))
    tot_v += v; tot_p += p

print()
print("TOTAL verified=%d pending=%d" % (tot_v, tot_p))
if not WRITE:
    print()
    print("DRY RUN. Re-run with --write to produce the _reviewed.csv files.")
