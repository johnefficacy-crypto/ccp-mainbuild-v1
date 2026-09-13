# Optionals corpus — defects and findings, tagging session (2026-09-11)

Appendix to `2026-09-10-optionals-corpus-defects.md`. Everything here was found
while tagging 4,038 optional questions to their primary topic.

---

## Tooling defects

### `pyq_question_review.py catalog` needs `metadata.exams`, and Mains never had it

`catalog_rows()` filters conjunctively: `level='microtopic'` **and**
`metadata.exams` intersecting the requested body key. The syllabus ingest writes
`{paper_id, official_syllabus_line, source}` and no `exams` key, so the
catalogue built empty and `apply` refused to run.

**This is not specific to the optionals.** GS-II Mains has no `exams` key
either — the convention lives on the Prelims catalogue and was never applied to
Mains. It is why the 1,209 Mains GS questions were hand-tagged through the CMS
rather than through this tool.

Fixed for the optionals by setting `exams: ["upsc"]` on all 1,069 optional
microtopics. **Mains GS still lacks it**, so the same wall is waiting for
anyone who tries to use this tool on GS. Either backfill Mains GS or teach the
ingest to write the key.

### `apply` is not resumable, and that matters on this backend

It re-POSTs every row on every run. Rows already tagged return 409 and cost a
full round-trip each, so a run interrupted at 80% spends most of the next
attempt colliding with its own work.

On the demo backend this failed to converge: Sociology Paper-II took four
passes, dropped by `ReadTimeout` and `RemoteDisconnected` each time, because
each pass re-sent hundreds of already-written rows before reaching new ones.

`workbench/scripts/apply_resume.py` was written for this. It asks the server
which questions already carry a primary tag, subtracts them, and posts only the
remainder. Tags only — no decision or difficulty handling; use the real tool for
those.

### A wrong tag still cannot be replaced by re-applying

`uq_pyq_question_one_primary_tag` is live and in no migration. Rejecting a tag
only sets `reviewer_status`; the row stays and a replacement 409s. Correcting a
tag needs delete-then-insert in SQL. Unchanged from before, restated because the
tagging pass is when it would bite.

---

## The scoring chain has four gates, and tagging satisfies none of them

`exam_priority_score` read 0.00 on all 127 PSIR Paper-I coverage rows after its
392 questions were tagged. That is correct behaviour, not a fault, and the
reason is worth recording because rev2 and rev3 both imply otherwise.

Coverage derivation does **not** read tags. `exam_priority_score` is copied
verbatim from a locked score snapshot — `coverage_derivation.py` states the
inputs are "locked snapshots + verified syllabus mentions" and that the score is
"copied verbatim from the locked snapshot — never recomputed here."

`score_snapshots.py` computes those snapshots, and requires **all three** of:

| gate | where |
|---|---|
| papers `trust_status='verified'` | `:196` |
| questions `reviewer_status='verified'` | `:222` |
| tags `reviewer_status='verified'`, primary only | `:249` |

and coverage then reads only snapshots at `reviewer_status='locked'` (`:302`).

**The first gate is held shut by our own decision.** Per M5, the optional papers
stay `pending` until the compiler PDFs are registered as `document_assets`,
because a coaching URL is not an auditable anchor. So the whole scoring axis is
blocked behind provenance work nobody has started — not behind tagging.

Full chain: **register PDFs → promote papers → verify questions → verify tags →
compute snapshot → lock snapshot → derive coverage.**

---

## What the corpus tagging showed

**Coverage isolation is now observed, not just reasoned about.** Deriving
coverage after PSIR Paper-I's mentions were verified wrote 127 new rows,
`updated: 0`, `skipped: 456` — every GS row untouched, `changed_fields` empty on
each. GS-II's coverage rows were last written 2026-08-27, two weeks before.
M8-rev3's isolation holds on `subject_id` alone, with no concept level and no
cross-subject parentage.

**Lexical matching is not good enough for this.** A trial run scoring question
text against microtopic names with IDF weighting proposed 375 of 392 PSIR
Paper-I tags, but ~10% were wrong even in its highest-confidence band — "pre-
Marxist socialist theory" to *Marxist theory of the state*, "constitutional
protection of rights" to *federalism*. A third of the paper came back as
near-ties between two topics. All 4,038 were read individually instead.

**Syllabus coverage by the exam is partial, as on GS.** Topics no question
touched in the corpus: PSIR P1 6 of 106, Anthropology P1 14 of 122, History P1
40 of 146, Geography P2 20 of 87. Sociology and Anthropology Paper-II used every
topic. This is the same shape as GS, where 134 of 444 microtopics were never
tested in thirteen years — the syllabus is broader than the paper.

**Map items carry real topical signal and should not be dumped on one topic.**
History Paper-I has 180 (20 a year, 2017–2025) and Geography Paper-II has 26.
Their hints — "A Harappan site", "Neolithic site", "Rock-cut cave site" — map
cleanly onto period and theme topics. They are tagged by hint category with a
`notes` entry recording that the tag rests on a locational hint only, since the
place names live on a map sheet no compilation reproduces.

---

## Operational notes, all of which cost time today

- **A pasted JWT can lose a character.** One run failed on every request with
  `invalid character 'È'`: the token was 1,389 chars and started `yJ`, missing
  its leading `e`. Check `.Length` (1390) and `.Substring(0,3)` (`eyJ`) after
  setting it.
- **Re-logging in invalidates the running token.** Refreshing mid-run 401s the
  run in progress. Refresh before starting, not during.
- **Supabase can invalidate a token before its `exp` claim.** A token showing
  nine minutes remaining 401'd on every route. Test with a cheap GET rather than
  trusting the countdown.
- **`export` drops `metadata`.** The worksheet carries `source_question_ref`
  but not the optional subject/paper keys, so splitting 4,038 rows into twelve
  papers is done on the ref prefix (`PSIR-P1-`, `SOCIO-P2-`, …). That prefix
  convention (M4) turned out to be load-bearing for far more than collision
  avoidance.
- **`text_preview` in the worksheet is truncated.** Match on full question text
  joined from the export by `row_id`, not on the preview.
- **Python on Windows defaults to cp1252.** Every `open()` against these files
  needs `encoding='utf-8'` explicitly; the corpus carries curly quotes
  throughout and a few non-Latin characters.
- **The env vars are per-window.** A script that exits with "set CCP_API_BASE
  and CCP_ADMIN_JWT" has done nothing — do not read a success report from
  another terminal as belonging to the run you just launched.
