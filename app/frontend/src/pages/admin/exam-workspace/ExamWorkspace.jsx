/**
 * ExamWorkspace — shell for the Exam Intelligence admin workspace (PR1).
 *
 * Renders: header with exam name + cycle picker, 7 disabled tabs, and a
 * placeholder content area.  All tab sections are deferred to later PRs.
 *
 * Routes:
 *   /admin/exam-intelligence/workspace/:exam_id
 *   /admin/exam-intelligence/workspace/:exam_id/:cycle_id
 */
import React from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ExamWorkspaceProvider, useExamWorkspace } from "./ExamWorkspaceContext";

const TABS = [
  { id: "setup",       label: "Setup" },
  { id: "documents",   label: "Documents" },
  { id: "syllabus",    label: "Syllabus Mapper" },
  { id: "pyq",         label: "PYQ Workbench" },
  { id: "updates",     label: "Updates" },
  { id: "competition", label: "Competition" },
  { id: "review",      label: "Review & Activate" },
];

function WorkspaceShell() {
  const { exam_id } = useParams();
  const navigate = useNavigate();
  const { exam, cycles, loading, error, refetch } = useExamWorkspace();

  function handleCycleChange(e) {
    const val = e.target.value;
    if (val) {
      navigate(`/admin/exam-intelligence/workspace/${exam_id}/${val}`);
    } else {
      navigate(`/admin/exam-intelligence/workspace/${exam_id}`);
    }
  }

  if (loading) {
    return (
      <div className="p-8 space-y-4" data-testid="workspace-loading">
        <div className="h-8 bg-gray-200 rounded w-1/3 animate-pulse" />
        <div className="h-4 bg-gray-200 rounded w-1/4 animate-pulse" />
        <div className="h-10 bg-gray-200 rounded w-full animate-pulse" />
        <div className="h-64 bg-gray-200 rounded w-full animate-pulse" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8" data-testid="workspace-error">
        <div className="rounded-md bg-rose-50 border border-rose-200 p-4 mb-4">
          <p className="text-sm text-rose-700">{error}</p>
        </div>
        <button
          onClick={refetch}
          className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded hover:bg-indigo-700"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white px-6 py-4 flex items-center gap-4">
        <div className="flex-1 min-w-0">
          <h1 className="text-xl font-semibold text-gray-900 truncate" data-testid="exam-name">
            {exam?.name ?? exam_id}
          </h1>
          {exam?.exam_type && (
            <span className="text-xs text-gray-500 uppercase tracking-wide">{exam.exam_type}</span>
          )}
        </div>

        {/* Cycle picker */}
        <div className="shrink-0">
          <select
            data-testid="cycle-picker"
            onChange={handleCycleChange}
            defaultValue=""
            className="text-sm border border-gray-300 rounded px-3 py-1.5 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All cycles</option>
            {cycles.map((c) => (
              <option key={c.id} value={c.id}>
                {c.cycle_name ?? c.year ?? c.id}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Tab strip — all disabled in PR1 */}
      <div className="border-b border-gray-200 bg-white px-6" role="tablist" data-testid="tab-strip">
        <div className="flex gap-1 -mb-px">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              role="tab"
              aria-selected="false"
              aria-disabled="true"
              disabled
              className="px-4 py-3 text-sm font-medium text-gray-400 border-b-2 border-transparent cursor-not-allowed select-none"
              data-testid={`tab-${tab.id}`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content area */}
      <div className="flex-1 flex items-center justify-center text-gray-400 text-sm" data-testid="workspace-placeholder">
        Select a section to begin
      </div>
    </div>
  );
}

export default function ExamWorkspace() {
  return (
    <ExamWorkspaceProvider>
      <WorkspaceShell />
    </ExamWorkspaceProvider>
  );
}
