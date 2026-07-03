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
from dataclasses import dataclass

import fitz  # PyMuPDF
import numpy as np
from PIL import Image

from .dispatch import (
    ELIGIBLE_FORMATS_V1,
    ELIGIBLE_SOURCE_KINDS_V1,
    ExamIdentity,
    SourceKind,
    StructuralFormat,
    is_extractable_by_v1,
    is_source_eligible_v1,
)
from .layout import assign_words_to_columns, detect_columns
from .ocr import DPI, TesseractUnavailableError, ocr_page
from .segmentation import reconstruct_lines, segment_column
from .types import ExtractionResult, ExtractedQuestion, Word

logger = logging.getLogger(__name__)

EXTRACTOR_VERSION = "0.2.0"

# The v1 corpus is two-column with the gutter reliably near x≈0.47-0.49
# (normalized).  Left-column body text and right-column question ordinals
# overlap in x globally — left text extends to ~0.49 while right ordinals
# start at ~0.47 — so layout.detect_columns' generic bimodal valley search
# frequently locks onto a spurious low-density bin far from the true gutter
# (e.g. 0.09, 0.31, 0.71).  A mis-placed split floods the right column with
# left-column words, dragging its effective_left west and causing the anchor
# gate to reject every genuine right-column ordinal.  Pinning the valley
# search to the gutter band below yields a stable split.
_GUTTER_BAND = (0.44, 0.52)
_GUTTER_BINS = 100

# Hardcoded page ranges for known corpus document IDs (exact UUID match).
CORPUS_ALLOWED_PAGES: dict[str, list[int]] = {
    "83722a86-610b-471d-8b6b-4a8397aa1791": list(range(3, 52, 2)),  # 2026 GS-I
    "afc8e285-0ea1-41a1-a524-83b8b3121154": list(range(3, 44, 2)),  # 2025 GS-I
}


# ─────────────────────────────────────────────────────────────────────────────
# Scope-fence error types
# ─────────────────────────────────────────────────────────────────────────────

class ExtractionNotSupportedError(RuntimeError):
    """v1 extractor cannot handle this document's structural_format."""


class ExtractionRequiresClassificationError(RuntimeError):
    """document_assets row has structural_format='unknown';
    classification required before extraction."""


class ExtractionRequiresCleanInputError(RuntimeError):
    """document_assets row has source_kind that is not in ELIGIBLE_SOURCE_KINDS_V1.

    Raw coaching PDFs (watermarks, promotional overlays) must be sanitized
    before the v1 extractor can produce reliable output. See
    docs/engineering/sanitization-sop-v1.md for the cleaning procedure.
    """


class ExtractionWrongDocumentKindError(RuntimeError):
    """document_assets row has document_kind not handled by v1.

    v1 processes pyq_paper only. Notifications, syllabi, corrigenda, and
    answer keys are out of scope for the question extractor.
    """


class ExtractionMixedFormatError(RuntimeError):
    """document_assets row is admin-declared mixed-format
    (metadata.mixed_format=true).

    A single uploaded PDF whose pages do not all share one
    structural_format (e.g. an MCQ objective section followed by a
    descriptive/essay section) cannot be safely run through the v1
    extractor: v1 applies one two-column MCQ strategy to every selected
    page, so non-MCQ pages would be silently mis-extracted into
    pyq_questions as garbage candidates (J3 Mixed-Format PDF Gate,
    Option B / B1 admin-declared detection).

    Split the source PDF into homogeneous per-format sub-documents (one
    structural_format each) and upload each separately, or reclassify the
    document if it was declared mixed-format in error. See the workaround
    SOP: docs/engineering/mixed-format-pdf-workaround-v1.md.
    """


ELIGIBLE_DOCUMENT_KINDS_V1: frozenset[str] = frozenset({'pyq_paper'})

MIXED_FORMAT_WORKAROUND_SOP: str = "docs/engineering/mixed-format-pdf-workaround-v1.md"


# ─────────────────────────────────────────────────────────────────────────────
# Document row dataclass (read-only; only the fields the extractor needs)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class _DocumentAssetsRow:
    id: str
    structural_format: StructuralFormat
    exam_identity: ExamIdentity
    source_kind: SourceKind
    document_kind: str
    storage_path: str
    mixed_format: bool = False


def _is_mixed_format_declared(metadata: dict | None) -> bool:
    """Validate the admin-declared metadata.mixed_format flag.

    B1 (admin-declared only, per J3 Mixed-Format PDF Gate / OD-2): the flag
    must be the JSON boolean literal `true`. Anything else (missing key,
    "true" string, 1, null, etc.) is treated as not-declared — app-level
    validation only, no DB constraint (no migration required for B1).
    """
    if not metadata:
        return False
    return metadata.get("mixed_format") is True


def _fetch_document_assets_row(document_id: str) -> _DocumentAssetsRow:
    """SELECT id, structural_format, exam_identity, source_kind, document_kind, storage_path, metadata
    FROM document_assets WHERE id = $1.

    Service-role client; read-only. Raises ValueError if not found.
    """
    from app.db.supabase_client import get_supabase_admin

    sb = get_supabase_admin()
    row = (
        sb.table("document_assets")
        .select("id, structural_format, exam_identity, source_kind, document_kind, storage_path, metadata")
        .eq("id", document_id)
        .single()
        .execute()
        .data
    )
    if not row:
        raise ValueError(f"document_assets row not found for id={document_id!r}")

    return _DocumentAssetsRow(
        id=row["id"],
        structural_format=StructuralFormat(row["structural_format"]),
        exam_identity=ExamIdentity(row["exam_identity"]),
        source_kind=SourceKind(row["source_kind"]),
        document_kind=row.get("document_kind") or "unknown",
        storage_path=row["storage_path"],
        mixed_format=_is_mixed_format_declared(row.get("metadata")),
    )


def allowed_pages_for(document_id: str, total_pages: int) -> list[int]:
    """Return the allowed page list for a known corpus ID.

    Falls back to odd pages 3..(total_pages-2) — drops cover and trailing blank.
    """
    if document_id in CORPUS_ALLOWED_PAGES:
        return CORPUS_ALLOWED_PAGES[document_id]
    return list(range(3, total_pages - 1, 2))


def _detect_columns_robust(words: list[Word]) -> list[tuple[float, float]]:
    """Split into two columns at the lowest-density bin in the gutter band.

    The generic detector (layout.detect_columns) searches the whole page for a
    histogram valley and is easily misled when the two columns overlap in x.
    This corpus-aware variant restricts the search to _GUTTER_BAND, where the
    real gutter always falls, and defers to detect_columns (which also handles
    the single-column case) whenever the band is unpopulated on either side.
    """
    if not words:
        return [(0.0, 1.0)]

    x_centers = np.array([(w.bbox[0] + w.bbox[2]) / 2.0 for w in words])
    counts, edges = np.histogram(x_centers, bins=_GUTTER_BINS, range=(0.0, 1.0))
    centers = (edges[:-1] + edges[1:]) / 2.0

    band_idx = [
        i for i, c in enumerate(centers)
        if _GUTTER_BAND[0] <= c <= _GUTTER_BAND[1]
    ]
    if not band_idx:
        return detect_columns(words)

    # Both columns must carry mass outside the band, else treat as single column.
    left_mass = int(counts[: band_idx[0]].sum())
    right_mass = int(counts[band_idx[-1] + 1:].sum())
    if left_mass == 0 or right_mass == 0:
        return detect_columns(words)

    # Lowest-density bin inside the band; tie-break toward the band centre.
    band_centre = (_GUTTER_BAND[0] + _GUTTER_BAND[1]) / 2.0
    best = min(band_idx, key=lambda i: (counts[i], abs(centers[i] - band_centre)))
    split = float(centers[best])
    return [(0.0, split), (split, 1.0)]


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

    columns = _detect_columns_robust(words)
    col_words = assign_words_to_columns(words, columns)

    split = columns[1][0] if len(columns) > 1 else None
    logger.debug(
        "DIAG page %d: words=%d split=%s ncols=%d last_acc_in=%d",
        page, len(words), None if split is None else round(split, 4),
        len(columns), last_accepted_ordinal,
    )

    questions: list[ExtractedQuestion] = []
    for col_idx in sorted(col_words.keys()):
        col = col_words[col_idx]
        if not col:
            continue
        col_start, _col_end = columns[col_idx]
        # Exclude words whose left edge is west of col_start (wide gutter-spanning
        # words assigned by centroid); their bbox[0] would drag effective_left
        # below the actual column edge and tighten the anchor gate too much.
        effective_left = min(
            (w.bbox[0] for w in col if w.bbox[0] >= col_start),
            default=col_start,
        )
        lines = reconstruct_lines(col)
        col_questions, last_accepted_ordinal = segment_column(
            lines, effective_left, last_accepted_ordinal, page
        )
        logger.debug(
            "DIAG page %d col %d: nwords=%d nlines=%d eff_left=%.4f "
            "first_line=%r qnums=%s last_acc_out=%d",
            page, col_idx, len(col), len(lines), effective_left,
            (" ".join(w.text for w in lines[0])[:40] if lines else ""),
            [q.question_number for q in col_questions], last_accepted_ordinal,
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
    # ─── Scope-fence guard ────────────────────────────────────
    # MUST run before any OCR or processing. Loud failure on
    # unsupported documents prevents silent garbage rows.

    doc_row = _fetch_document_assets_row(document_id)

    if doc_row.mixed_format:
        raise ExtractionMixedFormatError(
            f"Document {document_id} is declared mixed-format "
            f"(document_assets.metadata.mixed_format=true). This file mixes "
            f"multiple page-level structural formats (e.g. an MCQ objective "
            f"section followed by a descriptive/essay section) and cannot be "
            f"run through the v1 extractor, which applies a single strategy "
            f"to every selected page. Split the source PDF into homogeneous "
            f"sub-documents (one structural_format each) and upload each "
            f"separately, or clear the mixed_format flag if it was set in "
            f"error. Workaround SOP: {MIXED_FORMAT_WORKAROUND_SOP}."
        )

    if doc_row.structural_format == StructuralFormat.UNKNOWN:
        raise ExtractionRequiresClassificationError(
            f"Document {document_id} has structural_format='unknown'. "
            f"Admin must classify (set structural_format and exam_identity) "
            f"via the document_assets admin UI before extraction can run. "
            f"Exam identity: {doc_row.exam_identity.value}."
        )

    if not is_extractable_by_v1(doc_row.structural_format):
        raise ExtractionNotSupportedError(
            f"Document {document_id} has structural_format="
            f"{doc_row.structural_format.value!r}, which the v1 extractor does "
            f"not handle. v1 supports: {sorted(f.value for f in ELIGIBLE_FORMATS_V1)}. "
            f"Exam identity: {doc_row.exam_identity.value}. "
            f"Future extractor versions (v1.5/v2/v3) will handle additional "
            f"formats per the tier roadmap."
        )

    if not is_source_eligible_v1(doc_row.source_kind):
        raise ExtractionRequiresCleanInputError(
            f"Document {document_id} has source_kind={doc_row.source_kind.value!r}, "
            f"which is not eligible for the v1 extractor. "
            f"v1 requires clean input: {sorted(k.value for k in ELIGIBLE_SOURCE_KINDS_V1)}. "
            f"Raw coaching PDFs must be sanitized (watermarks/overlays removed) before "
            f"extraction. See docs/engineering/sanitization-sop-v1.md. "
            f"Exam identity: {doc_row.exam_identity.value}."
        )

    if doc_row.document_kind not in ELIGIBLE_DOCUMENT_KINDS_V1:
        raise ExtractionWrongDocumentKindError(
            f"Document {document_id} has document_kind={doc_row.document_kind!r}. "
            f"v1 extractor only processes {sorted(ELIGIBLE_DOCUMENT_KINDS_V1)}. "
            f"Notifications, syllabi, corrigenda, and answer keys are out of scope."
        )

    # ─── Existing pipeline below (unchanged) ──────────────────

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
        except TesseractUnavailableError:
            doc.close()
            raise
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
