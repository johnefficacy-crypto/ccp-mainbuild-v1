#!/usr/bin/env python3
r"""Stamp `assignment_method` on GS questions that were already moved.

WHAT WENT WRONG. `scripts/split_gs_buckets.py` moved 957 questions onto 55
split papers and stamped each one with `metadata.gs_paper` — which paper it is
on — and nothing about HOW that was decided. `assignment_method` was written
only onto the PAPER's metadata, where it is a set over the whole paper and
cannot answer "why is this question here". The 27 operator overrides in
`gs_split_overrides.csv` were applied correctly and then became invisible:
`assignment_method='override'` on demo counted zero.

This recomputes the method for rows that have already moved and writes ONLY
that stamp. It never moves a question, never touches `pyq_paper_id`, and never
creates or retires a paper — the split already happened and was verified
correct; this is the label that should have gone on with it.

SCOPED TO THE GS SPLIT'S OWN PAPERS (`UPSC-CSE-MAINS-GS-%`). The optional split
stamps the same `split_from_bucket_id` on the same exam and phase, so without
the paper-code filter this also scanned 4,040 optional questions and reported
every one of them as having no tag — they have optional-subject tags, which is
a different taxonomy and none of this script's business.

THE METHOD IS RECOMPUTED FROM THE SAME INPUTS THE SPLIT USED, in the same
order of precedence:

    override    the question is in the override sheet
    essay_tag   no GS primary tag, but a row in `essay_pyq_tags`
    tag_only    a GS primary tag, in a year whose verification signal agreed
                with the tags on less than half its questions
    tag         a GS primary tag, in a year that was actually verified

2013 and 2014 are tag_only by that rule — they agreed on 1 of 93 and 5 of 78 —
and this script will stamp them so, which is a correction to what the split
recorded at the time rather than a new opinion.

    export DATABASE_URL=postgresql://...
    python scripts/backfill_gs_assignment_method.py                  # dry run
    python scripts/backfill_gs_assignment_method.py --live           # apply
    python scripts/backfill_gs_assignment_method.py \
        --overrides /path/to/gs_split_overrides.csv                  # operator copy
"""
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# The split script is the source of truth for every rule here, so it is
# imported rather than restated. A second copy of "what makes a question an
# Essay question" is how the two would come to disagree.
_SPEC = importlib.util.spec_from_file_location(
    "split_gs_buckets", ROOT / "scripts" / "split_gs_buckets.py"
)
sgb = importlib.util.module_from_spec(_SPEC)
sys.modules["split_gs_buckets"] = sgb
_SPEC.loader.exec_module(sgb)


#: The GS split's own paper codes: `UPSC-CSE-MAINS-GS-<year>-GS<n>` and
#: `-ESSAY`. The optional split writes `UPSC-CSE-MAINS-OPT-...`, so this prefix
#: is what separates the two — and a test pins it against
#: `split_gs_buckets.paper_code_for`, which is where the codes are minted.
GS_PAPER_CODE_PREFIX = "UPSC-CSE-MAINS-GS-"

#: Every question sitting on a paper the GS split produced.
#:
#: `split_from_bucket_id` ALONE IS NOT THE GS MARK. `split_optional_buckets.py`
#: stamps the same key, and both splits share this exam and phase, so the
#: filter reached all 4,040 optional questions as well. They carry
#: `optional_subject` tags rather than GS topic tags, so every one of them came
#: back as "no tag, no essay tag and no override" — 4,040 rows reported as
#: unexplained, which is a statement about the wrong corpus.
_MOVED_SQL = """
select q.id, q.pyq_paper_id, q.question_number, q.metadata,
       p.year, p.metadata as paper_metadata
  from public.pyq_questions q
  join public.pyq_papers p on p.id = q.pyq_paper_id
 where p.exam_id = $1::uuid
   and p.exam_phase_id = $2::uuid
   and p.metadata->>'split_from_bucket_id' is not null
   and p.paper_code like $3
 order by p.year, q.question_number, q.id
"""

_TAGS_SQL = """
select tag.question_id::text as question_id, s.slug as subject_slug
  from public.pyq_question_topic_tags tag
  join public.topics   t on t.id = tag.topic_id
  join public.subjects s on s.id = t.subject_id
 where tag.question_id = any($1::uuid[])
   and tag.tag_role = 'primary'
"""

_ESSAY_TAGS_SQL = """
select distinct question_id::text as question_id
  from public.essay_pyq_tags
 where question_id = any($1::uuid[])
"""

#: Only the stamp. `pyq_paper_id` is deliberately absent from this statement.
_STAMP_SQL = """
update public.pyq_questions
   set metadata = coalesce(metadata, '{}'::jsonb)
                  || jsonb_build_object('assignment_method', $2::text)
 where id = $1::uuid
"""


def method_for(
    question_id: str,
    *,
    tag_paper: Any,
    has_essay_tag: bool,
    overridden: bool,
    tag_only_year: bool,
) -> str | None:
    """How this question's paper was decided, or None when nothing explains it.

    None is a real answer and is reported rather than guessed at: a moved
    question that carries no tag, no essay tag and no override was placed by
    something this script cannot see, and inventing a label for it would be
    worse than leaving the gap visible.
    """
    if overridden:
        return "override"
    if tag_paper is not None:
        return "tag_only" if tag_only_year else "tag"
    if has_essay_tag:
        return "essay_tag"
    return None


def plan_stamps(
    rows: list[dict[str, Any]],
    *,
    tags: dict[str, Any],
    essay_tagged: set[str],
    overrides: dict[str, Any],
    tag_only_years: frozenset[int],
) -> tuple[list[tuple[str, str]], list[dict[str, Any]]]:
    """(writes, unexplained) — the stamp each moved row should carry.

    A row already carrying the right method is not rewritten: the run is
    idempotent, and a no-op UPDATE still bumps nothing but still costs a round
    trip and an audit line.
    """
    writes: list[tuple[str, str]] = []
    unexplained: list[dict[str, Any]] = []
    for row in rows:
        qid = str(row.get("id"))
        year = sgb._as_int(row.get("year"))
        method = method_for(
            qid,
            tag_paper=tags.get(qid),
            has_essay_tag=qid in essay_tagged,
            overridden=qid in overrides,
            tag_only_year=year in tag_only_years,
        )
        if method is None:
            unexplained.append(row)
            continue
        current = sgb.as_metadata(row.get("metadata")).get("assignment_method")
        if current != method:
            writes.append((qid, method))
    return writes, unexplained


def summarise(rows: list[dict[str, Any]], writes: list[tuple[str, str]]) -> str:
    by_method: dict[str, int] = {}
    for _, method in writes:
        by_method[method] = by_method.get(method, 0) + 1
    parts = ", ".join(f"{m} {n}" for m, n in sorted(by_method.items()))
    return f"  {len(writes)} of {len(rows)} moved question(s) to stamp: {parts or 'none'}"


async def run(*, live: bool, overrides_path: Path, tag_only_years: frozenset[int]) -> int:
    try:
        import asyncpg
    except ImportError:
        print("asyncpg is required (it is in app/backend/requirements.txt)", file=sys.stderr)
        return 2
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL is not set", file=sys.stderr)
        return 2

    try:
        overrides = sgb.load_overrides(overrides_path)
    except sgb.ScopeAbort as exc:
        print(f"OVERRIDE SHEET — {exc}", file=sys.stderr)
        return 2
    if not overrides_path.is_file():
        # The sheet is the operator's, not the repo's. Saying so is the
        # difference between "0 overrides because there were none" and "0
        # overrides because I was pointed at the wrong file".
        print(f"NOTE: {overrides_path} does not exist, so no question will be "
              "stamped 'override'. Pass --overrides if your copy is elsewhere.\n",
              file=sys.stderr)
    else:
        print(f"{len(overrides)} override(s) from {overrides_path}\n")

    conn = await asyncpg.connect(dsn)
    try:
        rows = [
            dict(r) for r in await conn.fetch(
                _MOVED_SQL, sgb.EXAM_ID, sgb.EXAM_PHASE_ID,
                f"{GS_PAPER_CODE_PREFIX}%",
            )
        ]
        if not rows:
            print("No split GS questions found — nothing to stamp.")
            return 0
        ids = [r["id"] for r in rows]

        tags = sgb._tag_papers(
            [dict(r) for r in await conn.fetch(_TAGS_SQL, ids)]
        )
        essay_tagged = {
            str(r["question_id"]) for r in await conn.fetch(_ESSAY_TAGS_SQL, ids)
        }

        writes, unexplained = plan_stamps(
            rows, tags=tags, essay_tagged=essay_tagged,
            overrides=overrides, tag_only_years=tag_only_years,
        )

        print(f"{'DRY RUN — no writes' if not live else 'LIVE — applying'}")
        print(summarise(rows, writes))
        years = sorted({sgb._as_int(r.get("year")) for r in rows} - {None})
        print(f"  years: {', '.join(str(y) for y in years)}")
        if tag_only_years:
            print(f"  tag-only years: "
                  f"{', '.join(str(y) for y in sorted(tag_only_years))}")
        if unexplained:
            print(f"\n  {len(unexplained)} moved question(s) have no tag, no essay "
                  "tag and no override — left unstamped rather than guessed:",
                  file=sys.stderr)
            for row in unexplained[:20]:
                print(f"      {row['year']} q{row.get('question_number')} {row['id']}",
                      file=sys.stderr)
            if len(unexplained) > 20:
                print(f"      … and {len(unexplained) - 20} more", file=sys.stderr)

        if live and writes:
            async with conn.transaction():
                for qid, method in writes:
                    await conn.execute(_STAMP_SQL, qid, method)
            print(f"\n  stamped {len(writes)} question(s)")
        elif not live:
            print("\n(dry run — re-run with --live to apply)")
        return 1 if unexplained else 0
    finally:
        await conn.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--live", action="store_true", help="apply (default: dry run)")
    ap.add_argument(
        "--overrides", type=Path, default=sgb.OVERRIDES_CSV,
        help="the operator's override sheet (default: workbench/audit/gs_split_overrides.csv)",
    )
    ap.add_argument(
        "--tag-only-years", type=int, nargs="*", default=[2013, 2014],
        help="years whose verification signal agreed on less than half, so "
             "their tag-placed questions are stamped 'tag_only'. Defaults to "
             "2013 and 2014, which agreed on 1/93 and 5/78.",
    )
    args = ap.parse_args(argv)
    return asyncio.run(run(live=args.live, overrides_path=args.overrides,
                           tag_only_years=frozenset(args.tag_only_years)))


if __name__ == "__main__":
    sys.exit(main())
