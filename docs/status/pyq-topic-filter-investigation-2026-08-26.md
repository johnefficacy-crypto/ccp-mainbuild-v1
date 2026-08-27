# PYQ Explorer Topic-Filter Investigation — 2026-08-26

> **Investigation-only findings record.** No code was changed by this task.
> Two separate Topic-filter defects in the aspirant PYQ Explorer
> (`PyqExplorerSection.jsx`, rendered under `#pyq-explorer`) are diagnosed
> below with `file:line` citations. Fixes are described but deliberately **not
> implemented** — a separate implementation prompt follows. The two symptoms
> have **independent root causes** (see §3).

All line numbers are against `main @ 0a3dfc3` (post-#1020).

---

## Symptom 1 — dropdown options are full micro-theme paragraphs

**Status: root cause CONFIRMED from code (no live check needed).**

### What the label actually is
The Topic `<select>` option label is `topics.name`, verbatim:

- Frontend builds the option list from `/pyqs` rows, keying the visible label off
  `q.topic_names[i]`: `PyqExplorerSection.jsx:210-219` (`name = names[i]`, `:216`)
  → stored as `{ id, name, subject_id }` (`:216`).
- The `<FilterSelect>` maps each option to `{ value: t.id, label: t.name }`:
  `PyqExplorerSection.jsx:343`, rendered at `:408`.
- `topic_names` is populated backend-side straight from `topics.name`:
  `exam_intelligence.py:476` (`.select("id, name, subject_id")`) and
  `:504-507` (`topic_names = [topic_meta[tid]["name"] …]`), returned at `:533`.

### Why `topics.name` is a long paragraph
The GS1-4 micro-themes were ingested by `scripts/ingest_upsc_gs_syllabus.py`,
which stores **each micro-theme's full prose string as `topics.name`** (truncated
only at 300 chars):

- micro-theme rows: `ingest_upsc_gs_syllabus.py:369-385` — `name=theme`
  (`:379`), inserted as `name[:300]` (`:187`), `level="microtopic"`,
  `parent_topic_id` = the macro topic (`:381`).
- The source strings are the long `syllabus_nodes[].micro_themes[]` entries in
  `docs/reference/syllabus/upsc_cse_mains_gs_micro_themes_v2026.3.json`
  (100-300+ chars each). Today's verified tags point at exactly these
  microtopic rows.

### Is a shorter label available? (wrong-field-used vs no-label-exists)
**This is a hybrid, and the distinction matters for the fix:**

- A short **group** label DOES exist and is currently unused:
  - `topics.metadata.macro_topic` is written on every microtopic row
    (`ingest_upsc_gs_syllabus.py:384`, e.g. `"Indian Culture"`), and
  - the parent macro topic's own `name` is short (`:335`, `level="topic"`,
    `name=macro`).
- A short **but specific** label does NOT exist. `topics.slug` is *not* a
  usable short label — for microtopics it is `slugify("{paper}:{macro}:{theme}")`
  (`ingest_upsc_gs_syllabus.py:378`), i.e. derived from the long theme and
  itself long/opaque. `metadata.macro_topic` is shared by many micro-themes, so
  using it alone would render many identical, non-distinguishing options.
- The `topics` schema (`app/supabase/migrations/029_exam_intelligence_taxonomy.sql:29-44`)
  has `slug`, `name`, `level`, `description`, `metadata` — **no** curated
  short-display-title column.
- Additionally, `/pyqs` only selects `topics` `id, name, subject_id`
  (`exam_intelligence.py:476`) — so even the existing `metadata.macro_topic` and
  parent name are **not currently reaching the frontend**.

**Verdict:** part "wrong field used" (a short *group* label exists in
`metadata.macro_topic` / parent name and isn't wired through), part "no field
exists" (there is no short *specific* per-micro-theme title). Not a pure
one-line "use the other column" fix.

---

## Symptom 2 — selecting ANY topic returns 0 questions

**Status: structural defect CONFIRMED from code; one live check recommended to
pin the exact failure signature (see below). This is NOT a data-sparsity or
catalog-version issue.**

### The round-trip is self-consistent (rules out the "version mismatch" theory)
The value the user selects is literally a stored tag's own `topic_id`:

- The dropdown option `id` comes from `q.topic_tags[i].topic_id`
  (`PyqExplorerSection.jsx:215-216`), which `/pyqs` builds directly from
  `pyq_question_topic_tags.topic_id` (`exam_intelligence.py:466`, returned at
  `:540`).
- On selection the frontend sends it back unchanged as `topic_id`
  (`PyqExplorerSection.jsx:243`), URL-encoded via `URLSearchParams` (UUIDs are
  URL-safe — no trim/transform), and the backend reads the same param name
  (`exam_intelligence.py:265`) and matches with exact string equality against
  the same column (`:395`, `t.get("topic_id") == topic_id`).

So the filter compares a stored tag `topic_id` against stored tag `topic_id`
values. A topics **catalog/version mismatch cannot produce this symptom** — the
selected id is, by construction, a value that exists in
`pyq_question_topic_tags.topic_id`. Preflight §2/§3's version-mismatch
hypothesis is disproved. (Cross-check: `scripts/pyq_question_review.py` validates
each tag's `topic_id` against real topic ids before promotion — `:341-345` — so
tags reference the ingested topics rows.)

### The actual mechanism: an oversized, unbatched `IN()` that fails and is swallowed
The topic/subject filter branch fetches tags for **every** verified question of
the exam in a single unbatched `.in_()`:

```
# exam_intelligence.py:383-393
if topic_id or subject_id:
    tag_rows = (
        sb.table("pyq_question_topic_tags")
          .select("question_id, topic_id")
          .in_("question_id", [q["id"] for q in all_questions])   # :387 — up to ~1000 UUIDs
          .eq("reviewer_status", "verified")
          .limit(50000)
          .execute().data or [])
```

`all_questions` is the exam's verified questions fetched at `:367-380` with an
**unordered `.limit(10000)`**, which PostgREST silently caps at the server
`db-max-rows` (~1000) — the same truncation class fixed in #1016, and explicitly
left un-paginated here per the `NOTE` at `:305-312`. So `[q["id"] for q in
all_questions]` is up to ~1000 UUIDs (~37 KB of query string).

The rest of this codebase treats a large `.in_()` as unsafe and **batches at 250**
for exactly this reason:

- `app/backend/app/exam_intelligence/coverage.py:22` — `_BATCH = 250 # max items per IN() filter`
- `app/backend/app/exam_intelligence/pyq_papers.py:18` — `_BATCH = 250 # max ids per IN() filter (PostgREST URL-length ceiling)`

`list_exam_pyqs` is the one place that does **not** batch. An `.in_()` of ~1000
ids exceeds the PostgREST/proxy URL-length ceiling the repo batches to avoid; the
resulting error is caught by the endpoint's outer `try/except` at
`exam_intelligence.py:553-555`, which returns `{**empty, "exam_id": …, "error": …}`
— i.e. `items: [], total: 0`. Every topic (and every subject) selection therefore
returns "0 questions," **deterministically**, while the unfiltered Browse list
works because it never issues the big `.in_()` — its only per-page tag/option
fetches key on ≤20 question ids (`exam_intelligence.py:453-461`). The exam's
verified **paper** id list (`q_query.in_("pyq_paper_id", paper_ids)`, `:373`) is
small (UPSC CSE has well under ~100 verified papers), so it stays under the
ceiling — which is why unfiltered browse is unaffected.

This matches the reported signature exactly: unfiltered browse shows cards; ANY
topic → structurally 0, not a legitimately-small result.

### The one thing code alone can't fully settle
Whether a ~1000-id `.in_()` returns HTTP 414 / a PostgREST error (→ exception →
swallowed to `total:0`, the deterministic path above) versus is silently accepted
and truncated depends on the live proxy/PostgREST URL-limit config, which isn't in
the repo. Either way the fix (batch the `.in_()`) is correct, but to confirm the
exact failure:

- **Live check A (failure signature):** call
  `GET /api/exam-intelligence/exams/upsc-cse/pyqs?topic_id=<a-real-verified-topic-id>&page=1&page_size=20`
  and inspect the JSON. An `"error"` field present (a 414 / "URI too long" /
  postgrest message) confirms the swallowed-exception path. `"error"` absent with
  `items: []` would instead point at the truncation/sampling variant (still this
  PR's `.in_()`+pagination defect, different failure mode). Backend logs will show
  `"pyqs list failed for upsc-cse"` (`:554`) if the exception path fired.
- **Live check B (id-list size):**
  `SELECT count(*) FROM pyq_questions q JOIN pyq_papers p ON p.id = q.pyq_paper_id
  WHERE p.exam_id = <upsc-cse id> AND p.trust_status = 'verified'
  AND q.reviewer_status = 'verified';`
  A count comfortably above ~250 (expected given 13 verified Mains years) confirms
  the `.in_()` id list is well past the batched ceiling.

---

## §3 — Do the two symptoms share a root cause?

**No — they are fully independent.** They share only the surface (the Topic
dropdown) and the data (topic tags):

- **Symptom 1** is a *display* problem: `topics.name` holds long micro-theme
  prose and no short-yet-specific label field exists; `/pyqs` doesn't even
  surface the short `metadata.macro_topic`/parent name that do exist. It lives in
  the option-label wiring (`PyqExplorerSection.jsx:343`, `exam_intelligence.py:476/504`)
  and the ingest field mapping (`ingest_upsc_gs_syllabus.py`).
- **Symptom 2** is a *query* problem: an unbatched oversized `.in_()` in the
  filter branch fails and is swallowed to `total:0`
  (`exam_intelligence.py:387,553-555`).

Fixing one does not touch the other. They can be implemented as two independent
changes (or one PR with two clearly separated diffs).

---

## Recommended fix approach (described, NOT implemented)

### Symptom 1 (display)
Two viable directions; the follow-up prompt should pick one:

- **A — frontend-only, minimal:** truncate the option label to ~48-64 chars with
  an ellipsis and set the full text as the `<option title>` (and/or the card
  pill's `title`) for hover. No backend/data change. Fastest; keeps everything
  else intact. Trade-off: no macro grouping, truncation can clip mid-word.
- **B — surface the short group label (backend + frontend):** add
  `metadata` (or a computed `macro_topic`) and/or the parent topic name to the
  `/pyqs` topics select (`exam_intelligence.py:476`) and to the `topic_names`
  payload, then render options as `"{macro_topic} › {truncated micro-theme}"` or
  group them under `<optgroup label={macro_topic}>`. More scannable and unique;
  larger change. A curated short-title column on `topics` is a heavier
  alternative and probably unnecessary given `macro_topic` already exists.

Recommendation: ship **A** for the immediate readability win; consider **B** as a
follow-up polish. Do not conflate them.

### Symptom 2 (zero results)
Fix the filter branch in `list_exam_pyqs` (`exam_intelligence.py:383-413`):

1. **Batch the `.in_("question_id", …)` by `_BATCH = 250`** (reuse the exact
   `_chunks`/`_BATCH` pattern already in `coverage.py`/`pyq_papers.py`),
   accumulating `tag_rows` across chunks. This alone removes the deterministic
   `total:0`.
2. **Also paginate `all_questions` deterministically** with `.order("id").range()`
   (the #1016 pattern the `NOTE` at `:305-312` defers) so the filter operates over
   the *complete* verified set, not an arbitrary ≤1000-row sample — otherwise, once
   the corpus exceeds the server cap, filter results would be incomplete/variable
   even after batching. Apply the same batching to the subject-filter topics fetch
   (`:400-411`).
3. Keep the verified-only join conditions unchanged (`:388`, `:395`) — they are
   correct; only the id-list size / pagination is the defect.

This is a backend-only change to one endpoint. It is the natural companion to
#1016 (same truncation family, same file) and would let the next PR's `backend`
check reflect a genuinely working filter.
