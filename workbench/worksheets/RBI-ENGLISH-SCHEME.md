# RBI Grade B Phase II — English (Descriptive) tagging scheme

Worksheet: `workbench/worksheets/RBI-ENGLISH-DESCRIPTIVE-tags.csv`
Source: `workbench/sources/rbi-descriptive-english.json` (12 rows, full untruncated `question_text`)
Theme catalogue: `workbench/catalogs/essay_themes_live.json` (15 rows, merged in PR #1164)
Base: `origin/main` @ `9dd746cb`

Worksheet only. No POSTs, no live DB, no migration. Every tag is a proposal for review.

---

## 1. Format axis (primary)

The UPSC essay paper has one format. Each RBI English paper has three, always in the same slots:

| question_number | format | marks | stated word limit |
|---|---|---|---|
| 1 | `essay` — choose 1 of 4 prompts | 40 | 2022–23 `~600`; 2024–25 `600-620` |
| 2 | `precis` of a supplied passage | 30 | 2022–23 `~180`; 2024–25 `180-200` |
| 3 | `comprehension` — passage + sub-questions | 30 | none stated (blank in CSV) |

`format` is the first column a reader filters on. Theme comes second. Marks and word limits are copied from the source's `metadata` (`marks`, `word_limit`). They match the header line of each `question_text`.

## 2. E1 split convention (essay rows only)

Each essay row is a container: one `question_id` holds 4 alternative prompts, and the candidate writes on one of them. It gets one worksheet row per prompt:

- `row_id` = `RBI-ENG-<year>-Q1-P<n>`, `prompt_index` = n (1–4, in source order)
- `parent_question_id` = the container's `question_id`
- `prompt_text_excerpt` = the prompt text as written in the source (first 160 chars), with its leading bullet or `a)`/`A.` label removed
- `marks` / `word_limit` = the container's values, repeated on each prompt (the paper sets them per container, not per prompt)

This follows the UPSC optional map-item convention: one row per item, parented to the source question (`docs/status/2026-09-09-mains-optionals-strategy-rev2.md:361-362`).

Precis and comprehension rows are **not** split. Each is one row with `row_id` = `RBI-ENG-<year>-Q<n>` and `prompt_index` blank. The comprehension sub-questions (a)–(e) are read-only tests on a single passage, not alternatives to choose from.

## 3. How precis/comprehension theming differs from essay theming

- **Essay prompt** → tagged by the theme the candidate must *argue through*, the same as the UPSC essay corpus. `essay_type` is set (`quote_abstract` | `issue_concrete`).
- **Precis / comprehension** → tagged by the theme of the **source passage**. The candidate summarises or extracts; they take no position of their own. The theme tells a learner "what the passage is about", not "what stance to take". Every one of these 8 rows says so in `notes`. `essay_type` and `quote_source_type` are blank on them (see gap G4).
- `quote_source_type` is filled only when the prompt itself names who said the quote. The two quote prompts (2022 P1 "Peace cannot be kept by force…", 2024 P4 "Anyone who stops learning is old…") name no one, so both are blank. They are not filled from outside knowledge of who said them.
- Secondary theme: one primary tag plus an optional `secondary_theme_code`, used only where the prompt or passage really spans two themes, as in the UPSC corpus. A dual theme never splits a row.

## 4. Theme distribution

24 rows (16 essay prompts + 4 precis + 4 comprehension).

| theme_code | primary: essay | primary: precis | primary: comp | primary total | as secondary |
|---|---|---|---|---|---|
| ECO | 4 | 0 | 2 | **6** | 3 |
| SCI | 2 | 1 | 2 | **5** | 1 |
| SOC | 3 | 0 | 0 | **3** | 3 |
| ENV | 2 | 1 | 0 | **3** | 3 |
| IR | 2 | 0 | 0 | 2 | 2 |
| AIE | 0 | 2 | 0 | 2 | 0 |
| PER | 1 | 0 | 0 | 1 | 3 |
| HLW | 1 | 0 | 0 | 1 | 1 |
| SLF | 1 | 0 | 0 | 1 | 1 |
| ETH | 0 | 0 | 0 | 0 | 2 |
| NAT | 0 | 0 | 0 | 0 | 1 |
| GOV, ABS, CLM, FED | — | — | — | 0 | 0 |

- 17 of 24 rows carry a secondary code.
- `essay_type` across the 16 prompts: `issue_concrete` 14, `quote_abstract` 2. RBI prompts are mostly concrete issues. UPSC prompts lean heavily to quotes. In practice this makes `quote_abstract`, the column default (G4), the wrong default for RBI.
- Confidence: high 8, medium 11, low 5.

## 5. Codes used / never fired

- **Fired (primary or secondary), 11:** AIE ECO ENV ETH HLW IR NAT PER SCI SLF SOC. Only ETH and NAT fire as secondary alone.
- **Never fired, 4:** `GOV`, `ABS`, `CLM` (reserved), `FED` (reserved).
  - GOV: no prompt in 2022–25 asks about state machinery or polity.
  - ABS: both quote prompts have a clear domain hook (peace → IR, learning → SLF).
  - CLM (reserved): no reserved code was used. Four rows would fit CLM's "climate action" angle better than ENV's "civilisational nature-relationship" framing: 2022-Q1-P3 (renewables/OSOWOG), 2023-Q1-P3 (economic impact of climate change, as secondary), 2024-Q1-P2 (climate migration, as secondary), 2025-Q1-P1 (NDC emission intensity). Each is tagged with the nearest **active** code (ENV) and says so in `notes`. That is repeated evidence for promoting CLM, but deciding it is out of scope here.
- **Reserved-code usage:** none. No prompt fitted no active code at all, so `UNMAPPED` was not needed.

### Catalogue inconsistency (noted, not resolved)

`HLW` and `AIE` have `status: "active"` (`essay_themes_live.json:116`, `:136`), but their descriptions still begin "Reserved -- …" (`:115`, `:135`; HLW's also says "Promote to active on first clear PYQ hit"). Per instruction, both are treated as **ACTIVE and usable**. HLW is primary on 2024-Q1-P3 and AIE on 2023-Q2 and 2024-Q2. This worksheet does not try to reconcile the status and the description.

## 6. Where the catalogue strains for RBI (drives the 5 low-confidence rows)

The taxonomy was built for the UPSC essay paper (`265_essay_theme_taxonomy.sql:2-4`). The RBI paper draws on management and finance content that it has no home for:

| gap | rows | handling |
|---|---|---|
| GAP-1 no workplace / organisational-management / business code | 2023-Q1-P1 (org culture), 2023-Q1-P2 (social-media recruitment), 2023-Q1-P4 (multilingual business accounts), 2024-Q3 (CRM) | nearest active code (PER / SCI / SOC / SCI), `low` |
| GAP-2 no finance / banking-mechanics code; ECO's boundary excludes "policy mechanics" (`essay_themes_live.json:45`) | 2022-Q3 (financial derivatives) | ECO, `low` |
| ECO boundary strain (concrete sectoral economics, not philosophy) | 2022-Q1-P4, 2024-Q1-P1, 2025-Q1-P4 | ECO, `medium` |
| CLM reserved (see §5) | 2022-Q1-P3, 2025-Q1-P1 (primary ENV) | ENV, `medium` |

No new codes proposed. This table is the evidence a taxonomy owner would need.

## 7. Gap between this scheme and live `essay_pyq_tags`

Schema: `app/supabase/migrations/265_essay_theme_taxonomy.sql` (`essay_themes` :13-26, `essay_pyq_tags` :31-53). Routers: `app/backend/app/api/essay_builder.py:47` (`/essay-pyq-tags`), `:48` (`/essay-themes`). Admin write whitelist: `app/backend/app/api/admin_exam_intel_cms.py:3569-3572` (`_ESSAY_TAG_FIELDS`).

- **G1 — no `format`, no `prompt_index`, no `parent_question_id`.** `essay_pyq_tags` columns (:32-51) are `id, question_id, theme_id, secondary_theme_id, essay_type, quote_source_type, tagging_source, confidence_score, reviewer_status, reviewed_by, reviewed_at, metadata, created_at`. Nothing carries the format axis or the E1 parent/child link. The only place they could go without a schema change is `metadata jsonb` (:50), which the admin whitelist accepts (`admin_exam_intel_cms.py:3571`).
- **G2 — `question_id` must point at a real question.** `question_id uuid not null references public.pyq_questions(id)` (:33). The 16 split prompts are not `pyq_questions` rows, so as stored today all 4 prompts of a container would tag the **parent** `question_id`, and the prompt they belong to would be lost.
- **G3 — `unique(question_id, theme_id)` (:52)** stops two prompts under one container from sharing a theme once they are all stored against the parent (G2). Primary codes per container in this corpus: 2022 {IR, SOC, ENV, ECO}, 2023 {PER, SCI, ECO, SOC}, 2024 {ECO, IR, HLW, SLF}, 2025 {ENV, SCI, SOC, ECO}, so there are **0 primary collisions here**. The constraint still blocks the convention in general: it would bite as soon as a container repeats a theme.
- **G4 (additional, found in this run) — `essay_type text not null default 'quote_abstract'` (:36-37).** Precis and comprehension rows have no essay type, but the column cannot be null. An insert would silently record them as `quote_abstract`.

Described only. No migration is proposed or written in this run.

### 7.1 Resolution (added after this section was written)

All four gaps are now closed. Two by a schema change, two by the child-row load —
recorded here so the gap list above is read as history, not as open work.

- **G1 — RESOLVED by migration `304_essay_pyq_tags_format.sql`, applied live.**
  `essay_pyq_tags` now carries `format` as `NOT NULL` with **no default**, checked
  over `essay | precis | comprehension`. The 100 pre-existing UPSC essay rows were
  backfilled to `'essay'` in the same migration. `format` no longer needs to ride
  in `metadata`. `prompt_index` and `parent_question_id` deliberately did **not**
  become columns — see G2.

- **G2 — RESOLVED by the child-row load (RBI-ENG-CHILD-01).** The 16 split prompts
  are now real `pyq_questions` rows, one per prompt, `question_number` and
  `display_order` 301-304 per paper, refs `ENG-Q1-P1`…`ENG-Q1-P4`. Each prompt
  therefore has its own `question_id` and tags against itself, so nothing is lost
  to the parent. The four essay parents are marked `metadata.is_container = true`
  and are **not tagged**. The parent/child link lives in `pyq_questions.metadata`,
  which is why no `parent_question_id` column was added to `essay_pyq_tags`.

- **G3 — NO LONGER BINDS, for the same reason.** `unique(question_id, theme_id)`
  (`265:52`) is unchanged and was not relaxed. It stopped mattering rather than
  being fixed: with one `question_id` per prompt, two prompts of one container
  sharing a theme are now two different `question_id` values, so the constraint
  cannot collide on them. The 0-collision count recorded above was a property of
  this corpus; the convention is now safe in general.

- **G4 — RESOLVED by migration 304.** `essay_type` lost its
  `DEFAULT 'quote_abstract'` and its `NOT NULL`, and gained
  `essay_pyq_tags_essay_type_format_check`, which ties it to `format`:
  `format='essay'` requires `essay_type IS NOT NULL`, and
  `format IN ('precis','comprehension')` requires `essay_type IS NULL`. A precis
  row can no longer be silently recorded as a quote-abstract essay — the insert
  now fails instead.

**Apply-ready output:** `workbench/worksheets/RBI-ENGLISH-TAGS-APPLY.csv`. 24 rows
— the 16 essay rows retargeted onto their child `question_id`s, the 8
precis/comprehension rows on their existing parent ids — with theme codes resolved
to live UUIDs and the 304 CHECK satisfied row by row.

## 8. Validation

- 12 source rows → 24 worksheet rows: 4 essay containers × 4 prompts = 16 (2022: 4, 2023: 4, 2024: 4, 2025: 4) + 4 precis + 4 comprehension. Matches the expected 24.
- 12 / 12 source `question_id`s appear as `parent_question_id`.
- 24 / 24 primary codes and 17 / 17 secondary codes exist in the 15-code catalogue. 0 reserved codes, 0 UNMAPPED.
- 8 / 8 precis and comprehension rows carry the correct `format` and the source-passage theming note.
