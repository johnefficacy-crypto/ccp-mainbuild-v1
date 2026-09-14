import React from "react";
import PropTypes from "prop-types";

const RISK_COPY = {
  low: "Small change to today.",
  medium: "Today changes noticeably.",
  high: "Most of today is replaced.",
};

/**
 * What regenerating today would do, before it does it.
 *
 * `/api/study/plan/draft` already returns `changes` and `risk_level`, so the
 * preview is the real diff, not an estimate. Protected cards are counted from
 * the board itself — the planner cannot touch them, and saying so is the point
 * of showing this at all.
 */
export default function RegeneratePreview({
  draft,
  protectedCount,
  loading,
  error,
  onPreview,
  onApply,
  applying,
}) {
  const changes = draft?.changes;
  const risk = draft?.risk_level;

  return (
    <div className="rounded-xl border border-[#E7DECB] bg-white/60 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="font-heading text-[16px] leading-tight text-[#2E2218]">
            Rebuild today
          </h3>
          <p className="mt-1 text-[11.5px] text-clay-700">
            Replaces the planner&apos;s blocks for today.{" "}
            {protectedCount > 0
              ? `Your ${protectedCount} arranged ${
                  protectedCount === 1 ? "block stays" : "blocks stay"
                } exactly where ${protectedCount === 1 ? "it is" : "they are"}.`
              : "You have not arranged anything today, so all of it can change."}
          </p>
        </div>
        <button
          type="button"
          onClick={onPreview}
          disabled={loading}
          className="rounded border border-[#2E2218] px-3 py-1.5 text-[12px] font-semibold text-[#2E2218] hover:bg-[#F3EADB] disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#2E2218]"
        >
          {loading ? "Checking…" : "See what changes"}
        </button>
      </div>

      {error && (
        <p role="status" className="mt-3 text-[12px] text-rose-700">
          {error}
        </p>
      )}

      {changes && (
        <div className="mt-3 border-t border-[#E7DECB] pt-3">
          <dl className="flex flex-wrap gap-x-6 gap-y-1 text-[12px]">
            <div className="flex gap-1.5">
              <dt className="text-clay-700">Added</dt>
              <dd className="num-mono font-semibold text-[#2E2218]">
                {changes.added_count ?? 0}
              </dd>
            </div>
            <div className="flex gap-1.5">
              <dt className="text-clay-700">Removed</dt>
              <dd className="num-mono font-semibold text-[#2E2218]">
                {changes.removed_count ?? 0}
              </dd>
            </div>
            <div className="flex gap-1.5">
              <dt className="text-clay-700">Unchanged</dt>
              <dd className="num-mono font-semibold text-[#2E2218]">
                {changes.unchanged_count ?? 0}
              </dd>
            </div>
            <div className="flex gap-1.5">
              <dt className="text-clay-700">Impact</dt>
              <dd className="font-semibold text-[#2E2218]">
                {RISK_COPY[risk] || "Impact unknown."}
              </dd>
            </div>
          </dl>
          <button
            type="button"
            onClick={onApply}
            disabled={applying}
            className="mt-3 rounded bg-[#2E2218] px-3 py-1.5 text-[12px] font-semibold text-[#F3EADB] hover:bg-[#4a3726] disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#2E2218]"
          >
            {applying ? "Rebuilding…" : "Rebuild today"}
          </button>
        </div>
      )}
    </div>
  );
}

RegeneratePreview.propTypes = {
  draft: PropTypes.shape({
    changes: PropTypes.object,
    risk_level: PropTypes.string,
  }),
  protectedCount: PropTypes.number,
  loading: PropTypes.bool,
  error: PropTypes.string,
  onPreview: PropTypes.func,
  onApply: PropTypes.func,
  applying: PropTypes.bool,
};
