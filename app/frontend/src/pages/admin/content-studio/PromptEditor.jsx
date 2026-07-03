/**
 * Create/edit drawer for a subject-scoped writing prompt.
 *
 * Contract obligations (handoff doc):
 * - body is {reason, payload} (create) / {reason, expected_updated_at, payload} (edit)
 * - expected_updated_at is the updated_at the browser READ — a 409 means someone
 *   else changed the prompt; re-open from a fresh read
 * - required_words: one token per entry, unique case-insensitively (server NFC-trims)
 * - metadata.external_key is system-owned; exam ids must never appear anywhere
 * - verified prompts are locked (the Library hides Edit; the server 422s anyway)
 */
import React, { useState } from "react";
import useApiAction from "../../../lib/hooks/useApiAction";
import { getApiErrorMessage } from "../../../lib/api";
import { contentStudioApi, EXERCISE_TYPES, isValidReason } from "./contentStudioApi";

const EMPTY = {
  subject_id: "",
  topic_id: "",
  microtopic_id: "",
  exercise_type: "sentence_construction",
  prompt_text: "",
  source_text: "",
  required_words: "",
  required_sentence_count: "",
  difficulty_level: 3,
  min_words: "",
  max_words: "",
  max_rewrite_attempts: "",
  rubric_id: "",
  source_document_id: "",
};

function toForm(prompt) {
  if (!prompt) return { ...EMPTY };
  return {
    subject_id: prompt.subject_id || "",
    topic_id: prompt.topic_id || "",
    microtopic_id: prompt.microtopic_id || "",
    exercise_type: prompt.exercise_type || "sentence_construction",
    prompt_text: prompt.prompt_text || "",
    source_text: prompt.source_text || "",
    required_words: Array.isArray(prompt.required_words) ? prompt.required_words.join(", ") : "",
    required_sentence_count: prompt.required_sentence_count ?? "",
    difficulty_level: prompt.difficulty_level ?? 3,
    min_words: prompt.min_words ?? "",
    max_words: prompt.max_words ?? "",
    max_rewrite_attempts: prompt.max_rewrite_attempts ?? "",
    rubric_id: prompt.rubric_id || "",
    source_document_id: prompt.source_document_id || "",
  };
}

export function parseRequiredWords(text) {
  const words = (text || "")
    .split(",")
    .map((w) => w.trim())
    .filter(Boolean);
  const seen = new Set();
  const out = [];
  for (const w of words) {
    if (/\s/.test(w)) return { error: `"${w}" must be a single word (no spaces).` };
    const key = w.toLowerCase();
    if (seen.has(key)) return { error: `"${w}" appears more than once (case-insensitive).` };
    seen.add(key);
    out.push(w);
  }
  return { words: out };
}

export function buildPayload(form, { isCreate }) {
  const errors = [];
  const payload = {};

  if (isCreate) {
    if (!form.subject_id.trim()) errors.push("subject_id is required.");
    payload.subject_id = form.subject_id.trim();
  }
  if (!form.topic_id.trim() && isCreate) errors.push("topic_id is required.");
  if (form.topic_id.trim()) payload.topic_id = form.topic_id.trim();
  if (form.microtopic_id.trim()) payload.microtopic_id = form.microtopic_id.trim();

  payload.exercise_type = form.exercise_type;

  if (!form.prompt_text.trim()) errors.push("Prompt text must be non-blank.");
  payload.prompt_text = form.prompt_text;

  if (form.source_text.trim()) payload.source_text = form.source_text;

  const rw = parseRequiredWords(form.required_words);
  if (rw.error) errors.push(rw.error);
  else if (rw.words.length > 0) payload.required_words = rw.words;

  const d = Number(form.difficulty_level);
  if (!Number.isInteger(d) || d < 1 || d > 10) errors.push("Difficulty must be an integer 1–10.");
  payload.difficulty_level = d;

  const intField = (name, label, { min = 1 } = {}) => {
    const raw = form[name];
    if (raw === "" || raw === null || raw === undefined) return undefined;
    const n = Number(raw);
    if (!Number.isInteger(n) || n < min) {
      errors.push(`${label} must be an integer ≥ ${min}.`);
      return undefined;
    }
    return n;
  };
  const minWords = intField("min_words", "Min words", { min: 0 });
  const maxWords = intField("max_words", "Max words", { min: 0 });
  if (minWords !== undefined) payload.min_words = minWords;
  if (maxWords !== undefined) payload.max_words = maxWords;
  if (minWords !== undefined && maxWords !== undefined && maxWords < minWords) {
    errors.push("Max words must be ≥ min words.");
  }
  const rsc = intField("required_sentence_count", "Required sentence count");
  if (rsc !== undefined) payload.required_sentence_count = rsc;
  const mra = intField("max_rewrite_attempts", "Max rewrite attempts");
  if (mra !== undefined) payload.max_rewrite_attempts = mra;

  if (form.rubric_id.trim()) payload.rubric_id = form.rubric_id.trim();
  if (form.source_document_id.trim()) payload.source_document_id = form.source_document_id.trim();

  return { payload, errors };
}

export default function PromptEditor({ prompt, onClose, onSaved }) {
  const isCreate = !prompt;
  const [form, setForm] = useState(() => toForm(prompt));
  const [reason, setReason] = useState("");
  const [errors, setErrors] = useState([]);
  const [conflict, setConflict] = useState(false);
  const { run, busy } = useApiAction();

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const save = async () => {
    const { payload, errors: validationErrors } = buildPayload(form, { isCreate });
    const all = [...validationErrors];
    if (!isValidReason(reason)) all.push("Reason must be 8–500 characters (audit requirement).");
    setErrors(all);
    setConflict(false);
    if (all.length > 0) return;

    await run({
      action: () =>
        isCreate
          ? contentStudioApi.createPrompt({ reason: reason.trim(), payload })
          : contentStudioApi.updatePrompt(prompt.id, {
              reason: reason.trim(),
              expected_updated_at: prompt.updated_at,
              payload,
            }),
      successMessage: isCreate ? "Prompt created (pending review)." : "Prompt updated.",
      errorMessage: " ", // rendered inline below instead of a generic toast
      onSuccess: onSaved,
      rollback: () => {},
    }).then((res) => {
      if (!res.ok && res.error) {
        if (res.error.status === 409) setConflict(true);
        else setErrors([getApiErrorMessage(res.error)]);
      }
    });
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={isCreate ? "Create writing prompt" : "Edit writing prompt"}
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", zIndex: 100, display: "flex", justifyContent: "flex-end" }}
      onClick={onClose}
      data-testid="prompt-editor"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{ width: "min(560px, 95vw)", height: "100%", overflowY: "auto", background: "var(--paper, #fff)", padding: "1.25rem", boxShadow: "-4px 0 16px rgba(0,0,0,0.2)" }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>
            {isCreate ? "New writing prompt" : "Edit writing prompt"}
          </h2>
          <button type="button" className="btn small" onClick={onClose} aria-label="Close editor">✕</button>
        </div>

        <p style={{ fontSize: 12, opacity: 0.7, marginBottom: 12 }}>
          Prompts are subject-scoped canonical content — no exam fields here. New
          prompts land <strong>pending</strong> and inactive; exam applicability is
          managed under Exam Assignments.
        </p>

        {conflict ? (
          <div className="badge blocker" style={{ display: "block", padding: "0.6rem", marginBottom: 12, fontSize: 12 }} role="alert">
            This prompt changed while you were editing (409). Close and re-open it to
            load the latest revision, then re-apply your edit.
          </div>
        ) : null}
        {errors.length > 0 ? (
          <ul style={{ color: "var(--err, #c00)", fontSize: 12, marginBottom: 12, paddingLeft: 18 }} role="alert">
            {errors.filter((e) => e.trim()).map((e) => <li key={e}>{e}</li>)}
          </ul>
        ) : null}

        <div style={{ display: "grid", gap: 10 }}>
          {isCreate ? (
            <label style={{ fontSize: 12 }}>
              Subject ID (required)
              <input className="input" value={form.subject_id} onChange={set("subject_id")} placeholder="UUID of the English subject" data-testid="prompt-form-subject" />
            </label>
          ) : null}
          <label style={{ fontSize: 12 }}>
            Topic ID {isCreate ? "(required)" : ""}
            <input className="input" value={form.topic_id} onChange={set("topic_id")} placeholder="UUID" data-testid="prompt-form-topic" />
          </label>
          <label style={{ fontSize: 12 }}>
            Microtopic ID (optional)
            <input className="input" value={form.microtopic_id} onChange={set("microtopic_id")} placeholder="UUID (level=microtopic)" />
          </label>
          <label style={{ fontSize: 12 }}>
            Exercise type
            <select className="input" value={form.exercise_type} onChange={set("exercise_type")} data-testid="prompt-form-exercise-type">
              {EXERCISE_TYPES.map((t) => <option key={t} value={t}>{t.replaceAll("_", " ")}</option>)}
            </select>
          </label>
          <label style={{ fontSize: 12 }}>
            Prompt text (required)
            <textarea className="input" rows={4} value={form.prompt_text} onChange={set("prompt_text")} data-testid="prompt-form-text" />
          </label>
          <label style={{ fontSize: 12 }}>
            Source text (optional)
            <textarea className="input" rows={3} value={form.source_text} onChange={set("source_text")} />
          </label>
          <label style={{ fontSize: 12 }}>
            Required words (comma-separated; one word each, no duplicates)
            <input className="input" value={form.required_words} onChange={set("required_words")} placeholder="engage, resilient" data-testid="prompt-form-required-words" />
          </label>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 10 }}>
            <label style={{ fontSize: 12 }}>
              Difficulty (1–10)
              <input className="input" type="number" min={1} max={10} value={form.difficulty_level} onChange={set("difficulty_level")} data-testid="prompt-form-difficulty" />
            </label>
            <label style={{ fontSize: 12 }}>
              Required sentence count
              <input className="input" type="number" min={1} value={form.required_sentence_count} onChange={set("required_sentence_count")} />
            </label>
            <label style={{ fontSize: 12 }}>
              Min words
              <input className="input" type="number" min={0} value={form.min_words} onChange={set("min_words")} data-testid="prompt-form-min-words" />
            </label>
            <label style={{ fontSize: 12 }}>
              Max words
              <input className="input" type="number" min={0} value={form.max_words} onChange={set("max_words")} data-testid="prompt-form-max-words" />
            </label>
            <label style={{ fontSize: 12 }}>
              Max rewrite attempts
              <input className="input" type="number" min={1} value={form.max_rewrite_attempts} onChange={set("max_rewrite_attempts")} />
            </label>
          </div>
          <label style={{ fontSize: 12 }}>
            Rubric ID (optional)
            <input className="input" value={form.rubric_id} onChange={set("rubric_id")} placeholder="UUID" />
          </label>
          <label style={{ fontSize: 12 }}>
            Source document ID (optional)
            <input className="input" value={form.source_document_id} onChange={set("source_document_id")} placeholder="UUID (admin_exam_intelligence document)" />
          </label>
          <label style={{ fontSize: 12 }}>
            Reason (required, 8–500 chars — recorded in the audit log)
            <input className="input" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Why this change is being made" data-testid="prompt-form-reason" />
          </label>
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 16 }}>
          <button type="button" className="btn" onClick={onClose} disabled={busy}>Cancel</button>
          <button type="button" className="btn primary" onClick={save} disabled={busy} data-testid="prompt-form-save">
            {busy ? "Saving…" : isCreate ? "Create prompt" : "Save changes"}
          </button>
        </div>
      </div>
    </div>
  );
}
