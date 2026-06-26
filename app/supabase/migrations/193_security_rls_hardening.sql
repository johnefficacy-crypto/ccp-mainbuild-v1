-- =============================================================================
-- 193_security_rls_hardening.sql
-- Security: close confirmed RLS authorization vulnerabilities.
--
-- Four independent hardening sections, each idempotent and re-runnable:
--
--   Section 1 (CRITICAL) — Privileged-column write protection on public.profiles
--     Vuln: the profiles_update_own policy (migration 004) lets a row owner
--     UPDATE their own row with NO column restriction. A logged-in user can
--     therefore PATCH profiles.is_admin=true (or is_mentor / admin_role /
--     plan_id) directly through PostgREST and self-escalate. We add a
--     BEFORE UPDATE trigger that, for any non-service_role session, silently
--     forces the privileged columns back to their OLD values. It does NOT
--     raise — legitimate updates to non-privileged fields (display name, etc.)
--     in the same PATCH still succeed; only the privileged columns are pinned.
--
--   Section 2 (defense-in-depth) — Repoint deprecated profiles.is_admin admin
--     policies to the canonical public.is_admin() (migration 151).
--     Vuln: migrations 035/057/060/149 gate admin RLS on the DEPRECATED
--     profiles.is_admin column via an inline EXISTS check. Per migration 134
--     the source of truth for an auth role is auth.users.raw_app_meta_data.role
--     and profiles.is_admin is no longer authoritative. With Section 1 in place
--     a user can no longer flip profiles.is_admin, but these policies must be
--     correct regardless, so we DROP and RECREATE each to call
--     public.is_admin(auth.uid()) instead. The exact table lists and policy
--     names from 035/057 are replicated verbatim; only the predicate changes.
--
--   Section 3 — Fix world-writable mock-question admin policies (migration 136).
--     Vuln: mqg_admin_all / mqtt_admin_all / mqs_admin_all / mqrl_admin_all were
--     created `for all using (true) with check (true)` — readable AND writable
--     by anon/authenticated. We recreate each to mirror the CORRECT
--     mock_question_bank_admin_all pattern: service_role OR
--     app_metadata.role in ('admin','super_admin').
--
--   Section 4 — Enable RLS on audit / PII tables created without it.
--     Vuln: support_content_access (migration 102), content_access_requests and
--     mock_breakdown_recompute_runs (migration 104) were created WITHOUT
--     `enable row level security`, so with FORCE-free defaults the
--     anon/authenticated PostgREST roles could read these audit/PII rows. We
--     enable RLS and add NO policies, matching the migration 128 claim-tables
--     contract: RLS on + zero policies => only service_role (which bypasses
--     RLS) can touch them. The backend reaches them via the service-role client.
--
-- service_role detection (Section 1): we use auth.role() = 'service_role'.
--   Justification: this is the detection idiom used everywhere else in this
--   repo's RLS (migrations 013/014/015). current_setting('request.jwt.claims')
--   is not used anywhere in these migrations, and auth.role() is the
--   PostgREST-blessed accessor. The trigger is SECURITY DEFINER, but auth.role()
--   reads the request GUC (set per-statement by PostgREST/Supabase from the JWT)
--   rather than the executing function owner, so it still reports the CALLER's
--   role inside a SECURITY DEFINER function. We also accept the explicit
--   request.jwt.claims->>'role' = 'service_role' as a belt-and-braces fallback.
--
-- Does NOT weaken anything and grants NOTHING new to anon/authenticated.
-- Idempotent: safe on a fresh DB and re-runnable on an existing one.
-- =============================================================================

begin;

-- ─────────────────────────────────────────────────────────────────────────────
-- Section 1 — Protect privileged columns on public.profiles
-- ─────────────────────────────────────────────────────────────────────────────
-- The trigger function pins is_admin / is_mentor / admin_role / plan_id to their
-- OLD values for any non-service_role caller. Each column is guarded with a
-- to-regclass-free column-existence check via a per-column DO-built function
-- body is overkill; instead the function references the columns directly and we
-- only assign the ones that exist. Because a single CREATE OR REPLACE FUNCTION
-- body cannot reference a column that does not exist (it would fail to parse at
-- first execution via the plan cache, though plpgsql is late-bound per-field),
-- we build the function body dynamically from the set of privileged columns that
-- actually exist on public.profiles. This keeps the migration safe on canonical
-- DBs (no admin_role) and on legacy DBs (admin_role present, plan_id text).

do $$
declare
  v_assignments text := '';
  v_col         text;
  v_priv_cols   text[] := array['is_admin', 'is_mentor', 'admin_role', 'plan_id'];
begin
  foreach v_col in array v_priv_cols loop
    if exists (
      select 1
      from information_schema.columns
      where table_schema = 'public'
        and table_name   = 'profiles'
        and column_name  = v_col
    ) then
      -- new.<col> := old.<col>;
      v_assignments := v_assignments
        || format('    new.%I := old.%I;', v_col, v_col) || chr(10);
    end if;
  end loop;

  -- If none of the privileged columns exist (defensive), make the body a no-op
  -- comment so the function still compiles.
  if v_assignments = '' then
    v_assignments := '    -- no privileged columns present on this DB' || chr(10);
  end if;

  execute
    'create or replace function public.fn_profiles_protect_privileged_columns()' || chr(10) ||
    'returns trigger' || chr(10) ||
    'language plpgsql' || chr(10) ||
    'security definer' || chr(10) ||
    'set search_path = public' || chr(10) ||
    'as $fn$' || chr(10) ||
    'begin' || chr(10) ||
    '  -- service_role (the FastAPI backend) is trusted and may set these.' || chr(10) ||
    '  -- Detect it via auth.role() (the repo-wide idiom) OR the raw JWT claim.' || chr(10) ||
    '  if coalesce(auth.role(), '''') = ''service_role''' || chr(10) ||
    '     or coalesce(' || chr(10) ||
    '          (current_setting(''request.jwt.claims'', true))::jsonb ->> ''role'',' || chr(10) ||
    '          ''''' || chr(10) ||
    '        ) = ''service_role'' then' || chr(10) ||
    '    return new;' || chr(10) ||
    '  end if;' || chr(10) ||
    '  -- Non-service_role: silently preserve the OLD privileged values so a' || chr(10) ||
    '  -- legitimate update to other columns in the same statement still lands.' || chr(10) ||
    v_assignments ||
    '  return new;' || chr(10) ||
    'end' || chr(10) ||
    '$fn$;';
end $$;

comment on function public.fn_profiles_protect_privileged_columns() is
  'Security (migration 193 §1): pins privileged profiles columns '
  '(is_admin, is_mentor, admin_role, plan_id) to their OLD values for any '
  'non-service_role UPDATE, defeating self-escalation via PostgREST PATCH '
  'against the profiles_update_own RLS policy. Does not raise.';

drop trigger if exists tg_profiles_protect_privileged_columns on public.profiles;
create trigger tg_profiles_protect_privileged_columns
  before update on public.profiles
  for each row execute function public.fn_profiles_protect_privileged_columns();


-- ─────────────────────────────────────────────────────────────────────────────
-- Section 2 — Repoint deprecated profiles.is_admin admin policies to
--             canonical public.is_admin()
-- ─────────────────────────────────────────────────────────────────────────────
-- Decision: we RECREATE the policies (rather than drop them) so the authenticated
-- PostgREST surface they were designed for is preserved unchanged in shape; only
-- the admin predicate is swapped from the inline DEPRECATED
-- `exists (select 1 from public.profiles p where p.id = auth.uid() and p.is_admin = true)`
-- to the canonical `public.is_admin(auth.uid())`. Table arrays and policy names
-- are copied verbatim from migrations 035 and 057.

-- 2a. 035 — read policies that carry an admin disjunct (preserve the non-admin
--     branches exactly; only swap the admin EXISTS for public.is_admin()).
drop policy if exists exam_topic_coverage_read_reviewed on public.exam_topic_coverage;
create policy exam_topic_coverage_read_reviewed on public.exam_topic_coverage
  for select to authenticated
  using (
    reviewer_status in ('reviewed', 'locked')
    or public.is_admin(auth.uid())
  );

drop policy if exists exam_topic_score_snapshots_read_reviewed on public.exam_topic_score_snapshots;
create policy exam_topic_score_snapshots_read_reviewed on public.exam_topic_score_snapshots
  for select to authenticated
  using (
    status in ('reviewed', 'locked')
    or public.is_admin(auth.uid())
  );

-- 2b. 035 — admin_all loop over the same 23 tables (predicate swapped).
do $$
declare
  t text;
  policy_name text;
begin
  foreach t in array array[
    'subjects',
    'subject_aliases',
    'topics',
    'topic_aliases',
    'topic_prerequisites',
    'exam_families',
    'exams',
    'exam_cycles',
    'exam_phases',
    'exam_phase_sections',
    'exam_topic_coverage',
    'syllabus_documents',
    'syllabus_topic_mentions',
    'pyq_sources',
    'pyq_papers',
    'pyq_questions',
    'pyq_options',
    'pyq_question_topic_tags',
    'pyq_option_patterns',
    'pyq_option_repetitions',
    'question_relation_edges',
    'topic_relation_edges',
    'exam_topic_score_snapshots'
  ]
  loop
    policy_name := t || '_admin_all';
    -- Only touch tables that actually exist (defensive on partial DBs).
    if to_regclass('public.' || t) is not null then
      execute format('drop policy if exists %I on public.%I', policy_name, t);
      execute format(
        'create policy %I on public.%I for all to authenticated using (public.is_admin(auth.uid())) with check (public.is_admin(auth.uid()))',
        policy_name,
        t
      );
    end if;
  end loop;
end $$;

-- 2c. 057 — read policies that carry an admin disjunct.
drop policy if exists exam_competition_metrics_read_reviewed on public.exam_competition_metrics;
create policy exam_competition_metrics_read_reviewed on public.exam_competition_metrics
  for select to authenticated
  using (
    reviewer_status in ('reviewed', 'locked')
    or public.is_admin(auth.uid())
  );

drop policy if exists exam_policy_updates_read_trusted on public.exam_policy_updates;
create policy exam_policy_updates_read_trusted on public.exam_policy_updates
  for select to authenticated
  using (
    reviewer_status = 'verified'
    or (source_type <> 'official' and reviewer_status = 'pending')
    or public.is_admin(auth.uid())
  );

-- 2d. 057 — admin_all loop over its 2 tables (predicate swapped).
do $$
declare
  t text;
  policy_name text;
begin
  foreach t in array array[
    'exam_competition_metrics',
    'exam_policy_updates'
  ]
  loop
    policy_name := t || '_admin_all';
    if to_regclass('public.' || t) is not null then
      execute format('drop policy if exists %I on public.%I', policy_name, t);
      execute format(
        'create policy %I on public.%I for all to authenticated using (public.is_admin(auth.uid())) with check (public.is_admin(auth.uid()))',
        policy_name,
        t
      );
    end if;
  end loop;
end $$;

-- 2e. 060 — plan_impact_decisions_admin_all.
do $$
begin
  if to_regclass('public.plan_impact_decisions') is not null then
    drop policy if exists plan_impact_decisions_admin_all on public.plan_impact_decisions;
    create policy plan_impact_decisions_admin_all on public.plan_impact_decisions
      for all to authenticated
      using (public.is_admin(auth.uid()))
      with check (public.is_admin(auth.uid()));
  end if;
end $$;

-- 2f. 149 — extraction_runs_admin_all (the sibling
--     extraction_runs_service_role_all policy is already correct; leave it).
do $$
begin
  if to_regclass('public.extraction_runs') is not null then
    drop policy if exists extraction_runs_admin_all on public.extraction_runs;
    create policy extraction_runs_admin_all on public.extraction_runs
      for all to authenticated
      using (public.is_admin(auth.uid()))
      with check (public.is_admin(auth.uid()));
  end if;
end $$;


-- ─────────────────────────────────────────────────────────────────────────────
-- Section 3 — Fix the 4 world-writable mock-question policies (migration 136)
-- ─────────────────────────────────────────────────────────────────────────────
-- Each was `for all using (true) with check (true)`. Recreate to mirror
-- mock_question_bank_admin_all: service_role OR app_metadata.role admin/super.

do $$
begin
  if to_regclass('public.mock_question_groups') is not null then
    drop policy if exists "mqg_admin_all" on public.mock_question_groups;
    create policy "mqg_admin_all"
      on public.mock_question_groups for all
      using (
        (select (auth.jwt() ->> 'role') in ('service_role'))
        or (select (auth.jwt() -> 'app_metadata' ->> 'role') in ('admin', 'super_admin'))
      )
      with check (
        (select (auth.jwt() ->> 'role') in ('service_role'))
        or (select (auth.jwt() -> 'app_metadata' ->> 'role') in ('admin', 'super_admin'))
      );
  end if;

  if to_regclass('public.mock_question_topic_tags') is not null then
    drop policy if exists "mqtt_admin_all" on public.mock_question_topic_tags;
    create policy "mqtt_admin_all"
      on public.mock_question_topic_tags for all
      using (
        (select (auth.jwt() ->> 'role') in ('service_role'))
        or (select (auth.jwt() -> 'app_metadata' ->> 'role') in ('admin', 'super_admin'))
      )
      with check (
        (select (auth.jwt() ->> 'role') in ('service_role'))
        or (select (auth.jwt() -> 'app_metadata' ->> 'role') in ('admin', 'super_admin'))
      );
  end if;

  if to_regclass('public.mock_question_sources') is not null then
    drop policy if exists "mqs_admin_all" on public.mock_question_sources;
    create policy "mqs_admin_all"
      on public.mock_question_sources for all
      using (
        (select (auth.jwt() ->> 'role') in ('service_role'))
        or (select (auth.jwt() -> 'app_metadata' ->> 'role') in ('admin', 'super_admin'))
      )
      with check (
        (select (auth.jwt() ->> 'role') in ('service_role'))
        or (select (auth.jwt() -> 'app_metadata' ->> 'role') in ('admin', 'super_admin'))
      );
  end if;

  if to_regclass('public.mock_question_review_log') is not null then
    drop policy if exists "mqrl_admin_all" on public.mock_question_review_log;
    create policy "mqrl_admin_all"
      on public.mock_question_review_log for all
      using (
        (select (auth.jwt() ->> 'role') in ('service_role'))
        or (select (auth.jwt() -> 'app_metadata' ->> 'role') in ('admin', 'super_admin'))
      )
      with check (
        (select (auth.jwt() ->> 'role') in ('service_role'))
        or (select (auth.jwt() -> 'app_metadata' ->> 'role') in ('admin', 'super_admin'))
      );
  end if;
end $$;


-- ─────────────────────────────────────────────────────────────────────────────
-- Section 4 — Enable RLS on audit / PII tables created without it
-- ─────────────────────────────────────────────────────────────────────────────
-- RLS on + NO policies => only service_role (bypasses RLS) can access.
-- Guarded so a missing/renamed table cannot fail the migration.

do $$
begin
  if to_regclass('public.support_content_access') is not null then
    execute 'alter table public.support_content_access enable row level security';
  end if;

  if to_regclass('public.content_access_requests') is not null then
    execute 'alter table public.content_access_requests enable row level security';
  end if;

  if to_regclass('public.mock_breakdown_recompute_runs') is not null then
    execute 'alter table public.mock_breakdown_recompute_runs enable row level security';
  end if;
end $$;

commit;

-- PostgREST: reload the schema cache so the policy/RLS changes take effect.
select pg_notify('pgrst', 'reload schema');
