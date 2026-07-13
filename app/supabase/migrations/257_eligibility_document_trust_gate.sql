-- 257_eligibility_document_trust_gate.sql
--
-- (Renumbered from 256 → 257 to resolve a contiguous-migration collision with
-- PR #983's 256_ca_relevance_window_sweep.sql, which opened first.)
--
-- Enforcement prerequisite 1 of docs/architecture/regulatory-eligibility-authoring-spec.md
-- ("No document/review trust gate in the writer"). Until this lands, an
-- exam_eligibility_rules row could be promoted to reviewer_status='verified'
-- with nothing more than a free-text source_url or an arbitrary waiver_reason,
-- stamped by the same actor. This migration adds the reviewed-document linkage,
-- direct page locator, reviewer-separation, and the two atomic SECURITY DEFINER
-- review RPCs that gate promotion on a VERIFIED syllabus document backed by an
-- authoritative, processed, page-extracted document_assets row.
--
-- Scope is deliberately narrow — prerequisites 2 (exam-cycle trust), 3
-- (cutoff-aware age), and 4 (inactive-exam discovery) remain BLOCKED and are NOT
-- touched here.
--
-- Repository convention: document_assets linkage uses `source_document_id`
-- (mirrors pyq_papers / syllabus_documents, migrations 186 / 198).
--
-- Legacy safety: only NULLable columns and constraints satisfied by existing
-- rows (all new columns NULL) are added. Existing verified rows are NEVER
-- demoted or mutated by this migration.
--
-- DO NOT apply to production without staging sign-off.
-- DO NOT edit landed migrations.


-- ── A. Schema additions ─────────────────────────────────────────────────────

-- A.1 exam_eligibility_rules: reviewed-document linkage + direct page locator +
--     authorship (reviewer-separation requires a distinct created_by).
alter table public.exam_eligibility_rules
  add column if not exists source_document_id uuid
    references public.document_assets(id) on delete restrict;
alter table public.exam_eligibility_rules
  add column if not exists source_page_start integer;
alter table public.exam_eligibility_rules
  add column if not exists source_page_end integer;
alter table public.exam_eligibility_rules
  add column if not exists created_by uuid
    references auth.users(id) on delete set null;

-- Page numbers are 1-based and positive.
alter table public.exam_eligibility_rules
  drop constraint if exists exam_eligibility_rules_source_page_positive_check;
alter table public.exam_eligibility_rules
  add constraint exam_eligibility_rules_source_page_positive_check
  check (
    (source_page_start is null or source_page_start > 0)
    and (source_page_end is null or source_page_end > 0)
  );

-- Both page fields present together or absent together (a half-locator is
-- meaningless).
alter table public.exam_eligibility_rules
  drop constraint if exists exam_eligibility_rules_source_page_pair_check;
alter table public.exam_eligibility_rules
  add constraint exam_eligibility_rules_source_page_pair_check
  check ((source_page_start is null) = (source_page_end is null));

-- End page cannot precede the start page.
alter table public.exam_eligibility_rules
  drop constraint if exists exam_eligibility_rules_source_page_order_check;
alter table public.exam_eligibility_rules
  add constraint exam_eligibility_rules_source_page_order_check
  check (source_page_start is null or source_page_end >= source_page_start);

create index if not exists idx_eer_source_document_id
  on public.exam_eligibility_rules(source_document_id)
  where source_document_id is not null;

-- A.2 syllabus_documents: reviewer attribution (mirrors syllabus_topic_mentions,
--     migration 031). Per the enforcement spec these attribute the human who
--     verified the official document; FK → auth.users.
alter table public.syllabus_documents
  add column if not exists reviewed_by uuid
    references auth.users(id) on delete set null;
alter table public.syllabus_documents
  add column if not exists reviewed_at timestamptz;
alter table public.syllabus_documents
  add column if not exists reviewer_notes text;


-- ── B. Direct-update protection: a verified rule's MATERIAL fields cannot be
--     mutated while it stays reviewer_status='verified'. Any such edit must
--     first demote the row (clearing verified_by/verified_at). This is the DB
--     backstop for the API-level demote-on-material-edit rule.
create or replace function public._exam_eligibility_rules_block_verified_material_edit()
returns trigger
language plpgsql as $fn$
begin
  if old.reviewer_status = 'verified'
     and new.reviewer_status = 'verified'
     and (
          old.scope              is distinct from new.scope
       or old.rule_type          is distinct from new.rule_type
       or old.stream_id          is distinct from new.stream_id
       or old.value_num          is distinct from new.value_num
       or old.value_text         is distinct from new.value_text
       or old.value_json         is distinct from new.value_json
       or old.is_knockout        is distinct from new.is_knockout
       or old.source_document_id is distinct from new.source_document_id
       or old.source_page_start  is distinct from new.source_page_start
       or old.source_page_end    is distinct from new.source_page_end
     ) then
    raise exception
      'exam_eligibility_rules: cannot mutate material fields of a verified rule '
      'without demoting it first (set reviewer_status away from verified)'
      using errcode = 'P0422';
  end if;
  return new;
end;
$fn$;

drop trigger if exists trg_eer_block_verified_material_edit on public.exam_eligibility_rules;
create trigger trg_eer_block_verified_material_edit
  before update on public.exam_eligibility_rules
  for each row execute function public._exam_eligibility_rules_block_verified_material_edit();


-- ── C. review_syllabus_document() — atomic SECURITY DEFINER review RPC ────────
--
-- Mirrors review_pyq_paper (migration 186/187): reason length gate, target-status
-- validation, row lock, CAS on expected trust_status, transition matrix, an audit
-- row in the same transaction, and a provenance gate for pending → verified that
-- locks + validates the linked document_assets row.
--
-- pending → verified requires (all under the same lock):
--   • source_document_id set on the syllabus_documents row
--   • linked document_assets row exists (locked FOR UPDATE)
--   • scope = 'admin_exam_intelligence'
--   • document_kind in ('notification','corrigendum')
--   • status = 'processed'
--   • source_kind authoritative: 'official_archive' | 'official_scan'
--   • storage_bucket AND storage_path populated
--   • document metadata.exam_id matches syllabus_documents.exam_id
--   • when syllabus_documents.exam_cycle_id is set, metadata.exam_cycle_id matches
--   • at least one extracted document_pages row for the document
--   • reviewer actor is NOT document_assets.uploaded_by (reviewer separation)
--
-- On success the reviewer attribution is stamped; moving AWAY from verified
-- clears reviewed_by / reviewed_at / reviewer_notes.
create or replace function public.review_syllabus_document(
    p_document_id     text,
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
    v_doc            syllabus_documents%ROWTYPE;
    v_asset          document_assets%ROWTYPE;
    v_audit_id       uuid;
    v_updated        syllabus_documents%ROWTYPE;
    v_reason_trimmed text;
    v_blocking       text[];
    v_page_count     integer;
BEGIN
    -- 1. Reason length gate (explicit NULL guard: trim(NULL)/length(NULL) are NULL).
    IF p_reason IS NULL THEN
        RAISE EXCEPTION 'invalid_reason: reason must not be null' USING ERRCODE = 'P0422';
    END IF;
    v_reason_trimmed := trim(p_reason);
    IF length(v_reason_trimmed) < 8 OR length(v_reason_trimmed) > 500 THEN
        RAISE EXCEPTION 'invalid_reason: reason must be 8-500 characters (got %)',
            length(v_reason_trimmed) USING ERRCODE = 'P0422';
    END IF;

    -- 2. Target status must be a known value.
    IF p_target_status NOT IN ('verified', 'rejected', 'pending', 'superseded') THEN
        RAISE EXCEPTION 'invalid_target_status: % is not a recognised trust_status',
            p_target_status USING ERRCODE = 'P0422';
    END IF;

    -- 3. Lock the document row.
    SELECT * INTO v_doc
    FROM public.syllabus_documents
    WHERE id = p_document_id::uuid
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'not_found: syllabus_document % does not exist', p_document_id
            USING ERRCODE = 'P0404';
    END IF;

    -- 4. Concurrent-modification guard.
    IF v_doc.trust_status IS DISTINCT FROM p_expected_status THEN
        RAISE EXCEPTION 'concurrent_modification: expected trust_status=% but found %. Re-fetch and retry.',
            p_expected_status, v_doc.trust_status USING ERRCODE = 'P0409';
    END IF;

    -- 5. Transition matrix.
    IF NOT (
           (v_doc.trust_status = 'pending'    AND p_target_status IN ('verified', 'rejected'))
        OR (v_doc.trust_status = 'verified'   AND p_target_status IN ('rejected', 'superseded', 'pending'))
        OR (v_doc.trust_status = 'rejected'   AND p_target_status = 'pending')
        OR (v_doc.trust_status = 'superseded' AND p_target_status = 'pending')
    ) THEN
        RAISE EXCEPTION 'transition_not_allowed: % -> % is not a permitted transition',
            v_doc.trust_status, p_target_status USING ERRCODE = 'P0422';
    END IF;

    -- 6. Provenance gate for pending → verified (validated + LOCKED document).
    IF v_doc.trust_status = 'pending' AND p_target_status = 'verified' THEN
        v_blocking := ARRAY[]::text[];

        IF v_doc.source_document_id IS NULL THEN
            v_blocking := v_blocking || ARRAY['source_document_id_missing'];
        ELSE
            SELECT * INTO v_asset
            FROM public.document_assets
            WHERE id = v_doc.source_document_id
            FOR UPDATE;

            IF NOT FOUND THEN
                v_blocking := v_blocking || ARRAY['source_document_id_not_found'];
            ELSE
                IF v_asset.scope != 'admin_exam_intelligence' THEN
                    v_blocking := v_blocking || ARRAY['source_document_id_wrong_scope'];
                END IF;
                IF v_asset.document_kind NOT IN ('notification', 'corrigendum') THEN
                    v_blocking := v_blocking || ARRAY['source_document_id_wrong_kind'];
                END IF;
                IF v_asset.status != 'processed' THEN
                    v_blocking := v_blocking || ARRAY['source_document_id_not_processed'];
                END IF;
                IF v_asset.source_kind::text NOT IN ('official_archive', 'official_scan') THEN
                    v_blocking := v_blocking || ARRAY['source_document_id_untrusted_source_kind'];
                END IF;
                IF coalesce(trim(v_asset.storage_bucket), '') = ''
                   OR coalesce(trim(v_asset.storage_path), '') = '' THEN
                    v_blocking := v_blocking || ARRAY['source_document_id_no_storage'];
                END IF;
                IF (v_asset.metadata->>'exam_id') IS DISTINCT FROM v_doc.exam_id::text THEN
                    v_blocking := v_blocking || ARRAY['source_document_id_exam_mismatch'];
                END IF;
                IF v_doc.exam_cycle_id IS NOT NULL
                   AND (v_asset.metadata->>'exam_cycle_id') IS DISTINCT FROM v_doc.exam_cycle_id::text THEN
                    v_blocking := v_blocking || ARRAY['source_document_id_cycle_mismatch'];
                END IF;

                SELECT count(*) INTO v_page_count
                FROM public.document_pages
                WHERE document_id = v_asset.id
                  AND extraction_status = 'extracted';
                IF coalesce(v_page_count, 0) < 1 THEN
                    v_blocking := v_blocking || ARRAY['source_document_id_no_extracted_pages'];
                END IF;

                -- Reviewer separation: the actor cannot verify a document they
                -- uploaded, and it FAILS CLOSED when uploader attribution is
                -- absent — a legacy/manual asset with no uploaded_by cannot prove
                -- a second actor, so it must not be promotable.
                IF v_asset.uploaded_by IS NULL THEN
                    v_blocking := v_blocking || ARRAY['uploader_missing'];
                ELSIF v_asset.uploaded_by::text = p_actor_id THEN
                    v_blocking := v_blocking || ARRAY['reviewer_is_uploader'];
                END IF;
            END IF;
        END IF;

        IF array_length(v_blocking, 1) > 0 THEN
            RAISE EXCEPTION 'provenance_incomplete: blocking_fields=%',
                array_to_string(v_blocking, ',') USING ERRCODE = 'P0422';
        END IF;
    END IF;

    -- 7. Audit row in the same transaction.
    INSERT INTO public.admin_audit_logs (
        actor_id, actor_email, action, entity_type, entity_id, new_value, notes
    )
    VALUES (
        p_actor_id::uuid,
        p_actor_email,
        'exam_intel.cms.syllabus_document.review',
        'syllabus_document',
        p_document_id,
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

    -- 8. Apply the status change + reviewer attribution atomically.
    IF p_target_status = 'verified' THEN
        UPDATE public.syllabus_documents
        SET    trust_status   = p_target_status,
               reviewed_by     = p_actor_id::uuid,
               reviewed_at     = now(),
               reviewer_notes  = v_reason_trimmed,
               updated_at      = now()
        WHERE  id = p_document_id::uuid
        AND    trust_status = p_expected_status
        RETURNING * INTO v_updated;
    ELSE
        -- Moving away from verified (or any non-verify transition) clears the
        -- reviewer attribution so a non-verified row never claims a reviewer.
        UPDATE public.syllabus_documents
        SET    trust_status   = p_target_status,
               reviewed_by     = NULL,
               reviewed_at     = NULL,
               reviewer_notes  = NULL,
               updated_at      = now()
        WHERE  id = p_document_id::uuid
        AND    trust_status = p_expected_status
        RETURNING * INTO v_updated;
    END IF;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'concurrent_modification: zero rows updated after lock'
            USING ERRCODE = 'P0409';
    END IF;

    RETURN jsonb_build_object(
        'ok', true, 'audit_id', v_audit_id, 'row', to_jsonb(v_updated)
    );
END;
$$;

REVOKE EXECUTE ON FUNCTION public.review_syllabus_document(text, text, text, text, text, text) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.review_syllabus_document(text, text, text, text, text, text) FROM anon;
REVOKE EXECUTE ON FUNCTION public.review_syllabus_document(text, text, text, text, text, text) FROM authenticated;
GRANT  EXECUTE ON FUNCTION public.review_syllabus_document(text, text, text, text, text, text) TO service_role;


-- ── D. review_exam_eligibility_rule() — atomic SECURITY DEFINER review RPC ────
--
-- Gates promotion of an exam_eligibility_rules row on a VERIFIED syllabus
-- document + a direct page locator + an authoritative, processed, same-exam
-- document_assets row whose referenced pages are all extracted. No URL-only and
-- no waiver-based verification is possible through this path.
--
-- Transitions:
--   draft    → verified | archived
--   verified → draft | archived
--   archived → draft
--
-- draft → verified requires:
--   • source_document_id AND source_page_start AND source_page_end on the rule
--   • linked document_assets: status='processed', source_kind authoritative,
--     metadata.exam_id matches the rule's exam
--   • a matching syllabus_documents row: same source_document_id, same exam_id,
--     trust_status='verified'
--   • every referenced page (start..end) exists for that document with
--     extraction_status='extracted'
--   • reviewer actor differs from the rule's created_by
--   • the ambiguous discipline+min_percentage two-row representation is rejected
--     (record-correlated qualification_combination is required instead)
create or replace function public.review_exam_eligibility_rule(
    p_rule_id         text,
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
    v_rule           exam_eligibility_rules%ROWTYPE;
    v_asset          document_assets%ROWTYPE;
    v_audit_id       uuid;
    v_updated        exam_eligibility_rules%ROWTYPE;
    v_reason_trimmed text;
    v_blocking       text[];
    v_sibling        text;
    v_syl_id         uuid;
    v_extracted_ct   integer;
    v_want_pages     integer;
BEGIN
    -- 1. Reason length gate.
    IF p_reason IS NULL THEN
        RAISE EXCEPTION 'invalid_reason: reason must not be null' USING ERRCODE = 'P0422';
    END IF;
    v_reason_trimmed := trim(p_reason);
    IF length(v_reason_trimmed) < 8 OR length(v_reason_trimmed) > 500 THEN
        RAISE EXCEPTION 'invalid_reason: reason must be 8-500 characters (got %)',
            length(v_reason_trimmed) USING ERRCODE = 'P0422';
    END IF;

    -- 2. Target status must be a known value.
    IF p_target_status NOT IN ('draft', 'verified', 'archived') THEN
        RAISE EXCEPTION 'invalid_target_status: % is not a recognised reviewer_status',
            p_target_status USING ERRCODE = 'P0422';
    END IF;

    -- 3. Lock the rule row.
    SELECT * INTO v_rule
    FROM public.exam_eligibility_rules
    WHERE id = p_rule_id::uuid
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'not_found: rule % does not exist', p_rule_id
            USING ERRCODE = 'P0404';
    END IF;

    -- 4. Concurrent-modification guard.
    IF v_rule.reviewer_status IS DISTINCT FROM p_expected_status THEN
        RAISE EXCEPTION 'concurrent_modification: expected reviewer_status=% but found %. Re-fetch and retry.',
            p_expected_status, v_rule.reviewer_status USING ERRCODE = 'P0409';
    END IF;

    -- 5. Transition matrix.
    IF NOT (
           (v_rule.reviewer_status = 'draft'    AND p_target_status IN ('verified', 'archived'))
        OR (v_rule.reviewer_status = 'verified' AND p_target_status IN ('draft', 'archived'))
        OR (v_rule.reviewer_status = 'archived' AND p_target_status = 'draft')
    ) THEN
        RAISE EXCEPTION 'transition_not_allowed: % -> % is not a permitted transition',
            v_rule.reviewer_status, p_target_status USING ERRCODE = 'P0422';
    END IF;

    -- 6. Verification gate for draft → verified.
    IF v_rule.reviewer_status = 'draft' AND p_target_status = 'verified' THEN
        -- Reviewer separation (independent of provenance completeness). FAILS
        -- CLOSED when creator attribution is absent — a legacy/manual draft with
        -- no created_by cannot prove a second reviewer, so it is not promotable.
        IF v_rule.created_by IS NULL THEN
            RAISE EXCEPTION 'creator_missing: rule has no created_by; cannot establish reviewer separation'
                USING ERRCODE = 'P0422';
        END IF;
        IF v_rule.created_by::text = p_actor_id THEN
            RAISE EXCEPTION 'reviewer_is_creator: the rule author cannot verify their own rule'
                USING ERRCODE = 'P0422';
        END IF;

        -- Ambiguous two-row linked-qualification protection (retained from the
        -- Python writer guard; a verified discipline + verified min_percentage
        -- for the same (exam, stream, scope) must be one record-correlated
        -- qualification_combination instead).
        IF v_rule.rule_type IN ('discipline', 'min_percentage') THEN
            v_sibling := CASE WHEN v_rule.rule_type = 'discipline'
                              THEN 'min_percentage' ELSE 'discipline' END;
            IF EXISTS (
                SELECT 1 FROM public.exam_eligibility_rules s
                WHERE s.exam_id       = v_rule.exam_id
                  AND s.scope         = v_rule.scope
                  AND s.rule_type     = v_sibling
                  AND s.reviewer_status = 'verified'
                  AND s.stream_id IS NOT DISTINCT FROM v_rule.stream_id
                  AND s.id <> v_rule.id
            ) THEN
                RAISE EXCEPTION 'ambiguous_linked_qualification: a verified % rule already exists for this (exam, stream, scope); author a record-correlated qualification_combination instead',
                    v_sibling USING ERRCODE = 'P0422';
            END IF;
        END IF;

        v_blocking := ARRAY[]::text[];

        -- Direct page locator required (no URL-only, no waiver-based verify).
        IF v_rule.source_document_id IS NULL THEN
            v_blocking := v_blocking || ARRAY['source_document_id_missing'];
        END IF;
        IF v_rule.source_page_start IS NULL OR v_rule.source_page_end IS NULL THEN
            v_blocking := v_blocking || ARRAY['source_page_locator_missing'];
        END IF;

        IF v_rule.source_document_id IS NOT NULL THEN
            -- Lock the supporting VERIFIED syllabus_documents authority row FIRST
            -- (syllabus → asset lock ordering, consistent with
            -- review_syllabus_document). A bare EXISTS would let a concurrent
            -- verified → pending/rejected document review commit between the read
            -- and the rule UPDATE, leaving a verified rule backed by a
            -- non-verified document (TOCTOU). FOR UPDATE holds the exact row so
            -- the demotion serialises behind this transaction.
            SELECT sd.id INTO v_syl_id
            FROM public.syllabus_documents sd
            WHERE sd.source_document_id = v_rule.source_document_id
              AND sd.exam_id            = v_rule.exam_id
              AND sd.trust_status       = 'verified'
            ORDER BY sd.id
            LIMIT 1
            FOR UPDATE;
            IF v_syl_id IS NULL THEN
                v_blocking := v_blocking || ARRAY['no_verified_syllabus_document'];
            END IF;

            SELECT * INTO v_asset
            FROM public.document_assets
            WHERE id = v_rule.source_document_id
            FOR UPDATE;

            IF NOT FOUND THEN
                v_blocking := v_blocking || ARRAY['source_document_id_not_found'];
            ELSE
                IF v_asset.status != 'processed' THEN
                    v_blocking := v_blocking || ARRAY['source_document_id_not_processed'];
                END IF;
                IF v_asset.source_kind::text NOT IN ('official_archive', 'official_scan') THEN
                    v_blocking := v_blocking || ARRAY['source_document_id_untrusted_source_kind'];
                END IF;
                IF (v_asset.metadata->>'exam_id') IS DISTINCT FROM v_rule.exam_id::text THEN
                    v_blocking := v_blocking || ARRAY['source_document_id_exam_mismatch'];
                END IF;

                -- Every referenced page must exist + be extracted for the document.
                IF v_rule.source_page_start IS NOT NULL AND v_rule.source_page_end IS NOT NULL THEN
                    v_want_pages := v_rule.source_page_end - v_rule.source_page_start + 1;
                    SELECT count(DISTINCT page_number) INTO v_extracted_ct
                    FROM public.document_pages
                    WHERE document_id = v_asset.id
                      AND extraction_status = 'extracted'
                      AND page_number BETWEEN v_rule.source_page_start AND v_rule.source_page_end;
                    IF coalesce(v_extracted_ct, 0) < v_want_pages THEN
                        v_blocking := v_blocking || ARRAY['referenced_page_not_extracted'];
                    END IF;
                END IF;
            END IF;
        END IF;

        IF array_length(v_blocking, 1) > 0 THEN
            RAISE EXCEPTION 'provenance_incomplete: blocking_fields=%',
                array_to_string(v_blocking, ',') USING ERRCODE = 'P0422';
        END IF;
    END IF;

    -- 7. Audit row in the same transaction.
    INSERT INTO public.admin_audit_logs (
        actor_id, actor_email, action, entity_type, entity_id, new_value, notes
    )
    VALUES (
        p_actor_id::uuid,
        p_actor_email,
        'eligibility_rule.review',
        'exam_eligibility_rule',
        p_rule_id,
        jsonb_build_object(
            'from_status', p_expected_status,
            'to_status',   p_target_status,
            'reason',      v_reason_trimmed,
            'reviewed_by', p_actor_email,
            'reviewed_at', now()::text
        ),
        'admin_exam_eligibility'
    )
    RETURNING id INTO v_audit_id;

    -- 8. Apply the status change + verifier attribution atomically.
    IF p_target_status = 'verified' THEN
        UPDATE public.exam_eligibility_rules
        SET    reviewer_status = p_target_status,
               verified_by      = p_actor_id::uuid,
               verified_at      = now(),
               updated_at       = now()
        WHERE  id = p_rule_id::uuid
        AND    reviewer_status = p_expected_status
        RETURNING * INTO v_updated;
    ELSE
        UPDATE public.exam_eligibility_rules
        SET    reviewer_status = p_target_status,
               verified_by      = NULL,
               verified_at      = NULL,
               updated_at       = now()
        WHERE  id = p_rule_id::uuid
        AND    reviewer_status = p_expected_status
        RETURNING * INTO v_updated;
    END IF;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'concurrent_modification: zero rows updated after lock'
            USING ERRCODE = 'P0409';
    END IF;

    RETURN jsonb_build_object(
        'ok', true, 'audit_id', v_audit_id, 'row', to_jsonb(v_updated)
    );
END;
$$;

REVOKE EXECUTE ON FUNCTION public.review_exam_eligibility_rule(text, text, text, text, text, text) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.review_exam_eligibility_rule(text, text, text, text, text, text) FROM anon;
REVOKE EXECUTE ON FUNCTION public.review_exam_eligibility_rule(text, text, text, text, text, text) FROM authenticated;
GRANT  EXECUTE ON FUNCTION public.review_exam_eligibility_rule(text, text, text, text, text, text) TO service_role;


-- ── E. Authority-dependency guard — cascade-demote orphaned verified rules ───
--
-- The rule-verification RPC locks the supporting syllabus row only during
-- promotion. AFTER a rule commits as verified, the syllabus authority can still
-- be demoted (verified → pending/rejected/superseded via the review RPC) or have
-- its source_document_id/exam reassigned (documents/{id}/link-to-syllabus), which
-- would leave the eligibility rule verified and aspirant-visible with no matching
-- verified syllabus authority.
--
-- This AFTER UPDATE trigger closes that gap for ALL write paths (review RPC,
-- link-to-syllabus, any direct update) by atomically cascade-demoting every
-- dependent verified rule that would be left orphaned — but only when NO other
-- verified syllabus row still backs the same (source_document_id, exam_id). The
-- demotion is fail-safe: a verified rule can never outlive its authority.
create or replace function public._syllabus_documents_cascade_demote_dependent_rules()
returns trigger
language plpgsql as $fn$
declare
  v_rule record;
begin
  -- Act only when a row that WAS a verified authority stops backing its old
  -- (source_document_id, exam_id): demoted away from verified, or source/exam
  -- reassigned.
  IF OLD.trust_status = 'verified'
     AND OLD.source_document_id IS NOT NULL
     AND (
          NEW.trust_status       IS DISTINCT FROM 'verified'
       OR NEW.source_document_id IS DISTINCT FROM OLD.source_document_id
       OR NEW.exam_id            IS DISTINCT FROM OLD.exam_id
     ) THEN
    FOR v_rule IN
      SELECT r.id, r.exam_id, r.source_document_id
      FROM public.exam_eligibility_rules r
      WHERE r.reviewer_status    = 'verified'
        AND r.source_document_id = OLD.source_document_id
        AND r.exam_id            = OLD.exam_id
    LOOP
      -- Demote only if NO verified syllabus authority remains for this rule
      -- (another verified row for the same source+exam keeps it valid).
      IF NOT EXISTS (
        SELECT 1 FROM public.syllabus_documents sd
        WHERE sd.source_document_id = v_rule.source_document_id
          AND sd.exam_id            = v_rule.exam_id
          AND sd.trust_status       = 'verified'
          AND sd.id <> NEW.id
      ) THEN
        UPDATE public.exam_eligibility_rules
        SET    reviewer_status = 'draft',
               verified_by      = NULL,
               verified_at      = NULL,
               updated_at       = now()
        WHERE  id = v_rule.id;

        INSERT INTO public.admin_audit_logs (
          actor_id, actor_email, action, entity_type, entity_id, new_value, notes
        )
        VALUES (
          NULL, NULL,
          'eligibility_rule.auto_demote',
          'exam_eligibility_rule',
          v_rule.id::text,
          jsonb_build_object(
            'reason',               'supporting_syllabus_document_no_longer_verified',
            'syllabus_document_id', NEW.id::text,
            'from_status',          'verified',
            'to_status',            'draft'
          ),
          'system_cascade'
        );
      END IF;
    END LOOP;
  END IF;
  RETURN NEW;
end;
$fn$;

drop trigger if exists trg_syllabus_documents_cascade_demote_rules on public.syllabus_documents;
create trigger trg_syllabus_documents_cascade_demote_rules
  after update on public.syllabus_documents
  for each row execute function public._syllabus_documents_cascade_demote_dependent_rules();


notify pgrst, 'reload schema';
