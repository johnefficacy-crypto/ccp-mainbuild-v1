import React, { lazy, Suspense, useState } from "react";
import { useExamWorkspace } from "../ExamWorkspaceContext";
import { usePyqWorkbench } from "./usePyqWorkbench";
import BulkImportModal from "./bulk-import/BulkImportModal";

const PyqPaperWorkspace = lazy(() => import("../../studyos/PyqPaperWorkspace"));

const TRUST_LABEL = {
  verified: "Verified",
  rejected: "Rejected",
  pending: "Pending",
};

export default function PyqWorkbenchPanel() {
  const { exam, cycle } = useExamWorkspace();
  const examId = exam?.id;
  const cycleId = cycle?.id ?? null;

  const { papers, selectedPaperId, setSelectedPaperId, loading, error } = usePyqWorkbench(
    examId,
    cycleId,
  );

  const [showBulkImport, setShowBulkImport] = useState(false);

  return (
    <div className="flex flex-col h-full" data-testid="pyq-workbench-panel">
      {/* Paper overview table */}
      <div className="px-4 py-3 border-b border-gray-200 bg-white flex-shrink-0">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">PYQ Papers</span>
          <button
            type="button"
            onClick={() => setShowBulkImport(true)}
            className="text-sm px-3 py-1.5 rounded border border-indigo-300 text-indigo-700 hover:bg-indigo-50 whitespace-nowrap flex-shrink-0"
            data-testid="bulk-import-btn"
          >
            Bulk import questions
          </button>
        </div>
        {loading && <span className="text-sm text-gray-400">Loading papers…</span>}
        {error && <span className="text-sm text-rose-600" data-testid="pyq-papers-error">{error}</span>}
        {!loading && !error && papers.length === 0 && (
          <span className="text-sm text-gray-500" data-testid="pyq-empty-state">
            No PYQ papers for this exam/cycle. Create one in the CMS.
          </span>
        )}
        {!loading && papers.length > 0 && (
          <table
            className="w-full text-sm border-collapse"
            data-testid="pyq-paper-table"
          >
            <thead>
              <tr className="text-left text-xs text-gray-500 border-b border-gray-200">
                <th className="pb-1 pr-4 font-medium">Year</th>
                <th className="pb-1 pr-4 font-medium">Section</th>
                <th className="pb-1 pr-4 font-medium">Questions</th>
                <th className="pb-1 font-medium">Readiness</th>
              </tr>
            </thead>
            <tbody>
              {papers.map((p) => {
                const isSelected = p.id === selectedPaperId;
                const expectedCount = p.metadata?.expected_question_count ?? "—";
                const readiness = TRUST_LABEL[p.trust_status] ?? p.trust_status ?? "—";
                const section = [p.paper_code, p.shift].filter(Boolean).join(" · ") || "—";
                return (
                  <tr
                    key={p.id}
                    data-testid={`pyq-paper-row-${p.id}`}
                    onClick={() => setSelectedPaperId(p.id)}
                    style={{
                      cursor: "pointer",
                      fontWeight: isSelected ? "bold" : "normal",
                      background: isSelected ? "#eef2ff" : "transparent",
                    }}
                    className="border-b border-gray-100 hover:bg-indigo-50 transition-colors"
                  >
                    <td className="py-1.5 pr-4">{p.year ?? "—"}</td>
                    <td className="py-1.5 pr-4">{section}</td>
                    <td className="py-1.5 pr-4">{expectedCount}</td>
                    <td className="py-1.5">{readiness}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
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
