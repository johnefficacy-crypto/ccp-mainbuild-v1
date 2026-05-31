import React, { useEffect, useRef, useState } from "react";

export default function AcceptPreviewModal({ previewResult, loading, onCommit, onClose }) {
  const [reason, setReason] = useState("");
  const dialogRef = useRef(null);

  // Trap focus + Escape dismiss
  useEffect(() => {
    const el = dialogRef.current;
    if (!el) return;
    el.focus();
    const handler = (e) => { if (e.key === "Escape") onClose(); };
    el.addEventListener("keydown", handler);
    return () => el.removeEventListener("keydown", handler);
  }, [onClose]);

  const canCommit = reason.trim().length > 0 && !loading;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      data-testid="accept-preview-modal"
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label="Accept proposals preview"
        tabIndex={-1}
        className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6 outline-none"
      >
        <h2 className="text-base font-semibold text-gray-900 mb-4">Preview acceptance</h2>

        {previewResult && (
          <dl className="grid grid-cols-3 gap-3 text-center mb-4">
            <div className="bg-green-50 rounded p-3">
              <dt className="text-xs text-gray-500">Will insert</dt>
              <dd className="text-xl font-bold text-green-700" data-testid="preview-insert-count">
                {previewResult.summary?.insert ?? 0}
              </dd>
            </div>
            <div className="bg-yellow-50 rounded p-3">
              <dt className="text-xs text-gray-500">Skip (dup)</dt>
              <dd className="text-xl font-bold text-yellow-700" data-testid="preview-dup-count">
                {previewResult.summary?.skip_duplicate ?? 0}
              </dd>
            </div>
            <div className="bg-rose-50 rounded p-3">
              <dt className="text-xs text-gray-500">Invalid</dt>
              <dd className="text-xl font-bold text-rose-700" data-testid="preview-invalid-count">
                {previewResult.summary?.invalid ?? 0}
              </dd>
            </div>
          </dl>
        )}

        <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="accept-reason">
          Reason <span className="text-rose-500">*</span>
        </label>
        <input
          id="accept-reason"
          type="text"
          data-testid="accept-reason-input"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="e.g. Batch accept from SSC CGL 2026 syllabus PDF"
          className="w-full text-sm border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 mb-4"
        />

        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="text-sm px-4 py-2 rounded border border-gray-300 text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="button"
            data-testid="commit-btn"
            onClick={() => canCommit && onCommit(reason)}
            disabled={!canCommit}
            className="text-sm px-4 py-2 rounded bg-indigo-600 text-white font-medium hover:bg-indigo-700 disabled:opacity-50"
          >
            {loading ? "Committing…" : "Commit"}
          </button>
        </div>
      </div>
    </div>
  );
}
