-- 166_phase_window_flag_backfill.sql
-- Close the hole left by migration 165: rows with phase_window = 'TBD' or ''
-- were excluded from both the parse attempt and the needs_review flag, so they
-- became invisible to any tooling that keys off the flag.
--
-- This migration idempotently flags every row that has a non-empty phase_window
-- but no structured phase_start, regardless of format.  Never sets a date.
-- Re-runnable: skips rows already flagged and rows that already have phase_start.

do $$
begin
  update public.exam_phases
     set metadata   = metadata || '{"phase_window_needs_review": true}'::jsonb,
         updated_at = now()
   where phase_start is null
     and nullif(metadata->>'phase_window', '') is not null
     and (metadata->>'phase_window_needs_review') is distinct from 'true';
end;
$$;

notify pgrst, 'reload schema';
