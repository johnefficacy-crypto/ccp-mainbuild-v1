import { useEffect, useRef, useState } from "react";
import SourceContext from "./SourceContext";
import { wordCount as countWords } from "./requiredWords";
import {
  clearDraft,
  clearOutline,
  loadDraft,
  loadOutline,
  saveDraft,
  saveOutline,
} from "./autosave";

/**
 * Paragraph exercise types (mirrors the backend `_PARAGRAPH_EXERCISES` set in
 * `study_os/writing_practice/evidence_deriver.py`). The shell dispatches to the
 * Paragraph Builder for these; every other type stays on the Sentence Builder.
 */
export const PARAGRAPH_EXERCISE_TYPES = new Set([
  "paragraph_writing",
  "summary_writing",
  "precis_practice",
  "essay_practice",
  "letter_practice",
]);

/**
 * @param {string} [exerciseType]
 * @returns {boolean} true when the exercise is a paragraph-level drill.
 */
export function isParagraphExercise(exerciseType) {
  return PARAGRAPH_EXERCISE_TYPES.has(String(exerciseType || ""));
}

/**
 * ParagraphBuilder — EWP-6 Paragraph Builder compose surface (SCAFFOLD).
 *
 * This realises the §13.2 shell hierarchy slot for paragraph/summary/précis/
 * essay/letter drills. It mirrors the Sentence Builder's compose contract (word
 * count via the backend-parity tokeniser, autosaved draft, single `onSubmit`
 * that returns `{ ok }`) and adds an **outline scratchpad** — the ordered list
 * of points the writer plans before drafting, the `outline_json` shape from the
 * EWP-6 design.
 *
 * INERT BY DESIGN: no paragraph prompt is verified/active/launchable — the
 * paragraph release gate (`cms_writing_gate_open('paragraph')`, migration 226)
 * is CLOSED and no paragraph prompt is activated, so a real session never routes
 * here. This component is exercised by tests only until §16 opens the gate. It
 * introduces no API, no route, and no schema write: the outline is a client
 * scratchpad (sessionStorage), never sent to the backend in this scaffold.
 *
 * @param {Object} props
 * @param {number} props.unitNumber - Paragraph unit index (for labels/keys).
 * @param {string} [props.promptText] - Optional prompt shown above the editor.
 * @param {string} [props.sourceText] - Immutable source/task context (read-only).
 * @param {string} [props.exerciseType] - Drives the source-context label.
 * @param {number} [props.minWords] - Optional minimum word count.
 * @param {number} [props.maxWords] - Optional maximum word count.
 * @param {string} [props.initialValue] - Initial draft value.
 * @param {string} [props.sessionId] - Session id for autosave keys (enables autosave).
 * @param {(text: string) => Promise<{ ok: boolean }>} props.onSubmit - Submits the body.
 * @param {boolean} [props.busy] - Disables submit while a request is in flight.
 * @param {string} [props.submitLabel] - Label for the submit button.
 * @returns {JSX.Element}
 */
export default function ParagraphBuilder({
  unitNumber,
  promptText,
  sourceText,
  exerciseType,
  minWords,
  maxWords,
  initialValue = "",
  sessionId,
  onSubmit,
  busy = false,
  submitLabel = "Submit",
}) {
  // Restore an autosaved draft (reload safety) when nothing was passed in.
  const [draft, setDraft] = useState(() => {
    if (initialValue) return initialValue;
    if (sessionId != null) {
      const saved = loadDraft(sessionId, unitNumber);
      if (saved != null) return saved;
    }
    return "";
  });

  // Outline scratchpad — restore any autosaved plan, else start with one empty
  // point. Monotonic ids (a ref counter, never Date/random) keep list keys
  // stable and test-deterministic.
  const idRef = useRef(0);
  const nextId = () => (idRef.current += 1);
  const [outline, setOutline] = useState(() => {
    if (sessionId != null) {
      const saved = loadOutline(sessionId, unitNumber);
      if (Array.isArray(saved) && saved.length > 0) {
        // Reseed the id counter above any restored id so new points stay unique.
        idRef.current = saved.reduce((m, p) => Math.max(m, Number(p?.id) || 0), 0);
        return saved.map((p) => ({ id: Number(p?.id) || nextId(), text: String(p?.text ?? "") }));
      }
    }
    return [{ id: nextId(), text: "" }];
  });

  // Persist the draft as it changes so an accidental reload never loses work.
  useEffect(() => {
    if (sessionId == null) return;
    saveDraft(sessionId, unitNumber, draft);
  }, [sessionId, unitNumber, draft]);

  // Persist the outline plan alongside the draft.
  useEffect(() => {
    if (sessionId == null) return;
    saveOutline(sessionId, unitNumber, outline);
  }, [sessionId, unitNumber, outline]);

  const setPointText = (id, text) =>
    setOutline((prev) => prev.map((p) => (p.id === id ? { ...p, text } : p)));
  const addPoint = () => setOutline((prev) => [...prev, { id: nextId(), text: "" }]);
  const removePoint = (id) =>
    setOutline((prev) => (prev.length <= 1 ? prev : prev.filter((p) => p.id !== id)));

  // Count words with the backend-parity tokeniser so the displayed count never
  // diverges from the server's deterministic word_count (§16 gate #3).
  const wordCount = countWords(draft);
  const belowMin = typeof minWords === "number" && wordCount < minWords;
  const aboveMax = typeof maxWords === "number" && wordCount > maxWords;
  const outOfRange = belowMin || aboveMax;
  const hasHint = typeof minWords === "number" || typeof maxWords === "number";

  const isEmpty = draft.trim().length === 0;
  const disabled = busy || isEmpty;

  const handleSubmit = async () => {
    // Clear the autosaved draft + outline ONLY after a successful submit — a
    // failed / stale-CAS / network-errored submit keeps both so a reload can
    // still recover the work.
    const result = await onSubmit(draft.trim());
    if (sessionId != null && result?.ok) {
      clearDraft(sessionId, unitNumber);
      clearOutline(sessionId, unitNumber);
    }
  };

  return (
    <div
      data-testid="paragraph-builder"
      className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
    >
      <SourceContext sourceText={sourceText} exerciseType={exerciseType} />
      {promptText ? (
        <p className="mb-2 text-sm font-medium text-slate-700">{promptText}</p>
      ) : null}

      {/* Outline scratchpad (outline_json). Planning aid only — not submitted. */}
      <fieldset
        data-testid="paragraph-outline"
        className="mb-3 rounded-lg border border-slate-200 bg-slate-50 p-3"
      >
        <legend className="px-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Outline (scratchpad)
        </legend>
        <ul className="space-y-2">
          {outline.map((point, i) => (
            <li key={point.id} className="flex items-center gap-2">
              <span aria-hidden="true" className="text-xs text-slate-400">
                {i + 1}.
              </span>
              <input
                type="text"
                data-testid={`paragraph-outline-point-${i}`}
                aria-label={`Outline point ${i + 1}`}
                className="flex-1 rounded-lg border border-slate-300 p-1.5 text-sm text-slate-800 focus:border-emerald-400 focus:outline-none focus:ring-1 focus:ring-emerald-400"
                value={point.text}
                onChange={(e) => setPointText(point.id, e.target.value)}
              />
              <button
                type="button"
                data-testid={`paragraph-outline-remove-${i}`}
                aria-label={`Remove outline point ${i + 1}`}
                onClick={() => removePoint(point.id)}
                disabled={outline.length <= 1}
                className="rounded-lg border border-slate-300 px-2 py-1 text-xs text-slate-600 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
        <button
          type="button"
          data-testid="paragraph-outline-add"
          onClick={addPoint}
          className="mt-2 rounded-lg border border-slate-300 px-2.5 py-1 text-xs font-medium text-emerald-700 hover:bg-emerald-50"
        >
          + Add point
        </button>
      </fieldset>

      <label
        htmlFor={`paragraph-input-${unitNumber}`}
        className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500"
      >
        Paragraph
      </label>
      <textarea
        id={`paragraph-input-${unitNumber}`}
        data-testid="paragraph-input"
        aria-label={`Paragraph answer for unit ${unitNumber}`}
        className="w-full resize-y rounded-lg border border-slate-300 p-2 text-sm text-slate-800 focus:border-emerald-400 focus:outline-none focus:ring-1 focus:ring-emerald-400"
        rows={8}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
      />
      <div className="mt-2 flex items-center justify-between">
        <p className="text-xs text-slate-500">
          <span className={outOfRange ? "text-rose-600" : undefined}>{wordCount} words</span>
          {hasHint ? (
            <>
              {typeof minWords === "number" ? ` · min ${minWords}` : ""}
              {typeof maxWords === "number" ? ` · max ${maxWords}` : ""}
            </>
          ) : null}
        </p>
        <button
          type="button"
          data-testid="paragraph-submit"
          disabled={disabled}
          onClick={handleSubmit}
          className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          {submitLabel}
        </button>
      </div>
    </div>
  );
}
