/**
 * Content Studio consolidation (content-studio.md §3.1): the three legacy Mock
 * Content destinations redirect to the equivalent Content Studio tab, carrying
 * their query params (filters, pagination) through the redirect so deep links
 * and back-button history are preserved.
 *
 * Extracted from adminRoutes.jsx so the param-carry-through can be unit-tested
 * without mounting the whole admin route tree.
 */
import React from "react";
import { Navigate, useLocation } from "react-router-dom";

export default function MockContentRedirect({ tab }) {
  const location = useLocation();
  const search = new URLSearchParams(location.search);
  search.set("tab", tab);
  search.set("type", "objective_question");
  return <Navigate to={`/admin/content-studio?${search.toString()}`} replace />;
}
