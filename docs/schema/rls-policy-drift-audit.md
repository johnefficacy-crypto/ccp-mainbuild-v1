# RLS Policy Drift Audit

_Generated 2026-05-21 for the trust-contract / RLS codification work (migrations
129–132)._

## Scope & method

This audit lists every `public` table that has **RLS enabled but zero
policies**, derived from the migration history in `app/supabase/migrations/`
(not from live introspection). Run the validation query in
[Live verification](#live-verification) to confirm against the running DB —
the manually-applied catalog policies and the removed `ensure_rls` event
trigger mean live state can differ from the repo.

- RLS-enabled tables in repo: **134**
- Tables with ≥1 policy in repo: **86**
- **RLS enabled + zero policies: 48** (listed below)

## The access model matters more than the policy count

Two facts reframe every row below:

1. **The backend reads/writes with the service role.** `app/api/*` uses
   `get_supabase_admin()` (`app/backend/app/db/supabase_client.py`), which
   **bypasses RLS entirely**. Every catalog and user-data read the product
   serves today goes through this path.
2. **The frontend Supabase client is auth-only.** `app/frontend/src/lib/
   supabaseClient.js` is used for sign-in/session/reset flows. A repo-wide
   search for direct table reads (`.from('<table>')`) on the frontend
   returns **nothing** — there is no anon/authenticated PostgREST read path
   against application tables.

**Consequence:** an RLS-enabled table with zero policies is *currently safe* —
it is locked to anon/authenticated and the service-role backend still works.
The classifications below describe the policy each table **would need if a
direct (anon/authenticated) PostgREST read path is ever introduced**. They are
**not** a list of things that are broken today, and — per the task constraints
— this work does **not** auto-add policies to user-owned or private tables.

## Classification legend

- **service_role_only** — pipeline / admin / AI / analytics / system table.
  RLS-on + no-policy is the correct terminal state; service role bypasses, and
  anon/auth must never read it. No policy needed.
- **admin_only** — should be readable by admins via a direct client; would need
  an `is_admin(auth.uid())` policy if/when admins use a non-service client.
- **authenticated_owner_only** — per-user rows; would need an owner-column
  policy (`user_id = auth.uid()`) before any direct client access.
- **public_catalog_read** — non-PII catalog/content; a broad `select` policy is
  defensible if direct anon read is wanted. Verified app reader noted.
- **unknown / needs product decision** — gating (free vs paid, public vs
  private) is a product call; do not add a policy speculatively.

## RLS enabled + zero policies (48)

| Table | Owner column | Classification | Notes |
|---|---|---|---|
| `ai_action_policies` | — | service_role_only | AI guardrail config. |
| `ai_jobs` | — | service_role_only | Async AI job rows. |
| `ai_prompt_versions` | — | service_role_only | Prompt registry. |
| `ai_review_queue` | — | service_role_only | Internal review queue. |
| `anonymous_profile_merge_claims` | — | service_role_only | **Migration 128 — intentional, do NOT add a policy.** |
| `profile_merge_audit` | — | service_role_only | **Migration 128 — intentional, do NOT add a policy.** |
| `aspirant_persona_snapshots` | `user_id` | authenticated_owner_only | Owner = `profiles(id)`. |
| `candidate_field_registry` | — | service_role_only | Scraper field config. |
| `chat_sessions` | `user_id` | authenticated_owner_only | Owner = `profiles(id)`. |
| `course_sections` | — (via `courses`) | unknown / needs product decision | Public preview vs enrolled-only gating is a product call. |
| `courses` | `instructor_id` | public_catalog_read | Published marketplace catalog; read via backend `canonical`/marketplace APIs. Gate to `status='published'` if direct read added. |
| `enrollments` | `user_id` | authenticated_owner_only | Owner = `profiles(id)`. |
| `exam_eligibility_rules` | — | public_catalog_read | Reference data; read via `eligibility/runner.py` (service role). |
| `form_submissions` | — | service_role_only | Inbound form capture. |
| `funnel_events` | — | service_role_only | Analytics ingest. |
| `funnel_sessions` | — | service_role_only | Analytics ingest. |
| `instructor_payouts` | `instructor_id` | authenticated_owner_only / admin_only | Owner = instructor `profiles(id)`; finance-sensitive. |
| `lesson_progress` | `user_id` | authenticated_owner_only | Owner = `profiles(id)`. |
| `lessons` | — (via `courses`) | unknown / needs product decision | Free-preview vs paid gating is a product call. |
| `mock_subject_breakdowns` | (via `mock_tests`) | authenticated_owner_only | Child of user-owned `mock_tests`. |
| `mock_tests` | `user_id` | authenticated_owner_only | User study data. |
| `notification_generation_runs` | — | service_role_only | Pipeline run log. |
| `onboarding_answers` | `user_id` | authenticated_owner_only | Owner = `auth.users(id)`. |
| `onboarding_session_answers` | (via `onboarding_sessions`) | authenticated_owner_only | Child of user session. |
| `onboarding_sessions` | `user_id` | authenticated_owner_only | Owner = `auth.users(id)` (nullable for anon onboarding). |
| `payment_history` | `user_id` | authenticated_owner_only / admin_only | Finance-sensitive. |
| `persona_question_answers` | `user_id` | authenticated_owner_only | Owner = `profiles(id)`. |
| `persona_question_bank` | — | public_catalog_read | Question content bank; served via backend. |
| `persona_question_dismissals` | `user_id` | authenticated_owner_only | Owner = `profiles(id)`. |
| `persona_recompute_queue` | — | service_role_only | Internal queue. |
| `pyq_option_patterns` | — | unknown / needs product decision | PYQ analytics; free vs paid gating TBD. |
| `pyq_option_repetitions` | — | unknown / needs product decision | PYQ analytics; gating TBD. |
| `pyq_options` | — | unknown / needs product decision | PYQ content; gating TBD. |
| `pyq_papers` | — | unknown / needs product decision | PYQ content; gating TBD. |
| `pyq_question_topic_tags` | — | unknown / needs product decision | PYQ content; gating TBD. |
| `pyq_questions` | — | unknown / needs product decision | PYQ content; gating TBD. |
| `pyq_sources` | — | service_role_only | PYQ ingest provenance. |
| `question_relation_edges` | — | service_role_only | Knowledge-graph infra. |
| `recruitment_question_requirements` | — | service_role_only | Scraper/derived linkage. |
| `reviews` | `user_id` | public_catalog_read (read) / authenticated_owner_only (write) | Course reviews are typically public for display; owner writes. Needs split policy if direct access added. |
| `subscription_plans` | — | public_catalog_read | Pricing/plan catalog; public read of `is_active` plans is fine. |
| `syllabus_documents` | — | service_role_only | Content infra. |
| `syllabus_topic_mentions` | — | service_role_only | Content infra. |
| `topic_relation_edges` | — | service_role_only | Knowledge-graph infra. |
| `user_events` | `user_id` | service_role_only | Telemetry ingest; not a client-read surface. |
| `user_recruitment_feedback` | `user_id` | authenticated_owner_only | Owner = `profiles(id)`. |
| `user_signal_events` | `user_id` | service_role_only | Telemetry ingest. |
| `user_subscriptions` | `user_id` | authenticated_owner_only / admin_only | Owner = `profiles(id)`; billing-sensitive. |

## Catalog candidates (task list) — current RLS status

All of these have **RLS NOT enabled** in the repo (no `enable row level
security`, no policy). They are world-readable today *only* in the sense that
no anon path reads them — the backend reads them with the service role. They
are reasonable `public_catalog_read` candidates **if** a direct anon read path
is ever added; until then the safe action is to leave them as-is (do **not**
speculatively enable RLS without also adding a read policy, or you would lock
out a future direct reader).

| Table | RLS enabled? | Verified app reader (service role) | Classification |
|---|---|---|---|
| `source_registry` | no | `scraping/runner.py`, `scraping/official_resolver.py`, `api/admin_scrape.py`, `api/admin_trust.py` | admin_only catalog (trust-sensitive — prefer admin read, not broad public). |
| `recruitment_units` | no | `api/canonical.py` (nested in published recruitment detail), `scraping/runner.py` | public_catalog_read |
| `salary_details` | no | written by promote RPC; surfaced via recruitment detail | public_catalog_read |
| `age_criteria` | no | `eligibility/runner.py`, `scraping/runner.py` | public_catalog_read |
| `age_relaxation_rules` | no | `eligibility/runner.py`, `scraping/runner.py` | public_catalog_read |
| `education_criteria` | no | `eligibility/runner.py`, `scraping/runner.py` | public_catalog_read |
| `exam_patterns` | no | `api/canonical.py` (nested in recruitment detail) | public_catalog_read |
| `post_fees` | no | promote RPC / recruitment detail | public_catalog_read |
| `post_selection_stages` | no | promote RPC / recruitment detail | public_catalog_read |
| `skill_tests` | no | `api/canonical.py` (nested), `scraping/extractor.py` | public_catalog_read |
| `vacancy_reservations` | no | `scraping/runner.py` / recruitment detail | public_catalog_read |
| `post_disability_requirements` | no | `eligibility/runner.py` | public_catalog_read |
| `physical_requirement_types` | no | reference lookup | public_catalog_read (static reference) |
| `disability_types` | no | reference lookup | public_catalog_read (static reference) |

> Note: because the public recruitment detail (`api/canonical.py:get_recruitment`)
> reads these tables with the service role and filters the parent recruitment to
> `publish_status = 'published'`, draft-stage child rows are already not exposed
> through the product. A direct-anon `public_catalog_read` policy would only be
> needed if the frontend starts reading these tables via the Supabase client.

## User-owned tables (task list) — do NOT add broad read

| Table | Owner column | RLS enabled? | Classification |
|---|---|---|---|
| `study_tasks` | `user_id` (verify) | no | authenticated_owner_only |
| `study_sessions` | `user_id` (verify) | no | authenticated_owner_only |
| `study_plans` | `user_id` (verify) | no | authenticated_owner_only |
| `study_report_cards` | `user_id` (verify) | no | authenticated_owner_only |
| `mock_tests` | `user_id` | yes (no policy) | authenticated_owner_only |
| `mock_subject_breakdowns` | via `mock_tests` | yes (no policy) | authenticated_owner_only |
| `aspirant_*` (certifications, education, exam_attempts, exam_credentials, experience, location, preferences, recruitment_attempts, reservations) | `user_id` | mostly no (`aspirant_persona_snapshots` = yes) | authenticated_owner_only (credentials are PII-sensitive) |
| `persona_question_answers` | `user_id` | yes (no policy) | authenticated_owner_only |
| `onboarding_sessions` | `user_id` | yes (no policy) | authenticated_owner_only |
| `onboarding_session_answers` | via `onboarding_sessions` | yes (no policy) | authenticated_owner_only |
| `user_recruitment_applications` | `user_id` | no | authenticated_owner_only |
| `user_recruitment_feedback` | `user_id` | yes (no policy) | authenticated_owner_only |

## recruitments / posts / organizations (migration 130)

These three had **no `enable row level security` and no policy in any
migration**, yet the `*_public_read` policies were applied manually in the SQL
editor. A `select` policy is dormant unless RLS is enabled, so migration `130`
**enables RLS and creates the policies** (operator-confirmed decision):

- `recruitments_public_read` — `using (publish_status in ('published','needs_review'))`
- `posts_public_read` — `using (exists … parent recruitment published/needs_review)`
- `organizations_public_read` — `using (true)`

Service role (backend) bypasses RLS, so the existing `canonical.py` read path is
unaffected; the policies govern any direct anon/authenticated PostgREST read and
keep `draft` recruitments hidden.

## Removed: `ensure_rls` event trigger (migration 131)

Migration `131` drops a **live-only** `ensure_rls` `ddl_command_end` event
trigger and its `public.rls_auto_enable()` function. A repo grep for
`rls_auto_enable | ensure_rls | ddl_command_end | pg_event_trigger | event
trigger` returned **zero** matches, confirming these were never tracked. This
trigger is the most likely cause of the "RLS enabled, zero policies" drift
above: it silently RLS-locked every newly-created table. RLS is now managed
explicitly per table in migrations.

## Live verification

```sql
-- Every public table with RLS enabled and zero policies.
select c.relname as table_name
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public'
  and c.relkind = 'r'
  and c.relrowsecurity = true
  and not exists (select 1 from pg_policies p
                  where p.schemaname = 'public' and p.tablename = c.relname)
order by c.relname;
```

## Punted to product decision

- **PYQ content tables** (`pyq_questions`, `pyq_options`, `pyq_papers`,
  `pyq_option_patterns`, `pyq_option_repetitions`, `pyq_question_topic_tags`)
  and **course content** (`courses`, `course_sections`, `lessons`): free vs
  paid / preview vs enrolled gating must be decided before any read policy.
- **`reviews`**: confirm whether course reviews are public-read; if so, a split
  read(public)/write(owner) policy pair is needed.
- **`source_registry`**: trust-sensitive — confirm admin_only vs catalog read
  before exposing via any direct client.
- Whether to enable RLS on the **catalog candidate** tables at all is deferred
  until/unless a direct Supabase-client read path exists; today everything is
  service-role mediated.
