from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Word:
    text: str
    bbox: tuple[float, float, float, float]  # x_min, y_min, x_max, y_max normalized
    page: int


@dataclass(frozen=True)
class Region:
    page: int
    bbox: tuple[float, float, float, float]


@dataclass
class ExtractedQuestion:
    question_number: int
    question_text: str
    regions: list[Region]
    confidence: float = 1.0
    out_of_scope_v1: bool = False


@dataclass
class ExtractionResult:
    document_id: str
    extractor_version: str
    questions: list[ExtractedQuestion]
    pages_processed: list[int]
    pages_skipped: list[int]
    errors: list[dict]
