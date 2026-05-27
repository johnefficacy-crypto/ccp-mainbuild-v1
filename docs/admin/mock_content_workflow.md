# Mock Content Workflow — Admin Guide

> Applies to: PR2 `feat(mock-engine): PR2 admin question bank + review workflow`
> Introduced in migration `136_mock_question_workflow.sql`

---

## Overview

The Mock Content Workflow is a lightweight publishing pipeline for exam mock questions.
Questions move through a six-state lifecycle — from `draft` to `published` — with
mandatory human review and optional publisher gates before questions are served to
aspirants.

```
draft  ──submit──▶  in_review  ──approve──▶  verified  ──publish──▶  published
                        │                                                  │
                request_changes                                         archive
                        │                                                  │
                  needs_changes ──submit──▶  in_review             archived
```

Published questions are the only ones served by the mock engine.  Questions that have
passed their `valid_until` date are automatically excluded even if their status is
`published`.

---

## Roles and Permissions

The workflow uses **three granular permission strings** stored in a user's
`app_metadata.permissions` array (not role names):

| Permission string           | Who has it              | Can do |
|-----------------------------|-------------------------|--------|
| `mock_questions:author`     | Content authors         | Create questions, edit own drafts, submit for review |
| `mock_questions:review`     | Senior subject editors  | Approve or request changes on `in_review` questions; view Review Queue |
| `mock_questions:publish`    | Publishers / platform admins | Publish, archive, restore, force-status, override fingerprint |

`super_admin` role bypasses all permission checks.

### Granting permissions

Permissions are granted directly in `auth.users.raw_app_meta_data.permissions` via the
Supabase dashboard, the Admin → Access Control page (`/admin/rbac`), or the bootstrap
helper described below.

### Bootstrap — seed publisher at startup

Set the environment variable before starting the backend:

```bash
MOCK_PUBLISHER_BOOTSTRAP_EMAILS=alice@example.com,bob@example.com
```

On every server start, `_bootstrap_mock_publishers()` (called from `lifespan`) reads
this CSV list, looks up each email in `auth.users`, and **idempotently** adds
`mock_questions:publish` to their `app_metadata.permissions`.  The function never
raises on failure — it logs a warning so a broken bootstrap does not block boot.

---

## State Machine Reference

| From status     | Action            | To status       | Who can act               |
|-----------------|-------------------|-----------------|---------------------------|
| `draft`         | `submit`          | `in_review`     | Author of the question    |
| `needs_changes` | `submit`          | `in_review`     | Author of the question    |
| `in_review`     | `approve`         | `verified`      | Reviewer (≠ author)       |
| `in_review`     | `request_changes` | `needs_changes` | Reviewer (≠ author)       |
| `verified`      | `publish`         | `published`     | Publisher                 |
| `verified`      | `archive`         | `archived`      | Publisher                 |
| `published`     | `archive`         | `archived`      | Publisher                 |
| `archived`      | `restore`         | `verified`      | Publisher                 |
| any             | `force`           | any             | Publisher only, must supply reason; always logged |

### Conflict-of-interest rule

A reviewer **cannot** approve or request changes on a question they authored
(`created_by == actor_id`).  This returns HTTP 409 with `detail: "conflict_of_interest"`.

---

## Fingerprint and Deduplication

Each question has a `question_fingerprint` (SHA-256) computed from:

```
sha256(
    lower(normalize_ws(question_text))
  + "|"
  + "|".join(sorted(option_texts, key=lower))   # order-stable
  + "|"
  + str(index_of_correct_option_in_sorted_list)
)
```

This fingerprint is stored in `mock_question_bank.question_fingerprint` with a `UNIQUE`
constraint.  Saving a question whose fingerprint collides with an existing row returns
HTTP 409.

### Override (publisher only)

Publishers can bypass the fingerprint collision by sending the request header:

```
X-Override-Fingerprint: true
```

This is logged in `mock_question_review_log` with `action = "fingerprint_override"`.

### Similarity check

The `POST /api/admin/mocks/:id/dedup-check` endpoint also runs a trigram similarity
search (pg_trgm) for questions with `similarity > threshold` (default 0.6).
Trigram neighbors are returned as warnings but do **not** block the save.

---

## API Endpoints

All endpoints are under `/api/admin/mocks/`.

### Questions CRUD

| Method   | Path                             | Permission         | Description                          |
|----------|----------------------------------|--------------------|--------------------------------------|
| `POST`   | `/questions`                     | `author`           | Create a new draft question          |
| `PATCH`  | `/questions/:id`                 | `author` / `publish` | Update question text, options, metadata |
| `GET`    | `/questions`                     | `author`           | Paginated list (author sees own only; reviewer/publisher sees all) |
| `GET`    | `/questions/:id`                 | `author`           | Full detail: question + options + sources + tags + review log |

### Workflow transitions

| Method   | Path                             | Permission         | Description                          |
|----------|----------------------------------|--------------------|--------------------------------------|
| `POST`   | `/:id/submit`                    | `author`           | `draft` / `needs_changes` → `in_review` |
| `POST`   | `/:id/approve`                   | `review`           | `in_review` → `verified`             |
| `POST`   | `/:id/request-changes`           | `review`           | `in_review` → `needs_changes`        |
| `POST`   | `/:id/publish`                   | `publish`          | `verified` → `published`             |
| `POST`   | `/:id/archive`                   | `publish`          | any → `archived`                     |
| `POST`   | `/:id/force-status`              | `publish`          | Any → any; requires `reason`         |

### Review queue

| Method   | Path                             | Permission         | Description                          |
|----------|----------------------------------|--------------------|--------------------------------------|
| `GET`    | `/review-queue`                  | `review`           | All `in_review` questions, newest first, paginated |

### Enrichment

| Method   | Path                             | Permission         | Description                          |
|----------|----------------------------------|--------------------|--------------------------------------|
| `POST`   | `/:id/dedup-check`               | `review`           | Fingerprint collision + trigram neighbors |
| `POST`   | `/:id/link-translation`          | `publish`          | Link two language variants into the same group |
| `PUT`    | `/:id/topic-tags`                | `author`           | Replace-all topic tags               |
| `PUT`    | `/:id/sources`                   | `author`           | Replace-all source entries           |

### Bulk import

| Method   | Path                               | Permission | Description                          |
|----------|------------------------------------|------------|--------------------------------------|
| `POST`   | `/questions/import/dry-run`        | `author`   | Validate file, return token + per-row preview |
| `POST`   | `/questions/import/commit`         | `author`   | Commit previously dry-run token      |

---

## Bulk Import

### Flow

1. Upload CSV or JSON to `POST /questions/import/dry-run`
2. Review the per-row preview — each row has a `status` field: `ok`, `duplicate`, `parse_error`, or `missing_tags`
3. The response contains an `import_token` (valid for 1 hour, in-memory)
4. Call `POST /questions/import/commit` with `{ "import_token": "..." }` to insert the `ok` rows

Rows are inserted idempotently using `question_fingerprint` as the dedup key.  Already-existing
fingerprints are skipped (counted in `skipped`) rather than causing an error.

### CSV schema

```csv
question_text,option_a,option_b,option_c,option_d,correct_option,difficulty,language,source_kind,source_url,exam_id
```

| Column           | Required | Notes                                       |
|------------------|----------|---------------------------------------------|
| `question_text`  | yes      | Full question string                        |
| `option_a` … `option_d` | yes (min a,b) | At least two option columns must be non-empty |
| `correct_option` | yes      | 0-based index (0=a, 1=b, 2=c, 3=d)         |
| `difficulty`     | yes      | `easy` / `medium` / `hard`                  |
| `language`       | yes      | `en` or `hi`                                |
| `source_kind`    | no       | Defaults to `authored`                      |
| `source_url`     | no       | URL string                                  |
| `exam_id`        | no       | Overridden by `exam_id_override` if supplied |

### JSON schema

```json
[
  {
    "question_text": "…",
    "options": [{"text": "…", "is_correct": false}, {"text": "…", "is_correct": true}],
    "correct_option": 1,
    "difficulty": "medium",
    "language": "en",
    "source_kind": "pyq",
    "source_url": "https://…",
    "exam_id": "uuid-or-null"
  }
]
```

---

## Database Tables

| Table                        | Purpose                                      |
|------------------------------|----------------------------------------------|
| `mock_question_bank`         | Core question row (text, metadata, status, fingerprint) |
| `mock_question_options`      | Answer options (linked to question)           |
| `mock_question_topic_tags`   | Many-to-many with `topics`, with `role` per tag |
| `mock_question_sources`      | Source provenance (kind, trust, URL, evidence) |
| `mock_question_review_log`   | Immutable audit trail of every action         |
| `mock_question_groups`       | Links translation pairs / variant groups      |

### Row-Level Security

Public users (`anon`, `authenticated`) can only read questions where:
```sql
reviewer_status = 'published'
AND (valid_until IS NULL OR valid_until > now())
```

Admins using the service-role key bypass RLS entirely.

---

## Source Trust Levels

| Level         | Meaning                                         |
|---------------|-------------------------------------------------|
| `unverified`  | Contributed by author, not yet cross-checked    |
| `provisional` | Plausible source, needs official confirmation   |
| `verified`    | Confirmed against official document or syllabus |

---

## Cognitive Tags

Each question must have **at least one** cognitive tag:

| Tag               | Field               | When to use                             |
|-------------------|---------------------|-----------------------------------------|
| Conceptual        | `is_conceptual`     | Tests understanding of a concept        |
| Factual           | `is_factual`        | Tests recall of a specific fact         |
| Current Event     | `is_current_event`  | Based on a time-bound news/policy event; requires `valid_until` |

When `is_current_event = true`, the question can have `valid_from` and `valid_until`
dates.  The mock engine automatically excludes questions past their `valid_until`.

---

## Marks Configuration

As of PR2, marks are **not stored on the question**.  They are defined on the
mock template (`mock_templates.marks_per_correct` / `marks_per_wrong`) and injected
at attempt-creation time into the frozen `question_snapshot`.

This allows the same question to be used in templates with different marking schemes
without duplication.
