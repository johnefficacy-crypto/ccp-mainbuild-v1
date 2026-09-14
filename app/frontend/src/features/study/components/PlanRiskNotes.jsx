import React from "react";
import PropTypes from "prop-types";

/**
 * Why the plan looks the way it does, in sentences.
 *
 * Same flags as `PlanRiskFlags`, which still serves the home surface; what is
 * gone is the severity pill beside each one. "medium severity" is a triage
 * label from a queue, and it asks the reader to translate before they can act.
 * The reason and the suggested action say everything the pill did, in words an
 * aspirant can act on directly.
 *
 * Nothing flagged means nothing rendered. A card saying "nothing is wrong" is
 * still a card the reader has to scan past on the page's most crowded screen.
 */
export default function PlanRiskNotes({ flags }) {
  const rows = (Array.isArray(flags) ? flags : []).filter(
    (f) => f && (f.label || f.reason),
  );
  if (!rows.length) return null;

  return (
    <section data-testid="plan-risk-notes">
      <h2 className="font-heading text-[18px] leading-tight text-[#2E2218]">
        Why your plan looks like this
      </h2>
      <ul className="mt-3 space-y-3">
        {rows.map((f, i) => (
          <li
            key={`${f.code || "note"}-${(f.subject || f.reason || "").slice(0, 32)}-${i}`}
            data-testid={`plan-risk-note-${f.code || "note"}`}
            className="rounded-xl border border-[#E7DECB] bg-white/60 px-4 py-3"
          >
            <p className="text-[13px] leading-relaxed text-[#2E2218]">
              {f.reason || f.label}
            </p>
            {f.suggested_action ? (
              <p className="mt-1.5 text-[12.5px] leading-relaxed text-clay-700">
                {f.suggested_action}
              </p>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}

PlanRiskNotes.propTypes = {
  flags: PropTypes.arrayOf(
    PropTypes.shape({
      code: PropTypes.string,
      label: PropTypes.string,
      reason: PropTypes.string,
      subject: PropTypes.string,
      suggested_action: PropTypes.string,
    }),
  ),
};
