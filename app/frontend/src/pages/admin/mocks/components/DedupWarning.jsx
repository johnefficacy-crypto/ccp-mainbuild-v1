import React from "react";
import { AlertTriangle, XCircle } from "lucide-react";

/**
 * DedupWarning — shown in QuestionEditor when a dedup-check returns results.
 *
 * Props:
 *   result: { fingerprint_match, trigram_neighbors, similarity_threshold }
 *   onDismiss: () => void
 */
export default function DedupWarning({ result, onDismiss }) {
  if (!result) return null;
  const { fingerprint_match, trigram_neighbors = [] } = result;
  const hasBlock  = !!fingerprint_match;
  const hasNeighbors = trigram_neighbors.length > 0;
  if (!hasBlock && !hasNeighbors) return null;

  return (
    <div style={{
      border: `1px solid ${hasBlock ? "#dc2626" : "#d97706"}`,
      borderRadius: 8,
      background: hasBlock ? "#1a0505" : "#1c1004",
      padding: "12px 16px",
      marginBottom: 16,
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {hasBlock
            ? <XCircle size={18} color="#ef4444" />
            : <AlertTriangle size={18} color="#f59e0b" />}
          <span style={{ fontWeight: 600, color: hasBlock ? "#ef4444" : "#f59e0b", fontSize: 14 }}>
            {hasBlock ? "Exact duplicate — save blocked" : "Similar questions found"}
          </span>
        </div>
        {onDismiss && (
          <button onClick={onDismiss} style={{ background: "none", border: "none", cursor: "pointer", color: "#9ca3af", fontSize: 18, lineHeight: 1 }}>×</button>
        )}
      </div>

      {hasBlock && (
        <div style={{ marginTop: 8, fontSize: 13, color: "#fca5a5" }}>
          Fingerprint collision with question <strong>{fingerprint_match.id}</strong>
          {" "}(<em>{fingerprint_match.reviewer_status}</em>).
          Publishers can override with <code>X-Override-Fingerprint: true</code>.
        </div>
      )}

      {hasNeighbors && (
        <div style={{ marginTop: 10 }}>
          <div style={{ fontSize: 12, color: "#9ca3af", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            Top similar questions
          </div>
          <ul style={{ margin: 0, padding: 0, listStyle: "none" }}>
            {trigram_neighbors.map((n) => (
              <li key={n.id} style={{
                fontSize: 13, color: "#d1d5db",
                padding: "4px 0",
                borderBottom: "1px solid #374151",
                display: "flex", justifyContent: "space-between",
              }}>
                <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {n.question_text}
                </span>
                <span style={{ marginLeft: 12, color: "#f59e0b", flexShrink: 0 }}>
                  {Math.round((n.similarity || 0) * 100)}%
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
