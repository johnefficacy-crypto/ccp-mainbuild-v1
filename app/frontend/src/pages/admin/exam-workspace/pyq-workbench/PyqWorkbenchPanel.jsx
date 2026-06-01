import React, { lazy, Suspense, useState } from "react";
import { useExamWorkspace } from "../ExamWorkspaceContext";
import { usePyqWorkbench } from "./usePyqWorkbench";
import BulkImportModal from "./bulk-import/BulkImportModal";

const PyqPaperWorkspace = lazy(() => import("../../studyos/PyqPaperWorkspace"));

export default function PyqWorkbenchPanel() {
  const { exam, cycle } = useExamWorkspace();
  const examId = exam?.id;
  const cycleId = cycle?.id ?? null;

  const { papers, selectedPaperId, setSelectedPaperId, loading, error } = usePyqWorkbench(
    examId,
    cycleId,
  );

  const [showBulkImport, setShowBulkImport] = useState(false);

  function groupPapers() {
    if (cycleId) return null; // flat list when cycle is set
    const groups = {};
    for (const p of papers) {
      const key = p.exam_cycle_id || "—";
      if (!groups[key]) groups[key] = [];
      groups[key].push(p);
    }
    return groups;
  }

  function paperLabel(p) {
    return [p.year, p.paper_code, p.shift].filter(Boolean).join(" · ") || p.id;
  }

  const groups = groupPapers();

  return (
    <div className="flex flex-col h-full" data-testid="pyq-workbench-panel">
      {/* Paper picker bar */}
      <div className="flex items-center gap-3 px-4 py-2 border-b border-gray-200 bg-white flex-shrink-0">
        <label className="text-sm font-medium text-gray-700 whitespace-nowrap" htmlFor="pyq-paper-select">
          Paper:
        </label>
        {loading && <span className="text-sm text-gray-400">Loading papers…</span>}
        {error && <span className="text-sm text-rose-600" data-testid="pyq-papers-error">{error}</span>}
        {!loading && !error && papers.length === 0 && (
          <span className="text-sm text-gray-500" data-testid="pyq-empty-state">
            No PYQ papers for this exam/cycle. Create one in the CMS.
          </span>
        )}
        {!loading && papers.length > 0 && (
          <select
            id="pyq-paper-select"
            data-testid="pyq-paper-select"
            value={selectedPaperId || ""}
            onChange={(e) => setSelectedPaperId(e.target.value || null)}
            className="text-sm border border-gray-300 rounded px-3 py-1.5 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">— select a paper —</option>
            {groups
              ? Object.entries(groups).map(([cycleKey, ps]) => (
                  <optgroup key={cycleKey} label={`Cycle: ${cycleKey}`}>
                    {ps.map((p) => (
                      <option key={p.id} value={p.id}>{paperLabel(p)}</option>
                    ))}
                  </optgroup>
                ))
              : papers.map((p) => (
                  <option key={p.id} value={p.id}>{paperLabel(p)}</option>
                ))}
          </select>
        )}
        <button
          type="button"
          onClick={() => setShowBulkImport(true)}
          className="ml-auto text-sm px-3 py-1.5 rounded border border-indigo-300 text-indigo-700 hover:bg-indigo-50 whitespace-nowrap flex-shrink-0"
          data-testid="bulk-import-btn"
        >
          Bulk import questions
        </button>
      </div>

      {/* Workspace area */}
      <div className="flex-1 min-h-0">
        {selectedPaperId ? (
          <Suspense fallback={<div className="p-8 text-gray-400">Loading…</div>}>
            <PyqPaperWorkspace paperId={selectedPaperId} embedded />
          </Suspense>
        ) : (
          <div className="h-full flex items-center justify-center text-gray-400 text-sm" data-testid="pyq-no-paper-selected">
            Select a paper to begin reviewing.
          </div>
        )}
      </div>
      {showBulkImport && (
        <BulkImportModal
          papers={papers}
          initialPaperId={selectedPaperId}
          onClose={() => setShowBulkImport(false)}
        />
      )}
    </div>
  );
}
