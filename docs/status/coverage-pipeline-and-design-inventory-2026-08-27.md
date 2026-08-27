# Coverage/Scoring Pipeline Root Cause + repoadditions Design Inventory — 2026-08-27

> **Investigation-only findings record.** No code changed. Two independent
> parts, kept separate below (they share no root cause). Part A diagnoses why
> `exam_topic_coverage` reads as empty/unprioritised despite "successful"
> derive/compute runs; Part B inventories the design mockups under
> `repoadditions/` against the real current backend. Line numbers are against
> `main @ ff6bccc`.

---

## Part A — Coverage/scoring pipeline

### TL;DR

The scoring→coverage→surface pipeline is a **four-step chain with two manual
lock gates**, and running only `compute` + `derive` (as reported) crosses
neither gate. Both endpoints return honest "success" counts for the rows they
touched, but those rows are **drafts that (a) carry no real evidence and (b)
never reach any learner surface** — so the whole thing is silently
non-functional end to end. This is confirmed from code. The *specific*
"reviewer_status / exam_priority_score are null" observation is **physically
impossible** for a real `exam_topic_coverage` row (both columns are
`NOT NULL DEFAULT`), so that particular symptom points at an empty/absent read,
not a bare row — needs one live query to pin which (queries given at the end).

### The intended pipeline vs. what a compute+derive run actually does

```
1. compute  → writes exam_topic_score_snapshots  status = 'draft'
2. LOCK     → operator PATCHes each snapshot  draft → reviewed → locked   (MANUAL, no automation)
3. derive   → reads ONLY locked snapshots, writes exam_topic_coverage  reviewer_status = 'draft'
4. LOCK     → operator PATCHes each coverage row  draft → reviewed → locked (MANUAL, no automation)
             ↑ only 'locked' coverage reaches Study OS / learner surfaces
```

### Confirmed defect 1 — `compute` writes *draft* snapshots; `derive` reads only *locked* snapshots (no auto-lock between them)

- `compute_exam_topic_scores` writes every snapshot with `"status": "draft"` —
  `app/backend/app/exam_intelligence/score_snapshots.py:418` (function at `:123`).
- `derive_topic_coverage` sources its evidence numbers **only** from
  `locked_score_snapshots` — `app/backend/app/exam_intelligence/coverage_derivation.py:609`.
  `locked_score_snapshots` filters `.eq("status", "locked")` **and**
  `.eq("model_version", MODEL_VERSION)` — `score_snapshots.py:495-496`.
- Locking is a **separate manual endpoint**:
  `PATCH /score-snapshots/{id}/review` (`app/backend/app/api/admin_exam_intelligence.py:2979`),
  transition matrix `draft → reviewed → locked` (`:2871`). The compute endpoint
  (`:3080`) does not lock; there is no scheduler or piggy-back (OD-4, by design).

**Consequence:** unless an operator locks the 290 computed drafts *first*,
`derive`'s `snapshot_by_topic` (`coverage_derivation.py:612`) is empty. `derive`
then builds its topic universe from verified syllabus mentions only
(`:621`), and every coverage row it proposes gets
`exam_priority_score = (snapshot or {}).get(...) or 0 → 0` and
`is_high_yield = False` (`coverage_derivation.py:359-360, 333`). So even a
"successful" derive produces **zero real prioritisation** — priority 0,
not-high-yield — which is functionally "no scoring."

### Confirmed defect 2 — `derive` writes *draft* coverage; only *locked* coverage reaches learners (no auto-lock)

- `derive` writes coverage rows with `"reviewer_status": "draft"`
  (`coverage_derivation.py:365`).
- Learner/Study-OS consumption is gated on `locked`: "Only `locked` rows reach
  the Study OS" (`admin_exam_intelligence.py:245`); the status rollup counts
  `locked_coverage = coverage_counts.get("locked", 0)` (`:302`). Promotion is
  again the separate manual `PATCH /topic-coverage/{id}/review` (`:2979` region
  / `CoverageReviewBody` at `:845`).

**Consequence:** draft coverage rows — even correctly-scored ones — never
surface. The "By Subject – High-Yield" chart therefore has no locked coverage
to read and falls back to raw verified-tag counts (`/pyq-summary` `by_subject`),
exactly as reported.

Both endpoints' summaries (`written` / `updated` / `skipped`) report **rows
touched**, never **rows locked/surfaced** — which is why every run "looks
successful" while nothing user-facing changes.

### The "null reviewer_status / null exam_priority_score" symptom is not a real row

`exam_topic_coverage` (migration `030_exam_registry_cycles_phases.sql:95`) is
`NOT NULL DEFAULT` on exactly these columns:

- `exam_priority_score numeric(5,2) not null default 0` (`030:106`)
- `reviewer_status text not null default 'draft'` (`030:113`)
- `source_basis text not null default 'manual'` (`030:110`), plus
  `coverage_depth`/`is_high_yield`/`confidence_score` (`:103,107,108`).

A materialised coverage row therefore **cannot** have null `reviewer_status`
or null `exam_priority_score`. The operator's "genuinely absent, not zero"
reading is one of:

- **(a) an empty/absent result** — the read returned no coverage row for those
  topics at the queried scope, and the UI rendered the missing columns as blank
  (a LEFT-JOIN-style null of the 456-topic catalog against an empty or
  differently-scoped coverage set); or
- **(b)** rows that exist as `draft` / priority `0` (defect 1: snapshots never
  locked) that were perceived as empty.

Which one it is cannot be settled from code alone — see live checks.

### Verdicts on the prompt's four hypotheses

- **Preflight #2 (null reviewer_status treated as reviewed/locked → skip
  forever):** *Not as framed.* `derive` never treats null status as locked, and
  `reviewer_status` can't be null. **But a real, related hazard exists:** the
  §5.2 conflict matrix only ever writes rows `derive` *owns*
  (`source_basis='evidence_derived'` + an owned `model_version`,
  `coverage_derivation.py:78-85`). Any pre-existing row with a different/unknown
  `source_basis` at the derive scope is **skip-forever** — never populated
  (`coverage_derivation.py:714-824`, esp. the "unknown/legacy source_basis →
  skip+delta" fallthrough `:820-824`). No migration seeds bare shells today
  (`grep` found no `INSERT INTO exam_topic_coverage` in `app/supabase/migrations/`),
  so this is latent rather than the current cause — but if coverage rows are
  ever bootstrapped with the table default `source_basis='manual'`, `derive`
  would permanently refuse to fill them.
- **Preflight #3 (does `written` count rows that got real values, or just
  inserts?):** *Disconfirmed.* `_proposed_row` always sets
  `exam_priority_score` (snapshot value **or 0**) and `reviewer_status='draft'`
  (`coverage_derivation.py:359,365`); the insert path increments `written` only
  on a real insert (`:679-680`). So `written` counts real, non-null-valued
  inserts — it never counts null-valued rows. The nulls the operator saw are
  therefore not `derive`'s output.
- **Preflight #4 (column / scope mismatch write vs read):** *No column-name
  mismatch.* The read maps `exam_priority_score → priority_score` and
  `reviewer_status → status` (`admin_exam_intelligence.py:832,837`) — same
  columns the write path populates. There **is** a **scope** difference worth a
  live check: the read (`GET /topic-coverage`) filters on `exam_id` only, across
  **all** cycles/phases (`:754-760`), whereas `derive` writes strictly at
  `exam_cycle_id IS NULL` + (`exam_phase_id IS NULL` exam-wide **XOR** one phase)
  (`coverage_derivation.py:304,306-309`). If the actual "High-Yield" chart uses
  a *different* read than `GET /topic-coverage` (e.g. a catalog LEFT JOIN, or a
  phase/cycle-scoped filter), that read — not this endpoint — is where the
  null columns come from.

### Confirmed root cause (what to put in the fix prompt)

The pipeline is **structurally gated behind two manual lock steps with no
automation and no "you are not done yet" signal**, and a compute+derive run
crosses neither. Result: draft snapshots that are never locked (so derive
scores everything 0) and draft coverage that is never locked (so nothing
reaches learners). This is fully confirmed from code and is independent of the
exact `written=456`/`skipped=456` history.

**Still needs a live check** to settle the exact `null`/`456` observation
(which of (a)/(b) above, and whether any coverage rows exist at all):

1. **Coverage rows & scope:**
   `SELECT reviewer_status, source_basis, count(*),
    exam_cycle_id IS NULL AS cycle_null, exam_phase_id IS NULL AS phase_null
    FROM exam_topic_coverage WHERE exam_id = '<upsc-cse id>'
    GROUP BY reviewer_status, source_basis, cycle_null, phase_null;`
   — 456 `draft`/`evidence_derived` exam-wide rows ⇒ defect 1/2 (never locked);
   0 rows ⇒ derive's writes didn't persist at the read's scope.
2. **Snapshot lock state:**
   `SELECT status, count(*) FROM exam_topic_score_snapshots
    WHERE exam_id='<upsc-cse id>' AND model_version='v1.0' GROUP BY status;`
   — expect ~290 `draft`, 0 `locked`, directly confirming defect 1.
3. **Chart source:** identify the exact backend read behind "By Subject –
   High-Yield" (frontend `PyqSummaryCharts.jsx` / its endpoint) and confirm
   whether it reads *locked* `exam_topic_coverage` or `/pyq-summary` tag counts,
   and whether it LEFT-joins the topic catalog (the origin of the null columns).

### Recommended fix approach (described, NOT implemented)

- **Bridge/expose the lock gates for the operator flow.** Either (i) an explicit
  single "publish scores" operator action (behind `exam_intelligence.manage`,
  audited) that transitions the computed snapshots draft→locked, runs derive,
  and transitions the derived coverage draft→locked — honouring, not bypassing,
  the review lifecycle; **or** (ii) at minimum make the endpoints' responses and
  the admin UI **distinguish "drafted" from "locked/surfaced"** (e.g. compute
  returns `written=290 draft (0 locked)`, derive surfaces "N draft coverage rows
  — not yet visible to learners until locked"), so a compute+derive run can no
  longer *look* complete.
- **High-yield chart honesty:** when no locked coverage exists, the chart should
  render an explicit "prioritisation not published yet" state instead of
  silently substituting raw verified-tag counts styled as prioritisation.
- Confirm the chosen scope for coverage reads matches the derive write scope
  (exam-wide `cycle=null, phase=null`) before wiring the chart to
  `exam_topic_coverage`.

---

## Part B — repoadditions inventory

Files: `repoadditions/docs/design/README.md`,
`.../calendar-study-planner/Main.dc.html`,
`.../essay-idea-and-spine-builder/{Main,IdeaCanvas}.dc.html` + `canvas.json`,
`.../exam-study-roadmap/Main.dc.html`, and
`repoadditions/docs/status/PYQ-Tagging-and-Essay-Brainstorm-UI-Status-2026-08-25.md`.
`.dc.html` = throwaway "Claude Design" preview markup (not React); the README
is explicit these are interaction/layout references to re-implement fresh in
React 18 + Tailwind + TanStack Query + recharts, not port.

### 1. essay-idea-and-spine-builder — closest to build-ready

- **UI (2 artboards):** (a) *Idea Canvas* — a freeform mind-map: the essay
  topic centred, 6 draggable "angle" branches (Economic, Social Equity,
  Governance, Global/Comparative, Historical, Personal), sticky notes dragged
  anywhere, and a right-hand *Helpers* panel (vocabulary, quotes, books+authors,
  examples, stats-to-verify) whose cards drop onto the canvas. (b) *Spine* —
  sequences hook → thesis → reorderable body paragraphs → closing thought, with
  per-slot target word counts (~50 / 50 / 175-each / 100) and a live
  "planned vs. 1000–1200 words" bar; slots reject the wrong card type on drop.
- **Backend data model it assumes:** `essay_brainstorm_blocks` — **exists**,
  migration `265_essay_theme_taxonomy.sql:66`, alongside its parent
  `essay_themes` and `essay_pyq_tags`. Columns: `theme_id`→`essay_themes`,
  `block_type` (enum), `block_text`, `linked_gs_topic_id`→`topics`,
  `source_note`, `usage_count`, `created_by`, `metadata` (`265:66-82`).
  `/essay-themes` and `/essay-pyq-tags` CRUD endpoints exist
  (`admin_exam_intel_cms.py:3466+`); **15 themes + 100/100 essay PYQs are live**
  (status doc).
- **Gap vs. real backend:**
  - `essay_brainstorm_blocks` has **no endpoint** (grep: zero `essay_brainstorm`
    references under `app/backend/app`) and is **unseeded** — the UI has a home
    for its data but no API to read/write it yet.
  - **Taxonomy mismatch.** DB `block_type` enum = `hook, thesis, argument_for,
    argument_against, example, quote, counter_narrative, closing_thought`
    (`265:69-73`). The mockup's spine slots (hook / thesis / **body paragraphs**
    / closing) and helpers (quote, example) map cleanly, but: the 6 **angle**
    branches and the **vocabulary / books / stats** helpers have **no dedicated
    column** — they'd live in `metadata` or need new fields; and the DB's
    `argument_for` / `argument_against` are not surfaced by the mockup's generic
    "body paragraph." Freeform sticky-note **x/y positions** also have no
    schema (would go in `metadata`).
  - Net: schema fits the *storage* need; a thin blocks CRUD endpoint + a
    decision on where angles/positions/word-count targets live (metadata vs
    columns) is the outstanding work. README's "closest to build-ready" is
    accurate.

### 2. calendar-study-planner

- **UI:** weekly drag-and-drop planner — 7-day grid (Mon–Fri 2h cap, Sat/Sun 4h
  cap), 14 GS1–4 topic blocks draggable between days and a backlog column, a
  per-day capacity bar that turns red over cap, and a "carried over" tag demoing
  buffer-rollover.
- **Backend data model it assumes:** a per-day topic **assignment** with a
  manual-override write path, on top of the server-side prioritised topic list.
- **Gap vs. real backend:**
  - The prioritiser **exists** (`app/study_os/planner.py`, plus
    `plan_timeline.py` / `plan_impact.py` / `plan_preferences.py`); plan storage
    exists (`study_plans` `002:71`, `study_plan_versions` `033:88`,
    `user_study_plan_preferences` `061:8`).
  - **No day-assignment / weekly-grid table** and **no manual-override write
    path** (grep: no `plan_day` / `day_assignment` / `scheduled_topic` table).
  - **No `estimated_hours`** anywhere on `topics` (grep: zero hits), so the
    2h/4h capacity math and any duration have **no data source** — matches the
    status doc's known gap. Needs new backend (day-assignment table + per-topic
    hour estimates) before a real build.

### 3. exam-study-roadmap

- **UI:** macro cycle view (not a weekly grid) — one winding path across
  Foundation → Build → Prelims-intensive → Mains-consolidation → Interview,
  with clickable checkpoint/mock/exam-day nodes and a track toggle
  (full / prelims-only / mains-only) that dims non-matching nodes. Week
  numbers, dates and node content are **sample data**.
- **Backend data model it assumes:** an exam-cycle calendar — start date, phase
  boundaries, milestone list.
- **Gap vs. real backend:** `exam_cycles` / `exam_phases` exist as **identity**
  rows (`030_exam_registry_cycles_phases.sql`) but carry **no calendar
  semantics** — grep for `start_date` / `end_date` / `milestone` / `calendar`
  in `030` returns nothing. So phase boundaries, dates and milestones have no
  schema at all. Furthest from build-ready; needs the most new backend.

### Cross-cutting facts (verified, for the eventual build session)

- The "365 micro-themes" already exist as `topics` rows with `level='microtopic'`
  (`scripts/ingest_upsc_gs_syllabus.py`,
  `docs/reference/syllabus/upsc_cse_mains_gs_micro_themes_v2026.3.json`) — no new
  table needed for that part.
- Mastery is a continuous 0–100 `mastery_score` (not a discrete state enum),
  `_HIGH_YIELD_MASTERED_THRESHOLD = 75.0` in `report_cards.py` — reconcile
  before any syllabus-progress UI reads it.
- Suggested build order (per README, confirmed against schema): **essay tool
  first** (schema ready, only a blocks endpoint + taxonomy decision needed);
  calendar-planner and roadmap both need new backend tables before a real build.
