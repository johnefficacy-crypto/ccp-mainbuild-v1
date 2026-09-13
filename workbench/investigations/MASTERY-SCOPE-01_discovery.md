# MASTERY-SCOPE-01 — the two-row `user_topic_mastery` design

Read-only investigation. No code, migration, or data changed.
Line numbers are against `main @ bcc9cb9` (branch `investigate/mastery-row-scope`).

`public.user_topic_mastery` can hold **two rows for the same (user, topic)**: a
*global* row (`exam_id IS NULL AND exam_phase_id IS NULL`) and an *exam-scoped*
row (both non-null). Two writers, six readers, and only two of the six know the
distinction exists.

---

## 1. Writers and readers

### Writers — exactly two

| Writer | Site | Writes which row | Columns written |
|---|---|---|---|
| **W1** `recompute_topic_mastery` | `study_os/mastery.py:213-232` via `_upsert:90-111` | **Whatever `mock_tests` carries** — group key is `(topic_id, meta.exam_id, meta.exam_phase_id)` (`mastery.py:176`), read from `mock_tests` at `:126`. Global when both are NULL, scoped when both are set, and the **half-scoped** case when only one is (see §2) | `mastery_score`, `accuracy_score`, `confidence_score`, `last_practiced_at`, `next_revision_at`, `evidence_count`, `updated_at` |
| **W2** `apply_mock_mastery_delta` | RPC body `145_mock_attempt_jobs.sql:86-103`, called `mastery_writer.py:315-325` | **Global only** — hardcoded `where … exam_id is null and exam_phase_id is null` (`145:88-89`), and the INSERT at `145:98-99` names only `(id, user_id, topic_id, mastery_score)`, so both scope columns default NULL | `mastery_score` (+ a `user_topic_mastery_audit` row) |

No other writer exists. Three modules state in comments that they deliberately
never write it: `calibration.py:5`, `quant_signals.py:4,190`,
`subject_runtime_policy.py:325`. The writing-practice path is flagged off and
routes through an aggregator, never this table
(`docs/status/career-copilot-checklist.md:395`). No migration writes rows either
— only 145's function body.

**Correction to the brief:** the RPC call is `mastery_writer.py:315`, not `:210`
(it moved when MASTERY-GATE-01 landed).

### Readers — six, and only two are scope-aware

| Reader | Site | Scope handling |
|---|---|---|
| Planner `_load_user_signals_ex` | `planner.py:658-683` | **Scope-aware.** Prefers the row whose `exam_id` equals the target exam; falls back to any other row for that topic (`:678-683`) |
| `shared_core._read_global_mastery` | `shared_core.py:200-213` | **Scope-aware.** Filters `r.get("exam_id") is None` in Python (`:213`) — global row only, by design ("mastered GLOBALLY", `:201-202`) |
| W2's own baseline `_load_current_mastery` | `mastery_writer.py:256` | **Scope-blind.** `select topic_id,mastery_score`, no `exam_id`; builds `{topic_id: score}` — with two rows present, **last row wins**, and row order is unspecified |
| `attempt_derivation.derive_current_state_preview` | `attempt_derivation.py:400-413` | **Scope-blind**, same last-wins dict |
| `trap_drill_shadow._current_mastery` | `trap_drill_shadow.py:87-105` | **Scope-blind**, same last-wins dict |
| `calibration.resolve_required_subjects` | `calibration.py:222-236` | Existence only (`select topic_id`) — scope cannot affect it |

Downstream of the planner, `GET /api/study/topics` surfaces `mastery_score` and
`revision_due` from that same map (`api/study_os.py:1262,1266`), and
`report_cards` counts topics ≥ 75 through `_load_user_signals`
(`report_cards.py:281-289`). Both therefore inherit the planner's preference.

**The defect this produces today:** three readers key a dict by `topic_id`
alone. If a topic has both rows, the value they see is whichever row PostgREST
returns last — no `ORDER BY` is issued at any of the three sites. W2's own
baseline (`mastery_writer.py:256`) is one of them, so **W2 can compute its delta
against W1's scoped number and then write the result to the global row.**

---

## 2. Where the two-row design comes from

Migration `033_exam_topic_analytics_snapshots.sql` creates the table (`:36-57`)
with both scope columns nullable, and then **two partial unique indexes**:

```sql
-- 033:59-61
create unique index user_topic_mastery_user_exam_phase_topic_uidx
  on public.user_topic_mastery(user_id, exam_id, exam_phase_id, topic_id)
  where exam_id is not null and exam_phase_id is not null;

-- 033:63-65
create unique index user_topic_mastery_user_topic_no_exam_uidx
  on public.user_topic_mastery(user_id, topic_id)
  where exam_id is null and exam_phase_id is null;
```

The file's own header calls the table a "user-specific overlay" of the
analytical snapshots above it (`033:1-3`), and every sibling table in that
migration — `exam_topic_score_snapshots` (`:5-33`), `user_topic_error_patterns`
(`:102+`) — carries the same optional `(exam_id, exam_phase_id)` pair. So the
intent is plainly **one overlay per (exam, phase) with a global fallback**, not
two competing values for one topic.

What the migration does **not** do is say which of the two a reader should
prefer, or forbid both existing at once. Nothing in the schema, and nothing in
`docs/`, resolves that. The only place the question is answered is a docstring
added to the planner later (§3).

**A third state exists and is unconstrained.** A row with exactly one of the two
columns set — `exam_id` present, `exam_phase_id` NULL — satisfies **neither**
index's `WHERE`, so it is subject to **no uniqueness at all**. W1 reaches that
state whenever a `mock_tests` row has an exam but no phase (`mastery.py:176`
copies both straight through), and `_upsert` then matches on
`(user_id, topic_id, exam_id, exam_phase_id)` with `exam_phase_id IS NULL`
(`_existing_row:75-88` renders NULL as `.is_(key, None)`), so it will find and
update its own previous row — but nothing stops a second row appearing from a
concurrent write.

---

## 3. Is `planner.py:678-683` deliberate?

**Deliberate in code, unpinned by tests, and undocumented outside that function.**

- It is stated as contract in the function's own docstring, four lines above the
  implementation: *"When a topic has both an exam-scoped and a global mastery row
  the exam-scoped one wins"* (`planner.py:645-647`). That is a choice someone
  wrote down, not an accident of iteration.
- The implementation matches the docstring exactly: `is_exam = r.get("exam_id") == exam_id`,
  and an already-exam-scoped topic is never overwritten by a later non-exam row
  (`:678-680`).
- **No test pins it.** Searching every test fixture that seeds
  `user_topic_mastery` for two rows sharing one `topic_id` returns **zero**
  matches. The seeds that exist use a single row, usually exam-scoped
  (`test_planner_priors.py:166-168`, `:376-378`; `test_plan_preferences.py:46-49`;
  `test_topics_endpoint.py:52-54`). The precedence branch is executed by no test
  in the suite.
- Note what the condition actually compares: `r["exam_id"] == exam_id`, i.e. the
  **currently targeted** exam. A row scoped to a *different* exam is treated
  exactly like the global row — it can win, if it arrives first and no row for
  the target exam exists. That is almost certainly not intended, and it is not
  what the docstring says.
- The only other place the split is acknowledged is the canary runbook, which
  calls the global row "**mock scope**" and scopes both its baseline and its
  rollback to `exam_id IS NULL AND exam_phase_id IS NULL`
  (`docs/ops/pr8_live_canary_plan.md:258-271`, `:669-684`). Ops already treats
  the global row as W2's private property.

So: the *preference* is deliberate. The *coexistence of two rows* is not
documented as a decision anywhere — it is the schema's degree of freedom that
two writers independently used.

---

## 4. If the scoped row is retired — everything keys global

**What has to change:** W1 stops copying `mock_tests.exam_id/exam_phase_id` into
its group key (`mastery.py:176`) and writes the global row. The
`user_topic_mastery_user_exam_phase_topic_uidx` index (`033:59-61`) becomes dead;
`user_topic_mastery_user_topic_no_exam_uidx` (`033:63-65`) covers every row, so
uniqueness is total for the first time — the half-scoped gap in §2 closes.

**The five W1-only columns: no reader anywhere.**

| Column | Written | Read |
|---|---|---|
| `accuracy_score` | `mastery.py:220` | **nobody** |
| `confidence_score` | `mastery.py:221` | **nobody** |
| `last_practiced_at` | `mastery.py:222` | **nobody** |
| `next_revision_at` | `mastery.py:223` | **nobody** |
| `evidence_count` | `mastery.py:225` | **nobody** |

Every one of the six readers in §1 selects only `topic_id`, `mastery_score` and
(twice) `exam_id`. No frontend file references them either. They are write-only
columns today, so retiring the scoped row loses **no** reader — but note this is
a statement about *readers*, not about value: if the RPC becomes the only writer
it writes `mastery_score` alone, and those five stop being maintained at all.

**`idx_user_topic_mastery_revision` (`033:129-130`), on `(user_id, next_revision_at)`,
supports no query in this codebase.** `next_revision_at` appears exactly once
outside the migration — at `mastery.py:223`, where it is written. The spaced-
revision schedule W1 computes via `_next_revision` (`mastery.py:65-73`) and
`_REVISION_DAYS` (`:35`) is **not consumed by anything**; the `revision_due` flag
the topics API exposes is computed from `mastery_score >= 75`
(`api/study_os.py:1266`), not from this column. Retiring the scoped row does not
break revision scheduling because there is no revision scheduling.

**What genuinely changes behaviour:**

1. `shared_core._read_global_mastery` (`:200-213`) currently sees **only W2's**
   numbers. Fold W1 in and self-reported offline mocks start counting toward
   "mastered globally" for whatever gates that function feeds.
2. The planner's preference (`:678-683`) becomes dead code — one row per topic,
   `is_exam` never true. Its docstring at `:645-647` would be false.
3. Per-exam mastery is no longer expressible. A user preparing for two exams gets
   one number per topic. Nothing reads per-exam mastery today except the planner
   preference being removed, so nothing breaks — but the capability goes.
4. The three scope-blind readers (§1) become correct by construction, since the
   ambiguity they mishandle no longer exists.

**Cost:** loses a capability nothing currently uses. **Benefit:** one row, one
meaning, total uniqueness, and the last-wins defect disappears.

---

## 5. If the global row is retired instead — everything keys scoped

**This one does not currently work, for a concrete reason.**

The RPC would need `p_exam_id` / `p_exam_phase_id` parameters and W2 would have
to supply them per attempt. **W2 cannot.** Its evidence object
`DerivedAttemptAnalytics` carries `attempt_id`, `user_id`, `questions`, `topics`
and nothing else (`mastery_engine/schemas.py:38-42`). Walking back to the source:
`mock_attempts.template_id` → `mock_templates`, which has a **nullable**
`exam_id` (`135_mock_engine_core.sql:46`) and **no `exam_phase_id` column at all**
(`:41-55`).

So under this option every W2 write lands with `exam_phase_id IS NULL`, which is
precisely the half-scoped state that **neither partial unique index covers**
(§2). `_upsert`-style read-then-write cannot protect it, and the RPC has no
`ON CONFLICT` to fall back on: duplicate rows accumulate per (user, topic),
and the three scope-blind readers get an arbitrary one. That is strictly worse
than today.

Making it work first requires either an `exam_phase_id` on the mock-engine side
(a new column and a source of truth for what phase a generated mock represents),
or a third unique index covering the half-scoped case and a decision about what
a phase-less exam row *means* relative to a phased one.

**Other consequences, assuming that were solved:**

1. `shared_core._read_global_mastery` (`:200-213`) returns the empty set forever —
   its filter is `exam_id is None`. Every gate built on "mastered globally"
   silently opens or closes, depending on its polarity.
2. W2's own baseline (`mastery_writer.py:256`) must become scope-aware or it will
   read one exam's number and write another's.
3. A topic studied for two exams needs two independent mastery histories, and the
   audit table's `unique (user_id, topic_id, attempt_id)` (`144:26`) has no scope
   column — one attempt could legitimately need to write two rows, and cannot.
4. Every attempt not resolvable to an exam (nullable `mock_templates.exam_id`)
   has nowhere to write at all.

**Cost:** a new column on the mock-engine side, a third index, an audit-table
change, and a rewrite of the global-mastery gate. **Benefit:** per-exam mastery
becomes real, which is a genuine product capability — a user's Quant mastery for
SSC and for UPSC are not the same number.

### 4 vs 5, stated plainly

Option 4 is a deletion: it removes a capability nothing reads, closes the
uniqueness gap, and makes three buggy readers correct. Option 5 is a build: it
needs exam/phase identity to exist on the mock-engine side before it can be
written at all, and it turns `mock_templates.exam_id`'s nullability into a
correctness problem. If per-exam mastery is not on the roadmap, 4 is the cheap
and safe answer; if it is, 5 is the only one that gets there, and the missing
`exam_phase_id` is the first thing to resolve.

---

## 6. Re-review supersession (gap 4)

**The key that would work.** The RPC dedups on
`(user_id, topic_id, attempt_id)` (`145:77-84`, backed by the unique constraint
at `144:26`), so any key that is stable per *review revision* rather than per
*mock* lets a corrected review land while a replay stays a no-op. The review
route already deletes and re-inserts that mock's breakdowns on every PATCH
(`api/canonical.py:2352-2359`), so a revision counter has a natural increment
point: `(mock_test_id, review_revision)` hashed to a UUID, or a `review_id`
column on a W1-owned table that increments there. Replay of the same revision →
same key → `already_applied`. A corrected review → new revision → new key → the
delta applies, and both rows remain in the audit trail, which is what makes the
correction auditable rather than silent.

Note this is not merely a key change: superseding also means the *previous*
revision's delta should be backed out, or the two deltas compound. Nothing in
the current RPC can reverse a prior audit row.

**Does anything already do versioned supersession here? Yes — three precedents,
one of them very close.**

1. **`recruitment_verification_reports`** (`075_recruitment_verification_reports.sql:42-103`)
   is the closest match and the most developed: `chain_root_id` + `report_version`
   + `superseded_by`, with partial unique indexes enforcing exactly one *active*
   row per owner (`075:180-191`, `where superseded_by is null`). The
   `superseded_by` FK is `deferrable initially deferred` (`075:55-61`) so the
   supersede-and-insert happens in one transaction, and two RPCs own that
   atomically — the Python service validates chain crossing, self-supersession
   and version monotonicity, then calls them
   (`scraping/verification_reports.py:19-26`). `superseded` is a terminal,
   immutable lifecycle state (`verification_reports.py:96`).
2. **`study_plan_versions`** (`033:88-100`): `version_number` with
   `unique(plan_id, version_number)`, and the active one pointed at by
   `study_plans.current_plan_version_id` (`planner.py:1354-1370`). Simpler —
   a pointer to the current version rather than a chain.
3. **`exam_competition_metrics`** clone-published-into-new-draft revisioning,
   described at `graphify-out/GRAPH_REPORT.md:6186` and implemented in the CMS
   router.

Pattern 1 is the one to copy if supersession is wanted: it already solves
"exactly one active row, full history retained, atomic swap" in this codebase,
with a working answer to the FK ordering problem that a supersede chain creates.

---

## Defects observed

- **D11 — three scope-blind mastery readers.** `mastery_writer.py:256`,
  `attempt_derivation.py:401`, `trap_drill_shadow.py:88` each build
  `{topic_id: mastery_score}` from an unordered read with no `exam_id` filter.
  With both rows present the winner is arbitrary. W2's own delta baseline is one
  of them, so a delta can be computed from W1's scoped number and written to the
  global row.
- **D12 — the half-scoped row has no uniqueness.** A row with `exam_id` set and
  `exam_phase_id` NULL matches neither partial unique index (`033:59-65`). W1
  produces exactly that whenever `mock_tests.exam_phase_id` is NULL
  (`mastery.py:176`).
- **D13 — the planner's precedence accepts the wrong exam.** `is_exam` compares
  against the *target* exam only (`planner.py:678`); a row scoped to a different
  exam is treated as a global fallback and can win. The docstring at `:645-647`
  does not describe this.
- **D14 — five write-only columns and a dead index.** `accuracy_score`,
  `confidence_score`, `last_practiced_at`, `next_revision_at`, `evidence_count`
  have no reader in backend or frontend, and `idx_user_topic_mastery_revision`
  (`033:129-130`) supports no query. The spaced-revision schedule W1 computes is
  not consumed by anything.
- **D15 — no test covers the two-row case.** No fixture in the suite seeds two
  `user_topic_mastery` rows for one topic, so neither the planner's precedence
  nor the three scope-blind readers are exercised in the ambiguous state.

---

## Requires live data

Code cannot answer how often the ambiguity is actually realised. Three counts
settle it, and they also decide how urgent D11 is:

1. **How many (user, topic) pairs have both rows today?**
   ```sql
   select count(*) from (
     select user_id, topic_id
     from public.user_topic_mastery
     group by user_id, topic_id
     having count(*) filter (where exam_id is null and exam_phase_id is null) > 0
        and count(*) filter (where exam_id is not null) > 0
   ) x;
   ```
2. **How many half-scoped rows exist (D12's uncovered state), and are any
   duplicated?**
   ```sql
   select user_id, topic_id, exam_id, count(*) as rows
   from public.user_topic_mastery
   where exam_id is not null and exam_phase_id is null
   group by 1,2,3
   order by rows desc;
   ```
3. **Do W1's rows carry exam scoping at all in production** — i.e. is the
   collision in MASTERY-W1-01 the common case or the rare one?
   ```sql
   select
     (exam_id is null and exam_phase_id is null) as global_row,
     (exam_id is not null and exam_phase_id is not null) as fully_scoped,
     count(*)
   from public.user_topic_mastery
   group by 1,2;
   ```

---

## Live probe results — 2026-09-13

Operator ran all three queries above.

| Probe | Result |
|---|---|
| 1. (user, topic) pairs holding both a global and a scoped row | **0** |
| 2. Half-scoped rows (`exam_id` set, `exam_phase_id` NULL) | **no rows** |
| 3. Row counts grouped by scope shape | **no rows** |

Probe 3 carries no `WHERE` and no user filter, so an empty result means the
**table itself is empty**: `public.user_topic_mastery` holds zero rows. That
subsumes probes 1 and 2.

### What this changes

- **The MASTERY-W1-01 collision is hypothetical, not active.** No user has a
  mastery row, so no accumulated value has been overwritten. D11, D12 and D13
  are real defects in the code but have never fired against data.
- **The scope decision is greenfield.** Choosing §4 or §5 costs no backfill and
  no data migration today. That stops being true at the first live write.
- **W2 creates the first row by default.** The RPC inserts the global row seeded
  at 50 (`145:96-99`) on any live attempt; W1 writes only when a user reviews an
  offline mock carrying `topic_breakdowns`. Absent a decision, the global row
  wins by inaction.
- **Two live consequences of the emptiness**, independent of the scope question:
  every topic currently scores with the 55-point cold-start gap
  (`_score_topic`, `planner.py:874`), and
  `calibration.resolve_required_subjects` (`calibration.py:222-236`) finds no
  validated mastery for any user, so the gate treats every subject as required.

### Still unconfirmed

An empty table and a failed/permission-blocked read look identical from a
`GROUP BY`. One query separates them and also says whether either writer has
ever run end to end:

```sql
select
  (select count(*) from public.user_topic_mastery)       as mastery_rows,
  (select count(*) from public.user_topic_mastery_audit) as audit_rows,
  (select count(*) from public.mock_topic_breakdowns)    as breakdown_rows,
  (select count(*) from public.mock_mastery_shadow)      as shadow_rows;
```

`shadow_rows` is expected to be 127. `audit_rows = 0` would mean W2 has never
written live despite `FF_MOCK_MASTERY_WRITES=live`; `breakdown_rows = 0` would
mean W1 has never had input, i.e. the manual-review path has never run end to
end — which should be established before building on it.

### Confirming counts — 2026-09-13

```
mastery_rows 0 | audit_rows 0 | breakdown_rows 0 | shadow_rows 127
```

`shadow_rows = 127` proves the read is not blocked, so the three zeros are the
real state of the data.

- **`audit_rows = 0` — W2 has never written live.** With
  `FF_MOCK_MASTERY_WRITES=live` and a populated allowlist, not one
  `apply_mock_mastery_delta` call has landed an audit row. Every one of the 127
  rows is a shadow decision.
- **`breakdown_rows = 0` — W1 has never had input.** `mock_topic_breakdowns` is
  empty, so `recompute_topic_mastery` has never written a row in production.

The reason W1 has no input is structural, not incidental:

- the only writer of `mock_topic_breakdowns` is the review PATCH
  (`api/canonical.py:2359-2363`);
- `topic_breakdowns` exists only on the backend request model
  (`canonical.py:2146`);
- **no file under `app/frontend/src` or `app/frontend/e2e` mentions
  `topic_breakdowns` or `topicBreakdowns`** — zero matches. The study Mocks page
  patches `/api/study/mocks/{id}/review-state` with `{state}` alone
  (`app/frontend/src/pages/study/Mocks.jsx:211`).

**Correction to the MASTERY-W1-01 brief.** "W1 has always written it" and "W1 is
the surface for self-reported and third-party mocks… a real product feature" do
not hold in this repository as it stands: W1 has written nothing, and no client
here can make it write. The endpoint accepts the payload; nothing sends it.
Whether the multi-select offline-mock UI was never built, or lives outside this
repo, is not answerable from the code.

**Consequence for sequencing.** Changing W1's write semantics is now a
before-the-fact design choice on an unused path, not a rescue of live data. It
is cheaper to do now than after the UI ships, and it carries no backfill — but
it is not urgent, and the scope question in §4/§5 should be settled first
because it determines which row W1 would even write to.
