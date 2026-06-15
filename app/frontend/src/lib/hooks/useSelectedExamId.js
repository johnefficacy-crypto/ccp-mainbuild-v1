import { useParams } from "react-router-dom";

/**
 * Selected-exam context = URL single source of truth (Wave 4.6A D-B lock).
 *
 * Returns the currently-selected exam id by reading the `:exam_id` route
 * param directly. It is intentionally read-through: there is NO useState /
 * useReducer / context that retains an independent selected exam. The URL is
 * the store, so the value can never go stale relative to the address bar and
 * there is no second selector to keep in sync.
 *
 * @returns {string|null} the selected exam id, or null when none is in the URL.
 */
export default function useSelectedExamId() {
  const { exam_id } = useParams();
  return exam_id ?? null;
}
