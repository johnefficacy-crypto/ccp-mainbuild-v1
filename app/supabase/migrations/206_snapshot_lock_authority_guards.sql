-- Migration 206: Score-snapshot lock-authority guards
--
-- Extends cms_review_exam_topic_snapshot (migration 204) with two new
-- authority checks that fire only on the reviewed→locked transition:
--
--   Guard A — Stale-model check
--   Guard B — Superseded-current-model check
--
-- Rationale (see issue #822 for full spec):
--
--   The planner (locked_score_snapshots in score_snapshots.py) consumes only
--   rows whose model_version matches the server MODEL_VERSION constant AND
--   whose computed_at is the latest among locked rows for the same
--   (exam_id, exam_phase_id, topic_id).  Without these guards, the RPC
--   allows locking rows that the planner will silently ignore.
--
-- Approved policy (issue #822, 2026-07-01):
--   draft→reviewed:   always allowed regardless of model_version.
--   reviewed→locked:  reject if row.model_version ≠ p_current_model_version.
--   reviewed→locked:  reject if a locked row with a LATER OR EQUAL computed_at
--                     already exists for the same (exam_id, exam_phase_id,
--                     topic_id) at p_current_model_version.  Equal-timestamp
--                     rows are rejected to ensure a deterministic winner.
--   locked→reviewed:  always allowed with required reviewer_notes (unchanged).
--
-- Race safety:
--   A transaction-level advisory lock keyed by
--   hashtext(exam_id|exam_phase_id|topic_id|model_version) serialises
--   concurrent reviewed→locked attempts for the same scope, making Guard B
--   race-safe without a table-level lock.
--
-- Planner-active invariant:
--   An older row CANNOT become locked after a newer current-model locked row
--   exists for the same scope.  An older row CAN lock first; a newer row
--   may subsequently lock and the planner will select the newer row.
--
-- New parameter:
--   p_current_model_version  text  — supplied by the Python layer from
--                                    score_snapshots.MODEL_VERSION.  PostgreSQL
--                                    cannot read the Python constant directly.
--
-- New error tokens (P0422):
--   stale_model_version  — Guard A failure
--   superseded_snapshot  — Guard B failure
--
-- The old function signature (6 params) is replaced by a new one (7 params).
-- REVOKE/GRANT statements are updated to cover the new signature and drop the old.

-- Drop the old 6-param signature so the grant matrix stays clean.
REVOKE EXECUTE ON FUNCTION cms_review_exam_topic_snapshot(uuid, text, text, text, uuid, text) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION cms_review_exam_topic_snapshot(uuid, text, text, text, uuid, text) FROM anon;
REVOKE EXECUTE ON FUNCTION cms_review_exam_topic_snapshot(uuid, text, text, text, uuid, text) FROM authenticated;
DROP FUNCTION IF EXISTS cms_review_exam_topic_snapshot(uuid, text, text, text, uuid, text);

CREATE OR REPLACE FUNCTION cms_review_exam_topic_snapshot(
    p_snapshot_id             uuid,
    p_expected_status         text,
    p_new_status              text,
    p_reviewer_notes          text,   -- nullable; required for locked→reviewed; NULL preserves existing
    p_actor_user_id           uuid,
    p_actor_email             text,
    p_current_model_version   text    -- pass score_snapshots.MODEL_VERSION from Python layer
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_snap              exam_topic_score_snapshots%ROWTYPE;
    v_audit_id          uuid;
    v_updated           exam_topic_score_snapshots%ROWTYPE;
    v_effective_notes   text;
BEGIN
    -- 0. Fail closed on missing actor identity.
    IF p_actor_user_id IS NULL THEN
        RAISE EXCEPTION 'missing_actor_id: p_actor_user_id must not be NULL'
            USING ERRCODE = 'P0422';
    END IF;

    -- 1. Validate target status before touching any row.
    IF p_new_status NOT IN ('draft', 'reviewed', 'locked', 'rejected') THEN
        RAISE EXCEPTION 'invalid_target_status: % is not a recognised snapshot status',
            p_new_status
            USING ERRCODE = 'P0422';
    END IF;

    -- 2. For reviewed→locked, acquire a transaction-level advisory lock keyed
    --    by the business scope (exam_id, exam_phase_id, topic_id, model_version)
    --    BEFORE locking the candidate row.  This serialises concurrent lock
    --    attempts for the same scope, making Guard B race-safe.
    --
    --    We read exam_id/exam_phase_id/topic_id from the row without FOR UPDATE
    --    first (a plain SELECT is sufficient for advisory-lock keying; the FOR
    --    UPDATE comes next).  If the row does not exist the FOR UPDATE below
    --    will surface the not_found error as normal.
    IF p_new_status = 'locked' THEN
        DECLARE
            v_scope exam_topic_score_snapshots%ROWTYPE;
        BEGIN
            SELECT * INTO v_scope
            FROM public.exam_topic_score_snapshots
            WHERE id = p_snapshot_id;

            IF FOUND THEN
                PERFORM pg_advisory_xact_lock(
                    hashtext(
                        v_scope.exam_id::text           || '|' ||
                        COALESCE(v_scope.exam_phase_id::text, '') || '|' ||
                        v_scope.topic_id::text          || '|' ||
                        p_current_model_version
                    )
                );
            END IF;
        END;
    END IF;

    -- 3. Lock the candidate row for the duration of this transaction.
    SELECT * INTO v_snap
    FROM public.exam_topic_score_snapshots
    WHERE id = p_snapshot_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'not_found: snapshot % does not exist', p_snapshot_id
            USING ERRCODE = 'P0404';
    END IF;

    -- 4. Concurrent-modification guard.
    IF v_snap.status IS DISTINCT FROM p_expected_status THEN
        RAISE EXCEPTION
            'concurrent_modification: expected status=% but found %. Re-fetch and retry.',
            p_expected_status, v_snap.status
            USING ERRCODE = 'P0409';
    END IF;

    -- 5. Enforce the transition matrix on the locked row's actual status.
    IF NOT (
           (v_snap.status = 'draft'    AND p_new_status IN ('reviewed', 'rejected'))
        OR (v_snap.status = 'reviewed' AND p_new_status IN ('locked', 'rejected', 'draft'))
        OR (v_snap.status = 'locked'   AND p_new_status = 'reviewed')
        OR (v_snap.status = 'rejected' AND p_new_status = 'draft')
    ) THEN
        RAISE EXCEPTION 'transition_not_allowed: % -> % is not a permitted transition',
            v_snap.status, p_new_status
            USING ERRCODE = 'P0422';
    END IF;

    -- 6. locked→reviewed: require reviewer_notes.
    IF v_snap.status = 'locked' AND p_new_status = 'reviewed'
       AND nullif(trim(coalesce(p_reviewer_notes, '')), '') IS NULL
    THEN
        RAISE EXCEPTION 'invalid_reviewer_notes: reviewer_notes required when reverting a locked snapshot'
            USING ERRCODE = 'P0422';
    END IF;

    -- 7. Guard A — Stale-model check (reviewed→locked only).
    --    draft→reviewed is always allowed regardless of model_version.
    --    locked→reviewed reversal is always allowed.
    IF v_snap.status = 'reviewed' AND p_new_status = 'locked' THEN
        IF v_snap.model_version IS DISTINCT FROM p_current_model_version THEN
            RAISE EXCEPTION
                'stale_model_version: snapshot model_version=% does not match current=%',
                v_snap.model_version, p_current_model_version
                USING ERRCODE = 'P0422';
        END IF;
    END IF;

    -- 8. Guard B — Superseded-current-model check (reviewed→locked only).
    --    Reject if a locked row with a LATER computed_at already exists for
    --    the same (exam_id, exam_phase_id, topic_id) at the current model version.
    --    The advisory lock above ensures this SELECT is serialised with other
    --    concurrent reviewed→locked attempts for the same scope.
    IF v_snap.status = 'reviewed' AND p_new_status = 'locked' THEN
        IF EXISTS (
            SELECT 1
            FROM public.exam_topic_score_snapshots
            WHERE exam_id       = v_snap.exam_id
              AND topic_id      = v_snap.topic_id
              AND (exam_phase_id IS NOT DISTINCT FROM v_snap.exam_phase_id)
              AND model_version  = p_current_model_version
              AND status         = 'locked'
              AND computed_at    >= v_snap.computed_at
              AND id            <> p_snapshot_id   -- exclude the candidate itself
        ) THEN
            RAISE EXCEPTION
                'superseded_snapshot: a newer locked snapshot already exists for this scope'
                USING ERRCODE = 'P0422';
        END IF;
    END IF;

    -- 9. Resolve effective reviewer_notes: NULL means "keep existing".
    v_effective_notes := CASE
        WHEN p_reviewer_notes IS NULL THEN v_snap.reviewer_notes
        ELSE p_reviewer_notes
    END;

    -- 10. Insert audit row within the same transaction.
    INSERT INTO public.admin_audit_logs (
        actor_id, actor_email, admin_user_id,
        action, entity_type, entity_id,
        old_value, new_value, notes
    )
    VALUES (
        p_actor_user_id,
        p_actor_email,
        p_actor_user_id,
        'snapshot_status_transition',
        'exam_topic_score_snapshot',
        p_snapshot_id::text,
        jsonb_build_object('status', p_expected_status),
        jsonb_build_object('status', p_new_status),
        p_reviewer_notes
    )
    RETURNING id INTO v_audit_id;

    -- 11. Update snapshot.
    UPDATE public.exam_topic_score_snapshots
    SET
        status         = p_new_status,
        reviewed_by    = p_actor_user_id,
        reviewed_at    = now(),
        reviewer_notes = v_effective_notes
    WHERE id     = p_snapshot_id
    AND   status = p_expected_status
    RETURNING * INTO v_updated;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'concurrent_modification: zero rows updated after lock'
            USING ERRCODE = 'P0409';
    END IF;

    RETURN jsonb_build_object(
        'ok',          true,
        'audit_id',    v_audit_id,
        'snapshot_id', p_snapshot_id,
        'prev_status', p_expected_status,
        'new_status',  p_new_status
    );
END;
$$;

REVOKE EXECUTE ON FUNCTION cms_review_exam_topic_snapshot(uuid, text, text, text, uuid, text, text) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION cms_review_exam_topic_snapshot(uuid, text, text, text, uuid, text, text) FROM anon;
REVOKE EXECUTE ON FUNCTION cms_review_exam_topic_snapshot(uuid, text, text, text, uuid, text, text) FROM authenticated;
GRANT  EXECUTE ON FUNCTION cms_review_exam_topic_snapshot(uuid, text, text, text, uuid, text, text) TO service_role;

SELECT pg_notify('pgrst', 'reload schema');
