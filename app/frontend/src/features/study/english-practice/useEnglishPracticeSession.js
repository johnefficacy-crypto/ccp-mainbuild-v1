/**
 * Data-layer hook for the English Writing Practice surface (EWP-3).
 *
 * The single API source of truth for `/app/study/practice/english/*` is the
 * backend `/api/study/practice/english/*` surface (AGENTS.md). Mutations go
 * through this hook rather than raw `fetch`/`api.post` in components. Most use
 * `useApiAction` (optimistic/rollback + auto error toast); the exception is
 * `launchWriting`, deliberately returned as a bare promise so its EXPECTED
 * `409 no_eligible_prompt` is handled by the caller as a calm state instead of
 * firing an auto error toast (see LaunchWritingPracticeButton).
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

  // EWP-SP3 server-owned launch. The browser never picks a prompt — the server
  // verifies task ownership, reads the pinned exam context, resolves + gates
  // candidate prompts, and creates (or idempotently re-enters) the session,
  // returning `{ session_id, practice_route }`. The endpoint lives under
  // `/api/study/tasks/*` (the planner-task action namespace this surface already
  // uses for task status), NOT under BASE, but it funnels into the same
  // writing-session runtime this hook owns. Returned as a bare promise (not via
  // `useApiAction`) so the caller can distinguish the EXPECTED 409
  // `no_eligible_prompt` state from a hard error without an automatic error
  // toast firing.
  const launchWriting = useCallback(
    (studyTaskId) => api.post(`/api/study/tasks/${studyTaskId}/launch-writing`, {}),
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

  return { fetchSession, fetchEvaluation, launchWriting, submitUnit, reopenUnit, busy };
}
