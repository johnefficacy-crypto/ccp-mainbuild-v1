import React from "react";

export default function CommitConfirmation({
  overrideErrors,
  onSetOverride,
  reason,
  onSetReason,
  onBack,
  onCommit,
  loading,
  error,
}) {
  const canCommit = reason.trim().length > 0 && !loading;

  return (
    <div className="space-y-5" data-testid="commit-confirmation">
      {/* Override checkbox */}
      <div>
        <label className="flex items-start gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={overrideErrors}
            onChange={(e) => onSetOverride(e.target.checked)}
            className="mt-0.5"
            data-testid="override-errors-checkbox"
            aria-describedby="override-helper"
          />
          <span className="text-sm text-gray-700">
            Override duplicate/error warnings where importable
          </span>
        </label>
        <p id="override-helper" className="ml-6 text-xs text-gray-500 mt-1">
          Rows with missing required fields cannot be imported even with override.
        </p>
      </div>

      {/* Reason */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="commit-reason">
          Reason <span className="text-rose-500">*</span>
        </label>
        <textarea
          id="commit-reason"
          rows={3}
          data-testid="commit-reason-input"
          value={reason}
          onChange={(e) => onSetReason(e.target.value)}
          placeholder="e.g. Bulk import SSC CGL 2024 GS-I questions from official PDF"
          className="w-full text-sm border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      {error && (
        <div className="rounded bg-rose-50 border border-rose-200 px-3 py-2 text-sm text-rose-700" data-testid="commit-error">
          {error}
        </div>
      )}

      <div className="flex justify-between">
        <button
          type="button"
          onClick={onBack}
          className="text-sm px-4 py-2 rounded border border-gray-300 text-gray-700 hover:bg-gray-50"
          data-testid="back-to-preview-btn"
        >
          ← Back to preview
        </button>
        <button
          type="button"
          onClick={onCommit}
          disabled={!canCommit}
          aria-disabled={!canCommit}
          data-testid="commit-import-btn"
          className="text-sm px-5 py-2 rounded bg-indigo-600 text-white font-medium hover:bg-indigo-700 disabled:opacity-50"
        >
          {loading ? "Committing…" : "Commit import"}
        </button>
      </div>
    </div>
  );
}
