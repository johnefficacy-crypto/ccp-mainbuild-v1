# OPT-SPIKE-01 — prove the `concept` level before twelve topic trees rest on it

## PRIMING

Read `docs/status/2026-09-09-mains-optionals-strategy-rev2.md`, sections
"Isolation from GS" and "M8 has no live precedent".

M8 states that an optional question is never tagged to a topic owned by a GS
subject; it resolves instead to a `concept` row owned by the optional paper's
own subject, parented to the GS microtopic. Sharing is expressed by parentage,
never by two subjects tagging the same `topic_id`.

**M8 rests on a mechanism nobody has run.** Live: `concept` is a legal value in
`_TOPIC_LEVELS`, but every UPSC subject reports `concepts: 0`, and a probe for
concept rows parented to another subject's microtopic returned nothing. Migration
270's projection was written for a two-level tree.

This spike proves or disproves M8 on one row before twelve optional topic trees
are built on it.

Already created and available:

- Twelve optional subjects, `upsc-cse-mains-opt-<name>-p1|-p2`,
  `subject_group='upsc-optional'`. Ids in
  `workbench/ledgers/OPT-LOAD-03_subjects_sections.csv`.
- Sixteen optional year-papers, ids in
  `workbench/ledgers/OPT-LOAD-02_optional_year_papers.csv`.
- GS-II subject `upsc-cse-mains-gs2`: 5 topics, 89 microtopics.
- **All twelve optional subjects now carry their syllabus spine** — 1,252 topics
  and 1,252 mentions, ingested 2026-09-10, every row `pending`. PSIR Paper-I
  holds 21 topics and 106 microtopics. The spike therefore runs against a
  populated tree, not an empty one: its concept row is the 1,253rd, and cleanup
  must delete ONLY that row. Do not truncate or bulk-delete anything under an
  optional subject.
- 4,037 optional PYQ questions are loaded and `pending`. None are tagged. The
  spike must not tag any of them.

---

## PREFLIGHT — STOP gates

**G1.** Confirm `concept` is accepted by the topics CMS route and by any DB check
constraint on `topics.level`. Cite `path:line`.

**G2.** Read migration 270 (`270_pyq_projection_microtopic_fidelity.sql`) and
state what its level resolution does when a tag points at a row whose parent is
itself a microtopic — i.e. at concept depth. It writes microtopic to
`microtopic_id` and the parent to `topic_id` for a two-level tree; say what it
writes for three. If it cannot be determined by reading, say so and mark it for
the runtime check in step 4.

**G3.** Confirm the coverage unique index is
`exam_topic_coverage(exam_id, exam_cycle_id, exam_phase_id, topic_id)` with
`section_id` absent from the key. This is the reason M8 exists; if it has
changed, stop and report.

---

## SINGLE FORCED STRATEGY

A spike, not a feature. One concept row, four checks, one report. No production
data is modified beyond the single spike row, which is removed at the end.

Branch: `spike/opt-concept-level`
Report: `workbench/investigations/OPT-SPIKE-01_concept_level.md`

### 1. Create one concept row

Pick one GS-II microtopic whose subject matter PSIR Paper-I genuinely covers —
Federalism is the motivating example in revision 1. Create a single `topics` row:

- `subject_id` = `upsc-cse-mains-opt-psir-p1`
- `parent_topic_id` = the GS-II microtopic
- `level` = `concept`
- `metadata.spike = 'OPT-SPIKE-01'` so it is findable and removable

Record the id. Note that this row's subject and its parent's subject differ —
that is the whole point, and the first thing to confirm is that the write is
even allowed.

### 2. Does a GS-scoped read leak it?

Run the reads an aspirant's GS-II view actually issues. Report for each whether
the concept row appears:

- topic tree scoped by `subject_id = upsc-cse-mains-gs2`
- a read scoped by `level='microtopic'`
- a read that resolves by `topic_id` alone, with no subject scope

The third is expected to leak — M9 exists precisely because of it. Confirm it
does, and name every call site in the codebase that reads topics without a
subject scope. That list is the M9 work item.

### 3. Coverage derivation

Derive coverage for the exam and report whether `exam_topic_coverage` gains a
row for the concept, distinct from the parent microtopic's row. Then state
plainly whether the parent's `coverage_depth`, `exam_priority_score` or
`is_high_yield` changed. If the parent's row was overwritten, M8 has failed at
its primary purpose and the report must say so in its first line.

### 4. Projection at concept depth

Answer G2 empirically. Project or preview one question tagged to the concept row
and report what lands in `topic_id` and `microtopic_id`. State whether the
result is sane for a three-level tree or whether migration 270 needs a
follow-up. Descriptive questions do not reach `mock_question_bank`, so use an
existing MCQ if a live projection is needed, and say which you used.

### 5. Mastery across `parent_topic_id`

The open question M8 leaves. Determine, by reading and then by test if reading
is inconclusive, whether mastery on the parent GS microtopic has any effect on
the child concept — up, down, or neither. This decides whether revision 1's
motivating example survives M8 at all. A one-sentence answer with evidence is
what is needed, not a design.

### 6. Clean up

Delete the spike row and confirm it is gone. Report anything that could not be
deleted and why.

---

## BLAST RADIUS

One `topics` row, created and deleted within this spike. No schema change, no
migration, no code change. If `git status` shows anything other than the report
at the end, revert it.

## OUT OF SCOPE

- Building any optional topic tree
- Tagging any question
- Fixing anything found — this spike reports, it does not repair
- Changing migration 270

## VALIDATION

Every claim cites `path:line` or the SQL that produced it. Where the answer
needs live data you cannot reach, mark it `REQUIRES OPERATOR VERIFICATION` and
give the exact SQL. The operator runs PowerShell 5.1; see `POWERSHELL-SOP.md`.

## OUTPUT / PUBLICATION

Report structure:

1. Verdict on M8 in one sentence: does the concept level isolate GS from the
   optionals, yes or no
2. G1–G3 answers
3. Findings 1–6 with evidence
4. The M9 work item: every topic read lacking a subject scope
5. The mastery answer, and what it costs if the answer is "neither"

You are offline: no GitHub egress, no `gh` CLI, no push. Commit the report
locally and stop. The operator pushes.
