-- Atomic review transition for a PYQ question and its child options.
--
-- Updates pyq_questions.reviewer_status in the same transaction that
-- cascades reviewer_status / reviewed_by / reviewed_at to every child
-- pyq_options row, ensuring the pair is always consistent.
--
-- Cascade applies for verified / rejected / needs_correction.
-- 'pending' does NOT cascade: resetting all child options to pending is
-- destructive and never needed in the normal workflow.
--
-- Called by PATCH /api/admin/exam-intelligence/items/pyq_question/{id}/review.

create or replace function public.update_pyq_question_review_atomic(
    p_question_id     uuid,
    p_reviewer_status text,
    p_reviewed_by     uuid,
    p_reviewed_at     timestamptz
) returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
    v_question     jsonb;
    v_option_count integer := 0;
begin
    -- Update the question (pyq_questions has reviewer_status but not reviewed_by/reviewed_at).
    update public.pyq_questions
    set reviewer_status = p_reviewer_status
    where id = p_question_id
    returning to_jsonb(pyq_questions.*) into v_question;

    if v_question is null then
        raise exception 'pyq_question not found: %', p_question_id
            using errcode = 'no_data_found';
    end if;

    -- Cascade to child options for non-pending statuses.
    if p_reviewer_status in ('verified', 'rejected', 'needs_correction') then
        update public.pyq_options
        set reviewer_status = p_reviewer_status,
            reviewed_by     = p_reviewed_by,
            reviewed_at     = p_reviewed_at
        where question_id = p_question_id;

        get diagnostics v_option_count = row_count;
    end if;

    return jsonb_build_object(
        'question',              v_question,
        'cascaded_option_count', v_option_count
    );
end;
$$;

notify pgrst, 'reload schema';
