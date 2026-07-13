# Regulator eligibility rule authoring — SOP + enforcement prerequisites

**Status:** PLANNED / OPERATOR-RISK. This is a **manual, non-enforced** standard
operating procedure, **not** an enforced authoring contract. Several trust gates
it relies on do not exist in code yet (see §Enforcement gaps). No rule may be
promoted to `verified` until those gaps are closed. Nothing is landed by this doc.

Supersedes the withdrawn migration seed (PR #977, closed) — that leaked cycles
and used lossy encodings. This revision also corrects the first draft of this
spec (PR #979 checkpost), which wrongly described enforcement that the audited
writer does not perform.

## Enforcement gaps — BLOCKING prerequisites (must land before any `verified` rule)

These are real code gaps confirmed on `main`. Until each is closed, authoring is
manual-SOP only and every `verified` promotion is an operator-risk action.

1. **No document/review trust gate in the writer.**
   `admin_exam_eligibility.py._require_trust_provenance()` accepts **any** non-empty
   `source_url` *or* an arbitrary `waiver_reason`; the POST create path allows
   `reviewer_status='verified'` immediately, stamped by the **same** actor; there
   is **no** `document_asset_id` FK on `exam_eligibility_rules` and no check of
   document review state. → A rule can be "verified" with `source_url="https://x"`.
   **Prereq:** add a reviewed-`document_assets` linkage (`document_asset_id` FK +
   direct-locator + reviewer-separation transition) before treating verification
   as gated. Until then, direct official evidence is an honour-system field.
2. **No trust gate on `exam_cycles`.** It has no review column,
   `exam_cycles_read_authenticated` (035) grants authenticated read, and
   `study_os/exam_target_window.py` consumes every non-`cancelled` cycle. → Any
   cycle row is immediately live. **Prereq:** add a review/trust column + gate
   every consumer/RLS before authoring cycles. **Do not author cycles until then.**
3. **No cutoff-aware age evaluation.** The evaluator computes age against
   `date.today()`; the verified-rule loader does not select `cutoff_date_basis` /
   `cutoff_date` and the evaluator never applies them. → Notification age bands are
   unfaithful near the cut-off. **Prereq:** implement cutoff-aware evaluation, or
   keep notification age in the cycle layer, before authoring precise age rows.
4. **~~No include-inactive discovery for draft identities.~~ RESOLVED.**
   `GET /api/admin/exam-eligibility/exams?include_inactive=true` (admin-gated) now
   lists inactive seeded identities (PFRDA Grade A / IRDAI AM, migration 244), each
   with its `is_active` flag so the caller distinguishes draft from active. Default
   (`include_inactive=false`) is unchanged (active-only). The audited authoring flow
   can now resolve those exam ids.

## What the evaluator actually matches (source of truth)

`app/backend/app/exam_eligibility/evaluator.py` (`main`, post-#973). Per stream via
`_rules_for_stream` (stream rules override common for the same `(rule_type, scope)`);
exam-wide verdict uses common-only. **A stream with no own rules inherits the common
verdict** — the root of the SEBI-General hazard below.

| rule_type | field | semantics |
|---|---|---|
| `age_min`/`age_max` | DOB → age | integer compare, **against `date.today()` (no cutoff)** |
| `education_min_level` | highest `aspirant_education.level` | ranked 10th<12th<diploma<graduation<post_graduation<phd |
| `min_percentage` | `aspirant_education.percentage` | **standalone: best across ALL records**; **inside a `qualification_combination`: record-correlated** (the SAME education record must satisfy every leaf in that AND-group) |
| `discipline` | `aspirant_education.degree` + `.stream` | alias-expanded, boundary-aware (`_DISCIPLINE_ALIASES`), else literal boundary match |
| `certification` | `aspirant_certifications.certification_name` | alias-expanded, boundary-aware (`_CERT_ALIASES`); **no count/ordinal** |
| `nationality` | profile.nationality | exact |
| `qualification_combination` | above atomics | recursive `{op:and|or, clauses:[…]}`; leaf `{rule_type, value_text|value_num}`; AND-groups are record-correlated |
| `stream_availability` | — | `not_offered` knockout — **cycle-dependent availability MUST live in the cycle layer** (`exam_cycle_stream_eligibility`), not baseline, even though the baseline enum contains this type |

**Cross-record hazard (P0) — always fold the degree level into the combination.**
Standalone `discipline` / `min_percentage` search ALL of a user's education
records independently, and the common `education_min_level` rule checks only the
highest record. So a user with an unrelated graduation plus a diploma/certificate
whose text contains "law" satisfies the common graduation rule AND a standalone
`discipline = law` rule via **two different records** — a false positive; the
contract's SEBI example is LLB, not any law-labelled record. Only a
`qualification_combination` is **record-correlated** (§semantics), so any
degree-gated stream must encode `education_min_level` (and, where the notification
requires it, `post_graduation`) **inside the same AND-combination** as the
discipline/percentage — never as a standalone discipline rule leaning on the
common baseline. If the exact required level is not yet known from the ingested
source, **defer the recipe**.

**Writer guard (real):** `_reject_ambiguous_linked_qualification`
(`admin_exam_eligibility.py`) blocks verifying a standalone `discipline` AND a
standalone `min_percentage` for the same stream separately. Its scope is exactly
that pair — it does **not** enforce discipline/education-level correlation, which
is why the degree level must be folded into the combination above.

**Alias vocabulary (author values to these keys):**
- Discipline: `it`, `cs`, `ca`, `cma`, `llb`/`law`, `cfa`, `eng`; other values are
  literal boundary matches (`economics`, `statistics`, `electrical`, `civil`).
- Certification: `ca`, `cma`, `cs`, `cfa`, `frm`. **`actuarial`/`finance` are NOT
  keys** — do not use `finance`.

## Per-regulator rule set (draft; author via the admin API once §Prereqs close)

Scope `all` unless a category relaxation applies; qualification gates
`is_knockout=true`. Every row lands `draft`; **verification is blocked until §1
lands**.

### SEBI Grade A
Migration 110 seeds a **verified** common baseline (age + graduation + Indian).
**Hazard (P0):** because a stream with no own rule inherits the common verdict,
the **General** stream (and any stream lacking its own rule) will resolve
`eligible` on age + graduation alone — a known false positive; the contract says
this SEBI baseline is materially insufficient.

**Required before surfacing ANY SEBI stream verdict:** either (a) author General's
**complete** PG/professional qualification rule (record-correlated combination)
so it stops inheriting a bare-graduation pass, or (b) archive/replace the
misleading common baseline for the stream context, or (c) add a trusted
coverage/`unknown` sentinel. Do **not** verify stream deltas (below) while General
still inherits a positive.

Stream keys below are the canonical `exam_streams.stream_key` values from
migration 244. Every degree-gated recipe folds the level into the combination
(cross-record hazard above).

| stream | rule (author only after the General hazard is resolved) |
|---|---|
| `legal` | `qualification_combination {and:[discipline law, education_min_level graduation]}` (LLB) |
| `electrical-engineering` | `qualification_combination {and:[discipline electrical, education_min_level graduation]}` |
| `civil-engineering` | `qualification_combination {and:[discipline civil, education_min_level graduation]}` |
| `information-technology` | **Deferred** — engineering (graduation) vs PG-computing level is notification-specific; author record-correlated once the advertisement's exact acceptable-degree/level list is ingested |
| `research` | **Deferred** — PG economics/statistics/finance set + level from the advertisement |
| `general` | **Deferred** — full PG/professional set (record-correlated) from the advertisement; must be authored so General stops inheriting the bare-baseline pass |

### PFRDA Grade A (identity inactive — discover via admin `include_inactive=true`, §Prereq 4 resolved)
Canonical keys from 244.

| stream | rule |
|---|---|
| `legal` | `qualification_combination {and:[discipline law, education_min_level graduation]}` |
| `research-economics-statistics` | **Deferred** — PG level + exact discipline set from the handout |
| `information-technology` | **Deferred** — level notification-specific |
| `finance-accounts` | **Deferred** — exact professional-qualification / degree set from the handout |
| `actuarial` | **NOT representable** (paper count) — keep the whole stream `unknown`; see IRDAI Actuarial note |
| `general`, `official-language` | not covered here |

Baseline age: **do not author** as baseline (§Prereq 3) — defer to the cycle layer.

### IRDAI Assistant Manager (identity inactive — discover via admin `include_inactive=true`, §Prereq 4 resolved)
Canonical keys from 244. **Registry gap:** 244 seeds only five IRDAI streams
(`generalist`, `actuarial`, `finance`, `information-technology`, `research`) — the
notification's **Law** stream is missing; file a follow-up to add `irdai-am/law`
before authoring for it.

| stream | rule |
|---|---|
| `generalist` | `qualification_combination {and:[education_min_level graduation, min_percentage 60]}` |
| `finance` | `qualification_combination {and:[education_min_level graduation, min_percentage 60, {or:[certification ca, certification cma, certification cs, certification cfa]}]}` |
| `information-technology` | `qualification_combination {and:[education_min_level graduation, {or:[discipline it, discipline cs, discipline eng]}, min_percentage 60]}` |
| `research` | `qualification_combination {and:[education_min_level post_graduation, {or:[discipline economics, discipline statistics]}, min_percentage 60]}` |
| `actuarial` | **Keep the whole stream `unknown`.** "graduation 60% + seven IAI papers": the paper count is not representable, and a lone `min_percentage 60` would resolve `eligible` — a false positive violating the fail-closed rule. No partial floor; keep it a research/manual-review note until a count model or machine-enforced blocker exists. |
| `law` *(missing from 244)* | after the registry gap is filed: `qualification_combination {and:[discipline law, education_min_level graduation, min_percentage 60]}` |

Baseline age: defer to the cycle layer (§Prereq 3).

### RBI / NABARD / SIDBI / IFSCA
- RBI Grade B baseline is verified in 110; DEPR/DSIM deltas deferred to ingestion.
- NABARD/SIDBI specialist streams `blocked_on_notification` (244 metadata).
- IFSCA `blocked_on_advertisement_pdf`.

## Execution checklist (per exam)
0. **Close the relevant §Enforcement gaps first** — otherwise every `verified`
   promotion is honour-system and cycles/age are unsafe.
1. Ingest the advertisement/handout as a `document_assets` row (direct locator).
2. Resolve the exam id via the admin include-inactive path (§Prereq 4).
3. Author the rows above via `admin_exam_eligibility.py` (`draft`), folding
   degree level + discipline + percentage into single record-correlated
   combinations (respect `_reject_ambiguous_linked_qualification`; never
   standalone discipline for a degree-gated stream).
4. Resolve the SEBI-General hazard before verifying any SEBI stream.
5. Keep IRDAI/PFRDA Actuarial `unknown`; keep age out of baseline.
6. Reviewer verifies only against the ingested document; promote `verified` only
   after §1's linkage/reviewer-separation exists.

## Follow-ups to file
- `exam_eligibility_rules.document_asset_id` FK + reviewed-document verify transition + reviewer separation.
- `exam_cycles` trust/review column + gate every consumer & RLS.
- Cutoff-aware age evaluation (select + apply `cutoff_date_basis`/`cutoff_date`), or cycle-layer age only.
- ~~Admin include-inactive exam listing for draft identities.~~ **RESOLVED** — `GET /api/admin/exam-eligibility/exams?include_inactive=true` lists inactive seeded identities with their `is_active` flag.
- Registry gap: add the missing `irdai-am/law` stream to `exam_streams` (244 seeds only five of IRDAI's six streams).
