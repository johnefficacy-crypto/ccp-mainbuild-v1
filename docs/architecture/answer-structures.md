# Answer structures

Reviewed, per-question ANSWER STRUCTURES for descriptive PYQs: what the question
demands and what a good answer must contain. Shown to an aspirant only after
they submit their own answer. Not a model essay.

## Why

Self-evaluation against the generic six-criterion rubric (migration 293) tells
an aspirant *how* they wrote, never *what the question wanted*. The structure is
the missing half, and the ticks against it give Progress a content measure
("points covered") next to the rubric's form measure.

## Justification for an AI-drafted write path

CLAUDE.md forbids *unreviewed* AI-authored writes. This path is reviewed by
construction:

| Stage | Who | Can set |
|---|---|---|
| `scripts/generate_answer_structures.py --live` / Content Studio *Regenerate* | model | `status='draft'` only — `cms_create_answer_structure_draft` has no status parameter |
| Content Studio review queue | `content_studio.author` / `.review` | edit content of `draft` / `in_review` rows |
| Content Studio review queue | `content_studio.review` | `in_review`, `verified`, `rejected` (note required) |
| Learner read | — | reads `verified` rows of `verified` questions only (RLS + service code) |

No pgvector, no new model provider: the existing `anthropic` SDK, the model
configurable by `ANSWER_STRUCTURE_MODEL` / `--model`.

## Data (migration 303)

- `answer_structures` — one row per `(pyq_question_id, version)`; partial unique
  index allows one `verified` per question. Regenerating inserts version N+1;
  approving it demotes the previous verified version inside the same RPC.
- `descriptive_attempts.structure_version` + `covered_point_ids` — the body-point
  ids the aspirant ticked, against the version they ticked. Travel as a pair.
- RLS: learners select `verified` (and question verified); admin roles
  (`is_admin`) select/insert/update. Grants: `authenticated` select/insert/update
  only; no DELETE/TRUNCATE; nothing for `anon`. Write RPCs are service-role only
  and write `admin_audit_logs`.
- `word_budget` is computed from the question's `word_limit` (else the marks
  convention), never taken from the model.

## Generation rules

- Inputs: question text, subject, paper, syllabus section, microtopic, official
  syllabus line, marks, word limit.
- Tool use with a strict closed schema, then `validate_structure`; malformed
  output is retried with the validator's errors fed back, then reported — never
  written.
- Prompt forbids invented statistics, reports, case names and citations; the
  model must describe the evidence *type* and list uncertainty. Output is also
  linted (percentages, amounts, named cases, dated reports) and warnings are
  shown to the reviewer — never to learners.
- Cost: worst-case cost is checked before every call (retries included) against
  `--max-usd`; `--max-questions` bounds a run; `--resume` reads the JSONL log;
  questions with any non-rejected structure are skipped.
- Dry run is the default; `--call-model` calls without writing; `--live` writes
  drafts. CI never calls the model.

## Surfaces

- Admin: Content Studio → content type *Answer structures* → Review Queue
  (filters: status / subject / paper / year). No new top-level destination.
- Learner: after submit, *Compare with answer structure* beside the typed
  answer or handwritten pages (practice screen and My answers). Ticks save to
  the attempt. My answers rows show "N% points covered"; Progress shows the
  average over answers that were compared.

## API

| Route | Auth |
|---|---|
| `GET /api/study/descriptive/attempts/{id}/structure` | owner; 409 `not_submitted` for a draft |
| `PUT /api/study/descriptive/attempts/{id}/coverage` | owner, permanent account; 409 `structure_changed` if the version is no longer verified |
| `GET /api/admin/content-studio/answer-structures` | content read |
| `GET/PATCH /api/admin/content-studio/answer-structures/{id}` | read / author or review |
| `POST …/{id}/review` | `content_studio.review` |
| `POST …/{id}/regenerate` | `content_studio.author` |

Sample generator output: `answer-structures-dry-run-sample.md`.
