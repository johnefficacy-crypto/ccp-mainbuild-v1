# Corpus readiness — operator record, 2026-09-25

Hand-written record of the RBI Grade B corpus work done on 2026-09-25, and the
SSC CGL provenance decision.

**This is not the generated report.** `docs/status/corpus-readiness.md` is
produced by `scripts/corpus_readiness_report.py`, and the committed copy must
match a fresh fixture run byte for byte
(`app/backend/tests/scripts/test_corpus_readiness_report.py:338-346`). That file
was left untouched. Regenerating it against the live DB
(`python scripts/corpus_readiness_report.py --live --source demo`) is an
operator step; this session had no DB access. Until someone runs it, the
generated doc is **stale for RBI and SSC CGL**, and this record takes precedence
for those two exams.

Every number below was **verified against demo on 2026-09-25** by the operator.
None was re-derived here. Code and migration claims carry file:line.

---

## 1. RBI Grade B

### 1.1 Corpus state

| Bucket | Count |
|---|---:|
| Verified MCQ | 895 |
| Verified descriptive | 48 |
| Pending descriptive | 28 |
| needs_correction MCQ | 28 |
| Pending MCQ | 16 |
| **Total questions** | **1,015** |

*Verified against demo on 2026-09-25.*

This supersedes the 999-question figure in
`workbench/reports/REG-SUBJECT-INVENTORY-2026-09-22.md` §7.

### 1.2 Projection: 882 → 895

- 13 verified MCQs had been left out of the original projection batch. Each had a verified primary tag, 5 options and 1 correct option; nothing about the questions blocked them.
- Fixed by re-running projection per paper through `POST /api/admin/mocks/pyq-papers/{paper_id}/projection/sync` (`app/backend/app/api/admin_mocks.py:461`).
- Projected now equals verified MCQ (895 = 895). *Verified against demo on 2026-09-25.*

### 1.3 Primary-tag corrections: 23 retagged in place

- **Source:** 23 rows marked `tag_ok=no` in `workbench/audit/rbi_grade_b/drafts/rbi_domain_review_ALL_judged.csv`. That file is on the unmerged branch `origin/chore/review-evidence-rbi-ssc` (`1a295a28`), not on main.
- **Method:** `UPDATE pyq_question_topic_tags SET topic_id = …` in place, not delete-then-insert.
- **Why in place is safe:** the one-primary-per-question rule is the partial unique index `uq_pyq_question_one_primary_tag … (question_id) WHERE tag_role='primary'`. That index **exists live and in no migration**; its live definition is recorded at `docs/status/2026-09-09-mains-optionals-strategy-rev2.md:395-401`. Changing `topic_id` leaves `question_id` unchanged, so it cannot collide.
- The only tag uniqueness that migrations do define is `unique(question_id, topic_id, tag_role)` (`app/supabase/migrations/032_pyq_question_intelligence.sql:107`). A retag would collide there only if the question already had a primary tag on the target topic.
- **Evidence effect:** 16 of the 23 are in trust-verified papers and entered the evidence set. The other 7 are in the 4 pending-trust descriptive papers (§1.5) and did not. *Verified against demo on 2026-09-25.*

### 1.4 Coverage and snapshots

| Step | Result |
|---|---|
| Score snapshots recomputed | 244 → 254 topics after the retags; all 254 locked |
| Coverage derive | 168 new rows written, all locked |
| Locked coverage rows | 86 → 254 |
| Projected topics with a lock | 240/240; 248/248 after the 13 were projected |

*Verified against demo on 2026-09-25.*

**Every RBI subject is now reachable in topic mode.** Before this, only
Quantitative Aptitude, English and Reasoning (GIR) were.

### 1.5 The 4 pending-trust papers are left pending on purpose

- **Which papers:** 2022, 2023 and 2024 Phase II, and 2025 P2 ENG — 64 questions, all descriptive. *Verified against demo on 2026-09-25.*
- **Why they stay pending:** verifying them would put descriptive evidence into coverage.
- **Why that would happen:** snapshot compute filters papers on `trust_status='verified'` (`app/backend/app/exam_intelligence/score_snapshots.py:338-346`), questions on `reviewer_status='verified'` (`:406-411`) and tags on verified primary (`:439-445`). **It never filters on `question_type`.** Coverage would then rank topics on questions nobody can practise in MCQ mode.

### 1.6 Still open (RBI)

1. **76 descriptive questions have no learner surface** — 28 pending + 48 verified.
   - The Finance & Management subject shell is empty (0 macro / 0 micro).
   - Finance (17 macro / 101 micro) and Management (10 / 80) are fully built.
   - So the fix is a **remap onto the existing trees, not a tree build**. *Verified against demo on 2026-09-25.*
2. **28 needs_correction MCQs**, all from the 2022 text extraction.
3. **16 pending MCQs.**
4. **No explanations** for the ~412 questions promoted since the last export.
5. **The 2025 Phase II MCQs are labelled recreated/paraphrased in their own metadata.** They must not be presented to learners as verbatim PYQs.

---

## 2. SSC CGL — provenance decision

### 2.1 State

| Metric | Count |
|---|---:|
| Questions | 850 |
| Papers | 13 |
| `reviewer_status` | all `pending` |
| Tagged in DB | 0 |
| Projected | 0 |

*Verified against demo on 2026-09-25.*

- Offline drafts: 845 of 850 rows carry a proposed tag, with `decision` still blank.
- The 5 unmapped rows are Venn-diagram questions. They wait on a microtopic migration.
- The drafts are 13 files, `workbench/audit/ssc_cgl/drafts/ssc-cgl-2024-paper-*-draft.csv`, 850 data rows in total. Like the RBI worksheet, they are on the unmerged branch `origin/chore/review-evidence-rbi-ssc` (`1a295a28`), not on main.
- Tagging constraints are in `workbench/audit/ssc_cgl/README.md:14-35`.

### 2.2 Decision

Provenance for the 13 papers will be anchored by **uploading the 13 source
PDFs (7 MB total) as `document_assets`** and linking each one to its paper,
with:

- `document_kind='pyq_paper'`
- `source_kind='raw_coaching'` (`app/backend/app/exam_intelligence/extraction/dispatch.py:94`; DB CHECK `app/supabase/migrations/153_extraction_source_kind_gate.sql:19`)
- `exam_identity='unknown'` — the `document_exam_identity` enum has no SSC member (`app/supabase/migrations/152_extraction_paper_format_scope_fence.sql:22-39`, mirrored at `dispatch.py:23-39`)

**It will NOT be anchored by putting a coaching or ssc.gov.in URL in
`pyq_papers.source_url`.** That column is shown to learners: it is served by
`GET /api/exam-intelligence/exams/{slug}` and rendered as an "Open" link. See
`docs/runbooks/pyq-paper-provenance.md` §2.

The procedure is `docs/runbooks/pyq-paper-provenance.md` §3.

### 2.3 Open items the decision does not settle

1. **The gate also checks `source_type`, and the document does not satisfy that check.** Check (a) blocks `source_type` NULL or `'unknown'` (`app/supabase/migrations/271_review_pyq_paper_question_count_gate.sql:116-119`), whatever document is attached. The allowed values are `official, memory_based, coaching, community, aggregator, unknown` (`032_pyq_question_intelligence.sql:30-31`). The decision does not name one. `'coaching'` matches `raw_coaching`, but it has not been chosen.
2. **Each upload must use the paper's own `exam_id`.** `upload-url` writes the request's `exam_id` into `metadata.exam_id` (`app/backend/app/api/admin_exam_intel_documents.py:365-370`), and both the link RPC and the gate reject a mismatch (`189_cms_provenance_doc_lock.sql:199-203`, `271:152-156`).
3. **`raw_coaching` cannot be fed to the structured extraction pipeline**, because it is outside `ELIGIBLE_SOURCE_KINDS_V1` (`dispatch.py:100-105`; refused at `extraction/pipeline.py:361`). The questions are already loaded, so the upload is provenance only. `processing_policy='store_only'` records it that way (`admin_exam_intel_documents.py:443-453`).
4. **Upload size:** the per-file limit is `LIBRARY_MAX_UPLOAD_MB`, default 25 MB (`app/backend/app/core/config.py:34`). The 7 MB total is well inside it.
