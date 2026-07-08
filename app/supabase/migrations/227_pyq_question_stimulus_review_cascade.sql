-- 227_pyq_question_stimulus_review_cascade.sql
-- PYQ Intelligence v2 delivery order, PR-3 (admin review): extend the atomic
-- question-review cascade to the question<->stimulus ASSOCIATION rows.
--
-- Migration 162 introduced update_pyq_question_review_atomic(), which updates a
-- pyq_questions row and cascades reviewer_status to its child pyq_options rows
-- in one transaction. This migration supersedes 162 via CREATE OR REPLACE with
-- the SAME signature (p_question_id uuid, p_reviewer_status text, p_reviewed_by
-- uuid, p_reviewed_at timestamptz) so the existing caller (review_item) is
-- unchanged, and adds an identical cascade to public.pyq_question_stimuli for
-- the reviewed question.
--
-- Design boundary (see migration 223 header, checkpost P1b): only the LINK
-- (pyq_question_stimuli) is cascaded by question review — the shared stimulus
-- CONTENT (pyq_stimuli) is reviewed INDEPENDENTLY, because the same passage may
-- back other still-unreviewed questions. This RPC therefore never touches
-- pyq_stimuli.
--
-- Cascade applies for verified / rejected / needs_correction only — 'pending'
-- does NOT cascade (resetting all children to pending is destructive and never
-- needed in the normal workflow), matching migration 162.
--
-- Link-cascade guard (checkpost PR #899 fix #2): the question<->stimulus link is
-- INDEPENDENTLY governed (migration 223 header). A reviewer who has already set a
-- specific association to 'rejected' or 'needs_correction' has made an explicit
-- negative decision about that link; a later question review must NOT silently
-- flip it back to the question's status (e.g. 'verified'). The link UPDATE is
-- therefore scoped to links that are NOT already in an explicit negative decision
-- (`reviewer_status not in ('rejected','needs_correction')`), so pending/verified
-- links follow the question while explicit reject/needs_correction is preserved.
-- cascaded_link_count reflects only the rows actually updated. The pyq_options
-- cascade is deliberately unguarded: options are NOT independently governed — they
-- have no per-option review decision distinct from their parent question.
--
-- Called by PATCH /api/admin/exam-intelligence/items/pyq_question/{id}/review.
--
-- Wrapped in a single DO block so the migration runner can send it as one
-- prepared statement (pgx extended query protocol rejects multi-command files).

do $migration$
begin
  execute $ddl$
    create or replace function public.update_pyq_question_review_atomic(
        p_question_id     uuid,
        p_reviewer_status text,
        p_reviewed_by     uuid,
        p_reviewed_at     timestamptz
    ) returns jsonb
    language plpgsql
    security definer
    set search_path = public
    as $fn$
    declare
        v_question     jsonb;
        v_option_count integer := 0;
        v_link_count   integer := 0;
    begin
        update public.pyq_questions
        set reviewer_status = p_reviewer_status,
            reviewed_by     = p_reviewed_by,
            reviewed_at     = p_reviewed_at
        where id = p_question_id
        returning to_jsonb(pyq_questions.*) into v_question;

        if v_question is null then
            raise exception 'pyq_question not found: %', p_question_id
                using errcode = 'no_data_found';
        end if;

        if p_reviewer_status in ('verified', 'rejected', 'needs_correction') then
            update public.pyq_options
            set reviewer_status = p_reviewer_status,
                reviewed_by     = p_reviewed_by,
                reviewed_at     = p_reviewed_at
            where question_id = p_question_id;

            get diagnostics v_option_count = row_count;

            -- Cascade to the question<->stimulus ASSOCIATION rows only. The
            -- shared stimulus CONTENT (pyq_stimuli) is deliberately untouched:
            -- it is reviewed independently (migration 223, checkpost P1b).
            -- An explicit negative decision on a specific link
            -- ('rejected'/'needs_correction') is preserved — the question's
            -- review only carries pending/verified links along (fix #2).
            update public.pyq_question_stimuli
            set reviewer_status = p_reviewer_status,
                reviewed_by     = p_reviewed_by,
                reviewed_at     = p_reviewed_at
            where question_id = p_question_id
              and reviewer_status not in ('rejected', 'needs_correction');

            get diagnostics v_link_count = row_count;
        end if;

        return jsonb_build_object(
            'question',              v_question,
            'cascaded_option_count', v_option_count,
            'cascaded_link_count',   v_link_count
        );
    end;
    $fn$
  $ddl$;

  -- Restrict direct invocation: only service_role (used by the FastAPI backend)
  -- may call this function. Without this guard any authenticated PostgREST client
  -- can bypass the /review endpoint's permission check.
  execute 'revoke all on function public.update_pyq_question_review_atomic(uuid, text, uuid, timestamptz) from public';
  execute 'grant execute on function public.update_pyq_question_review_atomic(uuid, text, uuid, timestamptz) to service_role';

  perform pg_notify('pgrst', 'reload schema');
end;
$migration$;
