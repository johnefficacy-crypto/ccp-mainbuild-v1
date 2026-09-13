# PLAN-POOL-01 — Why the planner ranked 13 Prelims rows out of 1,510

Read-only investigation. No code, migration, or data changed.
Line numbers are against `main @ 2058441` (branch `investigate/plan-pool-01`).

---

## Answer in one paragraph

Elective scoping did not narrow anything. The **phase filter** did.
`load_scoped_coverage_checked` returns all 1,510 rows for this user — the 1,497
Mains rows survive because their `section_id` is NULL and the scoping filter
deliberately keeps unclassified rows (`planner.py:582-588`), and the 13
Prelims/CSAT rows survive because their sections are `compulsory` (migration 287
only marks `subjects.subject_group='upsc-optional'` sections elective). One line
later, `_compute_plan` asks the target-window resolver for a phase and, if any
coverage row carries that phase, **discards every row that does not**
(`planner.py:1526-1530`). The resolver returned the Prelims/CSAT phase
`6566d50e-…` — it only ever considers phases attached to the chosen verified
cycle (`exam_target_window.py:58`, templates excluded at `:57`), and the Mains
phase `626ec667-…` is the unattached template that the whole Mains corpus was
derived against (`workbench/scripts/lock_coverage.py:34`,
`scripts/ingest_upsc_gs_syllabus.py:34`). 13 rows matched, so the fallback at
`planner.py:1529` never fired and 1,497 rows left the candidate pool in one
list comprehension — silently, with no reason code and nothing in
`input_context`. The exact NULL/non-NULL correlation the operator saw is a
second, independent fact with the same cause (the derivation never writes
`section_id` — `coverage_derivation.py:387-400`); it is a *design finding*, not
this symptom's mechanism, and it means elective scoping is currently **inert on
every Mains row**.

---

## Q1 The filter chain

One `exam_topic_coverage` row, from `POST /api/study/plan/apply` to a
`study_tasks` insert. Every gate, in execution order.

### A. Route preconditions (before the planner)

| # | Gate | Location | Row fails when |
|---|---|---|---|
| A1 | canonical target flag | `app/backend/app/api/study_os.py:795` → `:132-153` | flag on and `profiles.target_exam` unset → HTTP 400 (whole request, not a row) |
| A2 | target-exam resolve, health-aware | `study_os.py:796` → `:105` | read failure → HTTP 503 `calibration_check_failed` |
| A3 | calibration gate | `study_os.py:117-128` | `calibration_required` true → HTTP 200 interstitial, planner never runs |
| A4 | planner invoked with `expected_exam_id` | `study_os.py:799` | — |

### B. `_compute_plan` preconditions (`planner.py:1416`)

| # | Gate | Location | Row fails when |
|---|---|---|---|
| B1 | `user_id` present | `planner.py:1433` | `no_user` |
| B2 | target exam resolves | `:1436` → `lookup.py:115` / `:151` | no profile target and no `aspirant_preferences.target_exams[0]` → `no_target_exam` (`:1449`) |
| B3 | exam is active | `lookup.py:41-54` (applies on cache hit too) | `exams.is_active is not True` → `InactiveExamError` → `exam_inactive` (`planner.py:1438-1447`) |
| B4 | TOCTOU guard | `:1451-1456` | resolved exam ≠ the one the gate checked → `target_changed` |
| B5 | target-window resolution | `:1459` | never fails; may return `target_phase_id = None` |
| B6 | `light`-exam activation | `:1466-1470` | `management_mode='light'` and the resolved cycle is not operational **and** `planner_activation_enabled` → `planner_activation_disabled` |

### C. Candidate-pool construction — `load_scoped_coverage_checked` (`:1492` → `:567`)

| # | Filter | Location | Row is dropped when |
|---|---|---|---|
| C1 | `exam_id` equality | `planner.py:335` | row belongs to another exam |
| C2 | `reviewer_status = 'locked'` | `:336` | draft / pending_review / reviewed / rejected |
| C3 | range pagination, `.order("id")` | `:270-304`, `:337-338` | never drops rows; a failed page returns a **prefix** and `complete=False` |
| C4 | topic must exist in the `topics` read | `:399` | topic id not returned by the chunked `in_` read |
| C5 | `topics.is_active is not False` | `:399` | topic deactivated |
| C6 | **elective scoping** | `:579-588` | `section_id` is non-NULL **and** not in the in-scope section set. **A NULL `section_id` is always kept** (`:587`) |
| C7 | read-health, fail closed | `:1492-1509` | any page read failed → `coverage_read_failed` (500), no plan |
| C8 | empty pool | `:1511-1514` | zero rows → `no_locked_coverage` |
| C9 | muted topics | `:1516` | `topic_id` in `user_study_plan_preferences.muted_topic_ids`; all muted → `all_topics_muted` (`:1518-1521`) |

C6 is where scoping lives, and the in-scope set is built by
`_in_scope_section_ids` (`:433-545`): phases of this exam (`:451-464`) →
their `exam_phase_sections` (`:468-484`) → `None` if the exam declares no
elective section at all (`:486-487`) → every non-elective section id (`:489-495`)
plus the elective sections whose `subject_id` appears in the user's
`user_exam_electives` row for that group (`:520-526`). Unresolvable stored
choices fall back to compulsory-only and log (`:528-545`).

### D. The phase filter — where 1,497 rows died

```python
# planner.py:1525-1530
resolver_phase_id = resolver_result["target_phase_id"]
if resolver_phase_id is not None:
    phase_coverage = [c for c in coverage if c.get("exam_phase_id") == resolver_phase_id]
    if phase_coverage:
        coverage = phase_coverage
```

| # | Filter | Location | Row is dropped when |
|---|---|---|---|
| D1 | `exam_phase_id == resolver_phase_id` | `:1528` | the row's phase is not the resolved target phase — **and at least one row does match**, so the `if phase_coverage` fallback (`:1529`) does not save it |

No reason code, no counter, no log. `input_context.locked_topic_count`
(`:1691`) is computed **after** this line, so the recorded value is the
post-filter count — which makes it the cheapest live proof (see probe §3).

### E. Scoring and ordering (no further exclusions)

| # | Step | Location | Effect |
|---|---|---|---|
| E1 | per-row score | `:1608-1643` → `_score_topic:848` | ranks only; never drops |
| E2 | sort desc | `:1645` | ranks only |
| E3 | prerequisite-aware reorder | `:1646` → `_order_topics:906` | reorders only; falls back to priority order on a cycle |
| E4 | **`ordered[:max_tasks]`** | `_build_tasks:991` | every row past `max_tasks` is dropped. `max_tasks` = `user_study_plan_preferences.max_tasks_per_day`, else `aspirant_persona_snapshots.study_policy.max_tasks_per_day`, else 4; clamped to 1..8 (`:1548-1562`) |
| E5 | writing tasks appended | `:1673-1680` | additive only |

### F. Persistence (`_persist:1202`)

| # | Step | Location | Fails with |
|---|---|---|---|
| F1 | reuse or insert `study_plans` (`_active_plan:1077`, `limit(1)`) | `:1246-1282` | `plan_persist_failed` |
| F2 | insert `study_plan_versions` | `:1284-1305` | `version_persist_failed` |
| F3 | delete today's `status='planned'` tasks for this plan | `:1316-1331` | `task_cleanup_failed` |
| F4 | **insert `study_tasks`** | `:1338-1352` | `task_persist_failed` |
| F5 | point plan at the new version + `active_phase_id` | `:1354-1370` | `plan_persist_failed` |
| F6 | `study_adaptation_events` audit | `:1379-1403` | `audit_persist_failed` (rolls back F1–F5) |

**Count of filters a row must survive to become a task: 9 pool filters
(C1–C6, C9 and the two pool-level refusals), 1 phase filter, 1 rank cut.**
Only C6 and D1 are new since #1100/#1102, and only D1 fired here.

---

## Q2 Phase resolution

`exam_phase_id` for plan generation is **not** read from the user, the exam row,
or the coverage rows. It comes from `resolve_exam_target_window`
(`planner.py:1459` → `exam_target_window.py:9`), which resolves it from the
exam's **cycles**:

1. Cycles: `exam_cycles` for this exam with `reviewer_status='verified'`
   (`exam_target_window.py:22-27`), minus `status='cancelled'` (`:28`); one is
   picked by `_pick_cycle` (`:162-196`) — active, else open, else the earliest
   `expected` with a future `exam_start`, else the most recent by `exam_start`.
2. Phases: all `exam_phases` for the exam (`:50-54`), then split —
   **`exam_cycle_id IS NULL` phases are templates and are never targeted**
   (`:56-57`); only `cycle_phases` (`:58`) enter the ladder.
3. Ladder: `manual_phase_id` (not passed by the planner) → **current phase**
   (`status='active'`, `phase_start <= today <= phase_end|NULL`, `:213-224`) →
   **next future phase** (smallest `phase_start > today`, status in
   expected/active, `:227-238`) → cycle `exam_start` (no phase, `target_phase_id`
   is then `None`) → `not_connected`.

With multiple phases in the chosen cycle, the tie-break is `phase_order` for the
current-phase branch (`:223`) and earliest `phase_start` for the future branch
(`:237`).

**Can this path resolve the Prelims phase for a `upsc-cse` user? Yes** — and on
the evidence it did: it is the only mechanism in the plan path that can reduce
1,510 rows to exactly the 13 that carry `6566d50e-…`, and the produced tasks are
Prelims-GS topics.

**What would make it prefer Mains?** The Mains phase would have to (a) be
attached to the chosen verified cycle — the repo's own operator scripts treat
`626ec667-…` as the exam-level Mains phase and the prompt calls it the template,
so today it is almost certainly `exam_cycle_id IS NULL` and structurally
unreachable (`exam_target_window.py:57`) — and (b) win the ladder: be the active
phase covering today, or have the earliest future `phase_start` among the
cycle's phases. Note the asymmetry this creates: a Mains phase that *is*
attached and *is* the target would flip the pool the other way and drop the 13
Prelims rows just as silently.

---

## Q3 Does anything require a non-NULL `section_id`?

Every read of `section_id` in the plan path — there are exactly three:

| Site | Location | Effect of NULL |
|---|---|---|
| SELECT list | `planner.py:330` | none; column is selected |
| carried onto the emitted row | `:424` | none; value is `None` |
| scoping filter | `:587` | **row is KEPT** — `if not c.get("section_id") or str(c["section_id"]) in scope` |

`grep section_id` across `app/backend/app/study_os/planner.py`,
`subjects.py` and `calibration.py` returns only those sites. No later stage —
scoring (`:1608`), ordering (`906`), `_build_tasks` (`981`), `_persist` (`1202`),
the `study_tasks` insert (`:1344`) — reads it at all. **Nothing re-filters on it.**

So the documented behaviour ("keep NULL as unclassified") is what the merged code
does, and the answer to the competing-explanations question is unambiguous:

- **Q2 is the cause.** The phase filter removed the 1,497 Mains rows.
- **Q3 is not.** Scoping removed nothing for this user: the Mains rows are kept
  as unclassified (NULL) and the Prelims/CSAT sections are `compulsory`, hence in
  scope by `:493-495`.
- They are not both true as explanations — but they are linked: the NULL
  `section_id` that makes scoping a no-op and the template phase that makes the
  Mains corpus unreachable were produced by the same derive-against-the-template
  load.

---

## Q4 Null `section_id` origin

**The code path.** The Mains rows were written by
`derive_topic_coverage` → `_proposed_row` (`coverage_derivation.py:353-400`).
That payload has exactly five identity keys — `exam_id`, `exam_cycle_id` (hard
`None`, `:389`), `exam_phase_id` (the scope argument, `:390`), `topic_id`
(`:391`) — and **no `section_id` key at all**. The column is nullable with no
default and no trigger (`030_exam_registry_cycles_phases.sql:100`), so every
derived row is NULL. The module's own scope contract says so: "exam-wide
(`exam_phase_id is None`) and phase-scoped only" (`coverage_derivation.py:38`) —
section-scoped derivation is not expressible.

Those rows are born `reviewer_status='draft'` (`:365`) and were promoted in bulk
by the operator script `workbench/scripts/lock_coverage.py` (PATCH
`/topic-coverage/{id}/review` → `locked`, `:99-112`), which is pinned to
`EXAM = 5466e62f-…` and `PHASE = 626ec667-…` (`:33-34`) — the Mains phase. That
is the same phase `scripts/ingest_upsc_gs_syllabus.py:34` seeded the GS syllabus
tree against. The optional papers followed the same route
(`lock_coverage.py --subjects optional`, `:62-64`).

Nothing on that route can set a section. The only two writers that *can* are:

- the CMS create endpoint, where `section_id` is an optional field validated
  against `exam_phase_sections` and required to match `exam_phase_id`
  (`admin_exam_intel_cms.py:2631-2633`, `:2674-2679`) — i.e. set only if the
  caller sends it; and
- the documented seed/import template, whose `exam_topic_coverage` INSERT
  **does not list the `section_id` column**
  (`app/supabase/seeds/templates/exam_intelligence_import_template.sql:159-168`).

**Should Mains coverage carry a section id?** Mains sections exist — migration
287's backfill marked twelve of them elective
(`287_exam_electives.sql:129-137`), and it keys on
`subjects.subject_group='upsc-optional'`, so those sections are real rows with
real `subject_id`s. The scope rule the migration states in one sentence — "a
subject is in scope if its section is 'compulsory', OR it is 'elective' and its
subject id is in the user's choice" (`287:15-17`) — is expressed **per section**,
and the only carrier from a coverage row to a section is
`exam_topic_coverage.section_id`. With that column NULL on all 1,497 Mains rows,
the rule is unreachable for Mains content.

So: **a derivation gap, with a design consequence.** The derivation was never
given a section dimension (it cannot express one), so the load could not have
produced anything else; but the elective-scoping design merged in #1100 assumes
the dimension exists. Both are true, and the net effect is the finding below.

---

## Corrections to stated facts

1. **"the planner ranked 13 rows out of 1,510" is right; "because of elective
   scoping" would be wrong.** Scoping returned all 1,510 for this user. Stated
   only because the observation sits next to the exact NULL/non-NULL
   correlation, which invites that reading.
2. **The correlation is exact but not causal.** `section_id` non-NULL on exactly
   the 13 Prelims rows and NULL on exactly the 1,497 Mains rows is a property of
   two different write paths, not of any filter the planner applies.
3. **Migration 287 is applied and correct, and it currently changes nothing for
   this user.** 12 elective sections exist; zero Mains coverage rows point at any
   section; the Prelims sections are compulsory. The scope intersection is
   therefore a no-op on this exam's coverage today.
4. **No code/live disagreement found.** Every live fact in the brief is
   consistent with the merged code. The one claim I could not verify from the
   repository is that `626ec667-…` is a *template* (`exam_cycle_id IS NULL`) — the
   repo only shows it used as the exam-level Mains phase; see Requires live data §1.

---

## Defects observed

- **D7 — the phase filter is silent and unreported.** `planner.py:1526-1530`
  removes 99.1 % of the candidate pool with no log line, no envelope field and no
  `input_context` counter; `locked_topic_count` (`:1691`) is measured after the
  cut, so the audit row records 13 and the 1,497 never existed as far as any
  surface is concerned. An aspirant whose plan is Prelims-only cannot tell
  whether Mains coverage is missing, unlocked, or filtered.
- **D8 — elective scoping is inert on UPSC Mains.** Because every Mains coverage
  row has `section_id IS NULL` and `planner.py:587` keeps NULL rows, the fix
  merged in #1100/#1102 excludes nothing on the Mains phase. The PSIR aspirant is
  not seeing Anthropology tasks because of the phase filter, not because of
  scoping. Every other consumer of `load_scoped_coverage` inherits this —
  calibration (`calibration.py:191`), the Subject Hub (`subjects.py:203`, `:407`),
  the plan timeline (`plan_timeline.py:705`), plan-by-subject
  (`plan_by_subject.py:91`), report cards (`report_cards.py:310`), the topics API
  (`api/study_os.py:1229`). If the target phase ever resolves to Mains, twelve
  optionals re-enter the pool. Live confirmation: probe §6.
- **D9 — `task_count=2` with 13 candidates.** `_build_tasks` slices
  `ordered[:max_tasks]` (`:991`); `max_tasks` defaults to 4 (`:118`,
  `:1554-1562`), so 2 implies an explicit `max_tasks_per_day = 2` in
  `user_study_plan_preferences` or in the persona snapshot's `study_policy`.
  Out of scope per the brief; probe §5 settles it.
- **D10 — `why_this_task` reported empty.** `_build_tasks` always builds a
  non-empty `why` dict (`:998-1037`) and assigns it at `:1054`, and `_why_summary`
  (`:935`) always returns a sentence. An empty value on a persisted row is
  therefore not producible by this path — the likely candidates are a read that
  selects a different column set or a client-side render, not the planner. Noted
  only; probe §7 captures the stored value.
- Both tasks scoring exactly `78.75` is consistent with `mastery=None` (the flat
  55-point cold-start gap, `_score_topic:874`) under `balanced` weights — i.e. no
  validated mastery and no self-assessment prior contributed. Not a defect;
  recorded because it means the ordering between the two was decided entirely by
  coverage priority, PYQ count and the high-yield bonus.

---

## Requires live data

Seven questions the repository cannot answer. SQL is in
`workbench/sql/PLAN-POOL-01_probe.sql`, SELECT-only, same numbering.

1. **Is the Mains phase `626ec667-…` attached to a cycle, or is it a template?**
   If `exam_cycle_id IS NULL` it can never be a plan target
   (`exam_target_window.py:57`) and the 1,497 Mains rows are structurally
   unreachable by the planner, for every user, until a cycle-attached Mains phase
   exists. → §1
2. **Which cycle does `_pick_cycle` choose, and which phase does the ladder
   return today?** This is the single fact that confirms Q2. → §2
3. **What did the plan actually record?** `study_plans.active_phase_id` and
   `study_plan_versions.input_context->>'locked_topic_count'` for plan
   `e87f1c91-…`. `locked_topic_count = 13` proves the phase filter fired;
   `= 1510` would falsify this whole report. → §3
4. **Provenance of the 13 vs the 1,497** — `source_basis`, `model_version`,
   `created_at`, `section_id` — i.e. which writer produced the Prelims rows, since
   no code path in the repo sets `section_id` on coverage except an explicit CMS
   payload. → §4
5. **Where does `max_tasks = 2` come from** — preference row or persona
   snapshot? → §5
6. **How many coverage rows would elective scoping actually exclude for this
   user?** Expected: zero. → §6
7. **Are the two persisted tasks' `why_this_task` payloads really empty?** → §7
