#!/usr/bin/env python3
"""Split UPSC CSE Mains optional PYQ "bucket" papers into one paper per
(subject, paper number).

WHY
---
The optional corpus was imported with one ``pyq_papers`` row per YEAR holding
~12 merged papers ("a bucket"). Each question carries
``metadata.optional_subject`` and ``metadata.optional_paper_number``, and
``question_number`` is block-encoded (100s, 200s, ... per subject). A learner
picking "Anthropology Paper I" has nothing to pick: the bucket is one row.

This splits each bucket into real papers and re-points its questions. It does
NOT renumber questions, does NOT touch the question rows in any other way, and
does NOT delete or re-review the bucket — the bucket is retired in place and
keeps the lineage (``metadata.split_into``).

SCOPE
-----
``pyq_papers`` where metadata.paper_kind = 'optional'
               AND metadata.paper_code LIKE 'UPSC-CSE-MAINS-OPT-%'
               AND metadata.corpus_half IS DISTINCT FROM 'thematic'
               AND metadata.retired IS NOT TRUE

The thematic half is excluded by design: it has no paper structure at all and
``question_number`` is NULL on purpose, so there is nothing to split.

SAFETY
------
Dry-run by default; ``--live`` applies. One transaction per bucket, so a bucket
that fails leaves nothing half-moved and the others still run. Idempotent: a
split paper is matched by ``metadata.paper_code``, so a re-run is a no-op.

A bucket is ABORTED (not partially applied) when:
  * any of its questions lacks optional_subject or optional_paper_number; or
  * any of its questions is linked to a stimulus (see STIMULUS below).

STIMULUS — the constraint that decides this script's shape
----------------------------------------------------------
Migration 223 installs ``trg_pyq_questions_revalidate_paper_move``, which fires
BEFORE UPDATE OF pyq_paper_id on pyq_questions and raises when the question has
any ``pyq_question_stimuli`` row whose stimulus sits on a different paper:

    'pyq_questions % move to paper % would break pyq_question_stimuli
     cross-paper integrity'

Re-pointing a question WITHOUT moving its stimuli is therefore not merely
untidy, it is refused by the database. Moving the stimuli too would mean
changing rows this task explicitly scopes out, and splitting a shared stimulus
across several new papers has no single right answer. So this script REFUSES
such a bucket and reports it, rather than patching around the trigger.

Usage:

    export DATABASE_URL=postgresql://...

    # what would change (default)
    python scripts/split_optional_buckets.py

    # apply
    python scripts/split_optional_buckets.py --live

    # one bucket only
    python scripts/split_optional_buckets.py --bucket-code UPSC-CSE-MAINS-OPT-2019
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import unicodedata
import uuid
from typing import Any, Iterable

BUCKET_CODE_PREFIX = "UPSC-CSE-MAINS-OPT-"
BUCKET_CODE_LIKE = f"{BUCKET_CODE_PREFIX}%"

# Bucket metadata keys copied onto every split paper. Provenance travels with
# the questions; a split paper that loses its extraction lineage is unauditable.
_CARRIED_METADATA_KEYS = (
    "extraction_source",
    "verified_against_official",
    "promotion_blocked_by",
)


class BucketAbort(Exception):
    """One bucket cannot be split. Raised before any write for that bucket."""


def uuid_str(value: Any) -> Any:
    """Render a ``uuid.UUID`` as its canonical string; pass everything else on.

    asyncpg decodes ``uuid`` columns to ``uuid.UUID`` objects, which
    ``json.dumps`` cannot serialise. Every id that ends up INSIDE a jsonb
    payload has to come through here first. Deliberately narrow: no
    ``default=str`` on the dumps call, because that would also silently
    stringify a date, a Decimal or a Record we did not mean to put in jsonb,
    and we would find out in production instead of in the type error.
    """
    return str(value) if isinstance(value, uuid.UUID) else value


# ── pure planning (no IO, so it is testable without a database) ──────────────

def subject_slug(subject: str) -> str:
    """'Political Science & IR' -> 'POLITICAL-SCIENCE-IR'.

    Accent-folded, non-alphanumerics collapsed to single hyphens, upper-cased.
    Deterministic: the slug is part of the split paper_code, which is the
    idempotency key, so the same subject must always produce the same slug.
    """
    folded = unicodedata.normalize("NFKD", str(subject or ""))
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    slug = re.sub(r"[^A-Za-z0-9]+", "-", folded).strip("-").upper()
    return slug


def year_from_bucket_code(paper_code: str) -> int | None:
    m = re.search(r"(\d{4})\s*$", str(paper_code or ""))
    return int(m.group(1)) if m else None


def split_paper_code(bucket_code: str, subject: str, paper_number: Any) -> str:
    return f"{bucket_code}-{subject_slug(subject)}-P{paper_number}"


def plan_bucket(bucket: dict, questions: Iterable[dict]) -> list[dict]:
    """Group a bucket's questions into planned split papers.

    Raises ``BucketAbort`` if any question is missing its subject or paper
    number — a partial split would silently strand those questions on a retired
    bucket, which is worse than not splitting at all.
    """
    bucket_meta = bucket.get("metadata") if isinstance(bucket.get("metadata"), dict) else {}
    bucket_code = bucket_meta.get("paper_code") or bucket.get("paper_code")
    if not bucket_code:
        raise BucketAbort("bucket has no metadata.paper_code")
    year = year_from_bucket_code(bucket_code)

    groups: dict[tuple[str, Any], list[dict]] = {}
    missing: list[str] = []
    for q in questions:
        qmeta = q.get("metadata") if isinstance(q.get("metadata"), dict) else {}
        subject = qmeta.get("optional_subject")
        number = qmeta.get("optional_paper_number")
        if not subject or number in (None, ""):
            missing.append(str(q.get("id")))
            continue
        groups.setdefault((str(subject), number), []).append(q)

    if missing:
        raise BucketAbort(
            f"{len(missing)} question(s) lack optional_subject/optional_paper_number "
            f"(first: {', '.join(missing[:3])})"
        )
    if not groups:
        raise BucketAbort("bucket has no questions to split")

    planned = []
    for (subject, number), qs in sorted(groups.items(), key=lambda kv: (kv[0][0], str(kv[0][1]))):
        code = split_paper_code(bucket_code, subject, number)
        meta = {
            "paper_code": code,
            "paper_kind": "optional",
            "optional_subject": subject,
            "optional_paper_number": number,
            "year": year,
            # A jsonb value, so the UUID must be a string here, not at dumps time.
            "split_from_bucket_id": uuid_str(bucket.get("id")),
            "question_count": len(qs),
        }
        for key in _CARRIED_METADATA_KEYS:
            if key in bucket_meta:
                meta[key] = bucket_meta[key]
        planned.append(
            {
                "paper_code": code,
                "optional_subject": subject,
                "optional_paper_number": number,
                "year": year,
                "question_ids": [q["id"] for q in qs],
                "question_count": len(qs),
                "metadata": meta,
            }
        )
    return planned


# ── IO ──────────────────────────────────────────────────────────────────────

_BUCKET_SQL = """
select id, exam_id, exam_phase_id, exam_cycle_id, paper_code, year, metadata
  from public.pyq_papers
 where metadata->>'paper_kind' = 'optional'
   and coalesce(metadata->>'paper_code', paper_code) like $1
   and metadata->>'corpus_half' is distinct from 'thematic'
   and coalesce((metadata->>'retired')::boolean, false) is not true
 order by coalesce(metadata->>'paper_code', paper_code)
"""

_QUESTIONS_SQL = """
select id, metadata
  from public.pyq_questions
 where pyq_paper_id = $1
 order by question_number nulls last, id
"""

# Trigger 4c (migration 223) refuses a pyq_paper_id move for any question that
# has a stimulus on a different paper. Detect it here, before the transaction,
# so the bucket is reported rather than blowing up mid-apply.
_STIMULUS_LINK_SQL = """
select count(*)::bigint
  from public.pyq_question_stimuli qs
  join public.pyq_questions q on q.id = qs.question_id
 where q.pyq_paper_id = $1
"""

_EXISTING_SPLIT_SQL = """
select id, metadata->>'paper_code' as paper_code
  from public.pyq_papers
 where metadata->>'paper_code' = any($1::text[])
"""

_INSERT_SQL = """
insert into public.pyq_papers
    (exam_id, exam_phase_id, exam_cycle_id, year, paper_code, trust_status, metadata)
values ($1, $2, $3, $4, $5, 'pending', $6::jsonb)
returning id
"""

_REPOINT_SQL = """
update public.pyq_questions set pyq_paper_id = $1 where id = any($2::uuid[])
"""

_RETIRE_SQL = """
update public.pyq_papers
   set metadata = metadata || jsonb_build_object('retired', true, 'split_into', $2::jsonb),
       updated_at = now()
 where id = $1
"""


# ── live-path payload builders ──────────────────────────────────────────────
# Kept out of _split_one so the exact argument tuples that reach asyncpg can be
# asserted without a database. Both produce a jsonb payload, and jsonb is where
# a uuid.UUID blows up.

def insert_args(bucket: dict, plan: dict) -> tuple:
    """Positional arguments for ``_INSERT_SQL``.

    ``paper_code`` is set as a COLUMN, not only inside metadata:
    ``pyq_papers_unique_known_uidx`` covers
    (exam_id, exam_phase_id, year, paper_date, shift, paper_code) where
    exam_phase_id is not null. Every split row of one bucket shares
    exam/phase/year, so a NULL paper_code column would leave them
    distinguishable only by NULL-vs-NULL — which that index does not treat as a
    conflict today, but which would collide the moment paper_date or shift were
    ever backfilled.

    The uuid columns ($1-$3) stay as asyncpg handed them over: asyncpg encodes
    ``uuid.UUID`` for a uuid parameter natively. Only the jsonb payload needs
    strings.
    """
    return (
        bucket["exam_id"],
        bucket["exam_phase_id"],
        bucket["exam_cycle_id"],
        plan["year"],
        plan["paper_code"],
        json.dumps(plan["metadata"]),
    )


def retire_args(bucket: dict, planned: list[dict]) -> tuple:
    """Positional arguments for ``_RETIRE_SQL``.

    ``split_into`` is a jsonb array of the split papers' ids. Those ids come
    back from the INSERT's RETURNING (or from the existing-row lookup on a
    re-run) as ``uuid.UUID``, so each one is stringified here.
    """
    return (
        bucket["id"],
        json.dumps([uuid_str(p["paper_id"]) for p in planned]),
    )


async def _split_one(conn, bucket: dict, *, live: bool) -> dict:
    bucket_meta = bucket.get("metadata") or {}
    if isinstance(bucket_meta, str):
        bucket_meta = json.loads(bucket_meta)
    bucket = {**bucket, "metadata": bucket_meta}
    bucket_code = bucket_meta.get("paper_code") or bucket.get("paper_code")

    rows = await conn.fetch(_QUESTIONS_SQL, bucket["id"])
    questions = [
        {"id": r["id"], "metadata": json.loads(r["metadata"]) if isinstance(r["metadata"], str) else (r["metadata"] or {})}
        for r in rows
    ]

    linked = await conn.fetchval(_STIMULUS_LINK_SQL, bucket["id"])
    if linked:
        raise BucketAbort(
            f"{linked} question(s) carry pyq_question_stimuli links; moving them would "
            "trip trg_pyq_questions_revalidate_paper_move (migration 223). Moving the "
            "stimuli too is out of this script's scope — reported, not patched around."
        )

    planned = plan_bucket(bucket, questions)

    codes = [p["paper_code"] for p in planned]
    existing = {r["paper_code"]: r["id"] for r in await conn.fetch(_EXISTING_SPLIT_SQL, codes)}

    created, reused = [], []
    for plan in planned:
        if plan["paper_code"] in existing:
            plan["paper_id"] = existing[plan["paper_code"]]
            reused.append(plan)
            continue
        if not live:
            plan["paper_id"] = None
            created.append(plan)
            continue
        new_id = await conn.fetchval(_INSERT_SQL, *insert_args(bucket, plan))
        plan["paper_id"] = new_id
        created.append(plan)

    moved = 0
    if live:
        for plan in planned:
            if plan["question_ids"] and plan["paper_id"]:
                await conn.execute(_REPOINT_SQL, plan["paper_id"], plan["question_ids"])
                moved += len(plan["question_ids"])
        await conn.execute(_RETIRE_SQL, *retire_args(bucket, planned))
    else:
        moved = sum(len(p["question_ids"]) for p in planned)

    return {
        "bucket_code": bucket_code,
        "bucket_id": bucket["id"],
        "planned": planned,
        "created": len(created),
        "reused": len(reused),
        "moved": moved,
        "noop": not created,
    }


async def run(*, live: bool, bucket_code: str | None) -> int:
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
    total_moved = total_created = aborted = 0
    try:
        buckets = [dict(r) for r in await conn.fetch(_BUCKET_SQL, BUCKET_CODE_LIKE)]
        if bucket_code:
            buckets = [
                b for b in buckets
                if ((b.get("metadata") or {}) if isinstance(b.get("metadata"), dict)
                    else json.loads(b.get("metadata") or "{}")).get("paper_code") == bucket_code
            ]
        if not buckets:
            print("No buckets in scope.")
            return 0

        print(f"{'DRY RUN — no writes' if not live else 'LIVE — applying'}: {len(buckets)} bucket(s)\n")
        for bucket in buckets:
            try:
                # One transaction per bucket: a failure rolls back only its own
                # bucket and the rest still run.
                if live:
                    async with conn.transaction():
                        out = await _split_one(conn, bucket, live=True)
                else:
                    out = await _split_one(conn, bucket, live=False)
            except BucketAbort as exc:
                aborted += 1
                print(f"  ABORT {bucket.get('paper_code') or bucket['id']}: {exc}\n")
                continue

            status = "no-op (already split)" if out["noop"] else f"{out['created']} new paper(s)"
            print(f"  {out['bucket_code']} — {status}, {out['reused']} reused")
            for plan in out["planned"]:
                print(f"      {plan['paper_code']:<58} {plan['question_count']:>4} questions")
            print(f"      questions moved: {out['moved']}\n")
            total_moved += out["moved"]
            total_created += out["created"]

        print(f"TOTAL: {total_created} paper(s) created, {total_moved} question(s) moved, {aborted} bucket(s) aborted")
        if not live:
            print("(dry run — re-run with --live to apply)")
        return 1 if aborted else 0
    finally:
        await conn.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--live", action="store_true", help="apply changes (default: dry run)")
    ap.add_argument("--bucket-code", default=None, help="restrict to one bucket paper_code")
    args = ap.parse_args(argv)
    return asyncio.run(run(live=args.live, bucket_code=args.bucket_code))


if __name__ == "__main__":
    sys.exit(main())
