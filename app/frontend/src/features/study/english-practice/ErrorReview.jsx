import React, { useState } from "react";
import PropTypes from "prop-types";
import { StudyCard } from "../../../shared/ui/studyos";

/**
 * Severity → badge classes (architecture §4.5b language-issue palette), shared
 * with {@link SentenceIssueCard}.
 * @type {Record<string, string>}
 */
const SEVERITY_BADGE = {
  must_fix: "bg-rose-100 text-rose-700",
  should_fix: "bg-amber-100 text-amber-800",
  advisory: "bg-slate-100 text-slate-600",
};

/**
 * One Error Lab microtopic group (EWP-4, §13.2 `ErrorReview`).
 *
 * Renders a microtopic header with its current-state issue count and an
 * expandable list of the caller's issues in that microtopic. Error Lab issues
 * span many sessions/answers, so there is no single answer text to highlight
 * against — each issue is shown as a compact card (issue_type, severity, the
 * quoted fragment, explanation, suggestion) rather than the UTF-16 in-line
 * highlight used inside a live session.
 *
 * The Grammar Lab cross-link is a disabled "coming soon" stub: a real drill
 * needs a verified grammar-prompt bank that does not exist yet, so it is never
 * wired to a generation endpoint (verified-only reads).
 *
 * @param {object} props
 * @param {{ microtopic_id: string|null, issue_count: number, issues: Array }} props.group
 * @param {boolean} [props.defaultExpanded]
 */
export default function ErrorReview({ group, defaultExpanded = false }) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const issues = Array.isArray(group?.issues) ? group.issues : [];
  const count = group?.issue_count ?? issues.length;
  const title = group?.microtopic_id
    ? `Microtopic ${group.microtopic_id}`
    : "Unmapped issues";
  const panelId = `error-group-${group?.microtopic_id || "unmapped"}`;

  return (
    <StudyCard className="mt-3" data-testid={`error-group-${group?.microtopic_id || "unmapped"}`}>
      <button
        type="button"
        aria-expanded={expanded}
        aria-controls={panelId}
        aria-label={`${title}: ${count} recurring ${count === 1 ? "issue" : "issues"}`}
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center justify-between gap-3 text-left"
      >
        <span className="flex items-center gap-2">
          <span className="text-sm font-semibold text-slate-800">{title}</span>
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
            {count} {count === 1 ? "issue" : "issues"}
          </span>
        </span>
        <span aria-hidden="true" className="text-slate-400">
          {expanded ? "▾" : "▸"}
        </span>
      </button>

      {expanded && (
        <div id={panelId} className="mt-3 space-y-2">
          {issues.map((issue) => {
            const badgeClass = SEVERITY_BADGE[issue.severity] || SEVERITY_BADGE.advisory;
            const label = String(issue.issue_type || "").replace(/_/g, " ");
            return (
              <div
                key={issue.id}
                data-testid="error-issue"
                className="rounded border border-slate-100 p-3 text-sm"
              >
                <div className="mb-2 flex items-center gap-2">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${badgeClass}`}>
                    {issue.severity ? issue.severity.replace(/_/g, " ") : "advisory"}
                  </span>
                  <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {label}
                  </span>
                </div>
                {issue.quoted_text ? (
                  <p className="mb-1">
                    <mark
                      className="rounded bg-rose-100 px-0.5 text-rose-800"
                      aria-label={`issue: ${issue.quoted_text}`}
                    >
                      {issue.quoted_text}
                    </mark>
                  </p>
                ) : null}
                {issue.explanation ? (
                  <p className="text-slate-500">{issue.explanation}</p>
                ) : null}
                {issue.suggested_text ? (
                  <div className="mt-2 rounded bg-emerald-50 p-2 text-emerald-800">
                    <span className="mb-0.5 block text-xs font-semibold uppercase tracking-wide">
                      Suggested
                    </span>
                    <span className="whitespace-pre-wrap">{issue.suggested_text}</span>
                  </div>
                ) : null}
              </div>
            );
          })}

          {/* Grammar Lab drill — deferred until a verified grammar-prompt bank
              exists (EWP-4). Disabled stub; never wired to generation. */}
          <button
            type="button"
            disabled
            aria-disabled="true"
            data-testid="grammar-lab-stub"
            aria-label={`Practise ${title} in Grammar Lab (coming soon)`}
            title="Grammar Lab drills are coming soon"
            className="mt-1 w-full cursor-not-allowed rounded-lg border border-dashed border-slate-200 px-3 py-2 text-xs font-medium text-slate-400"
          >
            Practise in Grammar Lab (coming soon)
          </button>
        </div>
      )}
    </StudyCard>
  );
}

ErrorReview.propTypes = {
  group: PropTypes.shape({
    microtopic_id: PropTypes.string,
    issue_count: PropTypes.number,
    issues: PropTypes.arrayOf(PropTypes.object),
  }).isRequired,
  defaultExpanded: PropTypes.bool,
};
