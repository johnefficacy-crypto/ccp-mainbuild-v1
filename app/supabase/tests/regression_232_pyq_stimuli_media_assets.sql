-- regression_232_pyq_stimuli_media_assets.sql
--
-- Manual PostgreSQL regression tests for migration 232's PYQ stimuli media
-- model (PYQ v2 PR-11, slice 1).
--
-- Proves:
--   1. A pending media stimulus linked to a live admin_exam_intelligence asset inserts.
--   2. A wrong-scope linked asset is rejected.
--   3. An archived linked asset is rejected.
--   4. Verifying a media stimulus without alt_text is rejected (accessibility).
--   5. Verifying a media stimulus with alt_text but no content/asset is rejected.
--   6. Verifying a compliant media stimulus (alt_text + asset) succeeds.
--   7. Editing alt_text / document_asset_id / asset_locator on a verified media
--      stimulus downgrades it to needs_correction.
--   8. A non-media (passage) stimulus can be verified without alt_text.
--
-- Prerequisites: migrations 223 + 232 applied.
-- Usage: psql "$DATABASE_URL" -f regression_232_pyq_stimuli_media_assets.sql
-- Expected output: eight NOTICE "PASS" lines, no unexpected errors.

\set ON_ERROR_STOP on

BEGIN;

-- ── Fixture ────────────────────────────────────────────────────────────────
insert into public.exam_families (id, slug, name)
values ('33333333-3333-3333-3333-333333333301'::uuid, 'rg232-family', 'Regression 232 Family');
insert into public.exams (id, exam_family_id, slug, name)
values ('33333333-3333-3333-3333-333333333302'::uuid, '33333333-3333-3333-3333-333333333301'::uuid, 'rg232-exam', 'Regression 232 Exam');
insert into public.pyq_papers (id, exam_id, year, trust_status, source_type)
values ('33333333-3333-3333-3333-333333333303'::uuid, '33333333-3333-3333-3333-333333333302'::uuid, 2025, 'pending', 'official');

-- Three assets: valid admin asset, wrong-scope asset, archived admin asset.
insert into public.document_assets
  (id, scope, document_kind, original_filename, mime_type, storage_bucket, storage_path, content_hash, status)
values
  ('33333333-3333-3333-3333-3333333330a1'::uuid, 'admin_exam_intelligence', 'image', 'venn.png', 'image/png', 'b', 'p/venn.png', 'h1', 'processed'),
  ('33333333-3333-3333-3333-3333333330a2'::uuid, 'personal_library',       'image', 'x.png',    'image/png', 'b', 'p/x.png',    'h2', 'processed'),
  ('33333333-3333-3333-3333-3333333330a3'::uuid, 'admin_exam_intelligence', 'image', 'old.png',  'image/png', 'b', 'p/old.png',  'h3', 'archived');

-- ── Test 1: pending media stimulus with a live admin asset inserts ─────────
insert into public.pyq_stimuli (id, pyq_paper_id, stimulus_type, document_asset_id, alt_text, reviewer_status)
values ('33333333-3333-3333-3333-3333333330c1'::uuid, '33333333-3333-3333-3333-333333333303'::uuid,
        'image', '33333333-3333-3333-3333-3333333330a1'::uuid, 'A Venn diagram of three sets', 'pending');
do $$ begin raise notice 'PASS 1: pending media stimulus with a live admin asset inserts'; end $$;

-- ── Test 2: wrong-scope asset rejected ─────────────────────────────────────
do $$ declare failed boolean := false; begin
  begin
    update public.pyq_stimuli set document_asset_id = '33333333-3333-3333-3333-3333333330a2'::uuid
     where id = '33333333-3333-3333-3333-3333333330c1'::uuid;
  exception when others then failed := true; end;
  if not failed then raise exception 'FAIL 2: wrong-scope asset accepted'; end if;
  raise notice 'PASS 2: wrong-scope linked asset rejected';
end $$;

-- ── Test 3: archived asset rejected ────────────────────────────────────────
do $$ declare failed boolean := false; begin
  begin
    update public.pyq_stimuli set document_asset_id = '33333333-3333-3333-3333-3333333330a3'::uuid
     where id = '33333333-3333-3333-3333-3333333330c1'::uuid;
  exception when others then failed := true; end;
  if not failed then raise exception 'FAIL 3: archived asset accepted'; end if;
  raise notice 'PASS 3: archived linked asset rejected';
end $$;

-- ── Test 4: verify media stimulus without alt_text rejected ────────────────
do $$ declare failed boolean := false; begin
  begin
    update public.pyq_stimuli set reviewer_status = 'verified', alt_text = null
     where id = '33333333-3333-3333-3333-3333333330c1'::uuid;
  exception when others then failed := true; end;
  if not failed then raise exception 'FAIL 4: verified media stimulus without alt_text accepted'; end if;
  raise notice 'PASS 4: verify media stimulus without alt_text rejected';
end $$;

-- ── Test 5: verify media stimulus with alt_text but no content/asset rejected ─
do $$ declare failed boolean := false; begin
  begin
    update public.pyq_stimuli
       set reviewer_status = 'verified', alt_text = 'chart', document_asset_id = null, content_text = null
     where id = '33333333-3333-3333-3333-3333333330c1'::uuid;
  exception when others then failed := true; end;
  if not failed then raise exception 'FAIL 5: verified media stimulus with no content/asset accepted'; end if;
  raise notice 'PASS 5: verify media stimulus without content or asset rejected';
end $$;

-- ── Test 6: compliant media stimulus verifies ──────────────────────────────
update public.pyq_stimuli
   set reviewer_status = 'verified', alt_text = 'A Venn diagram of three sets',
       document_asset_id = '33333333-3333-3333-3333-3333333330a1'::uuid,
       reviewed_by = null, reviewed_at = now()
 where id = '33333333-3333-3333-3333-3333333330c1'::uuid;
do $$ begin
  if (select reviewer_status from public.pyq_stimuli where id = '33333333-3333-3333-3333-3333333330c1'::uuid) <> 'verified' then
    raise exception 'FAIL 6: compliant media stimulus did not verify';
  end if;
  raise notice 'PASS 6: compliant media stimulus verifies';
end $$;

-- ── Test 7: editing media fields on a verified stimulus downgrades ─────────
update public.pyq_stimuli set alt_text = 'A Venn diagram (updated)'
 where id = '33333333-3333-3333-3333-3333333330c1'::uuid;
do $$ begin
  if (select reviewer_status from public.pyq_stimuli where id = '33333333-3333-3333-3333-3333333330c1'::uuid) <> 'needs_correction' then
    raise exception 'FAIL 7: alt_text edit did not downgrade a verified media stimulus';
  end if;
  raise notice 'PASS 7: editing alt_text on a verified media stimulus downgrades to needs_correction';
end $$;

-- ── Test 8: non-media stimulus verifies without alt_text ───────────────────
insert into public.pyq_stimuli (id, pyq_paper_id, stimulus_type, content_text, reviewer_status)
values ('33333333-3333-3333-3333-3333333330c2'::uuid, '33333333-3333-3333-3333-333333333303'::uuid,
        'passage', 'Read the following passage.', 'pending');
update public.pyq_stimuli set reviewer_status = 'verified'
 where id = '33333333-3333-3333-3333-3333333330c2'::uuid;
do $$ begin
  if (select reviewer_status from public.pyq_stimuli where id = '33333333-3333-3333-3333-3333333330c2'::uuid) <> 'verified' then
    raise exception 'FAIL 8: non-media passage stimulus failed to verify without alt_text';
  end if;
  raise notice 'PASS 8: non-media (passage) stimulus verifies without alt_text';
end $$;

ROLLBACK;
