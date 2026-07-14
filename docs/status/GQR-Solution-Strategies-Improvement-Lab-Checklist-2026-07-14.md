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
| Reasoning strategy authority | CODE-FIXED, VALIDATION PENDING | `app/supabase/migrations/262_reasoning_strategy_authority.sql`, `app/backend/app/study_os/reasoning_strategies.py`, Content Studio Reasoning tab (Library + Review Queue). Authoring/assignment UI still deferred; governed seeded content path landed (GQR-S3b — preflight/seed/proof SQL). |
| Improvement Lab composition | CODE-FIXED, VALIDATION PENDING | GQR-S5 rename + shell landed; personalized Quant/Reasoning feeds wired in GQR-S6 (this slice). |

---

## Delivery sequence

| ID | Slice | Status | Dependency | Required outcome |
|---|---|---|---|---|
| GQR-S0 | Product/architecture decision and checklist | DESIGN LOCKED | None | This document and `solution-strategies-improvement-lab.md` are the source for scope and sequencing. |
| GQR-S1 | Quant Solution Strategy delivery in mock review | CODE-FIXED, VALIDATION PENDING | Existing GQR-Q7 authority | Batched verified-only read, learner projection, review payload field, shared panel, regular/generated-mock tests. No migration. |
| GQR-S2 | Quant content-readiness completion | CODE-FIXED, VERIFY DB (this PR) | GQR-S1 code present; live submitted-review proof depends on seeded content | Seed verified linked Quant content via pending INSERT + audited `cms_review_quant_heuristic` RPC — no migration. Preflight/seed/proof scripts + read-layer regression. Full Content Studio authoring UI deferred (needs new create/edit/activate/link-review RPCs = migration). |
| GQR-S3 | Reasoning strategy authority and Content Studio | CODE-FIXED, VALIDATION PENDING | GQR-S0 | Governed schema, RLS, lifecycle/audit RPC, and the Content Studio Reasoning tab (Library + Review Queue) landed (migration 262). Mirrors the Quant heuristic authority: review-only. Authoring/editing/activation/assignment/link-review + learner-safe preview + seeded content are deferred to GQR-S3b, exactly as GQR-Q7 deferred Quant authoring to GQR-S2. |
| GQR-S3b | Reasoning authoring, assignment, and seeded content | CODE-FIXED, VERIFY DB | GQR-S3 | Governed verified strategy + verified link produced through the existing service-role INSERT + `cms_review_reasoning_strategy` RPC path (preflight/seed/proof SQL; no migration), mirroring GQR-S2. Full Content Studio authoring UI (new create/edit/activate/link-review RPCs = migration) remains a tracked follow-up. |
| GQR-S4 | Reasoning independent-question learner delivery | CODE-FIXED, VALIDATION PENDING | GQR-S3 authority (migration 262) present; live proof needs GQR-S3b content | `reasoning_strategies.strategies_for_questions` (batched, conjunctive verified+active+scope gate, mirrors Quant) + registered in `solution_strategies` aggregator (`_project_reasoning`, `subject_family='reasoning'`); `get_review` already batches it; shared `SolutionStrategyPanel` reused (renders `key_observation`). No migration. |
| GQR-S5 | Rename Error Lab learner page to Improvement Lab | CODE-FIXED, VALIDATION PENDING | GQR-S0; may run after GQR-S1 contract stabilizes | Canonical route, old-route compatibility, renamed header, existing English section preserved. |
| GQR-S6 | Improvement Lab Quant and Reasoning personalized feeds | CODE-FIXED, VALIDATION PENDING | GQR-S1 + GQR-S4 (both merged) | `study_os/improvement_lab.py::build_feed` (bounded owner-scoped submitted-attempt history → verified-only live aggregator projection → per-strategy evidence → wrong-and-recent ranking) + `/api/study/improvement-lab/{quant,reasoning}`; FE `StrategyFeedSection`/`StrategyFeedCard`/`useStrategyFeed` replace the S5 `PlannedSection` placeholders. No migration. Live proof needs seeded verified content (GQR-S2 quant present; GQR-S3b reasoning in flight, PR #996). |
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

**Status:** CODE-FIXED, VERIFY DB (this PR)

### Preflight — `app/supabase/checks/quant_content_readiness_preflight.sql` (read-only)

- [x] Count verified active Quant heuristics. (Greenfield: 0 before seed — migration 243 shipped tables + review RPC only, no content.)
- [x] Count verified Quant question links. (0 before seed.)
- [x] Confirm linked questions are reachable through mock/generated-mock review. (Preflight applies the mock-pipeline `verified/live/published` status gate; mere bank-row existence does not count.)
- [x] Confirm Content Studio can create/edit/activate heuristics or document the governed intake path that does. **Documented:** Content Studio ships review + read only (`/quant-heuristics`, `/{id}`, `/{id}/review`); there is NO create/edit/activate RPC/endpoint. The governed intake path is a **service-role INSERT** into `quant_heuristics` + the existing `cms_review_quant_heuristic` lifecycle RPC to reach verified.
- [x] Confirm Content Studio can create and review question links or document the governed assignment path that does. **Documented:** service-role INSERT into `quant_question_heuristics` + service-role UPDATE of `reviewer_status` (links carry their own status; no separate link RPC in v1).

### Decision

- [x] Skip full Content Studio authoring UI — production-ready verified linked content is producible through the existing governed service-role path; adding create/edit/activate/link-review the governed (RPC-owned-audit) way would require **new RPCs = a migration**, which this readiness/seed PR deliberately avoids. Authoring UI is a tracked follow-up.
- [x] Do not create a new AdminShell/sidebar destination. (No frontend change.)
- [x] Keep heuristic and link reviews separate and conjunctive. (Read authority `heuristics_for_question` already enforces link-verified AND heuristic-verified+active; proven below.)

### Data/operator gate

- [x] Seed or author at least one reviewed Quant strategy for a supported question. — `app/supabase/seeds/quant_heuristic_demo_ssc_cgl.sql` (idempotent; authors pending rows and verifies 2 heuristics through the audited RPC; 1 verified link on the SSC-CGL Quant demo taxonomy).
- [ ] Verify it appears in submitted review. — **BLOCKED on GQR-S1:** this branch proves the data/read-authority gate only; `heuristics_for_question` is not yet wired into the submitted-review payload, so direct helper tests are not submitted-review evidence.
- [x] Move the heuristic or link out of verified state and prove it disappears on the next read. — `app/supabase/validation/validate_quant_heuristic_readiness.sql` (rollback-only; 7 assertions incl. link-rejected, is_active retire, needs_correction).

**VERIFY DB:** run, in order, `checks/quant_content_readiness_preflight.sql` → `seeds/quant_heuristic_demo_ssc_cgl.sql` (with an existing operator `actor_user_id` / `actor_email`) → `validation/validate_quant_heuristic_readiness.sql` against staging. Prior ephemeral evidence predates the review fix and must be rerun.

---

## GQR-S3 — Reasoning strategy authority

**Status:** CODE-FIXED, VALIDATION PENDING
**Landed:** migration `262_reasoning_strategy_authority.sql`, `app/backend/app/study_os/reasoning_strategies.py`,
`app/backend/app/api/content_studio.py` (reasoning-strategies endpoints), Content Studio Reasoning tab
(`ReasoningStrategyLibrary.jsx` + `ReasoningStrategyReviewQueue.jsx`).
**Posture:** mirrors the Quant heuristic authority (GQR-Q7) exactly — review-only. Authoring/assignment
and seeded content are deferred to GQR-S3b (as GQR-Q7 deferred Quant authoring to GQR-S2).

### Schema

- [x] Add `reasoning_strategies`.
- [x] Add `reasoning_question_strategies`.
- [x] Add topic/microtopic scope checks.
- [x] Add stable strategy code uniqueness.
- [x] Add typed strategy values: approach, pattern, elimination, diagram method, set method, trap.
- [x] Add structured `applicability_rule` for internal selection.
- [x] Add method, observation, example, and trap content fields (columns named to match the shared learner DTO).
- [x] Add reviewer lifecycle and active state.
- [x] Add unique question-strategy link.
- [x] Add relevance and independent link reviewer status.
- [x] Add indexes for question, strategy, status, topic, and microtopic.

### Governance

- [x] Enable RLS on every new table.
- [x] Revoke direct anon/authenticated access.
- [x] Grant only deliberate service-role capabilities.
- [x] Add audited review lifecycle RPC (`cms_review_reasoning_strategy`).
- [x] Enforce expected-status CAS.
- [x] Enforce expected-`updated_at` CAS.
- [x] Require a review reason (8–500 chars).
- [x] Test transition matrix and stale-content rejection (router-layer, `test_content_studio_reasoning_strategies.py`).

### Content Studio

- [x] Add Reasoning Strategy Library inside existing Content Studio.
- [ ] Add draft creation/editing. *(GQR-S3b — migration 262 ships only the review RPC, mirroring GQR-Q7.)*
- [ ] Add activation/retirement. *(GQR-S3b)*
- [ ] Add question assignment. *(GQR-S3b)*
- [x] Add strategy review queue.
- [ ] Add question-link review. *(GQR-S3b)*
- [ ] Add learner-safe projection preview. *(GQR-S3b)*
- [x] No new top-level admin route (Reasoning is a content-type facet in the existing Content Studio surface).

### Initial coverage

Strategy types (`approach`/`pattern`/`elimination`/`diagram_method`/`set_method`/`trap`) support every
independent-question family below; the strategy CONTENT for each is seeded through the authoring workflow (GQR-S3b).

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

- [ ] Fresh migration stack succeeds. *(VERIFY DB — static migration renumbered to 262 after migration 261 landed on `main`; reconcile `SELECT MAX(version) FROM schema_migrations;` before apply.)*
- [ ] RLS/privilege tests pass. *(OPERATOR PENDING — RLS asserted by migration DDL; live proof pending.)*
- [x] Lifecycle and CAS tests pass (router-layer boundary + transition/CAS/reason guards).
- [x] Content Studio tests pass (`ContentStudio.test.jsx` reasoning blocks).
- [x] At least one verified strategy and verified question link can be produced through the governed workflow. *(GQR-S3b — governed service-role INSERT + `cms_review_reasoning_strategy` RPC path; seed + rollback proof below. VERIFY DB.)*

---

## GQR-S3b — Reasoning content readiness

**Status:** CODE-FIXED, VERIFY DB (this PR)

**Posture:** mirrors GQR-S2 exactly. No migration. The governed intake path is a
service-role INSERT into `reasoning_strategies` / `reasoning_question_strategies`
plus the existing `cms_review_reasoning_strategy` lifecycle RPC (migration 262) to
reach verified; the link carries its own `reviewer_status` and is verified by a
service-role UPDATE (v1 has no link RPC).

### Preflight — `app/supabase/checks/reasoning_content_readiness_preflight.sql` (read-only)

- [x] Count verified active reasoning strategies. (Greenfield: 0 before seed — migration 262 shipped tables + review RPC only, no content.)
- [x] Count verified reasoning question links. (0 before seed.)
- [x] Count DISTINCT learner-ready questions under the conjunctive gate (link verified AND strategy verified AND active).
- [x] Confirm those questions are reachable through mock/generated-mock review (mock-pipeline `verified/live/published` status gate).

### Decision

- [x] Skip full Content Studio authoring UI — verified linked content is producible through the existing governed service-role path; adding create/edit/activate/link-review the governed (RPC-owned-audit) way requires **new RPCs = a migration**, which this readiness/seed PR deliberately avoids (exactly as GQR-S2 decided for Quant). Authoring UI is a tracked follow-up.
- [x] Do not create a new AdminShell/sidebar destination. (No frontend change.)
- [x] Keep strategy and link reviews separate and conjunctive.

### Data/operator gate

- [x] Seed at least one reviewed Reasoning strategy + verified link for a **scope-matched** supported question. — `app/supabase/seeds/reasoning_strategy_demo_ssc_cgl.sql` (idempotent; authors pending rows, verifies 2 Coding-Decoding strategies through the audited RPC, 1 verified link on a reachable demo question seeded with the canonical Reasoning `subject_id` + Coding-Decoding `topic_id`; a final postcondition block aborts unless the promised 2 verified strategies + 1 verified scope-matched link exist — checkpost #996 P1/P2).
- [ ] Verify it appears in submitted review. — **BLOCKED on GQR-S4:** the batched `strategies_for_questions()` reader/projection is not landed yet, so submitted-review evidence belongs to the GQR-S4 branch.
- [x] Move the strategy or link out of verified and prove it disappears on the next read. — `app/supabase/validation/validate_reasoning_strategy_readiness.sql` (rollback-only; asserts pending-gate, reason gate, audit row, conjunctive link gate, **scope gate: mismatched-topic / null-scope / cross-subject / inconsistent topic↔microtopic parent all fail closed** while a consistent topic+microtopic pair passes, link-rejected, is_active retire, needs_correction).

**Proof run:** all three scripts executed against a scratch Postgres loaded with migration 262's real tables + `cms_review_reasoning_strategy` RPC — validation prints `ALL PASS` (13 assertions incl. 4 scope negatives + the consistent-pair positive); seed prints `SEED OK` and is idempotent across re-runs and reconciles a pre-existing non-admitted question; preflight reports `READINESS: PRESENT — 1`. The scope gate now mirrors `quant_heuristics._canonical_scope_is_quant` including the microtopic `parent_topic_id = topic_id` consistency requirement (checkpost #996 follow-up).

**VERIFY DB:** run, in order, `checks/reasoning_content_readiness_preflight.sql` → `seeds/reasoning_strategy_demo_ssc_cgl.sql` (with an existing operator `actor_user_id` / `actor_email`) → `validation/validate_reasoning_strategy_readiness.sql` against staging.

---

## GQR-S4 — Reasoning independent-question delivery

**Status:** CODE-FIXED, VALIDATION PENDING (live proof needs GQR-S3b verified content)

- [x] `app/backend/app/study_os/reasoning_strategies.py` gains the batched reader (existed for review; now read-authority too).
- [x] Implement batched verified-only `strategies_for_questions()` (one link + one strategy query; conjunctive verified+active+scope gate; embedded bank-question scope; fail-soft).
- [x] Project into the shared learner DTO (`_project_reasoning`, `subject_family='reasoning'`, explicit allowlist).
- [x] Add Reasoning as a source in `solution_strategies.py`.
- [x] Do not modify the mock review response loop again beyond source registration (`get_review` already batches the aggregator — untouched).
- [x] Reuse `SolutionStrategyPanel` without a Reasoning-specific fork.
- [x] Verify `key_observation` and elimination/trap content render (FE test).
- [x] Verify Quant and Reasoning strategies cannot cross-leak (scope gate blocks a Reasoning-scoped strategy on a Quant question and vice-versa; aggregator per-subject isolation test). A single canonical question has ONE topic scope, so mixed-family content on one real question is impossible by construction — the contract requires cross-source ISOLATION, not co-appearance.
- [x] Keep non-verbal Reasoning out of scope.
- [ ] Live/operator proof that a verified Reasoning strategy + verified link renders in submitted review — **blocked on GQR-S3b** (no governed authoring/seed for Reasoning yet, exactly as GQR-S1 waited on GQR-S2).

Tests: `app/backend/tests/study_os/test_reasoning_strategies_delivery.py` (11 — batched one-query, gate, scope/cross-subject block, isolation, projection-strip, aggregator multi-source composition with per-subject isolation, fail-soft, `get_review` attach); FE `SolutionStrategyPanel.test.jsx` (+1 reasoning case).

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
- [x] Render Methods & Shortcuts. (GQR-S6: real Quant `StrategyFeedSection`)
- [x] Render Approaches & Patterns. (GQR-S6: real Reasoning `StrategyFeedSection`)
- [x] Give each section an independent loading, empty, and error state.
- [x] One section failure must not hide the others. (`SectionBoundary` per section)

### English preservation

- [x] Continue using `GET /api/study/practice/english/error-lab`. (`useErrorLab` unchanged)
- [x] Do not rename or repurpose `ewp_error_lab`. (read model untouched)
- [x] Preserve owner scope, feedback-release gate, invalidation handling, and reclassification behavior. (no backend read-model change; only the learner-facing framing moved)

**Validation pending:** live browser walk of the canonical route, the `error-lab` → `improvement-lab` redirect, and independent per-section states.

---

## GQR-S6 — Personalized Improvement Lab feeds

**Status:** CODE-FIXED, VALIDATION PENDING (backend `study_os/improvement_lab.py` + `/api/study/improvement-lab/{quant,reasoning}`; FE `StrategyFeedSection`/`StrategyFeedCard`/`useStrategyFeed`; no migration)

### API

- [x] Add server-owned Quant learner feed (`GET /api/study/improvement-lab/quant`).
- [x] Add server-owned Reasoning learner feed (`GET /api/study/improvement-lab/reasoning`).
- [x] Authenticate and owner-scope every read (`get_current_user`; `.eq("user_id", …)`).
- [x] Bound recent attempt and response reads (`_MAX_ATTEMPTS=30`, `_MAX_RESPONSES=2000`, `_MAX_QUESTIONS=500`, `_MAX_ITEMS=50`).
- [x] Consider only submitted attempts (`.eq("status","submitted")`).
- [x] Batch strategy reads (single aggregator call over the deduped question set).
- [x] Deduplicate by strategy ID (per-strategy accumulator).
- [x] Keep verification and active-state checks live (via the verified-only aggregator — no frozen copy).

### Evidence summary

- [x] `times_seen`.
- [x] `wrong_count`.
- [x] `correct_count`.
- [x] `last_seen_at`.
- [x] bounded recent source question IDs (`_MAX_SOURCE_QUESTIONS=5`).

### Ranking

- [x] Wrong-associated strategies before correct-only strategies.
- [x] Recent before stale.
- [x] Relevance before stable name/ID tie-break.
- [x] Deterministic results for identical evidence (staged stable sorts; final tie-break on id).

### Boundaries

- [x] Do not dump the full canonical library (only strategies for attempted questions).
- [x] Do not add a saved-strategy table in v1.
- [x] Do not write planner tasks.
- [x] Do not infer target solve time.
- [x] Withdrawn content disappears on the next read (live aggregator; never frozen).

**Checkpost #999 hardening (2 rounds):** (F1) feed reads no longer swallow errors. Attempts/responses reads propagate; the shared strategy readers + aggregator gained a `strict=` mode (default fail-soft preserved for the mock-review consumer per §11.7; the standalone feed calls `strategies_for_questions(..., strict=True)` so a strategy/link-table outage also propagates). The endpoints map any propagated failure to **HTTP 502** so the client shows its error state; genuine empty stays 200. (F2) the bounded window is now a genuinely recent one: responses are fetched **per attempt** walking the stable recency-ordered attempts (`submitted_at` desc, id tie-break) — not a single unordered `.in_().limit()` that truncates arbitrarily — then the question window is `last_seen_at` desc / id tie-break; `source_question_ids` recent-first; per-attempt cap logs when saturated. (F3) per-strategy `relevance` aggregates the STRONGEST across links (min rank), order-independent. (F4) card renders `worked_example`.

**Codex #999 review (P2×2):** unattempted rows (`is_correct IS NULL`, skipped questions) are excluded from evidence (mirrors the §3.3 exclude-unanswered convention — no recommendations for untouched questions); and the aggregator gained a `subjects=` restriction so a subject-scoped feed reads ONLY its own source — an unrelated subject's outage can no longer 502 a healthy feed (independent-section contract).

Tests: `app/backend/tests/study_os/test_improvement_lab.py` (19 — scope, evidence, verified-only, not-a-library-dump, subject filter, wrong-first ranking, governance strip, empty, owner/response + strategy read-failure propagates, strongest-relevance both orders, recent-first sources, determinism, recency-bounded-window overflow both orders, skip-unanswered, unrelated-source-outage isolation, endpoint wiring + owner/strategy 502), FE `StrategyFeedSection.test.jsx` (4, incl. worked_example) + `ImprovementLab.test.jsx` updated.

- [ ] Live/operator proof that a real seeded strategy appears in a learner's feed — pending seeded verified content (Quant seed = GQR-S2; Reasoning seed = GQR-S3b, PR #996).

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
