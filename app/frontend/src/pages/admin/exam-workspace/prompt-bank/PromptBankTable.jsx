/**
 * Table of prompts with inline actions.
 *
 * Columns: Prompt, Exercise type, Topic, Difficulty, Word limit, Reviewer status, Active status, Updated
 * Actions: Preview, Edit, Clone, Review, Activate/Deactivate
 */
import React, { useState } from "react";

const REVIEWER_BADGE = {
  pending: { cls: "badge pending", text: "pending" },
  verified: { cls: "badge info", text: "verified" },
  rejected: { cls: "badge blocker", text: "rejected" },
  needs_correction: { cls: "badge warn", text: "needs fix" },
};

const EXERCISE_TYPE_LABELS = {
  sentence_construction: "Sentence construction",
  sentence_correction: "Sentence correction",
  vocabulary_in_context: "Vocabulary context",
  sentence_rewrite: "Rewrite",
  sentence_reconstruction: "Reconstruction",
  paragraph_writing: "Paragraph",
  summary_writing: "Summary",
  precis_practice: "Précis",
  essay_practice: "Essay",
  letter_practice: "Letter",
};

function TrustBadge({ status }) {
  const b = REVIEWER_BADGE[status] || REVIEWER_BADGE.pending;
  return <span className={b.cls}>{b.text}</span>;
}

function PromptActions({
  prompt,
  onPreview,
  onEdit,
  onClone,
  onReview,
  onActivate,
  hasCmsPermission,
  hasReviewPermission,
}) {
  const [open, setOpen] = useState(false);

  const canActivate = hasReviewPermission && prompt.reviewer_status === "verified";
  const canReview = hasReviewPermission;
  const canEdit = hasCmsPermission;

  if (!canActivate && !canReview && !canEdit) {
    return <span style={{ fontSize: 12, opacity: 0.6 }}>—</span>;
  }

  return (
    <div style={{ position: "relative" }}>
      <button
        className="btn small"
        onClick={() => setOpen(!open)}
        style={{ minWidth: 0, padding: "4px 8px" }}
        data-testid={`prompt-actions-${prompt.id}`}
      >
        ⋯
      </button>
      {open && (
        <div
          className="popover"
          style={{
            position: "absolute",
            right: 0,
            top: "100%",
            zIndex: 50,
            minWidth: 150,
            background: "white",
            border: "1px solid var(--rule)",
            borderRadius: 4,
            boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
            marginTop: 4,
          }}
          onMouseLeave={() => setOpen(false)}
        >
          <div style={{ display: "flex", flexDirection: "column" }}>
            <button
              className="link-button"
              onClick={() => {
                onPreview(prompt);
                setOpen(false);
              }}
              style={{ padding: "8px 12px", textAlign: "left", fontSize: 13 }}
            >
              👁 Preview
            </button>

            {canEdit && (
              <>
                <button
                  className="link-button"
                  onClick={() => {
                    onEdit(prompt);
                    setOpen(false);
                  }}
                  style={{ padding: "8px 12px", textAlign: "left", fontSize: 13 }}
                >
                  ✎ Edit
                </button>
                <button
                  className="link-button"
                  onClick={() => {
                    onClone(prompt.id);
                    setOpen(false);
                  }}
                  style={{ padding: "8px 12px", textAlign: "left", fontSize: 13 }}
                >
                  ⊕ Clone
                </button>
              </>
            )}

            {canReview && (
              <button
                className="link-button"
                onClick={() => {
                  onReview(prompt);
                  setOpen(false);
                }}
                style={{ padding: "8px 12px", textAlign: "left", fontSize: 13 }}
              >
                🔍 Review
              </button>
            )}

            {canActivate && (
              <button
                className="link-button"
                onClick={() => {
                  onActivate(prompt.id, !prompt.is_active);
                  setOpen(false);
                }}
                style={{ padding: "8px 12px", textAlign: "left", fontSize: 13 }}
              >
                {prompt.is_active ? "🚫" : "✓"} {prompt.is_active ? "Deactivate" : "Activate"}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function PromptBankTable({
  prompts = [],
  onEdit = () => {},
  onPreview = () => {},
  onReview = () => {},
  onActivate = () => {},
  onClone = () => {},
  hasCmsPermission = false,
  hasReviewPermission = false,
}) {
  const handleReviewClick = (prompt) => {
    // Show review modal
    const status = prompt.reviewer_status === "pending" || prompt.reviewer_status === "needs_correction"
      ? "verified"
      : "rejected";
    const notes = prompt.reviewer_status === "pending" ? "" : "Review feedback";
    onReview(prompt.id, status, notes);
  };

  return (
    <div style={{ overflowX: "auto" }}>
      <table className="data-table">
        <thead>
          <tr>
            <th>Prompt</th>
            <th>Exercise type</th>
            <th>Topic</th>
            <th style={{ textAlign: "right" }}>Difficulty</th>
            <th style={{ textAlign: "right" }}>Word limit</th>
            <th>Reviewer status</th>
            <th>Active</th>
            <th>Updated</th>
            <th style={{ width: 50 }}></th>
          </tr>
        </thead>
        <tbody>
          {prompts.map((prompt) => (
            <tr key={prompt.id} data-testid={`prompt-row-${prompt.id}`}>
              <td>
                <span
                  style={{
                    display: "-webkit-box",
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: "vertical",
                    overflow: "hidden",
                    fontSize: 13,
                  }}
                >
                  {prompt.prompt_text || "—"}
                </span>
              </td>
              <td>
                <span style={{ fontSize: 12, opacity: 0.8 }}>
                  {EXERCISE_TYPE_LABELS[prompt.exercise_type] || prompt.exercise_type}
                </span>
              </td>
              <td>
                <span style={{ fontSize: 12, opacity: 0.8 }}>
                  {prompt.topic_name || prompt.microtopic_name || "—"}
                </span>
              </td>
              <td style={{ textAlign: "right" }}>
                <span style={{ fontSize: 12 }}>{prompt.difficulty_level}/10</span>
              </td>
              <td style={{ textAlign: "right" }}>
                <span style={{ fontSize: 12 }}>
                  {prompt.min_words && prompt.max_words
                    ? `${prompt.min_words}–${prompt.max_words}`
                    : prompt.max_words
                    ? `0–${prompt.max_words}`
                    : "—"}
                </span>
              </td>
              <td>
                <TrustBadge status={prompt.reviewer_status} />
              </td>
              <td>
                <span
                  className={`badge ${prompt.is_active ? "info" : "neutral"} no-dot`}
                  style={{ fontSize: 11 }}
                >
                  {prompt.is_active ? "active" : "inactive"}
                </span>
              </td>
              <td>
                <span style={{ fontSize: 11, opacity: 0.7 }}>
                  {prompt.updated_at
                    ? new Date(prompt.updated_at).toLocaleDateString()
                    : "—"}
                </span>
              </td>
              <td>
                <PromptActions
                  prompt={prompt}
                  onPreview={onPreview}
                  onEdit={onEdit}
                  onClone={onClone}
                  onReview={handleReviewClick}
                  onActivate={onActivate}
                  hasCmsPermission={hasCmsPermission}
                  hasReviewPermission={hasReviewPermission}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
