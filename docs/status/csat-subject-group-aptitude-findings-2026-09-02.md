# CSAT `subject_group='aptitude'` — Origin, Blast Radius, and Operator Fix

**Date:** 2026-09-02
**Scope:** read-only investigation. No database was touched, no migration was authored.
**Subject under investigation:** `public.subjects.id = ce8d97ee-c1de-4ce2-a5ef-36d05c14d859`, `slug = 'upsc-csat'`.

---

## 0. Summary

Production CSAT carries `subject_group = 'aptitude'`. That string exists in **no repository
artefact**. Every seed, validation script, preflight check, and test in this repo expects
`'reasoning'`. Because `'aptitude'` is in neither `_GROUP_FAMILY` nor `_SLUG_FAMILY`
(`upsc-csat` is absent from the slug table too), `family_for_subject()` returns `None` and
CSAT silently runs on `_GENERIC_POLICY` instead of `FAMILY_REASONING`.

The value is **operator-entered free text**, almost certainly typed into the Exam Intelligence
CMS subject form, which renders `subject_group` as an unconstrained text input backed by an
unconstrained `text` column.

**No committed code path will re-introduce `'aptitude'` after a one-off `UPDATE`.** The fix is
therefore a single data correction, and this document does not propose a code change.
See §5 for the candidate code changes that were considered and rejected, with reasons.

---

## 1. Where `'aptitude'` could have been written

### 1.1 Every literal `aptitude` in the repository

A full-tree grep (excluding `.git`, `node_modules`, `graphify-out`) finds `aptitude` only as
**display prose**, never as a `subject_group` value:

| Location | Kind | Value |
| --- | --- | --- |
| `app/supabase/seeds/exam_intelligence_demo_upsc_cse.sql:99` | subject **name** | `'CSAT (Aptitude)'` — `subject_group` on that row is `'reasoning'` |
| `app/supabase/seeds/exam_intelligence_demo_ssc_cgl.sql:79` | subject name/slug | `'Quantitative Aptitude'` / `quantitative-aptitude`, `subject_group='numerical'` |
| `app/backend/app/study_os/subject_runtime_policy.py:87` | `_SLUG_FAMILY` key | `"quantitative-aptitude": FAMILY_QUANT` — a **slug**, not a group |
| `app/frontend/.../ScoreSnapshotPanel.jsx:83` | UI label | `reasoning: "CSAT Paper II — Aptitude"` |
| `app/supabase/seeds/pilot_content_ssc_cgl_banking.sql`, `migrations/135`, `e2e_fixtures.sql` | section/content labels | `Quantitative Aptitude` |
| `mains_syllabus_review_verified.csv`, `topic_catalog.json`, `pyq_2014_mains_questions.json`, `spot_check_review.txt` | GS4 ethics syllabus text | `"integrity and aptitude"` — unrelated |

`git log -S'aptitude'` across all history surfaces only the GS4 ethics content bulk-review
commits (`5d70eef`, `f8ed700`, `adffc5c`). No commit has ever written `'aptitude'` as a
taxonomy group value.

### 1.2 Every site that writes or updates `subjects.subject_group`

**Backend (the complete set — only two statements touch the table):**

| Site | Statement | Regression risk |
| --- | --- | --- |
| `app/backend/app/api/admin_exam_intel_cms.py:3307` | `POST /subjects` → `supabase.table("subjects").upsert(row, on_conflict="slug")` | **Overwrites an existing row by slug.** Accepts any string for `subject_group` — `_reject_unknown` checks only *field names* against `_SUBJECT_FIELDS`, never values. |
| `app/backend/app/api/admin_exam_intel_cms.py:3335` | `PATCH /subjects/{id}` → `.update(patch)` | Same: no value validation. |

Both are reachable through two more generic endpoints that reuse the same config:

| Endpoint | Config | Note |
| --- | --- | --- |
| `POST /bulk-import` (`admin_exam_intel_cms.py:4745`) | `_IMPORT_CONFIG["subjects"]` (`:4589`) — `allowed=_SUBJECT_FIELDS`, `enums={}`, `upsert_on="slug"` | Upserts by slug; `enums` is empty so `subject_group` is unvalidated. |
| `POST /bulk-update` (`:4934`) | `_BULK_EDIT_CONFIG["subjects"]` (`:4911`) — `allowed = _SUBJECT_FIELDS - {"slug","name"}`, `enums={}` | `subject_group` **is** in the bulk-editable set. |

**Frontend:** `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx:428` declares
`{ key: "subject_group", label: "subject_group" }` — no `type: "enum"`, no `options`. It renders
as a plain text box in both the create and edit forms (`subject_group` is not in
`EDIT_EXCLUDED_FIELDS.subjects`, which only excludes `slug`), and
`NULLABLE_ON_EDIT.subjects` (`:625`) permits clearing it to `null`.

**Scripts:** `scripts/ingest_upsc_gs_syllabus.py:164` posts `subject_group=group` through the
CMS `POST /subjects` envelope, where `group = paper.paper_id` verbatim (`:319`) — i.e.
`'GS_1'`…`'GS_4'`. It only ever creates slugs `upsc-cse-mains-gs1..gs4` (`:313`) and matches by
slug before writing, so it cannot have produced `'aptitude'` on `upsc-csat`. It is, however,
another free-text producer (see §4).

**SQL:** `seeds/exam_intelligence_demo_upsc_cse.sql`, `seeds/exam_intelligence_demo_ssc_cgl.sql`,
`seeds/e2e_workspace_fixtures.sql`, `seeds/templates/exam_intelligence_import_template.sql`,
`validation/validate_reasoning_strategy_readiness.sql`,
`validation/validate_quant_heuristic_readiness.sql`, `migrations/205:1060`. None writes
`'aptitude'`.

**Schema:** `migrations/029_exam_intelligence_taxonomy.sql:10` — `subject_group text` (nullable,
no `CHECK`, no FK, no enum). `slug text not null unique` (`:7`). Index at `:71`.

### 1.3 Most likely origin — and confidence

**Origin: a human operator typed `aptitude` into the CMS subject form** (create or edit) for the
production CSAT subject.

**Confidence: high** for "operator-entered via the CMS write path", **medium-high** for
"specifically the single-row create/edit form rather than `/bulk-import`".

Supporting evidence:

1. The value exists nowhere in the repo, in any branch, in any commit. It cannot have arrived
   from a seed, migration, script, or importable data file (no `.csv`/`.json`/`.ndjson` in the
   tree carries a `subject_group` key at all).
2. `subjects` has exactly two write statements in the whole backend, both CMS-gated. There is no
   scheduler job, scraper, or AI pipeline that writes this column.
3. The row's id `ce8d97ee-…` is a `gen_random_uuid()` default, not one of the deterministic seed
   ids (`a0000005-0000-0000-0000-000000000005` is the seeded CSAT). The production row was
   created outside the seed.
4. `docs/audits/2026-07-14-…-csat-set-b-…-validation.md:72` records the subject's display as
   `"subject_name": "upsc-csat"` — the **slug string reused as the name**, a hand-entry
   signature; the seeded row is named `'CSAT (Aptitude)'`.
5. `app/backend/op0_readiness/upsc-cse_prelims_2026.json:39` shows the sibling section label
   `" General Studies Paper II / CSAT"` with a **leading space** — the same manual-entry
   fingerprint on the same operator session.
6. `'aptitude'` is the natural lay word for CSAT (the paper is officially the *Civil Services
   Aptitude Test*), and the seeded display name literally contains "(Aptitude)". An operator
   filling a free-text `subject_group` box would write exactly this.

---

## 2. Will `'aptitude'` come back after a one-off `UPDATE`?

**No — not from any committed code.** This is the answer to "is there a deeper bug": there is
not. Every artefact that mentions CSAT's group already says `'reasoning'`
(`seeds/exam_intelligence_demo_upsc_cse.sql:99`;
`app/backend/tests/exam_intelligence/test_score_snapshot_admin_api.py:279`;
`app/supabase/checks/reasoning_content_readiness_preflight.sql`). Re-running any of them cannot
restore `'aptitude'`.

Two adjacent facts worth recording, neither of which is a regression of *this* value:

- **`POST /subjects` and `POST /bulk-import` upsert on `slug`.** A future import carrying
  `slug='upsc-csat'` overwrites the live row's `subject_group` wholesale. Today no such artefact
  exists in the repo. If one is ever authored, it must carry `'reasoning'`.
- **The demo seed collides rather than clobbers.** `exam_intelligence_demo_upsc_cse.sql:100` is
  `on conflict (id) do nothing`, but its `slug='upsc-csat'` collides with the live row's unique
  slug on a *different* id — so applying that seed to production raises a unique violation; it
  does not silently rewrite the group. That seed is demo-only and must not be applied to
  production.

**The only way `'aptitude'` returns is an operator typing it again into an unvalidated text
box.** That is a UI/validation gap, not a write-path bug — see §5 for why it is not being
patched in this change.

---

## 3. Blast radius of flipping `'aptitude'` → `'reasoning'`

`family_for_subject(slug='upsc-csat', subject_group=…)`
(`app/backend/app/study_os/subject_runtime_policy.py:100`) goes from `None` to
`FAMILY_REASONING`. Note that the slug fallback does **not** currently rescue CSAT:
`upsc-csat` is absent from `_SLUG_FAMILY` (`:85`), which lists only
`general-intelligence-reasoning` and `reasoning` for the reasoning family.

### 3.1 Policy diff — `_GENERIC_POLICY` (`:398`) vs `FAMILY_REASONING` (`:374`)

| Field | Today (generic) | After (reasoning) | Changes? |
| --- | --- | --- | --- |
| `supported_modes` | `("objective_practice",)` | `("topic_practice","timed_practice","reasoning_set")` | **yes** (declarative only — no backend consumer; see 3.5) |
| `wired_runtime_modes` | `(english_writing, topic_pyq)` | `(topic_pyq, timed_practice)` | **yes** |
| `attempt_kind` | `mock_attempt` | `mock_attempt` | no |
| `mastery_enabled` | `True` | `True` | no |
| `correction_enabled` | `True` | `True` | no |
| `retry_policy` | `normal_srs` | `normal_srs` | no |
| `planner_resolver` | `_pyq_planner_resolver` | `_pyq_planner_resolver` | no |

### 3.2 Behaviour that changes for CSAT

1. **Subject hub gains "Timed practice."**
   `resolve_subject_modes` (`:417`) → `_emit_timed_practice` (`:239`) emits a
   `MODE_TIMED_PRACTICE` card whenever CSAT has ≥1 projected practiceable topic, targeting the
   same weakest topic as `topic_pyq`. Launch lands in `_handle_timed_practice`
   (`app/backend/app/api/subject_practice.py:121`), which is `_launch_topic_pyq` plus a
   server-frozen `duration_sec`. Same attempt shell, same route.

2. **Subject hub loses the latent "Sentence practice" card.**
   `_emit_english_writing` (`:227`) is gated on `ctx.eng_available`, which is
   per-subject: `str(subject_id) in available_writing_subject_ids(...)`
   (`app/backend/app/study_os/subjects.py:236,260` →
   `writing_practice/subject_launch.py:74`, verified+active prompts scoped to that
   `subject_id`). **This is the one thing that was passing only because CSAT is generic.**
   If any English writing prompt is scoped to `ce8d97ee`, that card disappears after the flip
   and `POST /subjects/ce8d97ee/practice/start {"mode":"english_writing"}` starts returning
   422 at the family gate (`subject_practice.py:96`). Verify before the flip:
   ```sql
   select count(*) from public.writing_prompts
   where subject_id = 'ce8d97ee-c1de-4ce2-a5ef-36d05c14d859'
     and reviewer_status = 'verified' and is_active = true;
   ```
   An English writing prompt on a CSAT subject would itself be a mis-scoped-content defect, so
   the expected count is 0 and the expected impact is nil — but this is the check that makes
   the flip safe rather than assumed-safe.

3. **Reasoning strategies scoped to CSAT topics become learner-reachable.**
   `reasoning_strategies._canonical_scope_is_reasoning` (`:118`) fails closed unless **every**
   populated scope dimension resolves to `FAMILY_REASONING`. Today every strategy whose
   `topic_id`/`microtopic_id` hangs off a CSAT topic is silently suppressed. After the flip they
   pass the scope gate. This is a **content-exposure change**: the strategies still have to be
   `reviewer_status='verified'` and `is_active`, and the linked question must be
   `verified|live|published`, but the volume that becomes visible is unknown until measured.
   Run `app/supabase/checks/reasoning_content_readiness_preflight.sql` **after** the update — it
   matches on `lower(sub.subject_group) = 'reasoning'`, so today it reports 0 for CSAT by
   construction, and its post-update delta *is* the exposure measurement. Its
   `v_ready_ignoring_scope` counter also flags any null-scoped or cross-subject links that would
   look ready but are correctly rejected.

4. **`ScoreSnapshotPanel` sectioning and labelling.**
   `app/frontend/src/pages/admin/exam-workspace/score-snapshots/ScoreSnapshotPanel.jsx:81-98`:
   CSAT snapshots currently land in a fall-through section title-cased to **"Aptitude"**, ranked
   after `gs`/`reasoning` and sorted alphabetically among the unknowns
   (`groupRank` returns `SUBJECT_GROUP_ORDER.length` for an unlisted group). After the flip they
   render under **"CSAT Paper II — Aptitude"** in the intended second position. Backend
   enrichment is `admin_exam_intelligence.py:2957-2974` (pass-through of
   `subjects.subject_group`). This is the fix the panel's own comment (`:74-79`) was written
   for. `ScoreSnapshotPanel.test.jsx:475,480` already fixtures `subject_group: "reasoning"`.

### 3.3 Behaviour that does **not** change

- **Planner launch stamping** — `planner.py:311,345,800` → `resolve_planner_launch` (`:428`).
  Both generic and reasoning use `_pyq_planner_resolver`, so `retrieval_practice`/`revision`
  tasks keep stamping `pyq_practice` byte-identically.
- **Mock readiness verdicts** — `exam_intelligence/diagnostics.py:782` resolves the family only
  to test `== FAMILY_GENERAL_AWARENESS` (`:779-806`). `None` and `reasoning` are both non-GA, so
  `no_locked_coverage` / `thin_mcq_pool` / `structural_only` are unaffected. The CSAT section's
  current `thin_bank` / `thin_mcq_pool` verdict
  (`app/backend/op0_readiness/upsc-cse_prelims_2026.json:98-103`) is a real content gap and
  stays exactly as it is.
- **Quant heuristics** — `quant_heuristics._canonical_scope_is_quant` (`:112`) requires
  `FAMILY_QUANT`; CSAT is neither before nor after.
- **`topic_pyq`** — wired in both policies; the hub card, target-topic selection
  (`_weakest_available_topic`, `:213`) and launch route are unchanged.
- **Mastery / SRS / correction** — identical flags in both policies.
- **Coverage and admin subject listings** — `exam_intelligence/coverage.py:149` and
  `api/admin_exam_intel_manage.py:230` select `subject_group` for display pass-through only.

### 3.4 Governance note

Item 3 is the one that needs an operator decision rather than just an operator command. Turning
on CSAT reasoning-strategy exposure is a **verified-content reveal**, and the repo's rule is
verified-only reads with defence in depth. Sequence it as: run the pre-`SELECT`, run the
`UPDATE`, then immediately run the reasoning preflight and read its
`ready_reachable` / `ready_ignoring_scope` counters before announcing the surface as correct.

### 3.5 `supported_modes` has no consumer

`supported_modes` is declared on every policy but is read nowhere outside
`subject_runtime_policy.py` (grep across `app/backend/app`: only `subject_practice.py` imports
`MODE_TIMED_PRACTICE`, and the launch gate checks `wired_runtime_modes`, not `supported_modes`).
The `("objective_practice",)` → `("topic_practice","timed_practice","reasoning_set")` change is
therefore inert today. Recorded so it is not mistaken for a live delta.

---

## 4. The other unmapped `subject_group` values in the wild

**Report only. No mapping change is proposed for any of these.**

| Value | Written by | Family resolved today | Correct? |
| --- | --- | --- | --- |
| `language` | `migrations/205_english_writing_practice_schema.sql:1060` — subject `english-language` | `FAMILY_ENGLISH` | **Yes, already correct.** `'language'` misses `_GROUP_FAMILY`, but the slug fallback `_SLUG_FAMILY["english-language"] = FAMILY_ENGLISH` (`:89`) catches it. No behavioural bug. Adding `'language'` to `_GROUP_FAMILY` would be defence-in-depth against a future slug rename only — not needed now, and it would put Python ahead of the SQL preflights, which key on the slug list too. |
| `social_science` | `seeds/e2e_workspace_fixtures.sql:32` and `app/frontend/e2e/fixtures/seedWorkspace.ts:84` — subject `e2e-polity` | `None` → `_GENERIC_POLICY` | **Yes, correct as-is.** E2E-fixture-only; never in production. A polity subject is a PYQ-backed GS-type subject, and generic is exactly the intended runtime — the same treatment UPSC `gs` gets by design (`subject_runtime_policy.py:70-72` states `gs` is *deliberately* unmapped). It does not belong in `_GROUP_FAMILY`: none of `quant`/`english`/`reasoning`/`general_awareness` fits it, and mapping it to GA would wrongly disable mastery and PYQ. |
| `gs` | `seeds/exam_intelligence_demo_upsc_cse.sql:95-98` | `None` → `_GENERIC_POLICY` | **Yes, by explicit design** (`subject_runtime_policy.py:70-72`). Listed for completeness. |
| `GS_1` … `GS_4` | `scripts/ingest_upsc_gs_syllabus.py:164,319` — subjects `upsc-cse-mains-gs1..gs4` | `None` → `_GENERIC_POLICY` | **Correct runtime, sloppy vocabulary.** These are UPSC Mains GS papers and generic is the right policy, so behaviour is fine. But the script writes the raw `paper_id` (`'GS_1'`, underscore, uppercase) as the governed group, which is a fourth spelling of "GS" alongside the seed's `'gs'`. That is a taxonomy-hygiene item for the ingest script, not a family-mapping item — flagged, not changed. |

**Conclusion for §4:** none of the values in the wild needs to be added to `_GROUP_FAMILY`.
`'aptitude'` is the only one whose family resolution is actually wrong, and its fix is the data,
not the map.

---

## 5. Code changes: none, and why

Three candidate changes were considered against the "code changes only if…" bar. All three are
rejected:

1. **Add `"aptitude": FAMILY_REASONING` to `_GROUP_FAMILY`.** Rejected. It would fix the Python
   runtime while leaving `app/supabase/checks/reasoning_content_readiness_preflight.sql` and
   `app/supabase/validation/validate_reasoning_strategy_readiness.sql` — which match
   `lower(sub.subject_group) = 'reasoning'` literally — still blind to CSAT. The result is a
   split brain in which reasoning strategies are learner-reachable but the readiness gate reports
   them as absent. That is strictly worse than today's consistent-but-wrong state, and it
   legitimises a non-canonical value the repo has never accepted. `'reasoning'` is the canonical
   token; the row should carry it.

2. **Add `"upsc-csat": FAMILY_REASONING` to `_SLUG_FAMILY`.** Rejected for the same split-brain
   reason — the SQL slug allowlists are `('general-intelligence-reasoning','reasoning')`. It is
   also solving a problem the data fix removes.

3. **Constrain `subject_group` on the CMS write paths (enum validation, or a `CHECK`).**
   Rejected as out of scope here. It is the correct long-term guard against a re-typo, but it is
   a behaviour change on four endpoints, it would reject the values already live in production
   (`gs`, `social_science`, `GS_1`…`GS_4`), and a `CHECK` constraint requires a migration —
   explicitly excluded from this task. Recorded below as follow-up work.

**Follow-up work (not in this change):**

- Turn `subject_group` into a governed vocabulary: an `options` list on
  `ExamIntelCms.jsx` `ENTITY_CONFIG.subjects.fields`, plus an `enums` entry in
  `_IMPORT_CONFIG["subjects"]` and `_BULK_EDIT_CONFIG["subjects"]`, so an operator cannot invent
  a group. Requires first reconciling the values already live (`gs`, `social_science`,
  `GS_1`…`GS_4`).
- Normalise `scripts/ingest_upsc_gs_syllabus.py` to write a canonical group rather than the raw
  `paper_id`.
- Add the canonical group vocabulary to the CMS field help text as an interim, zero-risk guard.

---

## 6. Operator instructions

Run against production, in this order. **Do not** wrap these in a migration — the target row is
a production-only row that no migration is allowed to assume exists.

### Step 1 — pre-check (must return exactly one row, `subject_group = 'aptitude'`)

```sql
select id, slug, name, subject_group, is_active, updated_at
from public.subjects
where id = 'ce8d97ee-c1de-4ce2-a5ef-36d05c14d859';
```

Also confirm the English-writing exposure noted in §3.2(2) is nil (expected: `0`):

```sql
select count(*) as writing_prompts_on_csat
from public.writing_prompts
where subject_id = 'ce8d97ee-c1de-4ce2-a5ef-36d05c14d859'
  and reviewer_status = 'verified'
  and is_active = true;
```

**Abort** if the pre-check returns 0 rows, or a `subject_group` other than `'aptitude'` — the
row has already been changed by someone else and this document is stale.

### Step 2 — the update (one row, guarded)

```sql
update public.subjects
set subject_group = 'reasoning',
    updated_at = now()
where id = 'ce8d97ee-c1de-4ce2-a5ef-36d05c14d859'
  and subject_group = 'aptitude';
```

The `and subject_group = 'aptitude'` predicate makes the statement idempotent and makes a
re-run a no-op rather than a blind overwrite. Expect `UPDATE 1`.

### Step 3 — post-check (same row, `subject_group = 'reasoning'`)

```sql
select id, slug, name, subject_group, is_active, updated_at
from public.subjects
where id = 'ce8d97ee-c1de-4ce2-a5ef-36d05c14d859';
```

### Step 4 — measure the reasoning-content exposure opened by §3.2(3)

Run `app/supabase/checks/reasoning_content_readiness_preflight.sql` and record
`ready_questions`, `ready_reachable`, and `ready_ignoring_scope`. A positive
`ready_ignoring_scope − ready_questions` delta means there are null-scoped or cross-subject
strategy links that the real gate correctly rejects — content to re-scope, not a pass.

### Step 5 — sweep for any other ungoverned group (informational)

```sql
select subject_group, count(*) as subjects, array_agg(slug order by slug) as slugs
from public.subjects
where is_active = true
group by subject_group
order by subjects desc;
```

Cross-check the result against §4. Any value not in
`{gs, numerical, quantitative, verbal, english, reasoning, general-awareness, general_awareness,
current-affairs, language, social_science, GS_1..GS_4, null}` is a new unmapped value and needs
the same analysis this document performs.

### Evidence

This is an operator action against a live database. Per the operator-validation rules, code
inspection is not validation: capture the Step 1 / Step 3 / Step 4 outputs as evidence and keep
any associated gate at `validation_pending` until that live proof exists.
