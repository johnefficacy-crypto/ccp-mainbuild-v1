#!/usr/bin/env python3
r"""How many themes the catalogue can place in the syllabus, and which it cannot.

READ-ONLY. This script never writes to the database. Its only output is stdout
and, with --proposals, one CSV for a human to review.

WHY IT EXISTS
-------------
`app/backend/app/study_os/syllabus.py` places a theme from
`topics.metadata.paper_id` + `topics.metadata.macro_topic`, which
`scripts/ingest_upsc_gs_syllabus.py` stamps on every microtopic it writes, and
falls back to an exact name match against the compiled syllabus index. Both
routes are deterministic. Neither can be measured from the repository: whether
a given theme carries that metadata is a fact about the database.

So this reports the coverage the catalogue will actually achieve, per subject
and per paper:

    placed    — the theme resolves to a paper AND a syllabus section
    unplaced  — it does not, and will appear under "Other"

and, with --proposals, writes every unplaced theme to
`workbench/audit/theme_syllabus_proposals.csv` with an EMPTY placement for a
human to fill. Nothing is auto-applied and nothing here guesses: a proposal row
is a question put to a person, not an answer.

Applying approved rows is deliberately NOT part of this script. The right fix
for an unplaced theme is almost always to re-run the ingest, which places it
from the official file; hand-mapping is the exception, and an exception should
be visible.

    export DATABASE_URL=postgresql://...
    python scripts/syllabus_theme_coverage.py
    python scripts/syllabus_theme_coverage.py --proposals
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import os
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app" / "backend"))

from app.study_os import syllabus  # noqa: E402

PROPOSALS = ROOT / "workbench" / "audit" / "theme_syllabus_proposals.csv"

#: Every verified primary theme on a thematic question, with the subject the
#: question claims. Mirrors what `descriptive.get_catalog` reads.
_SQL = """
select distinct
       q.metadata->>'optional_subject' as subject,
       t.id::text                      as topic_id,
       t.name                          as theme,
       t.metadata->>'paper_id'         as meta_paper_id,
       t.metadata->>'macro_topic'      as meta_macro_topic,
       count(*) over (partition by t.id) as question_count
  from public.pyq_questions q
  join public.pyq_papers   p on p.id = q.pyq_paper_id
  join public.pyq_question_topic_tags tag
       on tag.question_id = q.id
      and tag.tag_role = 'primary'
      and tag.reviewer_status = 'verified'
  join public.topics t on t.id = tag.topic_id
 where q.question_type = 'descriptive'
   and q.reviewer_status = 'verified'
   and coalesce(p.metadata->>'corpus_half', q.metadata->>'corpus_half') = 'thematic'
   and coalesce((p.metadata->>'retired')::boolean, false) is not true
"""


async def run(*, proposals: bool) -> int:
    try:
        import asyncpg
    except ImportError:
        print("asyncpg is required (it is in app/backend/requirements.txt)", file=sys.stderr)
        return 2
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL is not set", file=sys.stderr)
        return 2

    conn = await asyncpg.connect(dsn)
    try:
        rows = [dict(r) for r in await conn.fetch(_SQL)]
    finally:
        await conn.close()

    by_subject: dict[str, dict[str, int]] = defaultdict(lambda: {"placed": 0, "unplaced": 0})
    by_paper: dict[tuple[str, str], int] = defaultdict(int)
    unplaced: list[dict] = []

    for row in rows:
        subject = row.get("subject") or "(no subject)"
        spot = syllabus.place(
            {
                "name": row.get("theme"),
                "metadata": {
                    "paper_id": row.get("meta_paper_id"),
                    "macro_topic": row.get("meta_macro_topic"),
                },
            }
        )
        bucket = "placed" if spot["placed"] else "unplaced"
        by_subject[subject][bucket] += 1
        if spot["placed"]:
            by_paper[(subject, spot["paper_label"])] += 1
        else:
            unplaced.append({**row, "subject": subject})

    print(f"{'subject':<52} {'placed':>7} {'unplaced':>9} {'coverage':>9}")
    print("-" * 82)
    total_placed = total_unplaced = 0
    for subject in sorted(by_subject):
        counts = by_subject[subject]
        total = counts["placed"] + counts["unplaced"]
        pct = (100.0 * counts["placed"] / total) if total else 0.0
        total_placed += counts["placed"]
        total_unplaced += counts["unplaced"]
        print(f"{subject[:52]:<52} {counts['placed']:>7} {counts['unplaced']:>9} {pct:>8.1f}%")
        for (subj, paper), n in sorted(by_paper.items()):
            if subj == subject:
                print(f"    {paper:<48} {n:>7}")
    total = total_placed + total_unplaced
    pct = (100.0 * total_placed / total) if total else 0.0
    print("-" * 82)
    print(f"{'TOTAL':<52} {total_placed:>7} {total_unplaced:>9} {pct:>8.1f}%")

    if proposals:
        PROPOSALS.parent.mkdir(parents=True, exist_ok=True)
        with PROPOSALS.open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(
                fh,
                fieldnames=[
                    "subject", "topic_id", "theme", "question_count",
                    # Deliberately blank. A human fills these in; nothing here
                    # proposes a value it cannot derive.
                    "proposed_paper_id", "proposed_section", "reviewer", "notes",
                ],
            )
            writer.writeheader()
            for row in sorted(unplaced, key=lambda r: (r["subject"], r["theme"] or "")):
                writer.writerow(
                    {
                        "subject": row["subject"],
                        "topic_id": row["topic_id"],
                        "theme": row["theme"],
                        "question_count": row["question_count"],
                        "proposed_paper_id": "",
                        "proposed_section": "",
                        "reviewer": "",
                        "notes": "",
                    }
                )
        print(f"\nwrote {len(unplaced)} unplaced theme(s) to {PROPOSALS.relative_to(ROOT)}")
        print("Placements are blank by design — fill them in, or re-run the ingest.")

    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--proposals", action="store_true",
                    help="also write the unplaced themes to a review CSV")
    args = ap.parse_args(argv)
    return asyncio.run(run(proposals=args.proposals))


if __name__ == "__main__":
    sys.exit(main())
