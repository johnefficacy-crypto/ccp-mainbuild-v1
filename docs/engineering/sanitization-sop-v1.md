# Sanitization SOP — v1 Extractor Clean-Input Requirement

**Status:** Active  
**Applies to:** v1 extractor (`exam_intelligence.extraction`, extractor_version 0.2.x)

---

## Why clean input, not a watermark filter

The v1 OCR pipeline (Tesseract PSM 3) runs on full-page rasterized images at 300 DPI.
Watermarks and coaching-overlay text contaminate the OCR word stream in three ways:

1. **Text collision** — OCR picks up watermark characters as real words, injecting
   spurious tokens into the word list that the segmentation module cannot distinguish
   from question text.
2. **Confidence dilution** — semi-transparent overlays reduce ink contrast and depress
   word-level OCR confidence, dragging p50 confidence below the `MIN_WORD_CONFIDENCE=30`
   floor and dropping real words.
3. **Layout disruption** — diagonal or full-bleed overlays add spurious x-coordinate
   mass that defeats the gutter-band column splitter, collapsing both columns into one.

A post-OCR watermark filter would need to:
- Detect all coaching agency naming conventions (hundreds, ever-changing)
- Handle partial overlap with real question text without over-stripping
- Be maintained for each new coaching source added to the corpus

This is fragile and gets harder over time. A pre-OCR clean-input gate is permanent:
sanitize once at upload time, run extraction on the clean copy.

---

## Source kind taxonomy

| `source_kind` value   | Extraction eligible? | Description |
|----------------------|---------------------|-------------|
| `official_scan`       | Yes                 | Directly from UPSC/government press; no overlays |
| `sanitized_coaching`  | Yes                 | Coaching PDF; watermarks/overlays removed; verified clean |
| `raw_coaching`        | **No**              | Coaching PDF as uploaded; overlays present |
| `crowd_sourced`       | **No**              | Community-contributed; provenance unclear |
| `unknown`             | **No**              | Not yet classified |

The v1 extractor raises `ExtractionRequiresCleanInputError` for any ineligible kind
before any OCR runs. No garbage rows are written to `extraction_runs`.

---

## How to sanitize a coaching PDF

### Prerequisites

- `pdftk` or `qpdf` for page extraction / reassembly
- `ghostscript` for rasterization / recompression
- Any PDF editor (Adobe Acrobat, PDF-XChange, LibreOffice Draw) for manual overlay removal

### Step-by-step

1. **Obtain the raw PDF** — upload with `source_kind=raw_coaching`. Do not attempt extraction.

2. **Identify overlay type:**
   - *Text overlays* (coaching agency name stamped as a PDF text object) →
     open in editor, select-all on each page, delete any text that is not
     question content.
   - *Image overlays* (semi-transparent PNG/JPEG burned into the page) →
     use Ghostscript to re-render pages and manually remove via image editing,
     or use Acrobat's "Edit PDF" layer tools.
   - *Full-page watermarks* (repeated diagonal text) → use Acrobat's watermark
     removal or a Ghostscript PostScript filter.

3. **Ghostscript clean rasterize + repack** (removes most PDF-layer overlays):
   ```bash
   gs -dBATCH -dNOPAUSE -sDEVICE=pdfwrite \
      -dCompatibilityLevel=1.4 \
      -dPrinted=false \
      -sOutputFile=clean.pdf \
      raw.pdf
   ```
   This flattens transparent layers. Inspect the output; some overlays survive flattening.

4. **Verify** — open `clean.pdf` in a PDF viewer and confirm:
   - No coaching agency name visible on any page
   - No semi-transparent logos or diagonal watermarks
   - Question text is fully legible

5. **Upload the clean PDF** via the admin UI with:
   - `source_kind = sanitized_coaching`
   - `sanitized_from_document_id = <UUID of the raw_coaching document uploaded in step 1>`

6. **Trigger extraction** — the v1 extractor will now accept the document.

---

## Quality bar

A sanitized document is accepted only if the acceptance gate (≥ 0.80 recall on the
2026 GS-I fixture) continues to hold after the document enters the corpus. Run:

```bash
pytest tests/exam_intelligence/extraction/test_pipeline_against_fixture.py \
    -m integration -v -s
```

If recall drops, the overlay was not fully removed; repeat steps 2–4.

---

## Grandfather clause

Documents uploaded before migration 153 that have no `source_kind` value are
backfilled to `sanitized_coaching` (migration 153, `UPDATE document_assets WHERE id IN (...)`).
Only the two known acceptance-gate fixture documents are backfilled; all other
pre-153 documents remain `unknown` and require classification before extraction.

---

## Adding a new source to the corpus

1. Obtain the PDF.
2. Check `source_kind`: if it is a coaching aggregate, it is `raw_coaching` by default.
3. Follow the sanitization steps above.
4. Upload with `source_kind=sanitized_coaching`, `sanitized_from_document_id` pointing at the raw version.
5. Classify `exam_identity` and verify `structural_format` is auto-inferred correctly.
6. Run the acceptance gate to confirm recall ≥ 0.80.
