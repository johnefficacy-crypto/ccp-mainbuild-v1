# Evidence-derived coverage: where the generator lives, and how to re-run it

Written 2026-09-24, answering: what wrote the 3,988 `exam_topic_coverage` rows with
`source_basis='evidence_derived'`, how does it compute `coverage_depth` and
`exam_priority_score`, and how is RBI Grade B's coverage regenerated now that its
projections have grown from 431 to 882 questions across seven newly verified subjects.

Nothing in this document was inferred from the shape of the data. Every formula
below is quoted from the module that computes it, with a file and line to check.

---

## 1. The generator

**There is no script and no migration.** The generator is two backend modules,
reachable only through two admin routes. That is why the 86 RBI rows all carry a
timestamp inside a 3-second window: one HTTP request wrote them in a loop.

| stage | module | route |
| --- | --- | --- |
| 1. score | `app/backend/app/exam_intelligence/score_snapshots.py` → `compute_exam_topic_scores` | `POST /admin/exam-intelligence/exams/{exam_id}/score-snapshots/compute` |
| 3. project | `app/backend/app/exam_intelligence/coverage_derivation.py` → `derive_topic_coverage` | `POST /admin/exam-intelligence/exams/{exam_id}/coverage/derive` |

Contract documents: `docs/status/J3-Evidence-Coverage-Scoring-Gate-2026-07-02.md`
(Sections B/C/E) and `docs/status/J3-OD-Resolutions-Locked-2026-07-02.md` §5
(OD-1…OD-6). Migration `217_evidence_derived_coverage.sql` adds the
`source_basis='evidence_derived'` vocabulary and the scope-unique index; it writes
no rows.

### The chain has four steps and two of them are human

```
1. compute  ──>  DRAFT exam_topic_score_snapshots       (route, code)
2. review   ──>  ... -> locked                          (HUMAN)
                 PATCH /admin/exam-intelligence/score-snapshots/{id}/review
3. derive   ──>  DRAFT exam_topic_coverage              (route, code)
                 reads ONLY locked snapshots (PD-1)
4. review   ──>  draft -> pending_review -> reviewed -> locked   (HUMAN)
                 PATCH /admin/exam-intelligence/topic-coverage/{id}/review
```

`derive_topic_coverage` writes `reviewer_status='draft'` and nothing else (PD-3),
and never mutates a reviewed, locked or human-authored row in any status (PD-4 /
§5.2 conflict matrix). So the 86 locked RBI rows are the product of a derive run
**plus** a human walking each row to `locked`.

**Only step 4 makes a microtopic practisable.** `app/backend/app/study_os/pyq_practice.py`
selects from `mock_question_bank` against locked coverage ids, at one level
(`_row_level_id`: `microtopic_id` when the row has one, else `topic_id` — a parent
lock has never served its children's questions). This is the direct cause of the
reported symptom: 154 microtopics carry projected RBI questions and no locked
coverage row, so topic mode cannot reach any of them.

## 2. How `coverage_depth` is computed

`coverage_derivation.bucket_coverage_depth(evidence_count, syllabus_mentions, is_high_yield)`
— a total function, resolutions §5.1 / OD-2:

| condition | bucket |
| --- | --- |
| `evidence_count = 0` and `syllabus_mentions = 0` | *(no row written)* |
| `evidence_count = 0`, `syllabus_mentions ≥ 1` | `mentioned` |
| `evidence_count` 1–2 | `light` |
| `evidence_count` 3–5 | `normal` |
| `evidence_count` 6–9 | `deep` |
| `evidence_count ≥ 10` and `syllabus_mentions ≥ 1` and `is_high_yield` | `core` |
| `evidence_count ≥ 10` otherwise | `deep` (fallback) |

`evidence_count` comes from the locked snapshot. `syllabus_mentions` is the count of
**verified** `syllabus_topic_mentions` rows for the topic.

### What `evidence_count` actually counts — and what it does not

`score_snapshots.compute_exam_topic_scores` builds it from:

- `pyq_papers` where `exam_id = <exam>` and `trust_status = 'verified'`;
- `pyq_questions` on those papers with `reviewer_status = 'verified'`;
- `pyq_question_topic_tags` with `tag_role='primary'` and `reviewer_status='verified'`.

**It is not `mock_question_bank`.** The projected bank is downstream of the same
verified tags, so the two move together, but they are not equal: the bank excludes
expired rows (`valid_until`) and non-verified rows, and migration 270 splits a
re-synced row's level across `topic_id`/`microtopic_id`. The brief asks to
regenerate "from current projected question counts"; the governed pipeline scores
from the verified tags those projections were built from, which is the same
evidence one step earlier and the only input the gate permits (PD-1). The runner
prints both numbers side by side (`--compare-bank`) so a divergence is visible
instead of assumed away, and the bank count feeds no score, bucket or lock
decision — there is a test asserting the proposal is byte-identical with and
without a populated bank.

## 3. How `exam_priority_score` is computed

`score_snapshots.compute_exam_topic_scores`, §8 "Score each topic". Not recomputed
anywhere downstream: `coverage_derivation._proposed_row` copies it verbatim from the
locked snapshot (PD-6, "single source of evidence numbers").

```
freq_component   = topic_count / max(cohort_total, 1)
cohort_mean      = cohort_total / cohort_topics
cohort_lift      = topic_count / cohort_mean
prominence       = min(cohort_lift / 10.0, 1.0)          # _LIFT_FULL_MARKS = 10
weight           = _cohort_weight(cohort_total, total_primary)
frequency_term   = freq_component * 50 * (1 - weight) + prominence * 50 * weight
cov_component    = (prior LOCKED coverage exam_priority_score) / 100
evidence_quality = min(topic_count / 10.0, 1.0)

exam_priority_score = round(frequency_term + cov_component * 40
                            + evidence_quality * 10, 2)
```

so the score is out of 100: up to 50 for how often the topic is asked, up to 40
carried from an existing locked coverage score, up to 10 for evidence volume.

Two derived flags ride along:

```
is_high_yield    = prior locked coverage is_high_yield
                   OR freq_component > 0.15
                   OR (weight > 0 AND cohort_lift >= 3.0)   # _HIGH_YIELD_LIFT
confidence_score = round(min(0.3 + evidence_quality * 0.7, 1.0), 3)
```

`predictability` / `predictability_band` are a **separate axis** and deliberately
not a term in the priority score — importance and recurrence are different claims.
A topic with no year evidence gets `NULL`, not a fabricated band.

### Reading the reported values back

The scores quoted in the brief — 11.41, 3.28, 2.19 — are all far below the 100
ceiling, which is what a low-evidence topic looks like under this formula: with
`evidence_count` in the low single digits, `evidence_quality * 10` contributes 1–3
points and `freq_component` a fraction of one percent of its cohort.

**This document deliberately does not decompose those three numbers.** Doing so
would need the cohort each topic fell into, and no live read was performed here.
Two things make a guess actively misleading rather than merely imprecise:

- RBI Grade B examines subject-specific papers (ESI, FM, GA), so its cohorts
  genuinely partition the corpus and `_cohort_weight` is **non-zero** — the
  cohort-prominence term is live, and a decomposition that assumed the
  single-cohort case (`weight = 0`, where the formula reduces to v1.0's exam-wide
  share) would attribute the score to the wrong axis.
- `cov_component` carries up to 40 points from a topic's *prior locked coverage*
  score, so a re-run over a topic that already has locked coverage is not
  comparable with a first run over one that does not.

The authoritative breakdown for any row is its own `score_components`, which
`compute_exam_topic_scores` records beside the score for exactly this reason —
`frequency_component`, `coverage_component`, `evidence_quality`, `cohort_lift`,
`cohort_prominence`, `cohort_weight`, and the three predictability terms.
`--explain` prints them and restates the arithmetic so an operator can check that
it adds up, without re-deriving anything.

## 4. Regenerating RBI coverage

`scripts/regenerate_exam_coverage.py` — **dry run by default**. It wraps the two
functions above and computes nothing itself.

```bash
export NEXT_PUBLIC_SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=...

# 1. What would change, nothing written.
python scripts/regenerate_exam_coverage.py --exam rbi

# 2. The forward-looking answer: coverage once the fresh drafts are locked,
#    with each score's derivation printed.
python scripts/regenerate_exam_coverage.py --exam rbi --assume-locked --explain

# 3. Verified-tag evidence beside the projected bank count, and the reach gap.
python scripts/regenerate_exam_coverage.py --exam rbi --assume-locked --compare-bank

# 4. Write the draft rows (steps 1 and 3 above). Both review gates stay open.
python scripts/regenerate_exam_coverage.py --exam rbi --live

# 5. Machine-readable, for an operator-validation evidence record.
python scripts/regenerate_exam_coverage.py --exam rbi --assume-locked --json
```

### Why `--assume-locked` exists

Step 2 sits in the middle of the chain, so a snapshot draft this run computes is
invisible to `derive_topic_coverage` until a human locks it. A plain dry run of
step 3 therefore answers "what would derive do with what is locked **today**",
which for the seven newly verified subjects is "nothing". `--assume-locked` feeds
step 1's proposed drafts into step 3's projection and answers the question being
asked — which topics gain coverage, at what depth, with what priority — using the
same `bucket_coverage_depth` and `_proposed_row` functions, so no formula is
duplicated.

It is dry-run only. `derive_topic_coverage` raises `CoverageDerivationError` if a
snapshot override is supplied with `dry_run=False`, because deriving coverage from
unlocked snapshots is exactly what PD-1 forbids. The script refuses the flag
combination too, so the refusal does not depend on one layer.

### Idempotency

Both stages are fingerprint-guarded and were already idempotent; the runner adds
nothing here and relies on it:

- **Step 1** skips a topic whose existing draft already carries the current
  fingerprint (SHA-256 over the topic's evidence tuple + `MODEL_VERSION`).
- **Step 3** fingerprints `(snapshot_id, snapshot's own input fingerprint,
  syllabus_mentions, DERIVATION_VERSION)` and CAS-updates a derivation-owned
  draft only when the fingerprint it read is still there.

So a second `--live` run over unchanged evidence writes nothing and reports
everything as skipped.

### What the operator still has to do

1. Run the dry run and read it. A topic listed as **STILL unreachable** has
   projected questions and no proposed coverage row — that is a missing verified
   primary tag, not a coverage problem, and no amount of re-deriving will fix it.
2. `--live`.
3. Lock the snapshots (step 2). Bulk review is a reviewer's call, not this
   script's.
4. `--live` again, now that the snapshots are locked, to write the coverage drafts
   the projection predicted.
5. Lock the coverage rows (step 4). Only now is topic-mode practice reachable.
6. Record the run in `docs/operator-validation/registry.json` as
   `validation_pending` until step 5 is verified on the deployed path. Code
   completion is not operator validation.

## 5. What this does not do

- **It never locks anything.** A script that locked its own output would be an AI
  job writing into locked coverage, which the J3 gate forbids in as many words
  ("do not write directly into locked exam_topic_coverage from an AI job"). Both
  gates stay with a human.
- **It proposes no score of its own.** If the numbers look wrong, the formula in
  §3 is wrong, and that is a change to `score_snapshots.py` with a
  `MODEL_VERSION` bump — not something to patch around in a runner.
- **It does not read `mock_question_bank` for anything but the comparison
  column.**
- **No live writes were made while writing this.** Every figure quoted from the
  live database (3,988 rows, 86 RBI rows, 431 → 882 questions, 154 uncovered
  microtopics) came from the brief, not from a read performed here.
