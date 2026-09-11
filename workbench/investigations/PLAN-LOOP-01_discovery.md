# PLAN-LOOP-01 — Discovery: what actually feeds the Study OS planner

Read-only investigation. No application code, migrations, or tests modified.
Every claim below cites `path:line` against the tree at commit `baeb2165`
(branch `investigate/plan-loop-01-discovery`, created from
`claude/quirky-allen-m8kwmw`, which has `main` @ `5f90e284` as an ancestor).

---

## Preflight results

**P1 — branch.** PASS with a deviation to record. The session's designated
development branch is `claude/quirky-allen-m8kwmw` (10 commits ahead of `main`,
`main` verified as an ancestor via `git merge-base --is-ancestor main HEAD`).
`investigate/plan-loop-01-discovery` was cut from that HEAD rather than from
`main` directly, so the recent optionals/PYQ-tagging commits are present. The
literal requirement — clean branch, `main` an ancestor of HEAD — holds.

**P2 — clean tree.** PASS. `git status --porcelain` was empty before any file
was created. The only new files are the two under `workbench/`.

**P3 — pre-existing event ledger.** PASS, but with two near-misses that a
future design must account for. **No generic cross-tool event ledger feeds the
planner.** Detail:

- `public.study_adaptation_events` (`app/supabase/migrations/033_exam_topic_analytics_snapshots.sql:102-115`)
  looks like an ingestion ledger — its `event_type` CHECK admits `mock_logged`,
  `task_completed`, `focus_session_completed`, `revision_overdue` — but it is an
  **output audit trail**, not an input. Its only writers are the planner itself
  (`app/backend/app/study_os/planner.py:1121`) and admin ops
  (`app/backend/app/api/admin_study_os.py:182`). Its only readers are UI
  changelog endpoints (`app/backend/app/api/study_os.py:797`,
  `app/backend/app/api/admin_study_os.py:520`). Nothing in `_compute_plan` reads
  it. The event types that sound like inputs are never emitted by the surfaces
  they name.
- `public.user_signal_events` (`app/supabase/migrations/052_persona_snapshots_and_signal_events.sql:50-67`)
  **is** a generic append-only ledger — `(user_id, event_type text, payload jsonb,
  processed_at)` — and its own comment at `:67-68` says the generic `event_type`
  exists so "future PRs (onboarding/study/focus/mock/eligibility) emit without
  schema changes". But it has exactly one writer
  (`app/backend/app/persona_questions/events.py:55`) and its consumer is persona
  recomputation (`app/backend/app/persona/queue.py:45`), not the planner. It is
  the closest existing substrate to reuse, and it changes the shape of any
  future emitter work — but it does not currently carry planner signal, so the
  survey continues rather than halting. **Flagging this explicitly so the
  decision can be overridden.**

Also inspected and ruled out: `mock_attempt_events`
(`app/supabase/migrations/138_mock_attempt_events.sql:10`) is per-attempt
telemetry/anti-cheat only; `writing_mastery_outbox`
(`app/supabase/migrations/205_english_writing_practice_schema.sql:740`) is a
writing-only transactional outbox; `quant_performance_signals`
(`app/supabase/migrations/245_quant_calc_gym_and_signals.sql:97`) is explicitly
"NEVER a `user_topic_mastery` writer" (`:93-95`).

**P4 — no live DB.** PASS. No database connection was opened and no credential
was read. Every finding comes from committed code, migrations, and schema.

---

## Answer in one paragraph

**No.** With one gated exception, performance from tools other than the mock
engine does not reach the planner. The planner's only per-user performance
inputs are `user_topic_mastery` (weakness term) and `user_topic_error_patterns`
(flat +10 error term), read at `app/backend/app/study_os/planner.py:409-419` and
`:439-449`. `user_topic_mastery` has exactly two writers: a full re-aggregation
from `mock_topic_breakdowns` triggered only by the manual mock-review PATCH
(`app/backend/app/study_os/mastery.py:215`, reached from
`app/backend/app/api/canonical.py:2365`), and an incremental per-attempt delta
RPC from the platform mock engine
(`app/supabase/migrations/145_mock_attempt_jobs.sql:60`, called at
`app/backend/app/study_os/mastery_writer.py:210`) which fires **only** when
`FF_MOCK_MASTERY_WRITES=live` **and** the user is on
`FF_MOCK_MASTERY_LIVE_USER_IDS` — both default to off/fail-closed
(`app/backend/app/study_os/mastery_writer.py:414-444`). The writing-practice
path — described in PRIMING as the known-working reference — does **not** write
`user_topic_mastery` at all; it writes a separate append-only
`user_topic_mastery_evidence` table
(`app/supabase/migrations/209_english_writing_practice_evaluator.sql:1155`),
whose `effective_user_topic_mastery_evidence` view is annotated "the ONLY
planner/level source (§4.12d)"
(`app/supabase/migrations/205_english_writing_practice_schema.sql:825`) yet is
read by **zero** Python call sites. Writing practice influences the plan only in
the output direction: the planner *emits* writing tasks
(`app/backend/app/study_os/planner.py:1370-1379`). PYQ practice, trap drills,
calc gym, essay builder, and eligibility contribute nothing to plan scoring.

---

## Q1 Mastery writers

Grepped three ways to establish exhaustiveness: the table name
`user_topic_mastery` (24 non-test files, Python + SQL + seeds), the column name
`mastery_score`, and the writer class `MasteryWriter`. There is no ORM model
class — every access is a Supabase PostgREST call or an RPC.

### W1 — `recompute_topic_mastery` (LIVE, manual-log mocks only)

| | |
|---|---|
| Path | `app/backend/app/study_os/mastery.py:155-259`; the write itself at `:213-231` via `_upsert` (`:90-112`) |
| Trigger | HTTP only: `PATCH` mock review in `app/backend/app/api/canonical.py:2365`, and **only** when the request body carries `topic_breakdowns` (`:2351`) |
| Input | `mock_topic_breakdowns.correct_answers` / `.wrong_answers`, joined through `mock_tests` for exam scoping (`app/backend/app/study_os/mastery.py:115-152`) |
| Derivation | `mastery_score = correct / (correct+wrong) * 100`, rounded to 2dp (`:206`). Raw accuracy — no prior, no decay, no trust weight |
| Overwrite vs accumulate | **Overwrite.** Re-aggregates *every* breakdown the user has ever had and replaces the row (`:215-231`) |
| Idempotent on replay | **Yes**, by construction — the docstring at `:5-9` states it, and the code never reads its own previous output |
| Live in production | **Yes**, unconditionally — no feature flag |

Scope key is `(user_id, topic_id, exam_id, exam_phase_id)` with `None` matched
as `IS NULL` (`app/backend/app/study_os/mastery.py:78-84`).

Note the input funnel: `mock_topic_breakdowns` has exactly **one** writer in the
whole repo — `app/backend/app/api/canonical.py:2362`, the same manual-review
PATCH. Platform mock attempts never produce breakdown rows. So W1's entire
evidence corpus is user-supplied self-reported topic tallies.

### W2 — `apply_mock_mastery_delta` RPC (LIVE but double-gated, default off)

| | |
|---|---|
| Path | SQL: `app/supabase/migrations/145_mock_attempt_jobs.sql:60-113` (insert at `:98`, update at `:101-103`). Caller: `app/backend/app/study_os/mastery_writer.py:203-217` (`_apply_mastery`) |
| Trigger | `MasteryWriter.process_attempt_sync` → `app/backend/app/study_os/mastery_writer.py:100-104`, reached from (a) the synchronous submit route `app/backend/app/api/mock_engine.py:245`, and (b) the `mastery_retry` job drained by `mock:sweeper` — `app/backend/app/study_os/mock_engine.py:1979-1984` |
| Input | `derive_from_analytics` over `mock_attempts` + `mock_attempt_responses` + `mock_attempt_response_classification`, via `load_mock_attempt_evidence` (`app/backend/app/study_os/mastery_writer.py:130-134`) |
| Derivation | Capped delta ±0.15 unit (`:28`, re-capped at `:213`), then scaled by source trust weight — `platform_verified`/`admin_verified` 1.0, `self_reported` 0.3 (`:34-38`, `:41-43`) |
| Overwrite vs accumulate | **Accumulate.** `v_new := clamp(v_current + p_delta_db, 0, 100)` (`145:...:93`); unseen topics seed at 50 (`:92`) |
| Idempotent on replay | **Yes**, transactionally — a prior `user_topic_mastery_audit` row for `(user, topic, attempt)` short-circuits to `already_applied` (`145:74-82`) |
| Live in production | **Gated.** `_apply_mastery` runs only under `if self.flag_state == "live"` (`app/backend/app/study_os/mastery_writer.py:100`). `get_mastery_write_flag()` defaults to `"off"` (`:414-416`). `resolve_effective_mastery_flag` downgrades `live` → `shadow` for any user absent from `FF_MOCK_MASTERY_LIVE_USER_IDS`, and downgrades to `shadow` when the allowlist is empty (`:419-444`) |

Scope key is `(user_id, topic_id)` with `exam_id IS NULL AND exam_phase_id IS NULL`
hard-coded in the RPC's `SELECT` (`145:87-90`) and omitted from its `INSERT`
(`145:98-99`). See **Defects observed / D1**.

At `flag_state != "live"` the writer still records a would-be decision in
`mock_mastery_shadow` (`app/backend/app/study_os/mastery_writer.py:161-192`) —
that is a sibling shadow table, not `user_topic_mastery`.

### Non-writers (verified, so the list above is closed)

- `app/backend/app/study_os/trap_drill_shadow.py:5-14` — writes only
  `trap_drill_mastery_shadow`; the table's `flag_state` is CHECK-pinned to
  `'shadow'`, so it is structurally incapable of becoming a live write.
  Separate flag `FF_TRAP_DRILL_MASTERY_SHADOW`, default off (`:37`).
- `app/backend/app/study_os/quant_signals.py:186-191` — shadow-writes
  `quant_performance_signals`; explicitly never `user_topic_mastery`.
- `app/backend/app/study_os/calibration.py:5-7, 218` — read-only by contract.
- `app/backend/app/api/admin_study_os.py:1389-1399` — `derive_preview`,
  zero-write.
- `tools/mastery_shadow_analysis/shadow_analysis.py` — read-only; the only
  `insert` hits are `sys.path.insert` (`:168-170`, `:774`).
- `app/supabase/seeds/exam_intelligence_demo_ssc_cgl.sql:85` — states the seed
  "never writes `user_topic_mastery`".
- **No migration backfill exists.** `grep -i 'insert into.*user_topic_mastery'`
  across `app/supabase/` returns only the RPC body in migration 145.
- **No script under `scripts/` writes it.** Only
  `scripts/v1_release_verification.sql:34` names the RPC, as an existence check.

### Dead / unreferenced

None of the writers is dead. W1 is live and unflagged; W2 is live code behind a
default-off flag. The near-dead surface is on the *read* side: see
**Defects observed / D2**.

---

## Q2 What the planner reads per user

Entry point `generate_plan` (`app/backend/app/study_os/planner.py:1703`) →
`apply_plan` (`:1620`) → `_compute_plan` (`:1151-1400`). Complete read set:

### (a) Deterministic / corpus inputs

| Source | Columns | Path |
|---|---|---|
| `exam_topic_coverage` (`reviewer_status='locked'` only) | `exam_priority_score`, `is_high_yield`, `confidence_score`, `exam_phase_id`, `section_id`, `coverage_depth`, `expected_difficulty` | `planner.py:263-276`, called at `:1223` |
| `topics` | `name, slug, subject_id, is_active, parent_topic_id, level` | `planner.py:285-297` |
| `subjects` | `name, slug, subject_group` | `planner.py:307-317` |
| verified PYQ primary-tag counts | `{topic_id: count}` over `pyq_papers`(verified) → `pyq_questions`(verified) → `pyq_question_topic_tags`(verified, `tag_role='primary'`) | `app/backend/app/exam_intelligence/coverage.py:187-203`, called at `planner.py:1226` |
| `topic_prerequisites` | `topic_id, prerequisite_topic_id, relation_type` | `planner.py:356-390`, called at `:1227` |
| `exam_topic_score_snapshots` (locked) | `exam_priority_score`, `confidence_score` | `locked_score_snapshots`, called at `planner.py:1275` |
| exam target window | `days_remaining`, `target_phase_id`, `cycle_id` | `resolve_exam_target_window`, `planner.py:1183` |
| `exam_cycles.planner_activation_enabled` | gating for `management_mode='light'` exams | `planner.py:1191-1194` |
| competition + policy context | cycle pressure level, `affects_syllabus` | `planner.py:1230-1233` |

### (b) Per-user inputs — exact source of each term

| Scoring term | Source table/column | Path | Writer count |
|---|---|---|---|
| `mastery_gap = 100 - mastery` (or **55.0** when no row) | `user_topic_mastery.mastery_score`; exam-scoped row beats global | `planner.py:409-419` (read), `:433` (map), `:610` (term) | **2** (W1, W2 — Q1) |
| `error_signal = 10.0` flat | membership in `user_topic_error_patterns` — `topic_id` only, nothing else read | `planner.py:439-449`, `:619` | **2** (`mastery.py:238-251`; `mastery_writer.py:220-240`, live-only) |
| `weights{coverage_w, mastery_w, high_yield_bonus}` | `user_study_plan_preferences.focus` | `plan_preferences.py:35-40, 51-53`, applied `planner.py:1200` | user-set |
| `pin_bonus = 30.0` | `user_study_plan_preferences.pinned_topic_ids` | `planner.py:582`, `:1199`, `:620` | user-set |
| topic exclusion | `user_study_plan_preferences.muted_topic_ids` | `planner.py:1198`, `:1209` | user-set |
| `max_tasks` (1-8), `minutes` | `user_study_plan_preferences.max_tasks_per_day` / `preferred_task_size`, else `aspirant_persona_snapshots.study_policy` | `planner.py:1236-1268` | persona classifier |
| cold-start `prior_mastery` blend | `user_topic_self_assessment.{band, prior_mastery, report_confidence, attempts_used}`, **subject-level rows only** | `planner.py:468-536`, consumed `:1310-1325` | onboarding calibration |
| prior gate | `calibration.gate_status(...) == 'completed'` **and** `mastery_ok` | `planner.py:1296-1302` | — |

Full scoring function (`planner.py:609-629`), correcting the PRIMING sketch:

```
score = coverage_w * exam_priority_score       # 0.50 at focus=balanced
      + mastery_w  * mastery_gap               # 0.25 at focus=balanced  ← per-user
      + min(20, pyq_count * 5)
      + min(15, snapshot_priority/100 * 15 * snapshot_confidence)
      + high_yield_bonus                       # 10.0 at focus=balanced
      + (10.0 if topic in error_patterns else 0)   ← per-user
      + (30.0 if topic pinned else 0)              ← per-user
```

**The finding this investigation exists to produce:** of the two per-user
*performance* terms, `mastery_gap` reads a table with exactly two writers (Q1),
and `error_signal` reads a table with the same two writers. Both writers are the
mock path. Every other per-user input is a **declared preference or a
self-report** — `user_study_plan_preferences`, `user_topic_self_assessment`,
`aspirant_persona_snapshots` — not observed performance. There is no third
performance writer for any surface.

**Prior task outcomes are not read at all.** `_compute_plan` never touches
`study_tasks`. Completion, skip, and carry-forward history influence nothing in
scoring. `build_regen_triggers` (`planner.py:1922-1947`) does read
`study_tasks.status` via `_missed_days_streak` (`:1746-1762`) and
`_backlog_trigger` (`:1803-1818`), and `mock_tests` scores via
`_mock_drift_trigger` (`:1873-1899`) — but its own docstring states "the planner
does **NOT** apply changes from this surface" (`:1930-1933`). It is a display
strip only.

---

## Q3 Does the Mock Engine feed the planner?

**Yes — but only at `FF_MOCK_MASTERY_WRITES=live` with the user explicitly
allowlisted. Off by default, and the default resolves fail-closed to shadow.**

End-to-end trace of a submitted platform mock:

1. **Attempt + frozen questions persisted.** `mock_attempts` insert at
   `app/backend/app/study_os/mock_engine.py:691`; per-question rows into
   `mock_attempt_responses` at `:724`. `selected_option_id` on those rows is
   "the only authority for scoring" (`:916`).
2. **Submit.** `submit_attempt` (`mock_engine.py:1170`) scores and finalises,
   then enqueues `JOB_ANALYTICS_RETRY` (`:1242`).
3. **Classification gate.** `MasteryWriter.process_attempt_sync` refuses to
   proceed until `mock_attempt_response_classification` is complete, re-enqueuing
   analytics and raising `MasteryClassificationNotReady`
   (`mastery_writer.py:74-85`).
4. **Mastery job.** The API submit route resolves a per-user pinned flag and
   runs the writer inline (`app/backend/app/api/mock_engine.py:230-246`);
   failures fall back to a `mastery_retry` row
   (`mock_engine.py:1857-1894`).
5. **`mock:sweeper`.** Runs on a **30-second `IntervalTrigger`**, not a cron
   (`app/backend/app/notifications/scheduler.py:344-352`). Phase A auto-submits
   attempts expired >60s; Phase B claims due `mock_attempt_jobs` and dispatches
   by kind (`mock_engine.py:2029-2100`). For `mastery_retry` it constructs
   `MasteryWriter(supabase, flag_state).process_attempt_sync(attempt_id)`
   (`:1979-1984`).
6. **The write.** At `live` only:
   `_apply_mastery` → `apply_mock_mastery_delta` → `user_topic_mastery`
   (`mastery_writer.py:100-101`, `:203-217`), plus
   `user_topic_error_patterns` inserts (`:220-240`) — both Q2(b) tables.

So the emitter already exists and is wired; what is missing is the flag being
on. At `shadow` the decision lands in `mock_mastery_shadow` and the planner
never sees it (`mastery_writer.py:161-192`).

**Nearest point already holding `topic_id` / `microtopic_id`:** the derived
evidence adapter. `load_mock_attempt_evidence`
(`app/backend/app/study_os/attempt_evidence.py:86-135`) already groups responses
by `(topic_id, microtopic_id)` (`:62`, `:121-128`), and every schema in
`app/backend/app/study_os/mastery_engine/schemas.py:11-12, 31-32, 58-59, 78-79`
carries both fields. A future cross-tool emitter attaches there — it is the one
place where a scored attempt is already normalised to topic scope and is
already shared between the mock path and the trap-drill path (`:20`).

---

## Q4 Do the other surfaces feed it?

**PYQ practice — yes, by inheritance, under the same gate.**
`app/backend/app/study_os/pyq_practice.py` has no submit function of its own; it
only starts attempts, via the `start_attempt_from_blueprint` RPC (`:706`), and
the resulting row is described as "a normal" mock attempt
(`app/backend/app/api/pyq_practice_launch.py:9`). Launch routes hand the client
`/app/study/mocks/attempts/{attempt_id}`
(`app/backend/app/api/subject_practice.py:118`, `:129`), i.e. the shared mock
engine submit path. A PYQ practice attempt therefore reaches
`user_topic_mastery` on exactly the same `live`+allowlist condition as a mock,
and reaches nothing otherwise.

**Essay Builder / brainstorm blocks — no.** `app/backend/app/api/essay_builder.py`
touches only `essay_themes` (`:411`), `essay_pyq_tags` (`:454`), `pyq_questions`
(`:471`), and `pyq_papers` (`:485`). All reads. No mastery, no evidence, no
planner table.

**Writing practice — no, and the PRIMING assumption is wrong.** This is *not* a
working `user_topic_mastery` path. The evaluator writes
`user_topic_mastery_evidence` (`app/supabase/migrations/209_english_writing_practice_evaluator.sql:1155`,
`:1364`, `:1949`) and `writing_mastery_shadow`
(`app/backend/app/study_os/writing_practice/evidence_deriver.py:93`), drained by
the `writing:mastery_outbox` job through four RPCs
(`app/backend/app/study_os/writing_practice/mastery_outbox_worker.py:35, 70, 81,
100`). Neither `user_topic_mastery` nor `user_topic_error_patterns` is touched;
`grep 'user_topic_mastery'` over migrations 205/209/234 returns only
`_evidence` matches. Writing practice's *actual* influence on the plan runs the
other way: the planner generates `english_writing_session` tasks
(`app/backend/app/study_os/planner.py:872-911`, appended at `:1370-1379`) from
locked coverage plus prompt eligibility
(`app/backend/app/study_os/writing_practice/planner_tasks.py:10-24`). Task
emission, not signal ingestion. As a *reference implementation* what it
demonstrates is the transactional outbox pattern — evidence keyed by
`evidence_key`, append-only with supersession
(`migrations/205:541-546`, `:835-845`) — which is a good model for a future
emitter, but it is a model, not a live loop.

**Eligibility (`elig:recompute`) — no.** Runs every 5 minutes
(`app/backend/app/notifications/scheduler.py:6`, `:318-322`) draining
`drain_recompute_queue` (`app/backend/app/notifications/recompute_worker.py:122`).
It recomputes eligibility verdicts; `recompute_worker.py` does not appear in the
list of files referencing `user_topic_mastery` or `mastery_score` at all.

**Calc gym — present, shadow-only, and not a mastery writer.**
`app/backend/app/study_os/calc_gym.py` contains zero matches for `mastery` or
`user_topic`. Its sibling signal module writes `quant_performance_signals`
(`app/backend/app/study_os/quant_signals.py:186-191`), a table whose migration
comment says it is "NOT a mastery tier" and "NEVER a `user_topic_mastery`
writer" (`app/supabase/migrations/245_quant_calc_gym_and_signals.sql:93-95`,
`:120-121`). Nothing reads it back into planning.

**Trap drills (direct PYQ) — no.** Shadow table only, CHECK-pinned to
`'shadow'`, behind its own default-off flag
(`app/backend/app/study_os/trap_drill_shadow.py:5-19`, `:37`).

**Vocab — not present in repo.** No module, table, or migration matching a
vocabulary surface was found.

---

## Q5 What triggers a regen, and what makes a plan stale

`regenerate_stale_plans` (`app/backend/app/study_os/regen.py:137-201`).

**Staleness predicate — time-based, string-compared:**

```python
if str(plan.get("updated_at") or "")[:10] >= today:   # regen.py:169
    skipped_fresh += 1; continue
```

`study_plans.updated_at`, truncated to its first 10 characters, lexicographically
compared against `datetime.now(timezone.utc).date().isoformat()` (`:37-38`).
A plan is stale iff its `updated_at` **date** is earlier than today UTC. There
is no dirty flag, no watermark, no mastery-version column, nothing content-aware.

**`updated_at` is bumped by the planner's own persist**
(`app/backend/app/study_os/planner.py:1100`), so "stale" means literally "has
not been regenerated since midnight UTC".

**Every trigger:**

| Trigger | Path | Notes |
|---|---|---|
| `study:plan_regen` cron | `app/backend/app/notifications/scheduler.py:327-331` | `CronTrigger(hour=3, minute=0, timezone="UTC")` — PRIMING **confirmed**. Sweeps `status='active'` plans, `limit=200` (`regen.py:137`, `:145-158`) |
| `regenerate_on_signal` | `app/backend/app/study_os/regen.py:92-134` | **Exactly one caller in the entire repo**: `app/backend/app/api/canonical.py:2366-2372`, the manual mock-review PATCH, `event_type="mock_reviewed"` |
| `POST /api/study/plan/generate` | `app/backend/app/api/study_os.py:683` | explicit user action |
| `POST /api/study/plan/apply` | `app/backend/app/api/study_os.py:736` | explicit user action (draw-then-apply) |
| Admin plan apply | `app/backend/app/api/admin_study_os.py:594` | operator action, `event_type='admin_apply'` |

**Does a mastery change set a staleness flag?** **No.** There is no flag. The
only causal link between a mastery write and a regen is the single code block at
`app/backend/app/api/canonical.py:2362-2372`, where the breakdown insert,
`recompute_topic_mastery`, and `regenerate_on_signal` are three sequential
`_safe(...)` calls in one request handler. Nothing in `MasteryWriter` calls
`regenerate_on_signal` — grep for it returns only `canonical.py:2366`, the
definition, and two docstrings.

**Consequence for an end-to-end proof.** A platform mock submitted at 10:00 UTC
that (at `FF=live`) moves `user_topic_mastery` will **not** reach the plan until
the 03:00 UTC sweep the next day — up to ~17 hours — unless the user manually
hits `/api/study/plan/generate`. Only the manual-log review path gets
minutes-latency propagation. Both regen entry points additionally no-op when
`user_study_plan_preferences.auto_regenerate` is false (`regen.py:104-105`,
`:172-174`) and when the user has no `status='active'` plan (`:107-108`).

---

## Q6 Where a user edit collides with regen

**No per-task column can express "user pinned this, do not regenerate."**

Full `public.study_tasks` column set, assembled from every migration that
touches it:

- `app/supabase/migrations/002_core_runtime_schema.sql:73` — `id, plan_id,
  user_id, title, status, due_at`
- `app/supabase/migrations/017_study_os_runtime_schema.sql:12-22` — `day_label,
  subject, topic, microtopic, task_type, duration_mins, planned_minutes,
  scheduled_date, completed_at, updated_at`
- `app/supabase/migrations/034_study_os_exam_intelligence_links.sql:12-24` —
  `exam_id, exam_cycle_id, exam_phase_id, subject_id, topic_id,
  exam_topic_coverage_id, plan_version_id, priority_score, why_this_task,
  evidence_required, completion_quality, skipped_reason`
- `app/supabase/migrations/205_english_writing_practice_schema.sql:793-796` —
  `launch_type, launch_entity_id, launch_context`

No `pinned`, `locked`, `user_modified`, `manual`, or `source`. (`pinned` appears
in migration 222 only as prose describing a *session* column, `:15`, `:41`,
`:173` — unrelated to `study_tasks`.)

**The only collision protection today is `status`.** `_persist` deletes and
rebuilds the day (`app/backend/app/study_os/planner.py:1055-1092`):

```python
supabase.table("study_tasks").delete()
    .eq("plan_id", plan_id)
    .eq("scheduled_date", today)
    .eq("status", "planned")      # planner.py:1066
```

A task survives regeneration **iff** its status has moved off `planned`. So a
user who reorders, re-times, or otherwise edits a task while leaving it
`planned` has that edit silently destroyed by the next regen — including the
03:00 UTC sweep.

Pinning exists, but only at **topic** granularity and only as a scoring boost:
`user_study_plan_preferences.pinned_topic_ids` → `+30.0`
(`app/backend/app/study_os/planner.py:582`, `:1199`, `:620`). It raises the
odds a topic is re-selected; it cannot preserve a specific task row, its
scheduled slot, or its planned minutes.

**Where a future flag would land** (not added here): a column on
`public.study_tasks`, in a new sequentially-numbered migration under
`app/supabase/migrations/`, with the matching predicate added to the delete at
`app/backend/app/study_os/planner.py:1059-1069`. `plan_timeline.py` is a
read-only projection — `get_plan_timeline`
(`app/backend/app/study_os/plan_timeline.py:590`) and its loaders
(`:246-318`) only `select` — so it needs no schema of its own; it would simply
surface the flag.

---

## Corrections to stated assumptions

1. **`regen.py::regenerate_stale_plans` at 03:00 UTC — correct.**
   `app/backend/app/notifications/scheduler.py:327-331`. No correction.

2. **Other known jobs — correct but incomplete on cadence.** `elig:recompute`
   is every 5 min (`scheduler.py:318-322`), `mock:sweeper` is a **30-second
   interval**, not a cron (`:344-352`), `writing:evaluate` and
   `writing:mastery_outbox` at `:370-384`. The scheduler also registers jobs
   the brief did not name, at `:303`, `:312-316` (00:30 UTC), `:336-340`
   (04:00 UTC), `:358`, `:392`, `:401`, `:410-414` (02:30 UTC).

3. **`_HIGH_YIELD_MASTERED_THRESHOLD = 75.0` in `report_cards.py` — correct.**
   `app/backend/app/study_os/report_cards.py:271`. But it is **not a planner
   input.** It is confined to report-card rollups (`:297`, `:306`, `:318`,
   `:325`, `:331`). The planner's own mastery cut-points are different and
   local: `_task_type` switches at **45** and **75**
   (`app/backend/app/study_os/planner.py:632-639`), and the cold-start blend
   uses a neutral of **45.0** (`:1318`). Three separate numbers, no shared
   constant.

4. **The scoring shape `0.50*coverage_priority + pyq_factor + high_yield_bonus`
   — incomplete, and `0.50` is not a constant.** The real function
   (`planner.py:609-629`) has **seven** terms, and `coverage_w` is
   preference-driven: 0.50 balanced / 0.30 weak_areas / 0.65 exam_priority /
   0.45 high_yield (`plan_preferences.py:35-40`). `high_yield_bonus` likewise
   varies 5.0–25.0 across those profiles. Missing from the sketch: the
   confidence-weighted snapshot component (≤15, `:611-616`), the flat error
   signal (10.0, `:619`), and the pin bonus (30.0, `:582`). Note the pin bonus
   is the single largest term available and exceeds the entire PYQ range.

5. **"Per-user mastery/error terms" — correct, and that is the whole of it.**
   `mastery_w * mastery_gap` and a flat `+10`. There is no per-user decay,
   recency, streak, velocity, or attempt-count term anywhere in the score.

6. **"Adaptive planner lives under `app/study_os/`" — correct**, though the
   real path is `app/backend/app/study_os/`. All four named modules exist:
   `planner.py` (1947 lines), `plan_preferences.py` (180), `plan_timeline.py`
   (793), `regen.py` (201).

7. **`user_topic_mastery` holds a continuous 0–100 `mastery_score` — correct.**
   `app/supabase/migrations/033_exam_topic_analytics_snapshots.sql:43`:
   `numeric(5,2) not null default 0 check (mastery_score >= 0 and <= 100)`.
   Worth noting the **default is 0**, while the delta RPC seeds absent topics at
   **50** (`145:92`) and the planner treats a missing row as a 55-point gap
   (`planner.py:610`) — three different notions of "unknown".

8. **Writing practice as "the one known-working path" — wrong.** See Q4. It
   never writes `user_topic_mastery`, and the evidence view its own migration
   calls "the ONLY planner/level source" has no Python reader. If an end-to-end
   proof was planned against the writing path as the control, that plan needs
   revisiting.

---

## Defects observed

Recorded per the brief. No fixes applied, no follow-up taken.

**D1 — W1 and W2 write different rows for the same `(user, topic)`, and W1 can
clobber W2.** `apply_mock_mastery_delta` hard-scopes to
`exam_id IS NULL AND exam_phase_id IS NULL`
(`app/supabase/migrations/145_mock_attempt_jobs.sql:87-90`) and inserts without
either column (`:98-99`). `recompute_topic_mastery` scopes to
`(user_id, topic_id, exam_id, exam_phase_id)` carried from the mock's own
metadata (`app/backend/app/study_os/mastery.py:210-215`), matching `None` as
`IS NULL` (`:78-84`). The schema permits both rows to coexist: migration 033
defines two *partial* unique indexes, one for the exam-scoped shape (`:59-61`)
and one for the global shape (`:63-65`), so nothing at the DB level collapses
them. Two consequences:

- When a manual-log mock carries a non-null `exam_id`, the two writers produce
  **two rows** for one topic. The planner prefers the exam-scoped one
  (`app/backend/app/study_os/planner.py:426-435`), so at `FF=live` the mock
  engine's accumulated deltas are invisible whenever a self-reported
  exam-scoped row exists for that topic.
- When a manual-log mock's `exam_id` is null, both writers target the **same**
  row — and W1 overwrites `mastery_score` with raw accuracy
  (`mastery.py:220`), discarding every capped, trust-weighted delta W2
  accumulated. `user_topic_mastery_audit` still shows the deltas as applied, so
  the audit trail and the live value silently disagree.

**D2 — the writing path's declared planner source has no reader.**
`app/supabase/migrations/205_english_writing_practice_schema.sql:825` annotates
`effective_user_topic_mastery_evidence` as "the ONLY planner/level source
(§4.12d)", and `:852` grants it to `service_role`. Grepping the whole backend
for both the view name and `user_topic_mastery_evidence` returns hits only in
`app/backend/app/study_os/writing_practice/evidence_deriver.py` (lines 8, 35,
93, 128, 148) — all docstrings and column-dict builders on the *write* side.
Zero read call sites. The writing evaluator, its outbox, its evidence
supersession chain, and its RLS posture are all built and running; the
consumer was never written.

**D3 — `build_regen_triggers` computes four signals and discards them.**
`app/backend/app/study_os/planner.py:1922-1947` assembles
`missed_days_streak`, `backlog_threshold`, `deadline_compression`, and
`mock_score_drift` from real user data — and its docstring states the planner
does not act on any of it (`:1930-1933`). `_mock_drift_trigger` (`:1873-1899`)
in particular reads `mock_tests` score history that reaches the planner through
no other route. Not a bug in the strict sense — the behaviour is documented and
deliberate — but it is four working detectors wired to a display strip while
the scoring function has no performance-trend term at all.

**D4 — a still-`planned` user edit is destroyed by the nightly sweep.**
`app/backend/app/study_os/planner.py:1059-1069`. Covered in Q6; recorded here
because it is reachable with no user action at all — the 03:00 UTC cron alone
triggers it.

---

## Requires live data

Nothing below was guessed; each is a question code cannot answer. SQL that
answers them is in `workbench/sql/PLAN-LOOP-01_probe.sql`.

1. **Is `FF_MOCK_MASTERY_WRITES` actually `live` in production, and is the
   allowlist non-empty?** Not answerable from code — it is Render environment
   configuration. This single fact decides whether Q3's answer is "yes" or "no
   in practice". Ask an operator; the DB proxy for it is whether any
   `user_topic_mastery_audit` rows exist (probe §1).

2. **How many `user_topic_mastery` rows exist, and what wrote them?** W1 leaves
   `accuracy_score`, `confidence_score`, and `evidence_count` populated; W2
   leaves them at defaults and writes an audit row. The split tells us whether
   any real mastery signal exists at all today. Probe §2.

3. **Does D1's dual-row condition occur in practice?** Count topics with both a
   null-scoped and an exam-scoped row for the same user. Probe §3.

4. **Has D1's clobber actually fired?** Look for topics whose audit trail shows
   an applied delta but whose current `mastery_score` equals a clean
   accuracy-shaped value inconsistent with the audit's `after_mastery_db`.
   Probe §4.

5. **Is any mastery evidence stranded in shadow?** `mock_mastery_shadow` row
   count by `flag_state`, and `trap_drill_mastery_shadow` count. These are
   attempts whose signal was derived and then discarded. Probe §5.

6. **Is the writing evidence table accumulating rows nobody reads?** Row count
   and distinct-user count on `user_topic_mastery_evidence` versus
   `effective_user_topic_mastery_evidence` (D2). Probe §6.

7. **What is the real end-to-end latency from mock submit to plan refresh?**
   Compare `mock_attempts.submitted_at` against the next
   `study_plan_versions.created_at` for the same user. Q5 predicts a bimodal
   distribution: minutes for the `mock_reviewed` path, up to ~17h otherwise.
   Probe §7.

8. **How often does the nightly sweep destroy a user edit (D4)?** Not directly
   observable — the deleted rows are gone. The closest proxy is the count of
   tasks still `planned` at the moment of regen, which the sweep's own
   `checked`/`regenerated` counters (`regen.py:196-201`) do not record. Would
   need instrumentation, not a query. Probe §8 gives the standing backlog of
   `planned` past-dated tasks as a lower-bound indicator.

9. **Is `user_signal_events` (P3) genuinely single-purpose in production, or
   are other `event_type` values already being written?** A distinct-`event_type`
   count decides whether it is reusable as the cross-tool ledger or is
   effectively a persona-private table. Probe §9.
