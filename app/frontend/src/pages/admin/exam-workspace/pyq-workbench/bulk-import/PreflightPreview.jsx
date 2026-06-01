import React from "react";

const STATUS_STYLES = {
  ok:        { bg: "bg-green-100 text-green-800",  label: "ok" },
  fuzzy:     { bg: "bg-yellow-100 text-yellow-800", label: "fuzzy" },
  duplicate: { bg: "bg-orange-100 text-orange-800", label: "duplicate" },
  error:     { bg: "bg-rose-100 text-rose-700",    label: "error" },
};

function StatusBadge({ status }) {
  const { bg, label } = STATUS_STYLES[status] || { bg: "bg-gray-100 text-gray-700", label: status };
  return (
    <span
      className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-semibold ${bg}`}
      aria-label={`Status: ${label}`}
    >
      {label}
    </span>
  );
}

export default function PreflightPreview({ preflight, onBack, onContinue }) {
  const { summary = {}, rows = [] } = preflight || {};

  return (
    <div className="flex flex-col h-full" data-testid="preflight-preview">
      {/* Summary bar */}
      <div className="flex gap-3 mb-4 flex-wrap">
        {[
          { key: "ok",        label: "OK",        color: "bg-green-50 text-green-700 border-green-200" },
          { key: "fuzzy",     label: "Fuzzy",     color: "bg-yellow-50 text-yellow-700 border-yellow-200" },
          { key: "duplicate", label: "Duplicate", color: "bg-orange-50 text-orange-700 border-orange-200" },
          { key: "error",     label: "Error",     color: "bg-rose-50 text-rose-700 border-rose-200" },
        ].map(({ key, label, color }) => (
          <div
            key={key}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded border text-sm font-medium ${color}`}
            data-testid={`summary-${key}`}
          >
            <span>{summary[key] ?? 0}</span>
            <span>{label}</span>
          </div>
        ))}
      </div>

      {/* Row table */}
      <div className="flex-1 overflow-auto border border-gray-200 rounded text-[12px]">
        <table className="w-full text-left">
          <thead className="bg-gray-50 sticky top-0">
            <tr>
              {["Row #", "Status", "Q#", "Question text", "Type", "Correct", "Difficulty", "Messages"].map((h) => (
                <th key={h} className="px-2 py-1.5 font-semibold text-gray-600 whitespace-nowrap border-b border-gray-200">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="px-2 py-1.5 text-gray-500">{row.row_number ?? i + 1}</td>
                <td className="px-2 py-1.5"><StatusBadge status={row.status} /></td>
                <td className="px-2 py-1.5 text-gray-700">{row.question_number ?? "—"}</td>
                <td className="px-2 py-1.5 max-w-[200px]">
                  <span title={row.question_text || ""} className="truncate block">
                    {(row.question_text || "").slice(0, 80) || "—"}
                  </span>
                </td>
                <td className="px-2 py-1.5 text-gray-600">{row.question_type ?? "—"}</td>
                <td className="px-2 py-1.5 text-gray-600">{row.correct_option ?? "—"}</td>
                <td className="px-2 py-1.5 text-gray-600">{row.observed_difficulty ?? "—"}</td>
                <td className="px-2 py-1.5 text-gray-500 max-w-[160px]">
                  <span title={(row.messages || []).join("; ")} className="truncate block">
                    {(row.messages || []).join("; ") || "—"}
                  </span>
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={8} className="px-2 py-4 text-center text-gray-400">No rows</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Actions */}
      <div className="flex justify-between mt-4">
        <button
          type="button"
          onClick={onBack}
          className="text-sm px-4 py-2 rounded border border-gray-300 text-gray-700 hover:bg-gray-50"
          data-testid="back-to-upload-btn"
        >
          ← Back to upload
        </button>
        <button
          type="button"
          onClick={onContinue}
          className="text-sm px-4 py-2 rounded bg-indigo-600 text-white font-medium hover:bg-indigo-700"
          data-testid="continue-to-commit-btn"
        >
          Continue to commit →
        </button>
      </div>
    </div>
  );
}
