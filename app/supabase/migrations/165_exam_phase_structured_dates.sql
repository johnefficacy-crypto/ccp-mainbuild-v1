-- 165_exam_phase_structured_dates.sql
-- Add structured phase_start / phase_end date columns to exam_phases.
--
-- The existing metadata.phase_window freeform string is preserved; structured
-- columns are populated by an idempotent backfill that parses the
-- operator-documented "24 May 2026" format.  Anything that doesn't parse
-- cleanly is left null and flagged with metadata.phase_window_needs_review=true
-- so operators can fill in the correct dates.  No date is ever guessed.

alter table public.exam_phases
  add column if not exists phase_start date,
  add column if not exists phase_end   date;

-- Idempotent backfill: only rows that have a phase_window string but no
-- structured phase_start yet.  Re-running this block is safe.
do $$
declare
  r      record;
  parsed date;
begin
  for r in
    select id, metadata->>'phase_window' as pw
    from   public.exam_phases
    where  phase_start is null
      and  (metadata->>'phase_window') is not null
      and  (metadata->>'phase_window') not in ('', 'TBD')
  loop
    begin
      -- The canonical operator format documented in SetupPanel is "24 May 2026".
      -- to_date with 'DD Mon YYYY' handles that exact shape.
      parsed := to_date(r.pw, 'DD Mon YYYY');
      update public.exam_phases
         set phase_start = parsed,
             updated_at  = now()
       where id = r.id;
    exception when others then
      -- Anything that doesn't fit: flag for operator review, leave dates null.
      update public.exam_phases
         set metadata   = metadata || '{"phase_window_needs_review": true}'::jsonb,
             updated_at = now()
       where id = r.id;
    end;
  end loop;
end;
$$;

create index if not exists idx_exam_phases_start_end
  on public.exam_phases(phase_start, phase_end)
  where phase_start is not null;

notify pgrst, 'reload schema';
