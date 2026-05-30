"""CLI to run the extractor against a document with optional live write.

Default is dry-run; --confirm is the explicit opt-in for live writes.
Combining --confirm with --dry-run is rejected.

Usage:
    # Dry run (default) — inspect dry_run_rows in the extraction_runs row
    python -m scripts.run_extractor_live \\
        --document-id 83722a86-610b-471d-8b6b-4a8397aa1791 \\
        --pyq-paper-id <pyq_paper_uuid>

    # Live write
    python -m scripts.run_extractor_live \\
        --document-id 83722a86-610b-471d-8b6b-4a8397aa1791 \\
        --pyq-paper-id <pyq_paper_uuid> \\
        --confirm
"""
from __future__ import annotations

import argparse
import sys


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Run v1 extractor; write pending pyq_questions rows via CMS path.",
    )
    p.add_argument('--document-id', required=True, help='document_assets UUID')
    p.add_argument(
        '--pyq-paper-id', required=True,
        help='pyq_papers UUID; extracted questions are linked here',
    )
    p.add_argument(
        '--confirm', action='store_true',
        help='Actually write rows. Without this flag, dry-run mode is used.',
    )
    p.add_argument(
        '--dry-run', action='store_true', default=False,
        help='Explicitly request dry-run (default behavior; --confirm overrides)',
    )
    p.add_argument(
        '--fuzzy-threshold', type=float, default=0.85,
        help='Levenshtein dedup threshold (default 0.85)',
    )
    return p


def main() -> None:
    args = _build_parser().parse_args()

    if args.confirm and args.dry_run:
        sys.stderr.write(
            "ERROR: --confirm and --dry-run cannot both be set.\n"
            "Default mode is dry-run. Use --confirm alone for live writes.\n"
        )
        sys.exit(2)

    is_dry_run = not args.confirm

    # Deferred imports so the module is importable without DB/env.
    from app.db.supabase_client import get_supabase_admin
    from app.exam_intelligence.extraction.pipeline import (
        ExtractionRequiresClassificationError,
        ExtractionRequiresCleanInputError,
        ExtractionWrongDocumentKindError,
        ExtractionNotSupportedError,
        extract,
        fetch_pdf_from_storage,
    )
    from app.exam_intelligence.extraction.run import (
        RunMetrics,
        RunStatus,
        complete_run,
        fail_run,
        start_run,
    )
    from app.exam_intelligence.extraction.writer import write_extraction_result
    from app.exam_intelligence.extraction.pipeline import EXTRACTOR_VERSION

    sb = get_supabase_admin()

    # All four guards run inside extract() before any DB write.
    try:
        pdf_bytes = fetch_pdf_from_storage(args.document_id)
        result = extract(pdf_bytes=pdf_bytes, document_id=args.document_id)
    except (
        ExtractionRequiresClassificationError,
        ExtractionRequiresCleanInputError,
        ExtractionWrongDocumentKindError,
        ExtractionNotSupportedError,
    ) as exc:
        sys.stderr.write(f"ERROR (eligibility guard): {exc}\n")
        sys.exit(1)

    run_id = start_run(
        sb,
        document_id=args.document_id,
        extractor_version=result.extractor_version,
        dry_run=is_dry_run,
        triggered_by_user_id=None,
    )

    try:
        metrics = write_extraction_result(
            sb=sb,
            result=result,
            run_id=run_id,
            pyq_paper_id=args.pyq_paper_id,
            dry_run=is_dry_run,
            fuzzy_threshold=args.fuzzy_threshold,
        )
        complete_run(sb, run_id, metrics, RunStatus.COMPLETED)
    except Exception as exc:
        fail_run(sb, run_id, exc, RunMetrics())
        sys.stderr.write(f"ERROR (pipeline): {exc}\n")
        sys.exit(1)

    mode = "DRY-RUN" if is_dry_run else "LIVE"
    print(f"\nRun {run_id} complete.")
    print(f"  Mode:               {mode}")
    print(f"  Questions extracted:{metrics.questions_extracted:>4}")
    if is_dry_run:
        print(f"  Would-insert:       {len(metrics.dry_run_rows):>4}")
        print(f"\n  Inspect dry-run rows:")
        print(f"    SELECT metadata->'dry_run_rows'")
        print(f"    FROM extraction_runs WHERE id = '{run_id}';")
    else:
        print(f"  Inserted:           {metrics.rows_inserted:>4}")
        print(f"  Skipped (idem):     {metrics.rows_skipped_idempotent:>4}")
        print(f"  Linked (fuzzy):     {metrics.rows_linked_fuzzy:>4}")
        print(f"  Errors:             {metrics.error_count:>4}")
        if metrics.error_count:
            print(f"\n  Error log:")
            for e in metrics.error_log:
                print(f"    {e}")


if __name__ == '__main__':
    main()
