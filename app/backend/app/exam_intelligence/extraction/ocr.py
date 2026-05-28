"""Tesseract OCR wrapper — word-level bbox output, normalized coordinates.

Fails fast at import time if the tesseract binary is not on PATH so that
missing-system-dependency errors surface immediately, not at first use.

Local install:
    sudo apt-get install -y tesseract-ocr tesseract-ocr-eng
Verify:
    python -c "import pytesseract; print(pytesseract.get_tesseract_version())"
"""
from __future__ import annotations

import statistics

import pytesseract
from PIL import Image
from pytesseract import Output

from .types import Word

# Fail fast at import time if tesseract binary is not on PATH.
try:
    pytesseract.get_tesseract_version()
except pytesseract.TesseractNotFoundError as e:
    raise RuntimeError(
        "Tesseract OCR binary not found. "
        "Install: sudo apt-get install -y tesseract-ocr tesseract-ocr-eng\n"
        "Verify:  python -c \"import pytesseract; print(pytesseract.get_tesseract_version())\""
    ) from e

TESSERACT_PSM = 3      # Fully automatic page segmentation (handles multi-column)
TESSERACT_LANG = "eng"
MIN_WORD_CONFIDENCE = 30
DPI = 300              # for rasterization


def ocr_page(page_image: Image.Image, page_number: int) -> list[Word]:
    """Run Tesseract on a single page image and return normalized Word list.

    Pixel-coordinate bboxes are converted to normalized [0,1] top-left coords
    using the image dimensions. Words with empty text or confidence below
    MIN_WORD_CONFIDENCE are filtered out.
    """
    width, height = page_image.size
    if width == 0 or height == 0:
        return []

    config = f"--psm {TESSERACT_PSM} --oem 3"
    data = pytesseract.image_to_data(
        page_image,
        lang=TESSERACT_LANG,
        config=config,
        output_type=Output.DICT,
    )

    words: list[Word] = []
    n = len(data["text"])
    for i in range(n):
        text = (data["text"][i] or "").strip()
        if not text:
            continue
        conf = float(data["conf"][i])
        if conf < MIN_WORD_CONFIDENCE:
            continue

        px_left = int(data["left"][i])
        px_top = int(data["top"][i])
        px_w = int(data["width"][i])
        px_h = int(data["height"][i])

        x_min = px_left / width
        y_min = px_top / height
        x_max = (px_left + px_w) / width
        y_max = (px_top + px_h) / height

        # Clamp to [0, 1]
        x_min = max(0.0, min(1.0, x_min))
        y_min = max(0.0, min(1.0, y_min))
        x_max = max(0.0, min(1.0, x_max))
        y_max = max(0.0, min(1.0, y_max))

        if x_max <= x_min or y_max <= y_min:
            continue

        words.append(Word(
            text=text,
            bbox=(x_min, y_min, x_max, y_max),
            page=page_number,
            confidence=conf,
        ))

    return words
