from __future__ import annotations

import importlib


def test_server_import_is_not_blocked_by_missing_tesseract(monkeypatch):
    from app.exam_intelligence.extraction import ocr

    def _missing_binary():
        raise ocr.pytesseract.TesseractNotFoundError()

    ocr._tesseract_checked = False
    monkeypatch.setattr(ocr.pytesseract, "get_tesseract_version", _missing_binary)

    server = importlib.import_module("server")

    assert server.app.title == "Career Copilot API"


def test_ocr_call_reports_missing_tesseract(monkeypatch):
    from PIL import Image

    from app.exam_intelligence.extraction import ocr

    def _missing_binary():
        raise ocr.pytesseract.TesseractNotFoundError()

    ocr._tesseract_checked = False
    monkeypatch.setattr(ocr.pytesseract, "get_tesseract_version", _missing_binary)

    try:
        ocr.ocr_page(Image.new("RGB", (1, 1)), 1)
    except ocr.TesseractUnavailableError as exc:
        assert "Tesseract OCR binary not found" in str(exc)
    else:  # pragma: no cover - defensive assertion for clarity
        raise AssertionError("ocr_page should fail clearly when Tesseract is missing")
