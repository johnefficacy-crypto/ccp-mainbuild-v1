-- regression_270_pyq_projection_microtopic.sql
--
-- Manual PostgreSQL regression tests for Migration 270
-- (project_pyq_question_to_mock_bank: microtopic fidelity).
--
-- Before 270 the projection wrote only `topic_id`, set verbatim from the
-- verified primary tag, so a tag pointing at a MICROTOPIC was flattened into
-- `topic_id` and `mock_question_bank.microtopic_id` stayed NULL.
--
-- Proves:
--   1. Primary tag is a MICROTOPIC -> microtopic_id = the tagged topic,
--      topic_id = that row's parent_topic_id.
--   2. Primary tag is a TOP-LEVEL topic -> topic_id = the tagged topic,
--      microtopic_id IS NULL.
--   3. NO verified primary tag -> the RPC blocks with
--      'primary_topic_tag_count_not_one' and writes no bank row.
--   4. Re-projecting an UNCHANGED microtopic question returns 'unchanged'
--      (the microtopic in the hash does not break idempotency).
--   5. Re-tagging a question to a SIBLING microtopic under the same parent
--      re-hashes, re-projects ('updated'), and lands the new microtopic while
--      topic_id stays the parent.
--
--      Honest scope note: the content hash already carried every verified
--      tag's topic_id Before 270, so a tag MOVE was already detected. What
--      the appended microtopic_id adds is that the hash now commits to the
--      value actually written to `mock_question_bank.microtopic_id`. It does
--      NOT cover a topics-tree RE-PARENT (the tag is unchanged, so the tag
--      aggregate is unchanged, yet the projected topic_id would change) —
--      closing that would require the resolved topic_id in the hash too, and
--      is out of scope for this migration.
--   6. The projection is idempotent after the re-tag: a second call on the
--      settled row returns 'unchanged' and the same mock_question_id.
--
-- Prerequisites:
--   Migrations up to and including 270 must be applied.
--
-- Usage:
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f regression_270_pyq_projection_microtopic.sql
--
-- Expected output: six NOTICE "PASS" lines, no unexpected errors.
-- Rollback-only; leaves no data behind. Never run this against production.

\set ON_ERROR_STOP on

BEGIN;

-- ── Fixture ────────────────────────────────────────────────────────────────

-- Real actor: mock_question_bank.created_by -> auth.users(id) (migration 136).
insert into auth.users (id, instance_id, aud, role, email)
values ('cccccccc-0000-0000-0000-000000000001'::uuid,
        '00000000-0000-0000-0000-000000000000'::uuid, 'authenticated', 'authenticated',
        'rg268-actor@example.com')
on conflict (id) do nothing;

insert into public.exam_families (id, slug, name)
values ('cccccccc-0000-0000-0000-000000000002'::uuid, 'rg268-family', 'regression 270 Family');

insert into public.exams (id, exam_family_id, slug, name)
values ('cccccccc-0000-0000-0000-000000000003'::uuid,
        'cccccccc-0000-0000-0000-000000000002'::uuid, 'rg268-exam', 'regression 270 Exam');

insert into public.subjects (id, slug, name)
values ('cccccccc-0000-0000-0000-000000000004'::uuid, 'rg268-subject', 'regression 270 Subject');

-- Two-level taxonomy: one top-level topic with two microtopic children.
insert into public.topics (id, subject_id, parent_topic_id, slug, name, level)
values
  ('cccccccc-0000-0000-0000-000000000010'::uuid,
   'cccccccc-0000-0000-0000-000000000004'::uuid, null,
   'rg268-parent', 'regression 270 Parent Topic', 'topic'),
  ('cccccccc-0000-0000-0000-000000000011'::uuid,
   'cccccccc-0000-0000-0000-000000000004'::uuid,
   'cccccccc-0000-0000-0000-000000000010'::uuid,
   'rg268-micro-a', 'regression 270 Microtopic A', 'microtopic'),
  ('cccccccc-0000-0000-0000-000000000012'::uuid,
   'cccccccc-0000-0000-0000-000000000004'::uuid,
   'cccccccc-0000-0000-0000-000000000010'::uuid,
   'rg268-micro-b', 'regression 270 Microtopic B', 'microtopic');

insert into public.pyq_papers (id, exam_id, year, trust_status, source_type)
values ('cccccccc-0000-0000-0000-000000000020'::uuid,
        'cccccccc-0000-0000-0000-000000000003'::uuid, 2025, 'verified', 'official');

-- Three questions: microtopic-tagged, topic-tagged, untagged.
insert into public.pyq_questions
  (id, pyq_paper_id, question_number, question_text, question_type, reviewer_status)
values
  ('cccccccc-0000-0000-0000-000000000031'::uuid,
   'cccccccc-0000-0000-0000-000000000020'::uuid, 1,
   'regression 270 question tagged at microtopic level.', 'mcq', 'verified'),
  ('cccccccc-0000-0000-0000-000000000032'::uuid,
   'cccccccc-0000-0000-0000-000000000020'::uuid, 2,
   'regression 270 question tagged at top-level topic.', 'mcq', 'verified'),
  ('cccccccc-0000-0000-0000-000000000033'::uuid,
   'cccccccc-0000-0000-0000-000000000020'::uuid, 3,
   'regression 270 question with no primary tag.', 'mcq', 'verified');

-- Two verified options each, exactly one correct (the RPC's projection gate).
insert into public.pyq_options
  (question_id, option_label, option_text, is_correct, reviewer_status)
select q.id, l.label, 'regression 270 option ' || l.label, (l.label = 'A'), 'verified'
from (values
        ('cccccccc-0000-0000-0000-000000000031'::uuid),
        ('cccccccc-0000-0000-0000-000000000032'::uuid),
        ('cccccccc-0000-0000-0000-000000000033'::uuid)
     ) as q(id)
cross join (values ('A'), ('B')) as l(label);

insert into public.pyq_question_topic_tags
  (question_id, topic_id, tag_role, reviewer_status)
values
  -- Q31: primary tag points at MICROTOPIC A.
  ('cccccccc-0000-0000-0000-000000000031'::uuid,
   'cccccccc-0000-0000-0000-000000000011'::uuid, 'primary', 'verified'),
  -- Q32: primary tag points at the TOP-LEVEL topic.
  ('cccccccc-0000-0000-0000-000000000032'::uuid,
   'cccccccc-0000-0000-0000-000000000010'::uuid, 'primary', 'verified'),
  -- Q33: only a SECONDARY tag — no verified primary.
  ('cccccccc-0000-0000-0000-000000000033'::uuid,
   'cccccccc-0000-0000-0000-000000000010'::uuid, 'secondary', 'verified');

-- ── Tests ──────────────────────────────────────────────────────────────────

do $$
declare
  v_actor      uuid := 'cccccccc-0000-0000-0000-000000000001'::uuid;
  v_parent     uuid := 'cccccccc-0000-0000-0000-000000000010'::uuid;
  v_micro_a    uuid := 'cccccccc-0000-0000-0000-000000000011'::uuid;
  v_micro_b    uuid := 'cccccccc-0000-0000-0000-000000000012'::uuid;
  v_q_micro    uuid := 'cccccccc-0000-0000-0000-000000000031'::uuid;
  v_q_topic    uuid := 'cccccccc-0000-0000-0000-000000000032'::uuid;
  v_q_untagged uuid := 'cccccccc-0000-0000-0000-000000000033'::uuid;

  v_res       jsonb;
  v_row       record;
  v_hash_before text;
  v_hash_after  text;
  v_mock_id_before uuid;
begin
  -- ── Test 1: microtopic tag splits into parent topic + microtopic ─────────
  v_res := public.project_pyq_question_to_mock_bank(
    v_q_micro, v_actor, 'regression 270 microtopic projection');

  if v_res ->> 'outcome' <> 'created' then
    raise exception 'FAIL test 1: expected outcome=created, got %', v_res;
  end if;

  select topic_id, microtopic_id into v_row
  from public.mock_question_bank
  where id = (v_res ->> 'mock_question_id')::uuid;

  if v_row.microtopic_id is distinct from v_micro_a then
    raise exception 'FAIL test 1: microtopic_id expected %, got %', v_micro_a, v_row.microtopic_id;
  end if;
  if v_row.topic_id is distinct from v_parent then
    raise exception 'FAIL test 1: topic_id expected the PARENT %, got %', v_parent, v_row.topic_id;
  end if;
  raise notice 'PASS test 1: microtopic tag -> microtopic_id = tag, topic_id = parent_topic_id';

  v_hash_before    := v_res ->> 'content_hash';
  v_mock_id_before := (v_res ->> 'mock_question_id')::uuid;

  -- ── Test 2: top-level tag keeps topic_id and leaves microtopic_id NULL ───
  v_res := public.project_pyq_question_to_mock_bank(
    v_q_topic, v_actor, 'regression 270 top-level topic projection');

  if v_res ->> 'outcome' <> 'created' then
    raise exception 'FAIL test 2: expected outcome=created, got %', v_res;
  end if;

  select topic_id, microtopic_id into v_row
  from public.mock_question_bank
  where id = (v_res ->> 'mock_question_id')::uuid;

  if v_row.topic_id is distinct from v_parent then
    raise exception 'FAIL test 2: topic_id expected %, got %', v_parent, v_row.topic_id;
  end if;
  if v_row.microtopic_id is not null then
    raise exception 'FAIL test 2: microtopic_id expected NULL, got %', v_row.microtopic_id;
  end if;
  raise notice 'PASS test 2: top-level tag -> topic_id = tag, microtopic_id IS NULL';

  -- ── Test 3: no verified primary tag blocks, and writes no bank row ───────
  v_res := public.project_pyq_question_to_mock_bank(
    v_q_untagged, v_actor, 'regression 270 untagged projection');

  if v_res ->> 'outcome' <> 'blocked'
     or v_res ->> 'reason' <> 'primary_topic_tag_count_not_one' then
    raise exception 'FAIL test 3: expected blocked/primary_topic_tag_count_not_one, got %', v_res;
  end if;
  if exists (select 1 from public.mock_question_bank where pyq_question_id = v_q_untagged) then
    raise exception 'FAIL test 3: a bank row was written for a question with no primary tag';
  end if;
  raise notice 'PASS test 3: no verified primary tag -> blocked, no bank row';

  -- ── Test 4: unchanged microtopic question stays idempotent ───────────────
  v_res := public.project_pyq_question_to_mock_bank(
    v_q_micro, v_actor, 'regression 270 idempotent re-projection');

  if v_res ->> 'outcome' <> 'unchanged' then
    raise exception 'FAIL test 4: expected outcome=unchanged, got %', v_res;
  end if;
  if v_res ->> 'content_hash' is distinct from v_hash_before then
    raise exception 'FAIL test 4: hash drifted on an unchanged re-projection';
  end if;
  raise notice 'PASS test 4: unchanged microtopic question re-projects as unchanged';

  -- ── Test 5: moving the tag to a SIBLING microtopic re-projects ───────────
  -- The projected topic_id does not change (same parent), so only
  -- microtopic_id distinguishes the two states on the bank row. The hash
  -- changes on two counts after 270 — the verified-tag aggregate (which
  -- already carried the tag's topic_id Before 270) and the appended
  -- microtopic_id — and the row must land on the NEW microtopic.
  update public.pyq_question_topic_tags
  set topic_id = v_micro_b
  where question_id = v_q_micro and tag_role = 'primary';

  v_res := public.project_pyq_question_to_mock_bank(
    v_q_micro, v_actor, 'regression 270 microtopic re-tag re-projection');

  if v_res ->> 'outcome' <> 'updated' then
    raise exception 'FAIL test 5: expected outcome=updated after a microtopic re-tag, got %', v_res;
  end if;

  v_hash_after := v_res ->> 'content_hash';
  if v_hash_after = v_hash_before then
    raise exception 'FAIL test 5: content hash did not change when the microtopic moved';
  end if;

  select topic_id, microtopic_id into v_row
  from public.mock_question_bank
  where id = (v_res ->> 'mock_question_id')::uuid;

  if v_row.microtopic_id is distinct from v_micro_b then
    raise exception 'FAIL test 5: microtopic_id expected %, got %', v_micro_b, v_row.microtopic_id;
  end if;
  if v_row.topic_id is distinct from v_parent then
    raise exception 'FAIL test 5: topic_id must stay the parent %, got %', v_parent, v_row.topic_id;
  end if;
  raise notice 'PASS test 5: microtopic re-tag re-hashes and re-projects (updated)';

  -- ── Test 6: settled row is idempotent again, same mock question id ───────
  v_res := public.project_pyq_question_to_mock_bank(
    v_q_micro, v_actor, 'regression 270 post-retag idempotency');

  if v_res ->> 'outcome' <> 'unchanged' then
    raise exception 'FAIL test 6: expected outcome=unchanged, got %', v_res;
  end if;
  if (v_res ->> 'mock_question_id')::uuid is distinct from v_mock_id_before then
    raise exception 'FAIL test 6: mock_question_id changed across re-projections (% -> %)',
      v_mock_id_before, v_res ->> 'mock_question_id';
  end if;
  raise notice 'PASS test 6: re-tagged row settles, ON CONFLICT keeps one mock_question_id';
end;
$$;

ROLLBACK;
