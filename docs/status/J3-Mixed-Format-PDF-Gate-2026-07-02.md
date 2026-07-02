# Mixed-Format PDF Extraction Gate — J3 (extraction-architecture sub-item)

- Document type: J3 implementation contract — mixed-format (page-level layout) PDF extraction architecture
- Status: **DRAFT — OPERATOR APPROVAL REQUIRED**
- Date: 2026-07-02
- Parent track: `J3 — schema/domain redesign` (checklist rows "Mixed-format PDF support DEFERRED — EXTRACTION ARCHITECTURE" and "mixed-format PDF extraction" under the J3 row)
- Authority / read order (CLAUDE.md): `graphify-out/GRAPH_REPORT.md`; `docs/00-ai-context.md`; `AGENTS.md`; `docs/architecture/domain-model.md`; this gate
- Prerequisite context: v1 extraction pipeline (`app/backend/app/exam_intelligence/extraction/`), scope-fence migration 152, `document_assets` migration 111, extraction-run migration 149, source-kind gate migrations 153/154
- Blocks: any implementation PR for page-level / page-range format classification. Does NOT block other J3 sub-items (competition metrics, applied-vs-appeared counts, coverage scoring), which each carry their own contract.

---

## How to use this document

This gate **reconciles the existing extraction implementation** — it does not design from scratch. Every section states a LOCKED decision or an exact specification. Items marked **OPERATOR DECISION REQUIRED** must be resolved by operator approval and not guessed.

**No implementation PR may be dispatched until this document is OPERATOR APPROVED.**

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

## Section C — OPERATOR DECISION REQUIRED (the either/or)

The checklist frames this as an either/or: **(A) support page-range classification** OR **(B) reject mixed files clearly and document a temporary workaround.** This gate presents both and a recommendation. **The operator must select one before any implementation PR.**

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

### Option B — Explicit clear rejection + documented temporary workaround (RECOMMENDED)

Keep one format per document. Detect that a file is mixed and **reject it loudly** with an actionable message; document the manual workaround (split the PDF into homogeneous per-format sub-documents, upload each with its own `structural_format`).

- **Detection (deterministic, no AI):** a document-level guard. Two acceptable mechanisms (operator picks one at implementation; both deterministic):
  - **B1 (admin-declared):** an explicit boolean/flag an admin sets when they know a file is mixed (e.g. `document_assets.metadata.mixed_format=true`, or reuse `structural_format='unknown'` to force classification). No detector required.
  - **B2 (heuristic pre-check):** a deterministic sampling pre-pass (e.g. page-level column/word-density signature already available from `layout.detect_columns`) that flags inconsistency across sampled pages. Its output only *rejects*; it never labels or extracts.
- **New scope-fence error (LOCKED shape if B is chosen):** add `ExtractionMixedFormatError(RuntimeError)` in `pipeline.py`, raised in the scope-fence block before OCR, with a message that (a) states the file appears to contain multiple formats, (b) instructs the admin to split it into homogeneous sub-documents (one `structural_format` each) or reclassify, and (c) links the workaround SOP doc.
- **Temporary workaround (documented):** admin splits the source PDF at the format boundary and uploads N homogeneous `document_assets` rows, each extracted independently by the existing pipeline. This is captured in an engineering SOP (e.g. `docs/engineering/mixed-format-pdf-workaround-v1.md`) and referenced by the error message.
- **Review lifecycle:** untouched.
- **Migration:** none required for B1 via `metadata` (JSONB already exists) — or a tiny nullable flag column if the operator prefers a typed field (then RLS re-verify). B2 requires no schema change.
- **Cost:** small, reversible, honors Trust > Speed / Determinism > Heuristics. Does not foreclose Option A later (segments can be added when the descriptive-format extractor tiers land).

### Recommendation

**Adopt Option B (explicit clear rejection + documented workaround) now.** Rationale:
- v1 only extracts `mcq_bilingual_two_column` (PD-2). Until the Tier-2/Tier-3 extractors for essay/technical/vernacular formats exist, per-range classification would still route every non-MCQ segment to "skip" — Option A's extra machinery buys **no additional extracted content today**, only maintenance surface and mis-extraction risk.
- Option B closes G-2/G-3 immediately (no silent garbage into review), is a small deterministic change, and is forward-compatible: `document_format_segments` (Option A) can be introduced in a later gate once a non-MCQ extractor is contracted.
- Prefer **B2 with a B1 override** phrasing at implementation only if the operator wants automatic detection; otherwise **B1** (admin-declared) is the lowest-risk, fully deterministic default.

**OPERATOR DECISION REQUIRED — OD-1:** choose **Option A** (build page-range classification now) or **Option B** (reject + workaround; recommended).
**OPERATOR DECISION REQUIRED — OD-2 (only if B):** choose detection mechanism **B1 (admin-declared)** vs **B2 (deterministic heuristic pre-check)**. Recommendation: B1 default, B2 optional.
**OPERATOR DECISION REQUIRED — OD-3 (only if A):** confirm the child-table approach (`document_format_segments`) vs. any alternative, and confirm **no backfill** (existing docs keep single-format behavior).

---

## Section D — Migration / RLS / reviewer lifecycle summary

| Approach | Migration | RLS | Reviewer lifecycle |
|---|---|---|---|
| A | New `document_format_segments` table (+ non-overlap constraint, indexes, `notify pgrst`); next free slot, verify number at impl time; **no backfill** | New admin/service-role-only policy; verify via `pg_policies` before complete | Unchanged — `create_pyq_question` → `pending` → verified |
| B1 (metadata flag) | None (reuse `document_assets.metadata` JSONB) | Unchanged (existing `document_assets` policies) | Unchanged |
| B1 (typed column) | Small nullable `boolean` column on `document_assets` | Re-verify `document_assets` policies still cover it | Unchanged |
| B2 (heuristic) | None | Unchanged | Unchanged |

Migration discipline: migrations immutable once merged; every new table needs an RLS policy; do not mark live/operator steps complete from code inspection alone — use `OPERATOR PENDING` / `VERIFY DB` until live proof is captured.

---

## Section E — Acceptance tests

### E.1 Common (both options)
```
[ ] a homogeneous mcq_bilingual_two_column document extracts exactly as today (no regression)
[ ] all extracted questions land as reviewer_status='pending' via create_pyq_question (no bypass)
[ ] no user-facing/verified write occurs from this feature (verified-only invariant)
[ ] document_kind != 'pyq_paper' still rejected (ExtractionWrongDocumentKindError)
```

### E.2 If Option A (page-range)
```
[ ] overlapping segments rejected by the non-overlap constraint
[ ] a document with segments {pp1-20 mcq_bilingual_two_column, pp21-40 essay_long_form} extracts ONLY pp1-20 as MCQ; pp21-40 recorded in pages_skipped with reason format_not_v1_eligible
[ ] a segment with structural_format='unknown' raises classification-required scoped to its range
[ ] a document with NO segment rows behaves exactly as the single-format path (backward compat)
[ ] extraction_runs.metadata records the segment_map used
[ ] pg_policies shows document_format_segments is service-role/admin only (no end-user read)
[ ] per-question provenance (source_page/source_regions) is correct for the extracted segment
```

### E.3 If Option B (reject + workaround)
```
[ ] a file declared/detected as mixed raises ExtractionMixedFormatError BEFORE any OCR
[ ] the error message names the split-and-reupload workaround and links the SOP doc
[ ] no pyq_questions rows are created for a rejected mixed file (loud failure, no partial garbage)
[ ] (B1) admin-declared mixed flag reliably triggers rejection
[ ] (B2) deterministic pre-check flags an actually-mixed sample and does NOT flag a homogeneous file (no false-positive on the v1 corpus fixtures)
[ ] splitting into homogeneous sub-documents lets each extract independently (workaround verified)
```

---

## Section F — Files to change (on approval)

| File | Change (A) | Change (B) |
|---|---|---|
| `app/supabase/migrations/<next>_*.sql` | new `document_format_segments` table + non-overlap constraint + indexes + RLS + `notify pgrst` | none (B1 metadata / B2) or small nullable flag column |
| `app/backend/app/exam_intelligence/extraction/dispatch.py` | per-segment eligibility resolution | (B2) deterministic mixed-format signature helper |
| `app/backend/app/exam_intelligence/extraction/pipeline.py` | segment-aware page dispatch; per-segment scope-fence errors; `pages_skipped` reasons | add `ExtractionMixedFormatError` + scope-fence guard before OCR |
| `app/backend/app/exam_intelligence/extraction/run.py` / writer | record segment_map in run metadata | none (writer unchanged) |
| admin classification surface (document_assets admin UI) | segment-range authoring UI | (B1) mixed-format declare control |
| `docs/engineering/mixed-format-pdf-workaround-v1.md` | reference note | **create** — the temporary workaround SOP (required for B) |
| backend tests | Section E.2 | Section E.3 |
| `docs/status/career-copilot-checklist.md` | flip the two mixed-format rows from DEFERRED to the implemented status | same |

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

*Status: DRAFT — OPERATOR APPROVAL REQUIRED. Recommendation: Option B (explicit clear rejection + documented workaround), B1 detection, given v1 extracts only `mcq_bilingual_two_column`; Option A (page-range `document_format_segments`) deferred to a later gate once a non-MCQ extractor tier is contracted. Open decisions: OD-1 (A vs B), OD-2 (B1 vs B2), OD-3 (A child-table + no-backfill confirmation). No implementation PR may be dispatched until this document is OPERATOR APPROVED.*
