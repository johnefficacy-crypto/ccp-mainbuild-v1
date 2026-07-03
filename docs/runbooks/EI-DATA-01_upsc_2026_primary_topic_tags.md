# EI-DATA-01 — UPSC 2026 primary topic-tag completion

**Type:** Operator / data-review task (SME judgment + live Supabase). Not a code change.
**Goal:** Every usable SME-verified UPSC-2026 PYQ question carries **exactly one** verified
`primary` topic tag, so the PYQ→Mock projection gate clears. Expected result: **98 questions
projection-eligible**; the **2 rejected** questions stay excluded.

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
   `_check_question_eligibility()` requires **exactly one** tag with
   `tag_role='primary'` **AND** `reviewer_status='verified'`
   (`not_exactly_one_verified_primary_tag:<n>` is raised when the count ≠ 1).

The relevant tables (schema `public`, migration `032_pyq_question_intelligence.sql`):

| Table | Columns that matter here |
|---|---|
| `pyq_papers` | `id`, `exam_id`, `year`, `trust_status ∈ (pending, verified, rejected)` |
| `pyq_questions` | `id`, `pyq_paper_id`, `reviewer_status`, `question_type` |
| `pyq_question_topic_tags` | `id`, `question_id`, `topic_id → topics.id`, `tag_role`, `reviewer_status`, `tag_weight`, `tagging_source`; **`UNIQUE(question_id, topic_id, tag_role)`** |
| `topics` | `id` — the syllabus topic the tag points at |

`tag_role ∈ (primary, secondary, prerequisite, trap, calculation_layer, conceptual_layer)`.
Only `primary` counts for the projection gate; `secondary` / `trap` etc. are separate roles and
do **not** substitute.

---

## Phase 0 — Scope & preflight (read-only)

Run everything in Phase 0 before touching a single row. Capture the counts — they are your
before/after evidence.

### 0.1 Resolve the exam + set a reusable scope

Confirm the UPSC exam id and the paper set. Adjust the `WHERE` to match how UPSC 2026 is modelled
(by `pyq_papers.year = 2026`, or by the exam's 2026 cycle — verify against the workbench before
trusting a single filter).

```sql
-- Identify the exam. Replace the name filter with the real UPSC exam identity if it differs.
SELECT id AS exam_id, name, slug
FROM public.exams
WHERE name ILIKE '%UPSC%'
ORDER BY name;
```

Set the resolved id below and reuse the CTE in every query:

```sql
-- :UPSC_EXAM_ID  = '<paste exam_id from 0.1>'
WITH scope_papers AS (
  SELECT p.id
  FROM public.pyq_papers p
  WHERE p.exam_id = :UPSC_EXAM_ID
    AND p.year = 2026
    AND p.trust_status = 'verified'   -- gate 1: only verified papers can ever project
)
SELECT count(*) AS verified_upsc_2026_papers FROM scope_papers;
```

### 0.2 Confirm the target set (the 98) and the 2 excluded rejects

```sql
-- :UPSC_EXAM_ID as above
WITH scope_papers AS (
  SELECT p.id FROM public.pyq_papers p
  WHERE p.exam_id = :UPSC_EXAM_ID AND p.year = 2026 AND p.trust_status = 'verified'
),
q AS (
  SELECT
    qn.id,
    qn.reviewer_status,
    (
      SELECT count(*) FROM public.pyq_question_topic_tags t
      WHERE t.question_id = qn.id
        AND t.tag_role = 'primary'
        AND t.reviewer_status = 'verified'
    ) AS verified_primary_tags
  FROM public.pyq_questions qn
  JOIN scope_papers sp ON sp.id = qn.pyq_paper_id
)
SELECT
  count(*) FILTER (WHERE reviewer_status = 'verified' AND verified_primary_tags = 0) AS needs_tag,          -- expect 98
  count(*) FILTER (WHERE reviewer_status = 'verified' AND verified_primary_tags = 1) AS already_ok,          -- expect 0 at start
  count(*) FILTER (WHERE reviewer_status = 'verified' AND verified_primary_tags > 1) AS over_tagged,         -- expect 0; if >0 see Phase 1 note
  count(*) FILTER (WHERE reviewer_status = 'rejected') AS rejected_excluded                                   -- expect 2, DO NOT touch
FROM q;
```

> If `needs_tag` ≠ 98 or `rejected_excluded` ≠ 2, **stop** and reconcile scope with the workbench
> before proceeding — the checklist figure assumes a specific paper set.

### 0.3 The worklist the SME will tag

This is the per-question list. `existing_primary` surfaces any pending/needs_correction primary
tag already present (reuse it, don't create a duplicate).

```sql
-- :UPSC_EXAM_ID as above
WITH scope_papers AS (
  SELECT p.id FROM public.pyq_papers p
  WHERE p.exam_id = :UPSC_EXAM_ID AND p.year = 2026 AND p.trust_status = 'verified'
)
SELECT
  qn.id            AS question_id,
  left(qn.question_text, 90) AS question_preview,
  (SELECT jsonb_agg(jsonb_build_object('tag_id', t.id, 'topic_id', t.topic_id, 'status', t.reviewer_status))
     FROM public.pyq_question_topic_tags t
    WHERE t.question_id = qn.id AND t.tag_role = 'primary') AS existing_primary_tags
FROM public.pyq_questions qn
JOIN scope_papers sp ON sp.id = qn.pyq_paper_id
WHERE qn.reviewer_status = 'verified'
  AND NOT EXISTS (
    SELECT 1 FROM public.pyq_question_topic_tags t
    WHERE t.question_id = qn.id AND t.tag_role = 'primary' AND t.reviewer_status = 'verified'
  )
ORDER BY qn.pyq_paper_id, qn.id;
```

---

## Phase 1 — Assign one verified primary tag per question (SME, per row)

For **each** question in the 0.3 worklist. Do **not** batch-verify — each tag is reviewed on its
own so `reviewed_by` / `reviewed_at` are truthful.

**Prefer the admin API** (it enforces validation, writes the audit trail, and keeps the review
lifecycle intact). Direct SQL is the fallback for a controlled operator session only.

### 1a. Choose the topic (SME judgement)

Read the question, map it to the single best-fitting `topics.id`. This is the human step the
gate exists to protect — there is no automation for it.

### 1b. Create the primary tag (pending)

```
POST /admin/exam-intelligence/pyq-question-topic-tags
{
  "payload": {
    "question_id":   "<question_id>",
    "topic_id":      "<chosen topics.id>",
    "tag_role":      "primary",
    "tagging_source":"admin",
    "tag_weight":    1
  }
}
```

Handler: `create_pyq_question_topic_tag` (`admin_exam_intel_cms.py`). Row lands
`reviewer_status='pending'`. If a pending primary tag already exists for the *same topic*, the
`UNIQUE(question_id, topic_id, tag_role)` constraint will reject a duplicate — reuse the existing
tag id instead.

### 1c. Verify the tag (pending → verified)

```
PATCH /admin/exam-intelligence/items/pyq_question_topic_tag/<tag_id>/review
{ "reviewer_status": "verified" }
```

Handler: `review_item` (`admin_exam_intelligence.py`) → updates only the **tag** row
(`reviewed_by`, `reviewed_at`, `reviewer_status`). It never touches `pyq_questions`, so the SME
question verification is preserved.

**Exactly-one invariant:** the projection gate needs the verified-primary count to equal `1`, not
`≥1`. If Phase 0.2 reported `over_tagged > 0`, or a question already had a verified primary on a
different topic, resolve to a single primary — demote the extras to `secondary` (PATCH the
`tag_role`) or set their `reviewer_status='rejected'`. Two verified primaries fail the gate just
as hard as zero.

### Direct-SQL fallback (operator session only, one question at a time)

```sql
-- Create (pending):
INSERT INTO public.pyq_question_topic_tags
  (question_id, topic_id, tag_role, tagging_source, tag_weight, reviewer_status)
VALUES ('<question_id>', '<topic_id>', 'primary', 'admin', 1, 'pending')
ON CONFLICT (question_id, topic_id, tag_role) DO NOTHING
RETURNING id;

-- Verify (pending -> verified). Scope the UPDATE to the single tag id from the INSERT:
UPDATE public.pyq_question_topic_tags
SET reviewer_status = 'verified', reviewed_by = '<operator_profile_id>', reviewed_at = now()
WHERE id = '<tag_id>';
```

> The `WHERE id = '<tag_id>'` scoping is what keeps this from being a "bulk status update." Never
> run the verify UPDATE against a set of rows.

---

## Phase 2 — Postflight verification (read-only)

### 2.1 The count contract

Re-run **0.2**. Expect: `needs_tag = 0`, `already_ok = 98`, `over_tagged = 0`,
`rejected_excluded = 2` (unchanged).

### 2.2 Question verification untouched

Confirm no SME question verdict changed as a side effect:

```sql
-- :UPSC_EXAM_ID as above — rejected set must still be exactly the same 2 rows.
WITH scope_papers AS (
  SELECT p.id FROM public.pyq_papers p
  WHERE p.exam_id = :UPSC_EXAM_ID AND p.year = 2026 AND p.trust_status = 'verified'
)
SELECT reviewer_status, count(*)
FROM public.pyq_questions qn
JOIN scope_papers sp ON sp.id = qn.pyq_paper_id
GROUP BY reviewer_status
ORDER BY reviewer_status;
-- Expect: verified = 98 (+ any that were already ok), rejected = 2. No change vs Phase 0.
```

### 2.3 Projection preview agrees (end-to-end proof)

The counts above prove the tag gate; this proves the *whole* projection chain. For each affected
paper, run the preview dry-run (no writes) and confirm `eligible_count` rose by the number of
questions you tagged on that paper:

```
GET  /admin/pyq/papers/<paper_id>/projection/preview     (preview_paper_projection)
```

`reason` should no longer contain `not_exactly_one_verified_primary_tag` for the tagged
questions. Any remaining ineligibles should be blocked on a *different* gate (options / correct
answer), not on the primary tag. Only then is it safe to Sync.

---

## Done / status

- Update `docs/status/career-copilot-checklist.md` EI-DATA-01 row to
  `VERIFY DB` → `MERGED` (data) only after Phase 2 is captured against the **live** DB with real
  counts — never from this document alone (`CLAUDE.md`: operator/Supabase steps are not complete
  from code inspection).
- Attach the Phase 0 and Phase 2 count outputs as the evidence pair.
