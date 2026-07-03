# EI-DATA-01 — UPSC 2026 primary topic-tag completion

**Type:** Operator / data-review task (SME judgment + live Supabase). Not a code change.
**Goal:** Every usable SME-verified UPSC PYQ question that currently blocks the PYQ→Mock
projection **only** on the missing-primary-tag gate carries **exactly one** verified `primary`
topic tag. Expected result: the **98** target questions become projection-eligible; the **2
rejected** questions stay excluded.

Why this is a runbook and not a migration: assigning the *correct* topic per question is SME
judgement, and it must go through the tag review lifecycle one row at a time. **No bulk
`UPDATE ... SET reviewer_status='verified'`** — that would fabricate review and is explicitly
prohibited (`CLAUDE.md` → verified-only reads; checklist EI-DATA-01: "no bulk status update").

---

## The contract you are satisfying

Two independent gates read topic tags. Assigning **exactly one verified `primary` tag** per
question clears both:

1. **PYQ readiness three-gate** — `app/backend/app/exam_intelligence/pyq_readiness.py`
   (verified paper + verified question + **≥1 verified tag of any role**).
2. **PYQ→Mock projection eligibility** — `app/backend/app/admin/pyq_mock_projection.py`
   `_check_question_eligibility()`. **The primary-tag gate is one of eight checks.** A question
   projects only when ALL of these hold:
   - `pyq_papers.trust_status = 'verified'`
   - `pyq_questions.reviewer_status = 'verified'`
   - `question_type = 'mcq'`
   - non-empty `question_text`
   - ≥ 2 verified `pyq_options` (`reviewer_status='verified'`)
   - every verified option has non-empty `option_text`
   - **exactly one** verified option with `is_correct = true`, and it matches
     `pyq_questions.correct_option_id` when that column is set
   - **exactly one** `pyq_question_topic_tags` row with `tag_role='primary'` AND
     `reviewer_status='verified'` (else `not_exactly_one_verified_primary_tag:<n>`)

EI-DATA-01 only fixes the last gate. Phase 0 therefore has to **prove** each target row is blocked
*only* by that gate — otherwise tagging it will not make it projection-eligible and the "98"
outcome is not real.

Tables (schema `public`, migration `032_pyq_question_intelligence.sql`):

| Table | Columns that matter here |
|---|---|
| `pyq_papers` | `id`, `exam_id`, `year`, `trust_status ∈ (pending, verified, rejected)` |
| `pyq_questions` | `id`, `pyq_paper_id`, `reviewer_status`, `question_type`, `correct_option_id` |
| `pyq_options` | `id`, `question_id`, `reviewer_status`, `is_correct`, `option_text` |
| `pyq_question_topic_tags` | `id`, `question_id`, `topic_id → topics.id`, `tag_role`, `reviewer_status`, `tag_weight`, `tagging_source`; **`UNIQUE(question_id, topic_id, tag_role)`** |
| `topics` | `id` — the syllabus topic the tag points at |

`tag_role ∈ (primary, secondary, prerequisite, trap, calculation_layer, conceptual_layer)`.
Only `primary` counts for the projection gate; other roles do **not** substitute.

---

## API surface (exact mounted paths + contracts)

Global prefix is `/api` (`app/backend/server.py:258` → `api = APIRouter(prefix="/api")`). All three
routers mount under it. Permissions are enforced per route; the CMS router is additionally gated on
the `ADMIN_STUDY_OS_ENABLED` feature flag (`_flag_enabled` → 404 when off).

| Action | Method + path | Permission / flag | Body |
|---|---|---|---|
| Create topic tag | `POST /api/admin/exam-intelligence-cms/pyq-question-topic-tags` | `exam_intelligence.cms` + `ADMIN_STUDY_OS_ENABLED` | `WriteEnvelope`: `{ "reason": <8–500 chars>, "payload": {…} }` |
| Re-role a tag (demote extra primary) | `PATCH /api/admin/exam-intelligence-cms/pyq-question-topic-tags/{tag_id}` | `exam_intelligence.cms` + flag | `WriteEnvelope`: `{ "reason": …, "payload": { "tag_role": "secondary" } }` |
| Verify / reject a tag | `PATCH /api/admin/exam-intelligence/items/pyq_question_topic_tag/{tag_id}/review` | `exam_intelligence.review` | `{ "reviewer_status": "verified" }` |
| Projection preview (dry-run) | `GET /api/admin/mocks/pyq-papers/{paper_id}/projection/preview` | `mock_questions:author` | — |
| Projection sync | `POST /api/admin/mocks/pyq-papers/{paper_id}/projection/sync` | `mock_questions:author` | (see handler) |

`WriteEnvelope` (`admin_exam_intel_cms.py:119-123`) rejects a request with a missing/short `reason`
(422) — the envelope is mandatory, not optional. Executable example for the create step:

```bash
curl -sS -X POST "$BASE/api/admin/exam-intelligence-cms/pyq-question-topic-tags" \
  -H "Authorization: Bearer $ADMIN_JWT" -H "Content-Type: application/json" \
  -d '{
        "reason": "EI-DATA-01: assign verified primary topic tag to SME-reviewed UPSC PYQ question",
        "payload": {
          "question_id": "<question_id>",
          "topic_id":    "<chosen topics.id>",
          "tag_role":    "primary",
          "tagging_source": "admin",
          "tag_weight":  1
        }
      }'
# → 201 with the new tag row (reviewer_status defaults to "pending").

# Then verify that specific tag id (review router has NO WriteEnvelope):
curl -sS -X PATCH \
  "$BASE/api/admin/exam-intelligence/items/pyq_question_topic_tag/<tag_id>/review" \
  -H "Authorization: Bearer $ADMIN_JWT" -H "Content-Type: application/json" \
  -d '{ "reviewer_status": "verified" }'
# → 200; updates only the tag row (reviewed_by/reviewed_at/reviewer_status). pyq_questions untouched.
```

---

## Phase 0 — Establish the canonical target set from live evidence (read-only)

**Do not scope by `pyq_papers.year` or `exam_cycle_id`.** D10 locks PYQ readiness as *exam-wide
historical evidence*; `year`/`exam_cycle_id` are provenance, not the readiness boundary. Scoping by
year risks selecting the wrong or empty corpus. Instead, derive the target question IDs from what
the operator surface actually flags, freeze them into one temp table, and reuse those exact IDs
through mutation and postflight.

### 0.1 Resolve the exam

```sql
SELECT id AS exam_id, name, slug
FROM public.exams
WHERE name ILIKE '%UPSC%'
ORDER BY name;
-- Set :UPSC_EXAM_ID = '<the row that matches the workbench exam identity>'.
```

### 0.2 Freeze the target IDs (exam-wide, evidence-driven — not year-filtered)

The target is: questions on **verified** papers for this exam, `reviewer_status='verified'`, whose
verified-`primary` count is `0`. Capture them once.

```sql
CREATE TEMP TABLE ei_data_01_targets AS
SELECT qn.id AS question_id, qn.pyq_paper_id
FROM public.pyq_questions qn
JOIN public.pyq_papers p ON p.id = qn.pyq_paper_id
WHERE p.exam_id = :UPSC_EXAM_ID
  AND p.trust_status = 'verified'          -- gate 1 (exam-wide; NO year/cycle filter)
  AND qn.reviewer_status = 'verified'      -- gate 2
  AND NOT EXISTS (                          -- missing the verified primary tag
    SELECT 1 FROM public.pyq_question_topic_tags t
    WHERE t.question_id = qn.id AND t.tag_role = 'primary' AND t.reviewer_status = 'verified'
  );

SELECT count(*) AS target_count FROM ei_data_01_targets;   -- must equal 98
```

Also snapshot the excluded rejects so Phase 2 can prove they were untouched:

```sql
CREATE TEMP TABLE ei_data_01_rejected AS
SELECT qn.id AS question_id
FROM public.pyq_questions qn
JOIN public.pyq_papers p ON p.id = qn.pyq_paper_id
WHERE p.exam_id = :UPSC_EXAM_ID AND p.trust_status = 'verified'
  AND qn.reviewer_status = 'rejected';

SELECT count(*) AS rejected_count FROM ei_data_01_rejected;  -- must equal 2
```

> **Stop condition for 0.2:** `target_count = 98` AND `rejected_count = 2`, AND those IDs are the
> same rows the workbench/readiness surface reports as "verified, not planner-ready". If either
> count differs, reconcile scope with the operator surface before proceeding — the "98/2" figure is
> the checklist's, and the temp table must reproduce it, not a year heuristic.

### 0.3 Prove the target rows are blocked ONLY by the primary-tag gate

Tagging a row only helps if the primary tag is its *sole* blocker. Run the projection preview per
affected paper and collect the reason per target question:

```
GET /api/admin/mocks/pyq-papers/{paper_id}/projection/preview   (for each distinct pyq_paper_id in ei_data_01_targets)
```

For every target `question_id`, the preview `reason` MUST be exactly
`not_exactly_one_verified_primary_tag:0`. Record the reason distribution.

- If all 98 report only that reason → tagging all 98 yields 98 eligible. Proceed.
- If any target row reports a *different* blocker (options / correct answer / text / not_mcq),
  that row will **not** become eligible from tagging alone. **Re-scope**: either exclude it from
  EI-DATA-01 (record the independent blocker as separate follow-up) or fix that blocker under its
  own task. Do not carry it into the "98 eligible" claim.

---

## Phase 1 — Assign one verified primary tag per question (SME, per row)

For **each** `question_id` in `ei_data_01_targets`. Do **not** batch-verify — each tag is reviewed
on its own so `reviewed_by` / `reviewed_at` are truthful. **Use the admin API** (validation,
feature-flag gate, and `admin_audit_logs` write); it is the supported path.

1. **Choose the topic (SME judgement).** Read the question, map it to the single best-fitting
   `topics.id`. This is the human step the gate exists to protect — there is no automation for it.
2. **Create the primary tag (pending).** `POST …/exam-intelligence-cms/pyq-question-topic-tags`
   with the `WriteEnvelope` shown above. Handler `create_pyq_question_topic_tag`. Lands
   `reviewer_status='pending'`. If a pending primary tag on the *same topic* already exists, the
   `UNIQUE(question_id, topic_id, tag_role)` constraint blocks the duplicate — reuse that tag id.
3. **Verify the tag (pending → verified).** `PATCH …/exam-intelligence/items/pyq_question_topic_tag/{tag_id}/review`
   `{ "reviewer_status": "verified" }`. Handler `review_item` updates only the tag row, so SME
   question verification is preserved.

**Exactly-one invariant.** The gate needs the verified-primary count to equal `1`, not `≥1`. Two
verified primaries fail the gate as hard as zero. If a question already has (or gains) a second
verified primary on a different topic, demote the extra to `secondary` via the CMS PATCH with a
`reason` envelope:

```bash
curl -sS -X PATCH \
  "$BASE/api/admin/exam-intelligence-cms/pyq-question-topic-tags/<extra_tag_id>" \
  -H "Authorization: Bearer $ADMIN_JWT" -H "Content-Type: application/json" \
  -d '{ "reason": "EI-DATA-01: keep a single primary; demote redundant primary to secondary",
        "payload": { "tag_role": "secondary" } }'
```

> **Direct SQL is not recommended** for this task and is intentionally omitted: an ad-hoc
> `INSERT ... ON CONFLICT DO NOTHING RETURNING id` returns no id on conflict (so a follow-up verify
> `UPDATE` has nothing to target), and it bypasses the CMS feature-flag/permission path and the
> `admin_audit_logs` create record. Use the API. If a controlled operator SQL session is
> unavoidable, it must run in one transaction, `SELECT ... FOR UPDATE` the existing tag id on
> conflict, assert `question_id`/`topic_id` ownership and exam scope, scope the verify `UPDATE` to
> that single `id`, and write an equivalent audit row — anything less is a prohibited bulk update.

---

## Phase 2 — Postflight verification (read-only, same frozen IDs)

### 2.1 Every target now has exactly one verified primary

```sql
SELECT
  count(*) FILTER (WHERE vp = 1) AS ok,          -- must equal 98
  count(*) FILTER (WHERE vp = 0) AS still_missing,-- must equal 0
  count(*) FILTER (WHERE vp > 1) AS over_tagged   -- must equal 0
FROM (
  SELECT tg.question_id,
         (SELECT count(*) FROM public.pyq_question_topic_tags t
           WHERE t.question_id = tg.question_id
             AND t.tag_role = 'primary' AND t.reviewer_status = 'verified') AS vp
  FROM ei_data_01_targets tg
) s;
```

### 2.2 SME question verdicts untouched

```sql
-- Targets must all still be 'verified'; rejects must still be exactly the same 2 rows.
SELECT
  (SELECT count(*) FROM public.pyq_questions q JOIN ei_data_01_targets t ON t.question_id=q.id
     WHERE q.reviewer_status <> 'verified') AS targets_changed,   -- must be 0
  (SELECT count(*) FROM public.pyq_questions q JOIN ei_data_01_rejected r ON r.question_id=q.id
     WHERE q.reviewer_status <> 'rejected') AS rejects_changed;   -- must be 0
```

### 2.3 Projection preview proves eligibility end-to-end

Re-run `GET /api/admin/mocks/pyq-papers/{paper_id}/projection/preview` for each affected paper.
Every one of the frozen 98 target IDs must now be `eligible=true` (`reason='eligible'`), with no
remaining `not_exactly_one_verified_primary_tag`. Only then is it safe to Sync. Any target row that
is still ineligible for a *different* reason means Phase 0.3 was not enforced — re-scope it out of
the "98 eligible" claim rather than marking EI-DATA-01 complete.

---

## Done / status

- Mark `docs/status/career-copilot-checklist.md` EI-DATA-01 `MERGED` (data) only after Phase 2 is
  captured against the **live** DB with real counts — never from this document alone (`CLAUDE.md`:
  operator/Supabase steps are not complete from code inspection).
- Attach the Phase 0 (0.2 counts + 0.3 reason distribution) and Phase 2 (2.1/2.2/2.3) outputs as
  the evidence pair. The stop condition is: the same frozen 98 IDs that were blocked only by
  `not_exactly_one_verified_primary_tag:0` are now `eligible`, and the 2 rejects are unchanged.
