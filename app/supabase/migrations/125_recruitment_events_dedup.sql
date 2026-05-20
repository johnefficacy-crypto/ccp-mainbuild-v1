-- 125_recruitment_events_dedup.sql
-- Stop recruitment_events write amplification.
--
-- Aggregator re-discovery INSERTed the same lifecycle link on every pass:
-- a reference run wrote 191 recruitment_events rows, ~184 of them from a
-- single source re-seeing the same URLs. There is no natural key on the
-- table, so nothing stopped the dupes.
--
-- recruitment_events has NO url column — the discovered link lives in
-- ``payload->>'discovered_url'`` (written by runner._record_lifecycle_event).
-- So the dedup key is (source_id, event_type, payload->>'discovered_url'),
-- materialised as a STORED generated ``event_hash`` with a UNIQUE index.
-- The runner switches the INSERT to an upsert(on_conflict=event_hash,
-- ignore_duplicates=true), making a re-seen link a no-op.

-- up
begin;

alter table public.recruitment_events
  add column if not exists event_hash text generated always as (
    encode(
      sha256(
        (coalesce(source_id::text, '') || '|' ||
         coalesce(event_type, '')      || '|' ||
         coalesce(payload->>'discovered_url', ''))::bytea
      ),
      'hex'
    )
  ) stored;

-- Collapse pre-existing duplicates BEFORE the unique index, else its
-- creation fails on the historical dupes. Keep the earliest row per hash
-- (recruitment_events is a leaf table — nothing references it — so deleting
-- the redundant copies is safe).
delete from public.recruitment_events
where id not in (
  select distinct on (event_hash) id
  from public.recruitment_events
  order by event_hash, created_at asc, id asc
);

create unique index if not exists uq_recruitment_events_dedup
  on public.recruitment_events(event_hash);

commit;

notify pgrst, 'reload schema';

-- down (manual only — do not auto-run on rollback)
-- drop index if exists public.uq_recruitment_events_dedup;
-- alter table public.recruitment_events drop column if exists event_hash;
