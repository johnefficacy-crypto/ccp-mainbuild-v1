-- 303_answer_structures.sql
-- Answer writing: a reviewed ANSWER STRUCTURE per descriptive question.
--
-- WHY THIS EXISTS. Self-evaluation against the generic six-criterion rubric
-- (migration 293) tells an aspirant HOW they wrote, never WHAT the question
-- wanted. An answer structure is the missing half: the directive, what the
-- question demands, and the points a good answer must carry. It is NOT a model
-- essay — no finished prose an aspirant could memorise and reproduce.
--
-- AI DRAFTS, HUMANS VERIFY. Rows are drafted by
-- scripts/generate_answer_structures.py (status 'draft' only) and reach an
-- aspirant only after a Content Studio reviewer sets status='verified'. The
-- learner read below is verified-only AND conjunctive with the question's own
-- reviewer_status, so an unverified question can never leak through a verified
-- structure.
--
-- VERSIONING. A regenerated structure is a NEW row (version + 1), never an
-- overwrite: an attempt that ticked points against version 2 must still be
-- measurable against version 2 after version 3 is verified. At most one
-- version per question is 'verified' at a time (partial unique index);
-- approving a new version demotes the old one inside the same transaction.
--
-- Applied version = MAX(filesystem)+1 at authoring (302_ca_reading_sources_in_resources).
-- Reconcile against the deployed state before applying to any environment:
--   SELECT MAX(version) FROM supabase_migrations.schema_migrations;
-- Migrations are immutable once merged.

begin;

-- ═════════════════════════════════════════════════════════════════════════
-- A. answer_structures
-- ═════════════════════════════════════════════════════════════════════════

create table if not exists public.answer_structures (
  id uuid primary key default gen_random_uuid(),
  pyq_question_id uuid not null
    references public.pyq_questions(id) on delete cascade,
  version integer not null check (version >= 1),

  status text not null default 'draft'
    check (status in ('draft', 'in_review', 'verified', 'rejected')),

  -- "Critically examine", "Discuss", ... — the instruction word the answer
  -- has to obey, and 1–2 lines on what the question is actually asking.
  directive text not null check (char_length(btrim(directive)) between 1 and 80),
  demand text not null check (char_length(btrim(demand)) between 1 and 400),

  -- Shapes are validated in the API (app/study_os/answer_structure_schema.py)
  -- rather than by deep CHECKs, so a schema revision does not need an
  -- immutable migration edited. The CHECKs pin only the top-level JSON type.
  intro_angles jsonb not null default '[]'::jsonb
    check (jsonb_typeof(intro_angles) = 'array'),
  -- Ordered. Each: {id, point, why, evidence_type, example, thinker, sub_points}.
  -- `id` is what an attempt's covered_point_ids refers to.
  body_points jsonb not null default '[]'::jsonb
    check (jsonb_typeof(body_points) = 'array'),
  dimensions jsonb not null default '[]'::jsonb
    check (jsonb_typeof(dimensions) = 'array'),
  examples jsonb not null default '[]'::jsonb
    check (jsonb_typeof(examples) = 'array'),
  conclusion_angles jsonb not null default '[]'::jsonb
    check (jsonb_typeof(conclusion_angles) = 'array'),
  pitfalls jsonb not null default '[]'::jsonb
    check (jsonb_typeof(pitfalls) = 'array'),
  -- {total, intro, body, conclusion, basis}. Derived deterministically from the
  -- question's word_limit or marks when known; null parts when not.
  word_budget jsonb null
    check (word_budget is null or jsonb_typeof(word_budget) = 'object'),
  sources_note text null,

  -- Provenance. `generated_by` is 'ai:<model>' or 'human:<user id>'.
  -- generation_meta carries model, prompt version, tokens, cost, retries,
  -- uncertainty flags and lint warnings — reviewer-facing, never learner-facing.
  generated_by text not null,
  generation_meta jsonb not null default '{}'::jsonb
    check (jsonb_typeof(generation_meta) = 'object'),

  reviewed_by uuid null references auth.users(id) on delete set null,
  reviewed_at timestamptz null,
  review_notes text null,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint answer_structures_question_version_unique
    unique (pyq_question_id, version),
  -- A rejection must say why: the note is what the next regeneration and the
  -- next reviewer read.
  constraint answer_structures_rejected_has_note
    check (status <> 'rejected' or nullif(btrim(coalesce(review_notes, '')), '') is not null),
  -- A verified row names who verified it and when.
  constraint answer_structures_verified_is_attributed
    check (status <> 'verified' or (reviewed_by is not null and reviewed_at is not null))
);

-- ONE verified structure per question. Learners read "the" structure for a
-- question; two verified versions would make that read ambiguous.
create unique index if not exists uq_answer_structures_one_verified
  on public.answer_structures(pyq_question_id)
  where status = 'verified';

create index if not exists idx_answer_structures_status
  on public.answer_structures(status, updated_at desc);
create index if not exists idx_answer_structures_question
  on public.answer_structures(pyq_question_id, version desc);

comment on table public.answer_structures is
  'Reviewed answer structure (directive, demand, body-point checklist, angles, '
  'pitfalls) for a descriptive PYQ. AI-drafted, human-verified; learners read '
  'status=verified only. Not a model answer.';

-- updated_at is the content CAS token consumed by the review/update RPCs, so it
-- is maintained in the database: any edit invalidates a reviewer's snapshot.
drop trigger if exists answer_structures_updated_at on public.answer_structures;
create trigger answer_structures_updated_at
before update on public.answer_structures
for each row execute function public.tg_set_updated_at();

-- ── RLS ──────────────────────────────────────────────────────────────────
alter table public.answer_structures enable row level security;

do $$
begin
  -- Learners: verified structures of verified questions only.
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'answer_structures'
      and policyname = 'answer_structures_learner_select_verified'
  ) then
    create policy answer_structures_learner_select_verified
      on public.answer_structures
      for select to authenticated
      using (
        status = 'verified'
        and exists (
          select 1 from public.pyq_questions q
          where q.id = answer_structures.pyq_question_id
            and q.reviewer_status = 'verified'
        )
      );
  end if;

  -- Admin roles: read every status (the review queue).
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'answer_structures'
      and policyname = 'answer_structures_admin_select'
  ) then
    create policy answer_structures_admin_select
      on public.answer_structures
      for select to authenticated
      using (public.is_admin(auth.uid()));
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'answer_structures'
      and policyname = 'answer_structures_admin_insert'
  ) then
    create policy answer_structures_admin_insert
      on public.answer_structures
      for insert to authenticated
      with check (public.is_admin(auth.uid()));
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'answer_structures'
      and policyname = 'answer_structures_admin_update'
  ) then
    create policy answer_structures_admin_update
      on public.answer_structures
      for update to authenticated
      using (public.is_admin(auth.uid()))
      with check (public.is_admin(auth.uid()));
  end if;
end $$;

-- Explicit grants. No DELETE/TRUNCATE for authenticated: a structure is
-- retired by rejecting it, and the version history is the audit record.
revoke all on public.answer_structures from public;
revoke all on public.answer_structures from anon;
revoke all on public.answer_structures from authenticated;
grant select, insert, update on public.answer_structures to authenticated;
grant select, insert, update, delete on public.answer_structures to service_role;

-- ═════════════════════════════════════════════════════════════════════════
-- B. descriptive_attempts — which points the aspirant says they covered
-- ═════════════════════════════════════════════════════════════════════════
-- Both null until the aspirant opens the comparison and ticks. The version is
-- stored beside the ticks because a tick is only meaningful against the
-- body_points of the structure it was made against.
alter table public.descriptive_attempts
  add column if not exists structure_version integer null
    check (structure_version is null or structure_version >= 1),
  add column if not exists covered_point_ids jsonb null
    check (covered_point_ids is null or jsonb_typeof(covered_point_ids) = 'array');

do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conname = 'descriptive_attempts_coverage_pairs'
  ) then
    alter table public.descriptive_attempts
      add constraint descriptive_attempts_coverage_pairs
      check ((structure_version is null) = (covered_point_ids is null));
  end if;
end $$;

comment on column public.descriptive_attempts.covered_point_ids is
  'body_points ids of answer_structures (pyq_question_id, structure_version) the '
  'aspirant ticked as covered after submitting. Self-reported, never machine-scored.';

-- ═════════════════════════════════════════════════════════════════════════
-- C. Write RPCs — every lifecycle write is atomic and audited
-- ═════════════════════════════════════════════════════════════════════════

-- C1. Create a draft (script --live and admin "regenerate"). Version is
-- allocated under a per-question advisory lock so two generators cannot both
-- claim version N+1.
create or replace function public.cms_create_answer_structure_draft(
    p_question_id     uuid,
    p_payload         jsonb,
    p_generated_by    text,
    p_generation_meta jsonb,
    p_reason          text,
    p_actor_user_id   uuid default null,
    p_actor_email     text default null
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
    v_version  integer;
    v_row      public.answer_structures%rowtype;
    v_audit_id uuid;
begin
    if nullif(btrim(coalesce(p_generated_by, '')), '') is null then
        raise exception 'invalid_generated_by: p_generated_by is required' using errcode = 'P0422';
    end if;
    if p_payload is null or jsonb_typeof(p_payload) <> 'object' then
        raise exception 'invalid_payload: p_payload must be an object' using errcode = 'P0422';
    end if;
    if not exists (select 1 from public.pyq_questions where id = p_question_id) then
        raise exception 'not_found: pyq_question % does not exist', p_question_id using errcode = 'P0404';
    end if;

    perform pg_advisory_xact_lock(hashtext('answer_structures:' || p_question_id::text));

    select coalesce(max(version), 0) + 1 into v_version
    from public.answer_structures where pyq_question_id = p_question_id;

    insert into public.answer_structures (
        pyq_question_id, version, status, directive, demand, intro_angles,
        body_points, dimensions, examples, conclusion_angles, pitfalls,
        word_budget, sources_note, generated_by, generation_meta
    ) values (
        p_question_id, v_version, 'draft',
        coalesce(p_payload->>'directive', ''),
        coalesce(p_payload->>'demand', ''),
        coalesce(p_payload->'intro_angles', '[]'::jsonb),
        coalesce(p_payload->'body_points', '[]'::jsonb),
        coalesce(p_payload->'dimensions', '[]'::jsonb),
        coalesce(p_payload->'examples', '[]'::jsonb),
        coalesce(p_payload->'conclusion_angles', '[]'::jsonb),
        coalesce(p_payload->'pitfalls', '[]'::jsonb),
        case when jsonb_typeof(p_payload->'word_budget') = 'object'
             then p_payload->'word_budget' else null end,
        nullif(p_payload->>'sources_note', ''),
        btrim(p_generated_by),
        coalesce(p_generation_meta, '{}'::jsonb)
    ) returning * into v_row;

    insert into public.admin_audit_logs (
        actor_id, actor_email, admin_user_id, action, entity_type, entity_id,
        old_value, new_value, notes
    ) values (
        p_actor_user_id, p_actor_email, p_actor_user_id,
        'answer_structure_draft_created', 'answer_structure', v_row.id::text,
        null,
        jsonb_build_object('pyq_question_id', p_question_id, 'version', v_version,
                           'generated_by', v_row.generated_by),
        nullif(btrim(coalesce(p_reason, '')), '')
    ) returning id into v_audit_id;

    return jsonb_build_object('ok', true, 'id', v_row.id, 'version', v_version,
                              'audit_id', v_audit_id);
end;
$$;

-- C2. Edit fields. Only draft / in_review rows are editable — a verified row
-- is what learners are reading, so it is changed by rejecting it and
-- approving a new version, never in place. CAS on updated_at.
create or replace function public.cms_update_answer_structure(
    p_id                  uuid,
    p_expected_updated_at timestamptz,
    p_patch               jsonb,
    p_reason              text,
    p_actor_user_id       uuid,
    p_actor_email         text default null
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
    v_old      public.answer_structures%rowtype;
    v_row      public.answer_structures%rowtype;
    v_audit_id uuid;
begin
    if p_actor_user_id is null then
        raise exception 'missing_actor_id: p_actor_user_id must not be NULL' using errcode = 'P0422';
    end if;
    if nullif(btrim(coalesce(p_reason, '')), '') is null
       or char_length(btrim(p_reason)) < 8 or char_length(btrim(p_reason)) > 500 then
        raise exception 'invalid_reason: p_reason must be 8–500 characters' using errcode = 'P0422';
    end if;
    if p_expected_updated_at is null then
        raise exception 'concurrent_modification: p_expected_updated_at (CAS token) is required' using errcode = 'P0409';
    end if;
    if p_patch is null or jsonb_typeof(p_patch) <> 'object' then
        raise exception 'invalid_payload: p_patch must be an object' using errcode = 'P0422';
    end if;

    select * into v_old from public.answer_structures where id = p_id for update;
    if not found then
        raise exception 'not_found: answer_structure % does not exist', p_id using errcode = 'P0404';
    end if;
    if v_old.updated_at is distinct from p_expected_updated_at then
        raise exception 'concurrent_modification: structure changed since read. Re-fetch and retry.'
            using errcode = 'P0409';
    end if;
    if v_old.status not in ('draft', 'in_review') then
        raise exception 'structure_locked: a % structure cannot be edited', v_old.status
            using errcode = 'P0422';
    end if;

    update public.answer_structures set
        directive         = case when p_patch ? 'directive' then p_patch->>'directive' else directive end,
        demand            = case when p_patch ? 'demand' then p_patch->>'demand' else demand end,
        intro_angles      = case when p_patch ? 'intro_angles' then p_patch->'intro_angles' else intro_angles end,
        body_points       = case when p_patch ? 'body_points' then p_patch->'body_points' else body_points end,
        dimensions        = case when p_patch ? 'dimensions' then p_patch->'dimensions' else dimensions end,
        examples          = case when p_patch ? 'examples' then p_patch->'examples' else examples end,
        conclusion_angles = case when p_patch ? 'conclusion_angles' then p_patch->'conclusion_angles' else conclusion_angles end,
        pitfalls          = case when p_patch ? 'pitfalls' then p_patch->'pitfalls' else pitfalls end,
        word_budget       = case when p_patch ? 'word_budget'
                                 then (case when jsonb_typeof(p_patch->'word_budget') = 'object'
                                            then p_patch->'word_budget' else null end)
                                 else word_budget end,
        sources_note      = case when p_patch ? 'sources_note' then nullif(p_patch->>'sources_note', '') else sources_note end
    where id = p_id
    returning * into v_row;

    insert into public.admin_audit_logs (
        actor_id, actor_email, admin_user_id, action, entity_type, entity_id,
        old_value, new_value, notes
    ) values (
        p_actor_user_id, p_actor_email, p_actor_user_id,
        'answer_structure_edited', 'answer_structure', p_id::text,
        (to_jsonb(v_old) - 'generation_meta') ,
        jsonb_build_object('fields', (select coalesce(jsonb_agg(k order by k), '[]'::jsonb)
                                      from jsonb_object_keys(p_patch) k)),
        btrim(p_reason)
    ) returning id into v_audit_id;

    return jsonb_build_object('ok', true, 'id', p_id, 'audit_id', v_audit_id,
                              'updated_at', v_row.updated_at);
end;
$$;

-- C3. Review transition.
--   draft     -> in_review | verified | rejected
--   in_review -> verified  | rejected | draft
--   verified  -> rejected           (withdraw; note required)
--   rejected  -> (terminal — regenerate creates a new version)
-- Rejection always requires a note. Verifying demotes any other verified
-- version of the same question to 'rejected' (superseded) atomically, so the
-- one-verified index can never fire mid-approval.
create or replace function public.cms_review_answer_structure(
    p_id                  uuid,
    p_expected_status     text,
    p_expected_updated_at timestamptz,
    p_new_status          text,
    p_review_notes        text,
    p_actor_user_id       uuid,
    p_actor_email         text default null
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
    v_row        public.answer_structures%rowtype;
    v_audit_id   uuid;
    v_superseded uuid;
    v_notes      text := nullif(btrim(coalesce(p_review_notes, '')), '');
begin
    if p_actor_user_id is null then
        raise exception 'missing_actor_id: p_actor_user_id must not be NULL' using errcode = 'P0422';
    end if;
    if p_expected_updated_at is null then
        raise exception 'concurrent_modification: p_expected_updated_at (CAS token) is required' using errcode = 'P0409';
    end if;
    if p_new_status not in ('draft', 'in_review', 'verified', 'rejected') then
        raise exception 'invalid_target_status: % is not a recognised status', p_new_status using errcode = 'P0422';
    end if;

    select * into v_row from public.answer_structures where id = p_id for update;
    if not found then
        raise exception 'not_found: answer_structure % does not exist', p_id using errcode = 'P0404';
    end if;
    if v_row.status is distinct from p_expected_status then
        raise exception 'concurrent_modification: expected status=% but found %. Re-fetch and retry.',
            p_expected_status, v_row.status using errcode = 'P0409';
    end if;
    if v_row.updated_at is distinct from p_expected_updated_at then
        raise exception 'concurrent_modification: structure changed since read. Re-fetch and retry.'
            using errcode = 'P0409';
    end if;

    if not (
           (v_row.status = 'draft'     and p_new_status in ('in_review', 'verified', 'rejected'))
        or (v_row.status = 'in_review' and p_new_status in ('verified', 'rejected', 'draft'))
        or (v_row.status = 'verified'  and p_new_status = 'rejected')
    ) then
        raise exception 'transition_not_allowed: % -> % is not a permitted transition',
            v_row.status, p_new_status using errcode = 'P0422';
    end if;

    if p_new_status = 'rejected' and v_notes is null then
        raise exception 'invalid_review_notes: review_notes required when rejecting'
            using errcode = 'P0422';
    end if;

    if p_new_status = 'verified' then
        update public.answer_structures
        set status = 'rejected',
            review_notes = 'Superseded by version ' || v_row.version || '.',
            reviewed_by = p_actor_user_id,
            reviewed_at = now()
        where pyq_question_id = v_row.pyq_question_id
          and status = 'verified'
          and id <> p_id
        returning id into v_superseded;
    end if;

    update public.answer_structures
    set status = p_new_status,
        reviewed_by = case when p_new_status in ('verified', 'rejected') then p_actor_user_id else reviewed_by end,
        reviewed_at = case when p_new_status in ('verified', 'rejected') then now() else reviewed_at end,
        review_notes = coalesce(v_notes, review_notes)
    where id = p_id
    returning * into v_row;

    insert into public.admin_audit_logs (
        actor_id, actor_email, admin_user_id, action, entity_type, entity_id,
        old_value, new_value, notes
    ) values (
        p_actor_user_id, p_actor_email, p_actor_user_id,
        'answer_structure_status_transition', 'answer_structure', p_id::text,
        jsonb_build_object('status', p_expected_status),
        jsonb_build_object('status', p_new_status, 'version', v_row.version,
                           'review_notes', v_notes, 'superseded_id', v_superseded),
        v_notes
    ) returning id into v_audit_id;

    return jsonb_build_object('ok', true, 'id', p_id, 'audit_id', v_audit_id,
                              'prev_status', p_expected_status, 'new_status', p_new_status,
                              'superseded_id', v_superseded, 'updated_at', v_row.updated_at);
end;
$$;

do $$
declare
    fn text;
begin
    foreach fn in array array[
        'public.cms_create_answer_structure_draft(uuid, jsonb, text, jsonb, text, uuid, text)',
        'public.cms_update_answer_structure(uuid, timestamptz, jsonb, text, uuid, text)',
        'public.cms_review_answer_structure(uuid, text, timestamptz, text, text, uuid, text)'
    ] loop
        execute format('revoke execute on function %s from public', fn);
        execute format('revoke execute on function %s from anon', fn);
        execute format('revoke execute on function %s from authenticated', fn);
        execute format('grant  execute on function %s to service_role', fn);
    end loop;
end $$;

commit;

notify pgrst, 'reload schema';
