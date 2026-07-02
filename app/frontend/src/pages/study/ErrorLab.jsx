/**
 * ErrorLab — the EWP-4 Error Lab surface.
 *
 * Route: /app/study/error-lab — mounted UNDER StudyShell and inside
 * RouteErrorBoundary (like the EWP-3 practice route), NOT via
 * AttemptShellRouter, and ABSENT from the sidebar (no-new-surface rule). Reached
 * from study surfaces / planner tasks, not a top-level destination.
 *
 * One API source of truth: /api/study/practice/english/error-lab through
 * useErrorLab (four-state useApiCollection). The backend returns only the
 * caller's current-state, feedback-released, non-invalidated issues grouped by
 * microtopic — no pending/rejected/stale/withdrawn leakage. The Grammar Lab
 * cross-links are disabled "coming soon" stubs (verified grammar prompts do not
 * exist yet); no generation endpoint is wired.
 */
import React from "react";

import ErrorState from "../../shared/ui/ErrorState";
import EmptyState from "../../shared/ui/EmptyState";
import { PageHeader, SectionHeader } from "../../shared/ui/studyos";
import ErrorReview from "../../features/study/english-practice/ErrorReview";
import useErrorLab from "../../features/study/english-practice/useErrorLab";

export default function ErrorLab() {
  const { groups, status, refresh } = useErrorLab();

  return (
    <div className="mx-auto max-w-3xl p-4" data-testid="error-lab">
      <PageHeader
        eyebrow="English Writing Practice"
        title="Error Lab"
        sub="Your recurring writing issues, grouped by microtopic"
      />

      {status === "loading" && (
        <div className="mt-4" role="status" aria-live="polite" data-testid="error-lab-loading">
          <div className="space-y-3">
            <div className="h-6 w-1/2 animate-pulse rounded bg-slate-100" />
            <div className="h-20 w-full animate-pulse rounded bg-slate-100" />
          </div>
          <span className="sr-only">Loading your recurring writing issues</span>
        </div>
      )}

      {status === "error" && (
        <div className="mt-4">
          <ErrorState
            title="Error Lab unavailable"
            message="We couldn't load your recurring writing issues."
            onRetry={refresh}
          />
        </div>
      )}

      {status === "empty" && (
        <div className="mt-4" data-testid="error-lab-empty">
          <EmptyState
            title="No recurring issues yet"
            description="Once your submitted English practice is evaluated, the issues to work on will appear here."
          />
        </div>
      )}

      {status === "live" && (
        <section className="mt-4" data-testid="error-lab-groups">
          <SectionHeader eyebrow="Feedback" title="Issues to work on" />
          {groups.map((group, i) => (
            <ErrorReview
              key={group.microtopic_id || "unmapped"}
              group={group}
              defaultExpanded={i === 0}
            />
          ))}
        </section>
      )}
    </div>
  );
}
