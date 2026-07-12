-- 248_exam_stream_eligibility.sql
--
-- Lane R §4 — baseline-vs-cycle eligibility, stream dimension + full value
-- model. Contract: docs/architecture/financial-regulatory-development-family.md §4.
-- Reworked per the PR #967 checkpost.
--
-- Two clearly separated scopes (the Compass "provenance bands"):
--   * BASELINE (stable) -> public.exam_eligibility_rules (110). Optional
--     stream_id for stream-STABLE facts. Evergreen — no cycle column.
--   * CYCLE / notification-specific -> public.exam_cycle_stream_eligibility,
--     keyed on (exam_cycle_id, stream_id). Percentages / experience / cut-off
--     dates that change per advertisement live here, never in baseline rows.
--
-- Value model (checkpost P0): rule_types now include discipline, min_percentage,
-- certification, qualification_combination, stream_availability AND
-- experience_min_years. Age rules on the cycle table carry cutoff_date_basis /
-- cutoff_date (the date age is measured on). qualification_combination is
-- machine-evaluable via a structured value_json:
--     {"op":"and"|"or","clauses":[<clause|group>, ...]}
--   clause = {"rule_type":"discipline"|"min_percentage"|"certification"
--                          |"experience_min_years", "value_text":.. | "value_num":..}
-- A CHECK requires value_json for qualification_combination rows; deeper
-- structural validation is enforced by the evaluator wiring (follow-up).
--
-- Runtime safety (checkpost P0): the current exam-wide evaluator is made
-- leak-proof in the same PR — app/exam_eligibility/evaluator.py now drops
-- stream-scoped rows (stream_id IS NOT NULL) before evaluation, and
-- app/api/admin_exam_eligibility.py is the audited writer for the new
-- rule_types / stream_id / value_json.

-- ─── 1. exam_eligibility_rules: stream dimension + rule_types + value_json ─
alter table public.exam_eligibility_rules
  add column if not exists stream_id uuid references public.exam_streams(id) on delete restrict;
alter table public.exam_eligibility_rules
  add column if not exists value_json jsonb;

create index if not exists idx_eer_stream
  on public.exam_eligibility_rules(stream_id);

-- Match the ENUM check specifically (`rule_type in (...)`) — NOT the
-- qualification_combination check, whose body also contains "rule_type".
do $$
declare cname text;
begin
  select conname into cname from pg_constraint
  where conrelid = 'public.exam_eligibility_rules'::regclass and contype = 'c'
    and pg_get_constraintdef(oid) ilike '%rule_type in (%';
  if cname is not null then
    execute format('alter table public.exam_eligibility_rules drop constraint %I', cname);
  end if;
end $$;

-- experience_min_years is NOT a baseline rule_type — experience is cycle /
-- recruitment-specific truth (§4), so it lives only on exam_cycle_stream_eligibility.
alter table public.exam_eligibility_rules
  drop constraint if exists exam_eligibility_rules_rule_type_check;
alter table public.exam_eligibility_rules
  add constraint exam_eligibility_rules_rule_type_check
  check (rule_type in (
    'age_min', 'age_max', 'education_min_level', 'nationality', 'gender', 'attempts_max',
    'discipline', 'min_percentage', 'certification', 'qualification_combination',
    'stream_availability'
  ));

-- Structural validator for qualification_combination value_json. Grammar:
--   node   = group | clause
--   group  = {"op":"and"|"or", "clauses":[node, ...]}   (clauses non-empty)
--   clause = {"rule_type":<atomic>, "value_text":<str> | "value_num":<num>}
--   atomic text  : discipline | certification | education_min_level | nationality
--   atomic number: min_percentage | experience_min_years
-- Top-level value_json must be a group. Nesting is supported.
create or replace function public.is_valid_qualification_combination(j jsonb)
returns boolean language plpgsql immutable as $fn$
declare el jsonb; rt text;
begin
  if j is null or jsonb_typeof(j) <> 'object' then return false; end if;
  if j ? 'op' then
    if (j->>'op') not in ('and','or') then return false; end if;
    -- `j ? 'clauses'` guards the missing-key case: jsonb_typeof(NULL) is NULL,
    -- so `NULL <> 'array'` would be NULL (not TRUE) and slip through.
    if not (j ? 'clauses')
       or jsonb_typeof(j->'clauses') <> 'array'
       or jsonb_array_length(j->'clauses') = 0 then
      return false;
    end if;
    for el in select value from jsonb_array_elements(j->'clauses') loop
      if not public.is_valid_qualification_combination(el) then return false; end if;
    end loop;
    return true;
  end if;
  rt := j->>'rule_type';
  if rt in ('min_percentage','experience_min_years') then
    return (j ? 'value_num') and jsonb_typeof(j->'value_num') = 'number';
  elsif rt in ('discipline','certification','education_min_level','nationality') then
    return (j ? 'value_text') and jsonb_typeof(j->'value_text') = 'string';
  else
    return false;
  end if;
end;
$fn$;

alter table public.exam_eligibility_rules
  drop constraint if exists exam_eligibility_rules_qual_combo_json_check;
alter table public.exam_eligibility_rules
  add constraint exam_eligibility_rules_qual_combo_json_check
  check (rule_type <> 'qualification_combination'
         or public.is_valid_qualification_combination(value_json));

-- Fail-closed (checkpost P0): a rule_type the evaluator does not yet interpret
-- cannot be promoted to reviewer_status='verified' — otherwise a verified
-- knockout rule would be silently ignored and the aspirant told "eligible".
-- Only the six branches implemented in evaluate_exam_for_user() may verify;
-- the new rule_types stay draft until stream-aware/typed evaluation lands (a
-- follow-up migration relaxes this CHECK when those branches ship).
alter table public.exam_eligibility_rules
  drop constraint if exists exam_eligibility_rules_verified_supported_check;
alter table public.exam_eligibility_rules
  add constraint exam_eligibility_rules_verified_supported_check
  check (reviewer_status <> 'verified' or rule_type in (
    'age_min', 'age_max', 'education_min_level', 'nationality', 'gender', 'attempts_max'
  ));

-- Stream-aware uniqueness (NULLS NOT DISTINCT), replacing the 110 key.
do $$
declare cname text;
begin
  select conname into cname from pg_constraint
  where conrelid = 'public.exam_eligibility_rules'::regclass and contype = 'u'
    and pg_get_constraintdef(oid) ilike '%(exam_id, scope, rule_type)%';
  if cname is not null then
    execute format('alter table public.exam_eligibility_rules drop constraint %I', cname);
  end if;
end $$;

create unique index if not exists exam_eligibility_rules_exam_stream_scope_type_uidx
  on public.exam_eligibility_rules(exam_id, stream_id, scope, rule_type)
  nulls not distinct;

-- Cross-parent integrity: a stream-scoped baseline rule's stream must belong to
-- the rule's exam. Fail-closed, INSERT + UPDATE, FOR SHARE (242 posture).
create or replace function public._exam_eligibility_rules_check_stream() returns trigger
language plpgsql as $fn$
declare v_stream_exam uuid;
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

-- ─── 2. Parent-side guard: include baseline rules in the stream-move guard ──
-- 242's _exam_streams_guard_exam_move() checked cycle-streams/phases/sections/
-- coverage but NOT exam_eligibility_rules, so a stream referenced only by a
-- baseline rule could be reassigned to another exam. Replace the function body
-- to also block that (the 242 trigger stays bound to it).
create or replace function public._exam_streams_guard_exam_move() returns trigger
language plpgsql as $fn$
begin
  if new.exam_id is distinct from old.exam_id and exists (
      select 1 from public.exam_cycle_streams cs where cs.stream_id = old.id
      union all select 1 from public.exam_phases p where p.stream_id = old.id
      union all select 1 from public.exam_phase_sections s where s.stream_id = old.id
      union all select 1 from public.exam_topic_coverage c where c.stream_id = old.id
      union all select 1 from public.exam_eligibility_rules r where r.stream_id = old.id
  ) then
    raise exception 'exam_streams: cannot reassign stream % to exam % — dependent cycle-streams/phases/sections/coverage/eligibility-rules exist',
      old.id, new.exam_id using errcode = 'P0422';
  end if;
  return new;
end;
$fn$;

-- ─── 3. Cycle / notification-specific eligibility ────────────────────────
-- Composite FK to exam_cycle_streams so a rule can only attach to a real
-- (cycle, stream) pair (single-exam by 242). ON DELETE RESTRICT preserves the
-- reviewer/verifier/source audit trail — retire via reviewer_status, never a
-- destructive pair delete.
create table if not exists public.exam_cycle_stream_eligibility (
  id uuid primary key default gen_random_uuid(),
  exam_cycle_id uuid not null,
  stream_id uuid not null,
  scope text not null default 'all'
    check (scope in ('all','general','obc','sc','st','ews','pwd','ex_serviceman','women')),
  rule_type text not null
    check (rule_type in (
      'age_min','age_max','education_min_level','nationality','gender','attempts_max',
      'discipline','min_percentage','certification','qualification_combination',
      'stream_availability','experience_min_years'
    )),
  value_num numeric,
  value_text text,
  value_json jsonb,
  cutoff_date_basis text
    check (cutoff_date_basis is null or cutoff_date_basis in ('cycle_notification','fixed_date')),
  cutoff_date date,
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
    references public.exam_cycle_streams(exam_cycle_id, stream_id) on delete restrict,
  constraint exam_cycle_stream_eligibility_qual_combo_json_check
    check (rule_type <> 'qualification_combination'
           or public.is_valid_qualification_combination(value_json)),
  unique (exam_cycle_id, stream_id, scope, rule_type)
);

create index if not exists idx_ecse_cycle_stream
  on public.exam_cycle_stream_eligibility(exam_cycle_id, stream_id);
create index if not exists idx_ecse_status
  on public.exam_cycle_stream_eligibility(reviewer_status);

-- Service-role only, mirroring exam_eligibility_rules (110).
alter table public.exam_cycle_stream_eligibility enable row level security;

drop trigger if exists exam_cycle_stream_eligibility_updated_at on public.exam_cycle_stream_eligibility;
create trigger exam_cycle_stream_eligibility_updated_at
  before update on public.exam_cycle_stream_eligibility
  for each row execute function public.tg_set_updated_at();

notify pgrst, 'reload schema';
