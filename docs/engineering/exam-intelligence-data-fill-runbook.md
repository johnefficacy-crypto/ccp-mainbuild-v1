# Exam Intelligence Data Fill Runbook (Production-Safe)

## Purpose

This runbook defines a safe, repeatable workflow to activate Exam Intelligence for Study OS without faking production truth and without prematurely promoting unverified data into planner-visible channels.

Use this for:
- local/dev demo refresh (SSC CGL demo seed);
- real exam onboarding via reviewed import templates;
- readiness validation before any planner-facing promotion.

## Trust & Review Model (must-follow)

- **Draft / Pending** = ingest stage. Never planner-ready.
- **Reviewed** = human-reviewed for context channels that allow reviewed reads (e.g., competition context can read reviewed/locked).
- **Verified** = required for official policy updates to carry `affects_*` flags and for verified evidence channels.
- **Locked** = planner-ready for topic coverage (`exam_topic_coverage.reviewer_status='locked'`).

Hard rules:
1. Never mark rows `locked` or `verified` without reviewer evidence.
2. Never fabricate official URLs, PYQ questions, or syllabus mentions.
3. Discovery sources (`aggregator`, `research`, `opportunity`) are awareness-only and must not set any `affects_* = true`.

## Minimum Data Required to Activate One Exam

Load in this exact order (foreign keys + downstream readers depend on it):

1. `exam_families`
2. `exams`
3. `exam_cycles`
4. `exam_phases`
5. `subjects`
6. `topics`
7. `topic_aliases`
8. `topic_prerequisites`
9. `exam_phase_sections`
10. `syllabus_documents`
11. `syllabus_topic_mentions`
12. `pyq_sources`
13. `pyq_papers`
14. `pyq_questions`
15. `pyq_options`
16. `pyq_question_topic_tags`
17. `exam_topic_coverage`
18. `exam_competition_metrics`
19. `exam_policy_updates`
20. Optional user seed: `profiles.target_exam`, `user_topic_mastery`, `user_topic_error_patterns`

## Safe Fill Workflow

### 1) Create import SQL from template
- Start with `app/supabase/seeds/templates/exam_intelligence_import_template.sql`.
- Keep defaults at `draft` / `pending` trust states.
- Use idempotent inserts (`on conflict do nothing` or explicit upsert logic with guarded `where` clauses).

### 2) Fill evidence-first
- Insert official syllabus + mentions with source URL and fetched date/hash notes.
- Insert PYQ sources/papers/questions/tags with explicit trust status.
- Ensure tag verification is tracked independently from question verification.

### 3) Add coverage only after evidence exists
- Add `exam_topic_coverage` initially as `reviewed` or `pending`.
- Promote to `locked` only after reviewer confirms evidence chain (syllabus or verified PYQ, or documented admin review rationale).

### 4) Add competition and policy context safely
- `exam_competition_metrics`: keep `reviewed`/`pending` until validated.
- `exam_policy_updates`:
  - only `source_type='official'` + `reviewer_status='verified'` may carry `affects_* = true`;
  - discovery rows keep all `affects_* = false`.

### 5) Validate readiness before planner activation
Run:

```bash
python app/backend/scripts/validate_exam_intelligence_seed.py --exam-slug <exam-slug>
python app/backend/scripts/validate_exam_intelligence_seed.py --exam-slug <exam-slug> --strict
```

Interpretation:
- Non-strict: prints PASS/WARN/FAIL report, exits 0.
- Strict: exits non-zero if hard failures are present.

## Local/Dev Demo Refresh

The demo seed is intentionally non-production truth and for local/dev exercise only:

```bash
psql "$DATABASE_URL" -f app/supabase/seeds/exam_intelligence_demo_ssc_cgl.sql
python app/backend/scripts/validate_exam_intelligence_seed.py --exam-slug ssc-cgl
```

Do not copy demo literals (URLs, papers, counts) into production imports.

## Real Exam Import (without premature lock)

1. Copy template SQL to a new import file per exam/cycle.
2. Keep all rows at pending/draft defaults.
3. Attach reviewer evidence notes and official links.
4. Run validation script; resolve FAILs/WARNs.
5. Promote statuses in controlled steps:
   - pending → reviewed
   - reviewed → verified (where required)
   - reviewed/verified → locked (coverage only when planner-ready)
6. Re-run strict validation before enabling planner reliance.

## Readiness Gate Summary

Exam can be considered planner-ready only when all are true:
- exam + cycle + phase + taxonomy present;
- locked topic coverage exists and resolves to active topics;
- each locked topic has verified evidence or explicit admin-review rationale;
- PYQ verified counts are based on verified question + verified tag pairs;
- competition rows used for context are reviewed/locked;
- policy rows with `affects_*` true are official+verified;
- discovery policy rows remain non-impacting (`affects_*` all false).

## UPSC CSE 2024 — Concrete Workflow

### Template location

```
app/supabase/seeds/imports/upsc_cse_2024_import_template.sql
```

This file covers all 19 tables in FK-safe order. Every row defaults to
`pending`/`pending_review`/`draft` trust states. No row is planner-ready
on first apply.

### Step 1 — Fill placeholders

Open the template and replace every `<placeholder>` with a real value:

- UUID fields: generate with `python3 -c "import uuid; print(uuid.uuid4())"` or `select gen_random_uuid()` in psql. Keep a local record of each UUID.
- Date fields: copy verbatim from the official UPSC notification at `upsc.gov.in`. Never guess or interpolate.
- `source_url` fields: paste the direct URL to the official document. If the URL is not yet public, leave the field as `null` and note `"awaiting_official_release"` in the `review_notes`/`reviewer_notes` jsonb.
- PYQ rows (§14–16): the template ships those as commented-out examples. Uncomment and populate only when you have a verified official question paper source.

### Step 2 — Apply the template

```bash
psql "$DATABASE_URL" -f app/supabase/seeds/imports/upsc_cse_2024_import_template.sql
```

Verify the transaction committed (no `ROLLBACK` in output).

### Step 3 — Non-strict validation (PASS/WARN/FAIL report, exits 0)

```bash
python app/backend/scripts/validate_exam_intelligence_seed.py --exam-slug upsc-cse
```

Expected result immediately after apply:
- **PASS**: exam + cycle + phase rows present; taxonomy rows present.
- **WARN**: topic coverage is `pending_review`, not `locked` — expected at this stage.
- **WARN**: PYQ sections empty if question rows are still commented out — expected.
- **FAIL**: any required FK missing, any `affects_* = true` on a non-official/non-verified row.

Resolve all FAILs before continuing.

### Step 4 — Review in Exam Workspace UI

Open: `/admin/exam-intelligence/workspace/<upsc-cse-exam-uuid>`

Use the **Readiness & Activation** panel to see per-section blockers:
- `setup` — exam + cycle + phases present
- `documents` — syllabus doc uploaded + extraction status
- `syllabus_mapper` — mention rows in `pending` → promote to `reviewed` after checking source
- `pyq_workbench` — paper + question + tag rows; promote tags after verifying mapping rationale
- `competition` — competition metrics row; promote to `reviewed`/`locked` after evidence confirmed
- `updates` — policy rows; promote official rows to `verified` after source confirmed

The panel copy explicitly states **"created ≠ planner-ready"** — do not confuse row existence with planner activation.

### Step 5 — Promote statuses via PATCH (never via direct SQL in production)

**Topic coverage** (required for planner):
```
PATCH /api/admin/exam-intelligence/topic-coverage/<id>/review
Body: {"reviewer_status": "reviewed"}    # after first human review
Body: {"reviewer_status": "locked"}      # after full evidence chain confirmed
```
`reviewer_status` CHECK on `exam_topic_coverage` (migration 030):
`draft | pending_review | reviewed | locked | rejected`

**Policy updates** (official-only, after evidence confirmed):
```
PATCH /api/admin/exam-intelligence/policy-updates/<id>/review
Body: {"reviewer_status": "verified"}
```
Then, and only then, set `affects_*` flags via a second PATCH if the update
genuinely affects plan/deadline/eligibility/documents/syllabus/vacancy.

**Competition metrics**:
```
PATCH /api/admin/exam-intelligence/competition-metrics/<id>/review
Body: {"reviewer_status": "reviewed"}    # or "locked"
```
`reviewer_status` CHECK on `exam_competition_metrics` (migration 055):
`draft | pending_review | reviewed | locked | rejected`
Note: `verified` is **not** valid for competition metrics or topic coverage.
Use `locked` (planner-preferred) or `reviewed`. See AGENTS.md §11.

### Step 6 — Strict validation (exits non-zero on hard failures)

```bash
python app/backend/scripts/validate_exam_intelligence_seed.py --exam-slug upsc-cse --strict
```

**Interpretation:**
| Output | Meaning |
|--------|---------|
| `PASS` (all sections) | Safe to enable planner reliance |
| `WARN` on coverage | Coverage exists but not yet `locked`; planner will not use it |
| `WARN` on PYQ | PYQ rows present but not fully verified; Study OS will not surface them |
| `FAIL` | Hard failure — FK violation, illegal `affects_*` flag, or missing required row |
| exit code 0 | Non-strict run always exits 0; check output for FAIL lines manually |
| exit code ≠ 0 | Strict run: at least one FAIL present; do not enable planner reliance |

### Step 7 — Verify endpoints

After strict validation passes, confirm the aspirant-facing contract:

```bash
# Exam listed and active
curl -H "Authorization: Bearer <token>" "$API_URL/api/exams" | jq '.items[] | select(.slug=="upsc-cse")'

# Exam detail returns shaped exam
curl -H "Authorization: Bearer <token>" "$API_URL/api/exams/upsc-cse"

# Exam intelligence returns partial/empty gracefully pre-review (must not 500)
curl -H "Authorization: Bearer <token>" "$API_URL/api/exam-intelligence/exams/upsc-cse"

# Study OS exam list includes upsc-cse
curl -H "Authorization: Bearer <token>" "$API_URL/api/study/exams"
```

A 404 on `/api/exams/upsc-cse` is a **missing-row 404** (the route exists at
`app/backend/app/api/exams.py:188`). It means the `exams` table has no row
with `slug='upsc-cse'` — apply the template to fix it.

### Step 8 — Planner readiness confirmation

`planner_ready` on a Study OS exam is `true` only when:
1. `exams.is_active = true`; AND
2. at least one `exam_topic_coverage` row with `reviewer_status = 'locked'` exists for this exam.

Until both are true, the Study OS planner shows the exam as not ready and the
`/api/study/exams` response will have `planner_ready: false`.

## Column-name inconsistency

- `exam_topic_coverage.review_notes`
- `syllabus_topic_mentions.reviewer_notes`

Both are correct per their migrations (030 and 031). Do not "normalise" either.
