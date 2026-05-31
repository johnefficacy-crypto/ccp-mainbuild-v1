import React from "react";

export default function ProposalActionBar({
  proposals,
  selectedKeys,
  currentPage,
  onAcceptSelected,
  onSelectPage,
  onSelectByMinConfidence,
  disabled,
}) {
  const selectedCount = proposals.filter((p) => selectedKeys.has(p.client_proposal_key)).length;

  return (
    <div
      className="flex flex-wrap items-center gap-2 px-4 py-2 border-t border-gray-200 bg-gray-50"
      data-testid="proposal-action-bar"
    >
      <button
        type="button"
        data-testid="accept-selected-btn"
        disabled={disabled || selectedCount === 0}
        onClick={onAcceptSelected}
        className="text-sm px-3 py-1 rounded bg-indigo-600 text-white font-medium hover:bg-indigo-700 disabled:opacity-50"
      >
        Accept Selected ({selectedCount})
      </button>

      <button
        type="button"
        data-testid="accept-all-page-btn"
        disabled={disabled}
        onClick={() => {
          onSelectPage(currentPage);
          // Trigger accept after selection updates — parent coordinates this
        }}
        className="text-sm px-3 py-1 rounded border border-indigo-300 text-indigo-700 hover:bg-indigo-50 disabled:opacity-50"
      >
        Accept All on Page
      </button>

      <button
        type="button"
        data-testid="accept-high-confidence-btn"
        disabled={disabled}
        onClick={() => onSelectByMinConfidence(0.95)}
        className="text-sm px-3 py-1 rounded border border-gray-300 text-gray-700 hover:bg-gray-100 disabled:opacity-50"
      >
        Accept ≥ 95%
      </button>
    </div>
  );
}
