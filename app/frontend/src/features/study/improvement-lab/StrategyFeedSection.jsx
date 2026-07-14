import React from "react";
import PropTypes from "prop-types";

import ErrorState from "../../../shared/ui/ErrorState";
import EmptyState from "../../../shared/ui/EmptyState";
import { SectionHeader } from "../../../shared/ui/studyos";
import useStrategyFeed from "./useStrategyFeed";
import StrategyFeedCard from "./StrategyFeedCard";

/**
 * A personalized Improvement Lab strategy section (GQR-S6) — Quant ("Methods &
 * Shortcuts") or Reasoning ("Approaches & Patterns"). Replaces the GQR-S5
 * `PlannedSection` placeholder without touching the parent composition: same
 * `${testId}` on the section and `${testId}-empty` on the empty body, so the
 * shell's section-isolation contract is preserved.
 *
 * Owns its own four-state (loading / error / empty / live) rendering so a
 * non-live feed never suppresses the sibling sections.
 */
export default function StrategyFeedSection({ subject, testId, eyebrow, title, sub, emptyDescription }) {
  const { items, status, refresh } = useStrategyFeed(subject);

  return (
    <section className="mt-6" data-testid={testId}>
      <SectionHeader eyebrow={eyebrow} title={title} sub={sub} />

      {status === "loading" && (
        <div className="mt-3" role="status" aria-live="polite" data-testid={`${testId}-loading`}>
          <div className="space-y-3">
            <div className="h-6 w-1/2 animate-pulse rounded bg-slate-100" />
            <div className="h-20 w-full animate-pulse rounded bg-slate-100" />
          </div>
          <span className="sr-only">Loading your practice strategies</span>
        </div>
      )}

      {status === "error" && (
        <div className="mt-3" data-testid={`${testId}-error`}>
          <ErrorState
            title={`${title} unavailable`}
            message="We couldn't load your practice strategies."
            onRetry={refresh}
          />
        </div>
      )}

      {status === "empty" && (
        <div className="mt-3" data-testid={`${testId}-empty`}>
          <EmptyState title="Nothing to revisit yet" description={emptyDescription} />
        </div>
      )}

      {status === "live" && (
        <div className="mt-3" data-testid={`${testId}-list`}>
          {items.map((s) => (
            <StrategyFeedCard key={`${s.subject_family}:${s.id}`} strategy={s} />
          ))}
        </div>
      )}
    </section>
  );
}

StrategyFeedSection.propTypes = {
  subject: PropTypes.oneOf(["quant", "reasoning"]).isRequired,
  testId: PropTypes.string.isRequired,
  eyebrow: PropTypes.string,
  title: PropTypes.string.isRequired,
  sub: PropTypes.string,
  emptyDescription: PropTypes.string,
};
