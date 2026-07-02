-- 211_d05_evidence_policy_foundation.sql
--
-- D05 evidence-policy foundation (PR-1 of the D12-v1 "full D05 engine" program).
-- SCHEMA ONLY — no readiness/planner behavior changes here. The document_policy
-- evaluator that consumes these tables and the cycle_readiness Step 9 wiring land
-- in a follow-up PR; planner enforcement + backfill in a further PR.
--
-- Implements the normalized evidence model from D05 §2–5:
--   §2 exam_evidence_requirements            — the policy table (seeded below)
--   §3 exam_document_evidence                — relational document registration + trust lifecycle
--   §4 exam_document_evidence_roles          — one source document may satisfy multiple roles
--   §5 exam_evidence_requirement_overrides   — narrow per-exam/cycle/phase exceptions
--
-- All four tables get RLS (admin-all; the backend reads via service role which
-- bypasses RLS). Migrations are immutable once merged.

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
  evidence_kind text not null,
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

-- Deterministic identity for a base policy row (used for idempotent seed + override joins).
create unique index if not exists exam_evidence_requirements_identity_uidx
  on public.exam_evidence_requirements (
    management_mode,
    coalesce(exam_type, ''),
    coalesce(phase_kind, ''),
    evidence_kind,
    scope
  );

comment on table public.exam_evidence_requirements is
  'D05 §2 normalized evidence-requirement policy. Requirements are derived from '
  'management_mode + exam_type + phase_kind + scope, NOT hardcoded per exam slug.';

-- ─────────────────────────────────────────────────────────────────────────────
-- §3 Relational document evidence registration (+ trust lifecycle)
-- ─────────────────────────────────────────────────────────────────────────────
create table if not exists public.exam_document_evidence (
  id uuid primary key default gen_random_uuid(),
  document_asset_id uuid not null references public.document_assets(id) on delete cascade,
  exam_id uuid not null references public.exams(id) on delete cascade,
  exam_cycle_id uuid references public.exam_cycles(id) on delete cascade,
  exam_phase_id uuid references public.exam_phases(id) on delete cascade,
  source_registry_id uuid,
  trust_status text not null default 'pending'
    check (trust_status in ('pending', 'verified', 'rejected', 'superseded')),
  superseded_by_id uuid references public.exam_document_evidence(id) on delete set null,
  reviewed_by uuid,
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
  'trust lifecycle (pending/verified/rejected/superseded). Readiness must join on these '
  'relational IDs rather than treating document_assets.metadata JSON as the canonical policy join.';

-- ─────────────────────────────────────────────────────────────────────────────
-- §4 Evidence roles (one source may satisfy multiple requirement classes)
-- ─────────────────────────────────────────────────────────────────────────────
create table if not exists public.exam_document_evidence_roles (
  id uuid primary key default gen_random_uuid(),
  document_evidence_id uuid not null
    references public.exam_document_evidence(id) on delete cascade,
  evidence_kind text not null,
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
  'D05 §4 normalized evidence roles for a registered document. Preserve display subtypes '
  '(information_bulletin/prospectus/etc.) elsewhere; here evidence_kind is the normalized '
  'policy role (primary_cycle_document, syllabus, exam_pattern, answer_key, ...).';

-- ─────────────────────────────────────────────────────────────────────────────
-- §5 Narrow per-exam/cycle/phase overrides
-- ─────────────────────────────────────────────────────────────────────────────
create table if not exists public.exam_evidence_requirement_overrides (
  id uuid primary key default gen_random_uuid(),
  base_requirement_id uuid references public.exam_evidence_requirements(id) on delete cascade,
  exam_id uuid not null references public.exams(id) on delete cascade,
  exam_cycle_id uuid references public.exam_cycles(id) on delete cascade,
  exam_phase_id uuid references public.exam_phases(id) on delete cascade,
  evidence_kind text not null,
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
  created_by uuid,
  created_at timestamptz not null default now(),
  expires_at timestamptz
);

create index if not exists exam_evidence_requirement_overrides_exam_idx
  on public.exam_evidence_requirement_overrides (exam_id);
create index if not exists exam_evidence_requirement_overrides_scope_idx
  on public.exam_evidence_requirement_overrides (exam_id, exam_cycle_id, exam_phase_id, evidence_kind);

comment on table public.exam_evidence_requirement_overrides is
  'D05 §5 narrow overrides. Precedence (most specific wins): phase > cycle > exam override > '
  'exact management_mode+exam_type+phase_kind > management_mode+exam_type > management_mode+phase_kind '
  '> management_mode default.';

-- ─────────────────────────────────────────────────────────────────────────────
-- Seed: per-management-mode × phase_kind phase-scoped evidence requirements (D05
-- "Phase-specific rules"). Only planner-activating modes (core, light) carry
-- phase evidence; index_only/archive do not enter activation. `light` rows mirror
-- `core` — light's "only when Study-OS exposed" gate is applied at the Step 9 mode
-- layer (planner_activation_enabled), not per-requirement, so the evidence set is
-- identical once light is exposed. Idempotent via ON CONFLICT on the identity index.
-- ─────────────────────────────────────────────────────────────────────────────
insert into public.exam_evidence_requirements
  (management_mode, phase_kind, evidence_kind, satisfied_by, requirement_level,
   gate_effect, scope, minimum_count, requires_verified_source, requires_human_review,
   requires_extraction, condition_code, priority)
select m.mode, b.phase_kind, b.evidence_kind, b.satisfied_by, 'required',
       'block', 'phase', b.minimum_count, true, true, b.requires_extraction, b.condition_code, 100
from (values
  -- objective_written
  ('objective_written', 'syllabus',     'document_asset', 1, true,  'always'),
  ('objective_written', 'exam_pattern',  'document_asset', 1, true,  'always'),
  ('objective_written', 'pyq_paper',     'source_registry', 1, false, 'always'),
  ('objective_written', 'answer_key',    'document_asset', 1, true,  'objective_pyq_used_for_scoring'),
  -- descriptive_written (answer_key not applicable)
  ('descriptive_written', 'syllabus',    'document_asset', 1, true,  'always'),
  ('descriptive_written', 'exam_pattern', 'document_asset', 1, true,  'always'),
  ('descriptive_written', 'pyq_paper',    'source_registry', 1, false, 'always'),
  -- mixed_written
  ('mixed_written', 'syllabus',          'document_asset', 1, true,  'always'),
  ('mixed_written', 'exam_pattern',       'document_asset', 1, true,  'always'),
  ('mixed_written', 'pyq_paper',          'source_registry', 1, false, 'always'),
  ('mixed_written', 'answer_key',         'document_asset', 1, true,  'objective_pyq_used_for_scoring'),
  -- non-written phases: official phase rules / standards
  ('interview',             'phase_rules', 'document_asset', 1, false, 'always'),
  ('physical_test',         'phase_rules', 'document_asset', 1, false, 'always'),
  ('medical',               'phase_rules', 'document_asset', 1, false, 'always'),
  ('document_verification', 'phase_rules', 'document_asset', 1, false, 'always')
) as b(phase_kind, evidence_kind, satisfied_by, minimum_count, requires_extraction, condition_code)
cross join (values ('core'), ('light')) as m(mode)
on conflict (management_mode, coalesce(exam_type, ''), coalesce(phase_kind, ''), evidence_kind, scope)
do nothing;

-- ─────────────────────────────────────────────────────────────────────────────
-- RLS: enable + admin-all (backend reads via service role, which bypasses RLS).
-- ─────────────────────────────────────────────────────────────────────────────
alter table public.exam_evidence_requirements enable row level security;
alter table public.exam_document_evidence enable row level security;
alter table public.exam_document_evidence_roles enable row level security;
alter table public.exam_evidence_requirement_overrides enable row level security;

do $$
declare
  t text;
  policy_name text;
begin
  foreach t in array array[
    'exam_evidence_requirements',
    'exam_document_evidence',
    'exam_document_evidence_roles',
    'exam_evidence_requirement_overrides'
  ]
  loop
    policy_name := t || '_admin_all';
    if not exists (
      select 1 from pg_policies
      where schemaname = 'public' and tablename = t and policyname = policy_name
    ) then
      execute format(
        'create policy %I on public.%I for all to authenticated using (exists (select 1 from public.profiles p where p.id = auth.uid() and p.is_admin = true)) with check (exists (select 1 from public.profiles p where p.id = auth.uid() and p.is_admin = true))',
        policy_name, t
      );
    end if;
  end loop;
end $$;

notify pgrst, 'reload schema';
