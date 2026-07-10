import React from "react";
import { Navigate, useLocation, useParams } from "react-router-dom";

// Compatibility redirect: the exam intelligence detail page moved from
// /app/eligibility/exams/:slug to the top-level /app/exam-intelligence/exams/:slug
// (PR #942 item 13). Old links keep working; the hash (e.g. #pyq-explorer) is
// preserved so deep links and attempt back-links land on the right section.
export default function ExamDetailRedirect() {
  const { slug } = useParams();
  const { hash } = useLocation();
  return <Navigate to={`/app/exam-intelligence/exams/${slug}${hash || ""}`} replace />;
}
