-- 310_authored_question_explanations.sql
-- REG-CORPUS-02 P4 (gap 8) — structured explanations for AUTHORED questions.
--
-- pyq_question_explanations (migration 230) is the one structured-explanation
-- shape (steps, option rationales, formula_used, traps) and review lifecycle.
-- It is keyed to pyq_questions only, so an authored mock_question_bank row can
-- carry nothing but the flat `explanation` column. This migration lets the SAME
-- table key a row to exactly one of:
--
--   question_id       -> pyq_questions(id)        (unchanged, PYQ rows)
--   mock_question_id  -> mock_question_bank(id)   (new, authored rows)
--
-- CHECK exactly one of the two is set. Authored rows' structured answer points
-- at mock_question_options through two new columns (final_/alternate_answer_
-- mock_option_id); a second CHECK stops a row mixing the two option families.
-- option_rationales stays a jsonb object, keyed by the option id of whichever
-- family the row belongs to (pyq_options.id or mock_question_options.id).
--
-- The guard trigger and the fenced review RPC are re-created with the 230 body
-- plus the mock-side equivalents of each rule: same-question answer integrity,
-- content-edit downgrade to needs_correction, and fail-closed verification
-- (a final answer is required on whichever side the row is keyed to). PYQ-side
-- rules keep their 230 meaning; the only changes are `<>` -> `IS DISTINCT FROM`
-- in the option-integrity checks (identical whenever question_id is set) and a
-- re-key (question_id / mock_question_id change) of a verified row now also
-- downgrades it to needs_correction.
--
-- Safe on a DB with live PYQ rows: DROP NOT NULL and nullable ADD COLUMNs are
-- catalog-only; every existing row has question_id set and the new columns
-- NULL, so both CHECKs validate (NOT VALID + VALIDATE: the scan holds SHARE
-- UPDATE EXCLUSIVE only). The existing unique (question_id,
-- explanation_source_type) still governs PYQ rows (NULL question_id never
-- collides); a partial unique index gives authored rows the same rule. Function
-- signatures, grants and the RLS policy are unchanged. Live row count was 0 at
-- REG-CORPUS-01 (inventory §7 / 6.2).

begin;

-- ── Schema ────────────────────────────────────────────────────────────────
alter table public.pyq_question_explanations
  alter column question_id drop not null;

alter table public.pyq_question_explanations
  add column if not exists mock_question_id uuid
    references public.mock_question_bank(id) on delete cascade,
  add column if not exists final_answer_mock_option_id uuid
    references public.mock_question_options(id) on delete set null,
  add column if not exists alternate_answer_mock_option_id uuid
    references public.mock_question_options(id) on delete set null;

comment on column public.pyq_question_explanations.mock_question_id is
  'Authored (non-PYQ) question this explanation belongs to. Exactly one of '
  'question_id / mock_question_id is set (pyq_question_explanations_one_question).';

do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conname = 'pyq_question_explanations_one_question'
      and conrelid = 'public.pyq_question_explanations'::regclass
  ) then
    alter table public.pyq_question_explanations
      add constraint pyq_question_explanations_one_question
      check (num_nonnulls(question_id, mock_question_id) = 1) not valid;
  end if;
  if not exists (
    select 1 from pg_constraint
    where conname = 'pyq_question_explanations_answer_family'
      and conrelid = 'public.pyq_question_explanations'::regclass
  ) then
    alter table public.pyq_question_explanations
      add constraint pyq_question_explanations_answer_family
      check (
        (question_id is not null
          and final_answer_mock_option_id is null
          and alternate_answer_mock_option_id is null)
        or
        (mock_question_id is not null
          and final_answer_option_id is null
          and alternate_answer_option_id is null)
      ) not valid;
  end if;
end $$;

alter table public.pyq_question_explanations
  validate constraint pyq_question_explanations_one_question;
alter table public.pyq_question_explanations
  validate constraint pyq_question_explanations_answer_family;

create unique index if not exists uq_pyq_question_explanations_mock_source
  on public.pyq_question_explanations (mock_question_id, explanation_source_type)
  where mock_question_id is not null;

create index if not exists idx_pyq_question_explanations_mock_question
  on public.pyq_question_explanations (mock_question_id)
  where mock_question_id is not null;

-- ── Guard (230 body + mock-side rules) ─────────────────────────────────────
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
    if v_q is null or v_q is distinct from new.question_id then
      raise exception
        'final_answer_option_id % does not belong to question %',
        new.final_answer_option_id, new.question_id;
    end if;
  end if;
  if new.alternate_answer_option_id is not null then
    select question_id into v_q
      from public.pyq_options where id = new.alternate_answer_option_id for share;
    if v_q is null or v_q is distinct from new.question_id then
      raise exception
        'alternate_answer_option_id % does not belong to question %',
        new.alternate_answer_option_id, new.question_id;
    end if;
  end if;
  -- 1b. Same rule for authored rows against mock_question_options.
  if new.final_answer_mock_option_id is not null then
    select question_id into v_q
      from public.mock_question_options where id = new.final_answer_mock_option_id for share;
    if v_q is null or v_q is distinct from new.mock_question_id then
      raise exception
        'final_answer_mock_option_id % does not belong to mock question %',
        new.final_answer_mock_option_id, new.mock_question_id;
    end if;
  end if;
  if new.alternate_answer_mock_option_id is not null then
    select question_id into v_q
      from public.mock_question_options where id = new.alternate_answer_mock_option_id for share;
    if v_q is null or v_q is distinct from new.mock_question_id then
      raise exception
        'alternate_answer_mock_option_id % does not belong to mock question %',
        new.alternate_answer_mock_option_id, new.mock_question_id;
    end if;
  end if;

  -- 2. Editing an already-verified row (without an explicit status change in the
  --    same statement) forces re-review. Covers ALL learner-facing content AND
  --    trust/provenance fields, now including the authored-side keys.
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
       or new.final_answer_mock_option_id is distinct from old.final_answer_mock_option_id
       or new.alternate_answer_mock_option_id is distinct from old.alternate_answer_mock_option_id
       or new.ambiguity_status is distinct from old.ambiguity_status
       -- identity
       or new.question_id is distinct from old.question_id
       or new.mock_question_id is distinct from old.mock_question_id
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
    if new.question_id is not null and new.final_answer_option_id is null then
      raise exception 'verify_requires_final_answer: final_answer_option_id is null';
    end if;
    if new.mock_question_id is not null and new.final_answer_mock_option_id is null then
      raise exception 'verify_requires_final_answer: final_answer_mock_option_id is null';
    end if;
    if new.reviewed_by is null or new.reviewed_at is null then
      raise exception 'verify_requires_reviewer_identity: reviewed_by/reviewed_at must be set';
    end if;
  end if;

  return new;
end;
$fn$;

-- Trigger binding is unchanged from 230 (same name, same function); re-assert it
-- so this migration is self-sufficient if replayed on its own.
drop trigger if exists trg_pyq_question_explanations_guard on public.pyq_question_explanations;
create trigger trg_pyq_question_explanations_guard
  before insert or update on public.pyq_question_explanations
  for each row execute function public.pyq_question_explanations_guard();

-- ── Fenced review RPC (230 body; verify precondition is side-aware) ─────────
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
    if v_row.question_id is not null and v_row.final_answer_option_id is null then
      raise exception 'verify_requires_final_answer: final_answer_option_id is null';
    end if;
    if v_row.mock_question_id is not null and v_row.final_answer_mock_option_id is null then
      raise exception 'verify_requires_final_answer: final_answer_mock_option_id is null';
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

commit;

notify pgrst, 'reload schema';

-- DOWN (manual; only valid while no authored explanation rows exist):
--   delete from public.pyq_question_explanations where mock_question_id is not null;
--   re-apply the 230 bodies of pyq_question_explanations_guard() and
--   cms_review_pyq_question_explanation();
--   drop index if exists public.idx_pyq_question_explanations_mock_question;
--   drop index if exists public.uq_pyq_question_explanations_mock_source;
--   alter table public.pyq_question_explanations
--     drop constraint if exists pyq_question_explanations_answer_family,
--     drop constraint if exists pyq_question_explanations_one_question,
--     drop column if exists alternate_answer_mock_option_id,
--     drop column if exists final_answer_mock_option_id,
--     drop column if exists mock_question_id,
--     alter column question_id set not null;
