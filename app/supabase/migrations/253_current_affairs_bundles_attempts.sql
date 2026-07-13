-- 253_current_affairs_bundles_attempts.sql
-- GQR-G5a — Current-affairs weekly bundle + learner attempt runtime.
--
-- GA current-affairs practice uses its OWN attempts tables (never mock_attempts), so
-- mock analytics/leaderboards/attempt-counts stay clean and NO mastery/SRS/correction
-- write can fire (there is no path into mock_engine.submit_attempt). A published+verified
-- bundle is the exam-scoping + calendar unit; a learner attempt freezes the bundle's
-- still-eligible promoted current-event questions (question_snapshot, mirroring the mock
-- freeze) and scores INLINE against the frozen correct option. Service-role only; no
-- client policy (learner reads go through the server-owned API, which self-enforces
-- ownership).
--
-- Scope precedence (§8 pipeline doc + writing_practice/applicability precedence band):
-- exact-exam (exam_id = learner exam) > exam-family (exam_family_id = learner family)
-- > global (both null). Resolved server-side; the RPC re-validates the chosen bundle.
--
-- The frozen set is the AUTHORITATIVE eligible bundle membership: every question must be
-- a reviewed promoted current_event inside its validity window. The start RPC re-derives
-- that set under a bundle lock and rejects any missing / stale / extra / mismatched row
-- rather than silently shortening the attempt.
--
-- No per-attempt TTL: the doc-specified learner start gate is the bundle availability
-- window (available_until); there is no separate attempt expiry in the contract, so we
-- do not advertise one. Deleting a bundle must NOT erase historical learner attempts
-- (ON DELETE RESTRICT on the attempt→bundle FK).

begin;

-- ── 1. Bundles (editorial/calendar unit; exam or exam-family scoped) ────────
create table if not exists public.current_affairs_bundles (
  id uuid primary key default gen_random_uuid(),
  cadence text not null check (cadence in ('weekly', 'monthly')),
  period_start date not null,
  period_end date not null,
  -- Scope: exact exam, exam family, or global (both null). exam_family_id is a real FK.
  exam_id uuid references public.exams(id) on delete set null,
  exam_family_id uuid references public.exam_families(id) on delete set null,
  title text,
  publish_at timestamptz,
  available_until timestamptz,
  reviewer_status text not null default 'draft'
    check (reviewer_status in ('draft', 'in_review', 'verified', 'rejected')),
  status text not null default 'draft'
    check (status in ('draft', 'published', 'archived')),
  published_by uuid,
  published_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (period_end >= period_start)
);
create index if not exists idx_cab_lookup
  on public.current_affairs_bundles(cadence, status, exam_id, period_start);
create index if not exists idx_cab_family
  on public.current_affairs_bundles(cadence, status, exam_family_id, period_start);

create table if not exists public.current_affairs_bundle_questions (
  id uuid primary key default gen_random_uuid(),
  bundle_id uuid not null references public.current_affairs_bundles(id) on delete cascade,
  mock_question_id uuid not null references public.mock_question_bank(id) on delete cascade,
  display_order integer not null default 0,
  importance_score numeric,
  inclusion_reason text,
  created_at timestamptz not null default now(),
  unique (bundle_id, mock_question_id)
);
create index if not exists idx_cabq_bundle on public.current_affairs_bundle_questions(bundle_id);

-- ── 2. Attempts (OWN tables — never mock_attempts) ─────────────────────────
-- attempt→bundle is ON DELETE RESTRICT: a published bundle can be archived but not
-- deleted out from under historical learner analytics (contract: expiry/retirement
-- never deletes historical attempt analytics).
create table if not exists public.current_affairs_attempts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  exam_id uuid,
  bundle_id uuid not null references public.current_affairs_bundles(id) on delete restrict,
  cadence text not null,
  period_start date,
  period_end date,
  status text not null default 'in_progress' check (status in ('in_progress', 'submitted')),
  template_snapshot jsonb not null default '{}'::jsonb,
  total_questions integer not null default 0,
  score_raw numeric,
  total_correct integer,
  total_wrong integer,
  total_unattempted integer,
  started_at timestamptz not null default now(),
  submitted_at timestamptz,
  created_at timestamptz not null default now(),
  -- One attempt per learner per bundle (idempotent start; conflict-safe insert below).
  unique (user_id, bundle_id)
);
create index if not exists idx_caa_user on public.current_affairs_attempts(user_id, status);

create table if not exists public.current_affairs_attempt_responses (
  id uuid primary key default gen_random_uuid(),
  attempt_id uuid not null references public.current_affairs_attempts(id) on delete cascade,
  mock_question_id uuid not null,
  question_snapshot jsonb not null,
  selected_option_id uuid,
  is_correct boolean,
  is_visited boolean not null default false,
  is_marked_for_review boolean not null default false,
  time_spent_sec integer not null default 0 check (time_spent_sec >= 0),
  client_seq integer not null default 0 check (client_seq >= 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (attempt_id, mock_question_id)
);
create index if not exists idx_caar_attempt on public.current_affairs_attempt_responses(attempt_id);

-- ── 3. RLS: service-role only (learner access via server-owned API) ─────────
do $$
declare t text;
begin
  foreach t in array array[
    'current_affairs_bundles', 'current_affairs_bundle_questions',
    'current_affairs_attempts', 'current_affairs_attempt_responses'
  ] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('revoke all on public.%I from public', t);
    execute format('revoke all on public.%I from anon', t);
    execute format('revoke all on public.%I from authenticated', t);
    execute format('grant select, insert, update, delete on public.%I to service_role', t);
  end loop;
end $$;

-- ── 4. Authoritative eligible-membership helper ────────────────────────────
-- The still-eligible promoted current-event questions of a bundle, ordered. A question
-- is eligible iff it is a reviewed promoted current_event inside its validity window.
-- Used by both the start RPC (integrity lock) and the server freeze path.
create or replace function public.ca_eligible_bundle_question_ids(p_bundle uuid)
returns table(mock_question_id uuid, display_order integer)
language sql stable security definer set search_path = public as $$
  select bq.mock_question_id, bq.display_order
  from public.current_affairs_bundle_questions bq
  join public.mock_question_bank q on q.id = bq.mock_question_id
  where bq.bundle_id = p_bundle
    and q.source_kind = 'current_event'
    and q.is_current_based = true
    and q.reviewer_status in ('verified', 'published', 'live')
    and (q.valid_from is null or q.valid_from <= now())
    and (q.valid_until is null or q.valid_until > now())
  order by bq.display_order, bq.mock_question_id
$$;

-- ── 5. Atomic attempt start (freeze; idempotent + integrity-locked) ─────────
-- Gates the bundle (published + verified + publish/availability window), re-derives the
-- authoritative eligible set under a bundle lock, and proves the caller's frozen rows
-- EXACTLY equal that set (no missing / stale / extra / mismatched row → fail closed).
-- Conflict-safe: a concurrent second start returns 'reused', never a unique violation.
create or replace function public.ca_start_current_affairs_attempt(
  p_user uuid,
  p_bundle uuid,
  p_exam uuid,
  p_template_snapshot jsonb,
  p_response_rows jsonb
) returns jsonb
language plpgsql security definer set search_path = public as $$
declare
  v_bundle public.current_affairs_bundles%rowtype;
  v_attempt_id uuid;
  v_existing public.current_affairs_attempts%rowtype;
  v_row jsonb;
  v_authoritative uuid[];
  v_caller uuid[];
begin
  if p_user is null then raise exception 'user_required' using errcode = 'P0422'; end if;

  -- Lock the bundle so its membership can't change under the integrity check.
  select * into v_bundle from public.current_affairs_bundles where id = p_bundle for update;
  if not found then raise exception 'bundle_not_found' using errcode = 'P0404'; end if;
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

  -- Authoritative eligible set (re-derived under the lock).
  select array_agg(mock_question_id order by display_order, mock_question_id)
    into v_authoritative
  from public.ca_eligible_bundle_question_ids(p_bundle);
  if v_authoritative is null or array_length(v_authoritative, 1) is null then
    raise exception 'empty_bundle' using errcode = 'P0422';
  end if;

  -- Caller-frozen question ids must EXACTLY equal the authoritative set (order-independent).
  select array_agg((elem->>'question_id')::uuid)
    into v_caller
  from jsonb_array_elements(coalesce(p_response_rows, '[]'::jsonb)) elem;
  if v_caller is null
     or not (v_caller <@ v_authoritative and v_authoritative <@ v_caller)
     or array_length(v_caller, 1) <> array_length(v_authoritative, 1) then
    raise exception 'bundle_set_mismatch' using errcode = 'P0409';
  end if;

  -- Conflict-safe idempotent create: concurrent starts collapse to one attempt.
  insert into public.current_affairs_attempts (
    user_id, exam_id, bundle_id, cadence, period_start, period_end,
    status, template_snapshot, total_questions)
  values (
    p_user, p_exam, p_bundle, v_bundle.cadence, v_bundle.period_start, v_bundle.period_end,
    'in_progress', coalesce(p_template_snapshot, '{}'::jsonb), array_length(v_authoritative, 1))
  on conflict (user_id, bundle_id) do nothing
  returning id into v_attempt_id;

  if v_attempt_id is null then
    -- Lost the race (or a retry): return the existing attempt idempotently.
    select * into v_existing from public.current_affairs_attempts
      where user_id = p_user and bundle_id = p_bundle for update;
    if v_existing.status = 'in_progress' then
      return jsonb_build_object('outcome', 'reused', 'attempt_id', v_existing.id,
        'question_count', v_existing.total_questions);
    end if;
    raise exception 'attempt_already_submitted' using errcode = 'P0409';
  end if;

  for v_row in select * from jsonb_array_elements(p_response_rows) loop
    insert into public.current_affairs_attempt_responses (
      attempt_id, mock_question_id, question_snapshot)
    values (v_attempt_id, (v_row->>'question_id')::uuid, v_row->'question_snapshot');
  end loop;

  return jsonb_build_object('outcome', 'ready', 'attempt_id', v_attempt_id,
    'question_count', array_length(v_authoritative, 1));
end $$;

-- ── 6. Atomic answer save (owner + in-progress + membership + seq guard) ────
-- In-place conditional UPDATE under an attempt lock. Idempotency mirrors mock_engine
-- save_answer: client_seq <= stored_seq is an already-recorded no-op (not an overwrite).
-- The selected option must be one of the frozen options for that question.
create or replace function public.ca_save_current_affairs_answer(
  p_attempt_id uuid,
  p_user uuid,
  p_question_id uuid,
  p_selected_option_id uuid,
  p_is_marked_for_review boolean,
  p_time_spent_sec integer,
  p_client_seq integer
) returns jsonb
language plpgsql security definer set search_path = public as $$
declare
  v_att public.current_affairs_attempts%rowtype;
  v_resp public.current_affairs_attempt_responses%rowtype;
  v_option_ok boolean;
begin
  select * into v_att from public.current_affairs_attempts where id = p_attempt_id for update;
  if not found then raise exception 'attempt_not_found' using errcode = 'P0404'; end if;
  if v_att.user_id is distinct from p_user then
    raise exception 'not_attempt_owner' using errcode = 'P0403';
  end if;
  if v_att.status <> 'in_progress' then
    raise exception 'attempt_not_in_progress' using errcode = 'P0422';
  end if;

  select * into v_resp from public.current_affairs_attempt_responses
    where attempt_id = p_attempt_id and mock_question_id = p_question_id for update;
  if not found then raise exception 'question_not_in_attempt' using errcode = 'P0422'; end if;

  -- Selected option (when present) must be one of the frozen options.
  if p_selected_option_id is not null then
    select exists(
      select 1 from jsonb_array_elements(coalesce(v_resp.question_snapshot->'options', '[]'::jsonb)) o
      where (o->>'id') = p_selected_option_id::text
    ) into v_option_ok;
    if not v_option_ok then raise exception 'option_not_in_question' using errcode = 'P0422'; end if;
  end if;

  -- Idempotent: an equal-or-lower client_seq was already recorded (no overwrite).
  if coalesce(p_client_seq, 0) <= coalesce(v_resp.client_seq, 0)
     and (v_resp.is_visited or v_resp.selected_option_id is not null) then
    return jsonb_build_object('ok', true, 'idempotent', true, 'status', 'already_recorded');
  end if;

  update public.current_affairs_attempt_responses
  set selected_option_id = p_selected_option_id,
      is_marked_for_review = coalesce(p_is_marked_for_review, false),
      is_visited = true,
      time_spent_sec = greatest(coalesce(p_time_spent_sec, 0), 0),
      client_seq = greatest(coalesce(p_client_seq, 0), 0),
      updated_at = now()
  where id = v_resp.id;

  return jsonb_build_object('ok', true, 'status', 'recorded');
end $$;

-- ── 7. Atomic submit (inline scoring; NO mastery/correction/SRS) ────────────
-- Scores against the frozen question_snapshot.correct_option_id. GA never enters
-- mock_engine.submit_attempt, so no mastery/correction/analytics fan-out can fire.
create or replace function public.ca_submit_current_affairs_attempt(
  p_attempt_id uuid,
  p_user uuid
) returns jsonb
language plpgsql security definer set search_path = public as $$
declare
  v_att public.current_affairs_attempts%rowtype;
  v_correct int := 0;
  v_wrong int := 0;
  v_unattempted int := 0;
begin
  select * into v_att from public.current_affairs_attempts where id = p_attempt_id for update;
  if not found then raise exception 'attempt_not_found' using errcode = 'P0404'; end if;
  if v_att.user_id is distinct from p_user then
    raise exception 'not_attempt_owner' using errcode = 'P0403';
  end if;
  if v_att.status = 'submitted' then
    return jsonb_build_object('outcome', 'already_submitted', 'attempt_id', p_attempt_id,
      'score_raw', v_att.score_raw, 'total_correct', v_att.total_correct);
  end if;

  -- Score inline: correct iff selected matches the frozen correct option.
  update public.current_affairs_attempt_responses r
  set is_correct = (r.selected_option_id is not null
      and r.selected_option_id::text = (r.question_snapshot->>'correct_option_id'))
  where r.attempt_id = p_attempt_id;

  select
    count(*) filter (where is_correct),
    count(*) filter (where selected_option_id is not null and not coalesce(is_correct, false)),
    count(*) filter (where selected_option_id is null)
  into v_correct, v_wrong, v_unattempted
  from public.current_affairs_attempt_responses where attempt_id = p_attempt_id;

  update public.current_affairs_attempts
  set status = 'submitted', submitted_at = now(),
      total_correct = v_correct, total_wrong = v_wrong, total_unattempted = v_unattempted,
      score_raw = v_correct  -- 1 mark/correct, no negative marking (current-affairs practice)
  where id = p_attempt_id;

  return jsonb_build_object('outcome', 'submitted', 'attempt_id', p_attempt_id,
    'total_correct', v_correct, 'total_wrong', v_wrong,
    'total_unattempted', v_unattempted, 'score_raw', v_correct);
end $$;

-- ── 8. Grants (service-role only) ──────────────────────────────────────────
revoke all on function public.ca_eligible_bundle_question_ids(uuid) from public, anon, authenticated;
revoke all on function public.ca_start_current_affairs_attempt(uuid, uuid, uuid, jsonb, jsonb) from public, anon, authenticated;
revoke all on function public.ca_save_current_affairs_answer(uuid, uuid, uuid, uuid, boolean, integer, integer) from public, anon, authenticated;
revoke all on function public.ca_submit_current_affairs_attempt(uuid, uuid) from public, anon, authenticated;
grant execute on function public.ca_eligible_bundle_question_ids(uuid) to service_role;
grant execute on function public.ca_start_current_affairs_attempt(uuid, uuid, uuid, jsonb, jsonb) to service_role;
grant execute on function public.ca_save_current_affairs_answer(uuid, uuid, uuid, uuid, boolean, integer, integer) to service_role;
grant execute on function public.ca_submit_current_affairs_attempt(uuid, uuid) to service_role;

commit;

notify pgrst, 'reload schema';
