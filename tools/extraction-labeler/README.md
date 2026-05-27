# Extraction Labeler — UPSC CSE PYQ v1 bbox tool

Standalone browser tool for drawing bounding-box regions on PDF pages and
exporting a `questions.json` fixture that conforms to the v1 schema.

Read `docs/engineering/exam-intelligence-extraction-v1-corpus.md` before
labeling.

## How to run

```
cd tools/extraction-labeler
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

## How to load a PDF

Click **Load PDF** in the header and pick a local `.pdf` file. The file is
never uploaded — it stays in your browser.

## Mouse and keyboard cheatsheet

| Action | Input |
|--------|-------|
| Draw new bbox | Click-drag on the PDF canvas |
| Select existing bbox | Click on the rectangle |
| Move bbox | Drag selected rectangle |
| Resize bbox | Drag a corner handle |
| Delete selected bbox | `Delete` or `Backspace` |
| New question | Click **+ New** button or press `n` |
| Next page | `→` or `↓` arrow key |
| Previous page | `←` or `↑` arrow key |

## Labeling workflow

1. Load your PDF.
2. Fill in **document_id**, **exam_id**, **paper_name**, **year**, and
   **page_count** in the right-hand panel (these come from the CMS, not the
   PDF filename).
3. Click **+ New** to create a question slot.
4. Draw a rectangle around the question text on the PDF. The rectangle
   attaches to the currently-selected question.
5. For questions that span columns or pages, draw additional rectangles — each
   adds a region to the same question.
6. Type or paste the question text into the textarea. The hash recomputes on
   blur.
7. Repeat for all questions.

## How to export

When validation passes (no red banner), click **⬇ Export questions.json**.
The file downloads immediately.

Move it to the fixture directory:

```
app/backend/tests/fixtures/exam_intelligence_extraction/upsc_cse_pyq_v1/questions.json
```

> **Copyright notice**: Do NOT commit fixture files derived from copyrighted
> UPSC content until legal review has cleared inclusion. Until cleared, store
> labeled fixtures in a private location and reference `document_assets.id`
> only — do not include the question text in a public commit.

## Session persistence

Labels autosave to `localStorage` every 5 seconds and on every edit, keyed by
`document_id`. Reload the page and enter the same `document_id` to restore a
session. Use **Clear session** to wipe it.

## Running tests

```
npm test
```

Tests cover `lib/hash.ts` (normalization + SHA-256) and `lib/coords.ts`
(canvas-pixel ↔ normalized, PDF-native ↔ normalized).
