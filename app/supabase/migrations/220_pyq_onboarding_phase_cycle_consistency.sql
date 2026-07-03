-- Migration 220: harden cms_pyq_onboarding() with phase↔cycle consistency
--
-- EI-CLEAN-02 review (PR #871, BLOCKING): the modal now submits both
-- exam_cycle_id and exam_phase_id, but migration 192's cms_pyq_onboarding()
-- validated each independently against exam_id only. Because pyq_papers carries
-- exam_cycle_id and exam_phase_id as independent FKs, a crafted/stale request
-- could persist cycle A with a phase belonging to cycle B of the SAME exam —
-- contradictory provenance for D05 phase-compatible evidence. Frontend
-- filtering is not an authority boundary; the RPC must enforce it.
--
-- This is a forward migration. Migration 192 is applied and immutable — do NOT
-- edit it. CREATE OR REPLACE here re-installs the whole function with one added,
-- fail-closed guard; all other behaviour is byte-for-byte migration 192.
--
-- Fail-closed rule (only added block, in step 1b): when a phase is supplied it
-- MUST be bound to exactly the supplied cycle. Rejected combinations —
--   * phase from cycle B while cycle A is supplied  (cross-cycle),
--   * phase whose exam_cycle_id IS NULL (template / cycle-agnostic phase),
--   * phase supplied with no cycle at all (p_exam_cycle_id IS NULL)
-- all raise exam_phase_cycle_mismatch (P0422 → HTTP 422).
--
-- Renumbered 219 → 220 to resolve a duplicate-version collision on main:
-- 219_j3_applied_vs_appeared.sql (PR for J3 Applied-vs-Appeared) also landed as
-- 219, so both files tried to INSERT version 219 into supabase_migrations and
-- the second violated schema_migrations_pkey (breaking migration apply / e2e).
-- This file has no external references by filename, so it is the one renumbered
-- (the migration-numbers guard exempts a duplicate-version rename). SQL body is
-- unchanged. Reconcile the applied version against the deployed
-- schema_migrations state at apply time.

CREATE OR REPLACE FUNCTION public.cms_pyq_onboarding(
    p_actor_id      text,
    p_actor_email   text,
    p_reason        text,
    p_exam_id       text,
    p_exam_cycle_id text,
    p_exam_phase_id text,
    p_source        jsonb,   -- null/omitted, or {existing_pyq_source_id, source_id,
                             -- source_type, title, source_url, metadata}
    p_paper         jsonb,   -- {year, paper_date, shift, paper_code, source_url,
                             -- source_type, metadata}
    p_document_id   text     -- optional already-uploaded document_assets row id
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_exam                  record;
    v_cycle                 record;
    v_phase                 record;
    v_existing_source_id    text;
    v_source                record;
    v_resolved_source_id    uuid;
    v_source_created        boolean := false;
    v_source_trust_status   text    := NULL;
    v_source_type           text;
    v_paper_id              uuid;
    v_paper_year            integer;
    v_paper_source_type     text;
    v_doc                   record;
    v_blocking              text[];
    v_source_audit_id       uuid;
    v_paper_audit_id        uuid;
    v_envelope_audit_id     uuid;
    v_document_linked       boolean := false;
BEGIN
    -- ── Reason guard (mirrors WriteEnvelope: 8–500 chars after trim) ──────────
    IF p_reason IS NULL OR length(trim(p_reason)) < 8 OR length(trim(p_reason)) > 500 THEN
        RAISE EXCEPTION 'invalid_reason: reason must be 8-500 characters'
            USING ERRCODE = 'P0422';
    END IF;

    -- ── 1. Exam must exist ────────────────────────────────────────────────────
    SELECT id INTO v_exam
    FROM public.exams
    WHERE id = p_exam_id::uuid;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'exam_not_found: exam % does not exist', p_exam_id
            USING ERRCODE = 'P0422';
    END IF;

    -- ── 1b. Optional cycle / phase ownership ─────────────────────────────────
    IF p_exam_cycle_id IS NOT NULL THEN
        SELECT id, exam_id INTO v_cycle
        FROM public.exam_cycles
        WHERE id = p_exam_cycle_id::uuid;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'exam_cycle_not_found: cycle % does not exist', p_exam_cycle_id
                USING ERRCODE = 'P0422';
        END IF;
        IF v_cycle.exam_id IS DISTINCT FROM v_exam.id THEN
            RAISE EXCEPTION 'exam_cycle_exam_mismatch: cycle % does not belong to exam %',
                p_exam_cycle_id, p_exam_id
                USING ERRCODE = 'P0422';
        END IF;
    END IF;

    IF p_exam_phase_id IS NOT NULL THEN
        SELECT id, exam_id, exam_cycle_id INTO v_phase
        FROM public.exam_phases
        WHERE id = p_exam_phase_id::uuid;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'exam_phase_not_found: phase % does not exist', p_exam_phase_id
                USING ERRCODE = 'P0422';
        END IF;
        IF v_phase.exam_id IS DISTINCT FROM v_exam.id THEN
            RAISE EXCEPTION 'exam_phase_exam_mismatch: phase % does not belong to exam %',
                p_exam_phase_id, p_exam_id
                USING ERRCODE = 'P0422';
        END IF;
        -- Phase↔cycle consistency (fail-closed): a supplied phase must be bound
        -- to exactly the supplied cycle. Rejects cross-cycle phases, a
        -- cycle-agnostic (template) phase, and a phase supplied without a cycle.
        IF p_exam_cycle_id IS NULL
           OR v_phase.exam_cycle_id IS DISTINCT FROM p_exam_cycle_id::uuid THEN
            RAISE EXCEPTION 'exam_phase_cycle_mismatch: phase % is not bound to cycle %',
                p_exam_phase_id, COALESCE(p_exam_cycle_id, '(none)')
                USING ERRCODE = 'P0422';
        END IF;
    END IF;

    -- ── 2. Source resolution ─────────────────────────────────────────────────
    IF p_source IS NOT NULL
       AND (p_source ? 'existing_pyq_source_id')
       AND (p_source->>'existing_pyq_source_id') IS NOT NULL THEN
        -- Reuse path: validate existence + exam match; do NOT mutate trust (OD-2).
        v_existing_source_id := p_source->>'existing_pyq_source_id';

        SELECT id, exam_id, trust_status INTO v_source
        FROM public.pyq_sources
        WHERE id = v_existing_source_id::uuid
        FOR UPDATE;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'pyq_source_not_found: source % does not exist', v_existing_source_id
                USING ERRCODE = 'P0422';
        END IF;
        IF v_source.exam_id IS DISTINCT FROM v_exam.id THEN
            RAISE EXCEPTION 'pyq_source_exam_mismatch: source % does not belong to exam %',
                v_existing_source_id, p_exam_id
                USING ERRCODE = 'P0422';
        END IF;

        v_resolved_source_id  := v_source.id;
        v_source_created      := false;
        v_source_trust_status := v_source.trust_status;

    ELSIF p_source IS NOT NULL
          AND (
                (p_source ? 'source_type')
             OR (p_source ? 'source_id')
             OR (p_source ? 'source_url')
             OR (p_source ? 'title')
          ) THEN
        -- Create path: source_type validated; trust_status forced 'pending'.
        v_source_type := COALESCE(NULLIF(p_source->>'source_type', ''), 'unknown');
        IF v_source_type NOT IN ('official', 'memory_based', 'coaching', 'community', 'aggregator', 'unknown') THEN
            RAISE EXCEPTION 'invalid_source_type: source.source_type % is not a recognised pyq source type', v_source_type
                USING ERRCODE = 'P0422';
        END IF;

        INSERT INTO public.pyq_sources (
            exam_id, source_id, source_type, source_url, title, trust_status, metadata
        )
        VALUES (
            v_exam.id,
            NULLIF(p_source->>'source_id', '')::uuid,
            v_source_type,
            NULLIF(p_source->>'source_url', ''),
            NULLIF(p_source->>'title', ''),
            'pending',
            COALESCE(p_source->'metadata', '{}'::jsonb)
        )
        RETURNING id INTO v_resolved_source_id;

        v_source_created      := true;
        v_source_trust_status := 'pending';

        INSERT INTO public.admin_audit_logs (
            actor_id, actor_email, action, entity_type, entity_id, new_value, notes
        )
        VALUES (
            p_actor_id::uuid,
            p_actor_email,
            'exam_intel.cms.pyq_source.create',
            'pyq_source',
            v_resolved_source_id::text,
            jsonb_build_object(
                'reason',       p_reason,
                'via',          'pyq_onboarding',
                'source_type',  v_source_type,
                'trust_status', 'pending'
            ),
            'admin_exam_intel_cms'
        )
        RETURNING id INTO v_source_audit_id;
    ELSE
        -- No source (OD-1: pyq_source_id is optional).
        v_resolved_source_id := NULL;
    END IF;

    -- ── 3. Create pyq_paper (always 'pending') ───────────────────────────────
    IF p_paper IS NULL OR (p_paper->>'year') IS NULL OR (p_paper->>'year') = '' THEN
        RAISE EXCEPTION 'invalid_paper: paper.year is required'
            USING ERRCODE = 'P0422';
    END IF;
    v_paper_year := (p_paper->>'year')::integer;

    v_paper_source_type := NULLIF(p_paper->>'source_type', '');
    IF v_paper_source_type IS NOT NULL
       AND v_paper_source_type NOT IN ('official', 'memory_based', 'coaching', 'community', 'aggregator', 'unknown') THEN
        RAISE EXCEPTION 'invalid_source_type: paper.source_type % is not a recognised paper source type', v_paper_source_type
            USING ERRCODE = 'P0422';
    END IF;

    INSERT INTO public.pyq_papers (
        pyq_source_id, exam_id, exam_cycle_id, exam_phase_id,
        year, paper_date, shift, paper_code, source_url, source_type,
        trust_status, metadata
    )
    VALUES (
        v_resolved_source_id,
        v_exam.id,
        p_exam_cycle_id::uuid,
        p_exam_phase_id::uuid,
        v_paper_year,
        NULLIF(p_paper->>'paper_date', '')::date,
        NULLIF(p_paper->>'shift', ''),
        NULLIF(p_paper->>'paper_code', ''),
        NULLIF(p_paper->>'source_url', ''),
        COALESCE(v_paper_source_type, 'unknown'),
        'pending',
        COALESCE(p_paper->'metadata', '{}'::jsonb)
    )
    RETURNING id INTO v_paper_id;

    INSERT INTO public.admin_audit_logs (
        actor_id, actor_email, action, entity_type, entity_id, new_value, notes
    )
    VALUES (
        p_actor_id::uuid,
        p_actor_email,
        'exam_intel.cms.pyq_paper.create',
        'pyq_paper',
        v_paper_id::text,
        jsonb_build_object(
            'reason',        p_reason,
            'via',           'pyq_onboarding',
            'year',          v_paper_year,
            'pyq_source_id', v_resolved_source_id,
            'trust_status',  'pending'
        ),
        'admin_exam_intel_cms'
    )
    RETURNING id INTO v_paper_audit_id;

    -- ── 4. Optional document link (six invariants under FOR UPDATE) ──────────
    IF p_document_id IS NOT NULL THEN
        v_blocking := ARRAY[]::text[];

        SELECT * INTO v_doc
        FROM public.document_assets
        WHERE id = p_document_id::uuid
        FOR UPDATE;

        IF NOT FOUND THEN
            v_blocking := array_append(v_blocking, 'source_document_id_not_found');
        ELSE
            IF v_doc.scope != 'admin_exam_intelligence' THEN
                v_blocking := array_append(v_blocking, 'source_document_id_wrong_scope');
            END IF;
            IF v_doc.document_kind != 'pyq_paper' THEN
                v_blocking := array_append(v_blocking, 'source_document_id_wrong_kind');
            END IF;
            IF v_doc.status IN ('failed', 'archived') THEN
                v_blocking := array_append(v_blocking, 'source_document_id_bad_status');
            END IF;
            IF coalesce(trim(v_doc.storage_bucket), '') = ''
               OR coalesce(trim(v_doc.storage_path), '') = '' THEN
                v_blocking := array_append(v_blocking, 'source_document_id_no_storage');
            END IF;
            IF (v_doc.metadata->>'exam_id') IS NOT NULL
               AND (v_doc.metadata->>'exam_id') != ''
               AND (v_doc.metadata->>'exam_id') IS DISTINCT FROM v_exam.id::text THEN
                v_blocking := array_append(v_blocking, 'source_document_id_exam_mismatch');
            END IF;
        END IF;

        IF array_length(v_blocking, 1) > 0 THEN
            -- Raising rolls back the source + paper + audit inserts above.
            RAISE EXCEPTION 'document_not_linkable: blocking_fields=%',
                array_to_string(v_blocking, ',')
                USING ERRCODE = 'P0422';
        END IF;

        UPDATE public.pyq_papers
        SET source_document_id = p_document_id::uuid,
            updated_at         = now()
        WHERE id = v_paper_id;

        v_document_linked := true;
    END IF;

    -- ── 5. Onboarding envelope audit ─────────────────────────────────────────
    INSERT INTO public.admin_audit_logs (
        actor_id, actor_email, action, entity_type, entity_id, new_value, notes
    )
    VALUES (
        p_actor_id::uuid,
        p_actor_email,
        'exam_intel.cms.pyq_onboarding',
        'pyq_paper',
        v_paper_id::text,
        jsonb_build_object(
            'reason',           p_reason,
            'exam_id',          v_exam.id,
            'exam_cycle_id',    p_exam_cycle_id,
            'exam_phase_id',    p_exam_phase_id,
            'pyq_source_id',    v_resolved_source_id,
            'source_created',   v_source_created,
            'pyq_paper_id',     v_paper_id,
            'document_id',      p_document_id,
            'document_linked',  v_document_linked
        ),
        'admin_exam_intel_cms'
    )
    RETURNING id INTO v_envelope_audit_id;

    -- ── 6. Return created records ────────────────────────────────────────────
    RETURN jsonb_build_object(
        'audit_id', v_envelope_audit_id,
        'source',
            CASE WHEN v_resolved_source_id IS NULL THEN NULL
                 ELSE jsonb_build_object(
                     'id',           v_resolved_source_id,
                     'created',      v_source_created,
                     'trust_status', v_source_trust_status
                 )
            END,
        'paper', jsonb_build_object(
            'id',            v_paper_id,
            'trust_status',  'pending',
            'pyq_source_id', v_resolved_source_id
        ),
        'document_link',
            CASE WHEN v_document_linked THEN
                 jsonb_build_object('document_id', p_document_id, 'linked', true)
                 ELSE NULL
            END
    );
END;
$$;

-- Grant matrix (unchanged; CREATE OR REPLACE preserves privileges, re-applied
-- here for a self-contained, idempotent forward migration — mirrors 190 / 191).
REVOKE ALL      ON FUNCTION public.cms_pyq_onboarding(text,text,text,text,text,text,jsonb,jsonb,text) FROM PUBLIC;
REVOKE EXECUTE  ON FUNCTION public.cms_pyq_onboarding(text,text,text,text,text,text,jsonb,jsonb,text) FROM anon;
REVOKE EXECUTE  ON FUNCTION public.cms_pyq_onboarding(text,text,text,text,text,text,jsonb,jsonb,text) FROM authenticated;
GRANT  EXECUTE  ON FUNCTION public.cms_pyq_onboarding(text,text,text,text,text,text,jsonb,jsonb,text) TO service_role;

SELECT pg_notify('pgrst', 'reload schema');
