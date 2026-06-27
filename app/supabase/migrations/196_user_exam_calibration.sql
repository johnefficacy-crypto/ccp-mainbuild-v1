-- Migration 196: user_exam_calibration — onboarding calibration gate state (per user, per exam)
--
-- This row is the explicit exam-level gate that controls onboarding calibration.
-- The per-subject user_topic_self_assessment rows remain the underlying evidence;
-- THIS record controls the gate. Specifically it controls:
--   * whether the pre-plan calibration interstitial is shown, and
--   * whether plan generation is unlocked.
--
-- status='completed' means the user answered the full required subject set.
-- status='skipped'   means the user explicitly skipped calibration.
--
-- required_subject_set_hash captures the set of required subjects at the moment the
-- gate decision was made. If exam coverage later changes (the required subject set
-- shifts), the hash mismatch can trigger a NON-BLOCKING "update your starting point"
-- prompt without re-gating plan generation.
--
-- Writes are service-role-only: the backend API owns gate transitions and writes via
-- the service-role key (which bypasses RLS). Clients only read their own row; the
-- absence of any INSERT/UPDATE/DELETE policy means authenticated/anon cannot write.

CREATE TABLE public.user_exam_calibration (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  exam_id uuid NOT NULL REFERENCES public.exams(id) ON DELETE CASCADE,
  status text NOT NULL CHECK (status IN ('completed','skipped')),
  required_subject_set_hash text,
  attempts_used int CHECK (attempts_used IS NULL OR attempts_used >= 0),
  completed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_user_exam_calibration ON public.user_exam_calibration(user_id, exam_id);
CREATE INDEX idx_user_exam_calibration_user ON public.user_exam_calibration(user_id);
ALTER TABLE public.user_exam_calibration ENABLE ROW LEVEL SECURITY;
-- Writes are service-role-only (backend API owns gate transitions); clients read their own row.
CREATE POLICY "owner_select" ON public.user_exam_calibration
  FOR SELECT USING (user_id = auth.uid());
