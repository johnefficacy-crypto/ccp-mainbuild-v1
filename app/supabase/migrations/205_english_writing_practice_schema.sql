-- Migration 205: English Writing Practice (EWP-1) — schema, constraints, RLS.
--
-- Lands the full practice-runtime data model locked in
-- docs/architecture/english-writing-practice.md. Additive only; no runtime
-- behaviour, API, or mastery writes (those are EWP-2/EWP-2B).
--
-- Invariants enforced here (see architecture §§4,8,9,10,12):
--   * user_id / reviewer FKs -> public.profiles(id) (repo convention; profiles.id = auth.users.id).
--   * Append-only history tables get DATABASE-level immutability triggers, not
--     just RLS — RLS does not constrain service_role (§12.4).
--   * Service-role-only tables get RLS enabled with NO client allow policy.
--   * Owner-readable tables get explicit owner-select policies (§12.1).
--   * Deterministic seed UUIDs via md5('ewp:...')::uuid — re-run safe, never gen_random_uuid() (§EWP-1).
--
-- Migration number: highest existing migration is 204; this is 205. VERIFY DB
-- against schema_migrations before applying (OPERATOR PENDING).

-- ---------------------------------------------------------------------------
-- 0. Helpers
-- ---------------------------------------------------------------------------

-- tier_rank: explicit evidence-tier ordering. NEVER compare evidence_tier text
-- lexically ('recognition' < 'production' is lexically true but semantically
-- production outranks recognition). §4.12.
CREATE OR REPLACE FUNCTION public.ewp_tier_rank(tier text)
RETURNS int
LANGUAGE sql
IMMUTABLE
AS $$
  SELECT CASE tier
    WHEN 'recognition' THEN 1
    WHEN 'correction'  THEN 2
    WHEN 'production'  THEN 3
    WHEN 'retention'   THEN 4
    ELSE 0
  END
$$;

-- Shared immutability guard for append-only tables (§12.4). Attached BEFORE
-- UPDATE OR DELETE. Raises even for service_role, which bypasses RLS.
CREATE OR REPLACE FUNCTION public.ewp_forbid_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION 'append_only_violation: % on %.% is forbidden (immutable history row)',
    TG_OP, TG_TABLE_SCHEMA, TG_TABLE_NAME;
END;
$$;

-- ---------------------------------------------------------------------------
-- 1. writing_rubrics
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.writing_rubrics (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name        text NOT NULL,
  version     int  NOT NULL,
  dimensions  jsonb NOT NULL,   -- array of {key,label,weight,max_score}
  created_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (name, version)
);

-- ---------------------------------------------------------------------------
-- 2. writing_prompts
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.writing_prompts (
  id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  exam_id                 uuid NOT NULL REFERENCES public.exams(id) ON DELETE CASCADE,
  exam_cycle_id           uuid REFERENCES public.exam_cycles(id) ON DELETE SET NULL,
  exam_phase_id           uuid REFERENCES public.exam_phases(id) ON DELETE SET NULL,
  subject_id              uuid NOT NULL REFERENCES public.subjects(id) ON DELETE CASCADE,
  topic_id                uuid NOT NULL REFERENCES public.topics(id) ON DELETE CASCADE,
  microtopic_id           uuid REFERENCES public.topics(id) ON DELETE SET NULL,   -- level='microtopic'
  exercise_type           text NOT NULL,
  prompt_text             text NOT NULL,
  source_text             text,
  required_words          jsonb,
  required_sentence_count int,
  difficulty_level        int NOT NULL CHECK (difficulty_level BETWEEN 1 AND 10),
  min_words               int,
  max_words               int,
  max_rewrite_attempts    int NOT NULL DEFAULT 3,
  rubric_id               uuid REFERENCES public.writing_rubrics(id) ON DELETE SET NULL,
  reviewer_status         text NOT NULL DEFAULT 'pending'
    CHECK (reviewer_status IN ('pending','verified','rejected','needs_correction')),
  is_active               boolean NOT NULL DEFAULT false,
  source_document_id      uuid REFERENCES public.document_assets(id) ON DELETE SET NULL,
  metadata                jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at              timestamptz NOT NULL DEFAULT now(),
  updated_at              timestamptz NOT NULL DEFAULT now(),
  CHECK (max_words IS NULL OR min_words IS NULL OR max_words >= min_words)
);
CREATE INDEX IF NOT EXISTS idx_writing_prompts_exam ON public.writing_prompts(exam_id);
CREATE INDEX IF NOT EXISTS idx_writing_prompts_active
  ON public.writing_prompts(exam_id, exercise_type) WHERE reviewer_status = 'verified' AND is_active = true;

-- ---------------------------------------------------------------------------
-- 3. exam_descriptive_requirements
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.exam_descriptive_requirements (
  id                              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  exam_id                         uuid NOT NULL REFERENCES public.exams(id) ON DELETE CASCADE,
  exam_cycle_id                   uuid REFERENCES public.exam_cycles(id) ON DELETE SET NULL,
  exam_phase_id                   uuid REFERENCES public.exam_phases(id) ON DELETE SET NULL,
  stream_key                      text,
  language                        text NOT NULL DEFAULT 'english',
  exercise_type                   text NOT NULL,
  paper_name                      text,
  marks                           numeric,
  duration_minutes                int CHECK (duration_minutes IS NULL OR duration_minutes > 0),
  minimum_words                   int CHECK (minimum_words IS NULL OR minimum_words >= 0),
  maximum_words                   int,
  required_sections               jsonb,
  format_rules                    jsonb,
  evaluation_dimensions           jsonb,
  feedback_release_policy         text NOT NULL
    CHECK (feedback_release_policy IN ('immediate','on_submit','on_evaluation_terminal','scheduled_after_submit')),
  feedback_release_delay_seconds  int,
  syllabus_document_id            uuid REFERENCES public.document_assets(id) ON DELETE SET NULL,
  notification_document_id        uuid REFERENCES public.document_assets(id) ON DELETE SET NULL,
  source_url                      text,
  source_locator                  jsonb,
  reviewer_status                 text NOT NULL DEFAULT 'pending'
    CHECK (reviewer_status IN ('pending','verified','rejected','needs_correction')),
  reviewed_by                     uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  reviewed_at                     timestamptz,
  reviewer_notes                  text,
  is_active                       boolean NOT NULL DEFAULT false,
  created_at                      timestamptz NOT NULL DEFAULT now(),
  updated_at                      timestamptz NOT NULL DEFAULT now(),
  CHECK (maximum_words IS NULL OR minimum_words IS NULL OR maximum_words >= minimum_words),
  -- NB: explicit IS NOT NULL — a bare `delay > 0` yields NULL for a NULL delay,
  -- and a CHECK only fails on FALSE, so scheduled_after_submit + NULL delay would
  -- otherwise slip through.
  CHECK (
    (feedback_release_policy = 'scheduled_after_submit'
       AND feedback_release_delay_seconds IS NOT NULL AND feedback_release_delay_seconds > 0)
    OR
    (feedback_release_policy <> 'scheduled_after_submit' AND feedback_release_delay_seconds IS NULL)
  )
);
-- Null-safe idempotency key (§4.2).
CREATE UNIQUE INDEX IF NOT EXISTS uq_exam_descriptive_requirements
  ON public.exam_descriptive_requirements(
    exam_id,
    COALESCE(exam_cycle_id, '00000000-0000-0000-0000-000000000000'::uuid),
    COALESCE(exam_phase_id, '00000000-0000-0000-0000-000000000000'::uuid),
    COALESCE(stream_key, ''),
    language,
    exercise_type
  );

-- ---------------------------------------------------------------------------
-- 4. writing_sessions
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.writing_sessions (
  id                              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id                         uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  study_task_id                   uuid REFERENCES public.study_tasks(id) ON DELETE SET NULL,
  prompt_id                       uuid NOT NULL REFERENCES public.writing_prompts(id) ON DELETE CASCADE,
  mode                            text NOT NULL CHECK (mode IN ('learning','exam')),
  status                          text NOT NULL DEFAULT 'active'
    CHECK (status IN ('active','evaluation_pending','rewrite_required','submitted','completed','evaluation_incomplete','abandoned')),
  projection_revision             int NOT NULL,
  feedback_release_policy         text NOT NULL,
  feedback_release_delay_seconds  int,
  feedback_released_at            timestamptz,
  evaluation_outcome              text
    CHECK (evaluation_outcome IS NULL OR evaluation_outcome IN ('unscored','deterministic_only','fully_evaluated')),
  started_at                      timestamptz NOT NULL DEFAULT now(),
  submitted_at                    timestamptz,
  completed_at                    timestamptz
);
CREATE INDEX IF NOT EXISTS idx_writing_sessions_user ON public.writing_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_writing_sessions_task ON public.writing_sessions(study_task_id);

-- ---------------------------------------------------------------------------
-- 5. writing_session_units
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.writing_session_units (
  id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id             uuid NOT NULL REFERENCES public.writing_sessions(id) ON DELETE CASCADE,
  unit_number            int NOT NULL,
  practice_microtopic_id uuid REFERENCES public.topics(id) ON DELETE SET NULL,   -- level='microtopic'
  unit_constraints       jsonb NOT NULL DEFAULT '{}'::jsonb,
  status                 text NOT NULL DEFAULT 'not_started'
    CHECK (status IN ('not_started','draft','evaluation_pending','evaluation_failed','rewrite_required','ready','completed')),
  UNIQUE (session_id, unit_number)
);

-- ---------------------------------------------------------------------------
-- 6. writing_unit_versions (append-only)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.writing_unit_versions (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  unit_id           uuid NOT NULL REFERENCES public.writing_session_units(id) ON DELETE CASCADE,
  version_number    int NOT NULL,
  answer_text       text NOT NULL,
  client_word_count int,
  server_word_count int,   -- computed at submit, included in INSERT; never updated
  submission_kind   text NOT NULL DEFAULT 'user' CHECK (submission_kind IN ('user','blank')),
  content_hash      text NOT NULL,   -- SHA-256(answer_text) lowercase hex
  submitted_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (unit_id, version_number)
);

-- ---------------------------------------------------------------------------
-- 7. writing_evaluations
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.writing_evaluations (
  id                              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  unit_version_id                 uuid NOT NULL REFERENCES public.writing_unit_versions(id) ON DELETE CASCADE,
  evaluation_revision             int NOT NULL DEFAULT 1,
  deterministic_evaluator_version text,
  language_evaluator_version      text,
  deterministic_status            text NOT NULL DEFAULT 'pending'
    CHECK (deterministic_status IN ('pending','completed','failed')),
  language_status                 text NOT NULL DEFAULT 'not_requested'
    CHECK (language_status IN ('not_requested','queued','running','completed','failed','needs_review')),
  human_review_status             text NOT NULL DEFAULT 'not_required'
    CHECK (human_review_status IN ('not_required','pending','in_review','completed')),
  overall_status                  text NOT NULL DEFAULT 'pending'
    CHECK (overall_status IN ('pending','partial','terminal_partial','completed','failed')),
  deterministic_result            jsonb,
  language_result                 jsonb,
  dimension_scores                jsonb,
  created_at                      timestamptz NOT NULL DEFAULT now(),
  updated_at                      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (unit_version_id, evaluation_revision)
);

-- ---------------------------------------------------------------------------
-- 8. writing_session_checks (append-only)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.writing_session_checks (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id       uuid NOT NULL REFERENCES public.writing_sessions(id) ON DELETE CASCADE,
  check_type       text NOT NULL,
  version_set_hash text NOT NULL,
  passed           boolean NOT NULL,
  details          jsonb NOT NULL DEFAULT '{}'::jsonb,
  checker_version  text NOT NULL,
  created_at       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_writing_session_checks_session ON public.writing_session_checks(session_id);

-- ---------------------------------------------------------------------------
-- 9. writing_issue_events (append-only)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.writing_issue_events (
  id                         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  evaluation_id              uuid NOT NULL REFERENCES public.writing_evaluations(id) ON DELETE CASCADE,
  issue_type                 text NOT NULL,
  microtopic_id              uuid REFERENCES public.topics(id) ON DELETE SET NULL,   -- level='microtopic'
  lineage_id                 uuid NOT NULL,
  predecessor_issue_event_id uuid REFERENCES public.writing_issue_events(id) ON DELETE SET NULL,
  span_start_utf16           int,
  span_end_utf16             int,
  quoted_text                text,
  original_text              text,
  suggested_text             text,
  explanation                text,
  severity                   text NOT NULL CHECK (severity IN ('advisory','should_fix','must_fix')),
  affects_current_state      boolean NOT NULL DEFAULT true,
  created_at                 timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_writing_issue_events_eval ON public.writing_issue_events(evaluation_id);
CREATE INDEX IF NOT EXISTS idx_writing_issue_events_lineage ON public.writing_issue_events(lineage_id);

-- ---------------------------------------------------------------------------
-- 10. writing_issue_resolution_events (append-only)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.writing_issue_resolution_events (
  id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  issue_event_id           uuid NOT NULL REFERENCES public.writing_issue_events(id) ON DELETE CASCADE,
  resolving_version_id     uuid NOT NULL REFERENCES public.writing_unit_versions(id) ON DELETE CASCADE,
  resolving_evaluation_id  uuid NOT NULL REFERENCES public.writing_evaluations(id) ON DELETE CASCADE,
  successor_issue_event_id uuid REFERENCES public.writing_issue_events(id) ON DELETE SET NULL,
  outcome                  text NOT NULL CHECK (outcome IN ('resolved','persisted','regressed','uncertain')),
  evaluator_version        text NOT NULL,
  confidence               numeric,
  rationale                text,
  created_at               timestamptz NOT NULL DEFAULT now(),
  UNIQUE (issue_event_id, resolving_version_id, evaluator_version)
);

-- ---------------------------------------------------------------------------
-- 11. writing_issue_projections (append-only)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.writing_issue_projections (
  id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  issue_event_id           uuid NOT NULL REFERENCES public.writing_issue_events(id) ON DELETE CASCADE,
  projection_revision      int NOT NULL,
  projection_kind          text NOT NULL DEFAULT 'automatic'
    CHECK (projection_kind IN ('automatic','review_override')),
  -- FK to writing_issue_review_events added by ALTER below (that table is
  -- created after this one).
  override_review_event_id uuid,
  canonical_error_type     text,
  projection_confidence    numeric,
  prior_occurrence_count   int,
  rationale                text,
  created_at               timestamptz NOT NULL DEFAULT now(),
  CHECK (
    (projection_kind = 'automatic' AND override_review_event_id IS NULL)
    OR
    (projection_kind = 'review_override' AND override_review_event_id IS NOT NULL)
  )
);
-- One automatic projection per (issue, revision); overrides live alongside (§4.11a).
CREATE UNIQUE INDEX IF NOT EXISTS uq_writing_issue_projections_automatic
  ON public.writing_issue_projections(issue_event_id, projection_revision)
  WHERE projection_kind = 'automatic';
CREATE UNIQUE INDEX IF NOT EXISTS uq_writing_issue_projections_override
  ON public.writing_issue_projections(override_review_event_id)
  WHERE projection_kind = 'review_override';

-- ---------------------------------------------------------------------------
-- 12. writing_issue_review_events (append-only, service-role-only)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.writing_issue_review_events (
  id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  issue_event_id        uuid NOT NULL REFERENCES public.writing_issue_events(id) ON DELETE CASCADE,
  decision              text NOT NULL CHECK (decision IN ('confirmed','invalidated','reclassified')),
  corrected_issue_type  text,
  reviewer_type         text NOT NULL CHECK (reviewer_type IN ('human','system')),
  reviewer_id           uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  evaluator_version     text,
  reason                text,
  created_at            timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_writing_issue_review_events_issue ON public.writing_issue_review_events(issue_event_id);

-- Deferred FK: writing_issue_projections.override_review_event_id references
-- this table, which is created after it. Add the FK now.
ALTER TABLE public.writing_issue_projections
  DROP CONSTRAINT IF EXISTS writing_issue_projections_override_review_event_id_fkey;
ALTER TABLE public.writing_issue_projections
  ADD CONSTRAINT writing_issue_projections_override_review_event_id_fkey
  FOREIGN KEY (override_review_event_id)
  REFERENCES public.writing_issue_review_events(id) ON DELETE CASCADE;

-- ---------------------------------------------------------------------------
-- 13. user_topic_mastery_evidence (append-only, service-role-only)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.user_topic_mastery_evidence (
  id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id                 uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  exam_id                 uuid REFERENCES public.exams(id) ON DELETE SET NULL,
  exam_phase_id           uuid REFERENCES public.exam_phases(id) ON DELETE SET NULL,
  topic_id                uuid NOT NULL REFERENCES public.topics(id) ON DELETE CASCADE,
  microtopic_id           uuid REFERENCES public.topics(id) ON DELETE SET NULL,   -- level='microtopic'
  source_type             text NOT NULL
    CHECK (source_type IN ('objective_mock','descriptive_mock','sentence_drill','paragraph_drill','human_review','mentor_review')),
  source_entity_id        uuid NOT NULL,
  evidence_tier           text NOT NULL CHECK (evidence_tier IN ('recognition','correction','production','retention')),
  score                   numeric,
  confidence              numeric,
  issue_projection_id     uuid REFERENCES public.writing_issue_projections(id) ON DELETE SET NULL,
  evidence_op             text NOT NULL DEFAULT 'assert' CHECK (evidence_op IN ('assert','retract','replace')),
  review_event_id         uuid REFERENCES public.writing_issue_review_events(id) ON DELETE SET NULL,
  supersedes_evidence_key text,
  evidence_key            text NOT NULL,
  observed_at             timestamptz NOT NULL,
  metadata                jsonb NOT NULL DEFAULT '{}'::jsonb,
  UNIQUE (evidence_key)
);
CREATE INDEX IF NOT EXISTS idx_utme_user_microtopic ON public.user_topic_mastery_evidence(user_id, microtopic_id);

-- ---------------------------------------------------------------------------
-- 14. writing_evaluation_jobs (mutable queue)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.writing_evaluation_jobs (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  evaluation_id  uuid NOT NULL REFERENCES public.writing_evaluations(id) ON DELETE CASCADE,
  job_kind       text NOT NULL CHECK (job_kind IN ('language_evaluation','rubric_evaluation')),
  generation     int NOT NULL DEFAULT 1,
  status         text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','running','done','failed')),
  attempts       int NOT NULL DEFAULT 0,
  max_attempts   int NOT NULL DEFAULT 3,
  scheduled_for  timestamptz,
  locked_at      timestamptz,
  claim_token    uuid,   -- lease/fencing (§8.3)
  last_error     text,
  created_at     timestamptz NOT NULL DEFAULT now(),
  updated_at     timestamptz NOT NULL DEFAULT now(),
  UNIQUE (evaluation_id, job_kind, generation)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_writing_evaluation_jobs_active
  ON public.writing_evaluation_jobs(evaluation_id, job_kind)
  WHERE status IN ('pending','running');

-- ---------------------------------------------------------------------------
-- 15. writing_mastery_shadow (append-only, service-role-only)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.writing_mastery_shadow (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  exam_id             uuid REFERENCES public.exams(id) ON DELETE SET NULL,
  topic_id            uuid NOT NULL REFERENCES public.topics(id) ON DELETE CASCADE,
  microtopic_id       uuid REFERENCES public.topics(id) ON DELETE SET NULL,
  source_type         text NOT NULL,
  source_entity_id    uuid NOT NULL,
  evaluation_id       uuid NOT NULL REFERENCES public.writing_evaluations(id) ON DELETE CASCADE,
  issue_projection_id uuid REFERENCES public.writing_issue_projections(id) ON DELETE SET NULL,
  evidence_tier       text NOT NULL,
  score               numeric,
  confidence          numeric,
  delta_json          jsonb NOT NULL DEFAULT '{}'::jsonb,
  evidence_key        text NOT NULL,
  processed_at        timestamptz NOT NULL DEFAULT now(),
  UNIQUE (evidence_key)
);

-- ---------------------------------------------------------------------------
-- 16. writing_mastery_outbox (mutable; drives post-commit mastery writes)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.writing_mastery_outbox (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_kind         text NOT NULL CHECK (source_kind IN ('evaluation','review_correction')),
  evaluation_id       uuid REFERENCES public.writing_evaluations(id) ON DELETE CASCADE,
  review_event_id     uuid REFERENCES public.writing_issue_review_events(id) ON DELETE CASCADE,
  evidence_op         text NOT NULL DEFAULT 'assert' CHECK (evidence_op IN ('assert','retract','replace')),
  user_id             uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  mastery_flag_state  text NOT NULL CHECK (mastery_flag_state IN ('shadow','live')),
  idempotency_key     text NOT NULL,
  status              text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','processing','done','failed')),
  attempts            int NOT NULL DEFAULT 0,
  max_attempts        int NOT NULL DEFAULT 5,
  locked_at           timestamptz,
  last_error          text,
  created_at          timestamptz NOT NULL DEFAULT now(),
  processed_at        timestamptz,
  CHECK (
    (source_kind = 'evaluation' AND evaluation_id IS NOT NULL AND review_event_id IS NULL)
    OR
    (source_kind = 'review_correction' AND review_event_id IS NOT NULL)
  ),
  UNIQUE (idempotency_key)
);
CREATE INDEX IF NOT EXISTS idx_writing_mastery_outbox_claim
  ON public.writing_mastery_outbox(status, locked_at) WHERE status IN ('pending','processing');

-- ---------------------------------------------------------------------------
-- 17. writing_issue_type_microtopic_map (backend-owned taxonomy resolution)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.writing_issue_type_microtopic_map (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  issue_type    text NOT NULL,
  microtopic_id uuid NOT NULL REFERENCES public.topics(id) ON DELETE CASCADE,   -- English, level='microtopic'
  map_version   int NOT NULL DEFAULT 1,
  is_active     boolean NOT NULL DEFAULT true,
  created_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (issue_type, map_version)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_issue_type_microtopic_active
  ON public.writing_issue_type_microtopic_map(issue_type) WHERE is_active = true;

-- ---------------------------------------------------------------------------
-- study_tasks: typed launch targets (never stored URLs) (§11.1)
-- ---------------------------------------------------------------------------
ALTER TABLE public.study_tasks
  ADD COLUMN IF NOT EXISTS launch_type      text,
  ADD COLUMN IF NOT EXISTS launch_entity_id uuid,
  ADD COLUMN IF NOT EXISTS launch_context   jsonb;

-- ---------------------------------------------------------------------------
-- Immutability triggers on append-only tables (§12.4)
-- ---------------------------------------------------------------------------
DO $$
DECLARE
  t text;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'writing_unit_versions',
    'writing_issue_events',
    'writing_issue_resolution_events',
    'writing_issue_projections',
    'writing_issue_review_events',
    'user_topic_mastery_evidence',
    'writing_mastery_shadow'
  ] LOOP
    EXECUTE format('DROP TRIGGER IF EXISTS %I ON public.%I', 'ewp_immutable_' || t, t);
    EXECUTE format(
      'CREATE TRIGGER %I BEFORE UPDATE OR DELETE ON public.%I '
      || 'FOR EACH ROW EXECUTE FUNCTION public.ewp_forbid_mutation()',
      'ewp_immutable_' || t, t
    );
  END LOOP;
END;
$$;

-- ---------------------------------------------------------------------------
-- effective_user_topic_mastery_evidence: the ONLY planner/level source (§4.12d)
-- ---------------------------------------------------------------------------
-- Folds assert/retract/replace per supersession chain. A row is effective when
-- no later row supersedes it AND it is not itself a retraction. Retracted or
-- replaced assertions, and stale evidence, are excluded. The planner and level
-- derivation must read THIS view, never the raw append-only table.
CREATE OR REPLACE VIEW public.effective_user_topic_mastery_evidence AS
  SELECT e.*
  FROM public.user_topic_mastery_evidence e
  WHERE e.evidence_op IN ('assert','replace')
    AND NOT EXISTS (
      SELECT 1
      FROM public.user_topic_mastery_evidence s
      WHERE s.supersedes_evidence_key = e.evidence_key
    );

-- ---------------------------------------------------------------------------
-- RLS (§12)
-- ---------------------------------------------------------------------------

-- Owner-readable: sessions and their children.
ALTER TABLE public.writing_sessions       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.writing_session_units  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.writing_unit_versions  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.writing_session_checks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.writing_evaluations    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.writing_issue_events   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.writing_issue_resolution_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.writing_issue_projections       ENABLE ROW LEVEL SECURITY;

-- Catalog reads (verified + active only).
ALTER TABLE public.writing_prompts                 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.exam_descriptive_requirements   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.writing_rubrics                 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.writing_issue_type_microtopic_map ENABLE ROW LEVEL SECURITY;

-- Service-role-only (RLS on, NO client allow policy — deliberate, §12.2).
ALTER TABLE public.writing_issue_review_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_topic_mastery_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.writing_evaluation_jobs     ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.writing_mastery_shadow      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.writing_mastery_outbox      ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS writing_sessions_owner_select ON public.writing_sessions;
CREATE POLICY writing_sessions_owner_select ON public.writing_sessions
  FOR SELECT USING (user_id = auth.uid());

DROP POLICY IF EXISTS writing_session_units_owner_select ON public.writing_session_units;
CREATE POLICY writing_session_units_owner_select ON public.writing_session_units
  FOR SELECT USING (EXISTS (
    SELECT 1 FROM public.writing_sessions s
    WHERE s.id = writing_session_units.session_id AND s.user_id = auth.uid()
  ));

DROP POLICY IF EXISTS writing_unit_versions_owner_select ON public.writing_unit_versions;
CREATE POLICY writing_unit_versions_owner_select ON public.writing_unit_versions
  FOR SELECT USING (EXISTS (
    SELECT 1 FROM public.writing_session_units u
    JOIN public.writing_sessions s ON s.id = u.session_id
    WHERE u.id = writing_unit_versions.unit_id AND s.user_id = auth.uid()
  ));

DROP POLICY IF EXISTS writing_session_checks_owner_select ON public.writing_session_checks;
CREATE POLICY writing_session_checks_owner_select ON public.writing_session_checks
  FOR SELECT USING (EXISTS (
    SELECT 1 FROM public.writing_sessions s
    WHERE s.id = writing_session_checks.session_id AND s.user_id = auth.uid()
  ));

-- Feedback-gated owner policy for evaluations and the issue tables (§12.1).
DROP POLICY IF EXISTS writing_evaluations_owner_select ON public.writing_evaluations;
CREATE POLICY writing_evaluations_owner_select ON public.writing_evaluations
  FOR SELECT USING (EXISTS (
    SELECT 1
    FROM public.writing_unit_versions v
    JOIN public.writing_session_units u ON u.id = v.unit_id
    JOIN public.writing_sessions s ON s.id = u.session_id
    WHERE v.id = writing_evaluations.unit_version_id
      AND s.user_id = auth.uid()
      AND (s.mode = 'learning'
           OR (s.feedback_released_at IS NOT NULL AND s.feedback_released_at <= now()))
  ));

DROP POLICY IF EXISTS writing_issue_events_owner_select ON public.writing_issue_events;
CREATE POLICY writing_issue_events_owner_select ON public.writing_issue_events
  FOR SELECT USING (EXISTS (
    SELECT 1
    FROM public.writing_evaluations e
    JOIN public.writing_unit_versions v ON v.id = e.unit_version_id
    JOIN public.writing_session_units u ON u.id = v.unit_id
    JOIN public.writing_sessions s ON s.id = u.session_id
    WHERE e.id = writing_issue_events.evaluation_id
      AND s.user_id = auth.uid()
      AND (s.mode = 'learning'
           OR (s.feedback_released_at IS NOT NULL AND s.feedback_released_at <= now()))
  ));

DROP POLICY IF EXISTS writing_issue_resolution_events_owner_select ON public.writing_issue_resolution_events;
CREATE POLICY writing_issue_resolution_events_owner_select ON public.writing_issue_resolution_events
  FOR SELECT USING (EXISTS (
    SELECT 1
    FROM public.writing_issue_events ie
    JOIN public.writing_evaluations e ON e.id = ie.evaluation_id
    JOIN public.writing_unit_versions v ON v.id = e.unit_version_id
    JOIN public.writing_session_units u ON u.id = v.unit_id
    JOIN public.writing_sessions s ON s.id = u.session_id
    WHERE ie.id = writing_issue_resolution_events.issue_event_id
      AND s.user_id = auth.uid()
      AND (s.mode = 'learning'
           OR (s.feedback_released_at IS NOT NULL AND s.feedback_released_at <= now()))
  ));

DROP POLICY IF EXISTS writing_issue_projections_owner_select ON public.writing_issue_projections;
CREATE POLICY writing_issue_projections_owner_select ON public.writing_issue_projections
  FOR SELECT USING (EXISTS (
    SELECT 1
    FROM public.writing_issue_events ie
    JOIN public.writing_evaluations e ON e.id = ie.evaluation_id
    JOIN public.writing_unit_versions v ON v.id = e.unit_version_id
    JOIN public.writing_session_units u ON u.id = v.unit_id
    JOIN public.writing_sessions s ON s.id = u.session_id
    WHERE ie.id = writing_issue_projections.issue_event_id
      AND s.user_id = auth.uid()
      AND (s.mode = 'learning'
           OR (s.feedback_released_at IS NOT NULL AND s.feedback_released_at <= now()))
  ));

-- Catalog reads: verified + active only.
DROP POLICY IF EXISTS writing_prompts_public_read ON public.writing_prompts;
CREATE POLICY writing_prompts_public_read ON public.writing_prompts
  FOR SELECT USING (reviewer_status = 'verified' AND is_active = true);

DROP POLICY IF EXISTS exam_descriptive_requirements_public_read ON public.exam_descriptive_requirements;
CREATE POLICY exam_descriptive_requirements_public_read ON public.exam_descriptive_requirements
  FOR SELECT USING (reviewer_status = 'verified' AND is_active = true);

DROP POLICY IF EXISTS writing_rubrics_read ON public.writing_rubrics;
CREATE POLICY writing_rubrics_read ON public.writing_rubrics
  FOR SELECT USING (true);

-- Non-sensitive reference data; readable by authenticated users (§4.15).
DROP POLICY IF EXISTS issue_type_microtopic_map_read ON public.writing_issue_type_microtopic_map;
CREATE POLICY issue_type_microtopic_map_read ON public.writing_issue_type_microtopic_map
  FOR SELECT USING (is_active = true);

-- Service-role-only tables: no client allow policy is created, by design.

-- ---------------------------------------------------------------------------
-- Seed: English Language taxonomy + issue_type -> microtopic map
-- Deterministic md5('ewp:...')::uuid ids; re-run safe.
-- ---------------------------------------------------------------------------
DO $$
DECLARE
  v_subject uuid := md5('ewp:subject:english-language')::uuid;
  v_parent  uuid;
  v_micro   uuid;
  rec       record;
  parents   text[][] := ARRAY[
    ARRAY['sentence-construction','Sentence Construction'],
    ARRAY['grammar','Grammar'],
    ARRAY['vocabulary-in-context','Vocabulary in Context'],
    ARRAY['paragraph-writing','Paragraph Writing']
  ];
  -- issue_type, parent_slug, microtopic_slug, microtopic_name
  micros    text[][] := ARRAY[
    ARRAY['sentence_fragment','sentence-construction','sentence-structure','Sentence Structure'],
    ARRAY['run_on_sentence','sentence-construction','sentence-structure','Sentence Structure'],
    ARRAY['subject_verb_agreement','grammar','subject-verb-agreement','Subject-Verb Agreement'],
    ARRAY['tense','grammar','tense','Tense'],
    ARRAY['article','grammar','articles','Articles'],
    ARRAY['preposition','grammar','prepositions','Prepositions'],
    ARRAY['pronoun_reference','grammar','pronoun-reference','Pronoun Reference'],
    ARRAY['modifier','grammar','modifiers','Modifiers'],
    ARRAY['spelling','grammar','spelling','Spelling'],
    ARRAY['punctuation','grammar','punctuation','Punctuation'],
    ARRAY['word_choice','vocabulary-in-context','word-choice','Word Choice'],
    ARRAY['collocation','vocabulary-in-context','collocations','Collocations'],
    ARRAY['redundancy','vocabulary-in-context','redundancy','Redundancy'],
    ARRAY['informal_usage','vocabulary-in-context','formal-vocabulary','Formal Vocabulary'],
    ARRAY['cohesion','paragraph-writing','cohesion','Cohesion'],
    ARRAY['logical_order','paragraph-writing','logical-order','Logical Order'],
    ARRAY['off_topic','paragraph-writing','content-relevance','Content Relevance'],
    ARRAY['word_limit','paragraph-writing','word-limit','Word Limit'],
    ARRAY['format_violation','paragraph-writing','format-rules','Format Rules']
  ];
  i int;
BEGIN
  -- Subject
  INSERT INTO public.subjects (id, slug, name, subject_group, description, is_active)
  VALUES (v_subject, 'english-language', 'English Language', 'language',
          'English writing practice taxonomy (EWP).', true)
  ON CONFLICT (slug) DO NOTHING;
  SELECT id INTO v_subject FROM public.subjects WHERE slug = 'english-language';

  -- Parent topics (level='topic')
  FOR i IN 1 .. array_length(parents, 1) LOOP
    INSERT INTO public.topics (id, subject_id, parent_topic_id, slug, name, level, is_active)
    SELECT md5('ewp:topic:' || parents[i][1])::uuid, v_subject, NULL,
           parents[i][1], parents[i][2], 'topic', true
    WHERE NOT EXISTS (
      SELECT 1 FROM public.topics
      WHERE subject_id = v_subject AND parent_topic_id IS NULL AND slug = parents[i][1]
    );
  END LOOP;

  -- Microtopics (level='microtopic') + issue_type map
  FOR i IN 1 .. array_length(micros, 1) LOOP
    SELECT id INTO v_parent FROM public.topics
      WHERE subject_id = v_subject AND parent_topic_id IS NULL AND slug = micros[i][2];

    INSERT INTO public.topics (id, subject_id, parent_topic_id, slug, name, level, is_active)
    SELECT md5('ewp:microtopic:' || micros[i][3])::uuid, v_subject, v_parent,
           micros[i][3], micros[i][4], 'microtopic', true
    WHERE NOT EXISTS (
      SELECT 1 FROM public.topics
      WHERE subject_id = v_subject AND parent_topic_id = v_parent AND slug = micros[i][3]
    );

    SELECT id INTO v_micro FROM public.topics
      WHERE subject_id = v_subject AND parent_topic_id = v_parent AND slug = micros[i][3];

    INSERT INTO public.writing_issue_type_microtopic_map (issue_type, microtopic_id, map_version, is_active)
    SELECT micros[i][1], v_micro, 1, true
    WHERE NOT EXISTS (
      SELECT 1 FROM public.writing_issue_type_microtopic_map
      WHERE issue_type = micros[i][1] AND map_version = 1
    );
  END LOOP;
END;
$$;

-- ---------------------------------------------------------------------------
-- Grants (service_role owns all writes; authenticated reads gated by RLS)
-- ---------------------------------------------------------------------------
GRANT SELECT ON public.effective_user_topic_mastery_evidence TO authenticated, service_role;

SELECT pg_notify('pgrst', 'reload schema');
