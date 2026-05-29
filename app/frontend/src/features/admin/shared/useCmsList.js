import { useQuery } from "@tanstack/react-query";
import { api } from "../../../lib/api";

const CMS_BASE = "/api/admin/exam-intelligence-cms";
// Backend list endpoints cap at 200 rows/page. These are admin reference
// tables (families/exams/cycles/phases) that stay well under that once
// cascade-filtered, so a single page is the working set for the picker.
const LIST_LIMIT = 200;

/**
 * Fetch + cache a CMS list endpoint for use in a picker.
 *
 * `filters` are passed through as query params; empty values are dropped
 * so an unset parent doesn't over-constrain the child. The active filter
 * set is part of the query key, so changing a parent selection refetches
 * the child list with the new param (cascade).
 */
export default function useCmsList(endpoint, filters = {}) {
  const active = Object.fromEntries(
    Object.entries(filters).filter(([, v]) => v != null && v !== ""),
  );
  const query = useQuery({
    queryKey: ["cms-list", endpoint, active],
    queryFn: async () => {
      const params = new URLSearchParams({ limit: String(LIST_LIMIT), ...active });
      const data = await api.get(`${CMS_BASE}/${endpoint}?${params.toString()}`);
      return Array.isArray(data?.items) ? data.items : [];
    },
    // Reference data changes rarely; keep it warm for the session.
    staleTime: 5 * 60 * 1000,
  });
  return {
    items: query.data || [],
    loading: query.isLoading,
    error: query.error,
  };
}
