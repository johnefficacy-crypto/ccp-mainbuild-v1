import React from "react";

import ErrorState from "../../../shared/ui/ErrorState";
import EmptyState from "../../../shared/ui/EmptyState";
import { SectionHeader } from "../../../shared/ui/studyos";
import ErrorReview from "../english-practice/ErrorReview";
import useErrorLab from "../english-practice/useErrorLab";

/**
 * My Writing Errors — the English section of the Improvement Lab (GQR-S5).
 *
 * Preserves the EWP-4 English authority verbatim after the parent page rename:
 * one API source of truth, `GET /api/study/practice/english/error-lab` through
 * `useErrorLab`. The `ewp_error_lab` read model, owner scope, feedback-release
 * gate, invalidation handling, and reclassification behaviour are untouched —
 * only the learner-facing framing moves under the new parent surface.
 *
 * Owns its own four-state (loading / error / empty / live) rendering so a
 * non-live English feed never suppresses the sibling Quant and Reasoning
 * sections.
 */
export default function MyWritingErrors() {
  const { groups, status, refresh } = useErrorLab();

  return (
    <section className="mt-6" data-testid="improvement-lab-english">
      <SectionHeader
        eyebrow="English"
        title="My Writing Errors"
        sub="Your recurring writing issues, grouped by microtopic"
      />

      {status === "loading" && (
        <div className="mt-3" role="status" aria-live="polite" data-testid="english-loading">
          <div className="space-y-3">
            <div className="h-6 w-1/2 animate-pulse rounded bg-slate-100" />
            <div className="h-20 w-full animate-pulse rounded bg-slate-100" />
          </div>
          <span className="sr-only">Loading your recurring writing issues</span>
        </div>
      )}

      {status === "error" && (
        <div className="mt-3" data-testid="english-error">
          <ErrorState
            title="My Writing Errors unavailable"
            message="We couldn't load your recurring writing issues."
            onRetry={refresh}
          />
        </div>
      )}

      {status === "empty" && (
        <div className="mt-3" data-testid="english-empty">
          <EmptyState
            title="No recurring issues yet"
            description="Once your submitted English practice is evaluated, the issues to work on will appear here."
          />
        </div>
      )}

      {status === "live" && (
        <div className="mt-3" data-testid="english-groups">
          {groups.map((group, i) => (
            <ErrorReview
              key={group.microtopic_id || "unmapped"}
              group={group}
              defaultExpanded={i === 0}
            />
          ))}
        </div>
      )}
    </section>
  );
}
