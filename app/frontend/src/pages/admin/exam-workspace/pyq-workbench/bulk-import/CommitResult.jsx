import React from "react";

const RESULT_STYLES = {
  committed:     "text-green-700",
  skipped:       "text-orange-600",
  skipped_stale: "text-orange-600",
  failed:        "text-rose-700",
};

export default function CommitResult({ commitResult, onImportAnother, onClose }) {
  const { committed = 0, skipped = 0, failed = 0, per_row = [] } = commitResult || {};
  const hasFailed = failed > 0;

  return (
    <div className="flex flex-col h-full" data-testid="commit-result">
      {hasFailed && (
        <div className="rounded bg-yellow-50 border border-yellow-300 px-3 py-2 text-sm text-yellow-800 mb-4" data-testid="commit-failure-banner">
          Some rows failed. Review the table below.
        </div>
      )}

      {/* Counts */}
      <div className="flex gap-6 mb-4 text-sm">
        <span data-testid="result-committed">
          <strong className="text-green-700">{committed}</strong> committed
        </span>
        <span data-testid="result-skipped">
          <strong className="text-orange-600">{skipped}</strong> skipped
        </span>
        <span data-testid="result-failed">
          <strong className="text-rose-700">{failed}</strong> failed
        </span>
      </div>

      {/* Per-row table */}
      <div className="flex-1 overflow-auto border border-gray-200 rounded text-[12px]">
        <table className="w-full text-left">
          <thead className="bg-gray-50 sticky top-0">
            <tr>
              {["Row #", "Q#", "Result", "Reason", "Question ID"].map((h) => (
                <th key={h} className="px-2 py-1.5 font-semibold text-gray-600 whitespace-nowrap border-b border-gray-200">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {per_row.map((row, i) => (
              <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="px-2 py-1.5 text-gray-500">{row.row_number ?? i + 1}</td>
                <td className="px-2 py-1.5 text-gray-700">{row.question_number ?? "—"}</td>
                <td className={`px-2 py-1.5 font-semibold ${RESULT_STYLES[row.result] || "text-gray-700"}`}>
                  {row.result}
                </td>
                <td className="px-2 py-1.5 text-gray-500 max-w-[180px]">
                  <span title={row.reason || ""} className="truncate block">{row.reason || "—"}</span>
                </td>
                <td className="px-2 py-1.5 text-gray-400 font-mono text-[10px]">
                  <span title={row.question_id || ""} className="truncate block max-w-[120px]">
                    {row.question_id || "—"}
                  </span>
                </td>
              </tr>
            ))}
            {per_row.length === 0 && (
              <tr>
                <td colSpan={5} className="px-2 py-4 text-center text-gray-400">No rows</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="flex justify-between mt-4">
        <button
          type="button"
          onClick={onImportAnother}
          className="text-sm px-4 py-2 rounded border border-indigo-300 text-indigo-700 hover:bg-indigo-50"
          data-testid="import-another-btn"
        >
          Import another batch
        </button>
        <button
          type="button"
          onClick={onClose}
          className="text-sm px-4 py-2 rounded bg-gray-800 text-white hover:bg-gray-900"
          data-testid="result-close-btn"
        >
          Close
        </button>
      </div>
    </div>
  );
}
