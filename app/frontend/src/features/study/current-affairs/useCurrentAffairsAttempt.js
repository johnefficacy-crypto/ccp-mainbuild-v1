/**
 * Data-layer hook for the GA Current-Affairs learner attempt surface (GQR-G5).
 *
 * The single API source of truth for `/app/study/current-affairs/attempts/*` is the
 * backend `/api/study/current-affairs/*` surface. Mutations go through this hook
 * rather than raw `fetch`/`api.post` in components (frontend governance).
 *
 * The learner never picks a bundle or a question set — those were frozen at launch by
 * the Subject Practice Hub `weekly_current_affairs` handler. This hook only reads the
 * frozen attempt, persists per-question answers (owner + in-progress + frozen-option +
 * monotonic `client_seq` all enforced server-side), and submits for inline scoring.
 * Answer/explanation/§10 provenance stay hidden until the attempt is submitted.
 */
import { useCallback } from "react";

import { api } from "../../../lib/api";
import useApiAction from "../../../lib/hooks/useApiAction";

const BASE = "/api/study/current-affairs";

export default function useCurrentAffairsAttempt() {
  const { run, busy } = useApiAction();

  // Read — plain GET; the caller owns its loading/resume state.
  const fetchAttempt = useCallback(
    (attemptId) => api.get(`${BASE}/attempts/${attemptId}`),
    [],
  );

  // Persist one answer. Silent success (no toast) — answering a question is a
  // high-frequency action, like a mock save. `client_seq` is a per-question
  // monotonic counter; an equal/lower seq is an idempotent server no-op.
  const saveAnswer = useCallback(
    (attemptId, { questionId, selectedOptionId = null, isMarkedForReview = false,
                   timeSpentSec = 0, clientSeq = 0 }) =>
      run({
        action: () =>
          api.post(`${BASE}/attempts/${attemptId}/answer`, {
            question_id: questionId,
            selected_option_id: selectedOptionId,
            is_marked_for_review: isMarkedForReview,
            time_spent_sec: timeSpentSec,
            client_seq: clientSeq,
          }),
        errorMessage: "Could not save your answer. Please try again.",
      }),
    [run],
  );

  // Submit for inline scoring + post-submit provenance reveal. No mastery/SRS write
  // ever fires (GA never enters the mock attempt path).
  const submitAttempt = useCallback(
    (attemptId) =>
      run({
        action: () => api.post(`${BASE}/attempts/${attemptId}/submit`, {}),
        successMessage: "Attempt submitted",
        errorMessage: "Could not submit your attempt. Please try again.",
      }),
    [run],
  );

  return { fetchAttempt, saveAnswer, submitAttempt, busy };
}
