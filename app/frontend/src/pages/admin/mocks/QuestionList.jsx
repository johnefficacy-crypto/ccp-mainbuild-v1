import React, { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../../../lib/api";
import StatusBadge from "./components/StatusBadge";
import { Plus, RefreshCw } from "lucide-react";

const STATUSES = ["", "draft", "in_review", "needs_changes", "verified", "published", "archived"];

const S = {
  page: { padding: 24, color: "#e5e7eb", minHeight: "100vh" },
  header: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 },
  title: { fontSize: 22, fontWeight: 700, color: "#f9fafb", margin: 0 },
  filters: { display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap" },
  select: { background: "#111827", border: "1px solid #374151", borderRadius: 6, padding: "6px 10px", color: "#e5e7eb", fontSize: 13, cursor: "pointer" },
  input: { background: "#111827", border: "1px solid #374151", borderRadius: 6, padding: "6px 10px", color: "#e5e7eb", fontSize: 13, minWidth: 180 },
  table: { width: "100%", borderCollapse: "collapse" },
  th: { textAlign: "left", fontSize: 11, color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em", padding: "8px 12px", borderBottom: "1px solid #1f2937" },
  td: { padding: "10px 12px", borderBottom: "1px solid #1f2937", fontSize: 13, color: "#d1d5db", verticalAlign: "middle" },
  btn: { display: "inline-flex", alignItems: "center", gap: 6, background: "#2563eb", color: "#fff", border: "none", borderRadius: 6, padding: "8px 16px", fontSize: 13, fontWeight: 600, cursor: "pointer", textDecoration: "none" },
};

export default function QuestionList() {
  const [params, setParams] = useSearchParams();
  const [data, setData] = useState({ items: [], page: 1, page_size: 50 });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const status   = params.get("status") || "";
  const language = params.get("language") || "";
  const page     = parseInt(params.get("page") || "1", 10);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    const qs = new URLSearchParams({ page, page_size: 50 });
    if (status) qs.set("status", status);
    if (language) qs.set("language", language);
    api.get(`/api/admin/mocks/questions?${qs}`)
      .then(setData)
      .catch((e) => setError(e?.message || "Failed to load"))
      .finally(() => setLoading(false));
  }, [status, language, page]);

  useEffect(() => { load(); }, [load]);

  const set = (key, val) => {
    const next = new URLSearchParams(params);
    if (val) next.set(key, val); else next.delete(key);
    if (key !== "page") next.delete("page");
    setParams(next);
  };

  return (
    <div style={S.page}>
      <div style={S.header}>
        <h1 style={S.title}>Question Bank</h1>
        <div style={{ display: "flex", gap: 10 }}>
          <button onClick={load} style={{ ...S.btn, background: "#374151" }}><RefreshCw size={14} /> Refresh</button>
          <Link to="/admin/mocks/questions/new" style={S.btn}><Plus size={14} /> New Question</Link>
        </div>
      </div>

      <div style={S.filters}>
        <select value={status} onChange={(e) => set("status", e.target.value)} style={S.select}>
          {STATUSES.map((s) => <option key={s} value={s}>{s || "All statuses"}</option>)}
        </select>
        <select value={language} onChange={(e) => set("language", e.target.value)} style={S.select}>
          <option value="">All languages</option>
          <option value="en">English</option>
          <option value="hi">Hindi</option>
        </select>
      </div>

      {error && <div style={{ background: "#450a0a", border: "1px solid #dc2626", borderRadius: 6, padding: "10px 14px", marginBottom: 16, color: "#fca5a5", fontSize: 13 }}>{error}</div>}

      <div style={{ background: "#111827", borderRadius: 8, border: "1px solid #1f2937", overflow: "auto" }}>
        <table style={S.table}>
          <thead>
            <tr>
              <th style={S.th}>Question</th>
              <th style={S.th}>Status</th>
              <th style={S.th}>Difficulty</th>
              <th style={S.th}>Language</th>
              <th style={S.th}>Updated</th>
              <th style={S.th} />
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={6} style={{ ...S.td, textAlign: "center", color: "#6b7280" }}>Loading…</td></tr>
            )}
            {!loading && data.items.length === 0 && (
              <tr><td colSpan={6} style={{ ...S.td, textAlign: "center", color: "#6b7280" }}>No questions found.</td></tr>
            )}
            {data.items.map((q) => (
              <tr key={q.id}>
                <td style={S.td}>
                  <span style={{ display: "block", maxWidth: 480, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {q.question_text}
                  </span>
                </td>
                <td style={S.td}><StatusBadge status={q.reviewer_status} /></td>
                <td style={{ ...S.td, textTransform: "capitalize" }}>{q.difficulty}</td>
                <td style={S.td}>{q.language}</td>
                <td style={{ ...S.td, color: "#6b7280", fontSize: 12 }}>{q.updated_at ? new Date(q.updated_at).toLocaleDateString() : "—"}</td>
                <td style={S.td}>
                  {q.id ? (
                    <Link to={`/admin/mocks/questions/${q.id}`} style={{ color: "#60a5fa", fontSize: 13, textDecoration: "none" }}>
                      View →
                    </Link>
                  ) : (
                    <span className="text-red-400">Missing id</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 12 }}>
        {page > 1 && <button onClick={() => set("page", page - 1)} style={{ ...S.btn, background: "#374151" }}>← Prev</button>}
        {data.items.length === data.page_size && <button onClick={() => set("page", page + 1)} style={S.btn}>Next →</button>}
      </div>
    </div>
  );
}
