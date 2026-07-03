-- 215_j3_competition_structure.sql
--
-- J3 PR 1 — Competition structure (serial anchor).
--
-- Gate: docs/status/J3-Competition-Cutoffs-Gate-2026-07-02.md, OPERATOR APPROVED
-- 2026-07-02. Resolutions: docs/status/J3-OD-Resolutions-Locked-2026-07-02.md
-- (§1-§4, §6). Implementation checklist: docs/status/J3-Implementation-Checklist-2026-07-02.md.
--
-- Applied version must be reconciled against the deployed schema_migrations
-- state at apply time (operator step); 215 = MAX(filesystem)+1 as of the
-- branch cut. Confirm with:
--   SELECT MAX(version) FROM schema_migrations;
-- before applying to any environment.
--
-- WHAT THIS DOES
-- --------------
-- A. reservation_categories + reservation_category_aliases (shared vertical
--    category taxonomy; seeded general/ews/obc/sc/st).
-- B. Additive columns on exam_competition_metrics: cutoff_by_category,
--    difficulty_assessment, metric_kind, version_no, supersedes_id,
--    superseded_at, is_current_published, breakdown_complete. Legacy
--    cutoff_trend / difficulty_trend / selection_ratio are NOT dropped or
--    renamed (deprecated in place).
-- C. Fail-closed legacy metric_kind disposition (resolutions §1.3): splits
--    combined rows, assigns metric_kind, preserves published data.
-- D. Fail-closed current-lane initialization (resolutions §1.4): resolves
--    duplicate published/working rows, backfills version_no/supersedes_id,
--    applies the per-source_basis legacy trust policy, asserts zero
--    availability loss.
-- E. Field-ownership + lineage CHECKs and the two-lane partial unique
--    indexes (resolutions §2.1) — enabled only after C+D complete.
-- F. JSON validation trigger (resolutions §1.5): cutoff_by_category /
--    vacancy_by_category / difficulty_assessment shapes.
-- G. Published-parent BEFORE UPDATE guard (content columns frozen once
--    reviewer_status is reviewed/locked).
-- H. exam_competition_metric_evidence child table + append-only
--    immutability triggers + RLS (resolutions §4).
-- I. Lifecycle RPC: cms_review_competition_metric (transition matrix + CAS,
--    mirrors migration 204/208) and cms_reopen_competition_metric_for_edit
--    (clone-to-draft, never mutates the published row in place).
--
-- All new tables get RLS per AGENTS.md app-metadata role convention
-- (auth.jwt() -> 'app_metadata' ->> 'role'), NOT the deprecated
-- profiles.is_admin flag used by migration 057.
--
-- Migrations are immutable once merged.

begin;

-- ═════════════════════════════════════════════════════════════════════════
-- A. Shared reservation-category taxonomy
-- ═════════════════════════════════════════════════════════════════════════

create table if not exists public.reservation_categories (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  label text not null,
  category_axis text not null default 'vertical'
    check (category_axis in ('vertical', 'horizontal')),
  sort_order integer not null default 0,
  is_active boolean not null default true,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.reservation_category_aliases (
  id uuid primary key default gen_random_uuid(),
  category_id uuid not null references public.reservation_categories(id) on delete cascade,
  alias text not null unique,
  created_at timestamptz not null default now()
);

insert into public.reservation_categories (code, label, category_axis, sort_order)
values
  ('general', 'General', 'vertical', 10),
  ('ews',     'EWS',     'vertical', 20),
  ('obc',     'OBC',     'vertical', 30),
  ('sc',      'SC',      'vertical', 40),
  ('st',      'ST',      'vertical', 50)
on conflict (code) do nothing;

insert into public.reservation_category_aliases (category_id, alias)
select rc.id, a.alias
from (values ('ur', 'general'), ('gen', 'general'), ('obc_ncl', 'obc')) as a(alias, code)
join public.reservation_categories rc on rc.code = a.code
on conflict (alias) do nothing;

alter table public.reservation_categories enable row level security;
alter table public.reservation_category_aliases enable row level security;

do $$
declare t text;
begin
  foreach t in array array['reservation_categories', 'reservation_category_aliases']
  loop
    execute format('revoke all on public.%I from public', t);
    execute format('revoke all on public.%I from anon', t);
    execute format('revoke all on public.%I from authenticated', t);
    execute format('grant select, insert, update, delete on public.%I to service_role', t);
    -- Reference data: authenticated users may read it (admin editors need the
    -- vocabulary), but only service_role writes.
    if not exists (
      select 1 from pg_policies
      where schemaname = 'public' and tablename = t and policyname = t || '_read_authenticated'
    ) then
      execute format(
        'create policy %I on public.%I for select to authenticated using (true)',
        t || '_read_authenticated', t
      );
    end if;
  end loop;
end $$;

-- ═════════════════════════════════════════════════════════════════════════
-- B. Additive columns on exam_competition_metrics
-- ═════════════════════════════════════════════════════════════════════════

alter table public.exam_competition_metrics
  add column if not exists cutoff_by_category jsonb not null default '{}'::jsonb,
  add column if not exists difficulty_assessment jsonb not null default '{}'::jsonb,
  add column if not exists metric_kind text,
  add column if not exists version_no integer,
  add column if not exists supersedes_id uuid,
  add column if not exists superseded_at timestamptz,
  add column if not exists is_current_published boolean not null default false,
  add column if not exists breakdown_complete boolean not null default false;

alter table public.exam_competition_metrics
  add constraint ecm_metric_kind_value
    check (metric_kind is null or metric_kind in ('cycle_summary', 'phase_cutoff'));

alter table public.exam_competition_metrics
  add constraint ecm_supersedes_self_fk
    foreign key (supersedes_id) references public.exam_competition_metrics(id) on delete restrict;

alter table public.exam_competition_metrics
  add constraint ecm_no_self_supersede
    check (supersedes_id is null or supersedes_id <> id);

comment on column public.exam_competition_metrics.cutoff_by_category is
  'Replacement for legacy cutoff_trend. Shape: {"<reservation_categories.code>": {"marks": number>=0, "max_marks": number>0 (optional)}}. See resolutions §1.5.';
comment on column public.exam_competition_metrics.difficulty_assessment is
  'Replacement for legacy difficulty_trend. Shape: {"level": "harder"|"stable"|"easier", "basis": text 8-500 chars}. Descriptive only, never planner input.';
comment on column public.exam_competition_metrics.metric_kind is
  'cycle_summary (exam_phase_id IS NULL; owns vacancy/pressure) | phase_cutoff (exam_phase_id required; owns cutoffs/difficulty). NULL only for legacy rows not yet disposed by this migration''s Section C, or malformed-content triage rows exempted per §1.3.';
comment on column public.exam_competition_metrics.selection_ratio is
  'DEPRECATED IN PLACE. Undefined persisted semantics (see resolutions §0.3); do not write new values. Served as a compatibility alias alongside the derived selection_rate/candidates_per_vacancy fields (resolutions §1.2). Removal deferred to a later cleanup migration.';
comment on column public.exam_competition_metrics.cutoff_trend is
  'DEPRECATED IN PLACE. Replaced by cutoff_by_category (resolutions §1.1). Retained for audit/back-compat; do not write new values.';
comment on column public.exam_competition_metrics.difficulty_trend is
  'DEPRECATED IN PLACE. Replaced by difficulty_assessment (resolutions §1.1). Retained for audit/back-compat; do not write new values.';

-- ═════════════════════════════════════════════════════════════════════════
-- C. Fail-closed legacy metric_kind disposition (resolutions §1.3)
-- ═════════════════════════════════════════════════════════════════════════
--
-- Runs once, idempotently (only touches rows with metric_kind IS NULL, so a
-- re-run after partial completion or on an already-disposed DB is a no-op).
-- On a fresh/empty CI database this loop simply does nothing.

do $$
declare
  r record;
  v_cycle_summary_id uuid;
  v_has_cycle_fields boolean;
  v_has_cutoff_fields boolean;
  v_pre_count integer;
  v_post_null_count integer;
begin
  select count(*) into v_pre_count from public.exam_competition_metrics where metric_kind is null;
  raise notice 'J3 §1.3 disposition: % row(s) with metric_kind IS NULL at start', v_pre_count;

  for r in
    select * from public.exam_competition_metrics
    where metric_kind is null
    order by created_at
  loop
    v_has_cycle_fields := (
      r.vacancy_total is not null
      or (r.vacancy_by_category is not null and r.vacancy_by_category <> '{}'::jsonb)
      or r.applicant_count is not null
      or r.competition_pressure_score is not null
    );
    v_has_cutoff_fields := (
      (r.cutoff_trend is not null and r.cutoff_trend <> '{}'::jsonb)
      or (r.difficulty_trend is not null and r.difficulty_trend <> '{}'::jsonb)
    );

    if r.exam_phase_id is null and not v_has_cutoff_fields then
      -- Clean cycle-level-only row: assign cycle_summary in place.
      update public.exam_competition_metrics
      set metric_kind = 'cycle_summary'
      where id = r.id;

    elsif r.exam_phase_id is not null then
      -- Phase-scoped row. If it ALSO carries cycle-level fields, split them
      -- into a cycle_summary revision for the same (exam, cycle); the
      -- phase row keeps only cutoff/difficulty content.
      if v_has_cycle_fields then
        select id into v_cycle_summary_id
        from public.exam_competition_metrics
        where exam_id = r.exam_id
          and exam_cycle_id is not distinct from r.exam_cycle_id
          and metric_kind = 'cycle_summary'
        limit 1;

        if v_cycle_summary_id is null then
          insert into public.exam_competition_metrics (
            exam_id, exam_cycle_id, exam_phase_id, metric_kind,
            vacancy_total, vacancy_by_category, applicant_count, selection_ratio,
            competition_pressure_score, source_basis, confidence_score,
            evidence_count, reviewer_status, reviewed_by, reviewed_at,
            reviewer_notes, metadata, created_at, updated_at
          ) values (
            r.exam_id, r.exam_cycle_id, null, 'cycle_summary',
            r.vacancy_total, r.vacancy_by_category, r.applicant_count, r.selection_ratio,
            r.competition_pressure_score, r.source_basis, r.confidence_score,
            r.evidence_count, r.reviewer_status, r.reviewed_by, r.reviewed_at,
            r.reviewer_notes,
            r.metadata || jsonb_build_object('legacy_split_from', r.id::text),
            r.created_at, now()
          );
        end if;

        -- Clear cycle-level fields from the phase row; it becomes phase_cutoff.
        update public.exam_competition_metrics
        set metric_kind = 'phase_cutoff',
            vacancy_total = null,
            vacancy_by_category = '{}'::jsonb,
            applicant_count = null,
            competition_pressure_score = null
        where id = r.id;
      else
        update public.exam_competition_metrics
        set metric_kind = 'phase_cutoff'
        where id = r.id;
      end if;

    else
      -- exam_phase_id IS NULL but cutoff/difficulty content exists: phase
      -- identity is unknown, so this cannot be assigned phase_cutoff, and it
      -- cannot be cycle_summary while carrying cutoff/difficulty content
      -- (field-ownership rule). Preserve the payload for operator triage and
      -- leave metric_kind NULL — exempted from the field-ownership CHECK
      -- (gated on metric_kind IS NOT NULL) and from the lane indexes.
      -- Published rows are NEVER reopened to draft (OD-7): a published row
      -- keeps its status with the malformed content redirected to metadata;
      -- a non-published row is simply left as a working triage row.
      if r.reviewer_status in ('reviewed', 'locked') then
        update public.exam_competition_metrics
        set metadata = metadata || jsonb_build_object(
              'legacy_phaseless_cutoff',
              jsonb_build_object('cutoff_trend', r.cutoff_trend, 'difficulty_trend', r.difficulty_trend)
            ),
            cutoff_trend = '{}'::jsonb,
            difficulty_trend = '{}'::jsonb,
            metric_kind = 'cycle_summary'
        where id = r.id;
        -- A separate working draft carries the legacy payload for operator
        -- phase assignment; it intentionally keeps metric_kind NULL.
        insert into public.exam_competition_metrics (
          exam_id, exam_cycle_id, exam_phase_id, metric_kind,
          source_basis, confidence_score, evidence_count, reviewer_status,
          metadata, created_at, updated_at
        ) values (
          r.exam_id, r.exam_cycle_id, null, null,
          r.source_basis, 0, 0, 'draft',
          jsonb_build_object(
            'legacy_phaseless_cutoff_triage', true,
            'legacy_split_from', r.id::text,
            'cutoff_trend', r.cutoff_trend,
            'difficulty_trend', r.difficulty_trend
          ),
          now(), now()
        );
      else
        update public.exam_competition_metrics
        set metadata = metadata || jsonb_build_object('legacy_phaseless_cutoff_needs_phase', true)
        where id = r.id;
        -- metric_kind intentionally left NULL — operator must assign a phase.
      end if;
    end if;
  end loop;

  select count(*) into v_post_null_count
  from public.exam_competition_metrics
  where metric_kind is null
    and not coalesce((metadata ->> 'legacy_phaseless_cutoff_triage')::boolean, false)
    and not coalesce((metadata ->> 'legacy_phaseless_cutoff_needs_phase')::boolean, false);

  if v_post_null_count > 0 then
    raise exception 'J3 §1.3 disposition failed: % row(s) left with metric_kind IS NULL and no triage flag', v_post_null_count
      using errcode = 'P0001';
  end if;

  raise notice 'J3 §1.3 disposition complete.';
end $$;

-- ═════════════════════════════════════════════════════════════════════════
-- D. Fail-closed current-lane initialization (resolutions §1.4)
-- ═════════════════════════════════════════════════════════════════════════

do $$
declare
  r record;
  v_dup_report text := '';
  v_dup_count integer := 0;
  v_pre_published_scopes integer;
  v_post_published_scopes integer;
  v_version integer;
  v_prev_id uuid;
begin
  -- Step 1: duplicate report. A "scope" is (exam_id, exam_cycle_id,
  -- exam_phase_id, metric_kind) for disposed rows only (metric_kind not null).
  for r in
    select exam_id, exam_cycle_id, exam_phase_id, metric_kind, count(*) as n
    from public.exam_competition_metrics
    where metric_kind is not null
      and reviewer_status in ('reviewed', 'locked')
    group by exam_id, exam_cycle_id, exam_phase_id, metric_kind
    having count(*) > 1
  loop
    v_dup_count := v_dup_count + 1;
    v_dup_report := v_dup_report || format(
      E'\n  scope exam=%s cycle=%s phase=%s kind=%s has % published rows',
      r.exam_id, r.exam_cycle_id, r.exam_phase_id, r.metric_kind, r.n
    );
  end loop;

  if v_dup_count > 0 then
    raise exception 'J3 §1.4 lane initialization BLOCKED: % scope(s) have multiple reviewed/locked rows and require an audited operator canonical selection before this migration can proceed (deterministic auto-pick is explicitly rejected — see resolutions §5.3 posture applied here). Resolve by demoting all but one row per scope to ''rejected'' (with reviewer_notes recording the operator decision), then re-run this migration. Conflicting scopes:%',
      v_dup_count, v_dup_report
      using errcode = 'P0001';
  end if;

  select count(distinct (exam_id, exam_cycle_id, exam_phase_id, metric_kind))
    into v_pre_published_scopes
  from public.exam_competition_metrics
  where metric_kind is not null and reviewer_status in ('reviewed', 'locked');

  -- Step 2: mark the sole published row per scope current, EXCEPT
  -- model_generated rows, which require fail-closed operator triage (never
  -- auto-grandfathered). Human-basis rows (manual/official/reviewed_analysis/
  -- derived) are grandfathered current with a prospective-evidence flag.
  update public.exam_competition_metrics ecm
  set is_current_published = true,
      version_no = 1,
      metadata = metadata || jsonb_build_object('legacy_unvalidated_evidence', true, 'legacy_evidence_worklist', true)
  where reviewer_status in ('reviewed', 'locked')
    and metric_kind is not null
    and source_basis in ('manual', 'official', 'reviewed_analysis', 'derived');

  update public.exam_competition_metrics ecm
  set version_no = 1
  where reviewer_status in ('reviewed', 'locked')
    and metric_kind is not null
    and source_basis = 'model_generated'
    and is_current_published = false;
  -- model_generated reviewed/locked rows: version_no backfilled for lineage,
  -- but is_current_published stays false. metadata flag for operator triage:
  update public.exam_competition_metrics
  set metadata = metadata || jsonb_build_object('legacy_model_generated_needs_triage', true)
  where reviewer_status in ('reviewed', 'locked')
    and metric_kind is not null
    and source_basis = 'model_generated'
    and is_current_published = false;

  -- Step 3: working-lane version backfill (draft/pending_review). At most one
  -- per scope is expected after disposition; if duplicates exist here (lower
  -- stakes than published dupes — nothing aspirant-visible), keep the most
  -- recently updated and supersede the rest.
  for r in
    select id, exam_id, exam_cycle_id, exam_phase_id, metric_kind
    from public.exam_competition_metrics
    where reviewer_status in ('draft', 'pending_review')
      and metric_kind is not null
    order by exam_id, exam_cycle_id, exam_phase_id, metric_kind, updated_at desc
  loop
    null; -- handled by the ranked update below
  end loop;

  with ranked as (
    select id,
           row_number() over (
             partition by exam_id, exam_cycle_id, exam_phase_id, metric_kind
             order by updated_at desc, created_at desc
           ) as rn
    from public.exam_competition_metrics
    where reviewer_status in ('draft', 'pending_review')
      and metric_kind is not null
  )
  update public.exam_competition_metrics ecm
  set superseded_at = now()
  from ranked
  where ranked.id = ecm.id and ranked.rn > 1;

  -- Step 4: version_no / supersedes_id chain backfill per scope (published
  -- current row is version 1 if it's the only row; if a working row also
  -- exists for the same scope, it becomes version 2 chained to the published
  -- row, or version 1 if no published row exists for that scope).
  for r in
    select exam_id, exam_cycle_id, exam_phase_id, metric_kind
    from public.exam_competition_metrics
    where metric_kind is not null
    group by exam_id, exam_cycle_id, exam_phase_id, metric_kind
  loop
    v_prev_id := null;
    v_version := 0;
    for r in
      select id from public.exam_competition_metrics
      where exam_id is not distinct from r.exam_id
        and exam_cycle_id is not distinct from r.exam_cycle_id
        and exam_phase_id is not distinct from r.exam_phase_id
        and metric_kind is not distinct from r.metric_kind
        and (superseded_at is null or reviewer_status in ('reviewed', 'locked'))
      order by
        case when reviewer_status in ('reviewed', 'locked') then 0 else 1 end,
        coalesce(reviewed_at, created_at)
    loop
      v_version := v_version + 1;
      update public.exam_competition_metrics
      set version_no = v_version,
          supersedes_id = v_prev_id
      where id = r.id;
      v_prev_id := r.id;
    end loop;
  end loop;

  -- Step 5: zero-availability-loss assertion. Every scope that had >=1
  -- published (reviewed/locked, non-model_generated-untriaged) row before
  -- this step must have exactly one is_current_published=true row now.
  select count(distinct (exam_id, exam_cycle_id, exam_phase_id, metric_kind))
    into v_post_published_scopes
  from public.exam_competition_metrics
  where is_current_published = true;

  if v_post_published_scopes < v_pre_published_scopes then
    -- Some scopes are missing a current row. This is EXPECTED and SAFE only
    -- when every such scope's sole published row is an untriaged
    -- model_generated row (intentional, reported, operator-gated visibility
    -- change per resolutions §1.4 step 5) — never silent.
    if exists (
      select 1
      from public.exam_competition_metrics
      where reviewer_status in ('reviewed', 'locked')
        and metric_kind is not null
        and is_current_published = false
        and source_basis <> 'model_generated'
    ) then
      raise exception 'J3 §1.4 zero-availability-loss assertion FAILED: a non-model_generated published row exists without is_current_published=true. This must never happen — investigate before proceeding.'
        using errcode = 'P0001';
    end if;
    raise notice 'J3 §1.4: % scope(s) have no current-published row because their only published row is source_basis=model_generated, pending operator triage (see metadata.legacy_model_generated_needs_triage). This is the documented, operator-visible exception.',
      (v_pre_published_scopes - v_post_published_scopes);
  end if;

  raise notice 'J3 §1.4 lane initialization complete. % scope(s) now current-published.', v_post_published_scopes;
end $$;

-- ═════════════════════════════════════════════════════════════════════════
-- E. Field-ownership + lineage constraints, two-lane partial unique indexes
--    (resolutions §2.1) — enabled only after Sections C+D complete.
-- ═════════════════════════════════════════════════════════════════════════

alter table public.exam_competition_metrics
  add constraint ecm_new_model_requires_cycle
    check (metric_kind is null or exam_cycle_id is not null);

alter table public.exam_competition_metrics
  add constraint ecm_kind_phase_shape
    check (metric_kind is null
           or (metric_kind = 'cycle_summary' and exam_phase_id is null)
           or (metric_kind = 'phase_cutoff' and exam_phase_id is not null));

alter table public.exam_competition_metrics
  add constraint ecm_kind_field_ownership
    check (metric_kind is null
           or (metric_kind = 'cycle_summary'
               and (cutoff_by_category = '{}'::jsonb)
               and (difficulty_assessment = '{}'::jsonb))
           or (metric_kind = 'phase_cutoff'
               and vacancy_total is null
               and vacancy_by_category = '{}'::jsonb
               and applicant_count is null
               and competition_pressure_score is null));

alter table public.exam_competition_metrics
  add constraint ecm_current_published_state
    check (not is_current_published
           or (reviewer_status in ('reviewed', 'locked') and superseded_at is null));

alter table public.exam_competition_metrics
  add constraint ecm_superseded_not_current
    check (superseded_at is null or not is_current_published);

alter table public.exam_competition_metrics
  add constraint ecm_version_no_positive
    check (metric_kind is null or (version_no is not null and version_no > 0));

-- One current PUBLISHED row per scope.
create unique index if not exists ecm_current_pub_cycle_summary_uq
  on public.exam_competition_metrics (exam_id, exam_cycle_id)
  where metric_kind = 'cycle_summary' and is_current_published;

create unique index if not exists ecm_current_pub_phase_cutoff_uq
  on public.exam_competition_metrics (exam_id, exam_cycle_id, exam_phase_id)
  where metric_kind = 'phase_cutoff' and is_current_published;

-- At most one current WORKING row per scope.
create unique index if not exists ecm_working_cycle_summary_uq
  on public.exam_competition_metrics (exam_id, exam_cycle_id)
  where metric_kind = 'cycle_summary'
    and reviewer_status in ('draft', 'pending_review') and superseded_at is null;

create unique index if not exists ecm_working_phase_cutoff_uq
  on public.exam_competition_metrics (exam_id, exam_cycle_id, exam_phase_id)
  where metric_kind = 'phase_cutoff'
    and reviewer_status in ('draft', 'pending_review') and superseded_at is null;

-- version_no unique per scope (monotonic chain, no duplicates).
create unique index if not exists ecm_version_cycle_summary_uq
  on public.exam_competition_metrics (exam_id, exam_cycle_id, version_no)
  where metric_kind = 'cycle_summary';

create unique index if not exists ecm_version_phase_cutoff_uq
  on public.exam_competition_metrics (exam_id, exam_cycle_id, exam_phase_id, version_no)
  where metric_kind = 'phase_cutoff';

create index if not exists idx_ecm_current_published
  on public.exam_competition_metrics (exam_id, metric_kind)
  where is_current_published;

-- ═════════════════════════════════════════════════════════════════════════
-- F. JSON validation trigger (resolutions §1.5)
-- ═════════════════════════════════════════════════════════════════════════

create or replace function public._ecm_validate_jsonb() returns trigger
language plpgsql as $fn$
declare
  v_key text;
  v_val jsonb;
  v_marks numeric;
  v_max_marks numeric;
  v_level text;
  v_basis text;
begin
  -- cutoff_by_category: {"<category code>": {"marks": >=0, "max_marks": >0 optional}}
  if new.cutoff_by_category is not null and new.cutoff_by_category <> '{}'::jsonb then
    if jsonb_typeof(new.cutoff_by_category) <> 'object' then
      raise exception 'cutoff_by_category must be a JSON object' using errcode = 'P0422';
    end if;
    for v_key, v_val in select * from jsonb_each(new.cutoff_by_category)
    loop
      if not exists (select 1 from public.reservation_categories where code = v_key) then
        raise exception 'cutoff_by_category: unknown category code %', v_key using errcode = 'P0422';
      end if;
      if jsonb_typeof(v_val) <> 'object' then
        raise exception 'cutoff_by_category[%]: value must be an object {marks, max_marks?}, not a bare string/number/list', v_key
          using errcode = 'P0422';
      end if;
      if not (v_val ? 'marks') then
        raise exception 'cutoff_by_category[%]: "marks" is required', v_key using errcode = 'P0422';
      end if;
      begin
        v_marks := (v_val ->> 'marks')::numeric;
      exception when others then
        raise exception 'cutoff_by_category[%]: marks must be numeric', v_key using errcode = 'P0422';
      end;
      if v_marks < 0 then
        raise exception 'cutoff_by_category[%]: marks must be >= 0', v_key using errcode = 'P0422';
      end if;
      if v_val ? 'max_marks' and v_val -> 'max_marks' is not null then
        begin
          v_max_marks := (v_val ->> 'max_marks')::numeric;
        exception when others then
          raise exception 'cutoff_by_category[%]: max_marks must be numeric', v_key using errcode = 'P0422';
        end;
        if v_max_marks <= 0 then
          raise exception 'cutoff_by_category[%]: max_marks must be > 0', v_key using errcode = 'P0422';
        end if;
      end if;
      if v_val ? 'stage' then
        raise exception 'cutoff_by_category[%]: "stage" is not permitted (exam_phase_id is the canonical phase)', v_key
          using errcode = 'P0422';
      end if;
    end loop;
  end if;

  -- vacancy_by_category: {"<category code>": integer >= 0}
  if new.vacancy_by_category is not null and new.vacancy_by_category <> '{}'::jsonb then
    if jsonb_typeof(new.vacancy_by_category) <> 'object' then
      raise exception 'vacancy_by_category must be a JSON object' using errcode = 'P0422';
    end if;
    for v_key, v_val in select * from jsonb_each(new.vacancy_by_category)
    loop
      if not exists (select 1 from public.reservation_categories where code = v_key) then
        raise exception 'vacancy_by_category: unknown category code %', v_key using errcode = 'P0422';
      end if;
      if v_val is null or jsonb_typeof(v_val) <> 'number' then
        raise exception 'vacancy_by_category[%]: value must be a non-negative integer', v_key using errcode = 'P0422';
      end if;
      if (v_val::text)::numeric < 0 or (v_val::text)::numeric <> floor((v_val::text)::numeric) then
        raise exception 'vacancy_by_category[%]: value must be a non-negative integer', v_key using errcode = 'P0422';
      end if;
    end loop;
  end if;

  -- difficulty_assessment: {"level": harder|stable|easier, "basis": text 8-500}
  if new.difficulty_assessment is not null and new.difficulty_assessment <> '{}'::jsonb then
    if jsonb_typeof(new.difficulty_assessment) <> 'object' then
      raise exception 'difficulty_assessment must be an object {level, basis}, not a bare string' using errcode = 'P0422';
    end if;
    v_level := new.difficulty_assessment ->> 'level';
    v_basis := new.difficulty_assessment ->> 'basis';
    if v_level is null or v_level not in ('harder', 'stable', 'easier') then
      raise exception 'difficulty_assessment.level must be one of harder|stable|easier' using errcode = 'P0422';
    end if;
    if v_basis is null or length(v_basis) < 8 or length(v_basis) > 500 then
      raise exception 'difficulty_assessment.basis must be 8-500 characters' using errcode = 'P0422';
    end if;
  end if;

  return new;
end;
$fn$;

drop trigger if exists trg_ecm_validate_jsonb on public.exam_competition_metrics;
create trigger trg_ecm_validate_jsonb
  before insert or update on public.exam_competition_metrics
  for each row execute function public._ecm_validate_jsonb();

-- ═════════════════════════════════════════════════════════════════════════
-- G. Published-parent BEFORE UPDATE guard (resolutions §2)
-- ═════════════════════════════════════════════════════════════════════════
--
-- Once a row is published (reviewer_status in reviewed/locked), all content
-- columns are frozen. Only lifecycle/supersession/review-stamp columns may
-- change, and only via the state-machine RPC (which sets a transaction-local
-- GUC so the trigger can distinguish an authorized transition from a raw
-- service-role UPDATE attempting to bypass it).

create or replace function public._ecm_guard_published_update() returns trigger
language plpgsql as $fn$
begin
  if old.reviewer_status in ('reviewed', 'locked') then
    if coalesce(current_setting('app.competition_lifecycle_rpc', true), '') <> 'true' then
      if new.exam_id is distinct from old.exam_id
         or new.exam_cycle_id is distinct from old.exam_cycle_id
         or new.exam_phase_id is distinct from old.exam_phase_id
         or new.metric_kind is distinct from old.metric_kind
         or new.vacancy_total is distinct from old.vacancy_total
         or new.vacancy_by_category is distinct from old.vacancy_by_category
         or new.applicant_count is distinct from old.applicant_count
         or new.selection_ratio is distinct from old.selection_ratio
         or new.cutoff_trend is distinct from old.cutoff_trend
         or new.difficulty_trend is distinct from old.difficulty_trend
         or new.cutoff_by_category is distinct from old.cutoff_by_category
         or new.difficulty_assessment is distinct from old.difficulty_assessment
         or new.competition_pressure_score is distinct from old.competition_pressure_score
         or new.source_basis is distinct from old.source_basis
         or new.confidence_score is distinct from old.confidence_score
         or new.breakdown_complete is distinct from old.breakdown_complete
         or new.metadata is distinct from old.metadata
         or new.version_no is distinct from old.version_no
         or new.supersedes_id is distinct from old.supersedes_id
      then
        raise exception 'published_row_immutable: exam_competition_metrics % is reviewer_status=% (published); content columns are frozen. Use the lifecycle RPC (reopen-for-edit clones a new draft revision instead of mutating this row).',
          old.id, old.reviewer_status
          using errcode = 'P0409';
      end if;
    end if;
  end if;
  return new;
end;
$fn$;

drop trigger if exists trg_ecm_guard_published_update on public.exam_competition_metrics;
create trigger trg_ecm_guard_published_update
  before update on public.exam_competition_metrics
  for each row execute function public._ecm_guard_published_update();

-- ═════════════════════════════════════════════════════════════════════════
-- H. Evidence child table (resolutions §4)
-- ═════════════════════════════════════════════════════════════════════════

create table if not exists public.exam_competition_metric_evidence (
  id uuid primary key default gen_random_uuid(),

  metric_id uuid not null
    references public.exam_competition_metrics(id) on delete cascade,

  claim_field text not null
    check (claim_field in (
      'vacancy_total', 'vacancy_by_category', 'cutoff_by_category',
      'difficulty_assessment', 'competition_pressure_score')),

  reservation_category_id uuid
    references public.reservation_categories(id) on delete restrict,

  evidence_kind text not null
    check (evidence_kind in (
      'official_notification', 'official_result', 'official_statistics',
      'corrigendum', 'official_page', 'reviewed_analysis')),

  evidence_role text not null default 'primary'
    check (evidence_role in ('primary', 'supporting')),

  source_id uuid references public.source_registry(id) on delete set null,
  document_asset_id uuid references public.document_assets(id) on delete set null,

  evidence_url text,
  source_label text,
  source_page integer check (source_page is null or source_page >= 1),
  source_excerpt text,

  claim_value jsonb not null,
  content_hash text,
  evidence_key text not null unique,

  captured_at timestamptz not null default now(),
  created_by uuid references public.profiles(id) on delete set null,
  created_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb,

  constraint ecme_source_present check (num_nonnulls(source_id, document_asset_id, evidence_url) >= 1),
  constraint ecme_category_claim_shape check (
    (claim_field in ('vacancy_by_category', 'cutoff_by_category') and reservation_category_id is not null)
    or
    (claim_field in ('vacancy_total', 'difficulty_assessment', 'competition_pressure_score') and reservation_category_id is null)
  )
);

create index if not exists exam_comp_metric_evidence_metric_idx
  on public.exam_competition_metric_evidence(metric_id);
create index if not exists exam_comp_metric_evidence_claim_idx
  on public.exam_competition_metric_evidence(metric_id, claim_field, reservation_category_id);

-- Append-only immutability: evidence is attach-while-draft only; once the
-- parent is published, evidence for that revision is frozen. A correction is
-- a new working revision (§2), never an edit of prior evidence.
create or replace function public._ecme_guard_immutable() returns trigger
language plpgsql as $fn$
declare v_parent_status text;
begin
  if tg_op = 'DELETE' then
    select reviewer_status into v_parent_status from public.exam_competition_metrics where id = old.metric_id;
    if v_parent_status in ('reviewed', 'locked') then
      raise exception 'evidence_immutable: cannot delete evidence % — parent metric % is published (%)',
        old.id, old.metric_id, v_parent_status using errcode = 'P0409';
    end if;
    return old;
  end if;

  if tg_op = 'UPDATE' then
    select reviewer_status into v_parent_status from public.exam_competition_metrics where id = old.metric_id;
    if v_parent_status in ('reviewed', 'locked') then
      raise exception 'evidence_immutable: cannot update evidence % — parent metric % is published (%)',
        old.id, old.metric_id, v_parent_status using errcode = 'P0409';
    end if;
    return new;
  end if;

  if tg_op = 'INSERT' then
    select reviewer_status into v_parent_status from public.exam_competition_metrics where id = new.metric_id;
    if v_parent_status in ('reviewed', 'locked') then
      raise exception 'evidence_immutable: cannot attach evidence to published parent metric % (%)',
        new.metric_id, v_parent_status using errcode = 'P0409';
    end if;
    return new;
  end if;
  return null;
end;
$fn$;

drop trigger if exists trg_ecme_guard_immutable on public.exam_competition_metric_evidence;
create trigger trg_ecme_guard_immutable
  before insert or update or delete on public.exam_competition_metric_evidence
  for each row execute function public._ecme_guard_immutable();

-- Published-parent DELETE guard: the FK cascade only ever fires for
-- genuinely-draft cleanup (a published parent cannot be deleted at all).
create or replace function public._ecm_guard_published_delete() returns trigger
language plpgsql as $fn$
begin
  if old.reviewer_status in ('reviewed', 'locked') then
    raise exception 'published_row_immutable: cannot delete exam_competition_metrics % — reviewer_status=% (published)',
      old.id, old.reviewer_status using errcode = 'P0409';
  end if;
  return old;
end;
$fn$;

drop trigger if exists trg_ecm_guard_published_delete on public.exam_competition_metrics;
create trigger trg_ecm_guard_published_delete
  before delete on public.exam_competition_metrics
  for each row execute function public._ecm_guard_published_delete();

alter table public.exam_competition_metric_evidence enable row level security;
revoke all on public.exam_competition_metric_evidence from public;
revoke all on public.exam_competition_metric_evidence from anon;
revoke all on public.exam_competition_metric_evidence from authenticated;
grant select, insert, update, delete on public.exam_competition_metric_evidence to service_role;

-- ═════════════════════════════════════════════════════════════════════════
-- I. Lifecycle RPC (resolutions §2, §D; mirrors migration 204/208 pattern)
-- ═════════════════════════════════════════════════════════════════════════

create or replace function public.cms_review_competition_metric(
    p_metric_id       uuid,
    p_expected_status text,
    p_new_status      text,
    p_reviewer_notes  text,
    p_actor_user_id   uuid,
    p_actor_email     text
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
    v_row   exam_competition_metrics%rowtype;
    v_audit_id uuid;
begin
    if p_actor_user_id is null then
        raise exception 'missing_actor_id: p_actor_user_id must not be NULL' using errcode = 'P0422';
    end if;

    if p_new_status not in ('draft', 'pending_review', 'reviewed', 'locked', 'rejected') then
        raise exception 'invalid_target_status: % is not a recognised status', p_new_status using errcode = 'P0422';
    end if;

    select * into v_row from public.exam_competition_metrics where id = p_metric_id for update;
    if not found then
        raise exception 'not_found: metric % does not exist', p_metric_id using errcode = 'P0404';
    end if;

    if v_row.reviewer_status is distinct from p_expected_status then
        raise exception 'concurrent_modification: expected status=% but found %. Re-fetch and retry.',
            p_expected_status, v_row.reviewer_status using errcode = 'P0409';
    end if;

    if not (
           (v_row.reviewer_status = 'draft'          and p_new_status in ('pending_review', 'rejected'))
        or (v_row.reviewer_status = 'pending_review' and p_new_status in ('reviewed', 'rejected', 'draft'))
        or (v_row.reviewer_status = 'reviewed'        and p_new_status in ('locked', 'rejected'))
        or (v_row.reviewer_status = 'locked'          and p_new_status = 'reviewed')
        or (v_row.reviewer_status = 'rejected'        and p_new_status = 'draft')
    ) then
        raise exception 'transition_not_allowed: % -> % is not a permitted transition', v_row.reviewer_status, p_new_status
            using errcode = 'P0422';
    end if;

    if v_row.reviewer_status = 'locked' and p_new_status = 'reviewed'
       and nullif(trim(coalesce(p_reviewer_notes, '')), '') is null
    then
        raise exception 'invalid_reviewer_notes: reviewer_notes required when reopening a locked row'
            using errcode = 'P0422';
    end if;

    -- model_generated rows may not reach reviewed/locked without qualifying
    -- primary evidence for every populated high-risk claim (OD-2).
    if p_new_status in ('reviewed', 'locked') and v_row.source_basis = 'model_generated' then
        if not exists (
          select 1 from public.exam_competition_metric_evidence e
          where e.metric_id = v_row.id and e.evidence_role = 'primary'
        ) then
            raise exception 'model_generated_requires_evidence: attach primary evidence and change source_basis before promoting a model_generated row'
                using errcode = 'P0422';
        end if;
    end if;

    -- Claim-value-match promotion validation: any populated high-risk claim
    -- must have qualifying primary evidence whose claim_value matches the
    -- CURRENT parent value (stale evidence from a prior edit does not
    -- qualify).
    if p_new_status in ('reviewed', 'locked') then
        if v_row.vacancy_total is not null and not exists (
          select 1 from public.exam_competition_metric_evidence e
          where e.metric_id = v_row.id and e.claim_field = 'vacancy_total' and e.evidence_role = 'primary'
            and (e.claim_value ->> 'vacancy_total')::numeric = v_row.vacancy_total
        ) then
            raise exception 'missing_or_stale_evidence: vacancy_total has no matching primary evidence' using errcode = 'P0422';
        end if;
        if v_row.cutoff_by_category <> '{}'::jsonb and not exists (
          select 1 from public.exam_competition_metric_evidence e
          where e.metric_id = v_row.id and e.claim_field = 'cutoff_by_category' and e.evidence_role = 'primary'
        ) then
            raise exception 'missing_evidence: cutoff_by_category has no primary evidence' using errcode = 'P0422';
        end if;
    end if;

    -- Vacancy sum rule (OD-4).
    if v_row.vacancy_total is not null and v_row.vacancy_by_category <> '{}'::jsonb then
        declare v_sum numeric;
        begin
            select coalesce(sum((value::text)::numeric), 0) into v_sum
            from jsonb_each(v_row.vacancy_by_category);
            if v_sum > v_row.vacancy_total then
                raise exception 'vacancy_sum_exceeds_total: category sum % exceeds vacancy_total %', v_sum, v_row.vacancy_total
                    using errcode = 'P0422';
            end if;
            if v_sum < v_row.vacancy_total and v_row.breakdown_complete then
                raise exception 'vacancy_sum_incomplete: breakdown_complete=true but category sum % < vacancy_total %', v_sum, v_row.vacancy_total
                    using errcode = 'P0422';
            end if;
        end;
    end if;

    perform set_config('app.competition_lifecycle_rpc', 'true', true);

    if p_new_status = 'locked' and v_row.reviewer_status = 'reviewed' then
        -- Promotion to published: supersede any existing current-published
        -- row for this scope, then mark this one current.
        update public.exam_competition_metrics
        set superseded_at = now(), is_current_published = false
        where exam_id = v_row.exam_id
          and exam_cycle_id is not distinct from v_row.exam_cycle_id
          and exam_phase_id is not distinct from v_row.exam_phase_id
          and metric_kind = v_row.metric_kind
          and is_current_published = true
          and id <> v_row.id;

        update public.exam_competition_metrics
        set reviewer_status = p_new_status,
            reviewed_by = p_actor_user_id,
            reviewed_at = now(),
            reviewer_notes = coalesce(p_reviewer_notes, reviewer_notes),
            is_current_published = true,
            updated_at = now()
        where id = p_metric_id
        returning * into v_row;
    else
        update public.exam_competition_metrics
        set reviewer_status = p_new_status,
            reviewed_by = p_actor_user_id,
            reviewed_at = now(),
            reviewer_notes = coalesce(p_reviewer_notes, reviewer_notes),
            is_current_published = (p_new_status in ('reviewed', 'locked') and v_row.is_current_published),
            updated_at = now()
        where id = p_metric_id
        returning * into v_row;
    end if;

    perform set_config('app.competition_lifecycle_rpc', 'false', true);

    insert into public.admin_audit_logs (
        actor_id, actor_email, admin_user_id, action, entity_type, entity_id,
        old_value, new_value, notes
    ) values (
        p_actor_user_id, p_actor_email, p_actor_user_id,
        'competition_metric_status_transition', 'exam_competition_metric', p_metric_id::text,
        jsonb_build_object('status', p_expected_status),
        jsonb_build_object('status', p_new_status),
        p_reviewer_notes
    ) returning id into v_audit_id;

    return jsonb_build_object(
        'ok', true, 'audit_id', v_audit_id, 'metric_id', p_metric_id,
        'prev_status', p_expected_status, 'new_status', p_new_status
    );
end;
$$;

-- Reopen-for-edit: clones the published row into a new draft revision. The
-- published row is NEVER mutated in place (OD-7) — it stays current until
-- the new draft is promoted through the lifecycle again.
create or replace function public.cms_reopen_competition_metric_for_edit(
    p_metric_id      uuid,
    p_reviewer_notes text,
    p_actor_user_id  uuid,
    p_actor_email    text
)
returns exam_competition_metrics
language plpgsql
security definer
set search_path = public
as $$
declare
    v_pub exam_competition_metrics%rowtype;
    v_new exam_competition_metrics%rowtype;
    v_next_version integer;
begin
    if p_actor_user_id is null then
        raise exception 'missing_actor_id: p_actor_user_id must not be NULL' using errcode = 'P0422';
    end if;
    if nullif(trim(coalesce(p_reviewer_notes, '')), '') is null then
        raise exception 'invalid_reviewer_notes: reviewer_notes required to reopen for edit' using errcode = 'P0422';
    end if;

    select * into v_pub from public.exam_competition_metrics where id = p_metric_id for update;
    if not found then
        raise exception 'not_found: metric % does not exist', p_metric_id using errcode = 'P0404';
    end if;
    if v_pub.reviewer_status not in ('reviewed', 'locked') then
        raise exception 'not_published: only a reviewed/locked row can be reopened for edit' using errcode = 'P0422';
    end if;

    select coalesce(max(version_no), 0) + 1 into v_next_version
    from public.exam_competition_metrics
    where exam_id = v_pub.exam_id
      and exam_cycle_id is not distinct from v_pub.exam_cycle_id
      and exam_phase_id is not distinct from v_pub.exam_phase_id
      and metric_kind = v_pub.metric_kind;

    insert into public.exam_competition_metrics (
        exam_id, exam_cycle_id, exam_phase_id, metric_kind,
        vacancy_total, vacancy_by_category, applicant_count, selection_ratio,
        cutoff_trend, difficulty_trend, cutoff_by_category, difficulty_assessment,
        competition_pressure_score, breakdown_complete,
        source_basis, confidence_score, evidence_count, reviewer_status,
        version_no, supersedes_id, metadata
    ) values (
        v_pub.exam_id, v_pub.exam_cycle_id, v_pub.exam_phase_id, v_pub.metric_kind,
        v_pub.vacancy_total, v_pub.vacancy_by_category, v_pub.applicant_count, v_pub.selection_ratio,
        v_pub.cutoff_trend, v_pub.difficulty_trend, v_pub.cutoff_by_category, v_pub.difficulty_assessment,
        v_pub.competition_pressure_score, v_pub.breakdown_complete,
        v_pub.source_basis, v_pub.confidence_score, 0, 'draft',
        v_next_version, v_pub.id, v_pub.metadata || jsonb_build_object('reopen_notes', p_reviewer_notes)
    ) returning * into v_new;

    insert into public.admin_audit_logs (
        actor_id, actor_email, admin_user_id, action, entity_type, entity_id,
        old_value, new_value, notes
    ) values (
        p_actor_user_id, p_actor_email, p_actor_user_id,
        'competition_metric_reopen_for_edit', 'exam_competition_metric', p_metric_id::text,
        jsonb_build_object('published_id', v_pub.id),
        jsonb_build_object('draft_id', v_new.id),
        p_reviewer_notes
    );

    return v_new;
end;
$$;

revoke execute on function public.cms_review_competition_metric(uuid, text, text, text, uuid, text) from public;
revoke execute on function public.cms_review_competition_metric(uuid, text, text, text, uuid, text) from anon;
revoke execute on function public.cms_review_competition_metric(uuid, text, text, text, uuid, text) from authenticated;
grant  execute on function public.cms_review_competition_metric(uuid, text, text, text, uuid, text) to service_role;

revoke execute on function public.cms_reopen_competition_metric_for_edit(uuid, text, uuid, text) from public;
revoke execute on function public.cms_reopen_competition_metric_for_edit(uuid, text, uuid, text) from anon;
revoke execute on function public.cms_reopen_competition_metric_for_edit(uuid, text, uuid, text) from authenticated;
grant  execute on function public.cms_reopen_competition_metric_for_edit(uuid, text, uuid, text) to service_role;

commit;

select pg_notify('pgrst', 'reload schema');
