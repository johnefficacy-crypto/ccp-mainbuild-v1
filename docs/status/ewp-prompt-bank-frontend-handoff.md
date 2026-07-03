# EWP Prompt Operations — Frontend Handoff (Content Studio)

Status: **CODE PRESENT IN PR / VALIDATION PENDING** (migration 215 + `app/api/content_studio.py`,
PR #855 — not yet merged; RPC apply + live round-trip + operator app-metadata provisioning
pending). Frontend **not started**.
Owner of this doc: the EWP backend slice. Consumer: the Content Studio frontend owner.

This is the API contract + placement rules for building the operator UI that authors,
curates, reviews, bulk-imports, and assigns **writing prompts**. Read the backend
architecture first: `docs/architecture/content-studio.md` (§1.1 division of ownership),
`docs/architecture/english-writing-practice.md` §17, and migration
`app/supabase/migrations/214_writing_prompt_content_scoping.sql` (content scoping) +
`215_writing_prompt_content_studio_ops.sql` (the write path).

## Non-negotiable architecture facts

- **Content is subject-scoped.** A writing prompt's canonical identity is
  `subject_id` / `topic_id` / `microtopic_id`. There are **no** exam columns on
  `writing_prompts` (migration 214 dropped `exam_id`/`exam_cycle_id`/`exam_phase_id`).
  The UI must never send an exam id as part of prompt content.
- **Applicability is separate, and its lifecycle is review-gated.** Which
  exams/families/phases a prompt applies to is carried by `writing_prompt_targets`
  ("Exam Assignments"), edited through its own endpoints. Per the locked J2 split,
  `exam_intelligence.manage` may only **propose** an inert `pending_review`
  assignment; promoting it to effective `active`/`excluded` and removing it require
  `exam_intelligence.review`. Making content applicable is never a manage action.
- **No new sidebar destination.** Prompt operations live **inside Content Studio**
  (Library / Review Queue / Bulk Import / Exam Assignments), filtered to
  subject = English. The no-new-surface rule (IA lock §1.2) is satisfied by Content
  Studio's own consolidation, not by this slice. Do **not** add `/admin/english`,
  and do **not** reintroduce the paused "Prompt Bank" tab in `ExamWorkspace`.
- **There is NO activate control.** Migration 214 deactivated every prompt and
  reactivation is blocked until the applicability resolver + session/planner
  enforcement + public-read replacement land (see the activation-gate row in
  `career-copilot-checklist.md`). The backend exposes **no** activate endpoint —
  the UI must not render an "activate / publish live" affordance. Reviewers can move
  a prompt to `verified`, but it stays `is_active=false`.

## API surface — base `/api/admin/content-studio`

All write bodies use the standard `{ "reason": <8–500 chars>, ... }` envelope; a
missing/short reason is a 422. All mutations go through the data-layer hook
(`useApiAction` / `useCollection`), never raw `fetch` in components.

### Library / Review Queue — writing prompts

| Method + path | Permission | Body / query | Notes |
|---|---|---|---|
| `GET /writing-prompts` | author OR review OR manage OR super_admin | query: `subject_id, topic_id, microtopic_id, exercise_type, difficulty_level, reviewer_status, is_active, q, limit, offset` | `q` = substring on `prompt_text`. Returns `{items,total,limit,offset}`. |
| `GET /writing-prompts/{id}` | (same read set) | — | `{id}` must be a valid UUID (malformed → 422, not 404). 404 if absent. |
| `POST /writing-prompts` | `content_studio.author` | `{reason, payload:{subject_id, topic_id, microtopic_id?, exercise_type, prompt_text, source_text?, required_words?, required_sentence_count?, difficulty_level(1–10), min_words?, max_words?, max_rewrite_attempts?, rubric_id?, source_document_id?, metadata?}}` | Always lands `pending` / `is_active=false`. `extra='forbid'` — unknown keys (e.g. `exam_id`) → 422. `max_words ≥ min_words`. **`prompt_text` must be non-blank; each `required_words` entry is NFC+trimmed and must be exactly one token, non-blank, unique case-insensitively** (else 422). **`metadata.external_key` is system-owned — sending it is 422** (it is set only by bulk import). |
| `PATCH /writing-prompts/{id}` | `content_studio.author` | `{reason, expected_updated_at, payload:{…partial…}}` | **`expected_updated_at` is REQUIRED** — pass the `updated_at` the browser read from GET (the server does NOT re-mint it; that is what makes edit-after-edit lose). Empty payload → 422. Verified prompts are **locked** → 422 `prompt_verified_locked`. Stale token → 409. Same content rules as create; `metadata.external_key` cannot be set or changed (422) and is preserved across edits. |
| `POST /writing-prompts/bulk` | `content_studio.author` | `{reason, subject_id, rows:[{…prompt fields…, external_key}]}` | `external_key` **required** per row (subject-scoped idempotency). Identical row = unchanged; changed pending/needs_correction = updated (reset to pending); changed verified/rejected = 422 `bulk_locked_row`; in-batch dup key = 422. **Atomic all-or-nothing** — the first invalid/locked row aborts the whole batch with ONE `422` (there are no per-row results). On success returns `{"ok": true, "result": {"created": N, "updated": N, "unchanged": N}}`. Rows carry **no** `subject_id` (body-level). |
| `POST /writing-prompts/{id}/review` | `content_studio.review` | `{status, expected_status, expected_updated_at, reason, reviewer_notes?}` | **`expected_status` + `expected_updated_at` are REQUIRED** — the reviewer_status and updated_at the reviewer actually saw (so you can't verify content that changed under you). Transitions: `pending → verified\|rejected\|needs_correction`; `needs_correction → verified\|rejected\|pending`; `verified → rejected\|needs_correction`; `rejected` terminal. Illegal/unknown status → 422; stale token/status → 409. |

### Exam Assignments — writing_prompt_targets (J2 propose/review/remove split)

Making an assignment **effective** is a lifecycle transition, so it is split by the
locked J2 authority separation: `exam_intelligence.manage` may only **propose** an
inert `pending_review` assignment (default-deny keeps it inapplicable); making it
`active`/`excluded` and removing it require `exam_intelligence.review`. The UI must
render "activate assignment" and "remove assignment" only for a reviewer, and show a
manage-only user their proposals as pending awaiting review.

| Method + path | Permission | Body | Notes |
|---|---|---|---|
| `GET /writing-prompts/{id}/targets` | read set | — | `{items}` — each row carries `id`, scope, `applicability_status`, `priority_score`, `updated_at` (the CAS token for review/remove). |
| `POST /writing-prompts/{id}/targets` (propose) | `exam_intelligence.manage` | `{reason, is_global?, exam_family_id?, exam_id?, exam_phase_id?, priority_score?}` | **Exactly one** scope → else 422 `invalid_scope`. Always lands `pending_review` (no `applicability_status` field — sending one is 422). A duplicate (prompt, scope) → **409 `target_exists`** (review/remove the existing one). |
| `POST /writing-prompt-targets/{target_id}/review` (activate) | `exam_intelligence.review` | `{reason, applicability_status: "active"\|"excluded", priority_score?, expected_updated_at}` | Promote a `pending_review` (or flip active↔excluded). `expected_updated_at` = the target's `updated_at` (**CAS, required**; stale → 409). A **global** assignment cannot be `excluded` → 422 `invalid_scope`. |
| `POST /writing-prompt-targets/{target_id}/remove` | `exam_intelligence.review` | `{reason, expected_updated_at}` | CAS-guarded (stale → 409). 404 if the target is gone. |

## Response envelope

Mutations return a standard wrapper — `POST /writing-prompts` → `{ok, audit_id, row}`;
`PATCH`, `review`, `bulk`, and every target endpoint → `{ok: true, result: {...}}`. Read
the counts/rows out of `result`; do not expect a flat top-level `{created,...}`.

## Optimistic locking (read this before wiring edit/review)

Every GET returns `updated_at`. The browser must **hold that token** and send it back as
`expected_updated_at` on PATCH/review (and target review/remove). The server passes the
client token straight to the DB CAS — it never re-reads a fresh one — so a form opened
against an older revision loses with `409` instead of silently clobbering a concurrent
edit or verifying content the reviewer never saw. Data-layer mutations go through the
`useApiCollection` hook (the locked contract), never raw `fetch`.

## Error → UX mapping

- `422` — validation / illegal transition / locked-verified / invalid scope / invalid
  content (blank prompt, bad required word) / reserved `metadata.external_key` / malformed
  UUID. Show the detail inline; for `prompt_verified_locked` guide the user to
  review→needs_correction first.
- `409` — concurrent modification (stale `expected_updated_at`/`expected_status`, or a
  duplicate-scope `target_exists`). Re-fetch, re-hold the token, retry.
- `404` — prompt/target not found (the id is a valid UUID but absent).
- `403` — missing permission; hide the affordance rather than surfacing raw 403s.

## UI states to cover

Loading / empty / error for each list; optimistic-lock retry on 409; disabled
"coming soon" state for anything activation-related (gated); reviewer-notes field on
review; bulk-import result summary from `result.{created,updated,unchanged}` plus a
**single batch-level error banner** on 422 (the import is atomic all-or-nothing — there
are no per-row results to render); accessibility on the assignment scope selector
(exactly-one enforced client-side too).

## What backend already ships (do not rebuild)

Migration 215 RPCs + `content_studio` router + `CONTENT_STUDIO_AUTHOR` /
`CONTENT_STUDIO_REVIEW` / `EXAM_INTELLIGENCE_REVIEW` permission constants; router-layer
tests (`tests/exam_intelligence/test_content_studio_writing_prompts.py`) and
Postgres-gated behaviour tests (`tests/study_os/test_content_studio_ops_pg_behaviour.py`).
