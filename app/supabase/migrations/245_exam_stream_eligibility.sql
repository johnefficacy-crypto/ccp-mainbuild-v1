-- 245_exam_stream_eligibility.sql
--
-- Lane R §4 — baseline-vs-cycle eligibility, stream dimension. Contract:
-- docs/architecture/financial-regulatory-development-family.md §4.
--
-- Two clearly separated scopes (the Compass "provenance bands"):
--   * BASELINE (stable) eligibility  -> public.exam_eligibility_rules (110).
--     Extended here with an optional stream_id for stream-STABLE facts
--     (e.g. SEBI Legal always needs LLB; IRDAI Law always LLB 60%) and new
--     rule_types. Evergreen — NO cycle column.
--   * CYCLE / notification-specific eligibility -> new
--     public.exam_cycle_stream_eligibility, keyed on (exam_cycle_id, stream_id).
--     Percentages / experience / professional-qual cut-offs that change per
--     advertisement live here, NEVER in the baseline rows.
--
-- Behaviour-neutral to the current evaluator (app/exam_eligibility/evaluator.py):
-- it reads only exam_id + scope + the six original rule_types and ignores
-- unknown types and the new stream_id column. Stream-aware evaluation (picking
-- stream-specific rules against a user's target stream) + the new rule_type
-- branches are a deliberate FOLLOW-UP PR with its own eligibility regression —
-- this migration only lays the schema so nothing user-facing changes yet.
--
-- The new rule_types (contract §4): discipline, min_percentage, certification,
-- qualification_combination, stream_availability. Category `scope` is NOT
-- overloaded — the stream axis is a separate column.

-- ─── 1. exam_eligibility_rules: optional stream dimension + rule_types ────
alter table public.exam_eligibility_rules
  add column if not exists stream_id uuid references public.exam_streams(id) on delete restrict;

create index if not exists idx_eer_stream
  on public.exam_eligibility_rules(stream_id);

-- Extend the rule_type CHECK (inline/auto-named in 110). Drop by definition
-- lookup so the migration is name-agnostic across environments.
do $$
declare
  cname text;
begin
  select conname into cname
  from pg_constraint
  where conrelid = 'public.exam_eligibility_rules'::regclass
    and contype = 'c'
    and pg_get_constraintdef(oid) ilike '%rule_type%';
  if cname is not null then
    execute format('alter table public.exam_eligibility_rules drop constraint %I', cname);
  end if;
end $$;

alter table public.exam_eligibility_rules
  add constraint exam_eligibility_rules_rule_type_check
  check (rule_type in (
    'age_min', 'age_max', 'education_min_level', 'nationality', 'gender', 'attempts_max',
    'discipline', 'min_percentage', 'certification', 'qualification_combination', 'stream_availability'
  ));

-- Replace unique(exam_id, scope, rule_type) with a stream-aware key. NULLS NOT
-- DISTINCT (PG15+, as 219/242) lets a common rule (stream_id NULL) and one rule
-- per stream coexist for the same (scope, rule_type) without a sentinel.
do $$
declare
  cname text;
begin
  select conname into cname
  from pg_constraint
  where conrelid = 'public.exam_eligibility_rules'::regclass
    and contype = 'u'
    and pg_get_constraintdef(oid) ilike '%(exam_id, scope, rule_type)%';
  if cname is not null then
    execute format('alter table public.exam_eligibility_rules drop constraint %I', cname);
  end if;
end $$;

create unique index if not exists exam_eligibility_rules_exam_stream_scope_type_uidx
  on public.exam_eligibility_rules(exam_id, stream_id, scope, rule_type)
  nulls not distinct;

-- Cross-parent integrity: a stream-scoped baseline rule's stream must belong to
-- the rule's exam (FKs alone allow a stream from another exam). Fail-closed,
-- INSERT + UPDATE, FOR SHARE parent read (242 posture).
create or replace function public._exam_eligibility_rules_check_stream() returns trigger
language plpgsql as $fn$
declare
  v_stream_exam uuid;
begin
  if new.stream_id is not null then
    select exam_id into v_stream_exam from public.exam_streams where id = new.stream_id for share;
    if v_stream_exam is distinct from new.exam_id then
      raise exception 'exam_eligibility_rules: stream % (exam %) does not belong to rule exam %',
        new.stream_id, v_stream_exam, new.exam_id using errcode = 'P0422';
    end if;
  end if;
  return new;
end;
$fn$;

drop trigger if exists trg_exam_eligibility_rules_check_stream on public.exam_eligibility_rules;
create trigger trg_exam_eligibility_rules_check_stream
  before insert or update on public.exam_eligibility_rules
  for each row execute function public._exam_eligibility_rules_check_stream();

-- ─── 2. Cycle / notification-specific eligibility ────────────────────────
-- Keyed on (exam_cycle_id, stream_id). The composite FK to exam_cycle_streams
-- guarantees the pair exists AND (via that table's own cross-exam trigger from
-- 242) that the cycle and stream share one exam — so cycle eligibility can
-- never contradict its parents.
create table if not exists public.exam_cycle_stream_eligibility (
  id uuid primary key default gen_random_uuid(),
  exam_cycle_id uuid not null,
  stream_id uuid not null,
  scope text not null default 'all'
    check (scope in ('all','general','obc','sc','st','ews','pwd','ex_serviceman','women')),
  rule_type text not null
    check (rule_type in (
      'age_min','age_max','education_min_level','nationality','gender','attempts_max',
      'discipline','min_percentage','certification','qualification_combination','stream_availability'
    )),
  value_num numeric,
  value_text text,
  is_knockout boolean not null default true,
  source_url text,
  source_notes text,
  reviewer_status text not null default 'draft'
    check (reviewer_status in ('draft','verified','archived')),
  verified_by uuid references auth.users(id) on delete set null,
  verified_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint exam_cycle_stream_eligibility_pair_fkey
    foreign key (exam_cycle_id, stream_id)
    references public.exam_cycle_streams(exam_cycle_id, stream_id) on delete cascade,
  unique (exam_cycle_id, stream_id, scope, rule_type)
);

create index if not exists idx_ecse_cycle_stream
  on public.exam_cycle_stream_eligibility(exam_cycle_id, stream_id);
create index if not exists idx_ecse_status
  on public.exam_cycle_stream_eligibility(reviewer_status);

-- Service-role only, mirroring exam_eligibility_rules (110): RLS enabled with
-- no policies. The evaluator/admin tool reads/writes via the service role.
alter table public.exam_cycle_stream_eligibility enable row level security;

drop trigger if exists exam_cycle_stream_eligibility_updated_at on public.exam_cycle_stream_eligibility;
create trigger exam_cycle_stream_eligibility_updated_at
  before update on public.exam_cycle_stream_eligibility
  for each row execute function public.tg_set_updated_at();

notify pgrst, 'reload schema';
