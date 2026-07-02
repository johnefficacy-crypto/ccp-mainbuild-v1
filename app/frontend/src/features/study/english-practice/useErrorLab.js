/**
 * Data-layer hook for the Error Lab surface (EWP-4).
 *
 * One API source of truth: the backend read endpoint
 * `GET /api/study/practice/english/error-lab`, which returns the caller's
 * current-state writing issues grouped by microtopic (owner-scoped,
 * feedback-released, `affects_current_state=true`, effective-invalidation
 * aware — the backend enforces the verified-only gating; the client never
 * fetches raw issue rows).
 *
 * Thin wrapper over the shared four-state `useApiCollection` (idle → loading →
 * data | empty | error). No raw `fetch`/`api.get` in components.
 */
import useApiCollection from "../../../lib/hooks/useApiCollection";

const ERROR_LAB_URL = "/api/study/practice/english/error-lab";

export default function useErrorLab() {
  const { items, status, refresh } = useApiCollection(ERROR_LAB_URL, []);
  return { groups: items, status, refresh };
}
