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

Type selection:

1. any wrong PYQ -> `pyq_revision`
2. concept_gap dominant -> `concept_review`
3. option_trap dominant -> `trap_review`
4. otherwise -> `practice_drill`

## Priority formula

`priority = clamp(5 - min(error_count,3) - (1 if hard-question evidence else 0), 1, 5)`

Lower number means higher urgency.
