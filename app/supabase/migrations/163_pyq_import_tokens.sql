-- Migration 163: pyq_import_tokens
--
-- Replaces the process-local token dict in pyq_bulk_import.py with a
-- durable table so preflight tokens survive worker restarts and are
-- visible across all workers in a multi-process deployment.

CREATE TABLE public.pyq_import_tokens (
  token              text        PRIMARY KEY,
  paper_id           uuid        NOT NULL REFERENCES public.pyq_papers(id) ON DELETE CASCADE,
  preflight_summary  jsonb       NOT NULL,
  preflight_rows     jsonb       NOT NULL,
  created_by         uuid        REFERENCES public.profiles(id) ON DELETE SET NULL,
  created_at         timestamptz NOT NULL DEFAULT now(),
  expires_at         timestamptz NOT NULL,
  consumed_at        timestamptz
);

CREATE INDEX idx_pyq_import_tokens_paper   ON public.pyq_import_tokens(paper_id);
CREATE INDEX idx_pyq_import_tokens_expires ON public.pyq_import_tokens(expires_at)
  WHERE consumed_at IS NULL;

-- RLS: service_role only. Operators never touch this table directly.
ALTER TABLE public.pyq_import_tokens ENABLE ROW LEVEL SECURITY;

CREATE POLICY pyq_import_tokens_service_role_all
  ON public.pyq_import_tokens FOR ALL
  TO service_role USING (true) WITH CHECK (true);
