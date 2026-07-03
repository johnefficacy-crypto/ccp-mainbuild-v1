import { useEffect, useState } from "react";
import BeforeAfterDiff from "./BeforeAfterDiff";
import { wordCount as countWords } from "./requiredWords";
import { clearDraft, loadDraft, saveDraft } from "./autosave";

/**
 * Edit a prior answer into a rewrite, with a live word-level diff.
 *
 * A rewrite must actually change the answer: submitting text identical to the
 * previous answer (ignoring surrounding whitespace) is blocked, since the
 * backend would only reject or duplicate an unchanged resubmission.
 *
 * In-progress rewrites are autosaved to `sessionStorage` keyed by
 * `sessionId + unitNumber` (same key space as first composition), so an
 * accidental reload during a mandatory rewrite recovers the correction rather
 * than discarding it back to the server answer. The draft is cleared only after
 * the submission succeeds.
 *
 * @param {Object} props
 * @param {string} props.previousAnswer - The prior answer to rewrite.
 * @param {number} [props.minWords] - Optional minimum word count.
 * @param {number} [props.maxWords] - Optional maximum word count.
 * @param {string} [props.sessionId] - Session id for autosave key (enables autosave).
 * @param {number|string} [props.unitNumber] - Unit number for autosave key.
 * @param {(text: string) => (Promise<{ok: boolean}>|void)} props.onSubmit - Called with the trimmed draft.
 * @param {boolean} [props.busy] - Disables submit while a request is in flight.
 * @returns {JSX.Element}
 */
export default function RewriteEditor({
  previousAnswer,
  minWords,
  maxWords,
  sessionId,
  unitNumber,
  onSubmit,
  busy = false,
}) {
  // Restore an autosaved in-progress rewrite; otherwise seed from the prior answer.
  const [draft, setDraft] = useState(() => {
    if (sessionId != null) {
      const saved = loadDraft(sessionId, unitNumber);
      if (saved != null) return saved;
    }
    return previousAnswer || "";
  });

  useEffect(() => {
    if (sessionId == null) return;
    saveDraft(sessionId, unitNumber, draft);
  }, [sessionId, unitNumber, draft]);

  // Backend-parity word count (§16 gate #3) — matches deterministic.word_count.
  const wordCount = countWords(draft);
  const belowMin = typeof minWords === "number" && wordCount < minWords;
  const aboveMax = typeof maxWords === "number" && wordCount > maxWords;
  const outOfRange = belowMin || aboveMax;

  const hasHint = typeof minWords === "number" || typeof maxWords === "number";
  const isEmpty = draft.trim().length === 0;
  const unchanged = draft.trim() === String(previousAnswer || "").trim();
  const disabled = busy || isEmpty || unchanged;

  const handleSubmit = async () => {
    const result = await onSubmit(draft.trim());
    if (sessionId != null && result?.ok) clearDraft(sessionId, unitNumber);
  };

  return (
    <div
      data-testid="rewrite-editor"
      className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
    >
      <textarea
        data-testid="rewrite-input"
        aria-label="Rewrite answer"
        className="w-full resize-y rounded-lg border border-slate-300 p-2 text-sm text-slate-800 focus:border-emerald-400 focus:outline-none focus:ring-1 focus:ring-emerald-400"
        rows={3}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
      />
      <div className="mt-3">
        <BeforeAfterDiff before={previousAnswer} after={draft} />
      </div>
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
          {unchanged && !isEmpty ? (
            <span className="ml-2 text-amber-600" data-testid="rewrite-unchanged">
              Change your answer to submit a rewrite.
            </span>
          ) : null}
        </p>
        <button
          type="button"
          data-testid="rewrite-submit"
          disabled={disabled}
          onClick={handleSubmit}
          className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          Submit rewrite
        </button>
      </div>
    </div>
  );
}
