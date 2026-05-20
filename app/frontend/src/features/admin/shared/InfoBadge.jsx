import React from "react";

// A small "i" badge for a panel's top-right corner. Holds explanatory text in
// a tooltip (title + aria-label) instead of a description line inside the panel
// body, keeping the panel compact. Rendered inside the `.oc` admin surface so
// it inherits the `.badge` styling.
export default function InfoBadge({ text }) {
  if (!text) return null;
  return (
    <span
      className="badge neutral"
      title={text}
      aria-label={text}
      role="img"
      style={{ cursor: "help", width: 18, height: 18, padding: 0, display: "inline-flex", alignItems: "center", justifyContent: "center", borderRadius: "50%", fontStyle: "italic", fontWeight: 700, flexShrink: 0 }}
    >
      i
    </span>
  );
}
