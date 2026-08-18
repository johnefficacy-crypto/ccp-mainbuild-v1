---
name: pyq-frontload-notes
description: UPSC CSE Mains PYQ bulk-import project state, reusable IDs, and bug log. Read before continuing any year's import.
---

# UPSC CSE Mains PYQ frontload — status & bugs

## Reusable IDs (do not recreate)
- exam_id (UPSC CSE) = `5466e62f-7382-4a38-ba96-2fe5fbfeaba2`
- Mains exam_phase_id (shared/null-cycle) = `626ec667-4bbf-4420-8715-48c5b83e0d11`
- Section IDs: Essay=`ea24354e-0aa6-4102-a273-36773e3f52d6`, GS1=`daca2e9f-012e-46fc-8b10-b6df340b4200`, GS2=`d332fcad-6750-4542-af0a-3f203f819096`, GS3=`b5cbb735-b687-4de5-90cb-3978f48a71a1`, GS4=`dee30326-920a-40cf-bee0-a5b4c76760f7`

## Year status
- Done: 2019, 2024, 2025 (prior sessions)
- Done: 2022 GS1 (20Q) + Essay (8Q) — paper_id `a8a393fd-dc45-40d2-a892-8dacac59400e`, source_id `f628c0d2-083a-4589-a031-e91da5cb644a`. GS2/GS3/GS4 pending source docs.
- In process: 2018
- Remaining: 2013-2017

## API payload shape (confirmed working)
All admin CMS POSTs wrap fields: `{ reason: "<string>", payload: { ...actual fields... } }`. Flat payload (no wrapper) gives misleading 422s like "exam_id is required" even when present.

Response shape: `{ ok, audit_id, row: { id, ... } }` — read `.row.id`, not `.id`.

### pyq-sources fields
`exam_id`, `source_type` (e.g. "official"), `title`, `metadata` (object, e.g. `{note: ""}`). NOT `source_name`/`year` (422 "Unknown field(s)").

### pyq-papers fields
`pyq_source_id`, `exam_id`, `exam_cycle_id`, `exam_phase_id`, `year`, `paper_date`, `shift`, `source_type`, `metadata`.

### pyq-questions fields
`pyq_paper_id`, `section_id`, `question_number`, `source_question_ref`, `display_order`, `question_text`, `question_type` ("descriptive" for Mains).

## Bug log (avoid repeating)
1. `question_number` must be globally unique per PAPER (not per section) — all 5 sections share one pyq_paper_id. Offset convention: GS1=1-20, GS2=21-40, GS3=41-60, GS4=61-79ish, Essay=80-87ish (verify actual counts per year).
2. `source_question_ref` must also be unique per paper — prefix every ref with section code from the start (GS1-Q1, Essay-A1, etc). Unprefixed refs collide → generic "Internal server error".
3. PowerShell UTF-8: always `[System.Text.Encoding]::UTF8.GetBytes($payload)` + `-Body $bytes` with `Content-Type: application/json; charset=utf-8` header — raw string body mangles curly quotes/em-dashes on PS 5.1.
4. Duplicate question_text (identical stems) trips a DB content-hash unique constraint → generic "Internal server error". Append distinguishing snippet if two questions in a batch are byte-identical.
5. **NEW (2022 Essay failure):** `display_order` is ALSO globally unique per paper, not per section — same failure mode as bug #1 but for display_order. Essay section using display_order 1-8 collided with GS1's already-used 1-8 → all 8 Essay POSTs failed with generic "Internal server error". Fix: give display_order the SAME offset as question_number (e.g. Essay display_order = 80-87, matching its question_number range), not a fresh 1-N per section.

## Extraction notes
- 2022 GS1 (labeled "History" in source filename) and Essay: digital PDF, clean pdfplumber text layer, bilingual (Hindi+English), English lines used directly — no OCR needed.
