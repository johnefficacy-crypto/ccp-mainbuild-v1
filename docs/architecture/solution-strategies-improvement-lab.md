# Solution Strategies and Improvement Lab

**Status:** DESIGN LOCKED — implementation planned  
**Decision date:** 2026-07-14  
**Scope:** learner-facing Quant and Reasoning strategy delivery, plus the broader Improvement Lab composition  
**Execution checklist:** `docs/status/GQR-Solution-Strategies-Improvement-Lab-Checklist-2026-07-14.md`

Related contracts:

- `docs/architecture/subject-practice-framework.md`
- `docs/architecture/english-writing-practice.md`
- `docs/status/career-copilot-checklist.md`
- `docs/status/career-copilot-pr-plan.md`

---

## 1. Locked product terminology

The learner-facing product vocabulary is:

| Context | Learner-facing term | Internal/admin term |
|---|---|---|
| Parent learner surface | **Improvement Lab** | subject-specific read models composed by the frontend |
| English section | **My Writing Errors** | EWP Error Lab / `ewp_error_lab` |
| Quant section | **Methods & Shortcuts** | Quant Heuristics / `quant_heuristics` |
| Reasoning section | **Approaches & Patterns** | Reasoning Strategies |
| Per-question review component | **Solution Strategy** | normalized learner projection from the relevant governed authority |

The internal Quant term **heuristic** remains unchanged in the schema, backend authority, migrations, tests, and Content Studio. It is technically accurate for operators but should not be shown as the primary learner-facing label.

The existing English writing Error Lab is not repurposed as a Quant or Reasoning data source. It remains the English-specific current-state issue model. The learner-facing page may be renamed and expanded, but the underlying English authority stays separate.

---

## 2. Goal

After a learner submits an objective question, the review experience may show verified instructional strategy content relevant to that question:

- Quant: standard method, faster method or shortcut, formula, worked example, and common trap.
- Reasoning: recommended approach, key observation, elimination or diagram method, worked example, common trap, and faster approach where meaningful.

The same governed strategy content can later be revisited through Improvement Lab, prioritized using the learner's submitted-attempt history.

The delivery must be:

- review-only;
- verified and active at read time;
- server projected;
- free of governance fields;
- batched rather than N+1;
- backward-compatible when no strategy exists;
- compatible with regular mocks and generated mocks through their shared review path.

---

## 3. Non-goals

The initial delivery does not include:

- direct learner reads from strategy or heuristic tables;
- new authenticated or anonymous RLS policies for governed content;
- raw `applicability_rule` JSON in learner payloads;
- strategy display during an active attempt;
- PYQ-practice or subject-practice review paths unless they already consume the shared mock review contract;
- planner routing from `speed_gap` to heuristic drills;
- Calculation Gym recommendation logic;
- target solve-time claims before reviewed, evidence-backed timing data exists;
- non-verbal Reasoning or image-dependent strategy rendering;
- set/stimulus-level Reasoning delivery in the first independent-question PR;
- a new top-level Study or Admin navigation destination.

Calculation Gym and performance signals remain GQR-Q8 concerns. Planner activation remains a later GQR-Q9 concern and must not be mixed into the review-delivery PR.

---

## 4. Existing repository grounding

### 4.1 Quant authority already exists

The repository already contains:

- `app/supabase/migrations/243_quant_heuristic_authority.sql`
- `app/supabase/migrations/246_quant_heuristic_review_cas_reason.sql`
- `app/backend/app/study_os/quant_heuristics.py`
- `app/backend/app/api/content_studio.py`
- `app/frontend/src/pages/admin/content-studio/QuantHeuristicLibrary.jsx`
- `app/frontend/src/pages/admin/content-studio/QuantHeuristicReviewQueue.jsx`

The current authority correctly requires the question link to be verified, the heuristic to be verified, and the heuristic to be active before learner delivery. The current helper is single-question oriented and must gain a batched read before it is used by mock review.

The existing Content Studio Quant library and review queue are governance surfaces. Verify whether authoring, editing, activation, and question-assignment workflows are complete before expecting learner-visible content. A correct review integration may legitimately return an empty list when no verified linked content exists.

### 4.2 Shared mock review path already exists

The integration point is:

- `app/backend/app/study_os/mock_engine.py::get_review`

The frontend path is:

- `app/frontend/src/pages/study/mocks/MockReview.jsx`
- `app/frontend/src/pages/study/mocks/components/questions/QuestionRenderer.jsx`
- type-specific renderers under `components/questions/types/`

Regular and generated mock attempts use the same review endpoint:

```text
GET /api/study/mocks/attempts/{attempt_id}/review
```

The review response currently returns the frozen `question_snapshot`, learner response state, classification, explanation, and timing. Strategy content is deliberately a live read, not part of the frozen question snapshot.

### 4.3 Existing English Error Lab is subject-specific

The current route and data path are:

- `/app/study/error-lab`
- `app/frontend/src/pages/study/ErrorLab.jsx`
- `app/frontend/src/features/study/english-practice/useErrorLab.js`
- `GET /api/study/practice/english/error-lab`
- the server-owned `ewp_error_lab` read model

That path represents the learner's current, feedback-released English writing issues grouped by microtopic. It must remain the English data source after the learner-facing page becomes Improvement Lab.

---

## 5. Unified learner contract

Both Quant and Reasoning project their governed internal records into one learner-safe shape:

```json
{
  "id": "uuid",
  "subject_family": "quant",
  "name": "Base-100 percentage method",
  "strategy_type": "shortcut",
  "formula_latex": "x = \\frac{a}{b} \\times 100",
  "standard_method": "...",
  "faster_method": "...",
  "worked_example": "...",
  "key_observation": null,
  "common_traps": "...",
  "relevance": "primary"
}
```

The normalized response key is:

```json
{
  "solution_strategies": []
}
```

### 5.1 Allowed learner fields

- `id`
- `subject_family`
- `name`
- `strategy_type`
- `formula_latex`
- `standard_method`
- `faster_method`
- `worked_example`
- `key_observation`
- `common_traps`
- `relevance`

### 5.2 Forbidden learner fields

The projection must never include:

- `applicability_rule`
- `reviewer_status`
- `reviewer_notes`
- `reviewed_by`
- `reviewed_at`
- `created_by`
- audit identifiers or audit records
- internal content hashes or concurrency tokens
- raw topic or microtopic governance metadata unless separately approved for learner display

### 5.3 Compatibility rule

Clients must treat a missing `solution_strategies` field as an empty list. Non-Quant and non-Reasoning questions naturally receive `[]`.

---

## 6. Quant implementation

### 6.1 Batched read

Add a batched authority function in `app/backend/app/study_os/quant_heuristics.py`:

```python
heuristics_for_questions(
    supabase,
    question_ids: list[str],
) -> dict[str, list[dict]]
```

Requirements:

1. Deduplicate and discard empty question IDs.
2. Initialize every requested ID with an empty list.
3. Fetch all verified question links in one query.
4. Fetch all referenced verified and active heuristic rows in one query.
5. Project only learner-safe fields.
6. Attach link relevance.
7. Sort deterministically by relevance, then stable name and ID ordering.
8. Prevent cross-question leakage.
9. Fail soft to empty strategy lists when the optional learner-content read fails; the main review response must remain available.
10. Retain `heuristics_for_question()` as a compatibility wrapper if existing callers require it.

For any number of questions, the Quant authority should use at most one link query and one heuristic query.

### 6.2 Shared strategy aggregator

Create:

```text
app/backend/app/study_os/solution_strategies.py
```

It owns:

- the normalized learner projection contract;
- common relevance ordering;
- source aggregation;
- the stable function called by `mock_engine.get_review()`.

Initial source:

- Quant heuristics.

Later source:

- Reasoning strategies.

`mock_engine.get_review()` must not need another structural rewrite when Reasoning is added.

### 6.3 Review payload integration

In `mock_engine.get_review()`:

1. Resolve the ordered question IDs using the frozen attempt order.
2. Fetch all solution strategies once before the per-question response loop.
3. Add `solution_strategies` as a sibling of `question_snapshot`.
4. Keep the strategy read live.

A Quant heuristic that later becomes inactive, rejected, pending, or `needs_correction`, or whose question link is no longer verified, must disappear immediately from subsequent review reads.

Do not copy the live strategy content into `question_snapshot` or any attempt-start snapshot.

---

## 7. Shared frontend delivery

### 7.1 Component

Create:

```text
app/frontend/src/pages/study/mocks/components/questions/shared/SolutionStrategyPanel.jsx
```

The panel:

- renders only when `mode === "review"`;
- is absent during active attempts;
- returns `null` for missing or empty strategy arrays;
- renders the learner-safe labels only;
- wraps bare `formula_latex` in math delimiters before passing it to the existing `MathRenderer`/KaTeX path;
- supports Quant and Reasoning fields without subject-specific component forks;
- uses stable keys based on subject and strategy ID;
- remains accessible through a labelled section heading.

Recommended learner labels:

| DTO field | Learner label |
|---|---|
| `standard_method` | Standard method |
| `faster_method` | Faster method |
| `key_observation` | Key observation |
| `worked_example` | Worked example |
| `common_traps` | Watch out for |

### 7.2 Render once in the shared wrapper

Render the panel in `QuestionRenderer.jsx`, after the type-specific question renderer, instead of modifying every question-type component separately.

This provides consistent behavior for:

- MCQ single;
- MCQ multi;
- numerical answers;
- statement-based questions;
- assertion-reason;
- match-the-following;
- future shared renderer types.

### 7.3 MockReview threading

`MockReview.jsx` adds:

```jsx
solution_strategies: current.solution_strategies ?? []
```

to the question object passed to `QuestionRenderer`.

No existing review field is renamed or removed.

---

## 8. Reasoning implementation

Reasoning uses the same learner contract and frontend component but requires its own governed internal authority.

### 8.1 Initial content coverage

The first Reasoning delivery covers independent text questions such as:

- analogy and classification;
- number or alphabet series;
- coding-decoding;
- blood relations;
- directions;
- ranking and ordering;
- syllogism;
- statement-conclusion;
- statement-assumption;
- logical sequence.

Text-based seating arrangements and puzzles are supported only at question level in the first slice. Proper set-aware delivery is a later slice.

### 8.2 Reasoning strategy authority

Create governed tables equivalent in posture to Quant:

```text
reasoning_strategies
reasoning_question_strategies
```

Suggested strategy types:

- `approach`
- `pattern`
- `elimination`
- `diagram_method`
- `set_method`
- `trap`

Suggested strategy fields:

- topic and microtopic scope;
- stable strategy code;
- name;
- structured `applicability_rule`;
- standard method;
- faster method;
- key observation;
- worked example;
- common traps;
- reviewer lifecycle;
- active state;
- audit metadata.

The question link has its own reviewer status and relevance. Learner delivery requires conjunctively:

```text
strategy verified
AND strategy active
AND question link verified
```

RLS remains enabled. Tables and lifecycle RPCs remain service-role-only for learner delivery.

### 8.3 Review lifecycle

The Reasoning authority must include:

- transition-matrix enforcement;
- expected-status CAS;
- expected-`updated_at` CAS;
- mandatory review reason;
- audited transitions;
- service-role-only execution;
- tests proving anon/authenticated cannot call the governance RPCs.

### 8.4 Backend integration

Create:

```text
app/backend/app/study_os/reasoning_strategies.py
```

Expose a batched `strategies_for_questions()` function with the same guarantees as the Quant batched reader. Add it to `solution_strategies.py`; do not rewrite the mock review loop.

### 8.5 Content Studio

Reasoning governance belongs inside the existing Content Studio surface, not in a new admin navigation destination.

Required capabilities are:

- strategy library;
- draft creation and editing;
- review queue;
- activation and retirement controls;
- question assignment;
- independent review of the strategy and its link;
- learner-safe preview of the normalized projection.

---

## 9. Reasoning set-aware delivery

Reasoning sets require a separate PR because a shared seating-arrangement or puzzle approach should not repeat on every linked question.

Add a later governed link such as:

```text
reasoning_stimulus_strategies
- stimulus_id
- strategy_id
- relevance
- reviewer_status
```

The review contract can then distinguish:

```json
{
  "stimulus_solution_strategies": [],
  "solution_strategies": []
}
```

Rendering rules:

1. Set-solving approach renders once above the grouped questions.
2. Derived arrangement, table, or working structure belongs to the set review.
3. Question-specific elimination or trap remains on the individual question.
4. The one-question-at-a-time review UI must not duplicate the same set strategy for every question.

Non-verbal Reasoning remains deferred until media-aware content and rendering are explicitly designed.

---

## 10. Improvement Lab

### 10.1 Learner page

Rename the learner-facing page to **Improvement Lab**.

Canonical route:

```text
/app/study/improvement-lab
```

Backward-compatible route:

```text
/app/study/error-lab
```

The old route should redirect or alias to the canonical route. The page remains under `StudyShell`, inside the existing route error boundary, and absent from primary navigation unless a separate no-new-surface decision changes that posture.

### 10.2 Composition

The page composes independent sections and independent data sources:

```text
Improvement Lab
├── My Writing Errors
├── Methods & Shortcuts
└── Approaches & Patterns
```

#### My Writing Errors

Continue to use:

```text
GET /api/study/practice/english/error-lab
```

No changes to the `ewp_error_lab` semantic contract are required for the rename.

#### Methods & Shortcuts

Use a new server-owned learner endpoint, for example:

```text
GET /api/study/improvement-lab/quant
```

#### Approaches & Patterns

Use a separate server-owned learner endpoint, for example:

```text
GET /api/study/improvement-lab/reasoning
```

Each section must have an independent loading, empty, and error state. A failure in one subject feed must not hide the other sections.

### 10.3 No raw library dump

The first personalized feed must not expose the full canonical strategy library. It should be derived from the learner's bounded, submitted-attempt history:

1. Load recent submitted attempts owned by the caller.
2. Load their response question IDs in a bounded batch.
3. Load currently verified linked strategies in a batch.
4. Deduplicate by strategy ID.
5. Aggregate evidence such as:
   - times seen;
   - wrong count;
   - correct count;
   - last seen time;
   - recent source question IDs.
6. Rank wrong-associated and recent strategies first, then by relevance and stable name ordering.

The feed remains a live projection. Withdrawn or inactive strategy content disappears from the learner feed without mutating historical attempts.

No saved-strategy table is required in v1.

---

## 11. Security and governance invariants

1. Learners never query governed strategy tables directly.
2. No new authenticated or anonymous table-read policy is added.
3. Every learner response is server projected.
4. Strategy and link verification are conjunctive.
5. Active state is checked at read time.
6. Governance fields are stripped explicitly, not merely ignored by the UI.
7. Optional strategy-read failure must not turn an otherwise valid review into a 500.
8. Attempt ownership and submitted-state checks run before learner review content is returned.
9. The strategy projection must never broaden question ownership or leak cross-question content.
10. Content Studio remains the governance authority.

---

## 12. Delivery sequence

### PR 1 — Quant review delivery

- normalized learner strategy contract;
- batched Quant read;
- mock review payload attachment;
- shared `SolutionStrategyPanel`;
- regular/generated-mock tests;
- no migration.

### PR 2 — Quant content readiness, if required

- authoring/editing/activation/question assignment if absent;
- verified test content and links;
- no learner-route redesign.

Do not open this PR when production-ready verified linked Quant content already exists through another governed intake path.

### PR 3 — Reasoning authority and Content Studio

- schema and indexes;
- RLS and privileges;
- lifecycle RPCs and audit;
- library, authoring, assignment, and review queue;
- no learner review display yet if the authority is not fully validated.

### PR 4 — Reasoning independent-question delivery

- batched Reasoning read;
- normalized projection;
- shared review payload and panel reuse;
- independent text-question coverage.

### PR 5 — Improvement Lab rename and shell

- canonical route and backward redirect;
- page rename;
- My Writing Errors preserved;
- empty Quant and Reasoning sections or feature-gated endpoints as appropriate;
- independent section states.

### PR 6 — Personalized Quant and Reasoning feeds

- bounded attempt-history aggregation;
- evidence summaries;
- ranking;
- live verification filtering;
- no planner writes.

### PR 7 — Reasoning set/stimulus delivery

- stimulus-strategy authority;
- set-aware review contract;
- grouped rendering;
- no non-verbal scope.

### Later work

- planner routing;
- Calculation Gym recommendations;
- speed and calculation-gap evidence;
- target solve-time claims backed by real reviewed attempt data;
- saved strategies;
- non-verbal Reasoning.

---

## 13. Required tests

### 13.1 Quant backend

- multiple question IDs use one link query and one heuristic query;
- verified link plus verified active heuristic included;
- pending/rejected link excluded;
- pending/rejected/`needs_correction`/inactive heuristic excluded;
- learner projection strips every governance field;
- deterministic ordering;
- no cross-question leakage;
- empty input performs no reads;
- optional read failure produces empty lists and preserves the review response;
- regular and generated mocks share the behavior;
- unsubmitted attempts remain inaccessible.

### 13.2 Reasoning backend

- equivalent batched-read and projection tests;
- lifecycle transition matrix;
- status and content-revision CAS;
- audit reason required;
- service-role-only RPC posture;
- verified strategy plus verified link required;
- no Quant/Reasoning cross-source leakage.

### 13.3 Frontend review

- panel renders only in review mode;
- panel absent during active attempts;
- missing and empty arrays render nothing;
- raw LaTeX is wrapped and rendered through existing KaTeX support;
- Quant fields render with learner labels;
- Reasoning `key_observation` renders;
- shared behavior works for MCQ, numerical, and statement-based renderers;
- existing explanations remain unchanged;
- old review payloads remain valid.

### 13.4 Improvement Lab

- canonical route renders the renamed page;
- old route redirects or aliases;
- English data continues to use the existing endpoint;
- Quant and Reasoning sections have independent states;
- one failed section does not suppress successful sections;
- personalized feed is owner scoped and bounded;
- withdrawn strategy disappears from subsequent reads.

### 13.5 Reasoning sets

- set strategy renders once;
- per-question strategy remains local;
- no duplicate strategy cards across a grouped set;
- shared text/table stimuli remain intact.

---

## 14. Acceptance criteria

The initial Quant learner-delivery slice is complete when:

- submitted regular and generated mock reviews return `solution_strategies` per question;
- the backend performs batched verified-only reads;
- the frontend renders Solution Strategy after the question solution only in review mode;
- no governance field reaches the learner payload;
- no RLS relaxation or migration is introduced;
- empty strategy content does not affect review usability;
- focused and affected regression suites pass;
- the implementation PR updates the execution checklist and central repository checklist row it changes.

Reasoning is complete only when its governed authority, Content Studio workflow, independent-question learner delivery, and later set-aware requirements have each passed their own PR gates.

---

## 15. Decision record

Locked decisions as of 2026-07-14:

1. The learner parent surface is **Improvement Lab**.
2. English appears as **My Writing Errors**.
3. Quant appears as **Methods & Shortcuts**.
4. Reasoning appears as **Approaches & Patterns**.
5. Per-question instructional content is labelled **Solution Strategy**.
6. Internal Quant schema and admin terminology remain **Quant Heuristic**.
7. Quant and Reasoning use distinct governed backend authorities.
8. The existing English Error Lab read model is preserved.
9. Immediate question review remains the first delivery target.
10. Improvement Lab composition and personalization follow in separate PRs.
11. Reasoning set-aware delivery is separate from independent-question delivery.
12. Raw `applicability_rule` is omitted from learner v1.
