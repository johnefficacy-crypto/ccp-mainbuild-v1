# Mixed-Format PDF Extraction Gate — J3 (extraction-architecture sub-item)

- Document type: J3 implementation contract — mixed-format (page-level layout) PDF extraction architecture
- Status: **AMENDED TO MATCH APPROVED RESOLUTIONS — OPERATOR SIGN-OFF PENDING.** Body reconciled with docs/status/J3-OD-Resolutions-Locked-2026-07-02.md §8 (2026-07-02). Implementation remains BLOCKED until explicit operator approval is recorded on the PR.
- Date: 2026-07-02
- Parent track: `J3 — schema/domain redesign` (checklist rows "Mixed-format PDF support DEFERRED — EXTRACTION ARCHITECTURE" and "mixed-format PDF extraction" under the J3 row)
- Authority / read order (CLAUDE.md): `graphify-out/GRAPH_REPORT.md`; `docs/00-ai-context.md`; `AGENTS.md`; `docs/architecture/domain-model.md`; this gate
- Prerequisite context: v1 extraction pipeline (`app/backend/app/exam_intelligence/extraction/`), scope-fence migration 152, `document_assets` migration 111, extraction-run migration 149, source-kind gate migrations 153/154
- Blocks: any implementation PR for page-level / page-range format classification. Does NOT block other J3 sub-items (competition metrics, applied-vs-appeared counts, coverage scoring), which each carry their own contract.

---

## How to use this document

This gate **reconciles the existing extraction implementation** — it does not design from scratch. Every section states a LOCKED decision or an exact specification. The body has been reconciled with the approved resolutions in `docs/status/J3-OD-Resolutions-Locked-2026-07-02.md` §8; the operator decisions below are RESOLVED (OD-1 = B, OD-2 = B1, OD-3 = N/A-now).

Implementation is **PR 3** in `docs/status/J3-Implementation-Checklist-2026-07-02.md` — independent, and may run in parallel with PR 1/PR 2. **Dispatch is blocked ONLY on explicit operator sign-off recorded on the PR.**

**Serial delivery rule (locked):** this work touches the extraction dispatch/pipeline and the `document_assets` classification surface — one owner's sequential work, no fan-out.

**Invariants carried from CLAUDE.md (non-negotiable, apply to every option below):**
- **No new AI writes.** No Neo4j/Pinecone/LangGraph/pgvector/LLM adapter, and no unreviewed AI-authored writes to user-facing content. Any per-page classifier is deterministic/heuristic (or admin-driven) and its *output is a routing decision only* — never a user-facing verdict.
- **Verified-only reads.** All extracted questions remain gated by the existing `pyq_questions` review lifecycle (`reviewer_status='pending'` on create; user-facing reads filter `reviewer_status='verified'`). This gate must not open any path that writes verified/user-facing content directly.
- **Determinism > Heuristics; Trust > Speed; Control > Automation.** Rejection-with-a-clear-message is preferred over silently mis-extracting a mixed file.
- `public.exams` vs `public.recruitments` canonicity is untouched here — extraction operates on `document_assets` → `pyq_papers`/`pyq_questions` (Study OS / exam-intelligence side), never on recruitment notifications.

---

## Section 0 — Actual implementation baseline (one format per document)

### 0.1 Classification model (migration 152, `document_assets`)

- `document_assets.structural_format` is a **single** `document_structural_format` ENUM column (`mcq_bilingual_two_column`, `mcq_monolingual_single`, `essay_long_form`, `mixed_objective_subjective`, `technical_with_figures`, `vernacular_non_devanagari`, `unknown`), `NOT NULL DEFAULT 'unknown'`.
- `document_assets.exam_identity` is a **single** `document_exam_identity` ENUM column.
- `document_assets.document_kind` (migration 111) and per-document `source_kind` (migrations 153/154) are also single-valued.
- **There is exactly one `(structural_format, exam_identity, source_kind, document_kind)` tuple per document.** Nothing today expresses "pages 1–20 are MCQ, pages 21–40 are essay."
- Note the existing enum value `mixed_objective_subjective`. This is **NOT** page-level mixing — it is a whole-document label for a homogeneous "blended MCQ + short-answer" *layout tier* (Tier 2, not v1-eligible). It does not model "different formats on different page ranges." This gate must not conflate the two.

### 0.2 Dispatch (`extraction/dispatch.py`)

- `infer_format_from_identity` and `EXAM_TO_FORMAT_DEFAULT` map one identity → one format.
- `ELIGIBLE_FORMATS_V1 = {mcq_bilingual_two_column}`; `is_extractable_by_v1(format)` is a document-level boolean.
- `ELIGIBLE_SOURCE_KINDS_V1` / `is_source_eligible_v1` — document-level source gate.

### 0.3 Pipeline (`extraction/pipeline.py`)

- `extract(pdf_bytes, document_id, pages=None)` fetches a single `_DocumentAssetsRow`, then runs a **document-level scope fence** before any OCR:
  - `structural_format == 'unknown'` → `ExtractionRequiresClassificationError`
  - `not is_extractable_by_v1(...)` → `ExtractionNotSupportedError`
  - `not is_source_eligible_v1(...)` → `ExtractionRequiresCleanInputError`
  - `document_kind not in {'pyq_paper'}` → `ExtractionWrongDocumentKindError`
- Page selection is `allowed_pages_for(document_id, total_pages)` — a corpus-specific hardcoded list or the odd-pages-3+ fallback. This is a page *filter*, but every selected page is processed **with the same single format's** column/segmentation strategy (`_detect_columns_robust`, `_process_page_words`). There is **no per-page format branch**.
- `EXTRACTOR_VERSION = "0.2.0"`; no DB writes occur in this module.

### 0.4 Writer + review lifecycle (`extraction/writer.py`)

- All writes go through `admin_exam_intel_cms.create_pyq_question()`, which forces `reviewer_status='pending'` and writes the audit log. Bypass is forbidden (module docstring).
- Dry-run mode is default; live mode requires `--confirm`. Idempotency + fuzzy dedup applied per row.
- Rows carry `source_document_id`, `source_page`, `source_regions`, `extractor_version`, `extraction_run_id`.

### 0.5 Where page-level classification would hook in

1. **Data model:** a per-page (or per-range) format assignment that `document_assets`'s single `structural_format` cannot currently hold.
2. **Dispatch:** `is_extractable_by_v1` would need a *per-segment* answer, not a per-document one.
3. **Pipeline:** `extract()`'s scope fence and `allowed_pages_for` would need to iterate segments, dispatch the right strategy per segment, and account eligible vs. ineligible pages separately in `pages_processed` / `pages_skipped` / `errors`.
4. **Writer/lifecycle:** unchanged in principle — every extracted question still flows through `create_pyq_question` → `pending` → review. No new write path.

---

## Section A — Gaps this gate addresses

| # | Gap | Consequence today |
|---|---|---|
| G-1 | One format per document | A genuinely mixed PDF (e.g. Prelims MCQ section + descriptive section) can only be given one label. |
| G-2 | Silent mis-extraction risk | If a mixed file is labelled `mcq_bilingual_two_column`, v1 will run its two-column MCQ strategy over the non-MCQ pages and emit garbage candidates into review. |
| G-3 | No clear rejection contract | There is no explicit, documented "this file is mixed and unsupported — do X" path or user/admin message. |
| G-4 | No page-range provenance | Even if handled, there is no place to record which page range produced which questions beyond per-row `source_page`. |

---

## Section B — Locked scope decisions

| ID | Decision |
|---|---|
| PD-1 | **Trigger definition (LOCKED).** "Mixed-format" means a single uploaded PDF whose pages do not all share one `structural_format` (e.g. an MCQ objective section followed by a descriptive/essay section). It is distinct from the homogeneous `mixed_objective_subjective` enum label (§0.1). |
| PD-2 | **v1 eligibility is unchanged (LOCKED).** Whatever the chosen approach, only `mcq_bilingual_two_column` segments are v1-extractable. Non-MCQ segments are out of scope for the current extractor and MUST NOT be extracted by v1 into `pyq_questions`. |
| PD-3 | **No new AI/heuristic verdict path (LOCKED).** A per-page format signal (if adopted) is a deterministic routing hint or an **admin-entered** classification, not an AI-authored user-facing write. It never sets `reviewer_status`. |
| PD-4 | **Lifecycle unchanged (LOCKED).** Every extracted question continues through `create_pyq_question` → `reviewer_status='pending'` → review → `verified`. No verified/user-facing content is written by this feature. |
| PD-5 | **Provenance (LOCKED).** Whichever approach is chosen, the emitted questions and/or the extraction-run metadata must record which page range they came from (reuse `source_page`/`source_regions`; extend run metadata if ranges are used). |

---

## Section C — OPERATOR DECISIONS — RESOLVED (pending sign-off)

The checklist framed this as an either/or: **(A) support page-range classification** OR **(B) reject mixed files clearly and document a temporary workaround.** The resolutions in `docs/status/J3-OD-Resolutions-Locked-2026-07-02.md` §8 select **Option B with B1 admin-declared detection only**. Options A and B are retained below for context; the resolved decisions are authoritative.

### Option A — Page-range format classification (full support)

Add a per-range format model, dispatch the extractor per segment, and skip/route ineligible segments.

- **Data model (LOCKED shape if A is chosen):** a new child table rather than mutating the single-valued `document_assets.structural_format` (keeps migration 152's column and its scope-fence semantics intact and backward-compatible):

  ```sql
  create table public.document_format_segments (
    id uuid primary key default gen_random_uuid(),
    document_id uuid not null references public.document_assets(id) on delete cascade,
    page_start int not null check (page_start >= 1),
    page_end   int not null check (page_end >= page_start),
    structural_format document_structural_format not null,
    exam_identity document_exam_identity,          -- optional per-segment override
    source_kind text,                              -- optional per-segment override
    assigned_by uuid references public.profiles(id) on delete set null,  -- admin classifier (deterministic/admin, not AI)
    created_at timestamptz not null default now(),
    -- ranges within one document must not overlap (enforced by EXCLUDE / trigger; see below)
    unique (document_id, page_start, page_end)
  );
  ```
  - Non-overlap of `[page_start, page_end]` per document enforced via a GiST `EXCLUDE` constraint (`int4range`) or a validation trigger. Gaps (unclassified pages) are treated as `unknown` → not extracted.
  - `document_assets.structural_format` remains the **document-level default / fallback**; when no segment rows exist, behavior is exactly today's (full backward compatibility — no backfill required, decision below).
- **Dispatch:** `extract()` builds an ordered segment map (segment rows if present, else the single document-level format). For each selected page it looks up its segment's `structural_format`; only `mcq_bilingual_two_column` pages run the v1 strategy. Ineligible-format pages go to `pages_skipped` with a reason (`format_not_v1_eligible`), never to OCR-as-MCQ. `structural_format='unknown'` on a covering segment raises the existing `ExtractionRequiresClassificationError` scoped to that range.
- **Review lifecycle:** unchanged — extracted MCQ questions still go through `create_pyq_question` → `pending`. Per-segment provenance recorded via `source_page`/`source_regions` plus an `extraction_runs.metadata.segment_map` snapshot.
- **RLS:** `document_format_segments` is admin/service-role scope only (mirror `document_assets` admin pattern: no end-user policy match; `for all to service_role`). Every new table needs an RLS policy — verify with `SELECT * FROM pg_policies WHERE tablename='document_format_segments'` before marking complete.
- **Migration:** one forward migration (next free slot at implementation time — do not hardcode; ≥ current max, verify against landed migrations) creating the table, the non-overlap constraint, indexes (`document_id`, `(document_id, page_start)`), RLS, and `notify pgrst`. **No backfill** — absence of segment rows preserves today's single-format path.
- **Cost:** classifier UI/logic, segment-aware dispatch, per-segment scope-fence errors, tests, admin surface to author ranges. Larger, and it commits us to per-segment maintenance.

### Option B — Explicit clear rejection + documented temporary workaround (SELECTED — OD-1)

Keep one format per document. Detect that a file is mixed and **reject it loudly** with an actionable message; document the manual workaround (split the PDF into homogeneous per-format sub-documents, upload each with its own `structural_format`).

- **Detection (RESOLVED per OD-2 — B1 admin-declared ONLY):**
  - **B1 (admin-declared, selected):** a validated explicit flag an admin sets when they know a file is mixed — `document_assets.metadata.mixed_format=true`. No detector required.
  - **B2 (heuristic pre-check) — explicitly deferred, NOT part of the locked scope.** A deterministic sampling pre-pass may be revisited in a later gate; do not add it now.
- **New scope-fence error (LOCKED shape):** add `ExtractionMixedFormatError(RuntimeError)` in `pipeline.py`, raised in the scope-fence block before any OCR, with a message that (a) states the file is declared mixed-format, (b) instructs the admin to split it into homogeneous sub-documents (one `structural_format` each) or reclassify, and (c) links the workaround SOP doc.
- **Temporary workaround (documented):** admin splits the source PDF at the format boundary and uploads N homogeneous `document_assets` rows, each extracted independently by the existing pipeline. This is captured in an engineering SOP (e.g. `docs/engineering/mixed-format-pdf-workaround-v1.md`) and referenced by the error message.
- **Review lifecycle:** untouched.
- **Migration:** none required for B1 via `metadata` (JSONB already exists) — unless a DB constraint is chosen for validating the flag (then RLS re-verify).
- **Cost:** small, reversible, honors Trust > Speed / Determinism > Heuristics. Does not foreclose Option A later (segments can be added when the descriptive-format extractor tiers land).

### Resolved path (per OD-1/OD-2)

**Option B (explicit clear rejection + documented workaround), with B1 admin-declared detection ONLY.** Rationale:
- v1 only extracts `mcq_bilingual_two_column` (PD-2). Until the Tier-2/Tier-3 extractors for essay/technical/vernacular formats exist, per-range classification would still route every non-MCQ segment to "skip" — Option A's extra machinery buys **no additional extracted content today**, only maintenance surface and mis-extraction risk.
- Option B closes G-2/G-3 immediately (no silent garbage into review), is a small deterministic change, and is forward-compatible: `document_format_segments` (Option A) can be introduced in a later gate once a non-MCQ extractor is contracted.
- Detection is **B1 admin-declared only**: a validated `document_assets.metadata.mixed_format=true` flag. **B2 heuristic detection is explicitly deferred** and is not part of the recommended or implemented path.

**OPERATOR DECISION — OD-1 (RESOLVED):** **Option B** — reject mixed PDFs loudly and document the split/re-upload workaround. (v1 applies one two-column MCQ strategy to every selected page and supports only `pyq_paper`; page-range infrastructure would not extract non-MCQ sections anyway.)
**OPERATOR DECISION — OD-2 (RESOLVED):** **B1 admin-declared** detection via validated `document_assets.metadata.mixed_format=true`. Do **not** add B2 heuristic detection yet.
**OPERATOR DECISION — OD-3 (RESOLVED):** Not applicable now. Recorded: a later Option A must use the proposed `document_format_segments` child table with **no backfill**.

**Required behavior:**

```text
mixed flag
  → ExtractionMixedFormatError before OCR
  → zero question writes
  → error links to the split-and-reupload SOP (docs/engineering/mixed-format-pdf-workaround-v1.md)
```

No migration required for the metadata approach (unless metadata validation needs a DB constraint). Create the SOP doc (`docs/engineering/mixed-format-pdf-workaround-v1.md`).

---

## Section D — Migration / RLS / reviewer lifecycle summary

| Approach | Migration | RLS | Reviewer lifecycle |
|---|---|---|---|
| **B1 metadata flag (SELECTED)** | None (reuse `document_assets.metadata` JSONB) — unless a DB constraint is chosen for the flag (then re-verify policies) | Unchanged (existing `document_assets` policies) | Unchanged — `create_pyq_question` → `pending` → verified |
| A (deferred; recorded for later per OD-3) | New `document_format_segments` child table (+ non-overlap constraint, indexes, `notify pgrst`); next free slot, verify number at impl time; **NO backfill** | New admin/service-role-only policy; verify via `pg_policies` before complete | Unchanged |
| B2 (heuristic) — deferred, out of scope | — | — | — |

Migration discipline: migrations immutable once merged; every new table needs an RLS policy; do not mark live/operator steps complete from code inspection alone — use `OPERATOR PENDING` / `VERIFY DB` until live proof is captured.

---

## Section E — Acceptance tests

Locked scope (Option B, B1 only):

```
[ ] a homogeneous mcq_bilingual_two_column document extracts exactly as today (no regression)
[ ] all extracted questions land as reviewer_status='pending' via create_pyq_question (no bypass)
[ ] no user-facing/verified write occurs from this feature (verified-only invariant)
[ ] document_kind != 'pyq_paper' still rejected (ExtractionWrongDocumentKindError)
[ ] a file with validated document_assets.metadata.mixed_format=true raises ExtractionMixedFormatError in the extraction pipeline scope fence BEFORE any OCR
[ ] no pyq_questions rows are created for a rejected mixed file (loud failure, zero writes)
[ ] the error message names the split-and-reupload workaround and links the SOP doc (docs/engineering/mixed-format-pdf-workaround-v1.md)
[ ] the admin-declared mixed flag reliably triggers rejection (declaration control works end to end)
[ ] splitting into homogeneous sub-documents lets each extract independently (workaround verified)
```

No B2 heuristic tests — B2 is deferred (OD-2). Option A tests (segment table, non-overlap constraint, segment-aware dispatch) are deferred with Option A (OD-3 N/A-now); recorded for later: Option A would use a `document_format_segments` child table with a non-overlap constraint and **no backfill**.

---

## Section F — Files to change (PR 3, locked scope: Option B + B1)

| File | Change |
|---|---|
| `app/backend/app/exam_intelligence/extraction/pipeline.py` | add `ExtractionMixedFormatError` + scope-fence guard (validated `document_assets.metadata.mixed_format=true`) raised before any OCR; error message links the SOP doc |
| admin classification surface (document_assets admin UI) | mixed-format declare control (admin sets the validated flag) |
| `docs/engineering/mixed-format-pdf-workaround-v1.md` | **create in PR 3** — the temporary split-and-reupload workaround SOP referenced by the error message |
| backend tests | Section E (locked-scope list) |
| `app/supabase/migrations/<next>_*.sql` | none — unless a DB constraint is chosen for validating the flag |
| `docs/status/career-copilot-checklist.md` | flip the two mixed-format rows from DEFERRED to the implemented status |

Deferred (not in PR 3): B2 heuristic helper in `dispatch.py` (OD-2); Option A `document_format_segments` table, segment-aware dispatch, and run-metadata segment_map (OD-3 N/A-now — recorded: child table with non-overlap constraint, no backfill).

---

## Appendix A — Code / evidence index

- `app/supabase/migrations/152_extraction_paper_format_scope_fence.sql:6–49` — single `structural_format` + `exam_identity` ENUM columns on `document_assets`; `mixed_objective_subjective` is a whole-document tier label, not page-level mixing.
- `app/supabase/migrations/111_document_assets.sql:9–55, 73–148` — `document_assets` schema, single `document_kind`, admin/service-role RLS pattern; `document_processing_jobs` scaffold (incl. `layout_parse`, `needs_review` status).
- `app/supabase/migrations/153_…`, `154_…` — document-level `source_kind` gate + archive/SME additions.
- `app/supabase/migrations/149_exam_intelligence_extraction_runs.sql` — extraction run rows + confidence constraints + metadata home for a segment_map / dry_run_rows.
- `app/backend/app/exam_intelligence/extraction/dispatch.py:13–124` — `StructuralFormat`/`ExamIdentity` enums, `EXAM_TO_FORMAT_DEFAULT` (one format per identity), `ELIGIBLE_FORMATS_V1 = {mcq_bilingual_two_column}`, document-level `is_extractable_by_v1` / `is_source_eligible_v1`.
- `app/backend/app/exam_intelligence/extraction/pipeline.py:64–90, 137–144, 265–321` — scope-fence error types, `allowed_pages_for` (page filter, single strategy), document-level scope fence before OCR.
- `app/backend/app/exam_intelligence/extraction/writer.py:1–92, 124–258` — all writes via `create_pyq_question` forcing `reviewer_status='pending'`; provenance fields; dry-run default.
- `docs/status/career-copilot-checklist.md:234, 236, 283` — J3 row and the "Mixed-format PDF support — DEFERRED — EXTRACTION ARCHITECTURE" either/or scope.

---

*Status: AMENDED TO MATCH APPROVED RESOLUTIONS — OPERATOR SIGN-OFF PENDING. Body reconciled with docs/status/J3-OD-Resolutions-Locked-2026-07-02.md §8 (2026-07-02); resolutions select Option B (explicit clear rejection + documented workaround) with B1 admin-declared detection (`document_assets.metadata.mixed_format=true`), given v1 extracts only `mcq_bilingual_two_column`; Option A (page-range `document_format_segments`, no backfill) deferred to a later gate once a non-MCQ extractor tier is contracted. Resolved: OD-1 = B, OD-2 = B1, OD-3 = N/A-now (later Option A uses `document_format_segments` with no backfill). Implementation per docs/status/J3-Implementation-Checklist-2026-07-02.md PR 3 (independent, may run parallel to PR 1/2); dispatch remains BLOCKED until explicit operator approval is recorded on the PR.*
