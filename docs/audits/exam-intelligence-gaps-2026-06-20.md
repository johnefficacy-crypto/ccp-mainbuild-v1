---
type: point-in-time-audit
date: 2026-06-20
source: operator screenshots + codebase verification
verified_against: main @ a2ded8c
status: open
---

# Exam Intelligence admin surface — gap audit 2026-06-20

Source: operator PDF with live production screenshots and encountered errors.
Verification method: code inspection only — no live HTTP calls made.

## P0 Runtime bugs

### BUG-EI-1 — `POST .../syllabus/propose` returns 404

**Endpoint:** `POST /api/admin/exam-intelligence/workspace/{exam_id}/syllabus/propose`

**Observed error:** `syllabus document not found: d91516ef-f745-424f-995b-410ec6d0c007`
The document exists in Supabase storage (signed URLs confirmed in screenshot).

**Root cause confirmed in code:**
`app/backend/app/exam_intelligence/syllabus_mapper.py` lines 97–109 (and duplicate block lines 503–516):

```python
doc_rows = _safe(
    lambda: (
        sb.table("document_assets")           # ← WRONG TABLE
        .select("id, exam_id, exam_cycle_id")  # ← exam_id column does not exist on document_assets
        .eq("id", syllabus_document_id)
        .limit(1).execute().data
    ),
    default=[],
) or []
if not doc_rows:
    raise ProposerError(f"syllabus document not found: {syllabus_document_id}", 404)
```

`document_assets` (migration 111) has no `exam_id` column.
The correct table is `syllabus_documents` (migration 031), which has `id, exam_id, exam_cycle_id`.
PostgREST silently ignores the missing column, the SELECT returns an empty list, and the 404 is raised.

**Fix scope:** `app/backend/app/exam_intelligence/syllabus_mapper.py` — change table name on both occurrences (lines ~99 and ~503) from `document_assets` to `syllabus_documents`.

**Additional observation:** `ProposerError` and `propose_syllabus_mentions` are both defined twice in the file (confirmed by grep). The second definitions shadow the first. This is a pre-existing code hygiene issue; the table-name fix must be applied to both copies or the file should be deduplicated.

---

### BUG-EI-2 — `GET /console/exams/{exam_id}` returns 500

**Endpoint:** `GET /api/admin/exam-intelligence/console/exams/{exam_id}`

**Observed error:** HTTP 500 Internal Server Error.

**Root cause confirmed in code:**
`app/backend/app/exam_intelligence/console_detail.py` lines 92–98:

```python
def _documents(sb, exam_id: str) -> list[dict[str, Any]]:
    return _paged(
        sb,
        lambda: sb.table("document_assets").select("id, extraction_status")
        .eq("exam_id", exam_id).order("id"),   # ← exam_id column does not exist on document_assets
        "console_detail.documents",
    )
```

Neither `exam_id` nor `extraction_status` exist on `document_assets` (migration 111).
The query returns zero rows, so `docs` is `[]`. `extracted` (line 257) is 0 rather than the real count.
The 500 likely comes from a downstream assertion or reason-parity violation in `_build_action_queue` (line 385–388) that fails when the document count is zero but other checks expect non-zero documents.

**Relationship to existing checklist item:** This is the concrete manifestation of the "Document readiness extraction status | NEEDS TARGETED RECHECK" checklist row. The audit originally suspected a mismatch; the mismatch is confirmed here.

**Fix scope:** `console_detail.py::_documents()` must be redesigned. Options:
- Query `syllabus_documents` (migration 031) filtered by `exam_id`, use `trust_status` as the readiness field.
- Join with a processing-job status source if a different "extraction" concept is intended.
A design decision is required before implementing the fix. See Lane H in the PR plan.

---

## UX / surface gaps — confirmed in code

### UX-EI-1 — Raw UUID visible in ReviewQueueTable

`app/frontend/src/features/admin/exam-intelligence/ReviewQueueTable.jsx` line 92 renders `{r.id}` as a "Row id" label without passing through `operatorChrome.humanizeToken`.
`SetupPanel.jsx` line 803 renders `{ptError.phaseId}` as a raw ID in an error message.
`operatorChrome.js` exists and defines the correct pattern (`humanizeToken`, `formatOperatorActor`), but these two sites violate it.

**Status:** CLEANUP PENDING

---

### UX-EI-2 — Topics CMS loads all topics globally (no exam scope filter)

`app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx` line 115 defines the `refTopic` descriptor with no `exam_id` or `exam_family_id` filter parameter. The backend has no `/topics` endpoint with exam scoping.
All topics across all exams are displayed simultaneously when using the CMS topic reference field.

**Status:** CLEANUP PENDING — not maintainable at scale.

---

### UX-EI-3 — OverviewPanel duplicates exam metadata already in workspace header

`app/frontend/src/pages/admin/exam-workspace/panels/OverviewPanel.jsx` lines 121–146 render exam name, slug, type, management lane, cadence, active status, organization name/type/trust tier, and family name. `ExamWorkspace.jsx` SmartHeader (lines 97–149) already renders exam name, family, slug, type, and active status.

**Status:** CLEANUP PENDING — confirmed duplication across two renders.

---

### UX-EI-4 — Bulk import JSON schema not documented

`ExamIntelCms.jsx` line 696 references a bulk-import endpoint. A `BulkImportModal.jsx` exists under the PYQ workbench. No in-repo documentation describes the accepted JSON/CSV schema, required fields, or whether a cycle/phase must be pre-created before importing.

**Status:** PLANNED — operator-facing docs needed.

---

### UX-EI-5 — "Phases needing dates" section lacks cycle context

`SetupPanel.jsx` lines 816–901 render a "Phases needing dates" section showing phases where `phase_start` is null. The section does not display which cycle the phases belong to or what cycle/year context they come from. With multiple cycles active, the operator cannot determine which cycle owns which phase stub.

**Status:** CLEANUP PENDING — UI label improvement needed.

---

### UX-EI-6 — Competition metrics: phase/category cutoffs unstructured

Migration 055 (`exam_competition_metrics`) stores `cutoff_trend` and `vacancy_by_category` as opaque JSONB. No schema documentation for the JSONB structure exists. Phase-wise and category-wise cutoffs are not surfaced as structured columns in the API response or UI.

**Status:** DESIGN QUESTION — requires operator decision on schema before implementation.

---

## Operator/product design questions — not verifiable from code alone

These were observed in screenshots but require explicit product or data decisions before any implementation can begin.

| # | Question | Location in screenshot | Code finding |
|---|---|---|---|
| DQ-1 | What is the purpose of the KG overview? Is exam-family hierarchy intended? | Page 3 | No hierarchical family→exam→cycle view exists in any current frontend component |
| DQ-2 | What does active/inactive mean for an exam? How does an operator activate? | Page 4 | `exams.is_active` boolean exists in DB; no UI toggle confirmed |
| DQ-3 | Business definition of core / managed-light / indexed not surfaced in UI | Page 4 | `coverage_depth` enum stored in DB; no UI glossary |
| DQ-4 | How are common subjects (Quant/Reasoning/English) managed across exam families? | Page 6 | No cross-exam subject grouping in current schema |
| DQ-5 | Error pattern taxonomy: time pressure ≠ all unattempted; guesswork/misread not inferrable from attempt data | Page 7 | Error pattern enum defined in mastery writer; no behavioral inference |
| DQ-6 | PYQ PDF upload: bilingual / two-column format handling | Page 8 | OCR pipeline exists; no column-split or bilingual parse documented |
| DQ-7 | How to add PYQ papers for historical cycles (2016, 2018 pre/mains) | Page 15 | PYQ import UI exists; no explicit historical-cycle workflow documented |

---

## Items that appeared in screenshots but were NOT verified as bugs

- **"affects" True/False display** (page 5): In code, `affects_*` fields render as read-only badge pills (`AffectsCell`), not as a dropdown. If the screenshot showed a True/False dropdown, it may be in a different CMS edit form not found in this search. No bug confirmed; mark for operator re-screenshot.
- **tag_role** (page 11): `tag_role` is a real, documented field on `pyq_question_topic_tags` with six valid enum values. It is rendered in `ReviewQueueTable.jsx`. The question "how to set tag_role" is a documentation gap, not a code bug.
- **reviewer_status / mention_type using raw IDs** (page 11): These are stored as enum strings, not UUIDs. The display issue is likely the raw token not being humanized (same as UX-EI-1 pattern). Not a separate bug.
