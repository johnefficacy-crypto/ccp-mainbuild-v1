# NABARD QRE gap re-tag — 24 questions

`nabard-qre-gap-retag.csv` moves 24 already-tagged NABARD questions off the
defensible-but-wrong microtopics they landed on and onto the four leaves
migration `277_qre_microtopic_gaps.sql` adds.

| new microtopic | n | moved off |
|---|---|---|
| Word-substitution message coding | 9 | Letter-to-symbol coding (9) |
| Data sufficiency with numbered statements | 6 | Floor puzzle (2), Box and stack puzzle (1), Family tree puzzle with generations (1), Comparison and ordering by attribute (1), Category and attribute matching puzzle (1) |
| Sentence completion with a missing part | 5 | Sentence-level correctness selection (5) |
| Correct and incorrect usage of a word | 4 | Single-word contextual fit (4) |

## The old tag has to go first

`pyq_question_topic_tags` is `unique (question_id, topic_id, tag_role)`
(migration 032, line 107). The old and new topic ids differ, so **nothing at
the database level stops both from existing as `tag_role='primary'`** — the
apply below will happily create a second primary tag and return no conflict.

The constraint that does bite is downstream. `pyq_mock_projection._eligible()`
requires *exactly one* **verified** primary tag:

```python
if len(verified_primary) != 1:
    return False, f"not_exactly_one_verified_primary_tag:{len(verified_primary)}"
```

Both tags are `pending` today, so stacking them breaks nothing immediately —
but the first reviewer who verifies both drops the question out of the mock
pool with no obvious cause.

**Delete the old tag.** It was never reviewed; it is a mistake, not history.

```
DELETE /api/admin/exam-intelligence-cms/pyq-question-topic-tags/{tag_id}
```

Verifying the new tag and rejecting the old one also satisfies the projection
(`rejected` is not counted), and is the right move if you want the wrong
mapping on the record. It leaves 24 rejected rows behind. Either is safe;
do not leave two pending primaries and verify both.

`pyq_question_review.py apply` only ever CREATES tags — it has no delete path —
so the removal is a separate step whichever route you take.

## Order of operations

1. Run migration 277.
2. Delete (or reject) the 24 existing primary tags.
3. Re-pull the catalogue from live — that is the authoritative check that 277
   inserted all four rows:

   ```
   python scripts/pyq_question_review.py catalog --body nabard `
       --out workbench/catalogs/topic_catalog_nabard.json --apply
   ```

   `workbench/catalogs/topic_catalog_nabard_277.json` is the same 469-row
   catalogue with the four new leaves appended by hand, for a dry run before
   the migration lands. It is a convenience file, not a source of truth.

4. Dry-run, then apply:

   ```
   python scripts/pyq_question_review.py apply --worksheet workbench\nabard-qre-gap-retag.csv `
       --topic-catalog workbench\catalogs\topic_catalog_nabard.json
   ```

   Expect `24 actionable of 24 rows`. Add `--apply --confirm` to write.

`decision`, `notes` and `difficulty` are blank on every row, so apply creates
the primary tag and touches nothing else. Tags land `pending` — the route
forces it.
