/**
 * Data-layer hook for the English Writing Practice surface (EWP-3).
 *
 * The single API source of truth for `/app/study/practice/english/*` is the
 * backend `/api/study/practice/english/*` surface (AGENTS.md). All mutations go
 * through this hook (via `useApiAction`, which handles optimistic/rollback +
 * toast) rather than raw `fetch`/`api.post` in components.
 */
import { useCallback } from "react";

import { api } from "../../../lib/api";
import useApiAction from "../../../lib/hooks/useApiAction";

const BASE = "/api/study/practice/english";

export default function useEnglishPracticeSession() {
  const { run, busy } = useApiAction();

  // Reads — plain GETs (collections/detail); callers own their loading state.
  const fetchSession = useCallback(
    (sessionId) => api.get(`${BASE}/sessions/${sessionId}`),
    [],
  );

  const fetchEvaluation = useCallback(
    (sessionId, evaluationId) =>
      api.get(`${BASE}/sessions/${sessionId}/evaluations/${evaluationId}`),
    [],
  );

  // Mutations — routed through useApiAction for toast + busy state. Each returns
  // the useApiAction result `{ ok, data | error }`.
  const submitUnit = useCallback(
    (sessionId, unitNumber, answerText, versionNumber, { clientWordCount = null } = {}) =>
      run({
        action: () =>
          api.post(`${BASE}/sessions/${sessionId}/units/${unitNumber}/submit`, {
            answer_text: answerText,
            client_word_count: clientWordCount,
            version_number: versionNumber,
          }),
        successMessage: "Answer submitted",
        errorMessage: "Could not submit your answer",
      }),
    [run],
  );

  const reopenUnit = useCallback(
    (sessionId, unitId, latestVersionId) =>
      run({
        action: () =>
          api.post(`${BASE}/sessions/${sessionId}/units/${unitId}/reopen`, {
            expected_latest_version_id: latestVersionId,
          }),
        errorMessage: "Could not reopen this sentence for a rewrite",
      }),
    [run],
  );

  return { fetchSession, fetchEvaluation, submitUnit, reopenUnit, busy };
}
