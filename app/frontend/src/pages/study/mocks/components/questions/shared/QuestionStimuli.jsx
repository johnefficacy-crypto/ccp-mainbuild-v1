import React from "react";
import PropTypes from "prop-types";
import MarkdownSafe from "./MarkdownSafe";

const TYPE_LABEL = {
  passage: "Passage",
  caselet: "Caselet",
  table: "Table",
};

/**
 * Renders the shared passage / caselet / table stimuli projected for a PYQ
 * (PYQ v2 PR-5/6). Frozen into the attempt snapshot at start, so this shows the
 * same passage the learner saw regardless of later edits to the source. Renders
 * nothing for authored questions or projected questions with no linked stimulus.
 */
export default function QuestionStimuli({ stimuli = [] }) {
  if (!Array.isArray(stimuli) || stimuli.length === 0) return null;
  return (
    <div className="question-stimuli" data-testid="question-stimuli">
      {stimuli.map((s, i) => (
        <figure
          key={s.id || i}
          className="mb-3 rounded border border-gray-200 bg-gray-50 px-3 py-2"
          data-testid={`question-stimulus-${i}`}
          dir="auto"
        >
          <figcaption className="text-xs font-medium uppercase tracking-wide text-gray-500">
            {TYPE_LABEL[s.stimulus_type] || "Reference"}
          </figcaption>
          <div className="mt-1 text-sm text-gray-800">
            <MarkdownSafe text={s.content_text || ""} />
          </div>
        </figure>
      ))}
    </div>
  );
}

QuestionStimuli.propTypes = {
  stimuli: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string,
      stimulus_type: PropTypes.string,
      content_text: PropTypes.string,
      display_order: PropTypes.number,
    })
  ),
};
