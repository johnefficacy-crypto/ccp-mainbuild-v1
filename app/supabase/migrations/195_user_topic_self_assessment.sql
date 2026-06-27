-- Migration 195: user_topic_self_assessment — onboarding knowledge priors

CREATE TABLE public.user_topic_self_assessment (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  exam_id uuid NOT NULL REFERENCES public.exams(id) ON DELETE CASCADE,
  subject_id uuid REFERENCES public.subjects(id) ON DELETE CASCADE,
  topic_id   uuid REFERENCES public.topics(id)   ON DELETE CASCADE,
  band text NOT NULL CHECK (band IN ('strong','decent','weak','new')),
  prior_mastery numeric(5,2)
    CHECK (prior_mastery IS NULL OR (prior_mastery >= 0 AND prior_mastery <= 100)),
  report_confidence numeric(4,3) NOT NULL DEFAULT 0.5
    CHECK (report_confidence >= 0 AND report_confidence <= 1),
  attempts_used int CHECK (attempts_used IS NULL OR attempts_used >= 0),
  source text NOT NULL DEFAULT 'onboarding_self_report',
  assessed_at timestamptz NOT NULL DEFAULT now(),
  superseded_at timestamptz,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK ((subject_id IS NOT NULL) <> (topic_id IS NOT NULL))
);

CREATE UNIQUE INDEX uq_self_assessment_subject
  ON public.user_topic_self_assessment(user_id, exam_id, subject_id)
  WHERE subject_id IS NOT NULL AND topic_id IS NULL;
CREATE UNIQUE INDEX uq_self_assessment_topic
  ON public.user_topic_self_assessment(user_id, exam_id, topic_id)
  WHERE topic_id IS NOT NULL;
CREATE INDEX idx_self_assessment_user_exam
  ON public.user_topic_self_assessment(user_id, exam_id);

ALTER TABLE public.user_topic_self_assessment ENABLE ROW LEVEL SECURITY;
-- Writes are service-role-only: the backend API writes via the service-role key,
-- which bypasses RLS. The server owns the band->prior_mastery and
-- attempts->report_confidence derivation; clients submit only a band. Exposing a
-- permissive write policy here would let a signed-in client set arbitrary
-- prior_mastery/report_confidence/attempts_used/source via PostgREST, bypassing
-- that server-owned mapping. So we grant clients READ-ONLY access to their own
-- rows; the absence of any INSERT/UPDATE/DELETE policy means authenticated/anon
-- cannot write.
CREATE POLICY "owner_select" ON public.user_topic_self_assessment
  FOR SELECT USING (user_id = auth.uid());
