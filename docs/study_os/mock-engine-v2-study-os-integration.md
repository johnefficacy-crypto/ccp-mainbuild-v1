---
owner: study-os
status: design + plan
last_verified_against_code: 2026-06-17
verified_against: fix/unify-mock-correction-policy (§7 #2 closed)
source_of_truth: code
related_code:
  - app/backend/app/study_os/planner.py
  - app/backend/app/study_os/mocks.py
  - app/backend/app/study_os/mock_blueprint_selection.py
  - app/backend/app/study_os/mastery_writer.py
  - app/backend/app/study_os/mastery.py
  - app/backend/app/study_os/mock_engine.py
  - app/backend/app/api/mock_engine.py
  - app/backend/app/exam_intelligence/diagnostics.py
  - app/backend/app/study_os/mastery_engine/correction_tasks.py
related_migrations:
  - app/supabase/migrations/063_study_os_mocks_analysis.sql
  - app/supabase/migrations/135_mock_engine_core.sql
  - app/supabase/migrations/174_mock_generated_blueprints.sql
  - app/supabase/migrations/175_mock_attempts_generated_blueprint.sql
review_cadence: per-sprint
---

# Mock Engine v2 ↔ Study OS: Findings, Decisions & Implementation Plan

> **What this is.** Rationale + plan for connecting the Track A generated-mock
> engine to the Study OS adaptive planner. It is a durable decision record, not
> a status board. **Live per-PR status is tracked in the living PR tracker (the
> HTML checklist) — this document does not duplicate it; cross-reference the
> tracker for "what's merged".**
>
> **Verification discipline.** Every code-grounded claim below is cited as
> `file:line` against `main @ 406648c` (2026-06-16). Claims that did **not** hold
> as originally framed are not stated as fact — they are corrected in
> [§8 Unverified / Corrected](#8-unverified--corrected).

---

## 1. Context & scope

**Mock Engine v2** is the exam-realistic — and, later, personalized — generated
mock layer that feeds the Study OS adaptive planner. **Track A** is the
generated-mock engine itself (envelope → readiness → selection → attempt). This
document covers only how Track A *connects to Study OS*: which feedback edges are
wired live today, which are pending, the decisions taken to close them safely,
and the ordered plan to get there.

It deliberately stops at the Study OS boundary. The internal mechanics of the
mastery engine, the submit/sweeper machinery, and the write-back flag cutover are
documented separately and referenced here:

- `docs/study_os/mock_submit_flow.md` — submit paths, derivation→mastery ordering, sweeper.
- `docs/study_os/mock_mastery_writeback.md` — `FF_MOCK_MASTERY_WRITES` states + cutover.
- `docs/mock_engine/mastery_engine.md` — delta formula, error signals, correction-task rules.

---

## 2. Verified architecture — three feedback loops

The planner ↔ mock relationship is three distinct loops. Two are live; one is
pending Track A's attempt write-path.

### Loop A — planner → task type — **LIVE**

The planner converts each topic's mastery + error state into a task *type* and a
priority score.

- Task-type rule (`_task_type`): mastery `None` → `concept_learning`; `< 45` →
  `concept_learning`; `< 75` **or** has error patterns → `retrieval_practice`;
  else `revision`. Verified at `app/backend/app/study_os/planner.py:406-413`.
- Inputs the planner reads:
  - `user_topic_mastery` (weakness) — `planner.py:325-326`.
  - `user_topic_error_patterns` (error topics) — `planner.py:352`.
  - **Locked** `exam_topic_coverage` — only `reviewer_status='locked'` rows are
    planner-ready — `planner.py:197-204`.
  - `verified_pyq_topic_counts` (PYQ weight) — imported `planner.py:30`, called
    `planner.py:839`.
- Outputs: `priority_score` (`planner.py:395-403`) and `why_this_task`
  (`planner.py:449-519`), assembled per-topic at `planner.py:891-900`.

### Loop B — manual/logged mock → correction task → study task — **LIVE**

A reviewed mock produces correction tasks, which can be promoted into the plan.

- Correction categories (`VALID_CORRECTION_CATEGORIES`): `concept_gap`,
  `memory_gap`, `careless`, `speed_issue`, `option_trap` —
  `app/backend/app/study_os/mocks.py:62-68`. (Note: **five** categories, not the
  four originally listed — see [§8](#8-unverified--corrected).)
- `list_correction_tasks` reads `mock_correction_tasks` — `mocks.py:196`.
- `draft_correction_tasks` writes `mock_correction_tasks` (insert at
  `mocks.py:427`; payload shape `mocks.py:414-423`).
- `apply_correction_task` promotes a correction into a study task and links it
  back via `mock_correction_tasks.study_task_id` — `mocks.py:446-454`.

### Loop C — generated mock → mastery/error → planner — **PENDING (A-PR3)**

Track A can *select* the questions for a generated mock but cannot yet *run* one,
so no mastery signal flows back from a generated attempt.

- `mock_blueprint_selection.py` (A-PR2) is **non-mutating**: it consumes the
  A-PR1 envelope and returns `selector_snapshot` + `question_ids` only — "no DB
  write, no `mock_generated_blueprints` insert (A-PR3), no attempt start"
  (`app/backend/app/study_os/mock_blueprint_selection.py:1-7`; `question_ids`
  populated at `:297`).
- The generated-attempt write path `start_attempt_from_blueprint` is explicitly
  deferred — migration 175 states it "lands later"
  (`app/supabase/migrations/175_mock_attempts_generated_blueprint.sql`, header).

---

## 3. Edge map — wired vs open

| Edge | Status | Evidence |
|---|---|---|
| selected exam → planner | LIVE | planner scoped by `exam_id` throughout; coverage/PYQ/mastery all exam-keyed — `planner.py:804-841` |
| syllabus / topics → planner | LIVE | locked `exam_topic_coverage` → topic rows — `planner.py:197-213` |
| PYQ → planner | LIVE | `verified_pyq_topic_counts` — `planner.py:30, 839` |
| persona → planner | LIVE (limited) | `aspirant_persona_snapshots.study_policy` drives task **count + sizing** only (`max_tasks_per_day`, `preferred_task_size`), user pref overrides — `planner.py:854-878`. Persona does **not** select topics. |
| mastery / error → planner | LIVE | `user_topic_mastery` + `user_topic_error_patterns` reads — `planner.py:325-326, 352` |
| mock submit → mastery write-back | IMPLEMENTED, FLAG-GATED | `MasteryWriter.process_attempt` reads frozen `question_snapshot` `topic_id`/`microtopic_id` — `mastery_writer.py:77-85`. `FF_MOCK_MASTERY_WRITES ∈ {off, shadow, live}` — `mastery_writer.py:18, 221`. shadow → `mock_mastery_shadow` (`:166`); live → `user_topic_mastery` (RPC `apply_mock_mastery_delta`, `:184-193`) + `user_topic_error_patterns` (`:197-200`) + `mock_correction_tasks` (`:202-217`). **Trigger is INLINE in the submit route, not job-driven** — `app/backend/app/api/mock_engine.py:155-160` (see [§8](#8-unverified--corrected)). |
| generated mock → submit → mastery | OPEN (A-PR3) | no generated attempt write path yet — migration 175 header; `mock_blueprint_selection.py:1-7` |
| weak-topic / persona → generated selection | OPEN (A-PR4/A-PR5) | `exposure_cooldown` + `personalization` ladder rungs are explicit **inert** no-ops — `mock_blueprint_selection.py:168-169` |
| PYQ-weighting → generated mock mix | PARTIAL | `source_mix`/`difficulty_mix` apply only when the envelope section carries targets — `mock_blueprint_selection.py:180-195`. Full PYQ weighting = Wave 5 compiler, pending. |

---

## 4. Verified risks / findings

### 4a. MSQ / integer latent correctness bug

The generated/readiness selectable pool admits a question type the scorer
mis-scores.

- `_SELECTABLE_QUESTION_TYPES = ("mcq", "msq", "integer")` —
  `app/backend/app/exam_intelligence/diagnostics.py:42` — used in
  `selectable_mcq_depth` (`:399`) and imported by A-PR2 selection
  (`mock_blueprint_selection.py:53, 106`).
- But scoring is **single-option only**: `save_answer` takes one
  `selected_option_id: str | None` (`mock_engine.py:459-464`), and
  `_finalize_submission` scores by single equality `selected == correct_opt`
  (`mock_engine.py:586-607`). There is no multi-select set comparison and no
  numeric answer handling.

**Consequence.** An `msq` (multiple correct options, one frozen
`correct_option_id`) or `integer` (no options at all) question that the selector
admits would be scored against a single option — silently wrong. The selector
admits a type the scorer cannot grade. This is the motivation for the Safety PR
in [§5](#5-decisions-taken).

### 4b. Dual writers — divergence / duplicate-logic risk

Two independent code paths write the same Study OS tables, with **different
categorizers and an incompatible schema contract**.

| Table | Writer 1 | Writer 2 |
|---|---|---|
| `user_topic_mastery` | `mastery_writer.py:184-193` (delta via `apply_mock_mastery_delta` RPC) | `mastery.py:213-215` (`recompute_topic_mastery` full upsert) |
| `user_topic_error_patterns` | `mastery_writer.py:197-200` (upsert) | `mastery.py:237-239` (upsert) |
| `mock_correction_tasks` | `mastery_writer.py:202-217` (`_draft_correction_tasks`) | `mocks.py:384-428` (`draft_correction_tasks`) |

Two concrete divergences make this more than a style concern:

1. **Different correction vocabularies.** The mastery-engine path emits
   `task_type ∈ {pyq_revision, concept_review, trap_review, practice_drill}`
   (`mastery_engine/correction_tasks.py:48-54`); the manual mock path emits
   `category ∈ {concept_gap, memory_gap, careless, speed_issue, option_trap}`
   (`mocks.py:62-68`). They are not the same categorizer.
2. **Schema-incompatible insert (latent).** `mock_correction_tasks` (the only
   migration that defines it, `063_study_os_mocks_analysis.sql:29-54`) has
   `mock_test_id NOT NULL` (FK), `category NOT NULL` (checked against the five
   values above), and `title NOT NULL` — and **no** `task_type`, `priority`,
   `evidence_json`, `duration_minutes`, or `source_attempt_id` columns. The
   manual path inserts exactly that schema (`mocks.py:414-423`). The
   `MasteryWriter` path inserts `mock_test_id: None` plus the five non-existent
   columns and omits `category`/`title` (`mastery_writer.py:205-215`) — which
   would fail at runtime. It is only reachable at `FF=live` (never flipped), so
   the defect is **latent**, not active.

Loop B and Loop C must produce **consistent** signals (same categorizer/
thresholds, no double-write) or the plan adapts incoherently depending on whether
a topic's signal came from a manual log or a generated mock. This is the central
pre-`live` blocker; see [§7](#7-open-items-to-resolve-before-fflive).

### 4c. Question-model fidelity gap

The question model is text-only end to end.

- `mock_question_bank.question_text` is `text` (`135_mock_engine_core.sql:65`)
  and `mock_question_options.option_text` is `text` (`:84`). No `stimulus`,
  `passage`, `image`/`asset` column exists on either table (no such column in
  the create or in any later `alter`).
- `_question_snapshot` freezes text only — `question_text`, `options[].option_text`
  — plus scoring/signal scalars (`topic_id`, `microtopic_id`, `difficulty`,
  `source_type`, `correct_option_id`) — `mock_engine.py:114-143`.

Four structural question categories, by representability today:

| Category | Examples | Status |
|---|---|---|
| Standalone text MCQ | incl. UPSC multi-statement / assertion-reason / text-match | **SUPPORTED** |
| Shared-stimulus sets | RC / puzzle / DI caselet | **NOT first-class** (no stimulus entity) |
| Stem images | DI charts / maps / figures | **NOT** (no media on questions) |
| Option images | non-verbal figure reasoning | **NOT** (no media on options) |

**Canary caveat.** "SSC CGL Tier 1 ready" means there are enough **text** MCQs to
fill the structure — **not** form-fidelity. SSC CGL's non-verbal figure
(option-image) and DI (stem-image) questions are not representable today. SSC CGL
is the right canary precisely *because* it is set-light; it is the wrong canary
for validating Track C (see [§5](#5-decisions-taken)).

---

## 5. Decisions taken

### D1 — Safety PR: restrict the generated/readiness selectable pool to `mcq` only

Set `_SELECTABLE_QUESTION_TYPES = ("mcq",)` — a single shared constant so that
**selection ≡ readiness** by construction (`diagnostics.py:42`, consumed by both
`selectable_mcq_depth` and `mock_blueprint_selection.py:53`). The enum keeps
`msq`/`integer` for *authoring*; they must not enter generated mocks until the
answer payload and scoring support them (closes [§4a](#4a-msq--integer-latent-correctness-bug)).
The template path's looser `question_type` handling is a **separate parked
divergence** (documented at `mock_blueprint_selection.py:39-45`) and is out of
scope for the Safety PR.

### D2 — A-PR3 reframed as a *signal producer*, not "start a mock"

A-PR3 is "**Start generated mock attempts as a Study OS feedback-loop signal
producer**," not "start a mock." Acceptance criteria (design targets, to be built
in A-PR3's own PR):

1. Blueprint persists with its 100 ids (`mock_generated_blueprints`, migration 174).
2. Attempt uses `generated_blueprint_id`, `template_id` null — XOR enforced by
   `mock_attempts_one_source_chk` (`175_mock_attempts_generated_blueprint.sql`).
3. Responses freeze `question_snapshot` `topic_id`/`microtopic_id`/`difficulty`/
   `source` (same freeze contract as `mock_engine.py:114-143`).
4. Atomic: one-transaction `start_attempt_from_blueprint()` with full rollback on
   failure (the path migration 175 says "lands later").
5. Start only if the recomputed outcome `== ready` — **server-side** thresholds,
   never trusted from the client.
6. Reuse `template_snapshot` so loader/scoring/UI are unchanged
   (`mock_engine.py:308-327`).
7. Submit goes through the **shared** submit path and triggers the mastery
   write-back. **Note:** the shared path currently runs the writer *inline*
   (`api/mock_engine.py:155-160`); "schedules the mastery job" describes a future
   trigger that does not exist on `main` — see [§7](#7-open-items-to-resolve-before-fflive)
   and [§8](#8-unverified--corrected).
8. **Single consistent path** — same categorizer/tables as the manual loop, no
   double-write of `mock_correction_tasks`/`user_topic_mastery` (depends on
   resolving [§4b](#4b-dual-writers--divergence--duplicate-logic-risk)).
9. Shadow parity — under `FF=shadow`, generated deltas reconcile against the
   manual path before any `live` flip; then the planner re-prioritizes on the
   updated signals.

### D3 — Track C = "Question Model v2" (a separate arc)

Stimulus → media → non-MCQ scoring is a **separate arc** that **re-opens** OP-0
readiness, A-PR1 envelope, and A-PR2 selection (the selection unit becomes
*question-or-set*). Decision-locks:

- Set is the atomic selectable unit; **all-or-none**.
- Contiguity via `stimulus_order`.
- Set-size is authored structure; selection tiles **exactly** to `question_count`
  (readiness = tiling feasibility, not a raw count).
- Section target counts **child** questions.
- Stimulus lifecycle gate: a question is selectable only if its stimulus is also
  published — placed in the **shared** predicate so readiness ≡ selection (the
  same discipline that keeps A-PR2 ≡ the readiness pool today,
  `mock_blueprint_selection.py:79-118`).
- On delete **RESTRICT** (not set-null) — mirrors the `on delete restrict` choice
  migration 175 already makes for `generated_blueprint_id`.
- Snapshot freezes the stimulus once at the **attempt** level; responses carry
  `stimulus_id`.
- Grouped UI render contract.
- FK / RLS / grants introspected — **do not guess** the `exams`/`subjects`/
  `topics` table names.
- **Dependencies:** full DI needs non-MCQ scoring; validate Track C on a
  **set-heavy** canary (CSAT or IBPS), **not** SSC CGL (set-light).
- **Naming:** Track C / **S-PR** series — do **not** reuse Track B's descriptive
  labels.

### D4 — Sequencing: depth-first

Close Loop C on the SSC CGL **text-MCQ** canary and validate it in **shadow**
*before* widening to Track C. Depth before breadth.

---

## 6. Implementation plan (ordered)

| # | Step | Notes |
|---|---|---|
| 0 | **Safety PR — `mcq`-only pool** | D1. Shared constant; selection ≡ readiness. |
| 1 | **A-PR3 — generated blueprint persist + atomic attempt start** | D2; signal producer, not "start a mock". |
| 2 | **Play SSC CGL generated attempt end-to-end** | submit + result through the shared path. |
| 3 | **`FF_MOCK_MASTERY_WRITES=shadow`; submit generated; inspect `mock_mastery_shadow`** | shadow write at `mastery_writer.py:166`. |
| 4 | **Resolve dual-writer consistency (Loop B vs Loop C)** | same categorizer, no double-write; reconcile shadow vs manual. Blocks step 5. ([§4b](#4b-dual-writers--divergence--duplicate-logic-risk)) |
| 5 | **`FF=live` after validation** | verify `user_topic_mastery`/`error_patterns` changed; regenerate plan; verify task priorities changed. |
| 6 | **A-PR4 (exposure cooldown) + A-PR5 (personalize the mock from mastery)** | closes the loop edge still open after A-PR3 — mock → mastery → smarter **mock**, not just smarter plan. Inert rungs already slotted: `mock_blueprint_selection.py:168-169`. |
| 7 | **Track C (stimulus → media → non-MCQ scoring)** | D3 locks; validate on a set-heavy canary. Wave 5 PYQ-weighting feeds mock realism here / in parallel. |

---

## 7. Open items to resolve before `FF=live`

Carry these as explicit TODOs; steps 4–5 above cannot land safely until they are
answered.

1. **Which mastery writer is authoritative** — delta-based `mastery_writer.py`
   (`:184-193`) or full-recompute `mastery.py` (`recompute_topic_mastery`,
   `:155-215`)? Do both fire for one attempt? They are not reconciled today.
2. **Do generated (`MasteryWriter`) and manual (`mocks.py`) corrections use the
   same categorizer + thresholds?** **RESOLVED.** One shared, source-neutral
   policy (`app/backend/app/study_os/correction_policy.py`) owns the canonical
   categories, alias normalization, and selection. Both **production** adapters
   call `select_categories(...)`, which returns an **ordered canonical correction
   SET** (one entry per canonical category, count-desc with a stable tie-break)
   over **aggregated** evidence — raw aliases are normalized and summed first, so
   collisions like `concept` + `concept_gap` collapse to a single correction and
   `concept=1, option=3` yields `[option_trap, concept_gap]` for *both* origins.
   Emission is one source-neutral rule (any recognized canonical error, or an
   explicit weak-topic / low-accuracy / unrecovered-prior-error fallback);
   `evidence_mode` is descriptive only. Category comes from EVIDENCE, never
   `task_type` (action style, derived after, never overrides the category).
   `CorrectionTaskDraft` carries `category`; `MasteryWriter` is a pure persistence
   adapter (its `task_type→category` mapping is removed). The generated pipeline
   feeds the policy from **question-level** `error_type` (not the narrower
   `error_patterns.TRACKED` write-vocab), so memory/speed/misread evidence
   survives. Titles are **category-only** (e.g. `Concept drill`) — identical
   across origins; `topic` stays a separate, source-specific column (manual = display
   label, generated = canonical id) and is **not** claimed equal. Adapter-level
   cross-origin parity is test-pinned (`tests/study_os/test_correction_policy.py`,
   driving both real adapters). The earlier schema-incompatibility was closed in
   #702 ([§4b](#4b-dual-writers--divergence--duplicate-logic-risk)).
   *Still open, separately:* DB-enforced correction uniqueness (dedup is
   **best-effort serial-retry**, not concurrency-safe), `FF_MOCK_MASTERY_WRITES`
   stays **off**, and operator shadow→live validation is next.
3. **Is the mastery trigger source-agnostic?** Today the trigger is **inline in
   the user-submit route** (`api/mock_engine.py:155-160`), so a generated submit
   with `template_id=null` going through that route *would* run the writer. But
   **auto-submitted** attempts (sweeper) do **not** run mastery — it is deferred
   to a future `mastery_retry` job that is defined but unwired
   (`mock_engine.py:1125`; `docs/study_os/mock_submit_flow.md:70-72`). Decide
   whether generated attempts must also produce signals on auto-submit.
4. **Wave 5 PYQ-weighting into the generated mock mix** — still pending; A-PR2
   enforces `source_mix`/`difficulty_mix` only when the envelope carries targets
   (`mock_blueprint_selection.py:180-195`).

---

## 8. Unverified / Corrected

Claims that did **not** hold exactly as originally framed. Documented here rather
than asserted as fact.

| # | Original claim | What `main @ 406648c` actually shows | Disposition |
|---|---|---|---|
| C1 | Loop B correction categories are four: `concept_gap, memory_gap, speed_issue, option_trap` | `VALID_CORRECTION_CATEGORIES` has **five** — adds `careless` — `mocks.py:62-68` | Corrected. The four named all exist; there is a fifth. |
| C2 | mock submit → mastery trigger is **job-driven** (`JOB_MASTERY_RETRY` / `schedule_job` from the submit path) | The submit route runs `MasteryWriter.process_attempt` **inline** — `api/mock_engine.py:155-160`. `JOB_MASTERY_RETRY = "mastery_retry"` is **defined but reserved/unwired** (`mock_engine.py:1125`; comment `:1121`). The submit path schedules only `JOB_ANALYTICS_RETRY` (`:731`) and `JOB_MOCK_TESTS_RETRY` (`:720`). | **Does not hold.** Trigger is inline, not job-driven. Carried into [§7 #3](#7-open-items-to-resolve-before-fflive). |
| C3 | `live → mock_correction_tasks` write (via `MasteryWriter`) is functional | The insert is **schema-incompatible**: it sends `mock_test_id: None` (the column is `NOT NULL` FK) plus columns that do not exist (`task_type`, `priority`, `evidence_json`, `duration_minutes`, `source_attempt_id`) and omits `NOT NULL` `category`/`title` — `mastery_writer.py:205-215` vs `063_study_os_mocks_analysis.sql:29-54`. Only reachable at `FF=live` (never flipped). | **Latent defect**, not active. Must be fixed before `FF=live` ([§4b](#4b-dual-writers--divergence--duplicate-logic-risk), [§7 #2](#7-open-items-to-resolve-before-fflive)). |

---

## 9. Cross-references

- Living PR tracker (HTML checklist) — authoritative for per-PR merge status.
- `docs/study_os/mock_submit_flow.md` — submit/derivation/sweeper internals.
- `docs/study_os/mock_mastery_writeback.md` — `FF_MOCK_MASTERY_WRITES` cutover.
- `docs/mock_engine/mastery_engine.md` — delta formula + correction-task rules.
- `docs/architecture/persona-layer.md`, `docs/architecture/study-os-mission-control.md`.
