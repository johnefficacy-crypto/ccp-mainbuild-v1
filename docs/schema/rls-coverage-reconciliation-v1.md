# RLS Coverage Reconciliation — v1 Release Gate

**Status:** CODE-FIXED, VALIDATION PENDING — **OPERATOR PENDING** for the authoritative
live inventory. This document is a *classification framework*, **not** a signed-off GREEN
gate. The gate cannot be marked GREEN until the post-migration staging/production
introspection query (below) is run and recorded.
**Source of truth:** the **live introspection query**, run against the current deployed
schema — **not** any file snapshot. `docs/schema/rls-policy-drift-audit.md` states this
explicitly: the set changes as tables are added, so the file is only a point-in-time aid.
The numbers below derive from the **2026-05-21 snapshot and are already known to be stale**
(see "Known staleness" — migrations after that date, e.g. 195/197, added at least one new
zero-policy table). Treat the counts as provisional pending the live re-run.
**Scope:** Provides a classification rule for each table flagged "RLS enabled, zero
policies" so that, once the live inventory is regenerated, every returned row can be sorted
into intentional / deferred / bug without re-litigating each table.

---

## TL;DR

- **No user-facing read path is known to be broken** — but this is provisional until the
  live inventory is regenerated and every returned row re-classified.
- Against the (stale) 2026-05-21 snapshot of **100** zero-policy tables, the classification is:
  - **56 SERVICE_ROLE_ONLY** = 20 public_catalog_read + 30 service_role_only + 6 admin_only.
    Correctly RLS-on / no-policy: the backend reads with the service key (bypasses RLS) and
    anon/authenticated access is correctly denied.
  - **31 DEFERRED (safe today)** = per-user owner-scoped tables. Safe only because all reads
    are service-role-mediated today; owner-column policies become *required* if a direct
    PostgREST read path is ever added.
  - **13 PRODUCT_DEFERRED** = blog / community / forum content needing a
    public-vs-member-vs-draft gating decision before policies are written.
  - 56 + 31 + 13 = **100**.
- The earlier "100 tables RLS-locked" drift was caused by an **untracked `ensure_rls` DDL
  trigger** that auto-enabled RLS on every `CREATE TABLE`. Migration `131` removed it;
  migration `130` repaired the three catalog tables (`recruitments`, `posts`,
  `organizations`) that genuinely needed public-read policies.

## Known staleness (why this is not yet a sign-off)

The 2026-05-21 snapshot predates later RLS changes, so the live set will differ:

- **`support_content_access`** — migration `195_security_rls_hardening.sql` (and re-asserted
  by `197_support_content_access_schema_repair.sql`) enables RLS with **no policy**. It is
  **absent from the snapshot below** and must be classified at verification time. Backend
  usage is admin-only (`app/backend/app/api/admin_study_os.py`, service-role) → expected
  classification **SERVICE_ROLE_ONLY**, to be confirmed live.
- Migration `195` also re-enables RLS on `content_access_requests` and
  `mock_breakdown_recompute_runs` (already in the lists below) and adds *policies* to a
  separate set of governance tables (`exam_topic_coverage`, `exam_topic_score_snapshots`,
  `exam_competition_metrics`, `exam_policy_updates`, `plan_impact_decisions`,
  `extraction_runs`, the `mock_question_*` tables) — those have policies and are NOT
  zero-policy.

The operator must regenerate the live inventory, diff the exact table-name set against the
snapshot (auditing every addition/removal), and classify each new row before this gate flips
to GREEN.

**Why this is safe:** the backend reads through `get_supabase_admin()` (service role) in
`app/backend/app/db/supabase_client.py`, and the frontend client
(`app/frontend/src/lib/supabaseClient.js`) holds only the anon key and performs no direct
table reads. RLS-on + zero-policy is the *correct* deny-all terminal state for any table
that is only ever touched by the service role.

---

## Classification of the flagged tables

Counts below are the corrected list lengths from the 2026-05-21 snapshot (sum = 100);
they remain provisional until the live re-run.

| Class | Count | v1 classification | Rationale |
|-------|-------|-------------------|-----------|
| public_catalog_read | 20 | **SERVICE_ROLE_ONLY** | Non-PII catalog/criteria data; read only via service role. No direct anon/auth path. |
| service_role_only | 30 | **SERVICE_ROLE_ONLY** | Pipeline / AI / analytics / verification system tables. No user-facing read path. Deny-all is intended. |
| authenticated_owner_only | 31 | **DEFERRED (safe today)** | Per-user tables (`aspirant_*`, `study_*`, `chat_sessions`, …). All reads are service-role mediated today. Owner-column policies become *required* only if a direct PostgREST read path is added later. |
| admin_only | 6 | **SERVICE_ROLE_ONLY** | Trust / moderation / verification tables. Admin ops run via service role; would need `is_admin()` policies only if admins ever use a non-service client. |
| needs product decision | 13 | **PRODUCT_DEFERRED** | Blog / community / forum content. Gating choice (public vs member vs draft) must precede any policy. |

### public_catalog_read (20)
age_criteria, age_relaxation_rules, attempt_limits, certification_criteria, certifications,
disability_types, education_criteria, exam_eligibility_rules, exam_patterns,
knowledge_base_university_thresholds, persona_question_bank, physical_requirement_types,
post_disability_requirements, post_fees, post_selection_stages, recruitment_units,
salary_details, skill_tests, vacancies, vacancy_reservations

### service_role_only (30)
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

## Operator verification (REQUIRED before this gate is GREEN)

Run this against **staging and production**, then diff the exact table-name set against the
2026-05-21 snapshot (≈100 tables) and **classify every difference**:
- An *increase* (expected — at minimum `support_content_access` from migration 195/197, plus
  any table added since the snapshot) → classify each new row using the rules above.
- A *decrease* → policies were added or RLS disabled somewhere outside migration history;
  audit that drift before release.
Record the resulting list and per-row classifications here; only then mark the gate GREEN.

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
