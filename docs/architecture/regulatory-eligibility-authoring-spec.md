# Regulator eligibility rule authoring — SOP + enforcement prerequisites

**Status:** CODE-FIXED, OPERATOR VALIDATION PENDING. The authoring safeguards
now exist in code, but migrations 257 and 261 still require linked-Supabase
application and operator/RLS proof (see §Enforcement gaps). No new rule or cycle
may be promoted to `verified` until that validation is captured.

Supersedes the withdrawn migration seed (PR #977, closed) — that leaked cycles
and used lossy encodings. This revision also corrects the first draft of this
spec (PR #979 checkpost), which wrongly described enforcement that the audited
writer does not perform.

## Enforcement gaps — BLOCKING prerequisites (must land before any `verified` rule)

These are real code gaps confirmed on `main`. Until each is closed, authoring is
manual-SOP only and every `verified` promotion is an operator-risk action.

1. **No document/review trust gate in the writer.** — **CODE-FIXED, VALIDATION PENDING**
   (migration 257; not yet applied to any linked Supabase / no operator validation).
   Previously `admin_exam_eligibility.py._require_trust_provenance()` accepted **any**
   non-empty `source_url` *or* an arbitrary `waiver_reason`; the POST create path
   allowed `reviewer_status='verified'` immediately, stamped by the **same** actor;
   there was **no** document linkage on `exam_eligibility_rules` and no check of
   document review state. → A rule could be "verified" with `source_url="https://x"`.

   **Closed by migration 257 + the document-gated review endpoints:**
   - `exam_eligibility_rules` gains `source_document_id` (FK → `document_assets`,
     `ON DELETE RESTRICT`, repo convention name), `source_page_start` /
     `source_page_end` (paired, positive, ordered CHECKs), and `created_by`
     (FK → `auth.users`) for reviewer separation.
   - `syllabus_documents` gains `reviewed_by` / `reviewed_at` / `reviewer_notes`.
   - `review_syllabus_document()` — atomic SECURITY DEFINER RPC: promotes
     `pending → verified` only when the linked `document_assets` row is a locked,
     `processed`, authoritative (`official_archive`/`official_scan`)
     notification/corrigendum with populated storage, ≥1 extracted page, matching
     exam (and cycle when set), and the reviewer is **not** the uploader.
   - `review_exam_eligibility_rule()` — atomic SECURITY DEFINER RPC: promotes
     `draft → verified` only with a page locator into a **verified**
     `syllabus_documents` row (**locked** `FOR UPDATE`, no TOCTOU) backed by an
     authoritative same-exam processed asset whose referenced pages are all
     extracted, and only when the reviewer differs from `created_by`. Reviewer
     separation **fails closed** when `created_by`/`uploaded_by` is absent. **No
     URL-only and no waiver-based verification remain.**
   - **Authority-dependency guard:** an `AFTER UPDATE` trigger on
     `syllabus_documents` cascade-demotes every dependent verified rule to `draft`
     when its supporting authority is demoted (`verified → pending/rejected/
     superseded`) or its `source_document_id`/exam is reassigned
     (`documents/{id}/link-to-syllabus`) and no other verified syllabus still backs
     it — so a verified rule can never outlive its authority, on any write path.
   - The admin API create path always lands `draft` (create-as-verified is
     rejected), the generic update path cannot promote to `verified`, a material
     edit demotes a verified rule (a DB trigger enforces this too), and a dedicated
     `POST /rules/{id}/review` endpoint is the only promotion path.

   The remaining work is operator/live validation (apply 257 to the linked
   Supabase, capture RLS/behavioural proof) before any rule is promoted `verified`
   in production. Until that validation lands, treat verification as code-gated but
   not operationally proven.
2. **Trust gate on `exam_cycles`.** — **CODE-FIXED, VALIDATION PENDING**
   Previously `exam_cycles` had no review column, `exam_cycles_read_authenticated`
   (035) granted every authenticated user read, and `study_os/exam_target_window.py`
   (+ planner / mission-control / plan-timeline) consumed every non-`cancelled`
   cycle → any cycle row was immediately live.
   - Migration **261** adds `reviewer_status` (`draft`/`reviewed`/`verified`) +
     `reviewed_by`/`reviewed_at`/`created_by`. Existing cycles are grandfathered
     `verified` once (column default `draft`, so new cycles are gated); the
     permissive 035 read policy is replaced by verified-only authenticated read
     (`exam_cycles_read_verified`, admin-exempt).
   - An atomic SECURITY DEFINER `review_exam_cycle` RPC gates
     `draft → reviewed → verified` (no jump; CAS on expected status; reviewer
     separation, fail-closed on missing `created_by`; atomic audit; demotion to
     draft clears the stamp), and a BEFORE-UPDATE trigger blocks reviewed-content edits on reviewed/verified
     cycles unless the same statement demotes to `draft` (the CMS create path lands
     `draft`; generic CMS and corrigendum registry-action updates demote on
     material edits, including source provenance/metadata, and can never promote). `POST /exam-cycles/{id}/review` is the only promotion path.
   - Every Study OS consumer (`exam_target_window.py`, `planner.py`,
     `mission_control.py`, `plan_timeline.py`, the `/study/exams` cycle API) now
     filters `reviewer_status='verified'`.

   The remaining work is operator/live validation (apply 261 to the linked
   Supabase, capture RLS/behavioural proof). **Do not author cycles until that
   validation lands.**
3. **~~No cutoff-aware age evaluation.~~ CODE-FIXED.** The baseline evaluator
   still measures age against `date.today()` (correct for stable baseline), but a
   cutoff-aware **cycle layer** now lands: `evaluator._resolve_cutoff_date`
   (`fixed_date`→the rule's own `cutoff_date`; `cycle_notification`→the
   authoritative cycle's `notification_date`), a `cutoff_context` mode on
   `evaluate_exam_for_user` that measures each age rule on its official cut-off,
   and a public `evaluate_cycle_eligibility`. The cycle loader
   (`_load_cycle_rules_by_stream`) selects `cutoff_date_basis` / `cutoff_date`
   from verified `exam_cycle_stream_eligibility` rows, and
   `summarize_user_eligibility` exposes an additive `cycle` provenance band. When
   the cut-off — or the authoritative cycle source — is unavailable the age rule
   is left unevaluated so the verdict **preserves `unknown`** (never a today-based
   guess). **Notification age still belongs in the cycle layer, not baseline
   rows.** Precise age rows may now be authored on `exam_cycle_stream_eligibility`
   with an explicit `fixed_date` cut-off. **A2 (CODE-FIXED, VALIDATION PENDING)
   wires the cycle-band loader:** `summarize_user_eligibility` now loads verified
   cycles via `_load_verified_cycles` (filters `reviewer_status='verified'` per the
   migration-261 trust gate) and `_cycle_band_for_exam` resolves `cycle_notification`
   age on the verified cycle's `notification_date`; unverified/absent cycles are
   dropped (never shown, baseline never substituted). The Regulatory Exam Compass
   (`ExamStreamBreakdown.jsx` + `EligibleExamsCard.jsx`) renders this real
   current-cycle band with an explicit "No verified cycle eligibility available"
   empty state. Live/browser proof PENDING.
4. **~~No include-inactive discovery for draft identities.~~ RESOLVED.**
   `GET /api/admin/exam-eligibility/exams?include_inactive=true` (admin-gated) lists
   inactive identities (PFRDA Grade A / IRDAI AM, migration 244); default
   (`include_inactive=false`) is unchanged (active-only). `is_active=false` alone is
   ambiguous — it cannot tell a **seeded draft** from a **retired** exam — so each
   item also carries `provenance` (from `exams.metadata.provenance`, e.g. `"draft"`);
   author only against `provenance="draft"` regulator identities.
   `GET /api/admin/exam-eligibility/exams/{exam_id}/streams` returns each canonical
   stream's generated `id` + `stream_key` + `provenance`, which `RuleCreate.stream_id`
   needs to author a stream-scoped rule (the 244 `exam_streams` UUIDs are
   non-deterministic). Exam id **and** stream ids now both resolve without a direct
   DB lookup.

## What the evaluator actually matches (source of truth)

`app/backend/app/exam_eligibility/evaluator.py` (`main`, post-#973). Per stream via
`_rules_for_stream` (stream rules override common for the same `(rule_type, scope)`);
exam-wide verdict uses common-only. **A stream with no own rules inherits the common
verdict** — the root of the SEBI-General hazard below.

| rule_type | field | semantics |
|---|---|---|
| `age_min`/`age_max` | DOB → age | integer compare; **baseline: against `date.today()`**; **cycle layer (`evaluate_cycle_eligibility`): against the official cut-off** (`fixed_date`→row `cutoff_date`; `cycle_notification`→authoritative cycle `notification_date`; unresolved⇒`unknown`) |
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
Canonical keys from 244, which seeds all **six** IRDAI streams — `generalist`,
`actuarial`, `finance`, `information-technology`, `research`, and **`law`** (the
`irdai-am` exam is described as "six streams" and `law` is an existing canonical
`exam_streams` row). No registry gap.

| stream | rule |
|---|---|
| `generalist` | `qualification_combination {and:[education_min_level graduation, min_percentage 60]}` |
| `finance` | `qualification_combination {and:[education_min_level graduation, min_percentage 60, {or:[certification ca, certification cma, certification cs, certification cfa]}]}` |
| `information-technology` | `qualification_combination {and:[education_min_level graduation, {or:[discipline it, discipline cs, discipline eng]}, min_percentage 60]}` |
| `research` | `qualification_combination {and:[education_min_level post_graduation, {or:[discipline economics, discipline statistics]}, min_percentage 60]}` |
| `actuarial` | **Keep the whole stream `unknown`.** "graduation 60% + seven IAI papers": the paper count is not representable, and a lone `min_percentage 60` would resolve `eligible` — a false positive violating the fail-closed rule. No partial floor; keep it a research/manual-review note until a count model or machine-enforced blocker exists. |
| `law` | `qualification_combination {and:[discipline law, education_min_level graduation, min_percentage 60]}` |

Baseline age: defer to the cycle layer (§Prereq 3).

### RBI / NABARD / SIDBI / IFSCA
- RBI Grade B baseline is verified in 110; DEPR/DSIM deltas deferred to ingestion.
- NABARD/SIDBI specialist streams `blocked_on_notification` (244 metadata).
- IFSCA `blocked_on_advertisement_pdf`.

## Execution checklist (per exam)
0. **Close the relevant §Enforcement gaps first** — otherwise every `verified`
   promotion is honour-system and cycles/age are unsafe.
1. Ingest the advertisement/handout as a `document_assets` row (direct locator).
2. Resolve the exam id via the admin include-inactive path (`provenance="draft"`
   only), then its stream ids via `GET …/exams/{exam_id}/streams` (§Prereq 4).
3. Author the rows above via `admin_exam_eligibility.py` (`draft`), folding
   degree level + discipline + percentage into single record-correlated
   combinations (respect `_reject_ambiguous_linked_qualification`; never
   standalone discipline for a degree-gated stream).
4. Resolve the SEBI-General hazard before verifying any SEBI stream.
5. Keep IRDAI/PFRDA Actuarial `unknown`; keep age out of baseline.
6. Reviewer verifies only against the ingested document; promote `verified` only
   after §1's linkage/reviewer-separation exists.

## Follow-ups to file
- ~~`exam_eligibility_rules` document linkage FK + reviewed-document verify transition + reviewer separation.~~ **CODE-FIXED (migration 257, `source_document_id` per repo convention); VALIDATION PENDING** — apply to the linked Supabase and capture operator/RLS proof before promoting any rule `verified`.
- ~~`exam_cycles` trust/review column + gate every consumer & RLS.~~ **CODE-FIXED (migration 261); VALIDATION PENDING** — apply to the linked Supabase and capture operator/RLS proof before authoring cycles.
- ~~Cutoff-aware age evaluation (select + apply `cutoff_date_basis`/`cutoff_date`), or cycle-layer age only.~~ **DONE** — cycle-layer cutoff-aware age (`evaluate_cycle_eligibility` + `cycle` provenance band). **A2 (CODE-FIXED, VALIDATION PENDING):** the summary path now passes migration-261 `verified` cycles (`_load_verified_cycles`), so `cycle_notification` age resolves on the verified cycle's `notification_date` and the Compass renders the real current-cycle band; unverified/absent cycles are dropped. Live/browser proof PENDING.
- ~~Admin include-inactive exam listing + stream listing for draft identities.~~ **RESOLVED** — `GET …/exams?include_inactive=true` surfaces inactive identities with `is_active` + `provenance`; `GET …/exams/{exam_id}/streams` returns canonical stream ids/keys for `RuleCreate.stream_id`.
- ~~Registry gap: add the missing `irdai-am/law` stream.~~ **NOT A GAP** — migration 244 already seeds all six IRDAI streams, including `law`.
