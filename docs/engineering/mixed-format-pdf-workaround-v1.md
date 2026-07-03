# Mixed-Format PDF Workaround — v1 (split-and-reupload SOP)

- Status: ACTIVE — companion SOP for J3 Mixed-Format PDF Gate (Option B, `docs/status/J3-Mixed-Format-PDF-Gate-2026-07-02.md`).
- Audience: admins uploading PDFs via the Exam Intelligence document admin surface (`ExamIntelDocuments.jsx` / `DocumentsPanel.jsx`, backed by `POST /admin/exam-intelligence-cms/documents/*`).
- Applies to: any single uploaded PDF whose pages do not all share one `structural_format` (e.g. a Prelims-style MCQ objective section followed by a Mains-style descriptive/essay section within the same file).

## Why this exists

`document_assets.structural_format` is a single-valued column — one format per document (see `app/supabase/migrations/152_extraction_paper_format_scope_fence.sql`). The v1 extraction pipeline (`app/backend/app/exam_intelligence/extraction/pipeline.py`) applies exactly one column/segmentation strategy to every page it processes, and only the `mcq_bilingual_two_column` format is v1-eligible. If a document actually mixes formats page-to-page but is labelled with a single format, the extractor will run its MCQ strategy over non-MCQ pages too, silently emitting garbage candidate questions into the `pyq_questions` review queue.

Rather than risk that silent mis-extraction, the platform requires an admin to **declare** a document mixed-format (`document_assets.metadata.mixed_format = true`) once they know it mixes formats. Declaring the flag causes the extraction pipeline's scope fence to reject the document outright — `ExtractionMixedFormatError` — before any OCR call runs, and before any row is written to `pyq_questions`.

This is a **temporary, manual workaround** (Option B in the gate doc). It does not auto-segment the PDF. A later gate may introduce page-range classification (`document_format_segments`, see the gate doc addendum) once a non-MCQ extractor tier exists — until then, the fix is to split the file yourself.

## Step-by-step: split and re-upload

1. **Identify the page ranges.** Open the source PDF and note which page ranges are homogeneous in structural format (e.g. pages 1–20 are two-column bilingual MCQ; pages 21–35 are single-column essay/descriptive).
2. **Split the PDF into one file per homogeneous range.** Use any reliable local PDF-splitting tool (e.g. `pdftk`, `qpdf`, or a desktop PDF editor) to produce N separate PDF files, one per structural-format range. Example with `qpdf`:
   ```
   qpdf --empty --pages source.pdf 1-20 -- gs1-mcq-section.pdf
   qpdf --empty --pages source.pdf 21-35 -- gs1-essay-section.pdf
   ```
3. **Upload each sub-document separately** through the existing admin upload flow (`ExamIntelDocuments.jsx` "Upload exam-intelligence PDF" form, or the equivalent `DocumentsPanel.jsx` upload step). For each sub-document:
   - Set `exam_identity` and let `structural_format` auto-infer (or override it) to the *single* correct format for that range.
   - Leave `metadata.mixed_format` unset (default `false`) on each sub-document — each one is now homogeneous.
   - Set `source_kind` as usual.
4. **Do not set `mixed_format=true` on the sub-documents.** The flag is only for the original mixed file, to keep it out of the extraction queue. If a sub-document was mistakenly still declared mixed, clear the flag via the "Mixed-format" toggle in the document admin table (or `POST /admin/exam-intelligence-cms/documents/{document_id}/mixed-format` with `{"mixed_format": false, "reason": "..."}`).
5. **Extract each sub-document independently.** Each one goes through `complete-upload` → the normal extraction pipeline exactly as any other homogeneous document. Only the `mcq_bilingual_two_column` sub-document(s) will actually be v1-extractable; other formats (essay, technical, vernacular) will still raise their existing scope-fence errors (`ExtractionNotSupportedError`, etc.) until a future extractor tier supports them — that is expected and unrelated to the mixed-format flag.
6. **(Optional) Archive or leave the original mixed file declared.** The original mixed-format document can stay in the system with `metadata.mixed_format=true` as a record that it was superseded by its split sub-documents, or be archived via the existing archive endpoint. Do not clear its flag and attempt to extract it directly — it will still fail as designed.

## Declaring the flag

Admins with CMS permission can toggle the flag from the document list in the Exam Intelligence document admin surface (button: "Mark mixed-format" / "Mixed-format ✓ (clear)"), or directly:

```
POST /admin/exam-intelligence-cms/documents/{document_id}/mixed-format
{
  "mixed_format": true,
  "reason": "Contains both an MCQ section and a descriptive section"
}
```

This updates `document_assets.metadata.mixed_format` (JSONB; no schema migration required) and is audit-logged (`exam_intel.cms.document.set_mixed_format`).

## What happens if you try to extract a declared-mixed document anyway

The extraction pipeline's scope fence raises before any OCR call:

```
ExtractionMixedFormatError: Document <id> is declared mixed-format
(metadata.mixed_format=true): ... Split the source PDF into homogeneous
per-format sub-documents ... See the workaround SOP:
docs/engineering/mixed-format-pdf-workaround-v1.md.
```

Zero rows are written to `pyq_questions` in this path — the guard runs before `fitz.open`/OCR/segmentation, so no processing of the mixed file occurs at all.

## Scope / limitations

- **No auto-segmentation.** This SOP is manual. There is no per-page classifier and none is planned as part of this gate.
- **B1 admin-declared detection only.** There is no heuristic pre-check that automatically flags a file as mixed; an admin must notice and declare it explicitly.
- **v1 eligibility unchanged.** Splitting a mixed file does not make its non-MCQ sub-documents extractable by v1 — only `mcq_bilingual_two_column` sub-documents will actually produce `pyq_questions` rows today.
- See `docs/status/J3-Mixed-Format-PDF-Gate-2026-07-02.md` for the full decision record, including the recorded (not-yet-built) future Option A (`document_format_segments` child table with a non-overlap page-range constraint, no backfill).
