# PRED-01 — implement predictability on score snapshots and coverage

## PRIMING

Read, in this order:

1. `docs/status/2026-09-12-predictability-axis-design.md` — the design, the
   measurements behind it, and what the axis deliberately is not
2. `app/backend/app/exam_intelligence/score_snapshots.py` — where it computes
3. `app/backend/app/exam_intelligence/coverage_derivation.py` — where it
   projects
4. `workbench/analysis/predict.py` — a throwaway sandbox script that produced
   the design's figures. **Reference implementation for the arithmetic only.**
   It reads local CSVs, has no DB access, and is not to be ported.
5. `workbench/analysis/predictability.json` — its output over 1,016 topics.
   Useful as an expected-values fixture.

## WHAT THIS IS FOR

`pyq_questions.observed_difficulty` (easy/medium/hard) is **null on all 8,188
verified Mains descriptive questions**, deliberately. Difficulty is judgeable
for an MCQ — distractors, elimination steps, obscurity of the traced fact — and
meaningless for "Discuss the impact of globalisation on informal sector
workers", which has no answer key.

`planner.py` reads that field, so today it sequences Mains study on nothing.

Predictability is the axis that does mean something for a descriptive paper:
**how reliably a topic recurs**. A theme asked in 1991, 1998, 2007, 2015 and
2023 must be prepared; one asked once in 2019 need not be. It is a property of
the corpus, measurable from 8,302 questions spanning 1980-2026.

## DECISIONS, ALREADY MADE — implement, do not relitigate

**D1. New columns, not a reuse of `observed_difficulty`.** Difficulty is a
property of a *question*; predictability is a property of a *topic*. Add
`predictability` (numeric) and `predictability_band` (text, CHECK over the four
band values) to `exam_topic_score_snapshots`, and the same pair to
`exam_topic_coverage`. Leave `observed_difficulty` null.

**D2. The measure**, per topic, over the span Y where that topic's own
subject-paper has evidence — **not** a global 1980-2026 span:

```
breadth    = distinct_years_asked / Y
regularity = 1 - min(cv_of_gaps, 1.5) / 1.5     # 0 if fewer than 3 years
recency    = 1.0 if last_asked within the most recent third of Y
             0.5 if within the middle third
             0.2 otherwise

predictability = 0.65*breadth + 0.25*regularity + 0.10*recency
```

Weights follow the measured distribution, not intuition. Breadth dominates
because that is what the data separates on. Recency is small because **only 3
of 176 frequently-asked topics ever stopped being asked** — it is a guard
against a rare case, not a driver.

**Count distinct YEARS, not questions.** A paper can ask two questions on one
topic in a year; that is not two data points. This also makes the measure
robust to the corpus's two halves counting differently (see Gotchas).

**D3. Bands are percentile within the subject-paper, with an absolute floor
that can only move a topic UP.**

```
percentile < 0.10  -> near_certain
percentile < 0.35  -> likely
percentile < 0.75  -> occasional
otherwise          -> rare

then:  if band == 'rare'       and breadth >= 0.12: band = 'occasional'
       if band == 'occasional' and breadth >= 0.40: band = 'likely'
```

This is not decoration. Both halves were found the hard way:

- **Absolute thresholds alone fail.** A flat `breadth >= 0.35` cut gave
  Geography and History **zero** near-certain topics and PubAd sixteen —
  because History Paper-I spreads ~660 questions over 127 topics and cannot
  reach 35% breadth by construction. Same lesson the v2.0 `exam_priority_score`
  model learned about cohort normalisation.
- **Percentiles alone fail too.** Sociology Paper-I has 43 topics and almost
  everything recurs, so its bottom quartile still contained a topic asked in
  **12 separate years** — labelled "rare", which is plainly wrong and would be
  worse than wrong in a user-facing band.

The floor only ever promotes, so a sprawling paper like History keeps its
honest tail of genuinely rare topics.

**D4. The band is what a UI shows; the score sorts within a band.**

## PREFLIGHT — STOP gates

**G1.** Establish where the per-topic year history comes from. Predictability
needs *years a topic was asked*, which is a join from
`pyq_question_topic_tags` (primary, verified) to `pyq_questions` to
`pyq_papers.year`. Confirm that join is available inside
`compute_exam_topic_scores` without a second round trip, or say what it costs.

**G2.** State how Y is derived per subject-paper. It must be the span where
that paper has evidence, not a constant. Geography's corpus starts 1986 and
History's 1985; using 1980-2026 for both would understate every Geography
topic's breadth by a tenth.

**G3.** Confirm the two corpus halves can be counted together safely. Thematic
rows (`metadata.corpus_half='thematic'`) are one per theme-year; year-wise rows
are one per question. Counting distinct years is robust to this — confirm the
implementation actually does that and not a row count.

**G4.** Say whether `predictability` should participate in the fingerprint that
governs snapshot idempotency. It must, or a recompute after this change would
skip every topic and silently write nothing.

## STRATEGY

One PR, draft, auto-merge off. Branch: `feat/predictability-axis`.

Migration adds the four columns. `score_snapshots.py` computes the measure
beside `exam_priority_score`. `coverage_derivation.py` projects both new fields
the same way it projects the existing ones — same review gates, same lock.

**Do not touch `planner.py`.** How a plan should *use* predictability —
front-load near-certain topics or spread them, whether `rare` gets any time at
all, whether high mastery on a near-certain topic yields to low mastery on a
likely one — is a product decision that has not been made. Deriving the number
is the small half.

## OUT OF SCOPE

- `planner.py`, per above.
- `observed_difficulty`. It stays null on descriptive questions. A rubric built
  for descriptive answers may fill it one day; that rubric does not exist.
- The UI. A separate ticket once the data lands.
- Re-running the publish chain. That is an operator action.

## GOTCHAS, each already paid for

- **Recompute after this lands or nothing changes.** Existing locked snapshots
  are not overwritten; the cycle is reject-locked → recompute → lock → unlock
  coverage → derive → lock coverage. Say this in the PR body.
- **PostgREST range paging without `.order()` is undefined.** Three modules had
  this and it silently corrupted a published ranking — 812 topics with wrong
  evidence counts. Any new read must be ordered.
- **PostgREST caps a select at 1,000 rows.** There are 1,306 snapshots and
  13,168 tags. Filter server-side or page with `.range()`; do not fetch and
  filter in Python.
- `regularity` is undefined below three years. Set it to 0 and let breadth
  carry those topics, which is correct — a topic asked twice is not
  predictable regardless of spacing.

## VALIDATION

- Unit tests for the measure against `predictability.json`: pick five topics
  spanning the bands and pin their score and band.
- A test that the absolute floor promotes and never demotes.
- A test that two topics with identical year counts but different spacing get
  different `regularity` and can land in different bands.
- A test that Y is per-subject-paper, using two papers with different spans.
- Cite `path:line` for every claim about existing behaviour. BE green.

## OUTPUT

G1-G4 answers; the migration; the diff; the band distribution per subject-paper
after a dry computation; and one sentence on what an operator must run for this
to appear in published coverage.

Offline: commit locally, do not push.
