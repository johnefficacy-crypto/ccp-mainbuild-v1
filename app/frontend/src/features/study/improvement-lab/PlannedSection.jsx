import React from "react";
import PropTypes from "prop-types";

import EmptyState from "../../../shared/ui/EmptyState";
import { SectionHeader } from "../../../shared/ui/studyos";

/**
 * A not-yet-wired Improvement Lab section (GQR-S5).
 *
 * The personalized Quant (Methods & Shortcuts) and Reasoning (Approaches &
 * Patterns) feeds are owned by GQR-S6 and depend on the learner strategy
 * endpoints, which are not built in this slice. Per the delivery sequence
 * (PR 5), these sections render an honest, independent empty state now rather
 * than pointing at a non-existent endpoint and surfacing a permanent error.
 *
 * Structurally independent: its own header and state box, so it neither hides
 * nor is hidden by the sibling sections. When the GQR-S6 endpoint lands, swap
 * the body for a four-state feed without touching the parent composition.
 */
export default function PlannedSection({ testId, eyebrow, title, sub, description }) {
  return (
    <section className="mt-6" data-testid={testId}>
      <SectionHeader eyebrow={eyebrow} title={title} sub={sub} />
      <div className="mt-3" data-testid={`${testId}-empty`}>
        <EmptyState title="Coming soon" description={description} />
      </div>
    </section>
  );
}

PlannedSection.propTypes = {
  testId: PropTypes.string.isRequired,
  eyebrow: PropTypes.string,
  title: PropTypes.string.isRequired,
  sub: PropTypes.string,
  description: PropTypes.string,
};
