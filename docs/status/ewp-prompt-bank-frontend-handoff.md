# EWP Prompt Operations — Frontend Handoff (Content Studio)

Status: **backend delivered** (migration 215 + `app/api/content_studio.py`), frontend **not started**.
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
- **Applicability is separate.** Which exams/families/phases a prompt applies to is
  carried by `writing_prompt_targets` ("Exam Assignments"), edited through its own
  endpoints and gated on `exam_intelligence.manage` (Manage Exam owns applicability).
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
| `GET /writing-prompts/{id}` | (same read set) | — | 404 if absent. |
| `POST /writing-prompts` | `content_studio.author` | `{reason, payload:{subject_id, topic_id, microtopic_id?, exercise_type, prompt_text, source_text?, required_words?, required_sentence_count?, difficulty_level(1–10), min_words?, max_words?, max_rewrite_attempts?, rubric_id?, source_document_id?, metadata?}}` | Always lands `pending` / `is_active=false`. `extra='forbid'` — unknown keys (e.g. `exam_id`) → 422. `max_words ≥ min_words`. |
| `PATCH /writing-prompts/{id}` | `content_studio.author` | `{reason, payload:{…partial…}}` | Empty payload → 422. Verified prompts are **locked** → 422 `prompt_verified_locked` (demote via review first). Stale write → 409. |
| `POST /writing-prompts/bulk` | `content_studio.author` | `{reason, subject_id, rows:[{…prompt fields…, external_key}]}` | `external_key` **required** per row (subject-scoped idempotency). Identical row = unchanged; changed pending/needs_correction = updated (reset to pending); changed verified/rejected = 422 `bulk_locked_row`; in-batch dup key = 422. Returns `{created,updated,unchanged}`. Rows carry **no** `subject_id` (body-level). |
| `POST /writing-prompts/{id}/review` | `content_studio.review` | `{status, reason, reviewer_notes?}` | Allowed transitions: `pending → verified\|rejected\|needs_correction`; `needs_correction → verified\|rejected\|pending`; `verified → rejected\|needs_correction`; `rejected` is terminal. Illegal/unknown status → 422. |

### Exam Assignments — writing_prompt_targets

| Method + path | Permission | Body | Notes |
|---|---|---|---|
| `GET /writing-prompts/{id}/targets` | read set | — | `{items}`. |
| `POST /writing-prompts/{id}/targets` | `exam_intelligence.manage` | `{reason, is_global?, exam_family_id?, exam_id?, exam_phase_id?, applicability_status(active\|excluded\|pending_review)=active, priority_score?}` | **Exactly one** of {is_global, exam_family_id, exam_id, exam_phase_id} → else 422 `invalid_scope`. Upsert by (prompt, scope). |
| `POST /writing-prompt-targets/{target_id}/remove` | `exam_intelligence.manage` | `{reason}` | 404 if the target is gone. |

## Error → UX mapping

- `422` — validation / illegal transition / locked-verified / invalid scope. Show the
  detail inline; for `prompt_verified_locked` guide the user to review→needs_correction first.
- `409` — concurrent modification. Prompt the user to re-fetch and retry (the row changed
  since it was read; the UI holds a stale `updated_at`).
- `404` — prompt/target not found.
- `403` — missing permission; hide the affordance rather than surfacing raw 403s.

## UI states to cover

Loading / empty / error for each list; optimistic-lock retry on 409; disabled
"coming soon" state for anything activation-related (gated); reviewer-notes field on
review; bulk-import result summary (created/updated/unchanged + per-row lock errors);
accessibility on the assignment scope selector (exactly-one enforced client-side too).

## What backend already ships (do not rebuild)

Migration 215 RPCs + `content_studio` router + `CONTENT_STUDIO_AUTHOR` /
`CONTENT_STUDIO_REVIEW` permission constants; router-layer tests
(`tests/exam_intelligence/test_content_studio_writing_prompts.py`) and Postgres-gated
behaviour tests (`tests/study_os/test_content_studio_ops_pg_behaviour.py`).
