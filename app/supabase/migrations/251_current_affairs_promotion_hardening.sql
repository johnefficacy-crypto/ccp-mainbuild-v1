-- 251_current_affairs_promotion_hardening.sql
-- GQR-G4 — harden CA review + promotion per checkpost #970 (migration 249 is landed
-- and immutable, so this is a forward migration).
--
-- F3: both RPCs dual-CAS on status AND updated_at (content-revision token) + a
--     mandatory 8-500 char audit reason (mirrors migration 246). Signatures change,
--     so the old-signature functions are dropped first.
-- F4: ca_promote_candidate REVALIDATES the persisted Stage-D verdict + structural
--     payload + evidence/claim/source integrity inside the txn (fail-closed).
-- F5: one provenance link per resolved claim — links unique key gains claim_id.

begin;

-- ── F5: one provenance row per grounding claim ─────────────────────────────
alter table public.current_affairs_question_links
  drop constraint if exists current_affairs_question_links_candidate_id_mock_question_id_key;
alter table public.current_affairs_question_links
  add constraint current_affairs_question_links_cand_mq_claim_key
  unique (candidate_id, mock_question_id, claim_id);

-- Drop the old-signature functions (new signatures below add an overload otherwise).
drop function if exists public.ca_review_candidate(uuid, text, text, text, uuid, text);
drop function if exists public.ca_promote_candidate(uuid, text, uuid, text);

-- ── Review transition (dual CAS + reason + audit; NEVER promotes) ──────────
create or replace function public.ca_review_candidate(
  p_candidate_id uuid,
  p_expected_status text,
  p_expected_updated_at timestamptz,
  p_new_status text,
  p_reason text,
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
  if nullif(btrim(coalesce(p_reason, '')), '') is null
     or char_length(btrim(p_reason)) < 8 or char_length(btrim(p_reason)) > 500 then
    raise exception 'invalid_reason: p_reason must be 8-500 characters' using errcode = 'P0422';
  end if;
  if p_expected_updated_at is null then
    raise exception 'concurrent_modification: p_expected_updated_at (CAS token) is required'
      using errcode = 'P0409';
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
    raise exception 'concurrent_modification: expected status % but found %',
      p_expected_status, v_row.status using errcode = 'P0409';
  end if;
  if v_row.updated_at is distinct from p_expected_updated_at then
    raise exception 'concurrent_modification: candidate changed since read (content token)'
      using errcode = 'P0409';
  end if;

  if not (
    (v_row.status = 'review_ready' and p_new_status in ('approved', 'rejected')) or
    (v_row.status = 'approved'     and p_new_status in ('rejected', 'review_ready')) or
    (v_row.status = 'rejected'     and p_new_status = 'review_ready')
  ) then
    raise exception 'illegal_transition: % -> %', v_row.status, p_new_status
      using errcode = 'P0422';
  end if;
  if v_row.status = 'approved' and p_new_status = 'review_ready'
     and coalesce(length(trim(p_reviewer_notes)), 0) = 0 then
    raise exception 'reason_required_on_reopen' using errcode = 'P0422';
  end if;

  update public.current_affairs_question_candidates
  set status = p_new_status, reviewed_by = p_actor_user_id, reviewed_at = now(), updated_at = now()
  where id = p_candidate_id;

  insert into public.admin_audit_logs (
    actor_id, actor_email, admin_user_id, action, entity_type, entity_id,
    old_value, new_value, notes)
  values (
    p_actor_user_id, p_actor_email, p_actor_user_id,
    'ca_candidate_status_transition', 'ca_question_candidate', p_candidate_id::text,
    jsonb_build_object('status', p_expected_status),
    jsonb_build_object('status', p_new_status),
    btrim(p_reason) || coalesce(' | ' || nullif(btrim(coalesce(p_reviewer_notes, '')), ''), ''))
  returning id into v_audit_id;

  return jsonb_build_object('ok', true, 'audit_id', v_audit_id,
    'prev_status', p_expected_status, 'new_status', p_new_status);
end $$;

-- ── Audited promotion (human gate + Stage-D revalidation) ──────────────────
create or replace function public.ca_promote_candidate(
  p_candidate_id uuid,
  p_expected_status text,
  p_expected_updated_at timestamptz,
  p_reason text,
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
  v_claim_ids uuid[];
  v_claim_id uuid;
  v_audit_id uuid;
  v_opt_idx int := 0;
  v_opt_texts text[] := array[]::text[];
  v_claim_count int;
  v_ev_count int;
  v_has_authoritative boolean;
begin
  if p_actor_user_id is null then
    raise exception 'actor_required' using errcode = 'P0422';
  end if;
  if nullif(btrim(coalesce(p_reason, '')), '') is null
     or char_length(btrim(p_reason)) < 8 or char_length(btrim(p_reason)) > 500 then
    raise exception 'invalid_reason: p_reason must be 8-500 characters' using errcode = 'P0422';
  end if;
  if p_expected_updated_at is null then
    raise exception 'concurrent_modification: p_expected_updated_at (CAS token) is required'
      using errcode = 'P0409';
  end if;

  select * into v_cand from public.current_affairs_question_candidates
  where id = p_candidate_id for update;
  if not found then
    raise exception 'candidate_not_found' using errcode = 'P0404';
  end if;
  if v_cand.status is distinct from p_expected_status then
    raise exception 'concurrent_modification: expected status % but found %',
      p_expected_status, v_cand.status using errcode = 'P0409';
  end if;
  if v_cand.updated_at is distinct from p_expected_updated_at then
    raise exception 'concurrent_modification: candidate changed since read (content token)'
      using errcode = 'P0409';
  end if;
  if v_cand.status <> 'approved' then
    raise exception 'candidate_not_approved: %', v_cand.status using errcode = 'P0422';
  end if;

  -- Stage-D REVALIDATION (F4): promotion NEVER trusts approval alone.
  if not coalesce((v_cand.validation_result->>'ok')::boolean, false) then
    raise exception 'validation_not_passed' using errcode = 'P0422';
  end if;

  select * into v_event from public.current_affairs_events where id = v_cand.event_id;
  if not found then
    raise exception 'event_not_found' using errcode = 'P0404';
  end if;
  if v_event.status <> 'active' then
    raise exception 'event_not_active: %', v_event.status using errcode = 'P0422';
  end if;
  if v_event.relevance_until is not null and v_event.relevance_until < current_date then
    raise exception 'event_relevance_expired' using errcode = 'P0422';
  end if;

  v_payload := v_cand.question_payload;
  v_correct_key := lower(coalesce(v_payload->>'correct_option_id', ''));

  if nullif(btrim(coalesce(v_payload->>'stem', '')), '') is null then
    raise exception 'empty_stem' using errcode = 'P0422';
  end if;
  if nullif(btrim(coalesce(v_payload->>'explanation', '')), '') is null then
    raise exception 'empty_explanation' using errcode = 'P0422';
  end if;
  if jsonb_array_length(coalesce(v_payload->'options', '[]'::jsonb)) <> 4 then
    raise exception 'must_have_exactly_four_options' using errcode = 'P0422';
  end if;

  -- Evidence / claim integrity (ADR 0007).
  v_claim_ids := array(
    select value::uuid
    from jsonb_array_elements_text(coalesce(v_payload->'resolved_claim_ids', '[]'::jsonb)) as value
    where value is not null and value <> '');
  if v_claim_ids is null or array_length(v_claim_ids, 1) is null then
    raise exception 'no_linked_claim' using errcode = 'P0422';
  end if;
  select count(*) into v_claim_count from public.current_affairs_claims
  where id = any(v_claim_ids) and factual_status = 'current';
  if v_claim_count <> array_length(v_claim_ids, 1) then
    raise exception 'noncurrent_or_missing_claim' using errcode = 'P0422';
  end if;
  select count(ev.*), bool_or(s.authority_level <> 'discovery_only' and s.is_active)
  into v_ev_count, v_has_authoritative
  from public.current_affairs_claim_evidence ev
  join public.current_affairs_documents d on d.id = ev.document_id
  join public.current_affairs_sources s on s.id = d.source_id
  where ev.claim_id = any(v_claim_ids);
  if coalesce(v_ev_count, 0) = 0 then
    raise exception 'no_resolvable_evidence' using errcode = 'P0422';
  end if;
  if not coalesce(v_has_authoritative, false) then
    raise exception 'sole_evidence_discovery_only' using errcode = 'P0422';
  end if;

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

  for v_opt in select * from jsonb_array_elements(coalesce(v_payload->'options', '[]'::jsonb)) loop
    if lower(coalesce(v_opt->>'text', '')) = any(v_opt_texts) then
      raise exception 'duplicate_options' using errcode = 'P0422';
    end if;
    v_opt_texts := v_opt_texts || lower(coalesce(v_opt->>'text', ''));
    insert into public.mock_question_options (question_id, option_text, option_index, is_correct)
    values (v_mock_q_id, v_opt->>'text', v_opt_idx,
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
  update public.mock_question_bank set correct_option_id = v_correct_opt_id where id = v_mock_q_id;

  -- One link row per grounding claim (F5).
  foreach v_claim_id in array v_claim_ids loop
    insert into public.current_affairs_question_links (
      candidate_id, event_id, claim_id, mock_question_id, promoted_by)
    values (p_candidate_id, v_event.id, v_claim_id, v_mock_q_id, p_actor_user_id);
  end loop;

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
    btrim(p_reason))
  returning id into v_audit_id;

  return jsonb_build_object('ok', true, 'audit_id', v_audit_id,
    'mock_question_id', v_mock_q_id, 'candidate_id', p_candidate_id);
end $$;

-- ── Grants: service_role only (new signatures) ─────────────────────────────
revoke all on function public.ca_review_candidate(uuid, text, timestamptz, text, text, text, uuid, text) from public, anon, authenticated;
revoke all on function public.ca_promote_candidate(uuid, text, timestamptz, text, uuid, text) from public, anon, authenticated;
grant execute on function public.ca_review_candidate(uuid, text, timestamptz, text, text, text, uuid, text) to service_role;
grant execute on function public.ca_promote_candidate(uuid, text, timestamptz, text, uuid, text) to service_role;

commit;

notify pgrst, 'reload schema';
