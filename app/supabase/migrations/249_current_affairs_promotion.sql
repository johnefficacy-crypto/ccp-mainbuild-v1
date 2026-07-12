-- 249_current_affairs_promotion.sql
-- GQR-G4a — Operator review + audited promotion of CA question candidates.
--
-- The human gate (ADR 0006): a candidate reaches the objective bank ONLY via
-- ca_promote_candidate, which is service-role + operator-gated at the endpoint and
-- requires an explicit approved candidate. The model/worker never promotes. Every
-- transition and promotion writes admin_audit_logs. Promoted questions land as
-- source_kind='current_event', is_current_based=true with the event's relevance
-- window, so mock_blueprint_selection._exam_base_pool (+ the GQR-G0 template fix)
-- keeps them out of permanent mocks.

begin;

-- ── 1. candidate → bank provenance links ───────────────────────────────────
create table if not exists public.current_affairs_question_links (
  id uuid primary key default gen_random_uuid(),
  candidate_id uuid not null references public.current_affairs_question_candidates(id) on delete cascade,
  event_id uuid not null references public.current_affairs_events(id) on delete cascade,
  claim_id uuid references public.current_affairs_claims(id) on delete set null,
  mock_question_id uuid not null references public.mock_question_bank(id) on delete cascade,
  promoted_by uuid,
  promoted_at timestamptz not null default now(),
  unique (candidate_id, mock_question_id)
);
create index if not exists idx_caql_event on public.current_affairs_question_links(event_id);
create index if not exists idx_caql_mock_question on public.current_affairs_question_links(mock_question_id);

do $$
declare t text;
begin
  foreach t in array array['current_affairs_question_links'] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('revoke all on public.%I from public', t);
    execute format('revoke all on public.%I from anon', t);
    execute format('revoke all on public.%I from authenticated', t);
    execute format('grant select, insert, update, delete on public.%I to service_role', t);
  end loop;
end $$;

-- ── 2. Review transition (CAS + audit; NEVER promotes) ─────────────────────
-- Mirrors cms_review_quant_heuristic (243): actor required, expected-status CAS,
-- whitelisted transition matrix, admin_audit_logs entry. 'promoted' is reachable
-- ONLY via ca_promote_candidate, so review can never publish.
create or replace function public.ca_review_candidate(
  p_candidate_id uuid,
  p_expected_status text,
  p_new_status text,
  p_reviewer_notes text,
  p_actor_user_id uuid,
  p_actor_email text
) returns jsonb
language plpgsql security definer set search_path = public as $$
declare
  v_row public.current_affairs_question_candidates%rowtype;
  v_audit_id uuid;
begin
  if p_actor_user_id is null then
    raise exception 'actor_required' using errcode = 'P0422';
  end if;
  if p_new_status not in ('approved', 'rejected', 'review_ready') then
    raise exception 'illegal_target_status: %', p_new_status using errcode = 'P0422';
  end if;

  select * into v_row from public.current_affairs_question_candidates
  where id = p_candidate_id for update;
  if not found then
    raise exception 'candidate_not_found' using errcode = 'P0404';
  end if;
  if v_row.status is distinct from p_expected_status then
    raise exception 'concurrent_modification: expected % but found %',
      p_expected_status, v_row.status using errcode = 'P0409';
  end if;

  -- Transition matrix (operator lifecycle; 'promoted' excluded — see promote RPC).
  if not (
    (v_row.status = 'review_ready' and p_new_status in ('approved', 'rejected')) or
    (v_row.status = 'approved'     and p_new_status in ('rejected', 'review_ready')) or
    (v_row.status = 'rejected'     and p_new_status = 'review_ready')
  ) then
    raise exception 'illegal_transition: % -> %', v_row.status, p_new_status
      using errcode = 'P0422';
  end if;
  -- Sending an approved/verified candidate back requires a reason.
  if v_row.status in ('approved') and p_new_status = 'review_ready'
     and coalesce(length(trim(p_reviewer_notes)), 0) = 0 then
    raise exception 'reason_required_on_reopen' using errcode = 'P0422';
  end if;

  update public.current_affairs_question_candidates
  set status = p_new_status, reviewed_by = p_actor_user_id, reviewed_at = now(),
      updated_at = now()
  where id = p_candidate_id;

  insert into public.admin_audit_logs (
    actor_id, actor_email, admin_user_id, action, entity_type, entity_id,
    old_value, new_value, notes)
  values (
    p_actor_user_id, p_actor_email, p_actor_user_id,
    'ca_candidate_status_transition', 'ca_question_candidate', p_candidate_id::text,
    jsonb_build_object('status', p_expected_status),
    jsonb_build_object('status', p_new_status), p_reviewer_notes)
  returning id into v_audit_id;

  return jsonb_build_object('ok', true, 'audit_id', v_audit_id,
    'prev_status', p_expected_status, 'new_status', p_new_status);
end $$;

-- ── 3. Audited promotion into the objective bank (human gate) ───────────────
-- Turns an APPROVED candidate into a mock_question_bank row + options + a
-- provenance link, marks the candidate 'promoted', and audits — all atomically.
-- CA isolation: source_kind='current_event', is_current_based=true, the event's
-- relevance window, and current_affairs_item_id → the event.
create or replace function public.ca_promote_candidate(
  p_candidate_id uuid,
  p_expected_status text,
  p_actor_user_id uuid,
  p_actor_email text
) returns jsonb
language plpgsql security definer set search_path = public as $$
declare
  v_cand public.current_affairs_question_candidates%rowtype;
  v_event public.current_affairs_events%rowtype;
  v_payload jsonb;
  v_opt jsonb;
  v_mock_q_id uuid;
  v_new_opt_id uuid;
  v_correct_opt_id uuid;
  v_correct_key text;
  v_claim_id uuid;
  v_audit_id uuid;
  v_opt_idx int := 0;
begin
  if p_actor_user_id is null then
    raise exception 'actor_required' using errcode = 'P0422';
  end if;

  select * into v_cand from public.current_affairs_question_candidates
  where id = p_candidate_id for update;
  if not found then
    raise exception 'candidate_not_found' using errcode = 'P0404';
  end if;
  -- CAS: the operator must be acting on the state they saw (an approved candidate).
  if v_cand.status is distinct from p_expected_status then
    raise exception 'concurrent_modification: expected % but found %',
      p_expected_status, v_cand.status using errcode = 'P0409';
  end if;
  if v_cand.status <> 'approved' then
    raise exception 'candidate_not_approved: %', v_cand.status using errcode = 'P0422';
  end if;

  select * into v_event from public.current_affairs_events where id = v_cand.event_id;
  if not found then
    raise exception 'event_not_found' using errcode = 'P0404';
  end if;
  -- Only a live, editorially-current event may be promoted (freshness gate).
  if v_event.status <> 'active' then
    raise exception 'event_not_active: %', v_event.status using errcode = 'P0422';
  end if;
  if v_event.relevance_until is not null and v_event.relevance_until < current_date then
    raise exception 'event_relevance_expired' using errcode = 'P0422';
  end if;

  v_payload := v_cand.question_payload;
  v_correct_key := lower(coalesce(v_payload->>'correct_option_id', ''));

  -- Bank row (stem/explanation/difficulty) + CA isolation provenance.
  insert into public.mock_question_bank (
    question_text, question_type, explanation, difficulty, language,
    reviewer_status, source_type, source_kind, is_current_based,
    event_anchor_date, valid_from, valid_until, current_affairs_item_id,
    question_fingerprint, created_by, last_reviewed_by, last_reviewed_at, published_at)
  values (
    v_payload->>'stem', 'mcq', v_payload->>'explanation',
    nullif(lower(v_payload->>'difficulty'), ''), 'en',
    'verified', 'current_event', 'current_event', true,
    v_event.event_date, v_event.relevance_from, v_event.relevance_until, v_event.id,
    v_cand.question_fingerprint, p_actor_user_id, p_actor_user_id, now(), now())
  returning id into v_mock_q_id;

  -- Options (0-based index) + capture the correct option's new uuid.
  for v_opt in select * from jsonb_array_elements(coalesce(v_payload->'options', '[]'::jsonb)) loop
    insert into public.mock_question_options (question_id, option_text, option_index, is_correct)
    values (
      v_mock_q_id, v_opt->>'text', v_opt_idx,
      (lower(coalesce(v_opt->>'id', '')) = v_correct_key))
    returning id into v_new_opt_id;
    if lower(coalesce(v_opt->>'id', '')) = v_correct_key then
      v_correct_opt_id := v_new_opt_id;
    end if;
    v_opt_idx := v_opt_idx + 1;
  end loop;
  if v_correct_opt_id is null then
    raise exception 'correct_option_not_resolved' using errcode = 'P0422';
  end if;
  update public.mock_question_bank set correct_option_id = v_correct_opt_id
  where id = v_mock_q_id;

  -- Provenance link (first resolved claim id, if any).
  v_claim_id := nullif((v_payload->'resolved_claim_ids'->>0), '')::uuid;
  insert into public.current_affairs_question_links (
    candidate_id, event_id, claim_id, mock_question_id, promoted_by)
  values (p_candidate_id, v_event.id, v_claim_id, v_mock_q_id, p_actor_user_id);

  -- Candidate → promoted (terminal).
  update public.current_affairs_question_candidates
  set status = 'promoted', reviewed_by = p_actor_user_id, reviewed_at = now(), updated_at = now()
  where id = p_candidate_id;

  insert into public.admin_audit_logs (
    actor_id, actor_email, admin_user_id, action, entity_type, entity_id,
    old_value, new_value, notes)
  values (
    p_actor_user_id, p_actor_email, p_actor_user_id,
    'ca_candidate_promoted', 'ca_question_candidate', p_candidate_id::text,
    jsonb_build_object('status', 'approved'),
    jsonb_build_object('status', 'promoted', 'mock_question_id', v_mock_q_id::text),
    'promoted to objective bank as current_event')
  returning id into v_audit_id;

  return jsonb_build_object('ok', true, 'audit_id', v_audit_id,
    'mock_question_id', v_mock_q_id, 'candidate_id', p_candidate_id);
end $$;

-- ── 4. Grants: service_role only ───────────────────────────────────────────
revoke all on function public.ca_review_candidate(uuid, text, text, text, uuid, text) from public, anon, authenticated;
revoke all on function public.ca_promote_candidate(uuid, text, uuid, text) from public, anon, authenticated;
grant execute on function public.ca_review_candidate(uuid, text, text, text, uuid, text) to service_role;
grant execute on function public.ca_promote_candidate(uuid, text, uuid, text) to service_role;

commit;

notify pgrst, 'reload schema';
