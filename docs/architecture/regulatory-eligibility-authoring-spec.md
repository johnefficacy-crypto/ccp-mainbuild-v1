# Regulator eligibility rule authoring — spec (post-#973)

**Status:** SPEC — ready to execute once official documents are ingested. No
rules are landed by this doc.

Supersedes the withdrawn migration-seed attempt (PR #977, closed). That seed was
correctly blocked: it leaked cycles through `exam_cycles`, its rules were lossy
encodings, and researched-not-ingested facts do not belong in a forward
migration. This spec is the sanctioned path.

## Hard rules (why the seed was wrong)

1. **Author via the audited writer, not a migration.** `admin_exam_eligibility.py`
   is the intended writer for the new rule_types / `stream_id` / `value_json`
   (migration 248 says so). Every rule is created there so it carries actor +
   audit, and stays `reviewer_status='draft'` until a reviewer promotes it.
2. **Nothing user-facing until a direct official locator is attached and
   reviewed.** The evaluator reads only `verified` rows, so draft rows are inert
   — but promotion to `verified` requires the exact advertisement/handout
   ingested as a `document_assets` row with a direct locator, not an institution
   homepage. Migration 253 dropped the fail-closed CHECK, so verification is now
   *possible* — that makes the review gate the only thing standing between a rule
   and an aspirant, so it must hold.
3. **Do NOT put unverified cycles in `public.exam_cycles`.** It has no trust
   column, `exam_cycles_read_authenticated` (035) grants authenticated read, and
   `study_os/exam_target_window.py` consumes every non-`cancelled` cycle. A
   "draft-in-metadata" cycle is therefore live. Cycles wait until a trust/review
   gate exists on that table or are staged elsewhere.
4. **Only encode what the evaluator can represent faithfully.** Anything that
   needs a count, a scored threshold the schema can't hold, or a credential the
   alias map doesn't know stays as draft research notes on the exam/stream —
   never as an executable rule that would misfire once verified.

## What the evaluator actually matches (source of truth)

From `app/backend/app/exam_eligibility/evaluator.py` (merged via #973). Rules are
evaluated per stream by `_rules_for_stream` (stream rules override common for the
same `(rule_type, scope)`); the exam-wide verdict uses common-only.

| rule_type | field consumed | match semantics |
|---|---|---|
| `age_min` / `age_max` | DOB → age | integer compare |
| `education_min_level` | highest `aspirant_education.level` | ranked: 10th<12th<diploma<graduation<post_graduation<phd |
| `min_percentage` | best `aspirant_education.percentage` | `best_percentage >= value_num` |
| `discipline` | `aspirant_education.degree` + `.stream` | **alias-expanded, boundary-aware** (`_DISCIPLINE_ALIASES`), else literal boundary match |
| `certification` | `aspirant_certifications.certification_name` | alias-expanded, boundary-aware (`_CERT_ALIASES`); **no count / no ordinal** |
| `nationality` | profile.nationality | exact |
| `qualification_combination` | above atomics | recursive `{op:and|or, clauses:[…]}`; leaf = `{rule_type, value_text|value_num}` |
| `stream_availability` | — | `not_offered` → knockout |

**Known alias vocabulary (author values to these keys):**
- Discipline: `it`, `cs`, `ca`, `cma`, `llb`/`law`, `cfa`, `eng` (b.e/b.tech/…).
  Any other value is a literal boundary match (e.g. `economics`, `statistics`,
  `electrical`, `civil` match a degree/stream token containing that word).
- Certification: `ca`, `cma`, `cs`, `cfa`, `frm`. **`actuarial`, `finance` are
  NOT keys** — `finance` would only literal-match a credential containing the
  word "finance" (fragile); do not use it.

## Per-regulator rule set (draft; author in `admin_exam_eligibility.py`)

Scope `all` unless a category relaxation applies; `is_knockout=true` for
qualification gates. **Every row lands `draft`; promotion is a separate reviewed
step keyed to the ingested advertisement.**

### SEBI Grade A (2025 advertisement — ingest before verifying)
Baseline (age 21–30 general +cat relaxations, graduation, Indian) already exists
verified in migration 110; leave it. Stream deltas:

| stream | rule | representable? |
|---|---|---|
| legal | `discipline = law` | ✅ (alias → llb/law) |
| electrical-engineering | `discipline = electrical` | ✅ literal |
| civil-engineering | `discipline = civil` | ✅ literal |
| information-technology | `qualification_combination {or:[discipline it, discipline cs, discipline eng]}` | ✅ |
| research | `qualification_combination {or:[discipline economics, discipline statistics, discipline finance]}` | ✅ literal tokens |
| general | broad PG/professional set — **defer** until the advertisement's exact acceptable-degree list is ingested; encode then as an `or` of `education_min_level=post_graduation` + specific disciplines / certs | ⚠ defer |

### PFRDA Grade A (2025 handout — ingest before verifying)
Baseline (age 21–30, graduation, Indian) → author draft. Stream deltas:

| stream | rule | representable? |
|---|---|---|
| legal | `discipline = law` | ✅ |
| research-economics-statistics | `qualification_combination {or:[discipline economics, discipline statistics]}` | ✅ |
| information-technology | `qualification_combination {or:[discipline it, discipline cs]}` | ✅ |
| finance-accounts | `qualification_combination {or:[certification ca, certification cma, certification cfa, discipline economics, discipline eng]}` — refine to the handout's exact list | ⚠ refine on ingest |
| actuarial | actuarial-paper requirement — **NOT representable** (count/ordinal); keep as a stream research note, not a rule | ❌ defer |

### IRDAI Assistant Manager (2024 advertisement — ingest before verifying)
Baseline (age 21–30, graduation, Indian) → author draft. Stream deltas (all
streams carry the 60% floor):

| stream | rule | representable? |
|---|---|---|
| generalist | `min_percentage = 60` | ✅ |
| law | `qualification_combination {and:[discipline law, min_percentage 60]}` | ✅ |
| finance | `qualification_combination {and:[min_percentage 60, {or:[certification ca, certification cma, certification cs, certification cfa]}]}` | ✅ (real cert aliases) |
| it | `qualification_combination {and:[{or:[discipline it, discipline cs, discipline eng]}, min_percentage 60]}` | ✅ |
| research | `qualification_combination {and:[education_min_level post_graduation, {or:[discipline economics, discipline statistics]}, min_percentage 60]}` | ✅ (PG encoded) |
| actuarial | "graduation 60% + seven IAI papers" — **the paper count is NOT representable**; author only `min_percentage 60` as the representable floor and record the IAI-papers requirement as a stream research note for manual/interview screening | ⚠ partial |

### RBI Grade B / NABARD / SIDBI / IFSCA
- RBI Grade B: baseline verified in 110; DEPR/DSIM stream deltas deferred until
  the notification's exact economics/statistics PG requirements are ingested.
- NABARD, SIDBI: specialist streams are `blocked_on_notification` (migration 244
  metadata) — author on the next open cycle.
- IFSCA: `blocked_on_advertisement_pdf` — nothing until the PDF is ingested.

## Execution checklist (per exam, when its advertisement is ingested)

1. Ingest the advertisement/handout as a `document_assets` row (direct locator).
2. Author the rows above via `admin_exam_eligibility.py` (draft), citing that
   `document_assets` id in source/notes.
3. Reviewer verifies discipline tokens against `_DISCIPLINE_ALIASES` /
   `_CERT_ALIASES`; anything not representable stays a research note.
4. Promote to `verified` only after human review; confirm the Compass renders the
   expected per-stream verdicts (streams now carry real rules).
5. Cycles: author only once a trust/review gate on `exam_cycles` exists (or the
   `exam_target_window` consumer is taught to exclude unreviewed cycles).

## Follow-up worth filing
- Add an explicit review/trust column to `exam_cycles` (+ gate every consumer &
  RLS), so cycle data can be staged draft like eligibility rules. Until then,
  cycles cannot be seeded safely.
