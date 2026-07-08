-- Migration 235: EWP semantic shadow evaluator telemetry.
--
-- Remote schema_migrations is currently applied through 222, but this branch
-- already contains local migration files 223..231. This migration therefore
-- RENUMBERED 232 → 235: main already carried 232 (trap_drill_mastery_shadow), 233, 234, so 235 is the next contiguous slot; apply after 234.
--
-- Purpose:
--   Append-only, service-role-only telemetry for semantic evaluator SHADOW runs.
--   These rows are benchmark/audit artifacts only. They must never drive
--   writing unit state, human-review state, lifecycle transitions, prompt
--   activation, or mastery evidence.

CREATE TABLE IF NOT EXISTS public.writing_language_evaluator_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),

  evaluation_id uuid NOT NULL
    REFERENCES public.writing_evaluations(id) ON DELETE NO ACTION,
  unit_version_id uuid NOT NULL
    REFERENCES public.writing_unit_versions(id) ON DELETE NO ACTION,
  evaluation_revision int NOT NULL CHECK (evaluation_revision > 0),

  role text NOT NULL DEFAULT 'shadow'
    CHECK (role IN ('shadow')),

  input_hash text NOT NULL
    CHECK (input_hash ~ '^[0-9a-f]{64}$'),

  deterministic_evaluator_version text NOT NULL,
  deterministic_source_comparison text
    CHECK (
      deterministic_source_comparison IS NULL
      OR deterministic_source_comparison IN (
        'source_unchanged',
        'meaning_not_preserved',
        'source_comparison_uncertain'
      )
    ),
  deterministic_needs_human_review boolean NOT NULL DEFAULT false,
  deterministic_issue_count int NOT NULL DEFAULT 0 CHECK (deterministic_issue_count >= 0),

  adapter_version text NOT NULL,
  provider text,
  provider_model text,
  prompt_version text,
  output_schema_version int NOT NULL DEFAULT 1 CHECK (output_schema_version > 0),

  status text NOT NULL
    CHECK (status IN (
      'succeeded',
      'failed',
      'timeout',
      'malformed',
      'low_confidence',
      'refusal',
      'provider_error',
      'skipped'
    )),

  semantic_source_comparison text
    CHECK (
      semantic_source_comparison IS NULL
      OR semantic_source_comparison IN (
        'source_unchanged',
        'meaning_not_preserved',
        'source_comparison_uncertain'
      )
    ),
  semantic_confidence numeric
    CHECK (semantic_confidence IS NULL OR semantic_confidence BETWEEN 0 AND 1),
  semantic_needs_human_review boolean,
  semantic_issue_count int CHECK (semantic_issue_count IS NULL OR semantic_issue_count >= 0),

  disagrees_with_deterministic boolean GENERATED ALWAYS AS (
    semantic_source_comparison IS NOT NULL
    AND deterministic_source_comparison IS DISTINCT FROM semantic_source_comparison
  ) STORED,

  result_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  error_code text,
  error_message text,

  latency_ms int CHECK (latency_ms IS NULL OR latency_ms >= 0),
  input_tokens int CHECK (input_tokens IS NULL OR input_tokens >= 0),
  output_tokens int CHECK (output_tokens IS NULL OR output_tokens >= 0),
  total_tokens int CHECK (total_tokens IS NULL OR total_tokens >= 0),
  estimated_cost_usd numeric(12, 6)
    CHECK (estimated_cost_usd IS NULL OR estimated_cost_usd >= 0),

  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),

  CHECK (
    total_tokens IS NULL
    OR input_tokens IS NULL
    OR output_tokens IS NULL
    OR total_tokens = input_tokens + output_tokens
  )
);

CREATE INDEX IF NOT EXISTS idx_writing_language_evaluator_runs_eval
  ON public.writing_language_evaluator_runs(evaluation_id);

CREATE INDEX IF NOT EXISTS idx_writing_language_evaluator_runs_created
  ON public.writing_language_evaluator_runs(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_writing_language_evaluator_runs_status
  ON public.writing_language_evaluator_runs(status, created_at DESC);

ALTER TABLE public.writing_language_evaluator_runs ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.writing_language_evaluator_runs
  FROM PUBLIC, anon, authenticated;

GRANT SELECT, INSERT ON TABLE public.writing_language_evaluator_runs
  TO service_role;

DROP TRIGGER IF EXISTS ewp_writing_language_evaluator_runs_immutable
  ON public.writing_language_evaluator_runs;

CREATE TRIGGER ewp_writing_language_evaluator_runs_immutable
  BEFORE UPDATE OR DELETE ON public.writing_language_evaluator_runs
  FOR EACH ROW EXECUTE FUNCTION public.ewp_forbid_mutation();


CREATE OR REPLACE FUNCTION public.ewp_record_language_evaluator_run(
  p_evaluation_id uuid,
  p_unit_version_id uuid,
  p_evaluation_revision int,
  p_input_hash text,
  p_deterministic_evaluator_version text,
  p_deterministic_source_comparison text,
  p_deterministic_needs_human_review boolean,
  p_deterministic_issue_count int,
  p_adapter_version text,
  p_status text,
  p_provider text DEFAULT NULL,
  p_provider_model text DEFAULT NULL,
  p_prompt_version text DEFAULT NULL,
  p_semantic_source_comparison text DEFAULT NULL,
  p_semantic_confidence numeric DEFAULT NULL,
  p_semantic_needs_human_review boolean DEFAULT NULL,
  p_semantic_issue_count int DEFAULT NULL,
  p_result_json jsonb DEFAULT '{}'::jsonb,
  p_error_code text DEFAULT NULL,
  p_error_message text DEFAULT NULL,
  p_latency_ms int DEFAULT NULL,
  p_input_tokens int DEFAULT NULL,
  p_output_tokens int DEFAULT NULL,
  p_total_tokens int DEFAULT NULL,
  p_estimated_cost_usd numeric DEFAULT NULL,
  p_metadata jsonb DEFAULT '{}'::jsonb
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_id uuid;
BEGIN
  INSERT INTO public.writing_language_evaluator_runs (
    evaluation_id,
    unit_version_id,
    evaluation_revision,
    input_hash,
    deterministic_evaluator_version,
    deterministic_source_comparison,
    deterministic_needs_human_review,
    deterministic_issue_count,
    adapter_version,
    provider,
    provider_model,
    prompt_version,
    status,
    semantic_source_comparison,
    semantic_confidence,
    semantic_needs_human_review,
    semantic_issue_count,
    result_json,
    error_code,
    error_message,
    latency_ms,
    input_tokens,
    output_tokens,
    total_tokens,
    estimated_cost_usd,
    metadata
  ) VALUES (
    p_evaluation_id,
    p_unit_version_id,
    p_evaluation_revision,
    p_input_hash,
    p_deterministic_evaluator_version,
    p_deterministic_source_comparison,
    p_deterministic_needs_human_review,
    p_deterministic_issue_count,
    p_adapter_version,
    p_provider,
    p_provider_model,
    p_prompt_version,
    p_status,
    p_semantic_source_comparison,
    p_semantic_confidence,
    p_semantic_needs_human_review,
    p_semantic_issue_count,
    COALESCE(p_result_json, '{}'::jsonb),
    p_error_code,
    p_error_message,
    p_latency_ms,
    p_input_tokens,
    p_output_tokens,
    p_total_tokens,
    p_estimated_cost_usd,
    COALESCE(p_metadata, '{}'::jsonb)
  )
  RETURNING id INTO v_id;

  RETURN jsonb_build_object('ok', true, 'id', v_id);
END;
$$;

REVOKE ALL ON FUNCTION public.ewp_record_language_evaluator_run(
  uuid, uuid, int, text, text, text, boolean, int, text, text, text, text, text,
  text, numeric, boolean, int, jsonb, text, text, int, int, int, int, numeric, jsonb
) FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION public.ewp_record_language_evaluator_run(
  uuid, uuid, int, text, text, text, boolean, int, text, text, text, text, text,
  text, numeric, boolean, int, jsonb, text, text, int, int, int, int, numeric, jsonb
) TO service_role;

COMMENT ON TABLE public.writing_language_evaluator_runs IS
  'Append-only service-role-only telemetry for EWP semantic evaluator shadow runs. No user-facing, lifecycle, prompt activation, or mastery authority.';

COMMENT ON COLUMN public.writing_language_evaluator_runs.input_hash IS
  'SHA-256 hash of the versioned evaluator input envelope. Do not persist raw learner text, prompt/source payloads, auth metadata, exam/user identifiers, or provider request payloads here.';


SELECT pg_notify('pgrst', 'reload schema');
