"""Extraction pipeline: PDF bytes → ExtractionResult.

This module is the public entry point. It:
1. Opens the PDF with PyMuPDF (fitz).
2. Determines which pages to process (corpus-specific or odd-pages-only default).
3. Rasterizes each page at 300 DPI to a PIL image.
4. Runs OCR (ocr.ocr_page) and segmentation (segmentation.segment_column).
5. Threads last_accepted_ordinal across all columns and pages for document-wide
   monotonicity, then deduplicates (drops both on conflict).
6. Assembles and returns an ExtractionResult.

No writes to any database table occur in this module.
"""
from __future__ import annotations

import logging

import fitz  # PyMuPDF
from PIL import Image

from .layout import assign_words_to_columns, detect_columns
from .ocr import DPI, ocr_page
from .segmentation import reconstruct_lines, segment_column
from .types import ExtractionResult, ExtractedQuestion, Word

logger = logging.getLogger(__name__)

EXTRACTOR_VERSION = "0.2.0"

# Hardcoded page ranges for known corpus document IDs (exact UUID match).
CORPUS_ALLOWED_PAGES: dict[str, list[int]] = {
    "83722a86-610b-471d-8b6b-4a8397aa1791": list(range(3, 52, 2)),  # 2026 GS-I
    "afc8e285-0ea1-41a1-a524-83b8b3121154": list(range(3, 44, 2)),  # 2025 GS-I
}


def allowed_pages_for(document_id: str, total_pages: int) -> list[int]:
    """Return the allowed page list for a known corpus ID.

    Falls back to odd pages 3..(total_pages-2) — drops cover and trailing blank.
    """
    if document_id in CORPUS_ALLOWED_PAGES:
        return CORPUS_ALLOWED_PAGES[document_id]
    return list(range(3, total_pages - 1, 2))


def _process_page_words(
    words: list[Word],
    page: int,
    last_accepted_ordinal: int,
) -> tuple[list[ExtractedQuestion], int]:
    """Segment one page's words into questions.

    Returns (questions, updated_last_accepted_ordinal).  The caller threads
    the updated ordinal across columns and pages to enforce document-wide
    monotonicity.
    """
    if not words:
        return [], last_accepted_ordinal

    columns = detect_columns(words)
    col_words = assign_words_to_columns(words, columns)

    questions: list[ExtractedQuestion] = []
    for col_idx in sorted(col_words.keys()):
        col = col_words[col_idx]
        if not col:
            continue
        col_start, _col_end = columns[col_idx]
        lines = reconstruct_lines(col)
        col_questions, last_accepted_ordinal = segment_column(
            lines, col_start, last_accepted_ordinal, page
        )
        questions.extend(col_questions)

    return questions, last_accepted_ordinal


def _dedup(questions: list[ExtractedQuestion]) -> list[ExtractedQuestion]:
    """Drop both entries when the same question_number appears more than once."""
    from collections import Counter
    counts = Counter(q.question_number for q in questions)
    return [q for q in questions if counts[q.question_number] == 1]


def extract_from_words(
    words: list[Word],
    page: int,
    document_id: str,
    last_accepted_ordinal: int = 0,
) -> ExtractionResult:
    """In-memory entry point for tests — skips PDF fetch and OCR.

    Processes a single page's pre-computed Word list through the column
    detection and segmentation pipeline.
    """
    page_questions, _ = _process_page_words(words, page, last_accepted_ordinal)
    return ExtractionResult(
        document_id=document_id,
        extractor_version=EXTRACTOR_VERSION,
        questions=page_questions,
        pages_processed=[page],
        pages_skipped=[],
        errors=[],
    )


def extract(
    pdf_bytes: bytes,
    document_id: str,
    pages: list[int] | None = None,
) -> ExtractionResult:
    """Extract questions from a scanned PDF.

    Args:
        pdf_bytes: Raw PDF content.
        document_id: Identifier recorded in the result (not written anywhere).
        pages: 1-indexed page numbers to process.  Defaults to corpus-specific
               allowed pages, falling back to odd pages 3+ only.

    Returns:
        ExtractionResult with extracted questions and diagnostics.
        No database writes occur.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total_pages = doc.page_count

    if pages is None:
        pages = allowed_pages_for(document_id, total_pages)

    all_pages = set(range(1, total_pages + 1))
    pages_skipped = sorted(all_pages - set(pages))

    questions: list[ExtractedQuestion] = []
    pages_processed: list[int] = []
    errors: list[dict] = []
    last_accepted_ordinal = 0  # threaded across all columns and pages

    for page_num in pages:
        if page_num < 1 or page_num > total_pages:
            errors.append({"page": page_num, "error": "page number out of range"})
            continue
        try:
            fitz_page = doc[page_num - 1]  # fitz is 0-indexed
            mat = fitz.Matrix(DPI / 72.0, DPI / 72.0)
            pix = fitz_page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            words = ocr_page(img, page_num)
            page_questions, last_accepted_ordinal = _process_page_words(
                words, page_num, last_accepted_ordinal
            )
            questions.extend(page_questions)
            pages_processed.append(page_num)
            logger.debug(
                "page %d: %d words → %d questions",
                page_num, len(words), len(page_questions),
            )
        except Exception as exc:
            logger.warning("non-fatal error on page %d: %s", page_num, exc)
            errors.append({"page": page_num, "error": str(exc)})

    doc.close()

    # Duplicate detection: drop BOTH occurrences and record in errors.
    seen: dict[int, ExtractedQuestion] = {}
    final_questions: list[ExtractedQuestion] = []
    for q in questions:
        if q.question_number in seen:
            errors.append({
                "kind": "duplicate_question_number",
                "question_number": q.question_number,
                "first_region": seen[q.question_number].regions[0],
                "duplicate_region": q.regions[0],
            })
            continue
        seen[q.question_number] = q
        final_questions.append(q)
    # Remove the first occurrence of any question_number that duplicated.
    bad_qnums = {
        e["question_number"] for e in errors
        if e.get("kind") == "duplicate_question_number"
    }
    questions = [q for q in final_questions if q.question_number not in bad_qnums]

    return ExtractionResult(
        document_id=document_id,
        extractor_version=EXTRACTOR_VERSION,
        questions=questions,
        pages_processed=pages_processed,
        pages_skipped=pages_skipped,
        errors=errors,
    )


def fetch_pdf_from_storage(document_id: str) -> bytes:
    """Fetch PDF bytes from Supabase Storage via service-role client.

    Reads document_assets to get storage_bucket + storage_path, then
    downloads from the library bucket.  Read-only — no writes.
    """
    from app.db.supabase_client import get_supabase_admin

    sb = get_supabase_admin()
    row = (
        sb.table("document_assets")
        .select("storage_bucket, storage_path")
        .eq("id", document_id)
        .single()
        .execute()
        .data
    )
    if not row:
        raise ValueError(f"document_assets row not found for id={document_id!r}")

    bucket: str = row["storage_bucket"]
    path: str = row["storage_path"]

    data = sb.storage.from_(bucket).download(path)
    if not data:
        raise ValueError(
            f"Storage download returned empty bytes for bucket={bucket!r}, path={path!r}"
        )
    return data
