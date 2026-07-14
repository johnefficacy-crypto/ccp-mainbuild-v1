-- GQR-S2 — Quant content-readiness VERIFY-DB proof (rollback-only, self-contained).
--
-- Proves the end-to-end governed readiness path WITHOUT a migration, using only
-- existing paths: service-role INSERT into the authority tables + the existing
-- cms_review_quant_heuristic lifecycle RPC (migration 246) to reach verified.
--
-- Asserted invariants (the GQR-S2 data/operator gate):
--   1. A reviewed (verified+active) heuristic with a verified link appears in the
--      conjunctive learner-ready read.
--   2. Moving the LINK out of verified makes it disappear on the next read.
--   3. Restoring the link, then retiring the HEURISTIC (is_active=false via edit,
--      then needs_correction via the review RPC) each make it disappear.
--   4. The review RPC enforces its guards (bad reason rejected).
--
-- Rollback-only; leaves no data. Requires service_role / superuser (the tables
-- are service-role-only and the RPC is SECURITY DEFINER granted to service_role).
--
-- Manual run:
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
--     -f app/supabase/validation/validate_quant_heuristic_readiness.sql

begin;

-- Real actor so reviewed_by / created_by FKs → auth.users resolve.
insert into auth.users (id, instance_id, aud, role, email)
values ('eeeeeeee-0000-0000-0000-000000000502'::uuid,
        '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated',
        'quant-verify@example.com')
on conflict (id) do nothing;

-- Self-contained Quant fixtures (subject → topic → bank question).
insert into public.subjects (id, slug, name, subject_group)
values ('55550000-0000-0000-0000-000000000502'::uuid, 'quant-verify', 'Quant (verify)', 'numerical')
on conflict (id) do nothing;

insert into public.topics (id, subject_id, slug, name, level)
values ('66660000-0000-0000-0000-000000000502'::uuid, '55550000-0000-0000-0000-000000000502'::uuid,
        'percentage-verify', 'Percentage (verify)', 'topic')
on conflict (id) do nothing;

insert into public.mock_question_bank (id, question_text, question_type, reviewer_status)
values ('b1110000-0000-0000-0000-000000000502'::uuid,
        'A number increased by 20% then decreased by 20% — net change?', 'mcq', 'reviewed')
on conflict (id) do nothing;

-- Author a heuristic (pending) + assign it to the question (link pending) — the
-- governed intake path is a service-role INSERT; verification is the RPC below.
insert into public.quant_heuristics
  (id, topic_id, heuristic_code, name, heuristic_type, applicability_rule,
   shortcut_method, worked_example, reviewer_status, is_active, created_by)
values ('a0000000-0000-0000-0000-000000000502'::uuid,
        '66660000-0000-0000-0000-000000000502'::uuid,
        'QH-VERIFY-SUCCESSIVE-PCT', 'Successive percentage change',
        'shortcut', '{"pattern": "successive_percentage"}'::jsonb,
        'net% = a + b + a*b/100 (signed)', '+20% then -20% → 20 - 20 - 400/100 = -4%',
        'pending', true, 'eeeeeeee-0000-0000-0000-000000000502'::uuid)
on conflict (id) do nothing;

insert into public.quant_question_heuristics
  (id, question_id, heuristic_id, relevance, reviewer_status)
values ('11110000-0000-0000-0000-000000000502'::uuid,
        'b1110000-0000-0000-0000-000000000502'::uuid,
        'a0000000-0000-0000-0000-000000000502'::uuid, 'primary', 'pending')
on conflict (id) do nothing;

-- ── The conjunctive learner-ready read, expressed once as a reusable check. ──
create function pg_temp._qh_ready(p_question uuid) returns int
language sql as $$
  select count(*)::int
  from public.quant_question_heuristics l
  join public.quant_heuristics h on h.id = l.heuristic_id
  where l.question_id = p_question
    and l.reviewer_status = 'verified'
    and h.reviewer_status = 'verified'
    and h.is_active = true;
$$;

do $$
declare
  v_q   constant uuid := 'b1110000-0000-0000-0000-000000000502'::uuid;
  v_h   constant uuid := 'a0000000-0000-0000-0000-000000000502'::uuid;
  v_l   constant uuid := '11110000-0000-0000-0000-000000000502'::uuid;
  v_act constant uuid := 'eeeeeeee-0000-0000-0000-000000000502'::uuid;
  v_tok timestamptz;
begin
  -- Pending heuristic → not ready yet.
  if pg_temp._qh_ready(v_q) <> 0 then raise exception 'FAIL: pending heuristic must not be learner-ready'; end if;
  raise notice 'PASS pending heuristic is not learner-ready';

  -- Bad reason is rejected by the RPC (governance guard).
  begin
    select updated_at into v_tok from public.quant_heuristics where id = v_h;
    perform public.cms_review_quant_heuristic(v_h, 'pending', v_tok, 'verified', null, 'short', v_act, 'op@example.com');
    raise exception 'FAIL: short reason should be rejected';
  exception when others then
    if sqlerrm not like 'invalid_reason%' then raise; end if;
    raise notice 'PASS review reason gate';
  end;

  -- Verify the heuristic via the governed RPC (pending → verified).
  select updated_at into v_tok from public.quant_heuristics where id = v_h;
  perform public.cms_review_quant_heuristic(
    v_h, 'pending', v_tok, 'verified', null, 'clear, correct successive-% shortcut', v_act, 'op@example.com');

  -- Heuristic verified but link still pending → still not ready (defense in depth).
  if pg_temp._qh_ready(v_q) <> 0 then raise exception 'FAIL: unverified link must gate a verified heuristic'; end if;
  raise notice 'PASS verified heuristic + pending link is not learner-ready';

  -- Verify the link (governed assignment path = service-role UPDATE; links carry
  -- their own reviewer_status but have no separate RPC in v1).
  update public.quant_question_heuristics
    set reviewer_status = 'verified', reviewed_by = v_act, reviewed_at = now()
    where id = v_l;

  -- Now fully verified + active → appears.
  if pg_temp._qh_ready(v_q) <> 1 then raise exception 'FAIL: double-verified active heuristic must be learner-ready'; end if;
  raise notice 'PASS double-verified active heuristic IS learner-ready';

  -- Move the LINK out of verified → disappears.
  update public.quant_question_heuristics set reviewer_status = 'rejected' where id = v_l;
  if pg_temp._qh_ready(v_q) <> 0 then raise exception 'FAIL: rejecting the link must remove the surface'; end if;
  raise notice 'PASS rejecting the link removes the surface';
  update public.quant_question_heuristics set reviewer_status = 'verified' where id = v_l;

  -- Retire the HEURISTIC (edit is_active=false) → disappears even with a verified link.
  update public.quant_heuristics set is_active = false, updated_at = now() where id = v_h;
  if pg_temp._qh_ready(v_q) <> 0 then raise exception 'FAIL: retiring (is_active=false) must remove the surface'; end if;
  raise notice 'PASS retiring the heuristic removes the surface';
  update public.quant_heuristics set is_active = true, updated_at = now() where id = v_h;

  -- Reopen the HEURISTIC for correction via the RPC (verified → needs_correction) → disappears.
  select updated_at into v_tok from public.quant_heuristics where id = v_h;
  perform public.cms_review_quant_heuristic(
    v_h, 'verified', v_tok, 'needs_correction', 'applicability rule under review',
    'reopening to re-verify the applicability rule', v_act, 'op@example.com');
  if pg_temp._qh_ready(v_q) <> 0 then raise exception 'FAIL: needs_correction must remove the surface'; end if;
  raise notice 'PASS needs_correction removes the surface';
end $$;

do $$ begin raise notice 'ALL PASS — Quant content readiness proven'; end $$;

rollback;
