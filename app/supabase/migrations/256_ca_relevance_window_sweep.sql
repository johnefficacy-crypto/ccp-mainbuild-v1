-- 256_ca_relevance_window_sweep.sql
-- GQR-G5b — current-affairs relevance-window retirement sweep.
--
-- The ca:promote-sweep scheduler job calls this to actively ARCHIVE current-affairs
-- events whose editorial relevance window has closed (relevance_until < today). It is
-- defence-in-depth over the existing read-time filters (attempt-start eligibility requires
-- event.status='active' and question valid_until > now): archiving the event flips a
-- durable editorial signal so an expired event can never re-enter a freshly-published
-- bundle. It touches ONLY current_affairs_events.status — it never mutates promoted
-- mock_question_bank rows, bundles, or historical attempts (expiry must never delete or
-- rewrite history). Service-role only; SECURITY DEFINER, search_path pinned.

begin;

create or replace function public.ca_sweep_expired_current_events()
returns integer
language plpgsql security definer set search_path = public as $$
declare
  v_count integer;
begin
  update public.current_affairs_events
    set status = 'archived', updated_at = now()
  where status = 'active'
    and relevance_until is not null
    and relevance_until < current_date;
  get diagnostics v_count = row_count;
  return v_count;
end $$;

revoke all on function public.ca_sweep_expired_current_events() from public, anon, authenticated;
grant execute on function public.ca_sweep_expired_current_events() to service_role;

commit;

notify pgrst, 'reload schema';
