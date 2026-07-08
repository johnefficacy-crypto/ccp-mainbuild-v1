import React from "react";
import PropTypes from "prop-types";
import MarkdownSafe from "./MarkdownSafe";

const TYPE_LABEL = {
  passage: "Passage",
  caselet: "Caselet",
  table: "Table",
  image: "Image",
  chart: "Chart",
  diagram: "Diagram",
};

const MEDIA_TYPES = new Set(["image", "chart", "diagram"]);

/**
 * Renders the shared stimuli projected for a PYQ. Frozen into the attempt
 * snapshot at start, so this shows the same reference the learner saw regardless
 * of later edits to the source. Renders nothing for authored questions or
 * projected questions with no linked stimulus.
 *
 * Text stimuli (passage/caselet/table) render their `content_text` (PYQ v2
 * PR-5/6). Media stimuli (image/chart/diagram, PYQ v2 PR-11) render the linked
 * asset via `asset_url` with `alt_text` as the accessibility text; when no asset
 * URL is present the `alt_text` is shown as a text fallback so the item is never
 * blank or inaccessible.
 */
export default function QuestionStimuli({ stimuli = [] }) {
  if (!Array.isArray(stimuli) || stimuli.length === 0) return null;
  return (
    <div className="question-stimuli" data-testid="question-stimuli">
      {stimuli.map((s, i) => {
        const isMedia = MEDIA_TYPES.has(s.stimulus_type);
        const altText = s.alt_text || "";
        return (
          <figure
            key={s.id || i}
            className="mb-3 rounded border border-gray-200 bg-gray-50 px-3 py-2"
            data-testid={`question-stimulus-${i}`}
            dir="auto"
          >
            <figcaption className="text-xs font-medium uppercase tracking-wide text-gray-500">
              {TYPE_LABEL[s.stimulus_type] || "Reference"}
            </figcaption>
            {isMedia && s.asset_url ? (
              <img
                src={s.asset_url}
                alt={altText}
                className="mt-1 max-w-full rounded"
                data-testid={`question-stimulus-media-${i}`}
                loading="lazy"
              />
            ) : isMedia ? (
              // Media stimulus with no resolvable asset URL: show the alt text so
              // the reference is never blank or unreadable by assistive tech.
              <div
                className="mt-1 text-sm italic text-gray-600"
                data-testid={`question-stimulus-media-fallback-${i}`}
                role="img"
                aria-label={altText}
              >
                {altText}
              </div>
            ) : (
              <div className="mt-1 text-sm text-gray-800">
                <MarkdownSafe text={s.content_text || ""} />
              </div>
            )}
          </figure>
        );
      })}
    </div>
  );
}

QuestionStimuli.propTypes = {
  stimuli: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string,
      stimulus_type: PropTypes.string,
      content_text: PropTypes.string,
      asset_url: PropTypes.string,
      alt_text: PropTypes.string,
      display_order: PropTypes.number,
    })
  ),
};
