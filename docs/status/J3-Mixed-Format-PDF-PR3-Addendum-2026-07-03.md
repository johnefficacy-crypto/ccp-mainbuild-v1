# J3 Mixed-Format PDF — PR 3 Delivery Addendum

- Parent gate: `docs/status/J3-Mixed-Format-PDF-Gate-2026-07-02.md`
- Date: 2026-07-03
- Status: **CODE-FIXED, VALIDATION PENDING** (Option B / B1, as scoped by PR 3 in `docs/status/J3-Implementation-Checklist-2026-07-02.md`)

## What PR 3 delivered

- `document_assets.metadata.mixed_format=true` — validated (boolean-only; any non-`true` value, including missing key, is treated as not-mixed), B1 admin-declared detection only. No migration — reuses the existing `metadata` JSONB column.
- `ExtractionMixedFormatError` raised in `app/backend/app/exam_intelligence/extraction/pipeline.py`'s `extract()` scope fence, before `fitz.open`/OCR/any processing. Zero `pyq_questions` writes occur on this path.
- Admin control to declare/clear the flag: `POST /admin/exam-intelligence-cms/documents/{document_id}/mixed-format`, surfaced in `app/frontend/src/pages/admin/studyos/ExamIntelDocuments.jsx` as a per-row "Mark mixed-format" / "Mixed-format ✓ (clear)" toggle. No new top-level route or sidebar destination added (existing document admin surface only).
- SOP doc created: `docs/engineering/mixed-format-pdf-workaround-v1.md` (split-and-reupload procedure), linked from the error message.
- Acceptance tests added under the extraction pipeline test suite (see PR body for the exact file).

## Option A — recorded, NOT built (documentation only)

Per OD-3 (`docs/status/J3-OD-Resolutions-Locked-2026-07-02.md` §8: "N/A-now"), a later Option A gate would introduce:

- A new child table `public.document_format_segments` (schema already specified in the parent gate doc, Section C, "Option A") — per-document, per-page-range `structural_format` assignments, with `page_start`/`page_end` and a **non-overlap constraint** enforced via a GiST `EXCLUDE` constraint on `int4range(page_start, page_end)` (or an equivalent validation trigger).
- **No backfill** of existing `document_assets` rows — absence of segment rows preserves today's single-format path exactly as-is.
- Segment-aware dispatch in `extraction/pipeline.py` and `extraction/dispatch.py` (per-segment `is_extractable_by_v1`, per-segment scope-fence errors, `pages_skipped` reasoning), and admin UI to author page ranges.

**PR 3 does not build any of this.** No `document_format_segments` table, migration, RLS policy, or segment-aware dispatch code exists in this PR. This section exists only to keep the recorded decision visible next to the shipped Option B code, per CLAUDE.md checklist-hygiene and migration-discipline rules (decisions are documented before/independently of implementation; nothing here is `MERGED` or `VERIFY DB` — it is a **PLANNED**, not-yet-scoped future item).

## Verification status

- Code: landed in this PR.
- Live/Supabase operator proof: not applicable (no schema change to verify — `metadata` JSONB already exists and is already covered by `document_assets`'s existing RLS policies, which are unchanged).
- Test proof: see PR body "Commands Run" section for the pytest invocation and results.
