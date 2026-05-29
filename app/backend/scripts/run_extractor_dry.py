"""CLI: extract questions from a stored PDF and dump candidates JSON.

Reads from Supabase Storage (read-only) and writes to a local output file.
No database writes occur.

Usage:
    python -m scripts.run_extractor_dry \\
        --document-id 83722a86-610b-471d-8b6b-4a8397aa1791 \\
        --output /tmp/extracted_2026.json

    python -m scripts.run_extractor_dry \\
        --document-id afc8e285-0ea1-41a1-a524-83b8b3121154 \\
        --output /tmp/extracted_2025.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time


def _result_to_dict(result) -> dict:
    """Serialize ExtractionResult to a dict shaped like the fixture format."""
    questions = []
    for q in result.questions:
        questions.append({
            "question_number": q.question_number,
            "question_text": q.question_text,
            "regions": [
                {"page": r.page, "bbox": list(r.bbox)}
                for r in q.regions
            ],
            "confidence_by_field": q.confidence_by_field,
        })

    return {
        "document_id": result.document_id,
        "extractor_version": result.extractor_version,
        "pages_processed": result.pages_processed,
        "pages_skipped": result.pages_skipped,
        "errors": result.errors,
        "expected_questions": questions,
        "_stats": {
            "total_questions": len(result.questions),
            "total_pages_processed": len(result.pages_processed),
            "total_pages_skipped": len(result.pages_skipped),
            "total_errors": len(result.errors),
            "question_numbers": sorted(q.question_number for q in result.questions),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract questions from a stored PDF (dry run — no DB writes)."
    )
    parser.add_argument(
        "--document-id",
        required=True,
        help="document_assets.id UUID of the PDF to extract from",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to write the candidates JSON file",
    )
    parser.add_argument(
        "--pages",
        nargs="+",
        type=int,
        default=None,
        help="Specific 1-indexed page numbers to process (default: odd pages only)",
    )
    args = parser.parse_args()

    from app.exam_intelligence.extraction.pipeline import extract, fetch_pdf_from_storage

    print(f"Fetching PDF for document_id={args.document_id} …", flush=True)
    t0 = time.time()
    pdf_bytes = fetch_pdf_from_storage(args.document_id)
    print(f"  Fetched {len(pdf_bytes):,} bytes in {time.time() - t0:.1f}s", flush=True)

    print("Running extractor …", flush=True)
    t1 = time.time()
    result = extract(pdf_bytes, document_id=args.document_id, pages=args.pages)
    elapsed = time.time() - t1
    print(f"  Done in {elapsed:.1f}s", flush=True)

    stats = result
    print(
        f"\nSummary:\n"
        f"  Questions extracted : {len(result.questions)}\n"
        f"  Pages processed     : {len(result.pages_processed)} {result.pages_processed[:5]}{'…' if len(result.pages_processed) > 5 else ''}\n"
        f"  Pages skipped       : {len(result.pages_skipped)}\n"
        f"  Non-fatal errors    : {len(result.errors)}\n"
        f"  Q# range            : {min((q.question_number for q in result.questions), default='n/a')}–"
        f"{max((q.question_number for q in result.questions), default='n/a')}",
        flush=True,
    )

    output = _result_to_dict(result)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nOutput written to {args.output}", flush=True)

    if result.errors:
        print("\nNon-fatal errors:", flush=True)
        for err in result.errors:
            print(f"  page {err.get('page', '?')}: {err.get('error', '')}", flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
