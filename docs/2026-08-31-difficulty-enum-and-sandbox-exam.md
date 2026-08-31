# Observed-difficulty enforcement, and what it uncovered

Date: 2026-08-31
Trigger: preparing the UPSC Prelims GS tagging programme, which captures
difficulty during the review pass.
Status: constraint applied to the live DB directly; migration file and seed fix
still to land.

---

## Summary

Adding a CHECK constraint on `pyq_questions.observed_difficulty` failed against
one existing row. Tracing that row surfaced a seed fixture that writes
unvalidated data through several tables, including two `exam_competition_metrics`
rows marked `reviewer_status = 'locked'` that no human ever reviewed.

The difficulty problem is closed. The rest is recorded here rather than fixed,
because fixing it means either defeating an immutability guard or deleting data
that turned out to have dependents.

---

## 1. The difficulty constraint

`observed_difficulty` is a bare `text` column with no DB-level check. The only
enforcement was `_OBSERVED_DIFFICULTIES = ("easy","medium","hard")` at
`admin_exam_intel_cms.py:2002`, on the PATCH route — so anything writing outside
that route (seed, backfill, psql) could store any string.

`PyqPaperWorkspace.jsx:43` offered `very_hard`, which migration 239's projection
silently rewrites to `medium` while analytics reads it as `hard`. Two live rows
carrying it were corrected in an earlier session; the dropdown has since been
fixed separately.

Distribution at time of writing:

| observed_difficulty | count |
|---|---|
| NULL | 3,219 |
| medium | 1,909 |
| hard | 31 |
| easy | 9 |
| medium_high | 1 |

Note the shape independently of the defect: of 1,949 populated rows, 1,909 are
`medium`. Only 40 rows in the whole table carry a difficulty anyone chose. This
is the bulk-default pattern the UPSC scope doc predicted, and the reason
difficulty is being captured during the tagging pass rather than after it.

Applied:

```sql
ALTER TABLE public.pyq_questions
  ADD CONSTRAINT pyq_questions_observed_difficulty_chk
  CHECK (observed_difficulty IS NULL
         OR observed_difficulty IN ('easy','medium','hard'));
```

Verified: `convalidated = true`, definition as expected.

Difficulty is now enforced at three layers — endpoint enum, review tool parse
(rejects `very_hard` by name), and the DB constraint. Only the last one is
unavoidable by a script.

---

## 2. The `medium_high` row

One row violated the constraint:

```
id          eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee3
exam        ssc-cgl-legacy-sandbox-do-not-use
created_at  2026-06-15 10:23:39.238952+00
updated_at  identical to created_at
```

Corrected to `medium`. `created_at = updated_at` means no reviewer ever touched
it — it arrived at seed time.

`medium_high` is not a `pyq_questions` value in origin. It propagated:

1. `exam_competition_metrics.metadata.legacy_difficulty_trend_unconverted.expected_difficulty`
   = `"medium_high"` (row `12121212-…-121201`)
2. `exams.default_difficulty_level` = `"medium_high"` on the sandbox exam
3. the sandbox question inherited it

Three hops, one seed run, no validated path anywhere along it.

`public.exams` constrains `cadence`, `exam_type` and `management_mode` but not
`default_difficulty_level`. `public.topics` has the same column. Both worth
reviewing — but check existing values first, since exam-level and question-level
difficulty need not share a scale.

---

## 3. The sandbox exam

```
id    22222222-2222-2222-2222-222222222222
slug  ssc-cgl-legacy-sandbox-do-not-use
name  [SANDBOX - DO NOT USE] SSC CGL
```

Contains 2 papers, 6 questions.

The real SSC CGL exam is `3742f421-eae0-4a02-8fd1-ac3aa0589c9f`, slug
`national-ssc-combined-graduate-level-cgl`, created through the registry path.
The 36-paper SSC CGL 2024 Tier I import targets that id.

So `2222…2222` is a bootstrap-era fixture that was renamed in place rather than
removed. The bootstrap seed still tries to create `ssc-cgl` at that hardcoded id
and fails on `exams_pkey`, because its `ON CONFLICT (slug)` never matches — the
id is taken under a different slug.

### Why the seed is the bug

Exam identity is DB/UI-owned after bootstrap (registry architecture, locked
2026-06-04). A seed recreating an exam at a hardcoded id contradicts that, and
the exam already exists. The fix is removing the SSC CGL block from the seed,
not re-pointing it.

Recreating it at `2222…2222` would produce a second SSC CGL exam alongside the
real one — worse than the current state.

### Why the sandbox was not deleted

Deletion cascades into `exam_competition_metrics` and hits
`_ecm_guard_published_delete()`:

```
P0409: published_row_immutable: cannot delete exam_competition_metrics
bf723882-3e44-43c5-aa94-8026d40caa71 — reviewer_status=locked (published)
```

The guard is correct and was not worked around. The difficulty defect is already
fixed, so removing the sandbox is cosmetic; it is not worth defeating an
immutability rule for.

---

## 4. Locked metrics rows that were never reviewed

Two rows in `exam_competition_metrics` carry `reviewer_status = 'locked'`. Both
belong to the sandbox exam. Both are seed fixtures.

| | bf723882-…caa71 | 12121212-…121201 |
|---|---|---|
| exam_id | 2222…2222 | 2222…2222 |
| reviewed_by | NULL | NULL |
| reviewed_at | 2026-05-03 | 2026-05-03 |
| created_at | 2026-06-15 10:23:39.238952 | 2026-06-15 10:23:39.238952 |
| is_current_published | true | true |

`reviewed_at` precedes `created_at` by six weeks and `reviewed_by` is NULL on
both. No review happened. The seed asserted `locked` as literal data, and the
immutability guard now protects rows no human approved. The metadata says as
much: `legacy_unvalidated_evidence: true`.

`bf723882` carries `legacy_split_from: 12121212-…-121201`, so these are a split
pair — parent and child, both `is_current_published: true`.

Every locked row in the system is fixture data. The lock semantics have never
been exercised by a real review.

### The pattern

This is the third instance in one session of a rule that validates content but
never validates that a decision occurred:

- **Projection** has no level check: a question tagged to a top-level topic
  passes `primary_topic_tag_count_not_one` exactly like one tagged to a
  microtopic, leaving `mock_question_bank.microtopic_id` NULL. 97 published
  questions are affected.
- **Review sweep** (`scripts/pyq_question_review.py`) built tag rows only from
  exported tags, so a question with zero tags produced no tag row and swept
  clean. Fixed by the `no_primary_tag` flag (PR #1053).
- **`_ecm_guard_published_delete()`** honours `reviewer_status = 'locked'`
  without requiring `reviewed_by IS NOT NULL`.

Each was found separately. The shared shape is worth naming once rather than
filing three unrelated tickets.

---

## Actions

Landing now, one PR:

- [ ] Migration file for `pyq_questions_observed_difficulty_chk` (applied
      directly; the migration is the record)
- [ ] Seed: remove the SSC CGL exam block
- [ ] Seed: stop `exam_competition_metrics` fixtures asserting
      `reviewer_status = 'locked'` with a NULL `reviewed_by`

Deliberately not doing:

- Deleting the sandbox exam, its 2 papers or its 6 questions — blocked by the
  published-row guard, and no longer necessary

Open, needs a decision:

- Should `_ecm_guard_published_delete()` require `reviewed_by IS NOT NULL`
  before honouring `locked`?
- Two `is_current_published` rows on one split pair — is that intended?
- `exams.default_difficulty_level` and `topics.default_difficulty_level` are
  unconstrained. Check existing values before adding anything.
- **Does any consumer surface read competition metrics by `reviewer_status`
  rather than by exam?** If so, fixture numbers (17,727 vacancies, 2.5M
  applicants, `is_current_published: true`) are live for an exam named DO NOT
  USE. This is the only item here with user-facing risk. It is a repo grep, not
  a SQL question.
