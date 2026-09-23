import React from "react";
import PropTypes from "prop-types";
import MarkdownSafe from "./MarkdownSafe";
import { formatOptionLabel } from "../../../optionLabels";

/**
 * PYQ Explanation — the learner-facing structured explanation panel (EXPL-READ-01).
 * Contract: docs/architecture/pyq-explanations.md.
 *
 * Fed by `questions[].pyq_explanation`, a live verified-only read on the review
 * response — a sibling of `question_snapshot`, never frozen into it. Renders ONLY
 * in review mode, and returns null when there is nothing verified to show, so it
 * is invisible during an active attempt and backward-compatible with payloads
 * that carry no `pyq_explanation` field at all.
 *
 * The backend sends structure, not flattened prose: steps stay a list, per-option
 * rationales stay attached to their option, traps stay separate from the body.
 * This renders each as its own shape rather than concatenating them.
 */

// Printed order mirrors OptionList / MCQSingle: display_order asc, NULLs last.
function byDisplayOrder(a, b) {
  const ad = a?.display_order;
  const bd = b?.display_order;
  if (ad == null && bd == null) return 0;
  if (ad == null) return 1;
  if (bd == null) return -1;
  return ad - bd;
}

// Resolve a rationale's option_index to the printed label the learner sees, so
// the rationale reads as "B. …" against the option list above it rather than
// against a bare number. Falls back to null when the option is not in the frozen
// list — the backend already drops those, this is belt and braces.
function labelForIndex(options, optionIndex) {
  if (!Array.isArray(options)) return null;
  const ordered = [...options].sort(byDisplayOrder);
  const pos = ordered.findIndex((o) => o?.option_index === optionIndex);
  if (pos === -1) return null;
  return formatOptionLabel(ordered[pos], pos);
}

function hasText(value) {
  return typeof value === "string" && value.trim() !== "";
}

function asList(value) {
  return Array.isArray(value) ? value.filter(hasText) : [];
}

export default function PyqExplanationPanel({ mode, explanation, options }) {
  if (mode !== "review") return null;
  if (!explanation || typeof explanation !== "object") return null;

  const steps = asList(explanation.solution_steps);
  const formulas = asList(explanation.formula_used);
  const traps = asList(explanation.common_traps);
  const rationales = Array.isArray(explanation.option_rationales)
    ? explanation.option_rationales.filter((r) => r && hasText(r.rationale))
    : [];

  const hasAnything =
    hasText(explanation.short_explanation) ||
    hasText(explanation.explanation_text) ||
    steps.length > 0 ||
    formulas.length > 0 ||
    traps.length > 0 ||
    rationales.length > 0;
  if (!hasAnything) return null;

  return (
    <section
      data-testid="pyq-explanation-panel"
      aria-label="Explanation"
      className="mt-4 rounded border border-border bg-white/60 p-3 text-left"
    >
      <h3 className="text-sm font-semibold text-slate-800">Explanation</h3>

      {hasText(explanation.short_explanation) ? (
        <p
          data-testid="pyq-explanation-short"
          className="mt-2 text-sm font-medium text-slate-800"
        >
          <MarkdownSafe text={explanation.short_explanation} />
        </p>
      ) : null}

      {hasText(explanation.explanation_text) ? (
        <div data-testid="pyq-explanation-text" className="mt-2 text-sm text-slate-700">
          <MarkdownSafe text={explanation.explanation_text} />
        </div>
      ) : null}

      {steps.length > 0 ? (
        <div className="mt-3">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Solution steps
          </div>
          <ol data-testid="pyq-explanation-steps" className="mt-1 list-decimal pl-5 space-y-1">
            {steps.map((step, i) => (
              // Steps are plain strings with no stable id of their own; position
              // is the identity here and the list is never reordered in place.
              // eslint-disable-next-line react/no-array-index-key
              <li key={i} className="text-sm text-slate-700">
                <MarkdownSafe text={step} />
              </li>
            ))}
          </ol>
        </div>
      ) : null}

      {rationales.length > 0 ? (
        <div className="mt-3">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Why each option
          </div>
          <ul data-testid="pyq-explanation-rationales" className="mt-1 space-y-1">
            {rationales.map((r) => {
              const label = labelForIndex(options, r.option_index);
              return (
                <li
                  key={r.option_index}
                  data-testid={`pyq-explanation-rationale-${r.option_index}`}
                  className="text-sm text-slate-700"
                >
                  {label ? <span className="font-semibold">{label} </span> : null}
                  <MarkdownSafe text={r.rationale} />
                </li>
              );
            })}
          </ul>
        </div>
      ) : null}

      {formulas.length > 0 ? (
        <div className="mt-3">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Formula used
          </div>
          <ul data-testid="pyq-explanation-formulas" className="mt-1 list-disc pl-5 space-y-1">
            {formulas.map((f) => (
              <li key={f} className="text-sm text-slate-700">
                <MarkdownSafe text={f} />
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {traps.length > 0 ? (
        <div className="mt-3">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Watch out for
          </div>
          <ul data-testid="pyq-explanation-traps" className="mt-1 list-disc pl-5 space-y-1">
            {traps.map((t) => (
              <li key={t} className="text-sm text-slate-700">
                <MarkdownSafe text={t} />
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

PyqExplanationPanel.propTypes = {
  mode: PropTypes.string,
  explanation: PropTypes.shape({
    short_explanation: PropTypes.string,
    explanation_text: PropTypes.string,
    solution_steps: PropTypes.arrayOf(PropTypes.string),
    option_rationales: PropTypes.arrayOf(
      PropTypes.shape({
        option_index: PropTypes.number,
        rationale: PropTypes.string,
      }),
    ),
    formula_used: PropTypes.arrayOf(PropTypes.string),
    common_traps: PropTypes.arrayOf(PropTypes.string),
  }),
  options: PropTypes.arrayOf(PropTypes.object),
};
