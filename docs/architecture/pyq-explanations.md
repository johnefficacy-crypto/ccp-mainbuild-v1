# PYQ Question Explanations

_Last updated: 2026-07-08_

First-class, source-aware, independently-reviewed explanation layer for PYQ
questions. Schema lands in `app/supabase/migrations/230_pyq_question_explanations.sql`.

## Why a separate table

Flat `pyq_questions.explanation_text` cannot cleanly carry option-wise
rationales, worked steps, ambiguity notes, or source/licence state, and it ties
explanation trust to the question's own review status. `public.pyq_question_explanations`
gives each explanation its **own** review lifecycle: a question can be
`verified` while its explanation still `needs_correction`.

## Model

| Column | Purpose |
|---|---|
| `question_id` | FK → `pyq_questions`. |
| `short_explanation`, `explanation_text` | Learner-facing prose (once verified). |
| `solution_steps`, `option_rationales`, `formula_used`, `common_traps` | Structured jsonb for numeracy steps / option-wise reasoning / traps. |
| `final_answer_option_id`, `alternate_answer_option_id` | **Structured** answer refs → `pyq_options`. A same-question integrity trigger proves each option belongs to `question_id`. There is no free-text answer label to drift from the canonical uppercase `A/B/C/D`. |
| `ambiguity_status` | `none` / `disputed` / `multiple_possible` / `source_conflict`. |
| `explanation_source_type` | `official` / `platform_original` / `coaching` / `community` / `imported`. |
| `source_url` | The **actual** explanation source only — never a generic homepage. |
| `source_document_id`, `source_hash` | Provenance for an imported reference document (FK → `document_assets`). |
| `license_status` | `owned` / `licensed` / `public_domain` / `permission_pending` / `restricted`. |
| `reviewer_status`, `reviewed_by`, `reviewed_at` | Independent review lifecycle. |

`unique(question_id, explanation_source_type)`.

## Governance invariants

- **RLS admin/service-role only.** Unverified explanations never reach learners
  via direct reads; learner exposure will flow through a reviewed projection.
- **Fail-closed verification** (`pyq_question_explanations_guard` trigger, on
  INSERT and UPDATE). `reviewer_status='verified'` is rejected unless:
  - `license_status ∈ {owned, licensed, public_domain}` (cleared),
  - `ambiguity_status = 'none'` (resolved),
  - `final_answer_option_id is not null` (a valid final answer is asserted),
  - `reviewed_by` and `reviewed_at` are set (reviewer identity/time).
- **Content-/trust-edit downgrade.** Editing a verified row's learner-facing
  content (`explanation_text`, `short_explanation`, `solution_steps`,
  `option_rationales`, `formula_used`, `common_traps`, answer option refs,
  `ambiguity_status`) **or** any trust/provenance field (`explanation_source_type`,
  `source_url`, `source_document_id`, `source_hash`, `license_status`) forces it
  back to `needs_correction` and clears reviewer identity.
- **Grants.** `service_role` and `authenticated` hold explicit table grants
  (post-173 tables don't inherit the one-time blanket grant); RLS still restricts
  `authenticated` to `is_admin`. `anon` gets nothing. The review RPC grants
  EXECUTE to `service_role` only.
- **Fenced review.** Prefer the audited RPC
  `cms_review_pyq_question_explanation(id, expected_status, target_status, notes, actor_user_id, actor_email)`
  (SECURITY DEFINER, `service_role` only) over direct mutation. It locks the
  row, enforces the transition matrix + verify preconditions, stamps reviewer
  identity, and writes one `admin_audit_logs` row per transition.

Regression coverage: `app/supabase/tests/regression_230_pyq_question_explanations.sql`
(same-question integrity, each fail-closed precondition, content downgrade,
uniqueness, and the RPC verify + audit + uncleared-licence refusal).

## Importing third-party (e.g. coaching) explanation reference material

Third-party explanation corpora are **not** committed to the repository as SQL
literals — committing copyrighted text whose licence is still
`permission_pending` is not acceptable regardless of read-time RLS. Ingest such
material out-of-band, as **operator reference only**, until it is cleared:

1. Record the permission basis for the source (owner, contact, terms).
2. Upload the source file as a `document_assets` record (scope
   `admin_exam_intelligence`); capture its content hash.
3. Run the operator import against that document, writing rows with
   `explanation_source_type='coaching'` (or `imported`),
   `license_status='permission_pending'` (or `restricted`),
   `reviewer_status='pending'`, `source_document_id` set, `source_hash` set,
   and `source_url` **null** unless it points at the real explanation source.
4. Do **not** set `pyq_options.is_correct` / `pyq_questions.correct_option_id`
   from a third-party key — the answer key stays operator-verified, never
   fabricated from a coaching source (determinism > heuristics).
5. Before any learner exposure, author **platform-original** reviewed
   explanations (or obtain a cleared licence), attach a structured
   `final_answer_option_id`, resolve any ambiguity, and verify via the RPC.

Row-level extraction QA (each explanation belongs to its intended
`question_number` and contains no next-question/passage boundary text) is a
prerequisite of the import path, not of this schema migration.

## CMS write path

Migration 230 landed the table, the guard trigger and the review RPC, but no
route could create a row. The write path lives in
`app/backend/app/api/admin_exam_intel_cms.py` and follows the same conventions
as every other exam-intelligence CMS resource (`WriteEnvelope`,
`_reject_unknown` against a field allowlist, enum validation, FK existence
checks, one `admin_audit_logs` row per write, rows born `pending`):

| Endpoint | Purpose |
|---|---|
| `GET /admin/exam-intelligence-cms/pyq-question-explanations` | List, filterable by `question_id`, `reviewer_status`, `explanation_source_type`. |
| `POST /admin/exam-intelligence-cms/pyq-question-explanations` | Create one explanation. Forces `reviewer_status='pending'`. |
| `PATCH /admin/exam-intelligence-cms/pyq-question-explanations/{id}` | Curate non-status fields. |
| `POST /admin/exam-intelligence-cms/bulk-import` with `entity='pyq-question-explanations'` | Bulk create, max 2000 rows, per-row outcome. |

Permission: `exam_intelligence.cms` (`super_admin` bypass), gated by
`ADMIN_STUDY_OS_ENABLED` like the rest of the router.

Contracts the routes add on top of the schema:

- **Never born verified.** `reviewer_status` is forced to `'pending'` on
  create and is not in the PATCH allowlist. Promotion stays with
  `cms_review_pyq_question_explanation`.
- **`question_id` is create-only.** Re-parenting an explanation would strand
  `final_answer_option_id` / `alternate_answer_option_id`, which the guard
  trigger proves against the original question. Same convention as
  `pyq_options`.
- **jsonb container shapes are checked.** Postgres accepts a bare scalar as
  valid jsonb, so a string sent for `formula_used` would land as `"..."`
  instead of `[...]`. `solution_steps`, `formula_used` and `common_traps` must
  be arrays; `option_rationales` and `metadata` must be objects.
- **Same-question option integrity is mirrored** so a mis-mapped option id is
  a named 422 rather than a raw trigger exception surfaced as a 409.
- **Uniqueness is the pair, not the question.**
  `unique (question_id, explanation_source_type)` is deliberate: one
  explanation per question PER SOURCE, so the operator import of coaching or
  official reference material above stays possible alongside a
  platform-authored row. Repeating the pair is a 422 naming both values; a
  second row under a different `explanation_source_type` is allowed.

**Consequence for the surfacing layer (not built yet):** a question can hold
several explanations. A read that assumes a single row per question is wrong.
Whatever surfaces explanations to learners must select one by an explicit
precedence over `explanation_source_type` (alongside the existing
`reviewer_status='verified'` trust gate), not by taking the first row.
