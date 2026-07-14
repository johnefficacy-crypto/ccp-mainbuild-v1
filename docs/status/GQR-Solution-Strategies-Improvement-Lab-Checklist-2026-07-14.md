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
| Quant verified-only read authority | MERGED / CODE PRESENT | `app/backend/app/study_os/quant_heuristics.py`; current helper is single-question oriented. |
| Quant Content Studio library | MERGED / CODE PRESENT | `QuantHeuristicLibrary.jsx`; verify whether complete authoring/editing/activation/assignment exists before learner launch. |
| Quant Content Studio review queue | MERGED / CODE PRESENT | `QuantHeuristicReviewQueue.jsx`. |
| Shared mock review endpoint | MERGED / CODE PRESENT | `mock_engine.py::get_review()` and `GET /api/study/mocks/attempts/{id}/review`. |
| Shared question renderer | MERGED / CODE PRESENT | `QuestionRenderer.jsx` owns shared stimulus + type renderer composition. |
| Existing English Error Lab read model | MERGED / CODE PRESENT | `ewp_error_lab`, English endpoint, hook, and `ErrorLab.jsx`; preserve as English-specific authority. |
| Quant learner strategy delivery | PLANNED | GQR-S1 below. |
| Reasoning strategy authority | PLANNED | GQR-S3 below. |
| Improvement Lab composition | CODE-FIXED, VALIDATION PENDING | GQR-S5 below — rename + shell landed; personalized feeds are GQR-S6. |

---

## Delivery sequence

| ID | Slice | Status | Dependency | Required outcome |
|---|---|---|---|---|
| GQR-S0 | Product/architecture decision and checklist | DESIGN LOCKED | None | This document and `solution-strategies-improvement-lab.md` are the source for scope and sequencing. |
| GQR-S1 | Quant Solution Strategy delivery in mock review | PLANNED | Existing GQR-Q7 authority | Batched verified-only read, learner projection, review payload field, shared panel, regular/generated-mock tests. No migration. |
| GQR-S2 | Quant content-readiness completion | PLANNED — CONDITIONAL | GQR-S1 or preflight | Add authoring/editing/activation/question assignment only when verified linked content cannot already be produced through an existing governed path. |
| GQR-S3 | Reasoning strategy authority and Content Studio | PLANNED | GQR-S0 | New governed schema, RLS, lifecycle/audit RPCs, library, authoring, assignment, and review queue. |
| GQR-S4 | Reasoning independent-question learner delivery | BLOCKED on GQR-S3 | GQR-S3 validated | Reuse normalized DTO and Solution Strategy panel for text Reasoning questions. |
| GQR-S5 | Rename Error Lab learner page to Improvement Lab | CODE-FIXED, VALIDATION PENDING | GQR-S0; may run after GQR-S1 contract stabilizes | Canonical route, old-route compatibility, renamed header, existing English section preserved. |
| GQR-S6 | Improvement Lab Quant and Reasoning personalized feeds | BLOCKED on learner delivery | GQR-S1 and GQR-S4 | Bounded owner-scoped attempt-history aggregation; live verified-only projection; independent section states. |
| GQR-S7 | Reasoning set/stimulus-aware strategies | BLOCKED on GQR-S3/GQR-S4 | Reasoning authority + independent delivery | Set-level authority and one-time grouped rendering; no duplication per question. |
| GQR-S8 | Planner/Calculation Gym recommendations | DEFERRED | GQR-Q8/Q9 and Lane A gates | Keep speed/calculation evidence and planner activation outside the strategy-delivery PRs. |
| GQR-S9 | Non-verbal Reasoning | DEFERRED | Media-aware contract required | No image-dependent Reasoning content in the active sequence. |

---

## GQR-S1 — Quant Solution Strategy delivery

**Status:** PLANNED  
**PR posture:** one focused backend-heavy learner-delivery PR; no schema migration.

### Backend

- [ ] Create `app/backend/app/study_os/solution_strategies.py`.
- [ ] Define the normalized learner-safe strategy projection.
- [ ] Add `quant_heuristics.heuristics_for_questions(supabase, question_ids)`.
- [ ] Deduplicate question IDs and initialize empty output lists.
- [ ] Use one verified-link query for all question IDs.
- [ ] Use one verified+active heuristic query for all referenced heuristic IDs.
- [ ] Require link verified AND heuristic verified AND heuristic active.
- [ ] Sort by relevance, stable name, then stable ID.
- [ ] Prevent cross-question leakage.
- [ ] Keep `heuristics_for_question()` as a compatibility wrapper if still used.
- [ ] Explicitly strip all governance fields.
- [ ] Omit raw `applicability_rule`.
- [ ] Make optional strategy-read failure fail soft to empty lists.
- [ ] Update `mock_engine.get_review()` to fetch strategies once before its response loop.
- [ ] Attach `solution_strategies` beside `question_snapshot`.
- [ ] Keep strategy content live rather than frozen in the attempt snapshot.
- [ ] Preserve submitted-attempt and ownership gates.

### Learner projection fields

- [ ] `id`
- [ ] `subject_family`
- [ ] `name`
- [ ] `strategy_type`
- [ ] `formula_latex`
- [ ] `standard_method`
- [ ] `faster_method`
- [ ] `worked_example`
- [ ] `key_observation`
- [ ] `common_traps`
- [ ] `relevance`

### Forbidden fields

- [ ] No `applicability_rule`.
- [ ] No `reviewer_status`.
- [ ] No `reviewer_notes`.
- [ ] No `reviewed_by`/`reviewed_at`.
- [ ] No `created_by` or audit identifiers.
- [ ] No content-revision/CAS internals.

### Frontend

- [ ] Create `SolutionStrategyPanel.jsx` under the shared question components.
- [ ] Render it from `QuestionRenderer.jsx`, not each question-type renderer.
- [ ] Render only when `mode === "review"`.
- [ ] Return `null` for empty or missing arrays.
- [ ] Wrap bare LaTeX before sending to the existing `MathRenderer`/KaTeX path.
- [ ] Render Standard method, Faster method, Key observation, Worked example, and Watch out for labels only when populated.
- [ ] Thread `current.solution_strategies ?? []` from `MockReview.jsx`.
- [ ] Preserve existing explanation behavior.
- [ ] Preserve old payload compatibility.

### Backend tests

- [ ] Multiple question IDs result in one link query and one heuristic query.
- [ ] Verified link + verified active heuristic is included.
- [ ] Pending/rejected link is excluded.
- [ ] Pending/rejected/`needs_correction` heuristic is excluded.
- [ ] Inactive heuristic is excluded.
- [ ] Projection strips governance fields.
- [ ] Strategies attach to the correct question only.
- [ ] Empty input causes no reads.
- [ ] Read failure returns empty lists without breaking review.
- [ ] Unsubmitted attempt cannot obtain review.
- [ ] Regular and generated mocks share the behavior.

### Frontend tests

- [ ] Panel renders in review mode.
- [ ] Panel is absent in active-attempt mode.
- [ ] Empty/missing strategy arrays render nothing.
- [ ] Formula is rendered through existing KaTeX support.
- [ ] Works through MCQ, numerical, and statement-based renderers.
- [ ] Existing MockReview tests remain green.

### Completion gate

- [ ] Focused backend tests pass.
- [ ] Focused frontend tests pass.
- [ ] Affected mock review regression suites pass.
- [ ] No migration or RLS change appears in the diff.
- [ ] Checklist row is changed to CODE-FIXED, VALIDATION PENDING or MERGED / CODE PRESENT only after evidence exists.

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

**Status:** CODE-FIXED, VALIDATION PENDING

### Routing

- [x] Create canonical `/app/study/improvement-lab` route under `StudyShell`. (`appRoutes.jsx`)
- [x] Preserve `RouteErrorBoundary` placement. (route stays under the same `StudyShell`/`RouteErrorBoundary` nesting)
- [x] Redirect or alias `/app/study/error-lab`. (`<Navigate>` redirect to the canonical route)
- [x] Update internal links and route tests. (`EnglishPracticeShell.jsx` link, `subject_runtime_policy.py` companion mode, `navContract.test.js`, `Subjects.test.js`, `EnglishPracticeShell.test.jsx`)
- [x] Keep the surface absent from the primary sidebar unless separately approved. (no `DashShell` nav entry added; nav contract unchanged)

### Page

- [x] Rename learner title to Improvement Lab. (`ImprovementLab.jsx`)
- [x] Use learner copy covering recurring errors and useful solving strategies.
- [x] Render My Writing Errors. (`features/study/improvement-lab/MyWritingErrors.jsx`)
- [x] Render Methods & Shortcuts. (Quant `PlannedSection`; personalized feed deferred to GQR-S6)
- [x] Render Approaches & Patterns. (Reasoning `PlannedSection`; personalized feed deferred to GQR-S6)
- [x] Give each section an independent loading, empty, and error state.
- [x] One section failure must not hide the others. (`SectionBoundary` per section)

### English preservation

- [x] Continue using `GET /api/study/practice/english/error-lab`. (`useErrorLab` unchanged)
- [x] Do not rename or repurpose `ewp_error_lab`. (read model untouched)
- [x] Preserve owner scope, feedback-release gate, invalidation handling, and reclassification behavior. (no backend read-model change; only the learner-facing framing moved)

**Validation pending:** live browser walk of the canonical route, the `error-lab` → `improvement-lab` redirect, and independent per-section states.

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

- [ ] No direct learner table reads.
- [ ] No new authenticated/anon RLS read policy for governed strategy content.
- [ ] Service-role server projection only.
- [ ] Strategy and link verification are conjunctive.
- [ ] Active state checked at read time.
- [ ] Governance fields stripped in backend code.
- [ ] Attempt ownership checked before review response.
- [ ] Submitted-state gate preserved.
- [ ] Optional strategy failure does not break core review.
- [ ] No question-to-question leakage.
- [ ] No subject-to-subject leakage.
- [ ] Content Studio remains governance authority.

---

## Cross-cutting compatibility checklist

- [ ] Existing explanation fields remain unchanged.
- [ ] Missing `solution_strategies` is treated as `[]`.
- [ ] Non-Quant/Reasoning questions receive `[]`.
- [ ] Regular and generated mocks use the same contract.
- [ ] Existing question-type renderers do not need subject-specific copies.
- [ ] Existing English Error Lab consumers continue to work through old-route compatibility.
- [ ] No planner, mastery, Calculation Gym, or current-affairs behavior changes in these PRs.

---

## Status synchronization

Every delivery PR must update:

- [ ] the affected row in this checklist;
- [ ] the corresponding row or note in `docs/status/career-copilot-checklist.md`;
- [ ] the architecture contract when a governed decision changes;
- [ ] PR body with changed files, tests run, migrations, operator steps, and deferred scope;
- [ ] Graphify outputs only when the repository's normal Graphify workflow requires it.

Do not mark a row MERGED / CODE PRESENT from planned text alone. Do not mark live/operator validation complete from mocked frontend tests or static migration inspection.
