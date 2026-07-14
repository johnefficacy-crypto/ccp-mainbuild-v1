/**
 * Data-layer hook for the personalized Improvement Lab strategy feeds (GQR-S6).
 *
 * One API source of truth per subject — the owner-scoped, verified-only learner
 * feeds `GET /api/study/improvement-lab/{quant|reasoning}` (the backend enforces
 * ownership, the submitted-only + bounded reads, and the verified-only projection;
 * the client never fetches raw strategy rows). Thin wrapper over the shared
 * four-state `useApiCollection` (loading → live | empty | error). No raw
 * `fetch`/`api.get` in components.
 */
import useApiCollection from "../../../lib/hooks/useApiCollection";

const FEED_URLS = {
  quant: "/api/study/improvement-lab/quant",
  reasoning: "/api/study/improvement-lab/reasoning",
};

export default function useStrategyFeed(subject) {
  const { items, status, refresh } = useApiCollection(FEED_URLS[subject], []);
  return { items, status, refresh };
}
