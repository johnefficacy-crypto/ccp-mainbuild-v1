import React from "react";
import PropTypes from "prop-types";
import ErrorState from "../../../shared/ui/ErrorState";

/**
 * Per-section error isolation for the Improvement Lab (GQR-S5).
 *
 * Improvement Lab composes independent, independently-sourced sections (My
 * Writing Errors, Methods & Shortcuts, Approaches & Patterns). The design lock
 * requires that a failure in one section must NOT hide the others. A thrown
 * render error in a single section would otherwise bubble to the route-level
 * RouteErrorBoundary and blank the whole page, so each section is wrapped in
 * this local boundary that degrades only that section to an error card.
 */
export default class SectionBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { failed: false };
  }

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    if (this.state.failed) {
      return (
        <ErrorState
          title={`${this.props.title} unavailable`}
          message="This section couldn't load. The rest of your Improvement Lab is unaffected."
        />
      );
    }
    return this.props.children;
  }
}

SectionBoundary.propTypes = {
  title: PropTypes.string.isRequired,
  children: PropTypes.node,
};
