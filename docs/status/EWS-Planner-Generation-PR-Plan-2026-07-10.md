# EWS / EWP Delivery PR Plan — Planner Generation + Prompt Ops + SP1b Shadow + `submitted_at`

> **Created 2026-07-10** against `main @ e739007` (#944 merged). Branch owner:
> `claude/ews-planner-generation-kqbo7i`. This is a focused execution plan for the
> four-item slice below. It does **not** restate the broad EWP arc — see
> `docs/status/career-copilot-pr-plan.md` (EWP-1…EWP-7) and
> `docs/architecture/english-writing-practice.md` §11 for the standing contract, and
> `docs/status/career-copilot-checklist.md` for the authoritative status of record.

## Scope of this plan

| # | Item | Nature of remaining work |
|---|---|---|
| 1 | Planner **generation** of `english_writing_session` tasks | **CODE — greenfield** (EWP-5) |
| 2 | `sentence_construction` prompt-bank ops (import → verify → activate → surface) | **OPERATIONS** (lifecycle code-complete) + small doc-fix |
| 3 | SP1b semantic provider adapter, SHADOW-only | **OPERATIONS** (adapter code merged) + doc-drift cleanup |
| 4 | Track `submitted_at` separately | **CODE — small**, gated on a design decision (data-quality, not a launch blocker) |

## Parallel-work reconciliation (checked 2026-07-10)

Investigated across sessions/branches to avoid duplicating already-landed work.
Reconciled against `origin/main @ e739007`:

- **Item 3 (SP1b) is already implemented and merged to `main`.** `semantic_evaluator.py`
  (`SemanticLanguageEvaluator`, shadow-only seam, migration 235 telemetry, 16 tests) is
  present on `origin/main` — identical blob on this branch. It is **not** a re-implementation
  task. (An earlier investigation flagged it as branch-unique; that was a stale `origin/main`
  ref before fetch. Confirmed: `git log origin/main..HEAD` is empty; SP1b is on `main`.)
- **Item 2's lifecycle is code-complete on `main`** — migrations 214/215/218/226,
  `content_studio` router, applicability resolver, `content_studio.activate` permission and
  the `cms_activate_writing_prompt` precondition machine. The runtime allowlist
  `cms_writing_runtime_ready_types()` = `['sentence_construction']`. **Zero prompts exist in
  any DB**; 270 seed rows (50 `sentence_construction`) are repo-authored JSON only.
- **Item 4's column already exists** (`writing_sessions.submitted_at`, migration 205) and is
  **never written**; `completed_at` was wired by migration 238 / #936 and is live-validated.
- **Item 1 is genuinely unstarted** on this branch (no half-implemented planner-writing path;
  no TODO/FIXME markers in `planner.py`). The launch/render half is shipped and live-validated
  (#941/#943).

**Net:** only items **1** and **4** require product-source code. Items **2** and **3** are
operator/evidence execution plus minor documentation corrections.

---

## PR-A — Planner generation of `english_writing_session` tasks (Item 1) · EWP-5

**Status:** PLANNED — greenfield. This is the deferred EWP-5 "planner **generation**" slice
(`career-copilot-pr-plan.md:386`, checklist EWP-5 "not started").

**Goal:** the deterministic planner auto-creates real EWP writing `study_tasks` (rows) instead
of those rows being operator-created. Consumes the already-shipped launch/render half.

**Design contract:** `docs/architecture/english-writing-practice.md` §11 (§11.1 launch columns,
§11.2 writing task types, §11.3 scheduling triggers). Pattern to mirror: the shipped PYQ
resolver PR-9 (`planner.py::_build_tasks` stamping `launch_type='pyq_practice'`;
`pyq_practice_launch.py`).

**Write scope:**
```
app/backend/app/study_os/planner.py
  _task_type()        (~L617)  introduce writing task types (or parallel writing path)
  _TASK_LABEL         (~L106)  labels for writing types
  _build_tasks()      (~L702)  writing-task branch; launch-stamp block ~L776–789
  _compute_plan()     (~L1052) wire writing-task emission into the plan
app/backend/tests/study_os/test_planner*.py   (generation + dedup tests)
docs/status/career-copilot-checklist.md       (EWP-5 + "Planner task deduplication" rows)
docs/status/EWS-Planner-Generation-PR-Plan-2026-07-10.md (this row)
```

**Contract for emitted rows** (shape `compute_action` already expects; no launch/render change):
- `task_type` = a writing type (e.g. `sentence_construction`); reuse the constant
  `LAUNCH_ENGLISH_WRITING_SESSION` from `writing_practice/launch.py` — no new literal.
- `launch_type = 'english_writing_session'`, `launch_entity_id = NULL`,
  `launch_context = {"exercise_type": <type>}`.
- Prompt selection stays server-side at launch time (`_select_launch_prompt`), so
  `launch_entity_id` is null by design — **no planner-side prompt selection.**

**Scheduling triggers (§11.3):** read `user_topic_error_patterns` (grammar/error signal →
correction drills) and `user_topic_mastery.next_revision_at` (hard revision trigger). The
planner already loads `error_topics` (`_load_user_signals_ex` ~L377) but only as a scoring
nudge — it must be extended to *spawn* writing tasks.

**Must include — deduplication** (checklist "Planner task deduplication", PLANNED, blocked on
EWP-5): retests/re-plans must not duplicate an open `english_writing_session` task for the same
topic/exercise. `_persist` (~L838) already inserts arbitrary task dicts, so persistence needs no
change once dedup is in `_build_tasks`.

**Constraint:** during shadow the planner personalizes from the effective-evidence fold
(`effective_user_topic_mastery_evidence`, §4.12d), never raw `user_topic_mastery` writing
deltas until Lane A `FF_MOCK_MASTERY_WRITES=live`. Generation itself is **not** blocked on Lane A
(it emits tasks; it does not write mastery).

**Gate:** deterministic, no AI/no randomness (planner module contract). No migration/RLS change.

**Serial/parallel:** self-contained to `planner.py` + planner tests — safe to own in one agent.
Does **not** touch routing/AdminShell. Can run concurrently with PR-D (item 4, different files).

---

## PR-B — `sentence_construction` prompt-bank operations (Item 2)

**Status:** LIFECYCLE CODE-COMPLETE / **OPERATOR PENDING** — this is an operations run, not a
build. Produces a dated evidence doc; the only code change is a stale-doc correction.

**Goal:** import → verify → activate more `sentence_construction` prompts and confirm Study Home
surfaces them.

**Operational procedure** (no direct SQL; all writes go through the audited `content_studio`
RPCs):
1. Author rows into `app/supabase/seeds/writing_prompts/01_sentence_construction.json` via
   `build_seed.py` (unique `external_key`, baked `topic_id`/`microtopic_id`, `prompt_text`,
   `required_words`, `difficulty_level`, min/max words).
2. Preflight taxonomy: `EWP_PG_DSN=… python3 preflight_ids.py` (must pass, else remap IDs).
3. Provision operator app-metadata: `content_studio.author` / `content_studio.review` /
   `content_studio.activate` + `exam_intelligence.manage` / `exam_intelligence.review`.
4. Import → `POST /api/admin/content-studio/writing-prompts/bulk` (Content Studio Bulk Import UI
   or `to_api_envelope.py` + curl). Lands `pending` / `is_active=false`, atomic all-or-nothing.
5. Verify → Review Queue → `.../writing-prompts/{id}/review` (`status=verified`, CAS tokens).
6. Applicability → propose target (`.../targets`, manage) then **review→active**
   (`.../writing-prompt-targets/{id}/review`, review). Without an ACTIVE target, activation is
   blocked (`no_active_applicability_target`).
7. Activate → `.../writing-prompts/{id}/activate` (`content_studio.activate`).
   `sentence_construction` passes `cms_writing_runtime_ready_types()`; other types are blocked.
8. Confirm surfacing → a planner (PR-A) `english_writing_session` task in the prompt's
   topic/exam scope renders "Start sentence practice" on Study Home →
   `POST /api/study/tasks/{id}/launch-writing` selects the prompt (verified ∧ active ∧
   `sentence_construction` ∧ default-deny applicability match).

**Blockers (operator, not code):** migration apply order 213→214→215→216→217→218→226(+234
grants) is operator-pending (live `schema_migrations` attested at 212); `content_studio.activate`
provisioning pending; 270-prompt review-lifecycle run pending before aspirant launch.

**Small code slice (doc-fix):** `docs/status/ewp-prompt-bank-frontend-handoff.md` says "There is
NO activate control" and `language_evaluator.py::get_writing_llm_eval_flag` docstring says
"SCAFFOLD ONLY … no real semantic/LLM adapter ships" — **both stale** (migration 226 shipped
activate; SP1b shipped the adapter). Correct the drift.

**Write scope:** `app/supabase/seeds/writing_prompts/*` (new rows), a dated evidence doc under
`docs/audits/`, `docs/status/ewp-prompt-bank-frontend-handoff.md` (drift fix), checklist rows
394–399/439. **Do not** add `/admin/english` or reintroduce the paused "Prompt Bank" tab
(IA lock).

**Dependency:** step 8 surfacing confirmation depends on **PR-A** (a planner-generated task) —
or, interim, an operator-created task per the already-validated Follow-up B path.

---

## PR-C — Continue SP1b semantic adapter in SHADOW-only (Item 3)

**Status:** ADAPTER CODE MERGED (`main`) / **VALIDATION PENDING** — evidence collection, not a
build. Promotion to LIVE is BLOCKED (§16 metrics + operator sign-off).

**Goal:** run SP1b in shadow to collect correction/grammar/vocab evidence. **NOT** for
`sentence_construction` (enforced by `_is_source_dependent()` in `language_evaluator.py`;
construction prompts stay on the deterministic mock).

**Shadow-only enforcement (already structural, do not weaken):** `FF_WRITING_LLM_EVAL ∈
{off,shadow,live}` fails closed to `off`; `get_semantic_shadow_evaluator()` returns the adapter
only when `=shadow`; canonical `get_language_evaluator()` always returns the mock; shadow output
writes only to append-only `writing_language_evaluator_runs` (role CHECK `shadow`, service-role
only, immutability trigger); no raw text persisted (SHA-256 `input_hash` only); the probe is
wrapped in try/except and discarded for authority.

**Operational run:** set `FF_WRITING_LLM_EVAL=shadow` + a real `ANTHROPIC_API_KEY` on the eval
worker; run `run_worker_pass` over correction/grammar/vocab jobs; collect
`writing_language_evaluator_runs` telemetry; begin the §16 gate-5 / §5.2 evidence window
(≥500 human-labelled samples/type: FP ≤5%, FN ≤10%, source-mismatch precision ≥90%, p95 ≤8s,
cost ≤$0.02/unit, zero determinism regressions). LIVE stays blocked pending that window +
operator sign-off.

**Model-id note:** default `EWP_SEMANTIC_MODEL=claude-opus-4-7` and the in-file pricing table
list opus-4-7/4-6 + sonnet-4-6; these can be refreshed to current model ids via env (no code
change) when the shadow run is provisioned.

**Write scope:** a dated shadow-evidence report under `docs/audits/`, checklist EWP-SP1b row.
Optional: fold the stale-docstring fix into PR-B rather than duplicating here.

**Dependency:** none on PR-A/PR-B (source-dependent types only). Fully parallelizable.

---

## PR-D — Track `submitted_at` separately (Item 4)

**Status:** PLANNED — small; **data-quality gap, explicitly not a launch blocker.** Requires a
design decision before code.

**Facts:** `writing_sessions.submitted_at` (migration 205:206) exists but is written by no path.
`completed_at` is written by the rollup (migration 238 / #936) and live-validated. Attempt-level
`writing_unit_versions.submitted_at` **is** written (`NOT NULL DEFAULT now()` per unit-version
insert). The gap is the **session-level** `submitted_at`, tied to the exam-mode `'submitted'`
status which is unimplemented (EWP ships learning-mode only).

**Decision required (do not drop in an arbitrary value — migration 238 deliberately deferred
this):**
- **Option A (minimal, learning-mode):** stamp `submitted_at = COALESCE(submitted_at, now())` in
  the rollup at the first transition where every unit has a submitted version (session first
  leaves `active`). `CREATE OR REPLACE FUNCTION ewp_private.ewp_apply_session_rollup` (new
  migration slot **240**) + parity in `session_finalizer.py`.
- **Option B (correct long-term, larger):** implement the exam-mode session-submit RPC/endpoint
  (`→ submitted`, lock answers, stamp `submitted_at`) — blocked on unbuilt EWP exam-mode runtime.

**Recommendation:** Option A for the data-quality fix now; leave Option B to the EWP exam-mode
track (EWP-7). Confirm with owner before choosing, since 238's authors intentionally left it
unwritten.

**Write scope (Option A):**
```
app/supabase/migrations/240_ewp_rollup_submitted_at.sql   (CREATE OR REPLACE rollup)
app/backend/app/study_os/writing_practice/session_finalizer.py  (Python parity)
app/backend/tests/study_os/test_ewp_rollup_*_migration.py       (extend existing pattern)
docs/status/career-copilot-checklist.md                         (Follow-up A row)
```

**Migration discipline:** 240 is the next free slot (238/239 taken); rollup change is a
`CREATE OR REPLACE`, no schema/RLS change (column already exists). Mark `CODE-FIXED, VALIDATION
PENDING` until staged and live-verified (`submitted_at` populates end-to-end).

**Serial/parallel:** touches the rollup function + finalizer — disjoint from PR-A's `planner.py`.
Safe to run concurrently with PR-A.

---

## Parallelization map

| PR | Files owned | Can run concurrently with |
|---|---|---|
| **PR-A** planner generation | `planner.py` + planner tests | PR-C, PR-D |
| **PR-B** prompt ops | seeds, audit doc, handoff/checklist docs | PR-C, PR-D (surfacing step depends on PR-A) |
| **PR-C** SP1b shadow run | audit doc, checklist | PR-A, PR-B, PR-D |
| **PR-D** `submitted_at` | rollup migration 240 + `session_finalizer.py` | PR-A, PR-C |

- None of these touch routing / AdminShell / `adminRoutes.jsx` — the serial-delivery rule does
  not bind this slice.
- **PR-A is the critical path**: item 2's surfacing confirmation and the product goal ("planner
  creates real EWP tasks automatically") both hinge on it.
- PR-C and PR-D are independent and may be dispatched immediately.

## Cross-references

- `docs/architecture/english-writing-practice.md` §11 (planner integration contract), §4.3/§4.3a
  (session status semantics), §16 / §5.2 (SP1b evidence gates).
- `docs/architecture/ewp-semantic-evaluator-adapter.md` (SP1b shadow authorization).
- `docs/status/career-copilot-pr-plan.md` EWP-5 (line ~358–386, planner generation deferral).
- `docs/status/career-copilot-checklist.md` (EWP-5, Planner task deduplication, Follow-up A/B,
  EWP-SP1a/SP1b, prompt-bank review rows).
- `docs/status/ewp-prompt-bank-frontend-handoff.md` (Content Studio API surface; **note the
  stale "no activate control" line — corrected by migration 226**).
