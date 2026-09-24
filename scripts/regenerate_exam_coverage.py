#!/usr/bin/env python3
r"""Regenerate evidence-derived `exam_topic_coverage` for one exam. Dry run by default.

WHY THIS EXISTS. The generator that wrote the 3,988 `source_basis='evidence_derived'`
coverage rows is not a script — it is two admin routes, and nothing in the
repository could run them from a terminal or show an operator what they would do
before they did it:

    POST /admin/exam-intelligence/exams/{exam_id}/score-snapshots/compute
        -> app.exam_intelligence.score_snapshots.compute_exam_topic_scores
    POST /admin/exam-intelligence/exams/{exam_id}/coverage/derive
        -> app.exam_intelligence.coverage_derivation.derive_topic_coverage

This wraps that existing chain. It computes NOTHING itself: every number it
prints comes from those two modules, called with `dry_run=True`. A second copy
of the scoring formula is the one thing that must not exist here (PD-6, "single
source of evidence numbers"), so if you want to know how a score is derived,
read `--explain` output — it prints the components the snapshot module itself
recorded, not a re-derivation.

THE CHAIN HAS TWO HUMAN GATES AND THIS SCRIPT CROSSES NEITHER:

    1. compute   -> writes DRAFT exam_topic_score_snapshots
    2. [HUMAN]      PATCH /admin/exam-intelligence/score-snapshots/{id}/review
                    draft -> ... -> locked
    3. derive    -> reads LOCKED snapshots, writes DRAFT exam_topic_coverage
    4. [HUMAN]      PATCH /admin/exam-intelligence/topic-coverage/{id}/review
                    draft -> pending_review -> reviewed -> locked

`pyq_practice.py` serves topic mode from `mock_question_bank` filtered on
LOCKED coverage ids, so only step 4 makes a microtopic practisable. `--live`
does steps 1 and 3. Steps 2 and 4 stay with a reviewer, by design: `derive`
writes draft rows only (PD-3) and a script that locked its own output would be
an AI job writing into locked coverage, which the gate forbids outright.

WHAT `--assume-locked` IS FOR. Because step 2 sits in the middle, a freshly
computed draft is invisible to `derive` until a human locks it — so a plain dry
run of step 3 reports what would happen with the snapshots locked TODAY, which
for newly verified subjects is "nothing". `--assume-locked` feeds step 1's
proposed drafts into step 3's projection (dry-run only; `derive_topic_coverage`
refuses the override on a live run) and answers the question actually being
asked: once these drafts are locked, which topics gain coverage, at what depth,
with what priority.

EVIDENCE IS VERIFIED PYQ TAGS, NOT PROJECTED BANK ROWS. `evidence_count` — the
input to the depth bucket — is the number of verified `pyq_questions` in
verified `pyq_papers` carrying this topic as a verified PRIMARY tag. It is not
`mock_question_bank`. The projected bank is downstream of the same tags, so the
two usually move together, but they are not the same number: the bank excludes
expired (`valid_until`) and non-active rows. `--compare-bank` prints both per
topic so a divergence is visible rather than assumed away.

    export NEXT_PUBLIC_SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=...

    # what would change for RBI Grade B, nothing written
    python scripts/regenerate_exam_coverage.py --exam aded8ee9-e9ec-4287-9015-6db1919fa67e

    # the forward-looking answer: coverage after the new drafts are locked
    python scripts/regenerate_exam_coverage.py --exam <id> --assume-locked --explain

    # show verified-tag evidence beside the projected bank count
    python scripts/regenerate_exam_coverage.py --exam <id> --assume-locked --compare-bank

    # actually write: draft snapshots (step 1) and draft coverage (step 3)
    python scripts/regenerate_exam_coverage.py --exam <id> --live

    # machine-readable, for an evidence record
    python scripts/regenerate_exam_coverage.py --exam <id> --assume-locked --json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app" / "backend"))

#: RBI Grade B — the exam this script was written for. Passed explicitly in
#: every documented invocation; here only so `--exam rbi` is possible.
EXAM_ALIASES = {
    "rbi": "aded8ee9-e9ec-4287-9015-6db1919fa67e",
    "rbi-grade-b": "aded8ee9-e9ec-4287-9015-6db1919fa67e",
}

#: Depth buckets in ascending order of evidence, for the summary table. The
#: authority is `coverage_derivation.bucket_coverage_depth`, not this list.
DEPTH_ORDER = ("mentioned", "light", "normal", "deep", "core")


class CoverageRunError(Exception):
    """Operator-facing failure: bad arguments, missing credentials, read error."""


def _load_modules() -> tuple[Any, Any, Any]:
    """Import the two governed modules and the client factory.

    Imported lazily so `--help` works with no Supabase credentials set and so
    the import error, when it comes, names what is missing.
    """
    try:
        from app.db.supabase_client import get_supabase_admin
        from app.exam_intelligence import coverage_derivation, score_snapshots
    except Exception as exc:  # noqa: BLE001
        raise CoverageRunError(
            f"cannot import the exam-intelligence modules from {ROOT / 'app' / 'backend'}: {exc}"
        ) from exc
    return get_supabase_admin, score_snapshots, coverage_derivation


def resolve_exam(value: str) -> str:
    key = (value or "").strip().lower()
    if not key:
        raise CoverageRunError("--exam is required")
    return EXAM_ALIASES.get(key, value.strip())


def as_locked_shape(proposed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Re-shape step 1's proposed draft rows into `locked_score_snapshots`' output.

    `derive_topic_coverage` consumes the reader's shape (`snapshot_id`,
    `fingerprint`, ...), not the writer's payload shape (`input_summary`,
    `status`, ...). This maps one to the other and invents no value: every
    field is copied, and `snapshot_id` is None because these rows have no id
    yet — they have not been written, which is the entire point.
    """
    out: list[dict[str, Any]] = []
    for row in proposed:
        summary = row.get("input_summary") or {}
        out.append(
            {
                "snapshot_id": None,
                "topic_id": row.get("topic_id"),
                "exam_priority_score": row.get("exam_priority_score"),
                "is_high_yield": bool(row.get("is_high_yield")),
                "confidence_score": row.get("confidence_score"),
                "model_version": row.get("model_version"),
                "score_components": row.get("score_components") or {},
                "computed_at": None,
                "evidence_count": row.get("evidence_count"),
                "fingerprint": summary.get("fingerprint"),
                "predictability": row.get("predictability"),
                "predictability_band": row.get("predictability_band"),
            }
        )
    return out


def bank_counts_by_level(sb: Any, exam_id: str) -> dict[str, int] | None:
    """Projected `mock_question_bank` rows per coverage-lock id, or None on read failure.

    Counted at the SAME level `pyq_practice.py` practises at: a row with a
    `microtopic_id` belongs to that microtopic and to nothing else, otherwise
    it belongs to its `topic_id` (migration 270's two coexisting row shapes —
    see `pyq_practice._row_level_id`, whose rule this mirrors). Counting
    `topic_id` alone would credit a parent with its children's questions and
    make the comparison column lie in the direction that matters most.

    This is REPORTING ONLY. No score, bucket or lock decision reads it.
    """
    counts: dict[str, int] = {}
    page = 1000
    start = 0
    while True:
        try:
            resp = (
                sb.table("mock_question_bank")
                .select("topic_id, microtopic_id")
                .eq("exam_id", exam_id)
                .eq("reviewer_status", "verified")
                .order("id")
                .range(start, start + page - 1)
                .execute()
            )
        except Exception as exc:  # noqa: BLE001
            print(f"NOTE: could not read mock_question_bank ({exc}); "
                  f"--compare-bank column omitted", file=sys.stderr)
            return None
        rows = resp.data or []
        for r in rows:
            level_id = r.get("microtopic_id") or r.get("topic_id")
            if level_id:
                counts[str(level_id)] = counts.get(str(level_id), 0) + 1
        if len(rows) < page:
            break
        start += page
    return counts


def locked_coverage_topic_ids(sb: Any, exam_id: str) -> set[str] | None:
    """Topic ids already carrying a LOCKED coverage row — what practice can reach today."""
    ids: set[str] = set()
    page = 1000
    start = 0
    while True:
        try:
            resp = (
                sb.table("exam_topic_coverage")
                .select("topic_id")
                .eq("exam_id", exam_id)
                .eq("reviewer_status", "locked")
                .order("topic_id")
                .range(start, start + page - 1)
                .execute()
            )
        except Exception as exc:  # noqa: BLE001
            print(f"NOTE: could not read locked coverage ({exc})", file=sys.stderr)
            return None
        rows = resp.data or []
        for r in rows:
            if r.get("topic_id"):
                ids.add(str(r["topic_id"]))
        if len(rows) < page:
            break
        start += page
    return ids


def summarise(proposed: list[dict[str, Any]]) -> dict[str, int]:
    """Count proposed coverage rows per depth bucket."""
    out = {d: 0 for d in DEPTH_ORDER}
    for row in proposed:
        depth = row.get("coverage_depth")
        if depth in out:
            out[depth] += 1
        else:
            out[str(depth)] = out.get(str(depth), 0) + 1
    return out


def explain_row(row: dict[str, Any], snapshot: dict[str, Any] | None) -> list[str]:
    """How this row's depth and priority were arrived at, from recorded values only.

    Every term printed here was written by `score_snapshots.compute_exam_topic_scores`
    into `score_components`; the arithmetic is restated so an operator can check
    it adds up, not to compute it. When a component is missing the line says so
    rather than filling in a plausible number.
    """
    meta = (row.get("metadata") or {}).get("evidence") or {}
    ev = meta.get("evidence_count")
    mentions = meta.get("syllabus_mentions")
    lines = [
        f"  depth        {row.get('coverage_depth')}"
        f"   <- evidence_count={ev}, syllabus_mentions={mentions},"
        f" is_high_yield={bool(row.get('is_high_yield'))}",
        f"               bucket_coverage_depth(): 0+0 none | 0 mentioned | 1-2 light |"
        f" 3-5 normal | 6-9 deep | >=10 core if mentioned & high-yield else deep",
    ]
    comp = (snapshot or {}).get("score_components") or {}
    if not comp:
        lines.append(
            "  priority     "
            f"{row.get('exam_priority_score')}   <- copied verbatim from the snapshot"
            " (PD-6); score_components not available on this row"
        )
        return lines
    freq = comp.get("frequency_component")
    cov = comp.get("coverage_component")
    qual = comp.get("evidence_quality")
    weight = comp.get("cohort_weight")
    prom = comp.get("cohort_prominence")
    lift = comp.get("cohort_lift")
    lines += [
        f"  priority     {row.get('exam_priority_score')}"
        f"   <- frequency_term + coverage_component*40 + evidence_quality*10",
        f"               frequency_term = freq*50*(1-w) + prominence*50*w"
        f"  [freq={freq}, prominence={prom}, w={weight}]",
        f"               coverage_component={cov} (prior locked coverage score / 100),"
        f" evidence_quality={qual} (min(evidence/10, 1))",
        f"               cohort_lift={lift} (times its cohort's mean;"
        f" >=3 with w>0 sets is_high_yield)",
        f"  confidence   {row.get('confidence_score')}"
        f"   <- min(0.3 + evidence_quality*0.7, 1)",
    ]
    band = row.get("predictability_band")
    lines.append(
        f"  predictability {row.get('predictability')} ({band})"
        f"   <- separate axis, projected not recomputed"
        if band or row.get("predictability") is not None
        else "  predictability none   <- no year evidence behind this row"
    )
    return lines


def run(args: argparse.Namespace) -> int:
    get_supabase_admin, score_snapshots, coverage_derivation = _load_modules()
    exam_id = resolve_exam(args.exam)
    live = bool(args.live)
    dry = not live

    try:
        sb = get_supabase_admin()
    except Exception as exc:  # noqa: BLE001
        raise CoverageRunError(
            f"no Supabase admin client: {exc}\n"
            "set NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY"
        ) from exc

    mode = "LIVE" if live else "DRY RUN"
    print(f"=== regenerate_exam_coverage — {mode} ===")
    print(f"exam_id       {exam_id}")
    print(f"phase         {args.phase or '(exam-wide)'}")
    print(f"snapshot ver  {score_snapshots.MODEL_VERSION}")
    print(f"derivation    {coverage_derivation.DERIVATION_VERSION}")
    print()

    # ── step 1: score snapshots ───────────────────────────────────────────
    step1 = score_snapshots.compute_exam_topic_scores(
        sb, exam_id, exam_phase_id=args.phase, dry_run=dry
    )
    if step1.get("invalid_scope"):
        raise CoverageRunError(f"--phase {args.phase} does not belong to exam {exam_id}")
    if step1.get("read_error"):
        raise CoverageRunError(
            "a critical input read failed during score computation — nothing was written"
        )

    verb = "would write" if dry else "wrote"
    print("step 1 — exam_topic_score_snapshots (draft)")
    print(f"  topics scored   {step1['total_topics']}")
    print(f"  {verb:<15} {step1['written']}")
    print(f"  skipped (same fingerprint) {step1['skipped']}")
    print(f"  errors          {step1['errors']}")
    print()
    print("  [HUMAN GATE] each draft must be locked via")
    print("    PATCH /admin/exam-intelligence/score-snapshots/{id}/review")
    print()

    # ── step 2: coverage derivation ───────────────────────────────────────
    override = None
    if args.assume_locked:
        if live:
            raise CoverageRunError(
                "--assume-locked is a dry-run projection and cannot be combined with "
                "--live: deriving coverage from unlocked snapshots would violate PD-1"
            )
        override = as_locked_shape(step1.get("proposed") or [])

    step2 = coverage_derivation.derive_topic_coverage(
        sb, exam_id, exam_phase_id=args.phase, dry_run=dry, snapshots_override=override
    )
    if step2.get("invalid_scope"):
        raise CoverageRunError(f"--phase {args.phase} does not belong to exam {exam_id}")
    if step2.get("read_error"):
        raise CoverageRunError(
            "a critical input read failed during coverage derivation — nothing was written"
        )

    src = (
        f"step 1's {len(override)} proposed draft(s), AS IF locked"
        if override is not None
        else "snapshots locked in the database today"
    )
    print(f"step 3 — exam_topic_coverage (draft), from {src}")
    print(f"  topics in scope {step2['total_topics']}")
    print(f"  {verb:<15} {step2['written']}   (new draft rows)")
    print(f"  would update    {step2['updated']}   (derivation-owned rows recomputed)"
          if dry else f"  updated         {step2['updated']}")
    print(f"  skipped         {step2['skipped']}   (human-authored / reviewed / locked — never touched)")
    print(f"  triaged         {step2['triaged']}   (model_generated rows flagged)")
    print(f"  no row          {step2['no_row']}   (zero evidence and zero syllabus mentions)")
    print(f"  stale flagged   {step2['stale_reconciled']}")
    print(f"  errors          {step2['errors']}")

    proposed = step2.get("proposed") or []
    if proposed:
        buckets = summarise(proposed)
        print("  depth split     " + ", ".join(
            f"{d}={buckets.get(d, 0)}" for d in DEPTH_ORDER if buckets.get(d)))
    print()
    print("  [HUMAN GATE] each draft must be locked via")
    print("    PATCH /admin/exam-intelligence/topic-coverage/{id}/review")
    print("    Only locked rows are reachable by topic-mode practice.")
    print()

    # ── what this unblocks ────────────────────────────────────────────────
    locked_now = locked_coverage_topic_ids(sb, exam_id)
    bank = bank_counts_by_level(sb, exam_id) if args.compare_bank else None

    if locked_now is not None:
        proposed_ids = {str(r.get("topic_id")) for r in proposed if r.get("topic_id")}
        new_ids = proposed_ids - locked_now
        print(f"reach — locked coverage today {len(locked_now)} topic(s)")
        print(f"        proposed rows          {len(proposed_ids)} topic(s)")
        print(f"        NOT yet locked         {len(new_ids)} topic(s)"
              f"  <- what locking these drafts would newly make practisable")
        if bank is not None:
            unreachable = {t: n for t, n in bank.items() if t not in locked_now}
            print(f"        projected-but-unlocked {len(unreachable)} topic(s),"
                  f" {sum(unreachable.values())} bank row(s)")
            uncovered = {t: n for t, n in unreachable.items() if t not in proposed_ids}
            if uncovered:
                print(f"        STILL unreachable      {len(uncovered)} topic(s),"
                      f" {sum(uncovered.values())} bank row(s) — these have projected"
                      f" questions but this run proposes no coverage row for them")
        print()

    if args.explain:
        snap_by_topic = {
            str(s.get("topic_id")): s
            for s in (override if override is not None else [])
            if s.get("topic_id")
        }
        shown = proposed if args.explain_all else proposed[: args.explain_limit]
        print(f"--explain — {len(shown)} of {len(proposed)} proposed row(s)")
        for row in shown:
            tid = str(row.get("topic_id"))
            head = f"topic {tid}"
            if bank is not None:
                head += f"   [verified-tag evidence vs projected bank: " \
                        f"{((row.get('metadata') or {}).get('evidence') or {}).get('evidence_count')}" \
                        f" vs {bank.get(tid, 0)}]"
            print(head)
            for line in explain_row(row, snap_by_topic.get(tid)):
                print(line)
            print()

    if args.json:
        print(json.dumps(
            {
                "exam_id": exam_id,
                "exam_phase_id": args.phase,
                "mode": mode,
                "assume_locked": bool(args.assume_locked),
                "snapshot_model_version": score_snapshots.MODEL_VERSION,
                "derivation_version": coverage_derivation.DERIVATION_VERSION,
                "step1_snapshots": {k: v for k, v in step1.items() if k != "proposed"},
                "step3_coverage": {k: v for k, v in step2.items() if k != "proposed"},
                "depth_split": summarise(proposed),
                "proposed_coverage": proposed,
            },
            indent=2, default=str,
        ))

    if dry:
        print("DRY RUN — nothing was written. Re-run with --live to write the draft rows.")
    else:
        print("LIVE — draft rows written. Both review gates above are still open.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Regenerate evidence-derived exam_topic_coverage. Dry run by default.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--exam", required=True,
                   help="exam id, or an alias: " + ", ".join(sorted(EXAM_ALIASES)))
    p.add_argument("--phase", default=None,
                   help="exam_phase_id for a phase-scoped run; omit for exam-wide")
    p.add_argument("--live", action="store_true",
                   help="write the draft rows (steps 1 and 3). Default is a dry run.")
    p.add_argument("--assume-locked", action="store_true",
                   help="project coverage as if step 1's fresh drafts were already "
                        "locked. Dry run only.")
    p.add_argument("--compare-bank", action="store_true",
                   help="print the projected mock_question_bank count beside the "
                        "verified-tag evidence count. Reporting only.")
    p.add_argument("--explain", action="store_true",
                   help="print how each proposed row's depth and priority were derived")
    p.add_argument("--explain-limit", type=int, default=20,
                   help="rows to explain (default 20)")
    p.add_argument("--explain-all", action="store_true", help="explain every proposed row")
    p.add_argument("--json", action="store_true", help="also emit the full result as JSON")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run(args)
    except CoverageRunError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
