/**
 * DocumentSelector — syllabus document picker for the Syllabus Mapper.
 *
 * Fetches from the confirmed CMS endpoint:
 *   GET /api/admin/exam-intelligence-cms/syllabus-documents?exam_id={examId}&limit=100
 *
 * The previous implementation called
 *   GET /api/admin/exam-intelligence/workspace/{examId}/documents
 * which does NOT exist in the backend, producing a perpetual "No documents" state
 * and blocking the mapper ("dead mapper loop"). This fix uses the existing CMS
 * list route that is populated by link-to-syllabus (PR-0 §6).
 *
 * No new backend endpoints are introduced.
 */
import React, { useEffect, useState } from "react";
import { api } from "../../../../lib/api";

const SYLLABUS_DOCS_URL = "/api/admin/exam-intelligence-cms/syllabus-documents";

export default function DocumentSelector({ examId, value, onChange }) {
  const [docs,    setDocs]    = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!examId) return;
    setLoading(true);
    api
      .get(`${SYLLABUS_DOCS_URL}?exam_id=${encodeURIComponent(examId)}&limit=100`)
      .then((d) => setDocs(d?.items || []))
      .catch(() => setDocs([]))
      .finally(() => setLoading(false));
  }, [examId]);

  return (
    <div className="flex items-center gap-2">
      <label
        className="text-sm font-medium text-gray-700"
        htmlFor="syllabus-doc-select"
      >
        Document
      </label>
      <select
        id="syllabus-doc-select"
        data-testid="syllabus-doc-select"
        value={value || ""}
        onChange={(e) => onChange(e.target.value || null)}
        disabled={loading || docs.length === 0}
        className="text-sm border border-gray-300 rounded px-3 py-1.5 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
      >
        <option value="">
          {loading
            ? "Loading…"
            : docs.length === 0
            ? "No documents"
            : "Select a document"}
        </option>
        {docs.map((d) => (
          <option key={d.id} value={d.id}>
            {d.title || d.document_type || d.id}
          </option>
        ))}
      </select>
    </div>
  );
}
