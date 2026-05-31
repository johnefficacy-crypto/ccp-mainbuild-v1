import React, { useRef } from "react";

function paperLabel(p) {
  return [p.year, p.paper_code, p.shift].filter(Boolean).join(" · ") || p.id;
}

export default function CsvUploadStep({
  papers,
  selectedPaperId,
  onSelectPaper,
  csvFilename,
  onSelectFile,
  onRunPreflight,
  loading,
  error,
}) {
  const fileRef = useRef(null);
  const canRun = selectedPaperId && csvFilename && !loading;

  return (
    <div className="space-y-5" data-testid="csv-upload-step">
      {/* Paper selection */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="bulk-paper-select">
          Destination paper <span className="text-rose-500">*</span>
        </label>
        {selectedPaperId ? (
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-800" data-testid="bulk-fixed-paper">
              {paperLabel(papers.find((p) => p.id === selectedPaperId) || { id: selectedPaperId })}
            </span>
            <button
              type="button"
              className="text-xs text-indigo-600 underline hover:no-underline"
              onClick={() => onSelectPaper(null)}
              data-testid="bulk-change-paper"
            >
              Change paper
            </button>
          </div>
        ) : (
          <select
            id="bulk-paper-select"
            data-testid="bulk-paper-select"
            value=""
            onChange={(e) => onSelectPaper(e.target.value || null)}
            className="w-full text-sm border border-gray-300 rounded px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">— select destination paper —</option>
            {papers.map((p) => (
              <option key={p.id} value={p.id}>{paperLabel(p)}</option>
            ))}
          </select>
        )}
      </div>

      {/* File picker */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="bulk-csv-input">
          CSV file <span className="text-rose-500">*</span>
        </label>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            className="text-sm px-4 py-2 border border-gray-300 rounded bg-white hover:bg-gray-50"
            data-testid="bulk-choose-file-btn"
          >
            Choose file
          </button>
          <span className="text-sm text-gray-500" data-testid="bulk-csv-filename">
            {csvFilename || "No file chosen"}
          </span>
        </div>
        <input
          id="bulk-csv-input"
          ref={fileRef}
          type="file"
          accept=".csv,text/csv"
          className="sr-only"
          data-testid="bulk-csv-input"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) onSelectFile(f);
          }}
        />
      </div>

      {error && (
        <div className="rounded bg-rose-50 border border-rose-200 px-3 py-2 text-sm text-rose-700" data-testid="preflight-error">
          {error}
        </div>
      )}

      <button
        type="button"
        data-testid="run-preflight-btn"
        onClick={onRunPreflight}
        disabled={!canRun}
        className="px-5 py-2 text-sm font-medium rounded bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
      >
        {loading ? "Running preflight…" : "Run preflight"}
      </button>
    </div>
  );
}
