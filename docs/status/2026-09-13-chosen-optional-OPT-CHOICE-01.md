# OPT-CHOICE-01 — the chosen optional, answered

Answers the four questions in `workbench/prompts/OPT-CHOICE-01_brief.md`.
Written 2026-09-13, after the thematic load (`48cca21`) put 8,302 optional
questions and a published ranking live.

Status: **proposed dispositions, awaiting repo-owner sign-off.** The evidence
below is repo-grounded and was checked before the answers were written. Nothing
here has been implemented.

---

## What the corpus actually is, stated once

Six optionals, twelve `subjects` rows — `paper is subject` (M2, rev2). So:

- A chosen optional is **two subject ids**, never one.
- Ten of the twelve rows are noise for a given user, not eleven.
- UPSC offers ~48 optionals; six are loaded. **"My optional is not in the
  corpus" is the common case, not an edge case**, and every answer below has to
  survive it. Mathematics was attempted and retained as evidence, not corpus
  (`16224d8`).

---

## Three live regressions the optionals already caused

These are not part of the feature. They are already shipped and already wrong,
and each is fixed by the same scope rule the feature needs.

1. **Onboarding calibration now asks for 16 subjects.**
   `calibration.resolve_required_subjects` derives the required set from locked
   coverage (`study_os/calibration.py:162-262`). Optional coverage is derived
   and published, so a UPSC user's required set is GS I–IV plus twelve optional
   papers. The `required_subject_set_hash` also changed for every existing UPSC
   user, which fires the non-blocking "update your starting point" prompt
   (migration `199`) across the base.
2. **The Subject Practice Hub shows twelve optional cards.**
   `study_os/subjects.py:176-220` buckets *all* locked coverage for the target
   exam into subject cards. No filter exists.
3. **The planner ranks across all twelve.** `planner.py:1203` takes the same
   locked-coverage set as its candidate pool. A generated plan today can spend a
   PSIR aspirant's week on Anthropology Paper-II.

Also to verify live, found while tracing the above: `_load_locked_coverage`
caps at `.limit(2000)` (`planner.py:256-278`). GS is ~456 rows and twelve
optional papers add roughly 1,200–1,500. UPSC is at or near that ceiling, and
the read truncates **silently** — topics would disappear from the planner with
no error. Count `exam_topic_coverage` rows for UPSC CSE at `reviewer_status =
'locked'` before anything else ships.

---

## Q1 — Where does the choice live?

**Answer: a per-exam elective choice row, not the profile and not the plan.**

- **Profile — rejected.** `profiles.target_exam` is single-valued and
  `aspirant_preferences.target_exams[0]` is what resolution actually reads
  (`calibration.py:104-131`), so two concurrent exams are not expressible today
  anyway. But the per-exam key costs nothing: `exam_id` is already in hand at
  every read that needs the filter.
- **Study plan — rejected.** Plans regenerate; an enrolment fact must not.
  `user_study_plan_preferences` is one row per user with no `exam_id`, so it is
  the wrong shape too.
- **Per-exam — adopted.** The precedent exists: `user_exam_calibration` is
  keyed `(user_id, exam_id)` with a unique index (migration `199`), and
  `user_exam_goals` is keyed `(user_id, exam_id, exam_phase_id)` (migration
  `065`). There is no exam *enrolment* object, and this feature does not need
  one invented — it needs one more per-exam user row.

**Shape (migration 287, next free number):**

```
public.user_exam_electives
  user_id        uuid  -> profiles(id) on delete cascade
  exam_id        uuid  -> exams(id)    on delete cascade
  elective_group text                  -- 'upsc-cse-optional'
  choice_key     text                  -- 'psir' | null when undecided
  subject_ids    uuid[] not null default '{}'   -- the two paper subjects
  chosen_at      timestamptz
  unique (user_id, exam_id, elective_group)
  RLS: owner select/insert/update; no delete
```

`subject_ids` is an array because the choice is two subjects (M2). It carries no
FK — the backend validates every id against the elective sections of the exam
before writing, and an empty array is the legitimate "still choosing / my
optional is not loaded" state.

Switches append to `public.user_exam_elective_history` (same key plus
`previous_choice_key`, `changed_at`) — small, append-only, and the only thing
that makes Q2's "kept, not discarded" auditable.

## Q2 — Can it change mid-preparation, and what happens to progress?

**Answer: yes, freely. Nothing is discarded, because nothing needs to be.**

Every user signal is keyed by `topic_id`, and the old optional's topics belong
to subjects that simply fall out of scope: `user_topic_mastery`,
`user_topic_mastery_evidence`, `user_topic_self_assessment`,
`user_topic_error_patterns`, `study_tasks.topic_id`. A switch is one `UPDATE` of
`subject_ids`. No data migration, no orphan, and switching back restores the old
subject's history intact.

- **Old progress: kept and out of scope.** Not deleted, not hidden behind a
  flag — just no longer in the filtered set. This is the whole reason to answer
  Q4 structurally rather than by deleting rows.
- **Plan: regenerates.** The existing regeneration path applies
  (`study_os/regen.py`, honouring `user_study_plan_preferences.auto_regenerate`).
  Tasks for the old optional's topics are replaced; GS tasks are untouched
  because GS topics stay in scope.
- **Calibration: reuses the mechanism already built for this.** The switch
  changes the required subject set, so `required_subject_set_hash` mismatches
  and migration `199`'s **non-blocking** "update your starting point" prompt
  fires. Plan generation must not be re-gated — the user is already calibrated
  on GS.
- **Confirmation: required, and it must say what is lost.** One dialog, one
  sentence of truth: *"Your PSIR plan tasks will be replaced. Your PSIR progress
  is kept and returns if you switch back."* Anything vaguer is a lie in one
  direction or the other.

## Q3 — Do the other optionals disappear, or stay browsable?

**Answer: split by surface. Hard scope where the user studies; browsable in the
PYQ Explorer only.**

- **Study OS — hard scope, no toggle.** Plan, Subject Practice Hub, calibration,
  mastery, progress, report cards. An unchosen optional has no business in a
  plan, and a toggle there is a way to generate a wrong plan on purpose.
- **PYQ Explorer — soft default.** The chosen optional's two papers are
  pre-selected; the others stay reachable behind one explicit "browse other
  optionals" control. Choosing an optional well is a real need, the platform now
  has 1980–2026 evidence per subject to serve it, and this is the only surface
  where a not-yet-decided user is doing legitimate work.
- **Undecided is the default state, and it is safe.** With no choice recorded,
  Study OS scopes to compulsory subjects only — GS I–IV, exactly what shipped
  before the optionals loaded. That single rule also closes all three
  regressions above, which is why it should land before the picker UI does.

This is cheaper than a general soft default (one surface keeps the escape hatch,
not all of them) and still reversible.

## Q4 — Does GS stay unfiltered while optionals are filtered?

**Answer: yes — but do not write a GS rule. Mark the electives.**

"Subjects I am studying" applied uniformly gets GS wrong, as the brief says. The
asymmetry is not about GS; it is about **compulsory versus elective**, which is
a property of the exam's structure and belongs in the exam registry:

```
alter table public.exam_phase_sections
  add column selection_kind text not null default 'compulsory'
    check (selection_kind in ('compulsory','elective')),
  add column elective_group text;   -- 'upsc-cse-optional' on the 12 optional sections
```

Scope rule, one sentence: **a subject is in scope if its section is
`compulsory`, or if it is `elective` and its subject id is in the user's choice
for that elective group.** GS is unfiltered because it is compulsory, not
because it is GS. Essay, CSAT and every other exam's electives get the right
answer for free, and no code ever matches on `'-opt-'` in a slug.

Implementation chokepoint: `_load_locked_coverage` (`planner.py:256`) is
imported by `subjects.py`, `plan_by_subject.py:91`, `plan_timeline.py:704` and
`report_cards.py:310`, and its rows already carry `section_id` — so the filter
is a section-id set intersection with no extra join. Add a `user_id`-aware
wrapper rather than changing the existing signature, so admin and derivation
callers stay explicitly unscoped, following `content_studio.py:847-858` (the one
route that 422s on an unscoped read) rather than defaulting quietly.

---

## The two adjacent problems

### Subject naming

Stored `subjects.name` is `"PSIR Paper-1 (Optional)"`
(`workbench/scripts/OPT-LOAD-03_subjects_sections.ps1:79`), and the Explorer
dropdown renders `subject_name` verbatim
(`PyqExplorerSection.jsx:332-341`). Once a user has chosen PSIR, two entries
both saying "PSIR … (Optional)" is noise: the user knows it is their optional,
and they know it is optional.

Do not rename the rows — `name` is the admin identity and the load scripts, the
tagging ledgers and the CMS all use it. Add presentation metadata instead
(`subjects.metadata.elective_label = "PSIR"`, `metadata.paper_label = "Paper I"`)
and let the learner UI render "Paper I" / "Paper II" under a PSIR group header.
Frontend uses `exam`/display labels; backend keeps explicit ids — the existing
rule (CLAUDE.md, frontend governance) already covers this.

### Explorer card count — worse than the brief assumed

M1 chose B2 to hold the Explorer at 43 cards. The thematic load added **31 more
paper rows** (`48cca21`, `thematic_papers.csv`), so the card list is **~74**
(27 base + 16 year-wise + 31 thematic; confirm against the live
`/pyq-summary` response before acting).

The harder half: **choosing an optional removes zero cards.** Under B2 one
`pyq_papers` row per year carries *every* optional subject as sections
(`load_thematic.py:152,209`), so a paper card is not attributable to one
subject. `pyq-summary` filters papers only on `trust_status='verified'`
(`exam_intelligence.py:658-670`) and takes no subject argument at all. Question
filtering is unaffected — `/pyqs?subject_id=` resolves through the tag join
(`exam_intelligence.py:439-470`) and works.

Recommended fix, no schema change: collapse the 47 optional paper rows into one
"Optional PYQs" entry that opens the subject-scoped question list, taking the
card list to ~28. Per-subject paper rows are the alternative and stay rejected —
they are model A, which M1 rejected on provenance and card count.

---

## The ticket, once the four answers are signed off

1. Migration 287: `exam_phase_sections.selection_kind` + `elective_group`;
   `user_exam_electives` + `user_exam_elective_history` with RLS on both.
   Backfill `elective_group='upsc-cse-optional'`, `selection_kind='elective'`
   on the twelve optional sections.
2. Scope wrapper over `_load_locked_coverage`; wire the four Study OS callers
   plus `calibration.resolve_required_subjects`. **This alone closes the three
   regressions**, and can ship before any UI.
3. `GET`/`PUT /api/study/electives` — read and set the choice, validating
   subject ids against the exam's elective sections.
4. Explorer: default `subject_id` to the chosen papers; "browse other optionals"
   escape hatch; presentation metadata for labels.
5. Switch flow: confirmation copy, history row, plan regeneration, non-blocking
   calibration refresh.
6. Explorer card collapse for optional papers.

Prerequisites and cross-references:

- **M9-rev3's nine unscoped reads** (`OPT-SPIKE-01_concept_level.md` §4) are
  needed regardless, and become load-bearing the moment scope means something
  per user. Do them first or alongside step 2.
- Verify the `.limit(2000)` coverage ceiling before step 2, or the filter will
  be applied to an already-truncated set.

## Still open

- **Mastery roll-up across `parent_topic_id`** — unresolved since rev2 ("Open,
  and needed before the overlap worksheet is built"). It decides whether a
  switcher's GS mastery counts toward their new optional's topics. Out of scope
  here; it does not block any step above.
- Whether an aspirant may record an optional the corpus does not carry (a name
  with no `subject_ids`), so the platform can say "not yet" instead of
  pretending the choice does not exist. Recommended, and the `subject_ids`
  default of `'{}'` leaves room for it.
