-- 182: Atomic RPC functions for mock correction-task persistence.
--
-- Replaces the application-layer delete-before-insert and batch-insert patterns
-- in mastery_writer.py (_draft_correction_tasks) and mocks.py
-- (draft_correction_tasks) with two SECURITY DEFINER RPCs, eliminating four
-- confirmed data-loss defects:
--
--  D1 (generated path): batch insert skips non-conflicting rows on first 23505
--  D2 (manual path):    delete-before-insert loses prior drafts on insert failure
--  D3 (manual path):    23505 catch fetches existing rows, non-conflicting rows lost
--  D4 (manual path):    review_state update wrapped in _safe — failure swallowed
--
-- Both RPCs target the partial unique indexes added by migration 181:
--
--   non-null topic: mock_correction_tasks_drafted_unique
--                   (mock_test_id, user_id, category, topic)
--                   WHERE state = 'drafted' AND topic IS NOT NULL
--
--   null topic:     mock_correction_tasks_drafted_null_topic_unique
--                   (mock_test_id, user_id, category)
--                   WHERE state = 'drafted' AND topic IS NULL
--
-- RPC grants: service_role only.
-- REVOKE from: public, anon, authenticated.
--
-- Rollback SQL (manual, non-production only):
--   DROP FUNCTION IF EXISTS public.ensure_mock_correction_draft(uuid,uuid,text,text,text,jsonb);
--   DROP FUNCTION IF EXISTS public.replace_manual_mock_correction_drafts(uuid,uuid,jsonb);
--   -- Migration 181 partial indexes remain — they are independently safe.

do $migration$
begin

  -- ── RPC 1: ensure_mock_correction_draft ──────────────────────────────────────
  --
  -- Idempotent single-draft upsert for the generated path (MasteryWriter).
  -- ON CONFLICT DO NOTHING against the appropriate partial index; then SELECT
  -- to return the row regardless of whether it was just inserted or already
  -- existed. Any exception propagates — no swallowing of 23505 or other errors.
  execute $ddl$
    create or replace function public.ensure_mock_correction_draft(
        p_mock_test_id     uuid,
        p_user_id          uuid,
        p_category         text,
        p_topic            text,    -- nullable
        p_title            text,
        p_source_questions jsonb
    ) returns public.mock_correction_tasks
    language plpgsql
    security definer
    set search_path = public, pg_temp
    as $fn$
    declare
        v_row public.mock_correction_tasks%rowtype;
    begin
        if p_topic is not null then
            -- Targets: mock_correction_tasks_drafted_unique partial index.
            insert into public.mock_correction_tasks
                (mock_test_id, user_id, category, topic, title, source_questions, state)
            values
                (p_mock_test_id, p_user_id, p_category, p_topic, p_title, p_source_questions, 'drafted')
            on conflict (mock_test_id, user_id, category, topic)
                where state = 'drafted' and topic is not null
            do nothing;
        else
            -- Targets: mock_correction_tasks_drafted_null_topic_unique partial index.
            insert into public.mock_correction_tasks
                (mock_test_id, user_id, category, topic, title, source_questions, state)
            values
                (p_mock_test_id, p_user_id, p_category, null, p_title, p_source_questions, 'drafted')
            on conflict (mock_test_id, user_id, category)
                where state = 'drafted' and topic is null
            do nothing;
        end if;

        -- Return the row whether it was just inserted or already existed.
        -- IS NOT DISTINCT FROM handles the null-safe topic comparison.
        select * into v_row
        from public.mock_correction_tasks
        where mock_test_id = p_mock_test_id
          and user_id      = p_user_id
          and category     = p_category
          and state        = 'drafted'
          and topic        is not distinct from p_topic;

        return v_row;
    end;
    $fn$
  $ddl$;

  execute 'revoke all on function public.ensure_mock_correction_draft(uuid,uuid,text,text,text,jsonb) from public';
  execute 'revoke execute on function public.ensure_mock_correction_draft(uuid,uuid,text,text,text,jsonb) from anon';
  execute 'revoke execute on function public.ensure_mock_correction_draft(uuid,uuid,text,text,text,jsonb) from authenticated';
  execute 'grant execute on function public.ensure_mock_correction_draft(uuid,uuid,text,text,text,jsonb) to service_role';

  -- ── RPC 2: replace_manual_mock_correction_drafts ──────────────────────────────
  --
  -- Full atomic replacement for the manual path (mocks.py).
  -- Single transaction: lock → validate source_type → upsert desired rows
  -- (category CHECK fires here) → delete obsolete drafted rows → update
  -- review_state → return final rows.  Applied/dismissed rows are never touched.
  --
  -- Empty p_drafts: deletes all drafted rows and sets review_state='reviewed'.
  execute $ddl$
    create or replace function public.replace_manual_mock_correction_drafts(
        p_mock_test_id uuid,
        p_user_id      uuid,
        p_drafts       jsonb   -- array of {category, topic?, title, source_questions}
    ) returns setof public.mock_correction_tasks
    language plpgsql
    security definer
    set search_path = public, pg_temp
    as $fn$
    declare
        v_mock   public.mock_tests%rowtype;
        v_draft  jsonb;
        v_cat    text;
        v_topic  text;
        v_title  text;
        v_src_qs jsonb;
    begin
        -- 1. Lock the mock row; surface immediately if not found or wrong owner.
        select * into v_mock
        from public.mock_tests
        where id      = p_mock_test_id
          and user_id = p_user_id
        for update;

        if not found then
            raise exception 'mock not found'
                using errcode = 'no_data_found';
        end if;

        -- 2. Forbid manual corrections for platform_attempt mocks.
        --    MasteryWriter owns the correction pipeline for that source type.
        if v_mock.source_type = 'platform_attempt' then
            raise exception 'PLATFORM_ATTEMPT_MANUAL_CORRECTION_FORBIDDEN'
                using errcode = 'raise_exception';
        end if;

        -- 3. Empty drafts: delete all drafted rows, set review_state='reviewed'.
        --    Explicit contract — callers may pass [] to reset the correction state.
        if jsonb_array_length(p_drafts) = 0 then
            delete from public.mock_correction_tasks
            where mock_test_id = p_mock_test_id
              and user_id      = p_user_id
              and state        = 'drafted';

            update public.mock_tests
            set review_state = 'reviewed',
                updated_at   = now()
            where id      = p_mock_test_id
              and user_id = p_user_id;

            return;  -- empty SETOF result
        end if;

        -- 4. UPSERT desired drafted rows.
        --    The mock_correction_tasks_category_check DB constraint fires here
        --    for invalid categories — this fails BEFORE the DELETE below, so
        --    prior drafts are never lost on a bad category.
        for v_draft in
            select value from jsonb_array_elements(p_drafts)
        loop
            v_cat    := v_draft ->> 'category';
            v_topic  := v_draft ->> 'topic';    -- null when key absent or JSON null
            v_title  := v_draft ->> 'title';
            v_src_qs := coalesce(v_draft -> 'source_questions', '[]'::jsonb);

            if v_topic is not null then
                insert into public.mock_correction_tasks
                    (mock_test_id, user_id, category, topic, title, source_questions, state)
                values
                    (p_mock_test_id, p_user_id, v_cat, v_topic, v_title, v_src_qs, 'drafted')
                on conflict (mock_test_id, user_id, category, topic)
                    where state = 'drafted' and topic is not null
                do update set
                    state            = 'drafted',
                    title            = excluded.title,
                    source_questions = excluded.source_questions;
            else
                insert into public.mock_correction_tasks
                    (mock_test_id, user_id, category, topic, title, source_questions, state)
                values
                    (p_mock_test_id, p_user_id, v_cat, null, v_title, v_src_qs, 'drafted')
                on conflict (mock_test_id, user_id, category)
                    where state = 'drafted' and topic is null
                do update set
                    state            = 'drafted',
                    title            = excluded.title,
                    source_questions = excluded.source_questions;
            end if;
        end loop;

        -- 5. Delete obsolete drafted rows not in the desired set.
        --    IS NOT DISTINCT FROM handles null-safe topic comparison.
        --    Applied/dismissed rows are unaffected (WHERE state = 'drafted').
        delete from public.mock_correction_tasks as mct
        where mct.mock_test_id = p_mock_test_id
          and mct.user_id      = p_user_id
          and mct.state        = 'drafted'
          and not exists (
              select 1
              from jsonb_array_elements(p_drafts) as d
              where (d.value ->> 'category') = mct.category
                and (d.value ->> 'topic')    is not distinct from mct.topic
          );

        -- 6. Advance review_state.  Applied/dismissed rows have already been
        --    excluded from the delete; they are never touched by this UPDATE.
        update public.mock_tests
        set review_state = 'correction_drafted',
            updated_at   = now()
        where id      = p_mock_test_id
          and user_id = p_user_id;

        -- 7. Return the final desired drafted rows.
        return query
            select *
            from public.mock_correction_tasks
            where mock_test_id = p_mock_test_id
              and user_id      = p_user_id
              and state        = 'drafted'
            order by created_at;
    end;
    $fn$
  $ddl$;

  execute 'revoke all on function public.replace_manual_mock_correction_drafts(uuid,uuid,jsonb) from public';
  execute 'revoke execute on function public.replace_manual_mock_correction_drafts(uuid,uuid,jsonb) from anon';
  execute 'revoke execute on function public.replace_manual_mock_correction_drafts(uuid,uuid,jsonb) from authenticated';
  execute 'grant execute on function public.replace_manual_mock_correction_drafts(uuid,uuid,jsonb) to service_role';

  perform pg_notify('pgrst', 'reload schema');

end;
$migration$;
