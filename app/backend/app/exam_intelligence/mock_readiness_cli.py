"""CLI for the mock content-readiness diagnostic (read-only).

Run against the live DB via the same env the other diagnostics use
(NEXT_PUBLIC_SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY). No credentials are
embedded here. Example:

    # 1. Discover the actual status vocabulary first (census only):
    python -m app.exam_intelligence.mock_readiness_cli --exam-slug upsc-cse

    # 2. Re-run with the discovered statuses + thresholds for the full report.
    #    Verdicts are grouped PER PHASE (mocks are phase-level); omit the phase
    #    flags to get every phase, or scope to one phase:
    python -m app.exam_intelligence.mock_readiness_cli \
        --exam-slug upsc-cse \
        --phase-slug prelims \
        --selectable-status verified --selectable-status published \
        --verified-status verified \
        --min-per-section 30 --min-locked-coverage 1

This is a thin wrapper: all logic lives in
``app.exam_intelligence.diagnostics``. It performs no writes.
"""
from __future__ import annotations

import argparse
import json
import sys

from app.db.supabase_client import get_supabase_admin
from app.exam_intelligence.diagnostics import assemble_mock_readiness_report


def _resolve_exam_id(sb, *, exam_id: str | None, exam_slug: str | None) -> str:
    """Resolve an exam slug to its id, or pass the id through."""
    if exam_id:
        return exam_id
    rows = (
        sb.table("exams")
        .select("id, slug")
        .eq("slug", exam_slug)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        raise SystemExit(f"No exam found for slug '{exam_slug}'")
    return rows[0]["id"]


def _resolve_phase_id(
    sb, *, exam_id: str, exam_phase_id: str | None, phase_slug: str | None
) -> str | None:
    """Resolve a phase slug (within the exam) to its id, or pass the id through.

    Returns None when neither is given — the report then groups by every phase.
    """
    if exam_phase_id:
        return exam_phase_id
    if not phase_slug:
        return None
    rows = (
        sb.table("exam_phases")
        .select("id, exam_id, phase_slug")
        .eq("exam_id", exam_id)
        .eq("phase_slug", phase_slug)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        raise SystemExit(
            f"No phase found for slug '{phase_slug}' on exam {exam_id}"
        )
    return rows[0]["id"]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mock_readiness_cli",
        description="Read-only mock content-readiness diagnostic for one exam.",
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--exam-slug", help="exams.slug to diagnose")
    target.add_argument("--exam-id", help="exams.id (uuid) to diagnose")
    phase = parser.add_mutually_exclusive_group(required=False)
    phase.add_argument(
        "--exam-phase-id",
        dest="exam_phase_id",
        help="optional exam_phases.id (uuid) to scope to one phase. "
        "When omitted, the report groups verdicts by every phase.",
    )
    phase.add_argument(
        "--phase-slug",
        dest="phase_slug",
        help="optional exam_phases.phase_slug (within the exam) to scope to "
        "one phase. When omitted, the report groups verdicts by every phase.",
    )
    parser.add_argument(
        "--selectable-status",
        action="append",
        dest="selectable_statuses",
        metavar="STATUS",
        help="reviewer_status value(s) that count as selectable (repeatable). "
        "Discover the real vocabulary from the census block first.",
    )
    parser.add_argument(
        "--verified-status",
        dest="verified_status",
        metavar="STATUS",
        help="verified-equivalent status for pyq trust/review gates.",
    )
    parser.add_argument(
        "--min-per-section",
        type=int,
        default=None,
        help="threshold: minimum selectable base-pool questions per section.",
    )
    parser.add_argument(
        "--min-locked-coverage",
        type=int,
        default=None,
        help="threshold: minimum locked coverage rows per section.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    sb = get_supabase_admin()
    exam_id = _resolve_exam_id(
        sb, exam_id=args.exam_id, exam_slug=args.exam_slug
    )
    exam_phase_id = _resolve_phase_id(
        sb,
        exam_id=exam_id,
        exam_phase_id=args.exam_phase_id,
        phase_slug=args.phase_slug,
    )
    report = assemble_mock_readiness_report(
        sb,
        exam_id=exam_id,
        exam_phase_id=exam_phase_id,
        selectable_statuses=args.selectable_statuses,
        verified_status=args.verified_status,
        min_per_section=args.min_per_section,
        min_locked_coverage=args.min_locked_coverage,
    )
    json.dump(report, sys.stdout, indent=2, default=str)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
