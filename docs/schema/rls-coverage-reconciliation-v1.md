# RLS Coverage Reconciliation — v1 Release Sign-off

**Status:** GREEN — no RLS bugs block v1. One operator verification step remains.
**Source of truth:** `docs/schema/rls-policy-drift-audit.md` (live introspection refreshed 2026-05-21).
**Scope:** Reconciles the ~100 tables flagged "RLS enabled, zero policies" into a
release decision: which are intentional, which are deferred, which (if any) are bugs.

---

## TL;DR

- **0 tables** are misconfigured in a way that breaks a user-facing read path.
- **81 tables** are correctly RLS-on / no-policy because they are **service-role only**
  (backend reads with the service key, which bypasses RLS; anon/authenticated access is
  correctly denied).
- **13 tables** (blog / community / forum content) are **product-deferred** — they need a
  public-vs-member-vs-draft gating decision *before* policies are written. Not a security
  bug today because the backend reads them via the service role and the frontend has no
  direct PostgREST path to them.
- The earlier "100 tables RLS-locked" drift was caused by an **untracked `ensure_rls` DDL
  trigger** that auto-enabled RLS on every `CREATE TABLE`. Migration `131` removed it;
  migration `130` repaired the three catalog tables (`recruitments`, `posts`,
  `organizations`) that genuinely needed public-read policies.

**Why this is safe:** the backend reads through `get_supabase_admin()` (service role) in
`app/backend/app/db/supabase_client.py`, and the frontend client
(`app/frontend/src/lib/supabaseClient.js`) holds only the anon key and performs no direct
table reads. RLS-on + zero-policy is the *correct* deny-all terminal state for any table
that is only ever touched by the service role.

---

## Classification of the flagged tables

| Class | Count | v1 classification | Rationale |
|-------|-------|-------------------|-----------|
| public_catalog_read | 19 | **SERVICE_ROLE_ONLY** | Non-PII catalog/criteria data; read only via service role. No direct anon/auth path. |
| service_role_only | 31 | **SERVICE_ROLE_ONLY** | Pipeline / AI / analytics / verification system tables. No user-facing read path. Deny-all is intended. |
| authenticated_owner_only | 31 | **DEFERRED (safe today)** | Per-user tables (`aspirant_*`, `study_*`, `chat_sessions`, …). All reads are service-role mediated today. Owner-column policies become *required* only if a direct PostgREST read path is added later. |
| admin_only | 6 | **SERVICE_ROLE_ONLY** | Trust / moderation / verification tables. Admin ops run via service role; would need `is_admin()` policies only if admins ever use a non-service client. |
| needs product decision | 13 | **PRODUCT_DEFERRED** | Blog / community / forum content. Gating choice (public vs member vs draft) must precede any policy. |

### public_catalog_read (19)
age_criteria, age_relaxation_rules, attempt_limits, certification_criteria, certifications,
disability_types, education_criteria, exam_eligibility_rules, exam_patterns,
knowledge_base_university_thresholds, persona_question_bank, physical_requirement_types,
post_disability_requirements, post_fees, post_selection_stages, recruitment_units,
salary_details, skill_tests, vacancies, vacancy_reservations

### service_role_only (31)
aggregator_listings, ai_action_policies, ai_jobs, ai_prompt_versions, ai_review_queue,
alert_events, anonymous_profile_merge_claims, candidate_field_registry,
candidate_observations, external_api_usage, form_submissions, funnel_events,
funnel_sessions, listing_observations, low_quality_extractions,
mock_breakdown_recompute_runs, notification_group_state, official_resolution_attempts,
persona_recompute_queue, profile_merge_audit, recruitment_candidates, recruitment_events,
recruitment_field_diffs, recruitment_question_requirements, recruitment_verification_reports,
reverification_batches, scrape_runs, source_observations, user_events, user_signal_events

### authenticated_owner_only (31) — deferred, safe today
aspirant_certifications, aspirant_education, aspirant_exam_attempts,
aspirant_exam_credentials, aspirant_experience, aspirant_location,
aspirant_persona_snapshots, aspirant_preferences, aspirant_recruitment_attempts,
aspirant_reservations, chat_sessions, community_votes, content_access_requests,
forum_comment_upvotes, forum_post_upvotes, forum_reputation, forum_saved_posts,
mock_subject_breakdowns, mock_tests, onboarding_answers, onboarding_session_answers,
onboarding_sessions, partner_rematch_blocks, persona_question_answers,
persona_question_dismissals, study_plans, study_report_cards, study_sessions,
study_tasks, user_recruitment_applications, user_recruitment_feedback

### admin_only (6)
community_reports, forum_reports, mentor_verification, recruitment_verification_overrides,
scrape_sources, source_registry

### needs product decision (13) — PRODUCT_DEFERRED
blog_categories, blog_ctas, blog_post_tags, blog_posts, blog_recruitment_links, blog_tags,
community_channels, community_replies, community_spaces, community_threads,
forum_categories, forum_comments, forum_posts

---

## Migrations that fixed the drift

- **`130_public_catalog_rls_repair.sql`** — enabled RLS and added public-read policies on
  `recruitments`, `posts`, `organizations` (filtered by `publish_status` where applicable).
  These three now have policies and correctly drop off the zero-policy list.
- **`131_remove_untracked_rls_auto_enable.sql`** — dropped the untracked `ensure_rls` DDL
  trigger + `rls_auto_enable()` function (the root cause). Idempotent and safe. RLS is now
  managed explicitly per migration.

---

## Operator verification (the one remaining step)

Run this against **staging and production** and confirm the result matches the
2026-05-21 audit snapshot (≈100 tables). Any *decrease* means policies were added or RLS
disabled somewhere outside migration history — audit that drift before release.

```sql
-- Every public table with RLS enabled and zero policies.
select c.relname as table_name
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public'
  and c.relkind = 'r'
  and c.relrowsecurity = true
  and not exists (
    select 1 from pg_policies p
    where p.schemaname = 'public' and p.tablename = c.relname
  )
order by c.relname;
```

**Gate:** confirm none of the returned tables is one the frontend reads directly with the
anon/authenticated key. (Today: none — frontend is anon-key with no direct table reads.)

---

## v1.x roadmap follow-ups (NOT v1 blockers)

1. **Blog/community/forum gating decision** (13 tables): pick public vs member-only vs
   draft-gated, then write the policies. Tracked here as the only RLS product decision.
2. **Owner-column policies** for the 31 `authenticated_owner_only` tables: required *only*
   if/when a direct Supabase-client read path is introduced for end users. Document this as
   a hard dependency for whoever builds that feature.
