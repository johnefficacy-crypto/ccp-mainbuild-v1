-- 183: PYQ → Mock Question Bank projection bridge.
--
-- Implements the canonical PYQ-to-runtime projection layer described in
-- docs/study_os/pyq-mock-projection-bridge.md.
--
-- This migration NEVER backfills data. No existing questions are projected.
-- Projection is always an explicit operator action (mock_questions:publish).
--
-- Overview:
--   A. Add nullable runtime snapshot columns to mock_question_bank.
--   B. Create pyq_mock_question_projections (1-to-1 identity map).
--   C. Create mock_source_mix_policies (source-proportion policy storage).
--   D. Create project_pyq_question_to_mock_bank() atomic projection RPC.
--   E. Create invalidation trigger (marks projections stale when canonical source changes).
--   F. Grants — service_role only for the RPC.
--
-- Rollback (non-production, run manually):
--   DROP TRIGGER IF EXISTS trg_invalidate_pyq_projection_q ON pyq_questions;
--   DROP TRIGGER IF EXISTS trg_invalidate_pyq_projection_p ON pyq_papers;
--   DROP TRIGGER IF EXISTS trg_invalidate_pyq_projection_o_upd ON pyq_options;
--   DROP TRIGGER IF EXISTS trg_invalidate_pyq_projection_o_del ON pyq_options;
--   DROP TRIGGER IF EXISTS trg_invalidate_pyq_projection_o_ins ON pyq_options;
--   DROP TRIGGER IF EXISTS trg_invalidate_pyq_projection_t_upd ON pyq_question_topic_tags;
--   DROP TRIGGER IF EXISTS trg_invalidate_pyq_projection_t_del ON pyq_question_topic_tags;
--   DROP TRIGGER IF EXISTS trg_invalidate_pyq_projection_t_ins ON pyq_question_topic_tags;
--   DROP FUNCTION IF EXISTS public.fn_invalidate_pyq_projection();
--   DROP FUNCTION IF EXISTS public.fn_invalidate_projection_for_question(uuid);
--   DROP FUNCTION IF EXISTS public.fn_block_projection_for_question(uuid, text);
--   DROP FUNCTION IF EXISTS public.project_pyq_question_to_mock_bank(uuid,uuid,text);
--   ALTER TABLE public.mock_question_bank
--     DROP COLUMN IF EXISTS pyq_question_id,
--     DROP COLUMN IF EXISTS pyq_paper_id,
--     DROP COLUMN IF EXISTS pyq_year;
--   DROP TABLE IF EXISTS public.mock_source_mix_policies;
--   DROP TABLE IF EXISTS public.pyq_mock_question_projections;
--   (Constraint extension in mock_question_review_log is backward-compatible; leave in place.)

-- ── A. Runtime snapshot columns on mock_question_bank ───────────────────────

alter table public.mock_question_bank
  add column if not exists pyq_question_id uuid
    references public.pyq_questions(id) on delete set null,
  add column if not exists pyq_paper_id uuid
    references public.pyq_papers(id) on delete set null,
  add column if not exists pyq_year integer;

create index if not exists idx_mock_qbank_pyq_question_id
  on public.mock_question_bank(pyq_question_id)
  where pyq_question_id is not null;

-- Unique constraint: at most one mock_question_bank row per PYQ source question.
-- Prevents two racing syncs from inserting duplicate rows for the same PYQ question.
create unique index if not exists uq_mock_qbank_pyq_question_id
  on public.mock_question_bank(pyq_question_id)
  where pyq_question_id is not null;

comment on column public.mock_question_bank.pyq_question_id is
  'When set, this runtime question is a projection of a canonical PYQ question. '
  'Frozen at projection time; never cleared for historical snapshot integrity.';
comment on column public.mock_question_bank.pyq_paper_id is
  'Denormalized from pyq_mock_question_projections for fast querying. '
  'Set when pyq_question_id is set.';
comment on column public.mock_question_bank.pyq_year is
  'Exam year of the source PYQ paper. Frozen into attempt snapshots.';

-- ── B. pyq_mock_question_projections — 1-to-1 identity map ─────────────────

create table if not exists public.pyq_mock_question_projections (
  -- Primary key: one PYQ question maps to at most one mock bank row.
  pyq_question_id  uuid primary key
    references public.pyq_questions(id) on delete restrict,
  -- Unique: one mock bank row comes from at most one PYQ question.
  mock_question_id uuid not null unique
    references public.mock_question_bank(id) on delete cascade,
  -- Hash of canonical source content at last sync: (question_text, options, correct).
  source_content_hash text not null,
  -- Lifecycle state.
  sync_status text not null default 'active'
    check (sync_status in ('active', 'stale', 'blocked', 'archived')),
  -- Full result from the last sync call, stored for audit and debugging.
  last_sync_result jsonb not null default '{}'::jsonb,
  -- Who projected it and when.
  projected_by uuid references auth.users(id) on delete set null,
  projected_at timestamptz not null,
  updated_at   timestamptz not null
);

create index if not exists idx_pyq_proj_mock_question_id
  on public.pyq_mock_question_projections(mock_question_id);
create index if not exists idx_pyq_proj_sync_status
  on public.pyq_mock_question_projections(sync_status);

comment on table public.pyq_mock_question_projections is
  'Authoritative 1-to-1 identity map between canonical PYQ questions and '
  'runtime mock_question_bank rows. Created and updated only by the '
  'project_pyq_question_to_mock_bank() service-role RPC. '
  'sync_status=active means the projection is current and the mock row is selectable. '
  'sync_status=stale means the source changed; re-sync is required before the question '
  'becomes selectable again.';

-- ── C. mock_source_mix_policies — configurable PYQ ratio targets ────────────

create table if not exists public.mock_source_mix_policies (
  id             uuid primary key default gen_random_uuid(),
  -- Scope: most-specific applicable policy wins (topic > subject > phase > exam).
  exam_id        uuid not null references public.exams(id) on delete cascade,
  exam_phase_id  uuid references public.exam_phases(id) on delete cascade,
  subject_id     uuid references public.subjects(id) on delete cascade,
  topic_id       uuid references public.topics(id) on delete cascade,
  -- Source targeted by this policy. Currently 'pyq'; other kinds reserved.
  source_kind    text not null default 'pyq',
  -- Ratio constraints: 0 ≤ minimum_ratio ≤ target_ratio ≤ maximum_ratio ≤ 1.
  target_ratio   numeric(5,4) not null,
  minimum_ratio  numeric(5,4) not null,
  maximum_ratio  numeric(5,4) not null,
  -- What to do when the eligible PYQ pool is thinner than minimum_ratio demands.
  fallback_policy text not null default 'relax_to_available'
    check (fallback_policy in ('relax_to_available', 'block')),
  is_active boolean not null default true,
  metadata  jsonb  not null default '{}'::jsonb,
  created_by uuid references auth.users(id) on delete set null,
  updated_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  -- Hard constraints on ratio values.
  check (minimum_ratio >= 0),
  check (maximum_ratio <= 1),
  check (minimum_ratio <= target_ratio),
  check (target_ratio  <= maximum_ratio)
);

create index if not exists idx_source_mix_policy_exam
  on public.mock_source_mix_policies(exam_id, is_active);
create index if not exists idx_source_mix_policy_scope
  on public.mock_source_mix_policies(exam_id, exam_phase_id, subject_id, topic_id)
  where is_active = true;

comment on table public.mock_source_mix_policies is
  'Configurable PYQ proportion targets per scope. The selector resolves the '
  'most-specific active policy (topic > subject > phase > exam). '
  'No hardcoded IDs — all scoping is by FK to canonical tables.';

-- ── B/C RLS: service-role + admin-only access on both new tables ─────────────

alter table public.pyq_mock_question_projections enable row level security;

create policy "pyq_proj_admin_all"
  on public.pyq_mock_question_projections for all
  using (
    (select (auth.jwt() ->> 'role') in ('service_role'))
    or (select (auth.jwt() -> 'app_metadata' ->> 'role') in ('admin', 'super_admin'))
  )
  with check (
    (select (auth.jwt() ->> 'role') in ('service_role'))
    or (select (auth.jwt() -> 'app_metadata' ->> 'role') in ('admin', 'super_admin'))
  );

alter table public.mock_source_mix_policies enable row level security;

create policy "source_mix_admin_all"
  on public.mock_source_mix_policies for all
  using (
    (select (auth.jwt() ->> 'role') in ('service_role'))
    or (select (auth.jwt() -> 'app_metadata' ->> 'role') in ('admin', 'super_admin'))
  )
  with check (
    (select (auth.jwt() ->> 'role') in ('service_role'))
    or (select (auth.jwt() -> 'app_metadata' ->> 'role') in ('admin', 'super_admin'))
  );

-- ── D. Projection RPC ───────────────────────────────────────────────────────
--
-- project_pyq_question_to_mock_bank(p_pyq_question_id, p_actor_id, p_audit_reason)
--
-- Validates eligibility, creates/updates the mock_question_bank row and its
-- child tables atomically, maintains the projection identity row, and writes
-- an audit event. Returns structured JSONB.
--
-- Called ONLY from the Python service (service_role); never exposed to clients.

do $migration$
begin
  -- Extend mock_question_review_log action constraint to include projection
  -- actions. The constraint was defined in migration 136 with a fixed
  -- vocabulary that predates this projection feature.
  execute $ddl$ alter table public.mock_question_review_log drop constraint if exists mock_question_review_log_action_check $ddl$;
  execute $ddl$
    alter table public.mock_question_review_log
      add constraint mock_question_review_log_action_check
      check (action in (
        'create','edit','submit','approve','request_changes',
        'publish','archive','restore','force','unauthorized','import',
        'pyq_projection_created','pyq_projection_updated'
      ))
  $ddl$;

  execute $ddl$

  create or replace function public.project_pyq_question_to_mock_bank(
      p_pyq_question_id uuid,
      p_actor_id        uuid,
      p_audit_reason    text
  ) returns jsonb
  language plpgsql
  security definer
  set search_path = public
  as $fn$
  declare
      -- Source rows
      v_q          record;     -- pyq_questions + paper join
      v_primary_tag record;    -- exactly-one verified primary topic tag
      v_topic      record;     -- topic row (for subject_id)

      -- Derived values
      v_content_hash        text;
      v_correct_count       integer;
      v_option_count        integer;
      v_verified_opt_count  integer;
      v_empty_opt_count     integer;
      v_primary_tag_count   integer;

      -- Projection identity
      v_projection record;
      v_mock_q_id  uuid;
      v_is_new     boolean := false;
      v_outcome    text;

      -- Mock row values
      v_correct_opt_id uuid;

      -- Option iteration
      v_opt_row    record;
      v_new_opt_id uuid;
  begin
      -- ── 0. Validate inputs ─────────────────────────────────────────────────

      if p_audit_reason is null or length(trim(p_audit_reason)) < 8 then
          return jsonb_build_object(
              'outcome', 'error',
              'error',   'audit_reason_required',
              'detail',  'p_audit_reason must be at least 8 non-blank characters'
          );
      end if;

      -- ── 1. Load and lock canonical source rows ─────────────────────────────

      select
          q.id,
          q.pyq_paper_id,
          q.question_number,
          q.question_text,
          q.question_type,
          q.correct_option_id     as pyq_correct_option_id,
          q.explanation_text,
          q.observed_difficulty,
          q.expected_solve_time_sec,
          q.language,
          q.reviewer_status       as q_reviewer_status,
          q.metadata              as q_metadata,
          -- paper fields
          p.exam_id,
          p.year                  as paper_year,
          p.trust_status          as paper_trust_status,
          p.source_url            as paper_source_url,
          p.source_type           as paper_source_type
      into v_q
      from public.pyq_questions q
      join public.pyq_papers    p on p.id = q.pyq_paper_id
      where q.id = p_pyq_question_id
      for update of q, p;

      if not found then
          return jsonb_build_object(
              'outcome', 'error',
              'error',   'question_not_found',
              'pyq_question_id', p_pyq_question_id
          );
      end if;

      -- ── 2. Eligibility checks ──────────────────────────────────────────────

      -- (a) Paper must be verified
      if v_q.paper_trust_status != 'verified' then
          perform public.fn_block_projection_for_question(p_pyq_question_id, 'paper_not_verified');
          return jsonb_build_object(
              'outcome',          'blocked',
              'reason',           'paper_not_verified',
              'paper_trust_status', v_q.paper_trust_status,
              'pyq_question_id',  p_pyq_question_id
          );
      end if;

      -- (b) Question must be verified
      if v_q.q_reviewer_status != 'verified' then
          perform public.fn_block_projection_for_question(p_pyq_question_id, 'question_not_verified');
          return jsonb_build_object(
              'outcome',            'blocked',
              'reason',             'question_not_verified',
              'reviewer_status',    v_q.q_reviewer_status,
              'pyq_question_id',    p_pyq_question_id
          );
      end if;

      -- (c) Must be MCQ
      if v_q.question_type != 'mcq' then
          perform public.fn_block_projection_for_question(p_pyq_question_id, 'not_mcq');
          return jsonb_build_object(
              'outcome',          'blocked',
              'reason',           'not_mcq',
              'question_type',    v_q.question_type,
              'pyq_question_id',  p_pyq_question_id
          );
      end if;

      -- (d) Question text must be non-empty
      if coalesce(trim(v_q.question_text), '') = '' then
          perform public.fn_block_projection_for_question(p_pyq_question_id, 'empty_question_text');
          return jsonb_build_object(
              'outcome',         'blocked',
              'reason',          'empty_question_text',
              'pyq_question_id', p_pyq_question_id
          );
      end if;

      -- (e) Options: verified count ≥ 2; no empty verified text; exactly one
      --     verified option is correct; correct_option_id (if set) must agree.
      select
          count(*)                                                             as total,
          count(*) filter (where reviewer_status = 'verified')                as verified_count,
          count(*) filter (where reviewer_status = 'verified' and is_correct)  as correct_verified_count,
          count(*) filter (
              where reviewer_status = 'verified'
                and coalesce(trim(option_text), '') = ''
          )                                                                    as empty_text_count
      into v_option_count, v_verified_opt_count, v_correct_count, v_empty_opt_count
      from public.pyq_options
      where question_id = p_pyq_question_id;

      if v_verified_opt_count < 2 then
          perform public.fn_block_projection_for_question(p_pyq_question_id, 'insufficient_verified_options');
          return jsonb_build_object(
              'outcome',               'blocked',
              'reason',                'insufficient_verified_options',
              'verified_option_count', v_verified_opt_count,
              'pyq_question_id',       p_pyq_question_id
          );
      end if;

      if v_empty_opt_count > 0 then
          perform public.fn_block_projection_for_question(p_pyq_question_id, 'empty_verified_option_text');
          return jsonb_build_object(
              'outcome',          'blocked',
              'reason',           'empty_verified_option_text',
              'empty_opt_count',  v_empty_opt_count,
              'pyq_question_id',  p_pyq_question_id
          );
      end if;

      if v_correct_count != 1 then
          perform public.fn_block_projection_for_question(p_pyq_question_id, 'not_exactly_one_verified_correct_option');
          return jsonb_build_object(
              'outcome',          'blocked',
              'reason',           'not_exactly_one_verified_correct_option',
              'correct_count',    v_correct_count,
              'pyq_question_id',  p_pyq_question_id
          );
      end if;

      -- Correct_option_id pointer must agree with the verified correct option.
      if v_q.pyq_correct_option_id is not null then
          if not exists (
              select 1 from public.pyq_options
              where question_id     = p_pyq_question_id
                and reviewer_status = 'verified'
                and is_correct      = true
                and id              = v_q.pyq_correct_option_id
          ) then
              perform public.fn_block_projection_for_question(p_pyq_question_id, 'correct_option_id_mismatch');
              return jsonb_build_object(
                  'outcome',           'blocked',
                  'reason',            'correct_option_id_mismatch',
                  'stated_correct_id', v_q.pyq_correct_option_id,
                  'pyq_question_id',   p_pyq_question_id
              );
          end if;
      end if;

      -- (f) Exactly one verified primary topic tag
      select count(*)
      into v_primary_tag_count
      from public.pyq_question_topic_tags
      where question_id    = p_pyq_question_id
        and tag_role       = 'primary'
        and reviewer_status = 'verified';

      if v_primary_tag_count != 1 then
          perform public.fn_block_projection_for_question(p_pyq_question_id, 'primary_topic_tag_count_not_one');
          return jsonb_build_object(
              'outcome',             'blocked',
              'reason',              'primary_topic_tag_count_not_one',
              'primary_tag_count',   v_primary_tag_count,
              'pyq_question_id',     p_pyq_question_id
          );
      end if;

      -- Load the primary tag
      select t.*
      into v_primary_tag
      from public.pyq_question_topic_tags t
      where t.question_id    = p_pyq_question_id
        and t.tag_role       = 'primary'
        and t.reviewer_status = 'verified'
      limit 1;

      -- (g) Primary topic must resolve to a valid subject
      select s.*
      into v_topic
      from public.topics s
      where s.id = v_primary_tag.topic_id
        and s.is_active = true
      limit 1;

      if not found then
          perform public.fn_block_projection_for_question(p_pyq_question_id, 'primary_topic_invalid_or_inactive');
          return jsonb_build_object(
              'outcome',         'blocked',
              'reason',          'primary_topic_invalid_or_inactive',
              'topic_id',        v_primary_tag.topic_id,
              'pyq_question_id', p_pyq_question_id
          );
      end if;

      if v_topic.subject_id is null then
          perform public.fn_block_projection_for_question(p_pyq_question_id, 'primary_topic_has_no_subject');
          return jsonb_build_object(
              'outcome',         'blocked',
              'reason',          'primary_topic_has_no_subject',
              'topic_id',        v_primary_tag.topic_id,
              'pyq_question_id', p_pyq_question_id
          );
      end if;

      -- ── 3. Compute source content hash ─────────────────────────────────────
      --
      -- Hash = SHA256( q_text NUL sorted_verified_opt_texts NUL verified_correct_opt )
      -- Only VERIFIED options are included so the hash tracks audited content.
      -- Formula matches compute_content_hash() in pyq_mock_projection.py.

      select encode(
          sha256((
              coalesce(lower(trim(v_q.question_text)), '') || chr(0) ||
              coalesce((
                  select string_agg(lower(trim(o.option_text)), chr(0)
                         order by lower(trim(o.option_text)))
                  from public.pyq_options o
                  where o.question_id = p_pyq_question_id
                    and o.reviewer_status = 'verified'
              ), '') || chr(0) ||
              coalesce((
                  select lower(trim(c.option_text))
                  from public.pyq_options c
                  where c.question_id = p_pyq_question_id
                    and c.reviewer_status = 'verified'
                    and c.is_correct = true
                  limit 1
              ), '')
          )::bytea),
          'hex'
      ) into v_content_hash;

      -- ── 4. Look up existing projection ─────────────────────────────────────

      select * into v_projection
      from public.pyq_mock_question_projections
      where pyq_question_id = p_pyq_question_id
      for update;

      if found then
          v_mock_q_id := v_projection.mock_question_id;

          -- Guard: the mock_question_id must still exist and still point back to us.
          -- If mock_question_bank.pyq_question_id is set to a DIFFERENT pyq question,
          -- that is a collision we must refuse rather than silently overwrite.
          declare
              v_existing_pyq_q_id uuid;
          begin
              select pyq_question_id
              into v_existing_pyq_q_id
              from public.mock_question_bank
              where id = v_mock_q_id;

              if not found then
                  -- Mock row was deleted externally — the projection row is orphaned.
                  -- Archive the orphaned projection and treat as new.
                  update public.pyq_mock_question_projections
                  set sync_status = 'archived', updated_at = now()
                  where pyq_question_id = p_pyq_question_id;
                  v_mock_q_id := null;
                  v_projection := null;
                  v_is_new := true;
              elsif v_existing_pyq_q_id is not null
                    and v_existing_pyq_q_id != p_pyq_question_id then
                  -- Another PYQ question is already attached to this mock ID.
                  return jsonb_build_object(
                      'outcome',              'conflict',
                      'error',                'mock_question_linked_to_different_pyq',
                      'mock_question_id',     v_mock_q_id,
                      'conflicting_pyq_id',   v_existing_pyq_q_id,
                      'pyq_question_id',      p_pyq_question_id
                  );
              end if;
          end;

          -- Check if content is unchanged (idempotent no-op)
          if v_projection is not null
             and v_projection.sync_status = 'active'
             and v_projection.source_content_hash = v_content_hash then
              -- Nothing to do
              v_outcome := 'unchanged';
          else
              v_outcome := 'updated';
          end if;
      else
          v_is_new    := true;
          v_mock_q_id := gen_random_uuid();
          v_outcome   := 'created';
      end if;

      -- Even for 'unchanged', we still re-sync to ensure referential integrity
      -- (options, tags, sources). The only skip is when outcome stays 'unchanged'
      -- AND we want a pure no-op. Per spec we do a full re-sync; return early only
      -- if we decide that is safe. For now: always re-sync on 'updated'/'created'.
      -- For 'unchanged' we still update the projection row's updated_at but skip
      -- the expensive child writes.

      if v_outcome = 'unchanged' then
          -- Touch updated_at to record the check happened
          update public.pyq_mock_question_projections
          set updated_at = now(),
              last_sync_result = jsonb_build_object(
                  'outcome', 'unchanged',
                  'checked_at', now()::text,
                  'content_hash', v_content_hash
              )
          where pyq_question_id = p_pyq_question_id;

          return jsonb_build_object(
              'outcome',           'unchanged',
              'mock_question_id',  v_mock_q_id,
              'pyq_question_id',   p_pyq_question_id,
              'content_hash',      v_content_hash
          );
      end if;

      -- ── 5. Upsert mock_question_bank ───────────────────────────────────────
      --
      -- source_type = 'pyq'  (canonical mastery weighting value)
      -- source_kind = 'pyq'  (selector/diagnostic compatibility)
      -- reviewer_status = 'verified'  (makes it selectable immediately)

      if v_is_new then
          insert into public.mock_question_bank (
              id,
              exam_id,
              subject_id,
              topic_id,
              question_text,
              question_type,
              difficulty,
              explanation,
              language,
              reviewer_status,
              published_at,
              source_type,
              source_kind,
              question_fingerprint,
              pyq_question_id,
              pyq_paper_id,
              pyq_year,
              expected_time_sec,
              created_by,
              created_at,
              updated_at
          ) values (
              v_mock_q_id,
              v_q.exam_id,
              v_topic.subject_id,
              v_primary_tag.topic_id,
              v_q.question_text,
              'mcq',
              case when lower(v_q.observed_difficulty) in ('easy','medium','hard')
                   then lower(v_q.observed_difficulty) else 'medium' end,
              v_q.explanation_text,
              coalesce(v_q.language, 'en'),
              'published',
              now(),
              'pyq',
              'pyq',
              v_content_hash,
              p_pyq_question_id,
              v_q.pyq_paper_id,
              v_q.paper_year,
              v_q.expected_solve_time_sec,
              p_actor_id,
              now(),
              now()
          );
      else
          update public.mock_question_bank set
              exam_id              = v_q.exam_id,
              subject_id           = v_topic.subject_id,
              topic_id             = v_primary_tag.topic_id,
              question_text        = v_q.question_text,
              question_type        = 'mcq',
              difficulty           = case when lower(v_q.observed_difficulty) in ('easy','medium','hard')
                                         then lower(v_q.observed_difficulty) else 'medium' end,
              explanation          = v_q.explanation_text,
              language             = coalesce(v_q.language, 'en'),
              reviewer_status      = 'published',
              published_at         = coalesce(
                                         (select published_at from public.mock_question_bank where id = v_mock_q_id),
                                         now()
                                     ),
              source_type          = 'pyq',
              source_kind          = 'pyq',
              question_fingerprint = v_content_hash,
              pyq_question_id      = p_pyq_question_id,
              pyq_paper_id         = v_q.pyq_paper_id,
              pyq_year             = v_q.paper_year,
              expected_time_sec    = v_q.expected_solve_time_sec,
              updated_at           = now()
          where id = v_mock_q_id;
      end if;

      -- ── 6. Replace mock_question_options atomically ────────────────────────
      --
      -- Only VERIFIED options are copied; the fingerprint was already set to
      -- v_content_hash (which hashes verified options), so both are consistent.

      delete from public.mock_question_options
      where question_id = v_mock_q_id;

      v_correct_opt_id := null;

      for v_opt_row in
          select id, option_text, option_label, is_correct,
                 row_number() over (order by option_label, id) - 1 as opt_idx
          from public.pyq_options
          where question_id = p_pyq_question_id
            and reviewer_status = 'verified'
          order by option_label, id
      loop
          insert into public.mock_question_options (
              question_id, option_text, option_index, is_correct
          ) values (
              v_mock_q_id,
              v_opt_row.option_text,
              v_opt_row.opt_idx,
              v_opt_row.is_correct
          )
          returning id into v_new_opt_id;

          if v_opt_row.is_correct then
              v_correct_opt_id := v_new_opt_id;
          end if;
      end loop;

      -- Set correct_option_id (fingerprint already set from v_content_hash above).
      update public.mock_question_bank
      set correct_option_id = v_correct_opt_id,
          updated_at        = now()
      where id = v_mock_q_id;

      -- ── 7. Replace mock_question_topic_tags ───────────────────────────────

      delete from public.mock_question_topic_tags
      where question_id = v_mock_q_id;

      insert into public.mock_question_topic_tags (question_id, topic_id, role)
      select v_mock_q_id, t.topic_id, t.tag_role
      from public.pyq_question_topic_tags t
      where t.question_id = p_pyq_question_id
        and t.reviewer_status = 'verified';

      -- ── 8. Upsert mock_question_sources (provenance) ──────────────────────

      delete from public.mock_question_sources
      where question_id = v_mock_q_id;

      insert into public.mock_question_sources (
          question_id, source_kind, source_trust,
          source_url, pyq_paper_id, pyq_year, evidence_text
      ) values (
          v_mock_q_id,
          'pyq',
          'verified',
          v_q.paper_source_url,
          v_q.pyq_paper_id,
          v_q.paper_year,
          'projected_from_pyq_question_id:' || p_pyq_question_id::text
      );

      -- ── 9. Upsert pyq_mock_question_projections ───────────────────────────

      insert into public.pyq_mock_question_projections (
          pyq_question_id,
          mock_question_id,
          source_content_hash,
          sync_status,
          last_sync_result,
          projected_by,
          projected_at,
          updated_at
      ) values (
          p_pyq_question_id,
          v_mock_q_id,
          v_content_hash,
          'active',
          jsonb_build_object('outcome', v_outcome, 'projected_at', now()::text),
          p_actor_id,
          now(),
          now()
      )
      on conflict (pyq_question_id) do update
        set mock_question_id     = excluded.mock_question_id,
            source_content_hash  = excluded.source_content_hash,
            sync_status          = 'active',
            last_sync_result     = excluded.last_sync_result,
            projected_by         = excluded.projected_by,
            projected_at         = case
                when pyq_mock_question_projections.projected_at is null
                then excluded.projected_at
                else pyq_mock_question_projections.projected_at
            end,
            updated_at           = now();

      -- ── 10. Audit log ─────────────────────────────────────────────────────

      insert into public.admin_audit_logs (
          actor_id,
          action,
          entity_type,
          entity_id,
          new_value,
          notes
      ) values (
          p_actor_id,
          'pyq_mock_projection_sync',
          'mock_question_bank',
          v_mock_q_id::text,
          jsonb_build_object(
              'outcome',          v_outcome,
              'pyq_question_id',  p_pyq_question_id,
              'pyq_paper_id',     v_q.pyq_paper_id,
              'exam_id',          v_q.exam_id,
              'pyq_year',         v_q.paper_year,
              'content_hash',     v_content_hash,
              'topic_id',         v_primary_tag.topic_id,
              'subject_id',       v_topic.subject_id
          ),
          p_audit_reason
      );

      -- ── 11. Write review log on mock_question_bank ────────────────────────

      insert into public.mock_question_review_log (
          question_id, actor_id, action, from_status, to_status, notes, at
      ) values (
          v_mock_q_id,
          p_actor_id,
          'pyq_projection_' || v_outcome,
          case when v_is_new then null else 'published' end,
          'published',
          p_audit_reason,
          now()
      );

      -- ── 12. Return structured result ──────────────────────────────────────

      return jsonb_build_object(
          'outcome',           v_outcome,
          'mock_question_id',  v_mock_q_id,
          'pyq_question_id',   p_pyq_question_id,
          'pyq_paper_id',      v_q.pyq_paper_id,
          'exam_id',           v_q.exam_id,
          'pyq_year',          v_q.paper_year,
          'topic_id',          v_primary_tag.topic_id,
          'subject_id',        v_topic.subject_id,
          'content_hash',      v_content_hash,
          'correct_option_id', v_correct_opt_id,
          'is_new',            v_is_new
      );

  exception
      when others then
          raise;
  end;
  $fn$
  $ddl$;

  -- ── E. Invalidation trigger ─────────────────────────────────────────────────
  --
  -- When a canonical source row changes in a way that breaks projection
  -- eligibility, the projection is marked stale and the mock_question_bank row
  -- is downgraded to 'draft' (non-selectable). This prevents a stale projection
  -- from remaining in the question pool after its verified source is invalidated.
  --
  -- Selector guard (mock_blueprint_selection.py) additionally excludes
  -- mock_question_bank rows whose pyq_question_id has no active projection.

  -- Shared helper: atomically mark one PYQ question's projection stale and
  -- downgrade the corresponding mock_question_bank row to draft so it falls
  -- out of every selector pool. Called from all trigger branches (fail-closed).
  execute $ddl$
  create or replace function public.fn_invalidate_projection_for_question(p_qid uuid)
  returns void
  language plpgsql
  security definer
  set search_path = public
  as $fn$
  begin
      update public.pyq_mock_question_projections
      set sync_status = 'stale', updated_at = now()
      where pyq_question_id = p_qid
        and sync_status = 'active';

      update public.mock_question_bank
      set reviewer_status = 'draft', updated_at = now()
      where pyq_question_id = p_qid
        and reviewer_status in ('verified', 'published', 'live');
  end;
  $fn$
  $ddl$;

  -- Helper: mark a projection as permanently blocked (ineligible re-sync) and
  -- downgrade the mock bank row to draft. Called by the projection RPC when
  -- an eligibility check fails on a question that was previously active.
  execute $ddl$
  create or replace function public.fn_block_projection_for_question(
      p_qid    uuid,
      p_reason text default null
  )
  returns void
  language plpgsql
  security definer
  set search_path = public
  as $fn$
  begin
      update public.pyq_mock_question_projections
      set sync_status      = 'blocked',
          last_sync_result = jsonb_build_object(
              'outcome',    'blocked',
              'reason',     coalesce(p_reason, 'eligibility_check_failed'),
              'blocked_at', now()::text
          ),
          updated_at       = now()
      where pyq_question_id = p_qid
        and sync_status = 'active';

      update public.mock_question_bank
      set reviewer_status = 'draft', updated_at = now()
      where pyq_question_id = p_qid
        and reviewer_status in ('verified', 'published', 'live');
  end;
  $fn$
  $ddl$;

  execute $ddl$
  create or replace function public.fn_invalidate_pyq_projection()
  returns trigger
  language plpgsql
  security definer
  set search_path = public
  as $fn$
  declare
      v_qid uuid;
  begin
      if TG_TABLE_NAME = 'pyq_questions' then
          if TG_OP = 'UPDATE' then
              -- Invalidate when question leaves verified state.
              if OLD.reviewer_status = 'verified' and NEW.reviewer_status != 'verified' then
                  perform public.fn_invalidate_projection_for_question(NEW.id);
              -- Invalidate when content changes while question remains verified
              -- (question_text, question_type, or correct_option_id pointer drift).
              elsif NEW.reviewer_status = 'verified' and (
                  OLD.question_text       is distinct from NEW.question_text
                  or OLD.question_type    is distinct from NEW.question_type
                  or OLD.correct_option_id is distinct from NEW.correct_option_id
              ) then
                  perform public.fn_invalidate_projection_for_question(NEW.id);
              end if;
          end if;
          return NEW;

      elsif TG_TABLE_NAME = 'pyq_papers' then
          -- Invalidate all questions in the paper on trust_status OR exam_phase_id change.
          if TG_OP = 'UPDATE' and (
              (OLD.trust_status = 'verified' and NEW.trust_status != 'verified')
              or (OLD.exam_phase_id is distinct from NEW.exam_phase_id)
          ) then
              for v_qid in
                  select id from public.pyq_questions where pyq_paper_id = NEW.id
              loop
                  perform public.fn_invalidate_projection_for_question(v_qid);
              end loop;
          end if;
          return NEW;

      elsif TG_TABLE_NAME = 'pyq_options' then
          -- Any material option change (INSERT/DELETE or UPDATE on key fields)
          -- invalidates the projection. Uses shared helper which also downgrades
          -- mock_question_bank so the question falls out of the selector pool.
          if TG_OP = 'DELETE' then
              perform public.fn_invalidate_projection_for_question(OLD.question_id);
              return OLD;
          end if;
          if TG_OP = 'INSERT' then
              perform public.fn_invalidate_projection_for_question(NEW.question_id);
              return NEW;
          end if;
          -- UPDATE: only invalidate on material field changes.
          if OLD.is_correct is distinct from NEW.is_correct
             or (OLD.option_text is distinct from NEW.option_text)
             or (OLD.reviewer_status is distinct from NEW.reviewer_status)
          then
              perform public.fn_invalidate_projection_for_question(NEW.question_id);
          end if;
          return NEW;

      elsif TG_TABLE_NAME = 'pyq_question_topic_tags' then
          if TG_OP = 'DELETE' then
              if OLD.tag_role = 'primary' then
                  perform public.fn_invalidate_projection_for_question(OLD.question_id);
              end if;
              return OLD;
          end if;
          if TG_OP = 'INSERT' then
              -- Inserting a primary tag could push the verified-primary count above 1.
              if NEW.tag_role = 'primary' then
                  perform public.fn_invalidate_projection_for_question(NEW.question_id);
              end if;
              return NEW;
          end if;
          -- UPDATE
          if NEW.tag_role = 'primary'
             or (OLD.tag_role = 'primary' and NEW.tag_role != 'primary')
             or (OLD.reviewer_status is distinct from NEW.reviewer_status
                 and (OLD.tag_role = 'primary' or NEW.tag_role = 'primary'))
          then
              perform public.fn_invalidate_projection_for_question(NEW.question_id);
          end if;
          return NEW;
      end if;

      return coalesce(NEW, OLD);
  end;
  $fn$
  $ddl$;

  -- Create triggers on each source table

  execute 'drop trigger if exists trg_invalidate_pyq_projection_q on public.pyq_questions';
  execute $t$
  create trigger trg_invalidate_pyq_projection_q
  after update on public.pyq_questions
  for each row execute function public.fn_invalidate_pyq_projection()
  $t$;

  execute 'drop trigger if exists trg_invalidate_pyq_projection_p on public.pyq_papers';
  execute $t$
  create trigger trg_invalidate_pyq_projection_p
  after update on public.pyq_papers
  for each row execute function public.fn_invalidate_pyq_projection()
  $t$;

  execute 'drop trigger if exists trg_invalidate_pyq_projection_o_upd on public.pyq_options';
  execute $t$
  create trigger trg_invalidate_pyq_projection_o_upd
  after update on public.pyq_options
  for each row execute function public.fn_invalidate_pyq_projection()
  $t$;

  execute 'drop trigger if exists trg_invalidate_pyq_projection_o_del on public.pyq_options';
  execute $t$
  create trigger trg_invalidate_pyq_projection_o_del
  after delete on public.pyq_options
  for each row execute function public.fn_invalidate_pyq_projection()
  $t$;

  execute 'drop trigger if exists trg_invalidate_pyq_projection_o_ins on public.pyq_options';
  execute $t$
  create trigger trg_invalidate_pyq_projection_o_ins
  after insert on public.pyq_options
  for each row execute function public.fn_invalidate_pyq_projection()
  $t$;

  execute 'drop trigger if exists trg_invalidate_pyq_projection_t_upd on public.pyq_question_topic_tags';
  execute $t$
  create trigger trg_invalidate_pyq_projection_t_upd
  after update on public.pyq_question_topic_tags
  for each row execute function public.fn_invalidate_pyq_projection()
  $t$;

  execute 'drop trigger if exists trg_invalidate_pyq_projection_t_del on public.pyq_question_topic_tags';
  execute $t$
  create trigger trg_invalidate_pyq_projection_t_del
  after delete on public.pyq_question_topic_tags
  for each row execute function public.fn_invalidate_pyq_projection()
  $t$;

  execute 'drop trigger if exists trg_invalidate_pyq_projection_t_ins on public.pyq_question_topic_tags';
  execute $t$
  create trigger trg_invalidate_pyq_projection_t_ins
  after insert on public.pyq_question_topic_tags
  for each row execute function public.fn_invalidate_pyq_projection()
  $t$;

  -- ── F. Grants ───────────────────────────────────────────────────────────────
  --
  -- The projection RPC must ONLY be callable from the backend service_role.
  -- Anon and authenticated PostgREST clients must never be able to invoke it.

  execute 'revoke all on function public.project_pyq_question_to_mock_bank(uuid, uuid, text) from public';
  execute 'revoke execute on function public.project_pyq_question_to_mock_bank(uuid, uuid, text) from anon';
  execute 'revoke execute on function public.project_pyq_question_to_mock_bank(uuid, uuid, text) from authenticated';
  execute 'grant execute on function public.project_pyq_question_to_mock_bank(uuid, uuid, text) to service_role';

  execute 'revoke all on function public.fn_invalidate_pyq_projection() from public';
  execute 'grant execute on function public.fn_invalidate_pyq_projection() to service_role';

  execute 'revoke all on function public.fn_invalidate_projection_for_question(uuid) from public';
  execute 'grant execute on function public.fn_invalidate_projection_for_question(uuid) to service_role';

  execute 'revoke all on function public.fn_block_projection_for_question(uuid, text) from public';
  execute 'grant execute on function public.fn_block_projection_for_question(uuid, text) to service_role';

  -- Revoke direct DML on new tables from public/anon/authenticated.
  -- All projection writes must go through the SECURITY DEFINER RPC only.
  execute 'revoke insert, update, delete on public.pyq_mock_question_projections from public, anon, authenticated';
  execute 'revoke insert, update, delete on public.mock_source_mix_policies from public, anon, authenticated';

  perform pg_notify('pgrst', 'reload schema');
end;
$migration$;
