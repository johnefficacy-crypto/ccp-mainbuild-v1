"""Dataclasses for the extraction pipeline.

All coordinates are normalized [0, 1], top-left origin, (x_min, y_min, x_max, y_max).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Word:
    text: str
    bbox: tuple[float, float, float, float]  # x_min, y_min, x_max, y_max NORMALIZED
    page: int
    confidence: float  # OCR confidence 0..100


@dataclass(frozen=True)
class Region:
    page: int
    bbox: tuple[float, float, float, float]  # normalized [0,1]


@dataclass(frozen=True)
class ExtractedOption:
    label: str        # normalised label: 'a', 'b', 'c', 'd'
    option_text: str


@dataclass(frozen=True)
class ExtractedQuestion:
    question_number: int  # printed number, not array index
    question_text: str
    regions: list[Region]
    confidence_by_field: dict[str, float]  # {'ocr_p50': 87.2, 'segmentation': 0.9, ...}
    options: tuple[ExtractedOption, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ExtractionResult:
    document_id: str
    extractor_version: str  # semver, hardcoded constant in pipeline.py
    questions: list[ExtractedQuestion]
    pages_processed: list[int]
    pages_skipped: list[int]  # with reasons
    errors: list[dict]  # non-fatal errors, page-scoped
