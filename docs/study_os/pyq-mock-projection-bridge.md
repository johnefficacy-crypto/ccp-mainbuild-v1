# PYQ Workbench → Mock Engine Projection Bridge

**Status:** Implemented (migration 183, backend service, frontend panel)  
**Migration:** `183_pyq_mock_projection_bridge.sql`  
**PR slice:** A0 (projection bridge) — Track C, prerequisite to PR-7

---

## Overview

The projection bridge allows verified PYQ (Past Year Question) content to flow
into the live mock question bank without manual re-entry.  A publisher action
in the PYQ Workbench triggers an atomic, idempotent DB function that copies
content to `mock_question_bank` and records a stable lineage link.

## Canonical authority

- **Source of truth:** `pyq_papers`, `pyq_questions`, `pyq_options`, `pyq_question_topic_tags`
- **Projection:** `mock_question_bank` rows derived from PYQ content
- **Lineage table:** `pyq_mock_question_projections` (one row per pyq_question)

## Eligibility rules

A PYQ question is eligible for projection when ALL of the following hold:

| Condition | Why |
|-----------|-----|
| `pyq_papers.trust_status = 'verified'` | Paper provenance must be verified |
| `pyq_questions.reviewer_status = 'verified'` | Question reviewed and approved |
| `pyq_questions.question_type = 'mcq'` | Only MCQ supported in mock engine |
| `question_text` not empty | No blank questions |
| ≥ 2 **verified** `pyq_options` | Minimum selector options (verified only) |
| Every verified option has non-empty `option_text` | No blank option text |
| Exactly 1 **verified** `pyq_options.is_correct = true` | MCQ invariant (verified only) |
| If `pyq_questions.correct_option_id` is non-null, it must match the verified correct option | Pointer consistency |
| Exactly 1 verified `pyq_question_topic_tags` with `tag_role = 'primary'` | Topic routing |
| `topics.subject_id` not null | Subject must be resolvable |

## Idempotency

One `pyq_question_id` maps to at most one `mock_question_id` (unique constraint
on `pyq_mock_question_projections.pyq_question_id`).  Re-syncing the same
question with unchanged content is a no-op (hash match → `outcome: unchanged`).
Content changes produce `outcome: updated`.

## Content hash

```
SHA256(
  lower(strip(question_text)) + chr(0) +
  sorted_verified_option_texts joined by chr(0) +
  chr(0) +
  lower(strip(verified_correct_option_text))
)
```

Only **verified** options are included in the hash.  `chr(0)` (NUL) is the
only separator — no `chr(1)` sentinel.  The Python `compute_content_hash()`
in `pyq_mock_projection.py` and the SQL hash in migration 183 section 3
must always use identical formulas.

## Invalidation triggers

When canonical content changes, the projection is automatically downgraded
(implemented via `fn_invalidate_projection_for_question` shared helper):

| Trigger event | Effect |
|---------------|--------|
| `pyq_questions` reviewer_status leaves 'verified' | projection → stale, mock bank → draft |
| `pyq_papers` trust_status leaves 'verified' | all paper projections → stale, mock bank → draft |
| `pyq_papers` exam_phase_id changes | all paper projections → stale, mock bank → draft |
| `pyq_options` INSERT, DELETE, or material UPDATE | projection → stale, mock bank → draft |
| `pyq_question_topic_tags` primary tag INSERT/DELETE/UPDATE | projection → stale, mock bank → draft |

After a projection goes stale, the mock bank row's `reviewer_status` is
downgraded to `draft` so it falls out of the selectable pool until the
operator re-syncs.

## Security

The SECURITY DEFINER RPC `project_pyq_question_to_mock_bank` is:
- Callable only by `service_role` (REVOKE from public/anon/authenticated)
- All writes go through this single function
- All projections are logged in `admin_audit_logs` and `mock_question_review_log`

## Source-type fields

Projected questions always have:
- `source_type = 'pyq'` — mastery weighting signal
- `source_kind = 'pyq'` — selector/diagnostic compatibility

Both fields are required; using only one would break either mastery write-back
or question selection.

## API endpoints

Mount: `/api/admin/mocks/pyq-papers/{paper_id}/projection/`

| Method | Path | Permission | Description |
|--------|------|------------|-------------|
| GET | `/preview` | author | Dry-run — which questions would sync |
| POST | `/sync` | publisher | Execute projection |
| GET | `/status` | author | Aggregated projection state |

### POST `/sync` request body

```json
{
  "audit_reason": "string (required, 8–500 chars)",
  "question_ids": ["uuid", "..."]
}
```

`audit_reason` is **required** (min 8, max 500 characters).  Requests without
it return HTTP 422.  `question_ids` is optional; omit to sync all eligible
questions in the paper.

### POST `/sync` response notes

- HTTP 200: normal result (per-question `outcome` values: `projected`, `updated`,
  `unchanged`, `ineligible`, `skipped`)
- HTTP 409: one or more questions had a fingerprint conflict — another row in
  `mock_question_bank` has the same content hash but a different lineage.  The
  response body contains `error: "fingerprint_conflict"` and the conflicting
  `question_id`.

## Active-lineage guard

The selector layer (`diagnostics.py` `selectable_mcq_depth` and
`mock_blueprint_selection.py` `_exam_base_pool`) applies a Python-layer safety
check: any question whose `pyq_question_id` is set but has no `active` row in
`pyq_mock_question_projections` is excluded from the pool before the blueprint
runs.  This prevents stale projected questions from being served after an
invalidation trigger fires and before the operator re-syncs.

## Frontend surface

The projection panel is embedded inside the existing **PYQ Workbench** panel
(`PyqWorkbenchPanel.jsx`) as a collapsible section below the paper workspace.
No new route or sidebar entry is created (no-new-surface rule).

## Frozen attempt provenance

When a projected question is included in a mock attempt, the
`_question_snapshot` in `mock_engine.py` now freezes:

```json
{
  "exam_id": "...",
  "subject_id": "...",
  "source_kind": "pyq",
  "pyq_year": 2023,
  "pyq_question_id": "...",
  "pyq_paper_id": "..."
}
```

This ensures mastery write-back and the `multi-exam-coverage` shadow validator
can identify PYQ provenance from the frozen attempt record without re-reading
the live bank.

## Source-mix policy

The `mock_source_mix_policies` table (added in migration 183) allows operators
to configure target ratios of `pyq` vs `authored` questions per exam/phase/
subject/topic scope.  The policy resolver uses a scope hierarchy
(topic > subject > phase > exam) and feeds into the relaxation ladder in
`mock_blueprint_selection.py`.

## UPSC CSAT readiness

The projection bridge is the prerequisite for onboarding UPSC CSAT questions.
No CSAT data should be ingested until the bridge is live on production and
migration 183 is confirmed.  See
`docs/engineering/exam-intelligence-data-fill-runbook.md` for the CSAT
operator runbook.

## Open constraints

- Do NOT flip `FF_MOCK_MASTERY_WRITES` before PR-7 shadow gate passes
- Do NOT start PR-7 until Track A gate is clean
- Do NOT mutate the live Supabase database outside the RPC
