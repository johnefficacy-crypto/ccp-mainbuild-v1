import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../../../lib/api";

export default function MockResult() {
  const { attemptId } = useParams();
  const navigate = useNavigate();
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await api.get(`/study/mocks/attempts/${attemptId}/result`);
        if (!cancelled) setResult(data);
      } catch (e) {
        if (!cancelled) setError(e?.message || "Could not load result.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [attemptId]);

  if (loading) return <div style={styles.center}>Loading result…</div>;
  if (error) return <div style={styles.center}>Error: {error}</div>;
  if (!result) return null;

  const { score_raw, score_percentage, total_correct, total_wrong, total_unattempted, per_question = [] } = result;
  const total = per_question.length;

  return (
    <div style={styles.page}>
      {/* Score card */}
      <div style={styles.scoreCard}>
        <h2 style={styles.heading}>Result</h2>
        <div style={styles.bigScore}>{score_percentage ?? 0}%</div>
        <div style={styles.rawScore}>Raw score: {score_raw ?? 0}</div>
        <div style={styles.pills}>
          <span style={{ ...styles.pill, background: "#16a34a" }}>✓ {total_correct ?? 0} correct</span>
          <span style={{ ...styles.pill, background: "#dc2626" }}>✗ {total_wrong ?? 0} wrong</span>
          <span style={{ ...styles.pill, background: "#374151" }}>— {total_unattempted ?? 0} skipped</span>
        </div>
        <div style={styles.totals}>Total questions: {total}</div>
      </div>

      {/* Per-question breakdown */}
      <div style={styles.breakdownSection}>
        <h3 style={styles.subHeading}>Question Breakdown</h3>
        {per_question.map((q, i) => {
          const isCorrect = q.is_correct === true;
          const isWrong = q.is_correct === false;
          const borderColor = isCorrect ? "#16a34a" : isWrong ? "#dc2626" : "#374151";
          return (
            <div key={q.question_id} style={{ ...styles.qCard, borderLeft: `4px solid ${borderColor}` }}>
              <div style={styles.qHeader}>
                <span style={styles.qNum}>Q{i + 1}</span>
                <span style={{
                  ...styles.badge,
                  background: isCorrect ? "#166534" : isWrong ? "#991b1b" : "#374151",
                  color: isCorrect ? "#bbf7d0" : isWrong ? "#fecaca" : "#9ca3af",
                }}>
                  {isCorrect ? "Correct" : isWrong ? "Wrong" : "Skipped"}
                </span>
                {q.marks_awarded !== null && q.marks_awarded !== undefined && (
                  <span style={styles.marksAwarded}>
                    {q.marks_awarded >= 0 ? "+" : ""}{Number(q.marks_awarded).toFixed(2)} marks
                  </span>
                )}
              </div>
              <p style={styles.qText}>{q.question_text}</p>
              <div style={styles.optList}>
                {(q.options || []).map((opt) => {
                  const isCorrectOpt = opt.id === q.correct_option_id;
                  const isSelected = opt.id === q.selected_option_id;
                  let bg = "transparent";
                  if (isCorrectOpt) bg = "#166534";
                  else if (isSelected && !isCorrectOpt) bg = "#7f1d1d";
                  return (
                    <div
                      key={opt.id}
                      style={{
                        ...styles.opt,
                        background: bg,
                        border: isCorrectOpt
                          ? "1px solid #16a34a"
                          : isSelected
                          ? "1px solid #dc2626"
                          : "1px solid #374151",
                      }}
                    >
                      <span style={styles.optIdx}>{opt.option_index}.</span>
                      {opt.option_text}
                      {isCorrectOpt && <span style={styles.correctTag}> ✓ correct</span>}
                      {isSelected && !isCorrectOpt && <span style={styles.wrongTag}> ✗ your answer</span>}
                    </div>
                  );
                })}
              </div>
              {q.explanation && (
                <div style={styles.explanation}>
                  <strong>Explanation:</strong> {q.explanation}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div style={styles.footer}>
        <button style={styles.backBtn} onClick={() => navigate("/app/study/mocks")}>
          ← Back to Mocks
        </button>
      </div>
    </div>
  );
}

const styles = {
  page: { minHeight: "100vh", background: "#111827", color: "#f9fafb", padding: "24px 16px", maxWidth: 760, margin: "0 auto" },
  center: { textAlign: "center", marginTop: 80, color: "#9ca3af" },
  scoreCard: { background: "#1f2937", borderRadius: 12, padding: 28, textAlign: "center", marginBottom: 24 },
  heading: { margin: "0 0 12px", fontSize: 22, fontWeight: 700 },
  bigScore: { fontSize: 56, fontWeight: 800, color: "#60a5fa", lineHeight: 1 },
  rawScore: { color: "#9ca3af", marginTop: 6, fontSize: 15 },
  pills: { display: "flex", gap: 10, justifyContent: "center", marginTop: 16, flexWrap: "wrap" },
  pill: { padding: "4px 12px", borderRadius: 20, fontSize: 14, fontWeight: 600, color: "#fff" },
  totals: { marginTop: 10, color: "#6b7280", fontSize: 14 },
  breakdownSection: { display: "flex", flexDirection: "column", gap: 16 },
  subHeading: { fontSize: 18, fontWeight: 600, marginBottom: 8 },
  qCard: { background: "#1f2937", borderRadius: 10, padding: "16px 18px" },
  qHeader: { display: "flex", alignItems: "center", gap: 10, marginBottom: 10, flexWrap: "wrap" },
  qNum: { fontWeight: 700, color: "#9ca3af", fontSize: 13 },
  badge: { padding: "2px 10px", borderRadius: 12, fontSize: 12, fontWeight: 600 },
  marksAwarded: { fontSize: 13, color: "#9ca3af", marginLeft: "auto" },
  qText: { fontSize: 15, lineHeight: 1.6, margin: "0 0 12px", color: "#e5e7eb" },
  optList: { display: "flex", flexDirection: "column", gap: 6 },
  opt: { padding: "8px 12px", borderRadius: 6, fontSize: 14, color: "#f3f4f6", display: "flex", gap: 8, alignItems: "flex-start" },
  optIdx: { fontWeight: 700, color: "#6b7280", minWidth: 18 },
  correctTag: { color: "#86efac", fontWeight: 600, marginLeft: 4 },
  wrongTag: { color: "#fca5a5", fontWeight: 600, marginLeft: 4 },
  explanation: { marginTop: 12, padding: "10px 14px", background: "#111827", borderRadius: 6, fontSize: 14, color: "#9ca3af" },
  footer: { marginTop: 28, paddingBottom: 24 },
  backBtn: { padding: "10px 22px", background: "#374151", color: "#f9fafb", border: "none", borderRadius: 8, cursor: "pointer", fontSize: 15 },
};
