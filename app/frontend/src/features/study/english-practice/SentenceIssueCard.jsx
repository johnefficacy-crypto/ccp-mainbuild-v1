import React from "react";
import { verifyAndSliceSpan } from "./utf16";
import { StudyCard } from "../../../shared/ui/studyos";

/**
 * Severity → badge classes (architecture §4.5b language-issue palette).
 * @type {Record<string, string>}
 */
const SEVERITY_BADGE = {
  must_fix: "bg-rose-100 text-rose-700",
  should_fix: "bg-amber-100 text-amber-800",
  advisory: "bg-slate-100 text-slate-600",
};

/**
 * Renders ONE language issue over the answer with a verified UTF-16 highlight.
 *
 * The highlight is only drawn when {@link verifyAndSliceSpan} confirms the span
 * still aligns with the issue's `quoted_text`; a stale/mismatched span falls
 * back to a plain (unhighlighted) explanation.
 *
 * @param {object} props
 * @param {{
 *   issue_type: string,
 *   span_start_utf16: number,
 *   span_end_utf16: number,
 *   quoted_text: string,
 *   explanation: string,
 *   suggested_text?: string,
 *   severity: 'must_fix' | 'should_fix' | 'advisory',
 * }} props.issue  the language issue to render
 * @param {string} props.answerText  full answer text the span refers to
 * @returns {JSX.Element}
 */
export default function SentenceIssueCard({ issue, answerText }) {
  const badgeClass = SEVERITY_BADGE[issue.severity] || SEVERITY_BADGE.advisory;
  const label = String(issue.issue_type || "").replace(/_/g, " ");

  const { valid, before, highlighted, after } = verifyAndSliceSpan(
    answerText,
    issue.span_start_utf16,
    issue.span_end_utf16,
    issue.quoted_text,
  );

  return (
    <StudyCard
      className="text-sm"
      data-testid={valid ? "issue-card" : "issue-card-invalid"}
    >
      <header className="mb-3 flex items-center gap-2">
        <span
          className={`rounded-full px-2 py-0.5 text-xs font-medium ${badgeClass}`}
        >
          {issue.severity ? issue.severity.replace(/_/g, " ") : "advisory"}
        </span>
        <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {label}
        </span>
      </header>

      {valid ? (
        <p className="mb-2 whitespace-pre-wrap text-slate-800">
          {before}
          <mark
            className="rounded bg-rose-100 px-0.5 text-rose-800"
            aria-label={`issue: ${issue.quoted_text}`}
          >
            {highlighted}
          </mark>
          {after}
        </p>
      ) : (
        <p className="mb-1 text-xs italic text-slate-400">
          Highlight unavailable for this revision.
        </p>
      )}

      <p className="text-slate-500">{issue.explanation}</p>

      {issue.suggested_text ? (
        <div className="mt-3 rounded bg-emerald-50 p-2 text-emerald-800">
          <span className="mb-0.5 block text-xs font-semibold uppercase tracking-wide">
            Suggested
          </span>
          <span className="whitespace-pre-wrap">{issue.suggested_text}</span>
        </div>
      ) : null}
    </StudyCard>
  );
}
