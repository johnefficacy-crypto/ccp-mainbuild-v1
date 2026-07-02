import { useEffect, useState } from "react";
import WordChips from "./WordChips";
import { clearDraft, loadDraft, saveDraft } from "./autosave";

/**
 * Compose and submit an answer for a single practice sentence unit.
 *
 * @param {Object} props
 * @param {number} props.unitNumber - The sentence unit index (for labels).
 * @param {string} [props.promptText] - Optional prompt shown above the textarea.
 * @param {number} [props.minWords] - Optional minimum word count.
 * @param {number} [props.maxWords] - Optional maximum word count.
 * @param {string[]} [props.requiredWords] - Required words for the exercise (chips).
 * @param {string} [props.initialValue] - Initial draft value.
 * @param {string} [props.sessionId] - Session id for autosave key (enables autosave).
 * @param {(text: string) => void} props.onSubmit - Called with the trimmed draft.
 * @param {boolean} [props.busy] - Disables submit while a request is in flight.
 * @param {string} [props.submitLabel] - Label for the submit button.
 * @returns {JSX.Element}
 */
export default function SentenceBuilder({
  unitNumber,
  promptText,
  minWords,
  maxWords,
  requiredWords,
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

  // Persist the draft as it changes so an accidental reload never loses work.
  useEffect(() => {
    if (sessionId == null) return;
    saveDraft(sessionId, unitNumber, draft);
  }, [sessionId, unitNumber, draft]);

  const words = draft.split(/\s+/).filter(Boolean);
  const wordCount = words.length;
  const belowMin = typeof minWords === "number" && wordCount < minWords;
  const aboveMax = typeof maxWords === "number" && wordCount > maxWords;
  const outOfRange = belowMin || aboveMax;

  const isEmpty = draft.trim().length === 0;
  const disabled = busy || isEmpty;

  const hasHint = typeof minWords === "number" || typeof maxWords === "number";

  const handleSubmit = () => {
    if (sessionId != null) clearDraft(sessionId, unitNumber);
    onSubmit(draft.trim());
  };

  return (
    <div
      data-testid="sentence-builder"
      className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
    >
      {promptText ? (
        <p className="mb-2 text-sm font-medium text-slate-700">{promptText}</p>
      ) : null}
      <textarea
        data-testid="sentence-input"
        aria-label={`Answer for sentence ${unitNumber}`}
        className="w-full resize-y rounded-lg border border-slate-300 p-2 text-sm text-slate-800 focus:border-emerald-400 focus:outline-none focus:ring-1 focus:ring-emerald-400"
        rows={3}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
      />
      <WordChips requiredWords={requiredWords} text={draft} />
      <div className="mt-2 flex items-center justify-between">
        <p className="text-xs text-slate-500">
          <span className={outOfRange ? "text-rose-600" : undefined}>
            {wordCount} words
          </span>
          {hasHint ? (
            <>
              {typeof minWords === "number" ? ` · min ${minWords}` : ""}
              {typeof maxWords === "number" ? ` · max ${maxWords}` : ""}
            </>
          ) : null}
        </p>
        <button
          type="button"
          data-testid="sentence-submit"
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
