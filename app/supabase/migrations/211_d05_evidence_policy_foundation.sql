-- 211_d05_evidence_policy_foundation.sql
--
-- D05 evidence-policy foundation (PR-1 of the D12-v1 "full D05 engine" program).
-- SCHEMA ONLY — no readiness/planner behavior change. The document_policy evaluator
-- that consumes these tables + the cycle_readiness Step 9 wiring land in PR-2; planner
-- enforcement + backfill in PR-3; upload/review UI in PR-4.
--
-- Implements the normalized evidence model from D05 §2–5:
--   §2 exam_evidence_requirements            — the policy table (seeded below)
--   §3 exam_document_evidence                — relational document registration + trust lifecycle
--   §4 exam_document_evidence_roles          — one source document may satisfy multiple roles
--   §5 exam_evidence_requirement_overrides   — narrow per-exam/cycle/phase exceptions
--   + exam_evidence_kinds                    — canonical evidence-kind vocabulary (shared FK)
--
-- ACCESS MODEL (governance tables — see PR #843 review): these four config/evidence tables
-- are backend/FastAPI mediated ONLY. RLS is enabled and NO authenticated policy is created, so
-- direct PostgREST access by anon/authenticated is denied by default; table privileges are
-- REVOKED from public/anon/authenticated and GRANTed to service_role (which the backend uses and
-- which bypasses RLS). This deliberately does NOT consult the deprecated profiles.is_admin flag
-- (AGENTS.md). All mutation — including trust_status transitions — must flow through FastAPI
-- permission + audit paths in PR-2/PR-4. Operator staging validation must assert the access
-- matrix (anon / ordinary authenticated / stale-profile-admin / app-metadata admin / service role).
--
-- Migrations are immutable once merged.

-- ─────────────────────────────────────────────────────────────────────────────
-- Canonical evidence-kind vocabulary (P2 — shared, not free text)
-- ─────────────────────────────────────────────────────────────────────────────
create table if not exists public.exam_evidence_kinds (
  kind text primary key,
  description text,
  created_at timestamptz not null default now()
);

insert into public.exam_evidence_kinds (kind, description) values
  ('primary_cycle_document',  'Notification / bulletin / prospectus / handbook — normalized primary cycle document'),
  ('syllabus',                'Official syllabus'),
  ('exam_pattern',            'Official pattern or scheme'),
  ('pyq_paper',               'Compatible previous-year question paper evidence'),
  ('answer_key',              'Official answer key'),
  ('phase_rules',             'Official phase rules or standards (interview/physical/medical/doc-verification)'),
  ('corrigendum',             'Official corrigendum'),
  ('notification',            'Notification document (display subtype of primary_cycle_document)'),
  ('application_instructions','Application instructions'),
  ('phase_schedule',          'Phase schedule or calendar')
on conflict (kind) do nothing;

-- ─────────────────────────────────────────────────────────────────────────────
-- §2 Policy table
-- ─────────────────────────────────────────────────────────────────────────────
create table if not exists public.exam_evidence_requirements (
  id uuid primary key default gen_random_uuid(),
  management_mode text not null
    check (management_mode in ('core', 'light', 'index_only', 'archive')),
  exam_type text
    check (exam_type is null or exam_type in
      ('recruitment', 'entrance', 'certification', 'opportunity', 'other')),
  phase_kind text
    check (phase_kind is null or phase_kind in
      ('objective_written', 'descriptive_written', 'mixed_written',
       'interview', 'physical_test', 'medical', 'document_verification', 'other')),
  evidence_kind text not null references public.exam_evidence_kinds(kind),
  satisfied_by text not null default 'document_asset'
    check (satisfied_by in
      ('document_asset', 'source_registry', 'cycle_fields', 'phase_fields', 'external_link')),
  requirement_level text not null default 'required'
    check (requirement_level in ('required', 'recommended', 'not_applicable')),
  gate_effect text not null default 'block'
    check (gate_effect in ('block', 'warn', 'none')),
  scope text not null default 'phase'
    check (scope in ('exam', 'cycle', 'phase')),
  minimum_count integer not null default 1 check (minimum_count >= 0),
  minimum_distinct_years integer check (minimum_distinct_years is null or minimum_distinct_years >= 0),
  lookback_years integer check (lookback_years is null or lookback_years >= 0),
  requires_verified_source boolean not null default true,
  requires_human_review boolean not null default true,
  requires_extraction boolean not null default false,
  -- D05: validated condition codes only — never arbitrary executable expressions.
  condition_code text not null default 'always'
    check (condition_code in
      ('always', 'cycle_is_operational', 'cycle_dates_published', 'study_os_enabled',
       'pattern_details_exposed', 'corrigendum_known', 'objective_pyq_used_for_scoring',
       'application_tracking_enabled')),
  condition_params jsonb not null default '{}'::jsonb,
  priority integer not null default 100,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Deterministic identity for a base policy row (idempotent seed + override joins).
create unique index if not exists exam_evidence_requirements_identity_uidx
  on public.exam_evidence_requirements (
    management_mode,
    coalesce(exam_type, ''),
    coalesce(phase_kind, ''),
    evidence_kind,
    scope
  );

comment on table public.exam_evidence_requirements is
  'D05 §2 normalized evidence-requirement policy. Derived from management_mode + exam_type + '
  'phase_kind + scope, NOT hardcoded per exam slug.';

-- ─────────────────────────────────────────────────────────────────────────────
-- §3 Relational document evidence registration (+ trust lifecycle)
-- ─────────────────────────────────────────────────────────────────────────────
create table if not exists public.exam_document_evidence (
  id uuid primary key default gen_random_uuid(),
  document_asset_id uuid not null references public.document_assets(id) on delete cascade,
  exam_id uuid not null references public.exams(id) on delete cascade,
  exam_cycle_id uuid references public.exam_cycles(id) on delete cascade,
  exam_phase_id uuid references public.exam_phases(id) on delete cascade,
  -- D05 source-authority predicate: canonical source is public.source_registry (migration 002/022).
  -- PR-2 satisfies `requires_verified_source=true` from this FK using existing registry facts —
  -- at minimum is_active AND is_official_source AND NOT discovery_only — kept DISTINCT from the
  -- human trust_status lifecycle below (source authority != human review).
  source_registry_id uuid references public.source_registry(id) on delete set null,
  trust_status text not null default 'pending'
    check (trust_status in ('pending', 'verified', 'rejected', 'superseded')),
  superseded_by_id uuid references public.exam_document_evidence(id) on delete set null,
  reviewed_by uuid references auth.users(id) on delete set null,
  reviewed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists exam_document_evidence_asset_exam_uidx
  on public.exam_document_evidence (document_asset_id, exam_id);
create index if not exists exam_document_evidence_exam_idx
  on public.exam_document_evidence (exam_id);
create index if not exists exam_document_evidence_cycle_idx
  on public.exam_document_evidence (exam_cycle_id);
create index if not exists exam_document_evidence_phase_idx
  on public.exam_document_evidence (exam_phase_id);
create index if not exists exam_document_evidence_trust_idx
  on public.exam_document_evidence (exam_id, trust_status);

comment on table public.exam_document_evidence is
  'D05 §3 relational registration of a document_asset as exam-domain evidence, with a human '
  'trust lifecycle (pending/verified/rejected/superseded). Readiness joins on these relational '
  'IDs, not on document_assets.metadata JSON. Hierarchy (cycle/phase belong to exam) is enforced '
  'by trigger _d05_check_evidence_scope, since individual FKs do not imply scope consistency.';

-- ─────────────────────────────────────────────────────────────────────────────
-- §4 Evidence roles (one source may satisfy multiple requirement classes)
-- ─────────────────────────────────────────────────────────────────────────────
create table if not exists public.exam_document_evidence_roles (
  id uuid primary key default gen_random_uuid(),
  document_evidence_id uuid not null
    references public.exam_document_evidence(id) on delete cascade,
  evidence_kind text not null references public.exam_evidence_kinds(kind),
  exam_cycle_id uuid references public.exam_cycles(id) on delete cascade,
  exam_phase_id uuid references public.exam_phases(id) on delete cascade,
  created_at timestamptz not null default now()
);

create unique index if not exists exam_document_evidence_roles_uidx
  on public.exam_document_evidence_roles (
    document_evidence_id,
    evidence_kind,
    coalesce(exam_phase_id, '00000000-0000-0000-0000-000000000000'::uuid),
    coalesce(exam_cycle_id, '00000000-0000-0000-0000-000000000000'::uuid)
  );
create index if not exists exam_document_evidence_roles_kind_idx
  on public.exam_document_evidence_roles (evidence_kind);

comment on table public.exam_document_evidence_roles is
  'D05 §4 normalized evidence roles for a registered document. Role scope must be consistent with '
  'the parent evidence registration''s exam (enforced by trigger _d05_check_role_scope).';

-- ─────────────────────────────────────────────────────────────────────────────
-- §5 Narrow per-exam/cycle/phase overrides (deterministic identity)
-- ─────────────────────────────────────────────────────────────────────────────
create table if not exists public.exam_evidence_requirement_overrides (
  id uuid primary key default gen_random_uuid(),
  base_requirement_id uuid references public.exam_evidence_requirements(id) on delete cascade,
  exam_id uuid not null references public.exams(id) on delete cascade,
  exam_cycle_id uuid references public.exam_cycles(id) on delete cascade,
  exam_phase_id uuid references public.exam_phases(id) on delete cascade,
  evidence_kind text not null references public.exam_evidence_kinds(kind),
  requirement_level text
    check (requirement_level is null or requirement_level in ('required', 'recommended', 'not_applicable')),
  gate_effect text
    check (gate_effect is null or gate_effect in ('block', 'warn', 'none')),
  minimum_count integer check (minimum_count is null or minimum_count >= 0),
  minimum_distinct_years integer check (minimum_distinct_years is null or minimum_distinct_years >= 0),
  requires_verified_source boolean,
  requires_human_review boolean,
  requires_extraction boolean,
  condition_code text
    check (condition_code is null or condition_code in
      ('always', 'cycle_is_operational', 'cycle_dates_published', 'study_os_enabled',
       'pattern_details_exposed', 'corrigendum_known', 'objective_pyq_used_for_scoring',
       'application_tracking_enabled')),
  condition_params jsonb,
  reason text,
  created_by uuid references auth.users(id) on delete set null,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  expires_at timestamptz
);

-- Deterministic winner: at most one ACTIVE override per canonical key
-- (exam + cycle-scope + phase-scope + evidence_kind). PR-2 resolves precedence
-- phase > cycle > exam deterministically because each level has a single active row.
create unique index if not exists exam_evidence_requirement_overrides_active_uidx
  on public.exam_evidence_requirement_overrides (
    exam_id,
    coalesce(exam_cycle_id, '00000000-0000-0000-0000-000000000000'::uuid),
    coalesce(exam_phase_id, '00000000-0000-0000-0000-000000000000'::uuid),
    evidence_kind
  )
  where is_active;
create index if not exists exam_evidence_requirement_overrides_exam_idx
  on public.exam_evidence_requirement_overrides (exam_id);

comment on table public.exam_evidence_requirement_overrides is
  'D05 §5 narrow overrides. At most one ACTIVE row per (exam, cycle, phase, evidence_kind) — '
  'see partial unique index. Precedence (PR-2): phase > cycle > exam > policy defaults. '
  'base_requirement_id (if set) must share evidence_kind (enforced by trigger _d05_check_override).';

-- ─────────────────────────────────────────────────────────────────────────────
-- Hierarchy / consistency triggers (P1 — FKs alone do not imply scope consistency)
-- ─────────────────────────────────────────────────────────────────────────────
create or replace function public._d05_check_evidence_scope() returns trigger
language plpgsql as $fn$
declare v_target_exam uuid;
begin
  if new.exam_cycle_id is not null
     and not exists (select 1 from public.exam_cycles c
                     where c.id = new.exam_cycle_id and c.exam_id = new.exam_id) then
    raise exception 'exam_document_evidence: cycle % does not belong to exam %',
      new.exam_cycle_id, new.exam_id;
  end if;
  if new.exam_phase_id is not null
     and not exists (select 1 from public.exam_phases p
                     where p.id = new.exam_phase_id and p.exam_id = new.exam_id
                       and (new.exam_cycle_id is null or p.exam_cycle_id = new.exam_cycle_id)) then
    raise exception 'exam_document_evidence: phase % not in exam %/cycle %',
      new.exam_phase_id, new.exam_id, new.exam_cycle_id;
  end if;
  -- Supersession consistency: a superseded link and the 'superseded' status are bidirectional;
  -- the target must exist, differ from self, and belong to the same exam.
  if new.superseded_by_id is not null then
    if new.superseded_by_id = new.id then
      raise exception 'exam_document_evidence: superseded_by_id cannot reference the row itself';
    end if;
    if new.trust_status <> 'superseded' then
      raise exception 'exam_document_evidence: superseded_by_id set but trust_status is % (must be superseded)',
        new.trust_status;
    end if;
    select exam_id into v_target_exam from public.exam_document_evidence e
      where e.id = new.superseded_by_id;
    if v_target_exam is null then
      raise exception 'exam_document_evidence: superseded_by_id % not found', new.superseded_by_id;
    end if;
    if v_target_exam <> new.exam_id then
      raise exception 'exam_document_evidence: superseded_by_id % belongs to a different exam', new.superseded_by_id;
    end if;
  elsif new.trust_status = 'superseded' then
    raise exception 'exam_document_evidence: trust_status=superseded requires a superseded_by_id target';
  end if;
  return new;
end;
$fn$;

create or replace function public._d05_check_role_scope() returns trigger
language plpgsql as $fn$
declare
  v_exam uuid;
  v_pcycle uuid;
  v_pphase uuid;
  v_eff_cycle uuid;
begin
  select exam_id, exam_cycle_id, exam_phase_id into v_exam, v_pcycle, v_pphase
    from public.exam_document_evidence e where e.id = new.document_evidence_id;
  if v_exam is null then
    raise exception 'evidence role: parent evidence % not found', new.document_evidence_id;
  end if;
  -- A role may inherit (leave null) or narrow an exam-level parent, but must not escape or
  -- conflict with a cycle/phase-scoped parent registration.
  if v_pcycle is not null and new.exam_cycle_id is not null and new.exam_cycle_id <> v_pcycle then
    raise exception 'evidence role: cycle % conflicts with cycle-scoped parent cycle %',
      new.exam_cycle_id, v_pcycle;
  end if;
  if v_pphase is not null and new.exam_phase_id is not null and new.exam_phase_id <> v_pphase then
    raise exception 'evidence role: phase % conflicts with phase-scoped parent phase %',
      new.exam_phase_id, v_pphase;
  end if;
  -- Effective cycle is the role's own cycle if set, else the parent's.
  v_eff_cycle := coalesce(new.exam_cycle_id, v_pcycle);
  if new.exam_cycle_id is not null
     and not exists (select 1 from public.exam_cycles c
                     where c.id = new.exam_cycle_id and c.exam_id = v_exam) then
    raise exception 'evidence role: cycle % not in parent exam %', new.exam_cycle_id, v_exam;
  end if;
  if new.exam_phase_id is not null
     and not exists (select 1 from public.exam_phases p
                     where p.id = new.exam_phase_id and p.exam_id = v_exam
                       and (v_eff_cycle is null or p.exam_cycle_id = v_eff_cycle)) then
    raise exception 'evidence role: phase % not in parent exam %/effective cycle %',
      new.exam_phase_id, v_exam, v_eff_cycle;
  end if;
  return new;
end;
$fn$;

create or replace function public._d05_check_override() returns trigger
language plpgsql as $fn$
declare v_base_kind text;
begin
  if new.exam_cycle_id is not null
     and not exists (select 1 from public.exam_cycles c
                     where c.id = new.exam_cycle_id and c.exam_id = new.exam_id) then
    raise exception 'override: cycle % not in exam %', new.exam_cycle_id, new.exam_id;
  end if;
  if new.exam_phase_id is not null
     and not exists (select 1 from public.exam_phases p
                     where p.id = new.exam_phase_id and p.exam_id = new.exam_id
                       and (new.exam_cycle_id is null or p.exam_cycle_id = new.exam_cycle_id)) then
    raise exception 'override: phase % not in exam %/cycle %',
      new.exam_phase_id, new.exam_id, new.exam_cycle_id;
  end if;
  if new.base_requirement_id is not null then
    select evidence_kind into v_base_kind from public.exam_evidence_requirements r
      where r.id = new.base_requirement_id;
    if v_base_kind is null then
      raise exception 'override: base_requirement % not found', new.base_requirement_id;
    end if;
    if v_base_kind <> new.evidence_kind then
      raise exception 'override: evidence_kind % != base_requirement evidence_kind %',
        new.evidence_kind, v_base_kind;
    end if;
  end if;
  return new;
end;
$fn$;

drop trigger if exists trg_d05_check_evidence_scope on public.exam_document_evidence;
create trigger trg_d05_check_evidence_scope
  before insert or update on public.exam_document_evidence
  for each row execute function public._d05_check_evidence_scope();

drop trigger if exists trg_d05_check_role_scope on public.exam_document_evidence_roles;
create trigger trg_d05_check_role_scope
  before insert or update on public.exam_document_evidence_roles
  for each row execute function public._d05_check_role_scope();

drop trigger if exists trg_d05_check_override on public.exam_evidence_requirement_overrides;
create trigger trg_d05_check_override
  before insert or update on public.exam_evidence_requirement_overrides
  for each row execute function public._d05_check_override();

-- ─────────────────────────────────────────────────────────────────────────────
-- Seed: the PHASE-SCOPED subset of the D05 matrix (D05 "Phase-specific rules") only.
-- The exam-scoped and cycle-scoped requirements from the D05 "Mandatory evidence matrix"
-- (verified official source, primary_cycle_document per cycle, conditional corrigendum,
-- phase_schedule, application_instructions) are NOT seeded here — they land with the
-- PR-2 evaluator migration, and Step 9 stays fail-closed until those policy rows exist.
-- PR-2 is therefore the "phase-completeness" evaluator over the full seeded set, not a
-- "full D05 evaluator" over a partial policy.
--
-- core and light are seeded SEPARATELY because their approved requirement levels differ:
--   core  written: syllabus/pattern/PYQ required+block; answer_key required when objective
--                  PYQ used for scoring; non-written phase rules required+block.
--   light written: syllabus required when Study-OS exposed; pattern required when pattern
--                  details exposed; PYQ recommended (warn, NOT a blocker); answer_key required
--                  when objective PYQ used for scoring; non-written phase rules recommended+warn.
-- index_only/archive carry no phase-activation evidence (they don't enter planner activation).
-- Idempotent via ON CONFLICT on the identity index.
-- ─────────────────────────────────────────────────────────────────────────────
insert into public.exam_evidence_requirements
  (management_mode, phase_kind, evidence_kind, satisfied_by, requirement_level, gate_effect,
   scope, minimum_count, requires_verified_source, requires_human_review, requires_extraction,
   condition_code, priority)
values
  -- ── core ─────────────────────────────────────────────────────────────────
  ('core','objective_written','syllabus',    'document_asset','required','block','phase',1,true,true,true, 'always',100),
  ('core','objective_written','exam_pattern', 'document_asset','required','block','phase',1,true,true,true, 'always',100),
  ('core','objective_written','pyq_paper',    'source_registry','required','block','phase',1,true,false,false,'always',100),
  ('core','objective_written','answer_key',   'document_asset','required','block','phase',1,true,true,true, 'objective_pyq_used_for_scoring',100),
  ('core','descriptive_written','syllabus',   'document_asset','required','block','phase',1,true,true,true, 'always',100),
  ('core','descriptive_written','exam_pattern','document_asset','required','block','phase',1,true,true,true, 'always',100),
  ('core','descriptive_written','pyq_paper',  'source_registry','required','block','phase',1,true,false,false,'always',100),
  ('core','mixed_written','syllabus',         'document_asset','required','block','phase',1,true,true,true, 'always',100),
  ('core','mixed_written','exam_pattern',     'document_asset','required','block','phase',1,true,true,true, 'always',100),
  ('core','mixed_written','pyq_paper',        'source_registry','required','block','phase',1,true,false,false,'always',100),
  ('core','mixed_written','answer_key',       'document_asset','required','block','phase',1,true,true,true, 'objective_pyq_used_for_scoring',100),
  ('core','interview','phase_rules',             'document_asset','required','block','phase',1,true,true,false,'always',100),
  ('core','physical_test','phase_rules',         'document_asset','required','block','phase',1,true,true,false,'always',100),
  ('core','medical','phase_rules',               'document_asset','required','block','phase',1,true,true,false,'always',100),
  ('core','document_verification','phase_rules', 'document_asset','required','block','phase',1,true,true,false,'always',100),
  -- ── light ────────────────────────────────────────────────────────────────
  ('light','objective_written','syllabus',    'document_asset','required','block','phase',1,true,true,true, 'study_os_enabled',100),
  ('light','objective_written','exam_pattern', 'document_asset','required','block','phase',1,true,true,true, 'pattern_details_exposed',100),
  ('light','objective_written','pyq_paper',    'source_registry','recommended','warn','phase',1,true,false,false,'always',100),
  ('light','objective_written','answer_key',   'document_asset','required','block','phase',1,true,true,true, 'objective_pyq_used_for_scoring',100),
  ('light','descriptive_written','syllabus',   'document_asset','required','block','phase',1,true,true,true, 'study_os_enabled',100),
  ('light','descriptive_written','exam_pattern','document_asset','required','block','phase',1,true,true,true, 'pattern_details_exposed',100),
  ('light','descriptive_written','pyq_paper',  'source_registry','recommended','warn','phase',1,true,false,false,'always',100),
  ('light','mixed_written','syllabus',         'document_asset','required','block','phase',1,true,true,true, 'study_os_enabled',100),
  ('light','mixed_written','exam_pattern',     'document_asset','required','block','phase',1,true,true,true, 'pattern_details_exposed',100),
  ('light','mixed_written','pyq_paper',        'source_registry','recommended','warn','phase',1,true,false,false,'always',100),
  ('light','mixed_written','answer_key',       'document_asset','required','block','phase',1,true,true,true, 'objective_pyq_used_for_scoring',100),
  ('light','interview','phase_rules',             'document_asset','recommended','warn','phase',1,true,false,false,'always',100),
  ('light','physical_test','phase_rules',         'document_asset','recommended','warn','phase',1,true,false,false,'always',100),
  ('light','medical','phase_rules',               'document_asset','recommended','warn','phase',1,true,false,false,'always',100),
  ('light','document_verification','phase_rules', 'document_asset','recommended','warn','phase',1,true,false,false,'always',100)
on conflict (management_mode, coalesce(exam_type, ''), coalesce(phase_kind, ''), evidence_kind, scope)
do nothing;

-- Seed assertions (fail the migration if the approved matrix is not what landed).
do $$
declare
  v_level text;
  v_gate text;
  v_cond text;
begin
  -- light written PYQ must be recommended/warn (NOT a blocker) for all three written kinds.
  for v_cond in select unnest(array['objective_written','descriptive_written','mixed_written']) loop
    select requirement_level, gate_effect into v_level, v_gate
      from public.exam_evidence_requirements
      where management_mode='light' and phase_kind=v_cond and evidence_kind='pyq_paper' and scope='phase';
    if v_level is distinct from 'recommended' or v_gate is distinct from 'warn' then
      raise exception 'seed assert failed: light/%/pyq_paper must be recommended/warn (got %/%)',
        v_cond, v_level, v_gate;
    end if;
  end loop;
  -- light written pattern is conditional on pattern exposure.
  select condition_code into v_cond from public.exam_evidence_requirements
    where management_mode='light' and phase_kind='objective_written' and evidence_kind='exam_pattern' and scope='phase';
  if v_cond is distinct from 'pattern_details_exposed' then
    raise exception 'seed assert failed: light objective exam_pattern condition must be pattern_details_exposed (got %)', v_cond;
  end if;
  -- answer_key stays conditional on objective PYQ scoring (core + light).
  select condition_code into v_cond from public.exam_evidence_requirements
    where management_mode='light' and phase_kind='mixed_written' and evidence_kind='answer_key' and scope='phase';
  if v_cond is distinct from 'objective_pyq_used_for_scoring' then
    raise exception 'seed assert failed: light mixed answer_key condition must be objective_pyq_used_for_scoring (got %)', v_cond;
  end if;
  -- core written PYQ must be required/block.
  select requirement_level, gate_effect into v_level, v_gate from public.exam_evidence_requirements
    where management_mode='core' and phase_kind='objective_written' and evidence_kind='pyq_paper' and scope='phase';
  if v_level is distinct from 'required' or v_gate is distinct from 'block' then
    raise exception 'seed assert failed: core objective pyq_paper must be required/block (got %/%)', v_level, v_gate;
  end if;
  -- descriptive_written must NOT seed an answer_key requirement (core or light).
  if exists (select 1 from public.exam_evidence_requirements
             where phase_kind='descriptive_written' and evidence_kind='answer_key') then
    raise exception 'seed assert failed: descriptive_written must not require answer_key';
  end if;
end $$;

-- ─────────────────────────────────────────────────────────────────────────────
-- RLS: enabled + service-role mediated. No authenticated policy (deny by default);
-- privileges revoked from public/anon/authenticated and granted to service_role.
-- ─────────────────────────────────────────────────────────────────────────────
do $$
declare t text;
begin
  foreach t in array array[
    'exam_evidence_kinds',
    'exam_evidence_requirements',
    'exam_document_evidence',
    'exam_document_evidence_roles',
    'exam_evidence_requirement_overrides'
  ]
  loop
    execute format('alter table public.%I enable row level security', t);
    execute format('revoke all on public.%I from public', t);
    execute format('revoke all on public.%I from anon', t);
    execute format('revoke all on public.%I from authenticated', t);
    execute format('grant select, insert, update, delete on public.%I to service_role', t);
  end loop;
end $$;

notify pgrst, 'reload schema';
