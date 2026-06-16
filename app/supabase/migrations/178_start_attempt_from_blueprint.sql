-- 178_start_attempt_from_blueprint.sql
-- A-PR3 (D4 Option-B): atomic "persist generated blueprint + start an attempt".
--
-- This migration adds the ONE write path for generated (non-template) mock
-- attempts. In a single transaction it:
--   1. inserts a mock_generated_blueprints row (status 'draft', expires_at, and
--      the snapshot/question_ids content columns from p_blueprint),
--   2. inserts a mock_attempts row (template_id NULL, generated_blueprint_id set,
--      template_snapshot = p_template_snapshot, owner = p_user, in_progress),
--   3. freezes the N mock_attempt_responses (each with its question_snapshot),
--   4. flips the blueprint status 'draft' -> 'started'.
-- Any failure rolls the WHOLE thing back — no orphan blueprint/attempt/response.
--
-- The generated attempt deliberately reuses mock_attempts.template_snapshot, so
-- the entire mock_engine read/score path (get_attempt / save_answer /
-- _finalize_submission / scoring) loads it UNCHANGED — no FE or loader change.
--
-- Idempotency: the partial unique index uq_mock_attempts_active_blueprint
-- (migration 175) permits at most one in_progress attempt per
-- (user_id, generated_blueprint_id). When a blueprint id is reused and an
-- in_progress attempt already exists, this function RETURNS that attempt instead
-- of erroring (and never double-inserts responses). p_blueprint may carry an
-- explicit 'id' so a retried call resolves to the same blueprint; otherwise a
-- fresh single-use blueprint id is generated.
--
-- security definer + service_role-only execute: this is invoked by the FastAPI
-- backend on service_role. Mirrors migration 162's convention (single DO block
-- so the pgx extended-query protocol receives one prepared statement).

do $migration$
begin
  execute $ddl$
    create or replace function public.start_attempt_from_blueprint(
        p_user              uuid,
        p_exam              uuid,
        p_exam_phase        uuid,
        p_blueprint         jsonb,
        p_template_snapshot jsonb,
        p_response_rows     jsonb,
        p_expires_at        timestamptz
    ) returns table(blueprint_id uuid, attempt_id uuid)
    language plpgsql
    security definer
    set search_path = public
    as $fn$
    declare
        v_blueprint_id uuid;
        v_attempt_id   uuid;
        v_source       text;
        v_question_ids uuid[];
    begin
        v_source := coalesce(nullif(p_blueprint->>'source', ''), 'exam_realistic');

        -- An explicit id makes a retried call idempotent on the same blueprint;
        -- otherwise mint a fresh single-use id.
        v_blueprint_id := coalesce(
            nullif(p_blueprint->>'id', '')::uuid,
            gen_random_uuid()
        );

        -- Blueprint question_ids -> uuid[] for the (uuid[]) column.
        select coalesce(array_agg(value::uuid), '{}'::uuid[])
          into v_question_ids
          from jsonb_array_elements_text(
                 coalesce(p_blueprint->'question_ids', '[]'::jsonb)
               ) as value;

        -- 1. blueprint row — status 'draft', expires_at NOT NULL, content columns
        --    straight from p_blueprint. do-nothing-on-conflict so a reused id is
        --    not re-inserted (the idempotent retry path below returns the attempt).
        insert into public.mock_generated_blueprints (
            id, user_id, exam_id, exam_phase_id, source, status,
            template_snapshot, section_snapshot, selector_snapshot,
            question_ids, readiness_snapshot, expires_at
        ) values (
            v_blueprint_id, p_user, p_exam, p_exam_phase, v_source, 'draft',
            coalesce(p_blueprint->'template_snapshot', '{}'::jsonb),
            coalesce(p_blueprint->'section_snapshot', '[]'::jsonb),
            coalesce(p_blueprint->'selector_snapshot', '{}'::jsonb),
            v_question_ids,
            coalesce(p_blueprint->'readiness_snapshot', '{}'::jsonb),
            p_expires_at
        )
        on conflict (id) do nothing;

        -- 2. attempt row — exactly one source (template_id NULL, blueprint set),
        --    owner = p_user. The owner-consistency composite FK + XOR check from
        --    migration 175 are satisfied by construction.
        begin
            insert into public.mock_attempts (
                user_id, template_id, generated_blueprint_id,
                template_snapshot, status, started_at, expires_at,
                current_section_index, section_locks_enabled
            ) values (
                p_user, null, v_blueprint_id,
                coalesce(p_template_snapshot, '{}'::jsonb), 'in_progress',
                now(), p_expires_at,
                0,
                coalesce((p_template_snapshot->>'section_locks_enabled')::boolean, false)
            )
            returning id into v_attempt_id;
        exception when unique_violation then
            -- An in_progress attempt already backs this blueprint: idempotent
            -- return of the existing attempt. Responses are already frozen, so
            -- they are NOT re-inserted. Keep the blueprint marked 'started'.
            select a.id
              into v_attempt_id
              from public.mock_attempts a
             where a.user_id = p_user
               and a.generated_blueprint_id = v_blueprint_id
               and a.status = 'in_progress'
             limit 1;

            update public.mock_generated_blueprints
               set status = 'started',
                   started_at = coalesce(started_at, now())
             where id = v_blueprint_id;

            blueprint_id := v_blueprint_id;
            attempt_id   := v_attempt_id;
            return next;
            return;
        end;

        -- 3. freeze the N response rows, each with its question_snapshot.
        insert into public.mock_attempt_responses (
            attempt_id, question_id, question_snapshot,
            is_visited, is_marked_for_review, client_seq
        )
        select
            v_attempt_id,
            (r->>'question_id')::uuid,
            coalesce(r->'question_snapshot', '{}'::jsonb),
            false, false, 0
        from jsonb_array_elements(coalesce(p_response_rows, '[]'::jsonb)) as r;

        -- 4. flip the blueprint draft -> started (only now that everything landed).
        update public.mock_generated_blueprints
           set status = 'started',
               started_at = now()
         where id = v_blueprint_id;

        blueprint_id := v_blueprint_id;
        attempt_id   := v_attempt_id;
        return next;
    end;
    $fn$
  $ddl$;

  -- Restrict direct invocation to the FastAPI backend's service_role. Without
  -- this any authenticated PostgREST client could start attempts bypassing the
  -- endpoint's server-side threshold + readiness gate.
  execute 'revoke all on function public.start_attempt_from_blueprint(uuid, uuid, uuid, jsonb, jsonb, jsonb, timestamptz) from public';
  execute 'grant execute on function public.start_attempt_from_blueprint(uuid, uuid, uuid, jsonb, jsonb, jsonb, timestamptz) to service_role';

  perform pg_notify('pgrst', 'reload schema');
end;
$migration$;
