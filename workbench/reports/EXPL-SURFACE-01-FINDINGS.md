# EXPL-SURFACE-01 — How does an explanation reach an aspirant?

- **Scope:** read-only code investigation. No live DB, no API calls, no migrations. Live row counts are the given facts from the prompt; nothing here re-derives them.
- **Base:** branch `claude/expl-surface-01` off `origin/main` @ `ae5ef4f5`.
- **Graph freshness:** `graphify-out/GRAPH_REPORT.md` was built from `3af5946f`, two commits behind HEAD. The gap is `43575b3a` (SSC CGL Tier I worksheets) plus its merge, and neither touches the paths below.
- **Convention:** "code" means it exists in executable source or SQL. "doc" means it exists only in prose. All paths are repo-relative.

## Verdict

**Is `pyq_question_explanations` read anywhere an aspirant can see? No.**
- The only reader is an admin CMS list route.
- No frontend file references the table or its routes.
- No backend or frontend caller invokes the review RPC.
- So the 402 SEBI rows are invisible to aspirants. Nothing in the product can move them to `verified` either.

**Is `mock_question_bank.explanation` rendered? Yes.**
- It reaches the aspirant on the mock attempt-review screen, through the frozen `question_snapshot`.
- The 220 populated rows are not dead storage. Any attempt started after a row got its text shows that text on review.

---

## A. The attempt-review path

**Backend endpoint**
- Route: `GET /api/study/mocks/attempts/{attempt_id}/review`. The router prefix `/study/mocks` is at `app/backend/app/api/mock_engine.py:48` and the handler is at `app/backend/app/api/mock_engine.py:309-320`.
- The handler calls `get_review` at `app/backend/app/study_os/mock_engine.py:1473-1570`, which requires `status == 'submitted'` (`:1475-1476`).

**Response shape** (`app/backend/app/study_os/mock_engine.py:1536-1570`):

```
{
  "attempt_id": ...,
  "questions": [{
      "question_id", "attempt_order",
      "question_snapshot",          # frozen dict, see below
      "selected_option_id", "numeric_answer", "is_correct",
      "error_type",
      "explanation",                # = question_snapshot.explanation (:1550)
      "solution_strategies",        # LIVE verified-only read, not frozen (:1551-1552)
      "time_spent_sec"
  }],
  "stimulus_solution_strategies": [...]
}
```

**What the snapshot carries**
- `question_snapshot` is built at attempt start by `_question_snapshot` (`mock_engine.py:263-333`) and frozen into `mock_attempt_responses` (`mock_engine.py:708-716`).
- It carries `"explanation": q.get("explanation")` (`:286`), copied from the `mock_question_bank` row. That row is loaded with `select("*")` (`mock_engine.py:106-110`).
- It also carries `pyq_question_id` (`:299`), which links the frozen question back to `pyq_questions.id`.
- It does **not** carry `common_trap`.

**Frontend component**
- Route: `/app/study/mocks/attempts/:attemptId/review` → `MockReview`, defined at `app/frontend/src/routes/appRoutes.jsx:55,143`.
- `app/frontend/src/pages/study/mocks/MockReview.jsx:53` fetches the endpoint. `:200-216` renders `<QuestionRenderer mode="review" showCorrect showExplanation question={{...current.question_snapshot, ...}}>`.
- Only the snapshot's copy of `explanation` is used. The top-level `questions[].explanation` duplicate is not read by the frontend.

**How it reaches pixels**
- `QuestionRenderer.jsx:14-27` dispatches on question type.
- `types/MCQSingle.jsx:58`, `types/MCQMulti.jsx:9` and `types/NumericalAnswer.jsx:43,59` render `{showExplanation && question.explanation ? <MarkdownSafe text={question.explanation}/> : null}`.
- `StatementBased.jsx`, `AssertionReason.jsx` and `MatchFollowing.jsx` never render `explanation` (0 matches).
- The projection writes `question_type='mcq'` (`272_pyq_projection_bytea_cast_fix.sql:506`), so projected PYQs go through `MCQSingle`.

**Fields that reach the aspirant on review**
- Stem, options, stimuli, correct answer (resolved to a label by `MCQSingle.jsx:22-31,52-57`), their own selection, numeric answer and tolerance, the error-type label (`MockReview.jsx:188`), solution strategies and the stimulus strategy panel (`MockReview.jsx:190-199`), and **`explanation`** (flat text from `mock_question_bank.explanation`).
- No field from `pyq_question_explanations` is among them.

**Adjacent screens**
- `GET .../result` (`mock_engine.py:1253-1257` → `_build_result`, `:1389`) also returns `explanation` per question. `MockResult.jsx` does not render it: `explanation` has no match in `app/frontend/src/pages/study/mocks/MockResult.jsx`.
- During the attempt, `_serialise_question_for_attempt` (`mock_engine.py:1318-1344`) omits `explanation`, so nothing leaks before submission.

## B. Is `mock_question_bank.explanation` rendered?

**Yes.** Every read path:

| Read | Where | Reaches aspirant? |
|---|---|---|
| Fixed-template selection, `select("*")` | `mock_engine.py:106-110` → `_question_snapshot` `:286` | Yes, via review (A) |
| Criteria and section selection, `select("*")` | `mock_engine.py:393-394`, `:559-560` → same snapshot builder | Yes, via review |
| Generated or blueprint attempts | `study_os/generated_mock_attempt.py:122-123` `select("*")`; `study_os/pyq_practice.py:31,319,544` reuse `_question_snapshot` | Yes, via review (see D) |
| `_build_result` | `mock_engine.py:1389` | Returned, not rendered (`MockResult.jsx`) |
| Admin question CRUD and import | `admin/mock_questions.py:190,230,335`; `admin/mock_import.py:165,457`; `api/admin_mocks.py:88,115` | Admin only (these are writes plus edit echo) |

**Gate: the value is frozen at attempt start**
- An explanation added or changed in the bank after an attempt started never reaches that attempt's review.
- An explanation removed later is not retracted from old attempts either.

## C. Is `pyq_question_explanations` read anywhere?

| Read | Where | Reaches aspirant? |
|---|---|---|
| `GET /admin/exam-intelligence-cms/pyq-question-explanations` | `app/backend/app/api/admin_exam_intel_cms.py:4558-4584` (`PERM_CMS` + `_flag_enabled`) | No: admin only. No frontend caller (no match for `pyq-question-explanations` under `app/frontend/src`) |
| Existence and uniqueness pre-checks inside create, patch and bulk | `admin_exam_intel_cms.py:4612-4623`, `:4650`, `:4669-4680`, `:4987-4995` | No: write-side validation |
| `cms_review_pyq_question_explanation` RPC (`SELECT … FOR UPDATE`) | `app/supabase/migrations/230_pyq_question_explanations.sql:209-309` | No. **No code caller exists**: the name appears in the backend only in comments and a docstring (`admin_exam_intel_cms.py:4480,4648`). Execute is granted to `service_role` only (`230:306-309`) |
| RLS | `230:183-196`: `is_admin(auth.uid())` only; `anon` has no grant (`230:205-206`) | Structurally blocks any direct learner read |

**What the docs say**
- `docs/architecture/pyq-explanations.md:35-36`: "learner exposure will flow through a reviewed projection".
- `docs/architecture/pyq-explanations.md:130-134`: "surfacing layer (not built yet)".
- Both are doc-only statements. No code implements either.

## D. PYQ practice, separately from mocks

**`pyq_practice.py`**
- `app/backend/app/api/pyq_practice.py` **does not exist (not found)**.
- The practice surface is `app/backend/app/api/pyq_practice_launch.py:26,56-57` (`POST /study/tasks/{id}/launch-pyq-practice`) plus `app/backend/app/study_os/pyq_practice.py`.
- Practice selects from `mock_question_bank` and freezes snapshots with the same `_question_snapshot` (`study_os/pyq_practice.py:31,319,544-547`).
- It starts via the `start_attempt_from_blueprint` RPC. That RPC freezes the caller-supplied snapshot verbatim: `179_start_attempt_from_blueprint.sql:141-149`, `coalesce(r->'question_snapshot', '{}')`.
- The resulting attempt is "a normal mock attempt served by the existing `/attempts/{id}` routes" (`api/pyq_practice_launch.py:9-10`).
- **So practice shows `mock_question_bank.explanation` on the same `MockReview` screen**, with the same gate as A. It does not read `pyq_question_explanations`.

**PYQ Explorer**
- Backend: `GET /api/exam-intelligence/exams/{slug}/pyqs`, at `app/backend/app/api/exam_intelligence.py:46` (prefix) and `:303-315`.
- It reads `pyq_questions.explanation_text` (`:417-420`) and returns it as `"explanation"` (`:601`).
- Frontend: `app/frontend/src/features/exams/PyqExplorerSection.jsx:124-129` renders "Explanation: {q.explanation}" in the expanded row. It is mounted from `ExamIntelligenceTab.jsx`, `pages/ExamDetail.jsx` and `pages/study/Subjects.jsx`.
- **The Explorer shows `pyq_questions.explanation_text`, a third store**, separate from both tables in the question.
- It does not read `pyq_question_explanations`.

## E. The gates

**Mock review and PYQ practice review**
- No gate on the explanation itself. It is shown whenever the frozen snapshot has it (`MCQSingle.jsx:58`) and the attempt belongs to the caller and is submitted (`mock_engine.py:1474-1476`).
- The upstream gates act on the question, not the explanation:
  - Bank selection: `reviewer_status in ('verified','published','live')` and not expired (`mock_engine.py:105-110`).
  - PYQ lineage: an active projection is required (`pyq_mock_question_projections.sync_status='active'`, `mock_engine.py:115-131`, fail-closed).
  - Projection: the RPC refuses unless `pyq_papers.trust_status='verified'` (`272:130-135`) and `pyq_questions.reviewer_status='verified'` (`272:163-168`). Options, tags and stimuli must also be verified (`272:194-197,238,257,274,329-339`).
- In practice, `pyq_questions.explanation_text` rides on the question's review, with no review lifecycle of its own.
- No feature flag was found on `get_review`.

**Explorer**
- `pyq_papers.trust_status='verified'` (`exam_intelligence.py:354`) and `pyq_questions.reviewer_status='verified'` (`:423`). Authenticated user (`:314`).
- No explanation-level gate.

**`pyq_question_explanations`**
- Its own gate is `reviewer_status='verified'`, which is fail-closed on licence, ambiguity, final answer and reviewer identity (`230:157-171`). Content and provenance edits downgrade a verified row (`230:125-155`).
- No read path consumes that gate, so it gates nothing today.

---

## Candidate routes from "row exists" to "aspirant reads it"

**Prerequisite for every route: verification.**
- No product route can move an explanation out of `pending`. The RPC has no backend wrapper and no admin UI.
- Whichever route is chosen, a `POST …/pyq-question-explanations/{id}/review` wrapper around `cms_review_pyq_question_explanation` is required first. Without it every route surfaces zero rows.

**The prerequisite that is missing**
- The verify precondition needs `final_answer_option_id` (`230:165-167`).
- The 402 rows were created through the create path, but whether they carry that ID is unknown without the DB.

### Route 1: live read at the attempt-review endpoint (recommended)

**Mechanism**
- In `get_review`, collect `question_snapshot.pyq_question_id` for all questions.
- Make one batched read of `pyq_question_explanations`, `reviewer_status='verified'`, `in_(question_id, ids)`.
- Pick one row per question by explicit source precedence.
- Attach a learner-safe DTO as a sibling of `question_snapshot`, exactly like `solution_strategies` (`mock_engine.py:1496-1501,1551-1552`).

**Precedent in code**
- GQR-S1 strategies are a live, verified-only, fail-soft sibling read, deliberately not frozen, so that "a strategy later unverified/inactive disappears from subsequent review reads" (`mock_engine.py:1496-1501`).
- `study_os/solution_strategies.py:27` defines a governance-free learner DTO and `:109-148` a batched, fail-soft reader.

**Files**
- New `app/backend/app/study_os/pyq_explanations.py`: batched verified-only reader, precedence, DTO with no `reviewer_status`, licence or source fields.
- `study_os/mock_engine.py` `get_review`.
- Backend tests.

**Frontend**
- Yes. `MockReview.jsx:204-215` passes the new field.
- The renderer needs a panel for structured content (`short_explanation`, `solution_steps`, `option_rationales`, `formula_used`, `common_traps`). Mounting it once in `QuestionRenderer.jsx` next to `SolutionStrategyPanel` (`:24-26`) avoids touching every type renderer.
- Decide whether a verified structured explanation suppresses the flat `question.explanation` or sits alongside it. Suppressing it avoids showing two explanations.

**Multiple source types**
- Handled explicitly: one precedence tuple, applied in one place.

**Properties**
- Retroactive: works for past attempts, including SEBI mocks already taken.
- Retracts on unverify.
- Zero migrations and no hash contract change.
- Covers PYQ practice for free, since it goes through the same review.
- The same helper can back the Explorer later (`exam_intelligence.py:601`).

### Route 2: project verified explanations into `mock_question_bank.explanation`

**Mechanism**
- A new migration re-creates `project_pyq_question_to_mock_bank`, which is currently at `272`.
- The projected text would become `coalesce(<verified pyq_question_explanations text by precedence>, pyq_questions.explanation_text)` at `272:509,525`.
- The content hash term would change at `272:363`, together with its Python mirror `admin/pyq_mock_projection.py:233-276`.

**Files**
- A new migration, `admin/pyq_mock_projection.py` (hash mirror plus `_fetch_paper_questions` `:59-77`), and hash-parity tests.
- Then a re-sync of every affected paper, which is an operator step.

**Frontend**
- None for flat text, but the flat column carries only prose. `solution_steps`, `option_rationales`, `formula_used` and `common_traps` are lost. `docs/architecture/pyq-explanations.md:10-14` says the table exists precisely because a flat column can't carry them.

**Multiple source types**
- Must be encoded in SQL inside the RPC, plus the Python mirror, so there are two places to keep in sync.

**Properties**
- Only attempts started after the re-sync see it, because of snapshot freeze. Every SEBI attempt already taken stays without it.
- An explanation unverified later stays in every frozen snapshot, which breaks "verified-only reads" for historical reviews.
- An unverify also doesn't trigger re-projection: the hash only re-projects on the next sync.
- This is the path the upsc-cse rows already use (see below), so it is the "existing" projection, but it inherits all of these limits.

### Route 3: backfill `pyq_questions.explanation_text` from verified explanations

**Mechanism**
- Copy verified text into `pyq_questions.explanation_text`, which is CMS-writable (`admin_exam_intel_cms.py:1980-1983`).
- The existing projection (`272:509`) and the Explorer (`exam_intelligence.py:601`) pick it up with zero read-path code.

**Cost**
- Two sources of truth, and it discards the independent review lifecycle (`docs/architecture/pyq-explanations.md:12-14`).
- It has all of Route 2's freeze and retraction problems.
- It edits the question row, which may itself trigger re-review, depending on the question guards. Not traced here.

**Multiple source types**
- Resolved by whoever runs the copy. Not enforced anywhere.

### Recommendation: Route 1

**Why**
- It is the only route that honours the explanation's own `reviewer_status` at read time. That means it retracts on unverify and never leaks via a frozen snapshot.
- It reaches attempts already taken.
- It keeps the structured fields.
- It follows an in-repo precedent (GQR-S1), not a new pattern.
- It needs no migration.

**Work**
- Review-RPC wrapper route (prerequisite), reader helper, and a `get_review` sibling field.
- One frontend panel in `QuestionRenderer`.
- The Explorer can adopt the same helper in a follow-up.

---

## Extra questions

### How did the 220 populated `mock_question_bank.explanation` rows get their text?

**upsc-cse (80 rows)**
- The only code writer that fits PYQ-projected rows is `project_pyq_question_to_mock_bank`. It copies `pyq_questions.explanation_text` → `mock_question_bank.explanation` on insert and update (`272_pyq_projection_bytea_cast_fix.sql:499-509,515-525`), with `source_type='pyq'` and `source_kind='pyq'`.
- `pyq_questions.explanation_text` is written through the CMS question allowlist (`admin_exam_intel_cms.py:1980-1983`), mirrored by `scripts/pyq_cms_body.py:44-54`.
- **Inferred, not proven from code.** Confirming it needs a query: those 80 rows should have `pyq_question_id is not null` and `source_kind='pyq'`.
- **This is the existing projection path.** It is what Route 2 would extend.

**ssc-cgl-legacy-sandbox (140 rows): writer not found in committed code**
- Sandbox exam id: `22222222-…` (`docs/2026-08-31-difficulty-enum-and-sandbox-exam.md:98-104`).
- The committed seed that targets that id, `app/supabase/seeds/pilot_content_ssc_cgl_banking.sql:488-493`, inserts 30 rows **without** an `explanation` column.
- `seeds/exam_intelligence_demo_ssc_cgl.sql` writes no explanation at all.
- The explanation-writing seeds, `migrations/135_mock_engine_core.sql:216-395` (20 rows) and `seeds/e2e_fixtures.sql:65-78`, are IBPS rows with no `exam_id`.
- Runtime writers that could have produced these rows:
  - Admin CSV/JSON import: `admin/mock_import.py:165,457`, rows born `draft`.
  - Admin create: `admin/mock_questions.py:230`.
  - The CA promotion RPC: `249_current_affairs_promotion.sql:166-173` and `251_current_affairs_promotion_hardening.sql:181-220`.
  - Out-of-band SQL.
- Which one it was cannot be established without the DB. `created_by`, `source_type`, `source_kind` and `question_fingerprint` on those rows would tell.

**2,484 regulatory rows with empty `explanation`**
- Consistent with the projection copying an empty `pyq_questions.explanation_text`.
- The 402 SEBI explanations live in the separate table, which the projection never reads.

**`mock_question_bank.common_trap`**
- Added by `158_fix_mock_question_provenance_enum.sql:36` and `159_mock_question_provenance.sql:45`.
- No reader was found. It is not in `_question_snapshot`, and `trap_drill.py`'s `common_trap` is a `pyq_option_patterns.pattern_type` value, not this column.
- It is dead storage.

### Precedent for choosing among multiple candidate rows by source precedence?

**No precedent for source-type precedence.**
- No `_PRECEDENCE`, `_SOURCE_ORDER` or `source_rank` construct exists in `app/backend/app`.

**Nearest analogues, neither of them source precedence:**
- `study_os/mock_blueprint_selection.py:88-90`, `_POLICY_SCOPE_PRIORITY = ("topic_id","subject_id","exam_phase_id","exam_id")`: "most specific active policy wins; ties broken by creation order". This picks one row out of several candidates, but ranks by scope, not source.
- `study_os/solution_strategies.py:45,98-103`, `_RELEVANCE_RANK` plus `_sort_key`: orders multiple verified rows but shows all of them. It does not pick one.

**Doc-only statement**
- `docs/architecture/pyq-explanations.md:130-134` requires "an explicit precedence over `explanation_source_type`… not by taking the first row". No code implements it, and no order is specified.
- A Route 1 implementation would have to define that order. A natural one is `official > platform_original > licensed imported/coaching`, but that is a product decision, not something in the code.
