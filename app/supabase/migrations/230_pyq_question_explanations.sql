-- 230_pyq_question_explanations.sql
-- First-class explanation layer for PYQ questions (schema + governance only).
--
-- Checkpost (PR #904) required split of schema from third-party data ingestion:
-- this migration deliberately commits NO explanation corpus. Coaching-derived
-- reference material is ingested out-of-band through an operator import path
-- against a document asset with recorded provenance + permission basis (see
-- docs/architecture/pyq-explanations.md); only platform-owned or cleared
-- explanation text may ever be committed. This file lands the reviewable
-- governance object: table, structured answer references, provenance columns,
-- fail-closed verification, an audited review RPC, and admin-only RLS.
--
-- Design points addressed from the checkpost review:
--   * Structured answer: final_answer_option_id / alternate_answer_option_id FK
--     to pyq_options, with a same-question integrity trigger (no free-text
--     A/B/C/D label that can drift from the canonical uppercase option labels).
--   * Provenance: source_url is for the ACTUAL explanation source only;
--     source_document_id (+ source_hash) carries the imported reference doc.
--     Neither is populated here.
--   * Fail-closed verification: reviewer_status='verified' is rejected unless the
--     licence is cleared, ambiguity is resolved, a final answer is asserted, and
--     reviewer identity/timestamp are present — enforced on INSERT and UPDATE
--     (initial verification and direct status changes), not only on content edit.
--   * Independent review lifecycle: explanations carry their own reviewer_status
--     so a question can be verified while its explanation still needs correction.
--   * Fenced review: cms_review_pyq_question_explanation() (SECURITY DEFINER,
--     service_role only) performs the audited state transition; direct mutation
--     stays possible but is guarded by the same fail-closed trigger.

-- ── Schema ────────────────────────────────────────────────────────────────
create table if not exists public.pyq_question_explanations (
  id uuid primary key default gen_random_uuid(),
  question_id uuid not null references public.pyq_questions(id) on delete cascade,

  short_explanation text,
  explanation_text text,
  solution_steps jsonb not null default '[]'::jsonb,
  option_rationales jsonb not null default '{}'::jsonb,
  formula_used jsonb not null default '[]'::jsonb,
  common_traps jsonb not null default '[]'::jsonb,

  -- Structured answer references (FK to the canonical options); a same-question
  -- integrity trigger proves each belongs to question_id.
  final_answer_option_id uuid references public.pyq_options(id) on delete set null,
  alternate_answer_option_id uuid references public.pyq_options(id) on delete set null,

  ambiguity_status text not null default 'none'
    check (ambiguity_status in ('none', 'disputed', 'multiple_possible', 'source_conflict')),

  -- Provenance. source_url is ONLY the real explanation source (never a generic
  -- homepage). source_document_id/source_hash carry an imported reference doc.
  explanation_source_type text not null default 'platform_original'
    check (explanation_source_type in ('official', 'platform_original', 'coaching', 'community', 'imported')),
  source_url text,
  source_document_id uuid references public.document_assets(id) on delete set null,
  source_hash text,

  license_status text not null default 'owned'
    check (license_status in ('owned', 'licensed', 'public_domain', 'permission_pending', 'restricted')),

  reviewer_status text not null default 'pending'
    check (reviewer_status in ('pending', 'verified', 'rejected', 'needs_correction')),
  reviewed_by uuid references public.profiles(id) on delete set null,
  reviewed_at timestamptz,

  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  unique (question_id, explanation_source_type)
);

create index if not exists idx_pyq_question_explanations_question
  on public.pyq_question_explanations(question_id);
create index if not exists idx_pyq_question_explanations_review
  on public.pyq_question_explanations(reviewer_status);
create index if not exists idx_pyq_question_explanations_license
  on public.pyq_question_explanations(license_status);
create index if not exists idx_pyq_question_explanations_source_document
  on public.pyq_question_explanations(source_document_id)
  where source_document_id is not null;

do $$
begin
  if not exists (
    select 1 from pg_trigger
    where tgname = 'trg_pyq_question_explanations_updated_at'
      and tgrelid = 'public.pyq_question_explanations'::regclass
  ) then
    create trigger trg_pyq_question_explanations_updated_at
      before update on public.pyq_question_explanations
      for each row execute function public.tg_set_updated_at();
  end if;
end $$;

-- ── Guard: same-question answer integrity + content-edit downgrade +
--    fail-closed verification, in one deterministic BEFORE trigger ───────────
create or replace function public.pyq_question_explanations_guard()
returns trigger
language plpgsql
as $fn$
declare
  v_q uuid;
begin
  -- 1. Same-question integrity for the structured answer references.
  if new.final_answer_option_id is not null then
    select question_id into v_q
      from public.pyq_options where id = new.final_answer_option_id for share;
    if v_q is null or v_q <> new.question_id then
      raise exception
        'final_answer_option_id % does not belong to question %',
        new.final_answer_option_id, new.question_id;
    end if;
  end if;
  if new.alternate_answer_option_id is not null then
    select question_id into v_q
      from public.pyq_options where id = new.alternate_answer_option_id for share;
    if v_q is null or v_q <> new.question_id then
      raise exception
        'alternate_answer_option_id % does not belong to question %',
        new.alternate_answer_option_id, new.question_id;
    end if;
  end if;

  -- 2. Editing an already-verified row (without an explicit status change in the
  --    same statement) forces re-review. Runs BEFORE the verification gate below
  --    so the downgrade is what gets validated. Covers ALL learner-facing
  --    content AND trust/provenance fields — a change to any of them invalidates
  --    the prior verification (checkpost PR #904, 2nd pass).
  if tg_op = 'UPDATE'
     and old.reviewer_status = 'verified'
     and new.reviewer_status is not distinct from old.reviewer_status
     and (
       -- learner-facing content
       new.explanation_text is distinct from old.explanation_text
       or new.short_explanation is distinct from old.short_explanation
       or new.solution_steps is distinct from old.solution_steps
       or new.option_rationales is distinct from old.option_rationales
       or new.formula_used is distinct from old.formula_used
       or new.common_traps is distinct from old.common_traps
       or new.final_answer_option_id is distinct from old.final_answer_option_id
       or new.alternate_answer_option_id is distinct from old.alternate_answer_option_id
       or new.ambiguity_status is distinct from old.ambiguity_status
       -- trust / provenance
       or new.explanation_source_type is distinct from old.explanation_source_type
       or new.source_url is distinct from old.source_url
       or new.source_document_id is distinct from old.source_document_id
       or new.source_hash is distinct from old.source_hash
       or new.license_status is distinct from old.license_status
     )
  then
    new.reviewer_status := 'needs_correction';
    new.reviewed_by := null;
    new.reviewed_at := null;
  end if;

  -- 3. Fail-closed verification preconditions (initial verify + direct changes).
  if new.reviewer_status = 'verified' then
    if new.license_status not in ('owned', 'licensed', 'public_domain') then
      raise exception 'verify_requires_cleared_license: license_status=%', new.license_status;
    end if;
    if new.ambiguity_status <> 'none' then
      raise exception 'verify_requires_resolved_ambiguity: ambiguity_status=%', new.ambiguity_status;
    end if;
    if new.final_answer_option_id is null then
      raise exception 'verify_requires_final_answer: final_answer_option_id is null';
    end if;
    if new.reviewed_by is null or new.reviewed_at is null then
      raise exception 'verify_requires_reviewer_identity: reviewed_by/reviewed_at must be set';
    end if;
  end if;

  return new;
end;
$fn$;

drop trigger if exists trg_pyq_question_explanations_guard on public.pyq_question_explanations;
create trigger trg_pyq_question_explanations_guard
  before insert or update on public.pyq_question_explanations
  for each row execute function public.pyq_question_explanations_guard();

-- ── RLS: admin / service-role only (mirrors pyq_stimuli, migrations 035/223) ─
alter table public.pyq_question_explanations enable row level security;
do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'pyq_question_explanations'
      and policyname = 'pyq_question_explanations_admin_all'
  ) then
    create policy pyq_question_explanations_admin_all on public.pyq_question_explanations
      for all to authenticated
      using (public.is_admin(auth.uid()))
      with check (public.is_admin(auth.uid()));
  end if;
end $$;

-- Table-level grants. Post-173 tables do not inherit migration 173's one-time
-- blanket grant (no ALTER DEFAULT PRIVILEGES exists), so service_role — which
-- bypasses RLS but still needs Postgres grants — must be granted explicitly, or
-- the operator/import path and direct admin writes hit 42501 (same lesson as
-- migration 225 for pyq_stimuli). authenticated is granted deliberately so the
-- admin-only RLS policy above is actually usable via PostgREST; RLS still
-- restricts authenticated rows to is_admin(auth.uid()).
grant select, insert, update, delete on public.pyq_question_explanations to service_role;
grant select, insert, update, delete on public.pyq_question_explanations to authenticated;

-- ── Fenced review RPC (audited state transition; service_role only) ─────────
create or replace function public.cms_review_pyq_question_explanation(
  p_id              text,
  p_expected_status text,
  p_target_status   text,
  p_reviewer_notes  text,
  p_actor_user_id   text,
  p_actor_email     text
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $fn$
declare
  v_row public.pyq_question_explanations;
  v_audit_id uuid;
begin
  if p_target_status not in ('verified', 'rejected', 'needs_correction', 'pending') then
    raise exception 'invalid_target_status: %', p_target_status;
  end if;

  select * into v_row
    from public.pyq_question_explanations
   where id = p_id::uuid
   for update;
  if not found then
    raise exception 'not_found: explanation % does not exist', p_id;
  end if;

  if v_row.reviewer_status is distinct from p_expected_status then
    raise exception 'concurrent_modification: expected % but row is %',
      p_expected_status, v_row.reviewer_status;
  end if;

  -- Transition matrix.
  if not (
       (v_row.reviewer_status = 'pending'          and p_target_status in ('verified', 'rejected', 'needs_correction'))
    or (v_row.reviewer_status = 'needs_correction' and p_target_status in ('verified', 'rejected', 'pending'))
    or (v_row.reviewer_status = 'verified'         and p_target_status in ('needs_correction', 'rejected'))
    or (v_row.reviewer_status = 'rejected'         and p_target_status in ('pending', 'needs_correction'))
  ) then
    raise exception 'transition_not_allowed: % -> %', v_row.reviewer_status, p_target_status;
  end if;

  if p_target_status = 'verified' then
    -- Preconditions (belt-and-suspenders with the guard trigger).
    if v_row.license_status not in ('owned', 'licensed', 'public_domain') then
      raise exception 'verify_requires_cleared_license: license_status=%', v_row.license_status;
    end if;
    if v_row.ambiguity_status <> 'none' then
      raise exception 'verify_requires_resolved_ambiguity: ambiguity_status=%', v_row.ambiguity_status;
    end if;
    if v_row.final_answer_option_id is null then
      raise exception 'verify_requires_final_answer: final_answer_option_id is null';
    end if;
    update public.pyq_question_explanations
       set reviewer_status = 'verified',
           reviewed_by = p_actor_user_id::uuid,
           reviewed_at = now(),
           updated_at = now()
     where id = v_row.id;
  elsif p_target_status in ('rejected', 'needs_correction') then
    update public.pyq_question_explanations
       set reviewer_status = p_target_status,
           reviewed_by = p_actor_user_id::uuid,
           reviewed_at = now(),
           updated_at = now()
     where id = v_row.id;
  else  -- 'pending' reset
    update public.pyq_question_explanations
       set reviewer_status = 'pending',
           reviewed_by = null,
           reviewed_at = null,
           updated_at = now()
     where id = v_row.id;
  end if;

  insert into public.admin_audit_logs
    (actor_id, actor_email, admin_user_id, action, entity_type, entity_id, old_value, new_value, notes)
  values
    (nullif(p_actor_user_id, '')::uuid, p_actor_email, nullif(p_actor_user_id, '')::uuid,
     'pyq_explanation_review_transition', 'pyq_question_explanation', v_row.id::text,
     jsonb_build_object('reviewer_status', v_row.reviewer_status),
     jsonb_build_object('reviewer_status', p_target_status),
     p_reviewer_notes)
  returning id into v_audit_id;

  return jsonb_build_object(
    'ok', true,
    'id', v_row.id,
    'prev_status', v_row.reviewer_status,
    'new_status', p_target_status,
    'audit_id', v_audit_id
  );
end;
$fn$;

revoke execute on function public.cms_review_pyq_question_explanation(text, text, text, text, text, text) from public;
revoke execute on function public.cms_review_pyq_question_explanation(text, text, text, text, text, text) from anon;
revoke execute on function public.cms_review_pyq_question_explanation(text, text, text, text, text, text) from authenticated;
grant  execute on function public.cms_review_pyq_question_explanation(text, text, text, text, text, text) to service_role;

notify pgrst, 'reload schema';
