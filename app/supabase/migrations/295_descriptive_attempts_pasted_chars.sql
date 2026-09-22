-- 295_descriptive_attempts_pasted_chars.sql
-- Answer writing: record how much of an answer was pasted, and narrow the
-- grants on descriptive_attempts to what the surface actually performs.
--
-- WHY PASTED CHARS
-- The whole value of this surface is that the aspirant wrote the answer. An
-- answer pasted from a model answer scores well against the rubric and teaches
-- nothing, and six months later the history is the only record of which was
-- which. This is NOT a policing signal and nothing reads it to gate anything:
-- it is shown back to its own author, on their own attempt, as "contains pasted
-- text". Honest self-review needs an honest record of what was written.
--
-- The count is characters received by paste events, summed by the client and
-- sent with every autosave. It is therefore an aspirant-reported number, like
-- the self-scores beside it; the server only refuses to let it go DOWN.
--
-- Null, not 0, for existing rows: every attempt written before this column
-- existed has an unknown paste history, and claiming 0 would assert something
-- nobody measured. The UI shows the line only for 0-and-above.
alter table public.descriptive_attempts
  add column if not exists pasted_chars integer null
    check (pasted_chars is null or pasted_chars >= 0);

comment on column public.descriptive_attempts.pasted_chars is
  'Characters entered by paste, summed client-side and sent with each autosave. '
  'The server keeps max(existing, incoming), so a restarted or out-of-order '
  'client can never lower it. Null means the attempt predates paste tracking. '
  'Self-reported and never used to gate anything.';

-- ── grants ───────────────────────────────────────────────────────────────
-- This table has exactly three operations: the aspirant reads their attempts,
-- opens one, and saves into it. Nothing in the product deletes an attempt, and
-- the history is the point of the surface — a submitted attempt is the record
-- of what was written under time.
--
-- 293 relied on the schema-wide default grant, which hands `authenticated`
-- every privilege the table has. RLS then constrains WHICH rows a delete could
-- reach, but not whether delete exists at all: any aspirant's own token could
-- erase their entire answer history in one request, and a bug or a hostile
-- page could do it for them. REFERENCES and TRIGGER are worse in kind — they
-- let a client attach objects to a table it only ever reads three columns of.
--
-- SELECT, INSERT and UPDATE stay exactly as they are, still under the owner
-- policies from 293.
revoke delete, truncate, references, trigger
  on public.descriptive_attempts from authenticated;

-- The owner DELETE policy from 293 is left in place deliberately, and is now
-- unreachable: with no delete privilege there is no statement for it to filter.
-- Restoring deletes is then a single GRANT rather than a policy that has to be
-- written correctly again from memory.

notify pgrst, 'reload schema';
