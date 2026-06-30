-- Migration 201: Atomic PYQ-source review transaction (authoritative validation)
-- (Renumbered from 193 via PR #782 — duplicate migration hotfix.)
--
-- Applied version must be reconciled against the deployed schema_migrations
-- state at apply time (operator step); 201 = renumbered from 193 to resolve duplicate.
--
-- pyq_sources previously had NO dedicated review action: trust_status was only
-- PATCH-editable via /pyq-sources/{id}, and sources created through PYQ
-- onboarding landed 'pending' with no proper way to promote them.  This is the
-- deferred OD-2 follow-up.  This migration adds a SECURITY DEFINER function that
-- mirrors review_pyq_paper (migration 185): it wraps the audit INSERT and the
-- trust_status UPDATE in one transaction and performs all business-rule
-- validation on the *locked* row so:
--
--   • A direct service-role call with an illegal target status, bad transition,
--     or short reason is rejected at the DB level — not just at the Python layer.
--   • A concurrent edit that changed trust_status between the caller's
--     pre-validation SELECT and this transaction is caught by the
--     SELECT … FOR UPDATE concurrent-modification guard.
--
-- NOTE: pyq_sources has NO updated_at column (migration 032) — unlike
-- pyq_papers, the UPDATE here must not set updated_at.
--
-- Error ERRCODE tokens the Python endpoint maps to HTTP status codes:
--   P0404 → 404  (not_found)
--   P0409 → 409  (concurrent_modification)
--   P0422 → 422  (transition_not_allowed | invalid_reason | invalid_target_status)

CREATE OR REPLACE FUNCTION cms_review_pyq_source(
    p_source_id       text,
    p_expected_status text,
    p_target_status   text,
    p_reason          text,
    p_actor_id        text,
    p_actor_email     text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_source         pyq_sources%ROWTYPE;
    v_audit_id       uuid;
    v_updated        pyq_sources%ROWTYPE;
    v_reason_trimmed text;
BEGIN
    -- 1. Validate reason length before touching the DB.
    --    Explicit NULL guard because trim(NULL)=NULL and length(NULL)=NULL, so
    --    the length comparison would evaluate to NULL (unknown) and silently pass.
    IF p_reason IS NULL THEN
        RAISE EXCEPTION 'invalid_reason: reason must not be null'
            USING ERRCODE = 'P0422';
    END IF;
    v_reason_trimmed := trim(p_reason);
    IF length(v_reason_trimmed) < 8 OR length(v_reason_trimmed) > 500 THEN
        RAISE EXCEPTION 'invalid_reason: reason must be 8-500 characters (got %)',
            length(v_reason_trimmed)
            USING ERRCODE = 'P0422';
    END IF;

    -- 2. Validate target status is a known value.
    IF p_target_status NOT IN ('verified', 'rejected', 'pending') THEN
        RAISE EXCEPTION 'invalid_target_status: % is not a recognised trust_status',
            p_target_status
            USING ERRCODE = 'P0422';
    END IF;

    -- 3. Lock the row for the duration of this transaction so no concurrent
    --    writer can mutate trust_status between the checks below and the UPDATE.
    SELECT * INTO v_source
    FROM public.pyq_sources
    WHERE id = p_source_id::uuid
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'not_found: source % does not exist', p_source_id
            USING ERRCODE = 'P0404';
    END IF;

    -- 4. Concurrent-modification guard: the caller's pre-validation SELECT may
    --    have seen a different status than the now-locked row.
    IF v_source.trust_status IS DISTINCT FROM p_expected_status THEN
        RAISE EXCEPTION 'concurrent_modification: expected trust_status=% but found %. Re-fetch and retry.',
            p_expected_status, v_source.trust_status
            USING ERRCODE = 'P0409';
    END IF;

    -- 5. Validate transition using the locked row's actual current status.
    --    Matrix mirrors review_pyq_paper (migration 185):
    --      pending  → verified | rejected
    --      verified → rejected
    --      rejected → pending  (re-queue)
    IF NOT (
           (v_source.trust_status = 'pending'  AND p_target_status IN ('verified', 'rejected'))
        OR (v_source.trust_status = 'verified' AND p_target_status = 'rejected')
        OR (v_source.trust_status = 'rejected' AND p_target_status = 'pending')
    ) THEN
        RAISE EXCEPTION 'transition_not_allowed: % -> % is not a permitted transition',
            v_source.trust_status, p_target_status
            USING ERRCODE = 'P0422';
    END IF;

    -- 6. Insert audit row within the same transaction.
    --    If this fails, neither the audit row nor the status change will persist.
    INSERT INTO public.admin_audit_logs (
        actor_id, actor_email, action, entity_type, entity_id,
        new_value, notes
    )
    VALUES (
        p_actor_id::uuid,
        p_actor_email,
        'exam_intel.cms.pyq_source.review',
        'pyq_source',
        p_source_id,
        jsonb_build_object(
            'from_status', p_expected_status,
            'to_status',   p_target_status,
            'reason',      v_reason_trimmed,
            'reviewed_by', p_actor_email,
            'reviewed_at', now()::text
        ),
        'admin_exam_intel_cms'
    )
    RETURNING id INTO v_audit_id;

    -- 7. Update source status (belt-and-suspenders WHERE given the FOR UPDATE
    --    lock).  pyq_sources has no updated_at column (migration 032) — do not
    --    set one.
    UPDATE public.pyq_sources
    SET    trust_status = p_target_status
    WHERE  id           = p_source_id::uuid
    AND    trust_status = p_expected_status
    RETURNING * INTO v_updated;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'concurrent_modification: zero rows updated after lock'
            USING ERRCODE = 'P0409';
    END IF;

    RETURN jsonb_build_object(
        'ok',       true,
        'audit_id', v_audit_id,
        'row',      to_jsonb(v_updated)
    );
END;
$$;

-- Only the service_role backend can call this; deny anon and authenticated.
-- In Supabase, functions in the public schema are auto-granted to anon and
-- authenticated at creation time, so REVOKE FROM PUBLIC alone is insufficient;
-- revoke from all three explicitly (mirrors migration 190).
REVOKE EXECUTE ON FUNCTION cms_review_pyq_source(text, text, text, text, text, text) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION cms_review_pyq_source(text, text, text, text, text, text) FROM anon;
REVOKE EXECUTE ON FUNCTION cms_review_pyq_source(text, text, text, text, text, text) FROM authenticated;
GRANT  EXECUTE ON FUNCTION cms_review_pyq_source(text, text, text, text, text, text) TO service_role;

SELECT pg_notify('pgrst', 'reload schema');
