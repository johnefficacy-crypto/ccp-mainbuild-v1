-- 255_current_affairs_attempt_start_hardening.sql
-- GQR-G5a hardening (checkpost #976 rounds 2 + 3) — forward migration over immutable 253.
--
-- Makes the published bundle an immutable, scope-checked, provenance-INTEGRITY-verified
-- authority and the frozen attempt a bank-verified, drift-proof snapshot (never trusts
-- caller JSON):
--   R2-F1 scope shape — exact XOR family XOR global (mutually exclusive columns).
--   R2/R3-F1 no drift — membership FK RESTRICT (a bank delete can't silently shrink a
--      bundle), membership is LOCKED while published (mutations forced through draft →
--      republish), and each attempt is bound to a membership fingerprint that changes
--      whenever the ordered set changes.
--   R2/R3-F2 content authority — start verifies each frozen snapshot's question text,
--      explanation, correct option, and per-option id+text against the LOCKED bank rows,
--      binding the bank content revision — a caller cannot swap option text under a
--      stable id, nor freeze a stale snapshot.
--   R2/R3-F3 provenance integrity — eligibility proves the FULL promoted relation:
--      event-id consistency (link/claim/bank), verified+current claim, active+relevant
--      event, and an active non-discovery_only source (ADR-0007) — not mere existence.
--   R3-F4 scope can't widen — bundle exam/family FKs become RESTRICT (deleting the exam/
--      family can't silently convert a published scoped bundle to global), and the
--      attempt's exam_id becomes a real FK (no dangling exam identifiers).
--
-- 253 is landed/immutable, so this ALTERs the tables and CREATE OR REPLACEs the two
-- functions in place (signatures unchanged → existing service_role grants are retained).

begin;

-- ── R2-F1: scope shape — never both exact- and family-scoped ───────────────
alter table public.current_affairs_bundles
  drop constraint if exists cab_scope_shape;
alter table public.current_affairs_bundles
  add constraint cab_scope_shape check (exam_id is null or exam_family_id is null);

-- ── R3-F1: membership FK RESTRICT — a bank delete can't silently shrink a bundle
alter table public.current_affairs_bundle_questions
  drop constraint if exists current_affairs_bundle_questions_mock_question_id_fkey;
alter table public.current_affairs_bundle_questions
  add constraint current_affairs_bundle_questions_mock_question_id_fkey
  foreign key (mock_question_id) references public.mock_question_bank(id) on delete restrict;

-- ── R3-F4: scope FKs RESTRICT — deleting the exam/family can't widen a published
--    bundle to global; attempt.exam_id becomes a real FK (no dangling identifiers).
alter table public.current_affairs_bundles
  drop constraint if exists current_affairs_bundles_exam_id_fkey;
alter table public.current_affairs_bundles
  drop constraint if exists current_affairs_bundles_exam_family_id_fkey;
alter table public.current_affairs_bundles
  add constraint current_affairs_bundles_exam_id_fkey
    foreign key (exam_id) references public.exams(id) on delete restrict;
alter table public.current_affairs_bundles
  add constraint current_affairs_bundles_exam_family_id_fkey
    foreign key (exam_family_id) references public.exam_families(id) on delete restrict;

alter table public.current_affairs_attempts
  add column if not exists membership_revision text;
alter table public.current_affairs_attempts
  drop constraint if exists current_affairs_attempts_exam_id_fkey;
alter table public.current_affairs_attempts
  add constraint current_affairs_attempts_exam_id_fkey
    foreign key (exam_id) references public.exams(id) on delete set null;

-- ── R3-F1: membership is immutable while a bundle is published ──────────────
-- Order / membership / inclusion edits must go through draft → republish, so a published
-- bundle id + membership fingerprint uniquely identify one ordered question set.
create or replace function public.ca_guard_bundle_membership_mutation()
returns trigger language plpgsql security definer set search_path = public as $$
declare v_status text;
begin
  select status into v_status from public.current_affairs_bundles
    where id = coalesce(new.bundle_id, old.bundle_id);
  if v_status = 'published' then
    raise exception 'bundle_membership_locked_when_published' using errcode = 'P0409';
  end if;
  return coalesce(new, old);
end $$;

drop trigger if exists ca_bundle_membership_guard on public.current_affairs_bundle_questions;
create trigger ca_bundle_membership_guard
  before insert or update or delete on public.current_affairs_bundle_questions
  for each row execute function public.ca_guard_bundle_membership_mutation();

-- ── R3-F3: eligibility proves the FULL promoted relation (not mere existence) ─
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
        and ql.event_id = q.current_affairs_item_id      -- link ↔ bank event consistency
        and cl.event_id = q.current_affairs_item_id      -- claim ↔ bank event consistency
        and cl.reviewer_status = 'verified'
        and cl.factual_status = 'current'                -- not rejected/corrected/superseded
        and ev.status = 'active'
        and (ev.relevance_until is null or ev.relevance_until >= current_date)
        and s.is_active = true
        and s.authority_level in ('primary_official', 'official_secondary')  -- ADR-0007
    )
  order by bq.display_order, bq.mock_question_id
$$;

-- ── R2/R3 F1/F2/F3: scope-gated, drift-proof, content-verified start ────────
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
  v_qid uuid;
  v_family uuid;
  v_raw uuid[];
  v_authoritative uuid[];
  v_caller uuid[];
  v_membership_rev text;
  v_bank_correct uuid;
  v_bank_rev timestamptz;
  v_bank_qtext text;
  v_bank_expl text;
  v_bank_opts text[];
  v_snap_opts text[];
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

  -- Scope gate: prove the bundle is actually servable to this learner's exam.
  select exam_family_id into v_family from public.exams where id = p_exam;
  if v_bundle.exam_id is not null then
    if v_bundle.exam_id is distinct from p_exam then
      raise exception 'bundle_scope_mismatch: exam' using errcode = 'P0403';
    end if;
  elsif v_bundle.exam_family_id is not null then
    if v_family is null or v_bundle.exam_family_id is distinct from v_family then
      raise exception 'bundle_scope_mismatch: family' using errcode = 'P0403';
    end if;
  end if;  -- else global: servable to any exam.

  -- Lock membership + referenced bank rows + their options so nothing races after read.
  perform 1 from public.current_affairs_bundle_questions where bundle_id = p_bundle for update;
  perform 1 from public.mock_question_bank
    where id in (select mock_question_id from public.current_affairs_bundle_questions
                 where bundle_id = p_bundle) for update;
  perform 1 from public.mock_question_options
    where question_id in (select mock_question_id from public.current_affairs_bundle_questions
                          where bundle_id = p_bundle) for update;

  -- Raw membership vs authoritative (eligible + provenance-integrity-verified) membership.
  select array_agg(mock_question_id order by display_order, mock_question_id) into v_raw
    from public.current_affairs_bundle_questions where bundle_id = p_bundle;
  if v_raw is null or array_length(v_raw, 1) is null then
    raise exception 'empty_bundle' using errcode = 'P0422';
  end if;
  select array_agg(mock_question_id order by display_order, mock_question_id)
    into v_authoritative
  from public.ca_eligible_bundle_question_ids(p_bundle);
  -- A published bundle whose raw members are not ALL still-eligible has degraded and must
  -- be re-published — refuse rather than silently serve a shrunken attempt.
  if v_authoritative is null or v_authoritative <> v_raw then
    raise exception 'bundle_degraded' using errcode = 'P0409';
  end if;
  -- Membership fingerprint: changes whenever the ordered set changes (drift binding).
  v_membership_rev := md5(array_to_string(v_authoritative, ','));

  -- Caller-frozen ids must equal the authoritative set IN ORDER (no missing/extra/reorder).
  select array_agg((elem->>'question_id')::uuid order by ord)
    into v_caller
  from jsonb_array_elements(coalesce(p_response_rows, '[]'::jsonb)) with ordinality as t(elem, ord);
  if v_caller is distinct from v_authoritative then
    raise exception 'bundle_set_mismatch' using errcode = 'P0409';
  end if;

  -- Verify each frozen snapshot against the authoritative (locked) bank row + options —
  -- text, explanation, correct option, and per-option id+text, not just the id set.
  for v_row in select * from jsonb_array_elements(p_response_rows) loop
    v_qid := (v_row->>'question_id')::uuid;
    select question_text, explanation, correct_option_id, updated_at
      into v_bank_qtext, v_bank_expl, v_bank_correct, v_bank_rev
      from public.mock_question_bank where id = v_qid;
    if (v_row->'question_snapshot'->>'question_text') is distinct from v_bank_qtext then
      raise exception 'snapshot_text_mismatch' using errcode = 'P0409';
    end if;
    if (v_row->'question_snapshot'->>'explanation') is distinct from v_bank_expl then
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
    -- Per-option TEXT must match the bank (defeats a text swap under a stable id).
    if exists (
      select 1
      from jsonb_array_elements(v_row->'question_snapshot'->'options') o
      left join public.mock_question_options mo
        on mo.id = (o->>'id')::uuid and mo.question_id = v_qid
      where mo.id is null or mo.option_text is distinct from (o->>'option_text')
    ) then
      raise exception 'snapshot_options_mismatch' using errcode = 'P0409';
    end if;
  end loop;

  -- Conflict-safe idempotent create: concurrent starts collapse to one attempt.
  insert into public.current_affairs_attempts (
    user_id, exam_id, bundle_id, cadence, period_start, period_end,
    status, template_snapshot, total_questions, membership_revision)
  values (
    p_user, p_exam, p_bundle, v_bundle.cadence, v_bundle.period_start, v_bundle.period_end,
    'in_progress',
    coalesce(p_template_snapshot, '{}'::jsonb)
      || jsonb_build_object('bundle_revision', v_bundle.updated_at,
                            'membership_revision', v_membership_rev),
    array_length(v_authoritative, 1), v_membership_rev)
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

  -- Freeze each response IN DISPLAY ORDER, binding the bank content revision.
  for v_row in
    select elem from jsonb_array_elements(p_response_rows) with ordinality as t(elem, ord) order by ord
  loop
    v_qid := (v_row->>'question_id')::uuid;
    select updated_at into v_bank_rev from public.mock_question_bank where id = v_qid;
    insert into public.current_affairs_attempt_responses (
      attempt_id, mock_question_id, question_snapshot)
    values (v_attempt_id, v_qid,
      (v_row->'question_snapshot') || jsonb_build_object('content_revision', v_bank_rev));
  end loop;

  return jsonb_build_object('outcome', 'ready', 'attempt_id', v_attempt_id,
    'question_count', array_length(v_authoritative, 1));
end $$;

commit;

notify pgrst, 'reload schema';
