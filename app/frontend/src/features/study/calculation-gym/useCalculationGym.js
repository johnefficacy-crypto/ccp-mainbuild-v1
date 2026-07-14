import { useCallback } from "react";

import { api } from "../../../lib/api";
import useApiAction from "../../../lib/hooks/useApiAction";

const BASE = "/api/study/calculation-gym";

export default function useCalculationGym() {
  const { run, busy } = useApiAction();

  const fetchSession = useCallback(
    (sessionId) => api.get(`${BASE}/sessions/${sessionId}`),
    [],
  );

  const submitSession = useCallback(
    (sessionId, answers) =>
      run({
        action: () => api.post(`${BASE}/sessions/${sessionId}/submit`, { answers }),
        successMessage: "Calculation Gym completed",
        errorMessage: "Could not submit this session. Please try again.",
      }),
    [run],
  );

  return { fetchSession, submitSession, busy };
}
