# Optionals corpus — known defects and the post-deploy repair queue

Written 2026-09-10, after loading 4,040 optional PYQ questions.
Everything here is recorded because it cannot be fixed today, or because a
future reader would otherwise mistake a deliberate state for a bug.

---

## Blocked: the deployed backend lags `main`

`PATCH /pyq-questions/{id}` and `DELETE /pyq-questions/{id}` both return **405**
on `ccp-api-demo.onrender.com`. The PATCH route exists at head
(`admin_exam_intel_cms.py:2129`); there is no DELETE route at all. Everything in
the queue below waits on a deploy.

**Do not work around this in SQL for anything that changes `question_text`.**
`normalized_question_hash` is computed by the application, not the database. A
SQL text edit leaves the stored hash describing the old text, which silently
disables `pyq_questions_paper_hash_uidx` — the index that caught every
duplicate-content defect found during this load.

### Queue

1. **History 2025 Paper-1 — 8 unlabelled map items.**
   `HIST-P1-2025-1(i)` through `1(viii)` carry the bare locational hint
   ("Neolithic site."). Every other map item in the corpus is prefixed with its
   printed item label ("(ix) Mesolithic site."). The label exists because UPSC
   can print the same hint twice — 2025 has "Mesolithic site" at both (ii) and
   (ix) — and the bare text collides on the content hash. These 8 loaded before
   the labelling fix. Prefix each with its label via PATCH.

2. **45 rows carry PDF ligatures.** `Deﬁne` rather than `Define`, from `\ufb01`
   and friends. Sociology only — Paper-1 28 rows, Paper-2 17. The corpus files
   are already fixed (both parsers now normalise `\ufb00`–`\ufb04`), so a
   re-parse is clean; only the loaded rows still carry it. Cosmetic, but it
   breaks a text search for "Define".

---

## Fixed, and worth not re-litigating

**1,455 inferred mark values removed (2026-09-10).** The loader inferred marks
from a 20/15/15 rule for non-compulsory sub-parts. An audit against all 1,059
printed values found the rule wrong 178 times — 17%. It holds for PSIR (107 of
108 parents) and Geography (14 of 14), but **Sociology is 20/20/10** (53 of 61)
and **History splits evenly** between 15/15/20 and 20/20/10. Rows in
subject-papers where the source printed no marks at all now carry
`marks_source='unknown'` with no `marks_inferred` key. The 1,230 that remain
sit in subject-papers with a corroborating printed pattern.

`marks` has always held only what the source printed. Nothing was invented; the
guess has simply been withdrawn where nothing supports it.

**Sociology 2014 Paper-II renumbered and completed.** The compiler's PDF is
corrupt from Q6 onward: it printed Q6's sub-parts as copies of Q5's, then
shifted the real Q6 into Q7 and the real Q7 into Q8, and dropped Q8 entirely.
Corrected against the IAS Gurukul 2014 Paper-II compilation:

- `7b`→`6b`, `7c`→`6c`, `8a`→`7a`, `8b`→`7b`, `8c`→`7c`
- Two artefacts (`6d`, a copy of `5d`; `7a`, a copy of `6a`) set
  `reviewer_status='rejected'` with `-VOID` appended to their refs. Kept, not
  deleted — they are the evidence the source was wrong.
- Q8(a)(b)(c) restored by POST, `marks_source='printed'` (20/20/10),
  `verified_against_official=false`.

The official 2014 paper could not be consulted: **the UPSC archive only reaches
2016.** Two independent compilations agree on the structure, which is the best
available evidence, not proof.

---

## Syllabus ingest — two defects found while fixing INGEST-FIX-01

**Every `--dry-run` count in this session's history means nothing.**
`CmsClient.find_all` returns `[]` unconditionally when `dry_run` is set
(`scripts/ingest_upsc_gs_syllabus.py`, the guard at the top of the paging
helper), so no existence check can answer "already there". Every subject,
topic, micro-theme, document and mention is therefore reported as a create,
whether the tree is empty or complete. The six dry runs performed on
2026-09-10 all reported 100% created regardless of live state, and were read
as plans. They were not plans; they are a report on the shape of the source
file. The output is now relabelled `would-create=` / `undetected=` under an
explicit "this is NOT a plan" header, so the mistake is not repeatable — but
nothing in the existing session log can be relied on retrospectively.

**Paged list reads are unstable above 200 rows, and GS is already over the
line.** `find_all` pages with `limit=200` against routes that order on a
non-unique column and slice with PostgREST `range()`:

| Route | Order clause | `admin_exam_intel_cms.py` |
|---|---|---|
| `GET /topics` | `.order("name", desc=False)` | `:3374` |
| `GET /syllabus-topic-mentions` | `.order("created_at", desc=True)` | `:4045` |
| `GET /syllabus-documents` | `.order("created_at", desc=True)` | `:880` |

With ties in the sort column the row order between two `range()` calls is not
guaranteed, so a row can be skipped at a page boundary and another returned
twice. A skipped row is a row the dedupe index never sees, and the next ingest
re-creates it.

This is live, not hypothetical — it is simply untriggered. The GS syllabus
document holds **456 `syllabus_topic_mentions`**, well past one page, and this
script bulk-inserts them inside the same second, so `created_at` ties are the
norm rather than an edge case. `load_mention_index` on GS is exposed today.
`topics` is under the line per subject for every optional loaded so far
(PSIR Paper-II is 19 macro + 93 micro = 112), so the topic index is safe for
now and unsafe on the first subject that passes 200.

`load_topic_index` now refuses to write when it reads fewer rows than the route
reports as its exact `total`, which converts this class of failure from a
silent duplicate tree into a hard stop — for topics. `load_mention_index` and
`resolve_document` carry no equivalent guard. Fixing the ordering needs a
unique tiebreaker on the routes themselves and belongs in its own change.

---

## Deliberate states, not defects

- **All 4,040 questions are `pending`.** Question review and tag review are
  separate gates; neither implies the other.
- **All 16 optional papers are `pending`** per M5 — not because they are
  aggregator-sourced, but because a coaching URL is not an anchor. They have a
  real route to `verified` once the compiler PDFs are registered as
  `document_assets`.
- **Map items are unanswerable from the corpus.** UPSC supplies the place names
  on a map sheet no compilation reproduces; the corpus holds only the locational
  hints. Flagged `requires_map_sheet` and `answerable_from_text_alone: false`.
- **Uneven year coverage.** Geography starts 2020, History 2017, PubAd 2011.
  Source limits, not load failures.
- **Four PubAd papers are incomplete in the source** (2022 P1 stops after Q5,
  2017 P1 has no Q6, 2011 P1 and P2 are short). Named in
  `extraction_meta.validation.papers_incomplete_in_source`.

---

## Two properties of the B2 model found during the load

**The content hash is unique per paper, and twelve subject-papers share one
paper row per year.** So if two different optionals ever printed identical
question text in the same year, the second would be refused. It did not happen,
but it is a real consequence of one paper row per year that was not obvious when
M1 was chosen.

**The CMS question route was always open to `descriptive`.** `_QUESTION_TYPES`
has included it throughout, and `_QUESTION_FIELDS` accepts `metadata`,
`idempotency_key`, `section_id` and `source_question_ref`. OPT-FRONTLOAD-02 was
never a blocker on this load — and the v2 importer still cannot carry the
metadata M6 and M7 require, because its `q_row` writes no `metadata` column.
Rev2's sequence puts the importer ahead of the load; that ordering is wrong.

**That route is a plain INSERT.** A unique-index conflict surfaces as an
unhandled 500, not a 409, so `idempotency_key` does not make a re-post safe. A
loader needs a pre-flight existence check; `OPT-LOAD-04_questions.ps1` does one.
