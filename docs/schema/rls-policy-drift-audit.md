# RLS Policy Drift Audit

_Originally generated 2026-05-21 for the trust-contract / RLS codification work
(migrations 129–132). **Refreshed 2026-05-21 against live introspection** — the
table list below now reflects what the running database returned, not the
migration history._

## Scope & method

This audit lists every `public` table that has **RLS enabled but zero
policies**. The earlier revision derived this from `app/supabase/migrations/`
and found **48**; live introspection returns **100**. The gap is real drift:
the live DB has RLS enabled on many tables that no migration enables (see
[Repo vs live delta](#repo-vs-live-delta)), almost certainly from the
now-removed `ensure_rls` event trigger (migration 131) auto-enabling RLS on
every `create table`.

Re-run the query in [Live verification](#live-verification) to regenerate the
list; treat that query — not this file — as the source of truth, since the set
changes as tables are added.

## The access model matters more than the policy count

Two facts reframe every table below:

1. **The backend reads/writes with the service role.** `app/api/*` uses
   `get_supabase_admin()` (`app/backend/app/db/supabase_client.py`), which
   **bypasses RLS entirely**. Every catalog and user-data read the product
   serves today goes through this path.
2. **The frontend Supabase client is auth-only.** `app/frontend/src/lib/
   supabaseClient.js` is used for sign-in/session/reset flows. A repo-wide
   search for direct table reads (`.from('<table>')`) on the frontend returns
   **nothing** — there is no anon/authenticated PostgREST read path against
   application tables.

**Consequence:** an RLS-enabled table with zero policies is *currently safe* —
it is locked to anon/authenticated and the service-role backend still works.
The classifications below describe the policy each table **would need if a
direct (anon/authenticated) PostgREST read path is ever introduced**. They are
**not** a list of things broken today, and this work does **not** auto-add
policies to user-owned or private tables.

## Classification legend

- **service_role_only** — pipeline / AI / analytics / verification / system
  table. RLS-on + no-policy is the correct terminal state. No policy needed.
- **admin_only** — trust/moderation/verification-sensitive; would need an
  `is_admin(auth.uid())` policy only if admins use a non-service client.
- **authenticated_owner_only** — per-user rows; would need an owner-column
  policy (`user_id = auth.uid()`) before any direct client access.
- **public_catalog_read** — non-PII catalog/content/reference; a broad `select`
  policy is defensible if direct anon read is wanted.
- **needs product decision** — gating (free vs paid, public vs member, draft vs
  published) is a product call; do not add a policy speculatively.

## Live RLS-enabled / zero-policy tables (100), grouped by classification

### public_catalog_read (19) — recruitment catalog/criteria + static reference
Non-PII; surfaced today via the service-role recruitment-detail/eligibility
paths. The public recruitment detail (`api/canonical.py:get_recruitment`)
already filters the parent recruitment to `publish_status='published'`, so
draft-stage child rows are not exposed through the product.

`age_criteria`, `age_relaxation_rules`, `attempt_limits`, `certification_criteria`,
`certifications`, `disability_types`, `education_criteria`, `exam_eligibility_rules`,
`exam_patterns`, `knowledge_base_university_thresholds`, `persona_question_bank`,
`physical_requirement_types`, `post_disability_requirements`, `post_fees`,
`post_selection_stages`, `recruitment_units`, `salary_details`, `skill_tests`,
`vacancies`, `vacancy_reservations`

> `persona_question_bank` is shared content served to all aspirants via the
> backend; broad read is fine but it has no direct anon path today.

### authenticated_owner_only (31) — per-user; need owner-column policy first
Owner column is `user_id` → `profiles(id)` unless noted. `aspirant_exam_credentials`
is PII-sensitive (exam login credentials) — never broaden.

`aspirant_certifications`, `aspirant_education`, `aspirant_exam_attempts`,
`aspirant_exam_credentials`, `aspirant_experience`, `aspirant_location`,
`aspirant_persona_snapshots`, `aspirant_preferences`, `aspirant_recruitment_attempts`,
`aspirant_reservations`, `chat_sessions`, `community_votes`, `content_access_requests`,
`forum_comment_upvotes`, `forum_post_upvotes`, `forum_reputation`, `forum_saved_posts`,
`mock_subject_breakdowns` (via `mock_tests`), `mock_tests`, `onboarding_answers`,
`onboarding_session_answers` (via `onboarding_sessions`), `onboarding_sessions`,
`partner_rematch_blocks`, `persona_question_answers`, `persona_question_dismissals`,
`study_plans`, `study_report_cards`, `study_sessions`, `study_tasks`,
`user_recruitment_applications`, `user_recruitment_feedback`

> `onboarding_*` use `auth.users(id)` (nullable for anon onboarding).
> `forum_reputation` could alternatively be public (leaderboards) — confirm.

### service_role_only (31) — pipeline / AI / analytics / verification / system
RLS-on + no-policy is the correct terminal state; do not add policies.

`aggregator_listings`, `ai_action_policies`, `ai_jobs`, `ai_prompt_versions`,
`ai_review_queue`, `alert_events`, `anonymous_profile_merge_claims`,
`candidate_field_registry`, `candidate_observations`, `external_api_usage`,
`form_submissions`, `funnel_events`, `funnel_sessions`, `listing_observations`,
`low_quality_extractions`, `mock_breakdown_recompute_runs`, `notification_group_state`,
`official_resolution_attempts`, `persona_recompute_queue`, `profile_merge_audit`,
`recruitment_candidates`, `recruitment_events`, `recruitment_field_diffs`,
`recruitment_question_requirements`, `recruitment_verification_reports`,
`reverification_batches`, `scrape_runs`, `source_observations`, `user_events`,
`user_signal_events`

> `anonymous_profile_merge_claims` and `profile_merge_audit` are **migration
> 128 intentional service-role-only — do NOT add policies.**

### admin_only (6) — trust / moderation / verification / KYC sensitive
Would need an `is_admin()` policy only if admins use a direct (non-service) client.

`community_reports`, `forum_reports`, `mentor_verification`,
`recruitment_verification_overrides`, `scrape_sources`, `source_registry`

> `source_registry` is trust-sensitive (it gates official-source resolution) —
> prefer admin read over broad public if ever exposed directly.

### needs product decision (13) — blog / community / forum public content
Public-read-of-published vs member-only vs owner-write gating is a product call.

`blog_categories`, `blog_ctas`, `blog_post_tags`, `blog_posts`,
`blog_recruitment_links`, `blog_tags`, `community_channels`, `community_replies`,
`community_spaces`, `community_threads`, `forum_categories`, `forum_comments`,
`forum_posts`

## Repo vs live delta

The earlier repo-derived list of 48 and the live list of 100 differ in **both**
directions:

- **In live but not repo (~70 tables).** Catalog/criteria, `aspirant_*`,
  `blog_*`, `community_*`, `forum_*`, scraper-pipeline, and verification tables
  show RLS-on/zero-policy live even though no migration enables RLS on them →
  drift from the removed `ensure_rls` trigger.
- **In repo but NOT in the live zero-policy list (~22 tables).** These migrations
  enable RLS, yet live does **not** report them as zero-policy — meaning live
  has *either* added policies *or* disabled RLS on them. Confirm each with the
  [per-table check](#live-verification):

  `course_sections`, `courses`, `enrollments`, `instructor_payouts`,
  `lesson_progress`, `lessons`, `notification_generation_runs`,
  `pyq_option_patterns`, `pyq_option_repetitions`, `pyq_options`, `pyq_papers`,
  `pyq_question_topic_tags`, `pyq_questions`, `pyq_sources`,
  `question_relation_edges`, `reviews`, `subscription_plans`,
  `syllabus_documents`, `syllabus_topic_mentions`, `topic_relation_edges`,
  `user_subscriptions`

This delta is exactly why the live query, not the migration history, is the
source of truth for RLS posture.

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
keep `draft` recruitments hidden. These three correctly do **not** appear in the
live zero-policy list (they now have policies).

## Removed: `ensure_rls` event trigger (migration 131)

Migration `131` drops a **live-only** `ensure_rls` `ddl_command_end` event
trigger and its `public.rls_auto_enable()` function. A repo grep for
`rls_auto_enable | ensure_rls | ddl_command_end | pg_event_trigger | event
trigger` returned **zero** matches, confirming these were never tracked. This
trigger is the most likely cause of the ~70-table "RLS enabled, zero policies"
drift above: it silently RLS-locked every newly-created table. RLS is now
managed explicitly per table in migrations.

> Note: when 131 was applied live it logged "event trigger ensure_rls does not
> exist, skipping" — so on this DB the trigger had already been removed (or
> created under another name) by apply time, but the auto-RLS footprint it left
> behind persists in the 100-table list. The drop is a safe idempotent no-op.

## Live verification

```sql
-- Every public table with RLS enabled and zero policies (regenerates the list).
select c.relname as table_name
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public'
  and c.relkind = 'r'
  and c.relrowsecurity = true
  and not exists (select 1 from pg_policies p
                  where p.schemaname = 'public' and p.tablename = c.relname)
order by c.relname;

-- Per-table check for the "repo but not live zero-policy" delta:
-- is RLS on, and does it have policies?
select c.relname,
       c.relrowsecurity as rls_enabled,
       count(p.policyname) as policy_count
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
left join pg_policies p on p.schemaname = 'public' and p.tablename = c.relname
where n.nspname = 'public'
  and c.relname in (
    'courses','course_sections','lessons','enrollments','lesson_progress',
    'instructor_payouts','reviews','subscription_plans','user_subscriptions',
    'pyq_questions','pyq_options','pyq_papers','pyq_option_patterns',
    'pyq_option_repetitions','pyq_question_topic_tags','pyq_sources',
    'question_relation_edges','topic_relation_edges','syllabus_documents',
    'syllabus_topic_mentions','notification_generation_runs'
  )
group by c.relname, c.relrowsecurity
order by c.relname;
```

## Punted to product decision

- **Blog / community / forum content** (`blog_*`, `community_channels|spaces|
  threads|replies`, `forum_categories|posts|comments`): decide public-read vs
  member-only vs draft-gated before adding policies.
- **`reviews`** (in the repo-vs-live delta): confirm whether course reviews are
  public-read; if so, a split read(public)/write(owner) policy pair is needed.
- **PYQ + course content** (`pyq_*`, `courses`, `course_sections`, `lessons`):
  free vs paid / preview vs enrolled gating — and first confirm their actual
  live RLS/policy state via the delta query above.
- **`source_registry`**: trust-sensitive — confirm admin_only vs catalog read
  before exposing via any direct client.
- Whether to add owner policies to the `authenticated_owner_only` set is deferred
  until a direct Supabase-client read path exists; today everything is
  service-role mediated.
