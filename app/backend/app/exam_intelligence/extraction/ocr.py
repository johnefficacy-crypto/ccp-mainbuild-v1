from __future__ import annotations
from PIL import Image
from .types import Word

DPI = 300


def ocr_page(img: Image.Image, page_num: int) -> list[Word]:
    """OCR a rasterized page and return word-level bboxes (normalized coords).

    Uses Tesseract with --psm 6 word-level output.
    """
    import pytesseract

    w, h = img.size
    data = pytesseract.image_to_data(
        img,
        lang="eng",
        config="--psm 6",
        output_type=pytesseract.Output.DICT,
    )
    words: list[Word] = []
    for i, text in enumerate(data["text"]):
        text = text.strip()
        if not text:
            continue
        x = data["left"][i] / w
        y = data["top"][i] / h
        bw = data["width"][i] / w
        bh = data["height"][i] / h
        words.append(Word(text=text, bbox=(x, y, x + bw, y + bh), page=page_num))
    return words
