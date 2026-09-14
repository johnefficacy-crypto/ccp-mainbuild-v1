# Runbook: consolidate UPSC Mains coverage onto the plannable phase (COV-PHASE-01)

Reusable for any exam whose corpus was derived against a cycle-less template
phase and must be reproduced on the cycle-attached one. Written against UPSC CSE
(`upsc-cse`), where it was first needed.

## Why

`exam_topic_coverage` is unique on `(exam_id, exam_cycle_id, exam_phase_id,
topic_id)`, so one topic may legally hold one locked row per phase. UPSC CSE
holds the Mains corpus on two phases with the same slug `mains`:

| phase | cycle | locked rows | targetable by a plan |
|---|---|---:|---|
| template | NULL | 1,497 | **no** — `exam_target_window` resolves through the cycle |
| cycle-attached | `787b0067-…` | 1,317 | yes |

Two consequences, one fixed in code and one only an operator can close:

1. **Duplicates in every exam-wide learner read** — fixed in code.
   `_canonical_coverage_rows` (`app/backend/app/study_os/planner.py`) keeps one
   row per topic, preferring the cycle-attached phase. No data change needed.
2. **180 topics exist only on the template phase** — this runbook. They are in
   the aspirant's syllabus, the palette offers them, and the planner declines to
   schedule them because they carry no row on the phase it targets. Only a
   re-derive against the cycle phase closes that.

The template phase stays canonical for **evidence** (`phase_inheritance.py`:
reads inherit, writes never). This runbook does not delete, retire, or rewrite
anything on it. Nothing here is destructive: the derivation writes `draft` rows
and can never mutate a `locked` one (PD-3/PD-4).

## Preconditions

- `ADMIN_STUDY_OS_ENABLED`, and an admin JWT with `exam_intelligence.manage`.
- `CCP_API_BASE` and `CCP_ADMIN_JWT` exported.
- The environment's exam id and both Mains phase ids, resolved by §1 of
  `workbench/sql/COV-PHASE-01_orphans.sql` — **resolve them, do not paste them
  from an older brief.** The corpus has moved phases once already.

## Steps

1. **Measure.** Run §1, §2, §2b, §3 and §4 of
   `workbench/sql/COV-PHASE-01_orphans.sql`. Record: the two phase ids, the
   orphan count (expected 180), the per-subject orphan split, how many orphans
   already hold a locked score snapshot on the cycle phase, and the topics-by-
   locked-row-count histogram.

2. **Snapshots first, if §3 says they are missing.** The derivation copies its
   numbers verbatim from a **locked** `exam_topic_score_snapshots` row for the
   target scope, and `locked_score_snapshots` does not inherit across phases — a
   topic with no locked snapshot on the cycle phase produces no coverage row
   however often the derivation runs. Evidence itself does inherit, so this
   recomputes from the template's corpus without copying it:

   ```
   POST {CCP_API_BASE}/api/admin/exam-intelligence/exams/{exam_id}/score-snapshots/compute
   {"exam_phase_id": "<cycle phase id>"}
   ```

   Then review and lock them (`PATCH /score-snapshots/{id}/review`). Locking
   snapshots is a review action, not a formality — read the ranking first.

3. **Derive coverage onto the cycle phase.**

   ```
   POST {CCP_API_BASE}/api/admin/exam-intelligence/exams/{exam_id}/coverage/derive
   {"exam_phase_id": "<cycle phase id>"}
   ```

   Expect `written` ≈ the orphan count and `updated` for rows already present.
   A 502 means an input read failed — retry; it is never a partial write. Every
   invocation is audited as `exam_topic_coverage.derive`.

4. **Review, then lock.** The new rows land as `draft` and are invisible to
   aspirants until locked. `workbench/scripts/lock_coverage.py` already pins the
   cycle-attached phase; run it without `--execute` first and read the ranking
   it prints. The History Paper-I map-item caveat in that script's docstring
   still applies.

5. **Verify.** Re-run §2 (healthy: `orphan_topics = 0`) and §6 (healthy: one
   canonical row per topic, `kind = 'cycle-attached'` for all but any genuinely
   exam-wide rows). §4's histogram will show MORE topics at two locked rows than
   before — that is expected and is not a regression: the duplicate is now
   resolved at read time, and the template rows are left in place deliberately.

6. **Spot-check the surface that reported it.** Open the planner palette as a
   learner on this exam and confirm a previously duplicated topic (e.g. "Balance
   of power: methods and contemporary relevance") appears exactly once, and that
   a topic from §2b's list can be added to the board.

## Rollback

Nothing written here is destructive. To undo step 4, PATCH the newly locked rows
back to `draft` (`PATCH /topic-coverage/{row_id}/review`) — the coverage review
endpoint accepts any target state in one call. The rows from step 3 can be left
as `draft` indefinitely; a draft row reaches no learner.

## Out of scope

Retiring the template phase's coverage rows. It would make the duplication
disappear from the table rather than from the reads, and the decision that the
template holds canonical *evidence* means its rows are not obviously disposable.
Raise it as its own gate if the duplication becomes a write-path problem.
