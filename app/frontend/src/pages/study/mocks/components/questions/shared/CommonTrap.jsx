import React from "react";
import PropTypes from "prop-types";
import MathRenderer from "./MathRenderer";

/**
 * The question's flat `common_trap` note (mock_question_bank.common_trap).
 * Review-only: returns null in any mode other than "review", so it can never
 * surface during an active attempt, and null when the field is absent/blank.
 */
export default function CommonTrap({ mode, text }) {
  if (mode !== "review") return null;
  if (typeof text !== "string" || text.trim() === "") return null;
  return (
    <div
      data-testid="question-common-trap"
      className="mt-3 rounded border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-slate-800"
    >
      <div className="text-xs font-semibold uppercase tracking-wide text-amber-800">Common trap</div>
      <div className="mt-1">
        <MathRenderer text={text} />
      </div>
    </div>
  );
}

CommonTrap.propTypes = {
  mode: PropTypes.string,
  text: PropTypes.string,
};
