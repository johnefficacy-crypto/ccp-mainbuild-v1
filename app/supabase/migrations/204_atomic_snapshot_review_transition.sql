-- Migration 204: Atomic exam-topic score-snapshot review transition
--
-- Applied version must be reconciled against the deployed schema_migrations
-- state at apply time (operator step); 204 = MAX(filesystem)+1 as of the
-- branch cut.  Confirm with:
--   SELECT MAX(version) FROM schema_migrations;
-- before applying to any environment.
--
-- PROBLEM
-- -------
-- The PATCH /score-snapshots/{id}/review endpoint previously performed two
-- separate PostgREST calls:
--
--   1. admin_audit_logs INSERT   (wrapped in _safe — silently ignored on failure)
--   2. exam_topic_score_snapshots UPDATE
--
-- This creates two failure modes:
--   • INSERT succeeds, UPDATE fails  → orphan audit row, no status change.
--   • INSERT fails (silently), UPDATE succeeds  → status change with no audit trail.
--
-- The comment at admin_exam_intelligence.py deferred the fix to "a dedicated
-- migration (cf. 185_pyq_paper_review_transaction.sql)".  This is that migration.
--
-- SOLUTION
-- --------
-- A SECURITY DEFINER function that mirrors the pattern of migration 185
-- (review_pyq_paper) and migration 201 (cms_review_pyq_source):
--
--   • SELECT ... FOR UPDATE the snapshot row (concurrent-modification guard).
--   • Return a distinguishable not_found error (P0404).
--   • Enforce the full transition matrix inside PostgreSQL.
--   • Enforce the locked→reviewed reviewer_notes requirement in PostgreSQL so
--     that direct service-role RPC calls cannot bypass the business rule.
--   • audit INSERT + snapshot UPDATE in one transaction — any failure rolls
--     back both; no orphan rows; no silent status changes without audit.
--   • Preserve existing reviewer_notes when p_reviewer_notes is NULL so that
--     non-reversal transitions cannot silently erase an earlier review rationale.
--   • Preserve the existing audit-row contract (action, admin_user_id, notes).
--   • Fail closed on a missing actor_id — NULL p_actor_user_id raises P0422.
--   • Return prev_status and new_status for the caller.
--   • SECURITY DEFINER with fixed search_path.
--   • EXECUTE revoked from PUBLIC, anon, and authenticated; granted only to
--     service_role (mirrors migration 203 / migration 190 pattern).
--
-- Transition matrix (matches _SNAPSHOT_TRANSITIONS in admin_exam_intelligence.py):
--
--   draft     → reviewed | rejected
--   reviewed  → locked   | rejected | draft
--   locked    → reviewed
--   rejected  → draft
--
-- Error ERRCODE tokens the Python endpoint maps to HTTP status codes:
--   P0404 → 404  (not_found)
--   P0409 → 409  (concurrent_modification)
--   P0422 → 422  (transition_not_allowed | invalid_target_status |
--                  invalid_reviewer_notes | missing_actor_id)

CREATE OR REPLACE FUNCTION cms_review_exam_topic_snapshot(
    p_snapshot_id     uuid,
    p_expected_status text,
    p_new_status      text,
    p_reviewer_notes  text,   -- nullable; required for locked→reviewed; NULL preserves existing
    p_actor_user_id   uuid,
    p_actor_email     text
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
    -- 0. Fail closed on missing actor identity — an unaudited actor must not
    --    be able to perform a review even via a direct service-role RPC call.
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

    -- 2. Lock the row for the duration of this transaction so no concurrent
    --    writer can mutate status between the checks below and the UPDATE.
    SELECT * INTO v_snap
    FROM public.exam_topic_score_snapshots
    WHERE id = p_snapshot_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'not_found: snapshot % does not exist', p_snapshot_id
            USING ERRCODE = 'P0404';
    END IF;

    -- 3. Concurrent-modification guard: the caller's pre-validation SELECT
    --    may have observed a different status than the now-locked row.
    IF v_snap.status IS DISTINCT FROM p_expected_status THEN
        RAISE EXCEPTION
            'concurrent_modification: expected status=% but found %. Re-fetch and retry.',
            p_expected_status, v_snap.status
            USING ERRCODE = 'P0409';
    END IF;

    -- 4. Enforce the transition matrix on the locked row's actual status.
    --    Mirrors _SNAPSHOT_TRANSITIONS in admin_exam_intelligence.py.
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

    -- 5. locked→reviewed requires reviewer_notes — enforce in DB so that a
    --    direct service-role RPC call cannot bypass the Python fast path.
    IF v_snap.status = 'locked' AND p_new_status = 'reviewed'
       AND nullif(trim(coalesce(p_reviewer_notes, '')), '') IS NULL
    THEN
        RAISE EXCEPTION 'invalid_reviewer_notes: reviewer_notes required when reverting a locked snapshot'
            USING ERRCODE = 'P0422';
    END IF;

    -- 6. Resolve effective reviewer_notes: NULL means "keep existing"; an empty
    --    string or a real value replaces whatever was stored.
    v_effective_notes := CASE
        WHEN p_reviewer_notes IS NULL THEN v_snap.reviewer_notes
        ELSE p_reviewer_notes
    END;

    -- 7. Insert audit row within the same transaction, preserving the
    --    pre-existing audit contract (action, admin_user_id, notes fields).
    --    If this fails the UPDATE below is also rolled back — no orphan rows.
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

    -- 8. Update snapshot (belt-and-suspenders WHERE given the FOR UPDATE lock).
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

-- Deny all non-service-role access.  In Supabase, functions in the public
-- schema are auto-granted to anon and authenticated at creation time, so
-- REVOKE FROM PUBLIC alone is insufficient; revoke from all three explicitly
-- (mirrors migration 190 / migration 201 / migration 203 pattern).
REVOKE EXECUTE ON FUNCTION cms_review_exam_topic_snapshot(uuid, text, text, text, uuid, text) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION cms_review_exam_topic_snapshot(uuid, text, text, text, uuid, text) FROM anon;
REVOKE EXECUTE ON FUNCTION cms_review_exam_topic_snapshot(uuid, text, text, text, uuid, text) FROM authenticated;
GRANT  EXECUTE ON FUNCTION cms_review_exam_topic_snapshot(uuid, text, text, text, uuid, text) TO service_role;

SELECT pg_notify('pgrst', 'reload schema');
