# Exam Intelligence Extraction v1

Deterministic, OCR-based question segmentation for scanned UPSC PYQ papers.

## System dependencies

Tesseract OCR must be installed on the host system.

```bash
# Ubuntu / Debian (CI and Docker)
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng

# Verify
python -c "import pytesseract; print(pytesseract.get_tesseract_version())"
```

If Tesseract is not installed, importing this package raises a `RuntimeError`
immediately (fail-fast, not at first use).

## Python dependencies

Added to `app/backend/requirements.txt`:

```
PyMuPDF>=1.23
pytesseract>=0.3.10
Pillow>=10.0
python-Levenshtein>=0.20
```

NumPy is already present in requirements.

## Module overview

| Module | Responsibility |
|---|---|
| `types.py` | `Word`, `Region`, `ExtractedQuestion`, `ExtractionResult` dataclasses |
| `ordinal.py` | Detect / strip leading printed question numbers (`PATTERN` constant) |
| `ocr.py` | Tesseract wrapper; pixel→normalized coord conversion |
| `layout.py` | Column detection via x-histogram bimodality |
| `segmentation.py` | Vertical clustering, question-block emission |
| `pipeline.py` | Orchestration: `extract(bytes) → ExtractionResult` |

## Usage

```python
from app.exam_intelligence.extraction import extract, fetch_pdf_from_storage

pdf_bytes = fetch_pdf_from_storage("83722a86-610b-471d-8b6b-4a8397aa1791")
result = extract(pdf_bytes, document_id="83722a86-...")
print(f"{len(result.questions)} questions extracted")
```

## Corpus assumptions (v1)

- Scanned PDF, no text layer, 300 DPI JPEG pages
- Bilingual: English on odd pages, Hindi on even pages
- Two-column layout, gutter ≈ x=0.5 normalized (detected per-page)
- Page width varies: 2026 paper ≈ 538 pts, 2025 paper ≈ 602 pts
  → all geometry in normalized [0,1] coords

## Non-goals (v1)

- No DB writes of any kind
- No LLM
- No Hindi / even-page processing
- No options, topic tags, matching tables, figures
