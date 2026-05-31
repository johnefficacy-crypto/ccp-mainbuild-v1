# Sanitization SOP — v1

UPSC papers acquired from coaching distributions (Drishti, Vision IAS, ForumIAS, etc.)
carry watermarks that interfere with OCR. This SOP describes how to sanitize a
`raw_coaching` PDF into a `sanitized_coaching` PDF eligible for extraction.

## When to use this SOP

Triggered when:
- Current year's UPSC paper is published by a coaching service (before official UPSC
  archive release ~1 year later)
- A `raw_coaching` document is uploaded; the admin or SME needs to produce its sanitized
  counterpart

## Source kind taxonomy

| `source_kind` value   | Extraction eligible? | Description |
|----------------------|---------------------|-------------|
| `official_archive`    | Yes                 | UPSC's published archive; no watermark; authoritative. Available ~1 year after exam. |
| `official_scan`       | Yes (legacy)        | Legacy alias for official_archive; prefer `official_archive` for new uploads. |
| `sanitized_coaching`  | Yes                 | Coaching PDF; watermarks/overlays removed and verified clean. |
| `sme_authored`        | Yes                 | SME-authored or transcribed test content. |
| `raw_coaching`        | **No**              | Coaching PDF as-is; overlays present. Must be sanitized first. |
| `crowd_sourced`       | **No**              | Community-contributed; provenance unclear. |
| `unknown`             | **No**              | Not yet classified. |

## Quality target

The sanitized PDF must:
- Have no visible watermark across all question pages
- Preserve English question text undamaged
- Preserve all original page numbers and ordering
- Contain only English question pages (Hindi/vernacular pages may be removed or kept;
  v1 extractor skips them either way)

## Recommended tooling

### ImageMagick (fastest for Drishti's "Al Vision" watermark)

The Drishti watermark is a flat color overlay at consistent opacity. ImageMagick handles
this in one command:

```bash
# Single-page test first
convert input.pdf[2] \
    -fuzz 25% -fill white \
    -opaque "rgb(220,180,180)" \
    -density 300 \
    test_page3.png

# Inspect test_page3.png. Adjust fuzz % and target color
# until the watermark disappears without damaging body text.

# Full document
convert input.pdf \
    -fuzz 25% -fill white \
    -opaque "rgb(220,180,180)" \
    -density 300 \
    sanitized.pdf
```

Tune the `rgb(...)` value by sampling the watermark color in GIMP or any image editor.
The default value above is calibrated for the Drishti distribution observed in v1 fixtures.

### Other coaching distributions

| Distribution | Watermark color (approximate) | Notes |
|--------------|------------------------------|-------|
| Drishti (Al Vision) | rgb(220,180,180), light red | Tested, works |
| Vision IAS | TBD on first encounter | Add row when seen |
| ForumIAS | TBD on first encounter | Add row when seen |

When encountering a new distribution, add a row here with the calibrated values.

## Quality check before upload

After sanitization, verify by spot-check:
1. Render pages 3, 5, 7 (first three English question pages)
2. Confirm: no visible watermark, body text unchanged
3. Render page 1 (cover) — should be intact
4. Word count comparison: `pdftotext input.pdf - | wc -w` vs
   `pdftotext sanitized.pdf - | wc -w`. Counts should differ by < 5%
   (watermark contributes minimal text-layer content).

If any of the above fails, retune ImageMagick parameters and retry. Do NOT upload a
sanitized PDF that damages body text — it will silently degrade extraction recall.

## Upload procedure

1. Upload the RAW PDF first via admin doc flow with `source_kind='raw_coaching'`. Record
   the resulting `document_id`.
2. Run sanitization producing `sanitized.pdf`.
3. Upload `sanitized.pdf` with:
   - `source_kind='sanitized_coaching'`
   - `sanitized_from_document_id=<id from step 1>`
   - `structural_format` and `exam_identity` matching the raw doc
4. The v1 extractor will now accept the document.

## Why clean-input pipeline, not a watermark filter in code

An earlier design (deferred H item from PR #499) considered a runtime watermark-detection
module. That approach was rejected in favour of upstream sanitization:

1. **Architectural**: the extractor's job is segmentation, not OCR preprocessing. Mixing
   concerns produces brittle code.
2. **Generalizability**: a code-resident filter needs maintenance as new coaching services
   emerge. The SOP scales with documentation, not code.
3. **False-positive risk**: a regex catching "Al Vision" could catch a legitimate question
   about "AI vision". Sanitization happens before the text layer is created.
4. **SME effort**: ~30–90 min per paper, ~10–15 papers per year. Bounded and one-time.
5. **Audit**: storing both raw and sanitized versions (via `sanitized_from_document_id`)
   lets reviewers verify what the extractor actually read.

The deferred H item from PR #499 is therefore **cancelled**, not deferred.

## What this SOP intentionally does not cover

- Hindi/vernacular page filtering: v1 extractor skips even pages automatically.
- Cropping: not needed if watermark removal is clean.
- OCR re-pass: not needed; extractor does its own OCR.
- Manual transcription: **never**. If sanitization fails, escalate — do not retype
  questions from the watermarked PDF.

## v2 plan

When v2 lands, this SOP will be supplemented (not replaced) by:
- Automated sanitization pipeline triggered on `raw_coaching` upload
- Per-distribution detector modules
- Vision-model-based watermark removal for complex cases
- Multilingual OCR enabling vernacular page extraction
