-- 131_remove_untracked_rls_auto_enable.sql
-- Removes a live-only ``ensure_rls`` event trigger and its
-- ``public.rls_auto_enable()`` backing function that were created directly in
-- the Supabase SQL editor and have no definition anywhere in this repo.
--
-- An on-ddl_command_end event trigger that auto-enables RLS on every new
-- table is surprising untracked behaviour: it makes ``create table`` in a
-- migration silently RLS-locked with zero policies, which is exactly the
-- drift catalogued in docs/schema/rls-policy-drift-audit.md. RLS is instead
-- managed explicitly per table in migrations.
--
-- Repo grep confirmed ZERO references before writing this removal migration:
--   rg -i 'rls_auto_enable|ensure_rls|ddl_command_end|pg_event_trigger|event trigger'
--   -> no matches in *.sql or *.py
--
-- Idempotent: drop ... if exists is a no-op on a clean DB that never had
-- these objects.

drop event trigger if exists ensure_rls;
drop function if exists public.rls_auto_enable();

notify pgrst, 'reload schema';
