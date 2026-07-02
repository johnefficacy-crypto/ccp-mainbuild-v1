/**
 * Readiness summary table showing target inventory vs actual counts.
 */
import React from "react";

// Target inventory per the spec
const TARGETS = {
  sentence_construction: 50,
  sentence_correction: 50,
  vocabulary_in_context: 50,
  sentence_rewrite: 0, // Not required in spec
  sentence_reconstruction: 0,
  paragraph_writing: 20,
  summary_writing: 0,
  precis_practice: 0,
  essay_practice: 0,
  letter_practice: 0,
};

// Map internal type names to display labels
const TYPE_LABELS = {
  sentence_construction: "Sentence construction",
  sentence_correction: "Sentence correction",
  vocabulary_in_context: "Vocabulary context",
  sentence_rewrite: "Sentence rewrite",
  sentence_reconstruction: "Sentence reconstruction",
  paragraph_writing: "Scaffolded paragraphs",
  summary_writing: "Summary writing",
  precis_practice: "Précis practice",
  essay_practice: "Essay practice",
  letter_practice: "Letter practice",
};

// Spec: 100 grammar-rule exercises (mapped to sentence_correction)
const GRAMMAR_RULES_TARGET = 100;

export default function PromptReadinessSummary({ summary = null }) {
  if (!summary) {
    return (
      <div style={{ padding: "1rem", color: "var(--ink-mute)" }}>
        Loading readiness data…
      </div>
    );
  }

  // Calculate total active and required
  const requiredTypes = ["sentence_construction", "sentence_correction", "vocabulary_in_context", "paragraph_writing"];
  let totalActive = 0;
  let allMettle = true;

  const rows = requiredTypes.map((type) => {
    const counts = summary[type] || { required: 0, authored: 0, verified: 0, active: 0 };
    const target = type === "sentence_correction" ? GRAMMAR_RULES_TARGET : TARGETS[type];
    const metTarget = counts.active >= target;

    if (!metTarget) allMettle = false;

    totalActive += counts.active;

    return {
      type,
      label: type === "sentence_correction" ? "Grammar rules" : TYPE_LABELS[type],
      target,
      authored: counts.authored || 0,
      verified: counts.verified || 0,
      active: counts.active || 0,
      metTarget,
    };
  });

  const launchReady = allMettle && totalActive >= 270;

  return (
    <div style={{ marginBottom: "2rem" }}>
      <div style={{ marginBottom: "1rem" }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>
          Readiness
        </h3>
      </div>

      <table className="data-table" style={{ marginBottom: "1rem" }}>
        <thead>
          <tr>
            <th>Type</th>
            <th style={{ textAlign: "right" }}>Required</th>
            <th style={{ textAlign: "right" }}>Authored</th>
            <th style={{ textAlign: "right" }}>Verified</th>
            <th style={{ textAlign: "right" }}>Active</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.type}>
              <td>
                <span style={{ fontWeight: 500 }}>{row.label}</span>
              </td>
              <td style={{ textAlign: "right" }}>{row.target}</td>
              <td style={{ textAlign: "right" }}>{row.authored}</td>
              <td style={{ textAlign: "right" }}>{row.verified}</td>
              <td style={{ textAlign: "right" }}>
                <span
                  className="badge"
                  style={{
                    background: row.metTarget ? "var(--success, #0b8)" : "var(--warn, #f80)",
                  }}
                >
                  {row.active} {row.metTarget ? "✓" : ""}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div
        style={{
          padding: "0.75rem 1rem",
          background: launchReady ? "var(--success-light, #e8f5e9)" : "var(--warn-light, #fff8e1)",
          border: `1px solid ${launchReady ? "var(--success, #0b8)" : "var(--warn, #f80)"}`,
          borderRadius: 4,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div>
          <div style={{ fontWeight: 600, fontSize: 13 }}>
            Total active: {totalActive} / 270
          </div>
          <div style={{ fontSize: 12, opacity: 0.7, marginTop: 2 }}>
            Launch ready: {launchReady ? "Yes ✓" : "No"}
          </div>
        </div>
      </div>
    </div>
  );
}
