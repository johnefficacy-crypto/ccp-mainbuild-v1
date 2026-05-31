import React, { useEffect, useState } from "react";
import { api } from "../../../../lib/api";

export default function DocumentSelector({ examId, value, onChange }) {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!examId) return;
    setLoading(true);
    api
      .get(`/api/admin/exam-intelligence/workspace/${examId}/documents`)
      .then((d) => setDocs(d?.items || []))
      .catch(() => setDocs([]))
      .finally(() => setLoading(false));
  }, [examId]);

  return (
    <div className="flex items-center gap-2">
      <label className="text-sm font-medium text-gray-700" htmlFor="syllabus-doc-select">
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
          {loading ? "Loading…" : docs.length === 0 ? "No documents" : "Select a document"}
        </option>
        {docs.map((d) => (
          <option key={d.id} value={d.id}>
            {d.file_name || d.id}
          </option>
        ))}
      </select>
    </div>
  );
}
