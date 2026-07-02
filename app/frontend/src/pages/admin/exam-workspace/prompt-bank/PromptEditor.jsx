/**
 * Create/edit prompt drawer with form validation.
 *
 * Fields:
 * - exam_id (locked)
 * - exam_cycle_id (optional)
 * - exam_phase_id (optional)
 * - subject_id (English, readonly)
 * - topic_id (required)
 * - microtopic_id (optional)
 * - exercise_type (required)
 * - prompt_text (required)
 * - source_text (optional)
 * - required_words (array, normalized)
 * - required_sentence_count (optional, positive)
 * - difficulty_level (required, 1-10)
 * - min_words (optional, >= 0)
 * - max_words (optional, >= min_words)
 * - max_rewrite_attempts (default 3, positive)
 * - rubric_id (optional)
 * - source_document_id (optional)
 * - metadata (JSON, optional)
 */
import React, { useCallback, useState } from "react";

const EXERCISE_TYPES = [
  "sentence_construction",
  "sentence_correction",
  "vocabulary_in_context",
  "sentence_rewrite",
  "sentence_reconstruction",
  "paragraph_writing",
  "summary_writing",
  "precis_practice",
  "essay_practice",
  "letter_practice",
];

function normalizeRequiredWords(words) {
  if (!words) return [];
  const arr = Array.isArray(words) ? words : String(words).split(/[\s,]+/);
  return [...new Set(arr.map((w) => String(w).toLowerCase().trim()).filter(Boolean))];
}

function validateForm(data) {
  const errors = {};

  if (!data.prompt_text || !String(data.prompt_text).trim()) {
    errors.prompt_text = "Prompt text is required";
  }

  if (!data.exercise_type) {
    errors.exercise_type = "Exercise type is required";
  }

  if (!data.topic_id) {
    errors.topic_id = "Topic is required";
  }

  if (!data.difficulty_level) {
    errors.difficulty_level = "Difficulty is required";
  } else {
    const d = Number(data.difficulty_level);
    if (isNaN(d) || d < 1 || d > 10) {
      errors.difficulty_level = "Difficulty must be 1–10";
    }
  }

  const minWords = data.min_words ? Number(data.min_words) : 0;
  const maxWords = data.max_words ? Number(data.max_words) : null;

  if (minWords < 0) {
    errors.min_words = "Min words must be >= 0";
  }

  if (maxWords !== null && maxWords < minWords) {
    errors.max_words = "Max words must be >= min words";
  }

  if (data.required_sentence_count) {
    const r = Number(data.required_sentence_count);
    if (isNaN(r) || r <= 0) {
      errors.required_sentence_count = "Must be positive";
    }
  }

  if (data.max_rewrite_attempts) {
    const m = Number(data.max_rewrite_attempts);
    if (isNaN(m) || m <= 0) {
      errors.max_rewrite_attempts = "Must be positive";
    }
  }

  if (data.metadata) {
    try {
      JSON.parse(data.metadata);
    } catch {
      errors.metadata = "Invalid JSON";
    }
  }

  return errors;
}

export default function PromptEditor({
  prompt = null,
  examId = null,
  examCycleId = null,
  onSave = () => {},
  onClose = () => {},
}) {
  const isCreate = !prompt;

  const [formData, setFormData] = useState({
    exam_id: examId,
    exam_cycle_id: examCycleId,
    exam_phase_id: "",
    topic_id: prompt?.topic_id || "",
    microtopic_id: prompt?.microtopic_id || "",
    exercise_type: prompt?.exercise_type || "",
    prompt_text: prompt?.prompt_text || "",
    source_text: prompt?.source_text || "",
    required_words: prompt?.required_words ? JSON.stringify(prompt.required_words) : "",
    required_sentence_count: prompt?.required_sentence_count || "",
    difficulty_level: prompt?.difficulty_level || "",
    min_words: prompt?.min_words || "",
    max_words: prompt?.max_words || "",
    max_rewrite_attempts: prompt?.max_rewrite_attempts || 3,
    rubric_id: prompt?.rubric_id || "",
    source_document_id: prompt?.source_document_id || "",
    metadata: prompt?.metadata ? JSON.stringify(prompt.metadata) : "{}",
  });

  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);

  const handleChange = useCallback((key, value) => {
    setFormData((prev) => ({
      ...prev,
      [key]: value,
    }));
    if (errors[key]) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[key];
        return next;
      });
    }
  }, [errors]);

  const handleSave = useCallback(async () => {
    const validationErrors = validateForm(formData);
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    setSaving(true);
    try {
      const payload = {
        exam_id: formData.exam_id,
        exam_cycle_id: formData.exam_cycle_id || null,
        exam_phase_id: formData.exam_phase_id || null,
        topic_id: formData.topic_id,
        microtopic_id: formData.microtopic_id || null,
        exercise_type: formData.exercise_type,
        prompt_text: formData.prompt_text,
        source_text: formData.source_text || null,
        required_words: formData.required_words
          ? normalizeRequiredWords(formData.required_words)
          : null,
        required_sentence_count: formData.required_sentence_count
          ? Number(formData.required_sentence_count)
          : null,
        difficulty_level: Number(formData.difficulty_level),
        min_words: formData.min_words ? Number(formData.min_words) : null,
        max_words: formData.max_words ? Number(formData.max_words) : null,
        max_rewrite_attempts: Number(formData.max_rewrite_attempts),
        rubric_id: formData.rubric_id || null,
        source_document_id: formData.source_document_id || null,
        metadata: formData.metadata ? JSON.parse(formData.metadata) : {},
      };

      await onSave(payload);
    } finally {
      setSaving(false);
    }
  }, [formData, onSave]);

  return (
    <div
      className="drawer-overlay"
      onClick={onClose}
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: "rgba(0,0,0,0.4)",
        zIndex: 100,
        display: "flex",
        justifyContent: "flex-end",
      }}
    >
      <div
        className="drawer"
        onClick={(e) => e.stopPropagation()}
        style={{
          width: "min(500px, 90vw)",
          height: "100vh",
          background: "white",
          display: "flex",
          flexDirection: "column",
          boxShadow: "-2px 0 8px rgba(0,0,0,0.15)",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "1rem",
            borderBottom: "1px solid var(--rule)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <h2 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>
            {isCreate ? "New Prompt" : "Edit Prompt"}
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

        {/* Body — scrollable form */}
        <div style={{ flex: 1, overflowY: "auto", padding: "1rem" }}>
          <div className="form-group">
            <label className="label">Exercise Type *</label>
            <select
              className={`input ${errors.exercise_type ? "error" : ""}`}
              value={formData.exercise_type}
              onChange={(e) => handleChange("exercise_type", e.target.value)}
            >
              <option value="">Select type…</option>
              {EXERCISE_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t.replace(/_/g, " ")}
                </option>
              ))}
            </select>
            {errors.exercise_type && (
              <div style={{ fontSize: 12, color: "var(--err)", marginTop: 4 }}>
                {errors.exercise_type}
              </div>
            )}
          </div>

          <div className="form-group">
            <label className="label">Topic *</label>
            <input
              type="text"
              className={`input ${errors.topic_id ? "error" : ""}`}
              placeholder="Select topic…"
              value={formData.topic_id}
              onChange={(e) => handleChange("topic_id", e.target.value)}
            />
            {errors.topic_id && (
              <div style={{ fontSize: 12, color: "var(--err)", marginTop: 4 }}>
                {errors.topic_id}
              </div>
            )}
          </div>

          <div className="form-group">
            <label className="label">Microtopic</label>
            <input
              type="text"
              className="input"
              placeholder="Optional…"
              value={formData.microtopic_id}
              onChange={(e) => handleChange("microtopic_id", e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="label">Prompt Text *</label>
            <textarea
              className={`input ${errors.prompt_text ? "error" : ""}`}
              rows={4}
              placeholder="Write the prompt…"
              value={formData.prompt_text}
              onChange={(e) => handleChange("prompt_text", e.target.value)}
            />
            {errors.prompt_text && (
              <div style={{ fontSize: 12, color: "var(--err)", marginTop: 4 }}>
                {errors.prompt_text}
              </div>
            )}
          </div>

          <div className="form-group">
            <label className="label">Source Text</label>
            <textarea
              className="input"
              rows={3}
              placeholder="For précis/comprehension…"
              value={formData.source_text}
              onChange={(e) => handleChange("source_text", e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="label">Required Words (comma-separated)</label>
            <textarea
              className="input"
              rows={2}
              placeholder="word1, word2, word3…"
              value={formData.required_words}
              onChange={(e) => handleChange("required_words", e.target.value)}
            />
            <div style={{ fontSize: 11, opacity: 0.6, marginTop: 4 }}>
              Normalized, trimmed, deduplicated case-insensitively.
            </div>
          </div>

          <div className="form-group">
            <label className="label">Required Sentence Count</label>
            <input
              type="number"
              className={`input ${errors.required_sentence_count ? "error" : ""}`}
              min="1"
              placeholder="Optional…"
              value={formData.required_sentence_count}
              onChange={(e) => handleChange("required_sentence_count", e.target.value)}
            />
            {errors.required_sentence_count && (
              <div style={{ fontSize: 12, color: "var(--err)", marginTop: 4 }}>
                {errors.required_sentence_count}
              </div>
            )}
          </div>

          <div className="form-group">
            <label className="label">Difficulty Level * (1–10)</label>
            <input
              type="number"
              className={`input ${errors.difficulty_level ? "error" : ""}`}
              min="1"
              max="10"
              value={formData.difficulty_level}
              onChange={(e) => handleChange("difficulty_level", e.target.value)}
            />
            {errors.difficulty_level && (
              <div style={{ fontSize: 12, color: "var(--err)", marginTop: 4 }}>
                {errors.difficulty_level}
              </div>
            )}
          </div>

          <div className="row" style={{ gap: 12 }}>
            <div className="form-group" style={{ flex: 1 }}>
              <label className="label">Min Words</label>
              <input
                type="number"
                className={`input ${errors.min_words ? "error" : ""}`}
                min="0"
                placeholder="0"
                value={formData.min_words}
                onChange={(e) => handleChange("min_words", e.target.value)}
              />
              {errors.min_words && (
                <div style={{ fontSize: 12, color: "var(--err)", marginTop: 4 }}>
                  {errors.min_words}
                </div>
              )}
            </div>
            <div className="form-group" style={{ flex: 1 }}>
              <label className="label">Max Words</label>
              <input
                type="number"
                className={`input ${errors.max_words ? "error" : ""}`}
                min="0"
                placeholder="No limit"
                value={formData.max_words}
                onChange={(e) => handleChange("max_words", e.target.value)}
              />
              {errors.max_words && (
                <div style={{ fontSize: 12, color: "var(--err)", marginTop: 4 }}>
                  {errors.max_words}
                </div>
              )}
            </div>
          </div>

          <div className="form-group">
            <label className="label">Max Rewrite Attempts (default 3)</label>
            <input
              type="number"
              className={`input ${errors.max_rewrite_attempts ? "error" : ""}`}
              min="1"
              value={formData.max_rewrite_attempts}
              onChange={(e) => handleChange("max_rewrite_attempts", e.target.value)}
            />
            {errors.max_rewrite_attempts && (
              <div style={{ fontSize: 12, color: "var(--err)", marginTop: 4 }}>
                {errors.max_rewrite_attempts}
              </div>
            )}
          </div>

          <div className="form-group">
            <label className="label">Rubric ID</label>
            <input
              type="text"
              className="input"
              placeholder="Optional…"
              value={formData.rubric_id}
              onChange={(e) => handleChange("rubric_id", e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="label">Metadata (JSON)</label>
            <textarea
              className={`input ${errors.metadata ? "error" : ""}`}
              rows={3}
              placeholder="{}"
              value={formData.metadata}
              onChange={(e) => handleChange("metadata", e.target.value)}
            />
            {errors.metadata && (
              <div style={{ fontSize: 12, color: "var(--err)", marginTop: 4 }}>
                {errors.metadata}
              </div>
            )}
          </div>

          {!isCreate && prompt?.reviewer_status === "verified" && (
            <div
              style={{
                padding: "0.75rem",
                background: "var(--warn-light, #fff8e1)",
                border: "1px solid var(--warn, #f80)",
                borderRadius: 4,
                fontSize: 12,
                marginBottom: "1rem",
              }}
            >
              ⚠ This prompt is verified. Material content changes may return it to pending review.
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          style={{
            padding: "1rem",
            borderTop: "1px solid var(--rule)",
            display: "flex",
            gap: 8,
            justifyContent: "flex-end",
          }}
        >
          <button className="btn" onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button
            className="btn primary"
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
