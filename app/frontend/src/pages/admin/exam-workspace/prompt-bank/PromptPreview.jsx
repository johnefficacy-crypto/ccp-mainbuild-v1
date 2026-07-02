/**
 * Preview modal showing how the prompt appears to aspirants.
 * Shows exercise type, prompt text, source text, constraints, etc.
 */
import React from "react";

const EXERCISE_TYPE_LABELS = {
  sentence_construction: "Construct a sentence",
  sentence_correction: "Correct the sentence",
  vocabulary_in_context: "Use the word in context",
  sentence_rewrite: "Rewrite for clarity",
  sentence_reconstruction: "Reconstruct the sentence",
  paragraph_writing: "Write a paragraph",
  summary_writing: "Summarize the text",
  precis_practice: "Write a précis",
  essay_practice: "Write an essay",
  letter_practice: "Write a letter",
};

export default function PromptPreview({ prompt, onClose }) {
  const exerciseLabel = EXERCISE_TYPE_LABELS[prompt.exercise_type] || prompt.exercise_type;

  return (
    <div
      className="modal-overlay"
      onClick={onClose}
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: "rgba(0,0,0,0.5)",
        zIndex: 101,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div
        className="modal"
        onClick={(e) => e.stopPropagation()}
        style={{
          width: "min(600px, 90vw)",
          maxHeight: "85vh",
          background: "white",
          borderRadius: 6,
          boxShadow: "0 4px 16px rgba(0,0,0,0.2)",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "1.5rem",
            borderBottom: "1px solid var(--rule)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <h2 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>
            Prompt Preview
          </h2>
          <button
            className="btn small"
            onClick={onClose}
            style={{ padding: "4px 8px" }}
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        {/* Body — scrollable preview */}
        <div style={{ flex: 1, overflowY: "auto", padding: "1.5rem" }}>
          {/* Exercise type banner */}
          <div
            style={{
              padding: "1rem",
              background: "var(--paper-dim, #f5f6f7)",
              borderRadius: 4,
              marginBottom: "1.5rem",
            }}
          >
            <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 4 }}>Exercise type</div>
            <div style={{ fontSize: 14, fontWeight: 500 }}>
              {exerciseLabel}
            </div>
          </div>

          {/* Main prompt */}
          <div style={{ marginBottom: "1.5rem" }}>
            <h3 style={{ fontSize: 12, fontWeight: 600, opacity: 0.7, marginBottom: 8 }}>
              Task
            </h3>
            <p
              style={{
                fontSize: 14,
                lineHeight: 1.6,
                margin: 0,
                padding: "1rem",
                background: "var(--paper-dim, #f5f6f7)",
                borderLeft: "3px solid var(--ink)",
                borderRadius: 2,
              }}
            >
              {prompt.prompt_text}
            </p>
          </div>

          {/* Source text (if any) */}
          {prompt.source_text && (
            <div style={{ marginBottom: "1.5rem" }}>
              <h3 style={{ fontSize: 12, fontWeight: 600, opacity: 0.7, marginBottom: 8 }}>
                Reference text
              </h3>
              <p
                style={{
                  fontSize: 13,
                  lineHeight: 1.6,
                  margin: 0,
                  padding: "1rem",
                  background: "var(--paper-dim, #f5f6f7)",
                  borderLeft: "3px solid var(--ink-mute)",
                  borderRadius: 2,
                }}
              >
                {prompt.source_text}
              </p>
            </div>
          )}

          {/* Constraints */}
          <div style={{ marginBottom: "1.5rem" }}>
            <h3 style={{ fontSize: 12, fontWeight: 600, opacity: 0.7, marginBottom: 8 }}>
              Constraints
            </h3>
            <ul style={{ margin: 0, paddingLeft: 20, fontSize: 13 }}>
              <li style={{ marginBottom: 4 }}>
                Difficulty level: {prompt.difficulty_level}/10
              </li>
              {prompt.min_words || prompt.max_words ? (
                <li style={{ marginBottom: 4 }}>
                  Word limit:{" "}
                  {prompt.min_words && prompt.max_words
                    ? `${prompt.min_words}–${prompt.max_words}`
                    : prompt.max_words
                    ? `max ${prompt.max_words}`
                    : `min ${prompt.min_words}`}
                </li>
              ) : null}
              {prompt.required_sentence_count && (
                <li style={{ marginBottom: 4 }}>
                  Required sentence count: {prompt.required_sentence_count}
                </li>
              )}
              {prompt.max_rewrite_attempts && (
                <li style={{ marginBottom: 4 }}>
                  Maximum rewrites: {prompt.max_rewrite_attempts}
                </li>
              )}
            </ul>
          </div>

          {/* Required words */}
          {prompt.required_words && prompt.required_words.length > 0 && (
            <div style={{ marginBottom: "1.5rem" }}>
              <h3 style={{ fontSize: 12, fontWeight: 600, opacity: 0.7, marginBottom: 8 }}>
                Required words
              </h3>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {prompt.required_words.map((w, i) => (
                  <span
                    key={i}
                    className="badge info"
                    style={{ fontSize: 12, padding: "4px 8px" }}
                  >
                    {w}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Review status */}
          <div style={{ marginBottom: "1.5rem" }}>
            <h3 style={{ fontSize: 12, fontWeight: 600, opacity: 0.7, marginBottom: 8 }}>
              Review status
            </h3>
            <div
              style={{
                display: "flex",
                gap: 8,
                alignItems: "center",
              }}
            >
              <span
                className={`badge ${
                  prompt.reviewer_status === "verified"
                    ? "info"
                    : prompt.reviewer_status === "pending"
                    ? "pending"
                    : prompt.reviewer_status === "rejected"
                    ? "blocker"
                    : "warn"
                }`}
              >
                {prompt.reviewer_status}
              </span>
              <span
                className={`badge ${prompt.is_active ? "info" : "neutral"}`}
                style={{ fontSize: 11 }}
              >
                {prompt.is_active ? "active" : "inactive"}
              </span>
            </div>
            {prompt.reviewer_status === "needs_correction" && prompt.reviewer_notes && (
              <div style={{ fontSize: 12, marginTop: 8, padding: "0.5rem", background: "var(--warn-light, #fff8e1)", borderRadius: 2 }}>
                <strong>Reviewer notes:</strong> {prompt.reviewer_notes}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div
          style={{
            padding: "1rem",
            borderTop: "1px solid var(--rule)",
            textAlign: "right",
          }}
        >
          <button className="btn primary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
