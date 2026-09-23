# SSC CGL 2024 Tier I — tagging runbook and audit trail

Exam slug: `national-ssc-combined-graduate-level-cgl`. Corpus at the time this
was written: **850 questions across 13 papers, every row
`reviewer_status='pending'`, zero topic tags, nothing projected** — the largest
idle corpus on the platform.

This directory is the **audit trail**, not a scratch space. The review
endpoint does not persist `reviewer_notes` for either kind (the
`update_pyq_question_review_atomic` RPC takes no notes parameter, and the tag
update is `supports_notes=False`), so the database row carries no record of why
it was promoted. The filled and applied worksheets here are that record.
Commit them.

## Standing constraints

- **General Awareness is excluded at import by a standing architecture lock.**
  Do not re-add it. The 35 `general-awareness` rows in `mock_question_bank` are
  authored mocks and are unrelated to this corpus.
- **Reuse the shared catalogues; do not create SSC-specific copies.** The three
  subjects — `quantitative-aptitude`, `general-intelligence-reasoning`,
  `english-language` — are shared with RBI Phase I, CSAT and the regulators and
  are **body-agnostic**: their rows carry no `topics.metadata.exams` key. That
  is why the catalogue is built by `--subject-id` and the proposer is run with
  `--any-body`; applying a body filter to them empties every candidate set and
  records the whole corpus UNMAPPED.
- **One primary tag per question** (`uq_pyq_question_one_primary_tag`), and the
  CMS create route cannot replace one. Leave `assign_topic_id` blank unless the
  tag would actually change — the tooling now enforces this offline rather than
  discovering it as a 409.
- **Difficulty rubric (locked, QRE) is STEP COUNT**, not perceived hardness:
  `easy` = a single formula or rule, one step; `medium` = two to three steps, a
  standard pattern; `hard` = multi-step, a non-obvious setup or an unusual
  pattern.

## 0. Credentials and scope

```bash
export CCP_API_BASE=https://<host>
export CCP_ADMIN_JWT=<admin/super_admin JWT>
```

Resolve the exam id and the Tier I phase id from the slug, then keep both for
every command below. Everything after step 1 is offline.

## 1. Export (read-only)

```bash
python scripts/pyq_question_review.py export \
    --exam-id <ssc-cgl-exam-id> \
    --exam-phase-id <tier-1-phase-id> \
    --status all \
    --out review_out_ssc --apply
```

`--status all` matters for this corpus: `current_primary_topic_id` and the
`no_primary_tag` flag are computed from the exported tag set, and a
pending-only export would describe the backlog rather than the corpus. The run
writes `questions_export.json`, `tags_export.json`, `stimuli_export.json`,
`options_export.json` and `papers_export.json`.

## 2. Catalogue (read-only; `--apply` writes the file)

```bash
python scripts/pyq_question_review.py catalog \
    --any-body \
    --subject-id <quantitative-aptitude-subject-id> \
    --subject-id <general-intelligence-reasoning-subject-id> \
    --subject-id <english-language-subject-id> \
    --is-active \
    --out topic_catalog_ssc.json --apply
```

`--any-body` drops the `metadata.exams` filter, which these rows do not carry,
and makes `--subject-id` required so the catalogue is still narrowed by
something. The file is **microtopic rows only** — `catalog` emits leaves, and a
row stating any other level aborts every tool that reads the file, so a
topic-level id typed into a worksheet is rejected as not in the catalogue
before any network call.

The file is a JSON **list**, and it carries both shapes: `name` / `subject`
(the slug) / `metadata.exams` for `propose_pyq_topic_tags.py`, and `text` /
`subject_id` / `exams` for `load_topic_catalog`, which `apply` uses at the end.
Step 4 reads it directly — there is no conversion step between them.

The subject slug comes from a second read of `{CMS}/subjects`; `{CMS}/topics`
returns only `subject_id`. If a subject id cannot be named, `catalog` warns and
the proposer refuses those rows rather than handing back an empty candidate
set.

Hand-writing the file is also fine as
`[{"id": ..., "text": ..., "level": "microtopic"}]`, under the same rule.

## 3. P1 — readiness report, BEFORE any generation

```bash
python scripts/ssc_cgl_readiness.py \
    --questions review_out_ssc/questions_export.json \
    --papers    review_out_ssc/papers_export.json \
    --options   review_out_ssc/options_export.json \
    --topic-catalog topic_catalog_ssc.json \
    --sample-size 100 \
    --out-md  workbench/audit/ssc_cgl_readiness.md \
    --out-csv workbench/audit/ssc_cgl_readiness.csv \
    --out-fit-csv workbench/audit/ssc_cgl/catalogue_fit_sample.csv \
    --apply
```

Without `--apply` the run prints the whole report and writes nothing. Without
`--options` the missing-options and missing-answer-key counters report **not
computed**, never zero.

The report also answers **P4** (projection readiness) from
`papers_export.json`: which of the 13 papers pass `review_pyq_paper`'s
provenance gate and, per blocked paper, the field that blocks it. Check (c) of
that gate reads `document_assets` and is **not** evaluated offline — the report
names every paper whose document check it could not run.

## 4. P2 — tag and difficulty proposals

Proposals only. This step never writes a tag.

**Run one paper first.** 850 questions is the whole corpus; `--papers` (and
`--limit`) exist so a mistake in the alias map costs one paper's worth of calls
instead of thirteen.

```bash
# pilot: one paper, reviewed by hand before the rest is spent
python scripts/propose_pyq_topic_tags.py \
    --questions review_out_ssc/questions_export.json \
    --options-export review_out_ssc/options_export.json \
    --catalogue topic_catalog_ssc.json \
    --alias-map workbench/audit/ssc_cgl/ssc_section_aliases.json \
    --subject-field section \
    --any-body \
    --papers <one-paper-id> \
    --batch-size 10 \
    --live --model claude-opus-5 \
    --report \
    --out-jsonl workbench/audit/ssc_cgl/proposals-pilot.jsonl \
    --out-sql   workbench/audit/ssc_cgl/proposals-pilot.sql \
    --out-worksheet-dir workbench/audit/ssc_cgl/worksheets

# then the rest, same command without --papers
python scripts/propose_pyq_topic_tags.py \
    --questions review_out_ssc/questions_export.json \
    --options-export review_out_ssc/options_export.json \
    --catalogue topic_catalog_ssc.json \
    --alias-map workbench/audit/ssc_cgl/ssc_section_aliases.json \
    --subject-field section \
    --any-body \
    --batch-size 10 \
    --live --model claude-opus-5 \
    --report \
    --out-jsonl workbench/audit/ssc_cgl/proposals.jsonl \
    --out-sql   workbench/audit/ssc_cgl/proposals.sql \
    --out-worksheet-dir workbench/audit/ssc_cgl/worksheets
```

`--catalogue` is the file step 2 wrote — the same path, a JSON list, no
conversion. `--report` prints `N mapped, N unmapped, N with no candidates` to
stderr; **`with no candidates` above zero means the subject did not resolve**,
not that the catalogue is thin. Stop and check the alias map before spending
the rest.

`workbench/audit/ssc_cgl/ssc_section_aliases.json` is committed. It maps the
printed section label to the catalogue subject slug, and also maps the three
subject ids, so a catalogue exported before the slug was written still
resolves:

```json
{
  "General Intelligence and Reasoning": "general-intelligence-reasoning",
  "Quantitative Aptitude": "quantitative-aptitude",
  "English Comprehension": "english-language",

  "55555555-5555-5555-5555-555555555551": "quantitative-aptitude",
  "55555555-5555-5555-5555-555555555552": "english-language",
  "55555555-5555-5555-5555-555555555553": "general-intelligence-reasoning"
}
```

Every proposed slug is validated against that question's own candidate list, so
a slug outside the catalogue aborts the run rather than reaching a worksheet.
`--out-sql` writes a file; it executes nothing.

One worksheet per paper lands in `worksheets/`, with `decision` **blank** in
every row, `difficulty` carrying the proposal, and `assign_topic_id` carrying
it only where the tag would actually change (`tag_unchanged` /
`tag_conflict` / `unmapped` rows leave the cell blank and say why in `flags`).

## 5. Review

A human opens each per-paper worksheet and types `decision`
(`verified` | `rejected` | `needs_correction`) on the rows they are signing,
correcting `assign_topic_id` and `difficulty` where the proposal is wrong.
Rows left with a blank decision stay pending.

## 6. P3 — apply (dry run by default)

```bash
# dry run — reports the plan per paper, sends nothing
python scripts/pyq_question_review.py apply \
    --worksheet workbench/audit/ssc_cgl/worksheets/worksheet-<paper-id>.csv \
    --exam-id <ssc-cgl-exam-id> \
    --topic-catalog topic_catalog_ssc.json \
    --require-decision

# then, to write:
python scripts/pyq_question_review.py apply \
    --worksheet workbench/audit/ssc_cgl/worksheets/worksheet-<paper-id>.csv \
    --exam-id <ssc-cgl-exam-id> \
    --topic-catalog topic_catalog_ssc.json \
    --require-decision \
    --applied-out workbench/audit/ssc_cgl/applied/worksheet-<paper-id>.applied.csv \
    --live --confirm
```

**`--require-decision` is not optional on these sheets.** They arrive
pre-filled with a model's proposals; without the flag, applying one writes
every proposal with nobody having reviewed a row.

The run reports `verified` / `needs_correction` / `rejected` / `skipped` per
paper, plus `tagged` / `tag_unchanged` / `tag_conflict` / `difficulty` /
`failed`. `--applied-out` writes the worksheet back into `applied/` with
`apply_result` and `apply_detail` per row. Commit that file — it is the audit
trail the database does not keep.
