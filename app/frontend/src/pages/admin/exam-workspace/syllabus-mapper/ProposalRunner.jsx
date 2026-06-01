import React from "react";

export default function ProposalRunner({ docId, loading, error, onRun, proposalCount }) {
  return (
    <div className="flex items-center gap-3">
      <button
        type="button"
        data-testid="run-propose-btn"
        onClick={() => docId && onRun(docId)}
        disabled={!docId || loading}
        className="text-sm px-4 py-1.5 rounded bg-indigo-600 text-white font-medium hover:bg-indigo-700 disabled:opacity-50"
      >
        {loading ? "Running…" : "Run Proposer"}
      </button>
      {proposalCount > 0 && (
        <span className="text-sm text-gray-600" data-testid="proposal-count">
          {proposalCount} proposals found
        </span>
      )}
      {error && (
        <span className="text-sm text-rose-600" data-testid="propose-error">
          {error}
        </span>
      )}
    </div>
  );
}
