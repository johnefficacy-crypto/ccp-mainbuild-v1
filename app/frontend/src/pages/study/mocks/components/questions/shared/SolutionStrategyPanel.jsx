import React from "react";
import PropTypes from "prop-types";
import MathRenderer from "./MathRenderer";
import MarkdownSafe from "./MarkdownSafe";

/**
 * Solution Strategy — the learner-facing per-question strategy panel (GQR-S1).
 * Contract: docs/architecture/solution-strategies-improvement-lab.md.
 *
 * Subject-agnostic: the same normalized DTO covers Quant ("Methods & Shortcuts")
 * and, later, Reasoning ("Approaches & Patterns"). Renders ONLY in review mode,
 * and returns null when there is nothing verified to show, so it is invisible
 * during an active attempt and backward-compatible with payloads that carry no
 * `solution_strategies` field.
 */

const FIELD_LABELS = [
  ["standard_method", "Standard method"],
  ["faster_method", "Faster method"],
  ["key_observation", "Key observation"],
  ["worked_example", "Worked example"],
  ["common_traps", "Watch out for"],
];

// `formula_latex` is stored as raw LaTeX (no delimiters); MathRenderer keys off
// `$…$`/`$$…$$`, so wrap a bare formula in block delimiters. An already-delimited
// string passes through untouched.
function asMath(latex) {
  const s = (latex || "").trim();
  if (!s) return "";
  return /\$[^$]+\$/.test(s) ? s : `$$${s}$$`;
}

export default function SolutionStrategyPanel({
  mode,
  strategies,
  title = "Solution Strategy",
  ariaLabel = "Solution strategies",
  testId = "solution-strategy-panel",
}) {
  if (mode !== "review") return null;
  const list = Array.isArray(strategies) ? strategies : [];
  if (list.length === 0) return null;

  return (
    <section
      aria-label={ariaLabel}
      data-testid={testId}
      className="mt-4 rounded border border-clay-200 bg-clay-50 p-3"
    >
      <h4 className="font-heading text-sm text-clay-900">{title}</h4>
      <div className="mt-2 space-y-3">
        {list.map((s) => (
          <div
            key={`${s.subject_family || "s"}:${s.id}`}
            data-testid={`solution-strategy-${s.id}`}
            className="rounded bg-white p-2 text-sm"
          >
            <div className="font-medium text-clay-900">
              {s.name}
              {s.strategy_type ? (
                <span className="ml-2 text-xs text-clay-600">
                  · {String(s.strategy_type).replaceAll("_", " ")}
                </span>
              ) : null}
            </div>
            {s.formula_latex ? (
              <div className="mt-1" data-testid={`solution-strategy-${s.id}-formula`}>
                <MathRenderer text={asMath(s.formula_latex)} />
              </div>
            ) : null}
            {FIELD_LABELS.map(([key, label]) =>
              s[key] ? (
                <div key={key} className="mt-1" data-testid={`solution-strategy-${s.id}-${key}`}>
                  <div className="text-xs font-semibold text-clay-600">{label}</div>
                  <MarkdownSafe text={s[key]} />
                </div>
              ) : null,
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

SolutionStrategyPanel.propTypes = {
  mode: PropTypes.string,
  strategies: PropTypes.arrayOf(PropTypes.object),
  title: PropTypes.string,
  ariaLabel: PropTypes.string,
  testId: PropTypes.string,
};
