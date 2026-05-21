-- 128_profile_merge_claims.sql
-- Anonymous → permanent profile merge on the Google "identity already exists"
-- conflict path.
--
-- Background: the v2 onboarding flow (migration 117) signs the guest in as a
-- Supabase anonymous user and writes progress against that profiles.id. On
-- linkIdentity the same id normally survives. But when the chosen Google
-- account's email already belongs to a *different* permanent profile, Supabase
-- refuses the link (identity_already_exists). The old frontend then signed the
-- anon user out and routed to /login — silently abandoning the anon profile and
-- everything written against it.
--
-- This migration adds the server-side machinery for a token-mediated merge:
--   * anonymous_profile_merge_claims — a short-lived, single-use claim minted by
--     the anon session and consumed by the permanent session after Google login.
--   * profile_merge_audit — an immutable record of what each consume merged.
--   * consume_profile_merge_claim() — the atomic, idempotent merge transaction.
--
-- Both tables have RLS enabled with NO policies: anon/authenticated roles get
-- zero access. Only service_role (which bypasses RLS) touches them, exclusively
-- through the backend endpoints in app/profile/merge_claim.py.

-- up
begin;

create table if not exists public.anonymous_profile_merge_claims (
  id uuid primary key default gen_random_uuid(),
  anonymous_user_id uuid not null references public.profiles(id) on delete cascade,
  claim_token_hash text not null unique,   -- sha256(hex) of the plaintext token
  expires_at timestamptz not null,         -- mint time + 15 minutes
  consumed_at timestamptz,
  consumed_by uuid references public.profiles(id),
  created_at timestamptz not null default now()
);

create index if not exists idx_merge_claims_anonymous_user_id
  on public.anonymous_profile_merge_claims (anonymous_user_id);

create table if not exists public.profile_merge_audit (
  id uuid primary key default gen_random_uuid(),
  claim_id uuid references public.anonymous_profile_merge_claims(id),
  anonymous_user_id uuid not null,
  permanent_user_id uuid not null,
  tables_merged jsonb not null,            -- {table: {inserted:n, skipped:n, ...}}
  ran_at timestamptz not null default now()
);

create index if not exists idx_profile_merge_audit_claim_id
  on public.profile_merge_audit (claim_id);

-- RLS on, no policies → only service_role (bypasses RLS) can read/write.
alter table public.anonymous_profile_merge_claims enable row level security;
alter table public.profile_merge_audit enable row level security;

-- ── consume_profile_merge_claim ────────────────────────────────────────────
-- Atomic, idempotent merge of an anonymous profile's onboarding progress into
-- a permanent profile. The token (its sha256 hash) is the bearer of authority:
-- whoever holds a valid permanent session AND the plaintext token may merge the
-- referenced anon profile into THEIR account. This is by design — the consuming
-- permanent user is whatever auth.uid() the backend passes as p_permanent_user_id.
--
-- Returns a discriminated jsonb result the endpoint maps to an HTTP status:
--   {status:'ok',               result:<tables_merged>, ...}  → 200
--   {status:'already_consumed', result:<prior tables_merged>} → 200 (idempotent)
--   {status:'not_found'}                                       → 404
--   {status:'expired'}                                         → 410
--   {status:'anon_missing'}                                    → 409
--   {status:'self_merge'}                                      → 409
--
-- Merge rules (permanent-wins-on-conflict unless permanent value is null/empty):
--   profiles                  per-column null-fill from anon; never id/email/
--                             is_admin/created_at/updated_at/is_anonymous;
--                             onboarding_completed = OR; persona_seed = jsonb
--                             merge with permanent keys winning.
--   aspirant_preferences      copy anon row only if permanent has none.
--   aspirant_education        same.
--   aspirant_location         same.
--   aspirant_reservations     same. (user_id is the PK → exactly one row per
--                             user, so the spec's "additive" is impossible; we
--                             copy-if-empty like the others.)
--   persona_question_answers  insert anon rows whose question_key the permanent
--                             user has no answer for; skip the rest.
create or replace function public.consume_profile_merge_claim(
    p_token_hash        text,
    p_permanent_user_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
    v_claim   public.anonymous_profile_merge_claims%rowtype;
    v_anon    uuid;
    v_prior   jsonb;
    v_tables  jsonb := '{}'::jsonb;
    v_col     text;
    v_filled  int := 0;
    v_n       int;
    v_ins     int;
    v_total   int;
begin
    -- Lock the claim so two concurrent consumes can't both merge.
    select * into v_claim
    from public.anonymous_profile_merge_claims
    where claim_token_hash = p_token_hash
    for update;

    if not found then
        return jsonb_build_object('status', 'not_found');
    end if;

    -- Idempotent replay: return the prior merge result, do NOT re-merge.
    if v_claim.consumed_at is not null then
        select tables_merged into v_prior
        from public.profile_merge_audit
        where claim_id = v_claim.id
        order by ran_at desc
        limit 1;
        return jsonb_build_object(
            'status', 'already_consumed',
            'result', coalesce(v_prior, '{}'::jsonb),
            'anonymous_user_id', v_claim.anonymous_user_id,
            'permanent_user_id', v_claim.consumed_by
        );
    end if;

    if v_claim.expires_at < now() then
        return jsonb_build_object('status', 'expired');
    end if;

    v_anon := v_claim.anonymous_user_id;

    perform 1 from public.profiles where id = v_anon;
    if not found then
        return jsonb_build_object('status', 'anon_missing');
    end if;

    if v_anon = p_permanent_user_id then
        return jsonb_build_object('status', 'self_merge');
    end if;

    -- ── profiles: per-column null-fill ─────────────────────────────────────
    -- Copy any column the permanent row left NULL where the anon row has a
    -- value. The denylist protects identity/admin/bookkeeping columns and the
    -- columns we merge with bespoke rules below.
    for v_col in
        select column_name
        from information_schema.columns
        where table_schema = 'public'
          and table_name = 'profiles'
          and column_name not in (
              'id', 'email', 'is_admin', 'created_at', 'updated_at',
              'is_anonymous', 'onboarding_completed', 'onboarding_step',
              'persona_seed'
          )
    loop
        execute format(
            'update public.profiles p set %1$I = a.%1$I '
            'from public.profiles a '
            'where p.id = $1 and a.id = $2 '
            '  and p.%1$I is null and a.%1$I is not null',
            v_col
        ) using p_permanent_user_id, v_anon;
        get diagnostics v_n = row_count;
        v_filled := v_filled + v_n;
    end loop;

    -- onboarding_completed = permanent OR anon
    update public.profiles p
       set onboarding_completed =
               coalesce(p.onboarding_completed, false)
               or coalesce(a.onboarding_completed, false),
           updated_at = now()
      from public.profiles a
     where p.id = p_permanent_user_id and a.id = v_anon;

    -- persona_seed: jsonb merge, permanent keys win (anon || permanent).
    update public.profiles p
       set persona_seed =
               coalesce(a.persona_seed, '{}'::jsonb)
               || coalesce(p.persona_seed, '{}'::jsonb)
      from public.profiles a
     where p.id = p_permanent_user_id and a.id = v_anon
       and a.persona_seed is not null;

    v_tables := v_tables || jsonb_build_object(
        'profiles', jsonb_build_object('columns_filled', v_filled)
    );

    -- ── aspirant_preferences (copy-if-empty) ───────────────────────────────
    select count(*) into v_n
      from public.aspirant_preferences where user_id = p_permanent_user_id;
    if v_n = 0 then
        insert into public.aspirant_preferences
            (user_id, preferred_sectors, preferred_states, willing_to_relocate,
             target_exams, study_mode, study_hours_per_day)
        select p_permanent_user_id, preferred_sectors, preferred_states,
               willing_to_relocate, target_exams, study_mode, study_hours_per_day
          from public.aspirant_preferences where user_id = v_anon;
        get diagnostics v_ins = row_count;
    else
        v_ins := 0;
    end if;
    v_tables := v_tables || jsonb_build_object(
        'aspirant_preferences',
        jsonb_build_object('inserted', v_ins, 'skipped', case when v_n > 0 then 1 else 0 end)
    );

    -- ── aspirant_education (copy-if-empty) ──────────────────────────────────
    select count(*) into v_n
      from public.aspirant_education where user_id = p_permanent_user_id;
    if v_n = 0 then
        insert into public.aspirant_education
            (user_id, level, degree, stream, institution, university,
             graduation_year, percentage, cgpa, is_completed)
        select p_permanent_user_id, level, degree, stream, institution, university,
               graduation_year, percentage, cgpa, is_completed
          from public.aspirant_education where user_id = v_anon;
        get diagnostics v_ins = row_count;
    else
        v_ins := 0;
    end if;
    v_tables := v_tables || jsonb_build_object(
        'aspirant_education',
        jsonb_build_object('inserted', v_ins, 'skipped', case when v_n > 0 then 1 else 0 end)
    );

    -- ── aspirant_location (copy-if-empty) ───────────────────────────────────
    select count(*) into v_n
      from public.aspirant_location where user_id = p_permanent_user_id;
    if v_n = 0 then
        insert into public.aspirant_location
            (user_id, state, district, is_rural, domicile_certificate)
        select p_permanent_user_id, state, district, is_rural, domicile_certificate
          from public.aspirant_location where user_id = v_anon;
        get diagnostics v_ins = row_count;
    else
        v_ins := 0;
    end if;
    v_tables := v_tables || jsonb_build_object(
        'aspirant_location',
        jsonb_build_object('inserted', v_ins, 'skipped', case when v_n > 0 then 1 else 0 end)
    );

    -- ── aspirant_reservations (copy-if-empty; user_id is PK) ────────────────
    select count(*) into v_n
      from public.aspirant_reservations where user_id = p_permanent_user_id;
    if v_n = 0 then
        insert into public.aspirant_reservations
            (user_id, category, sub_category, is_pwd, pwd_type, is_ex_serviceman,
             is_jk_domicile, is_widow, age_relaxation_extra_years)
        select p_permanent_user_id, category, sub_category, is_pwd, pwd_type,
               is_ex_serviceman, is_jk_domicile, is_widow, age_relaxation_extra_years
          from public.aspirant_reservations where user_id = v_anon;
        get diagnostics v_ins = row_count;
    else
        v_ins := 0;
    end if;
    v_tables := v_tables || jsonb_build_object(
        'aspirant_reservations',
        jsonb_build_object('inserted', v_ins, 'skipped', case when v_n > 0 then 1 else 0 end)
    );

    -- ── persona_question_answers (insert non-duplicate question_keys) ───────
    select count(*) into v_total
      from public.persona_question_answers where user_id = v_anon;
    insert into public.persona_question_answers
        (user_id, question_key, answer_value, normalized_value, skipped,
         source, confidence, needs_review, created_at)
    select p_permanent_user_id, a.question_key, a.answer_value, a.normalized_value,
           a.skipped, a.source, a.confidence, a.needs_review, a.created_at
      from public.persona_question_answers a
     where a.user_id = v_anon
       and not exists (
           select 1 from public.persona_question_answers p
           where p.user_id = p_permanent_user_id
             and p.question_key = a.question_key
       );
    get diagnostics v_ins = row_count;
    v_tables := v_tables || jsonb_build_object(
        'persona_question_answers',
        jsonb_build_object('inserted', v_ins, 'skipped', greatest(v_total - v_ins, 0))
    );

    -- ── mark consumed + audit ───────────────────────────────────────────────
    update public.anonymous_profile_merge_claims
       set consumed_at = now(), consumed_by = p_permanent_user_id
     where id = v_claim.id;

    insert into public.profile_merge_audit
        (claim_id, anonymous_user_id, permanent_user_id, tables_merged)
    values (v_claim.id, v_anon, p_permanent_user_id, v_tables);

    -- ── delete the anonymous profile ────────────────────────────────────────
    -- The migration-002 aspirant_* FKs have NO on-delete-cascade, so clear them
    -- first. persona_* / signal / recompute children DO cascade. We guard the
    -- final profiles delete: if some unforeseen FK child still references the
    -- anon row, leave it for the daily anonymous-cleanup cron rather than rolling
    -- back a merge that already succeeded.
    delete from public.aspirant_preferences      where user_id = v_anon;
    delete from public.aspirant_education         where user_id = v_anon;
    delete from public.aspirant_location          where user_id = v_anon;
    delete from public.aspirant_reservations      where user_id = v_anon;
    delete from public.aspirant_certifications    where user_id = v_anon;
    delete from public.aspirant_experience        where user_id = v_anon;
    delete from public.aspirant_exam_attempts     where user_id = v_anon;
    delete from public.aspirant_exam_credentials  where user_id = v_anon;

    begin
        delete from public.profiles where id = v_anon;
    exception when foreign_key_violation then
        raise notice 'consume_profile_merge_claim: anon profile % left for cron (FK child still present)', v_anon;
    end;

    return jsonb_build_object(
        'status', 'ok',
        'result', v_tables,
        'anonymous_user_id', v_anon,
        'permanent_user_id', p_permanent_user_id
    );
end;
$$;

grant execute on function public.consume_profile_merge_claim(text, uuid) to service_role;

commit;

notify pgrst, 'reload schema';

-- rollback (manual only):
-- drop function if exists public.consume_profile_merge_claim(text, uuid);
-- drop table if exists public.profile_merge_audit;
-- drop table if exists public.anonymous_profile_merge_claims;
