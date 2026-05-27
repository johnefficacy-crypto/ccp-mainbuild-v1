import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../../lib/api";
import StatusBadge from "./components/StatusBadge";
import { RefreshCw } from "lucide-react";

const S = {
  page: { padding: 24, color: "#e5e7eb", minHeight: "100vh" },
  header: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 },
  title: { fontSize: 22, fontWeight: 700, color: "#f9fafb", margin: 0 },
  table: { width: "100%", borderCollapse: "collapse" },
  th: { textAlign: "left", fontSize: 11, color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em", padding: "8px 12px", borderBottom: "1px solid #1f2937" },
  td: { padding: "10px 12px", borderBottom: "1px solid #1f2937", fontSize: 13, color: "#d1d5db", verticalAlign: "middle" },
  btn: { display: "inline-flex", alignItems: "center", gap: 6, background: "#374151", color: "#fff", border: "none", borderRadius: 6, padding: "8px 16px", fontSize: 13, fontWeight: 600, cursor: "pointer" },
};

export default function ReviewQueue() {
  const [data, setData] = useState({ items: [], page: 1 });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    api.get(`/api/admin/mocks/review-queue?page=${page}&page_size=50`)
      .then(setData)
      .catch((e) => setError(e?.message || "Failed to load"))
      .finally(() => setLoading(false));
  }, [page]);

  useEffect(() => { load(); }, [load]);

  return (
    <div style={S.page}>
      <div style={S.header}>
        <div>
          <h1 style={S.title}>Review Queue</h1>
          <p style={{ margin: "4px 0 0", fontSize: 13, color: "#6b7280" }}>Questions awaiting your review.</p>
        </div>
        <button onClick={load} style={S.btn}><RefreshCw size={14} /> Refresh</button>
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
              <th style={S.th}>Submitted</th>
              <th style={S.th} />
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={6} style={{ ...S.td, textAlign: "center", color: "#6b7280" }}>Loading…</td></tr>
            )}
            {!loading && data.items.length === 0 && (
              <tr><td colSpan={6} style={{ ...S.td, textAlign: "center", color: "#6b7280" }}>Queue is empty 🎉</td></tr>
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
                      Review →
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
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 12 }}>
        {page > 1 && <button onClick={() => setPage((p) => p - 1)} style={S.btn}>← Prev</button>}
        {data.items.length === 50 && <button onClick={() => setPage((p) => p + 1)} style={{ ...S.btn, background: "#2563eb" }}>Next →</button>}
      </div>
    </div>
  );
}
