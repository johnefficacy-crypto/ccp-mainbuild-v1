# Document-Readiness Identity/Status Audit — 2026-06-21

**Lane D — D1 — Read-only audit. No runtime code edits. No migrations. No live DB.**

Audited against branch `claude/adoring-bardeen-5rnn1d` (main @ `62d157e`).
Scope: trace document-readiness identity/status across the stack and validate
whether H2 (fix/h2-console-detail-500) chose the right source table.
H2 proposed Option A: `console_detail._documents()` reads `syllabus_documents`,
uses `trust_status=="verified"` as readiness/extracted proxy.

---

## Section 1: Entity Inventory

### 1.1 `document_assets`

| Field | Value |
|---|---|
| Defining migration | `app/supabase/migrations/111_document_assets.sql` |
| Primary key | `id uuid` |
| Status field | `status text` — `('uploaded','processing','processed','failed','archived')` |
| Extraction field | **None.** No `extraction_status` column exists on this table in any migration (confirmed by full scan of all 182 migrations). |
| Exam linkage | **None.** No `exam_id` or `exam_cycle_id` column. Exam identity is stored in `metadata jsonb` (Python-side filter, not a DB column). Column `exam_identity` (migration 152) is a domain-identity ENUM for extractor dispatch, not a FK to `exams`. |
| Other notable columns | `processing_policy`, `scope`, `document_kind`, `structural_format` (mig 152), `source_kind` (mig 153), `sanitized_from_document_id` (mig 153) |
| Scope for EI admin docs | `scope='admin_exam_intelligence'`, `owner_user_id IS NULL`, service-role RLS only |
| Role in pipeline | Storage shell for uploaded PDFs. No per-page extracted text and no exam FK live here. |

**Key finding:** `document_assets` has **no** `exam_id` column and **no** `extraction_status` column.
Confirmed by `admin_exam_intel_documents.py:424`:
```python
# exam_id lives in metadata (document_assets has no exam column), so it is
# filtered in Python rather than via a JSON operator.
```

### 1.2 `syllabus_documents`

| Field | Value |
|---|---|
| Defining migration | `app/supabase/migrations/031_syllabus_evidence_mapping.sql` |
| Primary key | `id uuid` |
| Exam linkage | `exam_id uuid NOT NULL REFERENCES exams(id)`, `exam_cycle_id uuid` (nullable) |
| Status field | `trust_status text` — `('pending','verified','rejected','superseded')` |
| Extraction field | **None.** No `extraction_status` column. |
| Other notable columns | `document_type`, `title`, `source_url`, `storage_path`, `content_hash`, `published_at`, `fetched_at`, `metadata` |
| Role in pipeline | CMS-managed registry of official syllabus documents attached to an exam. `trust_status` is a **human review gate** — an admin marks a document `verified` once its provenance is confirmed. Does NOT reflect whether text has been extracted from the PDF. |

### 1.3 `document_pages`

| Field | Value |
|---|---|
| Defining migration | `app/supabase/migrations/113_document_pages_text_extract.sql` |
| Primary key | `id uuid` |
| Parent FK | `document_id uuid NOT NULL REFERENCES document_assets(id)` |
| Status field | `extraction_status text` — `('extracted','empty','failed')` |
| Other notable columns | `page_number`, `text_content`, `char_count`, `parser_engine`, `parser_version` |
| Role in pipeline | Per-page extracted text rows for PDFs. Created/replaced atomically by `replace_document_pages()` RPC (SECURITY DEFINER, service-role only). This is where real page-level extraction status lives. |

### 1.4 `document_processing_jobs`

| Field | Value |
|---|---|
| Defining migration | `app/supabase/migrations/111_document_assets.sql` (co-defined with `document_assets`) |
| Primary key | `id uuid` |
| Parent FK | `document_id uuid NOT NULL REFERENCES document_assets(id)` |
| Status field | `status text` — `('queued','running','succeeded','failed','needs_review')` |
| Job type field | `job_type text` — `('text_extract','ocr','layout_parse','table_extract','domain_extract')` |
| Other notable columns | `parser_engine`, `parser_version`, `attempt_count`, `started_at`, `finished_at`, `error_code`, `error_message`, `metrics` |
| Extraction signal | For a `job_type='text_extract'` row, `status='succeeded'` means text extraction completed. This is the **canonical text-extraction completion signal** for the document-assets pipeline. |
| Note | One active `text_extract` job per document enforced by partial unique index added in migration 113. |

### 1.5 `library_ocr_jobs`

| Field | Value |
|---|---|
| Defining migration | `app/supabase/migrations/114_library_ocr_jobs.sql` |
| Primary key | `id uuid` |
| Parent FK | `item_id uuid NOT NULL REFERENCES document_assets(id)` |
| Status field | `status text` — `('pending','queued','running','succeeded','failed','skipped','cancelled')` |
| Trigger field | `trigger_reason text` — `('auto_likely_needs_ocr','manual_request','retry')` |
| Other notable columns | `engine`, `pages_total`, `pages_processed`, `error_code`, `error_message` |
| Role in pipeline | OCR job table for personal-library PDFs that likely need OCR after text extraction. Intentionally separate from `document_processing_jobs` (different status vocabulary per migration 114 comment). |
| EI relevance | **Not used by the Exam Intelligence pipeline.** EI documents use `document_processing_jobs`; `library_ocr_jobs` is library-only. |

---

## Section 2: Upload→List→Detail Identity Chain

### 2.1 Admin EI document upload flow (`admin_exam_intel_documents.py`)

```
upload-url      → mints signed Storage URL + inserts document_assets row (status='uploaded')
                  exam_id stored in metadata jsonb (NOT a real DB column)
complete-upload → verifies hash, flips status to 'processing',
                  enqueues text_extract job in document_processing_jobs
                  (job_type='text_extract', status='queued')
GET /{id}       → reads document_assets by id
GET /           → reads document_assets filtered by scope='admin_exam_intelligence'
                  exam_id filter is Python-side via metadata jsonb (NOT .eq("exam_id",...))
link-to-syllabus→ creates/updates syllabus_documents row for the same exam;
                  sets trust_status='pending' (human review gate, NOT extraction status)
```

Key identity separation: `document_assets.id` != `syllabus_documents.id`. They are separate rows linked by the explicit `link-to-syllabus` admin action. A `document_assets` row can exist without any corresponding `syllabus_documents` row.

### 2.2 Console detail — `console_detail.py`

```python
def _documents(sb, exam_id: str) -> list[dict[str, Any]]:
    return _paged(
        sb,
        lambda: sb.table("document_assets").select("id, extraction_status")
        .eq("exam_id", exam_id).order("id"),
        "console_detail.documents",
    )
# app/backend/app/exam_intelligence/console_detail.py:92-98

extracted = sum(1 for r in docs if r.get("extraction_status") == "succeeded")
# app/backend/app/exam_intelligence/console_detail.py:257
```

**Bug confirmed (BUG-EI-2):** `.eq("exam_id", exam_id)` is applied to `document_assets`, which has no `exam_id` column. `.select("id, extraction_status")` selects a column that also does not exist on the table. PostgREST returns an error or empty list, causing the 500 on `GET /console/exams/{id}`.

### 2.3 Workspace readiness — `readiness.py`

```python
q = sb.table("document_assets").select("id, extraction_status, exam_cycle_id").eq("exam_id", exam_id)
# app/backend/app/exam_intelligence/readiness.py:77
```

**Same bug pattern:** `exam_id`, `extraction_status`, and `exam_cycle_id` do not exist on `document_assets`. The `_documents` section in the workspace readiness endpoint is also broken, always returning empty/zero counts.

### 2.4 `syllabus_documents` identity chain

`syllabus_documents` has `exam_id` as a real FK column. The CMS reads and writes it correctly. The `link-to-syllabus` endpoint creates `syllabus_documents` rows with `trust_status='pending'`; a human reviewer later promotes to `trust_status='verified'`. This table is **not** currently used by `console_detail._documents()` or `readiness._documents()` (they query `document_assets` instead, which lacks the needed columns).

---

## Section 3: H2 Validation — Does Extraction Status Live Separately from `trust_status`?

**Verdict: YES — real text-extraction status lives separately from `trust_status`.**

### Evidence

#### 3.1 `trust_status` is a human review gate only

`trust_status` exists on `syllabus_documents` (and `pyq_papers`). It tracks whether a human reviewer has verified the provenance and authenticity of the document. It is forced to `'pending'` at creation and promoted to `'verified'` by a human reviewer. It has no relationship to whether text has been extracted from the PDF.

```
app/backend/app/api/admin_exam_intel_documents.py:450
# Wire storage in; never touch trust_status — it stays in the review pipeline.

app/backend/app/api/admin_exam_intel_documents.py:468
"trust_status": "pending",

app/backend/app/api/admin_exam_intel_cms.py:694
# CMS feeds the review queue — trust_status forced to 'pending'.

app/backend/app/api/admin_exam_intel_cms.py:705
row["trust_status"] = "pending"  # spec §12 #4 — no auto-publish
```

#### 3.2 Real text-extraction status lives in `document_processing_jobs`

Text extraction completion is tracked via `document_processing_jobs` where `job_type='text_extract'` and `status='succeeded'`:

```
app/backend/app/library/text_extract.py:86
    .eq("job_type", "text_extract")

app/backend/app/library/text_extract.py:113
    "job_type": "text_extract",

app/backend/app/library/text_extract.py:420
    extracted_page_count = sum(1 for r in rows if r["extraction_status"] == "extracted")
```

Per-page extraction results live in `document_pages.extraction_status` (`'extracted'|'empty'|'failed'`), the page-level signal written by `replace_document_pages()`.

#### 3.3 The two signals are orthogonal

- `syllabus_documents.trust_status` = "has a human reviewer vouched for this document?"
- `document_processing_jobs.status` (where `job_type='text_extract'`) = "has PDF text been extracted?"

A document can be `trust_status='verified'` with no text extraction ever run, or have extraction completed (`status='succeeded'`) while still at `trust_status='pending'`. No migration and no Python code sets `trust_status` based on extraction completion.

---

## Section 4: Option A Verdict

**Option A undercounts (and is structurally wrong for the intended signal).**

H2 proposed Option A: query `syllabus_documents` by `exam_id`, use `trust_status=="verified"` as readiness/extracted proxy.

### Why Option A undercounts

1. **Wrong signal:** `trust_status='verified'` measures human review approval of document provenance, not text-extraction completion. Option A would count reviewer-approved documents, not documents with extracted text.

2. **Identity gap:** `document_assets` and `syllabus_documents` are separate entities with separate IDs. An admin-EI upload creates a `document_assets` row; it is linked to a `syllabus_documents` row only via the explicit `link-to-syllabus` admin action. An uploaded `document_assets` row not yet linked would be entirely invisible to Option A, even if its text extraction has completed.

3. **No extraction coverage:** Option A does not consult `document_processing_jobs` or `document_pages` at all. It has no way to determine whether text was actually extracted.

### What the correct fix requires (named files only — no edits here)

- `app/backend/app/exam_intelligence/console_detail.py`: Replace `_documents()` to query `document_processing_jobs` for `job_type='text_extract'` and `status='succeeded'`, filtered to documents associated with the exam (via metadata JSONB or a new `exam_id` column added in a future migration).
- `app/backend/app/exam_intelligence/readiness.py`: Same fix for `_documents()`.
- Optional: a new migration adding `exam_id uuid REFERENCES exams(id)` to `document_assets` to enable a proper DB-side filter.

---

## Section 5: Outcome Class and Named Files

**Outcome class: backend-only fix**

The bugs are entirely in backend Python files. The frontend consumes the API response and renders whatever the backend returns. No frontend selector fix is needed.

### Files any future fix would touch

| File | Why |
|---|---|
| `app/backend/app/exam_intelligence/console_detail.py` | `_documents()` at lines 92–98 queries `document_assets` with non-existent `exam_id` and `extraction_status` columns. Lines 257–263 consume the broken result. |
| `app/backend/app/exam_intelligence/readiness.py` | `_documents()` at lines 76–108 uses `.eq("exam_id", exam_id)` and `.select("extraction_status")` on `document_assets` — same missing-column bug. |

A new migration adding `exam_id` to `document_assets` would also be needed if the chosen fix adds that column rather than using metadata-based Python filtering.

---

## Appendix: Grep Evidence Summary

| Claim | File:Line | Finding |
|---|---|---|
| `document_assets` has no `exam_id` col | `admin_exam_intel_documents.py:424` | `# exam_id lives in metadata (document_assets has no exam column)` |
| `document_assets` has no `extraction_status` col | All 182 migration files scanned | Column absent from all migrations |
| Real extraction job signal | `text_extract.py:113` | `"job_type": "text_extract"` inserted into `document_processing_jobs` |
| Extraction job query pattern | `text_extract.py:86` | `.eq("job_type", "text_extract")` |
| `trust_status` = review gate only | `admin_exam_intel_documents.py:450` | `# never touch trust_status — it stays in the review pipeline` |
| `trust_status` forced pending at create | `admin_exam_intel_cms.py:705` | `row["trust_status"] = "pending"` |
| Bug in `console_detail._documents()` | `console_detail.py:95` | `.select("id, extraction_status").eq("exam_id", exam_id)` on `document_assets` |
| Bug in `readiness._documents()` | `readiness.py:77` | `.select("id, extraction_status, exam_cycle_id").eq("exam_id", exam_id)` on `document_assets` |
