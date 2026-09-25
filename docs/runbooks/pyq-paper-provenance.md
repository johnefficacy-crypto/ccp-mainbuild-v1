# Runbook — PYQ paper provenance and the trust gate

This applies to every corpus. A `pyq_papers` row cannot move `pending → verified`
until it passes the provenance gate. The gate matters because a paper's trust
status feeds three things:

- **Snapshot evidence.** `score_snapshots.py:338-346` reads only `trust_status='verified'` papers.
- **Learner paper list.** `exam_intelligence/pyq_papers.py:99` lists only verified papers.
- **Projection.** The projection bridge treats a paper's `trust_status` as the gate it passes (`271_review_pyq_paper_question_count_gate.sql:15-17`).

All paths below are repo-relative. Backend paths are under
`app/backend/app/`; migrations are under `app/supabase/migrations/`.

---

## 1. The gate: `review_pyq_paper`

**Authority:** the PL/pgSQL function `review_pyq_paper`, latest body in
migration `271_review_pyq_paper_question_count_gate.sql`. It replaces 185/186/187.
Later migrations only mention it in comments (`272:141`, `307:265`).

**Reached through:** `POST /api/admin/exam-intelligence-cms/pyq-papers/{paper_id}/review`
(`api/admin_exam_intel_cms.py:1538-1543`). The request body is `PaperReviewBody`:

- `status`: `verified` | `rejected` | `pending`
- `reason`: 8–500 characters

The route requires permission `exam_intelligence.review` (`:57`) and the flag in §5.

**Allowed transitions** (`271:100-109`):

- `pending → verified`
- `pending → rejected`
- `verified → rejected`
- `rejected → pending`

Every other transition raises `transition_not_allowed`. A stale
`p_expected_status` raises `concurrent_modification` (`271:95-98`).

### Step 6 — the provenance checks

Step 6 runs only on `pending → verified`, against the row locked
`FOR UPDATE` (`271:112-181`). Each failed check appends a blocking field to one
list.

| Check | Blocks when | Blocking field | Line |
|---|---|---|---|
| (a) | `source_type` IS NULL or `'unknown'` | `source_type` | `271:116-119` |
| (b) | `source_url` NULL/blank **and** `source_document_id` NULL | `source_url` | `271:121-125` |
| (c) | only if `source_document_id` is set; the `document_assets` row is locked `FOR UPDATE` (`271:130-134`) and checked six ways, listed below | — | `271:130-158` |
| (d) | the paper has no `pyq_questions` row (added by 271; not locked, because concurrent inserts can only add questions) | `no_questions` | `271:160-174` |

The six document checks under (c):

| # | Blocks when | Blocking field |
|---|---|---|
| 1 | the row is missing | `source_document_id_not_found` |
| 2 | `scope != 'admin_exam_intelligence'` | `source_document_id_wrong_scope` |
| 3 | `document_kind != 'pyq_paper'` | `source_document_id_wrong_kind` |
| 4 | `status IN ('failed','archived')` | `source_document_id_bad_status` |
| 5 | `storage_bucket` or `storage_path` is blank | `source_document_id_no_storage` |
| 6 | `metadata.exam_id` is present, non-empty, and differs from the paper's `exam_id` | `source_document_id_exam_mismatch` |

**On failure**, the function raises all blocking fields in one exception
(`271:176-180`), SQLSTATE `P0422`:

```
provenance_incomplete: blocking_fields=<comma-separated list>
```

**Allowed `source_type` values:** `official, memory_based, coaching, community,
aggregator, unknown` (`032_pyq_question_intelligence.sql:30-31`).

**A document does not satisfy (a).** Check (a) runs whatever is attached, so a
paper anchored by a document still needs a real `source_type`.

**Direct `/rpc/` calls hit the same checks.** Check (d) exists because a direct
`/rpc/` call once skipped the Python endpoint's question count. Papers
`b06305ad` and `c82f3e64` were verified empty that way (`271:161-167`). Every
check in this section now lives in the function itself.

---

## 2. `pyq_papers.source_url` is learner-visible

**Correction.** It has been claimed that `source_url` is not learner-visible,
citing `study_os/pyq_explanations.py`. **For `pyq_papers.source_url` that is
false.** This comes up repeatedly, so the evidence is kept here.

- **What `pyq_explanations.py` actually drops.** It removes `source_url` from **`pyq_question_explanations`** rows, not paper rows. Its docstring lists the dropped provenance columns (`study_os/pyq_explanations.py:17-21`). The learner DTO is the `ALLOWED_FIELDS` tuple (`:40-48`). That is a different table's column.
- **The `study_os/update_context.py` hits are a different table again:** `exam_policy_updates.source_url` (`update_context.py:60, 78, 97`).
- **How a paper's `source_url` reaches learners:**
  1. `verified_pyq_papers()` selects `pyq_papers.source_url` and returns it in each paper dict (`exam_intelligence/pyq_papers.py:96`, `:137`).
  2. `exam_intelligence_summary()` puts that list in its payload as `pyq_papers` (`exam_intelligence/status.py:137`, `:171`).
  3. `GET /api/exam-intelligence/exams/{slug}` serves the payload to **any authenticated user** (`api/exam_intelligence.py:143-150`, `Depends(get_current_user)`).
  4. The frontend renders it as an external **"Open"** link (`app/frontend/src/features/exams/ExamIntelligenceTab.jsx:79-88`), in the tab mounted on `pages/ExamDetail.jsx`.

**Consequence:** any URL written to `source_url` on a verified paper is shown to
learners as a clickable link. Do not put coaching-site or third-party URLs
there. Use the document route (§3) to anchor provenance without publishing a
link. A `source_document_id` is never in the learner payload: the select at
`pyq_papers.py:94-96` omits it.

---

## 3. The document route (provenance without a public URL)

Router `api/admin_exam_intel_documents.py`, prefix
`/admin/exam-intelligence-cms/documents` (`:46-49`), mounted under `/api` (`app/backend/server.py:269`, `:386`).
Every step requires permission `exam_intelligence.cms` (`PERM_CMS`,
`admin_exam_intel_cms.py:56`) and the flag in §5.

### 3.1 `POST /api/admin/exam-intelligence-cms/documents/upload-url`

Handler at `admin_exam_intel_documents.py:275`. Request model
`DocUploadUrlRequest` (`:234-250`):

| Field | Type | Notes |
|---|---|---|
| `exam_id` | str, required | Must resolve to `exams` or 422 (`:325-326`). Written to `metadata.exam_id` (`:365-370`). **This is the value checks (c)(6) and the link check compare, so use the paper's own `exam_id`.** |
| `document_kind` | str, required, ≤40 | Must be one of `syllabus, pyq_paper, notification, corrigendum, answer_key` (`:53`, `:281-282`). Use **`pyq_paper`**. |
| `filename` | str, required, ≤255 | Extension must match `mime_type` (`:288-293`). |
| `mime_type` | str, required, ≤120 | Must be in `ACCEPTED_UPLOAD_MIMES`: PDF or DOCX (`:65-71`). |
| `size_bytes` | int ≥1 | Capped at `LIBRARY_MAX_UPLOAD_MB`, default 25 (`:295-296`; `core/config.py:34`). |
| `exam_cycle_id`, `exam_phase_id` | str, optional | Copied into `metadata`. |
| `title` | str, optional, ≤200 | |
| `exam_identity` | str, optional | Must be a `ExamIdentity` value (`:303-310`). Omitted → `unknown` (`:299`). The enum has **no SSC member** (`exam_intelligence/extraction/dispatch.py:23-39`; DB enum `152_extraction_paper_format_scope_fence.sql:22-39`). |
| `structural_format` | str, optional | Inferred from `exam_identity` unless you pass one (`:308-316`). |
| `source_kind` | str, optional | A `SourceKind` value (`:318-322`): `official_archive, official_scan, sanitized_coaching, raw_coaching, sme_authored, crowd_sourced, unknown` (`dispatch.py:90-97`). The gate does **not** read this. |
| `sanitized_from_document_id` | str, optional | Must resolve (`:328-331`). |
| `processing_policy` | str, optional | One of `store_only, extract_text, deep_parse, ocr_required` (`:77`). The PDF default is `extract_text` (`:95-97`). |

**What it writes:** a `document_assets` row with (`:344-372`):

- `scope='admin_exam_intelligence'`
- `visibility='admin_only'`
- `owner_user_id=NULL`
- `status='uploaded'`
- a placeholder `content_hash`

It also writes an audit row (`:374-386`).

**Response** (`:387-394`): `document_id`, `processing_policy`,
`storage_bucket`, `storage_path`, `upload_url`, `upload_token`.

### 3.2 `PUT <upload_url>`

Send the file bytes to the signed Storage URL returned in 3.1. The URL is minted
by `create_signed_upload_url` (`:336`). This step goes to Supabase Storage, not
to the API.

### 3.3 `POST /api/admin/exam-intelligence-cms/documents/complete-upload`

Handler at `:397`. Request model `DocCompleteUploadRequest` (`:253-258`):

| Field | Type | Notes |
|---|---|---|
| `document_id` | str, required | Must be an admin-scope asset, or 404 (`:404-406`). |
| `client_hash` | str, optional, ≤128 | Used only if the server cannot read the object back (`:433-441`). |
| `processing_policy` | str, optional | A late override, validated the same way as in 3.1 (`:414-417`). |

**Allowed state:** completes only from `status='uploaded'`. Any other status
returns 409 with a named error (`:418-431`).

**What it does:**

1. Computes the real hash from the stored bytes (`:433-436`).
2. With `store_only`: sets `status='processed'` directly, with no extraction (`:443-483`).
3. Otherwise: sets `processing`, enqueues `text_extract`, and runs it synchronously (`:485-543`).

For a paper whose questions are already loaded, **`store_only` is the
provenance-only path**.

Coaching sources (`raw_coaching`) are outside `ELIGIBLE_SOURCE_KINDS_V1`
(`dispatch.py:100-105`), so the structured extraction pipeline refuses them
(`exam_intelligence/extraction/pipeline.py:74`, `:361`).

### 3.4 `POST /api/admin/exam-intelligence-cms/documents/{document_id}/link-to-pyq-paper`

Handler at `:691`. Request model `LinkPyqPaperRequest` (`:267-269`):

| Field | Type |
|---|---|
| `reason` | str, 8–500 characters |
| `pyq_paper_id` | str, required |

**What it checks.** It re-runs the **six document checks from §1 (c)**, not
(a), (b) or (d):

- **Python pre-check** (`:712-728`). `_load_admin_asset` enforces scope (`:169-173`); the handler then checks kind, status, storage and exam match. A failure returns 422 `document_not_linkable` with `blocking_fields`.
- **The same six again under row locks** in `cms_link_document_to_pyq_paper`, latest body `189_cms_provenance_doc_lock.sql:143-210`, grants in `190`.

**It demotes a verified paper.** If the paper is `verified`, linking sets it
back to `pending` in the same transaction as the link
(`189_cms_provenance_doc_lock.sql:212-218`).

- The `p_was_verified` flag is read in Python just before the RPC call (`admin_exam_intel_documents.py:730`).
- The audit row records `demoted_from_verified` (`189:226-242`).

After linking, the paper must go through §1 again.

`POST /api/admin/exam-intelligence-cms/pyq-papers/{paper_id}/set-provenance`
(`admin_exam_intel_cms.py:1234-1245`) works the same way. It edits
`source_type` / `source_url` / `source_document_id`, runs the same document
checks, and also demotes a verified paper.

### 3.5 Then verify

`POST /api/admin/exam-intelligence-cms/pyq-papers/{paper_id}/review` with
`{"status": "verified", "reason": "..."}` (§1).

With a linked document, (b) and (c) pass, and (d) passes if questions exist.
**(a) still needs `source_type` set to something other than `unknown`.**

---

## 4. Order of operations for a new corpus

1. Load papers and questions. Papers start at `trust_status='pending'`.
2. Decide the anchor:
   - **Official, public source:** use `source_url`. It will be shown to learners, so it must be a URL you are willing to publish (§2).
   - **Anything else:** use the document route (§3).
3. Set `source_type` to a real value (§1, check a).
4. Upload, complete and link (§3.1–3.4), one document per paper. `exam_id` must match the paper's.
5. Review each paper `pending → verified` (§1).
6. Review questions and tags, then project per paper with `POST /api/admin/mocks/pyq-papers/{paper_id}/projection/sync` (`api/admin_mocks.py:461`).
7. **Think before verifying a descriptive-only paper.** Snapshot compute does not filter by `question_type` (`exam_intelligence/score_snapshots.py:406-411`), so a verified descriptive paper's tagged questions enter coverage evidence. This matters when no descriptive practice surface exists for that exam.

---

## 5. The feature flag

**Every route** in `api/admin_exam_intel_documents.py` depends on
`_flag_enabled`: `upload-url`, `complete-upload`, `GET /{id}`, `GET /{id}/pages`,
`GET /`, `link-to-syllabus`, `link-to-pyq-paper` and `archive` (`:279, 401,
568, 587, 616, 639, 696, 781`). It is imported from
`admin_exam_intel_cms.py:32`. The paper review and set-provenance routes use the
same dependency (`admin_exam_intel_cms.py:1239`, `:1543`).

- **Flag:** setting `ADMIN_STUDY_OS_ENABLED`, read from the env var of the same name. It is true for `1/true/yes/on` and **defaults to off** (`"0"`) (`core/config.py:27`).
- **When off:** `_flag_enabled` raises **HTTP 404** `"admin.study_os.enabled is off"` (`admin_exam_intel_cms.py:68-73`). The routes look absent rather than forbidden. A 404 from any route here on a fresh environment means check the flag first.

---

## Related

- `docs/status/corpus-readiness-2026-09-25.md` — RBI Grade B state and the SSC CGL decision that uses this runbook.
- `docs/status/Regulatory-corpus-decision-provenance-2026-09-06.md` — the question-level review audit trail. The paper gate audits itself; the question review route does not.
- `scripts/corpus_readiness_report.py:27-47` — why the generated readiness report reads the gate's verdict and never computes it.
