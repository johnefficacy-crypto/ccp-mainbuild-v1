-- 258_ca_monthly_retry.sql
-- GQR-G6 — Current-affairs MONTHLY consolidation + capped personalised retry tail.
--
-- The monthly attempt = an EDITORIAL CORE (a published+verified cadence='monthly' bundle,
-- verified exactly like the weekly runtime) PLUS a per-learner RETRY TAIL of the learner's
-- STILL-RELEVANT weekly mistakes (capped, frozen into the attempt). Retry items live in a
-- short-lived `current_affairs_retry_items` queue: expiry stops future scheduling but NEVER
-- deletes historical attempt analytics (the frozen attempt rows are untouched). No mastery/
-- SRS/Mistake-Book/correction write ever fires — GA stays on its own tables.
--
-- Immutable-migration discipline: 253/255 are landed, so this ALTERs the responses table
-- (adds a core/tail discriminator) and adds NEW functions; it never edits landed objects.

begin;

-- ── 1. Short-lived personalised retry queue ────────────────────────────────
-- One live item per learner+question. question_id RESTRICT-references the bank so a retry
-- item can't dangle; source_attempt_id SET NULL so purging a weekly attempt never blocks.
create table if not exists public.current_affairs_retry_items (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  question_id uuid not null references public.mock_question_bank(id) on delete restrict,
  source_attempt_id uuid references public.current_affairs_attempts(id) on delete set null,
  exam_id uuid references public.exams(id) on delete set null,
  due_at timestamptz,          -- earliest a monthly attempt may surface it (weekly→monthly gap)
  expires_at timestamptz,      -- relevance window end; past this the item is swept to 'expired'
  status text not null default 'pending'
    check (status in ('pending', 'consumed', 'expired')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, question_id)
);
create index if not exists idx_cari_due
  on public.current_affairs_retry_items(user_id, status, due_at);

alter table public.current_affairs_retry_items enable row level security;
revoke all on public.current_affairs_retry_items from public, anon, authenticated;
grant select, insert, update, delete on public.current_affairs_retry_items to service_role;

-- ── 2. Core/tail discriminator on the frozen responses ─────────────────────
-- Weekly rows default 'core'; the monthly RPC stamps 'retry_tail' on personalised items so
-- reporting can separate the editorial core from the learner's retry review.
alter table public.current_affairs_attempt_responses
  add column if not exists item_role text not null default 'core'
    check (item_role in ('core', 'retry_tail'));

-- ── 3. Reusable "question is still a promoted, relevant current-event" predicate ─
-- The SAME full-integrity relation the weekly eligibility helper proves, per single
-- question. Used to gate what may be enqueued as a mistake AND what may enter the tail.
create or replace function public.ca_question_current_relevant(p_qid uuid)
returns boolean
language sql stable security definer set search_path = public as $$
  select exists (
    select 1
    from public.mock_question_bank q
    where q.id = p_qid
      and q.source_kind = 'current_event'
      and q.is_current_based = true
      and q.reviewer_status in ('verified', 'published', 'live')
      and (q.valid_from is null or q.valid_from <= now())
      and (q.valid_until is null or q.valid_until > now())
      and q.current_affairs_item_id is not null
      and exists (
        select 1
        from public.current_affairs_question_links ql
        join public.current_affairs_claims cl on cl.id = ql.claim_id
        join public.current_affairs_claim_evidence ce on ce.claim_id = cl.id
        join public.current_affairs_documents d on d.id = ce.document_id
        join public.current_affairs_sources s on s.id = d.source_id
        join public.current_affairs_events ev on ev.id = q.current_affairs_item_id
        where ql.mock_question_id = q.id
          and ql.claim_id is not null
          and ql.event_id = q.current_affairs_item_id
          and cl.event_id = q.current_affairs_item_id
          and cl.reviewer_status = 'verified'
          and cl.factual_status = 'current'
          and ev.status = 'active'
          and (ev.relevance_until is null or ev.relevance_until >= current_date)
          and s.is_active = true
          and s.authority_level in ('primary_official', 'official_secondary')
      )
  )
$$;

-- ── 3b. Eligible retry-tail selector (server owns which items may enter a tail) ─
-- The learner's pending, due, non-expired, STILL-RELEVANT retry items, ordered oldest-due
-- first. The Python builder freezes from THIS set so the monthly start RPC's re-verification
-- can never be tripped by a stale item.
create or replace function public.ca_eligible_retry_tail(p_user uuid)
returns table(question_id uuid, due_at timestamptz, created_at timestamptz)
language sql stable security definer set search_path = public as $$
  select ri.question_id, ri.due_at, ri.created_at
  from public.current_affairs_retry_items ri
  where ri.user_id = p_user
    and ri.status = 'pending'
    and (ri.due_at is null or ri.due_at <= now())
    and (ri.expires_at is null or ri.expires_at > now())
    and public.ca_question_current_relevant(ri.question_id)
  order by ri.due_at nulls first, ri.created_at
$$;

-- ── 4. Enqueue a submitted weekly attempt's still-relevant mistakes ─────────
-- For each WRONG answer (answered + not correct) whose question is still a promoted,
-- relevant current-event, upsert a pending retry item (idempotent per learner+question).
-- due_at defaults to +7 days (weekly→monthly gap); expires_at to the bank relevance end.
create or replace function public.ca_enqueue_weekly_retry_items(
  p_attempt_id uuid,
  p_user uuid
) returns integer
language plpgsql security definer set search_path = public as $$
declare
  v_att public.current_affairs_attempts%rowtype;
  v_count int := 0;
  r record;
begin
  select * into v_att from public.current_affairs_attempts where id = p_attempt_id;
  if not found then raise exception 'attempt_not_found' using errcode = 'P0404'; end if;
  if v_att.user_id is distinct from p_user then
    raise exception 'not_attempt_owner' using errcode = 'P0403';
  end if;
  if v_att.status <> 'submitted' then
    raise exception 'attempt_not_submitted' using errcode = 'P0422';
  end if;
  if v_att.cadence <> 'weekly' then
    raise exception 'not_a_weekly_attempt' using errcode = 'P0422';
  end if;

  for r in
    select resp.mock_question_id as qid, q.valid_until as valid_until
    from public.current_affairs_attempt_responses resp
    join public.mock_question_bank q on q.id = resp.mock_question_id
    where resp.attempt_id = p_attempt_id
      and resp.selected_option_id is not null
      and coalesce(resp.is_correct, false) = false
      and public.ca_question_current_relevant(resp.mock_question_id)
  loop
    insert into public.current_affairs_retry_items (
      user_id, question_id, source_attempt_id, exam_id, due_at, expires_at, status)
    values (
      p_user, r.qid, p_attempt_id, v_att.exam_id,
      now() + interval '7 days', r.valid_until, 'pending')
    on conflict (user_id, question_id) do nothing;
    if found then v_count := v_count + 1; end if;
  end loop;

  return v_count;
end $$;

-- ── 5. Expire stale retry items (housekeeping; NEVER deletes history) ───────
create or replace function public.ca_sweep_expired_retry_items()
returns integer
language plpgsql security definer set search_path = public as $$
declare v_count int;
begin
  update public.current_affairs_retry_items
    set status = 'expired', updated_at = now()
  where status = 'pending'
    and (
      (expires_at is not null and expires_at < now())
      or not public.ca_question_current_relevant(question_id)
    );
  get diagnostics v_count = row_count;
  return v_count;
end $$;

-- ── 6. Start a MONTHLY attempt: editorial core + capped personalised retry tail ─
-- Verifies the CORE exactly like the weekly runtime (core must equal the monthly bundle's
-- authoritative eligible set, in order) AND the TAIL (each tail question must be a pending,
-- non-expired, still-relevant retry item OWNED by the learner, not overlapping the core,
-- within the cap). Every frozen row's content is verified against the LOCKED bank rows.
-- Consumed tail items flip to 'consumed'. Conflict-safe per (user, monthly bundle).
create or replace function public.ca_start_monthly_current_affairs_attempt(
  p_user uuid,
  p_bundle uuid,
  p_exam uuid,
  p_template_snapshot jsonb,
  p_core_rows jsonb,
  p_retry_rows jsonb
) returns jsonb
language plpgsql security definer set search_path = public as $$
declare
  v_cap constant int := 10;   -- capped personalised tail (pipeline §10)
  v_bundle public.current_affairs_bundles%rowtype;
  v_attempt_id uuid;
  v_existing public.current_affairs_attempts%rowtype;
  v_family uuid;
  v_row jsonb;
  v_qid uuid;
  v_raw uuid[];
  v_core uuid[];
  v_core_caller uuid[];
  v_tail uuid[];
  v_all uuid[];
  v_membership_rev text;
  v_bank_correct uuid;
  v_bank_rev timestamptz;
  v_bank_qtext text;
  v_bank_expl text;
  v_bank_opts text[];
  v_snap_opts text[];
begin
  if p_user is null then raise exception 'user_required' using errcode = 'P0422'; end if;

  select * into v_bundle from public.current_affairs_bundles where id = p_bundle for update;
  if not found then raise exception 'bundle_not_found' using errcode = 'P0404'; end if;
  if v_bundle.cadence <> 'monthly' then
    raise exception 'not_a_monthly_bundle' using errcode = 'P0422';
  end if;
  if v_bundle.status <> 'published' then
    raise exception 'bundle_not_published: %', v_bundle.status using errcode = 'P0422';
  end if;
  if v_bundle.reviewer_status <> 'verified' then
    raise exception 'bundle_not_verified: %', v_bundle.reviewer_status using errcode = 'P0422';
  end if;
  if v_bundle.publish_at is not null and v_bundle.publish_at > now() then
    raise exception 'bundle_not_yet_published' using errcode = 'P0422';
  end if;
  if v_bundle.available_until is not null and v_bundle.available_until <= now() then
    raise exception 'bundle_unavailable' using errcode = 'P0422';
  end if;

  -- Scope gate (identical to the weekly authority).
  select exam_family_id into v_family from public.exams where id = p_exam;
  if v_bundle.exam_id is not null then
    if v_bundle.exam_id is distinct from p_exam then
      raise exception 'bundle_scope_mismatch: exam' using errcode = 'P0403';
    end if;
  elsif v_bundle.exam_family_id is not null then
    if v_family is null or v_bundle.exam_family_id is distinct from v_family then
      raise exception 'bundle_scope_mismatch: family' using errcode = 'P0403';
    end if;
  end if;

  -- Caller-frozen core / tail ids (ordered).
  select array_agg((elem->>'question_id')::uuid order by ord) into v_core_caller
    from jsonb_array_elements(coalesce(p_core_rows, '[]'::jsonb)) with ordinality as t(elem, ord);
  select array_agg((elem->>'question_id')::uuid order by ord) into v_tail
    from jsonb_array_elements(coalesce(p_retry_rows, '[]'::jsonb)) with ordinality as t(elem, ord);
  v_tail := coalesce(v_tail, array[]::uuid[]);
  v_all := coalesce(v_core_caller, array[]::uuid[]) || v_tail;

  -- Lock membership + every referenced bank row + options (core AND tail).
  perform 1 from public.current_affairs_bundle_questions where bundle_id = p_bundle for update;
  perform 1 from public.mock_question_bank where id = any(v_all) for update;
  perform 1 from public.mock_question_options where question_id = any(v_all) for update;

  -- CORE authority: must equal the monthly bundle's eligible set, in order (no shrink).
  select array_agg(mock_question_id order by display_order, mock_question_id) into v_raw
    from public.current_affairs_bundle_questions where bundle_id = p_bundle;
  if v_raw is null or array_length(v_raw, 1) is null then
    raise exception 'empty_bundle' using errcode = 'P0422';
  end if;
  select array_agg(mock_question_id order by display_order, mock_question_id) into v_core
    from public.ca_eligible_bundle_question_ids(p_bundle);
  if v_core is null or v_core <> v_raw then
    raise exception 'bundle_degraded' using errcode = 'P0409';
  end if;
  if coalesce(v_core_caller, array[]::uuid[]) is distinct from v_core then
    raise exception 'bundle_set_mismatch' using errcode = 'P0409';
  end if;

  -- TAIL authority: capped, owned pending non-expired still-relevant retry items, no
  -- overlap with the core, no duplicates.
  if array_length(v_tail, 1) is not null and array_length(v_tail, 1) > v_cap then
    raise exception 'retry_tail_cap_exceeded' using errcode = 'P0422';
  end if;
  if (select count(distinct e) from unnest(v_tail) e) <> coalesce(array_length(v_tail, 1), 0) then
    raise exception 'retry_tail_duplicate' using errcode = 'P0409';
  end if;
  foreach v_qid in array v_tail loop
    if v_qid = any(v_core) then
      raise exception 'retry_tail_overlaps_core' using errcode = 'P0409';
    end if;
    if not exists (
      select 1 from public.current_affairs_retry_items
      where user_id = p_user and question_id = v_qid and status = 'pending'
        and (due_at is null or due_at <= now())
        and (expires_at is null or expires_at > now())
      for update
    ) then
      raise exception 'retry_tail_not_eligible' using errcode = 'P0409';
    end if;
    if not public.ca_question_current_relevant(v_qid) then
      raise exception 'retry_tail_not_relevant' using errcode = 'P0409';
    end if;
  end loop;

  v_membership_rev := md5(array_to_string(v_all, ','));

  -- Per-row content authority vs LOCKED bank rows (core + tail, identical to weekly).
  for v_row in
    select elem from jsonb_array_elements(coalesce(p_core_rows, '[]'::jsonb)) elem
    union all
    select elem from jsonb_array_elements(coalesce(p_retry_rows, '[]'::jsonb)) elem
  loop
    v_qid := (v_row->>'question_id')::uuid;
    select question_text, explanation, correct_option_id
      into v_bank_qtext, v_bank_expl, v_bank_correct
      from public.mock_question_bank where id = v_qid;
    if (v_row->'question_snapshot'->>'question_text') is distinct from v_bank_qtext
       or (v_row->'question_snapshot'->>'explanation') is distinct from v_bank_expl then
      raise exception 'snapshot_text_mismatch' using errcode = 'P0409';
    end if;
    if (v_row->'question_snapshot'->>'correct_option_id') is distinct from v_bank_correct::text then
      raise exception 'snapshot_answer_mismatch' using errcode = 'P0409';
    end if;
    select array_agg(id::text order by id) into v_bank_opts
      from public.mock_question_options where question_id = v_qid;
    select array_agg(o->>'id' order by o->>'id') into v_snap_opts
      from jsonb_array_elements(coalesce(v_row->'question_snapshot'->'options', '[]'::jsonb)) o;
    if v_bank_opts is distinct from v_snap_opts then
      raise exception 'snapshot_options_mismatch' using errcode = 'P0409';
    end if;
    if exists (
      select 1 from jsonb_array_elements(v_row->'question_snapshot'->'options') o
      left join public.mock_question_options mo on mo.id = (o->>'id')::uuid and mo.question_id = v_qid
      where mo.id is null or mo.option_text is distinct from (o->>'option_text')
    ) then
      raise exception 'snapshot_options_mismatch' using errcode = 'P0409';
    end if;
  end loop;

  -- Conflict-safe idempotent create.
  insert into public.current_affairs_attempts (
    user_id, exam_id, bundle_id, cadence, period_start, period_end,
    status, template_snapshot, total_questions, membership_revision)
  values (
    p_user, p_exam, p_bundle, v_bundle.cadence, v_bundle.period_start, v_bundle.period_end,
    'in_progress',
    coalesce(p_template_snapshot, '{}'::jsonb)
      || jsonb_build_object('bundle_revision', v_bundle.updated_at,
                            'membership_revision', v_membership_rev,
                            'core_count', array_length(v_core, 1),
                            'retry_tail_count', coalesce(array_length(v_tail, 1), 0)),
    array_length(v_all, 1), v_membership_rev)
  on conflict (user_id, bundle_id) do nothing
  returning id into v_attempt_id;

  if v_attempt_id is null then
    select * into v_existing from public.current_affairs_attempts
      where user_id = p_user and bundle_id = p_bundle for update;
    if v_existing.status = 'in_progress' then
      return jsonb_build_object('outcome', 'reused', 'attempt_id', v_existing.id,
        'question_count', v_existing.total_questions);
    end if;
    raise exception 'attempt_already_submitted' using errcode = 'P0409';
  end if;

  -- Freeze CORE rows (item_role='core') then TAIL rows (item_role='retry_tail'), in order.
  for v_row in
    select elem from jsonb_array_elements(coalesce(p_core_rows, '[]'::jsonb)) with ordinality as t(elem, ord) order by ord
  loop
    v_qid := (v_row->>'question_id')::uuid;
    select updated_at into v_bank_rev from public.mock_question_bank where id = v_qid;
    insert into public.current_affairs_attempt_responses (
      attempt_id, mock_question_id, question_snapshot, item_role)
    values (v_attempt_id, v_qid,
      (v_row->'question_snapshot') || jsonb_build_object('content_revision', v_bank_rev), 'core');
  end loop;
  for v_row in
    select elem from jsonb_array_elements(coalesce(p_retry_rows, '[]'::jsonb)) with ordinality as t(elem, ord) order by ord
  loop
    v_qid := (v_row->>'question_id')::uuid;
    select updated_at into v_bank_rev from public.mock_question_bank where id = v_qid;
    insert into public.current_affairs_attempt_responses (
      attempt_id, mock_question_id, question_snapshot, item_role)
    values (v_attempt_id, v_qid,
      (v_row->'question_snapshot') || jsonb_build_object('content_revision', v_bank_rev), 'retry_tail');
    -- The retry item is now consumed (frozen into this attempt); never deleted.
    update public.current_affairs_retry_items
      set status = 'consumed', updated_at = now()
    where user_id = p_user and question_id = v_qid and status = 'pending';
  end loop;

  return jsonb_build_object('outcome', 'ready', 'attempt_id', v_attempt_id,
    'question_count', array_length(v_all, 1),
    'core_count', array_length(v_core, 1),
    'retry_tail_count', coalesce(array_length(v_tail, 1), 0));
end $$;

-- ── 7. Grants (service-role only) ──────────────────────────────────────────
revoke all on function public.ca_question_current_relevant(uuid) from public, anon, authenticated;
revoke all on function public.ca_eligible_retry_tail(uuid) from public, anon, authenticated;
revoke all on function public.ca_enqueue_weekly_retry_items(uuid, uuid) from public, anon, authenticated;
revoke all on function public.ca_sweep_expired_retry_items() from public, anon, authenticated;
revoke all on function public.ca_start_monthly_current_affairs_attempt(uuid, uuid, uuid, jsonb, jsonb, jsonb) from public, anon, authenticated;
grant execute on function public.ca_question_current_relevant(uuid) to service_role;
grant execute on function public.ca_eligible_retry_tail(uuid) to service_role;
grant execute on function public.ca_enqueue_weekly_retry_items(uuid, uuid) to service_role;
grant execute on function public.ca_sweep_expired_retry_items() to service_role;
grant execute on function public.ca_start_monthly_current_affairs_attempt(uuid, uuid, uuid, jsonb, jsonb, jsonb) to service_role;

commit;

notify pgrst, 'reload schema';
