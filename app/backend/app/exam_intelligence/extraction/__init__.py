"""UPSC PYQ question-segmentation extractor — v1, OCR-based, read-only."""
from .pipeline import extract, fetch_pdf_from_storage
from .types import ExtractionResult, ExtractedQuestion, Region, Word

__all__ = [
    "extract",
    "fetch_pdf_from_storage",
    "ExtractionResult",
    "ExtractedQuestion",
    "Region",
    "Word",
]
