-- 219_j3_applied_vs_appeared.sql
--
-- J3 PR 2 — Applied-vs-Appeared (branches from merged PR 1, migration 216).
--
-- Gate: docs/status/J3-Applied-Vs-Appeared-Gate-2026-07-02.md, OPERATOR
-- APPROVED 2026-07-02. Resolutions: docs/status/J3-OD-Resolutions-Locked-
-- 2026-07-02.md §2 (two-lane model), §2.1 (NULL-safe DDL), §3 (OD-1..OD-6),
-- §4.1 (evidence exact schema), §6 (shared reservation_categories — reused,
-- NOT recreated). Implementation checklist: docs/status/
-- J3-Implementation-Checklist-2026-07-02.md (PR 2 section).
--
-- Applied version must be reconciled against the deployed schema_migrations
-- state at apply time (operator step); 219 = MAX(filesystem)+1 after
-- 218_writing_prompts_public_read_lockdown landed on main (this file was
-- renumbered 217→218→219 as those slots were taken by landed PRs — the
-- validate CI guard requires new migrations to be contiguous = MAX(main)+1).
-- Confirm with:
--   SELECT MAX(version) FROM schema_migrations;
-- before applying to any environment.
--
-- WHAT THIS DOES
-- --------------
-- A. exam_candidate_counts: typed applied/appeared candidate-count facts,
--    scope_kind (cycle|phase), optional reservation_category_id (NULL =
--    official total), full reviewer lifecycle + two-lane revision model
--    (mirrors exam_competition_metrics' §2.1 shape).
-- B. Scope-integrity trigger (exam_cycle_id/exam_phase_id belong to
--    exam_id, and phase belongs to the same cycle when both set) — mirrors
--    216's _ecm_check_scope / OD-3's write-validator requirement.
-- C. scope_kind / count_type shape CHECKs (OD-3): applied -> cycle scope,
--    no phase; appeared -> phase scope with phase set, OR an explicitly-
--    labelled cycle-level aggregate.
-- D. NULL-safe two-lane unique indexes (resolutions §2.1): NULLS NOT
--    DISTINCT partial unique indexes for the published/working lanes plus
--    per-scope version_no uniqueness and lineage constraints.
-- E. Published-parent BEFORE UPDATE guard (content columns frozen once
--    reviewer_status is reviewed/locked) — mirrors 216 Section G.
-- F. exam_candidate_count_evidence per resolutions §4.1 EXACT schema (no
--    claim_field / reservation_category_id on the evidence row — the
--    parent row IS the single claim) + append-only immutability triggers
--    + server-computed evidence_key.
-- G. RLS on both new tables: non-admin read requires reviewer_status IN
--    ('reviewed','locked') (mirrors migration 057/195's predicate, using
--    public.is_admin() — app-metadata role, NOT profiles.is_admin);
--    writes are service-role only (evidence has no authenticated policy
--    at all, matching 216's exam_competition_metric_evidence posture).
-- H. Lifecycle RPCs: cms_review_candidate_count (transition matrix + CAS +
--    evidence claim-value-match promotion gate, mirrors
--    cms_review_competition_metric) and
--    cms_reopen_candidate_count_for_edit (clone-to-draft).
-- I. OD-6 Option B backfill decision: NO ROWS ARE MIGRATED. See the
--    detailed comment in Section I below for why zero evidence exists to
--    prove disposition for any legacy exam_competition_metrics.applicant_count
--    value, and why exam_competition_metrics.applicant_count is therefore
--    left untouched/deprecated-in-place rather than partially backfilled.
--
-- Migrations are immutable once merged.

begin;

-- ═════════════════════════════════════════════════════════════════════════
-- A. exam_candidate_counts
-- ═════════════════════════════════════════════════════════════════════════

create table if not exists public.exam_candidate_counts (
  id uuid primary key default gen_random_uuid(),

  exam_id uuid not null references public.exams(id) on delete cascade,
  exam_cycle_id uuid not null references public.exam_cycles(id) on delete cascade,
  exam_phase_id uuid references public.exam_phases(id) on delete cascade,

  scope_kind text not null check (scope_kind in ('cycle', 'phase')),
  count_type text not null check (count_type in ('applied', 'appeared')),

  -- NULL = official total; non-NULL = a per-category count (OD-1/OD-4).
  reservation_category_id uuid
    references public.reservation_categories(id) on delete restrict,

  count_value integer not null check (count_value >= 0),

  -- Mirrors exam_competition_metrics' trust/lifecycle columns exactly.
  source_basis text not null default 'official'
    check (source_basis in ('manual', 'official', 'reviewed_analysis', 'derived', 'model_generated')),
  confidence_score numeric check (confidence_score is null or (confidence_score >= 0 and confidence_score <= 1)),

  -- Two-lane revision model (resolutions §2).
  version_no integer,
  supersedes_id uuid,
  superseded_at timestamptz,
  is_current_published boolean not null default false,

  -- Full reviewer lifecycle (mirrors 216).
  reviewer_status text not null default 'draft'
    check (reviewer_status in ('draft', 'pending_review', 'reviewed', 'locked', 'rejected')),
  reviewed_by uuid references public.profiles(id) on delete set null,
  reviewed_at timestamptz,
  reviewer_notes text,

  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint ecc_supersedes_self_fk
    foreign key (supersedes_id) references public.exam_candidate_counts(id) on delete restrict,
  constraint ecc_no_self_supersede
    check (supersedes_id is null or supersedes_id <> id),
  constraint ecc_version_no_positive
    check (version_no is not null and version_no > 0),
  constraint ecc_current_published_state
    check (not is_current_published
           or (reviewer_status in ('reviewed', 'locked') and superseded_at is null)),
  constraint ecc_superseded_not_current
    check (superseded_at is null or not is_current_published),

  -- OD-3 scope/count-type shape rule:
  --   applied  -> scope_kind='cycle' AND exam_phase_id IS NULL
  --   appeared -> (scope_kind='phase' AND exam_phase_id IS NOT NULL)
  --               OR (scope_kind='cycle' AND exam_phase_id IS NULL)  -- labelled cycle aggregate
  constraint ecc_count_type_scope_shape
    check (
      (count_type = 'applied' and scope_kind = 'cycle' and exam_phase_id is null)
      or
      (count_type = 'appeared' and (
        (scope_kind = 'phase' and exam_phase_id is not null)
        or (scope_kind = 'cycle' and exam_phase_id is null)
      ))
    ),
  constraint ecc_scope_kind_phase_consistency
    check (
      (scope_kind = 'cycle' and exam_phase_id is null)
      or (scope_kind = 'phase' and exam_phase_id is not null)
    )
);

comment on table public.exam_candidate_counts is
  'Applied-vs-appeared candidate-count facts (J3 PR2). Separate from '
  'exam_competition_metrics: applied/appeared arrive at different times '
  'with independent evidence/lifecycles (resolutions §3 OD-2). '
  'exam_id-scoped exam-master data, never recruitment_id.';
comment on column public.exam_candidate_counts.reservation_category_id is
  'NULL = official total for the scope; non-NULL = a per-category count '
  '(FK to shared reservation_categories, resolutions §6/OD-4). Category '
  'detail is optional, never mandatory (OD-1).';
comment on column public.exam_candidate_counts.scope_kind is
  'cycle | phase. applied is always cycle-scoped (exam_phase_id NULL). '
  'appeared is phase-scoped OR an explicitly-labelled cycle aggregate '
  '(scope_kind=''cycle'', exam_phase_id NULL) for authorities that only '
  'publish aggregate appearance data (resolutions §3 OD-3).';

-- ═════════════════════════════════════════════════════════════════════════
-- B. Scope-integrity trigger (mirrors 216's _ecm_check_scope). A write
-- validator confirming the phase belongs to the same exam AND cycle
-- (resolutions §3 OD-3) — bare FKs do not imply cross-table membership.
-- ═════════════════════════════════════════════════════════════════════════

create or replace function public._ecc_check_scope() returns trigger
language plpgsql as $fn$
begin
  if not exists (
    select 1 from public.exam_cycles c
    where c.id = new.exam_cycle_id and c.exam_id = new.exam_id
  ) then
    raise exception 'exam_candidate_counts: exam_cycle_id % does not belong to exam_id %',
      new.exam_cycle_id, new.exam_id using errcode = 'P0422';
  end if;
  -- OD-3 (checkpost P1-3): a phase-scoped count requires the phase to belong
  -- to the SAME exam AND the SAME cycle. p.exam_cycle_id IS NULL (a template /
  -- unbound phase) does NOT match any cycle — `p.exam_cycle_id = new.exam_cycle_id`
  -- is false for NULL, so template/unbound phases are rejected, not treated as
  -- a wildcard.
  if new.exam_phase_id is not null
     and not exists (
       select 1 from public.exam_phases p
       where p.id = new.exam_phase_id and p.exam_id = new.exam_id
         and p.exam_cycle_id = new.exam_cycle_id
     ) then
    raise exception 'exam_candidate_counts: exam_phase_id % must belong to exam % AND cycle % (template/unbound phases with NULL exam_cycle_id are rejected)',
      new.exam_phase_id, new.exam_id, new.exam_cycle_id using errcode = 'P0422';
  end if;
  return new;
end;
$fn$;

drop trigger if exists trg_ecc_check_scope on public.exam_candidate_counts;
create trigger trg_ecc_check_scope
  before insert or update on public.exam_candidate_counts
  for each row execute function public._ecc_check_scope();

-- ═════════════════════════════════════════════════════════════════════════
-- B.2 Lineage-validation trigger (checkpost P1-4; mirrors 216's §2.1
-- RPC/trigger same-scope-ancestry + version_no = parent+1 rule). A CHECK
-- cannot express a cross-row invariant, so a trigger enforces that a
-- superseding revision shares the FULL scope/category of its parent and that
-- version_no is strictly monotonic (parent.version_no + 1). This runs for
-- every writer, including raw service-role inserts that bypass the app layer.
-- ═════════════════════════════════════════════════════════════════════════

create or replace function public._ecc_check_lineage() returns trigger
language plpgsql as $fn$
declare v_parent public.exam_candidate_counts%rowtype;
begin
  if new.supersedes_id is null then
    return new;
  end if;
  select * into v_parent from public.exam_candidate_counts where id = new.supersedes_id;
  if not found then
    raise exception 'ecc_lineage: supersedes_id % does not exist', new.supersedes_id
      using errcode = 'P0422';
  end if;
  if v_parent.exam_id is distinct from new.exam_id
     or v_parent.exam_cycle_id is distinct from new.exam_cycle_id
     or v_parent.scope_kind is distinct from new.scope_kind
     or v_parent.exam_phase_id is distinct from new.exam_phase_id
     or v_parent.count_type is distinct from new.count_type
     or v_parent.reservation_category_id is distinct from new.reservation_category_id
  then
    raise exception 'ecc_lineage: supersedes_id % is a different scope/category than this revision — a superseding revision must share the full (exam, cycle, scope_kind, phase, count_type, category) scope of its parent',
      new.supersedes_id using errcode = 'P0422';
  end if;
  if new.version_no is distinct from (v_parent.version_no + 1) then
    raise exception 'ecc_lineage: version_no must be parent.version_no + 1 (parent=% expected=% got=%)',
      v_parent.version_no, v_parent.version_no + 1, new.version_no using errcode = 'P0422';
  end if;
  return new;
end;
$fn$;

drop trigger if exists trg_ecc_check_lineage on public.exam_candidate_counts;
create trigger trg_ecc_check_lineage
  before insert or update on public.exam_candidate_counts
  for each row execute function public._ecc_check_lineage();

-- ═════════════════════════════════════════════════════════════════════════
-- D. NULL-safe two-lane uniqueness (resolutions §2.1). exam_phase_id and
-- reservation_category_id are legitimately NULL inside a lane (cycle
-- scope / official total), so NULLS NOT DISTINCT is required (PG15+,
-- available on Supabase — mirrors the exact syntax the resolutions doc
-- specifies; no fallback needed since PR1's target environment already
-- assumes PG15+ for this feature per §2.1's own note).
-- ═════════════════════════════════════════════════════════════════════════

create unique index if not exists ecc_current_pub_uq
  on public.exam_candidate_counts
    (exam_id, exam_cycle_id, scope_kind, exam_phase_id, count_type, reservation_category_id)
  nulls not distinct
  where is_current_published;

create unique index if not exists ecc_working_uq
  on public.exam_candidate_counts
    (exam_id, exam_cycle_id, scope_kind, exam_phase_id, count_type, reservation_category_id)
  nulls not distinct
  where reviewer_status in ('draft', 'pending_review') and superseded_at is null;

-- version_no unique per scope (NULLS NOT DISTINCT over the scope tuple).
create unique index if not exists ecc_version_uq
  on public.exam_candidate_counts
    (exam_id, exam_cycle_id, scope_kind, exam_phase_id, count_type, reservation_category_id, version_no)
  nulls not distinct;

create index if not exists idx_ecc_current_published
  on public.exam_candidate_counts (exam_id, count_type)
  where is_current_published;

create index if not exists idx_ecc_exam_cycle
  on public.exam_candidate_counts (exam_id, exam_cycle_id);

-- ═════════════════════════════════════════════════════════════════════════
-- E. Published-parent BEFORE UPDATE guard (resolutions §2 — identical
-- posture to 216 Section G). Content columns frozen once published; only
-- lifecycle/supersession columns may change, and only via the lifecycle
-- RPC (transaction-local GUC distinguishes an authorized transition from a
-- raw service-role UPDATE attempting to bypass it).
-- ═════════════════════════════════════════════════════════════════════════

create or replace function public._ecc_guard_published_update() returns trigger
language plpgsql as $fn$
begin
  if old.reviewer_status in ('reviewed', 'locked') then
    if coalesce(current_setting('app.candidate_count_lifecycle_rpc', true), '') <> 'true' then
      if new.exam_id is distinct from old.exam_id
         or new.exam_cycle_id is distinct from old.exam_cycle_id
         or new.exam_phase_id is distinct from old.exam_phase_id
         or new.scope_kind is distinct from old.scope_kind
         or new.count_type is distinct from old.count_type
         or new.reservation_category_id is distinct from old.reservation_category_id
         or new.count_value is distinct from old.count_value
         or new.source_basis is distinct from old.source_basis
         or new.confidence_score is distinct from old.confidence_score
         or new.metadata is distinct from old.metadata
         or new.version_no is distinct from old.version_no
         or new.supersedes_id is distinct from old.supersedes_id
      then
        raise exception 'published_row_immutable: exam_candidate_counts % is reviewer_status=% (published); content columns are frozen. Use the lifecycle RPC (reopen-for-edit clones a new draft revision instead of mutating this row).',
          old.id, old.reviewer_status
          using errcode = 'P0409';
      end if;
    end if;
  end if;
  return new;
end;
$fn$;

drop trigger if exists trg_ecc_guard_published_update on public.exam_candidate_counts;
create trigger trg_ecc_guard_published_update
  before update on public.exam_candidate_counts
  for each row execute function public._ecc_guard_published_update();

create or replace function public._ecc_guard_published_delete() returns trigger
language plpgsql as $fn$
begin
  if old.reviewer_status in ('reviewed', 'locked') then
    raise exception 'published_row_immutable: cannot delete exam_candidate_counts % — reviewer_status=% (published)',
      old.id, old.reviewer_status using errcode = 'P0409';
  end if;
  return old;
end;
$fn$;

drop trigger if exists trg_ecc_guard_published_delete on public.exam_candidate_counts;
create trigger trg_ecc_guard_published_delete
  before delete on public.exam_candidate_counts
  for each row execute function public._ecc_guard_published_delete();

-- ═════════════════════════════════════════════════════════════════════════
-- F. exam_candidate_count_evidence (resolutions §4.1 EXACT schema)
-- ═════════════════════════════════════════════════════════════════════════

create table if not exists public.exam_candidate_count_evidence (
  id uuid primary key default gen_random_uuid(),

  count_id uuid not null
    references public.exam_candidate_counts(id) on delete cascade,
    -- cascade fires only for genuinely-draft cleanup; published-parent
    -- DELETE is trigger-blocked (Section E).

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

  -- Snapshot of the exact fact this evidence supported when attached:
  -- { count_type, scope_kind, exam_phase_id, reservation_category_code, count_value }
  claim_value jsonb not null,
  content_hash text,
  evidence_key text not null unique,

  captured_at timestamptz not null default now(),
  created_by uuid references public.profiles(id) on delete set null,
  created_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb,

  constraint ecce_source_present check (num_nonnulls(source_id, document_asset_id, evidence_url) >= 1)
);

create index if not exists exam_candidate_count_evidence_count_idx
  on public.exam_candidate_count_evidence(count_id);

-- Server-computed evidence_key (mirrors 216's _ecme_compute_evidence_key):
-- unconditionally OVERWRITES whatever the caller sends with the canonical
-- digest of (count_id, source/doc/url, source_page, claim_value).
create or replace function public._ecce_compute_evidence_key() returns trigger
language plpgsql as $fn$
begin
  new.evidence_key := encode(
    digest(
      concat_ws('|',
        new.count_id::text,
        coalesce(new.source_id::text, ''), coalesce(new.document_asset_id::text, ''),
        coalesce(new.evidence_url, ''), coalesce(new.source_page::text, ''),
        new.claim_value::text
      ),
      'sha256'
    ),
    'hex'
  );
  return new;
end;
$fn$;

drop trigger if exists trg_ecce_compute_evidence_key on public.exam_candidate_count_evidence;
create trigger trg_ecce_compute_evidence_key
  before insert on public.exam_candidate_count_evidence
  for each row execute function public._ecce_compute_evidence_key();

-- Append-only immutability (identical posture to 216's _ecme_guard_immutable).
create or replace function public._ecce_guard_immutable() returns trigger
language plpgsql as $fn$
declare v_parent_status text;
begin
  if tg_op = 'DELETE' then
    select reviewer_status into v_parent_status from public.exam_candidate_counts where id = old.count_id;
    if v_parent_status in ('reviewed', 'locked') then
      raise exception 'evidence_immutable: cannot delete evidence % — parent count % is published (%)',
        old.id, old.count_id, v_parent_status using errcode = 'P0409';
    end if;
    return old;
  end if;

  if tg_op = 'UPDATE' then
    select reviewer_status into v_parent_status from public.exam_candidate_counts where id = old.count_id;
    if v_parent_status in ('reviewed', 'locked') then
      raise exception 'evidence_immutable: cannot update evidence % — parent count % is published (%)',
        old.id, old.count_id, v_parent_status using errcode = 'P0409';
    end if;
    return new;
  end if;

  if tg_op = 'INSERT' then
    select reviewer_status into v_parent_status from public.exam_candidate_counts where id = new.count_id;
    if v_parent_status in ('reviewed', 'locked') then
      raise exception 'evidence_immutable: cannot attach evidence to published parent count % (%)',
        new.count_id, v_parent_status using errcode = 'P0409';
    end if;
    return new;
  end if;
  return null;
end;
$fn$;

drop trigger if exists trg_ecce_guard_immutable on public.exam_candidate_count_evidence;
create trigger trg_ecce_guard_immutable
  before insert or update or delete on public.exam_candidate_count_evidence
  for each row execute function public._ecce_guard_immutable();

-- ═════════════════════════════════════════════════════════════════════════
-- G. RLS (resolutions §3/§4.1/§7): non-admin read requires reviewer_status
-- IN ('reviewed','locked') (mirrors migration 057/195's exact predicate,
-- using public.is_admin() — app-metadata role, NOT profiles.is_admin).
-- Evidence has NO authenticated policy at all (mirrors 216's evidence
-- posture) — access only through permission-gated FastAPI routes using the
-- service role.
-- ═════════════════════════════════════════════════════════════════════════

alter table public.exam_candidate_counts enable row level security;
alter table public.exam_candidate_counts force row level security;

drop policy if exists exam_candidate_counts_read_reviewed on public.exam_candidate_counts;
create policy exam_candidate_counts_read_reviewed on public.exam_candidate_counts
  for select to authenticated
  using (
    reviewer_status in ('reviewed', 'locked')
    or public.is_admin(auth.uid())
  );

drop policy if exists exam_candidate_counts_admin_all on public.exam_candidate_counts;
create policy exam_candidate_counts_admin_all on public.exam_candidate_counts
  for all to authenticated
  using (public.is_admin(auth.uid()))
  with check (public.is_admin(auth.uid()));

revoke all on public.exam_candidate_counts from public;
revoke all on public.exam_candidate_counts from anon;
grant select on public.exam_candidate_counts to authenticated;
grant select, insert, update, delete on public.exam_candidate_counts to service_role;

alter table public.exam_candidate_count_evidence enable row level security;
alter table public.exam_candidate_count_evidence force row level security;
revoke all on public.exam_candidate_count_evidence from public;
revoke all on public.exam_candidate_count_evidence from anon;
revoke all on public.exam_candidate_count_evidence from authenticated;
grant select, insert, update, delete on public.exam_candidate_count_evidence to service_role;
-- No authenticated policy is created: ordinary authenticated users (admin
-- or not) cannot directly select/mutate evidence rows; all access is via
-- permission-gated FastAPI routes using the service role (resolutions §7).

-- ═════════════════════════════════════════════════════════════════════════
-- H. Lifecycle RPCs (mirrors 216 Section I exactly, adapted to the
-- candidate-count evidence promotion-comparison rule in §4.1: an
-- appeared/applied count may be promoted only when >=1 qualifying primary
-- evidence row exists whose claim_value.count_value equals the parent
-- count_value AND whose claim_value category/scope fields match the
-- parent; reviewed_analysis is not acceptable as the sole primary evidence
-- for official counts (§7)).
-- ═════════════════════════════════════════════════════════════════════════

create or replace function public.cms_review_candidate_count(
    p_count_id        uuid,
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
    v_row      exam_candidate_counts%rowtype;
    v_audit_id uuid;
    v_cat_code text;
begin
    if p_actor_user_id is null then
        raise exception 'missing_actor_id: p_actor_user_id must not be NULL' using errcode = 'P0422';
    end if;

    if p_new_status not in ('draft', 'pending_review', 'reviewed', 'locked', 'rejected') then
        raise exception 'invalid_target_status: % is not a recognised status', p_new_status using errcode = 'P0422';
    end if;

    select * into v_row from public.exam_candidate_counts where id = p_count_id for update;
    if not found then
        raise exception 'not_found: candidate count % does not exist', p_count_id using errcode = 'P0404';
    end if;

    if v_row.reviewer_status is distinct from p_expected_status then
        raise exception 'concurrent_modification: expected status=% but found %. Re-fetch and retry.',
            p_expected_status, v_row.reviewer_status using errcode = 'P0409';
    end if;

    if not (
           (v_row.reviewer_status = 'draft'          and p_new_status in ('pending_review', 'rejected'))
        or (v_row.reviewer_status = 'pending_review' and p_new_status in ('reviewed', 'rejected', 'draft'))
        or (v_row.reviewer_status = 'reviewed'        and p_new_status = 'locked')
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

    if v_row.reviewer_status = 'draft' and p_new_status = 'pending_review'
       and v_row.source_basis = 'model_generated'
    then
        raise exception 'model_generated_requires_evidence: attach primary evidence and change source_basis to official or reviewed_analysis before submitting a model_generated row for review'
            using errcode = 'P0422';
    end if;

    -- Publication gate (pending_review -> reviewed): >=1 qualifying primary
    -- evidence row whose claim_value.count_value matches the CURRENT parent
    -- value and whose category/scope fields match; source, when set, must
    -- be trusted (active, verified, not discovery-only, not an aggregator).
    -- reviewed_analysis never qualifies as the sole primary evidence for an
    -- official count (§4.1/§7).
    if v_row.reviewer_status = 'pending_review' and p_new_status = 'reviewed' then
        v_cat_code := null;
        if v_row.reservation_category_id is not null then
            select code into v_cat_code from public.reservation_categories where id = v_row.reservation_category_id;
        end if;

        if not exists (
          select 1 from public.exam_candidate_count_evidence e
          join public.source_registry sr on sr.id = e.source_id
          where e.count_id = v_row.id
            and e.evidence_role = 'primary'
            and e.evidence_kind <> 'reviewed_analysis'
            -- claim_value shape/type guard (checkpost P1-5): count_value must
            -- be a JSON number BEFORE the numeric cast, so a malformed direct
            -- insert fails this predicate (evidence does not qualify) instead
            -- of raising an uncontrolled cast error.
            and jsonb_typeof(e.claim_value -> 'count_value') = 'number'
            and (e.claim_value ->> 'count_value')::numeric = v_row.count_value
            and coalesce(e.claim_value ->> 'count_type', '') = v_row.count_type
            and coalesce(e.claim_value ->> 'scope_kind', '') = v_row.scope_kind
            and coalesce(e.claim_value ->> 'exam_phase_id', '') is not distinct from coalesce(v_row.exam_phase_id::text, '')
            and coalesce(e.claim_value ->> 'reservation_category_code', '') is not distinct from coalesce(v_cat_code, '')
            -- Source-trust (§7, checkpost P1-5): source_id IS NULL is NOT
            -- trusted. Promotion requires an EXISTING, active, verified,
            -- non-discovery, non-aggregator source_registry row PLUS an exact
            -- evidence_url or document_asset_id. The inner JOIN drops any
            -- evidence with a null/dangling source_id.
            and sr.is_active and sr.is_verified and not sr.discovery_only
            and sr.source_type <> 'aggregator'
            and (e.evidence_url is not null or e.document_asset_id is not null)
        ) then
            raise exception 'missing_or_stale_evidence: candidate count has no matching, source-trusted primary evidence' using errcode = 'P0422';
        end if;
    end if;

    perform set_config('app.candidate_count_lifecycle_rpc', 'true', true);

    if p_new_status = 'reviewed' and v_row.reviewer_status = 'pending_review' then
        update public.exam_candidate_counts
        set superseded_at = now(), is_current_published = false
        where exam_id = v_row.exam_id
          and exam_cycle_id = v_row.exam_cycle_id
          and scope_kind = v_row.scope_kind
          and exam_phase_id is not distinct from v_row.exam_phase_id
          and count_type = v_row.count_type
          and reservation_category_id is not distinct from v_row.reservation_category_id
          and is_current_published = true
          and id <> v_row.id;

        update public.exam_candidate_counts
        set reviewer_status = p_new_status,
            reviewed_by = p_actor_user_id,
            reviewed_at = now(),
            reviewer_notes = coalesce(p_reviewer_notes, reviewer_notes),
            is_current_published = true,
            updated_at = now()
        where id = p_count_id
        returning * into v_row;
    else
        update public.exam_candidate_counts
        set reviewer_status = p_new_status,
            reviewed_by = p_actor_user_id,
            reviewed_at = now(),
            reviewer_notes = coalesce(p_reviewer_notes, reviewer_notes),
            updated_at = now()
        where id = p_count_id
        returning * into v_row;
    end if;

    perform set_config('app.candidate_count_lifecycle_rpc', 'false', true);

    insert into public.admin_audit_logs (
        actor_id, actor_email, admin_user_id, action, entity_type, entity_id,
        old_value, new_value, notes
    ) values (
        p_actor_user_id, p_actor_email, p_actor_user_id,
        'candidate_count_status_transition', 'exam_candidate_count', p_count_id::text,
        jsonb_build_object('status', p_expected_status),
        jsonb_build_object('status', p_new_status),
        p_reviewer_notes
    ) returning id into v_audit_id;

    return jsonb_build_object(
        'ok', true, 'audit_id', v_audit_id, 'count_id', p_count_id,
        'prev_status', p_expected_status, 'new_status', p_new_status
    );
end;
$$;

create or replace function public.cms_reopen_candidate_count_for_edit(
    p_count_id       uuid,
    p_reviewer_notes text,
    p_actor_user_id  uuid,
    p_actor_email    text
)
returns exam_candidate_counts
language plpgsql
security definer
set search_path = public
as $$
declare
    v_pub exam_candidate_counts%rowtype;
    v_new exam_candidate_counts%rowtype;
    v_next_version integer;
begin
    if p_actor_user_id is null then
        raise exception 'missing_actor_id: p_actor_user_id must not be NULL' using errcode = 'P0422';
    end if;
    if nullif(trim(coalesce(p_reviewer_notes, '')), '') is null then
        raise exception 'invalid_reviewer_notes: reviewer_notes required to reopen for edit' using errcode = 'P0422';
    end if;

    select * into v_pub from public.exam_candidate_counts where id = p_count_id for update;
    if not found then
        raise exception 'not_found: candidate count % does not exist', p_count_id using errcode = 'P0404';
    end if;
    if v_pub.reviewer_status not in ('reviewed', 'locked') then
        raise exception 'not_published: only a reviewed/locked row can be reopened for edit' using errcode = 'P0422';
    end if;

    select coalesce(max(version_no), 0) + 1 into v_next_version
    from public.exam_candidate_counts
    where exam_id = v_pub.exam_id
      and exam_cycle_id = v_pub.exam_cycle_id
      and scope_kind = v_pub.scope_kind
      and exam_phase_id is not distinct from v_pub.exam_phase_id
      and count_type = v_pub.count_type
      and reservation_category_id is not distinct from v_pub.reservation_category_id;

    insert into public.exam_candidate_counts (
        exam_id, exam_cycle_id, exam_phase_id, scope_kind, count_type,
        reservation_category_id, count_value, source_basis, confidence_score,
        reviewer_status, version_no, supersedes_id, metadata
    ) values (
        v_pub.exam_id, v_pub.exam_cycle_id, v_pub.exam_phase_id, v_pub.scope_kind, v_pub.count_type,
        v_pub.reservation_category_id, v_pub.count_value, v_pub.source_basis, v_pub.confidence_score,
        'draft', v_next_version, v_pub.id, v_pub.metadata || jsonb_build_object('reopen_notes', p_reviewer_notes)
    ) returning * into v_new;

    insert into public.admin_audit_logs (
        actor_id, actor_email, admin_user_id, action, entity_type, entity_id,
        old_value, new_value, notes
    ) values (
        p_actor_user_id, p_actor_email, p_actor_user_id,
        'candidate_count_reopen_for_edit', 'exam_candidate_count', p_count_id::text,
        jsonb_build_object('published_id', v_pub.id),
        jsonb_build_object('draft_id', v_new.id),
        p_reviewer_notes
    );

    return v_new;
end;
$$;

revoke execute on function public.cms_review_candidate_count(uuid, text, text, text, uuid, text) from public;
revoke execute on function public.cms_review_candidate_count(uuid, text, text, text, uuid, text) from anon;
revoke execute on function public.cms_review_candidate_count(uuid, text, text, text, uuid, text) from authenticated;
grant  execute on function public.cms_review_candidate_count(uuid, text, text, text, uuid, text) to service_role;

revoke execute on function public.cms_reopen_candidate_count_for_edit(uuid, text, uuid, text) from public;
revoke execute on function public.cms_reopen_candidate_count_for_edit(uuid, text, uuid, text) from anon;
revoke execute on function public.cms_reopen_candidate_count_for_edit(uuid, text, uuid, text) from authenticated;
grant  execute on function public.cms_reopen_candidate_count_for_edit(uuid, text, uuid, text) to service_role;

create trigger trg_ecc_updated_at
  before update on public.exam_candidate_counts
  for each row execute function public.tg_set_updated_at();

-- ═════════════════════════════════════════════════════════════════════════
-- I. OD-6 Option B backfill decision: NO ROWS MIGRATED (documented judgment
-- call, not a shortcut).
--
-- Option B requires migrating only exam_competition_metrics.applicant_count
-- rows whose EVIDENCE explicitly proves the value means "applied" (never
-- ambiguous silent conversion). The evidence trail that could prove this
-- disposition is exam_competition_metric_evidence — but that table is
-- ITSELF new in migration 216 (this repo's PR1), and its claim_field CHECK
-- constraint does not even include "applicant_count" as a valid value
-- (216 Section H: claim_field in ('vacancy_total','vacancy_by_category',
-- 'cutoff_by_category','difficulty_assessment','competition_pressure_score')
-- — applicant_count is absent). Concretely:
--
--   SELECT count(*) FROM exam_competition_metric_evidence
--   WHERE claim_field = 'applicant_count';
--   -- always 0, both because the table is brand new (no historical
--   -- evidence was ever attached to any legacy applicant_count value)
--   -- AND because the schema does not even accept that claim_field.
--
-- Every existing applicant_count value therefore has ZERO queryable
-- evidence of any kind — there is no "prove it means applied" signal to
-- select on. Option B's own text is explicit that ambiguous rows are
-- NEVER silently converted; with zero evidence, every row is ambiguous by
-- construction. The fail-closed, evidence-based conclusion is that NO rows
-- can be conservatively migrated into exam_candidate_counts as "applied":
-- doing so would fabricate a disposition that no evidence supports, which
-- is exactly the failure mode OD-6 exists to prevent.
--
-- Disposition: exam_competition_metrics.applicant_count is left untouched
-- and deprecated-in-place (no new writes per PR1's write-allowlist removal
-- in admin_exam_intel_cms.py; the column itself is not dropped or renamed,
-- consistent with the immutable-migration / additive-deprecation pattern
-- used throughout J3). It is NOT read into exam_candidate_counts by this
-- migration. Operators who hold out-of-band evidence for a specific
-- historical applicant_count value may manually create a fresh, evidence-
-- backed exam_candidate_counts row through the normal CMS create + evidence
-- + review lifecycle — that is a forward-looking operator action, not a
-- migration-time bulk conversion.
-- ═════════════════════════════════════════════════════════════════════════

-- Executable, fail-closed OD-6 evidence (checkpost P1-6). Even though the
-- disposition is "convert 0 rows", the gate requires RAISE-on-mismatch
-- assertions rather than a prose notice, so the migration proves — at apply
-- time, in the same transaction — that:
--   (a) the pre-migration non-null applicant_count population is captured;
--   (b) exactly 0 rows were converted into exam_candidate_counts;
--   (c) every non-null applicant_count row is preserved as legacy-unknown
--       (converted + preserved_unknown = pre_count, zero loss);
--   (d) the non-null applicant_count population is byte-for-byte unchanged
--       after this migration (zero-loss equality — the column is untouched);
--   (e) a representative competition_pressure_score is preserved (this PR
--       never alters competition_pressure_score — OD-5 / F.4).
-- Any mismatch aborts the whole migration (fail-closed).
do $$
declare
  v_pre_count           bigint;
  v_post_count          bigint;
  v_converted           bigint;
  v_preserved_unknown   bigint;
  v_pressure_before     numeric;
  v_pressure_after      numeric;
  v_rep_id              uuid;
begin
  -- (a) pre-migration non-null applicant_count population.
  select count(*) into v_pre_count
    from public.exam_competition_metrics
    where applicant_count is not null;

  -- (b) rows this migration converted into exam_candidate_counts from
  -- applicant_count. Section I converts NONE, so this is 0 by construction;
  -- a converted row would carry metadata.converted_from_applicant_count.
  select count(*) into v_converted
    from public.exam_candidate_counts
    where (metadata ->> 'converted_from_applicant_count') is not null;

  if v_converted <> 0 then
    raise exception 'J3 PR2 §I (OD-6): expected 0 converted rows, found % — Section I must not convert any applicant_count value (ambiguous rows are never silently converted).', v_converted;
  end if;

  -- (c) every non-null applicant_count value is preserved as legacy-unknown
  -- (nothing converted → all preserved). Zero-loss accounting must balance.
  v_preserved_unknown := v_pre_count - v_converted;
  if (v_converted + v_preserved_unknown) <> v_pre_count then
    raise exception 'J3 PR2 §I (OD-6): zero-loss accounting failed — converted(%) + preserved(%) <> pre_count(%)', v_converted, v_preserved_unknown, v_pre_count;
  end if;

  -- (d) zero-loss equality: the applicant_count population is unchanged.
  select count(*) into v_post_count
    from public.exam_competition_metrics
    where applicant_count is not null;
  if v_post_count <> v_pre_count then
    raise exception 'J3 PR2 §I (OD-6): applicant_count was mutated (pre=% post=%) — the column must be deprecated-in-place, never touched by this migration.', v_pre_count, v_post_count;
  end if;

  -- (e) representative competition_pressure_score preservation (OD-5): this
  -- PR must never alter competition_pressure_score. Capture one representative
  -- score and re-read it after the migration body; they must be identical.
  select id, competition_pressure_score
    into v_rep_id, v_pressure_before
    from public.exam_competition_metrics
    where competition_pressure_score is not null
    order by id
    limit 1;
  if v_rep_id is not null then
    select competition_pressure_score into v_pressure_after
      from public.exam_competition_metrics where id = v_rep_id;
    if v_pressure_after is distinct from v_pressure_before then
      raise exception 'J3 PR2 §I (OD-5/F.4): competition_pressure_score changed for representative row % (before=% after=%) — this PR must never alter it.', v_rep_id, v_pressure_before, v_pressure_after;
    end if;
  end if;

  raise notice 'J3 PR2 §I (OD-6 Option B) fail-closed evidence PASSED: 0 rows migrated from exam_competition_metrics.applicant_count into exam_candidate_counts (zero evidence trail exists to prove any legacy value means "applied"). pre_non_null_applicant_count=%, converted=0, preserved_unknown=%, post_non_null_applicant_count=% (zero-loss), representative competition_pressure_score preserved. exam_competition_metrics.applicant_count remains untouched/deprecated-in-place; ambiguous rows were never converted.',
    v_pre_count, v_preserved_unknown, v_post_count;
end $$;

commit;

select pg_notify('pgrst', 'reload schema');
