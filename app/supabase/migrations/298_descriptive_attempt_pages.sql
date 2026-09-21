-- 298_descriptive_attempt_pages.sql
-- Answer writing: handwritten answers, photographed page by page.
--
-- WHY THIS EXISTS. The Mains answer an aspirant will actually write in the exam
-- hall is handwritten, under time, on paper. A typing-only practice surface
-- trains a different skill: it removes the handwriting speed that is half of
-- what the paper tests, and it makes the word count feel free. So an attempt
-- can be answered either way, and the two are kept distinct everywhere.
--
-- NO OCR. Nothing reads these images. They are the aspirant's own record, shown
-- back to them beside the same rubric a typed answer gets. Self-evaluation is
-- the judgement this product supports, and it does not need the text.

create table if not exists public.descriptive_attempt_pages (
  id uuid primary key default gen_random_uuid(),
  attempt_id uuid not null
    references public.descriptive_attempts(id) on delete cascade,

  -- 1-based, in the order the pages were written. Not the upload order: a
  -- re-shot page 3 replaces page 3.
  page_no integer not null check (page_no >= 1 and page_no <= 8),

  storage_bucket text not null,
  storage_path text not null,
  mime_type text not null
    check (mime_type in ('image/jpeg', 'image/png', 'image/heic',
                         'image/heif', 'application/pdf')),
  bytes integer not null check (bytes > 0 and bytes <= 10485760),

  created_at timestamptz not null default now()
);

-- One row per page of an attempt. Re-shooting a page replaces it rather than
-- appending a second image of the same page, which is what an aspirant means
-- when they retake a blurry photo.
create unique index if not exists uq_descriptive_attempt_pages_page
  on public.descriptive_attempt_pages(attempt_id, page_no);

-- A storage object belongs to exactly one page row. Without this a second row
-- could point at the same object and a delete would orphan the survivor.
create unique index if not exists uq_descriptive_attempt_pages_object
  on public.descriptive_attempt_pages(storage_bucket, storage_path);

create index if not exists idx_descriptive_attempt_pages_attempt
  on public.descriptive_attempt_pages(attempt_id, page_no);

comment on table public.descriptive_attempt_pages is
  'Photographed pages of a handwritten answer. Nothing reads them — no OCR, no '
  'AI evaluation. They are shown back to their own author beside the same '
  'self-evaluation rubric a typed answer gets.';

-- ── RLS ──────────────────────────────────────────────────────────────────
-- Ownership is inherited from the attempt, because a page has no user of its
-- own. The EXISTS is against descriptive_attempts, whose own policies already
-- restrict it to auth.uid() — so a page is reachable exactly when its attempt
-- is, and there is one definition of "mine" rather than two that can drift.
alter table public.descriptive_attempt_pages enable row level security;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'descriptive_attempt_pages'
      and policyname = 'descriptive_attempt_pages_owner_select'
  ) then
    create policy descriptive_attempt_pages_owner_select
      on public.descriptive_attempt_pages
      for select to authenticated
      using (
        exists (
          select 1 from public.descriptive_attempts a
          where a.id = descriptive_attempt_pages.attempt_id
            and a.user_id = auth.uid()
        )
      );
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'descriptive_attempt_pages'
      and policyname = 'descriptive_attempt_pages_owner_insert'
  ) then
    create policy descriptive_attempt_pages_owner_insert
      on public.descriptive_attempt_pages
      for insert to authenticated
      with check (
        exists (
          select 1 from public.descriptive_attempts a
          where a.id = descriptive_attempt_pages.attempt_id
            and a.user_id = auth.uid()
        )
      );
  end if;

  -- DELETE, unlike on the attempt itself, is a real operation: re-shooting a
  -- blurry page has to remove the old one, and an aspirant who changes their
  -- mind about uploading must be able to take the images back.
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'descriptive_attempt_pages'
      and policyname = 'descriptive_attempt_pages_owner_delete'
  ) then
    create policy descriptive_attempt_pages_owner_delete
      on public.descriptive_attempt_pages
      for delete to authenticated
      using (
        exists (
          select 1 from public.descriptive_attempts a
          where a.id = descriptive_attempt_pages.attempt_id
            and a.user_id = auth.uid()
        )
      );
  end if;
end $$;

-- An UPDATE policy is deliberately absent, and the privilege is revoked below.
-- A page is an immutable fact: this image, at this position, at this time.
-- Changing it means deleting it and uploading again, which is also what the
-- surface offers.
revoke update, truncate, references, trigger
  on public.descriptive_attempt_pages from authenticated;

-- ── the storage bucket ───────────────────────────────────────────────────
-- PRIVATE. Nothing in this product serves an aspirant's answer over a public
-- URL; every read goes through a short-lived signed URL issued to its owner.
insert into storage.buckets (id, name, public)
values ('answer-pages', 'answer-pages', false)
on conflict (id) do update set public = false;

-- Object paths are `<user_id>/<attempt_id>/page_<n>.<ext>`, so the FIRST path
-- segment is the owner. `storage.foldername(name)` splits the path, and
-- comparing element 1 to auth.uid() is what makes one aspirant's folder
-- unreadable to another — the table policies above protect the ROWS, these
-- protect the BYTES, and a leak needs both to be wrong.
do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'storage' and tablename = 'objects'
      and policyname = 'answer_pages_owner_select'
  ) then
    create policy answer_pages_owner_select
      on storage.objects for select to authenticated
      using (
        bucket_id = 'answer-pages'
        and (storage.foldername(name))[1] = auth.uid()::text
      );
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'storage' and tablename = 'objects'
      and policyname = 'answer_pages_owner_insert'
  ) then
    create policy answer_pages_owner_insert
      on storage.objects for insert to authenticated
      with check (
        bucket_id = 'answer-pages'
        and (storage.foldername(name))[1] = auth.uid()::text
      );
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'storage' and tablename = 'objects'
      and policyname = 'answer_pages_owner_delete'
  ) then
    create policy answer_pages_owner_delete
      on storage.objects for delete to authenticated
      using (
        bucket_id = 'answer-pages'
        and (storage.foldername(name))[1] = auth.uid()::text
      );
  end if;
end $$;

-- ── word_count becomes nullable ──────────────────────────────────────────
-- A handwritten attempt has no word count. Nothing has read the pages, so any
-- number here would be invented — and 0, the current default, would read as
-- "they wrote nothing", which is the opposite of the truth.
--
-- Typed attempts are unaffected: the server still computes their count on every
-- autosave, and the `>= 0` check still holds for every non-null value.
alter table public.descriptive_attempts
  alter column word_count drop not null,
  alter column word_count drop default;

comment on column public.descriptive_attempts.word_count is
  'Words in the typed answer, computed server-side on every save. NULL for a '
  'handwritten attempt: the pages are not read, so there is no count to state.';

notify pgrst, 'reload schema';
