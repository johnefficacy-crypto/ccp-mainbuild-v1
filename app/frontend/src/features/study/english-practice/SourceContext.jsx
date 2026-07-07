import { useId } from "react";

/**
 * SourceContext — immutable, read-only task context shown ABOVE the answer
 * editor for source-bearing writing exercises (EWP-SP1).
 *
 * The backend surfaces `prompt.source_text` from the immutable per-session
 * snapshot (migration 221). It is the sentence/passage the learner must act on
 * (correct, summarise, use in context) and MUST NOT be editable or submitted as
 * answer content — this component renders it as static, non-interactive text
 * (never an input), so it can never be mistaken for the answer field.
 *
 * Renders nothing when `sourceText` is null/empty — pure construction prompts
 * carry no source and must not show an empty context block.
 *
 * @param {Object} props
 * @param {string} [props.sourceText] - The immutable source/task text.
 * @param {string} [props.exerciseType] - Drives the human label.
 * @returns {JSX.Element|null}
 */
export default function SourceContext({ sourceText, exerciseType }) {
  const labelId = useId();
  if (sourceText == null || String(sourceText).trim().length === 0) return null;

  return (
    <section
      data-testid="source-context"
      aria-labelledby={labelId}
      aria-readonly="true"
      className="mb-3 rounded-xl border border-slate-200 bg-slate-50 p-3"
    >
      <p
        id={labelId}
        data-testid="source-context-label"
        className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500"
      >
        {sourceContextLabel(exerciseType)}
      </p>
      <p
        data-testid="source-context-text"
        className="whitespace-pre-wrap text-sm text-slate-800"
      >
        {sourceText}
      </p>
    </section>
  );
}

/**
 * Human label for the source block, chosen by exercise type.
 * - correction-type (e.g. `sentence_correction`) → "Sentence to correct"
 * - source/passage-bearing types → "Source passage"
 * - sensible default otherwise.
 */
export function sourceContextLabel(exerciseType) {
  const type = String(exerciseType || "").toLowerCase();
  if (type.includes("correction")) return "Sentence to correct";
  if (
    type.includes("summary") ||
    type.includes("precis") ||
    type.includes("passage") ||
    type.includes("comprehension") ||
    type.includes("vocabulary")
  ) {
    return "Source passage";
  }
  return "Task context";
}
