#!/usr/bin/env python3
r"""Stamp syllabus order onto `topics.metadata.sort_order`.

ORDER SOURCE: FOUND. The `upsc_gs_micro_theme_map` source is the thirteen
files under `docs/reference/syllabus/` — twelve optional papers plus the GS
map. Their `syllabus_nodes` array is in official syllabus order, and each
node's `micro_themes` array is in order within it. `scripts/build_syllabus_index.py`
already compiles exactly that into `syllabus_index.json`.

So nothing here invents an order. This script writes the order that is already
in the repository onto the rows, for readers that query `topics` directly and
cannot consult the index.

WHY THE CATALOGUE DOES NOT NEED THIS. `study_os/descriptive.py` orders themes
from the compiled index, so answer writing is already in syllabus order without
a single database write. This backfill is for everything else — and running it
is optional.

MATCHING IS BY NAME, WITHIN A PAPER. A topic's `slug` is
`slugify(f"{paper_id}:{macro}")` with a hash suffix, so it is reproducible but
only from the same source string; the name is what both sides actually hold. A
name that matches no node, or matches more than one, is REPORTED AND SKIPPED —
never given a guessed position.

    export DATABASE_URL=postgresql://...
    python scripts/backfill_topic_sort_order.py           # dry run (default)
    python scripts/backfill_topic_sort_order.py --live    # apply
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "app" / "backend" / "app" / "study_os" / "syllabus_index.json"

#: Subject slug -> paper id, mirroring `study_os/syllabus.py`. The empty GS
#: shells (`upsc-mains-gs1`, `upsc-gs-paper-1`) are deliberately absent.
def _paper_of(slug: str) -> str | None:
    import re

    text = (slug or "").strip().lower()
    m = re.fullmatch(r"upsc-cse-mains-gs([1-4])", text)
    if m:
        return f"GS_{m.group(1)}"
    m = re.fullmatch(r"upsc-cse-mains-(opt-[a-z0-9-]+-p[12])", text)
    return m.group(1) if m else None


_TOPICS_SQL = """
select t.id::text        as id,
       t.name            as name,
       t.level           as level,
       t.parent_topic_id::text as parent_id,
       s.slug            as subject_slug,
       coalesce(t.metadata->>'sort_order', '') as current_sort
  from public.topics t
  join public.subjects s on s.id = t.subject_id
 where s.slug like 'upsc-cse-mains-%'
 order by t.id
"""

_UPDATE_SQL = """
update public.topics
   set metadata = metadata || jsonb_build_object('sort_order', $2::int),
       updated_at = now()
 where id = $1::uuid
"""


def _plan(index: dict, rows: list[dict]) -> tuple[list[tuple[str, int]], list[str]]:
    """(id, sort_order) pairs to write, and the rows that could not be placed."""
    sections: dict[tuple[str, str], int] = {}
    for paper in index.get("papers", []):
        for section in paper.get("sections", []):
            sections[(paper["paper_id"], section["section"])] = section["order"]

    themes: dict[tuple[str, str], list[int]] = {}
    for name, hits in index.get("themes", {}).items():
        for hit in hits:
            themes.setdefault((hit["paper_id"], name), []).append(hit["order"])

    writes: list[tuple[str, int]] = []
    skipped: list[str] = []
    for row in rows:
        paper = _paper_of(row["subject_slug"])
        if not paper:
            skipped.append(f"{row['name'][:60]} — subject {row['subject_slug']} is not a paper")
            continue
        if row["level"] == "topic":
            order = sections.get((paper, row["name"]))
        else:
            hits = themes.get((paper, row["name"]) , [])
            # More than one position for the same name in the same paper is an
            # ambiguity, not a tie to break.
            order = hits[0] if len(hits) == 1 else None
        if order is None:
            skipped.append(f"{row['name'][:60]} — no unique {row['level']} in {paper}")
            continue
        if row["current_sort"] == str(order):
            continue  # already correct; idempotent
        writes.append((row["id"], order))
    return writes, skipped


async def run(*, live: bool) -> int:
    try:
        import asyncpg
    except ImportError:
        print("asyncpg is required (it is in app/backend/requirements.txt)", file=sys.stderr)
        return 2
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL is not set", file=sys.stderr)
        return 2
    if not INDEX.exists():
        print(f"{INDEX} is missing — run scripts/build_syllabus_index.py --write", file=sys.stderr)
        return 2

    index = json.loads(INDEX.read_text(encoding="utf-8"))
    conn = await asyncpg.connect(dsn)
    try:
        rows = [dict(r) for r in await conn.fetch(_TOPICS_SQL)]
        writes, skipped = _plan(index, rows)

        print(f"{'DRY RUN — no writes' if not live else 'LIVE — applying'}")
        print(f"  topics read      : {len(rows)}")
        print(f"  sort_order to set: {len(writes)}")
        print(f"  skipped          : {len(skipped)}")
        for line in skipped[:25]:
            print(f"      {line}")
        if len(skipped) > 25:
            print(f"      … and {len(skipped) - 25} more")

        if live and writes:
            async with conn.transaction():
                for topic_id, order in writes:
                    await conn.execute(_UPDATE_SQL, topic_id, order)
            print(f"  wrote {len(writes)} row(s)")
        elif not live:
            print("(dry run — re-run with --live to apply)")
    finally:
        await conn.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--live", action="store_true", help="apply (default: dry run)")
    args = ap.parse_args(argv)
    return asyncio.run(run(live=args.live))


if __name__ == "__main__":
    sys.exit(main())
