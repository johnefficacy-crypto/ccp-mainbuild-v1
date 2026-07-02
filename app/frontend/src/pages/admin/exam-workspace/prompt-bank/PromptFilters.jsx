/**
 * Filter bar for prompt search and filtering.
 */
import React from "react";

const EXERCISE_TYPES = [
  { value: "sentence_construction", label: "Sentence construction" },
  { value: "sentence_correction", label: "Sentence correction" },
  { value: "vocabulary_in_context", label: "Vocabulary context" },
  { value: "sentence_rewrite", label: "Sentence rewrite" },
  { value: "sentence_reconstruction", label: "Sentence reconstruction" },
  { value: "paragraph_writing", label: "Paragraph writing" },
  { value: "summary_writing", label: "Summary writing" },
  { value: "precis_practice", label: "Précis practice" },
  { value: "essay_practice", label: "Essay practice" },
  { value: "letter_practice", label: "Letter practice" },
];

const REVIEWER_STATUS = [
  { value: "pending", label: "Pending" },
  { value: "verified", label: "Verified" },
  { value: "rejected", label: "Rejected" },
  { value: "needs_correction", label: "Needs correction" },
];

const ACTIVE_STATUS = [
  { value: "true", label: "Active" },
  { value: "false", label: "Inactive" },
];

const DIFFICULTY_LEVELS = Array.from({ length: 10 }, (_, i) => ({
  value: String(i + 1),
  label: `Level ${i + 1}`,
}));

export default function PromptFilters({ filters = {}, onChange = () => {} }) {
  const handleChange = (key, value) => {
    onChange({ [key]: value });
  };

  const handleSearch = (e) => {
    onChange({ q: e.target.value });
  };

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
        gap: 12,
        marginBottom: "1.5rem",
        padding: "1rem",
        background: "var(--paper-dim, #fafbfb)",
        borderRadius: 4,
      }}
    >
      <div>
        <label className="label" style={{ fontSize: 12 }}>
          Search
        </label>
        <input
          type="text"
          className="input"
          placeholder="Text, word, topic…"
          value={filters.q || ""}
          onChange={handleSearch}
        />
      </div>

      <div>
        <label className="label" style={{ fontSize: 12 }}>
          Exercise Type
        </label>
        <select
          className="input"
          value={filters.exercise_type || ""}
          onChange={(e) => handleChange("exercise_type", e.target.value)}
        >
          <option value="">All types</option>
          {EXERCISE_TYPES.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="label" style={{ fontSize: 12 }}>
          Reviewer Status
        </label>
        <select
          className="input"
          value={filters.reviewer_status || ""}
          onChange={(e) => handleChange("reviewer_status", e.target.value)}
        >
          <option value="">All statuses</option>
          {REVIEWER_STATUS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="label" style={{ fontSize: 12 }}>
          Active Status
        </label>
        <select
          className="input"
          value={filters.is_active || ""}
          onChange={(e) => handleChange("is_active", e.target.value === "true" ? true : e.target.value === "false" ? false : "")}
        >
          <option value="">All</option>
          {ACTIVE_STATUS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="label" style={{ fontSize: 12 }}>
          Difficulty
        </label>
        <select
          className="input"
          value={filters.difficulty_level || ""}
          onChange={(e) => handleChange("difficulty_level", e.target.value)}
        >
          <option value="">All difficulties</option>
          {DIFFICULTY_LEVELS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
