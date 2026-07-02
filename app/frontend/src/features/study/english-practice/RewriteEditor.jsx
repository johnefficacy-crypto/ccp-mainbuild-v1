import { useState } from "react";
import BeforeAfterDiff from "./BeforeAfterDiff";

/**
 * Edit a prior answer into a rewrite, with a live word-level diff.
 *
 * A rewrite must actually change the answer: submitting text identical to the
 * previous answer (ignoring surrounding whitespace) is blocked, since the
 * backend would only reject or duplicate an unchanged resubmission.
 *
 * @param {Object} props
 * @param {string} props.previousAnswer - The prior answer to rewrite.
 * @param {number} [props.minWords] - Optional minimum word count.
 * @param {number} [props.maxWords] - Optional maximum word count.
 * @param {(text: string) => void} props.onSubmit - Called with the trimmed draft.
 * @param {boolean} [props.busy] - Disables submit while a request is in flight.
 * @returns {JSX.Element}
 */
export default function RewriteEditor({
  previousAnswer,
  minWords,
  maxWords,
  onSubmit,
  busy = false,
}) {
  const [draft, setDraft] = useState(previousAnswer || "");

  const wordCount = draft.split(/\s+/).filter(Boolean).length;
  const belowMin = typeof minWords === "number" && wordCount < minWords;
  const aboveMax = typeof maxWords === "number" && wordCount > maxWords;
  const outOfRange = belowMin || aboveMax;

  const hasHint = typeof minWords === "number" || typeof maxWords === "number";
  const isEmpty = draft.trim().length === 0;
  const unchanged = draft.trim() === String(previousAnswer || "").trim();
  const disabled = busy || isEmpty || unchanged;

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
          onClick={() => onSubmit(draft.trim())}
          className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          Submit rewrite
        </button>
      </div>
    </div>
  );
}
