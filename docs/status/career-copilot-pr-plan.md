# Career Copilot remaining-work PR plan

> **ARCHIVED DISPATCH PLAN — 2026-06-21 origin. Do not use as a live execution guide.**
>
> This document was last planned against `main @ 2308b31` (2026-06-21). The dispatch instructions below are stale: I3/I4/I5/I7/I8-A/B/C/I9/P-slice-1/P-slice-2/P-slice-1c and many other items described as "in review", "gated", or "ready to dispatch" are already merged. Following the lane instructions in this file risks re-opening work that is complete or dispatching stale preconditions.
>
> For the current open-work picture, see the **Current Execution Plan** section immediately below, then `docs/status/career-copilot-checklist.md` as the authoritative source of record. The historical dispatch details are preserved beneath for reference.

---

## Current Execution Plan — as of 2026-07-01 (`main @ b9bd9d7b`)

### Merged and closed (do not dispatch)

| Arc | Merged via | Status |
|---|---|---|
| I8-A/B/C Exam Management consolidation | PRs #755/#757/#759 | MERGED |
| I9 Cycle activation checklist | PRs #791/#794/#798/#801 | MERGED |
| I6 Cycle-setup gate document | PR #761 | MERGED |
| I7 KG exam lane removal | PR #747 | MERGED |
| I5 PYQ question pagination | PR #751 | MERGED |
| P-slice-1 frequency semantics + snapshot foundation | PR #767 | MERGED |
| P-slice-2 planner consumption of locked snapshots | PR #773 | MERGED |
| P-slice-1c / P-slice-3 snapshot review atomicity + workbench UI | PR #810 | MERGED |
| EI-worker text-extract background worker | PR #811 | MERGED |
| PYQ cycle/phase label fix | PR #812 | MERGED |
| IA design-lock document | PR #752 | MERGED |
| Backend management read model | Phase 0 PR | MERGED |
| Lane B Exam Governance cleanup (all) | PRs #755-#759 + earlier | MERGED |

### Open / next (as of 2026-06-30)

| Priority | Item | Gate |
|---|---|---|
| **Immediate** | Score Snapshot lock-authority correctness | PLANNED — scoped issue/contract required; see note below |
| **Immediate** | Operator validation wave: PYQ onboarding (#812), Score Snapshots (#810), text extraction (#811) | Deploy exact main SHA first |
| High | J1 Advanced Repair scoping contract | `docs/status/Advanced-Repair-Scoping-Gate-2026-06-29.md` DRAFT — OPERATOR APPROVAL PENDING |
| High | J1 Advanced Repair scoping implementation | J1 contract operator approval |
| High | J2 Manage Exam operational editors | Contract-first; I8-B and I6 gates cleared |
| High | Transient retry/backoff for text-extract worker | Issue #813 |
| High | Stuck-processing diagnostics and reset | Issue #542 |
| Medium | P2 cognitive-demand classification (metadata-only) | Contract-first; independent of Track C — see note |
| Blocked | A-PR4/A-PR5/Track C | Lane A clean gate (FF_MOCK_MASTERY_WRITES=live) |
| Blocked | J3 schema/domain redesign | Contract-first; I8 gates cleared |

**Score Snapshot lock-authority note:** Two distinct gaps require two explicit contract decisions before implementation: **(A) Stale-model guard:** the `reviewed→locked` transition must compare the candidate row's `model_version` against the server-owned current `MODEL_VERSION` constant and reject stale-model rows — independently of whether any current-model locked row exists. **(B) Superseded-current-model guard:** among rows for the same business scope `(exam_id, exam_phase_id, topic_id)` at the current model version, the planner uses the latest `computed_at` locked row; the RPC should prevent locking an older `computed_at` row when a newer locked row already exists for the same scope. Do not combine these into a single `(exam_id, exam_phase_id, topic_id, model_version)` tuple — that conflates the two checks. The scoped issue/contract must define: server-owned current-model authority; business scope key; supersession ordering; whether only `reviewed→locked` is guarded; exact error tokens and race-safe RPC behavior; historical-review policy for stale-model rows. Snapshot lifecycle: `draft→reviewed|rejected`, `reviewed→locked|rejected|draft`, `locked→reviewed`, `rejected→draft` — no `pending` status.

**P2 classification gate note:** Reviewed metadata-only classification (cognitive demand per PYQ question, no mock-selection weighting) is independent of Track C. It may proceed once its own contract is approved. However, no classification output may feed mock-selection, weighting, or personalization before Lane A clears the text-MCQ feedback-loop gate (`FF_MOCK_MASTERY_WRITES=live`).

### Parallelism constraints (unchanged)

- Never fan out to parallel agents work touching `AdminShell.jsx`, `adminRoutes.jsx`, `ExamWorkspace.jsx`, `ExamIntelligence.jsx`, or route/title tests simultaneously.
- J2 sub-steps are serial within a single agent.
- No new top-level surface unless it removes ≥ 2 existing peers.

---

## Historical dispatch plan (2026-06-21 origin — reference only)

The following lanes were written against `main @ 2308b31`. They are preserved for context and decision-record only.

This plan decomposes the remaining Career Copilot work into small PRs that can
be assigned to simultaneous agents without overlapping write scopes. Status
terms come from `docs/status/career-copilot-checklist.md`.

## Parallelization rules

1. Each PR owns only the files listed in its **write scope**. If an agent needs a
   file outside that scope, it must stop and split or re-plan the PR.
2. Checklist updates are allowed in every PR, but keep them to the rows touched
   by that PR.
3. Do not combine backend validation gates, frontend cleanup, and UX redesign in
   the same PR.
4. Operator-only tasks produce dated evidence docs; they do not edit runtime
   code unless a separate implementation PR is opened.
5. `FF_MOCK_MASTERY_WRITES=live`, A-PR4/A-PR5, and Track C remain blocked until
   the validation gate in Lane A passes.

## Lane map

| Lane | Can run now? | Blocking relationship | Primary owner |
|---|---:|---|---|
| A. Mock Engine validation gate | Yes, operator-led | Blocks `FF=live`, A-PR4/A-PR5, Track C | Operator / backend validator |
| B. Exam Governance cleanup | Yes | Independent of Lane A | Frontend cleanup agent |
| C. Exam workspace setup/timeline UX | Yes, after design lock | Independent of Lane A/B if scoped to SetupPanel | Frontend UX agent |
| D. Document readiness identity/status audit | Yes | May feed Lane C or a backend fix later | Backend+frontend auditor |
| E. Backend CI audit sequencing | Yes | Independent infrastructure PR | CI/backend infra agent |
| F. Live-DB tails | Yes, operator-led | Does not block code cleanup unless evidence changes status | Operator |
| G. Track C / personalization expansion | No | Waits on Lane A clean gate | Backend+frontend feature agents later |
| H. English Writing Practice | EWP-1 starts after architecture lock (#819 merge); EWP-5 mastery live blocked on Lane A gate | Architecture lock (#819) gates EWP-1; EWP-5 mastery live blocked on Lane A gate | Backend + frontend agents |

## Lane H — English Writing Practice

Architecture contract: `docs/architecture/english-writing-practice.md`
Checklist: `docs/status/career-copilot-checklist.md` § English Writing Practice

### Parallelization within Lane H

EWP-1 must land first. EWP-2 (deterministic API) and EWP-2B (evaluator worker) may be developed concurrently after EWP-1; both must land before EWP-3, EWP-4, EWP-5. Within EWP-3 onward, backend and frontend work can be parallelised across separate agents as long as the API contract from EWP-2 is respected. EWP-5 mastery live writes remain blocked on the Lane A gate.

---

### EWP-1 — Architecture contract, schema, constraints, RLS

**Status:** CODE PRESENT IN PR #821 (open) / REVIEW PENDING — migration `205_english_writing_practice_schema.sql` + `version_set_hash` helper + text tests + a Postgres integration suite that runs in CI (backend job provisions Postgres + `EWP_PG_DSN`). Validated against Postgres 16. OPERATOR PENDING: run the live `select max(version)::int+1 from schema_migrations` to confirm/rename the number before merge; staging apply.

**Goal:** Land the full schema with RLS, constraints, state-machine tests, and hash test vectors. No aspirant-facing UI. No mastery live writes. Migration number must come from `select max(version)::int + 1 from schema_migrations`.

**Write scope:**

```
docs/architecture/english-writing-practice.md        (already present — no further edits in this PR)
docs/status/career-copilot-checklist.md              (update EWP-1 row)
docs/status/career-copilot-pr-plan.md                (update EWP-1 row)
app/supabase/migrations/205_english_writing_practice_schema.sql
app/backend/app/study_os/writing_practice/__init__.py
app/backend/app/study_os/writing_practice/version_set_hash.py   (shared helper; EWP-2 consumes it)
app/backend/tests/study_os/test_writing_schema.py
app/backend/tests/study_os/test_version_set_hash.py
```

**Migration must include:**

1. Seed English Language subject → topic → microtopic hierarchy (§3 of architecture doc). Each `topics` row (level='microtopic') must use an explicit hardcoded UUID constant or a UUIDv5 value derived from a fixed namespace + deterministic slug. `gen_random_uuid()` is not permitted — it is non-deterministic and will produce different values on each migration run, breaking idempotency and re-run safety.
2. `writing_rubrics`
3. `writing_prompts` with reviewer lifecycle constraint
4. `exam_descriptive_requirements` with typed `feedback_release_policy` columns and constraints
5. `writing_sessions` with `projection_revision`, `feedback_released_at`, `evaluation_outcome`, `feedback_release_policy` columns
6. `writing_session_units` with `unique(session_id, unit_number)`, `unit_constraints` JSONB
7. `writing_unit_versions` with `content_hash`, `submission_kind`, `unique(unit_id, version_number)`
8. `writing_evaluations` with `evaluation_revision` envelope model, stage-specific status columns, `unique(unit_version_id, evaluation_revision)`
9. `writing_session_checks` with `version_set_hash`
10. `writing_issue_events` with `lineage_id`, `predecessor_issue_event_id`, `affects_current_state`, UTF-16 span columns
11. `writing_issue_resolution_events` with `successor_issue_event_id`, `unique(issue_event_id, resolving_version_id, evaluator_version)`
12. `writing_issue_projections` with `projection_kind` (`automatic`|`review_override`), `override_review_event_id`, source-kind check, partial `unique(issue_event_id, projection_revision) where kind='automatic'`, partial `unique(override_review_event_id) where kind='review_override'` (§4.11/§4.11a)
13. `writing_issue_review_events`
14. `user_topic_mastery_evidence` with `evidence_tier`, `issue_projection_id`, `evidence_op`, `review_event_id`, `supersedes_evidence_key`, `evidence_key` + `unique(evidence_key)` (§4.12b)
15. `writing_evaluation_jobs` with `generation`, `unique(evaluation_id, job_kind, generation)`, active partial unique index, `locked_at` + `claim_token` for lease/fencing (§8.3)
16. `writing_mastery_shadow` with `evidence_key` + `unique(evidence_key)` (§10.1a)
17. `writing_mastery_outbox` with `source_kind` (`evaluation`|`review_correction`), `evaluation_id`/`review_event_id`, `evidence_op`, `mastery_flag_state`, `locked_at`, `idempotency_key` + `unique(idempotency_key)` + the source-kind check constraint (§8.2)
18. `writing_issue_type_microtopic_map` (§4.15): `issue_type`, `microtopic_id references topics(id)`, `map_version`, `is_active`, partial `unique(issue_type) where is_active`, `unique(issue_type, map_version)`; seeded with stable UUIDs; English-subject + `level='microtopic'` validated; service-role writes. The evaluator never supplies taxonomy IDs.
19. `effective_user_topic_mastery_evidence` view/RPC (§4.12d): folds `assert/retract/replace`, honours effective review decision, excludes stale/withdrawn — the ONLY planner/level source
20. `study_tasks` additive columns: `launch_type text`, `launch_entity_id uuid`, `launch_context jsonb`
21. `tier_rank(text) returns int` SQL helper: `recognition→1, correction→2, production→3, retention→4` (§4.12 — never lexical comparison)
22. Immutability triggers (§12.4): `BEFORE UPDATE OR DELETE` raise-exception triggers on `writing_unit_versions`, `writing_issue_events`, `writing_issue_resolution_events`, `writing_issue_projections`, `writing_issue_review_events`, `user_topic_mastery_evidence`, `writing_mastery_shadow` — enforced against `service_role`, not just RLS
23. RLS on all tables (see §12 of architecture doc): explicit owner-select policy per owner-readable table (`writing_sessions`, `writing_session_units`, `writing_unit_versions`, `writing_session_checks`, evaluations + issue tables); service-role-only (no client allow policy) for `writing_issue_review_events`, `user_topic_mastery_evidence`, `writing_evaluation_jobs`, `writing_mastery_shadow`, `writing_mastery_outbox`; `writing_issue_type_microtopic_map` deliberate read policy recorded (§4.15)
24. RLS verification: every new table must have RLS enabled and a deliberate policy decision recorded. Owner-select tables get an explicit owner policy (see §12.1 table). Service-role-only tables (§12.2) intentionally have NO client allow policy (`USING (false)` or no policy) — this is the correct, documented state for them, not the zero-policy defect. The zero-policy defect applies only to tables that should be owner-readable but lack a policy.

**Tests must include (scope revised 2026-07-01 — schema-level only; runtime-state contracts moved to EWP-2):**

EWP-1 lands the *schema*, so its tests prove schema/constraint/RLS behaviour, not runtime state-machine logic. The following are EWP-1's contract (all present):
- Fixed-input `version_set_hash` fixture with pinned SHA-256 digest (§4.5a). Clients consume, never compute (AGENTS.md EWP-3) — backend vector test; the API integration assertion lands with the endpoint in EWP-2.
- `content_hash` for blank version: enforced by `writing_unit_versions_blank_ck` (empty text + `SHA-256('')` + zero word count); behavioural test present.
- Review-override projection: a `review_override` row inserts alongside `automatic` at the same `projection_revision` (partial unique indexes) — behavioural test present.
- RLS: wrapped-role test that a non-owner authenticated user and anon read zero owned rows; owner cannot read an effectively-invalidated issue/resolution/projection; the fold view is service-role-only.
- **Immutability triggers:** `service_role` UPDATE and DELETE both fail on every immutable table (§12.4) — parametrized behavioural test present.
- Constraint/domain rejection: value domains, key formats, lease shapes, causal-chain corrections, cross-user supersession.

**Moved to EWP-2 (runtime logic, not schema — enforced by the finalizer / API, not by DDL):**
- Unit state-machine allowed/forbidden transitions (learning + exam) — the DB CHECK constrains the *set* of states; the *legal transitions* are owned by `finalize_writing_session` (EWP-2).
- Session rollup incl. `evaluation_failed`/`evaluation_incomplete` (§4.3b) and session-level outcome monotonicity (§9.1a) — finalizer behaviour (EWP-2).
- `unit_constraints` Pydantic validation (valid accepted / unknown key rejected / `max_words < min_words`) — backend model validation (EWP-2).

**Does not include:** API endpoints, frontend, mastery writes, evaluator integration, and the runtime-state tests listed above.

---

### EWP-2 — Deterministic practice API

**Status:** PLANNED — blocked on EWP-1 merged

**Goal:** implement the practice runtime API with deterministic (Stage 1) evaluation only. No LLM calls. Returns immediate feedback on word count, required-word presence, sentence count, duplicates, and empty submissions.

**Tests must include (moved here from EWP-1 — runtime-state contracts):** unit state-machine allowed/forbidden transitions for learning + exam modes; session rollup incl. `evaluation_failed`/`evaluation_incomplete` (§4.3b) and outcome monotonicity (§9.1a) via `finalize_writing_session`; `unit_constraints` Pydantic validation (valid accepted / unknown key rejected / `max_words < min_words`); the `version_set_hash` API integration assertion (endpoint returns the backend-computed digest).

**Write scope:**

```
app/backend/app/study_os/writing_practice/
  __init__.py
  sessions.py          (session create/read/resume)
  units.py             (unit submit, rewrite submit)
  evaluation.py        (Stage 1 deterministic checks)
  version_set_hash.py  (shared hash helper — LANDED in EWP-1; EWP-2 consumes it)
  session_finalizer.py (finalize_writing_session — single owner of rollup)
  coverage_checker.py  (required-word coverage session check)
  mastery_shadow.py    (shadow-only mastery evidence emission, FF-gated)
app/backend/app/api/writing_practice.py
app/backend/tests/study_os/test_writing_practice_api.py
app/backend/tests/study_os/test_session_finalizer.py
app/backend/tests/study_os/test_coverage_checker.py
docs/status/career-copilot-checklist.md
```

**API endpoints:**

```
POST /api/study/practice/english/sessions
  body: { prompt_id, study_task_id? }
  returns: session with units, prompt, constraints

GET  /api/study/practice/english/sessions/{id}
  returns: full session state for resume

POST /api/study/practice/english/sessions/{id}/units/{unit_number}/submit
  body: { answer_text, client_word_count, version_number? }
  runs Stage 1 deterministic checks immediately
  enqueues writing_evaluation_jobs row for Stage 2 (consumed by EWP-2B worker)
  returns: evaluation stub with deterministic_result
```

The submit endpoint only *enqueues* the Stage 2 job. The worker that consumes it is delivered in **EWP-2B** (below). EWP-2 and EWP-2B may be developed concurrently but EWP-2B must merge before EWP-3 (issue cards) and EWP-4 (Error Lab), which depend on populated issue/projection data.

```

POST /api/study/practice/english/sessions/{id}/units/{unit_id}/reopen
  body: { expected_latest_version_id, reason }
  preconditions: §7.2 of architecture doc
  returns: updated unit state

GET  /api/study/practice/english/sessions/{id}/evaluations/{evaluation_id}
  returns: current evaluation state (poll or SSE)

GET  /api/study/practice/english/error-summary
  returns: user's recurring issues from writing_issue_events, grouped by microtopic
```

**Stale evaluation contract:** implement §8 of architecture doc exactly. Worker transaction must lock unit row, verify hash, check latest version, and conditionally apply side effects.

**Mastery evidence:** shadow mode only, behind `FF_WRITING_MASTERY_WRITES`. Does not touch `user_topic_mastery`.

**Mission-control:** extend the mission-control response to compute `action_url` and `action_label` from `study_tasks.launch_type + launch_entity_id`.

**Does not include:** LLM evaluation worker (EWP-2B), frontend shell, Grammar Lab, Error Lab.

---

### EWP-2B — Stage 2/Stage 3 evaluator runtime

**Status:** PLANNED — blocked on EWP-1 merged (concurrent with EWP-2; must merge before EWP-3/EWP-4)

**Goal:** the asynchronous language (Stage 2) and rubric (Stage 3) evaluator pipeline that consumes `writing_evaluation_jobs` and produces issue events, lineage, resolution events, and projections. Without this PR the jobs EWP-2 enqueues have no consumer and EWP-3/EWP-4 have no data.

**Write scope:**

```
app/backend/app/study_os/writing_practice/
  evaluator_worker.py    (job sweeper + SELECT ... FOR UPDATE SKIP LOCKED claiming)
  language_evaluator.py  (Stage 2 LLM call, structured-output schema + validation)
  rubric_evaluator.py    (Stage 3 dimension scoring; confidence gating)
  issue_pipeline.py      (issue event insert, lineage assignment, resolution events)
  projection.py          (writing_issue_projections insert, race-safe count §6)
  mastery_outbox.py      (outbox row creation with pinned mastery_flag_state §8.2)
  recovery.py            (generation+1 recovery, language_status compare-and-set)
app/backend/tests/study_os/test_evaluator_worker.py
app/backend/tests/study_os/test_language_evaluator_validation.py
app/backend/tests/study_os/test_issue_lineage.py
app/backend/tests/study_os/test_projection_race.py
app/backend/tests/study_os/test_mastery_outbox.py
docs/status/career-copilot-checklist.md
```

**Must implement (architecture references):**

- Job claiming with `SELECT ... FOR UPDATE SKIP LOCKED` (§8.3); no two workers claim one job
- Structured evaluator output validation against the Stage 2 schema (§5.3); reject and retry malformed responses
- Stale evaluation contract (§8.1): recompute `sha256(stored_text)`, version-number check, LLM call outside any open DB transaction, then short locking/write transaction
- Issue lineage + resolution event creation (§4.8a, §4.9); evaluator-referenced IDs validated against `active_prior_issues` / `resolved_prior_lineages`
- Projection insertion with race-safe counting (§6): advisory lock or SERIALIZABLE
- Mastery outbox row with pinned `mastery_flag_state` (§8.2); `off` creates no row
- Permanent-failure handling: `terminal_partial` mapping (§4.6a-1), `deterministic_only` outcome, recovery via `generation + 1`
- Retry accounting owned by `writing_evaluation_jobs`, not the evaluation row
- Atomic job acknowledgement: claimed job `status='done'` set in the SAME transaction as all evaluation side effects (§8.1 step 13); replay guard checks already-terminal evaluation before re-processing
- Canonical lock order (§8.0): session first, then ALL required units ascending (not just the target), before entering the finalizer — on evaluator, reopen, submission, recovery paths
- Evaluation-job lease + fencing (§8.3): `locked_at`/`claim_token`, stale-`running` sweeper, attempts/max-attempts, and a fencing re-check of `claim_token` in the final write transaction so an expired slow worker cannot commit after reclaim
- Evaluator returns `issue_type` only; backend resolves canonical microtopic via `writing_issue_type_microtopic_map` and validates subject/level/active before insert (§5.3)
- Review-correction pipeline (§4.12c): serialized per-issue processing, full transition matrix (assert/retract/replace/re-assert), `supersedes_evidence_key` points to the currently-effective row, review-override projection (§4.11a)
- Corrections independent of the current flag: correction inherits the superseded row's `mastery_flag_state`; a `retract` is emitted even when the flag is now `off`
- Effective-evidence fold `effective_user_topic_mastery_evidence` (§4.12d) is the only planner/level source
- Shadow/live worker transaction writes evidence + shadow row + outbox `done` atomically (§8.2)
- Mastery outbox claiming + lease-based recovery for stuck `processing` rows (§8.3)

**Tests must include:** crash-after-commit/before-ack regression (job not double-applied); crash-during-LLM-call → job reclaimed and completes once; lease-expiry double-worker fencing (only current owner commits); lock-order/no-deadlock (session→all-units-ascending); malformed-evaluator-response rejection; projection race-safety; review transition matrix incl. `invalidated→confirmed` re-assert and `reclassified→confirmed` restore; correction emitted while flag is `off`; effective-evidence fold nets a retracted `production` so level does not inflate; mastery-mode pinning; taxonomy-mapping rejection of invalid issue types.

**Stage 3 (rubric)** is included here for the dimensions used by sentence/paragraph drills. Descriptive-exam rubric extensions are scoped with EWP-7.

**Does not include:** frontend, planner task generation, live mastery writes.

---

### EWP-3 — Sentence Builder and rewrite UI

**Status:** PLANNED — blocked on EWP-2 + EWP-2B merged

**Goal:** five-sentence construction interface with word chips, per-sentence issue cards, mandatory rewrite, before/after diff, and session resume.

**Write scope:**

```
app/frontend/src/pages/study/practice/english/
  EnglishPracticeShell.jsx
  SentenceBuilder.jsx
  SentenceIssueCard.jsx
  RewriteEditor.jsx
  WordChips.jsx
  BeforeAfterDiff.jsx
app/frontend/src/routes/appRoutes.jsx              (add /app/study/practice/english/:sessionId)
app/frontend/src/pages/study/StudyHome.jsx         (wire action_url from mission-control)
app/frontend/src/__tests__/SentenceBuilder.test.jsx
docs/status/career-copilot-checklist.md
```

**UI contract:**

- Five independent sentence inputs, not a single textarea
- Word chips show required words; used words are visually distinguished
- `words_used: N/5` counter derived from client-side tokenisation (server validates on submit)
- Session autosave: answer text preserved in sessionStorage keyed by `sessionId + unitNumber`
- Issue cards display: original text, highlighted span, rule explanation, suggested correction, rewrite input
- Rewrite input guards against submitting unchanged span text (client-side warning; server validates)
- Before/after diff after successful rewrite: word-level diff, additions in green, deletions in strikethrough
- Loading, empty, and error states required (four-state `useApiCollection` contract)
- Exam mode: no issue display until `feedback_released_at` is reached

**Route:** mounted under `StudyShell`, inside `RouteErrorBoundary`. Not through `AttemptShellRouter`.

---

### EWP-4 — Grammar Lab and Error Lab

**Status:** PLANNED — blocked on EWP-2 + EWP-2B merged (can parallelize with EWP-3)

**Goal:** topic-specific grammar drills and Error Lab showing recurring issues linked to Grammar Lab.

**Write scope:**

```
app/frontend/src/pages/study/practice/english/
  GrammarDrill.jsx
  GrammarTopicNav.jsx
  ErrorLab.jsx
  ErrorLabIssueCard.jsx
  GrammarExerciseRenderer.jsx
app/backend/app/study_os/writing_practice/grammar_drill.py
app/backend/app/api/writing_practice.py            (add Grammar Lab endpoints)
app/backend/tests/study_os/test_grammar_drill.py
docs/status/career-copilot-checklist.md
```

**Grammar drill exercise types:** identify error / choose corrected sentence / rewrite / construct / reconstruct (scrambled sentence). Each type maps to a distinct `exercise_type` value in `writing_prompts`.

**Error Lab:** reads `writing_issue_events` via API. Displays recurring issues grouped by `microtopic_id`. Each issue card links to the relevant Grammar Lab topic. Invalidated issues are omitted or shown with `withdrawn` marker.

**Shadow evidence:** grammar drill completions emit source-neutral `user_topic_mastery_evidence` (raw evidence) + `writing_mastery_shadow` delta rows. Canonical aggregation into `user_topic_mastery` stays disabled in shadow (§10.1 locked contract). Evidence IS written in shadow so the EWP-5 planner can read it.

---

### EWP-5 — Planner integration and mastery projection

**Status:** PLANNED — blocked on EWP-2 merged; mastery live writes blocked on Lane A gate

**Goal:** planner generates writing tasks; mission-control routes to sessions; shadow-to-live promotion path validated.

**Write scope:**

```
app/backend/app/study_os/planner.py                (add writing task types, level gating)
app/backend/app/study_os/mission_control.py        (compute action_url from launch_type)
app/backend/app/study_os/writing_practice/
  mastery_shadow.py                                (shadow projection writer)
  mastery_aggregator.py                            (unified aggregator stub, off-by-default)
app/backend/tests/study_os/test_writing_planner.py
app/backend/tests/study_os/test_mastery_shadow.py
docs/status/career-copilot-checklist.md
```

**Mastery safety:** `FF_WRITING_MASTERY_WRITES` follows §10 of architecture doc exactly. Live writes remain blocked until:
1. Lane A mock mastery gate clears
2. Shadow-to-live promotion gates in §10.3 pass
3. Operator records approval in checklist

**Planner integration:** reads the effective-evidence fold `effective_user_topic_mastery_evidence` (§4.12d) at microtopic granularity — never the raw append-only table, so retracted/replaced evidence cannot drive tasks or level. Evidence is written in shadow per the §10.1 locked contract. Generates `sentence_construction`, `grammar_correction`, `vocabulary_in_context` task types with `launch_type = 'english_writing_session'`. During shadow the planner personalizes from the fold directly; it must NOT read writing-attributable `user_topic_mastery` deltas until `live`. Schedules retention retests using `user_topic_mastery.next_revision_at`.

---

### EWP-6 — Paragraph Builder (after EWP-3 evidence pipeline stable)

**Status:** PLANNED — blocked on EWP-3 merged and release gates §16 passed

Five-sentence paragraph editor. Scaffolded slots when `tier_rank(evidence_tier) < tier_rank('production')` for paragraph topics; single textarea after `production` evidence exists for ≥3 topics. (Use `tier_rank`, never lexical string comparison — §4.12.) Outline scratchpad stored as `outline_json` on `writing_sessions`. Not included in EWP-3 to keep the sentence pipeline clean before adding paragraph complexity.

---

### EWP-7 (later track) — Descriptive mock runtime

**Status:** PLANNED — blocked on EWP-6 stable and release gates §16 passed

Extend mock `AnswerBody` with `answer_text`. Add `descriptive` interface mode to `AttemptShellRouter`. Wire existing `answer_text`, `word_count`, autosave, `evaluation_status`, and `rubric_score` columns from M176/M177. Add essay, précis, letter and report configurations in `exam_descriptive_requirements`.

---

## Lane A — Mock Engine validation gate

Goal: prove the already-landed code remediations against live/operator evidence
without flipping `FF_MOCK_MASTERY_WRITES=live`.

### PR #716 — Shadow gate prerequisite hardening — **MERGED**

### PR #718 — Platform-review authority hardening (code-only, prerequisite for A1/A2/A3 clean-state signoff)

Fixes 5 confirmed bugs in `canonical.py::review_mock`:

1. **BUG-A — `review_status` silent mutation:** removed Pydantic default from `review_status`; patch built from `model_fields_set` only so omitted fields are never overwritten.
2. **BUG-B — TOCTOU race:** scoped UPDATE (`id + user_id + source_type`) replaces the single-predicate update; zero-row result triggers 4-case diagnostic.
3. **BUG-C — platform path pollution:** `aggregated_error_types` derivation and breakdown/mastery/regen writes are fully isolated to the manual/imported path.
4. **Denylist → allowlist:** `_PLATFORM_REVIEW_ALLOWED` replaces `_PLATFORM_FORBIDDEN`; future body fields are rejected by default for platform mocks.
5. **FK ordering (seedAttempt.ts):** `resetAttempts` now deletes `mock_tests` compat rows (`mock_attempt_id IN attemptIds`) before deleting `mock_attempts` to avoid FK violations.

PR #718 adds regression coverage for the existing PR #716 correction-task authority guard; it does not modify that guard (`study_os.py`, `mocks.py`, and `mastery_writer.py` are empty diff vs main).

**Write scope (changed files only):**
- `app/backend/app/api/canonical.py`
- `app/backend/tests/study_os/test_mock_review.py`
- `app/frontend/e2e/fixtures/seedAttempt.ts`
- `docs/status/career-copilot-checklist.md`
- `docs/status/career-copilot-pr-plan.md`

### PR #716 — Shadow gate prerequisite hardening (original)

Fixes 6 blocking review findings against the mastery shadow gate:

1. **Correction idempotency (23505):** `_draft_correction_tasks` in `mastery_writer.py`
   and `draft_correction_tasks` in `mocks.py` now handle PostgreSQL 23505 uniqueness
   conflicts idempotently. Migration 181 dedup CTE fixed for `NULL created_at`.
2. **Platform-attempt correction guard:** `POST /api/study/mocks/{id}/correction-tasks`
   returns HTTP 409 (`PLATFORM_ATTEMPT_MANUAL_CORRECTION_FORBIDDEN`) for
   `source_type=platform_attempt` mocks.
3. **`derive_preview` three sections:** redesigned to return `persisted_shadow_decision`,
   `current_read_only_preview`, and `replay_consistency` with zero writes.
4. **Shadow analysis tool redesign:** `shadow-replay` (self-consistency), `live-audit-compare`
   (canary-only), `tasks-overlap` (with semantic note); correct env vars; real pagination.
5. **Canary plan hardened:** user allowlist made a hard prerequisite; rollback scoped to
   exact canary attempt_ids covering all 5 affected tables.
6. **Status docs:** this file and `docs/status/career-copilot-checklist.md` updated.

### A1 — Scheduler/job visibility evidence

- **Type:** operator evidence doc only.
- **Write scope:** `docs/audits/*scheduler*2026-*.md`, checklist row updates.
- **Do not touch:** `app/backend/app/study_os/*`, migrations, frontend.
- **Work:** capture both scheduler env vars (`ENABLE_SCHEDULER=true` primary gate,
  `DISABLE_SCHEDULER=true` override kill switch), scheduler startup/registration,
  `/api/admin/jobs` payload, manual sweeper run, and pending-job drain.
- **Exit:** checklist scheduler row moves from `OPERATOR PENDING` to either
  verified or code-defect-found. If code defect is found, open a separate A1-fix
  PR with a narrow backend scope.

### A2 — Repeat off/shadow validation evidence

- **Type:** operator evidence doc only.
- **Write scope:** new dated shadow-validation report under `docs/audits/`,
  checklist row updates.
- **Do not touch:** the 2026-06-18 failed report.
- **Work:** prove only answered topics get deltas, classification-enriched
  corrections match, resubmit creates no new shadow rows, compat row exists with
  integral marks, and retry jobs drain.
- **Exit:** if clean, `FF=live` can move from `BLOCKED` to next controlled live
  canary plan. If not clean, file one defect-specific backend PR per root cause.

### A3 — Live canary plan, not implementation

- **Type:** plan/evidence doc only (canary plan exists at `docs/ops/pr8_live_canary_plan.md`).
- **Write scope:** `docs/runbooks/` or `docs/audits/`, checklist row updates.
- **Depends on:** A1 and A2 clean, **AND** the user-allowlist implementation PR merged.
- **Hard prerequisite — not optional:** `FF_MOCK_MASTERY_WRITES` is currently global.
  A live canary MUST be bounded to a named user allowlist before this plan can be
  approved. The allowlist implementation PR (check `user_id` against an explicit
  allow-list before calling `MasteryWriter.process_attempt_sync`) must be merged and
  the allowlist must be non-empty with named consenting users. Rollback is scoped to
  exact canary attempt_ids recorded in pre-canary queries — not a time window.
- **Work:** confirm allowlist implementation merged, populate allowlist, run
  pre-canary queries, flip flag for bounded users, verify post-canary queries against
  success thresholds, attach evidence to PR9.
- **Exit:** only after all success thresholds pass should any expansion of the
  allowlist or full promotion occur. Never flip without allowlist in place.

## Lane B — Exam Governance cleanup — **COMPLETE**

Goal achieved: all console-era leftovers removed; `/console/:exam_id` renders
`ExamActionConsole`; all CL-1b through CL-6b items are CODE PRESENT.

### B1 — De-leak `ExamActionConsole` labels — **MERGED / COMPLETE**

`ExamActionConsole.jsx` imports `humanizeToken` from `operatorChrome.js` and
applies it to all reason/area/gate/verdict-status fallbacks. Regression test:
`ExamActionConsole.identityHygiene.test.jsx`. CL-1b is closed.

### B2 — Remove orphaned console variant and task rail — **MERGED / COMPLETE**

`ExamTaskRail.jsx` deleted. `ExamWorkspace.jsx` carries no `variant="console"`
branch. CL-6 is closed.

### B3 — Remaining console polish PRs — **ALL COMPLETE**

| PR | Status | Evidence |
|---|---|---|
| B3a registry row expansion / dead columns | **COMPLETE** | `ExamListTable.jsx`; CL-2 CODE PRESENT. |
| B3b remove CMS `+ New guided exam` CTA | **COMPLETE** | No guided-exam CTA in `ExamIntelCms.jsx`; CL-3 CODE PRESENT. |
| B3c collapsible lifecycle banner | **COMPLETE** | `AdminSafetyBanner` in `ExamIntelligence.jsx` uses `collapsible defaultOpen={false}`; CL-4 CODE PRESENT. |
| B3d-2 Console Work Queue action hierarchy | **COMPLETE** | `ConsoleWorkQueue.jsx` uses `aria-pressed` for workflow filters; CL-5 CODE PRESENT. |
| B3d-3 Guided Exam Wizard primary-action hierarchy | **COMPLETE** | `GuidedExamWizard.jsx` uses `aria-pressed` for organization-mode selectors; CL-5 CODE PRESENT. |
| B3d-close cross-surface CL-5 closure audit | **COMPLETE** | `docs/reviews/exam-governance-primary-action-audit.md` exists; CL-5 CODE PRESENT. |
| B4 / CL-6b remove dormant console presentation plumbing | **COMPLETE** | `ExamWorkspaceContext.jsx` has no `variant`; `ExamPublishImpact.jsx` deleted; CL-6b CODE PRESENT. |


## Lane C — Exam workspace setup/timeline UX

Goal: clean the chaotic setup workflow without cross-wiring console or CMS.

### C0 — Design lock / component ownership preflight

- **Type:** read-only design doc.
- **Write scope:** `docs/reviews/` or `docs/status/`, checklist row updates.
- **Work:** decide whether to refactor `SetupPanel` in place or introduce a new
  child component such as `PhaseTimelineManager`.
- **Exit:** explicit write scopes for C1-C4.

### C1 — Phase timeline table extraction

- **Type:** frontend refactor.
- **Write scope:** `SetupPanel.jsx`, new component under
  `app/frontend/src/pages/admin/exam-workspace/panels/`, and targeted tests.
- **Do not touch:** documents, syllabus, PYQ, competition, backend.
- **Work:** replace phase boxes with a grouped table that distinguishes
  template vs cycle-bound phases and keeps current create/edit behavior intact.

### C2 — Merge Template Phases and Phases Needing Dates into timeline

- **Type:** frontend UX cleanup.
- **Write scope:** same new timeline component and tests only.
- **Depends on:** C1.
- **Work:** render missing-date rows inline with badges; remove duplicate template
  rendering outside the timeline.

### C3 — Fast date-entry mode

- **Type:** frontend performance/UX.
- **Write scope:** timeline date-entry component and tests only.
- **Depends on:** C1 or C2.
- **Work:** use native `input type="date"` or a focused drawer for dense rows;
  avoid mounting two `DateField`/DayPicker controls per row.

### C4 — Setup mutation governance

- **Type:** frontend governance fix.
- **Write scope:** `SetupPanel.jsx` / extracted setup hooks and tests only.
- **Can run parallel with:** C1 only if C1 owns rendering components and C4 owns
  mutation handlers; otherwise run after C1.
- **Work:** migrate add-phase, phase-date patch, and template promotion to
  `useApiAction`; preserve audit reason requirements and refetch behavior.

## Lane D — Document readiness identity/status audit

Goal: resolve the suspected mismatch between upload/list/document identity,
`extraction_status`, and readiness/console checks.

### D1 — Read-only contract audit

- **Type:** audit doc only.
- **Write scope:** `docs/reviews/` or `docs/audits/`, checklist row updates.
- **Work:** trace `document_assets`, `syllabus_documents`, `document_pages`,
  extraction jobs/status fields, workspace readiness, and console detail.
- **Exit:** one of: no bug; backend-only fix; frontend-only selector fix; or
  coordinated backend+frontend fix.

### D2 — Narrow implementation fix, if D1 finds a bug

- **Type:** implementation, scope chosen by D1.
- **Write scope:** only the files named by D1.
- **Rule:** do not combine with Setup timeline work.

## Lane E — Backend CI audit sequencing

Goal: make backend tests run even when dependency audit findings need attention.

### E1 — CI sequencing PR

- **Type:** infrastructure.
- **Write scope:** `.github/workflows/ci.yml`, backend requirements only if needed,
  checklist row updates.
- **Do not touch:** application code.
- **Work:** preserve `pip-audit` visibility while ensuring `pytest` still runs or
  is reported independently; avoid silent CVE suppression.
- **Tests:** workflow syntax check where available; no app test changes.

## Lane F — Live-DB-only tails

Goal: keep live state separate from code-verifiable status.

Run each as an operator evidence task with no runtime code changes unless a real
code defect is found:

1. Verify/delete `e2e-workspace-exam` prod row.
2. Verify state PSC official/calendar URL backfill.
3. Reconfirm SEBI Grade A only if a future workflow depends on it.

## Lane H — Exam Intelligence P0 bug fixes

Goal: fix the two confirmed runtime failures surfaced in the 2026-06-20 operator screenshot audit.
Evidence doc: `docs/audits/exam-intelligence-gaps-2026-06-20.md`.

These are independent of Lanes A–G and can run now.

### H1 — Fix `syllabus/propose` 404 (BUG-EI-1)

- **Type:** backend bug fix.
- **Write scope:**
  - `app/backend/app/exam_intelligence/syllabus_mapper.py`
  - `app/backend/tests/` — regression test for the propose path
  - checklist row for BUG-EI-1
- **Do not touch:** frontend, migrations, other study-os files.
- **Work:**
  1. Replace `sb.table("document_assets")` with `sb.table("syllabus_documents")` on both occurrences (~line 99 and ~line 503).
  2. Verify the SELECT columns (`id, exam_id, exam_cycle_id`) exist on `syllabus_documents` (migration 031 confirms they do).
  3. Investigate and resolve the duplicate `ProposerError` / `propose_syllabus_mentions` definitions in the file — either deduplicate or verify which copy is the live one.
  4. Add a regression test: mock a `syllabus_documents` row and assert that propose no longer raises 404.
- **Exit:** propose endpoint returns 200 with mention proposals for a known document.

### H2 — Fix `console/exams/{id}` → 500 and readiness.py wrong column (BUG-EI-2)

- **Type:** backend bug fix — **MERGED / CODE PRESENT — PR #750 merged on main. Do not dispatch.**
- **Status: ALREADY DONE on main (PR #750 merged).**
- **What landed:** `load_doc_extraction_counts(strict=True/False)` in `readiness.py` — sources extraction from `document_processing_jobs` (job_type='text_extract', latest job per asset, deterministic by (created_at, id)). `console_detail.py` uses it with `strict=True` (fail-closed). Workspace readiness path uses `strict=False` (fail-soft). Full vocabulary: total/extracted/pending/failed/needs_review/not_started. No `.limit(2000)` or `.limit(5000)`. 58 tests passing. Option B was used (NOT trust_status proxy). See `docs/audits/document-readiness-2026-06-21.md`.

### H3 — EI UX cleanup batch (UX-EI-1 through UX-EI-5)

Run these as a single frontend cleanup PR since they share no state and all live in the exam-intelligence admin surface.

- **Type:** frontend cleanup.
- **Write scope:**
  - `app/frontend/src/features/admin/exam-intelligence/ReviewQueueTable.jsx` — UX-EI-1 raw ID
  - `app/frontend/src/pages/admin/exam-workspace/panels/SetupPanel.jsx` — UX-EI-1 phaseId, UX-EI-5 cycle context label
  - `app/frontend/src/pages/admin/exam-workspace/panels/OverviewPanel.jsx` — UX-EI-3 deduplication
  - targeted tests for affected components
  - checklist rows for UX-EI-1, UX-EI-3, UX-EI-5
- **Do not touch:** backend, migrations, `ExamWorkspace.jsx` workspace shell, `ExamActionConsole.jsx`.
- **Work:**
  - UX-EI-1: Replace `{r.id}` in ReviewQueueTable with a truncated or humanized display; replace `ptError.phaseId` raw render in SetupPanel error with a friendlier label.
  - UX-EI-3: Remove or collapse fields from `OverviewPanel` that are already surfaced in the workspace SmartHeader (exam name, family, slug, type, active).
  - UX-EI-5: Add cycle name/year to the "Phases needing dates" section header so the operator knows which cycle each phase stub belongs to.
- **Depends on:** none; can run parallel with H1 and H2.

## Lane I — Exam Intelligence structural redesign

Goal: address the 23 structural design defects documented in `docs/reviews/exam-intelligence-design-review-2026-06-20.md`.
Items are split by category and blocked relationship. P2 items can run now; P3 items require design decisions first.

### I1 — Collapse redundant data: OverviewPanel and SetupPanel header fields (D1, D2)

- **Type:** frontend cleanup.
- **Write scope:** `OverviewPanel.jsx`, `SetupPanel.jsx` (lines 909–924 only), targeted tests.
- **Do not touch:** `ExamWorkspace.jsx` SmartHeader, backend.
- **Work:** Remove or collapse the "Exam identity" section in `OverviewPanel` (name, slug, type, family already in SmartHeader). Remove or minimize the exam detail block in `SetupPanel` (lines 909–924). Retain OverviewPanel sections that add value beyond the header (readiness per-section detail if not collapsed into header).
- **Depends on:** Operator must confirm which OverviewPanel fields (if any) are not already in SmartHeader.

### I2 — Collapse "Phases needing dates" into main phases list with cycle label (D3)

- **Type:** frontend cleanup.
- **Write scope:** `SetupPanel.jsx` and targeted tests.
- **Note:** Partially absorbed into H3 (UX-EI-5 adds cycle label). Full removal of the duplicate section belongs to Lane C (C2 — merge template phases into timeline).
- **Depends on:** C1 (phase timeline extraction) should land first.

### I3 — PYQ paper overview: replace dropdown with table (F3)

- **Type:** frontend UX improvement.
- **Write scope:** `PyqWorkbenchPanel.jsx`, targeted tests.
- **Do not touch:** backend, `PyqPaperWorkspace.jsx` embedded view, other workspace panels.
- **Work:** Replace flat `<select>` paper picker with a table of papers showing paper year, section, question count, and readiness status. Keep the embedded `<PyqPaperWorkspace>` as the detail view after selection.
- **Depends on:** none.

### I4 — Bulk import: auto-navigate to imported paper after success (F2)

- **Type:** frontend UX improvement.
- **Write scope:** `PyqWorkbenchPanel.jsx`, `BulkImportModal.jsx`, targeted tests.
- **Do not touch:** backend import logic, other panels.
- **Work:** After a successful bulk import response, close the modal and auto-select the first imported paper in the picker/table. Show a brief confirmation of what was imported before closing.
- **Depends on:** none.

### I5 — PYQ question pagination (M3)

- **Type:** frontend — **READY TO DISPATCH (with constraint).**
- **Backend pagination confirmed:** endpoint already supports `paper`, reviewer-status filter, `limit`, `offset`, exact `total`, deterministic question-number ordering. No backend changes required.
- **Write scope:** `PyqPaperWorkspace.jsx`, targeted tests.
- **Do not touch:** other workspace panels, unrelated PYQ routes.
- **Constraint:** must NOT hardcode old routes that I8-A will remove. Before implementing pagination: move supported filters server-side; keep deterministic server ordering; add `source_kind` server filter if required; remove or defer confidence/status sort controls unless globally correct; reset offset on filter/paper changes; clamp page after mutations; show total after filters; refetch after review actions.
- **Work:** Replace `limit=200` with paginated fetching; add page/section navigation in the question list UI.
- **Exit:** 100+ question papers paginate correctly; filter changes reset to page 1; total count visible.

### I6 — Remaining identifier leakage: CMS tables, CompetitionMetrics, Subjects (I3–I5)

- **Type:** frontend cleanup.
- **Write scope:** `ExamIntelCms.jsx`, `CompetitionMetricsTable.jsx`, targeted tests.
- **Do not touch:** backend, `ReviewQueueTable.jsx` (covered by H3), `SetupPanel.jsx` (covered by H3).
- **Work:** Apply `operatorChrome.humanizeToken` to entity `id` columns in CMS tables and the `exam_slug`/`subject_id` columns in Competition and Subjects surfaces.
- **Depends on:** none; can run in parallel with H3.

### I7 — KnowledgeGovernance: remove exam lane (E1)

- **Type:** frontend cleanup — **UNBLOCKED; READY TO DISPATCH.**
- **DQ-1 resolved (2026-06-21):** remove the exam lane/card. Console already owns triage. KG lane adds no unique capability and duplicates existing nav.
- **Write scope:**
  - `app/frontend/src/pages/admin/KnowledgeGovernance.jsx` — remove "Exam truth & planner readiness" lane/card
  - landing-page count/copy update (4 lanes → 3)
  - targeted tests for landing-page lane count and links
  - checklist row for E1
- **Do not touch:** sidebar exam group (deferred to I8-A), KG rename (separate later PR), backend metrics, routing.
- **Work:**
  1. Remove the exam lane block from `KnowledgeGovernance.jsx`.
  2. Update count/copy text from "4 lanes" → "3 lanes" (or equivalent).
  3. Update landing-page tests.
- **Exit:** landing page renders 3 lanes; no exam links appear on KG landing; sidebar exam group unchanged.

### I8 — Exam Management consolidation (E2) — GATED; SERIAL; ONE OWNER

- **Type:** structural redesign — **GATED on IA design-lock document.**
- **DQ-2 resolved (2026-06-21):** old "registry-first cleanup" approach is superseded. One visible Exam Management front door combining Registry + Console purposes. "Console" and "Workspace" must not be peer product choices.
- **CRITICAL: I8-A, I8-B, and I8-C must be serial and owned by one lane/owner. Do NOT fan out to parallel agents.** Shared write scope is too large: `AdminShell.jsx`, `adminRoutes.jsx`, `ExamIntelligence.jsx`, `ExamGovernanceConsole.jsx`, `ConsoleWorkQueue.jsx`, `ExamActionConsole.jsx`, `ExamWorkspace.jsx`, action CTA generation, route/title tests, navigation active-state tests.

#### I8-A — Exam Management front door (GATED — IA design lock)

- **Write scope:** `AdminShell.jsx`, `adminRoutes.jsx`, new `ExamManagement.jsx` (or replacement route), tests.
- **Goal:** One sidebar entry replacing the existing exam group. Family/exam/cycle discovery + triage in one page. Status filters. One row/drill-in action: `Manage exam`. Atomically adds new entry, removes old KG sidebar exam group, and removes visible Registry/Console peer navigation. Adds legacy route compatibility.
- **Redirect strategy:** Add canonical routes first; then change navigation and internal links; then validate all entry points; then convert old visible URLs to redirects; then remove orphaned shells/components only after redirect tests pass. Never create an intermediate 404 state.

#### I8-B — Manage Exam consolidation (GATED — I8-A + IA design lock)

- **Write scope:** `ExamWorkspace.jsx` (or successor), `ExamActionConsole.jsx`, `console_detail.py` (blocker deep-link contract), tests.
- **Goal:** Merge per-exam Console information into the exam-management drill-in. Show blocker, status, next action, and readiness in one selected-exam context. Remove visible "Open console" vs "Advanced workspace" choice. Implement locked deep-link blocker contract (every CTA routes to exact task state: `?tab=syllabus&status=pending`, `?tab=documents&document={id}`, etc.).
- **Blocked on:** IA design lock must choose one canonical readiness authority: Console detail/action queue OR workspace readiness sections OR unified read model.

#### I8-C — Advanced Repair isolation (GATED — I8-A + IA design lock)

- **Write scope:** `AdminShell.jsx` (remove CMS from nav), `ExamIntelCms.jsx` (or successor overflow entry), tests.
- **Goal:** Remove CMS from normal navigation. Expose selected-exam `Manage exam → More → Advanced repair` — scoped to selected exam, permission-gated, explicit warning. Global super-admin recovery may remain but must not be a primary CTA.

### I9 — Guided cycle-setup workflow (F1)

- **Type:** design → implementation (multi-PR) — **ARCHITECTURE LOCKED; IMPLEMENTATION GATED.**
- **Architecture locked (2026-06-21):** Hybrid. (1) Bounded mini-wizard for atomic cycle creation (identity + dates + phase selection + review + save → return to Manage Exam). (2) Persistent 9-step activation checklist resumable across sessions (Cycle details → Phases and schedule → Source documents → Extraction → Syllabus mapping → PYQ readiness → Policy updates → Competition context → Review and activate).
- **Blocked on:** I6 cycle-setup gate document (see §Documentation gates below). Must define, for all 9 steps: completion source, hard/advisory/N-A gate, deep-link target, resume behaviour, empty-state behaviour, selected-cycle behaviour, management-mode/cadence applicability, `AddCycleWizard` decision (reuse/embed/remove), progress derivation (backend-derived vs frontend-composed), manual-mark-complete rules.
- **Do not dispatch I9 implementation until gate document is approved.**

## Lane G — Later expansion after clean gate

Do not dispatch until Lane A exits clean:

1. A-PR4 exposure cooldown.
2. A-PR5 mastery-informed mock selection.
3. Track C question model v2: stimulus/shared passages, media, non-MCQ scoring.
4. Wave 5 PYQ weighting into generated mock mix.

Each of these needs its own preflight to define schema, scoring, and frontend
contract before implementation.

## Lane J — CMS → Manage Exam capability migration (DEFERRED — GATED BY I8)

Do not dispatch until I8-A/B/C are complete.

### J1 — Advanced Repair scoping

- Selected exam scope, selected cycle scope where applicable, search, filters, pagination.
- Explicit "Advanced Repair" warning; permission gate.
- Gated by I8-C.

### J2 — Missing operational editors in Manage Exam

Move normal work out of the generic CMS and into Manage Exam tabs:
topic/microtopic management, alias management, prerequisite editing, historical paper creation, question/option correction, policy flag correction, cycle-specific entity management.

Each capability is its own focused PR. Do not combine them.

### J3 — Schema/domain redesign (CONTRACT-FIRST)

Phase/category competition cutoffs, applied vs appeared candidate counts, mixed-format PDF extraction, evidence-based coverage scoring, structured competition breakdowns. Each needs its own domain contract and potentially schema changes before implementation. Do not interleave with I8 navigation work.

## Documentation gates

These are planning/decision documents, not code PRs. They gate downstream implementation.

### IA design-lock document — CODE PRESENT / pending merge

**Document:** `docs/status/Exam-Management-IA-Design-Lock-2026-06-21.md`  
**Branch/PR:** `docs/exam-management-ia-design-lock` (PR #752)  
**Status:** CODE PRESENT IN THIS PR / pending merge. I8 design gate is satisfied once this PR merges.

Gates all of I8-A/B/C. All 13 sections locked, Appendix B COMPLETE (all 5 previously-deferred decisions resolved):

- Section 1: Product hierarchy (1 visible peer post-I8; no-new-surface rule; surface-count exit test)
- Section 2: Canonical route map (`/exams/:exam_id`; 5-step redirect sequence; `action=add-cycle` redirect locked; transitional compatibility routes)
- Section 3: Page and component ownership (ExamIntelligence → single-view front door; ExamWorkspace evolved; ExamIntelCms overflow only; ExamGovernanceConsole retired)
- Section 4: Canonical readiness authority (`classify_exam` owns verdict; per-section facts from `readiness.py`; H2 DONE on main PR #750; locked section-state vocabulary)
- Section 5: Exam Management front-door content (family→exam→cycle hierarchy; single "Manage exam" row action)
- Section 6: Manage Exam content (action queue sections; cycle in URL query param; Overview tab eliminated)
- Section 7: Blocker-to-editor deep-link contract (tab+entity params required; 8 locked examples)
- Section 8: Management/readiness backend read-model contract (`/management/exams`; 2 endpoints; deterministic current-cycle selection rule; exact response fields; no second classifier)
- Section 9: Advanced Repair access model (Manage Exam → More → overflow; permission locked to `exam_intelligence.cms`; explicit warning; not a peer)
- Section 10: I8 delivery sequence and write scopes (serial; backend prerequisite first; I8-A removes ALL sidebar items atomically; I8-C scope limited to access model only)
- Section 11: Test migration plan (named tests to migrate; acceptance tests per I8-A/B/C)
- Section 12: Component retirement plan (retirement blocked on redirect tests)
- Section 13: Non-goals (I9, J1/J2/J3, KG rename, competition schema, mixed-PDF, coverage governance, new portfolio/matrix pages)

**I8 prerequisites after this PR merges:**

1. Backend read-model endpoints (`/api/admin/exam-intelligence/management/exams`) — parallel-safe; must land before I8-A displays real data
2. H2 fix (BUG-EI-2) — **ALREADY DONE on main (PR #750 merged)**. No further action.
3. I8-A → I8-B → I8-C: strictly serial, one owner, per write scopes in Section 10

### I6 cycle-setup gate document (write after IA lock)

Gates I9 implementation. Must define, for all 9 activation checklist steps:

- completion source
- hard gate vs advisory vs N/A
- deep-link target
- resume behaviour
- empty-state behaviour
- selected-cycle behaviour
- management-mode/cadence applicability
- `AddCycleWizard` decision (reuse / embed / remove)
- progress derivation (backend-derived vs frontend-composed)
- manual-mark-complete rules

## Lane P — PYQ Intelligence v2 delivery

Architecture doc: `docs/architecture/pyq-intelligence-v2.md`.
These PRs are isolated from all Exam Management IA work and can run in parallel with Lanes H/I/K.

### P-slice-1 — Primary-only frequency semantics + score snapshot foundation — **MERGED (PR #767)**

What landed:
- `coverage.py`: `verified_pyq_topic_counts` now filters `tag_role='primary'` only (DB + loop guard).
- `score_snapshots.py` (new): `compute_exam_topic_scores` (idempotent draft writer), `locked_score_snapshots` (locked-only reader), `list_exam_score_snapshots` (admin list).
- `admin_exam_intelligence.py`: three new admin endpoints for list/review/compute of score snapshots.
- New tests: `test_pyq_frequency_semantics.py` (7), `test_score_snapshots.py` (9), `test_score_snapshot_admin_api.py` (11).
- Updated `test_pyq_counts_trust.py`: aligned cross-paper aggregation test with primary-only contract.
- Checklist row added for slice-1.

**P1 review issues blocking merge** (from code review 2026-06-25):
1. Review mutation is not atomic — SELECT→UPDATE with discarded result; always returns `{ok: true}`.
2. Fingerprint missing primary tag content, locked coverage, `exam_phase_id`.
3. Phase scope not validated; PYQ papers leak from entire exam when phase is specified.
4. Multiple primary tags per question across topics not handled.
5. `locked_score_snapshots` returns all locked rows — no dedup to latest per `(exam_id, exam_phase_id, topic_id)`.
6. Read failures silently become empty evidence; admin must distinguish failure from no-evidence.

Fix PR: open as P-slice-1b addressing all six items plus P2 items (model_version server-owned, remove try/except ImportError, fix PR body files table).

**Write scope:**
- `app/backend/app/exam_intelligence/score_snapshots.py`
- `app/backend/app/api/admin_exam_intelligence.py`
- `app/backend/tests/exam_intelligence/test_score_snapshots.py`
- `app/backend/tests/exam_intelligence/test_score_snapshot_admin_api.py`
- `docs/status/career-copilot-checklist.md`

### P-slice-2 — Planner consumption of locked snapshots — **MERGED (PR #773)**

Wire `locked_score_snapshots()` into `planner.py` as an additional priority signal (up to 15 pts additive, confidence-weighted). Locked snapshots are cycle-independent (all-time verified PYQ corpus; no `exam_cycle_id` set by writer).

**Implementation details:**
- `locked_score_snapshots()` returns `None` on DB read failure (caller must distinguish from empty list); plan still generates with no snapshot component (`snapshot_read_failed=True` recorded in `input_context`).
- `confidence_score` modulates the snapshot component — `confidence=0.0` → 0 pts, `confidence=1.0` → full weight; absent `confidence_score` defaults to 1.0.
- `why_this_task` now carries 6 new nullable snapshot lineage fields (NOT 3): `snapshot_id`, `snapshot_priority_score`, `snapshot_confidence`, `snapshot_model_version`, `snapshot_computed_at`, `snapshot_evidence_count`. Plans without snapshots are NOT byte-identical to pre-P-slice-2 (these null fields are always present).
- `input_context` includes `snapshot_read_failed` and `snapshot_set_summary` (lineage per topic: `snapshot_id`, `model_version`, `computed_at`).
- `build_task_reasoning_detail()` adds a `locked_score_snapshot` trace row from persisted `why_this_task` lineage — no re-query.

**Write scope:**
- `app/backend/app/exam_intelligence/score_snapshots.py`
- `app/backend/app/study_os/planner.py`
- `app/backend/app/study_os/task_reasoning.py`
- `app/backend/tests/study_os/test_planner_snapshot_integration.py`
- `docs/status/career-copilot-pr-plan.md`

### P-slice-1c — Snapshot review atomicity (migration 204) — **MERGED as part of PR #810**

Closes the known atomicity gap. Shipped inside the Score Snapshot Workbench UI PR (#810) which also added the operator frontend and enrichment layer. See the PR #810 row in `career-copilot-checklist.md` for the full implementation record. **OPERATOR VALIDATION PENDING:** apply migration 204 to staging; verify EXECUTE grant matrix; confirm atomic audit trail in a live compute → review → lock cycle.

### P-slice-3 — Score Snapshot Workbench UI (operator surface) — **MERGED (PR #810)**

Operator workbench embedded as `?view=snapshots` inside PYQ Workbench tab. Scope selector, phase validation with error banner, generation-counter race guard, compute body contract, topic enrichment, evidence drawer, permission gate, focus management. 54 tests across two primary files: 25 frontend (`ScoreSnapshotPanel.test.jsx`) + 29 backend (`test_score_snapshot_admin_api.py`). CODE-FIXED, OPERATOR/BROWSER VALIDATION PENDING.

### Lane EI-worker — Admin text-extract background worker — **MERGED (PR #811)**

`text_extract_worker.py` + `doc:text_extract` APScheduler job (60 s, configurable). Scope-filtered to `admin_exam_intelligence` documents. `_fallback_fail_job` conditional write. `run_job_now` honours `_is_failure_result`. Manual-trigger permission raised to `exam_intelligence.cms`. 23 unit tests. OPERATOR VALIDATION PENDING. Retry/backoff deferred to issue #813; stuck-processing diagnostics deferred to issue #542.

### Lane PYQ-labels — Cycle/phase label fix in AddPyqPaperModal — **MERGED (PR #812)**

`AddPyqPaperModal` renders immutable cycle/phase context; `phaseId` always null (no `exam_phase_id` column on `exam_cycles`); ID/label mismatch fails closed with error banner + disabled submit; "No cycle selected (exam-wide paper)" shown when no cycle context active. BROWSER VALIDATION PENDING.

### P2 — Cognitive demand classification (Bloom's taxonomy) — **CONTRACT REQUIRED** (P-slice-2 merged PR #773; metadata-only classification independent of Track C but not dispatch-ready until contract approved)

Per `pyq-intelligence-v2.md` §P2 (governed cognitive and distractor classification): add `cognitive_demand` classification per PYQ question.
Contract-first: define the taxonomy levels and how they feed `score_components` before implementation.
Gate cleared — P-slice-2 is on main. Next step is the taxonomy + scoring contract (no code until agreed).

### P3 — Unified revision recommendations contract — **DEFERRED**

Per `pyq-intelligence-v2.md` §P3 (learner evidence and revision unification).
Revision → relearn/review/practice routing contract. Depends on SM-2 output (already in `services/srs.py`) + snapshot scores. Do not dispatch until P2 is designed.

### P-slice-5 — Current affairs provenance and linking pipeline — **DEFERRED**

CA provenance links CA items to exam topics. Contract-first; deferred post P-slice-2.

## Lane O — Onboarding knowledge calibration (SPEC — off PYQ roadmap)

Plan-personalization track addressing first-timer vs experienced-aspirant cold-start. Full spec: `docs/architecture/onboarding-knowledge-calibration.md`. Self-assessment is a subordinate planner prior in its own table — never touches `user_topic_mastery` or the gated `MasteryWriter`. Validated mastery always wins; the prior only fills the gap.

- **O-slice-1 — data + capture:** migration 198 (`user_topic_self_assessment`); `PUT/GET /api/study/self-assessment` (server owns band→prior + confidence); snapshot `attempts_used`. ✅ DONE
- **O-slice-2 — planner consumption:** `_load_topic_priors()` expands subject→topic_ids, blends `effective = rc * prior_mastery + (1-rc) * 45.0`; `mastery_source` in `why_this_task`; `self_assessment_summary` in `input_context`; graceful degradation on DB failure. ✅ DONE
- **O-slice-3 — frontend:** `PrePlanCalibration` interstitial on Study Plan page (post exam-select, pre first-generate); `useCalibrationPriors` hook; attempts capture. ✅ DONE

**PR #778** (`claude/onboarding-priors-spec`) — IN REVIEW. D1/D2/D3 all approved. 24 backend tests passing. OPERATOR PENDING: migrations 198/199 to staging, RLS confirm, E2E validate.

## Lane K — Mock semantics trust fix (READY — ISOLATED)

Independent of all IA work. Can run in parallel with H2, I7, I5.

- **Write scope:** `app/frontend/src/pages/study/Mocks.jsx`, targeted tests.
- **Work:**
  1. Relabel "Error patterns" → "Self-reported error patterns".
  2. Relabel average score display → "Average across N logged mocks".
  3. Add explanatory copy: time pressure / misread / guesswork / concept gap are user-entered values for manually logged mocks, not platform-inferred.
  4. For platform attempts, derive only what telemetry supports; do not infer unsupported causal labels from correctness alone.
- **Exit:** mock results page clearly attributes self-reported data to the user; no misleading platform-inference language.

## Suggested simultaneous dispatch batch (updated 2026-06-21)

Lane B is **closed** — all B items CODE PRESENT; do not dispatch.

PRs #747 (I5 PYQ pagination), #749 (I7 KG exam lane + mock semantics), #750 (H2 BUG-EI-2), #751 (mock semantics) merged on main.

### Already done — do not dispatch

- **H2 / BUG-EI-2** — MERGED (PR #750). `load_doc_extraction_counts` on main.
- **I7** — MERGED (PR #749). KG exam lane removed.
- **Mock semantics trust fix** — MERGED (PR #751). `Mocks.jsx` relabeled.
- **I5 PYQ pagination** — MERGED (PR #747). `PyqPaperWorkspace.jsx` paginated.

### Immediate dispatch (no gates)

These can run in parallel now:

1. **Agent H3:** EI UX cleanup batch (IDs, OverviewPanel dedup, phases cycle label). Does not touch routing.
2. **Agent A:** A1 scheduler evidence (operator/live, docs only).
3. **Agent E:** E1 CI sequencing (`.github/workflows/ci.yml` only). Independent.

### After IA design-lock PR (#752) merges

4. **Backend read-model agent (parallel-safe):** implement `GET /api/admin/exam-intelligence/management/exams` and `GET /api/admin/exam-intelligence/management/exams/{exam_id}` per design-lock Section 8. Must land before I8-A.
5. **I8-A agent (after backend merges):** Exam Management front door. Write scope per design-lock Section 10.3.
6. **I8-B agent (after I8-A merges):** Manage Exam consolidation. Write scope per design-lock Section 10.4.
7. **I8-C agent (after I8-B merges):** Advanced Repair isolation. Write scope per design-lock Section 10.5.

### Blocked until IA design lock

- I8-A, I8-B, I8-C — serial, one owner, cannot start until IA lock PR merges.
- Management read-model backend — after IA contract is locked (this PR).
- J1, J2, J3 — after I8-A/B/C.

### Blocked until Lane A clean gate

- G-lane work (A-PR4, A-PR5, Track C) — do not dispatch.

### Do not dispatch

- I9 — blocked on I6 gate document (write after IA lock).
- J3, competition metrics, mixed-PDF, coverage governance — contract-first; deferred.
- KG rename — separate later PR; do not fold into I7 or I8-A.
