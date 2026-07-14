# GQR Solution Strategies and Improvement Lab — execution checklist

**Status:** ACTIVE DELIVERY CHECKLIST  
**Decision locked:** 2026-07-14  
**Architecture contract:** `docs/architecture/solution-strategies-improvement-lab.md`  
**Parent contracts:** `docs/architecture/subject-practice-framework.md`, `docs/architecture/english-writing-practice.md`  
**Central status source:** `docs/status/career-copilot-checklist.md`

This checklist records the implementation sequence for learner-facing Quant and Reasoning Solution Strategies and the Improvement Lab composition. Every implementation PR must update the affected rows here and mirror any changed delivery status into `docs/status/career-copilot-checklist.md`.

---

## Status vocabulary

- **DESIGN LOCKED** — product and architecture decision is approved; implementation may proceed within the stated boundaries.
- **MERGED / CODE PRESENT** — verified in the repository.
- **CODE-FIXED, VALIDATION PENDING** — implementation exists but live/operator proof remains.
- **PLANNED** — implementation has not landed.
- **BLOCKED** — a stated prerequisite must clear first.
- **DEFERRED** — deliberately excluded from the active delivery sequence.

---

## Locked naming

| Surface | Locked learner label | Status |
|---|---|---|
| Parent learner surface | Improvement Lab | DESIGN LOCKED |
| English section | My Writing Errors | DESIGN LOCKED |
| Quant section | Methods & Shortcuts | DESIGN LOCKED |
| Reasoning section | Approaches & Patterns | DESIGN LOCKED |
| Question review component | Solution Strategy | DESIGN LOCKED |
| Internal Quant authority | Quant Heuristic | MERGED / CODE PRESENT — do not rename schema/admin terminology |

---

## Current repository baseline

| Item | Current status | Evidence / required action |
|---|---|---|
| Quant heuristic schema | MERGED / CODE PRESENT | `app/supabase/migrations/243_quant_heuristic_authority.sql` defines `quant_heuristics` and `quant_question_heuristics`. |
| Quant lifecycle CAS/reason hardening | MERGED / CODE PRESENT | `app/supabase/migrations/246_quant_heuristic_review_cas_reason.sql`. |
| Quant verified-only read authority | MERGED / CODE PRESENT | `app/backend/app/study_os/quant_heuristics.py`; batched verified/active reads, scope-compatible links, deterministic ordering, and compatibility wrapper are present. |
| Quant Content Studio library | MERGED / CODE PRESENT | `QuantHeuristicLibrary.jsx`; verify whether complete authoring/editing/activation/assignment exists before learner launch. |
| Quant Content Studio review queue | MERGED / CODE PRESENT | `QuantHeuristicReviewQueue.jsx`. |
| Shared mock review endpoint | MERGED / CODE PRESENT | `mock_engine.py::get_review()` and `GET /api/study/mocks/attempts/{id}/review`. |
| Shared question renderer | MERGED / CODE PRESENT | `QuestionRenderer.jsx` owns shared stimulus + type renderer composition. |
| Existing English Error Lab read model | MERGED / CODE PRESENT | `ewp_error_lab`, English endpoint, hook, and `ErrorLab.jsx`; preserve as English-specific authority. |
| Quant learner strategy delivery | CODE-FIXED, VALIDATION PENDING | GQR-S1 below — `solution_strategies.py` + batched and scope-compatible `heuristics_for_questions` + `get_review` attach + `SolutionStrategyPanel`; automated tests green; live/operator proof pending. |
| Reasoning strategy authority | PLANNED | GQR-S3 below. |
| Improvement Lab composition | PLANNED | GQR-S5 below. |

---

## Delivery sequence

| ID | Slice | Status | Dependency | Required outcome |
|---|---|---|---|---|
| GQR-S0 | Product/architecture decision and checklist | DESIGN LOCKED | None | This document and `solution-strategies-improvement-lab.md` are the source for scope and sequencing. |
| GQR-S1 | Quant Solution Strategy delivery in mock review | CODE-FIXED, VALIDATION PENDING | Existing GQR-Q7 authority | Batched verified-only read, learner projection, review payload field, shared panel, regular/generated-mock tests. No migration. |
| GQR-S2 | Quant content-readiness completion | PLANNED — CONDITIONAL | GQR-S1 or preflight | Add authoring/editing/activation/question assignment only when verified linked content cannot already be produced through an existing governed path. |
| GQR-S3 | Reasoning strategy authority and Content Studio | PLANNED | GQR-S0 | New governed schema, RLS, lifecycle/audit RPCs, library, authoring, assignment, and review queue. |
| GQR-S4 | Reasoning independent-question learner delivery | BLOCKED on GQR-S3 | GQR-S3 validated | Reuse normalized DTO and Solution Strategy panel for text Reasoning questions. |
| GQR-S5 | Rename Error Lab learner page to Improvement Lab | PLANNED | GQR-S0; may run after GQR-S1 contract stabilizes | Canonical route, old-route compatibility, renamed header, existing English section preserved. |
| GQR-S6 | Improvement Lab Quant and Reasoning personalized feeds | BLOCKED on learner delivery | GQR-S1 and GQR-S4 | Bounded owner-scoped attempt-history aggregation; live verified-only projection; independent section states. |
| GQR-S7 | Reasoning set/stimulus-aware strategies | BLOCKED on GQR-S3/GQR-S4 | Reasoning authority + independent delivery | Set-level authority and one-time grouped rendering; no duplication per question. |
| GQR-S8 | Planner/Calculation Gym recommendations | DEFERRED | GQR-Q8/Q9 and Lane A gates | Keep speed/calculation evidence and planner activation outside the strategy-delivery PRs. |
| GQR-S9 | Non-verbal Reasoning | DEFERRED | Media-aware contract required | No image-dependent Reasoning content in the active sequence. |

---

## GQR-S1 — Quant Solution Strategy delivery

**Status:** CODE-FIXED, VALIDATION PENDING  
**PR posture:** one focused backend-heavy learner-delivery PR; no schema migration.

### Backend

- [x] Create `app/backend/app/study_os/solution_strategies.py`.
- [x] Define the normalized learner-safe strategy projection.
- [x] Add `quant_heuristics.heuristics_for_questions(supabase, question_ids)`.
- [x] Deduplicate question IDs and initialize empty output lists.
- [x] Use one verified-link query for all question IDs.
- [x] Embed linked question topic/microtopic scope in the link query without adding another query.
- [x] Use one verified+active heuristic query for all referenced heuristic IDs.
- [x] Require link verified AND heuristic verified AND heuristic active.
- [x] Require every populated heuristic topic/microtopic dimension to match the linked question.
- [x] Fail closed for absent or inconsistent embedded question scope.
- [x] Sort by relevance, stable name, then stable ID.
- [x] Prevent cross-question and cross-subject leakage.
- [x] Keep `heuristics_for_question()` as a compatibility wrapper.
- [x] Explicitly strip governance and internal scope fields at the authority boundary.
- [x] Omit raw `applicability_rule`.
- [x] Make optional strategy-read failure fail soft to empty lists.
- [x] Update `mock_engine.get_review()` to fetch strategies once before its response loop.
- [x] Attach `solution_strategies` beside `question_snapshot`.
- [x] Keep strategy content live rather than frozen in the attempt snapshot.
- [x] Preserve submitted-attempt and ownership gates.

### Learner projection fields

- [x] `id`
- [x] `subject_family`
- [x] `name`
- [x] `strategy_type`
- [x] `formula_latex`
- [x] `standard_method`
- [x] `faster_method`
- [x] `worked_example`
- [x] `key_observation`
- [x] `common_traps`
- [x] `relevance`

### Forbidden fields

- [x] No `applicability_rule`.
- [x] No `reviewer_status`.
- [x] No `reviewer_notes`.
- [x] No `reviewed_by`/`reviewed_at`.
- [x] No `created_by` or audit identifiers.
- [x] No topic/microtopic scope fields in the learner payload.
- [x] No content-revision/CAS internals.

### Frontend

- [x] Create `SolutionStrategyPanel.jsx` under the shared question components.
- [x] Render it from `QuestionRenderer.jsx`, not each question-type renderer.
- [x] Render only when `mode === "review"`.
- [x] Return `null` for empty or missing arrays.
- [x] Wrap bare LaTeX before sending to the existing `MathRenderer`/KaTeX path.
- [x] Render Standard method, Faster method, Key observation, Worked example, and Watch out for labels only when populated.
- [x] Thread `current.solution_strategies ?? []` from `MockReview.jsx`.
- [x] Preserve existing explanation behavior.
- [x] Preserve old payload compatibility.

### Backend tests

- [x] Multiple question IDs result in one link query and one heuristic query.
- [x] The link query embeds `mock_question_bank` topic/microtopic scope.
- [x] Verified link + verified active heuristic is included.
- [x] Pending/rejected link is excluded.
- [x] Pending/rejected/`needs_correction` heuristic is excluded.
- [x] Inactive heuristic is excluded.
- [x] Topic and microtopic mismatches are excluded.
- [x] Missing embedded question scope is excluded.
- [x] Projection strips governance and internal scope fields.
- [x] Strategies attach to the correct question only.
- [x] Stable ID breaks equal relevance/name ties.
- [x] Empty input causes no reads.
- [x] Read failure returns empty lists without breaking review.
- [x] Unsubmitted attempt cannot obtain review.
- [x] Regular and generated mocks share the behavior.

### Frontend tests

- [x] Panel renders in review mode.
- [x] Panel is absent in active-attempt mode.
- [x] Empty/missing strategy arrays render nothing.
- [x] Formula is rendered through existing KaTeX support.
- [x] Works through MCQ, numerical, and statement-based renderers.
- [x] Existing MockReview tests remain green.

### Completion gate

- [x] Focused backend tests pass in CI.
- [x] Focused frontend tests pass in CI.
- [x] Affected mock review regression suites pass in CI.
- [x] No migration or RLS change appears in the diff.
- [x] Checklist row is set to CODE-FIXED, VALIDATION PENDING.
- [ ] Complete GQR-S2 live/operator proof with a verified heuristic and verified question link.

---

## GQR-S2 — Quant content readiness

**Status:** PLANNED — CONDITIONAL

### Preflight

- [ ] Count verified active Quant heuristics.
- [ ] Count verified Quant question links.
- [ ] Confirm linked questions are reachable through mock/generated-mock review.
- [ ] Confirm Content Studio can create/edit/activate heuristics or document the governed intake path that does.
- [ ] Confirm Content Studio can create and review question links or document the governed assignment path that does.

### Decision

- [ ] Skip GQR-S2 when production-ready verified linked content already exists and can be maintained.
- [ ] Otherwise implement draft authoring, editing, activation/retirement, assignment, and link review inside Content Studio.
- [ ] Do not create a new AdminShell/sidebar destination.
- [ ] Keep heuristic and link reviews separate and conjunctive.

### Data/operator gate

- [ ] Seed or author at least one reviewed Quant strategy for a supported question.
- [ ] Verify it appears in submitted review.
- [ ] Move the heuristic or link out of verified state and prove it disappears on the next read.

---

## GQR-S3 — Reasoning strategy authority

**Status:** PLANNED

### Schema

- [ ] Add `reasoning_strategies`.
- [ ] Add `reasoning_question_strategies`.
- [ ] Add topic/microtopic scope checks.
- [ ] Add stable strategy code uniqueness.
- [ ] Add typed strategy values: approach, pattern, elimination, diagram method, set method, trap.
- [ ] Add structured `applicability_rule` for internal selection.
- [ ] Add method, observation, example, and trap content fields.
- [ ] Add reviewer lifecycle and active state.
- [ ] Add unique question-strategy link.
- [ ] Add relevance and independent link reviewer status.
- [ ] Add indexes for question, strategy, status, topic, and microtopic.

### Governance

- [ ] Enable RLS on every new table.
- [ ] Revoke direct anon/authenticated access.
- [ ] Grant only deliberate service-role capabilities.
- [ ] Add audited review lifecycle RPC.
- [ ] Enforce expected-status CAS.
- [ ] Enforce expected-`updated_at` CAS.
- [ ] Require a review reason.
- [ ] Test transition matrix and stale-content rejection.

### Content Studio

- [ ] Add Reasoning Strategy Library inside existing Content Studio.
- [ ] Add draft creation/editing.
- [ ] Add activation/retirement.
- [ ] Add question assignment.
- [ ] Add strategy review queue.
- [ ] Add question-link review.
- [ ] Add learner-safe projection preview.
- [ ] No new top-level admin route.

### Initial coverage

- [ ] Analogy/classification.
- [ ] Number/alphabet series.
- [ ] Coding-decoding.
- [ ] Blood relations.
- [ ] Directions.
- [ ] Ranking/ordering.
- [ ] Syllogism.
- [ ] Statement-conclusion.
- [ ] Statement-assumption.
- [ ] Logical sequence.

### Completion gate

- [ ] Fresh migration stack succeeds.
- [ ] RLS/privilege tests pass.
- [ ] Lifecycle and CAS tests pass.
- [ ] Content Studio tests pass.
- [ ] At least one verified strategy and verified question link can be produced through the governed workflow.

---

## GQR-S4 — Reasoning independent-question delivery

**Status:** BLOCKED on GQR-S3

- [ ] Create `app/backend/app/study_os/reasoning_strategies.py`.
- [ ] Implement batched verified-only `strategies_for_questions()`.
- [ ] Project into the shared learner DTO.
- [ ] Add Reasoning as a source in `solution_strategies.py`.
- [ ] Do not modify the mock review response loop again beyond source registration.
- [ ] Reuse `SolutionStrategyPanel` without a Reasoning-specific fork.
- [ ] Verify `key_observation`, elimination, diagram, and trap content render.
- [ ] Verify Quant and Reasoning strategies cannot cross-leak.
- [ ] Keep non-verbal Reasoning out of scope.

---

## GQR-S5 — Improvement Lab rename and shell

**Status:** PLANNED

### Routing

- [ ] Create canonical `/app/study/improvement-lab` route under `StudyShell`.
- [ ] Preserve `RouteErrorBoundary` placement.
- [ ] Redirect or alias `/app/study/error-lab`.
- [ ] Update internal links and route tests.
- [ ] Keep the surface absent from the primary sidebar unless separately approved.

### Page

- [ ] Rename learner title to Improvement Lab.
- [ ] Use learner copy covering recurring errors and useful solving strategies.
- [ ] Render My Writing Errors.
- [ ] Render Methods & Shortcuts.
- [ ] Render Approaches & Patterns.
- [ ] Give each section an independent loading, empty, and error state.
- [ ] One section failure must not hide the others.

### English preservation

- [ ] Continue using `GET /api/study/practice/english/error-lab`.
- [ ] Do not rename or repurpose `ewp_error_lab`.
- [ ] Preserve owner scope, feedback-release gate, invalidation handling, and reclassification behavior.

---

## GQR-S6 — Personalized Improvement Lab feeds

**Status:** BLOCKED on GQR-S1 and GQR-S4

### API

- [ ] Add server-owned Quant learner feed.
- [ ] Add server-owned Reasoning learner feed.
- [ ] Authenticate and owner-scope every read.
- [ ] Bound recent attempt and response reads.
- [ ] Consider only submitted/trusted attempts allowed by the chosen contract.
- [ ] Batch strategy reads.
- [ ] Deduplicate by strategy ID.
- [ ] Keep verification and active-state checks live.

### Evidence summary

- [ ] `times_seen`.
- [ ] `wrong_count`.
- [ ] `correct_count`.
- [ ] `last_seen_at`.
- [ ] bounded recent source question IDs.

### Ranking

- [ ] Wrong-associated strategies before correct-only strategies.
- [ ] Recent before stale.
- [ ] Relevance before stable name/ID tie-break.
- [ ] Deterministic results for identical evidence.

### Boundaries

- [ ] Do not dump the full canonical library.
- [ ] Do not add a saved-strategy table in v1.
- [ ] Do not write planner tasks.
- [ ] Do not infer target solve time.
- [ ] Withdrawn content disappears on the next read.

---

## GQR-S7 — Reasoning set-aware strategies

**Status:** BLOCKED on GQR-S3 and GQR-S4

- [ ] Define governed stimulus/set strategy link authority.
- [ ] Require verified strategy + verified set link + active state.
- [ ] Add `stimulus_solution_strategies` to the review contract.
- [ ] Render set-solving approach once above grouped questions.
- [ ] Preserve question-specific `solution_strategies`.
- [ ] Do not repeat the same set strategy on every question.
- [ ] Preserve existing text/table stimuli.
- [ ] Add grouped seating-arrangement/puzzle tests.
- [ ] Keep non-verbal/image Reasoning deferred.

---

## Cross-cutting security checklist

- [x] No direct learner table reads for GQR-S1.
- [x] No new authenticated/anon RLS read policy for governed strategy content in GQR-S1.
- [x] Service-role server projection only for GQR-S1.
- [x] Strategy and link verification are conjunctive for GQR-S1.
- [x] Active state checked at read time for GQR-S1.
- [x] Question topic/microtopic scope checked at read time for GQR-S1.
- [x] Governance and internal scope fields stripped in backend code for GQR-S1.
- [x] Attempt ownership checked before review response.
- [x] Submitted-state gate preserved.
- [x] Optional strategy failure does not break core review.
- [x] No question-to-question leakage in GQR-S1 tests.
- [x] No subject-to-subject leakage in GQR-S1 tests.
- [x] Content Studio remains governance authority.

---

## Cross-cutting compatibility checklist

- [x] Existing explanation fields remain unchanged by GQR-S1.
- [x] Missing `solution_strategies` is treated as `[]`.
- [x] Non-eligible questions receive `[]`.
- [x] Regular and generated mocks use the same contract.
- [x] Existing question-type renderers do not need subject-specific copies.
- [ ] Existing English Error Lab consumers continue to work through old-route compatibility — GQR-S5.
- [x] No planner, mastery, Calculation Gym, or current-affairs behavior changes in GQR-S1.

---

## Status synchronization

Every delivery PR must update:

- [x] the affected GQR-S1 row in this checklist;
- [x] the corresponding GQR-S1 row or note in `docs/status/career-copilot-checklist.md`;
- [x] the architecture contract when a governed decision changes — no architecture change required in GQR-S1;
- [x] PR body with changed files, tests run, migrations, operator steps, and deferred scope;
- [ ] Graphify outputs only when the repository's normal Graphify workflow requires it — not required for this focused implementation.

Do not mark a row MERGED / CODE PRESENT from planned text alone. Do not mark live/operator validation complete from mocked frontend tests or static migration inspection.
