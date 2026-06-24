-- Migration 190: Fix RPC grant matrix + add composite document_assets index
--
-- Gaps found during staging validation of migrations 183–189:
--
-- 1. Grant regression on cms_set_pyq_paper_provenance and
--    cms_link_document_to_pyq_paper.  Migrations 188/189 only revoked from
--    PUBLIC.  In Supabase, functions in the public schema are auto-granted to
--    anon and authenticated at creation time; REVOKE FROM PUBLIC does not
--    remove those explicit per-role grants.  SECURITY DEFINER RPCs that mutate
--    pyq_papers/admin_audit_logs must never be callable by anon or
--    authenticated directly via PostgREST /rpc/.  Migration 185
--    (review_pyq_paper) correctly revoked from all three; this migration
--    applies the same pattern to the two provenance RPCs.
--
-- 2. Three-column composite index on document_assets(scope, document_kind,
--    status) was listed in the acceptance checklist but migration 111 only
--    created (scope, document_kind) and (status) as separate indexes.  The
--    admin document listing endpoint filters on all three columns together;
--    a composite index avoids a bitmap-AND of two separate index scans.

-- ─── 1. Revoke direct access to provenance RPCs from anon / authenticated ───

REVOKE EXECUTE ON FUNCTION public.cms_set_pyq_paper_provenance(text,text,text,jsonb,text,jsonb,boolean) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.cms_set_pyq_paper_provenance(text,text,text,jsonb,text,jsonb,boolean) FROM anon;
REVOKE EXECUTE ON FUNCTION public.cms_set_pyq_paper_provenance(text,text,text,jsonb,text,jsonb,boolean) FROM authenticated;
GRANT  EXECUTE ON FUNCTION public.cms_set_pyq_paper_provenance(text,text,text,jsonb,text,jsonb,boolean) TO service_role;

REVOKE EXECUTE ON FUNCTION public.cms_link_document_to_pyq_paper(text,text,text,text,text,boolean) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.cms_link_document_to_pyq_paper(text,text,text,text,text,boolean) FROM anon;
REVOKE EXECUTE ON FUNCTION public.cms_link_document_to_pyq_paper(text,text,text,text,text,boolean) FROM authenticated;
GRANT  EXECUTE ON FUNCTION public.cms_link_document_to_pyq_paper(text,text,text,text,text,boolean) TO service_role;

-- ─── 2. Composite index for admin document listing path ──────────────────────
--
-- The admin list endpoint always filters by scope='admin_exam_intelligence'
-- and optionally by document_kind and status.  This composite index covers the
-- full three-column filter in one scan instead of a bitmap-AND of two separate
-- indexes.  The existing idx_document_assets_scope_kind and
-- idx_document_assets_status indexes are kept for queries that omit one column.

CREATE INDEX IF NOT EXISTS idx_document_assets_scope_kind_status
    ON public.document_assets(scope, document_kind, status);

SELECT pg_notify('pgrst', 'reload schema');
