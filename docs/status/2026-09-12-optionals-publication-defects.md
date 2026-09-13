# Optionals corpus — publication session, defects and findings (2026-09-11/12)

Appendix to `2026-09-10-optionals-corpus-defects.md` and
`2026-09-11-optionals-tagging-defects.md`. Covers the run that took the corpus
from tagged to published: provenance, the four review gates, the scoring model
rescale, and locking.

**End state.** Every Mains subject is locked and published:

| | |
|---|---|
| Optional papers | 16, `trust_status=verified`, anchored on a registered document |
| Questions | 4,038 loaded; 3,924 verified, 114 held, 2 rejected |
| Primary tags | 3,924 verified |
| Score snapshots | 1,227 locked on model v2.0 |
| Coverage rows | 1,320 locked across 16 subject-papers, 40 high-yield |

---

## Live bugs found

### `/topic-coverage` silently truncates at 1,000 rows

`admin_exam_intelligence.py:736` builds the query as
`.limit(limit + offset)` and then slices in Python. PostgREST caps a select at
1,000 rows, so any request where `limit + offset` exceeds 1,000 returns 1,000
and every page beyond is empty — **with no error and no indication in the
response**.

Mains alone now has 1,320 coverage rows, so this is live: anyone browsing
coverage in the admin UI past the first thousand sees nothing and is not told
why. The `status` filter is the workaround (drafts alone fit under the cap),
but the route needs a real fix — range-based paging rather than
limit-plus-offset-then-slice.

### The score model could not discriminate on Mains — fixed in PR #1091

`exam_priority_score` read 10.25 for a topic asked 24 times and 10.15 for one
asked 14 times. Three causes, all in `score_snapshots.py` v1.0:

- `freq_component = count / total_primary` where `total_primary` was **every
  verified primary tag on the exam** (~5,133). No Mains topic exceeds 0.5%.
- `evidence_quality = min(count/10, 1.0)` saturates at 10 questions, so every
  topic above that contributed an identical 10 points.
- `cov_component` reads human-authored locked coverage, of which the optionals
  had none — so 40 of 100 points were dead.

**`is_high_yield` required `freq_component > 0.15`, which needed 771 questions
on one topic.** It had never fired on Mains and could not.

**And the same threshold has never fired on Prelims either** — its ceiling is
0.021, seven times short. Every `is_high_yield=true` on the platform before
this came from the human-entered coverage disjunct. The threshold was dead code
on every exam in the repo.

v2.0 measures a topic against its own paper's cohort rather than the whole
exam, weighted by `1 - cohort_total/scope_total` so the term vanishes when an
exam is a single undivided cohort — which is what keeps Prelims bit-identical,
proven by a test pinned at the pre-change commit. Range on the optionals went
from 0.10 to 23.24 (1.24–24.48), with 26 of 937 high-yield.

### Snapshot compute writes duplicates on repeat calls

Twelve identical `POST .../score-snapshots/compute` calls, one a minute, wrote
**1,092 duplicate v1.0 drafts across five of them** — 247, 366, 69, 267, 143 —
while the other seven correctly reported `skipped: 1227`. 839 topics ended up
with more than one draft.

The fingerprint index exists specifically to prevent this
(`score_snapshots.py`, the `existing_fps` dict and its comment about
PostgREST row order). It is not reliable under repeat calls. Nothing reads
drafts so no harm was done, but the endpoint must not be polled and should not
be automated until this is understood.

### No retry endpoint, despite the error saying otherwise

`previous_extraction_failed` tells the operator to "use the retry endpoint".
`admin_exam_intel_documents.py` has upload-url, complete-upload, two GETs, two
link routes, archive and mixed-format. There is no retry.

---

## Document registration — what the flow actually requires

**`extract_text` has a 30-second wall-clock cap**, and a 45 MB scanned PDF
cannot meet it. The upload succeeds, the hash matches, the file is stored — and
the document lands `status='failed'` because the *extraction job* failed. That
status then blocks `link-to-pyq-paper`, which rejects `failed` and `archived`.

**`store_only` is the correct policy for a provenance document.** It is valid
for any mime type, skips extraction entirely, and lands `processed`. Nobody
needs OCR text out of a scanned coaching compilation — the Mathematics OCR
attempt in this repo is the standing evidence of what that text looks like.

The default for `application/pdf` is `extract_text`, so this must be set
explicitly at `upload-url`.

**Upload cap is 50 MB** (`LIBRARY_MAX_UPLOAD_MB`). The merged six-subject
bundle was 104.5 MB and had to be compressed to 43.2.

### Six PDFs against sixteen papers

`source_document_id` is a single column. The compiler PDFs are per-subject; the
papers are per-year, each holding twelve subjects. Neither maps onto the other.

Resolved by merging the six into one bundle and linking all sixteen papers to
it. Every optional question on every year-paper did come from that bundle, so
the link asserts something true. Per-subject attribution survives where it
belongs — in each question's `metadata` per M6.

**Linking a verified paper reverts it to pending**, so the order is link first,
promote second.

### The promotion gate accepts either anchor

`review_pyq_paper`'s docstring says `pending → verified` requires
`source_url`. **The code requires `source_url` OR `source_document_id`**
(`admin_exam_intel_cms.py`, the provenance gate), plus a valid `source_type`
and at least one question. So no coaching URL had to be asserted, and M5 is
honoured as written: the document is the anchor.

---

## Review gates — what each one actually is

Four gates, and **none of them cascades to another**:

1. **Papers** — `POST /pyq-papers/{id}/review`, `{status, reason}`
2. **Questions** — `PATCH /items/pyq_question/{id}/review`, **flat body**, not
   the `{reason, payload}` CMS envelope. Cascades to `pyq_options` only.
3. **Tags** — `PATCH /items/pyq_question_topic_tag/{id}/review`, flat body,
   `reviewer_notes` dropped server-side
4. **Snapshots** — `PATCH /score-snapshots/{id}/review`. `draft → locked` is
   **not** a legal transition; it is `draft → reviewed → locked`, two calls
   per snapshot. Coverage, by contrast, allows any target state in one call.

`reviewer_status` is not in `_QUESTION_FIELDS`, so the CMS PATCH cannot set it
— promotion goes through the separate review router at `/items/{kind}/…`.

### Snapshot and coverage lists are phase-scoped by omission

`GET /exams/{id}/score-snapshots` **with no `exam_phase_id` returns only
exam-wide rows** (`exam_phase_id IS NULL`). With 1,227 phase-scoped drafts
live, that query returned 12 and looked like an empty result. Any snapshot
query without the phase parameter is answering a different question.

---

## Findings about the data

**GS Mains coverage was published flat.** All 50 locked GS coverage rows
carried `exam_priority_score = 0.00` — derived before GS had any locked
snapshots. Any planner ranking GS topics has been ordering them arbitrarily
since those rows went live. Now corrected: 255 GS topics carry real v2.0
scores.

**History Paper-I's ranking is inflated by map items.** 180 of its 387
questions are map-identification items (20 a year, 2017–2025), tagged by hint
category. They are real questions, but a 20-item map question is not a 15-mark
essay prompt, and History P1 consequently holds 9 of the top 12 optional topics
and 9 of the 26 high-yield flags. Locked deliberately, recorded here so the
ordering is not mistaken for a pure difficulty or importance signal.

**PSIR Paper-I has 27 coverage rows with no score** — 100 scored of 127 —
while every other optional paper is complete. Not investigated.

**Coverage rows do not carry `evidence_count` through** from the snapshot; the
list route returns 0 on rows whose score is non-zero. Cosmetic unless something
downstream reads it.

---

## Operational notes

- **A pasted JWT lost its leading `e` twice in one session** — 1,389 chars
  starting `yJ`. Check `.Length` (1390) and `.Substring(0,3)` (`eyJ`) every
  time the variable is set.
- **Re-logging in invalidates the token a run is using.** Refresh before
  starting a long run, never during.
- **Supabase invalidates tokens before their `exp` claim.** A token showing
  nine minutes left 401'd on every route. Test with a cheap GET.
- **`$hdr` does not update when `$env:CCP_ADMIN_JWT` does.** Rebuild it.
- **The env vars are per-window.** A script exiting with "set CCP_API_BASE and
  CCP_ADMIN_JWT" has done nothing — do not read another terminal's success
  report as belonging to the run you just launched.
- **Render drops long POST runs.** `ReadTimeout` and `RemoteDisconnected` both
  appeared repeatedly. Every bulk script written this session asks the server
  what is already done and posts only the remainder; re-running is always safe
  and is the intended recovery.
