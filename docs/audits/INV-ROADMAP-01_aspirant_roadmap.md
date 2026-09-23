# INV-ROADMAP-01 — Aspirant preparation roadmap / journey: what exists, what is missing

- **HEAD:** `490bd97a5bd0bd4db1f6b288de1e3424ebe37c54` (`main`, clean tree)
- **Date:** 2026-09-19, **re-verified 2026-09-21, 2026-09-22 and again 2026-09-23**

> **Revision note.** The first pass ran against `5f90e28`, which was 167 commits
> behind `origin/main` — a stale clone, not a stale branch. Every `file:line` below
> has been re-read at `f1a37b69`, then again at `f43e6d13`. Four capability rows and five conflicts changed
> materially and are rewritten, not patched: **C1, C4, C6, C10** and **K10**
> (resolved), plus the new planner board, elective scoping and predictability axis.
> Rows that re-verified unchanged keep their original wording with corrected line
> numbers. What landed in between: `planner_board.py` (760 lines), `descriptive.py`
> (954), `planner.py` +595, `api/study_os.py` +355, the `planner-board/` frontend,
> and migrations 287–293. The second re-check (`f1a37b69` → `f43e6d13`) touched exactly
> one cited file, `planner.py`, via `0d5314ec` ("one shared paginated read; delete nine
> short-page copies"): line numbers shifted by up to 3 and are corrected below. No finding
> changed — K9 is still unscoped with `.limit(5000)` and K10 is still resolved, both
> re-read at the new HEAD.
>
> **Third re-check (`f43e6d13` → `490bd97a`, 86 commits).** This one is not a line-number
> pass. ROADMAP-01 landed (`8d4fd4af`, PR #1149) and answers part of this investigation's
> own question: `study_os/roadmap.py` (435 lines), `roadmap_thresholds.py`,
> `GET /api/study/progress/roadmap` (`api/study_os.py:1218-1258`) and `SyllabusRoadmap.jsx`
> (302 lines) mounted on the Progress tab (`StudyProgressHub.jsx:5,22`). **C1, C3, C4, C5,
> C6, C7 and C10 are rewritten, the verdict with them, and K5 is resolved.** Five other
> cited files moved: `api/canonical.py`, `api/study_os.py`, `StudyPlan.jsx` (PLAN-UX-01,
> `c518278b`), `AnswerWriting.jsx`, `descriptive.py` — line numbers corrected below. K1, K2,
> K3, K4, K9 and K10 were re-read at this HEAD and are unchanged in substance.
- **Mode:** read-only investigation. No code, schema, API or UI changes. No live DB, no network.
- **Question:** can an aspirant see the roadmap/journey of their preparation — per-subject
  completion status, what is pending, what is completed, which topics need revision, and how
  they got there over time?
- **Scope:** every `file:line` below is at the HEAD above. Items that can only be settled with
  row counts or value distributions are marked **pending operator SQL** and written as
  SELECT-only queries in `INV-ROADMAP-01_operator.sql`.

---

## 1. Verdict

**Yes, now — for the first time, and with one denominator still wrong.** ROADMAP-01 landed
between the second and third re-check and closes the core of this investigation. An aspirant on
`/app/study/progress` now sees every topic they are scoped to for their target exam, grouped
subject → macro topic → microtopic, each carrying a state derived at read time from evidence that
already existed: `mastered | studied | not_started`, plus independent `weak` and `revise` flags, a
per-macro score, an attempt count, a last-practised date and a 10-point score sparkline
(`roadmap.py:240-259,314-414`, `GET /api/study/progress/roadmap` at `api/study_os.py:1218-1258`,
rendered by `SyllabusRoadmap.jsx:17-19,126-169`). Per-subject rollups carry `weak_count`,
`revise_count` and `pct_mastered` (`roadmap.py:395-410`). The thresholds are returned in the
payload and rendered as the legend, so the screen states the rule it used
(`roadmap.py:417-423`, `SyllabusRoadmap.jsx:77-81`).

Three things follow. **C4 is answered** — "never touched" and "finished last month" are now
distinguishable, which the palette alone could not do (K17). **K5 is resolved** — completing a task
finally moves a topic's state (`roadmap.py:193-205,258-259`). **Nothing new was invented to do it**:
`MASTERED_AT = 75.0` is pinned to `report_cards._HIGH_YIELD_MASTERED_THRESHOLD` with a drift test,
and `WEAK_BELOW = 50.0` matches `subjects.py:240` (`roadmap_thresholds.py:7-24`).

What is still missing is the **denominator**. The roadmap's universe is the user's scoped *locked*
`exam_topic_coverage` plus the macro parents of those rows (`roadmap.py:8-19`, via
`planner.load_scoped_coverage_checked`) — not the syllabus. A topic with no locked coverage row is
invisible on the roadmap exactly as it is everywhere else, so "12% mastered" means 12% of what was
locked, not of what will be examined. Alongside that, the older defects are untouched: the only
per-subject number outside the roadmap remains the average mastery of locked topics that happen to
have a mastery row (`subjects.py:259-260`); the only "covered / total" on the report card still
counts locked **high-yield** rows only (`report_cards.py:311-312`); `revision_due` on
`/api/study/topics` still fires at mastery ≥ 75 (`api/study_os.py:1388`, K3) while the roadmap's own
`revise` flag means the opposite and correct thing (`roadmap.py:252-255`); and the two endpoints
that would carry a cross-topic history are still broken against their own schema and wired to no
screen (K1, K2).

## 2. Capability matrix

| # | capability | status | evidence `file:line` | data source | aspirant-visible | gap |
|---|---|---|---|---|---|---|
| **C1** | Surfaces showing progress / plan / mastery / coverage / report card / streak / history | **exists** *(rewritten — was partial)* | `routes/appRoutes.jsx:96-134`; `StudyShell.jsx:6-9`; `StudyPlan.jsx:686-694`; **new:** `StudyProgressHub.jsx:5,22`, `SyllabusRoadmap.jsx:246-252` | see §2.1 | y | the Progress tab is no longer 22 lines of mock trend: it mounts `SyllabusRoadmap`, the first surface that shows per-user state across the whole scoped tree. K1 and K2 still have no consumer |
| **C2** | Per-user, per-topic / per-subject state model | **exists** | `033_exam_topic_analytics_snapshots.sql:36`; `:67`; `144_mock_mastery_dark_launch.sql:16`; `205_english_writing_practice_schema.sql:499`; `017_study_os_runtime_schema.sql:12-22`; `034_study_os_exam_intelligence_links.sql:12-24`; `093_revision_calendar.sql:7`; **new:** `289_study_tasks_user_origin.sql:24`, `290_study_tasks_day_ordinal.sql:20`, `293_descriptive_attempts.sql:18` | see §2.2 | partly | mock→mastery writes still flag-gated `off` by default (`mastery_writer.py:521`) |
| **C3** | A definition of "completed" | **exists, still not reconciled** *(rewritten)* | **new:** `roadmap_thresholds.py:14-24`, `roadmap.py:240-259`; `report_cards.py:271,311-330`; `shared_core.py:38`; `subjects.py:240`; `api/study_os.py:1358-1364`; `plan_timeline.py:517` | `user_topic_mastery.mastery_score`, `user_topic_mastery_audit`, `study_tasks.status` | y | a topic-level state enum now exists — `mastered \| studied \| not_started`, with `mastered` at ≥ 75 after ≥ 2 attempts and `studied` at ≥ 1 completed task or ≥ 1 attempt. It reuses the existing 75 and 50 rather than adding a fifth cut-off (a test pins `MASTERED_AT` to `report_cards._HIGH_YIELD_MASTERED_THRESHOLD`), but the other four readings are untouched and still disagree with each other (K4) |
| **C4** | A per-user list of not-yet-started / not-yet-scheduled topics | **exists** *(rewritten twice — absent, then partial)* | **new:** `roadmap.py:240-245,258-259,314-414`; `SyllabusRoadmap.jsx:100-169`; plus `planner_board.py:330-360,455-478`; `syllabusTree.js:1-12,38-60`; `PaletteCard.jsx:20-23` | scoped locked `exam_topic_coverage` + `user_topic_mastery(_audit)` + completed `study_tasks` | y | `not_started` is now a real per-user state over the whole scoped tree, not "absent from this week's board", so a topic never opened is distinguishable from one finished last month — the gap K17 named. The denominator is still scoped **locked coverage**, not the syllabus (`roadmap.py:8-19`) |
| **C5** | "Needs revision" — decay, last-studied, SRS interval, due date, error trigger | **partial** *(rewritten)* | **new:** `roadmap.py:252-255`, `roadmap_thresholds.py:24`; `033:50-51`; `mastery.py:36,72,224`; `mastery_engine/mastery_delta.py:36-37`; `093_revision_calendar.sql:7-27`; `api/study_os.py:1388` | `user_topic_mastery_audit.at`, `next_revision_at`, `revision_items`, `user_topic_error_patterns` | y | an aspirant can now see a decay signal: `revise` = mastered and not practised for more than 14 days, from the audit trail. But it is a **third** mechanism — `next_revision_at` (`_REVISION_DAYS`) and `revision_items` (`interval_days`/`ease`) still exist, still disagree, and `next_revision_at` still reaches no screen; `revision_due` on `/api/study/topics` is still inverted (K3) |
| **C6** | Rollup microtopic → macro → subject → exam | **exists** *(rewritten — was partial)* | **new:** `roadmap.py:302-312` (`_root_of`), `:347-391` (macro from children), `:395-410` (subject counts, `pct_mastered`); `subjects.py:259-260,404,455-466`; `plan_timeline.py:506-528`; `syllabusTree.js:6-11` | `exam_topic_coverage` + `user_topic_mastery(_audit)` + `study_tasks` | y | the macro tier now carries **per-user state**, not just counts: a macro's score is its own mastery row, else the attempts-weighted mean of its children (`roadmap.py:354-364`), and each subject rolls up to `not_started`/`studied`/`mastered` counts plus `pct_mastered`. Exam tier is still implicit (one exam per read). `level='concept'` still excluded everywhere (`subjects.py:404`, K14) |
| **C7** | Journey / history a timeline could be rebuilt from | **partial** *(rewritten)* | **new:** `roadmap.py:277-300` (`_audit_stats`: attempts, `last_practiced`, 10-point history), `roadmap_thresholds.py:27`, `SyllabusRoadmap.jsx:49-64` (sparkline); `144:16-27`; `205:499-546`; `033:88-113`; `100_study_os_report_cards.sql:1-29`; `plan_timeline.py:398-451` | audit + evidence + adaptation-event tables | y | `user_topic_mastery_audit` finally reaches a screen: the last 10 score points per macro topic, plus a last-practised date. It is per-topic and capped at 10 points — not a journey. K1 and K2, the two endpoints that would carry the full series, are still broken |
| **C8** | Exam scoping across multiple target exams | **partial, leaky** *(nuance added)* | `planner.py:760-783`; `planner.py:788-791`; `shared_core.py:11-17,204`; `065_study_os_behavior_foundation.sql:61-72`; **new:** `287_exam_electives.sql:26-53,78`, `planner.py:652-701`, `subjects.py:489-520` | `user_topic_mastery`, `user_exam_goals`, `user_exam_electives` | partly | **elective** scoping (which optional paper, within one exam) now exists and is enforced on every learner read. **Cross-exam** scoping is unchanged: the planner mastery read still has no exam filter (K9) |
| **C9** | Hours / pace data for "on track / behind" | **partial** | `002_core_runtime_schema.sql:25`; `061_user_study_plan_preferences.sql:8-30`; `planner.py:71`; `mission_control.py:1053`; `plan_timeline.py:326,515-518` | `study_tasks.planned_minutes`, `study_sessions.duration_mins`, `study_plans.weekly_hours_goal` | y | unchanged: no per-topic or per-subject time estimate (H6); pace is task throughput, not syllabus burn-down |
| **C10** | Host surface for a roadmap view | **exists and is occupied** *(rewritten)* | `StudyShell.jsx:6-9`; `appRoutes.jsx:100`; `StudyProgressHub.jsx:1-23`; `StudyPlan.jsx:686-694` | — | y | the question is settled: the roadmap went to the **Progress tab** (`StudyProgressHub.jsx:5,22`), under the existing route, so the locked no-new-surface rule was never engaged. The Plan page's tab strip still carries "Arrange" and "Plan changes"; decision 9 below is now about what the two hosts should each own, not where the roadmap goes |

### 2.1 C1 — surfaces, endpoints, and traced fields

| route | component | endpoint(s) | rendered field → backend source |
|---|---|---|---|
| `/app/study/progress` | `StudyProgressHub.jsx` + **`SyllabusRoadmap.jsx`** *(new)* | `GET /api/study/reports/mock-trend?days=90`; **`GET /api/study/target-exam`; `GET /api/study/progress/roadmap?exam_id=`** | `score_pct`, `accuracy_pct`, `time_used_sec`, `attempt_id` → mock-trend rows (`api/study_os.py:1000`). **Roadmap:** `subjects[].{name,counts,weak_count,revise_count,pct_mastered}` → derived (`roadmap.py:395-410`); `macro.{state,score,attempts,last_practiced,weak,revise,history,completed_tasks}` → `user_topic_mastery` + `user_topic_mastery_audit` + completed `study_tasks`, bounded by scoped locked coverage (`roadmap.py:99-215,347-391`); `micro.{state,completed_tasks}` → completed `study_tasks` only (`roadmap.py:258-259`); `thresholds` → `roadmap_thresholds.py`, rendered verbatim as the legend (`SyllabusRoadmap.jsx:77-81`) |
| `/app/study/plan` → **"Arrange" tab** *(new)* | `PlannerBoard.jsx` + `TopicPalette`, `PaletteCard`, `DayColumn`, `TaskCard` | `GET /api/study/plan/board`; `GET /api/study/plan/candidates`; `POST /plan/board/tasks`; `PATCH …/placement`; `DELETE …/{id}` | `topic`, `subject`, `parent_topic` → scoped locked coverage + `topics` (`planner_board.py:455-470`); `selection_kind` → `exam_sections.selection_kind` (`287_exam_electives.sql:26-53`); `scheduled_date` → this week's `study_tasks` (`planner_board.py:378-392`), rendered as the placed/unplaced pill (`PaletteCard.jsx:20-23`); `predictability_band` → `exam_topic_coverage.predictability_band` (`288_predictability_axis.sql:33-38`); subject/macro `count` → client-side group sizes (`syllabusTree.js:38-60`, rendered `TopicPalette.jsx:150,182`). `comparable_priority` orders the list and is deliberately **not** displayed (`planner_board.py:463-466`) |
| `/app/study/subjects` | `Subjects.jsx` + `SubjectPracticeCard` | `GET /api/study/subjects`; `GET /api/study/subjects/{id}/topics`; `POST …/practice/start` | `progress` → avg `user_topic_mastery.mastery_score` over scoped locked topics **that have a row** (`subjects.py:259-260`); `weak_count` → mastery < 50 OR row in `user_topic_error_patterns` (`subjects.py:240`); `locked_topics` → count of scoped locked `exam_topic_coverage.topic_id` (`subjects.py:268`); `trend` → this-week avg vs `_previous_review_mastery_by_subject` (`subjects.py:88-126`) |
| — (drill-down inside the card) | `SubjectTopicTree.jsx` | same `/topics` call | `name`, `level`, `parent_topic_id` → `topics`; `coverage.exam_priority_score`, `coverage.is_high_yield` → scoped locked `exam_topic_coverage` (`subjects.py:442-448`); `evidence_count` → `verified_pyq_topic_counts`; `is_rollup_zero_evidence` → locked row with 0 verified primary tags (`subjects.py:433`). **No per-user field — mastery is deliberately not joined** (`subjects.py:367`) |
| `/app/study/review` | `WeeklyReview.jsx` | `GET /api/study/report-card*` | `high_yield_coverage.{covered,total,mastered_threshold}` → `report_cards.py:311-330` (**still the only coverage fraction an aspirant can see**); `planned_tasks`/`completed_tasks`/`missed_tasks`/`skipped_tasks`/`carried_forward_tasks`/`planned_minutes`/`completed_minutes`/`focus_minutes` → `study_report_cards` columns (`100:8-18`); `scores.*` → `study_report_cards.scores` jsonb; `backlog_heatmap` → `report_cards.py` `_age_bucket` |
| `/app/study` (Home) | `StudyHome.jsx` + `ExamJourneyCard`, `ExamCycleTimeline`, `PlanChangeLogCard` | `GET /api/study/mission-control`; `/plan/timeline`; `/plan/changelog`; `/report-card/history?period=weekly&limit=2` | `milestones[].{kind,date}`, `phase_bands[].{name,start,end,days,color}` → `plan_timeline.py` `PHASE_BAND_TEMPLATE` + `exam_cycles`/`exam_phases`; changelog rows → `study_adaptation_events` (`PlanChangeLogCard.jsx:63`) |
| `/app/study/plan` (main tab) | `StudyPlan.jsx` + `CycleCountdown`, `WeekTruth`, `PlanRiskNotes`, `PlanByTopic`, `PlanTimelineTab`, `CycleSubjectProgress` | `/plan/draft`, `/plan/apply`, `/plan/timeline`, `/plan/by-subject`, `/reports/plan-timeline` | `subjects[].{planned_hours,actual_hours,actual_pct,trust_status}` → `plan_timeline.py:506-528`, now elective-filtered (`plan_timeline.py:453-466`, `subjects.py:489-520`); `series[].{date,planned_pct,actual_pct}` → `plan_timeline.py:398-451` |
| `/app/study/answer-writing` *(new)* | `AnswerWriting.jsx` + `QuestionScreen`, `AnswerEditor`, `RubricPanel` | descriptive-attempt endpoints | `descriptive_attempts` (`293_descriptive_attempts.sql:18-50`) — self-scored rubric, `word_count`, `time_spent_seconds`. Writes no `user_topic_mastery` |
| `/app/study/revision` | `Revision.jsx` | `/api/revision*` | `revision_items` rows (`093_revision_calendar.sql:7-27`) |
| `/app/study/mistakes` | `Mistakes.jsx` | `/api/study/reports/mistakes` | `api/study_os.py:1024` |
| `/app/study/learning` | `StudyLearningHub.jsx` | learning-hub links | now also the entry point for Answer Writing |

**Reads with no aspirant consumer** — re-checked at this HEAD, all four still orphaned:

- `GET /api/study/topics` (`api/study_os.py:1302-1410`) — still the *only* read returning per-topic
  `mastery_score`, `next_action` and `revision_due` together, and still called by no frontend file.
- `GET /api/study/reports/subject-mastery` (`api/study_os.py:1213-1217`).
- `GET /api/study/reports/topic-recovery` (`api/study_os.py:1201-1210`).
- `GET /api/study/regulatory-overlap` (`api/study_os.py:619`).
- `SubjectCards.jsx`, `SubjectCard.jsx`, `MasteryDistribution.jsx` and
  `features/study/components/TopicTreePanel.jsx` — zero importers outside their own dir and the
  prototype Handoff page (K12, re-confirmed).

**Untraced:** `study_report_cards.scores` is a `jsonb` blob (`100:24`); the score keys rendered at
`WeeklyReview.jsx:78-85` (`mock_review_score` and siblings) are not traceable to typed columns from
the schema alone, and neither is `evidence_summary.mock_score_block.trust_label`
(`WeeklyReview.jsx:85`).

### 2.2 C2 — per-user state tables

| table | key columns | writer | reader |
|---|---|---|---|
| `user_topic_mastery` (`033:36`) | `mastery_score numeric(5,2) 0..100`, `accuracy/speed/retention_score`, `confidence_score`, `last_practiced_at`, `next_revision_at`, `evidence_count` | `mastery.py:223-224` (mock breakdowns); `mastery_writer.py` gated by `FF_MOCK_MASTERY_WRITES` (`:521`); `writing_practice/mastery_outbox_worker.py` via `writing:mastery_outbox`; `calibration.py` (self-report) | `planner.py:760`, `subjects.py`, `report_cards.py`, `shared_core.py:204`, `api/study_os.py:1302+`, `roadmap.py:99-215` |
| `user_topic_error_patterns` (`033:67`) | `error_type` (9-value CHECK), `frequency_count`, `last_seen_at` | `mastery.py` | `planner.py:788-791`, `subjects.py:240` |
| `user_topic_mastery_audit` (`144:16`) | `before_mastery_db`, `after_mastery_db`, `delta_applied_db`, `reason`, `at`; unique `(user_id, topic_id, attempt_id)` | `145_mock_attempt_jobs.sql:106` | `api/study_os.py:1204` (**broken, see K1**); also read correctly for plan-impact events at `api/study_os.py:1147`; **new:** `roadmap.py:181-192` reads it correctly for attempts, last-practised and score history |
| `user_topic_mastery_evidence` (`205:499`) | append-only; `evidence_tier` ∈ recognition/correction/production/retention, `observed_at`, `evidence_op`, `supersedes_evidence_key` with a one-successor unique index (`205:547`) | EWP evaluation outbox | none on any aspirant surface |
| `study_tasks` (`002:73` + `017:12-22` + `034:12-24` + **`289:24`** + **`290:20`**) | `status`, `topic_id`, `subject_id`, `exam_id`, `planned_minutes`, `duration_mins`, `scheduled_date`, `completed_at`, `completion_quality`, `skipped_reason`, `why_this_task`, `priority_score`, **`source` ∈ planner\|user**, **`day_ordinal`** | planner / `canonical.py:2047` / `planner_board.py` (board mutations stamp `source='user'`) | `plan_timeline.py`, `mission_control.py`, `weekly_review.py`, `report_cards.py`, `planner_board.py` |
| `study_sessions` (`002:72` + `017:24-31`) | `duration_mins`, `started_at`, `ended_at`, `task_id`, `subject_id` | focus logging | `plan_timeline.py:273`, `mission_control.py` |
| `study_plan_versions` (`033:88`) | `version_number`, `reason`, `input_context`, `output_summary`, `activated_at` | planner regen | `/plan/changelog` |
| `study_adaptation_events` (`033:102`) | `event_type` (9-value CHECK), `trigger_payload`, `change_summary` | planner / review | `PlanChangeLogCard.jsx` |
| `revision_items` (`093:7`) | `source_kind`, `scheduled_for`, `interval_days`, `ease`, `repetitions`, `status` | revision API | `/app/study/revision` |
| `study_report_cards` (`100:1`) | task/minute counters, `scores` jsonb, `computed_at` | `report_cards.py` | `/app/study/review`, `Reports.jsx:29` |
| `user_study_plan_preferences` (`061:8`) | `focus`, `max_tasks_per_day`, `preferred_task_size`, `pinned_topic_ids`, `muted_topic_ids`, `auto_regenerate` | `/plan/preferences` | `planner.py` |
| `user_exam_goals` (`065:61`) | `priority_rank`, `weekly_weight_pct`, `status`, `target_date` | goals API | multi-exam weighting |

| `user_exam_electives` (`287:78`) *(new)* | the optional paper this user chose; `exam_sections.selection_kind` ∈ compulsory\|elective, `elective_group` (`287:26-53`) | elective-choice API | `planner.load_scoped_coverage` (`planner.py:652-701`) — every learner-facing coverage read |
| `descriptive_attempts` (`293:18`) *(new)* | `status` ∈ draft\|submitted, `word_count`, `time_spent_seconds`, `self_total` 0–12 | `/app/study/answer-writing` | the answer-writing surface only — **writes no `user_topic_mastery`** |

Not defined in any migration but read by the API: **`subject_mastery_snapshots`** — re-checked at
this HEAD, still absent from all of `app/supabase/migrations/*.sql` (see K2).

### 2.3 Items pending operator SQL

Thirteen, keyed to the queries in `INV-ROADMAP-01_operator.sql`:

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

10. **C4/C8** — whether `exam_sections.selection_kind` and `user_exam_electives` are populated
    (Q15). Every learner coverage read now filters on them; an empty elective table means
    `load_scoped_coverage` is a no-op and the new palette scoping is untested in practice.
11. **C6** — whether `exam_topic_coverage.predictability_band` is populated (Q16). The palette
    renders nothing where it is null, so an unpopulated column makes the new axis invisible.
12. **C4/K17** — how much of the palette's "unplaced" set the user has already mastered (Q17).
    This is the size of the gap K17 describes.
13. **C2/K5** — whether `study_tasks.source` and `day_ordinal` carry real values (Q18).

ROADMAP-01 raises the stakes on three of these without adding a query. The roadmap's whole tree is
the scoped locked coverage set, so **Q1** now decides whether the Progress tab renders anything at
all (`SyllabusRoadmap.jsx:282` has a dedicated "not ready" state for it). **Q5** decides whether
macro scores exist or every topic renders `not_started`. **Q9** decides whether
`user_topic_mastery_audit` carries the attempts and history the roadmap counts on — with an empty
audit table, `MIN_ATTEMPTS = 2` makes `mastered` and `weak` unreachable and every practised topic
renders as the middle state. No new query is added: the three existing ones answer it.

Two further operator-only facts are not SQL: the deployed value of `FF_MOCK_MASTERY_WRITES`
(`mastery_writer.py:521`) and of `FF_TRAP_DRILL_MASTERY_SHADOW`.

---

## 3. Hypothesis check

| # | claim | verdict | evidence |
|---|---|---|---|
| **H1** | Per-user topic state in `user_topic_mastery`, continuous 0–100 `mastery_score`, not a state enum | **confirmed** | `033_exam_topic_analytics_snapshots.sql:43` — `mastery_score numeric(5,2) not null default 0 check (mastery_score >= 0 and mastery_score <= 100)`. No status/state column on the table (`033:36-57`) |
| **H2** | `_HIGH_YIELD_MASTERED_THRESHOLD = 75.0` in `report_cards.py` is the **only** "mastered" cut-off | **refuted** | The constant exists (`report_cards.py:271`) but is one of four: `shared_core.py:38` `DEFAULT_MASTERY_THRESHOLD = 70.0`; `subjects.py:240` weak at `< 50`; `api/study_os.py:1358-1364` `_next_action` bands at 45 / 75; `api/study_os.py:1388` `revision_due` at `>= 75`. ROADMAP-01 adds a fifth *user* of 75 (`roadmap_thresholds.MASTERED_AT`) but not a fifth *value*: it is pinned to `report_cards._HIGH_YIELD_MASTERED_THRESHOLD` and guarded by a drift test (`roadmap_thresholds.py:7-9`) |
| **H3** | Planner in `study_os/planner*`, `plan_preferences.py`, `plan_timeline.py`; daily regen via APScheduler `study:plan_regen` → `regen.py::regenerate_stale_plans` | **confirmed** | All files present (`ls app/backend/app/study_os/`); job id registered in `notifications/scheduler.py`; `regen.py:137` `def regenerate_stale_plans(supabase, *, limit=200)` with the daily-sweep docstring at `:138-143` |
| **H4** | Task status includes `carried_forward` | **confirmed** | `api/canonical.py:1974` `TASK_STATES = {"planned","in_progress","completed","skipped","missed","rescheduled","carried_forward"}`; rollover write at `:2047`; counter column `100_study_os_report_cards.sql:12` |
| **H5** | Mastery updated from evaluated answers via `writing:mastery_outbox` → `mastery_outbox_worker.py`; mock results via `mock:sweeper` | **partially true** | Writing half exact: job `scheduler.py:254,380-382` → `writing_practice/mastery_outbox_worker.py:26 run_outbox_pass`. Mock half is indirect: `mock:sweeper` (`scheduler.py:251,162-167`) calls `mock_engine.run_sweeper`; the mastery write itself is `mastery_writer.py`, gated by `FF_MOCK_MASTERY_WRITES` with states `off\|shadow\|live` **defaulting to `off`** (`:521`). A separate legacy path aggregates mock breakdowns in `mastery.py` |
| **H6** | No `estimated_hours` (or equivalent) column on `topics` | **confirmed** | `029_exam_intelligence_taxonomy.sql:29-44` has no time column; no `estimated_hours`/`estimated_minutes` anywhere in migrations. The only hour data is `aspirant_preferences.study_hours_per_day` (`002:25`), `study_plans.weekly_hours_goal` (`017:8`) and per-task `planned_minutes` (`017:19`) |
| **H7** | No table named `user_syllabus_progress` | **confirmed** | Zero matches across `*.sql`, `*.py`, `*.jsx`, `*.js` |
| **H8** | `/app/study/progress` exists; locked IA rule bars a new top-level surface unless ≥2 are removed | **confirmed** | `routes/appRoutes.jsx:100` → `StudyProgressHub`; tab registered `StudyShell.jsx:9`. Rule at `AGENTS.md` "No-new-surface rule (locked)" and Patterns §18 |
| **H9** | UPSC Mains GS = 456 verified topics (30 macro + 426 microtopic) under syllabus_document `2bfbc4bb-…`; plus 18 orphaned pre-split topic rows not in the reviewed set | **partially true — and the unit is wrong** | The 456 / 30 / 426 split is documented, but it counts **`syllabus_topic_mentions`, not `topics`**: `docs/runbooks/EI-DATA-02_upsc_mains_syllabus_mention_review.md:4` ("456 `syllabus_topic_mentions`") and `:23-24` (30 `explicit` + 426 `derived`). The document id matches (`:44`); re-verified unchanged at this HEAD. The 18-orphan claim appears nowhere in the repo — **pending operator SQL** (Q2, Q3) |
| **H10** | Aspirant reads verified-only and scoped by `subject_id`, not `topic_id` alone | **partially true** | Coverage side holds: `planner.py:311-354` takes `reviewer_status='locked'` only, and `load_scoped_coverage` (`planner.py:652-701`) now additionally applies elective scope; `subjects.py:419` requires the coverage row's `subject_id` to match. But the **structure** read still has no review gate — `subjects.py:399-410` filters `topics` on `subject_id` + `level` + `is_active` only, with no `reviewer_status`; and `planner.py:760-764` / `:788-791` still read `user_topic_mastery` and `user_topic_error_patterns` with **no exam scoping at all** |

---

## 4. Conflicts and defects found

Every item below was re-read at `490bd97a`. **K5 and K10 are resolved**; the rest survive with
corrected line numbers, and K13 and K17 are narrowed by ROADMAP-01 rather than closed by it.

**K1 — `/api/study/reports/topic-recovery` cannot execute.** *(still live)* `api/study_os.py:1204`
selects `topic_id, topic_name, created_at, mastery_db` from `user_topic_mastery_audit` and orders by
`created_at`. That table's columns are `id, user_id, topic_id, attempt_id, before_mastery_db,
after_mastery_db, delta_applied_db, reason, at` (`144_mock_mastery_dark_launch.sql:16-27`; insert
list at `145_mock_attempt_jobs.sql:107`; the index is on `(user_id, at desc)` at
`146_plan_timeline_indexes.sql:5-6`). Three of the four selected columns and the order key do not
exist. No frontend calls it, so the drift is still unobserved. Note the same table IS read
correctly fifty-odd lines earlier, for plan-impact events (`api/study_os.py:1147`) — so the
column names were available to copy. Confirm with Q10.

**K2 — `/api/study/reports/subject-mastery` reads a table that is in no migration.** *(still live)*
`api/study_os.py:1213` reads `subject_mastery_snapshots`; re-grepped at this HEAD, zero matches
across `app/supabase/migrations/*.sql`. No frontend calls it. Confirm with Q10.

K1 and K2 remain the two endpoints that would have carried a per-topic journey and a per-subject
mastery rollup.

**K3 — `revision_due` means the opposite of its name.** *(still live)* `api/study_os.py:1388` sets
`"revision_due": mast is not None and mast >= 75`, so a topic becomes "due for revision" by being
*well mastered*, and a topic at mastery 10 is never flagged. `_next_action`
(`api/study_os.py:1358-1364`) returns `"revision"` for the same `>= 75` band, coherent as a *mode*
label but not as a *due* flag. The real decay signal — `next_revision_at`, written from
`mastery.py:36` `_REVISION_DAYS = {"low": 2, "medium": 5, "high": 10}` at `:224` — is returned by no
endpoint and rendered nowhere.

**K4 — four unreconciled "done" cut-offs.** *(still live)* 50 (`subjects.py:240`, weak), 70
(`shared_core.py:38`, cross-exam reuse), 75 (`report_cards.py:271` and `api/study_os.py:1388`),
45/75 (`api/study_os.py:1358-1364`, next-action bands). `report_cards.py:271` still carries the
comment asserting it "matches `revision_due` in /api/study/topics" — true of the number, false of
the meaning (K3).

**K5 — RESOLVED.** The first two passes found that `study_tasks.topic_id` (`034:17`) and
`completion_quality` (`034:24`) existed and that no code counted completed tasks per topic, so
finishing every task on a topic moved no number an aspirant could see. ROADMAP-01 closes it:
`roadmap.py:193-205` reads completed `study_tasks` bounded by the scoped topic and subject ids,
and `completed_tasks >= 1` is one of the two ways a macro topic reaches `studied`
(`:243-244`) and the **only** way a microtopic does (`:258-259`). The number is now on the screen
(`SyllabusRoadmap.jsx:100-123`). `completion_quality` is still read by nothing.

**K6 — the per-subject `progress` denominator is the measured subset, not the subject.**
*(still live)* `subjects.py:259-260` builds `masts` from scoped locked topics **that have a mastery
row** and averages those; topics with no row are excluded rather than counted as 0. One mastered
topic out of 97 renders as `progress: 100`. Q7 quantifies the exposure.

**K7 — the plan's own "progress" is self-referential.** *(still live)* `plan_timeline.py:517` sets
`"planned_pct": 100,  # the row represents 100% of its own plan`, and `actual_pct` is completed
minutes over planned minutes for that subject's tasks. "On track" at `CycleSubjectProgress.jsx:38`
still means "you did the tasks you were given", with no relation to syllabus coverage.

**K8 — the only aspirant-visible coverage fraction has a high-yield-only denominator.**
*(still live)* `report_cards.py:311-312` takes `total = len(high_yield)` over scoped locked
coverage and counts `covered` as mastery ≥ 75 (`:322`); rendered at `WeeklyReview.jsx:179-205`.
Non-high-yield syllabus is absent from both numerator and denominator. The read is now elective-
scoped (`report_cards.py:310`), which narrows the base further without changing what it means.

**K9 — cross-exam mastery leakage in the planner read.** *(still live, unchanged)*
`planner.py:760-764` reads `user_topic_mastery` filtered on `user_id` only, with `.limit(5000)`.
The preference loop at `:777-786` skips a non-exam row **only when an exam-scoped row for that
topic was already seen**, so for any topic without a row for the current exam a row belonging to a
*different* exam is used. `error_topics` (`:788-791`) has no exam filter at all. `shared_core.py:11-17`
still documents the correct fail-closed rule and `:204` still implements it — and `shared_core` is
still reached by no frontend. Note the contrast with the elective work (K16): within-exam scoping
was hardened thoroughly while this cross-exam read was left as it was.

**K10 — RESOLVED.** The first pass found `.limit(2000)` and no phase filter on the locked-coverage
read. Both are fixed at this HEAD: the read is now fully paginated with an exact count
(`planner.py:324-354`, `_paginate_all`), and phase duplicates are collapsed by
`_canonical_coverage_rows(coverage, phase_rows)` under COV-PHASE-01 (`planner.py:681-701`). The
mastery and error reads still carry `.limit(5000)` (K9).

**K11 — session-to-subject matching is by display name.** *(still live)* `plan_timeline.py:493-498`
still folds logged session minutes into a subject bucket by case-insensitive `subject_name` string
comparison, not by `subject_id`, even though `study_sessions.subject_id` exists (`034:30`). The
elective filter added around it (`:506-507`) operates on `subject_id` — so the two now disagree
about what identifies a subject within the same function.

**K12 — dead mastery UI.** *(still live)* `MasteryDistribution.jsx`, `SubjectCards.jsx`,
`SubjectCard.jsx` and `features/study/components/TopicTreePanel.jsx` still have zero importers
outside their own directory and `prototype/screens/Handoff.jsx`. Re-confirmed by import grep at
this HEAD.

**K13 — the topic drill-down shows exam priority, never user state.** *(narrowed, still live)*
`subjects.py:367` still states "User-specific mastery (`user_topic_mastery`) is intentionally NOT
joined here", and `SubjectTopicTree.jsx:35-36,66,85` renders `exam_priority_score` and
`is_high_yield` only. The palette (K16) repeats the pattern. The roadmap is now the **third**
syllabus tree an aspirant can open and the first that carries per-user state — so the defect is no
longer "no tree shows state" but "three trees over the same topics show three different things,
and only one of them is about the user".

**K14 — `level='concept'` is invisible.** *(still live)* `subjects.py:404` filters
`in_("level", ["topic", "microtopic"])`. The new palette tree is explicitly two-level by design
(`syllabusTree.js:6-11`), so concept rows are excluded there too. Whether any exist is Q4.

**K15 — no review gate on the structure read.** *(still live)* `subjects.py:399-410` reads `topics`
with no `reviewer_status` filter, and `:455-466` still keeps parent-less rows at the top level "so
no topic is dropped". Q3 settles whether any orphans exist.

**K16 — elective scoping is thorough within an exam and absent across exams.** *(new)*
`load_scoped_coverage` (`planner.py:652-701`) filters coverage by the user's chosen optional via
`exam_sections.selection_kind` (`287_exam_electives.sql:26-53`) and `user_exam_electives`
(`287:78`), and every learner read was migrated onto it: `subjects.py:205-216`, `:392`, `:414`,
`report_cards.py:310`, `plan_timeline.py:717-719`, `planner_board.py:365`. Launch gates were made
fail-loud by turning `user_id` into a required positional (`subjects.py:120-141`, `:146-178`).
`declined_elective_subject_ids` (`subjects.py:489-520`) exists specifically because task-derived
surfaces could not get scope from the tasks. This is careful, well-documented work — and it makes
K9's unscoped cross-exam mastery read harder to explain, not easier.

**K17 — the palette answers "placed this week", which is not "pending".** *(narrowed)*
`planner_board.py:330-360` returns candidates "minus what is already placed", where *placed* means
a `study_tasks` row inside the seven-day board window (`:378-392`, `window_dates`). A topic
mastered three months ago and a topic never opened are both rendered identically as unplaced
(`PaletteCard.jsx:20-23`). The docstring is precise about this; the UI affordance is not. The
roadmap now supplies the cross-check that did not exist — the same topic carries `not_started`,
`studied` or `mastered` on the Progress tab — but the palette itself is unchanged, so the two
surfaces still describe the same topic in incompatible terms on adjacent pages.

**K18 — two comparability scales now exist on one row, and only one is shown.** *(new)*
`exam_topic_coverage` rows carry `exam_priority_score` (raw, incomparable across `source_basis` —
`planner.py:334-337` records derived rows topping out at 36.10 against authored rows starting at
60.00), `comparable_priority` (a percentile within a `source_basis`, used for ordering and
deliberately **not** displayed, `planner_board.py:463-466`), and `predictability_band` (a percentile
within the topic's own subject-paper, `288_predictability_axis.sql:33-38`, the only one the palette
renders). `SubjectTopicTree.jsx:85` still renders the raw `exam_priority_score` as "priority N" —
so the two syllabus trees an aspirant can open show two different, non-comparable numbers for the
same topic.

## 5. Open decisions for John

Each is a single question, with only the options the code as it stands already constrains it to.
No recommendation is made. After the third re-check, decision 3 is **answered by ROADMAP-01** and
decision 9 is **settled**; 1, 2, 4, 5 and 11 are rewritten because the roadmap changed what they
turn on; the rest stand with corrected citations.

1. **What is the denominator of "my syllabus"?** *(rewritten — this is now the main open
   question.)* The code offers five and uses a different one per surface: all scoped locked
   `exam_topic_coverage` rows for the exam (`subjects.py:268`), locked high-yield rows only
   (`report_cards.py:311-312`), the current plan's scheduled tasks (`plan_timeline.py:517`), the
   palette's candidate set — scoped coverage minus this week's board (`planner_board.py:330-360`)
   — and now the roadmap's universe: scoped locked coverage **plus the macro parents of those
   rows** (`roadmap.py:8-19`). The roadmap is the first of the five an aspirant reads as a
   percentage (`pct_mastered`, `roadmap.py:408`), which makes its denominator the one that now
   matters most. The sixth — all `topics` rows under the exam's subjects, which is what an aspirant
   means by "my syllabus" — is still read only for tree *structure* (`subjects.py:399-410`) and is
   still never a denominator.
2. **Which existing cut-off is "done"?** *(rewritten.)* 50, 70, 75, or the 45/75 next-action bands
   (K4). ROADMAP-01 did not choose: it reused 75 and 50 and pinned 75 to `report_cards`
   (`roadmap_thresholds.py:7-24`), which makes the roadmap consistent with the report card and
   leaves it inconsistent with `shared_core.py:38` (70) and the next-action bands. The roadmap is
   now the most visible of the four, so picking one means deciding whether the other three move to
   it.
3. **Does completing a task count as covering its topic?** *(answered in code, not by decision.)*
   ROADMAP-01 says yes: one completed `study_tasks` row makes a microtopic `studied` and
   contributes to its macro's state (`roadmap.py:243-244,258-259`). That was shipped as a
   derivation choice, not a product ruling, and it is now what an aspirant sees.
   `completion_quality` (`034:24`) is still ignored, so a task marked done badly counts the same as
   one done well — that part is still open.
4. **Which of the *three* revision mechanisms is authoritative?** *(rewritten — a third arrived.)*
   `user_topic_mastery.next_revision_at` driven by `_REVISION_DAYS` (`mastery.py:36,224`),
   `revision_items` with its own `interval_days`/`ease`/`repetitions` (`093:7-27`), or the
   roadmap's flat `revise` = mastered and untouched for more than 14 days
   (`roadmap_thresholds.py:24`, `roadmap.py:252-255`). The third is the only one an aspirant can
   see, and it is the only one that ignores per-topic difficulty.
5. **Is `revision_due` a naming defect or a semantic one?** *(sharper now.)* (K3) The same
   repository now contains both readings of the word: `/api/study/topics` calls a topic
   "revision_due" for being well mastered (`api/study_os.py:1388`), and the roadmap calls a topic
   "revise" for being well mastered *and then left alone* (`roadmap.py:252-255`). The second is
   what the word means; the first is still what the orphaned endpoint returns.
6. **Should the `progress` average count unmeasured topics as 0, or keep reporting the measured
   subset?** (K6) Both readings are already in the UI copy at `Subjects.jsx:132`.
7. **Is the planner's cross-exam mastery fallback intended?** (K9) `shared_core.py:11-17`
   documents the opposite rule for the same data, and the elective work (K16) shows the team
   hardening scope everywhere except here.
8. **Do K1 and K2 get repaired or deleted?** *(cheaper to delete now.)* Both endpoints are still
   unreachable code (`api/study_os.py:1201-1217`), one broken against its own schema and one
   reading a table no migration creates. What they were for has since been built elsewhere and
   correctly: per-subject rollup at `roadmap.py:395-410`, per-topic score history at
   `roadmap.py:277-300`. Repairing them would produce a second answer to both questions.
9. **Does a roadmap view live in the Progress tab, or join the Plan page's tab strip?**
   *(settled — the Progress tab.)* ROADMAP-01 mounted `SyllabusRoadmap` under the existing
   `/app/study/progress` route (`StudyProgressHub.jsx:5,22`, `StudyShell.jsx:9`,
   `appRoutes.jsx:100`), so the locked no-new-surface rule was never engaged. What is left is a
   narrower question: the Plan page's "Arrange" palette (`StudyPlan.jsx:686-694`) and the Progress
   tab's roadmap now render the same topics with different vocabularies — "unplaced" against
   "not started" — and nothing says which page an aspirant is meant to start from.
10. **Is the `exam_phase_id` question closed?** *(rewritten — K10 is resolved.)* Phase duplicates
    are now collapsed by `_canonical_coverage_rows` (`planner.py:681-701`) and the read is
    paginated (`:327-354`). What remains open is whether an aspirant should see Prelims and Mains
    progress *separately*, which no surface offers.
11. **Should the palette distinguish "never studied" from "studied, not on this week's board"?**
    *(rewritten — K17 narrowed.)* The roadmap proves the distinction is derivable and renders it
    one page away (`roadmap.py:240-259`), but `planner_board.py:330-360` is unchanged: the palette
    still shows a topic mastered three months ago and a topic never opened identically. The choice
    is now whether the palette adopts the roadmap's state or whether the two surfaces stay
    deliberately different.
12. **Which priority number does an aspirant see?** *(new — K18.)* The two syllabus trees show
    different scales for the same topic: `SubjectTopicTree.jsx:85` renders raw
    `exam_priority_score`, the palette renders `predictability_band` and hides
    `comparable_priority` as "not for display" (`planner_board.py:463-466`).
