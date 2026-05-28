"""Extraction pipeline: PDF bytes → ExtractionResult.

This module is the public entry point. It:
1. Opens the PDF with PyMuPDF (fitz).
2. Processes odd pages only (English content; even pages are Hindi).
3. Rasterizes each page at 300 DPI to a PIL image.
4. Runs OCR (ocr.ocr_page) and segmentation (segmentation.segment_page).
5. Assembles and returns an ExtractionResult.

No writes to any database table occur in this module.
"""
from __future__ import annotations

import io
import logging

import fitz  # PyMuPDF
from PIL import Image

from .ocr import DPI, ocr_page
from .segmentation import segment_page
from .types import ExtractionResult, ExtractedQuestion

logger = logging.getLogger(__name__)

EXTRACTOR_VERSION = "0.1.0"


def extract(
    pdf_bytes: bytes,
    document_id: str,
    pages: list[int] | None = None,
) -> ExtractionResult:
    """Extract questions from a scanned PDF.

    Args:
        pdf_bytes: Raw PDF content.
        document_id: Identifier recorded in the result (not written anywhere).
        pages: 1-indexed page numbers to process. Defaults to odd pages only.

    Returns:
        ExtractionResult with extracted questions and diagnostics.
        No database writes occur.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total_pages = doc.page_count

    if pages is None:
        # Odd pages carry English content; even pages are Hindi translations.
        # Page 1 is the instructions/cover sheet — skip it to avoid spurious ordinals.
        pages = [p for p in range(3, total_pages + 1) if p % 2 == 1]

    # Resolve pages_skipped as all pages not in the requested set.
    all_pages = set(range(1, total_pages + 1))
    pages_skipped = sorted(all_pages - set(pages))

    questions: list[ExtractedQuestion] = []
    pages_processed: list[int] = []
    errors: list[dict] = []

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
            page_questions = segment_page(words, page_num)
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
    downloads from the library bucket. Read-only — no writes.
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
