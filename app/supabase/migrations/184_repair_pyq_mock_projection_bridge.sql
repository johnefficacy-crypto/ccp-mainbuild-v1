-- 184: Repair staging drift for the PYQ → Mock Bank projection bridge.
--
-- Context: migration 183 was recorded in schema_migrations on staging but
-- three of its objects were never created:
--
--   • public.fn_invalidate_projection_for_question(uuid)
--   • public.fn_block_projection_for_question(uuid, text)
--   • public.uq_mock_qbank_pyq_question_id (unique index on mock_question_bank)
--
-- This is a forward repair migration.  It re-installs those objects using the
-- exact final definitions from migration 183.  All four functions and all 8
-- invalidation triggers are also reinstalled (CREATE OR REPLACE / DROP+CREATE)
-- to guarantee the complete bridge is in a consistent state across every target
-- environment (staging, preview, CI).
--
-- Safety constraints enforced here:
--   • No rows are auto-deleted or merged.
--   • Duplicate pyq_question_id values cause an explicit exception; the
--     operator must resolve them before re-running.
--   • Do NOT apply to production without staging sign-off.
--   • Do NOT modify migration 183 or touch schema_migrations.

do $migration$
declare
    v_dupes text;
begin

-- ── 0. Pre-flight: reject duplicate pyq_question_id in mock_question_bank ─
--
-- The unique index below cannot be created when duplicate non-null
-- pyq_question_id values already exist.  Surface them explicitly so the
-- operator can decide how to resolve the data — we never auto-delete.

select string_agg(pyq_question_id::text, ', ' order by pyq_question_id)
into v_dupes
from (
    select pyq_question_id
    from public.mock_question_bank
    where pyq_question_id is not null
    group by pyq_question_id
    having count(*) > 1
) dup;

if v_dupes is not null then
    raise exception
        'Cannot create uq_mock_qbank_pyq_question_id: '
        'duplicate pyq_question_id values in mock_question_bank: [%]. '
        'Resolve duplicates manually before re-running migration 184.',
        v_dupes;
end if;

-- ── 1. Unique index ────────────────────────────────────────────────────────
--
-- 'CREATE UNIQUE INDEX IF NOT EXISTS' silently skips when an index with the
-- same name already exists, regardless of whether that index is unique, covers
-- the right column, or has the correct partial predicate.  Detect and drop a
-- mismatched same-named index first so the correct one is always installed.

if exists (
    select 1
    from pg_class ci
    join pg_index  i  on i.indexrelid = ci.oid
    join pg_class  ct on ct.oid        = i.indrelid
    join pg_namespace n on n.oid       = ct.relnamespace
    where n.nspname  = 'public'
      and ct.relname = 'mock_question_bank'
      and ci.relname = 'uq_mock_qbank_pyq_question_id'
      and not (
          -- must be unique
          i.indisunique = true
          -- must have exactly one key column (rejects UNIQUE (pyq_question_id, id))
          and i.indnkeyatts = 1
          -- must have no INCLUDE columns (indnatts = key cols + include cols)
          and i.indnatts    = 1
          -- must cover exactly pyq_question_id
          and (select a.attname
               from pg_attribute a
               where a.attrelid = i.indrelid
                 and a.attnum   = i.indkey[0]) = 'pyq_question_id'
          -- must have exactly the right partial predicate; indpred IS NOT NULL is
          -- insufficient — a wrong predicate like "reviewer_status = 'published'"
          -- would still pass.  pg_get_expr returns the predicate as decompiled SQL.
          and pg_get_expr(i.indpred, i.indrelid) = 'pyq_question_id IS NOT NULL'
      )
) then
    -- Wrong index exists: drop it so the correct one is created below.
    execute 'drop index public.uq_mock_qbank_pyq_question_id';
end if;

create unique index if not exists uq_mock_qbank_pyq_question_id
  on public.mock_question_bank(pyq_question_id)
  where pyq_question_id is not null;

-- ── 2. Extend review-log action constraint (idempotent drop+add) ──────────

execute $ddl$ alter table public.mock_question_review_log
  drop constraint if exists mock_question_review_log_action_check $ddl$;

execute $ddl$
  alter table public.mock_question_review_log
    add constraint mock_question_review_log_action_check
    check (action in (
      'create','edit','submit','approve','request_changes',
      'publish','archive','restore','force','unauthorized','import',
      'pyq_projection_created','pyq_projection_updated'
    ))
$ddl$;

-- ── 3. Projection RPC: project_pyq_question_to_mock_bank ──────────────────

execute $ddl$

create or replace function public.project_pyq_question_to_mock_bank(
    p_pyq_question_id uuid,
    p_actor_id        uuid,
    p_audit_reason    text
) returns jsonb
language plpgsql
security definer
set search_path = public
as $fn$
declare
    v_q          record;
    v_primary_tag record;
    v_topic      record;

    v_content_hash        text;
    v_correct_count       integer;
    v_option_count        integer;
    v_verified_opt_count  integer;
    v_empty_opt_count     integer;
    v_primary_tag_count   integer;

    v_projection record;
    v_mock_q_id  uuid;
    v_is_new     boolean := false;
    v_outcome    text;

    v_correct_opt_id uuid;

    v_opt_row    record;
    v_new_opt_id uuid;
begin
    if p_audit_reason is null or length(trim(p_audit_reason)) < 8 then
        return jsonb_build_object(
            'outcome', 'error',
            'error',   'audit_reason_required',
            'detail',  'p_audit_reason must be at least 8 non-blank characters'
        );
    end if;

    select
        q.id,
        q.pyq_paper_id,
        q.question_number,
        q.question_text,
        q.question_type,
        q.correct_option_id     as pyq_correct_option_id,
        q.explanation_text,
        q.observed_difficulty,
        q.expected_solve_time_sec,
        q.language,
        q.reviewer_status       as q_reviewer_status,
        q.metadata              as q_metadata,
        p.exam_id,
        p.year                  as paper_year,
        p.trust_status          as paper_trust_status,
        p.source_url            as paper_source_url,
        p.source_type           as paper_source_type
    into v_q
    from public.pyq_questions q
    join public.pyq_papers    p on p.id = q.pyq_paper_id
    where q.id = p_pyq_question_id
    for update of q, p;

    if not found then
        return jsonb_build_object(
            'outcome', 'error',
            'error',   'question_not_found',
            'pyq_question_id', p_pyq_question_id
        );
    end if;

    if v_q.paper_trust_status != 'verified' then
        perform public.fn_block_projection_for_question(p_pyq_question_id, 'paper_not_verified');
        return jsonb_build_object(
            'outcome',            'blocked',
            'reason',             'paper_not_verified',
            'paper_trust_status', v_q.paper_trust_status,
            'pyq_question_id',    p_pyq_question_id
        );
    end if;

    if v_q.q_reviewer_status != 'verified' then
        perform public.fn_block_projection_for_question(p_pyq_question_id, 'question_not_verified');
        return jsonb_build_object(
            'outcome',         'blocked',
            'reason',          'question_not_verified',
            'reviewer_status', v_q.q_reviewer_status,
            'pyq_question_id', p_pyq_question_id
        );
    end if;

    if v_q.question_type != 'mcq' then
        perform public.fn_block_projection_for_question(p_pyq_question_id, 'not_mcq');
        return jsonb_build_object(
            'outcome',         'blocked',
            'reason',          'not_mcq',
            'question_type',   v_q.question_type,
            'pyq_question_id', p_pyq_question_id
        );
    end if;

    if coalesce(trim(v_q.question_text), '') = '' then
        perform public.fn_block_projection_for_question(p_pyq_question_id, 'empty_question_text');
        return jsonb_build_object(
            'outcome',         'blocked',
            'reason',          'empty_question_text',
            'pyq_question_id', p_pyq_question_id
        );
    end if;

    select
        count(*)                                                             as total,
        count(*) filter (where reviewer_status = 'verified')                as verified_count,
        count(*) filter (where reviewer_status = 'verified' and is_correct) as correct_verified_count,
        count(*) filter (
            where reviewer_status = 'verified'
              and coalesce(trim(option_text), '') = ''
        )                                                                    as empty_text_count
    into v_option_count, v_verified_opt_count, v_correct_count, v_empty_opt_count
    from public.pyq_options
    where question_id = p_pyq_question_id;

    if v_verified_opt_count < 2 then
        perform public.fn_block_projection_for_question(p_pyq_question_id, 'insufficient_verified_options');
        return jsonb_build_object(
            'outcome',               'blocked',
            'reason',                'insufficient_verified_options',
            'verified_option_count', v_verified_opt_count,
            'pyq_question_id',       p_pyq_question_id
        );
    end if;

    if v_empty_opt_count > 0 then
        perform public.fn_block_projection_for_question(p_pyq_question_id, 'empty_verified_option_text');
        return jsonb_build_object(
            'outcome',         'blocked',
            'reason',          'empty_verified_option_text',
            'empty_opt_count', v_empty_opt_count,
            'pyq_question_id', p_pyq_question_id
        );
    end if;

    if v_correct_count != 1 then
        perform public.fn_block_projection_for_question(p_pyq_question_id, 'not_exactly_one_verified_correct_option');
        return jsonb_build_object(
            'outcome',       'blocked',
            'reason',        'not_exactly_one_verified_correct_option',
            'correct_count', v_correct_count,
            'pyq_question_id', p_pyq_question_id
        );
    end if;

    if v_q.pyq_correct_option_id is not null then
        if not exists (
            select 1 from public.pyq_options
            where question_id     = p_pyq_question_id
              and reviewer_status = 'verified'
              and is_correct      = true
              and id              = v_q.pyq_correct_option_id
        ) then
            perform public.fn_block_projection_for_question(p_pyq_question_id, 'correct_option_id_mismatch');
            return jsonb_build_object(
                'outcome',           'blocked',
                'reason',            'correct_option_id_mismatch',
                'stated_correct_id', v_q.pyq_correct_option_id,
                'pyq_question_id',   p_pyq_question_id
            );
        end if;
    end if;

    select count(*)
    into v_primary_tag_count
    from public.pyq_question_topic_tags
    where question_id     = p_pyq_question_id
      and tag_role        = 'primary'
      and reviewer_status = 'verified';

    if v_primary_tag_count != 1 then
        perform public.fn_block_projection_for_question(p_pyq_question_id, 'primary_topic_tag_count_not_one');
        return jsonb_build_object(
            'outcome',           'blocked',
            'reason',            'primary_topic_tag_count_not_one',
            'primary_tag_count', v_primary_tag_count,
            'pyq_question_id',   p_pyq_question_id
        );
    end if;

    select t.*
    into v_primary_tag
    from public.pyq_question_topic_tags t
    where t.question_id     = p_pyq_question_id
      and t.tag_role        = 'primary'
      and t.reviewer_status = 'verified'
    limit 1;

    select s.*
    into v_topic
    from public.topics s
    where s.id = v_primary_tag.topic_id
      and s.is_active = true
    limit 1;

    if not found then
        perform public.fn_block_projection_for_question(p_pyq_question_id, 'primary_topic_invalid_or_inactive');
        return jsonb_build_object(
            'outcome',         'blocked',
            'reason',          'primary_topic_invalid_or_inactive',
            'topic_id',        v_primary_tag.topic_id,
            'pyq_question_id', p_pyq_question_id
        );
    end if;

    if v_topic.subject_id is null then
        perform public.fn_block_projection_for_question(p_pyq_question_id, 'primary_topic_has_no_subject');
        return jsonb_build_object(
            'outcome',         'blocked',
            'reason',          'primary_topic_has_no_subject',
            'topic_id',        v_primary_tag.topic_id,
            'pyq_question_id', p_pyq_question_id
        );
    end if;

    -- Hash = SHA256 over all projected fields.
    -- Matches compute_content_hash() in pyq_mock_projection.py.
    select encode(
        sha256((
            coalesce(lower(trim(v_q.question_text)), '') || chr(0) ||
            coalesce(lower(trim(v_q.explanation_text)), '') || chr(0) ||
            (case when lower(trim(coalesce(v_q.observed_difficulty, ''))) in ('easy','medium','hard')
                  then lower(trim(v_q.observed_difficulty)) else 'medium' end) || chr(0) ||
            coalesce(nullif(lower(trim(coalesce(v_q.language, ''))), ''), 'en') || chr(0) ||
            coalesce(v_q.expected_solve_time_sec::text, '') || chr(0) ||
            coalesce(v_q.pyq_paper_id::text, '') || chr(0) ||
            coalesce(v_q.paper_year::text, '') || chr(0) ||
            coalesce(v_q.exam_id::text, '') || chr(0) ||
            coalesce(v_q.paper_source_url, '') || chr(0) ||
            coalesce(v_q.paper_source_type, '') || chr(0) ||
            coalesce((
                select string_agg(
                    coalesce(lower(o.option_label), '') || chr(30) ||
                    coalesce(lower(trim(o.option_text)), ''),
                    chr(31) order by coalesce(lower(o.option_label), ''), o.id
                )
                from public.pyq_options o
                where o.question_id   = p_pyq_question_id
                  and o.reviewer_status = 'verified'
            ), '') || chr(0) ||
            coalesce((
                select lower(trim(c.option_text))
                from public.pyq_options c
                where c.question_id   = p_pyq_question_id
                  and c.reviewer_status = 'verified'
                  and c.is_correct    = true
                limit 1
            ), '') || chr(0) ||
            coalesce((
                select string_agg(
                    coalesce(t.topic_id::text, '') || chr(30) ||
                    coalesce(t.tag_role, ''),
                    chr(31) order by t.topic_id, t.tag_role
                )
                from public.pyq_question_topic_tags t
                where t.question_id   = p_pyq_question_id
                  and t.reviewer_status = 'verified'
            ), '')
        )::bytea),
        'hex'
    ) into v_content_hash;

    select * into v_projection
    from public.pyq_mock_question_projections
    where pyq_question_id = p_pyq_question_id
    for update;

    if found then
        v_mock_q_id := v_projection.mock_question_id;

        declare
            v_existing_pyq_q_id uuid;
        begin
            select pyq_question_id
            into v_existing_pyq_q_id
            from public.mock_question_bank
            where id = v_mock_q_id;

            if not found then
                update public.pyq_mock_question_projections
                set sync_status = 'archived', updated_at = now()
                where pyq_question_id = p_pyq_question_id;
                v_mock_q_id  := null;
                v_projection := null;
                v_is_new     := true;
            elsif v_existing_pyq_q_id is not null
                  and v_existing_pyq_q_id != p_pyq_question_id then
                return jsonb_build_object(
                    'outcome',            'conflict',
                    'error',              'mock_question_linked_to_different_pyq',
                    'mock_question_id',   v_mock_q_id,
                    'conflicting_pyq_id', v_existing_pyq_q_id,
                    'pyq_question_id',    p_pyq_question_id
                );
            end if;
        end;

        if v_projection is not null
           and v_projection.sync_status = 'active'
           and v_projection.source_content_hash = v_content_hash then
            v_outcome := 'unchanged';
        else
            v_outcome := 'updated';
        end if;
    else
        v_is_new    := true;
        v_mock_q_id := gen_random_uuid();
        v_outcome   := 'created';
    end if;

    if v_outcome = 'unchanged' then
        update public.pyq_mock_question_projections
        set updated_at       = now(),
            last_sync_result = jsonb_build_object(
                'outcome',      'unchanged',
                'checked_at',   now()::text,
                'content_hash', v_content_hash
            )
        where pyq_question_id = p_pyq_question_id;

        return jsonb_build_object(
            'outcome',          'unchanged',
            'mock_question_id', v_mock_q_id,
            'pyq_question_id',  p_pyq_question_id,
            'content_hash',     v_content_hash
        );
    end if;

    if v_is_new then
        insert into public.mock_question_bank (
            id, exam_id, subject_id, topic_id, question_text, question_type,
            difficulty, explanation, language, reviewer_status, published_at,
            source_type, source_kind, question_fingerprint, pyq_question_id,
            pyq_paper_id, pyq_year, expected_time_sec, created_by, created_at, updated_at
        ) values (
            v_mock_q_id, v_q.exam_id, v_topic.subject_id, v_primary_tag.topic_id,
            v_q.question_text, 'mcq',
            case when lower(v_q.observed_difficulty) in ('easy','medium','hard')
                 then lower(v_q.observed_difficulty) else 'medium' end,
            v_q.explanation_text, coalesce(v_q.language, 'en'), 'published', now(),
            'pyq', 'pyq', v_content_hash, p_pyq_question_id,
            v_q.pyq_paper_id, v_q.paper_year, v_q.expected_solve_time_sec,
            p_actor_id, now(), now()
        );
    else
        update public.mock_question_bank set
            exam_id              = v_q.exam_id,
            subject_id           = v_topic.subject_id,
            topic_id             = v_primary_tag.topic_id,
            question_text        = v_q.question_text,
            question_type        = 'mcq',
            difficulty           = case when lower(v_q.observed_difficulty) in ('easy','medium','hard')
                                       then lower(v_q.observed_difficulty) else 'medium' end,
            explanation          = v_q.explanation_text,
            language             = coalesce(v_q.language, 'en'),
            reviewer_status      = 'published',
            published_at         = coalesce(
                                       (select published_at from public.mock_question_bank where id = v_mock_q_id),
                                       now()
                                   ),
            source_type          = 'pyq',
            source_kind          = 'pyq',
            question_fingerprint = v_content_hash,
            pyq_question_id      = p_pyq_question_id,
            pyq_paper_id         = v_q.pyq_paper_id,
            pyq_year             = v_q.paper_year,
            expected_time_sec    = v_q.expected_solve_time_sec,
            updated_at           = now()
        where id = v_mock_q_id;
    end if;

    delete from public.mock_question_options where question_id = v_mock_q_id;

    v_correct_opt_id := null;

    for v_opt_row in
        select id, option_text, option_label, is_correct,
               row_number() over (order by option_label, id) - 1 as opt_idx
        from public.pyq_options
        where question_id     = p_pyq_question_id
          and reviewer_status = 'verified'
        order by option_label, id
    loop
        insert into public.mock_question_options (
            question_id, option_text, option_index, is_correct
        ) values (
            v_mock_q_id, v_opt_row.option_text, v_opt_row.opt_idx, v_opt_row.is_correct
        )
        returning id into v_new_opt_id;

        if v_opt_row.is_correct then
            v_correct_opt_id := v_new_opt_id;
        end if;
    end loop;

    update public.mock_question_bank
    set correct_option_id = v_correct_opt_id, updated_at = now()
    where id = v_mock_q_id;

    delete from public.mock_question_topic_tags where question_id = v_mock_q_id;

    insert into public.mock_question_topic_tags (question_id, topic_id, role)
    select v_mock_q_id, t.topic_id, t.tag_role
    from public.pyq_question_topic_tags t
    where t.question_id   = p_pyq_question_id
      and t.reviewer_status = 'verified';

    delete from public.mock_question_sources where question_id = v_mock_q_id;

    insert into public.mock_question_sources (
        question_id, source_kind, source_trust, source_url,
        pyq_paper_id, pyq_year, evidence_text
    ) values (
        v_mock_q_id, 'pyq', 'verified', v_q.paper_source_url,
        v_q.pyq_paper_id, v_q.paper_year,
        'projected_from_pyq_question_id:' || p_pyq_question_id::text
    );

    insert into public.pyq_mock_question_projections (
        pyq_question_id, mock_question_id, source_content_hash, sync_status,
        last_sync_result, projected_by, projected_at, updated_at
    ) values (
        p_pyq_question_id, v_mock_q_id, v_content_hash, 'active',
        jsonb_build_object('outcome', v_outcome, 'projected_at', now()::text),
        p_actor_id, now(), now()
    )
    on conflict (pyq_question_id) do update
      set mock_question_id    = excluded.mock_question_id,
          source_content_hash = excluded.source_content_hash,
          sync_status         = 'active',
          last_sync_result    = excluded.last_sync_result,
          projected_by        = excluded.projected_by,
          projected_at        = case
              when pyq_mock_question_projections.projected_at is null
              then excluded.projected_at
              else pyq_mock_question_projections.projected_at
          end,
          updated_at          = now();

    insert into public.admin_audit_logs (
        actor_id, action, entity_type, entity_id, new_value, notes
    ) values (
        p_actor_id,
        'pyq_mock_projection_sync',
        'mock_question_bank',
        v_mock_q_id::text,
        jsonb_build_object(
            'outcome',         v_outcome,
            'pyq_question_id', p_pyq_question_id,
            'pyq_paper_id',    v_q.pyq_paper_id,
            'exam_id',         v_q.exam_id,
            'pyq_year',        v_q.paper_year,
            'content_hash',    v_content_hash,
            'topic_id',        v_primary_tag.topic_id,
            'subject_id',      v_topic.subject_id
        ),
        p_audit_reason
    );

    insert into public.mock_question_review_log (
        question_id, actor_id, action, from_status, to_status, notes, at
    ) values (
        v_mock_q_id, p_actor_id,
        'pyq_projection_' || v_outcome,
        case when v_is_new then null else 'published' end,
        'published',
        p_audit_reason,
        now()
    );

    return jsonb_build_object(
        'outcome',           v_outcome,
        'mock_question_id',  v_mock_q_id,
        'pyq_question_id',   p_pyq_question_id,
        'pyq_paper_id',      v_q.pyq_paper_id,
        'exam_id',           v_q.exam_id,
        'pyq_year',          v_q.paper_year,
        'topic_id',          v_primary_tag.topic_id,
        'subject_id',        v_topic.subject_id,
        'content_hash',      v_content_hash,
        'correct_option_id', v_correct_opt_id,
        'is_new',            v_is_new
    );

exception
    when others then raise;
end;
$fn$

$ddl$;

-- ── 4. Helper: fn_invalidate_projection_for_question ──────────────────────

execute $ddl$
create or replace function public.fn_invalidate_projection_for_question(p_qid uuid)
returns void
language plpgsql
security definer
set search_path = public
as $fn$
begin
    update public.pyq_mock_question_projections
    set sync_status = 'stale', updated_at = now()
    where pyq_question_id = p_qid
      and sync_status = 'active';

    update public.mock_question_bank
    set reviewer_status = 'draft', updated_at = now()
    where pyq_question_id = p_qid
      and reviewer_status in ('verified', 'published', 'live');
end;
$fn$
$ddl$;

-- ── 5. Helper: fn_block_projection_for_question ───────────────────────────

execute $ddl$
create or replace function public.fn_block_projection_for_question(
    p_qid    uuid,
    p_reason text default null
)
returns void
language plpgsql
security definer
set search_path = public
as $fn$
begin
    update public.pyq_mock_question_projections
    set sync_status      = 'blocked',
        last_sync_result = jsonb_build_object(
            'outcome',    'blocked',
            'reason',     coalesce(p_reason, 'eligibility_check_failed'),
            'blocked_at', now()::text
        ),
        updated_at       = now()
    where pyq_question_id = p_qid
      and sync_status not in ('blocked', 'archived');

    update public.mock_question_bank
    set reviewer_status = 'draft', updated_at = now()
    where pyq_question_id = p_qid
      and reviewer_status in ('verified', 'published', 'live');
end;
$fn$
$ddl$;

-- ── 6. Trigger function: fn_invalidate_pyq_projection ─────────────────────

execute $ddl$
create or replace function public.fn_invalidate_pyq_projection()
returns trigger
language plpgsql
security definer
set search_path = public
as $fn$
declare
    v_qid uuid;
begin
    if TG_TABLE_NAME = 'pyq_questions' then
        if TG_OP = 'UPDATE' then
            if OLD.reviewer_status = 'verified' and NEW.reviewer_status != 'verified' then
                perform public.fn_invalidate_projection_for_question(NEW.id);
            elsif NEW.reviewer_status = 'verified' and (
                OLD.question_text              is distinct from NEW.question_text
                or OLD.question_type           is distinct from NEW.question_type
                or OLD.correct_option_id       is distinct from NEW.correct_option_id
                or OLD.explanation_text        is distinct from NEW.explanation_text
                or OLD.observed_difficulty     is distinct from NEW.observed_difficulty
                or OLD.expected_solve_time_sec is distinct from NEW.expected_solve_time_sec
                or OLD.language                is distinct from NEW.language
                or OLD.pyq_paper_id            is distinct from NEW.pyq_paper_id
            ) then
                perform public.fn_invalidate_projection_for_question(NEW.id);
            end if;
        end if;
        return NEW;

    elsif TG_TABLE_NAME = 'pyq_papers' then
        if TG_OP = 'UPDATE' and (
            (OLD.trust_status = 'verified' and NEW.trust_status != 'verified')
            or (OLD.exam_phase_id is distinct from NEW.exam_phase_id)
            or (OLD.exam_id       is distinct from NEW.exam_id)
            or (OLD.year          is distinct from NEW.year)
            or (OLD.source_url    is distinct from NEW.source_url)
            or (OLD.source_type   is distinct from NEW.source_type)
        ) then
            for v_qid in
                select id from public.pyq_questions where pyq_paper_id = NEW.id
            loop
                perform public.fn_invalidate_projection_for_question(v_qid);
            end loop;
        end if;
        return NEW;

    elsif TG_TABLE_NAME = 'pyq_options' then
        if TG_OP = 'DELETE' then
            perform public.fn_invalidate_projection_for_question(OLD.question_id);
            return OLD;
        end if;
        if TG_OP = 'INSERT' then
            perform public.fn_invalidate_projection_for_question(NEW.question_id);
            return NEW;
        end if;
        if OLD.is_correct         is distinct from NEW.is_correct
           or OLD.option_text     is distinct from NEW.option_text
           or OLD.option_label    is distinct from NEW.option_label
           or OLD.reviewer_status is distinct from NEW.reviewer_status
        then
            perform public.fn_invalidate_projection_for_question(NEW.question_id);
        end if;
        return NEW;

    elsif TG_TABLE_NAME = 'pyq_question_topic_tags' then
        if TG_OP = 'DELETE' then
            if OLD.reviewer_status = 'verified' then
                perform public.fn_invalidate_projection_for_question(OLD.question_id);
            end if;
            return OLD;
        end if;
        if TG_OP = 'INSERT' then
            if NEW.reviewer_status = 'verified' then
                perform public.fn_invalidate_projection_for_question(NEW.question_id);
            end if;
            return NEW;
        end if;
        if (OLD.reviewer_status = 'verified' or NEW.reviewer_status = 'verified')
           or (OLD.tag_role is distinct from NEW.tag_role)
           or (OLD.topic_id is distinct from NEW.topic_id)
        then
            perform public.fn_invalidate_projection_for_question(NEW.question_id);
        end if;
        return NEW;
    end if;

    return coalesce(NEW, OLD);
end;
$fn$
$ddl$;

-- ── 7. Invalidation triggers — drop then recreate all 8 ──────────────────

execute 'drop trigger if exists trg_invalidate_pyq_projection_q on public.pyq_questions';
execute $t$
create trigger trg_invalidate_pyq_projection_q
after update on public.pyq_questions
for each row execute function public.fn_invalidate_pyq_projection()
$t$;

execute 'drop trigger if exists trg_invalidate_pyq_projection_p on public.pyq_papers';
execute $t$
create trigger trg_invalidate_pyq_projection_p
after update on public.pyq_papers
for each row execute function public.fn_invalidate_pyq_projection()
$t$;

execute 'drop trigger if exists trg_invalidate_pyq_projection_o_upd on public.pyq_options';
execute $t$
create trigger trg_invalidate_pyq_projection_o_upd
after update on public.pyq_options
for each row execute function public.fn_invalidate_pyq_projection()
$t$;

execute 'drop trigger if exists trg_invalidate_pyq_projection_o_del on public.pyq_options';
execute $t$
create trigger trg_invalidate_pyq_projection_o_del
after delete on public.pyq_options
for each row execute function public.fn_invalidate_pyq_projection()
$t$;

execute 'drop trigger if exists trg_invalidate_pyq_projection_o_ins on public.pyq_options';
execute $t$
create trigger trg_invalidate_pyq_projection_o_ins
after insert on public.pyq_options
for each row execute function public.fn_invalidate_pyq_projection()
$t$;

execute 'drop trigger if exists trg_invalidate_pyq_projection_t_upd on public.pyq_question_topic_tags';
execute $t$
create trigger trg_invalidate_pyq_projection_t_upd
after update on public.pyq_question_topic_tags
for each row execute function public.fn_invalidate_pyq_projection()
$t$;

execute 'drop trigger if exists trg_invalidate_pyq_projection_t_del on public.pyq_question_topic_tags';
execute $t$
create trigger trg_invalidate_pyq_projection_t_del
after delete on public.pyq_question_topic_tags
for each row execute function public.fn_invalidate_pyq_projection()
$t$;

execute 'drop trigger if exists trg_invalidate_pyq_projection_t_ins on public.pyq_question_topic_tags';
execute $t$
create trigger trg_invalidate_pyq_projection_t_ins
after insert on public.pyq_question_topic_tags
for each row execute function public.fn_invalidate_pyq_projection()
$t$;

-- ── 8. Security: revoke/grant ─────────────────────────────────────────────

execute 'revoke all on function public.project_pyq_question_to_mock_bank(uuid, uuid, text) from public';
execute 'revoke execute on function public.project_pyq_question_to_mock_bank(uuid, uuid, text) from anon';
execute 'revoke execute on function public.project_pyq_question_to_mock_bank(uuid, uuid, text) from authenticated';
execute 'grant execute on function public.project_pyq_question_to_mock_bank(uuid, uuid, text) to service_role';

execute 'revoke all on function public.fn_invalidate_pyq_projection() from public';
execute 'grant execute on function public.fn_invalidate_pyq_projection() to service_role';

execute 'revoke all on function public.fn_invalidate_projection_for_question(uuid) from public';
execute 'grant execute on function public.fn_invalidate_projection_for_question(uuid) to service_role';

execute 'revoke all on function public.fn_block_projection_for_question(uuid, text) from public';
execute 'grant execute on function public.fn_block_projection_for_question(uuid, text) to service_role';

perform pg_notify('pgrst', 'reload schema');

end;
$migration$;

-- ── Validation assertions ──────────────────────────────────────────────────
--
-- Runs after the DO block in the same transaction.  Any assertion failure
-- rolls the entire migration back so there is no partial state.

do $validate$
declare
    v_count    integer;
    v_has_priv boolean;
begin

    -- fn_invalidate_projection_for_question(uuid) exists
    select count(*) into v_count
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'public'
      and p.proname = 'fn_invalidate_projection_for_question'
      and p.pronargs = 1;

    if v_count = 0 then
        raise exception 'ASSERT: public.fn_invalidate_projection_for_question(uuid) not found';
    end if;

    -- fn_block_projection_for_question(uuid, text) exists
    select count(*) into v_count
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'public'
      and p.proname = 'fn_block_projection_for_question'
      and p.pronargs = 2;

    if v_count = 0 then
        raise exception 'ASSERT: public.fn_block_projection_for_question(uuid, text) not found';
    end if;

    -- project_pyq_question_to_mock_bank(uuid, uuid, text) exists
    select count(*) into v_count
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'public'
      and p.proname = 'project_pyq_question_to_mock_bank'
      and p.pronargs = 3;

    if v_count = 0 then
        raise exception 'ASSERT: public.project_pyq_question_to_mock_bank(uuid, uuid, text) not found';
    end if;

    -- fn_invalidate_pyq_projection() exists
    select count(*) into v_count
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'public'
      and p.proname = 'fn_invalidate_pyq_projection'
      and p.pronargs = 0;

    if v_count = 0 then
        raise exception 'ASSERT: public.fn_invalidate_pyq_projection() not found';
    end if;

    -- Unique index exists with exactly the right shape:
    --   UNIQUE (pyq_question_id) WHERE pyq_question_id IS NOT NULL
    -- indnkeyatts=1 rejects composite keys; indnatts=1 rejects INCLUDE columns;
    -- pg_get_expr comparison rejects a same-named index with a different predicate.
    select count(*) into v_count
    from pg_class ci
    join pg_index  i  on i.indexrelid = ci.oid
    join pg_class  ct on ct.oid        = i.indrelid
    join pg_namespace n on n.oid       = ct.relnamespace
    where n.nspname  = 'public'
      and ct.relname = 'mock_question_bank'
      and ci.relname = 'uq_mock_qbank_pyq_question_id'
      and i.indisunique                                = true
      and i.indnkeyatts                               = 1
      and i.indnatts                                  = 1
      and (select a.attname
           from pg_attribute a
           where a.attrelid = i.indrelid
             and a.attnum   = i.indkey[0])            = 'pyq_question_id'
      and pg_get_expr(i.indpred, i.indrelid)          = 'pyq_question_id IS NOT NULL';

    if v_count = 0 then
        raise exception
            'ASSERT: uq_mock_qbank_pyq_question_id is missing or has wrong shape '
            '(must be UNIQUE, single-column pyq_question_id, predicate = ''pyq_question_id IS NOT NULL'')';
    end if;

    -- All 8 invalidation triggers exist
    select count(*) into v_count
    from pg_trigger
    where tgname in (
        'trg_invalidate_pyq_projection_q',
        'trg_invalidate_pyq_projection_p',
        'trg_invalidate_pyq_projection_o_upd',
        'trg_invalidate_pyq_projection_o_del',
        'trg_invalidate_pyq_projection_o_ins',
        'trg_invalidate_pyq_projection_t_upd',
        'trg_invalidate_pyq_projection_t_del',
        'trg_invalidate_pyq_projection_t_ins'
    );

    if v_count < 8 then
        raise exception 'ASSERT: expected 8 invalidation triggers, found %', v_count;
    end if;

    -- anon cannot execute projection RPC
    select has_function_privilege(
        'anon',
        'public.project_pyq_question_to_mock_bank(uuid, uuid, text)',
        'execute'
    ) into v_has_priv;

    if v_has_priv then
        raise exception 'ASSERT: anon has execute on project_pyq_question_to_mock_bank — revoke failed';
    end if;

    -- authenticated cannot execute projection RPC
    select has_function_privilege(
        'authenticated',
        'public.project_pyq_question_to_mock_bank(uuid, uuid, text)',
        'execute'
    ) into v_has_priv;

    if v_has_priv then
        raise exception 'ASSERT: authenticated has execute on project_pyq_question_to_mock_bank — revoke failed';
    end if;

    -- service_role can execute projection RPC
    select has_function_privilege(
        'service_role',
        'public.project_pyq_question_to_mock_bank(uuid, uuid, text)',
        'execute'
    ) into v_has_priv;

    if not v_has_priv then
        raise exception 'ASSERT: service_role cannot execute project_pyq_question_to_mock_bank — grant failed';
    end if;

    raise notice 'Migration 184 validation: all assertions passed';

end;
$validate$;
