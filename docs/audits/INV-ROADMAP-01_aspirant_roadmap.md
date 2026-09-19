# INV-ROADMAP-01 — Aspirant preparation roadmap / journey: what exists, what is missing

- **HEAD:** `5f90e28419101da1a32e5d69b97d27548776587f` (`main`, clean tree)
- **Date:** 2026-09-19
- **Mode:** read-only investigation. No code, schema, API or UI changes. No live DB, no network.
- **Question:** can an aspirant see the roadmap/journey of their preparation — per-subject
  completion status, what is pending, what is completed, which topics need revision, and how
  they got there over time?
- **Scope:** every `file:line` below is at the HEAD above. Items that can only be settled with
  row counts or value distributions are marked **pending operator SQL** and written as
  SELECT-only queries in `INV-ROADMAP-01_operator.sql`.

---

## 1. Verdict

**Partial, and the missing half is the roadmap half.** The aspirant can see *effort* — hours
planned vs done per subject, tasks completed, a mock-score trend, a cycle rail with exam dates
(`plan_timeline.py`, `StudyProgressHub.jsx:21`). They cannot see *coverage*: no surface answers
"how much of my syllabus is done", because the only per-subject number shown is the average
mastery of the locked topics that happen to have a mastery row (`subjects.py:248-249`), and the
only "covered / total" in the product counts locked **high-yield** rows only
(`report_cards.py:311-320`). There is no pending-topic list anywhere. Revision state exists in
two unconnected places and the field named `revision_due` means "mastered", not "decayed"
(`api/study_os.py:1175`). History exists in the database (`user_topic_mastery_audit`,
`user_topic_mastery_evidence`) but both endpoints built to read it are broken against their own
schema and are wired to no screen.

---

## 2. Capability matrix

| # | capability | status | evidence `file:line` | data source | aspirant-visible | gap |
|---|---|---|---|---|---|---|
| **C1** | Surfaces showing progress / plan / mastery / coverage / report card / streak / history | **partial** | `routes/appRoutes.jsx:95-147`; `StudyShell.jsx:6-9` | see §2.1 | y | `/app/study/progress` renders only a mock-score trend (`StudyProgressHub.jsx:21`); the three richest reads have no consumer |
| **C2** | Per-user, per-topic / per-subject state model | **exists** | `033_exam_topic_analytics_snapshots.sql:36`; `:67`; `144_mock_mastery_dark_launch.sql:16`; `205_english_writing_practice_schema.sql:499`; `017_study_os_runtime_schema.sql:12-22`; `034_study_os_exam_intelligence_links.sql:12-24`; `093_revision_calendar.sql:7` | see §2.2 | partly | mock→mastery writes are flag-gated `off` by default (`mastery_writer.py:415-416`) |
| **C3** | A definition of "completed" | **partial + conflicting** | `report_cards.py:271,311-330`; `shared_core.py:38`; `subjects.py:228-230`; `api/study_os.py:1146-1152`; `plan_timeline.py:504` | `user_topic_mastery.mastery_score`, `study_tasks.status` | partly | four different cut-offs (50 / 70 / 75 / task-status); no topic-level "studied" flag at all |
| **C4** | A per-user list of not-yet-started / not-yet-scheduled topics | **absent** | no symbol exists; planner iterates only the locked set it scores (`planner.py:1301`) | — | n | denominator is neither the syllabus nor the plan — there is no denominator |
| **C5** | "Needs revision" — decay, last-studied, SRS interval, due date, error trigger | **partial** | `033:50-51`; `mastery.py:36,72,224`; `mastery_engine/mastery_delta.py:36-37`; `093_revision_calendar.sql:7-27`; `api/study_os.py:1175` | `user_topic_mastery.next_revision_at`, `revision_items`, `user_topic_error_patterns` | partly | `next_revision_at` reaches no screen; `revision_due` is inverted (fires at mastery ≥ 75) |
| **C6** | Rollup microtopic → macro → subject → exam | **partial** | `subjects.py:248-249`; `subjects.py:444-455`; `plan_timeline.py:495-508`; `subjects.py:393` | `exam_topic_coverage` + `user_topic_mastery` | partly | equal weighting only (no PYQ-frequency / priority weighting); `level='concept'` excluded from the tree; no macro-topic tier in any rollup |
| **C7** | Journey / history a timeline could be rebuilt from | **partial** | `144:16-27`; `205:499-546`; `033:88-113`; `100_study_os_report_cards.sql:1-29`; `plan_timeline.py:400-448` | audit + evidence + adaptation-event tables | partly | the two endpoints that read the history are broken (§6 K1, K2); only the plan's planned-vs-actual series is surfaced |
| **C8** | Exam scoping across multiple target exams | **partial, leaky** | `planner.py:413-435`; `planner.py:437-450`; `shared_core.py:11-17,204`; `065_study_os_behavior_foundation.sql:61-72` | `user_topic_mastery`, `user_exam_goals` | n | planner mastery read has no exam filter and falls back to another exam's row; `shared_core` is fail-closed but unconsumed |
| **C9** | Hours / pace data for "on track / behind" | **partial** | `002_core_runtime_schema.sql:25`; `061_user_study_plan_preferences.sql:8-30`; `planner.py:65`; `mission_control.py:1044-1066`; `plan_timeline.py:320,502-505` | `study_tasks.planned_minutes`, `study_sessions.duration_mins`, `study_plans.weekly_hours_goal` | y | no per-topic or per-subject time estimate (H6); pace is task-throughput, not syllabus burn-down |
| **C10** | Host surface for a roadmap view | **exists** | `StudyShell.jsx:6-9`; `appRoutes.jsx:99`; `StudyProgressHub.jsx:1-22` | — | y | the Progress tab already exists and is 22 lines; no new top-level surface is implied |

### 2.1 C1 — surfaces, endpoints, and traced fields

| route | component | endpoint(s) | rendered field → backend source |
|---|---|---|---|
| `/app/study/progress` | `StudyProgressHub.jsx` | `GET /api/study/reports/mock-trend?days=90` | `score_pct`, `accuracy_pct`, `time_used_sec`, `attempt_id` → mock-trend rows (`api/study_os.py:843`) |
| `/app/study/subjects` | `Subjects.jsx` + `SubjectPracticeCard` | `GET /api/study/subjects`; `GET /api/study/subjects/{id}/topics`; `POST …/practice/start` | `progress` → avg `user_topic_mastery.mastery_score` over locked topics **that have a row** (`subjects.py:248-249`); `weak_count` → mastery < 50 OR row in `user_topic_error_patterns` (`subjects.py:228-230`); `locked_topics` → count of locked `exam_topic_coverage.topic_id` (`subjects.py:257`); `trend` → this-week avg vs `_previous_review_mastery_by_subject` (`subjects.py:77-115`) |
| — (drill-down inside the card) | `SubjectTopicTree.jsx` | same `/topics` call | `name`, `level`, `parent_topic_id` → `topics`; `coverage.exam_priority_score`, `coverage.is_high_yield` → locked `exam_topic_coverage` (`subjects.py:431-434`); `evidence_count` → `verified_pyq_topic_counts`; `is_rollup_zero_evidence` → locked row with 0 verified primary tags (`subjects.py:422`). **No per-user field — mastery is deliberately not joined** (`subjects.py:356-357`) |
| `/app/study/review` | `WeeklyReview.jsx` | `GET /api/study/report-card*` | `high_yield_coverage.{covered,total,mastered_threshold}` → `report_cards.py:311-330` (**the only coverage fraction an aspirant can see**); `planned_tasks`/`completed_tasks`/`missed_tasks`/`skipped_tasks`/`carried_forward_tasks`/`planned_minutes`/`completed_minutes`/`focus_minutes` → `study_report_cards` columns (`100:8-18`); `scores.*` → `study_report_cards.scores` jsonb; `backlog_heatmap` → `report_cards.py` `_age_bucket` (`:335`) |
| `/app/study` (Home) | `StudyHome.jsx` + `ExamJourneyCard`, `ExamCycleTimeline`, `PlanChangeLogCard` | `GET /api/study/mission-control`; `/plan/timeline`; `/plan/changelog`; `/report-card/history?period=weekly&limit=2` | `milestones[].{kind,date}`, `phase_bands[].{name,start,end,days,color}` → `plan_timeline.py` `PHASE_BAND_TEMPLATE:41-45` + `exam_cycles`/`exam_phases`; changelog rows → `study_adaptation_events` (`PlanChangeLogCard.jsx:63`) |
| `/app/study/plan` | `StudyPlan.jsx` + `PlanByTopic`, `PlanTimelineTab`, `PlannedVsActualChart`, `CycleSubjectProgress` | `/plan/draft`, `/plan/apply`, `/plan/timeline`, `/plan/by-subject`, `/reports/plan-timeline` | `subjects[].{planned_hours,actual_hours,actual_pct,trust_status}` → `plan_timeline.py:495-508`; `series[].{date,planned_pct,actual_pct}` → `plan_timeline.py:406-448` |
| `/app/study/revision` | `Revision.jsx` | `/api/revision*` | `revision_items` rows (`093_revision_calendar.sql:7-27`) |
| `/app/study/mistakes` | `Mistakes.jsx` | `/api/study/reports/mistakes` | `api/study_os.py:867` |
| `/app/study/learning` | `StudyLearningHub.jsx` | learning-hub links | — |

**Reads with no aspirant consumer** (grep over `app/frontend/src`, test files excluded):

- `GET /api/study/topics` (`api/study_os.py:1102-1195`) — the *only* read that returns
  per-topic `mastery_score`, `next_action` and `revision_due` together. No frontend calls it;
  `SubjectTopicTree.jsx:19-21` explicitly notes the old consumer is dead.
- `GET /api/study/reports/subject-mastery` (`api/study_os.py:1055-1060`).
- `GET /api/study/reports/topic-recovery` (`api/study_os.py:1044-1054`).
- `GET /api/study/regulatory-overlap` (`api/study_os.py:484`).
- Components `SubjectCards.jsx`, `SubjectCard.jsx`, `MasteryDistribution.jsx` and
  `features/study/components/TopicTreePanel.jsx` are imported by nothing outside each other and
  `prototype/screens/Handoff.jsx`.

**Untraced:** `study_report_cards.scores` is a `jsonb` blob (`100:24`); the individual score keys
rendered at `WeeklyReview.jsx:78-85` (`mock_review_score` and siblings) are not traceable to
typed columns from the schema alone. `evidence_summary.mock_score_block.trust_label`
(`WeeklyReview.jsx:85`) is likewise untraced.

### 2.2 C2 — per-user state tables

| table | key columns | writer | reader |
|---|---|---|---|
| `user_topic_mastery` (`033:36`) | `mastery_score numeric(5,2) 0..100`, `accuracy/speed/retention_score`, `confidence_score`, `last_practiced_at`, `next_revision_at`, `evidence_count` | `mastery.py:223-224` (mock breakdowns); `mastery_writer.py` gated by `FF_MOCK_MASTERY_WRITES` (`:415-416`); `writing_practice/mastery_outbox_worker.py` via `writing:mastery_outbox`; `calibration.py:218` (self-report) | `planner.py:413`, `subjects.py`, `report_cards.py`, `shared_core.py:204`, `api/study_os.py:1144` |
| `user_topic_error_patterns` (`033:67`) | `error_type` (9-value CHECK), `frequency_count`, `last_seen_at` | `mastery.py` | `planner.py:437-450`, `subjects.py:229` |
| `user_topic_mastery_audit` (`144:16`) | `before_mastery_db`, `after_mastery_db`, `delta_applied_db`, `reason`, `at`; unique `(user_id, topic_id, attempt_id)` | `145_mock_attempt_jobs.sql:106` | `api/study_os.py:1046` (**broken, see K1**) |
| `user_topic_mastery_evidence` (`205:499`) | append-only; `evidence_tier` ∈ recognition/correction/production/retention, `observed_at`, `evidence_op`, `supersedes_evidence_key` with a one-successor unique index (`205:547`) | EWP evaluation outbox | none on any aspirant surface |
| `study_tasks` (`002:73` + `017:12-22` + `034:12-24`) | `status`, `topic_id`, `subject_id`, `exam_id`, `planned_minutes`, `duration_mins`, `scheduled_date`, `completed_at`, `completion_quality`, `skipped_reason`, `why_this_task`, `priority_score` | planner / `canonical.py:1961` | `plan_timeline.py`, `mission_control.py`, `weekly_review.py`, `report_cards.py` |
| `study_sessions` (`002:72` + `017:24-31`) | `duration_mins`, `started_at`, `ended_at`, `task_id`, `subject_id` | focus logging | `plan_timeline.py:273`, `mission_control.py` |
| `study_plan_versions` (`033:88`) | `version_number`, `reason`, `input_context`, `output_summary`, `activated_at` | planner regen | `/plan/changelog` |
| `study_adaptation_events` (`033:102`) | `event_type` (9-value CHECK), `trigger_payload`, `change_summary` | planner / review | `PlanChangeLogCard.jsx` |
| `revision_items` (`093:7`) | `source_kind`, `scheduled_for`, `interval_days`, `ease`, `repetitions`, `status` | revision API | `/app/study/revision` |
| `study_report_cards` (`100:1`) | task/minute counters, `scores` jsonb, `computed_at` | `report_cards.py` | `/app/study/review`, `Reports.jsx:29` |
| `user_study_plan_preferences` (`061:8`) | `focus`, `max_tasks_per_day`, `preferred_task_size`, `pinned_topic_ids`, `muted_topic_ids`, `auto_regenerate` | `/plan/preferences` | `planner.py` |
| `user_exam_goals` (`065:61`) | `priority_rank`, `weekly_weight_pct`, `status`, `target_date` | goals API | multi-exam weighting |

Not defined in any migration but read by the API: **`subject_mastery_snapshots`** (see K2).

### 2.3 Items pending operator SQL

Nine, keyed to the queries in `INV-ROADMAP-01_operator.sql`:

1. **C3/C4/C6** — whether the target exam has any locked `exam_topic_coverage` at all (Q1). Every
   surface in §2.1 is structurally empty without it.
2. **C4/H9** — the real syllabus denominator: topic counts by level per subject (Q2).
3. **C4/C6/H9** — whether the claimed 18 orphaned pre-split topic rows exist, and whether they
   would render to an aspirant (Q3).
4. **C6** — whether any `level='concept'` rows exist that the tree's level filter hides (Q4).
5. **C2/C6** — whether `user_topic_mastery` is populated, and how thin the `progress` average's
   denominator actually is per subject (Q5, Q7).
6. **C5** — whether `next_revision_at` and `revision_items` carry live rows (Q8).
7. **C7** — whether the audit / evidence / adaptation-event histories are populated at all (Q9).
8. **C8** — how many users hold multi-exam mastery rows or multiple active goals (Q6, Q12).
9. **C9** — whether `study_tasks.planned_minutes` and `topic_id` are actually populated (Q11).

Two further operator-only facts are not SQL: the deployed value of `FF_MOCK_MASTERY_WRITES`
(`mastery_writer.py:415`) and of `FF_TRAP_DRILL_MASTERY_SHADOW`.

---

## 3. Hypothesis check

| # | claim | verdict | evidence |
|---|---|---|---|
| **H1** | Per-user topic state in `user_topic_mastery`, continuous 0–100 `mastery_score`, not a state enum | **confirmed** | `033_exam_topic_analytics_snapshots.sql:43` — `mastery_score numeric(5,2) not null default 0 check (mastery_score >= 0 and mastery_score <= 100)`. No status/state column on the table (`033:36-57`) |
| **H2** | `_HIGH_YIELD_MASTERED_THRESHOLD = 75.0` in `report_cards.py` is the **only** "mastered" cut-off | **refuted** | The constant exists (`report_cards.py:271`) but is one of four: `shared_core.py:38` `DEFAULT_MASTERY_THRESHOLD = 70.0`; `subjects.py:229` weak at `< 50`; `api/study_os.py:1146-1152` `_next_action` bands at 45 / 75; `api/study_os.py:1175` `revision_due` at `>= 75` |
| **H3** | Planner in `study_os/planner*`, `plan_preferences.py`, `plan_timeline.py`; daily regen via APScheduler `study:plan_regen` → `regen.py::regenerate_stale_plans` | **confirmed** | All files present (`ls app/backend/app/study_os/`); job id registered at `notifications/scheduler.py:249,328-330`; `regen.py:137` `def regenerate_stale_plans(supabase, *, limit=200)` with the daily-sweep docstring at `:138-143` |
| **H4** | Task status includes `carried_forward` | **confirmed** | `api/canonical.py:1888` `TASK_STATES = {"planned","in_progress","completed","skipped","missed","rescheduled","carried_forward"}`; rollover write at `:1961`; counter column `100_study_os_report_cards.sql:12` |
| **H5** | Mastery updated from evaluated answers via `writing:mastery_outbox` → `mastery_outbox_worker.py`; mock results via `mock:sweeper` | **partially true** | Writing half exact: job `scheduler.py:254,380-382` → `writing_practice/mastery_outbox_worker.py:26 run_outbox_pass`. Mock half is indirect: `mock:sweeper` (`scheduler.py:251,162-167`) calls `mock_engine.run_sweeper`; the mastery write itself is `mastery_writer.py`, gated by `FF_MOCK_MASTERY_WRITES` with states `off\|shadow\|live` **defaulting to `off`** (`:415-416`). A separate legacy path aggregates mock breakdowns in `mastery.py` |
| **H6** | No `estimated_hours` (or equivalent) column on `topics` | **confirmed** | `029_exam_intelligence_taxonomy.sql:29-44` has no time column; no `estimated_hours`/`estimated_minutes` anywhere in migrations. The only hour data is `aspirant_preferences.study_hours_per_day` (`002:25`), `study_plans.weekly_hours_goal` (`017:8`) and per-task `planned_minutes` (`017:19`) |
| **H7** | No table named `user_syllabus_progress` | **confirmed** | Zero matches across `*.sql`, `*.py`, `*.jsx`, `*.js` |
| **H8** | `/app/study/progress` exists; locked IA rule bars a new top-level surface unless ≥2 are removed | **confirmed** | `routes/appRoutes.jsx:99` → `StudyProgressHub`; tab registered `StudyShell.jsx:9`. Rule at `AGENTS.md` "No-new-surface rule (locked)" and Patterns §18 |
| **H9** | UPSC Mains GS = 456 verified topics (30 macro + 426 microtopic) under syllabus_document `2bfbc4bb-…`; plus 18 orphaned pre-split topic rows not in the reviewed set | **partially true — and the unit is wrong** | The 456 / 30 / 426 split is documented, but it counts **`syllabus_topic_mentions`, not `topics`**: `docs/runbooks/EI-DATA-02_upsc_mains_syllabus_mention_review.md:4` ("456 `syllabus_topic_mentions`") and `:23-24` (30 `explicit` + 426 `derived`). The document id matches (`:44`). The 18-orphan claim appears nowhere in the repo — **pending operator SQL** (Q2, Q3) |
| **H10** | Aspirant reads verified-only and scoped by `subject_id`, not `topic_id` alone | **partially true** | Coverage side holds: `planner.py:259-272` takes `reviewer_status='locked'` only; `subjects.py:408` additionally requires the coverage row's `subject_id` to match. But the **structure** read has no review gate — `subjects.py:388-396` filters `topics` on `subject_id` + `level` + `is_active` only, with no `reviewer_status`; and `planner.py:413-415` / `:437-441` read `user_topic_mastery` and `user_topic_error_patterns` with **no exam scoping at all** |

---

## 4. Conflicts and defects found

**K1 — `/api/study/reports/topic-recovery` cannot execute.** `api/study_os.py:1046` selects
`topic_id, topic_name, created_at, mastery_db` from `user_topic_mastery_audit` and orders by
`created_at`. That table's columns are `id, user_id, topic_id, attempt_id, before_mastery_db,
after_mastery_db, delta_applied_db, reason, at` (`144_mock_mastery_dark_launch.sql:16-27`;
insert list at `145_mock_attempt_jobs.sql:107`; the index is on `(user_id, at desc)` at
`146_plan_timeline_indexes.sql:5-6`). Three of the four selected columns and the order key do not
exist. No frontend calls it, so the drift is unobserved. Confirm with Q10.

**K2 — `/api/study/reports/subject-mastery` reads a table that is in no migration.**
`api/study_os.py:1057` reads `subject_mastery_snapshots`; zero matches across
`app/supabase/migrations/*.sql`. No frontend calls it. Confirm with Q10.

K1 and K2 are precisely the two endpoints that would have carried a per-topic journey and a
per-subject mastery rollup.

**K3 — `revision_due` means the opposite of its name.** `api/study_os.py:1175` sets
`"revision_due": mast is not None and mast >= 75`, so a topic becomes "due for revision" by being
*well mastered*, and a topic at mastery 10 is never flagged. Two lines above, `_next_action`
(`:1146-1152`) returns `"revision"` for the same `>= 75` band, which is coherent as a *mode*
label but not as a *due* flag. Meanwhile the real decay signal — `next_revision_at`, written from
`mastery.py:36` `_REVISION_DAYS = {"low": 2, "medium": 5, "high": 10}` at `:224` — is returned by
no endpoint and rendered nowhere.

**K4 — four unreconciled "done" cut-offs.** 50 (`subjects.py:229`, weak), 70
(`shared_core.py:38`, cross-exam reuse), 75 (`report_cards.py:271` and `api/study_os.py:1175`),
45/75 (`api/study_os.py:1146-1152`, next-action bands). `report_cards.py:271` carries a comment
asserting it "matches `revision_due` in /api/study/topics", which is true of the number and false
of the meaning (K3).

**K5 — "task done" and "topic studied" are never connected.** `study_tasks` carries `topic_id`
(`034:17`) and `completion_quality` (`034:24`), but no code anywhere counts distinct completed
`topic_id`s: a grep for `distinct.*topic_id`, `topics_completed`, `topics_studied`,
`completed_topics` over `app/backend/app` returns nothing. A topic is therefore "done" only via
mastery, which only moves on evaluated attempts — completing every task on a topic moves no
coverage number.

**K6 — the per-subject `progress` denominator is the measured subset, not the subject.**
`subjects.py:248-249` builds `masts` from locked topics **that have a mastery row** and averages
those; topics with no row are excluded rather than counted as 0. One mastered topic out of 97
renders as `progress: 100`. Q7 quantifies the exposure.

**K7 — the plan's own "progress" is self-referential.** `plan_timeline.py:504` sets
`"planned_pct": 100,  # the row represents 100% of its own plan`, and `actual_pct` is completed
minutes over planned minutes for that subject's tasks. "On track" at `CycleSubjectProgress.jsx:38`
therefore means "you did the tasks you were given", with no relation to syllabus coverage.

**K8 — the only aspirant-visible coverage fraction has a high-yield-only denominator.**
`report_cards.py:311-312` takes `total = len(high_yield)` over locked coverage and counts
`covered` as mastery ≥ 75; rendered at `WeeklyReview.jsx:179-205`. Non-high-yield syllabus is
absent from both numerator and denominator, and the UI copy at `:205` states the threshold but not
that the base excludes the rest of the syllabus.

**K9 — cross-exam mastery leakage in the planner read.** `planner.py:413-415` reads
`user_topic_mastery` filtered on `user_id` only. The preference loop at `:426-435` skips a
non-exam row **only when an exam-scoped row for that topic was already seen**, so for any topic
without a row for the current exam a row belonging to a *different* exam is used. `error_topics`
(`:437-441`) has no exam filter at all. `shared_core.py:11-17` documents the correct fail-closed
rule (global rows only) and `:204` implements it — but `shared_core` is reached by no frontend.

**K10 — unfiltered scope and silent truncation in the coverage read.**
`planner.py:262-274` selects locked `exam_topic_coverage` for an exam with **no**
`exam_phase_id` or `exam_cycle_id` filter and `.limit(2000)`; the topic enrichment read is
`.limit(2000)` (`:292-293`), mastery and error reads `.limit(5000)` (`:415`, `:434`). For an exam
with both a Prelims and a Mains phase, one subject list mixes both phases' coverage. Truncation is
silent — there is no count check or warning.

**K11 — session-to-subject matching is by display name.** `plan_timeline.py:481-493` folds logged
session minutes into a subject bucket by case-insensitive `subject_name` string comparison, not by
`subject_id`, even though `study_sessions.subject_id` exists (`034:30`). A renamed or
differently-spelled subject silently drops its actual hours.

**K12 — dead mastery UI.** `MasteryDistribution.jsx`, `SubjectCards.jsx`, `SubjectCard.jsx` and
`features/study/components/TopicTreePanel.jsx` are imported only by each other and by
`prototype/screens/Handoff.jsx`. Mastery-distribution presentation exists and is unmounted.

**K13 — the topic drill-down shows exam priority, never user state.** `subjects.py:356-357`
states "User-specific mastery (`user_topic_mastery`) is intentionally NOT joined here", and
`SubjectTopicTree.jsx:35-36,66,85` renders `exam_priority_score` and `is_high_yield` only. The
one place in the product where an aspirant sees their syllabus as a tree shows what matters to the
examiner and nothing about where they stand.

**K14 — `level='concept'` is invisible.** `subjects.py:393` filters
`in_("level", ["topic", "microtopic"])`. `planner.py:291` selects `level` and passes it through, so
a concept row carrying locked coverage would reach `/api/study/topics` but never the tree. Whether
any such rows exist is Q4. Consistent with the optionals strategy M8-rev3 decision not to use the
concept level (`docs/status/2026-09-10-mains-optionals-strategy-rev3.md`).

**K15 — no review gate on the structure read.** `subjects.py:388-396` reads `topics` with no
`reviewer_status` filter, so an unreviewed or pre-split topic row under a live subject renders to
an aspirant, and `:441-450` deliberately keeps parent-less rows at the top level ("so no topic is
dropped"). This is the mechanism by which H9's claimed orphan rows would surface; Q3 settles
whether any exist.

---

## 5. Open decisions for John

Each is a single question, with only the options the code as it stands already constrains it to.
No recommendation is made.

1. **What is the denominator of "my syllabus"?** The code offers three and uses a different one
   per surface: all locked `exam_topic_coverage` rows for the exam (`subjects.py:257`), locked
   high-yield rows only (`report_cards.py:311-312`), or the current plan's scheduled tasks
   (`plan_timeline.py:504`). A fourth — all `topics` rows under the exam's subjects, which is what
   an aspirant means — is read today only for tree *structure* (`subjects.py:388-396`) and is never
   a denominator.
2. **Which existing cut-off is "done"?** 50, 70, 75, or the 45/75 next-action bands (K4). The
   options are the four constants that already exist; adding a fifth is what this question is for.
3. **Does completing a task count as covering its topic?** `study_tasks.topic_id` and
   `completion_quality` exist (`034:17,24`) and nothing reads them that way (K5). Either task
   completion feeds coverage, or coverage stays mastery-only and task completion stays effort-only.
4. **Which of the two revision mechanisms is authoritative?**
   `user_topic_mastery.next_revision_at` driven by `_REVISION_DAYS` (`mastery.py:36,224`), or
   `revision_items` with its own `interval_days`/`ease`/`repetitions` (`093:7-27`). They are
   unconnected today and only the second reaches a screen.
5. **Is `revision_due` a naming defect or a semantic one?** (K3) Either the field is renamed to
   what it computes (a mastered/revision-mode band), or its predicate is changed to read
   `next_revision_at`. Both are one-line changes with different downstream meanings.
6. **Should the `progress` average count unmeasured topics as 0, or keep reporting the measured
   subset?** (K6) The current behaviour is defensible as "average of what we know" and misleading
   as "% of subject". Both readings are already in the UI copy at `Subjects.jsx:132`.
7. **Is the planner's cross-exam mastery fallback intended?** (K9) `shared_core.py:11-17`
   documents the opposite rule for the same data. Either the planner adopts `shared_core`'s
   fail-closed read, or the fallback is documented as deliberate reuse.
8. **Do K1 and K2 get repaired or deleted?** Both endpoints are unreachable code today
   (`api/study_os.py:1044-1060`). They are also the only two reads aimed at history and
   per-subject rollup.
9. **Does a roadmap view live in the existing Progress tab?** `/app/study/progress` exists, is
   registered in the tab bar (`StudyShell.jsx:9`) and renders 22 lines of mock trend
   (`StudyProgressHub.jsx`). Under the locked no-new-surface rule this is the only host that costs
   no surface; the alternative is the in-card drill-down pattern already used at
   `Subjects.jsx:181-199`.
10. **Is the `exam_phase_id` mixing in `_load_locked_coverage` (K10) in scope of this question?**
    A UPSC aspirant's subject list currently merges Prelims and Mains coverage; per-phase progress
    is impossible until that read is scoped.
