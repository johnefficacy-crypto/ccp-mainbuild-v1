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
 *
 * EDIT builds a DIRTY-FIELD PATCH against the original row: unchanged fields are
 * omitted, changed non-empty fields are sent, and a nullable field the operator
 * cleared is sent as explicit `null` (the backend applies null via
 * jsonb_populate_record; omitting it would leave the stale value in place and
 * still report success). Non-nullable fields (subject_id, topic_id,
 * exercise_type, prompt_text, difficulty_level, max_rewrite_attempts) are never
 * nulled — clearing them in edit is ignored, not sent.
 */
import React, { useEffect, useRef, useState } from "react";
import useApiAction from "../../../lib/hooks/useApiAction";
import { getApiErrorMessage } from "../../../lib/api";
import { contentStudioApi, EXERCISE_TYPES, isValidReason } from "./contentStudioApi";
import { parseRequiredWordsField, validateInt } from "./validation";
import {
  SubjectSelect,
  TopicSelect,
  MicrotopicSelect,
  RubricSelect,
  SourceDocumentSelect,
} from "./selectors";
import CorrectionNote from "./CorrectionNote";

// Optional fields that CAN be cleared to null on edit (not in the backend
// _NOT_NULL guard). required_words clears to null (not []).
const NULLABLE = new Set([
  "microtopic_id",
  "source_text",
  "required_words",
  "required_sentence_count",
  "min_words",
  "max_words",
  "rubric_id",
  "source_document_id",
]);

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

// Normalise the form into typed values + validation errors, independent of
// create/edit. `undefined` = field left blank.
function normaliseForm(form) {
  const errors = [];
  const v = {};

  v.subject_id = form.subject_id.trim() || undefined;
  v.topic_id = form.topic_id.trim() || undefined;
  v.microtopic_id = form.microtopic_id.trim() || undefined;
  v.exercise_type = form.exercise_type;
  v.rubric_id = form.rubric_id.trim() || undefined;
  v.source_document_id = form.source_document_id.trim() || undefined;

  v.prompt_text = form.prompt_text.trim() ? form.prompt_text : undefined;
  v.source_text = form.source_text.trim() ? form.source_text : undefined;

  const rw = parseRequiredWordsField(form.required_words);
  if (rw.error) errors.push(rw.error);
  v.required_words = rw.words && rw.words.length > 0 ? rw.words : undefined;

  const dl = validateInt(form.difficulty_level, "Difficulty", { min: 1, max: 10 });
  if (dl.error) errors.push(dl.error);
  v.difficulty_level = dl.value;

  const rsc = validateInt(form.required_sentence_count, "Required sentence count", { min: 1 });
  if (rsc.error) errors.push(rsc.error);
  v.required_sentence_count = rsc.value;

  const mn = validateInt(form.min_words, "Min words", { min: 0 });
  if (mn.error) errors.push(mn.error);
  v.min_words = mn.value;

  const mx = validateInt(form.max_words, "Max words", { min: 0 });
  if (mx.error) errors.push(mx.error);
  v.max_words = mx.value;

  if (v.min_words !== undefined && v.max_words !== undefined && v.max_words < v.min_words) {
    errors.push("Max words must be ≥ min words.");
  }

  const mra = validateInt(form.max_rewrite_attempts, "Max rewrite attempts", { min: 0 });
  if (mra.error) errors.push(mra.error);
  v.max_rewrite_attempts = mra.value;

  return { values: v, errors };
}

const FIELDS = [
  "topic_id",
  "microtopic_id",
  "exercise_type",
  "prompt_text",
  "source_text",
  "required_words",
  "required_sentence_count",
  "difficulty_level",
  "min_words",
  "max_words",
  "max_rewrite_attempts",
  "rubric_id",
  "source_document_id",
];

function sameValue(a, b) {
  if (Array.isArray(a) || Array.isArray(b)) {
    const aa = Array.isArray(a) ? a : [];
    const bb = Array.isArray(b) ? b : [];
    return aa.length === bb.length && aa.every((x, i) => x === bb[i]);
  }
  return a === b;
}

export function buildPayload(form, { isCreate, original = null }) {
  const { values, errors } = normaliseForm(form);
  const payload = {};

  if (isCreate) {
    if (!values.subject_id) errors.push("subject_id is required.");
    if (!values.topic_id) errors.push("topic_id is required.");
    if (!values.prompt_text) errors.push("Prompt text must be non-blank.");
    if (values.difficulty_level === undefined) errors.push("Difficulty is required (1–10).");

    payload.subject_id = values.subject_id;
    payload.topic_id = values.topic_id;
    payload.exercise_type = values.exercise_type;
    payload.prompt_text = values.prompt_text;
    payload.difficulty_level = values.difficulty_level;
    // optional — only when provided
    FIELDS.forEach((f) => {
      if (["topic_id", "exercise_type", "prompt_text", "difficulty_level"].includes(f)) return;
      if (values[f] !== undefined) payload[f] = values[f];
    });
    return { payload, errors };
  }

  // EDIT: dirty diff against the original row.
  const orig = original || {};
  FIELDS.forEach((f) => {
    const nextVal = values[f]; // undefined = blank
    const origVal = f === "required_words"
      ? (Array.isArray(orig.required_words) ? orig.required_words : undefined)
      : (orig[f] === null || orig[f] === undefined || orig[f] === "" ? undefined : orig[f]);

    if (nextVal === undefined) {
      // Field cleared. Only send explicit null if it was set AND is nullable.
      if (origVal !== undefined && NULLABLE.has(f)) payload[f] = null;
      return;
    }
    if (!sameValue(nextVal, origVal)) payload[f] = nextVal;
  });

  return { payload, errors };
}

export default function PromptEditor({ prompt, onClose, onSaved }) {
  const isCreate = !prompt;
  const [form, setForm] = useState(() => toForm(prompt));
  const [reason, setReason] = useState("");
  const [errors, setErrors] = useState([]);
  const [conflict, setConflict] = useState(false);
  const { run, busy } = useApiAction();
  const dialogRef = useRef(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;

  // A11y: Escape closes; focus moves into the dialog on open and restores on close.
  useEffect(() => {
    const prevFocus = typeof document !== "undefined" ? document.activeElement : null;
    const node = dialogRef.current;
    const first = node && node.querySelector("input, textarea, select, button");
    if (first) first.focus();
    const onKey = (e) => { if (e.key === "Escape") closeRef.current(); };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      if (prevFocus && typeof prevFocus.focus === "function") prevFocus.focus();
    };
  }, []);

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  // Dependent-selector setter: changing a parent invalidates its children so the
  // form can never carry a topic that does not belong to the chosen subject (or a
  // microtopic outside the chosen topic).
  const setDependent = (key) => (value) =>
    setForm((f) => {
      const next = { ...f, [key]: value };
      if (key === "subject_id") { next.topic_id = ""; next.microtopic_id = ""; }
      if (key === "topic_id") { next.microtopic_id = ""; }
      return next;
    });

  // In edit mode the subject is fixed (not shown); topics still filter to it.
  const activeSubjectId = isCreate ? form.subject_id : (prompt && prompt.subject_id) || "";

  const save = async () => {
    const { payload, errors: validationErrors } = buildPayload(form, { isCreate, original: prompt });
    const all = [...validationErrors];
    if (!isValidReason(reason)) all.push("Reason must be 8–500 characters (audit requirement).");
    if (!isCreate && Object.keys(payload).length === 0) {
      all.push("No changes to save — edit a field first.");
    }
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
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", zIndex: 100, display: "flex", justifyContent: "flex-end" }}
      onClick={onClose}
      data-testid="prompt-editor-overlay"
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={isCreate ? "Create writing prompt" : "Edit writing prompt"}
        onClick={(e) => e.stopPropagation()}
        style={{ width: "min(560px, 95vw)", height: "100%", overflowY: "auto", background: "var(--paper, #fff)", padding: "1.25rem", boxShadow: "-4px 0 16px rgba(0,0,0,0.2)" }}
        data-testid="prompt-editor"
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

        {!isCreate && prompt && prompt.reviewer_status === "needs_correction" ? (
          <CorrectionNote promptId={prompt.id} />
        ) : null}

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
              Subject (required)
              <SubjectSelect value={form.subject_id} onChange={setDependent("subject_id")} testId="prompt-form-subject" />
            </label>
          ) : null}
          <label style={{ fontSize: 12 }}>
            Topic {isCreate ? "(required)" : ""}
            <TopicSelect subjectId={activeSubjectId} value={form.topic_id} onChange={setDependent("topic_id")} testId="prompt-form-topic" />
          </label>
          <label style={{ fontSize: 12 }}>
            Microtopic (optional)
            <MicrotopicSelect topicId={form.topic_id} value={form.microtopic_id} onChange={setDependent("microtopic_id")} testId="prompt-form-microtopic" />
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
            <textarea className="input" rows={3} value={form.source_text} onChange={set("source_text")} data-testid="prompt-form-source-text" />
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
              <input className="input" type="number" min={1} value={form.required_sentence_count} onChange={set("required_sentence_count")} data-testid="prompt-form-sentence-count" />
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
              <input className="input" type="number" min={0} value={form.max_rewrite_attempts} onChange={set("max_rewrite_attempts")} data-testid="prompt-form-rewrite" />
            </label>
          </div>
          <label style={{ fontSize: 12 }}>
            Rubric (optional)
            <RubricSelect value={form.rubric_id} onChange={setDependent("rubric_id")} testId="prompt-form-rubric" />
          </label>
          <label style={{ fontSize: 12 }}>
            Source document (optional)
            <SourceDocumentSelect value={form.source_document_id} onChange={setDependent("source_document_id")} testId="prompt-form-source-document" />
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
