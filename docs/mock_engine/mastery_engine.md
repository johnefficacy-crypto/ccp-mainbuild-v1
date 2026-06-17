# Mastery Engine (PR5a)

## Delta formula

Per-topic weighted observed accuracy is compared against expected accuracy by current mastery band:

- 0.0–0.3 => 0.40
- 0.3–0.6 => 0.60
- 0.6–0.9 => 0.75
- 0.9+ => 0.85

`raw_delta = (observed_accuracy - expected_accuracy) * weight_volume`

`weight_volume` scales from 0..1 using `min(1, total_question_weight / 5)`.

Each question weight is:

`difficulty_weight * source_weight * pyq_recency_weight * time_penalty`

- Difficulty: easy 0.5, medium 1.0, hard 1.5
- Source: pyq 1.2, authored 1.0, current_event 0.8
- PYQ recency decay for years older than 5 years: `0.95^(years_over_5)`, floor 0.5
- Time penalty: if actual time exceeds expected time, multiply by 0.95

Final `capped_delta` is clamped to ±0.15.

## Scale contract handoff to PR5 wiring

- **PR5a output unit:** mastery deltas are emitted on unit interval scale `[-1, 1]` (and currently capped at ±0.15).
- **PR5 persistence contract:** before `INSERT/UPDATE` into `user_topic_mastery.mastery_score` (0..100 column), PR5 must multiply delta by 100.
- This conversion is owned by PR5 wiring (integration contract), not by the PR5a `mastery_engine` internals.

## Error signal extraction

For every question classified as `option_trap`, `calc_error`, or `concept_gap`, emit one `ErrorPatternSignal` with:

- count=1
- evidence question id
- signal strength from confidence (clamped 0..1)

## Correction task type rules

A topic emits one draft when any is true:

- accuracy < 50% with attempted >= 3
- concept_gap + option_trap signals >= 2
- topic exists in prior error-pattern topics and is not recovered

**Category** (the 063 `mock_correction_tasks.category`) is owned by the shared,
source-neutral `study_os/correction_policy.py` (§7). Both the generated and manual
adapters call `select_categories(input)`, which:

1. normalizes + **aggregates** raw error aliases into canonical counts (collisions
   like `concept` + `concept_gap` collapse to one);
2. returns the canonical correction **set**, ordered count-desc with a stable
   tie-break — **one correction per canonical category**;
3. falls back to a single `concept_gap` only on explicit weak-topic / low-accuracy
   / unrecovered-prior-error signal; unknown-only evidence yields nothing.

The generated pipeline feeds the policy from **question-level** `error_type`
(not the narrower `error_patterns.TRACKED` write-vocab), so memory/speed/misread
evidence survives. Titles are **category-only** (`Concept drill`, …) and identical
across origins; `topic` stays a separate source-specific column. `MasteryWriter`
persists `draft.category` without re-classifying.

`task_type` is **action style only** (drives `estimated_minutes`/execution),
derived AFTER category selection and never altering the category:

- `concept_gap` -> `concept_review`
- `option_trap` -> `trap_review`
- `memory_gap` + wrong PYQ -> `pyq_revision`; otherwise -> `practice_drill`
- `careless` / `speed_issue` -> `practice_drill`

## Priority formula

`priority = clamp(5 - min(error_count,3) - (1 if hard-question evidence else 0), 1, 5)`

Lower number means higher urgency.
